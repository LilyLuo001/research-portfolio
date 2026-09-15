# Continuation checkpoint 01

Research remains HOLD_DESIGN + HOLD_DATA. These completed stages do not certify the full pilot, RTH eligibility, power or a treatment effect.

## Completed

1. **Fixed W002/high metadata comparison:** exactly four keys / one candidate / three PRE and one POST, using the frozen selection rules. Core and rescue `allcols_detu_epsus` have the same observed aggregate analyst support: one zero-ID key and three one-ID keys, four matched metadata rows in total. No new observed >=2 support was recovered from that alternative. Source-row/multiset identity was not tested and the families were not pooled. The first broad-filter attempt is invalid and excluded. See [reconciliation](artifacts/scc_detail_reconciliation_20260915/README.md).
2. **Implementation checks:** seven executable synthetic tests passed on the saved script with in-memory I/O. The single-CUSIP guard was added after the source run; the new code hash is not represented as the original source-run hash. See the executed test receipt, not merely the earlier worker checklist.
3. **Historical calendar:** 1,926 XNYS core sessions in [2019-01-01,2026-09-01), including 15 early closes. Eighteen fixture checks passed. Source schedule is versioned to exchange_calendars 4.13.2 / tzdata 2026.4. This resolves calendar boundaries, not IBES timezone, first-public semantics or uncertainty. See [calendar](artifacts/exchange_calendar_20260915/README.md).

## Next packet in progress

Check the fixed 202 previously unrepresented candidates against separate SCC core and rescue `actu_epsus` metadata sources. No new candidate universe, live WRDS access, raw values, competing-conversion rule changes or automatic tier/session adoption. Source inventory and permitted schemas are located; implementation/pilot/full-recovery receipts will be delivered in a separate increment.

Requested execution: Luna/low for the fixed-key comparison; retained Sol/medium for calendar and recovery implementation. Coordinator added executable synthetic verification after finding the worker's initial test record lacked a runnable harness. Backend telemetry NOT_OBSERVED; no high-model referee launched.

This increment publishes eleven source artifacts plus its index and status. Original snapshot and raw data remain unchanged. No purchase, empirical power or observed POST response computation occurred.
