# YAX — research plan v1

> **SUPERSEDED by `RESEARCH_PLAN_v2.md` (2026-08-26).** Retained for revision
> history. v1 was written before the MDE was located and before the novelty
> gate ran. Its §5.2 falsification condition — ceiling power across the grid —
> **did not trigger**, and its §12.1 kill condition is retired accordingly. Do
> not execute from this file.

**Young-worker AI Exposure.** Third dissertation chapter. Independently
authored. Not the job-market paper.

*Plan date 2026-08-25. Supersedes `CHAPTER_SCOPE_v1.md`, which is retained for
its revision history. Predecessor project archived at
`../dax/memo/DAX_ARCHIVE_2026-08-25.md`.*

---

## 0. Why the project is renamed

DAX — Dynamic AI Exposure — set out to build a task-level capability index from
model price and capability histories. It is archived: it failed its own signed
feasibility condition when 0 of 22 model vintages were captured before fixed
withdrawal dates. Its estimand, its missing-mass results and its price panel
stand as computed; they are simply not what this chapter does.

YAX is a different object with a different estimand and a different data spine.
Sharing a directory with the archived work would keep implying otherwise.

The name is deliberately neutral about the claim. A name like "pre-registered"
would assert the very property that is not yet secured — the freeze has not
happened — and would become a liability if the seal ever broke. YAX says what
the project is about, not what it has proved.

## 1. The question

> Does young employment deteriorate in AI-exposed occupations after the ChatGPT
> release, tested on nationally representative data under a specification and a
> coverage rule frozen before any post-period outcome was opened, and reported
> against a measured minimum detectable effect?

## 2. The contribution

Not the question. Others ask it — see §8. The contribution is that this is the
only test of it that will have all three of:

1. **A specification frozen before the outcomes were visible.** The pre-period
   file was built outcome-blind; the post-period file is sealed and has never
   been opened. Every current participant in this debate — ADP-based and
   public-data alike — chose a specification after seeing outcomes.
2. **A measured MDE.** 999 repetitions on the real panel, so a null can be
   distinguished from an underpowered null. The literature's public-data nulls
   currently come with no statement of what they could have detected.
3. **A pre-specified exposure-coverage rule, with all variants reported.** The
   measurement choice is visible in every table rather than taken on trust.

A null result is therefore as publishable as a positive one, and that is by
construction rather than by hope.

## 3. What is already established

Real numbers, on real data, each with a receipt.

| fact | value | source |
|---|---|---|
| Wide CPS extract | 9,262,480 rows, 2017-01 → 2026-07 | IPUMS extract 9 |
| Outcome-blind pre-period file | 6,188,956 rows | derived |
| Occupation clusters | 490 | pre-period panel |
| Pre-period months | 66 | pre-period panel |
| Power vs 19% relative decline | 100% (999 reps) | power aggregate |
| Power vs 4.88% relative decline | 98.6% | power aggregate |
| Null rejection rate (nominal 5%) | **6.6%** | power aggregate |
| Interval coverage (nominal 95%) | **93–94%** | power aggregate |
| Exposure-route coverage, strict rule | **88.70%** — fails the 90% gate | coverage receipt |
| Excluded mass in top 25 target codes | 93.4% | coverage audit |
| Janitors / Cooks component coverage | 99.38% / 99.27% | coverage audit |
| Exposure–telework R² range | 0.09 (Eloundou α) → 0.58 (AIOE) | `measurement/AUDIT_RESULTS.md` |
| Effective occupations in α's residual | 28 of 669 | `measurement/AUDIT_RESULTS.md` |

Also built and passing: the full occupation bridge, the exposure lookup, a
PPML-equivalent power engine with regression tests, and the measurement audit
in `measurement/`.

## 4. What is not established

1. **The MDE itself.** Power was ≥98.6% everywhere on the first grid, so the
   grid never located the 80% point. A finer 1%–4.5% grid is required.
2. **Whether the power engine is honest.** See §5 — this is the live risk.
3. **Any post-period result.** Nothing has been estimated. The seal holds.
4. **Novelty position.** §8 lists four unverified claims about prior work.

## 5. Reading the power result honestly — BINDING

The power number is the foundation of this chapter, which makes over-reading it
the most expensive available mistake. Three standing constraints:

1. **Wild-cluster bootstrap is primary inference**, not a robustness row. The
   engine rejects at 6.6% against a nominal 5% and covers at 93–94%: inference
   is mildly oversized, and the headline MDE must be recomputed under the
   bootstrap before it enters the manuscript.
2. **The fine grid must show a gradient.** A sound design has power falling
   through 80% somewhere in the 1–3% range. **If power is still near 100% at a
   1% relative decline, treat that as an engine bug, not a strong design**, and
   do not proceed to the freeze until it is explained. Simulated power on a
   fitted DGP cannot capture misspecification or unmodelled shocks, and a
   simulation that reports ceiling power across an order of magnitude of effect
   sizes is describing its own smoothness.
3. **Never write "100% power."** Write the MDE with its bootstrap interval and
   the DGP's assumptions.

This section is the falsifiable check on the plan. If constraint 2 fails, the
chapter's premise is wrong and the plan changes before anything is estimated.

## 6. Design

**Population.** Ages 16–75. Young = 20–29 primary; 16–24 and 22–27 as
pre-specified alternates.

**Outcome.** Employment (`EMPSTAT` ∈ {10, 12}); unconditional weekly hours
secondary, zero-filled for the non-employed with the zero-fill reported both
ways.

**Weights.** `WTFINL` for employment. `EARNWT` with `MISH` ∈ {4, 8} for any
earnings outcome — `EARNWEEK` and `HOURWAGE` are outgoing-rotation-only and
`WTFINL` is the wrong weight for them.

**Treatment.** Occupation-level exposure, standardised to mean 0 / sd 1 over
the employment-weighted occupation distribution. `Post` = 1 from 2022-11.

**Telework.** Occupation-level Dingel–Neiman share only. **Never a person's own
`TELWRKHR`/`TELWRKPAY`** — those begin 2022-10 and are asked only of people
employed and at work, so they are post-treatment and conditioned on the
outcome. The occupation-level measure avoids that mechanical conditioning but
remains endogenous to employer return-to-office decisions; it is not exogenous
and must not be described as such.

**Estimating equation.**

    y_iot = β (Exposure_o × Young_i × Post_t) + γ (Exposure_o × Young_i)
            + δ (Exposure_o × Post_t) + α_o + λ_t + X_it + ε_iot

Clustered on occupation, with bootstrap inference per §5. Event-time version
uses months relative to 2022-11, 2022-10 omitted.

**Coverage rule.** Three columns in every table — A strict, B sibling-imputed
(primary), C renormalized — per `COVERAGE_RULE_PRESPEC_v1.md`.

## 7. Robustness dimensions

Each a pre-specified table, run once:

1. **Exposure measure** — all seven (AIOE, Eloundou α/β/γ × GPT-4/human), run
   identically. No measure is selected; disagreement is explained, not resolved.
2. **Coverage rule** — A/B/C as columns everywhere.
3. **Crosswalk vintage** — exact-code merge vs crosswalked. A reported
   robustness dimension, **not** a contribution: AIOE and Dingel–Neiman cover
   the SOC 2010 taxonomy in full, and the 96.7% group-15 figure measures the
   cost of merging without a crosswalk. See `CORRECTION_2026-08-25_vintage_gloss.md`.
4. **Pre-trends** — event-time pre-period coefficients, reported whatever they
   show, plus a 2018-11 placebo `Post` on the 2017–2019 window.
5. **Remote work** — Dingel–Neiman share interacted with `Young × Post`;
   exposure coefficient reported with and without, alongside the VIF.

## 8. Position in the literature — VERIFY BEFORE THE FREEZE

None of the following has been verified from this repository. Each is cheap to
check and each reshapes the introduction. Treat as claims to confirm.

| claim | consequence if true |
|---|---|
| Eckhardt & Goldschlag (EIG, 2025) chose AIOE for crosswalk accuracy, compared two crosswalk approaches, published data on GitHub | dimension 3 is a citation, not a finding. Reconcile against their file rather than rebuilding |
| EIG report findings "similar across all available measures" | do not frame the chapter as a measures horse-race |
| Budget Lab SDID finds nulls | the contested magnitude is already public; position against it explicitly |
| Brynjolfsson, Chandar & Chen (Aug 2026) added interest-rate and telework robustness | dimension 5 becomes a supporting appendix, not a contribution |

**This is a gate, not an open item.** It runs before the design freeze.

## 9. The seal protocol

The pre-registration is the contribution. It cannot be reconstructed after the
fact, so the ordering is the one thing in this project that must not slip.

1. `COVERAGE_RULE_PRESPEC_v1.md` committed. *(done)*
2. Fine power grid run, gradient confirmed per §5.2.
3. MDE recomputed under wild-cluster bootstrap.
4. Novelty gate §8 answered.
5. `DESIGN_FREEZE_v1.md` committed — estimating equation as it will be run,
   empty table shells, sha256 of the analysis panel.
6. Tag `v1.0-preregistered`.
7. **Only then** may a post-period outcome be opened.

Opening a post-period file before step 6 is the single irreversible mistake
available in this project.

**The protocol is machine-checked.** `yax/gates.py` verifies seven conditions —
including, in git history rather than in prose, that
`COVERAGE_RULE_PRESPEC_v1.md` is an ancestor of the tag:

    python yax/gates.py --power-aggregate <aggregate>.json

Each gate reports `PASS`, `FAIL` or `BLOCKED`, and the exit status is non-zero
unless all seven pass, so an unchecked condition cannot be mistaken for a met
one. `briefs/YV_VERIFY.md` is the independent verification task that runs after
each milestone, in a fresh session and preferably a different model family,
because every one of this project's three false claims was caught by external
review and none by self-check.

## 10. Deliverables

| item | target |
|---|---|
| manuscript | 25–35 pages |
| principal figures | 3–4 |
| main tables | 4–6, each with A/B/C coverage columns |
| measurement appendix | `measurement/` — common support, vintage, residual concentration |
| replication package | code + public inputs + receipts; **no licensed microdata** |

Ship the IPUMS extract specification and extract id so a reader with their own
account can rebuild the panel. Verify the package builds from a clean clone
with no private path.

## 11. Timeline

Pre-freeze work is days, not weeks — the expensive parts are done. Three to
five calendar weeks from the freeze to a complete draft, solo, with no second
person to unblock a failure.

| week | work |
|---|---|
| 0 | fine grid, bootstrap, novelty gate, push to origin, freeze, tag |
| 1 | Tables 1–3, Figures 1–2 |
| 2 | Tables 4–6, Figures 3–4 |
| 3–4 | manuscript, appendix, replication package |

## 12. Kill conditions

Stated in advance so they are tests rather than judgement calls:

1. **The fine grid shows no gradient** and the engine cannot be shown correct.
   The power claim is then unsupported and the chapter's premise fails.
2. **§8 reveals the pre-registered-power test already exists** in public. Then
   the contribution is gone and the remaining work is a replication note.
3. **The seal is broken before step 6.** The chapter can still be written but
   must be labelled post-hoc, and its central claim is lost.

None of these is currently triggered.

## 13. Standing rules

From `../CLAUDE.md`, plus one earned in this project:

- LLM output is not a source of facts. Numbers come from code run on real data
  or an extraction with a raw-source locator.
- Don't know → stop. `NEED_HUMAN`, never guess-fill.
- Never specification-search. The first run of a pre-specified table is the
  reported run.
- Licensed microdata never enters the git work tree. Never `git add -A`.
- **A sentence describing a computed number must be checkable against the same
  artifact that produced the number.** Added after three instances of correct
  arithmetic carrying an overstated gloss — see
  `CORRECTION_2026-08-25_vintage_gloss.md`.

## 14. Dependency on archived work

`measurement/` reads `../dax/data_built/oews_wages.parquet` — OEWS 2021
employment, built under DAX and carrying its own lineage. The path is left
pointing at the archived project rather than copying the file, so the
dependency stays visible and the receipt chain stays intact.
