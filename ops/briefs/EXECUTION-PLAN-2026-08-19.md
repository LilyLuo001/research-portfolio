# Portfolio execution plan — 2026-08-19

**Written for an executing agent with no memory of the session that produced it.**
Repo: `LilyLuo001/research-portfolio`. Snapshot commit: `c9d913c` on branch
`claude/refraction-research-plan-11jsie` (13 commits ahead of `main`).

Read `CLAUDE.md` first — it is binding and it overrides anything here that
conflicts. Then read this. Then **verify state yourself** before acting:

```
git pull
python ops/runner/runner.py --plan      # authoritative READY/blocked list
python ops/runner/selfcheck.py          # queue DAG + contracts + vendor independence
python -m pytest -q                     # 263 passing at snapshot
```

If `make plan` disagrees with this document, **the runner wins** — this file is a
snapshot, the queue is the state.

---

## 0. The five rules that void work if broken

From `CLAUDE.md` §the five meta-rules. An executor that breaks these produces
output that must be discarded, so they come before any task.

1. **The model is not a source of facts.** Dates, AUM, holdings, coefficients,
   database schemas, bibliographic fields — all come only from (a) code you wrote
   executed on real data, or (b) an extraction carrying a raw-source locator
   (EDGAR accession + URL, WRDS library.table + query, page URL). Anything "from
   memory" is a hallucination. Discard it.
2. **Dual-channel** on high-hallucination tasks (event lists, citations, spec):
   two *different vendor families*, machine-diff, third model + human on splits.
3. **Schema contracts.** Tasks hand off through files in `ops/contracts/`, never
   through conversation. **Never rename a column.**
4. **Don't know → stop.** Emit `NEED_HUMAN: <reason>`. Never guess-fill.
5. **Expensive gates, cheap runs.** Frontier tier for spec/audit/red-team;
   cheap tiers for templated bulk. Two consecutive failures → auto-escalate.

### Four hard gates specific to this portfolio

- **Refraction prereg-before-outcomes.** Anything touching post-period outcome
  variables (tasks R6+) calls `refraction/guards/prereg_guard.py::assert_prereg_ok()`
  at startup and *refuses to run* until `frozen_config.yaml` carries the OSF
  timestamp. Do not work around the guard. Do not fill `beta.w_shrink` outside
  `REFR-GATE-OSF`.
- **Refraction lookahead ban.** β / lever / weights use only data strictly before
  a wave's effective date (`pipeline/assert_panel.py::a4_no_lookahead`).
- **DAX outcome seal.** Never open `dax/analysis/outcomes/` before the
  `v1.0-preregistered` tag exists. It does not exist yet.
- **Licensed data.** CRSP/WRDS rows never enter git. Policy and enforcement:
  `p1/t2_wrds/README.md`, `p1/tests/test_wrds_data_policy.py`.

**Never specification-search.** No "if significant then…". Report the first run.

---

## 1. Ground truth at snapshot

| | |
|---|---|
| Queue | 84 tasks · 12 complete · 17 READY · 2 human gates waiting · 1 in flight |
| Tests | 263 passing; selfcheck clean |
| Projects | P1 (fund→ETF conversions) · E2 (RWA looping) · DAX (AI exposure) · refraction (macro-event standby chapter) |
| Seats | A=dax · B=e2 · C=p1+refraction · D=shared/ops · E=writing float (`ops/accounts.yaml`) |

**What is actually blocking the portfolio** — four capabilities, not four tasks:

| Lane | Capability | What it unblocks |
|---|---|---|
| **B** | outbound HTTPS to gov/academic domains | REFR-R0, REFR-R1a, DAX-W0.5, all EDGAR/SEC pulls |
| **C** | WRDS credentials + a machine that can run jobs | P1-T2-wrds, and P1-T3 → T5 behind it |
| **D** | owner decisions and signatures | 7 items, several of which gate whole branches |
| **E** | seat D / infra | cron wiring, COMPLIANCE.md, box repair |

---

## 2. Lane A — startable immediately, no blockers

Nothing here needs network, credentials, or a decision. Take these first if you
have no other capability.

### A-1 · Open a PR for the 13 unmerged commits
Branch `claude/refraction-research-plan-11jsie` is 13 commits ahead of `main`.
PR #38 already merged and is closed — **these commits are not in it**, so a new
PR is required. Do not reuse #38.
**Done when:** a new PR exists and CI (`backbone`) is green.

### A-2 · Review the R1a fetcher (committed, never yet run against the network)
`refraction/fetch_r1a_sources.py` + its 11 tests are committed and green, but the
script has **never executed against a live network** — every lane that produced
it was egress-blocked. Its first real run belongs to Lane B (B-1), and its output
should be eyeballed once before anyone trusts the registry it writes. Treat a
first run that returns all-UNKNOWN rows as evidence about egress, not as a
finding about the sources.

### A-3 · `REFR-R14-metaqa` (resident, mechanical)
Cheap-tier ONLY (`Flash-Lite`/豆包 class — manual §R14 restricts this
deliberately; do not run it on a frontier model). Checklist = E2-T14 items plus
three refraction-specific ones: ⑥ the A4 lookahead PASS is recorded in the
manifest, ⑦ `w_shrink` appears only in `frozen_config.yaml`, ⑧ every task
consuming post-period outcomes carries runtime-after-OSF-timestamp proof.

### A-4 · `SH-l1-smoke`
One sentinel-fenced dummy batch end-to-end, to prove the L1 lane works before
real batches are spent on it. Runs whenever the box is alive.

---

## 3. Lane B — needs a web-capable session

These are blocked *only* by egress. Every one is mechanical once a session can
fetch. **Do not substitute search-result snippets for fetched pages** — they are
second-hand and fail rule 1.

### B-1 · `REFR-R1a-verify` — CRITICAL PATH
Brief: `ops/briefs/opus/OPUS-REFR-R1a-verify.md`. Spec: `ops/l1/REFR-R1a-verify.yaml`.
Originally routed to kimi; kimi is **benched** for retrieval (2026-07-09 vendor
decision). Run it in an Anthropic-lane session with web access, per the spec
header's own instruction.

A helper exists: `refraction/fetch_r1a_sources.py` fetches the seed pages,
records URL + status + SHA256 + retrieval timestamp per artifact, and extracts
the column list and first 20 rows of any tabular download automatically. Run it
first; it turns most of R1a into review rather than transcription.

Three deliverable registries: USMPD structure (verbatim variable definitions
≤25 words + URL each), 2017–2026 FOMC/CPI/Employment-Situation calendars
(per-year official URLs + release times ET), CPI/NFP consensus channels.
Answer sentinels S1/S2 yourself; a mismatch VOIDs the run.
**Done when:** `ops/l1/out/REFR-R1a-verify.json` + lineage; `--complete` is legal
(no channel pair). Then R1b is blocked only on the paste-list below.

### B-2 · `REFR-R1b-parse` — the adapter, once B-1 lands
**Half of R1b is already built and tested**: `refraction/pipeline/surprises.py`
(standardization, scheduled-window policy, five acceptance assertions).
What remains is an adapter from the real file's columns to the contract's.
`refraction/R1b_input_requirements.md` lists the eight inputs required, item by
item, with what consumes each. `parse_usmpd()` raises `NeedInfo` by design —
**do not implement it by guessing column names.**
**Done when:** `macro_calendar.csv` + `surprises.parquet` pass their contracts,
assertions A1/A3/A4/A5 green, A2 reconciles against R1a's calendar, manifest
records the null-`S_std` count.

### B-3 · `REFR-R0-collide` (channel A) + `-B`
Brief: `ops/briefs/opus/OPUS-REFR-R0-collide-A.md`. Literature collision sweep,
11 references + the Marta–Riva priority check (SSRN 4079302) + three 24-month
sweeps. **ALERT threshold is 40% for Marta–Riva, 60% for everything else.**
Channel B must stay a *different vendor family* (gemini) — rule 2.
If any hit crosses its threshold, append a `NEED_HUMAN` line to
`ops/decisions.md` naming the paper and the hypothesis it collides with.
Do **not** `--complete` while channel B is outstanding.

### B-4 · `DAX-W0.5-legwork`, `P1-T0-monitor`, `E2-T6b-nav`
Lower priority, same lane. `P1-T0-monitor` is the monthly Saglam–Tuzun watch;
the FEDS Note is its subject.

---

## 4. Lane C — box + WRDS

WRDS is **purchased but not yet delivered** at snapshot. The code is written and
tested against an injected fake connection, so day one is a run, not a build.

### C-0 · Before anything: repair the box
`ops/decisions.md` (2026-07-09/10) records SCC SSH publickey auth denied
account-wide and a broken venv (`.venv/bin/python` missing, no `python3` module).
**A WRDS credential is useless on a machine that cannot run the job**, and the
nightly L1 lane is dead until this is fixed. This is the highest-leverage repair
in the portfolio.

### C-1 · Verify the schema — FIRST, before the pipeline
```
python p1/t2_wrds/coverage_census.py --introspect
```
Every CRSP table/column in `holdings_pipeline.py::SCHEMA` is marked **UNVERIFIED**
— written before access existed. This prints what actually exists and names the
entries to correct. Correcting them is a one-place edit by construction, and a
test fails if an identifier leaks out of that dict.

### C-2 · Coverage census — SECOND, still before the pipeline
```
python p1/t2_wrds/coverage_census.py
```
Censuses all 131 conversion funds: mapped to a CRSP fund number, holdings report
strictly before conversion, staleness. **A pipeline that silently drops a third
of the funds looks exactly like a successful pipeline** — the free path computed
6,377 cells and dropped 5,929, visible only because someone counted.

### C-3 · `P1-T2-wrds` — the ConvExp build
```
python p1/t2_wrds/build_waves.py
python p1/t2_wrds/holdings_pipeline.py
python ops/runner/contracts.py conv_exposure p1/conv_exposure.parquet
```
Watch for: `shrout` is in **thousands** (×1000 is applied and tested — do not
"fix" it); cells with no denominator are dropped *with their numerator retained*,
never imputed; `pre_etf_ownership` is deliberately null, not aliased to
`conv_exp`. Raw rows never enter git — the run writes `query_manifest.json`
(locators) instead.

### C-4 · Reconciliation — the strongest validation available
```
python p1/t2_wrds/reconcile_convexp.py --build-map    # box, one query
python p1/t2_wrds/reconcile_convexp.py                # offline
```
Free EDGAR path vs WRDS path: two constructions of the same quantity sharing no
code, no vendor, no failure mode. **Bands were frozen before any number existed**
(agree ≤1%, close ≤10%, investigate above; verdict keys on the treated call at
≥0.5% against a 95% floor). Changing a band after seeing results is a disclosed
deviation, not a tweak. `NO_OVERLAP` is its own verdict and never reads as PASS.

### C-5 · Re-run the free path to activate two pending patches
`build_nport_convexp.py` now emits `val_usd` and a dropped-cell sidecar
(`dropped_cells_shares_held.csv`), both inert until it re-runs with network.
**In the same commit that lands the rebuilt parquet**, uncomment the `val_usd`
line in `ops/contracts/conv_exposure_free.yaml` — `contracts.py` treats every
declared column as mandatory, so declaring it earlier retroactively fails the
artifact Gate 2 was signed on.

### C-6 · Do NOT run
`p1/output/convexp_coverage_audit/recover_denominators.py --online` (yfinance/
Stooq denominator recovery) is **superseded** by CRSP `shrout`. Retained as a
fallback only if WRDS delivery slips.

---

## 5. Lane D — owner decisions (each needs one answer, not a discussion)

These are not research tasks. Each is a sentence from the PI that unblocks work.

| # | Question | What it gates | Where the evidence is |
|---|---|---|---|
| D-1 | International sleeve: **Option A** (drop pure-international waves), **A-strict** (drop any wave touching one), or **A + fund-level rebuild**? | P1 sample definition; must be fixed **before** T5 estimation | `p1/output/convexp_coverage_audit/international_sleeve_options.md` — anchor wave survives all options; A costs 8 stocks at ≥0.5% (389→381); A-strict costs a third of the ≥1% names (24→16) |
| D-2 | Paste the eight R1b inputs | `REFR-R1b-parse` | `refraction/R1b_input_requirements.md` |
| D-3 | CPI/NFP consensus source: Bloomberg ECO at BU vs a WRDS substitute | `frozen_config: surprise.consensus_source` (FOMC-only does not block Gate-0) | R1a item 3 answers whether a WRDS substitute exists |
| D-4 | `holdings_weights` weight-basis alignment with P1-T2, **in writing** | `REFR-R2-panel` pre-dispatch | refraction manual §2.3① |
| D-5 | Confirm Gate-0 thresholds in `ops/decisions.md` | `REFR-R3-gate0` | `frozen_config.yaml: gate0_thresholds` are Plan §9 provisional lines |
| D-6 | `P1-T1-events(+B)` gate calls — the runner still shows `P1-T1-arb` blocked although `events_merged.csv` and the spotcheck sign-off are committed | P1 bookkeeping; downstream readiness | `ops/decisions.md`, `p1/t1_spotcheck_SIGNOFF.md` |
| D-7 | ETF Global / issuer basket access; E2 verdict | `REFR-GATE-etfglobal`, `REFR-GATE-e2verdict` (both parked, non-blocking) | queue human gates |

**Also owner-owed, from `ops/briefs/ASSIGNMENTS-2026-08-14.md`:**
- **Stranded DAX-W1 work.** Commits `7a6a401` and `5d26fe2` sit on
  `task/DAX-W1-memo` above the PR #35 merge point and are **verified still not on
  `main`**. They carry the cross-vendor red team, its remediation, the memo
  revision, the updated PDF, and the IPUMS pull. **Until merged, the PDF on
  `main` is the pre-red-team draft — do not review that one.**
- **Rotate the GitHub PAT** (flagged in `progress_audit_2026-08-06.md`; a token
  was pasted into a chat session).
- **Counter-sign D1** (`dax/memo/PI_DECISION_D1_2026-08-18.md` — decided under
  delegation, does not bind until signed).
- **DAX D3/D4/F2 remain open** (`dax/memo/PI_DECISIONS_OPEN.md`). **D3 blocks the
  power rebuild**, and the power rebuild blocks `DAX-GATE1-memo` → `DAX-W5-index`.

---

## 6. Lane E — seat D / infrastructure

- **E-1** Add the monthly cron line for `refraction/scan.py` to
  `ops/box/cron_night.sh`, treating `refraction/scans/` as `e2/scans/` is already
  treated. Detail: `refraction/scans/manifest.md` §handoff.
- **E-2** Fold the WRDS data policy into `ops/COMPLIANCE.md`, which is currently
  silent on licensed data. Source text: `p1/t2_wrds/README.md`.
- **E-3** Give `REFR-R13-triage` a vendor lane (kimi is benched).

---

## 7. Suggested order

**If you have exactly one capability, do this:**

- *Web session* → B-1 (R1a) → B-3 (R0) → B-2 (R1b, once the paste-list lands).
  R1a is the single highest-value unblock in the portfolio: it opens
  R1b → R2 → R3 → GATE-PREREG, the whole refraction critical path.
- *Box/WRDS* → C-0 (repair) → C-1 (introspect) → C-2 (census) → C-3 → C-4.
  In that order. The census before the pipeline is not optional.
- *Owner* → D-6 and the D3 signature first: both are one-line answers that
  unblock branches other people are waiting on. Then D-1, then D-2.
- *Code only, no access* → A-1, A-2, then DAX-W2-data (seat A, non-price half,
  brief at `ops/briefs/opus/OPUS-DAX-W2-data-nonprice.md`) or E2-T4a-design
  (seat B, **write the brief into `ops/briefs/` first**, per the working protocol).

**Parallelism is safe** across lanes because seats are partitioned by directory
(`ops/accounts.yaml`). Two agents must never edit the same project subtree. Claim
before working: `python ops/runner/lease.py claim <task> --account <SEAT>`.

---

## 8. Definition of done (applies to every task)

A task is complete when **all** of these hold — not when the code runs:

1. Output passes its contract: `python ops/runner/contracts.py <contract> <path>`.
2. A lineage JSON sits beside every built artifact
   (`python ops/runner/lineage.py <output> <input>...`).
3. A `manifest.md` exists carrying inputs + row counts/hashes, environment,
   limitations, the UNKNOWN list, and downstream notes. **Missing manifest =
   not delivered** (manual §0.4).
4. `python -m pytest -q` and `python ops/runner/selfcheck.py` are green.
5. The work is committed and merged to `main`, then
   `python ops/runner/runner.py --complete <task>`.

Two exceptions, both deliberate: **resident** tasks (`REFR-R13-scan`,
`E2-T11-scan`, `REFR-R14-metaqa`) are never marked complete — they stay READY
forever. **Dual-channel** tasks are not completed while their sibling channel is
outstanding.

---

## 9. Traps that have already bitten this project

Read these; each cost real time or nearly corrupted a result.

1. **Concatenated programs.** Three artifacts have been damaged by a second
   program merged onto the first — the `conv_exposure_free` contract (two YAML
   docs; the validator demanded a column the data never had), and two Python
   files where a dead second `main()` shadowed the real one and would have
   overwritten a clean output. Guards now exist (`p1/tests/test_build_waves.py`,
   `test_build_nport_convexp.py`). An AST sweep at snapshot finds zero remaining.
2. **Truncating a committed log by importing a module.** Two pipelines opened
   their run log `mode="w"` at import time; the log is committed provenance that
   `recover_denominators.py` parses. Setup now lives in `_setup_run()`.
3. **Exact-date joins that silently drop rows.** The WRDS scaffold pinned one
   global month-end for `shrout`; any stock without a row on exactly that date
   lost its denominator. Same failure cost the free path ~5,600 cells.
4. **`""` in numeric contract columns.** Fails or silently corrupts validation.
   Use real nulls.
5. **The 8-vs-9 character CUSIP.** CRSP `ncusip` is 8 chars, N-PORT reports 9.
   Compared raw they match nothing, and "the two paths share no stocks" looks
   like a finding rather than an artefact of a check digit.
6. **A vendor that returns plausible prose instead of data.** kimi was benched
   after three distinct failure families; gemini once answered a launch date
   confidently and *wrongly* despite 34 grounded searches (`ops/decisions.md`,
   FalconX). This is why dual-channel exists — do not collapse it to save time.
7. **Filling a missing value with zero.** A CPI release with no consensus has no
   surprise; writing 0.0 asserts "the release matched expectations", which is a
   fabricated fact wearing a default's clothes. NULL, and count it.

---

## 10. What this plan does not decide

The international sleeve (D-1), the consensus source (D-3), the weight-basis
alignment (D-4), Gate-0 thresholds (D-5), and every prereg signature are the
PI's. Their evidence is assembled and costed; the choices are not made. Do not
let an executing agent pick one by default — a sample definition chosen
downstream of seeing results is specification search, whoever or whatever makes
it.
