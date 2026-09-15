# W002 high source reconciliation

状态：`BLOCKED_DIRECT_SOURCE_CONNECTIVITY`。本次只检查既有 SCC/WRDS count-only 连接能力，没有再次读取 parquet，也没有执行源表数据查询。

W002 high 固定范围为 4 个 exact event keys：PRE 3、POST 1；90 日窗口覆盖 2019-07-31 至 2021-11-02。既有 producer SQL 表明来源为 `ibes.detu_epsus`，按 `anndats` 年界分区，过滤 `usfirm=1` 和 `upper(measure)='EPS'`，无可见 `LIMIT/OFFSET`。这些条件匹配历史 producer filter；它们对四个目标 key 是否均为正确范围尚未由独立 key-level metadata 证明。本次没有引入新的 mapping 或筛选规则。

SCC 项目路径中未找到现成 `wrds.Connection`、`psycopg` 或 `raw_sql` adapter；批准的 runtime 也未安装 `wrds`、`psycopg2` 或 `sqlalchemy`。随后仅用系统 `psql -w` 做非交互连接测试，WRDS 返回 `fe_sendauth: no password supplied`。未读取 `.pgpass`、环境密钥或其他 credential store，未更改认证。因此无法执行一次性四-key 源端 reconciliation，现有结论保持：PRE 三个 keys 的观察 analyst counts 为 0、1、1；POST 一个 key 为 1，均为 UNKNOWN 而非确定不足。

解除本 blocker 的精确操作是：由已配置 WRDS 认证的现有 custodian 运行四-key、四列（`cusip,fpedats,analys,anndats`）固定 90 日查询，并返回源端 distinct analyst count 聚合、WRDS returned-row count、成功状态与 query hash；行级结果留 SCC。

安全 Step2：对同一四-key manifest 运行现有 metadata-only clock/session adapter，连接已批准的交易日历，仅返回 source-display-clock 的 session 分类和 UNKNOWN 原因；在缺 source timezone/first-public-release 证明时，不升级为 ET/RTH 或可交易时钟。
