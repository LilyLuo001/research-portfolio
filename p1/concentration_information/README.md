# P1：集中度与信息传播（独立工作目录）

此目录是新方向后续工作的主入口，与旧 MF→ETF conversion 档案分开。

## 最新状态（2026-09-21）

- **最新执行：[XOM × SPY 单事件 Stage-A 包](20260921_spy_xom_event_packet/DECISION.md)**：最终 SCC 脚本与输出已绑定，并由独立 Sol/high 代理用第二套 metadata-only 程序复算。裁定为 `HOLD_NAMED_INPUT`：现有 CRSP 仅给出 2022-12-31（`eff_dt=2023-01-09`）和 2023-01-31（`eff_dt=2023-02-07`）月度快照，不能证明 2023-01-31 06:30 ET 的实际 SPY 持仓或申赎篮子。XOM 精确 CUSIP/季度期间可定位，但 PIT 共识单位仍未准入。没有读取预测、EPS 或报价数值，没有购数或 Stage-B release。唯一下一输入是 State Street 当日历史 holdings/portfolio-composition/cash 文件及可用时间证据；滞后持仓代理只能作为待批准的规格修订。
- **最新执行：[系统性 pilot 支持阶段](20260921_systematic_pilot/README.md)**：已取得绑定正确 32 事件名单的 SCC 持仓汇总、六公告时钟证据、独立数值修复检验和 29 个已有报价文件的实际端点诊断。[科学决定](20260921_systematic_pilot/DECISION.md)仍为 HOLD_DATA + HOLD_MEASUREMENT，不是假设通过或失败、功效通过或研究 GO。旧名单误绑定汇总已作废，接手者以新目录机器生成 receipt 为准。
- **最新续作：[六公告来源定位与组间比值区间](20260921_ratio_continuation/README.md)**：SCC 连接正常但既有记录未给出所需历史源位置；新增联合区域保守投影的提案代码，不等于真实数据推断或研究 GO。此目录保存实际执行与独立审查记录。
- **本轮执行：[新闻—ETF—真实篮子 readiness](20260921_news_basket_readiness/README.md)**。已运行元数据回执再计数和合成方法实现；不是新经验结果。最终状态与下一行动见[决定](20260921_news_basket_readiness/DECISION.md)，独立复核见该目录报告。
- **先读：[新方向始末与接手说明](20260921_price_discovery_method/RESEARCH_HANDOFF.md)**。当前为 `HOLD_CONTRIBUTION_AND_EMPIRICAL_VALIDATION`，不是实证通过。
- [本轮所执行的 prompt（含模型/effort 分工）](20260921_price_discovery_method/NEXT_EXECUTION_PROMPT.md)：原始文件保留提交时状态；用户随后已批准执行，实际委派、产物及边界记录在 readiness 目录。不自动打开响应值。
- [文献贡献定位](20260921_price_discovery_literature/CONTRIBUTION_ASSESSMENT.md)与[方法原型/测试](20260921_price_discovery_method/README.md)：保留导师的价格发现问题，但宽泛 ETF/个股领先、权重效应与信息分解不是新贡献。原型及合成测试不能证明实际样本可行。
- [已完成的 H2 冻结检验](20260921_same_industry_replication/DECISION.md)：`INCONCLUSIVE_STOP_SPENDING`，停止共同持仓/两日反应路线的自动扩样与购买。
- [信息质量方向的定位执行与 SCC 字段核查](20260921_information_quality_repositioning/DECISION.md)：`HOLD_CONTRIBUTION_AND_MEASUREMENT`。通用 bellwether/ETF 信息外溢不是新贡献；新的独有信息质量命题尚未冻结或运行。只核查了文献、文件与 footer，没有新财务值/收益访问。
- [未完成：I/B/E/S 历史时点与值口径裁定](20260921_ibes_pit_semantics/未完成.md)：2026-09-21 按用户要求暂停，保留全部已有工作，未完成独立复核。下一步先讨论 ETF 与个股谁完成价格发现的研究定位，不自动执行新分析。旧计划与报告保留为历史，不能把它们的执行授权当作新定位已经通过。

## 历史入口

- [研究计划](20260920/RESEARCH_PLAN.md)
- [第一阶段实际结果](20260920/execution/RESULTS.md)
- [第一阶段执行记录](20260920/execution/EXECUTION_RECEIPT.json)
- [第二阶段进展](20260920_phase2/PROGRESS.md)
- `ARCHIVE_MANIFEST.json`：迁入文件的来源、大小、校验值及迁入一致性。

`20260920/` 保存原 `p1/concentration_information_plan/20260920/` 的完整研究文件副本，逐文件一致性记录在清单中。按用户要求，GitHub 是此目录的交接入口；远端确认成功后可以清理本地重复旧副本，不改写其 receipts。新代码、修复与报告从本目录继续。历史文件中的 SCC 路径仍然有效，不能因本地目录调整重新生成或替换原始数据。

许可行级研究数据继续只留 SCC：

`/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/derived/p1_concentration_information/20260920/`

后续阶段使用独立 SCC 子目录，不覆盖第一阶段结果。这里保存代码、配置、聚合结果、公开来源及执行记录，不保存密钥、许可逐行数据或原始报价。

当前没有效果、经验功效或因果 GO 结论。本次用户明确要求保存到 GitHub：只提交本方向文件到既有 `task/p1-feasibility-adjudication-20260913` 分支，不合并 main，不提交其他项目的未跟踪文件。
