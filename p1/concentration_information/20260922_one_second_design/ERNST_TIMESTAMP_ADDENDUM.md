# Ernst 时间戳核查与执行优先级修正

2026-09-22，公开文档核查，未查询账号、下载数据或执行 SCC 分析。用户在一秒 prompt 准备期间要求核对 participant/SIP timestamp 并关注逐笔粒度。本补充优先于 NEXT_EXECUTION_PROMPT.md 的“一秒最终裁定”安排。

## 原文与数据位置

[Ernst 2022-03-22 作者稿](https://terpconnect.umd.edu/~ternst/docs/Ernst_ETF.pdf)第27页（PDF页序）、脚注17明确：同步交易检验用 TAQ participant timestamp，不用 SIP timestamp。其定义是相距20微秒以内的交易；从±1000至±1200微秒窗口估算偶然配对基线，并按窗口长度缩放扣除。论文据样本时期交易所 gateway latency 解释为何近乎同步交易不应是看到另一笔成交后才发起的反应，并排除只有毫秒精度的成交。该规则不是两时间戳相减后挑延迟，更不能把旧20微秒边界未经论证移植到2023年。

[NYSE Daily TAQ v4.0](https://www.nyse.com/publicdocs/nyse/data/Daily_TAQ_Client_Spec_v4.0.pdf)中的同一条 Trades File 记录同时含 Time（SIP发布时间，第1列）与 Participant Timestamp（第13列）；Quotes File 也有 Time（第1列）与 Participant Timestamp（第20列）。这是原始文件列序，不是所有平台的变量名。NYSE/ICE 的 [Daily TAQ](https://www.nyse.com/data-products/catalog/daily-taq)是直接产品入口；本项目没有现成 TAQ/WRDS 访问，不把公开规格当成已获数据。

participant 时间是参与方提供的事件/发布时间，定义随 feed、消息和时期变化；不能无条件称为真实撮合物理瞬间。字段纳秒存储也不保证纳秒精度或跨交易所时钟准确。SIP发布时间也不是所有交易者同时收到信息的时间。

## Databento 对照

- [XNAS.ITCH](https://databento.com/docs/venues-and-datasets/xnas-itch)：官方把原生 TotalView Timestamp 映射到 ts_event；ts_recv 是 Databento capture-server 接收时间，不是 SIP 时间。
- [通用时间戳规范](https://databento.com/docs/standards-and-conventions/common-fields-enums-types)：ts_recv−ts_in_delta 是 publisher sending time；不同源可能没有独立 sending timestamp，故不能普遍把它命名为 SIP timestamp。
- [trades](https://databento.com/docs/schemas-and-data-formats/trades)保留逐笔成交；[mbp-1](https://databento.com/docs/schemas-and-data-formats/mbp-1)保留顶部盘口更新及交易。两者是候选数据，不是已验证的 TAQ 双时钟替代。bbo-1s 不保留完整秒内交易/报价过程。

## 对待执行 prompt 的明确修正

一秒结果保留为低成本可视化和粗分辨率诊断，不能作为停止整个价格发现问题的证据。下一轮先根据现有 receipts/manifest 核对这三个日期的原生 trades/mbp-1 是否已经拥有；若需更细数据，准备精确证券×场所×窗口×schema 的请求，并核对当年字段、精度与范围。当前文档准备不执行采购。

逐笔研究分开两个问题：

1. ETF 与固定篮子的报价先后，需要相匹配的篮子成员逐笔报价；只买发行人和SPY不能回答整体篮子先后。
2. Ernst 式公司股票—ETF 同步同向交易，需要成交、有效交易方向、交易所身份、精细时钟和配对基线；先用发行人/SPY小样本验证解析，但不能把此配对验证称为全论文机制复现。原文还使用价格冲击与 realized spread 证据。

先同一交易所内比较可减少跨场所时钟/网络传输差异，但仍需核对该场所不同证券的时间戳生成方式。跨场所扩展不能用数据商收包先后直接替代经济事件先后。纳秒字段、更多记录或直接 feed 本身都不认证“同一交易者”或因果先后。

后续 prompt 应把逐笔可用性与方法分支写实后再执行。若仅有 bbo-1s，也可交付粗诊断，但明确缺的是逐笔信息，而不是宣称 ETF 没有参与价格发现。本次没有新数值结果或独立 reviewer PASS。
