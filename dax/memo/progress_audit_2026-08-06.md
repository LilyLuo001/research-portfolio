# DAX progress audit and immediate work plan — 2026-08-06

## Executive assessment

DAX has passed its feasibility gate but remains at the end of Phase 0. The
repository contains a working pre-registration seal, lineage enforcement,
tests, and a PI-signed conditional-go note. It does not yet contain the W1
design memo, W1 power code, W2 public-data backbone, any of the three mappings,
the capability/cost panel, or the DAX index. The highest-value unblocked action
is therefore W1: turn the proposal into an auditable pre-registration draft
before data construction creates accidental specification choices.

## Evidence reviewed

- Current `main` at `caa95df`; no open remote `task/DAX-W1-memo` or
  `task/DAX-W2-data` branch existed at the start of this audit.
- DAX queue: 17 milestones from W0 through W10a.
- Implemented DAX code: the pre-registration guard and two guard tests.
- Fresh SCC clone validation: 52 DAX/runner tests passed.
- Feasibility gate: signed CONDITIONAL GO on 2026-07-10, binding the W4
  deadline, stand-in/EIV treatment, `gpt-4.5-preview` exclusion, and GDPval
  redistribution restriction.
- Remote history: DAX work after 2026-07-10 is absent; later commits concern P1.

## Progress by workstream

| Workstream | Evidence | Assessment |
|---|---|---|
| W0 infrastructure | guard, CI rules, lineage, Makefile, tests | Complete |
| W0.5 feasibility | signed note and cleared human gate | Complete in substance |
| W1 design memo | brief exists; deliverables absent | Ready; critical path |
| W1 power | no code or CPS pre-period inputs | Blocked on W1 draft/data |
| W2 data | contract and execution brief only | Ready; not started |
| W3 mappings | no mapping files/protocol | Blocked on W2 and W1 choices |
| W4 panel | no harness/registry/output | Blocked on W3; deadline-critical |
| W5–W10a | contracts/briefs only | Blocked upstream |

## Repository-state defects

1. `ops/decisions.md` records `DAX-W0.5-feasibility` complete and
   `DAX-GATE-feasibility` passed, but a later stale merge removed the feasibility
   task from `ops/runner/state.json`. The gate remains in `gates_cleared`, so W1
   and W2 are correctly unblocked, but the runner incorrectly re-advertises the
   finished feasibility task.
2. `DAX-W0.5-legwork` remains READY even though the decision log says it was
   superseded by the accepted owner-run legwork. It should be closed explicitly
   in a separate operations-state repair, not silently rerun.
3. The older SCC checkout contained a GitHub token in its remote URL. The token
   was removed during this audit. The token should still be rotated because it
   previously existed in plaintext configuration and chat history.
4. Two old SCC checkouts are dirty and divergent. A clean dedicated checkout at
   `~/dax-codex` now exists for DAX validation and scheduled compute.

## Research-design risks discovered

1. **Event registry is not yet source-complete.** Every event date and price
   change needs two locators. The current feasibility memo is sufficient for a
   go/no-go gate but not a pre-registration registry.
2. **δ calibration is under-specified.** A raw observed/predicted jump ratio does
   not identify δ because δ changes task crossing nonlinearly. The W1 draft uses
   minimum-distance calibration against predicted event jumps instead.
3. **Common-date continuous treatment needs exact clean-window rules.** A generic
   staggered-adoption recipe is insufficient because releases occur for all
   occupations on the same dates and dose is continuous.
4. **CPS hours must avoid conditioning on post-treatment employment.** The draft
   proposes zero-coded weekly hours as a primary outcome and conditional hours
   as secondary.
5. **Mapping robustness cannot become specification search.** The GDPval mapping
   remains primary; the median mapping estimate is only a descriptive
   tiebreaker and cannot rescue failure of the survive-all-three rule.

## Work plan for 2026-08-06

1. **Draft the W1 memo and PI checklist.** This has the highest option value:
   it freezes choices that W2/W3/W5 must implement and exposes decisions while
   they are still cheap to change.
2. **Build a two-source event registry.** Start with GPT-4, GPT-4o, o1, and
   GPT-4.1, then extend through the current model family. Dates lacking two
   primary locators remain visibly unresolved; no memory-filled dates.
3. **Specify the clean-window and dose rules.** These are prerequisites for
   power simulation and prevent later outcome-driven tuning.
4. **Specify validation, first-stage, EIV, and estimability thresholds as
   `[PI-DECISION]` defaults.** None becomes binding until PI signature.
5. **Prepare W2, but do not start IPUMS pulls until credentials and W1 variable
   definitions are confirmed.** O*NET/OEWS acquisition can then begin on SCC
   independently of memo review.

## Definition of today's useful finish

- A numbered `design_memo_v1.md` draft exists.
- Every proposed numeric commitment is visible in `PI_DECISIONS_OPEN.md`.
- No outcome directory is opened or modified.
- The branch remains explicitly pre-registration work; no task is marked
  complete and no `v1.0-preregistered` tag is created.
