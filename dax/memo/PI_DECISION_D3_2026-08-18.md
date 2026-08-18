# D3 resolved — the power standard becomes a frozen absolute constant

**Status:** decided under PI delegation, 2026-08-18. Requires PI counter-signature.
Recorded as a §11 deviation to the W1 draft. Supersedes the numeric part of
`[PI-DECISION 11]`.

## The defect

Decision 11 sets the employment bar at `min(6.5pp, ½ × baseline_employment_gap)`,
where `baseline_employment_gap` is the pre-event high-dose versus zero-dose
employment differential — **estimated from the analysis sample**. It therefore
depends on the dose definition, the mapping, and the event set. Rerunning the
committed simulation on three events instead of four:

| Events | baseline gap | pass bar | MDE80 | Verdict |
|---|---|---|---|---|
| 4 | 0.01667 | 0.00834 | 0.00816 | pass by 2% |
| 3 | 0.04746 | 0.02373 | 0.00974 | pass by 144% |

Dropping an event made the estimator 19% worse and the bar 185% looser. A
standard that moves with the specification it is judging cannot fail. That is
a specification-search channel written into the pre-registration, which
`CLAUDE.md` forbids by name.

The 6.5pp cap does not save it: at realistic gaps the gap term is always the
binding one, so the cap is inert.

## Decision criteria, fixed before options were scored

1. **Invariant to the specification it judges** — independent of event set,
   dose definition, mapping, and window rule.
2. **Economically interpretable** — a reader must be able to say what effect
   size the study was built to detect, and why that size matters.
3. **Computable once, from a frozen pre-period** — no quantity that moves as
   the analysis develops.
4. **Fail-closed** — until the constant is frozen with provenance, the engine
   must refuse to declare the design adequately powered.

## Decision

The standard is a **frozen absolute constant**, pre-registered as a literal
with its provenance, and never recomputed from the analysis sample.

```
benchmark_pp   = relative_decline x baseline_employment_rate_22_25
employment bar = max_mde_fraction x benchmark_pp
```

with, as pre-registered defaults:

- `relative_decline = 0.13` — the young-worker employment decline cited in the
  proposal, the effect the study exists to be able to detect.
- `baseline_employment_rate_22_25` — the employment-population ratio for ages
  22–25, computed **once** over the frozen pre-event window
  (2021-11 → 2023-02), from the frozen CPS extract, person-weighted, pooled
  across all occupations. A single scalar.
- `max_mde_fraction = 0.5` — the design must resolve an effect half the size
  of the benchmark, so the benchmark itself is detected with margin rather
  than marginally.

The hours standard is constructed the same way: `0.13 x baseline mean
unconditional weekly hours` over the same frozen window, times the same
fraction.

**Why this is invariant.** The old bar used the high-dose *versus* zero-dose
differential, which requires a dose definition and an event set to compute.
The new one uses the pooled employment *rate*, which requires neither. It is
one number from one fixed window, and nothing downstream can move it.

## What is explicitly forbidden

- Recomputing the constant after the event set, mapping, dose definition,
  window rule, or sample changes. It is frozen at first computation.
- Recomputing it on the post-event window under any circumstances.
- Reporting `adequately_powered` while the constant is unfrozen.
- Treating a failure as licence to search. Decision 11's existing language
  stands: failure triggers the proposal's informative-power limitation and PI
  reconsideration, not a different specification.

## Implementation

`dax/memo/power_calcs/power_standard.json` holds the constant, its provenance,
and a `status` field. It ships as `PLACEHOLDER_REQUIRES_REAL_CPS` because the
frozen CPS extract is not present in this environment — `dax/data_raw/` is
empty and IPUMS extract 6 lives on the box.

`freeze_power_standard.py` computes the constant from the real extract and
stamps the file with the source path, its SHA256, the row count, the frozen
window, and the timestamp. It refuses to overwrite an already-frozen file
without `--force`, so the constant cannot drift silently.

Until then the power engine reports MDEs and returns `adequately_powered: null`
with `standard_status: PLACEHOLDER_REQUIRES_REAL_CPS`. It does not guess, and
it does not pass.

## Interaction with D1

D1 replaced the discrete stack with a continuous cumulative-dose primary, so
the MDE this standard judges is now "effect per 0.10 DAX increment" estimated
on the monthly panel. The standard is expressed in the same units and is
unaffected by that change — which is the point of choosing a specification-
invariant benchmark.

## Not resolved here

D4 (entrant exclusion) and F2 (registry verification statuses) remain open.
