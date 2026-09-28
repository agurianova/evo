"""Map the first LLM mutation suggestion onto one JSON operator and apply it.

``substitute`` is the contract: ``OPERATOR=<ID>;`` plus assignments
(``set path to value``, ``enable path``, ``add pair``, spots/derived).
Mechanism/anchor text is not used to choose the operator or patch fields.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from gigaevo.evolution.mutation.constants import MUTATION_CONTEXT_METADATA_KEY
from gigaevo.programs.program import Program
from problems.pmhctcr.genotype import (
    BATCH_SIZES,
    HIDDEN_DIMS,
    INTERACTION_PAIRS,
    MODEL_TYPES,
    OPERATOR_IDS,
    SEQ_REGIONS,
    Genotype,
    SurfaceDerived,
    get_input_flag,
    pair_ok,
    sequence_on,
    set_input_flag,
    structure_on,
    surface_on,
)

_INSIGHT_HEADER = re.compile(
    r"1\.\s+\*\*\[(?P<typ>[^\]]+)\]\[[^\]]+\]\[[^\]]+\]\*\*(?P<body>.*?)(?=\n2\. |\n## |\Z)",
    re.DOTALL,
)
_OPERATOR_TOKEN = re.compile(
    r"OPERATOR\s*=\s*(?P<op>CHANGE_[A-Z]+|CREATE_SURFACE|NOOP)",
    re.IGNORECASE,
)
_SET_CMD = re.compile(
    r"\b(?P<verb>set|enable|disable)\s+(?P<path>[a-z][a-z0-9_.]*)"
    r"(?:\s+to\s+(?P<value>true|false|none|null|[a-z0-9_.+-]+))?",
    re.IGNORECASE,
)
_ADD_PAIR = re.compile(
    r"(?:add\s+)?pair\s+(?P<pair>peptide_tcr|peptide_mhc|mhc_tcr|peptide_mhc_tcr)",
    re.IGNORECASE,
)
_PATH_TO = re.compile(
    r"\b(?P<path>[a-z][a-z0-9_.]*)\s+to\s+(?P<value>true|false|none|null|[a-z0-9_.+-]+)",
    re.IGNORECASE,
)
_ADD_DERIVED = re.compile(
    r"add\s+derived\s+(?:(?P<op>ratio|diff|product)\s+)?"
    r"(?P<a>[a-z][a-z0-9_]*)\s*/\s*(?P<b>[a-z][a-z0-9_]*)",
    re.IGNORECASE,
)
_SPOTS_ENABLE = re.compile(
    r"enable\s+complementary\s+spots|spots\.enabled|complementary-match",
    re.IGNORECASE,
)

_PATH_ALIASES = {
    "peptide": "inputs.sequence.peptide",
    "mhc": "inputs.sequence.mhc",
    "tcr_alpha": "inputs.sequence.tcr_alpha",
    "tcr_beta": "inputs.sequence.tcr_beta",
    "sequence.peptide": "inputs.sequence.peptide",
    "sequence.mhc": "inputs.sequence.mhc",
    "sequence.tcr_alpha": "inputs.sequence.tcr_alpha",
    "sequence.tcr_beta": "inputs.sequence.tcr_beta",
    "pdb": "inputs.pdb.present",
    "pdb.present": "inputs.pdb.present",
    "pdb.kind": "inputs.pdb.kind",
    "tcr_direct": "inputs.masif.tcr_direct",
    "pmhc_flipped": "inputs.masif.pmhc_flipped",
    "masif.tcr_direct": "inputs.masif.tcr_direct",
    "masif.pmhc_flipped": "inputs.masif.pmhc_flipped",
    "arch": "encoders.sequence.arch",
    "region": "encoders.sequence.region",
    "pooling": "encoders.sequence.pooling",
    "pretrained": "encoders.sequence.pretrained",
    "sequence.arch": "encoders.sequence.arch",
    "sequence.region": "encoders.sequence.region",
    "sequence.pooling": "encoders.sequence.pooling",
    "type": "model.type",
    "num_layers": "model.num_layers",
    "hidden_dim": "model.hidden_dim",
    "num_heads": "model.num_heads",
    "dropout": "model.dropout",
    "residual": "model.residual",
    "method": "interaction.method",
    "fusion": "interaction.fusion",
    "pairs": "interaction.pairs",
    "loss": "training.loss",
    "sampling": "training.sampling",
    "lr": "training.lr",
    "learning_rate": "training.lr",
    "weight_decay": "training.weight_decay",
    "focal_gamma": "training.focal_gamma",
    "optimizer": "training.optimizer",
    "scheduler": "training.scheduler",
    "batch_size": "training.batch_size",
    "temperature": "calibration.temperature",
    "seq_mask_p": "training.augmentation.seq_mask_p",
    "structure_edge_dropout_p": "training.augmentation.structure_edge_dropout_p",
    "spots.enabled": "encoders.surface.spots.enabled",
    "spots.metric": "encoders.surface.spots.metric",
    "spots.threshold": "encoders.surface.spots.threshold",
    "spots.linkage_a": "encoders.surface.spots.linkage_A",
    "spots.linkage_A": "encoders.surface.spots.linkage_A",
    "threshold": "encoders.surface.spots.threshold",
}

_ALLOW: dict[str, frozenset[str]] = {
    "CHANGE_INPUT": frozenset(
        {
            "inputs.sequence.peptide",
            "inputs.sequence.mhc",
            "inputs.sequence.tcr_alpha",
            "inputs.sequence.tcr_beta",
            "inputs.pdb.present",
            "inputs.pdb.kind",
        }
    ),
    "CREATE_SURFACE": frozenset(
        {
            "inputs.masif.tcr_direct",
            "inputs.masif.pmhc_flipped",
            "encoders.surface.metrics",
            "encoders.surface.topk",
            "encoders.surface.threshold",
            "encoders.surface.patch_radius_A",
            "encoders.surface.patch_boundary",
        }
    ),
    "CHANGE_SURFACE": frozenset(
        {
            "encoders.surface.spots.enabled",
            "encoders.surface.spots.metric",
            "encoders.surface.spots.threshold",
            "encoders.surface.spots.linkage_A",
            "encoders.surface.spots.subsample",
            "encoders.surface.metrics",
            "encoders.surface.topk",
            "encoders.surface.threshold",
            "encoders.surface.patch_radius_A",
            "encoders.surface.patch_boundary",
        }
    ),
    "CHANGE_SEQUENCE": frozenset(
        {
            "encoders.sequence.arch",
            "encoders.sequence.region",
            "encoders.sequence.pooling",
            "encoders.sequence.pretrained",
            "encoders.sequence.hidden_dim",
        }
    ),
    "CHANGE_STRUCTURE": frozenset(
        {
            "encoders.structure.scope",
            "encoders.structure.arch",
            "encoders.structure.pooling",
            "encoders.structure.hidden_dim",
            "encoders.structure.edges.type",
            "encoders.structure.edges.k",
            "encoders.structure.edges.radius_A",
        }
    ),
    "CHANGE_INTERACTION": frozenset(
        {
            "interaction.method",
            "interaction.fusion",
            "interaction.pairs",
        }
    ),
    "CHANGE_MODEL": frozenset(
        {
            "model.type",
            "model.num_layers",
            "model.hidden_dim",
            "model.num_heads",
            "model.dropout",
            "model.residual",
        }
    ),
    "CHANGE_TRAINING": frozenset(
        {
            "training.loss",
            "training.sampling",
            "training.lr",
            "training.weight_decay",
            "training.focal_gamma",
            "training.hard_negative_ratio",
        }
    ),
    "CHANGE_OPTIMIZATION": frozenset(
        {
            "training.optimizer",
            "training.scheduler",
            "training.batch_size",
        }
    ),
    "CHANGE_CALIBRATION": frozenset({"calibration.temperature"}),
    "CHANGE_AUGMENTATION": frozenset(
        {
            "training.augmentation.seq_mask_p",
            "training.augmentation.structure_edge_dropout_p",
        }
    ),
}


@dataclass(frozen=True)
class PrimaryInsight:
    type: str
    substitute: str
    anchor: str
    body: str

    @property
    def blob(self) -> str:
        return f"{self.type} {self.substitute} {self.anchor} {self.body}".lower()

    @property
    def source(self) -> str:
        return self.substitute.strip() or self.body.strip()


def context_from_parent(parent: Program, memory_instructions: str | None = None) -> str:
    chunks: list[str] = []
    if memory_instructions:
        chunks.append(memory_instructions)
    meta = parent.metadata or {}
    ctx = meta.get(MUTATION_CONTEXT_METADATA_KEY)
    if isinstance(ctx, str) and ctx.strip():
        chunks.append(ctx)
    getter = getattr(parent, "get_metadata", None)
    if callable(getter):
        extra = getter(MUTATION_CONTEXT_METADATA_KEY)
        if isinstance(extra, str) and extra.strip() and extra not in chunks:
            chunks.append(extra)
    return "\n\n".join(chunks)


def parse_primary_insight(context: str) -> PrimaryInsight | None:
    if not context or "## Program Insights" not in context:
        return None
    if "<No insights available>" in context:
        return None
    match = _INSIGHT_HEADER.search(context)
    if not match:
        return None
    body = match.group("body")
    substitute = ""
    if "substitute:" in body:
        substitute = body.split("substitute:", 1)[1]
        substitute = substitute.split("|")[0]
        substitute = substitute.split("\n---", 1)[0]
        substitute = substitute.split("\n", 1)[0].strip()
    anchor = ""
    if "anchor `" in body:
        start = body.find("anchor `") + len("anchor `")
        end = body.find("`", start)
        if end > start:
            anchor = body[start:end]
    return PrimaryInsight(
        type=match.group("typ").strip(),
        substitute=substitute,
        anchor=anchor,
        body=body.strip(),
    )


def operator_token(text: str) -> str | None:
    match = _OPERATOR_TOKEN.search(text or "")
    if not match:
        return None
    op = match.group("op").upper()
    return op if op in OPERATOR_IDS else None


def map_operator(insight: PrimaryInsight, parent: Genotype) -> str | None:
    """Prefer ``OPERATOR=<ID>`` in substitute. Do not remap from mechanism words."""
    token = operator_token(insight.substitute) or operator_token(insight.body)
    if token:
        if token == "CREATE_SURFACE" and surface_on(parent):
            src = insight.substitute.lower()
            if any(
                k in src
                for k in ("spot", "complementary", "derived", "localization", "1.7")
            ):
                return "CHANGE_SURFACE"
            return None
        if token == "CHANGE_SURFACE" and not surface_on(parent):
            return "CREATE_SURFACE"
        return token
    return _map_from_keywords(insight.substitute.lower(), parent)


def _map_from_keywords(src: str, parent: Genotype) -> str | None:
    if not src:
        return None
    if not surface_on(parent) and any(
        k in src for k in ("masif", "create_surface", "tcr_direct", "pmhc_flipped")
    ):
        return "CREATE_SURFACE"
    if surface_on(parent) and any(
        k in src for k in ("spot", "complementary", "change_surface", "nn < 1.7")
    ):
        return "CHANGE_SURFACE"
    if any(
        k in src
        for k in (
            "seq_dual",
            "seq_cross",
            "pdb_gnn",
            "masif_siamese",
            "masif_patch",
            "multimodal",
            "hidden_dim",
            "num_layers",
            "num_heads",
            "dropout",
            "residual",
            "model.type",
        )
    ):
        return "CHANGE_MODEL"
    if any(
        k in src
        for k in ("interaction", "cross_attention", "fusion", "bilinear", "pair")
    ):
        return "CHANGE_INTERACTION"
    if any(
        k in src
        for k in (
            "encoders.sequence",
            "sequence.arch",
            "protein_lm",
            "esm2",
            "esm-2",
            "arch to cnn",
        )
    ):
        return "CHANGE_SEQUENCE"
    if any(
        k in src
        for k in (
            "hard_negative",
            "sampling",
            "focal",
            "contrastive",
            "weight_decay",
            "learning_rate",
        )
    ) or re.search(r"\blr\b", src):
        return "CHANGE_TRAINING"
    if "inputs.sequence" in src or "inputs.pdb" in src:
        return "CHANGE_INPUT"
    if any(k in src for k in ("pdb", "structure", "gat", "interface", "knn")):
        if not structure_on(parent):
            return "CHANGE_INPUT"
        return "CHANGE_STRUCTURE"
    if any(k in src for k in ("pooling", "region", "cdr3", "all_cdr", "cdr1", "cdr2")):
        return "CHANGE_SEQUENCE"
    if "temperature" in src or "calibration" in src:
        return "CHANGE_CALIBRATION"
    if any(k in src for k in ("optimizer", "scheduler", "batch_size")):
        return "CHANGE_OPTIMIZATION"
    if "augment" in src or "seq_mask" in src:
        return "CHANGE_AUGMENTATION"
    return None


def _clip(val: float, lo: float, hi: float) -> float:
    return float(min(hi, max(lo, val)))


def _search_float(blob: str, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        match = re.search(
            rf"{key}[^0-9eE\-+]*([0-9]+(?:\.[0-9]+)?(?:[eE]-?[0-9]+)?)",
            blob,
        )
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    return None


def _canonical_path(raw: str, operator_id: str) -> str | None:
    key = raw.strip().strip("\"'")
    if key in _PATH_ALIASES:
        key = _PATH_ALIASES[key]
    if not key.startswith(
        ("inputs.", "encoders.", "interaction.", "model.", "training.", "calibration.")
    ):
        aliased = _PATH_ALIASES.get(key)
        if aliased:
            key = aliased
    if operator_id == "CHANGE_SURFACE" and key == "encoders.surface.threshold":
        key = "encoders.surface.spots.threshold"
    allowed = _ALLOW.get(operator_id, frozenset())
    if key in allowed:
        return key
    return None


def _parse_scalar(raw: str | None, verb: str) -> Any:
    if verb == "enable":
        if raw is None or raw.lower() in {"", "true", "on"}:
            return True
    if verb == "disable":
        return False
    if raw is None:
        return True if verb == "enable" else None
    text = raw.lower()
    if text in {"true", "on", "yes"}:
        return True
    if text in {"false", "off", "no"}:
        return False
    if text in {"none", "null"}:
        return None
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"-?\d+\.\d+(e-?\d+)?", text) or re.fullmatch(r"-?\d+e-?\d+", text):
        return float(text)
    return raw


def _set_dotted(g: Genotype, path: str, value: Any) -> bool:
    parts = path.split(".")
    obj: Any = g
    for part in parts[:-1]:
        obj = getattr(obj, part)
    last = parts[-1]
    current = getattr(obj, last)
    if last == "present" and path == "inputs.pdb.present":
        flag = bool(value)
        if g.inputs.pdb.present == flag:
            return False
        set_input_flag(g, ("pdb",), flag)
        return True
    if isinstance(current, bool):
        new = bool(value)
        if current is new:
            return False
        setattr(obj, last, new)
        return True
    if current == value:
        return False
    setattr(obj, last, value)
    return True


def _promote_seq_encoder(g: Genotype) -> None:
    if g.encoders.sequence.arch == "protein_lm":
        if g.model.type in {"seq_dual_encoder", "seq_cross_encoder"}:
            g.model.type = "mlp_features"  # type: ignore[assignment]
            g.model.ensemble_members = []
        return
    if g.model.type == "mlp_features":
        g.model.type = "seq_dual_encoder"  # type: ignore[assignment]
        g.model.ensemble_members = []


def _promote_cross_encoder(g: Genotype) -> bool:
    """mlp + cross_attention trains pooled peptide↔TCR MHA, not tab self-attn."""
    if g.encoders.sequence.arch == "protein_lm":
        return False
    if g.model.type == "mlp_features" and sequence_on(g):
        g.model.type = "seq_cross_encoder"  # type: ignore[assignment]
        g.model.ensemble_members = []
        return True
    return False


def _apply_path(g: Genotype, path: str, value: Any) -> bool:
    if path == "encoders.sequence.arch":
        arch = str(value)
        if arch not in {"cnn", "transformer", "protein_lm"}:
            return False
        changed = g.encoders.sequence.arch != arch
        g.encoders.sequence.arch = arch  # type: ignore[assignment]
        g.encoders.sequence.pretrained = arch == "protein_lm"
        before_type = g.model.type
        _promote_seq_encoder(g)
        return changed or g.model.type != before_type
    if path == "encoders.sequence.region":
        region = str(value)
        if region not in SEQ_REGIONS:
            return False
        if g.encoders.sequence.region == region:
            return False
        g.encoders.sequence.region = region  # type: ignore[assignment]
        return True
    if path == "model.type":
        mtype = str(value)
        if mtype not in MODEL_TYPES:
            return False
        if g.model.type == mtype:
            return False
        g.model.type = mtype  # type: ignore[assignment]
        g.model.ensemble_members = []
        return True
    if path == "model.hidden_dim":
        hid = int(value)
        if hid not in HIDDEN_DIMS:
            return False
        if g.model.hidden_dim == hid:
            return False
        g.model.hidden_dim = hid  # type: ignore[assignment]
        if g.model.hidden_dim % g.model.num_heads != 0:
            for cand in (8, 4, 2, 1):
                if g.model.hidden_dim % cand == 0:
                    g.model.num_heads = cand  # type: ignore[assignment]
                    break
        return True
    if path == "training.batch_size":
        bs = int(value)
        if bs not in BATCH_SIZES:
            return False
        if g.training.batch_size == bs:
            return False
        g.training.batch_size = bs  # type: ignore[assignment]
        return True
    if path == "encoders.surface.spots.threshold":
        new = _clip(float(value), 0.5, 4.0)
        su = g.encoders.surface.spots
        changed = su.threshold != new or not su.enabled
        su.threshold = new
        su.enabled = True
        return changed
    if path == "training.lr":
        new = _clip(float(value), 1e-5, 1e-2)
        if g.training.lr == new:
            return False
        g.training.lr = new
        return True
    if path == "model.dropout":
        new = _clip(float(value), 0.0, 0.5)
        if g.model.dropout == new:
            return False
        g.model.dropout = new
        return True
    if path.startswith("inputs.sequence."):
        flag = path.rsplit(".", 1)[-1]
        enable = bool(value)
        key = ("sequence", flag)
        if get_input_flag(g, key) is enable:
            return False
        set_input_flag(g, key, enable)
        return True
    if path == "interaction.method":
        method = str(value)
        if method not in {"product", "abs_diff", "bilinear", "cross_attention"}:
            return False
        changed = g.interaction.method != method
        g.interaction.method = method  # type: ignore[assignment]
        changed = _ensure_interaction_pair(g) or changed
        if method == "cross_attention":
            changed = _promote_cross_encoder(g) or changed
        return changed
    if path == "interaction.fusion":
        fusion = str(value)
        if fusion not in {"concat", "gated_sum", "cross_attention"}:
            return False
        changed = g.interaction.fusion != fusion
        g.interaction.fusion = fusion  # type: ignore[assignment]
        changed = _ensure_interaction_pair(g) or changed
        if fusion == "cross_attention":
            changed = _promote_cross_encoder(g) or changed
        return changed
    try:
        return _set_dotted(g, path, value)
    except (AttributeError, ValueError, TypeError):
        return False


def _ensure_interaction_pair(g: Genotype) -> bool:
    """Integrity forbids method/fusion with empty pairs; pick a valid pair so the insight survives repair."""
    if g.interaction.pairs:
        return False
    for cand in ("peptide_tcr", "peptide_mhc", "mhc_tcr"):
        if pair_ok(g, cand):
            g.interaction.pairs = [cand]  # type: ignore[assignment]
            if g.interaction.fusion is None:
                g.interaction.fusion = "concat"  # type: ignore[assignment]
            if g.interaction.method is None:
                g.interaction.method = "product"  # type: ignore[assignment]
            return True
    return False


def _apply_pair(g: Genotype, pair: str) -> bool:
    if pair not in INTERACTION_PAIRS or not pair_ok(g, pair):
        return False
    pairs = list(g.interaction.pairs)
    if pair in pairs:
        return False
    pairs.append(pair)
    g.interaction.pairs = pairs  # type: ignore[assignment]
    if g.interaction.method is None:
        g.interaction.method = "product"
    if g.interaction.fusion is None:
        g.interaction.fusion = "concat"
    return True


def _apply_derived(g: Genotype, op: str, a: str, b: str) -> bool:
    combo = SurfaceDerived(op=op, a=a, b=b)  # type: ignore[arg-type]
    have = {(d.op, d.a, d.b) for d in g.encoders.surface.spots.derived}
    if (combo.op, combo.a, combo.b) in have or len(
        g.encoders.surface.spots.derived
    ) >= 8:
        return False
    g.encoders.surface.spots.derived = list(g.encoders.surface.spots.derived) + [combo]
    g.encoders.surface.spots.enabled = True
    return True


def _apply_spots_enable(g: Genotype, source: str) -> bool:
    su = g.encoders.surface.spots
    changed = False
    if not su.enabled:
        su.enabled = True
        changed = True
    if re.search(r"\bl2\b", source) and su.metric != "l2":
        su.metric = "l2"
        if su.threshold < 1.0:
            su.threshold = 1.7
        changed = True
    if "cosine" in source and "l2" not in source and su.metric != "cosine":
        su.metric = "cosine"
        if su.threshold >= 1.0:
            su.threshold = 0.5
        changed = True
    match = re.search(r"\b(1\.[0-9]+|0\.[0-9]+)\b", source)
    if match and (
        "nn" in source or "l2" in source or "threshold" in source or "spot" in source
    ):
        thr = _clip(float(match.group(1)), 0.5, 4.0)
        if su.threshold != thr:
            su.threshold = thr
            changed = True
        su.enabled = True
    return changed


def apply_guided_operator(g: Genotype, operator_id: str, text: str) -> bool:
    """Mutate ``g`` in place to match the insight. False = no field changed."""
    source = _action_source(text)
    recognized = False
    changed = False

    if operator_id == "CHANGE_INTERACTION":
        for match in _ADD_PAIR.finditer(source):
            recognized = True
            changed = _apply_pair(g, match.group("pair")) or changed
    if operator_id == "CHANGE_SURFACE":
        if _SPOTS_ENABLE.search(source) or "spot" in source.lower():
            recognized = True
            changed = _apply_spots_enable(g, source.lower()) or changed
        for match in _ADD_DERIVED.finditer(source):
            recognized = True
            changed = (
                _apply_derived(
                    g,
                    (match.group("op") or "ratio").lower(),
                    match.group("a"),
                    match.group("b"),
                )
                or changed
            )
    if operator_id == "CREATE_SURFACE" and not surface_on(g):
        if any(
            k in source.lower()
            for k in ("masif", "tcr_direct", "pmhc_flipped", "create_surface")
        ):
            recognized = True
            if not g.inputs.masif.tcr_direct:
                g.inputs.masif.tcr_direct = True
                changed = True
            if not g.inputs.masif.pmhc_flipped:
                g.inputs.masif.pmhc_flipped = True
                changed = True

    for match in _SET_CMD.finditer(source):
        path = _canonical_path(match.group("path"), operator_id)
        if path is None:
            continue
        recognized = True
        value = _parse_scalar(match.group("value"), match.group("verb").lower())
        if value is None and match.group("verb").lower() == "set":
            continue
        changed = _apply_path(g, path, value) or changed
    for match in _PATH_TO.finditer(source):
        path = _canonical_path(match.group("path"), operator_id)
        if path is None:
            continue
        recognized = True
        value = _parse_scalar(match.group("value"), "set")
        if value is None:
            continue
        changed = _apply_path(g, path, value) or changed

    if recognized:
        return changed
    return _keyword_apply(g, operator_id, source.lower())


def _action_source(text: str) -> str:
    match = re.search(r"OPERATOR\s*=\s*.+", text or "", re.IGNORECASE)
    if match:
        return match.group(0).split("|")[0].strip()
    return text or ""


def _keyword_apply(g: Genotype, operator_id: str, blob: str) -> bool:
    if operator_id == "CREATE_SURFACE":
        if not surface_on(g):
            g.inputs.masif.tcr_direct = True
            g.inputs.masif.pmhc_flipped = True
            return True
        return False
    if operator_id == "CHANGE_SURFACE":
        return _guided_surface(g, blob)
    if operator_id == "CHANGE_INTERACTION":
        return _guided_interaction(g, blob)
    if operator_id == "CHANGE_SEQUENCE":
        return _guided_sequence(g, blob)
    if operator_id == "CHANGE_TRAINING":
        return _guided_training(g, blob)
    if operator_id == "CHANGE_INPUT":
        return _guided_input(g, blob)
    if operator_id == "CHANGE_MODEL":
        return _guided_model(g, blob)
    if operator_id == "CHANGE_STRUCTURE":
        return _guided_structure(g, blob)
    if operator_id == "CHANGE_CALIBRATION":
        match = re.search(r"temperature[^0-9]*([0-9]+(?:\.[0-9]+)?)", blob)
        if match:
            new = _clip(float(match.group(1)), 0.5, 3.0)
            if g.calibration.temperature == new:
                return False
            g.calibration.temperature = new
            return True
        return False
    if operator_id == "CHANGE_OPTIMIZATION":
        return _guided_optimization(g, blob)
    if operator_id == "CHANGE_AUGMENTATION":
        return _guided_augmentation(g, blob)
    return False


def _guided_surface(g: Genotype, blob: str) -> bool:
    return _apply_spots_enable(g, blob)


def _guided_interaction(g: Genotype, blob: str) -> bool:
    changed = False
    if "peptide_tcr" in blob or "cross_attention" in blob:
        changed = _apply_pair(g, "peptide_tcr") or changed
    for pair in INTERACTION_PAIRS:
        if pair in blob:
            changed = _apply_pair(g, pair) or changed
    if "cross_attention" in blob and g.interaction.method != "cross_attention":
        g.interaction.method = "cross_attention"
        changed = True
    elif "bilinear" in blob and g.interaction.method != "bilinear":
        g.interaction.method = "bilinear"
        changed = True
    fusion = _parse_fusion(blob)
    if fusion is not None and g.interaction.fusion != fusion:
        g.interaction.fusion = fusion  # type: ignore[assignment]
        changed = True
    if g.interaction.pairs and g.interaction.method is None:
        g.interaction.method = "product"
        changed = True
    if g.interaction.pairs and g.interaction.fusion is None:
        g.interaction.fusion = "concat"
        changed = True
    if (
        g.interaction.method == "cross_attention"
        or g.interaction.fusion == "cross_attention"
    ):
        changed = _promote_cross_encoder(g) or changed
    return changed


def _parse_fusion(blob: str) -> str | None:
    quoted = re.search(
        r"fusion[\"'\s:=]+(concat|gated_sum|cross_attention)",
        blob,
    )
    if quoted:
        return quoted.group(1)
    if re.search(r"fusion.{0,40}concat|\bconcat\b.{0,24}fusion", blob):
        return "concat"
    if "gated" in blob:
        return "gated_sum"
    if re.search(r"fusion.{0,40}cross_attention", blob):
        return "cross_attention"
    return None


def _guided_sequence(g: Genotype, blob: str) -> bool:
    enc = g.encoders.sequence
    arch_ask = any(
        k in blob for k in ("arch", "cnn", "transformer", "protein_lm", "esm")
    )
    if (not arch_ask) or "region" in blob:
        for name in (
            "all_cdr",
            "all_fr",
            "cdr1",
            "cdr2",
            "cdr3",
            "fr1",
            "fr2",
            "fr3",
            "fr4",
            "groove_a1a2",
        ):
            if re.search(rf"\b{name}\b", blob):
                if enc.region == name:
                    return False
                enc.region = name  # type: ignore[assignment]
                return True
    if "protein_lm" in blob or "esm" in blob:
        changed = enc.arch != "protein_lm"
        if g.model.type in {"seq_dual_encoder", "seq_cross_encoder"}:
            changed = True
        enc.arch = "protein_lm"
        enc.pretrained = True
        _promote_seq_encoder(g)
        return changed
    if re.search(r"\bcnn\b", blob):
        changed = enc.arch != "cnn" or g.model.type == "mlp_features"
        enc.arch = "cnn"
        enc.pretrained = False
        _promote_seq_encoder(g)
        return changed
    if "transformer" in blob:
        changed = enc.arch != "transformer" or g.model.type == "mlp_features"
        enc.arch = "transformer"
        enc.pretrained = False
        _promote_seq_encoder(g)
        return changed
    if "attention" in blob and "pool" in blob:
        if enc.pooling == "attention":
            return False
        enc.pooling = "attention"
        return True
    return False


def _guided_training(g: Genotype, blob: str) -> bool:
    t = g.training
    if "hard_negative" in blob:
        if t.sampling == "hard_negative" and "ratio" not in blob:
            return False
        t.sampling = "hard_negative"
        ratio = _search_float(blob, ("hard_negative_ratio", "ratio"))
        if ratio is not None:
            t.hard_negative_ratio = _clip(ratio, 0.0, 0.8)
        return True
    if "focal" in blob:
        t.loss = "focal"
        gamma = _search_float(blob, ("focal_gamma", "gamma"))
        t.focal_gamma = (
            _clip(gamma, 0.5, 5.0) if gamma is not None else float(t.focal_gamma or 2.0)
        )
        return True
    if "contrastive" in blob:
        if t.loss == "contrastive":
            return False
        t.loss = "contrastive"
        return True
    if re.search(r"\bbce\b", blob):
        if t.loss == "bce":
            return False
        t.loss = "bce"
        return True
    lr = _search_float(blob, ("learning_rate", "lr"))
    if lr is not None:
        new = _clip(lr, 1e-5, 1e-2)
        if t.lr == new:
            return False
        t.lr = new
        return True
    wd = _search_float(blob, ("weight_decay",))
    if wd is not None:
        new = _clip(wd, 0.0, 1e-2)
        if t.weight_decay == new:
            return False
        t.weight_decay = new
        return True
    return False


def _guided_augmentation(g: Genotype, blob: str) -> bool:
    p = _search_float(blob, ("seq_mask_p", "seq_mask", "mask_p"))
    if p is not None:
        new = _clip(p, 0.0, 0.3)
        if g.training.augmentation.seq_mask_p == new:
            return False
        g.training.augmentation.seq_mask_p = new
        return True
    q = _search_float(blob, ("structure_edge_dropout", "edge_dropout"))
    if q is not None:
        new = _clip(q, 0.0, 0.3)
        if g.training.augmentation.structure_edge_dropout_p == new:
            return False
        g.training.augmentation.structure_edge_dropout_p = new
        return True
    if "seq_mask" in blob:
        if g.training.augmentation.seq_mask_p == 0.15:
            return False
        g.training.augmentation.seq_mask_p = 0.15
        return True
    return False


def _guided_optimization(g: Genotype, blob: str) -> bool:
    t = g.training
    if "adamw" in blob:
        if t.optimizer == "adamw":
            return False
        t.optimizer = "adamw"
        return True
    if "sgd" in blob:
        if t.optimizer == "sgd":
            return False
        t.optimizer = "sgd"
        return True
    if re.search(r"\badam\b", blob):
        if t.optimizer == "adam":
            return False
        t.optimizer = "adam"
        return True
    if "cosine" in blob:
        if t.scheduler == "cosine":
            return False
        t.scheduler = "cosine"
        return True
    if "scheduler" in blob and "step" in blob:
        if t.scheduler == "step":
            return False
        t.scheduler = "step"
        return True
    match = re.search(r"batch_size[^0-9]*(16|32|64|128|256)", blob)
    if match:
        bs = int(match.group(1))
        if t.batch_size == bs:
            return False
        t.batch_size = bs  # type: ignore[assignment]
        return True
    return False


def _guided_input(g: Genotype, blob: str) -> bool:
    changed = False
    for name, key in (
        ("peptide", ("sequence", "peptide")),
        ("mhc", ("sequence", "mhc")),
        ("tcr_alpha", ("sequence", "tcr_alpha")),
        ("tcr_beta", ("sequence", "tcr_beta")),
    ):
        if not re.search(rf"(inputs\.sequence\.{name}|sequence\.{name})", blob):
            continue
        enable = not any(w in blob for w in ("false", "disable", "off", "without"))
        if get_input_flag(g, key) is enable:
            continue
        set_input_flag(g, key, enable)
        changed = True
    if re.search(r"inputs\.pdb|pdb\.present", blob):
        enable = not any(w in blob for w in ("false", "disable", "off"))
        if g.inputs.pdb.present is not enable:
            set_input_flag(g, ("pdb",), enable)
            changed = True
    return changed


def _guided_model(g: Genotype, blob: str) -> bool:
    m = g.model
    if "masif_patch" in blob and surface_on(g):
        if m.type == "masif_patch_cross_attn":
            return False
        m.type = "masif_patch_cross_attn"  # type: ignore[assignment]
        m.ensemble_members = []
        return True
    if "masif_siamese" in blob and surface_on(g):
        if m.type == "masif_siamese":
            return False
        m.type = "masif_siamese"  # type: ignore[assignment]
        m.ensemble_members = []
        return True
    if "pdb_gnn" in blob and structure_on(g):
        if m.type == "pdb_gnn":
            return False
        m.type = "pdb_gnn"  # type: ignore[assignment]
        m.ensemble_members = []
        return True
    if "multimodal_cross" in blob or ("multimodal" in blob and "cross" in blob):
        if m.type == "multimodal_cross_attn":
            return False
        m.type = "multimodal_cross_attn"  # type: ignore[assignment]
        m.ensemble_members = []
        return True
    if "seq_cross" in blob:
        if m.type == "seq_cross_encoder":
            return False
        m.type = "seq_cross_encoder"  # type: ignore[assignment]
        m.ensemble_members = []
        return True
    if "seq_dual" in blob:
        if m.type == "seq_dual_encoder":
            return False
        m.type = "seq_dual_encoder"  # type: ignore[assignment]
        m.ensemble_members = []
        return True
    layers = re.search(r"num_layers[^0-9]*([1-6])", blob)
    if layers:
        n = int(layers.group(1))
        if m.num_layers == n:
            return False
        m.num_layers = n
        return True
    width = re.search(r"hidden_dim[^0-9]*(64|128|256|512|768)", blob)
    if width:
        return _apply_path(g, "model.hidden_dim", int(width.group(1)))
    drop = _search_float(blob, ("dropout",))
    if drop is not None:
        new = _clip(drop, 0.0, 0.5)
        if m.dropout == new:
            return False
        m.dropout = new
        return True
    if "residual" in blob:
        want = not any(w in blob for w in ("false", "off", "without", "disable"))
        if m.residual is want:
            return False
        m.residual = want
        return True
    return False


def _guided_structure(g: Genotype, blob: str) -> bool:
    st = g.encoders.structure
    if "interface" in blob and g.inputs.pdb.kind == "complex":
        if st.scope == "interface":
            return False
        st.scope = "interface"
        return True
    if "attention" in blob and "pool" in blob:
        if st.pooling == "attention":
            return False
        st.pooling = "attention"
        return True
    mapping = (
        ("se3", "se3_transformer"),
        ("egnn", "egnn"),
        ("mpnn", "mpnn"),
        ("gat", "gat"),
    )
    for key, arch in mapping:
        if key in blob:
            if st.arch == arch:
                return False
            st.arch = arch  # type: ignore[assignment]
            return True
    if "knn" in blob:
        st.edges.type = "knn"
        k = _search_float(blob, ("edges.k",))
        if k is not None:
            st.edges.k = int(_clip(k, 4, 32))
        return True
    if "radius" in blob:
        st.edges.type = "radius"
        r = _search_float(blob, ("radius",))
        if r is not None:
            st.edges.radius_A = _clip(r, 4.0, 15.0)
        return True
    return False
