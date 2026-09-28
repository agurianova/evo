"""One-operator-per-call mutations on the JSON genotype (TZ §6)."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np

from problems.pmhctcr.genotype import (
    BATCH_SIZES,
    HIDDEN_DIMS,
    INPUT_FLAGS,
    INTERACTION_PAIRS,
    MULTIMODAL_TYPES,
    NUM_HEADS,
    OPERATOR_IDS,
    SURFACE_METRICS,
    Genotype,
    ModelBody,
    SurfaceDerived,
    allowed_sequence_regions,
    functional_dumps,
    get_input_flag,
    n_active_inputs,
    pair_ok,
    sequence_on,
    set_input_flag,
    structure_on,
    surface_on,
)
from problems.pmhctcr.repair import (
    check_integrity,
    has_working_encoder,
    integrity_errors,
    repair,
)

EARLY_OPS = (
    "CHANGE_INPUT",
    "CHANGE_STRUCTURE",
    "CHANGE_MODEL",
    "CREATE_SURFACE",
    "CHANGE_SURFACE",
)
LATE_OPS = (
    "CHANGE_TRAINING",
    "CHANGE_OPTIMIZATION",
    "CHANGE_AUGMENTATION",
    "CHANGE_CALIBRATION",
)


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def _choice_other(rng: np.random.Generator, options: list[Any], current: Any) -> Any:
    others = [x for x in options if x != current]
    if not others:
        return current
    return others[int(rng.integers(0, len(others)))]


def _log_uniform(rng: np.random.Generator, lo: float, hi: float) -> float:
    return float(np.exp(rng.uniform(np.log(lo), np.log(hi))))


def is_applicable(g: Genotype, op: str) -> bool:
    if op in {
        "CHANGE_INPUT",
        "CHANGE_MODEL",
        "CHANGE_TRAINING",
        "CHANGE_AUGMENTATION",
        "CHANGE_OPTIMIZATION",
        "CHANGE_CALIBRATION",
        "NOOP",
    }:
        return True
    if op == "CHANGE_SEQUENCE":
        return sequence_on(g)
    if op == "CHANGE_STRUCTURE":
        return structure_on(g)
    if op == "CREATE_SURFACE":
        return not surface_on(g)
    if op == "CHANGE_SURFACE":
        return surface_on(g)
    if op == "CHANGE_INTERACTION":
        return True
    return False


def _change_input(g: Genotype, rng: np.random.Generator) -> None:
    active = [k for k in INPUT_FLAGS if get_input_flag(g, k)]
    inactive = [k for k in INPUT_FLAGS if not get_input_flag(g, k)]
    remove = bool(active) and (not inactive or rng.random() < 0.5)
    if remove and n_active_inputs(g) <= 1:
        remove = False
    if remove and active:
        set_input_flag(g, active[int(rng.integers(0, len(active)))], False)
        return
    if inactive:
        set_input_flag(g, inactive[int(rng.integers(0, len(inactive)))], True)


def _change_sequence(g: Genotype, rng: np.random.Generator) -> None:
    field = str(_choice_other(rng, ["region", "arch", "pooling"], None))
    enc = g.encoders.sequence
    if field == "region":
        opts = sorted(allowed_sequence_regions(g))
        enc.region = _choice_other(rng, opts, enc.region)
    elif field == "arch":
        enc.arch = _choice_other(rng, ["cnn", "transformer", "protein_lm"], enc.arch)
        enc.pretrained = enc.arch == "protein_lm"
        if enc.arch == "protein_lm":
            if g.model.type in {"seq_dual_encoder", "seq_cross_encoder"}:
                g.model.type = "mlp_features"  # type: ignore[assignment]
                g.model.ensemble_members = []
        elif g.model.type == "mlp_features":
            g.model.type = "seq_dual_encoder"  # type: ignore[assignment]
            g.model.ensemble_members = []
    else:
        enc.pooling = _choice_other(rng, ["mean", "attention"], enc.pooling)


def _change_structure(g: Genotype, rng: np.random.Generator) -> None:
    field = str(
        rng.choice(
            ["scope", "edges.type", "edges.k", "edges.radius_A", "arch", "pooling"]
        )
    )
    st = g.encoders.structure
    if field == "scope":
        if g.inputs.pdb.kind == "complex":
            st.scope = _choice_other(rng, ["full_complex", "interface"], st.scope)
        else:
            st.scope = "full_complex"
    elif field == "edges.type":
        st.edges.type = _choice_other(rng, ["radius", "knn"], st.edges.type)
    elif field == "edges.k":
        st.edges.type = "knn"
        st.edges.k = int(rng.integers(4, 33))
    elif field == "edges.radius_A":
        st.edges.type = "radius"
        st.edges.radius_A = float(rng.uniform(4.0, 15.0))
    elif field == "arch":
        st.arch = _choice_other(
            rng, ["gat", "mpnn", "egnn", "se3_transformer"], st.arch
        )
    else:
        st.pooling = _choice_other(rng, ["mean", "attention"], st.pooling)


def _enable_masif(g: Genotype) -> None:
    """Turn on both ImmRep25 MaSIF views (TCR direct + pMHC flipped)."""
    g.inputs.masif.tcr_direct = True
    g.inputs.masif.pmhc_flipped = True


def _create_surface(g: Genotype, rng: np.random.Generator) -> None:
    _enable_masif(g)


def _change_surface(g: Genotype, rng: np.random.Generator) -> None:
    su = g.encoders.surface
    if not su.spots.enabled:
        su.spots.enabled = True
        return
    field = str(
        rng.choice(
            [
                "threshold",
                "metric",
                "linkage_A",
                "derived",
                "patch_boundary",
                "patch_radius_A",
                "metrics",
                "topk",
            ]
        )
    )
    if field == "threshold":
        su.spots.threshold = (
            float(rng.uniform(1.2, 2.4))
            if su.spots.metric == "l2"
            else float(rng.uniform(0.5, 0.85))
        )
        return
    if field == "metric":
        su.spots.metric = _choice_other(rng, ["l2", "cosine"], su.spots.metric)
        if su.spots.metric == "l2" and su.spots.threshold >= 1.0:
            pass
        elif su.spots.metric == "cosine" and su.spots.threshold >= 1.0:
            su.spots.threshold = 0.5
        return
    if field == "linkage_A":
        su.spots.linkage_A = float(rng.uniform(1.2, 3.0))
        return
    if field == "derived":
        from problems.pmhctcr.spots import SPOT_CORE

        current = list(su.spots.derived)
        if current and rng.random() < 0.35:
            current.pop(int(rng.integers(0, len(current))))
        elif len(current) < 8:
            a = str(SPOT_CORE[int(rng.integers(0, len(SPOT_CORE)))])
            b = str(SPOT_CORE[int(rng.integers(0, len(SPOT_CORE)))])
            op = str(rng.choice(["ratio", "diff", "product"]))
            current.append(SurfaceDerived(op=op, a=a, b=b))  # type: ignore[arg-type]
        su.spots.derived = current
        return
    if field == "patch_boundary":
        su.patch_boundary = _choice_other(
            rng, ["nn_radius", "nn_learned"], su.patch_boundary
        )
        return
    if field == "patch_radius_A":
        su.patch_radius_A = float(rng.uniform(6.0, 20.0))
        return
    if field == "topk":
        su.topk = int(rng.integers(3, 51))
        return
    current = list(su.metrics)
    if len(current) > 1 and rng.random() < 0.5:
        current.pop(int(rng.integers(0, len(current))))
    else:
        missing = [m for m in SURFACE_METRICS if m not in current]
        if missing:
            current.append(missing[int(rng.integers(0, len(missing)))])
        elif len(current) > 1:
            current.pop(int(rng.integers(0, len(current))))
    su.metrics = current  # type: ignore[assignment]


def _change_interaction(g: Genotype, rng: np.random.Generator) -> None:
    aspect = str(rng.choice(["pairs_add", "pairs_remove", "method", "fusion"]))
    pairs = list(g.interaction.pairs)
    if aspect == "pairs_add":
        candidates = [p for p in INTERACTION_PAIRS if p not in pairs and pair_ok(g, p)]
        if not candidates:
            return
        pairs.append(candidates[int(rng.integers(0, len(candidates)))])
        g.interaction.pairs = pairs  # type: ignore[assignment]
        if g.interaction.method is None:
            g.interaction.method = "product"
        if g.interaction.fusion is None:
            g.interaction.fusion = "concat"
        return
    if aspect == "pairs_remove":
        if not pairs:
            return
        pairs.pop(int(rng.integers(0, len(pairs))))
        g.interaction.pairs = pairs  # type: ignore[assignment]
        return
    if not pairs:
        return
    if aspect == "method":
        g.interaction.method = _choice_other(
            rng,
            ["product", "abs_diff", "bilinear", "cross_attention"],
            g.interaction.method,
        )
        if (
            g.interaction.method == "cross_attention"
            and g.encoders.sequence.arch != "protein_lm"
        ):
            if g.model.type == "mlp_features" and sequence_on(g):
                g.model.type = "seq_cross_encoder"  # type: ignore[assignment]
                g.model.ensemble_members = []
    else:
        g.interaction.fusion = _choice_other(
            rng, ["concat", "gated_sum", "cross_attention"], g.interaction.fusion
        )
        if (
            g.interaction.fusion == "cross_attention"
            and g.encoders.sequence.arch != "protein_lm"
        ):
            if g.model.type == "mlp_features" and sequence_on(g):
                g.model.type = "seq_cross_encoder"  # type: ignore[assignment]
                g.model.ensemble_members = []


def _compatible_heads(hidden_dim: int) -> list[int]:
    return [h for h in NUM_HEADS if hidden_dim % h == 0]


def _change_model(g: Genotype, rng: np.random.Generator) -> None:
    field = str(
        rng.choice(
            ["type", "hidden_dim", "num_layers", "num_heads", "dropout", "residual"]
        )
    )
    m = g.model
    if field == "type":
        mods = sum((sequence_on(g), structure_on(g), surface_on(g)))
        allowed = [
            t
            for t in (
                "mlp_features",
                "seq_dual_encoder",
                "seq_cross_encoder",
                "pdb_gnn",
                "masif_siamese",
                "masif_patch_cross_attn",
                "multimodal_mlp",
                "multimodal_gated",
                "multimodal_cross_attn",
                "ensemble",
            )
            if t != m.type
        ]
        if mods < 2:
            allowed = [t for t in allowed if t not in MULTIMODAL_TYPES]
        if not sequence_on(g):
            allowed = [
                t for t in allowed if t not in {"seq_dual_encoder", "seq_cross_encoder"}
            ]
        if not structure_on(g):
            allowed = [t for t in allowed if t != "pdb_gnn"]
        if not surface_on(g):
            allowed = [
                t
                for t in allowed
                if t not in {"masif_siamese", "masif_patch_cross_attn"}
            ]
        if not allowed:
            return
        new_type = allowed[int(rng.integers(0, len(allowed)))]
        m.type = new_type  # type: ignore[assignment]
        if new_type == "ensemble":
            a = ModelBody(
                type="mlp_features", hidden_dim=m.hidden_dim, num_heads=m.num_heads
            )
            b_type = "seq_dual_encoder" if sequence_on(g) else "mlp_features"
            if b_type == "mlp_features":
                b_type = "pdb_gnn" if structure_on(g) else "mlp_features"
            b = ModelBody(type=b_type, hidden_dim=m.hidden_dim, num_heads=m.num_heads)
            if a.type == b.type:
                b = ModelBody(type="mlp_features", hidden_dim=64, num_heads=4)
            m.ensemble_members = [a, b]
        else:
            m.ensemble_members = []
        return
    if field == "hidden_dim":
        m.hidden_dim = _choice_other(rng, list(HIDDEN_DIMS), m.hidden_dim)
        heads = _compatible_heads(m.hidden_dim)
        if m.num_heads not in heads:
            m.num_heads = heads[-1]  # type: ignore[assignment]
        return
    if field == "num_layers":
        m.num_layers = int(_choice_other(rng, list(range(1, 7)), m.num_layers))
        return
    if field == "num_heads":
        m.num_heads = _choice_other(rng, _compatible_heads(m.hidden_dim), m.num_heads)
        return
    if field == "dropout":
        m.dropout = float(rng.uniform(0.0, 0.5))
        return
    m.residual = not m.residual


def _change_training(g: Genotype, rng: np.random.Generator) -> None:
    fields = ["loss", "sampling", "lr", "weight_decay"]
    if g.training.loss == "focal":
        fields.append("focal_gamma")
    if g.training.sampling == "hard_negative":
        fields.append("hard_negative_ratio")
    field = str(rng.choice(fields))
    t = g.training
    if field == "loss":
        t.loss = _choice_other(rng, ["bce", "focal", "contrastive"], t.loss)
        if t.loss == "focal" and t.focal_gamma is None:
            t.focal_gamma = 2.0
        return
    if field == "focal_gamma":
        t.focal_gamma = float(rng.uniform(0.5, 5.0))
        return
    if field == "sampling":
        t.sampling = _choice_other(rng, ["random", "hard_negative"], t.sampling)
        return
    if field == "hard_negative_ratio":
        t.hard_negative_ratio = float(rng.uniform(0.0, 0.8))
        return
    if field == "lr":
        t.lr = _log_uniform(rng, 1e-5, 1e-2)
        return
    if rng.random() < 0.15:
        t.weight_decay = 0.0
    else:
        t.weight_decay = _log_uniform(rng, 1e-8, 1e-2)


def _change_augmentation(g: Genotype, rng: np.random.Generator) -> None:
    if rng.random() < 0.5:
        g.training.augmentation.seq_mask_p = float(rng.uniform(0.0, 0.3))
    else:
        g.training.augmentation.structure_edge_dropout_p = float(rng.uniform(0.0, 0.3))


def _change_optimization(g: Genotype, rng: np.random.Generator) -> None:
    field = str(rng.choice(["optimizer", "scheduler", "batch_size"]))
    t = g.training
    if field == "optimizer":
        t.optimizer = _choice_other(rng, ["adamw", "adam", "sgd"], t.optimizer)
    elif field == "scheduler":
        t.scheduler = _choice_other(rng, ["none", "cosine", "step"], t.scheduler)
    else:
        t.batch_size = _choice_other(rng, list(BATCH_SIZES), t.batch_size)


def _change_calibration(g: Genotype, rng: np.random.Generator) -> None:
    g.calibration.temperature = float(rng.uniform(0.5, 3.0))


_APPLY = {
    "CHANGE_INPUT": _change_input,
    "CHANGE_SEQUENCE": _change_sequence,
    "CHANGE_STRUCTURE": _change_structure,
    "CREATE_SURFACE": _create_surface,
    "CHANGE_SURFACE": _change_surface,
    "CHANGE_INTERACTION": _change_interaction,
    "CHANGE_MODEL": _change_model,
    "CHANGE_TRAINING": _change_training,
    "CHANGE_AUGMENTATION": _change_augmentation,
    "CHANGE_OPTIMIZATION": _change_optimization,
    "CHANGE_CALIBRATION": _change_calibration,
}


def apply_operator(
    parent: Genotype,
    operator_id: str,
    *,
    rng: np.random.Generator | None = None,
    new_seed: int | None = None,
    guided_text: str | None = None,
) -> Genotype:
    if operator_id not in OPERATOR_IDS:
        raise ValueError(f"unknown operator {operator_id}")
    parent_key = functional_dumps(parent)
    child = deepcopy(parent)
    child.meta.parent_id = None
    gen_rng = rng or _rng(parent.seed + 17 * (parent.meta.generation + 1))
    if operator_id == "NOOP":
        child.meta.operator_applied = "NOOP"
        child.meta.generation = parent.meta.generation + 1
        if new_seed is not None:
            child.seed = int(new_seed)
        return child
    if not is_applicable(parent, operator_id):
        child.meta.operator_applied = f"{operator_id}_REJECTED"
        return child
    if guided_text:
        from problems.pmhctcr.insight_exec import apply_guided_operator

        # Execute the insight on this operator only. Never fall back to a
        # random sibling edit — that discards the LLM step.
        changed = apply_guided_operator(child, operator_id, guided_text)
        if not changed:
            child.meta.operator_applied = f"{operator_id}_REJECTED"
            return child
    elif operator_id in _APPLY:
        _APPLY[operator_id](child, gen_rng)
    repaired = repair(child)
    repaired.seed = parent.seed
    repaired.meta.generation = parent.meta.generation + 1
    repaired.meta.parent_id = parent.meta.parent_id
    if (not has_working_encoder(repaired)) or integrity_errors(repaired):
        rejected = deepcopy(parent)
        rejected.meta.operator_applied = f"{operator_id}_REJECTED"
        return rejected
    if guided_text and functional_dumps(repaired) == parent_key:
        rejected = deepcopy(parent)
        rejected.meta.operator_applied = f"{operator_id}_REJECTED"
        return rejected
    check_integrity(repaired)
    repaired.meta.operator_applied = operator_id
    return repaired
