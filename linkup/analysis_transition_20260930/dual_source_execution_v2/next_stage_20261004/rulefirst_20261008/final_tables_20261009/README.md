# T1–T6 固定样本结果，2026-10-09

最终 v2 已完成并通过独立工程验收。范围为 7,635 个独立文本，对应固定样本的 10,000 条广告记录，未加权；不是全库或美国总体结果。

先读 [结果与解释边界](FINDINGS_AND_LIMITS.md)。六表在 [public](public/)；逐字段验收见 [D57](ROOT_FIELD_ACCEPTANCE.json)，独立核验见 [QA](QA_FINAL_TABLES_PUBLIC.json)。

BU SCC 作业 `7978196` 在 econ 队列以 4 个 CPU slot 完成最终聚合，运行 12 秒，failed=0、exit_status=0。这是复用已有提取结果的汇总，不是 12 秒重新提取全部正文。本轮无付费 API 或批量模型调用。[执行回执](public/FINAL_TABLES_EXECUTION_PUBLIC.json)。

v1 将部分既往 mentoring 经验纳入当前职责，已由 v2 更正。旧表及旧 QA 保留并标记 superseded，不应用于最终报告。工程验收不等于语义准确率得到验证。
