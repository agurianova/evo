"""Execute reverse-SCM predictor graphs with leakage probes."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from problems.tabular._common import tabular_data

from .encode import TypeAwareEncoder
from .graph import RAW_INPUT, PredictorGraph
from .ops import OperatorExecutionError, get_operator


class GraphExecutionError(RuntimeError):
    pass


_ROUNDING_RTOL = 1e-9
_OWN_TARGET_PROBE_MAX_ROWS = 8


@dataclass(frozen=True)
class GraphTriplet:
    fit: np.ndarray
    validation: np.ndarray
    query: np.ndarray


def _concat_parent_outputs(
    node_inputs: list[str],
    *,
    raw_encoded: np.ndarray,
    node_outputs: dict[str, np.ndarray],
) -> np.ndarray:
    blocks: list[np.ndarray] = []
    for name in node_inputs:
        if name == RAW_INPUT:
            blocks.append(raw_encoded)
        else:
            blocks.append(node_outputs[name])
    if not blocks:
        return np.zeros((raw_encoded.shape[0], 0), dtype=np.float64)
    return np.hstack(blocks).astype(np.float64)


def _build_readout_matrix(
    graph: PredictorGraph,
    *,
    raw_encoded: np.ndarray,
    node_outputs: dict[str, np.ndarray],
) -> np.ndarray:
    blocks: list[np.ndarray] = []
    if graph.readout.include_raw:
        blocks.append(raw_encoded.astype(np.float64))
    for node in graph.nodes:
        if not node.is_readout:
            continue
        output = node_outputs[node.id]
        if node.gate != 1.0:
            output = output * node.gate
        blocks.append(output.astype(np.float64))
    if not blocks:
        return raw_encoded.astype(np.float64)
    return np.hstack(blocks)


def execute_graph_triplet(
    graph: PredictorGraph,
    X_fit: np.ndarray,
    X_validation: np.ndarray,
    X_query: np.ndarray,
    *,
    y_fit: np.ndarray | None,
    columns: tuple[tabular_data.ColumnSpec, ...],
    task_type: str,
    n_classes: int | None,
    seed: int = 0,
) -> tuple[GraphTriplet, GraphTriplet]:
    """Return final readout features and encoded-raw features for each role."""

    lengths = (len(X_fit), len(X_validation), len(X_query))
    if y_fit is not None and len(y_fit) != lengths[0]:
        raise GraphExecutionError(
            f"y_fit length {len(y_fit)} does not match fit rows {lengths[0]}"
        )

    encoder = TypeAwareEncoder.fit(
        X_fit,
        y_fit if y_fit is not None else np.zeros(lengths[0]),
        columns=columns,
        task_type=task_type,
        n_classes=n_classes,
        seed=seed,
        # Cross-fitted target encoding is safe when it feeds the final readout
        # directly.  Feeding it into another supervised cross-fit would require
        # nested folds for the whole pipeline, so schema-v1 supervised graphs
        # use frequency/missingness categorical channels instead.
        include_target_encoding=not any(
            get_operator(node.op).uses_supervision_for(node.params)
            for node in graph.nodes
        ),
    )
    encoded_fit = encoder.transform(X_fit, use_oof=True)
    encoded_val = encoder.transform(X_validation)
    encoded_query = encoder.transform(X_query)

    combined = np.vstack([encoded_fit, encoded_val, encoded_query])
    fit_stop = lengths[0]
    val_stop = fit_stop + lengths[1]

    node_outputs: dict[str, np.ndarray] = {}
    for node in graph.nodes:
        parent = _concat_parent_outputs(
            node.inputs,
            raw_encoded=combined,
            node_outputs=node_outputs,
        )
        parent_fit = parent[:fit_stop]
        operator = get_operator(node.op)
        try:
            state = operator.fit(
                parent_fit,
                y_fit,
                node.params,
                task_type=task_type,
                n_classes=n_classes,
            )
            transformed_fit = operator.transform_fit(parent_fit, state)
            if fit_stop == len(parent):
                transformed_rest = np.zeros(
                    (0, transformed_fit.shape[1]), dtype=transformed_fit.dtype
                )
            else:
                transformed_rest = operator.transform(parent[fit_stop:], state)
            transformed = np.vstack([transformed_fit, transformed_rest])
        except OperatorExecutionError as exc:
            raise GraphExecutionError(f"node {node.id}: {exc}") from exc
        except Exception as exc:
            raise GraphExecutionError(f"node {node.id}: {exc}") from exc
        if transformed.shape[0] != combined.shape[0]:
            raise GraphExecutionError(f"node {node.id}: row count changed")
        node_outputs[node.id] = transformed

    readout_all = _build_readout_matrix(
        graph,
        raw_encoded=combined,
        node_outputs=node_outputs,
    )
    readout = GraphTriplet(
        fit=readout_all[:fit_stop],
        validation=readout_all[fit_stop:val_stop],
        query=readout_all[val_stop:],
    )
    encoded_triplet = GraphTriplet(
        fit=encoded_fit,
        validation=encoded_val,
        query=encoded_query,
    )
    return readout, encoded_triplet


def assert_split_invariant(
    graph: PredictorGraph,
    X_fit: np.ndarray,
    *,
    y_fit: np.ndarray | None,
    columns: tuple[tabular_data.ColumnSpec, ...],
    task_type: str,
    n_classes: int | None,
) -> None:
    if len(X_fit) < 4:
        raise GraphExecutionError(
            f"split-invariance probe needs at least 4 rows; got {len(X_fit)}"
        )
    fit = np.asarray(X_fit, dtype=np.float64)
    full_query = fit.copy()
    subset_query = fit[1:-1:2]
    empty_val = fit[:0]

    full, _ = execute_graph_triplet(
        graph,
        fit,
        empty_val,
        full_query,
        y_fit=y_fit,
        columns=columns,
        task_type=task_type,
        n_classes=n_classes,
    )
    repeated, _ = execute_graph_triplet(
        graph,
        fit,
        empty_val,
        full_query,
        y_fit=y_fit,
        columns=columns,
        task_type=task_type,
        n_classes=n_classes,
    )
    if not np.allclose(full.query, repeated.query, rtol=0.0, atol=_ROUNDING_RTOL, equal_nan=True):
        raise GraphExecutionError(
            "non-deterministic behavior: readout features change between identical executions"
        )

    subset, _ = execute_graph_triplet(
        graph,
        fit,
        empty_val,
        subset_query,
        y_fit=y_fit,
        columns=columns,
        task_type=task_type,
        n_classes=n_classes,
    )
    full_subset = full.query[1:-1:2]
    if not np.allclose(
        full_subset, subset.query, rtol=0.0, atol=_ROUNDING_RTOL, equal_nan=True
    ):
        raise GraphExecutionError(
            "split-dependent behavior: readout features change with batch composition"
        )

    if y_fit is None or not any(
        get_operator(node.op).uses_supervision_for(node.params) for node in graph.nodes
    ):
        return

    baseline, _ = execute_graph_triplet(
        graph,
        fit,
        empty_val,
        fit[:0],
        y_fit=y_fit,
        columns=columns,
        task_type=task_type,
        n_classes=n_classes,
    )
    appended, _ = execute_graph_triplet(
        graph,
        fit,
        empty_val,
        subset_query,
        y_fit=y_fit,
        columns=columns,
        task_type=task_type,
        n_classes=n_classes,
    )
    if not np.allclose(
        baseline.fit, appended.fit, rtol=0.0, atol=_ROUNDING_RTOL, equal_nan=True
    ):
        raise GraphExecutionError(
            "batch-dependent fit rows: fit features differ when query batch is appended"
        )

    target = np.asarray(y_fit)
    scale = max(1.0, float(np.nanstd(target.astype(np.float64))))
    probe_count = min(_OWN_TARGET_PROBE_MAX_ROWS, len(fit))
    probe_indices = np.linspace(0, len(fit) - 1, num=probe_count, dtype=int)
    for index in probe_indices:
        perturbed = target.copy()
        if task_type == tabular_data.REGRESSION:
            perturbed[int(index)] = perturbed[int(index)] + scale
        else:
            if n_classes is None or n_classes < 2:
                raise GraphExecutionError("classification target probe needs n_classes >= 2")
            perturbed[int(index)] = (int(perturbed[int(index)]) + 1) % n_classes
        candidate, _ = execute_graph_triplet(
            graph,
            fit,
            empty_val,
            fit[:0],
            y_fit=perturbed,
            columns=columns,
            task_type=task_type,
            n_classes=n_classes,
        )
        if not np.allclose(
            baseline.fit[int(index)],
            candidate.fit[int(index)],
            rtol=0.0,
            atol=_ROUNDING_RTOL,
            equal_nan=True,
        ):
            raise GraphExecutionError(
                "own-target leakage: fit row "
                f"{int(index)} changes when only its own y_fit changes"
            )
