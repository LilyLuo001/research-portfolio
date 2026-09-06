# R3 corrected CPS flow and secondary-outcome specification

> **POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

This specification was written before executing the R3 flow and secondary-
outcome results in this directory. Earlier Phase 2 adjacent-month flow results
were already known. Accordingly, this is a post-outcome revision protocol, not
an ex-ante preregistration. It preserves the historical Phase 2 artifacts and
creates a corrected-calendar, explicitly weighted comparison package.

## 1. Questions and fixed treatment contract

The package asks three bounded descriptive questions:

1. Do corrected public-CPS links show a young-relative post-2022 change in
   employment exit, unemployment entry, labor-force exit, or occupational
   outflow from high- rather than low-beta occupations?
2. Is the adjacent-month result materially different at a twelve-month
   endpoint, recognizing that an endpoint comparison can miss intervening
   transitions and changes the age population?
3. Among workers, do usual hours or weekly earnings show an analogous
   young-relative Q5-versus-Q1 post association?

The treatment is the fully rebuilt Rule-A Eloundou-beta quintile membership
from `rebuilt_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv`. It was formed
from corrected January 2017--November 2022 employment stocks before this flow
execution. Webb software-patent exposure enters as the same preperiod-
standardized continuous companion used in the historical Phase 2 models. All
models use the intersection of finite beta and Webb values. No flow outcome
may change a quintile, cutoff, support rule, or normalization.

## 2. Corrected Basic Monthly data

The analysis reconstructs the Basic Monthly series by removing all base-
extract rows in March 2017--2021 before eligibility is evaluated and appending
the corresponding `03b` records from the authenticated March repair extract.
It never appends the repair to retained base March records. The five same-month
repair samples have zero eligible `YEAR`-`MONTH`-`CPSIDV` overlap with the
superseded positive-weight records, as established by the independent March
audit.

An IPUMS weight-only patch is requested for the same corrected 114-sample
calendar. It replaces `cps2017_03s` through `cps2021_03s` with the corresponding
`03b` samples and includes `LNKFW1MWT` and `LNKFW1YWT`. The patch is merged by
`YEAR`, `MONTH`, `SERIAL`, and `PERNUM`; all available longitudinal identifiers,
MISH, and age must agree. Restricted microdata and identifiers remain outside
git under `<YAX_SCC_PROJECT_ROOT>/private`.

October 2025 was not collected and is never interpolated. December 2022 is the
transition origin and is excluded from static adjacent-month models.

## 3. Link definitions, age, and attrition

### Adjacent month

An eligible origin is age 22--65 at interview, has nonzero `CPSIDV`, has MISH
1, 2, 3, 5, 6, or 7, and has an actually observed next calendar month. A valid
link has the same nonzero `CPSIDV`, destination month exactly `t+1`, and
destination MISH equal to origin MISH plus one. MISH 4-to-5 returns are not
adjacent and are excluded. September-to-November 2025 is not a link.

The young indicator is age 22--25 at origin; the main comparison is age 26--65
at origin. Destination age never reclassifies an origin. The age-26 crossing
rate is reported. One declared changed-population sensitivity replaces the
older comparison with ages 26--30 for adjacent employment exit only.

The official primary weight is positive origin `LNKFW1MWT`. Unweighted and
origin-`WTFINL` estimates are labeled sensitivities; `WTFINL` is not described
as correcting link attrition. Match and positive-weight retention rates are
reported by age, period, MISH transition, employment state, and origin beta
quintile, including linked-versus-unlinked composition.

### Twelve month

An eligible origin is MISH 1--4 and has an observed sample exactly twelve
calendar months later. A valid endpoint link has the same nonzero `CPSIDV` and
destination MISH equal to origin MISH plus four. The official primary weight is
positive origin `LNKFW1YWT`. The same CPSIDV validation is retained even though
the IPUMS weight is constructed for CPSIDP-compatible links.

To avoid classifying transitions that cross the January-2023 break as pre,
twelve-month pre origins end in November 2021, origins December 2021--December
2022 form an excluded transition band, and post origins begin January 2023.
Annual occupational-switch models also exclude every 2019 origin because the
endpoint crosses the 2010-to-2018 Census occupation coding break. Employment-
status models retain those origins. The annual outcome is endpoint status; it
does not count intervening jobs or spells. Ages are fixed at origin, so the
young endpoint population can be age 26. This is not the repeated stock
population of ages 22--25.

## 4. Flow risk sets and estimands

Each origin-based margin assigns exposure only from a valid employed origin.
No current occupation is assigned to a nonemployed person.

For adjacent and annual horizons, the registered origin-based margins are:

* **employment exit:** employed at origin and nonemployed at endpoint;
* **unemployment entry:** employed at origin and unemployed at endpoint;
* **labor-force exit:** employed at origin and not in the labor force at
  endpoint;
* **occupational outflow:** employed at both endpoints, both endpoints have
  valid harmonized `OCC2010`, and the endpoint codes differ.

The annual occupational-outflow result is an endpoint difference, not a count
of switches. For each margin, a grouped conditional-Poisson rate model is
computed through its two-age grouped-binomial representation. It contains
origin occupation-by-age, origin occupation-by-calendar-month, and
age-by-calendar-month effects; Q2--Q5 by young by post terms; and Webb by young
by post. The reported target is the beta Q5-versus-Q1 young-relative post
coefficient in log rate-ratio units. `100(exp(beta)-1)` is reported only as the
corresponding relative-rate comparison, not as an individual probability
effect.

For linked nonemployed origins who are employed at the endpoint, the
**entry-destination** model assigns beta/Webb only to the observed destination
occupation. It conditions on the number of observed entries by age and month
and asks about relative allocation to Q5 rather than Q1 destinations. It is
not an employment-finding probability, an employer hire rate, or BCC's
new-employer-match hiring outcome. The annual version is an endpoint
allocation and can miss intervening employment.

## 5. Hours, earnings, unemployment duration, and LFP decisions

The two selected worker outcomes are fixed before inspection:

* **Adjacent usual-hours change:** among employed origins and employed
  destinations with `UHRSWORKT` in 1--99 at both interviews, use origin
  `LNKFW1MWT`. Cell numerator is the weighted sum of destination usual hours
  and denominator is the weighted number of continuing workers. The grouped
  rate coefficient is a conditional mean-hours ratio; a companion descriptive
  table reports within-person hour changes. This conditions on continued
  employment and is not a total labor-input effect.
* **Weekly earnings level:** among employed Basic Monthly outgoing-rotation
  respondents with MISH 4 or 8, positive `EARNWT`, and `EARNWEEK` strictly
  between zero and the 9999.99 NIU code, estimate the same corrected monthly
  grouped mean-rate model using `EARNWT`. Age, occupation, and period are
  contemporaneous. Month effects absorb common nominal-price changes. This is
  a cross-sectional conditional weekly-earnings association, not a linked
  earnings change. No annual linked earnings model is run because IPUMS
  instructs users to use `EARNWT` for `EARNWEEK`, while `LNKFW1YWT` is the link
  weight; the available files provide no validated joint longitudinal-
  earnings weight.

Unemployment incidence and labor-force exit are executed as the two mutually
exclusive destination components of employment exit. `DURUNEMP` is described
only among linked employed-to-unemployed events: it is duration observed after
selection into unemployment, is censored as a spell measure, and does not
support the same at-risk occupation estimand. A population LFP-by-exposure
model is not run because unemployed and NILF respondents generally have no
comparable current occupation. The origin-based employed-to-NILF rate is the
valid registered LFP margin.

## 6. Inference, MDEs, and dependence

Primary intervals use a target-occupation-cluster sandwich and 9,999 common
Rademacher score draws within each horizon/weight comparison. The fixed seed
is `2026090524`. Analytic clustered SEs, wild-score two-sided 95-percent
intervals and p-values, and the labeled normal-theory
`MDE80 = (z_.975 + z_.80) * SE` are reported. The MDE is a precision
description, not a rejection or equivalence threshold.

Target-occupation clustering captures arbitrary serial dependence in the
occupation-level score. It is not complete CPS survey-design inference and
does not capture all household dependence when people move across
occupations. A lineage-component sensitivity gives every split route from the
same pre-2020 source occupation the same cluster lineage and reports the
number of components. It is a dependence sensitivity, not a uniquely correct
reference distribution. Household/sample-oriented uncertainty is kept
separate from occupation-shock uncertainty; the package does not mechanically
add variances. Repeated transitions from the same CPSIDV and household CPSID
are counted and disclosed.

Every pre-2020 route descendant of a source record receives the same source
record weight times its bridge probability. Route probabilities must sum to
one and risk/event quantities must be conserved before support exclusions.
No fractional descendant is treated as a new respondent.

## 7. Relation to employment stocks and BCC

The stock identity contains employment entry and exit, occupation switching,
aging into and out of ages 22--25, and residual population/sample-composition
change. Adjacent CPS transitions do not observe all employer changes; annual
endpoint links miss intervening transitions. BCC's payroll hiring margin is a
new-employer-match measure over a prior-year denominator and is not reproduced
by CPS nonemployment entry or occupation switching. Therefore no scalar
stock-flow calibration or claim that the flow coefficients explain a share of
the stock coefficient is authorized. The output supplies a bridge table that
names these mismatches and records BCC-04 as not identified rather than
manufacturing an implied response.

## 8. Fixed outputs and stopping rules

The runner writes aggregate-only link audits, risk/event counts, flow and
worker-outcome results, descriptive rates, MDEs, occupation support, a
stock-flow comparability table, a feasibility/limitations memo, an execution
receipt, stored score/draw representation, and a self-check. It writes no
person or household identifier.

Execution stops before estimates if the corrected weight patch fails the exact
merge/identifier audit, if CPSIDV/MISH/calendar validation fails, if route
weights fail conservation, or if rebuilt membership hashes do not match the
recorded input. Outcome-specific zero-event occupations may leave a likelihood
only when disclosed. Failed/nonconvergent models remain in a machine-readable
failure file and are not silently replaced.

