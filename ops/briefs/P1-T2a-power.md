# PRIME-BLOCK BRIEF — P1-T2a-power
_generated 2026-07-09T14:43:18.188905Z — a fresh session needs zero
conversational memory; the repo state IS the state._

- **project**: p1
- **owner seat**: C
- **worker**: code_pro
- **depends_on (all must be green)**: ['SH-econlib']
- **output contract**: power_memo  (task is DONE only when this passes `contracts.py`)
- **human gate**: False

## before you start
1. `git pull` on this seat's worktree.
2. claim the task:  `python ops/runner/lease.py claim P1-T2a-power --account C`
   (if this errors non-fast-forward, another seat beat you — pick the next brief)
3. `git switch -c task/P1-T2a-power`  (or reuse the worktree for this task)

## the task
AMEND P1-2: simulated power analysis / kill-switch pre-flight BEFORE any WRDS spend. Public FEDS-Note numbers + priors.

Paste the corresponding verbatim prompt from the manual/amendment for P1-T2a-power here,
then work. Plan → execute → **commit early and often** (if the 5h window or weekly
cap cuts the session, the next one resumes from the last commit, losing minutes).

## Wave-1 specifics (L2-PIPELINE.md, added 2026-07-09)
- ⚠ the queued input `p1/events_from_note.csv` DOES NOT EXIST yet — building
  it is step 1 of this block. Every row comes from the public FEDS Note
  itself (meta-rule 1: each number carries its source locator — FEDS Note
  URL + table/figure — no numbers from memory). Commit the CSV before the
  simulation code so the lineage chain starts clean.
- output path the gate reads: `p1/power_memo.md` (P1-GATE-t2a's declared
  input). Contract `power_memo` requires the sections 「三档结论」 and
  「kill-switch 判定线」 verbatim.
- this block feeds the single biggest L1 unlock in the portfolio: pass →
  P1-GATE-t2a → four overnight batches (P1-T1-events A/B, P1-T13-ant A/B).
  End the block with `make plan` and check whether those four need
  `ops/l1/<id>.yaml` specs written so the next night isn't wasted
  (P1-T1-events/T13-ant specs do not exist yet).
- kimi note: P1-T1-events / P1-T13-ant are queued on kimi, which is BENCHED
  (Wave-0 decision). If the bench still stands when the gate passes, write
  their specs with `worker: gemini_free` overrides (their B-channels are
  already gemini — same-family A/B breaks dual-channel independence, so
  flag it in the spec header as NEED_HUMAN before arming, or re-route the
  B-channels instead).

## definition of done
- output written to its contracted path; `python ops/runner/contracts.py power_memo <path>` returns PASS
- lineage JSON emitted: `python ops/runner/lineage.py <output> <inputs...>` (inputs, hashes, code version, timestamp)
- merge task/P1-T2a-power → main; `python ops/runner/runner.py --complete P1-T2a-power`
- `/clear` before the next task; one task per session.
