# PRIME-BLOCK BRIEF — DAX-W5-index
_generated 2026-07-06T14:48:27.354378Z — a fresh session needs zero
conversational memory; the repo state IS the state._

- **project**: dax
- **owner seat**: A
- **worker**: code_pro
- **depends_on (all must be green)**: ['DAX-GATE1-memo', 'DAX-W4-panel', 'DAX-W3-audit']
- **output contract**: dax_panel  (task is DONE only when this passes `contracts.py`)
- **human gate**: False

## before you start
1. `git pull` on this seat's worktree.
2. claim the task:  `python ops/runner/lease.py claim DAX-W5-index --account A`
   (if this errors non-fast-forward, another seat beat you — pick the next brief)
3. `git switch -c task/DAX-W5-index`  (or reuse the worktree for this task)

## the task
AMEND DAX-1: EIV sensitivity module appended (item 9).

Paste the corresponding verbatim prompt from the manual/amendment for DAX-W5-index here,
then work. Plan → execute → **commit early and often** (if the 5h window or weekly
cap cuts the session, the next one resumes from the last commit, losing minutes).

## definition of done
- output written to its contracted path; `python ops/runner/contracts.py dax_panel <path>` returns PASS
- lineage JSON emitted (inputs, hashes, code version, timestamp)
- merge task/DAX-W5-index → main; `python ops/runner/runner.py --complete DAX-W5-index`
- `/clear` before the next task; one task per session.
