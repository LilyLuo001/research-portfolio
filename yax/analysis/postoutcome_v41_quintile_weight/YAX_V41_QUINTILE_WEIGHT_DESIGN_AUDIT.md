# YAX V4.1 Quintile-Weight Design Audit

**Audit status:** COMPLETE BEFORE THE V4.1 SENSITIVITY.

**Design-freeze tag:** `v1.1-design-freeze`  
**Annotated-tag object:** `74d97a9b07e0cbedda2c646c5eed5938b8506f81`  
**Peeled design-freeze commit:** `22fbf7924809b7a535e31ae0ab68f5b113ce8078`

This audit reads the pre-outcome record rather than inferring intent from the
V4 manuscript. The decisive distinction is between (i) a rule saying that
occupations are weighted by employment and (ii) a rule saying which calendar
months supply that employment. The former was frozen; the latter was not.

## Authoritative language

| Artifact | Exact language | Interpreted temporal window | Authority level |
|---|---|---|---|
| `DESIGN_FREEZE_v2.md`, §4 | “All simulations use only the sealed 2017-01–2022-11 cells and create synthetic post months from pre-period donors.” | Explicitly pre-period for the **power simulations**; does not separately state the eventual production-quintile window. | Highest: signed design-freeze document at the tag. |
| `DESIGN_FREEZE_v2.md`, §4.1 | “`Q5–Q1` is defined by employment-weighted exposure quintiles on each scenario's estimation support, with tied scores kept together and Q2–Q4 separately absorbed.” | Employment weighting and scenario support are explicit; the temporal window supplying the weights is not stated. | Highest: operative estimand language in the signed freeze. |
| `DESIGN_FREEZE_v2.md`, §5.1 | “The cells contain 490 balanced Census-2018 occupation clusters × 66 months, 2017-01 through 2022-11.” | Describes the sealed precision input, not an explicit instruction for outcome-stage quintile weights. | Highest: frozen input record. |
| `RESEARCH_PLAN_v5.md`, Test C | “Hold **everything** fixed — same CPS data, population, occupation support, occupation vintage, standardisation, time period, outcome, fixed effects, inference and estimator — then **change only the definition of X**.” | Requires consistency across exposure comparisons but does not define which months supply employment weights. | High: live plan consolidated by the freeze. |
| `RESEARCH_PLAN_v5.md`, §7.3 | “Define a literature-comparable contrast — **Q5–Q1** — and compute **both the benchmark and the MDE on that same estimand**.” | Defines the contrast and common scale, not the weight window. | High: live plan consolidated by the freeze. |
| `FREEZE_AMENDMENT_2026-08-27.md`, §3 | “Define **Q5–Q1** and compute both the benchmark and the MDE on that one estimand.” | Defines Q5–Q1, but contains no temporal weighting rule. | High: pre-outcome amendment incorporated into v1.1. |
| `FREEZE_AMENDMENT_2026-08-29_PAIRED_PRECISION.md` | “For the explicitly frozen pair, this is the Q5–Q1 coefficient under Eloundou β minus the Q5–Q1 coefficient under Eloundou α, estimated on their common occupation support.” | Defines the paired coefficient object and support; contains no temporal weighting rule. | High: final pre-outcome amendment incorporated into v1.1. |
| `POWER_NOTE_v3.md` | “The AI effect is the employment-weighted Q5-Q1 log coefficient, with Q2-Q4 separately absorbed.” | Does not name the employment-weight calendar window. | Supporting pre-outcome precision note. |
| `JOINT_POWER_AGGREGATE_v3.json` | `"quintile_definition": "employment-weighted quintiles on scenario estimation support; equal scores are never split"` | Does not name the employment-weight calendar window. | Machine-readable pre-outcome precision receipt. |
| `PAIRED_DIFFERENCE_PRECISION_v2.json` | `"q5_q1_definition": "employment-weighted quintiles on pairwise common occupation support; Q5 coefficient relative to Q1 with Q2-Q4 separately absorbed"` | Does not name the employment-weight calendar window. | Machine-readable pre-outcome paired-precision receipt. |
| `power/joint_computerization_power.py::prepare` at the freeze commit | Rejects cells after `2022-11`; constructs `weights = (young + older).sum(axis=1)` on those cells; passes the weights to `weighted_quintiles`. | The executed power exercise necessarily uses 2017-01–2022-11 employment because protected post-period outcomes were unavailable. The code does not state that this must be the production-outcome rule. | Pre-outcome implementation evidence, subordinate to the design text. |
| `power/paired_equivalence_power.py::prepare` at the freeze commit | Rejects cells after `PRE_END`; constructs `weights = (young + older).sum(axis=1)` and passes them to both measures' quintile builders. | Necessarily pre-period for the paired precision simulation; no production-window instruction. | Pre-outcome implementation evidence, subordinate to the design text. |
| `tests/test_joint_computerization_power.py` at the freeze commit | Tests the post window and verifies that weighted quintiles preserve ties and contain five bins. | No test of the calendar months used to construct employment weights. | Pre-outcome unit test. |
| `tests/test_paired_equivalence_power.py` at the freeze commit | Tests the post window, rank invariance, and that equal scores are not split. | No test of the calendar months used to construct employment weights. | Pre-outcome unit test. |
| `analysis/run_frozen_v11.py` | Not present at `v1.1-design-freeze`; first introduced in commit `557abbd0732d7fd73f9d61e7f8b36a884bd1db36` after the tag. | Cannot supply a missing frozen instruction. Its implemented rule must be audited separately. | Outcome-stage implementation, not pre-outcome design authority. |
| `tests/test_frozen_outcome_analysis.py` | Not present at `v1.1-design-freeze`; introduced with the outcome-stage implementation. It tests tie ordering/five groups, estimator recovery, transition, gap, and reference month. | Does not test the employment-weight calendar window. | Outcome-stage implementation test, not pre-outcome design authority. |

## Classification

### Verdict 3 — Freeze ambiguity

The frozen design **specified employment weighting but did not clearly define
the temporal window** used to form exposure quintiles in the protected-outcome
analysis.

The pre-outcome power engines used 2017-01–2022-11 employment because their
authenticated inputs contained only pre-period outcomes. That fact establishes
the weighting rule used in the precision simulations. It does not, without an
explicit carry-forward instruction, establish whether the production estimator
had to retain those pre-period weights or recompute weights on its full static
estimation sample.

Accordingly:

- this is **not Verdict 1**: no frozen sentence explicitly requires the full
  108-month static window or the inclusion of post-period employment;
- this is **not Verdict 2**: no frozen sentence explicitly requires the
  outcome-stage estimator to use pre-period-only employment weights;
- neither the historical full-period implementation nor the cleaner
  pre-period sensitivity may be described retrospectively as the uniquely
  pre-specified temporal weighting rule.

The historical confirmatory result remains the result as executed. The V4.1
pre-period-weighted estimate is a post-outcome supplementary sensitivity to an
underspecified construction choice.

## Artifact authentication

At the V4.1 branch base, the frozen files retain their recorded SHA-256 values:

| Artifact | SHA-256 |
|---|---|
| `DESIGN_FREEZE_v2.md` | `47a210b5a3007006ddd8363338cdae4d513c37693e6fe2d4847c362b01dbe988` |
| `RESEARCH_PLAN_v5.md` | `ec6478bf1e85a431501dca54e78bd160a5330890dd0e02c235e52601422eab93` |
| `FREEZE_AMENDMENT_2026-08-27.md` | `4a7822b3b7e6f2a4ddf2205ab1babcdb791a6f3743ddd59bcc3d891bf15b3289` |

