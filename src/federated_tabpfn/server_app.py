from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import numpy as np
from flwr.app import ArrayRecord, Context
from flwr.serverapp import Grid, ServerApp
from flwr.serverapp.strategy import FedAvg, FedXgbBagging

from .dataset_pilot import (
    _arrayrecord_to_model_bytes,
    _bytes_to_arrayrecord,
    _create_model,
    _dataset_state,
    _get_model_parameters,
)
from .pilot import _arrays_num_bytes, _resource_usage, _result_to_history_dict
from .project import default_paths

app = ServerApp()


def _write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@app.main()
def main(grid: Grid, context: Context) -> None:
    scenario = str(context.run_config["scenario"])
    run_name = str(context.run_config["run-name"])
    num_rounds = int(context.run_config["num-server-rounds"])
    num_clients = int(context.run_config["num-clients"])
    selected_dataset = str(context.run_config["selected-dataset"])
    selected_baseline = str(context.run_config["selected-baseline"])
    selected_split_regime = str(context.run_config["selected-split-regime"])
    max_rows = int(context.run_config["dataset-backed-max-rows"])

    if scenario == "smoke":
        initial_ndarrays = [np.array([0.0, 0.0], dtype=np.float64)]
    elif scenario == "dataset-baseline":
        if selected_baseline == "xgboost":
            initial_arrays = _bytes_to_arrayrecord(b"")
            initial_ndarrays = None
        else:
            _, n_features = _dataset_state(selected_dataset, max_rows, num_clients, selected_split_regime)
            initial_ndarrays = _get_model_parameters(_create_model(n_features))
            initial_arrays = ArrayRecord(initial_ndarrays)
    else:
        raise ValueError(f"Unsupported Flower scenario: {scenario}")

    if selected_baseline == "xgboost":
        model_parameter_bytes = 0
        strategy = FedXgbBagging(
            fraction_train=1.0,
            fraction_evaluate=1.0,
            min_train_nodes=num_clients,
            min_evaluate_nodes=num_clients,
            min_available_nodes=num_clients,
        )
    else:
        model_parameter_bytes = _arrays_num_bytes(initial_ndarrays)
        strategy = FedAvg(
            fraction_train=1.0,
            fraction_evaluate=1.0,
            min_train_nodes=num_clients,
            min_evaluate_nodes=num_clients,
            min_available_nodes=num_clients,
        )

    started_at = datetime.now(timezone.utc).isoformat()
    start = time.perf_counter()
    result = strategy.start(
        grid=grid,
        initial_arrays=initial_arrays if selected_baseline == "xgboost" else ArrayRecord(initial_ndarrays),
        num_rounds=num_rounds,
    )
    runtime_seconds = round(time.perf_counter() - start, 4)
    resource_usage = _resource_usage()
    if scenario == "dataset-baseline" and selected_baseline == "xgboost" and result.arrays is not None:
        model_parameter_bytes = len(_arrayrecord_to_model_bytes(result.arrays))
    estimated_downstream_bytes = model_parameter_bytes * num_clients * num_rounds
    estimated_upstream_bytes = model_parameter_bytes * num_clients * num_rounds

    if scenario == "smoke":
        payload = {
            "run_name": run_name,
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "framework": "flower",
            "execution_mode": "local",
            "datasets": [selected_dataset],
            "baselines": [selected_baseline],
            "selected_baseline": selected_baseline,
            "num_clients": num_clients,
            "num_rounds": num_rounds,
            "smoke_test": True,
            "runtime_seconds": runtime_seconds,
            "train_seconds": runtime_seconds,
            "model_parameter_bytes": model_parameter_bytes,
            "estimated_downstream_bytes": estimated_downstream_bytes,
            "estimated_upstream_bytes": estimated_upstream_bytes,
            **resource_usage,
            "history": _result_to_history_dict(result),
            "notes": [
                "This is a Flower Message API smoke pilot launched via flwr run.",
                "It validates local execution, artifact creation, and status reporting rather than benchmark quality.",
            ],
        }
        artifact_path = default_paths().results / run_name / "pilot-summary.json"
    else:
        partitions, _ = _dataset_state(selected_dataset, max_rows, num_clients, selected_split_regime)
        payload = {
            "run_name": run_name,
            "started_at": started_at,
            "completed_at": datetime.now(timezone.utc).isoformat(),
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
                "This dataset-backed baseline slice uses Flower's Message API launched via flwr run.",
                (
                    "It uses the Adult engineering slice and federated XGBoost bagging under Flower."
                    if selected_baseline == "xgboost"
                    else "It uses the Adult engineering slice and federated logistic regression under Flower."
                ),
            ],
        }
        artifact_path = default_paths().results / run_name / "dataset-baseline-summary.json"

    _write_json(artifact_path, payload)
