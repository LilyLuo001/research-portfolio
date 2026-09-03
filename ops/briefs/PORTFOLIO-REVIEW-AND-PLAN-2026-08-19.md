# Portfolio review + execution plan — 2026-08-19

_Seat C, written against the repo as it stands at commit `81dc3f3` on
`claude/p1-continuation-zgdcem`. Every claim below was checked in the container
today: file listings, `git log`, `make plan`, `pytest`, and reads of the plan
docs. Nothing is carried over from another session's word._

**Audience: the next execution agent.** Part 1 is the state you are inheriting.
Part 2 is what went wrong structurally. Part 3 is the ordered work queue — start
there if you only read one section.

---

## Part 0 — the 60-second version

| | |
|---|---|
| **Health** | 328/328 tests pass. Runner self-consistent. No corrupt artifacts. |
| **Registered progress** | 18 of 86 queue tasks complete (21%). Unchanged on `main` since 2026-07-10. |
| **Real progress** | Materially higher than 18 — roughly 8 tasks' worth of finished work is unregistered or unmerged. |
| **Single worst problem** | The 24/7 box has been dead 40 days. It is the portfolio's entire automation lane. |
| **Second worst** | Four projects are running, not three. CLAUDE.md still says three. |
| **Strongest asset** | P1 has real data: 131 conversion events, 6,377 stock-wave cells, 389 treated stocks at ≥0.5%. |
| **Most at risk** | E2 — zero commits in 40 days, entirely dependent on the dead lane. |
| **Nearest publishable thing** | P1 spine-two, if a WRDS window is booked. |

---

# Part 1 — where each project actually is

## Portfolio-level facts

- **86 tasks** in `ops/runner/queue.yaml` across p1 / e2 / dax / refraction / shared.
- `make plan` reports: `completed=18 ready=18 in_flight=1 gated=2 blocked=47`.
- **Test suite: 328 passed** (repo-wide, ~31s). No failures, no skips of note.
- **No git tags exist at all.** `v1.0-preregistered` — the tag the DAX outcome
  seal depends on — has never been created. `dax/analysis/outcomes/` does not yet
  exist, so the CLAUDE.md prohibition is currently moot, but the seal it protects
  is also not yet armed.

### Seat map (`ops/accounts.yaml`)

| Seat | Owns | Reality |
|---|---|---|
| A | `dax/` | Active — six unmerged branches from 08-18/19 |
| B | `e2/` | **Dormant 40 days** |
| C | `p1/`, `refraction/` | Active — this session |
| D | `shared/`, `ops/` | Dormant since 07-10 (this is the box's owner) |
| E | roving writer | Never activated |

---

## P1 — fund conversions ⭐ *strongest*

**Registered: 18 tasks complete. Real state: further along than that.**

Built and committed, with lineage:

| Artifact | Content |
|---|---|
| `events_merged.csv` | 131 conversion events, EDGAR accession + URL per row |
| `conv_exposure_free.parquet` | 6,377 stock-wave cells, 13 columns |
| — treated ≥0.5% | **389 distinct stocks** (398 stock-wave cells) |
| — treated ≥1% | 24 distinct stocks (27 cells) |
| `waves.csv` / `waves_members.csv` | 78 waves / 131 members; DFA anchor W002 = 2021-06-11 |
| `t2a_power_results.json` | Conservative MDE80 = 0.159σ worst cell — all three dose tiers pass |

Gates cleared: `P1-GATE-t2a`, `P1-T1-spotcheck`, `P1-T2-killswitch`.

Completed this session but **not registered in `state.json.completed`**:
B1 (3 schema contracts), B2 (panel-integrity guard), B3 (spine-two outcomes
builder + 18 tests), B4 (Russell fallback check), B5 (ConvExp reconciliation
harness), A1 (文献包 — 10 papers, URL-locatable), A3 (Saglam–Tuzun stub),
**T3-spec channel A** (`p1/t3_spec/变量规格书.md`, contract PASS).

**Blocked on:**
1. **WRDS access — gone.** BU access lapsed (`ops/briefs/WRDS-access-assessment.md`).
   Gates T3-impl, T4, T5, T7. The free EDGAR path was built as a substitute for
   ConvExp only; every *outcome* variable still needs CRSP/TAQ/IBES/Compustat.
2. **Egress** — blocks `recover_denominators.py --online` and the Saglam–Tuzun PDF.
3. **T3-spec channel B** — needs the DeepSeek lane (i.e. needs the box).
4. **Owner decision, international sleeve** — costed and waiting since 08-18.
   Option A / A-strict / A + fund-level rebuild. Mirae W020 alone is 49% of all
   dropped cells. **Must be fixed before T5 or it becomes specification search.**

## DAX — AI exposure

**Registered: 3 complete. Real: much further, but stranded on branches.**

Advanced: all 17 PI design decisions APPROVED (2026-08-06); D1/D3/D4/F2
amendments counter-signed 08-18; event registry at 21 rows (20 date-verified);
crosswalk at 1,287 mapping rows / 503 CPS codes; price panel at 20 verified rows.

**Six branches from 08-18/19 are unmerged**, superset =
`task/DAX-w5-dose-panel-20260819` (7 commits ahead of main).

**Hard blocker, self-recorded** in `dax/data_raw/w5_dose_panel_blocker_receipt.json`:
`status: BLOCKED_MISSING_FROZEN_W3_W4_INPUTS`

- `mapping_a_gdpval` → `NOT_EXECUTED`. The protocol is committed; the embedding
  and adjudication run never happened.
- `w4_capability_cost_panel` → `MISSING`. No frozen artifact anywhere.
- Consequence: dose cannot be constructed. The receipt correctly refuses to
  substitute static scores. **This is the DAX critical path and it is one task
  deep: W3-mapA.**

Gate-1 evidence still owed: CPS/IPUMS extract (blocks the frozen power standard —
`power_standard.json` ships as `PLACEHOLDER_REQUIRES_REAL_CPS`); a *fresh*
cross-vendor red team (the DeepSeek CONDITIONAL_GO was on the superseded discrete
design and explicitly does not transfer); the `Canaries_August2026.pdf` excerpt
for the PI-directed 0.19 constant (`locator_status: PENDING_EXCERPT`); PI line-by-line
PDF review. Open red-team items: **M3** (entry mix estimability) and **M4**
(entrant sample conflates true entrants with CPSIDP linkage failures).

## E2 — RWA looping ⚠️ *at risk*

**Registered: 3 complete. Real: unchanged since 2026-07-10 — 40 days dead.**

Exists: `registry.csv` (17 assets, owner-signed 07-10, three residual risks
accepted), `build_panel.py` + `assert_panel.py` (A1–A15 battery passing) — but the
panel runs on `synth_inputs()`, self-documented as scaffolding. `main`'s own
`_note` says so: *"E2-T6a is NOT marked complete: build_panel.py is synthetic-input
scaffolding."*

**Blocked on:** `E2-T2-dune` (Dune SQL, deepseek lane) — 1 recorded failed attempt,
never retried. Everything downstream (T3 → T5 → T6a → T7 → T15 note) waits on it.
E2's fastest publishable artifact was the T15 note; that path has not moved in 40 days.

E2 is the project most damaged by the dead box, because nearly its whole chain is
L1-dispatched rather than seat-driven.

## refraction — macro-event standby chapter

**Not in CLAUDE.md.** 14 REFR tasks in the queue, seat C, `docs/Refraction_执行手册_v1_0.md`.

Landed: `frozen_config.yaml`, `guards/prereg_guard.py`, `pipeline/assert_panel.py`
(14 asserts), `scan.py` R13 resident collision monitor (23 tests), 5 contracts.
R6+ is **guard-blocked by design** until an OSF timestamp exists — correct behaviour.

Blocked on: R1b (needs the L1 lane), CRSP table list (same WRDS wall as P1), and
five open NEED_HUMAN items including the CPI/NFP consensus license and ETF Global
access. Two human gates parked: `REFR-GATE-e2verdict`, `REFR-GATE-etfglobal`.

Note `REFR-GATE-e2verdict` — refraction is *designed* to wait on an E2 verdict.
E2 being dead therefore silently blocks refraction too.

## shared — infra

`SH-runner` + `SH-econlib` complete and merged; econlib carries stacked DiD,
Callaway–Sant'Anna, wild cluster bootstrap, randomization inference, event study.
This is the one part of the portfolio that is finished and working.

---

# Part 2 — deviations from the original plan

Ordered by how much damage each is doing.

### D1 — the 24/7 box is dead. 40 days. ⛔ *root cause of most of the rest*

`docs/Agent_Architecture_24x7.md` puts a free/cheap L0+L1 lane underneath five
human seats: it reaps leases, dispatches overnight batches, and pushes a digest.

Last `portfolio-box` commit: **2026-07-10T12:30Z**. Nothing since.

Evidence it was already failing before it stopped — from `ops/box/l1_manual.log`:
- `E2-T1-facts` — VOID-SENTINEL ×2 (Kimi returned no parseable JSON) → escalated
- `E2-T9b-scenarios` — VOID-SENTINEL, truncated at the output-token cap → attempt 3, escalated
- Spend `2.910 / 70` daily cap. The lane was barely drawing budget.

Consequence: **all 15 L1-ready tasks in `make plan` are unreachable.** The plan's
premise — "expensive gates, cheap runs", L1 grinds overnight while seats sleep —
is not in force. Everything is being done by hand on L2 seats, which is exactly
the failure mode the architecture was designed to prevent.

This is one dead VPS masquerading as four stalled projects.

### D2 — `state.json` no longer describes the repo

`completed` is byte-identical on `main` and this branch: 18 entries, last touched
07-10. Since then B1–B5, A1, A3 and T3-spec-A have all landed as *files* with
passing contracts, but no `runner.py --complete` was ever called.

CLAUDE.md defines done as: *contract passes + lineage emitted → merge to main →
`runner.py --complete`*. The last two steps have been skipped repeatedly.

`decisions.md` even flags this against itself at line 482: *"the queue's
bookkeeping is stale against the repo."*

Cost: `make plan` still lists `P1-T3-spec` as a ready task I finished today, and
still lists `DAX-W2-data` as seat A's next move when DAX has run past it to W5. A
fresh agent reading `make plan` will redo finished work. **This is the most
expensive deviation for you specifically.**

### D3 — four projects, not three

CLAUDE.md's first line says three papers. `refraction/` is a fourth, with 14 queue
tasks, its own manual, its own contracts and its own seat-C claim — and seat C also
owns P1. The two are declared never to need heavy L2 blocks simultaneously; that
held only because refraction is parked behind a gate.

### D4 — merge discipline has lapsed

14 branches carry unmerged commits. Six are DAX work from the last 48 hours; the
integration branch `task/DAX-w5-dose-panel-20260819` is 7 ahead of main. Three
branches (`admiring-carson`, `box-bootstrap-smoke-test`, `research-portfolio-review`)
are 22–48 commits ahead but 183 behind — effectively abandoned, and nobody has
decided whether anything in them is worth salvaging.

The architecture's core claim is *"the repo state is the only shared state."*
With work spread over 14 branches, there is no single shared state.

### D5 — DAX front-loaded design and skipped the input it depends on

Seventeen PI decisions, four counter-signed amendments, a red-team round, a memo
and a PDF — all before `W3-mapA` (the mapping the entire dose measure is built from)
was ever executed. The W5 receipt is the bill arriving: `NOT_EXECUTED`.

To the pipeline's credit it **failed closed** rather than substituting static
scores. That is the guard working exactly as designed. But months of design effort
now sit on top of a missing input.

### D6 — dual-channel is half-enforced

Meta-rule 2 requires two vendor families on high-hallucination tasks. Channel A
exists for P1-T3-spec (mine, today); channel B is a DeepSeek task on the dead lane.
Same for `P1-T13-ant`/`-B`, `REFR-R0-collide`/`-B`. The runner still certifies
*"cross-vendor independence: all dual-channel pairs use distinct families"* — true
of the *configuration*, and misleading about *execution*, because the B channels
cannot run at all.

### D7 — one owner decision is now on the critical path for research integrity

The international-sleeve question (P1-T2 audit item 5) has been costed and waiting
since 08-18. Meta-rule "never specification-search" means the sample definition
must be frozen **before** T5 estimation. If WRDS arrives before this is answered,
there will be pressure to choose the sample after seeing outcomes. Answer it while
it is still cheap and unfalsifiable.

### D8 — what has *not* deviated (keep these)

Worth stating plainly, because the discipline here is unusually good and should
not be traded away under schedule pressure:

- Meta-rule 1 held. Every number I checked carries an EDGAR accession, a WRDS
  query locator, or a URL. `[NEED_PDF]` / `NEED_HUMAN` markers are used honestly
  instead of guess-filling.
- Fail-closed guards fired correctly (DAX W5 receipt; refraction R6 prereg guard;
  the WRDS loader refusing invented table names).
- The outcome seal held — no DAX outcome was opened.
- Test coverage is real: 328 tests, including tampered-world fixtures that must fail.

---

# Part 3 — execution plan

Rules for the executing agent:

- Work the phases **in order**. Phase 0 is not optional — later phases assume it.
- One task per session; `/clear` between tasks (CLAUDE.md).
- Branch `task/<id>`; touch only your seat's `owned_paths`; `shared/` is read-only
  unless you are seat D.
- Definition of done, in full: **contract passes → lineage JSON emitted → merged to
  main → `runner.py --complete <id>`.** Skipping the last two is what caused D2.
- If you don't know: emit `NEED_HUMAN: <reason>` and stop. Never guess-fill.
- Never specification-search. Report the first run.

---

## PHASE 0 — restore the ability to make progress (do first, blocks everything)

### P0-1 · Reconcile `state.json` with the repo — seat D — ~1 block
**Why:** D2. Until this is done, every agent reading `make plan` gets a false map.

Verify each of these has a passing contract and a lineage JSON, then register it:

```bash
python ops/runner/contracts.py variable_spec p1/t3_spec/变量规格书.md
python -m pytest -q                      # expect 328 passed
python ops/runner/runner.py --complete P1-T3-spec
```

Then audit every entry in `queue.yaml` against the filesystem and register any
other task whose output exists and passes. Record the reconciliation in
`ops/decisions.md`.

**Acceptance:** `make plan` no longer lists any task whose output is already
committed and contract-passing.

**Do not** mark complete: `P1-T3-spec-B` (never ran), `E2-T6a` (synthetic inputs),
anything in DAX W3/W4/W5 (blocked receipt stands).

### P0-2 · Merge the DAX branch backlog — seat A — ~1 block
**Why:** D4. Seven commits of finished DAX work are invisible to everyone.

Merge `task/DAX-w5-dose-panel-20260819` (the superset — verify with
`git log origin/main..origin/<branch> --oneline` before trusting that label) into
`main`. Run `python -m pytest -q` before and after. The other five DAX branches are
ancestors; confirm and delete them.

**Acceptance:** `main` contains the W5 blocker receipt and its tests; DAX branch
count drops to zero.

### P0-3 · Decide the fate of the box — **OWNER**, then seat D — ~1 block
**Why:** D1. This is the highest-leverage item in the document.

The owner must pick one:

- **(a) Revive it** — `ops/box/README.md` has the full runbook: clone, venv,
  `ops/box/setkeys.sh`, `python ops/runner/dispatch.py --workers` to prove keys
  are live, `--smoke` to prove the fence works, then install `ops/box/crontab`.
- **(b) Replace L1 with seat time** — accept that 15 L1 tasks become manual L2
  work, and re-plan capacity accordingly. E2 and refraction get much slower.
- **(c) Formally park E2** — if neither (a) nor (b) is affordable, say so in
  `ops/decisions.md` rather than leaving E2 to rot silently for another 40 days.

Two things to fix *before* re-enabling, both already diagnosed in the log: Kimi
returns unparseable JSON on `E2-T1-facts`, and hits the output-token cap on
`E2-T9b-scenarios`. Reviving without addressing these just reproduces the failures.

**Acceptance:** either `make smoke` passes on the box and a digest commit appears,
or a dated decision recording (b) or (c).

### P0-4 · Answer the international-sleeve question — **OWNER** — ~10 minutes
**Why:** D7. Cheap now, contaminating later.

Read `p1/output/convexp_coverage_audit/international_sleeve_options.md`. Answer
with one line in `ops/decisions.md`: **Option A**, **A-strict**, or
**A + fund-level rebuild**.

Numbers you already have (distinct stocks, the audit's convention): the DFA anchor
wave W002 is `no_intl`, so it survives every option. At the ≥0.5% line — the line
Gate 2 was read on — the sleeve is nearly free to drop: **389 → 381** under Option A
(−2%), against a power floor of ≥33. The ≥1% line is where it bites: 24 → 21 under
Option A, but **24 → 16** under A-strict.

**This must be recorded before T5 runs.**

### P0-5 · Update CLAUDE.md for four projects — seat D — ~15 minutes
**Why:** D3. Add refraction to the opening paragraph and the ownership table so a
fresh seat isn't surprised by a project that doesn't officially exist.

---

## PHASE 1 — unblock the two critical paths (parallel; different seats)

### P1-A · Execute DAX W3-mapA — seat A — 1–2 blocks 🔴 *DAX critical path*
**Why:** D5. Named by the W5 receipt as `NOT_EXECUTED`; nothing else in DAX can move.

Protocol is committed at `dax/mapping/PROTOCOL_mapA_gdpval.md`; the adjudication
code is `dax/mapping/mapA_adjudication.py`; `dax/tests/test_mapA.py` exists. Run
the embedding + adjudication, then **freeze** the output with version, SHA-256, row
count and adjudication status — the receipt requires all four.

Then `DAX-W3-audit` (10% stratified; κ ≥ 0.70 and binary agreement ≥ 90%, per
approved Decision 7).

**Acceptance:** `mapping_a_gdpval.csv` exists, frozen, with lineage; re-running the
W5 receipt generator no longer reports `mapping_a_gdpval: NOT_EXECUTED`.

**Constraint:** do not open `dax/analysis/outcomes/` — the seal is not lifted and
`v1.0-preregistered` does not exist.

### P1-B · Book the WRDS window — **OWNER** 🔴 *P1 critical path*
**Why:** gates T3-impl, T4, T5, T7 — i.e. every remaining P1 result.

`ops/briefs/P1-WRDS-SPRINT.md` is the runbook and the pull scripts are pre-written
so a borrowed window is pure execution. What the owner must supply: access, plus
the **pasted table/variable lists** for CRSP DSF/MSF, Compustat quarterly, IBES,
and TAQ-IID. The loader is built to *refuse* invented names — do not work around it.

Fills the 17 `[WRDS_NEEDED]` cells in `p1/t3_spec/变量规格书.md`.

### P1-C · Fetch the two blocked PDFs — **OWNER**, any browser — ~30 minutes
Both are free; only this container's egress blocks them.

1. **Saglam–Tuzun (2025) FEDS Note** — DOI `10.17016/2380-7172.3909`. Checklist of
   exactly what to transcribe is in `p1/t4_replication/saglam_tuzun_stub.md`.
   Unblocks the T4 transcription half.
2. **`Canaries_August2026.pdf`** headline-figure excerpt — resolves the DAX 0.19
   constant whose `locator_status` is `PENDING_EXCERPT`. `freeze_power_standard.py`
   refuses to run until `benchmark.version_status: RESOLVED`.

Optionally also the GNZ (2021) PDF — closes DECISION_NEEDED D2/D3/D4 and 17
`[NEED_PDF]` cells in the T3 spec.

### P1-D · Retry E2-T2-dune — seat B (or L1 if P0-3a) — 1 block
**Why:** one failed attempt, never retried; the whole E2 chain is behind it.

Per queue policy, two failures → escalate to Sonnet. Only user-supplied table
names; `NEED_INFO` otherwise. Also resolve the `syrupUSDC/Base market_id = UNKNOWN`
carried as residual risk #3 from the registry sign-off.

**Acceptance:** real flows/rates data exists, so `build_panel.py` can be pointed at
something other than `synth_inputs()`.

---

## PHASE 2 — resume the pipelines (after Phase 1 lands)

| # | Task | Seat | Precondition | Notes |
|---|---|---|---|---|
| 2-1 | `DAX-W4` capability/cost panel | A | P1-A | 13 fields named in the W5 receipt, incl. `task_duration` |
| 2-2 | `DAX-W5-index` re-run | A | 2-1 | Rerun from the exact branch state; no synthetic/static substitution |
| 2-3 | CPS/IPUMS extract → `freeze_power_standard.py` | A | — | Kills `PLACEHOLDER_REQUIRES_REAL_CPS`; also needed for M3/M4 |
| 2-4 | Fresh cross-vendor red team | A | memo v3 | The old CONDITIONAL_GO does **not** transfer — different design |
| 2-5 | `P1-T3-spec-B` + `P1-T3-decision` | — | P0-3 | Diff vs channel A; splits → owner gate |
| 2-6 | `P1-T3-impl` → `outcomes_panel.parquet` | C | P1-B, 2-5 | Contract exists (B1); assert every 值域 from the spec |
| 2-7 | `P1-T4-replication` | C | P1-B, P1-C | Report the first run. No tuning to match. |
| 2-8 | E2 T3 → T5 → T6a → T7 → T15 note | B | P1-D | T15 note is E2's fastest publishable artifact |

---

## PHASE 3 — results (gated; do not start early)

- `P1-T5-main` — needs T3-impl **and** the P0-4 sample decision on file first.
- `P1-T7-robust` — the §8 robustness list, in referee-attack order.
- `DAX-GATE2` → `v1.0-preregistered` tag → **only then** may
  `dax/analysis/outcomes/` be opened. All Gate-1 evidence must be checked off first.
- `REFR-*` — stays parked behind `REFR-GATE-e2verdict`. Note this is downstream of
  E2 being alive; if the owner picks P0-3(c), refraction should be parked
  explicitly too rather than left waiting on a verdict that will never come.

---

## Recommended assignment if you have limited capacity

Highest value per unit effort, in order:

1. **P0-3** (box decision) — one owner decision that unfreezes 15 tasks.
2. **P0-1** (state reconciliation) — prevents duplicated work by every future agent.
3. **P1-A** (DAX W3-mapA) — one task standing between DAX and its whole pipeline.
4. **P0-4** (sample decision) — 10 minutes now, protects T5's integrity later.
5. **P1-B** (WRDS) — largest unlock, but longest lead time; start procurement now.

If only one thing happens this week, make it **P0-3**. Everything else is
downstream of having a working automation lane.
