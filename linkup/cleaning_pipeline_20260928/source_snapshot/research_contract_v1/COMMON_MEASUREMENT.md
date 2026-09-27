# 计算机化—AI—劳动者经历：共同测量合同 v1

2026-09-27；研究设计版本，不是已完成的变量或因果识别。

## 研究对象与第一组产物

问题：在可比较的岗位、任务与技术角色中，不同技术扩散是否改变雇主所写明的经验对象、要求强度和资格替代方式；实际进入者的事前经历是否出现对应调整？方向不预设。

第一组研究产物不是单一“最低经验年数”。它由技术类别×技术角色、经验对象×明确年限、要求强度和资格关系组成。每一维单独记录证据和未知；没有写明不等于没有要求。多项标签允许共存。

| 维度 | LinkUp 标签与证据单位 | Revelio 对应目标（未上传，尚未实现） | 禁止替代 |
|---|---|---|---|
| 一般经验 | 明确总工作经历及其年限；无对象年限记 object_unspecified | 事件前已观察工作区间的并集时长、覆盖完整性 | 年龄、seniority 不等于实际累计经验；无对象不能默认一般经验 |
| 职业／任务经验 | 从事具体职业或执行任务的既有经验，保留原词与证据范围 | 同一统一职业及相关任务的事前任职区间 | 仅职责描述不能算既有经历要求 |
| 行业／领域经验 | 行业、客户类型、产品或制度领域的明确经验要求 | 同行业经历；业务领域需有带日期的岗位文本 | 同雇主不等于同行业经验；行业不等于全部业务领域 |
| 工具经验 | 明确使用／开发／实施某工具的既有经验及年限绑定 | 带时间的既往岗位中有工具证据的区间 | 当前个人技能清单不得回填早年经历 |
| 资格替代 | 明确学历、经历、工具等之间的 OR／等效／可培训条款 | 实际进入者的教育与经历组合 | 观察到的组合不是录用概率，也不是广告一对一录用 |

## 技术、角色与工作内容

技术类别：`software_information_system`、`predictive_ml_ai`、`generative_ai`、`ai_unspecified`、`technology_unspecified`。Python、SQL 等记录为工具，不能因它们出现就归为 AI；同一工具可在不同应用中使用。AI 一词没有足够语境时不能硬分传统／生成式。公司宣传或招聘流程中的 AI 与岗位资格／职责分开。

技术角色：`develop_train`、`implement_integrate`、`use_operate`、`evaluate_govern`、`role_unspecified`。只在原文对该技术存在明确动作关系时赋值。会使用模型不等于开发模型；同一广告可以同时要求开发和使用。不得根据职业码自动填充角色。

共同任务维度：`execution_information_processing`、`analysis_judgment`、`verification_accountability`、`coordination_communication`、`task_other_or_unknown`。它们是对原文工作内容的描述，不是“可被 AI 替代”的预设标签；沟通也不自动等于管理经验。

核心关系表以 `experience_clause_id → object_span_id` 和 `technology_span_id → role_span_id` 存边。只有同一明确语法／列举范围内可解释的绑定才标 `explicit`；同段共现为 `cooccurrence_only`，不能升级为直接绑定。`object_unspecified`、`binding_unresolved` 均保留。

## 具体编码例（均为合成例，不来自供应商正文）

- “3 years of accounting experience using SAP”：3 年绑定 accounting；SAP 有使用关系，但 SAP 的经验年数未明确，不赋 3 年。
- “3 years of SAP experience in healthcare”：3 年绑定 SAP；healthcare 是领域语境，是否明确要求领域经验另判。
- “5 years overall, including 2 years in risk modelling”：保留总经验与包含关系，不相加成 7 年。
- “Bachelor's + 5 years OR Master's + 3 years”：保留两条路径；不能合成本科 + 3 年。
- “SQL and Python required; deploy prediction models”：软件工具与预测模型分别记录；不能用软件名推断其 AI 类别。
- “Use an LLM to draft reports and independently verify outputs”：生成式 AI 使用与验证两项角色并存；不推断经验溢价方向。
- “We are an AI company; no prior experience required”：公司语境的 AI 不能算申请者 AI 技能；明确无需经验与未提及分开。

## 比较设计的边界

LinkUp 2016 年以后的正文比较不能覆盖最初计算机革命。共同覆盖期内可以比较成熟软件与 AI 的角色、任务和经验结构；若做两轮历史比较，早期计算机化需另接 CPS／历史任务和计算机使用证据。年份不是技术类型，也不是技术采用时间。

同一技术的开发、实施、使用阶段须分开；扩散阶段要用事先定义、可观察的指标，不能用本文待解释的经验下降反推“技术成熟”。成熟软件使用与早期 AI 开发的简单差异不是技术本质效应。

先报告企业—统一岗位族—地区—季度的招聘要求分布及覆盖。共同企业映射必须区分 company-scrape、子公司与母公司，匹配置信度、版本和生效期单列；不强行用名称相似实现一对一。稀疏单元可预先聚合，但不能根据显著性调整粒度。

## Revelio 事件接口

以外部新入职、同雇主职业转岗、同职业换雇主分开建事件。事件时间为 t：只累计 t 之前可观察到的经历；月精度日期保留区间不确定性。同一维度的重叠任职按区间并集计时，不把两个同时工作月算成两个月；兼职强度另标，不能在未知小时数时推算全职等价。

实习、创业、教育、未知岗位类型分别保留。首次观察到工作不是首次进入劳动市场。左侧履历缺失、日期缺失、近期更新滞后均独立标志；无法判断不是零年经验。教育完成时间晚于 t 的学历不用于当时资格。

若无申请数据，新入职者构成是实际进入者分布。职业转入率需另定事前风险集；现阶段不得将构成份额命名为录用概率。收入只在实际观测薪酬及其口径可核实时研究，不用模型预测薪资声称工资溢价。

## 文献约束（不是本项目已验证机制）

计算机化研究以任务调整解释技能需求，而非仅用软件词频：[Autor、Levy、Murnane (2003)](https://economics.mit.edu/sites/default/files/publications/the%20skill%20content%202003.pdf)。技能变动与经验回报的关系支持区分一般资历和特定技能经历：[Deming、Noray](https://www.nber.org/papers/w25065)。新技术招聘的技能构成随扩散变化，提醒比较时控制角色与阶段：[Kalyani 等](https://www.nber.org/papers/w28999)。这些文献说明测量维度有经济含义，不自动证明本项目存在相反机制或可识别因果效应。
