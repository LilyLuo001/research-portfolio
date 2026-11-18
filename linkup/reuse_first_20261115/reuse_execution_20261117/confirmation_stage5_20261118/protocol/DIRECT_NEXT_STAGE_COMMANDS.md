# 当前执行顺序：Azure 直连 Kimi v4

2026-11-18。此操作页取代 `NEXT_STAGE_COMMANDS.md` 中的 OpenCode/v2 启动和导入步骤；历史文件保留，不再照旧页启动 OpenCode。

## 已发生，不再重复

- Luna 的 135 个槽位已终态记账；134 个完成字段局部机械校验，1 个无效输出保留。这不是 134 条语义验收。
- 固定窗口 150 个候选中 15 个既有上下文被排除，实际 135 个新输入；不补样，不再 freeze。
- v2 的 10 次真实响应和 v3 的 1 次真实响应均被 v4 导入并永久跳过；所有旧账本、原始短模型名、请求 SHA、输出和成本保留。
- v4 通过现有 VM 托管身份直接调用原 Azure Kimi 部署；ARM 配置及响应头均核实 3,000,000 TPM。没有使用 OpenCode。
- v4 已启动；不得再次执行 prepare/launch。当前确认的冻结调度保持不变，较高配额不构成扩大样本或预算的许可。

## 剩余命令

本机控制入口为
`[private-runtime-path]`。

1. `status_direct_kimi_v4`：读取实际进程及账本。保留现有终端会话，不重复提交同一 RunCommand。
2. 仅当 Kimi 终态且所有 135 槽位已记账，执行 `score_direct_kimi`。该动作在云端机械验证、连接并调用原冻结评分器；不修改评分定义。
3. `download_scoring`：下载 SHA 验证后的无逐条身份公开汇总。
4. 若汇总中确定性 Astra 待诊断数为 1–6，使用 `prepare_astra`、`launch_astra`、`status_astra`。这些控制必须通过工程测试后才执行；最多 6 次物理请求、$8，完整固定输入、原 schema/instructions，不展示 Luna/Kimi 答案。
5. Astra 终态后执行 `diagnose_astra`、`download_astra`。诊断单独保存，不替换 Kimi reference、不重算 primary gate。
6. 仅根据实际独立合格研究量及其依赖决定试产资格；新队列、独占领取、排除清单和预算均须重新核对。最多 10,000 个真正未处理输入/$150，前 100 个包含在总数中。不自动扩大到全库。

## 云端结果位置

- Kimi：`[private-runtime-path]`
- 原冻结评分：`[private-runtime-path]`
- Astra 有界诊断：`[private-runtime-path]`

原文、逐条身份和模型内容留在私有位置；Git 只纳入经明确 allowlist 和扫描器检查的代码、公开汇总与回执。

## 解释边界

机器间一致性不是人工金标准准确率或全库准确率。未知、无输出、机械无效、隔离与证据不足分开保留。固定游标窗口不是概率样本。B+D 核心、A+C 支撑、E 扩展的研究议程不缩减；本次确认不声称完成约五亿条数据。
