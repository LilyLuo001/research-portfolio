# Macro-Event Chapter ("Refraction") · Multi-Agent Execution Playbook v1.0
### Companion to `MacroEvent_Chapter_Plan_v2_1_FINAL.md` — same format as Project_1.md (P1), E2_执行手册, DAX_Execution_Plan

> **[SUPERSEDED 2026-07-12]** The owner's `Refraction_执行手册_v1_0.md` (tasks **R0–R14**,
> inheriting the E2 manual's architecture and capability review) is now the authoritative
> execution manual for this chapter; its task IDs replace the ME-M* family below
> (mapping: M0→R0/R13 · M1→R1 · M2→R2 · M2a/M2b→R3 · prereg→R4 · M3→R5 · M5→R6 ·
> M6/spines→R7 · M7→R8 · M13→R9 · M14→R10 · M9→R11 · M10→R12 · M12→R14).
> This file is kept only as the English L0–L3 layer-mapping reference; where the two
> conflict, the 执行手册 wins. Repo scaffolding for R0–R14 lives in `refraction/` and
> `ops/` (queue nodes REFR-*).
>
> **Framing correction (owner, 2026-07-12):** this file's "standby/backup for E2" language
> is obsolete. The four projects (P1, E2, DAX, Refraction) are strictly parallel,
> independent, and of equal importance; Refraction is not a hedge for E2, and
> GATE-E2-VERDICT is purely a workflow/scheduling gate, not a fallback trigger.

> Model assignments follow the **v1.1 budget regime** (see P1_修订补丁_v1_1.md §5 and
> Agent_Architecture_24x7.md §4): Anthropic only via Pro subscription (Claude Code + claude.ai
> Projects/Research), no non-Anthropic flagship APIs; cross-vendor independence (R2) carried by
> cheap tiers (DeepSeek / Kimi / GLM / Qwen + Gemini free). Escalation ladder tops out at a
> Claude Code prime block. Re-check assignments quarterly with the three standard probe tasks.
>
> **Runtime layers.** Every task is decomposed across the portfolio's four layers — L0
> deterministic backbone (scripts/cron, runs everything long), L1 automated cheap workers
> (the overnight shift, no human in the loop), L2 Claude Pro seats (human-driven prime
> blocks), L3 human gates — in §2; §7 gives the ready-to-merge `queue.yaml` nodes and §8 the
> `ops/l1/` worker specs with sentinel fences and the L0 wiring checklist.
>
> **Standby protocol.** This is a **dormant task family** (`refraction/` project dir). Tasks
> M0–M4 + GATE-0-FREEZE run now, to "Gate-0-passed, spec-frozen, pre-registered" standby.
> M5 onward are blocked in `queue.yaml` behind the human gate **GATE-E2-VERDICT** (either
> verdict unblocks; the verdict only sets priority: E2 rejected → this chapter takes E2's seat
> slot; E2 approved → fourth-paper cadence on the float seat). Carrying cost at standby ≈ 0:
> no intraday pipeline, no live data feeds, only the monthly M0 monitor.

---

## §1 The five meta-rules

R1–R5 of Project_1.md §1 apply verbatim (LLM is not a source of facts; dual-channel on
high-hallucination tasks; schema contracts; don't-know→stop; expensive gates, cheap runs).
Every prompt below opens with the C0-ME context pack (§3), which restates them.

Chapter-specific additions:

- **R6 (framing gate).** The claim language ("basket-specific refraction" vs. the weaker
  "wrapper-induced beta compression") is decided by the Gate-0 basket-distinctiveness check
  and frozen in the pre-registration — no agent may strengthen the framing after outcomes
  exist. The writing task (M9) receives the frozen language as an input, not a choice.
- **R7 (pre-outcome archive).** `gate0_diagnostics.json` and `power_bar.json` are written and
  committed BEFORE any post-conversion outcome regression runs. The M5 runner refuses to
  execute if their commit timestamps do not predate the first outcomes run (same guard
  pattern as DAX `v1.0-preregistered`).

---

## §2 Layer map — every task decomposed across the L0–L3 runtime (queue.yaml vocabulary)

Layer semantics (Agent_Architecture_24x7.md §2):

- **L0 — deterministic backbone** (`worker: script`, cron): free, truly 24/7, no LLM. Runs
  every long computation (Rule Zero: L2 authors scripts, L0 runs them), all mechanical
  contract validation, channel diffs, sentinel voiding, the R7 pre-outcome guard, and the
  monthly re-arm of the monitor.
- **L1 — automated cheap workers** (`worker: deepseek | deepseek_r | kimi | glm | qwen |
  gemini_free`): the overnight shift — highly automated, dispatched by `l1_driver.py` from
  `ops/l1/<task_id>.yaml` specs, no human in the loop, trustworthy **only inside sentinel
  fences**. Carries all extraction, batch grids, unit tests, figures, every channel-B duty,
  red-team readers, 中文材料.
- **L2 — Claude Pro seats** (`worker: code_pro | project_pro`): scarce, human-driven,
  scheduled prime blocks from prepared briefs (`ops/briefs/`). Reserved for pipeline
  authorship, channel-甲 spec design, arbitration of channel diffs, escalations, writing.
- **L3 — human gates** (`human_gate: true`): owner/advisor decisions via daily digest →
  `ops/decisions.md`. Branches park at gates; the portfolio keeps moving.

Global two-strike escalation ladder (arch §3): qwen/glm → deepseek → code_pro (Claude Code)
→ human (L3); automatic on second failure; budget governor authorizes each step-up.

| Task | L0 (deterministic) | L1 (automated cheap worker) | L2 (Pro seat, human-driven) | L3 (human gate) |
|---|---|---|---|---|
| ME-M0 blocking sweep | machine-diff of the two channels | **kimi** `$web_search` = channel B | **project_pro** (claude.ai Research, seat C) = channel A | positioning re-check only if ALERT fires |
| ME-M0 monthly monitor | cron re-arms spec on the 1st (delete `ops/l1/out/ME-M0-monitor.json`) | **kimi**, sentinel-fenced, overnight | — (escalation target only) | reads ALERT lines in digest |
| ME-M1 macro events | channel diff; contract check on merge | **kimi** 甲 + **gemini_free** 乙 (independent sentinel fences) | **code_pro** (seat C) arbitrates disagreement rows only | spot-check 10% of H rows, all M/L |
| ME-GATE-consensus | — | — | — | CPI/NFP consensus license (`NEED_HUMAN`); FOMC lane never blocks |
| ME-M2 panel + betas + lever | scheduler runs the checkpointed build overnight; lineage JSON per stage | **deepseek** writes unit tests from §5 schemas only (never sees the implementation) | **code_pro** (seat C) authors pipeline modules, ≤1 prime block each; escalate Opus/Fable on the LOO-beta module | — |
| ME-M2a Gate-0 diagnostics | runs the shrinkage sweep; deterministic asserts | — | authored in the tail of the M2 block | thresholds `[VERIFY-IN-GATE-0]` supplied via decisions.md; owner reads gate0_memo |
| ME-M2b power sim + exit-D bar | runs seeded simulation; commits power_bar.json pre-outcome (R7) | — | **code_pro** re-parameterizes P1 T2a | reads power memo |
| ME-M3 estimation blueprint | machine-diff of the two blueprints | **deepseek_r** = channel 乙 | **project_pro** (seat C Project session) = channel 甲 | arbitrates EVERY divergence (DECISION_NEEDED) — mandatory |
| ME-M4 pre-trend triple | runs the three exhibits from templates | — | **code_pro** adapts P1 T5 event-study templates | reads GATE0-RISK flags |
| ME-GATE-0 + ME-GATE-prereg | registration-URL commit + tag enforced by R7 guard | — | **project_pro** drafts OSF/AEA text from frozen artifacts only | owner + advisor sign; human submits registration |
| GATE-E2-VERDICT | runner holds ME-M5+ un-READY until verdict recorded | — | — | owner records E2 verdict (either way unblocks; sets priority) |
| ME-M5 main estimation | R7 guard refuses to run if diagnostics/power-bar/prereg commits are missing; runs estimation | **gemini_free** results-blind code audit (blueprint↔code line check; red-flag result-driven branches) | **code_pro** implements the frozen blueprint | — |
| ME-M6 wedge + anchoring | runs; enforces plot-before-interpret by file-order check | — | **code_pro** re-targets P1 T3/T6 machinery | — |
| ME-M7 robustness grid | overnight dispatch; 2 sentinel rows auto-void batch on mismatch | **deepseek** (备 **qwen**), templated single-dimension variants | — (two-strike escalation only) | — |
| ME-M8 figures/tables | numbers-from-disk lint | **deepseek** flash tier | — | — |
| ME-M9 writing | numbers→file map trace check | **deepseek_r** independent polish pass | **project_pro** (seat E writing float), one section per session; frozen R6 language as input | numbers-map acceptance |
| ME-M10 red team ×2 | attack-checklist coverage check | **deepseek_r** 裁判甲 + **gemini_free** 裁判乙, cold second round, never Anthropic | **project_pro** drafts point-by-point responses | approves each round's response plan |
| ME-M11 中文材料 | — | **qwen** | — | — |
| ME-M12 gatekeeping | `contracts.py` validates every §5 schema on merge | **gemini_free** judgment checklist (locator audit, red-line scan) | — | the six gates (§5) |
| ME-M13 basket files (opt) | contract check | **kimi** 甲 + **gemini_free** 乙 | — | coverage/`NEED_HUMAN` gate first |
| ME-M14 TAQ pilot (gated) | runs pilot script; pass/fail computed mechanically | — | **code_pro** authors the gated module | promote/drop H1′–H5′ decision |

Reading the table by layer: **L1 owns** the monitor, M1, M7, M8, M10, M11, M13, every
channel-B and audit seat, and unit tests — the fully automated share, run overnight on the
Chinese-model pool + Gemini free. **L2 owns** authorship (M2/M2a/M2b/M4/M5/M6/M14 as
script-writers, never runners), channel-甲 spec work (M0/M3), and writing (M9). **L0 owns**
every actual long run, every diff, every guard, every contract check. **L3 owns** exactly
the six gates plus the two standby gates — nothing else needs a human.

---

## §3 C0-ME context pack (paste at the top of every prompt)

```
[CONTEXT PACK C0-ME v1.0 — Macro-Event "Refraction" chapter]
You are one execution unit in a multi-agent pipeline. The attached
MacroEvent_Chapter_Plan_v2_1_FINAL.md is the single source of truth; if your
task conflicts with it, follow the plan and report the conflict.

Glossary:
- Conversion / ConvExp_i,e / wave: as in P1 (frozen contract, conv_exposure.parquet).
- S_a: measured surprise of scheduled macro announcement a (FOMC/CPI/NFP).
- β_i: announcement-REGIME beta — estimated only from pre-conversion
  announcement-day responses, Vasicek-shrunk toward a characteristics prior.
- β_b^LOO(i): leave-one-out basket response of the converting fund's portfolio.
- L_i = β_b^LOO(i) − β_i: refraction lever; decomposition L = L_mkt + L_tilt,
  L_mkt = (1 − β_i), L_tilt = (β_b^LOO − 1).
- F'λ_b: basket factor tilt — the basket's non-market announcement response.
- γ (γ_mkt, γ_tilt, γ_fac): coefficient(s) on Post × ConvExp × (lever · S_a).
- W_{i,a}: fitted basket-induced wedge; D_b = |β_b^LOO − 1| basket distinctiveness.
- Framing gate: if Gate-0 distinctiveness fails, all claims are pre-committed to
  "wrapper-induced beta compression"; "basket-specific refraction" language is banned.

Hard rules (violating any one = task failure):
1. No dates, coefficients, AUM, event lists, or citations from memory; every fact
   carries a source locator (URL/accession/WRDS table+query) or comes from code
   executed on real data.
2. Output files follow the frozen schemas in §5 exactly; never rename a column.
3. Insufficient information → output NEED_HUMAN: <reason>; never guess-fill.
4. Cite only from the literature pack (Plan Appendix A verified list); new
   citations → CITE_REQUEST.
5. No specification search. Report the first run per the blueprint. Outcome data
   post-conversion may not be opened before gate0_diagnostics.json and
   power_bar.json are committed (R7).
6. End every deliverable with a PASS/FAIL self-check list.
```

---

## §4 Execution prompts

### M0 | Collision monitor + channel-B citation sweep — claude.ai Research (Pro) + Kimi

Runs NOW (before positioning is final), then monthly at standby.

```
[C0-ME]
Task: two-part sweep.
Part 1 (immediate, blocking): verify current status of Marta–Riva
("Do ETFs Increase Comovement?" SSRN 4079302 or successor titles, ETF
replication-technique switch). Report: latest version date, publication status,
outcome variables, whether any version conditions on macro announcements or
uses a stock-level signed lever. Hair trigger: overlap ≥ 40% with the
refraction design → ALERT + verbatim quotes of the overlapping passages.
Also verify the [VERIFY-CHANNEL-B] entries of Plan Appendix A (ATT QE 2021;
Bodilsen JBF 2021; Brogaard–Heath–Huang JFQA 2025; Greenwood–Thesmar JFE 2011;
Dannhauser–Hoseinzade RFS 2021; Todorov RoF 2023; Chen–Jiang FR 2024; BSW JFE
2005; Boyer JF 2011; Staer 2017; Liao et al. IRFA 2022): working link + venue
+ one-line result each; unverifiable → mark DROP-CANDIDATE, do not invent.
Part 2 (monthly): SSRN/NBER/arXiv q-fin keywords [ETF basket comovement
announcement; conversion comovement; announcement day beta ETF; ETF replication
switch comovement; creation basket transmission; passive macro news
cross-section]; track Da/Shive, Greenwood, Marta–Riva, Brogaard–Heath–Huang,
JFR-2025 authors, Sammon, Ernst, Saglam–Tuzun–Wermers. ALERT ≥ 60% overlap
(Marta–Riva: 40%). Every entry needs a working link; dead links are deleted.
Self-check: all links reachable? Marta–Riva status stated with version date?
```

### M1 | Macro calendar + surprise series — dual channel (Kimi 甲 / Gemini Flash 乙), arbitration Claude Code

```
[C0-ME]
Task: build the scheduled-announcement event table, 2017-01–2026-06.
Sources (only these): SF Fed USMPD (FOMC surprises, public download); official
FOMC calendar (federalreserve.gov); BLS release schedules (CPI, Employment
Situation); consensus expectations ONLY if the owner has confirmed the license
(else fill surprise_norm = NA for CPI/NFP and set confidence = M; the FOMC
series must be complete regardless).
Output schema (macro_events_通道X.csv): event_id | type(FOMC/CPI/NFP) |
release_date | release_time_ET | surprise_raw | surprise_norm | surprise_source
| source_url | confidence(H/M/L)
Rules: every row's every field traceable to a source URL; scheduled-but-
cancelled or rescheduled releases flagged, not dropped; no imputation of
missing consensus. Escalation: two sources disagree on a release timestamp →
NEED_HUMAN with both URLs.
Self-check: FOMC count ≈ 8/yr (list exceptions with URL); CPI/NFP monthly
continuity; zero rows from memory.
```

Arbitration (Claude Code): machine-diff the two channels; work only disagreement rows back to
sources; output `macro_events.csv` + adjudication log. Human spot-check: 10% of H, all M/L.

### M2 | Announcement panel + announcement-regime betas + lever — Claude Code (the main build, ~one seat-week)

```
[C0-ME]
Task: CRSP-only daily pipeline (no TAQ). Inputs: macro_events.csv,
conv_exposure.parquet + events_merged.csv (P1 frozen), CRSP daily incl. open
prices, P1 control set (fund flows, FIT, Russell constituents, 13F/N-PORT).
Steps:
1. announcement_panel.parquet: for every stock × event —
   r_c2c (prev close→close), r_c2o (close→open), r_o2c (open→close), and
   cumulative horizon returns h ∈ {+1d,+5d,+20d,+60d}; controls joined.
2. Announcement-regime betas: for each stock, regress announcement-day returns
   on S_a over PRE-conversion events only; Vasicek-shrink toward a
   characteristics-implied prior (size/BM/industry cells). Store raw AND shrunk
   β̂ with SEs and the per-stock count of usable pre-period announcements.
3. β_b^LOO(i): converting-fund portfolio announcement response, leave-one-out,
   from pre-period events; per wave.
4. Lever: L, L_mkt, L_tilt, D_b, and the basket factor-tilt response (basket
   announcement-day returns orthogonalized to the market response).
5. Output betas_lever.parquet (schema §5) + diagnostics memo: distributions of
   L̂, D_b, SE(β̂); corr(L, ConvExp); coverage counts.
Rules: every step writes asserts (row counts, duplicate keys, value ranges);
all intermediate tables on disk with lineage JSON; no interpolation of missing
prices; funds whose N-PORT vs CRSP-MF holdings diverge >10% inherit P1's
NEED_HUMAN list. The shrinkage weight is a PARAMETER (M2a sweeps it), never
hard-coded.
Unit tests: written by DeepSeek from this prompt + §5 schemas only (no access
to implementation), synthetic fixtures with hand-computed betas and levers.
```

### M2a | Gate-0 diagnostics — Claude Code (weeks 1–2; decisive)

```
[C0-ME]
Task: the two coupled Gate-0 checks, as pure functions of M2 outputs.
1. Shrinkage-intensity sweep: for shrinkage weight w ∈ {0, .1, …, 1}, compute
   SD(L̂) among ConvExp ≥ 0.5% stocks, |corr(L̂, ConvExp)|, median pre-period
   announcement count, share of treated names with SE(β̂) ≪ SD(L̂) (ratio ≤ 1/3).
   Pass = a non-empty, non-knife-edge window of w where simultaneously
   SD(L̂) ≥ 0.25, |corr| ≤ 0.3, median count ≥ 30, share ≥ 70%. Report the
   window; recommend the main-spec w from its interior. Empty window → output
   GATE0-FAIL-JOINT and the portfolio-level fallback diagnostics.
2. Basket distinctiveness: distribution of D_b and factor-tilt announcement
   responses across waves; treatment mass (Σ ConvExp) in waves with D_b ≥ 0.1.
   Below the pre-set mass line → output FRAMING-GATE-BINDS.
Output: gate0_diagnostics.json + gate0_memo.md (owner-readable, verdict per
check, no hedging). Committed BEFORE any outcome regression (R7).
Thresholds marked [VERIFY-IN-GATE-0] in the plan are inputs from the owner via
ops/decisions.md — do not choose them yourself; missing → NEED_HUMAN.
```

### M2b | Power simulation + exit-D bar — Claude Code (reuse P1 T2a)

```
[C0-ME]
Task: re-parameterize the P1 T2a simulation to the joint empirical
(ConvExp, L, S) distribution from M2, wave-clustered errors. Compute MDE for
γ pooled, γ_tilt, γ_fac at the frozen shrinkage weight and at the window
endpoints. Pass = MDE(γ) ≤ 0.5σ of announcement responses. Additionally
compute and archive the EXIT-D POWER BAR: the γ magnitude implied by the
Da–Shive / Greenwood comovement correlations (translation formula and source
page cites from the literature pack; ambiguity → NEED_HUMAN), and whether the
design detects it at 80% power. Output power_memo.md + power_bar.json,
committed pre-outcome (R7). Seeds fixed; all priors carry locators.
```

### M3 | Estimation blueprint — dual channel (claude.ai Project 甲 / DeepSeek reasoning 乙), diff, human arbitration

```
[C0-ME]
Task (each channel independently): translate Plan §6 into an estimation
blueprint precise enough to code without judgment calls:
- the main equation with ALL lower-order terms (b₁–b₄) and the γ decomposition
  (γ_mkt, γ_tilt, γ_fac); stacked clean-control construction per wave (P1 T5
  rules); CS/SA adaptations for continuous treatment;
- the beta-measurement battery: EIV instrument (independent-window
  unconditional beta), randomized-L placebo, portfolio-level replication
  design (L-quintile portfolios) for EVERY main table;
- the pre-trend triple and placebo-in-time, with exact windows;
- the four-way inference suite: two-way cluster dimensions; wild bootstrap
  null; RI-1 permute conversion dates; RI-2 permute announcement labels vs
  matched non-announcement days AND permute L within treated set; permutation
  counts;
- the frozen heterogeneity set (Plan §3 H4), interactions capped at triple,
  Romano–Wolf family definitions;
- FIT and saturation controls (T4/T5 threats), incl.
  Post × pre_etf_ownership × (L^Russell · S) construction.
Flag every point where the plan admits two readings as DECISION_NEEDED with a
recommendation. Do not resolve them.
```

Diff the two blueprints; every divergence = the econometrically dangerous points → NEED_HUMAN
(owner/advisor arbitration, written into ops/decisions.md). Frozen blueprint feeds M5 and the
pre-registration.

### GATE-0-FREEZE | Pre-registration — human gate

Owner + advisor sign off on: Gate-0 verdicts (M2a/M2b), the arbitrated blueprint (M3), the
frozen shrinkage weight and its window, the heterogeneity set, the triangulated verdict rules,
the full exit matrix incl. framing gate and exit-D bar, pre-period placebo results (M4).
Claude drafts the OSF/AEA registration text from those artifacts only; human submits;
the registration URL + timestamp is committed to the repo. **No M5+ task becomes READY
before this commit exists** (and GATE-E2-VERDICT for execution priority).

### M4 | Pre-trend triple + placebo-in-time — Claude Code

```
[C0-ME]
Task: three exhibits from M2 outputs + P1 T5 event-study templates:
(a) event-time γ̂ over ≥8 pre-quarters of announcements; (b) treated vs matched
trends in announcement-regime betas pre-conversion; (c) full design
re-estimated on 2017–2020 with fake conversion dates (γ must be zero).
Output: pretrend_results/ (figures data + coefficient files). Interpretation
sentence per exhibit ONLY after the figure file is written (plot-before-
interpret). Any non-flat exhibit → report as-is; do not re-specify (R5/no
spec search); flag GATE0-RISK for the owner.
```

### M5 | Main estimation — Claude Code; audit Gemini Flash free

```
[C0-ME]
Task: implement the frozen M3 blueprint. One module per estimand; seeds fixed;
runner refuses to start unless gate0_diagnostics.json, power_bar.json, and the
pre-registration commit predate this run (R7 guard, DAX pattern). Output
refraction_results/ (coefficient tables: estimator × {γ_mkt, γ_tilt, γ_fac,
pooled γ, b₁–b₄} × SE-suite × N) + event-study figure data.
Audit prompt (Gemini, read-only, results-blind): line-check code against
blueprint; red-flag any branch conditioned on a result value.
```

### M6 | Wedge fingerprint + fundamental anchoring — Claude Code

```
[C0-ME]
Task: (a) construct W_{i,a} from M5 estimates; cumulative wedge paths at
{0,+1d,+5d,+20d,+60d}, treated−control, bootstrap bands — P1 T6 visual grammar,
horizon in days; (b) wedge-reversal long-short portfolio monthly return series
+ alpha table; (c) anchoring regressions: W → next-quarter SUE and analyst
revisions (P1 T3 IBES machinery re-targeted, same variable definitions).
Wedge plots are generated BEFORE any H2 verdict sentence; every claim in the
interpretation must point to an identifiable feature of a disk file
(fingerprint_*.csv convention). The triangulated verdict table (reversal ∧
discipline ∧ anchoring) is filled mechanically from the three legs; the exit
classification (A/B/B′/C/D per Plan §10) follows the pre-registered rules —
you do not get to argue with the table.
```

### M7 | Robustness grid — DeepSeek V4 (备 Qwen3.7 Plus)

```
[C0-ME]
Task: templated. Input: main-spec code (read-only) + robustness_grid.csv
(each row = one variant: beta construction | estimator | inference | sample
filter | surprise measure | lever variant). For each row: copy main spec,
change ONLY the specified dimension, run, write coefficients/SE/N back to
robustness_results.csv. Two sentinel rows duplicate the main spec exactly —
any mismatch voids the whole batch. Errors → ERROR + traceback summary, never
skipped, never interpreted.
Self-check: results rows = grid rows; auto-diff proves single-dimension change.
```

Grid contents: Plan §8 items 1–8 (DFA in/out; three estimators; four-way inference; the beta
battery incl. portfolio replication at window endpoints; surprise/sign/type/regime splits;
exclusions; all placebos; Romano–Wolf within spine and heterogeneity families).

### M8 | Figures/tables — DeepSeek V4 Flash or Haiku 4.5

P1 T8 verbatim: journal-grade matplotlib, black-white friendly; every number read from disk;
LaTeX booktabs; the compression exhibit (responses vs β_i·S_a, pre/post, within announcement)
is the headline figure.

### M9 | Writing — claude.ai Project (Pro), section per session; polish DeepSeek

P1 T9 rules verbatim (numbers→file:cell map; citations only from the verified pack;
CITE_REQUEST for new ones; report insignificant results; no "first ever" claims beyond the
plan's boundary tables) **plus R6**: the Intro and abstract use the claim language frozen at
GATE-0 (refraction vs. beta-compression); the framing-gate paragraph and the pre-registration
URL appear in the introduction, not a footnote; the effective-cluster honesty sentence (waves,
not announcement-days, are the treatment shocks) appears in the text of §Inference.

### M10 | Red team — DeepSeek reasoning 甲 + Gemini free 乙, two cold rounds, never Anthropic

P1 T10 protocol + structured attack checklist forced into the prompt: DFA single family;
basket≈market / beta mean-reversion (FAQ 9); lever measurement error; FIT/flows (FAQ 7);
creation-basket sampling; few-cluster inference; estimand vs. claim language match against the
registration; exit-D power bar honesty. Writer (Claude) drafts responses; second round cold.

### M11 | Chinese materials — Qwen3.7 Max

开题/预答辩/导师纪要 from the English draft; same numbers-from-disk rule.

### M12 | Gatekeeping — deterministic + cheap tier

`contracts.py` validates every §5 schema on merge; cheap-tier checklist audits: source
locators on 5 random facts, schema conformity, downstream input satisfaction, red-line scan
(memory numbers, spec search, selective reporting). Human at the six gates (§5).

### M13 (optional) | Creation-basket extraction — Kimi + Gemini dual channel

Blocked on `NEED_HUMAN: ETF Global / issuer-file coverage confirmation`. Schema:
basket_daily.csv: etf_ticker | date | permno | in_creation_basket | weight | source_url.
Feeds H4 inclusion heterogeneity only (enhancement; floor-design rule).

### M14 (gated) | TAQ pilot → H1′/H5′ — Claude Code

Pilot: 30 treated + 30 control × 20 announcement days; pass ≥70% usable small-cap coverage →
build the intraday module (speed shares 5/15/30/60min; announcement-window spreads/depth/price
impact). Fail → drop enhancements; core chapter unaffected. Never on the critical path.

---

## §5 Schema contracts and continuity matrix

**File contracts (columns frozen; changes need owner sign-off):**

| File | Producer | Consumers | Key columns |
|---|---|---|---|
| macro_events.csv | M1 | M2, M2b, M5 | event_id, type, release_date, release_time_ET, surprise_norm, surprise_source, source_url |
| announcement_panel.parquet | M2 | M4, M5, M6, M7 | permno, event_id, r_c2c, r_c2o, r_o2c, r_h1d, r_h5d, r_h20d, r_h60d |
| betas_lever.parquet | M2 | M2a, M2b, M4, M5, M7 | permno, wave_id, beta_ann_raw, beta_ann_shrunk, se_beta, n_pre_events, beta_b_loo, L, L_mkt, L_tilt, factor_tilt_resp, D_b |
| gate0_diagnostics.json | M2a | GATE-0, M5 guard | window_lo, window_hi, chosen_w, sd_L, corr_L_convexp, distinctiveness_mass, framing_gate_binds |
| power_bar.json | M2b | GATE-0, M9 (exit D), M5 guard | mde_gamma, mde_gamma_tilt, mde_gamma_fac, exitD_bar_gamma, exitD_powered |
| pretrend_results/ | M4 | GATE-0, M9 | exhibit × coefficients × CI |
| refraction_results/ | M5 | M6, M7, M8, M9 | estimator × {γ_mkt, γ_tilt, γ_fac, γ_pooled, b1–b4} × SE_suite × N |
| fingerprint_*.csv, anchoring_results.csv | M6 | M8, M9 | horizon × wedge × CI; anchoring coefficients |
| robustness_results.csv | M7 | M8, M9, M10 | grid_id × coefficients (2 sentinel rows) |
| Paper draft + numbers→file map | M9 | M10, M11 | — |
| (reused, read-only) events_merged.csv, conv_exposure.parquet, IBES outcome tables | P1 T1/T2/T3 | M2, M2b, M6 | P1 frozen contracts — never edited by this family |

**Continuity self-audit:** every downstream input has exactly one producer; the only
cross-project inputs are P1's frozen T1/T2/T3 outputs, consumed read-only (no write
collision with seat C). The three highest-hallucination nodes and their gates: M1 (event
facts) → dual channel + locators + human spot-check; M3 (econometric readings) →
dual channel + DECISION_NEEDED forced to human; M9 (numbers in prose) → numbers→file map +
M12 trace-back audit. Independence: tests (DeepSeek) never see implementations (Claude);
red team non-Anthropic; extraction dual-channel cross-vendor. No conclusion passes through
a single model family.

**The six human gates:** (1) M1 spot-check; (2) Gate-0 verdicts + threshold inputs
(ops/decisions.md); (3) M3 DECISION_NEEDED arbitration; (4) GATE-0-FREEZE pre-registration
sign-off; (5) M9 numbers-map acceptance; (6) each M10 round's response plan.
Plus the standby gate **GATE-E2-VERDICT** controlling promotion of M5+.

---

## §6 Cost and cadence

- **Now (standby build, weeks 1–5):** M0 (blocking part) → M1 ∥ M2 → M2a/M2b → M3 ∥ M4 →
  GATE-0-FREEZE. Incremental cost ≈ one Claude Code seat-week (M2) + 2–3 seat-days
  (M2a/M2b/M4) + cheap-tier extraction; aligns with Plan §9's five-week table. The two
  decisive unknowns (lever dispersion; estimability) resolve in weeks 1–2 from data P1
  already holds — schedule M2/M2a first, before M1 completes (FOMC-only S_a suffices for
  the sweep).
- **At standby:** monthly M0 only.
- **On promotion (E2 verdict):** M5–M6 ≈ M2–M6 of the plan timeline (heaviest reuse of P1
  T5–T8 templates); M7–M8 cheap tier; M9–M10 months 7–11; SSRN by M11. Frontier load
  concentrates where it should (M3 spec, M9 writing, escalations) — everything else is
  cheap tier or deterministic, per R5.
- **Race clock:** the Marta–Riva hair trigger (M0) is the one external event that re-opens
  positioning; if it fires, re-run the Plan §I.3 boundary table before any further spend.

---

## §7 queue.yaml task nodes (ready to merge — seat D action)

Registration prerequisites (one seat-D block, task `SH-me-register`): add `me/` to seat C's
`owned_paths` in ops/accounts.yaml; add the six new contract YAMLs to ops/contracts/
(`macro_events`, `announcement_panel`, `betas_lever`, `gate0_diagnostics`, `power_bar`,
`fingerprint` — schemas from §5; ME-M7 reuses the existing `robustness_results` contract);
merge the nodes below. Project key `me` = the plan's "refraction" family.

```yaml
  # ---- ME standby build (runs NOW): M0–M4 + gates. owner_account C = P1 seat. ----
  - id: SH-me-register
    project: shared
    owner_account: D
    worker: code_pro
    depends_on: []
    inputs: [docs/MacroEvent_Execution_Playbook_v1.md]
    output_contract: null
    human_gate: false
    max_attempts: 2
    notes: "Register me/ family: accounts.yaml owned_paths, 6 contract YAMLs, R7 guard script (DAX outcomes-guard pattern), monthly re-arm cron line."

  - id: ME-M0-position
    project: me
    owner_account: C
    worker: project_pro
    depends_on: [SH-me-register]
    inputs: [docs/MacroEvent_Chapter_Plan_v2_1_FINAL.md]
    output_contract: null
    human_gate: false
    channel_a: true
    max_attempts: 2
    notes: "BLOCKING sweep: Marta–Riva status (40% hair trigger) + [VERIFY-CHANNEL-B] citations. claude.ai Research mode."

  - id: ME-M0-position-B
    project: me
    owner_account: null
    worker: kimi
    depends_on: [SH-me-register]
    inputs: []
    output_contract: null
    human_gate: false
    channel_of: ME-M0-position
    max_attempts: 2
    notes: "Channel B union sweep. NOTE: kimi benched for retrieval batches (Wave-0) — if bench holds, re-route to gemini_free or run in Anthropic lane like P1-T0-crash-A."

  - id: ME-M0-monitor
    project: me
    owner_account: null
    worker: kimi
    depends_on: [ME-M0-position]
    inputs: []
    output_contract: null
    human_gate: false
    max_attempts: 2
    notes: "Monthly at standby (P1-T0-monitor pattern; same kimi-bench caveat). The ONLY task that runs while family is dormant."

  - id: ME-M1-events
    project: me
    owner_account: null
    worker: kimi
    depends_on: [SH-me-register]
    inputs: []
    output_contract: null
    human_gate: false
    channel_a: true
    max_attempts: 2
    notes: "Macro calendar + surprises, channel 甲 (USMPD/FOMC/BLS sources only)."

  - id: ME-M1-events-B
    project: me
    owner_account: null
    worker: gemini_free
    depends_on: [SH-me-register]
    inputs: []
    output_contract: null
    human_gate: false
    channel_of: ME-M1-events
    max_attempts: 2
    notes: "Channel 乙, independent sentinel fence."

  - id: ME-M1-arb
    project: me
    owner_account: C
    worker: code_pro
    depends_on: [ME-M1-events, ME-M1-events-B]
    inputs: [ops/l1/out/ME-M1-events.json, ops/l1/out/ME-M1-events-B.json]
    output_contract: macro_events
    human_gate: false
    max_attempts: 2
    notes: "Diff arbitration on disagreement rows only → me/macro_events.csv. Human spot-check 10% H, all M/L."

  - id: ME-GATE-consensus
    project: me
    owner_account: null
    worker: script
    depends_on: []
    inputs: []
    output_contract: null
    human_gate: true
    max_attempts: 1
    notes: "CPI/NFP consensus license decision (Bloomberg at BU vs WRDS alt). Blocks only surprise_norm for CPI/NFP; FOMC lane proceeds."

  - id: ME-M2-panel
    project: me
    owner_account: C
    worker: code_pro
    depends_on: [ME-M1-arb]
    inputs: [me/macro_events.csv, p1/conv_exposure.parquet, p1/events_merged.csv]
    output_contract: announcement_panel
    human_gate: false
    max_attempts: 2
    notes: "Main build (~1 seat-week, Rule Zero: author scripts, scheduler runs). Also emits betas_lever contract. DeepSeek writes tests from schemas only."

  - id: ME-M2a-gate0diag
    project: me
    owner_account: null
    worker: script
    depends_on: [ME-M2-panel, ME-GATE-g0thresholds]
    inputs: [me/betas_lever.parquet, ops/decisions.md]
    output_contract: gate0_diagnostics
    human_gate: false
    max_attempts: 3
    notes: "Deterministic shrinkage sweep + distinctiveness. R7: must be committed pre-outcome."

  - id: ME-GATE-g0thresholds
    project: me
    owner_account: null
    worker: script
    depends_on: [ME-M2-panel]
    inputs: [me/gate0_memo_inputs.md]
    output_contract: null
    human_gate: true
    max_attempts: 1
    notes: "Owner supplies the [VERIFY-IN-GATE-0] thresholds (SD(L) line, D_b mass line) in decisions.md — never chosen by an agent."

  - id: ME-M2b-power
    project: me
    owner_account: C
    worker: code_pro
    depends_on: [ME-M2a-gate0diag]
    inputs: [me/betas_lever.parquet, me/macro_events.csv, p1/t2a_power_sim.py]
    output_contract: power_bar
    human_gate: false
    max_attempts: 2
    notes: "P1 T2a re-parameterized; archives exit-D power bar pre-outcome (R7)."

  - id: ME-M3-blueprint
    project: me
    owner_account: C
    worker: project_pro
    depends_on: [ME-M2a-gate0diag]
    inputs: [docs/MacroEvent_Chapter_Plan_v2_1_FINAL.md, me/gate0_diagnostics.json]
    output_contract: null
    human_gate: false
    channel_a: true
    max_attempts: 2
    notes: "Estimation blueprint channel 甲 (claude.ai Project)."

  - id: ME-M3-blueprint-B
    project: me
    owner_account: null
    worker: deepseek_r
    depends_on: [ME-M2a-gate0diag]
    inputs: [docs/MacroEvent_Chapter_Plan_v2_1_FINAL.md, me/gate0_diagnostics.json]
    output_contract: null
    human_gate: false
    channel_of: ME-M3-blueprint
    max_attempts: 2
    notes: "Channel 乙 (cross-family per R2)."

  - id: ME-GATE-m3arb
    project: me
    owner_account: null
    worker: script
    depends_on: [ME-M3-blueprint, ME-M3-blueprint-B]
    inputs: [me/blueprint_diff.md]
    output_contract: null
    human_gate: true
    max_attempts: 1
    notes: "Every blueprint divergence = DECISION_NEEDED → owner/advisor arbitration in decisions.md. Frozen blueprint feeds M5 + prereg."

  - id: ME-M4-pretrends
    project: me
    owner_account: C
    worker: code_pro
    depends_on: [ME-M2-panel]
    inputs: [me/announcement_panel.parquet, me/betas_lever.parquet]
    output_contract: null
    human_gate: false
    max_attempts: 2
    notes: "Pre-trend triple + placebo-in-time from P1 T5 templates. Non-flat → GATE0-RISK, never re-specified."

  - id: ME-GATE-0
    project: me
    owner_account: null
    worker: script
    depends_on: [ME-M2a-gate0diag, ME-M2b-power, ME-M4-pretrends, ME-GATE-m3arb]
    inputs: [me/gate0_memo.md, me/power_memo.md, me/pretrend_results]
    output_contract: null
    human_gate: true
    max_attempts: 1
    notes: "Owner+advisor sign Gate-0 verdicts incl. framing gate. Fail → exit matrix, no forcing."

  - id: ME-GATE-prereg
    project: me
    owner_account: E
    worker: project_pro
    depends_on: [ME-GATE-0]
    inputs: [me/blueprint_frozen.md, me/gate0_diagnostics.json, me/power_bar.json]
    output_contract: null
    human_gate: true
    max_attempts: 1
    notes: "Draft OSF/AEA registration from frozen artifacts only; HUMAN submits; commit URL+timestamp. End of standby build."

  - id: GATE-E2-VERDICT
    project: me
    owner_account: null
    worker: script
    depends_on: []
    inputs: [ops/decisions.md]
    output_contract: null
    human_gate: true
    max_attempts: 1
    notes: "Owner records E2 approval verdict. Either way unblocks ME-M5+; verdict only sets priority (rejected → me takes E2's slot; approved → 4th-paper cadence on float)."

  # ---- ME execution phase (dormant until ME-GATE-prereg + GATE-E2-VERDICT) ----
  - id: ME-M5-main
    project: me
    owner_account: C
    worker: code_pro
    depends_on: [ME-GATE-prereg, GATE-E2-VERDICT, SH-econlib]
    inputs: [me/blueprint_frozen.md, me/announcement_panel.parquet, me/betas_lever.parquet]
    output_contract: main_results
    human_gate: false
    max_attempts: 2
    notes: "R7 guard: runner refuses if gate0_diagnostics/power_bar/prereg commits missing or post-dated."

  - id: ME-M5-audit
    project: me
    owner_account: null
    worker: gemini_free
    depends_on: [ME-M5-main]
    inputs: [me/blueprint_frozen.md]
    output_contract: null
    human_gate: false
    max_attempts: 2
    notes: "Results-blind blueprint↔code line audit; red-flag result-conditioned branches."

  - id: ME-M6-wedge
    project: me
    owner_account: C
    worker: code_pro
    depends_on: [ME-M5-main]
    inputs: [me/refraction_results, p1/outcomes IBES tables]
    output_contract: fingerprint
    human_gate: false
    max_attempts: 2
    notes: "Wedge paths + reversal portfolio + fundamental anchoring. Plot-before-interpret; mechanical verdict table."

  - id: ME-M7-grid
    project: me
    owner_account: null
    worker: deepseek
    depends_on: [ME-M5-main]
    inputs: [me/robustness_grid.csv]
    output_contract: robustness_results
    human_gate: false
    max_attempts: 2
    notes: "Templated variants; 2 sentinel rows; overnight batch. 备 qwen."

  - id: ME-M8-figs
    project: me
    owner_account: null
    worker: deepseek
    depends_on: [ME-M6-wedge, ME-M7-grid]
    inputs: [me/refraction_results, me/fingerprint_files, me/robustness_results.csv]
    output_contract: null
    human_gate: false
    max_attempts: 2
    notes: "Journal-grade figures/tables; numbers only from disk."

  - id: ME-M9-write
    project: me
    owner_account: E
    worker: project_pro
    depends_on: [ME-M8-figs]
    inputs: [everything on disk + frozen R6 claim language]
    output_contract: null
    human_gate: false
    max_attempts: 2
    notes: "Section per session; numbers→file map. Polish pass: deepseek_r."

  - id: ME-GATE-numbers
    project: me
    owner_account: null
    worker: script
    depends_on: [ME-M9-write]
    inputs: [me/numbers_map.csv]
    output_contract: null
    human_gate: true
    max_attempts: 1
    notes: "Owner accepts numbers→file map before red team."

  - id: ME-M10-redteam
    project: me
    owner_account: null
    worker: deepseek_r
    depends_on: [ME-GATE-numbers]
    inputs: [me/draft.pdf]
    output_contract: null
    human_gate: false
    channel_a: true
    max_attempts: 2
    notes: "裁判甲; structured attack checklist (playbook §4 M10). Round 2 = cold session."

  - id: ME-M10-redteam-B
    project: me
    owner_account: null
    worker: gemini_free
    depends_on: [ME-GATE-numbers]
    inputs: [me/draft.pdf]
    output_contract: null
    human_gate: false
    channel_of: ME-M10-redteam
    max_attempts: 2
    notes: "裁判乙. Never Anthropic (writer family)."

  - id: ME-GATE-respond
    project: me
    owner_account: E
    worker: project_pro
    depends_on: [ME-M10-redteam, ME-M10-redteam-B]
    inputs: [both referee reports]
    output_contract: null
    human_gate: true
    max_attempts: 1
    notes: "Claude drafts responses; owner approves plan; then revision + cold round 2."

  - id: ME-M11-cn
    project: me
    owner_account: null
    worker: qwen
    depends_on: [ME-M9-write]
    inputs: [me/draft.pdf]
    output_contract: null
    human_gate: false
    max_attempts: 2
    notes: "开题/预答辩/导师纪要; numbers from disk only."

  - id: ME-GATE-basketdata
    project: me
    owner_account: null
    worker: script
    depends_on: [ME-GATE-0]
    inputs: []
    output_contract: null
    human_gate: true
    max_attempts: 1
    notes: "OPTIONAL branch: owner confirms ETF Global / issuer basket-file coverage before ME-M13 spend."

  - id: ME-M13-baskets
    project: me
    owner_account: null
    worker: kimi
    depends_on: [ME-GATE-basketdata]
    inputs: []
    output_contract: null
    human_gate: false
    channel_a: true
    max_attempts: 2
    notes: "Creation-basket extraction 甲; twin gemini_free node ME-M13-baskets-B (channel_of). Enhancement only (floor rule)."

  - id: ME-M14-taq
    project: me
    owner_account: C
    worker: code_pro
    depends_on: [ME-GATE-0]
    inputs: [me/macro_events.csv, p1/conv_exposure.parquet]
    output_contract: null
    human_gate: false
    max_attempts: 2
    notes: "GATED, non-blocking: TAQ pilot 30+30×20; pass ≥70% small-cap coverage → build H1'/H5' module; fail → drop, core unaffected."
```

## §8 L1 worker specs (`ops/l1/ME-*.yaml`) and L0 wiring

**L1 spec pattern** (EXAMPLE.yaml format: `worker`, `est_cost`, `items`, mandatory
`sentinels`). Each channel twin gets an **independent** sentinel fence (house rule — the two
fences must fail independently). All sentinel `expect` values below are facts already
verified in this repo (P1 plan §2, collision sweep, Plan v2.1 Appendix A) — never invent new
ones from memory.

`ops/l1/ME-M1-events.yaml` (channel 甲; twin `ME-M1-events-B.yaml` on gemini_free with
sentinels S3/S4):

```yaml
worker: kimi
web_search: true
est_cost: 2.0
items:
  - id: fomc-calendar
    prompt: |
      [paste C0-ME] Task: from federalreserve.gov ONLY, list every SCHEDULED
      FOMC meeting 2017-01..2026-06: statement release date + time ET.
      Unscheduled/emergency meetings in a separate section, flagged. Every row
      carries the federalreserve.gov URL it came from. Schema: event_id | type
      | release_date | release_time_ET | source_url. No memory rows.
  - id: usmpd-surprises
    prompt: |
      [paste C0-ME] Task: from the SF Fed U.S. Monetary Policy Event-Study
      Database page, report: exact dataset name, download URL, variable name
      of the 30-minute policy surprise, sample coverage dates. Do NOT
      transcribe surprise values (the script ingests the file; you only
      locate it).
  - id: bls-calendar
    prompt: |
      [paste C0-ME] Task: from bls.gov release calendars ONLY, list every CPI
      and Employment Situation release 2017-01..2026-06 with date + 08:30 ET
      confirmation + URL. Same schema. Reschedules flagged, not dropped.
sentinels:
  - id: S1
    # source: docs/基金转换实验_博士研究计划.md §2 (house-verified)
    prompt: "On what date did DFA's first mutual-fund-to-ETF conversion wave take effect (the ~$30B anchor wave)? Reply YYYY-MM-DD only."
    expect: "2021-06-11"
  - id: S2
    # source: p1/t0_collision_sweep_channelA.md (house-verified)
    prompt: "In which year and month did the Federal Reserve publish the FEDS Note 'Implications of Growth in ETFs: Evidence from Mutual Fund to ETF Conversions'? Reply YYYY-MM only."
    expect: "2025-11"
```

`ops/l1/ME-M0-monitor.yaml` — clone P1-T0-monitor.yaml's structure (incl. its `manual: true`
kimi-bench parking note if the bench still holds at first arming) with the Plan §11 keyword
set, the Marta–Riva ≥40% hair trigger spelled out in the item prompt, and fresh sentinels
(suggested: S1 = SEC ETF Rule "6c-11"; S2 = dual-share-class relief "2025-12" — distinct
from ME-M1's fence so the two fail independently).

`ops/l1/ME-M3-blueprint-B.yaml`, `ME-M5-audit.yaml`, `ME-M7-grid.yaml`,
`ME-M10-redteam*.yaml`, `ME-M11-cn.yaml`, `ME-M13-baskets*.yaml`: single-item specs whose
prompts are §4's task prompts verbatim (each headed by C0-ME); M7's fence is its two
sentinel grid rows rather than Q&A sentinels (validator compares them to the main-spec
coefficients mechanically).

**L0 wiring checklist (implemented by `SH-me-register`, seat D):**

1. **R7 guard** — `me/guards/pre_outcome_check.py`, imported by every script under
   `me/analysis/`: refuse to run unless `gate0_diagnostics.json`, `power_bar.json`, and the
   pre-registration URL commit exist and predate the run (DAX `v1.0-preregistered` pattern).
2. **Monthly re-arm cron** — first of month: delete `ops/l1/out/ME-M0-monitor.json`; the
   overnight driver re-runs it (P1-T0-monitor pattern).
3. **Channel-diff scripts** — `me/tools/diff_channels.py` for M1 (row-level) and M3
   (section-level); output feeds the arbitration brief / DECISION_NEEDED list.
4. **Contract YAMLs** — the six §5 schemas registered in ops/contracts/ so
   `contracts.py <contract> <path>` gates every merge (M12's deterministic 80%).
5. **Budget** — ME L1 spend rides the same governor (80% dispatch ceiling / 20% escalation
   reserve); est_cost lines in every spec; standby-mode spend = ME-M0-monitor only (≈¥1/mo).
