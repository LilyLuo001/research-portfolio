# Kunshan bounded V4 candidate/performance run

- Successful retry job: `123130531`, `kshctest02`, 8 CPUs, 12 GB requested.
- Scheduler result: `COMPLETED`, exit `0:0`, elapsed 00:02:01, TotalCPU
  06:25.289, batch-step MaxRSS 783,920 KiB.
- Runner identity: `5c7817f81f4b617e514ad41ac17d229179b43aa41ba789276d6cbd36e969cb35`.
- 16,000 rows, 13,235 candidate and 2,765 no-candidate rows; zero parse
  errors and zero truncated rows.
- Runner wall 107.479 seconds; summed worker CPU 383.848 seconds; maximum
  reported worker RSS 265.680 MiB. Observed throughput was about 148.9 rows per
  wall second.
- Selected-row projected Arrow bytes 62,523,472 and raw description UTF-8
  bytes 61,883,472.
- Four candidate Parquet shards total 59,488,322 bytes; total output directory
  59,508,234 bytes under the 250,000,000-byte cap.
- Each shard's SHA256, file size, schema and 4,000-row Parquet metadata count
  were independently checked against its receipt. No Parquet file was copied
  locally.
- Remote output:
  `/public/home/lilysharp/linkup_analysis_v1/stage_c_batch_v1/outputs/kunshan_bounded_v1`.

The first attempt, job `123130430`, failed before runner execution with signal
53 and no log or output files. The absent declared log directory plus successful
retry after creating it supports the log-directory diagnosis; Slurm itself
reported `Reason=None`, so the causal attribution remains an inference. Its
failure receipt is preserved in `failed_job_123130430.json` locally and remotely.

Quota preflight used full-home `du -sb`: 472,538,070,449 bytes. Against the
provided 498,000,000,000-byte ceiling this left 25,461,929,551 bytes. Site
`quota -s` and `lfs quota` returned no report.

The 13,235/2,765 statuses are bounded extractor candidate/no-candidate statuses,
not counts of qualified advertisements, validation outcomes, accuracy evidence,
or national estimates. The observed 59.49 MB Parquet output for 61.88 MB of raw
description UTF-8 text and 148.9 rows/second are measurements for this trial,
not a full-corpus runtime forecast.

Wuzhen was not submitted. Read-only discovery found Python 3.8.10 without
PyArrow, `quota -s` returned no report, and the 20-second bounded home `du`
timed out. Its frozen parser exists, but runtime and headroom are not ready.
