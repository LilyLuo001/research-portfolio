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

## Wave-1 specifics (L2-PIPELINE.md, added 2026-07-09)
- the kimi legwork batch is PARKED (kimi $web_search benched, Wave-0
  decision) — do the legwork INLINE in this Project session (Pro Research).
  The checklist is the three item prompts in `ops/l1/DAX-W0.5-legwork.yaml`:
  (1) vintage API accessibility + current prices from OpenAI's own
  pricing/deprecation pages, (2) open-weight stand-ins for retired vintages
  with benchmark-parity URLs, (3) GDPval license terms quoted verbatim.
  Same discipline as the batch spec: primary sources only, per-row URL +
  retrieval date, UNKNOWN with the search path if a page can't be found.
- the prior kimi output was QUARANTINED for fabrications (invented
  gdpval.mit.edu URL, fabricated retrieval date) — do not reuse anything
  from ops/l1/out/ for this task; there is no valid prior output.
- output path the gate reads: `dax/memo/feasibility_note.md`
  (DAX-GATE-feasibility's declared input). PI signs it at the gate → that
  unlocks DAX-W1-memo, W2-data, W3-mapA, W4-panel.
- seat note: queue owner is A, but if seat A is on DAX-W0-infra this block
  goes to floater seat E (runner assignment rule 2) — either way it lands
  on branch task/DAX-W0.5-feasibility, merged after review.

## definition of done
- output written to its contracted path; `python ops/runner/contracts.py <none> <path>` returns PASS
- lineage JSON emitted: `python ops/runner/lineage.py <output> <inputs...>` (inputs, hashes, code version, timestamp)
- merge task/DAX-W0.5-feasibility → main; `python ops/runner/runner.py --complete DAX-W0.5-feasibility`
- `/clear` before the next task; one task per session.
