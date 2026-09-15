# P1 缺失数据获取轮次（Sol）

日期：2026-09-14  
范围：只做 acquisition/build；不做识别、功效或结果判断。请求为 Sol/high；运行时路由遥测不可见（`NOT_OBSERVED`）。

## 本轮实际完成

- 从本地缓存的 N-PORT XML 中，对五个指定 wave 选择严格早于各自记录的 announcement cutoff 的 filing；共 12 个股票型 predecessor series、10,010 个持仓 position，其中 9,458 个为普通股候选。W021 只保留 JPEF 的 `S000032550`，明确排除债券基金 `S000003492`。
- 在 SCC 只读使用既有 CRSP stocknames、`dsf`、`dseshares` 2019–2024 分区，将 9,342 个 position 精确映射到 2,779 个 PERMNO，并构造 4,191 条 denominator 完整、正 ownership 的 stock-wave 暴露行。
- 依据原文中的上/下 tercile 生成候选暴露层，但保持 `PROVISIONAL` 标签。为判断数据是否足够，另计算 `-250` 到 `-21` 个交易日的 median `abs(price) × volume`；该指标明确标记为 diagnostic，不是冻结规则。
- 使用现有 IBES QTR 日期/时间元数据、CRSP–IBES link 和交易日历，生成最多 8 个 PRE 与 4 个实施后至少 20 sessions 的 POST 日期候选。结果为 29,729 条 metadata associations；2,088 个高/低尾部 stock-wave 候选拥有完整 8+4 支持。这些是 SCC 实际输出，不是推算。
- 完整支持的实际候选数（高/低）：W002 `595/559`、W013 `30/33`、W016 `146/134`、W021 `13/13`、W025 `285/280`。

## 没有静默完成的事项

- 没有冻结最终 40 个 stock-wave units。原始文字没有定义 authoritative 流动性指标、测量窗、缺失值/中位数并列处理、每个 half 内的排序与 reserve order；文字声称随包提供的 decision-pilot compiler 在本机未找到。因此现有 `PILOT_STOCKS_PROVISIONAL.csv` 不能改名或视为最终 `PILOT_STOCKS.csv`。
- 没有把 IBES metadata clock 当成已核证的公开发布时钟。公告日期/时间仍需逐事件 certification，之后才能生成 release-relative UTC 请求窗。
- 没有生成可报价的 480-association Databento 物理请求清单。主来源仍是“可用时采用 consolidated；否则三 venue”的条件分支，update-level validation 也没有指定事件。
- 没有调用 Databento metadata/cost/download，没有新消费，没有读取 raw actual/forecast 值，也没有读取 POST quote outcomes。

## 关键文件

- `MISSING_DATA_INVENTORY.csv`：逐项取得状态与缺口。
- `PREANNOUNCEMENT_HOLDINGS.parquet`、`PREANNOUNCEMENT_HOLDINGS_RECEIPT.json`：缓存 N-PORT 重建。
- `POSITION_MAPPING_AND_DENOMINATORS.parquet`、`PREANNOUNCEMENT_EXPOSURE_ALL.csv`、`SCC_EXPOSURE_RECEIPT.json`：SCC 映射、shares denominator 与暴露。
- `EARNINGS_METADATA_POOL_8PRE_4POST.csv`、`EARNINGS_METADATA_ELIGIBILITY.csv`、`FULL_SUPPORTED_CANDIDATE_POOL.csv`、`EARNINGS_METADATA_WAVE_TIER_SUMMARY.csv`、`SCC_EARNINGS_POOL_RECEIPT.json`：outcomes-blind 公告元数据候选池；full-support 文件恰为 2,088 行数据加表头。
- `DATABENTO_MANIFEST_STATUS.csv`：能机械编译的规则与仍缺少的精确输入。
- `ROSTER_FREEZE_STATUS.json`：为何没有冻结 40 行。
- `VALIDATION_RECEIPT.json`：本地复核结果，状态 `PASS`。

SCC 新目录：`/projectnb/econdept/qluo/P1_Refraction_WRDS/p1_missing_data_round_20260914`。本轮未修改认证配置、未扫描完整 archive、未执行 git commit/push。
