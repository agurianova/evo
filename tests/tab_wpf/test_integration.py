from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).parents[2]
SEED = ROOT / "problems/tab_wpf/initial_programs/baseline.json"
DATA_ROOT = os.environ.get("GIGAEVO_TABULAR_DATA")

pytestmark = pytest.mark.skipif(
    DATA_ROOT is None or not Path(DATA_ROOT).is_dir(),
    reason="GIGAEVO_TABULAR_DATA not configured",
)


def test_validate_smoke_on_baseline():
    os.environ["GIGAEVO_TABULAR_EVAL_DATASET"] = "california"
    from problems.tab_wpf.validate import validate

    metrics, artifact = validate(json.loads(SEED.read_text()))
    assert metrics["is_valid"] == 1.0
    assert metrics["fitness"] > -1.0
    assert all(np.isfinite(float(value)) for value in metrics.values())
    assert artifact["dataset"] == "california"


def test_same_genome_works_on_adult_without_column_names():
    os.environ["GIGAEVO_TABULAR_EVAL_DATASET"] = "adult"
    from problems.tab_wpf.validate import validate

    payload = json.loads(SEED.read_text())
    metrics, artifact = validate(payload)
    assert metrics["is_valid"] == 1.0
    assert artifact["dataset"] == "adult"


def test_nontrivial_evolved_style_dag_runs_through_full_evaluator():
    os.environ["GIGAEVO_TABULAR_EVAL_DATASET"] = "california"
    from problems.tab_wpf.validate import validate

    payload = {
        "schema_version": 1,
        "nodes": [
            {
                "id": "scaled",
                "op": "standardize",
                "inputs": ["raw"],
                "params": {},
                "gate": 0.8,
                "is_readout": True,
                "rationale": "Stable linear channels.",
            },
            {
                "id": "supervised",
                "op": "affine_activation",
                "inputs": ["raw"],
                "params": {
                    "fit": "supervised_ridge",
                    "activation": "tanh",
                    "n_components": 4,
                    "alpha": 1.0,
                    "seed": 11,
                },
                "gate": 1.0,
                "is_readout": True,
                "rationale": "Cross-fitted target-aligned projection.",
            },
            {
                "id": "nonlinear",
                "op": "rbf_features",
                "inputs": ["scaled"],
                "params": {"n_components": 8, "lengthscale": 1.2, "seed": 7},
                "gate": 0.5,
                "is_readout": True,
                "rationale": "Smooth nonlinear basis expansion.",
            },
        ],
        "readout": {"kind": "ridge", "alpha": 1.0, "include_raw": False},
    }
    metrics, artifact = validate(payload)

    assert metrics["is_valid"] == 1.0, artifact
    assert all(np.isfinite(float(value)) for value in metrics.values())
    assert metrics["graph_node_count"] == 3.0
    assert metrics["generated_feature_count"] > 0.0
