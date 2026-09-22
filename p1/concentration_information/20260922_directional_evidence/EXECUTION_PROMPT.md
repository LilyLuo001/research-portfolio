# P1 directional-evidence execution prompt

Date: 2026-09-22. Status: authorized exploratory execution.

## Question

Can the observed one-second ETF-to-stock predictive lead survive comparable-support missing-data handling and time-grid checks, and does it correspond to observable subsequent quote adjustment?

## Requested routing

- Coordinator/model implementation/economic interpretation: gpt-5.6-sol, medium. Retain an existing coordinator rather than restart it.
- SCC feature and quote-response engineering: gpt-5.6-terra, medium.
- Independent limited review after concrete outputs: separate gpt-5.6-sol, high.
- Record actual routing when observable; otherwise `NOT_OBSERVED`. No nested delegation or additional research team.

## Existing inputs

- Read the complete outputs under `../20260922_bidirectional_information/results/`.
- Use the fixed 24 dates, 23 provider-resolved stocks, SPY, two venues and chronological 12/4/8 split.
- SCC root: `/scratch/qluo/bidirectional_information_20260922/`.
- Keep native DBN, feature panels, event rows and prediction rows on SCC. Export only aggregate tables, plots, code, configuration and receipts.
- The observed dates are already viewed; all continuation results are exploratory.

## Work package A: comparable bidirectional prediction

1. Use future one-second midpoint change as the target.
2. First estimate quote-only histories: returns, spread, depth and time controls. Then add separately defined known-side net flow, unknown-side dollar volume and no-trade indicators.
3. Compare ETF history added to each stock; individual-stock history added to ETF; and the sampled stock panel added to ETF.
4. Baseline and expanded models must share target observations. Report a paired-support version across directions where meaningful.
5. For stock-panel-to-ETF, estimate both a per-stock feature model and high/mid/low report-weight-renormalized aggregates. Missing predictors may use training-date imputation plus missing indicators; do not impute targets or use future values.
6. Report out-of-sample `G=1-SSE_full/SSE_baseline`, absolute loss change, daily direction, date-block intervals, support and marginal tier contribution. Negative G means failure of the specified predictor to improve its baseline.

## Work package B: 0ms versus 500ms grid

1. Both grids retain a one-second prediction horizon. Treat 500ms as a half-second grid translation.
2. Report each grid on natural support and on paired corresponding-second support.
3. Compare daily G, positive-stock share, support and actual BBO update incidence/spacing. Use valid midpoint changes as quote updates, not every message.
4. Produce one figure covering both directions, both venues and the daily distribution. Do not search additional offsets.

## Work package C: symmetric quote-update response

1. Define source events as valid midpoint changes. Apply symmetric ETF-to-stock and stock-to-ETF rules, separately by venue.
2. Use the last valid quote strictly before the trigger as the response baseline. Put cross-security equal-timestamp cases in a simultaneous/order-uncertain category.
3. Measure sign-aligned midpoint response after 100ms, 500ms, 1s, 2s and 5s, plus corresponding pre-trigger paths. Report bp response, same-direction update probability, quote availability and counts.
4. Produce all-event and forward-looking-rule-free nonoverlap samples.
5. Construct same-symbol/date/time-of-day controls matched only on pre-trigger spread, recent volatility and quote-update activity. Do not select controls using future events or responses.
6. Interpret responses as temporal/mechanism evidence, not causal effects or information shares.

## Execution and interpretation

- Reuse existing SCC data before any purchase. Purchase only if a named output is impossible from the existing native files; record the missing source, exact request and charge.
- Twenty-three sampled stocks represent about 15.07% of report weight, subject to direct recomputation. Do not describe them as the complete SPY basket.
- Distinguish invalid/missing quotes, unknown aggressor side and no-trade intervals.
- Test centers are clustered within eight test dates. Report both center counts and date support.
- Do not redraw stocks/dates or optimize targets/specifications after seeing results.
- Fix material implementation errors and verify affected outputs without restarting the project audit.

## Deliverables

- `RESULTS.md`
- `BIDIRECTIONAL_PREDICTION.csv`
- `GRID_SHIFT_COMPARISON.csv`
- `QUOTE_RESPONSE_SUMMARY.csv`
- three core figures
- `REVIEW.md`
- `EXECUTION_RECEIPT.json`
- code/configuration
- `NEXT_ACTION.md`

The final report answers whether the one-second lead survives, whether aggregation hides reverse-direction information, what explains the grid difference, whether predictive results line up with quote response, and whether concentration adds explanatory content. It selects one next action: advance a conditional ETF-leading mechanism, reframe around quote-update synchronization, or stop this specification.
