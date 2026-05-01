# ICML Structured FM Workshop Paper Outline

## Working Title

**Federated TabPFN for Small Numerical Tabular Classification: An IID Benchmark on the OpenML CC18 Slice**

Alternative title:

**How Does Federated TabPFN Compare to Strong Tabular Baselines? A Flower-Only Benchmark in the Original TabPFN Regime**

## Core Claim

In the original small-numerical tabular regime, `federated TabPFN` is usually the strongest model under a Flower-only IID setup, outperforming strong classical baselines on most datasets while trading off additional runtime.

## Target Shape

- venue: **ICML 2026 Workshop on Foundation Models for Structured Data**
- format: short workshop paper
- emphasis:
  - benchmark evidence
  - structured/tabular foundation-model relevance
  - clean, scoped experimental claim

## Recommended Section Structure

### 1. Introduction

Goal:

- motivate why structured/tabular foundation models should also be evaluated in federated settings
- make the paper narrow and practical from the start

Key points:

- tabular learning remains important in real-world privacy-sensitive applications
- TabPFN is a strong foundation-model-style baseline for tabular classification
- federated evaluation of this model family is currently underexplored
- this paper asks a focused question rather than proposing a new training algorithm

Suggested ending paragraph:

> We study whether TabPFN remains competitive in a federated, Flower-only setup on the original small-numerical OpenML CC18 slice associated with prior TabPFN evaluation. Across 18 datasets, federated TabPFN achieves the strongest average performance and wins on most datasets, while introducing a clear runtime tradeoff relative to classical baselines.

### 2. Related Context

Keep this short.

Subtopics:

- federated learning for tabular classification
- strong classical tabular baselines
- tabular foundation models / TabPFN
- why federated evaluation matters

Important positioning:

- this is not a broad survey
- this is not a new federated optimization algorithm
- this is a benchmark-style empirical paper

### 3. Experimental Setup

This section should be very clear and compact.

Include:

- framework:
  - Flower-only local federated setup
- datasets:
  - the locked `18`-dataset OpenML CC18 small-numerical no-missing slice
- baselines:
  - `random_forest`
  - `xgboost`
  - `tabpfn`
- split regime:
  - `iid`
- clients:
  - `2`
- rounds:
  - `1` for serialized ensemble baselines
  - `2` where applicable for engineering-style boosted path
- metrics:
  - accuracy
  - eval loss
  - runtime

Important wording:

- describe the federated execution honestly
- avoid implying a novel federated training algorithm if the contribution is really benchmark evidence

### 4. Main Results

This is the heart of the paper.

Primary table:

- one row per dataset
- columns:
  - `random_forest`
  - `xgboost`
  - `tabpfn`
- highlight the best accuracy per row

Primary summary bullets:

- `tabpfn` wins `14/18`
- highest mean accuracy: `0.8897`
- best mean eval loss: `0.2453`
- strongest classical baseline is `random_forest`

Suggested subsections:

- **Overall comparison**
- **Where TabPFN wins clearly**
- **Where TabPFN loses narrowly**

### 5. Runtime and Tradeoffs

This should be a short but honest discussion.

Key points:

- `tabpfn` is the slowest model on average
- `random_forest` is materially faster and still strong
- the predictive advantage of `tabpfn` appears meaningful enough to justify the runtime cost in this benchmark setting

This section is important because it makes the paper sound serious rather than promotional.

### 6. Limitations

Keep this explicit.

Include:

- IID-only in the current workshop submission
- limited to the small-numerical CC18 slice
- no algorithmic novelty claim
- execution setup is benchmark-oriented rather than a production federated deployment study

### 7. Conclusion

Recommended conclusion shape:

- restate the narrow question
- summarize the result
- note that federated evaluation of tabular foundation models looks promising
- point to non-IID and broader structured-data extensions as future work

## Figures / Tables Recommendation

Minimal paper artifact set:

1. **Main results table**
   - all 18 datasets
   - all 3 baselines

2. **Win-count or average-performance summary figure**
   - simple and compact

3. **Runtime comparison figure**
   - bar chart or dot plot

Optional:

4. **Focused case-study table**
   - highlight 4-6 datasets where TabPFN wins most clearly or loses narrowly

## Most Useful Datasets to Highlight

Strong positive examples:

- `steel-plates-fault`
- `balance-scale`
- `vehicle`
- `mfeat-fourier`
- `mfeat-zernike`

Useful “near-loss” examples:

- `pc4`
- `pc3`
- `kc2`
- `pc1`

This mix helps show both strength and nuance.

## Writing Guidance

Tone:

- academic
- empirical
- restrained
- not hype-driven

Avoid:

- overstating “foundation model” implications
- implying generalized superiority beyond the tested slice
- presenting `xgboost` as more competitive than the results support

Prefer:

- precise empirical language
- honest runtime discussion
- a narrow benchmark contribution framing

## Immediate Next Writing Tasks

1. Draft the abstract.
2. Draft the introduction using the narrow benchmark framing.
3. Produce the main results table from the completed artifacts.
4. Add one compact runtime comparison figure.
5. Draft limitations early so the paper stays disciplined.
