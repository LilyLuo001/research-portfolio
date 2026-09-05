# P1 repository file audit — 2026-09-03

> **HISTORICAL SNAPSHOT ONLY.** Its authority hierarchy was superseded by
> `STATUS-2026-09-05.md` and
> `strategic_pivot/POST_V3_RESEARCH_DECISION-2026-09-06.md`. Retained paths and
> provenance remain useful, but no execution authorization or pre-V3 Gate label
> in this file is current.

## Scope and conclusion

The audit began from the current remote branch after quarantining 17 stale or
duplicate untracked local files in the recoverable directory
`/private/tmp/p1-pre-sync-20260903`. The branch was then fast-forwarded to the
remote baseline before any P1 edits.

An interrupted local SCC copy (one complete stocknames file and one truncated
daily file under ignored `p1/wrds/raw/scc_mirror_extract/`) was also removed
from the working tree and placed in the same recoverable quarantine. The final
construction read the verified SCC mirror directly, never that partial copy.

The 339 pre-existing tracked files under `p1/` were inventoried by role and the
active specifications were checked against the 2026-09-03 research plan. Raw
evidence and historical artifacts were not deleted merely because they contain
old sample counts: they are required to reproduce the register and the explicit
legacy-to-current discrepancy. They are classified below and are not execution
authority.

## Authority hierarchy recorded at that checkpoint

The following list is historical. Current authority is the 2026-09-06 memo
named in the banner above.

1. `p1/strategic_pivot/strategic_recommendation.md` — then-current project
   choice, design hierarchy, kill gates, and execution authority.
2. `docs/基金转换实验_博士研究计划.md` — the boxed 2026-09-03 strategic freeze;
   lower sections are retained architecture for the superseded stock design.
3. `p1/STATUS-2026-09-03.md` and `p1/EVENT-COUNT-AUDIT.md` — measured progress
   and current counts.
4. `p1/universe_v2/output/` — current event/date master.
5. `p1/exposure/` — current Gate0 universe, strictly-PRE holdings, treatment
   matrices, audits, and lineage.
6. `p1/t3_spec/变量规格书.md` and `p1/t5_spec/估计蓝图.md` — historical
   downstream implementation for the superseded stock design; not authorized
   for execution unless a future plan explicitly reactivates it.

## File-class dispositions

| File class | Disposition | Reason |
|---|---|---|
| `p1/universe_v2/` | Active; current output copied into Git | Current 247/156/74 event and timing build |
| `p1/exposure/` | Active; added | Current strict-PRE Exposure^pre build |
| `p1/strategic_pivot/` | Active; added | Outcome-blind dose/power audit, two share-class censuses, design comparison, and current recommendation |
| `p1/tests/`, `p1/pipeline/`, compatible `p1/design/` | Retained | Tested engineering infrastructure; no headline results |
| `p1/t3_spec/`, `p1/t5_spec/` | Retained as superseded design documentation | Useful reproducibility architecture, but no longer execution authority |
| `p1/lit/`, `p1/t4_replication/` | Retained | Supports revised novelty boundary; market quality is validation only |
| `p1/edgar_filings/`, `p1/t1_channelA_wip/`, `p1/t1_arb/`, `p1/t1_normalized/` | Retained as source evidence | Raw/provenance material, not current counts |
| `p1/events_merged.csv`, `p1/t2_wrds/`, `p1/t2_free/` legacy outputs | Retained as historical baseline | Needed to reproduce 172/96 discrepancy; not current universe |
| `p1/conv_exposure_free.parquet`, `p1/output/convexp_coverage_audit/`, old scenario/power outputs | Retained as legacy baseline | Needed to reconcile old 389-stock claim; prohibited as estimation input |
| `p1/EVENT-COUNT-AUDIT.md` | Replaced | Removed obsolete instruction to quote 172/96/389 as current |
| `p1/NON_WRDS_BLOCKERS.md` | Replaced | SEC and WRDS are no longer unavailable |
| `ops/briefs/P1-T2-CONVEXP-REBUILD.md` | Replaced | Records the provisional 71-event Gate0 build and current pause |
| Older P1/WRDS execution briefs | Retained as historical run records only | Referenced by decisions/tests and useful for provenance; superseded by current authority hierarchy |

No raw SEC evidence, signed decision record, test fixture, or reproducibility
artifact was deleted. This is deliberate: deleting a stale result that is the
comparison baseline would make the required discrepancy report unauditable.

## Consistency checks recorded at that checkpoint

- The then-current headline candidate was wrapper change → fund demand/flows
  and portfolio implementation. The 2026-09-06 memo now classifies construction
  as `NOT YET`; historical/modern share-class records are candidate validation
  observations pending institutional verification.
- Exposure is predetermined, wave-specific, and based only on strictly-PRE
  exact-series N-PORT reports.
- Corporate-action factors use the report/as-of date, not filing date.
- POST holdings are Gate0 evidence only.
- No fuzzy identifier match, post-event denominator, stale 2026 carry-forward,
  outcome merge, or headline regression was introduced.
- Many-to-one event rows, long-handoff flags, Dimensional and adviser fields,
  and unresolved mappings are preserved.
- The frozen 0.5% high-dose diagnostic is recorded without threshold tuning:
  583 stock-wave cells across four waves, only 21 cells/two waves outside
  Dimensional. It cannot be promoted to headline by adding stock rows.
- The modern census separates 10 launched ETF-class activations, one
  reverse-direction event, and ten pending events; proposed dates are never
  treated as realized dates.
- No TAQ outcome file exists in the current archive. Conditional MDEs are
  explicitly non-final and no Refraction/FOMC first-stage result is claimed.

Repository tests and artifact-level validations are reported in the final Git
commit and `p1/STATUS-2026-09-03.md`.
