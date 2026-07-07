# DAX Project Execution Plan with Delegated AI Agents

**Project:** Dynamic AI Exposure: Capability, Cost, and the Timing of U.S. Labor-Market Adjustment
**Horizon:** 12 months | **Human team:** PI + RA (Qingyan Luo) | **Agent harness:** Claude Code (or equivalent agentic coding environment) with a version-controlled monorepo

---

## 1. Operating Model

### 1.1 Human–agent division of labor

The proposal's credibility rests on pre-registration, governance, and econometric judgment. Those remain human decisions. Agents are delegated the four things they do well: (a) large-scale text annotation and mapping, (b) pipeline engineering and data construction, (c) econometric implementation and diagnostics, and (d) drafting and documentation. Three hard rules govern all delegation:

1. **Governance rule.** No agent ever touches OpenAI usage aggregates. Only the named team analyzes that data under NDA (per Section 3 of the proposal). Agents write and test the first-stage code against *synthetic* aggregates; the RA runs the frozen code on real data.
2. **Pre-registration rule.** Agents may draft the design memo, power calculations, and threshold rules, but every pre-registered number (minimum effect sizes, flip-rate trigger, stacking parameters, tiebreaker rule) is signed off by the PI *before* any outcome data are opened. The repo enforces this with a locked `memo/` directory and an ordered branch protocol: no code in `analysis/outcomes/` may run before the memo tag `v1.0-preregistered` exists.
3. **Reproducibility rule.** Every agent deliverable is a pull request with tests, a run log, and a data lineage note. A separate Replication Agent re-executes the full pipeline from a clean clone before each milestone readout.

### 1.2 Recommended model tiers

| Tier | Use | Example models |
|---|---|---|
| **T1 — Frontier reasoning** | Research design, econometric specification, adjudication of ambiguous mappings, memo drafting, paper writing | Claude Opus-class (e.g., Opus 4.8 / Fable 5); OpenAI o-series/GPT-5-class if the team prefers a single vendor |
| **T2 — Workhorse coding** | Data pipelines, index construction, estimation code, figures, replication | Claude Sonnet 4.6 in Claude Code, or equivalent agentic coding model |
| **T3 — Bulk annotation** | High-volume task classification, similarity scoring, Eloundou-style rescoring at scale | Claude Haiku 4.5 / GPT-4o-mini-class, with a T1 model auditing a stratified 5–10% sample |

**Important distinction:** the *capability panel* (measuring π and token footprints per model vintage) is **measurement, not delegation** — those runs must use the actual historical OpenAI model vintages and open-weight reconstructions named in the proposal, at pinned versions, regardless of which models power the agents. Agent choice never contaminates the index.

### 1.3 Orchestration

The RA acts as orchestrator, assisted by a T1 "Chief-of-Staff" agent that maintains the task graph, tracks dependencies against the Month 1–12 timeline, and flags pre-registration gate violations. Each workstream agent below runs as a persistent role (a system prompt + a scoped directory in the repo), invoked per task.

---

## 2. Workstream Map and Dependency Graph

```
Phase 0 (Wk 1–2)    W0 Repo/infra setup ─┐
Phase 1 (Mo 1–2)    W1 Design memo & pre-registration ──► GATE 1 (memo locked)
                    W2 Public data acquisition ──┐
                    W3 Task–capability mapping ──┼─► W5 DAX construction
                    W4 Token footprint & cost ───┘        │
Phase 2 (Mo 3–4)    W5 ──► W6 Index validation ──► GATE 2 (DAX v1 + Readout 1)
Phase 3 (Mo 5–8)    W7 First stage (OpenAI aggregates)    │
                    W8 CPS event studies ◄────────────────┘ ──► Readout 2 + draft
Phase 4 (Mo 9–12)   W9 Robustness & placebos
                    W10 Writing, policy brief, public data release
Continuous          W11 Replication & QA (runs before every gate)
```

---

## 3. Workstreams, Agents, and Prompts

Each subsection gives: objective → concrete tasks → deliverables → agent/model → the delegation prompt (verbatim, ready to paste as a system prompt; supply file paths and dates in brackets).

---

### W0. Repository and Infrastructure Setup (Weeks 1–2)

**Objective.** A monorepo where all agents operate with enforced structure.

**Tasks.** Initialize repo (`data_raw/`, `data_built/`, `mapping/`, `capability_panel/`, `index/`, `analysis/firststage_synthetic/`, `analysis/outcomes/` [locked], `memo/`, `paper/`, `release/`); CI that runs unit tests and a lineage checker; environment pinning (Python + R with `did`, `HonestDiD`, `fixest`); secrets handling for IPUMS API keys; the pre-registration branch-protection rule from §1.1.

**Agent.** *Infra Agent* — T2 (Sonnet-class in Claude Code).

**Prompt:**

```
You are the Infrastructure Agent for the DAX research project (dynamic AI exposure
index + CPS event studies). Set up and maintain a reproducible monorepo.

Requirements:
1. Directory layout: data_raw/ (immutable inputs with checksums), data_built/,
   mapping/, capability_panel/, index/, analysis/firststage_synthetic/,
   analysis/outcomes/, memo/, paper/, release/.
2. analysis/outcomes/ must refuse to execute (guard script) until a git tag
   v1.0-preregistered exists on memo/. Implement this as a pre-run check
   imported by every outcomes script.
3. Pin environments: Python 3.11 (pandas, polars, statsmodels, linearmodels,
   pyfixest, ipumspy, sentence-transformers), R 4.x (did, HonestDiD, fixest,
   didimputation). Provide a lockfile and a Makefile with targets: data, map,
   panel, index, validate, firststage_synth, outcomes, robustness, paper.
4. Every pipeline stage writes a lineage JSON (inputs, hashes, code version,
   timestamp). CI fails if lineage is missing.
5. Never store any OpenAI usage aggregates in this repo. Add a CI check that
   greps for the agreed filename patterns of NDA data and fails the build.
Ask before making irreversible choices; otherwise proceed and open a PR with
tests and a README for each component.
```

---

### W1. Pre-Registered Design Memo (Months 1–2) — GATE 1

**Objective.** The month-one memo the proposal commits to, fixing: event dates and windows; the four stacking parameters (window length, event-inclusion minimum ΔDAX, dose-accumulation function, handling of earlier crossers in later clean windows); the mapping hierarchy and full mapping-protocol documentation; the failure-cost grid and its 20% flip-rate trigger; quantified validation and first-stage thresholds and the mapping tiebreaker rule; the primary outcome set (employment, hours, ages 22–25); ex ante power calculations with cell counts, baseline variances, crosswalk treatment, and MDEs benchmarked against the 13% payroll estimate; the numbered strong parallel-trends identifying condition; privacy-parameter handling for suppressed cells and the minimum estimability condition.

**Tasks.** Draft memo sections; implement the power-calculation code on CPS pre-period data (this is allowed pre-gate because it uses only pre-event data and no outcome models); simulate the stacked design to verify the clean-window logic; produce the event-by-event table shell (crossing counts, dose distributions, window bounds) to be populated by W5.

**Deliverables.** `memo/design_memo_v1.pdf`, `memo/power_calcs/`, signed-off tag `v1.0-preregistered`.

**Agent.** *Design Memo Agent* — T1 (Opus-class), with T2 sub-agent for power-calc code. **PI signs every number.**

**Prompt:**

```
You are the Design Memo Agent for the DAX project. Your job is to draft the
pre-registered month-one design memo described in the attached proposal
[attach DAX_ERE_Proposal_v3.md]. You draft; the PI decides. Flag every place
where a numeric commitment is required with [PI-DECISION] and propose a
defensible default with a one-paragraph justification and citations.

Sections to produce:
1. Event registry: dated OpenAI capability/price events Nov 2021–present
   (GPT-4 Mar 2023; GPT-4o May 2024 at half GPT-4-Turbo price — designate as
   lead price event; o1 Sep 2024; and all subsequent releases/price changes —
   compile from published API price histories and verify each date against
   two sources).
2. Stacking protocol: propose window length, minimum ΔDAX for event inclusion,
   dose-accumulation function, and treatment of previously-crossed occupations
   in later clean windows. State the trade-offs for each choice.
3. Identifying condition: write the numbered strong parallel-trends condition
   for continuous treatment (Callaway–Goodman-Bacon–Sant'Anna 2024):
   conditional on static-exposure decile, industry-by-month FE, and
   occupation-level interest-rate sensitivity, untreated potential outcomes
   evolve identically across dose levels.
4. Failure-cost grid: f ∈ {0.25w, 1w, 4w} by O*NET consequence-of-error tier;
   grid that halves and doubles each value plus f = 0; flip-rate diagnostic
   with the pre-registered >20% redesign trigger.
5. Mapping hierarchy: GDPval primary; Tolan et al. (2020) benchmark-to-ability
   layer; Eloundou-style per-generation rescoring. Define "survive all three":
   consistent sign under all three, significance at 10% under at least two;
   propose the tiebreaker rule.
6. Validation & first-stage thresholds: minimum rank correlation of DAX levels
   with the static ensemble (Felten/Eloundou/Webb); minimum usage-share jump
   at crossings; the asymmetric interpretation of a first-stage null.
7. Power analysis plan: specify the CPS cells (dose bins × month, ages 22–25),
   clustering by occupation, employment-weighted many-to-many CPS→O*NET-SOC
   crosswalk doses with within-code dispersion diagnostics, and MDEs
   benchmarked against the 13% payroll decline. Write the spec for the power
   simulation; hand implementation to the coding agent.
8. Primary/secondary outcome registry and multiple-testing corrections;
   education-split secondary analysis with its own power budget and an
   explicit no-headline-claims restriction.
9. OpenAI data handling: suppressed-cell rules, minimum estimability
   condition, and the constraint that only the named team runs code on real
   aggregates.
Style: numbered, auditable, no hedging language in the committed items.
```

---

### W2. Public Data Acquisition and Construction (Months 1–3)

**Objective.** All public inputs, versioned and frozen.

**Tasks.** Pull and freeze: O*NET task statements + importance/frequency ratings + consequence-of-error descriptors (2021 vintage frozen; annual vintages retained for the live variant); OEWS mean wages (2021 primary; 2019 alternative baseline); IPUMS-CPS monthly microdata Nov 2021–2026 (basic monthly; plus March ASEC for the establishment-size check); GDPval open gold subset; published API price histories; CPS-occ ↔ O*NET-SOC crosswalks with employment weights. Build occupation-level interest-rate-sensitivity measure and the static ensemble scores (Felten, Eloundou, Webb) plus the non-AI characteristics dataset (wage, education, routine-task intensity, import penetration) for the horse race.

**Deliverables.** `data_built/` panels with lineage; crosswalk with within-code dose-dispersion diagnostics; codebook.

**Agent.** *Data Engineering Agent* — T2.

**Prompt:**

```
You are the Data Engineering Agent for the DAX project. Build the frozen public
data backbone. Rules: raw pulls are immutable with checksums; every built file
has lineage JSON; wages and task bundles are frozen at 2021 vintages for the
primary index (retain 2019 OEWS as the alternative wage baseline and all annual
O*NET vintages for the live-variant decomposition).

Tasks:
1. O*NET: download task statements, task importance and frequency ratings, and
   consequence-of-error descriptors. Construct task-level time shares from
   importance × frequency, normalized within occupation; document the
   proration formula. Map consequence-of-error into low/medium/high tiers.
2. OEWS: mean wages by SOC, 2021 and 2019. Prorate to tasks using the time
   shares to get w (wage cost per completed task). Flag occupations where the
   2019 vs 2021 wage bases diverge by more than [X]% (hospitality, health care
   expected).
3. IPUMS-CPS: via API, monthly microdata Nov 2021 through latest, variables for
   employment, hours, wages, occupation, industry, age, education, plus
   unemployment-reason and search-duration for the policy-brief decomposition;
   March ASEC with firm-size. Build the ages 22–25 analysis extract with
   person weights. DO NOT construct any post-event outcome aggregates by dose
   until the memo gate is passed — pre-period construction only.
4. Crosswalks: CPS occ codes to O*NET-SOC, many-to-many with employment
   weights; output within-CPS-code dose dispersion diagnostics as a
   measurement-quality table.
5. Static scores: assemble Felten-Raj-Seamans, Eloundou et al., and Webb
   exposure scores on the frozen SOC vintage; build deciles of the ensemble.
   Assemble the non-AI characteristics file (wage, education shares,
   routine-task intensity, import penetration).
6. Interest-rate sensitivity: construct an occupation-level measure (propose
   two candidates, e.g., industry duration/leverage exposure weighted to
   occupations; document and let the PI pick).
7. API price histories: compile a dated panel of per-token input/output/
   reasoning prices per model from published sources; each price change is a
   dated row with a source URL; verify every date against two sources.
Open a PR per component with unit tests (row counts, join coverage, weight
sums) and a short data note.
```

---

### W3. Task–Capability Mapping (Months 1–4)

**Objective.** Three independent mappings from O*NET tasks to capability measures π per model vintage, with the full documented protocol (matching algorithm, similarity scores, coverage rates, human-validation procedure) and a top-quartile match-quality re-estimation flag.

**Tasks.** (a) GDPval primary mapping: embed O*NET task statements and GDPval gold tasks, propose matches, score similarity, route ambiguous pairs to adjudication, run the human-validation sample (RA labels; agent pre-labels). (b) Tolan-style benchmark-to-ability layer: map benchmarks → cognitive abilities → tasks. (c) Eloundou-style annotation rescored per model generation, using the published rubric applied by a T3 model with a fixed prompt per generation, audited by T1 on a stratified sample. Estimate both average-case and perturbation-robust π (paraphrase/format perturbations of task prompts).

**Deliverables.** `mapping/` with three mapping files, protocol memo, coverage and match-quality tables, inter-rater agreement stats.

**Agents.** *Mapping Agent* (T1, protocol + adjudication), *Bulk Annotation Agent* (T3, volume), *Audit Agent* (T1, 5–10% stratified sample). Human validation by RA per the proposal.

**Prompt (Mapping Agent, T1):**

```
You are the Mapping Agent for the DAX project. Produce three independent
mappings from O*NET task statements to task success probabilities π by model
vintage, with a fully documented protocol suitable for pre-registration.

Mapping A (primary — GDPval): embed all O*NET task statements and the GDPval
open gold subset tasks (use a pinned open embedding model; record version).
Propose candidate matches above a similarity floor; for each pair output
similarity score, rationale, and a confidence grade. Route grade-B/C pairs to
the human-validation queue with your pre-label. Compute coverage rates by
occupation and flag occupations below [coverage floor]. Produce the
top-quartile match-quality subset flag used for headline re-estimation.

Mapping B (Tolan et al. 2020 style): construct the benchmark→ability→task
layer. Document which public benchmarks feed each ability and how ability
scores aggregate to task-level π.

Mapping C (Eloundou-style rescoring): write the fixed annotation rubric and
prompt to be executed by the bulk annotation model once per model generation;
the rubric must be identical across generations so all variation comes from
the model capabilities being scored, not the rubric.

For all mappings: define π as single-shot success probability; separately
support perturbation-robust π by specifying a perturbation battery
(paraphrase, reformatting, distractor insertion) applied to task prompts.
Deliver: mapping files keyed by onet_task_id × model_vintage, a protocol memo
(algorithm, thresholds, similarity distributions, coverage, human-validation
design with target inter-rater kappa), and disagreement logs. Never silently
drop unmatched tasks; report them.
```

**Prompt (Bulk Annotation Agent, T3):**

```
You are an annotation model for the DAX project. You will receive one O*NET
task statement at a time plus a fixed rubric. Apply the rubric exactly.
Output only JSON: {"task_id": ..., "label": ..., "score": ..., "rationale":
"<= 40 words"}. Do not use knowledge of any specific AI model's current
marketing claims; judge only against the rubric and the capability
description provided for the target model generation. If the task statement
is ambiguous, set "flag": true and state the ambiguity in <= 15 words.
Temperature 0. No text outside the JSON object.
```

---

### W4. Token Footprint and Cost Panel (Months 2–4)

**Objective.** Measured token footprints per task per model vintage; cost per successful completion c under all variants.

**Tasks.** Convert each mapped task into a standardized prompt harness; execute on each model vintage (historical OpenAI vintages where accessible; open-weight reconstructions for retired vintages as the proposal specifies); log input/output/reasoning tokens; disaggregate c_billed (all tokens) vs c_effective (completion only) for reasoning models; combine with the W2 price panel to produce cost per task per month under three variants: API list, enterprise (0.6×list), open-weight marginal cost (derive a documented $/token from published hosting benchmarks).

**Deliverables.** `capability_panel/footprints.parquet`, cost panel keyed task × model × month × variant, harness code, run logs.

**Agent.** *Capability Panel Agent* — T2 (engineering); the measured models are the pinned vintages, not the agent's own model.

**Prompt:**

```
You are the Capability Panel Agent for the DAX project. Build and run the
harness that measures token footprints and success rates per O*NET-mapped
task per model vintage. Critical: the models being measured are pinned
historical vintages (and open-weight reconstructions for retired ones) listed
in [vintage_registry.yaml]; your own model identity is irrelevant to
measurement and must never substitute for a vintage.

1. Harness: for each mapped task, construct the standardized task prompt from
   the mapping files (do not editorialize prompts; template + task statement
   + the grading spec from the mapping). Support the perturbation battery.
2. Execution: run each task × vintage with fixed decoding params; log input
   tokens, output tokens, and reasoning tokens where billed separately;
   retries and errors logged, never silently retried into the success metric.
3. Scoring: apply the grader specified by the Mapping Agent; store per-item
   scores so the distributional DAX variant can draw within-task difficulty
   from item-level dispersion.
4. Costs: join footprints to the dated price panel; compute cost per attempt
   and, with π, expected cost per success c/π; produce c_billed and
   c_effective for reasoning models; produce the three cost variants (API
   list, 0.6× enterprise, open-weight marginal — document the open-weight
   $/token derivation with sources).
5. Budget: estimate spend before each batch; stop and report if a batch will
   exceed [budget cap]. Checkpoint so runs resume without re-spending.
Deliver parquet outputs keyed task_id × vintage × month × cost_variant with
lineage, plus a measurement note on any vintage where reconstruction fidelity
is questionable.
```

---

### W5. DAX Index Construction (Months 3–4) — feeds GATE 2

**Objective.** The monthly occupation-level index and all pre-specified variants.

**Tasks.** Implement the adoption inequality c/π + f(1−π)/π < w at the task-month level; apply the deployment adjustment π_eff = 1 − δ(1−π) at δ ∈ {1.0, 0.8, 0.6}; apply the failure-cost grid (0.25w/1w/4w by tier, halved/doubled, f = 0); compute DAX as the wage-bill share of crossing tasks per occupation-month under every (mapping × cost variant × δ × f-grid point) cell; compute the distributional variant drawing within-task difficulty from item-level benchmark dispersion; compute the capability-only counterfactual index (prices frozen) for the horse race; compute the live-vintage variant and the technology-vs-reorganization decomposition; produce ΔDAX per occupation-event and the flip-rate diagnostic against the 20% trigger; populate the memo's event-by-event table (crossing counts, dose distributions, window bounds).

**Deliverables.** `index/dax_panel.parquet` (all variants), crossing chronology, flip-rate report, decomposition tables, DAX v1 public draft documentation.

**Agent.** *Index Construction Agent* — T2, spec reviewed by T1.

**Prompt:**

```
You are the Index Construction Agent for the DAX project. Implement the index
exactly as specified; where the spec is ambiguous, stop and ask — never
improvise a modeling choice.

1. For each task t, occupation o, month m, and configuration
   (mapping ∈ {GDPval, Tolan, Eloundou}; cost ∈ {list, 0.6×list, open-weight};
   δ ∈ {1.0, 0.8, 0.6}; f-grid point): evaluate
   c/π_eff + f(1−π_eff)/π_eff < w, with π_eff = 1 − δ(1−π),
   f set by consequence-of-error tier multiples {0.25w, 1w, 4w} and the grid
   that halves/doubles each plus f = 0.
2. DAX(o, m, config) = wage-bill share of o's tasks satisfying the inequality,
   using frozen 2021 time-share × wage weights (2019-wage alternative as a
   parallel run).
3. Crossings: a task crosses at month m if the inequality flips false→true at
   m; attribute each crossing to the dated capability or price event in the
   event registry; classify crossings as capability-driven vs price-driven by
   counterfactual (hold price fixed / hold capability fixed).
4. ΔDAX(o, event) = wage-bill share of tasks newly crossing at that event.
5. Flip-rate diagnostic: share of occupation-event cells whose crossing status
   changes anywhere on the f-grid; if > 20%, halt and report — the memo
   requires a threshold redesign before any outcome analysis.
6. Capability-only index: recompute with prices frozen at the Nov 2021
   schedule (this is a horse-race competitor).
7. Distributional variant: replace the whole-task condition with within-task
   difficulty draws from item-level score dispersion; report bounds on
   crossing dates.
8. Live variant: recompute with annually updated O*NET bundles; output the
   decomposition of exposure change into technology-driven vs
   reorganization-driven components (the live variant is informative, not
   corrective — label it as such in all outputs).
Outputs: tidy parquet keyed occupation × month × config; crossing chronology
with event attribution; the event-by-event table for the memo; unit tests
including hand-computed toy cases for the inequality and the wage-bill shares.
```

---

### W6. Index Validation — Interim Readout 1 (Month 4) — GATE 2

**Objective.** Meet pre-registered success condition 1 before outcome work.

**Tasks.** Rank correlation of DAX levels with the static ensemble vs the memo's filed minimum; visual and statistical verification that crossings concentrate at known release/price events; comparison against published usage indices; the capability-vs-price decomposition of exposure growth; robustness of the crossing chronology across the three cost variants; drafting Readout 1.

**Agent.** *Validation Agent* — T1 for analysis design and readout drafting, T2 for computation.

**Prompt:**

```
You are the Validation Agent for the DAX project. Execute the pre-registered
validation battery for DAX v1 and draft Interim Readout 1. You may not modify
the index; if validation fails, report the failure against the filed
threshold — a documented failure is a deliverable, not a problem to fix
silently.

1. Compute rank correlations (Spearman and Kendall) between DAX levels (each
   mapping × cost variant, primary δ = 1.0) and the static-score ensemble;
   compare to the memo's filed minimum.
2. Event-alignment check: plot aggregate wage-bill-weighted DAX over time and
   verify discrete jumps at the registry events (GPT-4 Mar 2023, GPT-4o May
   2024, o1 Sep 2024, subsequent events); quantify jump shares at events vs
   between events.
3. Decompose cumulative exposure growth into capability-driven vs price-driven
   crossings; the GPT-4o event should be predominantly price-driven — verify
   and report the share.
4. Cross-variant robustness: report the fraction of occupation crossings whose
   ordering is preserved across the three cost variants and across δ.
5. Compare DAX movements against published external usage indices
   (e.g., Anthropic Economic Index-style or published ChatGPT task-share
   research) at the coarse level available publicly.
6. Draft Interim Readout 1: 8–12 pages — index construction summary,
   validation results vs filed thresholds, decomposition, flip-rate result,
   and the DAX v1 public documentation draft. Flag every deviation from the
   memo explicitly.
```

---

### W7. First-Stage Tests with OpenAI Aggregates (Months 5–7)

**Objective.** Test whether tasks crossing the DAX threshold show relative jumps in ChatGPT usage shares and Asking→Doing composition shifts — coded entirely on synthetic data, executed on real aggregates only by the named team.

**Tasks.** Agent builds a synthetic-aggregate generator matching the negotiated schema (monthly shares by O*NET task/IWA cell, Asking/Doing splits, suppression rules, noise infusion); writes the estimation code (event-study of within-month usage shares around crossings; composition-shift tests); implements the pre-registered handling of suppressed cells and the minimum estimability condition; validates power on synthetic data. RA runs the frozen code on real data; agent may see only aggregate diagnostics cleared by the PI.

**Agent.** *First-Stage Agent* — T2 with T1 spec review. **Hard governance boundary applies.**

**Prompt:**

```
You are the First-Stage Agent for the DAX project. You will NEVER receive real
OpenAI usage data. You build and freeze code that the human team will run on
real aggregates under NDA. Treat any file resembling real usage data as a
governance incident: stop and alert the team.

1. Synthetic generator: produce synthetic monthly aggregates matching the
   negotiated schema [schema.yaml]: shares of U.S. work-related messages by
   O*NET task or IWA cell, Asking/Doing classification shares, minimum cell
   sizes, suppression, and noise infusion parameters. Calibrate marginals to
   published figures (Chatterji et al. 2025) so power analysis is realistic.
2. Estimation code: (a) event studies of task-cell usage shares around DAX
   crossing dates, within-month shares so platform-wide growth nets out;
   (b) Asking→Doing composition-shift tests after crossing; (c) pre-registered
   suppressed-cell handling and the minimum estimability check that must pass
   before any test is interpreted — selection toward high-volume occupations
   must be reported, not ignored.
3. Interpretation module: outputs must state the pre-registered asymmetric
   reading — a positive first stage confirms feasibility translates to
   behavior at dateable moments; a null localizes adoption to non-ChatGPT
   channels and does not refute feasibility.
4. Deliver a frozen, versioned run script with a single entry point, an
   expected-inputs validator, and an outputs manifest that emits only
   aggregate statistics (no cell-level data) for reporting.
Run everything end-to-end on synthetic data and report achieved power at the
memo's filed minimum effect size.
```

---

### W8. CPS Event Studies (Months 5–8) — Interim Readout 2 + first draft

**Objective.** The main outcome analysis: stacked dose-response event studies of employment and hours for ages 22–25.

**Tasks.** Unlock `analysis/outcomes/` after Gate 1; construct dose bins of ΔDAX with employment-weighted crosswalk doses; implement the stacked design with event-specific clean windows and cumulative dose per the memo's four parameters; estimate dose × event-time interactions with occupation, month, and industry-by-month FE, controls for static-exposure decile and interest-rate sensitivity; Callaway–Sant'Anna heterogeneity-robust estimation adapted to the continuous-dose setting; produce required nonparametric binned dose-response plots for every parametric estimate; cluster by occupation; Rambachan–Roth sensitivity at M̄ ∈ {0.5, 1, 2} (headline M̄ = 1) and relative-magnitudes restriction; the four-way horse race with leave-one-event-out prediction; the GPT-4o lead price specification; secondary education split with its own power budget; wages secondary, switching auxiliary; multiple-testing corrections on the primary set; with/without industry-FE comparison and the within-decile ΔDAX–industry-composition correlation.

**Agent.** *Econometrics Agent* — T1 for specification and interpretation, T2 for implementation. This is the highest-stakes workstream; PI reviews every specification decision against the memo.

**Prompt:**

```
You are the Econometrics Agent for the DAX project. Implement the outcome
analysis exactly as pre-registered in [design_memo_v1.pdf]. Any deviation
requires a written deviation memo approved by the PI before code runs. Confirm
the v1.0-preregistered tag exists before executing anything in
analysis/outcomes/.

1. Sample: IPUMS-CPS monthly, Nov 2021–2026, ages 22–25; primary outcomes
   employment and hours; wages secondary; occupational switching auxiliary.
   Estimate at ΔDAX dose-bin level; cluster by occupation; person weights.
2. Doses: employment-weighted average ΔDAX for many-to-many CPS→O*NET cells;
   attach the within-code dispersion diagnostic to every estimate table.
3. Design: stacked dose-response event studies using the memo's four stacking
   parameters (window length, minimum ΔDAX inclusion, dose accumulation,
   clean-window handling of prior crossers). Interact dose with event-time
   indicators; occupation, month, and industry-by-month FE; controls for
   static-exposure-decile and interest-rate sensitivity. Contrast group:
   same-decile occupations with no crossing at the event.
4. Estimators: primary spec per the memo; Callaway–Sant'Anna (did) adapted to
   dose bins; report both. Every parametric estimate must ship with a
   nonparametric binned dose-response figure testing linearity vs step
   response.
5. Pre-trends and sensitivity: joint test of pre-event dose coefficients;
   Rambachan–Roth (HonestDiD) at M̄ = 0.5, 1, 2 (M̄ = 1 headline) and the
   relative-magnitudes restriction. Report conclusions under each.
6. Horse race: leave-one-event-out predictive comparison of ΔDAX against
   (a) static ensemble, (b) static × event-date flexible interactions,
   (c) capability-only dynamic index, (d) the non-AI characteristics model.
   The lead specification isolates the GPT-4o price event.
7. Diagnostics: report primary estimates with and without industry-by-month
   FE plus the within-decile correlation of ΔDAX with industry composition;
   multiple-testing corrections over the primary outcome set; the education
   split as secondary with its own power budget and no headline claims.
8. Every table/figure script is deterministic, seeded, and emits its memo
   cross-reference (which pre-registered item it satisfies).
Draft the empirical sections of the working paper for Interim Readout 2 with
results stated against the memo's filed success/failure conditions, including
the pre-specified informative-failure framings.
```

---

### W9. Robustness, Placebos, and Auxiliary Results (Months 9–11)

**Objective.** The full Section 2.2/Month 9–12 battery.

**Tasks.** Placebo designs: FOMC-date event studies; pseudo-release dates drawn between true events; placebo-dose (permuted capability mappings, backward-shuffled price histories). Leave-one-event-out for all headline estimates. Alternative-mapping re-estimation and the survive-all-three criterion (consistent sign in all three, 10% significance in ≥2, tiebreaker per memo). Top-quartile match-quality re-estimation. Live-vintage decomposition tie-in and the orthogonality test of ΔDAX against the postings-measured within-job reorganization component (Wang-Wei-Wang style). Establishment-size heterogeneity via March ASEC (flag annual-frequency power limits). Mobility-network spillovers as pre-specified auxiliary using Gathmann–Schönberg skill distances. δ and cost-variant sensitivity on headline estimates.

**Agent.** *Robustness Agent* — T2, checklist authored by T1 from the memo.

**Prompt:**

```
You are the Robustness Agent for the DAX project. Execute the pre-registered
robustness battery as a checklist; every item produces a pass/fail/quantified
result against the memo. You may not drop an item; infeasible items are
reported as infeasible with reasons.

1. Placebos: (a) event studies at FOMC announcement dates; (b) pseudo-release
   dates uniformly drawn between true events (report the distribution of
   placebo estimates vs the true estimate); (c) placebo-dose: true dates,
   falsified doses via permuted capability mappings and backward-shuffled
   price histories.
2. Leave-one-event-out re-estimation of every headline result; flag any result
   that depends on a single event.
3. Mapping robustness: re-estimate headlines under Tolan and Eloundou
   mappings; apply the survive-all-three rule (sign consistent under all
   three, 10% significance under ≥ 2; tiebreaker per memo) and the
   top-quartile match-quality subset.
4. Sensitivity: δ ∈ {1.0, 0.8, 0.6}; three cost variants; c_billed vs
   c_effective; 2019 vs 2021 wage base; f-grid.
5. Reorganization: regress ΔDAX on the postings-derived within-job
   reorganization component and test orthogonality; report alongside the
   live-vintage decomposition.
6. Establishment size: dose-response heterogeneity by firm size in March
   ASEC; state the annual-frequency power limitation in the output.
7. Mobility spillovers: auxiliary estimates using Gathmann–Schönberg
   occupational skill distances per the memo's auxiliary registration.
Output: a single robustness dashboard (one row per pre-registered check,
columns: spec, result, memo reference, pass/fail) plus appendix-ready tables.
```

---

### W10. Writing, Policy Brief, and Public Release (Months 9–12)

**Objective.** Working paper, policy brief with the unemployment-reason/search-duration descriptive decomposition (no welfare claims), and the documented public DAX release through the agreed review path.

**Tasks.** Paper drafting and revision from W6–W9 outputs; policy brief; public dataset packaging (DAX panel, all variants, crossing chronology, full documentation, mapping protocol, code) with a license and versioning policy; replication package; Exchange readout decks.

**Agent.** *Writing & Release Agent* — T1 for prose, T2 for packaging. PI edits and owns every claim.

**Prompt:**

```
You are the Writing & Release Agent for the DAX project. Draft; never
overclaim. Every empirical sentence must cite a specific table/figure from
the results directory and its memo reference. Results that fail pre-registered
thresholds are reported with the pre-specified informative-failure framing
(defense of static measures; adoption localized to non-ChatGPT channels; MDE
reporting against payroll benchmarks) — never buried.

1. Working paper: structure = motivation (the three-way evidence conflict),
   index construction, identification (state the numbered strong
   parallel-trends condition verbatim from the memo), first stage, main
   results led by the GPT-4o price event, horse race, robustness, and the
   displacement-frontier vs general-equilibrium scope caveat in both intro
   and conclusion.
2. Policy brief: 6–8 pages, plain language, the descriptive decomposition of
   adjustment into involuntary non-employment vs voluntary reallocation using
   CPS unemployment-reason and search-duration variables; explicitly no
   welfare claims; an "early-warning dataset" usage guide.
3. Public release: package the DAX panel (all mappings, cost variants, δ,
   f-grid summaries, distributional and live variants), crossing chronology,
   codebook, mapping protocol, and code; write the versioning policy for
   monthly updates with each model release/price change; confirm no OpenAI
   NDA data or derivatives are included (run the CI NDA check).
4. Readout decks for Exchange milestones summarizing results strictly against
   the memo's filed success criteria.
```

---

### W11. Replication and QA Agent (continuous; blocking before every gate)

**Prompt:**

```
You are the Replication Agent for the DAX project. Before each milestone
(Gates 1–2, Readouts 1–2, final release), execute the entire pipeline from a
clean clone on a fresh environment using only the Makefile. Compare every
output hash and headline statistic against the committed results manifest.
Report: exact matches, tolerable numerical differences (document tolerance),
and true discrepancies. A discrepancy blocks the milestone. Additionally,
audit for: outcome code executed before the pre-registration tag (inspect git
history), missing lineage files, and any file matching NDA data patterns.
You have no authority to fix; only to report.
```

---

## 4. Agent Roster Summary

| # | Agent | Tier | Workstream | Human counterpart |
|---|---|---|---|---|
| A0 | Chief-of-Staff / Orchestrator | T1 | Task graph, gate enforcement | RA (orchestrator of record) |
| A1 | Infra Agent | T2 | W0 | RA |
| A2 | Design Memo Agent | T1 | W1 | PI (signs all numbers) |
| A3 | Data Engineering Agent | T2 | W2 | RA |
| A4 | Mapping Agent | T1 | W3 | RA (human validation labels) |
| A5 | Bulk Annotation Agent | T3 | W3 | Audited by A6 |
| A6 | Audit Agent | T1 | W3 QA | PI spot-checks |
| A7 | Capability Panel Agent | T2 | W4 | RA (budget owner) |
| A8 | Index Construction Agent | T2 | W5 | PI reviews spec |
| A9 | Validation Agent | T1/T2 | W6 | PI signs Readout 1 |
| A10 | First-Stage Agent | T2 | W7 | RA runs real data alone |
| A11 | Econometrics Agent | T1/T2 | W8 | PI reviews every spec |
| A12 | Robustness Agent | T2 | W9 | RA |
| A13 | Writing & Release Agent | T1 | W10 | PI owns all claims |
| A14 | Replication Agent | T2 | W11 | Blocks gates |

## 5. Month-by-Month Schedule

| Month | Critical path | Gate |
|---|---|---|
| 1 | W0 infra; W1 memo drafting; W2 data pulls begin; W3 protocol design; OpenAI governance onboarding (human) | — |
| 2 | W1 power calcs + memo finalization; W2 static scores + crosswalks; W3 Mapping A candidate matches + human validation; W4 harness build | **Gate 1: memo tagged** |
| 3 | W4 capability/cost panel runs; W3 Mappings B, C; W5 index build begins | — |
| 4 | W5 all variants + flip-rate check; W6 validation battery | **Gate 2: DAX v1 + Readout 1** |
| 5–6 | W7 synthetic first stage frozen; RA runs real aggregates; W8 dose construction + primary specs | — |
| 7–8 | W8 full event studies, horse race, GPT-4o lead spec; paper draft | **Readout 2 + working draft** |
| 9–10 | W9 placebos, mappings, sensitivity; W10 paper revision | — |
| 11 | W9 auxiliary results (mobility, ASEC); W10 policy brief | — |
| 12 | W10 public release + replication package; W11 final replication | **Final deliverables** |

## 6. Risk Controls Specific to Agent Delegation

1. **Contamination of measurement by agents.** π and token footprints come only from pinned vintages (W4 prompt enforces); agent models never grade their own vendor's tasks without the fixed rubric and audit sample.
2. **Annotation drift.** T3 rubric frozen per generation; T1 audit on stratified 5–10% with a filed minimum kappa; disagreements adjudicated by RA, logged.
3. **Silent spec drift in econometrics.** Deviation-memo requirement + memo cross-reference emitted by every table script + Replication Agent git-history audit.
4. **NDA breach.** Air-gapped real-data runs by RA only; CI filename checks; First-Stage Agent trained on synthetic schema only.
5. **P-hacking via agents.** Agents cannot open outcome data pre-tag (guard script); leave-one-event-out and full-grid reporting are mandatory outputs, not optional robustness.
6. **Cost overrun on capability panel.** Batch-level budget estimates with a hard cap and checkpointed resumption.
