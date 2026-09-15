# P1 pilot：下一批工作从这里开始

本目录是2026-09-15用户要求的完整pilot方案，不是又一次Gate1检查。Gate1暂停，未改成PASS。观察到的POST响应继续封存。

主文件：[完整研究与执行方案](PILOT_RESEARCH_PLAN.md)。配套：[真实数据缺口](DATA_GAP_MATRIX.md)、[独立方案复核](PLAN_REVIEW.md)、[执行记录](PLAN_RECEIPT.json)。

## 核心研究决策

先判断原定高/低暴露比较还有哪些wave、股票和实际可估支持，再测量现有报价、用PRE数据校准精度。能够算power不代表因果识别成立；报价下载成功也不代表研究样本成立。

现有71股票/852 associations足够开始有限的design build，不能据此宣告最终样本完整。两个主wave在拟议严格clean筛选下为空，是必须先解释的设计问题，不是行情下载问题。

## 单一下一步

执行主方案P0/P1/P3：**一次零采购、outcome-blind design build**，并把所需P2测量放入同一队列。

- 输入：现有版本化package/exposure、expanded earnings metadata、71-stock acquisition union、header/clock/repair receipts。先分清population版本，不能pool；旧free parquet与E007不替换最终PRE-A exposure。
- 首批输出：逐wave/tier的sequential attrition、calendar-cell支持、symbolic rank/alias、event/sponsor/date依赖，以及精确缺输入表。所有UNKNOWN单列，不写成零。旧all-12-events筛选与合同事件级要求分开报告。
- 并行：Sol/medium实现design；Terra/medium实现measurement adapter；纯合成测试由Sol/medium接续。不新建“全项目审计团队”。
- 下一阶段：仅依赖合格且明确获准的PRE输入做SUE/covariance校准与条件power模拟。Astra/high在完整决策packet形成后裁决，不监控下载。
- 停止：任何结构性失败直接报告指定目标为何不可估，最多一次明确amendment建议。不用无限补数挽救原本不存在的支持。

本次已经完成的是方案与盘点/复核，以上实施队列尚未运行。未购买数据、未访问SCC、未估计真实power/POST效应、未commit/push。新科学选择与精确操作权限按主方案统一决定包处理，不要求再次批准整份旧合同。
