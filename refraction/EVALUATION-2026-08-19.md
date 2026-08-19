# Refraction — quality evaluation and execution caveats, 2026-08-19

Scope: `refraction/` only. Method: run the code, read the artifacts, compare
what is built against `docs/Refraction_执行手册_v1_0.md` and
`docs/MacroEvent_Chapter_Plan_v2_1_FINAL.md`.

## Verdict

**The engineering is the best in the portfolio. The sample it rests on may not
support the design as planned, and that finding is sitting in a JSON file that
nothing reads.**

47 tests pass. The iron rules are machine-enforced and genuinely fail closed.
But the chapter's own sample-scale audit reports a treated sample roughly six
times smaller than the plan assumes, with 90.7% of it in a single wave — and
none of that has been escalated, gated, or recorded as a decision.

---

## 1. What is genuinely good — do not disturb it

- **Iron rules are program invariants, not discipline.** `assert_prereg_ok()`
  refuses while `prereg.osf_timestamp` is null; verified live, it currently
  returns `BLOCKED: prereg.osf_timestamp is empty`. `assert_no_lookahead()`
  encodes A4. This is the same fail-closed pattern as the DAX outcome seal and
  it is correctly built.
- **`frozen_config.yaml` is honest.** `prereg.osf_timestamp`, `prereg.osf_url`
  and `beta.w_shrink` are all genuinely `None`. Nothing has been quietly
  pre-filled to unblock work.
- **A1–A14 all exist.** The README claims 14 panel assertions; all fourteen are
  present in `pipeline/assert_panel.py`. Claim matches code, which is not
  something this repository can be assumed to have.
- **`scan.py` keeps the LLM out of the discovery path** — arXiv and Semantic
  Scholar APIs compute the 毛刺 flag and ALERT threshold *before* any model sees
  a row, and `scan.urlopen` is poisoned in all 23 tests so the suite can never
  touch the network. That is a better test posture than most of the repo.
- **`sample_scale_audit.json` is exemplary.** It quantifies each gap and names
  the plan section it bears on. The problem below is not that this work is bad —
  it is that nothing downstream consumes it.

---

## 2. The finding that dominates everything else

`refraction/sample_scale_audit.json`, run against the real P1 outputs:

| Quantity | Plan v2.1 assumes | Actually available |
|---|---|---|
| conversions | **203** | 131 total rows; **32** equity_US inside the wave window |
| AUM at conversion | **~$260B** | **not populated in a single row** (`aum_populated_rows: 0`) |
| distinct effective dates in window | — | **22** |
| distinct families in window | — | **23** |

And the concentration, which is worse than the headcount:

| | |
|---|---|
| treated stock-waves | 398 |
| distinct waves with any treated stock | **10** |
| waves with ≥10 treated | **2** |
| share of treated mass in wave W002 | **90.7%** |
| treated rows outside W002 | **37**, across 9 waves |

`conv_exp` quantiles: median 0.00024, p90 0.0033, p99 0.0080 — against a
treatment threshold of 0.005. Only the extreme right tail clears the bar.

**What this means.** Inference clusters on `[announcement_date, wave_industry]`.
With 90.7% of treated mass in one wave, the effective cluster count on the
treated side is close to one. This is not a thin panel; it is one event with a
scattering of company. Plan §6 says the design is "few, DFA-heavy" — the audit
supplies the magnitude, and the magnitude is the question of whether the
chapter is estimable at all.

This bears directly on plan §8.1 (drop-DFA robustness), §9 G5 (power) and §10
exit C — the audit says so itself, and nothing has acted on it.

---

## 3. Execution caveats and deviations to fix

### C1. The dominant risk is not a Gate-0 criterion — **fix first**
`gate0_thresholds` contains nine thresholds and **not one of them is a cluster
or wave count**. `effective_cluster_warning_below: 10` exists, but it lives in
the inference block as a *warning*, not in the gate.

Consequence: Gate-0 can pass on a design with effectively one treated cluster.
The single largest threat to the chapter cannot fail its own gate.

**Fix:** promote an effective-cluster / distinct-treated-wave minimum into
`gate0_thresholds` and into R3's `gate_report`, with the number chosen and
signed *before* R3 runs. Choosing it after seeing the report would be
specification search.

### C2. The audit's five flags were never escalated
`sample_scale_audit.json` carries five flags (SCALE, AUM, FILENAME,
CONCENTRATION, PERMNO). None appears in `ops/decisions.md`, none is a
`NEED_HUMAN`, none is a queue node. Grep for `sample_scale`, `90.7`,
`CONCENTRATION` across `ops/` returns nothing relevant.

An audit nothing reads is not a control. **Fix:** file the SCALE and
CONCENTRATION flags as owner decisions with an explicit go/no-go, and add the
audit to whatever R3 consumes so the numbers reach the gate.

### C3. The audit has no verdict field
It reports and flags but never concludes. Every other gate artifact in this
repository states a status. **Fix:** add a `verdict` (`OK` / `DEGRADED` /
`NOT_VIABLE`) computed mechanically from the flags, so a downstream reader
cannot mistake "flags present" for "flags acceptable".

### C4. `permno` is blank on all 6,377 rows
`permno_blank_rows: 6377/6377`. R2's CRSP merge and R10's TAQ pilot both need
it — R10 is listed as blocked on "R2 permno list", which does not exist.
**Fix:** either source a CUSIP→PERMNO bridge as an explicit R2 input with its
own locator, or mark R10 formally parked. It is currently neither.

### C5. The consensus-source `NEED_HUMAN` is not in the DAG
`surprise.consensus_source` is `None`. Surprise standardisation is the core of
a chapter about macro announcement surprises, yet **nothing enforces that the
field is non-null** (grep across `refraction/*.py` returns no reference), and
there is no gate node — the five refraction gates are PREREG, OSF, e2verdict,
R5arb, etfglobal. The README lists it as open NEED_HUMAN #1; the DAG does not
know about it.

**Fix:** add a `REFR-GATE-consensus` node blocking R1a/R2, and a startup check
that refuses when `consensus_source` is null, in the same style as
`assert_prereg_ok()`.

### C6. The R13 scanner has never actually run
`refraction/scans/` contains **only `manifest.md`** — no `hits_*.csv`, no
`seen_ids.json`, no `burr_*.md`. The README says "scanner DONE, triage un-run";
in fact the scan itself has never produced output, because its cron lived on
the box that was dead 2026-07-10 → 2026-08-18. A collision monitor that has
never run has not been monitoring for collisions.
**Fix:** run it once manually, commit the first `hits_*` output, then re-verify
the cron.

### C7. 0 of 25 queue nodes complete, while real work has landed
R0's repo contract and the R13 scanner are both built, tested and committed, but
no queue node is marked done because each node's L1 half is parked on the kimi
bench decision. The runner therefore shows refraction as untouched, which is
false and will mislead any planner reading `make plan`.
**Fix:** split the affected nodes, or record the parked halves explicitly, so
the queue reflects reality.

### C8. Filename drift, minor but load-bearing
Plan §4/§5 name `conv_exposure.parquet`; the built file is
`p1/conv_exposure_free.parquet`. Harmless until someone writes a path from the
plan. **Fix:** one line in the plan or a documented alias.

---

## 4. What I would do, in order

1. **Answer `REFR-GATE-e2verdict`.** It has been open for weeks and sets
   whether refraction takes E2's slot. Twenty-five tasks wait behind a decision
   that costs one sentence.
2. **Take C1 and C3 before R3.** A gate that cannot fail on the design's
   dominant risk is worse than no gate, because it will be cited as passed.
3. **Escalate C2 as an owner decision.** The honest question is whether a
   chapter whose treated mass is 90.7% one wave should proceed as designed,
   proceed as a single-event case study with matching claims, or wait for more
   conversions. That is a research-agenda call, not an agent's.
4. **Then C5, C4, C6** — all mechanical.

**Nothing here is a code-quality problem.** The code is careful, tested and
fail-closed. The problem is that a first-rate measurement instrument has been
pointed at a sample the plan over-estimated by roughly six times, and the
instrument's own report of that fact is not wired to anything that can stop the
work.

---

# 5. Decisions taken, 2026-08-19 (delegated — override any of them)

Recorded in `ops/decisions.md` as R-DEC-1…6.

| # | Decision | Reversible? |
|---|---|---|
| R-DEC-1 | Concentration becomes a Gate-0 line: `treated_waves_min: 10`, `largest_treated_wave_share_max: 0.5`, with a pre-registered consequence | yes, but not by relaxing the threshold |
| R-DEC-2 | `wave_id` added to `inference.cluster_dims` | yes |
| R-DEC-3 | `REFR-GATE-consensus` added (blocks R1b) + `assert_consensus_source()` refuses while null | yes |
| R-DEC-4 | `sample_scale_audit` emits a mechanical verdict | yes |
| R-DEC-5 | `REFR-GATE-e2verdict` cleared as deferred-priority — unblocks R5+ | trivially |
| R-DEC-6 | `REFR-GATE-etfglobal` failed, parking the R9 bypath | trivially |

**The threshold in R-DEC-1 is not a number I chose.** It is
`inference.effective_cluster_warning_below`, already registered in
`frozen_config.yaml`, promoted from a warning to a gate. Picking a new number
after seeing 90.7% would have been specification search; promoting the
project's own registered concern level is not.

**Mechanical verdict as it now stands: `NOT_VIABLE_AS_PANEL`** — and precisely
so. `treated_distinct_waves = 10` sits exactly at the minimum and *passes*; it
is `largest_wave_share_of_treated = 0.907 > 0.5` that fails. The count is
borderline; the concentration is not.

## What I deliberately did not decide

**Whether the chapter proceeds.** R-DEC-1 makes that question *decidable* and
pre-registers the consequence; it does not answer it. The live options are:

1. **Single-event study.** Own W002 as the event, scope every claim to it, drop
   the multi-wave panel language. Honest, publishable, smaller.
2. **Wait for conversions.** The wave window ends 2025-12-31; more conversions
   may accumulate. Costs time, changes nothing structural.
3. **Re-scope the treatment threshold.** `convexp_treated_min = 0.005` against a
   p99 of 0.008 is why the treated set is thin. Lowering it widens the sample —
   **but doing so now, having seen that 0.005 fails, is specification search.**
   If it is considered, it needs a signed amendment arguing the threshold on
   economic grounds, not on the sample it produces.

Option 3 is the tempting one and the one to be most careful with.

**The E2 research verdict.** R-DEC-5 clears a *scheduling* gate, nothing more.
No judgment about E2's merit is recorded or implied.

## Still open after these decisions

- `REFR-GATE-consensus` — name and license the CPI/NFP consensus channel.
  Now blocks R1b in the DAG instead of sitting in a README.
- C4 `permno` blank on all 6,377 rows — R10's stated input does not exist.
- C6 the R13 scanner has still never produced output; run it once by hand and
  commit the first `hits_*` before trusting the cron.
- C7 the queue still shows 0/25 while R0 and R13 have landed.
