# Recovered-99 CORE metadata support

状态：`RECOVERED_CANDIDATE_SUPPORT_FULL_COMPLETE`。本次在用户授权的 SCC-only census 范围内，将 `CORE_IBES_ACTUALS_EPS` 明确指定为诊断主来源；`RESCUE_ALLCOLS_ACTU_EPSUS` 仅保留为上一阶段的对照来源，未合并。本次没有改变 population、tier、PRE/POST、名义时钟或 analyst 规则。

## 先看不含 analyst 条件的支持

99 个 recovered stock-wave 候选中，27 个在完整来源时钟下至少各有一个 PRE 与 POST key；其中仅 2 个在 PRE 与 POST 两侧都至少有一个名义 `[09:30,15:00]` source-clock key。这 2 个均为 W002 low。

| wave | tier | recovered | full-clock PRE+POST | nominal-clock PRE+POST | full-clock observed-min2 PRE+POST | nominal-clock observed-min2 PRE+POST |
|---|---|---:|---:|---:|---:|---:|
| W002 | high | 33 | 1 | 0 | 1 | 0 |
| W002 | low | 36 | 18 | 2 | 13 | 0 |
| W016 | high | 7 | 1 | 0 | 0 | 0 |
| W016 | low | 9 | 1 | 0 | 0 | 0 |
| W025 | high | 3 | 1 | 0 | 0 | 0 |
| W025 | low | 11 | 5 | 0 | 5 | 0 |
| **合计** |  | **99** | **27** | **2** | **19** | **0** |

计数单位是 stock-wave candidate keys，不保证等于不同 PERMNO 数量。时钟只是来源显示时钟；timezone、首发语义与 RTH 均为 `UNKNOWN`，因此 nominal 不能解释为经认证的交易时段。

## Key lineage 与 analyst envelope

CORE 产生 1,151 个 source path rows，来自 1,124 个 distinct source rows；wave-specific source-row-candidate、period、release 和 release-inclusive analyst event keys 均为 1,151。名义时钟 release keys 为 35。它们不是经独立确认的唯一经济事件。

四列 analyst metadata（`cusip, fpedats, analys, anndats`）按固定窗口 `[release-90 days, release)` 计数：525/1,151 event keys 有至少两个已观察 analyst IDs；626/1,151 观察少于两个。前者是 `OBSERVED_SOURCE_MIN2_LOWER_BOUND`，后者因来源完整性未认证而保持 `UNKNOWN_OBSERVED_LT2_SOURCE_COMPLETENESS_UNCERTIFIED`，不是 SUE 或最终资格结论。35 个名义时钟 keys 中仅 1 个有 observed-min2，另外 34 个保持 unknown；两个 nominal-both 候选均未在两侧同时获得 observed-min2。

99 个候选在本次已观察 CORE paths 中均没有 non-unique source-row status，但这不等同于旧的 clean 标志，也不认证其他未观察转换路径。受保护 sidecar `protected_recovered99_event_sidecar.csv` 仅保留在 SCC；本地只有聚合、代码与回执。

详细结果见 [clock support](full_artifacts/candidate_clock_support_by_wave_tier.csv)、[analyst support](full_artifacts/candidate_analyst_support_by_wave_tier.csv)、[key units](full_artifacts/source_key_support_by_wave_tier_side.csv) 与 [receipt](full_artifacts/receipt.json)。
