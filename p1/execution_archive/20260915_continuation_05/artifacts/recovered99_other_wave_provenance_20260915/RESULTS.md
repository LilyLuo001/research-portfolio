# Recovered-99 × other-wave provenance sidecar

状态：`RECOVERED99_OTHER_WAVE_PROVENANCE_FULL_COMPLETE`。在固定的 99 个 recovered stock-wave candidate keys 上，使用同一 pinned exposure source version，以 PERMNO 精确连接所有不同 `wave_id`；同一 PERMNO 出现在多个 wave 时分别保留。fund-series metadata 先按 other wave 聚合再连接，因此不会把 candidate×other-wave pair 按基金数膨胀。

## 执行结果

99 个 focal candidate 中，24 个在该 30-wave exposure source version 里至少匹配一个 other wave，形成 45 个唯一 candidate×other-wave pairs；75 个保留为 `NO_OTHER_WAVE_MATCH_IN_THIS_VERSIONED_EXPOSURE_SOURCE`。后者不表示完整 conversion calendar 中不存在 competing conversion。

| Focal wave | Tier | Candidate denominator | 有 other-wave match | 无 match | Candidate×other-wave pairs |
|---|---|---:|---:|---:|---:|
| W002 | high | 33 | 10 | 23 | 19 |
| W002 | low | 36 | 4 | 32 | 5 |
| W016 | high | 7 | 3 | 4 | 5 |
| W016 | low | 9 | 5 | 4 | 9 |
| W025 | high | 3 | 1 | 2 | 3 |
| W025 | low | 11 | 1 | 10 | 4 |
| **合计** |  | **99** | **24** | **75** | **45** |

匹配的 other waves 只有 4 个：W002 10 pairs、W006 12、W016 11、W032 12。一个 focal candidate 可匹配多个 other waves，所以 45 pairs 不是 45 个独立 candidates。

## Provenance 状态

Pinned `exposure_stock_wave_all` projection 含 8,826 个 metadata rows、30 个 observed waves；public fund-series universe 含 71 rows、47 waves。30/30 exposure waves 均能在 public universe 找到同 wave 的至少一个完全相同 effective date；本次 45 pairs 也全部如此，missing-public-wave 与 effective-date-conflict 均为 0。这只是两个版本化 metadata source 的日期一致性，不证明日期是 rule-correct `I_w`。

所有 matched pairs 的 adviser 仅标为 `ADVISER_ONLY_NOT_SIGNED_ECONOMIC_SPONSOR`。primary public announcement bound 未附加，implementation 只有 effective-date metadata，因此 competing-conversion inference 对全部 99 仍为 `NOT_ASSESSED`；没有生成 clean/exclude boolean。

本次没有建立新 clock 规则。合同允许在将来用有来源的时间不确定区间进行 fail-closed 分类；并不要求每个公告都有秒级时间。当前缺的是 primary public-event/constituent provenance 与 rule-correct bounds，而不是机械地把 date/month precision 当成必然阻断。

受保护的 `candidate_id,wave_id,permno,other_wave_id` sidecar 只保留在 SCC。本地只保留聚合、公开 fund/package metadata、代码和 receipts；未读取财务、outcome、quote 字段，也未估计 clean、power 或 effects。

详见 [focal-wave/tier counts](full_artifacts/matches_by_focal_wave_tier.csv)、[other-wave detail aggregates](full_artifacts/matches_by_focal_wave_tier_other_wave.csv)、[matched-wave provenance](full_artifacts/matched_other_wave_metadata_coverage.csv) 与 [source-wave reconciliation](full_artifacts/source_wave_to_public_universe_coverage.csv)。
