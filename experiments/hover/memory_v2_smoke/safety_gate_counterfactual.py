#!/usr/bin/env python3
"""Fixed-history comparison of memory-v2 safety admission gates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import sys
from typing import Any

import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.special import logit  # noqa: E402
import yaml  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gigaevo.memory_v2.calibration import (  # noqa: E402
    _prepare_units,
    load_calibration_trajectory,
)
from gigaevo.memory_v2.models import canonical_digest  # noqa: E402
from gigaevo.memory_v2.policy import safety_gate_admits  # noqa: E402
from gigaevo.memory_v2.posterior import (  # noqa: E402
    StableBayesianLogisticRegressor,
    TerminalUtilityPosteriorConfig,
    _deterministic_safety_gate,
)

HISTORICAL_MODE = "credible_joint_safe"
COUNTERFACTUAL_MODE = "exclude_confident_incremental_harm"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _create_historical_projection(source: Path, destination: Path) -> dict[str, Any]:
    """Annotate old policy rows in a non-writable analysis copy."""

    source_hash = _sha256(source)
    shutil.copy2(source, destination)
    annotated = 0
    with sqlite3.connect(destination) as connection:
        rows = connection.execute(
            "SELECT decision_id, record_json, record_hash FROM decisions"
        ).fetchall()
        for decision_id, record_json, record_hash in rows:
            payload = json.loads(record_json)
            if canonical_digest(payload) != record_hash:
                raise ValueError(f"source record hash mismatch: {decision_id}")
            policy = payload["policy"]
            if "safety_gate_mode" in policy:
                continue
            policy["safety_gate_mode"] = HISTORICAL_MODE
            encoded = json.dumps(
                payload,
                ensure_ascii=True,
                separators=(",", ":"),
                sort_keys=True,
            )
            connection.execute(
                "UPDATE decisions SET record_json = ?, record_hash = ? "
                "WHERE decision_id = ?",
                (encoded, canonical_digest(payload), decision_id),
            )
            annotated += 1
        connection.execute(
            "INSERT OR REPLACE INTO ledger_metadata(key, value) VALUES (?, ?)",
            (
                "analysis_projection",
                "historical safety_gate_mode annotation; not a writable ledger",
            ),
        )
        connection.commit()
    if _sha256(source) != source_hash:
        raise RuntimeError("source ledger changed while creating analysis projection")
    return {
        "source_sha256": source_hash,
        "projection_sha256": _sha256(destination),
        "annotated_decisions": annotated,
    }


def _find_run_config(ledger: Path) -> Path:
    for directory in ledger.parents:
        candidate = directory / ".hydra" / "config.yaml"
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("no adjacent .hydra/config.yaml found")


def _posterior_config(config_path: Path) -> TerminalUtilityPosteriorConfig:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    configured = raw["memory"]["posterior_config"]
    values = {
        key: value
        for key, value in configured.items()
        if key in TerminalUtilityPosteriorConfig.model_fields
    }
    feature_config = raw["memory"]["feature_config"]
    if float(feature_config["progress_log_scale"]) != 100.0:
        raise ValueError(
            "this replay requires the default progress_log_scale used by the run"
        )
    return TerminalUtilityPosteriorConfig.model_validate(values)


def _stored_actions(projection: Path) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    with sqlite3.connect(f"file:{projection}?mode=ro", uri=True) as connection:
        rows = connection.execute(
            "SELECT record_json FROM decisions ORDER BY event_ordinal, decision_id"
        ).fetchall()
    for (record_json,) in rows:
        payload = json.loads(record_json)
        for action in payload["action_probabilities"]:
            result[(payload["decision_id"], action["treatment_id"])] = {
                "stored_admitted": bool(action["safe"]),
                "stored_probability_acceptable": float(
                    action["prediction"]["probability_safe"]
                ),
            }
    return result


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise ValueError(f"no rows for {path.name}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=tuple(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _trailing_lockout(rows: list[dict[str, Any]], key: str) -> int:
    count = 0
    for row in reversed(rows):
        if row[key]:
            break
        count += 1
    return count


def _plot(
    decision_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    output: Path,
) -> None:
    event = np.asarray([row["event_ordinal"] for row in decision_rows])
    old_count = np.asarray([row["historical_admitted"] for row in decision_rows])
    new_count = np.asarray([row["counterfactual_admitted"] for row in decision_rows])
    old_any = old_count > 0
    new_any = new_count > 0
    window = min(20, len(decision_rows))
    kernel = np.ones(window) / window
    old_rolling = np.convolve(old_any.astype(float), kernel, mode="valid")
    new_rolling = np.convolve(new_any.astype(float), kernel, mode="valid")
    rolling_event = event[window - 1 :]
    q_new = np.asarray(
        [row["counterfactual_probability_acceptable"] for row in candidate_rows]
    )
    margin = q_new - 0.10

    figure, axes = plt.subplots(2, 2, figsize=(12, 8), constrained_layout=True)
    axes[0, 0].plot(event, old_count, color="#B64343", label="historical gate")
    axes[0, 0].plot(event, new_count, color="#2765A8", label="new gate")
    axes[0, 0].set_title("Admitted candidates at each recorded decision")
    axes[0, 0].set_xlabel("decision ordinal")
    axes[0, 0].set_ylabel("candidate count")
    axes[0, 0].legend(frameon=False)

    axes[0, 1].plot(
        rolling_event,
        old_rolling,
        color="#B64343",
        label="historical gate",
    )
    axes[0, 1].plot(
        rolling_event,
        new_rolling,
        color="#2765A8",
        label="new gate",
    )
    axes[0, 1].set_ylim(-0.02, 1.02)
    axes[0, 1].set_title(f"Any admitted candidate, rolling {window} decisions")
    axes[0, 1].set_xlabel("decision ordinal")
    axes[0, 1].set_ylabel("fraction")

    axes[1, 0].hist(q_new, bins=30, color="#2765A8", alpha=0.85)
    axes[1, 0].axvline(
        0.10, color="#B64343", linestyle="--", label="admission boundary"
    )
    axes[1, 0].set_title("Posterior probability incremental harm is acceptable")
    axes[1, 0].set_xlabel("conservative posterior probability")
    axes[1, 0].set_ylabel("candidate-context rows")
    axes[1, 0].legend(frameon=False)

    axes[1, 1].hist(margin, bins=30, color="#3B7D44", alpha=0.85)
    axes[1, 1].axvline(0.0, color="#222222", linestyle="--")
    axes[1, 1].set_title("New-gate admission margin")
    axes[1, 1].set_xlabel("q - alpha; positive is admitted")
    axes[1, 1].set_ylabel("candidate-context rows")
    figure.suptitle("Heilbronn memory-v2 safety-gate fixed-history replay", fontsize=15)
    figure.savefig(output, dpi=180)
    plt.close(figure)


def replay(source: Path, output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    projection = output_dir / "historical_gate_projection.sqlite3"
    projection_meta = _create_historical_projection(source, projection)
    config_path = _find_run_config(source)
    config = _posterior_config(config_path)
    trajectory = load_calibration_trajectory(projection)
    units = _prepare_units((trajectory,))
    stored = _stored_actions(projection)
    regressor = StableBayesianLogisticRegressor(config)
    candidate_rows: list[dict[str, Any]] = []

    for unit_index, unit in enumerate(units, start=1):
        prior_mean = np.zeros(unit.space.outcome_dim, dtype=float)
        prior_mean[0] = float(logit(config.invalidity_prior_probability))
        prior_mean[unit.space.baseline_dim] = config.safety_shared_effect_prior_mean
        prior_variance = unit.space.prior_variance(
            baseline_sd=config.safety_baseline_prior_sd,
            shared_effect_sd=config.safety_shared_effect_prior_sd,
            card_effect_sd=config.safety_card_effect_prior_sd,
        )
        prior_variance[0] = config.safety_baseline_prior_sd**2
        posterior = regressor.fit(
            unit.history_design,
            unit.history_invalid,
            prior_mean,
            prior_variance,
        )
        for candidate in unit.candidates:
            designs = np.stack((candidate.control_design, candidate.treated_design))
            means = designs @ posterior.mean
            covariance = designs @ posterior.covariance @ designs.T
            historical_probability = _deterministic_safety_gate(
                means,
                covariance,
                max_treated_invalid_probability=(unit.max_treated_invalid_probability),
                max_incremental_invalid_probability=(
                    unit.max_incremental_invalid_probability
                ),
                alpha=unit.safety_alpha,
                integration_tolerance=config.safety_integration_tolerance,
            )[1]
            counterfactual_probability = _deterministic_safety_gate(
                means,
                covariance,
                max_treated_invalid_probability=None,
                max_incremental_invalid_probability=0.10,
                alpha=0.10,
                integration_tolerance=config.safety_integration_tolerance,
            )[1]
            stored_row = stored[(unit.decision_id, candidate.treatment_id)]
            candidate_rows.append(
                {
                    "decision_id": unit.decision_id,
                    "event_ordinal": unit.event_ordinal,
                    "treatment_id": candidate.treatment_id,
                    "history_count": unit.history_count,
                    "card_history_count": candidate.card_history_count,
                    "stored_admitted": stored_row["stored_admitted"],
                    "historical_admitted": safety_gate_admits(
                        gate_mode=HISTORICAL_MODE,
                        probability_acceptable=historical_probability,
                        alpha=unit.safety_alpha,
                    ),
                    "counterfactual_admitted": safety_gate_admits(
                        gate_mode=COUNTERFACTUAL_MODE,
                        probability_acceptable=counterfactual_probability,
                        alpha=0.10,
                    ),
                    "stored_probability_acceptable": stored_row[
                        "stored_probability_acceptable"
                    ],
                    "historical_probability_acceptable": historical_probability,
                    "counterfactual_probability_acceptable": (
                        counterfactual_probability
                    ),
                    "counterfactual_margin": counterfactual_probability - 0.10,
                }
            )
        if unit_index % 25 == 0 or unit_index == len(units):
            print(f"replayed {unit_index}/{len(units)} decisions", flush=True)

    decisions: dict[str, dict[str, Any]] = {}
    for row in candidate_rows:
        aggregate = decisions.setdefault(
            row["decision_id"],
            {
                "decision_id": row["decision_id"],
                "event_ordinal": row["event_ordinal"],
                "candidate_count": 0,
                "stored_admitted": 0,
                "historical_admitted": 0,
                "counterfactual_admitted": 0,
            },
        )
        aggregate["candidate_count"] += 1
        aggregate["stored_admitted"] += int(row["stored_admitted"])
        aggregate["historical_admitted"] += int(row["historical_admitted"])
        aggregate["counterfactual_admitted"] += int(row["counterfactual_admitted"])
    decision_rows = sorted(decisions.values(), key=lambda row: row["event_ordinal"])
    old_mismatches = sum(
        row["stored_admitted"] != row["historical_admitted"] for row in candidate_rows
    )
    probability_error = max(
        abs(
            row["stored_probability_acceptable"]
            - row["historical_probability_acceptable"]
        )
        for row in candidate_rows
    )
    summary = {
        "analysis": "fixed-history safety-gate counterfactual",
        "source_ledger": str(source.resolve()),
        "config": str(config_path.resolve()),
        "projection": str(projection.resolve()),
        **projection_meta,
        "decisions_with_candidates": len(decision_rows),
        "candidate_context_rows": len(candidate_rows),
        "historical_admitted_candidate_rows": sum(
            row["historical_admitted"] for row in candidate_rows
        ),
        "counterfactual_admitted_candidate_rows": sum(
            row["counterfactual_admitted"] for row in candidate_rows
        ),
        "historical_decisions_without_admitted_card": sum(
            not row["historical_admitted"] for row in decision_rows
        ),
        "counterfactual_decisions_without_admitted_card": sum(
            not row["counterfactual_admitted"] for row in decision_rows
        ),
        "historical_trailing_lockout": _trailing_lockout(
            decision_rows, "historical_admitted"
        ),
        "counterfactual_trailing_lockout": _trailing_lockout(
            decision_rows, "counterfactual_admitted"
        ),
        "historical_admission_mismatches": old_mismatches,
        "max_historical_probability_replay_error": probability_error,
        "counterfactual_min_margin": min(
            row["counterfactual_margin"] for row in candidate_rows
        ),
        "counterfactual_median_margin": float(
            np.median([row["counterfactual_margin"] for row in candidate_rows])
        ),
        "limitation": (
            "Uses each recorded decision's frozen observed history. It does not "
            "identify outcomes, future bank states, or evolution under newly "
            "admitted actions because the historical policy had zero support there."
        ),
    }
    _write_csv(output_dir / "candidate_gate_replay.csv", candidate_rows)
    _write_csv(output_dir / "decision_gate_replay.csv", decision_rows)
    _plot(
        decision_rows,
        candidate_rows,
        output_dir / "safety_gate_counterfactual.png",
    )
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    arguments = parser.parse_args()
    summary = replay(arguments.ledger.resolve(), arguments.output_dir.resolve())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
