#!/usr/bin/env python3
"""Shadow-replay historical v1 HoVer assignments through the v2 posterior.

Historical runs predate the immutable v2 causal ledger. Reconstructed rows are
never written to production evidence, and every approximation remains visible.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter, defaultdict
import csv
from datetime import UTC, datetime
import json
import math
from pathlib import Path
import re
import sys
from typing import Any, Literal
from zoneinfo import ZoneInfo

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from pydantic import BaseModel, ConfigDict, Field, model_validator  # noqa: E402
from scipy.stats import binomtest  # noqa: E402
import yaml  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gigaevo.memory.cards import Card  # noqa: E402
from gigaevo.memory_v2.features import (  # noqa: E402
    FeatureConfig,
    HierarchicalFeatureMap,
)
from gigaevo.memory_v2.models import (  # noqa: E402
    BehaviorCoordinate,
    CardSnapshot,
    CausalObservation,
    EnvironmentFingerprint,
    EvolutionContext,
    LLMFingerprint,
    MapElitesContext,
    OutcomeMeasurement,
    RewardDefinition,
    canonical_digest,
    import_qualified_class,
)
from gigaevo.memory_v2.posterior import (  # noqa: E402
    HierarchicalTerminalUtilityPosterior,
    TerminalUtilityPosteriorConfig,
)

LOG_TIME = r"(?P<time>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)"
CONTEXT_SELECTED_RE = re.compile(
    rf"^{LOG_TIME} .*\[Memory\]\[ContextStage\] Selected \d+ card\(s\) "
    r"for (?P<parent>[0-9a-f]{8}) \(ids=(?P<ids>\(.+\))\)"
)
CONTEXT_WITHHELD_RE = re.compile(
    rf"^{LOG_TIME} .*\[Memory\]\[ContextStage\] Withheld \d+ selected "
    r"card\(s\) for no-card control on (?P<parent>[0-9a-f]{8}) "
    r"\(ids=(?P<ids>\(.+\))\)"
)
CONTEXT_EMPTY_RE = re.compile(
    rf"^{LOG_TIME} .*\[Memory\]\[ContextStage\] Empty selection for "
    r"(?P<parent>[0-9a-f]{8}) \(candidates=(?P<candidates>\d+)\)"
)
MUTATION_RE = re.compile(
    rf"^{LOG_TIME} .*\[mutation\] Task \d+: \['(?P<parent>[0-9a-f]{{8}})'\] "
    r"\u2192 (?P<child>[0-9a-f]{8})"
)
FETCH_METRICS_RE = re.compile(
    rf"^{LOG_TIME} .*\[FetchMetrics\] (?P<child>[0-9a-f]{{8}}) metrics="
)
ARCHIVE_SIZE_RE = re.compile(r"Archive: N=(\d+)")
ARCHIVE_PERCENTILE_RE = re.compile(r"archive-percentile p(\d+(?:\.\d+)?)")
CONTEXT_CELL_RE = re.compile(r"^bd_cell:(\d+)/(\d+)/(\d+)$")
MOSCOW = ZoneInfo("Europe/Moscow")
TERMINAL_STATES = frozenset({"done", "discarded"})


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True, allow_inf_nan=False)


class HistoricalSlateRow(FrozenModel):
    card_id: str = Field(min_length=1)
    context_key: str = ""
    probe_selected: bool = False
    selection_reason: str = ""
    bid: float = 0.0


class HistoricalSelection(FrozenModel):
    event: Literal["MEMORY_READ_SELECTION"]
    timestamp_utc: datetime
    decision_id: str = Field(min_length=1)
    program_id: str = Field(min_length=1)
    selected_ids: tuple[str, ...] = ()
    candidate_ids: tuple[str, ...] = ()
    slate: tuple[HistoricalSlateRow, ...] = ()
    empty_reason: str = ""

    @model_validator(mode="after")
    def _singleton(self) -> HistoricalSelection:
        if len(self.selected_ids) > 1:
            raise ValueError("historical singleton replay found a multi-card slate")
        return self

    @property
    def card_id(self) -> str | None:
        return self.selected_ids[0] if self.selected_ids else None

    @property
    def context_key(self) -> str:
        if self.card_id is None:
            return ""
        row = next((row for row in self.slate if row.card_id == self.card_id), None)
        return "" if row is None else row.context_key


class HistoricalMutationOutput(FrozenModel):
    card_ids_used: tuple[str, ...] = ()


class HistoricalMetadata(FrozenModel):
    memory_base_selected_idea_ids: tuple[str, ...] = ()
    memory_injected_idea_ids: tuple[str, ...] = ()
    memory_base_metrics: dict[str, float] = Field(default_factory=dict)
    memory_base_id: str = ""
    memory_base_scores: tuple[float, ...] = ()
    memory_no_card_control: bool = False
    memory_used: bool = False
    per_sample_scores: tuple[float, ...] = ()
    mutation_context: str = ""
    mutation_output: HistoricalMutationOutput = Field(
        default_factory=HistoricalMutationOutput
    )


class HistoricalLineage(FrozenModel):
    parents: tuple[str, ...] = ()
    generation: int = Field(default=1, ge=1)


class HistoricalProgram(FrozenModel):
    id: str = Field(min_length=1)
    metrics: dict[str, float] = Field(default_factory=dict)
    metadata: HistoricalMetadata = Field(default_factory=HistoricalMetadata)
    iteration: int = Field(default=0, ge=0)
    state: str
    lineage: HistoricalLineage
    created_at: datetime


class StoredNoCardObservation(FrozenModel):
    id: str = Field(min_length=1)
    randomized_control: bool = False
    delta: float
    invalid: bool = False


class StoredNoCardEvidence(FrozenModel):
    observations: tuple[StoredNoCardObservation, ...] = ()


ContextAction = Literal["empty", "delivered", "withheld"]


class ContextResult(FrozenModel):
    timestamp: datetime
    parent_prefix: str = Field(min_length=8, max_length=8)
    action: ContextAction
    card_ids: tuple[str, ...] = ()
    candidate_count: int = Field(default=0, ge=0)


class HistoricalEpisode(FrozenModel):
    selection: HistoricalSelection
    context_result: ContextResult

    @model_validator(mode="after")
    def _coherent(self) -> HistoricalEpisode:
        expected = () if self.selection.card_id is None else self.selection.selected_ids
        if self.context_result.card_ids != expected:
            raise ValueError("selection and ContextStage card ids differ")
        if self.selection.card_id is None and self.context_result.action != "empty":
            raise ValueError("empty provider result became a treatment")
        if self.selection.card_id is not None and self.context_result.action == "empty":
            raise ValueError("proposed card vanished before ContextStage")
        return self


class MutationLink(FrozenModel):
    timestamp: datetime
    parent_prefix: str = Field(min_length=8, max_length=8)
    child_prefix: str = Field(min_length=8, max_length=8)


class ReplayChild(FrozenModel):
    child_id: str
    completion_time: datetime | None = None
    terminal_storage_state: bool
    outcome: float | None = None
    invalid: bool | None = None
    paired_se: float | None = Field(default=None, ge=0.0)
    n_pairs: int | None = Field(default=None, ge=2)
    declared_use: bool
    declared_used_card_ids: tuple[str, ...] = ()
    mutable_control_flag: bool
    stored_randomized_control: bool


class ReplayEpisode(FrozenModel):
    run_id: str
    decision_id: str
    parent_id: str
    card_id: str | None
    action: ContextAction
    offer_propensity: float = Field(gt=0.0, lt=1.0)
    context_key: str
    selection_time: datetime
    children: tuple[ReplayChild, ...] = ()
    payload_source: Literal["checkpoint_snapshot", "historical_id_only", "none"]

    @property
    def proposed(self) -> bool:
        return self.card_id is not None

    @property
    def treatment(self) -> bool:
        return self.action == "delivered"

    @property
    def measured_children(self) -> tuple[ReplayChild, ...]:
        return tuple(row for row in self.children if row.outcome is not None)

    @property
    def strict_children(self) -> tuple[ReplayChild, ...]:
        return tuple(
            row for row in self.measured_children if row.terminal_storage_state
        )


class RunInputs(FrozenModel):
    run_dir: Path
    checkpoint_dir: Path
    config: dict[str, Any]
    selections: tuple[HistoricalSelection, ...]
    programs: tuple[HistoricalProgram, ...]
    contexts: tuple[ContextResult, ...]
    mutations: tuple[MutationLink, ...]
    metric_times: dict[str, datetime]
    stored_no_card: StoredNoCardEvidence
    cards: tuple[Card, ...]


def _read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _parse_log_time(value: str) -> datetime:
    local = datetime.strptime(value, "%Y-%m-%d %H:%M:%S.%f").replace(tzinfo=MOSCOW)
    return local.astimezone(UTC)


def _parse_ids(value: str) -> tuple[str, ...]:
    parsed = ast.literal_eval(value)
    if not isinstance(parsed, tuple) or not all(
        isinstance(item, str) for item in parsed
    ):
        raise ValueError(f"invalid ContextStage ids: {value!r}")
    return parsed


def _read_log(
    path: Path,
) -> tuple[tuple[ContextResult, ...], tuple[MutationLink, ...], dict[str, datetime]]:
    contexts: list[ContextResult] = []
    mutations: list[MutationLink] = []
    metric_times: dict[str, datetime] = {}
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            match = CONTEXT_SELECTED_RE.search(line)
            if match is not None:
                contexts.append(
                    ContextResult(
                        timestamp=_parse_log_time(match.group("time")),
                        parent_prefix=match.group("parent"),
                        action="delivered",
                        card_ids=_parse_ids(match.group("ids")),
                    )
                )
                continue
            match = CONTEXT_WITHHELD_RE.search(line)
            if match is not None:
                contexts.append(
                    ContextResult(
                        timestamp=_parse_log_time(match.group("time")),
                        parent_prefix=match.group("parent"),
                        action="withheld",
                        card_ids=_parse_ids(match.group("ids")),
                    )
                )
                continue
            match = CONTEXT_EMPTY_RE.search(line)
            if match is not None:
                contexts.append(
                    ContextResult(
                        timestamp=_parse_log_time(match.group("time")),
                        parent_prefix=match.group("parent"),
                        action="empty",
                        candidate_count=int(match.group("candidates")),
                    )
                )
                continue
            match = MUTATION_RE.search(line)
            if match is not None:
                mutations.append(
                    MutationLink(
                        timestamp=_parse_log_time(match.group("time")),
                        parent_prefix=match.group("parent"),
                        child_prefix=match.group("child"),
                    )
                )
                continue
            match = FETCH_METRICS_RE.search(line)
            if match is not None:
                metric_times[match.group("child")] = _parse_log_time(
                    match.group("time")
                )
    return tuple(contexts), tuple(mutations), metric_times


def _load_selections(path: Path) -> tuple[HistoricalSelection, ...]:
    rows: list[HistoricalSelection] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if '"event": "MEMORY_READ_SELECTION"' not in line:
                continue
            try:
                rows.append(HistoricalSelection.model_validate_json(line))
            except Exception as exc:
                raise ValueError(f"invalid selection at {path}:{line_number}") from exc
    return tuple(sorted(rows, key=lambda row: (row.timestamp_utc, row.decision_id)))


def _program_dir(run_dir: Path) -> Path:
    candidates = sorted((run_dir / "storage").glob("*/programs"))
    if len(candidates) != 1:
        raise ValueError(f"expected one disk program directory under {run_dir}")
    return candidates[0]


def _load_programs(path: Path) -> tuple[HistoricalProgram, ...]:
    return tuple(
        sorted(
            (
                HistoricalProgram.model_validate(_read_json(program_path))
                for program_path in path.glob("*.json")
            ),
            key=lambda row: (row.created_at, row.id),
        )
    )


def _load_cards(path: Path) -> tuple[Card, ...]:
    if not path.is_file():
        return ()
    raw = _read_json(path)
    cards = raw.get("cards", {}) if isinstance(raw, dict) else {}
    if not isinstance(cards, dict):
        raise ValueError(f"{path} has an invalid cards mapping")
    return tuple(Card.model_validate(value) for value in cards.values())


def _no_card_offer_probability(config: dict[str, Any]) -> float:
    pipeline_builder = config.get("pipeline_builder")
    pipeline = config.get("pipeline")
    control = (
        pipeline_builder.get("no_card_control_probability")
        if isinstance(pipeline_builder, dict)
        else None
    )
    if control is None and isinstance(pipeline, dict):
        control = pipeline.get("no_card_control_probability")
    if not isinstance(control, (float, int)) or isinstance(control, bool):
        raise ValueError("resolved config lacks no-card control probability")
    offer = 1.0 - float(control)
    if not 0.0 < offer < 1.0:
        raise ValueError("historical offer gate lacks overlap")
    return offer


def load_run(run_dir: Path) -> RunInputs:
    run_dir = run_dir.resolve()
    with (run_dir / ".hydra" / "config.yaml").open(encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict):
        raise ValueError("resolved Hydra config is not a mapping")
    checkpoint_value = config.get("checkpoint_dir")
    if not isinstance(checkpoint_value, str) or not checkpoint_value:
        raise ValueError("resolved Hydra config has no checkpoint_dir")
    checkpoint = Path(checkpoint_value).resolve()
    log_paths = sorted(run_dir.glob("evolution_*.log"))
    if len(log_paths) != 1:
        raise ValueError(f"expected one evolution log under {run_dir}")
    contexts, mutations, metric_times = _read_log(log_paths[0])
    no_card_path = checkpoint / "no_card_evidence.json"
    stored = (
        StoredNoCardEvidence.model_validate(_read_json(no_card_path))
        if no_card_path.is_file()
        else StoredNoCardEvidence()
    )
    return RunInputs(
        run_dir=run_dir,
        checkpoint_dir=checkpoint,
        config=config,
        selections=_load_selections(run_dir / "memory" / "memory_events.jsonl"),
        programs=_load_programs(_program_dir(run_dir)),
        contexts=contexts,
        mutations=mutations,
        metric_times=metric_times,
        stored_no_card=stored,
        cards=_load_cards(checkpoint / "cards.json"),
    )


def _unique_prefix_map(programs: tuple[HistoricalProgram, ...]) -> dict[str, str]:
    by_prefix: dict[str, list[str]] = defaultdict(list)
    for program in programs:
        by_prefix[program.id[:8]].append(program.id)
    ambiguous = {key: values for key, values in by_prefix.items() if len(values) != 1}
    if ambiguous:
        raise ValueError(f"ambiguous eight-character program prefixes: {ambiguous}")
    return {key: values[0] for key, values in by_prefix.items()}


def _join_contexts(inputs: RunInputs) -> tuple[HistoricalEpisode, ...]:
    unused = set(range(len(inputs.contexts)))
    episodes: list[HistoricalEpisode] = []
    for selection in inputs.selections:
        expected_cards = selection.selected_ids
        candidates = [
            index
            for index in unused
            for context in (inputs.contexts[index],)
            if context.parent_prefix == selection.program_id[:8]
            and context.card_ids == expected_cards
            and 0.0
            <= (context.timestamp - selection.timestamp_utc).total_seconds()
            <= 10.0
        ]
        if len(candidates) != 1:
            raise ValueError(
                "selection does not join exactly one ContextStage result: "
                f"{selection.decision_id}, matches={len(candidates)}"
            )
        index = candidates[0]
        unused.remove(index)
        episodes.append(
            HistoricalEpisode(
                selection=selection,
                context_result=inputs.contexts[index],
            )
        )
    if unused:
        raise ValueError(f"{len(unused)} ContextStage results have no selection")
    return tuple(episodes)


def _paired_uncertainty(program: HistoricalProgram) -> tuple[float | None, int | None]:
    child = np.asarray(program.metadata.per_sample_scores, dtype=float)
    base = np.asarray(program.metadata.memory_base_scores, dtype=float)
    if child.ndim != 1 or child.size < 2 or child.shape != base.shape:
        return None, None
    if not np.isfinite(child).all() or not np.isfinite(base).all():
        return None, None
    differences = child - base
    return float(differences.std(ddof=1) / math.sqrt(len(differences))), len(
        differences
    )


def _child_record(
    program: HistoricalProgram,
    *,
    completion_time: datetime | None,
    stored_controls: frozenset[str],
) -> ReplayChild:
    base_fitness = program.metadata.memory_base_metrics.get("fitness")
    child_fitness = program.metrics.get("fitness")
    outcome = None
    invalid = None
    if (
        completion_time is not None
        and base_fitness is not None
        and child_fitness is not None
    ):
        outcome = float(child_fitness) - float(base_fitness)
        invalid = program.metrics.get("is_valid", 0.0) < 0.5
    paired_se, n_pairs = _paired_uncertainty(program)
    declared_used_card_ids = program.metadata.mutation_output.card_ids_used
    return ReplayChild(
        child_id=program.id,
        completion_time=completion_time,
        terminal_storage_state=program.state in TERMINAL_STATES,
        outcome=outcome,
        invalid=invalid,
        paired_se=paired_se,
        n_pairs=n_pairs,
        declared_use=bool(declared_used_card_ids),
        declared_used_card_ids=declared_used_card_ids,
        mutable_control_flag=program.metadata.memory_no_card_control,
        stored_randomized_control=program.id in stored_controls,
    )


def reconstruct_episodes(inputs: RunInputs) -> tuple[ReplayEpisode, ...]:
    episodes = _join_contexts(inputs)
    programs = {row.id: row for row in inputs.programs}
    prefixes = _unique_prefix_map(inputs.programs)
    cards = {row.id: row for row in inputs.cards}
    stored_controls = frozenset(
        row.id for row in inputs.stored_no_card.observations if row.randomized_control
    )
    children_by_decision: dict[str, list[ReplayChild]] = defaultdict(list)

    episodes_by_parent: dict[str, list[HistoricalEpisode]] = defaultdict(list)
    for episode in episodes:
        episodes_by_parent[episode.selection.program_id].append(episode)
    for rows in episodes_by_parent.values():
        rows.sort(key=lambda row: row.context_result.timestamp)

    for mutation in inputs.mutations:
        try:
            parent_id = prefixes[mutation.parent_prefix]
            child_id = prefixes[mutation.child_prefix]
        except KeyError as exc:
            raise ValueError(
                f"mutation link references an unknown program: {mutation}"
            ) from exc
        eligible = [
            episode
            for episode in episodes_by_parent.get(parent_id, [])
            if episode.context_result.timestamp <= mutation.timestamp
        ]
        if not eligible:
            raise ValueError(f"mutation child {child_id} has no prior context episode")
        latest_time = max(row.context_result.timestamp for row in eligible)
        latest = [
            row for row in eligible if row.context_result.timestamp == latest_time
        ]
        if len(latest) != 1:
            raise ValueError(
                f"mutation child {child_id} has an ambiguous context episode"
            )
        episode = latest[0]
        child = programs[child_id]
        if child.metadata.memory_base_id != parent_id:
            raise ValueError(f"child {child_id} frozen base differs from mutation log")
        if parent_id not in child.lineage.parents:
            raise ValueError(f"child {child_id} lineage omits logged parent")
        expected_proposed = episode.selection.selected_ids
        expected_injected = (
            expected_proposed if episode.context_result.action == "delivered" else ()
        )
        if child.metadata.memory_base_selected_idea_ids != expected_injected:
            raise ValueError(f"child {child_id} frozen effective slate is inconsistent")
        if child.metadata.memory_injected_idea_ids != expected_injected:
            raise ValueError(f"child {child_id} frozen injected slate is inconsistent")
        undeclared = set(child.metadata.mutation_output.card_ids_used) - set(
            expected_injected
        )
        if undeclared:
            raise ValueError(
                f"child {child_id} declared cards outside its injected slate: "
                f"{sorted(undeclared)}"
            )
        completion_time = inputs.metric_times.get(child_id[:8])
        children_by_decision[episode.selection.decision_id].append(
            _child_record(
                child,
                completion_time=completion_time,
                stored_controls=stored_controls,
            )
        )

    offer_probability = _no_card_offer_probability(inputs.config)
    result: list[ReplayEpisode] = []
    for episode in episodes:
        card_id = episode.selection.card_id
        result.append(
            ReplayEpisode(
                run_id=inputs.run_dir.name,
                decision_id=episode.selection.decision_id,
                parent_id=episode.selection.program_id,
                card_id=card_id,
                action=episode.context_result.action,
                offer_propensity=offer_probability,
                context_key=episode.selection.context_key,
                selection_time=episode.selection.timestamp_utc,
                children=tuple(
                    sorted(
                        children_by_decision.get(episode.selection.decision_id, []),
                        key=lambda row: row.child_id,
                    )
                ),
                payload_source=(
                    "none"
                    if card_id is None
                    else "checkpoint_snapshot"
                    if card_id in cards
                    else "historical_id_only"
                ),
            )
        )
    return tuple(result)


def _episode_outcome(
    episode: ReplayEpisode,
    *,
    strict_storage_terminal: bool,
) -> tuple[float, bool, float | None, int | None] | None:
    children = (
        episode.strict_children
        if strict_storage_terminal
        else episode.measured_children
    )
    if not children:
        return None
    values = [row.outcome for row in children]
    if any(value is None for value in values):
        raise AssertionError("measured child lacks an outcome")
    invalid = any(row.invalid is True for row in children)
    outcome = float(np.mean(np.asarray(values, dtype=float)))
    paired = [row for row in children if row.paired_se is not None]
    paired_se = None
    n_pairs = None
    if len(paired) == len(children):
        paired_se = float(
            math.sqrt(sum(float(row.paired_se) ** 2 for row in paired)) / len(paired)
        )
        n_pairs = min(int(row.n_pairs or 0) for row in paired)
    return outcome, invalid, paired_se, n_pairs


def _config_string(config: dict[str, Any], key: str, default: str) -> str:
    value = config.get(key, default)
    return value if isinstance(value, str) and value else default


def _task_key(config: dict[str, Any]) -> str:
    problem = config.get("problem")
    if isinstance(problem, dict):
        name = problem.get("name")
        if isinstance(name, str) and name:
            return name
    return "chains/hover/full7_vectorized"


def _environment(inputs: RunInputs) -> EnvironmentFingerprint:
    config = inputs.config
    pipeline = config.get("pipeline")
    program_format = config.get("program_format")
    mutation = config.get("mutation_operator")
    pipeline_id = (
        str(pipeline.get("id", "historical"))
        if isinstance(pipeline, dict)
        else "historical"
    )
    format_id = (
        str(program_format.get("id", "historical"))
        if isinstance(program_format, dict)
        else "historical"
    )
    mutation_path = (
        str(
            mutation.get(
                "_target_",
                "gigaevo.evolution.mutation.mutation_operator.LLMMutationOperator",
            )
        )
        if isinstance(mutation, dict)
        else "gigaevo.evolution.mutation.mutation_operator.LLMMutationOperator"
    )
    temperature = config.get("temperature", 0.0)
    task_key = _task_key(config)
    return EnvironmentFingerprint(
        task_key=task_key,
        problem_name=task_key,
        llm=LLMFingerprint(
            model_name=_config_string(config, "model_name", "unknown"),
            base_url=_config_string(config, "llm_base_url", "unknown"),
            temperature=float(temperature),
        ),
        mutation_operator=import_qualified_class(mutation_path),
        program_format=format_id,
        pipeline=pipeline_id,
        algorithm="chains_bd3d",
    )


def _static_cell(parent: HistoricalProgram) -> tuple[int, int, int]:
    values = (
        (parent.metrics.get("hop_depth", 0.0), 0.0, 5.0, 5),
        (parent.metrics.get("passages_fetched", 0.0), 0.0, 45.0, 5),
        (parent.metrics.get("instr_chars", 0.0), 0.0, 2500.0, 6),
    )
    result: list[int] = []
    for value, lower, upper, bins in values:
        normalized = min(max((float(value) - lower) / (upper - lower), 0.0), 1.0)
        result.append(min(int(normalized * bins), bins - 1))
    return result[0], result[1], result[2]


def _parse_cell(value: str, parent: HistoricalProgram) -> tuple[int, int, int]:
    match = CONTEXT_CELL_RE.fullmatch(value)
    if match is None:
        return _static_cell(parent)
    cell = tuple(int(match.group(index)) for index in (1, 2, 3))
    if any(index >= bins for index, bins in zip(cell, (5, 5, 6), strict=True)):
        raise ValueError(f"historical context cell is out of range: {value!r}")
    return cell  # type: ignore[return-value]


def _semantic_normalize(value: float, upper: float, transform: str) -> float:
    clipped = min(max(float(value), 0.0), upper)
    if transform == "log1p":
        return math.log1p(clipped) / math.log1p(upper)
    return clipped / upper


def _context(
    inputs: RunInputs,
    episode: ReplayEpisode,
    environment: EnvironmentFingerprint,
) -> EvolutionContext:
    programs = {row.id: row for row in inputs.programs}
    parent = programs[episode.parent_id]
    cell = _parse_cell(episode.context_key, parent)
    axis_specs = (
        ("hop_depth", 5.0, 5, "linear"),
        ("passages_fetched", 45.0, 5, "log1p"),
        ("instr_chars", 2500.0, 6, "log1p"),
    )
    coordinates = tuple(
        BehaviorCoordinate(
            key=key,
            raw_value=float(parent.metrics.get(key, 0.0)),
            semantic_normalized=_semantic_normalize(
                float(parent.metrics.get(key, 0.0)), upper, transform
            ),
            dynamic_normalized=(cell[index] + 0.5) / bins,
            cell_index=cell[index],
            num_bins=bins,
            dynamic_lower_bound=0.0,
            dynamic_upper_bound=upper,
        )
        for index, (key, upper, bins, transform) in enumerate(axis_specs)
    )
    mutation_context = parent.metadata.mutation_context
    archive_match = ARCHIVE_SIZE_RE.search(mutation_context)
    percentile_match = ARCHIVE_PERCENTILE_RE.search(mutation_context)
    raw_archive_size = 0 if archive_match is None else int(archive_match.group(1))
    archive_size = min(raw_archive_size, 150)
    quality = (
        None if percentile_match is None else float(percentile_match.group(1)) / 100.0
    )
    coverage = min(max(archive_size / 150.0, 0.0), 1.0)
    schema = [
        {
            "key": key,
            "upper": upper,
            "bins": bins,
            "transform": transform,
            "historical_dynamic_bounds": "unrecoverable",
        }
        for key, upper, bins, transform in axis_specs
    ]
    return EvolutionContext(
        run_id=inputs.run_dir.name,
        environment=environment,
        parent_id=parent.id,
        parent_iteration=parent.iteration,
        parent_generation=parent.lineage.generation,
        parent_metrics=dict(parent.metrics),
        reward=RewardDefinition(
            primary_metric="fitness",
            higher_is_better=True,
            metric_lower_bound=0.0,
            metric_upper_bound=1.0,
        ),
        map_elites=MapElitesContext(
            island_id="fitness_island",
            strategy_generation=parent.iteration,
            archive_size=archive_size,
            total_cells=150,
            coverage=coverage,
            parent_quality_quantile=quality,
            parent_cell=cell,
            parent_cell_occupied=True,
            # Exact local occupancy is absent. Global coverage is a transparent proxy.
            neighbor_occupancy=coverage,
            coordinates=coordinates,
            semantic_schema_hash=canonical_digest(
                {"historical_semantic_schema": tuple(row.key for row in coordinates)}
            ),
            behavior_schema_hash=canonical_digest(schema),
            archive_fingerprint=canonical_digest(
                {
                    "historical_archive_unrecoverable": True,
                    "raw_logged_archive_n": raw_archive_size,
                    "occupied_cell_proxy": archive_size,
                    "decision_id": episode.decision_id,
                }
            ),
        ),
    )


def _shadow_cards(
    inputs: RunInputs, episodes: tuple[ReplayEpisode, ...]
) -> dict[str, CardSnapshot]:
    task_key = _task_key(inputs.config)
    return {
        card_id: CardSnapshot.from_card(
            Card(
                id=card_id,
                task_key=task_key,
                category="historical_shadow",
                description=f"Historical treatment identity {card_id}",
            )
        )
        for card_id in sorted(
            {row.card_id for row in episodes if row.card_id is not None}
        )
    }


def _posterior_model(
    offer_probability: float,
    *,
    prior_scale: float = 1.0,
) -> HierarchicalTerminalUtilityPosterior:
    return HierarchicalTerminalUtilityPosterior(
        feature_map=HierarchicalFeatureMap(
            config=FeatureConfig(
                behavior_keys=("hop_depth", "passages_fetched", "instr_chars"),
            )
        ),
        config=TerminalUtilityPosteriorConfig(
            shared_effect_prior_sd=0.35 * prior_scale,
            card_effect_prior_sd=0.25 * prior_scale,
            reference_offer_probability=offer_probability,
        ),
    )


def _observations(
    inputs: RunInputs,
    episodes: tuple[ReplayEpisode, ...],
    *,
    strict_storage_terminal: bool,
    assume_paired_vectors: bool,
) -> tuple[
    tuple[CausalObservation, ...],
    dict[str, CardSnapshot],
    dict[str, EvolutionContext],
]:
    environment = _environment(inputs)
    cards = _shadow_cards(inputs, episodes)
    contexts: dict[str, EvolutionContext] = {}
    observations: list[CausalObservation] = []
    for ordinal, episode in enumerate(episodes):
        if episode.action == "empty" or episode.card_id is None:
            continue
        endpoint = _episode_outcome(
            episode, strict_storage_terminal=strict_storage_terminal
        )
        if endpoint is None:
            continue
        outcome, invalid, paired_se, n_pairs = endpoint
        context = _context(inputs, episode, environment)
        contexts[episode.decision_id] = context
        measurement = None
        if not invalid:
            if assume_paired_vectors and paired_se is not None and n_pairs is not None:
                measurement = OutcomeMeasurement(
                    value=outcome,
                    se=paired_se,
                    n_pairs=n_pairs,
                    kind="paired",
                    pairing_signature=canonical_digest(
                        {
                            "assumed_fixed_historical_cohort": True,
                            "run": inputs.run_dir.name,
                            "decision": episode.decision_id,
                        }
                    ),
                )
            else:
                measurement = OutcomeMeasurement(
                    value=outcome,
                    se=None,
                    kind="scalar",
                )
        offer = episode.offer_propensity
        treatment = episode.treatment
        card_used = treatment and any(
            episode.card_id in child.declared_used_card_ids
            for child in episode.children
        )
        observations.append(
            CausalObservation(
                decision_id=episode.decision_id,
                event_ordinal=ordinal,
                card=cards[episode.card_id],
                context=context,
                treatment=treatment,
                card_used=card_used,
                offer_propensity=offer,
                proposal_propensity=1.0,
                joint_action_propensity=offer if treatment else 1.0 - offer,
                status="invalid" if invalid else "outcome",
                measurement=measurement,
                reward_q_hat_control=0.0,
                reward_q_hat_treated=0.0,
                risk_q_hat_control=0.05,
                risk_q_hat_treated=0.05,
            )
        )
    return tuple(observations), cards, contexts


def _identification_status(treated: int, controls: int) -> str:
    if treated and controls:
        return "both_arms"
    if treated:
        return "treated_only"
    if controls:
        return "control_only"
    return "prior_only"


def _card_contexts(
    observations: tuple[CausalObservation, ...],
    cards: dict[str, CardSnapshot],
    contexts: dict[str, EvolutionContext],
) -> dict[str, EvolutionContext]:
    if not contexts:
        return {}
    fallback = contexts[min(contexts)]
    result: dict[str, EvolutionContext] = {}
    for card_id, card in cards.items():
        matching = [
            row.context
            for row in observations
            if row.card.treatment_id == card.treatment_id
        ]
        result[card_id] = matching[len(matching) // 2] if matching else fallback
    return result


def _prediction_rows(
    inputs: RunInputs,
    episodes: tuple[ReplayEpisode, ...],
    *,
    posterior_samples: int,
) -> tuple[
    list[dict[str, Any]],
    tuple[CausalObservation, ...],
    HierarchicalTerminalUtilityPosterior,
    Any,
]:
    conservative, cards, contexts = _observations(
        inputs,
        episodes,
        strict_storage_terminal=True,
        assume_paired_vectors=False,
    )
    paired, _, _ = _observations(
        inputs,
        episodes,
        strict_storage_terminal=True,
        assume_paired_vectors=True,
    )
    offer = _no_card_offer_probability(inputs.config)
    model = _posterior_model(offer)
    fitted = model.fit(conservative, tuple(cards.values()))
    fitted_paired = model.fit(paired, tuple(cards.values()))
    prior = model.fit((), tuple(cards.values()))
    card_contexts = _card_contexts(conservative, cards, contexts)
    rows: list[dict[str, Any]] = []
    for card_id, card in cards.items():
        context = card_contexts.get(card_id)
        if context is None:
            continue
        treated = sum(
            row.treatment and row.card.treatment_id == card.treatment_id
            for row in conservative
        )
        controls = sum(
            (not row.treatment) and row.card.treatment_id == card.treatment_id
            for row in conservative
        )
        predictions = {}
        for label, posterior, seed in (
            ("prior", prior, 101),
            ("conservative", fitted, 102),
            ("paired_assumption", fitted_paired, 103),
        ):
            predictions[label] = posterior.prediction(
                card,
                context,
                np.random.default_rng(seed),
                samples=posterior_samples,
                max_treated_invalid_probability=0.25,
                max_incremental_invalid_probability=0.10,
                safety_alpha=0.10,
            )
        row: dict[str, Any] = {
            "card_id": card_id,
            "treated_episodes": treated,
            "control_episodes": controls,
            "identification": _identification_status(treated, controls),
        }
        for label, prediction in predictions.items():
            row.update(
                {
                    f"{label}_effect_mean": prediction.usable_effect_mean,
                    f"{label}_effect_sd": prediction.usable_effect_sd,
                    f"{label}_probability_helpful": prediction.probability_helpful,
                    f"{label}_probability_safe": prediction.probability_safe,
                    f"{label}_treated_invalid": (
                        prediction.treated_invalid_probability
                    ),
                    f"{label}_incremental_invalid": (
                        prediction.incremental_invalid_probability
                    ),
                }
            )
        rows.append(row)
    return rows, conservative, model, fitted


def _episode_rows(episodes: tuple[ReplayEpisode, ...]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for episode in episodes:
        strict = _episode_outcome(episode, strict_storage_terminal=True)
        evaluated = _episode_outcome(episode, strict_storage_terminal=False)
        rows.append(
            {
                "decision_id": episode.decision_id,
                "parent_id": episode.parent_id,
                "selection_time": episode.selection_time.isoformat(),
                "action": episode.action,
                "card_id": episode.card_id or "",
                "candidate_context": episode.context_key,
                "offer_propensity": episode.offer_propensity,
                "proposal_propensity": "",
                "joint_propensity": "",
                "child_count": len(episode.children),
                "measured_child_count": len(episode.measured_children),
                "strict_child_count": len(episode.strict_children),
                "strict_episode_outcome": "" if strict is None else strict[0],
                "evaluated_episode_outcome": "" if evaluated is None else evaluated[0],
                "declared_use_count": sum(row.declared_use for row in episode.children),
                "declared_used_card_ids": "|".join(
                    sorted(
                        {
                            card_id
                            for child in episode.children
                            for card_id in child.declared_used_card_ids
                        }
                    )
                ),
                "stored_control_count": sum(
                    row.stored_randomized_control for row in episode.children
                ),
                "mutable_control_count": sum(
                    row.mutable_control_flag for row in episode.children
                ),
                "payload_source": episode.payload_source,
                "training_eligible": False,
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _complete_case_difference(
    episodes: tuple[ReplayEpisode, ...],
    *,
    strict_storage_terminal: bool,
) -> float | None:
    values: dict[bool, list[float]] = {True: [], False: []}
    for episode in episodes:
        if episode.action not in {"delivered", "withheld"}:
            continue
        endpoint = _episode_outcome(
            episode, strict_storage_terminal=strict_storage_terminal
        )
        if endpoint is not None:
            values[episode.treatment].append(endpoint[0])
    if not values[True] or not values[False]:
        return None
    return float(np.mean(values[True]) - np.mean(values[False]))


def _child_weighted_difference(
    episodes: tuple[ReplayEpisode, ...],
    *,
    strict_storage_terminal: bool,
) -> float | None:
    values: dict[bool, list[float]] = {True: [], False: []}
    for episode in episodes:
        if episode.action not in {"delivered", "withheld"}:
            continue
        children = (
            episode.strict_children
            if strict_storage_terminal
            else episode.measured_children
        )
        values[episode.treatment].extend(
            float(row.outcome) for row in children if row.outcome is not None
        )
    if not values[True] or not values[False]:
        return None
    return float(np.mean(values[True]) - np.mean(values[False]))


def _first_child_difference(episodes: tuple[ReplayEpisode, ...]) -> float | None:
    values: dict[bool, list[float]] = {True: [], False: []}
    for episode in episodes:
        if episode.action not in {"delivered", "withheld"}:
            continue
        children = sorted(
            episode.strict_children,
            key=lambda row: (
                row.completion_time or datetime.max.replace(tzinfo=UTC),
                row.child_id,
            ),
        )
        if children and children[0].outcome is not None:
            values[episode.treatment].append(float(children[0].outcome))
    if not values[True] or not values[False]:
        return None
    return float(np.mean(values[True]) - np.mean(values[False]))


def _offer_ess(
    observations: tuple[CausalObservation, ...], target: float = 0.5
) -> float:
    weights = np.asarray(
        [
            (target if row.treatment else 1.0 - target)
            / (row.offer_propensity if row.treatment else 1.0 - row.offer_propensity)
            for row in observations
        ],
        dtype=float,
    )
    if not len(weights) or not np.square(weights).sum():
        return 0.0
    return float(weights.sum() ** 2 / np.square(weights).sum())


def _confusion(
    inputs: RunInputs, episodes: tuple[ReplayEpisode, ...]
) -> dict[str, int]:
    stored = {
        row.id for row in inputs.stored_no_card.observations if row.randomized_control
    }
    true = {
        child.child_id
        for episode in episodes
        if episode.action == "withheld"
        for child in episode.measured_children
    }
    universe = {row.id for row in inputs.stored_no_card.observations} | true
    return {
        "true_positive": len(stored & true),
        "false_positive": len(stored - true),
        "false_negative": len(true - stored),
        "true_negative": len(universe - stored - true),
    }


def _observed_utility(row: CausalObservation) -> float:
    if row.invalid:
        parent = row.context.parent_metrics[row.context.reward.primary_metric]
        return row.context.reward.metric_lower_bound - parent
    if row.measurement is None:
        raise AssertionError("valid observation lacks a measurement")
    return row.measurement.value


def _counterfactual_rows(
    observations: tuple[CausalObservation, ...],
    fitted: Any,
    *,
    posterior_samples: int,
) -> list[dict[str, Any]]:
    q_hats: list[tuple[float, float, float, float]] = []
    for index, row in enumerate(observations):
        prediction = fitted.prediction(
            row.card,
            row.context,
            np.random.default_rng(10_000 + index),
            samples=posterior_samples,
            max_treated_invalid_probability=0.25,
            max_incremental_invalid_probability=0.10,
            safety_alpha=0.10,
        )
        q_hats.append(
            (
                prediction.usable_gain_control_mean,
                prediction.usable_gain_treated_mean,
                prediction.control_invalid_probability,
                prediction.treated_invalid_probability,
            )
        )

    result: list[dict[str, Any]] = []
    for target in (0.0, 0.25, 0.5, 0.75, 1.0):
        reward_scores: list[float] = []
        risk_scores: list[float] = []
        weights: list[float] = []
        for row, (q0, q1, r0, r1) in zip(observations, q_hats, strict=True):
            target_action = target if row.treatment else 1.0 - target
            behavior_action = (
                row.offer_propensity if row.treatment else 1.0 - row.offer_propensity
            )
            weight = target_action / behavior_action
            observed_reward = _observed_utility(row)
            observed_risk = float(row.invalid)
            q_action = q1 if row.treatment else q0
            r_action = r1 if row.treatment else r0
            reward_scores.append(
                (1.0 - target) * q0
                + target * q1
                + weight * (observed_reward - q_action)
            )
            risk_scores.append(
                (1.0 - target) * r0 + target * r1 + weight * (observed_risk - r_action)
            )
            weights.append(weight)
        weight_array = np.asarray(weights, dtype=float)
        ess = (
            0.0
            if not len(weight_array) or not np.square(weight_array).sum()
            else float(weight_array.sum() ** 2 / np.square(weight_array).sum())
        )
        result.append(
            {
                "target_offer_probability": target,
                "dr_reward": (
                    None if not reward_scores else float(np.mean(reward_scores))
                ),
                "dr_invalid_probability": (
                    None if not risk_scores else float(np.mean(risk_scores))
                ),
                "importance_ess": ess,
                "max_importance_weight": (0.0 if not weights else float(max(weights))),
                "n_episode_clusters": len(observations),
                "inferential_se": None,
                "shadow_only": True,
            }
        )
    return result


def _prefix_rows(
    observations: tuple[CausalObservation, ...],
    model: HierarchicalTerminalUtilityPosterior,
    *,
    posterior_samples: int,
) -> list[dict[str, Any]]:
    if not observations:
        return []
    counts = Counter(row.card.treatment_id for row in observations)
    target = max(
        observations,
        key=lambda row: (counts[row.card.treatment_id], row.card.treatment_id),
    )
    candidates = tuple(
        {row.card.treatment_id: row.card for row in observations}.values()
    )
    result: list[dict[str, Any]] = []
    for count in range(len(observations) + 1):
        prefix = observations[:count]
        fitted = model.fit(prefix, candidates)
        prediction = fitted.prediction(
            target.card,
            target.context,
            np.random.default_rng(50_000 + count),
            samples=posterior_samples,
            max_treated_invalid_probability=0.25,
            max_incremental_invalid_probability=0.10,
            safety_alpha=0.10,
        )
        evidence_hash = canonical_digest(
            [
                row.model_dump(mode="json", exclude_computed_fields=True)
                for row in prefix
            ]
        )
        result.append(
            {
                "evidence_count": count,
                "evidence_hash": evidence_hash,
                "card_id": target.card.bank_card_id,
                "effect_mean": prediction.usable_effect_mean,
                "effect_sd": prediction.usable_effect_sd,
                "probability_helpful": prediction.probability_helpful,
                "probability_safe": prediction.probability_safe,
                "treated_invalid_probability": (prediction.treated_invalid_probability),
            }
        )
    # Prefix replay must be deterministic and cannot see future observations.
    audit_count = len(observations) // 2
    replay = model.fit(observations[:audit_count], candidates).prediction(
        target.card,
        target.context,
        np.random.default_rng(50_000 + audit_count),
        samples=posterior_samples,
        max_treated_invalid_probability=0.25,
        max_incremental_invalid_probability=0.10,
        safety_alpha=0.10,
    )
    if not math.isclose(
        replay.usable_effect_mean,
        float(result[audit_count]["effect_mean"]),
        rel_tol=0.0,
        abs_tol=1e-12,
    ):
        raise AssertionError("prefix posterior changed after future evidence was added")
    return result


def _prior_sensitivity(
    observations: tuple[CausalObservation, ...],
    *,
    posterior_samples: int,
) -> list[dict[str, Any]]:
    if not observations:
        return []
    counts: dict[str, tuple[int, int]] = {}
    for row in observations:
        treated, controls = counts.get(row.card.treatment_id, (0, 0))
        counts[row.card.treatment_id] = (
            treated + int(row.treatment),
            controls + int(not row.treatment),
        )
    target = max(
        observations,
        key=lambda row: (
            int(all(counts[row.card.treatment_id])),
            sum(counts[row.card.treatment_id]),
            row.card.treatment_id,
        ),
    )
    candidates = tuple(
        {row.card.treatment_id: row.card for row in observations}.values()
    )
    result: list[dict[str, Any]] = []
    for scale in (0.5, 1.0, 2.0):
        model = _posterior_model(target.offer_propensity, prior_scale=scale)
        fitted = model.fit(observations, candidates)
        prediction = fitted.prediction(
            target.card,
            target.context,
            np.random.default_rng(70_000 + int(10 * scale)),
            samples=posterior_samples,
            max_treated_invalid_probability=0.25,
            max_incremental_invalid_probability=0.10,
            safety_alpha=0.10,
        )
        result.append(
            {
                "prior_scale": scale,
                "card_id": target.card.bank_card_id,
                "effect_mean": prediction.usable_effect_mean,
                "effect_sd": prediction.usable_effect_sd,
                "probability_helpful": prediction.probability_helpful,
            }
        )
    controls_removed = tuple(row for row in observations if row.treatment)
    fitted = _posterior_model(target.offer_propensity).fit(controls_removed, candidates)
    prediction = fitted.prediction(
        target.card,
        target.context,
        np.random.default_rng(70_100),
        samples=posterior_samples,
        max_treated_invalid_probability=0.25,
        max_incremental_invalid_probability=0.10,
        safety_alpha=0.10,
    )
    result.append(
        {
            "prior_scale": "leave_all_controls_out",
            "card_id": target.card.bank_card_id,
            "effect_mean": prediction.usable_effect_mean,
            "effect_sd": prediction.usable_effect_sd,
            "probability_helpful": prediction.probability_helpful,
        }
    )
    return result


def _standardized_mean_difference(
    left: list[float], right: list[float]
) -> float | None:
    if len(left) < 2 or len(right) < 2:
        return None
    left_array = np.asarray(left, dtype=float)
    right_array = np.asarray(right, dtype=float)
    pooled_variance = (
        (len(left_array) - 1) * left_array.var(ddof=1)
        + (len(right_array) - 1) * right_array.var(ddof=1)
    ) / (len(left_array) + len(right_array) - 2)
    if pooled_variance <= 0.0:
        return None
    return float((left_array.mean() - right_array.mean()) / math.sqrt(pooled_variance))


def _parent_balance(
    inputs: RunInputs, episodes: tuple[ReplayEpisode, ...]
) -> dict[str, Any]:
    programs = {row.id: row for row in inputs.programs}
    realized: list[float] = []
    unrealized: list[float] = []
    provider_empty: list[float] = []
    realized_provider_empty: list[float] = []
    for episode in episodes:
        fitness = programs[episode.parent_id].metrics.get("fitness")
        if fitness is None:
            continue
        if not episode.proposed:
            provider_empty.append(float(fitness))
            if episode.children:
                realized_provider_empty.append(float(fitness))
            continue
        target = realized if episode.children else unrealized
        target.append(float(fitness))
    return {
        "child_bearing_n": len(realized),
        "no_child_n": len(unrealized),
        "child_bearing_mean_parent_fitness": (
            None if not realized else float(np.mean(realized))
        ),
        "no_child_mean_parent_fitness": (
            None if not unrealized else float(np.mean(unrealized))
        ),
        "standardized_mean_difference": _standardized_mean_difference(
            realized, unrealized
        ),
        "provider_empty_n": len(provider_empty),
        "provider_empty_mean_parent_fitness": (
            None if not provider_empty else float(np.mean(provider_empty))
        ),
        "child_bearing_vs_provider_empty_smd": _standardized_mean_difference(
            realized, provider_empty
        ),
        "child_bearing_provider_empty_n": len(realized_provider_empty),
        "child_bearing_provider_empty_mean_parent_fitness": (
            None
            if not realized_provider_empty
            else float(np.mean(realized_provider_empty))
        ),
        "child_bearing_proposed_vs_empty_smd": _standardized_mean_difference(
            realized, realized_provider_empty
        ),
    }


def _censoring_bounds(
    inputs: RunInputs, episodes: tuple[ReplayEpisode, ...]
) -> dict[str, Any]:
    programs = {row.id: row for row in inputs.programs}
    values: dict[bool, list[tuple[float, float]]] = {True: [], False: []}
    observed: dict[bool, int] = {True: 0, False: 0}
    for episode in episodes:
        if episode.action not in {"delivered", "withheld"}:
            continue
        endpoint = _episode_outcome(episode, strict_storage_terminal=False)
        if endpoint is not None:
            values[episode.treatment].append((endpoint[0], endpoint[0]))
            observed[episode.treatment] += 1
            continue
        parent_fitness = float(programs[episode.parent_id].metrics["fitness"])
        values[episode.treatment].append((-parent_fitness, 1.0 - parent_fitness))

    if not values[True] or not values[False]:
        lower = None
        upper = None
    else:
        lower = float(
            np.mean([row[0] for row in values[True]])
            - np.mean([row[1] for row in values[False]])
        )
        upper = float(
            np.mean([row[1] for row in values[True]])
            - np.mean([row[0] for row in values[False]])
        )
    return {
        "delivered_decisions": len(values[True]),
        "withheld_decisions": len(values[False]),
        "delivered_observed": observed[True],
        "withheld_observed": observed[False],
        "worst_case_itt_lower": lower,
        "worst_case_itt_upper": upper,
        "reward_bounds": "child_fitness in [0, 1] relative to frozen parent",
    }


def _card_specific_difference(
    episodes: tuple[ReplayEpisode, ...], card_id: str
) -> float | None:
    values: dict[bool, list[float]] = {True: [], False: []}
    for episode in episodes:
        if episode.card_id != card_id:
            continue
        endpoint = _episode_outcome(episode, strict_storage_terminal=False)
        if endpoint is not None:
            values[episode.treatment].append(endpoint[0])
    if not values[True] or not values[False]:
        return None
    return float(np.mean(values[True]) - np.mean(values[False]))


def _summary(
    inputs: RunInputs,
    episodes: tuple[ReplayEpisode, ...],
    observations: tuple[CausalObservation, ...],
    prediction_rows: list[dict[str, Any]],
    prefix_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    actions = Counter(row.action for row in episodes)
    proposed = actions["delivered"] + actions["withheld"]
    controls = actions["withheld"]
    behavior_control_probability = 1.0 - _no_card_offer_probability(inputs.config)
    child_actions = {
        action: {
            "episodes": sum(
                row.action == action and bool(row.children) for row in episodes
            ),
            "children": sum(
                len(row.children) for row in episodes if row.action == action
            ),
            "measured_children": sum(
                len(row.measured_children) for row in episodes if row.action == action
            ),
        }
        for action in ("empty", "delivered", "withheld")
    }
    paired_ses = [
        child.paired_se
        for episode in episodes
        for child in episode.measured_children
        if child.paired_se is not None
    ]
    delivered_children = [
        child
        for episode in episodes
        if episode.action == "delivered"
        for child in episode.children
    ]
    measured_delivered = [row for row in delivered_children if row.outcome is not None]
    card_differences = {
        card_id: difference
        for card_id in sorted(
            {row.card_id for row in episodes if row.card_id is not None}
        )
        if (difference := _card_specific_difference(episodes, card_id)) is not None
    }
    strict_episode_itt = _complete_case_difference(
        episodes, strict_storage_terminal=True
    )
    evaluated_episode_itt = _complete_case_difference(
        episodes, strict_storage_terminal=False
    )
    strict_child_itt = _child_weighted_difference(
        episodes, strict_storage_terminal=True
    )
    evaluated_child_itt = _child_weighted_difference(
        episodes, strict_storage_terminal=False
    )
    identification = Counter(row["identification"] for row in prediction_rows)
    return {
        "schema_version": 1,
        "mode": "historical_shadow_conditional_offer",
        "run_dir": str(inputs.run_dir),
        "checkpoint_dir": str(inputs.checkpoint_dir),
        "training_eligible": False,
        "production_ledger_writes": 0,
        "verdict": "historical_data_inconclusive_for_policy_validation",
        "assignment_funnel": {
            "selection_decisions": len(episodes),
            "provider_empty": actions["empty"],
            "provider_proposed": proposed,
            "delivered": actions["delivered"],
            "withheld": controls,
            "realized_control_fraction_given_proposal": (
                None if not proposed else controls / proposed
            ),
            "configured_control_probability": behavior_control_probability,
            "randomization_count_two_sided_p": (
                None
                if not proposed
                else float(
                    binomtest(
                        controls,
                        proposed,
                        behavior_control_probability,
                    ).pvalue
                )
            ),
        },
        "reconstruction_integrity": {
            "selection_context_join": f"{len(episodes)}/{len(inputs.selections)}",
            "mutation_episode_join": (
                f"{sum(len(row.children) for row in episodes)}/{len(inputs.mutations)}"
            ),
            "frozen_action_consistency": (
                f"{sum(len(row.children) for row in episodes)}/{len(inputs.mutations)}"
            ),
            "outcome_completion": (
                f"{sum(len(row.measured_children) for row in episodes)}/"
                f"{len(inputs.mutations)}"
            ),
            "measured_valid": sum(
                child.invalid is False
                for episode in episodes
                for child in episode.measured_children
            ),
            "measured_total": sum(len(row.measured_children) for row in episodes),
            "v1_control_label_confusion": _confusion(inputs, episodes),
            "prefix_replay_deterministic": bool(prefix_rows),
        },
        "child_realization": child_actions,
        "causal_support": {
            "strict_episode_clusters": len(observations),
            "strict_treated_clusters": sum(row.treatment for row in observations),
            "strict_control_clusters": sum(not row.treatment for row in observations),
            "balanced_target_offer_ess": _offer_ess(observations),
            "card_identification_counts": dict(identification),
        },
        "sensitivity_estimands": {
            "strict_equal_episode_itt": strict_episode_itt,
            "evaluated_equal_episode_itt": evaluated_episode_itt,
            "strict_child_weighted_difference": strict_child_itt,
            "evaluated_child_weighted_difference": evaluated_child_itt,
            "strict_first_child_difference": _first_child_difference(episodes),
            "card_specific_evaluated_episode_differences": card_differences,
        },
        "paired_vectors": {
            "measured_with_paired_vectors": len(paired_ses),
            "minimum_se": None if not paired_ses else min(paired_ses),
            "maximum_se": None if not paired_ses else max(paired_ses),
            "pairing_signature_recoverable": False,
            "paired_posterior_is_sensitivity_only": True,
        },
        "compliance": {
            "delivered_children": len(delivered_children),
            "declared_use_children": sum(
                row.declared_use for row in delivered_children
            ),
            "measured_delivered_children": len(measured_delivered),
            "measured_declared_use_children": sum(
                row.declared_use for row in measured_delivered
            ),
            "estimand": "delivery_intention_to_treat",
            "declared_use_is_post_treatment_mediator": True,
        },
        "selection_balance": _parent_balance(inputs, episodes),
        "censoring_bounds": _censoring_bounds(inputs, episodes),
        "assumptions": [
            "conditional_on_logged_behavior_proposal",
            "fixed_offer_gate_recovered_from_resolved_hydra_config",
            "noninformative_child_realization_for_shadow_posterior_only",
            "episode_mean_is_the_primary_clustered_outcome",
            "static_semantic_bounds_proxy_unrecoverable_dynamic_map_elites_bounds",
            "logged_archive_n_is_capped_as_an_occupied_cell_coverage_proxy",
            "checkpoint_card_payloads_are_diagnostic_only",
        ],
        "unrecoverable": [
            "proposal_and_retrieval_inclusion_propensities",
            "predecision_q_hats",
            "historical_card_revision_and_bank_snapshots",
            "random_number_generator_state",
            "exact_archive_and_map_elites_state",
            "historical_prompt_and_code_fingerprints",
            "paired_cohort_signature",
        ],
        "prohibited_uses": [
            "production_posterior_training",
            "policy_safety_admission",
            "card_promotion_or_eviction",
            "full_policy_ips_snips_or_dr",
        ],
    }


def _number(value: Any, digits: int = 5) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, (float, np.floating)):
        return f"{float(value):.{digits}f}"
    return str(value)


def _plot_dashboard(
    path: Path,
    episodes: tuple[ReplayEpisode, ...],
    prediction_rows: list[dict[str, Any]],
    summary: dict[str, Any],
) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    figure.suptitle("Historical v1 replay: support and shadow posterior", fontsize=15)

    funnel = summary["assignment_funnel"]
    labels = ("Decisions", "Proposed", "Child episodes", "Strict outcomes")
    values = (
        funnel["selection_decisions"],
        funnel["provider_proposed"],
        sum(bool(row.children) for row in episodes if row.proposed),
        summary["causal_support"]["strict_episode_clusters"],
    )
    axes[0, 0].bar(labels, values, color=("#4C78A8", "#F58518", "#54A24B", "#B279A2"))
    axes[0, 0].set_title("Assignment and outcome funnel")
    axes[0, 0].set_ylabel("Episode clusters")
    axes[0, 0].tick_params(axis="x", rotation=18)
    for index, value in enumerate(values):
        axes[0, 0].text(index, value + 0.5, str(value), ha="center", va="bottom")

    proposed = [row for row in episodes if row.proposed]
    observed_y: list[float] = []
    for index, episode in enumerate(proposed):
        endpoint = _episode_outcome(episode, strict_storage_terminal=False)
        if endpoint is None:
            continue
        observed_y.append(endpoint[0])
        color = "#E45756" if episode.treatment else "#4C78A8"
        marker = "o" if episode.strict_children else "s"
        axes[0, 1].scatter(index, endpoint[0], color=color, marker=marker, s=55)
    axes[0, 1].axhline(0.0, color="#666666", linewidth=1)
    axes[0, 1].set_title("Chronological realized episode outcomes")
    axes[0, 1].set_xlabel("Proposed decision order")
    axes[0, 1].set_ylabel("Mean child fitness gain")
    if observed_y:
        floor = min(observed_y) - max(np.ptp(observed_y) * 0.12, 0.005)
        missing_x = [
            index
            for index, episode in enumerate(proposed)
            if _episode_outcome(episode, strict_storage_terminal=False) is None
        ]
        axes[0, 1].scatter(
            missing_x,
            [floor] * len(missing_x),
            marker="|",
            color="#9D9D9D",
            s=60,
            label="no realized outcome",
        )
        axes[0, 1].legend(frameon=False, loc="best")

    for index, row in enumerate(prediction_rows):
        axes[1, 0].errorbar(
            row["prior_effect_mean"],
            index + 0.13,
            xerr=1.645 * row["prior_effect_sd"],
            fmt="o",
            color="#9D9D9D",
            alpha=0.75,
        )
        axes[1, 0].errorbar(
            row["conservative_effect_mean"],
            index - 0.13,
            xerr=1.645 * row["conservative_effect_sd"],
            fmt="o",
            color="#4C78A8",
        )
    axes[1, 0].axvline(0.0, color="#666666", linewidth=1)
    axes[1, 0].set_yticks(range(len(prediction_rows)))
    axes[1, 0].set_yticklabels(
        [f"{row['card_id'][:16]}  {row['identification']}" for row in prediction_rows],
        fontsize=8,
    )
    axes[1, 0].set_title("Prior (gray) vs shadow posterior (blue), 90% interval")
    axes[1, 0].set_xlabel("Usable treatment effect")

    support = summary["causal_support"]
    axes[1, 1].axis("off")
    axes[1, 1].set_title("Identification and propensity audit", loc="left")
    audit_text = (
        f"Known offer probability: {1.0 - funnel['configured_control_probability']:.3f}\n"
        "Proposal propensity: unavailable\n"
        "Predecision q-hats: unavailable\n"
        f"Strict treated / control clusters: "
        f"{support['strict_treated_clusters']} / {support['strict_control_clusters']}\n"
        f"Balanced-target offer ESS: {support['balanced_target_offer_ess']:.2f}\n\n"
        "Permitted: shadow posterior stress test\n"
        "Prohibited: policy OPE or production training"
    )
    axes[1, 1].text(0.02, 0.92, audit_text, va="top", fontsize=12, linespacing=1.5)
    figure.savefig(path, dpi=170)
    plt.close(figure)


def _plot_integrity(
    path: Path,
    summary: dict[str, Any],
) -> None:
    figure, axes = plt.subplots(2, 2, figsize=(13, 9), constrained_layout=True)
    figure.suptitle("Historical v1 replay: integrity and sensitivity", fontsize=15)

    confusion = summary["reconstruction_integrity"]["v1_control_label_confusion"]
    matrix = np.asarray(
        [
            [confusion["true_negative"], confusion["false_positive"]],
            [confusion["false_negative"], confusion["true_positive"]],
        ]
    )
    axes[0, 0].imshow(matrix, cmap="Blues", vmin=0)
    for row in range(2):
        for column in range(2):
            axes[0, 0].text(
                column, row, str(matrix[row, column]), ha="center", va="center"
            )
    axes[0, 0].set_xticks((0, 1), labels=("Stored non-control", "Stored control"))
    axes[0, 0].set_yticks(
        (0, 1), labels=("Reconstructed non-control", "Reconstructed control")
    )
    axes[0, 0].set_title("Mutable v1 control-label confusion")

    sensitivity = summary["sensitivity_estimands"]
    sensitivity_keys = (
        "strict_equal_episode_itt",
        "evaluated_equal_episode_itt",
        "strict_child_weighted_difference",
        "evaluated_child_weighted_difference",
        "strict_first_child_difference",
    )
    sensitivity_labels = (
        "Strict episode",
        "Evaluated episode",
        "Strict child-weighted",
        "Evaluated child-weighted",
        "First child",
    )
    sensitivity_values = [sensitivity[key] for key in sensitivity_keys]
    valid = [
        index for index, value in enumerate(sensitivity_values) if value is not None
    ]
    axes[0, 1].barh(
        [sensitivity_labels[index] for index in valid],
        [sensitivity_values[index] for index in valid],
        color=("#4C78A8", "#72B7B2", "#F58518", "#ECA82C", "#B279A2")[: len(valid)],
    )
    axes[0, 1].axvline(0.0, color="#666666", linewidth=1)
    axes[0, 1].set_title("Complete-case estimands change with aggregation")
    axes[0, 1].set_xlabel("Delivered minus withheld gain")

    compliance = summary["compliance"]
    compliance_labels = (
        "Delivered children",
        "Declared use",
        "Measured delivered",
        "Measured + declared use",
    )
    compliance_values = (
        compliance["delivered_children"],
        compliance["declared_use_children"],
        compliance["measured_delivered_children"],
        compliance["measured_declared_use_children"],
    )
    axes[1, 0].bar(
        compliance_labels,
        compliance_values,
        color=("#E45756", "#54A24B", "#4C78A8", "#B279A2"),
    )
    axes[1, 0].tick_params(axis="x", rotation=18)
    axes[1, 0].set_title("Delivery and post-treatment declared use")
    axes[1, 0].set_ylabel("Children")

    realization = summary["child_realization"]
    arm_labels = ("Natural empty", "Delivered", "Withheld")
    arm_keys = ("empty", "delivered", "withheld")
    episode_values = [realization[key]["episodes"] for key in arm_keys]
    child_values = [realization[key]["children"] for key in arm_keys]
    measured_values = [realization[key]["measured_children"] for key in arm_keys]
    x = np.arange(3)
    width = 0.24
    axes[1, 1].bar(
        x - width, episode_values, width, label="Child episodes", color="#4C78A8"
    )
    axes[1, 1].bar(x, child_values, width, label="Children", color="#F58518")
    axes[1, 1].bar(x + width, measured_values, width, label="Measured", color="#54A24B")
    axes[1, 1].set_xticks(x, labels=arm_labels)
    axes[1, 1].set_title("Post-assignment child realization and measurement")
    axes[1, 1].legend(frameon=False)
    figure.savefig(path, dpi=170)
    plt.close(figure)


def _plot_prefix(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    figure, axes = plt.subplots(
        2, 1, figsize=(11, 8), sharex=True, constrained_layout=True
    )
    x = np.asarray([row["evidence_count"] for row in rows])
    mean = np.asarray([row["effect_mean"] for row in rows])
    sd = np.asarray([row["effect_sd"] for row in rows])
    axes[0].plot(x, mean, color="#4C78A8", marker="o", label="Posterior mean")
    axes[0].fill_between(
        x,
        mean - 1.645 * sd,
        mean + 1.645 * sd,
        color="#4C78A8",
        alpha=0.18,
        label="90% interval",
    )
    axes[0].axhline(0.0, color="#666666", linewidth=1)
    axes[0].set_ylabel("Usable treatment effect")
    axes[0].set_title("Chronological shadow-posterior prefix replay")
    axes[0].legend(frameon=False)
    axes[1].plot(
        x,
        [row["probability_helpful"] for row in rows],
        marker="o",
        color="#54A24B",
        label="P(helpful)",
    )
    axes[1].plot(
        x,
        [row["probability_safe"] for row in rows],
        marker="s",
        color="#E45756",
        label="P(safe)",
    )
    axes[1].set_ylim(-0.02, 1.02)
    axes[1].set_xlabel("Strict episode clusters observed")
    axes[1].set_ylabel("Probability")
    axes[1].legend(frameon=False)
    figure.savefig(path, dpi=170)
    plt.close(figure)


def _plot_counterfactual(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    x = [row["target_offer_probability"] for row in rows]
    figure, axes = plt.subplots(
        2, 1, figsize=(10, 8), sharex=True, constrained_layout=True
    )
    axes[0].plot(
        x,
        [row["dr_reward"] for row in rows],
        marker="o",
        color="#4C78A8",
        label="Exploratory DR reward",
    )
    axes[0].axhline(0.0, color="#666666", linewidth=1)
    axes[0].set_ylabel("Estimated utility")
    axes[0].set_title("Conditional-offer counterfactual sensitivity (not policy OPE)")
    risk_axis = axes[0].twinx()
    risk_axis.plot(
        x,
        [row["dr_invalid_probability"] for row in rows],
        marker="s",
        color="#E45756",
        label="Exploratory DR invalidity",
    )
    risk_axis.set_ylabel("Estimated invalidity")
    axes[1].plot(
        x, [row["importance_ess"] for row in rows], marker="o", color="#54A24B"
    )
    axes[1].set_xlabel("Target delivery probability given logged proposal")
    axes[1].set_ylabel("Offer-only ESS")
    axes[1].set_title("Support collapses near deterministic target policies")
    figure.savefig(path, dpi=170)
    plt.close(figure)


def _render_report(
    summary: dict[str, Any], prediction_rows: list[dict[str, Any]]
) -> str:
    funnel = summary["assignment_funnel"]
    support = summary["causal_support"]
    integrity = summary["reconstruction_integrity"]
    confusion = integrity["v1_control_label_confusion"]
    sensitivity = summary["sensitivity_estimands"]
    balance = summary["selection_balance"]
    censoring = summary["censoring_bounds"]
    lines = [
        "# Historical v1 shadow replay",
        "",
        "## Verdict",
        "",
        "The run is useful for reconstruction-integrity and posterior numerical stress testing. It is **not causally sufficient for policy validation** and no reconstructed row is eligible for production training.",
        "",
        "## Assignment reconstruction",
        "",
        f"- Decisions: {funnel['selection_decisions']}; provider proposals: {funnel['provider_proposed']}; delivered: {funnel['delivered']}; withheld: {funnel['withheld']}.",
        f"- Exact joins: selection/context {integrity['selection_context_join']}; mutation/episode {integrity['mutation_episode_join']}; completed outcomes {integrity['outcome_completion']}.",
        f"- Configured control probability: {_number(funnel['configured_control_probability'], 3)}; realized fraction: {_number(funnel['realized_control_fraction_given_proposal'], 3)}; binomial count check p={_number(funnel['randomization_count_two_sided_p'], 3)}.",
        f"- Mutable v1 control labels: TP={confusion['true_positive']}, FP={confusion['false_positive']}, FN={confusion['false_negative']}, TN={confusion['true_negative']}.",
        "",
        "The old control field was mutable and relabeled birth assignments after descendants ran their own memory stage. Assignment is therefore reconstructed from the immutable selection event plus the next matching ContextStage result.",
        "",
        "## Causal support",
        "",
        f"- Strict observed episode clusters: {support['strict_episode_clusters']} ({support['strict_treated_clusters']} delivered, {support['strict_control_clusters']} withheld).",
        f"- Balanced-target offer-only ESS: {_number(support['balanced_target_offer_ess'], 2)}.",
        f"- Equal-episode strict ITT: {_number(sensitivity['strict_equal_episode_itt'])}; evaluated-running sensitivity: {_number(sensitivity['evaluated_equal_episode_itt'])}.",
        f"- Child-weighted strict/evaluated differences: {_number(sensitivity['strict_child_weighted_difference'])} / {_number(sensitivity['evaluated_child_weighted_difference'])}.",
        f"- Parent-fitness SMD, child-bearing proposals vs unrealized proposals: {_number(balance['standardized_mean_difference'], 3)}; vs child-bearing provider-empty decisions: {_number(balance['child_bearing_proposed_vs_empty_smd'], 3)}.",
        f"- Worst-case decision-level ITT bounds under missing realization: [{_number(censoring['worst_case_itt_lower'], 3)}, {_number(censoring['worst_case_itt_upper'], 3)}].",
        "",
        "These estimands change sign or magnitude with reasonable aggregation choices, and outcome realization is post-randomization. Full IPS/SNIPS/DR is unidentified because proposal propensities and frozen q-hats are absent.",
        "",
        "## Shadow posterior",
        "",
        "| Card | Arms (T/C) | Identification | Effect mean | Effect SD | P(helpful) | P(safe) |",
        "|---|---:|---|---:|---:|---:|---:|",
    ]
    for row in prediction_rows:
        lines.append(
            f"| `{row['card_id']}` | {row['treated_episodes']}/{row['control_episodes']} | {row['identification']} | "
            f"{_number(row['conservative_effect_mean'])} | {_number(row['conservative_effect_sd'])} | "
            f"{_number(row['conservative_probability_helpful'], 3)} | {_number(row['conservative_probability_safe'], 3)} |"
        )
    lines.extend(
        [
            "",
            "Posterior rows use placeholder historical treatment identities. Current checkpoint card text is never used as historical training data. Paired-vector posteriors are sensitivity analyses because the cohort pairing signature cannot be recovered.",
            "",
            "## Scope",
            "",
            "Permitted: parser integrity checks, prefix replay, numerical posterior stress tests, and qualitative prior-sensitivity review.",
            "",
            "Prohibited: production posterior updates, safety-set admission, card promotion/eviction, or claims about an improved target policy.",
            "",
        ]
    )
    return "\n".join(lines)


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def replay_run(
    run_dir: Path,
    output_dir: Path,
    *,
    posterior_samples: int,
) -> dict[str, Any]:
    inputs = load_run(run_dir)
    episodes = reconstruct_episodes(inputs)
    prediction_rows, observations, model, fitted = _prediction_rows(
        inputs,
        episodes,
        posterior_samples=posterior_samples,
    )
    counterfactual_rows = _counterfactual_rows(
        observations,
        fitted,
        posterior_samples=posterior_samples,
    )
    prefix_rows = _prefix_rows(
        observations,
        model,
        posterior_samples=posterior_samples,
    )
    prior_rows = _prior_sensitivity(
        observations,
        posterior_samples=posterior_samples,
    )
    summary = _summary(
        inputs,
        episodes,
        observations,
        prediction_rows,
        prefix_rows,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "episodes.csv", _episode_rows(episodes))
    _write_csv(output_dir / "posterior.csv", prediction_rows)
    _write_csv(output_dir / "counterfactual.csv", counterfactual_rows)
    _write_csv(output_dir / "prefix_replay.csv", prefix_rows)
    _write_csv(output_dir / "prior_sensitivity.csv", prior_rows)
    _plot_dashboard(
        output_dir / "replay_dashboard.png", episodes, prediction_rows, summary
    )
    _plot_integrity(output_dir / "integrity_sensitivity.png", summary)
    _plot_prefix(output_dir / "prefix_posterior.png", prefix_rows)
    _plot_counterfactual(output_dir / "counterfactual_support.png", counterfactual_rows)
    summary["artifacts"] = {
        "report": "report.md",
        "episodes": "episodes.csv",
        "posterior": "posterior.csv",
        "counterfactual": "counterfactual.csv",
        "prefix_replay": "prefix_replay.csv",
        "prior_sensitivity": "prior_sensitivity.csv",
        "dashboard": "replay_dashboard.png",
        "integrity": "integrity_sensitivity.png",
        "prefix_plot": "prefix_posterior.png",
        "counterfactual_plot": "counterfactual_support.png",
    }
    _write_json(output_dir / "summary.json", summary)
    (output_dir / "report.md").write_text(
        _render_report(summary, prediction_rows), encoding="utf-8"
    )
    return summary


def _slug(run_dir: Path) -> str:
    value = f"{run_dir.parent.name}_{run_dir.name}"
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value)


def _comparison_rows(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for summary in summaries:
        funnel = summary["assignment_funnel"]
        support = summary["causal_support"]
        integrity = summary["reconstruction_integrity"]
        sensitivity = summary["sensitivity_estimands"]
        confusion = integrity["v1_control_label_confusion"]
        censoring = summary["censoring_bounds"]
        result.append(
            {
                "run": Path(summary["run_dir"]).parent.name,
                "decisions": funnel["selection_decisions"],
                "proposals": funnel["provider_proposed"],
                "delivered": funnel["delivered"],
                "withheld": funnel["withheld"],
                "strict_episode_clusters": support["strict_episode_clusters"],
                "strict_treated_clusters": support["strict_treated_clusters"],
                "strict_control_clusters": support["strict_control_clusters"],
                "offer_only_ess": support["balanced_target_offer_ess"],
                "strict_equal_episode_itt": sensitivity["strict_equal_episode_itt"],
                "evaluated_equal_episode_itt": sensitivity[
                    "evaluated_equal_episode_itt"
                ],
                "evaluated_child_weighted_difference": sensitivity[
                    "evaluated_child_weighted_difference"
                ],
                "worst_case_itt_lower": censoring["worst_case_itt_lower"],
                "worst_case_itt_upper": censoring["worst_case_itt_upper"],
                "stored_control_false_positive": confusion["false_positive"],
                "stored_control_false_negative": confusion["false_negative"],
                "verdict": summary["verdict"],
            }
        )
    return result


def _plot_comparison(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    labels = [row["run"].replace("hover-diff-memory-", "") for row in rows]
    x = np.arange(len(rows))
    figure, axes = plt.subplots(2, 2, figsize=(14, 9), constrained_layout=True)
    figure.suptitle("Historical memory runs: causal support comparison", fontsize=15)

    width = 0.25
    axes[0, 0].bar(
        x - width,
        [row["proposals"] for row in rows],
        width,
        color="#F58518",
        label="Proposals",
    )
    axes[0, 0].bar(
        x,
        [row["strict_episode_clusters"] for row in rows],
        width,
        color="#54A24B",
        label="Strict outcomes",
    )
    axes[0, 0].bar(
        x + width,
        [row["strict_control_clusters"] for row in rows],
        width,
        color="#4C78A8",
        label="Strict controls",
    )
    axes[0, 0].set_xticks(x, labels=labels, rotation=15)
    axes[0, 0].set_ylabel("Episode clusters")
    axes[0, 0].set_title("Assignment funnel and identified controls")
    axes[0, 0].legend(frameon=False)

    axes[0, 1].bar(
        x - width / 2,
        [row["strict_equal_episode_itt"] for row in rows],
        width,
        color="#4C78A8",
        label="Strict episode ITT",
    )
    axes[0, 1].bar(
        x + width / 2,
        [row["evaluated_child_weighted_difference"] for row in rows],
        width,
        color="#F58518",
        label="Evaluated child-weighted",
    )
    axes[0, 1].axhline(0.0, color="#666666", linewidth=1)
    axes[0, 1].set_xticks(x, labels=labels, rotation=15)
    axes[0, 1].set_ylabel("Delivered minus withheld gain")
    axes[0, 1].set_title("Complete-case results depend on aggregation")
    axes[0, 1].legend(frameon=False)

    lower = np.asarray([row["worst_case_itt_lower"] for row in rows], dtype=float)
    upper = np.asarray([row["worst_case_itt_upper"] for row in rows], dtype=float)
    center = 0.5 * (lower + upper)
    axes[1, 0].errorbar(
        x,
        center,
        yerr=np.stack((center - lower, upper - center)),
        fmt="o",
        color="#B279A2",
        capsize=5,
    )
    axes[1, 0].axhline(0.0, color="#666666", linewidth=1)
    axes[1, 0].set_xticks(x, labels=labels, rotation=15)
    axes[1, 0].set_ylabel("Decision-level ITT")
    axes[1, 0].set_title("Worst-case bounds under missing child realization")

    axes[1, 1].bar(
        x - width / 2,
        [row["stored_control_false_positive"] for row in rows],
        width,
        color="#E45756",
        label="False controls",
    )
    axes[1, 1].bar(
        x + width / 2,
        [row["stored_control_false_negative"] for row in rows],
        width,
        color="#72B7B2",
        label="Missed controls",
    )
    axes[1, 1].set_xticks(x, labels=labels, rotation=15)
    axes[1, 1].set_ylabel("Children")
    axes[1, 1].set_title("Mutable v1 control-label corruption is systemic")
    axes[1, 1].legend(frameon=False)
    figure.savefig(path, dpi=170)
    plt.close(figure)


def _render_comparison_report(rows: list[dict[str, Any]]) -> str:
    lines = [
        "# Historical memory-run comparison",
        "",
        "All rows are shadow-only reconstructions and are ineligible for production training.",
        "",
        "| Run | Proposals | Strict T/C | Offer ESS | Strict episode ITT | Evaluated child-weighted | Worst-case bounds | FP/FN controls |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['run']} | {row['proposals']} | "
            f"{row['strict_treated_clusters']}/{row['strict_control_clusters']} | "
            f"{_number(row['offer_only_ess'], 2)} | "
            f"{_number(row['strict_equal_episode_itt'])} | "
            f"{_number(row['evaluated_child_weighted_difference'])} | "
            f"[{_number(row['worst_case_itt_lower'], 3)}, {_number(row['worst_case_itt_upper'], 3)}] | "
            f"{row['stored_control_false_positive']}/{row['stored_control_false_negative']} |"
        )
    lines.extend(
        [
            "",
            "The immutable reconstruction finds control-label errors in every run. Complete-case estimates vary across runs and aggregation choices, while decision-level censoring bounds remain wide because assignment precedes child realization. The historical evidence therefore stress-tests posterior numerics but does not identify a superior memory policy.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Shadow-replay historical v1 memory assignments through memory v2"
    )
    parser.add_argument("--run-dir", type=Path, action="append", required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "outputs" / "memory_v2_historical_replay",
    )
    parser.add_argument("--posterior-samples", type=int, default=512)
    arguments = parser.parse_args()
    if arguments.posterior_samples < 128:
        parser.error("--posterior-samples must be at least 128")
    root = arguments.output_dir.resolve()
    full_summaries: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for run_dir in arguments.run_dir:
        resolved = run_dir.resolve()
        summary = replay_run(
            resolved,
            root / _slug(resolved),
            posterior_samples=arguments.posterior_samples,
        )
        full_summaries.append(summary)
        summaries.append(
            {
                "run_dir": summary["run_dir"],
                "verdict": summary["verdict"],
                "output_dir": str(root / _slug(resolved)),
            }
        )
    index = {
        "schema_version": 1,
        "training_eligible": False,
        "runs": summaries,
    }
    root.mkdir(parents=True, exist_ok=True)
    comparison_rows = _comparison_rows(full_summaries)
    _write_csv(root / "comparison.csv", comparison_rows)
    _plot_comparison(root / "historical_comparison.png", comparison_rows)
    (root / "report.md").write_text(
        _render_comparison_report(comparison_rows), encoding="utf-8"
    )
    _write_json(root / "index.json", index)
    print(json.dumps(index, indent=2))


if __name__ == "__main__":
    main()
