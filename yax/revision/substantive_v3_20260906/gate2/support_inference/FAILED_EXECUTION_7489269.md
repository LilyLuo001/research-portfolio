# Gate 2 support-inference failed execution 7489269

This is the permanent record of the fourth authorized Gate 2
support-inference attempt. It is a failed batch-launch attempt, not a numerical
or scientific result.

- SGE job: `7489269`
- Run ID: `gate2_support_inference_sge_7489269`
- Implementation commit: `ee609a37c18fb369532ac32019f1c4656845935e`
- Authorization commit: `1ca9c47bcd875d2ca1a59f72b191f61d4547fe7f`
- SCC host/queue: `scc-gr4.scc.bu.edu` / `econ`
- Start/end: `2026-09-07 22:31:58` / `2026-09-07 22:31:58` (SCC time)
- Accounting: `failed=0`, application `exit_status=127`, wall clock 0 seconds,
  maximum resident set size 3,492 KB
- SCC evidence directory:
  `/projectnb/econdept/qluo/yax-v3-gate2-support-runs-ee609a3`
- `sge.err` and `sge.out`: both empty

No Python process, result leaf, receipt, failure-evidence leaf, protected input
read, model fit, or scientific output was produced. Scheduler accounting and
the empty output files show that the batch shell exited before the launcher
started.

The operational job script used `set -e` followed by `module purge` and
`module load`. The SGE batch shell did not initialize the environment-modules
shell function, so the first `module` invocation returned command-not-found;
its diagnostic was redirected to `/dev/null`, producing application exit 127
with empty scheduler logs. The pinned Python 3.13.8 virtual environment is
self-contained and was independently verified under an empty environment, so
the retry removes only these unnecessary launcher-level module commands. The
analysis runner, specification, authenticated scientific inputs, estimator,
targets, thresholds, and inference procedure are unchanged.

The authorization committed at `1ca9c47` was single-use and is preserved in
Git history. It is removed from the subsequent implementation state. Any retry
requires a new held SGE job, authorization document, authorization commit, and
run ID.
