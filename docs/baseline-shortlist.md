# Baseline Shortlist

Initial comparable models for the pilot benchmark.

## Selection Rules

- comparable on tabular classification tasks
- realistic local-machine runtime
- defensible as strong baselines
- enough variety to reveal a real model-family story
- baseline preprocessing should follow each model family's best-practice path, not a forced single pipeline
- workshop-first scope should prefer models that can be integrated and defended quickly

## Candidate Baselines

### Logistic Regression

- simple calibration point
- very cheap runtime
- useful sanity-check baseline
- should remain a secondary baseline once the study-facing tranche begins

### Random Forest

- strong classical ensemble baseline
- robust comparison point for tabular data
- one of the first study-facing baselines

### XGBoost

- mandatory tree baseline for any serious TabPFN comparison
- explicitly discussed in the original TabPFN review process and should not be left as a later extra
- should retain native handling where appropriate instead of forcing linear-model preprocessing onto it
- one of the first study-facing baselines

### MLP

- lightweight neural comparison point
- useful because prior federated tabular work often includes neural baselines
- should remain secondary unless the workshop story clearly needs a neural counterpoint early

### TabPFN

- target model family under study
- potentially stronger novelty signal than standard tabular baselines alone
- must be evaluated in a regime consistent with its small-data strengths
- should not receive scaling or one-hot encoding that the current TabPFN guidance advises against
- one of the first study-facing baselines

### TabH2O

- optional tabular foundation-model comparator
- only include if the API and evaluation setup are low-friction and reproducible enough for a fair comparison
- should not block the first workshop submission tranche

## Workshop-First Recommendation

Use this priority order:

1. Finish the Adult engineering slice.
2. Move to the first study-facing IID tranche with `Random Forest`, `XGBoost`, and `TabPFN`.
3. Add `TabH2O` only if it is quick to integrate and compare fairly.
4. Leave `MLP` and the broader non-IID expansion for later unless the workshop story still looks too thin.

## Open Questions

- whether `TabH2O` is easy enough to evaluate reproducibly under the current local-first constraints
- whether the first workshop story is stronger with only tree baselines plus TabPFN, or whether one neural comparator is still needed
