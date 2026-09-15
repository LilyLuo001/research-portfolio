# P1 数据与研究准备状态检查清单（Sol）

日期：2026-09-14  
本轮角色：按用户要求使用 Sol / High 做事实核对；实际运行模型/推理强度遥测 **NOT_OBSERVED**。  
范围：只回答“原来要求做什么、现在做了什么、还没做什么”。本报告不提出新的研究执行计划，不做实证功效结论，不打开 POST 行情，不发起新购买。

## 状态定义

- **ACQUIRED**：文件已实际取得，并有清单/哈希/结构性收据。
- **MEASUREMENT_PARTIAL**：已完成有限的 PRE-only 测量或元数据核对，但不足以认证最终研究对象。
- **NOT_RUN**：需要的构造、估计或检验尚未运行。
- **NOT_CERTIFIED**：有候选记录或日期，但关键语义、时钟、成员资格或因果用途尚未得到认证。

## 一、固定 8 股票 / 32 事件订单

| 原要求 | 当前状态 | 已有证据 | 仍未完成 / 不能据此声称 |
|---|---|---|---|
| 使用 W002（Dimensional）与 W016（Bridgeway）两次转换 | **ACQUIRED** | `conversion_cohorts.csv` 固定两波；订单按这两波执行 | 这两波并未因此成为可识别的因果样本 |
| 8 只指定股票，每只 2 个 PRE-focal、2 个 POST-focal，共 32 个公告日 | **ACQUIRED** | `securities.csv` 8 行；`earnings_events.csv` 32 行；每波 PRE 8、POST 8 | “PRE-focal”只表示早于实施日，不等于严格早于公开公告，也不等于未受其他转换影响 |
| XNAS.ITCH / bbo-1s 的股票与 SPY 分段行情 | **ACQUIRED** | 冻结选择共 374 个请求/原生文件，结构性下载全部完成；核心 32 事件映射完整 | XNAS 是 Nasdaq 场内 BBO，不是 SIP NBBO；下载完成不等于六个研究时点都有有效双边报价 |
| 4 个 PRE 窗口的 XNAS mbp-1 验证 | **ACQUIRED** | 8 个 mbp-1 文件（4 只股票及对应 SPY）已下载 | 原交付中的“100% BBO/MBP 匹配”没有有效双边状态分母，且未按 publisher/instrument 键控，不能作为最终有效性认证 |
| 限量 ARCX.PILLAR / bbo-1s 场所敏感性 | **ACQUIRED** | 8 个 ARCX 文件已下载 | 只是第二场所样本，不构成全国最优报价，也未完成重新计算后的跨场所有效状态指标 |
| 可选 IWM、DFAC、BSVO 包 | **ACQUIRED** | 冻结 374 请求中包含完整 optional ETF bundle | POST ETF 内容仍封存；不能用于处理效应或 ETF 领先性结论 |
| 控制花费 | **ACQUIRED** | 报价/预留 gross usage 为 `$1.578307747849`，低于上限；原下载在既有 credit 授权下完成 | 本次检查没有新增消费；当前环境没有可用 Databento key，本报告不请求密钥、不发起新订单 |
| PRE 与 POST 访问隔离 | **ACQUIRED** | POST 文件保持 sealed；本轮 PRE 测量脚本只读取 PRE 映射窗口 | 没有打开任何 POST 报价、响应曲线、处理系数或处理后选模结果 |

## 二、固定订单的测量核对

| 核对项 | 当前状态 | 已有证据 | 仍未完成 / 不能据此声称 |
|---|---|---|---|
| PRE 映射腿可解码性 | **MEASUREMENT_PARTIAL** | 192 个 PRE map-leg 分母中实际解码 176 个；另外 16 个因物理文件混有 sealed/archive 内容而明确不解码，不能记作零覆盖 | 尚不是 192/192 的可分析覆盖；混合文件隔离问题未改变 |
| 事件股票与 SPY 同步固定时钟覆盖 | **MEASUREMENT_PARTIAL** | 56 个可解码 stock+SPY leg pairs；按腿同步覆盖：D−1 92.4%、D 80.6%、D+1 82.0%、D+2 93.4% | 这些是固定市场时钟，不是实际公告时钟；不能转化为 5/15/30/60 分钟事件响应覆盖 |
| 一秒 BBO 状态重建 | **MEASUREMENT_PARTIAL** | 5,227,200 个固定端点；4,877,315 个双边有效；2,378,084 个端点直接有效；2,499,231 个由先前状态 carry；202,344 个首条记录前缺失；147,541 个未定义/零边状态 | carry 规则和缺失状态已可审计，但还没有认证为最终 P1 outcome 构造 |
| 原生字段是否因 `None==None` 假匹配 | **MEASUREMENT_PARTIAL** | 新 PRE-only 审计直接测试了 2,231,698 条记录的 level-0 字段，0 条不可读，存在 `levels[0]` fallback，未发现 publisher/instrument 流异常 | 这排除了“所有字段都是 None”的具体怀疑；不等于旧 100% 匹配统计本身已经被重新认证 |
| 精确 earnings release clock | **NOT_CERTIFIED** | 32/32 在订单中均标记 `NOT_CERTIFIED_BY_THIS_ORDER` | 未验证公告时间、时区、精度、公开发布来源；不能划分合同要求的 RTH / non-RTH |
| 六个共同 horizon 的 live-quote mask | **NOT_RUN** | 当前只有日期宽窗及固定时钟覆盖统计 | 5m、15m、30m、60m、close、+1d 的共同有效支持尚未按真实公告时钟构造 |
| POST 测量或处理比较 | **NOT_RUN** | POST 原生文件存在但未解码 | 没有 PRE/POST 曲线、处理差异、回归或结果驱动的规格选择 |

## 三、固定 8 股票是否已经构成 P1 高/低暴露设计

| 研究要求 | 当前状态 | 已有证据 | 仍未完成 / 不能据此声称 |
|---|---|---|---|
| 严格 PRE-announcement ownership | **NOT_CERTIFIED** | 固定 8 只股票都能在 PRE-effective 前身持仓中定位 | `securities.csv` 的 8/8 都是 `pre_announcement_membership=NOT_CERTIFIED`；现有 E007 快照 W002 为 2021-04-30、W016 为 2022-12-30，均晚于现有公告证据 |
| W016 公告时钟 | **NOT_CERTIFIED**（日期事实已加强） | SEC adviser FAQ 表明转换提案已于 2022-08-26 在线公布；因此 2022-12-30 E007 快照确定是公告后 | 仍需把精确来源、最早可能时点和 package rule 写入最终签署时钟；当前 E007 不能作为 PRE-announcement dose |
| W002 公告时钟 | **NOT_CERTIFIED** | 本地事件资料已给出不晚于 2021-03-03 的构成基金日期；另有 2020-11-17 公共计划证据正在钉住 | 尚无最终 package-level 最早公开时点；无论使用 2021-03-03 还是更早日期，2021-04-30 E007 都不是严格 PRE-announcement |
| 高/低 tercile 成员资格 | **NOT_RUN** | `securities.csv` 的 8/8 均为 `analysis_tier=NOT_ASSIGNED` | 没有用严格公告前持仓对完整合格总体分层，也没有已签署的最终 tier 规则 |
| 仅作诊断的 E007 旧时钟分层 | **MEASUREMENT_PARTIAL** | W002 固定样本：ORCL low、MSFT low、JJSF middle、PLXS high；W016：AROC middle、BHE middle、AXL high、SKYW high | 这些分层来自公告后快照，不能升级为处理组；W016 固定样本甚至没有 low，因此当前 high×post 对比在组别上缺项 |
| 其他转换重叠 / clean comparison | **NOT_CERTIFIED** | 32/32 事件在订单中均标记 `other_conversion_cleanliness=NOT_CERTIFIED` | 完整 `[A_w-24m,A_w+24m)` 转换日历和逐 stock-wave 排除尚未构造 |
| 真实 SUE | **NOT_RUN** | SCC 已确认所需实际值、分析师明细、CRSP 日收益和 shares-history 的 2019–2024 源/schema 存在 | 未读取本轮研究所需 financial values；未构造 90 天内最新预测、中位数、至少 2 位分析师、币种/每股口径一致性及公告前缩放 |
| 实际设计矩阵与秩 | **NOT_RUN** | 事件、股票、波次的采购标识存在 | 行业×季度、stock-wave 斜率、SUE 交互、共同 calendar support 尚未合并；不能报告真实 rank |
| 依赖组件与推断 | **NOT_RUN** | 两个公开 adviser 标签可描述为两个 sponsor proxies | 未构造 unique-event / shared-stock / signed-sponsor / response-date 图；一秒记录、多个 horizon 与重复 stack 不是独立事件 |
| 实证功效 | **NOT_RUN** | 无 | 没有通过真实估计器得到的 PRE 协方差、残差化信息或可辩护 MDE；本报告不以简单行数公式代替实证功效 |

## 四、原“5 package / 40 stock-wave / 最多 480 associations”决策试点

| 原要求 | 当前状态 | 已有证据 | 仍未完成 / 不能据此声称 |
|---|---|---|---|
| 四个 main packages：W002、W013/DVAL、W021/JPEF、W025/Fidelity；W016/BSVO 单列 stress | **MEASUREMENT_PARTIAL** | E007 中五个旧 wave/date bucket 都存在；各自有不同 raw adviser label；W016 已在固定订单中出现 | 当前实际行情订单只有 W002 与 W016；W013、W021、W025 没有进入固定采购。raw adviser 文本不是 signed economic sponsor |
| 每波 4 high + 4 low，共 40 stock-wave units | **NOT_RUN** | 旧时钟 E007 在五波均有足够正暴露尾部候选：W002 846/845、W013 39/38、W016 181/180、W021 13/13、W025 316/315（low/high） | 这些是公告后快照上的旧时钟数量；没有严格公告前 ownership 重建，没有最终 40 名单 |
| 每 tier 按公告前流动性再分上下半组 | **NOT_RUN** | CRSP 日度数据源/schema 已确认存在 | 未计算冻结的 PRE-announcement 流动性窗口、未生成 selection rank |
| 每 stock-wave 取 8 个 PRE-announcement + 4 个 POST（实施后至少 20 sessions） | **NOT_RUN** | 固定订单只提供每只 2 PRE-focal + 2 POST-focal | 目标最多 480 个 associations 未构造、未报价、未采购；当前只有 32 个采购 associations |
| 五波公告前 N-PORT 历史 | **MEASUREMENT_PARTIAL** | 本地缓存审计只读了 810 个 XML 的 `genInfo`；五个旧波共 13 个前身 series 均有 2019 年起的缓存历史。W016 有 12 份早于 2022-08-26 的报告，最近为 2022-06-30 | 尚未读取/重建持仓明细、拆股一致 shares、分母或 `D_iw`；缓存存在不等于合格 ownership 已完成 |
| W021/JPEF package identity | **NOT_CERTIFIED** | W021 旧 effective-date bucket 同时含 Equity Focus Fund 与 Limited Duration Bond Fund | 不能因同一旧 wave/date 就把债券前身并入 JPEF 股票暴露或共用时钟；named JPEF membership 尚需逐 fund 解析 |
| 精确 earnings 元数据覆盖 | **MEASUREMENT_PARTIAL** | SCC v2 元数据脚本修复旧 Python 日期解析后成功；固定 8 股票 31/32 个公开订单日有同日 source hit | AROC 2023-11-01 没有同日 hit，仅见相邻日记录；CUSIP/date match 未认证经济事件或公告来源；时区/session 仍未知 |
| 事件中心报价窗口与真实 horizon | **NOT_RUN** | 固定订单采用 D 日及相邻日的大窗口，确保先买到数据 | 原决策试点的 release−20/+70、首个反应开盘、前收盘/当日收盘/+1d 收盘窗口没有按认证事件时钟编译 |
| 首选 consolidated quote，或固定三场所 XNAS+ARCX+XNYS | **NOT_RUN** | 实际固定试点取得 XNAS，并对 4 个 PRE 事件做有限 ARCX 验证 | 没有 consolidated product；没有固定三场所全样本；XNYS 未采购 |
| PRE 稳定性、实际估计器、package sensitivity、精度与路线判断 | **NOT_RUN** | 当前 PRE-only 只有测量覆盖与固定市场时钟描述统计 | 没有按真实 SUE/时钟/组别/固定效应运行的 P1 估计、pre-block stability、leave-package-out 或功效投影 |
| 独立 stock–ETF measurement component | **NOT_RUN** | 固定订单仅含 IWM/DFAC/BSVO 的有限窗口 | 原计划的 AAPL/MSFT–XLK、JPM/BAC–XLF、UNH/PFE–XLV 及 8 个 FOMC 窗口未执行；本清单不把它复活为当前替代研究 |

## 五、数据源与历史材料状态

| 项目 | 当前状态 | 证据 / 限制 |
|---|---|---|
| E007 exposure roster | **MEASUREMENT_PARTIAL** | 8,801 个 positive/primary-ready stock-wave rows、3,440 PERMNO、30 个旧波；这是 effective-date roster，不是严格公告前分析总体 |
| IBES 公告元数据投影 | **MEASUREMENT_PARTIAL** | 103,876 source records；96,573 有公告日有效的 seed link；不是 unique economic-event count，不提供已验证时区/session |
| IBES actuals / detail forecasts、CRSP dsf / dseshares | **ACQUIRED**（源/schema 存在） | SCC inventory 已确认 2019–2024 分区与字段；本轮未读取 financial values |
| 历史 N-PORT 本地缓存 | **ACQUIRED**（缓存文件存在） | 已做 genInfo-only 元数据审计；没有读取 holdings rows，没有 ownership reconstruction |
| `P1_documents_bundle.zip` | **ACQUIRED**（历史资料） | 7 个历史文件：旧 DECISION/review/data-review/minimum-request/delta-review，加 index-rebalancing plan/PDF。它不是新的执行授权，旧 free-parquet 口径不能替代 E007，也不能触发另一个研究分支 |
| 新采购 / POST 访问 | **NOT_RUN** | 本次清单没有新消费，没有读取 POST 报价，没有读取 raw financial values |

## 结论性对账

- **已经做完并可核对的**：固定 8 股票/32 事件订单的原生文件采购、预算收据、访问隔离、PRE-only 字段可读性与有限固定时钟覆盖审计；SCC 和本地缓存中相关源/schema/历史文件是否存在的核对。
- **只做了一部分的**：PRE quote 测量、固定订单日期与 IBES source-record 的匹配、五个旧波的公告/持仓缓存可用性、E007 旧时钟暴露尾部数量。
- **还没有运行的**：严格公告前 ownership 重建、最终 high/low 与流动性分层、5-package 40-unit 名单、最多 480 个 earnings associations、真实事件时钟/session、SUE、实际设计矩阵/rank、依赖图、PRE 稳定性、处理估计和实证功效。
- **尚未认证的**：固定 8 股票的 P1 组别身份、RTH 资格、clean overlap、市场范围可比性，以及任何 MF→ETF 因果或 timing 结论。

## 主要证据文件

- `delivery/DOWNLOAD_MANIFEST.csv`, `PILOT_COVERAGE.csv`, `SELECTION_RECEIPT.json`, `COST_RECEIPT.json`
- `evaluation_20260914/measurement/MEASUREMENT_FINDINGS.md`, `measurement_summary.json`
- `evaluation_20260914/scc_metadata_readiness_receipt.json`
- `evaluation_20260914/cached_filing_metadata_receipt.json`
- `securities.csv`, `earnings_events.csv`, `PILOT_DATA_ORDER.md`
- reconciled candidate contract: `research-portfolio-p1-feasibility-20260913/p1/feasibility_adjudication/20260913/reconciliation/estimation_contract.reconciled.PROPOSED.yaml`

