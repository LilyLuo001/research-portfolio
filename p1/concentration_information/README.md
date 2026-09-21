# P1：集中度与信息传播（独立工作目录）

此目录是新方向后续工作的主入口，与旧 MF→ETF conversion 档案分开。

## 最新状态（2026-09-21）

- [已完成的 H2 冻结检验](20260921_same_industry_replication/DECISION.md)：`INCONCLUSIVE_STOP_SPENDING`，停止共同持仓/两日反应路线的自动扩样与购买。
- [信息质量方向的定位执行与 SCC 字段核查](20260921_information_quality_repositioning/DECISION.md)：`HOLD_CONTRIBUTION_AND_MEASUREMENT`。通用 bellwether/ETF 信息外溢不是新贡献；新的独有信息质量命题尚未冻结或运行。只核查了文献、文件与 footer，没有新财务值/收益访问。
- 后续唯一具体工作是现有 I/B/E/S 历史时点与值口径裁定，不是启动另一轮全量回归或报价采购。旧计划与报告保留为历史，不能把它们的执行授权当作新定位已经通过。

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
