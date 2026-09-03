# D1 resolved — primary specification changes from a discrete event stack to a continuous cumulative-dose design

**Status:** decided under PI delegation, 2026-08-18. Requires PI counter-signature
before it binds. Recorded as a §11 deviation to the W1 draft.

**Decided by:** the DAX seat, on explicit written delegation from the PI
("go ahead make decision for me D1").

**Seal status at decision time:** closed. No `v1.0-preregistered` tag exists.
`dax/data_raw/` and `dax/data_built/` contain no outcome data. Every quantity
consulted below is either pure date arithmetic on the frozen registry or a
power statistic computed on the synthetic fixture stamped
`NOT_EVIDENCE_SYNTHETIC_SMOKE_TEST`. **No estimated treatment effect exists or
was consulted.** This is a feasibility decision, which is what power analysis
is for — not a specification search, which requires results to search over.

## Decision criteria, fixed before the options were scored

An acceptable resolution had to satisfy all four:

1. **Feasible now** — at least three estimable events, or no dependence on an
   event count at all.
2. **Monotone in evidence quality** — completing the registry must not reduce
   identifying variation. The current rule fails this, and that failure is what
   makes the project's own W2 work self-defeating.
3. **Diagnostics preserved** — Decision 14's joint pre-event test must remain
   computable; a design with one pre-period month cannot separate a level shift
   from a trend.
4. **No nominal purity** — a rule may not achieve clean windows by declaring
   that events which actually occurred are absent.

## Options scored

| Option | Feasible | Monotone | Diagnostics | Real purity | Verdict |
|---|---|---|---|---|---|
| 1. Widen the window (±9/±12/±18) | no | no | yes | yes | **inert** — adjacency truncation binds, not nominal width; ±18 gives the same 2/1/1 as ±6 |
| 2. Relax 3+3 to 2+2 or 1+1 | only at 1+1 | no (2 under C) | **no** | yes | rejected — 1+1 destroys the pre-trend test |
| 5. Compound events within K months | at K=4 (3 events) | **no** (1 under B and C) | yes | yes | rejected as primary — collapses as the registry completes |
| 4. Pre-register a spaced subset (S=7) | yes (6 under C) | yes | yes | **no** | rejected — 11 of 17 origins dropped but still delivering dose inside the retained windows |
| **3. Continuous cumulative dose** | **n/a — no event selection** | **yes** | **yes** | **yes** | **ADOPTED** |

## Root cause, stated plainly

A stacked event study with clean windows presumes discrete, well-separated
shocks. By 2026 that premise is false: the registry carries 21 events across
41 months, frequently 1–3 months apart. The treatment is effectively
continuous. No parameterisation of a discrete design rescues it — each option
either collapses to one event (1, 2, 5) or manufactures purity by ignoring
events that actually happened (4).

The design was not mis-implemented. Its framing no longer matches the
data-generating process it is aimed at.

## The decision

**Primary specification.** The confirmatory analysis is a continuous
dose-response on the full monthly panel, using the `DAX_om` index the memo
already constructs in §2:

- Unit: person-month, ages 22–25, Nov 2021 → latest frozen month.
- Dose assignment: unchanged from §7 (most recent CPS occupation strictly
  before the reference month, ≤15-month lookback). D4 remains open and is not
  resolved here.
- Regressor: the continuous monthly `DAX_om` level, with the within-month
  increment reported alongside it. No event selection, no windows, no stacking.
- Design: occupation, calendar-month, industry×month, and frozen
  static-exposure-decile×month effects, plus the registered controls. Standard
  errors clustered on the original CPS occupation code.
- Identification: IC-1 restated for a continuous, time-varying dose under
  Callaway–Goodman-Bacon–Sant'Anna (2024). IC-2 and IC-3 carry over unchanged.
- Pre-trend test: Nov 2021 → Feb 2023, the interval before the first eligible
  event, where DAX movement is near zero by construction.
- Estimand: change in employment probability and unconditional weekly hours
  per 0.10 increment in DAX, over the observed common-support population.

**Secondary specification.** The discrete stack survives as corroboration
only, under the compound rule at K = 4 months (an extension of the
same-calendar-month compounding already pre-registered in §3.2, using its
existing joint pre-to-post state algorithm). It currently yields three
estimable composites. It is explicitly **not** confirmatory, carries its own
power statement, and is expected to degrade as the registry completes. A
disagreement between primary and secondary is reported, not adjudicated in
favour of whichever is significant.

**Why this satisfies criterion 2.** The primary requires no event selection at
all, so its identifying variation strictly increases as the registry is
completed: every newly verified event adds dose movement. The perverse
incentive is removed — W2 evidence work now improves the design instead of
destroying it, and the price panel becomes directly valuable rather than
self-defeating.

## What this costs, stated honestly

1. **The identification narrative is weaker.** There is no single discrete
   shock to point at. The design leans harder on conditional parallel trends
   and is more exposed to secular occupation-level trends correlated with AI
   exposure. Existing mitigations — static-exposure-decile conditioning,
   industry×month effects, Rambachan–Roth sensitivity at M̄ ∈ {0.5, 1, 2},
   permuted-mapping and backward-shuffled-price placebos — all carry over and
   now matter more, not less.
2. **The pre-trend window is short.** Roughly 16 months of near-zero DAX
   movement. That is the main analytical cost of this decision and must be
   reported as a limitation, not buried.
3. **The committed power result does not carry over.** It simulates a discrete
   four-event stack. A continuous-dose power calculation on pre-event CPS
   moments must be built before Gate 1. This makes the power rebuild
   mandatory, not optional.
4. **Decision 13(c) needs re-scoping.** Its ≥3-events condition is written for
   the OpenAI usage first stage; `simulate_power.py` currently enforces it as a
   global hard gate. Under the continuous primary that gate is misapplied and
   must be restricted to the first stage.

## Explicitly not decided here

- **D3** (Decision 11's pass bar is estimated from the data it judges) is
  independent of D1 and remains open. It must be frozen before any power
  standard is meaningful.
- **D4** (the pre-event occupation requirement excludes labour-market
  entrants) remains open. The continuous design inherits it unchanged.
- **F2** (three registry rows verified on insufficient evidence) remains open.

## Required before this binds

1. PI counter-signature on this file.
2. §§3, 4, 7, 9 of `design_memo_v1.md` rewritten to make the continuous design
   primary, with the stack demoted in place — the memo must not carry two
   competing primaries.
3. Continuous-dose power simulation built and passing a frozen standard
   (blocked on D3).
4. A dated deviation entry under §11, since this changes the pre-registered
   primary specification of a draft already reviewed by the red team. The red
   team reviewed the discrete design; its `CONDITIONAL_GO` does not transfer,
   and a re-review of the amended memo is required before Gate 1.
