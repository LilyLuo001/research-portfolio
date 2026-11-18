# 阶段五实际结果与停点

**主确认已完成评分；没有合格的 Luna 试产字段。Astra 诊断未取得模型答案，因此不能称整轮独立审核全部完成。**

## 已做完

- 固定150候选排除15个既有上下文后，135个新上下文不补样。Luna与Kimi各135次请求，均已终态记账。
- Kimi已直接使用Azure VM托管身份；实际配额300万TPM。此前11次响应复用，v4新增124次；最终134个完整响应、1个截断输出保留，不重跑。
- 原冻结评分器已在Azure运行，51个独立研究量分别判定；不是13字段捆绑判整条。
- 26项因正例支持或参考覆盖不足而证据不足；25项支持量足够但至少一项既定质量指标不足。最终合格项0，1万条/$150试产没有启动。

## 这次到底卡在哪里

第一，当前廉价候选Luna相对独立Kimi的一致性不足，不是Kimi配额或SSH问题。接近门槛的字段和核心字段要分开看：

| 研究量 | 正例Precision | 正例Recall | 二类Macro-F1 | 主要不足 |
|---|---:|---:|---:|---|
| 职业/任务经验提及 | 79.7% | 80.9% | 81.1% | outcome_macro_f1_below_gate, outcome_precision_below_gate |
| 行业经验年限 | 84.6% | 42.3% | 72.5% | outcome_macro_f1_below_gate, outcome_precision_below_gate, outcome_recall_below_gate, supported_relation_precision_below_gate, supported_relation_recall_below_gate, supported_relation_f1_below_gate |
| 人员监督提及 | 87.5% | 84.0% | 91.1% | outcome_precision_below_gate |
| 培训指导提及 | 100.0% | 75.6% | 90.8% | outcome_recall_below_gate |
| 技术提及 | 91.1% | 81.8% | 80.9% | outcome_macro_f1_below_gate |

这些是机器参考一致性，不是人工准确率，也不代表五亿总体。关系型字段另受原关系门槛约束，上表不是给未通过项变相放行。

第二，Astra的6次请求全部HTTP400：Responses的json_object要求input本身含json；脚本只在instructions里写了JSON。这是11月16日曾记录并修复过、此次被重新引入的工程错误，不是模型不够强，也不是没权限。0个Astra判断，不能冒充6条审核。
错误正文、原账本和输出槽位均保留；已定位旧修复，另备未应用补丁。不重置6次物理请求上限，不用额外调用或Astra替换Kimi来改写本次primary结果。

## 成本与时间

- 本轮请求保守预留 **$37.2664 / $50**；有usage部分按原记录单价计算约 **$12.5209**。两者不相加，未核实Azure发票。Astra无usage不当作零实际费用。
- Kimi v4直接执行约 **73.0分钟**；本次固定确认保持原串行调度，并未宣称用满300万TPM。
- 原历史预留不重置；本轮未花试产$150。上述数额不含现有VM/存储或Codex会话费用。

## 后续边界

此次固定确认已给出决定，不再重抽一批、换一套门槛反复求pass。不能自动把Luna扩大到1万条或全库；已保存结果作为版本化机器输出保留，不覆盖旧accepted。
已有基础清洗、旧验收语义和复用增量仍按各自原范围有效。五大模块及LinkUp—Revelio目标不缩减；本结果既不证明五亿处理完成，也不证明Kimi自身不合格。
Astra未应用的传输修复与有界恢复需另列明确执行版本；当前阶段五三个模型进程均已结束。真正的全量缺口、可接受的测量误差和后续生产路线仍未解决，不虚报完成。

## 结果位置

- 云端评分：`[private-runtime-path]`
- 云端Kimi输出：`[private-runtime-path]`
- 云端Astra失败及诊断：`[private-runtime-path]`
- 本机对应目录：`[private-runtime-path]`
