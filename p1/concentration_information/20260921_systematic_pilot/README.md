# Systematic pilot — execution checkpoint

Status: SUPPORT_STAGE_EXECUTED / EMPIRICAL_RELEASE_BLOCKED. This is not a completed test of the research hypothesis. See `DECISION.md` for the scientific disposition.

## Actual findings

The corrected SCC holdings census binds the original 32-event, eight-issuer inventory. It reads 307 holdings partitions from 2022–2023 and six historical fund-header partitions; licensed rows stay on SCC. Including 2022 eliminates the earlier artificial January gap.

| Diagnostic, denominator 32 events per fund | QQQ | SPY |
| --- | ---: | ---: |
| Prior-or-same-calendar-date holdings report exists | 32 | 32 |
| Issuer ticker-group represented in that report | 16 | 32 |
| Latest report's maximum vendor eff_dt no later than event date | 21 | 19 |
| Holdings report date equals event date | 1 | 1 |

These are report/ticker-group diagnostics, not verified event-time holdings or issuer-level Top/Rest assignments. A monthly report is not the actual contemporaneous basket; eff_dt is not established first-public availability. A report failing the date proxy does not imply no older usable report exists. The 32-event inventory contains 25 event dates and is not a frozen research population.

Six technical announcement probes yield three premarket and three after-hours source timestamps, none RTH. XOM July has a 30-minute issuer/wire disagreement; Microsoft April's 16:07 notice says results are already available and cannot be treated as the initial release. These sources improve clock evidence, but do not release primary outcomes. Source-time classification is not a certified first-public census.

The new exact-PSD validator passed 19 combined engineering/independent tests, and the reviewer separately reran 15 prior adversarial fixtures through the wrapper. This fixes a numerical defect; it does not validate empirical covariance calibration, identify causality, or show power.

The SCC quote-state projection completed on all 29 files, yielding 456 file-source cells. The 70-row summary retains all seven clock variants × two ETFs × five datasets, including zero-file gaps. Eight distinct variant×ETF pairs have at least one single file with all six endpoints observed, positive/noncrossed, and within the required header coverage. This includes a notice-only Microsoft clock and both XOM July variants; it is not eight independent releases or approved news responses. UNH has no candidate file. Across file cells, 265 have unavailable observed states, 104 have interval age ≤1s, 52 have age >1–60s and 35 >60s; those ages do not prove quote invalidity. No conflicting same-timestamp state was observed. No continuous-live or actual-basket certification follows.

## Artifacts and boundaries

- `EXECUTION_SCOPE.md`: approved scope and requested routing.
- `ANALYSIS_CONTRACT.yaml`: specified, not empirically released.
- `CONTRACT_REVIEW.md`: independent method/contract findings.
- `CLOCK_SUPPORT.csv`, `clock/`: actual public timestamp evidence and receipts.
- `data/holdings_census_aggregate.json`, `data/holdings_census_receipt.json`: actual corrected SCC outputs.
- `data/census_holdings_support.py`: reproducible bounded holdings query.
- `data/prepare_quote_manifest.py`, `data/quote_state_diagnostic.py`: executed bounded file/header and boolean-only diagnostics.
- `data/QUOTE_INPUT_MANIFEST.json`, `data/DIAGNOSTIC_RELEASE.json`, `data/QUOTE_SUPPORT_RESULTS.json`, `QUOTE_SUPPORT_TABLE.csv`: exact inputs, reviewed release and actual results.
- `DIAGNOSTIC_CONTRACT.json`: seven timestamp variants for six probes; not the primary research contract.

Early engineer outputs used a wrong issuer roster and were invalidated. `data/DATA_SUPPORT.md`, `data/holdings_event_support.json`, and `data/source_support_matrix.csv` preserve that disposition, not authoritative support counts. No invalidated count is used above.

No primary effect, empirical power, equivalence conclusion, or research GO has been produced. No data were purchased. Raw inputs were not changed. An isolated SCC scratch environment with Databento 0.86.0 / databento-dbn 0.69.0 was installed and used because the previously asserted SDK module was not actually available. Public search snippets incidentally exposed release values; they were not used as signals, sample rules, or response data (see clock exposure log).

Next bounded step: the single SPY event-level basket-and-news admissibility packet specified in `DECISION.md`. Do not restart the old project audits or purchase quotes to solve missing basket/news provenance.
