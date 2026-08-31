# YAX Phase 2 implementation fixes

> **POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1**

## 2026-08-31: grouped-flow convergence criterion

The first attempted Stage-2A execution stopped before writing any coefficient
or results table. The official employment-exit model reached the 5,000-iteration
cap because the initial implementation required the largest update among all
nuisance fixed effects to fall below `1e-8`. The log contains only the
exception `offset grouped-binomial fit did not converge`.

The repair does not change the frozen sample, outcomes, exposure, weighting,
fixed effects, Webb control, treatment columns, estimand, bootstrap, or margin
gate. It:

1. initializes occupation fixed effects from occupation-specific event shares
   net of the risk offset; and
2. declares convergence only when the largest treatment-parameter step is
   below `1e-8` and the maximum normalized fixed-effect/treatment first-order
   condition is below `1e-9`.

This avoids conditioning convergence on drift in a nuisance-FE normalization
while continuing to require tight likelihood scores. The corrected code is
committed before the identical specifications are rerun.
