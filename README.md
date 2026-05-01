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
- Track the modern Flower surface, not deprecated simulation helpers.

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
6. If a worker needs external credentials such as `TABPFN_TOKEN`, put them in a local `.env` in this repo or point `FEDERATED_TABPFN_ENV_FILE` at another env file before running commands.
7. Run `python -m federated_tabpfn show-config`, `python -m federated_tabpfn show-study-datasets`, `python -m federated_tabpfn show-results`, `python -m federated_tabpfn check-ready`, `python -m federated_tabpfn worker preflight`, `python -m federated_tabpfn worker run-pilot`, `python -m federated_tabpfn worker run-dataset-baseline`, `python -m federated_tabpfn worker run-plan`, or `python -m federated_tabpfn render-dashboard`.

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
- runs a local Flower Message API smoke simulation
- saves a pilot artifact in `results/<run-name>/pilot-summary.json`
- publishes a worker update that Pengu can report back

The first dataset-backed benchmark step is `python -m federated_tabpfn worker run-dataset-baseline`, which:

- loads either the Adult engineering slice or a locked paper-track OpenML dataset
- runs a Flower-backed baseline for logistic regression, random forest, XGBoost, or TabPFN
- saves a summary artifact in `results/<run-name>/dataset-baseline-summary.json`
- updates worker status and the dashboard for Pengu to report

The first phase-oriented execution step is `python -m federated_tabpfn worker run-plan --phase engineering`, which:

- reads the configured study phase from `configs/pilot.yaml`
- skips already completed runs automatically
- runs all currently supported slices for that phase in sequence
- marks unsupported slices explicitly instead of pretending they ran
- updates worker status, results summaries, and the dashboard after each run

An aggregate planning/execution pass is `python -m federated_tabpfn worker run-plan --phase overall`, which:

- combines the engineering slice and the current workshop IID tranche
- skips slices that are already completed
- runs the supported workshop-first matrix in sequence
- gives Pengu one truthful top-level answer to “how far can the study run right now?”

The interactive tracking UI is `reports/generated/dashboard.html`, which is regenerated when worker commands update project state.

The repo also generates a Telegram-friendly results summary under:

- `reports/generated/results-summary.json`
- `reports/generated/results-summary.md`

## Current Status

This repository is now in an early study-facing execution phase:

- Adult engineering runs are executable for logistic regression, random forest, XGBoost, and TabPFN
- the paper-facing dataset path now targets the locked 18-dataset numerical no-missing OpenML-CC18 slice from the original TabPFN paper
- XGBoost supports the paper-facing multiclass path
- random forest uses a Flower-backed serialized local-model ensemble path
- TabPFN is wired into the same execution surface through `tabpfn-client`, and it requires `TABPFN_TOKEN` in the runtime environment before those slices can run
