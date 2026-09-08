# Gate 2 support-inference failed execution 7489450

This is the permanent record of the sixth authorized Gate 2
support-inference attempt. It is a failed pre-fit runtime-authentication
attempt, not a numerical or scientific result.

- SGE job: `7489450`
- Run ID: `gate2_support_inference_sge_7489450`
- Implementation commit: `115807d7807db8916b73db48bbaedbaa51d6fc54`
- Authorization commit: `e7bc0d5956274cf7ee76414c451b28f5aa7aa7cd`
- SCC host/queue: `scc-gr4.scc.bu.edu` / `econ`
- Start/end: `2026-09-07 23:06:13` / `2026-09-07 23:06:16` (SCC time)
- Accounting: `failed=0`, application `exit_status=2`, wall clock 3 seconds,
  maximum virtual memory 845.883 MB
- SCC evidence directory:
  `/projectnb/econdept/qluo/yax-v3-gate2-support-runs-115807d`

The runner failed closed before fitting any model with:

> BLOCKED: hash-pinned A1 runtime-contract verification failed

No result receipt or scientific output was created. The single-use
authorization and command binding passed on the hard-pinned execution host.

A same-host reconstruction under the explicitly pinned library environment
passed the A1 and independent runtime-contract checks, including exact package
versions, executable hashes, payload hash, and the NumPy structural probe. A
subsequent same-queue batch diagnostic passed the same checks as well.

The external launcher, rather than SCC or the scientific runner, caused the
failure. It resolved the virtual-environment Python symlink before `exec`,
turning the authorized venv path into the base SCC interpreter path. The venv
provided NumPy 2.5.1, pandas 3.0.3, and pytest 9.1.1; the dereferenced base
interpreter instead loaded NumPy 2.2.6, pandas 2.3.3, and pytest 8.4.2. The
runtime guard correctly rejected that environment. The corrected launcher
validates but does not dereference the venv interpreter path. This does not
alter scientific inputs, estimator, targets, thresholds, or inference.

The authorization committed at `e7bc0d5` is single-use and preserved in Git
history. It is removed from the subsequent implementation state. Any retry
requires a new held SGE job, output-parent identity, authorization document,
authorization commit, and run ID.
