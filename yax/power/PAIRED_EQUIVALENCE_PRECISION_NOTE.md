# Outcome-blind Test C paired precision

**Run date:** 2026-08-28  
**SCC job:** `7344574`  
**Artifact:** `PAIRED_EQUIVALENCE_PRECISION_v1.json`  
**Artifact SHA-256:** `4898f452f1368796d141f142ecbc88e6963b2ec273ed47446adaa0934908df5e`  
**Outcome seal:** intact; no protected post-period outcome was opened.

## Design executed

The run compares the explicitly frozen Eloundou GPT-4 beta primary measure with
the named GPT-4 alpha contrast. Both models use the same 468 common-support
occupations, the same 66 pre-period months, the same synthetic post panels and
the same 999 Rademacher/donor draws. The static synthetic post window begins
January 2023, excludes December 2022 as transition, ends July 2026, and omits
October 2025. Webb software exposure is the primary computerization control.

The direct object is:

    Delta = (Q5 - Q1 coefficient under beta)
            - (Q5 - Q1 coefficient under alpha)

## Precision result

| Quantity | Result |
|---|---:|
| Paired draws | 999 |
| Failed draws | 0 |
| `SE(Delta)` | 0.011672 log points |
| Paired beta/alpha covariance | 0.00009467 |
| Mean null Delta | 0.000701 log points |
| Empirical 95% critical half-width | 0.023430 log points |
| `MDE_Delta,80` | 0.032722 log points |
| `MDE_Delta,80`, relative magnitude | 3.326% |

This is evidence about **difference-detection precision**, not equivalence.

## Binding unresolved object

The latest-version benchmark audit found no published magnitude on YAX's exact
young-relative-to-pooled-26--65 saturated cell-stock PPML/log estimand. The BCC
19% headline and −0.179 Table 1 coefficient are inadmissible shortcuts for the
reasons documented in `../literature/BENCHMARK_ALIGNMENT_2026-08-28.md`.

Consequently the signed-off SESOI has no numerical value, and the artifact
correctly records null values for:

- the primary equivalence interval;
- equivalence-test power at `Delta = 0`;
- the 12.5% / 25% / 50% benchmark-margin grid.

The `paired_delta_power` gate therefore remains **BLOCKED**. A small
`MDE_Delta,80` does not establish equivalence, and the SESOI is not widened or
replaced to obtain a pass.

