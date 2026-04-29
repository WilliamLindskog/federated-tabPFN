from __future__ import annotations

from functools import lru_cache

import numpy as np
from flwr.app import ArrayRecord, Context, Message, MetricRecord, RecordDict
from flwr.clientapp import ClientApp
from sklearn.metrics import accuracy_score, log_loss

from .dataset_pilot import _create_model, _dataset_state, _get_model_parameters, _set_model_parameters
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
    max_rows = int(context.run_config["dataset-backed-max-rows"])
    selected_split_regime = str(context.run_config["selected-split-regime"])
    partitions, n_features = _scenario_dataset_state(selected_dataset, max_rows, num_clients, selected_split_regime)
    partition = partitions[partition_id]
    model = _create_model(n_features)
    _set_model_parameters(model, msg.content["arrays"].to_numpy_ndarrays(), n_features)
    model.partial_fit(partition.x_train, partition.y_train)
    probabilities = model.predict_proba(partition.x_train)
    loss_value = float(log_loss(partition.y_train, probabilities, labels=[0, 1]))
    metrics = MetricRecord({"train_loss": round(loss_value, 6), "num-examples": len(partition.x_train)})
    content = RecordDict({"arrays": ArrayRecord(_get_model_parameters(model)), "metrics": metrics})
    return Message(content=content, reply_to=msg)


def _dataset_evaluate(msg: Message, context: Context) -> Message:
    partition_id = int(_client_id_from_context(context))
    num_clients = int(context.run_config["num-clients"])
    selected_dataset = str(context.run_config["selected-dataset"])
    max_rows = int(context.run_config["dataset-backed-max-rows"])
    selected_split_regime = str(context.run_config["selected-split-regime"])
    partitions, n_features = _scenario_dataset_state(selected_dataset, max_rows, num_clients, selected_split_regime)
    partition = partitions[partition_id]
    model = _create_model(n_features)
    _set_model_parameters(model, msg.content["arrays"].to_numpy_ndarrays(), n_features)
    probabilities = model.predict_proba(partition.x_eval)
    predictions = np.argmax(probabilities, axis=1)
    accuracy = float(accuracy_score(partition.y_eval, predictions))
    loss_value = float(log_loss(partition.y_eval, probabilities, labels=[0, 1]))
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