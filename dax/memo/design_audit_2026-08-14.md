# DAX W1 design audit — 2026-08-14

Audit of the W1 pre-registration package against the memo's own specification.
Method: execute each rule the memo states against the data the memo ships.
Every finding below is reproducible from the repository with no network access
and no privileged data.

The outcome seal was not opened. No `v1.0-preregistered` tag exists or was
created. Nothing in this audit authorizes outcome work.

## Resolution status as of 2026-08-18

| # | State | Where |
|---|---|---|
| D1 | **RESOLVED** — continuous cumulative-dose primary | `PI_DECISION_D1_2026-08-18.md` |
| D2 | **RESOLVED** — primary engine rebuilt; stacked engine demoted and labelled | `power_calcs/simulate_power_continuous.py` |
| D3 | **RESOLVED** — pass bar frozen and external, fail-closed | `PI_DECISION_D3_2026-08-18.md` |
| D4 | **PART 1 RESOLVED** (estimand named); Part 2 (entrant companion) left to the PI | `PI_DECISION_D4_2026-08-18.md` |
| F2 | **RESOLVED** — 5 rows demoted, `date_conflict` column added, rule enforced in the validator | `validate_event_registry.py` |

All decisions require PI counter-signature before they bind. None opened the
outcome seal; no tag exists.

## Summary

| # | Finding | Severity | Reproduce |
|---|---|---|---|
| D1 | §3.2 leaves 2 estimable events; the power engine requires 3 | blocker | `python dax/memo/validate_window_survival.py` |
| D2 | The power simulation does not implement §3.2 | blocker | `grep -n "range(-6, 7)" dax/memo/power_calcs/simulate_power.py` |
| D3 | Decision 11's pass bar is estimated from the data it judges | serious | rerun `simulate_power.py` on a 3-event dose file |
| D4 | The sample excludes labour-market entrants | substantive | `dax/memo/design_memo_v1.md` §7, lookback rule |
| F2 | Three registry rows are `verified` on evidence the memo calls insufficient | should-fix | see table below |

D1–D3 are pinned by `dax/tests/test_window_survival.py`. They cannot silently
reappear.

## D1 — The stacking protocol cannot deliver an estimable design

`validate_window_survival.py` implements §3.2 verbatim and is checked against
the memo's own worked example (April/December origins eight months apart:
April keeps May–July, December keeps September–November, August excluded as
the tied midpoint). It reproduces that example exactly, so the implementation
is the memo's rule.

Applied to the registry:

| Scenario | Monthly origins | Estimable |
|---|---|---|
| A — rows currently `eligible` (the power sim's event set) | 4 | **2** |
| B — every date-`verified` row eligible | 14 | **1** |
| C — registry completed, every non-excluded row eligible | 17 | **1** |

GPT-4.1 (2025-04) and GPT-5 (2025-08) are four months apart, so each retains a
single clean month on the facing side and both fail the three-per-side
requirement. Only GPT-4 and GPT-4o survive.

Two consequences:

1. **The design is infeasible as written.** `simulate_power.py` raises
   `ValueError: approved minimum estimability requires at least three events`
   at two events. The protocol produces an event set its own power engine
   refuses.
2. **The rule is non-monotone in evidence quality.** Completing the registry
   *reduces* estimable events, because eligibility drives adjacency and
   adjacency truncates windows. The design currently appears workable only
   because sixteen of twenty-one rows are unresolved. Diligent W2 sourcing
   makes identification worse.

Consequence (2) is the sequencing constraint: **§3.2 must be decided before or
alongside W2**, not after. Otherwise the price and mapping work completes and
then cannot be used.

Candidate resolutions — all `[PI-DECISION]`, none selectable by an agent, and
deliberately not chosen here: widen the window; relax three-per-side; permit
overlapping stacks with explicit contamination controls; pre-register a fixed
well-spaced event subset and treat the rest as descriptive chronology.

## D2 — The power simulation does not implement §3.2

`simulate_power.py:183` gives every event the full window:

```python
for event_time in range(-6, 7):
```

No adjacency, no midpoint truncation, no three-per-side test. The committed
result therefore rests on four events × 13 months = 52 event-months, where
§3.2 permits two events × 25 months. `"adequately_powered": true` is computed
on a stack the pre-registration does not authorize, and the margin it clears
by is 2.2% (MDE 0.00816 against a 0.00834 threshold).

The power result must be re-derived once §3.2 is settled. It should not be
quoted to the PI in its current form.

## D3 — Decision 11's power standard is self-validating

Decision 11 sets the employment bar at `min(6.5pp, ½ × baseline_employment_gap)`.
`baseline_employment_gap` is estimated from the data and depends on which
events are in the stack. Rerunning the committed simulation on three events
instead of four:

| Events | baseline gap | pass bar | MDE80 | Passes |
|---|---|---|---|---|
| 4 | 0.01667 | 0.00834 | 0.00816 | yes, by 2% |
| 3 | 0.04746 | 0.02373 | 0.00974 | yes, by 144% |

Dropping an event made the estimator 19% worse and the bar 185% looser. A
standard that moves with the specification it judges is a specification-search
channel, which `CLAUDE.md` forbids by name. The gap must be frozen against a
fixed pre-period and event set, or replaced with an absolute economic
benchmark, before the bar means anything.

Note also that in the committed run both education splits already report
`adequately_powered: false` for employment. §7 treats that split as unable to
carry headline claims; it should additionally state plainly that it is
underpowered.

## D4 — The sample may exclude the margin the paper is about

§7 assigns dose from the most recent CPS occupation strictly before the event
(≤15 months) and drops persons with no such observation. For ages 22–25 that
removes labour-market entrants.

The 13% payroll benchmark the design targets operates substantially through
reduced *hiring* of new entrants rather than separations of incumbents. The
primary estimand therefore conditions on prior employment and is structurally
silent on the headline mechanism. The memo reports the exclusion as a count
and never discusses its effect on the estimand. Neither the memo nor the
independent red team raises it.

This is not necessarily a defect — an incumbent-margin estimand is defensible
— but it must be stated as the estimand, and the entrant margin either
addressed as a companion design or explicitly disclaimed.

## F2 — Registry verification statuses are inconsistent

The memo's standard: a model page confirms identity, not an independent
release date. `GPT56_FAMILY_LAUNCH` is `pending_second_date_locator` for
exactly that reason. Three rows carry `verified` on the same or weaker
evidence:

| Row | Dated snapshot | source_2 | Status |
|---|---|---|---|
| `GPT54_MINI_NANO_LAUNCH` | none | model page | `verified` — identical shape to the pending row |
| `O1_PREVIEW_LAUNCH` | none | deprecations page (dates retirement, not release) | `verified` |
| `GPT4_TURBO_PREVIEW` | none | deprecations page | `verified` |

Separately, `GPT55_LAUNCH` carries `api_effective_date` 2026-04-24 against a
snapshot dated 2026-04-23. The note says both dates must remain visible, but
the schema has no field to hold the second date, so downstream consumers see
one value and the conflict is lost.

`validate_event_registry.py` cannot catch either issue by construction — it
checks provenance shape and says so honestly. Suggested remedy, for PI
approval: require `verified` to rest on a dated snapshot matching
`api_effective_date` or on a source that is not a model/deprecations/pricing
page, and add a `date_conflict` column so conflicts survive machine-readably.

None of the four `eligible` rows is affected, so no downstream artifact is
currently contaminated.

## What the audit did not cover

- **Locator URLs were not verified to resolve.** `openai.com` and
  `web.archive.org` are blocked by the execution environment's egress policy.
  No fabricated value was found anywhere in the repository, but "the cited
  pages say what the registry claims" remains unproven, not disproven. It
  needs a host with egress.
- **No real CPS data was examined.** `dax/data_raw/` and `data_built/` hold no
  IPUMS file; only the extract receipt is in the repository. Every power
  number discussed above is from the synthetic fixture, correctly stamped
  `NOT_EVIDENCE_SYNTHETIC_SMOKE_TEST`.

## On the review process itself

The independent cross-vendor red team ran three substantive rounds and reached
`CONDITIONAL_GO`. It caught the unresolved `conflict_b` price-resolution gap.
It did not catch D1, D2, D3 or D4. A correctly-executed adversarial review is
therefore not sufficient evidence that a design closes; the review read the
specification, and every finding here came from *executing* it. Composition
checks belong in CI, which is what `test_window_survival.py` now provides.
