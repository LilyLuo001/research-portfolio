# Stage C evaluation sample v2

This directory prepares an annotation pack; it does not contain completed human validation and cannot release semantic variables automatically.

The frozen target is 1,000 USA ads: 600 calibration and 400 convention-sealed test. Eight time strata are kept separate: 2015, 2016–17, 2018–19, 2020–22, 2023, 2024, 2025, and 2026 partial. The core contains 800 parser-independent selections. A separately flagged 200-ad supplement is allocated among predicted candidate, predicted noncandidate, and predicted complex paths. Conditional probabilities are stored separately for core and supplement and are not presented as national survey weights.

The frame uses 32 deterministic Kunshan-held description shards that were absent from the old 64-shard pilot. It excludes the union of the 72 recorded development cases/templates/company-scrape IDs and the prior 120 pack, including its observed company-scrape IDs. Exact and conservatively masked template signatures are grouped; at most one ad per observed `Records.COMPANY_ID` is selected. This ID is a company-scrape unit, not a verified harmonized parent employer. Related subsidiaries/sites with different IDs and paraphrased or cross-entity templates may remain across splits. The masked signature is a conservative approximation, not exhaustive near-duplicate detection.

Only `calibration/texts.jsonl` and its blank form should be opened during calibration. `sealed_test/texts.jsonl` is sealed by workflow convention. Neither labeler-facing text file contains parser predictions. `selection_metadata_private.jsonl` is restricted sampling metadata and includes the supplement path solely for design-based reporting.

The sample is a regional file frame. Acquisition order is not known to be random, and the result is not nationally or fully corpus representative. A bounded job-level O*NET lookup index was unavailable, so the current pack does not implement occupation stratification; this is a recorded shortfall, not silently flattened coverage. Text is a delivery snapshot linked to a `CREATED` cohort and is not verified historical point-in-time text.

Run order:

1. `build_exclusion_bundle.py` locally freezes exclusions.
2. `prepare_evaluation_frame.py` scans only keys in selected unused shards, joins the compact Records index, and decodes descriptions only for retained pool row groups.
3. `finalize_annotation_pack.py` applies exclusions/grouping, creates the frozen split, and hashes every artifact.
4. `test_evaluation_pack.py` verifies counts, hashes, blank labels, non-overlap, exclusion rules, and absence of predictions from labeler-facing files.

The initial 260-per-period candidate pool stopped without publishing a pack because the conservative global employer/template grouping left 157 eligible groups in 2020–22 for a target of 160. The frozen extension rule doubles every period's deterministic bottom-k to 520 and reruns the bounded metadata join/text fetch from the cached key projection. It does not alter time targets or substitute outcomes across periods.

Kunshan job `123132130` completed the initial 2,080-row frame and then exited with status `FAILED` as designed on that explicit shortfall; it did not publish a pack. Job `123132322` reused the cached projection, completed the frozen 4,160-row extension, and exited `COMPLETED` after publishing and validating the 1,000-row pack. The final sample-manifest SHA256 is `daeaa6444c3a4adfd8cc7c99a37d02a879000e62c2967fd585c6ed4d08a81a47`.
