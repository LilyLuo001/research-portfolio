# E2 执行手册：分任务 Prompt + Agent 指派 + Meta 连续性审核

配套文件：《E2 研究计划：链上再抵押——RWA 内嵌杠杆的测量、机制与脆弱性》
版本：v1.0（模型与价格信息基于 2026 年 3–6 月公开资料，**下发任务前请复核各家最新定价与型号**，本领域每季度都在变）

---

## 第 0 部分：总架构与三条铁律（先读这个，再用任何 prompt）

### 0.1 路由哲学

任务分四类，各类的"最低成本可用模型"完全不同：

| 任务类型 | 质量瓶颈 | 省钱策略 |
|---|---|---|
| A. 联网事实核验 | 检索覆盖率 + 引用纪律 | 用带原生搜索的中低价模型，强制逐条给 URL |
| B. 数据工程/写代码 | 代码正确性（可用执行验证兜底） | 用最便宜的强代码模型，靠"跑通+对账"验收，不靠模型自觉 |
| C. 核心算法与计量设计 | 推理深度（错了不易被发现） | **不省钱**，用旗舰推理模型 + 第二家旗舰交叉复核 |
| D. 写作/红队/整理 | 语言与批判质量 | 旗舰写、异家旗舰审；机械整理用白菜价模型 |

### 0.2 三条铁律（写进每一个 prompt，也是你验收时的宪法）

1. **数字只能来自两个地方**：被执行过的代码的输出文件，或带 URL 的引用。任何模型在任何环节**不得凭记忆写出**合约地址、日期、TVL、利率、论文结论。凭记忆写数字 = 该产出整体作废。
2. **UNKNOWN 优于编造**：所有 prompt 内置"查不到/不确定就输出 `UNKNOWN` 并说明卡在哪"，并在验收标准里规定 UNKNOWN 不扣分、编造一票否决。
3. **交接靠文件契约，不靠对话记忆**：所有任务的输入输出都是带 schema 的文件（见 0.4 输出契约）。任何 agent 不得假设自己"记得"上一个 agent 说过什么——它只被允许读你贴给它的契约文件。

### 0.3 共享上下文包 C0（每个 prompt 开头都要粘贴）

以下文本为 C0，请原样置于每个任务 prompt 的最前面：

```
【项目上下文 C0 · v1.0】
本项目为金融学实证研究《链上再抵押：RWA 内嵌杠杆的测量、机制与脆弱性》的数据与分析工程。
研究对象：代币化真实世界资产(RWA)在 DeFi 借贷协议中的循环杠杆(looping)。
核心协议：Morpho Blue(隔离市场,单例合约,CreateMarket 事件定义市场,五参数:
collateralToken/loanToken/oracle/irm/lltv)、Aave Horizon(许可型 Aave V3 实例,
2025-08 上线)、Euler、Spark。
核心资产代码(仅为符号约定,地址一律以 registry.csv 为准,不得凭记忆填写地址):
sACRED, mF-ONE, AA_FalconXUSDC, syrupUSDC, USTB, USCC, JAAA, JTRSY, USYC,
VBILL, cUSDO, mTBILL。
关键定义:
- gross_v(t): 策略 v 在 t 日的链上 RWA 抵押品总额(USD, 按 oracle NAV 计)
- net_v(t): 外部净本金(未被循环放大的真实流入)
- λ_v(t) = gross/net(杠杆乘数); I(t) = 1 - net/gross(虚增率)
- 利差 s = y_RWA - r_borrow
- LLTV: 清算阈值; d* = 1 - u/ℓ (触发清算的 NAV 临界跌幅)
ID 约定:
- market_id: Morpho 官方 market id(bytes32)；Aave 市场用 "horizon:<asset symbol>"
- 事件单位: (asset, protocol, chain, market_id)
- 日期一律 UTC, ISO-8601; 金额单位一律 USD 并注明计价来源(oracle/NAV/发行方API)
文件契约:
- registry.csv: 资产与合约地址主表(唯一权威来源)
- events.parquet: 市场创建事件表
- flows.parquet: 逐笔 supply/withdraw/borrow/repay/liquidate
- panel_daily.parquet: 市场×日面板
- results/*.json: 一切统计数字的唯一合法出处
纪律:
1) 不得凭记忆输出任何地址、日期、数值; 未在输入中给出的事实一律标 UNKNOWN。
2) 你只知道本 prompt 中提供的信息与文件; 不要假设存在其他对话历史。
3) 输出严格遵守本任务规定的 schema; 多余的解释放在 notes 字段。
```

### 0.4 统一输出契约

每个任务交付物 = ①主产出文件（按任务 schema）＋②`manifest.md`，内含：输入文件清单及其行数/哈希、运行环境、已知局限、UNKNOWN 清单、下游任务需要注意的事项。manifest 是连续性的粘合剂，缺 manifest 视为未交付。

---

## 第 1 部分：任务分解、Agent 指派与完整 Prompt

> 指派表使用"主选（最低成本可用）→ 升级备选（主选验收失败时切换）"结构。价格量级引用 2026 年 3–6 月公开对比资料：DeepSeek V4 系（输出约 $0.87/M，最便宜档）、Kimi K2.6（缓存命中约 $0.07/M、2M 上下文）、GLM-5/5.1（输出约 $3.2/M，SWE 强，开源可自部署）、Qwen3.6 Max（输出约 $3.9/M）、Gemini 2.5 Flash/Flash-Lite（最便宜的 1M 上下文档）、Claude Sonnet 4.6（均衡旗舰）、Claude Opus 4.x / GPT-5.x / Gemini Pro 档（贵，只用于 C/D 类关键环节）。**用前复核现价。**

---

### T1｜M1 制度事实核验冲刺（对应计划 §10 未核实项）

- **类型**：A（联网核验）
- **主选 agent**：Kimi K2.6（联网检索 + 超长上下文读发行文件，缓存价极低）；发行方法律文件 PDF 精读部分可并行给 Gemini 2.5 Flash（1M 上下文最便宜）。
- **升级备选**：Gemini Pro 档 Deep Research（覆盖率最好）或 GPT-5 联网档。
- **不要用**：任何离线模型。此任务 100% 依赖检索。
- **验收**：抽查 20% 引用 URL 逐条人工点开核对；任何一条"有结论无 URL"退回。

**Prompt T1（三个子任务分三次下发，此为 T1a，T1b/T1c 同构改问题清单即可）**：

```
【粘贴 C0】
你的任务(T1a): 逐项核验以下制度事实, 只依据你联网检索到的一手来源
(协议官方文档、发行方法律文件、链上浏览器、官方博客), 二手媒体只可作线索不可作结论。

问题清单:
1. 下列 Morpho RWA 市场各自使用的 oracle 具体实现是什么(NAVLink/发行方直喂/
   硬编码/其他)? 逐市场回答: sACRED, mF-ONE, AA_FalconXUSDC, syrupUSDC, mTBILL, cUSDO。
2. 上述每个抵押资产的发行方赎回条款: 结算周期(T+N)、最低赎回额、是否存在
   赎回门槛(gate)条款、门槛触发条件。
3. Aave Horizon 各 reserve 的 NAVLink 喂价更新频率(每日/每工作日/其他)与
   周末是否更新。
4. Coinbase USDC 出借所路由的 Morpho 金库(curator、金库地址), 该金库当前
   与历史上是否配置过任何 RWA 抵押市场。

输出格式: Markdown 表格, 列 = [问题编号, 对象, 结论, 置信度(高/中/低),
一手来源URL(可多条), 检索日期, 备注]。
硬性规则:
- 每条结论必须有 ≥1 个一手 URL; 找不到一手来源→结论列写 UNKNOWN 并在备注
  写明你尝试过的检索路径。
- 禁止依据训练记忆作答; 禁止把"合理推断"写成结论, 推断必须显式标注"推断:"。
- 若来源之间冲突, 两个都列出, 不要自行裁决。
最后附一节"下游影响提示": 逐条说明哪个结论会改变研究设计(对照计划 §2.4/§10)。
```

---

### T2｜D1 事件与市场清单（Dune SQL + subgraph）

- **类型**：B（代码，产出可执行验证）
- **主选**：DeepSeek V4（写 SQL/GraphQL 极便宜且够用）；你在 Dune 上执行。
- **升级备选**：Claude Sonnet 4.6（若查询涉及 spellbook 表结构调试反复失败）。
- **验收**：查询结果行数与 Morpho 官方界面市场数对账（±0 容忍已过滤口径差异需书面解释）；抽 5 个 market_id 在链上浏览器人工复核。

**Prompt T2**：

```
【粘贴 C0】
你的任务(T2): 编写可直接在 Dune 上运行的 SQL, 以及 Morpho subgraph 的 GraphQL
查询, 构建 events.parquet 的原始数据。

交付四个查询:
Q1 Dune SQL: 从 morpho_blue 相关 spellbook 表提取全链所有 CreateMarket 事件,
   字段: chain, block_time, tx_hash, market_id, collateral_token, loan_token,
   oracle, irm, lltv。我会把我账号可见的表名与字段清单贴在本消息末尾——
   【重要】只允许使用我贴出的表名和字段, 不得虚构任何表名或列名;
   若你需要的字段不在清单里, 输出 NEED_INFO 并说明缺什么。
Q2 Dune SQL: Aave Horizon 部署实例的 reserve 初始化事件(我将贴出合约地址
   与 ABI 事件签名, 同样不得虚构)。
Q3 GraphQL: Morpho 官方 subgraph 拉取市场元数据作为 Q1 的交叉验证源。
Q4 SQL: 对 Q1 结果按 collateral_token 关联 registry.csv(我上传), 打标
   is_rwa 布尔列, 并输出未匹配代币清单供人工分类。

另交付: 一段 Python(pandas), 读入 Q1-Q4 导出的 CSV, 做三方对账
(Dune vs subgraph vs registry), 输出 events.parquet + 差异报告 diff_report.md。
规则: 代码必须可整体复制运行; 所有假设写在代码注释; 不确定的表结构一律
NEED_INFO, 禁止猜测。
[此处粘贴: 表名字段清单 / 合约地址 / registry.csv 样例前 20 行]
```

---

### T3｜D2 头寸流水与 call-trace 索引管道

- **类型**：B（重工程，多文件、需调试循环）
- **主选**：**Claude Code（Sonnet 4.6 档）**——这是全手册中唯一"agent 形态"优先于"单次问答"的任务：需要建 repo、跑 RPC、迭代调试。订阅制下边际成本可控。
- **低价备选**：GLM-5.1 Coding Plan 或 Qwen 系 coding agent（国内直付、便宜），质量近年已接近；若你无外币支付渠道用此选项。
- **验收**：对任意抽样的 3 个市场，管道输出的 supply/borrow 总量与 Dune 聚合值对账，误差 <0.5%；trace 解析对 10 笔人工标注的已知循环交易召回率 = 10/10。

**Prompt T3（作为 Claude Code / coding agent 的任务书）**：

```
【粘贴 C0】
任务(T3): 在本 repo 内实现链上索引管道, Python 3.11。
输入: events.parquet(市场清单), registry.csv, 我提供的 archive RPC 端点
(环境变量 RPC_URL, 有速率限制 QPS=25)。
实现模块:
1. fetch_logs.py: 按 market_id 拉取 Morpho 单例合约的 Supply/Withdraw/
   SupplyCollateral/WithdrawCollateral/Borrow/Repay/Liquidate 事件,
   增量写入 flows.parquet(schema 见 C0; 附加列: log_index, block_number)。
2. fetch_traces.py: 对 flows 中涉及的每笔交易拉取 debug_traceTransaction
   (callTracer), 仅保留与循环识别相关的子调用(borrow→swap/subscribe→
   supplyCollateral 链条), 压缩存 traces/ 分区。
3. reconcile.py: 逐市场把事件累计余额与合约 view 函数当前状态对账,
   输出 reconcile_report.md, 不达 99.5% 一致自动标红。
工程规则:
- 断点续传与幂等: 任何模块可从任意 block 重启不产生重复行。
- 全部 RPC 调用带重试与限速; 失败区块记入 failed_blocks.csv 而非静默跳过。
- 不得硬编码任何地址/ABI——只从 registry.csv 与 abis/ 目录读取;
  缺 ABI 时停止并输出 NEED_INFO 清单。
- 每个模块附 pytest 冒烟测试(用我提供的 3 笔样例交易 fixtures)。
完成定义: reconcile_report 全绿 + 冒烟测试通过 + manifest.md。
逐模块提交, 每次提交前自行运行测试; 不要一次性生成全部代码后宣布完成。
```

---

### T4｜D3 持有人重构、包装映射与跨链去重

- **类型**：B
- **主选**：DeepSeek V4（纯数据处理代码）；包装映射的守恒检查逻辑设计部分先让 Claude Sonnet 4.6 出 1 页方案再交 DeepSeek 实现（设计 200 行内很便宜，实现量大给白菜价模型）。
- **验收**：每资产 Σ(地址余额) 与合约 totalSupply 对账误差 = 0；Wormhole 跨链净额与发行方公布总供给核对（差异需在 manifest 解释）。

**Prompt T4**（同 T3 格式，任务改为：Transfer 全量→地址日度余额表 holders.parquet；ACRED↔sACRED 等包装对 mint/burn 守恒检验；Wormhole burn/mint 配对去重；输出 HHI/前十集中度日度序列。规则同：地址分类启发式的每条规则写成可配置 YAML，禁止写死在代码里——这是 §6 稳健性第 3 条的前置要求。）

---

### T5｜§4.1 分解算法：外部本金 vs 循环放大（论文技术核心）

- **类型**：C（**不省钱区**）
- **主选**：Claude Opus 档（推理+代码综合最强）**设计并实现参考版**；随后把同一任务书**独立**发给 GPT-5 思考档做**盲评复核**（不给它看 Opus 的答案，比对两者算法分歧点）；分歧仲裁由你 + 第三家（Gemini Pro 档或 DeepSeek 推理档，便宜）出具意见。
- **理由**：此处错误不可被"跑通"发现——代码能运行但分解口径错，全文数字皆错。唯一防线是异家旗舰的独立重做 + 上下界带（k 窗口敏感性）。
- **验收**：①两家旗舰的算法在 10 笔人工标注交易上的分类一致率 ≥9/10，分歧逐笔书面裁决；②λ 估计对 k∈{同交易,50,250,1800} 的带宽 < 均值 50%（否则触发计划 kill criterion #2）；③与 curator 公开披露的目标杠杆比对（T1 产出）。

**Prompt T5**：

```
【粘贴 C0】
任务(T5): 设计并实现"外部净本金 vs 循环放大"分解算法。这是全项目最高
风险模块, 请以最高推理强度工作。
输入: flows.parquet, traces/, holders.parquet, registry.csv(含发行方
一级申购合约地址), 10 笔人工标注的 ground-truth 交易(附标签)。
要求:
1. 先交付 2 页设计文档: 状态机定义(资金因果链的判定规则)、闪电型与
   迭代型循环的识别条件、边界情形清单(部分循环、跨市场循环、经 DEX 换币
   后再申购、金库代客操作)及各自处理决策与理由。
2. 设计文档经我确认后再写代码: decompose.py, 输出
   decomposition.parquet(粒度: 供给事件级, 列含 classification∈
   {external, loop_flash, loop_iter_k, ambiguous}, k 参数化)。
3. 对 ground-truth 10 笔逐笔给出你的分类与推理链。
4. 自我攻击一节: 列出你的算法最可能系统性错分的 3 类情形, 各给一个
   构造性反例与检测方法。
规则: ambiguous 是合法输出, 严禁为了指标好看而强行归类; 所有阈值
(金额容差、k 窗口)必须参数化并在配置文件中。
```

（发给第二家旗舰的复核 prompt = 同文，仅把第 3 条改为"给出你的独立设计后，再对附件中另一算法的设计文档做逐条批判"。）

---

### T6｜D4–D6 面板构建与 NAV 口径调和

- **类型**：B + 少量 A
- **主选**：代码 DeepSeek V4；各发行方 API 文档阅读与口径差异整理给 Gemini 2.5 Flash（长文档便宜）或 Kimi。
- **验收**：panel_daily.parquet 通过 15 条自动断言（无重复键、覆盖率、单位一致、rebasing 资产的 NAV 单调性检查等，断言清单随任务书给出）；NAV 口径调和表（rebasing vs 累积）经你人工签字。

---

### T7｜F1–F5 描述性事实与图表

- **类型**：B/D
- **主选**：Claude Sonnet 4.6（图表品味与"事实陈述贴数据"的纪律较好）；量大的重复出图改 Qwen3.6 或 GLM-5。
- **关键反幻觉条款（写入 prompt）**：图注与文字中的每一个数字必须由脚本从 results/*.json 读取生成（模板变量），**禁止任何手写数字**；交付物含出图脚本而不只是图。
- **验收**：随机抽 10 个正文数字回溯到 results 字段一一对上。

---

### T8｜H1 计量：面板回归、局部投影、少聚类推断

- **类型**：C（设计不省钱）+ B（实现可省钱）
- **设计与规格审查**：GPT-5 思考档或 Claude Opus 档——把计划 §5.2 全文贴入，要求输出：完整设定式、聚类/自助法选择的论证、货币政策冲击数据集选型（Bauer–Swanson 类）、预期威胁与安慰剂设计；**再交异家旗舰盲审一次**（同 T5 的双旗舰协议）。
- **实现**：DeepSeek V4 或 GLM-5 写 Python(linearmodels/statsmodels) + R(fixest) 双实现，**双语言结果互为复算**——这是比任何模型自检都硬的验收。
- **验收**：Python 与 R 点估计差异 <1e-6（同一样本同设定）；wild cluster bootstrap 用成熟包（boottest/fwildclusterboot），禁止模型手搓推断程序。

---

### T9｜§5.3 压力测试引擎

- **类型**：B（工程）+ C（情景校准）
- **主选**：Claude Code（多模块仿真工程，同 T3 理由）；情景参数校准（CLO/私募信贷历史 NAV 回撤）是 A 类检索任务，给 Kimi 并要求逐参数 URL。
- **验收**：引擎对样本内已发生的利用率触顶事件做"事后预测"复现（计划 §6 第 13 条），复现失败禁止出反事实结果。

---

### T10｜H4 oracle 事件研究

- **类型**：B。主选 DeepSeek V4（围绕 NAV 更新时间戳的事件研究是模板化代码）。设计已在计划 §5.3 写死，无需旗舰。

---

### T11｜双周文献占坑扫描（kill criterion #3 的执行者）

- **类型**：A（低价高频）
- **主选**：豆包或 DeepSeek 联网档（近零成本）；同时跑一个**不经 LLM** 的 Semantic Scholar/arXiv API 关键词脚本（T2 顺手让模型写好），LLM 只做命中结果的相关性初筛。
- **Prompt 要点**：固定关键词清单（"RWA looping / tokenized collateral rehypothecation / embedded leverage DeFi / NAV oracle liquidation"中英双语）；输出三栏表（命中文献、与本文重叠度 高/中/低、判断理由 + 摘要引文）；**规定"低重叠"必须给出理由而非默认值**，防止模型为省事全标低。

---

### T12｜论文写作（英文学术稿）

- **类型**：D
- **主选**：Claude Opus 档或 Claude 旗舰逐节写作（经济学论文文体最稳）；预算紧张时正文初稿 GLM-5/Qwen3.6 Max 写、旗舰重写引言与贡献段（引言值 80% 的审稿权重，只给旗舰）。
- **铁律条款（写入 prompt）**：正文所有实证数字用 `{{results.f1.gross_total}}` 式模板占位符，由脚本注入；文献引用只允许来自我提供的 `references.bib`，**bib 之外的引用一律禁止**（LLM 编造参考文献是本环节最高频事故）。

---

### T13｜红队/审稿人模拟

- **类型**：D
- **主选**：与 T12 写作者**不同家**的旗舰（Claude 写→GPT-5 审；反之亦然），外加 DeepSeek 推理档跑一轮低价"民间审稿"看是否捕到不同问题。
- **Prompt 要点**：角色 = JFQA/RFS 审稿人；要求产出 referee report 标准结构（Summary / Major / Minor / 建议裁决）；**规定至少 3 条 Major 且每条必须指向具体章节与可执行修改**，禁止空泛表扬；把计划 §7 的攻防预案表附上，要求审稿人专门攻击预案未覆盖的角度。

---

### T14｜Meta-QA 对账 agent（贯穿全程）

- **类型**：B（机械核对）
- **主选**：Gemini 2.5 Flash-Lite 或豆包（最便宜档即可，任务是执行清单不是思考）。
- **职责**：每个任务交付后，按下节"连续性矩阵"核对 manifest、schema、行数守恒、UNKNOWN 清单是否传递到下游任务书。它不判断学术质量，只判断契约合规。

---

## 第 2 部分：Meta 连续性审核

### 2.1 连续性矩阵（上游产出 → 下游消费，交接即查此表）

| 产出 | 生产者 | Schema 权威 | 消费者 | 交接检查点 |
|---|---|---|---|---|
| registry.csv | 你 + T1 | C0 | T2/T3/T4/T5 | 地址均有链上浏览器 URL 佐证；T1 的 UNKNOWN 项在 registry 标记 status=unverified |
| 制度事实表 | T1 | T1 prompt | T5(赎回条款进模拟)/T9/论文§2 | 每条进正文的事实必须"高置信+一手URL" |
| events.parquet | T2 | C0 | T3/T7 | 三方对账 diff_report 全绿 |
| flows/traces | T3 | C0 | T5/T10 | reconcile ≥99.5%；failed_blocks 传递给 T5 任务书 |
| holders.parquet | T4 | C0 | T5/T7 | totalSupply 对账=0 |
| decomposition.parquet | T5 | T5 设计文档 | T7/T8/T9 | 双旗舰一致率≥9/10；k 带宽达标 |
| panel_daily.parquet | T6 | C0 | T8/T10 | 15 条断言全过 |
| results/*.json | T7/T8/T9/T10 | 各任务 | T12 | 论文数字 100% 模板注入，零手写 |
| referee report | T13 | — | 你 | Major≥3 且可执行 |

### 2.2 全局反幻觉协议（为什么这套流程整体上防得住）

1. **数字与文字分离**：LLM 从头到尾不"说出"实证数字，只写"生产数字的代码"和"引用数字的模板"。幻觉只能发生在代码逻辑里，而代码逻辑有对账（T3/T4/T6）、双实现互算（T8）、双旗舰盲评（T5/T8 设计）、事后复现门槛（T9）四道闸。
2. **检索与结论分离**：A 类任务只允许"结论+一手 URL"成对出现，抽检 20%；训练记忆被 prompt 明令禁用。
3. **异家交叉**：所有 C 类任务强制两家旗舰独立完成后比对——同一家模型自我复核会共享同一盲区，异家盲评是当前对抗高阶推理错误的最便宜手段。
4. **UNKNOWN 的正激励**：每个 prompt 都声明 UNKNOWN 合法且不扣分，验收标准把"编造"列为一票否决——把模型的最优策略从"糊弄过验收"扭成"诚实报告"。
5. **上下文最小化**：每个 agent 只见 C0 + 本任务输入，不见全项目对话史。信息越少，越无从编造"看似记得"的内容；连续性由文件契约而非上下文承担。

### 2.3 各任务 prompt 连续性自查结果（我已逐条核过）

- C0 中的定义（λ、I、市场五参数、ID 约定）与研究计划 §2/§4 完全一致，且被 T2–T10 所有 prompt 通过粘贴 C0 继承——**术语单点维护**，改定义只改 C0 一处。
- T5 依赖的 ground-truth 标注交易在 T3 验收中先行产生（同一批 10 笔），无循环依赖。
- T1 的"下游影响提示"节显式桥接到 T5（赎回条款）与 T9（gate 情景）——制度事实到模型参数的链路不断。
- 已发现并修补的一个断点：T4 的地址分类规则若写死在代码里，§6 稳健性第 3 条无法执行——故 T4 prompt 强制 YAML 配置化。
- 残余风险（须由你人工把守，无法外包给任何 agent）：①registry.csv 初版地址录入——建议你逐条从链上浏览器复制，这 1 小时手工是全项目的地基；②T5 分歧仲裁——两旗舰意见相左时最终裁决必须是你；③各任务书里"[此处粘贴]"占位符必须真实填充后再下发，空占位符会诱发模型自行虚构输入。

### 2.4 成本量级估算（按 2026 年中价格，仅供排序用）

B 类全部走 DeepSeek/GLM/Qwen 档 + Claude Code 订阅：全项目预计 <$150 API 支出 + 1–2 个月 coding agent 订阅。C/D 类旗舰调用集中在 T5/T8 设计与 T12/T13：单次长任务 $5–30 量级、总计 <$200。**整个 E2 的 LLM 总成本上限约 $400–500**，相对于其防错结构（双实现、双旗舰、四道对账闸）是极高杠杆的支出；请勿在 T5/T8/T13 上省这 $150——那是全文对错的分界线。
