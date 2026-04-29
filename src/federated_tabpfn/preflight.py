from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .project import default_paths


def _contains_pending(value: object) -> bool:
    if isinstance(value, str):
        return value.startswith("pending-")
    if isinstance(value, list):
        return any(_contains_pending(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_pending(item) for item in value.values())
    return False


def build_preflight_report(config: dict[str, Any], run_name: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "run_name": run_name,
        "created_at": now,
        "framework": config.get("framework"),
        "execution_mode": config.get("execution_mode"),
        "datasets": config.get("datasets", []),
        "baselines": config.get("baselines", []),
        "metrics": config.get("metrics", []),
        "ready": not _contains_pending(config),
        "blocking_placeholders": _find_pending_values(config),
    }


def _find_pending_values(value: object, prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(value, str):
        if value.startswith("pending-"):
            hits.append(prefix.rstrip("."))
        return hits
    if isinstance(value, list):
        for index, item in enumerate(value):
            hits.extend(_find_pending_values(item, f"{prefix}[{index}]."))
        return hits
    if isinstance(value, dict):
        for key, item in value.items():
            hits.extend(_find_pending_values(item, f"{prefix}{key}."))
    return hits


def write_preflight_artifacts(run_name: str, config: dict[str, Any]) -> Path:
    run_dir = default_paths().results / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    report = build_preflight_report(config, run_name)
    artifact_path = run_dir / "preflight.json"
    artifact_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return artifact_path