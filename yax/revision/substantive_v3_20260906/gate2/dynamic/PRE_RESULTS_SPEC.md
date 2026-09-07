# Gate 2 dynamic reconciliation: pre-result specification

This directory is a pre-result implementation for V3 Sections 9.1--9.2. It
does not execute or certify an authoritative Gate 2 result. The machine-readable
contract is `DYNAMIC_RECONCILIATION_SPEC.json`; its ID hashes every field other
than `spec_id`, including the runner byte hash and all upstream input hashes.

The core is limited to the four already A1-certified models: `pooled`,
`family_month`, `dynamics_unconditioned`, and `dynamics_family_month`. No local
quintile, support, Webb normalization, sample, nuisance structure, endpoint, or
objective may be recomputed or changed.

## Frozen calendar and functionals

The fitted calendar has 113 months: 71 observed pre months from January 2017
through November 2022 and 42 observed post months from January 2023 through
July 2026. December 2022 is the excluded transition month. October 2025 is
genuinely absent. Thus 2022Q4 has two observed reference months, 2025Q4 has two
observed post months, and 2026Q3 has one observed post month.

For each structure, `S` is the certified static Q5-by-post coefficient. `P` is
the observed-post-month-weighted mean of Q5 quarter coefficients relative to
the published 2022Q4 reference. `D` is that post mean minus the
observed-pre-month-weighted mean, including two zero-coefficient reference
months under the published normalization. The runner reports `P-S`, `D-S`,
`P-D`, and family-month minus unconditioned movements for `S`, `P`, `D`, and
both static/dynamic gaps.

## Checks and nonclaims

The bound Gate 1 audit supplies complete dynamic coefficient vectors, so the
runner verifies all-component coefficient extraction, frozen weights, the
published post functional, and coefficient-level reference invariance. Generic
utilities implement arbitrary invertible linear transformations without calling
them reference rebases. A distinct reference-rebase validator independently
derives the unique free-coordinate map from period labels and the old/new
references, rejects any supplied map that differs beyond the signed absolute
tolerance, and only then certifies transformed restrictions. Other utilities
implement caller-predeclared exact `Xs = Xd A` validation (the mapping is never
fitted inside a PASS-exact check), dynamic score-moment preservation, and
pseudo-stock grouped-binomial projection.

The public release does not contain the full covariance, occupation influence,
common multiplier matrix, ordered full designs, fitted dynamic probabilities,
or full static parameter vectors. The runner must not synthesize them. Therefore
paired inference, covariance/influence reparameterization, numerical Wald
invariance, and nesting/projection remain implemented but unrun.

Y04 defines both original-reference equality and within-block equality for the
full preperiod, 2017Q1--2019Q4, 2021Q1--2022Q3, and the original preperiod
excluding 2020Q2--2020Q4. Rank-aware Wald utilities use restricted-covariance
rank as feasible degrees of freedom using one scale-relative spectral cutoff.
A joint Wald result is blocked if the restricted target has a material
component outside the retained covariance range; that component is never
silently projected away and presented as the full-null statistic.
Y05 defines simultaneous common-draw, true leave-one-quarter, persistent-level,
elapsed-quarter drift, and seasonal diagnostics. Each leave-one-quarter null is
rebuilt on the remaining labels, including selection of a new within-block
anchor when needed. A leave-out Wald change is not an additive contribution,
dates do not identify a COVID mechanism, and no window may be selected after
inspecting p-values.

N04's six A1-certified post-2020/seasonality fits do not complete Y08. Y08 still
requires 16 fresh onset fits (eight November 2022--June 2023 starts times two
structures), with same-objective numerical certification. T05 still requires
two through-December-2024 fits, also same-objective certified with fixed
preperiod labels. The dependency map's `complete_onset_and_seasonality` label
does not establish those missing fits.
