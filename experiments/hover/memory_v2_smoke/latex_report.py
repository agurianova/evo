#!/usr/bin/env python3
"""Build a publication-style Bayesian audit for one memory-v2 run.

The live endpoint and the longer lineage endpoint are deliberately reported
separately. The latter is reconstructed as a shadow analysis and never changes
the behavior policy that generated the ledger.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
from typing import Any
import unicodedata

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.hover.memory_v2_smoke.analyze import (  # noqa: E402
    Audit,
    LedgerRow,
    audit_rows,
    canonical_treatment_ids,
    causal_observations,
    evaluate_ope,
    evidence_lifecycle,
    flatten,
    invalid_penalty_sensitivity,
    lineage_evidence,
    load_ledger,
    shadow_lineage_evidence,
)
from gigaevo.memory.cards import Card  # noqa: E402
from gigaevo.memory.write.admission import WriteLedgerRecord  # noqa: E402
from gigaevo.memory_v2.candidates import (  # noqa: E402
    AgenticApplicabilityProvider,
    NullApplicabilityProvider,
    WholeBankCandidateSource,
)
from gigaevo.memory_v2.features import (  # noqa: E402
    FeatureConfig,
    HierarchicalFeatureMap,
)
from gigaevo.memory_v2.models import (  # noqa: E402
    CardSnapshot,
    CausalObservation,
    EvolutionContext,
    LineageOutcome,
    PolicySpecification,
    qualified_class_name,
)
from gigaevo.memory_v2.ope import ConditionalOfferDREvaluator  # noqa: E402
from gigaevo.memory_v2.posterior import (  # noqa: E402
    FittedTerminalUtilityPosterior,
    HierarchicalTerminalUtilityPosterior,
    TerminalUtilityPosteriorConfig,
)

INK = "#18212b"
MUTED = "#667281"
BLUE = "#2765a8"
TEAL = "#16847a"
GREEN = "#3b7d44"
ORANGE = "#d66b36"
RED = "#b64343"
PURPLE = "#74569b"
GOLD = "#b88621"
GRID = "#d9dee5"
LIGHT = "#f3f5f7"
COLORS = (BLUE, TEAL, ORANGE, PURPLE, GREEN, GOLD, RED)
WRITER_LLM_STAGES = frozenset(
    {"ConsolidateAgent", "ProgramAuthorAgent", "ReconcileAgent", "TaskSummaryAgent"}
)
MAX_TRAILING_SAFETY_LOCKOUT_DECISIONS = 24


@dataclass(frozen=True)
class ReportPaths:
    output_dir: Path
    figure_dir: Path
    table_dir: Path
    tex_path: Path
    pdf_path: Path


@dataclass
class ReportData:
    ledger: Path
    run_root: Path
    rows: list[LedgerRow]
    integrity: str
    audit: Audit
    decisions: list[dict[str, Any]]
    candidate_rows: list[dict[str, Any]]
    terminal_rows: list[dict[str, Any]]
    immediate: tuple[CausalObservation, ...]
    active_outcomes: tuple[LineageOutcome, ...]
    active_rewards: tuple[CausalObservation, ...]
    shadow_immediate: tuple[CausalObservation, ...]
    shadow_outcomes: tuple[LineageOutcome, ...]
    shadow_rewards: tuple[CausalObservation, ...]
    lifecycle: list[dict[str, Any]]
    cards: tuple[CardSnapshot, ...]
    card_descriptions: dict[str, str]
    write_rows: list[dict[str, Any]]
    config: dict[str, Any]
    posterior_model: HierarchicalTerminalUtilityPosterior
    active_fit: FittedTerminalUtilityPosterior
    shadow_fit: FittedTerminalUtilityPosterior | None
    active_ope: list[dict[str, Any]]
    active_ope_error: str | None
    shadow_ope: list[dict[str, Any]]
    overlap: dict[str, Any]
    bootstrap: pd.DataFrame
    final_posterior: pd.DataFrame
    shadow_final_posterior: pd.DataFrame
    writer_trace: pd.DataFrame
    llm_calls: pd.DataFrame
    shadow_depth: int
    shadow_budget: int


def _ascii(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value))
    return text.encode("ascii", "ignore").decode("ascii")


def _tex(value: Any) -> str:
    text = _ascii(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def _short(card_id: str, length: int = 13) -> str:
    return card_id.replace("program-", "prog-")[:length]


def _finite(value: Any, default: float = math.nan) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _quantile(
    values: Sequence[float], probability: float, default: float = 0.0
) -> float:
    finite = np.asarray(
        [value for value in values if math.isfinite(value)], dtype=float
    )
    return float(np.quantile(finite, probability)) if finite.size else default


def _configure_matplotlib() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": GRID,
            "axes.labelcolor": INK,
            "axes.titlecolor": INK,
            "axes.titlesize": 12,
            "axes.titleweight": "bold",
            "axes.grid": True,
            "grid.color": GRID,
            "grid.linewidth": 0.65,
            "grid.alpha": 0.75,
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "legend.frameon": False,
            "xtick.color": MUTED,
            "ytick.color": MUTED,
            "savefig.facecolor": "white",
            "savefig.bbox": "tight",
        }
    )


def _figure(title: str, subtitle: str, *, size: tuple[float, float] = (12.4, 7.2)):
    fig = plt.figure(figsize=size, constrained_layout=False)
    fig.text(0.055, 0.965, title, fontsize=18, weight="bold", color=INK, va="top")
    fig.text(0.055, 0.925, subtitle, fontsize=9.5, color=MUTED, va="top")
    return fig


def _save_figure(fig: plt.Figure, paths: ReportPaths, name: str) -> None:
    paths.figure_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(paths.figure_dir / f"{name}.pdf", dpi=220)
    fig.savefig(paths.figure_dir / f"{name}.png", dpi=180)
    plt.close(fig)


def _load_yaml_config(run_root: Path) -> dict[str, Any]:
    path = _config_path(run_root)
    if not path.is_file():
        return {}
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else {}


def _first_existing(*paths: Path) -> Path:
    for path in paths:
        if path.is_file():
            return path
    return paths[0]


def _config_path(run_root: Path) -> Path:
    return _first_existing(
        run_root / "resolved_config.yaml",
        run_root / ".hydra" / "config.yaml",
    )


def _cards_path(run_root: Path) -> Path:
    return _first_existing(
        run_root / "memory" / "cards.json",
        run_root / "checkpoints" / "cards.json",
    )


def _write_ledger_path(run_root: Path) -> Path:
    return _first_existing(
        run_root / "memory" / "write_ledger.jsonl",
        run_root / "checkpoints" / "write_ledger.jsonl",
    )


def _audit_input_paths(run_root: Path, ledger: Path) -> tuple[Path, ...]:
    return (
        ledger,
        _config_path(run_root),
        _cards_path(run_root),
        _write_ledger_path(run_root),
    )


def _run_logs(run_root: Path) -> tuple[Path, ...]:
    """Return every execution segment for a run, in chronological order."""
    candidates = [run_root / "run.log", *run_root.glob("evolution_*.log")]
    unique: dict[tuple[int, int], Path] = {}
    for path in candidates:
        if not path.is_file():
            continue
        stat = path.stat()
        unique.setdefault((stat.st_dev, stat.st_ino), path)
    return tuple(
        sorted(unique.values(), key=lambda path: (path.stat().st_mtime, path.name))
    )


def _load_write_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    result = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if line.strip():
            try:
                row = WriteLedgerRecord.model_validate_json(line)
            except ValueError as exc:
                raise ValueError(
                    f"invalid write-ledger row {path}:{line_number}"
                ) from exc
            result.append(row.model_dump(mode="json"))
    return result


def _load_llm_calls(path: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return pd.DataFrame()
    for line in path.open(encoding="utf-8", errors="replace"):
        if "[LLM_CALL]" not in line:
            continue
        try:
            payload = json.loads(line[line.index("{") :])
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"malformed LLM_CALL in {path}:{line!r}") from exc
        tokens_in = int(payload.get("tokens_in") or 0)
        tokens_out = int(payload.get("tokens_out") or 0)
        tokens_reasoning = int(payload.get("tokens_reasoning") or 0)
        stage = str(payload.get("stage") or "unknown")
        writer_call = stage in WRITER_LLM_STAGES
        call_category = (
            "writer"
            if writer_call
            else "retrieval"
            if stage.startswith("Retrieval")
            else "mutation"
        )
        rows.append(
            {
                "stage": stage,
                "model": str(payload.get("model") or ""),
                "ok": bool(payload.get("ok", False)),
                "latency_seconds": float(payload.get("latency_ms") or 0.0) / 1000.0,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "tokens_reasoning": tokens_reasoning,
                # Provider usage reports reasoning as a subset of completion tokens.
                "total_tokens": tokens_in + tokens_out,
                "writer_call": writer_call,
                "call_category": call_category,
            }
        )
    return pd.DataFrame(rows)


def _load_run_llm_calls(run_root: Path) -> pd.DataFrame:
    """Load LLM accounting across checkpoint-resumed execution logs."""
    frames = []
    for path in _run_logs(run_root):
        frame = _load_llm_calls(path)
        if frame.empty:
            continue
        frame.insert(0, "log_segment", path.name)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _llm_resource_summary(calls: pd.DataFrame) -> pd.DataFrame:
    if calls.empty:
        return pd.DataFrame()
    frame = calls.copy()
    if "call_category" not in frame:
        frame["call_category"] = np.where(
            frame["writer_call"],
            "writer",
            np.where(
                frame["stage"].str.startswith("Retrieval"), "retrieval", "mutation"
            ),
        )
    frame["failure"] = ~frame["ok"].astype(bool)
    return (
        frame.groupby(["stage", "writer_call", "call_category"], as_index=False)
        .agg(
            calls=("stage", "size"),
            total_tokens=("total_tokens", "sum"),
            provider_latency_seconds=("latency_seconds", "sum"),
            failures=("failure", "sum"),
        )
        .sort_values("total_tokens", ascending=False)
    )


def _load_cards(
    path: Path, rows: list[LedgerRow]
) -> tuple[tuple[CardSnapshot, ...], dict[str, str]]:
    cards: list[CardSnapshot] = []
    descriptions: dict[str, str] = {}
    if not path.is_file():
        raise FileNotFoundError(path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("cards"), dict):
        raise ValueError(f"invalid card-bank document: {path}")
    for stored_id, value in raw["cards"].items():
        try:
            card = Card.model_validate(value)
            snapshot = CardSnapshot.from_card(card)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid card {stored_id!r} in {path}") from exc
        if card.id != stored_id:
            raise ValueError(f"card key/id mismatch for {stored_id!r} in {path}")
        cards.append(snapshot)
        descriptions[snapshot.treatment_id] = snapshot.payload.strip()
    for row in rows:
        for card in row.decision.lineage_registry:
            descriptions.setdefault(card.treatment_id, card.payload.strip())
    unique = {card.treatment_id: card for card in cards}
    return tuple(
        sorted(unique.values(), key=lambda row: row.treatment_id)
    ), descriptions


def _memory_config(config: dict[str, Any]) -> dict[str, Any]:
    memory = config.get("memory")
    if not isinstance(memory, dict):
        raise ValueError("resolved config omits memory")
    return memory


def _expected_policy_specification(config: dict[str, Any]) -> PolicySpecification:
    memory = _memory_config(config)
    policy = memory.get("policy_config")
    safety = memory.get("safety")
    if not isinstance(policy, dict) or not isinstance(safety, dict):
        raise ValueError("resolved config omits memory policy or safety settings")
    return PolicySpecification(
        safety_gate_mode=safety["gate_mode"],
        max_treated_invalid_probability=safety.get("max_treated_invalid_probability"),
        max_incremental_invalid_probability=safety[
            "max_incremental_invalid_probability"
        ],
        safety_alpha=safety["alpha"],
        offer_probability=policy["offer_probability"],
        proposal_exploration_probability=policy["proposal_exploration_probability"],
        posterior_summary_samples=policy["posterior_summary_samples"],
        proposal_worlds=policy["proposal_worlds"],
        abstain_effect=policy["abstain_effect"],
        max_pending_per_card=policy["max_pending_per_card"],
    )


def _expected_applicability_name(config: dict[str, Any]) -> str:
    memory = _memory_config(config)
    candidate = memory.get("candidate_source")
    if not isinstance(candidate, dict):
        raise ValueError("resolved config omits memory candidate_source")
    target = candidate.get("_target_")
    if target != qualified_class_name(WholeBankCandidateSource):
        raise ValueError(f"unsupported memory-v2 candidate source: {target!r}")
    applicability = memory.get("applicability")
    if not isinstance(applicability, dict):
        raise ValueError("resolved config omits memory applicability")
    applicability_target = applicability.get("_target_")
    if applicability_target == qualified_class_name(AgenticApplicabilityProvider):
        return "agentic_research"
    if applicability_target == qualified_class_name(NullApplicabilityProvider):
        return "none"
    raise ValueError(f"unsupported memory-v2 applicability: {applicability_target!r}")


def _ledger_config_contract(
    config: dict[str, Any], rows: list[LedgerRow]
) -> dict[str, bool]:
    if not rows:
        return {
            "policy": False,
            "candidate_universe": False,
            "applicability": False,
            "run_seed": False,
        }
    expected_policy = _expected_policy_specification(config)
    expected_applicability = _expected_applicability_name(config)
    memory = _memory_config(config)
    expected_seed = int(memory["run_seed"])
    return {
        "policy": {row.decision.policy.digest for row in rows}
        == {expected_policy.digest},
        "candidate_universe": {
            row.decision.candidate_universe.specification.name for row in rows
        }
        == {"eligible_bank"},
        "applicability": {row.decision.applicability.specification.name for row in rows}
        == {expected_applicability},
        "run_seed": {row.decision.run_seed for row in rows} == {expected_seed},
    }


def _model_from_config(
    config: dict[str, Any], rows: list[LedgerRow]
) -> HierarchicalTerminalUtilityPosterior:
    memory = config.get("memory", {}) if isinstance(config, dict) else {}
    feature_raw = memory.get("feature_config", {}) if isinstance(memory, dict) else {}
    observed_keys = tuple(
        coordinate.key
        for coordinate in rows[-1].decision.context.map_elites.coordinates
    )
    feature_config = FeatureConfig(
        # ``--cfg job`` preserves custom ``ref:`` expressions as strings. The
        # ledger contains the resolved, ordered BehaviorDimension coordinates
        # that the live posterior actually consumed.
        behavior_keys=observed_keys,
        progress_log_scale=float(feature_raw.get("progress_log_scale", 100.0)),
        card_kind_contrast=bool(feature_raw.get("card_kind_contrast", False)),
        retrieval_applicability_contrast=bool(
            feature_raw.get("retrieval_applicability_contrast", False)
        ),
    )
    posterior_raw = (
        memory.get("posterior_config", {}) if isinstance(memory, dict) else {}
    )
    allowed = set(TerminalUtilityPosteriorConfig.model_fields)
    posterior_config = TerminalUtilityPosteriorConfig(
        **{key: value for key, value in posterior_raw.items() if key in allowed}
    )
    return HierarchicalTerminalUtilityPosterior(
        feature_map=HierarchicalFeatureMap(config=feature_config),
        config=posterior_config,
    )


def _writer_lifecycle(
    write_rows: list[dict[str, Any]], final_ids: set[str]
) -> pd.DataFrame:
    active: set[str] = set()
    counters: Counter[str] = Counter()
    result: list[dict[str, Any]] = []
    for index, row in enumerate(write_rows, 1):
        outcome = str(row.get("outcome", "unknown"))
        incoming = str(row.get("incoming_id", ""))
        final = str(row.get("final_id", ""))
        duplicate = str(row.get("duplicate_of", ""))
        if outcome in {"added", "updated"} and final:
            active.add(final)
        elif outcome == "merged":
            if incoming and incoming != final:
                active.discard(incoming)
            if duplicate and duplicate != final:
                active.discard(duplicate)
            if final:
                active.add(final)
        elif outcome in {"evicted", "retired", "rejected"} and incoming:
            active.discard(incoming)
        counters[outcome] += 1
        result.append(
            {
                "write_index": index,
                "timestamp_utc": row.get("timestamp_utc", ""),
                "outcome": outcome,
                "reconstructed_bank_size": len(active),
                "added": counters["added"],
                "merged": counters["merged"],
                "rejected": counters["rejected"],
                "evicted": counters["evicted"] + counters["retired"],
            }
        )
    frame = pd.DataFrame(result)
    if not frame.empty:
        frame.attrs["matches_final_bank"] = active == final_ids
    return frame


def _posterior_thresholds(
    rows: list[LedgerRow],
) -> tuple[float | None, float, float]:
    policy = rows[-1].decision.policy
    return (
        policy.max_treated_invalid_probability,
        policy.max_incremental_invalid_probability,
        policy.safety_alpha,
    )


def _fit_final_table(
    fitted: FittedTerminalUtilityPosterior | None,
    cards: tuple[CardSnapshot, ...],
    context: EvolutionContext | None,
    thresholds: tuple[float | None, float, float],
    *,
    seed: int,
) -> pd.DataFrame:
    if fitted is None or not cards or context is None:
        return pd.DataFrame()
    predictions = fitted.predictions(
        cards,
        context,
        np.random.default_rng(seed),
        samples=8192,
        max_treated_invalid_probability=thresholds[0],
        max_incremental_invalid_probability=thresholds[1],
        safety_alpha=thresholds[2],
    )
    result = []
    for card in cards:
        row = predictions[card.treatment_id]
        result.append(
            {
                "treatment_id": card.treatment_id,
                "effect_mean": row.usable_effect_mean,
                "effect_sd": row.usable_effect_sd,
                "effect_lower_normal": row.usable_effect_mean
                - 1.96 * row.usable_effect_sd,
                "effect_upper_normal": row.usable_effect_mean
                + 1.96 * row.usable_effect_sd,
                "probability_helpful": row.probability_helpful,
                "probability_safe": row.probability_safe,
                "probability_safe_and_helpful": row.probability_safe_and_helpful,
                "control_gain": row.usable_gain_control_mean,
                "treated_gain": row.usable_gain_treated_mean,
                "control_invalid": row.control_invalid_probability,
                "treated_invalid": row.treated_invalid_probability,
                "incremental_invalid": row.incremental_invalid_probability,
                "treated_invalid_upper": row.treated_invalid_upper,
                "incremental_invalid_upper": row.incremental_invalid_upper,
                "predictive_sd": row.usable_gain_predictive_sd,
            }
        )
    return pd.DataFrame(result).sort_values(
        ["probability_safe_and_helpful", "effect_mean"], ascending=False
    )


def _lineage_descendants(
    rows: list[LedgerRow], outcomes: tuple[LineageOutcome, ...]
) -> dict[str, set[str]]:
    decisions = {row.decision.decision_id: row.decision for row in rows}
    terminals = {
        row.decision.decision_id: row.terminal
        for row in rows
        if row.terminal is not None
    }
    children: dict[str, list[Any]] = defaultdict(list)
    for row in rows:
        terminal = row.terminal
        if terminal is not None:
            children[row.decision.context.parent_id].append((row.decision, terminal))
    result: dict[str, set[str]] = {}
    for outcome in outcomes:
        if outcome.status not in {"outcome", "invalid"}:
            continue
        root = decisions[outcome.decision_id]
        terminal = terminals.get(outcome.decision_id)
        if terminal is None:
            continue
        if terminal.status == "invalid":
            result[outcome.decision_id] = {terminal.child_id}
            continue
        maturity = outcome.maturity_ordinal
        if maturity is None:
            continue
        queue = deque([(root, terminal, 1)])
        seen: set[str] = set()
        while queue:
            decision, current, depth = queue.popleft()
            if current.child_id in seen:
                continue
            seen.add(current.child_id)
            if depth >= outcome.lineage_depth:
                continue
            for child_decision, child_terminal in children.get(current.child_id, ()):
                if not (
                    root.event_ordinal < child_decision.event_ordinal <= maturity
                    and child_decision.context.map_elites.island_id
                    == root.context.map_elites.island_id
                ):
                    continue
                if child_terminal.status == "outcome":
                    queue.append((child_decision, child_terminal, depth + 1))
        result[outcome.decision_id] = seen
    return result


def _overlap_analysis(
    rows: list[LedgerRow], outcomes: tuple[LineageOutcome, ...]
) -> dict[str, Any]:
    descendants = _lineage_descendants(rows, outcomes)
    roots_by_descendant: dict[str, set[str]] = defaultdict(set)
    for root, values in descendants.items():
        for descendant in values:
            roots_by_descendant[descendant].add(root)
    multiplicities = [len(roots) for roots in roots_by_descendant.values()]
    parent = {root: root for root in descendants}

    def find(node: str) -> str:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for roots in roots_by_descendant.values():
        ordered = sorted(roots)
        for left, right in zip(ordered, ordered[1:]):
            union(left, right)
    components: dict[str, set[str]] = defaultdict(set)
    for root in parent:
        components[find(root)].add(root)
    total_assignments = sum(len(values) for values in descendants.values())
    unique_descendants = len(roots_by_descendant)
    return {
        "descendants_by_root": descendants,
        "roots_by_descendant": roots_by_descendant,
        "multiplicities": multiplicities,
        "roots": len(descendants),
        "unique_descendants": unique_descendants,
        "descendant_assignments": total_assignments,
        "reused_descendants": sum(value > 1 for value in multiplicities),
        "maximum_multiplicity": max(multiplicities, default=0),
        "mean_multiplicity": (
            total_assignments / unique_descendants if unique_descendants else 0.0
        ),
        "overlap_components": len(components),
        "largest_overlap_component": max(
            (len(value) for value in components.values()), default=0
        ),
        "components": tuple(tuple(sorted(value)) for value in components.values()),
    }


def _observed_utility(row: CausalObservation) -> float:
    reward = row.context.reward
    parent = row.context.parent_metrics[reward.primary_metric]
    if row.invalid:
        return (
            reward.metric_lower_bound - parent
            if reward.higher_is_better
            else parent - reward.metric_upper_bound
        )
    assert row.measurement is not None
    return row.measurement.value


def _dr_effect_score(row: CausalObservation) -> float:
    observed = _observed_utility(row)
    propensity = row.offer_propensity
    treated_score = row.reward_q_hat_treated
    control_score = row.reward_q_hat_control
    if row.treatment:
        treated_score += (observed - row.reward_q_hat_treated) / propensity
    else:
        control_score += (observed - row.reward_q_hat_control) / (1.0 - propensity)
    return treated_score - control_score


def _moving_block_bootstrap(
    rows: tuple[CausalObservation, ...],
    *,
    block_length: int,
    samples: int,
    seed: int,
    label: str,
) -> pd.DataFrame:
    ordered = tuple(sorted(rows, key=lambda row: row.event_ordinal))
    if not ordered:
        return pd.DataFrame()
    scores = np.asarray([_dr_effect_score(row) for row in ordered], dtype=float)
    rng = np.random.default_rng(seed)
    n = len(scores)
    length = max(1, min(block_length, n))
    boot = np.empty(samples, dtype=float)
    for index in range(samples):
        selected: list[int] = []
        while len(selected) < n:
            start = int(rng.integers(0, n))
            selected.extend((start + offset) % n for offset in range(length))
        boot[index] = float(np.mean(scores[np.asarray(selected[:n], dtype=int)]))
    estimate = float(np.mean(scores))
    iid_se = float(np.std(scores, ddof=1) / math.sqrt(n)) if n > 1 else math.nan
    result = pd.DataFrame({"endpoint": label, "bootstrap_effect": boot})
    result.attrs.update(
        {
            "estimate": estimate,
            "iid_se": iid_se,
            "block_se": float(np.std(boot, ddof=1)),
            "lower": float(np.quantile(boot, 0.025)),
            "upper": float(np.quantile(boot, 0.975)),
            "observations": n,
            "block_length": length,
        }
    )
    return result


def _combine_bootstrap(frames: Sequence[pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for frame in frames:
        if frame.empty:
            continue
        metadata = dict(frame.attrs)
        for value in frame["bootstrap_effect"]:
            rows.append(
                {"endpoint": frame.iloc[0]["endpoint"], "bootstrap_effect": value}
            )
        rows.append(
            {
                "endpoint": frame.iloc[0]["endpoint"],
                "bootstrap_effect": math.nan,
                **metadata,
            }
        )
    result = pd.DataFrame(rows)
    result.attrs["summaries"] = [
        dict(frame.attrs, endpoint=frame.iloc[0]["endpoint"])
        for frame in frames
        if not frame.empty
    ]
    return result


def _representative_context(
    observations: tuple[CausalObservation, ...], rows: list[LedgerRow]
) -> EvolutionContext | None:
    if observations:
        return sorted(observations, key=lambda row: row.event_ordinal)[-1].context
    return rows[-1].decision.context if rows else None


def _available_ope(
    reward_observations: tuple[CausalObservation, ...],
    safety_observations: tuple[CausalObservation, ...],
) -> tuple[list[dict[str, Any]], str | None]:
    try:
        return (
            evaluate_ope(
                reward_observations,
                safety_observations,
                reward_estimand="lineage_residual",
            ),
            None,
        )
    except ValueError as exc:
        error = str(exc)
    evaluator = ConditionalOfferDREvaluator()
    result: list[dict[str, Any]] = []
    for target in (0.0, 0.25, 0.5, 0.75, 1.0):

        def target_policy(_unit: Any, probability: float = target) -> float:
            return probability

        for kind, observations, method in (
            ("reward", reward_observations, evaluator.evaluate_reward),
            ("invalidity", safety_observations, evaluator.evaluate_invalidity),
        ):
            if not observations:
                continue
            try:
                report = method(observations, target_offer_probability=target_policy)
            except ValueError:
                continue
            result.append(
                {
                    "target_offer_probability": target,
                    "endpoint_kind": kind,
                    "reward_estimand": ("lineage_residual" if kind == "reward" else ""),
                    **report.model_dump(mode="json"),
                }
            )
    return result, error


def _current_lineage_ids(
    rows: list[LedgerRow], cards: tuple[CardSnapshot, ...]
) -> dict[str, str]:
    """Resolve every observed alias to the final persisted card survivor."""

    canonical = canonical_treatment_ids(rows)
    current_by_member: dict[str, str] = {}
    for card in cards:
        for card_id in (
            card.treatment_id,
            card.bank_card_id,
            *card.absorbed_bank_card_ids,
        ):
            current_by_member[card_id] = card.treatment_id
    for card_id, historical in tuple(canonical.items()):
        canonical[card_id] = current_by_member.get(
            card_id, current_by_member.get(historical, historical)
        )
    canonical.update(current_by_member)
    return canonical


def _current_evidence_lifecycle(
    rows: list[LedgerRow],
    candidates: list[dict[str, Any]],
    cards: tuple[CardSnapshot, ...],
) -> list[dict[str, Any]]:
    """Compute support after final merges instead of at the last decision snapshot."""

    canonical = _current_lineage_ids(rows, cards)
    remapped = []
    components: dict[str, set[str]] = defaultdict(set)
    for candidate in candidates:
        row = dict(candidate)
        original = str(row["treatment_id"])
        survivor = canonical.get(original, original)
        row["treatment_id"] = survivor
        remapped.append(row)
        if row.get("selected"):
            components[survivor].add(original)
    lifecycle = evidence_lifecycle(rows, remapped, canonical_ids=canonical)
    for row in lifecycle:
        treatment_id = str(row["treatment_id"])
        row["component_treatment_ids"] = "|".join(sorted(components[treatment_id]))
    return lifecycle


def prepare_data(
    ledger: Path,
    *,
    shadow_depth: int,
    shadow_budget: int,
    bootstrap_samples: int,
) -> ReportData:
    run_root = ledger.parent.parent
    audit = Audit()
    rows, integrity = load_ledger(ledger, audit)
    if not rows:
        raise ValueError("the ledger contains no decisions")
    audit_rows(rows, audit)
    decisions, candidate_rows, terminal_rows = flatten(rows)
    immediate = causal_observations(rows)
    active_outcomes, active_rewards = lineage_evidence(rows, immediate)
    shadow_immediate, shadow_outcomes, shadow_rewards = shadow_lineage_evidence(
        rows,
        immediate,
        lineage_depth=shadow_depth,
        opportunity_budget=shadow_budget,
    )
    config = _load_yaml_config(run_root)
    cards, descriptions = _load_cards(
        _cards_path(run_root),
        rows,
    )
    model = _model_from_config(config, rows)
    active_fit = model.fit(
        immediate,
        cards,
        lineage_observations=active_rewards,
    )
    shadow_fit = (
        model.fit(
            shadow_immediate,
            cards,
            lineage_observations=shadow_rewards,
        )
        if shadow_rewards
        else None
    )
    thresholds = _posterior_thresholds(rows)
    active_context = _representative_context(active_rewards, rows)
    shadow_context = _representative_context(shadow_rewards, rows)
    final_posterior = _fit_final_table(
        active_fit, cards, active_context, thresholds, seed=2026071501
    )
    shadow_final = _fit_final_table(
        shadow_fit, cards, shadow_context, thresholds, seed=2026071502
    )
    lifecycle = _current_evidence_lifecycle(rows, candidate_rows, cards)
    write_rows = _load_write_rows(_write_ledger_path(run_root))
    writer_trace = _writer_lifecycle(write_rows, {card.treatment_id for card in cards})
    llm_calls = _load_run_llm_calls(run_root)
    active_ope, active_ope_error = _available_ope(active_rewards, immediate)
    shadow_reward_ope = (
        _available_ope(shadow_rewards, shadow_immediate)[0] if shadow_rewards else []
    )
    shadow_ope = [row for row in shadow_reward_ope if row["endpoint_kind"] == "reward"]
    overlap = _overlap_analysis(rows, shadow_outcomes)
    bootstrap = _combine_bootstrap(
        (
            _moving_block_bootstrap(
                active_rewards,
                block_length=shadow_budget,
                samples=bootstrap_samples,
                seed=2026071511,
                label="Immediate D=1",
            ),
            _moving_block_bootstrap(
                shadow_rewards,
                block_length=shadow_budget,
                samples=bootstrap_samples,
                seed=2026071512,
                label=f"Shadow D={shadow_depth}, K={shadow_budget}",
            ),
        )
    )
    return ReportData(
        ledger=ledger,
        run_root=run_root,
        rows=rows,
        integrity=integrity,
        audit=audit,
        decisions=decisions,
        candidate_rows=candidate_rows,
        terminal_rows=terminal_rows,
        immediate=immediate,
        active_outcomes=active_outcomes,
        active_rewards=active_rewards,
        shadow_immediate=shadow_immediate,
        shadow_outcomes=shadow_outcomes,
        shadow_rewards=shadow_rewards,
        lifecycle=lifecycle,
        cards=cards,
        card_descriptions=descriptions,
        write_rows=write_rows,
        config=config,
        posterior_model=model,
        active_fit=active_fit,
        shadow_fit=shadow_fit,
        active_ope=active_ope,
        active_ope_error=active_ope_error,
        shadow_ope=shadow_ope,
        overlap=overlap,
        bootstrap=bootstrap,
        final_posterior=final_posterior,
        shadow_final_posterior=shadow_final,
        writer_trace=writer_trace,
        llm_calls=llm_calls,
        shadow_depth=shadow_depth,
        shadow_budget=shadow_budget,
    )


def _search_frame(data: ReportData) -> pd.DataFrame:
    result = []
    best = _initial_best_fitness(data)
    for row in data.rows:
        decision = row.decision
        reward = decision.context.reward
        parent = decision.context.parent_metrics[reward.primary_metric]
        best = max(best, parent) if reward.higher_is_better else min(best, parent)
        child = math.nan
        if (
            row.terminal is not None
            and row.terminal.status == "outcome"
            and row.terminal.measurement is not None
        ):
            child = (
                parent + row.terminal.measurement.value
                if reward.higher_is_better
                else parent - row.terminal.measurement.value
            )
            best = max(best, child) if reward.higher_is_better else min(best, child)
        result.append(
            {
                "ordinal": decision.event_ordinal,
                "parent_fitness": parent,
                "child_fitness": child,
                "best_fitness": best,
                "coverage": decision.context.map_elites.coverage,
                "archive_size": decision.context.map_elites.archive_size,
                "candidate_count": len(decision.candidates),
                "safe_count": sum(
                    action.safe for action in decision.action_probabilities
                ),
                "proposed": decision.proposed_treatment_id is not None,
                "delivered": decision.delivered,
                "status": row.terminal.status
                if row.terminal is not None
                else "pending",
            }
        )
    return pd.DataFrame(result)


def _initial_best_fitness(data: ReportData) -> float:
    """Load the actual valid seed best from immutable program storage."""

    problem = data.config.get("problem", {})
    problem_name = problem.get("name") if isinstance(problem, dict) else None
    if not isinstance(problem_name, str) or not problem_name:
        raise ValueError("resolved config omits problem.name")
    directory = data.run_root / "storage" / Path(problem_name) / "programs"
    if not directory.is_dir():
        raise FileNotFoundError(directory)

    reward = data.rows[0].decision.context.reward
    values = []
    for path in sorted(directory.glob("*.json")):
        try:
            program = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid program record: {path}") from exc
        metadata = program.get("metadata", {})
        if metadata.get("source") != "initial_program":
            continue
        metrics = program.get("metrics", {})
        if float(metrics.get("is_valid", 0.0)) <= 0.5:
            continue
        value = _finite(metrics.get(reward.primary_metric))
        if not math.isfinite(value):
            raise ValueError(
                f"valid initial program {path.name} has no finite "
                f"{reward.primary_metric}"
            )
        values.append(value)
    if not values:
        raise ValueError("program storage contains no valid initial-program fitness")
    return max(values) if reward.higher_is_better else min(values)


def _selected_candidate_frame(data: ReportData) -> pd.DataFrame:
    frame = pd.DataFrame(
        [row for row in data.candidate_rows if bool(row.get("selected"))]
    )
    if frame.empty:
        return frame
    terminal = {row.decision.decision_id: row.terminal for row in data.rows}
    actual_utility = []
    actual_invalid = []
    predicted_utility = []
    predicted_invalid = []
    for row in frame.to_dict("records"):
        outcome = terminal.get(str(row["decision_id"]))
        ledger = next(
            item
            for item in data.rows
            if item.decision.decision_id == row["decision_id"]
        )
        decision = ledger.decision
        reward = decision.context.reward
        parent = decision.context.parent_metrics[reward.primary_metric]
        if outcome is None or outcome.status == "censored":
            actual_utility.append(math.nan)
            actual_invalid.append(math.nan)
        elif outcome.status == "invalid":
            actual_utility.append(
                reward.metric_lower_bound - parent
                if reward.higher_is_better
                else parent - reward.metric_upper_bound
            )
            actual_invalid.append(1.0)
        else:
            actual_utility.append(
                outcome.measurement.value if outcome.measurement else math.nan
            )
            actual_invalid.append(0.0)
        treated = bool(decision.delivered)
        predicted_utility.append(
            decision.reward_q_hat_treated if treated else decision.reward_q_hat_control
        )
        predicted_invalid.append(
            decision.risk_q_hat_treated if treated else decision.risk_q_hat_control
        )
    frame["actual_utility"] = actual_utility
    frame["actual_invalid"] = actual_invalid
    frame["predicted_realized_utility"] = predicted_utility
    frame["predicted_realized_invalid"] = predicted_invalid
    return frame


def _box(
    ax: plt.Axes,
    xy: tuple[float, float],
    width: float,
    height: float,
    title: str,
    body: str,
    color: str,
) -> None:
    patch = FancyBboxPatch(
        xy,
        width,
        height,
        boxstyle="round,pad=0.012,rounding_size=0.018",
        edgecolor=color,
        facecolor="white",
        linewidth=1.7,
    )
    ax.add_patch(patch)
    ax.text(
        xy[0] + 0.03 * width,
        xy[1] + 0.78 * height,
        title,
        weight="bold",
        color=color,
        va="top",
        fontsize=11,
    )
    ax.text(
        xy[0] + 0.03 * width,
        xy[1] + 0.58 * height,
        body,
        color=INK,
        va="top",
        fontsize=8.3,
        linespacing=1.3,
    )


def _arrow(
    ax: plt.Axes,
    start: tuple[float, float],
    end: tuple[float, float],
    color: str = MUTED,
) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=13,
            linewidth=1.4,
            color=color,
        )
    )


def render_architecture(data: ReportData, paths: ReportPaths) -> None:
    agentic = any(
        row.decision.applicability.specification.name == "agentic_research"
        for row in data.rows
    )
    candidate_detail = (
        "full eligible bank\nRAG applicability label\none card action"
        if agentic
        else "whole current bank\nlineage exclusion\none card action"
    )
    offer_probability = data.rows[-1].decision.policy.offer_probability
    fig = _figure(
        "Memory v2: causal and Bayesian data flow",
        "The lower lineage branch is computed offline in this smoke and never feeds the live policy.",
    )
    ax = fig.add_axes((0.04, 0.08, 0.92, 0.80))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    boxes = (
        (
            (0.01, 0.61),
            0.15,
            0.23,
            "Frozen context",
            "parent fitness\nsemantic MAP coordinates\nprogress + task",
            BLUE,
        ),
        (
            (0.21, 0.61),
            0.15,
            0.23,
            "Eligible bank",
            candidate_detail,
            TEAL,
        ),
        (
            (0.41, 0.61),
            0.18,
            0.23,
            "Hierarchical posterior",
            "bounded reward head\nlogistic safety head\nshared + card effects",
            PURPLE,
        ),
        (
            (0.64, 0.61),
            0.15,
            0.23,
            "Policy",
            "chance constraint\nprobability matching\n5% support floor",
            ORANGE,
        ),
        (
            (0.84, 0.61),
            0.15,
            0.23,
            "Randomized offer",
            f"fixed p={offer_probability:.2f}\ntreated or withheld\nknown propensity",
            GOLD,
        ),
        (
            (0.16, 0.18),
            0.18,
            0.23,
            "Mutation + terminal",
            "selected base lineage\nchild outcome or invalid\nmeasurement uncertainty",
            GREEN,
        ),
        (
            (0.41, 0.18),
            0.18,
            0.23,
            "Immutable ledger",
            "decision before action\nterminal after action\nreplayable probabilities",
            BLUE,
        ),
        (
            (0.68, 0.18),
            0.22,
            0.23,
            "Shadow lineage endpoint",
            f"best descendant to depth {data.shadow_depth}\nfirst {data.shadow_budget} local opportunities\none return per root",
            RED,
        ),
    )
    for args in boxes:
        _box(ax, *args)
    for start, end in (
        ((0.16, 0.725), (0.21, 0.725)),
        ((0.36, 0.725), (0.41, 0.725)),
        ((0.59, 0.725), (0.64, 0.725)),
        ((0.79, 0.725), (0.84, 0.725)),
        ((0.915, 0.61), (0.30, 0.41)),
        ((0.34, 0.295), (0.41, 0.295)),
        ((0.59, 0.295), (0.68, 0.295)),
        ((0.50, 0.41), (0.50, 0.61)),
    ):
        _arrow(ax, start, end)
    ax.text(
        0.79,
        0.08,
        "working-independence fit is audited for overlap",
        color=RED,
        ha="center",
        fontsize=9,
        weight="bold",
    )
    _save_figure(fig, paths, "01_system_architecture")


def render_executive(data: ReportData, paths: ReportPaths) -> None:
    search = _search_frame(data)
    statuses = Counter(row["status"] for row in data.terminal_rows)
    proposals = sum(row["proposed"] for row in data.decisions)
    mature_shadow = sum(
        row.status in {"outcome", "invalid"} for row in data.shadow_outcomes
    )
    audit_pass = not data.audit.errors and data.integrity == "ok"
    fig = _figure(
        "Executive evidence dashboard",
        "Operational health, randomized support, search progress, and long-horizon maturity at a glance.",
    )
    grid = fig.add_gridspec(
        3, 4, left=0.055, right=0.97, top=0.86, bottom=0.08, hspace=0.48, wspace=0.35
    )
    kpis = (
        (
            "Ledger",
            "PASS" if audit_pass else "FAIL",
            f"{len(data.rows)} decisions",
            GREEN if audit_pass else RED,
        ),
        (
            "Randomized",
            str(proposals),
            f"{sum(row['delivered'] for row in data.decisions)} treated / {proposals - sum(row['delivered'] for row in data.decisions)} control",
            BLUE,
        ),
        ("Bank", str(len(data.cards)), f"{len(data.write_rows)} write events", TEAL),
        (
            "Shadow mature",
            str(mature_shadow),
            f"of {len(data.shadow_outcomes)} proposed roots",
            PURPLE,
        ),
    )
    for index, (title, value, detail, color) in enumerate(kpis):
        ax = fig.add_subplot(grid[0, index])
        ax.axis("off")
        ax.add_patch(
            FancyBboxPatch(
                (0, 0.02),
                1,
                0.92,
                boxstyle="round,pad=0.02",
                facecolor=LIGHT,
                edgecolor=GRID,
            )
        )
        ax.text(0.06, 0.78, title.upper(), color=MUTED, size=8.5)
        ax.text(0.06, 0.47, value, color=color, size=23, weight="bold")
        ax.text(0.06, 0.18, detail, color=INK, size=8.7)
    ax = fig.add_subplot(grid[1:, :2])
    ax.plot(
        search["ordinal"],
        search["best_fitness"],
        color=BLUE,
        linewidth=2.2,
        label="best observed",
    )
    ax.scatter(
        search["ordinal"],
        search["child_fitness"],
        s=13,
        color=TEAL,
        alpha=0.45,
        label="valid child",
    )
    ax.set_title("Evolutionary search trajectory", loc="left")
    ax.set_xlabel("memory decision ordinal")
    ax.set_ylabel("fitness")
    ax.legend(loc="best")
    ax = fig.add_subplot(grid[1:, 2])
    labels = ["outcome", "invalid", "censored", "pending"]
    values = [statuses.get(label, 0) for label in labels[:-1]] + [
        sum(row.terminal is None for row in data.rows)
    ]
    ax.bar(labels, values, color=(GREEN, RED, MUTED, GOLD))
    ax.set_title("Terminal accounting", loc="left")
    ax.tick_params(axis="x", rotation=25)
    for index, value in enumerate(values):
        ax.text(
            index, value + max(values + [1]) * 0.025, str(value), ha="center", color=INK
        )
    ax = fig.add_subplot(grid[1:, 3])
    shadow_counts = Counter(row.status for row in data.shadow_outcomes)
    labels = ["mature", "pending", "censored"]
    values = [
        shadow_counts["outcome"] + shadow_counts["invalid"],
        shadow_counts["pending"],
        shadow_counts["censored"],
    ]
    ax.bar(labels, values, color=(PURPLE, GOLD, MUTED))
    ax.set_title(f"Shadow D={data.shadow_depth}, K={data.shadow_budget}", loc="left")
    ax.tick_params(axis="x", rotation=25)
    for index, value in enumerate(values):
        ax.text(
            index, value + max(values + [1]) * 0.025, str(value), ha="center", color=INK
        )
    _save_figure(fig, paths, "02_executive_dashboard")


def render_search_and_context(data: ReportData, paths: ReportPaths) -> None:
    frame = _search_frame(data)
    fig = _figure(
        "Search, archive, and memory intervention trace",
        "All panels share the immutable decision ordinal; no wall-clock interpolation is used.",
    )
    grid = fig.add_gridspec(
        2, 2, left=0.07, right=0.97, top=0.86, bottom=0.09, hspace=0.42, wspace=0.28
    )
    ax = fig.add_subplot(grid[0, 0])
    ax.plot(
        frame["ordinal"],
        frame["parent_fitness"],
        color=MUTED,
        alpha=0.55,
        linewidth=1,
        label="selected parent",
    )
    ax.plot(
        frame["ordinal"],
        frame["best_fitness"],
        color=BLUE,
        linewidth=2.1,
        label="cumulative best",
    )
    treated = frame[frame["delivered"]]
    control = frame[frame["proposed"] & ~frame["delivered"]]
    ax.scatter(
        treated["ordinal"],
        treated["child_fitness"],
        s=18,
        color=TEAL,
        alpha=0.65,
        label="treated child",
    )
    ax.scatter(
        control["ordinal"],
        control["child_fitness"],
        s=18,
        facecolor="white",
        edgecolor=ORANGE,
        alpha=0.8,
        label="withheld child",
    )
    ax.set_title("Fitness and randomized arms", loc="left")
    ax.set_ylabel("fitness")
    ax.legend(ncol=2, fontsize=8)
    ax = fig.add_subplot(grid[0, 1])
    ax.plot(
        frame["ordinal"],
        frame["coverage"],
        color=GREEN,
        linewidth=1.8,
        label="coverage",
    )
    ax2 = ax.twinx()
    ax2.plot(
        frame["ordinal"],
        frame["archive_size"],
        color=PURPLE,
        linewidth=1.4,
        alpha=0.8,
        label="archive size",
    )
    ax.set_title("MAP-Elites archive state", loc="left")
    ax.set_ylabel("coverage", color=GREEN)
    ax2.set_ylabel("archive size", color=PURPLE)
    ax = fig.add_subplot(grid[1, 0])
    ax.step(
        frame["ordinal"],
        frame["candidate_count"],
        where="post",
        color=BLUE,
        label="eligible cards",
    )
    ax.step(
        frame["ordinal"],
        frame["safe_count"],
        where="post",
        color=TEAL,
        label="admitted",
    )
    ax.set_title("Candidate and admitted set sizes", loc="left")
    ax.set_xlabel("decision ordinal")
    ax.set_ylabel("cards")
    ax.legend()
    ax = fig.add_subplot(grid[1, 1])
    rolling = (
        frame["delivered"].where(frame["proposed"]).rolling(25, min_periods=5).mean()
    )
    ax.plot(
        frame["ordinal"],
        rolling,
        color=ORANGE,
        linewidth=1.8,
        label="25-proposal delivery rate",
    )
    ax.axhline(
        data.rows[-1].decision.policy.offer_probability,
        color=INK,
        linestyle="--",
        linewidth=1,
        label="configured p",
    )
    ax.set_ylim(0, 1)
    ax.set_title("Randomized offer realization", loc="left")
    ax.set_xlabel("decision ordinal")
    ax.set_ylabel("treated fraction")
    ax.legend()
    _save_figure(fig, paths, "03_search_and_interventions")


def render_bank_lifecycle(data: ReportData, paths: ReportPaths) -> None:
    candidate = pd.DataFrame(data.candidate_rows)
    selected = candidate[candidate["selected"]] if not candidate.empty else candidate
    canonical = _current_lineage_ids(data.rows, data.cards)
    if not selected.empty:
        selected = selected.copy()
        selected["canonical_id"] = selected["treatment_id"].map(
            lambda value: canonical.get(value, value)
        )
    fig = _figure(
        "Bank growth, merging, and evidence throughput",
        "The task-wide hard cap is absent; merging preserves a statistical lineage instead of resetting evidence.",
    )
    grid = fig.add_gridspec(
        2, 2, left=0.07, right=0.97, top=0.86, bottom=0.10, hspace=0.43, wspace=0.30
    )
    ax = fig.add_subplot(grid[0, 0])
    if not data.writer_trace.empty:
        trace = data.writer_trace
        ax.step(
            trace["write_index"],
            trace["reconstructed_bank_size"],
            where="post",
            color=BLUE,
            linewidth=2,
        )
        ax.axhline(
            len(data.cards),
            color=TEAL,
            linestyle="--",
            label=f"final persisted={len(data.cards)}",
        )
    ax.set_title("Bank size across write events", loc="left")
    ax.set_xlabel("write event")
    ax.set_ylabel("cards")
    ax.legend()
    ax = fig.add_subplot(grid[0, 1])
    write_counts = Counter(
        str(row.get("outcome", "unknown")) for row in data.write_rows
    )
    labels = sorted(write_counts)
    ax.bar(
        labels,
        [write_counts[label] for label in labels],
        color=[COLORS[index % len(COLORS)] for index in range(len(labels))],
    )
    ax.set_title("Writer outcomes", loc="left")
    ax.tick_params(axis="x", rotation=25)
    ax = fig.add_subplot(grid[1, 0])
    if not selected.empty:
        counts = selected.groupby("canonical_id").size().sort_values(ascending=False)
        ranks = np.arange(1, len(counts) + 1)
        ax.bar(ranks, counts.values, color=TEAL)
        ax.axhline(
            4,
            color=ORANGE,
            linestyle="--",
            linewidth=1,
            label="2 treated + 2 control minimum",
        )
    ax.set_title("Randomized offers per stable card lineage", loc="left")
    ax.set_xlabel("card rank by offers")
    ax.set_ylabel("offers")
    ax.legend()
    ax = fig.add_subplot(grid[1, 1])
    if data.lifecycle:
        lifecycle = pd.DataFrame(data.lifecycle)
        x = lifecycle["offers"].to_numpy(dtype=float)
        y = lifecycle["balanced_ess"].to_numpy(dtype=float)
        ready = lifecycle["support_ready"].to_numpy(dtype=bool)
        ax.scatter(
            x[~ready], y[~ready], color=MUTED, alpha=0.65, label="cold / imbalanced"
        )
        ax.scatter(x[ready], y[ready], color=GREEN, alpha=0.85, label="support-ready")
        limit = max(float(np.max(x)), 1.0)
        ax.plot([0, limit], [0, limit], color=GRID, linestyle="--", linewidth=1)
    ax.set_title("Offers versus balanced randomized ESS", loc="left")
    ax.set_xlabel("closed offers")
    ax.set_ylabel("balanced ESS")
    ax.legend()
    _save_figure(fig, paths, "04_bank_and_evidence_lifecycle")


def render_llm_resources(data: ReportData, paths: ReportPaths) -> pd.DataFrame:
    summary = _llm_resource_summary(data.llm_calls)
    fig = _figure(
        "LLM resource profile by system component",
        "Provider latency is summed call latency, not wall time; calls may overlap. Writer stages include authoring, reconciliation, and consolidation.",
    )
    grid = fig.add_gridspec(
        2, 2, left=0.12, right=0.97, top=0.86, bottom=0.10, hspace=0.42, wspace=0.34
    )
    panels = (
        ("calls", "LLM calls", "calls"),
        ("total_tokens", "Tokens consumed", "tokens"),
        ("provider_latency_seconds", "Summed provider latency", "seconds"),
    )
    for index, (column, title, xlabel) in enumerate(panels):
        ax = fig.add_subplot(grid[index // 2, index % 2])
        if not summary.empty:
            ordered = summary.sort_values(column, ascending=True)
            colors = ordered["call_category"].map(
                {"writer": TEAL, "retrieval": PURPLE, "mutation": BLUE}
            )
            ax.barh(ordered["stage"], ordered[column], color=colors)
        ax.set_title(title, loc="left")
        ax.set_xlabel(xlabel)
    ax = fig.add_subplot(grid[1, 1])
    if not summary.empty:
        labels = ("calls", "tokens", "provider latency")
        values = {}
        for category in ("writer", "retrieval", "mutation"):
            selected = summary[summary["call_category"] == category]
            values[category] = np.asarray(
                [
                    selected["calls"].sum(),
                    selected["total_tokens"].sum(),
                    selected["provider_latency_seconds"].sum(),
                ],
                dtype=float,
            )
        total = np.maximum(sum(values.values()), 1.0)
        x = np.arange(len(labels))
        bottom = np.zeros(len(labels), dtype=float)
        for category, label, color in (
            ("writer", "memory writer", TEAL),
            ("retrieval", "agentic retrieval", PURPLE),
            ("mutation", "mutation pipeline", BLUE),
        ):
            share = values[category] / total
            ax.bar(x, share, bottom=bottom, color=color, label=label)
            bottom += share
        ax.set_xticks(x, labels, rotation=18)
        ax.set_ylim(0, 1)
        ax.set_yticks(np.linspace(0, 1, 5), ["0%", "25%", "50%", "75%", "100%"])
    ax.set_title("Resource share", loc="left")
    ax.legend(fontsize=8)
    _save_figure(fig, paths, "17_llm_resource_profile")
    return summary


def _top_cards(data: ReportData, limit: int = 8) -> tuple[CardSnapshot, ...]:
    offers = Counter(
        row["treatment_id"] for row in data.candidate_rows if row.get("selected")
    )
    card_by_id = {card.treatment_id: card for card in data.cards}
    ranked = sorted(
        data.cards,
        key=lambda card: (
            offers[card.treatment_id],
            float(
                data.final_posterior.set_index("treatment_id")
                .get("effect_mean", {})
                .get(card.treatment_id, -math.inf)
                if not data.final_posterior.empty
                else -math.inf
            ),
        ),
        reverse=True,
    )
    return tuple(card_by_id[card.treatment_id] for card in ranked[:limit])


def _posterior_draw_table(
    fitted: FittedTerminalUtilityPosterior | None,
    cards: tuple[CardSnapshot, ...],
    context: EvolutionContext | None,
    *,
    seed: int,
) -> np.ndarray:
    if fitted is None or not cards or context is None:
        return np.empty((0, len(cards)))
    return fitted.sample_usable_effects(
        cards, context, np.random.default_rng(seed), samples=12000
    )


def render_posterior_distributions(data: ReportData, paths: ReportPaths) -> None:
    cards = _top_cards(data, 8)
    active_context = _representative_context(data.active_rewards, data.rows)
    shadow_context = _representative_context(data.shadow_rewards, data.rows)
    active = _posterior_draw_table(
        data.active_fit, cards, active_context, seed=2026071521
    )
    shadow = _posterior_draw_table(
        data.shadow_fit, cards, shadow_context, seed=2026071522
    )
    fig = _figure(
        "Fitted card-effect posteriors at the final observed context",
        "Violins are posterior draws of usable treated-minus-withheld utility; dots are means and bars are 95% credible intervals.",
    )
    grid = fig.add_gridspec(
        1, 2, left=0.12, right=0.98, top=0.84, bottom=0.12, wspace=0.32
    )
    labels = [_short(card.treatment_id) for card in cards]
    for ax, draws, title, color in (
        (fig.add_subplot(grid[0, 0]), active, "Live posterior: immediate D=1", BLUE),
        (
            fig.add_subplot(grid[0, 1]),
            shadow,
            f"Shadow posterior: D={data.shadow_depth}, K={data.shadow_budget}",
            PURPLE,
        ),
    ):
        if draws.size:
            parts = ax.violinplot(
                [draws[:, index] for index in range(draws.shape[1])],
                positions=np.arange(len(cards)),
                vert=False,
                showextrema=False,
                widths=0.8,
            )
            for body in parts["bodies"]:
                body.set_facecolor(color)
                body.set_edgecolor(color)
                body.set_alpha(0.28)
            means = np.mean(draws, axis=0)
            lower = np.quantile(draws, 0.025, axis=0)
            upper = np.quantile(draws, 0.975, axis=0)
            ax.errorbar(
                means,
                np.arange(len(cards)),
                xerr=(means - lower, upper - means),
                fmt="o",
                color=color,
                ecolor=color,
                capsize=3,
            )
        ax.axvline(0, color=INK, linewidth=1, linestyle="--")
        ax.set_yticks(np.arange(len(cards)), labels)
        ax.invert_yaxis()
        ax.set_xlabel("usable effect / metric range")
        ax.set_title(title, loc="left")
    _save_figure(fig, paths, "05_fitted_posterior_distributions")


def _context_with_fitness(context: EvolutionContext, value: float) -> EvolutionContext:
    metrics = dict(context.parent_metrics)
    metrics[context.reward.primary_metric] = value
    return context.model_copy(update={"parent_metrics": metrics})


def _context_with_progress(
    context: EvolutionContext, iteration: int
) -> EvolutionContext:
    return context.model_copy(update={"parent_iteration": max(0, int(iteration))})


def _context_with_behavior(
    context: EvolutionContext, key: str, normalized: float
) -> EvolutionContext:
    coordinates = tuple(
        coordinate.model_copy(update={"semantic_normalized": float(normalized)})
        if coordinate.key == key
        else coordinate
        for coordinate in context.map_elites.coordinates
    )
    map_elites = context.map_elites.model_copy(update={"coordinates": coordinates})
    return context.model_copy(update={"map_elites": map_elites})


def _context_prediction_grid(
    fitted: FittedTerminalUtilityPosterior | None,
    cards: tuple[CardSnapshot, ...],
    contexts: Sequence[EvolutionContext],
    x_values: Sequence[float],
    thresholds: tuple[float | None, float, float],
    *,
    seed: int,
    endpoint: str,
) -> pd.DataFrame:
    if fitted is None:
        return pd.DataFrame()
    result = []
    for index, (x_value, context) in enumerate(zip(x_values, contexts)):
        predictions = fitted.predictions(
            cards,
            context,
            np.random.default_rng(seed + index),
            samples=2048,
            max_treated_invalid_probability=thresholds[0],
            max_incremental_invalid_probability=thresholds[1],
            safety_alpha=thresholds[2],
        )
        for card in cards:
            prediction = predictions[card.treatment_id]
            result.append(
                {
                    "endpoint": endpoint,
                    "x": float(x_value),
                    "treatment_id": card.treatment_id,
                    "effect": prediction.usable_effect_mean,
                    "effect_sd": prediction.usable_effect_sd,
                    "p_help": prediction.probability_helpful,
                    "p_safe": prediction.probability_safe,
                    "risk_treated": prediction.treated_invalid_probability,
                    "risk_upper": prediction.treated_invalid_upper,
                    "risk_increment": prediction.incremental_invalid_probability,
                }
            )
    return pd.DataFrame(result)


def render_contextual_posteriors(data: ReportData, paths: ReportPaths) -> pd.DataFrame:
    cards = _top_cards(data, 5)
    thresholds = _posterior_thresholds(data.rows)
    active_context = _representative_context(data.active_rewards, data.rows)
    shadow_context = _representative_context(data.shadow_rewards, data.rows)
    if active_context is None:
        return pd.DataFrame()
    reward = active_context.reward
    observed_fitness = [
        row.decision.context.parent_metrics[reward.primary_metric] for row in data.rows
    ]
    lower = _quantile(observed_fitness, 0.02, reward.metric_lower_bound)
    upper = _quantile(observed_fitness, 0.98, reward.metric_upper_bound)
    if upper <= lower:
        lower, upper = reward.metric_lower_bound, reward.metric_upper_bound
    fitness = np.linspace(lower, upper, 25)
    active_fitness = _context_prediction_grid(
        data.active_fit,
        cards,
        [_context_with_fitness(active_context, value) for value in fitness],
        fitness,
        thresholds,
        seed=2026071530,
        endpoint="live D=1",
    )
    shadow_fitness = _context_prediction_grid(
        data.shadow_fit,
        cards,
        [_context_with_fitness(shadow_context, value) for value in fitness]
        if shadow_context
        else [],
        fitness if shadow_context else [],
        thresholds,
        seed=2026071560,
        endpoint=f"shadow D={data.shadow_depth}",
    )
    behavior_key = (
        active_context.map_elites.coordinates[0].key
        if active_context.map_elites.coordinates
        else ""
    )
    behavior = np.linspace(0, 1, 25)
    behavior_grid = (
        _context_prediction_grid(
            data.active_fit,
            cards,
            [
                _context_with_behavior(active_context, behavior_key, value)
                for value in behavior
            ],
            behavior,
            thresholds,
            seed=2026071590,
            endpoint=f"behavior:{behavior_key}",
        )
        if behavior_key
        else pd.DataFrame()
    )
    observed_iterations = [row.decision.context.parent_iteration for row in data.rows]
    progress = np.linspace(
        min(observed_iterations), max(observed_iterations), 25
    ).astype(int)
    progress_grid = _context_prediction_grid(
        data.active_fit,
        cards,
        [_context_with_progress(active_context, int(value)) for value in progress],
        progress,
        thresholds,
        seed=2026071620,
        endpoint="progress",
    )
    combined = pd.concat(
        (active_fitness, shadow_fitness, behavior_grid, progress_grid),
        ignore_index=True,
    )
    fig = _figure(
        "Contextual posterior response surfaces",
        "Each curve changes one frozen pre-treatment coordinate while holding the remaining context at the final observed state.",
    )
    grid = fig.add_gridspec(
        2, 2, left=0.08, right=0.98, top=0.86, bottom=0.10, hspace=0.43, wspace=0.30
    )
    ax = fig.add_subplot(grid[0, 0])
    for index, card in enumerate(cards):
        subset = active_fitness[active_fitness["treatment_id"] == card.treatment_id]
        color = COLORS[index % len(COLORS)]
        ax.plot(
            subset["x"], subset["effect"], color=color, label=_short(card.treatment_id)
        )
        ax.fill_between(
            subset["x"],
            subset["effect"] - 1.96 * subset["effect_sd"],
            subset["effect"] + 1.96 * subset["effect_sd"],
            color=color,
            alpha=0.09,
        )
    ax.axhline(0, color=INK, linestyle="--", linewidth=1)
    ax.set_title("Live effect by parent fitness", loc="left")
    ax.set_xlabel("parent fitness")
    ax.set_ylabel("usable effect")
    ax.legend(ncol=2, fontsize=7.5)
    ax = fig.add_subplot(grid[0, 1])
    if not shadow_fitness.empty:
        for index, card in enumerate(cards):
            subset = shadow_fitness[shadow_fitness["treatment_id"] == card.treatment_id]
            if not subset.empty:
                ax.plot(
                    subset["x"],
                    subset["effect"],
                    color=COLORS[index % len(COLORS)],
                    label=_short(card.treatment_id),
                )
    ax.axhline(0, color=INK, linestyle="--", linewidth=1)
    ax.set_title("Shadow lineage effect by parent fitness", loc="left")
    ax.set_xlabel("parent fitness")
    ax.set_ylabel("usable effect")
    if not shadow_fitness.empty:
        ax.legend(ncol=2, fontsize=7.5)
    ax = fig.add_subplot(grid[1, 0])
    for index, card in enumerate(cards):
        subset = behavior_grid[behavior_grid["treatment_id"] == card.treatment_id]
        ax.plot(subset["x"], subset["effect"], color=COLORS[index % len(COLORS)])
    ax.axhline(0, color=INK, linestyle="--", linewidth=1)
    ax.set_title(f"Live effect by semantic MAP coordinate: {behavior_key}", loc="left")
    ax.set_xlabel("stable semantic normalization")
    ax.set_ylabel("usable effect")
    ax = fig.add_subplot(grid[1, 1])
    for index, card in enumerate(cards):
        subset = progress_grid[progress_grid["treatment_id"] == card.treatment_id]
        ax.plot(subset["x"], subset["effect"], color=COLORS[index % len(COLORS)])
    ax.axhline(0, color=INK, linestyle="--", linewidth=1)
    ax.set_title("Live effect by evolutionary progress", loc="left")
    ax.set_xlabel("parent iteration")
    ax.set_ylabel("usable effect")
    _save_figure(fig, paths, "06_contextual_posterior_surfaces")
    return combined


def render_safety_posterior(
    data: ReportData, paths: ReportPaths, contextual: pd.DataFrame
) -> None:
    cards = _top_cards(data, 7)
    thresholds = _posterior_thresholds(data.rows)
    policy = data.rows[-1].decision.policy
    incremental_gate = policy.safety_gate_mode == "exclude_confident_incremental_harm"
    final = (
        data.final_posterior.set_index("treatment_id")
        if not data.final_posterior.empty
        else pd.DataFrame()
    )
    fig = _figure(
        "Invalidity posterior and admission behavior",
        (
            "The default gate excludes only confident excess incremental harm; "
            "posterior invalidity levels remain diagnostics."
            if incremental_gate
            else "The joint-safe gate uses posterior probability, not only mean invalidity."
        ),
    )
    grid = fig.add_gridspec(
        2, 2, left=0.09, right=0.98, top=0.86, bottom=0.10, hspace=0.43, wspace=0.32
    )
    ax = fig.add_subplot(grid[0, 0])
    labels = [_short(card.treatment_id) for card in cards]
    values = [
        final.loc[card.treatment_id, "treated_invalid"]
        if card.treatment_id in final.index
        else math.nan
        for card in cards
    ]
    uppers = [
        final.loc[card.treatment_id, "treated_invalid_upper"]
        if card.treatment_id in final.index
        else math.nan
        for card in cards
    ]
    y = np.arange(len(cards))
    ax.scatter(values, y, color=BLUE, label="posterior mean")
    ax.scatter(uppers, y, facecolor="white", edgecolor=RED, label="90% upper")
    if thresholds[0] is not None:
        ax.axvline(
            thresholds[0],
            color=RED,
            linestyle="--",
            linewidth=1.3,
            label="treated-risk limit",
        )
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(left=0)
    ax.set_title("Final-context treated invalidity", loc="left")
    ax.set_xlabel("probability")
    ax.legend(fontsize=8)
    ax = fig.add_subplot(grid[0, 1])
    increments = [
        final.loc[card.treatment_id, "incremental_invalid"]
        if card.treatment_id in final.index
        else math.nan
        for card in cards
    ]
    inc_upper = [
        final.loc[card.treatment_id, "incremental_invalid_upper"]
        if card.treatment_id in final.index
        else math.nan
        for card in cards
    ]
    ax.scatter(increments, y, color=TEAL, label="posterior mean")
    ax.scatter(inc_upper, y, facecolor="white", edgecolor=ORANGE, label="90% upper")
    ax.axvline(
        thresholds[1],
        color=ORANGE,
        linestyle="--",
        linewidth=1.3,
        label="incremental limit",
    )
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_title("Final-context incremental invalidity", loc="left")
    ax.set_xlabel("treated minus control risk")
    ax.legend(fontsize=8)
    fitness = (
        contextual[contextual["endpoint"] == "live D=1"]
        if not contextual.empty
        else contextual
    )
    ax = fig.add_subplot(grid[1, 0])
    for index, card in enumerate(cards[:5]):
        subset = fitness[fitness["treatment_id"] == card.treatment_id]
        ax.plot(
            subset["x"],
            subset["risk_upper"],
            color=COLORS[index % len(COLORS)],
            label=_short(card.treatment_id),
        )
    if thresholds[0] is not None:
        ax.axhline(thresholds[0], color=RED, linestyle="--", linewidth=1.2)
        ax.set_ylim(0, max(0.35, thresholds[0] * 1.35))
    elif not fitness.empty:
        ax.set_ylim(0, max(0.35, float(fitness["risk_upper"].max()) * 1.1))
    ax.set_title("Risk upper bound across parent fitness", loc="left")
    ax.set_xlabel("parent fitness")
    ax.set_ylabel("treated invalid upper")
    ax.legend(ncol=2, fontsize=7.5)
    ax = fig.add_subplot(grid[1, 1])
    candidate = pd.DataFrame(data.candidate_rows)
    if not candidate.empty:
        selected = candidate[candidate["selected"]]
        ax.plot(
            selected["ordinal"],
            selected["probability_safe"],
            color=GREEN,
            linewidth=1.3,
            alpha=0.8,
        )
        ax.scatter(
            selected["ordinal"],
            selected["treated_invalid_upper"],
            color=RED,
            s=12,
            alpha=0.5,
            label="treated-risk upper",
        )
    ax.axhline(
        thresholds[2] if incremental_gate else 1.0 - thresholds[2],
        color=GREEN,
        linestyle="--",
        linewidth=1,
        label="admission boundary",
    )
    if thresholds[0] is not None:
        ax.axhline(
            thresholds[0], color=RED, linestyle=":", linewidth=1, label="risk limit"
        )
    ax.set_title("Selected-card acceptable-event probability", loc="left")
    ax.set_xlabel("decision ordinal")
    ax.set_ylabel("probability")
    ax.legend(fontsize=8)
    _save_figure(fig, paths, "07_safety_posterior")


def _coefficient_labels(fitted: FittedTerminalUtilityPosterior) -> list[str]:
    behavior = list(fitted.space.config.behavior_keys)
    context = ["intercept", "parent fitness", "progress", *behavior]
    labels = [
        *(f"baseline: {name}" for name in context),
        *(f"shared treatment: {name}" for name in context),
    ]
    if fitted.space.config.card_kind_contrast:
        labels.append("shared treatment: card kind (program - insight)")
    if fitted.space.config.retrieval_applicability_contrast:
        labels.append("shared treatment: RAG applicability")
    return labels


def render_hierarchy(data: ReportData, paths: ReportPaths) -> None:
    fitted = data.active_fit
    labels = _coefficient_labels(fitted)
    count = len(labels)
    reward_mean = fitted.reward.mean[:count]
    reward_sd = np.sqrt(np.maximum(np.diag(fitted.reward.covariance)[:count], 0.0))
    safety_mean = fitted.safety.mean[:count]
    safety_sd = np.sqrt(np.maximum(np.diag(fitted.safety.covariance)[:count], 0.0))
    context_dim = fitted.space.context_dim
    shared_effect_stop = context_dim + fitted.space.card_effect_slice.start
    effect_cov = fitted.reward.covariance[
        context_dim:shared_effect_stop, context_dim:shared_effect_stop
    ]
    shared_effect_labels = labels[context_dim:]
    denom = np.sqrt(np.outer(np.diag(effect_cov), np.diag(effect_cov)))
    correlation = np.divide(
        effect_cov, denom, out=np.zeros_like(effect_cov), where=denom > 0
    )
    fig = _figure(
        "Hierarchical posterior anatomy",
        "Shared coefficients borrow strength across cards; card-lineage deviations are regularized around those shared effects.",
    )
    grid = fig.add_gridspec(
        2, 2, left=0.18, right=0.97, top=0.86, bottom=0.11, hspace=0.46, wspace=0.34
    )
    y = np.arange(count)
    ax = fig.add_subplot(grid[:, 0])
    ax.errorbar(
        reward_mean,
        y - 0.12,
        xerr=1.96 * reward_sd,
        fmt="o",
        color=BLUE,
        capsize=2.5,
        label="bounded reward",
    )
    ax.errorbar(
        safety_mean,
        y + 0.12,
        xerr=1.96 * safety_sd,
        fmt="s",
        color=RED,
        capsize=2.5,
        label="invalidity log-odds",
    )
    ax.axvline(0, color=INK, linestyle="--", linewidth=1)
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_title("Shared posterior coefficients", loc="left")
    ax.set_xlabel("coefficient with 95% marginal interval")
    ax.legend()
    ax = fig.add_subplot(grid[0, 1])
    image = ax.imshow(correlation, vmin=-1, vmax=1, cmap="coolwarm", aspect="auto")
    ax.set_xticks(
        np.arange(len(shared_effect_labels)),
        [label.replace("shared treatment: ", "") for label in shared_effect_labels],
        rotation=35,
        ha="right",
    )
    ax.set_yticks(
        np.arange(len(shared_effect_labels)),
        [label.replace("shared treatment: ", "") for label in shared_effect_labels],
    )
    ax.set_title("Shared treatment coefficient correlation", loc="left")
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    ax = fig.add_subplot(grid[1, 1])
    start = fitted.space.card_effect_slice.start
    card_dim = fitted.space.card_context_dim
    bank_index = fitted.space._bank_index
    card_ids = [
        card_id for card_id, _ in sorted(bank_index.items(), key=lambda row: row[1])
    ]
    means = []
    sds = []
    for card_id in card_ids:
        position = start + bank_index[card_id] * card_dim
        means.append(fitted.reward.mean[position])
        sds.append(math.sqrt(max(fitted.reward.covariance[position, position], 0.0)))
    order = (
        np.argsort(means)[-min(12, len(means)) :]
        if means
        else np.asarray([], dtype=int)
    )
    if len(order):
        yy = np.arange(len(order))
        ax.errorbar(
            np.asarray(means)[order],
            yy,
            xerr=1.96 * np.asarray(sds)[order],
            fmt="o",
            color=PURPLE,
            capsize=2,
        )
        ax.set_yticks(yy, [_short(card_ids[index]) for index in order])
    ax.axvline(0, color=INK, linestyle="--", linewidth=1)
    ax.set_title("Card-lineage intercept deviations", loc="left")
    ax.set_xlabel("latent coefficient")
    _save_figure(fig, paths, "08_hierarchical_coefficients")


def _lineage_frames(data: ReportData) -> tuple[pd.DataFrame, pd.DataFrame]:
    outcomes = pd.DataFrame(
        [row.model_dump(mode="json") for row in data.shadow_outcomes]
    )
    immediate = {row.decision_id: row for row in data.immediate}
    reward = {row.decision_id: row for row in data.shadow_rewards}
    deltas = []
    for decision_id, shadow in reward.items():
        proximal = immediate[decision_id]
        if (
            shadow.invalid
            or proximal.invalid
            or shadow.measurement is None
            or proximal.measurement is None
        ):
            continue
        deltas.append(
            {
                "decision_id": decision_id,
                "ordinal": shadow.event_ordinal,
                "proximal_gain": proximal.measurement.value,
                "lineage_gain": shadow.measurement.value,
                "descendant_lift": shadow.measurement.value
                - proximal.measurement.value,
                "treated": shadow.treatment,
            }
        )
    return outcomes, pd.DataFrame(deltas)


def render_lineage_credit(
    data: ReportData, paths: ReportPaths
) -> tuple[pd.DataFrame, pd.DataFrame]:
    outcomes, deltas = _lineage_frames(data)
    fig = _figure(
        "Opportunity budget and descendant credit",
        f"Shadow endpoint: best valid descendant through depth {data.shadow_depth}, matured after {data.shadow_budget} later opportunities in the root's frozen island.",
    )
    grid = fig.add_gridspec(
        2, 2, left=0.08, right=0.97, top=0.86, bottom=0.10, hspace=0.43, wspace=0.30
    )
    ax = fig.add_subplot(grid[0, 0])
    if not outcomes.empty:
        colors = outcomes["status"].map(
            {"outcome": PURPLE, "invalid": RED, "pending": GOLD, "censored": MUTED}
        )
        ax.scatter(
            outcomes.index,
            outcomes["opportunities_observed"],
            c=colors,
            s=21,
            alpha=0.8,
        )
    ax.axhline(
        data.shadow_budget,
        color=INK,
        linestyle="--",
        linewidth=1,
        label="maturity budget",
    )
    ax.set_title("Local opportunities observed per root", loc="left")
    ax.set_xlabel("proposed-root sequence")
    ax.set_ylabel("opportunities")
    ax.legend()
    ax = fig.add_subplot(grid[0, 1])
    if not outcomes.empty:
        statuses = Counter(outcomes["status"])
        labels = ["outcome", "invalid", "pending", "censored"]
        ax.bar(
            labels,
            [statuses[label] for label in labels],
            color=(PURPLE, RED, GOLD, MUTED),
        )
        for index, label in enumerate(labels):
            ax.text(index, statuses[label] + 0.3, str(statuses[label]), ha="center")
    ax.set_title("Maturity funnel", loc="left")
    ax.tick_params(axis="x", rotation=20)
    ax = fig.add_subplot(grid[1, 0])
    mature = (
        outcomes[outcomes["status"] == "outcome"] if not outcomes.empty else outcomes
    )
    if not mature.empty:
        depths = mature["best_depth"].dropna().astype(int)
        counts = depths.value_counts().sort_index()
        ax.bar(counts.index, counts.values, color=TEAL)
        ax.set_xticks(range(1, data.shadow_depth + 1))
    ax.set_title("Depth of credited best descendant", loc="left")
    ax.set_xlabel("lineage depth")
    ax.set_ylabel("mature roots")
    ax = fig.add_subplot(grid[1, 1])
    if not deltas.empty:
        ax.scatter(
            deltas["proximal_gain"],
            deltas["lineage_gain"],
            c=np.where(deltas["treated"], TEAL, ORANGE),
            s=24,
            alpha=0.7,
        )
        low = min(deltas["proximal_gain"].min(), deltas["lineage_gain"].min())
        high = max(deltas["proximal_gain"].max(), deltas["lineage_gain"].max())
        ax.plot([low, high], [low, high], color=INK, linestyle="--", linewidth=1)
    ax.set_title("Proximal versus credited lineage gain", loc="left")
    ax.set_xlabel("immediate child gain")
    ax.set_ylabel("best descendant gain")
    _save_figure(fig, paths, "09_lineage_opportunity_budget")
    return outcomes, deltas


def render_overlap_sensitivity(data: ReportData, paths: ReportPaths) -> None:
    overlap = data.overlap
    multiplicities = np.asarray(overlap["multiplicities"], dtype=int)
    descendants = overlap["descendants_by_root"]
    roots = list(descendants)
    roots.sort(
        key=lambda decision_id: next(
            row.decision.event_ordinal
            for row in data.rows
            if row.decision.decision_id == decision_id
        )
    )
    roots = roots[: min(45, len(roots))]
    matrix = np.zeros((len(roots), len(roots)))
    for left_index, left in enumerate(roots):
        for right_index, right in enumerate(roots):
            union = descendants[left] | descendants[right]
            matrix[left_index, right_index] = (
                len(descendants[left] & descendants[right]) / len(union)
                if union
                else 0.0
            )
    fig = _figure(
        "Shared-descendant overlap and uncertainty sensitivity",
        "Overlap does not bias the randomized estimand by itself, but an iid likelihood can understate posterior uncertainty.",
    )
    grid = fig.add_gridspec(
        2, 2, left=0.08, right=0.97, top=0.86, bottom=0.10, hspace=0.43, wspace=0.31
    )
    ax = fig.add_subplot(grid[0, 0])
    if multiplicities.size:
        bins = np.arange(0.5, multiplicities.max() + 1.5)
        ax.hist(multiplicities, bins=bins, color=PURPLE, alpha=0.8, rwidth=0.85)
    ax.set_title("How many roots reuse each descendant", loc="left")
    ax.set_xlabel("root multiplicity")
    ax.set_ylabel("unique descendants")
    ax = fig.add_subplot(grid[0, 1])
    if matrix.size:
        image = ax.imshow(matrix, vmin=0, vmax=1, cmap="magma", aspect="auto")
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label="Jaccard overlap")
    ax.set_title("Root-window descendant overlap", loc="left")
    ax.set_xlabel("root sequence")
    ax.set_ylabel("root sequence")
    ax = fig.add_subplot(grid[1, 0])
    summaries = data.bootstrap.attrs.get("summaries", [])
    for index, summary in enumerate(summaries):
        label = summary["endpoint"]
        subset = data.bootstrap[
            (data.bootstrap["endpoint"] == label)
            & data.bootstrap["bootstrap_effect"].notna()
        ]
        values = subset["bootstrap_effect"].to_numpy(dtype=float)
        if not values.size:
            continue
        lower = float(values.min())
        upper = float(values.max())
        padding = max(
            (upper - lower) * 0.05,
            np.finfo(float).eps * max(abs(lower), abs(upper), 1.0) * 100.0,
        )
        ax.hist(
            values,
            bins=45,
            range=(lower - padding, upper + padding),
            density=True,
            alpha=0.35,
            color=COLORS[index],
            label=label,
        )
        ax.axvline(summary["estimate"], color=COLORS[index], linewidth=1.7)
    ax.axvline(0, color=INK, linestyle="--", linewidth=1)
    ax.set_title(
        f"Moving-block DR effect bootstrap (block={data.shadow_budget})", loc="left"
    )
    ax.set_xlabel("offered-minus-withheld effect")
    ax.set_ylabel("density")
    ax.legend(fontsize=8)
    ax = fig.add_subplot(grid[1, 1])
    if summaries:
        labels = [summary["endpoint"] for summary in summaries]
        iid = [summary["iid_se"] for summary in summaries]
        block = [summary["block_se"] for summary in summaries]
        x = np.arange(len(labels))
        ax.bar(x - 0.18, iid, width=0.36, color=BLUE, label="iid SE")
        ax.bar(x + 0.18, block, width=0.36, color=RED, label="moving-block SE")
        ax.set_xticks(x, labels, rotation=15)
    ax.set_title("Dependence sensitivity of uncertainty", loc="left")
    ax.set_ylabel("standard error")
    ax.legend()
    _save_figure(fig, paths, "10_lineage_overlap_sensitivity")


def render_randomization_ope(data: ReportData, paths: ReportPaths) -> None:
    behavior_offer_probability = data.rows[-1].decision.policy.offer_probability
    proposals = [row for row in data.decisions if row["proposed"]]
    frame = pd.DataFrame(proposals)
    active_ope = pd.DataFrame(
        [row for row in data.active_ope if row["endpoint_kind"] == "reward"]
    )
    risk_ope = pd.DataFrame(
        [row for row in data.active_ope if row["endpoint_kind"] == "invalidity"]
    )
    shadow_ope = pd.DataFrame(data.shadow_ope)
    fig = _figure(
        "Randomization integrity and conditional-offer OPE",
        "OPE changes only the offer gate among cards proposed by the logged policy; it does not evaluate a different retrieval or card-selection policy.",
    )
    grid = fig.add_gridspec(
        2, 2, left=0.08, right=0.97, top=0.86, bottom=0.10, hspace=0.43, wspace=0.30
    )
    ax = fig.add_subplot(grid[0, 0])
    if not frame.empty:
        cumulative = frame["delivered"].astype(int).cumsum() / np.arange(
            1, len(frame) + 1
        )
        p = float(frame["offer_probability"].iloc[-1])
        n = np.arange(1, len(frame) + 1)
        radius = 1.96 * np.sqrt(p * (1 - p) / n)
        ax.plot(
            np.arange(1, len(frame) + 1),
            cumulative,
            color=BLUE,
            linewidth=1.8,
            label="realized",
        )
        ax.fill_between(
            np.arange(1, len(frame) + 1),
            np.maximum(0, p - radius),
            np.minimum(1, p + radius),
            color=BLUE,
            alpha=0.12,
            label="95% binomial band",
        )
        ax.axhline(p, color=INK, linestyle="--", linewidth=1)
    ax.set_ylim(0, 1)
    ax.set_title("Cumulative treated fraction", loc="left")
    ax.set_xlabel("proposal count")
    ax.set_ylabel("treated fraction")
    ax.legend(fontsize=8)
    ax = fig.add_subplot(grid[0, 1])
    if not frame.empty:
        probabilities = frame["proposal_probability"].dropna().to_numpy(dtype=float)
        ax.hist(probabilities, bins=25, color=TEAL, alpha=0.8)
    ax.set_title("Logged card proposal propensities", loc="left")
    ax.set_xlabel("proposal probability of selected card")
    ax.set_ylabel("decisions")
    ax = fig.add_subplot(grid[1, 0])
    for table, label, color, style in (
        (active_ope, "immediate reward", BLUE, "-"),
        (shadow_ope, "shadow lineage reward", PURPLE, "--"),
        (risk_ope, "invalidity", RED, ":"),
    ):
        if not table.empty:
            ax.plot(
                table["target_offer_probability"],
                table["estimate"],
                color=color,
                linestyle=style,
                marker="o",
                label=label,
            )
    ax.axvline(
        behavior_offer_probability,
        color=INK,
        linestyle="--",
        linewidth=1,
        alpha=0.6,
        label=f"behavior p={behavior_offer_probability:.2f}",
    )
    ax.set_title("Doubly robust target-offer curve", loc="left")
    ax.set_xlabel("target offer probability")
    ax.set_ylabel("estimated endpoint")
    ax.legend(fontsize=8)
    ax = fig.add_subplot(grid[1, 1])
    if not active_ope.empty:
        ax.plot(
            active_ope["target_offer_probability"],
            active_ope["effective_sample_size"],
            color=BLUE,
            marker="o",
            label="reward ESS",
        )
        ax2 = ax.twinx()
        ax2.plot(
            active_ope["target_offer_probability"],
            active_ope["maximum_importance_weight"],
            color=ORANGE,
            marker="s",
            label="max weight",
        )
        ax2.set_ylabel("maximum importance weight", color=ORANGE)
    ax.set_title("OPE support and weight stability", loc="left")
    ax.set_xlabel("target offer probability")
    ax.set_ylabel("effective sample size", color=BLUE)
    _save_figure(fig, paths, "11_randomization_and_ope")


def _binned_calibration(
    predicted: pd.Series, observed: pd.Series, bins: int = 6
) -> pd.DataFrame:
    frame = pd.DataFrame({"predicted": predicted, "observed": observed}).dropna()
    if frame.empty:
        return frame
    distinct = frame["predicted"].nunique()
    count = max(1, min(bins, distinct))
    frame["bin"] = pd.qcut(frame["predicted"], q=count, duplicates="drop")
    return (
        frame.groupby("bin", observed=False)
        .agg(
            predicted=("predicted", "mean"),
            observed=("observed", "mean"),
            count=("observed", "size"),
            observed_sd=("observed", "std"),
        )
        .reset_index(drop=True)
    )


def _wilson_interval(
    observed: pd.Series, count: pd.Series, *, z: float = 1.96
) -> tuple[np.ndarray, np.ndarray]:
    """Wilson score interval for binomial rates, including all-zero/all-one bins."""

    probability = observed.to_numpy(dtype=float)
    sample_size = count.to_numpy(dtype=float)
    denominator = 1.0 + z * z / sample_size
    center = (probability + z * z / (2.0 * sample_size)) / denominator
    radius = (
        z
        * np.sqrt(
            probability * (1.0 - probability) / sample_size
            + z * z / (4.0 * sample_size * sample_size)
        )
        / denominator
    )
    return center - radius, center + radius


def render_calibration(data: ReportData, paths: ReportPaths) -> None:
    selected = _selected_candidate_frame(data)
    fig = _figure(
        "Prequential calibration and realized residuals",
        "Every prediction was logged before its outcome; calibration is therefore prequential rather than refitted in-sample prediction.",
    )
    grid = fig.add_gridspec(
        2, 2, left=0.08, right=0.97, top=0.86, bottom=0.10, hspace=0.43, wspace=0.30
    )
    ax = fig.add_subplot(grid[0, 0])
    if not selected.empty:
        valid = selected.dropna(subset=["actual_utility", "predicted_realized_utility"])
        ax.scatter(
            valid["predicted_realized_utility"],
            valid["actual_utility"],
            c=np.where(valid["delivered"], TEAL, ORANGE),
            s=18,
            alpha=0.55,
        )
        low = min(
            valid["predicted_realized_utility"].min(), valid["actual_utility"].min()
        )
        high = max(
            valid["predicted_realized_utility"].max(), valid["actual_utility"].max()
        )
        ax.plot([low, high], [low, high], color=INK, linestyle="--", linewidth=1)
    ax.set_title("Predicted versus realized usable utility", loc="left")
    ax.set_xlabel("decision-time posterior mean")
    ax.set_ylabel("realized endpoint")
    ax = fig.add_subplot(grid[0, 1])
    if not selected.empty:
        calibrated = _binned_calibration(
            selected["predicted_realized_invalid"], selected["actual_invalid"]
        )
        if not calibrated.empty:
            lower, upper = _wilson_interval(calibrated["observed"], calibrated["count"])
            center = calibrated["observed"].to_numpy(dtype=float)
            ax.errorbar(
                calibrated["predicted"],
                calibrated["observed"],
                yerr=np.vstack((center - lower, upper - center)),
                fmt="o",
                color=RED,
                capsize=3,
            )
        ax.plot([0, 1], [0, 1], color=INK, linestyle="--", linewidth=1)
    ax.set_xlim(0, max(0.3, ax.get_xlim()[1]))
    ax.set_ylim(0, max(0.3, ax.get_ylim()[1]))
    ax.set_title("Invalidity reliability", loc="left")
    ax.set_xlabel("predicted invalid probability")
    ax.set_ylabel("observed invalid frequency")
    ax = fig.add_subplot(grid[1, 0])
    if not selected.empty:
        valid = selected.dropna(
            subset=["actual_utility", "predicted_realized_utility"]
        ).copy()
        valid["residual"] = (
            valid["actual_utility"] - valid["predicted_realized_utility"]
        )
        ax.scatter(
            valid["ordinal"],
            valid["residual"],
            c=np.where(valid["delivered"], TEAL, ORANGE),
            s=17,
            alpha=0.6,
        )
        ax.plot(
            valid["ordinal"],
            valid["residual"].rolling(25, min_periods=6).mean(),
            color=INK,
            linewidth=1.5,
            label="rolling mean",
        )
    ax.axhline(0, color=INK, linestyle="--", linewidth=1)
    ax.set_title("Reward residual through time", loc="left")
    ax.set_xlabel("decision ordinal")
    ax.set_ylabel("observed - predicted")
    ax.legend()
    ax = fig.add_subplot(grid[1, 1])
    if not selected.empty:
        selected = selected.copy()
        selected["effect_z"] = selected["usable_effect_mean"] / selected[
            "usable_effect_sd"
        ].replace(0, np.nan)
        ax.hist(selected["effect_z"].dropna(), bins=35, color=PURPLE, alpha=0.8)
    ax.axvline(0, color=INK, linestyle="--", linewidth=1)
    ax.set_title("Decision-time posterior effect z-scores", loc="left")
    ax.set_xlabel("posterior mean / posterior SD")
    ax.set_ylabel("selected decisions")
    _save_figure(fig, paths, "12_prequential_calibration")


def render_map_elites(data: ReportData, paths: ReportPaths) -> None:
    records = []
    for row in data.rows:
        context = row.decision.context
        for coordinate in context.map_elites.coordinates:
            records.append(
                {
                    "ordinal": row.decision.event_ordinal,
                    "key": coordinate.key,
                    "raw": coordinate.raw_value,
                    "semantic": coordinate.semantic_normalized,
                    "dynamic": coordinate.dynamic_normalized,
                    "cell": coordinate.cell_index,
                    "bins": coordinate.num_bins,
                    "dynamic_lower": coordinate.dynamic_lower_bound,
                    "dynamic_upper": coordinate.dynamic_upper_bound,
                    "schema": context.map_elites.semantic_schema_hash[:10],
                }
            )
    frame = pd.DataFrame(records)
    keys = list(dict.fromkeys(frame["key"])) if not frame.empty else []
    key = keys[0] if keys else ""
    subset = frame[frame["key"] == key] if key else frame
    fig = _figure(
        "Dynamic MAP-Elites context audit",
        "The posterior consumes stable semantic coordinates; dynamic bin indices and live bounds remain frozen in the ledger for replay and diagnostics.",
    )
    grid = fig.add_gridspec(
        2, 2, left=0.08, right=0.97, top=0.86, bottom=0.10, hspace=0.43, wspace=0.30
    )
    ax = fig.add_subplot(grid[0, 0])
    if not subset.empty:
        ax.plot(subset["ordinal"], subset["raw"], color=BLUE, label="raw parent value")
        ax.plot(
            subset["ordinal"],
            subset["dynamic_lower"],
            color=MUTED,
            linestyle="--",
            label="live lower",
        )
        ax.plot(
            subset["ordinal"],
            subset["dynamic_upper"],
            color=ORANGE,
            linestyle="--",
            label="live upper",
        )
    ax.set_title(f"Raw coordinate and recomputed live bounds: {key}", loc="left")
    ax.set_xlabel("decision ordinal")
    ax.legend(fontsize=8)
    ax = fig.add_subplot(grid[0, 1])
    if not subset.empty:
        ax.plot(
            subset["ordinal"],
            subset["semantic"],
            color=TEAL,
            label="semantic normalized",
        )
        ax.plot(
            subset["ordinal"],
            subset["dynamic"],
            color=PURPLE,
            alpha=0.75,
            label="dynamic normalized",
        )
    ax.set_ylim(-0.03, 1.03)
    ax.set_title("Stable semantic versus drifting dynamic normalization", loc="left")
    ax.set_xlabel("decision ordinal")
    ax.legend(fontsize=8)
    ax = fig.add_subplot(grid[1, 0])
    if not subset.empty:
        ax.step(
            subset["ordinal"],
            subset["cell"],
            where="post",
            color=ORANGE,
            label="live cell index",
        )
        ax2 = ax.twinx()
        ax2.step(
            subset["ordinal"],
            subset["bins"],
            where="post",
            color=INK,
            alpha=0.55,
            label="number of bins",
        )
        ax2.set_ylabel("bins", color=INK)
    ax.set_title("Dynamic cell identity through time", loc="left")
    ax.set_xlabel("decision ordinal")
    ax.set_ylabel("cell index", color=ORANGE)
    ax = fig.add_subplot(grid[1, 1])
    if not subset.empty:
        jitter = np.random.default_rng(7).normal(0, 0.02, len(subset))
        ax.scatter(
            subset["semantic"],
            subset["cell"] + jitter,
            c=subset["ordinal"],
            cmap="viridis",
            s=18,
            alpha=0.65,
        )
    ax.set_title("Same semantic region can cross live cells", loc="left")
    ax.set_xlabel("stable semantic coordinate")
    ax.set_ylabel("dynamic cell index")
    _save_figure(fig, paths, "13_map_elites_dynamic_context")


def render_numerical_health(data: ReportData, paths: ReportPaths) -> None:
    frame = pd.DataFrame(data.decisions)
    fit = data.active_fit
    shadow = data.shadow_fit
    reward_eigen = np.linalg.eigvalsh(fit.reward.covariance)
    safety_eigen = np.linalg.eigvalsh(fit.safety.covariance)
    fig = _figure(
        "Posterior numerical health and uncertainty scale",
        "Convergence, adaptive residual-scale integration, curvature, and covariance spectra are checked independently of policy outcomes.",
    )
    grid = fig.add_gridspec(
        2, 2, left=0.08, right=0.97, top=0.86, bottom=0.10, hspace=0.43, wspace=0.30
    )
    ax = fig.add_subplot(grid[0, 0])
    if not frame.empty:
        ax.plot(
            frame["ordinal"],
            frame["reward_residual_sd"],
            color=BLUE,
            label="reward residual SD",
        )
        ax.plot(
            frame["ordinal"],
            frame["reward_card_effect_sd"],
            color=PURPLE,
            label="card prior SD",
        )
    ax.set_title("Reward scale through prequential fits", loc="left")
    ax.set_xlabel("decision ordinal")
    ax.set_yscale("log")
    ax.legend(fontsize=8)
    ax = fig.add_subplot(grid[0, 1])
    if not frame.empty:
        ax.plot(
            frame["ordinal"],
            frame["safety_gradient_inf"],
            color=GREEN,
            label="gradient infinity norm",
        )
        ax.plot(
            frame["ordinal"],
            frame["safety_hessian_condition"],
            color=RED,
            label="Hessian condition",
        )
    ax.set_yscale("log")
    ax.set_title("Safety MAP/Laplace convergence", loc="left")
    ax.set_xlabel("decision ordinal")
    ax.legend(fontsize=8)
    ax = fig.add_subplot(grid[1, 0])
    ax.plot(
        np.arange(1, len(reward_eigen) + 1),
        np.sort(reward_eigen)[::-1],
        color=BLUE,
        label="reward covariance",
    )
    ax.plot(
        np.arange(1, len(safety_eigen) + 1),
        np.sort(safety_eigen)[::-1],
        color=RED,
        label="safety covariance",
    )
    ax.set_yscale("log")
    ax.set_title("Final posterior covariance eigenvalues", loc="left")
    ax.set_xlabel("ordered eigenvalue")
    ax.set_ylabel("variance")
    ax.legend(fontsize=8)
    ax = fig.add_subplot(grid[1, 1])
    names = ["live reward", "live safety"]
    conditions = [
        float(np.linalg.cond(fit.reward.covariance)),
        float(np.linalg.cond(fit.safety.covariance)),
    ]
    if shadow is not None:
        names.extend(("shadow reward", "shadow safety"))
        conditions.extend(
            (
                float(np.linalg.cond(shadow.reward.covariance)),
                float(np.linalg.cond(shadow.safety.covariance)),
            )
        )
    ax.bar(names, conditions, color=(BLUE, RED, PURPLE, ORANGE)[: len(names)])
    ax.set_yscale("log")
    ax.set_title("Final covariance condition numbers", loc="left")
    ax.tick_params(axis="x", rotation=20)
    _save_figure(fig, paths, "14_numerical_health")


def render_card_dossier(data: ReportData, paths: ReportPaths) -> None:
    frame = data.final_posterior.copy()
    lifecycle = pd.DataFrame(data.lifecycle)
    if not lifecycle.empty:
        frame = frame.merge(lifecycle, on="treatment_id", how="left")
    frame = frame.head(18)
    fig = _figure(
        "Card dossier: posterior value versus randomized support",
        "A high posterior mean without balanced treated/control evidence remains a pooled, prior-sensitive estimate.",
    )
    grid = fig.add_gridspec(
        1, 2, left=0.10, right=0.98, top=0.84, bottom=0.12, wspace=0.36
    )
    ax = fig.add_subplot(grid[0, 0])
    if not frame.empty:
        size = (
            25
            + 12
            * frame.get("balanced_ess", pd.Series(np.zeros(len(frame))))
            .fillna(0)
            .to_numpy()
        )
        scatter = ax.scatter(
            frame["effect_mean"],
            frame["probability_safe_and_helpful"],
            s=size,
            c=frame["probability_helpful"],
            cmap="viridis",
            vmin=0,
            vmax=1,
            alpha=0.75,
            edgecolor="white",
        )
        for _, row in frame.head(10).iterrows():
            ax.annotate(
                _short(row["treatment_id"], 10),
                (row["effect_mean"], row["probability_safe_and_helpful"]),
                xytext=(3, 3),
                textcoords="offset points",
                fontsize=7,
            )
        fig.colorbar(scatter, ax=ax, fraction=0.046, pad=0.04, label="P(helpful)")
    ax.axvline(0, color=INK, linestyle="--", linewidth=1)
    ax.set_title("Value, viability, and evidence volume", loc="left")
    ax.set_xlabel("posterior usable effect mean")
    ax.set_ylabel("P(acceptable and helpful)")
    ax = fig.add_subplot(grid[0, 1])
    if not frame.empty:
        ordered = frame.sort_values("effect_mean")
        y = np.arange(len(ordered))
        ax.errorbar(
            ordered["effect_mean"],
            y,
            xerr=1.96 * ordered["effect_sd"],
            fmt="o",
            color=BLUE,
            capsize=2,
        )
        ax.set_yticks(y, [_short(value) for value in ordered["treatment_id"]])
    ax.axvline(0, color=INK, linestyle="--", linewidth=1)
    ax.set_title("Final live posterior forest", loc="left")
    ax.set_xlabel("mean +/- 1.96 posterior SD")
    _save_figure(fig, paths, "15_card_dossier")


def card_evidence_timing(data: ReportData) -> pd.DataFrame:
    canonical = _current_lineage_ids(data.rows, data.cards)
    terminal_by_decision = {row.decision.decision_id: row.terminal for row in data.rows}
    offers: dict[str, list[int]] = defaultdict(list)
    closed: dict[str, list[int]] = defaultdict(list)
    revisions: dict[str, set[str]] = defaultdict(set)
    arms: dict[str, Counter[str]] = defaultdict(Counter)
    for ledger_row in data.rows:
        decision = ledger_row.decision
        treatment_id = decision.proposed_treatment_id
        if treatment_id is None:
            continue
        stable = canonical.get(treatment_id, treatment_id)
        offers[stable].append(decision.event_ordinal)
        card = next(
            candidate
            for candidate in decision.candidates
            if candidate.treatment_id == treatment_id
        )
        revisions[stable].add(card.payload_sha256)
        terminal = terminal_by_decision[decision.decision_id]
        if (
            terminal is not None
            and terminal.ope_eligible
            and terminal.status != "censored"
        ):
            closed[stable].append(decision.event_ordinal)
            arms[stable]["treated" if decision.delivered else "control"] += 1
    lifecycle = {row["treatment_id"]: row for row in data.lifecycle}
    last_ordinal = max((row.decision.event_ordinal for row in data.rows), default=0)
    result = []
    for treatment_id, ordinals in sorted(offers.items()):
        closed_ordinals = sorted(closed[treatment_id])
        half_ordinal = (
            closed_ordinals[(len(closed_ordinals) - 1) // 2]
            if closed_ordinals
            else None
        )
        life = lifecycle.get(treatment_id, {})
        result.append(
            {
                "treatment_id": treatment_id,
                "first_offer_ordinal": min(ordinals),
                "last_offer_ordinal": max(ordinals),
                "offer_span": max(ordinals) - min(ordinals),
                "offers": len(ordinals),
                "closed_evidence": len(closed_ordinals),
                "evidence_half_ordinal": half_ordinal,
                "evidence_accumulation_half_time": (
                    half_ordinal - min(ordinals) if half_ordinal is not None else None
                ),
                "evidence_age_at_end": (
                    last_ordinal - max(closed_ordinals)
                    if closed_ordinals
                    else last_ordinal - min(ordinals)
                ),
                "payload_revisions": len(revisions[treatment_id]),
                "treated": arms[treatment_id]["treated"],
                "control": arms[treatment_id]["control"],
                "balanced_ess": life.get("balanced_ess"),
                "cold_start_randomized_h50": life.get("randomized_evidence_h50"),
                "support_ready": bool(life.get("support_ready")),
            }
        )
    return pd.DataFrame(result)


def render_evidence_persistence(data: ReportData, paths: ReportPaths) -> pd.DataFrame:
    frame = card_evidence_timing(data)
    fig = _figure(
        "Randomized-evidence persistence and cold-start pressure",
        "Evidence is pooled by stable card lineage across payload-preserving revisions; half-time measures accumulation, not exponential decay.",
    )
    grid = fig.add_gridspec(
        2,
        2,
        left=0.08,
        right=0.97,
        top=0.86,
        bottom=0.10,
        hspace=0.43,
        wspace=0.30,
    )
    ax = fig.add_subplot(grid[0, 0])
    if not frame.empty:
        ordered = frame.sort_values("first_offer_ordinal").reset_index(drop=True)
        y = np.arange(len(ordered))
        for index, row in ordered.iterrows():
            color = GREEN if row["support_ready"] else MUTED
            ax.plot(
                [row["first_offer_ordinal"], row["last_offer_ordinal"]],
                [index, index],
                color=color,
                linewidth=2.3,
            )
            ax.scatter(row["first_offer_ordinal"], index, color=BLUE, s=15)
            ax.scatter(row["last_offer_ordinal"], index, color=color, s=15)
        ax.set_yticks(y, [_short(value) for value in ordered["treatment_id"]])
    ax.set_title("Observed offer lifetime by card lineage", loc="left")
    ax.set_xlabel("decision ordinal")
    ax = fig.add_subplot(grid[0, 1])
    if not frame.empty:
        ready = frame["support_ready"]
        ax.scatter(
            frame.loc[~ready, "offers"],
            frame.loc[~ready, "evidence_accumulation_half_time"],
            color=MUTED,
            alpha=0.7,
            label="not support-ready",
        )
        ax.scatter(
            frame.loc[ready, "offers"],
            frame.loc[ready, "evidence_accumulation_half_time"],
            color=GREEN,
            alpha=0.85,
            label="support-ready",
        )
    ax.set_title("Time to accumulate half of final evidence", loc="left")
    ax.set_xlabel("final offers")
    ax.set_ylabel("decision ordinals from first offer")
    ax.legend(fontsize=8)
    ax = fig.add_subplot(grid[1, 0])
    if not frame.empty:
        ax.scatter(
            frame["evidence_age_at_end"],
            frame["balanced_ess"],
            c=frame["payload_revisions"],
            cmap="viridis",
            s=42,
            alpha=0.8,
        )
    ax.set_title("Evidence age, ESS, and payload revisions", loc="left")
    ax.set_xlabel("decisions since last closed evidence")
    ax.set_ylabel("balanced randomized ESS")
    ax = fig.add_subplot(grid[1, 1])
    if not frame.empty:
        finite = frame.dropna(subset=["cold_start_randomized_h50"])
        ax.scatter(
            finite["offers"],
            finite["cold_start_randomized_h50"],
            c=np.where(finite["support_ready"], GREEN, ORANGE),
            s=38,
            alpha=0.75,
        )
        ax.axhline(
            data.shadow_budget,
            color=PURPLE,
            linestyle="--",
            linewidth=1,
            label=f"lineage K={data.shadow_budget}",
        )
    ax.set_yscale("log")
    ax.set_title("Cold-start opportunities to balanced 2+2 support (H50)", loc="left")
    ax.set_xlabel("offers observed")
    ax.set_ylabel("opportunities from zero evidence")
    ax.legend(fontsize=8)
    _save_figure(fig, paths, "16_evidence_persistence")
    return frame


def _bootstrap_summary(data: ReportData, endpoint: str) -> dict[str, Any]:
    for row in data.bootstrap.attrs.get("summaries", []):
        if row["endpoint"] == endpoint:
            return row
    return {}


def _prequential_metrics(data: ReportData) -> dict[str, Any]:
    selected = _selected_candidate_frame(data).dropna(
        subset=[
            "actual_utility",
            "actual_invalid",
            "predicted_realized_utility",
            "predicted_realized_invalid",
        ]
    )
    if selected.empty:
        return {}

    def arm_metrics(frame: pd.DataFrame) -> dict[str, Any]:
        return {
            "observations": len(frame),
            "mean_utility": float(frame["actual_utility"].mean()),
            "invalid_rate": float(frame["actual_invalid"].mean()),
            "mean_predicted_utility": float(frame["predicted_realized_utility"].mean()),
            "mean_predicted_invalid": float(frame["predicted_realized_invalid"].mean()),
        }

    treated = selected[selected["delivered"].astype(bool)]
    control = selected[~selected["delivered"].astype(bool)]
    utility_se = math.sqrt(
        float(treated["actual_utility"].var(ddof=1)) / max(len(treated), 1)
        + float(control["actual_utility"].var(ddof=1)) / max(len(control), 1)
    )
    invalid_se = math.sqrt(
        float(treated["actual_invalid"].var(ddof=1)) / max(len(treated), 1)
        + float(control["actual_invalid"].var(ddof=1)) / max(len(control), 1)
    )
    predicted_invalid = selected["predicted_realized_invalid"]
    actual_invalid = selected["actual_invalid"]
    predicted_utility = selected["predicted_realized_utility"]
    actual_utility = selected["actual_utility"]
    return {
        "observations": len(selected),
        "treated": arm_metrics(treated),
        "control": arm_metrics(control),
        "raw_utility_difference": float(
            treated["actual_utility"].mean() - control["actual_utility"].mean()
        ),
        "raw_utility_naive_se": utility_se,
        "raw_invalid_rate_difference": float(
            treated["actual_invalid"].mean() - control["actual_invalid"].mean()
        ),
        "raw_invalid_naive_se": invalid_se,
        "mean_predicted_invalid": float(predicted_invalid.mean()),
        "realized_invalid_rate": float(actual_invalid.mean()),
        "invalidity_underprediction": float(
            actual_invalid.mean() - predicted_invalid.mean()
        ),
        "invalidity_brier_score": float(
            np.mean((predicted_invalid - actual_invalid) ** 2)
        ),
        "reward_rmse": float(
            np.sqrt(np.mean((predicted_utility - actual_utility) ** 2))
        ),
        "reward_prediction_bias": float(np.mean(predicted_utility - actual_utility)),
    }


def _report_metrics(data: ReportData) -> dict[str, Any]:
    search = _search_frame(data)
    proposals = [row for row in data.decisions if row["proposed"]]
    support_ready = sum(bool(row["support_ready"]) for row in data.lifecycle)
    active_bootstrap = _bootstrap_summary(data, "Immediate D=1")
    shadow_bootstrap = _bootstrap_summary(
        data, f"Shadow D={data.shadow_depth}, K={data.shadow_budget}"
    )
    statuses = Counter(
        row.terminal.status if row.terminal is not None else "pending"
        for row in data.rows
    )
    shadow_statuses = Counter(row.status for row in data.shadow_outcomes)
    write_counts = Counter(
        str(row.get("outcome", "unknown")) for row in data.write_rows
    )
    initial_best = _initial_best_fitness(data)
    final_best = float(search["best_fitness"].iloc[-1])
    higher = data.rows[0].decision.context.reward.higher_is_better
    search_gain = final_best - initial_best if higher else initial_best - final_best
    live_numerically_healthy = bool(
        data.active_fit.reward.optimizer_success
        and not data.active_fit.reward.hyperparameters_at_boundary
        and data.active_fit.safety.gradient_norm <= 1e-4
        and data.active_fit.safety.hessian_condition <= 1e12
    )
    ledger_healthy = not data.audit.errors and data.integrity == "ok"
    closed = statuses["pending"] == 0
    treated = sum(bool(row["delivered"]) for row in proposals)
    control = len(proposals) - treated
    eligible_treated = sum(row.treatment for row in data.immediate)
    eligible_control = len(data.immediate) - eligible_treated
    randomized_support_ready = eligible_treated >= 10 and eligible_control >= 10
    expected_ope_grid = {
        (kind, target)
        for kind in ("reward", "invalidity")
        for target in (0.0, 0.25, 0.5, 0.75, 1.0)
    }
    actual_ope_grid = {
        (str(row.get("endpoint_kind")), float(row.get("target_offer_probability")))
        for row in data.active_ope
    }
    expected_ope_counts = {
        "reward": len(data.active_rewards),
        "invalidity": len(data.immediate),
    }
    policy_offers = {row.decision.policy.offer_probability for row in data.rows}
    observation_offers = {row.offer_propensity for row in data.immediate}
    ope_complete = bool(
        data.active_ope_error is None
        and actual_ope_grid == expected_ope_grid
        and all(
            int(row.get("observations", -1))
            == expected_ope_counts[str(row.get("endpoint_kind"))]
            for row in data.active_ope
        )
        and len(policy_offers) == 1
        and observation_offers == policy_offers
    )
    posterior_config_hashes = {row.decision.posterior_config_hash for row in data.rows}
    posterior_config_matches = posterior_config_hashes == {
        data.posterior_model.model_config_hash
    }
    ledger_config_contract = _ledger_config_contract(data.config, data.rows)
    writer_bank_matches = bool(
        data.writer_trace.attrs.get(
            "matches_final_bank", not data.write_rows and not data.cards
        )
    )
    overlap_material = data.overlap["reused_descendants"] > 0
    timing = card_evidence_timing(data)
    support_timing = (
        timing[timing["support_ready"].astype(bool)] if not timing.empty else timing
    )
    prequential = _prequential_metrics(data)
    material_risk_underprediction = (
        _finite(prequential.get("invalidity_underprediction"), 0.0) > 0.05
    )
    decisions_with_candidates = [
        row for row in data.decisions if row["candidate_count"] > 0
    ]
    trailing_safety_lockout = 0
    for row in reversed(data.decisions):
        if row["candidate_count"] == 0:
            break
        if row["safe_count"] > 0:
            break
        trailing_safety_lockout += 1
    safety_lockout_decisions = sum(
        row["safe_count"] == 0 for row in decisions_with_candidates
    )
    support_accumulated = support_ready >= 1
    sustained_lockout_absent = (
        trailing_safety_lockout <= MAX_TRAILING_SAFETY_LOCKOUT_DECISIONS
    )
    readiness_gates = {
        "ledger integrity": ledger_healthy,
        "posterior numerics": live_numerically_healthy,
        "terminal closure": closed,
        "randomized arm support": randomized_support_ready,
        "OPE completeness": ope_complete,
        "posterior configuration": posterior_config_matches,
        "ledger configuration": all(ledger_config_contract.values()),
        "writer-bank reconciliation": writer_bank_matches,
        "lineage evidence accumulation": support_accumulated,
        "absence of sustained safety lockout": sustained_lockout_absent,
    }
    failed_readiness_gates = tuple(
        name for name, passed in readiness_gates.items() if not passed
    )
    depth1_ready = not failed_readiness_gates
    lineage_outcomes, descendant_deltas = _lineage_frames(data)
    matured_shadow_roots = shadow_statuses["outcome"] + shadow_statuses["invalid"]
    outcome_roots = (
        lineage_outcomes[lineage_outcomes["status"] == "outcome"]
        if not lineage_outcomes.empty
        else lineage_outcomes
    )
    depth_gt_one_roots = (
        int((outcome_roots["best_depth"] > 1).sum()) if not outcome_roots.empty else 0
    )
    positive_descendant_lift = (
        int((descendant_deltas["descendant_lift"] > 0).sum())
        if not descendant_deltas.empty
        else 0
    )
    llm_summary = _llm_resource_summary(data.llm_calls)
    writer_llm = (
        llm_summary[llm_summary["writer_call"]]
        if not llm_summary.empty
        else llm_summary
    )
    total_llm_tokens = (
        int(llm_summary["total_tokens"].sum()) if not llm_summary.empty else 0
    )
    writer_llm_tokens = (
        int(writer_llm["total_tokens"].sum()) if not writer_llm.empty else 0
    )
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "run_root": str(data.run_root),
        "ledger": str(data.ledger),
        "audit_input_sha256": {
            str(path.relative_to(data.run_root)): _sha256_file(path)
            for path in _audit_input_paths(data.run_root, data.ledger)
        },
        "sqlite_integrity": data.integrity,
        "ledger_audit_passed": ledger_healthy,
        "audit_errors": list(data.audit.errors),
        "audit_warnings": list(data.audit.warnings),
        "decisions": len(data.rows),
        "proposals": len(proposals),
        "treated": treated,
        "control": control,
        "eligible_ope_treated": eligible_treated,
        "eligible_ope_control": eligible_control,
        "abstentions": len(data.rows) - len(proposals),
        "decisions_with_candidates": len(decisions_with_candidates),
        "safety_lockout_decisions": safety_lockout_decisions,
        "trailing_safety_lockout_decisions": trailing_safety_lockout,
        "terminal_statuses": dict(statuses),
        "live_reward_observations": len(data.active_rewards),
        "shadow_reward_observations": len(data.shadow_rewards),
        "shadow_statuses": dict(shadow_statuses),
        "shadow_depth": data.shadow_depth,
        "shadow_budget": data.shadow_budget,
        "bank_cards": len(data.cards),
        "writer_events": len(data.write_rows),
        "writer_outcomes": dict(write_counts),
        "writer_bank_matches_final": writer_bank_matches,
        "posterior_config_matches_ledger": posterior_config_matches,
        "policy_config_matches_ledger": ledger_config_contract["policy"],
        "candidate_universe_config_matches_ledger": ledger_config_contract[
            "candidate_universe"
        ],
        "applicability_config_matches_ledger": ledger_config_contract["applicability"],
        "run_seed_matches_ledger": ledger_config_contract["run_seed"],
        "posterior_config_hashes": sorted(posterior_config_hashes),
        "refit_posterior_config_hash": data.posterior_model.model_config_hash,
        "randomized_support_ready": randomized_support_ready,
        "ope_complete": ope_complete,
        "ope_error": data.active_ope_error,
        "ope_reports": len(data.active_ope),
        "ope_expected_observations": expected_ope_counts,
        "llm_log_segments": (
            int(data.llm_calls["log_segment"].nunique())
            if not data.llm_calls.empty
            else 0
        ),
        "llm_calls": int(llm_summary["calls"].sum()) if not llm_summary.empty else 0,
        "llm_tokens": total_llm_tokens,
        "llm_provider_latency_seconds": (
            float(llm_summary["provider_latency_seconds"].sum())
            if not llm_summary.empty
            else 0.0
        ),
        "llm_failures": int(llm_summary["failures"].sum())
        if not llm_summary.empty
        else 0,
        "writer_llm_calls": (
            int(writer_llm["calls"].sum()) if not writer_llm.empty else 0
        ),
        "writer_llm_tokens": writer_llm_tokens,
        "writer_llm_token_fraction": (
            writer_llm_tokens / total_llm_tokens if total_llm_tokens else 0.0
        ),
        "stable_card_lineages_with_offers": len(data.lifecycle),
        "support_ready_card_lineages": support_ready,
        "support_accumulated": support_accumulated,
        "max_trailing_safety_lockout_decisions": (
            MAX_TRAILING_SAFETY_LOCKOUT_DECISIONS
        ),
        "sustained_safety_lockout_absent": sustained_lockout_absent,
        "prequential_calibration": prequential,
        "material_safety_risk_underprediction": material_risk_underprediction,
        "median_evidence_accumulation_half_time": (
            float(timing["evidence_accumulation_half_time"].dropna().median())
            if not timing.empty
            and not timing["evidence_accumulation_half_time"].dropna().empty
            else None
        ),
        "support_ready_median_evidence_accumulation_half_time": (
            float(support_timing["evidence_accumulation_half_time"].dropna().median())
            if not support_timing.empty
            and not support_timing["evidence_accumulation_half_time"].dropna().empty
            else None
        ),
        "median_cold_start_randomized_h50": (
            float(timing["cold_start_randomized_h50"].dropna().median())
            if not timing.empty
            and not timing["cold_start_randomized_h50"].dropna().empty
            else None
        ),
        "shadow_matured_roots": matured_shadow_roots,
        "shadow_pending_roots": shadow_statuses["pending"],
        "shadow_censored_roots": shadow_statuses["censored"],
        "shadow_outcome_roots": shadow_statuses["outcome"],
        "shadow_best_depth_gt_1_roots": depth_gt_one_roots,
        "shadow_best_depth_gt_1_fraction": (
            depth_gt_one_roots / len(outcome_roots) if len(outcome_roots) else None
        ),
        "descendant_lift_observations": len(descendant_deltas),
        "positive_descendant_lift_observations": positive_descendant_lift,
        "positive_descendant_lift_fraction": (
            positive_descendant_lift / len(descendant_deltas)
            if len(descendant_deltas)
            else None
        ),
        "median_descendant_lift": (
            float(descendant_deltas["descendant_lift"].median())
            if not descendant_deltas.empty
            else None
        ),
        "initial_best_fitness": initial_best,
        "final_best_fitness": final_best,
        "search_gain": search_gain,
        "reward_residual_sd": data.active_fit.reward.residual_sd,
        "reward_observations": data.active_fit.reward.observations,
        "safety_observations": data.active_fit.safety.observations,
        "reward_optimizer_success": data.active_fit.reward.optimizer_success,
        "reward_hyperparameters_at_boundary": data.active_fit.reward.hyperparameters_at_boundary,
        "safety_gradient_inf": data.active_fit.safety.gradient_norm,
        "safety_hessian_condition": data.active_fit.safety.hessian_condition,
        "overlap": {
            key: value
            for key, value in data.overlap.items()
            if key
            in {
                "roots",
                "unique_descendants",
                "descendant_assignments",
                "reused_descendants",
                "maximum_multiplicity",
                "mean_multiplicity",
                "overlap_components",
                "largest_overlap_component",
            }
        },
        "active_block_sensitivity": active_bootstrap,
        "shadow_block_sensitivity": shadow_bootstrap,
        "depth1_core_ready": depth1_ready,
        "failed_readiness_gates": failed_readiness_gates,
        "depth1_efficacy_identified": False,
        "depth_gt_1_online_ready": False,
        "verdict": (
            "Core mechanics passed; default safety gate is not calibrated and efficacy is not established"
            if depth1_ready and material_risk_underprediction
            else "Depth-1 mechanics ready for guarded experiments; safety calibration and efficacy not established"
            if depth1_ready
            else "Depth-1 core not ready; failed gates: "
            + ", ".join(failed_readiness_gates)
        ),
        "shadow_verdict": (
            "Shadow-only: shared descendant overlap invalidates iid calibration"
            if overlap_material
            else "No descendant reuse observed, but one trajectory is insufficient for online promotion"
        ),
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, Path):
        return str(value)
    return value


def export_tables(
    data: ReportData,
    paths: ReportPaths,
    contextual: pd.DataFrame,
    lineage_outcomes: pd.DataFrame,
    lineage_deltas: pd.DataFrame,
    evidence_timing: pd.DataFrame,
) -> dict[str, Any]:
    paths.table_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(data.decisions).to_csv(
        paths.table_dir / "decision_trace.csv", index=False
    )
    pd.DataFrame(data.candidate_rows).to_csv(
        paths.table_dir / "candidate_posterior_trace.csv", index=False
    )
    pd.DataFrame(data.terminal_rows).to_csv(
        paths.table_dir / "terminal_trace.csv", index=False
    )
    pd.DataFrame(data.lifecycle).to_csv(
        paths.table_dir / "card_evidence_lifecycle.csv", index=False
    )
    data.final_posterior.to_csv(
        paths.table_dir / "live_final_posterior.csv", index=False
    )
    data.shadow_final_posterior.to_csv(
        paths.table_dir / "shadow_final_posterior.csv", index=False
    )
    contextual.to_csv(paths.table_dir / "contextual_posterior_grid.csv", index=False)
    lineage_outcomes.to_csv(
        paths.table_dir / "shadow_lineage_outcomes.csv", index=False
    )
    lineage_deltas.to_csv(paths.table_dir / "shadow_descendant_lift.csv", index=False)
    data.writer_trace.to_csv(paths.table_dir / "writer_lifecycle.csv", index=False)
    data.llm_calls.to_csv(paths.table_dir / "llm_call_trace.csv", index=False)
    _llm_resource_summary(data.llm_calls).to_csv(
        paths.table_dir / "llm_resource_summary.csv", index=False
    )
    evidence_timing.to_csv(paths.table_dir / "card_evidence_timing.csv", index=False)
    bootstrap_values = (
        data.bootstrap[data.bootstrap["bootstrap_effect"].notna()]
        if not data.bootstrap.empty
        else data.bootstrap
    )
    bootstrap_values.to_csv(paths.table_dir / "block_bootstrap_draws.csv", index=False)
    overlap_rows = []
    for descendant, roots in data.overlap["roots_by_descendant"].items():
        overlap_rows.append(
            {
                "descendant_id": descendant,
                "root_count": len(roots),
                "root_decision_ids": "|".join(sorted(roots)),
            }
        )
    pd.DataFrame(overlap_rows).to_csv(
        paths.table_dir / "descendant_overlap.csv", index=False
    )
    pd.DataFrame(data.active_ope).to_csv(paths.table_dir / "live_ope.csv", index=False)
    pd.DataFrame(data.shadow_ope).to_csv(
        paths.table_dir / "shadow_reward_ope.csv", index=False
    )
    penalty_rows, penalty_summary = invalid_penalty_sensitivity(
        data.decisions, data.candidate_rows
    )
    pd.DataFrame(penalty_rows).to_csv(
        paths.table_dir / "invalid_penalty_sensitivity.csv", index=False
    )
    metrics = _report_metrics(data)
    metrics["invalid_penalty_sensitivity"] = penalty_summary
    (paths.output_dir / "report_metrics.json").write_text(
        json.dumps(_jsonable(metrics), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return metrics


def _fmt(value: Any, digits: int = 3) -> str:
    number = _finite(value)
    if not math.isfinite(number):
        return "n/a"
    if number != 0 and (abs(number) < 10 ** (-digits) or abs(number) >= 10_000):
        return f"{number:.2e}"
    return f"{number:.{digits}f}"


def _simple_table(
    headers: Sequence[str], rows: Sequence[Sequence[Any]], widths: str | None = None
) -> str:
    column_spec = widths or ("l" * len(headers))
    lines = [r"\begin{center}", rf"\begin{{tabular}}{{{column_spec}}}", r"\toprule"]
    lines.append(" & ".join(_tex(value) for value in headers) + r" \\")
    lines.append(r"\midrule")
    for row in rows:
        lines.append(" & ".join(_tex(value) for value in row) + r" \\")
    lines.extend((r"\bottomrule", r"\end{tabular}", r"\end{center}"))
    return "\n".join(lines)


def _figure_tex(name: str, caption: str, label: str) -> str:
    return "\n".join(
        (
            r"\begin{figure}[htbp]",
            r"\centering",
            rf"\includegraphics[width=\textwidth]{{figures/{name}.pdf}}",
            rf"\caption{{{_tex(caption)}}}",
            rf"\label{{fig:{label}}}",
            r"\end{figure}",
        )
    )


def _top_card_table(data: ReportData, limit: int = 12) -> str:
    frame = data.final_posterior.head(limit)
    rows = []
    lifecycle = {row["treatment_id"]: row for row in data.lifecycle}
    for _, row in frame.iterrows():
        support = lifecycle.get(row["treatment_id"], {})
        rows.append(
            (
                _short(row["treatment_id"]),
                _fmt(row["effect_mean"]),
                _fmt(row["effect_sd"]),
                _fmt(row["probability_helpful"], 2),
                _fmt(row["probability_safe"], 2),
                int(support.get("treated", 0)),
                int(support.get("control", 0)),
                "yes" if support.get("support_ready") else "no",
            )
        )
    return _simple_table(
        ("card", "effect", "SD", "P(help)", "P(accept)", "T", "C", "support"),
        rows,
        "lrrrrrrl",
    )


def _card_appendix(data: ReportData) -> str:
    lines = [
        r"\begin{longtable}{p{0.20\textwidth}p{0.73\textwidth}}",
        r"\toprule",
        r"Card lineage & Current delivered advice \\",
        r"\midrule",
        r"\endfirsthead",
        r"\toprule",
        r"Card lineage & Current delivered advice \\",
        r"\midrule",
        r"\endhead",
    ]
    for card in data.cards:
        description = data.card_descriptions.get(card.treatment_id, card.payload)
        description = textwrap.shorten(
            _ascii(description).replace("\n", " "), width=520, placeholder=" ..."
        )
        lines.append(
            rf"\texttt{{{_tex(_short(card.treatment_id, 18))}}} & {_tex(description)} \\"
        )
        lines.append(r"\addlinespace")
    lines.extend((r"\bottomrule", r"\end{longtable}"))
    return "\n".join(lines)


def build_tex(data: ReportData, metrics: dict[str, Any], paths: ReportPaths) -> None:
    task = data.rows[0].decision.context.environment.task_key
    environment = data.rows[0].decision.context.environment
    policy = data.rows[-1].decision.policy
    reward = data.rows[-1].decision.context.reward
    agentic_retrieval = any(
        row.decision.applicability.specification.name == "agentic_research"
        for row in data.rows
    )
    candidate_selection_step = (
        "Enumerate the full eligible bank and use one LLM research pass only to "
        "emit a frozen applicability label whose effect is learned from outcomes."
        if agentic_retrieval
        else "Enumerate the whole eligible task bank after lineage exclusion; no "
        "LLM retriever or lexical prefilter is used."
    )
    active_bootstrap = metrics.get("active_block_sensitivity", {})
    overlap = metrics["overlap"]
    support_fraction = metrics["support_ready_card_lineages"] / max(
        metrics["stable_card_lineages_with_offers"], 1
    )
    calibration = metrics.get("prequential_calibration", {})
    treated_observed = calibration.get("treated", {})
    control_observed = calibration.get("control", {})
    live_verdict_color = (
        "AuditPurple"
        if metrics["depth1_core_ready"]
        and metrics["material_safety_risk_underprediction"]
        else ("AuditGreen" if metrics["depth1_core_ready"] else "AuditRed")
    )
    efficacy_sentence = (
        "The moving-block interval is entirely positive, which is supportive but still not a full-policy causal comparison."
        if active_bootstrap and _finite(active_bootstrap.get("lower")) > 0
        else (
            "The moving-block interval is entirely negative, so this run gives a concrete warning that offering the selected cards may have hurt the immediate endpoint."
            if active_bootstrap and _finite(active_bootstrap.get("upper")) < 0
            else "The moving-block interval crosses zero; this trajectory does not establish that offering selected cards improves immediate utility."
        )
    )
    shadow_sentence = (
        f"{overlap['reused_descendants']} descendants are reused by multiple roots, with maximum multiplicity {overlap['maximum_multiplicity']}. "
        "The shadow working-likelihood posterior is therefore descriptive, not calibrated for online Thompson decisions."
        if overlap["reused_descendants"]
        else "No literal descendant reuse was observed, but adjacent windows still share trajectory shocks and one run cannot validate online calibration."
    )
    lineage_sentence = (
        f"The shadow funnel contains {metrics['shadow_matured_roots']} matured, "
        f"{metrics['shadow_pending_roots']} pending, and "
        f"{metrics['shadow_censored_roots']} censored roots. Among "
        f"{metrics['shadow_outcome_roots']} valid matured roots, "
        f"{metrics['shadow_best_depth_gt_1_roots']} achieved their best endpoint deeper "
        f"than the immediate child "
        f"({metrics['shadow_best_depth_gt_1_fraction']:.1%}). "
        f"Positive descendant lift occurred in "
        f"{metrics['positive_descendant_lift_observations']}/"
        f"{metrics['descendant_lift_observations']} comparable roots; median lift was "
        f"{_fmt(metrics['median_descendant_lift'], 4)}."
    )
    invalidity_error = _finite(calibration.get("invalidity_underprediction"))
    if not calibration:
        calibration_sentence = (
            "No closed prequential rows were available for calibration."
        )
    elif invalidity_error > 0.05:
        calibration_sentence = (
            f"Decision-time invalidity predictions averaged {_fmt(calibration.get('mean_predicted_invalid'), 3)}, "
            f"while realized invalidity was {_fmt(calibration.get('realized_invalid_rate'), 3)}. "
            f"The {_fmt(invalidity_error, 3)} absolute underprediction is material: "
            "optimizer convergence did not produce calibrated safety probabilities."
        )
    elif invalidity_error < -0.05:
        calibration_sentence = (
            f"Decision-time invalidity predictions averaged {_fmt(calibration.get('mean_predicted_invalid'), 3)}, "
            f"while realized invalidity was {_fmt(calibration.get('realized_invalid_rate'), 3)}. "
            f"The {_fmt(-invalidity_error, 3)} absolute overprediction made the gate conservative."
        )
    else:
        calibration_sentence = (
            f"Decision-time invalidity predictions averaged {_fmt(calibration.get('mean_predicted_invalid'), 3)}, "
            f"versus {_fmt(calibration.get('realized_invalid_rate'), 3)} realized; aggregate error was small, "
            "although one trajectory cannot establish calibration."
        )
    raw_utility = _finite(calibration.get("raw_utility_difference"))
    raw_invalidity = _finite(calibration.get("raw_invalid_rate_difference"))
    if raw_utility > 0 and raw_invalidity <= 0:
        randomized_direction = "Both raw endpoint directions favored treatment, without establishing significance."
    elif raw_utility < 0 and raw_invalidity >= 0:
        randomized_direction = "Both raw endpoint directions disfavored treatment."
    else:
        randomized_direction = "The raw utility and invalidity directions were mixed."
    treated_invalidity = _finite(treated_observed.get("invalid_rate"))
    control_invalidity = _finite(control_observed.get("invalid_rate"))
    if policy.safety_gate_mode == "exclude_confident_incremental_harm":
        arm_safety_sentence = (
            f"Treated offers realized {_fmt(treated_invalidity, 3)} invalidity versus "
            f"{_fmt(control_invalidity, 3)} for withheld controls. The default gate "
            "does not impose a task-independent absolute invalidity ceiling; it "
            f"screens for incremental invalidity above "
            f"{policy.max_incremental_invalid_probability:.3f}."
        )
        gate_selection_step = (
            "Admit a card unless the posterior is at least "
            f"{1.0 - policy.safety_alpha:.0%} confident that it increases invalidity "
            f"by more than {policy.max_incremental_invalid_probability:.2f}."
        )
    else:
        absolute_limit = policy.max_treated_invalid_probability
        if absolute_limit is None:
            raise ValueError("legacy joint-safe policy lacks its absolute limit")
        treated_limit_relation = (
            "below" if treated_invalidity <= absolute_limit else "above"
        )
        arm_safety_sentence = (
            f"Treated offers realized {_fmt(treated_invalidity, 3)} invalidity versus "
            f"{_fmt(control_invalidity, 3)} for withheld controls. The treated arm was "
            f"{treated_limit_relation} the configured absolute limit of "
            f"{absolute_limit:.3f}."
        )
        gate_selection_step = (
            "Admit a card only when the joint posterior probability of treated "
            f"invalidity at most {absolute_limit:.2f} and incremental invalidity at "
            f"most {policy.max_incremental_invalid_probability:.2f} is at least "
            f"{1.0 - policy.safety_alpha:.0%}."
        )
    lockout_sentence = (
        f"Among {metrics['decisions_with_candidates']} decisions with a nonempty candidate bank, "
        f"{metrics['safety_lockout_decisions']} had no admitted card; the run ended with "
        f"{metrics['trailing_safety_lockout_decisions']} consecutive admission lockouts."
    )
    run_table = _simple_table(
        ("field", "value"),
        (
            ("task", task),
            ("LLM", environment.llm.model_name),
            ("mutation", qualified_class_name(environment.mutation_operator)),
            ("pipeline", environment.pipeline),
            ("algorithm", environment.algorithm),
            ("decisions", metrics["decisions"]),
            ("live endpoint", f"{reward.endpoint}, D={reward.lineage_depth}"),
            (
                "shadow endpoint",
                f"best descendant, D={data.shadow_depth}, K={data.shadow_budget}",
            ),
            ("offer probability", _fmt(policy.offer_probability, 2)),
            ("proposal exploration", _fmt(policy.proposal_exploration_probability, 2)),
            ("max pending per card", policy.max_pending_per_card),
            ("bank cap", "none for v2 insight bank"),
        ),
        "p{0.28\\textwidth}p{0.62\\textwidth}",
    )
    accounting_table = _simple_table(
        ("quantity", "count"),
        (
            ("ledger decisions", metrics["decisions"]),
            ("card proposals", metrics["proposals"]),
            ("treated offers", metrics["treated"]),
            ("withheld controls", metrics["control"]),
            ("abstentions", metrics["abstentions"]),
            ("live reward rows", metrics["live_reward_observations"]),
            (
                "raw treated-control utility",
                _fmt(calibration.get("raw_utility_difference"), 3),
            ),
            (
                "raw treated-control invalidity",
                _fmt(calibration.get("raw_invalid_rate_difference"), 3),
            ),
            ("shadow matured reward rows", metrics["shadow_reward_observations"]),
            ("current bank cards", metrics["bank_cards"]),
            (
                "support-ready lineages",
                f"{metrics['support_ready_card_lineages']} / {metrics['stable_card_lineages_with_offers']}",
            ),
        ),
        "lr",
    )
    diagnostics_table = _simple_table(
        ("diagnostic", "value", "interpretation"),
        (
            ("SQLite integrity", metrics["sqlite_integrity"], "must be ok"),
            (
                "reward residual SD",
                _fmt(metrics["reward_residual_sd"], 4),
                "learned noise scale",
            ),
            (
                "reward optimizer",
                "pass" if metrics["reward_optimizer_success"] else "fail",
                "adaptive scale quadrature",
            ),
            (
                "scale at boundary",
                str(metrics["reward_hyperparameters_at_boundary"]),
                "false required for eviction",
            ),
            (
                "safety gradient infinity norm",
                _fmt(metrics["safety_gradient_inf"], 2),
                "smaller is better",
            ),
            (
                "safety Hessian condition",
                _fmt(metrics["safety_hessian_condition"], 2),
                "below 1e12",
            ),
            (
                "predicted / realized invalidity",
                f"{_fmt(calibration.get('mean_predicted_invalid'), 3)} / {_fmt(calibration.get('realized_invalid_rate'), 3)}",
                "prequential calibration",
            ),
            (
                "overlap mean multiplicity",
                _fmt(overlap["mean_multiplicity"], 2),
                "1 means no reuse",
            ),
            (
                "largest overlap component",
                overlap["largest_overlap_component"],
                "correlated shadow roots",
            ),
        ),
        "p{0.33\\textwidth}p{0.18\\textwidth}p{0.37\\textwidth}",
    )
    glossary_rows = (
        (
            "Prior",
            "What the model believes before seeing this run; it keeps cold cards finite and conservative.",
        ),
        (
            "Likelihood",
            "The mathematical rule connecting a proposed card, context, treatment arm, and observed outcome.",
        ),
        (
            "Posterior",
            "The updated distribution after combining the prior with all eligible ledger evidence.",
        ),
        (
            "Hierarchical / partial pooling",
            "Every card gets its own deviation, but sparse cards borrow the bank-wide pattern instead of fitting noise independently.",
        ),
        (
            "Contextual",
            "Card value may change with frozen parent fitness, progress, and stable MAP-Elites behavior coordinates.",
        ),
        (
            "Credible interval",
            "A posterior range containing the modeled effect with the stated probability, conditional on model assumptions.",
        ),
        (
            "Laplace approximation",
            "A local Gaussian approximation around the safety model's most likely coefficients.",
        ),
        (
            "Thompson / probability matching",
            "Sample plausible worlds and select cards in proportion to how often each is best.",
        ),
        (
            "Chance constraint",
            "A posterior safety rule. The default admits unless added risk is confidently harmful; stricter modes may also enforce an absolute treated-risk limit.",
        ),
        (
            "Propensity",
            "The logged probability that the randomized policy took the action it actually took.",
        ),
        (
            "Overlap / positivity",
            "Every action evaluated by OPE must have nonzero probability under the logging policy.",
        ),
        (
            "Doubly robust OPE",
            "A target-policy estimate combining logged randomization weights with pre-decision outcome predictions.",
        ),
        (
            "Censoring",
            "An outcome is unknown for a reason that prevents honest causal use; it is not silently converted to zero.",
        ),
        (
            "Opportunity budget",
            "The next K mutation decisions in the root's frozen island, regardless of whether that lineage is selected.",
        ),
        (
            "Shared-descendant overlap",
            "One descendant contributes to multiple root endpoints, inducing dependence that an iid likelihood misses.",
        ),
    )
    glossary_table = _simple_table(
        ("term", "plain-language meaning"),
        glossary_rows,
        "p{0.22\\textwidth}p{0.70\\textwidth}",
    )
    figures = {
        "architecture": _figure_tex(
            "01_system_architecture",
            "Complete live and shadow data flow. The shadow branch is isolated from online action selection.",
            "architecture",
        ),
        "executive": _figure_tex(
            "02_executive_dashboard",
            "Executive run-level evidence dashboard.",
            "executive",
        ),
        "search": _figure_tex(
            "03_search_and_interventions",
            "Evolutionary search, archive state, candidate availability, and offer randomization.",
            "search",
        ),
        "bank": _figure_tex(
            "04_bank_and_evidence_lifecycle",
            "Bank growth and the throughput of balanced randomized evidence.",
            "bank",
        ),
        "posterior": _figure_tex(
            "05_fitted_posterior_distributions",
            "Live and shadow fitted card-effect posterior draws at representative final contexts.",
            "posterior",
        ),
        "context": _figure_tex(
            "06_contextual_posterior_surfaces",
            "Counterfactual context slices for parent fitness, semantic behavior location, and progress.",
            "context",
        ),
        "safety": _figure_tex(
            "07_safety_posterior",
            "Safety posterior means, upper bounds, and chance-constraint thresholds.",
            "safety",
        ),
        "hierarchy": _figure_tex(
            "08_hierarchical_coefficients",
            "Shared reward and safety coefficients, correlations, and card-lineage deviations.",
            "hierarchy",
        ),
        "lineage": _figure_tex(
            "09_lineage_opportunity_budget",
            "Shadow maturity funnel, credited depth, and descendant lift over proximal gain.",
            "lineage",
        ),
        "overlap": _figure_tex(
            "10_lineage_overlap_sensitivity",
            "Literal descendant reuse and moving-block uncertainty sensitivity.",
            "overlap",
        ),
        "ope": _figure_tex(
            "11_randomization_and_ope",
            "Randomization realization and conditional-offer doubly robust OPE.",
            "ope",
        ),
        "calibration": _figure_tex(
            "12_prequential_calibration",
            "Decision-time reward and invalidity calibration against later terminal outcomes.",
            "calibration",
        ),
        "map": _figure_tex(
            "13_map_elites_dynamic_context",
            "Stable semantic context versus dynamic MAP-Elites cells and recomputed bounds.",
            "map",
        ),
        "numeric": _figure_tex(
            "14_numerical_health",
            "Posterior convergence, covariance spectra, and numerical condition diagnostics.",
            "numeric",
        ),
        "cards": _figure_tex(
            "15_card_dossier",
            "Card-level posterior value, safety, uncertainty, and randomized support.",
            "cards",
        ),
        "persistence": _figure_tex(
            "16_evidence_persistence",
            "Per-lineage evidence accumulation half-time, age, revision count, and cold-start balanced-support H50 from zero evidence.",
            "persistence",
        ),
        "resources": _figure_tex(
            "17_llm_resource_profile",
            "LLM calls, tokens, provider latency, and the share consumed by card writing and consolidation.",
            "resources",
        ),
    }
    preamble = r"""
\documentclass[10pt]{article}
\usepackage[a4paper,margin=18mm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{microtype}
\usepackage{graphicx}
\usepackage{booktabs,longtable,tabularx,array}
\usepackage[table,dvipsnames]{xcolor}
\usepackage{amsmath,amssymb}
\usepackage{caption}
\usepackage[section]{placeins}
\usepackage{enumitem}
\usepackage[most]{tcolorbox}
\usepackage{fancyhdr}
\usepackage[hidelinks]{hyperref}
\definecolor{AuditBlue}{HTML}{2765A8}
\definecolor{AuditGreen}{HTML}{3B7D44}
\definecolor{AuditRed}{HTML}{B64343}
\definecolor{AuditPurple}{HTML}{74569B}
\definecolor{AuditLight}{HTML}{F3F5F7}
\hypersetup{colorlinks=true,linkcolor=AuditBlue,urlcolor=AuditBlue}
\pagestyle{fancy}
\fancyhf{}
\lhead{Memory v2 Bayesian causal audit}
\rhead{\thepage}
\setlength{\headheight}{14pt}
\setlength{\textfloatsep}{12pt plus 2pt minus 2pt}
\setlist{nosep,leftmargin=1.5em}
\raggedbottom
\captionsetup{font=small,labelfont=bf}
\newtcolorbox{auditbox}[2][]{colback=AuditLight,colframe=#2,boxrule=0.8pt,arc=1mm,left=2mm,right=2mm,top=1.5mm,bottom=1.5mm,#1}
\newcommand{\code}[1]{\texttt{#1}}
\begin{document}
"""
    body = rf"""
\begin{{titlepage}}
{{\color{{AuditBlue}}\rule{{\textwidth}}{{1.5pt}}}}
\vspace{{1.4cm}}
{{\color{{AuditBlue}}\Huge\bfseries Memory v2 Bayesian Causal Audit\par}}
\vspace{{0.35cm}}
{{\color{{AuditBlue}}\Large Real evolutionary smoke, fitted posteriors, contextual behavior, and lineage-credit validation\par}}
\vspace{{1.2cm}}
\begin{{auditbox}}{{{live_verdict_color}}}
\textbf{{Primary verdict:}} {_tex(metrics["verdict"])}.\\
\textbf{{Long-horizon verdict:}} {_tex(metrics["shadow_verdict"])}.
\end{{auditbox}}
\vfill
{run_table}
\vfill
\textbf{{Generated:}} {_tex(metrics["generated_at_utc"])}\\
\textbf{{Run:}} \texttt{{{_tex(data.run_root.name)}}}\\
\textbf{{Evidence source:}} immutable SQLite decision/terminal ledger\\
\textbf{{Report contract:}} no HTML rendering; vector figures and compiled LaTeX PDF\par
\vspace{{0.5cm}}
{{\color{{AuditBlue}}\rule{{\textwidth}}{{1.5pt}}}}
\end{{titlepage}}

\tableofcontents
\clearpage

\section{{Executive assessment}}
\begin{{auditbox}}{{{live_verdict_color}}}
The depth-1 online core {"passed" if metrics["depth1_core_ready"] else "failed"} its integrity, closure, numerical, randomized-support, evidence-accumulation, sustained-lockout, and OPE gates. It logged {metrics["decisions"]} decisions, randomized {metrics["proposals"]} card offers into {metrics["treated"]} treated and {metrics["control"]} withheld arms, and closed {metrics["live_reward_observations"]} live reward outcomes. This establishes that the machinery ran coherently; it does not by itself establish that memory improves the full evolutionary policy.
\end{{auditbox}}

The search best moved from {_fmt(metrics["initial_best_fitness"], 6)} to {_fmt(metrics["final_best_fitness"], 6)}, an oriented improvement of {_fmt(metrics["search_gain"], 6)}. That is an operational search result, not a causal memory effect, because this run has no independent no-memory policy trajectory. {_tex(efficacy_sentence)}

Within the {metrics["proposals"]} randomized offers, the direct treated-minus-control contrast was {_fmt(calibration.get("raw_utility_difference"), 3)} bounded utility and {_fmt(calibration.get("raw_invalid_rate_difference"), 3)} invalidity probability. The doubly robust immediate estimate was {_fmt(active_bootstrap.get("estimate"), 3)} with moving-block interval [{_fmt(active_bootstrap.get("lower"), 3)}, {_fmt(active_bootstrap.get("upper"), 3)}]. {_tex(randomized_direction)} {_tex(calibration_sentence)}

{_tex(lockout_sentence)}

The bank ended with {metrics["bank_cards"]} cards. {metrics["support_ready_card_lineages"]} of {metrics["stable_card_lineages_with_offers"]} offered stable lineages reached at least two treated and two control outcomes across at least two contexts ({support_fraction:.1%}). This is the first-class cold-start metric: whether randomized evidence accumulates before the bank changes.

For long-horizon attribution, {metrics["shadow_reward_observations"]} roots produced reward observations under the depth-{data.shadow_depth}, K={data.shadow_budget} shadow definition. {_tex(lineage_sentence)} {_tex(shadow_sentence)}

{figures["executive"]}

\subsection{{Causal accounting}}
{accounting_table}

\section{{System and estimands}}
{figures["architecture"]}

\subsection{{What is randomized}}
At each mutation decision the system freezes the selected parent, task, parent fitness, evolutionary progress, and stable MAP-Elites behavior coordinates. The current eligible bank is scored. Exactly one card may be proposed. Conditional on that proposed card, a fixed Bernoulli gate with probability {policy.offer_probability:.2f} either delivers the card to the mutator (treated) or withholds it (control). Both the card proposal probability and offer probability are written before mutation. The immediate estimand is the effect of delivering that selected card for one child under the logged proposal policy.

The conditional-offer OPE estimand is narrower than a full memory-policy comparison: it asks what would happen if the offer probability changed while retaining the behavior policy's distribution over proposed cards and contexts. It does not identify a new retriever, a different candidate bank, or no-memory evolution.

\subsection{{Shadow long-horizon estimand}}
For randomized root decision $i$, let $\mathcal{{D}}_i(D,K)$ be valid descendants reachable from its child within lineage depth $D$ and before the $K$th later mutation opportunity in the root's frozen island. The shadow endpoint is
\[
Y_i^{{D,K}} = \max_{{j \in \mathcal{{D}}_i(D,K)}} s\,(f_j-f_{{\mathrm{{parent}}(i)}}),
\]
where $s=+1$ for higher-is-better and $s=-1$ otherwise. There remains exactly one endpoint per original randomized decision. Whether descendants are ever selected is part of utility. The last K roots are naturally pending rather than filled with zero.

\section{{Bayesian model}}
\subsection{{Bounded reward head}}
For valid outcome $i$, card lineage $j$, treatment $A_i\in\{{0,1\}}$, and frozen context features $x_i$, the latent working model is
\[
z_i = x_i^\top\beta + A_i\left(x_i^\top\gamma + c_i^\top u_j\right) + \epsilon_i,
\qquad \epsilon_i\sim\mathcal{{N}}(0,\sigma^2+s_i^2).
\]
$\beta$ is the context-dependent control baseline, $\gamma$ is the shared treatment response, and $u_j$ is the regularized card-lineage deviation. $s_i$ is known evaluation uncertainty when available. The residual scale $\sigma$ is not fixed: it is integrated over an adaptive quadrature on log scale. Latent gains are projected to the root-specific feasible metric interval, so predicted fitness cannot leave the task's declared bounds.

\subsection{{Safety head and hurdle utility}}
Invalidity is modeled separately:
\[
\operatorname{{logit}}\Pr(I_i=1)=x_i^\top\alpha+A_i\left(x_i^\top\delta+c_i^\top v_j\right).
\]
The logistic coefficients use proper Gaussian priors and a MAP/Laplace posterior. Reward and invalidity combine as a hurdle utility. In posterior world $w$,
\[
Q_a^{{(w)}}=(1-p_a^{{(w)}})g_a^{{(w)}}+p_a^{{(w)}}L_i,
\qquad \Delta^{{(w)}}=Q_1^{{(w)}}-Q_0^{{(w)}},
\]
where $L_i$ is the worst feasible root-specific gain. This penalty is an explicit modeling choice; the report exports the configured penalty sensitivity for inspection.

\subsection{{Hierarchy and context}}
The live context contains an intercept, oriented normalized parent fitness, log-scaled evolutionary progress, and stable semantic behavior coordinates. Shared coefficients learn patterns common to the bank. Card effects are deviations around the shared response and therefore shrink toward it when evidence is sparse. There are no lexical payload, token, bigram, or embedding features. Tasks are isolated by the environment/task key in this version; cross-task hierarchical transfer is deliberately not claimed.

{figures["hierarchy"]}

\section{{How one card is selected}}
The complete selection procedure is:
\begin{{enumerate}}
\item Freeze the typed evolutionary context and current evidence snapshot.
\item {_tex(candidate_selection_step)}
\item Fit the reward and safety posteriors to closed causal rows. In-flight decisions count against a per-card pending budget but never become fake outcomes.
\item Draw coherent posterior worlds. Shared coefficients are sampled once per world, preserving cross-card correlation.
\item {_tex(gate_selection_step)}
\item In every world choose the feasible card with highest sampled usable effect; count wins to obtain probability-matching proposal mass.
\item Mix in a {policy.proposal_exploration_probability:.1%} uniform floor across feasible cards so each retains support.
\item Draw one proposed card, then independently draw the fixed {policy.offer_probability:.0%} treated/withheld gate.
\item Persist all probabilities and the frozen card payload before mutation.
\end{{enumerate}}
The result is contextual: the same card can rank differently for different parents and MAP-Elites regions. Card prose can guide the agentic candidate gate, but it is not a Bayesian posterior feature. Equivalent writer merges preserve the stable bank lineage and pool evidence; materially different ideas remain different cards.

\section{{Search and bank behavior}}
{figures["search"]}
{figures["bank"]}

Removing the task-wide card cap prevents late ideas from being rejected solely because the bank is full. It also increases the burden on randomized evidence: a larger bank spreads proposal mass unless the posterior differentiates cards. Figure~\ref{{fig:bank}} therefore reports both bank growth and balanced effective support. Card retirement remains fail-closed and requires treated/control/context support, no pending evidence, healthy optimization, and very low posterior viability across observed contexts.

{figures["resources"]}

Card writing and consolidation consumed {metrics["writer_llm_calls"]} of {metrics["llm_calls"]} LLM calls and {metrics["writer_llm_tokens"]:,} of {metrics["llm_tokens"]:,} tokens ({metrics["writer_llm_token_fraction"]:.1%}). This is operational overhead, not Bayesian selector cost. Summed provider latency is reported only as workload because concurrent calls make it different from wall time.

{figures["persistence"]}

There is no statistical revision reset and no evidence-decay parameter in this iteration. Equivalent content merges into a stable card lineage, so its prior outcomes remain credited. Across all lineages the median accumulation half-time is {_fmt(metrics["median_evidence_accumulation_half_time"], 1)} decisions, which is dominated by lineages with only one or two observations; among support-ready lineages it is {_fmt(metrics["support_ready_median_evidence_accumulation_half_time"], 1)} decisions. At the observed card-level randomized-evidence rate, the median cold-start H50 for reaching balanced 2-treated/2-control support from zero evidence is {_fmt(metrics["median_cold_start_randomized_h50"], 1)} opportunities. It is not a forecast of remaining time for partially observed cards. These are throughput diagnostics, not literal Bayesian half-lives.

\section{{Fitted posteriors}}
{figures["posterior"]}

The left panel is the actual live endpoint used by the policy. The right panel refits the same hierarchical machinery offline to matured shadow outcomes. Its location can be informative about long-term credit, but its width is a working-independence width until overlapping roots are modeled explicitly.

\subsection{{Final live card summaries}}
{_top_card_table(data)}

{figures["cards"]}

\subsection{{Contextual versions}}
{figures["context"]}

Each context curve is a controlled posterior slice, not a claim about the observed marginal distribution. Parent fitness, one stable semantic behavior coordinate, or progress changes while all other frozen values stay at a representative final context. Dynamic MAP cell identity is not treated as a stable category.

\section{{Safety behavior}}
{figures["safety"]}

At cold start, the default incremental-harm gate remains open under uncertainty and excludes only cards with confident evidence of added risk; a numerical fit failure is separately fail-closed. This avoids permanent cold-start abstention, but it does not excuse probability miscalibration. {_tex(calibration_sentence)} {_tex(arm_safety_sentence)} {_tex(lockout_sentence)}

\section{{Lineage credit and dependence}}
{figures["lineage"]}

The opportunity budget is global only within the root's frozen island, not within its descendants. Every later mutation in that island consumes one opportunity. This avoids survivor bias: a root whose lineage is never selected receives the utility it actually produced under the downstream evolutionary policy. Breadth-first ancestry traversal follows selected-parent child IDs, excludes siblings, stops at depth D and the K-opportunity cutoff, and censors an ancestor if a reachable descendant terminal is causally unknown. {_tex(lineage_sentence)}

{figures["overlap"]}

{_tex(shadow_sentence)} The block bootstrap is a sensitivity diagnostic for temporal dependence, not a replacement Bayesian posterior. Promotion of D$>1$ to online action selection requires an explicit dependent likelihood, non-overlapping credit design, or another validated uncertainty correction.

\section{{Randomization, OPE, and calibration}}
{figures["ope"]}

The logged offer gate has exact support at both arms. Extreme target offer probabilities raise importance weights, which is why effective sample size falls away from the behavior value {policy.offer_probability:.2f}. Because this run contains one evolution trajectory, run-cluster OPE standard errors are not identifiable; the report supplies moving-block sensitivity instead and does not present a single-trajectory OPE point estimate as definitive efficacy.

{figures["calibration"]}

{_tex(efficacy_sentence)} {_tex(calibration_sentence)} Prequential residuals also expose drift or misspecification that an end-of-run refit could conceal.

\section{{Dynamic MAP-Elites context}}
{figures["map"]}

The live binner may recompute bounds and change cell indices as the archive evolves. Each decision freezes both raw/dynamic diagnostics and a stable semantic normalization supplied by the behavior dimension. The posterior consumes the stable semantic coordinate, so changing bin edges do not silently relabel old evidence.

\section{{Numerical and ledger integrity}}
{figures["numeric"]}
{diagnostics_table}

All decision and terminal payloads are content-hashed in SQLite, terminal rows join by decision ID, and audit timestamps must respect decision-before-terminal ordering. Numerical failure is fail-closed: the provider abstains rather than using a non-finite, unconverged, or ill-conditioned fit. Audit errors and warnings are preserved in \code{{report\_metrics.json}}.

\section{{Findings and readiness verdict}}
\subsection{{What worked}}
\begin{{itemize}}
\item The immutable causal lifecycle, fixed randomized offer, propensity accounting, and terminal closure {"passed" if metrics["ledger_audit_passed"] else "did not pass"} the ledger audit.
\item The live depth-1 reward and immediate safety heads remained numerically {"healthy" if metrics["depth1_core_ready"] else "unhealthy or incomplete"} under the configured diagnostics.
\item Card writing started from an empty bank, produced {metrics["bank_cards"]} current cards, pooled equivalent merges by stable lineage, and imposed no task-wide capacity rejection.
\item Context uses typed parent fitness, progress, and stable semantic MAP-Elites coordinates; no ad-hoc lexical card features enter the posterior.
\item The shadow resolver matured {metrics["shadow_reward_observations"]} real root decisions and measured when descendant credit exceeded proximal credit without feeding those estimates back into the run.
\end{{itemize}}

\subsection{{What remains weak or unidentified}}
\begin{{itemize}}
\item One trajectory cannot identify the effect of the complete memory policy versus no memory. Search improvement is observational at policy level.
\item Only {metrics["support_ready_card_lineages"]} stable lineages reached the retirement support gate. The remaining bank is still partially pooled and cold.
\item {_tex(calibration_sentence)} {_tex(arm_safety_sentence)}
\item {_tex(lockout_sentence)} A long lockout means the policy stopped collecting new randomized card evidence even though evolution continued.
\item D$>1$ root windows reuse descendants or nearby trajectory shocks. The current iid Gaussian reward likelihood is not calibrated for that dependence.
\item Conditional-offer OPE evaluates the offer gate under logged card proposals, not a new selector, retriever, writer, or bank policy.
\item The worst-feasible invalid penalty materially couples safety and utility; sensitivity is exported, but this single run cannot choose its optimal strength.
\end{{itemize}}

\begin{{auditbox}}{{{live_verdict_color}}}
\textbf{{Depth 1:}} {_tex(metrics["verdict"])}. {"The causal machinery is suitable for replicated guarded experiments, but safety priors/calibration require tuning before relying on the gate for production protection." if metrics["depth1_core_ready"] else "The causal machinery is not suitable for guarded experiments until every failed readiness gate is resolved."}\\
\textbf{{Depth greater than 1:}} {_tex(metrics["shadow_verdict"])}. Keep it shadow-only until dependence-aware uncertainty is implemented and validated on multiple trajectories.
\end{{auditbox}}

\section{{Bayesian and causal terms, ELI5}}
{glossary_table}

\appendix
\section{{Current card bank}}
{_card_appendix(data)}

\section{{Reproducible artifacts}}
Every plotted value is exported beneath \code{{tables/}}. Key files are:
\begin{{itemize}}
\item \code{{live\_final\_posterior.csv}} and \code{{shadow\_final\_posterior.csv}}
\item \code{{contextual\_posterior\_grid.csv}}
\item \code{{shadow\_lineage\_outcomes.csv}} and \code{{shadow\_descendant\_lift.csv}}
\item \code{{descendant\_overlap.csv}} and \code{{block\_bootstrap\_draws.csv}}
\item \code{{candidate\_posterior\_trace.csv}}, \code{{card\_evidence\_lifecycle.csv}}, and OPE tables
\item \code{{card\_evidence\_timing.csv}} with accumulation half-time, evidence age, revisions, and H50
\item \code{{llm\_call\_trace.csv}} and \code{{llm\_resource\_summary.csv}}
\item \code{{report\_metrics.json}}, the machine-readable verdict and diagnostics
\end{{itemize}}

\section{{Scope statement}}
This report explains and demonstrates the complete implemented memory-v2 core for this run. It distinguishes mechanical correctness, posterior calibration, and evolutionary efficacy. The first can pass in one smoke; the second needs diagnostic evidence and repeated trajectories; the third requires a controlled policy-level comparison. No claim is promoted across those boundaries.

\end{{document}}
"""
    paths.tex_path.write_text(preamble + body, encoding="utf-8")


def compile_tex(paths: ReportPaths, tectonic: str | None = None) -> None:
    executable = tectonic or shutil.which("tectonic")
    if executable is None:
        candidate = PROJECT_ROOT.parent / ".local" / "bin" / "tectonic"
        executable = str(candidate) if candidate.is_file() else None
    if executable is None:
        workspace_candidate = Path(
            "/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/.local/bin/tectonic"
        )
        executable = str(workspace_candidate) if workspace_candidate.is_file() else None
    if executable is None:
        raise FileNotFoundError("tectonic is required to compile the audit PDF")
    result = subprocess.run(
        [
            executable,
            "--keep-logs",
            "--outdir",
            str(paths.output_dir),
            paths.tex_path.name,
        ],
        cwd=paths.output_dir,
        text=True,
        capture_output=True,
        check=False,
        timeout=600,
    )
    (paths.output_dir / "tectonic.stdout.log").write_text(
        result.stdout, encoding="utf-8"
    )
    (paths.output_dir / "tectonic.stderr.log").write_text(
        result.stderr, encoding="utf-8"
    )
    if result.returncode != 0 or not paths.pdf_path.is_file():
        raise RuntimeError(
            "LaTeX compilation failed; see tectonic.stderr.log\n"
            + result.stderr[-3000:]
        )


def _primary_env_file() -> Path | None:
    result = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    candidate = Path(result.stdout.strip()).resolve().parent / ".env"
    return candidate if candidate.is_file() else None


def send_telegram(
    paths: ReportPaths, metrics: dict[str, Any], env_file: Path | None
) -> None:
    from dotenv import load_dotenv

    resolved_env = env_file or _primary_env_file()
    if resolved_env is not None:
        load_dotenv(resolved_env, override=False)
    from tools.telegram_notify import notify, send_document, send_photo

    notify(
        "\n".join(
            (
                "Memory v2 Bayesian audit completed.",
                f"Depth-1 verdict: {metrics['verdict']}",
                f"Long-horizon verdict: {metrics['shadow_verdict']}",
                f"Decisions: {metrics['decisions']}; cards: {metrics['bank_cards']}; shadow matured: {metrics['shadow_reward_observations']}",
            )
        ),
        parse_mode=None,
    )
    for path in sorted(paths.figure_dir.glob("*.png")):
        caption = path.stem.replace("_", " ").title()
        send_photo(str(path), caption=caption, parse_mode=None)
    send_document(
        str(paths.pdf_path),
        caption="Memory v2 Bayesian causal audit (compiled LaTeX PDF)",
        parse_mode=None,
    )
    send_document(
        str(paths.output_dir / "report_metrics.json"),
        caption="Machine-readable audit metrics and verdict",
        parse_mode=None,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--shadow-depth", type=int, default=3)
    parser.add_argument("--shadow-budget", type=int, default=32)
    parser.add_argument("--bootstrap-samples", type=int, default=4000)
    parser.add_argument("--tectonic", type=str)
    parser.add_argument("--skip-compile", action="store_true")
    parser.add_argument("--send-telegram", action="store_true")
    parser.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    if args.shadow_depth < 2:
        parser.error("shadow-depth must be at least 2")
    if args.shadow_budget < 1:
        parser.error("shadow-budget must be positive")
    if args.bootstrap_samples < 500:
        parser.error("bootstrap-samples must be at least 500")

    ledger = args.ledger.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = ReportPaths(
        output_dir=output_dir,
        figure_dir=output_dir / "figures",
        table_dir=output_dir / "tables",
        tex_path=output_dir / "memory_v2_bayesian_audit.tex",
        pdf_path=output_dir / "memory_v2_bayesian_audit.pdf",
    )
    _configure_matplotlib()
    print(
        "[report] reconstructing ledger and fitting live/shadow posteriors", flush=True
    )
    data = prepare_data(
        ledger,
        shadow_depth=args.shadow_depth,
        shadow_budget=args.shadow_budget,
        bootstrap_samples=args.bootstrap_samples,
    )
    print("[report] rendering vector and PNG figures", flush=True)
    render_architecture(data, paths)
    render_executive(data, paths)
    render_search_and_context(data, paths)
    render_bank_lifecycle(data, paths)
    render_llm_resources(data, paths)
    render_posterior_distributions(data, paths)
    contextual = render_contextual_posteriors(data, paths)
    render_safety_posterior(data, paths, contextual)
    render_hierarchy(data, paths)
    lineage_outcomes, lineage_deltas = render_lineage_credit(data, paths)
    render_overlap_sensitivity(data, paths)
    render_randomization_ope(data, paths)
    render_calibration(data, paths)
    render_map_elites(data, paths)
    render_numerical_health(data, paths)
    render_card_dossier(data, paths)
    evidence_timing = render_evidence_persistence(data, paths)
    print("[report] exporting source tables and writing LaTeX", flush=True)
    metrics = export_tables(
        data,
        paths,
        contextual,
        lineage_outcomes,
        lineage_deltas,
        evidence_timing,
    )
    build_tex(data, metrics, paths)
    if not args.skip_compile:
        print("[report] compiling LaTeX with Tectonic", flush=True)
        compile_tex(paths, args.tectonic)
    manifest = {
        "pdf": str(paths.pdf_path) if paths.pdf_path.is_file() else None,
        "tex": str(paths.tex_path),
        "figures": [str(path) for path in sorted(paths.figure_dir.glob("*.png"))],
        "tables": [str(path) for path in sorted(paths.table_dir.glob("*.csv"))],
        "metrics": str(paths.output_dir / "report_metrics.json"),
    }
    (paths.output_dir / "report_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if args.send_telegram:
        if not paths.pdf_path.is_file():
            raise RuntimeError("Telegram delivery requires a compiled PDF")
        print("[report] sending PDF and every PNG figure to Telegram", flush=True)
        send_telegram(paths, metrics, args.env_file)
    print(json.dumps(_jsonable(metrics), indent=2, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
