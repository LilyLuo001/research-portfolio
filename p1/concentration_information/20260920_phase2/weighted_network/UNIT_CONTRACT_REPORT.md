# Bounded weighted-network input contract check

Status: **negative-control only; not representative of the target common-stock network.** The `b0001` holdings rows have no PERMNO overlap with the stage-1 cached target membership. Its numerical results must not be generalized to the weighted network or used as a global infeasibility finding.

## What was read

On SCC, the check read only one named 2022 CRSP holdings partition (`b0001`, report dates 2022-09-01 through 2022-12-30), the full historical fund-header mapping, and 2022 `fund_summary2`. The source-path manifest and file hashes are in `UNIT_CONTRACT_DIAGNOSTICS.json`. No EPS, forecast, return, or quote column was read; raw rows stayed on SCC.

The mirrored CRSP holdings schema documents `report_dt` as the reported period-end date, `market_val` as the security market value at that reported date, and `percent_tna` as the security percentage of total net assets. The mirrored `fund_summary2` schema documents `tna_latest` as latest month-end TNA and `tna_latest_dt` as its date; its key includes both `crsp_fundno` and `crsp_portno`. Thus the row fields have an explicit report-date valuation/percentage contract, while the summary TNA is a fund-identifier-level latest-month-end field. The mirror does not itself document an allocation from that field to the holdings portfolio denominator.

## Actual bounded diagnostics

The partition contained 527 rows across two portfolio-report-date observations; 519 had positive `market_val` and `percent_tna`, and neither field was null. `percent_tna` never exceeded 100 (493 positive values were at most 1, consistent with percentage points for small positions, but this is not used to infer a scaling convention).

Both portfolio-report-date observations had five date-valid fund classes. Of the 527 holdings rows, 263 found multiple same-`caldt` fund-summary classes and 264 found none. All 263 matching rows had positive class TNA, but every one had disagreement among the available class-TNA values exceeding 1%; all 263 also had an `asset_dt` different from the holdings `report_dt` (while `tna_latest_dt` happened to equal the report date for these rows).

For the 259 rows eligible for a purely mathematical comparison, neither the unscaled `market_val / (percent_tna / 100)` denominator nor that quantity times 1,000 was within 1% of the minimum same-date fund `tna_latest`. These are arbitrary candidate-scale counts, not an inferred unit conversion or a source-failure result. Different fund/share-class TNA values can be economically expected.

## Consequence and exact gap

The holdings field `percent_tna` is already the reported numerical holding weight (in percent); lack of TNA does not block weight-based network diagnostics. It blocks a dollar-valued `L` only when an AUM/TNA term is required. The available mirror metadata does not establish a pro-rata portfolio-to-fund/share-class allocation. `fund_summary2.asset_dt` is an asset-composition date, distinct from `tna_latest_dt`; its mismatch with `report_dt` is not itself a TNA-denominator failure.

No weighted-`L` conclusion follows from this partition. The target-relevant diagnostic is reported separately. A dollar-valued measurement still requires either (1) an authoritative CRSP definition of the holdings portfolio denominator and the units of the relevant TNA, or (2) a date-valid, documented portfolio-to-class allocation rule (including ETF eligibility). Fit-based scaling is prohibited.

Backend execution telemetry: `NOT_OBSERVED`.
