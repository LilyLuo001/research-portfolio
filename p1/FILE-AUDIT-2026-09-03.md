# P1 repository file audit — 2026-09-03

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

## Authority hierarchy

1. `docs/基金转换实验_博士研究计划.md` — research question, hypotheses,
   identification, outcomes, inference, and stopping rules.
2. `p1/STATUS-2026-09-03.md` and `p1/EVENT-COUNT-AUDIT.md` — measured progress
   and current counts.
3. `p1/universe_v2/output/` — current event/date master.
4. `p1/exposure/` — current Gate0 universe, strictly-PRE holdings, treatment
   matrices, audits, and lineage.
5. `p1/t3_spec/变量规格书.md` and `p1/t5_spec/估计蓝图.md` — downstream
   variable/inference implementation, only where consistent with item 1.

## File-class dispositions

| File class | Disposition | Reason |
|---|---|---|
| `p1/universe_v2/` | Active; current output copied into Git | Current 247/156/74 event and timing build |
| `p1/exposure/` | Active; added | Current strict-PRE Exposure^pre build |
| `p1/tests/`, `p1/pipeline/`, compatible `p1/design/` | Retained | Tested engineering infrastructure; no headline results |
| `p1/t3_spec/`, `p1/t5_spec/` | Retained; stale measured counts corrected | Frozen downstream architecture remains compatible |
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

## Consistency checks

- The headline question remains wrapper change → dynamic incorporation of
  firm-specific earnings information; liquidity/volatility remain validation.
- Exposure is predetermined, wave-specific, and based only on strictly-PRE
  exact-series N-PORT reports.
- Corporate-action factors use the report/as-of date, not filing date.
- POST holdings are Gate0 evidence only.
- No fuzzy identifier match, post-event denominator, stale 2026 carry-forward,
  outcome merge, or headline regression was introduced.
- Many-to-one event rows, long-handoff flags, Dimensional and adviser fields,
  and unresolved mappings are preserved.
- The conditional 21-stock K2 diagnostic is recorded without threshold tuning;
  K2 is suspended pending the Fed/source universe gate.

Repository tests and artifact-level validations are reported in the final Git
commit and `p1/STATUS-2026-09-03.md`.
