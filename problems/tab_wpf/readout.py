"""Linear readout heads for reverse-SCM predictor graphs."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression, Ridge

from problems.tabular._common import tabular_data

from .graph import ReadoutConfig


@dataclass
class ReadoutState:
    model: Ridge | LogisticRegression
    kind: str


def fit_readout(
    features: np.ndarray,
    y_fit: np.ndarray,
    *,
    config: ReadoutConfig,
    task_type: str,
    n_classes: int | None,
    seed: int = 0,
) -> ReadoutState:
    X = np.asarray(features, dtype=np.float64)
    y = np.asarray(y_fit)
    if task_type == tabular_data.REGRESSION:
        model = Ridge(alpha=config.alpha, random_state=seed)
        model.fit(X, y.astype(np.float64))
        return ReadoutState(model=model, kind="ridge")

    if n_classes is None or n_classes < 2:
        raise ValueError("classification requires n_classes >= 2")
    model = LogisticRegression(
        C=1.0 / config.alpha,
        max_iter=1000,
        random_state=seed,
        solver="lbfgs",
    )
    model.fit(X, y.astype(int))
    return ReadoutState(model=model, kind="logistic")


def predict_readout(
    state: ReadoutState,
    features: np.ndarray,
    *,
    task_type: str,
    n_classes: int | None,
) -> np.ndarray:
    X = np.asarray(features, dtype=np.float64)
    if state.kind == "ridge":
        return np.asarray(state.model.predict(X), dtype=np.float64)
    if n_classes is None:
        raise ValueError("classification requires n_classes")
    proba = state.model.predict_proba(X)
    full = np.zeros((proba.shape[0], n_classes), dtype=np.float64)
    full[:, state.model.classes_.astype(int)] = proba
    return full
