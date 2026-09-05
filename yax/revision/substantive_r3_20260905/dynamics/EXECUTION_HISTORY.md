# Dynamics execution history

This file preserves failed and superseded execution facts without promoting
their partial numerical artifacts to final evidence.

## SCC job 7467443 (provisional)

- Exit status: 0.
- Wall time: 1,242 seconds.
- Maximum virtual memory: 2.839 GB.
- Role: computational feasibility run of the first quarterly implementation.
- Disposition: superseded before interpretation because it did not contain the
  explicit March-source preflight, lower-dimensional seasonality specification,
  expanded endpoint grid, or fail-closed grid ledger.

## SCC job 7468697 (failed authoritative attempt)

- Exit status: 1.
- Wall time: 282 seconds.
- Maximum virtual memory: 2.477 GB.
- The March append-versus-replace preflight passed.
- Historical unconditioned quarterly dynamics converged in 5 iterations.
- Historical SOC2-by-calendar-month quarterly dynamics converged in 6
  iterations.
- The complete onset grid finished.
- Execution stopped when a grouped-binomial endpoint model did not converge.
  The then-current code aborted on the first failure rather than retaining the
  rest of the declared grid.
- Local diagnostic log SHA-256:
  `6296d4b0201b44890daa93ff7065acf0092af8f4abd8540986fcb7633b2cda25`.
- March policy receipt SHA-256:
  `359a861956cdbf05441e4e15243a7cd1f6859cf144eb281d2b103c9548995921`.

Response: the estimator and estimands were not changed. The revised runner
records a failed grid row and continues the remaining predeclared rows, while
still requiring both historical quarterly core models. Linear algebra is fixed
to one thread to reduce numerical nondeterminism. No alternative endpoint is
silently substituted for a failed endpoint.

## SCC job 7468699 (failed package installation)

- Exit status: 1.
- Wall time: 52 seconds.
- `HonestDiD` source retrieval began, but its official `Rglpk` dependency could
  not locate GLPK and failed during configuration.

Response: the revised installer loads SCC's `glpk/5.0` module, checks the exact
header and shared-library paths, and uses a new project-storage R library so no
partial lock or failed build is reused. The statistical analysis continues to
require the official pinned `HonestDiD` source; no local reimplementation is
allowed.

## SCC job 7468738 (successful package installation)

- Exit status: 0.
- Wall time: 53 seconds.
- Maximum virtual memory: 1.404 GB.
- SCC modules: `R/4.5.2` and `glpk/5.0`.
- Installation target: project-storage library
  `agents/dynamics/r-library/4.5-glpk-module`; nothing was installed in the
  quota-limited home directory.
- Installed package: official `HonestDiD` 0.2.8 from pinned source commit
  `6813f02ed38f0b63bdca6915604b2eac90491303`.
- The package loaded successfully after installation. A nonzero `clarabel`
  compiler warning was retained in the log but did not prevent the pinned
  package or its GLPK dependency from loading.

Disposition: this resolves the technical blocker from job 7468699. Statistical
results still require a separate run against the authoritative event vector and
full covariance; installation success is not recorded as analysis success.

## SCC job 7468737 (authoritative Python dynamics)

- Exit status: 0.
- Wall time: 2,042 seconds.
- Maximum virtual memory: 2.770 GB.
- Final status: `PASS_R3_DYNAMICS_SELFCHECK`.
- Output dimensions: 608 fully interacted dynamic-profile rows, 152 Q5-versus-Q1
  rows, 32 onset rows, and 24 endpoint-grid rows.
- Execution-receipt SHA-256:
  `98b2b0aecf64f35499a0c92eaff35cee26a3f7b97256a46cb3454360eb094e07`.
- All four post-2020 coding-stable endpoint models failed to converge and are
  retained as `FAILED_REPORTED_NOT_SUBSTITUTED` rows.
- The four lower-dimensional Q2--Q5-by-month-of-year sensitivities converged.
  All four saturated occupation-by-month-of-year sensitivities failed to
  converge and are retained rather than replaced.

Disposition: this is the authoritative Python result set. It validates all four
38-element Q5 event vectors and full-rank covariance matrices for the separate
official HonestDiD stage.

## SCC job 7469127 (failed HonestDiD serialization handoff)

- Exit status: 1.
- Wall time: 2 seconds.
- Maximum virtual memory: 238.7 MB.
- Failure: R `read.csv` retained Python's capitalized `True`/`False` event flags
  as character values, so `which(vector$is_pre)` rejected a nonlogical input
  before any sensitivity model ran.

Response: the event vector, covariance, package, estimand, and declared grids
are unchanged. The R handoff now validates and converts only the six admitted
Boolean serializations (`true`, `false`, `t`, `f`, `1`, `0`) before calling the
official package. Unexpected values still fail closed. No statistical result
from job 7469127 exists or is substituted.

## SCC job 7469157 (failed dependency compatibility check)

- Exit status: 1.
- Wall time: 7 seconds.
- Maximum virtual memory: 644.516 MB.
- The strict Boolean conversion succeeded and the official HonestDiD routine
  reached its optimizer.
- Failure: installed CVXR did not export `status`, which HonestDiD 0.2.8 calls;
  the official routine stopped with `"'status' is not an exported object from
  'namespace:CVXR'"` before returning a sensitivity result.

Response: no method is reimplemented or substituted. The environment is moved
to a new project library and pins official CVXR 1.8.2 at source commit
`2fe1dac4d0c903c4a29515bef19c5d3824d09656`. Its official namespace exports
both `status` and `problem_status`, and its DESCRIPTION satisfies HonestDiD's
declared `CVXR (>= 1.8)` dependency. Installation and execution both verify the
CVXR version, source SHA, and exported API before running. No result from job
7469157 is used.

## SCC job 7469187 (failed pinned-CVXR build without Rust)

- Exit status: 1 (scheduler `failed=0`).
- Wall time: 16 seconds.
- Maximum virtual memory: 851.758 MB.
- CVXR 1.8.2 was retrieved from the pinned official source, but its declared
  `clarabel (>= 0.11)` dependency could not compile because `rustc` and `cargo`
  were absent from the job environment. CVXR therefore was not installed and no
  statistical routine ran.

Response: SCC exposes the official `rust/1.84.0` module, which exceeds clarabel's
Rust 1.70 minimum. The installer now loads that module, verifies both `rustc` and
`cargo`, and uses another fresh project library. CVXR, HonestDiD, their source
pins, and every declared sensitivity parameter remain unchanged. No result from
job 7469187 is used.

## SCC job 7469208 (failed CVXR dependency-version check)

- Exit status: 1 (scheduler `failed=0`).
- Wall time: 145 seconds.
- Maximum virtual memory: 2.351 GB.
- With the official Rust module loaded, clarabel compiled. CVXR then failed its
  lazy-load check because SCC resolved `highs` 1.10.0-3 while CVXR 1.8.2 requires
  `highs (>= 1.12)`.

Response: the next clean project library explicitly installs the official CRAN
archive release `highs` 1.12.0-3 before CVXR and rejects any other loaded
version. The install, execution, and final self-check all verify that version.
The official CVXR and HonestDiD source pins and the statistical analysis remain
unchanged. No result from job 7469208 is used.

## SCC job 7469229 (failed CVXR `osqp` lower bound)

- Exit status: 1 (scheduler `failed=0`).
- Wall time: 993 seconds.
- Maximum virtual memory: 2.403 GB.
- The pinned `highs` release compiled. CVXR then failed lazy loading because SCC
  resolved `osqp` 0.6.3.3 while CVXR 1.8.2 requires `osqp (>= 1.0)`.

Response: the installer explicitly installs and verifies the official CRAN
`osqp` 1.0.0 release in the project library before CVXR. Execution and final
self-check repeat the exact version check. CVXR/HonestDiD source pins and all
statistical inputs and grids remain unchanged. No result from job 7469229 is
used.

## SCC job 7469287 (successful pinned dependency stack)

- Exit status: 0 (scheduler `failed=0`).
- Wall time: 172 seconds.
- Maximum virtual memory: 1.582 GB.
- Verified packages: official CRAN `osqp` 1.0.0, official CRAN `highs`
  1.12.0-3, official CVXR 1.8.2 at source commit
  `2fe1dac4d0c903c4a29515bef19c5d3824d09656`, `Rglpk` 0.6-5.1, and official
  HonestDiD 0.2.8 at source commit
  `6813f02ed38f0b63bdca6915604b2eac90491303`.

Disposition: the official package and every dependency that caused a prior
failure now pass their version/source/API checks. Statistical success remains a
separate claim requiring job 7469301 and its final artifact self-check.

## SCC job 7469301 (successful official HonestDiD analysis)

- Exit status: 0 (scheduler `failed=0`).
- Wall time: 4,189 seconds.
- Maximum virtual memory: 1.445 GB.
- Host: `scc-mf1`.
- Result package: official `HonestDiD` 0.2.8 at source commit
  `6813f02ed38f0b63bdca6915604b2eac90491303`, with official CVXR 1.8.2 at
  `2fe1dac4d0c903c4a29515bef19c5d3824d09656`.
- Final status: `PASS_OFFICIAL_HONESTDID_SELFCHECK` and
  `PASS_R3_DYNAMICS_SELFCHECK`.

The official routine evaluated both historical and rebuilt event vectors under
the pooled and SOC2-by-calendar-month structures.  For the rebuilt vectors, the
conventional companion intervals are `[-0.263649, 0.023871]` and
`[-0.425163, 0.010295]`.  Both already include zero, so no positive
zero-exclusion breakdown is defined.  All declared smoothness and
relative-magnitude grids, package/source receipts, event vectors, and covariance
hashes are preserved in `dynamics/results/`.

Disposition: these are the authoritative official trend-sensitivity artifacts.
Earlier failed package and serialization attempts remain in this history and in
the failure registry; none contributes a statistical result.

## SCC job 7469348 (failed rebuilt-inference wrapper)

- Exit status: 2; the process stopped before reading data.
- Failure: the first wrapper retained an obsolete hard-coded repository root.
- Disposition: preserved in `inference_rebuilt/scc_execution.log`.  The code was
  changed only to accept the explicit isolated-worktree root.

## SCC job 7469956 (successful rebuilt-inference audit)

- Exit status: 0 (scheduler `failed=0`).
- Wall time: 43 seconds.
- Maximum virtual memory: 1.924 GB.
- Final status: `PASS_REBUILT_INFERENCE_SELFCHECK`.

The 22-family Webb interval for the conditioned-minus-pooled movement is
`[0.005876, 0.214993]`.  Elapsed-calendar HAC matrices are positive semidefinite
in the rebuilt run and no projection is applied.  These results supersede
historical-treatment inference rows for substantive synthesis.

## SCC jobs 7469964 and 7469972 (rebuilt family harmonization)

Job 7469964 remains error-queued because its declared log directory did not
exist; it never started and was not deleted.  After creating that directory, a
fresh unchanged submission, job 7469972, completed with exit status 0 in 180
seconds and used at most 1.915 GB.  Its 49 checks passed under status
`PASS_REBUILT_FAMILY_SELFCHECK`.  The authoritative direct-tail population is 29
occupations and 5.03 percent of full-support preperiod stock; all family results
use the rebuilt corrected-preperiod treatment contract.
