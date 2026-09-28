"""Sequence baseline: logistic regression on AA composition of epitope + CDR3s."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

_AA = "ACDEFGHIKLMNPQRSTVWY"


def _aa_frac(seq: object) -> np.ndarray:
    text = "" if seq is None or (isinstance(seq, float) and np.isnan(seq)) else str(seq)
    counts = np.zeros(len(_AA), dtype=np.float64)
    for ch in text:
        i = _AA.find(ch)
        if i >= 0:
            counts[i] += 1
    n = counts.sum()
    if n > 0:
        counts /= n
    return counts


def _features(df: pd.DataFrame) -> np.ndarray:
    rows = []
    for epi, a, b in zip(df["epitope_seq"], df["tcra_seq_cdr3"], df["tcrb_seq_cdr3"]):
        rows.append(np.concatenate([_aa_frac(epi), _aa_frac(a), _aa_frac(b)]))
    return np.stack(rows, axis=0)


class Cdr3Logistic:
    def __init__(self):
        self.model = LogisticRegression(
            max_iter=1000, class_weight="balanced", random_state=0
        )

    def fit(self, train_df: pd.DataFrame) -> None:
        x = _features(train_df)
        y = train_df["label"].to_numpy(dtype=int)
        self.model.fit(x, y)

    def score(self, rows_df: pd.DataFrame) -> np.ndarray:
        proba = self.model.predict_proba(_features(rows_df))
        classes = list(self.model.classes_)
        if 1 in classes:
            return proba[:, classes.index(1)]
        return np.zeros(len(rows_df), dtype=float)


def entrypoint():
    return Cdr3Logistic()
