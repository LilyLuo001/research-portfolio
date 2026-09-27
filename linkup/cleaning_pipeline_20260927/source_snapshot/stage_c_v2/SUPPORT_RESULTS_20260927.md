# Stage C v2 support-table audit

## Completed jobs

- `123126482` — full O*NET/remote key, date, interval, and USA Records-coverage audit; completed successfully in 20m11s.
- `123127202` — one-pass remote START_DATE calendar audit; completed successfully in 39s.

## O*NET

The 62 files contain 356,299,258 rows and the same number of distinct `JOB_HASH` values. No null or malformed hashes, duplicate keys, or multi-code conflicts were found. There are 4,651 keys without a nonempty code.

Among 253,210,047 USA Records, 253,127,252 match an O*NET key (99.9673%) and 253,123,825 have one nonempty, format-conforming code (99.9659%). Format conformity does not validate the code against a particular O*NET release, and the unconfirmed O*NET version timing does not establish historical classification.

## Remote support table

The 64 files contain 304,916,642 rows for 295,654,306 distinct keys. Some 9,183,333 keys have multiple rows and 8,888,797 have multiple observed status/detail combinations. These can be sequential changes; this audit does not label them conflicts without overlapping intervals.

Among the same USA Records denominator, 202,888,939 keys appear in the remote table (80.1267%). This is membership by job `CREATED` cohort and is not historical remote-label coverage.

There are 295,654,306 open/missing ends, zero invalid starts, invalid ends, negative intervals, or strict overlaps, and 79,003 boundary-touching intervals. Open intervals remain a separate state. `REMOTE_STATUS=false` means not tagged remote and does not confirm onsite work.

## Calendar diagnostic

All 304,916,642 `START_DATE` strings parsed. The range is 2007-11-08 through 2026-09-05, but 304,579,947 rows (99.8896%) begin in 2024 or later; only 336,695 begin before 2024. `REMOTE_STATUS=true` appears on 24,566,344 rows (8.057%); false appears on 280,350,298 rows.

This concentration makes early-period comparisons especially vulnerable to support-table timing and coverage changes. A match to a job created in an earlier year must not be treated as evidence that its remote label existed in that year.

Machine-readable results are in `results/support_audit_v1/support_summary.json` and `results/remote_monthly_audit_v1/remote_monthly_summary.json`.
