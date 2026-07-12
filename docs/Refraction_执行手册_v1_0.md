# Refraction 执行手册 v1.0：R0–R14 全任务 Prompt + Agent 指派 + Meta 连续性审核

配套文件：《One Shock, Many Prices: ETF Baskets and the Refraction of Macroeconomic News》研究计划 v2.1（简称"计划"）。
版本：v1.0（模型与价格信息沿用 E2 执行手册 v1.1 的 2026 年 3–6 月复核结论，**下发前请复核最新定价与型号**）。
与 E2 手册的关系：总架构、三条铁律、输出契约、附录 A 的能力复核结论全部继承（含两处修正：DeepSeek API 无原生联网、豆包仅限机械核对）；本手册只写 Refraction 特有的内容。

---

## 第 0 部分：总架构（先读，再用任何 prompt）

### 0.1 任务分型与路由（继承 E2 0.1，不重复论证）

A 联网核验 → 带原生搜索的中低价模型 + 逐条 URL；B 数据工程/代码 → 最便宜强代码模型 + "跑通+对账"验收；C 核心计量/算法设计 → **不省钱**，双旗舰异家盲评；D 写作/红队 → 旗舰写、异家旗舰审，机械整理白菜价。

### 0.2 三条铁律（继承 E2 0.2，每个 prompt 都粘）

1. 数字只能来自被执行过的代码的输出文件，或带 URL 的引用；凭记忆写数字 = 产出作废。
2. UNKNOWN 优于编造；UNKNOWN 不扣分，编造一票否决。
3. 交接靠文件契约，不靠对话记忆；agent 只读贴给它的契约文件。

**本项目追加两条项目级铁律：**

4. **禁止前视（lookahead ban）**：β 估计窗、特征先验、L 杠杆、篮子权重一律只用该 wave 转换生效日之前的数据；任何模块的输入若含 post 时段数据，必须在 manifest 声明用途并证明不进入 pre 量的构造。违反 = 作废。
5. **预注册先于结果（prereg-before-outcomes）**：R6 及之后一切在 post 时段结果变量上的估计，必须在 R4 的 OSF 时间戳之后运行；Gate-0 诊断（R3）只允许触碰 pre 时段与功效模拟。执行顺序由队列 GATE 强制，不靠自觉。

### 0.3 共享上下文包 C0-R（每个 prompt 开头原样粘贴）

```
【项目上下文 C0-R · v1.0】
本项目为金融学实证研究《One Shock, Many Prices: ETF 篮子对宏观新闻的折射》
的数据与分析工程。研究问题: 共同基金→ETF 转换(wrapper 变化、持仓与管理人
不变)是否使成分股对预定宏观公告(FOMC/CPI/就业)的反应向篮子反应倾斜, 以及
倾斜成分是信息还是噪音。
识别: 转换自然实验(沿用 P1 项目冻结资产), 公告内截面识别。

关键定义:
- ConvExp_{i,e}: wave e 中转换基金对股票 i 的持股占比(冻结文件 conv_exposure.parquet)
- S_a: 公告 a 的标准化 surprise(FOMC 来自 SF Fed USMPD; CPI/NFP 为 实际-共识)
- beta_i: 公告体制 beta——只用 pre 时段公告日, r_i 对 S_a 回归, Vasicek 收缩
  向特征隐含先验; 收缩权重 w_shrink 是全局配置项, 只能从 frozen_config.yaml 读取
- beta_b_loo(i): 转换基金组合的留一篮子公告反应(权重=pre 时段持仓权重)
- 杠杆分解: L_i = beta_b_loo - beta_i = L_mkt + L_tilt, 其中 L_mkt = 1 - beta_i,
  L_tilt = beta_b_loo - 1; 另有篮子因子倾斜反应 F_tilt(篮子公告日收益对市场
  正交化后的 S_a 敏感度)
- 主设定式(编号 SPEC-MAIN, 低阶项 b3/b4 为必需项, 缺失即 SPEC_ISSUE):
  r_{i,a} = b1*(beta_i*S_a) + b2*(Post*ConvExp)*(beta_i*S_a)
          + b3*Post*(beta_i*S_a) + b4*Post*(L_i*S_a)
          + gamma*(Post*ConvExp)*(L_i*S_a) + lambda_a + delta_{ind×a} + alpha_i + 控制
  gamma 一律分解报告: gamma_mkt / gamma_tilt / gamma_fac; 合并 gamma 只是汇总行
- 楔子: W_{i,a} = gamma_hat*Post*ConvExp*L_i*S_a; 指纹三腿 = 反转路径
  {+1d,+5d,+20d,+60d} ∧ 纪律(H3) ∧ 基本面锚定(W 预测下季 SUE/分析师修正)
ID 约定:
- 股票 = CRSP permno; 公告 a = (type ∈ {FOMC,CPI,NFP}, date_ET); wave e 见
  events_merged.csv; 日期存储 UTC、公告时刻按 ET 标注(FOMC 14:00, CPI/NFP 08:30)
文件契约:
- 冻结输入(P1 产出, 只读): events_merged.csv, conv_exposure.parquet,
  holdings_weights.parquet, ibes_sue.parquet(P1-T3)
- 本项目产出: macro_calendar.csv, surprises.parquet, betas.parquet,
  panel_ann.parquet(粒度 permno×announcement), gate_report.md,
  frozen_config.yaml, results/*.json(一切统计数字唯一合法出处)
纪律:
1) 不得凭记忆输出任何日期、数值、数据库表名/变量名、文献结论; 未在输入中
   给出的一律 UNKNOWN。
2) 你只知道本 prompt 提供的信息与文件; 不假设其他对话历史存在。
3) beta/杠杆/权重的一切构造禁止使用 wave 生效日之后的数据(前视禁令)。
4) 输出严格遵守任务 schema; 多余解释放 notes。
```

### 0.4 统一输出契约（继承 E2 0.4）

交付物 = 主产出文件 + `manifest.md`（输入清单+行数/哈希、环境、局限、UNKNOWN 清单、下游注意事项）。缺 manifest 视为未交付。

### 0.5 队列与两道人工 GATE

```
R0→R1→R2→R3 ──GATE-PREREG(人工: 审 gate_report, 冻结配置, 提交 OSF)──→ R4
R4 ──GATE-E2-VERDICT(人工: E2 批复到达, 无论结果)──→ R5→R6→R7→R8→R11→R12
R9(创建篮子)/R10(TAQ 试点): 非阻塞旁路, 随时可启, 失败不影响主线
R13(碰撞监测)/R14(Meta-QA): 常驻, 自 R0 起运行
```
R0–R3 立即执行至 standby（计划 §11）；R3 的任何核心线失败 → 直接进计划 §10 退出矩阵，不强推。

---

## 第 1 部分：任务分解、Agent 指派与完整 Prompt

> 指派沿用 E2 附录 A 复核结论：Kimi K2.6（API 原生 `$web_search`）承担联网核验；DeepSeek V4 承担模板化代码（**不承担任何联网任务**）；Claude Code 承担多文件工程；GPT-5 思考档 × Claude Opus 档承担 C 类双旗舰；Gemini 2.5 Flash 承担长文档抽取；豆包/Gemini Flash-Lite 仅机械核对。用前复核现价。

---

### R0｜Channel-B 碰撞扫描 + Marta–Riva 优先核验 + repo 契约落地

- **类型**：A + 机械。**主选**：Kimi K2.6；高价值项（Marta–Riva、Brogaard–Heath–Huang）用 Gemini grounding 复跑求并集（E2 T1 兜底模式）。repo 落地部分是 30 分钟人工 + 一次 Sonnet 短调用生成目录骨架。
- **验收**：计划附录 A 全部 `[VERIFY-CHANNEL-B]` 条目获得 存在性+发表状态+URL 三元组或 UNKNOWN；Marta–Riva 单列一节；抽 20% URL 人工点开。
- **为何在 R0**：计划 §11 明确 Marta–Riva 的核验先于 positioning 定稿，不是先于投稿。

**Prompt R0（发 Kimi，开 `$web_search`）**：

```
【粘贴 C0-R】
任务(R0): 逐条核验以下文献条目的 ①存在性 ②当前发表状态(WP/在审/已发表,
期刊卷期) ③可用 URL ④摘要与本项目研究问题的重叠度(高/中/低+引用式理由≤25词):
[粘贴计划附录 A 的 VERIFY-CHANNEL-B 清单全文]
特别任务(单列一节, 最高优先): Marta & Riva "Do ETFs Increase the Comovements
of Their Underlying Assets? Evidence from a Switch in ETF Replication Technique"
—— 检索其最新版本: 是否已发表/更名/扩展? 其结果窗口是否已扩展到
"条件于公告/事件"的设定? 是否引入任何股票级带符号杠杆? 逐项给 URL。
再执行三个碰撞检索(近 24 个月): ①mutual fund ETF conversion comovement
②ETF basket macro announcement cross-section ③passive ownership announcement
day beta pricing。命中疑似占坑文献逐篇输出 [标题, 作者, 状态, 与计划哪个
假说编号撞车, 引用式理由, URL]。
硬性规则: 无一手 URL → UNKNOWN + 已尝试检索路径; 禁止凭记忆补书目字段;
来源冲突两个都列。
末尾输出"positioning 影响评估": 哪些发现要求修改计划 §1 边界表或 §10。
```

---

### R1｜宏观日历与 surprise 序列（计划任务 M1，双通道）

- **类型**：A（口径核验）+ B（解析代码）。**主选**：R1a 核验 → Kimi；R1b 解析 → DeepSeek V4。
- **不要做**：让任何模型凭记忆报 USMPD 的文件结构、变量名、覆盖区间——一律先下载后核验。
- **验收**：2017-01–2026-06 全部预定 FOMC/CPI/NFP 覆盖率 ≥95%（Gate-0 第 1 行）；FOMC surprise 与 USMPD 官方说明文档逐变量对得上；CPI/NFP 共识源为 `NEED_HUMAN`（你去 BU 确认 Bloomberg ECO 或 WRDS 替代），确认前 FOMC-only 不阻塞。

**Prompt R1a（发 Kimi）**：

```
【粘贴 C0-R】
任务(R1a): 只依据联网检索到的一手来源(SF Fed 官网、BLS/BEA/Fed 官方日历页),
核验并登记:
1. SF Fed US Monetary Policy Event-Study Database(USMPD)当前版本: 下载地址、
   文件格式、更新至何时、官方文档对各 surprise 变量的定义(逐字引用≤25词+页码/
   URL)、是否区分 statement 与 press conference 窗口、非预定会议如何标记。
2. 2017–2026 年 FOMC 预定会议日历、CPI 与就业报告(Employment Situation)
   发布日历的官方来源页(逐年 URL); 发布时刻的官方说明(ET)。
3. CPI/NFP 市场共识数据的可得渠道清单(Bloomberg ECO 字段、WRDS 内可能的
   替代库), 每个渠道注明: 覆盖起点、许可类型、UNKNOWN 项。
输出: 三张登记表, 列含 [事实, 结论, 一手URL, 检索日期, 置信度, UNKNOWN]。
规则同铁律: 禁止记忆作答; 该数据库结构你训练时的印象一律作废, 以本次
检索为准。末尾"下游影响提示": 哪条结论影响 R1b 解析器与 Gate-0 第 1 行。
```

**Prompt R1b（发 DeepSeek，附 R1a 定稿 + 你下载的原始文件前 20 行）**：

```
【粘贴 C0-R】
任务(R1b): 按附件(R1a 登记表 + 我贴出的 USMPD 原始文件列名与前 20 行 +
日历 CSV 样例)实现 build_calendar.py 与 build_surprises.py, 输出
macro_calendar.csv 与 surprises.parquet(列: type, date_ET, time_ET,
S_raw, S_std, source, is_scheduled)。
规则:
- 只允许使用我贴出的列名; 需要但没有的列输出 NEED_INFO, 禁止猜列名。
- S_std 的标准化口径(除以样本内标准差)写成配置; 非预定会议 is_scheduled=false
  且默认排除, 排除逻辑写成配置。
- 断言并写入 assert_report: ①无重复 (type,date); ②2017-01–2026-06 各类型
  计数与 R1a 日历逐年对账; ③S_std 无 inf/NaN(缺共识的 CPI/NFP 行合法,
  标 S_std=NULL 并计数)。断言失败非零码退出。
交付: 代码 + pytest(用合成 fixtures) + manifest.md。
```

---

### R2｜公告日面板 + 公告体制 beta 构建（计划任务 M2，主建设，≈1 seat-week）

- **类型**：B（重工程）。**主选**：**Claude Code**（多文件、需在 WRDS/本地 CRSP 环境迭代调试——与 E2 T3 同理由）；国内替代 GLM-5.1 Coding Plan。
- **关键能力风险**：任何模型都不知道你 WRDS/CRSP 环境的当前表名与变量名 → 任务书强制"只用我贴出的表/变量清单"。
- **验收**：14 条断言全过；LOO 篮子 beta 的"留一"正确性通过重构检验（断言 A9）；随机抽 20 行回溯上游（断言 A14）。

**Prompt R2（Claude Code 任务书）**：

```
【粘贴 C0-R】
任务(R2): 在 repo 内实现公告面板与 beta 管道, Python 3.11。输入:
surprises.parquet, macro_calendar.csv, 冻结文件(events_merged.csv,
conv_exposure.parquet, holdings_weights.parquet), CRSP 日度数据——
【我在文末贴出你可用的数据表名与变量名清单, 只许用清单内名称,
缺什么输出 NEED_INFO, 禁止凭记忆写任何 WRDS/CRSP 表名或变量名】。
实现模块:
1. build_returns.py: permno×公告日收益切片, 含 open 价的隔夜/日内拆分
   (CPI/NFP: close→open 与 open→close; FOMC: prevclose→close 与
   close→nextopen), 退市收益按 CRSP 规则并入; 输出 returns_ann.parquet。
2. build_betas.py: 逐 permno 公告体制 beta——只用该股所属 wave 生效日之前
   的公告日, r_i 对 S_std 回归; Vasicek 收缩向特征隐含先验(特征回归的
   系数也只用 pre 时段估计); w_shrink 只从 frozen_config.yaml 读取,
   且必须支持 --sweep 模式输出 w∈网格 的全套 beta(供 R3 收缩扫描)。
   同时输出每 permno 的 n_pre_announcements 与 SE(beta_hat)。
3. build_basket.py: 逐 wave 的 beta_b_loo(i)=Σ_{j≠i} w_j*beta_j /(1-w_i),
   权重取 pre 时段持仓权重(holdings_weights.parquet); 另计算篮子公告日
   收益序列与 F_tilt(对市场正交化后的 S 敏感度, 市场收益列名见清单)。
4. build_panel_ann.py: 汇成 panel_ann.parquet(permno×announcement), 列含
   r_total 与拆分项, beta_i, beta_b_loo, L, L_mkt, L_tilt, F_tilt 载荷,
   ConvExp, Post, wave, 控制变量(清单列名), is_treated。
5. assert_panel.py: 14 条断言, 全过才写 parquet, 任一失败非零码退出:
   A1 主键(permno,announcement_id)无重复。
   A2 处理组每 permno 覆盖其 wave 前后各≥8 个季度的全部预定公告(缺口给清单)。
   A3 r_total = 拆分项之和(容差 1e-8); 拆分项缺 open 价的行合法但须计数。
   A4 beta 估计窗内不含任何 post 时段公告(前视禁令的机器检查——逐 permno
      比对估计用样本的最大日期 < wave 生效日)。
   A5 n_pre_announcements 分布写入 manifest; 中位数与 ≥30 的占比单列
      (Gate-0 第 3 行的原料)。
   A6 w_shrink 的取值来自 frozen_config.yaml, 代码中无默认魔数(静态扫描)。
   A7 |beta_b_loo|、|L| 无 inf; L = L_mkt + L_tilt 逐行可复算。
   A8 篮子权重逐 wave 求和 ∈ [0.98, 1.02](允许现金/缺数据, 越界给清单)。
   A9 留一正确性: 随机抽 50 个 (i,wave), 用全篮子 beta 与 w_i、beta_i
      反推 beta_b_loo, 与输出逐一比对(容差 1e-10)。
   A10 ConvExp 与冻结文件逐行一致(哈希级)。
   A11 S_std 合并后无静默丢行: panel 行数 = 预期 permno×公告组合数,
       差异逐项解释。
   A12 时区: 所有公告的收益窗口与 time_ET 一致(FOMC 当日 close 在事件后,
       CPI/NFP 当日 open 在事件后——逐类型抽 5 个公告人工可核对的清单)。
   A13 无任何列全 NaN; 每列缺失率入 manifest。
   A14 随机抽 20 行, 各列值回溯到上游文件逐一比对(脚本自动执行并留痕)。
工程规则: 幂等、断点续传、逐模块 pytest(合成 fixtures 开发, 真实数据即插
即用)、不为过断言修改上游(上游问题输出 UPSTREAM_ISSUE)。
完成定义: 断言全绿 + manifest.md。逐模块提交, 每次提交前自跑测试。
[此处粘贴: 你的 CRSP 表名/变量名清单 / frozen_config.yaml 初版 /
holdings_weights schema / fixtures 说明]
```

---

### R3｜Gate-0 诊断四件套（计划 §9 的执行者；只碰 pre 时段）

- **类型**：C（诊断设计沿用 P1-T2a 机理，判读不外包）+ B（实现）。**主选**：实现 → DeepSeek V4（功效模拟复用 P1-T2a 代码骨架，模板化）；诊断报告的**判读备忘**（是否过线、框架门是否触发）→ Claude Sonnet 4.6 一次调用起草，**最终裁决是你**（同 E2 "T5 分歧仲裁必须是你"条款）。
- **验收**：gate_report.md 六条线逐条 PASS/FAIL/边缘 + 证据图表；收缩扫描给出联合可行窗口的存在性与宽度；篮子区分度给出 |β_b−1| 与 F_tilt 的逐 wave 分布；功效模拟同时给 γ 合并、γ_tilt、γ_fac 三条 MDE 并归档 exit-D 功效门数值。

**Prompt R3（发 DeepSeek，附 P1-T2a 代码与 R2 产出 schema）**：

```
【粘贴 C0-R】
任务(R3): 实现 gate_diagnostics.py, 输入 panel_ann.parquet(含 --sweep 全套
beta)、frozen_config.yaml、P1-T2a 功效模拟骨架(附件, 复用其 wave 聚类
数据生成过程, 只改参数化为 (ConvExp, L, S) 三维)。只允许使用 pre 时段
结果数据与模拟数据; 触碰任何 post 时段结果列即违反 prereg-before-outcomes,
程序启动时硬检查并拒绝。
输出 gate_report.md + gate_report.json, 六节:
G1 surprise 覆盖率(消费 R1b assert_report)。
G2 收缩扫描联合窗口: 对 w_shrink 网格逐点计算 SD(L_hat)(ConvExp≥0.5% 组)、
   |corr(L,ConvExp)|、SE(beta_hat)≪SD(L_hat) 的达标占比; 输出三曲线同图 +
   同时满足 [SD≥0.25, corr≤0.3, 占比≥70%] 的 w 区间; 区间为空或宽度
   <网格 2 格 → FAIL/边缘。
G3 beta 可估性: n_pre 中位数、分布, ≥30 占比。
G4 篮子区分度: 逐 wave 的 |beta_b_loo−1| 分布、F_tilt 的量级与 t 值;
   D_b≥0.1 的处理质量占比; 判据不满足时输出"框架门触发"标记。
G5 功效模拟: MDE(gamma 合并/γ_tilt/γ_fac) 各自 ≤0.5σ? 另按附件给定的
   "Da–Shive/Greenwood 相关性隐含量级"参数计算 exit-D 功效门并归档
   (此数值一经写出即冻结, 供预注册引用)。
G6 预趋势三件套: 事件时 γ_hat(仅 pre 时段公告)、处理组公告 beta 趋势 vs
   匹配对照、placebo-in-time(2017–2020 假转换日全设计重估)——三者须平/零。
规则: 判据阈值全部从 frozen_config.yaml 读取; 报告只陈述事实与 PASS/FAIL,
不写"建议继续/放弃"——裁决留给人工。
```

---

### R4｜OSF 预注册包（GATE-PREREG 通过后 48 小时内提交）

- **类型**：D。**主选**：Claude Opus 档起草；**提交与时间戳是 `NEED_HUMAN`**（OSF 账号、勾选公开时点由你决定）。
- **验收**：注册文档逐项覆盖计划 §11 清单：SPEC-MAIN 与 γ 分解、冻结的 w_shrink 及可行窗口、异质性五项集合、三腿裁决规则、五出口矩阵 + 框架门 + exit-D 功效门（引用 G5 归档数值）、pre 时段 placebo 结果、数据与样本定义哈希。

**Prompt R4（发 Opus，附 gate_report + frozen_config 定稿 + 计划 §3/§9/§10 节选）**：

```
【粘贴 C0-R】
任务(R4): 依据附件(gate_report.json 定稿、frozen_config.yaml、计划节选)
起草 OSF 预注册文档(英文), 结构: Hypotheses(H1–H4 逐条+符号方向)、
Design(SPEC-MAIN 全式+γ 分解+估计器+推断四件套)、冻结参数(w_shrink 及
其可行窗口、异质性集合、交互阶数上限、Romano–Wolf 族定义)、裁决规则
(三腿三联的布尔逻辑逐字)、Outcome-neutral 检查(G6 三件套结果)、
出口矩阵含框架门与 exit-D 功效门(数值直接引 gate_report.json 键名)、
偏离政策(任何偏离须在论文附录披露)。
铁律: 文中一切数值写成 {{gate.<键名>}} 占位符由脚本注入; 不得出现任何
你自己生成的数字; 缺的信息列 NEED_INFO。交付: 文档 + 占位符清单。
```

---

### R5｜计量设计 + 异家盲评（计划 §6 的落地；C 类，不省钱区）

- **指派**：R5a 设计 → GPT-5 思考档；R5b 盲评 → Claude Opus 档（异家）；分歧你仲裁（E2 T8a/b 协议原样搬用）。
- **验收**：设计文档覆盖八个必答项（见 prompt）；盲评比对表的每个分歧点给出可判定裁决标准。

**Prompt R5a（发 GPT-5 思考档，附计划 §3/§6 全文 + panel_ann schema 与描述统计）**：

```
【粘贴 C0-R】
任务(R5a): 你是计量经济学专家。基于附件, 产出 SPEC-MAIN 的完整计量设计
文档, 供双实现与异家盲评。必答八项:
1. SPEC-MAIN 的完整变量构造与低阶项完备性论证——特别论证 b4(Post×L·S)
   吸收经济体范围 beta 均值回归的充分性, 以及还需要哪些低阶/两两交互项
   才能使 gamma 的三阶交互识别不被遗漏低阶项污染; 给出完备项清单。
2. γ 分解(γ_mkt/γ_tilt/γ_fac)的联立估计方案与共线性诊断(篮子≈市场时
   三项的病态程度如何量化、报告什么统计量)。
3. 堆叠(stacked-by-wave)估计的 clean-control 构造细节; CS/SA 类估计器
   在"结果 = 公告内截面系数"场景下的适配方式(或论证不适配及替代)。
4. 推断四件套的具体实施参数: 双向聚类(公告日×wave/行业)、wild cluster
   bootstrap、RI(转换日/公告标签/L 三种置换)——各自的成熟软件包选型
   (Python 与 R 各一, 禁止建议手搓推断), 有效聚类数 <10 时的失效评估。
5. beta 测量误差: EIV 与 size/流动性相关时对 γ 的偏误方向分析;
   组合级(L 五分位组合)复刻的估计式; 特征隐含 beta 工具变量方案的
   有效性条件。
6. 楔子指纹的估计: W 的构造对 γ_hat 抽样误差的传递(生成回归量问题),
   反转路径与锚定回归的标准误如何校正。
7. Romano–Wolf 族定义(每 spine 一族 + 异质性单独一族)的检验清单。
8. 威胁逐条对策规格化: 计划 §6 T1–T7 逐条落成可执行检验。
规则: 只依据附件; 缺失数据特征列 NEED_INFO; 文献建议单列 SUGGESTED_REFS
标注"需人工核实存在性", 不得写入正文。
```

**Prompt R5b（发 Opus）**：同 R5a 全文，末尾追加 E2 T8b 的盲评条款（先独立设计，再逐条比对附件 B，分歧点必须给可判定裁决标准，非"两者皆可"）。

---

### R6｜主估计双实现（Py + R 互算；GATE-E2-VERDICT 之后、R4 时间戳之后）

- **指派**：Python(linearmodels/statsmodels+设计指定 bootstrap 包) → DeepSeek V4；R(fixest+boottest 系) → GLM-5。逐设定点估计互比容差 1e-6（E2 T8c 协议原样搬用）。
- **验收**：results/main_py.json 与 main_r.json 逐设定对齐；样本定义哈希一致；任何设定实现不了输出 SPEC_ISSUE 不变通。

**Prompt R6（Py 版发 DeepSeek；R 版换语言与包名发 GLM-5）**：

```
【粘贴 C0-R】
任务(R6-py): 按附件计量设计定稿(R5a/b 合成版, 我已确认)实现估计脚本,
输入 panel_ann.parquet 与 frozen_config.yaml。启动时硬检查: 系统日期 >
OSF 注册时间戳(从 config 读取), 否则拒绝运行。
输出 results/main_py.json: 每个设定编号一个对象{点估计(含 γ 三分解),
SE 三口径, RI p 值, N, 有效聚类数, 样本定义哈希, w_shrink}。
规则: 严格按设计文档设定编号逐一实现, 不得增删; 缺失值处理显式声明,
禁止任何未写明的默认行为; 无法实现输出 SPEC_ISSUE。
说明: 同一文档已交另一模型用 R 独立实现, 点估计将逐设定比对(容差 1e-6)。
```

---

### R7｜四条 spine：楔子指纹、纪律、剂量/异质性 + 出图

- **指派**：首轮全套脚本 → Claude Sonnet 4.6（图表纪律好，E2 T7 结论）；批量微调 → Qwen3.6/GLM-5。**纯 API 模型不自己跑图——脚本由你运行或入 Claude Code 跑通**。
- **验收**：一切图注/正文数字运行时读 results/*.json（零硬编码）；锚定回归只消费 P1-T3 冻结的 ibes_sue.parquet；反转组合的构造参数全在配置。

**Prompt R7（发 Sonnet）**：

```
【粘贴 C0-R】
任务(R7): 编写 spines/ 分析与出图脚本, 输入 panel_ann.parquet,
results/main_*.json, ibes_sue.parquet(P1-T3 冻结, 只读)。
1. compute_spines.py → results/spines.json(扁平自述键名), 内容:
   S1 折射: 分解 γ 汇总、压缩图数据(处理组公告日反应对 beta_i*S 的
      散点旋转, pre vs post, 公告内去均值)、日度时点拆分(隔夜/日内)。
   S2 楔子: W 的累计路径 {0,+1d,+5d,+20d,+60d}(处理−对照);
      Greenwood 式楔子反转多空组合(参数入配置)的收益序列与 alpha;
      锚定回归(W → 下季 SUE / 分析师修正), 标准误按 R5 设计的生成
      回归量校正实现。
   S3 纪律: 逐公告截面 R²/斜率(对自身 beta vs 篮子 beta), 处理×时期网格。
   S4 剂量/异质性: |S|、ConvExp、|L| 梯度; 冻结异质性五项(Amihud、
      分析师覆盖、篮子权重/纳入、pre_etf_ownership、|L|), 交互阶数≤3,
      Romano–Wolf 按 R5 族定义调成熟包实现。
2. plot_s1.py…plot_s4.py: 每图一脚本, 零硬编码数值(坐标轴范围除外且注释
   理由); 楔子图沿用 P1-T6 视觉语法(附样式文件)。
3. spines_narrative.md: 每 spine 3–5 句正文草稿, 数字一律
   {{spines.<键名>}} 占位符。
先用我附的合成样例开发, 合成数值不得出现在 narrative。
```

---

### R8｜稳健性网格（计划 §8 全清单，config-driven）

- **指派**：DeepSeek V4（P1-T7 模板改参即用）。**验收**：网格行 = 计划 §8 的 1–8 条逐条映射（含 beta 构造电池、placebo-in-time、随机化 L、双胞胎篮子证伪、饱和度带符号梯度），每行输出与主表同 schema 的 json；无一行靠改上游数据过关。

**Prompt R8**：同 R6 结构，把设定清单换成 §8 网格（附计划 §8 全文），追加一条："双胞胎篮子证伪需要 twin 基金持仓权重文件（我提供），其 L^twin 构造复用 build_basket.py 的函数而非复制代码。"

---

### R9｜创建篮子(creation basket)抽取与制度事实（旁路，`NEED_HUMAN` 先行）

- **类型**：A + 长文档抽取。**指派**：N-CEN/招募书节选精读 → Gemini 2.5 Flash（1M 上下文最便宜，分发行方分批投喂——E2 T6b 的"中间遗忘"对策）；ETF Global/发行方每日篮子文件的可得性检索 → Kimi。**前置 `NEED_HUMAN`**：你先确认 BU 是否有 ETF Global 权限。
- **验收**：逐锚定 wave ETF 输出"篮子实践登记行"，每条结论逐字引用 ≤25 词 + 页码/URL；查不到 → UNKNOWN，禁止用行业惯例填空（计划 §2 的"机制事实陈述不假设"条款）。

**Prompt R9a（发 Gemini Flash，逐发行方分批）**：

```
【粘贴 C0-R】
任务(R9a): 我将分批上传锚定 wave ETF 的 N-CEN 节选与招募说明书节选。
对每只 ETF 输出一行登记表: [ETF, 复制方式(全复制/抽样/UNKNOWN),
是否使用 custom basket(条款原文逐字≤25词+页码), 申赎篮子与持仓的关系表述,
现金比例条款, UNKNOWN 项]。
硬性规则: 每个结论必须定位到我上传文档的具体位置; 找不到→UNKNOWN;
禁止依据 Rule 6c-11 的一般规定推断具体基金的实践——一般规定只能写在
"背景"列。末尾输出"对 H4 篮子纳入异质性检验的可行性评估"。
```

---

### R10｜TAQ 试点 + 增强 spine H1′/H5′（旁路，非阻塞门）

- **指派**：Claude Code（与 E2 T3/T9a 同理由：WRDS 环境内迭代）。**门槛**：30 处理 + 30 对照 × 20 公告日覆盖率 ≥70%（含小盘）→ 才许实现增强 spine；不过门只交 coverage_report，主线不受影响（硬编码此闸——E2 T9a "出厂门槛"模式）。

**Prompt R10（Claude Code 任务书）**：

```
【粘贴 C0-R】
任务(R10): 两阶段, 阶段间有硬闸。
阶段1 taq_pilot.py: 对我给定的 30 处理+30 对照 permno × 20 个公告日,
从 TAQ(表名与字段以我贴出的清单为准, 禁止凭记忆)拉取公告时刻 ±90 分钟
的 NBBO 与成交, 输出 coverage_report.md: 逐股逐日的可用报价占比、
陈旧报价占比(>60s 无更新)、小盘子样本单列。
硬闸: 覆盖率(含小盘)≥70% 才允许阶段2 目标进入队列; 否则程序输出
GATE_FAIL 并终止, 不产出任何增强结果文件。
阶段2(仅过闸后): speed_liquidity.py——公告后 {5,15,30,60} 分钟已实现
移动占比、日内 IPT、有效/报价价差与深度的事件窗曲线, 按 R5 设计的
聚类方案出置信带, 写 results/enhance.json。
工程规则同 R2(幂等、限速重试、fixtures 测试、manifest)。
```

---

### R11｜论文写作（英文稿；引言/贡献/概念框架给旗舰）

- **指派**：引言、贡献段、§2 概念框架、§10 结论 → Claude Opus 档；中段章节初稿 GLM-5/Qwen3.6 Max、旗舰统稿（E2 T12 分工）。铁律条款照搬：一切数字 `{{spines.<键名>}}`/`{{main.<键名>}}` 占位符；引用只许 references.bib 白名单，bib 外引用 = 编造；SUGGESTED_REFS 隔离待人工核实。
- **Prompt R11**：套用 E2 T12 模板，替换：目标风格 JF/JFE/RFS；每节主张必须挂到占位符或 R0/R9 已核实制度事实编号；框架门条款——**若 gate_report 的 G4 标记"框架门触发"，全稿禁用 "basket-specific refraction" 表述，统一用 "wrapper-induced beta compression"**（把这条写进 prompt 硬性规则第 4 条）。

---

### R12｜红队/审稿模拟（异家）

- **指派**：GPT-5 思考档主审（异家于写作者）+ DeepSeek 推理档平行低价审（E2 T13 协议）。
- **Prompt R12**：套用 E2 T13 模板，附件 B 换成**计划 §12 的 Referee FAQ 九条**（作者自认已防守的攻击点），特别指令不变：≥3 Major、至少 2 条落在 FAQ 未覆盖角度、拆掉 FAQ 中站不住的防守也算 Major；追加一条领域敏感项："对'篮子≈市场'与'生成回归量标准误'两点做定向攻击尝试。"

---

### R13｜月度碰撞监测（常驻；Marta–Riva 毛刺阈值）

- **指派**：主体 = 不依赖 LLM 联网的脚本（arXiv + Semantic Scholar API + SSRN 检索 URL 生成——E2 T11 修正后架构原样搬用）；初筛 → Kimi。
- **Prompt R13a（让 R2 同款代码模型写 scan 脚本）**：同 E2 T11a，关键词换为：ETF basket comovement announcement / conversion comovement / announcement day beta ETF / ETF replication switch comovement / creation basket transmission / passive macro news cross-section（中英双语）。
- **Prompt R13b（每期初筛，发 Kimi）**：同 E2 T11b，追加："命中作者含 Marta 或 Riva，或标题含 replication technique/switch 的条目，无论初判重叠度如何一律单列'毛刺节'并给全文链接——该来源的 ALERT 阈值为 40% 而非 60%。命中'高'≥1 或毛刺节非空时，单列'计划 §10/§1 边界表影响评估'。"

---

### R14｜Meta-QA 对账 agent（常驻）

- **指派**：Gemini 2.5 Flash-Lite 或豆包（**仅限此类机械核对**——E2 附录 A 修正沿用）。
- **Prompt R14**：套用 E2 T14 模板，核对清单追加三条本项目特有项：⑥前视禁令证据（R2 断言 A4 的 PASS 记录是否在 manifest）；⑦w_shrink 是否只出现在 frozen_config.yaml（静态扫描结果，R2 断言 A6）；⑧凡消费 post 结果数据的任务，manifest 是否含"晚于 OSF 时间戳"的运行时间证明。

---

## 第 2 部分：Meta 连续性审核

### 2.1 连续性矩阵

| 产出 | 生产者 | Schema 权威 | 消费者 | 交接检查点 |
|---|---|---|---|---|
| 冻结输入四件(events/convexp/holdings/ibes_sue) | P1 项目 | P1 契约 | R2/R3/R7/R8 | 只读哈希登记；任何任务修改冻结文件 = RETURN |
| channel-B 核验表 + Marta–Riva 节 | R0 | R0 prompt | R11(§1 边界表)/R13 | 进正文的文献必须"存在性+URL"双证 |
| surprises.parquet | R1 | C0-R | R2/R3 | 覆盖率对账过 G1；CPI/NFP 缺共识行合法且计数 |
| betas/panel_ann.parquet | R2 | C0-R | R3/R6/R7/R8 | 14 条断言全绿；A4 前视检查 PASS 是硬前提 |
| gate_report.json + frozen_config | R3 | R3 prompt | R4/R6/R7/R8/R11 | 六线判读由你签字；G5 的 exit-D 功效门数值一经写出即冻结 |
| OSF 时间戳 | R4(+你) | OSF | R6 及之后 | R6 启动硬检查时间戳；无时间戳一切 post 估计非法 |
| 计量设计定稿 | R5a/b(+你仲裁) | R5 文档 | R6/R7/R8 | 分歧逐条书面裁决后才下发实现 |
| results/main_*.json | R6 | R5 文档 | R7/R11 | Py/R 逐设定 1e-6 互算 |
| results/spines.json | R7 | R7 prompt | R11 | 论文数字 100% 模板注入，零手写 |
| 篮子实践登记表 | R9 | R9 prompt | R11(§2)/H4 | 逐字引用+页码；UNKNOWN 不入正文结论 |
| coverage_report / enhance.json | R10 | R10 prompt | R11(附录) | 未过硬闸不得出现任何增强数字 |
| referee reports | R12 | — | 你 | ≥3 Major 且 ≥2 条在 FAQ 之外 |

### 2.2 全局反幻觉协议（继承 E2 2.2 五机制，两处本项目强化）

E2 的五机制（数字与文字分离、检索与结论分离、异家交叉、UNKNOWN 正激励、上下文最小化）全部适用。强化：⑥**前视禁令的机器化**——不靠模型自觉，靠 R2-A4 断言 + R14 第⑥项核对双闸；⑦**预注册时序的机器化**——R6/R8 启动时硬检查 OSF 时间戳，把"先注册后估计"从纪律变成程序不变量。

### 2.3 连续性自查结果（已逐条核过）

- C0-R 的定义（β 公告体制、LOO、L 分解、SPEC-MAIN 低阶项、楔子三腿）与计划 v2.1 §3/§6 逐字一致，被 R2–R12 通过粘贴继承——术语单点维护。
- R3 的收缩扫描消费 R2 `--sweep` 输出——**w_shrink 在 R2 是网格、在 R3 之后才冻结**，顺序不可倒；frozen_config 的 w_shrink 字段在 GATE-PREREG 前允许为空，R6 读到空值必须报错。
- R5a 第 1 条（低阶项完备性）直接对应第二轮评审的"beta 均值回归"攻击——设计文档若删减 b3/b4 即 SPEC_ISSUE，实现层不得自行补项。
- 楔子的生成回归量问题在 R5 第 6 条设计、R7-S2 实现两处出现——实现必须引用设计文档节号，防止两处口径漂移。
- 框架门(G4)有三个下游消费点：R4 预注册、R7 叙事、R11 写作硬性规则第 4 条——三处都已显式写入，任一遗漏会造成"注册了压缩、写成了折射"的致命不一致。
- 已发现并修补的一个断点：反转组合(R7-S2)的构造参数若硬编码，计划 §8 的稳健性无法执行——已在 R7 prompt 强制入配置。
- 残余风险（人工把守，不可外包）：①holdings_weights.parquet 的权重口径（市值权重日期基准）须你与 P1-T2 的口径书面对齐后再发 R2；②R3 六线判读与 R5 分歧仲裁必须是你；③OSF 提交与时间戳；④CPI/NFP 共识许可（NEED_HUMAN）；⑤各任务书"[此处粘贴]"必须真实填充——空占位符诱发虚构输入。

### 2.4 成本量级估算（按 E2 2.4 口径，仅供排序）

B 类（R1b/R2/R3/R6/R7/R8/R10/R13a）走 DeepSeek/GLM/Qwen + Claude Code 订阅：API <$100 + 既有订阅（R2 是主建设，约 1 seat-week，在订阅内）。C/D 类集中在 R5 双旗舰、R4/R11 Opus、R12 双审：单次 $5–30、总计 <$150。A 类（R0/R1a/R9/R13b）Kimi/Gemini Flash <$30。**Refraction 全项目 LLM 成本上限约 $250–300**——低于 E2，因为最重的识别资产是 P1 冻结复用。请勿在 R5/R12 上省钱：本文对错的分界线在计量设计（低阶项完备性、生成回归量、少聚类推断）与"篮子≈市场"的攻防上。

---

## 附录 A｜逐任务能力复核（增量表；E2 附录 A 全部结论继承）

| 任务 | 关键能力 | 指派 | 复核结论 | 残余风险 → 兜底 |
|---|---|---|---|---|
| R0/R1a/R9b/R13b | API 联网 + 引用纪律 | Kimi(主)/Gemini grounding(并集) | ✅ 同 E2-T1 行 | 覆盖率 → 高价值项双引擎并集 |
| R1b/R3/R6/R8/R13a | 模板化数据/计量代码 | DeepSeek V4 | ✅ 同 E2-T2/T6a/T8c/T10 行 | 不知 WRDS/USMPD 现行结构（所有模型皆然）→ prompt 强制"只用贴出的表/列名" |
| R2/R10 | 多文件工程 + WRDS 环境调试 | Claude Code | ✅ 同 E2-T3/T9a 行 | 前视与留一是本项目特有易错点 → 断言 A4/A9 机器化，不靠模型自觉 |
| R3 判读 | 诊断解读 | Sonnet 起草 + 你裁决 | ✅ 判读文档化即可 | 判读外包风险 → 报告禁写建议，裁决权收归人工 |
| R5a/b | 计量方法论（三阶交互完备性、EIV、生成回归量、少聚类） | GPT-5 思考档 + Opus 盲评 | ✅ 同 E2-T5/T8a 行；**不存在便宜且够用的选项** | 双旗舰同盲区 → 分歧裁决标准强制可判定 + R6 双实现互算做第三道闸 |
| R6 | Py/R 双栈计量实现 | DeepSeek(Py)+GLM-5(R) | ✅ 同 E2-T8c 行 | 真验收 = 1e-6 互算 + OSF 时间戳硬检查 |
| R7 | 出图 + 排版纪律 | Sonnet 4.6 | ✅ 同 E2-T7 行 | API 模型不自跑脚本 → 由你运行/入 Claude Code |
| R9a | 1M 长文档逐字抽取 | Gemini 2.5 Flash | ✅ 同 E2-T6b 行 | 中间遗忘 → 分发行方分批投喂 |
| R11 | 英文学术写作 | Opus 主笔 | ✅ 同 E2-T12 行 | 编数字/编文献两大事故 → 占位符 + bib 白名单结构性封死；框架门条款写进硬性规则 |
| R12 | 对抗审稿 | GPT-5 主审 + DeepSeek 推理档平行 | ✅ 同 E2-T13 行 | 礼貌偏差 → ≥3 Major、≥2 条 FAQ 之外、定向攻击两处软肋 |
| R14 | 机械清单核对 | Flash-Lite/豆包 | ✅ 同 E2-T14 行（豆包仅限此用途） | 清单全部为可机械验证项 |

**总体结论**：①本手册无新增能力性风险指派——全部任务型态在 E2 已验证的能力边界之内，且本项目最危险的三类错误（前视、预注册时序、篮子≈市场的口径漂移）都已从"纪律"降维成"断言/硬闸/单点配置"，不依赖任何模型的自觉；②与 E2 相同，最脆弱环节是 R5（设计错误无法被执行发现），保障来自异家盲评 + 双实现互算 + R12 定向攻击这三个结构性机制，请勿用"换更强模型"替代。
