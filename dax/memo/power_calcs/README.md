# DAX W1 power calculations

This directory implements the PI-approved ex ante power specification without
opening post-event outcomes. The empirical run requires two inputs:

1. `preperiod_cells.csv`: IPUMS-CPS occupation-month-education moments dated
   before 2023-03-01.
2. `event_doses.csv`: measurement-side occupation-event incremental doses.

Until those inputs exist, `make synthetic_power` runs a deterministic smoke
test. Its output is labeled `NOT_EVIDENCE` and cannot satisfy Gate 1.

## Pre-period cell schema

| Field | Meaning |
|---|---|
| `cps_occ` | Frozen CPS occupation code |
| `month` | `YYYY-MM-01`; must be before 2023-03-01 |
| `industry` | Frozen industry group |
| `education_group` | `college` or `noncollege` |
| `n_unweighted` | Person count in the cell |
| `weight_sum` | Sum of CPS person weights |
| `weight_sq_sum` | Sum of squared CPS person weights |
| `employment_rate` | Weighted employment probability |
| `hours_mean_unconditional` | Weighted weekly hours, zero when not employed |
| `hours_variance_unconditional` | Weighted variance of unconditional hours |
| `employment_hours_covariance` | Weighted covariance of employment and hours |
| `dose_sd_within_cps` | Employment-weighted within-code O*NET dose SD |
| `max_crosswalk_weight` | Largest O*NET mapping weight for the CPS code |

## Event-dose schema

| Field | Meaning |
|---|---|
| `event_id` | Registry event ID |
| `event_month` | API-effective month, `YYYY-MM-01` |
| `cps_occ` | Frozen CPS occupation code |
| `dose_increment` | Event-specific `DeltaDAX` in `[0,1]` |
| `prior_dax` | DAX level immediately before the event |

The estimator uses event-normalized CPS weights and a pooled `dose_increment ×
post` coefficient scaled to a 0.10 DAX increase. Nuisance controls are CPS
occupation fixed effects, event-by-event-time fixed effects,
industry-by-calendar-month fixed effects, and prior DAX. Inference uses a CR1
occupation-clustered sandwich estimator implemented directly with NumPy.

The engine reports the primary pooled sample and the two education subsamples,
crosswalk flags from approved Decision 12, empirical rejection rates, analytic
80% MDEs (`(1.96 + 0.84) × median cluster SE`), and the Decision-11 adequacy
test. All output records the seed and input SHA-256 hashes.
