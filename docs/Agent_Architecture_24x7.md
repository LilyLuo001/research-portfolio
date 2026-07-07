# 24×7 Multi-Project Agent Architecture v1.0

**Scope:** runs P1 (fund conversions), E2 (RWA looping), and DAX (AI exposure) as one portfolio.
**Resources:** Claude Pro subscription (fixed cost) + ¥300–500/month external API budget + one human reviewer (~30 min/day).
**Companion patches:** `P1_修订补丁_v1.1.md`, `E2_修订补丁_v1.2.md`, `DAX_Amendment_v1.1.md` — task-level model reassignments live there; this document defines the runtime they plug into.

---

## §1 Design philosophy: what "24/7" means under your constraints

Two facts dictate the whole design:

1. **Claude Pro is a shared, rate-limited pool.** Chat, Projects, Research mode, and Claude Code all draw from one budget with a 5-hour rolling window plus a weekly cap. It is your highest-quality resource and it cannot run continuously. Treat it like telescope time: scheduled, prepared-for, never wasted on work a script or a cheap model could do.
2. **¥300–500/month buys enormous volume at the budget tier and almost nothing at the flagship tier.** DeepSeek/Kimi/GLM/Qwen-class APIs at this budget support tens of millions of tokens monthly; a handful of Western-flagship API calls would consume the same budget in a day. Gemini's free tier adds a second non-Anthropic vendor at zero cost.

Therefore the system is **not** "three LLM agents running around the clock." It is:

> **A deterministic backbone that runs 24/7 for free, dispatching cheap-model batch work overnight and staging everything so that your scarce Claude Code blocks and your scarce 30 human minutes are never spent waiting, deciding what to do next, or redoing lost work.**

The single most important principle, worth stating before the diagram:

> **Rule Zero — Agents write scripts; scripts do the long-running work.** An LLM session must never *be* the long computation. If a robustness grid takes six hours, the agent's job is a checkpointed script + tests delivered in 30 minutes; the scheduler runs the six hours. This one rule eliminates the dominant failure mode ("agent broke down mid-task") by making mid-task breakdown structurally impossible for anything long: sessions are short, and long things are resumable code.

---

## §2 Architecture: four layers

```
┌────────────────────────────────────────────────────────────────┐
│ L3  HUMAN GATES (30 min/day)                                   │
│     daily digest → decisions.md → gates unblock                │
├────────────────────────────────────────────────────────────────┤
│ L2  CLAUDE PRO (fixed cost, rate-limited → scheduled blocks)   │
│     Claude Code (Sonnet): pipeline eng., arbitration, escalation│
│     claude.ai Projects: specs, memos, writing, Research mode   │
├────────────────────────────────────────────────────────────────┤
│ L1  CHEAP WORKER POOL (¥300–500/mo, runs overnight, 24/7-able) │
│     DeepSeek: batch code, robustness grids, tests, reasoning-B │
│     Kimi: long-doc extraction, web-search tasks, lit monitoring│
│     GLM/Qwen: 2nd code channel (R), 中文材料, bulk annotation   │
│     Gemini Flash (free tier): cross-vendor channel B, QA       │
├────────────────────────────────────────────────────────────────┤
│ L0  DETERMINISTIC BACKBONE (free, truly 24/7)                  │
│     monorepo (git) · task DAG (queue.yaml) · scheduler (cron)  │
│     schema validator · manifest/lineage · budget governor      │
│     sentinel checks · escalation digest · econlib (shared)     │
└────────────────────────────────────────────────────────────────┘
```

### L0 — Deterministic backbone (free, the actual 24/7 layer)

One monorepo, three project directories plus `shared/`:

```
repo/
  shared/econlib/        # stacked DiD, Callaway–Sant'Anna wrappers, wild
                         # bootstrap, randomization inference, event-study
                         # plots — built ONCE, tested, imported by all three
  shared/contracts/      # unified schema registry (one YAML format replacing
                         # P1 §5, E2 连续性矩阵, DAX lineage — same semantics)
  shared/runner/         # queue.yaml (task DAG), runner.py, budget.py
  p1/  e2/  dax/         # each keeps its manual's task IDs (T*, W*)
  ops/digest/            # daily digest + decisions.md (L3 interface)
```

Components, all plain Python + cron on your own machine (or any always-on box — an old laptop is fine; a budget VPS also works but eats ~10% of the API budget, so prefer hardware you own):

- **`queue.yaml` task DAG.** Every task from the three manuals becomes a node: `id, project, depends_on, worker (which model/channel), input_files, output_contract, max_attempts, escalation_path, human_gate (bool)`. The DAG is the merged form of P1 §5, E2's 连续性矩阵, and DAX §2 — one vocabulary.
- **`runner.py` scheduler.** Cron-driven loop: pick ready tasks (deps satisfied, gate cleared, budget OK) → dispatch to L1 via API, or emit a **prepared brief** for the next L2 block, or run a plain script. Retries with backoff; two-strike escalation (below).
- **Schema validator.** On every task completion, validates output files against the contract *mechanically* (columns, dtypes, row counts vs. manifest, key uniqueness). This replaces ~80% of what P1's T12 and E2's T14 assigned to LLM meta-agents — a critical budget saving, and *more* reliable: contract checking is exactly what deterministic code beats LLMs at.
- **Budget governor.** Logs every API call's cost estimate; hard-stops L1 dispatch at 80% of monthly budget (remaining 20% reserved for escalations); daily spend line in the digest.
- **Sentinel harness.** Generalizes P1's sentinel-row trick to every batch job: each batch includes known-answer items; mismatch voids the batch automatically. Cheap models are only trustworthy inside sentinel fences.

### L1 — Cheap worker pool (the overnight shift, ¥300–500/month)

| Worker | Role across the portfolio | Why it, budget share (range) |
|---|---|---|
| **DeepSeek** (V-series + reasoning mode) | Batch/templated code (P1-T7, E2-T8c-py, E2-T10, DAX robustness scripts); unit-test generation; **reasoning channel B** for every dual-channel spec/red-team task | Near-frontier code at budget price; reasoning mode is the affordable non-Anthropic "second brain." ~40–50% |
| **Kimi** (K-series, `$web_search`) | Long-document extraction (P1-T1, E2-T6b overflow); web-verified fact tasks (E2-T1, T9b); monthly lit monitoring (all three) | Long context + native API search + citation discipline. ~25–35% |
| **GLM / Qwen** | Second implementation channel (E2-T8c-R); 中文材料 (P1-T11); bulk annotation (DAX-A5, frozen rubric) | Cheapest adequate tier; keeps dual-implementation cross-vendor. ~10–20% |
| **Gemini Flash, free tier** | Channel B for dual-channel extraction (P1-T1乙, DAX audit split); mechanical QA where the validator needs judgment; red-team second reader | Zero cost; adds a third vendor family, preserving every manual's cross-vendor independence rules without budget. ¥0 |

All L1 calls go through one thin client (plain SDKs or LiteLLM — avoid heavyweight agent frameworks; every added framework is a new mid-task failure source). L1 runs **overnight batches**: the scheduler queues extraction/robustness/test jobs after your evening review, results + validator verdicts await you in the morning digest.

### L2 — Claude Pro (the scarce flagship, scheduled)

Split Pro usage into two disciplined channels:

**Claude Code prime blocks (Sonnet), 1–2 per day, 60–90 min each.** Reserved for what actually needs an agentic frontier coder: pipeline engineering (P1-T2, E2-T3/T9a, DAX-W0/W2/W5/W8 implementation), `econlib`, arbitration of dual-channel diffs, and **escalations** (anything a cheap worker failed twice). Session protocol — this is your anti-breakdown discipline for the rate-limited layer:

1. Every block starts from a **prepared brief** (`ops/briefs/T*.md`, generated by the scheduler): task, contract, file paths, acceptance tests. A fresh session needs zero conversational memory — repo state *is* the state.
2. **Plan → execute → commit early and often.** If the 5-hour window or weekly cap cuts a session, the next session resumes from the last commit + brief, losing minutes not hours.
3. `/clear` between tasks; keep `CLAUDE.md` under ~200 lines with the contract conventions; one task per session.
4. Never babysit long runs (Rule Zero): kick off the script, verify on a sample, hand the full run to the scheduler, end the session.

**claude.ai Projects (one per paper), for judgment work at zero marginal cost:** spec/memo design (P1-T3/T5 channel A, E2-T5/T8b, DAX-W1), arbitration write-ups, all paper writing (P1-T9, E2-T12/T15, DAX-W10), monthly Research-mode lit sweeps (P1-T0, DAX event registry verification). Load each project's plan + 文献包 into Project knowledge once — caching means repeated reference doesn't re-burn limits.

**What Pro does *not* do:** bulk extraction, robustness grids, mechanical QA, anything a sentinel-fenced cheap model can do. Sonnet time spent on Haiku-grade work is the main way this architecture fails economically.

### L3 — Human gates (your 30 minutes)

The scheduler compiles a **daily digest** (`ops/digest/YYYY-MM-DD.md`): ① overnight batch results + validator verdicts; ② NEED_HUMAN / DECISION_NEEDED / UNKNOWN items across all three projects, each with a one-line ask and links; ③ budget line; ④ tomorrow's proposed prime-block agenda. You reply in `decisions.md`; the scheduler parses it and unblocks gates. All the manuals' mandatory human gates (P1's six 门, E2's arbitration points, DAX's PI sign-offs) are nodes with `human_gate: true` — agents queue *around* them (other branches keep running) but never through them.

---

## §3 Anti-breakdown workflow (the seven rules)

Mid-task agent failure has five root causes: session death (limits/crashes), context rot in long sessions, silent wrong output, dead-end retry loops, and idle-blocking on humans. One rule per cause, plus two economic guards:

1. **Rule Zero (session ≠ computation).** Stated in §1. Long work = checkpointed, idempotent scripts with resume-from-manifest; sessions only author and verify them.
2. **Atomize.** No agent task larger than one prime block (or one L1 batch call). The manuals' big tasks are already decomposed (T-numbers, W-numbers); `queue.yaml` splits any remaining task whose brief can't fit on one page.
3. **Files, not conversations** (all three manuals already mandate this — the scheduler *enforces* it): a task is complete only when its output passes the mechanical contract check. No agent output enters a downstream prompt except by file reference.
4. **Two-strike escalation ladder** (P1-R5, generalized): Qwen/GLM → DeepSeek → Claude Code Sonnet → human. Automatic on second failure; budget governor authorizes the step-up. This kills the "cheap model retry loop costs more than doing it right" trap.
5. **Sentinel fences on every batch** (§2 L0). Silent numerical error from cheap models is the residual risk the manuals all flag; sentinels convert it from undetectable to batch-voiding.
6. **Gate-aware parallelism.** When a branch hits a human gate, the scheduler switches the worker pool to another project's ready tasks — the portfolio never idles on you, and you never feel pressured to rubber-stamp.
7. **Budget governor with reserve** (§2 L0): 80% dispatch ceiling, 20% escalation reserve, daily visibility. Cost overruns are a breakdown mode too.

Cross-vendor independence (P1-R2, E2 附录A, DAX audit rules) survives the budget cut because it was always about *vendor families*, not price tiers: Anthropic (Pro) × DeepSeek × Kimi/Moonshot × Gemini-free × GLM/Qwen gives five families. Every dual-channel and red-team pairing in the patches keeps writer ≠ reviewer at the family level.

---

## §4 Master model assignment (portfolio view)

Task-level detail is in the three patches; the portfolio logic in one table:

| Work class | Assignment | Examples |
|---|---|---|
| Pipeline engineering, arbitration, escalations | **Claude Code (Sonnet, Pro blocks)** | P1-T2, E2-T3/T9a, DAX-W2/W5/W8, econlib |
| Spec/memo/writing/judgment | **claude.ai Projects (Pro)** | P1-T3/T5甲/T9, E2-T5/T8b/T12/T15, DAX-W1/W10 |
| Independent reasoning channel B (blind cross-check, red team lead) | **DeepSeek reasoning** | P1-T5乙/T10甲, E2-T8a/T13, DAX spec cross-reads |
| Batch/templated code + tests | **DeepSeek standard** | P1-T7, E2-T8c-py/T10, DAX robustness |
| Long-doc extraction + web-verified facts + lit monitoring | **Kimi** | P1-T1甲, E2-T1/T6b/T9b/T11b, monthly sweeps |
| Second code stack / bulk annotation / 中文 | **GLM / Qwen** | E2-T8c-R, DAX-A5, P1-T11 |
| Free cross-vendor channel + judgment-QA | **Gemini Flash free tier** | P1-T1乙/T10乙, E2-T14 residuals, DAX audit split |
| Contract/QA checking | **Deterministic validator (no LLM)** | replaces most of P1-T12, E2-T14, DAX-A14 |

**Withdrawn everywhere:** GPT-flagship API, Gemini-Pro API, Opus-class API. **The one exception that money must be found for separately:** DAX-W4 capability-panel runs — that spend is *measurement data*, not agent labor, cannot fit in ¥500/month, and is gated by the new W0.5 feasibility note (see DAX Amendment 4/5).

Budget envelope (ranges, per your instruction — no token accounting): DeepSeek ¥120–220, Kimi ¥80–150, GLM/Qwen ¥40–80, reserve ¥50–100, Gemini ¥0. Comfortably inside ¥300–500 in normal months; heavy months (E2 extraction waves, P1 robustness grid) lean on the reserve or shift batches across the month boundary — the scheduler's budget governor does this automatically.

---

## §5 Time-multiplexing the three projects

Running three full pipelines at once would thrash your prime blocks and your 30 minutes. The portfolio runs **two hot + one warm**, rotating on phase boundaries:

**Weeks 1–2 — Foundation sprint (everything else waits):**
- Claude Code blocks: `shared/runner` + validator + `econlib` skeleton (this is the highest-ROI code you will ever commission — three projects amortize it).
- Overnight L1: P1-T0 immediate crash check (Pro Research + Kimi), P1-T2a simulated power memo inputs, E2-T1/T6b extraction batches, DAX-W0.5 feasibility legwork.
- Human gates: P1-T2a verdict (continue or kill), DAX-W0.5 sign-off.

**Months 1–2 — Hot: E2 + DAX; Warm: P1.**
E2 races to `panel_daily` → T15 descriptive note (the portfolio's fastest publishable artifact and industry calling card). DAX runs W1 memo (Projects) + W2 data (Code blocks) toward Gate 1. P1, if T2a passed, runs only cheap tasks (T1 extraction overnight).

**Months 3–5 — Hot: DAX + P1; Warm: E2.**
DAX: W3–W5 → Gate 2 → **W10a public index release** (the portfolio's highest-value external milestone). P1: T2 WRDS pipeline + T4 replication through its week-6 kill-switch. E2: T15 circulation, T9a engine in background blocks, T11 scanner on cron.

**Months 6+ —** phase-driven rotation: whichever project is in a *spec/writing* phase consumes Projects sessions; whichever is in a *pipeline* phase consumes Code blocks; whichever is in a *batch* phase consumes L1 overnight. The three phases rarely collide because the scheduler stages briefs a day ahead — when they do, priority order is DAX > E2 > P1 (matching the evaluation: highest ceiling, then fastest external payoff, then cleanest-but-smallest).

Weekly rhythm: Mon–Thu two prime blocks/day on the hot projects; Fri one block for escalation backlog + weekly replication replay (`make replicate`, DAX-W11 pattern applied portfolio-wide); weekends are pure L1 batch + your digest replies only if you feel like it — the DAG guarantees Monday's briefs regardless.

---

## §6 Bootstrap checklist (what to actually do first)

1. Create the monorepo; paste the three manuals + patches into `docs/`.
2. First Claude Code block: `shared/runner/queue.yaml` schema + `runner.py` MVP (dispatch, retry, escalate, digest) + contract validator. Brief is one page; this is a one-to-two-block build.
3. Second block: `econlib` skeleton with the wild-bootstrap and RI wrappers + toy-data tests (they serve P1-T5, E2-T8, DAX-W8 alike).
4. Wire API keys (DeepSeek, Kimi, GLM/Qwen, Gemini) into the runner; run one sentinel-fenced dummy batch end-to-end overnight.
5. Encode Phase-1 tasks (§5 weeks 1–2 list) into `queue.yaml`; start the cron; read your first digest the next morning.
6. Set up three claude.ai Projects (one per paper) with plans + 文献包 in Project knowledge.

From day 3 onward the system is in steady state: overnight L1 shifts, daily prime blocks from prepared briefs, 30-minute digests, and gates that block branches instead of blocking the portfolio.
