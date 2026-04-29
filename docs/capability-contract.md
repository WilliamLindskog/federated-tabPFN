# Capability Contract

This file defines what this repository must be able to do before Pengu can be trusted to execute the full study instead of only planning it.

## Mandatory Capabilities

### Research Discovery

- identify public tabular datasets suitable for federation
- shortlist comparable baseline models
- capture related-work and novelty constraints

### Benchmark Implementation

- use Flower as the only federated framework
- define config-driven pilot experiments
- support local-machine execution first
- save run outputs in deterministic locations

### Reporting

- generate status reports from saved artifacts
- track risks, blockers, and runtime estimates
- preserve experiment assumptions in version control

## Minimum Repo Outputs

- dataset shortlist
- baseline shortlist
- pilot plan
- first runnable benchmark scaffold
- first status report

## Readiness Checks

The repository is only considered execution-ready when all of the following are true:

1. one pilot can be launched from a documented command
2. Flower is the only federated framework in use
3. datasets are public and documented
4. baseline choices are justified and scoped
5. results can be summarized from files in `results/` and `reports/`

## Non-Goals For The First Pass

- cloud execution
- broad dataset expansion
- large-scale hyperparameter sweeps
- paper drafting before pilot signal exists