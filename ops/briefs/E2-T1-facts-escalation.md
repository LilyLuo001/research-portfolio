# PRIME-BLOCK BRIEF — E2-T1-facts (ESCALATED to seat D)

> **⛔ SUPERSEDED 2026-07-09 (same day) — do NOT lease this task.**
> A delegated Anthropic L2 session already executed the block: channel A at
> `ops/l1/out/E2-T1-facts.json` (sentinels 3/3 PASS), union check at
> `e2/t1_union_check.md` incl. on-chain explorer verification. What remains
> is OWNER work only: arbitrate the union check's 3 conflicts, then write
> `complete E2-T1-facts` in ops/decisions.md. Kept for the record of the
> escalation design; see L2-PIPELINE.md §3 for live status.

_hand-written 2026-07-09 per the two-strike ladder (arch §3 rule 4): 4 kimi
strikes recorded, task parked NEED_HUMAN in ops/decisions.md. A failed L1
worker escalates to a Claude Code block on seat D so it never steals a
project seat's block. Fresh session, zero conversational memory._

- **project**: e2 (but leased by seat **D** — escalation float; e2/ writes are
  limited to the contracted output file, nothing else in seat B's tree)
- **worker**: code_pro (was: kimi ×4)
- **depends_on**: none
- **channel B**: `ops/l1/out/E2-T1-facts-B.json` (gemini_free, HAS-OUTPUT) —
  already exists, so this block is **arbitration + gap-fill**, not a redo
- **human gate**: false, but the A/B union output goes to the owner for the
  usual spot-check before anything flows to E2-T2-dune

## before you start
1. `git pull` on seat D's worktree.
2. claim: `python ops/runner/lease.py claim E2-T1-facts --account D`
3. `git switch -c task/E2-T1-facts`
4. Read the strike post-mortems at the top of `ops/l1/E2-T1-facts.yaml` —
   the four kimi failure modes are documented there so you don't re-derive them.

## the task
制度事实核验, channel A. Source prompt: docs/E2_执行手册_Prompt与Agent指派.md
T1a (verbatim questions), C0 discipline core per manual §0.3.

1. Answer the T1a question set with sources — every answer carries a
   first-hand URL / doc locator (meta-rule 1). No locator → `UNKNOWN`.
2. **Union check vs channel B** (v1.1 appendix A, id-by-id) against
   `ops/l1/out/E2-T1-facts-B.json`. Known landmine: the FalconX Credit Vault
   (AA_FalconXUSDC) launch date — owner personally confirmed **2025-08**;
   channel B answered 2025-06 despite grounded searches (see decisions.md).
   Treat channel B's other rows with the same suspicion this example earned.
3. Divergences you cannot resolve from first-hand sources: list them as
   `NEED_HUMAN` rows in the output — do not guess-fill (meta-rule 4).
4. Write the merged answer map to `ops/l1/out/E2-T1-facts.json` in the same
   shape as the channel-B file, plus lineage JSON.

## definition of done
- merged output at `ops/l1/out/E2-T1-facts.json`, every row sourced or UNKNOWN/NEED_HUMAN
- lineage JSON emitted
- merge task/E2-T1-facts → main; `python ops/runner/runner.py --complete E2-T1-facts`
- run `make plan` — this should flip **E2-T2-dune** (deepseek, L1) to READY;
  confirm its spec `ops/l1/E2-T2-dune.yaml` exists / write it so tonight's
  driver picks it up (L2-PIPELINE.md cadence rule 2)
- also decide/record in decisions.md whether E2-T9b-scenarios and E2-T6b-nav
  re-arm tonight (they were parked on the same vendor question)
- `/clear` before the next task; one task per session.
