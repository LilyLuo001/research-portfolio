# Archive catalog check — 2026-09-13

The supplied data manual identifies the actual archive as
`scc1.bu.edu:/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/`.
The earlier search of `/usr3/graduate/qluo/dax-codex/p1` did not establish absence from this archive.

Read-only SSH inspection verified `_migration_meta/FINAL_SCC_MANIFEST.tsv`
SHA-256 `ce2f23683d69d89fae705363f4dadc0e551f639684c2980210c960753ff3e3bb`.
It lists `raw/ibes_actuals_eps_2019.parquet` through `2026`, `raw/ibes_idsum_us_full.parquet`,
and `raw/maximal/crsp_metaexchangecalendar_full.parquet` under `p1_refraction_wrds_shared`.
These are source locators, not inspected outcome records or measured candidate event coverage.
The migration report says PATH_SIZE_CHECK=PASS; it does not itself establish final checksum success.

`meta/schema__ibes__actu_epsus.csv` identifies `ticker,cusip,pends,pdicity,anndats,anntims,actdats,acttims`.
The archived 2025 harvest SQL corroborates them and contains an outcome column `value`, deliberately excluded by the new projection.
Harvest SQL SHA-256: `5dbdc44a2ef1771bf1786a2952c3734de1f500f60413b991ce756e51b42a288d`.
`meta/schema__crsp__metaexchangecalendar.csv` identifies trading/holiday/weekend/date-status flags and exchange group,
but supplies no market-open/close instants or early-close times. No session counts can be derived from that schema alone.
The IBES schema provides no timezone convention or unique economic-event/revision rule.

`code/custodian_projection.py` is an executable adapter to the documented annual IBES files.
It projects eight identifier/date/time/period fields only; filters a separately approved eight-character CUSIP list
and the requested date window; preserves revisions/duplicates; and reports source-record counts, not unique economic earnings events.
No raw IBES values were opened during this catalog check. The adapter has not been executed against licensed source files.

The remaining specific action is for the authorized SCC data custodian to approve and run this exact column projection
against the selected candidate CUSIP list, returning the projected CSV and receipt. This is a source-processing request,
not another request for broad PI permission. Existing Lily Luo census/SCC authorization is retained.
Exact candidate-list pathname remains pending source-version selection; no placeholder command is represented as an executed census.
