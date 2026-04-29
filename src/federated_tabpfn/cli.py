from __future__ import annotations

from pathlib import Path

import typer
import yaml

from .dashboard import write_dashboard
from .dataset_pilot import run_dataset_backed_logreg
from .directions import consume_latest_direction
from .preflight import write_preflight_artifacts
from .pilot import run_flower_smoke_pilot
from .project import default_paths
from .results_summary import format_results_summary
from .status import load_status, update_worker_status
from .study_registry import format_study_registry

app = typer.Typer(help="Utilities for the federated-tabPFN benchmark scaffold.")
worker_app = typer.Typer(help="Worker commands for execution updates and preflight steps.")
app.add_typer(worker_app, name="worker")


def _load_pilot_config() -> dict:
    config_path = default_paths().configs / "pilot.yaml"
    return yaml.safe_load(config_path.read_text(encoding="utf-8"))


def _contains_pending(value: object) -> bool:
    if isinstance(value, str):
        return value.startswith("pending-")
    if isinstance(value, list):
        return any(_contains_pending(item) for item in value)
    if isinstance(value, dict):
        return any(_contains_pending(item) for item in value.values())
    return False


@app.command("check-ready")
def check_ready() -> None:
    """Check whether the pilot config still contains placeholders."""
    config = _load_pilot_config()
    if _contains_pending(config):
        raise typer.Exit(
            code=1,
        )
    typer.echo("Pilot config is ready for the next execution step.")


@app.command("show-config")
def show_config() -> None:
    """Print the current pilot config."""
    typer.echo(yaml.safe_dump(_load_pilot_config(), sort_keys=False))


@app.command("init-run-dir")
def init_run_dir(name: str = "pilot") -> None:
    """Create a deterministic run directory for the next local benchmark pass."""
    run_dir = default_paths().results / name
    run_dir.mkdir(parents=True, exist_ok=True)
    typer.echo(str(Path(run_dir).resolve()))


@app.command("show-status")
def show_status(as_json: bool = typer.Option(False, "--json", help="Print JSON status.")) -> None:
    """Show the current machine-readable execution status for Pengu and workers."""
    status = load_status()
    if as_json:
        typer.echo(yaml.safe_dump(status, sort_keys=False))
        return
    typer.echo(status["latest_summary"])
    typer.echo(f"Phase: {status['phase']}")
    typer.echo(f"Overall status: {status['overall_status']}")
    typer.echo(f"Next step: {status['next_step']}")


@app.command("render-dashboard")
def render_dashboard() -> None:
    """Generate the interactive experiment tracking dashboard."""
    output_path = write_dashboard()
    typer.echo(str(output_path.resolve()))


@app.command("show-results")
def show_results(limit: int = typer.Option(5, min=1, help="Maximum number of recent runs to show.")) -> None:
    """Print a compact summary of recent dataset-backed experiment results."""
    typer.echo(format_results_summary(limit=limit))


@app.command("show-study-datasets")
def show_study_datasets() -> None:
    """Print the locked paper-facing dataset registry."""
    typer.echo(format_study_registry())


@worker_app.command("update")
def worker_update(
    worker: str,
    status: str,
    summary: str,
    next_step: str,
    artifact: str | None = None,
    phase: str | None = None,
    overall_status: str | None = None,
) -> None:
    """Publish a worker status update for Pengu to consume."""
    update_worker_status(
        worker,
        worker_status=status,
        summary=summary,
        next_step=next_step,
        artifact=artifact,
        phase=phase,
        overall_status=overall_status,
    )
    typer.echo(f"Updated worker status for {worker}.")


@worker_app.command("preflight")
def worker_preflight(
    worker: str = typer.Option("experiment-builder", help="Worker publishing the execution step."),
    run_name: str = typer.Option("pilot-preflight", help="Run directory name under results/."),
) -> None:
    """Perform the first concrete execution step and publish it as worker status."""
    config = _load_pilot_config()
    artifact_path = write_preflight_artifacts(run_name, config)
    ready = not _contains_pending(config)
    summary = (
        "Completed pilot preflight. Config is ready for a first pilot run."
        if ready
        else "Completed pilot preflight. Config still contains placeholders that block the first pilot run."
    )
    next_step = (
        "Implement the Flower pilot entrypoint and run the first local pass."
        if ready
        else "Replace placeholder datasets and baselines in configs/pilot.yaml, then rerun preflight."
    )
    update_worker_status(
        worker,
        worker_status="completed" if ready else "blocked",
        summary=summary,
        next_step=next_step,
        artifact=str(artifact_path.relative_to(default_paths().root)),
        phase="preflight-complete",
        overall_status="ready-for-pilot" if ready else "blocked-on-config",
    )
    write_dashboard()
    typer.echo(str(artifact_path.resolve()))


@worker_app.command("run-pilot")
def worker_run_pilot(
    worker: str = typer.Option("experiment-builder", help="Worker publishing the execution step."),
    run_name: str = typer.Option("pilot-smoke", help="Run directory name under results/."),
) -> None:
    """Run the first local Flower smoke pilot and publish execution status."""
    config = _load_pilot_config()
    if _contains_pending(config):
        update_worker_status(
            worker,
            worker_status="blocked",
            summary="Pilot run blocked because the config still contains placeholders.",
            next_step="Replace placeholders in configs/pilot.yaml, rerun preflight, then rerun the pilot.",
            phase="pilot-blocked",
            overall_status="blocked-on-config",
        )
        raise typer.Exit(code=1)
    try:
        artifact_path = run_flower_smoke_pilot(config, run_name)
    except Exception as exc:
        update_worker_status(
            worker,
            worker_status="failed",
            summary=f"Flower smoke pilot failed: {exc}",
            next_step="Fix the local Flower execution error, then rerun the worker pilot command.",
            phase="pilot-failed",
            overall_status="pilot-failed",
        )
        write_dashboard()
        raise typer.Exit(code=1) from exc

    update_worker_status(
        worker,
        worker_status="completed",
        summary="Completed the first local Flower smoke pilot and wrote pilot artifacts.",
        next_step="Replace the synthetic smoke pilot with dataset-backed training and add result extraction for the first real comparison run.",
        artifact=str(artifact_path.relative_to(default_paths().root)),
        phase="pilot-smoke-complete",
        overall_status="pilot-smoke-complete",
    )
    write_dashboard()
    typer.echo(str(artifact_path.resolve()))


@worker_app.command("run-dataset-baseline")
def worker_run_dataset_baseline(
    worker: str = typer.Option("experiment-builder", help="Worker publishing the execution step."),
    run_name: str = typer.Option("adult-logreg", help="Run directory name under results/."),
) -> None:
    """Run the first real dataset-backed federated baseline slice."""
    config = _load_pilot_config()
    try:
        artifact_path = run_dataset_backed_logreg(config, run_name)
    except Exception as exc:
        update_worker_status(
            worker,
            worker_status="failed",
            summary=f"Dataset-backed baseline failed: {exc}",
            next_step="Fix the dataset or baseline execution issue, then rerun the dataset-backed worker command.",
            phase="dataset-baseline-failed",
            overall_status="dataset-baseline-failed",
        )
        write_dashboard()
        raise typer.Exit(code=1) from exc

    update_worker_status(
        worker,
        worker_status="completed",
        summary="Completed the first dataset-backed federated baseline run on Adult with logistic regression.",
        next_step="Review runtime and metrics, then decide whether to expand to another baseline or dataset.",
        artifact=str(artifact_path.relative_to(default_paths().root)),
        phase="dataset-baseline-complete",
        overall_status="dataset-baseline-complete",
    )
    write_dashboard()
    typer.echo(str(artifact_path.resolve()))


@worker_app.command("consume-directions")
def worker_consume_directions(
    worker: str = typer.Option("experiment-builder", help="Worker publishing the execution step."),
) -> None:
    """Consume the latest Pengu direction and publish it into project status."""
    direction, artifact_path = consume_latest_direction()
    if direction is None or artifact_path is None:
        update_worker_status(
            worker,
            worker_status="idle",
            summary="No new Pengu direction was available to consume.",
            next_step="Wait for a new /project direct instruction or continue the current execution plan.",
            phase="direction-idle",
        )
        write_dashboard()
        typer.echo("No new directions available.")
        return

    direction_text = str(direction.get("direction", "")).strip()
    update_worker_status(
        worker,
        worker_status="directed",
        summary=f"Consumed Pengu direction: {direction_text}",
        next_step="Apply the accepted direction to the next implementation slice and publish a follow-up worker update.",
        artifact=str(artifact_path.relative_to(default_paths().root)),
        phase="direction-consumed",
    )
    write_dashboard()
    typer.echo(str(artifact_path.resolve()))