# D59 targeted metadata linkage

This pipeline attaches Records employer/lifecycle fields and the current-delivery O*NET occupation to frozen D58 posting keys. It does not rerun text rules, change semantic evidence, or restrict the frame to the older 6,010,975-row technology candidate release.

The accepted initial denominator is 424,226 canonical USA postings. Every final row retains `JOB_HASH`, `SOURCE_FILE`, `SOURCE_ROW`, and `RECORD_SOURCE_ROW`. Records linkage uses `(JOB_HASH, RECORD_SOURCE_ROW)`; O*NET linkage uses `JOB_HASH`. The final operation is a left join that must preserve the complete posting denominator.

## Frozen source inputs

- Records index: `/public/home/lilysharp/linkup_analysis_v1/stage_b/records_index_v1/hash_prefix=*/*.parquet`, 15,415,489,237 bytes. Required projection: `JOB_HASH`, `RECORD_SOURCE_ROW`, `COMPANY_ID`, `CREATED`, `LAST_CHECKED`, `DELETE_DATE`, `STATE`.
- O*NET snapshot: `/public/home/lilysharp/dewey_downloads/data/dewey_ONET_tables/onet-taxonomy/*.parquet`, 11,190,966,290 bytes. Required projection: `JOB_HASH`, `ONET_OCCUPATION_CODE`.
- Official occupation codes: `/public/home/lilysharp/linkup_analysis_execution_oct02/private/official_onet2019_occupations.csv`; the file digest must match the earlier verified release.

Records plus O*NET total 26,606,455,527 bytes. D59 permits a 35,000,000,000-byte retained metadata source cache, leaving 8,393,544,473 bytes before the official-code file, hit projections, and receipts. The task-wide budget remains separate. Source files are transported once by Sol's credential-owning controller, verified against a frozen per-file size/SHA inventory, and retained. No second credential owner or competing writer is allowed.

No verified full-frame thinner row-level cache exists. The old `candidate_onet` projection is restricted to the older candidate frame, while T4 retained cohort and concentration aggregates rather than JOB_HASH-level metadata.

## Scheduled BU stages

1. `prepare-keys` reads the five verified posting outputs on BU, asserts canonical locator and JOB_HASH uniqueness, and writes 16 hash-prefix key files. The public receipt binds every key-file row count, byte count, and SHA.
2. The transport controller retains the 26.6 GB verified source cache. It groups cached files into extraction specifications of at most 10,000,000,000 bytes. `extract-batch` runs as scheduled BU work, scans only required columns, writes matching Records or O*NET rows, and binds each staged source file and hit output by SHA. The retained source files are not deleted.
3. A private Records extraction manifest and a private O*NET extraction manifest enumerate every frozen source exactly once. Their source inventory digests and exact byte totals are required by `finalize`.
4. `finalize` reads all hit projections once, audits multiplicity before selecting values, and writes exactly one metadata row per posting key. Missing Records/O*NET rows, missing company/state/code, placeholder and unofficial occupation codes, and unmapped states remain separate states.

Any Records or O*NET one-to-many match blocks completion; the code never chooses an arbitrary value. A disagreement between posting and Records `CREATED` calendar dates also blocks completion. Missing or unofficial values do not remove rows. `COMPANY_ID` remains a scraper company identity, O*NET is the current delivered snapshot, and Records dates are observation metadata rather than body-version dates.

The implementation uses bounded PyArrow streaming and requires Python 3.8+, `ParquetFile.iter_batches`, `Table.to_pydict`, `Table.from_arrays`, and Zstandard support. DuckDB is not required. Runtime capabilities and versions are written to receipts. Lightweight import/version inspection may run on a login node; all research-data reads and joins must run through the BU scheduler.

For subsequent production, accumulate newly verified posting keys into a grouped metadata wave and scan the retained source cache once for that wave. Do not rescan all 26.6 GB separately for each small source shard.
