# Macro-Event Chapter ("Refraction") · Multi-Agent Execution Playbook v1.0
### Companion to `MacroEvent_Chapter_Plan_v2_1_FINAL.md` — same format as Project_1.md (P1), E2_执行手册, DAX_Execution_Plan

> Model assignments follow the **v1.1 budget regime** (see P1_修订补丁_v1_1.md §5 and
> Agent_Architecture_24x7.md §4): Anthropic only via Pro subscription (Claude Code + claude.ai
> Projects/Research), no non-Anthropic flagship APIs; cross-vendor independence (R2) carried by
> cheap tiers (DeepSeek / Kimi / GLM / Qwen + Gemini free). Escalation ladder tops out at a
> Claude Code prime block. Re-check assignments quarterly with the three standard probe tasks.
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

## §2 Model assignment table (v1.1 budget regime)

| Task | Role | Assignment | Channel-B / audit |
|---|---|---|---|
| M0 | Collision sweep + citation verification | claude.ai Research (Pro, zero marginal) | Kimi `$web_search` (union, R2) |
| M1 | Macro calendar + surprise extraction | Kimi K2.6 (channel 甲) | Gemini Flash free (channel 乙); arbitration Claude Code |
| M2 | Announcement panel + betas + lever (main build) | Claude Code (Sonnet; escalate Opus/Fable on the LOO-beta module) | Unit tests by DeepSeek V4 (spec-only, no implementation access) |
| M2a | Gate-0 diagnostics (shrinkage sweep; distinctiveness) | Claude Code | Deterministic asserts; owner reads memo |
| M2b | Power simulation + exit-D power bar | Claude Code (reuse P1 T2a machinery) | Sentinel: known-answer config row |
| M3 | Estimation blueprint (spec) | claude.ai Project session (Pro) — channel 甲 | DeepSeek reasoning tier — channel 乙; diff; disputes → NEED_HUMAN |
| M4 | Pre-trend triple + placebo-in-time | Claude Code | Gemini Flash free code audit (checklist) |
| GATE-0-FREEZE | Pre-registration (OSF/AEA) | Human (owner + advisor) | Claude drafts the registration text (M3 outputs only) |
| M5 | Main estimation implementation | Claude Code | Gemini Flash free audit: blueprint↔code line check; flag result-driven branches |
| M6 | Wedge fingerprint + fundamental anchoring | Claude Code (P1 T3/T6 machinery re-targeted) | Plot-before-interpret rule (P1 T6) |
| M7 | Robustness grid | DeepSeek V4 (备: Qwen3.7 Plus) | 2 sentinel rows (= main spec); mismatch voids batch |
| M8 | Figures/tables | DeepSeek V4 Flash or Haiku 4.5 | Numbers only from disk files |
| M9 | Paper writing | claude.ai Project (Pro), section per session | DeepSeek reasoning polish pass; numbers→file map |
| M10 | Red team ×2 (non-Anthropic, cold second round) | DeepSeek reasoning (裁判甲) | Gemini free tier (裁判乙); structured attack checklist |
| M11 | Chinese materials | Qwen3.7 Max | — |
| M12 | Gatekeeping | Deterministic scripts (contracts.py) + cheap-tier checklist | Human at the six gates (§5) |
| M13 (opt) | Creation-basket file extraction | Kimi + Gemini Flash dual channel | `NEED_HUMAN: coverage` first |
| M14 (gated) | TAQ pilot → H1′/H5′ module | Claude Code | Runs only on pilot pass; never load-bearing |

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
