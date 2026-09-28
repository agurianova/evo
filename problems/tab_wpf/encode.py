"""Type-aware feature encoder fit only on labeled context rows."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.model_selection import KFold, StratifiedKFold

from problems.tabular._common import tabular_data


@dataclass
class TypeAwareEncoder:
    """Encode assembled tabular matrices into a fixed-width float32 matrix."""

    columns: tuple[tabular_data.ColumnSpec, ...]
    task_type: str
    n_classes: int | None
    numeric_mean: np.ndarray
    numeric_std: np.ndarray
    binary_default: np.ndarray
    cat_frequency: list[dict[int, float]]
    include_target_encoding: bool = True
    cat_target_oof: list[np.ndarray] = field(default_factory=list)
    cat_target_maps: list[dict[int, np.ndarray]] = field(default_factory=list)
    cat_global_prior: list[np.ndarray] = field(default_factory=list)

    @property
    def output_dim(self) -> int:
        numeric_count = sum(1 for c in self.columns if c.kind == "numeric")
        binary_count = sum(1 for c in self.columns if c.kind == "binary")
        categorical_count = sum(1 for c in self.columns if c.kind == "categorical")
        target_width = 1 if self.task_type == tabular_data.REGRESSION else int(self.n_classes or 2)
        categorical_width = 2 + (target_width if self.include_target_encoding else 0)
        return numeric_count * 2 + binary_count * 2 + categorical_count * categorical_width

    @classmethod
    def fit(
        cls,
        X_fit: np.ndarray,
        y_fit: np.ndarray,
        *,
        columns: tuple[tabular_data.ColumnSpec, ...],
        task_type: str,
        n_classes: int | None,
        seed: int = 0,
        include_target_encoding: bool = True,
    ) -> TypeAwareEncoder:
        X_fit = np.asarray(X_fit, dtype=np.float64)
        y_fit = np.asarray(y_fit)
        n_rows, _ = X_fit.shape

        numeric_idx = [c.index for c in columns if c.kind == "numeric"]
        binary_idx = [c.index for c in columns if c.kind == "binary"]
        categorical_idx = [c.index for c in columns if c.kind == "categorical"]

        numeric_mean = np.zeros(len(numeric_idx), dtype=np.float64)
        numeric_std = np.ones(len(numeric_idx), dtype=np.float64)
        if numeric_idx:
            numeric_block = X_fit[:, numeric_idx]
            finite = np.isfinite(numeric_block)
            counts = finite.sum(axis=0)
            numeric_mean = np.divide(
                np.where(finite, numeric_block, 0.0).sum(axis=0),
                counts,
                out=np.zeros(len(numeric_idx), dtype=np.float64),
                where=counts > 0,
            )
            centered = np.where(finite, numeric_block - numeric_mean, 0.0)
            variance = np.divide(
                np.square(centered).sum(axis=0),
                counts,
                out=np.ones(len(numeric_idx), dtype=np.float64),
                where=counts > 0,
            )
            numeric_std = np.sqrt(variance)
            numeric_std[numeric_std < 1e-8] = 1.0

        binary_default = np.zeros(len(binary_idx), dtype=np.float64)
        if binary_idx:
            binary_block = X_fit[:, binary_idx]
            finite = np.isfinite(binary_block)
            counts = finite.sum(axis=0)
            binary_default = np.divide(
                np.where(finite, binary_block, 0.0).sum(axis=0),
                counts,
                out=np.zeros(len(binary_idx), dtype=np.float64),
                where=counts > 0,
            )

        cat_frequency: list[dict[int, float]] = []
        cat_target_oof: list[np.ndarray] = []
        cat_target_maps: list[dict[int, np.ndarray]] = []
        cat_global_prior: list[np.ndarray] = []

        y_numeric = y_fit.astype(np.float64)

        for local_j, col_idx in enumerate(categorical_idx):
            raw_codes = X_fit[:, col_idx]
            codes = np.where(np.isnan(raw_codes), -1, raw_codes).astype(np.int64)
            valid = codes >= 0
            freqs: dict[int, float] = {}
            if valid.any():
                unique, counts = np.unique(codes[valid], return_counts=True)
                total = counts.sum()
                freqs = {int(code): float(count / total) for code, count in zip(unique, counts)}
            cat_frequency.append(freqs)

            prior = _global_prior(y_numeric, task_type=task_type, n_classes=n_classes)
            cat_global_prior.append(prior)
            full_map = _target_encode_mapping(
                codes, y_numeric, task_type=task_type, n_classes=n_classes, prior=prior
            )
            cat_target_maps.append(full_map)

            oof_values = np.tile(prior, (n_rows, 1))
            if n_rows >= 2:
                folds = _target_folds(y_fit, task_type=task_type, seed=seed)
                for train_idx, val_idx in folds:
                    fold_prior = _global_prior(
                        y_numeric[train_idx],
                        task_type=task_type,
                        n_classes=n_classes,
                    )
                    fold_map = _target_encode_mapping(
                        codes[train_idx],
                        y_numeric[train_idx],
                        task_type=task_type,
                        n_classes=n_classes,
                        prior=fold_prior,
                    )
                    oof_values[val_idx] = _apply_target_map(
                        codes[val_idx], fold_map, prior=fold_prior
                    )
            else:
                oof_values = _apply_target_map(codes, full_map, prior=prior)
            cat_target_oof.append(oof_values)

        return cls(
            columns=columns,
            task_type=task_type,
            n_classes=n_classes,
            numeric_mean=numeric_mean,
            numeric_std=numeric_std,
            binary_default=binary_default,
            cat_frequency=cat_frequency,
            include_target_encoding=include_target_encoding,
            cat_target_oof=cat_target_oof,
            cat_target_maps=cat_target_maps,
            cat_global_prior=cat_global_prior,
        )

    def transform(self, X: np.ndarray, *, use_oof: bool = False) -> np.ndarray:
        X = np.asarray(X, dtype=np.float64)
        n_rows = X.shape[0]
        blocks: list[np.ndarray] = []

        numeric_idx = [c.index for c in self.columns if c.kind == "numeric"]
        binary_idx = [c.index for c in self.columns if c.kind == "binary"]
        categorical_idx = [c.index for c in self.columns if c.kind == "categorical"]

        if numeric_idx:
            block = X[:, numeric_idx]
            missing = np.isnan(block)
            filled = np.where(missing, self.numeric_mean, block)
            scaled = (filled - self.numeric_mean) / self.numeric_std
            blocks.extend([_as_2d(scaled), _as_2d(missing)])

        if binary_idx:
            block = X[:, binary_idx]
            missing = np.isnan(block)
            filled = np.where(missing, self.binary_default, block)
            blocks.extend([_as_2d(filled), _as_2d(missing)])

        for local_j, col_idx in enumerate(categorical_idx):
            raw_codes = X[:, col_idx]
            codes = np.where(np.isnan(raw_codes), -1, raw_codes).astype(np.int64)
            freq_map = self.cat_frequency[local_j]
            freq = _as_2d(
                np.array(
                    [freq_map.get(int(code), 0.0) if code >= 0 else 0.0 for code in codes],
                    dtype=np.float32,
                )
            )
            if use_oof and len(self.cat_target_oof[local_j]) == n_rows:
                target_enc = _as_2d(self.cat_target_oof[local_j])
            else:
                target_enc = _apply_target_map(
                    codes,
                    self.cat_target_maps[local_j],
                    prior=self.cat_global_prior[local_j],
                )
            missing = _as_2d((codes < 0).astype(np.float32))
            blocks.append(freq)
            if self.include_target_encoding:
                blocks.append(target_enc)
            blocks.append(missing)

        if not blocks:
            return np.zeros((n_rows, 0), dtype=np.float32)
        return np.hstack(blocks).astype(np.float32)


def _global_prior(
    y_fit: np.ndarray, *, task_type: str, n_classes: int | None
) -> np.ndarray:
    if task_type == tabular_data.REGRESSION:
        return np.array([float(np.mean(y_fit))], dtype=np.float64)
    if n_classes is None or n_classes < 2:
        return np.array([0.5, 0.5], dtype=np.float64)
    counts = np.bincount(y_fit.astype(int), minlength=n_classes)
    # A small symmetric prior keeps unseen classes finite in tiny folds.
    return (counts + 1.0) / (counts.sum() + n_classes)


def _target_encode_mapping(
    fit_codes: np.ndarray,
    fit_y: np.ndarray,
    *,
    task_type: str,
    n_classes: int | None,
    prior: np.ndarray,
    smoothing: float = 10.0,
) -> dict[int, np.ndarray]:
    mapping: dict[int, np.ndarray] = {}
    for code in np.unique(fit_codes[fit_codes >= 0]):
        mask = fit_codes == code
        if task_type == tabular_data.REGRESSION:
            count = float(mask.sum())
            total = float(np.sum(fit_y[mask]))
            mapping[int(code)] = np.array(
                [(total + smoothing * prior[0]) / (count + smoothing)],
                dtype=np.float64,
            )
        else:
            counts = np.bincount(fit_y[mask].astype(int), minlength=n_classes or 2)
            mapping[int(code)] = (counts + smoothing * prior) / (counts.sum() + smoothing)
    if not mapping:
        return {-1: prior.copy()}
    return mapping


def _as_2d(values: np.ndarray) -> np.ndarray:
    array = np.asarray(values, dtype=np.float32)
    return array if array.ndim == 2 else array.reshape(-1, 1)


def _apply_target_map(
    codes: np.ndarray, mapping: dict[int, np.ndarray], *, prior: np.ndarray
) -> np.ndarray:
    if len(codes) == 0:
        return np.zeros((0, len(prior)), dtype=np.float64)
    return np.vstack(
        [mapping.get(int(code), prior) if code >= 0 else prior for code in codes]
    ).astype(np.float64)


def _target_folds(y: np.ndarray, *, task_type: str, seed: int):
    n_rows = len(y)
    if task_type != tabular_data.REGRESSION:
        _, counts = np.unique(y.astype(int), return_counts=True)
        if len(counts) >= 2 and int(counts.min()) >= 2:
            n_splits = min(5, int(counts.min()))
            splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=seed)
            return splitter.split(np.arange(n_rows), y.astype(int))
    splitter = KFold(n_splits=min(5, n_rows), shuffle=True, random_state=seed)
    return splitter.split(np.arange(n_rows))
