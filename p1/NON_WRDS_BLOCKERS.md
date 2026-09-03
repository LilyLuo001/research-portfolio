# P1 remaining gates and blockers — current

**Status date:** 2026-09-03

The prior version of this file described SEC egress and WRDS access as active
blockers. That is no longer true. SEC/N-PORT Gate0 has run, and the BU SCC WRDS
mirror is available at the location documented in the owner's
`P1_Refraction_WRDS_Data_Usage_Manual.md`.

## Completed

- Event recovery and reconciliation: 247 structural members, 156 completed,
  74 verified exact-day events.
- N-PORT Gate0: 74 tested, 71 PASS, 3 pending first-POST filings.
- Strictly-PRE holdings extraction and date-aware CRSP identifier mapping.
- Corporate-action-aligned Exposure^pre construction on SCC using CRSP through
  2025.
- All/Dimensional-only/ex-Dimensional matrices, LOSO position inputs, leakage
  audit, coverage lists, census, discrepancy report, and lineage.
- No earnings outcome or headline coefficient has been inspected.

## Active gates

1. **Fed/source universe reconciliation — open.** The note's empirical sample
   is four Dimensional conversions and all four match P1, but its separate
   end-2024 aggregate of 125 funds has no published row list. P1 currently has
   95 dated-through-2024 completions. See
   `p1/universe_v2/output/event_universe_reconciliation_report.md`. The 71-event
   set remains a valid verified subset but is not the final global universe.
2. **K2 exit decision — suspended.** Excluding Dimensional currently leaves 21
   unique PERMNOs at ExposureOwnership ≥0.5%, below the frozen floor of 33.
   Preserve that conditional diagnostic and its threshold, but do not apply K2
   until the universe gate is resolved.
3. **Economic-sponsor signoff.** Adviser strings are preserved as a proxy, but
   the economic-sponsor crosswalk still requires evidence and owner signoff.
   This blocks final LOSO matrices and the headline bootstrap-cluster decision.
4. **Three recent first-POST filings.** `P1E000004419`, `P1E000004424`, and
   `P1E000002790` remain pending; they are excluded from the 71-event build.
5. **2026 CRSP daily coverage.** The mirror's CRSP daily security files end in
   2025. Missing 2026 factor/denominator observations are retained as missing;
   no stale carry-forward or Compustat substitute is allowed.
6. **Final outcome inputs.** IBES announcement-time coverage/timezone and the
   genuine intraday quote/trade source remain load-bearing for the earnings
   response path. They have not been merged or estimated.
7. **OpenGap ex-date and DGTW verdict.** These WRDS questions remain downstream
   checks under `ops/briefs/P1-WRDS-SPRINT.md`; neither should be improvised.

## Current authority

- Research design: `docs/基金转换实验_博士研究计划.md`
- Detailed progress: `p1/STATUS-2026-09-03.md`
- Universe: `p1/universe_v2/output/`
- Exposure build and diagnostics: `p1/exposure/`
- WRDS execution manual: owner's
  `P1_Refraction_WRDS_Data_Usage_Manual.md` (external to the repo)
