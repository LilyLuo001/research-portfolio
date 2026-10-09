# D58 增量生产（进行中）

本目录记录用户于 2026-10-09 批准的 BU SCC 增量生产方案。任务把已冻结的 rulefirst-v1.2、relation overlay 和 D57 v2 responsibility gate 应用于实际语料的已准入 shard；不改变规则，不调用付费 API，不启动新的模型推理。固定的 7,635 篇/10,000 行样本仍是此前独立的规则测量，不能当作本轮全语料生产结果。

首批输入由昆山经本机 SSH 流式转发至 BU，Mac 不落地原始正文。首批作业须先证明调度成功、输入行守恒、shard 内 canonical key 唯一、source/evidence 坐标和 schema 与冻结代码一致、unknown/conditional/empty/failed 状态保留，以及按 code+input hash 可幂等恢复；在验收前不会盲目扩展并发或重跑全库。首批实际作业已完成并通过独立 QA：82880 个 canonical USA rows、421154 个 evidence rows，生产耗时 179.693 秒；这只是冻结规则的首个 shard，不能外推为全库完成。下一组四个 disjoint shards 已提交 BU 调度（7979088、7979089、7979111、7979090）；部分仍在运行或等待退出，尚未宣称完成。运输清单的 1,106,065,455 bytes 为已核验输入总量，不是处理完成量。

公开结果只能包含聚合数量、状态、吞吐、代码/输入 provenance 和脱敏回执。JOB_HASH、SOURCE_ROW、原文、私有 JSONL、模型/runtime 私有包、凭据和逐行输出不得进入 Git；公开回执可保留经审查的 source-file basename 元数据。COMPANY_ID 仍是 source company identity，不等于法人或集团母公司；O*NET 是当前交付快照；CREATED year 是观察元数据，不是正文发布时间。no-match 不是已验证不存在，角色标签仍是词汇指标；任何对强度、对象、技术角色或因果关系的解释都须保留限制。

- 主决策：[ROOT_PRODUCTION_DECISION.json](ROOT_PRODUCTION_DECISION.json)
- 映射复用审计：[MAPPING_REUSE_AUDIT.json](MAPPING_REUSE_AUDIT.json)
- 状态：BU 首批 shard 传输及首个生产作业待回执；归档、清理和全量扩展均未宣称完成。
