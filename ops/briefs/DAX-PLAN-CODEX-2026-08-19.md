# DAX execution plan for Codex — 2026-08-19

Scope: **DAX only**. Written for an agent with no memory of the session that
produced it. Every item names its owner, its precondition, the exact command
where one exists, what "done" means mechanically, and what to do when it cannot
be done.

A note on sizing: this is scoped to the work that actually exists between here
and Gate 2, which is months of it — comfortably more than any weekly budget
absorbs. It is not padded to fill a quota, because padded work in this
repository has historically become prose nobody executed, which is the failure
mode §0.4 exists to prevent.

---

## §0. How to work

### 0.1 The five rules that override everything

From `CLAUDE.md`. Where an instruction below conflicts with these, these win
and you emit `NEED_HUMAN`.

1. **The model is not a source of facts.** Every date, price, AUM, holding and
   coefficient comes from code you ran on real data, or from an extraction
   carrying a raw-source locator (EDGAR accession + URL, WRDS table + query,
   doc page). A number recalled from training is a hallucination — discard it.
2. **Dual channel on high-hallucination work** — event lists, citations, spec.
   Two *different vendor families*, machine-diffed, third model plus human on
   splits. A self-review satisfies nothing.
3. **Schema contracts.** Tasks hand off through files. Column names in
   `ops/contracts/` are frozen; never rename one.
4. **Don't know → stop.** Emit `NEED_HUMAN: <reason>`. Never guess-fill.
5. **Expensive gates, cheap runs.** Spec, audit and red-team use the frontier;
   templated bulk uses cheap tiers.

### 0.2 The seal — three layers, do not work around any of them

- Never create the tag `v1.0-preregistered`. Only the PI creates it, at A7.
- Never create or open `dax/analysis/outcomes/`. CI refuses committed files
  there; `preregistration_guard.py` refuses execution; the NDA grep is the
  third layer.
- Never put OpenAI NDA usage aggregates anywhere in the repo.
- `simulate_power_continuous.py` refuses to run if its cell file contains any
  month at or after the first event. If it refuses, fix the input, not the
  check.

### 0.3 Restricted artifacts

Respondent-level CPS, the detailed crosswalk, the legacy O*NET archive and the
occupation gap audit are **private and must not be committed**. Only sanitized
receipts and aggregate reports belong in git. `audit_standard_freeze.py`
rejects tracked row-level restricted artifacts. See §1.3 — this policy is
currently in direct conflict with a contract, and resolving that is B0.

### 0.4 What "done" means

An item is done when its stated mechanical check passes and a lineage JSON
exists (`python ops/runner/lineage.py <output> <inputs...>`). Not when the code
looks right. Every significant defect this project has had was prose that was
never executed against the data it governs — including in the rewrites that
were fixing earlier instances of exactly that. **Run the rule before believing
it.**

### 0.5 Before you finish any session

```bash
python -m compileall -q .            # a parse error breaks pytest COLLECTION
python -m pytest -q                  # 346 passing, 1 known failure (P1, not yours)
python ops/runner/selfcheck.py
python ops/runner/runner.py --plan
```
`main` once carried a syntax error that broke collection, so CI was green-less
with **zero tests running** and every guard above was unenforced for days.
`compileall` first is not optional.

---

## §1. Verified state, 2026-08-19

### 1.1 Tasks

3 of 17 DAX tasks complete: `DAX-W0-infra`, `DAX-W0.5-feasibility`,
`DAX-GATE-feasibility`. `DAX-GATE1-memo` is not cleared.

### 1.2 What exists

- **W1 memo**: drafted, twice revised, currently amended for the D1 continuous
  design. Independent cross-vendor red team returned `REVISE` / gate `BLOCK`
  with 4 majors on 2026-08-18.
- **W2 price panel**: **done and two-channel verified** — 65 rows, all
  `verified`, zero date-coherence violations. This is the one W2 deliverable
  that is finished.
- **W2 crosswalk**: `build_occ2010_crosswalk.py` + `dose_bounds.py` +
  `audit_standard_freeze.py` built and frozen; outputs deliberately not
  committed.
- **W3**: protocol and adjudication logic built (`dax/mapping/`), embedding
  step not implemented.
- **W4**: `dax/capability_panel/` is **empty**.
- **W5, W6, W10a**: not started.

### 1.3 The clock, and why it reorders the plan

`DAX-W4-panel` depends on `DAX-GATE-feasibility` and `DAX-W3-mapA`. **It does
not depend on `DAX-GATE1-memo`.**

The signed feasibility conditions bind W4 capture of accessible historical model
snapshots to finish **before 2026-10-23 and 2026-12-11**.

> **65 days to the first shutdown. 114 to the second.**

Once a vintage is retired it cannot be captured later, at any price, by any
amount of subsequent work. Gate 1 blocks W5 (index build) — it does **not**
block W4. So:

**The critical path is W2 → W3-mapA → W4, not Gate 1.** These two tracks run in
parallel. If the whole budget goes to Gate 1 and W4 slips past October, the
measurement the chapter is built on is permanently unavailable and no later
effort recovers it.

Track 1 (§3) therefore takes priority on any day both are runnable.

---

## §2. B0 — the blocker that stops both tracks. **Do this first.**

`ops/contracts/dax_built_backbone.yaml` requires four files in
`dax/data_built/`:

```
onet_timeshares.parquet, oews_wages.parquet, cps_extract.parquet, price_histories.csv
```

Only `price_histories.csv` is present. Worse, **`cps_extract.parquet` is
respondent-level CPS microdata**, which §0.3's restricted-artifact policy says
must never be committed. The contract as written therefore **can never pass**,
and `DAX-W2-data` can never complete — which blocks `DAX-W3-mapA`, which blocks
`DAX-W4-panel`, the deadline-critical item.

This is a real contradiction between two rules the project holds
simultaneously, not an oversight to route around.

**B0.1** Split the contract. `dax_built_backbone` keeps the artifacts that may
be tracked; restricted artifacts are represented by **sanitized receipts** with
path, SHA256, row count and build timestamp — the pattern
`occ2010_onet_standard_freeze_receipt.json` already uses. Do not weaken the
restricted-artifact policy to satisfy the contract; change the contract.

**B0.2** Add `ops/contracts/dax_backbone_receipts.yaml` describing the receipt
schema, and a test asserting no `*.parquet` under `dax/data_built/` is
respondent-level.

**B0.3** Re-run `python ops/runner/contracts.py dax_built_backbone dax/data_built/`.

**Done =** the contract passes without any restricted artifact being tracked,
and a test would fail if one were.

**If you disagree** with splitting it, `NEED_HUMAN` and stop. Do not commit
microdata, and do not delete the requirement.

---

## §3. TRACK 1 — deadline-critical (65 days). Highest priority.

### B1. Finish W2's public data
*Precondition: B0.*

Three deliverables, all pre-period, none touching outcomes:

**B1.1 O*NET 2021 vintage task/IWA time-shares** → `onet_timeshares.parquet`.
The 2021 vintage is the frozen primary (memo §0). Annually-updated bundles are
a robustness variant and must be separate, clearly-named files.

**B1.2 OEWS May 2021 occupation wages** → `oews_wages.parquet`. Carry the 2019
baseline as a registered robustness vintage in a separate column or file, never
as a substitute.

**B1.3 CPS extract.** IPUMS extract 6 is already pulled and checksum-recorded
in `dax/memo/power_calcs/ipums_preperiod_extract_receipt.json`. **Reuse it.**
Verify every SHA256 before building and fail closed on mismatch. Only pull a
new extract if a required variable is genuinely absent; if you do, emit a new
receipt in the same shape.

Required columns downstream (`freeze_power_standard.py` will `NEED_HUMAN`
without them): `month`, `age`, the person weight, `employed`,
`hours_unconditional`, and `CPSIDP` for the §7 lookback.

Every file gets a lineage JSON. Every download records agency, table/series ID,
vintage, retrieval timestamp and checksum.

**Done =** `contracts.py dax_built_backbone` passes under B0's split.

### B2. Freeze the static-score ensemble
*Precondition: B1.*

Felten / Eloundou / Webb at occupation level, frozen now so the Decision-8
convergent-validity benchmark (Spearman ≥ 0.50) cannot drift later.

### B3. W3 Mapping A — the embedding step
*Precondition: B1.1. This is the last thing between here and W4.*

`dax/mapping/mapA_adjudication.py` already implements grading, routing,
coverage, the top-quartile flag and the GDPval licence guard, with 14 tests.
`PROTOCOL_mapA_gdpval.md` specifies the rest. **The only missing component is
the embedding.**

**B3.1** Pin an open embedding model. Record name, version, revision hash and
dimension in the run lineage. Pinning matters: a silent upgrade changes every
similarity score and therefore every crossing, with no diff to show for it.
This is left open in the protocol deliberately — decide it now that the O*NET
statements exist, and record the reasoning.

**B3.2** Embed all O*NET task statements and the GDPval open gold subset.
Cosine similarity within occupation-adjacent blocks.

**B3.3** Run grading and routing. Emit `dax/mapping/mapping_a_gdpval.csv` under
`ops/contracts/mapping_a_gdpval.yaml`. **Every O*NET task appears exactly
once** — matched, queued, or unmatched. `route()` partitions; it must not
filter.

**B3.4** Before emitting anything on a release path, call
`assert_release_safe()`. The signed feasibility condition permits GDPval **by
task ID only**; no task text, no derived task content.

**B3.5** Freeze the adjudication order *before* adjudicating: occupation
wage-bill share descending, then `onet_task_id`. Choosing the order after
seeing the queue is not allowed.

**B3.6** If the real similarity distribution is bimodal with a trough far from
the 0.60 floor, the floor should move — **before** any pair is adjudicated,
via a §11 deviation memo with the distribution attached. Moving it afterwards
is specification search.

**Done =** the mapping file passes its contract; coverage table emitted;
adjudication queue populated; no task silently dropped.

### B4. W4 — capability/cost panel. **The deadline item.**
*Precondition: B3. Do not let anything else preempt this after B3 lands.*

Capture accessible historical model snapshots and their measured capability
before the shutdown waves. Order the capture by **shutdown date ascending**, so
the vintages that disappear on 2026-10-23 are captured first and the
2026-12-11 cohort second. Anything still uncaptured on 2026-10-16 should be
escalated, not quietly reordered.

Binding conditions from the signed feasibility gate:
- Retired vintages enter **only** through cited stand-ins, and stand-in
  uncertainty propagates into the EIV analysis.
- `gpt-4.5-preview` is **excluded** — no qualified stand-in was filed.
- The deprecations page carries a provenance conflict for `gpt-4-1106-preview`
  (a 2025-09-26 row saying 2026-03-26, and a 2026-04-22 row saying
  2026-10-23). Both locators are preserved deliberately. **W4 must test actual
  availability rather than trusting either row.**

**B4.1** Availability probe across the registry's `model_ids`, recording for
each: reachable yes/no, timestamp, and the response that establishes it.
**B4.2** Capability measurement per reachable vintage, against the frozen
rubric. Perturbation-robust π uses the registered battery — paraphrase,
reformatting, distractor insertion — applied to task prompts.
**B4.3** A capture receipt per vintage with locator and checksum.
**B4.4** For each unreachable vintage, either a cited stand-in with its
uncertainty, or an explicit `UNKNOWN`. Never an interpolation.

**Done =** every registry model is reachable-and-captured, or has a filed
stand-in, or is `UNKNOWN` with a reason. No gaps, no guesses.

### B5. W3 Mappings B and C
*Precondition: B3. Parallel to B4, lower priority than B4.*

**B5.1 Mapping B (Tolan-style)**: benchmark → ability → task. Document which
public benchmarks feed each ability and how ability scores aggregate to π.
**B5.2 Mapping C (Eloundou-style rescoring)**: write the fixed rubric once;
it must be **identical across model generations**, so all variation comes from
the capabilities being scored rather than from the rubric. Bulk annotation is a
cheap-tier task (`DAX-W3-bulk`, qwen); audit is frontier (`DAX-W3-audit`).
**B5.3 Human validation**: Decision 7 — audit 10% stratified by occupation
family, score decile and ambiguity flag; require weighted Cohen's κ ≥ 0.70 and
≥ 90% agreement on the binary crossing-relevant label **before** W5. Failure
returns the rubric for redesign; it does not lower the bar.

---

## §4. TRACK 2 — Gate 1. Runs in parallel; yields to Track 1.

### A1. Benchmark locator — **PI only, not delegable**

`power_standard.json` currently has `relative_decline: null`,
`version_status: UNRESOLVED`, `locator_status: PENDING_EXCERPT`.
`freeze_power_standard.py` refuses on both, correctly.

Red-team M3 requires one of:
- the headline-figure excerpt from `Canaries_August2026.pdf` (Brynjolfsson,
  Chandar & Chen), with page/section, setting `locator_status: VERIFIED`; or
- `relative_decline: 0.13` with `locator_status: VERIFIED`, sourced to
  `docs/DAX_ERE_Proposal_v3.md:12`.

**Codex must not choose.** 0.19 loosens the pass bar ~46% versus 0.13; choosing
after seeing a marginal result is specification search. If you find this
unresolved, work on Track 1 instead and report it.

### A2. Freeze the power standard
*Precondition: A1 + B1.3.*
```bash
python dax/memo/power_calcs/freeze_power_standard.py --extract <path>
```
One-way. Refuses to overwrite without `--force`, which requires a §11 deviation.

### A3. Identification gate on real dose
*Precondition: a real dose panel. Independent of A1/A2.*

`run_identification_gate.py` exists and **has never been run** — no receipt in
`data_raw/` or `data_built/`. Red-team M1 requires rank and leading share of the
dose matrix **residualized on the full nuisance design**, not the raw matrix.
`residualized_dose_profile()` implements it; on the synthetic fixture only
**23.7%** of dose variance survives absorption, so this may well come back
degenerate on real data.

**Done =** a committed receipt with effective rank, leading share,
`residual_variance_retained`, and the `degenerate` verdict against the
pre-registered thresholds. **If degenerate, apply memo §9.2's pre-registered
consequence** — drop the dynamic claim, argue the index on the crossing
chronology, promote Decision 8 to load-bearing. Do not re-tune the design.

### A4. Person-level power
*Precondition: A2.* Red-team M4 rejects the cell-level "conservative" claim as
asserted rather than proven. Run the estimator at person level and replace the
synthetic results; that is cheaper than proving the bound analytically under
clustering.

### A5. Memo reconciliation — **do this even if everything else stalls**
*No preconditions. Cheap and overdue.*

**A5.1** §7.2 still registers the entrant companion as a **secondary design**.
The real-data audit demoted it: `occupation_level_pi_go_estimable: False`,
**100%** of linked entries in cells below the minimum, 1,623 entries, **16.3%**
CPSIDP link failure. Status is `ENTRANT_COMPANION_DEMOTED_TO_EXPLORATORY` and
the memo contains **zero** occurrences of "exploratory". Rewrite §7.2 and §4's
estimand list with the numbers, state what an exploratory companion may and may
not claim, and **file it as a §11 deviation** — this partially reverses a
counter-signed decision.
**A5.2** Red team requires `event_table_shell_v1.csv`'s continuous columns
populated or explicitly deferred; they are blank with
`w5_fill_status = PENDING_W5_MECHANICAL_FILL`, which is fine, but §1.2 must say
so.
**A5.3** Re-render the PDF (`render_design_memo.py`). `test_pdf_matches_the_memo`
fails if it is stale — PR #35 once shipped a PDF a revision behind its source.

### A6. Re-run the independent red team
*Precondition: A1–A5 all closed. Needs a vendor key and egress.*
```bash
python dax/memo/run_deepseek_red_team.py
```
Packet and prompt are already v2 and tell the reviewer the prior verdict does
not transfer. **Do not run before A1–A5.** Spending the pass on a draft with
known-open majors wastes it.

### A7. Gate 1 — PI only
Only after A6 returns `CONDITIONAL_GO` or `GO` and every evidence-checklist
item is checked. The tag is what unseals `dax/analysis/outcomes/`.

---

## §5. TRACK 3 — after both tracks

### C1. W5 index build
*Precondition: `DAX-GATE1-memo`, `DAX-W4-panel`, `DAX-W3-audit`.*

Emit the full mapping × cost × δ × failure-grid panel, crossing chronology,
event table, flip-rate report, EIV diagnostics, capability-only counterfactual,
distributional variant and live-vintage decomposition. **No configuration may
be dropped because it performs poorly.**

W5 fills only the blank fields of `event_table_shell_v1.csv` — it may not
change event IDs, dates, thresholds or column definitions.

### C2. W6 validation battery
Decision 8 convergent validity; the behavioural first stage under Decision 9;
Decision 13's minimum estimability, which governs the **first stage only** —
its ≥3-events clause does not gate the continuous primary.

### C3. Gate 2, then W10a public release
W10a excludes outcomes, first-stage and NDA material. The NDA CI check is a
release blocker.

---

## §6. Standing rules for this plan

1. **Track 1 outranks Track 2** on any day both are runnable. The October
   deadline is the only irreversible thing in the project.
2. **Never tag, never open outcomes, never commit microdata.**
3. **Thresholds are chosen before the data that judges them.** If you find
   yourself picking a number after seeing a result it will change, stop and
   file a deviation instead.
4. **Two channels for event lists, citations and spec.** A self-review clears
   nothing.
5. **Run the rule before believing it.** Execute every specification against
   the data it governs, and report the disagreement as the finding.
6. **Commit early, hand off through files.** Nothing important lives only in a
   conversation.
7. **`NEED_HUMAN` is a valid outcome.** Stopping with a stated reason beats a
   plausible guess, always.

---

## §7. What only the PI can do

| Item | Why |
|---|---|
| A1 benchmark locator | choosing it after seeing a marginal result is specification search |
| A7 Gate 1 tag | it unseals outcomes |
| §11 deviation approvals | including A5.1, which reverses a counter-signed decision |
| B3.6 similarity-floor change | if the real distribution warrants it |
| Any `--force` re-freeze | one-way by design |

## §8. Known open items not on either track

- `DAX-W0.5-legwork` still advertised READY though `ops/decisions.md` §3 records
  it superseded — it will re-spend if dispatched.
- Stale lease on `DAX-W1-memo`; `make reap`.
- The GitHub PAT flagged in `progress_audit_2026-08-06.md` defect 3 is still
  unrotated.
- CI has no `compileall` step; add one so a parse error cannot again present as
  a test suite that "ran".
