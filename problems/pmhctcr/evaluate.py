"""Per-pMHC AUCPR and AUC0.1. Fitness is Macro-AUCPR; AUC0.1 is logged."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

# sklearn max_fpr uses McClish standardisation, as ImmRep25 / Kaggle Macro-AUC0.1.
_MAX_FPR = 0.1

INVALID = {
    "fitness": -1.0,
    "is_valid": 0.0,
    "mean_aucpr": 0.0,
    "mean_auc01": 0.0,
    "min_auc01": 0.0,
    "min_aucpr": 0.0,
    "n_scored": 0.0,
    "n_pmhc": 0.0,
}


def _pmhc_scores(y_true: np.ndarray, y_score: np.ndarray) -> tuple[float, float] | None:
    if y_true.size < 2 or np.unique(y_true).size < 2:
        return None
    if not np.all(np.isfinite(y_score)):
        return None
    aucpr = float(average_precision_score(y_true, y_score))
    auc01 = float(roc_auc_score(y_true, y_score, max_fpr=_MAX_FPR))
    return aucpr, auc01


def per_pmhc_metrics(
    rows: pd.DataFrame, scores: np.ndarray
) -> dict[str, dict[str, float]]:
    y = rows["label"].to_numpy(dtype=float)
    s = np.asarray(scores, dtype=float)
    if s.shape != (len(rows),):
        raise ValueError(f"score shape {s.shape} != ({len(rows)},)")
    pmhc = rows["mhc_epitope_id"].to_numpy()
    out: dict[str, dict[str, float]] = {}
    for p in sorted(set(pmhc.tolist()), key=str):
        mask = pmhc == p
        rec = {"n": float(mask.sum()), "n_pos": float(y[mask].sum())}
        got = _pmhc_scores(y[mask], s[mask])
        if got is None:
            rec["aucpr"] = float("nan")
            rec["auc0.1"] = float("nan")
        else:
            rec["aucpr"], rec["auc0.1"] = got
        out[str(p)] = rec
    return out


def aggregate(per: dict[str, dict[str, float]]) -> tuple[dict[str, float], dict]:
    auc01 = np.array([v["auc0.1"] for v in per.values()], dtype=float)
    aucpr = np.array([v["aucpr"] for v in per.values()], dtype=float)
    if (
        auc01.size == 0
        or not np.all(np.isfinite(auc01))
        or not np.all(np.isfinite(aucpr))
    ):
        return dict(INVALID), {"per_pmhc": per, "reason": "non_finite_or_empty_macro"}
    n_scored = float(sum(v["n"] for v in per.values()))
    metrics = {
        "fitness": float(np.mean(aucpr)),
        "is_valid": 1.0,
        "mean_aucpr": float(np.mean(aucpr)),
        "mean_auc01": float(np.mean(auc01)),
        "min_auc01": float(np.min(auc01)),
        "min_aucpr": float(np.min(aucpr)),
        "n_scored": n_scored,
        "n_pmhc": float(len(per)),
    }
    return metrics, {"per_pmhc": per}


def score_fold(rows: pd.DataFrame, scores: np.ndarray) -> tuple[dict[str, float], dict]:
    try:
        per = per_pmhc_metrics(rows, scores)
    except ValueError as exc:
        return dict(INVALID), {"reason": str(exc)}
    return aggregate(per)
