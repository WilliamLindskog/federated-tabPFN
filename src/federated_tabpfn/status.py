from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .project import default_paths

STATUS_FILE = "execution-status.json"
REPORT_FILE = "execution-status.md"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def status_paths() -> tuple[Path, Path]:
    reports_dir = default_paths().reports / "generated"
    reports_dir.mkdir(parents=True, exist_ok=True)
    return reports_dir / STATUS_FILE, reports_dir / REPORT_FILE


def default_status() -> dict[str, Any]:
    return {
        "objective": "benchmark federated TabPFN against comparable tabular models",
        "phase": "scaffolded",
        "overall_status": "not-started",
        "updated_at": _now(),
        "workers": {},
        "latest_summary": "No worker has published a status update yet.",
        "next_step": "Run a worker preflight or update to create the first execution artifact.",
        "active_direction": None,
        "artifacts": [],
    }


def load_status() -> dict[str, Any]:
    json_path, _ = status_paths()
    if not json_path.exists():
        return default_status()
    return json.loads(json_path.read_text(encoding="utf-8"))


def _render_markdown(status: dict[str, Any]) -> str:
    lines = [
        "# Execution Status",
        "",
        f"- Objective: {status['objective']}",
        f"- Phase: {status['phase']}",
        f"- Overall status: {status['overall_status']}",
        f"- Updated: {status['updated_at']}",
        "",
        "## Active Direction",
        "",
    ]
    active_direction = status.get("active_direction")
    if active_direction:
        lines.extend(
            [
                f"- source: {active_direction.get('source', 'unknown')}",
                f"- timestamp: {active_direction.get('timestamp', 'unknown')}",
                f"- text: {active_direction.get('text', 'unknown')}",
                "",
            ]
        )
    else:
        lines.extend(["- No active direction recorded.", ""])
    lines.extend(
        [
        "## Latest Summary",
        "",
        status["latest_summary"],
        "",
        "## Next Step",
        "",
        status["next_step"],
        "",
        "## Workers",
        "",
        ]
    )
    workers = status.get("workers", {})
    if not workers:
        lines.append("- No worker updates recorded.")
    else:
        for name, worker in sorted(workers.items()):
            lines.extend(
                [
                    f"### {name}",
                    "",
                    f"- status: {worker['status']}",
                    f"- updated: {worker['updated_at']}",
                    f"- summary: {worker['summary']}",
                    f"- next step: {worker['next_step']}",
                    "",
                ]
            )
    artifacts = status.get("artifacts", [])
    lines.extend(["## Artifacts", ""])
    if not artifacts:
        lines.append("- No artifacts recorded.")
    else:
        for artifact in artifacts:
            lines.append(f"- {artifact}")
    return "\n".join(lines) + "\n"


def save_status(status: dict[str, Any]) -> None:
    status["updated_at"] = _now()
    json_path, md_path = status_paths()
    json_path.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(status), encoding="utf-8")


def update_worker_status(
    worker_name: str,
    *,
    worker_status: str,
    summary: str,
    next_step: str,
    artifact: str | None = None,
    phase: str | None = None,
    overall_status: str | None = None,
) -> dict[str, Any]:
    status = load_status()
    status.setdefault("workers", {})[worker_name] = {
        "status": worker_status,
        "summary": summary,
        "next_step": next_step,
        "updated_at": _now(),
    }
    status["latest_summary"] = f"{worker_name}: {summary}"
    status["next_step"] = next_step
    if phase:
        status["phase"] = phase
    if overall_status:
        status["overall_status"] = overall_status
    if artifact:
        artifacts = status.setdefault("artifacts", [])
        if artifact not in artifacts:
            artifacts.append(artifact)
    save_status(status)
    return status


def set_active_direction(*, text: str, timestamp: str, source: str) -> dict[str, Any]:
    status = load_status()
    status["active_direction"] = {
        "text": text,
        "timestamp": timestamp,
        "source": source,
    }
    save_status(status)
    return status