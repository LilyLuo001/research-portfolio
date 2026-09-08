# Gate 3 generated-shortfall findings (I08 and C05)

Status: the corrected shortfalls, 399-draw linked-household sensitivity, and
two-direction household-split diagnostic are complete and pass independent
public-output reconstruction. They replace the historical fixed-shortfall
rows; they do not turn the constructed shortfall into an exogenous control.

## Construction and support

Both shortfalls use ages 22--65, matching the estimating population. The trend
window is January 2017--December 2019, the measurement window is January
2020--November 2022, and December 2022 is excluded as a transition month. The
total-stock measure is the mean bounded trend prediction minus realized
normalized employment. The young-relative measure is the employment-weighted
mean bounded trend prediction minus the realized ages-22--25 employment share.
Positive values mean employment or the young share fell below trend.

The analysis excludes split Census occupation mappings and sparse histories.
It retains 363 occupations for the full-sample calculation and 361 occupations
for the two-fold common-support diagnostic. This is materially narrower than
the 468-occupation central support. On the 363-occupation support, the baseline
pooled coefficient is -0.16417 and the family-month coefficient is -0.08708,
rather than -0.13211 and -0.02167 on the central support. Consequently, the
shortfall exercise identifies within-support conditioning movements; it is not
a claim that restricting to shortfall-eligible occupations leaves the central
coefficient unchanged.

Bounding is consequential but explicit. Before enforcing the logical support,
the full-sample fits produced 174 negative total-employment predictions and
1,258 out-of-[0,1] young-share predictions. The reported shortfalls use the
declared lower bound of zero and unit interval, respectively. This functional-
form dependence remains a limitation rather than being hidden in the regressor.

## Corrected conditioning results

| shortfall | target | baseline Q5--Q1 | conditioned Q5--Q1 | movement |
|---|---:|---:|---:|---:|
| total stock | pooled | -0.16417 | -0.16377 | +0.00040 |
| total stock | family-month | -0.08708 | -0.08758 | -0.00050 |
| young relative | pooled | -0.16417 | -0.16303 | +0.00114 |
| young relative | family-month | -0.08708 | -0.08095 | +0.00613 |

The corrected total-stock coefficient is 0.00114 in the pooled model and
0.00079 in the family-month model. The young-relative coefficient is -0.00792
and -0.01349, respectively. The total-stock conditioning movement is negligible.
The young-relative row attenuates the pooled coefficient by 0.00114 log point
and the family-month coefficient by 0.00613 log point. These magnitudes do not
explain either within-support exposure coefficient.

## Generated-input sampling sensitivity

The linked-household exercise keeps a mean-one Exponential multiplier common
across every month, co-resident, and routed descendant of a positive CPSID. It
reports three distinct targets: fixed shortfalls and labels; regenerated
shortfalls with fixed labels; and regenerated shortfalls and labels. These are
released-weight household sampling sensitivities, not CPS design-based
intervals, and are never added mechanically to occupation- or family-shock
variance.

Regenerating the shortfall matters for precision, not for the point estimate.
For the young-relative conditioning movement, its sampling-sensitivity standard
error rises from 0.00111 to 0.00267 in the pooled model, from 0.00363 to 0.00700
in the family-month model, and from 0.00259 to 0.00549 for the paired
family-month-minus-pooled movement. The corresponding regenerated-input basic
intervals for the conditioning movement are [-0.00509, 0.00573], [-0.00889,
0.01835], and [-0.00628, 0.01494]. Thus the linked-household design does not
detect a shortfall-induced movement in the exposure coefficient.

Regenerating exposure labels in the same draws changes these quantities only
slightly. An average of 1.99 occupations is reclassified per draw; the
young-relative family-month movement remains 0.00613 with a 0.00695
sampling-sensitivity standard error. The fixed-input rows therefore do omit
first-stage uncertainty, but including the feasible first-stage variation does
not overturn the substantive result.

All 399 draws completed with zero failed joint refits. The maximum binding
bootstrap-of-bootstrap endpoint Monte Carlo standard error is 0.00979 log
point, below the predeclared 0.01 threshold, so the expansion to 799 draws is
not triggered. The independent validator reconstructs all 7,182 retained
result rows, coefficient identities, summaries, and stopping statistics.

## Household-split diagnostic

The deterministic two-fold diagnostic keeps all months and co-residents of a
linked household together, constructs the shortfall on one half, estimates on
the other, and reverses the roles. Its equal-weight average is close to the
same-support full-sample calculation. For the young-relative shortfall, the
average family-month conditioning movement is 0.00694 versus 0.00617 in the
full in-sample row; the augmented coefficient differs by -0.00013. The pooled
movement is 0.00215 versus 0.00115. The two directions are heterogeneous --
the family-month movement is 0.01388 in one direction and approximately zero
in the other -- so the average is a diagnostic rather than evidence that
regression-to-the-mean bias has been eliminated.

## Interpretation for the paper

The repaired exercise does not support the claim that the exposure association
is a disguised 2020--2022 employment shortfall on the eligible support. It
also does not establish that pandemic dynamics are absent. The shortfall is
constructed from related CPS employment outcomes, bounding and support choices
remain consequential, the linked-household design is not design-based CPS
inference, and sample splitting does not remove PSU-level shared error or all
regression-to-the-mean concerns. The manuscript should report the small
within-support movements, the wider regenerated-input sensitivity, and the
support change together.

## Evidence

- Specification: `SHORTFALL_RESAMPLING_SPEC.md`
- Batch runner and construction: `run_shortfall_refit_batch.py` and
  `shortfall_engine.py`
- 399-draw public run: `../../runs/gate3_shortfall_20260908/household_0399/`
- Summary: `../../runs/gate3_shortfall_20260908/household_0399/summary/SHORTFALL_REFIT_SUMMARY.csv`
- Independent validation:
  `../../runs/gate3_shortfall_20260908/household_0399/summary/INDEPENDENT_VALIDATION.json`
- Household split: `../../runs/gate3_shortfall_20260908/crossfit/`
