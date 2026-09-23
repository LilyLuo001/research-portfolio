# Data requirements and availability boundary

Date: 2026-09-23.  This is an engineering specification, not evidence that a product has been purchased, a licence permits the use, or an event is covered.

## Already located (SCC only; no new read or computation in this subtask)

The existing FOMC demonstration receipt identifies the SCC root as `/project/econdept/qluo/bidirectional_information_20260922/fomc_information_arrival_20260922`.  It records native `mbp-1` inputs for `XNAS.ITCH`, `ARCX.PILLAR`, and `GLBX.MDP3`, with 16 2023/2024 FOMC event dates and 16 fixed controls.  The retained equity input is **SPY plus 23 individual stocks**, not a complete contemporaneous S&P 500 basket and not a national NBBO.

Available feature-level fields, as defined in the existing SCC builders, include event timestamp and ordering (`ts_event`, sequence, source order), `bid_px`, `ask_px`, `bid_sz`, `ask_sz`, trade action/side/price/size, midpoint, spread, displayed depth, midpoint-update count and age, known signed flow, unknown trade volume, and an explicit no-trade flag.  ES is a contemporaneous raw contract resolved from `ES.v.0`, not a claim that a continuous series is a traded contract.  These inputs are licensed/SCC-resident; raw DBN and row-level parquet must remain there.  Actual licence entitlement for a new analysis is **NOT_YET_VERIFIED**.

The first chronological 2023 FOMC event/control pair present in the receipt is 2023-02-01/2023-01-25; the next is 2023-03-22/2023-03-15.  This is a metadata-only chronological choice for a measurement demonstration, not a new sample, response inspection, or channel-restriction test.

## Required for the retained NYSE 2015 case

| Object | Exact fields / construction requirement | Historical window | Known status and permitted landing place |
|---|---|---|---|
| U.S. consolidated quote and trade record | SIP/CTA/UTP message timestamp, participant/exchange timestamp where supplied, exchange/MIC, symbol, quote prices and sizes, trade price/size/conditions, NBBO/quote condition and correction/cancel status | 2015-07-08, at least 10:00-15:30 America/New_York plus pre-specified matched normal days | Product family: NYSE Daily TAQ (official catalogue is listed in `LITERATURE_AND_DATA.md`). Coverage and licence for 2015 fields are **UNKNOWN**. Keep raw/row data SCC-only. |
| Direct venue audit | NYSE and NYSE MKT gateway/market-status messages if obtainable; direct feeds for XNYS, ARCX, XNAS and named alternative venues; exchange sequence and event clocks | 2015-07-08, same window | Required to separate the documented 10:45-ish degradation from formal 11:32 halt and to distinguish source outage from trading outage. Existing SCC coverage **UNKNOWN**; do not purchase or request a new subscription under this task. |
| Index ecosystem | SPY venue-level quote/trades; the actual ES contract's CME MDP3 quote/trade/order-book records and trading status; official contract metadata, multiplier, expiry and session state | Same intraday window; ES contract must be resolved by date | Existing GLBX MDP3 is only verified for the 2023/24 FOMC demonstration. 2015 coverage **UNKNOWN**. Product can be requested from CME/Databento only after coverage, licence, and authorized purchase are separately established. |
| Complete comparable basket | Point-in-time S&P 500 membership; SPY historical holdings/PCF quantities, cash/fees/shares; security identifiers; corporate actions; same-time stock prices | 2015-07-08 and each chosen comparison day | Existing 23-stock list is inadequate. S&P Global ETP/holdings/PCF and a point-in-time index-constituent source are candidate products; historical versioning, units, and permission are **UNKNOWN**. All detailed holdings and constructions remain SCC-only. |
| Incident and contamination audit | Original operator/regulator notices, timestamped market-status sequence, scheduled macro releases, exchange rule or halt notices, data-vendor incident status | 2015-07-08; pre-halt through recovery | SEC source already pins formal interval and documents degradation. A public chronology of what participants knew and a systematic same-day news screen remain **TO_OBTAIN**. Store public source metadata locally; no licensed event rows locally. |

## Minimum checks before treating a case as estimable

1. Confirm a timestamp basis for each feed and quantify inter-feed clock error; do not merge participant time and SIP time as though identical.
2. Resolve exact ES contract and its active session; use a tradable contract rather than a back-adjusted continuous series for execution/quote comparisons.
3. Build per-SPY-share basket value from historical quantities, same-time prices, and cash/fees where applicable. `sum(weight × raw stock price)` is not an ETF value.
4. Retain invalid, cancelled, stale and no-update states distinctly. A lack of a valid quote cannot be silently filled with a future value.
5. Confirm which venues stayed executable, not merely which data feeds emitted messages. Alternative venues are substitution outcomes and cannot automatically be untreated controls.

## Excluded-event data gaps

The Xetra, Euronext and ISE rows are preserved as factual candidates, but no acquisition request follows from them. Their operator sources respectively lack an auditable interval/alternative-channel scope, affect cash and derivatives jointly with corrected closing records, or lack contract/alternative-venue scope.  No current SCC coverage of their data is asserted.

## Explicit non-actions

No data were bought, no vendor account or agreement was changed, no WRDS connection was made, and no SCC raw file was opened in this subtask.
