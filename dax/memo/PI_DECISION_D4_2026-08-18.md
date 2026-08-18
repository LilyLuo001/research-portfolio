# D4 — the estimand is named (decided); the entrant companion is scoped (not decided)

**Status:** partially decided under PI delegation, 2026-08-18. Part 1 requires
counter-signature. Part 2 is deliberately left to the PI.

## Why this one is split when D1 and D3 were not

D1 and D3 were **defects**: a protocol that could not run, and a pass bar that
could not fail. Fixing a defect has one correct direction, so deciding it under
delegation was appropriate.

D4 is two different things wearing one label:

1. **A defect** — the memo never states what its primary estimand actually is,
   given the sample it constructs. That has one correct direction: say it.
   Decided below.
2. **A scope question** — whether the paper should *also* study the entrant
   margin. That is a research-agenda and budget choice with no defect-driven
   answer. Deciding it under delegation would be me choosing what your paper is
   about. Options are laid out; the choice is yours.

## Part 1 — DECIDED: name the estimand

§7 assigns dose from the most recent CPS occupation strictly before the event,
with a ≤15-month lookback, and drops persons with no such observation. For
ages 22–25 that systematically removes labour-market entrants: anyone not yet
observed in an occupation.

The memo reports this as an exclusion count. It never states the consequence:
**the primary estimand is conditional on prior employment.** It measures what
happens to young workers *already attached to* an exposed occupation — an
incumbent margin.

The memo must say so, in §7 and again wherever the estimand is stated:

> The primary estimand is the effect of AI exposure on the employment and hours
> of young workers with a prior occupational attachment. It is not an effect on
> labour-market entry. Persons with no pre-period occupation observation are
> outside the estimand by construction, not missing data, and the count and
> weighted share of such persons is reported.

This is a defensible estimand. What is not defensible is leaving a reader — or
a referee — to infer it from a lookback rule buried in the sample section.

**Additionally required:** because the proposal's 13% benchmark is drawn from
literature where the effect operates substantially through reduced *hiring*,
the memo must state plainly that its benchmark and its estimand are not the
same object, and that a null on the incumbent margin is not evidence against
the entrant-margin finding it benchmarks against.

## Part 2 — NOT DECIDED: whether to add an entrant companion design

The mechanism most associated with the 13% figure is reduced hiring of new
entrants. The current design cannot see it. Three options:

**(a) Disclaim only.** Ship the incumbent estimand, state the limitation,
recommend the entrant margin as future work. Cost: none. Risk: a referee asks
why the headline mechanism was excluded and the answer is a sample-construction
artefact rather than a considered choice.

**(b) Entrant companion as a registered secondary.** Build a cohort-level
design: for each month, the employment rate of young people with no prior
occupational attachment, against the DAX of the occupations that such cohorts
historically enter, using a frozen pre-period entry-occupation distribution.
Cost: a new dose construction (entry-mix weights), its own power budget, and
its own identification section — realistically an additional W-block. Risk:
the entry-mix instrument is weaker and needs its own defence.

**(c) Redefine the primary to cover both.** Reject. It would require imputing
an occupation for people who never had one, which is fabrication, and it would
merge two mechanisms into one coefficient that means neither.

**Recommendation: (b)**, if there is budget for one more W-block, because it
addresses the mechanism the paper is benchmarked against rather than working
around it. **(a)** is a perfectly respectable ship-it decision and costs
nothing. **(c)** should not be adopted under any budget.

Whichever you choose, Part 1 stands — the estimand must be named either way.

## Not resolved here

Nothing else. D1, D3 and F2 are closed; this is the last open item from the
2026-08-14 audit apart from Part 2 above.
