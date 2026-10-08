# Rule-first 交付说明

本阶段使用 BU 计划任务 `7960837` 执行冻结的 rule-first v1.2。它处理了
7,635 个独立文本、代表固定样本 10,000 行，处理错误为 0，证据坐标检查
225,838 次且错误为 0。开发集 120 行、评价集 80 行、21 个 synthetic cases
均有公开收据；这些检查和表格是候选测量与覆盖记录，不是语义准确率验证。

六组公开表：

- [T1 完整性](../cloud_execution_20261008/rulefirst_20261008/full_public/T1_EXPANSION_COMPLETENESS.csv)
- [T2 经验对象/强度/范围/年限](../cloud_execution_20261008/rulefirst_20261008/full_public/T2_EXPERIENCE_OBJECT_STRENGTH_SCOPE_YEARS.csv)
- [T3 技术角色线索](../cloud_execution_20261008/rulefirst_20261008/full_public/T3_TECH_ROLE_CUES.csv)
- [T4 创建年份快照](../cloud_execution_20261008/rulefirst_20261008/full_public/T4_CREATED_YEAR_SNAPSHOT.csv)
- [T5 入门经验与任务共现](../cloud_execution_20261008/rulefirst_20261008/full_public/T5_ENTRY_EXPERIENCE_TASK_COOCCURRENCE.csv)
- [T6 敏感性与可用性](../cloud_execution_20261008/rulefirst_20261008/full_public/T6_SENSITIVITY_AVAILABILITY.csv)

7031 行包含至少一个规则绑定的数值经验句，4999 行包含至少一个未触发
engine review 的数值句。这些是规则输出计数；`clear` 或 `required` 不是已验证
语义标签，未匹配也不等于没有经验要求。根的六篇全文 AI 诊断发现标题继承、
经验对象和 required/preferred 作用域等实质问题，因此不得宣称 strength、
object 或 technology-role 已通过正式语义验收，也不得声称全库清洗完成。
固定样本的 `created_year` 仅覆盖 2023–2026。旧 B 组 4,000 行中有 61 行出现
当前 GenAI 词典匹配，因此不能把 B 组当作纯无 AI 对照；词匹配也不等于岗位采用 AI。

CPU 基础检索已完成，但强度、对象和技术角色关系仍是候选结果，尚未通过正式
语义量产验收。

本阶段不启动新模型或付费 API；旧 Qwen 结果保持历史不变。私有文本、证据和
逐行链接只在集群回传并完成 SHA 校验后处理，Git 仅保存公开代码、聚合表和收据。
BU 到昆山的结果归档回传仍在进行，BU 暂未删除；本次发布不宣称归档已完成。
