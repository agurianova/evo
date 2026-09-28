"""Reduce one finished Memory V2 run to report-sized causal audit data.

The SQLite ledger is authoritative for assignments and outcomes.  The JSON card
bank is used only for card text/provenance, and the event stream supplies writer
snapshots.  Terminal measurements are already stored on the task's native R2
scale; the posterior performs its own normalization while fitting.

Usage: python build_memory_analysis.py <run_dir> <arm-slug>
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
from pathlib import Path
import re
import sqlite3
import statistics
import sys
from typing import Any

HERE = Path(__file__).parent
VIZ = HERE / "viz"


def _mean(values: list[float]) -> float | None:
    return statistics.fmean(values) if values else None


def _load_programs(run_dir: Path) -> dict[str, dict[str, Any]]:
    root = run_dir / "storage" / "dag_tab" / "programs"
    return {
        row["id"]: row
        for path in root.glob("*.json")
        if (row := json.loads(path.read_text()))
    }


def _event_payloads(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(errors="replace") as handle:
        for line in handle:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _log_retirement(run_dir: Path) -> dict[str, Any]:
    pattern = re.compile(
        r"\[MemoryV2\]\[Retirement\] disabled.*boundary mass "
        r"(?P<mass>[0-9.eE+-]+) exceeds alpha=(?P<alpha>[0-9.eE+-]+)"
    )
    values: list[tuple[float, float]] = []
    for path in sorted(run_dir.glob("evolution_*.log")):
        for line in path.read_text(errors="replace").splitlines():
            if match := pattern.search(line):
                values.append((float(match.group("mass")), float(match.group("alpha"))))
    return {
        "disabled_sweeps": len(values),
        "last_boundary_mass": values[-1][0] if values else None,
        "max_boundary_mass": max((row[0] for row in values), default=None),
        "alpha": values[-1][1] if values else None,
    }


def _program_card_ids(program: dict[str, Any]) -> list[str]:
    mutation = program.get("metadata", {}).get("mutation_output", {})
    return list(mutation.get("card_ids_used") or [])


def _native_gain(
    terminal: dict[str, Any], decision: dict[str, Any]
) -> tuple[float | None, float | None]:
    del decision
    measurement = terminal.get("measurement") or {}
    if measurement.get("value") is None:
        return None, None
    value = float(measurement["value"])
    se = measurement.get("se")
    return value, None if se is None else float(se)


def _group_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid = [row for row in rows if row["gain"] is not None]
    invalid = [row for row in rows if row["terminal_status"] == "invalid"]
    return {
        "n": len(rows),
        "valid_n": len(valid),
        "invalid_n": len(invalid),
        "invalid_rate": len(invalid) / len(rows) if rows else None,
        "mean_gain": _mean([row["gain"] for row in valid]),
        "median_gain": statistics.median([row["gain"] for row in valid])
        if valid
        else None,
        "positive_share": _mean([float(row["gain"] > 0.0) for row in valid]),
    }


def main() -> None:
    run_dir, arm = Path(sys.argv[1]), sys.argv[2]
    VIZ.mkdir(exist_ok=True)
    programs = _load_programs(run_dir)

    database = run_dir / "memory" / "memory_v2_selection_evidence.sqlite3"
    connection = sqlite3.connect(database)
    decisions = {
        decision_id: json.loads(payload)
        for decision_id, payload in connection.execute(
            "SELECT decision_id, record_json FROM decisions"
        )
    }
    terminals = {
        decision_id: json.loads(payload)
        for decision_id, payload in connection.execute(
            "SELECT decision_id, terminal_json FROM terminals"
        )
    }
    child_by_decision = {
        decision_id: child_id
        for decision_id, child_id in connection.execute(
            "SELECT decision_id, child_id FROM decision_children"
        )
    }
    edge_statuses = Counter(
        status for (status,) in connection.execute("SELECT status FROM mutation_edges")
    )
    connection.close()

    outcomes: list[dict[str, Any]] = []
    cell_alignment_errors = 0
    dynamic_coordinate_errors = 0
    semantic_by_parent_axis: dict[tuple[str, str], list[float]] = defaultdict(list)
    cells_by_parent: dict[
        str, list[tuple[int, tuple[int, ...], list[dict[str, Any]]]]
    ] = defaultdict(list)
    semantic_schema_hashes: set[str] = set()
    behavior_schema_hashes: set[str] = set()
    parent_cell_unoccupied = 0

    for decision_id, decision in sorted(
        decisions.items(), key=lambda item: item[1]["event_ordinal"]
    ):
        context = decision["context"]
        map_context = context["map_elites"]
        coordinates = map_context["coordinates"]
        cell = tuple(map_context["parent_cell"])
        if tuple(row["cell_index"] for row in coordinates) != cell:
            cell_alignment_errors += 1
        for coordinate in coordinates:
            raw = float(coordinate["raw_value"])
            lower = float(coordinate["dynamic_lower_bound"])
            upper = float(coordinate["dynamic_upper_bound"])
            dynamic = float(coordinate["dynamic_normalized"])
            if not (
                lower - 1e-12 <= raw <= upper + 1e-12
                and -1e-12 <= dynamic <= 1.0 + 1e-12
            ):
                dynamic_coordinate_errors += 1
            semantic_by_parent_axis[(context["parent_id"], coordinate["key"])].append(
                float(coordinate["semantic_normalized"])
            )
        semantic_schema_hashes.add(map_context["semantic_schema_hash"])
        behavior_schema_hashes.add(map_context["behavior_schema_hash"])
        parent_cell_unoccupied += int(not map_context["parent_cell_occupied"])
        cells_by_parent[context["parent_id"]].append(
            (decision["event_ordinal"], cell, coordinates)
        )

        terminal = terminals.get(decision_id)
        proposed = decision.get("proposed_treatment_id")
        delivered = bool(decision.get("delivered"))
        used_card_ids = list((terminal or {}).get("used_card_ids") or [])
        gain, gain_se = (
            (None, None) if terminal is None else _native_gain(terminal, decision)
        )
        if proposed is None:
            assignment = "empty"
        elif not delivered:
            assignment = "withheld_control"
        elif used_card_ids:
            assignment = "explicit_use"
        else:
            assignment = "delivered_ignored"
        outcomes.append(
            {
                "decision_id": decision_id,
                "event_ordinal": decision["event_ordinal"],
                "parent_id": context["parent_id"],
                "parent_fitness": context["parent_metrics"]["fitness"],
                "parent_iteration": context["parent_iteration"],
                "parent_generation": context["parent_generation"],
                "parent_cell": list(cell),
                "proposed_treatment_id": proposed,
                "delivered": delivered,
                "assignment": assignment,
                "used_card_ids": used_card_ids,
                "child_id": (terminal or {}).get("child_id")
                or child_by_decision.get(decision_id),
                "terminal_status": None if terminal is None else terminal["status"],
                "ope_eligible": None if terminal is None else terminal["ope_eligible"],
                "gain": gain,
                "gain_se": gain_se,
                "completion_ordinal": None
                if terminal is None
                else terminal.get("completion_ordinal"),
            }
        )

    repeated = {
        parent: rows for parent, rows in cells_by_parent.items() if len(rows) > 1
    }
    changed = {
        parent: rows
        for parent, rows in repeated.items()
        if len({row[1] for row in rows}) > 1
    }
    example_parent = max(
        changed,
        key=lambda parent: (
            len({row[1] for row in changed[parent]}),
            len(changed[parent]),
        ),
        default=None,
    )
    example = []
    if example_parent is not None:
        for ordinal, cell, coordinates in changed[example_parent]:
            example.append(
                {
                    "event_ordinal": ordinal,
                    "cell": list(cell),
                    "bounds": {
                        row["key"]: [
                            row["dynamic_lower_bound"],
                            row["dynamic_upper_bound"],
                        ]
                        for row in coordinates
                    },
                }
            )
    semantic_max_spread = max(
        (max(values) - min(values) for values in semantic_by_parent_axis.values()),
        default=0.0,
    )

    events = _event_payloads(run_dir / "memory" / "memory_events.jsonl")
    writer_syncs = [
        {
            "timestamp_utc": row["timestamp_utc"],
            "evidence_count": row["evidence_count"],
            "pending_count": row["pending_count"],
            "bank_size": row["bank_size"],
            "released_child_count": row["released_child_count"],
            "retired_count": len(row.get("retired_card_ids") or []),
        }
        for row in events
        if row.get("event") == "MEMORY_V2_WRITER_SYNC"
    ]
    store_writes = [row for row in events if row.get("event") == "MEMORY_STORE_WRITE"]

    card_payload = json.loads((run_dir / "memory" / "cards.json").read_text())["cards"]
    card_rows: list[dict[str, Any]] = []
    per_card: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in outcomes:
        if row["proposed_treatment_id"]:
            per_card[row["proposed_treatment_id"]].append(row)
    explicit_by_card: Counter[str] = Counter(
        card_id for row in outcomes for card_id in row["used_card_ids"]
    )
    for card_id, card in card_payload.items():
        rows = per_card.get(card_id, [])
        valid = [row for row in rows if row["gain"] is not None]
        treated = [row for row in valid if row["delivered"]]
        controls = [row for row in valid if not row["delivered"]]
        explicit = [row for row in valid if card_id in row["used_card_ids"]]
        card_rows.append(
            {
                "id": card_id,
                "kind": card["kind"],
                "description": card["description"],
                "programs": len(card.get("programs") or []),
                "gain_events": len(card.get("gain_events") or []),
                "proposals": len(rows),
                "delivered": sum(row["delivered"] for row in rows),
                "controls": sum(not row["delivered"] for row in rows),
                "explicit_uses": explicit_by_card[card_id],
                "valid_outcomes": len(valid),
                "invalid_outcomes": sum(
                    row["terminal_status"] == "invalid" for row in rows
                ),
                "mean_delivered_gain": _mean([row["gain"] for row in treated]),
                "mean_control_gain": _mean([row["gain"] for row in controls]),
                "mean_explicit_gain": _mean([row["gain"] for row in explicit]),
                "best_explicit_gain": max(
                    (row["gain"] for row in explicit), default=None
                ),
            }
        )
    card_rows.sort(
        key=lambda row: (-row["explicit_uses"], -row["proposals"], row["id"])
    )

    randomized = [
        row
        for row in outcomes
        if row["proposed_treatment_id"] is not None
        and row["terminal_status"] is not None
    ]
    assignment_groups = {
        key: _group_summary(
            [
                row
                for row in outcomes
                if row["assignment"] == key and row["terminal_status"] is not None
            ]
        )
        for key in ("withheld_control", "delivered_ignored", "explicit_use", "empty")
    }
    causal_slices: dict[str, Any] = {}
    for name, predicate in (
        ("all", lambda _: True),
        ("parent_below_0_865", lambda row: row["parent_fitness"] < 0.865),
        ("parent_at_least_0_875", lambda row: row["parent_fitness"] >= 0.875),
    ):
        selected = [row for row in randomized if predicate(row)]
        causal_slices[name] = {
            "delivered": _group_summary([row for row in selected if row["delivered"]]),
            "withheld_control": _group_summary(
                [row for row in selected if not row["delivered"]]
            ),
        }

    valid_programs = [
        row for row in programs.values() if row["metrics"].get("is_valid") == 1.0
    ]
    champion = max(valid_programs, key=lambda row: row["metrics"]["fitness"])
    explicit_programs = [row for row in valid_programs if _program_card_ids(row)]
    best_explicit = max(explicit_programs, key=lambda row: row["metrics"]["fitness"])

    lineage: list[dict[str, Any]] = []
    cursor = champion
    while True:
        lineage.append(
            {
                "id": cursor["id"],
                "generation": cursor["lineage"].get("generation"),
                "fitness": cursor["metrics"].get("fitness"),
                "cv_score_std": cursor["metrics"].get("cv_score_std"),
                "nodes": cursor["metrics"].get("graph_node_count"),
                "depth": cursor["metrics"].get("graph_max_depth"),
                "features": cursor["metrics"].get("generated_feature_count"),
                "card_ids_used": _program_card_ids(cursor),
                "cards_delivered": list(
                    cursor.get("metadata", {}).get("memory_injected_idea_ids") or []
                ),
            }
        )
        parents = cursor["lineage"].get("parents") or []
        if not parents or parents[0] not in programs:
            break
        cursor = programs[parents[0]]
    lineage.reverse()

    graph = json.loads(champion["code"])
    nodes = [
        {
            "id": node["id"],
            "kind": node["kind"],
            "dependencies": node["dependencies"],
            "input_cols": node["input_cols"],
            "output_cols": node["output_cols"],
            "is_output": node["is_output"],
            "rationale": node["rationale"],
        }
        for node in graph["nodes"]
    ]

    llm_stats = json.loads((VIZ / f"{arm}_stats.json").read_text())["llm_calls"]
    llm_by_model: dict[str, dict[str, Any]] = {}
    for model, rows in (
        (model, [row for row in llm_stats if row["model"] == model])
        for model in sorted({row["model"] for row in llm_stats})
    ):
        ok = [row for row in rows if row["ok"]]
        llm_by_model[model] = {
            "calls": len(rows),
            "failed": len(rows) - len(ok),
            "tokens_in": sum((row["tokens_in"] or 0) for row in ok),
            "tokens_out": sum((row["tokens_out"] or 0) for row in ok),
        }

    founding_gain_events = [
        event
        for card in card_payload.values()
        for event in card.get("gain_events") or []
        if event.get("founding")
    ]
    terminal_ses = [
        row["gain_se"]
        for row in outcomes
        if row["gain"] is not None and row["gain_se"] is not None
    ]
    online_decisions = sorted(decisions.values(), key=lambda row: row["event_ordinal"])
    final_online = online_decisions[-1]["fit_diagnostics"]

    report = {
        "arm": arm,
        "run_dir": str(run_dir),
        "counts": {
            "programs_stored": len(programs),
            "programs_completed": sum(
                "is_valid" in row["metrics"] for row in programs.values()
            ),
            "programs_valid": len(valid_programs),
            "programs_invalid": sum(
                row["metrics"].get("is_valid") == 0.0 for row in programs.values()
            ),
            "programs_incomplete": sum(
                "is_valid" not in row["metrics"] for row in programs.values()
            ),
            "decisions": len(decisions),
            "terminals": len(terminals),
            "mutation_edges": sum(edge_statuses.values()),
            "mutation_edge_statuses": dict(edge_statuses),
            "randomized_proposals": sum(
                row["proposed_treatment_id"] is not None for row in outcomes
            ),
            "delivered": sum(
                row["proposed_treatment_id"] is not None and row["delivered"]
                for row in outcomes
            ),
            "withheld_controls": sum(
                row["proposed_treatment_id"] is not None and not row["delivered"]
                for row in outcomes
            ),
            "empty_decisions": sum(
                row["proposed_treatment_id"] is None for row in outcomes
            ),
            "explicit_uses": sum(bool(row["used_card_ids"]) for row in outcomes),
        },
        "cards": {
            "count": len(card_payload),
            "kinds": dict(Counter(card["kind"] for card in card_payload.values())),
            "adds": sum(row.get("op") == "save" for row in store_writes),
            "updates": sum(row.get("op") == "update" for row in store_writes),
            "retired": sum(row["retired_count"] for row in writer_syncs),
            "rows": card_rows,
        },
        "assignment_groups": assignment_groups,
        "causal_slices": causal_slices,
        "outcomes": outcomes,
        "writer_syncs": writer_syncs,
        "retirement": _log_retirement(run_dir),
        "dynamic_map_audit": {
            "semantic_schema_hashes": len(semantic_schema_hashes),
            "behavior_schema_hashes": len(behavior_schema_hashes),
            "cell_alignment_errors": cell_alignment_errors,
            "dynamic_coordinate_errors": dynamic_coordinate_errors,
            "parent_cell_unoccupied": parent_cell_unoccupied,
            "repeated_parents": len(repeated),
            "parents_that_changed_cell": len(changed),
            "semantic_max_spread_for_same_parent": semantic_max_spread,
            "example_parent_id": example_parent,
            "example_cell_history": example,
            "posterior_uses": "fixed semantic_normalized coordinates; live cell indices are audit/locality state only",
        },
        "uncertainty": {
            "valid_terminal_measurements": len(terminal_ses),
            "nonzero_terminal_se": sum(value > 0.0 for value in terminal_ses),
            "min_terminal_se": min(terminal_ses, default=None),
            "max_terminal_se": max(terminal_ses, default=None),
            "founding_gain_events": len(founding_gain_events),
            "founding_gain_se_zero": sum(
                event.get("gain_se") == 0.0 for event in founding_gain_events
            ),
        },
        "posterior": {
            "last_online_evidence_count": final_online["evidence_count"],
            "last_online_offered_observations": final_online["offered_observations"],
            "last_online_used_observations": final_online["used_observations"],
            "last_online_ignored_observations": final_online["ignored_observations"],
            "last_online_reward_residual_sd": final_online["reward_residual_sd"],
            "last_online_reward_residual_boundary_probability": final_online[
                "reward_residual_boundary_probability"
            ],
            "final_writer_evidence_count": writer_syncs[-1]["evidence_count"],
            "final_writer_pending_count": writer_syncs[-1]["pending_count"],
        },
        "champion": {
            "id": champion["id"],
            "fitness": champion["metrics"]["fitness"],
            "cv_score_std": champion["metrics"]["cv_score_std"],
            "generation": champion["lineage"]["generation"],
            "nodes": champion["metrics"]["graph_node_count"],
            "depth": champion["metrics"]["graph_max_depth"],
            "features": champion["metrics"]["generated_feature_count"],
            "card_ids_used": _program_card_ids(champion),
            "cards_delivered": list(
                champion.get("metadata", {}).get("memory_injected_idea_ids") or []
            ),
            "nodes_detail": nodes,
        },
        "best_explicit_memory": {
            "id": best_explicit["id"],
            "fitness": best_explicit["metrics"]["fitness"],
            "cv_score_std": best_explicit["metrics"]["cv_score_std"],
            "generation": best_explicit["lineage"]["generation"],
            "card_ids_used": _program_card_ids(best_explicit),
        },
        "lineage": lineage,
        "llm_by_model": llm_by_model,
    }

    # The terminal utility is required to agree with the persisted fitness delta.
    mismatches = []
    for row in outcomes:
        if (
            row["gain"] is None
            or row["child_id"] not in programs
            or row["parent_id"] not in programs
        ):
            continue
        observed = (
            programs[row["child_id"]]["metrics"]["fitness"]
            - programs[row["parent_id"]]["metrics"]["fitness"]
        )
        if not math.isclose(row["gain"], observed, rel_tol=0.0, abs_tol=1e-12):
            mismatches.append(row["decision_id"])
    report["uncertainty"]["fitness_delta_mismatches"] = len(mismatches)

    path = VIZ / f"{arm}_memory.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True))
    print(
        f"{path.name}: {len(decisions)} decisions, {len(terminals)} terminals, "
        f"{len(card_payload)} cards, {report['counts']['explicit_uses']} explicit uses"
    )


if __name__ == "__main__":
    main()
