# P1 concentration-information empirical decision

This is the executed 2026-09-21 continuation, not another proposed research plan. It uses existing SCC data and keeps licensed row-level records on SCC. Historical P1 stages are preserved.

## Read first

1. [Scientific decision and next action](PRECISION_AND_DECISION.md)
2. [Actual daily/network results](daily_network/ACTUAL_RESULTS.md)
3. [Independent finite review](INDEPENDENT_REVIEW.md)
4. [Minute-data feasibility](intraday/INTRADAY_FEASIBILITY.md)

The strong concentration/ETF causal story is not established. The broad unsigned daily response and broad adjusted network slope are negative in the development sample. A positive same-industry association remains exploratory. Shared control windows prevent treating the printed event-block intervals as a fully adjusted precision assessment. No empirical power, causal effect or research GO is claimed.

## Evidence and reproduction map

| Deliverable | Location |
| --- | --- |
| Frozen analysis plus disclosed amendments | `SPEC_AMENDMENT.md`, `analysis_config.json`, `daily_network/RUN_CHRONOLOGY.md` |
| Daily aggregate table | `daily_network/results/PUBLIC_DAILY_NONMECHANICAL_RESULTS.csv` |
| Same-mask absolute basket secondary | `daily_network/results/PUBLIC_MATCHED_BASKET_ABSOLUTE_SUPPLEMENT.csv` |
| Issuer-specific network table | `daily_network/results/PUBLIC_ISSUER_RECEIVER_NETWORK_RESULTS.csv` |
| Attrition | `daily_network/results/PUBLIC_SAMPLE_ATTRITION_AND_DEPENDENCE.csv` |
| Control reuse and calendar dependence | `daily_network/results/PUBLIC_CONTROL_REUSE_AND_DEPENDENCE.json` |
| Leave-one-event-block sensitivity | `daily_network/results/PUBLIC_LEAVE_ONE_BLOCK_OUT.csv` |
| Corrected industry mapping receipt | `daily_network/results/PUBLIC_NETWORK_REPAIR_RECEIPT.json` |
| Source-date coverage audit | `daily_network/results/PUBLIC_DAILY_INPUT_AUDIT.json` |
| Initial full run receipt and final-code chronology | `daily_network/results/PUBLIC_RUN_SUMMARY.json`, `daily_network/RUN_CHRONOLOGY.md` |
| Source-specific intraday reproducer and aggregate | `intraday/run_existing_file_initialization_diagnostic.py`, `intraday/EXISTING_FILE_INITIALIZATION_DIAGNOSTIC.csv` |
| Public macro dates | `public_macro_calendar.json` |
| Actual role dispatch | `COORDINATION.md` |
| Final small-artifact hashes | `ROUTING_AND_RUN_RECEIPT.json` |

The public summary of an earlier execution is historical evidence, not a claim that later repaired code produced that original run. Follow the chronology, targeted-repair receipt and independent review for final provenance.

SCC scripts are in `daily_network/`; job scripts contain the exact existing mirror paths. Do not run them from a laptop expecting raw data to be present. The final integration receipt hashes only this small publication directory, never the raw archive. It intentionally excludes itself from its hash manifest.

## Important execution limits

- H1 daily returns alone entered the estimates. An earlier full-year delisting read loaded 452 H2 records in process; no H2 value entered the H1 estimates or model-visible output. The final source predicate is corrected and the deviation is disclosed, not erased.
- Source-date coverage is not a certification that every share class had a valid return.
- Daily two-session responses are not minute price-discovery measurements.
- The optional date-bundle exposure secondary is `NOT_RUN`; executed network regressions use issuer-event observations and disclose repeated receiver responses.
- No new Databento query, purchase or subscription was made in this stage.
- This directory contains no raw licensed security/response panels or credentials. No merge is authorized or performed.
