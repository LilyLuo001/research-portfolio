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
| 95% bootstrap critical half-width | 0.023430 log points |
| `MDE_(Delta,80)` | 0.032722 log points |
| relative magnitude | 3.326% |

The 95% confidence interval is frozen as
`[delta_hat - 0.023430, delta_hat + 0.023430]`; its numerical endpoints are
formed only after the protected `delta_hat` is estimated.

## Interpretation

If that interval excludes zero, the estimates are statistically distinguishable
across the frozen exposure definitions. If it includes zero, the design does not
detect a difference. Neither result licenses an economic-equivalence claim.

The literature-alignment audit found no verified published benchmark on the YAX
estimand. Numerical SESOI, equivalence interval and equivalence power are
therefore retired rather than invented. The audit and the original failed SESOI
fields remain part of the permanent pre-outcome record.
