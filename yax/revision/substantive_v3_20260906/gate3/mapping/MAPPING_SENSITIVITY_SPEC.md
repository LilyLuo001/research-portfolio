# Gate 3 mapping-sensitivity specification

Status: **post-outcome exploratory; written before this current-contract run**.
The outcome has already been opened elsewhere in YAX. No result from the run
specified here has been inspected when this document is committed. The frozen
v1.1 design and confirmatory results are unchanged.

This block closes W01--W04 and the mapping-dependent part of L02. It replaces
historical mapping, service-exclusion, and influence numbers with estimates on
the current rebuilt treatment contract. Historical artifacts remain evidence
about project chronology only.

## 1. Fixed scientific contract

The analysis uses the current 468-occupation BASE-03 support, the 113 observed
Basic CPS months from January 2017 through July 2026, ages 22--25 versus
26--65, December 2022 excluded as the transition month, and October 2025 absent
because no CPS survey was fielded. The canonical exposure is Rule-A Eloundou
beta. Its quintiles and the Webb-software normalization use weighted employed
stock from January 2017 through November 2022.

The estimator is the current grouped-binomial two-age model. The pooled version
contains occupation and calendar-month fixed effects plus Q2--Q5 by post and
Webb-software by post. The family-month companion replaces calendar-month fixed
effects with SOC2-family by calendar-month effects. The target is Q5 by post
with Q1 omitted. Inference uses 9,999 common occupation- and family-level
Rademacher score multipliers, preserving covariance in paired differences.

Before fitting any sensitivity, the runner must reproduce from raw data:

1. every canonical young and older occupation-month stock in the protected
   calibration object, within a maximum relative tolerance of `1e-10`;
2. all current preperiod construction weights, quintiles, and Webb z-scores;
3. the pooled coefficient `-0.13210945079219025` and the family-month
   coefficient `-0.021674952018246537`, within `1e-8`.

Failure of any identity blocks the run. No microdata row or identifier is
written to the repository.

## 2. Official routes and feasible allocation set

For 2017--2019, a source Census-2010 occupation can contribute only to target
Census-2018 occupations listed in the authenticated official bridge. For 2020
onward, the Census-2018 occupation is observed directly and never tilted.

All sensitivities preserve, separately for every source occupation, age group,
and month, the stock routed to the fixed 468-occupation analysis support under
the official bridge. Structural zeros remain zero. We impose no all-age target
margin because the published bridge shares are conversion proportions, not
known realized age-specific margins. Thus every evaluated point is jointly
feasible under the stated source-age-month constraints, but the set is not
claimed to be an identified set for true age-specific routes.

Only a split source with at least two supported targets and finite current beta
and Webb scores for every supported target is tilt-eligible. Targets are ranked
by beta within source, average ranks are used for ties, and ranks are scaled to
`[-0.5, 0.5]`. Ineligible sources retain official weights. The run reports the
eligible sources and their share of bridge-dependent weighted stock.

## 3. Symmetric odds-tilt sensitivity (W02)

For official route weight `w_sj`, scaled beta rank `r_sj`, and
`theta = log(K)/2`, the supported route weights are proportional to

```
young: w_sj exp(+theta r_sj)
older: w_sj exp(-theta r_sj).
```

Within each source and age, weights are normalized back to that source's
official mass on the 468 support. Consequently `K` is the young-versus-older
relative high-versus-low allocation odds. The fixed grid is
`K = {0.25, 0.5, 2/3, 1, 1.5, 2, 4}`. `K=1` is the official bridge.

Each grid point is estimated two ways:

- **fixed labels:** hold the canonical quintiles and Webb normalization fixed;
- **rebuilt treatment:** recompute 2017--November-2022 occupation weights,
  beta cutoffs/memberships, and Webb normalization on the unchanged 468 support.

Both pooled and family-month models are fit. Every model stores current
occupation and family influence vectors. Paired intervals against `K=1` use
the same cluster multipliers. A confidence interval containing zero means only
that the design does not detect a difference.

## 4. Adverse joint grid (W03)

The adverse exercise lets the young and older high-versus-low odds move
independently. For age `a`, supported weights are proportional to
`w_sj exp(log(K_a) r_sj)` and are normalized within source-age-month. The fixed
grid is

```
K_young, K_older in {0.05, 0.25, 1, 4, 20}.
```

All 25 points use canonical fixed labels and the pooled estimator. The minimum
and maximum fitted coefficients are an **explored adverse envelope**, not a
sharp or global coefficient bound. No separate numerator, denominator, or tail
extrema are combined. The run reports the grid, constraints, extrema, and mass
conservation. No outcome-directed local optimization follows this grid.

## 5. Unsplit and stable-taxonomy checks (W04)

The clean-route support excludes every current target occupation with any
structurally possible inbound one-to-many route. It is reported with canonical
labels fixed and, separately, with weights/cutoffs/Webb normalization rebuilt
on the smaller population. These are support-changing estimates, not the same
estimand as the 468-occupation baseline.

The successful current-contract post-2020 coding-stable models are carried
forward by hash from Gate 2. The earlier stable-Census-2010 result is also
carried forward by hash and labeled as changing the occupation population,
taxonomy, exposure mapping, and labels. Neither is adjacent-vintage
pseudo-validation.

## 6. Current service and influence diagnostics (W01)

Four inherited, rule-based exclusions are rerun with current canonical labels:
all SOC35; Q1 SOC35; all SOC35/37/39; and Q1 SOC35/37/39. SOC33 protective
services are not part of these definitions. The exact historical top-5,
top-10, and top-20 deletion sets, plus the named fast-food occupation, are
rerun as explicitly outcome-informed inherited diagnostics; they are not
reselected or presented as confirmatory tests.

The canonical current-model occupation influence vector, squared-influence
shares, effective contributing-occupation count, and named ranks are stored.
The influence function is a local linear diagnostic; it is not mislabeled as
an exact leave-one-out refit. The predefined deletion fits are exact refits.

## 7. Coding-error disposition (L02)

The bridge tilt is an allocation sensitivity, not a validated occupation-code
error model. YAX has no authenticated dual-coded validation sample or external
misclassification matrix for the relevant CPS occupation coding process.
Immediate longitudinal reversals are not used as an error rate because they
mix real mobility, proxy response, editing, and coding error. A symmetric
random-error simulation without a calibrated matrix would add an arbitrary
assumption and is therefore not executed. This scientific feasibility
disposition is recorded alongside the completed feasible bridge sensitivities.

## 8. Required outputs and refusal rules

Required outputs include model results, paired movements, complete influence
vectors, tilt memberships, route eligibility/coverage, source-age-month mass
checks, adverse-envelope points, service/deletion results, carry-forward
records with hashes, model failures, and a sanitized execution receipt. A
separate public validator must reconstruct intervals and paired intervals from
the stored influence vectors and must verify every no-tilt, mass, support, and
carry-forward identity.

The runner refuses to publish if any required fit fails, if a route assigns
mass outside official support, if any source-age-month mass changes beyond
tolerance, if the no-tilt data or coefficient differs, or if a carried-forward
source hash moves. Results are descriptive sensitivity analyses. They do not
identify true age-specific route probabilities, causal AI effects, or economic
equivalence.
