# Dataset Shortlist

Initial pilot candidates for a public, local-first federated tabular benchmark.

## Selection Rules

- public and reproducible
- classification-first for the first pass
- manageable local runtime
- varied enough to expose model-family tradeoffs

## Candidate Datasets

### Covertype

- large enough to stress runtime and model behavior
- strong classical tabular benchmark reference point
- useful if the pilot needs one higher-scale public dataset

### Adult

- standard public classification dataset
- light local runtime
- useful for establishing the first end-to-end Flower path

### Bank Marketing

- common tabular classification baseline
- moderate size and practical feature mix
- useful as a second or third pilot dataset

## Initial Recommendation

Start with `Adult` and `Bank Marketing` for the first runnable pilot. Keep `Covertype` as the first scale-up candidate once the pipeline is stable.

## Open Questions

- exact federation split strategy
- classification-only first pass versus mixed task types
- how much client heterogeneity to model in the pilot