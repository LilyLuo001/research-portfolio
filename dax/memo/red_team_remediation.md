# DAX W1 independent-review remediation log

This log records design findings from independent DeepSeek V4-Pro reviews. It
does not claim that the separate registry, empirical-power, or PI PDF-review
evidence items are complete.

> **Supersession notice, 2026-08-18:** the Round 3 `CONDITIONAL_GO` below
> reviewed the superseded design. Three fresh reruns over the current packet all
> returned `REVISE/BLOCK`. The controlling record is
> `red_team_rerun_adjudication_20260818.md`; nothing below clears Gate 1.

## Round 1

- Window midpoint ambiguity: resolved in Section 3.2 with integer CPS-month
  distances, strict-nearer assignment, exclusion of ties, and a worked example.
- Event eligibility versus treated-bin order: resolved by computing raw doses,
  applying Decision 1, constructing adjacency, and applying Decision 3 last.
- Synthetic power is not empirical evidence: remains correctly open; IPUMS CPS
  extract 6 is now completed and checksum-recorded, but actual event doses and
  empirical results are still required.
- Missing event-locator fallback and usage-share denominator: resolved in
  Sections 1.2 and 6.2.

## Round 2

- Compound-event adjacency: resolved by using one first-of-month origin,
  removing components from adjacency, computing a joint state transition, and
  adding a two-compound-event example.
- Co-primary hours power benchmark: resolved in Decision 11 with a two-hour or
  half-baseline-gap threshold, whichever is smaller; the power engine reports
  that benchmark and pass/fail status.
- Continuous-dose EIV attenuation: resolved in Decision 15 by defining the
  weighted residualized-dose slope, aggregation across draws, and interval.
- Alleged possibility of a Decision-1 passer with zero Decision-3 treated cells:
  mathematically impossible under the shared weak threshold and registered
  median rule; Section 3.2 now states this and handles unmapped events.
- Lookback, effective estimation weight, and relative-price taxonomy: resolved
  with a 15-month cap plus nine-month robustness check, a residualized
  identifying-variation formula, and explicit price-status definitions.

The outcome-data seal remains closed. No review finding authorizes opening
post-event outcomes or creating the preregistration tag.

## Round 3

The review advanced to `CONDITIONAL_GO` and marked the independent red-team
item satisfied. The remaining registry, empirical-power, and PI PDF-review
items remain open. Its mechanical follow-ups are now incorporated: unresolved
price conflicts fail closed; compound states apply timestamp-ordered component
changes; zero pre-means are excluded without regularization; missing historical
snapshots fail closed absent an approved stand-in; and calibration variances
use a 1,000-draw two-way pigeonhole bootstrap with frozen winsorization.
