# Specific custodian handoff

Lily Luo's census-only and SCC permission is already recorded. The remaining source-side step is approval/execution by the SCC WRDS archive custodian of `code/custodian_projection.py`, whose input columns were verified in archived schema and harvest SQL (see `ARCHIVE_CATALOG_CHECK.md`). No new broad permission or whole-contract signature is requested here.

Host: `scc1.bu.edu`. Source root:
`/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw/`.
Exact partitions: `ibes_actuals_eps_2019.parquet` through `ibes_actuals_eps_2026.parquet`.
The source-side executor is the authorized BU SCC/WRDS archive custodian for qluo; the prompt does not identify a separate named institutional representative, and this handoff does not invent one.

Approve/run this one projection with a source-version-specific eight-character CUSIP allowlist, and return its metadata CSV and receipt. The source-list choice/point-in-time CUSIP–PERMNO link remains unresolved: the free and reconstructed inventories are separate, so no combined candidate list has been generated. The supplied `--candidate-cusips` must identify its source version. The verified available SCC runtime is `/share/pkg.8/python3/3.12.4/install/bin/python3`.

The adapter's `--help` describes its three required arguments. A complete execution command is intentionally not supplied until the custodian supplies the actual candidate-list path, new output directory, and process approval reference. No invented table name or dummy input path is presented as runnable work.

Exact returned source fields: `ticker,cusip,pends,pdicity,anndats,anntims,actdats,acttims`, plus `source_partition`. Filter: approved candidate CUSIPs and 2019-01-01 <= announcement date < 2026-09-01. Revisions and source duplicates are retained; count units are records. No EPS values, forecast values, SUE, price, return, quote-price/size, CAR, model coefficient or p-value is projected. The adapter neither computes eligibility from those excluded values nor grants permission through a string argument.

The metadata can establish candidate record presence and reported clocks. Unique economic events require a separately documented revision/key rule; timezone and actual exchange open/close/half-day times remain unverified. This projection does not manufacture session, stock/SPY quote masks, clean controls, sponsor identity, or response-leg dates. Those adapters remain UNIMPLEMENTED because their exact sources/semantics have not been verified. Stages with these inputs missing remain unavailable while the completed source inventories are retained.

Validation so far is schema/SQL inspection and code review only. This review has not executed the adapter on raw IBES. It can be reviewed now without opening any source values. An executed protected projection must carry its real source/query/output hashes and handling authorization in `ibes_projection_receipt.json`.
