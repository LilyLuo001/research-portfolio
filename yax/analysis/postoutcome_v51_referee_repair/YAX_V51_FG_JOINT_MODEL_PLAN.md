# YAX V5.1 joint F+G stock-model plan

**POST-OUTCOME EXPLORATORY. WRITTEN AND COMMITTED BEFORE THE RESULT IS EXECUTED.**

Exactly one new labor-outcome specification is authorized.

## Frozen construction

On the frozen 463-occupation pre-period reference support, standardize each of the six exposure scores using its recorded `preperiod_employment_weight` mean and standard deviation. Let `A_o` be the equal-weight centroid of the three standardized AIOE measures and `E_o` the equal-weight centroid of the three standardized Eloundou measures. Define

\[
F_o=(A_o+E_o)/2,\qquad G_o=(A_o-E_o)/2.
\]

`F` is the **family-balanced consensus component**. `G` is the **between-family disagreement component**. G captures only the AIOE-versus-Eloundou family-centroid dimension; it does not represent all architecture-specific disagreement.

The model uses the frozen literal six-measure common support: exactly 444 Census-2018 occupations with support hash `1e184b27678b7978d4b15e618db5b44f44b5e9ec1b50b69b53093ec62e0ce462`. Within that fixed support, F, G, and Webb software exposure are each standardized once using young-plus-older employment stocks over the 108 static estimation months. This is the same model-period weighting convention as the authoritative common-support stock comparison. No second scaling or alternative family weight is allowed.

## Exact equation

For occupation `o`, age group `a`, and calendar month `t`, estimate

\[
E[N_{oat}\mid\mathcal X]=\exp\{\gamma_{oa}+\delta_{ot}+\lambda_{at}
+[\beta_F\widetilde F_o+\beta_G\widetilde G_o+\theta\widetilde W_o]
\,Young_a\,Post_t\},
\]

where `N_oat` is the CPS survey-weighted employment stock, `Young_a=1` for ages 22–25 and zero for pooled ages 26–65, `Post_t=1` from January 2023 through July 2026, December 2022 is excluded, October 2025 is absent from the source series, `W_o` is Webb software exposure, and tildes denote the single model-support employment-weighted standardization just described. The fixed effects are occupation-by-age (`gamma_oa`), occupation-by-month (`delta_ot`), and age-by-month (`lambda_at`).

With two age groups, implementation uses the frozen grouped-binomial conditional equivalent of this PPML model. It conditions on each occupation-month total and absorbs occupation and month effects in the young share. The three implemented slope columns are, in fixed order:

1. `F_z × Post`;
2. `G_z × Post`;
3. `Webb_z × Post`.

These are algebraically the `Young × Post` triple interactions in the PPML representation. The cell outcome is not additionally weighted; CPS person weights already form `N_oat`.

## Inference

Use the existing occupation-cluster one-step Rademacher wild-score algorithm with 999 common multiplier draws and fixed seed `2026090501`. For each coefficient, studentize with its analytic occupation-cluster standard error and form the two-sided 95% interval from the 95th percentile of the absolute centered shift statistic. Report the centered bootstrap covariance between beta_F and beta_G. Also report one predeclared joint max-absolute-t test of `H0: beta_F=beta_G=0`; this is descriptive supporting inference and does not select either coefficient.

## Interpretation

If G's interval includes zero: “Conditional on the consensus dimension, the between-family disagreement dimension has no precisely detected incremental stock association.” This does not mean G is zero, architecture disagreement is irrelevant, or the measures are equivalent.

If G's interval excludes zero, report its sign and magnitude without opening a follow-up. If F changes materially relative to the existing F-only tail model, report that directly; the continuous F+G coefficient is not numerically commensurate with the prior F Q5-versus-Q1 coefficient.

No F/G rotation, alternate standardization, nonlinear interaction, alternate support, alternate age group, alternate post period, extra control, F-only variant, G-only variant, or architecture-residual stock regression is permitted.
