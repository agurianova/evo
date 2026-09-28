"""Restricted synthetic classification prior for the first Tab-WPF run.

The sandbox intentionally exposes a much smaller hypothesis class than the
general regression bank.  Every hidden GeneratorDAG contains 2--8 computation
nodes and uses only linear, MLP, and tree blocks.  The generator is run once to
freeze a bank; only PredictorDAG JSON genomes evolve afterwards.
"""

from __future__ import annotations

from collections.abc import Iterator
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from dataclasses import dataclass
from functools import cache
import hashlib
import json
from pathlib import Path
import platform
from typing import Any

import numpy as np

from problems.tabular._common import tabular_data

BANK_SCHEMA_VERSION = 2
GENERATOR_VERSION = "tab_wpf_sandbox_classifier_v2"
DEFAULT_MASTER_SEED = 20260819

META_TRAIN = "meta_train"
META_VALID = "meta_valid"
META_TEST = "meta_test"
META_SPLITS = (META_TRAIN, META_VALID, META_TEST)

FAMILIES: tuple[str, ...] = ("linear", "tree", "mlp", "mixed")
PILOT_TASKS_PER_PRIMARY_STRATUM = 5
DEFAULT_TASKS_PER_PRIMARY_STRATUM = 50

# Deliberately small, enumerable support for the debugging prior.
ROW_CHOICES: tuple[int, ...] = (256, 512, 1024)
FEATURE_CHOICES: tuple[int, ...] = (4, 8, 16, 24)
CATEGORICAL_FRACTIONS: tuple[float, ...] = (0.0, 0.25, 0.5)
MAX_CARDINALITY_CHOICES: tuple[int, ...] = (2, 4, 8)
CLASS_COUNT_CHOICES: tuple[int, ...] = (2, 3, 5)
NODE_COUNT_CHOICES: tuple[int, ...] = tuple(range(2, 9))
ELIGIBLE_FEATURE_FRACTIONS: tuple[float, ...] = (0.5, 0.75, 1.0)
ORACLE_QUALITY_TARGETS: tuple[float, ...] = (0.35, 0.55, 0.75)
ORACLE_QUALITY_TOLERANCE = 0.02
CLASS_MARGINAL_TOLERANCE = 0.025
MIN_CLASS_PROBABILITY_STD = 1e-3

PRIMARY_STRATUM_COUNT = (
    len(FAMILIES)
    * len(NODE_COUNT_CHOICES)
    * len(CLASS_COUNT_CHOICES)
    * len(ORACLE_QUALITY_TARGETS)
)


@dataclass(frozen=True)
class SandboxTask:
    task_id: str
    family: str
    meta_split: str
    task_type: str
    n_classes: int
    columns: tuple[tabular_data.ColumnSpec, ...]
    X_context: np.ndarray
    y_context: np.ndarray
    X_query: np.ndarray
    y_query: np.ndarray
    metadata: dict[str, Any]


def _json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _hash_payload(value: Any) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _source_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _update_array_hash(hasher: Any, name: str, values: np.ndarray) -> None:
    array = np.ascontiguousarray(values)
    hasher.update(name.encode("utf-8"))
    hasher.update(str(array.dtype).encode("ascii"))
    hasher.update(_json_bytes(list(array.shape)))
    hasher.update(array.tobytes(order="C"))


def _task_checksum(metadata: dict[str, Any], arrays: dict[str, np.ndarray]) -> str:
    hasher = hashlib.sha256()
    hasher.update(
        _json_bytes(
            {key: value for key, value in metadata.items() if key != "task_checksum"}
        )
    )
    for name in sorted(arrays):
        _update_array_hash(hasher, name, arrays[name])
    return hasher.hexdigest()


def _content_checksum(
    *,
    columns: list[dict[str, Any]],
    generator: dict[str, Any],
    arrays: dict[str, np.ndarray],
) -> str:
    """Identity-blind checksum used to reject relabeled duplicate tasks."""

    hasher = hashlib.sha256()
    hasher.update(_json_bytes({"columns": columns, "generator": generator}))
    for name in sorted(arrays):
        _update_array_hash(hasher, name, arrays[name])
    return hasher.hexdigest()


def _rng(
    master_seed: int,
    family_index: int,
    node_index: int,
    class_index: int,
    quality_index: int,
    replica: int,
    attempt: int,
    stream: int,
) -> np.random.Generator:
    return np.random.default_rng(
        np.random.SeedSequence(
            [
                master_seed,
                family_index,
                node_index,
                class_index,
                quality_index,
                replica,
                attempt,
                stream,
            ]
        )
    )


def _latin_values(
    master_seed: int,
    family_index: int,
    node_index: int,
    class_index: int,
    quality_index: int,
    replica: int,
    tasks_per_primary_stratum: int,
) -> np.ndarray:
    """Low-discrepancy coordinates for controls outside the primary stratum."""

    values: list[float] = []
    for dimension in range(5):
        seed = np.random.SeedSequence(
            [
                master_seed,
                family_index,
                node_index,
                class_index,
                quality_index,
                104729,
                dimension,
            ]
        )
        order = np.random.default_rng(seed).permutation(tasks_per_primary_stratum)
        values.append((float(order[replica]) + 0.5) / tasks_per_primary_stratum)
    return np.asarray(values, dtype=np.float64)


def _choice(values: tuple[Any, ...], coordinate: float) -> Any:
    index = min(int(coordinate * len(values)), len(values) - 1)
    return values[index]


@cache
def _split_assignment(
    master_seed: int,
    family_index: int,
    node_index: int,
    class_index: int,
    quality_index: int,
    tasks_per_primary_stratum: int,
) -> tuple[str, ...]:
    """Choose a deterministic 60/20/20 split inside one primary stratum."""

    if tasks_per_primary_stratum <= 0 or tasks_per_primary_stratum % 5:
        raise ValueError("tasks_per_primary_stratum must be a positive multiple of 5")
    rng = np.random.default_rng(
        np.random.SeedSequence(
            [
                master_seed,
                family_index,
                node_index,
                class_index,
                quality_index,
                130363,
            ]
        )
    )
    order = rng.permutation(tasks_per_primary_stratum)
    train_stop = 3 * tasks_per_primary_stratum // 5
    valid_stop = 4 * tasks_per_primary_stratum // 5
    assignment = [META_TRAIN] * tasks_per_primary_stratum
    for replica in order[train_stop:valid_stop]:
        assignment[int(replica)] = META_VALID
    for replica in order[valid_stop:]:
        assignment[int(replica)] = META_TEST
    return tuple(assignment)


def _meta_split(
    master_seed: int,
    family_index: int,
    node_index: int,
    class_index: int,
    quality_index: int,
    replica: int,
    tasks_per_primary_stratum: int,
) -> str:
    return _split_assignment(
        master_seed,
        family_index,
        node_index,
        class_index,
        quality_index,
        tasks_per_primary_stratum,
    )[replica]


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits, axis=1, keepdims=True)
    exponent = np.exp(np.clip(shifted, -60.0, 60.0))
    return exponent / exponent.sum(axis=1, keepdims=True)


def _balance_bias(logits: np.ndarray, scale: float) -> tuple[np.ndarray, np.ndarray]:
    n_classes = logits.shape[1]
    target = np.full(n_classes, 1.0 / n_classes, dtype=np.float64)
    bias = np.zeros(n_classes, dtype=np.float64)
    # Iterative proportional fitting converges quickly for the deliberately
    # small K<=5 sandbox.  A looser numerical tolerance is more than enough
    # for class-balance calibration and keeps large-bank generation tractable.
    for _ in range(20):
        probabilities = _softmax(scale * logits + bias)
        marginal = np.clip(probabilities.mean(axis=0), 1e-9, 1.0)
        update = np.log(target) - np.log(marginal)
        bias += update
        bias -= float(np.mean(bias))
        if float(np.max(np.abs(update))) < 1e-6:
            break
    return bias, _softmax(scale * logits + bias)


def _oracle_quality(probabilities: np.ndarray) -> float:
    conditional_entropy = -np.sum(
        probabilities * np.log(np.clip(probabilities, 1e-12, 1.0)), axis=1
    )
    marginal = np.mean(probabilities, axis=0)
    marginal_entropy = -float(np.sum(marginal * np.log(np.clip(marginal, 1e-12, 1.0))))
    if marginal_entropy <= 1e-12:
        return 0.0
    mutual_information = marginal_entropy - float(np.mean(conditional_entropy))
    return float(np.clip(mutual_information / marginal_entropy, 0.0, 1.0))


def _calibrate_logits(
    logits: np.ndarray, target_quality: float
) -> tuple[float, np.ndarray, np.ndarray, float]:
    low, high = 1e-3, 64.0
    bias = np.zeros(logits.shape[1], dtype=np.float64)
    probabilities = _softmax(logits)
    # Sixteen bisection steps resolve the logit scale much more finely
    # than the three requested oracle-quality strata while avoiding thousands
    # of redundant softmax passes per task.
    for _ in range(16):
        scale = 0.5 * (low + high)
        bias, probabilities = _balance_bias(logits, scale)
        quality = _oracle_quality(probabilities)
        if quality < target_quality:
            low = scale
        else:
            high = scale
    scale = 0.5 * (low + high)
    bias, probabilities = _balance_bias(logits, scale)
    return scale, bias, probabilities, _oracle_quality(probabilities)


def _raw_table(
    n_rows: int,
    *,
    n_features: int,
    categorical_fraction: float,
    max_cardinality: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, list[dict[str, Any]], dict[str, Any]]:
    n_categorical = int(round(n_features * categorical_fraction))
    n_categorical = min(n_categorical, n_features - 2)
    n_numeric = n_features - n_categorical

    common = rng.normal(size=(n_rows, 2))
    loadings = rng.normal(scale=0.35, size=(2, n_numeric))
    numeric = 0.75 * rng.normal(size=(n_rows, n_numeric)) + common @ loadings

    blocks: list[np.ndarray] = [numeric[:, index] for index in range(n_numeric)]
    specs: list[dict[str, Any]] = [
        {
            "kind": "numeric",
            "cardinality": None,
            "vocabulary": None,
        }
        for _ in range(n_numeric)
    ]
    cardinalities: list[int] = []
    category_permutations: list[list[int]] = []
    for categorical_index in range(n_categorical):
        if categorical_index == 0 or max_cardinality == 2:
            # When categoricals exist, at least one column realizes the
            # requested cap; the remaining columns vary below it.
            cardinality = max_cardinality
        else:
            options = tuple(value for value in (2, 4, 8) if value <= max_cardinality)
            cardinality = int(rng.choice(options))
        codes = rng.integers(0, cardinality, size=n_rows)
        permutation = rng.permutation(cardinality)
        codes = permutation[codes].astype(np.float64)
        blocks.append(codes)
        specs.append(
            {
                "kind": "categorical",
                "cardinality": cardinality,
                "vocabulary": [str(level) for level in range(cardinality)],
            }
        )
        cardinalities.append(cardinality)
        category_permutations.append(permutation.astype(int).tolist())

    order = rng.permutation(n_features)
    X = np.column_stack([blocks[int(index)] for index in order]).astype(np.float64)
    columns: list[dict[str, Any]] = []
    for new_index, old_index in enumerate(order):
        spec = dict(specs[int(old_index)])
        spec["index"] = new_index
        columns.append(spec)
    metadata = {
        "numeric_common_loadings": loadings.tolist(),
        "pre_shuffle_column_order": order.astype(int).tolist(),
        "categorical_cardinalities": cardinalities,
        "categorical_code_permutations": category_permutations,
        "n_numeric": n_numeric,
        "n_categorical": n_categorical,
    }
    return X, columns, metadata


def _fit_basis(
    X_calibration: np.ndarray,
    columns: list[dict[str, Any]],
) -> tuple[np.ndarray, dict[str, Any]]:
    blocks: list[np.ndarray] = []
    provenance: list[dict[str, Any]] = []
    numeric_state: dict[str, dict[str, float]] = {}
    for column in columns:
        index = int(column["index"])
        if column["kind"] == "numeric":
            center = float(np.mean(X_calibration[:, index]))
            scale = float(np.std(X_calibration[:, index]))
            if scale < 1e-8:
                raise ValueError("degenerate numeric calibration feature")
            blocks.append((X_calibration[:, index] - center) / scale)
            provenance.append({"column_index": index, "kind": "numeric"})
            numeric_state[str(index)] = {"center": center, "scale": scale}
        else:
            cardinality = int(column["cardinality"])
            codes = X_calibration[:, index].astype(int)
            for level in range(cardinality):
                blocks.append((codes == level).astype(np.float64))
                provenance.append(
                    {
                        "column_index": index,
                        "kind": "categorical_level",
                        "level": level,
                    }
                )
    basis = np.column_stack(blocks).astype(np.float64)
    return basis, {"numeric_state": numeric_state, "provenance": provenance}


def _transform_basis(
    X: np.ndarray,
    columns: list[dict[str, Any]],
    state: dict[str, Any],
) -> np.ndarray:
    blocks: list[np.ndarray] = []
    for column in columns:
        index = int(column["index"])
        if column["kind"] == "numeric":
            numeric = state["numeric_state"][str(index)]
            blocks.append(
                (X[:, index] - float(numeric["center"])) / float(numeric["scale"])
            )
        else:
            cardinality = int(column["cardinality"])
            codes = X[:, index].astype(int)
            for level in range(cardinality):
                blocks.append((codes == level).astype(np.float64))
    return np.column_stack(blocks).astype(np.float64)


def _tree_values(
    parents: np.ndarray,
    *,
    split_positions: list[int],
    thresholds: list[float],
    leaves: list[float],
    depth: int,
) -> np.ndarray:
    path = np.zeros(len(parents), dtype=np.int64)
    for level in range(depth):
        offset = (1 << level) - 1
        node_index = offset + path
        positions = np.asarray(split_positions, dtype=np.int64)[node_index]
        cuts = np.asarray(thresholds, dtype=np.float64)[node_index]
        decision = parents[np.arange(len(parents)), positions] > cuts
        path = 2 * path + decision.astype(np.int64)
    return np.asarray(leaves, dtype=np.float64)[path]


def _evaluate_node_raw(node: dict[str, Any], parents: np.ndarray) -> np.ndarray:
    op = str(node["op"])
    if op == "linear":
        return parents @ np.asarray(node["weights"], dtype=np.float64) + float(
            node["bias"]
        )
    if op == "mlp":
        hidden = np.tanh(
            parents @ np.asarray(node["weights_in"], dtype=np.float64)
            + np.asarray(node["bias_hidden"], dtype=np.float64)
        )
        return hidden @ np.asarray(node["weights_out"], dtype=np.float64) + float(
            node["bias_out"]
        )
    if op == "tree":
        return _tree_values(
            parents,
            split_positions=[int(value) for value in node["split_positions"]],
            thresholds=[float(value) for value in node["thresholds"]],
            leaves=[float(value) for value in node["leaves"]],
            depth=int(node["depth"]),
        )
    raise ValueError(f"unknown sandbox generator op {op!r}")


def _normalize_node(values: np.ndarray, node: dict[str, Any]) -> np.ndarray:
    return (values - float(node["normalization"]["center"])) / float(
        node["normalization"]["scale"]
    )


def _make_node(
    op: str,
    node_id: str,
    parents: list[str],
    parent_values: np.ndarray,
    rng: np.random.Generator,
    *,
    min_tree_depth: int = 1,
) -> tuple[dict[str, Any], np.ndarray]:
    width = parent_values.shape[1]
    node: dict[str, Any] = {"id": node_id, "op": op, "parents": parents}
    if op == "linear":
        node.update(
            {
                "weights": (rng.normal(size=width) / np.sqrt(max(width, 1))).tolist(),
                "bias": float(rng.normal(scale=0.25)),
            }
        )
    elif op == "mlp":
        hidden_width = int(rng.choice((4, 8, 16)))
        node.update(
            {
                "hidden_width": hidden_width,
                "weights_in": (
                    rng.normal(size=(width, hidden_width)) / np.sqrt(max(width, 1))
                ).tolist(),
                "bias_hidden": rng.normal(scale=0.3, size=hidden_width).tolist(),
                "weights_out": (
                    rng.normal(size=hidden_width) / np.sqrt(hidden_width)
                ).tolist(),
                "bias_out": float(rng.normal(scale=0.2)),
                "activation": "tanh",
            }
        )
    elif op == "tree":
        if min_tree_depth not in (1, 2, 3, 4):
            raise ValueError("min_tree_depth must be in {1, 2, 3, 4}")
        unique_parent_rows = len(np.unique(parent_values, axis=0))
        max_tree_depth = min(4, int(np.floor(np.log2(unique_parent_rows))))
        if max_tree_depth < min_tree_depth:
            raise ValueError("tree parents cannot realize the minimum depth")
        requested_depth = int(
            rng.choice(tuple(range(min_tree_depth, max_tree_depth + 1)))
        )

        def build_splits(depth: int) -> tuple[list[int], list[float]]:
            # Fit every split on the calibration rows that actually reach that
            # node. Global thresholds can make most deep leaves empty, which
            # makes high-information multiclass strata unreachable.
            positions: list[int] = []
            cuts: list[float] = []
            active_rows = [np.arange(len(parent_values), dtype=np.int64)]
            for _level in range(depth):
                next_rows: list[np.ndarray] = []
                for rows in active_rows:
                    chosen: tuple[int, float, np.ndarray, np.ndarray] | None = None
                    for position in rng.permutation(width):
                        values = parent_values[rows, int(position)]
                        ordered = np.sort(values)
                        boundaries = np.flatnonzero(np.diff(ordered) > 1e-12) + 1
                        minimum_child = max(1, int(np.ceil(0.15 * len(rows))))
                        boundaries = boundaries[
                            (boundaries >= minimum_child)
                            & (boundaries <= len(rows) - minimum_child)
                        ]
                        if not len(boundaries):
                            continue
                        target_rank = int(
                            round(float(rng.uniform(0.35, 0.65)) * len(rows))
                        )
                        rank = int(
                            boundaries[np.argmin(np.abs(boundaries - target_rank))]
                        )
                        threshold = 0.5 * (
                            float(ordered[rank - 1]) + float(ordered[rank])
                        )
                        right_mask = values > threshold
                        chosen = (
                            int(position),
                            threshold,
                            rows[~right_mask],
                            rows[right_mask],
                        )
                        break
                    if chosen is None:
                        raise ValueError("tree depth is not realizable")
                    position, threshold, left_rows, right_rows = chosen
                    positions.append(position)
                    cuts.append(threshold)
                    next_rows.extend((left_rows, right_rows))
                active_rows = next_rows
            return positions, cuts

        for depth in range(requested_depth, min_tree_depth - 1, -1):
            try:
                split_positions, thresholds = build_splits(depth)
            except ValueError:
                continue
            break
        else:
            raise ValueError("tree node cannot realize its requested depth")
        node.update(
            {
                "depth": depth,
                "split_positions": split_positions,
                "thresholds": thresholds,
                "leaves": rng.normal(size=1 << depth).tolist(),
            }
        )
    else:
        raise ValueError(f"unknown node op {op!r}")

    raw = _evaluate_node_raw(node, parent_values)
    center = float(np.mean(raw))
    scale = float(np.std(raw))
    if not np.isfinite(scale) or scale < 1e-6:
        raise ValueError(f"degenerate {op} generator node")
    node["normalization"] = {"center": center, "scale": scale}
    return node, _normalize_node(raw, node)


def _execute_hidden_dag(
    basis: np.ndarray,
    nodes: list[dict[str, Any]],
) -> dict[str, np.ndarray]:
    values: dict[str, np.ndarray] = {
        f"b{index}": basis[:, index] for index in range(basis.shape[1])
    }
    for node in nodes:
        if node["op"] == "class_logits":
            continue
        parents = np.column_stack([values[parent] for parent in node["parents"]])
        values[node["id"]] = _normalize_node(_evaluate_node_raw(node, parents), node)
    return values


def _logits_from_values(
    values: dict[str, np.ndarray], head: dict[str, Any]
) -> np.ndarray:
    parents = np.column_stack([values[parent] for parent in head["parents"]])
    raw = parents @ np.asarray(head["weights"], dtype=np.float64)
    raw += np.asarray(head["bias"], dtype=np.float64)
    return (raw - np.asarray(head["normalization"]["center"])) / np.asarray(
        head["normalization"]["scale"]
    )


def _sample_labels(probabilities: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    cumulative = np.cumsum(probabilities, axis=1)
    draws = rng.random(len(probabilities))
    labels = np.sum(draws[:, None] > cumulative, axis=1)
    return np.minimum(labels, probabilities.shape[1] - 1).astype(np.int64)


def _stratified_indices(
    labels: np.ndarray,
    *,
    n_query: int,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray]:
    """Deterministically allocate an exact, class-stratified outer split."""

    labels = np.asarray(labels, dtype=np.int64)
    n_classes = int(labels.max()) + 1
    counts = np.bincount(labels, minlength=n_classes)
    if int(counts.min()) < 20:
        raise ValueError("insufficient total class coverage")
    target = counts * (n_query / len(labels))
    query_counts = np.floor(target).astype(int)
    query_counts = np.maximum(query_counts, 5)
    query_counts = np.minimum(query_counts, counts - 15)
    fractional_order = np.argsort(-(target - np.floor(target)), kind="stable")
    while int(query_counts.sum()) < n_query:
        changed = False
        for class_index in fractional_order:
            if query_counts[class_index] < counts[class_index] - 15:
                query_counts[class_index] += 1
                changed = True
                if int(query_counts.sum()) == n_query:
                    break
        if not changed:
            raise ValueError("cannot allocate requested stratified query size")
    while int(query_counts.sum()) > n_query:
        changed = False
        for class_index in fractional_order[::-1]:
            if query_counts[class_index] > 5:
                query_counts[class_index] -= 1
                changed = True
                if int(query_counts.sum()) == n_query:
                    break
        if not changed:
            raise ValueError("cannot reduce stratified query allocation")

    context_parts: list[np.ndarray] = []
    query_parts: list[np.ndarray] = []
    for class_index, class_query_count in enumerate(query_counts):
        class_indices = np.flatnonzero(labels == class_index)
        class_indices = rng.permutation(class_indices)
        query_parts.append(class_indices[:class_query_count])
        context_parts.append(class_indices[class_query_count:])
    context = rng.permutation(np.concatenate(context_parts)).astype(np.int64)
    query = rng.permutation(np.concatenate(query_parts)).astype(np.int64)
    return context, query


def _generate_task(
    family_index: int,
    node_index: int,
    class_index: int,
    quality_index: int,
    replica: int,
    *,
    tasks_per_primary_stratum: int,
    master_seed: int,
    attempt: int,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    family = FAMILIES[family_index]
    n_nodes = int(NODE_COUNT_CHOICES[node_index])
    n_classes = int(CLASS_COUNT_CHOICES[class_index])
    target_quality = float(ORACLE_QUALITY_TARGETS[quality_index])
    task_id = (
        f"sandbox_{family}_n{n_nodes:02d}_k{n_classes:02d}_"
        f"q{int(round(100 * target_quality)):02d}_r{replica:04d}"
    )
    latin = _latin_values(
        master_seed,
        family_index,
        node_index,
        class_index,
        quality_index,
        replica,
        tasks_per_primary_stratum,
    )
    n_rows = int(_choice(ROW_CHOICES, float(latin[0])))
    n_features = int(_choice(FEATURE_CHOICES, float(latin[1])))
    categorical_fraction = float(_choice(CATEGORICAL_FRACTIONS, float(latin[2])))
    max_cardinality = int(_choice(MAX_CARDINALITY_CHOICES, float(latin[3])))
    eligible_feature_fraction = float(
        _choice(ELIGIBLE_FEATURE_FRACTIONS, float(latin[4]))
    )
    n_context = int(round(0.75 * n_rows))
    n_query = n_rows - n_context
    n_calibration = 2048

    raw_rng = _rng(
        master_seed,
        family_index,
        node_index,
        class_index,
        quality_index,
        replica,
        attempt,
        1,
    )
    structure_rng = _rng(
        master_seed,
        family_index,
        node_index,
        class_index,
        quality_index,
        replica,
        attempt,
        2,
    )
    label_rng = _rng(
        master_seed,
        family_index,
        node_index,
        class_index,
        quality_index,
        replica,
        attempt,
        3,
    )
    split_rng = _rng(
        master_seed,
        family_index,
        node_index,
        class_index,
        quality_index,
        replica,
        attempt,
        4,
    )
    X_all, columns, raw_metadata = _raw_table(
        n_calibration + n_rows,
        n_features=n_features,
        categorical_fraction=categorical_fraction,
        max_cardinality=max_cardinality,
        rng=raw_rng,
    )
    X_calibration = X_all[:n_calibration]
    X = X_all[n_calibration:]
    basis_calibration, basis_state = _fit_basis(X_calibration, columns)
    basis = _transform_basis(X, columns, basis_state)

    raw_feature_indices = structure_rng.choice(
        n_features,
        size=max(2, int(round(eligible_feature_fraction * n_features))),
        replace=False,
    )
    eligible_columns = {int(value) for value in raw_feature_indices}
    numeric_columns = [
        int(column["index"]) for column in columns if column["kind"] == "numeric"
    ]
    if not eligible_columns.intersection(numeric_columns):
        eligible_columns.remove(max(eligible_columns))
        eligible_columns.add(int(structure_rng.choice(numeric_columns)))
    basis_refs = [
        f"b{index}"
        for index, source in enumerate(basis_state["provenance"])
        if int(source["column_index"]) in eligible_columns
    ]
    numeric_basis_refs = [
        f"b{index}"
        for index, source in enumerate(basis_state["provenance"])
        if source["kind"] == "numeric"
        and int(source["column_index"]) in eligible_columns
    ]
    if len(basis_refs) < 2:
        raise ValueError("sandbox task has fewer than two informative basis channels")

    calibration_values: dict[str, np.ndarray] = {
        f"b{index}": basis_calibration[:, index]
        for index in range(basis_calibration.shape[1])
    }
    hidden_nodes: list[dict[str, Any]] = []
    hidden_count = n_nodes - 1
    mixed_ops = ["tree", "mlp", "linear"]
    structure_rng.shuffle(mixed_ops)
    for node_index in range(hidden_count):
        node_id = f"n{node_index}"
        if family == "mixed":
            if hidden_count == 1:
                # Together with the linear class-logit head this still gives
                # two genuinely different mechanisms.
                op = str(structure_rng.choice(("tree", "mlp")))
            else:
                op = mixed_ops[node_index % len(mixed_ops)]
        else:
            op = family
        candidates = basis_refs + [node["id"] for node in hidden_nodes]
        minimum_parents = 2 if node_index == 0 else 1
        parent_count = int(
            structure_rng.integers(minimum_parents, min(4, len(candidates)) + 1)
        )
        selected = [
            str(value)
            for value in structure_rng.choice(
                candidates, size=parent_count, replace=False
            )
        ]
        if hidden_nodes and hidden_nodes[-1]["id"] not in selected:
            selected[-1] = hidden_nodes[-1]["id"]
        if (
            hidden_count == 1
            and n_classes > 2
            and op == "tree"
            and not set(selected).intersection(numeric_basis_refs)
        ):
            selected[-1] = str(structure_rng.choice(numeric_basis_refs))
        # Stable de-duplication after forcing the chain parent.
        selected = list(dict.fromkeys(selected))
        parent_values = np.column_stack(
            [calibration_values[parent] for parent in selected]
        )
        node, output = _make_node(
            op,
            node_id,
            selected,
            parent_values,
            structure_rng,
            # With one scalar hidden node, fewer than 16 tree leaves cannot
            # robustly realize five balanced high-information classes. Keep
            # the declared two-node DAG, but give its single tree block enough
            # internal states for the requested multiclass strata.
            min_tree_depth=(
                4 if hidden_count == 1 and n_classes > 2 and op == "tree" else 1
            ),
        )
        hidden_nodes.append(node)
        calibration_values[node_id] = output

    head_parents = [node["id"] for node in hidden_nodes]
    head_input = np.column_stack(
        [calibration_values[parent] for parent in head_parents]
    )
    if len(head_parents) == 1 and n_classes > 2:
        # Random one-dimensional multiclass slopes often leave middle classes
        # dominated for every input. Ordered slopes let calibration allocate a
        # non-empty interval to each class; a later random class permutation
        # removes any label-order convention.
        head_weights = np.linspace(-2.0, 2.0, n_classes, dtype=np.float64)[None, :]
    else:
        head_weights = structure_rng.normal(
            size=(len(head_parents), n_classes)
        ) / np.sqrt(len(head_parents))
    head_bias = structure_rng.normal(scale=0.15, size=n_classes)
    raw_logits = head_input @ head_weights + head_bias
    # One global normalization preserves relative class slopes.  Per-class
    # normalization would collapse a one-parent multiclass head to at most two
    # distinct curves (sign(w_k) * z), making requested difficulty unreachable.
    logit_center = float(np.mean(raw_logits))
    logit_scale = float(np.std(raw_logits))
    if not np.isfinite(logit_scale) or logit_scale < 1e-6:
        raise ValueError("degenerate class-logit head")
    calibration_logits = (raw_logits - logit_center) / logit_scale
    (
        probability_scale,
        class_bias,
        calibration_probabilities,
        realized_quality,
    ) = _calibrate_logits(calibration_logits, target_quality)
    marginal_error = float(
        np.max(np.abs(calibration_probabilities.mean(axis=0) - 1.0 / n_classes))
    )
    if abs(realized_quality - target_quality) > ORACLE_QUALITY_TOLERANCE:
        raise ValueError(
            "requested oracle quality is not attainable: "
            f"target={target_quality:.6f}, realized={realized_quality:.6f}"
        )
    if marginal_error > CLASS_MARGINAL_TOLERANCE:
        raise ValueError(
            f"calibration class marginal is not balanced: error={marginal_error:.6f}"
        )
    minimum_class_probability_std = float(
        np.min(np.std(calibration_probabilities, axis=0))
    )
    if minimum_class_probability_std < MIN_CLASS_PROBABILITY_STD:
        raise ValueError("a class probability is effectively input-independent")
    class_permutation = structure_rng.permutation(n_classes)
    head = {
        "id": "class_logits",
        "op": "class_logits",
        "parents": head_parents,
        "weights": head_weights.tolist(),
        "bias": head_bias.tolist(),
        "normalization": {
            "center": logit_center,
            "scale": logit_scale,
        },
        "probability_scale": probability_scale,
        "class_bias": class_bias.tolist(),
        "class_permutation": class_permutation.astype(int).tolist(),
    }
    nodes = hidden_nodes + [head]

    directly_used_basis = {
        str(parent)
        for node in hidden_nodes
        for parent in node["parents"]
        if str(parent).startswith("b")
    }
    used_input_columns = sorted(
        {
            int(basis_state["provenance"][int(parent[1:])]["column_index"])
            for parent in directly_used_basis
        }
    )

    actual_values = _execute_hidden_dag(basis, hidden_nodes)
    logits = _logits_from_values(actual_values, head)
    probabilities = _softmax(probability_scale * logits + class_bias)
    probabilities = probabilities[:, class_permutation]
    labels = _sample_labels(probabilities, label_rng)
    context_indices, query_indices = _stratified_indices(
        labels, n_query=n_query, rng=split_rng
    )
    y_context = labels[context_indices]
    y_query = labels[query_indices]
    context_counts = np.bincount(y_context, minlength=n_classes)
    query_counts = np.bincount(y_query, minlength=n_classes)
    if int(context_counts.min()) < 15 or int(query_counts.min()) < 5:
        raise ValueError("insufficient class coverage")
    for column in columns:
        if column["kind"] != "categorical":
            continue
        index = int(column["index"])
        context_values = X[context_indices, index].astype(int)
        query_values = X[query_indices, index].astype(int)
        if np.bincount(context_values, minlength=int(column["cardinality"])).min() < 5:
            raise ValueError("categorical level has insufficient context support")
        if not set(query_values) <= set(context_values):
            raise ValueError("query contains an unseen categorical level")

    task_type = tabular_data.BINCLASS if n_classes == 2 else tabular_data.MULTICLASS
    generator = {
        "generator_version": GENERATOR_VERSION,
        "family": family,
        "node_count_semantics": "composition_blocks_including_class_logits",
        "nodes": nodes,
        "output_node": "class_logits",
        "node_count": n_nodes,
        "raw_distribution": raw_metadata,
        "basis_state": basis_state,
        # "Eligible" is deliberately not called "informative": a compact
        # 2--8 node graph may consume only a subset of this candidate pool.
        "eligible_feature_fraction": eligible_feature_fraction,
        "eligible_input_column_indices": sorted(eligible_columns),
        "used_input_column_indices": used_input_columns,
        "requested_oracle_quality": target_quality,
        "realized_calibration_oracle_quality": realized_quality,
        "calibration_class_marginal_max_error": marginal_error,
        "minimum_calibration_class_probability_std": minimum_class_probability_std,
        "realized_context_oracle_quality": _oracle_quality(
            probabilities[context_indices]
        ),
        "realized_query_oracle_quality": _oracle_quality(probabilities[query_indices]),
        "calibration_row_count": n_calibration,
        "latin_cell": latin.tolist(),
    }
    arrays = {
        "X_context": X[context_indices].astype(np.float64),
        "y_context": y_context.astype(np.int64),
        "X_query": X[query_indices].astype(np.float64),
        "y_query": y_query.astype(np.int64),
    }
    metadata: dict[str, Any] = {
        "schema_version": BANK_SCHEMA_VERSION,
        "task_id": task_id,
        "family": family,
        "family_index": family_index,
        "primary_stratum": {
            "family": family,
            "generator_dag_nodes": n_nodes,
            "n_classes": n_classes,
            "oracle_quality_target": target_quality,
        },
        "primary_stratum_id": (
            f"{family}/n{n_nodes:02d}/k{n_classes:02d}/"
            f"q{int(round(100 * target_quality)):02d}"
        ),
        "replica": replica,
        "tasks_per_primary_stratum": tasks_per_primary_stratum,
        "meta_split": _meta_split(
            master_seed,
            family_index,
            node_index,
            class_index,
            quality_index,
            replica,
            tasks_per_primary_stratum,
        ),
        "attempt": attempt,
        "master_seed": master_seed,
        "n_rows": n_rows,
        "n_context": n_context,
        "n_query": n_query,
        "n_features": n_features,
        "generator_dag_nodes": n_nodes,
        "categorical_fraction_requested": categorical_fraction,
        "categorical_fraction_realized": raw_metadata["n_categorical"] / n_features,
        "max_categorical_cardinality": max_cardinality,
        "task_type": task_type,
        "n_classes": n_classes,
        "oracle_quality_target": target_quality,
        "columns": columns,
        "generator": generator,
        "class_counts_context": context_counts.astype(int).tolist(),
        "class_counts_query": query_counts.astype(int).tolist(),
    }
    metadata["generator_checksum"] = _hash_payload(generator)
    metadata["content_checksum"] = _content_checksum(
        columns=columns, generator=generator, arrays=arrays
    )
    metadata["task_checksum"] = _task_checksum(metadata, arrays)
    return metadata, arrays


def _task_specs(tasks_per_primary_stratum: int) -> list[tuple[int, int, int, int, int]]:
    return [
        (family_index, node_index, class_index, quality_index, replica)
        for family_index in range(len(FAMILIES))
        for node_index in range(len(NODE_COUNT_CHOICES))
        for class_index in range(len(CLASS_COUNT_CHOICES))
        for quality_index in range(len(ORACLE_QUALITY_TARGETS))
        for replica in range(tasks_per_primary_stratum)
    ]


def _generate_task_with_retries(
    job: tuple[tuple[int, int, int, int, int], int, int],
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    spec, master_seed, tasks_per_primary_stratum = job
    family_index, node_index, class_index, quality_index, replica = spec
    for attempt in range(50):
        try:
            return _generate_task(
                family_index,
                node_index,
                class_index,
                quality_index,
                replica,
                tasks_per_primary_stratum=tasks_per_primary_stratum,
                master_seed=master_seed,
                attempt=attempt,
            )
        except ValueError:
            continue
    family = FAMILIES[family_index]
    raise RuntimeError(
        "failed to generate "
        f"{family}/n{NODE_COUNT_CHOICES[node_index]}/"
        f"k{CLASS_COUNT_CHOICES[class_index]}/"
        f"q{ORACLE_QUALITY_TARGETS[quality_index]}/r{replica}"
    )


def _parallel_generated_tasks(
    jobs: list[tuple[tuple[int, int, int, int, int], int, int]],
    workers: int,
) -> Iterator[tuple[dict[str, Any], dict[str, np.ndarray]]]:
    """Generate in parallel with bounded result buffering and stable ordering."""

    if workers == 1:
        for job in jobs:
            yield _generate_task_with_retries(job)
        return
    buffer_limit = 2 * workers
    with ProcessPoolExecutor(max_workers=workers) as executor:
        job_iter = iter(enumerate(jobs))
        pending: dict[Any, int] = {}
        ready: dict[int, tuple[dict[str, Any], dict[str, np.ndarray]]] = {}
        for _ in range(min(len(jobs), buffer_limit)):
            index, job = next(job_iter)
            pending[executor.submit(_generate_task_with_retries, job)] = index
        next_index = 0
        jobs_exhausted = not pending
        while pending or ready:
            while next_index in ready:
                yield ready.pop(next_index)
                next_index += 1
                if not jobs_exhausted:
                    try:
                        replacement_index, replacement_job = next(job_iter)
                    except StopIteration:
                        jobs_exhausted = True
                    else:
                        pending[
                            executor.submit(
                                _generate_task_with_retries, replacement_job
                            )
                        ] = replacement_index
            if not pending:
                if ready:
                    raise RuntimeError("parallel generator lost stable task order")
                break
            completed, _ = wait(pending, return_when=FIRST_COMPLETED)
            for future in completed:
                index = pending.pop(future)
                ready[index] = future.result()
            if len(pending) + len(ready) > buffer_limit:
                raise RuntimeError("parallel generator exceeded its result buffer")


def _manifest_record(metadata: dict[str, Any]) -> dict[str, Any]:
    task_id = str(metadata["task_id"])
    return {
        "task_id": task_id,
        "family": metadata["family"],
        "primary_stratum_id": metadata["primary_stratum_id"],
        "generator_dag_nodes": metadata["generator"]["node_count"],
        "oracle_quality_target": metadata["generator"]["requested_oracle_quality"],
        "meta_split": metadata["meta_split"],
        "task_dir": f"tasks/{task_id}",
        "n_rows": metadata["n_rows"],
        "n_context": metadata["n_context"],
        "n_query": metadata["n_query"],
        "n_features": metadata["n_features"],
        "n_classes": metadata["n_classes"],
        "task_type": metadata["task_type"],
        "generator_checksum": metadata["generator_checksum"],
        "content_checksum": metadata["content_checksum"],
        "task_checksum": metadata["task_checksum"],
    }


def generate_sandbox_bank(
    output_dir: str | Path,
    *,
    master_seed: int = DEFAULT_MASTER_SEED,
    tasks_per_primary_stratum: int = PILOT_TASKS_PER_PRIMARY_STRATUM,
    workers: int = 1,
) -> dict[str, Any]:
    """Freeze a balanced restricted bank, refusing to overwrite existing data."""

    if tasks_per_primary_stratum <= 0 or tasks_per_primary_stratum % 5:
        raise ValueError("tasks_per_primary_stratum must be a positive multiple of 5")
    if workers <= 0:
        raise ValueError("workers must be positive")
    root = Path(output_dir).expanduser().resolve()
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty sandbox bank: {root}")
    root.mkdir(parents=True, exist_ok=True)
    tasks_root = root / "tasks"
    tasks_root.mkdir()

    specs = _task_specs(tasks_per_primary_stratum)
    jobs = [(spec, master_seed, tasks_per_primary_stratum) for spec in specs]
    records: list[dict[str, Any]] = []
    seen_content: set[str] = set()
    for metadata, arrays in _parallel_generated_tasks(jobs, workers):
        content_checksum = str(metadata["content_checksum"])
        if content_checksum in seen_content:
            raise RuntimeError(
                f"duplicate generated content for task {metadata['task_id']}"
            )
        seen_content.add(content_checksum)
        task_id = str(metadata["task_id"])
        task_dir = tasks_root / task_id
        task_dir.mkdir()
        np.savez_compressed(task_dir / "data.npz", **arrays)
        (task_dir / "task.json").write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n"
        )
        records.append(_manifest_record(metadata))

    task_count = PRIMARY_STRATUM_COUNT * tasks_per_primary_stratum
    tasks_per_family = task_count // len(FAMILIES)
    manifest: dict[str, Any] = {
        "schema_version": BANK_SCHEMA_VERSION,
        "bank_kind": "tab_wpf_sandbox_classification",
        "generator_version": GENERATOR_VERSION,
        "node_count_semantics": "composition_blocks_including_class_logits",
        "generator_source_sha256": _source_sha256(),
        "master_seed": master_seed,
        "task_count": len(records),
        "families": list(FAMILIES),
        "primary_stratum_axes": [
            "family",
            "generator_dag_nodes",
            "n_classes",
            "oracle_quality_target",
        ],
        "primary_stratum_count": PRIMARY_STRATUM_COUNT,
        "tasks_per_primary_stratum": tasks_per_primary_stratum,
        "tasks_per_family": tasks_per_family,
        "split_counts": {
            split: sum(record["meta_split"] == split for record in records)
            for split in META_SPLITS
        },
        "family_counts": {
            family: sum(record["family"] == family for record in records)
            for family in FAMILIES
        },
        "parameter_support": {
            "n_rows": list(ROW_CHOICES),
            "n_features": list(FEATURE_CHOICES),
            "categorical_fraction": list(CATEGORICAL_FRACTIONS),
            "max_categorical_cardinality": list(MAX_CARDINALITY_CHOICES),
            "n_classes": list(CLASS_COUNT_CHOICES),
            "generator_dag_nodes": list(NODE_COUNT_CHOICES),
            "eligible_feature_fraction": list(ELIGIBLE_FEATURE_FRACTIONS),
            "oracle_quality_target": list(ORACLE_QUALITY_TARGETS),
        },
        "generation_environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "workers": workers,
        },
        "tasks": records,
    }
    manifest["bank_checksum"] = _hash_payload(
        {
            key: value
            for key, value in manifest.items()
            if key != "generation_environment"
        }
    )
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    verify_sandbox_bank(root)
    return manifest


@cache
def _load_manifest_cached(resolved_dir: str) -> dict[str, Any]:
    path = Path(resolved_dir) / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"sandbox manifest not found: {path}")
    manifest = json.loads(path.read_text())
    if manifest.get("schema_version") != BANK_SCHEMA_VERSION:
        raise ValueError("unsupported sandbox bank schema")
    checksum = _hash_payload(
        {
            key: value
            for key, value in manifest.items()
            if key not in {"bank_checksum", "generation_environment"}
        }
    )
    if checksum != manifest.get("bank_checksum"):
        raise ValueError("sandbox manifest checksum mismatch")
    if manifest.get("generator_version") != GENERATOR_VERSION:
        raise ValueError("sandbox generator version does not match this checkout")
    if manifest.get("generator_source_sha256") != _source_sha256():
        raise ValueError("sandbox bank was produced by a different generator source")
    return manifest


def load_sandbox_manifest(bank_dir: str | Path) -> dict[str, Any]:
    return _load_manifest_cached(str(Path(bank_dir).expanduser().resolve()))


def _column_spec(payload: dict[str, Any]) -> tabular_data.ColumnSpec:
    vocabulary = payload.get("vocabulary")
    return tabular_data.ColumnSpec(
        index=int(payload["index"]),
        kind=str(payload["kind"]),
        cardinality=(
            None if payload.get("cardinality") is None else int(payload["cardinality"])
        ),
        vocabulary=None if vocabulary is None else tuple(str(v) for v in vocabulary),
    )


@cache
def _load_task_cached(
    root: str,
    task_id: str,
    relative_dir: str,
    task_checksum: str,
    content_checksum: str,
    verify_checksum: bool,
) -> SandboxTask:
    task_dir = Path(root) / relative_dir
    metadata = json.loads((task_dir / "task.json").read_text())
    with np.load(task_dir / "data.npz", allow_pickle=False) as stored:
        arrays = {name: np.asarray(stored[name]) for name in stored.files}
    required = {"X_context", "y_context", "X_query", "y_query"}
    if set(arrays) != required:
        raise ValueError(f"task {task_id}: unexpected arrays {sorted(arrays)}")
    if verify_checksum:
        computed_task_checksum = _task_checksum(metadata, arrays)
        if metadata.get("task_checksum") != task_checksum:
            raise ValueError(f"task {task_id}: self checksum mismatch")
        if computed_task_checksum != task_checksum:
            raise ValueError(f"task {task_id}: checksum mismatch")
        computed_content = _content_checksum(
            columns=list(metadata["columns"]),
            generator=dict(metadata["generator"]),
            arrays=arrays,
        )
        if metadata.get("content_checksum") != content_checksum:
            raise ValueError(f"task {task_id}: self content checksum mismatch")
        if computed_content != content_checksum:
            raise ValueError(f"task {task_id}: content checksum mismatch")
    for array in arrays.values():
        array.setflags(write=False)
    return SandboxTask(
        task_id=str(metadata["task_id"]),
        family=str(metadata["family"]),
        meta_split=str(metadata["meta_split"]),
        task_type=str(metadata["task_type"]),
        n_classes=int(metadata["n_classes"]),
        columns=tuple(_column_spec(column) for column in metadata["columns"]),
        X_context=arrays["X_context"],
        y_context=arrays["y_context"],
        X_query=arrays["X_query"],
        y_query=arrays["y_query"],
        metadata=metadata,
    )


def load_sandbox_task(
    bank_dir: str | Path,
    record_or_id: dict[str, Any] | str,
    *,
    verify_checksum: bool = True,
) -> SandboxTask:
    root = Path(bank_dir).expanduser().resolve()
    manifest = load_sandbox_manifest(root)
    if isinstance(record_or_id, str):
        matches = [
            record for record in manifest["tasks"] if record["task_id"] == record_or_id
        ]
        if len(matches) != 1:
            raise KeyError(f"unknown sandbox task {record_or_id!r}")
        record = matches[0]
    else:
        record = record_or_id
    return _load_task_cached(
        str(root),
        str(record["task_id"]),
        str(record["task_dir"]),
        str(record["task_checksum"]),
        str(record["content_checksum"]),
        verify_checksum,
    )


def iter_sandbox_tasks(
    bank_dir: str | Path,
    *,
    meta_split: str,
    verify_checksum: bool = True,
    sample_size: int | None = None,
    sample_seed: int = 0,
) -> Iterator[SandboxTask]:
    if meta_split not in META_SPLITS:
        raise ValueError(f"unknown meta split {meta_split!r}")
    if sample_size is None:
        manifest = load_sandbox_manifest(bank_dir)
        records = [
            record for record in manifest["tasks"] if record["meta_split"] == meta_split
        ]
    else:
        records = sample_sandbox_records(
            bank_dir,
            meta_split=meta_split,
            sample_size=sample_size,
            sample_seed=sample_seed,
        )
    for record in records:
        yield load_sandbox_task(bank_dir, record, verify_checksum=verify_checksum)


def sample_sandbox_records(
    bank_dir: str | Path,
    *,
    meta_split: str,
    sample_size: int,
    sample_seed: int,
) -> list[dict[str, Any]]:
    """Return a deterministic, family-balanced rotating cohort.

    Primary strata are visited at most once before a second task is selected
    from any stratum.  Family orders are interleaved, so cohort counts differ
    by at most one across the four mechanism families.
    """

    if meta_split not in META_SPLITS:
        raise ValueError(f"unknown meta split {meta_split!r}")
    manifest = load_sandbox_manifest(bank_dir)
    available = [
        record for record in manifest["tasks"] if record["meta_split"] == meta_split
    ]
    if not 0 < sample_size <= len(available):
        raise ValueError(
            f"sample_size must be in [1, {len(available)}], got {sample_size}"
        )
    if sample_size % len(FAMILIES):
        raise ValueError(
            f"sample_size must be divisible by {len(FAMILIES)} for family balance"
        )

    by_family: dict[str, dict[str, list[dict[str, Any]]]] = {
        family: {} for family in FAMILIES
    }
    for record in available:
        family = str(record["family"])
        stratum_id = str(record["primary_stratum_id"])
        by_family[family].setdefault(stratum_id, []).append(record)

    family_orders: dict[str, list[str]] = {}
    record_orders: dict[str, list[dict[str, Any]]] = {}
    for family_index, family in enumerate(FAMILIES):
        strata = sorted(by_family[family])
        family_rng = np.random.default_rng(
            np.random.SeedSequence([sample_seed, family_index, 32452843])
        )
        family_orders[family] = [
            strata[index] for index in family_rng.permutation(len(strata))
        ]
        for stratum_index, stratum_id in enumerate(family_orders[family]):
            records = sorted(
                by_family[family][stratum_id], key=lambda record: record["task_id"]
            )
            stratum_rng = np.random.default_rng(
                np.random.SeedSequence(
                    [sample_seed, family_index, stratum_index, 49979687]
                )
            )
            record_orders[stratum_id] = [
                records[index] for index in stratum_rng.permutation(len(records))
            ]

    selected: list[dict[str, Any]] = []
    pass_index = 0
    while len(selected) < sample_size:
        made_progress = False
        strata_per_family = max(len(order) for order in family_orders.values())
        for stratum_position in range(strata_per_family):
            for family in FAMILIES:
                order = family_orders[family]
                if stratum_position >= len(order):
                    continue
                records = record_orders[order[stratum_position]]
                if pass_index >= len(records):
                    continue
                selected.append(records[pass_index])
                made_progress = True
                if len(selected) == sample_size:
                    return selected
        if not made_progress:
            raise RuntimeError("sandbox cohort sampler exhausted records early")
        pass_index += 1
    return selected


def _finite_array(
    value: Any, expected_shape: tuple[int, ...], *, label: str
) -> np.ndarray:
    array = np.asarray(value, dtype=np.float64)
    if array.shape != expected_shape or not np.isfinite(array).all():
        raise ValueError(
            f"{label} must be finite with shape {expected_shape}, got {array.shape}"
        )
    return array


def _verify_generator_structure(task: SandboxTask) -> None:
    """Strictly validate the auditable closed GeneratorDAG representation."""

    generator = task.metadata["generator"]
    if generator.get("generator_version") != GENERATOR_VERSION:
        raise ValueError(f"task {task.task_id}: generator version mismatch")
    if (
        generator.get("node_count_semantics")
        != "composition_blocks_including_class_logits"
    ):
        raise ValueError(f"task {task.task_id}: node-count semantics mismatch")
    if generator.get("family") != task.family:
        raise ValueError(f"task {task.task_id}: generator family mismatch")
    nodes = generator.get("nodes")
    if not isinstance(nodes, list) or len(nodes) != int(generator["node_count"]):
        raise ValueError(f"task {task.task_id}: DAG node count mismatch")
    if int(generator["node_count"]) not in NODE_COUNT_CHOICES:
        raise ValueError(f"task {task.task_id}: DAG size outside support")

    provenance = generator.get("basis_state", {}).get("provenance")
    if not isinstance(provenance, list) or not provenance:
        raise ValueError(f"task {task.task_id}: missing basis provenance")
    for source in provenance:
        column_index = int(source.get("column_index", -1))
        if not 0 <= column_index < len(task.columns):
            raise ValueError(f"task {task.task_id}: invalid basis column index")
        expected_kind = task.columns[column_index].kind
        source_kind = source.get("kind")
        if expected_kind == "numeric" and source_kind != "numeric":
            raise ValueError(f"task {task.task_id}: numeric basis mismatch")
        if expected_kind == "categorical" and source_kind != "categorical_level":
            raise ValueError(f"task {task.task_id}: categorical basis mismatch")
        if source_kind == "categorical_level":
            level = int(source.get("level", -1))
            cardinality = int(task.columns[column_index].cardinality or 0)
            if not 0 <= level < cardinality:
                raise ValueError(
                    f"task {task.task_id}: invalid categorical basis level"
                )

    available = {f"b{index}" for index in range(len(provenance))}
    hidden_nodes = nodes[:-1]
    hidden_ids: list[str] = []
    allowed = {"linear", "tree", "mlp"}
    for node in hidden_nodes:
        node_id = str(node.get("id", ""))
        if not node_id or node_id in available or node_id in hidden_ids:
            raise ValueError(f"task {task.task_id}: duplicate or invalid node id")
        parents = [str(parent) for parent in node.get("parents", [])]
        if not parents or len(parents) != len(set(parents)):
            raise ValueError(f"task {task.task_id}: invalid hidden-node parents")
        if not set(parents) <= available:
            raise ValueError(f"task {task.task_id}: non-topological DAG parent")
        width = len(parents)
        op = str(node.get("op"))
        if op not in allowed:
            raise ValueError(f"task {task.task_id}: operator outside sandbox catalog")
        normalization = node.get("normalization", {})
        center = float(normalization.get("center", np.nan))
        scale = float(normalization.get("scale", np.nan))
        if not np.isfinite(center) or not np.isfinite(scale) or scale <= 0.0:
            raise ValueError(f"task {task.task_id}: invalid node normalization")
        if op == "linear":
            _finite_array(
                node.get("weights"), (width,), label=f"{task.task_id} linear weights"
            )
            if not np.isfinite(float(node.get("bias", np.nan))):
                raise ValueError(f"task {task.task_id}: invalid linear bias")
        elif op == "mlp":
            hidden_width = int(node.get("hidden_width", 0))
            if hidden_width not in (4, 8, 16) or node.get("activation") != "tanh":
                raise ValueError(f"task {task.task_id}: invalid MLP block")
            _finite_array(
                node.get("weights_in"),
                (width, hidden_width),
                label=f"{task.task_id} MLP input weights",
            )
            _finite_array(
                node.get("bias_hidden"),
                (hidden_width,),
                label=f"{task.task_id} MLP hidden bias",
            )
            _finite_array(
                node.get("weights_out"),
                (hidden_width,),
                label=f"{task.task_id} MLP output weights",
            )
            if not np.isfinite(float(node.get("bias_out", np.nan))):
                raise ValueError(f"task {task.task_id}: invalid MLP output bias")
        else:
            depth = int(node.get("depth", 0))
            if depth not in (1, 2, 3, 4):
                raise ValueError(f"task {task.task_id}: invalid tree depth")
            split_count = (1 << depth) - 1
            positions = np.asarray(node.get("split_positions"), dtype=np.int64)
            _finite_array(
                node.get("thresholds"),
                (split_count,),
                label=f"{task.task_id} tree thresholds",
            )
            _finite_array(
                node.get("leaves"),
                (1 << depth,),
                label=f"{task.task_id} tree leaves",
            )
            if (
                positions.shape != (split_count,)
                or np.any(positions < 0)
                or np.any(positions >= width)
            ):
                raise ValueError(f"task {task.task_id}: invalid tree split positions")
        hidden_ids.append(node_id)
        available.add(node_id)

    head = nodes[-1]
    if (
        head.get("id") != "class_logits"
        or head.get("op") != "class_logits"
        or generator.get("output_node") != "class_logits"
    ):
        raise ValueError(f"task {task.task_id}: invalid output node")
    head_parents = [str(parent) for parent in head.get("parents", [])]
    if head_parents != hidden_ids or len(head_parents) != len(set(head_parents)):
        raise ValueError(f"task {task.task_id}: dead or duplicate head parent")
    _finite_array(
        head.get("weights"),
        (len(hidden_ids), task.n_classes),
        label=f"{task.task_id} head weights",
    )
    _finite_array(
        head.get("bias"), (task.n_classes,), label=f"{task.task_id} head bias"
    )
    normalization = head.get("normalization", {})
    head_center = float(normalization.get("center", np.nan))
    head_scale = float(normalization.get("scale", np.nan))
    probability_scale = float(head.get("probability_scale", np.nan))
    if (
        not np.isfinite(head_center)
        or not np.isfinite(head_scale)
        or head_scale <= 0.0
        or not np.isfinite(probability_scale)
        or probability_scale <= 0.0
    ):
        raise ValueError(f"task {task.task_id}: invalid head calibration")
    _finite_array(
        head.get("class_bias"),
        (task.n_classes,),
        label=f"{task.task_id} class bias",
    )
    permutation = [int(value) for value in head.get("class_permutation", [])]
    if sorted(permutation) != list(range(task.n_classes)):
        raise ValueError(f"task {task.task_id}: invalid class permutation")

    target = float(generator.get("requested_oracle_quality", np.nan))
    realized = float(generator.get("realized_calibration_oracle_quality", np.nan))
    marginal_error = float(
        generator.get("calibration_class_marginal_max_error", np.nan)
    )
    if (
        target not in ORACLE_QUALITY_TARGETS
        or abs(realized - target) > ORACLE_QUALITY_TOLERANCE
    ):
        raise ValueError(f"task {task.task_id}: oracle quality calibration mismatch")
    if not np.isfinite(marginal_error) or marginal_error > CLASS_MARGINAL_TOLERANCE:
        raise ValueError(f"task {task.task_id}: class marginal calibration mismatch")
    minimum_class_probability_std = float(
        generator.get("minimum_calibration_class_probability_std", np.nan)
    )
    if (
        not np.isfinite(minimum_class_probability_std)
        or minimum_class_probability_std < MIN_CLASS_PROBABILITY_STD
    ):
        raise ValueError(f"task {task.task_id}: input-independent class probability")

    eligible = {
        int(value) for value in generator.get("eligible_input_column_indices", [])
    }
    used = {int(value) for value in generator.get("used_input_column_indices", [])}
    eligible_fraction = float(generator.get("eligible_feature_fraction", np.nan))
    expected_eligible_count = max(2, int(round(eligible_fraction * len(task.columns))))
    if (
        eligible_fraction not in ELIGIBLE_FEATURE_FRACTIONS
        or len(eligible) != expected_eligible_count
        or not eligible <= set(range(len(task.columns)))
        or not used
        or not used <= eligible
    ):
        raise ValueError(f"task {task.task_id}: invalid eligible/used input audit")


def verify_sandbox_bank(bank_dir: str | Path) -> dict[str, Any]:
    root = Path(bank_dir).expanduser().resolve()
    manifest = load_sandbox_manifest(root)
    if manifest.get("bank_kind") != "tab_wpf_sandbox_classification":
        raise ValueError("unexpected sandbox bank kind")
    if manifest.get("families") != list(FAMILIES):
        raise ValueError("sandbox family catalog mismatch")
    tasks_per_primary_stratum = int(manifest.get("tasks_per_primary_stratum", 0))
    if tasks_per_primary_stratum <= 0 or tasks_per_primary_stratum % 5:
        raise ValueError("sandbox tasks-per-primary-stratum must be a multiple of 5")
    if manifest.get("primary_stratum_count") != PRIMARY_STRATUM_COUNT:
        raise ValueError("sandbox primary-stratum count mismatch")
    if manifest.get("primary_stratum_axes") != [
        "family",
        "generator_dag_nodes",
        "n_classes",
        "oracle_quality_target",
    ]:
        raise ValueError("sandbox primary-stratum axes mismatch")
    expected_task_count = PRIMARY_STRATUM_COUNT * tasks_per_primary_stratum
    expected_tasks_per_family = expected_task_count // len(FAMILIES)
    if manifest.get("tasks_per_family") != expected_tasks_per_family:
        raise ValueError("sandbox tasks-per-family mismatch")
    if (
        manifest.get("node_count_semantics")
        != "composition_blocks_including_class_logits"
    ):
        raise ValueError("sandbox node-count semantics mismatch")
    expected_support = {
        "n_rows": list(ROW_CHOICES),
        "n_features": list(FEATURE_CHOICES),
        "categorical_fraction": list(CATEGORICAL_FRACTIONS),
        "max_categorical_cardinality": list(MAX_CARDINALITY_CHOICES),
        "n_classes": list(CLASS_COUNT_CHOICES),
        "generator_dag_nodes": list(NODE_COUNT_CHOICES),
        "eligible_feature_fraction": list(ELIGIBLE_FEATURE_FRACTIONS),
        "oracle_quality_target": list(ORACLE_QUALITY_TARGETS),
    }
    if manifest.get("parameter_support") != expected_support:
        raise ValueError("sandbox parameter support mismatch")
    if manifest.get("task_count") != expected_task_count:
        raise ValueError(f"sandbox bank must contain {expected_task_count} tasks")
    if (
        not isinstance(manifest.get("tasks"), list)
        or len(manifest["tasks"]) != expected_task_count
    ):
        raise ValueError("sandbox manifest task records are incomplete")
    expected_split_counts = {
        META_TRAIN: 3 * expected_task_count // 5,
        META_VALID: expected_task_count // 5,
        META_TEST: expected_task_count // 5,
    }
    if manifest.get("split_counts") != expected_split_counts:
        raise ValueError("sandbox split must be exactly 60/20/20")
    if manifest.get("family_counts") != {
        family: expected_tasks_per_family for family in FAMILIES
    }:
        raise ValueError("sandbox bank must be exactly family-balanced")

    ids: list[str] = []
    task_checksums: list[str] = []
    content_checksums: list[str] = []
    for family in FAMILIES:
        family_records = [
            record for record in manifest["tasks"] if record["family"] == family
        ]
        counts = {
            split: sum(record["meta_split"] == split for record in family_records)
            for split in META_SPLITS
        }
        expected_family_splits = {
            META_TRAIN: 3 * expected_tasks_per_family // 5,
            META_VALID: expected_tasks_per_family // 5,
            META_TEST: expected_tasks_per_family // 5,
        }
        if counts != expected_family_splits:
            raise ValueError(f"family {family!r} is not split 60/20/20")

    stratum_records: dict[str, list[dict[str, Any]]] = {}
    for record in manifest["tasks"]:
        stratum_records.setdefault(str(record.get("primary_stratum_id")), []).append(
            record
        )
    if len(stratum_records) != PRIMARY_STRATUM_COUNT:
        raise ValueError("sandbox does not cover every primary stratum")
    for stratum_id, records in stratum_records.items():
        if len(records) != tasks_per_primary_stratum:
            raise ValueError(f"stratum {stratum_id!r} has the wrong task count")
        counts = {
            split: sum(record["meta_split"] == split for record in records)
            for split in META_SPLITS
        }
        if counts != {
            META_TRAIN: 3 * tasks_per_primary_stratum // 5,
            META_VALID: tasks_per_primary_stratum // 5,
            META_TEST: tasks_per_primary_stratum // 5,
        }:
            raise ValueError(f"stratum {stratum_id!r} is not split 60/20/20")

    for record in manifest["tasks"]:
        if (
            record.get("family") not in FAMILIES
            or record.get("meta_split") not in META_SPLITS
        ):
            raise ValueError("sandbox task record has invalid family or split")
        expected_relative_dir = f"tasks/{record.get('task_id')}"
        if record.get("task_dir") != expected_relative_dir:
            raise ValueError("sandbox task directory is not canonical")
        task = load_sandbox_task(root, record, verify_checksum=True)
        ids.append(task.task_id)
        task_checksums.append(str(record["task_checksum"]))
        content_checksums.append(str(record["content_checksum"]))
        if task.metadata.get("generator_checksum") != _hash_payload(
            task.metadata.get("generator")
        ):
            raise ValueError(f"task {task.task_id}: generator checksum mismatch")
        if task.metadata.get("master_seed") != manifest.get("master_seed"):
            raise ValueError(f"task {task.task_id}: master seed mismatch")
        if task.metadata.get("tasks_per_primary_stratum") != tasks_per_primary_stratum:
            raise ValueError(f"task {task.task_id}: stratum-size mismatch")
        if not 0 <= int(task.metadata.get("attempt", -1)) < 50:
            raise ValueError(f"task {task.task_id}: invalid generation attempt")
        for key in (
            "task_id",
            "family",
            "primary_stratum_id",
            "meta_split",
            "n_rows",
            "n_context",
            "n_query",
            "n_features",
            "n_classes",
            "generator_dag_nodes",
            "oracle_quality_target",
            "task_type",
            "generator_checksum",
            "content_checksum",
            "task_checksum",
        ):
            if task.metadata.get(key) != record.get(key):
                raise ValueError(
                    f"task {task.task_id}: manifest field {key!r} mismatch"
                )
        if task.metadata["n_rows"] not in ROW_CHOICES:
            raise ValueError(f"task {task.task_id}: n_rows outside sandbox support")
        if (
            task.metadata["n_context"] + task.metadata["n_query"]
            != task.metadata["n_rows"]
        ):
            raise ValueError(f"task {task.task_id}: outer split size mismatch")
        if task.metadata["n_context"] != int(round(0.75 * task.metadata["n_rows"])):
            raise ValueError(f"task {task.task_id}: outer split ratio mismatch")
        if task.metadata["n_features"] not in FEATURE_CHOICES:
            raise ValueError(f"task {task.task_id}: width outside sandbox support")
        if task.n_classes not in CLASS_COUNT_CHOICES:
            raise ValueError(f"task {task.task_id}: class count outside support")
        expected_task_type = (
            tabular_data.BINCLASS if task.n_classes == 2 else tabular_data.MULTICLASS
        )
        if task.task_type != expected_task_type:
            raise ValueError(f"task {task.task_id}: task type/class mismatch")
        if task.metadata["max_categorical_cardinality"] not in MAX_CARDINALITY_CHOICES:
            raise ValueError(f"task {task.task_id}: cardinality outside support")
        if task.metadata["categorical_fraction_requested"] not in CATEGORICAL_FRACTIONS:
            raise ValueError(
                f"task {task.task_id}: categorical fraction outside support"
            )
        generator = task.metadata["generator"]
        _verify_generator_structure(task)
        nodes = generator["nodes"]
        if task.family != "mixed" and any(
            node["op"] != task.family for node in nodes[:-1]
        ):
            raise ValueError(f"task {task.task_id}: family/operator mismatch")
        mechanisms = {str(node["op"]) for node in nodes[:-1]} | {"linear"}
        if task.family == "mixed" and len(mechanisms) < 2:
            raise ValueError(
                f"task {task.task_id}: mixed DAG lacks mechanism diversity"
            )
        if task.X_context.shape != (
            task.metadata["n_context"],
            task.metadata["n_features"],
        ):
            raise ValueError(f"task {task.task_id}: context shape mismatch")
        if task.X_query.shape != (
            task.metadata["n_query"],
            task.metadata["n_features"],
        ):
            raise ValueError(f"task {task.task_id}: query shape mismatch")
        if task.y_context.shape != (
            task.metadata["n_context"],
        ) or task.y_query.shape != (task.metadata["n_query"],):
            raise ValueError(f"task {task.task_id}: label shape mismatch")
        if not np.isfinite(task.X_context).all() or not np.isfinite(task.X_query).all():
            raise ValueError(f"task {task.task_id}: non-finite features")
        if not np.issubdtype(task.y_context.dtype, np.integer) or not np.issubdtype(
            task.y_query.dtype, np.integer
        ):
            raise ValueError(f"task {task.task_id}: labels must be integers")
        if len(task.columns) != task.metadata["n_features"] or [
            column.index for column in task.columns
        ] != list(range(task.metadata["n_features"])):
            raise ValueError(f"task {task.task_id}: invalid column schema indices")
        categorical_count = 0
        realized_cardinalities: list[int] = []
        for column in task.columns:
            if column.kind not in {"numeric", "categorical"}:
                raise ValueError(f"task {task.task_id}: invalid column kind")
            values = np.concatenate(
                [task.X_context[:, column.index], task.X_query[:, column.index]]
            )
            if column.kind == "numeric":
                if column.cardinality is not None or column.vocabulary is not None:
                    raise ValueError(f"task {task.task_id}: invalid numeric schema")
                continue
            categorical_count += 1
            cardinality = int(column.cardinality or 0)
            realized_cardinalities.append(cardinality)
            if (
                not 2 <= cardinality <= task.metadata["max_categorical_cardinality"]
                or column.vocabulary is None
                or len(column.vocabulary) != cardinality
                or not np.array_equal(values, values.astype(int))
                or int(values.min()) < 0
                or int(values.max()) >= cardinality
            ):
                raise ValueError(f"task {task.task_id}: invalid categorical schema")
            context_counts = np.bincount(
                task.X_context[:, column.index].astype(int), minlength=cardinality
            )
            if int(context_counts.min()) < 5:
                raise ValueError(
                    f"task {task.task_id}: insufficient categorical context support"
                )
        realized_fraction = categorical_count / len(task.columns)
        if not np.isclose(
            realized_fraction,
            float(task.metadata["categorical_fraction_realized"]),
        ):
            raise ValueError(f"task {task.task_id}: categorical fraction mismatch")
        if categorical_count and max(realized_cardinalities) != int(
            task.metadata["max_categorical_cardinality"]
        ):
            raise ValueError(
                f"task {task.task_id}: requested cardinality cap unrealized"
            )
        for labels, minimum in ((task.y_context, 15), (task.y_query, 5)):
            counts = np.bincount(labels.astype(int), minlength=task.n_classes)
            if len(counts) != task.n_classes or int(counts.min()) < minimum:
                raise ValueError(f"task {task.task_id}: insufficient class coverage")
        if (
            task.metadata.get("class_counts_context")
            != np.bincount(task.y_context, minlength=task.n_classes)
            .astype(int)
            .tolist()
            or task.metadata.get("class_counts_query")
            != np.bincount(task.y_query, minlength=task.n_classes).astype(int).tolist()
        ):
            raise ValueError(f"task {task.task_id}: class-count audit mismatch")
        for column in task.columns:
            if column.kind != "categorical":
                continue
            if not set(task.X_query[:, column.index].astype(int)) <= set(
                task.X_context[:, column.index].astype(int)
            ):
                raise ValueError(f"task {task.task_id}: unseen query category")

    if (
        len(ids) != len(set(ids))
        or len(task_checksums) != len(set(task_checksums))
        or len(content_checksums) != len(set(content_checksums))
    ):
        raise ValueError("sandbox task identities or contents are not unique")
    return manifest
