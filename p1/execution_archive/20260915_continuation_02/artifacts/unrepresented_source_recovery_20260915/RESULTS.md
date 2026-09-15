# 202 个未表示候选的 SCC 来源恢复结果

状态：`UNREPRESENTED_SOURCE_RECOVERY_FULL_COMPLETE`。在固定的 2,794 个 H/L 候选、固定日期区间 `[2019-01-01, 2026-09-01)` 内，只检查原先未在 v1 快照表示的 202 个 stock-wave 候选。未读取 actual/EPS/预测值、价格、回报或响应；受保护行级结果仅留在 SCC。

## 结果

两个严格分开的 archive family 给出相同候选级结果：99/202 在各自来源中获得唯一、日期有效的 CUSIP→PERMNO 映射；103/202 在这两个已检查 family 中没有唯一恢复。两者之间没有 core-only 或 rescue-only 候选，因此 rescue family 没有提供独立的增量覆盖证据。

| wave | tier | 原未表示候选 | 两个 family 均恢复 | 两个 family 均未唯一恢复 |
|---|---:|---:|---:|---:|
| W002 | high | 59 | 33 | 26 |
| W002 | low | 73 | 36 | 37 |
| W016 | high | 24 | 7 | 17 |
| W016 | low | 29 | 9 | 20 |
| W025 | high | 6 | 3 | 3 |
| W025 | low | 11 | 11 | 0 |
| **合计** |  | **202** | **99** | **103** |

每个 family 对这 99 个候选各观察到 1,246 个 wave-specific candidate release keys：PRE 833（覆盖 99 个候选）、POST 318（覆盖 27 个候选）、TRANSITION 95（覆盖 59 个候选）。这些是候选—wave—metadata release keys，不代表经独立核验的唯一经济事件，也不证明时钟、首发或最终 RTH 语义。

全 QTR archive 日期窗内，两 family 各有 160,612 个不同 metadata rows，行键交集也是 160,612，core-only/rescue-only 均为 0。该分母是完整 QTR archive 日期窗的行，不是 202 候选，不能解释成候选重叠。

## 边界与决定

- `NO_MATCH_IN_CHECKED_SCC_FAMILY` 仅表示在这两个已检查 SCC family/version 内无唯一恢复，不是全球供应商无 earnings，也不是 0。
- 未自动改变 population、tier、session、analyst 或样本批准状态；99 个恢复项仍是候选恢复证据。
- 两 family 保持分离；完全相同的聚合和 archive row-key 支持说明 rescue 不是新增独立证据源。

唯一下一步：对这 99 个已唯一恢复候选生成一个版本化、候选键保持不变的 metadata-projection proposal，并用现有冻结 session/analyst 规则重新计算其资格；103 个未恢复项继续保留 `UNKNOWN`。在明确批准该 projection 替代旧 v1 视图前，不纳入最终样本。

关键证据见 [candidate overlap](full_artifacts/candidate_source_overlap_aggregate.csv)、[wave/tier/family recovery](full_artifacts/recovery_by_wave_tier_family.csv)、[side support](full_artifacts/support_by_wave_tier_family_side.csv) 与 [full receipt](full_artifacts/receipt.json)。
