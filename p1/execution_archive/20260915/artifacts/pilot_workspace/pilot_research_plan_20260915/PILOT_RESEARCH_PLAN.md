# P1：从现有数据到一次可结束的 pilot 研究决策

日期：2026-09-15。版本：研究执行方案 v1，待 PI 批准其中列明的科学选择；不是新合同签署、Gate 1 PASS 或研究 GO。

## 1. 本轮决定与最终要回答的问题

**停止把“继续核查 Gate 1”作为项目主线。现在按完整研究方案组织工作。** 保留历史 Gate 1 未通过的事实，但不以它阻断样本/识别诊断、代码准备或纯合成实验。测量问题只阻断依赖该测量的步骤。不开启旧 Gate 0/1，不重做已接受的数据合同 reconciliation，不恢复 Refraction、IRR 或股票–ETF 错误合并。

Pilot 的终点是一份证据支持的决策，而不是一条显著系数：

1. 这个 MF→ETF conversion **package** 的比较能否对应一个明确、可信度可说明的因果对象？
2. 在同一个冻结的比较对象下，有多少真实可用的证券、盈余事件、wave、经济 sponsor 和独立变异？
3. 测量误差、选择和相关性之后，实际估计程序能否有足够精度识别预先认定有经济意义的效应？
4. 若不能，具体哪一种额外数据能够改变判断；哪些问题买再多报价也无济于事？

本轮只完成方案、现有证据盘点和独立方案复核。后续 pilot 在批准范围内使用 metadata、合成数据和 PRE 校准；**不需要查看观察到的 POST response 来作出 pilot 决策**。实际 POST 效应估计另设明确解封决定。

权威基线：`/Users/lilyluo/research-portfolio-p1-feasibility-20260913/p1/feasibility_adjudication/20260913/reconciliation/estimation_contract.reconciled.PROPOSED.yaml`，SHA256 `00af7d39fd51e9c3c6a9051036f26a68b337f2132848368a729ff8a70d32663f`。已接受的复核不重启；这里保留其候选设计并把尚未签署的实施选择显式列出。后来获得的数据操作许可不自动等于批准最终科学合同。

## 2. 从真实起点出发，不把下载量当作研究样本

现有证据：相邻 `../gate1_20260915/DECISION.md`、`readiness_receipt.json`、`followup/VERIFICATION_V2.md`、`followup/clock_crosscheck_v3/RESULTS.md`。它们的时间顺序重要：后两份已推进 class identity 和时钟证据，不再把这些问题描述为完全未查。

| 层级 | 当前已知 | 不能据此推出 |
|---|---|---|
| 获取总体 | 71 PERMNO / 71 stock-wave / 5 waves；852 associations = 568 PRE + 284 POST | 852 个已认证独立经济事件或最终合格样本 |
| 结构完整性 | 5,544 个已选择下载文件存在且 header/size 一致；原计划 5,548 jobs | 全部 body 可解码或六 horizon 同步有效 |
| 核心请求映射 | 839/852 associations 的 8 个 stock/SPY 请求 legs 映射齐全 | 8 个获取 legs 等于 6 个研究 endpoints |
| CRD 修复 | 历史 Class B 已核实；192 个修正单证券窗口全部日期映射成功 | 修正报价已购买/下载：尚未完成 |
| 盈余输入 | 852 个源映射；659/852 有至少两位分析师的获取 envelope | 已经构造兼容口径且严格先于 release 的 SUE |
| 时钟 | 8 个非随机 PRE 对照：6 有时间，5 同分钟、1 差一分钟，2 date-only | 整体 timestamp 误差界或完整 RTH census |
| exposure | 71/71 报告和分母日期早于记录的 A；split basis 仍 provisional | 最终分组、完整 package 或公开可得时点已认证 |

最重要的已知设计警报：在当前**拟议** competing-conversion 排除与“全 12 次事件都有至少两位分析师”筛选的交集中，完整支持池为 W002 H10/L165、W013 H0/L0、W016 H2/L1、W021 H0/L0、W025 H2/L2。W016 原为 stress，不自动转主样本。15 是被 acquisition cap 截取的子集，不是完整池上限。这个交集不是最终合同人口；要分别报告 overlap、事件级 SUE、全 12 次平衡筛选的损耗，不能把采购便利条件悄悄变成科学条件。

## 3. 候选研究设计：先固定问题，再评估是否做得成

### 3.1 人口、处理与时钟

目标是 verified conversion package 中，严格 PRE-announcement 的正持仓美国普通股。包内各基金分别有 pooled portfolio、share class、ETF security 标识；持仓证券使用历史有效 PERMNO/证券标识。保留经济日期与 availability timestamp，不能用后者替代前者。

`A_w` 为包内最早独立验证的公开公告时点，使用最早合理边界排除潜在受影响 PRE；`I_w` 为批准 package 规则下最后实施时点。所有 PRE response legs 必须严格早于 A；跨越 [A,I) 的窗口剔除。原采购 POST 的 20-session buffer 保留为待确认的候选实施细节，不默认为已签合同；整个窗口而非仅 release date 必须满足 regime 条件。

剂量 `D_iw = Σ(pre-A、split-consistent fund shares) / contemporaneous split-consistent shares outstanding`。同一经济基准、分母日期、基金合并和 ETF class pro-rata 规则沿用已验证合同；未验证项不凭日期排序放行。较晚发布、但经济日期在 A 前的文件可以回溯测量 predetermined ownership，不能称为 A 时公众可见。

在完整 eligible positive ownership 波次内、**先于 earnings/quote 选择**，按原逆经验 CDF terciles 分 H/L，剂量相同不拆分。中间组和零持仓留作预先标明的 secondary，不把零组冒充 primary low。采购的 71 名称只是工作样本，不代表总体随机抽样；不外推至所有 conversions。

### 3.2 主要估计对象与解释上限

令 `b_w,g,p,h` 为经过固定模型和共同观测支持标准化的 signed-SUE response slope：

`δ_w,h = (b_w,H,POST,h − b_w,H,PRE,h) − (b_w,L,POST,h − b_w,L,PRE,h)`；
`θ_h = mean_w δ_w,h`，在事前冻结且实际 estimable 的 wave 集合等权平均。

Low 也受暴露，所以这不是“转型 versus 不转型”的平均效应，更不是 AP arbitrage 单机制效应。最强允许主张是：在下述不可完全检验的条件下，conversion package 造成的高低暴露**差异性**盈余响应变化。

沿用逐 wave、equal event-row fit：所有 SUE/group/post 低阶项、stock-by-wave 截距和 baseline SUE slopes、industry-by-calendar-quarter-by-wave 截距和 SUE slopes；仅删除 exact redundancy。标准化股票权重和 calendar-cell 权重及“每个正权重 stock×cell 必须有真实观察”限制照原 YAML 实现。先输出该限制导致的空单元，不能以预测补齐，或为了 rank 偷删控制。若这一严格支持对象不可行，报告 **该标准化对象 NOT_ESTIMABLE**，提出一次明确 amendment，而非无限补原不存在的 stock-quarter earnings。

### 3.3 SUE、价格响应与 session（实施候选，不在本轮计算）

- SUE：quarterly actual EPS 减每位分析师在 release 前 90 calendar days 内最后一次 forecast 的跨分析师中位数；至少两位、相同货币/share/accounting basis。时间不确定的预测须早于 release uncertainty 的最早边界；同日无明确先后时不假定先于 release。版本/修订去重先于计算，不用未来修订 actual 偷换原始 surprise。
- 价格缩放与单一 PRE SD 沿用 YAML：按股票最早相关公告前的 split-consistent closing price 及 unique eligible PRE events 的单一 SD；正式字段、缺值与 corporate-action policy 在值计算前冻结。同一经济事件跨 stack 使用同一个 SUE；不能分组或 POST 重新标准化。两位分析师 count 不等于该条件已满足。
- `CAR_h = R_stock,h − β_i R_SPY,h`，对应同 feed、同 clock midpoint price-return legs；不减 alpha。β 用 CRSP RETX 的 [-250,-21] trading-day 窗口、含截距、≥120 usable days；stock-specific 跨 wave 最早安全 PRE 基准写入实现，以免校准混入已处理时期。
- horizons 5/15/30/60 min、close、+1d close；RTH-only legs 用简单回报乘法串接，overnight/opening gaps 单独，不悄悄加回。事件前 baseline 及每个开收盘端点的 as-of/state 规则、stale 与 withdrawal 区分必须在代码配置中明确，并用小样本验证。
- 原 primary candidate 为 release 在实际收盘前至少 60 trading minutes 的 RTH，open inclusive/close exclusive，六 horizon common mask。非 RTH 的 opening-response 是不同 estimand，只报告其可用性，不自动替换。全日期下载让我们能做 metadata census，不代表 session 已定。
- XNAS、BATS、ARCX、XNYS 是 venue-specific feeds，不宣称四个等于 SIP NBBO。建议 pilot 核心测量明确标为 XNAS venue response，其他三源为同 mask sensitivity；若论文必须回答 consolidated-market 发现，缺的是相应市场覆盖证据/数据，而非把 XNAS 命名成全国市场。此限定需 PI 明示接受。

### 3.4 什么支持识别，什么不能

需要 conditional parallel changes in SUE slopes、足够 overlap、稳定 surprise/观测选择、没有与剂量相关的 sponsor 同期冲击、没有差异性 conversion/peer spillovers。转型时间非随机，持仓非随机，分析师与报价 coverage 可能内生。列出每个 wave 的并购、管理/mandate/费用/基准变更及同日事件来源；这些是识别威胁，不是假装可以全部用固定效应吸收。

诊断：只用安全 PRE 做 event-time SUE-slope placebo、早/晚 PRE 稳定性、dose 与可观察协变量差异、surprise 分布与分析师覆盖稳定性、stock/sponsor leave-one-out 影响；报告估计精度与可排除的偏离大小，**不把 pretrend p>0.05 当成平行趋势证明**。这与 [Roth 对 pretest 的低功效与选择风险的分析](https://www.aeaweb.org/articles?id=10.1257%2Faeri.20210236)一致，但该文不是 P1 的实证验证。POST 仅用已许可非响应 eligibility 比较选择率，不能在本阶段看 POST response 或据此选窗口。

Raw curve 本身不能证明“加快价格发现”。Normalized `b_h/b_T` 需要另一组 shape counterfactual 限制及联合分母不确定性；terminal reference 近零/符号不定就不解释比例，不删除弱 wave。纯 timing 还要求两组各自 terminal equivalence 与高组自身 acceleration，而非仅相对 κ>0；+1d 不是真实基本价值。H3 未定义，保留为开放 scientific issue：建议 PI 批准本 pilot 先决策 differential signed response 的可行性，不假装已完成原 co-primary H3。

## 4. 有限执行图：三个工作线，共用一个版本化 manifest

`P0 → [P1 design / P2 measurement / P3 synthetic engine] → P4 PRE calibration → P5 power+identification decision`

P1 不等 P2；P3 可先用合成 fixture；P4 只接入合格 PRE；不能因某一步 UNKNOWN 清空已经完成的其他结果。

| 包 | 实际工作及输出 | 完成/停止标准 | 模型、effort |
|---|---|---|---|
| P0 控制面 | 一个版本化 `pilot_config`、输入清单、权限/已批准科学选择、数据缺口登记表 | 每个字段已冻结或明确 UNKNOWN；不要求再次审全项目 | 现有 coordinator；本身不可见路由写 NOT_OBSERVED |
| P1 人口与识别 | 每 wave/tier 的 sequential attrition；PRE/POST、session、stock×calendar support；冲突 conversion/source；signed sponsor；symbolic rank 与 required-column alias | 定位到哪些 rows/cells/假设失败；输出 supported target 与原目标差异；无 SUE 数值时 numeric rank 未知 | gpt-5.6-sol / medium |
| P2 测量 | 根据证据给 release uncertainty；source-specific session census；小 golden PRE endpoint 测试；再对固定 manifest 输出 stock/SPY 六 horizon booleans | 输出 usable/unavailable/unknown 的确切分母；失败只影响该边/事件；禁止整档反复扫描 | gpt-5.6-terra / medium；纯 job/status 用 gpt-5.6-luna / low |
| P3 合成引擎 | 实现原标准化与 rank；event reuse 与全 horizon covariance；已知真值/零效应/缺组/弱 terminal fixtures | 合成真值恢复、缺支持 fail-closed、event duplication 不造精度；不重复旧代数测试，只补新接口 | gpt-5.6-sol / medium |
| P4 PRE 校准 | custodian 算 PRE-only SUE、β、response nuisance；数值 rank、residualized SUE information、残差协方差 | 存储安全 PRE 范围与每个校准值 lineage；未授权部分 NOT_RUN；POST nuisance 不进入 | gpt-5.6-sol / medium；一个指定 covariance 难点可 high |
| P5 决策 | exact-estimator conditional simulation；效应大小×coverage×dependence scenarios；识别 threat matrix；最小增量数据建议 | 一份 GO/HOLD_DATA/HOLD_DESIGN/NO_GO 和一个行动；不需要真实 POST θ | gpt-5.6-sol / high（仅统计实现）；gpt-6-astra / high 独立科学裁决 |

同一时间最多两个 worker；无嵌套、无 Max/Ultra。模型不负责忙等，每个包用脚本 checkpoint、退出码及窄 receipt。低模型监控不改变科学规则。一次 source pass、一次主要执行、有限修复后仅复核变更，不全量重审。没有技术性失败不得重跑相同任务。每包即使失败也交付 partial table 和准确阻断点。

P2 的时钟先表示为有来源的 uncertainty interval；只有区间内所有可能时点均属同一 session/满足 RTH-60 才称确定分类，跨边界为 UNKNOWN。不能把已观察的一分钟差异推广成全样本 ±1 分钟误差界。缺少秒级界可以阻断短 horizon 测量，却不阻断 P1 的可计算 metadata 结果。一个固定来源 pass 后保留 unknown，不继续无限网页搜寻。

原 fail-closed 要求继续有效，但范围缩小到真正的新实现：任何新公式、cutoff、mapping、counterfactual 修订均需版本化 amendment、新 golden sample 与小 pilot；至少20个最终小样本观察由 custodian 回查原行，模型只收允许的核验结果。相关 full-run 入口必须在扫描 archive 前核对 `PILOT_PASS.json` 的 code/config/data-contract/manifest hashes 与 invariants。不重跑不相关旧 fixtures、不重算用户已取消的全档 DBN hashes。该约束不阻断写方案、local metadata joins 或 synthetic-only 实验。

## 5. 具体功效方案：不是按 852 套公式

### 5.1 信息与依赖结构先于 p 值

报告每 wave×tier×regime 的 unique stock、unique economic earnings event、calendar cell、SUE variation、残差化 treatment×SUE 列范数、rank、leverage 和 wave 权重。结构 rank 可先用符号/合成数值诊断；最终 numeric rank 要真实许可 SUE。报告 shared event、stock、经济 sponsor 与全部 response-leg dates（含+1d）网络。连接分量不是有效样本量。

原 candidate component multiplier 若图塌为单一/极少主导 component，就停止**该 inference procedure**。不能凭调 cluster 维度获得想要的标准误。更不能把四个 package、417 release dates 或一秒报价数当作独立 treatment assignments。

仅允许一次有边界替代 inference memo：明确抽样/依赖假设、small-cluster 推断适用条件与不能验证处，由 Astra 复核、PI 冻结后再校准。若没有支持的程序，报告 descriptive/model-conditional precision，不给 confirmatory power/GO。没有随机化机制，不称 randomization inference 为 exact。[Cameron–Gelbach–Miller 的多向聚类方法](https://cameron.econ.ucdavis.edu/research/multiway06.html)允许非嵌套相关维度；该方法存在不代表当前少 sponsor 样本可用。

### 5.2 校准与模拟的实施规则

冻结 final outcome-blind POST eligibility design，但不读 POST SUE/response 值作校准。PRE 保留六 horizon joint residual vectors、股票内和 sponsor/date 依赖；记录 PRE→POST covariance transport 假设。模拟中的 POST SUE 取 PRE 分布的事先固定生成机制，不把模拟出的 variation 当作已观察 variation；未来实测数值 rank 仍需单独确认。

每次模拟要走同一 fit、standardization、weights、covariance、multiplicity、weak-reference 处理。伪重复 stack 引用同一 latent economic event。完整保留 horizon/reference covariance。先做 null size 和 coverage，再报 power；不能直接用 `2.8×SE` 充当真实主设计功效。

建议事先固定的 scenario grid（均为方案建议，非校准结果）：

- 效应：零；早期 raw slope 单独变化；terminal amplitude 变化；两者混合；相对 shape 与高组自身 shape 不一致。禁止只模拟偏好的 acceleration。
- 尺度：raw MDE 用 bps / 一个冻结 PRE SUE SD 输出完整 power curve 与 MDE80/MDE90；在 PI 给 raw economic margin 前不评“足够”。Shape 使用现合同待批 0.05；terminal 使用待批 0.05×B*，B* 的 PRE 估计误差也模拟。
- variance transport：PRE基准及 residual SD×1.25、×1.5；dependence 保留基准并做事先固定 stronger sponsor/date correlation stress；selection 按已测 masks 与预设增加10%/20%失配情形。不从 POST 响应拟合这些 stress。
- 主 family 六个 raw θ，沿候选 Romano–Wolf familywise 5%（先确认与最终合法 inference 配套）。建议 raw-power 主要 rejection event 为至少一个 horizon 在该 family 校正后拒绝各自零假设；这仅表示 any-horizon detection，不等于全部 horizon、early acceleration 或纯timing。逐 horizon 与 all-required-horizons power 分开报告，不能用较高的 any-horizon power 代替指定科学主张的功效。Shape/equivalence 分开有联合 confidence region。正式内层 bootstrap draws 沿原候选 9,999；开发 smoke 不冒充最终。
- 先 1,000 Monte Carlo draws；仅当 size/power 决策落在 Monte Carlo uncertainty band 时按预设规则延长到最多5,000。所有 attempted replicates 为分母；failed fit 记 non-detection，未形成置信区间记 noncoverage，另报 conditional-on-success 指标但不得替代主要指标。报告 seeds、MC confidence intervals、失败fit比例及失败原因。失败率是独立报警项，不能靠失败造成的低拒绝率宣称 size 好。禁止以继续模拟寻找 PASS。

计算上先缓存固定设计分解和允许的score映射；20次合成smoke仅用于性能/实现测试。建议首轮按事前scenario manifest选最多6个决策场景（不是整个grid笛卡尔积），运行前给出 outer×inner×scenario 工作量及实测耗时外推。建议首个正式packet设16 CPU小时预算；预算内不足以达到指定MC精度则交付未完成receipt和精确追加计算请求，不减9999到一个方便数后冒称同一程序，也不自行启用更贵AI agent。该预算与scenario顺序属于P0待批实施配置，不是本轮已运行或保证耗时。

建议 pilot 报告标准：null familywise rejection 的95% Monte Carlo区间上端≤7.5%作为实施报警线，coverage区间覆盖目标水平；power在批准 economic margin 下达到80%且披露90%所需规模。它们是待批工程/决策阈值，不是证明推断有效的定理。若 tolerance 不达标，只修具体 implementation bug；依赖假设不可信即 HOLD_DESIGN，不能把某个模拟 DGP 下 size 好看当作验证现实识别。

### 5.3 增加数据究竟增加什么

分别模拟三个固定扩展场景：现有 wave 增加可观测 H/L stocks；同股票增加合格 PRE 盈余次数以改善校准；增加独立 verified conversion packages/sponsors。虚构扩展只能标注 scenario，不冒充真实可得 roster。报价加密用于 measurement，不直接增加 treatment shocks。若限制来自 few sponsors/overlap，优先先查新的独立 package metadata，而不是继续买同一71股票的行情。

## 6. 缺口→测试→最小补数，不再盲下载

详见本目录 `DATA_GAP_MATRIX.md`（现有 receipts 的独立盘点）。所有新需求写入一次增量表：`gap_id, affected_wave/event, input_version, test_unblocked, exact_source/fields/window, existing_data_reusable, incremental_cost, authority, decision_impact`。

优先级：

1. **先无需买数据**：区分 clean-overlap 与全12次两分析师平衡筛选的损耗；完整支持/控制矩阵；经济 sponsor/package identity；基于已有 broad windows 的 session 与 mask；现有CRSP和IBES输入的计算就绪度。
2. **仅修真正影响 eligible 样本的报价**：先把 CRD 192修正窗口和4失败请求与 eligible event manifest 交叉。原4请求免费复报价总计$0.028855502605，不是CRD修复总价，原 bare-CRD group 不能再原样下。只报价需要的修正单证券窗口，去掉已下载SPY；不得再买完整重复面板。账户实际余额另核，不沿用$123作当前余额。
3. **按识别缺口补证据**：缺 package公告/并发转换/denominator basis 时指定fund与字段。只有 endpoint需要秒级精度而来源不支持时，提出一个source-specific clock request；源无法给出误差界则该 timing对象不可认证，不无限找网页。
4. **若原主设计结构失败**：提交一次 alternative target amendment（例如减少目标wave或独立新package扩展），明确改变的是问题本身。不得偷偷放松 competing-conversion 排除、转非RTH、加stresswave或删控制后称原设计成功。

一个补数 batch 后重新计算受影响行，不全量重复 Gate1。若补数不能改变可识别性、rank 或批准 margin 下的决策，不下载。任何购买前报精确订单、报价与余额/授权；本轮无购买。

## 7. 收口决策与一个 PI 决定包

| 输出 | 必须有的证据 | 不允许的捷径 |
|---|---|---|
| GO（仅进入另行批准的 confirmatory preparation） | 明确目标/assumptions、可测量共同支持、PRE数值rank及POST symbolic/generic支持、可信推断与批准幅度下足够conditional power、解释边界冻结 | 实际完整PRE+POST数值rank仍未观察；模拟POST SUE不能认证它。不叫“已证实 conversion 有效”或自动解封 POST |
| HOLD_DATA | 确切缺输入且补齐可能改变上述决策；有一笔最小需求 | 泛化“数据还不够”、无限核查 |
| HOLD_DESIGN | 估计对象/对照/推断/经济margin/H3未决，或已有证据显示当前设计结构不支持 | 用增加报价数量掩盖设计问题 |
| NO_GO（指定设计） | 冻结人口/比较不可估，或在预先限定的可行扩展范围仍无法满足已批准目标；说明适用范围 | 宣称所有MF→ETF问题均不值得做 |

**当前研究仍 HOLD_DESIGN + HOLD_DATA；不是 NO_GO，未计算真实 power。** 已有证据足够把重点从下载迁移到“原比较到底剩几个 wave、什么信息量、能推断什么”。

建议一次性 PI 决定包，而非逐条反复要批准：

1. 批准有限 pilot 以 differential signed SUE slope 可行性为首要目标；H3/纯timing留作明确未解决项，不宣称完整原研究完成。
2. 原 RTH-60、标准化/overlap/tercile 规则作为 literal baseline；允许并列 outcome-blind attrition diagnostics，但不让诊断自动选另一主设计。确认20-session buffer与venue-specific measurement范围。
3. 批准 named custodian 在现有许可环境做上述PRE-only SUE/response/covariance校准及POST非响应mask，返回汇总与receipt，不向模型展示raw值；若旧授权已覆盖，只引用其版本，不重复索要。
4. 给出raw slope的经济意义阈值（bps/1 PRE SUE SD），或同意先看整个MDE曲线、不作“足够”结论；确认shape/terminal拟议margin和模拟报警线。不依据 power 反选经济margin。
5. 认可本轮只计划/复核；正式POST解封、新购买、替代session/inference/人口变更各有明确操作决定。

**下一步仅一个：实施 P0/P1/P3 的一次零采购、outcome-blind design build，并把 P2 的必要测量纳入同一队列；首先交付逐 wave/tier 的最终候选支持、rank 与依赖表。** 这批可以定位哪些缺数据值得补，不再等待一个笼统 Gate1 PASS。P4/P5 按其输入/许可衔接，不重新写整份研究计划。

## 8. 交付清单与成本纪律

本轮：本方案、`DATA_GAP_MATRIX.md`、`PLAN_REVIEW.md`、`PLAN_RECEIPT.json`。后续每包：版本化config/manifest、support与exclusion表、mask census、design/rank/dependence report、PRE calibration receipt、synthetic/power results、单页finaldecision及一个精确增量order或无采购决定。

本轮实际委派为 Sol/medium 盘点、Astra/high 独立方案复核；当前主agent路由若不可见写 NOT_OBSERVED，不伪装已切换。后续表是拟定路由，不代表所有agent已经运行。OpenAI Docs用于核对独立subagent配置原则；[官方 subagents 文档](https://learn.chatgpt.com/docs/agent-configuration/subagents)不替代本客户端实际dispatch记录。未测得实际token/美元花费时不虚报节省比例。
