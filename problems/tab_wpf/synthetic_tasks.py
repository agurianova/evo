"""Deterministic TabICL-style synthetic regression tasks for Tab-WPF.

The hidden generator DAG is used only to create a frozen task bank.  Predictor
graphs receive observed context/query arrays and never receive the generator
graph, task family, seed, query target, or split identity.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
import hashlib
import json
from pathlib import Path
import platform
from typing import Any

import numpy as np

from problems.tabular._common import tabular_data

BANK_SCHEMA_VERSION = 1
GENERATOR_VERSION = "tab_wpf_generator_dag_v2"
DEFAULT_MASTER_SEED = 20260819
REPLICAS_PER_FAMILY = 10

META_TRAIN = "meta_train"
META_VALID = "meta_valid"
META_TEST = "meta_test"
META_SPLITS = (META_TRAIN, META_VALID, META_TEST)

FAMILIES: tuple[str, ...] = (
    "sparse_linear",
    "smooth_additive",
    "low_order_interactions",
    "periodic_rbf",
    "piecewise_rules",
    "mlp_scm",
    "mixed_mechanisms",
    "mixed_feature_types",
    "missing_heavy_tail",
    "latent_factor_shift",
)

_FAMILY_OPS: dict[str, tuple[str, ...]] = {
    "sparse_linear": ("linear",),
    "smooth_additive": ("linear", "tanh", "sin", "quadratic"),
    "low_order_interactions": ("linear", "quadratic", "product", "max"),
    "periodic_rbf": ("sin", "rbf", "tanh"),
    "piecewise_rules": ("threshold", "max", "linear"),
    "mlp_scm": ("linear", "tanh", "leaky_relu"),
    "mixed_mechanisms": (
        "linear",
        "tanh",
        "sin",
        "quadratic",
        "product",
        "max",
        "threshold",
        "rbf",
    ),
    "mixed_feature_types": ("linear", "tanh", "product", "threshold"),
    "missing_heavy_tail": ("linear", "tanh", "product", "threshold"),
    "latent_factor_shift": ("linear", "tanh", "product", "quadratic"),
}


@dataclass(frozen=True)
class SyntheticTask:
    task_id: str
    family: str
    meta_split: str
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


def _generator_source_sha256() -> str:
    """Fingerprint the exact generator implementation that froze the bank."""

    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _update_array_hash(hasher: Any, name: str, array: np.ndarray) -> None:
    contiguous = np.ascontiguousarray(array)
    hasher.update(name.encode("utf-8"))
    hasher.update(str(contiguous.dtype).encode("ascii"))
    hasher.update(_json_bytes(list(contiguous.shape)))
    hasher.update(contiguous.tobytes(order="C"))


def _task_checksum(
    *,
    metadata: dict[str, Any],
    arrays: dict[str, np.ndarray],
) -> str:
    """Hash all serialized task metadata and arrays except this checksum."""

    hasher = hashlib.sha256()
    hasher.update(
        _json_bytes(
            {key: value for key, value in metadata.items() if key != "task_checksum"}
        )
    )
    for name in sorted(arrays):
        _update_array_hash(hasher, name, arrays[name])
    return hasher.hexdigest()


def _task_content_checksum(
    *,
    columns: list[dict[str, Any]],
    generator: dict[str, Any],
    X_context: np.ndarray,
    y_context: np.ndarray,
    X_query: np.ndarray,
    y_query: np.ndarray,
) -> str:
    """Hash task content without identity or outer-split labels.

    ``task_checksum`` protects the complete serialized record.  This second
    checksum is deliberately blind to ``task_id`` and ``meta_split`` so the
    generator cannot pass the diversity check by relabeling duplicate data.
    """

    hasher = hashlib.sha256()
    hasher.update(_json_bytes({"columns": columns, "generator": generator}))
    for name, array in (
        ("X_context", X_context),
        ("y_context", y_context),
        ("X_query", X_query),
        ("y_query", y_query),
    ):
        _update_array_hash(hasher, name, array)
    return hasher.hexdigest()


def _latin_values(master_seed: int, family_index: int, replica: int) -> np.ndarray:
    values: list[float] = []
    for dimension in range(10):
        seed = np.random.SeedSequence(
            [master_seed, family_index, 104729, dimension]
        )
        permutation = np.random.default_rng(seed).permutation(REPLICAS_PER_FAMILY)
        values.append((float(permutation[replica]) + 0.5) / REPLICAS_PER_FAMILY)
    return np.asarray(values, dtype=np.float64)


def _meta_split(master_seed: int, family_index: int, replica: int) -> str:
    seed = np.random.SeedSequence([master_seed, family_index, 130363])
    order = np.random.default_rng(seed).permutation(REPLICAS_PER_FAMILY)
    rank = int(np.flatnonzero(order == replica)[0])
    if rank < 6:
        return META_TRAIN
    if rank < 8:
        return META_VALID
    return META_TEST


def _sample_root(
    distribution: str,
    n_rows: int,
    rng: np.random.Generator,
) -> np.ndarray:
    if distribution == "uniform":
        return rng.uniform(-2.0, 2.0, size=n_rows)
    if distribution == "student_t":
        return np.clip(rng.standard_t(df=5, size=n_rows), -12.0, 12.0)
    if distribution == "mixture":
        component = rng.integers(0, 3, size=n_rows)
        centers = np.asarray([-2.0, 0.0, 2.5])
        return centers[component] + rng.normal(scale=0.45, size=n_rows)
    if distribution == "bernoulli":
        return rng.binomial(1, 0.5, size=n_rows).astype(np.float64)
    return rng.normal(size=n_rows)


def _standardize_from_context(
    values: np.ndarray,
    n_context: int,
) -> tuple[np.ndarray, float, float]:
    context = values[:n_context]
    center = float(np.mean(context))
    scale = float(np.std(context))
    if not np.isfinite(scale) or scale < 1e-8:
        scale = 1.0
    normalized = np.clip((values - center) / scale, -20.0, 20.0)
    return normalized, center, scale


def _evaluate_node(
    op: str,
    parent_values: np.ndarray,
    *,
    weights: np.ndarray,
    aux_weights: np.ndarray,
    bias: float,
    threshold: float,
) -> np.ndarray:
    linear = parent_values @ weights + bias
    if op == "linear":
        return linear
    if op == "tanh":
        return np.tanh(linear)
    if op == "leaky_relu":
        return np.where(linear >= 0.0, linear, 0.05 * linear)
    if op == "sin":
        return np.sin(linear)
    if op == "quadratic":
        return linear + 0.35 * ((parent_values**2) @ aux_weights)
    if op == "product":
        if parent_values.shape[1] == 1:
            return linear * parent_values[:, 0]
        product_width = min(3, parent_values.shape[1])
        return linear + np.prod(parent_values[:, :product_width], axis=1)
    if op == "max":
        return np.max(parent_values * weights.reshape(1, -1), axis=1) + bias
    if op == "threshold":
        signs = np.where(parent_values > threshold, 1.0, -1.0)
        return signs @ weights + 0.2 * linear
    if op == "rbf":
        return np.exp(-0.5 * linear**2) + 0.15 * linear
    raise ValueError(f"unknown generator op {op!r}")


def _ancestors(nodes: list[dict[str, Any]], target_id: str) -> set[str]:
    by_id = {node["id"]: node for node in nodes}
    found: set[str] = set()
    stack = list(by_id[target_id].get("parents", []))
    while stack:
        node_id = stack.pop()
        if node_id in found:
            continue
        found.add(node_id)
        stack.extend(by_id[node_id].get("parents", []))
    return found


def _quantile_codes(
    values: np.ndarray,
    n_context: int,
    cardinality: int,
) -> np.ndarray:
    probabilities = np.linspace(0.0, 1.0, cardinality + 1)[1:-1]
    edges = np.unique(np.quantile(values[:n_context], probabilities))
    return np.digitize(values, edges, right=False).astype(np.float64)


def _feature_columns(
    base_features: list[np.ndarray],
    *,
    family: str,
    n_context: int,
    rng: np.random.Generator,
    missing_fraction: float,
) -> tuple[np.ndarray, list[dict[str, Any]], list[dict[str, Any]]]:
    converted: list[tuple[str, np.ndarray, int | None]] = []
    feature_meta: list[dict[str, Any]] = []
    for index, values in enumerate(base_features):
        kind = "numeric"
        cardinality: int | None = None
        converted_values = np.asarray(values, dtype=np.float64).copy()
        if family == "mixed_feature_types":
            mod = index % 4
            if mod == 1:
                kind = "binary"
                threshold = float(np.median(converted_values[:n_context]))
                converted_values = (converted_values > threshold).astype(np.float64)
            elif mod in (2, 3):
                kind = "categorical"
                cardinality = int(rng.integers(3, 9))
                converted_values = _quantile_codes(
                    converted_values, n_context, cardinality
                )
                if mod == 3:
                    # A few query-only levels exercise unseen-category fallback.
                    query_rows = np.arange(n_context, len(converted_values), 17)
                    converted_values[query_rows] = float(cardinality)
        converted.append((kind, converted_values, cardinality))
        feature_meta.append(
            {
                "source_position": index,
                "kind": kind,
                "cardinality": cardinality,
            }
        )

    order = sorted(
        range(len(converted)),
        key=lambda index: {"numeric": 0, "binary": 1, "categorical": 2}[
            converted[index][0]
        ],
    )
    columns: list[dict[str, Any]] = []
    blocks: list[np.ndarray] = []
    ordered_meta: list[dict[str, Any]] = []
    for new_index, old_index in enumerate(order):
        kind, values, cardinality = converted[old_index]
        blocks.append(values)
        vocabulary = (
            None
            if cardinality is None
            else [str(level) for level in range(cardinality)]
        )
        columns.append(
            {
                "index": new_index,
                "kind": kind,
                "cardinality": cardinality,
                "vocabulary": vocabulary,
            }
        )
        ordered_meta.append(feature_meta[old_index])
        ordered_meta[-1]["column_index"] = new_index

    X = np.column_stack(blocks).astype(np.float64)
    if missing_fraction > 0.0:
        driver = np.nan_to_num(X[:, 0], nan=0.0)
        driver = np.clip(driver, -4.0, 4.0)
        for column in range(X.shape[1]):
            base_probability = missing_fraction * (0.5 + 0.5 / (1.0 + np.exp(-driver)))
            missing = rng.random(len(X)) < np.clip(base_probability, 0.0, 0.45)
            X[missing, column] = np.nan
    return X, columns, ordered_meta


def _generate_task(
    family_index: int,
    replica: int,
    *,
    master_seed: int,
    attempt: int,
) -> tuple[dict[str, Any], dict[str, np.ndarray]]:
    family = FAMILIES[family_index]
    task_id = f"syn_f{family_index:02d}_r{replica:02d}"
    latin = _latin_values(master_seed, family_index, replica)
    seed_sequence = np.random.SeedSequence(
        [master_seed, family_index, replica, attempt]
    )
    structure_seed, row_seed, feature_seed, noise_seed = seed_sequence.spawn(4)
    structure_rng = np.random.default_rng(structure_seed)
    row_rng = np.random.default_rng(row_seed)
    feature_rng = np.random.default_rng(feature_seed)
    noise_rng = np.random.default_rng(noise_seed)

    n_context = int(128 + round(latin[0] * 384 / 16) * 16)
    n_query = int(96 + round(latin[1] * 160 / 16) * 16)
    if family == "latent_factor_shift":
        n_features = int(24 + round(latin[2] * 24))
    else:
        n_features = int(5 + round(latin[2] * 15))
    n_roots = int(3 + round(latin[3] * 4))
    n_hidden = int(3 + round(latin[4] * 8))
    target_r2 = float(0.55 + 0.40 * latin[5])
    n_rows = n_context + n_query

    if family == "sparse_linear":
        n_hidden = min(n_hidden, 4)
    root_distributions = ["normal", "uniform", "student_t", "mixture"]
    if family == "missing_heavy_tail":
        root_distributions = ["student_t", "mixture"]

    nodes: list[dict[str, Any]] = []
    values_by_id: dict[str, np.ndarray] = {}
    for root_index in range(n_roots):
        node_id = f"z{root_index}"
        distribution = str(structure_rng.choice(root_distributions))
        values = _sample_root(distribution, n_rows, row_rng)
        shift = 0.0
        if family == "latent_factor_shift" and root_index % 2 == 0:
            shift = float(0.4 + 1.2 * latin[6])
            values[n_context:] += shift
        normalized, center, scale = _standardize_from_context(values, n_context)
        values_by_id[node_id] = normalized
        nodes.append(
            {
                "id": node_id,
                "op": "root",
                "parents": [],
                "distribution": distribution,
                "query_shift": shift,
                "normalization": {"center": center, "scale": scale},
            }
        )

    allowed_ops = _FAMILY_OPS[family]
    for hidden_index in range(n_hidden):
        node_id = f"z{n_roots + hidden_index}"
        available = [node["id"] for node in nodes]
        max_parents = min(3, len(available))
        min_parents = 2 if hidden_index == n_hidden - 1 else 1
        parent_count = int(structure_rng.integers(min_parents, max_parents + 1))
        if family == "sparse_linear":
            parent_count = min(parent_count, 2)
        parents = [
            str(value)
            for value in structure_rng.choice(
                available, size=parent_count, replace=False
            )
        ]
        op = str(structure_rng.choice(allowed_ops))
        weights = structure_rng.normal(size=parent_count) / np.sqrt(parent_count)
        aux_weights = structure_rng.normal(size=parent_count) / np.sqrt(parent_count)
        bias = float(structure_rng.normal(scale=0.4))
        threshold = float(structure_rng.normal(scale=0.5))
        parent_values = np.column_stack([values_by_id[parent] for parent in parents])
        raw = _evaluate_node(
            op,
            parent_values,
            weights=weights,
            aux_weights=aux_weights,
            bias=bias,
            threshold=threshold,
        )
        normalized, center, scale = _standardize_from_context(raw, n_context)
        values_by_id[node_id] = normalized
        nodes.append(
            {
                "id": node_id,
                "op": op,
                "parents": parents,
                "weights": weights.tolist(),
                "aux_weights": aux_weights.tolist(),
                "bias": bias,
                "threshold": threshold,
                "normalization": {"center": center, "scale": scale},
            }
        )

    target_id = nodes[-1]["id"]
    ancestor_ids = sorted(_ancestors(nodes, target_id))
    if len(ancestor_ids) < 2:
        raise ValueError("target must have at least two observed ancestors")

    feature_sources: list[dict[str, Any]] = []
    base_features: list[np.ndarray] = []
    informative_count = min(
        len(ancestor_ids), max(2, int(round(0.55 * n_features)))
    )
    # Always expose the target's direct causal parents.  Randomly exposing only
    # distant ancestors can make a task irreducible for reasons unrelated to a
    # predictor's quality and destroy useful evolutionary headroom.  Remaining
    # informative slots still sample the wider ancestor set for diversity.
    direct_parent_ids = [str(value) for value in nodes[-1]["parents"]]
    informative_count = max(informative_count, len(direct_parent_ids))
    remaining_ancestors = [
        node_id for node_id in ancestor_ids if node_id not in direct_parent_ids
    ]
    additional_count = informative_count - len(direct_parent_ids)
    additional_ids = (
        []
        if additional_count == 0
        else [
            str(value)
            for value in feature_rng.choice(
                remaining_ancestors,
                size=additional_count,
                replace=False,
            )
        ]
    )
    informative_ids = direct_parent_ids + additional_ids
    for node_id in informative_ids:
        base_features.append(values_by_id[node_id].copy())
        feature_sources.append({"kind": "ancestor", "node_id": node_id})

    while len(base_features) < n_features:
        position = len(base_features)
        if family in {"sparse_linear", "latent_factor_shift"} and position % 3:
            left = int(feature_rng.integers(0, informative_count))
            right = int(feature_rng.integers(0, informative_count))
            mix = (
                0.75 * base_features[left]
                + 0.25 * base_features[right]
                + feature_rng.normal(scale=0.05, size=n_rows)
            )
            normalized, _, _ = _standardize_from_context(mix, n_context)
            base_features.append(normalized)
            feature_sources.append(
                {"kind": "redundant_mix", "parents": [left, right]}
            )
        else:
            nuisance_distribution = str(
                feature_rng.choice(["normal", "uniform", "student_t"])
            )
            nuisance = _sample_root(nuisance_distribution, n_rows, feature_rng)
            normalized, _, _ = _standardize_from_context(nuisance, n_context)
            base_features.append(normalized)
            feature_sources.append(
                {"kind": "independent_nuisance", "distribution": nuisance_distribution}
            )

    missing_fraction = 0.0
    if family == "missing_heavy_tail":
        missing_fraction = float(0.05 + 0.25 * latin[7])
    elif family == "mixed_feature_types":
        missing_fraction = float(0.01 + 0.07 * latin[7])
    X, columns, feature_type_meta = _feature_columns(
        base_features,
        family=family,
        n_context=n_context,
        rng=feature_rng,
        missing_fraction=missing_fraction,
    )
    # _feature_columns groups columns by runtime type.  Reorder the provenance
    # records by the same permutation so observed_features[i] always describes
    # columns[i], rather than silently attaching metadata to the wrong feature.
    ordered_sources: list[dict[str, Any]] = []
    for typed in feature_type_meta:
        source_position = int(typed["source_position"])
        source = dict(feature_sources[source_position])
        source.update(typed)
        ordered_sources.append(source)
    feature_sources = ordered_sources

    signal = values_by_id[target_id].copy()
    signal_scale = float(np.std(signal[:n_context]))
    desired_noise_scale = signal_scale * np.sqrt(
        (1.0 - target_r2) / target_r2
    )
    if family == "missing_heavy_tail":
        driver = np.abs(values_by_id[nodes[0]["id"]])
        noise = noise_rng.standard_t(df=5, size=n_rows)
        noise *= 0.35 + 0.65 * np.clip(driver, 0.0, 3.0)
        outliers = noise_rng.random(n_rows) < 0.02
        noise[outliers] += noise_rng.normal(scale=4.0, size=outliers.sum())
    else:
        noise = noise_rng.normal(size=n_rows)

    # Match the requested context SNR for every noise shape, including the
    # heavy-tailed/heteroscedastic family.  Orthogonalization uses context rows
    # only and preserves the sampled query distribution while preventing a
    # chance finite-sample signal/noise correlation from falsifying the label.
    signal_center = float(np.mean(signal[:n_context]))
    signal_centered = signal - signal_center
    noise -= float(np.mean(noise[:n_context]))
    signal_energy = float(
        np.dot(signal_centered[:n_context], signal_centered[:n_context])
    )
    if signal_energy > 1e-12:
        projection = float(
            np.dot(noise[:n_context], signal_centered[:n_context]) / signal_energy
        )
        noise -= projection * signal_centered
    noise -= float(np.mean(noise[:n_context]))
    realized_noise_scale = float(np.std(noise[:n_context]))
    if not np.isfinite(realized_noise_scale) or realized_noise_scale < 1e-8:
        raise ValueError("degenerate sampled context noise")
    noise *= desired_noise_scale / realized_noise_scale
    y = signal + noise
    context_noise_energy = float(np.sum(np.square(noise[:n_context])))
    context_target_centered = y[:n_context] - float(np.mean(y[:n_context]))
    context_target_energy = float(np.sum(np.square(context_target_centered)))
    realized_context_signal_r2 = 1.0 - (
        context_noise_energy / max(context_target_energy, 1e-12)
    )
    y_center = float(np.mean(y[:n_context]))
    y_scale = float(np.std(y[:n_context]))
    if not np.isfinite(y_scale) or y_scale < 1e-8:
        raise ValueError("degenerate context target")
    y = (y - y_center) / y_scale

    X_context = X[:n_context].astype(np.float64)
    X_query = X[n_context:].astype(np.float64)
    y_context = y[:n_context].astype(np.float64)
    y_query = y[n_context:].astype(np.float64)
    if not np.all(np.isfinite(y_context)) or not np.all(np.isfinite(y_query)):
        raise ValueError("non-finite target")
    finite_per_column = np.isfinite(X_context).sum(axis=0)
    if np.any(finite_per_column < max(8, n_context // 3)):
        raise ValueError("too few finite context values in a feature")

    meta_split = _meta_split(master_seed, family_index, replica)
    generator = {
        "generator_version": GENERATOR_VERSION,
        "nodes": nodes,
        "target_node": target_id,
        "observed_features": feature_sources,
        "target_postprocess": {
            "requested_signal_r2": target_r2,
            "realized_context_signal_r2": realized_context_signal_r2,
            "realized_context_noise_std": float(np.std(noise[:n_context])),
            "noise_scale": float(desired_noise_scale),
            "context_center": y_center,
            "context_scale": y_scale,
        },
        "missing_fraction": missing_fraction,
        "observed_target_parent_count": len(direct_parent_ids),
        "latin_cell": latin.tolist(),
    }
    metadata: dict[str, Any] = {
        "schema_version": BANK_SCHEMA_VERSION,
        "task_id": task_id,
        "family": family,
        "family_index": family_index,
        "replica": replica,
        "meta_split": meta_split,
        "attempt": attempt,
        "master_seed": master_seed,
        "n_context": n_context,
        "n_query": n_query,
        "n_features": int(X.shape[1]),
        "task_type": tabular_data.REGRESSION,
        "n_classes": None,
        "columns": columns,
        "generator": generator,
    }
    metadata["generator_checksum"] = _hash_payload(generator)
    metadata["content_checksum"] = _task_content_checksum(
        columns=columns,
        generator=generator,
        X_context=X_context,
        y_context=y_context,
        X_query=X_query,
        y_query=y_query,
    )
    arrays = {
        "X_context": X_context,
        "y_context": y_context,
        "X_query": X_query,
        "y_query": y_query,
    }
    metadata["task_checksum"] = _task_checksum(metadata=metadata, arrays=arrays)
    return metadata, arrays


def generate_task_bank(
    output_dir: str | Path,
    *,
    master_seed: int = DEFAULT_MASTER_SEED,
) -> dict[str, Any]:
    """Create exactly 100 frozen tasks, refusing to overwrite any existing bank."""

    root = Path(output_dir).expanduser().resolve()
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"refusing to overwrite non-empty task bank: {root}")
    root.mkdir(parents=True, exist_ok=True)
    tasks_root = root / "tasks"
    tasks_root.mkdir()

    records: list[dict[str, Any]] = []
    seen_content_checksums: set[str] = set()
    for family_index, family in enumerate(FAMILIES):
        for replica in range(REPLICAS_PER_FAMILY):
            metadata: dict[str, Any] | None = None
            arrays: dict[str, np.ndarray] | None = None
            accepted = False
            for attempt in range(20):
                try:
                    metadata, arrays = _generate_task(
                        family_index,
                        replica,
                        master_seed=master_seed,
                        attempt=attempt,
                    )
                except ValueError:
                    continue
                if metadata["content_checksum"] not in seen_content_checksums:
                    accepted = True
                    break
            if not accepted or metadata is None or arrays is None:
                raise RuntimeError(f"failed to generate {family}/{replica}")
            checksum = str(metadata["task_checksum"])
            content_checksum = str(metadata["content_checksum"])
            if content_checksum in seen_content_checksums:
                raise RuntimeError(f"duplicate generated task {metadata['task_id']}")
            seen_content_checksums.add(content_checksum)

            task_id = str(metadata["task_id"])
            task_dir = tasks_root / task_id
            task_dir.mkdir()
            np.savez_compressed(task_dir / "data.npz", **arrays)
            (task_dir / "task.json").write_text(
                json.dumps(metadata, indent=2, sort_keys=True) + "\n"
            )
            records.append(
                {
                    "task_id": task_id,
                    "family": family,
                    "meta_split": metadata["meta_split"],
                    "task_dir": f"tasks/{task_id}",
                    "n_context": metadata["n_context"],
                    "n_query": metadata["n_query"],
                    "n_features": metadata["n_features"],
                    "generator_checksum": metadata["generator_checksum"],
                    "content_checksum": content_checksum,
                    "task_checksum": checksum,
                }
            )

    split_counts = {
        split: sum(record["meta_split"] == split for record in records)
        for split in META_SPLITS
    }
    family_counts = {
        family: sum(record["family"] == family for record in records)
        for family in FAMILIES
    }
    manifest: dict[str, Any] = {
        "schema_version": BANK_SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "generator_source_sha256": _generator_source_sha256(),
        "master_seed": master_seed,
        "task_count": len(records),
        "families": list(FAMILIES),
        "replicas_per_family": REPLICAS_PER_FAMILY,
        "split_counts": split_counts,
        "family_counts": family_counts,
        "task_type": tabular_data.REGRESSION,
        "generation_environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
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
    verify_task_bank(root)
    return manifest


@cache
def _load_manifest_cached(resolved_bank_dir: str) -> dict[str, Any]:
    path = Path(resolved_bank_dir) / "manifest.json"
    if not path.is_file():
        raise FileNotFoundError(f"synthetic task manifest not found: {path}")
    manifest = json.loads(path.read_text())
    if manifest.get("schema_version") != BANK_SCHEMA_VERSION:
        raise ValueError("unsupported synthetic task bank schema")
    recorded_checksum = str(manifest.get("bank_checksum", ""))
    computed_checksum = _hash_payload(
        {
            key: value
            for key, value in manifest.items()
            if key not in {"bank_checksum", "generation_environment"}
        }
    )
    if recorded_checksum != computed_checksum:
        raise ValueError("synthetic task bank manifest checksum mismatch")
    if manifest.get("generator_version") != GENERATOR_VERSION:
        raise ValueError(
            "task bank generator version does not match this checkout: "
            f"{manifest.get('generator_version')!r} != {GENERATOR_VERSION!r}"
        )
    if manifest.get("generator_source_sha256") != _generator_source_sha256():
        raise ValueError(
            "task bank was produced by a different synthetic_tasks.py; use the "
            "recorded checkout or regenerate the frozen bank"
        )
    return manifest


def load_manifest(bank_dir: str | Path) -> dict[str, Any]:
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
    resolved_bank_dir: str,
    task_id: str,
    relative_task_dir: str,
    recorded_checksum: str,
    recorded_content_checksum: str,
    verify_checksum: bool,
) -> SyntheticTask:
    task_dir = Path(resolved_bank_dir) / relative_task_dir
    metadata = json.loads((task_dir / "task.json").read_text())
    with np.load(task_dir / "data.npz", allow_pickle=False) as data:
        arrays = {name: np.asarray(data[name]) for name in data.files}
    required = {"X_context", "y_context", "X_query", "y_query"}
    if set(arrays) != required:
        raise ValueError(f"task {task_id}: unexpected arrays {sorted(arrays)}")
    columns = tuple(_column_spec(column) for column in metadata["columns"])
    if verify_checksum:
        checksum = _task_checksum(metadata=metadata, arrays=arrays)
        if checksum != metadata["task_checksum"] or checksum != recorded_checksum:
            raise ValueError(f"task {task_id}: checksum mismatch")
        content_checksum = _task_content_checksum(
            columns=list(metadata["columns"]),
            generator=dict(metadata["generator"]),
            X_context=arrays["X_context"],
            y_context=arrays["y_context"],
            X_query=arrays["X_query"],
            y_query=arrays["y_query"],
        )
        if (
            content_checksum != metadata.get("content_checksum")
            or content_checksum != recorded_content_checksum
        ):
            raise ValueError(f"task {task_id}: content checksum mismatch")
    for array in arrays.values():
        array.setflags(write=False)
    return SyntheticTask(
        task_id=str(metadata["task_id"]),
        family=str(metadata["family"]),
        meta_split=str(metadata["meta_split"]),
        columns=columns,
        X_context=arrays["X_context"],
        y_context=arrays["y_context"],
        X_query=arrays["X_query"],
        y_query=arrays["y_query"],
        metadata=metadata,
    )


def load_task(
    bank_dir: str | Path,
    record_or_id: dict[str, Any] | str,
    *,
    verify_checksum: bool = True,
) -> SyntheticTask:
    root = Path(bank_dir).expanduser().resolve()
    manifest = load_manifest(root)
    if isinstance(record_or_id, str):
        matches = [
            record
            for record in manifest["tasks"]
            if record["task_id"] == record_or_id
        ]
        if len(matches) != 1:
            raise KeyError(f"unknown task id {record_or_id!r}")
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


def iter_tasks(
    bank_dir: str | Path,
    *,
    meta_split: str,
    verify_checksum: bool = True,
):
    if meta_split not in META_SPLITS:
        raise ValueError(f"unknown meta split {meta_split!r}")
    manifest = load_manifest(bank_dir)
    for record in manifest["tasks"]:
        if record["meta_split"] == meta_split:
            yield load_task(
                bank_dir,
                record,
                verify_checksum=verify_checksum,
            )


def verify_task_bank(bank_dir: str | Path) -> dict[str, Any]:
    root = Path(bank_dir).expanduser().resolve()
    manifest = load_manifest(root)
    expected_count = len(FAMILIES) * REPLICAS_PER_FAMILY
    if manifest.get("task_count") != expected_count:
        raise ValueError(
            f"task bank must contain {expected_count} tasks, got {manifest.get('task_count')}"
        )
    if manifest.get("split_counts") != {
        META_TRAIN: 60,
        META_VALID: 20,
        META_TEST: 20,
    }:
        raise ValueError(f"unexpected meta split counts: {manifest.get('split_counts')}")
    if any(
        int(manifest.get("family_counts", {}).get(family, 0))
        != REPLICAS_PER_FAMILY
        for family in FAMILIES
    ):
        raise ValueError("task bank is not balanced across generator families")
    for family in FAMILIES:
        family_records = [
            record for record in manifest["tasks"] if record["family"] == family
        ]
        family_splits = {
            split: sum(record["meta_split"] == split for record in family_records)
            for split in META_SPLITS
        }
        if family_splits != {META_TRAIN: 6, META_VALID: 2, META_TEST: 2}:
            raise ValueError(
                f"family {family!r} has unexpected meta split counts: "
                f"{family_splits}"
            )
    ids = [str(record["task_id"]) for record in manifest["tasks"]]
    checksums = [str(record["task_checksum"]) for record in manifest["tasks"]]
    content_checksums = [
        str(record["content_checksum"]) for record in manifest["tasks"]
    ]
    if (
        len(ids) != len(set(ids))
        or len(checksums) != len(set(checksums))
        or len(content_checksums) != len(set(content_checksums))
    ):
        raise ValueError(
            "task ids, task checksums, and identity-blind content checksums "
            "must be unique"
        )
    for record in manifest["tasks"]:
        task = load_task(root, record, verify_checksum=True)
        if task.metadata.get("generator_checksum") != _hash_payload(
            task.metadata.get("generator")
        ):
            raise ValueError(f"task {task.task_id}: generator checksum mismatch")
        if task.task_id != record["task_id"]:
            raise ValueError(f"task {record['task_id']}: metadata id mismatch")
        if task.family != record["family"] or task.meta_split != record["meta_split"]:
            raise ValueError(f"task {task.task_id}: manifest metadata mismatch")
        for key in (
            "n_context",
            "n_query",
            "n_features",
            "generator_checksum",
            "content_checksum",
            "task_checksum",
        ):
            if task.metadata.get(key) != record.get(key):
                raise ValueError(
                    f"task {task.task_id}: manifest field {key!r} does not match metadata"
                )
        if task.X_context.shape[1] != len(task.columns):
            raise ValueError(f"task {task.task_id}: column metadata width mismatch")
        if task.X_query.shape[1] != task.X_context.shape[1]:
            raise ValueError(f"task {task.task_id}: context/query width mismatch")
        if len(task.y_context) != len(task.X_context):
            raise ValueError(f"task {task.task_id}: context target length mismatch")
        if len(task.y_query) != len(task.X_query):
            raise ValueError(f"task {task.task_id}: query target length mismatch")
        if [column.index for column in task.columns] != list(range(len(task.columns))):
            raise ValueError(f"task {task.task_id}: column indices are not contiguous")
        observed = task.metadata["generator"]["observed_features"]
        if len(observed) != len(task.columns):
            raise ValueError(f"task {task.task_id}: feature provenance width mismatch")
        if any(
            int(source["column_index"]) != column_index
            for column_index, source in enumerate(observed)
        ):
            raise ValueError(f"task {task.task_id}: feature provenance order mismatch")
    return manifest
