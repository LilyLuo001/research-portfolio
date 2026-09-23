# Paper 1 Phase 2 — 2023 NYSE opening-auction failure

This folder is the complete handoff for the first contemporary Paper 1 case.

## Read in this order

1. [Decision](DECISION.md)
2. [Results and limitations](RESULTS.md)
3. [Analysis specification](ANALYSIS_SPEC.md)
4. [Case selection](CASE_SELECTION.md) and [method review](METHOD_REVIEW.md)
5. [Run receipt](RUN_RECEIPT.json), [source/order manifest](SOURCE_AND_ORDER_MANIFEST.json) and [dataset conditions](DATASET_CONDITIONS.json)
6. [Independent numerical review](REVIEW.md) and its receipt when complete

`results/` contains only permitted aggregate tables and figures. Raw Databento DBN, per-security administrative rows and price-level paths remain on SCC under `/project/econdept/qluo/p1_price_discovery_resilience_20260923/phase2`.

The empirical label is `INCOMPLETE_ACTIVITY_SUBSTITUTION / COMMON_PRICE_RESILIENCE`. The direct-feed quote construct is not NBBO, the event-day XNYS feed is vendor-flagged degraded, and the result is a documented case study rather than a universal causal effect of ETF concentration.
