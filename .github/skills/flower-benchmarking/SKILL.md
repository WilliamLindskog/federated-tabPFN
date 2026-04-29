---
name: flower-benchmarking
description: 'Use for Flower-only federated benchmark implementation, pilot setup, client/server structure, config choices, and local-first experiment execution in this repository.'
user-invocable: false
---

# Flower Benchmarking

## When to Use

- building or refining the Flower experiment scaffold
- checking that a new implementation slice stays Flower-only
- narrowing a local-first pilot run

## Procedure

1. Read `README.md`, `docs/capability-contract.md`, and `experiments/pilot.md`.
2. Keep Flower as the only federated framework.
3. Prefer the smallest config-driven pilot before widening the experiment matrix.
4. Save runtime assumptions and outputs in `results/` or `reports/`.

## Rules

- do not introduce a second federated framework
- do not optimize for distributed scale before the local pilot works
- do not add broad infra before a runnable pilot exists