# Bounded V4 candidate/performance runner

This package runs the frozen V4 parser on the first 4,000 physical rows of four
deterministically selected raw description files in one region. Selection is by
provider basename and then full path in lexical order. It is a computation and
performance trial. It is not a probability sample, a national sample, a formal
semantic release, or a source of validated binary labels.

The runner reads only `JOB_HASH` and `DESCRIPTION` through Arrow record batches
of 128 or 256 rows. A bounded process pool assigns one file to each worker. It
does not call `read_table` on raw inputs and does not hash, edit, move, or delete
raw files. Existing audited raw SHA256 values are identity metadata; current
path, size, and stat mtime are checked without generating a new full-file hash.

Each source file produces one atomically renamed Parquet shard and one exclusive
receipt. Every row is retained, including no-candidate and parser-error rows.
`CANDIDATE_JSON` retains the complete parser response and normalized text, so
evidence offsets remain exactly resolvable. Fields such as
`qualification_expected`, `context_conflict`, and
`qualification_relation_unresolved` remain inside that JSON and are never
converted to validated binary outcomes. Truncation and parse errors have
separate columns and counts. Dates and evidence time semantics remain unknown.

Resume skips a shard only after checking its job identity, source identity,
Parquet schema and row count, file size, and output SHA256. A changed runner,
parser, manifest, configuration, input path, size, or mtime is rejected in an
existing output directory. An exclusive running lock prevents duplicate writers
for the same job. On failure, a worker removes only its own `.tmp.<pid>` file.
This is conservative bounded-run resume, not unattended crash recovery: a hard
kill can leave a stale lock or an atomic output without its receipt, and the
runner then refuses to continue until an operator reviews that job directory.

The first-run persistent-output cap is 250,000,000 decimal bytes. One MB is
reserved for identity and receipts; the remaining budget is divided evenly
across four shards, and total files are checked before the final receipt. The
Slurm wrappers request 8 CPUs and 12 GB but use four
workers. Before execution they display user quota and project `du`, then require
`LINKUP_CONFIRMED_HEADROOM_BYTES>=300000000`; shared `df` capacity is not used as
a quota estimate. The Wuzhen wrapper performs read-only PyArrow discovery and
fails with a clear message when no Python 3.8 runtime is supplied. It installs
nothing.

Worker receipts report actual selected rows, projected Arrow bytes, raw UTF-8
text bytes, output bytes, wall and CPU seconds, rows per wall/CPU second, and
peak RSS. Whole raw-file size is reported separately as storage context rather
than mislabeled as bytes scanned.

No script in this directory submits a job. After copying the reviewed files and
creating the declared log directory, an operator can submit the chosen `.sbatch`
file manually. The frozen parser must retain SHA256
`19da310725580bc0ff12c2088e0c5b969558474eda5f7b92d5ab37a3bd92bfbc`.
