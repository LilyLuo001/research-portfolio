# 两篇计划的文献边界与数据来源

日期：2026-09-23。用途：提供来源、已知重叠、阅读程度及需要继续核实的问题。不是系统综述、不是不存在其他相关论文的证明，也不是独立referee PASS。

下述金融文献与数据页面已在本对话2026-09-23方向评估阶段检索/阅读；本次计划编写复用该证据，不虚称逐篇全文精读。旧价格发现文献的精确版本和读取层次另见[20260921贡献定位](../20260921_price_discovery_literature/CONTRIBUTION_ASSESSMENT.md)。

## 1. 最近邻及本系列必须超过的内容

| 文献/来源 | 已核实的相关内容 | 本系列不能冒称的贡献 | 阅读层次 |
|---|---|---|---|
| [Ernst, Stock-Specific Price Discovery From ETFs，2020作者稿](https://www.mit.edu/~ternst/docs/jmp.pdf)；旧档案另存2022版本定位 | 公司特有信息可以通过ETF交易表达；权重相关异质性 | ETF含公司信息、大权重更强不是新命题 | 本次检索摘要；旧档案有2022稿相关方法段落；本次2022直链失败，不冒称重新读完 |
| [Box等，Intraday arbitrage between ETFs and their underlying portfolios](https://www.sciencedirect.com/science/article/pii/S0304405X21001537) | ETF/底层日内动态、套利及领先关系 | 平均先后、换频率或换年份本身不够 | 沿用旧档案的出版方摘要/方法片段，本次直开失败 |
| [Kosar & Mikhalishchev，Inattentive Price Discovery in ETFs，2022工作论文](https://www.cerge-ei.cz/pdf/wp/Wp735.pdf) | 公司消息、权重、新闻拥挤及底层关闭时的ETF响应 | 不能把权重或注意力异质性直接叫新贡献 | 本次读取摘要、引言、理论及设计定位；非全文复核 |
| [Cespa & Foucault，Illiquidity Contagion and Liquidity Crashes，RFS 2014](https://academic.oup.com/rfs/article/27/6/1615/1596760) | 跨资产价格学习能联系流动性与脆弱性 | 信息连接与流动性传染的联系已有理论 | 出版方摘要；正式方法使用前需读模型条件 |
| [Ben-David、Franzoni、Moussawi，Do ETFs Increase Volatility?](https://www.nber.org/papers/w20071) | ETF持有、套利和底层波动；NBER页面列2018 JF发表版 | ETF传播交易冲击/波动不是新现象 | NBER摘要与发表信息；不把2014稿数字当所有样本通用参数 |
| [Rappoport & Tuzun，Arbitrage and Liquidity，FEDS 2020-097](https://www.federalreserve.gov/econres/feds/files/2020097pap.pdf) | ETF/底层流动性、价格偏离及套利效率；使用TAQ、TRACE、篮子等 | 仅把价差和折价做VAR不够；偏离不等于AP已失败 | 摘要、引言、机制及数据章节，非全文复现 |
| [Pan & Zeng，ETF Arbitrage under Liquidity Mismatch，2017会议稿](https://conference.nber.org/confer/2017/LTAMs17/Pan_Zeng.pdf) | 公司债ETF、细粒度AP数据、库存与套利冲突 | 不能把债券流动性错配直接搬成SPY资本约束结论 | 摘要与机制/数据定位；不用页面抓取日期冒充论文年份 |
| [Fixed income ETFs: Primary market participation and resilience of liquidity during periods of stress，2020](https://www.sciencedirect.com/science/article/pii/S0165176520301725) | 独特一级市场交易数据；部分压力期替代参与者进入 | 不允许预设所有AP同时退出 | 出版方摘要、数据及结论片段 |
| [Gabaix & Koijen，Inelastic Markets Hypothesis](https://www.nber.org/papers/w28967) | 总体股票市场需求弹性与资金流乘数 | 不是任意ETF流入/流出通用5倍，更不是毫秒订单簿乘数 | NBER摘要及论文介绍；不作为本系列主估计方法 |
| [Small、Wansley等，Security Concentration, Adverse Selection Costs and Liquidity](https://aquila.usm.edu/fac_pubs/21499/) | 已有ETF证券集中度与流动性相关研究 | “集中度影响价差”不能未经核查称空白 | 机构库书目记录；研究设计及结论待全文核实 |
| [Liquidity spillover between ETFs and their constituents](https://www.sciencedirect.com/science/article/abs/pii/S1059056023002198) | 出版方摘要涉及压力/高波动状态下流动性溢出 | 正常与压力时段对比本身不够 | 出版方摘要，不声称完整方法核实 |

未来针对第一篇优先精读最接近的跨市场价格发现、流动性替代及渠道中断研究；第二篇再补组合执行/交叉冲击。限制到改变研究设计的论文，不重开全领域综述。每个新增来源标注版本、读取层次和实际支持的命题。

## 2. 商业数据可以拓宽设计，但不能偷换对象

| 来源 | 官方可支持的产品事实 | 尚需核实的事项 |
|---|---|---|
| [NYSE Daily TAQ](https://www.nyse.com/data-products/catalog/daily-taq) | 提供美股市场成交/报价历史 | 具体年份、参与者/SIP时钟字段、条件码、历史修订、许可和交付；不等于所有交易所的完整MBO |
| [Databento MBP-1](https://databento.com/docs/schemas-and-data-formats/mbp-1) | L1最优档，含最优买卖价格、数量和相关事件 | 数据集语义、市场范围、时钟与历史schema覆盖；L1不能恢复前五档 |
| [S&P Global Exchange Traded Products](https://www.spglobal.com/market-intelligence/en/solutions/etp) | 创建、赎回、跟踪、持仓篮子信息产品 | 历史版本、基金范围、现金项和计量单位、字段时间；篮子内容不是实际申赎订单 |
| [CRSP Mutual Funds Guide](https://www.crsp.org/wp-content/uploads/guides/CRSP_US_Mutual_Funds_Guide_Sift.pdf) | 文档区分daily NAV/return与monthly等字段 | 不能自动假设SCC镜像含全部ETF的日度份额/实际流量；本次仅读字段说明，不新增WRDS连接 |
| [SEC Form 13F数据](https://www.sec.gov/data-research/sec-markets-data/form-13f-data-sets) | 机构管理人持仓披露 | 不是基金级主动/被动标签，不含完整AP跨市场库存 |

不报告报价或购买状态；此文件仅为来源路线。用户允许更广商业数据，不等于已拥有每份产品、已同意新供应商协议，或可以买到监管受限的逐参与者记录。

## 3. 防止错误叙述回流

- [SEC ETF说明](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-24)：二级交易与一级申赎不同。AP、做市商和其他套利者不能自动合并成一个人。
- [SEC 2015-08-24市场报告](https://www.sec.gov/marketstructure/research/equity_market_volatility.pdf)：SPY相对前收盘的跌幅不能当NAV折价；不能引用AI材料中的“SPY 10%–20%折价”作为事实。
- [SEC ETF交易暂停研究](https://www.sec.gov/about/divisions-offices/division-economic-risk-analysis/staff-papers-analyses/feb2016-dera-white-paper-etf-volatility)：成交需求与流动性供给等多因素有关，不可简化成所有AP都因VaR触顶离场。
- 股票价格上涨时市值权重可随既有持仓价值自动调整，不推出市值加权基金必须新增买入；申赎、再平衡与价格影响分开建模。
- 下一秒G不显著/为负，不证明价格完全有效、ETF无信息、AP资本约束是唯一风险或现有方法已经成为学术标杆。

## 4. 委派来源与实际能力

本次已调用官方文档搜索及读取 [Codex subagents](https://developers.openai.com/codex/subagents)。文档说明可继承或显式选择模型/effort；它不是本机执行遥测。本会话工具目录支持计划使用的 `gpt-5.6-sol`、`gpt-5.6-terra`、`gpt-6-astra` 及所列effort。网页默认建议不覆盖本用户沿用的型号，也不授权修改config或认证。

计划中的角色在本次均未启动。执行时记录请求、工具接受结果和可见实际设置，无法观察写 `NOT_OBSERVED`；没有独立代理就不能写独立review PASS。
