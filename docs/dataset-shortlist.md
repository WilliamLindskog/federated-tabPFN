# Dataset Shortlist

Study-facing shortlist for a public, local-first federated TabPFN benchmark.

## Selection Rules

- public and reproducible
- classification-first for the first pass
- manageable local runtime for local simulation
- close enough to the original TabPFN evaluation regime to keep claims defensible
- explicit separation between engineering sanity checks and paper-facing benchmark sets

## Paper-Grounded Regime

- The original TabPFN paper emphasized small numerical classification problems and highlighted 18 OpenML-CC18 datasets with up to 1000 training points, up to 100 numerical features, no missing values, and up to 10 classes.
- The same paper also reported an additional 67 small numerical OpenML datasets as a broader validation surface.
- That implies our paper-facing benchmark should not start from arbitrary mixed-feature tabular datasets if we want claims about TabPFN to be scientifically aligned with prior evidence.

## Execution Tracks

### Adult Engineering Slice

- kept as the first executable sanity-check dataset because it is easy to load and debug locally
- useful for validating Message API execution, artifact generation, runtime collection, and Pengu reporting
- not sufficient as the paper-facing benchmark story on its own

### OpenML-CC18 Small Numerical Slice

- primary study track for an initial federated TabPFN claim set
- constrained to datasets that respect the original paper's small-data numerical regime
- should be filtered to avoid missing values and feature spaces that force one-off preprocessing decisions

Locked paper-facing dataset list:

- `11` `balance-scale`
- `14` `mfeat-fourier`
- `16` `mfeat-karhunen`
- `18` `mfeat-morphological`
- `22` `mfeat-zernike`
- `37` `diabetes`
- `54` `vehicle`
- `458` `analcatdata_authorship`
- `1049` `pc4`
- `1050` `pc3`
- `1063` `kc2`
- `1068` `pc1`
- `1462` `banknote-authentication`
- `1464` `blood-transfusion-service-center`
- `1494` `qsar-biodeg`
- `1510` `wdbc`
- `40982` `steel-plates-fault`
- `40994` `climate-model-simulation-crashes`

These 18 datasets are the paper-facing default. The earlier 30-dataset reduced CC18 slice is no longer specific enough for headline claims because it still includes categorical and missing-value settings where the original paper was explicitly more cautious.

### OpenML Small Numerical Holdout Slice

- secondary validation track meant to mirror the original paper's broader 67-dataset numerical evaluation spirit
- useful once the engineering slice and the first CC18 subset are stable

### Robustness Track

- datasets with categorical features andor missing values should be treated as robustness analyses, not as the first headline claim
- this matters because the original TabPFN discussion is more favorable on numerical datasets than on mixed-feature settings

## Split Regimes

- `iid`: first executable regime and the current engineering default
- `label_skew`: next priority because it exposes class-imbalance and client heterogeneity without changing total data volume
- `quantity_skew`: useful for understanding aggregation sensitivity and communication efficiency

## Initial Recommendation

Keep `Adult` as the engineering slice. Build the first paper-facing matrix from a filtered small numerical OpenML shortlist, then widen to the holdout numerical slice only after the Flower Datasets partition flow is in place.

## Open Questions

- exact OpenML task list to inherit from CC18 after federated filtering
- whether any target datasets violate TabPFN runtime or licensing constraints in local execution
- how much non-IID severity to model before the benchmark stops resembling prior TabPFN evidence