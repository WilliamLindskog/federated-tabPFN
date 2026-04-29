from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import flwr as fl
import numpy as np
from flwr.common import Context

from .project import default_paths


class SmokeNumPyClient(fl.client.NumPyClient):
    def __init__(self, cid: str) -> None:
        self.cid = cid
        self.parameters = [np.array([0.0, float(cid)], dtype=np.float32)]

    def get_parameters(self, config: dict[str, Any]) -> list[np.ndarray]:
        return self.parameters

    def fit(self, parameters: list[np.ndarray], config: dict[str, Any]) -> tuple[list[np.ndarray], int, dict[str, Any]]:
        updated = np.array(parameters[0], copy=True)
        updated[0] = updated[0] + 0.1 + (0.05 * int(self.cid))
        updated[1] = float(int(self.cid))
        self.parameters = [updated]
        return self.parameters, 16, {"train_loss": round(1.0 / (int(self.cid) + 2), 4)}

    def evaluate(self, parameters: list[np.ndarray], config: dict[str, Any]) -> tuple[float, int, dict[str, Any]]:
        accuracy = round(0.55 + (0.05 * int(self.cid)), 4)
        return 1.0 - accuracy, 16, {"accuracy": accuracy}


def _average_metrics(metrics: list[tuple[int, dict[str, Any]]]) -> dict[str, Any]:
    if not metrics:
        return {}
    totals: dict[str, float] = {}
    total_examples = 0
    for num_examples, metric_values in metrics:
        total_examples += num_examples
        for key, value in metric_values.items():
            totals[key] = totals.get(key, 0.0) + (float(value) * num_examples)
    return {key: round(value / total_examples, 6) for key, value in totals.items()}


def _client_id_from_context(context: Context | str) -> str:
    if isinstance(context, str):
        return context
    node_config = getattr(context, "node_config", {}) or {}
    partition_id = node_config.get("partition-id")
    if partition_id is None:
        partition_id = node_config.get("node_id", 0)
    return str(partition_id)


def _history_to_dict(history: fl.server.history.History) -> dict[str, Any]:
    return {
        "losses_distributed": [[round_num, loss] for round_num, loss in history.losses_distributed],
        "losses_centralized": [[round_num, loss] for round_num, loss in history.losses_centralized],
        "metrics_distributed_fit": {
            key: [[round_num, value] for round_num, value in values]
            for key, values in history.metrics_distributed_fit.items()
        },
        "metrics_distributed": {
            key: [[round_num, value] for round_num, value in values]
            for key, values in history.metrics_distributed.items()
        },
        "metrics_centralized": {
            key: [[round_num, value] for round_num, value in values]
            for key, values in history.metrics_centralized.items()
        },
    }


def run_flower_smoke_pilot(config: dict[str, Any], run_name: str) -> Path:
    pilot = config.get("pilot", {})
    num_clients = int(pilot.get("num_clients", 2))
    num_rounds = int(pilot.get("num_rounds", 1))

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
        return SmokeNumPyClient(_client_id_from_context(context)).to_client()

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
        "datasets": config.get("datasets", []),
        "baselines": config.get("baselines", []),
        "selected_baseline": pilot.get("selected_baseline"),
        "num_clients": num_clients,
        "num_rounds": num_rounds,
        "smoke_test": bool(pilot.get("smoke_test", False)),
        "runtime_seconds": runtime_seconds,
        "history": _history_to_dict(history),
        "notes": [
            "This is a Flower smoke pilot using synthetic client behavior.",
            "It validates local execution, artifact creation, and status reporting rather than benchmark quality.",
        ],
    }
    artifact_path = run_dir / "pilot-summary.json"
    artifact_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return artifact_path