# Y1a — Unblock the critical path

*Self-contained. Does not need `Y0_CONTEXT_PACK.md` prepended — everything is
below. One session. Run on the SCC.*

Three tasks in order. Task 1 makes the other two verifiable by anyone; tasks 2
and 3 decide a fork that must be settled before the design freeze.

---

## Who you are and what this is

You are the execution agent for **YAX**, a self-contained third dissertation
chapter. It is not the student's main paper — two finance papers serve that
role. The objective is a rigorous, independent, defensible chapter without
methodological expansion.

The chapter asks: *among occupations with comparable pre-existing
computerization, did employment of workers aged 22–25 decline relative to 26–65
after ChatGPT, in occupations with greater LLM exposure?*

**The contribution is the design freeze and the measured MDE, not the question.**
Protect the ordering above all else.

Read `yax/RESEARCH_PLAN_v4.md` before starting. §3 (what is unresolved), §6
(operationalization) and §13 (order of work) are binding. You may not alter
them; if one is wrong, stop and say so.

## The five rules that override your defaults

1. **You are not a source of facts.** Every number, date, taxonomy claim or
   file property comes from code you ran or a document you opened, with a
   locator. A fact recalled from training is a hallucination — discard it. This
   project has shipped four confidently-worded false claims that way and
   external review caught every one.
2. **Schema contracts.** Tasks hand off through files, never conversation.
   Never rename a column another task reads.
3. **Don't know → stop.** Emit `NEED_HUMAN: <reason>` and halt. Never
   guess-fill, never substitute a plausible value, never silently narrow scope.
4. **Never specification-search.** The first run of a pre-specified table is the
   reported run.
5. **Commit early and often.** Long runs are scripts handed to the scheduler.

## The one irreversible mistake

**Never open a post-ChatGPT outcome before `v1.0-design-freeze` is tagged.** Not
to sanity-check a merge, not to look at a row count. The design freeze is this
chapter's entire contribution and cannot be reconstructed afterwards. This task
touches no outcome data at all.

## Environment and safety

- **SCC Python is old**: `pandas` is 1.4.3, not ≥2.1 despite `requirements.txt`.
  Verify with `python -c "import pandas; print(pandas.__version__)"`. No
  `lineterminator=` in `to_csv` (pandas ≥1.5 only).
- **Licensed IPUMS microdata never enters the git work tree.** Call
  `dax/w2/microdata_guard.py::assert_not_committable` before writing any file
  that could contain person-level records. Do not disable it.
- **Never `git add -A`.** Stage named paths only.
- **Never echo a credential.** Do not run `git remote -v`, do not print
  environment variables, do not paste a key into your output. Read the IPUMS key
  from the environment or a private file and reference it only by name. A PAT
  was leaked into a transcript earlier in this project by exactly this route.

---

## Task 1 — Push the SCC work to `origin`

Roughly eight hours of work exists only on two SCC working copies —
`/usr3/graduate/qluo/dax_design_power_20260825` and
`/usr3/graduate/qluo/dax-cps-sparse-20260825` — with commits cherry-picked
between them and no remote.

This has already cost something concrete: a reviewer reading the GitHub branch
concluded the wide IPUMS extract had never been submitted, because no receipt
for it exists on `origin`. It has been submitted; it produced 9,262,480 rows.
The record simply is not where anyone can see it.

Push the **code, receipts, lineage sidecars and audit CSVs**. These are not
licensed data. Only the CPS panels themselves stay private.

    git status --short          # named paths only
    git diff --cached --stat    # confirm no microdata staged

Push to the branch `claude/dax-research-direction-1ohi97`. If the two working
copies have diverged, reconcile them and say how.

## Task 2 — Does IPUMS CPS offer `OCC1990` for 2017–2026?

**Verified blocker:** the wide extract spec
(`dax/memo/power_calcs/ipums_ai_telework_extract_v1.json`) has 26 variables and
exactly one occupation code, `OCC2010`. `OCC1990` is absent. Webb's software
exposure — the chapter's primary computerization measure — is commonly
distributed on `occ1990dd` and keyed on IPUMS `OCC90`.

**One metadata call settles whether this is a real fork.** Query the IPUMS
variables metadata for the `cps` collection and establish whether `OCC1990` is
available for **basic monthly samples, 2017-01 through 2026-07**.

- Consult the current IPUMS API documentation for the correct endpoint rather
  than assuming one. Record the endpoint you used.
- **Metadata only. Do not submit an extract.** Submitting is the owner's call.
- Report availability per sample, not just in aggregate — partial coverage
  across the window is the outcome that would actually complicate things.

## Task 3 — Verify Webb, and settle the `occ1990dd` question

Webb (2020), `michaelwebb.co/webb_ai.pdf`, constructs **software, robot and AI**
exposure from a common task–patent framework. That much is verified from the
paper. **The data file is not.**

1. Locate the distributed data file. Record URL, sha256, row count, and its
   **native occupation taxonomy** as the file itself declares it.
2. **Is `occ1990dd` the same thing as IPUMS `OCC1990`?** It is understood to be
   Dorn's *time-consistent modification* of `OCC1990` rather than `OCC1990`
   itself — meaning adding the variable would be necessary but **not
   sufficient**, and Dorn's crosswalk would still be required. **Verify this
   against Webb's replication files and Dorn's documentation. Do not take that
   sentence, or any agent's recollection, on faith.** It decides whether Task 2
   alone clears the blocker.
3. Cross-check against `github.com/EIG-Research/AI-unemployment`, which keys
   Webb on IPUMS `OCC90` in a CPS setting.

Take Webb's **software** measure as the computerization primary. His **AI**
measure is not the computerization control and must never be used as one.

---

## Deliverable

A receipt at `yax/measurement/webb_occ1990_feasibility_receipt.json` recording:
endpoint used, `OCC1990` availability by sample, Webb file URL and sha256, its
native taxonomy, and whether `occ1990dd` requires Dorn's crosswalk — each with
its locator.

Then **`NEED_HUMAN`** with a recommendation between:

- **Amend and resubmit** the extract with `OCC1990`, then apply Dorn's crosswalk
  if Task 3 says it is needed. The extract is already built, so this is a
  resubmission with queue time — outcome-blind today, impossible after the tag.
- **Bridge `OCC2010` → `occ1990dd`** with a documented, cited crosswalk,
  reporting coverage and naming the occupations lost. This costs coverage for
  nothing if Task 2 says `OCC1990` is available.

State the coverage cost of the bridge if you can estimate it. **Do not pick
silently** — one route changes the extract.

## Definition of done

- Everything pushed to `origin`, no microdata staged, divergence reported.
- The feasibility receipt exists with every locator filled in.
- `NEED_HUMAN` with a recommendation and its reasoning.
- `pytest -q` green. Report the counts **and the skip list with reasons** —
  three modules skip on optional imports (`torch`, `sklearn`, `cryptography`)
  and the total is environment-dependent, so a bare number means nothing.

## Do not

- Do not submit or amend an IPUMS extract. Report and recommend.
- Do not open any post-period file.
- Do not use Webb's AI measure or AIOE as the computerization control.
- Do not print any credential.
