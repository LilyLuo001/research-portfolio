# Gate 4 ACS pre-execution audit

Date: 2026-09-08 Asia/Shanghai

Status: **implemented and locally tested; public-data execution not yet run**.
No ACS outcome was opened while writing or correcting this package.

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

## Local evidence

- Focused unit tests: 13 passed.
- A reduced-replicate synthetic end-to-end producer run completed and its
  independent validator passed all 15 checks.
- Python byte compilation and `git diff --check` passed.
- The full repository suite passed: 1,493 tests, 3 skips, and 26 subtests.

This audit is pre-result evidence only. It is not an execution receipt,
empirical result, or independent review.
