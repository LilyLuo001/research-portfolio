# Gate 4 ACS pre-execution audit

Date: 2026-09-08 Asia/Shanghai

Status: **historical pre-execution audit, with failed-execution corrections
recorded below; no ACS result has been published**.

No ACS outcome was opened when the original package and its estimands were
written. Public-data execution has since begun. Failed attempts are retained
below rather than relabeled as pre-execution work.

The first protected execution stopped before reading any outcome row because
the runner requested a housing-record type field from the person CSV. The
runner now uses the vintage-specific person relationship field to identify
group-quarters residents. This changes only the household-only sensitivity's
input construction; the populations, exposure definitions, estimands, support,
and inference rules are unchanged.

The corrected job then stopped on released negative replicate-weight values.
Official ACS accuracy documentation confirms that negative SDR replicate
weights are valid. The input guard now requires finite replicate weights and a
positive full person weight, preserves the signed replicate values, and records
their incidence. No estimate from either failed attempt was produced.

A later attempt completed public aggregation and full-weight fitting but
stopped on the first nonlinear replicate refit: the shared ordinary-binomial
routine rejected an aggregate made negative by valid signed replicate weights.
No output directory or estimate was published, and no transient coefficient
was inspected. The correction is confined to replicate-weight numerics. It
retains the signed values and all fixed estimating rows, solves the unchanged
weighted grouped-logit score from the certified full-weight solution, and
requires score and local-curvature certificates. The main estimator, age
groups, treatment, support, calendars, outcomes and SDR formula do not change.

The first run of that signed-score implementation stopped before publishing an
output because its initializer tried to reconstruct the full-weight nuisance
surface on cells with zero full-weight stock. The shared estimator deliberately
stores a neutral fitted probability on such unused cells; that placeholder is
not part of the fitted linear predictor and need not be additive in the fixed
effects. The corrected initializer reconstructs the certified full-weight
nuisance effects only on the estimator's positive-stock rows, then uses those
effects to initialize every replicate row. A regression test now sets a
full-weight cell to zero, makes it positive in a replicate, and verifies both
pooled and family-year coefficients against an independent explicit-dummy
Newton solution. No empirical output or transient coefficient from the failed
run was published or inspected. The estimand, estimating rows in each
replicate, score, and final acceptance tolerances remain unchanged.

## Scientific checks completed

- The BCC comparison target is a Q5-minus-Q1 difference in 2022-to-2024
  employment growth factors for ages 22--25, not a log-regression coefficient.
- The sequential population definitions, annual endpoints, standard 2020
  omission, occupation-vintage break, 80 replicate weights, and official
  successive-difference factor are explicit.
- BCC's unavailable exhaustive occupation membership is not reconstructed from
  memory or described as public. The three declared groupings remain visibly
  non-exact analogues.
- The 2017 occupation bridge splits full and replicate weights by the same
  official route shares and never renormalizes a partial surviving route.
- Benchmark and model survey variances perturb one year and one replicate at a
  time. Paired variances difference estimates before applying the SDR sum, so
  common replicate covariance is preserved.
- The six-year annual model and the separate subframe-cycle sensitivity exclude
  2022 as a transition year. Their cross-year survey variance is labeled a
  block-independent approximation, not exact multi-year design inference.
- Fixed support and exposure assignments do not change across pooled and
  family-year models or survey replicates. Any numerical fit that drops a
  separated cell or fixed-effect group is refused.
- Occupation-shock inference uses two-point Rademacher multipliers; the
  22-family inference uses the declared six-point Webb support. These are
  reported separately from ACS person-sampling uncertainty.

## Result-relevant implementation defect corrected before execution

The first draft tested for a nonexistent `webb_six_point_support` helper and
therefore would have silently used Rademacher draws for the family-level
intervals. The implementation now draws directly from the authenticated
six-point support exposed by the shared inference engine, and the output labels
the two multiplier distributions. No outcome had been read and no retained
result existed when this was corrected.

## Local evidence before the first execution

- Focused unit tests: 13 passed.
- A reduced-replicate synthetic end-to-end producer run completed and its
  independent validator passed all 15 checks.
- Python byte compilation and `git diff --check` passed.
- The full repository suite passed: 1,493 tests, 3 skips, and 26 subtests.

This audit is pre-result evidence only. It is not an execution receipt,
empirical result, or independent review.

## Post-attempt numerical evidence

The signed-score implementation is checked against the ordinary estimator on
nonnegative weights and against a separate explicit-dummy Newton solution on
synthetic signed cells, under both pooled and family-year structures. The
initializer is also checked when a zero-stock full-weight cell becomes active
under a replicate weight. The
independent output validator recomputes every SDR variance and paired variance
and rejects any replicate fit with a score over `1e-8` or nonpositive certified
local curvature. Passing public-data evidence remains outstanding until the
full job completes.
