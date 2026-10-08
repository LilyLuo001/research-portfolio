# Contextual handoff 交付说明

本目录记录 D53 的上下文复核准备与公开结果。冻结的 rule-first v1.2 已处理
7,635 个独立文本、代表 10,000 行；本阶段不改写既有规则输出，不宣称已有
语义生产验收或新的 API 标签。

经验局部截取规则使 7,359/7,635 篇回退全文（96.4%），保留
45,770,100/46,319,767 个字符（98.8%），因此选择 B 一次联合全文判读。
这些是覆盖与路由记录，不是准确率。

预算仅作情景比较，不是预测或保证：

| 每篇总输出预算 token（含隐藏推理） | 7,635 篇 GPT-6 Astra Batch 估算费用 |
|---|---:|
| 1,024 | $295–362 |
| 4,096 | $882–948 |
| 8,192 | $1,663–1,730 |
| 25,000 | $4,872–4,938 |

费用情景使用输入 UTF-8 bytes 除以 5 到 3 的规划换算；这不是严格上下界，且不含
重试、税费或额外审计。费率依据 [OpenAI pricing](https://developers.openai.com/api/docs/pricing)。

Root 负责变量契约与决策，Sol 负责 BU 计划任务 `7963223`，另有独立 QA；Luna
负责 Git 与来源记录。上下文输入、私有绑定和逐行输出不进入 Git。最终发布仍
等待 Sol 的归档状态与 qacct：需以已验证并清理完成，或明确 blocked 收据为准。

公开来源：

- [上下文收据](../../cloud_execution_20261008/rulefirst_20261008/contextual_handoff_public/CONTEXT_HANDOFF_RECEIPT_PUBLIC.json)
- [按 arm 的范围计数](../../cloud_execution_20261008/rulefirst_20261008/contextual_handoff_public/SCOPE_COUNTS_BY_ARM_PUBLIC.csv)
- [按 arm 的上下文计数](../../cloud_execution_20261008/rulefirst_20261008/contextual_handoff_public/CONTEXT_COUNTS_BY_ARM_PUBLIC.csv)
- [预算情景](../../cloud_execution_20261008/rulefirst_20261008/contextual_handoff_public/BUDGET_SCENARIOS_PUBLIC.csv)
