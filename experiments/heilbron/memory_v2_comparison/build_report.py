#!/usr/bin/env python3
"""Build a descriptive three-arm Heilbronn memory-v2 comparison report."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import hashlib
import json
import math
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import yaml  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from experiments.hover.memory_v2_smoke.analyze import (  # noqa: E402
    Audit,
    audit_rows,
    load_ledger,
)
from experiments.hover.memory_v2_smoke.latex_report import (  # noqa: E402
    BLUE,
    GREEN,
    GRID,
    INK,
    LIGHT,
    MUTED,
    ORANGE,
    PURPLE,
    RED,
    TEAL,
    _audit_input_paths,
    _cards_path,
    _config_path,
    _configure_matplotlib,
    _load_run_llm_calls,
    _run_logs,
)
from gigaevo.evolution.engine.hooks import NullPostRunHook  # noqa: E402
from gigaevo.memory.provider import NullMemoryProvider  # noqa: E402
from gigaevo.memory.write.writer import MemoryWriter  # noqa: E402
from gigaevo.memory_v2.candidates import (  # noqa: E402
    AgenticApplicabilityProvider,
    NullApplicabilityProvider,
    WholeBankCandidateSource,
)
from gigaevo.memory_v2.models import (  # noqa: E402
    ApplicabilityStatus,
    CandidateUniverseStatus,
)
from gigaevo.memory_v2.provider import CausalBanditMemoryProvider  # noqa: E402

ARM_COLORS = {
    "agentic": BLUE,
    "whole_bank": ORANGE,
    "no_memory": GREEN,
}
ARM_LABELS = {
    "agentic": "RAG applicability + Bayes",
    "whole_bank": "Null applicability + Bayes",
    "no_memory": "No memory",
}
AUDIT_FIGURE_CAPTIONS = {
    "01_system_architecture": "Memory-v2 decision and evidence architecture",
    "02_executive_dashboard": "Run-level Bayesian audit dashboard",
    "03_search_and_interventions": "Search trajectory and memory interventions",
    "04_bank_and_evidence_lifecycle": "Card-bank and evidence lifecycle",
    "05_fitted_posterior_distributions": "Fitted card-effect posteriors",
    "06_contextual_posterior_surfaces": "Contextual posterior surfaces",
    "07_safety_posterior": "Invalidity and incremental-harm posteriors",
    "08_hierarchical_coefficients": "Hierarchical posterior coefficients",
    "09_lineage_opportunity_budget": "Lineage-credit opportunity budget",
    "10_lineage_overlap_sensitivity": "Lineage-overlap sensitivity analysis",
    "11_randomization_and_ope": "Randomization integrity and conditional-offer OPE",
    "12_prequential_calibration": "Prequential reward and safety calibration",
    "13_map_elites_dynamic_context": "Dynamic MAP-Elites context",
    "14_numerical_health": "Posterior numerical diagnostics",
    "15_card_dossier": "Card-level evidence dossier",
    "16_evidence_persistence": "Randomized-evidence persistence",
    "17_llm_resource_profile": "LLM resource profile",
}
REQUIRED_AUDIT_TABLES = frozenset(
    {
        "decision_trace.csv",
        "candidate_posterior_trace.csv",
        "terminal_trace.csv",
        "card_evidence_lifecycle.csv",
        "live_final_posterior.csv",
        "contextual_posterior_grid.csv",
        "shadow_lineage_outcomes.csv",
        "shadow_descendant_lift.csv",
        "card_evidence_timing.csv",
        "live_ope.csv",
    }
)


@dataclass
class ArmData:
    key: str
    root: Path
    config: dict[str, Any]
    trace: pd.DataFrame
    archive: pd.DataFrame
    seed_signature: str
    seed_best: float
    seed_valid_fitnesses: tuple[float, ...]
    archive_cells: int
    llm_calls: pd.DataFrame
    memory_trace: pd.DataFrame
    memory_audit: Audit | None
    sqlite_integrity: str | None
    audit_metrics: dict[str, Any]
    memory_events: list[dict[str, Any]]
    bank_cards: int
    log_segments: int
    llm_log_segments: int
    storage_ledger_issues: tuple[str, ...]
    decision_ordinals_contiguous: bool


@dataclass(frozen=True)
class ReportPaths:
    root: Path
    figures: Path
    tables: Path
    per_run: Path
    tex: Path
    pdf: Path


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line_number, line in enumerate(
        path.open(encoding="utf-8", errors="replace"), 1
    ):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"malformed JSONL row in {path}: {line!r}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"non-object JSONL row in {path}:{line_number}")
        rows.append(value)
    return rows


def _load_config(root: Path) -> dict[str, Any]:
    path = _config_path(root)
    if not path.is_file():
        raise FileNotFoundError(path)
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"invalid Hydra config: {path}")
    return value


def _program_rows(root: Path) -> list[dict[str, Any]]:
    directory = root / "storage" / "heilbron" / "programs"
    if not directory.is_dir():
        raise FileNotFoundError(directory)
    rows = []
    for path in sorted(directory.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid program record: {path}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"non-object program record: {path}")
        required = {"id", "iteration", "created_at", "metadata", "metrics"}
        missing = sorted(required - value.keys())
        if missing:
            raise ValueError(f"program record {path} omits {missing}")
        if not isinstance(value["metadata"], dict) or not isinstance(
            value["metrics"], dict
        ):
            raise ValueError(f"program record {path} has invalid metadata or metrics")
        rows.append(value)
    if not rows:
        raise ValueError(f"no program records under {directory}")
    return rows


def _seed_facts(
    programs: list[dict[str, Any]],
) -> tuple[int, str, float, tuple[float, ...]]:
    seeds = [
        row
        for row in programs
        if row.get("metadata", {}).get("source") == "initial_program"
    ]
    if len(seeds) != 5:
        raise ValueError(f"expected five initial programs, found {len(seeds)}")
    seed_iterations = [int(row["iteration"]) for row in seeds]
    if len(set(seed_iterations)) != len(seed_iterations):
        raise ValueError("initial program iterations are not unique")
    seeds.sort(key=lambda row: int(row["iteration"]))
    digest = hashlib.sha256()
    best = -math.inf
    valid_fitnesses = []
    for row in seeds:
        digest.update(str(row.get("code", "")).encode())
        digest.update(json.dumps(row.get("metrics", {}), sort_keys=True).encode())
        metrics = row.get("metrics", {})
        if "is_valid" not in metrics or "fitness" not in metrics:
            raise ValueError(f"initial program {row['id']} omits validity or fitness")
        validity = float(metrics["is_valid"])
        fitness = float(metrics["fitness"])
        if not math.isfinite(validity) or validity not in {0.0, 1.0}:
            raise ValueError(f"initial program {row['id']} has invalid is_valid")
        if not math.isfinite(fitness):
            raise ValueError(f"initial program {row['id']} has non-finite fitness")
        if validity > 0.5:
            valid_fitnesses.append(fitness)
            best = max(best, fitness)
    if not valid_fitnesses:
        raise ValueError("initial programs contain no valid fitness")
    return (
        max(int(row["iteration"]) for row in seeds),
        digest.hexdigest(),
        best,
        tuple(valid_fitnesses),
    )


def _load_trace(
    root: Path,
    *,
    allowed_pending_program_ids: frozenset[str] = frozenset(),
) -> tuple[pd.DataFrame, str, float, tuple[float, ...]]:
    programs = _program_rows(root)
    seed_max, signature, seed_best, seed_valid_fitnesses = _seed_facts(programs)
    metric_dir = root / "metrics"
    reported_by_iteration: dict[int, list[float]] = defaultdict(list)
    for row in _read_jsonl(metric_dir / "program_metrics:valid_program_fitness.jsonl"):
        if row.get("v") is not None:
            reported_by_iteration[int(row["s"])].append(float(row["v"]))
    seed_times = [
        datetime.fromisoformat(
            str(row["created_at"]).replace("Z", "+00:00")
        ).timestamp()
        for row in programs
        if row.get("metadata", {}).get("source") == "initial_program"
    ]
    if not seed_times:
        raise ValueError(f"no seed timestamps under {root}")
    t0 = min(seed_times)
    rows = []
    observed_pending_ids: set[str] = set()
    pending_indexes: set[int] = set()
    for program in programs:
        step = int(program.get("iteration", -1))
        metrics = program.get("metrics", {})
        if step <= seed_max:
            continue
        if "is_valid" not in metrics:
            program_id = str(program["id"])
            if program_id in allowed_pending_program_ids:
                observed_pending_ids.add(program_id)
                pending_indexes.add(step - seed_max)
                continue
            raise ValueError(f"non-seed program {program['id']} omits metrics.is_valid")
        valid = float(metrics["is_valid"]) > 0.5
        if valid and "fitness" not in metrics:
            raise ValueError(f"valid program {program['id']} omits metrics.fitness")
        resolved_fitness = float(metrics["fitness"]) if valid else math.nan
        reported = reported_by_iteration.get(step, []) if valid else []
        sources_match = not reported or any(
            math.isclose(
                value,
                resolved_fitness,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
            for value in reported
        )
        created_at = datetime.fromisoformat(
            str(program["created_at"]).replace("Z", "+00:00")
        ).timestamp()
        rows.append(
            {
                "mutant_index": step - seed_max,
                "program_step": step,
                "program_id": str(program["id"]),
                "created_at": created_at,
                "elapsed_seconds": created_at - t0,
                "valid": valid,
                "fitness": resolved_fitness,
                "fitness_source": "program_storage",
                "reporter_present": bool(reported),
                "reporter_storage_match": sources_match,
            }
        )
    if not rows:
        raise ValueError(f"no evaluated mutants under {root}")
    frame = pd.DataFrame(rows).sort_values("mutant_index").reset_index(drop=True)
    if frame["mutant_index"].duplicated().any():
        raise ValueError(f"duplicate program iterations in {root}")
    if observed_pending_ids != set(allowed_pending_program_ids):
        raise ValueError(
            f"pending ledger children do not match metric-less programs in {root}"
        )
    observed_indexes = set(frame["mutant_index"].astype(int))
    all_indexes = sorted(observed_indexes | pending_indexes)
    expected_indexes = list(range(1, len(all_indexes) + 1))
    if all_indexes != expected_indexes:
        raise ValueError(f"non-contiguous mutant iterations in {root}")
    observed = frame["fitness"].where(frame["valid"], np.nan)
    frame["best_fitness"] = (
        observed.cummax().ffill().fillna(seed_best).clip(lower=seed_best)
    )
    frame["rolling_valid_rate"] = (
        frame["valid"].astype(float).rolling(25, min_periods=1).mean()
    )
    return frame, signature, seed_best, seed_valid_fitnesses


def _load_archive_trace(root: Path, evaluated_mutants: int) -> tuple[pd.DataFrame, int]:
    metric_dir = root / "metrics"
    processed = pd.DataFrame(
        _read_jsonl(metric_dir / "evolution_engine:programs_processed.jsonl")
    )
    sizes = pd.DataFrame(
        _read_jsonl(metric_dir / "evolution_engine:size_fitness_island.jsonl")
    )
    if processed.empty or sizes.empty:
        frame = pd.DataFrame(columns=["mutant_index", "archive_cells"])
    else:
        processed = processed.rename(columns={"v": "processed"}).sort_values("t")
        sizes = sizes.rename(columns={"v": "archive_cells"}).sort_values("t")
        frame = pd.merge_asof(
            processed[["t", "processed"]],
            sizes[["t", "archive_cells"]],
            on="t",
            direction="nearest",
            tolerance=2.0,
        )
        final_processed = int(processed["processed"].max())
        # Live storage can lead the ingestor by the current buffer. Preserve the
        # observed counter in that case; the final alignment gate will fail.
        initial_processed = max(final_processed - evaluated_mutants, 0)
        frame["mutant_index"] = frame["processed"].astype(int) - initial_processed
        frame = (
            frame[frame["mutant_index"] >= 0]
            .dropna(subset=["archive_cells"])
            .drop_duplicates("mutant_index", keep="last")
            .sort_values("mutant_index")
        )
        frame["elapsed_seconds"] = frame["t"] - float(frame["t"].min())
    archive_path = (
        root / "storage" / "heilbron" / "archives" / "island_fitness_island.json"
    )
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    value = json.loads(archive_path.read_text(encoding="utf-8"))
    if (
        not isinstance(value, dict)
        or not value
        or any(not isinstance(cell, str) for cell in value)
        or any(
            not isinstance(program_id, str) or not program_id
            for program_id in value.values()
        )
    ):
        raise ValueError(f"invalid final archive: {archive_path}")
    try:
        cell_indices = [int(cell) for cell in value]
    except ValueError as exc:
        raise ValueError(f"invalid final archive cell keys: {archive_path}") from exc
    if any(cell < 0 for cell in cell_indices):
        raise ValueError(f"invalid final archive cell keys: {archive_path}")
    programs = {str(row["id"]): row for row in _program_rows(root)}
    missing_programs = sorted(set(value.values()) - programs.keys())
    if missing_programs:
        raise ValueError(
            f"final archive references missing programs: {missing_programs[:5]}"
        )
    invalid_programs = []
    for program_id in value.values():
        metrics = programs[program_id]["metrics"]
        try:
            is_valid = float(metrics.get("is_valid"))
            fitness = float(metrics.get("fitness"))
        except (TypeError, ValueError):
            invalid_programs.append(program_id)
            continue
        if is_valid != 1.0 or not math.isfinite(fitness):
            invalid_programs.append(program_id)
    if invalid_programs:
        raise ValueError(
            f"final archive references non-valid programs: {invalid_programs[:5]}"
        )
    final_cells = len(value)
    return frame, final_cells


def _categorize_llm(stage: str) -> str:
    if stage.startswith("Retrieval"):
        return "retrieval"
    if stage.startswith("Mutation"):
        return "mutation"
    if stage in {
        "ConsolidateAgent",
        "ProgramAuthorAgent",
        "ReconcileAgent",
        "TaskSummaryAgent",
    }:
        return "writer"
    return "other"


def _load_memory(root: Path) -> tuple[pd.DataFrame, Audit | None, str | None]:
    ledger = root / "checkpoints" / "memory_v2_selection_evidence.sqlite3"
    if not ledger.is_file():
        return pd.DataFrame(), None, None
    audit = Audit()
    rows, integrity = load_ledger(ledger, audit)
    audit_rows(rows, audit)
    result = []
    for row in rows:
        record = row.decision
        proposed = record.proposed_treatment_id
        source = "none"
        proposed_bank_id = next(
            (
                card.bank_card_id
                for card in record.candidates
                if card.treatment_id == proposed
            ),
            None,
        )
        if proposed_bank_id is not None:
            source = (
                "rag_applicable"
                if proposed_bank_id in record.applicability.applicable_bank_card_ids
                else "not_rag_applicable"
            )
        action = next(
            (
                item
                for item in record.action_probabilities
                if item.treatment_id == proposed
            ),
            None,
        )
        terminal = row.terminal
        terminal_gain = (
            terminal.measurement.value
            if terminal is not None and terminal.measurement is not None
            else math.nan
        )
        result.append(
            {
                "decision_index": record.event_ordinal + 1,
                "decision_id": record.decision_id,
                "candidate_universe_status": record.candidate_universe.status,
                "applicability_name": record.applicability.specification.name,
                "applicability_status": record.applicability.status,
                "eligible_cards": len(record.candidate_universe.eligible_bank_card_ids),
                "applicable_cards": len(record.applicability.applicable_bank_card_ids),
                "slate_cards": len(record.candidates),
                "research_iterations": record.applicability.research_iterations,
                "posterior_candidates": len(record.candidates),
                "safe_candidates": sum(
                    item.safe for item in record.action_probabilities
                ),
                "evidence_count": record.fit_diagnostics.evidence_count,
                "proposed": proposed is not None,
                "proposed_treatment_id": proposed or "",
                "proposal_source": source,
                "proposal_probability": (
                    action.proposal_probability if action is not None else math.nan
                ),
                "delivered": bool(record.delivered),
                "offer_probability": record.offer_probability or math.nan,
                "terminal_status": (
                    terminal.status if terminal is not None else "pending"
                ),
                "terminal_gain": terminal_gain,
                "predicted_effect": (
                    action.prediction.usable_effect_mean
                    if action is not None
                    else math.nan
                ),
            }
        )
    return pd.DataFrame(result), audit, integrity


def _pending_child_ids(root: Path) -> frozenset[str]:
    ledger = root / "checkpoints" / "memory_v2_selection_evidence.sqlite3"
    if not ledger.is_file():
        return frozenset()
    with sqlite3.connect(ledger) as connection:
        rows = connection.execute(
            """
            SELECT dc.child_id
            FROM decisions AS d
            JOIN decision_children AS dc USING(decision_id)
            LEFT JOIN terminals AS t USING(decision_id)
            WHERE t.decision_id IS NULL
            """
        ).fetchall()
    return frozenset(str(row[0]) for row in rows)


def _bank_size(root: Path) -> int:
    path = _cards_path(root)
    if not path.is_file():
        raise FileNotFoundError(path)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("cards"), dict):
        raise ValueError(f"invalid card-bank document: {path}")
    cards = value["cards"]
    return len(cards)


def _storage_ledger_integrity(root: Path) -> tuple[tuple[str, ...], bool]:
    ledger = root / "checkpoints" / "memory_v2_selection_evidence.sqlite3"
    if not ledger.is_file():
        return (), True
    programs = {str(row.get("id")): row for row in _program_rows(root)}
    rows, _ = load_ledger(ledger, Audit())
    ordinals = [row.decision.event_ordinal for row in rows]
    contiguous = ordinals == list(range(len(rows)))
    issues: list[str] = []
    for row in rows:
        decision = row.decision
        terminal = row.terminal
        if terminal is None:
            continue
        base = programs.get(terminal.base_id)
        if base is None:
            issues.append(f"{decision.decision_id}: base {terminal.base_id} missing")
            continue
        if terminal.base_id != decision.context.parent_id:
            issues.append(f"{decision.decision_id}: terminal/context base mismatch")
        primary = decision.context.reward.primary_metric
        base_metrics = base.get("metrics", {})
        stored_parent = base_metrics.get(primary)
        frozen_parent = decision.context.parent_metrics.get(primary)
        if (
            stored_parent is None
            or frozen_parent is None
            or not math.isclose(
                float(stored_parent), float(frozen_parent), rel_tol=0.0, abs_tol=1e-12
            )
        ):
            issues.append(f"{decision.decision_id}: frozen parent metric mismatch")
        if terminal.status not in {"outcome", "invalid"}:
            continue
        child = programs.get(terminal.child_id)
        if child is None:
            issues.append(f"{decision.decision_id}: child {terminal.child_id} missing")
            continue
        child_metrics = child.get("metrics", {})
        stored_valid = float(child_metrics.get("is_valid", 0.0)) > 0.5
        if terminal.status == "invalid":
            if stored_valid:
                issues.append(
                    f"{decision.decision_id}: invalid terminal has valid child"
                )
            continue
        if (
            not stored_valid
            or terminal.measurement is None
            or primary not in child_metrics
        ):
            issues.append(
                f"{decision.decision_id}: outcome terminal lacks valid measurement"
            )
            continue
        direction = 1.0 if decision.context.reward.higher_is_better else -1.0
        expected_gain = direction * (
            float(child_metrics[primary]) - float(frozen_parent)
        )
        if not math.isclose(
            terminal.measurement.value,
            expected_gain,
            rel_tol=0.0,
            abs_tol=1e-10,
        ):
            issues.append(
                f"{decision.decision_id}: terminal gain disagrees with storage"
            )
    return tuple(issues), contiguous


def _audit_provenance_error(
    key: str, root: Path, metrics: dict[str, Any]
) -> str | None:
    root = root.resolve()
    expected_ledger = (
        root / "checkpoints" / "memory_v2_selection_evidence.sqlite3"
    ).resolve()
    recorded_root = Path(str(metrics.get("run_root", ""))).resolve()
    recorded_ledger = Path(str(metrics.get("ledger", ""))).resolve()
    if recorded_root != root or recorded_ledger != expected_ledger:
        return (
            f"audit provenance mismatch for {key}: "
            f"run={recorded_root}, ledger={recorded_ledger}"
        )

    fingerprints = metrics.get("audit_input_sha256")
    if not isinstance(fingerprints, dict):
        return f"audit provenance mismatch for {key}: missing input fingerprints"
    expected_paths = _audit_input_paths(root, expected_ledger)
    if any(not path.is_file() for path in expected_paths):
        missing = [str(path) for path in expected_paths if not path.is_file()]
        return f"audit provenance mismatch for {key}: missing inputs {missing}"
    expected_keys = {str(path.relative_to(root)) for path in expected_paths}
    if set(fingerprints) != expected_keys:
        return (
            f"audit provenance mismatch for {key}: fingerprint inputs "
            f"{sorted(fingerprints)} != {sorted(expected_keys)}"
        )
    for relative, expected_digest in fingerprints.items():
        path = (root / relative).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            return f"audit provenance mismatch for {key}: path escapes run root"
        actual_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if not isinstance(expected_digest, str) or actual_digest != expected_digest:
            return (
                f"audit provenance mismatch for {key}: "
                f"fingerprint changed for {relative}"
            )
    return None


def _validate_audit_artifacts(audit_dir: Path) -> None:
    required = {
        audit_dir / "report_metrics.json",
        audit_dir / "report_manifest.json",
        audit_dir / "memory_v2_bayesian_audit.pdf",
    }
    required.update(audit_dir / "tables" / name for name in REQUIRED_AUDIT_TABLES)
    for stem in AUDIT_FIGURE_CAPTIONS:
        required.add(audit_dir / "figures" / f"{stem}.png")
        required.add(audit_dir / "figures" / f"{stem}.pdf")
    missing = sorted(str(path) for path in required if not path.is_file())
    if missing:
        raise FileNotFoundError(
            "incomplete Bayesian audit artifacts:\n" + "\n".join(missing)
        )


def load_arm(
    key: str,
    root: Path,
    audit_dir: Path | None,
    *,
    allow_pending_programs: bool = False,
) -> ArmData:
    root = root.resolve()
    config = _load_config(root)
    pending_program_ids = (
        _pending_child_ids(root) if allow_pending_programs else frozenset()
    )
    trace, seed_signature, seed_best, seed_valid_fitnesses = _load_trace(
        root, allowed_pending_program_ids=pending_program_ids
    )
    archive, archive_cells = _load_archive_trace(root, len(trace))
    logs = _run_logs(root)
    llm_calls = _load_run_llm_calls(root)
    if not llm_calls.empty:
        llm_calls = llm_calls.copy()
        llm_calls["category"] = llm_calls["stage"].map(_categorize_llm)
        llm_calls["arm"] = key
    memory_trace, memory_audit, integrity = _load_memory(root)
    if not memory_trace.empty:
        memory_trace["arm"] = key
    events = _read_jsonl(root / "memory" / "memory_events.jsonl")
    metrics = {}
    if audit_dir is not None:
        _validate_audit_artifacts(audit_dir)
        path = audit_dir / "report_metrics.json"
        metrics = json.loads(path.read_text(encoding="utf-8"))
        provenance_error = _audit_provenance_error(key, root, metrics)
        if provenance_error is not None:
            raise ValueError(provenance_error)
    storage_ledger_issues, ordinals_contiguous = _storage_ledger_integrity(root)
    return ArmData(
        key=key,
        root=root,
        config=config,
        trace=trace,
        archive=archive,
        seed_signature=seed_signature,
        seed_best=seed_best,
        seed_valid_fitnesses=seed_valid_fitnesses,
        archive_cells=archive_cells,
        llm_calls=llm_calls,
        memory_trace=memory_trace,
        memory_audit=memory_audit,
        sqlite_integrity=integrity,
        audit_metrics=metrics,
        memory_events=events,
        bank_cards=_bank_size(root) if key != "no_memory" else 0,
        log_segments=len(logs),
        llm_log_segments=(
            int(llm_calls["log_segment"].nunique()) if not llm_calls.empty else 0
        ),
        storage_ledger_issues=storage_ledger_issues,
        decision_ordinals_contiguous=ordinals_contiguous,
    )


def _endpoint_summary(arms: list[ArmData], metric_upper: float) -> pd.DataFrame:
    rows = []
    for arm in arms:
        trace = arm.trace
        final_best = float(trace["best_fitness"].iloc[-1])
        reached = trace.index[trace["best_fitness"] >= final_best - 1e-15]
        calls = arm.llm_calls
        rows.append(
            {
                "arm": arm.key,
                "evaluated_mutants": len(trace),
                "valid_mutants": int(trace["valid"].sum()),
                "valid_rate": float(trace["valid"].mean()),
                "seed_best": arm.seed_best,
                "final_best": final_best,
                "observed_gain": final_best - arm.seed_best,
                "final_best_mutant": int(trace.loc[reached[0], "mutant_index"]),
                "normalized_best_auc": float(
                    np.trapezoid(trace["best_fitness"], trace["mutant_index"])
                    / max(len(trace) - 1, 1)
                    / metric_upper
                ),
                "archive_cells": arm.archive_cells,
                "elapsed_minutes": (
                    float(arm.archive["elapsed_seconds"].max()) / 60.0
                    if not arm.archive.empty
                    else float(trace["elapsed_seconds"].max()) / 60.0
                ),
                "llm_calls": len(calls),
                "llm_tokens": int(calls["total_tokens"].sum())
                if not calls.empty
                else 0,
                "llm_failures": (
                    int((~calls["ok"].astype(bool)).sum()) if not calls.empty else 0
                ),
                "bank_cards": arm.bank_cards,
            }
        )
    return pd.DataFrame(rows)


def _lineage_credit_summary(arms: list[ArmData]) -> pd.DataFrame:
    rows = []
    for arm in arms:
        if arm.key == "no_memory":
            continue
        metrics = arm.audit_metrics
        rows.append(
            {
                "arm": arm.key,
                "matured_roots": metrics.get("shadow_matured_roots"),
                "pending_roots": metrics.get("shadow_pending_roots"),
                "censored_roots": metrics.get("shadow_censored_roots"),
                "valid_outcome_roots": metrics.get("shadow_outcome_roots"),
                "best_depth_gt_1_roots": metrics.get("shadow_best_depth_gt_1_roots"),
                "best_depth_gt_1_fraction": metrics.get(
                    "shadow_best_depth_gt_1_fraction"
                ),
                "positive_descendant_lift_fraction": metrics.get(
                    "positive_descendant_lift_fraction"
                ),
                "median_descendant_lift": metrics.get("median_descendant_lift"),
                "reused_descendants": metrics.get("overlap", {}).get(
                    "reused_descendants"
                ),
            }
        )
    return pd.DataFrame(rows)


def _retrieval_summary(arm: ArmData) -> dict[str, Any]:
    frame = arm.memory_trace
    statuses = Counter(frame["applicability_status"]) if not frame.empty else Counter()
    proposed = frame[frame["proposed"]] if not frame.empty else frame
    research_steps = [
        row for row in arm.memory_events if row.get("event") == "MEMORY_RESEARCH_STEP"
    ]
    research_calls = [
        row for row in arm.memory_events if row.get("event") == "MEMORY_RESEARCH"
    ]
    research_durations = [float(row.get("duration_ms", 0.0)) for row in research_calls]
    research_timeline: list[tuple[datetime, int]] = []
    for row, duration_ms in zip(research_calls, research_durations):
        ended_at = datetime.fromisoformat(str(row["timestamp_utc"]))
        started_at = ended_at - timedelta(milliseconds=duration_ms)
        research_timeline.extend(((started_at, 1), (ended_at, -1)))
    active_research = 0
    max_concurrent_research = 0
    for _, delta in sorted(research_timeline, key=lambda point: (point[0], point[1])):
        active_research += delta
        max_concurrent_research = max(max_concurrent_research, active_research)
    query_scopes = Counter(
        scope for row in research_steps for scope in row.get("scopes", [])
    )
    research_decisions = Counter(
        str(row.get("decision", "unknown")) for row in research_steps
    )
    sources = Counter(proposed["proposal_source"]) if not proposed.empty else Counter()
    selected = (
        Counter(proposed["proposed_treatment_id"]) if not proposed.empty else Counter()
    )
    total = sum(selected.values())
    concentration = (
        sum((count / total) ** 2 for count in selected.values()) if total else 0.0
    )
    source_diagnostics = {}
    slot_counts = {
        "rag_applicable": int(frame["applicable_cards"].sum())
        if not frame.empty
        else 0,
        "not_rag_applicable": int(
            (frame["eligible_cards"] - frame["applicable_cards"]).sum()
        )
        if not frame.empty
        else 0,
    }
    total_slate_slots = sum(slot_counts.values())
    for source in ("rag_applicable", "not_rag_applicable"):
        selected_source = proposed[proposed["proposal_source"] == source]
        delivered_source = selected_source[selected_source["delivered"]]
        closed_delivered = delivered_source[
            delivered_source["terminal_status"].isin(("outcome", "invalid"))
        ]
        valid_delivered = closed_delivered[
            closed_delivered["terminal_status"] == "outcome"
        ]
        source_diagnostics[source] = {
            "slate_slots": slot_counts[source],
            "slate_slot_share": (
                slot_counts[source] / total_slate_slots if total_slate_slots else None
            ),
            "proposals": len(selected_source),
            "proposal_share": len(selected_source) / len(proposed)
            if len(proposed)
            else 0.0,
            "delivered": len(delivered_source),
            "closed_delivered": len(closed_delivered),
            "delivered_invalid_rate": (
                float((closed_delivered["terminal_status"] == "invalid").mean())
                if len(closed_delivered)
                else None
            ),
            "mean_valid_delivered_gain": (
                float(valid_delivered["terminal_gain"].mean())
                if len(valid_delivered)
                else None
            ),
            "mean_decision_time_predicted_effect": (
                float(selected_source["predicted_effect"].mean())
                if len(selected_source)
                else None
            ),
        }
    ledger_rows, _ = load_ledger(
        arm.root / "checkpoints" / "memory_v2_selection_evidence.sqlite3", Audit()
    )
    applicability_sets = [
        set(row.decision.applicability.applicable_bank_card_ids)
        for row in ledger_rows
        if row.decision.applicability.applicable_bank_card_ids
    ]
    eligible_union = {
        card_id
        for row in ledger_rows
        for card_id in row.decision.candidate_universe.eligible_bank_card_ids
    }
    applicable_union = {
        card_id
        for row in ledger_rows
        for card_id in row.decision.applicability.applicable_bank_card_ids
    }
    jaccards = []
    for left, right in zip(applicability_sets, applicability_sets[1:]):
        union = left | right
        jaccards.append(len(left & right) / len(union) if union else 1.0)
    return {
        "decisions": len(frame),
        "initial_registry_size": (
            len(ledger_rows[0].decision.lineage_registry) if ledger_rows else None
        ),
        "applicability_statuses": dict(statuses),
        "research_calls": len(research_calls),
        "research_steps": len(research_steps),
        "research_empty_calls": sum(
            row.get("outcome") == "empty" for row in research_calls
        ),
        "research_errors": sum(
            row.get("outcome") == "failed" for row in research_calls
        ),
        "committed_researched_decisions": (
            int(
                (
                    (frame["research_iterations"] > 0)
                    | (
                        frame["applicability_status"]
                        == ApplicabilityStatus.FAILED.value
                    )
                ).sum()
            )
            if not frame.empty
            else 0
        ),
        "query_scopes": dict(query_scopes),
        "research_decisions": dict(research_decisions),
        "median_research_ms": (
            float(np.median(research_durations)) if research_durations else None
        ),
        "p90_research_ms": (
            float(np.percentile(research_durations, 90)) if research_durations else None
        ),
        "max_concurrent_research": max_concurrent_research,
        "mean_query_count": (
            float(np.mean([int(row.get("query_count", 0)) for row in research_steps]))
            if research_steps
            else None
        ),
        "mean_hit_count": (
            float(np.mean([len(row.get("hit_ids", [])) for row in research_steps]))
            if research_steps
            else None
        ),
        "proposal_sources": dict(sources),
        "source_diagnostics": source_diagnostics,
        "unique_proposed_cards": len(selected),
        "proposal_hhi": concentration,
        "mean_consecutive_applicability_jaccard": (
            float(np.mean(jaccards)) if jaccards else None
        ),
        "unique_eligible_cards": len(eligible_union),
        "unique_applicable_cards": len(applicable_union),
        "unique_surfaced_cards": len(eligible_union),
        "nonempty_bank_empty_slate": (
            int(((frame["eligible_cards"] > 0) & (frame["slate_cards"] == 0)).sum())
            if not frame.empty
            else 0
        ),
        "max_eligible_cards": int(frame["eligible_cards"].max())
        if not frame.empty
        else 0,
        "max_slate_cards": int(frame["slate_cards"].max()) if not frame.empty else 0,
    }


def _excerpt(value: Any, limit: int = 220) -> str:
    text = " ".join(str(value).split())
    return text if len(text) <= limit else text[: limit - 3].rstrip() + "..."


def _config_value(config: dict[str, Any], path: str) -> Any:
    value: Any = config
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return None
        value = value[key]
    return value


def _config_signature(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _requested_budget_status(arms: list[ArmData], budget: int) -> tuple[bool, str]:
    configured = {arm.key: _config_value(arm.config, "max_mutants") for arm in arms}
    matches = all(
        isinstance(value, int) and not isinstance(value, bool) and value == budget
        for value in configured.values()
    )
    return matches, f"requested={budget}; configured={configured}"


def _fitness_contract(arm: ArmData, lower: float, upper: float) -> tuple[bool, str]:
    mutant_fitness = arm.trace.loc[arm.trace["valid"], "fitness"]
    seed_fitness = np.asarray(arm.seed_valid_fitnesses, dtype=float)
    valid = bool(
        seed_fitness.size > 0
        and np.isfinite(seed_fitness).all()
        and ((seed_fitness >= lower) & (seed_fitness <= upper)).all()
        and np.isfinite(mutant_fitness).all()
        and mutant_fitness.between(lower, upper).all()
    )
    return (
        valid,
        f"{len(seed_fitness)} valid seeds and {len(mutant_fitness)} valid mutants; "
        f"bounds [{lower}, {upper}]",
    )


def _ledger_metric_contract(
    arms: list[ArmData],
    *,
    asserted_lower: float,
    asserted_upper: float,
    asserted_total_cells: int,
) -> tuple[float, float, int]:
    """Derive bounds and archive cardinality from immutable memory decisions."""

    by_arm: dict[str, tuple[float, float, int]] = {}
    for arm in arms:
        if arm.key == "no_memory":
            continue
        ledger = arm.root / "checkpoints" / "memory_v2_selection_evidence.sqlite3"
        rows, _ = load_ledger(ledger, Audit())
        contracts = {
            (
                float(row.decision.context.reward.metric_lower_bound),
                float(row.decision.context.reward.metric_upper_bound),
                int(row.decision.context.map_elites.total_cells),
            )
            for row in rows
        }
        if len(contracts) != 1:
            raise ValueError(
                f"{arm.key} ledger has non-constant metric/archive contract: "
                f"{sorted(contracts)}"
            )
        by_arm[arm.key] = next(iter(contracts))
    if len(set(by_arm.values())) != 1:
        raise ValueError(
            f"memory ledgers disagree on metric/archive contract: {by_arm}"
        )
    derived = next(iter(by_arm.values()))
    asserted = (asserted_lower, asserted_upper, asserted_total_cells)
    if derived != asserted:
        raise ValueError(
            f"CLI metric/archive assertions {asserted} disagree with ledgers {derived}"
        )
    return derived


def _model_label(value: Any) -> str:
    text = str(value or "unknown")
    return text.rsplit("/", 1)[-1]


def _experiment_contract(arms: list[ArmData], budget: int) -> dict[str, Any]:
    by_key = {arm.key: arm for arm in arms}
    common = arms[0].config
    agentic = by_key["agentic"].config
    memory = _config_value(agentic, "memory")
    memory = memory if isinstance(memory, dict) else {}
    llm_models = _config_value(agentic, "memory.llm.models")
    research_models = (
        [
            _model_label(model.get("model"))
            for model in llm_models
            if isinstance(model, dict)
        ]
        if isinstance(llm_models, list)
        else []
    )
    behavior = _config_value(common, "behavior_space")
    behavior = behavior if isinstance(behavior, dict) else {}
    dimensions = len(behavior.get("keys", ()))
    dynamic = bool(behavior.get("dynamic", False))
    offer_probability = float(memory.get("policy_config", {}).get("offer_probability"))
    writer = memory.get("writer")
    writer = writer if isinstance(writer, dict) else {}
    bank_cap = writer.get("max_task_cards")
    return {
        "problem": str(_config_value(common, "problem.name")),
        "mutation_model": _model_label(_config_value(common, "model_name")),
        "research_model": ", ".join(research_models) or "unknown",
        "budget": budget,
        "num_parents": int(_config_value(common, "num_parents")),
        "memory_seed": int(memory["run_seed"]),
        "offer_probability": offer_probability,
        "behavior_dimensions": dimensions,
        "dynamic_archive": dynamic,
        "bank_cap": bank_cap,
    }


def _class_path(value: type[Any]) -> str:
    return f"{value.__module__}.{value.__qualname__}"


def _arm_contract_issues(arm: ArmData) -> tuple[str, ...]:
    expected = {
        "agentic": {
            "pipeline": "memory_guided_noise",
            "provider": _class_path(CausalBanditMemoryProvider),
            "writer": _class_path(MemoryWriter),
            "candidate": _class_path(WholeBankCandidateSource),
            "applicability": _class_path(AgenticApplicabilityProvider),
            "capabilities": {"read": True, "write": True, "causal_v2": True},
        },
        "whole_bank": {
            "pipeline": "memory_guided_noise",
            "provider": _class_path(CausalBanditMemoryProvider),
            "writer": _class_path(MemoryWriter),
            "candidate": _class_path(WholeBankCandidateSource),
            "applicability": _class_path(NullApplicabilityProvider),
            "capabilities": {"read": True, "write": True, "causal_v2": True},
        },
        "no_memory": {
            "pipeline": "guided",
            "provider": _class_path(NullMemoryProvider),
            "writer": _class_path(NullPostRunHook),
            "candidate": None,
            "applicability": None,
            "capabilities": {"read": False, "write": False},
        },
    }[arm.key]
    actual = {
        "pipeline": _config_value(arm.config, "pipeline.id"),
        "provider": _config_value(arm.config, "memory.provider._target_"),
        "writer": _config_value(arm.config, "memory.writer._target_"),
        "candidate": _config_value(arm.config, "memory.candidate_source._target_"),
        "applicability": _config_value(arm.config, "memory.applicability._target_"),
        "capabilities": _config_value(arm.config, "memory.capabilities"),
    }
    issues = []
    for key in expected:
        if actual[key] == expected[key]:
            continue
        observed = actual[key]
        if key in {"provider", "writer", "candidate"} and isinstance(observed, str):
            observed = observed.rsplit(".", 1)[-1]
        issues.append(f"{key}={observed!r}")
    return tuple(issues)


def _retrieval_contract(arm: ArmData) -> tuple[bool, str]:
    ledger = arm.root / "checkpoints" / "memory_v2_selection_evidence.sqlite3"
    if arm.key == "no_memory":
        absent = not ledger.exists()
        return absent, "ledger absent" if absent else "unexpected causal ledger"
    if not ledger.is_file():
        return False, "causal ledger missing"
    rows, _ = load_ledger(ledger, Audit())
    expected_applicability = "agentic_research" if arm.key == "agentic" else "none"
    allowed_applicability_statuses = (
        frozenset(ApplicabilityStatus) - {ApplicabilityStatus.DISABLED}
        if arm.key == "agentic"
        else {ApplicabilityStatus.DISABLED}
    )
    violations = [
        row.decision.event_ordinal
        for row in rows
        if row.decision.candidate_universe.specification.name != "eligible_bank"
        or row.decision.candidate_universe.status not in CandidateUniverseStatus
        or row.decision.applicability.specification.name != expected_applicability
        or row.decision.applicability.status not in allowed_applicability_statuses
    ]
    universes = Counter(row.decision.candidate_universe.status.value for row in rows)
    statuses = Counter(row.decision.applicability.status.value for row in rows)
    evidence = f"universes={dict(universes)}; applicability={dict(statuses)}"
    if violations:
        evidence += f"; violating ordinals={violations[:5]}"
    return not violations and bool(rows), evidence


def _research_accounting_gate(summary: dict[str, Any]) -> tuple[bool, str]:
    failed_decisions = int(
        summary["applicability_statuses"].get(ApplicabilityStatus.FAILED.value, 0)
    )
    failed_episodes = int(summary["research_errors"])
    research_calls = int(summary["research_calls"])
    committed_decisions = int(summary["committed_researched_decisions"])
    passed = (
        failed_episodes == failed_decisions
        and research_calls >= committed_decisions
        and committed_decisions > 0
    )
    evidence = (
        f"{failed_episodes} failed episodes / {failed_decisions} failed decisions; "
        f"{research_calls} aggregate episodes; "
        f"{committed_decisions} committed research attempts; "
        "events precede decision IDs and are compared in aggregate"
    )
    return passed, evidence


def _retrieval_cases(arm: ArmData, count: int = 3) -> list[dict[str, Any]]:
    rows, _ = load_ledger(
        arm.root / "checkpoints" / "memory_v2_selection_evidence.sqlite3", Audit()
    )
    rows = [
        row
        for row in rows
        if row.decision.applicability.specification.name == "agentic_research"
    ]
    if not rows:
        return []
    if len(rows) == 1 or count == 1:
        selected = [rows[0]]
    else:
        positions = {
            round(index * (len(rows) - 1) / (count - 1)) for index in range(count)
        }
        selected = [rows[index] for index in sorted(positions)]
    programs = {str(row["id"]): row for row in _program_rows(arm.root)}
    cases = []
    for row in selected:
        record = row.decision
        snapshots = {card.bank_card_id: card for card in record.candidates}
        proposed_id = record.proposed_treatment_id
        proposed = next(
            (card for card in record.candidates if card.treatment_id == proposed_id),
            None,
        )
        source = (
            "RAG applicable"
            if proposed is not None
            and proposed.bank_card_id in record.applicability.applicable_bank_card_ids
            else "not RAG applicable"
            if proposed is not None
            else "abstention"
        )
        terminal = row.terminal
        terminal_value = (
            terminal.measurement.value
            if terminal is not None and terminal.measurement is not None
            else None
        )
        coordinates = ", ".join(
            f"{coordinate.key}={coordinate.dynamic_normalized:.3f}"
            for coordinate in record.context.map_elites.coordinates
        )
        cases.append(
            {
                "ordinal": record.event_ordinal + 1,
                "parent_fitness": record.context.parent_metrics.get("fitness"),
                "parent_quantile": (record.context.map_elites.parent_quality_quantile),
                "coordinates": coordinates or "none",
                "parent_excerpt": _excerpt(
                    programs.get(record.context.parent_id, {}).get(
                        "code", "Parent source unavailable."
                    ),
                    limit=360,
                ),
                "eligible": len(record.candidate_universe.eligible_bank_card_ids),
                "applicable": len(record.applicability.applicable_bank_card_ids),
                "applicable_advice": [
                    _excerpt(snapshots[card_id].payload)
                    for card_id in record.applicability.applicable_bank_card_ids[:3]
                    if card_id in snapshots
                ],
                "source": source,
                "assignment": (
                    "delivered"
                    if record.delivered
                    else "matched control"
                    if proposed_id
                    else "abstained"
                ),
                "terminal_status": terminal.status
                if terminal is not None
                else "pending",
                "terminal_value": terminal_value,
                "proposed_advice": (
                    _excerpt(snapshots[proposed_id].payload)
                    if proposed_id in snapshots
                    else "No card proposed."
                ),
            }
        )
    return cases


def _gates(
    arms: list[ArmData], budget: int, lower: float, upper: float
) -> pd.DataFrame:
    by_key = {arm.key: arm for arm in arms}
    signatures = {arm.seed_signature for arm in arms}
    common_paths = (
        "problem.name",
        "model_name",
        "llm_base_url",
        "temperature",
        "max_tokens",
        "num_parents",
        "mutation_mode",
        "max_mutants",
        "program_format.id",
        "mutation_operator._target_",
        "behavior_space",
        "islands",
        "evolution_strategy",
        "archive_selector",
        "parent_selector",
        "program_acceptor",
        "engine_config",
        "stopper",
    )
    common_mismatches = [
        path
        for path in common_paths
        if len({_config_signature(_config_value(arm.config, path)) for arm in arms})
        != 1
    ]
    memory_paths = (
        "memory.posterior_config",
        "memory.policy_config",
        "memory.safety",
        "memory.credit",
        "memory.causal_writer_updater",
    )
    memory_arms = (by_key["agentic"], by_key["whole_bank"])
    memory_mismatches = [
        path
        for path in memory_paths
        if _config_value(memory_arms[0].config, path)
        != _config_value(memory_arms[1].config, path)
    ]
    memory_contracts = []
    for arm in memory_arms:
        memory = _config_value(arm.config, "memory")
        memory_contracts.append(
            {key: value for key, value in memory.items() if key != "candidate_source"}
            if isinstance(memory, dict)
            else memory
        )
    if memory_contracts[0] != memory_contracts[1]:
        memory_mismatches.append("memory excluding candidate_source")
    budget_matches, budget_evidence = _requested_budget_status(arms, budget)
    rows = [
        ("Matched initial programs", len(signatures) == 1, "code and seed metrics"),
        (
            "Common task and mutator contract matched",
            not common_mismatches,
            "matched" if not common_mismatches else str(common_mismatches),
        ),
        (
            "Memory inference and writer contract matched",
            not memory_mismatches,
            "matched" if not memory_mismatches else str(memory_mismatches),
        ),
        ("Requested budget matches run configs", budget_matches, budget_evidence),
    ]
    for arm in arms:
        contract_issues = _arm_contract_issues(arm)
        rows.append(
            (
                f"{ARM_LABELS[arm.key]} arm contract",
                not contract_issues,
                "matched" if not contract_issues else "; ".join(contract_issues),
            )
        )
    for arm in arms:
        fitness_ok, fitness_evidence = _fitness_contract(arm, lower, upper)
        failed_calls = (
            arm.llm_calls[~arm.llm_calls["ok"].astype(bool)]
            if not arm.llm_calls.empty
            else arm.llm_calls
        )
        retrieval_failures = (
            failed_calls[failed_calls["category"] == "retrieval"]
            if not failed_calls.empty
            else failed_calls
        )
        mutation_failures = (
            int((failed_calls["category"] == "mutation").sum())
            if not failed_calls.empty
            else 0
        )
        fail_soft_writer_failures = (
            int((failed_calls["category"] == "writer").sum())
            if not failed_calls.empty
            else 0
        )
        rows.extend(
            (
                (
                    f"{ARM_LABELS[arm.key]} completed budget",
                    arm.trace["mutant_index"].tolist() == list(range(1, budget + 1)),
                    f"contiguous 1..{len(arm.trace)} / expected 1..{budget}",
                ),
                (
                    f"{ARM_LABELS[arm.key]} finite valid seed and mutant fitness",
                    fitness_ok,
                    fitness_evidence,
                ),
                (
                    f"{ARM_LABELS[arm.key]} reporter/storage agreement",
                    bool(arm.trace["reporter_storage_match"].all()),
                    f"{int((~arm.trace['reporter_storage_match']).sum())} mismatches; "
                    f"{int((arm.trace['valid'] & ~arm.trace['reporter_present']).sum())} valid programs absent from reporter stream",
                ),
                (
                    f"{ARM_LABELS[arm.key]} completion counter aligned",
                    bool(
                        not arm.archive.empty
                        and int(arm.archive["mutant_index"].max()) == budget
                    ),
                    (
                        f"final={int(arm.archive['mutant_index'].max())}"
                        if not arm.archive.empty
                        else "missing"
                    ),
                ),
                (
                    f"{ARM_LABELS[arm.key]} retrieval LLM calls succeeded",
                    retrieval_failures.empty,
                    f"{len(retrieval_failures)} retrieval failures; "
                    f"{mutation_failures} recovered mutation failures; "
                    f"{fail_soft_writer_failures} fail-soft writer timeouts",
                ),
                (
                    f"{ARM_LABELS[arm.key]} execution logs present",
                    arm.log_segments > 0 and arm.llm_log_segments > 0,
                    f"{arm.log_segments} execution segments; "
                    f"{arm.llm_log_segments} with LLM calls",
                ),
            )
        )
    for key in ("agentic", "whole_bank"):
        arm = by_key[key]
        retrieval_summary = _retrieval_summary(arm)
        retrieval_contract_ok, retrieval_contract_evidence = _retrieval_contract(arm)
        pending_terminals = int(
            (arm.memory_trace["terminal_status"] == "pending").sum()
        )
        closed_terminals = len(arm.memory_trace) - pending_terminals
        closed = not arm.memory_trace.empty and pending_terminals == 0
        rows.extend(
            (
                (
                    f"{ARM_LABELS[key]} ledger integrity",
                    bool(
                        arm.sqlite_integrity == "ok"
                        and arm.memory_audit is not None
                        and not arm.memory_audit.errors
                    ),
                    arm.sqlite_integrity or "missing",
                ),
                (
                    f"{ARM_LABELS[key]} program-ledger linkage",
                    not arm.storage_ledger_issues,
                    (
                        "all terminal/base metrics agree with program storage"
                        if not arm.storage_ledger_issues
                        else f"{len(arm.storage_ledger_issues)} mismatches; "
                        f"first={arm.storage_ledger_issues[0]}"
                    ),
                ),
                (
                    f"{ARM_LABELS[key]} decision ordinals contiguous",
                    arm.decision_ordinals_contiguous,
                    "0..N-1" if arm.decision_ordinals_contiguous else "gap or reorder",
                ),
                (
                    f"{ARM_LABELS[key]} applicability contract",
                    retrieval_contract_ok,
                    retrieval_contract_evidence,
                ),
                (
                    f"{ARM_LABELS[key]} terminal closure",
                    bool(closed and len(arm.memory_trace) == budget),
                    f"{closed_terminals} closed + {pending_terminals} pending / "
                    f"{len(arm.memory_trace)} decisions; expected {budget}",
                ),
                (
                    f"{ARM_LABELS[key]} depth-1 readiness audit",
                    arm.audit_metrics.get("depth1_core_ready") is True,
                    (
                        "ready"
                        if arm.audit_metrics.get("depth1_core_ready") is True
                        else "not ready; see per-run audit"
                    ),
                ),
                (
                    f"{ARM_LABELS[key]} randomized offer support",
                    arm.audit_metrics.get("randomized_support_ready") is True,
                    f"eligible treated={arm.audit_metrics.get('eligible_ope_treated')}; "
                    f"eligible control={arm.audit_metrics.get('eligible_ope_control')}",
                ),
                (
                    f"{ARM_LABELS[key]} card-lineage evidence accumulated",
                    arm.audit_metrics.get("support_accumulated") is True,
                    f"support-ready={arm.audit_metrics.get('support_ready_card_lineages')}/"
                    f"{arm.audit_metrics.get('stable_card_lineages_with_offers')}",
                ),
                (
                    f"{ARM_LABELS[key]} no sustained trailing safety lockout",
                    arm.audit_metrics.get("sustained_safety_lockout_absent") is True,
                    f"trailing={arm.audit_metrics.get('trailing_safety_lockout_decisions')}; "
                    f"maximum={arm.audit_metrics.get('max_trailing_safety_lockout_decisions')}",
                ),
                (
                    f"{ARM_LABELS[key]} conditional-offer OPE complete",
                    arm.audit_metrics.get("ope_complete") is True,
                    f"reports={arm.audit_metrics.get('ope_reports')}; "
                    f"observations={arm.audit_metrics.get('ope_expected_observations')}; "
                    f"error={arm.audit_metrics.get('ope_error')}",
                ),
                (
                    f"{ARM_LABELS[key]} posterior config provenance",
                    arm.audit_metrics.get("posterior_config_matches_ledger") is True,
                    str(arm.audit_metrics.get("posterior_config_matches_ledger")),
                ),
                (
                    f"{ARM_LABELS[key]} policy config provenance",
                    arm.audit_metrics.get("policy_config_matches_ledger") is True,
                    str(arm.audit_metrics.get("policy_config_matches_ledger")),
                ),
                (
                    f"{ARM_LABELS[key]} candidate-universe provenance",
                    arm.audit_metrics.get("candidate_universe_config_matches_ledger")
                    is True,
                    str(
                        arm.audit_metrics.get(
                            "candidate_universe_config_matches_ledger"
                        )
                    ),
                ),
                (
                    f"{ARM_LABELS[key]} RAG applicability provenance",
                    arm.audit_metrics.get("applicability_config_matches_ledger")
                    is True,
                    str(arm.audit_metrics.get("applicability_config_matches_ledger")),
                ),
                (
                    f"{ARM_LABELS[key]} run-seed provenance",
                    arm.audit_metrics.get("run_seed_matches_ledger") is True,
                    str(arm.audit_metrics.get("run_seed_matches_ledger")),
                ),
                (
                    f"{ARM_LABELS[key]} writer/final-bank agreement",
                    arm.audit_metrics.get("writer_bank_matches_final") is True,
                    str(arm.audit_metrics.get("writer_bank_matches_final")),
                ),
                (
                    f"{ARM_LABELS[key]} started with empty bank",
                    retrieval_summary["initial_registry_size"] == 0,
                    f"initial registry={retrieval_summary['initial_registry_size']}",
                ),
            )
        )
    agentic_summary = _retrieval_summary(by_key["agentic"])
    research_accounting_ok, research_accounting_evidence = _research_accounting_gate(
        agentic_summary
    )
    whole_retrieval_llm_calls = int(
        (by_key["whole_bank"].llm_calls["category"] == "retrieval").sum()
    )
    rows.extend(
        (
            (
                "Agentic applicability produced labels",
                agentic_summary["applicability_statuses"].get(
                    ApplicabilityStatus.ASSESSED.value, 0
                )
                > 0,
                str(agentic_summary["applicability_statuses"]),
            ),
            (
                "Agentic aggregate research accounting present",
                research_accounting_ok,
                research_accounting_evidence,
            ),
            (
                "Agentic nonempty-bank slate continuity",
                agentic_summary["nonempty_bank_empty_slate"] == 0,
                f"{agentic_summary['nonempty_bank_empty_slate']} empty slates",
            ),
            (
                "Whole-bank arm made no retrieval LLM calls",
                whole_retrieval_llm_calls == 0,
                f"{whole_retrieval_llm_calls} calls",
            ),
            (
                "No-memory arm has no causal ledger",
                _retrieval_contract(by_key["no_memory"])[0],
                _retrieval_contract(by_key["no_memory"])[1],
            ),
        )
    )
    return pd.DataFrame(rows, columns=["gate", "passed", "evidence"])


def _annotate_intentional_agentic_stop(
    gates: pd.DataFrame,
    agentic: ArmData,
    *,
    budget: int,
    enabled: bool,
) -> tuple[pd.DataFrame, bool]:
    """Separate stop-induced closure limits from implementation failures."""
    result = gates.copy()
    result["expected_limitation"] = False
    pending = (
        int((agentic.memory_trace["terminal_status"] == "pending").sum())
        if not agentic.memory_trace.empty
        else 0
    )
    accepted = bool(
        enabled
        and len(agentic.memory_trace) == budget
        and pending > 0
        and set(agentic.audit_metrics.get("failed_readiness_gates", ()))
        == {"terminal closure"}
    )
    if accepted:
        stop_derived = {
            f"{ARM_LABELS['agentic']} completed budget",
            f"{ARM_LABELS['agentic']} completion counter aligned",
            f"{ARM_LABELS['agentic']} terminal closure",
            f"{ARM_LABELS['agentic']} depth-1 readiness audit",
        }
        result.loc[
            (~result["passed"].astype(bool)) & result["gate"].isin(stop_derived),
            "expected_limitation",
        ] = True
    result["blocks_readiness"] = ~(
        result["passed"].astype(bool) | result["expected_limitation"].astype(bool)
    )
    return result, accepted


def _figure(title: str, subtitle: str, size: tuple[float, float] = (12.4, 7.2)):
    fig = plt.figure(figsize=size)
    fig.text(0.055, 0.965, title, fontsize=18, weight="bold", color=INK, va="top")
    fig.text(0.055, 0.925, subtitle, fontsize=9.5, color=MUTED, va="top")
    return fig


def _save(fig: plt.Figure, paths: ReportPaths, name: str) -> None:
    paths.figures.mkdir(parents=True, exist_ok=True)
    fig.savefig(paths.figures / f"{name}.pdf", dpi=220, bbox_inches="tight")
    fig.savefig(paths.figures / f"{name}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def render_contract(arms: list[ArmData], paths: ReportPaths, budget: int) -> None:
    contract = _experiment_contract(arms, budget)
    offer = float(contract["offer_probability"])
    offer_label = f"{100.0 * offer:.0f}/{100.0 * (1.0 - offer):.0f}"
    archive_mode = "dynamic" if contract["dynamic_archive"] else "fixed"
    dimensions = int(contract["behavior_dimensions"])
    parents = int(contract["num_parents"])
    parent_label = "parent" if parents == 1 else "parents"
    fixed_label = (
        f"Fixed: {contract['problem']}, {contract['mutation_model']} mutation, "
        f"{contract['budget']} mutants, memory seed={contract['memory_seed']}, "
        f"{parents} {parent_label}, {archive_mode} {dimensions}D MAP-Elites"
    )
    fig = _figure(
        "Experimental contract",
        "One matched adaptive trajectory per arm; differences are descriptive, not independent replicates.",
    )
    ax = fig.add_axes([0.055, 0.10, 0.89, 0.75])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    for index, arm in enumerate(arms):
        y = 0.72 - index * 0.27
        color = ARM_COLORS[arm.key]
        ax.add_patch(
            FancyBboxPatch(
                (0.02, y),
                0.96,
                0.19,
                boxstyle="round,pad=0.008,rounding_size=0.012",
                facecolor="white",
                edgecolor=color,
                linewidth=1.8,
            )
        )
        ax.text(
            0.05,
            y + 0.135,
            ARM_LABELS[arm.key],
            color=color,
            weight="bold",
            fontsize=13,
        )
        if arm.key == "agentic":
            detail = (
                f"{contract['research_model']} research -> frozen RAG label + "
                f"full-bank Bayesian selector -> {offer_label} offer"
            )
        elif arm.key == "whole_bank":
            detail = (
                "All eligible cards -> same Bayesian selector, posterior, writer, "
                f"safety gate, and {offer_label} offer"
            )
        else:
            detail = "Guided mutation with null reader/writer; no card, retrieval, posterior, or memory-LLM calls"
        ax.text(0.05, y + 0.075, detail, color=INK, fontsize=9.5)
        ax.text(
            0.05,
            y + 0.025,
            fixed_label,
            color=MUTED,
            fontsize=8.5,
        )
    _save(fig, paths, "01_experimental_contract")


def render_search(arms: list[ArmData], paths: ReportPaths, metric_upper: float) -> None:
    fig = _figure(
        "Search outcome by mutation budget",
        "Best-so-far is a correlated adaptive-search statistic; raw valid scores and invalid attempts show its support.",
        (12.4, 8.4),
    )
    grid = fig.add_gridspec(
        2, 1, left=0.075, right=0.97, bottom=0.08, top=0.86, hspace=0.18
    )
    top = fig.add_subplot(grid[0])
    bottom = fig.add_subplot(grid[1])
    for arm in arms:
        color = ARM_COLORS[arm.key]
        trace = arm.trace
        top.plot(
            trace["mutant_index"],
            trace["best_fitness"],
            color=color,
            lw=2.2,
            label=ARM_LABELS[arm.key],
        )
        valid = trace[trace["valid"]]
        bottom.scatter(
            valid["mutant_index"],
            valid["fitness"],
            s=13,
            color=color,
            alpha=0.35,
            label=ARM_LABELS[arm.key],
        )
        invalid = trace[~trace["valid"]]
        bottom.scatter(
            invalid["mutant_index"],
            np.full(len(invalid), -0.001),
            marker="|",
            s=45,
            color=color,
            alpha=0.45,
        )
    top.axhline(
        metric_upper,
        color=MUTED,
        lw=1,
        ls="--",
        label=f"Configured upper bound {metric_upper:g}",
    )
    top.set_ylabel("Best valid fitness")
    top.legend(ncol=4, loc="lower right")
    bottom.set_xlabel("Attempted mutant")
    bottom.set_ylabel("Raw valid fitness")
    _save(fig, paths, "02_search_by_budget")


def render_wall_time(arms: list[ArmData], paths: ReportPaths) -> None:
    fig = _figure(
        "Search outcome and throughput by wall time",
        "Fitness uses mutant/program creation time; completion throughput comes from the engine counter.",
    )
    left = fig.add_axes([0.075, 0.13, 0.42, 0.72])
    right = fig.add_axes([0.56, 0.13, 0.41, 0.72])
    for arm in arms:
        minutes = arm.trace["elapsed_seconds"] / 60.0
        color = ARM_COLORS[arm.key]
        left.plot(
            minutes,
            arm.trace["best_fitness"],
            color=color,
            lw=2.2,
            label=ARM_LABELS[arm.key],
        )
        if not arm.archive.empty:
            right.plot(
                arm.archive["elapsed_seconds"] / 60.0,
                arm.archive["mutant_index"],
                color=color,
                lw=2.2,
                label=ARM_LABELS[arm.key],
            )
    left.set_xlabel("Minutes from run start (mutant/program creation time)")
    left.set_ylabel("Best valid fitness")
    left.legend()
    right.set_xlabel("Minutes from run start")
    right.set_ylabel("Completed mutants")
    _save(fig, paths, "03_wall_time_and_throughput")


def render_reliability(
    arms: list[ArmData], paths: ReportPaths, total_cells: int
) -> None:
    fig = _figure(
        "Reliability and archive coverage",
        "Validity is shown in non-overlapping 25-mutant blocks; archive occupancy uses the live MAP-Elites metric.",
    )
    left = fig.add_axes([0.075, 0.13, 0.42, 0.72])
    right = fig.add_axes([0.56, 0.13, 0.41, 0.72])
    width = 0.24
    block_count = max(math.ceil(len(arm.trace) / 25) for arm in arms)
    blocks = np.arange(block_count)
    for offset, arm in enumerate(arms):
        trace = arm.trace.copy()
        trace["block"] = (trace["mutant_index"] - 1) // 25
        rates = trace.groupby("block")["valid"].mean().reindex(blocks)
        left.bar(
            blocks + (offset - 1) * width,
            rates,
            width=width,
            color=ARM_COLORS[arm.key],
            alpha=0.82,
            label=ARM_LABELS[arm.key],
        )
        if not arm.archive.empty:
            right.step(
                arm.archive["mutant_index"],
                arm.archive["archive_cells"] / total_cells,
                where="post",
                color=ARM_COLORS[arm.key],
                lw=2,
                label=ARM_LABELS[arm.key],
            )
    left.set_xticks(blocks)
    left.set_xticklabels(
        [
            f"{25 * i + 1}-{min(25 * (i + 1), max(len(arm.trace) for arm in arms))}"
            for i in blocks
        ],
        rotation=45,
        ha="right",
    )
    left.set_ylim(0, 1)
    left.set_ylabel("Valid fraction")
    left.legend(fontsize=8)
    right.set_xlabel("Processed mutant")
    right.set_ylabel(f"Archive coverage (occupied/{total_cells})")
    right.set_ylim(0, 0.55)
    _save(fig, paths, "04_reliability_and_archive")


def render_memory(arms: list[ArmData], paths: ReportPaths) -> None:
    memories = [arm for arm in arms if not arm.memory_trace.empty]
    fig = _figure(
        "Memory candidate flow",
        "Both memory arms evaluate the full eligible bank; agentic RAG adds only a learned applicability signal.",
        (12.4, 8.2),
    )
    grid = fig.add_gridspec(
        2, 2, left=0.07, right=0.97, bottom=0.08, top=0.86, hspace=0.28, wspace=0.24
    )
    for col, arm in enumerate(memories):
        frame = arm.memory_trace
        top = fig.add_subplot(grid[0, col])
        top.plot(
            frame["decision_index"],
            frame["eligible_cards"],
            color=MUTED,
            lw=1.5,
            label="eligible bank",
        )
        top.plot(
            frame["decision_index"],
            frame["slate_cards"],
            color=ARM_COLORS[arm.key],
            lw=2,
            label="slate",
        )
        if arm.key == "agentic":
            top.plot(
                frame["decision_index"],
                frame["applicable_cards"],
                color=PURPLE,
                lw=1.4,
                label="RAG applicable",
            )
        top.set_title(ARM_LABELS[arm.key])
        top.set_ylabel("Cards")
        top.legend(fontsize=8)
        bottom = fig.add_subplot(grid[1, col])
        bottom.plot(
            frame["decision_index"],
            frame["evidence_count"],
            color=ARM_COLORS[arm.key],
            lw=2,
            label="closed evidence",
        )
        bottom.plot(
            frame["decision_index"],
            frame["safe_candidates"],
            color=RED,
            lw=1.2,
            alpha=0.8,
            label="safe candidates",
        )
        bottom.set_xlabel("Memory decision")
        bottom.set_ylabel("Count")
        bottom.legend(fontsize=8)
    _save(fig, paths, "05_memory_candidate_flow")


def render_randomization(arms: list[ArmData], paths: ReportPaths) -> None:
    memories = [arm for arm in arms if not arm.memory_trace.empty]
    fig = _figure(
        "Randomized offer calibration",
        "Residual is cumulative delivered minus cumulative logged expectation, conditional on a proposed card.",
    )
    left = fig.add_axes([0.075, 0.13, 0.55, 0.72])
    right = fig.add_axes([0.70, 0.16, 0.27, 0.66])
    labels = []
    delivered = []
    controls = []
    for arm in memories:
        proposed = arm.memory_trace[arm.memory_trace["proposed"]].copy()
        proposed["expected"] = proposed["offer_probability"].fillna(0.0)
        proposed["residual"] = proposed["delivered"].astype(int) - proposed["expected"]
        left.plot(
            np.arange(1, len(proposed) + 1),
            proposed["residual"].cumsum(),
            color=ARM_COLORS[arm.key],
            lw=2,
            label=ARM_LABELS[arm.key],
        )
        labels.append(ARM_LABELS[arm.key])
        delivered.append(int(proposed["delivered"].sum()))
        controls.append(int((~proposed["delivered"]).sum()))
    left.axhline(0, color=MUTED, lw=1)
    left.set_xlabel("Proposed-card opportunities")
    left.set_ylabel("Cumulative delivered - expected")
    left.legend()
    y = np.arange(len(labels))
    right.barh(y, delivered, color=TEAL, label="delivered")
    right.barh(
        y, controls, left=delivered, color=LIGHT, edgecolor=GRID, label="control"
    )
    right.set_yticks(y)
    right.set_yticklabels(labels)
    right.set_xlabel("Proposals")
    right.legend(fontsize=8)
    _save(fig, paths, "06_randomization_calibration")


def render_agentic_retrieval(arm: ArmData, paths: ReportPaths) -> None:
    frame = arm.memory_trace.copy()
    research = [
        row for row in arm.memory_events if row.get("event") == "MEMORY_RESEARCH_STEP"
    ]
    fig = _figure(
        "Agentic applicability dossier",
        "Research activity, frozen applicability labels, proposal source, and downstream assignment are shown separately.",
        (12.4, 8.6),
    )
    grid = fig.add_gridspec(
        2,
        2,
        left=0.07,
        right=0.97,
        bottom=0.08,
        top=0.86,
        hspace=0.30,
        wspace=0.24,
    )
    status_ax = fig.add_subplot(grid[0, 0])
    statuses = list(ApplicabilityStatus)
    status_y = {value: index for index, value in enumerate(statuses)}
    colors = {
        ApplicabilityStatus.DISABLED: MUTED,
        ApplicabilityStatus.ASSESSED: BLUE,
        ApplicabilityStatus.EMPTY: ORANGE,
        ApplicabilityStatus.FAILED: RED,
    }
    for status in statuses:
        selected = frame[frame["applicability_status"] == status.value]
        status_ax.scatter(
            selected["decision_index"],
            np.full(len(selected), status_y[status]),
            s=18,
            color=colors[status],
            alpha=0.75,
            label=status.value.replace("_", " "),
        )
    status_ax.set_yticks(range(len(statuses)))
    status_ax.set_yticklabels([status.value.replace("_", " ") for status in statuses])
    status_ax.set_xlabel("Memory decision")
    status_ax.set_title("Applicability outcome over the run")

    research_ax = fig.add_subplot(grid[0, 1])
    if research:
        x = np.arange(1, len(research) + 1)
        queries = [int(row.get("query_count", 0)) for row in research]
        hits = [len(row.get("hit_ids", [])) for row in research]
        research_ax.plot(x, queries, color=PURPLE, lw=1.4, label="queries")
        research_ax.plot(x, hits, color=TEAL, lw=1.4, label="raw hits")
        latency_ax = research_ax.twinx()
        latency_ax.plot(
            x,
            [float(row.get("duration_ms", 0.0)) / 1000.0 for row in research],
            color=ORANGE,
            lw=1.0,
            alpha=0.65,
            label="latency",
        )
        latency_ax.set_ylabel("Seconds", color=ORANGE)
        research_ax.set_xlabel("Research episode")
        research_ax.set_ylabel("Count")
        lines = research_ax.lines + latency_ax.lines
        research_ax.legend(lines, [line.get_label() for line in lines], fontsize=8)
    else:
        research_ax.text(0.5, 0.5, "No research calls", ha="center", va="center")
    research_ax.set_title("LLM research breadth and latency")

    source_ax = fig.add_subplot(grid[1, 0])
    proposed = frame[frame["proposed"]].copy()
    if not proposed.empty:
        source_table = (
            proposed.groupby(["proposal_source", "delivered"])
            .size()
            .unstack(fill_value=0)
        )
        labels = list(source_table.index)
        control = source_table.get(False, pd.Series(0, index=labels)).to_numpy()
        treated = source_table.get(True, pd.Series(0, index=labels)).to_numpy()
        y = np.arange(len(labels))
        source_ax.barh(y, treated, color=TEAL, label="delivered")
        source_ax.barh(
            y,
            control,
            left=treated,
            color=LIGHT,
            edgecolor=GRID,
            label="control",
        )
        source_ax.set_yticks(y)
        source_ax.set_yticklabels([value.replace("_", " ") for value in labels])
        source_ax.legend(fontsize=8)
    source_ax.set_xlabel("Proposals")
    source_ax.set_title("Where selected cards came from")

    coverage_ax = fig.add_subplot(grid[1, 1])
    nonempty = frame[frame["eligible_cards"] > 0].copy()
    if not nonempty.empty:
        nonempty["slate_coverage"] = (
            nonempty["slate_cards"] / nonempty["eligible_cards"]
        )
        nonempty["applicability_share"] = nonempty["applicable_cards"] / nonempty[
            "eligible_cards"
        ].replace(0, np.nan)
        coverage_ax.plot(
            nonempty["decision_index"],
            nonempty["slate_coverage"],
            color=BLUE,
            lw=1.7,
            label="slate / eligible bank",
        )
        coverage_ax.plot(
            nonempty["decision_index"],
            nonempty["applicability_share"],
            color=PURPLE,
            lw=1.4,
            label="RAG applicable / eligible",
        )
        coverage_ax.set_ylim(0, 1.05)
        coverage_ax.legend(fontsize=8)
    coverage_ax.set_xlabel("Memory decision")
    coverage_ax.set_ylabel("Fraction")
    coverage_ax.set_title("Full-bank coverage and applicability")
    _save(fig, paths, "08_agentic_retrieval_dossier")


def render_posteriors(
    audit_dirs: dict[str, Path], paths: ReportPaths, limit: int = 14
) -> None:
    fig = _figure(
        "Final fitted card effects",
        "Posterior means and normal 95% summaries at each run's final representative context; color is P(safe and helpful).",
        (12.4, 8.8),
    )
    grid = fig.add_gridspec(
        1, 2, left=0.08, right=0.97, bottom=0.08, top=0.86, wspace=0.42
    )
    for col, key in enumerate(("agentic", "whole_bank")):
        ax = fig.add_subplot(grid[0, col])
        path = audit_dirs[key] / "tables" / "live_final_posterior.csv"
        frame = pd.read_csv(path).head(limit) if path.is_file() else pd.DataFrame()
        if frame.empty:
            ax.text(
                0.5,
                0.5,
                "Posterior table unavailable",
                ha="center",
                va="center",
                color=MUTED,
            )
            ax.axis("off")
            continue
        frame = frame.sort_values("effect_mean")
        y = np.arange(len(frame))
        low = frame["effect_mean"] - frame["effect_lower_normal"]
        high = frame["effect_upper_normal"] - frame["effect_mean"]
        colors = plt.cm.viridis(frame["probability_safe_and_helpful"].clip(0, 1))
        ax.errorbar(
            frame["effect_mean"],
            y,
            xerr=np.vstack([low, high]),
            fmt="none",
            ecolor=GRID,
            capsize=2,
        )
        ax.scatter(
            frame["effect_mean"], y, c=colors, s=42, edgecolor="white", linewidth=0.5
        )
        ax.axvline(0, color=MUTED, lw=1)
        ax.set_yticks(y)
        ax.set_yticklabels(
            [str(value)[:16] for value in frame["treatment_id"]], fontsize=7.5
        )
        ax.set_title(ARM_LABELS[key])
        ax.set_xlabel("Normalized usable effect")
    _save(fig, paths, "07_final_card_posteriors")


def render_resources(arms: list[ArmData], paths: ReportPaths) -> None:
    fig = _figure(
        "LLM resource profile",
        "Token and call totals are observed accounting; retrieval and writer overhead are separated from mutation work.",
    )
    left = fig.add_axes([0.075, 0.15, 0.42, 0.68])
    right = fig.add_axes([0.56, 0.15, 0.41, 0.68])
    categories = ["mutation", "retrieval", "writer", "other"]
    colors = [BLUE, PURPLE, ORANGE, MUTED]
    x = np.arange(len(arms))
    call_bottom = np.zeros(len(arms))
    token_bottom = np.zeros(len(arms))
    for category, color in zip(categories, colors):
        calls = []
        tokens = []
        for arm in arms:
            frame = arm.llm_calls
            selected = (
                frame[frame["category"] == category] if not frame.empty else frame
            )
            calls.append(len(selected))
            tokens.append(
                float(selected["total_tokens"].sum()) / 1e6
                if not selected.empty
                else 0.0
            )
        left.bar(x, calls, bottom=call_bottom, color=color, label=category)
        right.bar(x, tokens, bottom=token_bottom, color=color, label=category)
        call_bottom += calls
        token_bottom += tokens
    labels = [ARM_LABELS[arm.key] for arm in arms]
    for ax in (left, right):
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=15, ha="right")
    left.set_ylabel("LLM calls")
    right.set_ylabel("Tokens (millions)")
    left.legend(fontsize=8)
    _save(fig, paths, "09_llm_resources")


def render_gates(gates: pd.DataFrame, paths: ReportPaths) -> None:
    fig = _figure(
        "Integrity and readiness summary",
        "Every raw gate remains in the following evidence table; this dashboard groups the mechanical verdict.",
        (12.4, 8.2),
    )
    grouped = gates.copy()

    def group_name(gate: str) -> str:
        if gate.startswith(ARM_LABELS["agentic"]):
            return "Agentic arm"
        if gate.startswith(ARM_LABELS["whole_bank"]):
            return "Whole-bank arm"
        if gate.startswith(ARM_LABELS["no_memory"]):
            return "No-memory arm"
        if gate.startswith(("Matched", "Common", "Memory inference", "Requested")):
            return "Cross-arm contract"
        return "Retrieval ablation"

    grouped["group"] = grouped["gate"].map(group_name)
    grouped["raw_pass"] = grouped["passed"].astype(bool)
    grouped["expected"] = grouped["expected_limitation"].astype(bool)
    grouped["blocking"] = grouped["blocks_readiness"].astype(bool)
    order = [
        "Cross-arm contract",
        "Agentic arm",
        "Whole-bank arm",
        "No-memory arm",
        "Retrieval ablation",
    ]
    counts = grouped.groupby("group")[["raw_pass", "expected", "blocking"]].sum()
    counts = counts.reindex(order).fillna(0)

    raw_passes = int(grouped["raw_pass"].sum())
    expected_count = int(grouped["expected"].sum())
    blocking_count = int(grouped["blocking"].sum())
    fig.text(
        0.08,
        0.86,
        f"{raw_passes} raw passes",
        color=GREEN,
        fontsize=16,
        weight="bold",
    )
    fig.text(
        0.37,
        0.86,
        f"{expected_count} expected stop limits",
        color=ORANGE,
        fontsize=16,
        weight="bold",
    )
    fig.text(
        0.75,
        0.86,
        f"{blocking_count} blocking failures",
        color=GREEN if blocking_count == 0 else RED,
        fontsize=16,
        weight="bold",
    )

    ax = fig.add_axes([0.19, 0.43, 0.72, 0.34])
    y = np.arange(len(order))
    left = np.zeros(len(order))
    for column, label, color in (
        ("raw_pass", "Raw pass", GREEN),
        ("expected", "Expected stop", ORANGE),
        ("blocking", "Blocking failure", RED),
    ):
        values = counts[column].to_numpy(dtype=float)
        ax.barh(y, values, left=left, color=color, label=label, height=0.55)
        for index, value in enumerate(values):
            if value > 0:
                ax.text(
                    left[index] + value / 2,
                    index,
                    str(int(value)),
                    ha="center",
                    va="center",
                    color="white",
                    fontsize=9,
                    weight="bold",
                )
        left += values
    ax.set_yticks(y)
    ax.set_yticklabels(order)
    ax.invert_yaxis()
    ax.set_xlabel("Number of declared gates")
    ax.set_xlim(0, max(float(left.max()) + 1.0, 5.0))
    ax.legend(loc="lower right", frameon=False, ncol=3, bbox_to_anchor=(1.0, 1.02))

    expected_rows = grouped[grouped["expected"]]
    detail = fig.add_axes([0.08, 0.08, 0.84, 0.25])
    detail.axis("off")
    detail.text(
        0.0,
        0.98,
        "Explicit stop-induced limitations",
        color=INK,
        fontsize=12,
        weight="bold",
        va="top",
    )
    for index, row in enumerate(expected_rows.itertuples(index=False)):
        detail.text(
            0.01,
            0.78 - index * 0.19,
            f"{row.gate}: {row.evidence}",
            color=MUTED,
            fontsize=9.2,
            va="top",
        )
    _save(fig, paths, "10_integrity_gates")


def _tex(value: Any) -> str:
    text = str(value)
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
        "\u2264": r"\(\leq\)",
        "\u2265": r"\(\geq\)",
    }
    return "".join(replacements.get(char, char) for char in text)


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "n/a"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(number):
        return "n/a"
    return f"{number:.{digits}f}"


def _pct(value: Any, digits: int = 1) -> str:
    return "n/a" if value is None else _fmt(100.0 * float(value), digits)


def _copy_audit_figures(audit_dirs: dict[str, Path], paths: ReportPaths) -> None:
    for key, directory in audit_dirs.items():
        target = paths.per_run / key / "figures"
        target.mkdir(parents=True, exist_ok=True)
        for source in sorted((directory / "figures").glob("*.pdf")):
            shutil.copy2(source, target / source.name)


def build_tex(
    arms: list[ArmData],
    endpoints: pd.DataFrame,
    gates: pd.DataFrame,
    retrieval: dict[str, dict[str, Any]],
    audit_dirs: dict[str, Path],
    paths: ReportPaths,
    budget: int,
    metric_contract: tuple[float, float, int],
    intentional_agentic_stop: bool,
) -> None:
    contract = _experiment_contract(arms, budget)
    problem_label = str(contract["problem"]).replace("_", " ").title()
    archive_mode = "dynamic" if contract["dynamic_archive"] else "fixed"
    dimensions = int(contract["behavior_dimensions"])
    parents = int(contract["num_parents"])
    parent_label = "parent" if parents == 1 else "parents"
    offer = float(contract["offer_probability"])
    offer_label = f"{100.0 * offer:.0f}/{100.0 * (1.0 - offer):.0f}"
    bank_cap = contract["bank_cap"]
    bank_label = "uncapped bank" if bank_cap is None else f"bank cap {bank_cap}"
    metric_lower, metric_upper, total_cells = metric_contract
    all_passed = bool(gates["passed"].all())
    implementation_ready = not bool(gates["blocks_readiness"].any())
    best = endpoints.sort_values("final_best", ascending=False).iloc[0]
    endpoint_by_key = {str(row.arm): row for row in endpoints.itertuples(index=False)}
    agentic_endpoint = endpoint_by_key["agentic"]
    whole_endpoint = endpoint_by_key["whole_bank"]
    no_memory_endpoint = endpoint_by_key["no_memory"]
    slowest_endpoint = max(
        endpoints.itertuples(index=False), key=lambda row: row.elapsed_minutes
    )
    fastest_minutes = min(float(value) for value in endpoints["elapsed_minutes"])
    runtime_ratio = float(slowest_endpoint.elapsed_minutes) / fastest_minutes
    arm_by_key = {arm.key: arm for arm in arms}
    agentic_audit = arm_by_key["agentic"].audit_metrics
    whole_audit = arm_by_key["whole_bank"].audit_metrics
    agentic_calibration = agentic_audit.get("prequential_calibration", {})
    whole_calibration = whole_audit.get("prequential_calibration", {})
    lineage = _lineage_credit_summary(arms)
    endpoint_rows = "\n".join(
        f"{_tex(ARM_LABELS[row.arm])} & {int(row.evaluated_mutants)} & {_fmt(row.valid_rate, 3)} & {_fmt(row.final_best, 6)} & {int(row.final_best_mutant)} & {int(row.archive_cells)} & {_fmt(row.elapsed_minutes, 1)} \\\\"
        for row in endpoints.itertuples()
    )
    memory_rows = []
    for key in ("agentic", "whole_bank"):
        arm = next(item for item in arms if item.key == key)
        frame = arm.memory_trace
        proposed = frame[frame["proposed"]]
        memory_rows.append(
            f"{_tex(ARM_LABELS[key])} & {arm.bank_cards} & {len(frame)} & {len(proposed)} & {int(proposed['delivered'].sum())} & {int((~proposed['delivered']).sum())} & {int(frame['evidence_count'].max())} \\\\"
        )
    lineage_rows = "\n".join(
        f"{_tex(ARM_LABELS[row.arm])} & {int(row.matured_roots)} & "
        f"{int(row.pending_roots)} & {int(row.censored_roots)} & "
        f"{_pct(row.best_depth_gt_1_fraction)} & "
        f"{_pct(row.positive_descendant_lift_fraction)} & "
        f"{_fmt(row.median_descendant_lift, 4)} & "
        f"{int(row.reused_descendants)} \\\\"
        for row in lineage.itertuples(index=False)
    )
    gate_rows = "\n".join(
        f"{_tex(row.gate)} & "
        f"{'PASS' if row.passed else 'EXPECTED STOP' if row.expected_limitation else 'FAIL'} & "
        f"{_tex(row.evidence)} \\\\"
        for row in gates.itertuples()
    )
    appendix = []
    for key in ("agentic", "whole_bank"):
        appendix.append(
            f"\\section{{{_tex(ARM_LABELS[key])}: full Bayesian audit figures}}"
        )
        for figure in sorted((paths.per_run / key / "figures").glob("*.pdf")):
            caption = AUDIT_FIGURE_CAPTIONS.get(
                figure.stem, figure.stem.replace("_", " ").title()
            )
            rel = figure.relative_to(paths.root).as_posix()
            appendix.append(
                "\\begin{figure}[p]\n"
                "\\centering\n"
                f"\\includegraphics[width=0.98\\textwidth]{{{rel}}}\n"
                f"\\caption{{{_tex(caption)}}}\n"
                "\\end{figure}\n\\clearpage"
            )
    retrieval_text = retrieval["agentic"]
    applicable_source = retrieval_text["source_diagnostics"]["rag_applicable"]
    nonapplicable_source = retrieval_text["source_diagnostics"]["not_rag_applicable"]
    cases = _retrieval_cases(next(arm for arm in arms if arm.key == "agentic"))
    agentic_arm = arm_by_key["agentic"]
    checkpoint_note = (
        "The agentic output contains "
        f"{agentic_arm.log_segments} execution-log segments, "
        f"{agentic_arm.llm_log_segments} with LLM activity, because the run was "
        "checkpoint-resumed after an infrastructure interruption. Program "
        "iterations and causal-ledger ordinals are continuous; LLM accounting "
        "aggregates every segment. Its reported wall-clock span includes the pause."
        if agentic_arm.log_segments > 1
        else "Each arm used one execution-log segment."
    )
    if intentional_agentic_stop:
        pending = int((agentic_arm.memory_trace["terminal_status"] == "pending").sum())
        checkpoint_note += (
            " The agentic process was intentionally stopped at the user's request "
            f"after all {len(agentic_arm.memory_trace)} decisions were committed; "
            f"{pending} terminal outcome remained pending. No synthetic outcome or "
            "post-hoc censoring was inserted."
        )
    case_blocks = []
    for case in cases:
        advice = (
            "\n".join(f"\\item {_tex(value)}" for value in case["applicable_advice"])
            or "\\item No card was labelled applicable."
        )
        terminal_value = (
            "n/a" if case["terminal_value"] is None else _fmt(case["terminal_value"], 4)
        )
        case_blocks.append(
            rf"""
\subsection*{{Decision {case["ordinal"]}}}
Parent fitness {_fmt(case["parent_fitness"], 6)}, quality quantile {_fmt(case["parent_quantile"], 3)}, dynamic coordinates {_tex(case["coordinates"])}. The frozen bank had {case["eligible"]} eligible cards; research labelled {case["applicable"]} as applicable while the full bank remained selectable.

\textbf{{Parent program excerpt.}} {_tex(case["parent_excerpt"])}

\textbf{{LLM-labelled applicable advice excerpts}}
\begin{{itemize}}
{advice}
\end{{itemize}}

\textbf{{Bayesian policy result.}} Source: {_tex(case["source"])}; assignment: {_tex(case["assignment"])}; terminal: {_tex(case["terminal_status"])}; oriented proximal gain (raw fitness units): {terminal_value}. Proposed advice: {_tex(case["proposed_advice"])}
"""
        )
    if all_passed:
        verdict = (
            "All declared mechanical and integrity report gates passed. RAG "
            "applicability is suitable as the default for further replicated "
            "experiments; this single trajectory per arm does not establish "
            "cross-policy causal superiority."
        )
        readiness = "PASS"
    elif implementation_ready and intentional_agentic_stop:
        verdict = (
            "All blocking implementation gates passed. The only failed raw gates "
            "are terminal-closure checks caused by the explicit stop with one "
            "outcome still pending. RAG applicability is suitable as the default "
            "for further replicated experiments, while this arm is correctly "
            "classified as truncated rather than complete."
        )
        readiness = "CONDITIONAL PASS"
    else:
        verdict = (
            "At least one blocking integrity report gate failed. The observed "
            "curves remain diagnostic, but the implementation is not cleared for "
            "the default until each blocking failure is resolved."
        )
        readiness = "FAIL"
    tex = rf"""
\documentclass[a4paper,10pt]{{article}}
\usepackage[margin=0.72in]{{geometry}}
\usepackage{{graphicx,booktabs,array,longtable,xcolor,hyperref,microtype,fancyhdr}}
\definecolor{{ink}}{{HTML}}{{18212B}}
\definecolor{{muted}}{{HTML}}{{667281}}
\definecolor{{blue}}{{HTML}}{{2765A8}}
\definecolor{{green}}{{HTML}}{{3B7D44}}
\definecolor{{red}}{{HTML}}{{B64343}}
\hypersetup{{colorlinks=true,linkcolor=blue,urlcolor=blue}}
\pagestyle{{fancy}}
\fancyhf{{}}
\lhead{{GigaEvo Memory v2}}
\rhead{{{_tex(problem_label)} systems comparison}}
\cfoot{{\thepage}}
\setlength{{\parindent}}{{0pt}}
\setlength{{\parskip}}{{5pt}}
\setlength{{\emergencystretch}}{{2em}}
\newcommand{{\reportgraphic}}[1]{{\par\noindent\includegraphics[width=\textwidth,height=0.78\textheight,keepaspectratio]{{#1}}\par\medskip}}
\begin{{document}}
\begin{{center}}
{{\LARGE\bfseries Memory v2 on {_tex(problem_label)}}}\\[4pt]
{{\large RAG applicability, full-bank Bayesian selection, and no memory}}\\[7pt]
{{\color{{muted}} Single-run descriptive systems comparison; generated {datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")}}}
\end{{center}}

\tableofcontents
\clearpage

\section{{Executive verdict}}
{_tex(verdict)}

The highest observed final fitness was {_fmt(best.final_best, 6)} in the {_tex(ARM_LABELS[str(best.arm)])} arm. This is an observed adaptive-search outcome, not a cross-arm causal estimate: there is one dependent trajectory per arm, no cross-arm p-value is reported, and best-so-far values are selection statistics. Within each memory arm, the randomized delivery gate supports its narrower conditional-offer analysis under the logged proposal policy.

\begin{{quote}}
\textbf{{Readiness:}} {_tex(readiness)}. {_tex(verdict)}
\end{{quote}}

\subsection*{{Observed findings}}
\begin{{itemize}}
\item \textbf{{Search endpoint.}} The observed agentic endpoint was {_fmt(agentic_endpoint.final_best, 6)}, whole-bank memory ended at {_fmt(whole_endpoint.final_best, 6)}, and no memory ended at {_fmt(no_memory_endpoint.final_best, 6)}. Relative to no memory, the observed differences were {_fmt(agentic_endpoint.final_best - no_memory_endpoint.final_best, 6)} and {_fmt(whole_endpoint.final_best - no_memory_endpoint.final_best, 6)}.
\item \textbf{{Reliability.}} Valid-mutant fractions were {_fmt(agentic_endpoint.valid_rate, 3)}, {_fmt(whole_endpoint.valid_rate, 3)}, and {_fmt(no_memory_endpoint.valid_rate, 3)}, respectively. Archive occupancy ended at {agentic_endpoint.archive_cells}, {whole_endpoint.archive_cells}, and {no_memory_endpoint.archive_cells} cells.
\item \textbf{{Runtime and model work.}} Observed spans through each arm's end or explicit stop were {_fmt(agentic_endpoint.elapsed_minutes, 1)}, {_fmt(whole_endpoint.elapsed_minutes, 1)}, and {_fmt(no_memory_endpoint.elapsed_minutes, 1)} minutes. The slowest observed arm was {_tex(ARM_LABELS[str(slowest_endpoint.arm)])} at {_fmt(runtime_ratio, 2)} times the fastest span. This includes evaluator work chosen by mutated programs, not just LLM or retrieval latency. The live Bayesian reward does not penalize evaluator time, so expensive advice can remain attractive when it improves fitness; this report audits, but does not optimize, cost-adjusted utility. The arms made {agentic_endpoint.llm_calls}, {whole_endpoint.llm_calls}, and {no_memory_endpoint.llm_calls} logged LLM calls, consuming {agentic_endpoint.llm_tokens}, {whole_endpoint.llm_tokens}, and {no_memory_endpoint.llm_tokens} tokens. Logged failures were {agentic_endpoint.llm_failures}, {whole_endpoint.llm_failures}, and {no_memory_endpoint.llm_failures}; memory-writer timeouts are fail-soft and remain visible rather than being counted as retrieval success.
\item \textbf{{RAG handoff.}} RAG-labelled cards made up {_pct(applicable_source["slate_slot_share"])} percent of eligible-bank slots and {_pct(applicable_source["proposal_share"])} percent of downstream Bayesian proposals; unlabelled cards made up {_pct(nonapplicable_source["slate_slot_share"])} and {_pct(nonapplicable_source["proposal_share"])} percent. Research recorded {retrieval_text["research_errors"]} errors.
\item \textbf{{Safety calibration.}} Agentic realized invalidity was {_fmt(agentic_calibration.get("realized_invalid_rate"), 3)} versus mean predicted {_fmt(agentic_calibration.get("mean_predicted_invalid"), 3)}; whole-bank values were {_fmt(whole_calibration.get("realized_invalid_rate"), 3)} and {_fmt(whole_calibration.get("mean_predicted_invalid"), 3)}. Material underprediction flags were {_tex(agentic_audit.get("material_safety_risk_underprediction", "n/a"))} and {_tex(whole_audit.get("material_safety_risk_underprediction", "n/a"))}. This diagnoses probability calibration; the configured gate is a confident incremental-harm exclusion rule, not an absolute-risk guarantee.
\item \textbf{{Evidence persistence.}} Support-ready lineages were {agentic_audit.get("support_ready_card_lineages", "n/a")}/{agentic_audit.get("stable_card_lineages_with_offers", "n/a")} for agentic and {whole_audit.get("support_ready_card_lineages", "n/a")}/{whole_audit.get("stable_card_lineages_with_offers", "n/a")} for whole-bank. Median cold-start H50 opportunities from zero evidence were {_fmt(agentic_audit.get("median_cold_start_randomized_h50"), 1)} and {_fmt(whole_audit.get("median_cold_start_randomized_h50"), 1)}; these are throughput diagnostics, not remaining-time forecasts.
\end{{itemize}}

\section{{Experimental contract}}
\reportgraphic{{figures/01_experimental_contract.pdf}}

All arms use the same five initial programs, {_tex(problem_label)} fitness definition and bounds, {_tex(contract["mutation_model"])} mutator, {parents} {parent_label}, {archive_mode} {dimensions}-dimensional MAP-Elites archive, and {contract["budget"]} attempted mutants. The memory arms use run seed {contract["memory_seed"]}. Agentic research uses {_tex(contract["research_model"])}. Agentic and null-applicability arms share the same full-bank candidate universe, card writer, hierarchical Bayesian posterior, safety gate, {offer_label} offer randomization, credit endpoint, and {_tex(bank_label)}. Their intended difference is only whether a pre-treatment RAG applicability label is supplied. The no-memory arm uses the canonical guided pipeline with null reader and writer.

The declared fitness interval [{metric_lower:.6f}, {metric_upper:.6f}] and MAP-Elites cardinality of {total_cells} cells are derived independently from every immutable decision in both memory ledgers; the command-line values are equality assertions, not the source of these quantities.

{_tex(checkpoint_note)}

Both memory arms use the same full-bank candidate source. The null-applicability arm makes no retrieval-LLM call; the agentic arm assesses applicability before the provider lock, while timeout or failure emits an empty neutral label. Neither path changes the candidate universe, posterior fit, randomization, leases, or causal record. The no-memory arm does not instantiate the provider.

\clearpage
\section{{Evolutionary outcomes}}
\begin{{center}}\small
\begin{{tabular}}{{lrrrrrr}}
\toprule
Arm & Mutants & Valid rate & Final best & Best at & Cells & Minutes \\
\midrule
{endpoint_rows}
\bottomrule
\end{{tabular}}
\end{{center}}

\reportgraphic{{figures/02_search_by_budget.pdf}}
\reportgraphic{{figures/03_wall_time_and_throughput.pdf}}
\reportgraphic{{figures/04_reliability_and_archive.pdf}}

\clearpage
\section{{Memory and retrieval mechanics}}
\reportgraphic{{figures/05_memory_candidate_flow.pdf}}
\reportgraphic{{figures/08_agentic_retrieval_dossier.pdf}}

The agentic assessor logged {retrieval_text["research_calls"]} aggregate research episodes, with {retrieval_text["research_errors"]} errors and {retrieval_text["research_empty_calls"]} empty results. Research events are emitted before a causal decision ID exists, so episode counts are aggregate accounting rather than an asserted one-to-one join to committed decisions; program IDs provide the available correlation key. Median and 90th-percentile research latency were {_fmt(retrieval_text["median_research_ms"], 1)} and {_fmt(retrieval_text["p90_research_ms"], 1)} ms; the event intervals show up to {retrieval_text["max_concurrent_research"]} overlapping episodes. Mean queries per research step were {_fmt(retrieval_text["mean_query_count"], 2)}, with {_fmt(retrieval_text["mean_hit_count"], 2)} returned hits. Query-scope usage was {_tex(retrieval_text["query_scopes"])} and reflection decisions were {_tex(retrieval_text["research_decisions"])}. The final policy proposal sources were {_tex(retrieval_text["proposal_sources"])}. Sequential nonempty applicability sets had mean Jaccard overlap {_fmt(retrieval_text["mean_consecutive_applicability_jaccard"], 3)}; this measures label turnover, not semantic relevance. The full eligible bank is always the Bayesian action universe, so no random tail or retriever inclusion propensity is part of the policy.

The parent and its typed evolutionary context are frozen before research begins. This is causally pre-treatment and does not bias the randomized offer contrast, but a slow retrieval call can describe an archive snapshot that is older than the one current when the immutable decision is committed.

Across agentic decisions, RAG-labelled cards supplied {_pct(applicable_source["slate_slot_share"])} percent of eligible-bank slots and {_pct(applicable_source["proposal_share"])} percent of policy proposals; unlabelled cards supplied {_pct(nonapplicable_source["slate_slot_share"])} and {_pct(nonapplicable_source["proposal_share"])} percent. Among closed delivered proposals, observed invalidity was {_fmt(applicable_source["delivered_invalid_rate"], 3)} for labelled cards and {_fmt(nonapplicable_source["delivered_invalid_rate"], 3)} for unlabelled cards; mean valid proximal gain was {_fmt(applicable_source["mean_valid_delivered_gain"], 4)} and {_fmt(nonapplicable_source["mean_valid_delivered_gain"], 4)}, respectively. These are adaptive descriptive outcomes, not randomized label effects, because labels and posterior proposals are adaptive.

Across the observed agentic trajectory, {retrieval_text["unique_eligible_cards"]} distinct cards entered at least one eligible-bank snapshot, {retrieval_text["unique_applicable_cards"]} were labelled applicable at least once, and all {retrieval_text["unique_surfaced_cards"]} eligible cards entered the posterior action universe. This union-level coverage is descriptive because the bank grows and merges during the run.

\begin{{center}}\small
\begin{{tabular}}{{lrrrrrr}}
\toprule
Arm & Final cards & Decisions & Proposals & Delivered & Control & Evidence \\
\midrule
{" ".join(memory_rows)}
\bottomrule
\end{{tabular}}
\end{{center}}

\clearpage
\section{{Retrieval trace case studies}}
These evenly spaced ledger cases expose the full handoff: dynamic parent context to RAG applicability labels, full-bank Bayesian proposal, randomized delivery, and terminal measurement. Advice excerpts are immutable decision-time card payloads, not post-hoc summaries. Their face relevance is inspectable; the outcome comparison remains adaptive and non-causal across label groups.

{"".join(case_blocks)}

\clearpage
\section{{Randomization and fitted posteriors}}
The plotted effects are normalized proximal usable-utility effects at each run's final representative context. Hierarchical pooling lets cold cards borrow global and contextual information while retaining card-specific uncertainty. Safety is an exploratory confident-harm exclusion rule, not a calibrated 90 percent guarantee. The full appendices show posterior distributions, contextual surfaces, safety probabilities, lineage shadow credit, conditional-offer OPE, calibration, dynamic MAP-Elites context, numerical diagnostics, and evidence persistence separately for both memory arms.

\reportgraphic{{figures/06_randomization_calibration.pdf}}
\reportgraphic{{figures/07_final_card_posteriors.pdf}}

\subsection{{Descendant-credit audit}}
\begin{{center}}\small
\resizebox{{\textwidth}}{{!}}{{%
\begin{{tabular}}{{lrrrrrrr}}
\toprule
Arm & Mature & Pending & Censored & Best D$>1$ (\%) & Positive lift (\%) & Median lift & Reused \\
\midrule
{lineage_rows}
\bottomrule
\end{{tabular}}}}
\end{{center}}

The depth-3, 32-opportunity endpoint is an offline shadow analysis. ``Best D$>1$'' measures how often a valid matured root's best credited descendant was deeper than its immediate child. Positive lift compares the long-horizon endpoint with proximal gain where both are valid. Reused descendants expose dependence between root windows; therefore these fitted shadow posteriors are descriptive and are never promoted to online action selection in this version.

\clearpage
\section{{Resource accounting}}
\reportgraphic{{figures/09_llm_resources.pdf}}

Resource differences include real concurrent provider load and cannot be interpreted as causal latency overhead. Retrieval calls occur only in the agentic arm. Writer/consolidation calls occur in both memory arms. No-memory has no memory-LLM calls by construction.

\clearpage
\section{{Integrity gates}}
\reportgraphic{{figures/10_integrity_gates.pdf}}
\clearpage
\begin{{longtable}}{{>{{\raggedright\arraybackslash}}p{{0.40\textwidth}}l>{{\raggedright\arraybackslash}}p{{0.29\textwidth}}}}
\toprule
Gate & Result & Evidence \\
\midrule
{gate_rows}
\bottomrule
\end{{longtable}}

\clearpage
\section{{What this experiment can and cannot establish}}
It can establish whether the software recorded coherent candidate universes, probabilities, assignments, outcomes, posteriors, and resource use; whether the agent actually retrieved cards; and what search trajectories occurred. It cannot establish that one memory policy is generally superior from one seed. Mutants within a trajectory are adaptively dependent and are not {contract["budget"]} independent replicates. A policy-level efficacy claim requires multiple independent seed-matched trajectories. A clean RAG-applicability ablation would additionally freeze one bank and disable writing in both memory arms.

\appendix
{"".join(appendix)}
\end{{document}}
"""
    paths.tex.write_text(tex, encoding="utf-8")


def compile_tex(paths: ReportPaths) -> None:
    executable = shutil.which("tectonic")
    if executable is None:
        candidates = (
            PROJECT_ROOT.parent / ".local" / "bin" / "tectonic",
            Path(
                "/mnt/virtual_ai0001071-04017_SR004-nfs1/CFS-SR008/workspace/mathemage/.local/bin/tectonic"
            ),
        )
        executable = next((str(path) for path in candidates if path.is_file()), None)
    if executable is None:
        raise FileNotFoundError("tectonic is required")
    result = subprocess.run(
        [executable, "--keep-logs", "--outdir", str(paths.root), paths.tex.name],
        cwd=paths.root,
        text=True,
        capture_output=True,
        check=False,
        timeout=900,
    )
    (paths.root / "tectonic.stdout.log").write_text(result.stdout, encoding="utf-8")
    (paths.root / "tectonic.stderr.log").write_text(result.stderr, encoding="utf-8")
    if result.returncode != 0 or not paths.pdf.is_file():
        raise RuntimeError(result.stderr[-4000:])


def send_telegram(paths: ReportPaths, audit_dirs: dict[str, Path]) -> None:
    from dotenv import load_dotenv

    common = subprocess.run(
        ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if common.returncode == 0:
        env_file = Path(common.stdout.strip()).resolve().parent / ".env"
        if env_file.is_file():
            load_dotenv(env_file, override=False)
    from tools.telegram_notify import notify, send_document, send_photo

    def deliver(send: Any, *args: Any, **kwargs: Any) -> None:
        for delay in (0.0, 2.0, 5.0, 10.0):
            if delay:
                time.sleep(delay)
            if send(*args, **kwargs):
                time.sleep(1.05)
                return
        raise RuntimeError(f"Telegram delivery failed for {args[0]!r}")

    deliver(
        notify,
        "Heilbronn memory-v2 three-arm audit completed. Sending every comparison and per-run figure, followed by the compiled reports.",
        parse_mode=None,
    )
    for path in sorted(paths.figures.glob("*.png")):
        deliver(
            send_photo,
            str(path),
            caption=path.stem.replace("_", " ").title(),
            parse_mode=None,
        )
    for key, directory in audit_dirs.items():
        for path in sorted(directory.parent.glob("*.png")):
            deliver(
                send_photo,
                str(path),
                caption=f"{ARM_LABELS[key]}: {path.stem.replace('_', ' ').title()}",
                parse_mode=None,
            )
        for path in sorted((directory / "figures").glob("*.png")):
            deliver(
                send_photo,
                str(path),
                caption=f"{ARM_LABELS[key]}: {path.stem.replace('_', ' ').title()}",
                parse_mode=None,
            )
    deliver(
        send_document,
        str(paths.pdf),
        caption="Heilbronn three-arm memory-v2 comparison (TeX/PDF)",
        parse_mode=None,
    )
    for key, directory in audit_dirs.items():
        pdf = directory / "memory_v2_bayesian_audit.pdf"
        if pdf.is_file():
            deliver(
                send_document,
                str(pdf),
                caption=f"{ARM_LABELS[key]} full Bayesian audit",
                parse_mode=None,
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agentic-run", type=Path, required=True)
    parser.add_argument("--whole-bank-run", type=Path, required=True)
    parser.add_argument("--no-memory-run", type=Path, required=True)
    parser.add_argument("--agentic-audit", type=Path, required=True)
    parser.add_argument("--whole-bank-audit", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--budget", type=int, default=250)
    parser.add_argument("--metric-lower", type=float, default=0.0)
    parser.add_argument("--metric-upper", type=float, default=0.0365)
    parser.add_argument("--total-cells", type=int, default=150)
    parser.add_argument("--agentic-intentionally-stopped", action="store_true")
    parser.add_argument("--send-telegram", action="store_true")
    args = parser.parse_args()

    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    paths = ReportPaths(
        root=output,
        figures=output / "figures",
        tables=output / "tables",
        per_run=output / "per_run",
        tex=output / "memory_v2_heilbron_comparison.tex",
        pdf=output / "memory_v2_heilbron_comparison.pdf",
    )
    paths.tables.mkdir(parents=True, exist_ok=True)
    audit_dirs = {
        "agentic": args.agentic_audit.resolve(),
        "whole_bank": args.whole_bank_audit.resolve(),
    }
    arms = [
        load_arm(
            "agentic",
            args.agentic_run,
            audit_dirs["agentic"],
            allow_pending_programs=args.agentic_intentionally_stopped,
        ),
        load_arm("whole_bank", args.whole_bank_run, audit_dirs["whole_bank"]),
        load_arm("no_memory", args.no_memory_run, None),
    ]
    metric_lower, metric_upper, total_cells = _ledger_metric_contract(
        arms,
        asserted_lower=args.metric_lower,
        asserted_upper=args.metric_upper,
        asserted_total_cells=args.total_cells,
    )
    endpoints = _endpoint_summary(arms, metric_upper)
    lineage = _lineage_credit_summary(arms)
    retrieval = {
        key: _retrieval_summary(arm)
        for key, arm in ((arm.key, arm) for arm in arms if not arm.memory_trace.empty)
    }
    gates = _gates(arms, args.budget, metric_lower, metric_upper)
    gates, intentional_agentic_stop = _annotate_intentional_agentic_stop(
        gates,
        arms[0],
        budget=args.budget,
        enabled=args.agentic_intentionally_stopped,
    )

    traces = []
    archives = []
    llm_calls = []
    memories = []
    for arm in arms:
        trace = arm.trace.copy()
        trace["arm"] = arm.key
        traces.append(trace)
        archive = arm.archive.copy()
        archive["arm"] = arm.key
        archives.append(archive)
        if not arm.llm_calls.empty:
            llm_calls.append(arm.llm_calls)
        if not arm.memory_trace.empty:
            memories.append(arm.memory_trace)
    pd.concat(traces, ignore_index=True).to_csv(
        paths.tables / "run_trace.csv", index=False
    )
    pd.concat(archives, ignore_index=True).to_csv(
        paths.tables / "archive_trace.csv", index=False
    )
    pd.concat(llm_calls, ignore_index=True).to_csv(
        paths.tables / "llm_calls.csv", index=False
    )
    pd.concat(memories, ignore_index=True).to_csv(
        paths.tables / "memory_trace.csv", index=False
    )
    endpoints.to_csv(paths.tables / "endpoint_summary.csv", index=False)
    lineage.to_csv(paths.tables / "lineage_credit_summary.csv", index=False)
    gates.to_csv(paths.tables / "integrity_gates.csv", index=False)
    (paths.tables / "retrieval_summary.json").write_text(
        json.dumps(retrieval, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scope": "single-run descriptive systems comparison",
        "runs": {arm.key: str(arm.root) for arm in arms},
        "execution_logs": {
            arm.key: {
                "segments": arm.log_segments,
                "segments_with_llm_activity": arm.llm_log_segments,
            }
            for arm in arms
        },
        "audit_dirs": {key: str(value) for key, value in audit_dirs.items()},
        "budget": args.budget,
        "metric_bounds": [metric_lower, metric_upper],
        "total_map_elites_cells": total_cells,
        "metric_archive_contract_source": "both immutable memory ledgers",
        "cli_metric_archive_assertions": [
            args.metric_lower,
            args.metric_upper,
            args.total_cells,
        ],
        "all_gates_passed": bool(gates["passed"].all()),
        "implementation_readiness_passed": not bool(gates["blocks_readiness"].any()),
        "agentic_intentionally_stopped": intentional_agentic_stop,
    }
    (paths.root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    _configure_matplotlib()
    render_contract(arms, paths, args.budget)
    render_search(arms, paths, metric_upper)
    render_wall_time(arms, paths)
    render_reliability(arms, paths, total_cells)
    render_memory(arms, paths)
    render_randomization(arms, paths)
    render_agentic_retrieval(arms[0], paths)
    render_posteriors(audit_dirs, paths)
    render_resources(arms, paths)
    render_gates(gates, paths)
    _copy_audit_figures(audit_dirs, paths)
    build_tex(
        arms,
        endpoints,
        gates,
        retrieval,
        audit_dirs,
        paths,
        args.budget,
        (metric_lower, metric_upper, total_cells),
        intentional_agentic_stop,
    )
    compile_tex(paths)
    if args.send_telegram:
        send_telegram(paths, audit_dirs)
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["implementation_readiness_passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
