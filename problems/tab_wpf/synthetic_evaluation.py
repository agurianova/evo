"""Episode-level evaluation of PredictorDAG genomes on a frozen task bank.

The evaluator is intentionally asymmetric: a predictor receives only
``(X_context, y_context, X_query)``.  ``y_query`` remains in the evaluator and
is touched only after prediction, when the held-out score is computed.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.metrics import r2_score

from gigaevo.programs.metrics.paired import sample_sequence_signature
from problems.tabular._common import tabular_data

from .graph import PredictorGraph
from .model import PredictorGraphModel
from .synthetic_tasks import (
    META_TEST,
    SyntheticTask,
    iter_tasks,
    load_manifest,
)

SCORE_LOWER_BOUND = -1.0
SCORE_UPPER_BOUND = 1.0


class SyntheticEvaluationError(RuntimeError):
    """A graph failed on one of the frozen predictor episodes."""


@dataclass(frozen=True)
class PredictorEpisode:
    """The complete public input of a predictor, excluding hidden query labels."""

    columns: tuple[tabular_data.ColumnSpec, ...]
    X_context: np.ndarray
    y_context: np.ndarray
    X_query: np.ndarray


def predictor_episode(task: SyntheticTask) -> PredictorEpisode:
    """Drop all generator metadata and query labels at the predictor boundary."""

    return PredictorEpisode(
        columns=task.columns,
        X_context=task.X_context,
        y_context=task.y_context,
        X_query=task.X_query,
    )


def _episode_seed(task_id: str) -> int:
    digest = hashlib.sha256(task_id.encode("utf-8")).digest()
    return int.from_bytes(digest[:4], byteorder="little", signed=False)


def predict_episode(
    graph: PredictorGraph,
    episode: PredictorEpisode,
    *,
    seed: int,
) -> tuple[np.ndarray, int]:
    """Fit on labeled context and predict query rows without a query-target API."""

    model = PredictorGraphModel(
        graph,
        columns=episode.columns,
        task_type=tabular_data.REGRESSION,
        n_classes=None,
    )
    prediction = model.predict_episode(
        episode.X_context,
        episode.y_context,
        episode.X_query,
        seed=seed,
    )
    prediction = np.asarray(prediction, dtype=np.float64).reshape(-1)
    if prediction.shape != (len(episode.X_query),):
        raise SyntheticEvaluationError(
            "predictor returned an invalid query prediction shape: "
            f"{prediction.shape}"
        )
    if not np.all(np.isfinite(prediction)):
        raise SyntheticEvaluationError("predictor returned non-finite query values")
    feature_count = int(getattr(model, "generated_feature_count_", 0))
    return prediction, feature_count


def evaluate_synthetic_suite(
    graph: PredictorGraph,
    bank_dir: str | Path,
    *,
    meta_split: str,
    allow_meta_test: bool = False,
) -> tuple[dict[str, float], dict[str, Any]]:
    """Evaluate one graph on one frozen outer split.

    The primary fitness is the mean clipped query R2, first averaged within
    each generator family and then equally across families.  Because every
    production split is balanced by family, this also equals the task mean.
    Each task, rather than a fold or row, is the statistical replicate.
    """

    if meta_split == META_TEST and not allow_meta_test:
        raise PermissionError(
            "meta_test is sealed during evolution; use the reporting CLI with "
            "--allow-meta-test after selecting a final graph"
        )
    manifest = load_manifest(bank_dir)
    tasks = list(iter_tasks(bank_dir, meta_split=meta_split, verify_checksum=True))
    if not tasks:
        raise ValueError(f"task bank has no tasks in split {meta_split!r}")
    expected_count = int(manifest["split_counts"][meta_split])
    if len(tasks) != expected_count:
        raise ValueError(
            f"split {meta_split!r} must contain {expected_count} tasks, "
            f"got {len(tasks)}"
        )

    per_task: list[dict[str, Any]] = []
    by_family: dict[str, list[float]] = defaultdict(list)
    generated_feature_counts: list[int] = []
    for task in tasks:
        try:
            prediction, feature_count = predict_episode(
                graph,
                predictor_episode(task),
                seed=_episode_seed(task.task_id),
            )
            # y_query is first accessed here, after the prediction is complete.
            raw_score = float(r2_score(task.y_query, prediction))
        except Exception as exc:
            raise SyntheticEvaluationError(
                f"task {task.task_id} ({task.family}) failed: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        if not np.isfinite(raw_score):
            raise SyntheticEvaluationError(
                f"task {task.task_id} produced non-finite query R2"
            )
        clipped_score = float(
            np.clip(raw_score, SCORE_LOWER_BOUND, SCORE_UPPER_BOUND)
        )
        generated_feature_counts.append(feature_count)
        by_family[task.family].append(clipped_score)
        per_task.append(
            {
                "task_id": task.task_id,
                "family": task.family,
                "raw_query_r2": raw_score,
                "clipped_query_r2": clipped_score,
            }
        )

    family_means = {
        family: float(np.mean(scores)) for family, scores in sorted(by_family.items())
    }
    expected_families = set(manifest["families"])
    family_sizes = {family: len(scores) for family, scores in by_family.items()}
    if set(family_sizes) != expected_families or len(set(family_sizes.values())) != 1:
        raise ValueError(
            f"split {meta_split!r} is not balanced across generator families: "
            f"{family_sizes}"
        )
    clipped_scores = np.asarray(
        [record["clipped_query_r2"] for record in per_task], dtype=np.float64
    )
    raw_scores = np.asarray(
        [record["raw_query_r2"] for record in per_task], dtype=np.float64
    )
    fitness = float(np.mean(list(family_means.values())))
    score_std = float(np.std(clipped_scores, ddof=1)) if len(clipped_scores) > 1 else 0.0
    task_score_p10 = float(np.quantile(clipped_scores, 0.10))
    feature_count = max(generated_feature_counts, default=0)

    metrics = {
        "fitness": fitness,
        "is_valid": 1.0,
        # Kept for compatibility with the real-data protocol.  In synthetic
        # mode the evaluation unit is a whole task, not a CV fold.
        "cv_score_std": score_std,
        "task_score_p10": task_score_p10,
        "evaluated_task_count": float(len(per_task)),
        "valid_task_rate": 1.0,
        "graph_node_count": float(len(graph.nodes)),
        "graph_max_depth": float(graph.depth),
        "generated_feature_count": float(feature_count),
        # The existing single-dataset behavior descriptors do not have a
        # comparable meaning across heterogeneous synthetic tasks.  They stay
        # finite and prompt-hidden; the synthetic preset archives by fitness.
        "local_lipschitz_p95": 0.0,
        "ood_delta_slope": 0.0,
    }
    ordered_task_ids = [record["task_id"] for record in per_task]
    cohort_signature = sample_sequence_signature(
        {
            "bank_checksum": manifest["bank_checksum"],
            "meta_split": meta_split,
            "ordered_task_ids": ordered_task_ids,
        }
    )
    artifact: dict[str, Any] = {
        "evaluation_mode": "synthetic_task_bank",
        "meta_split": meta_split,
        "bank_checksum": manifest["bank_checksum"],
        "task_count": len(per_task),
        "score_unit": "synthetic_task",
        "fitness_aggregation": "mean_within_family_then_equal_mean_across_families",
        "score_clipping": [SCORE_LOWER_BOUND, SCORE_UPPER_BOUND],
        "family_mean_clipped_query_r2": family_means,
        "raw_query_r2_mean": float(np.mean(raw_scores)),
        "raw_query_r2_min": float(np.min(raw_scores)),
        "per_task_scores": per_task,
        "behavior_descriptors": "not_computed_in_synthetic_mode",
        "_program_metadata": {
            "synthetic_bank_checksum": manifest["bank_checksum"],
            "synthetic_meta_split": meta_split,
            "synthetic_task_ids": ordered_task_ids,
            "per_sample_scores": clipped_scores.tolist(),
            "per_sample_signature": cohort_signature,
        },
        "_evaluation_measurements": {
            "fitness": {
                "sample_sd": score_std,
                "n": len(per_task),
                "method": "sample SD across frozen synthetic tasks",
            }
        },
    }
    return metrics, artifact
