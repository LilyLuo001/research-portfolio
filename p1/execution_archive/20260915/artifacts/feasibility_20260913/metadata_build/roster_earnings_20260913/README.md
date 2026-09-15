# Outcome-blind roster seeds

`out/seed_stock_wave.csv` is a seed roster, not an earnings-event sample. It
contains the 8,801 `primary_ready=True` rows from evidence `E007`, keyed by
`permno,wave_id`, with report-date metadata and deterministic source line
locators. `out/seed_security.csv` aggregates those rows to 3,440 unique
PERMNOs. The 25 remaining E007 rows are preserved as explicit `NOT_PRIMARY_READY`
gaps, not silently dropped.

Inputs were verified before generation: E007
`exposure_stock_wave_all.csv` SHA-256
`905b7faa844a3a415f5b6c42d0e8de4c1fa28060efe16370182ef86df20b7320`; E011
lineage SHA-256 `c0c0f817068609ff4c20ef4eb21958932d35a785390733d9b5c7993475aaff4a`.

The permitted point-in-time bridge is catalogued, not executed: archive
`raw/crsp_ibes_link_full.parquet`, schema
`meta/schema__wrdsapps_link_crsp_ibes__ibcrsphist.csv`, with fields
`ticker,permno,ncusip,sdate,edate,score`. A custodian must apply point-in-time
validity and a documented score rule. No static ticker/CUSIP mapping was used.
No IBES raw records or outcome-bearing fields were read.
