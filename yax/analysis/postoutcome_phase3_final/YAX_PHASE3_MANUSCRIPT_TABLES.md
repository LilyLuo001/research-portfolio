# YAX Phase 3 manuscript-ready tables

**POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.**

## Table P3.1. Hard reallocation benchmark

| Sample | Realized conflict | Current marginal mean | Hard mean | Hard 95% reference interval | Realized - hard | Tail area | Classification |
|---|---:|---:|---:|---:|---:|---:|---|
| Primary | 53.28% | 45.27% | 52.32% | [52.21%, 52.43%] | 0.96 pp | .001 | HB-C |
| Persistent | 54.46% | -- | 53.58% | [53.49%, 53.66%] | 0.88 pp | .001 | HB-C |

Notes: The hard benchmark preserves age group, calendar month, origin broad occupational family, destination broad occupational family, and observed weighted origin and destination marginals within those strata. It uses 200,000 pseudo-units and 999 fixed-seed draws. The tail area describes a constrained-rematching reference distribution; it is not a conventional sampling p-value or causal evidence. The primary benchmark represents 98.31% of official switch weight; the persistent benchmark represents 99.92%.

## Table P3.2. Conflict by absolute shared-component movement

| Weighted quintile of abs(delta F) | Primary conflict | Persistent conflict |
|---:|---:|---:|
| 1 (smallest) | 94.59% | 94.94% |
| 2 | 65.96% | 66.88% |
| 3 | 52.67% | 53.51% |
| 4 | 34.06% | 34.07% |
| 5 (largest) | 19.06% | 19.01% |

Notes: F is the frozen shared family component. The employment-weighted absolute-movement cuts are 0.17855, 0.39019, 0.71236, and 1.21427. Directional conflict means that at least two of the six architectures assign opposite signs to the same realized switch. The descriptive classification is SC-R1.

## Table P3.3. Shared-family-component employment-stock model

| Treatment | Coefficient | Cluster SE | Wild-score p | Wild-score 95% CI | Percent | Occupations | Employment support |
|---|---:|---:|---:|---:|---:|---:|---:|
| F Q5 versus Q1 | -0.12854 | 0.04698 | .005 | [-0.21849, -0.03858] | -12.06% | 444 | 83.14% |

Notes: This is the only new labor-outcome regression authorized in Phase 3. The treatment is employment-weighted quintiles of the frozen shared family component on literal six-measure common support. The PPML model, fixed effects, Webb comparison-technology interaction, occupation clustering, and one-step wild-score method match the existing headline design. The result is SC-A and remains observational.

## Table P3.4. Simultaneous one-sided inference across six architecture-specific coefficients

| Architecture | Coefficient | Cluster SE | Simultaneous 95% upper bound | Upper bound below zero |
|---|---:|---:|---:|---|
| AIOE administrative equal | -0.07386 | 0.04090 | 0.01858 | No |
| AIOE ability direct | -0.10285 | 0.03811 | -0.01671 | Yes |
| AIOE source weighted | -0.10210 | 0.04223 | -0.00665 | Yes |
| Eloundou alpha | -0.10132 | 0.04171 | -0.00703 | Yes |
| Eloundou beta | -0.12896 | 0.04517 | -0.02685 | Yes |
| Eloundou broad | -0.14652 | 0.04522 | -0.04431 | Yes |

Notes: The null is that at least one architecture-specific coefficient is nonnegative; the alternative is that all six are negative. Common occupation-cluster multipliers preserve cross-architecture covariance on the same 444-occupation support (999 draws; seed 2026090304). Because one simultaneous upper bound exceeds zero, the frozen familywise statement is not supported. The six parameters are not assumed to be estimates of one common causal parameter.
