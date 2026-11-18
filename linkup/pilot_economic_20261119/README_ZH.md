# LinkUp 经济阈值增量试产（2026-11-19）

最新首100条闭环、吞吐与5亿条件报价见 `FIRST100_AND_SCALE_ZH.md`。

## 本轮实际执行

- 现有 Azure VM `linkup-transfer`（Standard_B2als_v2，2 vCPU / 约 4 GB）承担计算；已有 ARM service principal 通过 VM Agent 控制，VM managed identity 访问 Blob 与模型。未使用 OpenCode、SCNet、GPU、新资源或计时器。
- 云端独立目录：`/home/linkup/migration/pilot_economic_20261119/run01`。
- 从真实旧断点 `shard_ordinal=0,row_offset=52804` 起步。前100物理行准备出93个新正文；下一900行准备出792个新正文。累计1000行全部有物理映射，885个新正文，115行旧状态保留且不重推。
- CPU规则已实际完成885个新正文的候选提取。93条耗时0.392秒、792条耗时3.346秒；这是短时内核性能，不是全库I/O或B系列虚机持续吞吐保证。
- Luna主处理已真实启动；Kimi首5次独立对照、Astra首1次传输诊断均已返回并完成字段机械校验。不能将这些事实当作准确率或人工验收。
- Astra新请求的`input`增加`Return JSON.`，已验证原HTTP400消失。旧6次失败输出及原135条评分未修改。
- 实际响应头：Luna250,000 TPM、Kimi3,000,000 TPM、Astra1,000,000 TPM。通过有回执的静止断点修改**调度**：Luna80k→200k，4个网络工作线程；仍共享800k调度上限。原policy、claims、成本预留、时间窗、结果SHA均不变。
- 有界后台控制器已启动：先等待首批结束，再串联下一批，最多10000物理行、48小时、$150；有独占锁、逐次请求前预留、失败状态保留、断点与每批SHA，不是无限生产许可。

## 测量口径：按用户新授权放行，不改旧成绩

`measurement/ECONOMIC_RELEASE_PUBLIC.json`绑定旧135条评分SHA，发布15个旧二元outcome Macro-F1 ≥0.80的研究量。

这是看过确认结果后的**显式政策调整**，不是新的独立验证，更不是经济学普遍承认的统一质量标准。分字段保留有效值，未知不填0。`.relations`、`.conditionality`、`.family_role`、`.exact_named_relation`放行的是原评分的**二元是否存在结果**，不是宣称完整关系、对象、条件、工具名称都达到该F1。完整结构仍标记`saved_unverified`。

CPU提供数字/学历/工具等原文命中、offset与条件线索；没命中不等于没要求。年限不自动压成无条件最低年限，附近的行业词不自动证明年限属于该行业。禁止为追求通过率强猜未知或丢弃物理行。

## 数据、回填和断点

- `preparation/batch0001`与`batch0002`：输入、物理映射、排除账本、来源Range回执、CPU结果和manifest。
- `ADMISSION_PRIVATE.sqlite3`：唯一共享请求/预算/结果SHA账本。
- `results/<模型>/<正文SHA>/`：不可覆盖原始响应和字段校验结果。
- `projection/batchNNNN/PHYSICAL_INCREMENT_PRIVATE.jsonl`：累计物理回填，包括分字段语义结果与CPU候选；旧/隔离状态、缺失仍保留。
- `control/FINITE_PIPELINE_STATE_PUBLIC.json`：真实后台状态；prepared不是completed。
- `control/batchNNNN_FINITE_COMPLETE_PUBLIC.json`：每批计算/投影完成回执。
- 新出现的provider隔离会同时阻止该上下文的语义和CPU结果发布，不通过规则或其他模型绕行。

## 预算和全量边界

旧模型保守预留$215.3315657；本轮最多$150（Luna110/Kimi25/Astra15），基础设施预留$50；合计保守框架$415.3315657，仍在原$450内。实际token计价仅估算，不能再加到保守预留上当重复费用，也不是Azure发票。上述仅为云端研究脚本账本；Codex会话/协作代理的供应商费用不受该脚本限额控制，本轮完整客户端计费未核实。后台未自动启动新的Kimi/Astra额度，当前为5次/1次。

5亿商业物理行目标保留。已核实的204,774,035美国规范广告、298,673,078 Description原始行、356,449,214 Records页脚行是不同口径，**不能相加**。全范围不重叠物理分母和真正缺失的唯一正文数仍待明确；1000行的局部复用比例不能外推成5亿全局缓存率。

全量报价应为：CPU/存储/回填 + 缺失唯一正文的Luna成本 + 有限Kimi/Astra成本；不能把5亿物理行直接当5亿模型调用，也不能承诺Hash缓存一定能把模型账单压进几千美元。本轮最多1万条是吞吐压测和增量，不是将5亿研究范围缩小为样本。

## 复现与安全

代码及合成测试可在本地执行；真实广告读取、清洗、模型运行、统计与投影均在云端。Git只保存代码、公开汇总和回执；不含广告正文、逐行身份、模型原文、私钥、SAS或令牌。

勿重新运行初始部署脚本作为“重置”。它们使用不可覆盖文件与旧断点绑定；恢复应先检查云端账本和后台状态。`STOP`阻止新领取但不强杀在途请求。原provider受限线程及batch035继续隔离。CREATED仍只代表首次观察时间代理，不自动构成AI因果识别。
