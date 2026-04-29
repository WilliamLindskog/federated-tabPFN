# Baseline Shortlist

Initial comparable models for the pilot benchmark.

## Selection Rules

- comparable on tabular classification tasks
- realistic local-machine runtime
- defensible as strong baselines
- enough variety to reveal a real model-family story
- baseline preprocessing should follow each model family's best-practice path, not a forced single pipeline

## Candidate Baselines

### Logistic Regression

- simple calibration point
- very cheap runtime
- useful sanity-check baseline

### Random Forest

- strong classical ensemble baseline
- robust comparison point for tabular data

### XGBoost

- mandatory tree baseline for any serious TabPFN comparison
- explicitly discussed in the original TabPFN review process and should not be left as a later extra
- should retain native handling where appropriate instead of forcing linear-model preprocessing onto it

### Extra Trees or LightGBM

- useful second tree-family baseline once the XGBoost path is stable
- helps distinguish whether any gain is specific to one boosting implementation or more general across strong tabular trees

### MLP

- lightweight neural comparison point
- useful because prior federated tabular work often includes neural baselines

### TabPFN

- target model family under study
- potentially stronger novelty signal than standard tabular baselines alone
- must be evaluated in a regime consistent with its small-data strengths
- should not receive scaling or one-hot encoding that the current TabPFN guidance advises against

## Initial Recommendation

Start the engineering slice with `Logistic Regression`, then make `Random Forest`, `XGBoost`, and `TabPFN` the first study-facing comparison set. Keep `MLP` as a secondary neural reference once the tree baselines and split regimes are stable.

## Open Questions

- exact choice between XGBoost-only versus XGBoost plus LightGBM or Extra Trees in the first full matrix
- whether to add a second tabular foundation model after the first robust TabPFN versus tree benchmark lands