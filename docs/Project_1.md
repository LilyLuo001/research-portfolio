# 基金转换研究计划 · 多 Agent 执行手册(Prompt Playbook v1.0)

> 模型选型基于 2026 年 7 月市场格局,**每季度复核一次**。所有价格层级为相对值(旗舰 / 主力 / 廉价),同层级模型可互换,替换规则见 §2。

---

## §1 总架构:五条不可违反的元规则

任何 prompt、任何 agent、任何时候,以下五条优先于具体任务指令。每个 prompt 头部都必须粘贴(见 §3 公共上下文包)。

**R1|LLM 不是事实来源。** 所有数据事实(日期、AUM、持仓、系数)只能来自两种途径:(a) agent 写的代码在真实数据上执行的输出;(b) 附带原始文件定位符(EDGAR accession number + URL、WRDS 表名 + 查询语句)的抽取。凡是 agent"凭记忆"给出的数字,一律视为幻觉,直接丢弃。

**R2|双通道交叉验证。** 高幻觉风险任务(事件清单、文献引用、计量规格)必须由**两个不同厂商**的模型独立完成,机器 diff,分歧交第三个模型仲裁 + 人工裁决。同厂商不同型号不算独立通道。

**R3|Schema 契约。** 任务之间只通过文件交接,不通过对话交接。每个任务的输出文件名、列名、数据类型、单位在本手册 §5 固定,下游 prompt 引用同一 schema。任何 agent 不得擅自改列名。

**R4|不知道就停。** 每个 prompt 内置升级条件("遇到 X 情况,停止并输出 NEED_HUMAN + 原因"),禁止 agent 在信息不足时猜测补全。宁可停,不可编。

**R5|贵模型把关,便宜模型跑量。** 规格设计、计量审计、红队用旗舰;模板化批量、抽取、绘图用廉价档。警惕反向陷阱:廉价模型反复失败重试的总成本可能高于旗舰一次做对——任何任务连续失败 2 次,自动升级一档。

---

## §2 模型选型总表(2026-07)

| 档位 | 海外 | 国产 | 单位成本 | 用于 |
|---|---|---|---|---|
| **旗舰推理** | Claude Fable 5 / Opus 4.8;GPT-5.5 Pro/Thinking;Gemini 3.1 Pro | Qwen3.7 Max;DeepSeek V4 Pro-Thinking | 高 | 计量规格设计、代码审计、红队、英文论文正文 |
| **主力均衡** | Claude Sonnet 4.6(Claude Code 内);Gemini 3.5 Flash | DeepSeek V4 Pro;GLM-5.1;Kimi K2.6 | 中(约旗舰 1/5–1/20) | 数据管道实现、复现、事件研究图 |
| **廉价批量** | Haiku 4.5;Gemini Flash 低配 | DeepSeek V4 Flash;Qwen3.7 Plus/Flash;Kimi K2.x(长文档) | 极低(可低至旗舰 1/100 量级) | EDGAR 文件抽取、批量稳健性、单元测试、绘图、格式化 |
| **Deep Research** | Gemini / GPT / Claude 的深度研究模式 | Kimi 探索版 | 按次 | 文献综述、撞车监控 |

**分工逻辑(不是跑分,是失败模式)**:
- **代码 agent 主力 = Claude Code(Sonnet 4.6)**:终端原生 agent,长任务自主性和"报错就修"闭环最成熟;卡在复杂计量时切 Opus 4.8/Fable 5。
- **海量文件抽取 = Kimi K2.6 + Gemini 3.5 Flash 双通道**:超长上下文 + 便宜,497 文件一次整读;两家独立抽,满足 R2。
- **批量代码/测试 = DeepSeek V4**:接近一线的代码能力、成本约为 Claude 旗舰的百分位级,是稳健性流水线的最优解;注意其 agent 长链自主性弱于 Claude Code,只给它**模板明确的单文件任务**。
- **中文材料 = Qwen3.7 Max**:开题报告、答辩、导师沟通稿的原生中文语感。
- **红队 = 与写作者不同厂商**:论文用 Claude 写,红队必须用 GPT-5.5 Pro + Gemini 3.1 Pro(避免同族模型的盲区重叠)。
- **不用于本项目**:任何模型的"凭知识回答金融数据"模式;Agent benchmark 高分但工具调用不稳的型号不进数据管道关键路径。

**替换规则**:同档位内可替换;跨档只许升不许降;每季度用固定的 3 个探针任务(一个 EDGAR 抽取、一个 DiD 代码、一个红队)重测本表。

---

## §3 公共上下文包(每个 prompt 头部原样粘贴)

```
[CONTEXT PACK v1.0 — 基金转换研究项目]
你是本项目多 agent 流水线中的一个执行单元。附件《基金转换实验_博士研究计划.md》是唯一的项目真相源(single source of truth),你的任务定义若与它冲突,以它为准并报告冲突。

术语表:
- 转换(conversion):共同基金整体改组为 ETF,委托关系不变,外壳改变。
- ConvExp_i,e:股票 i 在事件波次 e 的处理强度 = 转换基金转换前持仓股数 / 流通股数。
- 波次(wave):同一生效日的一组转换,DFA 2021-06-11 为锚波次。
- 脊柱一/二/三/四:系统性盈余纳入 / 收益指纹 / 剂量机制 / 成本侧(定义见计划 §7)。

硬性规则(违反任何一条 = 任务失败):
1. 不得凭记忆给出任何日期、金额、持仓、引文页码;一切事实须附来源定位符或来自代码执行输出。
2. 输出文件严格遵守指定 schema,不增删改列名。
3. 信息不足时输出 NEED_HUMAN: <原因>,禁止猜测。
4. 引用学术文献只允许引用我提供的文献包内条目;需要新文献时输出 CITE_REQUEST: <描述>,由人工检索后补给你。
5. 每次输出末尾附自检清单(逐条 PASS/FAIL)。
```

---

## §4 执行 Prompt(T0–T12)

### T0|文献综述与撞车监控 —— Deep Research 档(Gemini 或 GPT 深度研究模式;月度监控用 Kimi 免费档)

```
[粘贴 CONTEXT PACK]
任务:两阶段文献工作。
阶段 A(一次性):围绕以下四条文献带做系统综述,输出结构化文献矩阵(CSV:作者|年份|期刊/状态|数据|识别|结果变量|与本文边界):
  1) ETF 与价格效率(GNZ 2021 MS;Israeli-Lee-Sridharan 2017 RAST;Ben-David-Franzoni-Moussawi 2018 JF;Bhojraj 系列)
  2) 共同基金转 ETF(Saglam-Tuzun 2025 FEDS Note 及其可能的完整版;税收/资金流文献)
  3) staggered DiD 计量(Callaway-Sant'Anna;Sun-Abraham;stacked 设计;少聚簇推断)
  4) 盈余信息纳入度量(FERC;IPT;PEAD;price delay)
阶段 B(每月执行):在 SSRN/NBER/arXiv q-fin 检索关键词 [mutual fund ETF conversion; wrapper; earnings information; price discovery],报告新增工作论文,重点标记 Saglam/Tuzun/Wermers 的任何新版本。发现主题重叠 ≥ 60% 的论文时输出 ALERT。
禁止:编造不存在的论文;每条文献必须附可点击链接,链接打不开的条目删除。
自检:所有链接可达?矩阵无空列?与计划 §1 边界表逐条对齐?
```

### T1|转换事件清单采集 —— 双通道:Kimi K2.6(通道甲)+ Gemini 3.5 Flash(通道乙);仲裁:Claude Sonnet 4.6

```
[粘贴 CONTEXT PACK]
任务:从我提供的 EDGAR 文件包(497/497K/N-14/N-8 补充文件,PDF/HTML 原文)中抽取共同基金转 ETF 事件,构建事件主表。
输入:文件目录 /edgar_filings/,每个文件已命名为 <CIK>_<accession>.htm
输出 schema(events_raw_通道X.csv):
  fund_name | family | mutual_fund_ticker | etf_ticker | announce_date | effective_date | asset_class(equity_US/equity_intl/fixed_income/other) | AUM_at_conversion_USD | source_accession | source_url | confidence(H/M/L)
规则:
- 每一行的每个字段必须能在 source_accession 对应文件中找到原文依据;抽不到的字段填 NA,不许推断。
- announce_date = 该文件首次披露转换意向的日期;effective_date = 文件声明的转换生效日;两者缺一按 NA 处理并降 confidence。
- 你只处理文件包内的文件。不得用你的记忆补充"你知道的"其他转换事件——那是下一批文件的事。
升级条件:同一基金出现互相矛盾的日期 → NEED_HUMAN 并列出两处原文。
自检:行数 = 文件包中含转换语言的文件数?所有 accession 真实存在于输入目录?无凭记忆行?
```

**仲裁 prompt(Sonnet 4.6)**:输入两份 events_raw,机器 diff 后仅对分歧行工作:逐行回到原文判定,输出 events_merged.csv + 分歧裁决日志。人工抽查:confidence=H 抽 10%,M/L 全查。

### T2|持仓管道与 ConvExp 构造 —— Claude Code(Sonnet 4.6)

```
[粘贴 CONTEXT PACK]
任务:在 WRDS 云端(Python + wrds 包)建立持仓管道。
输入:events_merged.csv(schema 见 T1);WRDS 凭证由我在环境变量注入。
步骤:
1. 用 CRSP MF(crsp.holdings / crsp.portnomap)与 EDGAR N-PORT 把每只转换基金映射到转换前最后一个报告期的股票持仓(CUSIP→PERMNO 用 crsp.stocknames,按报告期对齐)。
2. 计算 ConvExp_i,e = Σ_f 持仓股数 / CRSP 流通股数(shrout,千股,注意单位×1000)。
3. 输出 conv_exposure.parquet:permno | wave_id | effective_date | conv_exp | n_funds | mcap_decile | pre_etf_ownership
4. 输出诊断报告:ConvExp 分布直方图、≥0.5% 与 ≥1% 的股票数(按波次)、DFA 波次占比 —— 这是 kill-switch 第 2 关的直接输入。
规则:所有中间表落盘;每一步写 assert(行数、重复键、单位合理性);N-PORT 与 CRSP MF 持仓差异 >10% 的基金单独列出 NEED_HUMAN。
禁止:对缺失持仓期做任何插值。
```

### T3|结果变量规格书 —— 旗舰(Claude Fable 5 或 GPT-5.5 Thinking);实现 —— Claude Code;单元测试生成 —— DeepSeek V4

```
[粘贴 CONTEXT PACK]
任务(规格阶段,旗舰):为计划 §7 的四条脊柱写《变量构造规格书》,精确到可直接编码:
- 脊柱一:GNZ 式系统性/特质盈余分解(给出分解回归的确切方程、估计窗口、样本过滤)、FERC 规格、IPT 定义、Hou-Moskowitz delay。
- 脊柱二:事件定义(自身公告 vs 篮子 peer 公告)、CAR 计算基准(特征调整)、[0,+120] 路径、永久/回吐分解公式、反转策略构造。
- 脊柱四:TAQ 有效价差(WRDS IID 表)、Amihud、1−R²。
每个变量给:数学定义 | 数据表与字段 | 已知文献口径出处(仅限文献包)| 边界情形处理 | 合理值域(供 assert)。
规则:凡文献包中口径有分歧处(如 SUE 用分析师预期 vs 时序模型),列出选项并给推荐 + 理由,标记 DECISION_NEEDED 交人工拍板,不得自行默认。
实现阶段(Claude Code):严格按规格书编码,产出 outcomes_panel.parquet(permno|yyyyq|各变量),每个变量跑值域 assert。
测试阶段(DeepSeek V4):对每个变量构造函数生成单元测试(合成小样本,手算预期值),不看实现细节、只看规格书——测试与实现独立,防止实现错误自我确认。
```

### T4|Saglam–Tuzun 复现 —— Claude Code(Sonnet 4.6)

```
[粘贴 CONTEXT PACK]
任务:复现 Saglam-Tuzun (2025 FEDS Note) 的核心表:2021-06 转换波次 → 股票波动率与有效价差的 DiD。目的不是创新,是校准数据管道(kill-switch 第 3 关)。
输入:conv_exposure.parquet + CRSP 日频 + TAQ IID;Note 原文 PDF(我提供)。
输出:replication_report.md,并排列出:他们的系数(从 PDF 表格抄录,附页码)vs 我们的系数;方向一致 + 量级在 2 倍以内 = PASS。
规则:抄录原文数字时逐个附页码;复现失败时输出差异诊断(样本量、变量定义、窗口)而非调参硬凑。禁止为了"复现成功"而搜索规格(specification searching)——如实报告第一次按规格书跑出的结果。
```

### T5|主识别实现 —— 规格:旗舰双通道(Claude Fable 5 通道甲 + GPT-5.5 Pro 通道乙);实现:Claude Code;代码审计:Gemini 3.1 Pro

```
[粘贴 CONTEXT PACK]
任务(规格,两旗舰独立完成后 diff):把计划 §6 的主规格翻译成估计蓝图:
- stacked DiD 的 clean control 构造规则(逐波次事件窗、禁止 already-treated、权重);
- Callaway-Sant'Anna 与 Sun-Abraham 在连续处理强度下的适配方案(明确说明各自的原假设差异);
- 三套推断的确切实现:双向聚类的维度、wild cluster bootstrap 的 null 施加方式、随机化推断的置换单元(转换日重排 vs 基金替换)与置换次数;
- 事件研究图规格(t=0 定义、bin、置信带)。
两通道 diff 后的分歧点 = 计量上最危险的点,全部 NEED_HUMAN(带双方论证)交人工/导师裁决。
任务(实现,Claude Code):按裁决后的蓝图编码;每个估计量单独模块;随机数种子固定;输出 main_results/ 下的系数表 + 事件研究图数据。
任务(审计,Gemini 3.1 Pro):只读代码与蓝图,不看结果,逐行核对实现与蓝图一致性,输出审计清单。发现"结果驱动的代码分支"(if 显著则…)一律标红。
```

### T6|收益指纹分析 —— Claude Code(Sonnet 4.6;分解公式部分升 Opus 4.8)

```
[粘贴 CONTEXT PACK]
任务:实现脊柱二。输入 outcomes_panel + conv_exposure + T5 的估计框架。
输出:(a) 处理−对照 CAR 楔形图数据([0,+120] 每日点估计 + bootstrap 带,自身公告与 peer 公告分开);(b) 永久/回吐分解表;(c) 反转策略月度收益时序。
规则:楔形图必须先出图后解读——你不得在图生成前对 H2a/H2b 表态;解读段落里每个论断对应图上可指认的特征。图数据落盘为 fingerprint_*.csv 供 T9 写作引用,写作 agent 只准引用这些落盘数字。
```

### T7|稳健性批量 —— DeepSeek V4(主)/ Qwen3.7 Plus(备)

```
[粘贴 CONTEXT PACK]
任务:按计划 §8 清单执行稳健性矩阵。我提供:主规格代码(T5 产物,只读)+ 稳健性配置表 robustness_grid.csv(每行 = 一个变体:样本过滤|估计量|聚类方式|强度定义)。
你的工作是模板化的:对每一行,复制主规格、只改配置指定的维度、运行、把系数/SE/N 写回 robustness_results.csv 对应行。
禁止:改动配置表未指定的任何代码;对任何结果做解读;跳过报错的行(报错行填 ERROR + traceback 摘要)。
自检:results 行数 = grid 行数?每行只有指定维度与主规格不同(自动 diff 证明)?
```

### T8|图表制作 —— DeepSeek V4 Flash 或 Haiku 4.5

```
[粘贴 CONTEXT PACK]
任务:把 main_results/、fingerprint_*.csv、robustness_results.csv 渲染为期刊级图表(matplotlib,黑白友好,JF/RFS 版式惯例)。数字只从落盘文件读取,图注中的每个数字用代码引用生成,禁止手打。输出 figures/ + tables/(LaTeX booktabs)。
```

### T9|英文论文写作 —— Claude Fable 5 或 Opus 4.8(正文);GPT-5.5(独立润色过一遍)

```
[粘贴 CONTEXT PACK]
任务:按计划的论文结构写英文初稿,分节交付(Intro → 制度背景 → 假设 → 数据 → 识别 → 结果 → 稳健性 → 结论),每节一个独立会话,输入 = 计划相应章节 + 该节涉及的落盘结果文件 + 文献矩阵(T0)。
规则:
- 文中每个数字必须能在落盘文件中找到,交付时附"数字→文件:单元格"对照表;
- 引文只从 T0 文献矩阵取,格式 (Author Year),需要新引文输出 CITE_REQUEST;
- Intro 的贡献段严格对齐计划 §1 的三层贡献与边界表,不得擅自加"首次""填补空白"类不可证声明;
- 预注册纪律:结果节如实报告 T5–T7 落盘数字,包括不显著结果,禁止选择性叙述。
```

### T10|Referee 红队 —— GPT-5.5 Pro(裁判甲)+ Gemini 3.1 Pro(裁判乙),各自独立,禁止使用 Claude

```
[粘贴 CONTEXT PACK]
任务:你是 JF/JFE/RFS 最挑剔的 referee。输入 = 完整论文稿 + 主要图表。不复述、不客套,输出标准审稿报告:致命伤(major)按可拒稿程度排序,每条附"作者最可能的辩护 + 该辩护为何不够"。特别攻击:DFA 单家族依赖、2021-06 并发事件、披露混淆、少聚簇推断、estimand 与结论措辞是否匹配。
两位裁判报告合并后,由写作模型(Claude)逐条起草回应并修改稿件;第二轮红队换新会话冷启动(不给第一轮报告,防止锚定)。
```

### T11|中文材料 —— Qwen3.7 Max

```
[粘贴 CONTEXT PACK]
任务:基于英文稿与计划文档,产出开题报告、预答辩幻灯片文字稿、给导师的进度纪要。术语中英对照沿用计划文档;数字规则同 T9(只引落盘文件)。
```

### T12|流水线元协调(Orchestrator)—— 固定用一个旗舰(建议 Claude Fable 5),全程同一项目上下文

```
[粘贴 CONTEXT PACK + 本手册全文]
任务:你是流水线总控。每个任务交付时,你执行四项检查并出具放行/退回意见:
1. Schema 合规(§5 契约逐列核对);
2. 来源合规(抽查 5 个事实,回溯定位符);
3. 连续性(该输出是否满足所有下游任务的输入声明);
4. 红线(是否出现凭记忆数字、规格搜索、选择性报告的痕迹)。
你不做任何实质分析,只做守门。放行日志追加到 pipeline_log.md。
```

---

## §5 接口契约与连续性矩阵(Meta 审核核心)

**文件契约**(列名一经冻结,改动需人工签字):

| 文件 | 生产者 | 消费者 | 关键列 |
|---|---|---|---|
| events_merged.csv | T1 | T2, T0-监控 | fund_name, effective_date, asset_class, source_accession |
| conv_exposure.parquet | T2 | T4, T5, T6, T7 | permno, wave_id, conv_exp, effective_date |
| 变量规格书.md | T3 | T3-实现, T5, T9 | — |
| outcomes_panel.parquet | T3 | T5, T6, T7 | permno, yyyyq, 脊柱变量 |
| main_results/ | T5 | T6, T7, T8, T9 | 估计量×系数×SE×N |
| fingerprint_*.csv | T6 | T8, T9 | 日 × CAR × 置信带 |
| robustness_results.csv | T7 | T8, T9, T10 | grid_id × 系数 |
| 论文稿 + 数字对照表 | T9 | T10, T11 | — |

**连续性自查(我已做的 meta 审核结论)**:
1. 每个下游输入都有唯一上游生产者;无孤儿输入。T5 需要的"波次 clean control 窗口"依赖 T1 的 effective_date 唯一性——已在 T1 仲裁 prompt 中加入重复键检查。
2. 幻觉最高危的三个环节及其闸门:T1(事实抽取)→ 双通道 + 定位符 + 人工抽查;T3(计量口径)→ DECISION_NEEDED 强制人工拍板;T9(写作引数字)→ 数字对照表 + T12 抽查回溯。
3. 独立性保障:测试(DeepSeek)不看实现(Claude);红队(GPT/Gemini)不与写作(Claude)同族;两通道抽取跨厂商。全流水线没有任何一个结论只经过单一模型族。
4. 已知残余风险:(a) T5 两旗舰规格 diff 若双方都错在同处(同源训练数据的系统性盲区),闸门失效——缓解:计量蓝图关键裁决必须过导师;(b) T7 廉价模型的静默数值错误——缓解:robustness grid 中埋 2 行"已知答案"哨兵配置(与主规格完全相同的行),结果不等于主规格系数即整批作废。

**人工必到场的六个门**:T1 抽查、T2 的 kill-switch 数字、T3 的 DECISION_NEEDED、T5 的规格分歧裁决、T9 的数字对照表签收、每轮 T10 后的修改方案。

---

## §6 成本与节奏(粗算,量级参考)

- 大头是 T5–T7 的代码 agent 会话(主力档)与 T9/T10 的旗舰会话;T1 抽取用廉价档,几百份 filing 的成本可忽略。
- 经验法则:整个第一章流水线的 API/订阅成本相对博士生时间成本是零头;**不要为省旗舰的钱让廉价模型碰规格设计和红队**——那两处的错误以月为单位烧你的时间。
- 与计划 §9 六周 kill-switch 对齐:T0/T1/T2 并行于第 1–3 周,T4 第 3–4 周,T3 规格书与 kill-switch 判定并行于第 4–6 周。
