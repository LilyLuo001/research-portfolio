# Numerical amendment A1

Status: **owner authorized; pre-execution numerical implementation amendment**

Owner authorization is preserved byte-for-byte at
`revision_inputs/GATE1_NUMERICAL_ADJUDICATION_A1.md` (SHA-256
`ff4963e66940741abc8a4eda87fd9050c51cae5cedfabb3ae1ab42c21f5836a9`).
This record does not certify a coefficient or alter the preserved blocked run.

## Historical record retained

The A1 parent is numerical specification
`yaxnumspec_v1_4c784c23726ad5ce258af6151afdf83e1e05efe6d1086d43007e5d06a5843991`.
Its fresh execution remains unchanged under
`runs/gate1_numerical_blocked_b9a7dd1/`. All 11 historical model
classifications remain blocked.

The old per-solver metrics are transcribed without re-estimation in
`A1_ORIGINAL_SOLVER_METRICS.csv`; the pairwise target-vector and fitted-value
comparisons are in `A1_ORIGINAL_SOLVER_COMPARISON.csv`.

## Observed failure mechanism

All 11 L-BFGS-B fits returned SciPy status 0 with the termination message
`RELATIVE REDUCTION OF F <= FACTR*EPSMCH`, but all 11 failed the unchanged
external standardized-score threshold of `1e-4`. The normalized gradient
threshold was not the binding check. Two dynamic L-BFGS-B fits also exceeded
the `1e-6` maximum declared-target Newton-correction threshold.

Trust-ncg returned SciPy status 2 (`A bad approximation caused failure to
predict improvement`) in every model. Ten candidates nevertheless passed the
external original-coordinate certificate, showing why solver status is not an
acceptance rule. `seasonal_quintile_month_unconditioned` stopped with a
standardized-score residual of approximately `8.79e-4`, above `1e-4`, and did
not pass. The two original solvers nevertheless agreed closely on its objective
and fitted probabilities; that is diagnostic evidence of a common basin, not a
certificate.

The old run therefore establishes premature solver stopping relative to the
external certificate. It does not by itself establish that the objective,
analytic derivatives, or final target are correct.

## Unchanged scientific identity

A1 leaves unchanged:

- authenticated cells and their digest;
- eligibility, occupation support, assignments, exposure scales, age groups,
  calendar, transition treatment, and weights;
- the continuous-stock grouped-binomial likelihood, nuisance column spaces,
  normalizations, rank reduction, boundary profiling, and separation rules;
- all 11 model definitions and their complete target vectors;
- the interpretation of the coefficient and every downstream scientific
  estimand.

The new full numerical specification is `ANALYSIS_SPEC_A1.json`, ID
`yaxnumspec_v1_e0b71ceb9f1d0daf501300114234121c087d1ee145a401107fbaa2caf6df18a4`
and SHA-256
`7d5798546004e5d6804a1f1440158e4f168eb1adf54e692f93bf60df00b47cca`.
Its explicit scientific-target fingerprint matches the A1 parent while its
algorithm, implementation hashes, and corroboration rule receive the new full
identity.

## Uniform A1 algorithms

Every model will run the following three visible paths.

1. **Primary candidate:** trust-ncg from the declared zero start in the existing
   exact invertible design-only coordinates. If and only if the untouched
   trust-ncg candidate fails the unchanged external certificate, a deterministic
   damped full-Hessian Newton refinement of that candidate is permitted. The
   unpolished and polished metrics are both retained.
2. **Independent reference:** a standalone damped sparse Newton/IRLS path from
   its own zero-based initialization. It evaluates the algebraically equivalent
   loss as young-stock softplus of minus the predictor plus older-stock
   softplus of the predictor, with independently written score and Hessian
   calculations. It never starts from a trust-ncg or L-BFGS-B result.
3. **Historical diagnostic:** L-BFGS-B is run and reported under its existing
   settings, but its failure is not an automatic veto. A materially better
   independently evaluated objective, unexplained derivative discrepancy, or
   unresolved target contradiction remains blocking evidence.

The diagnostic contradiction rule is fixed before execution. The L-BFGS-B
candidate is evaluated by both objective/derivative implementations. It blocks
if its objective per total is lower than the better mandatory candidate by more
than `1e-10`, or if the two evaluators fail their unchanged objective, score,
Hessian-product, probability, or directional-derivative checks at that
candidate. If and only if L-BFGS-B independently passes the unchanged score and
full-Hessian stationarity certificate, any declared-target difference from the
zero-start reference above `1e-6` also blocks. A nonstationary L-BFGS-B
coefficient is retained but is not treated as a substantive contradiction.

The independent evaluator must be checked against the canonical evaluator at
declared deterministic parameter vectors and by directional finite-difference
score and Hessian-product tests. Both final candidates must be cross-evaluated
under both independently coded objective, score, and Hessian implementations.
The reference path may share immutable core/design bytes and the sparse linear
algebra library, but it may not call the canonical objective/derivative builder,
the primary-polish routine, or use any primary or L-BFGS-B solution as its
initialization. Numerical damping changes steps, not the objective. No penalty,
prior, pseudocount, probability clipping, finite nuisance cap, sparse-row
deletion, or scientific-data change is allowed.

Each numerical path must retain its implementation-owned termination code and
message, exact objective/score/Hessian/line-search evaluation counts, final
metrics, and trajectory on success or failure. L-BFGS-B must execute for every
model; an absent or exceptional diagnostic run blocks that model even though
mere nonconvergence does not. This makes a failed seasonal fit and every other
failed candidate inspectable rather than silently replaceable.

The immutable specification binds identical active-row masks, design-column
order and labels, normalization references, target matrices, and core-row order
for the two paths by digest. It also predeclares the external-certificate polish
trigger, damping and line-search grid, iteration budget, no-progress disposition,
and mandatory rerun of the untouched external certificate after any polish.

Fixed-target nuisance profiles use the independently converged reference path;
they do not inherit the historical L-BFGS-B stopping failure.

## Final acceptance rule

For each model separately, both the primary candidate and independent reference
must pass the original-coordinate external certificate. They must then agree
under the existing final thresholds:

| check | unchanged threshold |
|---|---:|
| normalized gradient infinity norm | `1e-7` |
| standardized score maximum | `1e-4` |
| objective difference per total stock | `1e-10` |
| fitted-probability maximum difference | `1e-7` |
| focal and every declared target-vector difference | `1e-6` |
| every identified treatment-vector coefficient difference | `1e-6` |
| raw likelihood rise/decrement diagnostic | `1e-4` |
| rank/conditioning relative tolerance | `1e-10` |

The comparison records the full identified treatment vector, full declared
event-target vector, core fitted probabilities, objective, normalized linear
predictor/fitted-mean agreement, external target corrections, and curvature
solve residuals. Maximum absolute agreement across all 190 identified treatment
coefficients is binding for each dynamic model; recording only the 38 reported
Q5 event targets is insufficient. Because the nuisance normalization is
identical, nuisance coordinate differences are reported as diagnostics;
fitted-value agreement is the invariant check.

At both mandatory candidates, the full normalized nuisance-plus-treatment
fitted Hessian must pass the raw and diagonally scaled extreme-spectrum audits.
Sparse eigenvalue calculations retain eigenpair residuals and conservative
bounds, and positive definiteness passes only when the certified smallest lower
bound exceeds the declared relative threshold against the certified largest
upper bound. The recession/lineality audit likewise covers every reconstructed
original treatment functional after any exact reparameterization; transformed-
basis checks are diagnostics, not substitutes for original-coordinate checks.

All five fixed-target profile points use the independent reference path for
their noncenter nuisance fits and must pass their KKT and likelihood-rise checks.
The fitted-information/Hessian, linear-solve/backward-error, primal/adjoint, and
dynamic target-matrix checks must also pass. A model that fails any required
check or has an unresolved cross-implementation contradiction remains blocked;
the procedure may not select the preferred coefficient. No suite-wide PASS may
be claimed unless all 11 pass; certified models may release only the consumers
named in the target-level dependency map.

The amended run may reuse only the authenticated parent cells with SHA-256
`5e10dabf78b1b1cbc8b6aa9f8745435224b9fe3cb078e73cd9d9e27a9c292717`.
The caller-supplied cell receipt must match the retained parent receipt
byte-for-byte at SHA-256
`9cd1e5fe999dcdff124b0ab413be13106928f42b55951a99c1893e263395b51a`.
The preserved blocked numerical receipt, model registry, status, and model
classifications remain historical evidence and are not rewritten by A1.

## Old-to-new numerical specification diff

| field | historical specification | A1 specification |
|---|---|---|
| mandatory pair | L-BFGS-B plus trust-ncg | trust-ncg path plus standalone damped sparse Newton/IRLS reference |
| L-BFGS-B role | indispensable passing solver | visible diagnostic and contradiction check |
| trust failure handling | retain untouched final candidate | retain metrics; uniformly permit exact damped-Newton refinement when external certificate fails |
| independent objective check | common evaluator only | algebraically equivalent independently coded evaluator plus derivative/Hessian tests |
| fixed-target profile solver | L-BFGS-B | standalone reference Newton/IRLS |
| scientific inputs/estimand | parent definition | unchanged |
| final thresholds | parent values | unchanged |

Any modification outside this table requires another owner decision.
