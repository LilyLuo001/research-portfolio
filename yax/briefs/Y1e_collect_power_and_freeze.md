# Y1e — Collect the queued power runs, then close the remaining gates

*Self-contained handoff. The previous agent hit a usage limit with eight
cluster jobs queued. One session. Run on the SCC.*

---

## Who you are and what this is

You are the execution agent for **YAX**, a self-contained third dissertation
chapter — not the student's main paper. It asks: *among occupations with
comparable pre-existing computerization, did employment of workers aged 22–25
decline relative to 26–65 after ChatGPT, in occupations with greater LLM
exposure?*

Read `yax/RESEARCH_PLAN_v4.md`. §2, §3, §5, §12, §13 and §13b are binding.

**The five rules.** (1) You are not a source of facts — every number from code
you ran or a document you opened, with a locator. (2) Schema contracts: hand off
through files, never rename a column another task reads. (3) Don't know → stop:
`NEED_HUMAN`, never guess-fill. (4) Never specification-search: the first run of
a pre-specified table is the reported run. (5) Commit early, named paths only.

**The one irreversible mistake.** Never open a post-ChatGPT outcome before
`v1.0-design-freeze` is tagged. Everything below is pre-period or simulation.

**Environment.** Verify before assuming: SCC default Python is 3.6.8 with **no
pandas**; the project venv is `/usr3/graduate/qluo/portfolio/.venv/bin/python`.
Never `git add -A`. Never echo a credential. No API key needed.

---

## Exactly where things stand

Everything through commit `219ec40` is on `claude/dax-research-direction-1ohi97`
and pushed. **Do not redo any of it.**

| item | state |
|---|---|
| SCC worktree | `/projectnb/econdept/qluo/yax-y1d-20260827`, branch `task/yax-y1d-20260827` |
| Construct validity | **done** — `CONSTRUCT_VALIDITY.md`, status `PASS_RANKINGS_COHERENT_WITH_RECORDED_LIMITATIONS` |
| Support reconciliation | **done** — `SUPPORT_RECONCILIATION.md`, status `PASS_SUPPORTS_RECONCILED_AND_PRIMARY_PINNED` |
| Pinned primary support | **490 balanced Census-2018 clusters × 66 months, 2017-01 → 2022-11**, cells sha256 `4b8c8b96…` |
| Joint power code | **written, tested, not yet aggregated** — `yax/power/` |
| Power jobs | **8 submitted, were still queued**: `7330197`–`7330204`, requeued to `academic-pub` |
| Suite | 749 passed, 3 skipped |

Gates now: `coverage_rule`, `computerization`, `convergent_validity`,
`plan_consistency`, `seal` **PASS**. `gradient`, `calibration`,
`novelty`, `prespec_before_tag`, `freeze_doc` **BLOCKED**.

**Two supports are not contradictory and this is settled** — do not re-open it.
The 445/442 artifacts are OCC2010 with a lookup role that can inherit a recent
occupation for non-employed people; the 490-cluster panel uses current
Census-2018 occupations among employed workers. Different vintage, different
estimand. `SUPPORT_RECONCILIATION.md` records it, including that the 13m→66m
comparison mixes horizon, vintage, balance rule and weight definition and is
**not** a clean calendar-window experiment.

## Task 1 — Collect the eight power runs

    ssh scc 'qstat -u qluo'
    ls /projectnb/econdept/qluo/yax-y1d-20260827/yax/power/scenarios
    ls /projectnb/econdept/qluo/yax-y1d-20260827/yax/power/logs

Four primary scenarios (β and α × O\*NET importance and Webb, β_C = log 0.95)
and four sensitivity runs (β_C = 0 and β_C = log 0.90).

**Check the logs before assuming anything.** Jobs may have run, failed, or been
killed on walltime. Re-submit only what genuinely did not produce output, using
`yax/power/run_joint_power_scc.sh AI_MEASURE COMP_MEASURE BETA_C OUTPUT`
unchanged. **Do not re-run a scenario that already succeeded** — the first run
of a pre-specified simulation is the reported run.

Then aggregate:

    python yax/power/aggregate_joint_power.py <primary scenario json...> \
      --sensitivity <sensitivity json...> \
      --output <aggregate>.json --markdown POWER_NOTE.md

## Task 2 — Check the gradient before believing the MDE

    python yax/gates.py --power-aggregate <aggregate>.json

`gradient` FAILs two different ways and they mean opposite things:

- **Power at ceiling at the smallest tested effect** → the engine is describing
  its own smoothness, not a strong design. Extend the grid downward and
  diagnose. **Do not freeze.**
- **Power never reaches 80%** → the joint design is underpowered on this
  support. That triggers plan §12.4 and is a `NEED_HUMAN`, not something to
  work around.

`calibration` FAILs unless the aggregate carries a bootstrap field. The
unconditional engine rejected at 6.8068% against a nominal 5%, so expect
over-rejection and let the wild-cluster bootstrap carry primary inference.

Report the conditional MDE80 **for each of the four primary scenarios**, with
bootstrap intervals. O\*NET importance and Webb bracket the confounding range
— VIF 2.80 against ≈1.00 — so their MDEs should differ, and both belong in the
freeze. **Never quote the unconditional 3.44%. Never write "100% power".**

## Task 3 — The novelty gate, which has never been run

`novelty` has been BLOCKED since the beginning. `RESEARCH_PLAN_v4.md` §9a lists
what is outstanding:

- **Locators** — URL, author, date, version — for the Dallas Fed and Anthropic
  CPS young-vs-older patterns, and for EHP and Tucker.
- **The decisive question:** *has anyone run a pre-registered, power-stated test
  of this claim on public data?* Search the AEA RCT Registry and OSF. **List the
  sources you searched**, since absence found in an hour is not absence.

Rewrite §9a from claims-to-verify into findings. The gate keys on the
unresolved markers, so it clears only when they genuinely go. If plan §12.2
triggers — the pre-registered powered test already exists — **stop and
`NEED_HUMAN`.** Do not quietly re-frame the chapter to dodge it.

## Task 4 — Write the freeze document and tag

Only after Tasks 1–3 leave every gate PASS.

`yax/DESIGN_FREEZE_v1.md` must carry:

- the estimating equation exactly as it will be run, with clustering and the
  bootstrap procedure named;
- **β primary, α as the pre-specified direct-LLM contrast** — plan §2 fixes this
  on conceptual grounds and bars selecting on separability statistics. α being
  less confounded is **not** a reason to promote it;
- all five computerization measures reported, not treated as substitutes (§13b);
- the three coverage rules by reference to `COVERAGE_RULE_PRESPEC_v1.md`;
- the conditional MDEs from Task 1 with their intervals and the assumed β_C;
- **the pinned support and its sha256** — `4b8c8b96…`, 490 clusters × 66 months;
- empty table shells for the six main tables, every cell blank;
- the environment: interpreter and library versions, test counts, **and the skip
  list with reasons**. Three modules skip on `torch`, `sklearn`, `cryptography`
  and the total is environment-dependent, so a bare number is not reproducible.

Then:

    git tag -a v1.0-design-freeze -m "YAX design freeze: specification, coverage rule, computerization controls and conditional MDE fixed before any post-period outcome"
    git push origin --tags
    python yax/gates.py --power-aggregate <aggregate>.json   # all ten PASS

`prespec_before_tag` verifies in git history that
`COVERAGE_RULE_PRESPEC_v1.md` is an ancestor of the tag. **If it FAILs, do not
delete and re-tag** — that falsifies the record. Report it; the paper then
reports the coverage rule as a post-hoc choice.

The tag is `v1.0-design-freeze`, **not** `preregistered`: nothing is deposited
in an external registry, and a git tag is not a public timestamped third-party
record.

---

## Definition of done

- Eight scenarios collected or their failures diagnosed; aggregate + lineage
  committed.
- `gradient` and `calibration` PASS, or a written diagnosis of why not.
- `POWER_NOTE.md`: conditional MDE per scenario with intervals, assumed β_C,
  realised type-I error, effective occupations identifying β_AI, and what a
  simulation on a fitted DGP cannot capture.
- §9a rewritten as findings with locators; `novelty` PASS.
- `DESIGN_FREEZE_v1.md` committed, `v1.0-design-freeze` tagged and pushed, all
  ten gates PASS.
- `pytest -q` green — report counts, **the skip list, and which repository and
  branch you ran in.** Expect ~749 passed, 3 skipped on
  `claude/dax-research-direction-1ohi97`.

## Do not

- Do not open a post-period file before the tag exists.
- Do not re-run a power scenario that already succeeded.
- Do not re-open the 445/442/490 support question — it is settled.
- Do not promote α over β because α is less confounded.
- Do not drop Webb for being orthogonal to the other controls — §13b explains
  it as a distinct construct, patent exposure rather than computer use.
- Do not quote the unconditional 3.44% MDE, and never write "100% power".
- Do not delete and re-tag to clear a failed ordering check.
