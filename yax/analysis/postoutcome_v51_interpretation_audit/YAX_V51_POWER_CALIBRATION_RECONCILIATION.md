# YAX V5.1 prospective-power versus realized-precision reconciliation

## Decisions

- **Primary beta×Webb headline: HEADLINE-P2.** The outcome-blind simulation is reproducible design-history provenance, but its synthetic precision was materially optimistic.
- **Paired beta-minus-alpha contrast: PAIRED-P2.** The paired simulation preserved covariance and is reproducible, but its synthetic precision was materially optimistic.

Neither calculation is used as substantive evidence about realized precision. No ex-post MDE replaces either prospective quantity.

## A. Primary beta×Webb headline

The authoritative pre-outcome design is `scenarios_v3/beta_webb_primary.json`, aggregated in `JOINT_POWER_AGGREGATE_v3.json` and described in `POWER_NOTE_v3.md`.

| Design feature | Frozen value |
|---|---|
| Estimand | Eloundou beta Q5-versus-Q1 log coefficient, with Q2–Q4 separately absorbed |
| Comparison technology | Webb software exposure, standardized on the scenario support |
| Assumed AI-effect grid | 0, -0.005, -0.015, -0.03, -0.05, -0.08, -0.12, -0.18 log points |
| Assumed computerization effect | `log(0.95)=-0.0512933` per weighted SD; a design stress parameter |
| Synthetic construction | Fixed pre-period grouped-logit fit; cyclic pre-period month donors; one Rademacher sign per occupation applied to its entire residual time path; injected AI and Webb shifts in synthetic post months |
| Occupations | 468 from 490 balanced pre-period clusters |
| Prospective residual-treatment effective occupations | 53.263; top-five share 22.15% |
| Pre-period | 66 months, January 2017–November 2022 |
| Planned synthetic post | 42 months, January 2023–July 2026, excluding October 2025; December 2022 excluded |
| Residual variance | The observed pre-period fitted residual paths, signed by occupation; no realized post-period residual path |
| Cluster dependence | A single sign multiplies an occupation's full residual path; inference clustered by occupation |
| Calibration | 999 null draws; independent null rejection rate 0.038; two-sided critical value 2.2120 |
| MDE80 | 4.061% relative decline (Monte Carlo interval 3.979%–4.136%); approximately 0.04146 in absolute log magnitude |
| Synthetic SE recorded at the null | Mean occupation-cluster SE 0.0121696; null RMSE 0.0124937 |

The realized primary result is -0.131074 with occupation-cluster SE 0.0444098. The commensurable realized-SE to prospective-null-mean-SE ratio is therefore **3.649**. The realized estimator-information effective count is 43.300 occupations and the top-five information share is 24.57%; these differ from, but do not by themselves explain, the prospective residual-treatment figures.

The simulation used the observed exposure distribution and pre-period occupation/month structure. Its own pre-outcome limitation record says it could not reproduce an unobserved post-2022 aggregate shock, structural composition change, exposure measurement error, or conditional-mean misspecification. Panel length and nominal support were implemented as planned. The audit cannot isolate which unmodeled feature produced the precision gap. The supported conclusion is: **the prospective simulation materially overstated realized precision; the available audit does not isolate a unique cause.**

## B. Paired beta-minus-alpha comparison

The authoritative artifacts are `PAIRED_EQUIVALENCE_PRECISION_v1.json`, `PAIRED_DIFFERENCE_PRECISION_v2.json`, `paired_equivalence_power.py`, and `YAX_V51_PAIRED_MDE_RECONCILIATION.md`.

| Design feature | Frozen value |
|---|---|
| Estimand | Beta Q5–Q1 minus alpha Q5–Q1, each conditional on Webb |
| Synthetic construction | Same 66 pre-period months, cyclic donors, and occupation-level Rademacher sign applied to both exposure definitions |
| Occupations | 468 from 490 balanced pre-period clusters |
| Planned synthetic post | 42 months under the same January 2023–July 2026 calendar |
| Common draws | 999 successful of 999 attempts, seed 20260828 |
| Preserved prospective covariance | 0.00009467 between beta and alpha |
| Prospective paired SE | 0.0116715 log points |
| Prospective centered 95% half-width | 0.0234301 log points |
| Prospective MDE80 | 0.0327216 log points, or 3.326% under the exponential magnitude translation |
| Realized paired estimate | -0.032396 log points |
| Realized paired SE | 0.036968 log points |
| Realized interval | [-0.102345, 0.037553] |

The realized-to-prospective paired-SE ratio is **3.167**. Common synthetic draws correctly preserved covariance, but the donor-plus-sign DGP could not know the realized post-period residual path, nonlinear fit, or realized cross-architecture sampling covariance. Again, the artifacts do not identify a unique cause.

## Manuscript rule

Both prospective calculations remain appendix-only design history. The manuscript must state in the main text that the primary prospective simulation, like the paired simulation, overstated realized precision. It must not present either prospective MDE as a guarantee of realized power, and it must not relabel an ex-post calculation as design-stage evidence.

No new labor-outcome model was estimated for this audit.
