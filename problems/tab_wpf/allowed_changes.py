"""Schema-constrained mutations for reverse-SCM predictor graph JSON genomes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Literal

from loguru import logger
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    create_model,
)

from gigaevo.evolution.mutation.allowed_changes import (
    AllowedChanges,
    DiffSchema,
    DiffStructuredOutputBase,
)
from gigaevo.exceptions import MutationError
from gigaevo.llm.schema_compat import portable_json_schema
from problems.tab_wpf.graph import OperatorKind, OperatorNode, PredictorGraph, ReadoutConfig


class ReadoutKeep(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["keep"]


class ReadoutSet(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["set"]
    alpha: float = Field(default=1.0, gt=0.0, le=1000.0)
    include_raw: bool = True


class TabWpfDiffBase(DiffStructuredOutputBase):
    structural_intent: Literal[
        "local_edit", "extend_chain", "compose_chain", "simplify_graph"
    ] = Field(
        description=(
            "Topology intent. extend_chain must increase parent depth; "
            "compose_chain must reach depth >= 2."
        )
    )
    readout_change: ReadoutKeep | ReadoutSet | None = Field(
        default=None,
        description="Null/keep preserves the base readout; set replaces it.",
    )


_RATIONALE_MAX_LENGTH = 500
_OPERATOR_DESCRIPTION = (
    "Closed TabPFN-inspired operator. identity passes inputs; standardize z-scores; "
    "quantile rank-transforms; affine_activation applies linear mix + activation with "
    "fit=pca or fit=supervised_ridge; rbf_features adds GP-style random Fourier "
    "features; pairwise_product multiplies selected column pairs; column_gate keeps "
    "top-k columns by OOF |corr| with y_fit."
)
_INPUTS_DESCRIPTION = (
    'Complete parent list using earlier node ids and/or the reserved "raw" encoder output.'
)


class NoOperatorParams(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuantileParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = 0
    n_quantiles: int = Field(default=32, gt=0, le=2048)
    output_distribution: Literal["normal", "uniform"] = "normal"


class AffineActivationParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = 0
    fit: Literal["pca", "supervised_ridge"] = "pca"
    activation: Literal["tanh", "leaky_relu", "elu", "identity"] = "tanh"
    n_components: int = Field(default=8, gt=0, le=128)
    alpha: float = Field(default=1.0, gt=0.0, le=1e6)


class RbfParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = 0
    n_components: int = Field(default=16, gt=0, le=128)
    lengthscale: float = Field(default=1.0, gt=0.0, le=1e6)


class PairwiseParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = 0
    k: int = Field(default=8, gt=0, le=128)


class ColumnGateParams(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int = 0
    k: int = Field(default=8, gt=0, le=128)


_PARAM_MODELS: dict[OperatorKind, type[BaseModel]] = {
    "identity": NoOperatorParams,
    "standardize": NoOperatorParams,
    "quantile": QuantileParams,
    "affine_activation": AffineActivationParams,
    "rbf_features": RbfParams,
    "pairwise_product": PairwiseParams,
    "column_gate": ColumnGateParams,
}


def _new_node_models() -> list[type[BaseModel]]:
    models: list[type[BaseModel]] = []
    for op, params_model in _PARAM_MODELS.items():
        models.append(
            create_model(
                f"New{op.title().replace('_', '')}Node",
                __config__=ConfigDict(extra="forbid"),
                kind=(
                    Literal["new"],
                    Field(..., description="Create a new operator node."),
                ),
                id=(
                    str,
                    Field(
                        ...,
                        min_length=1,
                        pattern=r"^[A-Za-z][A-Za-z0-9_]*$",
                        description=(
                            "Dependency label; child id is deterministically uniquified."
                        ),
                    ),
                ),
                op=(Literal[op], Field(..., description=_OPERATOR_DESCRIPTION)),
                inputs=(
                    list[str],
                    Field(..., min_length=1, description=_INPUTS_DESCRIPTION),
                ),
                params=(params_model, Field(default_factory=params_model)),
                gate=(float, Field(default=1.0, ge=0.0, le=1.0)),
                is_readout=(
                    bool,
                    Field(
                        default=True,
                        description=(
                            "Export this node to the final readout. Set false only when "
                            "a later node consumes it and contributes to the readout."
                        ),
                    ),
                ),
                rationale=(
                    str,
                    Field(default="", max_length=_RATIONALE_MAX_LENGTH),
                ),
            ),
        ),
    return models


def _keep_edits_model(node: OperatorNode) -> type[BaseModel]:
    params_model = _PARAM_MODELS[node.op]
    return create_model(
        f"Keep{node.id.title().replace('_', '')}Edits",
        __config__=ConfigDict(extra="forbid"),
        inputs=(list[str] | None, Field(default=None, min_length=1)),
        params=(params_model | None, None),
        gate=(float | None, Field(default=None, ge=0.0, le=1.0)),
        is_readout=(bool | None, None),
        rationale=(str | None, Field(default=None, max_length=_RATIONALE_MAX_LENGTH)),
    )


def _node_entry_model(parent_nodes: tuple[OperatorNode, ...]):
    forms: list[Any] = []
    for node in parent_nodes:
        edits_model = _keep_edits_model(node)
        forms.insert(
            len(forms),
            create_model(
                f"Keep{node.id.title().replace('_', '')}Node",
                __config__=ConfigDict(extra="forbid"),
                kind=(Literal["keep"], Field(..., description="Reuse a parent node.")),
                id=(Literal[node.id], Field(...)),
                edits=(edits_model, Field(default_factory=edits_model)),
            ),
        )
    forms.extend(_new_node_models())
    entry: Any = forms[0]
    for form in forms[1:]:
        entry |= form
    return entry


class AllowedTabWpfChanges(AllowedChanges):
    """Compile a structured full-child diff into a validated PredictorGraph JSON."""

    def __init__(self, *, min_nodes: int = 0, max_nodes: int = 12):
        if not 0 <= min_nodes <= max_nodes <= 16:
            raise ValueError(
                f"invalid node bounds: min={min_nodes} max={max_nodes}; maximum is 16"
            )
        self.min_nodes = min_nodes
        self.max_nodes = max_nodes

    def build_schema(self, parents: dict[str, str]) -> DiffSchema:
        graphs = self._parse(parents)
        adapter = TypeAdapter(self._diff_model(graphs))
        schema = portable_json_schema(
            {**adapter.json_schema(), "title": "tab_wpf_predictor_graph_diff"}
        )

        def validate(payload: Any) -> Any:
            try:
                return adapter.validate_python(payload)
            except ValidationError as original:
                repaired = self._repair_payload(payload)
                if repaired is None:
                    raise
                try:
                    validated = adapter.validate_python(repaired)
                except ValidationError:
                    raise original
                logger.warning("tab_wpf_predictor_graph_diff: truncated overlong rationale")
                return validated

        return DiffSchema(json_schema=schema, validate=validate)

    @staticmethod
    def _repair_payload(payload: Any) -> dict | None:
        if not isinstance(payload, dict):
            return None
        repaired = deepcopy(payload)
        changed = False
        nodes = repaired.get("nodes")
        if not isinstance(nodes, list):
            return None
        for node in nodes:
            if not isinstance(node, dict):
                continue
            rationale_owner = node.get("edits") if node.get("kind") == "keep" else node
            if not isinstance(rationale_owner, dict):
                continue
            rationale = rationale_owner.get("rationale")
            if isinstance(rationale, str) and len(rationale) > _RATIONALE_MAX_LENGTH:
                rationale_owner["rationale"] = rationale[:_RATIONALE_MAX_LENGTH].rstrip()
                changed = True
        return repaired if changed else None

    @staticmethod
    def _addressed_nodes(graphs: dict[str, PredictorGraph]) -> dict[str, list]:
        qualify_ids = len(graphs) > 1
        addressed: dict[str, list] = {}
        for namespace, graph in graphs.items():
            addressed[namespace] = [
                node.model_copy(
                    update={"id": f"{namespace}_{node.id}" if qualify_ids else node.id}
                )
                for node in graph.nodes
            ]
        return addressed

    def render_parents(self, parents: dict[str, str]) -> str:
        graphs = self._parse(parents)
        addressed = self._addressed_nodes(graphs)
        blocks: list[str] = []
        for namespace, graph in graphs.items():
            lines = [
                f"=== Parent {namespace} ===",
                f"readout: {graph.readout.model_dump()}",
            ]
            for node in addressed[namespace]:
                lines.extend(
                    [
                        f"id={node.id} | op={node.op} | inputs={node.inputs} | "
                        f"params={node.params} | gate={node.gate} | is_readout={node.is_readout}",
                        f"    rationale: {node.rationale}",
                    ]
                )
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    def apply(self, diff: Any, parents: dict[str, str]) -> str:
        graphs = self._parse(parents)
        try:
            if len(diff.nodes) > self.max_nodes:
                raise ValueError(
                    f"child graph has {len(diff.nodes)} nodes but at most "
                    f"{self.max_nodes} are allowed"
                )
            child = self._transcribe(diff, graphs)
            reparsed = PredictorGraph.model_validate_json(child.to_json())
        except MutationError:
            raise
        except Exception as exc:
            raise MutationError(f"diff_apply_assertion: {exc}") from exc
        return reparsed.to_json()

    def describe(self) -> str:
        return (
            "TAB-WPF PREDICTOR-GRAPH DIFF\n"
            "- nodes is the complete child in topological order; omitted parent nodes are deleted.\n"
            '- inputs may reference earlier node ids or the reserved "raw" encoder output.\n'
            "- kind=keep reuses a parent node; kind=new creates a closed-catalog operator.\n"
            "- gate scales a node's readout contribution in [0, 1].\n"
            "- every node must feed a later readout node or set is_readout=true; dead nodes are rejected.\n"
            "- readout_change can keep or set alpha and include_raw; the evaluator "
            "fixes ridge for regression and logistic for classification.\n"
            "- structural_intent is verified against the child's consumed-input depth.\n"
            "- params must use only operator-specific keys documented in task_description.txt."
        )

    def _parse(self, parents: dict[str, str]) -> dict[str, PredictorGraph]:
        if not parents:
            raise MutationError("tab_wpf_validation_error: no parents provided")
        graphs: dict[str, PredictorGraph] = {}
        for namespace, code in parents.items():
            try:
                graphs[namespace] = PredictorGraph.model_validate_json(code)
            except Exception as exc:
                raise MutationError(
                    f"tab_wpf_validation_error: parent {namespace}: {exc}"
                ) from exc
        return graphs

    def _diff_model(self, graphs: dict[str, PredictorGraph]) -> type[TabWpfDiffBase]:
        addressed = self._addressed_nodes(graphs)
        all_nodes = tuple(node for nodes in addressed.values() for node in nodes)
        node_entry = _node_entry_model(all_nodes)
        return create_model(
            "TabWpfPredictorGraphDiff",
            __base__=TabWpfDiffBase,
            base_parent=(Literal[tuple(graphs)], ...),
            nodes=(
                list[node_entry],  # type: ignore[valid-type]
                Field(
                    ...,
                    min_length=self.min_nodes,
                    description=(
                        "Complete child graph in topological order, at most "
                        f"{self.max_nodes} nodes."
                    ),
                ),
            ),
        )

    def _transcribe(self, diff: TabWpfDiffBase, graphs: dict[str, PredictorGraph]) -> PredictorGraph:
        base = graphs[diff.base_parent]
        addressed = self._addressed_nodes(graphs)
        nodes_by_id = {node.id: node for nodes in addressed.values() for node in nodes}
        child_nodes = []
        emitted_node_ids: set[str] = set()
        child_id_by_entry_id: dict[str, str] = {}

        for entry in diff.nodes:
            if entry.kind == "keep":
                data = nodes_by_id[entry.id].model_dump()
                data.update(entry.edits.model_dump(exclude_none=True))
            else:
                data = entry.model_dump(
                    include={
                        "id",
                        "op",
                        "inputs",
                        "params",
                        "gate",
                        "is_readout",
                        "rationale",
                    }
                )

            requested_id = entry.id
            suffix = 2
            while data["id"] in emitted_node_ids:
                data["id"] = f"{requested_id}_{suffix}"
                suffix += 1

            available = {"raw", *child_id_by_entry_id.values()}
            missing = set(data["inputs"]) - available
            if missing:
                raise ValueError(
                    f"node {data['id']}: unavailable inputs {sorted(missing)}"
                )

            node = OperatorNode.model_validate(data)
            child_nodes.append(node)
            emitted_node_ids.add(node.id)
            child_id_by_entry_id[entry.id] = node.id

        readout = base.readout
        if diff.readout_change is not None and diff.readout_change.kind == "set":
            readout = ReadoutConfig(
                kind=base.readout.kind,
                alpha=diff.readout_change.alpha,
                include_raw=diff.readout_change.include_raw,
            )

        child = PredictorGraph(schema_version=1, nodes=child_nodes, readout=readout)
        if diff.structural_intent == "compose_chain":
            required_depth = 2
        elif diff.structural_intent == "extend_chain":
            required_depth = base.depth + 1
        else:
            required_depth = None
        if required_depth is not None and child.depth < required_depth:
            raise ValueError(
                f"structural_intent={diff.structural_intent} requires child depth "
                f">= {required_depth}, got {child.depth}"
            )
        return child
