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
