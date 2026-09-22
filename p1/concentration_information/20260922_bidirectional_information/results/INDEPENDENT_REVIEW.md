# Independent P1 bidirectional-pilot review

Date: 2026-09-22
Verdict: **PASS_WITH_LIMITATIONS**

The exported pairwise results are arithmetically reproducible, the chronological split and estimator implementation do not expose test outcomes to scaling or lambda selection, and an independent native-DBN reconstruction matched the SCC feature parquet at 20 test-window centers. The economically decisive limitation is the group ablation: its common complete-case sample is only **2 train / 2 validation / 4 test centers on XNAS grid0** and **383 / 98 / 595 on ARCX grid0**. I do **not** certify the reported group-ablation gains or leave-group-out loss changes as economic evidence.

## Scope and evidence

I reviewed `NEXT_EXECUTION_PROMPT.md`, `analysis_config.json`, roster/date/request/download/feature/model receipts, `SAFE_ROSTER.csv`, `DATE_MANIFEST.csv`, `COVERAGE.csv`, feature/model/summarizer code, and the actual aggregate outputs. Native DBN and the 4,147,200-row feature parquet were read in place on SCC at `/scratch/qluo/bidirectional_information_20260922/`; none was copied locally or modified.

Requested reviewer routing was `gpt-5.6-sol / high`. Dispatch was observable as accepted; actual model telemetry was **NOT_OBSERVED**.

## Independent reproductions

- Output cardinality is coherent: 552 pair-model rows = 2 venues × 2 grids × 23 resolved stocks × 2 directions × 3 horizons; 4,416 daily rows = 552 × 8 test dates. BF is the sole unresolved roster member, leaving 23/24 stocks (95.83% count coverage). Its reference weight is 0.0004, or about 0.265% of the selected sample's summed report weight.
- Every `DAILY_LOSS_SUMMARY.csv` row satisfies `loss_difference = SSE_baseline - SSE_full`. Regrouping daily losses reproduces pairwise `n_test`, baseline SSE, full SSE, and `G = 1 - SSE_full/SSE_baseline` in `PREDICTIVE_GAINS.csv` to floating-point precision.
- Repeating the synchronized whole-date bootstrap from daily losses with seed 20260922 and 1,000 draws reproduces `AGGREGATE_GAINS.csv`. The bootstrap resamples the same test date for every stock within a draw, as required.
- Primary XNAS/grid0/5s pairwise test support is 833–3,918 centers per stock, median 3,023, in both directions; all models retain all eight test dates.
- Four stock checks spanning all weight tiers, independently summed from daily rows:

| Stock | Tier | Direction | Test n | Baseline SSE | Full SSE | G |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| AAPL | high | ETF→stock | 833 | 3892.826375 | 3853.140867 | 0.010195 |
| AAPL | high | stock→ETF | 833 | 1629.163899 | 1629.036832 | 0.000078 |
| CMI | mid | ETF→stock | 3686 | 12435.050993 | 12179.192766 | 0.020576 |
| CMI | mid | stock→ETF | 3686 | 4667.977657 | 4668.124396 | -0.000031 |
| NWSA | low | ETF→stock | 3557 | 17691.111422 | 17629.261732 | 0.003496 |
| NWSA | low | stock→ETF | 3557 | 4359.136014 | 4359.021061 | 0.000026 |
| XYL | low | ETF→stock | 3262 | 15002.212794 | 14879.487386 | 0.008180 |
| XYL | low | stock→ETF | 3262 | 4164.098936 | 4164.298956 | -0.000048 |

The primary five-second equal-stock aggregates also reproduce exactly: XNAS ETF→stock `G=0.001224881`, 95% day-block interval `[-0.000929706, 0.003067713]`; XNAS stock→ETF `G=0.000685680`, interval `[-0.000715395, 0.001620066]`. Both cross zero. ARCX/grid0 also crosses zero in both directions (`0.000274077 [-0.001030780, 0.001216054]` and `0.000150748 [-0.000422797, 0.000468037]`). This supports `PREDICTIVE_TRANSMISSION_NOT_ESTABLISHED` at the primary horizon.

The secondary one-second ETF→stock result is positive on grid0 at both venues—XNAS `0.001689322 [0.000856557, 0.002214074]`, ARCX `0.000769138 [0.000058029, 0.001549542]`—but is not boundary-stable: at +500ms XNAS is `0.000485501 [-0.000501271, 0.001096344]` and ARCX is `-0.000593620 [-0.002157679, 0.000756695]`. XNAS/grid0 stock→ETF at one second is negative (`-0.001330383 [-0.002299636, -0.000934014]`). These are secondary diagnostics, not a basis to overturn the five-second decision.

## Timing, leakage, state, and placebo checks

- Dates are the fixed fifth/fifteenth NYSE sessions and are split chronologically 12 train / 4 validation / 8 test. Selection code uses only 2022 report weight, prior 60-session liquidity, dated identity, and the fixed hash seed; no response-based redraw is present.
- Scaling is fitted on train rows. Lambda is selected on validation rows only. The selected lambda is then used for a train+validation refit while retaining the train-fitted scaler. Test rows enter only final prediction and diagnostics. Baseline and full models use the same finite observation mask.
- Feature windows are `(t-100ms,t]`, `(t-1s,t-100ms]`, and `(t-5s,t-1s]`; targets start at `t` and end at `t+h`. `state_at(..., side="right")` uses messages at or before the boundary and does not backfill from the future.
- Native trade sign is `B=+1`, `A=-1`, and other/unknown is missing. No-trade intervals are observed zero flow and volume; an interval containing unknown-side dollar volume does not become false zero flow. BBO state is invalidated on action `R`, undefined size/price, nonpositive fields, or crossed quotes.
- I independently decoded XNAS native DBN for 2023-10-20 and reconstructed 20 centers: AAPL, CMI, NWSA, and SPY at five clock times each. All three lagged returns, all three signed-flow fields (including matching missingness), spread, depths, five-second volume, native-direction share, and 100ms/1s/5s targets matched the SCC parquet exactly. The sampled raw file contained native `B`, `A`, and unknown trade sides; the sampled symbols had no clear/invalid-BBO event, so raw invalidation was verified from implementation rather than an observed sampled clear.
- The off-day diagnostic deterministically replaces only the added source block with the next test day's same-window offset, leaves the baseline prediction fixed, and uses no refit. Primary mean off-day G values reproduce (`-0.005680440` ETF→stock and `0.000119941` stock→ETF on XNAS/grid0), weakening a strong aligned-time interpretation rather than rescuing the main result.
- Post-review correction from authenticated Databento `metadata.get_dataset_condition`: the three degraded dates—2023-09-22, 2023-11-21, and 2023-12-07—belong to **ARCX.PILLAR**; XNAS.ITCH reports `available`. **Resolved:** current `COVERAGE.csv` assigns all three labels to ARCX, and `AGGREGATE_GAINS.csv` now applies the exclusion only to ARCX. All 12 XNAS rows have `equal_stock_G_without_degraded_dates` exactly equal to the full `equal_stock_G`; all 12 ARCX rows reflect the venue-specific exclusion.

## Group-ablation finding: not certified

The all-stock ablation requires every one of 11 historical fields for SPY and all 23 resolved stocks at the same center. That complete-case intersection collapses to:

- XNAS/grid0: 2 train, 2 validation, 4 test centers; the four test centers occur across only three dates. The reported 269-feature all-stock model is therefore fitted on four train+validation rows. Its `G=0.802895` and tier-removal values have no defensible economic interpretation.
- XNAS/+500ms: no output row because no complete training centers survive. This absence is currently silent in `GROUP_ABLATION.csv`.
- ARCX/grid0: 383 train, 98 validation, 595 test centers. This is better than XNAS but remains tiny relative to the nominal 14,400 test centers and is a selected complete-case subset; 269 features are fitted on 481 train+validation observations. ARCX/+500ms is similarly only 386/105/595.

Accordingly, Figure 4 and the numeric ablation table may remain only as failed-support diagnostics. They must not support claims about high-, mid-, or low-weight firms, concentration, or company-level coverage.

## Correction status before final delivery

1. **RESOLVED:** `RESULTS.md` and `EXECUTION_RECEIPT.json` now record the completed empirical run and independent review.
2. **RESOLVED:** the final report states `PREDICTIVE_TRANSMISSION_NOT_ESTABLISHED` for the primary five-second design and treats the one-second result as boundary-sensitive secondary evidence.
3. **RESOLVED:** group-ablation economics are labeled **NOT ESTIMABLE / INSUFFICIENT COMPLETE-CASE SUPPORT**; Figure 4 is support-only, split counts are reported, and the absent XNAS/+500ms result is disclosed. The substantive non-certification remains in force.
4. **RESOLVED:** final provenance hashes were regenerated from the files actually used.
5. **RESOLVED:** adjacent-two-test-day block sensitivity was added; the primary intervals cross zero and do not alter the conservative decision.
6. **RESOLVED:** BF coverage loss is preserved, authenticated ARCX degraded-date provenance is recorded, and the venue-specific exclusion sensitivity is corrected in `COVERAGE.csv` and `AGGREGATE_GAINS.csv`.

Subject to those corrections, the core pairwise pilot is suitable for delivery. The group-ablation contribution claim is not.
