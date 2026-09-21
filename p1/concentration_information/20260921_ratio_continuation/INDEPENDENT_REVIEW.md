# Independent finite review

Date: 2026-09-21. Final implementation disposition:
**`HOLD_IMPLEMENTATION_AFTER_TWO_REPAIR_ROUNDS`**. This supersedes the
provisional limited PASS issued before the final proof-level PSD check. The
mathematical outer-enclosure proposal is sound only conditional on an actually
valid joint region; the retained implementation does not enforce that premise
for every accepted input. Overall research status remains
`HOLD_DATA + HOLD_METHOD; HOLD_CONTRIBUTION_AND_EMPIRICAL_VALIDATION`.

This review was limited to the continuation scope, mathematical amendment,
local implementation, synthetic outputs, locator receipt, and the preserved
prior readiness package. It read no financial values, quotes, returns,
outcomes, licensed rows, or new remote data. Requested Sol/high routing was
accepted, but backend model/effort telemetry and token use are `NOT_OBSERVED`.

## Mathematical-scope finding

For a genuine PSD covariance `V` with `A A' = V`, every point
`theta_hat + A u`, `||u||^2 <= q`, satisfies
`|(A u)_i| <= sqrt(q V_ii)`. The coordinate box therefore contains the one
joint four-coefficient ellipsoid. When both denominator ranges exclude zero,
corner interval arithmetic encloses the image of that box under
`N_TOP/k_TOP - N_REST/k_REST`, and hence encloses the ellipsoid image.
Conditional on the one joint region covering the true four coefficients and
the true denominators being nonzero, set inclusion gives at least the joint
region's coverage.

This is a conservative outer projection, not exact Fieller inversion for a
difference of ratios and not subtraction of two marginal confidence intervals.
Off-diagonal covariance does not tighten this axis-aligned box; tests with the
same diagonal and different dependence return the same endpoints. `ALL_REAL`
when a denominator box touches zero is a safe fallback, not a claim that the
exact projection is all real. A true zero denominator leaves the ratio
undefined.

The interface correctly requires a positive caller-supplied squared joint
critical value and a nonempty calibration declaration. A declaration is not
evidence of valid calibration. Neither the documents nor code estimate or
validate the empirical cross-group covariance, shared-news dependence,
few-cluster correction, overlap correction, rank-specific threshold, or `q`.

## Independent implementation evidence

The independent suite exercises randomized containment for full-rank and
singular ellipsoid support points; negative and zero-touching denominators;
zero covariance; groupwise unit scaling; same-diagonal dependence; required
`q` and calibration state; nonfinite, negative-diagonal, zero-variance,
asymmetric, and heterogeneous-scale covariance inputs; extreme finite
arithmetic; and the supplied-score covariance helper.

The score helper reproduces `multiplier * scores.T @ scores`, preserves joint
cross-products, and labels its output
`NOT_ESTIMATED_EMPIRICAL_PIPELINE_ABSENT`. That is valid only when the caller
has already supplied the four-coefficient event influence sums, including any
bread transform. It is not an empirical covariance pipeline.

Two bounded repair rounds addressed the initially reproducible defects:

1. A unit-dependent global scale floor accepted a tiny negative variance and
   tiny asymmetry, while equivalent rescaled inputs were rejected. Extreme
   finite inputs could also fail inside eigensystem arithmetic or emit an
   infinite bounded interval.
2. Global maximum normalization still allowed an invalid small covariance
   block or asymmetry to be hidden by another group's units. Per-coordinate
   correlation normalization, zero-variance consistency checks, and finite
   arithmetic guards closed those fixtures.

Before the decisive final case was added, eight engineering scenarios and
fourteen independent tests passed under warnings-as-errors, and compilation
completed. The final independent command is:

```text
python3 -W error -m pytest -p no:cacheprovider -q reviewer/test_ratio_adversarial.py
-> 14 passed, 1 failed
```

The failure is
`test_near_indefinite_matrix_is_not_treated_as_an_existing_ellipsoid`.
With `V = I` except `V[0,1] = V[1,0] = 1 + 5e-11`, the minimum eigenvalue is
approximately `-5.0000004e-11`. The validator accepts it under its `-1e-10`
correlation-scale tolerance and returns the original, uncorrected matrix; the
projection then emits a `BOUNDED_INTERVAL`. No real `A` can satisfy `A A' = V`
for that indefinite `V`, so the implementation accepts an input for which its
stated ellipsoid does not exist. The same general tolerance approach can accept
slight asymmetry without returning a symmetrized matrix.

Accordingly, the final paragraph of `METHOD_AMENDMENT.md` describes the
intended scale-consistent validation, but is insufficient as implemented: the
correlation normalization fixes heterogeneous units, while the tolerance plus
return of the original matrix does not guarantee an actually symmetric PSD
matrix. There is no documented repair/projection policy redefining accepted
`V`. The authorized two-repair limit was reached, so no third implementation
change was requested or made. The failing regression is retained for handoff.

## Source-locator and historical-integrity findings

The locator receipt accurately distinguishes connectivity from provenance:
`ssh ... true` exited 0, but the approved local records documented no exact SCC
path, publisher archive identifier, distribution archive identifier, or other
retrievable historical view. No SCC directory search or row query occurred.
This is not evidence that SCC contains no useful metadata, and no six-event
clock status changed.

Additional public release/archive URLs for the same six announcements would
relax the earlier no-new-URL boundary. The recorded permission question remains
unanswered, and no such search is authorized or reported as completed.

All 24 stage-local entries in the prior readiness review's hash manifest still
match. Its single external `../README.md` entry changed intentionally to index
this continuation; the old reviewed readiness files themselves were not
modified.

## Final decision

The conditional set-inclusion argument remains a proposed mathematical
specification. The current code is **not** a validated implementation of that
specification and must not be used for empirical inference. It does not remove
the prior method or data holds, establish exact identification, calibrate a
joint region, or support any effect, power, causal, or production conclusion.

Final reviewed SHA-256 values are recorded in
`reviewer/FINAL_HASHES.json`; that manifest omits only its own hash.
