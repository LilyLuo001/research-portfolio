# R3 within-family analysis specification

**Status:** POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.

This specification implements registered analyses FAM-01 through FAM-06.  It
was written before this workstream's new estimates were computed.  Protected
design-freeze and confirmatory-result artifacts are read-only inputs.

## Common data and treatment

All models use the March-restored 113-month calendar from January 2017 through
July 2026, omit the December 2022 transition month, and necessarily lack
October 2025.  They retain the historical 468-occupation Rule-A Eloundou-beta
support, exposure values, Webb-software control, and employment-weighted
quintile assignments used in the frozen 108-month model.  The run is invalid
unless it reproduces the previously audited corrected-calendar coefficient
`-0.1345539535732939` to absolute tolerance `1e-10`.

Inference uses 9,999 common occupation-level Rademacher score multipliers with
seed `2026090517`.  Signs are indexed to the common 468-occupation support and
subselected, without regeneration, when a model has narrower support.  These
intervals condition on the realized weighted CPS cells, mapping, exposure
labels, and model.  They are not design-based CPS intervals.

## FAM-01: full quintile profile

Estimate the Q2--Q5 post profile (Q1 omitted) with Webb-software-by-post under:

1. occupation and calendar-month fixed effects;
2. those fixed effects plus SOC2-by-post slopes, omitting the stock-largest
   SOC2 group as the redundant reference; and
3. occupation and SOC2-by-calendar-month fixed effects.

For every model report pointwise and four-coefficient max-|t| simultaneous
intervals, a wild-score Wald test that all four coefficients are zero, a test
that Q2=Q3=Q4=Q5, and the least-favorable max-t monotone-nonincreasing
diagnostic.  Report each conditioned-minus-baseline coefficient change using
the common draws and its paired normal-theory MDE.

## FAM-02: direct-tail changed-population benchmark

Use only Q1 and Q5 occupations in SOC2 families that contain at least one
occupation in each tail.  Estimate a binary Q5-by-post contrast under the same
three fixed-effect structures.  This is a changed-population benchmark, not a
re-expression of the full-support coefficient.  Report every included family
and occupation, preperiod stock, and shares of the full-support occupation
count and preperiod stock.

## FAM-03: continuous within-family companion

For occupation `o` in SOC2 family `g`, form

`z_within[o] = (beta[o] - weighted_mean_g(beta)) / weighted_sd(beta - mean_g)`.

Both centering and scaling use historical-support preperiod employment stocks
through November 2022.  One unit is therefore one employment-weighted
within-SOC2 standard deviation of the original Eloundou-beta score.  Estimate
a single common `z_within`-by-post slope under baseline, SOC2-by-post, and
SOC2-by-month structures, always retaining Webb-software-by-post.  The scalar
slope restricts all families to share the same within-family response per unit;
it is not an average of unrestricted family-specific slopes.

## FAM-04: leave one family out

For the Q2--Q5 SOC2-by-post and SOC2-by-month models and the continuous
SOC2-by-post and SOC2-by-month models, delete each observed SOC2 family in
stable code order, refit without recomputing exposure, quintiles, centering, or
scaling, and report the target coefficient and precision.  No deletion is
selected as a preferred result.  Failure or rank loss is recorded explicitly.

## FAM-05: named trajectories

Rank the four direct-tail families by their contribution to nuisance-adjusted
Q5 information in the direct-tail SOC2-by-month model, never by coefficient
sign.  For every such family and for Q1 and Q5 separately, report monthly young
and older weighted employment stocks, preperiod-normalized indices, and the
young-to-older log stock ratio.  These are descriptive paths; no sampling
interval is fabricated from aggregated final weights.

## FAM-06: information and MDE definitions

For scalar target column `x`, fitted information weights are
`h_i = T_i p_i (1-p_i)`.  Let `A_FE` denote exact weighted absorption of the
implemented fixed effects and let `Z` contain every other slope regressor.
The reported target residual is

`r = M_Z^h A_FE x`,

where the projection on `Z` uses the same fitted-information metric.  The
nuisance-adjusted Fisher information and occupation shares are

`I = sum_i h_i r_i^2`,

`s_o = sum_{i in o} h_i r_i^2 / I`, and

`G_eff = 1 / sum_o s_o^2`.

For comparison, raw treatment variation is
`sum_i h_i (x_i - weighted_mean_h(x))^2`; fixed-effect residual variation is
`sum_i h_i (A_FE x_i)^2`.  The output reports all three quantities, their
weighted standard deviations, the information retained relative to the raw
quantity, `G_eff`, the top-five occupation share, and the nominal occupation
cluster count.  The conditional two-sided five-percent normal-theory
`MDE80=(z_.975+z_.80) SE` uses the occupation-cluster SE.  Its information-only
analogue uses `1/sqrt(I)` and is labeled as an independent-cell diagnostic,
not sampling precision.  Paired MDEs use the SD of common-draw coefficient
differences.  None is a new rejection rule.

## Outputs

The workstream writes only to its requested project-storage output directory:

- `FAMILY_QUINTILE_SUPPORT.csv`
- `PROFILE_COEFFICIENTS.csv`, `PROFILE_JOINT_TESTS.csv`
- `PAIRED_PROFILE_CHANGES.csv`
- `DIRECT_TAIL_SUPPORT.csv`, `DIRECT_TAIL_MODELS.csv`
- `CONTINUOUS_WITHIN_FAMILY_MODELS.csv`
- `LEAVE_ONE_FAMILY_OUT.csv`, `MODEL_FAILURES.csv`
- `INFORMATION_DIAGNOSTICS.csv`, `OCCUPATION_INFORMATION.csv`
- `FAMILY_INFORMATION.csv`, `FAMILY_TAIL_TRAJECTORIES.csv`
- `FAMILY_TRAJECTORY_SELECTION.csv`
- `CENTERED_BOOTSTRAP_DRAWS.npz`
- `EXECUTION_RECEIPT.json`, `SELF_CHECK.json`, and `FINDINGS.md`.

