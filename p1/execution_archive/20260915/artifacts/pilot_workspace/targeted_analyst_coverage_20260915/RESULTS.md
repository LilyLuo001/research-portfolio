# Targeted analyst coverage results

状态：`COMPLETE`。本轮只处理 corrected_v2 中同时具有 nominal source-clock PRE/POST、且旧 overlap 标为 known-clean 的 W002 候选，并把 W016 low 作为独立 stress cell。单位是 exact event keys 与 stock-wave candidate keys，不是 SUE 或最终可用样本。

| wave/tier | side | 目标 keys | 观察到 ≥2 analyst IDs | UNKNOWN（观察 <2，来源完整性未认证） |
|---|---:|---:|---:|---:|
| W002 high | PRE | 3 | 0 | 3 |
| W002 high | POST | 1 | 0 | 1 |
| W002 low | PRE | 45 | 9 | 36 |
| W002 low | POST | 42 | 9 | 33 |
| W016 low stress | PRE | 8 | 7 | 1 |
| W016 low stress | POST | 9 | 3 | 6 |

合计 108 keys、16 stock-wave candidates。28 keys 观察到至少两个不同 analyst IDs，因此这是稳健的下界；其余 80 keys 保持 UNKNOWN，不能把观察 <2 解释成确定不足。candidate 层面“PRE 与 POST 各至少一个 observed-min2 key”为：W002 high 0/1、W002 low 4/14、W016 low 1/1。UNKNOWN keys 不阻止“至少一个”的存在性计数，但另行保留。

W002 high 的 4 keys 都不是缺 source year 或超过已观察日期：PRE 的观察 analyst counts 为 0（1 key）和 1（2 keys），POST 为 1（1 key）。因此 PRE 与 POST 均未观察到 min2，但 1→0 不是科学排除，因为源抽取完整性未被证明。

执行只读取 SCC I/B/E/S detail 的 `cusip,fpedats,analys,anndats`。窗口沿用 `[release_date-90 days, release_date)`；exact key 保留 wave、tier、PERMNO、side、pends、release date；revision/duplicate rows 不增加 distinct analyst count。2018–2024 使用既有 receipt 的历史 SHA，并在本次核对固定 SCC stat；2025–2026 仅核对固定 stat，未额外全档哈希。所有行级目标与计数留在 SCC，本地仅有 aggregates、code 与 receipts。未读取 forecast/EPS value、价格、收益、quote 或 response，backend telemetry 为 `NOT_OBSERVED`。

定向 provenance 查找进一步确认：W002 high 的窗口落在 2019-07-31 至 2021-11-02；对应 2019、2020、2021 SQL 均按 `anndats` 年界提取 `ibes.detu_epsus`，固定过滤 `usfirm=1` 与 `upper(measure)='EPS'`，文本中没有 `LIMIT/OFFSET`。mirror manifest 记录三份 parquet 的 SHA、SQL 路径和 `existing_not_overwritten`，迁移 manifest 的文件尺寸也一致。但现有 artifact 没有原生产执行的返回行数、成功终止或客户端无截断证明，`existing_not_overwritten` 只说明后续 mirror 没覆盖文件。因此 W002 high 的 4 个 UNKNOWN 不能升级。

下一步所缺的唯一精确 artifact 是：`ibes_detu_eps_2019/2020/2021` 原生产 query execution receipt/log，其中必须含 WRDS 返回行数、成功完成状态、无客户端 row cap/truncation，并与三份 parquet row counts 对账；不再泛化请求全部 108 keys 的“认证”。
