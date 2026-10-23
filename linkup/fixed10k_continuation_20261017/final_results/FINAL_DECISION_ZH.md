# 单次最终基线：评估与生产裁决

裁决时间：2026-10-23T15:22:45.072871+00:00。门槛提交 `3e76a62` 早于最终训练与查看成绩。

**结论：0 个字段获准正式生产，10 个仅作候选辅助，17 个不采用或支持不足。当前 TF-IDF + LinearSVC 基线试验结束，不自动再补标、调参或重新训练。全项目的复杂语义生产并未因此完成。**

参考标注停在 Batch069：原剩余6,500份中6,486份补判完成，可处理队列0，14份原文无法恢复仍隔离。1,002份含已审未知，按字段保留，不整体返工。本轮新增审阅0。

最终训练作业47251408已实际完成，180秒、8CPU；聚合裁决作业47251980完成，1秒、2CPU。训练采用固定模型与划分，最终1,331个留出及旧留出均不入训练。97个最终留出有历史暴露记录，因此全体不得称盲测。全部指标均相对Pro参考标签，不是人工真值准确率。

## 为何未放行

- 一般工作经验的正类精确率46.2%、召回率31.9%，漏检严重。
- 职业／任务经验虽正类召回率95.9%，负类召回率仅35.3%；不能用高正类分数掩盖大量误报。
- 独立判断职责的负类精确率44.3%、召回率44.1%，不足以支撑初级岗位职责比较。
- 生成式AI类别总体正类精确率92.5%、召回率88.5%，但A组仅2个负例且均判错；B组仅12个正例，精确率／召回率均50%。总体好看不能认证关键比较组，所以仅候选。

## 逐字段结果

表中N/P是有效负／正例数；P/R为精确率／召回率。完整混淆矩阵、两类F1、预测正类占比、Wilson下界、各比较组和暴露组及逐项失败原因见同目录JSON与CSV。

| 目标 | 训练N/P | 评估N/P | 负类P/R | 正类P/R | 裁决 |
|---|---:|---:|---:|---:|---|
| `entry_presence.current_student_internship` | 5783/238 | 1275/52 | 99.1%/99.5% | 87.0%/76.9% | 仅候选／辅助 |
| `entry_presence.explicit_junior_or_entry_label` | 5846/175 | 1294/33 | 97.9%/99.4% | 42.9%/18.2% | 不采用／支持不足 |
| `entry_presence.explicit_new_graduate` | 5966/55 | 1317/10 | 99.3%/99.8% | 25.0%/10.0% | 不采用／支持不足 |
| `entry_presence.explicit_no_experience` | 5920/101 | 1313/14 | 99.2%/99.2% | 26.7%/28.6% | 不采用／支持不足 |
| `experience_presence.general_work` | 4795/1142 | 1032/285 | 82.7%/89.7% | 46.2%/31.9% | 不采用／支持不足 |
| `experience_presence.industry_domain` | 3213/2724 | 726/591 | 77.2%/72.7% | 68.7%/73.6% | 仅候选／辅助 |
| `experience_presence.occupation_task` | 607/5330 | 136/1181 | 49.5%/35.3% | 92.8%/95.9% | 不采用／支持不足 |
| `experience_presence.tool_specific` | 1011/4926 | 207/1110 | 51.5%/58.5% | 92.1%/89.7% | 不采用／支持不足 |
| `strict_current_duty.client_ownership` | 4491/1476 | 1015/312 | 88.1%/90.5% | 66.2%/60.3% | 仅候选／辅助 |
| `strict_current_duty.independent_judgment` | 1906/4061 | 413/914 | 44.3%/44.1% | 74.8%/74.9% | 不采用／支持不足 |
| `strict_current_duty.people_supervision` | 4982/985 | 1111/216 | 93.3%/95.7% | 74.5%/64.8% | 仅候选／辅助 |
| `strict_current_duty.training_mentoring` | 3824/2143 | 861/466 | 85.2%/88.9% | 77.6%/71.5% | 仅候选／辅助 |
| `technology_family.generative_ai` | 3551/1876 | 789/416 | 94.1%/96.2% | 92.5%/88.5% | 仅候选／辅助 |
| `technology_family.predictive_ml_ai` | 4019/1408 | 854/351 | 89.9%/91.7% | 78.7%/74.9% | 仅候选／辅助 |
| `technology_family.traditional_software_system` | 591/4836 | 135/1070 | 34.1%/34.8% | 91.8%/91.5% | 不采用／支持不足 |
| `technology_family_role.generative_ai.background_mention` | 5263/164 | 1167/38 | 97.2%/98.7% | 25.0%/13.2% | 不采用／支持不足 |
| `technology_family_role.generative_ai.develop_technology` | 4479/948 | 993/212 | 96.1%/94.7% | 76.7%/82.1% | 仅候选／辅助 |
| `technology_family_role.generative_ai.implement_deploy_technology` | 5120/307 | 1134/71 | 95.6%/97.5% | 41.7%/28.2% | 不采用／支持不足 |
| `technology_family_role.generative_ai.use_tool_for_work` | 4633/794 | 1039/166 | 92.1%/93.6% | 55.3%/50.0% | 不采用／支持不足 |
| `technology_family_role.predictive_ml_ai.background_mention` | 5235/192 | 1147/58 | 95.4%/98.4% | 18.2%/6.9% | 不采用／支持不足 |
| `technology_family_role.predictive_ml_ai.develop_technology` | 4548/879 | 996/209 | 95.4%/93.1% | 70.4%/78.5% | 仅候选／辅助 |
| `technology_family_role.predictive_ml_ai.implement_deploy_technology` | 5175/252 | 1134/71 | 94.8%/97.3% | 24.4%/14.1% | 不采用／支持不足 |
| `technology_family_role.predictive_ml_ai.use_tool_for_work` | 5117/310 | 1132/73 | 94.9%/96.5% | 25.9%/19.2% | 不采用／支持不足 |
| `technology_family_role.traditional_software_system.background_mention` | 5073/354 | 1130/75 | 93.8%/96.9% | 7.9%/4.0% | 不采用／支持不足 |
| `technology_family_role.traditional_software_system.develop_technology` | 3595/1832 | 798/407 | 85.5%/85.6% | 71.7%/71.5% | 仅候选／辅助 |
| `technology_family_role.traditional_software_system.implement_deploy_technology` | 4341/1086 | 953/252 | 87.1%/87.6% | 52.0%/50.8% | 不采用／支持不足 |
| `technology_family_role.traditional_software_system.use_tool_for_work` | 1967/3460 | 442/763 | 57.2%/59.0% | 75.8%/74.4% | 不采用／支持不足 |

## 模型、速度与生产状态

私有冻结模型：

`/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline_optimized/final_fit/run/FINAL_PRESENCE_BASELINE_PRIVATE.pkl`

SHA256：`d30ee5527e82d2980680e64ae16614c371a8fa26367582d21a139f20b16f2f49`。模型、成员清单和正文不进入Git。

本次实际训练流水线：读取1.63秒、标准化22.53秒、特征转换64.25秒、拟合69.82秒、评估预测0.109秒、模型写盘2.82秒，总计162.24秒；共享4组特征矩阵。总计还含未逐项列出的调度内Python开销。该速度不是新模型全库推断速度。

**正式生产提交0个分片。最终模型的真实分片推断、全库工期估算均未执行**：无字段通过质量门槛，不为测速而运行已知不合格字段。旧模型20,000行/117.92秒的结果保留为历史工程基线，不冒充新模型工期依据。

年限与对象绑定、必需／优先、替代分支、职责主体关系重建、原文证据抽取仍未实现；任何二元预测都不替代它们。候选框外人口未经认证。

## 复现入口与终止规则

已执行命令（记录用途，不得重新提交）：

```bash
sbatch /work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline_optimized/code/wz_final_fit.sbatch
sbatch /work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline_optimized/code/wz_adjudicate_final_fields.sbatch
```

代码：`../baseline_optimized/code/`；冻结门槛：`../FINAL_FIELD_ADOPTION_RULES.json`；完整裁决：`FINAL_FIELD_ADJUDICATION_PUBLIC.json`；逐目标逐组表：`FINAL_FIELD_ADJUDICATION_PUBLIC.csv`；运行与根裁决：`FINAL_RUN_AND_ROOT_DECISION_PUBLIC.json`。

本轮按预定停止规则关闭基线试验。保留全库粗处理、Formal800及fixed10k参考标签；不因本次分类器失败而重开这些工作，不新增资源申请。后续研究范围或生产通道改变需要用户明确决定。
