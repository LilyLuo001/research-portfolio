# Independent Stage-A review

## Decision

**`HOLD_NAMED_INPUT` — A-stage measurement gate: FAIL/HOLD.** Do not create `EVENT_PIPELINE_RELEASE.json`; do not open forecast, actual EPS or quote values; do not download constituent quotes; and do not make treatment, response, power or hypothesis inferences.

The decisive failure is the absence of a dated, pre-anchor actual SPY holdings or portfolio-composition record with usable quantity units, cash treatment, corporate-action treatment and availability provenance. The I/B/E/S metadata identify a plausible exact issuer/period candidate, but the point-in-time consensus and comparable-unit rule are not yet certified. The 06:30 ET clock is an operational candidate, not a proven earliest-public time.

This is an aggregate-only review. I executed the two metadata-only SCC programs against licensed files in place; I did not independently decode or export raw licensed rows.

## Version binding and execution

Reviewed final artifacts:

| Artifact | SHA-256 |
| --- | --- |
| `code/stage_a_scc_probe.py` | `bfc5939ae1bacbc1c15492e6497a1ed9874d8927767e7a3f68d0b7e7128160a9` |
| `stage_a_probe_aggregate.json` | `d2f7133db078219451dbb34b207daab42303bba304129501dd7b0ed7763b5969` |
| `code/independent_stage_a_recompute.py` | `e1ef79d1503bfd8172e7aa34328ea7b2d85d5b01e0dc9f754fb763a3cf3b04b2` |
| `independent_stage_a_recompute.json` | `e1ef18056f83b184068b12f5ab9fc620b07a17942451fa27351dd1df74bd84d3` |
| `SOURCE_MANIFEST.json` | `d2001d7c61caf9b42e7a7b149b8a5420b2271846fab8e60bb7bf5698951161b7` |
| SCC I/B/E/S Detail source | `9544b0ed865581359a2b2b69c4af4a2286e847af0adba8bf98fb3d099d51a4b5` |
| SCC I/B/E/S Actual source | `e774cc2e823249c58f6131f284ad4ece1baaf00208f635316074b578c8f60ba1` |

The engineer export initially did not match final code: it retained the pre-patch key `impossible_null_permno`, showed zero exact-CUSIP rows, and the receipt said final code had not been rerun. I copied and executed the final script on SCC, corrected the null-ID/add/drop aggregation and exact-CUSIP period join, replaced every broad Parquet/CTE projection with an explicit metadata-only column list, reran it, then executed a separately written aggregate recomputation with the same projection restriction. The two final outputs agree on every decisive count.

Commands executed:

```text
python3 -m py_compile code/stage_a_scc_probe.py
scp -q code/stage_a_scc_probe.py qluo@scc1.bu.edu:/scratch/qluo/spy_xom_event_packet_20260921/stage_a_scc_probe.py
ssh -o BatchMode=yes qluo@scc1.bu.edu '/scratch/qluo/systematic_pilot_support/dbn_runtime/bin/python /scratch/qluo/spy_xom_event_packet_20260921/stage_a_scc_probe.py'
scp -q qluo@scc1.bu.edu:/scratch/qluo/spy_xom_event_packet_20260921/stage_a_probe_aggregate.json ./stage_a_probe_aggregate.json
python3 -m py_compile code/independent_stage_a_recompute.py
scp -q code/independent_stage_a_recompute.py qluo@scc1.bu.edu:/scratch/qluo/spy_xom_event_packet_20260921/independent_stage_a_recompute.py
ssh -o BatchMode=yes qluo@scc1.bu.edu '/scratch/qluo/systematic_pilot_support/dbn_runtime/bin/python /scratch/qluo/spy_xom_event_packet_20260921/independent_stage_a_recompute.py'
scp -q qluo@scc1.bu.edu:/scratch/qluo/spy_xom_event_packet_20260921/independent_stage_a_recompute.json ./independent_stage_a_recompute.json
shasum -a 256 code/stage_a_scc_probe.py stage_a_probe_aggregate.json code/independent_stage_a_recompute.py independent_stage_a_recompute.json
test ! -e EVENT_PIPELINE_RELEASE.json
```

## Decisive recomputation

### SPY snapshots and missing-ID semantics

Both programs used CRSP portfolio number `1021980` over the already permitted 2022/2023 holdings files.

| Item | 2022-12-31 report | 2023-01-31 report |
| --- | ---: | ---: |
| rows | 505 | 505 |
| valid distinct `permno` | 501 | 501 |
| rows with missing `permno` | 4 | 4 |
| sole `eff_dt` | 2023-01-09 | 2023-02-07 |

The latest strictly prior report is 2022-12-31. Comparing only valid security IDs yields 500 overlaps, one drop and one addition. The earlier full outer join's apparent five drops/five additions was wrong: it counted four null-ID rows on each side as unmatched positions. A null `permno` is a missing security ID, not an identity, and cannot establish membership change.

There are 500 comparable valid-ID share pairs and 500 distinct ratios after rounding to ten decimals. This is only a file diagnostic. It cannot establish economic non-proportionality without the applicable fund-share/Creation-Unit denominator, cash, corporate actions and units. The hold does not rely on that ratio count.

The 2022-12-31 report's `eff_dt=2023-01-09` precedes the event, but that establishes neither its public/vendor availability time nor that it represents the actual portfolio or creation basket at 2023-01-31 06:30 ET. The 2023-01-31 report's `eff_dt=2023-02-07` is after the anchor. Therefore neither snapshot qualifies as the required event-time input.

### XOM I/B/E/S identity, period and pre-anchor rule

Final code uses exact eight-character CUSIP `30231G10` on both Actual and Detail. The period join is `Detail.fpedats = Actual.pends` and the measure is exact `EPS`; ticker is not used as an identity key. This corrects the stale ticker-based/zero-row output.

Recomputed metadata-only counts are:

- two exact-CUSIP Jan-31 EPS Actual metadata rows;
- one exact quarterly Actual period candidate for 2022-12-31;
- 41 Detail records passing the nominal 90-day announcement-date and pre-anchor activation cutoff;
- 18 distinct analyst/estimator keys;
- two distinct FPI codes; and
- 41/41 Detail records with missing currency metadata.

No forecast or actual EPS value column is named or projected by either script. The count query also does not deduplicate or construct a consensus.

This component is not Stage-B ready. Before a value query, source documentation or version evidence must establish the activation time's time zone and point-in-time/first-vintage meaning, FPI periodicity semantics, revision/withdrawal status, currency, split/share basis, GAAP-versus-adjusted definition, and the deterministic latest-pre-anchor record per analyst/estimator. The issuer release itself reports both GAAP and adjusted EPS, so `measure='EPS'` alone does not prove definition comparability.

### Public clock and ETF basket claims

Nasdaq's Business Wire republication displays “Jan 31, 2023 6:30am EST,” supporting 11:30 UTC as an operational candidate. The [issuer release](https://corporate.exxonmobil.com/news/news-releases/2023/0131_exxonmobil-announces-full-year-2022-results) confirms the date and content but its current page does not display a publication minute. The packet therefore may not say the issuer and Nasdaq independently agree at 06:30, and neither source proves no earlier distribution. The fixed 06:29/06:30/06:31 ET sensitivity remains acceptable because it is declared without reference to returns.

The [January 27, 2023 SPY prospectus](https://www.sec.gov/Archives/edgar/data/884394/000119312523017928/d449477d497.htm) distinguishes common stocks actually held by the Trust (“Portfolio Securities”) from Index Securities and describes 50,000-Unit creation/redemption transactions with separate cash components. It does not provide the 2023-01-31 event-time basket. State Street's [current authorized-participant resources](https://www.ssga.com/us/en/intermediary/resources/authorized-participants) list authenticated Daily Portfolio Composition (“Basket”), Cash in Lieu, Balancing Cash and Daily SPDR ETF Holdings files. That supports a specifically named source family but does not establish that the historical 2023-01-31 files are available or what time they were published. A creation basket/PCF also must not be relabeled as complete actual holdings without evidence.

The archived quote files are only header-level evidence for four venue-specific `bbo-1s` feeds. They are not SIP NBBO, not a full-market composite, and not proof of constituent coverage or endpoint reconstruction.

## Required repairs before any Stage-B review

1. Obtain, or document unavailability of, State Street's historical SPY daily holdings and portfolio-composition/cash package applicable before 2023-01-31 06:30 ET. Bind exact file hashes, economic date, publication/vendor-observation time, security IDs, quantity denominator, cash/CIL/balancing cash and corporate-action rules.
2. State whether the recovered object is actual Trust holdings, a creation/redemption basket, or another proxy. Do not substitute one for another. If only the CRSP lagged report is proposed, issue `SPEC_AMENDMENT_PROPOSED` for PI approval and state that the actual event-time basket claim is lost.
3. Resolve the I/B/E/S field/version semantics listed above, implement the prespecified status and latest-record deduplication rule using exact CUSIP `30231G10` plus the exact fiscal period, and rerun metadata-only validation before exposing values.
4. Only after an actual basket is approved, generate the historical-ID-by-date-by-venue/schema quote request matrix and verify complete coverage. Do not silently drop or renormalize missing constituents.
5. Bind the repaired packet, code, source manifest and independent review hashes in a new event-specific release. Until then, retain `EVENT_PIPELINE_RELEASE.json` as absent.

## Boundary and routing record

Review completed 2026-09-21T15:22:16Z locally; SCC clock observed 2026-09-21T15:22:17Z. Values read: forecast `false`, actual EPS `false`, quote `false`. Licensed rows exported: `false`. Purchases: USD 0. Authentication changed: `false`. Release created: `false`. Treatment/power inference: `NOT_RUN`.

Requested reviewer route: `gpt-5.6-sol / high`. Dispatch was accepted by the parent orchestration, but actual backend/model telemetry and token accounting were not exposed to this reviewer: `NOT_OBSERVED`. No nested delegation was used.
