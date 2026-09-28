"""Compile a genotype to a fit/score predictor.

Frozen numpy features (sequence composition, V/J one-hot, MaSIF, Cα readout)
always enter the head. When the genotype asks for a sequence Transformer/CNN,
a GAT on Cα, or cross-attention — or when the MLP has hidden layers so
dropout / residual / optimizer / scheduler matter — the head is a PyTorch
module. ``num_layers==1`` + ``mlp_features`` stays sklearn logistic.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

try:
    from problems.pmhctcr.features import build_feature_matrix, hard_negative_index
    from problems.pmhctcr.genotype import (
        Genotype,
        cross_kind,
        loads,
        sequence_on,
        structure_on,
        surface_on,
        uses_learned_cross,
        uses_learned_gat,
        uses_learned_sequence,
        uses_siamese,
    )
    from problems.pmhctcr.nn_model import (
        TorchPredictor,
        use_torch_head,
    )
except ImportError:
    from features import build_feature_matrix, hard_negative_index
    from genotype import (
        Genotype,
        cross_kind,
        loads,
        sequence_on,
        structure_on,
        surface_on,
        uses_learned_cross,
        uses_learned_gat,
        uses_learned_sequence,
        uses_siamese,
    )
    from nn_model import (
        TorchPredictor,
        use_torch_head,
    )


def _calibrate(p: np.ndarray, temperature: float) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    if abs(temperature - 1.0) < 1e-12:
        return p
    logit = np.log(p / (1.0 - p))
    return 1.0 / (1.0 + np.exp(-logit / temperature))


def _class_weight(g: Genotype) -> dict[int, float] | str:
    if g.training.loss == "focal":
        gamma = float(g.training.focal_gamma or 2.0)
        return {0: 1.0, 1: float(2.0 ** max(gamma - 1.0, 0.0))}
    return "balanced"


def _C(g: Genotype) -> float:
    wd = float(g.training.weight_decay)
    return float(np.clip(1.0 / max(wd, 1e-8), 0.1, 1e6))


def hidden_layer_sizes(g: Genotype) -> tuple[int, ...]:
    """Hidden widths of the sklearn linear path. Empty → no hidden layer."""
    n = int(g.model.num_layers)
    if n <= 1:
        return ()
    h = int(g.model.hidden_dim)
    return tuple(h for _ in range(n - 1))


def _make_head(g: Genotype):
    return LogisticRegression(
        max_iter=400,
        class_weight=_class_weight(g),
        C=_C(g),
        solver="lbfgs",
        random_state=int(g.seed),
    )


class CompiledPredictor:
    def __init__(self, genotype: Genotype):
        self.genotype = genotype
        self.model = _make_head(genotype)
        self._prior = 0.1
        self._fitted = False
        self._members: list[Any] = []
        if (
            genotype.model.type == "ensemble"
            and len(genotype.model.ensemble_members) >= 2
        ):
            for member in genotype.model.ensemble_members:
                sub = genotype.model_copy(deep=True)
                sub.model.type = member.type  # type: ignore[assignment]
                sub.model.hidden_dim = member.hidden_dim
                sub.model.num_layers = member.num_layers
                sub.model.num_heads = member.num_heads
                sub.model.dropout = member.dropout
                sub.model.residual = member.residual
                sub.model.ensemble_members = []
                self._members.append(compile_genotype(sub))

    def fit(self, train_df: pd.DataFrame) -> None:
        if self._members:
            for m in self._members:
                m.fit(train_df)
            self._fitted = any(m._fitted for m in self._members)
            self._prior = self._members[0]._prior
            return
        y = train_df["label"].to_numpy(dtype=int)
        self._prior = float(y.mean()) if len(y) else 0.1
        rng = np.random.default_rng(self.genotype.seed + 7)
        idx = hard_negative_index(train_df, self.genotype, rng)
        part = train_df.iloc[idx]
        x = build_feature_matrix(self.genotype, part, train=True)
        y = part["label"].to_numpy(dtype=int)
        if x.shape[0] < 2 or np.unique(y).size < 2 or np.allclose(x, x[:1]):
            self._fitted = False
            return
        self.model.fit(x, y)
        self._fitted = True

    def score(self, rows_df: pd.DataFrame) -> np.ndarray:
        if self._members:
            stacked = np.stack([m.score(rows_df) for m in self._members], axis=0)
            return stacked.mean(axis=0)
        if not self._fitted:
            raw = np.full(len(rows_df), self._prior, dtype=float)
            return _calibrate(raw, self.genotype.calibration.temperature)
        x = build_feature_matrix(self.genotype, rows_df, train=False)
        proba = self.model.predict_proba(x)
        classes = list(self.model.classes_)
        if 1 in classes:
            raw = proba[:, classes.index(1)]
        else:
            raw = np.zeros(len(rows_df), dtype=float)
        return _calibrate(raw, self.genotype.calibration.temperature)


def _coerce_genotype(payload: Genotype | dict[str, Any] | str) -> Genotype:
    """Accept JSON, dict, or a Genotype from either import path."""
    if isinstance(payload, Genotype):
        return payload
    if isinstance(payload, (str, dict)):
        return loads(payload)
    dump = getattr(payload, "model_dump", None)
    if callable(dump):
        return loads(dump(mode="json"))
    raise TypeError(f"cannot compile genotype from {type(payload)!r}")


def describe_compiled(payload: Genotype | dict[str, Any] | str) -> dict[str, Any]:
    """What the JSON actually instantiates. Fields listed as ignored do not train."""
    g = _coerce_genotype(payload)
    torch_head = use_torch_head(g)
    learned_seq = uses_learned_sequence(g)
    ignored: list[str] = []
    if g.model.type == "mlp_features" and sequence_on(g) and not learned_seq:
        if g.encoders.sequence.arch == "protein_lm":
            ignored.append(
                "SeqEncoder off; encoders.sequence.arch=protein_lm is the frozen ESM-2 8M cache"
            )
        else:
            ignored.append(
                "encoders.sequence.arch="
                f"{g.encoders.sequence.arch} (bag-of-AA; no SeqEncoder until "
                "CHANGE_SEQUENCE cnn/transformer or CHANGE_MODEL seq_dual/seq_cross/multimodal)"
            )
    if (
        g.encoders.sequence.pooling == "attention"
        and not learned_seq
        and g.encoders.sequence.arch != "protein_lm"
    ):
        ignored.append(
            "encoders.sequence.pooling=attention unused on tabular path (no entropy proxy; "
            "attention pooling lives on SeqEncoder / GATEncoder)"
        )
    if g.encoders.structure.arch == "se3_transformer" and uses_learned_gat(g):
        ignored.append(
            "encoders.structure.arch=se3_transformer name: Cα distance kernel exp(-0.5 d), not SE(3)"
        )
    if g.training.loss != "bce" and torch_head:
        ignored.append(
            f"training.loss={g.training.loss} is 0.1× aux; primary train signal is within-pMHC rank"
        )
    if not torch_head:
        ignored.append(
            "model.dropout / residual / optimizer / scheduler (sklearn logistic path)"
        )
    return {
        "head": "torch" if torch_head else "sklearn",
        "learned_sequence": learned_seq,
        "learned_gat": uses_learned_gat(g),
        "learned_cross": uses_learned_cross(g),
        "learned_siamese": uses_siamese(g),
        "cross_kind": cross_kind(g),
        "tabular_sequence": sequence_on(g),
        "tabular_surface": surface_on(g),
        "tabular_structure": structure_on(g),
        "interaction_pairs": list(g.interaction.pairs),
        "ignored": ignored,
    }


def compile_genotype(
    payload: Genotype | dict[str, Any] | str,
) -> CompiledPredictor | TorchPredictor:
    g = _coerce_genotype(payload)
    if g.model.type == "ensemble" and len(g.model.ensemble_members) >= 2:
        return CompiledPredictor(g)
    if use_torch_head(g):
        return TorchPredictor(g)
    return CompiledPredictor(g)
