# P1 + Refraction WRDS Data Archive
## Data Usage, Location, Frequency, and Analysis Manual for Future AI Agents

**Archive snapshot:** 2026-09-02

**Primary SCC mirror root**

`/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/`

**Main mirrored WRDS project**

`/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/`

**Migration metadata**

`/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/_migration_meta/`

**Original WRDS source path**

`/home/tsinghua/gxyssd/p1_refraction_wrds_shared/`

---

# 1. Purpose

This archive is the WRDS-side data harvest for two finance research projects, **P1** and **Refraction**. It was created under a short WRDS-access window, so the priority was maximum preservation rather than a perfectly normalized storage layout.

The archive intentionally contains:

- broad core WRDS pulls,
- later rescue pulls,
- annual partitions,
- monthly partitions,
- portfolio-number batches,
- multi-part query outputs,
- legacy CRSP and newer CRSP/CIZ-style files,
- overlapping insurance copies,
- metadata describing query and migration status.

A future AI agent must **not blindly concatenate every Parquet file**. The correct workflow is:

1. identify the logical dataset needed;
2. inspect the final manifest;
3. locate all relevant partitions;
4. inspect schema and economic date fields;
5. determine whether files are complementary partitions or overlapping copies;
6. reconcile/deduplicate only after understanding keys and date coverage;
7. retain source provenance in every analysis-ready table.

---

# 2. Archive Integrity and Final Snapshot

At the final post-Rescue synchronization stage, the following path/size checks passed:

- WRDS source files: **12,100**
- SCC files: **12,100**
- Matched files: **12,100**
- Missing files: **0**
- Wrong-size files: **0**
- Extra SCC files: **0**
- WRDS source size: **9.913 GiB**
- Matched SCC size: **9.913 GiB**
- WRDS Parquet files: **4,482**
- SCC Parquet files: **4,482**
- Path/size verification: **PASS**
- Parquet-count verification: **PASS**

A final byte-level checksum verification was launched after these checks. Before treating the SCC mirror as the sole authoritative copy, inspect:

`_migration_meta/FINAL_VERIFY_REPORT.txt`

and:

`_migration_meta/FINAL_CHECKSUM_DIFF.txt`

The strongest acceptable final state is:

```text
PATH_SIZE_CHECK = PASS
PARQUET_COUNT_CHECK = PASS
CHECKSUM_CHECK = PASS
SAFE_TO_DELETE_WRDS = YES
```

Do not infer checksum success merely from matching file sizes.

---

# 3. Directory Structure

Expected SCC layout:

```text
/projectnb/econdept/qluo/P1_Refraction_WRDS/
└── WRDS_MIRROR_20260902/
    ├── p1_refraction_wrds_shared/
    │   ├── raw/
    │   │   ├── maximal/
    │   │   ├── rescue/
    │   │   ├── rescue_remaining/
    │   │   └── other core/raw exports
    │   ├── meta/
    │   └── .ipynb_checkpoints/
    │
    └── _migration_meta/
        ├── FINAL_SOURCE_MANIFEST.tsv
        ├── FINAL_SCC_MANIFEST.tsv
        ├── FINAL_VERIFY_REPORT.txt
        ├── FINAL_CHECKSUM_DIFF.txt
        ├── RSYNC.log
        └── other migration records
```

## 3.1 `raw/`

Contains the research data exports. A logical dataset may appear directly in `raw/`, in `raw/maximal/`, in `raw/rescue/`, or in `raw/rescue_remaining/`.

Always search all four locations before declaring a dataset absent.

## 3.2 `raw/maximal/`

Contains large early-stage or “maximal” pulls intended to harvest broad WRDS coverage.

These files may overlap with later rescue pulls.

## 3.3 `raw/rescue/`

Contains later targeted rescue downloads and extensions.

Known patterns include:

```text
raw/rescue/compna_secd_YYYY_MM.parquet
raw/rescue/newcrsp_crsp_dsf_v2_YYYY.parquet
raw/rescue/newcrsp_crsp_a_stock_dsf_v2_YYYY.parquet
raw/rescue/compna_sec_dprc_YYYY.parquet
```

The final manifest, not this manual, is authoritative for the exact set.

## 3.4 `raw/rescue_remaining/`

Contains additional rescue-stage outputs created after or outside the main rescue sequence. Treat this directory as part of the same logical archive.

If the same logical dataset appears in both `rescue/` and `rescue_remaining/`, compare schema, row coverage, dates, keys, and completion metadata before combining.

## 3.5 `meta/`

Contains audit, inventory, discovery, progress, and harvest metadata.

Known important files include:

```text
meta/GAP_AUDIT_20260902_164009.csv
meta/GAP_AUDIT_20260902_164009.json
```

There may be additional inventories and job-status files.

## 3.6 `_migration_meta/`

This is outside the mirrored WRDS project and contains migration controls.

Most useful locator files:

```text
FINAL_SOURCE_MANIFEST.tsv
FINAL_SCC_MANIFEST.tsv
```

Each manifest is intended to contain:

```text
<byte_size><TAB><relative_path>
```

Use these manifests as the fastest authoritative index of what was physically archived.

---

# 4. How to Locate Data

Never guess a path if the manifest is available.

## 4.1 Shell search

```bash
ROOT="/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902"
MANIFEST="$ROOT/_migration_meta/FINAL_SCC_MANIFEST.tsv"

grep -Ei 'crsp.*dsf|dsf.*crsp' "$MANIFEST"
grep -Ei 'holdings' "$MANIFEST"
grep -Ei 'ibes' "$MANIFEST"
grep -Ei 'secd|sec_dprc' "$MANIFEST"
grep -Ei 'fundq|funda' "$MANIFEST"
grep -Ei 'dsedist|dsedelist|dseshares' "$MANIFEST"
grep -Ei 'fama|ff_' "$MANIFEST"
```

## 4.2 Python manifest search

```python
from pathlib import Path
import pandas as pd

root = Path(
    "/projectnb/econdept/qluo/P1_Refraction_WRDS/"
    "WRDS_MIRROR_20260902"
)

manifest = root / "_migration_meta" / "FINAL_SCC_MANIFEST.tsv"

m = pd.read_csv(
    manifest,
    sep="\t",
    names=["bytes", "path"],
    dtype={"bytes": "int64", "path": "string"},
)

hits = m[m["path"].str.contains(
    "holdings|ibes|secd|dsf",
    case=False,
    regex=True,
    na=False,
)]

print(hits.to_string(index=False))
```

## 4.3 Rule before concatenation

A filename is not sufficient evidence that two files belong in one table.

Before concatenating, compare:

- column names,
- data types,
- date variables,
- source schema,
- row counts,
- min/max dates,
- security coverage,
- duplicate rates,
- proposed primary keys.

---

# 5. Frequency and Structure Summary

| Data family | Frequency / structure | Main date concept |
|---|---|---|
| CRSP `dsf` | Daily security panel | Trading date |
| New CRSP/CIZ daily | Daily security panel | Often `dlycaldt` |
| CRSP `msf` | Monthly security panel | Month/trading date |
| CRSP `dsi` | Daily market index | Trading date |
| CRSP `msi` | Monthly market index | Month |
| CRSP `dsedist` | Event-level corporate actions/distributions | `exdt` and related dates |
| CRSP `dsedelist` | Event-level delisting | Delisting date |
| CRSP `dseshares` | Share-history/event/as-of style | Table-specific date |
| CRSP holdings | Holdings-report snapshots | `report_dt` |
| CRSP fund summary/NAV/returns/flows | Mostly monthly fund observations | Calendar/report month |
| Compustat `fundq` | Quarterly accounting | Fiscal/data date |
| Compustat `funda` | Annual accounting | Fiscal/data date |
| Compustat `secd` | Daily security | Daily security date |
| Compustat `sec_dprc` | Daily security price | Daily security date |
| I/B/E/S actuals | Announcement/actual records | Announcement date/time |
| I/B/E/S summary | Estimate summary records | Summary/snapshot date |
| I/B/E/S detail | Estimate-history records | Estimate date |
| CRSP–I/B/E/S link | Effective-date intervals | `sdate`, `edate` |
| CCM link | Effective-date intervals | link start/end dates |
| Fama–French daily | Daily factor | Trading date |
| Fama–French monthly | Monthly factor | Month |

Do not infer frequency from file partition names. A yearly Parquet file can contain daily data.

---

# 6. Legacy CRSP Daily Stock File (`crsp.dsf`)

**Frequency:** daily security-level panel  
**Known core coverage:** approximately 2014-01-02 through 2024-12-31  
**Unit:** PERMNO/security × trading date

Typical fields may include:

- `permno`
- `permco`
- `date`
- `ret`
- `retx`
- `prc`
- `vol`
- `shrout`
- bid/ask variables where available
- exchange/security-code variables depending on export schema

Use for:

- daily stock returns,
- beta-estimation windows,
- daily outcomes,
- CRSP identifiers,
- price/volume controls,
- return validation.

## P1 benchmark rule

For the frozen P1 benchmark:

- stock daily **RETX** is used for beta estimation;
- SPY daily **RETX** is the market benchmark;
- beta window is `[-250, -21]` trading days relative to the event;
- no event-window alpha is estimated;
- primary event-window intraday returns are not replaced by daily CRSP returns.

## SPY warning

Known SPY identifier:

```text
PERMNO = 84398
SHRCD  = 73
```

Therefore a common-stock universe filter such as:

```python
shrcd in (10, 11)
```

will exclude SPY.

Extract SPY separately from the ordinary stock universe.

---

# 7. New CRSP / CIZ-Style Daily Files

Known rescue naming patterns include:

```text
newcrsp_crsp_dsf_v2_YYYY.parquet
newcrsp_crsp_a_stock_dsf_v2_YYYY.parquet
```

**Frequency:** daily  
**Purpose:** newer coverage and insurance beyond the legacy CRSP pull.

Known examples included 2024 and 2025.

## Schema warning

Newer CRSP/CIZ data may use date fields such as:

```text
dlycaldt
mthcaldt
```

rather than legacy CRSP date names.

Do not assume CIZ schemas are identical to legacy `crsp.dsf` or `crsp.msf`.

## Overlap warning

Similarly named rescue files may overlap or be candidate duplicates.

Before combining:

1. compare schema;
2. compare row counts;
3. compare date range;
4. compare PERMNO coverage;
5. compare key-level equality or hashes;
6. determine whether one is a view/subset/insurance copy.

Never stack them automatically.

---

# 8. CRSP Monthly Stock Data (`crsp.msf`)

**Frequency:** monthly security-level panel  
**Known traditional coverage:** through 2024-12-31

Use for:

- monthly returns,
- monthly market capitalization,
- lower-frequency robustness,
- validation of daily history.

Do not use monthly values as a substitute for daily or intraday data where higher frequency is required.

---

# 9. CRSP Market Index Data

Known harvested families include:

```text
crsp.dsi
crsp.msi
```

Frequency:

- `dsi`: daily
- `msi`: monthly

Use for diagnostics or models that explicitly call for CRSP index series.

For P1, the frozen primary market benchmark is SPY, not an arbitrary CRSP index.

---

# 10. CRSP Distribution and Corporate-Action Data

Known exported families include:

```text
crsp.dsedist
crsp.dsedelist
crsp.dseshares
```

## 10.1 `dsedist`

**Structure:** event-level distribution/corporate-action records.

A critical field is:

```text
exdt
```

Use the true ex-date for distribution screening.

For P1 OpenGap work, explicit distribution records should be used when possible. A `RET` versus `RETX` diagnostic can help identify distribution effects but should not casually replace the event records.

## 10.2 `dsedelist`

**Structure:** event-level delisting records.

Use for return-panel cleaning and securities near delisting.

## 10.3 `dseshares`

**Structure:** share-history/event/as-of style.

Do not assume it provides economically dated daily ETF SharesOut appropriate for Refraction G8.

---

# 11. CRSP Mutual Fund / ETF Metadata

Known harvested families include:

- CRSP fund header/metadata,
- `fund_summary2`,
- monthly NAV,
- monthly fund returns,
- fund flows,
- holdings.

Known `fund_summary2` availability extended through approximately 2026-06-30.

The rescue logic identified ETFs using:

```text
et_flag = 'F'
```

in the CRSP fund header.

Confirm the exact local fund-header filename via the manifest.

---

# 12. CRSP Holdings

**Source family:** `crsp.holdings`  
**Observed WRDS coverage:** approximately 2018-01-31 through 2026-06-30  
**Economic frequency:** holdings-report snapshots by `report_dt`, not a regular daily panel.

This is one of the most heavily partitioned families.

## 12.1 Portfolio-batch partitioning

Logical rescue names followed patterns similar to:

```text
crsp_holdings_etf_2019_b0001
crsp_holdings_etf_2019_b0002
...
crsp_holdings_etf_2020_b0001
...
```

Interpretation:

```text
YYYY  = holdings report year
bNNNN = CRSP portfolio-number batch
```

Initial batches were built from groups of `crsp_portno` values, often around 50 portfolios per batch.

A logical batch may contain:

- one Parquet part,
- several `part_*.parquet` files,
- completion metadata,
- zero Parquet parts if the query returned zero rows.

## 12.2 Empty-batch behavior

The initial ETF holdings rescue used a broad historical list of ETF `crsp_portno` values for every year.

Therefore many early-year batches were valid zero-row queries because some ETFs did not yet exist or had no holdings in that year.

Do not interpret:

```text
0 rows
0 parts
```

as proof of missing WRDS holdings.

## 12.3 Reading a holdings year

For a target year:

1. search the manifest for all holdings paths matching the year;
2. include all non-empty Parquet parts;
3. inspect `_DONE`, status, or metadata files if present;
4. validate schemas before concatenation;
5. deduplicate only after identifying the actual holdings key.

Likely key components include:

- `crsp_portno`
- `report_dt`
- held-security identifier
- possibly other position dimensions

Inspect the stored schema before defining uniqueness.

## 12.4 Critical research-design restriction

CRSP mutual-fund holdings are **not** the authoritative treatment dataset for either P1 or Refraction G9.

They may be used for:

- validation,
- ETF/fund characterization,
- robustness,
- auxiliary holdings analysis.

They must not substitute for the frozen SEC N-PORT pre/post construction.

---

# 13. Compustat Quarterly Fundamentals (`comp.fundq`)

**Frequency:** fiscal-quarter observations  
**Known WRDS availability at harvest:** through approximately 2026-08-31

Use for:

- accounting controls,
- firm characteristics,
- quarterly balance-sheet/income-statement variables.

An early script incorrectly requested:

```text
sich
```

from `comp.fundq`.

That invalid request was corrected. Do not recreate the old broken query.

Inspect stored columns before selecting industry variables.

---

# 14. Compustat Annual Fundamentals (`comp.funda`)

**Frequency:** fiscal-year observations  
**Known WRDS availability at harvest:** through approximately 2026-08-31

Use for annual accounting characteristics and robustness controls.

Always distinguish:

- fiscal period,
- data date,
- information availability,
- event date.

Do not create look-ahead bias by joining accounting information that was not yet available.

---

# 15. Compustat Security Daily (`compna.secd`)

A large rescue extraction was performed in monthly partitions.

Known pattern:

```text
raw/rescue/compna_secd_YYYY_MM.parquet
```

Known rescue coverage:

```text
2024-01 through 2026-09
```

The final September 2026 file, if present, is likely partial as of the archive date 2026-09-02.

**Frequency:** daily security-level  
**Storage partition:** one calendar month per Parquet file

Example:

```text
compna_secd_2025_03.parquet
```

contains March 2025 daily security records.

Do not assume equal row counts across months.

---

# 16. Compustat Daily Price / `sec_dprc`

Known pattern:

```text
raw/rescue/compna_sec_dprc_YYYY.parquet
```

Known examples included 2024 and 2025.

**Frequency:** daily security price records  
**Storage partition:** annual

This family may overlap conceptually with `compna_secd`.

Before using both:

- compare table provenance,
- compare schema,
- compare identifiers,
- compare dates,
- determine whether one is a subset/view or a distinct source.

Do not double-count.

---

# 17. CRSP/Compustat Merged Linking

A CCM-related pull was included.

Use it to map CRSP securities/firms to Compustat entities.

Expected linking concepts include:

- `permno`
- `permco`
- `gvkey`
- link start/end dates
- link type
- link primary indicators

Always enforce link-date validity.

Never apply a historical link to all dates without respecting its effective interval.

---

# 18. I/B/E/S Families

Known harvested families include:

```text
ibes.actu_epsus
ibes.statsumu
ibes.statsum
ibes.detu
ibes.idsum
```

or equivalent WRDS exports.

Exact local filenames must be located in the final manifest.

---

# 19. I/B/E/S Actuals / Earnings Announcements

Known source:

```text
ibes.actu_epsus
```

Known WRDS availability at harvest extended through approximately:

```text
2026-05-14
```

A key announcement-time field:

```text
anntims
```

had essentially full observed coverage in discovery.

## Critical timezone warning

The timezone interpretation of `anntims` was **not verified** during the harvest.

Do not convert `anntims` into an intraday event timestamp until official I/B/E/S/WRDS documentation or external validation confirms its timezone semantics.

This is critical for event-time alignment.

---

# 20. I/B/E/S Summary Estimates

Known families:

```text
statsumu
statsum
```

These are estimate-summary records, not ordinary stock-day observations.

A future AI must distinguish:

- fiscal period,
- measure,
- statistic,
- summary/snapshot date,
- announcement date.

Do not merge summary estimates to events by ticker alone.

---

# 21. I/B/E/S Detail Estimates

Known family:

```text
detu
```

**Structure:** analyst-level/detail estimate-history records.

Potential uses:

- consensus construction,
- analyst dispersion,
- revisions,
- pre-announcement expectations.

Inspect fields for:

- analyst/estimator,
- estimate date,
- fiscal period,
- measure,
- estimate value,
- announcement relation.

Do not treat each row as an independent firm-day observation.

---

# 22. I/B/E/S Identifier Summary

Known family:

```text
idsum
```

Use as an identifier aid.

Do not rely on ticker alone across long samples because tickers can change or be reused.

---

# 23. CRSP–I/B/E/S Link

A full link table was recovered from:

```text
wrdsapps_link_crsp_ibes.ibcrsphist
```

Known columns:

```text
ticker
permno
ncusip
sdate
edate
score
```

Known row count:

```text
37,662
```

Known local file:

```text
raw/crsp_ibes_link_full.parquet
```

If the file was later moved, confirm via the final manifest.

## Link usage

When linking CRSP and I/B/E/S:

1. enforce the effective interval (`sdate`/`edate`);
2. inspect `score`;
3. do not silently retain multiple matches;
4. log ambiguous links;
5. prefer this recovered link to improvised ticker matching.

---

# 24. Fama–French Data

Known harvested families include daily and monthly Fama–French files.

Frequency:

- daily factor file: daily
- monthly factor file: monthly

Use for analyses explicitly calling for factor models.

Do not substitute Fama–French factors for P1's frozen SPY beta-adjusted-market benchmark except as a separately labeled robustness analysis.

---

# 25. Index Data

CRSP index-related tables were harvested where SELECT permission existed.

A separate index-description object was visible during discovery but did not permit SELECT in the relevant stage.

Therefore index return/history data may be present while some descriptive metadata are incomplete.

Do not identify an index solely from an internal code without checking available descriptions.

---

# 26. Stock Industry Membership

A family similar to:

```text
stkindmembership_ind
```

was included.

Use for historical membership/industry work only after checking effective dates and membership intervals.

---

# 27. Known Coverage Summary

The following values are orientation. Always compute actual local min/max dates before analysis.

| Dataset family | Approximate known coverage | Frequency / structure |
|---|---:|---|
| Legacy CRSP `dsf` | 2014-01-02 to 2024-12-31 | Daily security |
| Legacy CRSP `msf` | through 2024-12-31 | Monthly security |
| CRSP holdings | 2018-01-31 to 2026-06-30 | Holdings-report snapshots |
| CRSP `fund_summary2` | through 2026-06-30 | Fund summary, typically monthly |
| Fama–French | through about 2026-06-30 in discovery | Daily and monthly |
| Compustat `fundq` | through about 2026-08-31 availability | Quarterly |
| Compustat `funda` | through about 2026-08-31 availability | Annual |
| Compustat `secd` rescue | 2024-01 to 2026-09 | Daily, monthly file partitions |
| I/B/E/S actual EPS US | through about 2026-05-14 | Announcement/actual record |
| I/B/E/S estimate histories | broad 2012-2026 harvest window | Estimate records |
| CRSP–I/B/E/S link | full recovered table | Effective-date link history |

---

# 28. Partition Conventions

## 28.1 Annual partitions

Pattern:

```text
..._YYYY.parquet
```

Examples:

```text
newcrsp_crsp_dsf_v2_2025.parquet
compna_sec_dprc_2025.parquet
```

## 28.2 Monthly partitions

Pattern:

```text
..._YYYY_MM.parquet
```

Example:

```text
compna_secd_2025_03.parquet
```

## 28.3 Portfolio batches

Logical pattern:

```text
..._YYYY_bNNNN
```

Example:

```text
crsp_holdings_etf_2019_b0135
```

## 28.4 Multi-part exports

A logical query may contain:

```text
part_00001.parquet
part_00002.parquet
...
```

These parts usually belong to one logical export and may be concatenated vertically after schema validation.

Do not concatenate JSON/status metadata as data.

---

# 29. Safe Parquet Reading

Inspect schema and metadata before loading large files.

```python
from pathlib import Path
import pyarrow.parquet as pq

root = Path(
    "/projectnb/econdept/qluo/P1_Refraction_WRDS/"
    "WRDS_MIRROR_20260902/p1_refraction_wrds_shared"
)

files = sorted(root.glob(
    "raw/rescue/compna_secd_2025_*.parquet"
))

for f in files:
    pf = pq.ParquetFile(f)
    print(f.name, pf.metadata.num_rows, pf.schema.names)
```

Only after validating compatible schemas should files be concatenated.

For very large collections, prefer:

- PyArrow Dataset,
- DuckDB,
- Polars lazy scan,
- column projection,
- predicate pushdown,
- date-selective reads.

Avoid loading the full 9.9 GiB archive into pandas.

---

# 30. Candidate Duplicate / Overlap Policy

Overlap is expected because the archive was built for maximum preservation under time pressure.

Possible overlap classes:

1. legacy CRSP versus newer CRSP/CIZ;
2. initial maximal pull versus rescue pull;
3. rescue versus rescue_remaining;
4. related WRDS views with similar content;
5. annual and monthly partitions covering the same period;
6. reruns of interrupted extraction jobs.

Before combining sources, build a reconciliation table with:

```text
source_file
source_family
schema_signature
row_count
min_date
max_date
unique_key_count
duplicate_key_count
checksum_or_row_hash
```

Never delete a source merely because filenames look similar.

Never stack overlapping sources without a source/provenance flag.

---

# 31. Recommended Provenance Columns

When constructing analysis-ready tables, add provenance fields before concatenation:

```text
_source_file
_source_family
_source_schema
_source_partition
_source_download_stage
```

Example:

```python
df["_source_file"] = str(path)
df["_source_family"] = "compna_secd"
df["_source_partition"] = "2025_03"
df["_source_download_stage"] = "rescue"
```

---

# 32. Date Handling Rules

Future AI agents must distinguish:

- trading date,
- fiscal period end,
- accounting data date,
- holdings report/as-of date,
- SEC filing date,
- earnings announcement date,
- earnings announcement time,
- ex-distribution date,
- identifier-link effective date,
- conversion effective date,
- intraday event timestamp.

Do not substitute one date concept for another.

This is especially important for SEC N-PORT and corporate-action alignment.

---

# 33. P1 Research-Design Data Rules

These are frozen data-use constraints.

## 33.1 Exposure

Primary treatment:

```text
Exposure^pre_{i,w}
```

must be time-invariant and predetermined using strictly **pre-conversion SEC N-PORT holdings/shares**.

CRSP mutual-fund holdings are not a substitute.

## 33.2 Event outcome

Primary CAR horizons include:

```text
5m
15m
30m
60m
close
+1d
```

The WRDS archive does not contain the full required intraday stock + SPY midquote series.

Therefore the WRDS archive alone cannot generate the frozen primary intraday CAR outcomes.

## 33.3 Frozen beta benchmark

Benchmark:

```text
beta_adjusted_market
```

Beta estimation:

- stock daily CRSP RETX;
- SPY daily CRSP RETX;
- window `[-250, -21]`;
- no event-window alpha.

Intraday event-window abnormal return:

- stock midquote return;
- SPY midquote return;
- beta estimated from the daily window.

## 33.4 Non-RTH events

For announcements outside regular trading hours:

```text
t0 = next regular-market open
```

OpenGap is a separate outcome.

## 33.5 Corporate actions

For N-PORT share-factor alignment, use CRSP share factors aligned to the N-PORT report/as-of date, **not the SEC filing date**.

For OpenGap distribution screening, use true ex-date information where possible.

---

# 34. Refraction Research-Design Data Rules

## 34.1 G9 / N-PORT

G9 requires real SEC N-PORT pre/post holdings.

Do not substitute:

- CRSP mutual-fund holdings;
- inferred holdings;
- unrelated contemporaneous ETF holdings.

## 34.2 G7

G7 requires FOMC statement/press-conference intraday ETF and synthetic-basket data.

Full required intraday data were not available in the harvested WRDS environment.

This remains an external-data requirement.

## 34.3 G8

G8 requires:

- economically dated ETF SharesOut / creation-redemption proxy;
- aligned intraday dollar order imbalance.

CRSP SPY `shrout` was observed to behave like a lower-frequency/monthly-style field and is **not valid as the required daily G8 SharesOut series**.

## 34.4 Macro expectations

CPI/NFP consensus is external.

FOMC surprise inputs can come from public/external sources.

---

# 35. SEC N-PORT: Foundational External Data

SEC N-PORT is foundational to both projects.

Required logic includes:

- strictly PRE N-PORT;
- first eligible POST N-PORT;
- report/as-of date alignment;
- preservation of many-to-one sponsor/member relationships;
- no use of filing date as the economic holdings date.

For P1 Gate 0, a member needs true PRE plus FIRST ELIGIBLE POST evidence.

Do not fake or interpolate a post filing when none exists.

---

# 36. P1 Event-Master Context

The event-master recovery work produced a latest known state of approximately:

```text
156 total structural/event members
74 verified exact-day
14 proposed
57 month-only
9 bounded-window
2 year-only
```

Timing-primary eligibility was approximately:

```text
74 eligible
82 ineligible
49 waves
```

A future AI should locate the latest event-master files rather than recreate these counts from this manual.

Search for terms such as:

```text
event_master
verified_exact_day
timing_primary
wave
effective_date
```

Do not use month-only approximate dates in exact-day primary timing regressions.

---

# 37. Sponsor / Adviser Structure

P1 uses an **economic sponsor** crosswalk, not a raw textual adviser-name match.

Known project state included approximately:

```text
34 advisers
HHI ≈ 0.069
largest adviser/sponsor share ≈ 16%
```

Sponsor crosswalks require evidence/manual signoff.

Do not silently convert fuzzy string matches into verified sponsor identity.

Where specified, inference should support sponsor × stock clustering.

---

# 38. External-Required Data From the Gap Audit

The last major gap audit found no critical/high WRDS-side foundational gaps, but several important inputs remained external.

Known external-required categories included:

1. CPI/NFP consensus;
2. daily ETF SharesOut suitable for G8;
3. FOMC ETF + synthetic-basket intraday data;
4. full intraday stock + SPY data;
5. intraday order imbalance;
6. SEC N-PORT pre/post holdings.

These are not failed WRDS downloads. They are external-data requirements.

---

# 39. Optional / Lower-Priority Gaps

The audit also noted optional or lower-priority missing items such as:

- TFN s34/s12 insurance;
- alternative CRSP 2026 insurance;
- WRDS holdings insurance;
- CRSP–TAQ link.

Do not confuse these with the foundational external inputs above.

---

# 40. TAQ Availability Warning

The WRDS environment exposed only sample TAQ-style libraries rather than full TAQ coverage.

Therefore:

- do not assume full intraday trades/quotes are in this archive;
- do not construct primary intraday outcomes from sample TAQ;
- use the designated external intraday source.

---

# 41. DGTW Restriction

Do not construct an intraday or daily DGTW benchmark unless a genuine same-frequency DGTW series exists.

Do not relabel a lower-frequency characteristic benchmark as same-frequency event-window DGTW.

---

# 42. SPY Handling Summary

Known:

```text
SPY PERMNO = 84398
SPY SHRCD  = 73
```

Consequences:

- `(SHRCD in 10,11)` excludes SPY;
- benchmark extraction must be separate;
- CRSP SPY `shrout` is not a validated daily G8 SharesOut series.

---

# 43. Coverage Audit Before Any Merge

For every candidate logical dataset, compute:

```text
number of files
number of rows
min date
max date
number of unique securities
number of unique dates
duplicate rate on proposed key
missingness of identifiers
missingness of critical variables
```

Example:

```python
def basic_panel_audit(df, date_col, id_col):
    print("rows:", len(df))
    print("date min:", df[date_col].min())
    print("date max:", df[date_col].max())
    print("unique IDs:", df[id_col].nunique())
    print("unique dates:", df[date_col].nunique())
    print(
        "duplicate id-date rows:",
        df.duplicated([id_col, date_col]).sum()
    )
```

---

# 44. Never Use Filename Dates as Economic Dates

A filename such as:

```text
compna_secd_2025_03.parquet
```

is a storage partition, not the authoritative economic date.

Use the date column inside each record.

Similarly, a holdings batch labeled `2019` only identifies a report-year partition. Use the actual `report_dt`.

---

# 45. Current-Year Files May Be Partial

Archive date:

```text
2026-09-02
```

Any 2026 annual file or September 2026 monthly file may be partial.

For current-year analysis, inspect:

- max observation date,
- row counts by month,
- latest report date,
- whether the final period is truncated.

Do not interpret a partial year as a full year.

---

# 46. Memory and File-Size Guidance

Some rescue files are individually large, including files around 160–175 MB.

A compressed Parquet file can expand substantially in pandas memory.

Avoid:

```python
pd.concat([pd.read_parquet(f) for f in thousands_of_files])
```

unless necessary.

Prefer DuckDB, PyArrow Dataset, Polars lazy scan, selective columns, and selective dates.

---

# 47. DuckDB Example

```python
import duckdb

root = (
    "/projectnb/econdept/qluo/P1_Refraction_WRDS/"
    "WRDS_MIRROR_20260902/p1_refraction_wrds_shared"
)

con = duckdb.connect()

q = f'''
select *
from read_parquet(
    '{root}/raw/rescue/compna_secd_2025_*.parquet'
)
limit 100
'''

df = con.execute(q).df()
```

Before using a wildcard across many files, verify schema compatibility.

---

# 48. Recommended Source Reconciliation

When legacy and rescue/new data overlap:

1. define the analysis-required fields;
2. select a primary source family;
3. use the alternate source for extension or validation;
4. compare overlapping periods;
5. document discrepancies;
6. retain a source flag.

A sensible default orientation is:

```text
Legacy CRSP DSF:
    preferred for frozen historical P1 daily RET/RETX construction

New CRSP/CIZ:
    useful for newer coverage and insurance
    requires explicit schema harmonization
```

---

# 49. Suggested Logical Data Catalog

Create a machine-readable catalog with one row per logical dataset.

Suggested columns:

```text
logical_name
source_wrds_table
local_path_pattern
partition_type
frequency
primary_date_column
entity_key
min_date
max_date
n_rows
n_files
schema_hash
research_role
overlap_notes
quality_status
```

This catalog should be generated from the archive, not reconstructed from memory.

---

# 50. Core Dataset Roles by Project

## P1

Likely WRDS roles:

- CRSP daily stock:
  - beta estimation,
  - daily outcomes,
  - RET versus RETX checks,
  - identifiers.
- SPY CRSP series:
  - beta-adjusted-market benchmark estimation.
- I/B/E/S:
  - earnings actuals,
  - announcement information,
  - expectation/SUE inputs,
  - analyst estimates.
- CRSP–I/B/E/S link:
  - firm/security linking.
- Compustat:
  - accounting controls.
- CRSP corporate actions:
  - ex-distribution and share-factor screens.
- CRSP fund/holdings:
  - auxiliary/validation only for exposure unless explicitly authorized.
- SEC N-PORT:
  - external foundational treatment data.

## Refraction

Likely WRDS roles:

- CRSP:
  - security history,
  - returns,
  - identifiers,
  - corporate actions.
- Compustat:
  - controls where required.
- CRSP fund/ETF metadata:
  - ETF characterization.
- CRSP holdings:
  - auxiliary/validation, not G9 replacement.
- SEC N-PORT:
  - external G9 foundation.
- external intraday data:
  - G7/G8.
- external economically dated ETF SharesOut:
  - G8.
- external macro consensus:
  - CPI/NFP.

---

# 51. Known Harvest Problems That Were Fixed

Old logs may contain failed queries. These do not necessarily imply missing archived data.

## 51.1 Visible objects without SELECT permission

Some WRDS objects were visible in metadata but could not be selected.

## 51.2 New CRSP date-field mismatch

Old scripts expected legacy fields and did not recognize newer fields such as:

```text
dlycaldt
mthcaldt
```

## 51.3 Invalid `sich` in `comp.fundq`

The query was corrected by removing the invalid field.

## 51.4 Index descriptions

Some index-description metadata lacked SELECT permission.

## 51.5 Very large in-memory queries

Some large queries killed the WRDS session. Rescue logic therefore used smaller partitions, which is why the archive contains many files.

---

# 52. Empty Files and Completion Metadata

The rescue framework may leave completion/status metadata for queries returning zero rows.

Therefore:

- an empty logical batch is not automatically a failure;
- a completion marker may represent a valid zero-row query;
- `0 parts` can be valid.

Use actual Parquet parts plus batch metadata to reconstruct logical data.

---

# 53. Determining Whether a Batch Is Complete

For a logical rescue batch:

1. locate its status metadata;
2. locate all associated `part` files;
3. read Parquet row counts from metadata;
4. check for a completion marker;
5. compare with progress/audit logs.

Do not infer completeness from the presence of only `part_00001.parquet`.

---

# 54. Candidate Keys and Duplicate Checks

These are starting points only. Confirm actual schemas.

## CRSP daily

Candidate key:

```text
PERMNO × trading date
```

## CRSP monthly

Candidate key:

```text
PERMNO × month/date
```

## Compustat quarterly

Potential key requires more than naïve `GVKEY × DATADATE` in some cases because reporting format/consolidation/version dimensions may matter.

## Holdings

Likely key components:

```text
crsp_portno × report_dt × held-security identifier
```

Possibly additional dimensions.

## CRSP–I/B/E/S link

This is interval-based and must not be reduced to a static one-row-per-PERMNO mapping without justification.

---

# 55. Identifier Hierarchy

Prefer stable/effective-date identifiers over names.

Common identifiers include:

```text
PERMNO
PERMCO
GVKEY
CRSP_PORTNO
I/B/E/S ticker
CUSIP / NCUSIP
```

Rules:

- CRSP security analysis: prefer PERMNO.
- Compustat firm analysis: prefer GVKEY.
- CRSP–Compustat: use CCM effective-date links.
- CRSP–I/B/E/S: use recovered `ibcrsphist`.
- Fund/ETF portfolios: use `crsp_portno`.
- Do not use company/fund names as primary keys.

---

# 56. Event-Time Alignment

For event studies distinguish:

```text
calendar date
trading date
announcement timestamp
regular trading hours
next regular open
```

For P1:

- non-RTH event `t0` is the next regular open;
- OpenGap is a separate outcome;
- primary event-window midquote data are external.

Do not approximate 5-minute or 15-minute outcomes with daily CRSP returns.

---

# 57. Audit First, Estimate Second

Do not launch main regressions simply because some data are present.

In particular:

- P1 needs true PRE + first eligible POST N-PORT foundation;
- Refraction G9 needs real pre/post SEC N-PORT;
- G7/G8 need required external intraday inputs.

No headline estimation should be considered final before these foundations are satisfied.

---

# 58. Gap-Audit Orientation

A prior unified audit reported approximately:

```text
PASS                 41
EXTERNAL_REQUIRED     6
MISSING               4
```

with no critical/high WRDS-side gaps at that stage.

The audit files are authoritative:

```text
meta/GAP_AUDIT_20260902_164009.csv
meta/GAP_AUDIT_20260902_164009.json
```

If the files disagree with this manual, use the files.

---

# 59. Minimal AI Checklist Before Using Any Dataset

Before analysis, answer all of the following:

```text
[ ] What is the logical WRDS source table?
[ ] Which local files contain it?
[ ] Is the data annual, monthly, daily, event-level, or report-snapshot?
[ ] What is the true economic date column?
[ ] What is the security/fund identifier?
[ ] Are the files partitions or overlapping copies?
[ ] Are there newer rescue versions?
[ ] Is the current year partial?
[ ] Are there duplicate keys?
[ ] Is an effective-date link table required?
[ ] Is timezone interpretation verified?
[ ] Does the paper design permit this source for the intended variable?
[ ] Is this WRDS data or an external-required input?
[ ] Has source provenance been retained?
```

If any answer is unknown, do not proceed to final estimation.

---

# 60. Quick Discovery Script for a Future AI

```python
from pathlib import Path
import pandas as pd

BASE = Path(
    "/projectnb/econdept/qluo/P1_Refraction_WRDS/"
    "WRDS_MIRROR_20260902"
)

PROJECT = BASE / "p1_refraction_wrds_shared"
META = BASE / "_migration_meta"

manifest_path = META / "FINAL_SCC_MANIFEST.tsv"

m = pd.read_csv(
    manifest_path,
    sep="\t",
    names=["bytes", "path"],
)

m["mib"] = m["bytes"] / 1024**2

print("Files:", len(m))
print("GiB:", m["bytes"].sum() / 1024**3)

keywords = [
    "dsf",
    "msf",
    "holdings",
    "fundq",
    "funda",
    "secd",
    "dprc",
    "ibes",
    "ibcrsp",
    "dsedist",
    "dsedelist",
    "dseshares",
    "fama",
    "ff",
]

for k in keywords:
    x = m[
        m["path"].str.contains(
            k,
            case=False,
            na=False
        )
    ]

    print("\n" + "=" * 70)
    print(k, len(x))
    print("=" * 70)

    if len(x):
        print(
            x[["mib", "path"]]
            .sort_values("path")
            .to_string(index=False)
        )
```

This should normally be one of the first programs run by a future AI agent.

---

# 61. Canonical Paths for New Analysis Code

Do not hard-code individual rescue filenames throughout notebooks.

Define:

```python
from pathlib import Path

ARCHIVE = Path(
    "/projectnb/econdept/qluo/P1_Refraction_WRDS/"
    "WRDS_MIRROR_20260902"
)

WRDS = ARCHIVE / "p1_refraction_wrds_shared"
RAW = WRDS / "raw"
META = WRDS / "meta"
MIGRATION_META = ARCHIVE / "_migration_meta"
```

Then resolve actual files through the manifest.

If the archive is moved elsewhere, change only `ARCHIVE`.

---

# 62. If the Archive Is Moved

Preserve internal relative paths.

Example:

```python
ARCHIVE = Path("/new/location/WRDS_MIRROR_20260902")
```

Everything beneath:

```text
p1_refraction_wrds_shared/
_migration_meta/
```

should remain intact.

Do not flatten the archive into one folder.

---

# 63. Long-Term Backup Rules

When copying the SCC mirror to Google Drive, TeraBox, local storage, or another server:

- preserve `WRDS_MIRROR_20260902/` as one top-level folder;
- preserve all relative directories;
- preserve `_migration_meta/`;
- preserve manifests and verification reports;
- do not place all Parquet files in a single flat directory.

The manifest is essential for future recovery.

---

# 64. Authority Order

When sources disagree, use this priority.

## Physical file existence

1. `FINAL_SCC_MANIFEST.tsv`
2. actual SCC filesystem
3. earlier inventories/audits
4. remembered filenames in this manual

## Migration integrity

1. `FINAL_VERIFY_REPORT.txt`
2. `FINAL_CHECKSUM_DIFF.txt`
3. source/SCC manifests
4. `RSYNC.log`

## Research design

Use the project's frozen research specifications and signed-off event/crosswalk files.

Do not allow a convenient WRDS variable to override the frozen design.

---

# 65. Critical Cautions

1. **Do not concatenate every Parquet file in the archive.**
2. **Do not interpret storage partitions as independent economic samples.**
3. **Do not treat zero-row holdings batches as database failure.**
4. **Do not use CRSP holdings as SEC N-PORT treatment data.**
5. **Do not use CRSP SPY `shrout` as validated daily G8 SharesOut.**
6. **Do not use sample TAQ as full intraday data.**
7. **Do not merge I/B/E/S and CRSP by ticker alone when the recovered link is available.**
8. **Do not apply a common-stock filter to SPY.**
9. **Do not use SEC filing date in place of N-PORT report/as-of date.**
10. **Do not assume current-year files are complete.**
11. **Do not ignore effective dates in CCM or CRSP–I/B/E/S links.**
12. **Do not assume legacy and new CRSP schemas are identical.**
13. **Do not run headline regressions before required treatment/event foundations are complete.**
14. **Always retain provenance when harmonizing overlapping exports.**
15. **Always inspect the final manifest before declaring a dataset missing.**

---

# 66. One-Sentence Summary for Future AI

**This archive is a high-coverage, heavily partitioned WRDS research mirror for P1 and Refraction; use the final manifest to locate data, reconstruct logical tables by source-aware partitions rather than filenames alone, respect economic dates and effective-date links, and never substitute CRSP mutual-fund holdings or low-frequency WRDS fields for the projects' required SEC N-PORT or external intraday inputs.**
