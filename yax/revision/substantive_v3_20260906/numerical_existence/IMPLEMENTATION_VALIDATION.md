# N01--N03 implementation validation

Validation date: 2026-09-06 UTC.

This validates the final code and restamped contracts before the fresh SCC
execution. It does not claim that the eleven protected-data models have run.
No licensed microdata or protected aggregate cell was opened locally.

The final suite covers the original likelihood, boundary, separation, rank,
design-parity, dynamic-target, authentication, and atomic-publication checks.
It additionally verifies:

- design-only `p=0.5` diagonal coordinates preserve the exact likelihood,
  fitted probabilities, original-coordinate coefficients, score, and Hessian
  products;
- neither SciPy success nor a stopping message can override the declared
  original-coordinate score and sparse full-Hessian acceptance checks;
- the L-BFGS-B-only Fisher-scoring start and trust-ncg zero start remain
  independent, and both recover a deterministic nearly collinear target that
  previously produced a false zero solution;
- a complete 65-point dyadic line search detects the attainable raw-likelihood
  improvement rather than accepting the first nonincrease;
- refined sparse primal and declared-target adjoint solves agree, retain the
  unrelaxed backward-error tolerance, and catch a mocked solver that silently
  drops the weak component;
- an 8,000-column synthetic system uses no dense conversion or iterative Ritz
  certificate; and
- the same full-Hessian stationarity logic governs noncenter nuisance profile
  fits.

Observed local result:

```text
python3 -m pytest -q \
  yax/revision/substantive_v3_20260906/numerical_existence/test_numerical_existence_audit.py
....................................................................     [100%]
68 passed, 17 subtests passed
```

The complete cell, target, and numerical producer/consumer suite also passed:

```text
134 passed, 17 subtests passed
```

The production numerical audit remains **UNRUN** until the newly authorized
SCC chain produces and authenticates a fresh cell leaf, passes the exact-target
audit, and executes all eleven models. A blocked model is a numerical finding;
it is not permission to substitute another objective, support rule, penalty,
pseudocount, tolerance, or design.
