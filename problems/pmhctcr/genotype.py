"""JSON genotype for pMHC-TCR programs (TZ v2). Isolated to this problem."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

HIDDEN_DIMS = (64, 128, 256, 512, 768)
NUM_HEADS = (1, 2, 4, 8)
BATCH_SIZES = (16, 32, 64, 128, 256)
SURFACE_METRICS = (
    "cosine",
    "dot",
    "l2",
    "max_sim",
    "mean_topk",
    "count_above_thr",
)
INTERACTION_PAIRS = ("peptide_tcr", "peptide_mhc", "mhc_tcr", "peptide_mhc_tcr")
TCR_REGIONS = (
    "cdr1",
    "cdr2",
    "cdr3",
    "all_cdr",
    "fr1",
    "fr2",
    "fr3",
    "fr4",
    "all_fr",
)
SEQ_REGIONS = TCR_REGIONS + ("full", "groove_a1a2", "mask")
MODEL_TYPES = (
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
MULTIMODAL_TYPES = frozenset(
    {"multimodal_mlp", "multimodal_gated", "multimodal_cross_attn"}
)
OPERATOR_IDS = (
    "CHANGE_INPUT",
    "CHANGE_SEQUENCE",
    "CHANGE_STRUCTURE",
    "CREATE_SURFACE",
    "CHANGE_SURFACE",
    "CHANGE_INTERACTION",
    "CHANGE_MODEL",
    "CHANGE_TRAINING",
    "CHANGE_AUGMENTATION",
    "CHANGE_OPTIMIZATION",
    "CHANGE_CALIBRATION",
    "NOOP",
)

SequenceSource = Literal["peptide", "mhc", "tcr_alpha", "tcr_beta"]
INPUT_FLAGS: tuple[tuple[str, ...], ...] = (
    ("sequence", "peptide"),
    ("sequence", "mhc"),
    ("sequence", "tcr_alpha"),
    ("sequence", "tcr_beta"),
    ("pdb",),
    ("masif", "tcr_direct"),
    ("masif", "pmhc_flipped"),
)


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SequenceInputs(_Strict):
    peptide: bool = True
    mhc: bool = True
    tcr_alpha: bool = True
    tcr_beta: bool = True


class PdbInputs(_Strict):
    present: bool = False
    kind: Literal["complex", "monomer"] | None = None


class MasifInputs(_Strict):
    tcr_direct: bool = False
    pmhc_flipped: bool = False


class Inputs(_Strict):
    sequence: SequenceInputs = Field(default_factory=SequenceInputs)
    pdb: PdbInputs = Field(default_factory=PdbInputs)
    masif: MasifInputs = Field(default_factory=MasifInputs)


class SequenceEncoder(_Strict):
    region: Literal[
        "cdr1",
        "cdr2",
        "cdr3",
        "all_cdr",
        "fr1",
        "fr2",
        "fr3",
        "fr4",
        "all_fr",
        "full",
        "groove_a1a2",
        "mask",
    ] = "full"
    arch: Literal["cnn", "transformer", "protein_lm"] = "transformer"
    # protein_lm = frozen ESM-2 8M cache (no HuggingFace at eval).
    pretrained: bool = False
    pooling: Literal["mean", "attention"] = "mean"
    hidden_dim: Literal[64, 128, 256, 512, 768] = 256


class StructureEdges(_Strict):
    type: Literal["radius", "knn"] = "knn"
    k: int = Field(default=16, ge=4, le=32)
    radius_A: float | None = Field(default=8.0, ge=4.0, le=15.0)


class StructureEncoder(_Strict):
    scope: Literal["full_complex", "interface"] = "full_complex"
    edges: StructureEdges = Field(default_factory=StructureEdges)
    arch: Literal["gat", "mpnn", "egnn", "se3_transformer"] = "gat"
    pooling: Literal["mean", "attention"] = "mean"
    hidden_dim: Literal[64, 128, 256, 512, 768] = 256


class SurfaceDerived(_Strict):
    """One algebraic combo of core complementary-spot scalars."""

    op: Literal["ratio", "diff", "product"] = "ratio"
    a: Literal[
        "n_match",
        "area_frac",
        "n_components",
        "gyration",
        "com_x",
        "com_y",
        "com_z",
        "min_nn",
        "mean_nn",
        "alpha_frac",
        "beta_frac",
        "cdr3_frac",
        "all_cdr_frac",
        "all_fr_frac",
        "dist_peptide",
        "dist_mhc",
        "dist_cdr3",
    ] = "cdr3_frac"
    b: Literal[
        "n_match",
        "area_frac",
        "n_components",
        "gyration",
        "com_x",
        "com_y",
        "com_z",
        "min_nn",
        "mean_nn",
        "alpha_frac",
        "beta_frac",
        "cdr3_frac",
        "all_cdr_frac",
        "all_fr_frac",
        "dist_peptide",
        "dist_mhc",
        "dist_cdr3",
    ] = "area_frac"


class SurfaceSpots(_Strict):
    """Complementary-match spots: TCR points whose NN pMHC descriptor is close."""

    enabled: bool = False
    metric: Literal["l2", "cosine"] = "l2"
    threshold: float = Field(default=1.7, ge=0.5, le=4.0)
    linkage_A: float = Field(default=2.0, ge=0.8, le=4.0)
    subsample: Literal[256, 512, 768] = 256
    derived: list[SurfaceDerived] = Field(default_factory=list)


class SurfaceEncoder(_Strict):
    patch_boundary: Literal["nn_radius", "nn_learned"] = "nn_radius"
    patch_radius_A: float = Field(default=12.0, ge=6.0, le=20.0)
    metrics: list[
        Literal["cosine", "dot", "l2", "max_sim", "mean_topk", "count_above_thr"]
    ] = Field(default_factory=lambda: ["cosine"])
    topk: int = Field(default=10, ge=3, le=50)
    threshold: float = Field(default=0.7, ge=0.3, le=0.95)
    spots: SurfaceSpots = Field(default_factory=SurfaceSpots)


class Encoders(_Strict):
    sequence: SequenceEncoder = Field(default_factory=SequenceEncoder)
    structure: StructureEncoder = Field(default_factory=StructureEncoder)
    surface: SurfaceEncoder = Field(default_factory=SurfaceEncoder)


class Interaction(_Strict):
    pairs: list[Literal["peptide_tcr", "peptide_mhc", "mhc_tcr", "peptide_mhc_tcr"]] = (
        Field(default_factory=list)
    )
    method: Literal["product", "abs_diff", "bilinear", "cross_attention"] | None = None
    fusion: Literal["concat", "gated_sum", "cross_attention"] | None = None


class ModelBody(_Strict):
    type: Literal[
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
    ] = "mlp_features"
    hidden_dim: Literal[64, 128, 256, 512, 768] = 256
    num_layers: int = Field(default=2, ge=1, le=6)
    num_heads: Literal[1, 2, 4, 8] = 4
    dropout: float = Field(default=0.1, ge=0.0, le=0.5)
    residual: bool = True

    @model_validator(mode="after")
    def heads_divide_hidden(self) -> ModelBody:
        if self.hidden_dim % self.num_heads != 0:
            raise ValueError("num_heads must divide hidden_dim")
        return self


class ModelConfig(ModelBody):
    ensemble_members: list[ModelBody] = Field(default_factory=list)


class Augmentation(_Strict):
    seq_mask_p: float = Field(default=0.0, ge=0.0, le=0.3)
    structure_edge_dropout_p: float = Field(default=0.0, ge=0.0, le=0.3)


class Training(_Strict):
    loss: Literal["bce", "focal", "contrastive"] = "bce"
    focal_gamma: float = Field(default=2.0, ge=0.5, le=5.0)
    sampling: Literal["random", "hard_negative"] = "random"
    hard_negative_ratio: float = Field(default=0.3, ge=0.0, le=0.8)
    lr: float = Field(default=1e-3, ge=1e-5, le=1e-2)
    weight_decay: float = Field(default=1e-4, ge=0.0, le=1e-2)
    optimizer: Literal["adamw", "adam", "sgd"] = "adamw"
    scheduler: Literal["none", "cosine", "step"] = "none"
    batch_size: Literal[16, 32, 64, 128, 256] = 64
    augmentation: Augmentation = Field(default_factory=Augmentation)


class Calibration(_Strict):
    temperature: float = Field(default=1.0, ge=0.5, le=3.0)


class Meta(_Strict):
    generation: int = 0
    parent_id: str | None = None
    operator_applied: str | None = None


class Genotype(_Strict):
    inputs: Inputs = Field(default_factory=Inputs)
    encoders: Encoders = Field(default_factory=Encoders)
    interaction: Interaction = Field(default_factory=Interaction)
    model: ModelConfig = Field(default_factory=ModelConfig)
    training: Training = Field(default_factory=Training)
    calibration: Calibration = Field(default_factory=Calibration)
    seed: int = 0
    meta: Meta = Field(default_factory=Meta)


def default_genotype() -> Genotype:
    return Genotype()


def dumps(g: Genotype) -> str:
    import json

    return json.dumps(g.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"


def functional_dumps(g: Genotype) -> str:
    """Stable JSON of trainable fields, ignoring lineage ``meta``.

    Two CREATE_SURFACE children of the same seed used to retrain because
    ``parent_id`` / ``generation`` made ``dumps`` unique. Fitness eval keys
    off this fingerprint instead.
    """
    import json

    payload = g.model_dump(mode="json")
    payload.pop("meta", None)
    return json.dumps(payload, sort_keys=True)


def loads(raw: str | dict[str, Any]) -> Genotype:
    if isinstance(raw, dict):
        return Genotype.model_validate(raw)
    return Genotype.model_validate_json(raw)


def sequence_on(g: Genotype) -> bool:
    s = g.inputs.sequence
    return s.peptide or s.mhc or s.tcr_alpha or s.tcr_beta


def tcr_sequence_on(g: Genotype) -> bool:
    return g.inputs.sequence.tcr_alpha or g.inputs.sequence.tcr_beta


def surface_on(g: Genotype) -> bool:
    return g.inputs.masif.tcr_direct or g.inputs.masif.pmhc_flipped


def structure_on(g: Genotype) -> bool:
    return g.inputs.pdb.present


def has_peptide(g: Genotype) -> bool:
    return (
        g.inputs.sequence.peptide or g.inputs.pdb.present or g.inputs.masif.pmhc_flipped
    )


def has_mhc(g: Genotype) -> bool:
    return g.inputs.sequence.mhc or g.inputs.pdb.present or g.inputs.masif.pmhc_flipped


def has_tcr(g: Genotype) -> bool:
    return tcr_sequence_on(g) or g.inputs.masif.tcr_direct or g.inputs.pdb.present


def pair_ok(g: Genotype, pair: str) -> bool:
    if pair == "peptide_tcr":
        return has_peptide(g) and has_tcr(g)
    if pair == "peptide_mhc":
        return has_peptide(g) and has_mhc(g)
    if pair == "mhc_tcr":
        return has_mhc(g) and has_tcr(g)
    if pair == "peptide_mhc_tcr":
        return has_peptide(g) and has_mhc(g) and has_tcr(g)
    return False


def active_modalities(g: Genotype) -> set[str]:
    mods: set[str] = set()
    if sequence_on(g):
        mods.add("sequence")
    if structure_on(g):
        mods.add("structure")
    if surface_on(g):
        mods.add("surface")
    return mods


_LEARNED_SEQ_TYPES = frozenset(
    {
        "seq_dual_encoder",
        "seq_cross_encoder",
        "multimodal_mlp",
        "multimodal_gated",
        "multimodal_cross_attn",
    }
)
_LEARNED_GAT_TYPES = frozenset(
    {"pdb_gnn", "multimodal_mlp", "multimodal_gated", "multimodal_cross_attn"}
)


def uses_learned_sequence(g: Genotype) -> bool:
    """Train SeqEncoder on residue tokens. Frozen ESM cache is not a SeqEncoder."""
    if not sequence_on(g):
        return False
    if g.encoders.sequence.arch == "protein_lm":
        return False
    return g.model.type in _LEARNED_SEQ_TYPES


def uses_learned_gat(g: Genotype) -> bool:
    return structure_on(g) and g.model.type in _LEARNED_GAT_TYPES


def uses_pair_cross(g: Genotype) -> bool:
    """Pooled peptide/MHC ↔ TCR MultiheadAttention (1 token each)."""
    if (
        g.interaction.method == "cross_attention"
        or g.interaction.fusion == "cross_attention"
    ):
        return True
    return g.model.type == "seq_cross_encoder"


def uses_modality_cross(g: Genotype) -> bool:
    return g.model.type == "multimodal_cross_attn"


def uses_patch_cross(g: Genotype) -> bool:
    return surface_on(g) and g.model.type == "masif_patch_cross_attn"


def uses_siamese(g: Genotype) -> bool:
    return surface_on(g) and g.model.type == "masif_siamese"


def uses_learned_cross(g: Genotype) -> bool:
    return uses_pair_cross(g) or uses_modality_cross(g) or uses_patch_cross(g)


def cross_kind(g: Genotype) -> str:
    """Runtime comment for `# cross_attn:` — pooled MHA, not residue-level."""
    kinds: list[str] = []
    if uses_pair_cross(g):
        kinds.append("mha_pooled(peptide_tcr)")
    if uses_modality_cross(g):
        kinds.append("mha_modalities")
    if uses_patch_cross(g):
        kinds.append("mha_masif_patches")
    return "+".join(kinds) if kinds else "off"


def n_active_inputs(g: Genotype) -> int:
    n = 0
    s = g.inputs.sequence
    n += int(s.peptide) + int(s.mhc) + int(s.tcr_alpha) + int(s.tcr_beta)
    n += int(g.inputs.pdb.present)
    n += int(g.inputs.masif.tcr_direct) + int(g.inputs.masif.pmhc_flipped)
    return n


def allowed_sequence_regions(g: Genotype) -> set[str]:
    allowed = {"full", "mask"}
    if tcr_sequence_on(g):
        allowed.update(TCR_REGIONS)
    if g.inputs.sequence.mhc:
        allowed.add("groove_a1a2")
    return allowed


def get_input_flag(g: Genotype, key: tuple[str, ...]) -> bool:
    if key == ("pdb",):
        return g.inputs.pdb.present
    if key[0] == "sequence":
        return bool(getattr(g.inputs.sequence, key[1]))
    return bool(getattr(g.inputs.masif, key[1]))


def set_input_flag(g: Genotype, key: tuple[str, ...], value: bool) -> None:
    if key == ("pdb",):
        g.inputs.pdb.present = value
        if value:
            g.inputs.pdb.kind = "complex"
        else:
            g.inputs.pdb.kind = None
        return
    if key[0] == "sequence":
        setattr(g.inputs.sequence, key[1], value)
        return
    setattr(g.inputs.masif, key[1], value)
