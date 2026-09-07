# Gate 2 support and accounting preflight

Status: specified and unit-tested before execution against the authenticated
Gate 1 aggregate.

## Scope

This first Gate 2 unit advances the model-free portions of S01--S02 and the
exact descriptive accounting in D01, D03, and D04. It does not claim to finish
the inferential support models, paired uncertainty, broader beta-valid support,
age/enrollment analysis, or manuscript integration.

The signed specification is `SUPPORT_ACCOUNTING_SPEC.json`. The runner accepts
only the authenticated 468-occupation Gate 1 aggregate, its exact receipt, the
canonical specification, the fixed membership file, and the independently
upheld Gate 1 A1 model audit. It does not read row-level CPS microdata.

## Historical-result exclusion

The historical within-family output is not reused as V3 evidence. Direct code
inspection found that its `primary_setup()` passed the full supplied analysis
panel into `prepare_model()`, whose weights sum young and older stock over all
supplied months before calling `weighted_quintiles()`. That behavior is
incompatible with the historical prose claiming fixed 2017-01--2022-11
assignments.

The difference is material to support. Historical
`DIRECT_TAIL_SUPPORT.csv` classified occupation 3620 as Q1. The byte-locked
canonical membership classifies it as Q2. Recomputing support from the fixed
membership gives 29 direct-tail occupations in exactly four families: 27, 29,
31, and 41. A regression test pins all three facts. Historical coefficients,
draws, support shares, information statistics, and trajectory selections are
therefore algorithm references only.

## Frozen descriptive choices

- Preperiod: 71 observed months, January 2017 through November 2022.
- Transition: December 2022 retained in transport and excluded here.
- Postperiod: 42 observed months, January 2023 through July 2026, with October
  2025 absent and never interpolated.
- Period stocks: equal-weight arithmetic means over observed months.
- Support shares: national, within-family, and within-quintile denominators are
  separately labeled.
- Graph: every within-family observed quintile pair is an edge; connectedness
  and incidence rank do not turn the national common-profile coefficient into
  an average of direct family Q5--Q1 effects.
- Composition: the exact midpoint decomposition is reported in level ratio
  units. An exact three-factor log Shapley decomposition separately allocates
  the log change to within-family ratios, older-family weights, and boundary
  mass.
- Zero denominators: every family-quintile-period cell is classified. Undefined
  ratios are never set to zero. Young stock outside the common-positive set is
  retained as boundary mass, and every hybrid used by the log decomposition
  must remain strictly positive.
- Inference: not executed in this unit. Exact descriptive identities do not
  provide confidence intervals.

## Pre-result validation

Six focused tests cover the complete 22-by-5 matrix, graph rank and named
edges, frozen direct-tail correction, exact log-stock closure, level and log
composition closure, boundary-mass retention, assignment mismatch rejection,
and specification fingerprint sensitivity. Full repository tests must pass
again after this unit is added and before the SCC run is committed.
