# Pre-outcome implementation audit for the v1.1 frozen analysis

**Recorded before any protected post-period outcome was read.** The immutable
design authority remains commit `22fbf7924809b7a535e31ae0ab68f5b113ce8078`
and tag `v1.1-design-freeze`.

## Why implementation code was added after the tag

The tagged tree contains the estimating equation, outcome, support, timing,
exposures, controls, inference requirements, power engine, table shells, and
sealed pre-period cells, but no production post-outcome estimator. The only
cell builder in the tag hard-refuses post-period rows. Implementing the frozen
design is therefore a category-1 execution requirement, not a new
specification.

## Mechanical implementation choices

- The frozen two-age PPML is run through its exact grouped-binomial
  conditional likelihood already used by the tagged power engine.
- The 490 occupation clusters are selected solely from the authenticated
  2017-01 through 2022-11 pre-period cells. Post-period support never selects
  occupations.
- Post cells use raw Census-2018 `OCC`, `WTFINL`, `EMPSTAT in {10,12}`, ages
  22–25 and 26–65. December 2022 is omitted from static models and retained in
  the event study. October 2025 is absent.
- Rule A, B, and C implement the signed definitions. The measurement-only
  Rule-B builder authenticates its component coverage and partial sums against
  the frozen variants before it emits sibling-imputed values. Four Census
  occupations have no scored sibling in the specified SOC broad group; none is
  in the frozen 490-cluster support, so this global source limitation does not
  change any analysis sample.
- Q5–Q1 uses employment-weighted quintiles on each frozen scenario's support,
  keeps tied scores together, and separately absorbs Q2–Q4, matching the power
  engine.
- Primary inference is a 999-draw occupation-cluster Rademacher wild **score**
  bootstrap. Cluster score contributions from the frozen conditional
  likelihood are multiplied by Rademacher weights. The paired beta-minus-alpha
  analysis uses the same 999 signs for both estimates and forms Delta within
  draw.
- The event-study reference remains 2022-10, the last explicit reference-month
  instruction in the frozen lineage. December 2022 is the first exposure month.
- The remote-work exposure is the static Dingel–Neiman occupation measure named
  `remote_work_control` in the authenticated frozen lookup receipt. No young
  worker's own telework response is used.
- The frozen “post-2025 extension” label is implemented as 2025-01 through
  2026-07 versus 2023-01 through 2024-12, excluding the known 2025-10 gap.
- The four-row crosswalk decomposition uses the deliberately naïve exact-code
  AIOE baseline and the repaired administrative AIOE mapping, with one scale
  fixed on repaired expanded support; row 4 excludes SOC major group 15.

## Non-additions

No age band, outcome, treatment date, exposure ordering, support threshold,
fixed effect, rival mechanism, or confirmatory interpretation was changed. No
protected post-period row was used to write or test this implementation.

