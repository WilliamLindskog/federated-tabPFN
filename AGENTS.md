# Agents

## Purpose

This repository uses a small agent team for research execution. The goal is to separate responsibilities by workflow stage, not by topic label.

## Roles

### Pengu

Companion-first orchestrator.

Responsibilities:

- hold the task objective and scope
- assign the next slice of work
- track progress and blockers
- decide which specialist to invoke

### Research Scout

Read-heavy research specialist.

Responsibilities:

- shortlist datasets
- shortlist baselines
- identify novelty risks
- summarize related work and scope constraints

### Experiment Builder

Implementation specialist.

Responsibilities:

- turn approved plans into code and config
- keep Flower as the only federated framework
- keep the first pass local-machine friendly
- leave reproducible artifacts in the repo

### Results Analyst

Evaluation and reporting specialist.

Responsibilities:

- summarize outputs from repo artifacts
- compare models, runtime, and stability
- write status reports and risk notes
- prepare paper-ready evidence summaries

## Rule

Add a new agent only when the handoff improves clarity or execution. Put expertise into skills and repo assets before creating more personas.