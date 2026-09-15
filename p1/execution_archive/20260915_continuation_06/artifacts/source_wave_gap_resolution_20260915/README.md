# Source-wave gap resolution

状态：`SOURCE_WAVE_GAP_RESOLUTION_COMPLETE`。47 个 public-universe waves 与 30 个现有 exposure-stock waves 的差集严格为 17。

其中 14 个是固定的 date-valid CRSP U.S. common-stock 构造下的有意 scope absence：9 个 wave 的严格 PRE N-PORT 没有 common-equity candidate，5 个 wave 的候选全部被现有映射明确分类为 non-common 或 non-U.S.。这不等于基金没有持仓，也不证明新时钟或最终合同下为零。另 3 个仍是映射 UNKNOWN：W019 有 5 个 unmatched candidate rows，W031 有 1 个，W047 有 3 个。每个 wave 的 candidate 数都与 mapping-audit rows 对账，状态集合穷尽，17 个 wave 均没有 exact-mapped row。

W006 是同一 2022-05-06 日期桶中的两个独立 predecessor/sponsor：DFA `S000001015→S000075030` 与 JPM `S000003858→S000074055`，不能称为一个 package。前聚合 holdings lineage 保留 series id，因此 fund attribution 可执行。实际 12 个 recovered99 candidate/date-bucket pairs 中，11 个 `DFA_ONLY`，1 个 `BOTH_DFA_AND_JPM`，没有 `JPM_ONLY`；逐候选结果只在 SCC。这个归因说明记录来自哪个 predecessor holdings，不批准 package，也不生成 competing-clean/exclude。

W032 的历史 2024-11-15 是 N-14 proposal；后续完成证据是 2024-12-09，另有 12-06 close-of-business asset-acquisition 线索。它们是 date type/version evidence，不在本阶段选择合同 `I_w`。

独立 adjusted-detail family `rescue/ibes_allcols_det_epsus_2019..2021` 对 W002-high 固定四键的结果与 core/unadjusted-rescue aggregate 相同：PRE 3 键 observed-min2 为 0，POST 1 键为 0；3/4 键有记录，总计 4 rows，analyst histogram 为 `0:1, 1:3`。该来源没有与其他 family 合并，`<2` 仍是 source-completeness 未认证的 UNKNOWN，不是 SUE 排除。

主要文件：`wave_gap_classification.csv`、`w006_attribution_by_focal_wave_tier.csv`、`w006_attribution_receipt.json`、`w032_date_version_conflict.csv`、`adjusted_detail_w002_high_receipt.json` 与 `EXECUTION_RECEIPT.json`。未读取 outcome、forecast value、price、return、quote 或 response。
