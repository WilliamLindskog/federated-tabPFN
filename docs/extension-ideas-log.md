# Extension Ideas Log

## Purpose

This file is a persistent scratchpad for follow-on study ideas so they do not get lost between sessions.

Items here are intentionally broader and lower-friction than the more structured prioritization in `extensions-roadmap.md`.

## Current Ideas

### Heterogeneity extensions

- Add `label_skew` across the full `18`-dataset paper track and core trio.
- Add `quantity_skew` across the same paper track and core trio.
- Add `feature_skew` as a later non-IID extension once the OpenML paper-track partitioning path supports it.
- Compare whether TabPFN's current IID win profile survives the different heterogeneity types.

### Dataset-scope extensions

- Add the `tabpfn_paper_openml_numerical_holdout` track after the workshop-focused tranche.
- Consider a larger dataset expansion only after the federated story is already solid.
- Keep the workshop submission anchored to the current narrow CC18 slice rather than collapsing everything into one oversized benchmark.

### Comparator extensions

- Test `TabH2O` if integration is stable, fair, and reproducible.
- Consider stronger classical baseline tuning, especially for `random_forest`, since it is currently the strongest classical comparator.
- Consider whether additional neural tabular baselines are worth adding in a larger follow-on study.

### Resource-analysis extensions

- Surface `max_rss_bytes` in the dashboard and paper-facing result summaries.
- Add explicit comparison of:
  - runtime
  - memory footprint
  - model parameter bytes
  - estimated upstream communication
  - estimated downstream communication
- Use this to turn the paper into a stronger “performance versus cost” story, not just an accuracy table.

### Paper-quality extensions

- Add a compact non-IID result if it strengthens the workshop paper without destabilizing scope.
- Produce a publication-ready per-dataset main table.
- Add figures for win counts, average performance, runtime, memory, and communication.
- Tighten the wording around what the Flower-only setup evaluates and what it does not.

### Bigger PhD directions

- Expand toward a broader federated benchmark paper for tabular model families.
- Explore whether there is a stronger methodology paper around federated evaluation of foundation-model-style tabular systems.
- Use the workshop result as a stepping stone toward a stronger journal-scale paper with more datasets, more heterogeneity, and more robust baseline tuning.
