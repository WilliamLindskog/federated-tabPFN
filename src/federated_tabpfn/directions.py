from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .project import default_paths
from .status import set_active_direction


def directions_path() -> Path:
    return default_paths().reports / "generated" / "pengu-directions.jsonl"


def direction_state_path() -> Path:
    return default_paths().reports / "generated" / "direction-state.json"


def _load_direction_state() -> dict[str, Any]:
    path = direction_state_path()
    if not path.exists():
        return {"last_consumed_timestamp": None}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_direction_state(state: dict[str, Any]) -> None:
    path = direction_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def load_direction_entries() -> list[dict[str, Any]]:
    path = directions_path()
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries


def consume_latest_direction() -> tuple[dict[str, Any] | None, Path | None]:
    state = _load_direction_state()
    last_consumed_timestamp = state.get("last_consumed_timestamp")
    entries = load_direction_entries()
    latest: dict[str, Any] | None = None
    for entry in entries:
        timestamp = entry.get("timestamp")
        if last_consumed_timestamp is None or (isinstance(timestamp, str) and timestamp > last_consumed_timestamp):
            latest = entry
    if latest is None:
        return None, None

    set_active_direction(
        text=str(latest.get("direction", "")).strip(),
        timestamp=str(latest.get("timestamp", "")),
        source=str(latest.get("source", "Pengu")),
    )
    artifact_path = default_paths().reports / "generated" / "active-direction.json"
    artifact_path.write_text(json.dumps(latest, indent=2) + "\n", encoding="utf-8")
    _save_direction_state({"last_consumed_timestamp": latest.get("timestamp")})
    return latest, artifact_path