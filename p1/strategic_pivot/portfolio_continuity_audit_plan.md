# Portfolio continuity audit plan

The continuity audit describes whether realized holdings look like a wrapper
transformation, a strategy transformation, or an inseparable bundle. Under the
2026-09-06 decision it is a post-treatment diagnostic, not a headline-sample
eligibility gate. Eligibility must be frozen using only information available by
the assignment date: legal identity, mandate, benchmark, manager, asset class,
and publicly announced concurrent changes.

## Event-level inputs

Use the last two valid predecessor holdings reports and first two valid successor/shared-portfolio reports. Align securities through audited CUSIP/CIK/PERMNO mappings and corporate actions. Preserve cash, derivatives, short positions, and unmatched value as explicit categories rather than deleting them.

For ETF share-class activations, the same SEC series/CRSP portfolio number supplies
only a candidate relationship. Historical pro-rata status still requires
prospectus/class-structure evidence and verified effective and first-trade clocks;
realized holdings stability is then quantified as a diagnostic. For full
conversions, predecessor and successor series differ, so realized continuity is
also a diagnostic rather than a retrospective eligibility gate.

## Frozen diagnostics

| Diagnostic | Definition | Clean threshold | Review band | Fail flag |
|---|---|---:|---:|---:|
| Value-weight overlap | Sum of minimum pre/post security weights | ≥ 0.90 | 0.80–0.90 | < 0.80 |
| Weight correlation | Pearson correlation across union of holdings | ≥ 0.95 | 0.85–0.95 | < 0.85 |
| Rank correlation | Spearman correlation across common holdings | ≥ 0.90 | 0.75–0.90 | < 0.75 |
| Active-weight change | Half sum absolute weight changes | ≤ 0.10 | 0.10–0.20 | > 0.20 |
| Objective continuity | Same audited objective/benchmark text | exact or immaterial edit | documented clarification | material mandate change |
| Name/adviser/team | Same economic adviser and core team | unchanged | disclosed partial change | simultaneous full change |
| Asset-class continuity | Equity/fixed-income/style allocation | within 10 percentage points | 10–20 pp | > 20 pp |
| Unmatched value | Unmapped value share in either report | ≤ 5% | 5–10% | > 10% |

These are pre-specified descriptive diagnostic cutoffs, not eligibility
thresholds. They may not be tuned after viewing treatment-effect estimates.

## Realized post-treatment diagnostic classification

- `A_REALIZED_WRAPPER_CONTINUITY`: all core diagnostics clean and no mandate/team fail.
- `B_REALIZED_PROBABLE_CONTINUITY`: no fail flag and at most two review-band measures.
- `C_REALIZED_BUNDLED_TRANSFORMATION`: any mandate/team/asset-class fail or two quantitative fail flags.
- `D_REALIZED_UNRESOLVED_DATA`: missing/unmatched coverage prevents classification.

Headline eligibility may not use these realized categories. Report them for all
pre-treatment-eligible events. Any split by realized category is descriptive
post-treatment heterogeneity and must not be presented as causal sample
selection. Only material changes documented by the assignment date can define
an ex-ante bundled-transformation exclusion.

## Timing controls and report

Compute predecessor-to-predecessor turnover as the counterfactual baseline. Compare the event transition with that normal turnover so scheduled rebalancing is not mistaken for discontinuity. Flag quarter-end index reconstitutions, adviser changes, benchmark changes, mergers, tax-liquidation programs, and large net flows.

The final audit table must contain event ID, every diagnostic, raw source accession/report date, classification, reviewer note, and a deterministic reason code. A second reviewer resolves only source interpretation; they may not view outcome estimates.
