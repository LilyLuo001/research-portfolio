# PRIME-BLOCK BRIEF — DAX-W0.5-feasibility
_generated 2026-07-09T14:43:18.021020Z — a fresh session needs zero
conversational memory; the repo state IS the state._

- **project**: dax
- **owner seat**: A
- **worker**: project_pro
- **depends_on (all must be green)**: —
- **output contract**: —  (task is DONE only when this passes `contracts.py`)
- **human gate**: False

## before you start
1. `git pull` on this seat's worktree.
2. claim the task:  `python ops/runner/lease.py claim DAX-W0.5-feasibility --account A`
   (if this errors non-fast-forward, another seat beat you — pick the next brief)
3. `git switch -c task/DAX-W0.5-feasibility`  (or reuse the worktree for this task)

## the task
AMEND DAX-4: vintage + GDPval-license feasibility note. Kimi legwork feeds it (DAX-W0.5-legwork).

Paste the corresponding verbatim prompt from the manual/amendment for DAX-W0.5-feasibility here,
then work. Plan → execute → **commit early and often** (if the 5h window or weekly
cap cuts the session, the next one resumes from the last commit, losing minutes).

## definition of done
- output written to its contracted path; `python ops/runner/contracts.py <none> <path>` returns PASS
- lineage JSON emitted: `python ops/runner/lineage.py <output> <inputs...>` (inputs, hashes, code version, timestamp)
- merge task/DAX-W0.5-feasibility → main; `python ops/runner/runner.py --complete DAX-W0.5-feasibility`
- `/clear` before the next task; one task per session.
