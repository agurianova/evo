"""Classification evaluation on the restricted frozen sandbox bank."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import balanced_accuracy_score, log_loss

from gigaevo.programs.metrics.paired import sample_sequence_signature
from problems.tabular._common import tabular_data

from .graph import PredictorGraph
from .model import PredictorGraphModel
from .sandbox_tasks import (
    META_TEST,
    SandboxTask,
    iter_sandbox_tasks,
    load_sandbox_manifest,
)

SCORE_LOWER_BOUND = -1.0
SCORE_UPPER_BOUND = 1.0


class SandboxEvaluationError(RuntimeError):
    """A PredictorDAG violated the sandbox episode contract."""


@dataclass(frozen=True)
class SandboxPredictorEpisode:
    """Complete public predictor input; no query label or generator metadata."""

    columns: tuple[tabular_data.ColumnSpec, ...]
    task_type: str
    n_classes: int
    X_context: np.ndarray
    y_context: np.ndarray
    X_query: np.ndarray


def sandbox_predictor_episode(task: SandboxTask) -> SandboxPredictorEpisode:
    return SandboxPredictorEpisode(
        columns=task.columns,
        task_type=task.task_type,
        n_classes=task.n_classes,
        X_context=task.X_context,
        y_context=task.y_context,
        X_query=task.X_query,
    )


def _episode_seed(task_id: str) -> int:
    digest = hashlib.sha256(task_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], byteorder="little", signed=False)


def predict_sandbox_episode(
    graph: PredictorGraph,
    episode: SandboxPredictorEpisode,
    *,
    seed: int,
) -> tuple[np.ndarray, int]:
    """Fit on labeled context and return canonical K-class probabilities."""

    model = PredictorGraphModel(
        graph,
        columns=episode.columns,
        task_type=episode.task_type,
        n_classes=episode.n_classes,
    )
    probabilities = np.asarray(
        model.predict_episode(
            episode.X_context,
            episode.y_context,
            episode.X_query,
            seed=seed,
        ),
        dtype=np.float64,
    )
    expected_shape = (len(episode.X_query), episode.n_classes)
    if probabilities.shape != expected_shape:
        raise SandboxEvaluationError(
            f"predictor returned {probabilities.shape}, expected {expected_shape}"
        )
    if not np.all(np.isfinite(probabilities)):
        raise SandboxEvaluationError("predictor returned non-finite probabilities")
    if np.any(probabilities < -1e-12) or np.any(probabilities > 1.0 + 1e-12):
        raise SandboxEvaluationError("predictor probabilities fall outside [0, 1]")
    row_sums = probabilities.sum(axis=1)
    if not np.allclose(row_sums, 1.0, atol=1e-10, rtol=1e-10):
        raise SandboxEvaluationError("predictor probability rows do not sum to one")
    feature_count = int(getattr(model, "generated_feature_count_", 0))
    return probabilities, feature_count


def normalized_log_loss_score(
    y_query: np.ndarray,
    probabilities: np.ndarray,
    *,
    y_context: np.ndarray,
    n_classes: int,
) -> tuple[float, float, float]:
    """Return ``1 - model_log_loss / context-prior_log_loss``.

    The Laplace-smoothed context prior is a legal no-feature baseline.  A score
    of zero matches that baseline, one is perfect, and negative values are
    worse.  Clipping is performed by the suite, not by this pure helper.
    """

    labels = np.arange(n_classes)
    model_loss = float(log_loss(y_query, probabilities, labels=labels))
    counts = np.bincount(np.asarray(y_context).astype(int), minlength=n_classes)
    prior = (counts + 1.0) / (counts.sum() + n_classes)
    prior_probabilities = np.tile(prior, (len(y_query), 1))
    prior_loss = float(log_loss(y_query, prior_probabilities, labels=labels))
    if not np.isfinite(prior_loss) or prior_loss <= 0.0:
        raise SandboxEvaluationError("context-prior log loss is not positive")
    return 1.0 - model_loss / prior_loss, model_loss, prior_loss


def evaluate_sandbox_suite(
    graph: PredictorGraph,
    bank_dir: str | Path,
    *,
    meta_split: str,
    allow_meta_test: bool = False,
    sample_size: int | None = None,
    sample_seed: int = 0,
) -> tuple[dict[str, float], dict[str, Any]]:
    """Evaluate one PredictorDAG on a complete frozen sandbox split."""

    if meta_split == META_TEST and not allow_meta_test:
        raise PermissionError(
            "sandbox meta_test is sealed during evolution; explicit reporting "
            "opt-in is required"
        )
    manifest = load_sandbox_manifest(bank_dir)
    tasks = list(
        iter_sandbox_tasks(
            bank_dir,
            meta_split=meta_split,
            verify_checksum=True,
            sample_size=sample_size,
            sample_seed=sample_seed,
        )
    )
    expected_count = (
        int(manifest["split_counts"].get(meta_split, 0))
        if sample_size is None
        else int(sample_size)
    )
    if len(tasks) != expected_count or expected_count <= 0:
        raise ValueError(
            f"sandbox split {meta_split!r} expected {expected_count} tasks, "
            f"loaded {len(tasks)}"
        )

    per_task: list[dict[str, Any]] = []
    by_family: dict[str, list[float]] = defaultdict(list)
    generated_feature_counts: list[int] = []
    valid_count = 0
    for task in tasks:
        record: dict[str, Any] = {
            "task_id": task.task_id,
            "family": task.family,
            "n_classes": task.n_classes,
        }
        try:
            probabilities, feature_count = predict_sandbox_episode(
                graph,
                sandbox_predictor_episode(task),
                seed=_episode_seed(task.task_id),
            )
            # Query labels are accessed only after prediction has returned.
            raw_score, model_loss, prior_loss = normalized_log_loss_score(
                task.y_query,
                probabilities,
                y_context=task.y_context,
                n_classes=task.n_classes,
            )
            predicted_labels = np.argmax(probabilities, axis=1)
            balanced_accuracy = float(
                balanced_accuracy_score(task.y_query, predicted_labels)
            )
            chance_adjusted_balanced_accuracy = (
                balanced_accuracy - 1.0 / task.n_classes
            ) / (1.0 - 1.0 / task.n_classes)
            if not all(
                np.isfinite(value)
                for value in (
                    raw_score,
                    model_loss,
                    prior_loss,
                    balanced_accuracy,
                    chance_adjusted_balanced_accuracy,
                )
            ):
                raise SandboxEvaluationError("non-finite classification score")
            clipped_score = float(
                np.clip(raw_score, SCORE_LOWER_BOUND, SCORE_UPPER_BOUND)
            )
            record.update(
                {
                    "is_valid": True,
                    "model_log_loss": model_loss,
                    "context_prior_log_loss": prior_loss,
                    "raw_normalized_log_loss_score": raw_score,
                    "clipped_normalized_log_loss_score": clipped_score,
                    "balanced_accuracy": balanced_accuracy,
                    "chance_adjusted_balanced_accuracy": float(
                        chance_adjusted_balanced_accuracy
                    ),
                }
            )
            generated_feature_counts.append(feature_count)
            valid_count += 1
        except Exception as exc:
            clipped_score = SCORE_LOWER_BOUND
            record.update(
                {
                    "is_valid": False,
                    "clipped_normalized_log_loss_score": clipped_score,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
        by_family[task.family].append(clipped_score)
        per_task.append(record)

    family_sizes = {family: len(scores) for family, scores in by_family.items()}
    if (
        set(family_sizes) != set(manifest["families"])
        or len(set(family_sizes.values())) != 1
    ):
        raise ValueError(
            f"sandbox split {meta_split!r} is not family-balanced: {family_sizes}"
        )
    family_means = {
        family: float(np.mean(scores)) for family, scores in sorted(by_family.items())
    }
    clipped_scores = np.asarray(
        [record["clipped_normalized_log_loss_score"] for record in per_task],
        dtype=np.float64,
    )
    fitness = float(np.mean(list(family_means.values())))
    score_std = (
        float(np.std(clipped_scores, ddof=1)) if len(clipped_scores) > 1 else 0.0
    )
    ordered_task_ids = [record["task_id"] for record in per_task]
    cohort_signature = sample_sequence_signature(
        {
            "bank_checksum": manifest["bank_checksum"],
            "meta_split": meta_split,
            "ordered_task_ids": ordered_task_ids,
        }
    )
    valid_rate = valid_count / len(per_task)
    metrics = {
        "fitness": fitness,
        "is_valid": float(valid_count == len(per_task)),
        "cv_score_std": score_std,
        "task_score_p10": float(np.quantile(clipped_scores, 0.10)),
        "evaluated_task_count": float(len(per_task)),
        "valid_task_rate": float(valid_rate),
        "graph_node_count": float(len(graph.nodes)),
        "graph_max_depth": float(graph.depth),
        "generated_feature_count": float(max(generated_feature_counts, default=0)),
        "local_lipschitz_p95": 0.0,
        "ood_delta_slope": 0.0,
    }
    artifact: dict[str, Any] = {
        "evaluation_mode": "sandbox_classification_bank",
        "meta_split": meta_split,
        "bank_checksum": manifest["bank_checksum"],
        "sampling": {
            "mode": "complete_split" if sample_size is None else "balanced_cohort",
            "sample_seed": None if sample_size is None else sample_seed,
        },
        "task_count": len(per_task),
        "score_unit": "synthetic_classification_task",
        "task_score": (
            "clip(1 - model_log_loss / laplace_context_prior_log_loss, -1, 1)"
        ),
        "fitness_aggregation": "mean_within_family_then_equal_mean_across_families",
        "score_clipping": [SCORE_LOWER_BOUND, SCORE_UPPER_BOUND],
        "family_mean_clipped_score": family_means,
        "per_task_scores": per_task,
        "behavior_descriptors": "not_computed_in_sandbox_mode",
        "_program_metadata": {
            "sandbox_bank_checksum": manifest["bank_checksum"],
            "sandbox_meta_split": meta_split,
            "sandbox_task_ids": ordered_task_ids,
            "per_sample_scores": clipped_scores.tolist(),
            "per_sample_signature": cohort_signature,
        },
        "_evaluation_measurements": {
            "fitness": {
                "sample_sd": score_std,
                "n": len(per_task),
                "method": "sample SD across frozen sandbox tasks",
            }
        },
    }
    return metrics, artifact
