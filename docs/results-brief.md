# Federated TabPFN Workshop Results Brief

## Objective

Summarize the completed IID workshop tranche for the **ICML 2026 Workshop on Foundation Models for Structured Data**.

Primary study question:

> In TabPFN's original small-numerical regime, how does federated TabPFN compare to strong tabular baselines under a Flower-only setup?

## Completed Scope

- Execution status: `overall-complete`
- Runnable specs completed: `49/49`
- Previously completed specs skipped: `17`
- Unsupported specs blocked: `0`
- Core workshop tranche:
  - `18` OpenML CC18 small-numerical datasets
  - `3` baselines: `random_forest`, `xgboost`, `tabpfn`
  - `1` split regime: `iid`

This brief focuses on the **paper-facing IID tranche**, not the engineering slice.

## Aggregate Result

Across the `18` IID paper-track datasets:

| Baseline | Avg. Accuracy | Avg. Eval Loss | Avg. Runtime | Dataset Wins |
| --- | ---: | ---: | ---: | ---: |
| `tabpfn` | `0.8897` | `0.2453` | `19.51s` | `14/18` |
| `random_forest` | `0.8650` | `0.4102` | `7.63s` | `3/18` |
| `xgboost` | `0.8209` | `0.7608` | `11.05s` | `1/18` |

Headline observation:

- `tabpfn` is the strongest model overall in this federated IID setting.
- `random_forest` is the strongest classical baseline.
- `xgboost` is useful as a comparator, but it is not the main competitive baseline in this tranche.

## Main Empirical Story

The strongest workshop claim supported by the current results is:

> Federated TabPFN is usually the best-performing model on the original small-numerical CC18 slice under a Flower-only IID setup, and when it loses, it tends to lose narrowly.

This is attractive for the workshop because it is:

- narrow
- empirical
- foundation-model relevant
- easy to explain within a short paper

## Strongest Wins for TabPFN

The clearest positive margins for `tabpfn` are:

| Dataset | TabPFN Accuracy | Best Non-TabPFN Baseline | Margin |
| --- | ---: | --- | ---: |
| `openml:40982:steel-plates-fault` | `0.8045` | `random_forest` | `+0.0638` |
| `openml:11:balance-scale` | `0.9490` | `random_forest` | `+0.0637` |
| `openml:54:vehicle` | `0.8585` | `random_forest` | `+0.0566` |
| `openml:14:mfeat-fourier` | `0.8900` | `random_forest` | `+0.0560` |
| `openml:22:mfeat-zernike` | `0.8420` | `random_forest` | `+0.0500` |
| `openml:18:mfeat-morphological` | `0.7600` | `xgboost` | `+0.0360` |

It also reaches very strong absolute performance on several datasets:

- `openml:1462:banknote-authentication`: `1.0000`
- `openml:1510:wdbc`: `1.0000`
- `openml:40994:climate-model-simulation-crashes`: `0.9412`
- `openml:16:mfeat-karhunen`: `0.9840`

## Where TabPFN Loses

`tabpfn` loses on only `4` of `18` datasets, and all losses are small:

| Dataset | Winner | Winner Accuracy | TabPFN Accuracy | Delta |
| --- | --- | ---: | ---: | ---: |
| `openml:1049:pc4` | `random_forest` | `0.8989` | `0.8962` | `0.0027` |
| `openml:1050:pc3` | `random_forest` | `0.9031` | `0.8980` | `0.0051` |
| `openml:1063:kc2` | `xgboost` | `0.8258` | `0.8182` | `0.0076` |
| `openml:1068:pc1` | `random_forest` | `0.9353` | `0.9245` | `0.0108` |

This is useful paper material because it suggests the benchmark is not trivial or cherry-picked.

## Runtime Interpretation

Runtime tradeoff:

- `tabpfn` has the best predictive profile, but it is the slowest model in the study.
- `random_forest` is materially faster and remains strong.
- `xgboost` sits in the middle on runtime, but does not justify equal emphasis on performance grounds.

That suggests the cleanest paper framing is:

- performance leadership: `tabpfn`
- strongest classical comparator: `random_forest`
- runtime tradeoff: worth discussing explicitly

## Engineering Slice Sanity Check

The Adult engineering slice also behaved reasonably:

- `logistic_regression` IID: `0.8420`
- `random_forest` IID: `0.8320`
- `xgboost` IID: `0.8200`
- `tabpfn` IID: `0.8333`

Non-IID engineering variants did not reveal a contradiction that would undermine the paper-facing IID story.

## Workshop Recommendation

Recommended workshop story:

1. Present this as a **focused federated benchmark** for tabular foundation-model evaluation.
2. Keep the main comparison centered on:
   - `tabpfn`
   - `random_forest`
   - `xgboost`
3. Emphasize:
   - `tabpfn` wins `14/18`
   - best mean accuracy
   - best mean eval loss
   - losses are few and narrow
4. Treat runtime as an honest tradeoff, not a hidden weakness.

## Risks / Caveats

- This is currently an IID-only workshop story.
- The federated setup is a serialized local-model ensemble / Flower-local execution path, not a novel algorithmic training contribution.
- The paper should avoid overclaiming broad “foundation models for all structured data” conclusions.
- `xgboost` underperformance means the strongest comparison is really `tabpfn` vs `random_forest`.

## Recommended Next Steps

1. Turn these findings into a short workshop paper outline.
2. Decide which `4-6` datasets to highlight in figures or tables.
3. Add a compact runtime discussion.
4. Only expand beyond IID if it strengthens the story without destabilizing the deadline.
