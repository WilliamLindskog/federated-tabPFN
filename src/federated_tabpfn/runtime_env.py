from __future__ import annotations

import os
from pathlib import Path

from .project import default_paths


def _candidate_env_files() -> list[Path]:
    candidates: list[Path] = []
    configured = os.environ.get("FEDERATED_TABPFN_ENV_FILE")
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.append(default_paths().root / ".env")
    return candidates


def _parse_env_line(line: str) -> tuple[str, str] | None:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None
    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip()
    if value and len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        value = value[1:-1]
    return key, value


def load_runtime_env(*, override: bool = False) -> dict[str, str]:
    loaded: dict[str, str] = {}
    for path in _candidate_env_files():
        if not path.exists():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            parsed = _parse_env_line(line)
            if parsed is None:
                continue
            key, value = parsed
            if override or key not in os.environ:
                os.environ[key] = value
                loaded[key] = value
        break
    return loaded
