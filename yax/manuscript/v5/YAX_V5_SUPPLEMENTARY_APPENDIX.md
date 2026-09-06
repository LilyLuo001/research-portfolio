# Online Appendix: Measurement Architecture and Statement-Specific Robustness

Lily Luo — September 2026

> Phase 3 materials are **POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**.

## A. Immutable confirmatory record

The protected design-freeze tag peels to `22fbf7924809b7a535e31ae0ab68f5b113ce8078`; the protected confirmatory-results tag peels to `b16109482c3bf5ca176f6f08976e120b04769945`. Their raw `rev-parse` values are annotated-tag object hashes, not moved commit references. V4.1 remains fixed at `ca5a02478b68f1a0e47eadd4e8816bbc96c9dcc3`.

Confirmatory YAX v1.1 includes the pre-specified alpha/beta measurement architectures, stock models, paired-difference inference, mapping and coverage rules, and associated gates. Outcome-dependent estimator-support work, common-support six-measure comparisons, event-study refinements, Phase 2 flows, Phase 2.5 reallocation, and Phase 3 are supplementary post-outcome analyses.

## B. Exposure construction, harmonization, and support

Complete construction lineage, source hashes, SOC crosswalks, coverage diagnostics, and Rule-A/Rule-B decisions remain in the frozen analysis directories. The exact-code/repaired-score/expanded-support/minus-computer-math decomposition separates score correction from sample composition. The literal common support contains 444 occupations and represents 83.14% of employment in the frozen stock comparison.

Residual-treatment support and conditional-information support answer different questions. The first decomposes weighted residual exposure after continuous computerization controls. The second decomposes the fitted PPML information for the categorical Q5-versus-Q1 coefficient. Neither is a leave-one-out influence measure.

## C. Confirmatory employment-stock results

The primary strict-support beta-by-Webb coefficient is -0.1311 with a cluster SE of 0.0444 and one-step wild-score interval [-0.2170, -0.0451]. Across the 12 alpha/beta headline architectures, coefficients range from -0.0971 to -0.2085. The paired beta-minus-alpha difference is -0.0324 with interval [-0.1023, 0.0376]. A CI containing zero means the design does not detect a difference; it does not establish economic equivalence. The frozen paired design had 80% power to detect about 0.0327 log points.

## D. Literal common-support comparison and joint inference

All six common-support point estimates are negative. Phase 3 reconstructs those exact estimates and uses 999 common occupation-cluster multiplier draws (seed 2026090304) to preserve covariance. The simultaneous one-sided critical value is 2.26036. The administrative-equal AIOE upper bound is +0.01858; the other five upper bounds are negative. Under the frozen criterion, the joint all-six-negative statement is not supported.

The intersection-union marginal p-value is .045. It is reported but does not supersede the declared simultaneous-bound rule. No common-parameter restriction, model averaging, or “true AI effect” interval is imposed.

## E. Shared and architecture-specific exposure components

For occupation o, the frozen construction is:

\[
A_o=(X_{A1,o}+X_{A2,o}+X_{A3,o})/3,
\quad
E_o=(X_{E1,o}+X_{E2,o}+X_{E3,o})/3,
\]

\[
F_o=(A_o+E_o)/2,
\quad
G_o=(A_o-E_o)/2.
\]

Inputs are standardized under the frozen employment weighting. F's orientation is mechanical. F is a shared statistical component; G is a family-disagreement component. Neither is a causal factor. The PCA/factor implementation is descriptive robustness only and does not replace the centroid construction.

## F. Reallocation component decomposition

The primary diagnostic uses 108,500 realized switches and retains all official weight on the six-way support. Weighted cut points for absolute delta F are 0.17855, 0.39019, 0.71236, and 1.21427. Conflict rates by ascending quintile are 94.59%, 65.96%, 52.67%, 34.06%, and 19.06%. On 39,893 persistent switches they are 94.94%, 66.88%, 53.51%, 34.07%, and 19.01%.

Among primary conflict transitions, median absolute delta F is 0.28356, median absolute delta G is 0.29493, and median architecture-specific displacement H is 0.48293. For unanimous transitions the corresponding medians are 0.93247, 0.18710, and 0.34430. The conflict-to-unanimous median-H ratio is 1.40262. These fixed diagnostics yield SC-R1.

## G. Hard reallocation benchmark

The primary hard benchmark stratifies by age group, calendar month, origin broad occupational family, and destination broad occupational family. It preserves observed weighted detailed origin and destination marginals within those strata, Hamilton-expands to 200,000 pseudo-units, repairs false self-switches under the frozen rule, and uses 999 draws with seed 2026090301.

The benchmark covers 98.305% of official switch weight, 30,170 strata, and 84,192 detailed joint cells. Realized conflict is 0.532828; the hard mean is 0.523227; its 2.5th and 97.5th percentiles are 0.522140 and 0.524275. The gap is 0.009601, below the 0.0100 meaningful-gap threshold, yielding HB-C. Zero false self-switches remain.

The persistent sensitivity uses seed 2026090302, represents 99.920% of official weight, and yields realized 0.544623, mean 0.535798, and gap 0.008826. It also yields HB-C. The empirical upper-tail areas are descriptive properties of constrained rematching, not conventional p-values.

## H. Shared-component stock model

Exactly one new Phase 3 labor-outcome regression was run. It uses F-weighted quintiles on the 444-occupation literal support, Q1 omitted and Q2–Q5 entered separately, the frozen static post and transition month, the existing PPML fixed effects, Webb interaction, occupation clustering, and one-step wild-score inference.

The Q5-versus-Q1 coefficient is -0.128536, analytic cluster SE 0.046975, wild-score p = .005, and interval [-0.218487, -0.038585]. The transformed contrast is -12.062%. Q1 contains 117 occupations; Q5 contains 95. The result yields SC-A. No continuous-F, G, alternate-cutoff, residual-treatment, or alternative-factor outcome model was estimated.

## I. Flow mechanism results

The official-longitudinal-weight beta flow coefficients and intervals are:

| Margin | Coefficient | 95% interval | p-value |
|---|---:|---:|---:|
| Employment exit | 0.1195 | [-0.0668, 0.3059] | .229 |
| Occupational outflow | 0.0107 | [-0.1063, 0.1277] | .857 |
| Entry destination | -0.0888 | [-0.2787, 0.1011] | .383 |

All intervals include zero; the flow mechanism remains unresolved. The unweighted exit sensitivity excludes zero while official and ordinary cross-sectional weighting do not, reinforcing the decision not to claim a mechanism. Stage 2B and the six-architecture flow grid were not run.

## J. Computerization, remotability, and timing

The complete comparison-technology table reports Webb, two O\*NET computer-use measures, RTI, and Frey-Osborne. The more-than-twofold beta range is interpreted as estimand dependence, not a menu from which to select a preferred effect. Remotability results do not absorb the beta gradient but do not rule out remote-work mechanisms. The categorical pretrend joint test detects no differential Q5-versus-Q1 pretrend, while the post path is non-immediate and non-monotone.

## K. Reproducibility and stopping rule

Phase 3 numerical outputs were generated from pre-result commit `2683af26768c343af6060988689728d88878d568`. Two bracket-access implementation defects and one headless plotting-backend defect are recorded in the permanent implementation-fix ledger; none changes an estimand or numerical result. All seeds, inputs, artifact hashes, classifications, and tests appear in `YAX_PHASE3_REPRODUCIBILITY_RECEIPT.json`.

The binding path is PATH-P3-C because HB-C weakens the benchmark-based economic-relevance interpretation. V5 is the final authorized manuscript assembly. No Phase 4 empirical search follows.
