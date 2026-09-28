#!/usr/bin/env python3
"""Strictly verify and summarize a frozen Tab-WPF sandbox bank."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from problems.tab_wpf.sandbox_tasks import verify_sandbox_bank  # noqa: E402


def _counter(values: list[Any]) -> dict[str, int]:
    return {
        str(key): int(count)
        for key, count in sorted(Counter(values).items(), key=lambda item: str(item[0]))
    }


def _quantiles(values: list[float]) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "min": float(np.min(array)),
        "p50": float(np.quantile(array, 0.50)),
        "p95": float(np.quantile(array, 0.95)),
        "max": float(np.max(array)),
    }


def audit(bank_dir: Path) -> dict[str, Any]:
    root = bank_dir.expanduser().resolve()
    manifest = verify_sandbox_bank(root)
    metadata = [
        json.loads((root / record["task_dir"] / "task.json").read_text())
        for record in manifest["tasks"]
    ]
    attempts = [int(task["attempt"]) for task in metadata]
    calibration_errors = [
        abs(
            float(task["generator"]["realized_calibration_oracle_quality"])
            - float(task["generator"]["requested_oracle_quality"])
        )
        for task in metadata
    ]
    context_quality_offsets = [
        float(task["generator"]["realized_context_oracle_quality"])
        - float(task["generator"]["requested_oracle_quality"])
        for task in metadata
    ]
    query_quality_offsets = [
        float(task["generator"]["realized_query_oracle_quality"])
        - float(task["generator"]["requested_oracle_quality"])
        for task in metadata
    ]
    tree_depths = [
        int(node["depth"])
        for task in metadata
        for node in task["generator"]["nodes"][:-1]
        if node["op"] == "tree"
    ]
    bank_bytes = sum(path.stat().st_size for path in root.rglob("*") if path.is_file())
    return {
        "path": str(root),
        "bank_checksum": manifest["bank_checksum"],
        "generator_source_sha256": manifest["generator_source_sha256"],
        "task_count": manifest["task_count"],
        "bank_bytes": bank_bytes,
        "primary_stratum_count": manifest["primary_stratum_count"],
        "tasks_per_primary_stratum": manifest["tasks_per_primary_stratum"],
        "split_counts": manifest["split_counts"],
        "family_counts": manifest["family_counts"],
        "controls": {
            "n_rows": _counter([task["n_rows"] for task in metadata]),
            "n_features": _counter([task["n_features"] for task in metadata]),
            "categorical_fraction_requested": _counter(
                [task["categorical_fraction_requested"] for task in metadata]
            ),
            "max_categorical_cardinality": _counter(
                [task["max_categorical_cardinality"] for task in metadata]
            ),
            "n_classes": _counter([task["n_classes"] for task in metadata]),
            "generator_dag_nodes": _counter(
                [task["generator_dag_nodes"] for task in metadata]
            ),
            "oracle_quality_target": _counter(
                [task["oracle_quality_target"] for task in metadata]
            ),
            "tree_depth": _counter(tree_depths),
        },
        "generation_attempts": {
            "nonzero_count": sum(attempt > 0 for attempt in attempts),
            "maximum": max(attempts),
            "mean": float(np.mean(attempts)),
        },
        "absolute_calibration_quality_error": _quantiles(calibration_errors),
        "context_quality_minus_target": _quantiles(context_quality_offsets),
        "query_quality_minus_target": _quantiles(query_quality_offsets),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bank", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = audit(args.bank)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
