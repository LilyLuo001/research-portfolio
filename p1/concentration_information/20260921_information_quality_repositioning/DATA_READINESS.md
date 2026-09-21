# 实际数据定位与尚未通过的条件

证据分层：本轮 SCC footer 实测 > 历史已执行 receipts > 数据 manual 的概括。当前 canonical raw 根目录为 `/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw`。

## 本轮已执行的内容

只对 raw 根目录及 maximal/rescue/rescue_remaining 的直接子文件进行限定模式查找，读取匹配文件的 schema、物理行数和大小。未递归扫描、未读取任何数据列或行、未访问 footer 数值统计、未写远端文件。SCC 运行 Python 3.12.4 模块，脚本退出码 0。

| 家族 | 本轮文件数 | 已观察的文件名年份/结构 | 可用性含义 |
| --- | ---: | --- | --- |
| comp_fundq | 34 | direct 17 个 + rescue allcols 17 个，2010–2026 | 两个版本并存，不得拼接；实际行日期和公开日期未核查 |
| comp_funda | 34 | 同样两套，2010–2026 | 年度辅助数据定位完成，不作为季度替代 |
| CCM 名称匹配 | 5 | linktable、lnkhist、lnkrng、lnkused | 不是五套可叠加的同义链接；需选择语义正确的一个版本 |
| 直接版 I/B/E/S detail EPS | 15 | ibes_detu_eps_2012…2026 | 文件存在，不是完整日期覆盖或 analyst coverage 的结论 |
| 直接版 I/B/E/S actual EPS | 15 | ibes_actuals_eps_2012…2026 | 文件存在，不是唯一公告或首次发布值的结论 |

2023 文件的物理行数实例：`comp_fundq_2023.parquet` 50,690；`rescue/comp_fundq_allcols_2023.parquet` 也为 50,690；`ibes_detu_eps_2023.parquet` 1,260,016；`ibes_actuals_eps_2023.parquet` 28,468。相同行数不是内容相同证明；没有相加为样本量。

## 字段存在与语义状态

| 必需概念 | 本轮实际观察字段 | 状态/阻碍 |
| --- | --- | --- |
| 季度主体与财政期 | gvkey, datadate, fyearq, fqtr, fyr | 存在；非日历季，不能仅按年份文件名合并 |
| 季度基本面目标/尺度 | ibq, atq, saleq, epspxq, ajexq | 仅字段名可见；值未读，披露版本与调整基准未验证 |
| Compustat 公开/处理时间 | rdq；allcols 另有 pdateq, fdateq, finalq, updq | 存在不等于保存原始发布时值；不能凭这些字段宣称 point-in-time |
| 有效期证券—公司链接 | gvkey, lpermno, lpermco, linkdt, linkenddt, linktype, linkprim | linktable/lnkhist 实际存在；一对多与有效期尚未计数 |
| 分析师/预测期 | analys, estimator, ticker, cusip, fpedats, fpi, measure | 直接版 detail 存在；analyst 是数值型标识，需防小数/缺失处理及重复覆盖 |
| 预测日期与激活时间 | anndats, anntims, actdats, acttims | 存在；时间含义及可用时点需 source-specific 裁定，不猜时区 |
| 预测/实际值口径 | detail 有 value,curr；actual 有 value,pends,pdicity,measure | 不构造差额；actual 的所查 schema 未见 curr，不能默认为同币种/同调整口径 |

完整机器证据：[SCC_FOOTER_PREFLIGHT.json](SCC_FOOTER_PREFLIGHT.json)。该文件 schemas 为 relevant-field signatures，不是全字段清单；没有出现的其他字段不能被解释成源表绝对缺失。

## 优先源选择（候选，不是静默合并）

- I/B/E/S 起点限定 `raw/ibes_detu_eps_YYYY.parquet` 与 `raw/ibes_actuals_eps_YYYY.parquet` 的 direct 系列。旧 count-only manifest 有实际存在证据，但没有授权或验证预测值使用，也没有证明两系列经济口径一致。
- Compustat 可优先查 allcols 源的版本标志和标准化维度；不得拿 direct 的值与 allcols 的版本字段按行号拼接。必须用完整经济键核实。
- CCM `raw/crsp_ccm_linktable_full.parquet` 已定位；`rescue/crsp_ccmxpf_lnkhist_full.parquet` 是另一个候选版本，不混合。
- CRSP 日频、历史 IBES link 已有旧执行 manifest，本轮不重复读取；对新跨年人口的完整覆盖仍未核实。
- 新人口、实际经济日期覆盖、首次披露值、预测者信息集均是 UNKNOWN，不是 0，也不是 READY。

## 下一项具体操作边界

下一步只裁定 direct I/B/E/S 两系列的历史时点与值口径：优先旧 extraction query/字典/manifest；必要时 SCC 仅投影身份、财政期、measure/fpi/pdicity、currency 元数据及 announcement/activation 日期时间，并只返回聚合缺口。禁止投影 value、EPS、收益；禁止 SELECT *。输出应是一个 source-specific `PIT_SEMANTICS_DECISION.md`（SUPPORTED / UNSUPPORTED / UNRESOLVED）和有限缺口，不再要求 PI 提供程序可构造的股票名单。

语义无法由现存资料验证时，不能用样本值看起来合理代替来源定义。此时只报告哪个定义缺失；不连接 WRDS/LSEG、不买 TAQ 或 Databento 数据。现有报价不能解决财务时点/修订问题。
