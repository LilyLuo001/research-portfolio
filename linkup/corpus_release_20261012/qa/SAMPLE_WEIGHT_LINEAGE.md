# Sample and weight lineage for the Formal800 release

Date: 2026-10-12  
Scope: read-only design audit of existing code and receipts. No records were sampled, reviewed, extracted, or recomputed.

## Decision

Keep the released Formal800 estimand as the finite, post-exclusion fixed10k description using `w3 = 1/pi3`. This is a defensible probability result for the 9,282 eligible advertisements in the realized fixed10k frame. It is not a full-corpus prevalence estimate and it does not represent all advertisements in the supported occupations.

Do not expand the 800, start another review loop, or enable parent-frame inference in the current release. The apparent absence of C-arm upstream weights is recoverable from existing artifacts, but correcting that metadata alone does not resolve the estimand change created by the 718 prior-exposure exclusions. A single scheduled metadata audit is the appropriate next step if a parent screened-frame sensitivity is wanted later.

## Scheduled correction addendum

The authorized metadata-only audit is complete. Wuzhen job `46396281` completed successfully in two seconds with 2 CPUs and 4 GB. The final receipt is [`WEIGHT_LINEAGE_AUDIT_RECEIPT.json`](../weights/WEIGHT_LINEAGE_AUDIT_RECEIPT.json); its SHA-256 is `0ba9f498227ce6c57334505f73d862a1b5a294b3d305f59ce23a60f16b65a0bb`. The audit binds the accepted Formal800 freeze receipt to the exact 10,000-row frame hash, rejects null canonical keys, and verifies every frozen 800 linkage arm against its source record.

The scheduled result confirms 10,000 unique fixed-sample keys; arm counts 4,000/4,000/2,000; 69 accepted allocation cells per arm; no missing dedicated probability or weight fields; and exact frozen-800 reconciliation at 320/320/160. The 2,000 C records have structurally null legacy A/B fields but complete dedicated fields. The largest `nested_design_weight × total_inclusion_probability - 1` absolute error is `2.22e-16`. Therefore the earlier “2,000 missing upstream probabilities” wording is corrected to “2,000 structurally null legacy A/B fields; dedicated C probabilities and weights verified.”

The 718 exclusions and 9,282 eligible count remain attributed to the hashed frozen receipt; the metadata audit did not reread text, rerun normalization, or reconstruct excluded-record weight mass. The published finite estimand remains unchanged and parent inference remains disabled. [`RUN_HISTORY.json`](../weights/RUN_HISTORY.json) preserves the failed shell attempt, the canceled overbroad attempt, the initial metadata receipt, independent static QA, and the final corrected run.

## What the existing design identifies

The fixed10k has three mutually exclusive old-rule arms in 69 occupation-major × census-region × created-year cells:

| Arm | Fixed10k count | Parent/source frame documented by the sampler | Existing probability lineage |
|---|---:|---|---|
| A | 4,000 | 10,075 explicit GenAI-use candidates; all 10,075 were in the earlier formal frame | Earlier-stage probability × 4,000-within-cell subsampling probability |
| B | 4,000 | 1,064,428 traditional-software-use/no-detected-AI candidates; 30,225 were selected into the earlier 40,300 formal frame | Earlier-stage probability × 4,000-within-cell subsampling probability |
| C | 2,000 | 83,070 residual records inside the upstream technology-screened joined frame | Direct within-cell probability `selected_cell_arm_n/frame_cell_arm_N`; it is not nested in the A/B 40,300 draw |

Thus “the 40,300 frame” is accurate for the earlier A/B formal sample, not for C. The combined parent target, if ever used, must be named the **69-cell technology-screened candidate frame** (A+B+C under the frozen old classification). C is neither an all-job background group nor an untreated group. The sampler receipt and final QA explicitly preserve this limitation.

Formal800 then excludes every fixed10k ad whose exact or normalized context was previously exposed. It removes 718 ads (A 339, B 239, C 140), leaving 9,282 eligible ads. The third-stage sample is 800 ads (A 320, B 320, C 160) from six arm × entry-candidate strata. All short candidate strata are censuses and the balance is reallocated only to the no-hit stratum in the same arm. The result contains 719 distinct primary contexts; 160 ads, representing 153 contexts, receive blind audit. Context reuse changes reading workload, not the ad-level probabilities.

For this realized finite target, each sampled ad has

`pi3 = n_h / N_h`, and `w3 = N_h / n_h`,

where `h` is arm × frozen entry stratum after exclusions. The receipt supplies all six `N_h` and `n_h` values. This supports finite-frame totals, means, ratios, unknown bounds, and the stated stratified finite-population variance. It does not require any upstream weight.

## The C weights are present; the freeze check used the wrong completeness rule

The fixed10k construction code writes, for every C record:

- `original_inclusion_probability = 1`;
- `conditional_inclusion_probability = selected_cell_arm_n / frame_cell_arm_N`;
- `total_inclusion_probability` equal to that conditional probability; and
- `nested_design_weight = frame_cell_arm_N / selected_cell_arm_n`.

The public allocation has 69 C rows and the final sample QA reports C frame total 83,070, selected total 2,000, positive probabilities in every cell, and complete dedicated C probability fields. The exact-text cache receipt records that the same 10,000-row sample hash was used and that all probability/weight columns were retained with the Arrow schema preserved.

The Formal800 freeze code nevertheless marks all 2,000 C rows as missing. Its loop requires **both** the legacy pair `inclusion_probability`/`design_weight` and the dedicated pair `total_inclusion_probability`/`nested_design_weight`. Final-sample QA had already documented that the legacy pair is A/B-only and intentionally null for C, while the dedicated C fields are complete. Therefore:

- the dedicated C probability is not statistically missing and need not be imputed;
- the `upstream_probability_status: missing 2000` receipt value diagnoses a validator/completeness-definition mismatch;
- the original Formal800 decision to leave parent inference off was conservative and should remain unchanged for this release; and
- a correction must validate the existing dedicated fields by key and cell, rather than fill the null legacy fields with invented values.

## Why repaired C metadata does not automatically authorize a parent estimate

The main finite estimand excludes 718 fixed10k ads because their contexts were previously exposed. Those exclusions are fully observed within the fixed10k, so `w3` correctly describes the remaining 9,282 ads.

For a parent screened-frame estimand, however, multiplying by `nested_design_weight/pi3` after deleting those 718 records does not by itself estimate the original A+B+C parent frame. The deletion occurred after the fixed10k draw, and the release has not defined or observed the same prior-exposure restriction for every unit in the parent frame. The resulting target would otherwise be an ambiguous hybrid: parent expansion of the eligible part of a realized second-stage sample. The exclusions also carry substantial design mass: the freeze receipt reports 69,076.5006 of known A/B nested weight plus 140 excluded C ads whose dedicated weights were misclassified as missing.

A future parent analysis must choose one of two explicit targets before calculation:

1. **Original technology-screened candidate frame.** Treat the excluded fixed10k ads as outcome-missing sampled units, retain their existing upstream weights, and report bounded or otherwise prespecified missing-outcome treatment. Do not silently drop their parent mass.
2. **Parent frame restricted by prior exposure.** Establish the exclusion indicator for the entire parent frame under an exact frozen rule. This requires a separately justified parent-frame hash operation and is outside the current no-new-processing default.

Neither target is the full LinkUp corpus, all jobs in the occupations, or a historical technology-adoption population. The existing third-stage variance calculation also covers only the Formal800 draw conditional on the fixed10k; a parent inferential release would need a variance method that reflects the earlier sampling stages or must be labeled a weighted descriptive sensitivity without parent-design confidence intervals.

## Completed one-pass metadata scope

The completed audit used the existing fixed10k Parquet, frozen 800 linkage, hashed freeze receipt, and existing 207-row allocation CSV. It did not read advertisement text or semantic review content and did not create a new sample.

The audit should emit only aggregate counts, tolerances, hashes, and status, and verify in one pass:

1. exact input hashes and 10,000 unique canonical keys;
2. arm counts A 4,000, B 4,000, C 2,000 and 69 cells per arm;
3. per arm-cell `N`, `n`, and selected-row reconciliation to the allocation CSV;
4. completeness, positivity, and `<=1` for the dedicated probability fields;
5. `total_pi = original_pi × conditional_pi` and `nested_design_weight × total_pi = 1` within a declared numerical tolerance;
6. C legacy A/B fields are null by design while C dedicated fields are complete;
7. counts and dedicated weight mass of the 718 excluded ads, separately by arm and exclusion reason; and
8. counts and dedicated weight mass in all six post-exclusion Formal800 strata.

The passing audit corrects the lineage description from “2,000 missing upstream probabilities” to “2,000 legacy A/B fields structurally null; 10,000 dedicated probabilities verified.” It does not alter the released estimates. Any separately named parent screened-frame sensitivity still requires the root decisions below.

## Metadata required for any later parent sensitivity

The existing private row-level source should retain: canonical ad key; arm; occupation major, region, and created year; `frame_cell_arm_N`; `selected_cell_arm_n`; original, conditional, and total inclusion probabilities; nested design weight; exact and normalized context hashes; exclusion indicator and reason; post-exclusion entry stratum; `N_h`, `n_h`, and `pi3`; audit indicator; and semantic outcome missingness. Public output needs only cell/arm totals, weight-mass totals, input hashes, tolerances, and pass/fail status.

Root must make three decisions before any parent result is produced:

- name the target as the technology-screened candidate frame and accept that C is a restricted residual;
- choose original-parent bounds/missingness treatment versus a fully defined parent-wide exposure restriction; and
- choose a valid multistage uncertainty method or label the result descriptive and omit parent-design confidence intervals.

Absent those decisions, the current finite fixed10k result is the appropriate terminal research result.

## Evidence

- [`formal800_20261012/METHODS_ESTIMANDS.md`](../../formal800_20261012/METHODS_ESTIMANDS.md)
- [`formal800_20261012/receipts/FORMAL800_FREEZE_RECEIPT_PUBLIC.json`](../../formal800_20261012/receipts/FORMAL800_FREEZE_RECEIPT_PUBLIC.json)
- [`formal800_20261012/EXECUTION_LEDGER.md`](../../formal800_20261012/EXECUTION_LEDGER.md)
- [`formal800_20261012/code/freeze_formal800_sample.py`](../../formal800_20261012/code/freeze_formal800_sample.py)
- [`analysis_transition_20260930/dual_source_execution_v2/linkup_sample/build_l1_sample.py`](../../analysis_transition_20260930/dual_source_execution_v2/linkup_sample/build_l1_sample.py)
- [`analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/linkup/build_fixed_research_sample.py`](../../analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/linkup/build_fixed_research_sample.py)
- [`analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/linkup/artifacts/run-123660254/SAMPLE_EXECUTION_RECEIPT.json`](../../analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/linkup/artifacts/run-123660254/SAMPLE_EXECUTION_RECEIPT.json)
- [`analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/QA_FINAL_SAMPLE.json`](../../analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/QA_FINAL_SAMPLE.json)
- [`analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/text_handoff_20261007/FIXED10000_EXACT_TEXT_CACHE_RECEIPT.json`](../../analysis_transition_20260930/dual_source_execution_v2/next_stage_20261004/text_handoff_20261007/FIXED10000_EXACT_TEXT_CACHE_RECEIPT.json)
- [`retrospective_20261012/ARTIFACT_REUSE_AUDIT.md`](../../retrospective_20261012/ARTIFACT_REUSE_AUDIT.md)
- [`formal800_20261012/RESULTS_ZH.md`](../../formal800_20261012/RESULTS_ZH.md)
