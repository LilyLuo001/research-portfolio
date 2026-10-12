# Artifact reuse audit

Audit date: 2026-10-12. Scope: documentary and public-receipt audit only. This does not rerun a job, inspect raw advertisements, or treat a receipt status as semantic validation.

## What is already complete and reusable

| Asset | Evidence and scope | Reuse status |
|---|---|---|
| Old full base | [`BATCH_RECEIPT.json`](../analysis_transition_20260930/pre_revelio_execution_v1/results/full_semantic_narrow_v1/BATCH_RECEIPT.json) says `complete`, 2,464 shards; [`AGGREGATE_RECEIPT.json`](../analysis_transition_20260930/pre_revelio_execution_v1/results/full_semantic_narrow_v1/aggregate/AGGREGATE_RECEIPT.json) confirms complete aggregate products. D65 records 204,774,035 canonical US ads and 204,768,752 engineering-usable ads. | The default corpus base. Do not relaunch end-to-end extraction or treat newer incomplete coverage as an unfinished base. |
| Old typed evidence | D65 identifies `ad_status`, canonical disposition, experience clause/object offsets, literal duration bounds, technology/role candidates, and sparse `v6_audit`. | Reuse identities, dates/provenance, literal evidence, and candidate flags as **old-version** measures. |
| Frozen old T1--T6 | [`EXECUTION_REPORT_20261003.md`](../analysis_transition_20260930/pre_revelio_execution_v1/EXECUTION_REPORT_20261003.md) and D65 record computed/accepted tables; the report itself limits T2/T3/T5 semantic interpretation and cancels unsupported C2. | Preserve as historical candidate-measure outputs, not as a current semantic certification or a replacement for later estimands. |
| D66 exact overlap | [`RUN_RECEIPT_PUBLIC.json`](../analysis_transition_20260930/reuse_analysis_20261010/public/RUN_RECEIPT_PUBLIC.json): 424,226 exact keys; 424,219 old-usable/current-processed; engineering QA pass. | Reusable bounded five-shard, version-comparison evidence. It is not a representative corpus sample or validation of every old field. |
| D67 frozen convenience wave | [`OVERLAY_69_STAGE_RECEIPT_PUBLIC.json`](../analysis_transition_20260930/reuse_expansion_20261010/public/OVERLAY_69_STAGE_RECEIPT_PUBLIC.json): 69 QA-passed shards (KS13+WZ56), 5,804,936 postings, no full-text/model/API calls. Final [`RUN_RECEIPT_PUBLIC.json`](../analysis_transition_20260930/reuse_expansion_20261010/public/final_results/final/RUN_RECEIPT_PUBLIC.json) passes row, metadata, NA, support, and weight checks. | Reusable additive old/current overlay and descriptive comparison release only; its own receipt excludes full-corpus prevalence and semantic-accuracy claims. |
| Wave02 semantic increment | [`RESULTS_AND_DECISIONS.md`](../analysis_transition_20260930/pro_review_wave02_20261012/RESULTS_AND_DECISIONS.md): 96 purposively selected contexts in KS13, 71 field changes across 49 ads; before/after aggregates published. | Reuse exact reviewed decisions and their direct aggregate correction only. Do not extrapolate purposive corrections to corpus error rates or apply them by fuzzy matching. |

## Field-level gaps and conflicts

[`FIELD_REUSE_MAP_PUBLIC.json`](../analysis_transition_20260930/reuse_analysis_20261010/FIELD_REUSE_MAP_PUBLIC.json) is the operative field inventory.

- **Directly reusable:** four-key identity (`JOB_HASH`, `SOURCE_FILE`, `SOURCE_ROW`, `RECORD_SOURCE_ROW`); old general-work, tool, and industry candidate flags; clause-level literal bounds/units/strength/binding; old technology candidates; completed joins where their time provenance is retained.
- **Candidate, not gold:** all old/new rule-derived experience, technology, waiver, alternative-qualification and uncertainty flags. A non-detection is not absence; a literal number is not automatically a universal job minimum.
- **Structurally missing in old release:** occupation/task prior experience is `NA`, not zero; a complete graduate/junior inventory; current-duty responsibility and its binding to newcomer/qualification wording. `v6_audit` is selective evidence, not a complete task/responsibility inventory.
- **Do not collapse versions:** old and rule-first taxonomy/role/conditional semantics differ. Equal canonical keys permit a measurement-version comparison, not semantic ground-truth validation. The old no-experience unconditional flag is structurally false for explicit no-experience candidates, so its zeros are unavailable rather than observed negatives.
- **Time conflict:** JOB_HASH is a URL tracker, not a text-version identifier. Posting/observation dates support coverage and risk descriptions, not historical-text claims.

## Denominators and the remembered “20% usable” claim

“Usable” in D65 is an **engineering parse state**: no `DESCRIPTION_EMPTY`, `PARSE_ERROR`, `INPUT_EVIDENCE_TRUNCATED`, or `ENRICHMENT_INCOMPLETE`; it is not semantic accuracy. The old base's 204,768,752 / 204,774,035 engineering-usable canonical US ads is about 99.9974%, so no receipt supports “only 20% of all extracted data usable.”

The documented nearby 20-ish number is the old C1 software-arm common-support retention (22.2%), a comparison-sample retention statistic. D65 also notes hypothetical 10--20% exception/cost planning language. Neither is a corpus usability rate. D67 has a different denominator: 5,804,936 completed-output postings, of which 5,804,788 were old-usable matches; it must not replace the 204.8m base denominator.

## Actual T1--T6 deliverables

The completed October 3 release delivered: T1 coverage/funnel; T2 three measured experience dimensions plus duration sidecar and explicit unmeasured occupation/task status; T3 technology/role candidates and overlap; T4 date-risk/concentration plus 12 groups/200 fixed annual cases; T5 fixed software-versus-AI common-support comparison with C2 cancelled for insufficient support; T6 fixed sensitivities. The current rule-first table family also uses T1--T6 labels, but its estimands differ: a frozen candidate sample, four experience objects including current-only occupation/task, lexical technology arms, created-year snapshots, co-occurrence, and availability/sensitivity. Same labels do not make tables interchangeable.

## Decision-ready conclusion

Treat the old 2,464-shard extraction as complete; reuse D66/D67 only as versioned additive overlays; reuse Wave02 only as exact, bounded review corrections. The remaining work is named-field evidence/semantic scope, not basic cleaning. Any proposal that says the base is unfinished, calls sparse-audit non-detection absence, converts old occupation/task `NA` to zero, uses a D67/Wave02 denominator as full corpus, or calls 20% a verified usable share conflicts with the receipts above.

## Verified fixed10k reuse contract

The fixed10k is a recoverable finite text frame, not an unobserved future sample. [`SAMPLE_EXECUTION_RECEIPT.json`](../analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/linkup/artifacts/run-123660254/SAMPLE_EXECUTION_RECEIPT.json) defines a fixed sample with A/B nested in the earlier40,300 design:4,000 A (explicit GenAI-use candidate),4,000 B (explicit traditional-software-use candidate with no detected AI), plus2,000 C drawn directly from the residual technology-screened candidate frame. C is neither nested in the A/B40,300 draw nor an all-job background. It retains total inclusion probability and inverse nested weight. [`FIXED10000_EXACT_TEXT_CACHE_RECEIPT.json`](../analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/text_handoff_20261007/FIXED10000_EXACT_TEXT_CACHE_RECEIPT.json) verifies 10,000 nonempty texts and 7,635 exact unique texts with probability/weight fields retained; private selection/source maps and materializers exist. This permits one finite probability-based semantic analysis without text re-extraction, while retaining candidate-arm and no-human-gold limitations. Its 69 support cells are not D67's 69 QA-passed shards.


Correction after cloud probability audit46396281: all10,000 dedicated total inclusion probabilities and nested weights are complete;2,000 null legacy A/B fields belong to C by design. Preserve the Formal800 finite9,282-ad target and frozen estimates. See [weight audit](../corpus_release_20261012/weights/WEIGHT_LINEAGE_AUDIT_RECEIPT.json) and [root decisions](../corpus_release_20261012/ROOT_DECISIONS.md).
