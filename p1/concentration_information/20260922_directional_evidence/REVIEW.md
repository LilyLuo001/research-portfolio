# Independent review of the directional-evidence continuation

Date: 2026-09-22
Verdict: **PASS_WITH_LIMITATIONS**
Requested reviewer route: `gpt-5.6-sol / high`
Actual reviewer route telemetry: `NOT_OBSERVED`

This review covers the final saved code and aggregate outputs, not the earlier
conversation or superseded intermediate Work-C files. No analysis file was
modified by the reviewer, no data were purchased, and no raw or event-level
data were exported from SCC.

## What passed

### 1. Missing quotes, unknown aggressors, and no-trade intervals

`scc_build_directional_features.py` keeps the three concepts distinct.

- Quote fields become missing when the effective BBO endpoint is invalid; an
  effective quote is otherwise carried forward only until a later message
  changes or invalidates it.
- `known_signed_flow_*` sums only trades with a finite dollar value and known
  side. `unknown_dollar_volume_*` separately sums finite-dollar trades whose
  side is unknown. Unknown-side volume is not assigned a buy or sell sign.
- `no_trade_*` equals one only when no trade message lies in the interval. It
  is not used as a synonym for unknown aggressor side.

On the SCC feature table (4,147,200 rows), these fields were nonmissing by
construction; 30,731 0–100ms rows had positive unknown-side dollar volume,
4,039,602 were explicit no-trade rows, and no no-trade row had nonzero known
flow or unknown volume. There were 347 intervals with a trade message but zero
finite-dollar known/unknown amount; the code correctly does not label these as
no-trade, although they remain a negligible vendor-data residue rather than a
separate modeled category.

### 2. No test-period or future leakage in the prediction models

The date split remains 12 train / 4 validation / 8 test dates. Predictor
medians, missing indicators, means, and scales are fitted from training data.
The ridge penalty is selected on validation loss. The final coefficient fit
uses train plus validation outcomes with the already training-fitted
preprocessing. Test outcomes and test predictor distributions do not enter
imputation, scaling, or lambda choice. Predictor returns end at the grid
center; `y_1s_bp` starts at that center and ends one second later.

### 3. Baseline and full models use common target support

`model_pair` first retains rows with finite target and then constructs both
baseline and full matrices on exactly those rows. Predictor missingness is
imputed with training medians and represented by missing indicators rather
than causing model-specific row deletion. Independently summing
`PREDICTION_DAILY.csv` reproduced every saved baseline SSE, full SSE, test
count, and G in `BIDIRECTIONAL_PREDICTION.csv`; the maximum G discrepancy was
`5.2e-16`.

### 4. The 0ms/500ms comparison is a translated one-second grid

Both grids use a one-second target. The 500ms setting shifts the center by
half a second; it is not a shorter or more frequent prediction horizon.
`second_index` pairs corresponding integer and half-second centers within a
date. In the final test sample every pairwise row has 14,400 natural centers
and 14,400 paired centers, so `paired_G == natural_G` for all 736 saved rows.
Sample-support selection therefore cannot explain the final grid difference.

### 5. Independent recomputation of G and date bootstrap

The reviewer independently reconstructed all 32 pairwise aggregate rows from
the saved daily losses, including the synchronized 2,000-draw date bootstrap.
Every equal-stock and report-weight point estimate and every saved interval
endpoint matched to below `1.0e-16`.

For the main rest-basket-controlled quote specification, independently
recomputed equal-stock G values were:

| Venue | Grid | ETF→stock | Stock→ETF |
| --- | ---: | ---: | ---: |
| XNAS | 0ms | 0.003366 | -0.000092 |
| XNAS | 500ms | 0.002409 | -0.001157 |
| ARCX | 0ms | 0.003101 | -0.001964 |
| ARCX | 500ms | 0.002275 | -0.000112 |

The corresponding quote-plus-separated-trade ETF→stock values are positive
in all four cells (0.001866–0.002782), while the reverse values are negative.
These are small conditional prediction gains, not price-discovery shares or
causal effects.

### 6. SCC raw-event and matched-control backtrace

The final Work-C code and CSV hashes matched between SCC and the local
aggregate-only directory. A raw backtrace of ARCX 2023-01-09 SPY→AAPL found:

- 81,715 SPY midpoint-change events in the required `[10:00, 10:30)` center
  interval and none outside it;
- seven AAPL midpoint updates at exactly a SPY event timestamp, correctly
  marked order-uncertain in the quote-response calculation;
- a manually recomputed first-event one-second signed response of
  `-3.4081227254 bp` and forward signed prepath of `-1.1362990751 bp`, matching
  the final formulas;
- 81,126 matched event/control observations for that pair/date, zero matching
  cell mismatches, zero separations at or below ten seconds, and a minimum
  absolute separation of `10.000101888` seconds.

Across the aggregate files, usable quote counts never exceeded event counts,
matched-pair counts never exceeded candidate counts, the five horizons shared
the same candidate support within each venue/direction/sample, and all groups
covered 24 dates. `QUOTE_UPDATE_DIAGNOSTICS.csv` has the expected 1,152
venue-date-symbol rows.

The decoder retains an invalid/reset timestamp endpoint as `NaN`, prevents a
later recovery from being classified as a change across the invalid epoch,
and makes endpoint queries inside that epoch unavailable. A scan of all 48
final DBN files and all 1,152 decoded venue-date-symbol series found zero
persistent invalid timestamp endpoints after the documented same-timestamp
last-state collapse. Thus the invalid-epoch path is correct by code inspection,
but this particular sample offers no persistent invalid epoch for an empirical
event backtrace.

### 7. Per-stock, rest-basket, tier, and marginal-tier results are distinct

- `PAIRWISE / ETF_TO_STOCK` adds SPY history to a stock-history baseline. In
  `*_WITH_REST_BASKET`, the baseline additionally controls the other 22 sampled
  stocks.
- `PAIRWISE / STOCK_TO_ETF` adds one stock to an SPY-history baseline; the
  rest-basket variant controls the other 22 stocks before adding that stock.
- `JOINT_PER_STOCK` adds all 23 stock histories separately to the SPY baseline.
- `JOINT_TIER` adds three report-weighted tier aggregates and their coverage
  fields.
- `TIER_MARGINAL_*` adds the named tier only after the other two tiers are
  already in the baseline.

The per-stock joint trade extension was not run; the receipt correctly says
that the trade joint model is tier-aggregate only. The final narrative does
not treat tier aggregation as equivalent to the per-stock model and does not
claim a stable concentration gradient. The 23 provider-resolved stocks have
combined report weight `0.1506999625` (15.07%), so they are correctly described
as a sampled basket rather than the complete SPY basket.

## Corrections incorporated before this verdict

Three material Work-C issues found during review were corrected and fully
rerun before the hashes below were sealed:

1. Matched-control spread and five-second movement originally included the
   trigger-center source state. Final covariates are strictly pre-center.
2. Work-C event/control centers originally included the one-minute download
   buffers. Final centers are restricted to 10:00–10:30 ET; buffers provide
   endpoint support only.
3. The original prepath used the reverse return. Final `mean_prepath_bp` uses
   the forward path from `t-h` to the strictly pre-trigger baseline.

The final report also avoids attributing the old grid instability to one
unidentified cause, discloses that a matched control may be before or after
the trigger, and notes that the matched-control table retains the very rare
equal-timestamp order-uncertain observations while the raw-response table
provides excluded variants.

## Limitations that remain

- This is exploratory reuse of previously viewed dates. The 14,400 centers are
  clustered in eight test days, not 14,400 independent experiments.
- The matched-control exercise is a temporal comparison, not a causal design.
  Controls may lie after a trigger, matching uses coarse tercile cells, and
  controls can be reused. Equal-timestamp order-uncertain observations remain
  in the matched-control table, although they are rare and excluded variants
  in the raw-response table leave the qualitative result unchanged.
- The two feeds are venue-level BBOs, not SIP NBBO, and the sampled stocks cover
  only 15.07% of report weight.
- The event response is positive in both directions. It supports rapid
  comovement and a more persistent ETF→stock path, but it does not independently
  establish one-way ETF causality, arbitrage, or permanent price discovery.
- Cross-sectional weight/tier comparisons do not identify a time-varying
  concentration mechanism. Concentration should remain outside the main claim.

Subject to these limitations, the final `RESULTS.md` claim—small but robust
conditional ETF→stock prediction improvement, no comparable reverse
improvement, bidirectional event response, and no supported concentration
mechanism—is supported by the saved code and aggregates.
