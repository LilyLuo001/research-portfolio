# Package provenance inventory

状态：`PACKAGE_PROVENANCE_INVENTORY_COMPLETE`。这是一次已有 metadata 的 package-level 盘点，不是新 census、时钟判定或最终样本资格判断。所有数量均从已保存的聚合/metadata 重现；未运行新的全来源扫描。

## 五个 package 的现有证据

| Wave | Fund/package membership | Sponsor evidence | Announcement evidence | Strict holding report | Denominator evidence | Recovered-99 scope |
|---|---|---|---|---|---|---:|
| W002 | 4 个 Dimensional predecessor series → 4 个 ETF series | `conversion_cohorts.csv` 有 sponsor 与公开来源，但无 canonical sponsor ID/signoff | 2020-11-17，date-only，仍为 earliest-public pin pending | 2020-10-31，4/4 series 严格早于记录 cutoff | 2,503 个 positive-exposure rows 有 report-date denominator；split basis provisional | 69 |
| W013 | BrandywineGLOBAL Dynamic US Large Cap Value，1→1 | 仅 exposure universe 的 adviser 字段；不是签署的 economic sponsor | 仅知 2021-12，ledger 使用保守 month lower bound 2021-12-01 | 2021-09-30，1/1 | 98 rows；split basis provisional | 0 |
| W016 | Omni Tax-Managed Small-Cap Value → EA Bridgeway Omni ETF | cohort 文件有 Bridgeway sponsor 与公开来源，但无 canonical ID/signoff | 2022-08-26，有 primary date evidence、无 timestamp | 2022-06-30，1/1 | 588 rows；split basis provisional | 16 |
| W021 | JPMorgan Equity Focus → JPMorgan Equity Focus ETF；bond series 明确排除 | 仅 adviser 字段 | 2023-02-07，provisional local board date | 2022-12-31，1/1 | 39 rows；split basis provisional | 0 |
| W025 | 5 个 Fidelity enhanced-index predecessor series → 5 个 ETF series | 仅 adviser 字段 | 2023-06-14，date-only constituent evidence | 2023-05-31，5/5 | 963 rows；split basis provisional | 14 |

五个 package 共 12 个纳入的 predecessor series。全部选择的 holdings report date 均严格早于当前记录 cutoff；这只证明相对于当前 cutoff 的日期顺序，不证明 cutoff 是合同要求的最早公开公告瞬间 `A_w`。4,191 个 exposure rows 的 denominator 日期基准是 `pre_report_date`，row-level 来源字段为 `denominator_source`：CRSP `dseshares` 在报告日有效，缺失时使用 prior-DSF fallback。corporate-action/split basis 仍为 provisional。

W002 有一个明确版本冲突：当前 exposure lineage 的 `PACKAGE_INPUTS.csv` 使用 2020-11-17；历史 `build_strict_preannouncement_holdings.py` 硬编码 2020-11-16。2020-10-31 holdings 对两者均严格在前，因此现有 exposure 数量不受该一天差异影响，但最终 `A_w` 不能据此冻结。

W002/W016 同时保存 repository effective date 和不同的 public ETF operation date；其余 wave 在 `conversion_cohorts.csv` 没有独立 public-operation record。它们没有形成“所有 constituent 中最晚 legal-effective 或 first-trading instant”的最终 `I_w`。

## 为什么 recovered 99 的 competing conversion 仍为 UNKNOWN

`recovered_candidate_support_20260915/full_artifacts/candidate_conversion_status_aggregate.csv` 中的 conversion status 只检查 CRSP/IBES source-row 到 PERMNO 的唯一性，不是共同/竞争 MF→ETF conversion 状态。

已有 ±24-month 文件只覆盖另一个 40-row roster：每个 wave 8 rows；W002/W013/W016/W021/W025 分别 flag 5/8/8/8/7。该规则标为 `PROPOSED_NOT_FINAL_CONTRACT`，输入只用 other-wave `effective_date`。它既没有覆盖 recovered-99 的精确候选分母，也没有签署的 sponsor/package membership、earliest-public announcement instant 或 concurrent-event provenance。因此 W002 的 69、W016 的 16、W025 的 14 个 recovered stock-wave keys 均保持 `UNKNOWN_NOT_JOINED_TO_SIGNED_PACKAGE_SPONSOR_CONCURRENT_CONVERSION_LEDGER`；不是 clean，也不是 competing=false。

## 精确证据指针

- 公告与 package 成员：`missing_data_round_20260914/PACKAGE_INPUTS.csv` 的 `wave_id, effective_date, announcement_cutoff, cutoff_precision, cutoff_status, pre_series_id, source_locator`。
- 选定 holdings：`SELECTED_PREANNOUNCEMENT_FILINGS.csv` 的 `wave_id, pre_series_id, report_date, cache_sha256, source_locator`。
- 分母：`POSITION_MAPPING_AND_DENOMINATORS.parquet` 的 `wave_id, pre_series_id, pre_report_date, denominator_source, denominator_complete`，逻辑在 `build_scc_exposure.py`。
- successor 与 adviser：`exposure_universe_gate0_pass.csv` 的 `wave_id, effective_date, adviser, pre_series_id, post_series_id, gate0`。
- 竞争 conversion 旧代理：`competing_conversion/supported_roster_overlap_flags.csv` 的 `permno, wave_id, announcement_cutoff, other_wave_ids, other_effective_dates, rule_status`；其全 conversion 输入是 `exposure_stock_wave_all.csv`。
- sponsor 缺口：`sponsor_crosswalk_PROPOSED.csv` 的 `proposed_sponsor, status, evidence_locator, owner_signoff` 尚未成为 five-package canonical key 表。

## 下一步（一个可执行动作）

在 SCC 构造 `recovered99_concurrent_conversion_provenance_sidecar`：将受保护 recovered-99 的 `candidate_id,wave_id,permno` 与现有 `exposure_stock_wave_all.csv[permno,wave_id,effective_date]` 的所有 other-wave rows 精确连接，再附加 `exposure_universe_gate0_pass.csv[wave_id,effective_date,adviser,pre_series_id,post_series_id]`。输出受保护的 candidate-by-other-wave 证据及本地聚合。现有 adviser 只能标为 `ADVISER_ONLY`；公告/实施字段缺失则保持 UNKNOWN；不得生成 clean/exclude boolean。该动作完全依赖现有允许 metadata，可以立即执行，并覆盖 exact 99 denominator。

Step 4 的 primary-provenance 阻点逐 package 写在 `missing_primary_package_evidence.csv`：缺少的是特定基金/package 的 `canonical_sponsor_id`、`earliest_public_announcement_at`、`announcement_source_accession`、constituent-level `legal_effective_at/first_trading_at`、对应 implementation source accession，以及依据既定 package 规则选出的 `I_w`。机械 sidecar 不依赖这些字段，但它们缺失时 competing 状态必须继续 UNKNOWN；不是 earnings、quotes 或另一轮全库扫描。
