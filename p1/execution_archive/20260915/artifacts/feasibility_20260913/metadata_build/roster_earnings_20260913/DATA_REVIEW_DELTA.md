# Independent E007 roster and earnings-metadata review delta

Date: 2026-09-13. Reviewer: separate agent `/root/p1_census_data_reviewer`. Requested routing: `gpt-6-astra`, reasoning `high`. Actual model/effort telemetry: **NOT_OBSERVED**. Usage: **NOT_OBSERVED**. This review is an independent analytic pass, not a claim that model errors are statistically independent.

**Verdict: PASS for the final v2 execution of this pinned E007 retrieval seed, conversion-date-valid identifier bridge, and eight-field source-record projection.** This does not approve an economic earnings-event census, announcement-clock eligibility, session classification, causal sample, or estimator. The earlier metadata review's unexecuted-adapter status is superseded for this specific executed projection and these hashes only.

## Independent reproduction

The reviewer read the existing E007 exposure metadata and local seed, then ran read-only Python on SCC using `/share/pkg.8/python3/3.12.4/install/bin/python3 -B`. No source-side file was created or changed by the reviewer. No row-level licensed metadata was returned to the local workspace or conversation. All printed results were counts, field names, hashes, or other aggregate validation flags. No EPS/forecast/SUE value, price, quote, return, CAR, outcome, or estimation column was projected or inspected. Only this review file was written locally.

1. **Seed PASS.** E007's `primary_ready == True` projection exactly matches all 8,801 seed rows, including seven retained metadata fields and original line locators. The seed has 3,440 PERMNOs and 30 waves. All announcement-eligibility labels remain `UNKNOWN_NOT_EVALUATED`. The SCC input copy has the same SHA-256 as local `out_v3/seed_stock_wave.csv`. The other 25 E007 rows are outside this retrieval seed; readiness is not strict pre-announcement eligibility.

2. **Bridge PASS under its stated retrieval rule.** The reviewer independently projected only `permno,ncusip,sdate,edate,score` from the archived historical link, filtered to seed PERMNOs. A PERMNO equality join followed by `sdate <= effective_date <= edate` (missing end allowed by code) reproduces every delivered usable mapping row exactly. The candidate CUSIP set also matches exactly. No ticker or static identifier mapping is used. There are no nonmissing unparseable start/end dates and no open-ended mapped rows in this run.

3. **Projection PASS.** The reviewer independently read only `ticker,cusip,pends,pdicity,anndats,anntims,actdats,acttims` from each of the eight annual source partitions on SCC, applied the delivered candidate-CUSIP set and `2019-01-01 <= anndats < 2026-09-01`, and regenerated the CSV entirely in memory. Its SHA-256 exactly matches the delivered source-side metadata file: `97a3c35c1f59013047924b89859df67ff361327a61b7bec0a28bdf3412c562cb`. The delivered CSV header is exactly those eight columns plus `source_partition`; there is no value column.

4. **Aggregate PASS.** Independent aggregation reproduces all record, parseability, duplicate-key and annual counts below. The final v2 receipt correctly names the 3,339 covered identifiers `candidate_cusips_with_source_records`; these are not a verified count of PERMNOs, issuers or economic securities. The source-record count is explicitly not an economic-event count. The v2 mappings, candidate list and projected metadata are byte-identical to the independently reproduced v1 files. Its aggregate equals the independently verified earlier aggregate except for this corrected field name and the new projection-receipt hash.

| Bridge quantity | Independently reproduced |
|---|---:|
| Seed stock-wave rows | 8,801 |
| Historical-link rows after PERMNO filtering | 5,065 |
| Usable mappings valid at conversion effective date | 8,516 |
| Seed rows with a usable mapping | 8,516 |
| Seed rows without a mapping | 285 |
| Seed rows with multiple usable mappings | 0 |
| Date-valid rows with invalid eight-character identifiers | 0 |
| Distinct candidate CUSIPs | 3,344 |
| Retained mapping rows with score 1 | 8,510 |
| Retained mapping rows with score 2 | 6 |

All date-valid usable links were retained; no score threshold was selected. Zero ambiguous rows under this operational rule is not proof of economic identity quality.

| Projection quantity | Independently reproduced |
|---|---:|
| Metadata source rows projected across eight partitions | 207,343 |
| Candidate source records in the date window | 103,876 |
| Distinct candidate CUSIPs with records | 3,339 |
| Candidate CUSIPs without records | 5 |
| Records with parseable announcement dates | 103,876 |
| Records with parseable announcement times | 103,876 |
| Records in duplicate full source-key groups | 0 |
| Records in duplicate CUSIP/period/periodicity groups | 0 |

| Source partition year | Candidate records |
|---|---:|
| 2019 | 12,155 |
| 2020 | 13,089 |
| 2021 | 14,179 |
| 2022 | 14,834 |
| 2023 | 14,618 |
| 2024 | 14,279 |
| 2025 | 13,677 |
| 2026 | 7,045 |

The duplicate source key is `(cusip,pends,pdicity,anndats,anntims,actdats,acttims)`; the period key is `(cusip,pends,pdicity)`. Zero duplicates under these keys does not choose a revision/economic-event rule. Parseable clock strings do not establish timezone, exchange session, release provenance, or timing precision.

## Remaining limits and blockers

- Bridge validity is checked at the E007 **conversion effective date**, not at each returned earnings-record date. The union of candidate CUSIPs retrieves historical records across the requested window; those records have not been joined back to a PERMNO/wave using validity at announcement time. CUSIP reuse, changing identifiers and competing conversions therefore remain analysis-eligibility questions.
- The bridge preserves score 2 links as well as score 1 links. This is an explicit retrieval policy; it is not a signed mapping-quality threshold for analysis.
- The final v2 projection now enforces both candidate-set cardinality and exact candidate-file SHA-256 against the bridge receipt, before creating outputs or reading raw parquet. An independent in-memory same-cardinality/wrong-hash test rejected the substituted seed, with zero output-directory and raw-parquet-reader calls. The v2 bridge receipt, delivered candidate hash and projection receipt agree. This fixes the initial cardinality-only guard; it does not certify the bridge's economic mapping policy for analysis.
- Source-column exclusion is established by the reviewed code, exact output schema and independently regenerated metadata output. Receipts are not a general access log for unrelated activity outside this bounded task.
- The 285 unmapped seed rows and five candidate CUSIPs without records remain explicit retrieval gaps. E007 authority, strict pre-announcement holdings/public-availability eligibility, public announcement-clock uncertainty, point-in-time earnings linkage, revision rules, timezone, exchange/session rules, horizon/SPY coverage, controls and signed sponsor components remain unresolved. No RTH/non-RTH count, economic-event count, post-treatment response, or scientific GO is certified.

## Hash binding

All hashes are SHA-256. `LOCAL` is `/Users/lilyluo/research-portfolio-p1-feasibility-20260913/p1/feasibility_adjudication/20260913/metadata_build/roster_earnings_20260913`; `RUN` is SCC `/projectnb/econdept/qluo/P1_Refraction_WRDS/p1_roster_earnings_20260913`. Raw historical link is under SCC `/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw`.

| Artifact | Exact SHA-256 |
|---|---|
| E007 `exposure_stock_wave_all.csv` | `905b7faa844a3a415f5b6c42d0e8de4c1fa28060efe16370182ef86df20b7320` |
| LOCAL `out_v3/seed_stock_wave.csv`; RUN `input/seed_stock_wave.csv` | `0c5d9175d53e76d746777776c2ff3ee46cc038f7227120eb22e86077a6d05555` |
| LOCAL `out_v3/ROSTER_RECEIPT.json` | `562ac06c013867c197f3f64045fb636ccec52d470458a0a25a0433800a43200c` |
| LOCAL `code/build_roster.py` | `784417b7272fa85c6e6a087d8b6122fb72a2e957f269e1bc3df61da26d4e42cc` |
| LOCAL `pit_execution/build_pit_bridge.py` | `9fee90690827f9963474a5b978a16de34bd361adfe5a86eeac0374c6e39ffebf` |
| Historical `crsp_ibes_link_full.parquet` | `fd259ac817ab9ea64553e0cdacadc22fcd94de361d1f1851855f9e27ed87e326` |
| RUN `pit_bridge_v2/pit_bridge_receipt.json`; LOCAL `receipts_v2/pit_bridge_receipt.json` | `3b2e7c4880d45e258ecf41992cb85c5bc3ec7906cea9939f62e83a3334106799` |
| RUN `pit_bridge_v2/date_valid_pit_mappings.csv` | `1f2df97548ef4bfcb783d0b09f04b348130356135effdd392016fd3b69623878` |
| RUN `pit_bridge_v2/seed_mapping_status.csv` | `8b2b67bbab2cd3e61cafef968cdd4242413b9cef9d180e2810cd0e114562c9d3` |
| RUN `pit_bridge_v2/candidate_cusips.csv` | `68f39fbb19803dc2c63ecaf0754a1b9c900c27af1ec5ba3fd1b3d84764ce3d87` |
| LOCAL `../code/custodian_projection.py` | `8796a465b9b51384319652ad901a4f1513331313f0a78c1b6d73c4287ba86ae1` |
| RUN `ibes_metadata_projection_v2/ibes_projection_receipt.json`; LOCAL `receipts_v2/ibes_projection_receipt.json` | `2618fd2d5e8d431920dbe90ccf3393379a7bf84083ee20a01feea56be60ec2ac` |
| RUN `ibes_metadata_projection_v2/ibes_announcement_metadata.csv` | `97a3c35c1f59013047924b89859df67ff361327a61b7bec0a28bdf3412c562cb` |
| RUN `ibes_metadata_projection_v2/earnings_metadata_aggregate.json`; LOCAL `receipts_v2/earnings_metadata_aggregate.json` | `70849963654933e4b6901fb532910fb186f100b30b2ce6c98f1153cd22e45605` |
| LOCAL `pit_execution/aggregate_ibes_metadata.py` | `ee4b0a09ae9f54dab64d3c105f8f2a2ad7ef0ff64a951022e5dbdcfa947de901` |

The eight annual raw-source hashes are recorded in the pinned projection receipt. This reviewer independently regenerated its output through eight-column projections, rather than claiming a separate full-file checksum audit of all licensed source partitions. A changed seed, mapping policy, query, receipt or delivered output requires a fresh targeted verification.
