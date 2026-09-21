# Source and extraction provenance

This is a bounded provenance hunt, not an inference from filename or data values.

| Frozen file | Intended family label | Original extraction source table | Original year predicate | Evidence/status |
| --- | --- | --- | --- | --- |
| `raw/ibes_detu_eps_2023.parquet` | direct unadjusted I/B/E/S Detail EPS | `ibes.detu_epsus` | `anndats >= '2023-01-01' AND anndats < '2024-01-01' AND usfirm = 1 AND upper(measure) = 'EPS'` | Exact canonical SCC query: `.../p1_refraction_wrds_shared/meta/ibes_detu_eps_2023.sql.txt`. It is an announcement-date partition, not an `fpedats` partition. |
| `raw/ibes_actuals_eps_2023.parquet` | direct unadjusted I/B/E/S Actuals EPS | `ibes.actu_epsus` | `anndats >= '2023-01-01' AND anndats < '2024-01-01' AND usfirm = 1 AND upper(measure) = 'EPS'` | Exact canonical SCC query: `.../p1_refraction_wrds_shared/meta/ibes_actuals_eps_2023.sql.txt`. It is an announcement-date partition, not a fiscal-period partition. |

The audit's new filters are separate and never substituted for these original predicates: Detail uses EPS plus the documented quarterly FPI strata because its observed direct schema lacks `pdicity`; Actuals uses EPS plus `pdicity=QTR`. Same-year matching is a metadata diagnostic only, not proof of full candidate-to-actual coverage.

The Detail extraction query selected `curr` but its projected values are all missing. The Actual extraction query selected `curr_act`, not a field named `curr`; this authorized audit did not read `curr_act`, and the resulting parquet lacks `curr`. Thus the actual-side reporting-currency question remains a source-schema/projection gap, not a conclusion about currency values.

## Safe original SELECT-field provenance (field names only)

- `ibes.detu_epsus` selected: `ticker, cusip, oftic, cname, actdats, estimator, analys, currfl, pdf, fpi, measure, value, curr, usfirm, fpedats, acttims, revdats, revtims, anndats, anntims, report_curr`.
- `ibes.actu_epsus` selected: `ticker, cusip, oftic, cname, pends, measure, pdicity, anndats, anntims, actdats, acttims, value, curr_act, usfirm`.

Both original lists include `value`, which this stage never read. SCC schema inspection confirmed `curr_act` in Actuals, so one actual-only supplement then projected exactly `curr_act, measure, pdicity`; its protected projection and aggregate are recorded in `ENGINEERING_RECEIPT.json`. The earlier `curr` conclusion is therefore superseded: actual currency *metadata is observed under `curr_act`*, but Detail `curr` is all missing, so pairwise currency compatibility remains unresolved.

The SCC audit projected only whitelist metadata fields. It saved the protected row-level projection solely at `/projectnb/econdept/qluo/P1_Refraction_WRDS/ibes_pit_metadata_audit_20260921/private/whitelist_projection.parquet`; no such rows were copied locally. Its aggregate result was independently transcribed into `METADATA_RESULTS.json`.

The direct Detail candidate key is `ticker, estimator, analys, fpedats, fpi, measure, anndats, anntims, actdats, acttims`; Actual key is `ticker, pends, measure, pdicity, anndats, anntims, actdats, acttims`. These are source metadata keys, **not economic-event definitions**. The cross-source diagnostic only normalizes ticker, measure, and parsed `fpedats/pends`; it has no CUSIP cross-check and cannot resolve share-basis or vendor-version ambiguity.
