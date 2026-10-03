# 六表交付验收清单（有限审计，2026-10-03）

本清单只包装已有真实聚合。T2/T3 的 2,464 分片全量聚合与数值验收已完成；T5/T6 全量描述性计算与数值验收已完成；T4 仍 pending compatibility fix；P4 40 条文本已交付但真人标签未返回。以下 pilot 不得写成全库结果。

| 表 | 当前可验收内容 | 分母/范围 | 必须补齐后才能称正式表 |
|---|---|---|---|
| T1 `01_population_funnel` | 2,464 分片全波 raw/matched/country/usable 守恒、global JOB_HASH audit 与 USA reverse coverage 已验收；重复 hash=0 | raw 298,673,078 = matched 298,645,910 + unmatched 27,168；matched = USA 204,774,035 + non-USA 70,527,457 + unknown 23,344,418；usable 204,768,752，短差 5,283；USA reverse coverage 204,774,035 / 253,210,047 = 0.8087121242862847 | comparison eligibility and downstream P1/P2 outputs remain pending; reverse coverage is USA-only and before content usability |
| T2 `02_experience_profiles` | 2,464 分片全量 T2 聚合已落地；`T2_T3_NUMERIC_ACCEPTANCE.json` 数值验收通过；global JOB_HASH audit 通过；required/preferred、duration 分母和缺失语义保留 | canonical USA 204,774,035；unique usable ads 204,768,752；occupation_task=NA/unmeasured；general_work 是窄口径 explicit-object candidate measure | 语义/人工诊断；candidate non-detection 不得写成无要求，general_work 不得写成全部工作经验，predictive_ai 零值不得写成不存在 |
| T3 `03_technology_role_overlap` | 2,464 分片全量 T3 role/pair/cooccurrence 聚合已落地；数值验收通过；global JOB_HASH audit 通过；多标签与候选限制保留 | unique usable ads 204,768,752；role subsets 与 within-ad cooccurrence 已按两边边际核验；cross cells 非互斥；predictive_ai=NA/不可解释 | 绑定感知语义/人工诊断；cross 只能称广告内候选共现，不能相加为 technology prevalence 或直接绑定 |
| T4 `04_cohort_and_time_risk` | 当前 2,464 分片 CREATED 首次观察队列两种分母均守恒；global JOB_HASH audit 已通过；旧时间风险结果仍是历史昆山子集诊断 | canonical_usa 队列和 204,774,035；usable 队列和 204,768,752；历史 112,836,465 不得作当前全库分母 | compatibility fix、LAST_CHECKED/DELETE_DATE 风险、公司标题地点年度对照；CREATED 不是正文生效日 |
| T5 `05_comparable_experience_contrasts` | 全库固定 T5 已计算且数值验收通过（8 行）；Records 6,010,975/6,010,975 一对一；O*NET 6,008,133 命中、2,842 缺失；C1 保留率受限（B=22.198%），C2 因仅 2 个职业大类取消；85,376 行 pilot 与旧 15,254 linkage 仅作历史参考 | full candidate rows 6,010,975；primary eligible 4,962,792；C1/C2 support status 按冻结门槛 | 真人语义诊断；specific_tool 是受限词典且与 traditional-software arm 选择耦合；不得作因果、显著性或全部 AI/计算机技能门槛结论 |
| T6 `06_sensitivity_and_claim_status` | 全库固定 T6 已计算且数值验收通过（56 行）；S2/S3 与主规格相同的保留人数/估计数已明确不能算独立稳健性证据 | full fixed T6 output；描述性 raw/standardized differences 与 claim statuses | 真人语义诊断、T4 compatibility fix；不得作因果或显著性推断 |

## 共同放行条件

- [x] 每表写明 source file、数据单位、分子/分母、时间含义和是否 pilot。
- [x] Records 侧反向覆盖进入 T1；不能只按正文中成功匹配者计算总体覆盖。
- [x] T1 守恒核对：raw=matched+unmatched；matched=USA+non-USA+unknown；failure flags 允许重叠，不相加。
- [x] 任何 pilot（3 分片、32 分片、100,000 ads、15,254 linkage keys）均保留 pilot 标签，不外推全库。
- [x] 多标签允许进入多个单元格；不把行百分比相加为 100%。
- [x] “未检出”与“雇主没有要求”分开；候选检测与人工验证分开。
- [x] 时间表写明 snapshot/CREATED 首次观察含义；不能把年度新 hash 或跨季度区间写成正文改写率；旧 112,836,465 条时间风险结果不得写成当前全库 USA 比例。
- [x] CREATED 月份队列分别核对 canonical_usa=204,774,035 与 usable_nonempty_complete_parse=204,768,752，不能混用分母。
- [ ] T4 compatibility fix 与相应全量结果尚未完成；T5/T6 已通过守恒、join 不扩行、缺失与重复键检查，但仍受 D22 解释边界约束。
- [x] 对外解释必须随附 `results/MEASUREMENT_STATUS.csv` 与 `PREDICTIVE_AI_MEASUREMENT_LIMITATION.md`：predictive_ai 零值标 NA/不可解释，occupation_task 标 unmeasured/NA，general_work 标窄口径 candidate measure。
- [x] T2/T3 全量聚合的数值通过不等于语义验证通过；global JOB_HASH audit 已报告 204,774,035 distinct USA matched JOB_HASH、duplicates=0；T2/T3 unique usable ads 为 204,768,752。
- [x] P4 phase 2 已交付 40 条文本（32 core、8 challenge、8 dual review）；真人 labels 未返回，不标记为人工语义验收通过，heldout exclusion 仍未验证。
