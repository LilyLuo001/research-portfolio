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

# ARBITRATED 2026-07-10 (owner-delegated in-session; record in
# e2/t1_union_check.md §仲裁): conflict 1 (syrupUSDC oracle) = per-chain
# on-chain ruling (ETH vault exchange-rate wrapper / Base Chainlink-pattern;
# API3 rejected); conflict 3 (coinbase-vault) = both addresses adopted,
# Base-only + V1/V2 qualifiers; conflict 2 (FalconX redemption) = UNKNOWN-
# pending, all sources 403'd from the session proxy — owner browser path in
# the memo (docs.pareto.credit or Etherscan 0x433d5b17…be4d Read Contract).
# applied: complete E2-T1-facts

# Owner confirmed in-session 2026-07-10 ("yes i confirm, please proceed"):
# applied: gate P1-GATE-t2a pass
# applied: complete P1-T0-crash

# SIGNED 2026-07-10 (owner, verbatim in seat-C session — expands the two
# bare "# applied:" lines above with the owner's recorded justification):
# 1. P1-T0-crash CONTINUE verdict signed. No collision on P1's outcome
#    variable (Saglam–Tuzun line = volatility/liquidity; P1 = earnings-
#    information incorporation). SSRN 3142081 adverse-selection-cost result
#    to be explicitly differentiated at paper stage.
# 2. P1-GATE-t2a PASS — "0.1σ MDE is entirely reasonable and economically
#    significant in our literature context":
#    a. Cohen's d baseline & ambition: 0.2σ is the standard "small"-effect
#       benchmark; designing to a 0.1σ MDE is intentionally ambitious, to
#       capture very faint but critical signals.
#    b. Economic significance: across empirical economics (micro-
#       interventions, macro shocks, informational-efficiency metrics such
#       as PEAD/ERC), a 0.1σ improvement is often highly relevant for policy
#       and market design — a "small but meaningful" shift in earnings-
#       information incorporation.
#    c. Cost/feasibility vs rigor: shrinking the MDE from 0.2σ to 0.1σ
#       roughly quadruples the required sample size; setting it this tight
#       proves the design's statistical rigor — sufficiently powered so that
#       even a true effect somewhat below the MDE (e.g. ~70% of it) remains
#       statistically detectable.
# 3. NEED_HUMAN infra item (SCC SSH publickey auth): acknowledged by owner —
#    will log in manually (password+Duo) to fix on the server side.

# RESOLVED 2026-07-10 (owner-relayed answer pack; conflict 2 of
# e2/t1_union_check.md — FalconX/AA_FalconXUSDC redemption terms):
# upgrade from UNKNOWN-pending to:
#   monthly cycle ("Cycle length | One month"); 1-month notice
#   ("Redemptions | Monthly, 1-month notice"); instant/early withdraw exists,
#   enabled when the next-cycle rate is "lower than the previous one by 1% or
#   more", claim "within 72 hours"; min redemption UNKNOWN (not stated);
#   withdrawal fee UNKNOWN ("Performance fee | 10%" is a performance fee, not
#   a redemption fee).
# Sources (quotes relayed; session proxy cannot re-fetch, 403):
#   https://docs.pareto.credit/product/credit-vaults/live-vaults.md
#   https://docs.pareto.credit/product/users/lenders/guides/redeem.md
#   https://docs.pareto.credit/developers/addresses/product/credit-vaults.md
#   (lists Ethereum contract 0x433D5B175148dA32Ffe1e1A37a939E1b7e79be4d).
# The union check's pre-registered hypothesis is CONFIRMED: channels A and B
# described two sides of one mechanism (A = regular monthly epoch redemption;
# B = the parameterized instant-withdraw path). Addendum recorded in
# e2/t1_union_check.md §仲裁. Registry note: e2/registry.csv does not exist
# yet — carry these terms into the AA_FalconXUSDC row when it is created.
# Residual caveat: the relaying pack was itself a model run (vendor unstated);
# channel A's "min 250k, no fee" claims did NOT re-surface and stay UNKNOWN.

# STATUS 2026-07-10 (E2-T2-dune arming, owner pack): ARMING-1 (Dune table
# list) and ARMING-2 (Horizon addresses + reserve-init ABI signatures) both
# came back NEED_INFO — the pack could not see the owner's Dune account and
# refused to invent Horizon addresses (correctly). ARMING-3 arrived as a
# 17-row draft but is QUARANTINED (e2/registry.draft.csv + .NOTES.md:
# admitted-reconstructed market_id, no explorer sighting, env 403).
# E2-T2-dune therefore STAYS manual:true — do not delete the flag until
# ARMING-1/2 are supplied and the draft rows are promoted per the checklist.

# NEED_HUMAN (2026-07-10, DAX-W0.5): legwork tables landed
# (dax/memo/w05_legwork_2026-07-10.md, two rows corroborated by an in-session
# second channel) but the feasibility note is NOT gate-ready: (a) every price
# cell UNKNOWN — owner browser capture of platform.openai.com/docs/pricing;
# (b) GDPval license terms all UNKNOWN — owner browser capture of the
# huggingface.co/datasets/openai/gdpval card; (c) gpt-4-1106-preview shutdown
# CONFLICT (2026-03-26 vs 2026-10-23) — owner to read the deprecations page;
# (d) vendor family of the owner's manual run unstated (dual-channel ledger).

# UPDATE 2026-07-10 (owner second pack, ~10m run; details in
# dax/memo/w05_legwork_2026-07-10.md §Second pass and ops/l1/E2-T2-dune.yaml):
# - DAX-W0.5 item (a) RESOLVED-with-conflicts: prices supplied from OpenAI
#   docs (retrieved 2026-07-09). Two flags carried into the memo:
#   CONFLICT-A — pricing pass lists o1-preview / o1-mini / gpt-4-turbo-preview
#   as accessible while the deprecations pass has them shut down (deprecations
#   page governs accessibility; "yes" treated as page-artifact pending owner
#   re-check); CONFLICT-B — the pricing page itself shows two tables at 2x for
#   the gpt-5.4/5.5/5.6 families (both recorded, neither filed as "the"
#   price). o1-mini/o3-mini output prices remain UNKNOWN.
# - DAX-W0.5 item (b) RESOLVED as a verified negative: HF card openai/gdpval
#   declares NO license (no card metadata license, no LICENSE file; the
#   "solely for research and evaluation purposes" quote is from the
#   Third-Party References disclosure, not a license grant). Feasibility note
#   must treat redistribution basis as an open legal item.
# - DAX-W0.5 item (c) RESOLVED: gpt-4-1106-preview shutdown = 2026-10-23
#   (deprecations page's newer 2026-04-22 section supersedes; page keeps both
#   rows, which caused the original conflict).
# - DAX-W0.5 item (d) STILL OPEN: vendor of the first-pack run unstated.
# - E2-T2-dune ARMING-2 SUPPLIED and spliced into q2: Horizon RWA Market Pool
#   0xAe05Cd22df81871bc7cC2a04BeCfb516bFe332C8 (Ethereum only),
#   PoolConfigurator 0x83cb1b4af26eef6463ac20afbac9c0e2e017202f (owner
#   on-chain reads = first-hand tier); ReserveInitialized signature
#   independently re-fetched in-session from aave-dao/aave-v3-origin
#   IPoolConfigurator.sol — exact match. STILL OWED before un-parking:
#   ARMING-1 (owner Dune table list) + ARMING-3 promotion (registry.draft
#   stays quarantined).

# ROUTED 2026-07-10 (owner-directed in-session — "generate an L1 list fully
# ready to run" for the execution agent): E2-T9b-scenarios goes to the
# Anthropic lane NOW instead of waiting for the gemini_free nightly. Reason:
# the box L1 lane is DOWN (02:03Z inbox run died pre-dispatch — venv broken,
# no python3 module on SCC; NEED_HUMAN below) so the ¥0 path has no ETA; the
# task has no dual-channel pair (no cross-vendor issue); precedent =
# E2-T1-facts channel A. Brief: ops/briefs/E2-T9b-scenarios-escalation.md.
# If the box lane revives first and lands a clean gemini output, that wins.
# It is the ONLY L1 batch armable without owner input today — E2-T2-dune
# (ARMING-1/3), E2-T6b-nav (owner terminal run), P1-T0-monitor (parked to
# 2026-08-01), DAX-W0.5-legwork (superseded by owner inline run) all wait;
# P1-T1-events(+B)/P1-T13-ant(+B) have no specs yet and their sentinels are
# owner-owed (L2-PIPELINE item 7).

# NEED_HUMAN (2026-07-10, box infra): the 02:03Z inbox run broke the L1 lane
# — `.venv/bin/python` missing AND no python3 module visible from the login
# shell (module system regression?), on top of the standing SCC SSH publickey
# NEED_HUMAN. Nightly L1 dispatch (incl. any gemini runs) is dead until an
# interactive fix on the SCC. Also EDGAR_CONTACT: inbox_log still shows the
# harvester refusing to start, yet p1/edgar_filings/manifest.csv is committed
# (547c577) — owner presumably ran it by hand; confirm and, if so, set
# EDGAR_CONTACT anyway so the next payload doesn't re-block.
