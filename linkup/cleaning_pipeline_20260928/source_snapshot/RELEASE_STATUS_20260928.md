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

Full regional jobs have not been submitted yet. The user has authorized
execution; full processing still requires the operational preparation and
conservation gates. Raw data and record-level results are excluded from Git.
