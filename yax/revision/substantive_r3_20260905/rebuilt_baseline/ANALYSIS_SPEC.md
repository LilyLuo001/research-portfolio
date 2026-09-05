# BASE-03: fully rebuilt corrected-treatment baseline

Status: **post-outcome exploratory; specified before BASE-03 execution**

This module distinguishes the historical production baseline from a pipeline in
which the five missing March Basic samples are restored not only to the outcome
calendar but also to every treatment-construction object. It does not alter any
frozen or confirmatory artifact.

## Rebuilt contract

Before any model is fit, the runner must:

1. rebuild employment-stock cells from the authenticated wide CPS file and the
   March Basic repair extract using the declared Census 2010-to-2018 routes;
2. verify route-mass conservation against the raw eligible records;
3. verify the exact 71-month pre-period calendar, January 2017 through November
   2022;
4. form the candidate occupation universe directly from those rebuilt cells,
   without reading the historical sealed support;
5. require positive pre-period employment stock for ages 22--25 and ages
   26--65, strict Rule-A Eloundou beta, and finite Webb software exposure;
6. compute occupation weights, beta and Webb weighted scales, tie-preserving
   employment-weighted quintile cuts, and memberships using pre-period stock
   only; and
7. write the complete gate artifacts and a `no_postperiod_stock_used` assertion.

Only after this gate passes may the historical sealed pre-period artifact be
read for the two historical-treatment comparison rows.

## Models and comparisons

All static fits exclude December 2022. October 2025 remains absent; it is never
interpolated. The target is the Q5-by-post coefficient relative to Q1 in the
grouped-binomial conditional equivalent of the two-age PPML, with occupation
and calendar-month fixed effects and Webb software-by-post conditioning.

The decomposition contains:

- historical 108-month outcomes with the historical production treatment;
- corrected 113-month outcomes with the same historical production treatment;
- corrected 113-month outcomes with the fully rebuilt pre-period treatment;
- on the exact intersection support, corrected outcomes with native historical
  versus native rebuilt classifications and normalizations.

The first calendar contrast and the fixed-common-support reclassification use
common occupation-level Rademacher multipliers. A contrast involving different
occupation supports is descriptive and is never labeled paired. The common-
support reclassification combines the consequences of native weighting,
cutoffs, memberships, and Webb normalization; it is not a causal decomposition.
If the historical and rebuilt native supports are exactly identical, the third
versus second decomposition row is already the fixed-common-support comparison;
duplicate common-support model rows are not emitted.

Inference uses 9,999 occupation-cluster wild-score multiplier draws with seed
`2026090521`. All successes and failures are retained.
