# P1：集中度与信息传播（独立工作目录）

此目录是新方向后续工作的主入口，与旧 MF→ETF conversion 档案分开。

## 最新状态（2026-09-22）

- **最新实际结果：[FOMC消息到达与跨市场响应](20260922_fomc_information_arrival/results/RESULTS.md)**：2023/2024 全部16次例行声明、16个机械对照、96个原生 mbp-1 窗口已完成。2024事件后60秒的绝对调整中位数为ES 18.45bp、SPY 18.38bp、23股16.74bp，显著大于对照；但控制ES和现金股票信息后，SPY完整块的下一秒增量在自选lambda为+0.002512、固定A2 lambda为−0.000770，两者区间均跨零。决定为 `COMMON_NEWS_WITHOUT_DISTINCT_SPY_INCREMENT`：FOMC支持共同消息下的联合快速调整，不支持SPY独立主导个股价格发现。独立reviewer发现并促成修复一秒窗口端点边界；最终四单元已按新哈希重跑。下一步保留FOMC作共同信息基准，只把同一框架用于固定earnings样本，检验宏观/公司独有信息的双轨价格发现。
- **最新实际结果：[信息来源六模型拆分与2024全年跨期复现](20260922_source_attribution_replication/results/RESULTS.md)**：用户将外部样本扩为2024全年每月第5/15个NYSE交易日，共24日；72个XNAS/ARCX/ES窗口已齐备且原始DBN仅留SCC。弱基准下SPY报价在主调参规格仍有很小正增量，但控制目标股/rest成交后明显减弱，SPY成交增量为负，完整SPY块A2→A5在2024等权主指标为−0.000156，日期区间[−0.000310,−0.000020]，24次LOO全负；固定A2 lambda为−0.000321。现金股票成交块反而稳定为正。决定为 `LIMITED_TO_INFORMATION_SET`：SPY报价可作共同信息代理，但现有普通日条件预测不能建立ETF独立结构性价格发现主导。唯一下一行动是停止扩买普通机械日，先冻结一个独立定时的earnings或macro事件设计。原执行prompt和解释修正仍保留在同目录。
- **最新实际结果：[ES期货控制后的条件预测比较](20260922_futures_control/results/RESULTS.md)**：24个普通机械日期（不是earnings或macro日）的ES原生报价已取得并形成100%有效的一秒特征。ES与SPY相对基础模型的原始增量均稳定为正；quote-only下SPY|ES四格为正且leave-one-date-out不翻号，但加入分离成交历史后SPY|ES接近零并变号。决定为 `MIXED_OR_UNRESOLVED`：一秒尺度的共同市场信息高度重叠，SPY是有用预测代理，但独立ETF结构性贡献未建立。反向股票层增量八格均为负。原始DBN和逐行特征只留SCC；API报价金额为USD 3.422716096042，非已核实账单扣款。唯一下一行动是12个未查看2024普通日期的固定规格复现，带停止规则。
- **本轮已执行规格：[期货控制执行 prompt](20260922_futures_control/NEXT_EXECUTION_PROMPT.md)**：承接 `999faf6` 的探索性结果，在相同24日加入一套ES期货报价，用四个同支持模型比较SPY与ES的条件预测增量。历史prompt保留为执行规格，实际结论以上一条为准。
- **最新探索性结果：[一秒方向性证据包](20260922_directional_evidence/RESULTS.md)**：在控制目标股自身历史和其余22只抽样股票的报告权重篮子后，SPY历史对23只股票未来一秒midpoint的样本外增量在XNAS/ARCX、0/500ms网格和报价／成交扩展口径均为正；反方向及股票联合面板对SPY的增量为负。原生报价更新后的同向响应在两个方向都存在，ETF→股票在较长窗口通常更持久，但不足以证明单向因果价格发现。横截面权重／high-mid-low梯度不稳定，故集中度暂不构成贡献。全部原始DBN、事件行和特征行留在SCC；本轮无需新增Databento购买。研究决定为 `ADVANCE_CONDITIONAL_ETF_LEAD_MECHANISM`，下一步只加入同窗口E-mini期货基准，区分ETF特有先行与一般共同信息传递。
- **最新实际结果：[双向增量信息传递完整试点](20260922_bidirectional_information/results/RESULTS.md)**：48/48 个精确 `mbp-1` 双场所窗口已留在 SCC，形成 4,147,200 行特征和 552 个日期外股票×方向×时距结果。五秒主尺度的 ETF→股票与股票→ETF区间都跨零，裁定 `PREDICTIVE_TRANSMISSION_NOT_ESTABLISHED`；整数秒的一秒次指标显示 ETF→股票为正、反向为负且错日安慰剂消失，但 +500ms 网格明显减弱，不能升级成结构性价格发现主导。组删除模型因联合 complete-case 支持只有 XNAS 4、ARCX 595 个测试中心而不作经济解释；集中度贡献尚未成立。独立 Sol/high 原始中心与损失复算见结果目录。
- **同轮探索性续作：[一秒非平衡联合模型](20260922_bidirectional_information/results/exploratory_eda/EDA_RESULTS.md)**：改用层内可用股票的报告权重重归一化、覆盖率变量和训练期插补后，每个场所×网格均保留 14,400 个测试中心。三层股票历史联合起来仍未改善 SPY 的下一秒预测，与逐股 ETF→股票先行构成方向性一致的早期证据；但 high/mid/low 删除结果没有稳定巨头排序。该文件用于假设生成，不改写五秒确认性裁定。
- **最新实际结果：[原生逐笔解释与分支裁定](20260922_native_tick_interpretation/results/RESULTS.md)**：18 个已购 DBN 已按原生主动买/卖、50µs–60s horizon 和共同五分钟格完成重算。AAPL 的绝对 excess 在四格中三格增加，但每千笔股票率四格均下降；报价响应在 2 月、8 月、方向和场所间不稳定，XOM 无共同支持格。独立原始数据复算为 `PASS_WITH_LIMITATIONS`。决定 `METHOD_ONLY_STOP_THIS_BRANCH`：保留方法模块，停止自动扩张同三事件；这不终止 ETF–股票价格发现研究问题。
- **本轮执行规格：[逐笔 pilot 解释与下一样本裁定 prompt](20260922_native_tick_interpretation/NEXT_EXECUTION_PROMPT.md)**。该规格因发现绝对 excess 与股票交易分母增长相反、旧五分钟格内比较未实现而建立；现已执行完毕，结果以上一条为准。它取代下条“直接扩权重×财报面板”的后续建议，不改写历史计数或旧独立复算。
- **最新实际结果：[有限逐笔机制试点](20260922_native_tick_results/RESULTS.md)**：18/18 个 XNAS/ARCX `mbp-1` 请求、12,298,752 条原生记录已经计算；原生方向优先、严格前序 midpoint 补缺和独立复算已纳入。AAPL 在 RTH 与普通日均有稳健的同向近同步交易及后续报价响应，但两个普通对照日的每千笔 excess 都高于相应财报后 RTH；XOM 近乎为零，公告分钟稀疏或时钟敏感。决定为 `COACTIVITY_ONLY`：测量工程可用，但三事件不支持财报特定、ETF 主导或集中度因果机制。唯一下一行动是用这套代码做一个预声明的“权重/集中度 × 财报日/匹配普通日”较大 RTH 面板，而不是继续购买同三事件窗口。
- **本轮已执行规格：[有限逐笔机制试点 prompt](20260922_native_tick_pilot/NEXT_EXECUTION_PROMPT.md)** 与[参考信息核查](20260922_native_tick_pilot/REFERENCE_CHECK.md)。原生 `mbp-1`、两证券/双场所、公告/RTH/普通比较窗口和范围计数均按规格保存；实际结果以上一条目录为准。
- **同日追加：[Ernst participant/SIP 时间戳核查](20260922_one_second_design/ERNST_TIMESTAMP_ADDENDUM.md)**：其20微秒同步检验使用 participant、不用 SIP timestamp。一秒稿尚未执行；先核对逐笔 trades/mbp-1 与源时钟，一秒仅保留为粗诊断。Databento ts_recv 不能当 SIP 时间。
- **最新准备、尚未执行：[一秒报价与价差诊断 prompt](20260922_one_second_design/NEXT_EXECUTION_PROMPT.md)**，及[文献方法对照/解释修正](20260922_one_second_design/LITERATURE_AND_MEASUREMENT.md)。复用两次 AAPL 和一次 XOM 的已有 bbo-1s，分别计算 bid/ask/mid、价差与相对检测时刻。修正：lag0 不是领先时长上界；同秒同步不否定 ETF 信息作用；bbo-1s 快照间隔不等于精确报价年龄。新准备不改变下述历史计算数字，不代表秒级检验已运行。
- **最新实际结果：[ETF／完整滞后篮子时序决定](20260922_etf_basket_timing_decision/RESULTS.md)**：六事件、七时钟变体、双场所和双时间网格已完成，独立 reviewer 从 SCC 原始 holdings/DBN 复算关键结果一致。两个 AAPL 财报和 MSFT 通知窗口在四种设定下均为一分钟 lag 0；四个 XOM／UNH 变体受场所、网格或陈旧报价影响，无稳定 ETF-leading 或 basket-leading 结果。决定为 `ADVANCE_BOUNDED_RESEARCH`，仅用现有数据做一次一秒级反应起点检验；失败即停止“谁领先”的主叙述，不再自动购数或扩事件。
- **本轮已执行 prompt：[一次完成 ETF／篮子时序检验并作决定](20260922_six_event_observed_paths/NEXT_EXECUTION_PROMPT.md)**。以同六日期整体滞后篮子／SPY 比较为主，ETF-implied issuer 为误差放大诊断；实际产物与最终决定见上一条。

- **2026-09-22 最新实际结果：[固定六公告 SPY／发行人路径](20260922_six_event_observed_paths/RESULTS.md)**：六事件、四发行人、六日期和七个时钟变体均已取得 XNAS/ARCX 共同路径；八个精确 Databento 窗口报价合计 $0.015461。独立 Sol/high reviewer 从 SCC 原始 DBN 复算 52 个可用关键单元，数值完全一致，并修复 7 月越过 archive 结尾携带报价及重复路径假斜线。AAPL、UNH 等窗口的滞后权重×发行人变动已能解释 SPY 同期变动的较大部分，说明幅度分离本身不能证明谁主导价格发现。下一步是在同六日期构造预声明的 rest-of-SPY 代理与 ETF-implied issuer component，先检验可比经济成分的时序。
- **本轮执行 prompt：[固定六公告路径比较](20260921_xom_spy_observed_paths/NEXT_EXECUTION_PROMPT.md)**：bid/ask/mid、跨价差区间、文件边界、双场所对照、静态报告权重量级和独立复算均已完成。历史 prompt 保留为执行规格，实际最终产物以上一条目录为准。
- **最新实际结果：[XOM/SPY 单事件可观测路径](20260921_xom_spy_observed_paths/RESULTS.md)**：SCC 已直接读取既有四个 venue 的 bbo-1s；独立 reviewer 从原始 DBN 复算关键端点。06:30 ET 锚点下，XNAS +5 分钟 SPY 为 −8.65bp、XOM 为 −241.19bp；ARCX 方向一致。六股滞后代理只占报告 `percent_tna` 约 2.10%，且基准价值 67.62% 来自 XOM；剔除 XOM 的五股诊断 +5 分钟为 −15.64bp，不能代表完整篮子。工程测量可行，但单事件和低覆盖代理不能裁定价格发现。下一步改为固定六公告的 SPY/发行人股票有限复现，不再等待同一历史持仓缺口后才出结果。
- **本轮已执行 prompt（按用户要求去掉程序性冻结）：[固定 XOM/SPY 可观测路径](20260921_spy_xom_event_packet/NEXT_EXECUTION_PROMPT.md)**：两证券路径、可用滞后股票子组合和独立复算均已完成，实际产物见上一条。取消事前 reviewer 放行、release 文件、多层哈希及单独规格审批没有妨碍必要的数据质量检查；历史 HOLD 文件仍作为历史记录保留，不阻塞本轮诊断。
- **最新执行：[XOM × SPY 单事件 Stage-A 包](20260921_spy_xom_event_packet/DECISION.md)**：最终 SCC 脚本与输出已绑定，并由独立 Sol/high 代理用第二套 metadata-only 程序复算。裁定为 `HOLD_NAMED_INPUT`：现有 CRSP 仅给出 2022-12-31（`eff_dt=2023-01-09`）和 2023-01-31（`eff_dt=2023-02-07`）月度快照，不能证明 2023-01-31 06:30 ET 的实际 SPY 持仓或申赎篮子。XOM 精确 CUSIP/季度期间可定位，但 PIT 共识单位仍未准入。没有读取预测、EPS 或报价数值，没有购数或 Stage-B release。唯一下一输入是 State Street 当日历史 holdings/portfolio-composition/cash 文件及可用时间证据；滞后持仓代理只能作为待批准的规格修订。
- **最新执行：[系统性 pilot 支持阶段](20260921_systematic_pilot/README.md)**：已取得绑定正确 32 事件名单的 SCC 持仓汇总、六公告时钟证据、独立数值修复检验和 29 个已有报价文件的实际端点诊断。[科学决定](20260921_systematic_pilot/DECISION.md)仍为 HOLD_DATA + HOLD_MEASUREMENT，不是假设通过或失败、功效通过或研究 GO。旧名单误绑定汇总已作废，接手者以新目录机器生成 receipt 为准。
- **最新续作：[六公告来源定位与组间比值区间](20260921_ratio_continuation/README.md)**：SCC 连接正常但既有记录未给出所需历史源位置；新增联合区域保守投影的提案代码，不等于真实数据推断或研究 GO。此目录保存实际执行与独立审查记录。
- **本轮执行：[新闻—ETF—真实篮子 readiness](20260921_news_basket_readiness/README.md)**。已运行元数据回执再计数和合成方法实现；不是新经验结果。最终状态与下一行动见[决定](20260921_news_basket_readiness/DECISION.md)，独立复核见该目录报告。
- **先读：[新方向始末与接手说明](20260921_price_discovery_method/RESEARCH_HANDOFF.md)**。当前为 `HOLD_CONTRIBUTION_AND_EMPIRICAL_VALIDATION`，不是实证通过。
- [本轮所执行的 prompt（含模型/effort 分工）](20260921_price_discovery_method/NEXT_EXECUTION_PROMPT.md)：原始文件保留提交时状态；用户随后已批准执行，实际委派、产物及边界记录在 readiness 目录。不自动打开响应值。
- [文献贡献定位](20260921_price_discovery_literature/CONTRIBUTION_ASSESSMENT.md)与[方法原型/测试](20260921_price_discovery_method/README.md)：保留导师的价格发现问题，但宽泛 ETF/个股领先、权重效应与信息分解不是新贡献。原型及合成测试不能证明实际样本可行。
- [已完成的 H2 冻结检验](20260921_same_industry_replication/DECISION.md)：`INCONCLUSIVE_STOP_SPENDING`，停止共同持仓/两日反应路线的自动扩样与购买。
- [信息质量方向的定位执行与 SCC 字段核查](20260921_information_quality_repositioning/DECISION.md)：`HOLD_CONTRIBUTION_AND_MEASUREMENT`。通用 bellwether/ETF 信息外溢不是新贡献；新的独有信息质量命题尚未冻结或运行。只核查了文献、文件与 footer，没有新财务值/收益访问。
- [未完成：I/B/E/S 历史时点与值口径裁定](20260921_ibes_pit_semantics/未完成.md)：2026-09-21 按用户要求暂停，保留全部已有工作，未完成独立复核。下一步先讨论 ETF 与个股谁完成价格发现的研究定位，不自动执行新分析。旧计划与报告保留为历史，不能把它们的执行授权当作新定位已经通过。

## 历史入口

- [研究计划](20260920/RESEARCH_PLAN.md)
- [第一阶段实际结果](20260920/execution/RESULTS.md)
- [第一阶段执行记录](20260920/execution/EXECUTION_RECEIPT.json)
- [第二阶段进展](20260920_phase2/PROGRESS.md)
- `ARCHIVE_MANIFEST.json`：迁入文件的来源、大小、校验值及迁入一致性。

`20260920/` 保存原 `p1/concentration_information_plan/20260920/` 的完整研究文件副本，逐文件一致性记录在清单中。按用户要求，GitHub 是此目录的交接入口；远端确认成功后可以清理本地重复旧副本，不改写其 receipts。新代码、修复与报告从本目录继续。历史文件中的 SCC 路径仍然有效，不能因本地目录调整重新生成或替换原始数据。

许可行级研究数据继续只留 SCC：

`/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/derived/p1_concentration_information/20260920/`

后续阶段使用独立 SCC 子目录，不覆盖第一阶段结果。这里保存代码、配置、聚合结果、公开来源及执行记录，不保存密钥、许可逐行数据或原始报价。

当前没有效果、经验功效或因果 GO 结论。本次用户明确要求保存到 GitHub：只提交本方向文件到既有 `task/p1-feasibility-adjudication-20260913` 分支，不合并 main，不提交其他项目的未跟踪文件。
