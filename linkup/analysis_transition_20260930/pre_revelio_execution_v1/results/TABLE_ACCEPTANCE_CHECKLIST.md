# 六表交付验收清单（有限审计，2026-10-03）

本清单只包装已有真实聚合。P1 全波已完成；P2 比较产物仍 pending；以下 pilot 不得写成全库结果。

| 表 | 当前可验收内容 | 分母/范围 | 必须补齐后才能称正式表 |
|---|---|---|---|
| T1 `01_population_funnel` | 2,464 分片全波 raw/matched/country/usable 守恒已验收；全局 JOB_HASH distinct 仍 pending | raw 298,673,078 = matched 298,645,910 + unmatched 27,168；matched = USA 204,774,035 + non-USA 70,527,457 + unknown 23,344,418；usable 204,768,752，短差 5,283 | combined key-only global JOB_HASH audit；在此之前不得把 204,774,035 写成全球 distinct JOB_HASH |
| T2 `02_experience_profiles` | 经验候选、教育/无经验审计字段、守恒与缺失语义可参考 | V6 固定 Kunshan pilot 100,000；主完整队列 96,141 | 全库经验聚合、required/preferred、明确年限分母；candidate non-detection 不得写成无要求 |
| T3 `03_technology_role_overlap` | 2,464 分片全波候选 diagnostic 已落地；多标签与候选限制保留 | canonical USA 204,774,035；technology evidence 82,379,739；experience evidence 421,992,351；cross cells 非互斥 | 绑定感知语义验证；cross 只能称广告内候选共现，不能相加为 technology prevalence 或直接绑定 |
| T4 `04_cohort_and_time_risk` | 当前 2,464 分片 CREATED 首次观察队列两种分母均守恒；旧时间风险结果仍是历史昆山子集诊断 | canonical_usa 队列和 204,774,035；usable 队列和 204,768,752；历史 112,836,465 不得作当前全库分母 | LAST_CHECKED/DELETE_DATE 风险、公司标题地点年度对照、global JOB_HASH audit；CREATED 不是正文生效日 |
| T5 `05_comparable_experience_contrasts` | 仅能复用 15,254 条 linkage pilot 的无扩行诊断 | 15,254 fixed-prefix pilot；O*NET official 15,248、placeholder 3、missing 3 | 全库 Records/O*NET join、C1/C2 支持规则、原始与固定权重差异；当前 blocked |
| T6 `06_sensitivity_and_claim_status` | 可复用 S1/S2/S3 预设口径、pilot/time-risk 限制与 claims 边界 | pilot 与 full time-risk 范围分开记录 | 实际敏感性行、逐比较状态、P2 结果；不得用工程通过替代语义验证 |

## 共同放行条件

- [ ] 每表写明 source file、数据单位、分子/分母、时间含义和是否 pilot。
- [ ] Records 侧反向覆盖进入 T1；不能只按正文中成功匹配者计算总体覆盖。
- [ ] T1 守恒核对：raw=matched+unmatched；matched=USA+non-USA+unknown；failure flags 允许重叠，不相加。
- [ ] 任何 pilot（3 分片、32 分片、100,000 ads、15,254 linkage keys）均保留 pilot 标签，不外推全库。
- [ ] 多标签允许进入多个单元格；不把行百分比相加为 100%。
- [ ] “未检出”与“雇主没有要求”分开；候选检测与人工验证分开。
- [ ] 时间表写明 snapshot/CREATED 首次观察含义；不能把年度新 hash 或跨季度区间写成正文改写率；旧 112,836,465 条时间风险结果不得写成当前全库 USA 比例。
- [ ] CREATED 月份队列分别核对 canonical_usa=204,774,035 与 usable_nonempty_complete_parse=204,768,752，不能混用分母。
- [ ] P1/P2 产物到位并通过守恒、join 不扩行、缺失与重复键检查后，才把相应表从 limited/pilot/blocked 改为正式状态。
