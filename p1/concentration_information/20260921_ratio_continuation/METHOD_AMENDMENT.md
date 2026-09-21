# Proposed amendment: conservative cross-group ratio-contrast projection

Date: 2026-09-21. Status: **`PROPOSED_NOT_FROZEN / SYNTHETIC_ONLY`**. This
new utility adds a deliberately conservative projection of a caller-supplied
joint four-coefficient confidence region. It does not replace the reviewed V2
estimator, resolve `HOLD_METHOD`, establish calibration, or make any empirical,
causal, data-readiness, or production-inference claim.

## Scope and required inputs

Write `theta = (N_TOP, k_TOP, N_REST, k_REST)`. The caller must supply all of:

- `theta_hat` in that exact order;
- a finite symmetric PSD 4x4 covariance matrix `V`, including any shared-news
  cross-group covariance it intends to use;
- a positive `joint_critical_squared = q` calibrated for **one simultaneous
  four-coefficient region**; and
- a nonempty caller-provided calibration-status declaration.

There is no default 1.96, no claim that normal 95% marginal intervals provide a
joint threshold, and no automatic calibration from a bootstrap, clustering, or
the supplied covariance. The optional score helper accepts already-formed
event-level joint coefficient influence sums (including any bread transform) and
retains their cross-products, but labels empirical covariance construction
`NOT_ESTIMATED_EMPIRICAL_PIPELINE_ABSENT`.

## Conservative construction

The stipulated joint Wald region is

`E = { theta_hat + A u : ||u||^2 <= q },  A A' = V`.

For every coordinate, `E` lies within
`theta_hat_i +/- sqrt(q V_ii)`. The code forms this axis-aligned box `B`; hence
`E subset B`, including when `V` is singular (rank-specific calibration remains
external). If both denominator ranges avoid zero, it evaluates each ratio over
the four numerator/denominator box corners and returns

`[min(N_TOP/k_TOP) - max(N_REST/k_REST), max(N_TOP/k_TOP) - min(N_REST/k_REST)]`.

This contains the image of `E` under `N_TOP/k_TOP - N_REST/k_REST`. Conditional
on valid simultaneous coverage of `E` and nonzero true denominators, it thus has
at least that coverage by set inclusion. It is an **outer bound**, not exact
Fieller inversion for a difference of ratios. While off-diagonal covariance is
preserved in the caller-supplied joint region/interface, it does not tighten the
axis-aligned-box result and must not be claimed to do so.

If either denominator coordinate range touches zero, the result is `ALL_REAL`.
That is a conservative fallback, not a finding that the exact projection is all
real. A true zero denominator makes the ratio undefined, not zero.

## Explicit exclusions

This method never subtracts ordinary marginal ratio confidence intervals, uses
no finite grid, reads no remote or empirical data, and does not estimate a
covariance, choose clusters, solve shared-news dependence, validate few-cluster
or overlap corrections, or calibrate `q`. Therefore it cannot remove the prior
method hold or support an estimator switch, final parameter freeze, causal
interpretation, or real-data inference.

## Synthetic reproduction

From `20260921_ratio_continuation/method/` run:

```bash
python3 synthetic_tests.py
python3 -m py_compile estimator.py synthetic_tests.py
shasum -a 256 estimator.py synthetic_tests.py SYNTHETIC_TEST_RESULTS.json
```

The tests exercise correlated ellipsoid point enclosure, negative bounded
denominators, weak denominator fallback, singular PSD support,
nonfinite/non-PSD rejection, a generic joint event-score covariance interface,
and groupwise common-unit scaling invariance.

Numerical validation is done in per-coefficient correlation units: negative
variances and nonzero covariance on a zero-variance coordinate are rejected,
then symmetry and PSD are checked after congruence normalization by the positive
coordinate standard deviations. This is invariant to heterogeneous coefficient
unit changes and avoids overflow from a global covariance scale. It is a
floating-point input guard, not a covariance-calibration claim.
