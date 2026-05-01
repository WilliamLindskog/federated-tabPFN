from __future__ import annotations

from functools import lru_cache

import numpy as np
from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp

from .dataset_pilot import (
    _create_model,
    _create_random_forest_model,
    _create_tabpfn_model,
    _dataset_state,
    _ensemble_probabilities,
    _get_model_parameters,
    _load_xgb_booster,
    _probability_metrics,
    _set_model_parameters,
    _serialize_model,
    _train_xgb_booster,
    _xgb_prediction_metrics,
)
from .ensemble_strategy import arrayrecord_to_bytes, bytes_to_arrayrecord, decode_ensemble_payload
from .pilot import _client_id_from_context

app = ClientApp()


@lru_cache(maxsize=8)
def _scenario_dataset_state(
    selected_dataset: str,
    max_rows: int,
    num_clients: int,
    selected_split_regime: str,
):
    return _dataset_state(selected_dataset, max_rows, num_clients, selected_split_regime)


def _smoke_train(msg: Message, context: Context) -> Message:
    cid = int(_client_id_from_context(context))
    updated = np.array(msg.content["arrays"].to_numpy_ndarrays()[0], copy=True)
    updated[0] = updated[0] + 0.1 + (0.05 * cid)
    updated[1] = float(cid)
    metrics = MetricRecord({"train_loss": round(1.0 / (cid + 2), 4), "num-examples": 16})
    content = RecordDict({"arrays": ArrayRecord([updated]), "metrics": metrics})
    return Message(content=content, reply_to=msg)


def _smoke_evaluate(msg: Message, context: Context) -> Message:
    cid = int(_client_id_from_context(context))
    accuracy = round(0.55 + (0.05 * cid), 4)
    metrics = MetricRecord({"accuracy": accuracy, "eval_loss": 1.0 - accuracy, "num-examples": 16})
    return Message(content=RecordDict({"metrics": metrics}), reply_to=msg)


def _dataset_train(msg: Message, context: Context) -> Message:
    partition_id = int(_client_id_from_context(context))
    num_clients = int(context.run_config["num-clients"])
    selected_dataset = str(context.run_config["selected-dataset"])
    selected_baseline = str(context.run_config["selected-baseline"])
    max_rows = int(context.run_config["dataset-backed-max-rows"])
    selected_split_regime = str(context.run_config["selected-split-regime"])
    dataset_state = _scenario_dataset_state(selected_dataset, max_rows, num_clients, selected_split_regime)
    partition = dataset_state.partitions[partition_id]
    if selected_baseline == "xgboost":
        current_model_bytes = arrayrecord_to_bytes(msg.content["arrays"])
        booster = _train_xgb_booster(
            x_train=partition.x_train,
            y_train=partition.y_train,
            current_model_bytes=current_model_bytes,
            num_classes=len(dataset_state.classes),
        )
        train_accuracy, train_loss = _xgb_prediction_metrics(
            booster,
            x_eval=partition.x_train,
            y_eval=partition.y_train,
            classes=dataset_state.classes,
        )
        metrics = MetricRecord(
            {
                "train_accuracy": round(train_accuracy, 6),
                "train_loss": round(train_loss, 6),
                "num-examples": len(partition.x_train),
            }
        )
        model_bytes = bytes(booster.save_raw(raw_format="json"))
        content = RecordDict({"arrays": bytes_to_arrayrecord(model_bytes), "metrics": metrics})
        return Message(content=content, reply_to=msg)
    if selected_baseline == "random_forest":
        model = _create_random_forest_model()
        model.fit(partition.x_train, partition.y_train)
        probabilities = model.predict_proba(partition.x_train)
        _, loss_value = _probability_metrics(partition.y_train, probabilities, classes=dataset_state.classes)
        metrics = MetricRecord({"train_loss": round(loss_value, 6), "num-examples": len(partition.x_train)})
        content = RecordDict({"arrays": bytes_to_arrayrecord(_serialize_model(model)), "metrics": metrics})
        return Message(content=content, reply_to=msg)
    if selected_baseline == "tabpfn":
        model = _create_tabpfn_model()
        model.fit(partition.x_train, partition.y_train)
        probabilities = model.predict_proba(partition.x_train)
        _, loss_value = _probability_metrics(partition.y_train, probabilities, classes=dataset_state.classes)
        metrics = MetricRecord({"train_loss": round(loss_value, 6), "num-examples": len(partition.x_train)})
        content = RecordDict({"arrays": bytes_to_arrayrecord(_serialize_model(model)), "metrics": metrics})
        return Message(content=content, reply_to=msg)

    model = _create_model(dataset_state.n_features, dataset_state.classes)
    _set_model_parameters(
        model,
        msg.content["arrays"].to_numpy_ndarrays(),
        dataset_state.n_features,
        dataset_state.classes,
    )
    model.partial_fit(partition.x_train, partition.y_train)
    probabilities = model.predict_proba(partition.x_train)
    _, loss_value = _probability_metrics(partition.y_train, probabilities, classes=dataset_state.classes)
    metrics = MetricRecord({"train_loss": round(loss_value, 6), "num-examples": len(partition.x_train)})
    content = RecordDict({"arrays": ArrayRecord(_get_model_parameters(model)), "metrics": metrics})
    return Message(content=content, reply_to=msg)


def _dataset_evaluate(msg: Message, context: Context) -> Message:
    partition_id = int(_client_id_from_context(context))
    num_clients = int(context.run_config["num-clients"])
    selected_dataset = str(context.run_config["selected-dataset"])
    selected_baseline = str(context.run_config["selected-baseline"])
    max_rows = int(context.run_config["dataset-backed-max-rows"])
    selected_split_regime = str(context.run_config["selected-split-regime"])
    dataset_state = _scenario_dataset_state(selected_dataset, max_rows, num_clients, selected_split_regime)
    partition = dataset_state.partitions[partition_id]
    if selected_baseline == "xgboost":
        current_model_bytes = arrayrecord_to_bytes(msg.content["arrays"])
        if not current_model_bytes:
            raise ValueError("Expected a trained XGBoost model before evaluation, but received an empty model.")
        booster = _load_xgb_booster(current_model_bytes)
        accuracy, loss_value = _xgb_prediction_metrics(
            booster,
            x_eval=partition.x_eval,
            y_eval=partition.y_eval,
            classes=dataset_state.classes,
        )
        metrics = MetricRecord(
            {
                "accuracy": round(accuracy, 6),
                "eval_loss": round(loss_value, 6),
                "num-examples": len(partition.x_eval),
            }
        )
        return Message(content=RecordDict({"metrics": metrics}), reply_to=msg)
    if selected_baseline in {"random_forest", "tabpfn"}:
        model_payloads = decode_ensemble_payload(arrayrecord_to_bytes(msg.content["arrays"]))
        probabilities = _ensemble_probabilities(model_payloads, partition.x_eval)
        accuracy, loss_value = _probability_metrics(partition.y_eval, probabilities, classes=dataset_state.classes)
    else:
        model = _create_model(dataset_state.n_features, dataset_state.classes)
        _set_model_parameters(
            model,
            msg.content["arrays"].to_numpy_ndarrays(),
            dataset_state.n_features,
            dataset_state.classes,
        )
        probabilities = model.predict_proba(partition.x_eval)
        accuracy, loss_value = _probability_metrics(partition.y_eval, probabilities, classes=dataset_state.classes)
    metrics = MetricRecord(
        {
            "accuracy": round(accuracy, 6),
            "eval_loss": round(loss_value, 6),
            "num-examples": len(partition.x_eval),
        }
    )
    return Message(content=RecordDict({"metrics": metrics}), reply_to=msg)


@app.train()
def train(msg: Message, context: Context) -> Message:
    scenario = str(context.run_config["scenario"])
    if scenario == "smoke":
        return _smoke_train(msg, context)
    if scenario == "dataset-baseline":
        return _dataset_train(msg, context)
    raise ValueError(f"Unsupported Flower scenario: {scenario}")


@app.evaluate()
def evaluate(msg: Message, context: Context) -> Message:
    scenario = str(context.run_config["scenario"])
    if scenario == "smoke":
        return _smoke_evaluate(msg, context)
    if scenario == "dataset-baseline":
        return _dataset_evaluate(msg, context)
    raise ValueError(f"Unsupported Flower scenario: {scenario}")
