# 六表交付验收清单（有限审计，2026-10-03）

本清单只包装已有真实聚合。T1–T6 的实际计算产物均已交付并通过相应数值/工程验收。用户依 D23 以 AI 辅助复核替代本轮人工标签门槛；AI 诊断已经完成，但不等于人工验证或真值测试。T2/T3/T5/T6 仍是候选测量，T4 年度案例仍是固定 prefix 0 的有界诊断；以下 pilot 不得写成全库结果。

| 表 | 当前可验收内容 | 分母/范围 | 必须补齐后才能称正式表 |
|---|---|---|---|
| T1 `01_population_funnel` | 2,464 分片全波 raw/matched/country/usable 守恒、global JOB_HASH audit 与 USA reverse coverage 已验收；重复 hash=0；工程交付完成 | raw 298,673,078 = matched 298,645,910 + unmatched 27,168；matched = USA 204,774,035 + non-USA 70,527,457 + unknown 23,344,418；usable 204,768,752，短差 5,283；USA reverse coverage 204,774,035 / 253,210,047 = 0.8087121242862847 | 无剩余计算门槛；reverse coverage 仅限 USA 且先于正文可用性筛选，不验证语义标签 |
| T2 `02_experience_profiles` | 2,464 分片全量 T2 聚合、数值验收和有限 AI 诊断均已完成；global JOB_HASH audit 通过；required/preferred、duration 分母和缺失语义保留 | canonical USA 204,774,035；unique usable ads 204,768,752；occupation_task=NA/unmeasured；general_work 是窄口径 explicit-object candidate measure | 候选测量边界继续有效；AI-only 诊断不是人工真值，candidate non-detection 不得写成无要求，predictive_ai 零值不得写成不存在 |
| T3 `03_technology_role_overlap` | 2,464 分片全量 T3 role/pair/cooccurrence 聚合、数值验收和有限 AI 诊断均已完成；多标签与候选限制保留 | unique usable ads 204,768,752；role subsets 与 within-ad cooccurrence 已按两边边际核验；cross cells 非互斥；predictive_ai=NA/不可解释 | 候选测量边界继续有效；AI-only 诊断不认证绑定准确率，cross 不能相加为 prevalence 或直接绑定 |
| T4 `04_cohort_and_time_risk` | 六个实际 CSV、公开回执及独立数值验收均完成；全库时间风险与固定 prefix 0 年度案例均已交付 | USA matched 204,774,035；有效 CREATED–LAST_CHECKED 区间 204,773,879，缺失/异常 156；跨季度 76,769,916，跨年 27,324,502；年度案例 12 组、200 keys、2014–2025 | 无剩余计算门槛；年度案例不是全体公司×标题×地点组的概率样本，观察日期不是正文生效日期，新 JOB_HASH 不是历史正文版本 |
| T5 `05_comparable_experience_contrasts` | 全库固定 T5、数值验收和有限 AI 诊断均已完成（8 行）；Records 6,010,975/6,010,975 一对一；O*NET 6,008,133 命中、2,842 缺失；C1 受限，C2 取消 | full candidate rows 6,010,975；primary eligible 4,962,792；C1/C2 support status 按冻结门槛 | 候选测量边界继续有效；specific_tool 与分组选择耦合；不得作因果、显著性或全部 AI/计算机技能门槛结论 |
| T6 `06_sensitivity_and_claim_status` | 全库固定 T6、数值验收和有限 AI 诊断均已完成（56 行）；S2/S3 与主规格相同，不能算独立稳健性证据 | full fixed T6 output；描述性 raw/standardized differences 与 claim statuses | 候选解释边界继续有效；不得作因果或显著性推断 |

## 共同放行条件

- [x] 每表写明 source file、数据单位、分子/分母、时间含义和是否 pilot。
- [x] Records 侧反向覆盖进入 T1；不能只按正文中成功匹配者计算总体覆盖。
- [x] T1 守恒核对：raw=matched+unmatched；matched=USA+non-USA+unknown；failure flags 允许重叠，不相加。
- [x] 任何 pilot（3 分片、32 分片、100,000 ads、15,254 linkage keys）均保留 pilot 标签，不外推全库。
- [x] 多标签允许进入多个单元格；不把行百分比相加为 100%。
- [x] “未检出”与“雇主没有要求”分开；候选检测与人工验证分开。
- [x] 时间表写明 snapshot/CREATED 首次观察含义；不能把年度新 hash 或跨季度区间写成正文改写率；旧 112,836,465 条时间风险结果不得写成当前全库 USA 比例。
- [x] CREATED 月份队列分别核对 canonical_usa=204,774,035 与 usable_nonempty_complete_parse=204,768,752，不能混用分母。
- [x] T4 六个实际输出、公开回执和独立数值验收均已通过；receipt SHA-256 为 `ffadf261fff03da923425d856478e7077fdb568ea2f9ab3253c6c8c49d38594d`，numeric acceptance SHA-256 为 `70ad44c54f79fa904bacc224dbcd1a47a1077a64961a2ad584459b567bae9569`。年度 12 组/200 keys 只作 prefix 0 有界诊断。
- [x] 对外解释必须随附 `results/MEASUREMENT_STATUS.csv` 与 `PREDICTIVE_AI_MEASUREMENT_LIMITATION.md`：predictive_ai 零值标 NA/不可解释，occupation_task 标 unmeasured/NA，general_work 标窄口径 candidate measure。
- [x] T2/T3 全量聚合的数值通过不等于语义验证通过；global JOB_HASH audit 已报告 204,774,035 distinct USA matched JOB_HASH、duplicates=0；T2/T3 unique usable ads 为 204,768,752。
- [x] D23 AI-only 复核已完成：40 条文本、48 次阅读、8 条双审及 GPT-6 裁决；回执 SHA-256 为 `db18f59eb247049f92b8bdfe24b9c3aeb3dd738b91eb07cbb8dbd7eb271f7411`。用户已取消本轮人工门槛；不标记为人工语义验收或真值测试，same-family correlation、分层抽样与 heldout exclusion 未验证限制继续保留。
