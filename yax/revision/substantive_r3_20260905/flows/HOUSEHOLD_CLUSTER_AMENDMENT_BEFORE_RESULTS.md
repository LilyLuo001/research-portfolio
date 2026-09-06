# R3 flow dependence amendment: person and household score clustering

> **POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

This narrow amendment was written after the corrected flow point estimates and
occupation-cluster intervals were known, but before any person- or
household-cluster flow result was computed. It responds to the requirement to
preserve dependence induced by repeated CPS links. It does not change an
outcome, risk set, treatment, calendar rule, weight, point estimator, or the
primary occupation-cluster inference in
`ANALYSIS_SPEC_BEFORE_RESULTS.md`.

## Fixed scope

The sensitivity covers every official-weight core flow model, with no selection
based on its coefficient:

* employment exit, unemployment entry, labor-force exit, occupational
  outflow, and entry-destination allocation;
* adjacent-month and twelve-month endpoints;
* Rule-A beta Q5 versus Q1, ages 22–25 versus 26–65, January 2023 break, and
  the Webb control exactly as in the completed flow package.

The continuing-worker hours model, cross-sectional earnings model, and near-age
changed-population sensitivity are outside this amendment. They are not part of
the compact core-flow collection and their estimating equations do not share
the same conditional event-allocation score.

## Computation fixed before inspection

The script must rebuild the corrected official-weight linked samples from the
same restricted inputs and must reproduce each stored core-flow point estimate.
For each occupation-by-calendar-month cell, it refits the same grouped
conditional-binomial representation. Conditional on the cell's weighted risk
sets and total events, an event contributes

* `w * (1 - p)` when the event belongs to the young group; and
* `-w * p` when the event belongs to the older group,

where `w` is the official longitudinal weight (including a route share before
2020), and `p` is the fitted conditional young-event share. Multiplying this
contribution by the nuisance-residualized design and the model bread yields an
event-level score influence. The event influences must sum back to the stored
occupation influences, within numerical tolerance, before any cluster result is
accepted.

The target influences are summed separately by origin `CPSIDV` and origin
household `CPSID`. Only aggregate cluster counts and variance summaries may be
written. Identifiers and event-level contributions remain in memory and outside
git. Each one-way cluster variance uses the finite-cluster factor `G/(G-1)` and
a normal 95-percent interval. The normal-theory MDE80 is
`(z_.975 + z_.80) * SE`.

No paired cross-horizon comparison is defined: adjacent and annual samples have
different eligibility, weights, transition windows, and endpoint meanings.
Consequently no common-draw paired claim is authorized. All ten outcomes are
reported, and no multiplicity-adjusted discovery claim is made.

## Interpretation fixed before inspection

Occupation clustering remains the primary economic-shock inference. Person and
household clustering are separate sampling-dependence sensitivities; their
variances are not added to, substituted for, or selected against the
occupation-cluster variance. They condition on the model's cell risk sets and
event totals, use released IPUMS longitudinal weights, and are not full CPS
replicate-weight or design-based inference. A narrower interval under either
sensitivity cannot be presented as stronger evidence.

If either person or household clustering materially widens an interval, the
main flow discussion must foreground that dependence sensitivity. If it does
not, the paper may state only that this declared conditional-score sensitivity
does not overturn the occupation-cluster precision assessment. It may not claim
that household dependence is absent or that the CPS survey design has been
fully reproduced.

