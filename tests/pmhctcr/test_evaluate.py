from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pytest

PROBLEM_DIR = Path(__file__).resolve().parents[2] / "problems" / "pmhctcr"


def _load(name: str, path: Path):
    spec = spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_cdr3_logistic_validate_and_test_are_disjoint():
    from problems.pmhctcr.dataset import data_root

    asset_root = data_root()
    required = (
        PROBLEM_DIR / "tables" / "samples.parquet",
        asset_root / "pdb",
        asset_root / "masif",
        asset_root / "esm2_t6_8M_UR50D",
    )
    if not all(path.exists() for path in required):
        pytest.skip("ImmRep25 tables and feature assets are provided separately")
    sys.path.insert(0, str(PROBLEM_DIR))
    seed = _load("_pmhctcr_cdr3", PROBLEM_DIR / "initial_programs" / "cdr3_logistic.py")
    validator = _load("_pmhctcr_validate", PROBLEM_DIR / "validate.py")
    predictor = seed.entrypoint()
    val_metrics, val_art = validator.validate(predictor)
    assert val_metrics["is_valid"] == 1.0
    assert val_metrics["n_pmhc"] == 4.0
    assert 0.0 <= val_metrics["fitness"] <= 1.0
    assert 0.0 <= val_metrics["mean_aucpr"] <= 1.0
    assert "auc0.1" in next(iter(val_art["per_pmhc"].values()))
    assert "aucpr" in next(iter(val_art["per_pmhc"].values()))
    assert val_metrics["fitness"] == pytest.approx(
        sum(v["aucpr"] for v in val_art["per_pmhc"].values()) / 4.0
    )
    assert val_metrics["mean_aucpr"] == pytest.approx(val_metrics["fitness"])
    assert val_metrics["mean_auc01"] == pytest.approx(
        sum(v["auc0.1"] for v in val_art["per_pmhc"].values()) / 4.0
    )
    assert val_art["eval_fold"] == "val"
    test_metrics, test_art = validator.score_on_test(seed.entrypoint())
    assert test_metrics["is_valid"] == 1.0
    assert test_metrics["n_pmhc"] == 4.0
    assert test_art["eval_fold"] == "test"
    assert set(val_art["per_pmhc"]) != set(test_art["per_pmhc"])
    assert set(val_art["per_pmhc"]).isdisjoint(set(test_art["per_pmhc"]))


def test_macro_is_unweighted_mean_across_pmhc():
    sys.path.insert(0, str(PROBLEM_DIR))
    evaluate = _load("_pmhctcr_evaluate_macro", PROBLEM_DIR / "evaluate.py")
    import numpy as np
    import pandas as pd

    y_a = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 0], dtype=float)
    s_a = np.array([0.9, 0.8, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1])
    y_b = np.array([1, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=float)
    s_b = np.array([0.2, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.1, 0.0])
    rows = pd.DataFrame(
        {
            "mhc_epitope_id": ["pmhc_a"] * 10 + ["pmhc_b"] * 10,
            "label": np.concatenate([y_a, y_b]),
        }
    )
    scores = np.concatenate([s_a, s_b])
    metrics, artifact = evaluate.score_fold(rows, scores)
    per = artifact["per_pmhc"]
    assert metrics["is_valid"] == 1.0
    assert metrics["fitness"] == pytest.approx(
        0.5 * (per["pmhc_a"]["aucpr"] + per["pmhc_b"]["aucpr"])
    )
    assert metrics["mean_aucpr"] == pytest.approx(metrics["fitness"])
    assert metrics["mean_auc01"] == pytest.approx(
        0.5 * (per["pmhc_a"]["auc0.1"] + per["pmhc_b"]["auc0.1"])
    )
    assert metrics["n_pmhc"] == 2.0
