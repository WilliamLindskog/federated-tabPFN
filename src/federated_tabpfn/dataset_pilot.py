from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os
import pickle
import time
from typing import Any

import numpy as np
import pandas as pd
import xgboost as xgb
from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp
from flwr_datasets import FederatedDataset
from flwr_datasets.partitioner import DirichletPartitioner, IidPartitioner, LinearPartitioner
from flwr.serverapp import Grid, ServerApp
from flwr.serverapp.strategy import FedAvg
from flwr.simulation import run_simulation
from sklearn.compose import ColumnTransformer
from sklearn.datasets import fetch_openml
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score, log_loss
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, StandardScaler

from .ensemble_strategy import arrayrecord_to_bytes, bytes_to_arrayrecord, decode_ensemble_payload, encode_ensemble_payload
from .pilot import (
    _arrays_num_bytes,
    _client_id_from_context,
    _resource_usage,
    _result_to_history_dict,
    _run_flower_app,
    _wait_for_fresh_artifact,
)
from .project import default_paths
from .study_registry import parse_dataset_key

ADULT_DATASET_NAME = "scikit-learn/adult-census-income"
ADULT_TARGET_COLUMN = "income"
SUPPORTED_DATASET_BACKED_BASELINES = frozenset({"logistic_regression", "random_forest", "xgboost", "tabpfn"})


@dataclass(frozen=True)
class ClientPartition:
    x_train: np.ndarray
    y_train: np.ndarray
    x_eval: np.ndarray
    y_eval: np.ndarray


@dataclass(frozen=True)
class DatasetState:
    partitions: list[ClientPartition]
    n_features: int
    classes: np.ndarray


def _normalize_selected_dataset(selected_dataset: str) -> str:
    if selected_dataset == "adult_engineering_slice":
        return "adult"
    if selected_dataset.startswith("openml:"):
        return "openml"
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


def _load_openml_frame(selected_dataset: str) -> pd.DataFrame:
    dataset = parse_dataset_key(selected_dataset)
    if dataset is None:
        raise ValueError(f"Expected an OpenML dataset key, got '{selected_dataset}'.")
    bunch = fetch_openml(
        data_id=dataset.data_id,
        as_frame=True,
        data_home=str(default_paths().openml_cache),
        parser="auto",
    )
    frame = bunch.frame.copy()
    if frame.isnull().any().any():
        frame = frame.dropna().reset_index(drop=True)
    return frame


def _encode_labels(labels: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    encoder = LabelEncoder()
    encoded = encoder.fit_transform(labels.astype(str))
    return encoded.astype(np.int64), encoder.classes_


def _iid_partition_indices(num_rows: int, num_clients: int, seed: int = 42) -> list[np.ndarray]:
    indices = np.arange(num_rows)
    rng = np.random.default_rng(seed)
    rng.shuffle(indices)
    return [partition.astype(np.int64) for partition in np.array_split(indices, num_clients)]


def _preprocess_adult(features: pd.DataFrame) -> np.ndarray:
    transformer = _fit_adult_preprocessor(features)
    transformed = transformer.transform(features)
    return np.asarray(transformed, dtype=np.float64)


def _fit_adult_preprocessor(features: pd.DataFrame) -> ColumnTransformer:
    categorical = [
        column
        for column in features.columns
        if pd.api.types.is_string_dtype(features[column])
        or pd.api.types.is_object_dtype(features[column])
        or isinstance(features[column].dtype, pd.CategoricalDtype)
        or pd.api.types.is_bool_dtype(features[column])
    ]
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


def _probability_matrix(probabilities: np.ndarray) -> np.ndarray:
    probabilities = np.asarray(probabilities, dtype=np.float64)
    if probabilities.ndim == 1:
        positive = np.clip(probabilities, 1e-7, 1.0 - 1e-7)
        negative = 1.0 - positive
        return np.column_stack([negative, positive])
    probabilities = np.clip(probabilities, 1e-7, 1.0)
    row_sums = probabilities.sum(axis=1, keepdims=True)
    return probabilities / np.clip(row_sums, 1e-7, None)


def _probability_metrics(
    y_true: np.ndarray,
    probabilities: np.ndarray,
    *,
    classes: np.ndarray,
) -> tuple[float, float]:
    probability_matrix = _probability_matrix(probabilities)
    predictions = np.argmax(probability_matrix, axis=1)
    accuracy = float(accuracy_score(y_true, predictions))
    loss_value = float(log_loss(y_true, probability_matrix, labels=list(range(len(classes)))))
    return accuracy, loss_value


def _frame_to_client_partition(frame: pd.DataFrame, preprocessor: ColumnTransformer, seed: int) -> ClientPartition:
    if len(frame) < 4:
        raise ValueError("A client partition became too small after filtering to support train/eval splitting.")
    target = frame[ADULT_TARGET_COLUMN].to_numpy(dtype=np.int64, copy=True)
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
        x_train=np.asarray(x_train, dtype=np.float64),
        y_train=np.asarray(y_train, dtype=np.int64),
        x_eval=np.asarray(x_eval, dtype=np.float64),
        y_eval=np.asarray(y_eval, dtype=np.int64),
    )


def _numeric_frame_to_client_partition(
    x: np.ndarray,
    y: np.ndarray,
    *,
    seed: int,
) -> ClientPartition:
    if len(x) < 4:
        raise ValueError("A client partition became too small after filtering to support train/eval splitting.")
    unique_labels, counts = np.unique(y, return_counts=True)
    can_stratify = len(unique_labels) > 1 and np.all(counts >= 2)
    x_train, x_eval, y_train, y_eval = train_test_split(
        x,
        y,
        test_size=0.25,
        random_state=seed,
        stratify=y if can_stratify else None,
    )
    return ClientPartition(
        x_train=np.asarray(x_train, dtype=np.float64),
        y_train=np.asarray(y_train, dtype=np.int64),
        x_eval=np.asarray(x_eval, dtype=np.float64),
        y_eval=np.asarray(y_eval, dtype=np.int64),
    )


@lru_cache(maxsize=8)
def _dataset_state(
    selected_dataset: str,
    max_rows: int,
    num_clients: int,
    selected_split_regime: str,
) -> DatasetState:
    normalized_dataset = _normalize_selected_dataset(selected_dataset)
    if normalized_dataset == "openml":
        if selected_split_regime != "iid":
            raise ValueError(
                f"OpenML paper-track execution currently supports only 'iid', got '{selected_split_regime}'."
            )
        frame = _load_openml_frame(selected_dataset)
        if max_rows > 0 and len(frame) > max_rows:
            frame = frame.sample(n=max_rows, random_state=42).reset_index(drop=True)
        target_column = frame.columns[-1]
        y, classes = _encode_labels(frame[target_column])
        x = (
            frame.drop(columns=[target_column])
            .apply(pd.to_numeric, errors="raise")
            .to_numpy(dtype=np.float64, copy=True)
        )
        index_partitions = _iid_partition_indices(len(frame), num_clients)
        partitions = [
            _numeric_frame_to_client_partition(x[index_partition], y[index_partition], seed=42 + partition_id)
            for partition_id, index_partition in enumerate(index_partitions)
        ]
        return DatasetState(
            partitions=partitions,
            n_features=partitions[0].x_train.shape[1],
            classes=np.asarray(classes),
        )
    if normalized_dataset != "adult":
        raise ValueError(f"Unsupported selected_dataset '{selected_dataset}'.")
    frames = _load_adult_partition_frames(
        max_rows=max_rows,
        num_clients=num_clients,
        selected_split_regime=selected_split_regime,
    )
    all_targets = pd.concat([frame[ADULT_TARGET_COLUMN] for frame in frames], ignore_index=True)
    encoded_targets, classes = _encode_labels(all_targets)
    encoded_frames: list[pd.DataFrame] = []
    start = 0
    for frame in frames:
        encoded_frame = frame.copy()
        end = start + len(encoded_frame)
        encoded_frame[ADULT_TARGET_COLUMN] = encoded_targets[start:end]
        encoded_frames.append(encoded_frame)
        start = end
    combined_features = pd.concat(
        [frame.drop(columns=[ADULT_TARGET_COLUMN]) for frame in encoded_frames],
        ignore_index=True,
    )
    preprocessor = _fit_adult_preprocessor(combined_features)
    partitions = [
        _frame_to_client_partition(frame, preprocessor, seed=42 + partition_id)
        for partition_id, frame in enumerate(encoded_frames)
    ]
    return DatasetState(
        partitions=partitions,
        n_features=partitions[0].x_train.shape[1],
        classes=np.asarray(classes),
    )


def _create_model(n_features: int, classes: np.ndarray) -> SGDClassifier:
    model = SGDClassifier(
        loss="log_loss",
        penalty="l2",
        alpha=0.0001,
        max_iter=1,
        tol=None,
        random_state=42,
    )
    bootstrap_x = np.zeros((len(classes), n_features), dtype=np.float64)
    bootstrap_y = np.arange(len(classes), dtype=np.int64)
    model.partial_fit(bootstrap_x, bootstrap_y, classes=bootstrap_y)
    return model


def _xgb_params(num_classes: int) -> dict[str, Any]:
    params: dict[str, Any] = {
        "max_depth": 6,
        "eta": 0.3,
        "subsample": 1.0,
        "colsample_bytree": 1.0,
        "tree_method": "hist",
        "verbosity": 0,
        "seed": 42,
    }
    if num_classes > 2:
        params["objective"] = "multi:softprob"
        params["eval_metric"] = "mlogloss"
        params["num_class"] = num_classes
    else:
        params["objective"] = "binary:logistic"
        params["eval_metric"] = "logloss"
    return params


def _load_xgb_booster(model_bytes: bytes) -> xgb.Booster:
    booster = xgb.Booster()
    booster.load_model(bytearray(model_bytes))
    return booster


def _train_xgb_booster(
    *,
    x_train: np.ndarray,
    y_train: np.ndarray,
    current_model_bytes: bytes,
    num_classes: int,
) -> xgb.Booster:
    dtrain = xgb.DMatrix(x_train, label=y_train)
    if current_model_bytes:
        current_booster = _load_xgb_booster(current_model_bytes)
        return xgb.train(_xgb_params(num_classes), dtrain, num_boost_round=1, xgb_model=current_booster)
    return xgb.train(_xgb_params(num_classes), dtrain, num_boost_round=1)


def _xgb_prediction_metrics(
    booster: xgb.Booster,
    *,
    x_eval: np.ndarray,
    y_eval: np.ndarray,
    classes: np.ndarray,
) -> tuple[float, float]:
    deval = xgb.DMatrix(x_eval, label=y_eval)
    probabilities = booster.predict(deval)
    return _probability_metrics(y_eval, probabilities, classes=classes)


def _create_random_forest_model() -> RandomForestClassifier:
    return RandomForestClassifier(
        n_estimators=200,
        max_features="sqrt",
        random_state=42,
        n_jobs=1,
    )


def _create_tabpfn_model() -> Any:
    from tabpfn_client import set_access_token as set_tabpfn_access_token
    from tabpfn_client.estimator import TabPFNClassifier

    token = os.environ.get("TABPFN_TOKEN")
    if token:
        set_tabpfn_access_token(token)
    return TabPFNClassifier(
        n_estimators=4,
        ignore_pretraining_limits=True,
        random_state=42,
        paper_version=True,
    )


def _tabpfn_ready() -> bool:
    return bool(os.environ.get("TABPFN_TOKEN"))


def _ensure_tabpfn_ready() -> None:
    if _tabpfn_ready():
        return
    raise RuntimeError(
        "TabPFN client mode requires TABPFN_TOKEN in the environment. "
        "Export TABPFN_TOKEN before running TabPFN slices."
    )


def _serialize_model(model: Any) -> bytes:
    return pickle.dumps(model, protocol=pickle.HIGHEST_PROTOCOL)


def _deserialize_model(payload: bytes) -> Any:
    return pickle.loads(payload)


def _ensemble_probabilities(model_payloads: list[bytes], x_eval: np.ndarray) -> np.ndarray:
    probability_matrices = [
        _probability_matrix(_deserialize_model(payload).predict_proba(x_eval))
        for payload in model_payloads
    ]
    return np.mean(probability_matrices, axis=0)


def _get_model_parameters(model: SGDClassifier) -> list[np.ndarray]:
    return [model.coef_.astype(np.float64), model.intercept_.astype(np.float64)]


def _set_model_parameters(
    model: SGDClassifier,
    parameters: list[np.ndarray],
    n_features: int,
    classes: np.ndarray,
) -> None:
    coef, intercept = parameters
    model.coef_ = coef.astype(np.float64)
    model.intercept_ = intercept.astype(np.float64)
    model.classes_ = np.arange(len(classes), dtype=np.int64)
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
    dataset_state = _dataset_state(selected_dataset, max_rows, num_clients, selected_split_regime)
    partitions = dataset_state.partitions
    n_features = dataset_state.n_features
    classes = dataset_state.classes
    initial_model = _create_model(n_features, classes)
    initial_ndarrays = _get_model_parameters(initial_model)
    model_parameter_bytes = _arrays_num_bytes(initial_ndarrays)

    client_app = ClientApp()

    @client_app.train()
    def train(msg: Message, context: Context) -> Message:
        partition_id = int(_client_id_from_context(context))
        partition = partitions[partition_id]
        model = _create_model(n_features, classes)
        _set_model_parameters(model, msg.content["arrays"].to_numpy_ndarrays(), n_features, classes)
        model.partial_fit(partition.x_train, partition.y_train)
        probabilities = model.predict_proba(partition.x_train)
        metrics = MetricRecord(
            {
                "train_loss": round(float(log_loss(partition.y_train, probabilities, labels=list(range(len(classes))))), 6),
                "num-examples": len(partition.x_train),
            }
        )
        content = RecordDict({"arrays": ArrayRecord(_get_model_parameters(model)), "metrics": metrics})
        return Message(content=content, reply_to=msg)

    @client_app.evaluate()
    def evaluate(msg: Message, context: Context) -> Message:
        partition_id = int(_client_id_from_context(context))
        partition = partitions[partition_id]
        model = _create_model(n_features, classes)
        _set_model_parameters(model, msg.content["arrays"].to_numpy_ndarrays(), n_features, classes)
        probabilities = model.predict_proba(partition.x_eval)
        accuracy, loss_value = _probability_metrics(partition.y_eval, probabilities, classes=classes)
        metrics = MetricRecord(
            {
                "accuracy": round(accuracy, 6),
                "eval_loss": round(loss_value, 6),
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


def _run_dataset_baseline_via_flower_app(
    *,
    run_name: str,
    selected_dataset: str,
    selected_baseline: str,
    selected_split_regime: str,
    num_clients: int,
    num_rounds: int,
    max_rows: int,
) -> Path:
    artifact_path = default_paths().results / run_name / "dataset-baseline-summary.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    if artifact_path.exists():
        artifact_path.unlink()
    started_at = time.time()
    _run_flower_app(
        run_config={
            "scenario": "dataset-baseline",
            "run-name": run_name,
            "num-server-rounds": num_rounds,
            "num-clients": num_clients,
            "selected-dataset": selected_dataset,
            "selected-baseline": selected_baseline,
            "selected-split-regime": selected_split_regime,
            "dataset-backed-max-rows": max_rows,
        },
        num_supernodes=num_clients,
    )
    return _wait_for_fresh_artifact(artifact_path, started_at=started_at)


def _run_serialized_ensemble_baseline_simulation(
    *,
    run_name: str,
    selected_dataset: str,
    selected_baseline: str,
    selected_split_regime: str,
    num_clients: int,
    num_rounds: int,
    max_rows: int,
) -> Path:
    dataset_state = _dataset_state(selected_dataset, max_rows, num_clients, selected_split_regime)
    partitions = dataset_state.partitions
    classes = dataset_state.classes

    def _train_local_model(partition: ClientPartition) -> Any:
        if selected_baseline == "random_forest":
            model = _create_random_forest_model()
        elif selected_baseline == "tabpfn":
            model = _create_tabpfn_model()
        else:
            raise ValueError(f"Unsupported serialized ensemble baseline '{selected_baseline}'.")
        model.fit(partition.x_train, partition.y_train)
        return model

    client_app = ClientApp()

    @client_app.train()
    def train(msg: Message, context: Context) -> Message:
        partition_id = int(_client_id_from_context(context))
        partition = partitions[partition_id]
        model = _train_local_model(partition)
        probabilities = model.predict_proba(partition.x_train)
        _, loss_value = _probability_metrics(partition.y_train, probabilities, classes=classes)
        metrics = MetricRecord(
            {
                "train_loss": round(loss_value, 6),
                "num-examples": len(partition.x_train),
            }
        )
        content = RecordDict(
            {
                "arrays": bytes_to_arrayrecord(_serialize_model(model)),
                "metrics": metrics,
            }
        )
        return Message(content=content, reply_to=msg)

    @client_app.evaluate()
    def evaluate(msg: Message, context: Context) -> Message:
        partition_id = int(_client_id_from_context(context))
        partition = partitions[partition_id]
        model_payloads = decode_ensemble_payload(arrayrecord_to_bytes(msg.content["arrays"]))
        probabilities = _ensemble_probabilities(model_payloads, partition.x_eval)
        accuracy, loss_value = _probability_metrics(partition.y_eval, probabilities, classes=classes)
        metrics = MetricRecord(
            {
                "accuracy": round(accuracy, 6),
                "eval_loss": round(loss_value, 6),
                "num-examples": len(partition.x_eval),
            }
        )
        return Message(content=RecordDict({"metrics": metrics}), reply_to=msg)

    from .ensemble_strategy import SerializedEnsembleStrategy

    server_app = ServerApp()
    result_box: dict[str, Any] = {}

    @server_app.main()
    def main(grid: Grid, context: Context) -> None:
        strategy = SerializedEnsembleStrategy(
            fraction_train=1.0,
            fraction_evaluate=1.0,
            min_train_nodes=num_clients,
            min_evaluate_nodes=num_clients,
            min_available_nodes=num_clients,
        )
        result_box["result"] = strategy.start(
            grid=grid,
            initial_arrays=bytes_to_arrayrecord(b""),
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
    model_payloads = decode_ensemble_payload(arrayrecord_to_bytes(result.arrays)) if result.arrays is not None else []
    model_parameter_bytes = len(encode_ensemble_payload(model_payloads)) if model_payloads else 0
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
        "estimated_downstream_bytes": model_parameter_bytes * num_clients * num_rounds,
        "estimated_upstream_bytes": model_parameter_bytes * num_clients * num_rounds,
        **resource_usage,
        "train_examples_per_client": [len(partition.x_train) for partition in partitions],
        "eval_examples_per_client": [len(partition.x_eval) for partition in partitions],
        "history": _result_to_history_dict(result),
        "notes": [
            "This dataset-backed benchmark uses Flower local simulation with serialized local-model ensembling.",
            f"The federated ensemble baseline for {selected_baseline} averages client-level predictive probabilities.",
        ],
    }
    artifact_path.write_text(__import__("json").dumps(report, indent=2) + "\n", encoding="utf-8")
    return artifact_path


def run_dataset_backed_baseline(config: dict[str, Any], run_name: str) -> Path:
    pilot = config.get("pilot", {})
    selected_dataset = str(pilot.get("selected_dataset", "adult_engineering_slice"))
    selected_baseline = str(pilot.get("selected_baseline", "logistic_regression"))

    num_clients = int(pilot.get("num_clients", 2))
    num_rounds = int(pilot.get("num_rounds", 1))
    max_rows = int(pilot.get("dataset_backed_max_rows", 2000))
    selected_split_regime = str(pilot.get("selected_split_regime", "iid"))
    default_paths().openml_cache.mkdir(parents=True, exist_ok=True)
    default_paths().matplotlib_cache.mkdir(parents=True, exist_ok=True)
    if selected_baseline == "tabpfn":
        _ensure_tabpfn_ready()
    _dataset_state(selected_dataset, max_rows, num_clients, selected_split_regime)
    if selected_baseline == "logistic_regression":
        return _run_dataset_baseline_simulation(
            run_name=run_name,
            selected_dataset=selected_dataset,
            selected_baseline=selected_baseline,
            selected_split_regime=selected_split_regime,
            num_clients=num_clients,
            num_rounds=num_rounds,
            max_rows=max_rows,
        )
    if selected_baseline == "xgboost":
        return _run_dataset_baseline_via_flower_app(
            run_name=run_name,
            selected_dataset=selected_dataset,
            selected_baseline=selected_baseline,
            selected_split_regime=selected_split_regime,
            num_clients=num_clients,
            num_rounds=num_rounds,
            max_rows=max_rows,
        )
    if selected_baseline in {"random_forest", "tabpfn"}:
        return _run_serialized_ensemble_baseline_simulation(
            run_name=run_name,
            selected_dataset=selected_dataset,
            selected_baseline=selected_baseline,
            selected_split_regime=selected_split_regime,
            num_clients=num_clients,
            num_rounds=num_rounds,
            max_rows=max_rows,
        )
    raise ValueError(
        "Dataset-backed baseline is only implemented for "
        f"{sorted(SUPPORTED_DATASET_BACKED_BASELINES)!r} right now, got '{selected_baseline}'."
    )
