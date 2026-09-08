# Gate 2 support-inference failed execution 7489319

This is the permanent record of the fifth authorized Gate 2
support-inference attempt. It is a failed pre-fit command-binding attempt, not
a numerical or scientific result.

- SGE job: `7489319`
- Run ID: `gate2_support_inference_sge_7489319`
- Implementation commit: `618c65fdd648b08c2f81db54770bd0cdb116f9b7`
- Authorization commit: `544ff1dd1646a0b9781eb1906fece3b78b2531bc`
- SCC host/queue: `scc-gr4.scc.bu.edu` / `econ`
- Start/end: `2026-09-07 22:54:52` / `2026-09-07 22:55:04` (SCC time)
- Accounting: `failed=0`, application `exit_status=2`, wall clock 12 seconds,
  maximum virtual memory 843.078 MB
- SCC evidence directory:
  `/projectnb/econdept/qluo/yax-v3-gate2-support-runs-618c65f`

The runner failed closed before fitting any model with:

> BLOCKED: pre-execution authorization run binding differs

No result receipt, failure-evidence leaf, or scientific output was created.
The corrected batch bootstrap successfully started Python and the runner.

The authorization was generated on the SCC login host, where the GPFS mount
reported device number 157. The hard-pinned execution host reported device
number 48 for the same paths and identical inodes and resolved-path hashes.
Because the command-binding contract includes the host-local device number,
every path identity differed even though paths, inodes, and bytes were
unchanged. A field-by-field comparison on the execution host verified that
this device-number difference was the only mismatch.

The analysis runner, specification, authenticated scientific inputs,
estimator, targets, thresholds, and inference procedure remain unchanged. The
retry must generate its single-use authorization on the hard-pinned execution
host so the existing command-binding rule is instantiated in the environment
where the job will run.

The authorization committed at `544ff1d` is preserved in Git history and
removed from the subsequent implementation state.
