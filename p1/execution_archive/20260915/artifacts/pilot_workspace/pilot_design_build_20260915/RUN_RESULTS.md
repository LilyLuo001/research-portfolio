# P1 pilot 有限执行结果

日期：2026-09-15。结论：本轮 P0/P1 已完成，P2 接口已准备，P3 合成测试通过；研究 pilot 仍为 **HOLD_DESIGN + HOLD_DATA**。这不是 Gate 1 PASS、最终样本批准、真实功效或效应估计。已接受候选合同 SHA256 保持为 `00af7d39fd51e9c3c6a9051036f26a68b337f2132848368a729ff8a70d32663f`。

## 人口与支持

来源 H/L tail 为 2,794 个 stock-wave；v1 snapshot 仅表示其中 2,592，另 202 个在进入 8 PRE/4 POST 筛选前即未被表示，原因只能记为 retrieval/coverage `UNKNOWN`，不能写成“无盈余”。后续为 2,592 → 2,088（8 PRE/4 POST）→ 508（拟议 overlap-clean）→ 182（clean 且全 12 次均至少两位分析师）。71-unit acquisition union 是扩展工作 roster，不是下一层 attrition 或最终样本；它有 852 associations（568 PRE、284 POST），659 个仅满足事件级两位分析师 metadata 条件。

共同 H/L calendar-quarter 必要支持矩阵有 860 个 stock-cell，13 个缺口；更宽的 all-quarter 910/59 仅作诊断。event-stock 与 event-release-date 图有 3 个 component，最大 828；加入 wave edge 的代理图为 1 个 component。两者都不是 ESS 或合法推断 cluster 数，sponsor 仍为 `UNKNOWN`。

## 时钟与测量

71-unit snapshot 的来源显示时钟中，仅 18/852 落在名义 `[09:30,15:00]`，其中 5 个有 min-2 analyst metadata。v1 capped history 为 29,729 行，名义窗口 465 行、min-2 为 207；拟议 clean 子集名义窗口 101 行、min-2 为 38。所有 wave 的 clean HIGH 在 PRE 与 POST 两侧同时有至少一个名义窗口/min-2 事件的股票数均为 0。

这些只是未附时区的显示时钟。来源时钟尚未认证为首个公开时点、实际 RTH 或 RTH-60；历史 snapshot 又固定最多 8 PRE/4 POST，因此上述数字不是完整历史或更广总体的上限。P2 对 852 行的严格 session 状态全部保留 `UNKNOWN`；16 个合成测量接口 fixture 通过。

## 实现、SCC 与复核

P3 的 11 个合成 fixture 全部通过，包括已知 contrast 恢复、缺支持 fail-closed、重复事件不增加信息及跨 horizon covariance 保留；这不证明真实 rank、covariance、power 或 inference。

SCC 登录/连接检查成功，只对两个来源执行了 stat/header：`ibes_announcement_metadata.csv` 为 10,260,575 bytes，header 为 `ticker,cusip,pends,pdicity,anndats,anntims,actdats,acttims,source_partition`；`crsp_ibes_link_full.parquet` 为 606,920 bytes。未远程读取 raw body。独立复核最终接受本轮 metadata 计数与实现范围，并维持 HOLD_DESIGN + HOLD_DATA。

执行阶段：P0/P1 完成；P2 已准备但未运行真实测量；P3 合成测试通过；P4/P5 因输入与设计未就绪而未运行。请求路由为 Sol/medium、Terra/medium、Astra/high；实际 backend telemetry 均为 `NOT_OBSERVED`。本轮无购买、POST response、真实功效、真实 rank、效应估计或 Git 操作。

## 唯一下一步

先制作一个版本化的 uncapped metadata census manifest，固定原始候选 ID 与原先已记录的日期边界，并保留 202 个未表示单位为 `UNKNOWN`；随后仅在既有 metadata 权限与完全相同边界内派发一次 census。不得借此扩大 ID/window、改变 session 规则、查询 outcome、购买数据或现在直接运行 census。
