# Baseline Shortlist

Initial comparable models for the pilot benchmark.

## Selection Rules

- comparable on tabular classification tasks
- realistic local-machine runtime
- defensible as strong baselines
- enough variety to reveal a real model-family story

## Candidate Baselines

### Logistic Regression

- simple calibration point
- very cheap runtime
- useful sanity-check baseline

### Random Forest

- strong classical ensemble baseline
- robust comparison point for tabular data

### XGBoost-style Gradient Boosting

- likely one of the strongest classical baselines
- important if the study claims modern models outperform established tabular methods

### MLP

- lightweight neural comparison point
- useful because prior federated tabular work often includes neural baselines

### TabPFN

- target model family under study
- potentially stronger novelty signal than standard tabular baselines alone
- may need a narrower pilot because of runtime or setup constraints

## Initial Recommendation

Start the first pilot with `Logistic Regression`, `Random Forest`, `MLP`, and `TabPFN`. Add gradient boosting immediately after the end-to-end Flower path is stable if local runtime remains acceptable.

## Open Questions

- exact implementation choice for gradient boosting under the Flower-only constraint
- fairness of comparing TabPFN on the smallest pilot datasets versus larger-scale datasets