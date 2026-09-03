# Portfolio continuity audit plan

The continuity audit determines whether an event is a wrapper transformation, a strategy transformation, or an inseparable bundle. It must be completed before causal outcome estimation.

## Event-level inputs

Use the last two valid predecessor holdings reports and first two valid successor/shared-portfolio reports. Align securities through audited CUSIP/CIK/PERMNO mappings and corporate actions. Preserve cash, derivatives, short positions, and unmatched value as explicit categories rather than deleting them.

For ETF share-class activations, portfolio identity is mechanically supported by the same SEC series/CRSP portfolio number, but actual holdings stability is still quantified. For full conversions, predecessor and successor series differ and require empirical continuity evidence.

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

Thresholds are outcome-blind. They classify events; they are not tuned to strengthen estimates.

## Classification

- `A_WRAPPER_CONTINUITY`: all core diagnostics clean and no mandate/team fail.
- `B_PROBABLE_CONTINUITY`: no fail flag and at most two review-band measures.
- `C_BUNDLED_TRANSFORMATION`: any mandate/team/asset-class fail or two quantitative fail flags.
- `D_UNRESOLVED_DATA`: missing/unmatched coverage prevents classification.

Headline analyses use A and B with A-only as the primary robustness. C estimates a different bundled intervention and is reported separately; D never enters a headline sample.

## Timing controls and report

Compute predecessor-to-predecessor turnover as the counterfactual baseline. Compare the event transition with that normal turnover so scheduled rebalancing is not mistaken for discontinuity. Flag quarter-end index reconstitutions, adviser changes, benchmark changes, mergers, tax-liquidation programs, and large net flows.

The final audit table must contain event ID, every diagnostic, raw source accession/report date, classification, reviewer note, and a deterministic reason code. A second reviewer resolves only source interpretation; they may not view outcome estimates.
