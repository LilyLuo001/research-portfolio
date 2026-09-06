# V3 Gate-1 BASE-03 wrapper

This directory contains the fail-closed wrapper for a fresh reconstruction of
the canonical corrected-calendar, rebuilt-treatment pooled baseline. It wraps
the existing R3 BASE-03 implementation; it does not copy, edit, tune, or
replace that estimator.

The wrapper deliberately separates three things:

- the immutable analysis contract;
- resolved SCC paths used only by the process;
- sanitized audit artifacts that may be transferred or versioned.

Run it only in a fresh SCC worktree whose BASE-03 runner hash and environment
match the canonical contract and whose imported implementation matches
`TRANSITIVE_CODE_LOCK.json`. Supply a new result directory and a disjoint new
audit directory under the writable SCC compute root. Placeholder command:

```sh
<YAX_PYTHON_BIN> yax/revision/substantive_v3_20260906/gate1_baseline/run_gate1_baseline.py \
  --repo-root <YAX_REPO_ROOT> \
  --python-bin <YAX_PYTHON_BIN> \
  --microdata <YAX_PRIVATE_ROOT>/ai_telework_2017_2026/cps_00009.csv.gz \
  --repair-microdata <YAX_PRIVATE_ROOT>/yax_referee_march_repair/cps_00011.csv.gz \
  --historical-preperiod-cells <YAX_PRIVATE_ROOT>/ai_telework_2017_2026/preperiod_gate_v1/young_relative_employment_cells_v1.csv \
  --output-dir <YAX_V3_RUN_ROOT>/gate1_baseline/results \
  --audit-dir <YAX_V3_RUN_ROOT>/gate1_baseline/audit
```

The wrapper enforces that result and audit leaves are outside the repository,
do not already exist (even as empty directories), and are disjoint. Their
atomic creation prevents two jobs from sharing a leaf. On either a pass or a
failure, retain the entire SCC directories. The audit directory
contains `V3_EXECUTION_RECEIPT.json`, `WRAPPER_FAILURES.json`, and separate
runner, self-check, and wrapper logs. The wrapper sanitizes known resolved paths
and common credential patterns before writing those artifacts, and the receipt
refuses known local/SCC path markers.

The wrapper pins both the canonical `spec_id` and the contract file's byte
hash, so `--spec` permits an immutable copy but not a substitute restamped
contract. The source contract intentionally names the R3 command template with
placeholders. The V3 receipt records that template, source and dependency
hashes, runtime versions, subprocess timestamps and exit codes, code hashes,
fresh output hashes, and post-run checkpoint comparisons. The supplemental
code lock binds the frozen engine and cell-building modules imported by the
BASE-03 entry point to the source commit recorded by the byte-pinned,
authenticated R3 reference. The receipt never records the resolved command
line. It records a sanitized wrapper command template, Git state, and one
`result_id` per checkpoint row.

The wrapper intentionally does not mutate the project-level result ledger or
run DAG. After a passing SCC execution, a separate reviewed transfer must copy
the sanitized receipt to the contract-named repository location and register
its result IDs and dependencies. Do not mark the baseline requirement verified
until that integration step passes. The canonical contract also carries the
historical preperiod cells in its command rather than as a standalone
`data.sources` row; `PRE_RESULTS_SPEC.md` records the wrapper's transitive
authentication and the remaining project-level adjudication.

Tests exercise contract validation, immutable reference authentication,
post-run comparison logic, output-directory refusal, runtime-lock parsing, and
redaction without accessing licensed CPS microdata:

```sh
<YAX_PYTHON_BIN> -m pytest -q \
  yax/revision/substantive_v3_20260906/gate1_baseline/tests
```

Neither this README nor the presence of the wrapper is evidence of a completed
fresh run. Only a passing V3 execution receipt backed by retained SCC outputs
can establish that result.
