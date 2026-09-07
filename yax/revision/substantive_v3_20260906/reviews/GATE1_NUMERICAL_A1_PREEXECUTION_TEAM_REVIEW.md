# Gate 1 numerical amendment A1: pre-execution team review

Status: **same-team pre-execution review; not independent replication and not
evidence that any full-data model passes**

The review inspected the owner authorization, historical blocked artifacts,
scientific-target fingerprint, A1 specification, numerical runner and tests,
transfer normalizer, target-level dependency map, and dependency guard. No
protected post-period outcome was opened and no A1 production model was run.

## Review disposition

The reviewed implementation remains on the original continuous-stock grouped
binomial likelihood, authenticated cells, treatment definitions, support,
nuisance column space, normalization, and targets. It changes numerical paths
and certification evidence only. The historical blocked run and parent
numerical specification have no tracked modifications.

The review found and required correction of the following fail-open or
incomplete-evidence paths before execution:

1. L-BFGS-B contradiction evidence is now binding when it reveals a materially
   lower independently evaluated objective, a cross-evaluator derivative
   discrepancy, or a stationary declared-target contradiction. The diagnostic
   must actually execute for each model, but its own nonconvergence is not an
   automatic veto.
2. Both final mandatory candidates separately undergo raw and diagonally
   scaled full-Hessian rank/positive-definiteness checks. Sparse extreme
   eigenvalues retain residual norms and conservative bounds; a Ritz estimate
   alone cannot pass the `1e-10` relative threshold.
3. Dynamic reparameterization now reconstructs every original event
   coefficient as an explicit linear functional. Original-coordinate
   componentwise agreement, Newton/adjoint corrections, and recession
   invariance are binding; transformed-basis comparisons remain diagnostic.
4. The independent Newton/IRLS path retains implementation-owned termination
   codes, exact evaluation counts, final metrics, and trajectories on both
   success and failure. Conditional fitted-stock means, normalized means, and
   linear-predictor differences are reported.
5. The caller-supplied cell receipt must match the byte-pinned retained parent
   receipt. The parent blocked MODEL_AUDIT and its eleven blocked
   classifications are also byte- and semantics-checked.
6. The numerical-only transfer accepts only the declared byte-pinned parent
   cells/target artifacts plus the new A1 numerical receipt. A partial blocked
   suite may transfer model evidence but cannot be represented as a suite-wide
   PASS.
7. Downstream release validates nested comparison, evaluator, Hessian, and
   L-BFGS evidence rather than trusting summary booleans. It binds the exact
   A1 spec and runner, the complete original treatment family, the 38 Q5 event
   targets and 23 pretrend targets, and the pre-outcome dependency-map bytes at
   the authorization commit.
8. Requirement-level consumers use AND dependencies for pooled/conditioned,
   static/dynamic, and seasonal comparisons; an atomic target cannot release a
   multi-model requirement early.

## Verification performed

- Owner authorization copy is byte-identical to the supplied A1 document.
- A1 scientific-target payload and fingerprint equal the immutable parent.
- A1 specification self-ID, runner hash, and synthetic-test hash are checked by
  executable tests.
- The retained parent cells and blocked numerical artifacts are hash-bound;
  the old specification and preserved blocked run have no tracked diff.
- Focused numerical, transfer, authorization, and dependency tests pass.
- Full repository suite: `1107 passed, 3 skipped, 17 subtests passed`.
- `git diff --check` passes.

## Remaining evidence boundary

This review certifies implementation readiness only. Model certification,
actual diagnostics, the complete 11-model status table, and target-specific
downstream release remain pending the fresh authenticated SCC execution. Any
failed model remains blocked, and overall Gate 1 remains blocked unless all 11
models pass the unchanged final criteria.
