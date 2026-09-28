"""Fit on train pMHCs, score val pMHCs. Split unit is pMHC."""

from __future__ import annotations

import copy
from typing import Any

from dataset import feature_frame, load_cv3_folds, load_folds, split_mode
from evaluate import INVALID, aggregate, score_fold
import numpy as np

try:
    from behavior import behavior_metrics
except ImportError:
    from problems.pmhctcr.behavior import behavior_metrics


def _as_predictor(payload: Any):
    if isinstance(payload, dict) and "inputs" in payload:
        try:
            from codegen import exec_program, render_program
            from genotype import loads as loads_genotype
        except ImportError:
            from problems.pmhctcr.codegen import exec_program, render_program
            from problems.pmhctcr.genotype import loads as loads_genotype
        return exec_program(render_program(loads_genotype(payload)))
    if isinstance(payload, str) and (
        "def entrypoint" in payload or "GENOTYPE_JSON" in payload
    ):
        try:
            from codegen import exec_program
        except ImportError:
            from problems.pmhctcr.codegen import exec_program
        return exec_program(payload)
    if payload is None:
        raise ValueError("entrypoint() returned None")
    if hasattr(payload, "fit") and hasattr(payload, "score"):
        return payload
    if callable(payload):
        obj = payload()
        if hasattr(obj, "fit") and hasattr(obj, "score"):
            return obj
    raise ValueError(
        "entrypoint() must return an object with fit(train) and score(rows)"
    )


def _with_behavior(metrics: dict[str, float], payload: Any) -> dict[str, float]:
    out = dict(metrics)
    out.update(behavior_metrics(payload))
    return out


def _fresh_predictor(payload: Any):
    """New unfitted predictor so each CV fold does not share weights."""
    if isinstance(payload, dict) and "inputs" in payload:
        return _as_predictor(payload)
    if isinstance(payload, str) and (
        "def entrypoint" in payload or "GENOTYPE_JSON" in payload
    ):
        return _as_predictor(payload)
    src = getattr(payload, "__genome_source__", None)
    if isinstance(src, str) and src.strip():
        try:
            from codegen import exec_program
        except ImportError:
            from problems.pmhctcr.codegen import exec_program
        return exec_program(src)
    if callable(payload) and not (
        hasattr(payload, "fit") and hasattr(payload, "score")
    ):
        return _as_predictor(payload)
    return copy.deepcopy(payload)


def _run_cv3(payload: Any) -> tuple[dict[str, float], dict]:
    """3-fold leave-one-pMHC-out: fit on 2 pMHCs, score the held-out one."""
    predictor = None
    try:
        per: dict[str, dict[str, float]] = {}
        n_train: dict[str, int] = {}
        for train, val, val_id in load_cv3_folds():
            predictor = _fresh_predictor(payload)
            predictor.fit(train)
            scores = np.asarray(predictor.score(feature_frame(val)), dtype=float)
            _, art = score_fold(val, scores)
            per.update(art.get("per_pmhc") or {})
            n_train[val_id] = int(len(train))
        metrics, artifact = aggregate(per)
        artifact = dict(artifact)
        artifact["eval_fold"] = "cv3"
        artifact["n_train"] = n_train
        artifact["split"] = "cv3"
        return _with_behavior(metrics, predictor), artifact
    except Exception as exc:
        return _with_behavior(
            dict(INVALID), predictor if predictor is not None else payload
        ), {
            "reason": f"{type(exc).__name__}: {exc}",
            "eval_fold": "cv3",
            "split": "cv3",
        }


def _run(payload: Any, eval_fold: str) -> tuple[dict[str, float], dict]:
    predictor = None
    try:
        predictor = _as_predictor(payload)
        folds = load_folds()
        train = folds["train"]
        ev = folds[eval_fold]
        predictor.fit(train)
        scores = np.asarray(predictor.score(feature_frame(ev)), dtype=float)
        metrics, artifact = score_fold(ev, scores)
        artifact = dict(artifact)
        artifact["eval_fold"] = eval_fold
        artifact["n_train"] = int(len(train))
        return _with_behavior(metrics, predictor), artifact
    except Exception as exc:
        return _with_behavior(
            dict(INVALID), predictor if predictor is not None else payload
        ), {
            "reason": f"{type(exc).__name__}: {exc}",
            "eval_fold": eval_fold,
        }


def validate(payload, context=None):
    if split_mode() == "cv3":
        return _run_cv3(payload)
    return _run(payload, "val")


def score_on_test(payload, context=None):
    if split_mode() == "cv3":
        return _run_cv3(payload)
    return _run(payload, "test")
