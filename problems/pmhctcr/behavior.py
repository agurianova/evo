"""MAP-Elites behavioral descriptors from the JSON genotype (not from eval labels)."""

from __future__ import annotations

import math
import re
from typing import Any

try:
    from problems.pmhctcr.genotype import (
        Genotype,
        active_modalities,
        loads,
        sequence_on,
        structure_on,
        surface_on,
    )
except ImportError:
    from genotype import (  # type: ignore[no-redef]
        Genotype,
        active_modalities,
        loads,
        sequence_on,
        structure_on,
        surface_on,
    )

# Compressed MAP-Elites pathway: 4 bins LLM actually fills (sequence stays on).
# 0 sequence, 1 surface (pdb off), 2 structure (masif off), 3 structure+surface.
MODALITY_MIX_NAMES = (
    "sequence",
    "surface",
    "structure",
    "structure+surface",
)
MODALITY_MIX_CODE = {name: i for i, name in enumerate(MODALITY_MIX_NAMES)}

# Interaction family: 8 bins. Fusion outranks method so gated/cross fusion
# does not collapse into the method=cross_attention cells.
INTERACTION_KIND_NAMES = (
    "none",
    "product",
    "abs_diff",
    "bilinear",
    "cross_attn_1pair",
    "cross_attn_multipair",
    "fusion_gated",
    "fusion_cross",
)
INTERACTION_KIND_CODE = {name: i for i, name in enumerate(INTERACTION_KIND_NAMES)}

# Typical ImmRep25 sizes used only for FLOPs (params do not scale with them).
_SEQ_LEN = {"peptide": 9, "mhc": 365, "tcr_alpha": 253, "tcr_beta": 291}
_N_PDB_NODES = 2500
_N_MASIF_POINTS = 4000
_AA_VOCAB = 21
_MASIF_DIM = 80
_ESM_DIM = 320  # frozen ESM-2 8M cache; not counted as trainable weights


def _as_genotype(payload: Any) -> Genotype | None:
    if isinstance(payload, Genotype):
        return payload
    if isinstance(payload, dict) and "inputs" in payload:
        return loads(payload)
    genotype = getattr(payload, "genotype", None)
    if isinstance(genotype, Genotype):
        return genotype
    if isinstance(payload, str) and ("GENOTYPE_JSON" in payload or "def entrypoint" in payload):
        try:
            try:
                from problems.pmhctcr.codegen import loads_program
            except ImportError:
                from codegen import loads_program
            return loads_program(payload)
        except Exception:
            return None
    if isinstance(payload, str) and '"inputs"' in payload:
        try:
            return loads(payload)
        except Exception:
            return None
    return None


def used_modalities(g: Genotype) -> set[str]:
    """Modalities that actually enter X: the input flags, matching `_row_features`."""
    return active_modalities(g)


def modality_mix_name(g: Genotype) -> str:
    """Compressed pathway: ignore sequence-off vs on (LLM keeps sequence)."""
    mods = used_modalities(g)
    st = "structure" in mods
    su = "surface" in mods
    if st and su:
        return "structure+surface"
    if st:
        return "structure"
    if su:
        return "surface"
    return "sequence"


def modality_mix_code(g: Genotype) -> int:
    return MODALITY_MIX_CODE[modality_mix_name(g)]


def interaction_kind_name(g: Genotype) -> str:
    pairs = list(g.interaction.pairs or [])
    method = g.interaction.method
    fusion = g.interaction.fusion
    if not pairs:
        return "none"
    if fusion == "cross_attention":
        return "fusion_cross"
    if fusion == "gated_sum":
        return "fusion_gated"
    if method == "cross_attention":
        return "cross_attn_multipair" if len(pairs) >= 2 else "cross_attn_1pair"
    if method == "bilinear":
        return "bilinear"
    if method == "abs_diff":
        return "abs_diff"
    return "product"


def interaction_kind_code(g: Genotype) -> int:
    return INTERACTION_KIND_CODE[interaction_kind_name(g)]


def _linear(in_dim: int, out_dim: int) -> int:
    return in_dim * out_dim + out_dim


def _transformer_layer(hidden: int) -> int:
    # Attention (QKV+out) + FFN 4h.
    return 4 * hidden * hidden + 2 * hidden * (4 * hidden)


def _gnn_layer(hidden: int, arch: str, heads: int) -> int:
    if arch == "se3_transformer":
        return 4 * _transformer_layer(hidden)
    if arch == "egnn":
        return 3 * _linear(hidden + 3, hidden)
    if arch == "gat":
        return _linear(hidden, hidden * heads) + _linear(hidden * heads, hidden)
    return 2 * _linear(hidden, hidden)


def _sequence_params(g: Genotype, hidden: int, layers: int) -> tuple[int, int]:
    if not sequence_on(g):
        return 0, 0
    s = g.inputs.sequence
    n_tokens = 0
    if s.peptide:
        n_tokens += _SEQ_LEN["peptide"]
    if s.mhc:
        n_tokens += _SEQ_LEN["mhc"]
    if s.tcr_alpha:
        n_tokens += _SEQ_LEN["tcr_alpha"]
    if s.tcr_beta:
        n_tokens += _SEQ_LEN["tcr_beta"]
    n_tokens = max(n_tokens, 1)
    enc = g.encoders.sequence
    h = int(enc.hidden_dim or hidden)
    if enc.arch == "protein_lm":
        # Frozen ESM-2 8M cache; trainable cost is only the MLP that reads 320-d vectors.
        n_src = int(s.peptide) + int(s.mhc) + int(s.tcr_alpha) + int(s.tcr_beta)
        params = n_src * _linear(_ESM_DIM, h) if n_src else 0
    elif enc.arch == "cnn":
        params = _linear(_AA_VOCAB, h) + layers * (3 * h * h + h)
    else:
        params = _linear(_AA_VOCAB, h) + layers * _transformer_layer(h)
    if enc.pooling == "attention":
        params += h * 2
    return params, n_tokens


def _structure_params(g: Genotype, hidden: int, layers: int, heads: int) -> tuple[int, int]:
    if not structure_on(g):
        return 0, 0
    st = g.encoders.structure
    h = int(st.hidden_dim or hidden)
    params = layers * _gnn_layer(h, st.arch, heads)
    if st.pooling == "attention":
        params += h * 2
    k = st.edges.k if st.edges.type == "knn" else 16
    flops_units = _N_PDB_NODES * max(int(k), 1)
    return params, flops_units


def _surface_params(g: Genotype, hidden: int) -> tuple[int, int]:
    if not surface_on(g):
        return 0, 0
    su = g.encoders.surface
    params = _linear(_MASIF_DIM, hidden)
    if su.patch_boundary == "nn_learned":
        params += _linear(_MASIF_DIM, hidden)
    n_metrics = max(len(su.metrics), 1)
    params += n_metrics * hidden
    sides = int(g.inputs.masif.tcr_direct) + int(g.inputs.masif.pmhc_flipped)
    return params, _N_MASIF_POINTS * max(sides, 1)


def _head_params(g: Genotype, in_dim: int) -> int:
    m = g.model
    h = int(m.hidden_dim)
    layers = int(m.num_layers)
    params = _linear(max(in_dim, 1), h)
    params += max(layers - 1, 0) * _linear(h, h)
    if m.residual:
        params += h
    params += _linear(h, 1)
    if g.interaction.pairs:
        n_pairs = len(g.interaction.pairs)
        if g.interaction.method == "bilinear":
            params += n_pairs * h * h
        elif g.interaction.method == "cross_attention":
            params += n_pairs * _transformer_layer(h)
        else:
            params += n_pairs * h
        if g.interaction.fusion == "gated_sum":
            params += 3 * h
        elif g.interaction.fusion == "cross_attention":
            params += _transformer_layer(h)
    return params


def estimate_n_params(g: Genotype) -> int:
    m = g.model
    h = int(m.hidden_dim)
    layers = int(m.num_layers)
    heads = int(m.num_heads)
    used = used_modalities(g)

    def _encoders_for(mods: set[str]) -> tuple[int, int]:
        params = 0
        units = 0
        if "sequence" in mods:
            p, u = _sequence_params(g, h, layers)
            params += p
            units += u
        if "structure" in mods:
            p, u = _structure_params(g, h, layers, heads)
            params += p
            units += u
        if "surface" in mods:
            p, u = _surface_params(g, h)
            params += p
            units += u
        return params, units

    if m.type == "ensemble" and len(m.ensemble_members) >= 2:
        total = 0
        for member in m.ensemble_members:
            fake = g.model_copy(deep=True)
            fake.model.type = member.type  # type: ignore[assignment]
            fake.model.hidden_dim = member.hidden_dim
            fake.model.num_layers = member.num_layers
            fake.model.num_heads = member.num_heads
            fake.model.ensemble_members = []
            total += estimate_n_params(fake)
        return total + _linear(len(m.ensemble_members), 1)

    enc_params, _ = _encoders_for(used)
    n_mods = max(len(used), 1)
    return enc_params + _head_params(g, n_mods * h)


def estimate_flops(g: Genotype) -> int:
    """One-complex forward FLOPs ≈ 2 * params * work units of active encoders."""
    m = g.model
    h = int(m.hidden_dim)
    layers = int(m.num_layers)
    heads = int(m.num_heads)
    used = used_modalities(g)
    params = estimate_n_params(g)
    units = 1
    if "sequence" in used:
        units += _sequence_params(g, h, layers)[1]
    if "structure" in used:
        units += _structure_params(g, h, layers, heads)[1]
    if "surface" in used:
        units += _surface_params(g, h)[1]
    return int(2 * params * units)


def _python_modalities(payload: Any) -> set[str]:
    """Read the explicit modality contract used by free-form Python genomes."""
    raw = getattr(payload, "active_modalities", ("sequence",))
    if isinstance(raw, str):
        raw = (raw,)
    try:
        modalities = {str(name).lower() for name in raw}
    except TypeError:
        modalities = {"sequence"}
    return modalities & {"sequence", "structure", "surface"} or {"sequence"}


def _python_n_params(payload: Any) -> int:
    """Count fitted model capacity without requiring a specific ML framework."""
    model = getattr(payload, "model", payload)

    # sklearn Pipeline: preprocessing statistics are not trainable parameters.
    steps = getattr(model, "steps", None)
    if steps:
        model = steps[-1][1]

    parameters = getattr(model, "parameters", None)
    if callable(parameters):
        try:
            return max(1, sum(int(parameter.numel()) for parameter in parameters()))
        except Exception:
            pass

    count = 0
    for name in ("coef_", "intercept_"):
        value = getattr(model, name, None)
        if value is not None and hasattr(value, "size"):
            count += int(value.size)
    if count:
        return count

    # Tree estimators: node count is a stable proxy for learned capacity.
    estimators = getattr(model, "estimators_", None)
    if estimators is not None:
        stack = list(getattr(estimators, "flat", estimators))
        for estimator in stack:
            tree = getattr(estimator, "tree_", None)
            if tree is not None:
                count += int(tree.node_count)
    predictors = getattr(model, "_predictors", None)
    if predictors is not None:
        for stage in predictors:
            for predictor in stage:
                nodes = getattr(predictor, "nodes", None)
                if nodes is not None:
                    count += int(nodes.size)
    return max(count, 61)


# Python MAP-Elites axis: architecture family (4 bins). Higher wins when several match.
ARCH_KIND_NAMES = (
    "linear_mlp",  # 0 — Linear / shallow MLP on flat features
    "modality_attention",  # 1 — modality-token MHA / gated / late fusion
    "geometric",  # 2 — PDB/MaSIF neighborhood graphs + message passing
    "interface_cross_attn",  # 3 — cross-attn pMHC↔TCR on MaSIF patches and/or PDB residues
)
ARCH_KIND_CODE = {name: i for i, name in enumerate(ARCH_KIND_NAMES)}

# Final python_patch MAP-Elites axis (6 bins). Set interaction_family to one of these.
PMHC_TCR_INTERACTION_NAMES = (
    "global_concat",  # 0 — pooled vectors / early concat / Linear+MLP
    "explicit_patch_matching",  # 1 — MaSIF NN matching, components, trace, reciprocal stats
    "bilinear_product",  # 2 — bilinear / outer-product / elementwise product interaction
    "single_cross_attention",  # 3 — one cross-attn module (single direction OK)
    "reciprocal_dual_attention",  # 4 — bidirectional / dual-interface cross-attn
    "multi_branch_gated",  # 5 — gated fusion over parallel branches or latent states
)
PMHC_TCR_INTERACTION_CODE = {name: i for i, name in enumerate(PMHC_TCR_INTERACTION_NAMES)}


def _python_source(payload: Any) -> str:
    """Best-effort genome source for free-form Python predictors."""
    for attr in ("__genome_source__", "_genome_source", "source_code"):
        value = getattr(payload, attr, None)
        if isinstance(value, str) and "def " in value:
            return value
    cls = payload if isinstance(payload, type) else type(payload)
    try:
        import inspect

        src = inspect.getsource(cls)
        if src and "def " in src:
            # Class body alone loses module-level helpers; prefer full module.
            module = inspect.getmodule(cls)
            if module is not None:
                file = getattr(module, "__file__", None)
                if isinstance(file, str):
                    import linecache

                    lines = linecache.getlines(file)
                    if lines:
                        return "".join(lines)
            return src
    except (OSError, TypeError):
        pass
    try:
        import linecache

        for name in ("user_code.py", "<pmhctcr_child>"):
            lines = linecache.getlines(name)
            if lines and any("def entrypoint" in line or "class " in line for line in lines):
                return "".join(lines)
    except Exception:
        pass
    return ""


def _arch_kind_from_source(code: str) -> int:
    """Map Python genome text to ARCH_KIND_NAMES index (highest matching family)."""
    if not code:
        return 0
    low = code.lower()
    fam_match = re.search(
        r"interaction_family\s*=\s*['\"]([^'\"]+)['\"]", code, flags=re.I
    )
    fam = fam_match.group(1).lower() if fam_match else ""

    has_mha = (
        "multiheadattention" in low
        or "multi_head_attention" in low
        or "nn.multiheadattention" in low
    )

    interface = False
    interface_markers = (
        "patch_cross",
        "masif_cross",
        "residue_cross",
        "interface_cross",
        "cross_attention_token",
        "pmhc_tcr_cross",
        "tcr_pmhc_cross",
        "pdb_cross_attn",
        "masif_patch_cross",
    )
    if any(m in fam for m in interface_markers) or any(m in low for m in interface_markers):
        interface = True
    # Token-level pMHC↔TCR attention (not flat 3–4 modality vectors).
    token_cues = (
        "tcr_tokens",
        "pmhc_tokens",
        "patch_tokens",
        "residue_tokens",
        "masif_tokens",
        "pdb_tokens",
    )
    flat_modality_fam = fam in {
        "modality_attention",
        "cross_modal_attention",
        "early_concat",
        "gated_branch_fusion",
        "late_fusion",
        "",
    }
    if has_mha and any(k in low for k in token_cues):
        interface = True
    if (
        has_mha
        and not flat_modality_fam
        and ("tcr_desc" in low and "pmhc_desc" in low)
        and (
            "cross_attn" in low
            or "cross-attn" in low
            or "cross_attention" in low
            or re.search(r"attn\s*\(.*tcr.*pmhc|attn\s*\(.*pmhc.*tcr", low)
        )
    ):
        interface = True
    if (
        has_mha
        and "load_pdb" in low
        and "chain" in low
        and not flat_modality_fam
        and ("cross_attn" in low or "cross_attention" in low or "residue_tokens" in low)
    ):
        interface = True

    geom = False
    geom_markers = (
        "torch_geometric",
        "gatconv",
        "gcnconv",
        "sageconv",
        "transformerconv",
        "message_passing",
        "radius_graph",
        "knn_graph",
        " knn(",
        "radius_neighbors",
    )
    if any(m in low for m in geom_markers):
        geom = True
    if any(m in fam for m in ("gnn", "geometric", "graph", "structure_gnn")):
        geom = True
    if re.search(r"\b(knn|radius)[_\s-]?(graph|neighbors?)\b", low) and (
        "xyz" in low or "load_pdb" in low or "masif" in low
    ):
        geom = True
    if "scatter" in low and ("xyz" in low or "edge_index" in low):
        geom = True

    modality = False
    if has_mha or "modalityattention" in low or "gated_branch" in low:
        modality = True
    if any(
        m in fam
        for m in (
            "modality_attention",
            "gated_branch_fusion",
            "gated",
            "late_fusion",
            "cross_modal_attention",
            "cross_modal",
        )
    ):
        modality = True

    if interface:
        return ARCH_KIND_CODE["interface_cross_attn"]
    if geom:
        return ARCH_KIND_CODE["geometric"]
    if modality:
        return ARCH_KIND_CODE["modality_attention"]
    return ARCH_KIND_CODE["linear_mlp"]


def _arch_kind_from_predictor(payload: Any) -> int:
    """Fallback when source is unavailable: fitted modules + interaction_family."""
    fam = str(getattr(payload, "interaction_family", "") or "").lower()
    if any(
        m in fam
        for m in (
            "patch_cross",
            "masif_cross",
            "residue_cross",
            "interface_cross",
            "cross_attention_token",
        )
    ):
        return ARCH_KIND_CODE["interface_cross_attn"]
    if any(m in fam for m in ("gnn", "geometric", "graph", "structure_gnn")):
        return ARCH_KIND_CODE["geometric"]

    model = getattr(payload, "model", None)
    has_mha = False
    if model is not None:
        named = getattr(model, "named_modules", None)
        if callable(named):
            try:
                for _, module in named():
                    name = type(module).__name__.lower()
                    if "multiheadattention" in name:
                        has_mha = True
                        break
            except Exception:
                pass
        else:
            has_mha = "attention" in type(model).__name__.lower()

    if any(
        m in fam
        for m in (
            "modality_attention",
            "gated",
            "late_fusion",
            "cross_modal",
        )
    ):
        return ARCH_KIND_CODE["modality_attention"]
    if has_mha:
        return ARCH_KIND_CODE["modality_attention"]
    return ARCH_KIND_CODE["linear_mlp"]


def _pmhc_tcr_interaction_from_source(code: str) -> int:
    """Map Python genome text to PMHC_TCR_INTERACTION_NAMES index (highest matching family)."""
    if not code:
        return PMHC_TCR_INTERACTION_CODE["global_concat"]
    low = code.lower()
    fam_match = re.search(
        r"interaction_family\s*=\s*['\"]([^'\"]+)['\"]", code, flags=re.I
    )
    fam = fam_match.group(1).lower() if fam_match else ""

    def fam_has(*markers: str) -> bool:
        return any(m in fam for m in markers)

    has_mha = (
        "multiheadattention" in low
        or "multi_head_attention" in low
        or "nn.multiheadattention" in low
    )

    if fam_has(
        "multi_branch_gated",
        "gated_branch",
        "gated_fusion",
        "gated_mixture",
        "mixture_of",
        "latent_state",
        "latent_mode",
    ):
        return PMHC_TCR_INTERACTION_CODE["multi_branch_gated"]
    if (
        "gated_branch" in low
        or "branch_gate" in low
        or "branch_gates" in low
        or re.search(r"softmax\s*\(\s*.*gate", low)
        or ("num_states" in low and "gate" in low)
        or ("k_states" in low and ("gate" in low or "mixture" in low))
    ):
        return PMHC_TCR_INTERACTION_CODE["multi_branch_gated"]

    if fam_has(
        "reciprocal_dual_attention",
        "dual_attention",
        "dual_interface",
        "reciprocal_attn",
        "bidirectional_cross",
    ):
        return PMHC_TCR_INTERACTION_CODE["reciprocal_dual_attention"]
    if (
        ("pmhc_to_tcr" in low and "tcr_to_pmhc" in low)
        or ("pdb_to_tcr" in low and "tcr_to_pdb" in low)
        or re.search(r"cross_attn.*cross_attn", low)
        or ("bidirectional" in low and has_mha)
        or (has_mha and "dual" in low and "cross" in low)
    ):
        return PMHC_TCR_INTERACTION_CODE["reciprocal_dual_attention"]

    if fam_has(
        "single_cross_attention",
        "interface_cross",
        "masif_patch_cross",
        "residue_cross",
        "cross_attention",
    ):
        return PMHC_TCR_INTERACTION_CODE["single_cross_attention"]
    if has_mha and (
        "cross_attn" in low
        or "cross-attn" in low
        or "cross_attention" in low
        or re.search(r"attn\s*\(.*tcr.*pmhc|attn\s*\(.*pmhc.*tcr", low)
    ):
        return PMHC_TCR_INTERACTION_CODE["single_cross_attention"]

    if fam_has("bilinear_product", "bilinear", "product_interaction", "outer_product"):
        return PMHC_TCR_INTERACTION_CODE["bilinear_product"]
    if (
        "bilinear" in low
        or "outer_product" in low
        or "einsum" in low
        or re.search(r"\*\s*[a-z_]+_emb", low)
    ):
        return PMHC_TCR_INTERACTION_CODE["bilinear_product"]

    if fam_has(
        "explicit_patch_matching",
        "patch_matching",
        "masif_complementarity",
        "complementary_patch",
    ):
        return PMHC_TCR_INTERACTION_CODE["explicit_patch_matching"]
    if (
        "masif_complementarity_stats" in low
        or "core_spot_features" in low
        or "trace_length" in low
        or "reciprocal_match_frac" in low
        or "connected_components" in low
        or re.search(r"l2\s*<\s*1\.7", low)
        or "nn < 1.7" in low
    ):
        return PMHC_TCR_INTERACTION_CODE["explicit_patch_matching"]

    if fam_has("global_concat", "early_concat", "linear_mlp", "pooled_concat"):
        return PMHC_TCR_INTERACTION_CODE["global_concat"]
    return PMHC_TCR_INTERACTION_CODE["global_concat"]


def _pmhc_tcr_interaction_from_predictor(payload: Any) -> int:
    fam = str(getattr(payload, "interaction_family", "") or "").lower()
    if not fam:
        return PMHC_TCR_INTERACTION_CODE["global_concat"]
    mapping = {
        "multi_branch_gated": "multi_branch_gated",
        "gated_branch_fusion": "multi_branch_gated",
        "reciprocal_dual_attention": "reciprocal_dual_attention",
        "dual_interface": "reciprocal_dual_attention",
        "single_cross_attention": "single_cross_attention",
        "interface_cross_attn": "single_cross_attention",
        "masif_patch_cross": "single_cross_attention",
        "residue_cross": "single_cross_attention",
        "bilinear_product": "bilinear_product",
        "bilinear": "bilinear_product",
        "explicit_patch_matching": "explicit_patch_matching",
        "patch_matching": "explicit_patch_matching",
        "global_concat": "global_concat",
        "early_concat": "global_concat",
    }
    for key, name in mapping.items():
        if key in fam:
            return PMHC_TCR_INTERACTION_CODE[name]
    return PMHC_TCR_INTERACTION_CODE["global_concat"]


def python_pmhc_tcr_interaction(payload: Any) -> int:
    """pMHC–TCR interaction family for final python_patch MAP-Elites (0–5)."""
    source = _python_source(payload)
    if isinstance(payload, str) and "def " in payload:
        source = payload
    if source:
        return _pmhc_tcr_interaction_from_source(source)
    return _pmhc_tcr_interaction_from_predictor(payload)


def python_arch_kind(payload: Any) -> int:
    """Architecture family for free-form Python genomes (0–3)."""
    source = _python_source(payload)
    if isinstance(payload, str) and "def " in payload:
        source = payload
    if source:
        return _arch_kind_from_source(source)
    return _arch_kind_from_predictor(payload)


def genotype_arch_kind(g: Genotype) -> int:
    """Map JSON genotype model.type onto the same 4 architecture bins."""
    mtype = g.model.type
    if mtype == "masif_patch_cross_attn":
        return ARCH_KIND_CODE["interface_cross_attn"]
    if mtype == "pdb_gnn":
        return ARCH_KIND_CODE["geometric"]
    if mtype in {
        "multimodal_cross_attn",
        "seq_cross_encoder",
        "multimodal_gated",
    }:
        return ARCH_KIND_CODE["modality_attention"]
    kind = interaction_kind_name(g)
    if kind in {
        "cross_attn_1pair",
        "cross_attn_multipair",
        "fusion_cross",
        "fusion_gated",
    }:
        return ARCH_KIND_CODE["modality_attention"]
    return ARCH_KIND_CODE["linear_mlp"]


def compute_tier(n_params: float) -> int:
    """Six logarithmic bins: 10^0–10^1 through >=10^5 learned parameters."""
    return min(5, max(0, int(math.floor(math.log10(max(float(n_params), 1.0))))))


def behavior_metrics(payload: Any) -> dict[str, float]:
    g = _as_genotype(payload)
    if g is None:
        modalities = _python_modalities(payload)
        n_params = float(_python_n_params(payload))
        legacy_mix = (
            3.0
            if {"structure", "surface"} <= modalities
            else 2.0
            if "structure" in modalities
            else 1.0
            if "surface" in modalities
            else 0.0
        )
        return {
            "modality_mix": legacy_mix,
            "interaction_kind": 0.0,
            "modality_count": float(len(modalities)),
            "arch_kind": float(python_arch_kind(payload)),
            "pmhc_tcr_interaction": float(python_pmhc_tcr_interaction(payload)),
            "compute_tier": float(compute_tier(n_params)),
            "compute_cost": n_params,
            "n_params": n_params,
            "est_flops": n_params,
        }
    n_params = float(estimate_n_params(g))
    arch = genotype_arch_kind(g)
    return {
        "modality_mix": float(modality_mix_code(g)),
        "interaction_kind": float(interaction_kind_code(g)),
        "modality_count": float(len(used_modalities(g))),
        "arch_kind": float(arch),
        "pmhc_tcr_interaction": float(min(arch, len(PMHC_TCR_INTERACTION_NAMES) - 1)),
        "compute_tier": float(compute_tier(n_params)),
        "compute_cost": n_params,
        "n_params": n_params,
        "est_flops": float(estimate_flops(g)),
    }
