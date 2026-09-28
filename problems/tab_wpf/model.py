"""Predictor graph model implementing the tabular fit_predict contract."""

from __future__ import annotations

import numpy as np
from sklearn.metrics import log_loss, mean_squared_error
from sklearn.model_selection import train_test_split

from problems.tabular._common import tabular_data

from .execution import execute_graph_triplet
from .graph import PredictorGraph, ReadoutConfig
from .readout import fit_readout, predict_readout


class PredictorGraphModel:
    """Reverse-SCM DAG that predicts targets directly."""

    def __init__(
        self,
        graph: PredictorGraph,
        dataset_name: str | None = None,
        *,
        columns: tuple[tabular_data.ColumnSpec, ...] | None = None,
        task_type: str | None = None,
        n_classes: int | None = None,
    ):
        self.graph = graph
        self.dataset_name = dataset_name
        if dataset_name is not None:
            dataset = tabular_data.load_dataset(dataset_name)
            self.task_type = dataset.task_type
            self.n_classes = dataset.n_classes
            self.columns = dataset.columns
        else:
            if columns is None or task_type is None:
                raise ValueError(
                    "dataset_name or both columns and task_type must be provided"
                )
            self.task_type = task_type
            self.n_classes = n_classes
            self.columns = columns

    def _resolve_readout_kind(self) -> ReadoutConfig:
        readout = self.graph.readout.model_copy()
        if self.task_type == tabular_data.REGRESSION:
            readout.kind = "ridge"
        elif readout.kind == "ridge":
            readout.kind = "logistic"
        return readout

    def _fit_predict_once(
        self,
        X_train,
        y_train,
        X_val,
        X_query,
        *,
        readout_config: ReadoutConfig | None = None,
    ):
        train_x = np.asarray(X_train, dtype=np.float64)
        train_y = np.asarray(y_train)
        val_x = np.asarray(X_val, dtype=np.float64)
        query_x = np.asarray(X_query, dtype=np.float64)
        readout = readout_config or self._resolve_readout_kind()

        features, _ = execute_graph_triplet(
            self.graph,
            train_x,
            val_x,
            query_x,
            y_fit=train_y,
            columns=self.columns,
            task_type=self.task_type,
            n_classes=self.n_classes,
        )
        self.generated_feature_count_ = int(features.fit.shape[1])
        readout_state = fit_readout(
            features.fit,
            train_y,
            config=readout,
            task_type=self.task_type,
            n_classes=self.n_classes,
        )
        return predict_readout(
            readout_state,
            features.query,
            task_type=self.task_type,
            n_classes=self.n_classes,
        )

    def fit_predict(self, X_train, y_train, X_val, y_val, X_query):
        base_readout = self._resolve_readout_kind()
        candidates = sorted(
            {
                max(1e-4, min(1e4, base_readout.alpha * multiplier))
                for multiplier in (0.1, 1.0, 10.0)
            }
        )
        best_loss = np.inf
        search_readout = base_readout
        train_x = np.asarray(X_train, dtype=np.float64)
        train_y = np.asarray(y_train)
        val_x = np.asarray(X_val, dtype=np.float64)
        val_y = np.asarray(y_val)
        if len(val_x):
            empty = train_x[:0]
            search_features, _ = execute_graph_triplet(
                self.graph,
                train_x,
                empty,
                val_x,
                y_fit=train_y,
                columns=self.columns,
                task_type=self.task_type,
                n_classes=self.n_classes,
            )
            for alpha in candidates:
                candidate = base_readout.model_copy(update={"alpha": alpha})
                try:
                    state = fit_readout(
                        search_features.fit,
                        train_y,
                        config=candidate,
                        task_type=self.task_type,
                        n_classes=self.n_classes,
                    )
                    val_pred = predict_readout(
                        state,
                        search_features.query,
                        task_type=self.task_type,
                        n_classes=self.n_classes,
                    )
                    loss = self._validation_loss(val_y, val_pred)
                except (ValueError, FloatingPointError):
                    continue
                if loss < best_loss:
                    best_loss = loss
                    search_readout = candidate

        self.selected_alpha_ = search_readout.alpha

        fit_x = np.concatenate([np.asarray(X_train), np.asarray(X_val)])
        fit_y = np.concatenate([np.asarray(y_train), np.asarray(y_val)])
        empty = np.asarray(X_val)[:0]
        return self._fit_predict_once(
            fit_x,
            fit_y,
            empty,
            X_query,
            readout_config=search_readout,
        )

    def predict_episode(
        self,
        X_context,
        y_context,
        X_query,
        *,
        validation_fraction: float = 0.2,
        seed: int = 0,
    ) -> np.ndarray:
        """Predict query targets from labeled context only.

        The inner validation rows used to select the readout regularization are
        carved deterministically out of the labeled context.  Query labels are
        not an argument and therefore cannot enter graph fitting.
        """

        X = np.asarray(X_context, dtype=np.float64)
        y = np.asarray(y_context)
        query = np.asarray(X_query, dtype=np.float64)
        if len(X) != len(y):
            raise ValueError("X_context and y_context row counts differ")
        if len(X) < 10:
            raise ValueError("predict_episode requires at least 10 context rows")
        if not 0.05 <= validation_fraction <= 0.5:
            raise ValueError("validation_fraction must be in [0.05, 0.5]")

        indices = np.arange(len(X))
        stratify = None
        if self.task_type != tabular_data.REGRESSION:
            _, counts = np.unique(y.astype(int), return_counts=True)
            if len(counts) >= 2 and int(counts.min()) >= 2:
                stratify = y.astype(int)
        fit_idx, val_idx = train_test_split(
            indices,
            test_size=validation_fraction,
            random_state=seed,
            shuffle=True,
            stratify=stratify,
        )
        return self.fit_predict(
            X[fit_idx],
            y[fit_idx],
            X[val_idx],
            y[val_idx],
            query,
        )

    def _validation_loss(self, y_true: np.ndarray, prediction: np.ndarray) -> float:
        if len(y_true) == 0:
            return 0.0
        if self.task_type == tabular_data.REGRESSION:
            return float(mean_squared_error(y_true.astype(np.float64), prediction))
        if self.n_classes is None or self.n_classes < 2:
            raise ValueError("classification validation requires n_classes >= 2")
        probabilities = np.clip(np.asarray(prediction, dtype=np.float64), 1e-12, 1.0)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        return float(
            log_loss(y_true.astype(int), probabilities, labels=np.arange(self.n_classes))
        )
