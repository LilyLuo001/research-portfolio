# Y1b — Build the real computerization measures

*Self-contained. Does not need `Y0_CONTEXT_PACK.md` prepended. One session.
Run on the SCC. Requires Y1a (done, `14d741d`).*

---

## Who you are and what this is

You are the execution agent for **YAX**, a self-contained third dissertation
chapter. It is not the student's main paper — two finance papers serve that
role. The objective is a rigorous, independent, defensible chapter without
methodological expansion.

The chapter asks: *among occupations with comparable pre-existing
computerization, did employment of workers aged 22–25 decline relative to 26–65
after ChatGPT, in occupations with greater LLM exposure?*

Read `yax/RESEARCH_PLAN_v4.md` first. §2 (the three concepts), §3 (what is
unresolved) and §6 (operationalization) are binding. §6 fixes the choices below;
you implement them, you do not re-decide them.

## The five rules that override your defaults

1. **You are not a source of facts.** Every number, taxonomy claim or file
   property comes from code you ran or a document you opened, with a locator. A
   fact recalled from training is a hallucination. This project has shipped
   four confidently-worded false claims that way; external review caught every
   one, self-check caught none.
2. **Schema contracts.** Tasks hand off through files. Never rename a column
   another task reads.
3. **Don't know → stop.** `NEED_HUMAN: <reason>` and halt. Never guess-fill.
4. **Never specification-search.** The first run of a pre-specified table is the
   reported run.
5. **Commit early and often**, named paths only.

## The one irreversible mistake

**Never open a post-ChatGPT outcome before `v1.0-design-freeze` is tagged.** A
control added after outcomes are seen is specification search, and the design
freeze is this chapter's entire contribution. This task touches no outcome data.

## Environment

- **Do not assume an interpreter or a pandas version. Verify first.** Measured
  2026-08-26: the SCC **default** Python is 3.6.8 with **no pandas**. A project
  venv carries 1.4.3. Prefer stdlib `csv`/`json` where pandas is absent. Never
  `lineterminator=` in `to_csv` (pandas ≥1.5 only).
- Licensed microdata never enters the git work tree. Call
  `dax/w2/microdata_guard.py::assert_not_committable` before any person-level
  write. Never `git add -A`. Never echo a credential.
- **No API key is needed for this task.**

---

## Why this task exists

Everything the project currently knows about AI-versus-computerization
separability comes from `yax/measurement/computerization_support.py`, which uses
Dingel–Neiman **teleworkability as a stand-in**. Teleworkability is not
computerization — an occupation can be computer-intensive and not teleworkable,
and the reverse. **No number from that script may be quoted.** This task
replaces the proxy with real measures.

`yax/gates.py::gate_computerization` blocks the design freeze until it is done.

## Task 1 — Webb software exposure

**The route is settled by Y1a. Do not re-litigate it.**

- Webb file: `exposure_by_occ1990dd_lswt2010.xls`, sha256
  `c5652fd3f862948cb77d87f38aa8296137c51e028992ab54e57246a066e0a779`, 341 rows,
  **UTF-8 CSV despite the `.xls` suffix**. Distribution via
  `michaelwebb.co` → `eepurl.com/gxo4zr`.
- Native taxonomy is Dorn's **`occ1990dd`** (341 categories) — *not* IPUMS
  `OCC1990` (389). `OCC1990` is not needed and the extract is not amended.
- Bridge with **Dorn's direct crosswalk**:
  `ddorn.net/data/occ2010_occ1990dd.zip`, zip sha256 `454cf8d7…`, dta sha256
  `7d6069da…`.
- Measure: **`pct_software`**.
- Cross-check the merge against `github.com/EIG-Research/AI-unemployment`,
  `code/02 Microdata Monthly Build.R`.

Verified coverage on the outcome-blind pre-period support: 445 observed CPS
`OCC2010` codes, **0 unmapped**, 442 carrying a Webb score = 99.9515% of
employment weight.

**Open item:** the three occupations Webb does not score are counted but **not
named**. Name them, with their combined employment weight. This project names
occupations rather than reporting only shares — it is how the 96.7% group-15
finding became interpretable.

## Task 2 — O\*NET *Interacting With Computers*

| choice | value |
|---|---|
| release | **O\*NET 24.3, May 2020** |
| descriptor | **`4.A.3.b.1`, Interacting With Computers** — using computers and software to program, enter data, or process information |
| scale | **Importance primary**, Level as robustness |

`onetcenter.org/db_releases.html`. Record release and sha256.

24.3 is the last release before the O\*NET-SOC 2019 transition (25.1 introduced
it), so the measure stays on one vintage — and the project's existing SOC-2010
vintage repair applies unchanged.

**Do not use current O\*NET ratings.** They are collected after LLM diffusion
began and are not a measure of *prior* computerization. This is the whole point
of the measure.

## Task 3 — RTI and Frey–Osborne

Routine-task intensity by the Autor–Levy–Murnane / Acemoglu–Autor recipe. Note
that `dax/data_built/onet_task_weights.parquet` carries task-level importance
and frequency only — the work-context and work-activity items RTI needs are not
in it, so obtain them.

Frey–Osborne (2017) **secondary only**: it bundles AI and robotics into an
automation-risk score rather than measuring prior computerization cleanly, so it
partly contains the treatment. Report it; do not lean on it.

## Task 4 — Re-run the diagnostics on real measures

Re-run `yax/measurement/computerization_support.py` against Webb `pct_software`,
O\*NET `4.A.3.b.1`, RTI and Frey–Osborne.

**The statistic that matters is partial variance, not a cell share.** For each
AI × computerization pair report:

- employment-weighted correlation, **partial variance of AI (1 − R²), VIF and
  SE inflation** — these decide identification;
- effective number of occupations identifying β_AI;
- share of residual variation by SOC major group;
- **named** divergence occupations;
- common-support employment coverage.

An earlier version of this script led with a discretized "clean cell" share and
reached the wrong verdict; see
`yax/CORRECTION_2026-08-26_separability_verdict.md`. The cell is a descriptive
aid and the source of the named occupations. It is not the identification test.

**Report the result whatever it is.** If conditional support is weak across
every computerization measure, the chapter's conclusion becomes that
occupation-level public data cannot separately attribute the young-employment
pattern to LLM exposure rather than prior computerization. That is smaller, and
still a chapter.

**The receipt's `proxy_warning` field must be removed only when the receipt
genuinely reflects a real computerization measure.** `gates.py` blocks on that
field; clearing it while still on the proxy would falsify a gate rather than
pass it.

---

## Definition of done

- Webb vendored and merged via Dorn's crosswalk; the three unscored occupations
  named with their weight; source sha256s recorded.
- O\*NET 24.3 `4.A.3.b.1` Importance and Level, crosswalked, receipted.
- RTI and Frey–Osborne built.
- `computerization_support.py` re-run; receipt + lineage committed.
- `python yax/gates.py` shows `computerization` **no longer BLOCKED**.
- `pytest -q` green. Report counts **and the skip list with reasons**, and say
  which repository and branch you ran in — a count that does not describe the
  artifact under verification is not verification. Expect ~725 passed, 3
  skipped on `claude/dax-research-direction-1ohi97`.

## Do not

- Do not open a post-period file.
- Do not use Webb's **AI** measure, or AIOE, as the computerization control.
  AIOE is an alternative *AI* measure and is barred from that role.
- Do not use current O\*NET ratings.
- Do not clear `proxy_warning` while still on the proxy.
- Do not drop a computerization measure because it absorbs the AI coefficient.
  That absorption is the result.
