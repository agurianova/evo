from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[2]
PROBLEM_DIR = REPO / "problems" / "pmhctcr"
OOD = REPO / "double_ood_seed"


def _load(name: str, path: Path):
    spec = spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def cv3_env(monkeypatch):
    if not (OOD / "tables" / "samples.parquet").is_file():
        pytest.skip("double_ood_seed tables missing")
    monkeypatch.setenv("PMHCTCR_DATA", str(OOD))
    monkeypatch.setenv("PMHCTCR_SPLIT", "cv3")
    for name in ("dataset", "evaluate", "behavior", "assets", "split"):
        sys.modules.pop(name, None)
        sys.modules.pop(f"problems.pmhctcr.{name}", None)
    sys.path.insert(0, str(PROBLEM_DIR))
    dataset = _load("_pmhctcr_dataset_cv3", PROBLEM_DIR / "dataset.py")
    validate = _load("_pmhctcr_validate_cv3", PROBLEM_DIR / "validate.py")
    return dataset, validate


def test_cv3_folds_are_leave_one_pmhc_out(cv3_env):
    dataset, _ = cv3_env
    folds = dataset.load_cv3_folds()
    assert len(folds) == 3
    ids = {val_id for _, _, val_id in folds}
    assert ids == {"pmhc_0000010", "pmhc_0000031", "pmhc_0000048"}
    for train, val, val_id in folds:
        assert set(val["mhc_epitope_id"].unique()) == {val_id}
        assert val_id not in set(train["mhc_epitope_id"].unique())
        assert train["mhc_epitope_id"].nunique() == 2
        assert len(train) + len(val) == 1642


def test_cv3_validate_dummy_scores_three_pmhc(cv3_env):
    _, validate = cv3_env

    class Dummy:
        def __init__(self):
            self.fits = []

        def fit(self, train_df):
            self.fits.append(sorted(train_df["mhc_epitope_id"].unique()))

        def score(self, rows_df):
            return np.full(len(rows_df), 0.2)

    metrics, art = validate.validate(Dummy())
    assert art["eval_fold"] == "cv3"
    assert art["split"] == "cv3"
    assert set(art["per_pmhc"]) == {"pmhc_0000010", "pmhc_0000031", "pmhc_0000048"}
    assert metrics["n_pmhc"] == 3.0
    assert metrics["n_scored"] == 1642.0
    assert metrics["is_valid"] == 1.0
    assert metrics["fitness"] == pytest.approx(metrics["mean_aucpr"])
