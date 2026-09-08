# Gate 4 CPS flow selection and denominator specification

> **POST-OUTCOME, REFEREE-DIRECTED EXTENSION.** The historical R3 flow
> coefficients were known before this document. This specification fixes the
> additional selection, denominator, and annual-timing analyses before their
> current-contract outputs are generated. It is not a preregistration and does
> not turn the flow analysis into a causal AI design.

## 1. Fixed inputs and treatment

The corrected 2017--2026 Basic Monthly CPS reconstruction, official IPUMS
`LNKFW1MWT` and `LNKFW1YWT` patch, CPSIDV/MISH/calendar link validation, 468-
occupation Rule-A Eloundou-beta membership, Webb companion measure, and
2010-to-2018 Census occupation bridge are unchanged from the corrected R3 flow
package. The runner verifies their bytes. It writes aggregates only and never
writes person or household identifiers.

The current treatment file is byte-identical to the one used by the historical
R3 flow run. That fact permits the previously certified conditional flow
coefficients and occupation/person/household dependence calculations to remain
the regression evidence. This package addresses omissions in their risk-set
and selection interpretation; it does not silently substitute a new treatment.

## 2. Eligibility and linkage accounting

For each horizon, audit age-22--65 Basic Monthly origins whose exact target
calendar month is absent, then define the eligible-origin population among
origins whose target month exists. Report, separately:

1. rotation-position ineligibility;
2. rotation-eligible records without a nonzero validated identifier;
3. eligible records with no CPSIDV/MISH-valid endpoint;
4. valid endpoint links with zero official longitudinal weight; and
5. valid positive-official-weight analysis links.

Adjacent-month eligible MISH positions are 1, 2, 3, 5, 6, and 7 and require a
one-step MISH progression. Twelve-month eligible positions are 1--4 and require
a four-step progression. October 2025 is absent, not interpolated; September to
November is never treated as adjacent.

Origin-exposure results use employed origins with a valid reported occupation
that routes to the fixed support. Link retention uses origin `WTFINL` in both
its numerator and denominator. Transition probabilities use the appropriate
positive official link weight among retained links. Raw and fractional routed
record counts, risk weights, event weights, and probabilities are shown by
horizon, origin age group, beta quintile, period, and margin.

## 3. Linked versus eligible-unlinked composition

Compare retained and eligible-but-not-retained employed origins using the same
origin-`WTFINL` population basis. The fixed observable characteristics are
exact age, BA-or-higher attainment, 35-plus usual hours, wage/salary class, and
origin weight. Comparisons are reported by horizon, period, age group, and
quintile. They diagnose observed selection; they do not establish the sign of
selection on unobserved outcomes, and clustering is never described as a
selection correction.

## 4. Observable-selection sensitivity and positivity

For each horizon/period/age/quintile cell, post-stratify retained employed
origins to the eligible-origin distribution over exact age, calendar year,
MISH, three-level education status, and 35-plus-hours status. Within a stratum,
the factor is eligible origin `WTFINL` divided by retained origin `WTFINL`.
There is no trimming or cap. Report unsupported eligible mass, minimum/median/
99th-percentile/maximum factors, and effective sample size.

The post-stratified probability assumes conditional missing-at-random: outcome
missingness is independent of linkage within these observed strata. It is an assumption-
labeled sensitivity, not a correction known to identify the population rate.
Official-link-weight, origin-`WTFINL` complete-case, and post-stratified rates
remain distinct.

## 5. Missing-outcome accounting bounds

For employment exit, unemployment entry, and labor-force exit, let `ell` be the
origin-`WTFINL` share retained and `p_L` the linked origin-`WTFINL` event rate.
The group probability range is

`[ell * p_L, ell * p_L + 1 - ell]`.

Report the resulting jointly feasible linear Q5-minus-Q1, young-minus-older,
post-minus-pre contrast bounds. The eight population cells are disjoint, so
the interval endpoints can be attained by assigning missing binary outcomes
at the original-record level. In particular, every fractional bridge descendant
of one source record receives the same missing outcome; descendants are never
optimized independently. Report a conservative marginal outer interval for the
analogous log-relative contrast and label it non-sharp. Zero probability
endpoints produce literal positive or negative infinity; they are never
clipped. Bounds are margin-specific and do not impose cross-margin
restrictions. No Lee trimming or monotone-selection claim is permitted.

## 6. Entry probabilities on one risk set

The denominator is every retained nonemployed origin. With the appropriate
official link weight, destinations are mutually exhaustive:

- remaining nonemployed;
- employed in each supported destination quintile Q1--Q5;
- employed with a valid occupation outside retained exposure support; and
- employed with missing/invalid destination occupation.

Pre-2020 destination occupation routes may split fractionally through the
fixed bridge. Per-origin category mass and aggregate probability must sum to
one. The supported-Q1--Q5 allocation conditional on an observed supported
entry is retained in a separately labeled table. Neither object is an employer
hiring rate. A nonexistent/failed entry receives no destination occupation or
destination cluster.

## 7. Annual timing

Age and exposure are defined at origin; destination age and age-26 crossings
are reported. The primary annual regression excludes origins December 2021
through December 2022: December 2021 ends in the excluded December-2022
transition month, and January--December 2022 endpoints cross the January-2023
onset. Pre origins therefore end November 2021 and post origins begin January
2023.

The fixed sensitivity retains all valid annual endpoints and replaces binary
post with the fraction of the twelve destination months `t+1,...,t+12` that
fall in January 2023 or later. This fraction is zero through December 2021,
1/12 for January 2022, ..., 12/12 for December 2022, and one thereafter. Its
coefficient is a full-zero-to-one exposure-duration comparison. Both rules
exclude annual occupation-change observations that cross the 2010/2018 coding
boundary, and both disclose missing target months. Annual endpoints are never
described as sums of monthly transitions.

The corrected March Basic replacement, the unavailable October 2025 survey,
the terminal right-censoring of the extract, and the 2019/2020 occupation-code
change are reported as distinct file/calendar facts. No population-control or
file revision is interpolated into an unobserved endpoint.

## 8. Inference and scope

The annual timing comparison uses the same grouped-binomial estimator,
occupation fixed effects, month fixed effects, Webb companion term, and 9,999
common occupation score multipliers as the corrected R3 analysis. It also
reports route-lineage-component sensitivity. Previously computed CPSIDV and
household score sensitivities remain attached to the primary exclusion-rule
models; the duration specification is labeled a timing sensitivity and is not
selected by significance.

Hours remain a within-person change among adjacent continuing workers with
valid hours. Unemployment duration remains descriptive after selection into
unemployment. Full-window weekly earnings remain blocked because the
authorized extracts lack `EARNWEEK2`; the three-post-month `EARNWEEK` result is
not full-window evidence. No CPS-to-employer stock-flow calibration is made.
