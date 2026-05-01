# Extensions Roadmap

## Purpose

This document lists the most valuable extensions to strengthen the current workshop result into a better paper and a more durable PhD contribution.

The goal is not to add scope indiscriminately. The goal is to choose extensions that improve:

- publishability
- novelty
- robustness
- long-term thesis value

## Tier 1: Highest-Value Immediate Extensions

### 1. Non-IID robustness tranche

Add a controlled follow-up on the same core trio:

- `random_forest`
- `xgboost`
- `tabpfn`

Preferred order:

1. `label_skew`
2. `quantity_skew`
3. `feature_skew`

Why this matters:

- tests whether TabPFN's current advantage survives client heterogeneity
- gives the workshop result a stronger “federated” angle
- creates a natural bridge into a stronger journal-scale version

Additional note:

- `feature_skew` is scientifically important, but it should be treated as a later extension than label and quantity skew because it is more likely to complicate interpretation in a short workshop paper.

Why not make it mandatory immediately:

- the current workshop story already works without it
- this should only be added if it strengthens the narrative cleanly

### 2. Publication-ready figure and table set

Current result quality is good enough that presentation matters.

Minimum additions:

- full per-dataset main results table
- mean accuracy / mean loss summary figure
- runtime figure
- memory / peak RSS figure
- communication footprint figure
- win-count summary figure

Why this matters:

- improves readability and perceived rigor quickly
- low implementation risk
- high leverage for submission quality

Resource reporting note:

- the benchmark artifacts already capture `max_rss_bytes`, `model_parameter_bytes`, `estimated_upstream_bytes`, and `estimated_downstream_bytes`; these should be surfaced explicitly in the dashboard and the paper-facing summaries.

### 3. Stronger discussion of the federated execution model

The current study is benchmark-oriented, not algorithmically novel.

That makes the wording and methodological framing important:

- explain what the Flower-only setup evaluates
- explain what it does not evaluate
- avoid overstating the contribution

Why this matters:

- reduces reviewer skepticism
- makes the paper sound more mature and defensible

## Tier 2: Strong Follow-On Paper Extensions

### 4. Holdout numerical OpenML extension

Add a second dataset track beyond the locked CC18 slice:

- `tabpfn_paper_openml_numerical_holdout`

Why this matters:

- tests whether the current result is specific to the original benchmark slice
- increases robustness and external validity
- makes the follow-on paper less benchmark-locked

### 5. Stronger classical baseline tuning

Random forest is already the strongest classical comparator in the current tranche.

A follow-on study should ask:

- does TabPFN still win if the strongest classical baselines are tuned more carefully?
- are the current advantages robust or partly due to shallow configuration choices?

Why this matters:

- improves credibility
- reduces the chance of an “insufficiently tuned baseline” critique

### 6. Additional foundation-model-style comparator

Potential example:

- `TabH2O`, if integration is stable, fair, and reproducible

Why this matters:

- makes the study less like “TabPFN vs classical baselines only”
- strengthens the workshop's foundation-model-for-structured-data relevance

Why it should remain secondary:

- easy to destabilize the current clean story
- hosted dependencies and fairness concerns need to be managed carefully

## Tier 3: Bigger PhD-Oriented Research Directions

### 7. Federated TabPFN under heterogeneous federation regimes

Move beyond a benchmark result toward a broader empirical paper:

- more clients
- stronger heterogeneity
- multiple partition strategies
- deeper robustness analysis

This is a strong candidate for a larger follow-on paper if the initial non-IID signals are promising.

### 8. Federated benchmark paper for tabular model families

Expand from a TabPFN-centered workshop story to a broader benchmark contribution:

- tree ensembles
- boosted trees
- foundation-model-style tabular methods
- potentially neural tabular baselines

This aligns well with the benchmark-first PhD strategy already discussed.

### 9. Federated TabPFN methodology paper

If the empirical signal stays strong, a later paper could explore:

- more principled federated evaluation design
- aggregation or adaptation strategies specific to TabPFN-style inference
- practical guidance for foundation-model-style tabular federation

This should only happen if the benchmark evidence continues to justify deeper investment.

## Recommended Next Order

If the goal is to maximize value quickly, the order should be:

1. polish the workshop draft and figures
2. add a small non-IID extension only if it stays clean
3. prepare a holdout-track or stronger-baseline follow-on
4. only later broaden to bigger methodological or systems contributions

## What Would Most Improve the Current Study

If only one thing is added before submission, the best candidate is:

- a **small, disciplined non-IID extension**

If only one thing is added after submission, the best candidate is:

- a **holdout-track expansion with the same core trio**

That sequence preserves the current clear story while giving you a credible path toward a stronger publication. 
