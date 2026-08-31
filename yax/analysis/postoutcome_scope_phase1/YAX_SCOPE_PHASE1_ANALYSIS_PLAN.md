# YAX Scope Expansion Phase 1 Analysis Plan

> **POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

This plan was written and committed before executing the one new outcome
regression authorized in Phase 1. The immutable `v1.1-design-freeze`,
`v1.1-confirmatory-results`, V4, and V4.1 states remain unchanged.

## Authorized work

Phase 1 authorizes exactly:

1. one flexible age-profile employment-stock model; and
2. a data-design feasibility audit of CPS longitudinal links.

No CPS flow treatment-effect regression is authorized. No BTOS/adoption,
PCA/factor, alpha/E2, wage/hours, education, gender, race, industry, or other
outcome extension is authorized.

## Age-profile outcome and sample

The outcome is the CPS survey-weighted employment stock in occupation \(o\),
age bin \(g\), and month \(t\), denoted \(Y_{ogt}\). The six and only six age
bins are:

- 18–21;
- 22–25;
- 26–30;
- 31–40;
- 41–50;
- 51–65.

The sample is January 2017 through July 2026, with the same absent March
2017–2021 basic-month cells and October 2025 gap as the existing YAX panel.
December 2022 is excluded from the static model. `Post` begins in January 2023.
Employment is `EMPSTAT` 10 or 12 and the cell weight is `WTFINL`. Raw Census
occupation codes through 2019 are routed to the Census-2018 basis through the
existing probabilistic 2010-to-2018 bridge; 2020-forward raw codes are already
on that basis.

The occupation universe is the immutable 468-occupation intersection of
Eloundou GPT-4 beta Rule-A strict support and finite Webb software-patent
exposure used by the V4/V4.1 primary model. An occupation is retained even if a
particular age bin has a zero cell in some months; the model conditions on the
occupation-month total across all six bins.

## Treatment and computerization construction

Eloundou beta quintiles are constructed once on the 468 occupations with the
immutable weighted-quintile algorithm: stable sort; cumulative cuts at
20/40/60/80 percent using left search; equal scores are not split. Weights are
the sum of employed CPS stocks for ages 22–65 from January 2017 through
November 2022. Ages 18–21 do not redefine the treatment classification; this
preserves the V4.1 primary population used to form occupational weights while
moving the weighting window fully before treatment. Q1 is omitted. The
implementation will report whether Q5 membership remains identical to the
historical full-static classification.

The Webb software-patent control is standardized using the same 468-occupation
full-static (108-month), ages-22–65 employment weights used by the historical
primary implementation. This preserves the existing control scaling while the
single declared treatment-classification change uses pre-period weights.
Because the model includes a separate Webb slope for every non-reference age
bin, any positive affine rescaling would leave the fitted AI-quintile
coefficients unchanged.

## Exact estimand and algebraically equivalent estimator

Let \(r=51\text{–}65\) be the reference age bin, \(Q_{oq}\) indicate beta
exposure quintile \(q\), and \(W_o\) be standardized Webb software exposure.
The conceptual PPML conditional mean is

\[
 E[Y_{ogt}\mid X]=\exp\left(
   \alpha_{og}+\delta_{ot}+\lambda_{gt}
   +\sum_{q=2}^{5}\beta_{gq}Q_{oq}Post_t
   +\theta_g W_oPost_t
 \right),
\]

with the interactions for the reference bin normalized to
\(\beta_{rq}=\theta_r=0\). Thus the model contains occupation×age-bin,
occupation×month, and age-bin×month fixed effects; age-specific Q2–Q5 post
gradients; and the analogous age-relative Webb control.

The implemented, algebraically equivalent parameterization conditions on the
occupation-month total \(N_{ot}=\sum_gY_{ogt}\). The resulting grouped
multinomial quasi-likelihood has, for every non-reference age bin,

\[
 \log\frac{p_{ogt}}{p_{ort}}
 =a_{og}+\ell_{gt}
 +\sum_{q=2}^{5}\beta_{gq}Q_{oq}Post_t
 +\theta_gW_oPost_t,
\]

where \(a_{og}=\alpha_{og}-\alpha_{or}\),
\(\ell_{gt}=\lambda_{gt}-\lambda_{rt}\), and conditioning eliminates
\(\delta_{ot}\). This is one jointly estimated saturated multi-age model, not
a collection of pairwise regressions.

For each non-reference age bin \(g\), the reported coefficient is
\(\beta_{g5}\). It answers: relative to ages 51–65, how much less (or more)
favorably did age-bin \(g\)'s employment-stock share evolve after January 2023
in beta Q5 rather than Q1, conditional on the other fixed effects and Webb?
The reference-bin coefficient is zero by normalization and has no separate SE,
CI, or p-value. The transformed interpretation is
\(100[\exp(\beta_{g5})-1]\) percent.

The original confirmatory coefficient for ages 22–25 versus pooled ages 26–65
is a different estimand. It may appear only as a separately labeled benchmark
marker and will not be treated as a coefficient from this model.

## Estimation and inference

The grouped multinomial log-likelihood is maximized jointly with analytic
scores. Identification uses ages 51–65 as the reference and drops one month
effect per non-reference age equation. The implementation must verify
convergence, finite fitted probabilities, the fixed 468-occupation support,
the expected static-month set, and first-order conditions before reporting.

Inference clusters by Census-2018 occupation. Analytic cluster-robust standard
errors use the inverse profiled information matrix after removing the
occupation×age and age×month nuisance parameters. One-step wild-score
inference uses 999 common occupation-cluster Rademacher multipliers, seed
`20260901`, and the analytic cluster SE as the fixed studentizer, matching the
existing YAX architecture where applicable. For each \(\beta_{g5}\), the
two-sided p-value uses the finite-draw correction and the pointwise 95 percent
CI uses the higher empirical 95th percentile of the absolute studentized
one-step draws. These are pointwise exploratory intervals, not simultaneous
bands.

## Frozen interpretation questions and classification

The result will answer, without searching alternative bins:

1. whether ages 22–25 are uniquely negative relative to older workers;
2. whether the absolute coefficients attenuate monotonically or approximately
   monotonically from 22–25 through 31–40;
3. whether ages 18–21 resemble ages 22–25, with schooling and labor-force
   transitions stated as interpretive cautions; and
4. whether the negative pattern extends materially to ages 26–30.

Classification is limited to the prompt's four states:

- **AGE-A:** 22–25 is clearly among the most negative groups and attenuation
  occurs with age/experience;
- **AGE-B:** 22–25 and 26–30 are similarly negative, with later attenuation;
- **AGE-C:** no meaningful age gradient; or
- **AGE-D:** 22–25 is not negative or older groups dominate strongly.

The profile is descriptive heterogeneity. It cannot by itself identify junior
substitution, hiring, tacit experience, firm-specific capital, or task
assignment mechanisms.

## CPS longitudinal feasibility audit

The feasibility audit will read the actual extract metadata and microdata. It
will prefer validated `CPSIDV` links and separately describe `CPSIDP`, `CPSID`,
`SERIAL`, and `MISH`. Adjacent-month transitions are the prospective primary
structure; MISH 4-to-5 returns after the rotation gap will be counted
separately and never pooled with one-month transitions.

All flow sample counts and match rates are diagnostics, not exposure-effect
estimates. Age is classified at the origin interview. Employment occupation is
defined only for respondents employed in that interview; a most-recent
occupation reported while nonemployed will not be treated as a current origin
occupation. Pre-2020 exposure-quintile diagnostics may use a documented
deterministic modal route through the existing probabilistic Census bridge,
solely to count feasibility support; no treatment regression will use that
shortcut.

The audit will explicitly determine whether an official longitudinal weight is
present, quantify linked-versus-unlinked observable selection, diagnose coding
reversals and the 2019/2020 taxonomy boundary, and classify feasibility as
FLOW-A, B, C, or D. It will then write—but not execute—the exact future flow
estimands.

## Integrity rule

The reproducibility receipt will list every new outcome regression executed.
That list must contain only this pre-declared age-profile model.

