# Stage C evaluation v2 run report

The annotation-preparation target was achieved: 1,000 new USA ads from a Kunshan regional shard frame, with 600 calibration records and 400 convention-sealed test records. The sample contains an 800-record parser-independent core and a separately flagged 200-record prediction-path supplement. It is an annotation pack awaiting external human review and adjudication, not completed validation and not an automatic semantic release.

Time counts are frozen at 100 (2015), 130 (2016–17), 130 (2018–19), 160 (2020–22), and 120 each for 2023, 2024, 2025, and 2026 partial. All 32 selected description shards were absent from the prior 64-shard pilot and all 32 appear in the final pack. The frame is not a national or full-corpus probability sample. No bounded job-level O*NET lookup index was available, so occupation stratification remains an explicit shortfall.

The exclusion union contains the 72 recorded development cases plus the prior 120 pack, including their recorded templates and observed company-scrape IDs. In the 4,160-row extended pool, 597 rows were excluded by observed company-scrape ID and seven by exact prior template. Conservative grouping removed 1,470 repeated observed company-scrape IDs and two exact templates, leaving 2,084 groups. The final selection has 1,000 unique observed `Records.COMPANY_ID` keys, exact normalized hashes, and conservative masked signatures, with zero overlap of those chosen keys across splits. `Records.COMPANY_ID` is a company-scrape unit, not a verified harmonized parent employer. Related subsidiaries/sites using different IDs and paraphrased or cross-entity templates may still cross splits; the masked signature is not exhaustive near-duplicate detection.

Kunshan job `123132130` produced the initial 2,080-row frame but stopped during finalization because the 2020–22 layer had 157 groups for a target of 160. No incomplete pack was published. The one-time extension rule had already fixed the response: double bottom-k to 520 per layer, reuse the cached key projection, preserve period targets, and stop again if any target remained short. Job `123132322` completed that 4,160-row frame and the final pack. Remote full validation passed all row, period, hash, blank-label, exclusion, grouping and split checks.

The sealed test text remains remote-only at `/public/home/lilysharp/linkup_analysis_v1/stage_c_evaluation_v2/annotation_pack_v1/sealed_test/texts.jsonl`. It was not downloaded or displayed to a model. A 32-record model-diagnostic subset was mechanically selected from calibration-core records only with seed `diagnostic32-20260927`, four per time stratum; its manifest records `sealed_test_accessed: false`.

Frozen checksums:

- Final sample manifest: `daeaa6444c3a4adfd8cc7c99a37d02a879000e62c2967fd585c6ed4d08a81a47`
- Grouping quality report: `72ed73b4dcbd8834226015127e677a4c5b596242f6fba0f782b199888b31d49c`
- Coverage report: `2cb5d733447a98f6246bb1143b5b2cda59b7d3019ca51832968386a80fc2b2e7`
- Source-selection manifest: `f244a9dd890b598baf4fae06cdc8dc5d13ba287e4e4957fb314f45f03a7ada5e`
- Final frame report: `95124cca97a6157c6c87a21d9bf94dc44bdd3ee47d7fe9b9242720d032361850`
- Diagnostic32 texts: `c98c06db979e5b5cf4b8ee23cd09ba8c21d19a371babc7382cfb2260a42111b1`
- Diagnostic32 hidden mapping: `66fdfb7d43e2b45941dec53850478e0f5ec21e99673a32cf2364eef247282e97`

The provisional evaluation contract reports presence false positives/false negatives, strength confusion including unknowns, numeric/unit/object/path binding, experience object, technology role and task families overall and by time. Its numeric gates are explicitly engineering proposals, not universal validity thresholds. Comparative release also requires measurement-error changes to be small relative to a minimum detectable effect fixed before parser results. Human-label fields remain blank and automatic release is disabled.
