# Outcome-blind Test C paired-difference precision

**Amendment date:** 2026-08-29

**Derived receipt:** `PAIRED_DIFFERENCE_PRECISION_v2.json`

**Original computation:** SCC job `7344574`, 999 common draws, zero failures

**Outcome seal:** intact; no protected post-period outcome was opened.

The original blocked artifact remains unchanged at
`PAIRED_EQUIVALENCE_PRECISION_v1.json`. Its stored paired distribution is
authenticated by SHA-256 from the derived receipt.

| quantity | outcome-blind result |
|---|---:|
| `SE(Delta)` | 0.011672 log points |
| paired β/α covariance | 0.00009467 |
| outcome-blind 95% null critical half-width for power | 0.023430 log points |
| `MDE_(Delta,80)` | 0.032722 log points |
| relative magnitude | 3.326% |

The eventual 95% confidence interval remains the pre-specified percentile-t
paired occupation-cluster bootstrap interval with at least 999 common draws.
Its numerical endpoints are formed only after protected estimates are opened.
The 0.023430 value above is a null critical half-width used for the outcome-blind
power diagnostic; it is not relabelled as the eventual outcome CI.

## Interpretation

If that interval excludes zero, the estimates are statistically distinguishable
across the frozen exposure definitions. If it includes zero, the design does not
detect a difference. Neither result licenses an economic-equivalence claim.

The literature-alignment audit found no verified published benchmark on the YAX
estimand. Numerical SESOI, equivalence interval and equivalence power are
therefore retired rather than invented. The audit and the original failed SESOI
fields remain part of the permanent pre-outcome record.
