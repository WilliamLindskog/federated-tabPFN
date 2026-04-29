# Worker Protocol

This file defines how specialized workers should execute and report status to Pengu.

## Rule

Workers do not report status conversationally only. They must leave repo artifacts that Pengu can read.

## Required Status Outputs

- `reports/generated/execution-status.json`
- `reports/generated/execution-status.md`

## Required Worker Fields

- worker name
- worker status
- summary
- next step
- updated timestamp
- artifact path when one exists

## Current Concrete Execution Step

Use:

`python -m federated_tabpfn worker preflight`

This is the first bounded execution step. It does not run the benchmark yet. It verifies whether the pilot is blocked by placeholder config and leaves a deterministic artifact in `results/`.

Use:

`python -m federated_tabpfn worker consume-directions`

This accepts the latest unconsumed direction from Pengu, records it as the active direction, and publishes the acceptance into execution status.

## Intended Flow

1. Pengu assigns a narrow slice to a worker.
2. The worker performs a concrete action in the repo.
3. The worker publishes a status update through the worker CLI.
4. Pengu reads the generated status files and reports actual repo state.