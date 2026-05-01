from __future__ import annotations

import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from flwr.app import Context

from .project import default_paths


def _client_id_from_context(context: Context | str) -> str:
    if isinstance(context, str):
        return context
    node_config = getattr(context, "node_config", {}) or {}
    partition_id = node_config.get("partition-id")
    if partition_id is None:
        partition_id = node_config.get("node_id", 0)
    return str(partition_id)


def _resource_usage() -> dict[str, float | int]:
    usage = resource.getrusage(resource.RUSAGE_SELF)
    max_rss = int(usage.ru_maxrss if sys.platform == "darwin" else usage.ru_maxrss * 1024)
    return {
        "process_user_cpu_seconds": round(float(usage.ru_utime), 4),
        "process_system_cpu_seconds": round(float(usage.ru_stime), 4),
        "max_rss_bytes": max_rss,
    }


def _metric_records_to_history(metrics_by_round: dict[int, MetricRecord]) -> dict[str, list[list[float | int]]]:
    history: dict[str, list[list[float | int]]] = {}
    for round_num, record in sorted(metrics_by_round.items()):
        for key, value in dict(record).items():
            if key == "num-examples":
                continue
            if isinstance(value, (int, float, np.integer, np.floating)):
                history.setdefault(key, []).append([round_num, round(float(value), 6)])
    return history


def _result_to_history_dict(result: Any) -> dict[str, Any]:
    return {
        "losses_distributed": [],
        "losses_centralized": [],
        "metrics_distributed_fit": _metric_records_to_history(result.train_metrics_clientapp),
        "metrics_distributed": _metric_records_to_history(result.evaluate_metrics_clientapp),
        "metrics_centralized": _metric_records_to_history(result.evaluate_metrics_serverapp),
    }


def _arrays_num_bytes(ndarrays: list[np.ndarray]) -> int:
    return int(sum(array.nbytes for array in ndarrays))


def _run_flower_app(*, run_config: dict[str, str | int], num_supernodes: int) -> None:
    def _format_value(value: str | int) -> str:
        if isinstance(value, str):
            escaped = value.replace('"', '\\"')
            return f'"{escaped}"'
        return str(value)

    config_text = " ".join(f"{key}={_format_value(value)}" for key, value in run_config.items())
    paths = default_paths()
    env = dict(**os.environ)
    src_path = str(paths.root / "src")
    env["PYTHONPATH"] = src_path if not env.get("PYTHONPATH") else f"{src_path}:{env['PYTHONPATH']}"
    venv_flwr = Path(sys.executable).with_name("flwr")
    flwr_executable = str(venv_flwr) if venv_flwr.exists() else shutil.which("flwr")
    if flwr_executable is None:
        raise FileNotFoundError("Could not find the 'flwr' executable in PATH.")
    flwr_home = paths.root / ".flower-local"
    flwr_home.mkdir(parents=True, exist_ok=True)
    paths.huggingface_cache.mkdir(parents=True, exist_ok=True)
    paths.openml_cache.mkdir(parents=True, exist_ok=True)
    paths.matplotlib_cache.mkdir(parents=True, exist_ok=True)
    (flwr_home / "config.toml").write_text(
        "\n".join(
            [
                "[superlink]",
                'default = "local"',
                "",
                "[superlink.local]",
                'address = ":local:"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    with tempfile.TemporaryDirectory(prefix="federated-tabpfn-flower-app-") as temp_dir:
        temp_path = Path(temp_dir)
        (temp_path / "LICENSE").write_text("Temporary local Flower app scaffold.\n", encoding="utf-8")
        (temp_path / "pyproject.toml").write_text(
            "\n".join(
                [
                    "[build-system]",
                    'requires = ["setuptools>=68", "wheel"]',
                    'build-backend = "setuptools.build_meta"',
                    "",
                    "[project]",
                    'name = "federated-tabpfn-local-runner"',
                    'version = "0.0.0"',
                    'description = "Temporary Flower app wrapper for local federated-tabPFN runs"',
                    'license = { file = "LICENSE" }',
                    'dependencies = ["flwr[simulation]>=1.29,<1.30", "tabpfn-client>=0.2.8"]',
                    "",
                    "[tool.flwr.app]",
                    'publisher = "local"',
                    'fab-format-version = 1',
                    'flwr-version-target = "1.29.0"',
                    "",
                    "[tool.flwr.app.components]",
                    'serverapp = "federated_tabpfn.server_app:app"',
                    'clientapp = "federated_tabpfn.client_app:app"',
                    "",
                    "[tool.flwr.app.config]",
                    'scenario = "smoke"',
                    'run-name = "pilot-smoke"',
                    'num-server-rounds = 1',
                    'num-clients = 2',
                    'selected-dataset = "adult_engineering_slice"',
                    'selected-baseline = "logistic_regression"',
                    'selected-split-regime = "iid"',
                    'dataset-backed-max-rows = 2000',
                    "",
                ]
            ),
            encoding="utf-8",
        )
        subprocess.run(
            [
                flwr_executable,
                "run",
                str(temp_path),
                "local",
                "--stream",
                "--run-config",
                config_text,
                "--federation-config",
                f"num-supernodes={num_supernodes}",
            ],
            check=True,
            cwd=paths.root,
            env={
                **env,
                "FLWR_HOME": str(flwr_home),
                "FLWR_LOCAL_CONTROL_API_PORT": "39193",
                "HF_HOME": str(paths.huggingface_cache),
                "HF_DATASETS_CACHE": str(paths.huggingface_cache / "datasets"),
                "MPLCONFIGDIR": str(paths.matplotlib_cache),
            },
        )


def _wait_for_fresh_artifact(artifact_path: Path, *, started_at: float, timeout_seconds: float = 420.0) -> Path:
    deadline = time.time() + timeout_seconds
    while time.time() <= deadline:
        if artifact_path.exists() and artifact_path.stat().st_mtime >= started_at:
            return artifact_path
        time.sleep(0.5)
    raise FileNotFoundError(f"Expected fresh artifact at {artifact_path} within {timeout_seconds} seconds.")


def run_flower_smoke_pilot(config: dict[str, Any], run_name: str) -> Path:
    pilot = config.get("pilot", {})
    num_clients = int(pilot.get("num_clients", 2))
    artifact_path = default_paths().results / run_name / "pilot-summary.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    if artifact_path.exists():
        artifact_path.unlink()
    started_at = time.time()
    _run_flower_app(
        run_config={
            "scenario": "smoke",
            "run-name": run_name,
            "num-server-rounds": int(pilot.get("num_rounds", 1)),
            "num-clients": num_clients,
            "selected-dataset": str(pilot.get("selected_dataset", "adult_engineering_slice")),
            "selected-baseline": str(pilot.get("selected_baseline", "logistic_regression")),
            "selected-split-regime": str(pilot.get("selected_split_regime", "iid")),
            "dataset-backed-max-rows": int(pilot.get("dataset_backed_max_rows", 2000)),
        },
        num_supernodes=num_clients,
    )
    return _wait_for_fresh_artifact(artifact_path, started_at=started_at)
