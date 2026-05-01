from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .project import default_paths
from .study_registry import study_registry_payload

RESULTS_SUMMARY_JSON = "results-summary.json"
RESULTS_SUMMARY_MD = "results-summary.md"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _metric_tail(history: dict[str, Any], section: str, metric_name: str) -> float | None:
    series = (((history or {}).get(section) or {}).get(metric_name) or [])
    if not series:
        return None
    return float(series[-1][1])


def _completed_key(summary: dict[str, Any], path: Path) -> str:
    return str(summary.get("completed_at") or path.stat().st_mtime)


def _result_summary(path: Path) -> dict[str, Any]:
    summary = _load_json(path)
    history = summary.get("history", {})
    return {
        "artifact": str(path.relative_to(default_paths().root)),
        "run_name": summary.get("run_name", path.parent.name),
        "completed_at": summary.get("completed_at", "unknown"),
        "dataset": summary.get("dataset", "unknown"),
        "baseline": summary.get("baseline", "unknown"),
        "split_regime": summary.get("split_regime", "unknown"),
        "runtime_seconds": summary.get("runtime_seconds"),
        "max_rss_bytes": summary.get("max_rss_bytes"),
        "model_parameter_bytes": summary.get("model_parameter_bytes"),
        "estimated_upstream_bytes": summary.get("estimated_upstream_bytes"),
        "estimated_downstream_bytes": summary.get("estimated_downstream_bytes"),
        "accuracy": _metric_tail(history, "metrics_distributed", "accuracy"),
        "eval_loss": _metric_tail(history, "metrics_distributed", "eval_loss"),
        "train_loss": _metric_tail(history, "metrics_distributed_fit", "train_loss"),
    }


def recent_result_rows(limit: int | None = None) -> list[dict[str, Any]]:
    result_paths = sorted(default_paths().results.glob("*/dataset-baseline-summary.json"))
    rows = [_result_summary(path) for path in result_paths]
    rows.sort(key=lambda row: row.get("completed_at") or "", reverse=True)
    if limit is not None:
        return rows[:limit]
    return rows


def results_summary_payload(limit: int = 10) -> dict[str, Any]:
    rows = recent_result_rows(limit=limit)
    return {
        "generated_from": "results/*/dataset-baseline-summary.json",
        "recent_runs": rows,
        "run_count": len(recent_result_rows()),
        "latest_run": rows[0] if rows else None,
        "study_registry": study_registry_payload(),
    }


def format_results_summary(limit: int = 5) -> str:
    payload = results_summary_payload(limit=limit)
    rows = payload["recent_runs"]
    lines = [
        "Recent Experiment Results",
        "",
        f"Tracked runs: {payload['run_count']}",
    ]
    latest = payload.get("latest_run")
    if latest:
        lines.extend(
            [
                f"Latest run: {latest['run_name']}",
                (
                    f"Latest metrics: accuracy={latest['accuracy']:.3f} | "
                    f"eval_loss={latest['eval_loss']:.3f} | runtime={latest['runtime_seconds']:.2f}s"
                ),
            ]
        )
    lines.extend(["", "Runs:"])
    if not rows:
        lines.append("- No dataset-backed result artifacts found.")
    else:
        for row in rows:
            runtime = row.get("runtime_seconds")
            accuracy = row.get("accuracy")
            eval_loss = row.get("eval_loss")
            lines.append(
                "- "
                f"{row['dataset']} | {row['baseline']} | {row['split_regime']} | "
                f"acc {accuracy:.3f} | eval_loss {eval_loss:.3f} | runtime {runtime:.2f}s"
            )

    study_track = payload["study_registry"]["paper_track"]
    lines.extend(
        [
            "",
            f"Paper track: {study_track['name']}",
            f"Paper track dataset count: {study_track['dataset_count']}",
        ]
    )
    return "\n".join(lines)


def write_results_summary(limit: int = 10) -> tuple[Path, Path]:
    reports_dir = default_paths().reports / "generated"
    reports_dir.mkdir(parents=True, exist_ok=True)
    json_path = reports_dir / RESULTS_SUMMARY_JSON
    md_path = reports_dir / RESULTS_SUMMARY_MD
    json_path.write_text(json.dumps(results_summary_payload(limit=limit), indent=2) + "\n", encoding="utf-8")
    md_path.write_text(format_results_summary(limit=limit) + "\n", encoding="utf-8")
    return json_path, md_path
