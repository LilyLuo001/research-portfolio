# Gate 2 support-inference design (frozen before results)

This package resolves the pre-result design obligations for S03, S04, S06,
and S07. It does not contain authoritative estimates. The runner accepts only
the hash-pinned aggregate cells and receipts listed in
`SUPPORT_INFERENCE_SPEC.json`, and publishes nothing unless every new primary
fit passes the A1 numerical certificate. The historical within-family and
direct-tail solvers are not imported.

## Shared likelihood and calendar

Let `Y_ot` be young employment, `O_ot` older employment, and
`T_ot = Y_ot + O_ot`. Every model uses the exact grouped-binomial likelihood
for `Y_ot | T_ot`, occupation fixed effects, and the stated time partition.
There is no probability clipping, pseudocount, ridge penalty, or silent row
deletion. Static estimation includes the 113 observed months from 2017-01
through 2026-07 except 2022-12; 2025-10 is genuinely absent and is never
interpolated. `P_t` is one from 2023-01 onward. Quintiles and Rule-A beta are
the frozen membership values, never recomputed on an analysis subset.

Every published artifact is bound by filename, logical key, byte count, and
SHA-256 to a content-derived artifact ID. A content-derived result ID binds the
complete artifact manifest, and a content-derived receipt ID binds that result,
the frozen spec ID, and the manifest file. The spec ID itself is recomputed
from canonical JSON content at runtime; changing any signed behavior or input
binding without changing the ID blocks execution.

The success publication class is exactly
`CERTIFIED_RESULT_ARTIFACTS_WITH_EXPECTED_STRUCTURAL_RANK_BLOCK`; its 40-file
artifact inventory is enumerated in the frozen spec. The only failure class is
`NONAUTHORITATIVE_NUMERICAL_FAILURE_EVIDENCE_ONLY`, with exactly
`FAILURE_EVIDENCE.json` and `FAILURE_VALIDATION.json`. Missing, extra, or
duplicate logical keys block publication. Success also requires a
content-derived PASS validation report with zero failed checks, the exact
structural-rank disclosure below, and hashes binding every stored draw family
to the single occupation-ordered multiplier matrix.

## S07: pooled versus family-month profile

The pooled model is

`eta_ot = alpha_o + delta_t + gamma w_o P_t + sum_(q=2)^5 beta^P_q 1[q_o=q]P_t`.

The family-month model replaces `delta_t` with `delta_(g,t)` and otherwise has
the same treatment columns, producing `beta^F_q`. The report contains the
complete vectors `beta^P`, `beta^F`, and `Delta = beta^F-beta^P`, their paired
occupation-cluster covariance, both within-model covariance matrices, both
directions of the cross-model covariance, rank-aware joint-null tests, pointwise
intervals, and max-|t| simultaneous intervals for all three vectors. The
reported estimates come from the A1 trust path; the independent zero-start path
is retained as a reference with complete target/probability/objective
differences. Before these quantities may be
used, the new run must reproduce every A1 pooled and family-month treatment
coefficient within the frozen A1 target tolerance; mismatch aborts the run.

## S03: support-respecting family heterogeneity and direct tails

For family `g`, let `Q_g` be exactly the supported quintiles in the authenticated
support matrix and `q0_g = min(Q_g)`. The fitted model is

`eta_ot = alpha_o + delta_(g,t) + gamma w_o P_t
          + sum_g sum_(q in Q_g excluding q0_g) theta_gq 1[g_o=g,q_o=q]P_t`.

For each authenticated support edge `(g,q,r)`, the estimand is
`tau_gqr = theta_gr - theta_gq`, with the omitted reference interpreted as
zero. Only actual edges are reported; unsupported cells are not imputed and
contrasts are not chained through a missing endpoint. A pair-specific summary,
when formed, uses frozen pre-period stock:

`lambda_g,qr = (S_gq+S_gr) / sum_h(S_hq+S_hr)` and
`tau_qr = sum_g lambda_g,qr tau_gqr`, over families with that edge.

The family-specific coefficients remain heterogeneous; the summary is not a
common-slope maximum-likelihood coefficient.

Edge labels and coefficient functionals are rebuilt from the authenticated
support matrix and complete authenticated edge set, rather than accepted from
a result table. The ten pair-specific aggregates are then rebuilt from those
edge functionals and authenticated endpoint stocks. Their family weights,
coefficient functionals, labels and order, eligible-family counts, full
covariance, and common-multiplier centered draws are all persisted. Validation
repeats the reconstruction from authenticated inputs and checks point
estimates, every public metadata/inference field in the estimate and functional
tables, influence-derived and functional covariance, and draws.

### Direct Q1-Q5 tail estimand

The sample is exactly the 29 occupations in the authenticated direct-tail
membership file, spanning families 27, 29, 31, and 41. It fits

`eta_ot = alpha_o + delta_(g,t) + gamma w_o P_t
          + sum_g phi_g 1[g_o=g,q_o=5]P_t`.

All four `phi_g` are primary. The aggregate is the fixed pre-stock weighted
average `tau_DT = sum_g lambda_g phi_g`, where
`lambda_g = (S_g1+S_g5)/sum_h(S_h1+S_h5)`. This is explicitly not a pooled
common-slope MLE.

The four direct-effect labels and unit functionals, as well as the fixed-stock
aggregate functional, are independently rebuilt from authenticated direct-tail
membership. Result estimates, covariance, occupation/family influence closure,
and common draws must agree with those reconstructed functionals.

The fixed-weight aggregate is the declared A1 focal functional. Its two-sided
fixed-target likelihood profile, full fitted-Hessian checks, and trust/reference
comparison are therefore required alongside the four-family coefficient
certificate.

## S04: continuous Rule-A beta and information diagnostics

Let `S_o = sum_(t<=2022-11) T_ot`, `a_o` be raw Rule-A beta, and
`mu_g = sum_(o in g)S_o a_o / sum_(o in g)S_o`. Define `x_o=a_o-mu_g` and fit
once:

`eta_ot = alpha_o + delta_(g,t) + gamma w_o P_t + rho x_o P_t`.

The raw-beta coefficient is primary. Two scaled effects are exact
reparameterizations of the same fit: `rho_W=sigma_W rho`, with
`sigma_W^2=sum S_o x_o^2/sum S_o`; and `rho_R=sigma_R rho`, where `sigma_R`
is the pre-stock-weighted SD of raw beta residualized on family dummies plus
Webb. The second equality is exact because family-post terms are absorbed by
family-month fixed effects and Webb-post is already present. No scaled model is
refit.

### Information panels

Information is computed for each fitted model coefficient in its exact target
coordinate after residualizing against the complete nuisance space. The fixed
direct-tail aggregate is not a separately tabulated information target; its
full inferential covariance and occupation/family influence closure are
reported instead. Three coefficient panels are defined: half-information
`h=T/4`; pooled-reference
curvature `h=T p_P(1-p_P)` evaluated only on the target model's retained rows;
and own-fit `h=T p(1-p)`. The pooled-reference panel is explicitly labeled
`fixed_pooled_within_support`. It is not an absolute-level comparison to the
full pooled sample when support differs. Each panel reports `sum(h)`, raw
centered exposure SS/SD, fixed-effect-residual SS/SD, all-nuisance conditional
information/SD, occupation contributions, and effective occupation equivalent
`1/sum s_o^2`.

## S06: influence accounting and descriptive paths

For fitted probability `p`, set `h=T p(1-p)` and residualize every target
column against the full nuisance fixed-effect space. With residualized matrix
`R`, `J=R'hR`, occupation score `S_o=sum_t R_ot(Y_ot-T_ot p_ot)`, and raw
influence `IF_o=J^-1 S_o`, covariance is
`G/(G-1) sum_o IF_o IF_o'`. Approximate deletion change is `-IF_o`.
Occupation influences are also summed by family, preserving the closure back
to the occupation total.

A single occupation-ordered 9,999-draw Rademacher matrix with seed 2026090521
is used for every model and paired difference. Draws are centered score draws
`sqrt(G/(G-1)) sum_o xi_bo IF_o`. Joint tests report covariance rank and block
the full-dimensional claim if rank is below the restriction count. Multiplier
p-values use `(1 + # exceedances)/(B+1)`. Simultaneous intervals use the upper
empirical quantile of the maximum absolute studentized draw.

The 89 reported supported edges are linear functions of exactly 50 independent
family-exposure directions: 72 supported cells minus one reference in each of
22 families. (The separately fitted Webb-post coefficient is not an edge
direction.) Their full 89-dimensional covariance is therefore
structurally rank deficient. The runner records
`EXPECTED_STRUCTURAL_RANK_BLOCK`, requires functional rank 50, requires
covariance rank at most 50, discloses any further covariance deficiency below
50, reports restriction count and observed rank, and emits no chi-square or
p-value for that unavailable full-dimensional joint
test. This disclosed limitation does not invalidate the fitted coefficients,
marginal edge results, or max-|t| simultaneous edge intervals.

### Calendar-safe descriptive paths

Family-by-quintile monthly young and older aggregates are archived for every
supported cell on the full calendar scaffold. 2025-10 is a `MISSING` row with
blank values; 2022-12 is labeled `TRANSITION`. Log ratios are defined only when
both counts are positive. Static-estimation quarterly means exclude both the
missing month and 2022-12, retain explicit transition counts, and report the
number of months with a defined log ratio. Thus 2022Q4 has two estimation
months and one separately counted transition month. There is no interpolation and no
occupation-by-month artifact. Candidate main-text paths can be selected from
the largest positive and negative family influences for the pooled Q5 and
paired Q5 movement, deduplicated before presentation; selection is descriptive,
not a new inferential search.

## Explicit blockers

The package blocks publication on any hash, receipt, calendar, membership,
support, rank, A1-profile reproduction, solver, profile-likelihood, or
fitted-Hessian failure. It also blocks fixed-reference information comparisons
without exact row/probability alignment. Authoritative execution requires the
authenticated aggregate file in the controlled environment; it was not run
while freezing this package.

Authoritative execution additionally requires Python `-I`, absence of
import-affecting Python environment variables, the pinned Python 3.13.8 and Git
2.43.7 executable hashes, and the authenticated A1 runtime payload. Before any
aggregate cell is opened, the runner invokes the hash-pinned A1
`execution_runtime_authentication` and `verify_runtime_contract`, independently
reconstructs and hashes architecture, glibc, compiler, Python, NumPy, pandas,
SciPy, and pytest fields, and executes a NumPy 2.5.1 `vstack` structural probe.
The loaded A1 `artifact_safety.py` must be the exact runner sibling with the
signed hash. Runner and
spec bytes must equal a clean committed `HEAD`. After that exact implementation
commit exists, a version-2 `PRE_EXECUTION_AUTHORIZATION.json` with at most a
24-hour validity interval and at most 24 hours of issue age must be
committed as the sole file in the immediately following commit, binding the
canonical spec, support spec, runner, authenticated-input registry, positive
numeric SGE `JOB_ID`, exact `gate2_support_inference_sge_<JOB_ID>` run ID,
canonical sanitized argument identities, and output-parent resolved-path hash,
device, and inode. The authorization is single-use for that held scheduler job,
run ID, and output parent. The runner reconstitutes the same run identity before
each provenance checkpoint and publication; publication additionally requires
the capability issued in-process after the initial authenticated provenance.
That
authorization is intentionally absent from this pre-execution package:
external object immutability and authorization remain pending until the clean
implementation commit exists. The runner checks the same repository, runtime,
authorization, and input state again immediately before publication and records
the full provenance and all input hashes in the receipt.

S05 and L01 are not resolved by this package and remain explicitly out of
scope. No status ledger, STATE file, manuscript, or presentation claim is
changed by freezing this design.

Fresh A1 audits, solver rows, profile grids, Hessian diagnostics, trajectories,
checkpoint differences, and trust/reference state-source metrics are retained
for independent verification. Numerical values are preserved; the narrowly
protected occupation-plus-month identifier attached to an extremal diagnostic
location is redacted so the evidence package does not create a prohibited
occupation-by-month output.

If an A1 certificate, reconstructed finite face, rank basis, reference path,
trust path, trust/reference comparison, or A1 checkpoint fails, the successful
result receipt is never created. Instead, a sibling directory ending
`__FAILURE_EVIDENCE` stores only sanitized, content-bound, explicitly
nonauthoritative numerical failure evidence and its own manifest and receipt.
It carries `scientific_result_claims=false` and cannot be mistaken for a result
publication. Success and failure output leaves require the scheduler-unique
form `gate2_support_inference_sge_<positive job number>`, an existing direct
output parent outside the Git repository, and disjointness from every input;
traversal, separators, absolute paths, dot names, existing symlinks, and
overwrite are rejected.

The runner constructs the hash-pinned A1 reservation type through a local
descriptor-bound reservation routine that never calls the helper's
pathname-cleanup exception branch. If lock creation succeeds, every later
reservation failure retains the lock and any staging leaf for inode-audited
manual inspection. The final leaf is then created exclusively with mode 0700 and
held through an `O_DIRECTORY|O_NOFOLLOW` descriptor. Staged regular-file inodes
are hard-linked relative to that descriptor. Every link is opened with nofollow
through the directory descriptor and checked against its expected staged inode,
byte count, and SHA-256 immediately; after `EXECUTION_RECEIPT.json` is linked
last as the commit marker, every destination artifact including the manifest
and receipt is opened and checked again. This is deliberately an exclusive
reserved-leaf protocol, not atomic directory visibility, and it never invokes
the GPFS ordinary-rename fallback. A competing filename, directory-to-symlink
swap, or same-inode in-place content mutation aborts without overwrite or
redirection. Only descriptor-relative links that still have the exact inode
created by this attempt may be unlinked from an incomplete final leaf; an
incomplete leaf has no receipt.

The runner never calls the A1 recursive staging discard or pathname-based lock
unlink. On success and failure it closes the lock descriptor but retains the
private staging leaf and sibling lock leaf. Those retained leaves make each
authorized run/output leaf non-reusable and consume filesystem quota. Cleanup
is an explicit operator action only: first establish that no publisher holds
the lock, record and compare the exact lock/staging device and inode, inspect
whether the final leaf has a valid receipt, remove only exact retained staging
entries by basename, remove the empty staging directory, and unlink the lock
only if its device/inode still match the inspected object. The runner performs
none of these cleanup steps automatically and never recursively deletes a final
target.

Failures after all fits have
certified—including state reconstruction, influence, information, derived
validation, or success-publication failures—are converted where feasible into
the same sanitized two-file nonauthoritative evidence class.

Before either numerical-audit success output or failure evidence is staged, a
typed sanitizer removes explicit and composite occupation-month identifiers,
general-recession cell counts and row indices, and the aligned strict-boundary
row-index/margin arrays. The final text scan also blocks unredacted quoted JSON
secret fields. Successful publication does not depend on a subsequent stdout
write, so a broken scheduler log pipe cannot turn a committed receipt into an
ambiguous failed job or trigger a second failure publication.
