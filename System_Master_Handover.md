# System Master Handover — research-portfolio (P1 · E2 · DAX · Refraction)
### For a successor model with zero historical context. Written 2026-07-12 from repo state + session records.

> Read this once, top to bottom (~15 min). Then read `CLAUDE.md` (the standing rules you
> operate under), then `ops/runner/queue.yaml` + `ops/runner/state.json` (what is done and
> what is ready), then `ops/decisions.md` (the owner's live decision log). After that you
> know everything this document knows. **The repo is the only shared state — nothing
> important lives in any conversation history, including the one that wrote this.**

---

## 1. What this system is

One PhD student (the owner; BU Economics) is running **four research papers as one
industrialized portfolio**, using a multi-layer, multi-vendor agent pipeline with a fixed
monthly budget (Claude Pro subscription + ¥300–500 API). The repo is simultaneously:

1. **The dissertation** — three chapters are required to graduate.
2. **The factory that produces it** — a deterministic scheduler (L0), cheap automated
   workers (L1), scarce human-driven frontier seats (L2), and human gates (L3).
3. **The audit trail** — every number must trace to executed code or a source URL;
   contracts, sentinels, lineage JSONs, and a decisions log enforce this mechanically.

The architecture doc is `docs/Agent_Architecture_24x7.md`; the one rule that explains most
design choices is **Rule Zero: agents write scripts; scripts do the long-running work.**

## 2. The four projects and how they fit together

### 2.1 The business logic in one paragraph

The advisor approved **P1** and **DAX** as chapters; **E2 is pending approval and may be
rejected**. **Refraction** exists as the engineered hedge against that rejection: a fourth
chapter built to top-field standard, held at "Gate-0-passed, pre-registered, dormant" for
near-zero carrying cost, promoted the moment the E2 verdict lands (either way — if E2
passes, Refraction becomes the fourth paper / job-market spare). The queue's ceiling
priority is `dax > e2 > p1`, but the **scheduling fulcrum is the E2 verdict**
(`REFR-GATE-e2verdict` in the queue). Graduation logic and ceiling logic are different
orderings — do not confuse them when arbitrating seat time.

### 2.2 Project by project

| | P1 (approved) | E2 (pending) | DAX (approved) | Refraction (standby) |
|---|---|---|---|---|
| Question | Do mutual-fund→ETF conversions (wrapper changes, delegation constant) change how **earnings information** gets into stock prices? | RWA (real-world-asset) tokens with embedded leverage / looping in DeFi: panel, facts, risk engine | A monthly, cost-thresholded **Dynamic AI Exposure index**: when does AI substitution become privately cost-effective per occupation, and does crossing predict labor-market adjustment? | Do newly wrapped ETF **baskets refract scheduled macro news** (FOMC/CPI/NFP) into constituents — and is the refracted component information or noise? |
| Identification asset | Conversion events + ConvExp exposure panel (EDGAR-harvested, dual-channel verified) — **the portfolio's crown jewel** | On-chain data (Dune SQL, subgraphs), dual-channel fact verification | GDPval-era capability × price panel; GPT-4o price-cut event; pre-registered stacked event studies | **Reuses P1's frozen assets read-only** + announcement-regime betas and a leave-one-out basket lever L |
| Deliverable logic | JFE/RFS-class paper; races Saglam–Tuzun's 12–18-month window | Fastest publishable note (T15) + commercial engine (T9a) | OpenAI ERE proposal (`docs/DAX_ERE_Proposal_v3.md`); highest ceiling, external funder | Standby chapter; both main exits (efficiency / fragility) publishable |
| Manual | `docs/Project_1.md` + `P1_修订补丁_v1_1.md` | `docs/E2_执行手册_v1_1_完整版.md` + patches | `docs/DAX_Execution_Plan_with_AI_Agents.md` | `docs/Refraction_执行手册_v1_0.md` (R0–R14) — supersedes the English playbook |
| Plan | `docs/基金转换实验_博士研究计划.md` | `docs/E2_研究计划_RWA内嵌杠杆.md` | ERE proposal + Amendment v1.1 | `docs/MacroEvent_Chapter_Plan_v2_1_FINAL.md` (v2.1) |

### 2.3 The load-bearing couplings (what breaks what)

- **P1 → Refraction (data):** Refraction consumes P1's `events_merged.csv`,
  `conv_exposure.parquet`, `holdings_weights.parquet`, `ibes_sue.parquet` **read-only,
  hash-registered**. If P1's event harvest changes (it did once — see K-4 below),
  Refraction's exposure panel inherits the fix automatically ONLY if it re-reads the frozen
  files; never fork them.
- **P1 ↔ Refraction (intellectual):** one dissertation arc — the index revolution
  reallocates price discovery across the micro–macro boundary (Sammon MS 2025 shows passive
  erodes micro/pre-earnings discovery; P1 tests wrapper × earnings info; Refraction tests
  wrapper × macro news). This arc is the advisor's original "Project 1 as two chapters"
  request, rebuilt causally. It is also the anti-salami defense both chapters cite.
- **DAX → Refraction (pattern):** DAX invented the repo's pre-registration enforcement
  (locked `analysis/outcomes/`, `v1.0-preregistered` tag, fail-closed guard). Refraction
  generalized it (`refraction/guards/prereg_guard.py`). Keep the two patterns aligned.
- **E2 → Refraction (manual):** the Refraction 执行手册 inherits E2's architecture, iron
  rules, and capability-review conclusions wholesale. A change to E2's appendix-A vendor
  verdicts propagates to Refraction assignments.
- **Shared runtime:** `shared/econlib` (stacked DiD, CS/SA, wild bootstrap, randomization
  inference, event-study plots) serves P1-T5, E2-T8, DAX-W8, REFR-R6 alike. One bug there
  is a four-paper bug — it has the strictest test discipline for a reason.
- **Never rules (CLAUDE.md):** no DAX `analysis/outcomes/` before the prereg tag; no OpenAI
  NDA aggregates in the repo (CI greps); no specification search anywhere.

## 3. The runtime in 60 seconds

- **L0** — cron + `ops/runner/` (queue DAG, leases, contract validator, budget governor,
  sentinel harness, digest). Free, truly 24/7, no LLM, holds no Claude credential.
- **L1** — cheap automated workers (DeepSeek code/reasoning, Kimi retrieval **[currently
  BENCHED]**, GLM/Qwen second stack + 中文, Gemini-free channel B). Dispatched overnight
  from `ops/l1/<task>.yaml` specs; trustworthy **only inside sentinel fences**.
- **L2** — Claude Pro seats A–E, human-driven, partitioned by project subtree
  (`ops/accounts.yaml`): A=dax, B=e2, C=p1+refraction, D=shared/ops, E=writing float.
  Seats coordinate ONLY through git (leases, contracts) — never through conversation.
- **L3** — the owner's ~30 min/day: digest → `ops/decisions.md` → gates unblock.
- Cross-vendor independence (meta-rule R2): every dual-channel pair and red-team pairing is
  cross-vendor-family; the runner selfcheck enforces it on `channel_of` pairs.

## 4. State snapshot (2026-07-12)

- **Completed** (`state.json`): SH-runner, SH-econlib, P1-T2a-power (+gate PASS),
  P1-T0-crash A/B (collision verdict: CONTINUE), E2-T1-facts A/B (+union arbitration),
  E2-T9b-scenarios, DAX-W0-infra; gates cleared: `P1-GATE-t2a`, `DAX-GATE-feasibility`.
- **P1 harvest:** K-4 remediation done — union re-harvest 1832 filings (conversion family
  9 → 879 hits); extraction specs regenerated; T1 dual-channel extraction is next.
- **⚠ Branch alert:** everything Refraction (project dir, guards, queue nodes REFR-*,
  contracts, both macro-chapter docs) lives on branch
  `claude/macro-event-dissertation-chapter-dqakv4` — **PR #20, NOT yet merged to main**.
  A fresh clone of main will not contain it. First action if you can't find `refraction/`:
  check that PR.
- **Parked / benched:** kimi benched for retrieval batches (Wave-0, three failure
  families); re-arm decision due 2026-08-01. Parked specs carry `manual: true` + header
  notes: P1-T0-monitor, REFR-R0-collide, REFR-R1a-verify, DAX-W0.5-legwork (seat E inline).
- **Open owner items (NEED_HUMAN):** K-1 per-fund AUM browser check (blocks nothing until
  P1-T5, then blocks); FalconX redemption source (403'd, conflict 2 in
  `e2/t1_union_check.md`); SCC SSH publickey outage (box cron unaffected, red-path response
  delayed); CPI/NFP consensus license; ETF Global access; holdings_weights口径 alignment;
  Gate-0 threshold confirmation; E2 verdict itself.

## 5. Major pitfalls encountered (with receipts — read these before repeating them)

1. **Grounded ≠ true.** Gemini answered a fact (FalconX vault launch) wrongly **despite 34
   grounded searches**; the owner's personally-confirmed date won. The dual-channel union
   check exists precisely for this (ops/decisions.md, RESOLVED 2026-07-09). Never let one
   vendor's confident, cited answer bypass the union check.
2. **Model memory poisons quietly.** The "2026-07-23 gpt-3.5-turbo shutdown" date rested on
   a community post and turned out to be the wrong model set (git 42099ca / a7d23ff); DFA
   per-fund AUMs were a later-snapshot artifact requiring an SEC N-14 fix (K-1). Meta-rule
   R1 (no numbers from memory) is not bureaucracy; it caught real errors within days.
3. **Too-narrow extraction silently shrinks the universe.** The EDGAR harvest's original
   phrase family found 9 conversion filings where the corrected family found 879 (K-4).
   For event studies this is the deadliest failure shape: everything runs, nothing errors,
   the sample is wrong. Coverage guards + loud truncation warnings (T-1 fix) are the
   countermeasure — keep them.
4. **Silent data-corruption modes in long pipelines:** capped pagination with no signal
   (T-1), partial downloads that resume-as-complete (T-2). Fixes: loud WARNING on caps,
   write-to-`.part` + atomic rename. Apply both patterns to any new fetcher.
5. **Retrieval vendors fail in families, not instances.** Kimi produced three distinct
   failure families across three tasks (404s, prose-drift, plan-then-stop, UNKNOWN on armed
   sentinels) → benched entirely rather than retried per-task. The two-strike ladder plus
   bench-with-decision-date is the pattern; per-task heroics are the anti-pattern.
6. **Sentinel/modality mismatch burns strikes.** T-4: asking post-cutoff world knowledge of
   a `web_search: false` worker guarantees UNKNOWN-on-sentinel and voids good batches.
   Rule: fences for non-web workers use stable in-domain facts only.
7. **The session proxy 403s key sources** (SEC/EDGAR, seekingalpha, some docs sites).
   Design consequence: verification tasks must fail loud, not silent, and unresolvable
   checks become owner-browser items in decisions.md — never "probably fine".
8. **Positioning is perishable.** The original micro (earnings) half of the macro/micro
   idea was occupied by Sammon (MS 2025); the macro half was rebuilt twice more when review
   found the naive designs dead on arrival (saturated arbitrage conduit predicting its own
   null; "power" that was outcome repetition, not treatment variation; basket≈market
   observational equivalence; the shrinkage knob coupling two Gate-0 pass lines). Lessons:
   run collision sweeps BEFORE design freeze, red-team the design before building, and
   pre-commit framing downgrades (the framing gate) so claims can't inflate after results.
9. **Infra masks its own breakage.** SSH auth broke account-wide but was hidden for hours
   by a persistent ControlMaster socket; CI gates PRs but lanes push straight to main, so
   enforcement is post-merge. Assume liveness signals lie; verify the actual path.
10. **Session death is normal, not exceptional.** Everything that matters is committed;
    briefs make fresh sessions zero-memory-capable. If you inherit mid-task, `git pull` +
    the brief is the whole recovery procedure. (This handover exists because that works.)

## 6. System-level recommendations for the next iteration

1. **Merge or die: get PR #20 decided.** The standby chapter's entire machinery sits on an
   unmerged branch. Either merge it to main (recommended — it passed selfcheck + 69 tests)
   or consciously park it; do not let it drift behind main.
2. **Promote the guard patterns to `shared/`.** Three projects now hand-roll invariant
   guards (DAX outcomes-lock, Refraction prereg/lookahead, E2's hard gates in code). Next
   econlib iteration should ship `econlib.guards` (fail-closed tag/timestamp checks,
   lookahead assertions) so the fourth implementation isn't hand-rolled too.
3. **Kill LLM-retrieval on the critical path.** The scanner architecture that survived
   contact with reality is script+API (arXiv/Semantic Scholar) with LLM triage only
   (E2-T11, REFR-R13). Extend that to every monitoring task; reserve LLM web search for
   one-off verifications with sentinel fences and a second channel.
4. **Contract-first for every new artifact.** Refraction registered its five output
   contracts before any producer ran. Retrofit the remaining E2/DAX outputs that still have
   `output_contract: null` — the validator is free and catches schema drift at merge time.
5. **Unify the K-item / NEED_HUMAN tracker.** Open knowledge errors (K-1, K-2) and
   NEED_HUMAN items live scattered across decisions.md, audit briefs, README tables, and
   memo flags. One `ops/OPEN_ITEMS.md` (or a digest section) with owner+deadline per item
   would have prevented K-1 sitting unresolved while its CSV feeds toward P1-T5.
6. **Close the post-merge CI gap.** Either protect main (PR-only) or add the selfcheck as a
   pre-push hook for the lanes. A red main has not shipped yet; that is luck, not design.
7. **Make the graduation-critical path explicit in queue meta.** `priority_order:
   [dax, e2, p1]` encodes ceiling, not graduation risk. Add a `graduation_critical:` note
   (or per-task priority overrides) so a zero-context scheduler doesn't starve the E2
   verdict path or the Refraction standby build during contention.
8. **Keep the supersession-banner discipline.** Two macro-chapter execution documents
   coexist (English playbook, Chinese 执行手册); the banner + ID mapping prevented a
   two-sources-of-truth failure. Any doc replaced by a newer version gets the banner, same
   commit.
9. **Vendor table is a quarterly perishable.** Model/pricing verdicts (manual headers say
   so) and the bench list must be re-probed with the three standard probe tasks; the
   2026-08-01 kimi re-arm decision is the next scheduled instance — don't let it slip.
10. **Protect the two human monopolies.** The system deliberately reserves (a) gate
    adjudication/thresholds and (b) dual-channel conflict arbitration for the owner.
    Every past incident where a model "helpfully" resolved these (Gemini's confident wrong
    date; threshold self-selection) is why. Draft verdicts, never issue them.

## 7. First-hour checklist for the successor

1. `git fetch --all` — check whether PR #20 merged; if not, read it (branch
   `claude/macro-event-dissertation-chapter-dqakv4`).
2. Read `CLAUDE.md` (rules), then `README.md` (runtime), then this document's §2 table.
3. `make plan` (or read `ops/runner/queue.yaml` + `state.json`) — the ready set is your
   work queue; claim via `ops/runner/lease.py` before touching anything.
4. Read `ops/decisions.md` bottom-up until you hit a date you've seen; unapplied owner
   decisions outrank everything here.
5. Check `ops/l1/out/` for overnight batch results awaiting validation, and
   `ops/briefs/L2-AUDIT-2026-07-10.md` for the open T-3/T-4/K-1..K-4 items.
6. Then: one task per session, on its `task/<id>` branch, in your seat's subtree,
   run-until-blocked, `/clear` between tasks. The repo is the only teammate you have —
   and the only one you need.
