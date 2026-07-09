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

## definition of done
- output written to its contracted path; `python ops/runner/contracts.py power_memo <path>` returns PASS
- lineage JSON emitted: `python ops/runner/lineage.py <output> <inputs...>` (inputs, hashes, code version, timestamp)
- merge task/P1-T2a-power → main; `python ops/runner/runner.py --complete P1-T2a-power`
- `/clear` before the next task; one task per session.
