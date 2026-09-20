# 第二阶段执行进展

本阶段继续时钟与持仓单位验证，不读取事件响应，不购买报价。

## 历史交易日历：实际执行

将 32 个候选发布组与 [ICE/NYSE 在 2022-12-21 发布的 2023 休市和提前收市安排](https://ir.theice.com/press/news-details/2022/NYSE-Group-Announces-2023-2024-and-2025-Holiday-and-Early-Closings-Calendar/default.aspx) 对齐，冬夏采用 America/New_York。

实际分类为：12 PRE_OPEN、16 AFTER_CLOSE、4 WEEKEND_CLOSED。原来的 16 个粗分类盘前事件中，4 个被更正为周末。

周末事件保留在总体中，但不自动改为下周一开盘事件，也不为不存在的同刻股票交易购买窗口。日历分类并不认证最早公开发布时间；该项仍 UNKNOWN。

结果与脚本：`clock/CALENDAR_SUMMARY.json`、`clock/calendar_2023.json`、`clock/classify_calendar.py`。许可逐行分类留 SCC。周末、假日、半日市、开盘边界以及冬夏 UTC 偏移小测试通过。

## 公开发行人时钟：已执行一个有边界的检索

访问 Apple 官网 2023 四次季度业绩公告页面，仅提取 publication/modified 元数据，不解析或返回财务数值。四页访问成功，但公开 `datePublished` 只有日期，没有可比较的钟点；`dateModified` 是后续网页更新时间，不能替代发布时间。

因此本次获得的是日期来源证据，不是四个精确时钟 PASS，也不把 0 个可比时间戳误报为 0 个匹配事件。保存 `clock/PUBLIC_CLOCK_PROBE.json` 和脚本，避免后续重复同一无效检索。

## 加权持仓：定向验证，尚未通过

`weighted_network/` 保存 source-specific 脚本和实际诊断。最初 b0001 小分区是有限边界检查，不代表目标股票持仓总体；多股类 TNA 各不相同本来就可能合理，不能据此判定源数据错误。

定向检查现已完成：选取 3 个实际持有目标股票的 ETF_ONLY_RECORDED_CLASSES 组合/报告日，得到 991 行持仓，其中 777 行 market_val 与 percent_tna 同为正。三个组合都没有匹配到同 caldt 的正 TNA，因此可比较分母行数为 0。这只是有限样本的同报告日覆盖缺口，不是全库无 TNA 的结论。635 个接收股票成员与 19 个头部股票成员是各组合内去重后求和，并非跨组合唯一证券数。

进入美元加权 L 前需要已知单位、正确报告日期、目标 pooled portfolio 分母及历史 ETF 类别/分配。`percent_tna` 本身是报告权重，不能把缺少美元分母误说成连数值权重也不存在。实际结果见 `weighted_network/RELEVANT_UNIT_CONTRACT_REPORT.md`；未计算 dollar exposure。

## 保存与执行边界

新方向独立 GitHub 目录为 `p1/concentration_information/`。21 个前期研究文件已经逐文件比较一致后归入 `20260920/`；后续阶段单独记录，不覆盖历史。

本轮没有 Databento API 调用/支出，没有连接 WRDS，没有打开旧 conversion 封存响应。原始和许可行级数据仍只在 SCC；本地和 GitHub 只保存小型代码、公开元数据、聚合结果与执行记录。

接下来核实有实际钟点的发行来源，并完成与目标股票相关的持仓分母验证，再确定接收股票与采购差集。未报告效果、经验功效或研究 GO。
