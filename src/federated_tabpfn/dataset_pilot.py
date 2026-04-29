from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import flwr as fl
import numpy as np
import pandas as pd
from flwr.common import Context
from sklearn.compose import ColumnTransformer
from sklearn.datasets import fetch_openml
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, log_loss
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

from .pilot import _average_metrics, _client_id_from_context, _history_to_dict
from .project import default_paths


@dataclass(frozen=True)
class ClientPartition:
    x_train: np.ndarray
    y_train: np.ndarray
    x_eval: np.ndarray
    y_eval: np.ndarray


def _load_adult_frame(max_rows: int) -> tuple[pd.DataFrame, np.ndarray]:
    bunch = fetch_openml("adult", version=2, as_frame=True)
    frame = bunch.frame.dropna().reset_index(drop=True)
    if max_rows and len(frame) > max_rows:
        frame = frame.sample(n=max_rows, random_state=42).reset_index(drop=True)
    target = LabelEncoder().fit_transform(frame["class"])
    features = frame.drop(columns=["class"])
    return features, target


def _preprocess_adult(features: pd.DataFrame) -> np.ndarray:
    categorical = [column for column in features.columns if str(features[column].dtype) in {"category", "object"}]
    numeric = [column for column in features.columns if column not in categorical]
    transformer = ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), numeric),
            (
                "categorical",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                categorical,
            ),
        ]
    )
    transformed = transformer.fit_transform(features)
    return np.asarray(transformed, dtype=np.float64)


def _partition_clients(x: np.ndarray, y: np.ndarray, num_clients: int) -> list[ClientPartition]:
    x_train, x_eval, y_train, y_eval = train_test_split(
        x,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )
    train_indices = np.array_split(np.arange(len(x_train)), num_clients)
    eval_indices = np.array_split(np.arange(len(x_eval)), num_clients)
    partitions: list[ClientPartition] = []
    for train_idx, eval_idx in zip(train_indices, eval_indices, strict=True):
        partitions.append(
            ClientPartition(
                x_train=x_train[train_idx],
                y_train=y_train[train_idx],
                x_eval=x_eval[eval_idx],
                y_eval=y_eval[eval_idx],
            )
        )
    return partitions


class FederatedLogRegClient(fl.client.NumPyClient):
    def __init__(self, cid: str, partition: ClientPartition, n_features: int) -> None:
        self.cid = cid
        self.partition = partition
        self.n_features = n_features
        self.classes_ = np.array([0, 1], dtype=np.int64)
        self.model = SGDClassifier(
            loss="log_loss",
            penalty="l2",
            alpha=0.0001,
            max_iter=1,
            tol=None,
            random_state=42,
        )
        self.model.partial_fit(self.partition.x_train[:2], self.partition.y_train[:2], classes=self.classes_)

    def get_parameters(self, config: dict[str, Any]) -> list[np.ndarray]:
        return [self.model.coef_.astype(np.float64), self.model.intercept_.astype(np.float64)]

    def set_parameters(self, parameters: list[np.ndarray]) -> None:
        coef, intercept = parameters
        self.model.coef_ = coef.astype(np.float64)
        self.model.intercept_ = intercept.astype(np.float64)
        self.model.classes_ = self.classes_
        self.model.n_features_in_ = self.n_features

    def fit(self, parameters: list[np.ndarray], config: dict[str, Any]) -> tuple[list[np.ndarray], int, dict[str, Any]]:
        self.set_parameters(parameters)
        self.model.partial_fit(self.partition.x_train, self.partition.y_train)
        probabilities = self.model.predict_proba(self.partition.x_train)
        loss_value = float(log_loss(self.partition.y_train, probabilities, labels=[0, 1]))
        return self.get_parameters(config), len(self.partition.x_train), {"train_loss": round(loss_value, 6)}

    def evaluate(self, parameters: list[np.ndarray], config: dict[str, Any]) -> tuple[float, int, dict[str, Any]]:
        self.set_parameters(parameters)
        probabilities = self.model.predict_proba(self.partition.x_eval)
        predictions = np.argmax(probabilities, axis=1)
        accuracy = float(accuracy_score(self.partition.y_eval, predictions))
        loss_value = float(log_loss(self.partition.y_eval, probabilities, labels=[0, 1]))
        return loss_value, len(self.partition.x_eval), {"accuracy": round(accuracy, 6)}


def run_dataset_backed_logreg(config: dict[str, Any], run_name: str) -> Path:
    pilot = config.get("pilot", {})
    selected_dataset = str(pilot.get("selected_dataset", "adult"))
    selected_baseline = str(pilot.get("selected_baseline", "logistic_regression"))
    if selected_dataset != "adult":
        raise ValueError(f"Dataset-backed baseline is only implemented for 'adult' right now, got '{selected_dataset}'.")
    if selected_baseline != "logistic_regression":
        raise ValueError(
            f"Dataset-backed baseline is only implemented for 'logistic_regression' right now, got '{selected_baseline}'."
        )

    num_clients = int(pilot.get("num_clients", 2))
    num_rounds = int(pilot.get("num_rounds", 1))
    max_rows = int(pilot.get("dataset_backed_max_rows", 2000))

    features, target = _load_adult_frame(max_rows=max_rows)
    x = _preprocess_adult(features)
    partitions = _partition_clients(x, target, num_clients=num_clients)
    n_features = x.shape[1]

    run_dir = default_paths().results / run_name
    run_dir.mkdir(parents=True, exist_ok=True)

    strategy = fl.server.strategy.FedAvg(
        fraction_fit=1.0,
        fraction_evaluate=1.0,
        min_fit_clients=num_clients,
        min_evaluate_clients=num_clients,
        min_available_clients=num_clients,
        fit_metrics_aggregation_fn=_average_metrics,
        evaluate_metrics_aggregation_fn=_average_metrics,
    )

    def client_fn(context: Context | str) -> fl.client.Client:
        cid = int(_client_id_from_context(context))
        return FederatedLogRegClient(str(cid), partitions[cid], n_features=n_features).to_client()

    started_at = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    history = fl.simulation.start_simulation(
        client_fn=client_fn,
        num_clients=num_clients,
        config=fl.server.ServerConfig(num_rounds=num_rounds),
        strategy=strategy,
        client_resources={"num_cpus": 1},
        ray_init_args={"include_dashboard": False, "ignore_reinit_error": True},
    )
    runtime_seconds = round(time.perf_counter() - start, 4)

    report = {
        "run_name": run_name,
        "started_at": started_at,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "framework": config.get("framework"),
        "execution_mode": config.get("execution_mode"),
        "dataset": selected_dataset,
        "baseline": selected_baseline,
        "num_clients": num_clients,
        "num_rounds": num_rounds,
        "max_rows": max_rows,
        "runtime_seconds": runtime_seconds,
        "train_examples_per_client": [len(partition.x_train) for partition in partitions],
        "eval_examples_per_client": [len(partition.x_eval) for partition in partitions],
        "history": _history_to_dict(history),
        "notes": [
            "This is the first dataset-backed baseline slice.",
            "It uses the Adult dataset and federated logistic regression under Flower.",
        ],
    }
    artifact_path = run_dir / "dataset-baseline-summary.json"
    artifact_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return artifact_path