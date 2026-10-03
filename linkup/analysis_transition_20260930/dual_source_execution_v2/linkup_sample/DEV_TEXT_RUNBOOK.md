# Development text handoff

Current state is `repair_submitted_pending`. Slurm job 123581861 failed after four seconds on a shared DuckDB output-file lock. Recovery job 123582600 uses the separate private output directory `run-123582600` and a job-specific DuckDB temporary database; it was pending for priority at the recorded observation. No background process will automatically materialize text after selection completes.

The first gate is the run-specific private core receipt:

```bash
test -f /public/home/lilysharp/linkup_analysis_execution_oct02/private/dual_source_execution_v2/linkup_sample/run-123582600/L1_CORE_RECEIPT_PRIVATE.json
```

After that gate passes, use the existing bounded `materialize_selected_text.py` with:

- selection: `L1_DEVELOPMENT_200_KEYS_PROVISIONAL.parquet`
- canonical locator: `JOB_HASH`, `SOURCE_FILE`, `SOURCE_ROW`, `RECORD_SOURCE_ROW`
- text column: the verified original description column in each regional source
- row cap: 200

The source files remain split across the original regional stores, so first partition the 200-key Parquet by the frozen source manifest's region and build an explicit basename-to-absolute-path map in each region. Run the materializer once per regional partition, merge exactly 200 verified rows, and verify the union of canonical keys. The nested 80 configuration keys must be selected from these already-materialized 200 texts; they do not authorize another source scan.

Before calling the development and evaluation lists final, compute a cryptographic digest of the frozen normalized full text, exclude digest groups found in recoverable historical review material, and keep one deterministic member per repeated-text group. Refill from stable-ranked candidates under the same arm design. Until that step, retain `PROVISIONAL` in filenames and do not claim text-level independence. Evaluation text may be materialized for this exclusion and locking step, but no evaluation labels or semantic outputs may be revealed during development.
