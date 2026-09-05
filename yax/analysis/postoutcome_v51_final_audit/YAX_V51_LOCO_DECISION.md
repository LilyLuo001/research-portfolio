# YAX V5.1 fixed-treatment LOCO decision

## Scope and implementation

This post-outcome influence audit refit exactly two previously reported models. For each refit, one Census-2018 occupation was deleted while every full-sample treatment object remained fixed: exposure scores, quintile cutoffs and membership, Webb standardization, F and G values and scaling, age definitions, post window, and fixed-effect specification. Deletions followed lexicographically sorted Census-2018 occupation codes.

No new labor-outcome specification was estimated. LOCO refits only delete one occupation while preserving the exact previously defined treatment and model. No leave-one-measure-out labor-outcome model was executed. No new bootstrap multipliers were generated.

## Primary beta-by-Webb Q5-versus-Q1 coefficient

**Decision: LOCO-B2 — MODERATE INFLUENCE.** Some occupations move the magnitude materially, but no single deletion overturns or radically shrinks the central negative result.

| Diagnostic | Result |
|---|---:|
| Frozen full estimate | -0.131074 |
| Occupations deleted one at a time | 468 |
| Minimum leave-one-out estimate | -0.142384 |
| Maximum leave-one-out estimate | -0.110553 |
| Maximum absolute movement | 0.020521 |
| Maximum relative movement | 15.66% |
| Sign changes / estimates reaching or crossing zero | 0 / 0 |

The largest movement follows deletion of **Fast food and counter workers** (Census 4055): the estimate changes from -0.131074 to -0.110553, a +0.020521 movement. Customer service representatives produce the second-largest change (+0.017962). The full top ten are:

| Rank | Census code | Deleted occupation | Leave-one-out estimate | Signed movement | Absolute movement |
|---:|---:|---|---:|---:|---:|
| 1 | 4055 | Fast food and counter workers | -0.110553 | +0.020521 | 0.020521 |
| 2 | 5240 | Customer service representatives | -0.113112 | +0.017962 | 0.017962 |
| 3 | 3601 | Home health aides | -0.142384 | -0.011310 | 0.011310 |
| 4 | 1108 | Computer occupations, all other | -0.120798 | +0.010276 | 0.010276 |
| 5 | 5860 | Office clerks, general | -0.141094 | -0.010021 | 0.010021 |
| 6 | 5740 | Secretaries and administrative assistants, except legal, medical, and executive | -0.140894 | -0.009820 | 0.009820 |
| 7 | 4030 | Food preparation workers | -0.139812 | -0.008738 | 0.008738 |
| 8 | 9620 | Laborers and freight, stock, and material movers, hand | -0.139464 | -0.008390 | 0.008390 |
| 9 | 4850 | Sales representatives, wholesale and manufacturing | -0.139244 | -0.008170 | 0.008170 |
| 10 | 1021 | Software developers | -0.138787 | -0.007713 | 0.007713 |

Employment-stock-weighted signed-movement quantiles are:

| Quantile | Movement |
|---:|---:|
| 0% | -0.011310 |
| 1% | -0.010021 |
| 5% | -0.008170 |
| 25% | -0.000224 |
| 50% | -0.000012 |
| 75% | +0.000304 |
| 95% | +0.003773 |
| 99% | +0.017962 |
| 100% | +0.020521 |

The headline remains negative throughout the full deletion set. The magnitude is not literally invariant, so B1 would overstate stability; the absence of any sign reversal and the bounded range rule out B3.

## Exploratory between-family G coefficient

**Decision: LOCO-G1 — STABLE.** G remains positive and similar under all 444 deletions; no isolated deletion approaches or crosses zero.

| Diagnostic | Result |
|---|---:|
| Frozen full estimate | +0.030894 |
| Occupations deleted one at a time | 444 |
| Minimum leave-one-out estimate | +0.025128 |
| Maximum leave-one-out estimate | +0.035993 |
| Maximum absolute movement | 0.005766 |
| Maximum relative movement | 18.66% |
| Estimates at or below zero | 0 (0.00%) |

The largest movement follows deletion of **Driver/sales workers and truck drivers** (Census 9130): G changes from +0.030894 to +0.025128, a -0.005766 movement. The full top ten are:

| Rank | Census code | Deleted occupation | Leave-one-out G | Signed movement | Absolute movement |
|---:|---:|---|---:|---:|---:|
| 1 | 9130 | Driver/sales workers and truck drivers | +0.025128 | -0.005766 | 0.005766 |
| 2 | 5120 | Bookkeeping, accounting, and auditing clerks | +0.035993 | +0.005100 | 0.005100 |
| 3 | 1010 | Computer programmers | +0.035410 | +0.004516 | 0.004516 |
| 4 | 5510 | Couriers and messengers | +0.026656 | -0.004237 | 0.004237 |
| 5 | 4055 | Fast food and counter workers | +0.027430 | -0.003463 | 0.003463 |
| 6 | 5840 | Insurance claims and policy processing clerks | +0.027672 | -0.003221 | 0.003221 |
| 7 | 5140 | Payroll and timekeeping clerks | +0.033762 | +0.002869 | 0.002869 |
| 8 | 3601 | Home health aides | +0.033511 | +0.002618 | 0.002618 |
| 9 | 0052 | Sales managers | +0.033499 | +0.002605 | 0.002605 |
| 10 | 1108 | Computer occupations, all other | +0.028384 | -0.002509 | 0.002509 |

Employment-stock-weighted signed-movement quantiles are:

| Quantile | Movement |
|---:|---:|
| 0% | -0.005766 |
| 1% | -0.005766 |
| 5% | -0.001693 |
| 25% | -0.000475 |
| 50% | -0.000024 |
| 75% | +0.000177 |
| 95% | +0.002155 |
| 99% | +0.004516 |
| 100% | +0.005100 |

LOCO-G1 concerns occupation influence only. It does not supersede `G-PARTIAL`: the separate outcome-free construction audit shows that removing alpha materially changes G's geometry. Together, the findings permit a bounded description of the frozen exploratory construction, not a general family ranking or causal mechanism.

## Authoritative machine-readable outputs

- `YAX_V51_LOCO_PRIMARY.csv`: all 468 primary deletions.
- `YAX_V51_LOCO_G.csv`: all 444 G deletions.
- `YAX_V51_LOCO_RESULTS.json`: frozen estimates, summaries, input and output hashes, and execution-boundary attestations.
