# INF-03 and INF-05 analysis specification

Status: **post-outcome exploratory; written after the March replacement audit
and before the INF-03/INF-05 results were produced**

The March gate in `results/march_replacement_audit/` must pass before this
module reads outcomes.  The module uses the fully rebuilt corrected-treatment
contract (468 occupations; treatment weights and labels built only from the 71
pre-period months) and the corrected 113-month static calendar.  December 2022
is excluded; October 2025 is absent and is not interpolated.

## INF-03: CPSID-linked household multiplier sensitivity

### Target and limits

The extract contains no public stratum, PSU, or replicate-weight variables.
Consequently this exercise is **not CPS design-based inference**.  It is a
sampling-oriented sensitivity that treats observed, longitudinally linked
`CPSID` household records as independent multiplier units, conditional on the
released final person weights and their calibration.  It captures repeated
appearances of the same linked household and co-resident dependence, but omits
dependence between households in common unavailable PSUs, the multistage
sample design, and uncertainty from nonresponse and population-control
calibration.

Each of 199 draws uses an independent mean-one exponential multiplier for
every positive `CPSID`.  One household receives the same multiplier in all
months.  Every fractional 2010-to-2018 crosswalk descendant of a source record
inherits exactly the source household's multiplier.  `SERIAL` is not used as
the longitudinal unit because it is unique only within year and month; `MISH`
categories are not treated as independent PSUs.

For every draw the microdata contributions are reaggregated into young and
older occupation-month stocks and both the corrected baseline and the
SOC2-by-young-by-post model are fully refit.  Common household draws preserve
the covariance of their paired movement.

Two classification targets are reported:

1. **fixed corrected labels:** the 468-occupation support, beta quintiles, and
   Webb normalization are held at the audited corrected-preperiod contract;
2. **rebuilt labels:** support is held fixed, but pre-period employment weights,
   employment-weighted quintile cuts/memberships, and Webb normalization are
   reconstructed in every positive-weight draw.

The first isolates outcome-cell sampling conditional on the reported
treatment definition.  The second also propagates the sampling sensitivity of
data-derived weighting and classification.  Positive multipliers preserve the
observed support; this exercise does not target uncertainty about the finite
exposure lookup itself.

Sampling-oriented standard errors are the standard deviation of full-refit
coefficient shifts.  Basic 95-percent intervals invert the empirical 2.5 and
97.5 percent shift quantiles.  These intervals are reported separately and are
never mechanically added to occupation-cluster uncertainty.

Seed: `2026090551`.  Draw count: 199.

Every full refit has a fixed 100-iteration ceiling.  Nonconvergence is retained
and reported rather than hidden or allowed to consume an unbounded compute
budget.

## INF-05: sparse-cell, broad-family full-refit simulation

This is a calibrated stress test of the grouped-binomial estimator and its
occupation-cluster normal interval, not a model of the full CPS sample design.
It uses the observed 468-by-113 support, corrected fixed treatment labels,
actual weighted occupation-month totals, and the fitted nuisance index.

### Sparse-cell sampling layer

For each occupation-month, a Kish effective record count is constructed from
the routed person weights,

\[
n^{\mathrm{eff}}_{ot}=(\sum_i w_{iot})^2/\sum_i w_{iot}^2.
\]

The count is rounded to the nearest positive integer.  Conditional on a DGP
probability, a binomial draw at this count is converted back to a young stock
by multiplying the simulated share by the observed weighted total.  This
preserves outcome bounds and the actual heterogeneity in weighted totals while
making the approximation for unequal survey weights explicit.  Fractional
crosswalk descendants enter both weight moments under their declared route
weights.

### Broad-family shock layer

The observed baseline score residual is aggregated to SOC2-family by month and
divided by fitted information.  That family-month logit disturbance is
weighted-residualized against family and month effects.  In every simulation a
single Rademacher sign multiplies each family's complete 113-month residual
path, preserving its time pattern and creating common shocks across detailed
occupations in that family.  It is then added to the fitted nuisance logit and
the declared target effect.  This outcome-calibrated residual layer is a
stress scenario, not an independently identified structural DGP.

The true Q5-by-post effects are `0`, `-0.05`, and the observed corrected
baseline checkpoint `-0.132109...`.  Each uses 199 full refits of both the
baseline and SOC2-post models.  The outputs report convergence failures, bias,
empirical dispersion, mean reported occupation-cluster SE, two-sided 5-percent
null rejection, 95-percent normal-interval coverage, and binomial Monte Carlo
standard errors.  Actual target-information concentration and the effective
count distribution document how the stress test represents concentrated
influence and sparse cells.

Seed family: `2026090561 + replicate`; draws per effect: 199.

The same 100-iteration ceiling applies to the simulation.  Coverage and
rejection summaries state their successful-refit denominator; a nontrivial
failure rate is itself an adverse finite-sample finding.

## Fail-closed rules

The runner stops before either exercise unless:

- the March audit is `PASS_FUNCTIONAL_REPLACEMENT`;
- both private input hashes match the audit receipt;
- all active records have a positive `CPSID`;
- explicitly excluding the zero-weight ASEC March rows and inserting the Basic
  rows produces exactly 113 model months;
- source-route mass and fractional descendants are constructed before
  household multipliers are applied;
- the unperturbed refit reproduces the fully rebuilt corrected coefficient to
  numerical tolerance; and
- no individual identifier is serialized.
