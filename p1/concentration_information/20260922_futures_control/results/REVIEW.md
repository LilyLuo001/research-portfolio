# Independent ES futures-control review

Date: 2026-09-22  
Decision: `PASS_WITH_LIMITATIONS`

## Scope and routing

This review covered only the completed ES futures-control execution. The requested independent route was `gpt-5.6-sol / high`; model/effort telemetry was not directly observable inside the reviewer runtime and is therefore recorded as `NOT_OBSERVED`. No nested delegation, data purchase, model refit, or raw-data export was performed.

## Independent checks

- All 24 `ES.v.0` files were present on SCC. The first MBP-1 instrument ID in every file matched `CONTRACT_MAP.csv`. The five observed contract/ID pairs were ESH3/206299, ESM3/95414, ESU3/3445, ESZ3/314863, and ESH4/17077.
- I independently reconstructed the 09:59–10:31 ET request clock with `America/New_York`. All 24 UTC intervals matched: winter requests began 14:59 UTC and daylight-saving requests 13:59 UTC. The 10:00–10:30 ET core has 1,800 rows per grid and date.
- I inspected 20 distinct ES raw centers from five dates spanning winter, daylight-saving time, and roll regimes (2023-01-09, 2023-03-21, 2023-07-10, 2023-09-22, 2023-11-07), both 0/500ms grids, and the first/last core seconds. I independently decoded MBP-1, ordered records by event timestamp/sequence/source order, and recomputed all eight AT_T fields and all eight t−1s fields. There were zero mismatches. A separate 24-cell trace over both XNAS and ARCX confirmed one stock row, one ES row, identical `t_ns`, and a finite stock target at every checked cell. Licensed row values remained on SCC.
- Across the full futures feature table, every t−1s field equaled the preceding same-grid AT_T field for all 86,352 within-day comparisons per field. This verifies that `AT_T_MINUS_1S` changes only the ES information cutoff while retaining the stock target.
- The date contract is 12 train, 4 validation, and 8 test dates. Every stock has 14,400 test centers. Training/validation counts range from 21,590–21,600 and 7,193–7,200 because a few ARCX targets are missing and correctly excluded rather than imputed.
- ES validity is 100%. FULL and ES_VALID model rows are numerically identical. The common-date bootstrap repair now uses the same 2,000 whole-date draws in every venue/grid/specification; FULL and ES_VALID intervals are identical.
- From the saved daily losses I independently reproduced model SSE, MSE, all four G statistics, 23-stock equal/report-weight aggregates, all leave-one-date-out values, and the final synchronized-date intervals. Maximum discrepancies were `1.46e-11` for daily-to-model SSE, `1.33e-15` for MSE, `4.28e-16` for model G, `1.84e-16` for aggregate/LOO points, and `1.03e-16` for bootstrap endpoints.
- All eight main reverse checks are negative after conditioning on ES (`-0.003988` to `-0.000458`).

## Interpretation check

`MIXED_OR_UNRESOLVED` is supported by the frozen comparisons. In the quote-only family, SPY|ES is positive in all four venue/grid cells (`0.000211`–`0.000463`), all leave-one-test-date-out values remain positive, and two of four synchronized-date intervals exclude zero. In the quote-plus-trade family, SPY|ES ranges from `-0.000215` to `0.000211`; two cells are positive and all four intervals cross zero. Thus the quote-only residual is not a stable ETF-specific contribution once richer cash-market trade history is included. The reverse negative results reinforce, but do not causally identify, common-market/ETF leadership.

The 24 dates are mechanically selected fifth/fifteenth NYSE sessions, not earnings or macro-event dates. Only eight already-viewed test dates support inference. The results establish small out-of-sample conditional prediction changes, not permanent price discovery, ETF arbitrage, causal transmission, information shares, trading profitability, or power for an event design.

## Review finding and disposition

During review, the initial bootstrap seed varied by cell and support, so identical FULL/ES_VALID samples had slightly different Monte Carlo intervals and venue/grid draws were not synchronized. The coordinator corrected only this aggregation step from saved daily losses, regenerated the tables/figures, and corrected two stale interval counts in `RESULTS.md`; no model was refit. The final hashes below passed re-review.

No remaining error changes the point estimates or the `MIXED_OR_UNRESOLVED` decision. The one fixed-specification, unseen-date replication in `NEXT_ACTION.md` is an appropriate bounded next test, not an automatic authorization to purchase or claim a mechanism.
