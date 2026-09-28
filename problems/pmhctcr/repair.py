"""Integrity checks and deterministic repair after one mutation (TZ §4–5)."""

from __future__ import annotations

from copy import deepcopy

from problems.pmhctcr.genotype import (
    Genotype,
    MULTIMODAL_TYPES,
    allowed_sequence_regions,
    n_active_inputs,
    pair_ok,
    sequence_on,
    structure_on,
    surface_on,
)


class IntegrityError(ValueError):
    pass


def integrity_errors(g: Genotype) -> list[str]:
    errors: list[str] = []
    for pair in g.interaction.pairs:
        if not pair_ok(g, pair):
            errors.append(f"pair {pair} missing molecule encoder")
    if g.interaction.pairs:
        if g.interaction.method is None or g.interaction.fusion is None:
            errors.append("non-empty pairs require method and fusion")
    else:
        if g.interaction.method is not None or g.interaction.fusion is not None:
            errors.append("empty pairs require method=fusion=null")
    if g.encoders.structure.scope == "interface" and g.inputs.pdb.kind != "complex":
        errors.append("interface scope requires pdb.kind=complex")
    mods = {m for m, on in (("sequence", sequence_on(g)), ("structure", structure_on(g)), ("surface", surface_on(g))) if on}
    if g.model.type in MULTIMODAL_TYPES and len(mods) < 2:
        errors.append("multimodal model needs >=2 modalities")
    if g.model.type == "ensemble":
        if len(g.model.ensemble_members) < 2:
            errors.append("ensemble needs >=2 members")
        for i, member in enumerate(g.model.ensemble_members):
            if member.type in MULTIMODAL_TYPES and len(mods) < 2:
                errors.append(f"ensemble member {i} multimodal without 2 modalities")
            if member.type == "ensemble":
                errors.append(f"ensemble member {i} must not be ensemble")
    if n_active_inputs(g) < 1:
        errors.append("no active input")
    if g.model.hidden_dim % g.model.num_heads != 0:
        errors.append("num_heads must divide hidden_dim")
    if g.encoders.sequence.pretrained and g.encoders.sequence.arch != "protein_lm":
        errors.append("pretrained only with protein_lm")
    if g.encoders.sequence.region not in allowed_sequence_regions(g):
        errors.append("sequence region not allowed for active inputs")
    if surface_on(g) and not g.encoders.surface.metrics:
        errors.append("surface metrics must be non-empty")
    return errors


def check_integrity(g: Genotype) -> None:
    errs = integrity_errors(g)
    if errs:
        raise IntegrityError("; ".join(errs))


def _snap_heads(hidden_dim: int, num_heads: int) -> int:
    for h in (num_heads, 8, 4, 2, 1):
        if hidden_dim % h == 0 and h in (1, 2, 4, 8):
            return h
    return 1


def repair(g: Genotype) -> Genotype:
    """Deterministic cleanup. Not a mutation operator."""
    out = deepcopy(g)
    if out.encoders.sequence.region not in allowed_sequence_regions(out):
        out.encoders.sequence.region = "full"
    if out.encoders.sequence.arch == "protein_lm":
        out.encoders.sequence.pretrained = True
        if out.model.type in {"seq_dual_encoder", "seq_cross_encoder"}:
            out.model.type = "mlp_features"
            out.model.ensemble_members = []
    else:
        out.encoders.sequence.pretrained = False
    kept = [p for p in out.interaction.pairs if pair_ok(out, p)]
    seen: list[str] = []
    for p in kept:
        if p not in seen:
            seen.append(p)
    out.interaction.pairs = seen  # type: ignore[assignment]
    if not out.interaction.pairs:
        out.interaction.method = None
        out.interaction.fusion = None
    if out.inputs.pdb.kind != "complex":
        out.encoders.structure.scope = "full_complex"
    if not out.inputs.pdb.present:
        out.inputs.pdb.kind = None
        out.encoders.structure.scope = "full_complex"
    mods = sum(
        (
            sequence_on(out),
            structure_on(out),
            surface_on(out),
        )
    )
    if out.model.type in {"seq_dual_encoder", "seq_cross_encoder"} and not sequence_on(out):
        out.model.type = "mlp_features"
        out.model.ensemble_members = []
    if (
        out.model.type == "mlp_features"
        and sequence_on(out)
        and out.encoders.sequence.arch != "protein_lm"
        and (
            out.interaction.method == "cross_attention"
            or out.interaction.fusion == "cross_attention"
        )
    ):
        out.model.type = "seq_cross_encoder"
        out.model.ensemble_members = []
    if out.model.type == "pdb_gnn" and not structure_on(out):
        out.model.type = "mlp_features"
        out.model.ensemble_members = []
    if out.model.type in {"masif_siamese", "masif_patch_cross_attn"} and not surface_on(out):
        out.model.type = "mlp_features"
        out.model.ensemble_members = []
    if out.model.type in MULTIMODAL_TYPES and mods < 2:
        out.model.type = "mlp_features"
        out.model.ensemble_members = []
    if out.model.type == "ensemble":
        valid = []
        for member in out.model.ensemble_members:
            if member.type == "ensemble":
                continue
            if member.type in MULTIMODAL_TYPES and mods < 2:
                continue
            valid.append(member)
        out.model.ensemble_members = valid
        if len(valid) >= 2:
            pass
        elif len(valid) == 1:
            body = valid[0]
            out.model.type = body.type
            out.model.hidden_dim = body.hidden_dim
            out.model.num_layers = body.num_layers
            out.model.num_heads = body.num_heads
            out.model.dropout = body.dropout
            out.model.residual = body.residual
            out.model.ensemble_members = []
        else:
            out.model.type = "mlp_features"
            out.model.ensemble_members = []
    out.model.num_heads = _snap_heads(out.model.hidden_dim, out.model.num_heads)  # type: ignore[assignment]
    if surface_on(out) and not out.encoders.surface.metrics:
        out.encoders.surface.metrics = ["cosine"]
    if not surface_on(out):
        out.encoders.surface.spots.enabled = False
    if len(out.encoders.surface.spots.derived) > 8:
        out.encoders.surface.spots.derived = list(out.encoders.surface.spots.derived[:8])
    if out.encoders.surface.spots.metric == "cosine" and out.encoders.surface.spots.threshold >= 1.0:
        out.encoders.surface.spots.threshold = 0.5
    return out


def has_working_encoder(g: Genotype) -> bool:
    return n_active_inputs(g) >= 1
