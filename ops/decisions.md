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

# OWNER PACK 3 APPLIED 2026-07-10 (all four items owner-stated in-session):
# 1. VENDOR ATTRIBUTION: first-pack DAX legwork run = codex gpt-5.5 (OpenAI
#    family). Dual-channel ledger closed — in-session spot checks were
#    Anthropic-lane, so corroborated rows are cross-vendor.
# 2. CONFLICT-A ADJUDICATED: deprecations page governs; o1-preview, o1-mini,
#    gpt-4-turbo-preview treated as discontinued.
# 3. E2-T2-dune ARMING-1 SUPPLIED (owner Dune account tables:
#    morpho_blue_ethereum/.../base morphoblue_evt_createmarket, 8 fields
#    each). COVERAGE LIMIT recorded in the spec: eth+base only — no
#    polygon/arbitrum tables visible, so Q1 cannot see the sACRED(polygon)/
#    syrupUSDC(arbitrum) markets; q3 subgraph is the cross-chain check.
# 4. REGISTRY PROMOTED: e2/registry.csv created from the draft under owner
#    formal sign-off, with the owner-directed correction (syrupUSDC/base
#    token address owner-verified; its fabricated market_id CLEARED to
#    UNKNOWN). Residual risks accepted at sign-off and recorded in
#    e2/registry.draft.NOTES.md: remaining market_ids are pack-generated/
#    unsighted (T2 acceptance = the catch), mTBILL dual-chain address
#    unconfirmed.
# => E2-T2-dune manual:true DELETED — fully armed; dispatches on deepseek
#    the first night the box L1 lane is back (see NEED_HUMAN below).
# => dax/memo/feasibility_note.md DRAFTED (CONDITIONAL GO: W4 capture before
#    2026-10-23/2026-12-11 shutdowns; stand-ins with EIV caveats,
#    gpt-4.5-preview excluded; GDPval = no license declared → no
#    redistribution in W10a until clarified). Awaiting PI signature:
#    gate DAX-GATE-feasibility pass/fail.

# SIGNED 2026-07-10 (owner, verbatim in-session — "I have reviewed the
# drafted feasibility note and I fully agree with the CONDITIONAL GO verdict
# and its three stipulations (the W4 deadline, the gpt-4.5-preview
# exclusion, and the GDPval license constraints)"; owner directed the gate
# sign-off be executed on their behalf):
# - DAX-W0.5-feasibility deliverable (dax/memo/feasibility_note.md)
#   accepted → task complete.
# - DAX-GATE-feasibility = PASS with the note's three conditions binding:
#   1. W4 capability/cost API capture scheduled before the 2026-10-23 /
#      2026-12-11 shutdown waves (budget line flagged to funder).
#   2. Retired vintages via cited open-weight stand-ins only, stand-in
#      error into the amendment-1 EIV bounds; gpt-4.5-preview EXCLUDED.
#   3. GDPval: task-by-ID referencing only; no GDPval-derived text in the
#      W10a public release until license terms are clarified.
# Owner also confirmed handling box infra repairs (venv, module, SSH,
# EDGAR_CONTACT) manually.
# applied: complete DAX-W0.5-feasibility
# applied: gate DAX-GATE-feasibility pass

# NEED_HUMAN (2026-07-10, box infra): the 02:03Z inbox run broke the L1 lane
# — `.venv/bin/python` missing AND no python3 module visible from the login
# shell (module system regression?), on top of the standing SCC SSH publickey
# NEED_HUMAN. Nightly L1 dispatch (incl. any gemini runs) is dead until an
# interactive fix on the SCC. Also EDGAR_CONTACT: inbox_log still shows the
# harvester refusing to start, yet p1/edgar_filings/manifest.csv is committed
# (547c577) — owner presumably ran it by hand; confirm and, if so, set
# EDGAR_CONTACT anyway so the next payload doesn't re-block.

# ROUTED 2026-07-16 (owner-directed in-session, seat-C lane): a new
# Anthropic-family execution lane is available — Opus 4.8 sessions on the
# owner's BU SCC. Frontier tier stays on spec/audit/gates only (rule 5).
# Prompt pack + structural workplan: ops/briefs/opus/ (P1-T1-events-A finish
# w/ handoff in p1/t1_channelA_wip/handoff/, P1-T13-ant-A, P1-T1-arb
# [blocked], REFR-R0-collide-A re-route, REFR-R1a, REFR-R1b [needs owner
# USMPD heads], DAX-W1-memo, DAX-W2-data). Constraint enforced in the pack:
# channel-B tasks (P1-T1-events-B, P1-T13-ant-B, REFR-R0-collide-B) must NOT
# run on this lane — they stay gemini_free (cross-vendor, meta-rule 2);
# revive via box repair or GEMINI key + l1_driver on SCC. P1-T1-events
# channel A stands at 35/90 batches (rb_001–035 committed); lease held by C.
# FLAG for owner review: this note records lane routing only, no gate calls.

# FIX 2026-07-17 (owner-directed, SCC lane): P1 extraction sentinel fence
# replaced. Old S1/S2 were world-knowledge trivia (S2 = 2025-11 FEDS note,
# past every no-web worker cutoff) — gemini_free voided both P1-*-B batches
# on chunk 1 while returning healthy extractions (see *.void.json). New S1/S2
# are document-grounded (synthetic excerpt, answer known by construction);
# S3 domain fact kept. Both infra strikes cleared (--clear-fail). Owner keys
# arrived: gemini is a PAID key — models.py gemini_free price 0->real 2.5-flash
# so the ledger logs real spend. Owner-approved run order: channel A (deepseek)
# first, then channel B (gemini), P1 tasks only.

ROUTED 2026-07-18 (owner-directed): P1 channel B vendor switched gemini_free →
qwen (Qwen Max/qwen3.x-plus on DashScope, alibaba family) for stability + cost;
gemini was pausing mid-run. Cross-vendor independence vs channel A (deepseek)
preserved (alibaba ≠ deepseek). models.py: qwen id env-overridable via
QWEN_MODEL (default qwen-max), price bumped to Max tier; queue + both B specs +
make_extraction_specs.py updated. Owner pins the exact QWEN_MODEL in ops/box/.env.

SCOPE CHANGE same date: deepseek v2-A accepted as PRIMARY T1 channel (1418/1418,
97.2% agreement with the seat-C reference channel on its 45% overlap). Full
independent channel B is SUPERSEDED by TARGETED arbitration: qwen re-runs only
the contested/self-risky subset (ops/l1/P1-T1-events-arb-qwen.yaml, 140 items;
rationale in p1/t1_flagged_for_arb.md). The gemini v1/v2 partial outputs remain
archived for the record. T1-arb adjudicates deepseek-vs-qwen-vs-reference on the
flagged set; un-flagged deepseek verdicts stand.

ASSEMBLED 2026-07-18 (seat C): P1-T1-arb → p1/events_merged.csv (contract PASS,
139 conversions). Upstream channel adjudication (deepseek v2-A + qwen tiebreaker
+ owner gate, 21 flips) collapsed via p1/t1_arb/assemble.py: 1207 event-filings
→ 248 conversion groups → 139 with resolvable fund_name+effective_date; 109 held
back as needs_fulltext (no closing date in excerpt windows) in p1/t1_arb/
arb_report.md; 17 effective_date conflicts resolved to latest-filed. NEXT: human
門 1 P1-T1-spotcheck (H 抽10%, M/L 全查) over events_merged.csv is READY for owner;
needs_fulltext list also owner-actionable. Did NOT runner --complete (manual lane).

GATE1 2026-07-18 (owner spotcheck of events_merged.csv): 9 false-positive rows
caught — all ETF-to-ETF mis-verdicts on UN-REFEREED deepseek rows (not in the
qwen-140 set). Applied via p1/t1_arb/apply_spotcheck.py: 6 filings→no_event, iM
DBi events removed + Dolan McEniry held for recheck, Zevenbergen deferred
(future-dated source). Fixed an over-merge (name-only grouping collided distinct
same-named funds) by keying assemble on (fund_name, family) + a PK-collapse pass
for cross-trust splits. events_merged.csv now 173 conversions, contract PASS.
Corpus evidence-sweep confirms no other ETF-to-ETF survive. Results in
p1/t1_spotcheck_results.md. Date-recovery (deepseek, box) had promoted held-back
dates just prior (¥0.83, fence held).

FULL-REVIEW 2026-07-18 (owner manual re-eval of all events): applied via
p1/t1_arb/apply_full_review.py (record: owner_full_review.csv). 5 event→no_event
(ETF/ETP-to-ETF: CSOP A50, WisdomTree GCC, iShares LifePath 2025, Sterling Core
Bond, Impact Shares MBS); 1 no_event→event (Chestnut Street Exchange Fund);
96 event rows→recheck (owner evidentiary standard: 'acquirer is an ETF' alone
insufficient — must prove target was open-end/mutual fund); 11 no_event→
recheck_noevent (blank/weak evidence). events_merged.csv 173→124 (recheck items
quarantined pending full-text target-type proof). NEXT: recheck full-text pass
(deepseek re-reads raw filings to confirm target fund type + pull MF ticker).

# BLOCKED 2026-08-18 (seat C, refraction session — egress policy, not a vendor
# failure): REFR-R0-collide channel A and REFR-R1a-verify were both attempted
# in this Claude Code session per their briefs (ops/briefs/opus/OPUS-REFR-
# R0-collide-A.md, OPUS-REFR-R1a-verify.md, routed to the Anthropic lane
# 2026-07-16 after the kimi bench). Neither can be executed here: this
# container's egress proxy answers 403 CONNECT for every primary source both
# tasks require —
#   www.frbsf.org (USMPD), www.federalreserve.gov (FOMC calendars),
#   www.bls.gov (CPI/Employment Situation schedules),
#   papers.ssrn.com, doi.org, export.arxiv.org, api.semanticscholar.org,
#   www.jstor.org
# WebSearch (result titles/URLs) works; WebFetch and curl do not. Search
# snippets are second-hand summaries, so they cannot satisfy R1a's "逐字引用
# ≤25词 + 页码/URL" or R0's per-claim first-hand URL rule. Per meta-rule 1 and
# the 铁律, NOTHING was written from memory or from snippets and no partial
# registry was emitted — an R1a table with unverifiable rows is worse than no
# table, because R1b would parse it.
# NEED_HUMAN: re-route both to a lane that can actually fetch — the SCC Opus
# lane, a claude.ai session with web access, or an owner browser pass — or
# have the owner widen this environment's egress allowlist to the seven hosts
# above (frbsf/federalreserve/bls are the R1a critical path; ssrn/doi/arxiv/s2
# are R0's). R1b stays blocked on R1a plus the owner-pasted USMPD file heads
# either way, so this does not newly block the chapter; it just means the two
# retrieval nodes stay READY and unclaimed.
#
# LANDED same session (the one REFR node that needs no external facts):
# REFR-R13-scan — refraction/scan.py (resident monthly collision monitor,
# arXiv + S2 APIs + generated SSRN URLs, §R13b Marta–Riva/replication-switch
# 毛刺 flag + 40%/60% ALERT threshold computed in the script), 23 pytest cases
# on synthetic payloads (network poisoned in tests), refraction/scans/
# manifest.md, lineage JSON. NOT marked complete — R13 is resident, exactly as
# E2-T11-scan is left ready forever. Cron wiring is a seat-D edit
# (ops/box/cron_night.sh, monthly): see the manifest's handoff section.

# P1-T2 2026-08-18 (seat C, same session as the refraction block above): the two
# coverage-audit items that needed no network are implemented, and the audit's
# open verification check was run and FAILED, so a third instance of the
# concatenated-program defect is now fixed. Detail in
# p1/output/convexp_coverage_audit/{coverage_audit_memo.md,README.md}.
#   item 2 (retain shares_held on dropped cells) — done; sidecar
#     p1/t2_free/dropped_cells_shares_held.csv, now recover_denominators.py's
#     default for --shares-held.
#   item 4 (valUSD for value-weighted coverage) — done; val_usd on computed rows
#     and in the sidecar.
#   item 1 (waves.csv corruption) — root-caused: build_waves.py held two
#     programs and the dead 7-column main() was the one that ran, so the audit's
#     hand-cleaned file would have been overwritten and waves_members.csv left
#     stale on the next invocation. Scaffold removed; regenerated by the pipeline
#     itself (78 waves / 131 members, content identical to the hand-cleaned file).
#
# BOX ACTION REQUIRED for items 2 and 4 to produce anything: they are inert until
# `python p1/t2_free/build_nport_convexp.py` is re-run with net access. In the
# SAME commit that lands the rebuilt parquet, uncomment the `val_usd` line in
# ops/contracts/conv_exposure_free.yaml — contracts.py treats every declared
# column as mandatory, so declaring it earlier would retroactively fail the
# artifact Gate 2 was signed on. Then `--online` recovery can finally PROVE
# (not merely expect) that the >=0.5% treated set is unchanged.
#
# STILL OWNER-OWED, unchanged by this session: audit item 5 — how the paper
# treats the international sleeve (Mirae W020 alone is 49% of all dropped cells;
# document it in the sample definition, or scope a separate non-US analysis).
# Also note the queue's bookkeeping is stale against the repo: P1-T1-events(+B)
# are not marked complete, so the runner still shows P1-T1-arb as blocked while
# events_merged.csv and the spotcheck sign-off are committed.

# P1-T2 item 5 COSTED 2026-08-18 (seat C; decision still owner's, nothing chosen):
# p1/output/convexp_coverage_audit/international_sleeve_options.md attaches numbers
# to the international-sleeve question. DFA anchor wave W002 is `no_intl`, so it
# survives every option. Dropping pure-international waves costs 8 stocks at the
# >=0.5% treated line (389 -> 381; power floor is >=33). Dropping any wave that
# merely touches an international fund costs a third of the >=1% names (24 -> 16).
# Excluding international FUNDS rather than WAVES is not a filter on the built
# parquet — cells are aggregated across a wave's funds — it needs a fund-level
# re-run on the box, best bundled with the re-run that activates audit items 2/4.
# OWNER, one line please: Option A, A-strict, or A + fund-level rebuild? Record it
# before T5 main estimation so the sample definition is fixed independently of any
# outcome (no specification search).

# WRDS-INDEPENDENT WORK COMPLETE 2026-08-18 (seat C, owner-directed: "identify
# them and start working on them now"). Register: ops/briefs/WRDS-independent-
# workplan.md — 18 problems that survive WRDS's arrival, six of which this seat
# could execute with no access to anything. All six landed with tests (252
# passing, from 137; selfcheck clean throughout):
#   W-06 CRSP licensing guard (irreversible-failure item, done first)
#   W-07 holdings_pipeline.py made real and testable, schema isolated+UNVERIFIED
#   W-08 coverage_census.py — run FIRST when access lands, before the pipeline
#   W-17 reconcile_convexp.py — free-path vs WRDS, bands frozen pre-data
#   W-03b refraction R1b transform+assertions, and the exact owner paste-list
#   W-05b fund-level asset-class filter (sleeve decision becomes one flag)
#   W-18 yfinance/Stooq recovery retired as superseded-pending-WRDS (kept)
# NOTHING on that register is now blocked on this seat. Owner-owed: the R1b
# paste-list, the consensus source, the sleeve decision, the holdings_weights
# alignment, the P1-T1 gate calls, prereg sequencing, and BOX INFRA — the SCC
# SSH/venv breakage gates the WRDS pull itself, so it is the one worth fixing
# while delivery is pending. Lane-owed: a web-capable session for R0/R1a, seat D
# for the refraction cron line and for folding the data policy into COMPLIANCE.md.

# REFRACTION AUDIT 2026-08-19 (seat C, owner-requested quality review of
# refraction/ only). Full findings: refraction/AUDIT-2026-08-19.md.
# VERDICT: machinery sound (iron rules are program invariants, 14/14 panel
# asserts present, 90 tests green, no post-period column touched). The defects
# are missing NUMBERS and two spec conflicts, all of which must be settled
# BEFORE Gate-0 — settling them after seeing a diagnostic is specification
# search regardless of who does it.
# FIXED IN THIS PASS:
#   - G1 threshold was missing entirely: surprise_coverage_min: 0.95 transcribed
#     from Plan §9 (transcription, not a choice; R3 would otherwise hardcode it).
#   - G4 and G6 thresholds do not exist anywhere to transcribe -> added as
#     explicit nulls (d_b_mass_share_min, pretrend_joint_p_min) so R3 fails on
#     the config read. Iron rule 4 as configuration.
#   - §0.4 manifests were missing for two landed deliverables -> refraction/
#     MANIFEST.md now covers every artifact with digests, limitations, UNKNOWNs.
#   - New test file pins every Gate-0 threshold to its Plan v2.1 value and fails
#     if a null one acquires a value without an owner decision recorded here.
# OWNER DECISIONS NEEDED BEFORE R3 (four):
#   1. d_b_mass_share_min — G4 "sufficient treatment mass with D_b >= 0.1".
#   2. pretrend_joint_p_min — G6 "flat/zero"; DAX Decision 14 (joint p >= 0.10,
#      no Holm-adjusted individual lead) is the obvious precedent.
#   3. Plan §9 vs 执行手册 §R3: Plan puts median n_pre >= 30 INSIDE the G2 joint
#      window; the 手册 sweeps three conditions and treats n_pre as a separate
#      G3 line. This decides whether the feasible w_shrink window is non-empty,
#      and an empty window is the Plan's own trigger for portfolio-level-or-kill.
#   4. sample.waves_end is 2025-12-31 but p1/t2_wrds/waves.csv now runs to
#      2026-11-20 (11 waves past the cap, some future-dated). Is the cap current,
#      and what minimum post-period must a wave have? Assert A2 CANNOT catch a
#      truncated post window — it measures coverage against a calendar that is
#      itself truncated at announcements_end — so this needs a config line, not
#      a code fix.
# DISCLOSE AT R4/OSF (not a defect): S_std uses the FULL-SAMPLE in-sample std per
# C0-R, so an early announcement's scale embeds later variance. Does not breach
# the lookahead ban (rule 4 names beta/priors/L/weights), but state it and name
# expanding-window standardization as the robustness variant.
# PROCESS DEVIATIONS ON THE RECORD: R1b's transform half was built by this Claude
# Code seat though the queue routes REFR-R1b-parse to deepseek (no channel pair,
# so no cross-vendor breach — but the DeepSeek executor should EXTEND the adapter,
# not rebuild the module); the R1b and fetcher work carried no lease and ran on
# the harness-pinned branch rather than task/<id>. scan.py and fetch_r1a_sources.py
# have never run live — treat their first output as evidence to review.

# REFRACTION GATE-0 DECISIONS 2026-08-19 — MADE UNDER DELEGATION, AWAITING PI
# COUNTER-SIGNATURE (owner instruction: "go ahead and make these decisions for
# me", following refraction/AUDIT-2026-08-19.md). Full reasoning and the evidence
# table: refraction/DECISIONS-2026-08-19.md. Same standing as DAX's D1 memo —
# recorded and machine-enforced, binding only once signed.
# Legitimacy note: no Gate-0 diagnostic has run (R3 has not executed; there is no
# panel, beta, or sweep output), so fixing these now IS pre-registration. Doing it
# after a first diagnostic would have been specification search.
#   D-A  d_b_mass_share_min = 0.50 — G4 clears at a MAJORITY of treated ConvExp
#        mass (mass-weighted, not name-counted). Failing G4 costs language (the
#        §10 framing gate), not the chapter, so a strict line is cheap insurance
#        against overclaiming. 0.70 considered for consistency with G2 and
#        rejected: G2's share is estimability, G4's is mechanism presence.
#   D-B  pretrend_joint_p_min = 0.10 + pretrend_individual_lead_adjust = holm —
#        DAX Decision 14 adopted verbatim; house precedent beats an invented
#        number and gives one flatness standard portfolio-wide. CAVEAT recorded
#        in-config: this is a failure-to-reject, so R3 must report pre-trend CIs
#        beside the p and it is only meaningful against G5's archived power bar.
#   D-C  Plan §9 vs §R3 conflict RESOLVED BY OBSERVATION, no arbitration needed:
#        median n_pre is invariant in w_shrink, so the Plan's "inside the joint
#        window" is satisfied automatically whenever the line holds, and if it
#        fails it fails at every w = an empty window. R3 must route a G3 failure
#        into the empty-window portfolio-level-or-kill branch.
#   D-D  post_quarters_required = 4, waves_end = 2025-06-30 (was 2025-12-31).
#        Evidence: 4 post-quarters costs 9 of 395 treated names (2.3%) while
#        keeping 53 waves; a symmetric 8Q costs 28 waves and therefore effective
#        clusters, buying 1 further treated name. waves_end is no longer hand-set
#        — it is governed by the invariant waves_end + post_quarters_required <=
#        announcements_end, enforced in tests, and assert A2 now reads the post
#        bound from config instead of mirroring the pre bound.
# TO REVERSE ANY OF THESE: now is the free moment — nothing downstream has run.
