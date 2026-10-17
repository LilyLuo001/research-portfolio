# CPU 监督文本 baseline：固定 holdout 与真实分片结果

作业 46770303 在 WZ `wzhdtest` 完成（0:0）。模型仅在固定训练 contexts 上拟合，holdout 不参与词表或模型拟合，也未用于调参。指标是对既有兼容语义标签的预测评估，不称为人工准确率。

真实输入为字典序第一份 LinkUp parquet（总 124,855 行）的原序前 20,000 行；20,000 条正文均有效。读取原文、冻结 normalizer、27 个目标逐模型 vectorize/predict、writer close/原子改名共 573.527 秒，即 34.872 行/秒。模型已在内存，计时不含 pickle 加载。

| target | fit/eval | train 0/1 | holdout 0/1 | TN/FP/FN/TP | class0 P/R/F1 | class1 P/R/F1 | macro F1 | majority class/macro F1 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| entry_presence.current_student_internship | fit/evaluated | 595/32 | 177/7 | 177/0/6/1 | 0.9672/1.0000/0.9833 | 1.0000/0.1429/0.2500 | 0.6167 | 0/0.4903 |
| entry_presence.explicit_junior_or_entry_label | fit/insufficient_holdout_class_support | 600/27 | 182/2 | 182/0/2/0 | 0.9891/1.0000/0.9945 | 0.0000/0.0000/0.0000 | 0.4973 | 0/0.4973 |
| entry_presence.explicit_new_graduate | fit/insufficient_holdout_class_support | 602/25 | 181/3 | 180/1/2/1 | 0.9890/0.9945/0.9917 | 0.5000/0.3333/0.4000 | 0.6959 | 0/0.4959 |
| entry_presence.explicit_no_experience | fit/insufficient_holdout_class_support | 605/22 | 180/4 | 180/0/4/0 | 0.9783/1.0000/0.9890 | 0.0000/0.0000/0.0000 | 0.4945 | 0/0.4945 |
| experience_presence.general_work | fit/evaluated | 457/105 | 119/40 | 111/8/28/12 | 0.7986/0.9328/0.8605 | 0.6000/0.3000/0.4000 | 0.6302 | 0/0.4281 |
| experience_presence.industry_domain | fit/evaluated | 272/290 | 73/86 | 50/23/19/67 | 0.7246/0.6849/0.7042 | 0.7444/0.7791/0.7614 | 0.7328 | 1/0.3510 |
| experience_presence.occupation_task | fit/evaluated | 39/523 | 13/146 | 1/12/0/146 | 1.0000/0.0769/0.1429 | 0.9241/1.0000/0.9605 | 0.5517 | 1/0.4787 |
| experience_presence.tool_specific | fit/evaluated | 109/453 | 21/138 | 12/9/9/129 | 0.5714/0.5714/0.5714 | 0.9348/0.9348/0.9348 | 0.7531 | 1/0.4646 |
| strict_current_duty.client_ownership | fit/evaluated | 472/112 | 129/33 | 126/3/18/15 | 0.8750/0.9767/0.9231 | 0.8333/0.4545/0.5882 | 0.7557 | 0/0.4433 |
| strict_current_duty.independent_judgment | fit/evaluated | 185/399 | 46/116 | 18/28/13/103 | 0.5806/0.3913/0.4675 | 0.7863/0.8879/0.8340 | 0.6508 | 1/0.4173 |
| strict_current_duty.people_supervision | fit/evaluated | 492/92 | 131/31 | 126/5/24/7 | 0.8400/0.9618/0.8968 | 0.5833/0.2258/0.3256 | 0.6112 | 0/0.4471 |
| strict_current_duty.training_mentoring | fit/evaluated | 381/203 | 102/60 | 87/15/33/27 | 0.7250/0.8529/0.7838 | 0.6429/0.4500/0.5294 | 0.6566 | 0/0.3864 |
| technology_family.generative_ai | fit/evaluated | 310/187 | 81/57 | 72/9/9/48 | 0.8889/0.8889/0.8889 | 0.8421/0.8421/0.8421 | 0.8655 | 0/0.3699 |
| technology_family.predictive_ml_ai | fit/evaluated | 364/133 | 105/33 | 96/9/13/20 | 0.8807/0.9143/0.8972 | 0.6897/0.6061/0.6452 | 0.7712 | 0/0.4321 |
| technology_family.traditional_software_system | fit/evaluated | 28/469 | 6/132 | 0/6/4/128 | 0.0000/0.0000/0.0000 | 0.9552/0.9697/0.9624 | 0.4812 | 1/0.4889 |
| technology_family_role.generative_ai.background_mention | fit/insufficient_holdout_class_support | 487/10 | 135/3 | 135/0/3/0 | 0.9783/1.0000/0.9890 | 0.0000/0.0000/0.0000 | 0.4945 | 0/0.4945 |
| technology_family_role.generative_ai.develop_technology | fit/evaluated | 404/93 | 113/25 | 109/4/7/18 | 0.9397/0.9646/0.9520 | 0.8182/0.7200/0.7660 | 0.8590 | 0/0.4502 |
| technology_family_role.generative_ai.implement_deploy_technology | fit/evaluated | 463/34 | 126/12 | 125/1/11/1 | 0.9191/0.9921/0.9542 | 0.5000/0.0833/0.1429 | 0.5485 | 0/0.4773 |
| technology_family_role.generative_ai.use_tool_for_work | fit/evaluated | 392/105 | 101/37 | 95/6/22/15 | 0.8120/0.9406/0.8716 | 0.7143/0.4054/0.5172 | 0.6944 | 0/0.4226 |
| technology_family_role.predictive_ml_ai.background_mention | fit/insufficient_holdout_class_support | 481/16 | 135/3 | 135/0/3/0 | 0.9783/1.0000/0.9890 | 0.0000/0.0000/0.0000 | 0.4945 | 0/0.4945 |
| technology_family_role.predictive_ml_ai.develop_technology | fit/evaluated | 422/75 | 116/22 | 108/8/11/11 | 0.9076/0.9310/0.9191 | 0.5789/0.5000/0.5366 | 0.7279 | 0/0.4567 |
| technology_family_role.predictive_ml_ai.implement_deploy_technology | fit/evaluated | 470/27 | 129/9 | 128/1/9/0 | 0.9343/0.9922/0.9624 | 0.0000/0.0000/0.0000 | 0.4812 | 0/0.4831 |
| technology_family_role.predictive_ml_ai.use_tool_for_work | fit/evaluated | 458/39 | 132/6 | 126/6/4/2 | 0.9692/0.9545/0.9618 | 0.2500/0.3333/0.2857 | 0.6238 | 0/0.4889 |
| technology_family_role.traditional_software_system.background_mention | fit/insufficient_holdout_class_support | 476/21 | 134/4 | 131/3/4/0 | 0.9704/0.9776/0.9740 | 0.0000/0.0000/0.0000 | 0.4870 | 0/0.4926 |
| technology_family_role.traditional_software_system.develop_technology | fit/evaluated | 343/154 | 99/39 | 89/10/13/26 | 0.8725/0.8990/0.8856 | 0.7222/0.6667/0.6933 | 0.7895 | 0/0.4177 |
| technology_family_role.traditional_software_system.implement_deploy_technology | fit/evaluated | 382/115 | 106/32 | 94/12/18/14 | 0.8393/0.8868/0.8624 | 0.5385/0.4375/0.4828 | 0.6726 | 0/0.4344 |
| technology_family_role.traditional_software_system.use_tool_for_work | fit/evaluated | 95/402 | 23/115 | 8/15/12/103 | 0.4000/0.3478/0.3721 | 0.8729/0.8957/0.8841 | 0.6281 | 1/0.4545 |

`insufficient_holdout_class_support` 表示 holdout 任一类别少于 5；原始混淆矩阵与指标仍保留作透明记录，不能解释为语义通过。

支持范围只含 27 个二元 presence 目标。不支持经验强度（必需/优先）、经验条件性与逻辑分支、字面数值年限、开放命名对象、逐字证据及资格分支关系重建。LinearSVC 仅写二元类别；margin 不是概率且未写出。

若把实测 34.872 行/秒机械用于 204,774,035 行，单个同类作业约 67.96 天。该数仅在相同 27 目标、schema、文本长度分布、存储吞吐、逐目标串行 vectorize 且同样不计模型加载时成立；没有授权全库推断，也不主张线性扩展。

私有模型：`/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline/artifacts/tfidf_linearsvc_holdout_frozen.pkl`

私有 sidecar：`/work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline/sidecar/first_linkup_shard_first20000_predictions.parquet`
复跑：`sbatch /work/home/lilysharp/private/fixed10k_semantic_production_20261017/private/baseline/code/wz_train_evaluate_infer.sbatch`
