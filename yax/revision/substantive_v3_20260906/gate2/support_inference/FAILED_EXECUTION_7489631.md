# Gate 2 support-inference failed execution 7489631

This is the permanent record of the eighth authorized Gate 2
support-inference attempt. It is a post-certification publication failure, not
an authoritative scientific result.

- SGE job: `7489631`
- Run ID: `gate2_support_inference_sge_7489631`
- Implementation commit: `0099aa2b3906e53c03d398033d594ef6513ae2c5`
- Authorization commit: `9938917cc098683a6c989f5a62e7941cf964e7d7`
- SCC host/queue: `scc-gr4.scc.bu.edu` / `econ`
- Start/end: `2026-09-07 23:48:39` / `2026-09-07 23:52:19` (SCC time)
- Accounting: `failed=0`, application `exit_status=2`, wall clock 220 seconds,
  maximum virtual memory 3.203 GB
- SCC evidence directory:
  `/projectnb/econdept/qluo/yax-v3-gate2-support-runs-0099aa2`

The corrected launcher preserved the pinned virtual environment. Runtime and
authorization checks passed, and all five required models reached the frozen
A1 numerical certificate. The retained private staging catalog records all
five `PASS_A1_NUMERICAL_CERTIFICATE` statuses. No authoritative result leaf or
receipt was published.

Publication stopped while writing the second staged artifact because the
public numerical-evidence sanitizer handled NumPy scalars but not NumPy
arrays. The same omission prevented the nonauthoritative failure record from
being serialized:

> BLOCKED: post-certification pipeline failed and nonauthoritative evidence
> could not be published: Object of type ndarray is not JSON serializable

The repair recursively converts NumPy arrays through the existing redacting
sanitizer, maps non-finite floating values to JSON null as in the hash-pinned
A1 writer, and applies the same sanitizer to stored trajectories. Regression
tests cover nested arrays, non-finite values, and failure evidence. This is an
output-serialization repair only; scientific inputs, estimators, targets,
thresholds, and inference remain unchanged.

The authorization committed at `9938917` is single-use and preserved in Git
history. It is removed from the subsequent implementation state. Any retry
requires a new held SGE job, output-parent identity, authorization document,
authorization commit, and run ID.
