# P1 checkpoint 07 — package/clock sidecar and W021 source repair

2026-09-15. Evidence status remains **HOLD_DATA**, not design failure and not GO. This checkpoint implements the factual action requested by the independent scientific referee. It does not estimate effects or power.

## Completed package/clock result

The versioned sidecar represents 17 predecessor series as nine distinct packages and preserves the difference between legacy pre-effective holdings and later strict-pre-announcement holdings. It keeps W006's unrelated DFA and JPM chains separate and W032's proposed November dates separate from December implementation evidence.

For the exact recovered-99 denominator, 99 candidates produce 120 candidate/other-wave keys: 45 observed links and 75 no-match keys in the pinned, incomplete exposure version. Sixty-four exact candidate-pair-series membership rows were linked. Twenty-five pair-level facts robustly meet the contract's other-conversion condition, covering 17 distinct candidates: W002 H6/L1, W016 H3/L5 and W025 H1/L1. The remaining 82 candidates are **not certified clean**; no-match and incomplete-calendar states remain unknown.

Six date/package fixtures passed. A 20-candidate pilot preceded the full protected join. Full mode is hash-gated by the current contract, code, facts, mapping, manifest and pilot receipt. Direct full-mode bypass and stale-pilot input tests both fail before protected input is read. Row-level results remain on SCC; only permitted public facts, aggregates, code and receipts are archived here.

## W021 factual repair

The December 15, 2022 JPMorgan public conversion supplement proves that the formerly selected December 31 holdings report is post-announcement. A public NPORT-P for series `S000032550` was located and acquired on SCC: report date September 30, filed November 23, accession `0001752724-22-263385`. The immutable XML has SHA-256 `cb68bd2cd53956060fd3d27a3224450628ff5e086580b1d992ee172a2f86aa2d`.

A source-side projection contains 41 positions and 39 common-equity candidates under the pre-existing parsing convention. These are candidates, not final historically eligible securities. The initial backtrace checked only indices and was superseded. Final coordinator verification restored all predicates, passed 11 synthetic assertions, and compared all 14 exported fields for the first 20 positions to the raw XML without printing row values. Historical mapping, denominator, split consistency and exposure/tier reconstruction are the active next stage.

Read the [sidecar result](artifacts/fund_package_clock_facts_20260915/README.md), [execution receipt](artifacts/fund_package_clock_facts_20260915/EXECUTION_RECEIPT.json), [W021 source locator](artifacts/w021_preannouncement_holdings_locator_20260915/SOURCE_LOCATOR.md), and [fieldwise correction](artifacts/w021_preannouncement_holdings_locator_20260915/COORDINATOR_CORRECTION.md).

## Active continuation

An existing Terra/medium executor is constructing W021's date-valid CUSIP-to-PERMNO mapping and report-date shares denominator from harvested SCC metadata. No current-ticker shortcut, price/volume/return fields, live WRDS call or quote purchase is permitted in that repair. Final support, numerical rank, identification and calibrated power remain NOT_RUN pending the repaired population.
