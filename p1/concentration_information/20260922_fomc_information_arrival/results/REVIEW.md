# FOMC information-arrival execution: independent review

Review date: 2026-09-22. Independent reviewer routing: `gpt-5.6-sol / high`; no delegation. Review verdict: **NUMERICAL_IMPLEMENTATION_PASS_AFTER_ONE_CORRECTION / RESEARCH_INTERPRETATION_LIMITED**.

This review separates whether the implementation reproduces its stated calculation from whether the result identifies ETF price discovery. The corrected numerical implementation passes the checks below. The evidence does **not** establish an event-conditional SPY increment, permanent price discovery, ETF causality, or the concentration mechanism.

## 1. Correction closed before final review

The first model summary assigned a one-second-ahead target to a window using the predictor/start second. That admitted a target endpoint on the next window boundary, contrary to the contract. The reviewer raised the error before sign-off. `daily_sse` now assigns by `target_rel = predictor_rel + 1`; all four venue-grid model cells and the summary were rerun. This review uses only:

- final model code SHA-256 `7c0496168790bf1c44b4599ca3c498ce860c52cb00397eb1f72e50121bf98c9a`;
- final `DAILY_MODEL_SSE.csv` SHA-256 `f5058bdba46644eba95973cf8683ee2304686bcb0ce8b51c5b72876237f02854`.

The corrected main result is close to the superseded result, but the earlier hash is not review-approved.

## 2. Event clocks and controls

The Federal Reserve calendar independently confirms the eight regular statement dates in each of 2023 and 2024, and marks March, June, September and December as SEP meetings. Each of the 16 linked statement pages says “For release at 2:00 p.m.” in EST or EDT as appropriate. Source: [Federal Reserve FOMC calendar](https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm) and the statement URLs in `EVENT_MANIFEST.csv`.

Independent `America/New_York` conversion reproduced all manifest UTC timestamps: five EST observations map to 19:00 UTC and eleven EDT observations map to 18:00 UTC. The scheduled clock is an official anchor, not a claim about simultaneous terminal receipt.

For every event, independent enumeration of NYSE weekdays after removing the 2023–2024 full-day exchange holidays gave exactly five sessions from the listed control through the session immediately before the event. All 16 listed controls are therefore the deterministic fifth-prior full NYSE session. No event/control pair crosses folds, and no control was selected using outcomes.

## 3. Raw endpoint reconstruction

Raw DBN stayed on SCC. I independently decoded and ordered MBP-1 by `ts_event`, sequence, and source order; reset/invalid states remained invalid; baseline was the last state at or before 14:00 ET minus 1 ns. For a winter event/control and a summer event/control, independently calculated SPY and ES results matched the saved safe summary exactly (maximum absolute bp discrepancy below `4e-15`; state ages also matched):

| date | role | asset | contract | baseline mid | +0.1s bp | +60s bp |
|---|---|---|---|---:|---:|---:|
| 2024-01-24 | control | SPY | SPY | 487.315 | 0.000000 | 0.615599 |
| 2024-01-24 | control | ES | ESH4 | 4918.375 | 0.000000 | 0.508285 |
| 2024-01-31 | event | SPY | SPY | 487.415 | 0.000000 | -22.593542 |
| 2024-01-31 | event | ES | ESH4 | 4913.250 | 0.254411 | -22.413539 |
| 2024-07-24 | control | SPY | SPY | 543.885 | 0.643498 | -1.011294 |
| 2024-07-24 | control | ES | ESU4 | 5497.625 | 0.909442 | -0.909525 |
| 2024-07-31 | event | SPY | SPY | 550.285 | 1.453686 | -11.091314 |
| 2024-07-31 | event | ES | ESU4 | 5556.000 | 2.024633 | -10.804971 |

This validates the audited endpoint implementation; it does not validate cross-market microsecond clock equivalence.

## 4. Split isolation and feature timing

The manifest contains 4 TRAIN event/control pairs, 2 VALID pairs, 2 HISTORY pairs, and 8 TEST pairs. Each event and its control have one common split. Code inspection and output receipts show:

- medians, scaling, and lambda validation use TRAIN/VALID only;
- refitting uses the first six 2023 pairs; HISTORY and 2024 TEST are scored without external refit or rescaling;
- quote and trade predictors use records at or before grid center `g`; the outcome is the stock midpoint return from `g` to `g+1s`;
- rest-of-stock, SPY, and ES features are joined on the same date/grid center; no future response or persistence diagnostic enters a predictor;
- missing predictors are imputed from the training fold with explicit missing indicators, so A2 and A5 use the same finite-target rows.

The corrected primary cell has 92 venue-grid-stock cells per event (`23 stocks × 2 venues × 2 grids`) and 5,520 target observations per event (`92 × 60`). There are eight independent 2024 event/control clusters; stocks and grids are not eight additional independent samples.

## 5. ES trades

The implementation follows the official Databento convention: for MBP-1 `action=T`, `side=B` is buyer aggressor, `side=A` is seller aggressor, and `side=N` is unknown. See [common enums](https://databento.com/docs/standards-and-conventions/common-fields-enums-types) and [MBP-1](https://databento.com/docs/schemas-and-data-formats/mbp-1).

Independent enumeration of all 32 GLBX files found 855,779 trades: 429,682 buyer-aggressor, 426,096 seller-aggressor, and one unknown-side trade. The sole unknown was on 2024-09-18 and was correctly put in unknown volume rather than signed flow. ES price times contracts is only a scaled flow proxy because the contract multiplier is not applied.

## 6. Independent primary recomputation

From final SCC `DAILY_MODEL_SSE.csv`, I pivoted A2/A5 losses on identical cell keys, computed `G = 1 - SSE_A5/SSE_A2`, averaged equally over the 92 cells within each event/day, and then equally over the eight 2024 clusters.

| fit specification | event G | control G | event minus control | event-G 95% cluster bootstrap | paired 95% cluster bootstrap |
|---|---:|---:|---:|---:|---:|
| own lambda | 0.002512 | -0.009621 | 0.012133 | [-0.000642, 0.006541] | [-0.002875, 0.029314] |
| fixed A2 lambda | -0.000770 | -0.026190 | 0.025420 | [-0.003155, 0.001702] | [0.012525, 0.040846] |

All eight event-level values and all 16 leave-one-event-pair-out values independently match the saved `PAIRED_EVENT_CONTROL.csv` and `LOO.csv`; exact values are recorded in `REVIEW_RECEIPT.json`.

The paired contrast is positive in 7/8 events under own lambdas and 8/8 under fixed A2 lambda. That is not the same as positive SPY incremental prediction on event days: event G is positive in only 4/8 and 3/8, respectively; the fixed-lambda mean event G is negative, and both event-G bootstrap intervals include zero. Much of the positive paired contrast comes from A5 performing worse than A2 on controls.

## 7. Vendor conditions and sensitivity

Databento marks ARCX.PILLAR 2023-12-06 (and the next calendar-date condition returned with that request) degraded; this is a HISTORY control, not a primary 2024 observation. GLBX.MDP3 marks the 2024-09-18 event degraded. These conditions are not silently treated as harmless.

Leaving out the complete 2024-09-18 event/control pair gives:

| fit specification | event G | control G | paired difference |
|---|---:|---:|---:|
| own lambda | 0.002239 | -0.005903 | 0.008142 |
| fixed A2 lambda | -0.001384 | -0.024010 | 0.022626 |

The paired sign survives, but the core limitation also survives: event-day SPY incremental G is small and specification-dependent.

## 8. Credentials and API scope

The task directory contains no literal Databento key, GitHub token, or supplied password pattern. Code reads `DATABENTO_API_KEY` only from the environment and never serializes or hashes it. The download receipt contains 96 unique requests—32 each for XNAS, ARCX, and GLBX—matching the manifest hash `e255ce1ac5d62c2393df094437bf9795cab048762549e05e546cfa69452aaaa8`. All 96 completed once as native SCC DBN files. The inspected client code uses symbology, metadata cost/count/condition, and the authorized finite `timeseries.get_range`; it contains no batch, live, subscription, reference purchase, or out-of-manifest expansion.

## 9. Review conclusion

**Numerical implementation:** PASS on the corrected hashes. Event clocks, controls, two raw endpoint samples, folds, feature timing, trade-side handling, primary aggregation, event values, LOO, and degraded-date sensitivity reproduce.

**Research interpretation:** the defensible decision is `COMMON_NEWS_WITHOUT_DISTINCT_SPY_INCREMENT`, not `EVENT_CONDITIONAL_SPY_SIGNAL`. FOMC windows show substantial joint adjustment, but the complete SPY block does not deliver stable positive event-day incremental prediction after stock, rest-of-stock, and ES information. The positive event-control difference is driven partly by negative control G and is not an ETF information share, a causal DiD, or evidence that SPY permanently leads underlying stocks.

One next action: use this completed FOMC exercise as a bounded mechanism/measurement result in the project record, and return the main research effort to the separately defined concentration-and-idiosyncratic-information question rather than buying more FOMC windows or re-optimizing this model.
