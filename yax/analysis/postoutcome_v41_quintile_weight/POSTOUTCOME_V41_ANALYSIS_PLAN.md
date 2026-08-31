# YAX V4.1 Quintile-Weight Analysis Plan

**Written after the design audit and before executing the V4.1 sensitivity.**

**Status label for every empirical output:**

> **POST-OUTCOME SUPPLEMENTARY QUINTILE-WEIGHT SENSITIVITY — NOT PART OF CONFIRMATORY YAX v1.1**

## Design-audit finding

`YAX_V41_QUINTILE_WEIGHT_DESIGN_AUDIT.md` classifies the frozen temporal
weighting instruction as **Verdict 3 — Freeze ambiguity**. The freeze specifies
employment-weighted quintiles on scenario support, but it does not say whether
the production weights must use the pre-period or the full static estimation
window.

## S1 — Required primary sensitivity

Re-estimate exactly one primary static model:

- Eloundou GPT-4 beta exposure;
- Rule A strict support;
- Webb software-patent computerization control;
- the same 468 occupations as the confirmatory primary model;
- the same occupation-by-age-by-month employment-stock outcome;
- ages 22–25 versus pooled ages 26–65;
- the same 108 static estimation months, excluding December 2022 and with the
  known October 2025 gap absent;
- the same January 2023–July 2026 post indicator;
- the same grouped-binomial quasi-likelihood/PPML score representation;
- the same occupation-by-age, occupation-by-month, and age-by-month fixed
  effects;
- the same occupation-cluster analytic standard error and 999-draw one-step
  Rademacher wild-score inference;
- the same seed as the historical primary coefficient.

Change only the occupation weights supplied to the AI-exposure quintile
builder. The supplementary classification uses young-plus-older employment
stocks from the available pre-period cells, January 2017 through November 2022.
No transition or post-period cell enters those classification weights.

The Webb standardization, model cells, exposure values, occupation support,
estimator, fixed effects, target coefficient, and inference remain as in the
historical primary execution. This isolates treatment-category classification
from other weighting uses in the estimator.

## S2 — Classification comparison

Before interpreting S1, compare the historical full-static-sample and the
pre-period-only classifications on the same 468 occupations. Report:

- the four weighted cut values and all five resulting bins;
- occupation counts and within-window weighted employment shares by bin;
- Q1 and Q5 Jaccard overlap;
- the number changing bin;
- movements into and out of Q1 and Q5;
- weighted exposure rank correlation, reported only as a descriptive check.

Ties follow the immutable production helper: stable sort, cumulative-weight
cuts at 20/40/60/80 percent using `searchsorted(..., side="left")`, and
`searchsorted(cuts, values, side="left") + 1`, so equal scores are not split.

## S3 — Conditional six-measure extension

After S1 and S2, the existing 444-occupation literal common-support comparison
may be repeated once with pre-period-only AI-quintile weights **only if** it is
computationally trivial using the V4 estimator and requires no new support,
window, estimator, control, or inference choice. The six measures, common
support hash, measure-specific seed discipline, and all other model components
must match V4. No alternative intersection may be searched.

## Decision rules

- **W1:** near-identical Q1/Q5 membership and substantively similar primary
  coefficient.
- **W2:** noticeable classification change, but a negative and economically
  similar primary coefficient.
- **W3:** negative sign survives but magnitude changes economically
  substantially.
- **W4:** sign changes or the headline conclusion substantially weakens; stop.

No new multiple-testing framework, timing search, event window, event-study
model, support definition, or mechanism analysis is authorized.

The categorical event study is not rerun unless S2 shows material Q1/Q5
membership change and S1 also shows material coefficient change. Under that
joint condition, work stops for owner review before any dynamic model is run.

