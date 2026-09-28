"""GigaEvo validator for reverse-SCM predictor graph JSON genomes."""

from __future__ import annotations

from enum import StrEnum
import os
from pathlib import Path
import re
import sys

import numpy as np

_SOURCE_PATH = globals().get("__file__")
_PROBLEM_DIR = (
    Path(_SOURCE_PATH).resolve().parent if _SOURCE_PATH else Path(sys.path[0]).resolve()
)
_TABULAR_COMMON = _PROBLEM_DIR.parent / "tabular" / "_common"
if str(_TABULAR_COMMON) not in sys.path:
    sys.path.insert(0, str(_TABULAR_COMMON))

import tabular_data  # noqa: E402
from tabular_problem import build  # noqa: E402

from problems.tab_wpf.execution import (  # noqa: E402
    GraphExecutionError,
    assert_split_invariant,
    execute_graph_triplet,
)
from problems.tab_wpf.graph import PredictorGraph  # noqa: E402
from problems.tab_wpf.model import PredictorGraphModel  # noqa: E402
from problems.tab_wpf.sandbox_evaluation import (  # noqa: E402
    evaluate_sandbox_suite,
)
from problems.tab_wpf.synthetic_evaluation import (  # noqa: E402
    evaluate_synthetic_suite,
)
from problems.tab_wpf.synthetic_tasks import META_TRAIN  # noqa: E402

_DATASET_ENV = "GIGAEVO_TABULAR_EVAL_DATASET"
_DEFAULT_DATASET = "california"
_EVALUATION_MODE_ENV = "GIGAEVO_TAB_WPF_EVAL_MODE"
_TASK_BANK_ENV = "GIGAEVO_TAB_WPF_TASK_BANK"
_META_SPLIT_ENV = "GIGAEVO_TAB_WPF_META_SPLIT"
_SAMPLE_SIZE_ENV = "GIGAEVO_TAB_WPF_SAMPLE_SIZE"
_SAMPLE_SEED_ENV = "GIGAEVO_TAB_WPF_SAMPLE_SEED"

_INVALID = {
    "fitness": -1.0,
    "is_valid": 0.0,
    "cv_score_std": 2.0,
    "task_score_p10": -1.0,
    "evaluated_task_count": 0.0,
    "valid_task_rate": 0.0,
    "graph_node_count": 0.0,
    "graph_max_depth": 0.0,
    "generated_feature_count": 0.0,
    "local_lipschitz_p95": 4.0,
    "ood_delta_slope": 2.0,
}


class ValidationFailureReason(StrEnum):
    SCHEMA = "schema"
    EXECUTION = "execution"
    NON_FINITE = "non_finite"
    BATCH_PURITY = "batch_purity"
    DETERMINISM = "determinism"
    OWN_TARGET_INVARIANCE = "own_target_invariance"
    MODEL_FIT = "model_fit"
    DATASET_CONTRACT = "dataset_contract"
    SYNTHETIC_TASK_BANK = "synthetic_task_bank"
    SANDBOX_TASK_BANK = "sandbox_task_bank"
    UNKNOWN = "unknown"


def dataset_name(context: dict | None = None) -> str:
    if context and isinstance(context, dict):
        dataset = context.get("dataset")
        if isinstance(dataset, str) and dataset:
            return dataset
    return os.environ.get(_DATASET_ENV, _DEFAULT_DATASET)


def _validation_failure_reason(exc: Exception, stage: str) -> ValidationFailureReason:
    message = str(exc).lower()
    if stage == "schema":
        return ValidationFailureReason.SCHEMA
    if stage == "dataset_contract":
        return ValidationFailureReason.DATASET_CONTRACT
    if stage == "synthetic_task_bank":
        return ValidationFailureReason.SYNTHETIC_TASK_BANK
    if stage == "sandbox_task_bank":
        return ValidationFailureReason.SANDBOX_TASK_BANK
    if stage == "model_fit":
        return ValidationFailureReason.MODEL_FIT
    if "own-target leakage" in message:
        return ValidationFailureReason.OWN_TARGET_INVARIANCE
    if "non-deterministic" in message:
        return ValidationFailureReason.DETERMINISM
    if "split-dependent" in message or "batch-dependent" in message:
        return ValidationFailureReason.BATCH_PURITY
    if "non-finite" in message or "contains inf" in message:
        return ValidationFailureReason.NON_FINITE
    if stage == "behavioral_probes":
        return ValidationFailureReason.EXECUTION
    return ValidationFailureReason.UNKNOWN


def _failure_artifact(exc: Exception, stage: str) -> dict[str, object]:
    message = str(exc)
    node_match = re.search(r"\bnode ([A-Za-z][A-Za-z0-9_]*)", message)
    artifact: dict[str, object] = {
        "error": f"{type(exc).__name__}: {message}",
        "validation_failure_reason": _validation_failure_reason(exc, stage).value,
        "validation_failure_stage": stage,
    }
    if node_match is not None:
        artifact["validation_failure_node"] = node_match.group(1)
    return artifact


def _factory(graph: PredictorGraph, dataset: str):
    return lambda: PredictorGraphModel(graph, dataset)


def _sanitize_behavior_descriptors(metrics: dict[str, float]) -> list[str]:
    """Replace undefined behavior descriptors with their conservative caps."""
    replaced: list[str] = []
    for name in ("local_lipschitz_p95", "ood_delta_slope"):
        value = metrics.get(name)
        if value is not None and not np.isfinite(float(value)):
            metrics[name] = _INVALID[name]
            replaced.append(name)
    return replaced


def validate(payload, context=None):
    """Validate and score a decoded PredictorGraph JSON document."""
    stage = "schema"
    dataset = dataset_name(context if isinstance(context, dict) else None)
    try:
        graph = PredictorGraph.model_validate(payload)
        stage = "evaluation_mode"
        evaluation_mode = os.environ.get(_EVALUATION_MODE_ENV, "real").strip().lower()
        if evaluation_mode == "synthetic":
            stage = "synthetic_task_bank"
            bank_dir = os.environ.get(_TASK_BANK_ENV)
            if not bank_dir:
                raise ValueError(f"{_TASK_BANK_ENV} is required in synthetic mode")
            meta_split = os.environ.get(_META_SPLIT_ENV, META_TRAIN)
            return evaluate_synthetic_suite(
                graph,
                bank_dir,
                meta_split=meta_split,
                allow_meta_test=False,
            )
        if evaluation_mode == "sandbox":
            stage = "sandbox_task_bank"
            bank_dir = os.environ.get(_TASK_BANK_ENV)
            if not bank_dir:
                raise ValueError(f"{_TASK_BANK_ENV} is required in sandbox mode")
            meta_split = os.environ.get(_META_SPLIT_ENV, META_TRAIN)
            sample_size_raw = os.environ.get(_SAMPLE_SIZE_ENV, "").strip()
            sample_size = int(sample_size_raw) if sample_size_raw else None
            sample_seed = int(os.environ.get(_SAMPLE_SEED_ENV, "0"))
            return evaluate_sandbox_suite(
                graph,
                bank_dir,
                meta_split=meta_split,
                allow_meta_test=False,
                sample_size=sample_size,
                sample_seed=sample_seed,
            )
        if evaluation_mode != "real":
            raise ValueError(
                f"unknown {_EVALUATION_MODE_ENV}={evaluation_mode!r}; "
                "expected 'real', 'synthetic', or 'sandbox'"
            )
        stage = "dataset_contract"
        ds = tabular_data.load_dataset(dataset)
        stage = "behavioral_probes"
        sample_size = min(1024, len(ds.X_train))
        rng = np.random.default_rng(0)
        sample_indices = np.sort(
            rng.choice(len(ds.X_train), size=sample_size, replace=False)
        )
        X_sample = np.asarray(ds.X_train[sample_indices], dtype=np.float64)
        y_sample = np.asarray(ds.y_train[sample_indices])
        assert_split_invariant(
            graph,
            X_sample,
            y_fit=y_sample,
            columns=ds.columns,
            task_type=ds.task_type,
            n_classes=ds.n_classes,
        )
        execute_graph_triplet(
            graph,
            X_sample,
            X_sample[:0],
            X_sample[: min(8, sample_size)],
            y_fit=y_sample,
            columns=ds.columns,
            task_type=ds.task_type,
            n_classes=ds.n_classes,
        )
        stage = "model_fit"
        metrics, evaluation_artifact = build(dataset).validate(_factory(graph, dataset))
        descriptor_fallbacks = _sanitize_behavior_descriptors(metrics)
        sample_size = min(64, len(ds.X_train))
        readout_features, _ = execute_graph_triplet(
            graph,
            np.asarray(ds.X_train[:sample_size], dtype=np.float64),
            np.asarray(ds.X_train[:0], dtype=np.float64),
            np.asarray(ds.X_train[: min(8, sample_size)], dtype=np.float64),
            y_fit=np.asarray(ds.y_train[:sample_size]),
            columns=ds.columns,
            task_type=ds.task_type,
            n_classes=ds.n_classes,
        )
        readout_channels = readout_features.fit.shape[1]
        metrics.update(
            {
                "task_score_p10": float(metrics["fitness"]),
                "evaluated_task_count": 1.0,
                "valid_task_rate": 1.0,
                "graph_node_count": float(len(graph.nodes)),
                "graph_max_depth": float(graph.depth),
                "generated_feature_count": float(readout_channels),
            }
        )
        artifact = {
            "dataset": dataset,
            "graph_node_count": len(graph.nodes),
            "readout_kind": graph.readout.kind,
        }
        if isinstance(evaluation_artifact, dict):
            artifact.update(evaluation_artifact)
        if descriptor_fallbacks:
            artifact["behavior_descriptor_fallbacks"] = descriptor_fallbacks
        non_finite = [
            name for name, value in metrics.items() if not np.isfinite(float(value))
        ]
        if non_finite:
            raise GraphExecutionError(
                f"non-finite metrics after descriptor fallback: {sorted(non_finite)}"
            )
        return metrics, artifact
    except Exception as exc:
        return dict(_INVALID), _failure_artifact(exc, stage)


def score_on_test(payload, *, dataset: str | None = None):
    """Score on the untouched test split under the tabular protocol."""
    graph = PredictorGraph.model_validate(payload)
    ds_name = dataset or dataset_name()
    return build(ds_name).score_on_test(_factory(graph, ds_name))


def score_on_synthetic_split(
    payload,
    *,
    bank_dir: str | Path,
    meta_split: str,
    allow_meta_test: bool = False,
):
    """Explicit reporting API; sealed meta-test requires deliberate opt-in."""

    graph = PredictorGraph.model_validate(payload)
    return evaluate_synthetic_suite(
        graph,
        bank_dir,
        meta_split=meta_split,
        allow_meta_test=allow_meta_test,
    )


def score_on_sandbox_split(
    payload,
    *,
    bank_dir: str | Path,
    meta_split: str,
    allow_meta_test: bool = False,
    sample_size: int | None = None,
    sample_seed: int = 0,
):
    """Explicit reporting API for the restricted classification sandbox."""

    graph = PredictorGraph.model_validate(payload)
    return evaluate_sandbox_suite(
        graph,
        bank_dir,
        meta_split=meta_split,
        allow_meta_test=allow_meta_test,
        sample_size=sample_size,
        sample_seed=sample_seed,
    )
