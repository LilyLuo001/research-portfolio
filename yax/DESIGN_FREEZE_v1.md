# Design freeze v1.0

**Written 2026-08-27, before any post-ChatGPT outcome has been opened.**

This document fixes the specification of the YAX chapter. The tag it supports is
`v1.0-design-freeze`. It is **not** a preregistration: nothing here was lodged
with an external registry, and the chapter must never be described as
preregistered. What the tag buys is an ordering that a reader can check in git —
the specification existed before the outcomes were seen.

**Chapter question.** Among occupations with comparable pre-existing
computerization, did employment of workers aged 22–25 decline relative to 26–65
after ChatGPT, in occupations with greater LLM exposure?

## 1. The estimating equation, exactly as it will run

    E[N_oat] = exp[ γ_oa + δ_ot + λ_at
                    + β_AI (AI_o × Young_a × Post_t)
                    + β_C  (Comp_o × Young_a × Post_t) ]

Poisson pseudo-maximum-likelihood on occupation × age-group × month employment
counts `N_oat`. Fixed effects are occupation × age-group (`γ_oa`), occupation ×
month (`δ_ot`) and age-group × month (`λ_at`).

The fixed effect is written `γ_oa` here, not `α_oa` as in plan §5, purely to
keep it distinct from the Eloundou α measure in §2 below. It is the same term.

- **Young** = ages 22–25. **Comparison** = ages 26–65.
- **Post** = 2022-12 onward.
- **Clustering:** on occupation.
- **Primary inference:** wild cluster bootstrap, Rademacher weights, clustered
  on occupation, 999 draws, with the critical value calibrated independently of
  the point estimate. The bootstrap is the primary inference, not a robustness
  check; the analytic cluster-robust standard error is reported beside it.
- **Never assign a current occupation to a non-employed person.** The
  occupation lookup's role is to classify employment, not to impute a recent
  occupation onto someone who is not employed.

The power simulation ran this same equation in its grouped-binomial conditional
equivalent form (`yax/power/joint_computerization_power.py`), on the observed
joint distribution of AI exposure and computerization, preserving their
correlation.

## 2. β is primary, α is the pre-specified contrast

| measure | definition | role |
|---|---|---|
| Eloundou **β** = E1 + ½E2 | tasks an LLM accelerates, including those needing complementary LLM-powered software | **primary** |
| Eloundou **α** = E1 | tasks an LLM accelerates on its own | **pre-specified contrast**, reported in every main table |

β stays primary because it is the source paper's headline definition — a
conceptual choice, made before any estimate existed.

**α is not promoted, and specifically not promoted for being less confounded.**
Plan §2 bars selecting the exposure measure on any separability statistic. On
the frozen support α does separate more cleanly from computerization than β
does (§5 below), and that is precisely the kind of fact that must not be
allowed to reorder the two. If the gradient appears under β but not under α,
that is evidence about complementary software and is reported as such.

## 3. Computerization: five measures, all reported

All five are reported. They are **not** substitutes for one another and no one
of them is a fallback for another.

| measure | column | standing |
|---|---|---|
| Webb software exposure | `webb_pct_software` | primary computerization control |
| O\*NET *Interacting With Computers*, `4.A.3.b.1` | `onet_computers_importance` | first robustness; contains no AI content |
| O\*NET same descriptor, level scale | `onet_computers_level` | robustness |
| Routine-task intensity, Autor–Dorn | `rti_autor_dorn` | robustness |
| Frey–Osborne automation probability | `frey_osborne_probability` | **secondary only** — bundles AI and robotics into automation risk rather than measuring prior computerization |

**Webb's software measure is the computerization primary. His AI measure is
never the computerization control.**

Webb is retained despite being close to orthogonal to the AI measures. Plan
§13b explains why: Webb's exposure is built from *patent* text, so it measures
what has been mechanized, not what a worker's computer use looks like. Low
correlation with an LLM task-exposure measure is the expected result of
measuring a different construct, not evidence of a failed join. The ranked
occupation audit in `yax/measurement/CONSTRUCT_VALIDITY.md` confirmed the
rankings are coherent. **Orthogonality is not grounds for dropping it.**

**AIOE is barred from the computerization role.** It is built from AI
capability benchmarks mapped onto O\*NET abilities; using it as the control
would put AI on both sides of the equation. It is an alternative *AI* measure.

## 4. Exposure coverage: three rules, by reference

The three coverage rules are specified in `yax/COVERAGE_RULE_PRESPEC_v1.md`,
committed 2026-08-25, before this freeze. That ordering is checked
mechanically by the `prespec_before_tag` gate, in git rather than in prose.

- **Rule A — strict.** Include an occupation only if every SOC component is
  exposure-scored. Achieves 88.70% coverage and fails the predeclared 90% gate.
- **Rule B — sibling-imputed, thresholded, `s_c ≥ 0.95`. PRIMARY.**
- **Rule C — renormalized, `s_c ≥ 0.95`, scored components only.**

All three appear as three columns in every results table — not one primary with
two footnotes. The 88.70% failure of Rule A is reported, not patched.

## 5. Power: conditional MDEs on the frozen support

Simulated on pre-period cells only. Synthetic post months are built from
pre-period donors; **no post-period outcome was opened**. Every scenario record
carries `post_outcomes_read: false`.

The computerization coefficient is **fixed at β_C = log(0.95)** per
employment-weighted standard deviation — a design stress parameter, not an
estimate from outcomes.

Conditional MDE80, as a relative decline in young-worker employment, with 95%
Monte Carlo intervals over 999 bootstrap draws:

| AI measure | computerization control | clusters | VIF | partial variance of AI | effective occupations | null size | **MDE80** | 95% MC interval |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| β | `onet_computers_importance` | 465 | 2.738 | 0.365 | 63.2 | 0.041 | **2.27%** | 2.22% – 2.32% |
| β | `webb_pct_software` | 468 | 1.003 | 0.997 | 53.3 | 0.036 | **1.24%** | 1.22% – 1.25% |
| α | `onet_computers_importance` | 465 | 1.102 | 0.908 | 31.1 | 0.060 | **1.36%** | 1.34% – 1.39% |
| α | `webb_pct_software` | 468 | 1.017 | 0.983 | 17.4 | 0.058 | **1.23%** | 1.21% – 1.24% |

**O\*NET and Webb bracket the confounding range.** Against O\*NET the AI
measure is materially collinear with the control (VIF 2.738, 36.5% of β's
variance surviving); against Webb it is nearly orthogonal (VIF 1.003). The true
degree of confounding is not known, so both ends are carried rather than one
being chosen.

Sensitivity to the fixed computerization effect, bracketing log(0.95) by zero
and log(0.90):

| computerization control | β_C = 0 | β_C = log(0.95) | β_C = log(0.90) |
|---|---:|---:|---:|
| `onet_computers_importance` | 2.22% | 2.27% | 2.22% |
| `webb_pct_software` | 1.22% | 1.24% | 1.19% |

The MDE is insensitive to β_C across this range, which is the reassuring
direction: the design's resolution does not depend on guessing the
computerization effect correctly.

**Two figures are barred from this chapter.** The obsolete *unconditional*
3.44% MDE must never be quoted — it describes a model without the
computerization control and so answers a different question. And no scenario may
be described as having "100% power"; the simulated rejection rate reaches 1.000
only at a 16.47% effect, far above any contested magnitude.

Gate results on this aggregate:

- `gradient` **PASS** — power is bracketed in all four scenarios, rising from
  0.110–0.287 at a 0.50% effect to 1.000 at 16.47%. Neither failure branch
  fires: power is not at the ceiling at the smallest tested effect (which would
  indicate an engine bug), and it does reach 80% within the grid (so §12.4 is
  not triggered).
- `calibration` **PASS** — bootstrap null sizes 0.036–0.060 against a nominal
  0.05, with bootstrap fields recorded as §5.1 requires.

**§12.4 does not trigger.** The kill condition is a conditional MDE approaching
the contested magnitude. The contested young-worker declines in the literature
are an order of magnitude larger than the 1.2–2.3% this design resolves.

## 6. The frozen support

The panel this freeze pins, sha256:

4b8c8b96caeebc4121ad4914adbadf7ebfa98d677a80b32b78a9f905956ea800

| artifact | sha256 |
|---|---|
| `young_relative_employment_cells_v1.csv` (pre-period cells) | `4b8c8b96caeebc4121ad4914adbadf7ebfa98d677a80b32b78a9f905956ea800` |
| `yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv` | `c6eb70623ea598bfc41f2352391add7a342a8809a4e57b02f2af0e75dd0223f8` |
| `yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv` | `352cb40834ec83225f747d316eb3e03fce1d1c5c65d80720c558177f85801fdd` |

- **490 balanced Census-2018 occupation clusters × 66 months, 2017-01 through
  2022-11.** Balanced means present in every month of the window.
- Measure overlap reduces this to **465** clusters under O\*NET and **468**
  under Webb. Common-support employment share is 95.39% and 98.12%.
- **43 planned post months.**
- The cells file lives outside the git work tree, under the private SCC root.
  Licensed person-level microdata never enters this repository; only the
  occupation × age-group × month aggregates and this hash do.

The 445 / 442 / 490 reconciliation is settled and is not reopened here. The
smaller counts are OCC2010 artifacts whose lookup role can inherit a recent
occupation for a non-employed person; the 490 figure is the Census-2018 panel of
employed workers, and it is the one that governs.

## 7. Table shells

Empty. Filled only after the tag.

### Table 1 — AI versus computerization: measurement and identifying support

| AI measure | comp. measure | VIF | partial var. of AI | effective occupations | common support emp. share |
|---|---|---|---|---|---|
|  |  |  |  |  |  |

### Table 2 — Joint AI–computerization employment estimates (central table)

| | β, Rule A | β, Rule B | β, Rule C | α, Rule A | α, Rule B | α, Rule C |
|---|---|---|---|---|---|---|
| AI × Young × Post |  |  |  |  |  |  |
| Comp. × Young × Post |  |  |  |  |  |  |
| wild bootstrap p |  |  |  |  |  |  |
| occupations |  |  |  |  |  |  |

### Table 3 — Event study and pre-period placebos

| period | β coefficient | 95% CI | placebo |
|---|---|---|---|
|  |  |  |  |

### Table 4 — Alternative AI and computerization measures on common support

| AI measure | comp. measure | coefficient | wild bootstrap p |
|---|---|---|---|
|  |  |  |  |

### Table 5 — Crosswalk decomposition (§7.1's four rows, one fixed scale)

| row | contribution | scale |
|---|---|---|
|  |  |  |

### Table 6 — Entrant hiring versus separations, and the post-2025 extension

| margin | coefficient | 95% CI |
|---|---|---|
|  |  |  |

## 8. Environment

- **Repository:** `github.com/LilyLuo001/research-portfolio`
- **Branch:** `claude/dax-research-direction-1ohi97`
- **Test suite run in:** the SCC worktree
  `/projectnb/econdept/qluo/yax-y1d-20260827`, branch
  `task/yax-y1d-20260827`, whose tree content matches the branch tip.
- **Python:** `/usr3/graduate/qluo/portfolio/.venv/bin/python`. The SCC default
  interpreter is 3.6.8 and has no pandas; it is not usable for this project.
- **Cluster:** SGE, queue `academic-pub`, project `econdept`, `h_rt=02:00:00`,
  `mem_per_core=4G`. The eight power scenarios ran as jobs 7330197–7330204.
- **Simulation seed:** 20260827. 999 repetitions per effect, 999 bootstrap
  draws, 999 MDE bootstrap draws.

**`pytest -q` — 751 passed, 3 skipped.**

The three skips, with reasons — all are optional third-party dependencies absent
from the venv, and none is in the YAX path:

| test module | reason |
|---|---|
| `dax/tests/test_mapA_runner.py` | could not import `torch` |
| `dax/tests/test_mapA_v2_prediction.py` | could not import `sklearn` |
| `dax/tests/test_w4_harness.py` | could not import `cryptography` |

## 9. What this freeze does not settle

- **Webb's data file is not pinned by hash.** The only distribution route on the
  author's site is an email-gated form. The measure's taxonomy is settled —
  Webb uses `occ1990dd` (Dorn 2009, extended by Deming 2017), which is **not**
  IPUMS `OCC1990` and requires Dorn's crosswalk — but the file's own URL,
  sha256 and row count remain unverified. See §6.1.
- **The extract carries `OCC1990`,** so the crosswalk route is available without
  amending the extract.
- **October 2025 has no CPS sample** — a real one-month hole from the federal
  shutdown, not a coverage defect in any measure.
