# federated-tabPFN

Dedicated research execution repository for benchmarking federated TabPFN against comparable tabular models using Flower as the only federated framework.

## Objective

Build a local-first, public-data-only benchmark that answers a narrow research question clearly enough to justify a full paper-scale study.

## Execution Principles

- Flower is the only federated framework.
- Public datasets only.
- Local-machine execution first.
- Start with a pilot before widening scope.
- Save reports from repo artifacts, not from memory.

## Initial Deliverables

1. baseline shortlist
2. dataset shortlist
3. pilot experiment plan
4. initial benchmark scaffold
5. first status report with risks and estimated runtime

## Repository Layout

- `src/federated_tabpfn/` - Python package for shared code
- `configs/` - experiment and pilot configs
- `experiments/` - benchmark plans and run definitions
- `results/` - saved outputs and runtime summaries
- `reports/` - structured status reports
- `papers/` - paper notes and drafts
- `docs/` - capability contract and workflow docs
- `.github/agents/` - stage-specific subagents
- `.github/skills/` - reusable domain skills

## Execution Model

Pengu is the orchestrator. Specialized subagents handle narrow stages:

- `research-scout` for literature, baselines, datasets, and risks
- `experiment-builder` for code, configs, Flower setup, and pilots
- `results-analyst` for runtime summaries, comparisons, and report-ready findings

Expertise is stored in skills rather than split into many narrow agent personas.

## Getting Started

1. Create and activate a Python environment.
2. Install the project in editable mode: `pip install -e .[benchmark]`
3. Read [docs/capability-contract.md](docs/capability-contract.md).
4. Review [docs/dataset-shortlist.md](docs/dataset-shortlist.md) and [docs/baseline-shortlist.md](docs/baseline-shortlist.md).
5. Start with [experiments/pilot.md](experiments/pilot.md).
6. Run `python -m federated_tabpfn show-config`, `python -m federated_tabpfn check-ready`, `python -m federated_tabpfn worker preflight`, `python -m federated_tabpfn worker run-pilot`, `python -m federated_tabpfn worker run-dataset-baseline`, or `python -m federated_tabpfn render-dashboard`.

## Worker Status Surface

Workers now publish machine-readable status for Pengu under:

- `reports/generated/execution-status.json`
- `reports/generated/execution-status.md`
- `reports/generated/dashboard.html`

The first concrete worker execution step is `python -m federated_tabpfn worker preflight`, which:

- reads `configs/pilot.yaml`
- creates a deterministic run artifact in `results/<run-name>/preflight.json`
- records whether placeholders still block execution
- publishes the worker update for Pengu to consume

The first local Flower execution step is `python -m federated_tabpfn worker run-pilot`, which:

- reads the locked pilot config
- runs a local Flower smoke simulation
- saves a pilot artifact in `results/<run-name>/pilot-summary.json`
- publishes a worker update that Pengu can report back

The first dataset-backed benchmark step is `python -m federated_tabpfn worker run-dataset-baseline`, which:

- loads the Adult dataset
- runs a federated logistic regression baseline under Flower
- saves a summary artifact in `results/<run-name>/dataset-baseline-summary.json`
- updates worker status and the dashboard for Pengu to report

The interactive tracking UI is `reports/generated/dashboard.html`, which is regenerated when worker commands update project state.

## Current Status

This repository is intentionally scaffolded for the first pilot. The next implementation slice is:

- finalize dataset shortlist
- finalize baseline shortlist
- add a first config-driven Flower pilot entrypoint
- record local runtime assumptions