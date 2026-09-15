# Source-clock evidence for the fixed pilot

状态：`DOCUMENTARY_SUPPORT_ONLY`。本轮只整合既有 code、metadata receipts、制造商文档摘录与已完成的八例 public-clock comparison；未读取 raw rows、新闻正文、EPS、预测值、价格、收益或 POST response，未重跑 census。

## 字段与本地谱系

Gate 1 custodian 对 852 个既有 associations 只投影 `permno,cusip,pends,pdicity,anndats,anntims,actdats,acttims`。852/852 为 `pdicity=QTR`；`anndats` 与选定 manifest 的日期 852/852 一致，`anntims` 也 852/852 一致。所有 `anntims` 都在分钟边界，非零秒 0/852，`00:00:00` sentinel 0/852。这证明已选 source strings 的转录一致，不证明源时钟真实精度、舍入或 first-public semantics。

`actdats` 与 `anndats` 同日 796/852，晚于公告日 56/852，早于公告日 0/852。既有 manufacturer evidence 将 announcement 与 activation（数据库记录）区分，因此不得用 `actdats/acttims` 替换 `anndats/anntims`，即使多数日期相同。现有 receipts 没有逐 revision/correction 的稳定性或 duplicate-publication 规则；这些状态仍 UNKNOWN。

## 时区与公开发布时间证据

2013 Thomson Reuters I/B/E/S Detail History Guide 的既有摘录说明 Detail History timestamps 按季节使用 Eastern Standard/Daylight time；Summary History Guide 的既有摘录说明 2013 年 4 月后 Summary 与 Detail 共用 actuals 文件，并列出 announcement 与 activation 字段。但 Detail Guide 明示适用于 direct delivery；现有证据尚未把该约定完整桥接到 2019–2024 WRDS `ibes.actu_epsus`。

既有固定八例 PRE public comparison 中，6 例有可解释时间：5 例与保存 source clock 同分钟，1 例晚 1 分钟；2 例仅有日期。该样本小且非随机，且网页 JSON-LD 可同时含 WebPage 与 NewsArticle 不同 offset。证据仅支持已成功比较记录的 Eastern/DST 解释；不支持全 852、W002 high 四个 keys、固定 ±1 分钟误差或 first-public guarantee。不得据此统一平移一分钟或把 `anntims` 直接定为 ET/RTH。

## 历史 calendar 支持

现有 calendar projection 只含 `calendar_basis,session_date`，可识别观察到的交易日期；852 个公告日期中 1 个不在该 session-date 集。它缺 `calendar_id,calendar_timezone,open_local,close_local`，因此不能做 intraday RTH、RTH-60 或五分钟 endpoint 分类。calendar 日期支持与 source-clock 语义必须分别验证。

## 当前可用与 UNKNOWN

| 项目 | 当前状态 |
|---|---|
| `pdicity` quarterly metadata | 852/852 observed QTR |
| `anndats/anntims` 转录 | 852/852 与固定 manifest 一致 |
| `actdats/acttims` | activation metadata，不是 release 替代项 |
| Detail History Eastern/DST | manufacturer documentary support；WRDS actuals bridge UNKNOWN |
| first-public release | UNKNOWN |
| 秒级精度、rounding、correction/revision rule | UNKNOWN |
| W002 high 四-key 时区/误差适用性 | NOT_ASSESSED_BY_EVENT-SPECIFIC_SOURCE |
| historical session dates | observed-date support only |
| intraday open/close 与 RTH/RTH-60 | UNKNOWN |

## 下一步

唯一适用的 source-clock 动作是向 WRDS/LSEG 发送已有的窄问题：确认 2019–2024 `ibes.actu_epsus.anndats/anntims` 是否保留 Eastern/DST、字段是否代表 actual announcement 而非 activation、分钟 rounding/imputation 与 revision/correction 规则。若无法获得 provider 回答，则只为固定 key 获取原始 issuer/wire publication timestamp，并保留 date-only/conflicting-object 为 UNKNOWN。之后才可版本化 uncertainty interval；历史 calendar 还需一个独立的 versioned exchange-session projection，字段为 `calendar_id,session_date,calendar_timezone,open_local,close_local`。在这两项输入到位前不运行 RTH/full census。

