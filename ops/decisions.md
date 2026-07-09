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
#    E2-T1-facts escalates to a seat-D Claude Code block per the two-strike
#    ladder — brief at ops/briefs/E2-T1-facts-escalation.md. Task stays
#    manual:true for the L1 driver (seat D produces the output instead).
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
