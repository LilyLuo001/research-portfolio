# Gate-1 sanitized receipt transfer

This directory contains a **pre-result, fail-closed** normalizer for three
Gate-1 execution receipts. It converts runner-recorded, hash-consistent,
module-specific receipt fields into the six-field public interface required by
the V3 delivery checker: `command`, `start_utc`, `end_utc`, `exit_code`,
`mode`, and `code_hash`.

The normalizer does not read or transfer `aggregate_cells.csv`, row-level CPS,
or any analysis result. Its input directory must have exactly these four
directories and six files, with no extra or empty directories:

- `cells/EXECUTION_RECEIPT.json`
- `target/EXECUTION_RECEIPT.json`
- `numerical/EXECUTION_RECEIPT.json`
- `scheduler/cells.json`
- `scheduler/target.json`
- `scheduler/numerical.json`

Each scheduler file must contain exactly `jobnumber`, `qname`, `hostname`,
`start_time`, `end_time`, `failed`, `exit_status`, `ru_wallclock`, `maxvmem`,
and `qacct_export_provenance`. The last field records runner-observed,
byte-pinned consistency with the approved `qacct` executable and exporter; it
is not a cryptographic signature. The terminal transfer spec binds each input
byte hash and each module to its observed scheduler job number. Naive Grid
Engine times require an explicit IANA `scheduler_time_zone`; ambiguous or
nonexistent local times and non-finite numeric values are rejected.

## Fresh-run boundary

Legacy source receipts do **not** contain the required runner-recorded exact
argv array. They cannot produce a valid transfer by adding a command to the
transfer spec, editing a receipt after execution, or restamping hashes. Only
receipts emitted by a fresh authorized producer run are eligible. This
implementation alone therefore does not establish that Gate 1 passes.

The normalizer also refuses to run unless this file is tracked at `HEAD`, its
bytes equal the committed bytes, and the entire Git worktree is clean and has
no untracked files. During this untracked review state that check must fail.
Commit/publish authorization is separate from this implementation review.

A future authorized producer must write a top-level
`execution_command_binding` at execution time. Its exact schema is:

```json
{
  "schema_version": "yax-execution-command-binding-v2",
  "status": "RUNNER_RECORDED_HASH_CONSISTENT",
  "module_key": "cells",
  "run_id": "gate1_cells_sge_<observed-job-number>",
  "scheduler_jobnumber": "<observed-job-number>",
  "sanitized_argv": [
    "<YAX_PYTHON_BIN>",
    "-I",
    "yax/revision/substantive_v3_20260906/gate1_cells/run_gate1_cells.py",
    "--repo-root",
    "<YAX_REPO_ROOT>",
    "--microdata",
    "<INPUT:ipums_cps_extract_9_wide>",
    "--repair-microdata",
    "<INPUT:ipums_cps_extract_11_march_basic_repair>",
    "--output-parent",
    "<YAX_V3_RUN_ROOT>"
  ],
  "sanitized_argv_sha256": "<sha256 of canonical JSON argv bytes>",
  "binding_sha256": "<sha256 of canonical JSON for the other eight fields>"
}
```

The code fixes a different exact argv array for each module from the actual
producer CLI. The executable and every private path use fixed placeholders;
the script, flag order, flag count, and path-role placeholders are immutable.
No shell command string or extra positional token is accepted. The normalized
six-field `command` value is derived as canonical JSON text for the verified
argv array; it is not separately supplied.

`module_key`, `run_id`, and `scheduler_jobnumber` must agree with the terminal
spec and scheduler record. The argv hash and binding self-hash must be
consistent. These unkeyed hashes detect inconsistency; they are not signatures
and do not independently prove who wrote the receipt. Adding the field changes
producer code, so any producer amendment needs separate pre-execution review
and authorization.

## Pre-execution authorization

After the implementation is reviewed and committed, invoke the generator
directly with the pinned SCC Python 3.13.8 executable and isolated mode. Its
`issued_at` value must be within five minutes of the SCC UTC clock, and the
authorization window may not exceed 24 hours:

```bash
<YAX_PYTHON_BIN> -I \
  yax/revision/substantive_v3_20260906/gate1_transfer/generate_pre_execution_authorization.py \
  --implementation-commit <CURRENT_IMPLEMENTATION_HEAD> \
  --issued-at-utc <CURRENT_UTC_Z> \
  --not-before-utc <CURRENT_UTC_Z> \
  --not-after-utc <UTC_Z_WITHIN_24_HOURS>
```

Review the generated `PRE_EXECUTION_AUTHORIZATION.json`, then commit it as the
sole file in the immediately following commit. All three producers and the
normalizer independently require that exact two-commit sequence, current
HEAD, source-registry hash, complete module registry, and authorization time
window. Receipt-carried summaries are never accepted as authority on their
own.

## Pre-result terminal spec

`TRANSFER_SPEC.template.json` deliberately remains `UNSTAMPED_FAIL_CLOSED`
and contains visible `<REQUIRED_...>` placeholders. Copy it to a separate
terminal spec only after authorized future execution. Fill only observed file
hashes, distinct job numbers, distinct run IDs, and the verified scheduler time
zone; then change its status to `TERMINAL_TRANSFER_CONFIG`.

The code and configuration enforce:

- module sequence `cells`, `target`, `numerical`;
- dependency topology `[]`, `[cells]`, `[cells, target]`;
- `cells.end <= target.start`, and both upstream ends `<= numerical.start`;
- cells/target `generated_at_utc` inside the scheduler interval with an exact
  immutable two-second boundary tolerance;
- numerical receipt start/end inside its scheduler interval with the same
  two-second tolerance;
- modes `empirical_reestimate`, `aggregate_analysis`, `numerical_analysis`;
- exact canonical and typed spec identities/hashes, receipt schema/status,
  producer code hash/pointer, time source, and receipt path;
- source-declared reciprocal cell receipt/artifact hashes and exact
  target/numerical artifact and code-hash maps.

The numerical receipt carries a cell receipt/hash link. It carries no target
receipt hash. The numerical-to-target entry is therefore labeled only as a
temporal and topological dependency.

## Run and publication rules

After each non-array job completes, export its scheduler record without shell
redirection, using the same pinned isolated Python:

```bash
<YAX_PYTHON_BIN> -I \
  yax/revision/substantive_v3_20260906/gate1_transfer/export_sanitized_qacct.py \
  --job-id <OBSERVED_JOB_ID> \
  --output <NEW_SCHEDULER_JSON>
```

The exporter pins `/usr/local/ogs-ge2011.11.p1/sge_root/bin/linux-x64/qacct`
by SHA-256, requires the observed version `OGS/GE 2011.11p1`, empty stderr,
one exact non-array record, and an exact job-number join.

```bash
<YAX_PYTHON_BIN> -I \
  yax/revision/substantive_v3_20260906/gate1_transfer/normalize_public_receipts.py \
  --spec /path/to/terminal_transfer_spec.json \
  --input-dir /path/to/dedicated_sanitized_receipts \
  --output-dir /path/to/new_public_transfer_leaf
```

The output leaf must not exist and must not overlap the input or spec. A
same-name lock plus an atomic no-replace directory rename prevents racing
publishers. The lock is JSON containing PID, host, UTC creation time, and
target leaf. A pre-existing lock is never deleted automatically. To recover a
stale lock, inspect that metadata, verify on the recorded host that the PID is
not an active publisher, verify the target does not exist, and only then remove
that one lock manually.

Input and staged files must be regular, single-link files. Symlinks and
hardlinks are rejected. Inputs are snapshotted with filesystem identity and
SHA-256 and rechecked before publication. The terminal spec, committed
authorization, and normalizer source/commit/tree are also rechecked. Exact
file and directory inventories reject hidden files and empty extras. A clean
worktree is required both at capture and immediately before publication;
ignored importable/executable files in the V3 code scope are forbidden.

A successful normalization publishes exactly:

```text
receipt_projections/cells.json
receipt_projections/target.json
receipt_projections/numerical.json
normalized_receipts/cells.json
normalized_receipts/target.json
normalized_receipts/numerical.json
TRANSFER_VALIDATION.json
```

The projections are schema-specific public allowlists; source receipts are
never copied wholesale. No `RUN_LEDGER_MAP.json` is emitted. The normalizer
does not modify `run_manifest.json`, result/claim ledgers, requirement statuses,
or the Gate-1 decision.

Replay of identical inputs and terminal spec to a **different fresh leaf** is
allowed. The output bytes, module fingerprints, and validation identity must
be identical because the destination and lock metadata are excluded from the
identity. Replay to an existing leaf is forbidden.

## Fail-closed boundaries

- Missing argv bindings, unresolved placeholders, stale hashes, failed jobs,
  duplicate run/job IDs, extra/missing/reordered argv tokens, extra/missing
  files or directories, duplicate JSON keys, unsafe times, dependency overlap,
  and identity/hash mismatches block publication.
- `aggregate_cells.csv` is rejected by name during inventory before opening.
- Every decoded JSON key and string value in inputs and outputs is scanned
  recursively after Unicode normalization. The enumerated private-path and
  credential patterns include marker strings even after underscores, generic
  secret-shaped keys such as `api_key`, credential flags/URLs, authorization
  tokens, and private-key material. Exact public projection allowlists provide
  the second boundary. This is an enumerated scan, not a claim to detect every
  possible secret encoding.
- Success attests only normalization, byte provenance, sanitation, and the
  stated runner-recorded/hash-consistent checks. It does not validate
  coefficients, numerical existence, estimands, or a manuscript claim.

Run the adversarial synthetic suite from the repository root with:

```bash
python3 -m pytest -q yax/revision/substantive_v3_20260906/gate1_transfer/tests
```
