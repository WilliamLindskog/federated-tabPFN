# Initial Status Report

## Objective

Benchmark federated TabPFN against comparable tabular models using Flower only, public datasets only, and local-machine execution first.

## Completed

- dedicated research repository created
- repo execution contract documented
- pilot experiment plan created
- initial dataset shortlist created
- initial baseline shortlist created
- stage-specific subagents and domain skills added
- minimal Python package scaffold added

## Current State

The repository is ready for the next implementation slice: a config-driven Flower pilot entrypoint and the first explicit federation/data split assumptions.

## Risks

- TabPFN runtime or setup constraints may force a narrower initial matrix
- gradient boosting may need to be deferred until the first pilot path is stable
- novelty depends on comparison quality and benchmark framing, not only model inclusion

## Estimated Runtime

- documentation and scaffold: complete
- first pilot implementation slice: low to moderate effort
- first local pilot run: likely feasible once dataset loading and model wrappers are in place

## Next Step

Implement a first local pilot command that loads `configs/pilot.yaml`, checks readiness, and creates a deterministic run directory.