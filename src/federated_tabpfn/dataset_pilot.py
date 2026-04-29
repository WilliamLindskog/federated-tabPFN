from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import time
from typing import Any

import numpy as np
import pandas as pd
from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp
from flwr_datasets import FederatedDataset
from flwr_datasets.partitioner import DirichletPartitioner, IidPartitioner, LinearPartitioner
from flwr.serverapp import Grid, ServerApp
from flwr.serverapp.strategy import FedAvg
from flwr.simulation import run_simulation
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import SGDClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

from .pilot import _arrays_num_bytes, _client_id_from_context, _resource_usage, _result_to_history_dict
from .project import default_paths

ADULT_DATASET_NAME = "scikit-learn/adult-census-income"
ADULT_TARGET_COLUMN = "income"


@dataclass(frozen=True)
class ClientPartition:
    x_train: np.ndarray
    y_train: np.ndarray
    x_eval: np.ndarray
    y_eval: np.ndarray


def _normalize_selected_dataset(selected_dataset: str) -> str:
    if selected_dataset == "adult_engineering_slice":
        return "adult"
    return selected_dataset


def _adult_partitioner(selected_split_regime: str, num_clients: int) -> Any:
    if selected_split_regime == "iid":
        return IidPartitioner(num_partitions=num_clients)
    if selected_split_regime == "label_skew":
        return DirichletPartitioner(
            num_partitions=num_clients,
            partition_by=ADULT_TARGET_COLUMN,
            alpha=1.5,
            min_partition_size=50,
            self_balancing=True,
            seed=42,
        )
    if selected_split_regime == "quantity_skew":
        return LinearPartitioner(num_partitions=num_clients)
    raise ValueError(
        f"Dataset-backed baseline currently supports split regimes 'iid', 'label_skew', and 'quantity_skew', got '{selected_split_regime}'."
    )


def _load_adult_partition_frames(
    *,
    max_rows: int,
    num_clients: int,
    selected_split_regime: str,
) -> list[pd.DataFrame]:
    fds = FederatedDataset(
        dataset=ADULT_DATASET_NAME,
        partitioners={"train": _adult_partitioner(selected_split_regime, num_clients)},
    )
    partitions: list[pd.DataFrame] = []
    per_client_cap = max(4, int(np.ceil(max_rows / num_clients))) if max_rows > 0 else None
    for partition_id in range(num_clients):
        frame = pd.DataFrame(fds.load_partition(partition_id, "train").with_format("pandas")[:])
        frame = frame.replace("?", np.nan).dropna().reset_index(drop=True)
        if per_client_cap is not None and len(frame) > per_client_cap:
            frame = frame.sample(n=per_client_cap, random_state=42 + partition_id).reset_index(drop=True)
        partitions.append(frame)
    if not any(len(frame) for frame in partitions):
        raise ValueError("No Adult engineering-slice rows were loaded after filtering.")
    return partitions


def _preprocess_adult(features: pd.DataFrame) -> np.ndarray:
    transformer = _fit_adult_preprocessor(features)
    transformed = transformer.transform(features)
    return np.asarray(transformed, dtype=np.float64)


def _fit_adult_preprocessor(features: pd.DataFrame) -> ColumnTransformer:
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
    transformer.fit(features)
    return transformer


def _frame_to_client_partition(frame: pd.DataFrame, preprocessor: ColumnTransformer, seed: int) -> ClientPartition:
    if len(frame) < 4:
        raise ValueError("A client partition became too small after filtering to support train/eval splitting.")
    target = LabelEncoder().fit_transform(frame[ADULT_TARGET_COLUMN])
    features = frame.drop(columns=[ADULT_TARGET_COLUMN])
    x = np.asarray(preprocessor.transform(features), dtype=np.float64)
    unique_labels, counts = np.unique(target, return_counts=True)
    can_stratify = len(unique_labels) > 1 and np.all(counts >= 2)
    x_train, x_eval, y_train, y_eval = train_test_split(
        x,
        target,
        test_size=0.25,
        random_state=seed,
        stratify=target if can_stratify else None,
    )
    return ClientPartition(
        x_train=x_train,
        y_train=y_train,
        x_eval=x_eval,
        y_eval=y_eval,
    )


@lru_cache(maxsize=8)
def _dataset_state(
    selected_dataset: str,
    max_rows: int,
    num_clients: int,
    selected_split_regime: str,
) -> tuple[list[ClientPartition], int]:
    normalized_dataset = _normalize_selected_dataset(selected_dataset)
    if normalized_dataset != "adult":
        raise ValueError(
            f"Dataset-backed baseline is only implemented for the Adult engineering slice right now, got '{selected_dataset}'."
        )
    frames = _load_adult_partition_frames(
        max_rows=max_rows,
        num_clients=num_clients,
        selected_split_regime=selected_split_regime,
    )
    combined_features = pd.concat([frame.drop(columns=[ADULT_TARGET_COLUMN]) for frame in frames], ignore_index=True)
    preprocessor = _fit_adult_preprocessor(combined_features)
    partitions = [
        _frame_to_client_partition(frame, preprocessor, seed=42 + partition_id)
        for partition_id, frame in enumerate(frames)
    ]
    return partitions, partitions[0].x_train.shape[1]


def _create_model(n_features: int) -> SGDClassifier:
    model = SGDClassifier(
        loss="log_loss",
        penalty="l2",
        alpha=0.0001,
        max_iter=1,
        tol=None,
        random_state=42,
    )
    bootstrap_x = np.zeros((2, n_features), dtype=np.float64)
    bootstrap_y = np.array([0, 1], dtype=np.int64)
    model.partial_fit(bootstrap_x, bootstrap_y, classes=np.array([0, 1], dtype=np.int64))
    return model


def _get_model_parameters(model: SGDClassifier) -> list[np.ndarray]:
    return [model.coef_.astype(np.float64), model.intercept_.astype(np.float64)]


def _set_model_parameters(model: SGDClassifier, parameters: list[np.ndarray], n_features: int) -> None:
    coef, intercept = parameters
    model.coef_ = coef.astype(np.float64)
    model.intercept_ = intercept.astype(np.float64)
    model.classes_ = np.array([0, 1], dtype=np.int64)
    model.n_features_in_ = n_features


def _run_dataset_baseline_simulation(
    *,
    run_name: str,
    selected_dataset: str,
    selected_baseline: str,
    selected_split_regime: str,
    num_clients: int,
    num_rounds: int,
    max_rows: int,
) -> Path:
    partitions, n_features = _dataset_state(selected_dataset, max_rows, num_clients, selected_split_regime)
    initial_model = _create_model(n_features)
    initial_ndarrays = _get_model_parameters(initial_model)
    model_parameter_bytes = _arrays_num_bytes(initial_ndarrays)

    client_app = ClientApp()

    @client_app.train()
    def train(msg: Message, context: Context) -> Message:
        partition_id = int(_client_id_from_context(context))
        partition = partitions[partition_id]
        model = _create_model(n_features)
        _set_model_parameters(model, msg.content["arrays"].to_numpy_ndarrays(), n_features)
        model.partial_fit(partition.x_train, partition.y_train)
        probabilities = model.predict_proba(partition.x_train)
        metrics = MetricRecord(
            {
                "train_loss": round(float(_binary_log_loss(partition.y_train, probabilities)), 6),
                "num-examples": len(partition.x_train),
            }
        )
        content = RecordDict({"arrays": ArrayRecord(_get_model_parameters(model)), "metrics": metrics})
        return Message(content=content, reply_to=msg)

    @client_app.evaluate()
    def evaluate(msg: Message, context: Context) -> Message:
        partition_id = int(_client_id_from_context(context))
        partition = partitions[partition_id]
        model = _create_model(n_features)
        _set_model_parameters(model, msg.content["arrays"].to_numpy_ndarrays(), n_features)
        probabilities = model.predict_proba(partition.x_eval)
        predictions = np.argmax(probabilities, axis=1)
        metrics = MetricRecord(
            {
                "accuracy": round(float(np.mean(predictions == partition.y_eval)), 6),
                "eval_loss": round(float(_binary_log_loss(partition.y_eval, probabilities)), 6),
                "num-examples": len(partition.x_eval),
            }
        )
        return Message(content=RecordDict({"metrics": metrics}), reply_to=msg)

    server_app = ServerApp()
    result_box: dict[str, Any] = {}

    @server_app.main()
    def main(grid: Grid, context: Context) -> None:
        strategy = FedAvg(
            fraction_train=1.0,
            fraction_evaluate=1.0,
            min_train_nodes=num_clients,
            min_evaluate_nodes=num_clients,
            min_available_nodes=num_clients,
        )
        result_box["result"] = strategy.start(
            grid=grid,
            initial_arrays=ArrayRecord(initial_ndarrays),
            num_rounds=num_rounds,
        )

    run_dir = default_paths().results / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = run_dir / "dataset-baseline-summary.json"
    if artifact_path.exists():
        artifact_path.unlink()

    started_at = time.time()
    run_simulation(
        server_app=server_app,
        client_app=client_app,
        num_supernodes=num_clients,
        verbose_logging=False,
    )
    runtime_seconds = round(time.time() - started_at, 4)
    result = result_box["result"]
    resource_usage = _resource_usage()
    estimated_downstream_bytes = model_parameter_bytes * num_clients * num_rounds
    estimated_upstream_bytes = model_parameter_bytes * num_clients * num_rounds
    report = {
        "run_name": run_name,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started_at)),
        "completed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "framework": "flower",
        "execution_mode": "local",
        "dataset": selected_dataset,
        "baseline": selected_baseline,
        "split_regime": selected_split_regime,
        "num_clients": num_clients,
        "num_rounds": num_rounds,
        "max_rows": max_rows,
        "runtime_seconds": runtime_seconds,
        "train_seconds": runtime_seconds,
        "model_parameter_bytes": model_parameter_bytes,
        "estimated_downstream_bytes": estimated_downstream_bytes,
        "estimated_upstream_bytes": estimated_upstream_bytes,
        **resource_usage,
        "train_examples_per_client": [len(partition.x_train) for partition in partitions],
        "eval_examples_per_client": [len(partition.x_eval) for partition in partitions],
        "history": _result_to_history_dict(result),
        "notes": [
            "This dataset-backed benchmark uses Flower's Message API with the local simulation runtime.",
            "The Adult engineering slice now supports iid, label_skew, and quantity_skew partitioning via Flower Datasets.",
        ],
    }
    artifact_path.write_text(__import__("json").dumps(report, indent=2) + "\n", encoding="utf-8")
    return artifact_path


def _binary_log_loss(y_true: np.ndarray, probabilities: np.ndarray) -> float:
    positive_prob = np.clip(probabilities[:, 1], 1e-7, 1 - 1e-7)
    negative_prob = 1.0 - positive_prob
    return float(-np.mean((y_true * np.log(positive_prob)) + ((1 - y_true) * np.log(negative_prob))))


def run_dataset_backed_logreg(config: dict[str, Any], run_name: str) -> Path:
    pilot = config.get("pilot", {})
    selected_dataset = str(pilot.get("selected_dataset", "adult_engineering_slice"))
    selected_baseline = str(pilot.get("selected_baseline", "logistic_regression"))
    if selected_baseline != "logistic_regression":
        raise ValueError(
            f"Dataset-backed baseline is only implemented for 'logistic_regression' right now, got '{selected_baseline}'."
        )

    num_clients = int(pilot.get("num_clients", 2))
    num_rounds = int(pilot.get("num_rounds", 1))
    max_rows = int(pilot.get("dataset_backed_max_rows", 2000))
    selected_split_regime = str(pilot.get("selected_split_regime", "iid"))
    _dataset_state(selected_dataset, max_rows, num_clients, selected_split_regime)
    return _run_dataset_baseline_simulation(
        run_name=run_name,
        selected_dataset=selected_dataset,
        selected_baseline=selected_baseline,
        selected_split_regime=selected_split_regime,
        num_clients=num_clients,
        num_rounds=num_rounds,
        max_rows=max_rows,
    )