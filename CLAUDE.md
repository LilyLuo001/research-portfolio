# CLAUDE.md — portfolio conventions (keep < 200 lines)

You are one execution unit in a multi-seat pipeline for three research papers
(P1 fund conversions, E2 RWA looping, DAX AI exposure). The repo state is the
only shared state. You never message another agent.

## the five meta-rules (from P1 §1, apply everywhere)
1. **LLM is not a source of facts.** Dates/AUM/holdings/coefficients come only
   from (a) code you wrote executed on real data, or (b) extractions carrying a
   raw-source locator (EDGAR accession+URL / WRDS table+query / doc page). Any
   number "from memory" is a hallucination — discard it.
2. **Dual-channel** on high-hallucination tasks (event lists, citations, spec):
   two *different vendor families*, machine-diff, third model + human on splits.
3. **Schema contracts.** Tasks hand off through files, never conversation.
   Column names are frozen in ops/contracts/; never rename a column.
4. **Don't know → stop.** Emit `NEED_HUMAN: <reason>`; never guess-fill.
5. **Expensive gates, cheap runs.** Spec/audit/red-team use the frontier;
   templated bulk uses cheap tiers. Two consecutive failures → auto-escalate.

## working protocol (every prime block)
- Start from `ops/briefs/<task>.md`. Fresh session, zero conversational memory.
- Claim first: `python ops/runner/lease.py claim <task> --account <SEAT>`.
- Work on branch `task/<task>` in THIS seat's worktree. Only touch your project's
  directory (see ops/accounts.yaml owned_paths). `shared/` is read-only unless
  you are seat D.
- Plan → execute → **commit early and often**. Long runs are scripts handed to
  the scheduler (Rule Zero), never babysat in-session.
- Done = output passes `python ops/runner/contracts.py <contract> <path>` +
  lineage JSON emitted. Then merge to main and `runner.py --complete <task>`.
- `/clear` between tasks. One task per session.

## never
- Never open DAX `analysis/outcomes/` before the `v1.0-preregistered` tag.
- Never put OpenAI NDA usage aggregates in the repo (CI greps for them).
- Never specification-search ("if significant then…"). Report the first run.
