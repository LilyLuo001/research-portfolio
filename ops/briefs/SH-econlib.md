# PRIME-BLOCK BRIEF — SH-econlib
_generated 2026-07-07T09:08:17.942770Z — a fresh session needs zero
conversational memory; the repo state IS the state._

- **project**: shared
- **owner seat**: D
- **worker**: code_pro
- **depends_on (all must be green)**: ['SH-runner']
- **output contract**: econlib_smoke  (task is DONE only when this passes `contracts.py`)
- **human gate**: False

## before you start
1. `git pull` on this seat's worktree.
2. claim the task:  `python ops/runner/lease.py claim SH-econlib --account D`
   (if this errors non-fast-forward, another seat beat you — pick the next brief)
3. `git switch -c task/SH-econlib`  (or reuse the worktree for this task)

## the task
stacked DiD, Callaway–Sant'Anna, wild bootstrap, randomization inference, event-study plots + toy-data tests. Serves P1-T5, E2-T8, DAX-W8 alike.

Paste the corresponding verbatim prompt from the manual/amendment for SH-econlib here,
then work. Plan → execute → **commit early and often** (if the 5h window or weekly
cap cuts the session, the next one resumes from the last commit, losing minutes).

## definition of done
- output written to its contracted path; `python ops/runner/contracts.py econlib_smoke <path>` returns PASS
- lineage JSON emitted (inputs, hashes, code version, timestamp)
- merge task/SH-econlib → main; `python ops/runner/runner.py --complete SH-econlib`
- `/clear` before the next task; one task per session.
