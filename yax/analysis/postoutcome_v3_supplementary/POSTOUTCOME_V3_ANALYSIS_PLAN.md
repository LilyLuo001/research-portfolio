# YAX V3 Post-Outcome Supplementary Analysis Plan

> **POST-OUTCOME SUPPLEMENTARY ANALYSIS — NOT PART OF CONFIRMATORY YAX v1.1**

Written before executing any V3 supplementary model. The immutable design and
confirmatory tags remain `v1.1-design-freeze` and
`v1.1-confirmatory-results`. Nothing in this directory may be added to or used
to overwrite the 195-row confirmatory result ledger.

## Fixed inputs and implementation boundary

All outcome-bearing analyses use the already authenticated CPS extract,
pre-period cells, Census occupation bridge, Rule-A exposure lookup, and
computerization file recorded in `yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json`.
They reproduce the same cell construction, month exclusions, grouped-binomial
conditional equivalent of the PPML estimator, fixed-effect absorption, and
occupation-cluster one-step wild-score machinery implemented in
`yax/analysis/run_frozen_v11.py`. The confirmatory code and outputs are read
only.

Static analyses omit December 2022 and the absent October 2025 observation.
The event study retains December 2022 and keeps October 2022 as the reference
month. All supplementary randomization procedures use 999 Rademacher draws and
fixed seeds declared below. Failed model fits are fatal; they are not replaced
or selectively discarded.

## S1. Headline Q5-Q1 PPML information support

### Exact estimators

Run the 12 already pre-specified headline architectures only:

- AI exposure: Eloundou alpha or beta;
- coverage: Rule A, B, or C;
- computerization: Webb software-patent exposure or O*NET computer-use
  importance;
- measure-specific employment-weighted quintiles, Q1 omitted and Q2-Q5 entered
  separately;
- occupation-by-age, occupation-by-month, and age-by-month fixed effects;
- the actual static estimation sample.

No coefficient is selected or substituted. Outcome coefficients are used only
to recover fitted information weights for this referee-requested diagnostic.

### Headline-estimator information formula

Let `R` be the slope-regressor matrix after the exact fitted PPML information
weighted absorption of the fixed effects, and let

`W_i = N_i p_hat_i (1 - p_hat_i)`.

For target column `t` (Q5 x Post), residualize `R_t` on every other absorbed
slope column under `W`:

`z = R_t - R_-t (R_-t' W R_-t)^(-1) R_-t' W R_t`.

For occupation `o`, define conditional information

`H_o = sum_(i in o) W_i z_i^2`,

share `h_o = H_o / sum_j H_j`, and effective headline support

`N_eff,headline = 1 / sum_o h_o^2`.

The top-five share is the sum of the five largest `h_o`. This is the
occupation decomposition of the target coefficient's conditional expected
information (equivalently the relevant Schur complement of the absorbed slope
information matrix) at the fitted model. It is not conventional leverage, an
outcome influence function, or a decomposition of the coefficient estimate.

The implementation must verify numerically that `sum_o H_o` equals both the
weighted residual sum of squares `z'Wz` and the inverse of the target diagonal
of the absorbed slope-information inverse, within stated floating-point
tolerance.

### Bridge to continuous residual-treatment support

For each of the four Rule-A alpha/beta-by-Webb/O*NET architectures, reconstruct
the pre-outcome continuous diagnostic exactly as

`s_o = w_o X_tilde_o^2 / sum_j w_j X_tilde_j^2`,

using January 2017-November 2022 employment-stock weights. Validate its
effective count and top-five share against the stored pre-outcome Test-B row.
Compare continuous shares with headline information shares on common occupation
support using:

- both effective counts and top-five shares;
- the named top five under each diagnostic;
- top-five Jaccard overlap;
- Spearman rank correlation of occupation shares.

The interpretation follows the realized comparison; alignment is not assumed.

## S2. Test-A validator-source split

Use only the existing 348-occupation complete-support Test-A file and its
existing pre-period weights. No new covariate or data source is introduced.

The source taxonomy is fixed before calculation:

- **construction-linked/same-source O*NET variables:** cognitive ability
  importance, manual/physical ability importance, required-education category,
  and O*NET computer-use importance. Cognitive ability is directly linked to
  AIOE construction; the other three are not AIOE inputs but share the O*NET
  occupational information system and are therefore kept in the conservative
  same-source group.
- **more external validators:** Autor-Dorn RTI, OEWS log mean annual wage,
  Dingel-Neiman teleworkability, and OEWS-based STEM major-group share.

For each of the six AI measures, estimate two employment-weighted OLS
projections of the standardized exposure, each with an intercept: one on all
four standardized construction-linked variables and one on all four
standardized external validators. Report weighted R-squared, residual SD,
inverse-Herfindahl effective residual support, top-five residual-variance share,
and named top contributors. Report all measures and both validator groups.

## S3. CPS survey-uncertainty feasibility audit

Before any resampling, inspect only the authenticated microdata schema, extract
specification, and IPUMS metadata already stored with the project. Record which
person, household, rotation-panel, strata, PSU, and replicate-weight identifiers
are actually available. A microdata resampling exercise is permitted only if
those fields support a documented CPS-design-consistent procedure that retains
the exact cell-stock estimand. No ad hoc person bootstrap, occupation bootstrap
relabelled as survey inference, or invented PSU/stratum structure is allowed.

If the required survey-design information is unavailable, execute no survey
resampling and document that confirmatory occupation-cluster intervals are
conditional on the realized weighted stocks. This feasibility audit does not
change the confirmatory inference.

## S4. One remotability-heterogeneity model

Run exactly one model:

- Rule-A Eloundou beta, Webb software-patent exposure, and Dingel-Neiman
  occupation-level remotability on their common static support;
- standardize all three continuous occupation variables with actual
  employment-stock weights on that fixed support;
- regressors are `AI_z x Post`, `Webb_z x Post`, `Remote_z x Post`, and
  `(AI_z x Remote_z) x Post`, in that order;
- the same saturated fixed effects as the confirmatory static model;
- target: the fourth coefficient, interpreted as heterogeneity in the
  young-relative AI gradient per one-SD increase in occupational remotability;
- occupation-cluster one-step wild-score inference with 999 Rademacher draws,
  seed `20260830 + 11000`.

This is occupational heterogeneity, not realized individual telework and not a
causal mechanism test. No alternative cuts, scales, or interaction forms will
be run in this round.

## S5. One joint pretrend test and simultaneous pre-period bands

Use the exact primary Rule-A beta-by-Webb continuous event-study model, full
existing event window, and October 2022 reference month. The tested vector is
all 65 non-reference AI-exposure-by-young coefficients dated before December
2022.

The single omnibus statistic is

`T_obs = max_k |beta_hat_k / analytic_SE_k|`.

Using the same occupation-cluster linearized wild-score architecture as the
confirmatory event study, draw 999 common Rademacher occupation multipliers
with seed `20260830 + 12000`. For each draw compute

`T_b = max_k |shift_bk / analytic_SE_k|`.

The finite-sample corrected p-value is

`(1 + sum_b 1[T_b >= T_obs]) / 1000`.

The 95% quantile of `T_b` (higher interpolation) also forms simultaneous
pre-period bands `beta_hat_k +/- critical * analytic_SE_k`. This is a
referee-requested post-outcome timing diagnostic; it does not turn the original
pointwise event study into confirmatory joint inference.

## S6. Timing windows

No new alternative post window will be estimated. The already-confirmatory
2023-2024 versus 2025-2026 split and its joint p-value address the stated
late-sample concern without specification search.

## Scale correction (documentation only)

The frozen paired-precision artifact defines
`MDE_Delta,80 = 0.0327215699` on the Q5-Q1 **log-coefficient-difference scale**.
Its exponential relative-magnitude translation is
`100 * (exp(0.0327215699) - 1) = 3.3262808%`.
It is not an additive 3.27-percentage-point estimand. The realized paired
coefficient difference and its confidence interval will remain on the log
scale in V3; the frozen artifact itself is not edited.
