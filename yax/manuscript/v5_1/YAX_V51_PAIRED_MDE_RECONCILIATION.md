# YAX V5.1 paired-MDE reconciliation

## Decision: MDE-R2

The prospective calculation is reproducible, but it is a design-specific synthetic precision exercise whose standard error is materially smaller than realized uncertainty. It belongs in the appendix and must not be used to describe the realized beta–alpha comparison as highly powered.

## Prospective procedure

The sealed calculation used only January 2017–November 2022 occupation-by-age employment stocks; protected post-period outcomes were not opened. It retained 468 common-support occupations from 490 balanced pre-period clusters, 66 observed pre-period months, and constructed 42 synthetic post months matching the planned January 2023–July 2026 horizon with October 2025 omitted. December 2022 was excluded.

For each of 999 successful draws (seed `20260828`), the program cyclically selected pre-period donor months, applied one Rademacher sign to each occupation's entire residual time path, imposed only the fixed Webb association `log(0.95)` in the synthetic post period, and estimated the frozen beta and alpha Q5-versus-Q1 models on the same synthetic outcome. Applying identical donors and occupation signs to both definitions preserved covariance. The centered paired distribution produced:

| Prospective quantity | Value |
|---|---:|
| `SE(Delta)` | 0.0116715 log points |
| beta/alpha covariance | 0.00009467 |
| centered 95% critical half-width | 0.0234301 log points |
| `MDE_Delta,80` | 0.0327216 log points |
| exponential magnitude translation | 3.326% |

The MDE is obtained by shifting the centered synthetic paired distribution until 80% of draws exceed the outcome-blind two-sided critical half-width. The planned confidence interval was a percentile-t occupation-cluster interval with common draws. No numerical SESOI or equivalence test was supplied.

## Realized comparison

The realized beta-minus-alpha difference is -0.032396 log points, with paired SE 0.036968 and 95% interval [-0.102345, 0.037553] (`p=.403`). The realized SE is 3.17 times the prospective synthetic SE. The prospective engine preserved pair covariance but could not know the post-period residual path, realized nonlinear fit, or realized cross-architecture sampling variability. Its donor-plus-sign synthetic DGP is therefore informative about that frozen scenario, not a guarantee of future precision.

No arithmetic or scale failure was found: 0.0327 is in log points, not additive percentage points, and corresponds to a 3.326% exponential magnitude. The discrepancy is an assumption-to-realization gap. V5.1 therefore reports the realized paired interval in the main results and relegates the prospective MDE to appendix provenance with the MDE-R2 classification. It does not recompute an ex-post replacement and does not infer economic equivalence.

Authoritative artifacts: `PAIRED_EQUIVALENCE_PRECISION_v1.json`, `PAIRED_DIFFERENCE_PRECISION_v2.json`, `paired_equivalence_power.py`, and `PAIRED_MDE_SCALE_NOTE_V3.md`.
