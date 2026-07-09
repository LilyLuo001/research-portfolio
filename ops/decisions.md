# decisions.md — the L3 reply channel (arch §2)
#
# Reply to digest items here, one decision per line (no leading '#'). The box
# applies them on its next cycle (`runner.py --apply-decisions`) and prefixes
# applied lines with '# applied:' so nothing runs twice. Recognized forms:
#
#     gate <TASK-ID> pass
#     gate <TASK-ID> fail
#     complete <TASK-ID>
#
# Unknown task ids are ignored (and logged). Anything else is commentary.

# RESOLVED 2026-07-09 by owner: FalconX Credit Vault launch = 2025-08
# (personally confirmed). Plan §10 stands; Gemini channel B's 2025-06 was
# WRONG despite 34 grounded searches — treat channel B's AA_FalconXUSDC rows
# in ops/l1/out/E2-T1-facts-B.json with extra suspicion during the A/B union
# check, and count this as a live example of why the union check exists.
# Original conflict note kept below for the record:
# NEED_HUMAN (2026-07-09, E2 dual-channel conflict): FalconX Credit Vault
# (AA_FalconXUSDC collateral) launch date — research plan §10 says 2025-08
# (marked 已核实), but Gemini channel B answered 2025-06 backed by grounded
# searches (raw reply: ops/l1/out/E2-T1-facts-B.void.json).
# NEED_HUMAN (2026-07-09, E2-T1-facts): 4 kimi failure modes exhausted (kimi-latest 404, prose-drift, plan-then-stop/truncation, UNKNOWN on armed sentinels even chunked 1-item). Re-parked with strike standing. Needs seat-D re-assignment or vendor change; channel B output (E2-T1-facts-B.json) exists for the union check.

# WAVE 0 EXECUTED 2026-07-09 (owner-approved via L2-PIPELINE.md; details there):
# 1. VENDOR DECISION — kimi $web_search is BENCHED for retrieval batches.
#    Evidence: three distinct failure families on three tasks, incl. last
#    night's chunked k2.6 legwork run replying only an <antThinking> plan
#    (out/DAX-W0.5-legwork.void.json). Resolves the NEED_HUMAN above:
#    E2-T1-facts re-assigned off kimi per the two-strike ladder. Task stays
#    manual:true for the L1 driver.
# 2. E2-T1-facts-B validated + completed (raw channel-B input for the union):
#    all 4 item keys, 6/6 assets in oracles+redemption, every row URL-or-
#    UNKNOWN, sentinels S1/S2 correct. Union-block flags: t1a-navlink is one
#    aggregate row (not per-reserve); t1a-coinbase-vault is a dict, not rows;
#    FalconX oracle row self-declares "inferred"/Medium — on top of the
#    standing 2025-06 launch-date suspicion.
# 3. DAX-W0.5-legwork PARKED at attempt 1 (kimi bench) — seat E does the
#    legwork inline in the DAX-W0.5-feasibility session (Wave 1); the spec's
#    three item prompts are that session's checklist.
# 4. E2-T9b-scenarios un-parked, re-routed kimi→gemini_free (no channel pair,
#    so no cross-vendor issue; ¥0). S2 fence risk documented in the spec.
# 5. E2-T6b-nav stays manual by design (upload-and-read via gemini_helper.py,
#    grounded one-shot already failed) — it is an owner 30-min item, schedule
#    alongside a Wave-1 block; output needs sign-off before T6a consumes it.

# RESOLVED 2026-07-09 (owner-delegated "go ahead"): the E2-T1-facts vendor
# question — channel A re-assigned from kimi to an Anthropic L2 session
# (cross-vendor independence vs Gemini channel B preserved). Executed same
# day: ops/l1/out/E2-T1-facts.json, sentinels 3/3 PASS. Union check with
# three arbitration items: e2/t1_union_check.md. E2-T9b-scenarios follows
# the same path on its next block. `complete E2-T1-facts` awaits owner
# review of the union-check conflicts.
# P1-T0-crash channel A executed the same way: p1/t0_collision_sweep_channelA.md.
# Verdict: no collision on P1's outcome variable (their line = volatility/
# liquidity; one medium-adjacent flag on adverse-selection costs in SSRN
# 3142081). Recommendation CONTINUE — kill/pivot signature stays with owner.

# RECONCILED 2026-07-09 (merge of the two notes above, owner-approved items
# 1–4 in-session): Wave-0 item 1's seat-D block for E2-T1-facts is SUPERSEDED
# — the delegated Anthropic L2 session already produced channel A + the union
# check (ops/briefs/E2-T1-facts-escalation.md now historical; only the owner
# arbitration of e2/t1_union_check.md's 3 conflicts remains, then
# `complete E2-T1-facts`). On E2-T9b-scenarios the two notes disagreed
# (gemini_free vs Anthropic session): per rule 5 (cheap runs, expensive
# gates) the ¥0 gemini_free arming stands for tonight's driver; if its fence
# trips, the Anthropic-session path is the escalation — no strike ambiguity,
# the two paths are ordered, not parallel.
# NEED_HUMAN (2026-07-09 ~16:00 UTC, infra): SSH publickey auth to SCC denied account-wide (scc1/2/3 all reject key SHA256:tKu/vjdm...) — broke between 15:27-16:20 UTC, previously masked by a persistent ControlMaster socket. Server-side cause (authorized_keys / home-dir perms / account state); needs owner interactive login (password+Duo) to inspect ~/.ssh/authorized_keys and home perms. Box cron + its PAT pushes are UNAFFECTED (02:00 T9b-gemini run + scanner will proceed); monitoring agent has failed over to GitHub-side watch from the Mac clone. Note: 02:00 L1 outputs only reach GitHub at the NEXT 21:00 EDT digest, so red-path response is delayed until access is restored.
