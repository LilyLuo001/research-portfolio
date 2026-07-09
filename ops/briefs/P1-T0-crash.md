# PRIME-BLOCK BRIEF — P1-T0-crash
_generated 2026-07-09T14:43:18.103704Z — a fresh session needs zero
conversational memory; the repo state IS the state._

- **project**: p1
- **owner seat**: C
- **worker**: project_pro
- **depends_on (all must be green)**: —
- **output contract**: —  (task is DONE only when this passes `contracts.py`)
- **human gate**: False

## before you start
1. `git pull` on this seat's worktree.
2. claim the task:  `python ops/runner/lease.py claim P1-T0-crash --account C`
   (if this errors non-fast-forward, another seat beat you — pick the next brief)
3. `git switch -c task/P1-T0-crash`  (or reuse the worktree for this task)

## the task
AMEND P1-1: Saglam–Tuzun collision check moved to week 0. Pro Research (channel A) ∪ Kimi $web_search (channel B).

Paste the corresponding verbatim prompt from the manual/amendment for P1-T0-crash here,
then work. Plan → execute → **commit early and often** (if the 5h window or weekly
cap cuts the session, the next one resumes from the last commit, losing minutes).

## definition of done
- output written to its contracted path; `python ops/runner/contracts.py <none> <path>` returns PASS
- lineage JSON emitted: `python ops/runner/lineage.py <output> <inputs...>` (inputs, hashes, code version, timestamp)
- merge task/P1-T0-crash → main; `python ops/runner/runner.py --complete P1-T0-crash`
- `/clear` before the next task; one task per session.
