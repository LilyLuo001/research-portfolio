# Formal 800 preproduction QA

Date: 2026-10-12

Status: provisional design audit; code and cloud receipts remain pending. This memo contains no advertisement text, record identifiers, row-level decisions, or local research computation.

## Acceptance contract

The scientific target is a finite, explicitly post-exclusion subset of the already frozen fixed10k candidate frame. It is not the 204.8 million-ad corpus, the D67 convenience wave, or an occupation-wide background frame. Arms retain their frozen candidate meanings: A is explicit GenAI-use candidate, B is explicit traditional-software-use candidate with no AI detected, and C is the residual inside the upstream technology-screened candidate frame.

Sampling uses advertisements as the probability unit and exact UTF-8 text SHA-256 only as the semantic-reading reuse unit. Historical development, review, and locked-evaluation exposure is excluded by the union of exact-text hashes before eligible ad counts, allocations, or random ordering are computed; therefore every fixed10k ad sharing an exposed exact context is excluded. The exclusion receipt must report, by arm and reason, both unique contexts and fixed10k ad rows, plus overlap between reasons. Excluded contexts redefine the finite eligible target and cannot be silently treated as zero-probability members of the original fixed10k target.

To preserve the ad-level finite-frame estimand and the approved cap, select at most 800 eligible ads within frozen arm x entry-candidate/no-hit strata. Within a stratum, the third-stage probability is `pi3 = selected_ads / eligible_ads`. Only after the ad sample is frozen may byte-identical complete semantic contexts be grouped for one reading. The resulting decision binds to sampled ads in that group only; it is never propagated to unsampled fixed10k ads or beyond the frame. The sample remains at most 800 ads and the number of unique readings is at most 800.

Two estimators are distinct. The main finite eligible fixed10k estimator uses third-stage weight `1/pi3`; it describes the post-exclusion fixed10k frame. An optional parent candidate-frame estimator uses `nested_design_weight/pi3`, equivalently `1/(total_inclusion_probability*pi3)`, only after the upstream probability lineage and identities are verified. A result using the latter cannot be labeled a finite-fixed10k mean. `pooled_cell_standardization_weight` is a separate standardization quantity and must never replace or be multiplied into a design weight without an explicitly named separate estimand.

The fixed allocation is A/B/C = 320/320/160. Each arm is split by the frozen old entry-qualification candidate versus no-hit flag. The allocation rule, including shortage transfer within arm, must be fully deterministic from post-exclusion stratum sizes and fixed before any semantic result exists. Stable sampling rank must hash the unique canonical ad key with the fixed seed, selection-purpose salt, and arm/stratum. Audit rank uses the same unique ad key with an independent purpose salt. Context hash is not a sampling-rank key because duplicate contexts remain separate ad probability units. Ranking must not depend on labels, outputs, review order, filenames that encode results, or retry state.

The independent audit set is a fixed 20% of selected ads (160 if 800 ads are selected), stratified using the same frozen design variables. It must be selected at sample freeze, before primary outputs exist. The audit packet may contain the same source text and frozen schema, but no primary label, explanation, confidence, adjudication status, or result-derived field. Exact duplicates can reduce the number of unique audit readings, but the receipt must retain the 160 ad-level audit indicators and separately report unique audit contexts and any context overlap between audited and non-audited sampled ads. Such duplicates are dependent diagnostic observations, not additional independent semantic evidence. Root adjudication remains capped at 40 contexts and cannot trigger replacement sampling.

## Required preproduction checks

1. Input hashes bind the fixed10k unique-context queue, represented-ad map, and every historical-exposure source used for exclusion.
2. Every eligible ad has a unique canonical key and binds to one exact-text SHA and its own frozen arm/stratum. The same exact context may legitimately occur across arms or strata because candidate metadata vary by represented ad; cross-arm/stratum context reuse is reported and never relabels an ad. Duplicate-context ads remain separate probability units and are grouped only after selection for semantic reading.
3. Candidate/no-hit is frozen from pre-existing fields and is neither recomputed from semantic outputs nor converted from missing/unknown to no-hit without an explicit source-field contract.
4. Post-exclusion context counts, ad counts, allocations, quota transfers, and selected ad counts conserve by arm and stratum. The public receipt contains aggregates only.
5. For every sampled ad, finite-fixed10k weight equals `1/pi3`. For the optional parent-frame estimator, `final_pi = original_inclusion_probability * conditional_inclusion_probability * pi3`, `parent_weight = 1/final_pi`, and `parent_weight = nested_design_weight/pi3` within numerical tolerance. Original design weights and pooled-cell standardization weights remain separate.
6. Selection is byte-identical on rerun with the same input hashes and seed. Changing a semantic result file cannot affect selection because result files are not inputs.
7. Primary and audit assignments conserve sampled ads, duplicate-context overlap is disclosed, and audit packets contain no leakage fields. Packet IDs and framework/schema hashes are fixed; evidence quotes are returned by reviewers and code resolves offsets against exact source text.
8. Receipts state the claim boundary: estimates describe the eligible post-exclusion fixed10k candidate frame (or a still narrower supported comparison), not all LinkUp ads, semantic accuracy of unreviewed ads, human gold, historical change, or causal effects.

## Semantic-output validator gates

JSON Schema validation alone is insufficient. The validator must also enforce the frozen instructions across fields:

- A record with `document_status` other than `reviewed_full` cannot emit any `not_mentioned` outcome or `technology_inventory_status=not_mentioned_after_full_review`.
- An experience `present` outcome requires a same-object, quoted, non-waived clause. A waived-only clause cannot support `present`; `not_mentioned` cannot coexist with a same-object non-waived clause.
- An entry `present` outcome requires a quoted item with the same target.
- A responsibility `present` outcome requires a quoted same-dimension item whose subject is `advertised_worker` and whose relation is `current_duty`, `required_capability`, or `prior_experience`. Other-employee and employer-general material never supports an advertised-worker positive. Strict responsibility statistics use only `advertised_worker` plus `current_duty`.
- `explicit_mentions_recorded` requires nonempty `technology_items`; `not_mentioned_after_full_review` requires a full review and an empty inventory. A nonempty technology inventory does not itself establish work technology: `background_mention` and `unresolved` remain separate from use, development, and implementation.
- Every evidence quote must occur byte-for-byte in the bound complete context. A missing quote rejects the output; a repeated quote records every offset or an explicit ambiguity. There is no normalization or fuzzy repair.
- Year bounds must agree with `years_relation`: `not_stated` has two null bounds; `at_least` only a minimum; `at_most` only a maximum; `exact` equal nonnull bounds; `range` ordered nonnull bounds. Alternative group and branch references are jointly null or resolve to a nonempty, uniquely named declared group and branch.
- Submitted blind IDs and hashes must match the packet exactly, with no missing, duplicate, or unexpected decisions. One semantic payload is reused for identical sampled contexts, but mapping is restricted to sampled ads.

## Open gate

Root fixed the ad-level design described above. Until code passes these gates and a scheduler receipt names the frozen sample, no sample is complete.
