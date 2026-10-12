# Whole-corpus narrow release

This package registers the completed October 3, 2026 semantic-narrow base as a
research release without extracting text, changing the parser, or copying the
204.8-million-row table.  The release is an immutable catalog plus SQL view
definition over the retained 2,464 ad-level Parquet shards and their 2,464
duration sidecars.

The scheduled verifier reads JSON receipts and Parquet metadata only.  It does
not read column data.  It checks the exact shard set, freshly hashes each small
receipt and verifies its binding to the batch marker, verifies that the
marker and receipt agree on their previously recorded data hashes, and checks
footer row counts and schema consistency.  It does not freshly hash the base
Parquet files.  Candidate-join files are checked against manifest sizes, footer
rows, and one common schema; their manifest-recorded hashes are required but
are not freshly recomputed.  The five already-published T2/T3 aggregates and
the copied T1/T4 outputs are freshly hash-checked.  It then writes:

* `CORPUS_RELEASE_RECEIPT.json`, a sanitized aggregate receipt;
* `CORPUS_RELEASE_CATALOG_PRIVATE.jsonl`, the private path and hash catalog;
* `CORPUS_RELEASE_VIEWS_PRIVATE.sql`, zero-copy DuckDB view definitions;
* `SCHEMA_PUBLIC.json`, the field inventory without private paths or keys; and
* copies of the five already-computed T2/T3 aggregate CSVs under `reused/`.

The full ad-level base has 204,774,035 canonical US rows, of which 204,768,752
are engineering-usable.  `usable` is a parse-completeness state, not semantic
validation.  Experience and technology outputs remain old-version candidate
measures.  Occupation/task prior experience is structurally unavailable and
must remain `NA`.  Observation dates do not identify historical text versions.
Predictive-AI is frozen all-zero/unmeasurable under the old vocabulary.
Candidate false or non-detection never establishes semantic absence.

The release does not claim a full row-level Records/O*NET metadata join.  T4
retained full-corpus cohort and concentration aggregates, but its temporary
204.8-million-row joined tables did not survive.  The retained 6,010,975-row
comparison join is candidate-only and is not part of the whole-corpus denominator.
It is included in the query package as the separate
`linkup_candidate_metadata_join_v1` view.  Its 6,010,975 rows must never replace
the 204,774,035-row corpus denominator.

On Kunshan, the completed private query package is:

`/public/home/lilysharp/linkup_analysis_execution_oct02/corpus_release_20261012/private/release_v1`

Register its zero-copy views in DuckDB with:

```text
duckdb research.duckdb < CORPUS_RELEASE_VIEWS_PRIVATE.sql
```

Then query `linkup_corpus_narrow_v1`,
`linkup_corpus_duration_evidence_v1`, or the separately scoped
`linkup_candidate_metadata_join_v1`.  The SQL contains explicit verified file
lists, so duration sidecars cannot be accidentally included in the ad view.

Run only through the scheduler, using `run_corpus_release_ks.sbatch`.  The
production roots are passed explicitly and remain outside Git.
