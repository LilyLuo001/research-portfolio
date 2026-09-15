# Source selection and authority

**Execution:** SCC `scc1.bu.edu:/usr3/graduate/qluo/dax-codex`, read-only source inspection on 2026-09-13.  Owner authorization is Lily Luo's 2026-09-13 instruction in this task.  The executor was the protected-view engineer; no source was modified and no output was written to SCC.

## Versioned sources compared; no authority choice made

| Role | Versioned source | SHA-256 / lineage | Decision |
|---|---|---|---|
| Free-path exposure membership | SCC `p1/conv_exposure_free.parquet` | `350c3c7...a5d2b4e7`; lineage timestamp 2026-07-19 | Separate free-path version |
| Reconstructed exposure membership | `/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure/exposure_stock_wave_all.csv` | `905b7faa...f20b7320`; evidence `E007` | Separate reconstructed version |
| Reconstructed lineage | `/Users/lilyluo/research-portfolio-p1-advanced-readonly/p1/exposure/exposure_construction_lineage.json` | `c0c0f817...5aaff4a`; evidence `E011` | Confirms implementation inputs, not scientific validity |
| Exposure provenance | `p1/conv_exposure_free.parquet.lineage.json` | output lineage declares inputs `events_merged.csv` and `t2_wrds/waves.csv` | Used to verify, not pooled |
| Conversion chronology | `p1/events_merged.csv` | lineage input of the selected parquet | Used only for date-level conversion linkage |
| Identifier mapping | `p1/t2_free/conv_exposure_free_crosswalk.csv` | ancillary public crosswalk | Mapping audit only; not an exposure substitute |

The SCC checkout does not contain the reconstructed CSV.  The SCC crosswalk (2,247 identifier mappings) is **not** that CSV and was not treated as one.  Source inventories are separate: the free parquet has 49 waves/6,377 cells; the reconstructed CSV has 30 waves/8,826 cells.  They share 20 effective dates, with 29 free-only and 10 reconstructed-only dates.  Stock membership cannot be compared: the free version has CUSIP keys while the reconstructed version has PERMNO keys and no validated cross-source bridge was supplied.  No source is selected as sole authority and no sources are pooled.  The recommended authority decision remains pending a versioned, point-in-time key bridge plus provenance reconciliation.

## Permitted computation and output boundary

Allowed inputs were conversion dates, exposure membership/dose metadata and identifier metadata.  The computation grouped stock-by-wave cells, joined only conversion-calendar metadata, and calculated ternary-tier feasibility and reuse counts.  Returned fields are counts, dates, presence flags and source receipts.  No EPS, forecast, SUE, price, quote, return, CAR, coefficient, p-value, ranking, or response value was read or returned.

Both exposure versions contain no earnings/session/quote fields.  The reconstructed CSV contains raw `advisers`/`is_dimensional` proxies, but no signed point-in-time economic-sponsor key.  Their holdings are PRE-effective or pre-conversion, not demonstrably pre-announcement.  All tier results are **old-clock diagnostics only**; new-clock eligibility is `UNKNOWN`, not zero.  The reconstructed inventory records 8,801 positive `primary_ready` cells out of 8,826 total cells.
