# Gate 1 numerical existence and convergence audit

This directory implements requirements N01--N03 without changing the YAX
estimand. It audits the exact frequency-weighted grouped-binomial likelihood,
including genuine one-sided cells and both fixed-effect partitions.

`ANALYSIS_SPEC.json` is the pre-result numerical contract. The production cell
builder is `../gate1_cells/run_gate1_cells.py`; there is no second or substitute
builder in this directory. A run requires the byte-locked canonical V2 spec, a
fresh balanced occupation-month cell leaf, and its authenticated receipt.

## Authentication and publication

The consumer rejects a receipt unless it binds all of the following:

- canonical and numerical-spec identifiers and byte hashes;
- the aggregate-cell byte hash and complete canonical source-hash registry;
- every exposure/computerization/rule-B/bridge/authorization lookup hash;
- the exact producer-spec self-ID and byte hash, builder hash, and aggregate
  transitive-code fingerprint;
- the declared SCC runtime payload and environment lock, exact sanitized
  command template, committed Git tree, required ancestry, clean worktree, and
  live files equal to their committed blobs;
- the canonical six-field raw-data router, physical-record identities,
  per-source and total route-mass reconciliation, and weight-once stock totals;
- fixed-membership support and the per-occupation fingerprint of
  `(occ_code, family, beta_quintile, webb_z)`;
- strict four-digit occupation codes, the 468-occupation by 114-month
  balanced-grid counts, and one survey-weight application; and
- a false private-path flag plus a receipt that contains no resolved private
  path.

The numerical program is also equality-locked to the dedicated SCC runtime
(CPython 3.13.8, NumPy 2.5.1, pandas 3.0.3, SciPy 1.16.2, pytest 9.1.1,
x86_64/glibc 2.28). The compute-node kernel is recorded but not equality-locked.
Every staged output—not only the receipt—is scanned for private paths and
credential forms. A sanitation failure discards the private staging leaf.
Every blocked run exits nonzero; there is no report-only override.

Both the cell builder and this audit require a fresh, named output leaf outside
the Git repository. They refuse an existing leaf, a repository destination, or
an input/output overlap. Artifacts are written to a private same-parent staging
directory and atomically published only when complete. Persisted commands use
placeholders, never resolved SCC or workstation paths.

Publication attempts kernel no-replace first. If the mounted filesystem
explicitly rejects that primitive, the already-open exclusive sibling lock is
revalidated and the runner performs an ordinary same-parent atomic rename only
after immediate target-absence and staging-identity checks. Before publication,
the receipt discloses both permitted paths without claiming the not-yet-observed
backend. The runner attempts to record the actual postcommit method in
sanitized scheduler stdout; an output-stream failure after commit is reported
conservatively when possible and cannot invalidate the published leaf. Both
records state that the fallback does not provide kernel no-replace and retains
a bounded but uneliminated noncooperating same-user check-to-rename window.

## Existence logic

No pseudocount, penalty, probability clip, minimum-count rule, or selective
sparse-cell deletion is allowed. Zero-total cells remain in input accounting
and have zero likelihood contribution. A fixed-effect group whose remaining
observations contain only young or only older stock is profiled to its
extended-likelihood boundary, with every affected row recorded and cascading
boundaries iterated.

On the remaining face, a linear program classifies complete or quasi
separation. Its HiGHS candidate is independently checked against every scaled
equality, inequality, bound, and objective residual. Separate finite
minimum-infinity-norm epigraph LPs fix each target at +1 and -1. This directly
tests whether a target can move; a certified zero-gain lineality direction is
also target-moving, not evidence of a finite coefficient. A target-moving
direction blocks the model. A proven
target-invariant nuisance recession is resolved by profiling its strict-margin
rows and repeating the face audit. Nonfocal rank dependence may be replaced by
an exact pivoted-QR column-space basis only when the original focal coordinate
is rank identified and retained.

Every model must exactly match its submitted implementation in regressor
values, semantic labels, and both fixed-effect partitions. This adjudicated one
earlier discrepancy: the locked submitted dynamics code removes December 2022,
so the audit does too.

The registry contains eleven exact designs: pooled, family-post, and
family-month; unconditioned and family-month dynamics; unconditioned and
family-month post-2020 models; and both conditioning variants of the
quintile-seasonal and occupation-seasonal models. The family-post omitted
family uses all-analysis-period stock, matching submitted code. For each
dynamic model, the primary scalar is the equal-observed-calendar-month-weighted
post-2022 Q5-versus-Q1 functional. The audit separately requires complete
construction, rank, recession invariance, and two-solver agreement for all 38
reported Q5 event coefficients and full rank for the 23-dimensional joint
pretrend test.

For a finite face, unclipped sparse L-BFGS-B and trust-ncg solve the same exact
objective. The audit compares the focal coefficient, all slopes, fitted means,
all reported dynamic Q5 targets, objective, gradients, and a fixed-target
likelihood profile. Optimizer termination is not acceptance evidence. Each
untouched candidate must also pass original-coordinate score checks and a
sparse full-Hessian certificate: a refined primal Newton solve, a complete
dyadic raw-likelihood-decrease check, and independent adjoint solves for every
reported target. The adjoints must agree with the primal target corrections
and satisfy the existing coefficient tolerance. This catches weak joint
directions without converting the 5,000--8,000-column production Hessians to
dense matrices. It reports raw
and diagonally scaled spectra of the full nuisance-plus-treatment Hessian both
at total/4 weights and at fitted probabilities. The inherited clipped solver
is only a disclosed comparator.

No licensed microdata or protected aggregate cells are committed here. The 68
implementation tests (plus 17 unittest subtests) are synthetic or use public
byte-locked submitted code.

## Production invocation

Build the cells first using `../gate1_cells/README.md`. Then run from the YAX
repository root, with a new outside-repository output leaf:

```sh
<YAX_PYTHON_BIN> -I yax/revision/substantive_v3_20260906/numerical_existence/run_numerical_existence_audit.py \
  --canonical-spec <YAX_REPO_ROOT>/yax/revision/substantive_v3_20260906/contracts/specs/canonical_baseline_reproduction_v2.json \
  --analysis-spec <YAX_REPO_ROOT>/yax/revision/substantive_v3_20260906/numerical_existence/ANALYSIS_SPEC.json \
  --cells '<YAX_GATE1_CELLS_LEAF>/aggregate_cells.csv' \
  --cells-receipt '<YAX_GATE1_CELLS_LEAF>/EXECUTION_RECEIPT.json' \
  --legacy-engine <YAX_REPO_ROOT>/dax/memo/power_calcs/young_relative_employment_power.py \
  --output-parent '<YAX_V3_RUN_ROOT>'
```

The numerical runner derives its unique output leaf from the numeric SGE
`JOB_ID`; callers cannot select or overwrite a result leaf.
