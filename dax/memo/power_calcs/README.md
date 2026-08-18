# DAX W1 power calculations

This directory implements the PI-approved ex ante power specification without
opening post-event outcomes. The empirical run requires two inputs:

1. `preperiod_cells.csv`: IPUMS-CPS occupation-month-education moments dated
   before 2023-03-01.
2. `event_doses.csv`: measurement-side occupation-event incremental doses.

Until those inputs exist, `make synthetic_power` runs a deterministic smoke
test. Its output is labeled `NOT_EVIDENCE` and cannot satisfy Gate 1.

## Frozen IPUMS pre-period extract

`ipums_preperiod_extract_v1.json` freezes the 16 monthly CPS samples from
2021-11 through 2023-02, ages 22--25, and the variables needed for panel
occupation assignment and the two primary outcomes. `ipums_extract.py`
validates that no post-event or March ASEC sample enters before it submits,
monitors, or downloads an extract. The committed receipt contains only the
extract number, status, hashes, sizes, and errors; API keys, download URLs,
email, and raw microdata are prohibited from the repository.

IPUMS extract 6 completed on 2026-08-06 and its data/codebook checksums are in
`ipums_preperiod_extract_receipt.json`. The compressed microdata remains in
private SCC storage. Completion of this download is not the empirical-power
evidence item: W5 must first supply the frozen real occupation-event dose panel,
after which the exact pre-event moment table and registered power run can be
produced without opening post-event outcomes.

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

---

## After D1 and D3 (2026-08-18)

**`simulate_power_continuous.py` is the primary engine.** D1 replaced the
discrete stacked event study with a continuous cumulative-dose design, because
with 21 events across 41 months the treatment is effectively continuous and
every discrete option either collapsed to one estimable event or manufactured
clean windows by ignoring events that happened. There is no event selection, no
stacking, and no window rule; the regressor is the monthly DAX level itself.

**`simulate_power.py` is now secondary.** It models the demoted stacked design
and still gives every event a full [-6,+6] window, which §3.2 does not permit
(`dax/tests/test_window_survival.py` pins this). Treat its numbers as an upper
bound on the secondary design, never as a result.

**The pass bar is frozen and external.** Both engines read
`power_standard.json` and neither derives a threshold from the sample it is
judging — that was the D3 defect, where dropping one event loosened the bar by
185%. The file ships as `PLACEHOLDER_REQUIRES_REAL_CPS`, so both engines report
MDEs and return `adequately_powered: null`. Fill it once, on a host with the
real extract:

```bash
python dax/memo/power_calcs/freeze_power_standard.py \
    --extract dax/data_built/cps_extract.parquet
```

It refuses to overwrite a frozen file without `--force`, so the bar cannot
drift as the analysis develops.

**Reading the unfrozen output.** Each sample carries `break_even_baseline`:
the value the frozen pre-event baseline would have to exceed for that outcome
to pass, since `ceiling = fraction x relative_decline x baseline`. On the
synthetic fixture the pooled employment sample breaks even at a baseline
employment rate of 0.334, but the college and non-college splits need 0.488 and
0.521 — materially closer to the line. No baseline is asserted here; supplying
one from memory is exactly what meta-rule 1 forbids.

**`dose_profile`** reports the effective rank of the occupation-by-month dose
matrix and the share of variation in its leading component. Rank 1 means every
occupation moves proportionally and the design degenerates to a single
exposure-times-post contrast. On the synthetic fixture: rank 4, leading share
0.909 — timing variation contributes, but most identification still comes from
cross-occupation dose magnitude.
