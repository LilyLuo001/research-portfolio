# Release status — 2026-09-28

The enrichment module is frozen at SHA-256
`cf0cf8fae3451d463430c14ebe6bf2a6dcc72b8239589ed2fbeb20ef0c4451c6`.

The 100k Kunshan pilot completed as job 123196678: 13,463,321 bytes in
6 minutes 17 seconds, using 8 processes at approximately 94.5% CPU utilization.
Validation job 123198421 confirmed 100,000 input/ad-status rows and 100,000
unique composite ad keys, 205,849 experience evidence rows, 40,237 technology
evidence rows, zero parse errors, and three truncated/incomplete rows.
Evidence counts reconcile to ad-level counts; evidence keys are subsets of
ad keys, and recorded file hashes and Parquet row counts agree.
These size and runtime measurements precede the subsequent audit-retention
writer change; they are not measurements of that final output schema.

The actual Kunshan-to-Huazhong 4 KiB transfer passed size and SHA verification.
The production transfer helper also passed a live generated-Parquet publish
test: exact manifest, file set, byte counts and hashes agreed, followed by
atomic publication and removal of only the generated source copy. A deliberate
same-size, different-content collision was refused and the source retained.
Huazhong's authoritative user storage figure is 450 GB; no quota query was
performed. New release output is capped at 420 GB.

Full regional semantic jobs have not been submitted yet. The user has
authorized execution; full processing still requires the operational
preparation and conservation gates. Raw data and record-level results are
excluded from Git.

The disposition fixture passed on the actual Python 3.8 / DuckDB 0.9.2
runtime, covering same-shard multiple prefixes, cross-region duplicated keys,
unmatched/non-USA/unknown-country rows, duplicate Records-key rejection, and
verified resume/consolidation. Delayed submission responses caused three
identical tiny fixture jobs (123200001, 123200034, 123200112); all passed.
Bulk submission must resolve uncertain responses by looking up the existing
unique job name before retrying.

The canonical first-prefix benchmark is Kunshan job 123203388. It completed
successfully in 9 minutes 19 seconds and conserved 18,654,989 occurrence rows
into 778,999,716 bytes of prefix fragments. Scaling that observed prefix by
row count gives a 12,472,065,406-byte linear full-prefix projection; the
predeclared 25% skew guard gives 15,590,081,757 bytes. The preparation
controller initially paused before the remaining prefixes because the original
fixed fragment budget was 12,000,000,000 bytes. This was an operational capacity
gate, not a semantic failure; the measured capacity decision below supersedes it.

Job 123203487 was a duplicate recovery submission and was canceled after the
canonical job was identified. The earlier job 123201568 failed before heavy
work because its projection path acquired a second `.parquet` suffix; its
failure evidence remains part of the audit trail. Full regional semantic jobs
have not yet been submitted at this checkpoint.

The user's queue policy is: bounded Kunshan tests may use a more expensive
queue when it is actually faster and idle; full runs stay on inexpensive or
free resources. Do not migrate or restart work that is already running solely
to change queues. Huazhong remains the persistent storage destination. The
user confirmed 450 GB is available there, so the pipeline must not issue a new
Huazhong capacity query.

## Measured capacity decision and resumed execution

A bounded Kunshan home usage check measured 477,723,761,664 allocated bytes
against the existing 498,000,000,000-byte operating ceiling. This was a Kunshan
check only; Huazhong capacity was not queried. The measured prefix-0 fragment
allocation was 789,715,968 bytes.

The preparation controller now permits 16 GB of fragments. The remaining-prefix
watchdog covers published and attempt fragments together (16 GB cap), with a
separate 2 GB scratch cap. Consolidation checks a 17 GB intermediate cap before
and after each shard. Existing lifecycle rules remove the generated Wuzhen
key-staging copy after all prefixes pass and remove each generated fragment
set only after its consolidated sidecar is sealed. Raw data are retained.
Kunshan's semantic output buffer is reduced from 8 GB to 4 GB; Wuzhen's is
unchanged. Shared-filesystem free space is not evidence of team quota.

The single server supervisor submitted job **123204704**, observed **RUNNING**
in `kshctest02` with an active preparation lock and a passing capacity gate.
It processes the remaining 15 prefixes. There was no manual parallel submission.
The frozen preparation core and input configuration hashes were unchanged.
The supervisor is intended to continue through consolidation and regional
semantic submission; neither that future submission nor full completion is
claimed as achieved here.
