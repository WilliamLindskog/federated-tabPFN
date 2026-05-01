# Federated TabPFN for Small Numerical Tabular Classification: An IID Benchmark on the OpenML CC18 Slice

## Abstract

Foundation-model-style approaches for tabular classification have recently shown strong performance in centralized evaluation, but their behavior in federated settings remains underexplored. We study a focused question: in the original small-numerical tabular regime associated with prior TabPFN evaluation, how does federated TabPFN compare to strong classical baselines under a Flower-only setup? We evaluate `random_forest`, `xgboost`, and `tabpfn` on a locked `18`-dataset small-numerical no-missing slice of OpenML CC18 using an IID two-client federated benchmark. Federated TabPFN achieves the strongest average performance overall, with mean accuracy `0.8897` and mean evaluation loss `0.2453`, and wins on `14/18` datasets. The strongest classical baseline is `random_forest`, which reaches mean accuracy `0.8650` and wins on `3/18` datasets, while `xgboost` reaches mean accuracy `0.8209` and wins on `1/18`. TabPFN's losses are few and narrow, but its runtime is higher than the classical baselines. These findings suggest that tabular foundation models remain competitive in federated evaluation even in a deliberately narrow benchmark setting, while also highlighting runtime and scope limitations that must be addressed in broader future studies.

## 1. Introduction

Tabular classification remains central to many applied machine learning workflows, especially in domains where privacy, decentralization, or organizational boundaries make centralized data pooling difficult. Federated learning offers one route for learning across such distributed data silos while avoiding direct raw-data sharing. At the same time, tabular foundation-model-style methods have become increasingly relevant, with TabPFN emerging as a particularly strong approach for small to medium sized tabular classification problems.

Despite the growing interest in both federated learning and foundation-model-style tabular methods, there is still relatively little empirical evidence about how such methods behave in a federated setting. This gap matters for two reasons. First, many realistic tabular applications are precisely the kinds of tasks where federated execution is appealing. Second, strong centralized performance does not automatically imply strong behavior once the evaluation or execution setup becomes distributed.

This work addresses a deliberately narrow version of that broader question. Rather than proposing a new federated optimization algorithm, we ask whether TabPFN remains competitive in a simple Flower-based federated benchmark on the original small-numerical OpenML CC18 slice associated with prior TabPFN-style evaluation. We compare federated TabPFN against two strong tabular baselines, random forest and XGBoost, using a Flower-only setup and public data.

The benchmark is intentionally scoped for a short workshop paper. We focus on `18` numerical no-missing datasets, use an IID split regime, and emphasize empirical clarity over breadth. Within that scope, the main result is straightforward: federated TabPFN achieves the strongest average predictive performance and wins on most datasets, while introducing a clear runtime cost relative to the strongest classical baseline.

Our contribution is therefore benchmark-oriented rather than algorithmic. We provide a compact federated evaluation surface for tabular foundation-model-style comparison, show that TabPFN is usually the strongest model in this setting, and identify the specific tradeoffs and limitations that should shape a larger follow-on study.

## 2. Scope and Positioning

This paper should be read as a focused benchmark study, not as a claim of general superiority for foundation models on all structured-data tasks and not as a new federated training method. The goal is narrower:

- evaluate whether TabPFN remains strong under a Flower-only federated setup,
- keep the comparison grounded in the original small-numerical tabular regime,
- and produce a clean empirical story suitable for a short workshop submission.

That narrowness is a strength here. It lets us separate the immediate question of comparative federated performance from broader questions around non-IID robustness, large-scale deployment, multimodal structured data, or novel federated optimization schemes.

## 3. Experimental Setup

### 3.1 Benchmark Objective

We evaluate the following question:

> In TabPFN's original small-numerical regime, how does federated TabPFN compare to strong tabular baselines under a Flower-only setup?

### 3.2 Datasets

The paper-facing benchmark uses the locked `tabpfn_paper_cc18_numerical_18` track:

- source: OpenML CC18
- slice: small numerical classification datasets with no missing values
- dataset count: `18`

The included datasets are:

- `balance-scale`
- `mfeat-fourier`
- `mfeat-karhunen`
- `mfeat-morphological`
- `mfeat-zernike`
- `diabetes`
- `vehicle`
- `analcatdata_authorship`
- `pc4`
- `pc3`
- `kc2`
- `pc1`
- `banknote-authentication`
- `blood-transfusion-service-center`
- `qsar-biodeg`
- `wdbc`
- `steel-plates-fault`
- `climate-model-simulation-crashes`

An Adult engineering slice was also used earlier to validate the execution path and sanity-check baseline behavior, but it is not part of the main paper-facing claim.

### 3.3 Baselines

We compare three models:

- `random_forest`
- `xgboost`
- `tabpfn`

These were chosen to provide:

- one strong ensemble tree baseline,
- one strong boosted-tree baseline,
- and one foundation-model-style tabular baseline.

### 3.4 Federated Setup

The benchmark is executed through a Flower-only local federated setup. The execution surface is benchmark-oriented rather than production-deployment-oriented. In particular:

- client count: `2`
- split regime: `iid`
- data is partitioned across two simulated clients
- public data only

For the current workshop version, we intentionally keep the study IID-only. The reason is not that non-IID effects are unimportant, but that the workshop submission benefits from a clean first comparative result before broadening the scope.

### 3.5 Metrics

We track:

- accuracy
- evaluation loss
- runtime

Accuracy is the main ranking metric in this study, with evaluation loss used as a supporting signal and runtime used to interpret practical tradeoffs.

## 4. Results

### 4.1 Aggregate Outcome

Across the `18` IID paper-track datasets:

| Baseline | Avg. Accuracy | Avg. Eval Loss | Avg. Runtime | Dataset Wins |
| --- | ---: | ---: | ---: | ---: |
| `tabpfn` | `0.8897` | `0.2453` | `19.51s` | `14/18` |
| `random_forest` | `0.8650` | `0.4102` | `7.63s` | `3/18` |
| `xgboost` | `0.8209` | `0.7608` | `11.05s` | `1/18` |

The central empirical result is clear: federated TabPFN is the strongest model overall in this benchmark. It has the highest average accuracy, the best average evaluation loss, and the largest number of dataset wins.

### 4.2 Where TabPFN Wins Clearly

Several datasets show a meaningful positive margin for TabPFN over the best non-TabPFN comparator:

| Dataset | TabPFN Accuracy | Best Non-TabPFN Baseline | Margin |
| --- | ---: | --- | ---: |
| `steel-plates-fault` | `0.8045` | `random_forest` | `+0.0638` |
| `balance-scale` | `0.9490` | `random_forest` | `+0.0637` |
| `vehicle` | `0.8585` | `random_forest` | `+0.0566` |
| `mfeat-fourier` | `0.8900` | `random_forest` | `+0.0560` |
| `mfeat-zernike` | `0.8420` | `random_forest` | `+0.0500` |
| `mfeat-morphological` | `0.7600` | `xgboost` | `+0.0360` |

These are especially useful for the workshop paper because they show that the result is not merely a weak average advantage. On several representative datasets, TabPFN is clearly ahead.

TabPFN also achieves very high absolute performance on a number of cleaner binary tasks:

- `banknote-authentication`: `1.0000`
- `wdbc`: `1.0000`
- `climate-model-simulation-crashes`: `0.9412`
- `mfeat-karhunen`: `0.9840`

### 4.3 Where TabPFN Loses

TabPFN loses on only `4` of the `18` datasets:

| Dataset | Winner | Winner Accuracy | TabPFN Accuracy | Delta |
| --- | --- | ---: | ---: | ---: |
| `pc4` | `random_forest` | `0.8989` | `0.8962` | `0.0027` |
| `pc3` | `random_forest` | `0.9031` | `0.8980` | `0.0051` |
| `kc2` | `xgboost` | `0.8258` | `0.8182` | `0.0076` |
| `pc1` | `random_forest` | `0.9353` | `0.9245` | `0.0108` |

These losses are small. This matters for interpretation: the result is not “TabPFN dominates everywhere,” but rather “TabPFN is usually strongest, and where it is not, the gap is modest.” That is a more credible and useful benchmark conclusion.

### 4.4 Interpretation of the Classical Baselines

Among the classical baselines, random forest is the more important comparator. It is stronger than XGBoost on average and wins on more datasets. XGBoost remains useful for triangulation, but the main paper story is more naturally framed as:

- `tabpfn` versus `random_forest`,
- with `xgboost` as an additional supporting baseline rather than the central competitor.

This matters for how the final paper should allocate space. If the paper is short, the figures and discussion should emphasize TabPFN's relationship to random forest first.

## 5. Runtime and Tradeoffs

The main cost of TabPFN in this benchmark is runtime. On average:

- `tabpfn`: `19.51s`
- `xgboost`: `11.05s`
- `random_forest`: `7.63s`

So the benchmark does not suggest a free lunch. Instead, it suggests a specific tradeoff:

- TabPFN gives the best predictive performance and the best average loss,
- but it is noticeably slower than the strongest classical baseline.

That tradeoff should be treated as part of the contribution rather than as an inconvenient detail. For a workshop paper, this helps the study sound serious and balanced: the foundation-model-style baseline is strong, but it is not obviously the best choice under all operational constraints.

## 6. Engineering Validation

Before running the paper-facing IID tranche, we validated the execution path on an Adult engineering slice. The IID engineering results were:

- `logistic_regression`: `0.8420`
- `random_forest`: `0.8320`
- `xgboost`: `0.8200`
- `tabpfn`: `0.8333`

This engineering slice was not meant to be a headline result. Its role was to verify the benchmark surface, artifact generation, and monitoring pipeline. The engineering non-IID variants also did not reveal contradictions strong enough to undermine the main paper-facing IID story.

## 7. Limitations

This study has several important limitations.

First, the workshop-facing claim is IID-only. That is a deliberate scope decision, but it means we are not yet making a statement about how these baselines compare under stronger client heterogeneity.

Second, the dataset scope is intentionally narrow. We use the small-numerical no-missing CC18 slice aligned with the original TabPFN-style evaluation regime. This makes the study cleaner, but it also limits generality.

Third, this work does not propose a novel federated optimization or aggregation algorithm. The contribution is benchmark evidence under a Flower-only federated setup.

Fourth, the execution path is benchmark-oriented rather than a production deployment study. That is appropriate for the current paper, but it should not be mistaken for a full systems evaluation.

Finally, the workshop paper format encourages a compact empirical story. Some potentially interesting follow-up questions, especially around non-IID behavior and broader structured-data scope, are intentionally deferred.

## 8. Discussion and Extensions

The current result is already strong enough for a narrow workshop submission, but it also points to a larger research path.

The most immediate extension is non-IID evaluation. The main reason to add it is not to make the paper look bigger, but to test whether TabPFN's current advantage is robust once the client distributions become more heterogeneous. The natural first extensions would be:

- label skew
- quantity skew

A second extension is broader structured-data scope. The current study is intentionally limited to small numerical classification. A stronger post-workshop paper could ask whether the same pattern persists across:

- more heterogeneous OpenML holdout datasets
- larger tabular problems
- potentially additional structured-data settings

A third extension is comparator depth. The present results already suggest that random forest is the strongest classical comparator in this benchmark. That creates room for a better second paper: instead of broadening aimlessly, the next stage can ask whether TabPFN remains competitive against an even more carefully tuned classical stack under more demanding federation regimes.

A fourth extension is methodology clarity. Since this study is benchmark-oriented, a stronger follow-on paper could sharpen the methodological discussion around what exactly it means to evaluate foundation-model-style tabular systems in a federated setting when the contribution is comparative rather than algorithmic.

## 9. Conclusion

We studied a narrow but relevant question: how federated TabPFN compares to strong classical tabular baselines in the original small-numerical regime under a Flower-only IID setup. Across `18` OpenML CC18 datasets, federated TabPFN achieves the strongest average accuracy and evaluation loss and wins on `14/18` datasets. Its losses are few and narrow, but its runtime is higher than the strongest classical baseline.

These findings suggest that foundation-model-style tabular methods remain promising even when evaluated through a federated benchmark surface. At the same time, the current evidence should be interpreted carefully: this is an IID-only benchmark result on a deliberately narrow dataset slice, not a broad claim about all structured-data federation scenarios. That balance makes the result suitable for a short workshop submission and also provides a strong basis for a larger follow-on study.

## Appendix-Style Notes for Expansion

If this draft is expanded into a longer version, the highest-value additions are:

- a full per-dataset results table in publication-ready form
- a runtime comparison figure
- one concise win-count or mean-performance summary figure
- one small non-IID extension if it materially strengthens the story
- a short reproducibility note describing the benchmark execution surface and artifacts
