# DAX execution plan — 2026-08-19

**Scope note (2026-08-19):** this was requested as a DAX plan. Sections 1, 2
and 4 are DAX. Section 5 lists P1/E2/refraction only as parallel context so a
DAX executor does not collide with them — it is not their plan. Refraction has
its own evaluation at `refraction/EVALUATION-2026-08-19.md`.

Written to be executed by an agent with no memory of this session. Every item
states its owner, its precondition, what "done" means mechanically, and what to
do when it cannot be done. Follow `CLAUDE.md` meta-rules throughout; where an
item conflicts with them, the meta-rules win and you emit `NEED_HUMAN`.

---

## 1. Where the portfolio actually is

| Project | Tasks done | Total | Notes |
|---|---|---|---|
| **DAX** | 3 | 17 | At Gate 1, **blocked**. Highest priority, highest ceiling. |
| **P1** | 10 | 21 | Furthest along. T1/T2 done; T3 spec is next and is seat-C blocked. |
| **E2** | 3 | 20 | T1 facts done, T4a design ready and unstarted. |
| **Refraction** | 0 | 25 | Untouched. Two human gates waiting. |
| shared | 2 | 3 | fine |

Gates cleared: `P1-GATE-t2a`, `DAX-GATE-feasibility`, `P1-T1-spotcheck`,
`P1-T2-killswitch`. **`DAX-GATE1-memo` is not cleared and is the portfolio's
critical path.**

Test suite: 340 passing, 1 failing (§6.1). `selfcheck` passes, 86 tasks,
22 contracts. Outcome seal intact — no `v1.0-preregistered` tag, nothing under
`dax/analysis/outcomes/`.

---

## 2. Deviations from the original plan

The original month-by-month schedule (`docs/DAX_Execution_Plan_with_AI_Agents.md`
§5) puts **Gate 1 — memo tagged** in Month 2. Calendar-wise that is now. The
memo is drafted and heavily revised, but Gate 1 is blocked, and the reasons are
substantive rather than schedule slippage.

**D-1. The DAX primary specification changed.** The registered design was a
stacked event study with clean windows. Executing §3.2 against its own registry
left **2 estimable events** from 4 eligible rows, and **1** if the registry is
completed — below the 3 the power engine requires. The rule was also
non-monotone: better evidence made identification worse. Replaced on 2026-08-18
(D1, PI counter-signed) with a continuous cumulative-dose design; the stack
survives as secondary corroboration. This is the largest deviation in the
portfolio and it is documented in `PI_DECISION_D1_2026-08-18.md`.

**D-2. The power standard was redefined.** Decision 11's bar was
`min(6.5pp, ½ × baseline_gap)` where the gap is estimated from the sample being
judged — dropping one event loosened the bar 185% while the estimator got 19%
worse. Replaced by a frozen external constant (D3).

**D-3. The entrant companion was approved, then demoted by evidence.** The PI
counter-signed D4 Part 2 (registered secondary). The real-data audit
(`dax/data_raw/entrant_companion_audit_receipt.json`) then found:
`occupation_level_pi_go_estimable: False`; **100%** of linked entries sit in
cells below the minimum count; median pairs per cell **1**; only **1,623**
linked labour-market entries; CPSIDP link failure **16.3%**. Status is now
`ENTRANT_COMPANION_DEMOTED_TO_EXPLORATORY`.
**The memo has not been updated** — §7.2 still registers it as a secondary
design (0 occurrences of "exploratory" in `design_memo_v1.md`). This is the
project's recurring failure mode: prose that no longer matches the evidence.

**D-4. The benchmark figure moved 0.13 → 0.19 without a locator.** PI-directed;
`power_standard.json` carries `locator_status: PENDING_EXCERPT`. The
independent red team's M3 blocks Gate 1 on exactly this.

**D-5. Gate 1 returned BLOCK.** The cross-vendor red team
(`red_team_deepseek_v4_pro_rerun_20260818_round3.json`) returned
`verdict: REVISE`, `gate_recommendation: BLOCK`, 4 major issues. This is
progress — the review is now evidence rather than absence — but Gate 1 is
further away than it looked.

**D-6. The crosswalk approach changed.** A naive equal-split builder was
replaced by `build_occ2010_crosswalk.py`, which preserves unresolved components
at original weight and emits `dose_min`/`dose_max` intervals. Restricted
artifacts deliberately stay out of git.

**D-7. Two infrastructure failures cost real time.** The box was dead
2026-07-10 → 2026-08-18 (39 days), so the entire L1 overnight layer produced
nothing and every "the batch will handle it" assumption in the plan was false.
Separately, `main` carried a syntax error that broke pytest **collection**, so
CI was red with **zero tests running** and every repo guard was unenforced.
Both are fixed. Neither was detected by the plan's own controls.

**D-8. Refraction has not started.** 25 tasks, 0 done, and two human gates
(`REFR-GATE-e2verdict`, `REFR-GATE-etfglobal`) have been waiting. The original
portfolio ordering treats refraction as contingent on the E2 verdict, so this
may be intentional — but it should be an explicit decision, not drift.

---

## 3. Critical path

Everything below Gate 1 is DAX. Nothing in W3/W4/W5 should be *completed*
before Gate 1, but the items in §4 are all pre-gate legal: they use pre-event
data only, and none opens `dax/analysis/outcomes/`.

```
A1 benchmark locator ─┐
A2 freeze standard ───┼─► A4 person-level power ─┐
A3 identification gate┘                          ├─► A6 re-run red team ─► GATE 1
A5 memo reconciliation ──────────────────────────┘
```

---

## 4. DAX — the Gate 1 sequence (do these in order)

### A1. Resolve the benchmark locator — **blocks A2, blocks Gate 1**
*Owner: PI (human). Not delegable.*

Red-team M3 requires one of:
- supply the headline-figure excerpt from `Canaries_August2026.pdf`
  (Brynjolfsson, Chandar & Chen), set `benchmark.locator_status: VERIFIED` and
  record page/section; **or**
- revert `relative_decline` to `0.13` with `locator_status: VERIFIED`, sourced
  to `docs/DAX_ERE_Proposal_v3.md:12`.

Do **not** let an agent choose. 0.19 loosens the pass bar ~46% versus 0.13, so
choosing after seeing a marginal result is specification search.
`freeze_power_standard.py` already refuses while `version_status != RESOLVED`;
add the same refusal on `locator_status != VERIFIED`.

**Done =** `power_standard.json` has `locator_status: VERIFIED` with a page cite.

### A2. Freeze the power standard
*Owner: seat A. Precondition: A1, plus `dax/data_built/cps_extract.parquet`.*

```bash
python dax/memo/power_calcs/freeze_power_standard.py \
    --extract dax/data_built/cps_extract.parquet
```
It is one-way and refuses to overwrite without `--force`. If the extract lacks
`month`, `age`, the weight column, `employed`, or `hours_unconditional`, it
emits `NEED_HUMAN` — fix the extract, do not relax the check.

**Done =** `status: FROZEN`, both ceilings non-null, provenance carries the
extract SHA256 and person-record count.

### A3. Run the identification gate on real dose
*Owner: seat A. Precondition: W2 dose panel exists. No dependency on A1/A2.*

`run_identification_gate.py` exists but **has never been run** — there is no
receipt in `data_raw/` or `data_built/`. Red-team M1 requires the rank and
leading share of the dose matrix **residualized on the full nuisance design**
(occupation, month, industry×month, static-decile×month), not the raw matrix.
`residualized_dose_profile()` in `simulate_power_continuous.py` implements it;
on the synthetic fixture only **23.7%** of dose variance survives absorption.

**Done =** a committed receipt reporting effective rank, leading share,
`residual_variance_retained`, and the `degenerate` verdict against the
pre-registered thresholds (leading share > 0.95, retained < 0.01, rank ≤ 1).
If it comes back degenerate, apply memo §9.2's pre-registered consequence —
drop the dynamic claim, do not re-tune the design.

### A4. Person-level power run
*Owner: seat A. Precondition: A2, CPS extract.*

Red-team M4 rejects the cell-level approximation's "conservative" claim as
asserted rather than proven. Either run the estimator at person level and
replace the synthetic results, or prove the upper-bound analytically under
clustering. Running it is cheaper than proving it.

**Done =** `power_results_continuous.json` regenerated from the real extract
with `status` no longer `NOT_EVIDENCE_SYNTHETIC_SMOKE_TEST`, and
`adequately_powered` non-null for pooled and both education splits.

### A5. Reconcile the memo with the evidence — **do not skip**
*Owner: seat A. No preconditions. Cheap and overdue.*

Three known memo-versus-evidence divergences:

1. **§7.2 still registers the entrant companion as a secondary design.** The
   audit demoted it to exploratory. Rewrite §7.2 to state the demotion, the
   numbers behind it (π_go not estimable at occupation level, 100% of linked
   entries below minimum cell count, 1,623 entries, 16.3% link failure), and
   what an exploratory companion may and may not claim. Update §4's estimand
   list and `PI_DECISIONS_OPEN.md`. **This reverses part of a PI-counter-signed
   decision, so file it as a §11 deviation with the receipt as evidence.**
2. Red team requires `event_table_shell_v1.csv` continuous columns to be
   *populated or explicitly deferred* — they are currently blank with
   `w5_fill_status = PENDING_W5_MECHANICAL_FILL`, which is fine, but §1.2 must
   say so.
3. Confirm §9.2's degeneracy consequence and §7.4's approximation caveat still
   match the code after A3/A4 land.

**Done =** `python dax/memo/validate_w1_readiness.py` blockers reduce to only
those genuinely outstanding, and the PDF is re-rendered
(`render_design_memo.py` — `test_pdf_matches_the_memo` fails if it is stale).

### A6. Re-run the independent red team
*Owner: seat A, on a host with a vendor key and egress. Precondition: A1–A5.*

```bash
python dax/memo/run_deepseek_red_team.py
```
Packet and prompt are already v2 and tell the reviewer the prior
`CONDITIONAL_GO` does not transfer. **Do not run it before A1–A5** — spending
the pass on a draft with known-open majors wastes it.

**Done =** a round-3 receipt with `gate_recommendation` of `CONDITIONAL_GO` or
`GO`. If it returns `BLOCK` again, treat the new majors as the next A-list and
do not tag.

### A7. Gate 1
*Owner: PI. Precondition: A6 clean, all evidence-checklist items checked.*

Only then create `v1.0-preregistered`. The tag is what unseals
`dax/analysis/outcomes/`; nothing may pre-empt it.

---

## 5. Work that runs in parallel (does not touch the Gate 1 path)

### B. P1 — `P1-T3-spec` (seat C)
Ready and currently the binding P1 item; `P1-T4-replication` waits behind it.
Channel B (`P1-T3-spec-B`, DeepSeek reasoning) is an L1 batch and needs the box.
P1 is the portfolio's most advanced project and should not stall while DAX is
gated.

### C. E2 — `E2-T4a-design` (seat B)
READY, unblocked, unstarted. **No brief exists** — writing one into
`ops/briefs/` is the first act of that session, per the working protocol.

### D. Refraction — decide, do not drift
Two human gates have been open for weeks. `REFR-GATE-e2verdict` sets priority
either way (rejected → refraction takes E2's slot; approved → 4th-paper
cadence). Answer it so the 25 blocked tasks either start or are formally
parked.

### E. L1 overnight batches (needs the box)
`P1-T0-monitor`, `P1-T13-ant` + `-B`, `E2-T2-dune`, `E2-T6b-nav`,
`REFR-R0-collide` + `-B`, `REFR-R1a-verify`, `REFR-R13-scan`,
`REFR-R14-metaqa`, `SH-l1-smoke`. All were dark for 39 days. Before trusting
them again run `make smoke` (`SH-l1-smoke`) and confirm a sentinel batch
completes end-to-end.

---

## 6. Housekeeping that is small and keeps biting

### 6.1 One failing test — a real schema decision (seat C)
`p1/tests/test_build_nport_convexp.py::test_sidecar_is_written_alongside_need_human`.
Two writers (`_write_dropped_cells`/`valusd` and `_write_dropped_sidecar`/`val_usd`)
target the **same path** via two constants, so they collide; two test files
encode both; and `_cell_rows` emits **both spellings** depending on code path
(lines 573/713 vs 602/635). The real consumer, `recover_denominators.py:206`,
reads **by name**, which disproves the sidecar docstring's column-order
rationale. Fix `_cell_rows` to one spelling, delete the losing writer, its
constant and its test. Full evidence in
`p1/output/convexp_coverage_audit/README.md`.

### 6.2 Close `DAX-W0.5-legwork`
`ops/decisions.md` §3 records it superseded by owner-run inline legwork, but
the runner still advertises it READY and will re-spend on it.

### 6.3 Reap stale leases
`DAX-W1-memo` still shows in flight. `make reap` runs on the box's 30-minute
tick, which is why it never cleared.

### 6.4 Rotate the GitHub PAT
Flagged in `progress_audit_2026-08-06.md` defect 3; a token was subsequently
pasted into a chat session. Still outstanding.

### 6.5 Add a CI guard against the failure that hid everything
A syntax error broke pytest **collection**, so CI was red with zero tests run
and no guard was enforced. Add a step that compiles every tracked Python file
(`python -m compileall -q`) **before** pytest, so a parse error is reported as
a parse error instead of masquerading as a test suite that "ran".

---

## 7. Standing rules for whoever executes this

1. **Do not create `v1.0-preregistered`** except at A7, by the PI.
2. **Do not open or create `dax/analysis/outcomes/`.** Three layers enforce
   this; do not work around any of them.
3. **Do not freeze the power standard** until A1 is `VERIFIED`. Freezing is
   one-way.
4. **Numbers need locators.** No figure from model memory — code you ran on
   real data, or an extraction with a raw-source locator. If neither exists,
   emit `NEED_HUMAN` and stop.
5. **Two channels for high-hallucination work** (event lists, citations,
   spec). A self-review never satisfies this and never clears a gate.
6. **When prose and code disagree, that is the finding.** Every significant
   defect in this project has been prose that was never executed against the
   data it governs. Run the rule before believing it.
7. **Commit early, hand off through files.** Nothing important should exist
   only in a conversation.
