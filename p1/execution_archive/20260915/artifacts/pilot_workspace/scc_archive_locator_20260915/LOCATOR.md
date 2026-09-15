# SCC IBES archive locator (bounded)

Canonical root: `/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/`.
The core partitions are `p1_refraction_wrds_shared/raw/ibes_detu_eps_YYYY.parquet`;
rescue alternatives are under `p1_refraction_wrds_shared/raw/rescue/`.
The core and `allcols_detu_epsus` rescue files have equal row counts in the checked
years and matching schemas; this is locator evidence only, not a deduplication claim.
Overlap is NOT_ASSESSED. `allcols_det_epsus` adds actuals fields and is an alternative,
not to be concatenated without a key/date reconciliation.

|path (relative to raw)|year|bytes|rows|columns|
|---|---:|---:|---:|---|
|ibes_detu_eps_2019.parquet|2019|17272993|1272334|21; forecast/detail fields|
|ibes_detu_eps_2020.parquet|2020|18863826|1427342|21; forecast/detail fields|
|ibes_detu_eps_2021.parquet|2021|17514976|1284222|21; forecast/detail fields|
|rescue/ibes_allcols_detu_epsus_2019.parquet|2019|16754976|1272334|21; same detail schema|
|rescue/ibes_allcols_detu_epsus_2020.parquet|2020|18268746|1427342|21; same detail schema|
|rescue/ibes_allcols_detu_epsus_2021.parquet|2021|16949287|1284222|21; same detail schema|
|rescue/ibes_allcols_det_epsus_2019.parquet|2019|18345946|1272828|27; detail plus actuals fields|
|rescue/ibes_allcols_det_epsus_2020.parquet|2020|19953777|1427941|27; detail plus actuals fields|
|rescue/ibes_allcols_det_epsus_2021.parquet|2021|18710056|1284602|27; detail plus actuals fields|

Metadata-only checks used SCC's existing databento runtime Python with PyArrow
Parquet footer access; no row values were read. Migration controls:
`_migration_meta/FINAL_SCC_MANIFEST.tsv`, `FINAL_VERIFY_REPORT.txt`, and empty
`FINAL_CHECKSUM_DIFF.txt`. No WRDS query/extraction was performed.

Relevant Git locator history: `cdaeb7d` includes `p1/wrds/SCC-MIRROR.md`,
`p1/wrds/TABLE-REQUEST.md`, `p1/t2_wrds/README.md`, and WRDS operational briefs.
