# 六表交付验收清单（有限审计，2026-10-03）

本清单只包装已有真实聚合。T2/T3 的 2,464 分片全量聚合与数值验收已完成；T4/T5/T6 全量产物仍 pending。以下 pilot 不得写成全库结果。

| 表 | 当前可验收内容 | 分母/范围 | 必须补齐后才能称正式表 |
|---|---|---|---|
| T1 `01_population_funnel` | 2,464 分片全波 raw/matched/country/usable 守恒、global JOB_HASH audit 与 USA reverse coverage 已验收；重复 hash=0 | raw 298,673,078 = matched 298,645,910 + unmatched 27,168；matched = USA 204,774,035 + non-USA 70,527,457 + unknown 23,344,418；usable 204,768,752，短差 5,283；USA reverse coverage 204,774,035 / 253,210,047 = 0.8087121242862847 | comparison eligibility and downstream P1/P2 outputs remain pending; reverse coverage is USA-only and before content usability |
| T2 `02_experience_profiles` | 2,464 分片全量 T2 聚合已落地；`T2_T3_NUMERIC_ACCEPTANCE.json` 数值验收通过；global JOB_HASH audit 通过；required/preferred、duration 分母和缺失语义保留 | canonical USA 204,774,035；unique usable ads 204,768,752；occupation_task=NA/unmeasured；general_work 是窄口径 explicit-object candidate measure | 语义/人工诊断；candidate non-detection 不得写成无要求，general_work 不得写成全部工作经验，predictive_ai 零值不得写成不存在 |
| T3 `03_technology_role_overlap` | 2,464 分片全量 T3 role/pair/cooccurrence 聚合已落地；数值验收通过；global JOB_HASH audit 通过；多标签与候选限制保留 | unique usable ads 204,768,752；role subsets 与 within-ad cooccurrence 已按两边边际核验；cross cells 非互斥；predictive_ai=NA/不可解释 | 绑定感知语义/人工诊断；cross 只能称广告内候选共现，不能相加为 technology prevalence 或直接绑定 |
| T4 `04_cohort_and_time_risk` | 当前 2,464 分片 CREATED 首次观察队列两种分母均守恒；global JOB_HASH audit 已通过；旧时间风险结果仍是历史昆山子集诊断 | canonical_usa 队列和 204,774,035；usable 队列和 204,768,752；历史 112,836,465 不得作当前全库分母 | LAST_CHECKED/DELETE_DATE 风险、公司标题地点年度对照；CREATED 不是正文生效日 |
| T5 `05_comparable_experience_contrasts` | 已验证 85,376 行 comparison pilot；其中候选 2,394 行 Records 1:1，O*NET official 2,393、missing 1；旧 15,254 linkage pilot 仅作历史参考 | 85,376-row pilot；不代表全库覆盖或正式比较支持 | 全库 Records/O*NET join、C1/C2 支持规则、原始与固定权重差异；T5 全量仍 pending |
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
- [ ] P1/P2 产物到位并通过守恒、join 不扩行、缺失与重复键检查后，才把相应表从 limited/pilot/blocked 改为正式状态；当前 T4/T5/T6 全量仍 pending。
- [ ] 对外解释必须随附 `results/MEASUREMENT_STATUS.csv` 与 `PREDICTIVE_AI_MEASUREMENT_LIMITATION.md`：predictive_ai 零值标 NA/不可解释，occupation_task 标 unmeasured/NA，general_work 标窄口径 candidate measure。
- [ ] T2/T3 全量聚合的数值通过不等于语义验证通过；global JOB_HASH audit 已报告 204,774,035 distinct USA matched JOB_HASH、duplicates=0；T2/T3 unique usable ads 为 204,768,752。
