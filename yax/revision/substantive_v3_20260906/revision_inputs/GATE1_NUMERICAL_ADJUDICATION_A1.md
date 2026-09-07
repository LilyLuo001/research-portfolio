# Gate 1 decision A1: same-estimator numerical repair and target-specific validation

**Purpose:** This is a proposed owner authorization to send to the execution agent. It becomes an instruction when the project owner sends or approves it. Preparing this document did not run the empirical models, verify a remote Git commit, or certify any coefficient.

**Decision:** Authorize a versioned amendment to the numerical implementation and its named-solver validation rule. Do not waive numerical accuracy, change the scientific estimand, or promote any existing diagnostic coefficient to a validated result. Preserve the blocked run. Execute the repair rather than another proposal-only or integrity-only cycle.

## 1. Evidence and limits of this decision

The five supplied Gate 1 reports establish, as reported by the execution team:

- Cell reconstruction and the exact-target audit passed: 53,352 transport rows, 52,884 canonical static rows, and 51,891 positive-total estimating rows.
- All 11 declared models remain blocked under the existing numerical certificate.
- The same-team review records trust-ncg as numerically valid for 10 models, L-BFGS-B as valid for none, and `seasonal_quintile_month_unconditioned` as invalid under both. It also records target-correction failures in two dynamic L-BFGS-B fits.
- The convergence report records full treatment rank and no detected separation in the retained core of each model. It separately profiles boundary nuisance contributions; this is not a statement that every original nuisance parameter has a finite optimum.
- Dependent Gates 2–5 have not run under V3. The same-team review is not independent scientific replication.

The supplied summaries do not contain the full per-solver metric table, threshold specification, termination traces, or implementation. Therefore, this authorization does not diagnose the underlying cause as premature stopping, bad scaling, a derivative error, or an impossible tolerance. Establish the cause from the actual artifacts.

The original V3 prompt §6.2 explicitly allows better scaling, valid profiling, warm starts, and a second trusted solver for the same objective and column space. Seed requirement N03 says “Use valid profiling or a second solver” and requires comparisons at stated tolerances without hidden estimator changes. Neither requires L-BFGS-B specifically. The later frozen numerical certificate nevertheless remains binding historical evidence and must be superseded transparently, not rewritten.

## 2. Exactly what is authorized

Keep the scientific problem unchanged: authenticated stocks; eligibility and canonical occupation support; exposure assignments and scales; age universes, including the potentially different exposure-construction universe; calendar and transition rules; nuisance column space; identifying restrictions; boundary-likelihood treatment; targets; and the interpretation of the frequency-weighted criterion.

You may change numerical algorithms, starting values, preconditioners, exactly invertible coordinate systems, stable arithmetic, internal convergence settings, and iteration budgets within existing resource permissions. You may multiply the entire objective by one documented positive constant for computation, provided derivatives, checks, and subsequent inference are mapped correctly. These are permissions to calculate the same estimator, not permission to introduce a different estimator.

The following remain prohibited without a separate scientific decision: penalties or priors; pseudocounts; clipping fitted probabilities or stocks to conceal boundary behavior; finite nuisance caps that change the optimum; dropping sparse observations for convenience; changing exposure groups, weights, age ranges, calendar, or controls; and weakening the final numerical acceptance tolerances simply to obtain PASS.

Replacing the named L-BFGS-B prerequisite is authorized. Replacing the requirement for actual numerical corroboration with trust-ncg's success flag is not.

## 3. Preserve the history and separate scientific from numerical identity

Retain the blocked run at commit `b9a7dd1c8703397f1a6686ff9b1a55d4bb67cbde`, its outputs, classifications, numerical specification, and receipts unchanged. Keep it linked to this amendment. Verify the current working commit rather than assuming the status message identifies the current checkout.

Create a new numerical specification and run identifier. Preserve the unchanged scientific/data/treatment fingerprints, while recording any changed implementation identifier. Where the existing full specification ID includes solver details, issue a new full ID and an explicit unchanged-scientific-target comparison; do not claim byte-identical specifications.

Do not edit the immutable requirements seed. Annotate the working ledger with this authorization and maintain all 11 models in the declared registry. Reuse existing dependency and integrity machinery. This amendment does not call for a new general framework or a second large administrative checklist.

Existing authenticated cells may be reused inside the protected environment after their checksum and dependency bindings are verified. A numerical-only repair does not require reconstructing unchanged microdata inputs. Do not publish restricted cells or microdata or interfere with pre-existing jobs.

## 4. First recover the actual reason each check failed

Read the existing numerical specification, execution receipt, per-solver diagnostics, logs, and code. Produce one compact table covering all 11 models and both original solvers. For each fit report:

- objective definition, constant scaling, data/design hash, optimizer and software version;
- starting-value rule, settings, iteration/evaluation counts, termination code and message;
- objective value under a common evaluation convention;
- original-coordinate score/KKT residual, its exact norm/normalization, and threshold;
- the numerical value and threshold for every failed fitted-mean, full-Hessian, Newton-correction, and target-profile check;
- full target-vector disagreement, not just the Q5 coefficient or average dynamic target;
- any active bound, boundary profiling, component normalization, or rank reduction.

Do not infer that `success=True` means the independent certificate passed or that `success=False` disproves existence. Distinguish a solver's own stopping condition from the external certificate.

Determine whether the common L-BFGS-B failures share a cause. Investigate objective-decrease stopping before score convergence, objective/coordinate scaling, line-search precision, derivative discrepancies, under-solving of nuisance parameters, and inconsistent original-scale checks. These are hypotheses, not predetermined diagnoses. Inspect the actual installed implementation and version.

Do not repeat the identical deterministic run. A follow-up run must identify which numerical mechanism changed and why it could resolve the recorded failure.

## 5. Use a uniform replacement benchmark on the same objective

Preferred implementation: retain trust-ncg as one candidate path and add a genuinely distinct same-objective reference, such as damped Newton/IRLS with a checked sparse direct linear solve, or a verified nuisance-profile implementation. Choose the reference for mathematical appropriateness and computational feasibility, not because it reproduces a desired coefficient.

The reference must use the original continuous weighted stocks and a correct likelihood. A generic GLM wrapper is not automatically equivalent: verify its frequency-weight convention, offsets, constraints, separation handling, and estimation criterion. Correct numerical damping of optimization steps is permissible; adding a penalty to the fitted objective is not.

Declare the primary/reference algorithms, coordinate mappings, starts, settings, budgets, and acceptance checks before running the amended validation suite. Test small synthetic examples with finite, boundary, rank-deficient, and nearly collinear designs. Use an independently specified start for the reference fit. Warm-start polishing may supplement this but cannot alone constitute independent corroboration.

For a model to pass, require independently corroborated solutions satisfying the same final numerical accuracy standard, with agreement in the common objective, core fitted probabilities and conditional means, identified target vector, and the quantities needed for downstream curvature/influence calculations. Compare only identified nuisance combinations after compatible normalizations.

L-BFGS-B remains visible as a diagnostic, but its inability to meet the certificate is no longer an automatic veto if the replacement paths establish the same optimum. Conversely, an L-BFGS-B fit with a materially better objective, a contradictory target, or an unresolved derivative discrepancy cannot be ignored. Resolve the contradiction.

Changing to another optimizer name while reusing an erroneous objective, derivative, or profiling routine does not provide independent verification. Independently evaluate the grouped-stock objective and analytic derivatives and perform appropriate directional derivative/Hessian-product checks.

## 6. Scale computation correctly; do not move the goalposts

On the finite identified core, write

\[
f(\theta)=\sum_i\{T_i\log(1+\exp(\eta_i))-N_{y,i}\eta_i\},\qquad
\eta_i=x_i'\theta+\text{offset}_i.
\]

Use stable equivalent expressions, such as the sum of young and older stock times the corresponding softplus losses, to avoid cancellation for extreme predictors. Do not change the mathematical loss. With correct derivatives,

\[
g=X'(Tp-N_y),\qquad H=X'\operatorname{diag}(Tp(1-p))X.
\]

These identities give a direct implementation check. The negative criterion is convex; full identification and proper handling of boundary directions are still required. A small gradient alone is not enough to establish accurate targets in poorly conditioned directions.

If optimizing \(\widetilde f(z)=f(Az+b)/c\), for fixed positive \(c\) and an invertible mapping on the identified subspace, record

\[
\widetilde g=A'g/c,\qquad \widetilde H=A'HA/c.
\]

Map checks back to the declared original scientific coordinates. A score tolerance of \(\varepsilon\) for \(g\) is not the same tolerance when applied unchanged to \(g/c\). Likewise, do not carry the inverse scaled Hessian into model-based variance calculations without the required correction. Consistent scaling of both bread and score contributions is essential in sandwich calculations.

Internal stopping parameters may be made tighter or changed to facilitate the same final certificate. Retain the existing final acceptance thresholds and units. Report raw and normalized metrics. Do not choose a new pass threshold from the observed residuals or because a coefficient is small relative to its standard error.

If an original acceptance threshold is demonstrably incoherent under its stated units or below an evidenced arithmetic limit, supply the old rule, the error analysis, a proposed mathematically comparable replacement, and its implications for target accuracy. That is a specific additional adjudication request, not permission already granted here to weaken the rule. A correct algebraic unit conversion is not a weakening.

## 7. Validate the identified core, boundary handling, and target accuracy

Verify each nuisance-component normalization. The reports show multiple graph components in some models; disconnected components do not by themselves prove the target is unidentified. Establish that normalizations remove only aliases, not substantive variation.

Check the separation/recession-direction procedure, not merely its Boolean output. Confirm that profiled boundary contributions reach their extended-likelihood supremum without altering finite identified targets. Preserve row accounting that distinguishes both-zero rows, retained one-sided zero observations, and analytically profiled boundary groups. Never describe all these operations as generic sparse-cell deletion.

Recompute full-Hessian or mathematically equivalent Schur-complement quantities using the independently checked fit. Use checked linear solves instead of an unexamined matrix inverse. Report conditioning and solve residuals on the identified subspace.

For a finite-core solution, \(-H^{-1}g\) is a useful local Newton correction. Its projection onto a target indicates local numerical sensitivity; by itself it is not a rigorous global error bound. Combine it with converged independent fitting, valid profile checks or justified curvature/error bounds, and fitted-value agreement. Do not treat a handful of nearby profile evaluations as a theorem about all possible parameters.

For the dynamic models, certify the entire identified coefficient vector and the nuisance-adjusted matrices needed for later event-time covariance and linear functionals. A passing average postperiod coefficient cannot hide offsetting errors in individual quarters. Do not introduce new inferential claims at this gate.

For `seasonal_quintile_month_unconditioned`, neither original solver passed. Investigate its failure separately under the same standard; it cannot inherit validation from a related family-conditioned model or another seasonal specification.

## 8. Re-run the complete declared set; release work by actual dependencies

Apply the amended policy to all 11 registered models and report every disposition. Prioritize the pooled and exact family-month fits and then their dynamic counterparts because they support central comparisons, not because of their signs or significance. Keep the family-post, post-2020, and all seasonal models in the work program.

Numerically verified targets may unlock downstream tasks that actually depend on those targets once the new receipt and dependency checks pass. An unresolved seasonal model must continue to block its own result and any claims requiring that sensitivity, but need not block an unrelated verified baseline accounting or support task.

Before doing this, record the target-level dependency map and update the existing guard accordingly. Do not manually bypass it. Parent requirements and overall completion remain incomplete while required children are unresolved. Report the denominator: for example, “k of 11 numerically certified; remaining models blocked,” never “Gate 1 PASS” for an incomplete suite.

A paired comparison requires both member fits to be numerically certified on the intended common support. Its statistical inference still requires the later paired-covariance work. Similarly, numerical convergence of an event-study vector does not validate its confidence intervals or HonestDiD inputs.

No bootstrap, simulation, or sensitivity run may silently discard numerically failed draws. Carry the numerical-validation policy into subsequent refits and report failures. Do not claim that Gate 1 numerical certification validates sampling assumptions, causal interpretation, or finite-sample coverage.

## 9. Required deliverables for this repair—not a new bureaucracy project

Use the existing architecture and return:

1. The signed/owner-authorized amendment record and old-to-new numerical specification diff, with unchanged scientific inputs documented.
2. The per-model/per-solver diagnostic table showing actual metrics, thresholds, termination reasons, and the diagnosed failure mechanism or remaining uncertainty.
3. The minimal code changes, relevant derivative/boundary/solver tests, and fresh full-data numerical run receipts under the amended specification.
4. A complete 11-model result-status table and certificates for passing targets, with blocked models explicitly retained.
5. Updated dependency/working-ledger state showing exactly which Gate 2 tasks are now permitted and why.

The separate reviewer should inspect the objective equivalence, scaling transformations, boundary treatment, full target accuracy, and numerical comparisons—not only file hashes and status consistency. Label same-team review accurately.

Once target-specific prerequisites pass, continue the already authorized V3 work without asking for permission merely to use another allowed numerical algorithm or tighter internal setting. Request a further owner decision only for a genuine change outside this authorization, such as a different estimator, a weakened final acceptance criterion, a new data-access permission, or additional resources beyond the existing authorization.

The final update must distinguish: repair implemented; repair actually executed; number of models numerically certified; remaining blockers; downstream tasks run; and overall V3 completion. Do not summarize another integrity-only pass as completion of the scientific revision.

## 10. Technical references and reviewed materials

The decision is grounded in the supplied blocked-run README, convergence/existence report, exact-target audit, same-team review, and execution state, and in original V3 prompt §§4.3 and 6.2 and seed N03. This is a single-file authorization; no new companion checklist or input package is required. The execution agent should use the actual reports, specifications, and code already held in its authenticated project workspace. Inspection of these reports is not independent verification of their underlying empirical computations.

Official documentation checked for this adjudication:

- SciPy L-BFGS-B: documents relative objective-decrease and projected-gradient stopping criteria, which are distinct checks. `https://docs.scipy.org/doc/scipy/reference/optimize.minimize-lbfgsb.html`
- SciPy trust-ncg: documents its gradient-norm stopping criterion. `https://docs.scipy.org/doc/scipy/reference/optimize.minimize-trustncg.html`
- Boyd and Vandenberghe, *Convex Optimization*, especially optimality conditions and Newton-method sections: mathematical background for finite identified-core checks. `https://web.stanford.edu/~boyd/cvxbook/bv_cvxbook.pdf`

These are general numerical references, not evidence that any particular stopping or scaling problem occurred in this run. Check the execution environment's installed versions and actual traces.
