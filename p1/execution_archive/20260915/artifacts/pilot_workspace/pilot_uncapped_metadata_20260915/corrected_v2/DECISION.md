# P1 uncapped metadata census — coordinator decision

Date: 2026-09-15. Research status: **HOLD_DESIGN + HOLD_DATA**.
This bounded metadata execution is complete; no empirical power or treatment effect was calculated.

## What changed

The one corrected SCC full run preserved all 2,794 H/L stock-wave candidates. Of these, 2,592 have valid mappings in the existing metadata view; 202 remain unresolved, not classified as having no earnings.

Removing the acquisition cap increased PRE/POST exact metadata keys from 29,729 to 61,486. This is a substantial retrieval loss recovered, not a doubling of independent observations or identification strength. The unchanged source window is [2019-01-01, 2026-09-01), not a newly approved analysis window.

## Decision-relevant support

Using only the unverified 09:30–15:00 source-display clock, 72 stock-wave keys have at least one PRE and one POST record before applying cached analyst coverage. In the existing proposed overlap-clean stratum, only 16 have this support:

| Wave | High, before cached min2 | Low, before cached min2 | High, cached min2 | Low, cached min2 |
|---|---:|---:|---:|---:|
| W002 | 1 | 14 | 0 | 2 |
| W013 | 0 | 0 | 0 | 0 |
| W016 (stress) | 0 | 1 | 0 | 1 |
| W021 | 0 | 0 | 0 | 0 |
| W025 | 0 | 0 | 0 | 0 |

Unknown analyst coverage on newly retrieved keys is not a failed eligibility test. These counts do not certify ET/RTH, economic-event uniqueness, final PRE-announcement ownership eligibility, six-horizon measurement, or the contract's stricter standardization support. Unknown overlap and the 202 unresolved candidates prevent treating this known-clean subset as a complete-population upper bound.

Nevertheless, the currently evidenced subset does **not** establish the original multi-wave high-versus-low comparison. More quote files alone cannot establish missing comparison cells or independent conversion shocks. No supported claim of adequate power follows from this census, and this is not a NO_GO for every MF-to-ETF design.

## One next action

Complete versioned, outcome-blind analyst-coverage metadata for the already observed nominal-clock/known-clean PRE and POST keys, prioritizing the sole W002 high candidate. Reuse the existing licensed custodian process only within its approved source/field scope; retain unknowns otherwise. Do not buy another blanket quotation panel, extend the population, or switch session/inference to manufacture support. This targeted step resolves whether the presently observed W002 comparison survives the analyst requirement; it cannot by itself establish the missing multi-wave design.

## Execution boundaries and routing

The implementation worker was the existing `pilot_design_build` agent (recorded requested routing: gpt-5.6-sol / medium). Backend model/effort telemetry: NOT_OBSERVED. No new high-model reviewer or nested delegation was launched. The coordinator inspected final receipts and the decisive support summary; the separate lineage verifier is a script, not a separate AI referee.

Twelve synthetic fixtures and 20 actual mapped-row lineage checks passed before the full run. Protected rows remained on SCC. No financial, forecast, quotation or response values were read; no purchase, effect estimation, empirical power run, commit or push occurred. See `RUN_RESULTS.md`, `EXECUTION_RECEIPT.json` and `scc/full/` for the completed evidence.
