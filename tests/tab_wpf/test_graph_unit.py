from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest
from hydra import compose, initialize_config_dir
from hydra.utils import get_class
from pydantic import ValidationError

from gigaevo.database.program_storage import ProgramStorage
from gigaevo.entrypoint.default_pipelines import DefaultPipelineBuilder
from gigaevo.entrypoint.evolution_context import EvolutionContext
from gigaevo.entrypoint.program_formats import JsonDocumentEvaluationFeature
from gigaevo.llm.models import MultiModelRouter
from gigaevo.memory.provider import NullMemoryProvider
from problems.tab_wpf.allowed_changes import AllowedTabWpfChanges
from problems.tab_wpf.encode import TypeAwareEncoder
from problems.tab_wpf.execution import assert_split_invariant, execute_graph_triplet
from problems.tab_wpf.graph import PredictorGraph
from problems.tab_wpf.ops import get_operator
from problems.tab_wpf.problem_context import TabWpfProblemContext
from problems.tab_wpf.readout import fit_readout, predict_readout
from problems.tabular._common import tabular_data

ROOT = Path(__file__).parents[2]
CONFIG_DIR = ROOT / "config"
SEED = ROOT / "problems/tab_wpf/initial_programs/baseline.json"


def _synthetic_columns() -> tuple[tabular_data.ColumnSpec, ...]:
    return (
        tabular_data.ColumnSpec(0, "numeric", None, None),
        tabular_data.ColumnSpec(1, "numeric", None, None),
        tabular_data.ColumnSpec(2, "binary", None, None),
        tabular_data.ColumnSpec(3, "categorical", 3, ("a", "b", "c")),
    )


def _synthetic_xy(n: int = 128, seed: int = 0):
    rng = np.random.default_rng(seed)
    X = np.column_stack(
        [
            rng.normal(size=n),
            rng.normal(size=n),
            rng.integers(0, 2, size=n).astype(np.float64),
            rng.integers(0, 3, size=n).astype(np.float64),
        ]
    )
    y = X[:, 0] * 0.5 + rng.normal(scale=0.1, size=n)
    return X, y


def _baseline() -> PredictorGraph:
    return PredictorGraph.model_validate(json.loads(SEED.read_text()))


def test_baseline_graph_has_no_dataset_or_raw_columns():
    graph = _baseline()
    dumped = graph.model_dump()
    assert "dataset" not in dumped
    assert "raw_columns" not in dumped
    assert graph.nodes == []


def test_graph_validates_operator_chain():
    graph = PredictorGraph.model_validate(
        {
            "schema_version": 1,
            "nodes": [
                {
                    "id": "std",
                    "op": "standardize",
                    "inputs": ["raw"],
                    "params": {},
                    "gate": 1.0,
                    "is_readout": True,
                    "rationale": "Normalize encoded raw features.",
                },
                {
                    "id": "mix",
                    "op": "affine_activation",
                    "inputs": ["std"],
                    "params": {
                        "activation": "tanh",
                        "n_components": 4,
                        "fit": "pca",
                        "seed": 0,
                    },
                    "gate": 0.8,
                    "is_readout": True,
                    "rationale": "SCM-style nonlinear mix.",
                },
            ],
            "readout": {"kind": "ridge", "alpha": 1.0, "include_raw": False},
        }
    )
    assert graph.depth == 2


def test_graph_rejects_unknown_input():
    with pytest.raises(ValueError, match="unavailable inputs"):
        PredictorGraph.model_validate(
            {
                "schema_version": 1,
                "nodes": [
                    {
                        "id": "bad",
                        "op": "identity",
                        "inputs": ["missing"],
                        "params": {},
                        "is_readout": True,
                        "rationale": "bad",
                    }
                ],
            }
        )


def test_graph_rejects_unknown_operator_parameter():
    with pytest.raises(ValueError, match="unknown params"):
        PredictorGraph.model_validate(
            {
                "schema_version": 1,
                "nodes": [
                    {
                        "id": "typo",
                        "op": "rbf_features",
                        "inputs": ["raw"],
                        "params": {"n_component": 8},
                        "is_readout": True,
                    }
                ],
            }
        )


def test_graph_rejects_dead_non_readout_leaf():
    with pytest.raises(ValueError, match="do not contribute to the final readout"):
        PredictorGraph.model_validate(
            {
                "schema_version": 1,
                "nodes": [
                    {
                        "id": "unused",
                        "op": "standardize",
                        "inputs": ["raw"],
                        "params": {},
                        "is_readout": False,
                    }
                ],
                "readout": {"kind": "ridge", "alpha": 1.0, "include_raw": True},
            }
        )


def test_graph_accepts_non_readout_intermediate_consumed_by_readout_node():
    graph = PredictorGraph.model_validate(
        {
            "schema_version": 1,
            "nodes": [
                {
                    "id": "intermediate",
                    "op": "standardize",
                    "inputs": ["raw"],
                    "params": {},
                    "is_readout": False,
                },
                {
                    "id": "output",
                    "op": "identity",
                    "inputs": ["intermediate"],
                    "params": {},
                    "is_readout": True,
                },
            ],
            "readout": {"kind": "ridge", "alpha": 1.0, "include_raw": False},
        }
    )
    assert graph.depth == 2


def test_graph_rejects_empty_readout_matrix():
    with pytest.raises(ValueError, match="readout has no inputs"):
        PredictorGraph.model_validate(
            {
                "schema_version": 1,
                "nodes": [],
                "readout": {"kind": "ridge", "alpha": 1.0, "include_raw": False},
            }
        )


def test_graph_rejects_supervised_operator_after_supervised_ancestor():
    with pytest.raises(ValueError, match="nested cross-fitting is not implemented"):
        PredictorGraph.model_validate(
            {
                "schema_version": 1,
                "nodes": [
                    {
                        "id": "first",
                        "op": "column_gate",
                        "inputs": ["raw"],
                        "params": {"k": 2, "seed": 0},
                        "is_readout": False,
                    },
                    {
                        "id": "second",
                        "op": "affine_activation",
                        "inputs": ["first"],
                        "params": {
                            "fit": "supervised_ridge",
                            "activation": "tanh",
                            "n_components": 2,
                            "alpha": 1.0,
                            "seed": 0,
                        },
                        "is_readout": True,
                    },
                ],
                "readout": {
                    "kind": "ridge",
                    "alpha": 1.0,
                    "include_raw": False,
                },
            }
        )


def test_column_gate_preserves_original_channel_slots_across_oof_folds():
    X, y = _synthetic_xy(n=80)
    X = X[:, :3]
    operator = get_operator("column_gate")
    state = operator.fit(
        X,
        y,
        {"k": 1, "seed": 3},
        task_type=tabular_data.REGRESSION,
        n_classes=None,
    )
    transformed_fit = operator.transform_fit(X, state)
    transformed_query = operator.transform(X[:7], state)
    assert transformed_fit.shape == X.shape
    assert transformed_query.shape == (7, X.shape[1])
    nonzero = transformed_fit != 0.0
    assert np.array_equal(transformed_fit[nonzero], X[nonzero])


def test_encoder_output_dim_on_synthetic_table():
    columns = _synthetic_columns()
    X, y = _synthetic_xy()
    encoder = TypeAwareEncoder.fit(
        X,
        y,
        columns=columns,
        task_type=tabular_data.REGRESSION,
        n_classes=None,
    )
    encoded = encoder.transform(X[:16])
    assert encoded.shape[1] == encoder.output_dim
    assert encoded.dtype == np.float32


def test_numeric_missing_value_is_neutral_after_scaling():
    columns = (tabular_data.ColumnSpec(0, "numeric", None, None),)
    X = np.array([[10.0], [12.0], [np.nan], [14.0]])
    y = np.arange(len(X), dtype=np.float64)
    encoder = TypeAwareEncoder.fit(
        X,
        y,
        columns=columns,
        task_type=tabular_data.REGRESSION,
        n_classes=None,
    )
    encoded = encoder.transform(np.array([[np.nan]]))
    assert encoded.shape == (1, 2)
    assert encoded[0, 0] == pytest.approx(0.0)
    assert encoded[0, 1] == pytest.approx(1.0)


def test_all_missing_numeric_and_binary_columns_remain_finite():
    columns = (
        tabular_data.ColumnSpec(0, "numeric", None, None),
        tabular_data.ColumnSpec(1, "binary", None, None),
    )
    X = np.full((8, 2), np.nan)
    encoder = TypeAwareEncoder.fit(
        X,
        np.arange(len(X), dtype=np.float64),
        columns=columns,
        task_type=tabular_data.REGRESSION,
        n_classes=None,
    )
    assert np.all(np.isfinite(encoder.transform(X)))


def test_multiclass_target_encoding_uses_probability_vector():
    columns = (tabular_data.ColumnSpec(0, "categorical", 3, ("a", "b", "c")),)
    X = np.repeat(np.arange(3, dtype=np.float64), 6).reshape(-1, 1)
    y = np.tile(np.arange(3, dtype=int), 6)
    encoder = TypeAwareEncoder.fit(
        X,
        y,
        columns=columns,
        task_type=tabular_data.MULTICLASS,
        n_classes=3,
    )
    encoded = encoder.transform(X, use_oof=True)
    assert encoded.shape == (len(X), 5)
    assert np.allclose(encoded[:, 1:4].sum(axis=1), 1.0)
    assert np.all((encoded[:, 1:4] > 0.0) & (encoded[:, 1:4] < 1.0))


def test_regression_target_encoding_excludes_own_target():
    columns = (tabular_data.ColumnSpec(0, "categorical", 3, ("a", "b", "c")),)
    X = np.tile(np.arange(3, dtype=np.float64), 16).reshape(-1, 1)
    y = np.linspace(-1.0, 1.0, len(X))
    baseline = TypeAwareEncoder.fit(
        X,
        y,
        columns=columns,
        task_type=tabular_data.REGRESSION,
        n_classes=None,
        seed=0,
    ).transform(X, use_oof=True)
    perturbed_y = y.copy()
    perturbed_y[7] += 100.0
    perturbed = TypeAwareEncoder.fit(
        X,
        perturbed_y,
        columns=columns,
        task_type=tabular_data.REGRESSION,
        n_classes=None,
        seed=0,
    ).transform(X, use_oof=True)
    assert np.allclose(baseline[7], perturbed[7])


def test_ops_registry_contains_catalog():
    for op in (
        "identity",
        "standardize",
        "quantile",
        "affine_activation",
        "rbf_features",
        "pairwise_product",
        "column_gate",
    ):
        assert get_operator(op).op == op


def test_execute_empty_graph_on_synthetic_data():
    graph = _baseline()
    columns = _synthetic_columns()
    X, y = _synthetic_xy(n=64)
    readout, _ = execute_graph_triplet(
        graph,
        X,
        X[:0],
        X[:8],
        y_fit=y,
        columns=columns,
        task_type=tabular_data.REGRESSION,
        n_classes=None,
    )
    assert readout.fit.shape[0] == len(X)
    assert readout.query.shape[0] == 8
    assert np.all(np.isfinite(readout.query))


def test_split_invariant_holds_for_baseline_on_synthetic_data():
    graph = _baseline()
    columns = _synthetic_columns()
    X, y = _synthetic_xy(n=128)
    assert_split_invariant(
        graph,
        X,
        y_fit=y,
        columns=columns,
        task_type=tabular_data.REGRESSION,
        n_classes=None,
    )


def test_supervised_ridge_node_uses_cross_fitted_train_features():
    graph = PredictorGraph.model_validate(
        {
            "schema_version": 1,
            "nodes": [
                {
                    "id": "supervised",
                    "op": "affine_activation",
                    "inputs": ["raw"],
                    "params": {
                        "fit": "supervised_ridge",
                        "activation": "identity",
                        "n_components": 3,
                        "alpha": 1.0,
                        "seed": 0,
                    },
                    "is_readout": True,
                }
            ],
            "readout": {"kind": "ridge", "alpha": 1.0, "include_raw": False},
        }
    )
    columns = (
        tabular_data.ColumnSpec(0, "numeric", None, None),
        tabular_data.ColumnSpec(1, "numeric", None, None),
    )
    X, y = _synthetic_xy(n=96)
    X = X[:, :2]
    assert_split_invariant(
        graph,
        X,
        y_fit=y,
        columns=columns,
        task_type=tabular_data.REGRESSION,
        n_classes=None,
    )
    readout, _ = execute_graph_triplet(
        graph,
        X,
        X[:0],
        X[:7],
        y_fit=y,
        columns=columns,
        task_type=tabular_data.REGRESSION,
        n_classes=None,
    )
    assert readout.fit.shape == (len(X), 3)
    assert readout.query.shape == (7, 3)


def test_readout_ridge_predicts_regression():
    X, y = _synthetic_xy(n=64)
    state = fit_readout(
        X,
        y,
        config=_baseline().readout,
        task_type=tabular_data.REGRESSION,
        n_classes=None,
    )
    pred = predict_readout(
        state,
        X[:8],
        task_type=tabular_data.REGRESSION,
        n_classes=None,
    )
    assert pred.shape == (8,)
    assert np.all(np.isfinite(pred))


def test_allowed_changes_keeps_parent_node():
    graph = PredictorGraph.model_validate(
        {
            "schema_version": 1,
            "nodes": [
                {
                    "id": "std",
                    "op": "standardize",
                    "inputs": ["raw"],
                    "params": {},
                    "is_readout": True,
                    "rationale": "Normalize.",
                }
            ],
        }
    )
    parent = graph.to_json()
    diff_model = AllowedTabWpfChanges(min_nodes=0, max_nodes=12).build_schema(
        {"p0": parent}
    ).validate(
        {
            "base_parent": "p0",
            "structural_intent": "local_edit",
            "archetype": "Guided Innovation",
            "justification": "unit test",
            "nodes": [
                {
                    "kind": "keep",
                    "id": "std",
                    "edits": {"gate": 0.5},
                }
            ],
        }
    )
    child = AllowedTabWpfChanges().apply(diff_model, {"p0": parent})
    parsed = PredictorGraph.model_validate_json(child)
    assert parsed.nodes[0].gate == 0.5


def test_structured_diff_schema_rejects_params_from_another_operator():
    parent = _baseline().to_json()
    schema = AllowedTabWpfChanges().build_schema({"p0": parent})
    payload = {
        "base_parent": "p0",
        "structural_intent": "local_edit",
        "archetype": "Guided Innovation",
        "justification": "schema must reject semantically invalid params",
        "nodes": [
            {
                "kind": "new",
                "id": "scaled",
                "op": "standardize",
                "inputs": ["raw"],
                "params": {"seed": 7},
                "is_readout": True,
            }
        ],
    }

    with pytest.raises(ValidationError):
        schema.validate(payload)


def test_structured_diff_schema_accepts_operator_specific_params():
    parent = _baseline().to_json()
    schema = AllowedTabWpfChanges().build_schema({"p0": parent})
    payload = {
        "base_parent": "p0",
        "structural_intent": "local_edit",
        "archetype": "Guided Innovation",
        "justification": "valid RBF parameters",
        "nodes": [
            {
                "kind": "new",
                "id": "rbf",
                "op": "rbf_features",
                "inputs": ["raw"],
                "params": {"seed": 7, "n_components": 12, "lengthscale": 0.8},
                "is_readout": True,
            }
        ],
    }

    validated = schema.validate(payload)
    child = AllowedTabWpfChanges().apply(validated, {"p0": parent})
    parsed = PredictorGraph.model_validate_json(child)
    assert parsed.nodes[0].params == {
        "seed": 7,
        "n_components": 12,
        "lengthscale": 0.8,
    }


def test_structured_diff_cannot_mutate_task_determined_readout_kind():
    parent = _baseline().to_json()
    schema = AllowedTabWpfChanges().build_schema({"p0": parent})
    payload = {
        "base_parent": "p0",
        "structural_intent": "local_edit",
        "archetype": "Guided Innovation",
        "justification": "readout family is fixed by task type",
        "nodes": [],
        "readout_change": {
            "kind": "set",
            "readout_kind": "logistic",
            "alpha": 0.5,
            "include_raw": True,
        },
    }
    with pytest.raises(ValidationError):
        schema.validate(payload)


def test_structured_diff_readout_set_keeps_parent_kind():
    parent = _baseline().to_json()
    changes = AllowedTabWpfChanges()
    validated = changes.build_schema({"p0": parent}).validate(
        {
            "base_parent": "p0",
            "structural_intent": "local_edit",
            "archetype": "Guided Innovation",
            "justification": "tune only live readout fields",
            "nodes": [],
            "readout_change": {
                "kind": "set",
                "alpha": 0.5,
                "include_raw": True,
            },
        }
    )
    child = PredictorGraph.model_validate_json(changes.apply(validated, {"p0": parent}))
    assert child.readout.kind == "ridge"
    assert child.readout.alpha == 0.5


def test_extend_chain_from_empty_seed_accepts_one_node_depth():
    parent = _baseline().to_json()
    schema = AllowedTabWpfChanges().build_schema({"p0": parent})
    payload = {
        "base_parent": "p0",
        "structural_intent": "extend_chain",
        "archetype": "Guided Innovation",
        "justification": "the first operator extends an empty graph",
        "nodes": [
            {
                "kind": "new",
                "id": "scaled",
                "op": "standardize",
                "inputs": ["raw"],
                "params": {},
                "is_readout": True,
            }
        ],
    }

    validated = schema.validate(payload)
    child = AllowedTabWpfChanges().apply(validated, {"p0": parent})
    assert PredictorGraph.model_validate_json(child).depth == 1


def test_compose_chain_still_requires_two_consumed_levels():
    parent = _baseline().to_json()
    schema = AllowedTabWpfChanges().build_schema({"p0": parent})
    payload = {
        "base_parent": "p0",
        "structural_intent": "compose_chain",
        "archetype": "Guided Innovation",
        "justification": "one node is not a composed chain",
        "nodes": [
            {
                "kind": "new",
                "id": "scaled",
                "op": "standardize",
                "inputs": ["raw"],
                "params": {},
                "is_readout": True,
            }
        ],
    }

    validated = schema.validate(payload)
    with pytest.raises(Exception, match="requires child depth >= 2"):
        AllowedTabWpfChanges().apply(validated, {"p0": parent})


def test_tab_wpf_config_uses_json_loader_and_structured_diff():
    with initialize_config_dir(config_dir=str(CONFIG_DIR), version_base=None):
        cfg = compose(
            config_name="config",
            overrides=[
                "experiment=tab_wpf",
            ],
        )

    assert cfg.problem.name == "tab_wpf"
    assert get_class(cfg.program_loader._target_).__name__ == "TabWpfSeedLoader"
    assert get_class(cfg.problem_context._target_).__name__ == "TabWpfProblemContext"
    assert get_class(cfg.mutation_operator.allowed_changes._target_).__name__ == (
        "AllowedTabWpfChanges"
    )


def test_tab_wpf_problem_context_does_not_enable_add_context_stage():
    problem_dir = ROOT / "problems" / "tab_wpf"
    problem_context = TabWpfProblemContext(problem_dir, dataset="california")
    context = EvolutionContext(
        problem_ctx=problem_context,
        llm_wrapper=MagicMock(spec=MultiModelRouter),
        storage=MagicMock(spec=ProgramStorage),
        memory_provider=NullMemoryProvider(),
    )
    blueprint = DefaultPipelineBuilder(
        context,
        program_format_feature=JsonDocumentEvaluationFeature(),
    ).build_blueprint()
    assert problem_context.is_contextual is False
    assert "AddContext" not in blueprint.nodes
