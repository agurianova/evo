"""Canonical JSON genome for reverse-SCM tabular predictor DAGs."""

from __future__ import annotations

import json
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

OperatorKind = Literal[
    "identity",
    "standardize",
    "quantile",
    "affine_activation",
    "rbf_features",
    "pairwise_product",
    "column_gate",
]

ActivationKind = Literal["tanh", "leaky_relu", "elu", "identity"]
AffineFitKind = Literal["pca", "supervised_ridge"]
ReadoutKind = Literal["ridge", "logistic"]

RAW_INPUT = "raw"

_OPERATOR_PARAM_KEYS: dict[str, set[str]] = {
    "identity": set(),
    "standardize": set(),
    "quantile": {"seed", "n_quantiles", "output_distribution"},
    "affine_activation": {"seed", "fit", "activation", "n_components", "alpha"},
    "rbf_features": {"seed", "n_components", "lengthscale"},
    "pairwise_product": {"seed", "k"},
    "column_gate": {"seed", "k"},
}


class OperatorNode(BaseModel):
    """One closed-catalog operator in topological graph order."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        min_length=1,
        pattern=r"^[A-Za-z][A-Za-z0-9_]*$",
        description="Stable semantic name for the operator node.",
    )
    op: OperatorKind = Field(description="Closed operator from the TabPFN-inspired catalog.")
    inputs: list[str] = Field(
        min_length=1,
        description='Parent node ids or the reserved "raw" encoder output.',
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Operator hyperparameters; unknown keys are rejected at execution.",
    )
    gate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Evolutionary contribution weight for readout features from this node.",
    )
    is_readout: bool = Field(
        default=False,
        description="Whether this node's outputs are concatenated into the readout matrix.",
    )
    rationale: str = Field(
        default="",
        max_length=1000,
        description="Short hypothesis for why this operator helps prediction.",
    )

    @model_validator(mode="after")
    def validate_local_uniqueness(self) -> Self:
        if len(self.inputs) != len(set(self.inputs)):
            raise ValueError(f"node {self.id}: duplicate inputs")
        unknown = set(self.params) - _OPERATOR_PARAM_KEYS[self.op]
        if unknown:
            raise ValueError(
                f"node {self.id}: unknown params for {self.op}: {sorted(unknown)}"
            )
        _validate_operator_params(self)
        return self


class ReadoutConfig(BaseModel):
    """Final linear readout over selected DAG channels."""

    model_config = ConfigDict(extra="forbid")

    kind: ReadoutKind = Field(default="ridge")
    alpha: float = Field(default=1.0, gt=0.0, le=1000.0)
    include_raw: bool = Field(
        default=True,
        description="Whether encoded raw features are concatenated into the readout matrix.",
    )


class PredictorGraph(BaseModel):
    """Feature-agnostic reverse-SCM predictor graph."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(default=1, ge=1, le=1)
    nodes: list[OperatorNode] = Field(default_factory=list, max_length=16)
    readout: ReadoutConfig = Field(default_factory=ReadoutConfig)

    @model_validator(mode="after")
    def validate_graph(self) -> Self:
        node_ids: set[str] = set()
        available = {RAW_INPUT}
        supervised_ancestors: dict[str, bool] = {RAW_INPUT: False}

        for node in self.nodes:
            if node.id in node_ids:
                raise ValueError(f"duplicate node id {node.id!r}")
            missing_inputs = set(node.inputs) - available
            if missing_inputs:
                raise ValueError(
                    f"node {node.id}: unavailable inputs {sorted(missing_inputs)}"
                )
            parent_is_supervised = any(
                supervised_ancestors[parent] for parent in node.inputs
            )
            node_is_supervised = _uses_supervision(node)
            if node_is_supervised and parent_is_supervised:
                raise ValueError(
                    f"node {node.id}: supervised operators cannot consume another "
                    "supervised operator in schema v1; nested cross-fitting is not "
                    "implemented"
                )
            node_ids.add(node.id)
            available.add(node.id)
            supervised_ancestors[node.id] = parent_is_supervised or node_is_supervised

        productive = {node.id for node in self.nodes if node.is_readout}
        for node in reversed(self.nodes):
            if node.id in productive:
                productive.update(self._consumed_parents(node))
        dead_nodes = node_ids - productive
        if dead_nodes:
            raise ValueError(
                "nodes do not contribute to the final readout: "
                f"{sorted(dead_nodes)}"
            )
        if not self.readout.include_raw and not productive:
            raise ValueError(
                "readout has no inputs: include_raw is false and no node is_readout"
            )

        return self

    def _consumed_parents(self, node: OperatorNode) -> list[str]:
        return [parent for parent in node.inputs if parent != RAW_INPUT]

    @property
    def depth(self) -> int:
        depths: dict[str, int] = {RAW_INPUT: 0}
        for node in self.nodes:
            parent_depths = [depths[parent] for parent in node.inputs]
            depths[node.id] = 1 + max(parent_depths, default=0)
        return max((depths[node.id] for node in self.nodes), default=0)

    @property
    def readout_nodes(self) -> list[OperatorNode]:
        return [node for node in self.nodes if node.is_readout]

    def to_json(self) -> str:
        return json.dumps(self.model_dump(mode="json"), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, text: str) -> PredictorGraph:
        return cls.model_validate_json(text)


def _validate_operator_params(node: OperatorNode) -> None:
    params = node.params
    if "seed" in params and (
        isinstance(params["seed"], bool) or not isinstance(params["seed"], int)
    ):
        raise ValueError(f"node {node.id}: seed must be an integer")

    for name in ("n_quantiles", "n_components", "k"):
        if name in params and (
            isinstance(params[name], bool)
            or not isinstance(params[name], int)
            or params[name] <= 0
        ):
            raise ValueError(f"node {node.id}: {name} must be a positive integer")
    upper_bounds = {"n_quantiles": 2048, "n_components": 128, "k": 128}
    for name, upper_bound in upper_bounds.items():
        if name in params and params[name] > upper_bound:
            raise ValueError(f"node {node.id}: {name} must be <= {upper_bound}")

    for name in ("alpha", "lengthscale"):
        if name in params and (
            isinstance(params[name], bool)
            or not isinstance(params[name], (int, float))
            or not 0.0 < float(params[name]) <= 1e6
        ):
            raise ValueError(f"node {node.id}: {name} must be in (0, 1e6]")

    if "fit" in params and params["fit"] not in {"pca", "supervised_ridge"}:
        raise ValueError(f"node {node.id}: unknown affine fit mode {params['fit']!r}")
    if "activation" in params and params["activation"] not in {
        "tanh",
        "leaky_relu",
        "elu",
        "identity",
    }:
        raise ValueError(f"node {node.id}: unknown activation {params['activation']!r}")
    if "output_distribution" in params and params["output_distribution"] not in {
        "normal",
        "uniform",
    }:
        raise ValueError(
            f"node {node.id}: output_distribution must be 'normal' or 'uniform'"
        )


def _uses_supervision(node: OperatorNode) -> bool:
    if node.op == "column_gate":
        return True
    return node.op == "affine_activation" and node.params.get("fit", "pca") == "supervised_ridge"
