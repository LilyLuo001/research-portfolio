# P0/P1 roster execution record

Run date: 2026-09-20.  This record contains no licensed row-level data,
identifiers, issuer names, prices, shares, returns, EPS values, forecasts, or
quote observations.

## Actual outputs

The SCC-only output root is:

```text
/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/derived/p1_concentration_information/20260920/roster/
```

`private_top500_permco_marketcap.parquet` is the receiver issuer pool, and
`private_top500_common_shareclasses.parquet` is its security-level expansion.
The latter has `permno`, `permco`, `date`, `prc`, `shrout`, `shrcd`,
`market_cap_usd`, and `issuer_rank`, exclusively on SCC.  The opaque top-eight
issuer and security identifiers are in `private_top8_permco_marketcap.parquet`
and `private_top8_permno_permco.parquet`, respectively.  The release-group
candidate calendar is
`private_2023_top8_earnings_release_group_candidates.parquet`; its source-row
and fiscal-period-metadata audit companions remain in the same SCC directory.

The run actually ranked 4,253 qualified PERMCO issuers from 4,295 active common
share-class rows.  It produced the requested 500-PERMCO receiver pool (519
security rows) and eight source issuers (10 security rows).  Two joined
common-stock rows had invalid/non-positive market-cap inputs and were excluded;
there were no duplicate CRSP security/date keys, duplicate active names, or
conflicting active-name intervals.

The 2023 I/B/E/S EPS source partition had 28,468 rows with a valid `anndats`;
24,105 source rows had exactly one non-null effective historical CRSP-I/B/E/S
PERMNO link and non-null historical PERMCO name interval, 4,363 had zero valid
historical mappings, and none had multiple valid PERMNO mappings. The eight
sources account for 50 mapped source
rows, 40 distinct source metadata tuples (32 quarterly and 8 annual), and 32
issuer/date/time release-group candidates.  Annual and quarterly records are
not claimed to be separate public releases merely because they are separate
I/B/E/S rows.  Neither the top-eight subset nor the full linked 2023 source
set had a source row with multiple valid PERMNO or PERMCO alternatives.  No
release-group candidate lacked `anntims`.

## Definitions and provenance

The rank date is 2022-12-30, the last observed CRSP trading date in the 2022
daily input.  The security-level market-cap ingredient is
`abs(prc) * shrout * 1000` (CRSP `shrout` is in thousands); qualified
common-stock securities have an active `crsp_dsenames_full` interval with
`SHRCD` 10 or 11.  Security market caps are then summed to PERMCO before
ranking, so multiple share classes do not become multiple issuers.

Sources read were:

- `raw/crsp_dsf_2022.parquet` and `raw/crsp_dsenames_full.parquet` for the
  ranking;
- `raw/ibes_actuals_eps_2023.parquet`, `raw/crsp_ibes_link_full.parquet`, and
  `raw/crsp_dsenames_full.parquet` for the calendar.

Calendar mapping first applies the full CRSP–I/B/E/S historical link at
`anndats`, then applies the historical CRSP name interval at that same date to
obtain PERMCO.  It never uses a current ticker to map an event.  The physical
partition query in `meta/ibes_actuals_eps_2023.sql.txt` filters `anndats >=
2023-01-01` and `< 2024-01-01`, `usfirm=1`, and EPS; it is an announcement-date
partition, not a fiscal-period (`pends`) partition.

`anndats` is the source economic announcement date.  `anntims` follows the
archived W021 nominal Eastern/DST convention.  A separately observed
availability date, exact public-release precision, and proof that this is the
earliest public dissemination remain UNKNOWN; they must be independently
validated before intraday use.

## Runtime and reproducibility

The executable source is [build_roster.py](build_roster.py).  It was copied to
the SCC output directory above and executed there with `module load
python3/3.12.4`.  It performs only targeted reads of the listed CRSP, name,
link, and 2023 I/B/E/S files; no archive-wide scan, WRDS connection, download,
price/return outcome read, forecast read, or EPS-value read occurred.  No job
scheduler telemetry was observed, so no unobserved scheduler status is
reported as actual telemetry.

The portable aggregate-safe machine-readable counterpart is
[safe_summary.json](safe_summary.json).
