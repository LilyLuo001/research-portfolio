# INF-03 and INF-05 findings

Status: **complete post-outcome exploratory sensitivity analyses; not part of
confirmatory YAX v1.1**

The full SCC run used 199 household-multiplier draws and 199 simulations per
effect. It completed with no INF-03 failures. INF-05 retained 20 failed model
refits (ten paired replicate failures) under the fixed 100-iteration ceiling.
All aggregate-output self-checks pass. These results do not alter the frozen
confirmatory analysis.

## INF-03: CPSID-linked household sensitivity

The extract permits a longitudinal-household multiplier sensitivity, but it
does not contain public CPS strata, PSU, or replicate-weight variables. The
exercise therefore remains conditional on released `WTFINL` and is **not
design-based CPS inference**. It captures co-resident and repeated-month
dependence within 640,401 analysis-contributing positive `CPSID` units; 567,373
of those units appear in more than one analysis month. It does not capture
unavailable PSU dependence, multistage selection, calibration/nonresponse
weight uncertainty, or linkage error.

All 199 common-draw full refits succeeded for both classification rules:

| classification rule | object | estimate | sampling-oriented SE | basic 95% interval | MDE80 from this SE |
|---|---|---:|---:|---:|---:|
| fixed corrected labels | baseline | -0.132109 | 0.026246 | [-0.182209, -0.080044] | 0.073531 |
| fixed corrected labels | SOC2-post | -0.021599 | 0.045279 | [-0.108852, 0.054810] | 0.126853 |
| fixed corrected labels | SOC2 minus baseline | 0.110510 | 0.035987 | [0.036647, 0.175669] | 0.100819 |
| rebuilt preperiod labels | baseline | -0.132109 | 0.026137 | [-0.179376, -0.080047] | 0.073226 |
| rebuilt preperiod labels | SOC2-post | -0.021599 | 0.045368 | [-0.111871, 0.055973] | 0.127103 |
| rebuilt preperiod labels | SOC2 minus baseline | 0.110510 | 0.036092 | [0.036986, 0.172209] | 0.101115 |

The common household draws preserve the covariance of the paired SOC2-minus-
baseline movement. Under this sampling perturbation, the paired interval does
not include zero for either classification rule. Rebuilding preperiod
employment weights, quintile memberships, and Webb normalization changes
between zero and seven occupations per draw (median two; 95th percentile four)
and leaves the reported sampling dispersion nearly unchanged.

These sampling-oriented SEs are smaller than the corresponding analytic
occupation-cluster SEs (0.045174 for the baseline and 0.071599 for SOC2-post),
but they target different perturbations. They are reported separately and are
not mechanically added to occupation-cluster variance.

## INF-05: finite-sample full-refit stress test

The stress test preserves the actual 468-occupation by 113-month support and
weighted totals. It combines cell-level binomial sampling at rounded Kish
effective counts with signed, complete-path SOC2-family-by-month residual
shocks. It evaluates the normal occupation-cluster interval after a full
grouped-binomial refit. This is an outcome-calibrated finite-sample stress
scenario, not a structural data-generating process or a reconstruction of the
full CPS sampling design.

| true effect | model | successful refits | bias | empirical SD | mean reported SE | 95% coverage (MC SE) | reject zero (MC SE) |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0 | baseline | 195/199 | 0.000356 | 0.031448 | 0.017665 | 0.733 (0.032) | 0.267 (0.032) |
| 0 | SOC2-post | 195/199 | -0.001822 | 0.025531 | 0.021578 | 0.887 (0.023) | 0.113 (0.023) |
| -0.05 | baseline | 196/199 | -0.000674 | 0.032811 | 0.017384 | 0.704 (0.033) | 0.668 (0.034) |
| -0.05 | SOC2-post | 196/199 | -0.001025 | 0.025077 | 0.021675 | 0.923 (0.019) | 0.633 (0.034) |
| -0.132109 | baseline | 196/199 | 0.001657 | 0.031202 | 0.017746 | 0.679 (0.033) | 1.000 (0.000) |
| -0.132109 | SOC2-post | 196/199 | 0.000096 | 0.024316 | 0.021626 | 0.913 (0.020) | 1.000 (0.000) |

The simulated point estimates are approximately unbiased, but the conventional
occupation-cluster normal interval is anti-conservative in this calibrated
stress scenario. Under the null, rejection is 26.7% for the baseline model and
11.3% for SOC2-post rather than 5%. The baseline interval covers only 67.9% to
73.3% across the three effect values; SOC2-post coverage is 88.7% to 92.3%.
The SOC2-post model is materially better calibrated here, but the null
over-rejection remains above nominal. With 195 or 196 successful draws, the
reported Monte Carlo standard errors are about 1.9 to 3.4 percentage points,
so the main size distortion is larger than simulation noise.

The stress is empirically relevant to the observed support. Of 51,891 positive
occupation-month cells, 12,890 have zero young stock and 75 have zero older
stock. Kish effective counts have median 23.85; 6,748 cells are below five,
14,585 below ten, and 23,671 below twenty. Influence is also concentrated: the
effective occupation-influence count is 14.54 for the baseline and 11.60 for
SOC2-post; the top five occupations account for 47.1% and 54.0% of squared
influence, respectively.

Nonconvergence was not discarded silently. Four null replicates and three
replicates under each nonzero effect failed, with both models failing in the
same ten replicates. Successful-refit rates are 98.0% under the null and 98.5%
under each nonzero effect. Inference is therefore conditional on successful
refits, with the failure record retained in `MODEL_FAILURES.json`.

## Bottom line

INF-03 shows that the baseline result and the paired movement under SOC2
conditioning persist under the declared resampling of linked households with
the available final weights, while also establishing that the public extract
cannot support a design-based CPS interval. INF-05 supplies an adverse warning:
under a sparse-cell, broad-family stress calibrated to this panel, the ordinary
occupation-cluster normal interval can substantially over-reject, especially
for the pooled baseline model. The simulation diagnoses finite-sample behavior
under its declared DGP; it does not identify the true repeated-sampling law of
the CPS estimator.

Machine-readable outputs are in `results/inf03_inf05_full/`. SCC batch job
`7468793` exited successfully after 2,360 seconds with maximum memory of 2.363
GB. No protected identifier, individual record, or cell-level private stock is
serialized in the release artifacts.
