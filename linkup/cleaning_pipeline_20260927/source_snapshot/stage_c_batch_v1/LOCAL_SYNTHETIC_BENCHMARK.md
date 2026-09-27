# Local synthetic sizing check

An unsubmitted local end-to-end check processed four temporary Parquet files,
4,000 rows each, with batch size 256 and four workers. It used the frozen V4
parser and the same runner path as the Slurm scripts. The temporary inputs and
outputs were removed when the check completed.

Observed on the local macOS host with Python 3 and PyArrow 24.0.0:

- 16,000 rows in 3.30 wall seconds; summed worker CPU 9.11 seconds.
- Maximum per-worker `ru_maxrss`: 98.27 MiB.
- Candidate/no-candidate/parse-error rows: 12,000 / 4,000 / 0.
- Projected selected-column Arrow bytes: 1,952,000; raw description UTF-8 bytes:
  1,312,000.
- Candidate Parquet output: 1,536,328 bytes; all persistent output including
  identity and receipts: 1,550,930 bytes.

This is a plumbing and lower-bound sizing check using four short repeated text
patterns. It is not an HPC performance prediction: real advertisements are
longer and more varied, output compression differs, and Linux worker RSS and
filesystem throughput must be taken from the bounded regional run receipts.
