# Generator usage

The generator's selection phase makes one Arrow batch scan of the complete,
verified full semantic-narrow Parquet frame. DuckDB ranks bounded candidates
within each batch, and the generator writes at most 40 selected keys to a
private manifest. It never reads original text or materializes the full
frame. The batch aggregate counts true strata N and keeps only bounded
hash-ranked candidates (32 core / 40 challenge per stratum). A key-only CSV
is retained only for small fixtures. An existing source locator then uses the selected
`SOURCE_FILE`/`SOURCE_ROW` values to produce a private
`--selected-text` CSV containing exactly those keys and texts.

`private_key` is the compact JSON serialization of the fixed four-field tuple
`[JOB_HASH, SOURCE_FILE, SOURCE_ROW, RECORD_SOURCE_ROW]`. The index metadata
must attest the global uniqueness audit and exact full-frame row count, name
the relevant source receipts, and use that namespace. Its 20 frozen core
strata are `tech_group|experience_group`, where technology priority is
`genAI-use`, `genAI-develop`, `software-use-no-AI`, `software-develop-no-AI`,
then `other`; experience priority is `specific_tool`, `industry_domain`,
`general_work`, then `none`. This priority is only for sampling.

```sh
python3 build_blind_review_pack.py \
  --frame-parquet /private/semantic_narrow_v1/shards \
  --duplicate-job-hash-parquet /private/comparison_join/global_duplicate_job_hashes \
  --frame-metadata /private/full_verified_review_index.metadata.json \
  --heldout-key-manifest /private/heldout_400_keys.json \
  --reviewer-schema ../../execution_oct02_07/reviewer_pack_schema.json \
  --private-output-dir /private/human_review_pack_20261003 \
  --public-receipt human_review/ACTUAL_PACK_RECEIPT.json \
  --repo-root /path/to/repo
```

The Parquet mode derives the compact four-field key, all 20 priority strata,
challenge flags, and created-year display stratum directly from frozen narrow
columns. It admits only `usable=true` rows and excludes every globally
duplicated `JOB_HASH` using the private audit list. No full-frame CSV export or
full occupational join is needed; occupation availability is displayed as
`unknown`.

`verified_full_frame_rows` in the private metadata is the independently
audited count after the fixed `usable` and global-duplicate filters but before
heldout/prior-review exclusions. The receipt then records that true review
frame N, each stratum N and n/N, and all later exclusions.

The actual 400-key heldout manifest is absent locally. The authorized D18
exception creates only a limited human diagnostic, explicitly marked
`heldout_exclusion_unverified`; it excludes all prior-review cases that can be
confirmed in the same four-field namespace and cannot be described as an
independent heldout accuracy check.

```sh
python3 ../materialize_selected_text.py \
  --selection /private/human_review_pack_20261003/selected_source_locator_rows.parquet \
  --source-map /private/source_locator_map.jsonl \
  --text-column DESCRIPTION \
  --max-rows 40 \
  --output /private/human_review_pack_20261003/selected_40_texts.csv \
  --receipt /private/human_review_pack_20261003/selected_40_texts.receipt.json
```

This is phase 2: it runs only on the frozen selected locator rows and verifies
`SOURCE_FILE`, `SOURCE_ROW`, and `JOB_HASH` before opening text. Do not invoke
`build_blind_review_pack.py` again with `--selected-text`, because its current
CLI repeats phase-1 selection. Under D18, preserve the phase-1 receipt's
`heldout_exclusion_unverified` status when preparing the human-facing files.

The receipt reports true full-frame stratum sizes, selected counts and `n/N`,
source receipts, and the D18 status. The private output contains the selected
key manifest, reviewer pack, answer key, and dual-review assignments. It never
writes text, keys, or predictions to the public receipt.
