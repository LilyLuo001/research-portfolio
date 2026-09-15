# P1 execution ledger — 2026-09-15

Research: **HOLD_DESIGN + HOLD_DATA**. Safe artifact commit `e2256c4c54d51b5053da60973b0cb8e9bda43b94` was pushed and independently matched with `git ls-remote` on `task/p1-feasibility-adjudication-20260913`. See `GIT_DELIVERY.json`; its bookkeeping commit may advance the branch tip. No merge into main occurred.

| Stage | Actual state | Evidence location under `artifacts/` |
|---|---|---|
| 20260913 feasibility/reconciliation/closure/roster history | Historical documents preserved; do not rerun accepted reviews | `feasibility_20260913/` |
| 20260914 data order, acquisition and checklist | Code/reports/receipts archived; licensed files not uploaded | `pilot_workspace/delivery/`, `missing_data_round_20260914/`, `evaluation_20260914/` |
| 20260915 Gate 1 checks | Historical limited findings, not research GO | `pilot_workspace/gate1_20260915/` |
| Full pilot plan | Written/reviewed; user authorized finite execution | `pilot_workspace/pilot_research_plan_20260915/` |
| Outcome-blind design build | Structural diagnostics complete; synthetic fixtures passed, real calibration/power not run | `pilot_workspace/pilot_design_build_20260915/` |
| First uncapped implementation | INVALID_REQUIRED_SEMANTICS; preserve history, do not use findings | `pilot_workspace/pilot_uncapped_metadata_20260915/README.md` |
| Corrected uncapped full run | Complete: 2,794 candidates, 2,592 mapped, 202 unknown; PRE/POST keys 29,729→61,486 | `pilot_workspace/pilot_uncapped_metadata_20260915/corrected_v2/` |
| Targeted analyst metadata | Complete: 108 keys, 28 observed ≥2 IDs, 80 unknown; W002 high PRE0/1/1 and POST1 observed IDs | `pilot_workspace/targeted_analyst_coverage_20260915/` |
| Direct-source connectivity attempt | Historical direction superseded by user's SCC-only correction; NOT a required research dependency | `pilot_workspace/source_reconciliation_20260915/` |
| SCC-only archive locator | Complete bounded locator: core and overlooked rescue IBES detail 2019–2021 found; footer counts measured; row-level overlap not assessed | `pilot_workspace/scc_archive_locator_20260915/` |
| Real session, final population, measurement, PRE calibration, power | Not completed; proceed through finite roadmap/early stops | `EXECUTION_ROADMAP.md` |

The 20260903 manual reports a baseline 12,100 files / 4,482 Parquets / 9.913 GiB matched on SCC plus later rescue additions. These are historical archive facts, not newly measured current totals or proof of statistical suitability. Its explicit harvest-complete statement and user instruction mean no renewed WRDS access is needed. Use actual SCC and final/rescue manifests to locate any overlooked inputs.

The low-cost locator found both `raw/ibes_detu_eps_YYYY.parquet` and `raw/rescue/ibes_allcols_detu_epsus_YYYY.parquet` for 2012–2026. For checked 2019/2020/2021, both series have 1,272,334 / 1,427,342 / 1,284,222 rows respectively, although compressed sizes differ. `ibes_allcols_det_epsus_YYYY` also exists with additional columns and different row counts. Equal row counts do not prove equivalent values or identical keys. The next bounded data operation is metadata-only comparison of these existing alternatives for the frozen target keys, with source labels preserved; not renewed WRDS access or unconditional concatenation.

## Current dispatch record

- Existing `pilot_design_build`: requested Sol/medium; source-clock documentation work only after correction, no further WRDS access.
- Existing `p1_git_inventory`: dispatched Luna/low; safe artifact inventory completed, now SCC archive locator.
- Attempt to resume the old Terra measurement agent was rejected by client capacity; it was NOT launched.
- Backend model/effort telemetry: NOT_OBSERVED. No new high-model reviewer or nested delegation.

## Preservation and exclusions

`ARTIFACT_INDEX.json` records published files with hashes and excluded files with paths/sizes/reasons. Excluded raw/unreviewed data are not opened or hashed for publication. Original files are preserved. No `.DS_Store`, keys, DBN/parquet, unrestricted event-level CSVs or sealed response outputs are staged. Some historical value-bearing reports are indexed only. This snapshot covers two identified workspace roots, not every message or attachment in the chat.

No effect estimation, empirical power, market-data purchase or authentication change occurred in this publication/locator turn.
