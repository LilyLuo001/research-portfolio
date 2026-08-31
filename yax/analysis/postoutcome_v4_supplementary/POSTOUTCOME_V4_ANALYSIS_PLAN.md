# YAX V4 estimand-alignment analysis plan

> **POST-OUTCOME SUPPLEMENTARY ANALYSIS — NOT PART OF CONFIRMATORY YAX v1.1**

Declared before executing any V4 outcome-bearing analysis. The immutable design and confirmatory tags remain `v1.1-design-freeze` and `v1.1-confirmatory-results`. This plan authorizes only the Table 5B support audit, the single literal-intersection comparison triggered by that audit, and the categorical event-study alignment requested in the V4 handoff.

## Declaration boundary

- Parent manuscript commit: `679f4a2d482a8475697feb0776b87643412148b1`.
- Declaration commit: `b775621bb6aa8c459f1de54c981a861bf6979148`.
- No V4 result may be appended to the 195-row confirmatory ledger.
- Every machine-readable V4 output must carry the status string shown above.
- No alternative support intersection, reference month, event window, treatment date, post window, mechanism, control, or inference method may be searched.

## S1. Table 5B native-support audit

For each of the six Rule-A/Webb exposure models already reported in confirmatory Table 5B, reconstruct the exact occupation set used by the frozen estimator:

1. begin with the authenticated frozen occupation universe;
2. retain finite Rule-A exposure for that measure;
3. retain finite Webb software-patent exposure;
4. apply no additional support rule.

For each sorted occupation-code set, compute SHA-256 over UTF-8 newline-delimited codes with a terminal newline. Report occupation count, literal codes, support hash, and model-period employment coverage. Employment coverage is the retained share of the January 2017–July 2026 young-plus-older weighted stock over the 108 static estimation months; December 2022 is excluded exactly as in the frozen static estimator.

The confirmatory artifact already shows unequal counts (495, 484, 485, 468, 468, 468), so the six sets are not literally identical. This mechanically triggers S2; no judgment after seeing outcome estimates is involved.

## S2. One literal six-way common-support comparison

Use the exact six-way intersection of occupations scored by all six exposure measures under Rule A and with finite Webb exposure. Hold fixed:

- the identical sorted occupation set and its hash;
- occupation-by-age employment-stock outcome;
- ages 22–25 versus pooled ages 26–65;
- January 2017–July 2026 static estimation months, excluding December 2022;
- January 2023 post start;
- Q1 omitted and Q2–Q5 entered separately;
- Webb standardized continuous young-by-post comparison term;
- occupation-by-age, occupation-by-month, and age-by-month fixed-effect structure represented by the frozen grouped-binomial quasi-likelihood score;
- one-step occupation-cluster Rademacher wild-score inference with 999 draws and the frozen seed convention.

Each exposure measure may define its own employment-weighted Q1–Q5 ranking within the identical support. To match the existing headline estimator literally, quintile weights are the young-plus-older weighted stocks over the 108 static estimation months. This is a model-period weighting rule fixed by the frozen implementation; it is not relabelled as a pre-period weighting rule.

Report the six Q5–Q1 coefficients, analytic occupation-cluster SE, one-step wild-score CI and p-value, measure-specific Q5 membership, common occupation count, common employment coverage, and common support hash. Run exactly once.

Stop before manuscript polishing if the literal-intersection result materially overturns sign robustness.

## S3. Categorical headline Q5–Q1 event study

Use Eloundou beta, Rule A, Webb, and the exact primary static-model occupation support and Q1–Q5 classification. The classification is constructed once from the primary static model's 108 estimation-month employment weights and then reused unchanged in the dynamic model.

For every observed month except the omitted October 2022 reference month, include:

\[
\sum_{q=2}^{5}\beta_{q,\tau}
\left[1\{Q_o=q\}\times Young_a\times1\{t=\tau\}\right].
\]

Q1 is omitted. Q2–Q4 enter month by month but are not the plotted target. Webb enters as one standardized continuous Webb-by-young-by-month interaction for every non-reference month, matching the comparison-technology treatment in the legacy continuous event study. The Webb standardization uses the same full event-panel occupation weights as the legacy dynamic implementation. All occupation-by-age, occupation-by-month, and age-by-month fixed effects are handled through the same frozen grouped-binomial quasi-likelihood score architecture.

Use all observed January 2017–July 2026 months, preserve the October 2022 reference, retain December 2022 as the transition month, and make no window change. The plotted series is beta-Q5 relative to Q1.

For each coefficient, use the analytic occupation-cluster SE and a 999-draw one-step wild-score pointwise interval under a fixed V4 seed. For the 65 non-reference Q5 coefficients before December 2022, use the same 999 common occupation-cluster multipliers to compute a maximum-absolute-analytic-t joint test and simultaneous 95% bands. Report observed max-|t|, p-value, critical value, and number of simultaneous intervals excluding zero.

Stop before manuscript polishing if the categorical Q5–Q1 event study shows substantial pre-treatment divergence inconsistent with the paper's descriptive identification story. Do not change the reference month, event window, or treatment definition in response.

## S4. No additional empirical analysis

The continuous event study and all V3 supplementary analyses remain unchanged. No additional timing, mechanism, remote-work, computerization, sample, or inferential analysis is authorized in V4.
