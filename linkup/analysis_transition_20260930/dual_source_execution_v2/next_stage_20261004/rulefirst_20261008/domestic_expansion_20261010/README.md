# D63 domestic expansion skeleton

This public skeleton defines the narrow table vocabulary for the two active D63 tracks. It reuses the frozen D57/D61 schema and meanings; it contains no new analysis result and no unverified production code. G2 owns full-corpus processed/pending/excluded inventory and remaining domestic production. Independent QA owns first-five-shard substantive comparison.

The current accepted metadata result covers only the first five-shard keys (424,226 postings). Expansion outputs, inventory counts, and comparisons remain pending. No raw text, private identifiers, row-level outputs, credentials, or speculative claims belong here.

See `FIELD_DICTIONARY_PUBLIC.json` for the stable field meanings and missing-state rules.

## D64 bounded continuation

D64 records the necessary core-priority ruling, minimal engineering repair, and continuation of the existing candidate expansion under the same 64-shard bound. It does not establish semantic pass-through. Candidate expansion is approved as an evidence-bearing layer; the first-five QA did not independently recompute weights or common-support rates, and the 12 targeted evidence items were root review rather than 12 full documents or an accuracy estimate. General and graduate retrieval buckets are not verified feature labels. See [`d64_acceptance/CORE_PRIORITY_DECISION.json`](d64_acceptance/CORE_PRIORITY_DECISION.json), [`d64_acceptance/ROOT_MEASUREMENT_USE_CONTRACT.json`](d64_acceptance/ROOT_MEASUREMENT_USE_CONTRACT.json), [`d64_semantic_packet/TARGETED_SEMANTIC_PACKET_RECEIPT_PUBLIC.json`](d64_semantic_packet/TARGETED_SEMANTIC_PACKET_RECEIPT_PUBLIC.json), and [`D64_ENGINEERING_PATCH_20261010/PATCH_README_PUBLIC.md`](D64_ENGINEERING_PATCH_20261010/PATCH_README_PUBLIC.md).


WZ wave 0001 已完成：production `46220171` 四个子任务成功，QA `46220172` 成功；335,958 postings、1,715,007 evidence rows，旧 4 + 新 4 cross-8 keys unique。此为工程覆盖验收，不是语义 gold 或全库结论。下一波若仅已提交仍保持 pending。


本轮冻结规则生产覆盖以 2,464 个 source-file production shards 为单位：inventory 为 21 accepted、2,443 remaining（KS 1,358/13/1,345；WZ 1,106/8/1,098）。这套分母不能与此前 72 个清洗分区混用。rolling controller 遵循 64 上限、3 lane、afterok QA 和 10 GB reserve；已提交但尚未验收的 16/64 不得写成 accepted 或 complete。


First-five descriptive comparison is complete: producer `46222688` and QA `46222690` passed. Public QA checks passed raw denominators, output hashes, standardized arithmetic, technology partition over 424,225 processed postings, and entry 2×2 denominators. Public outputs remain conditional descriptive aggregates; responsibility wording indicates independent-work/responsibility markers, not uniformly advanced judgment.


最终裁定见 [ROOT_D63_FINDINGS_AND_ACCEPTANCE.json](ROOT_D63_FINDINGS_AND_ACCEPTANCE.json)：first-five comparison accepted over 74 occupation cells; entry marker 449/11,889 = 3.78%; sensitivity direction/range is narrow. 当前生产为 21 accepted、64 bounded pending；这些结果不扩展为全库、语义 gold、人口代表性或因果结论。
