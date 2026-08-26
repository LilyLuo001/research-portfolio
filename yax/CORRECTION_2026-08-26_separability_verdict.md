# Correction — "NOT SEPARABLE" was the wrong verdict on the right number

**Date:** 2026-08-26. **Raised by:** external review. **Verified:** in repo.

## The error

`computerization_support.py` v1 discretized AI exposure at its employment-
weighted 75th percentile, crossed it with teleworkable == 0, and labelled any
measure whose resulting cell held under 5% of employment **NOT SEPARABLE**. It
concluded that "for AIOE a horse-race regression is not identified", and
`RESEARCH_PLAN_v2.md` §8a built its primary approach on that conclusion —
timing rather than controls.

**The cell shares are correct. The verdict is not.**

A continuous conditional model is identified off the partial variance of AI
exposure after projecting out computerization, not off a 2×2 cell. Cutting a
continuous regressor into quadrants discards most of the identifying variation:

| measure | R² | partial variance | VIF | SE inflation | est. conditional MDE | v1 cell | v1 verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| AIOE | 0.5792 | **42.1%** | 2.38 | 1.54× | 5.63% | 1.61% | NOT SEPARABLE |
| Eloundou α | 0.0909 | 90.9% | 1.10 | 1.05× | 3.87% | 10.48% | SEPARABLE |
| Eloundou β | 0.4208 | **57.9%** | 1.73 | 1.31× | 4.82% | 3.22% | NOT SEPARABLE |
| Eloundou γ | 0.4537 | 54.6% | 1.83 | 1.35× | 4.96% | 1.66% | NOT SEPARABLE |

Eloundou β has **57.9%** of its variance orthogonal to the computer proxy while
its clean cell holds 3.22% of employment. Those describe different things, and
only the first bears on identification. Against a contested magnitude of 19%,
even AIOE — the worst case — retains 3.4× headroom over its conditional MDE.

**The horse race is identified.** A joint AI-plus-computerization model is the
right primary specification, and v2 §8a's reasoning for demoting it was wrong.

## Why this one is worse than the previous three

`CORRECTION_2026-08-25_vintage_gloss.md` records three instances of correct
arithmetic carrying an overstated verbal gloss. This is the fourth, and it
repeats a mistake **this project had already written down**:
`measurement/CORRECTION_2026-08-25.md` §3 is titled *"The off-diagonal share is
not a common-support diagnostic."* A gate was then built around a near-identical
discretized statistic, and the standing rule added after the third instance —
that a sentence describing a computed number must be checkable against the
artifact producing it — did not catch it, because the sentence *was* checkable
against the cell share. It was the wrong number to be describing.

## The rule that follows

The existing rule is necessary and insufficient. Add:

> **State which statistic answers the question before computing one.** A
> diagnostic must be justified by the estimator it is meant to inform. For a
> continuous conditional model that is partial variance, VIF and conditional
> MDE — never a discretized cell share, however carefully the cell is cut.

## What changed

- `computerization_support.py` now leads with partial variance, VIF, SE
  inflation and an estimated conditional MDE. The clean cell is retained as a
  descriptive aid and as the source of the named divergence occupations, which
  remain genuinely useful for presentation.
- The `SEPARABLE` / `NOT SEPARABLE` verdict field is removed rather than
  rewritten. It should not have existed.
- `gates.py::gate_computerization` no longer keys on the cell floor.
- `RESEARCH_PLAN_v3.md` re-centres on the joint model as primary, with timing
  demoted to supporting evidence.

## What was right

The underlying concern stands and the advisor was correct to raise it: AIOE is
heavily collinear with computer-based work at R² = 0.58, the confound is real,
and it must be addressed before the freeze. Only the claim that it *cannot* be
addressed by conditioning was wrong.
