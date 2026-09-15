# Step 4 readiness diagnostic

状态：`HOLD_DATA_AND_SCIENTIFIC_CHOICE_ACTUAL_RANK_NOT_RUN`。先前把“两只股票/每 tier”当必要识别门槛的草稿已明确作废；该阈值只能作为未批准的稳健性启发式。

| Main wave | Nominal PRE+POST, all statuses H/L | Cached-min2 H/L | Proposed-clean nominal H/L | Legacy clean+all12 H/L | Nonempty H/L diagnostic |
|---|---:|---:|---:|---:|---|
| W002 | 18 / 23 | 3 / 5 | 1 / 14 | 10 / 165 | yes / yes / yes |
| W013 | 1 / 2 | 1 / 0 | 0 / 0 | 0 / 0 | yes / no / no |
| W021 | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | yes / no / no |
| W025 | 7 / 2 | 4 / 1 | 0 / 0 | 2 / 2 | yes / yes / no |

单位是 stock-wave candidate keys。Nominal 是 `[09:30,15:00]` source-display clock，未认证为 ET/RTH；cached-min2 是旧 exact-key metadata 下界；proposed-clean 使用未签署的 competing rule；legacy clean+all12 不是 session support。它们互不替代，也都不是最终 population × common-calendar support。

最宽松的 all-status/no-min2 诊断在四个 main waves 都有非空 H/L；因此现有证据不能据“两只股票”启发式宣告原比较必然失败。施加 cached min2 后只有 W002、W025 保持双 tier 非空；施加 proposed-clean/no-min2 后仅 W002 保持双 tier 非空。这说明结果强烈依赖尚未批准的 analyst-completeness 与 competing-event 规则。实际 stock-by-wave baseline-SUE columns、冻结 PRE-stock × observed common-calendar cells和数值 rank 均为 `NOT_RUN`，不能声称已识别或不可识别。

17-wave gap 已分解为 14 个当前 U.S.-common-stock scope absence 与 3 个 identifier-link UNKNOWN；不能把 14 当作新时钟合同下的零，也不能把 recovered99 的 75 个 no-match 当 clean。W006 的 12 个日期桶配对现已归因为 11 个 DFA-only、1 个同时 DFA/JPM，但这仍是 predecessor-holdings membership，不是批准的 shared package、sponsor 或 competing exclusion。W002-high 的独立 adjusted-detail 来源仍是 PRE 0/3、POST 0/1 observed-min2，下界未改善且 `<2` 继续保持 UNKNOWN。

下一项真正改变裁决的科学选择是冻结 package 单元和 concurrent-event/exclusion 规则；随后可在现有 SCC 权限内按 predecessor-series lineage 重建 fund/package sidecar。来源侧还需 timestamp semantics/uncertainty interval，再接已认证 XNYS calendar。无需 exact second 或全球“无更早新闻”证明：记录 earliest independently verified source、检索范围、已知更早信号与保守界即可，边界跨越者保持 UNKNOWN。

报价 body、PRE 校准、真实 rank 与 power 继续 NOT_RUN，因为其人口、时钟和规则输入尚未冻结；这不是基于虚构的两股票门槛作出的 early stop。该包适合进入一次针对实际结果与上述门槛修正的 Astra/high 科学复核。
