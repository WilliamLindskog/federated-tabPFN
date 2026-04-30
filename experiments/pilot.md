# Pilot Experiment Plan

## Goal

Determine whether federated TabPFN produces a publishable empirical story relative to strong tabular baselines under a Flower-only local benchmark setup.

## Immediate Submission Target

- target: `ICML 2026 Workshop on Foundation Models for Structured Data`
- deadline: `May 8, 2026 (AoE)`
- format: short workshop paper

## Scope Constraints

- public datasets only
- local-machine execution first
- Flower only
- small matrix before full expansion
- prioritize an IID paper-ready comparison before widening to non-IID

## First Deliverables

1. 2-3 candidate datasets
2. 3-5 baseline models
3. one Flower pilot config
4. one initial benchmark entrypoint
5. one status report with runtime and risk notes

## Workshop-First Execution Order

1. finish the engineering slice on Adult
2. move to the paper-facing IID tranche with `Random Forest`, `XGBoost`, and `TabPFN`
3. optionally add `TabH2O` if integration is easy and fair
4. only widen to non-IID if time remains after the IID story is credible

## Decision Rule

Continue to a broader benchmark only if the pilot reveals a clear comparison story, feasible runtime, and a credible novelty angle.
