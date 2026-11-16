# LinkUp 复用优先执行留痕（2026-11-15）

本目录保存当前“复用已有成果 → 有限实测低成本路线 → 以真实剩余工作量报价 → 分层完成全量”的公共控制面记录。创建这些记录不代表数据生产已经运行或完成。

## 最新研究方向更正（2026-11-16，非生产启动）

用户否决了上一份 good-enough 提案的“最终以代表性样本替代全量、只保留两个核心变量”。约 5 亿条全部交付记录与未来增量仍为目标，实际唯一身份总量仍待核清。恢复机会数量、任务与经历组合、跨背景人员进入以及计算机化/AI比较的原研究主线；Revelio 从变量定义阶段参与。原提议与原资格失败记录不改写。论文增产暂停，不恢复定时器。

最新文档位于 `research_agenda_recovery_20261116/`：`RESEARCH_AGENDA_AND_MEASUREMENT_ZH.md`、`RESEARCH_TO_FIELDS_PUBLIC.json`、`REVIEW_SOURCES_PUBLIC.json`、`AGENDA_STATUS_PUBLIC.json`。本轮只完成研究复核与方案纠偏，未启动新云任务、模型测试或生产，未改变运行策略/预算。最近已保存的生产资格终态见 `execution_20261116/continuation02/final/CHECKPOINT_PUBLIC.json`：固定资格结束、0字段通过、0新增正式生产；下方早期20条测试内容是历史记录。

## 当前边界

- 目标仍是全部 LinkUp 交付数据，不把固定 1 万样本、Formal800 或单一已挂载美国目录当成完整目标。约 5 亿交付行不自动等于 5 亿独立新模型请求。
- 数据计算只使用已有授权 Azure；本机只做代码、配置、公开汇总、回执和 Git。不要连接国内 SCNet / BU，不恢复计时器或已关闭复制服务。
- 优先复用已经验收且输入、schema、上下文严格兼容的结果。原 PRIMARY、accepted 账本、失败输出、原 schema、已审未知与保护隔离项不覆盖、不自动重跑；不绕过提供商限制。
- 用户不做真人审核。采用独立模型审核、原文证据与结构关系校验，明确其不是人工金标准；不通过降低规则或改写历史结果制造通过。
- 训练/蒸馏不是前置工程。允许有明确数额上限、任务数量及停止条件的有限付费实测；本记录本身没有发起调用或批准无上限全库推理。
- 旧 $5,000 分配方案已撤回为默认报价，保留作历史情景。Azure credit 不是必须花完的目标；旧 $800 与当前全量路线必须按同一分母、字段及费用边界比较。
- CREATED 是首次观察时间代理。招聘新增、活跃存量、退出分别统计；前后变化不自动等于 AI 因果效应。Revelio 属于后续劳动市场扩展；WRDS tick 保持独立。

## 记录导航

- `AUTHORIZATION_AND_BOUNDARIES_PUBLIC.json`：当前授权、保护边界、Git 起点和旧指令被替代的有限范围。
- `BUDGET_RECONCILIATION_PUBLIC.json`：旧报价与新方案的分母和方法核对。
- `OLD_OCT09_BUDGET_PROVENANCE_PUBLIC.json`：7,635 唯一正文 / 10,000 样本报价的原始行号、公式和 SHA。
- `NEW_5000_PLAN_CORRECTION_AUDIT_PUBLIC.json`：新 $5,000 预算池不等于已测得必要成本。
- `PUBLIC_COPY_MANIFEST.json`：三个源文件的原始 SHA、公开副本 SHA 及路径去标识处理。
- `PUBLIC_GIT_ALLOWLIST.json` / `scan_public_git.py`：只允许本目录已审白名单文件的轻量检查；拒绝路径越界、符号链接、疑似凭据、记录标识和原文字段。
- `PUBLIC_GIT_SCAN_RECEIPT.json`：实际扫描结果。它只是发布检查，不是语义验收证明，也不能保证发现任意形式的秘密。

## Git 操作纪律

不使用 `git add -A`，不混入其他目录或别人已有的 staged / untracked 内容。本次准备不暂存、不提交、不 push。提交时必须逐个白名单路径精确暂存，再运行扫描的 `--check-staged` 校验；新文件加入白名单前应逐一检查。代码、非敏感配置、汇总和回执可以入库；凭据、正文、逐条记录标识、模型原始输出与私有映射不得入库。

读取来源时，`repository:` 代表本仓库相对路径，`external_public:` 代表仓库外已有公开交接文件的来源别名。原件不改动；这些副本保留原始 SHA 以便私下核对。

## 固定 20 条执行与版本留痕

本目录新增环境、准备、部署、模型通道和启动/早期状态快照，以及冻结配置、worker、launcher、只读状态器和结束后的只读比较/归档代码。各文件记录自己的观测时间；早期快照不代替最后完成回执。部署成功和工程校验通过都不表示语义准确率达标。

实际云端准备使用 `code/cloud_prepare_benchmark_executed_v1.py`；稍后的 `code/cloud_prepare_benchmark.py` 新增保护标记小写匹配和 20 个 context 唯一性断言。两版本原字节及 SHA 都保留，不能把稍后版本冒称为此前实际执行源码。原始公共回执、公开去标识副本和字节相同代码的来源对应关系见 `PUBLIC_COPY_MANIFEST.json`。私有 selection IDs、逐条路径映射和原始模型输出不发布。

扫描器只允许已审读的固定保护线程 UUID 与公开操作路径假阳性使用豁免；每条必须同时匹配文件 SHA、规则、行号和 literal SHA，代码改变后自动失效。凭据、原始记录标识和正文/模型载荷规则不允许豁免。

## First actual benchmark result

The fixed run finished: 20 physical requests, 14 frozen-engineering passes, 6 preserved failures; 565.424 seconds; public-rate token estimate USD 0.0165363, not an invoice. It is not population-quality certification or 20 new accepted production records. The worker is stopped. See FINAL_SUMMARY_PUBLIC.json, FAILURE_DIAGNOSTIC_PUBLIC.json and RUN_LOG_ZH.md. Private evidence was archived to existing Azure Blob and its SHA read back. No historical result was overwritten.
