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

- `relative_decline = 0.13` — the young-worker relative decline in
  **employment**, the effect the study exists to be able to detect. See the M2
  adjudication below for why this is employment and not payroll.
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


---

# M2 adjudicated — 2026-08-18

**Question.** Does the `0.13` refer to a decline in employment or in payroll?
The two are different objects (payroll = employment x hours x wage), and a
frozen constant built on the wrong one is unrecoverable.

**Answer: a relative decline in EMPLOYMENT (headcount).** "Payroll" names the
*data source*, not the outcome variable.

**Evidence, channel 1 — the project's own proposal, in-tree.**

> "U.S. payroll data, by contrast, show a 13 percent relative employment
> decline among workers ages 22-25 in the most AI-exposed occupations
> (Brynjolfsson, Chandar, and Chen 2025)."
> — `docs/DAX_ERE_Proposal_v3.md:12`

Full reference, `docs/DAX_ERE_Proposal_v3.md:100`:

> Brynjolfsson, E., B. Chandar, and R. Chen. 2025. "Canaries in the Coal Mine?
> Six Facts about the Recent Employment Effects of Artificial Intelligence."
> Working paper.

**Evidence, channel 2 — web search** (citations are a dual-channel task under
meta-rule 2). Two independent queries returned the same characterisation: a 13
percent *relative decline in employment* for ages 22-25 in the most AI-exposed
occupations, estimated on ADP administrative payroll data, after controlling
for firm-level shocks.

**Consequence.** The D3 formula `0.5 x 0.13 x baseline_employment_rate` was
already correct; `0.13` is a *relative* decline, so the absolute
percentage-point benchmark is `0.13 x baseline rate`. The defect was purely
terminological — the execution plan calls it "the 13% payroll estimate"
(`docs/DAX_Execution_Plan_with_AI_Agents.md:95, :139`), which the memo
inherited. Memo section 7.4 now states the distinction explicitly and carries
the citation, and a test prevents the wording from drifting back.

## New blocker surfaced while resolving M2: **M2b — which version?**

The same paper has been revised, and the headline figure moved with it:

| Version | Reported relative employment decline |
|---|---|
| The version the proposal cites (2025) | **0.13** |
| A later revision | reportedly 0.16 |
| August 2026, ADP data through June 2026 | reportedly 0.19 |

**Evidence quality, stated honestly.** The 0.16 and 0.19 figures come from
web-search result summaries only. `digitaleconomy.stanford.edu`,
`thedocs.worldbank.org` and `bharatchandar.substack.com` are all egress-blocked
from this environment, so **no version of the paper was actually read**. Under
meta-rule 1 those two figures are not yet sourced to a locator and must not be
frozen on this evidence.

**Why this is a PI decision and not an agent's.** Two defensible options:

- **Freeze 0.13** — benchmark against the figure the registered proposal cites.
  Consistent with the pre-registration; arguably the point of a registered
  benchmark is that it does not move.
- **Freeze the current figure** — benchmark against the same paper's best
  current estimate.

The second loosens the pass bar by roughly 46% (0.19 vs 0.13) and therefore
makes the design easier to pass. Choosing it *after* seeing that the design's
margin is tight would be specification search, which is exactly the failure D3
exists to prevent. An agent must not pick the option that benefits the
analysis.

`freeze_power_standard.py` now refuses to run while
`benchmark.version_status != "RESOLVED"`, so this cannot be resolved by
forgetting about it.

**What would settle it.** The exact excerpt naming the headline figure from:

> Brynjolfsson, Erik, Bharat Chandar, and Ruyu Chen.
> "Canaries in the Coal Mine? Six Facts about the Recent Employment Effects of
> Artificial Intelligence." Stanford Digital Economy Lab — **the August 2026
> version** (`Canaries_August2026.pdf`), and ideally the November 2025 version
> for the intermediate figure.

With that excerpt the value gets a locator and `version_status` can be set to
`RESOLVED` with the PI's chosen figure.
