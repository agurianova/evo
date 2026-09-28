"""Closed operator catalog for reverse-SCM predictor DAGs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np
from sklearn.decomposition import PCA
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, StratifiedKFold
from sklearn.preprocessing import QuantileTransformer

from problems.tabular._common import tabular_data

from .graph import ActivationKind, OperatorKind


class OperatorExecutionError(RuntimeError):
    pass


def _activation(name: ActivationKind, values: np.ndarray) -> np.ndarray:
    if name == "tanh":
        return np.tanh(values)
    if name == "leaky_relu":
        return np.where(values >= 0, values, 0.01 * values)
    if name == "elu":
        return np.where(values >= 0, values, np.expm1(values))
    return values


def _check_finite(name: str, values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float64)
    if not np.all(np.isfinite(array)):
        raise OperatorExecutionError(f"{name}: output contains non-finite values")
    return array


@dataclass
class OperatorState:
    fitted: Any


class BaseOperator(ABC):
    op: OperatorKind
    uses_supervision: bool = False

    @abstractmethod
    def fit(
        self,
        X_fit: np.ndarray,
        y_fit: np.ndarray | None,
        params: dict[str, Any],
        *,
        task_type: str,
        n_classes: int | None,
    ) -> OperatorState:
        raise NotImplementedError

    @abstractmethod
    def transform(self, X: np.ndarray, state: OperatorState) -> np.ndarray:
        raise NotImplementedError

    def transform_fit(self, X_fit: np.ndarray, state: OperatorState) -> np.ndarray:
        """Transform fit rows; supervised operators override this with OOF output."""
        return self.transform(X_fit, state)

    def uses_supervision_for(self, params: dict[str, Any]) -> bool:
        return self.uses_supervision


class IdentityOperator(BaseOperator):
    op = "identity"
    uses_supervision = False

    def fit(self, X_fit, y_fit, params, *, task_type, n_classes):
        return OperatorState(fitted=None)

    def transform(self, X, state):
        return _check_finite("identity", X)


class StandardizeOperator(BaseOperator):
    op = "standardize"
    uses_supervision = False

    def fit(self, X_fit, y_fit, params, *, task_type, n_classes):
        mean = np.mean(X_fit, axis=0)
        std = np.std(X_fit, axis=0)
        std[std < 1e-8] = 1.0
        return OperatorState(fitted=(mean, std))

    def transform(self, X, state):
        mean, std = state.fitted
        return _check_finite("standardize", (X - mean) / std)


class QuantileOperator(BaseOperator):
    op = "quantile"
    uses_supervision = False

    def fit(self, X_fit, y_fit, params, *, task_type, n_classes):
        seed = int(params.get("seed", 0))
        n_quantiles = min(int(params.get("n_quantiles", 32)), max(X_fit.shape[0], 2))
        qt = QuantileTransformer(
            n_quantiles=n_quantiles,
            output_distribution=str(params.get("output_distribution", "normal")),
            random_state=seed,
        )
        qt.fit(X_fit)
        return OperatorState(fitted=qt)

    def transform(self, X, state):
        return _check_finite("quantile", state.fitted.transform(X))


class AffineActivationOperator(BaseOperator):
    op = "affine_activation"
    uses_supervision = True

    def uses_supervision_for(self, params):
        return str(params.get("fit", "pca")) == "supervised_ridge"

    def fit(self, X_fit, y_fit, params, *, task_type, n_classes):
        if y_fit is None:
            raise OperatorExecutionError("affine_activation requires y_fit")
        fit_mode = str(params.get("fit", "pca"))
        activation = str(params.get("activation", "tanh"))
        n_components = int(params.get("n_components", min(8, X_fit.shape[1])))
        alpha = float(params.get("alpha", 1.0))
        seed = int(params.get("seed", 0))
        n_components = max(1, min(n_components, X_fit.shape[1], X_fit.shape[0]))

        if fit_mode == "pca":
            pca = PCA(n_components=n_components, random_state=seed)
            pca.fit(X_fit)
            return OperatorState(
                fitted={
                    "mode": "pca",
                    "components": pca.components_.astype(np.float64),
                    "mean": pca.mean_.astype(np.float64),
                    "activation": activation,
                }
            )

        if fit_mode != "supervised_ridge":
            raise OperatorExecutionError(f"affine_activation: unknown fit mode {fit_mode!r}")

        target = _ridge_targets(
            y_fit,
            task_type=task_type,
            n_classes=n_classes,
        )
        supervised_width = min(n_components, target.shape[1])
        ridge = Ridge(alpha=alpha, random_state=seed)
        ridge.fit(X_fit, target[:, :supervised_width])
        oof_supervised = _cross_fitted_ridge_projection(
            X_fit,
            target[:, :supervised_width],
            y_fit,
            task_type=task_type,
            alpha=alpha,
            seed=seed,
        )

        pca = None
        extra_width = n_components - supervised_width
        if extra_width > 0:
            pca = PCA(n_components=extra_width, random_state=seed)
            pca.fit(X_fit)
            oof_extra = pca.transform(X_fit)
            oof_projected = np.hstack([oof_supervised, oof_extra])
        else:
            oof_projected = oof_supervised
        return OperatorState(
            fitted={
                "mode": "supervised_ridge",
                "ridge": ridge,
                "pca": pca,
                "activation": activation,
                "oof_train": np.asarray(oof_projected, dtype=np.float64),
            }
        )

    def transform(self, X, state):
        fitted = state.fitted
        if fitted["mode"] == "supervised_ridge":
            projected = _predict_supervised_projection(X, fitted)
            return _check_finite(
                "affine_activation", _activation(fitted["activation"], projected)
            )
        centered = X - fitted["mean"]
        projected = centered @ fitted["components"].T
        return _check_finite("affine_activation", _activation(fitted["activation"], projected))

    def transform_fit(self, X_fit, state):
        fitted = state.fitted
        if fitted["mode"] != "supervised_ridge":
            return self.transform(X_fit, state)
        oof = fitted["oof_train"]
        if len(oof) != len(X_fit):
            raise OperatorExecutionError("affine_activation: OOF row count mismatch")
        return _check_finite(
            "affine_activation", _activation(fitted["activation"], oof)
        )


class RBFFeaturesOperator(BaseOperator):
    op = "rbf_features"
    uses_supervision = False

    def fit(self, X_fit, y_fit, params, *, task_type, n_classes):
        seed = int(params.get("seed", 0))
        n_components = int(params.get("n_components", min(16, X_fit.shape[1] * 2)))
        lengthscale = float(params.get("lengthscale", 1.0))
        rng = np.random.default_rng(seed)
        n_features = X_fit.shape[1]
        n_components = max(1, n_components)
        weights = rng.normal(0.0, 1.0 / max(lengthscale, 1e-8), size=(n_components, n_features))
        bias = rng.uniform(0.0, 2 * np.pi, size=n_components)
        return OperatorState(fitted={"weights": weights, "bias": bias})

    def transform(self, X, state):
        weights = state.fitted["weights"]
        bias = state.fitted["bias"]
        projected = X @ weights.T + bias
        scale = 1.0 / np.sqrt(max(len(weights), 1))
        features = scale * np.cos(projected)
        features = np.concatenate([features, scale * np.sin(projected)], axis=1)
        return _check_finite("rbf_features", features)


class PairwiseProductOperator(BaseOperator):
    op = "pairwise_product"
    uses_supervision = False

    def fit(self, X_fit, y_fit, params, *, task_type, n_classes):
        seed = int(params.get("seed", 0))
        k = int(params.get("k", min(8, max(X_fit.shape[1] - 1, 1))))
        n_features = X_fit.shape[1]
        rng = np.random.default_rng(seed)
        if n_features < 2:
            pairs = []
        else:
            all_pairs = [(i, j) for i in range(n_features) for j in range(i + 1, n_features)]
            k = min(k, len(all_pairs))
            indices = rng.choice(len(all_pairs), size=k, replace=False)
            pairs = [all_pairs[int(i)] for i in indices]
        return OperatorState(fitted={"pairs": pairs})

    def transform(self, X, state):
        pairs = state.fitted["pairs"]
        if not pairs:
            return np.zeros((X.shape[0], 0), dtype=np.float64)
        products = [X[:, i] * X[:, j] for i, j in pairs]
        return _check_finite("pairwise_product", np.column_stack(products))


class ColumnGateOperator(BaseOperator):
    op = "column_gate"
    uses_supervision = True

    def fit(self, X_fit, y_fit, params, *, task_type, n_classes):
        if y_fit is None:
            raise OperatorExecutionError("column_gate requires y_fit")
        k = int(params.get("k", min(8, X_fit.shape[1])))
        seed = int(params.get("seed", 0))
        k = max(1, min(k, X_fit.shape[1]))
        scores = _association_scores(
            X_fit,
            y_fit,
            task_type=task_type,
            n_classes=n_classes,
        )
        top = np.argsort(scores)[::-1][:k]
        # Keep the original feature axis.  Selecting k unrelated columns into
        # positions 0..k-1 independently in every OOF fold makes a position
        # mean different things for different rows and for query data.  A
        # sparse mask is wider, but its channel semantics remain stable.
        oof_train = np.zeros_like(X_fit, dtype=np.float64)
        for train_idx, val_idx in _target_folds(y_fit, task_type=task_type, seed=seed):
            fold_scores = _association_scores(
                X_fit[train_idx],
                y_fit[train_idx],
                task_type=task_type,
                n_classes=n_classes,
            )
            fold_top = np.argsort(fold_scores)[::-1][:k]
            oof_train[np.ix_(val_idx, fold_top)] = X_fit[np.ix_(val_idx, fold_top)]
        return OperatorState(fitted={"indices": top, "oof_train": oof_train})

    def transform(self, X, state):
        indices = state.fitted["indices"]
        selected = np.zeros_like(X, dtype=np.float64)
        selected[:, indices] = X[:, indices]
        return _check_finite("column_gate", selected)

    def transform_fit(self, X_fit, state):
        oof = state.fitted["oof_train"]
        if len(oof) != len(X_fit):
            raise OperatorExecutionError("column_gate: OOF row count mismatch")
        return _check_finite("column_gate", oof)


OPERATOR_REGISTRY: dict[OperatorKind, BaseOperator] = {
    "identity": IdentityOperator(),
    "standardize": StandardizeOperator(),
    "quantile": QuantileOperator(),
    "affine_activation": AffineActivationOperator(),
    "rbf_features": RBFFeaturesOperator(),
    "pairwise_product": PairwiseProductOperator(),
    "column_gate": ColumnGateOperator(),
}


def get_operator(op: OperatorKind) -> BaseOperator:
    if op not in OPERATOR_REGISTRY:
        raise OperatorExecutionError(f"unknown operator {op!r}")
    return OPERATOR_REGISTRY[op]


def _ridge_targets(
    y: np.ndarray, *, task_type: str, n_classes: int | None
) -> np.ndarray:
    target = np.asarray(y)
    if task_type == tabular_data.REGRESSION:
        return target.astype(np.float64).reshape(-1, 1)
    width = int(n_classes or (int(np.max(target)) + 1))
    one_hot = np.zeros((len(target), width), dtype=np.float64)
    one_hot[np.arange(len(target)), target.astype(int)] = 1.0
    return one_hot


def _cross_fitted_ridge_projection(
    X: np.ndarray,
    target: np.ndarray,
    stratify_y: np.ndarray,
    *,
    task_type: str,
    alpha: float,
    seed: int,
) -> np.ndarray:
    oof = np.zeros((len(X), target.shape[1]), dtype=np.float64)
    if len(X) < 2:
        ridge = Ridge(alpha=alpha, random_state=seed)
        ridge.fit(X, target)
        return np.asarray(ridge.predict(X)).reshape(len(X), -1)
    for train_idx, val_idx in _target_folds(stratify_y, task_type=task_type, seed=seed):
        ridge = Ridge(alpha=alpha, random_state=seed)
        ridge.fit(X[train_idx], target[train_idx])
        oof[val_idx] = np.asarray(ridge.predict(X[val_idx])).reshape(len(val_idx), -1)
    return oof


def _predict_supervised_projection(X: np.ndarray, fitted: dict[str, Any]) -> np.ndarray:
    supervised = np.asarray(fitted["ridge"].predict(X)).reshape(len(X), -1)
    if fitted["pca"] is None:
        return supervised
    return np.hstack([supervised, fitted["pca"].transform(X)])


def _target_folds(y: np.ndarray, *, task_type: str, seed: int):
    n_rows = len(y)
    if task_type != tabular_data.REGRESSION:
        _, counts = np.unique(np.asarray(y).astype(int), return_counts=True)
        if len(counts) >= 2 and int(counts.min()) >= 2:
            splitter = StratifiedKFold(
                n_splits=min(5, int(counts.min())),
                shuffle=True,
                random_state=seed,
            )
            return splitter.split(np.arange(n_rows), np.asarray(y).astype(int))
    splitter = KFold(n_splits=min(5, n_rows), shuffle=True, random_state=seed)
    return splitter.split(np.arange(n_rows))


def _association_scores(
    X: np.ndarray,
    y: np.ndarray,
    *,
    task_type: str,
    n_classes: int | None,
) -> np.ndarray:
    _, n_features = X.shape
    scores = np.zeros(n_features, dtype=np.float64)
    targets = _ridge_targets(y, task_type=task_type, n_classes=n_classes)
    for j in range(n_features):
        col = X[:, j]
        if np.std(col) < 1e-8:
            continue
        correlations = []
        for target in targets.T:
            if np.std(target) < 1e-8:
                continue
            coefficient = float(np.corrcoef(col, target)[0, 1])
            if np.isfinite(coefficient):
                correlations.append(abs(coefficient))
        if correlations:
            scores[j] = max(correlations)
    return scores
