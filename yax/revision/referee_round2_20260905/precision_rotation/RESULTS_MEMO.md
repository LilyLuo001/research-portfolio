# Precision, timing, and CPS-rotation audit

Status: **post-outcome exploratory; not part of confirmatory YAX v1.1**  
Execution date: 2026-09-05  
Audit: `results/AUDIT_REPORT.json` reports PASS on all 13 programmed checks.

## Executive conclusions

1. The sole canonical interval for the frozen primary estimate is now based on 9,999 common wild-score draws: **-0.1311 log points, occupation-clustered SE 0.0444, 95% CI [-0.2171, -0.0451], p = 0.0030**. Its normal-theory 80% MDE is **0.1244 log points** (about 13.25% on the relative-stock-ratio scale). The realized design is therefore precise enough to detect effects about as large as the headline estimate, but not modest differences between exposure architectures.
2. Every paired beta-versus-alternative architecture interval includes zero. Paired 80% MDEs range from 0.0609 to 0.1689 log points. These results support only **"the design does not detect a difference"**, not economic equivalence or architecture invariance.
3. The four earlier intervals attached to -0.1311 are reconciled. Three came from different finite sets of 999 bootstrap multipliers on the same estimator and sample; the minimum-count interval used a different 463-occupation sample. None should remain alongside the primary estimate. The new 9,999-draw interval is the only canonical primary interval.
4. Sparse occupation-month-age cells are common for ages 22--25: p10/median/p90 respondent equivalents are 0/2/16, 26.3% are zero, and 69.9% are below five. The grouped-binomial likelihood validly retains one-sided boundary cells and omits only cells with zero total respondents. Conditioning on at least five respondents changes the sample and estimand; it attenuates the coefficient to about -0.109 but does not eliminate it.
5. Quarterly aggregation changes essentially nothing: -0.1310 under the frozen calendar and -0.1345 under the repaired 113-month calendar. This is evidence against monthly cell noise being the sole source of the point estimate, although it cannot repair weak occupation-level identification.
6. Adding cross-occupation monthly score covariance and lagged covariance increases the SE moderately. At a 12-month HAC lag, the SE is 0.0491 and the normal 95% CI is [-0.2273, -0.0349]. Occupation clustering already allows arbitrary within-occupation serial dependence; this additional calculation addresses contemporaneous and nearby-month dependence across occupations. It is a model-based score sensitivity, not CPS design-based inference.
7. In the balanced pre-AI pseudo-break set (12 candidate breaks in 2017--2019), the median estimate is approximately zero and no estimate approaches the observed -0.1311. The most negative values in the unrestricted 34-break set occur at the beginning of the window with only one pre-break month, so they are endpoint artifacts. The pseudo-break estimates overlap heavily and their empirical tails are descriptive, not exact randomization p-values.
8. Preserving an entire donor month's contemporaneous cross-occupation residual vector in the historical power simulation does **not** close the prospective-versus-realized precision gap under the tested sharp global-sign DGP. The exercise is informative about that particular mechanism, but it does not prove that cross-occupation dependence is generally irrelevant or identify the source of the gap.

## 1. Canonical interval and precision

| Quantity | Frozen primary chronology | Repaired 113-month calendar |
|---|---:|---:|
| Estimate | -0.131074 | -0.134554 |
| Occupation-clustered SE | 0.044410 | 0.044957 |
| 95% wild-score CI | [-0.217075, -0.045073] | [-0.222307, -0.046801] |
| Wild-score p-value | 0.0030 | 0.0016 |
| Normal-theory MDE80 | 0.124418 | 0.125950 |
| Wild-score draws | 9,999 | 9,999 |

The frozen chronology remains the confirmatory estimand. The 113-month estimate is a post-outcome repaired-calendar substantive baseline that retains the frozen quintile membership and Webb scaling. It should be labeled as such rather than substituted silently for the frozen result.

Source files:

- `results/CANONICAL_PRIMARY_INTERVAL.csv`
- `results/REPAIRED_MONTHLY_BASELINE.csv`

## 2. Why the manuscript previously showed four intervals

| Source | 95% interval | Explanation |
|---|---:|---|
| Frozen confirmatory result | [-0.217038, -0.045110] | Original 999-draw interval |
| First-round calendar reproduction | [-0.216639, -0.045509] | Same estimator/sample; different 999 multipliers |
| First-round reference contrast | [-0.217889, -0.044258] | Same estimator/sample; different 999 common draws |
| First-round age comparison | [-0.219020, -0.043128] | Same estimator/sample; different 999 common draws |
| Minimum-100 sensitivity | [-0.219843, -0.042306] | Different 463-occupation sample; never primary |
| **Round-2 canonical primary** | **[-0.217075, -0.045073]** | **Same frozen estimator/sample; 9,999 draws** |

The variation among the first four intervals is finite-bootstrap Monte Carlo variation, not different substantive findings. The revision should report the final row wherever the frozen primary coefficient appears and identify sample-changing sensitivities separately.

Source: `results/INTERVAL_RECONCILIATION.csv`.

## 3. Paired architecture precision

All differences below equal beta minus the named alternative and use common occupation-level multipliers, preserving covariance by construction.

| Alternative | Paired difference | Paired SE | 95% paired CI | MDE80 |
|---|---:|---:|---:|---:|
| AIOE administration/equal | -0.0717 | 0.0454 | [-0.1614, 0.0181] | 0.1272 |
| AIOE ability/direct | -0.0273 | 0.0446 | [-0.1134, 0.0589] | 0.1250 |
| AIOE OEWS-weighted | -0.0665 | 0.0455 | [-0.1557, 0.0227] | 0.1273 |
| Eloundou alpha | -0.0324 | 0.0376 | [-0.1054, 0.0406] | 0.1053 |
| Eloundou gamma | 0.0259 | 0.0217 | [-0.0156, 0.0674] | 0.0609 |
| Webb AI | -0.0646 | 0.0535 | [-0.1682, 0.0389] | 0.1499 |
| OECD capability gap | -0.1115 | 0.0603 | [-0.2257, 0.0027] | 0.1689 |

The architecture comparisons are underpowered for small or moderate differences. For example, beta minus Webb AI is -0.0646, but its CI is [-0.1682, 0.0389] and its MDE80 is 0.1499. The appropriate conclusion is that the data do not distinguish these estimates at this precision. The table does not establish that the measures are economically equivalent.

Source: `results/PAIRED_ARCHITECTURE_PRECISION.csv`.

Reference-category contrasts are similarly imprecise except for Q5 minus Q3:

| Contrast | Estimate | 95% CI | MDE80 |
|---|---:|---:|---:|
| Q5 - Q1 | -0.1311 | [-0.2171, -0.0451] | 0.1244 |
| Q5 - Q2 | -0.0456 | [-0.1248, 0.0335] | 0.1137 |
| Q5 - Q3 | -0.0833 | [-0.1581, -0.0084] | 0.1081 |
| Q5 - Q4 | -0.0340 | [-0.1110, 0.0429] | 0.1099 |
| Q4 - Q2 | -0.0116 | [-0.0728, 0.0496] | 0.0884 |

Source: `results/REFERENCE_CONTRAST_PRECISION.csv`.

## 4. Sparse cells and boundary behavior

For the primary 468 occupations across 108 frozen months, the data contain 50,544 occupation-months and 101,088 age-specific cells.

| Age group | p10 | Median | p90 | Zero share | Below-five share |
|---|---:|---:|---:|---:|---:|
| 22--25 | 0 | 2 | 16 | 26.32% | 69.93% |
| 26--65 | 4 | 25 | 199 | 2.05% | 11.07% |

There are 13,305 zero-young cells, 1,036 zero-older cells, and 965 cells with both groups empty. The conditional grouped-binomial likelihood gives finite contributions when one age group has zero observed employment (`y=0` or `y=n`) and drops only the 965 cells with `n=0`.

Two deliberately non-primary selection diagnostics condition on realized respondent counts:

- Requiring at least five young respondent equivalents retains 302 occupations and 46.60% of occupation-month cells: estimate -0.1090, SE 0.0499, 95% CI [-0.2050, -0.0131].
- Requiring at least five respondent equivalents in both age groups retains 298 occupations and 47.18% of cells: estimate -0.1097, SE 0.0499, 95% CI [-0.2056, -0.0138].

These estimates cannot be advertised as cleaner versions of the primary result: selection is directly based on realized outcome counts, materially reduces support, and changes the estimand. They show that sparse cells contribute to magnitude but do not alone account for the headline estimate.

Sources: `results/RESPONDENT_COUNT_DISTRIBUTION.csv`, `results/BOUNDARY_CELL_DIAGNOSTICS.csv`, and `results/BOUNDARY_SELECTION_ESTIMATES.csv`.

## 5. Quarterly aggregation

| Calendar | Quarters | Incomplete quarters | Estimate | SE | 95% CI |
|---|---:|---:|---:|---:|---:|
| Frozen 108-month chronology | 39 | 8 | -0.131030 | 0.044411 | [-0.217591, -0.044468] |
| Repaired 113-month chronology | 39 | 3 | -0.134540 | 0.044953 | [-0.222246, -0.046834] |

The quarterly estimates match their monthly counterparts to within 0.00004 log points. Incomplete quarters remain because December 2022 is the omitted transition month, October 2025 is absent during the CPS shutdown, and the extract ends in July 2026. The result therefore demonstrates frequency robustness but not a fully balanced quarterly panel.

Sources: `results/QUARTERLY_ESTIMATES.csv` and `results/QUARTERLY_RESPONDENT_COUNTS.csv`.

## 6. CPS rotation and cross-occupation time dependence

The primary occupation-clustered SE (0.04441) already allows arbitrary serial dependence within occupation. To probe dependence induced across occupations in the same or nearby CPS months, the sensitivity adds a Newey--West covariance of aggregate month scores and subtracts the occupation-month intersection term.

| Time-HAC lag | Sensitivity SE | Normal 95% CI | MDE80 |
|---:|---:|---:|---:|
| 0 | 0.04493 | [-0.21914, -0.04300] | 0.12589 |
| 1 | 0.04655 | [-0.22232, -0.03983] | 0.13042 |
| 4 | 0.04830 | [-0.22575, -0.03640] | 0.13533 |
| 12 | 0.04909 | [-0.22729, -0.03485] | 0.13754 |
| 16 | 0.04897 | [-0.22705, -0.03510] | 0.13719 |

All estimated covariance matrices are positive semidefinite. The sensitivity widens inference but leaves the primary contrast separated from zero. Because CPS replicate-weight/design variables are unavailable here, these are model-based score covariances rather than a complete survey-design variance estimator. The manuscript should say this directly.

Source: `results/ROTATION_TIME_HAC_SENSITIVITY.csv`.

## 7. Pre-AI pseudo-break distribution

The authenticated extract begins in January 2017, so requested 2015--2016 placebo breaks are infeasible. The executable continuous pre-AI window is January 2017 through December 2019. The audit estimates all 34 feasible pseudo-breaks with at least one retained month on each side and also reports a balanced subset of 12 breaks with at least 12 retained months per side.

Two classification rules were run:

- pre-AI classifications and scaling constructed only with 2017--2019 weights;
- the frozen primary classification and Webb scaling held fixed.

| Classification | Break set | p05 | Median | p95 | One-sided empirical tail vs. -0.1311 |
|---|---|---:|---:|---:|---:|
| Pre-AI weights | All 34 | -0.1156 | -0.0056 | 0.0199 | 0.0571 |
| Pre-AI weights | Balanced 12 | -0.0064 | -0.0015 | 0.0128 | 0.0769 |
| Frozen classification | All 34 | -0.1139 | -0.0045 | 0.0195 | 0.0571 |
| Frozen classification | Balanced 12 | -0.0055 | -0.0010 | 0.0128 | 0.0769 |

The empirical tail uses a plus-one finite-sample convention. In the balanced set, none of the 12 estimates is as negative as -0.1311; hence 1/(12+1) = 0.0769 is the attainable floor, not evidence of an exact 7.69% test. Overlapping break estimates are dependent. Actual post-2022 outcomes were not used in the pseudo-break models, but the exercise was designed and executed after the headline outcome was known and must remain labeled exploratory.

Sources: `results/PSEUDO_BREAK_DISTRIBUTION_2017_2019.csv` and `results/PSEUDO_BREAK_SUMMARY.json`.

## 8. Historical simulation with contemporaneous covariance

The original beta/Webb Q5--Q1 power DGP, its 66 pre-period donor months, 42 synthetic post months, and fixed computerization shift were held constant. The only change was replacing independent occupation signs with one global sign per simulated path, preserving each donor month's entire cross-occupation residual vector. All 66 cyclic donor offsets and both signs were enumerated, yielding 132 paths per effect. No post-2022 outcome was read by the simulation.

Under the null:

- mean occupation-clustered SE: 0.012168;
- original independent-sign mean SE: 0.012170;
- realized primary SE: 0.044410;
- contemporaneous-covariance empirical SD: 0.006591;
- original independent-sign null RMSE: 0.012494.

Thus the sharp global-sign covariance sensitivity closes essentially none of the analytic SE gap and actually widens the empirical-SD gap. This rules out the tested global-sign implementation as an explanation for the prospective precision error. It does not validate the original power calculation or rule out other residual dependence structures: the DGP is sharp, only 132 unique paths exist, and occupation-clustered SEs still condition on aggregate CPS cells.

Sources: `results/HISTORICAL_CROSS_OCCUPATION_SIMULATION.json` and `results/HISTORICAL_CROSS_OCCUPATION_DRAWS.csv`.

## Manuscript-facing rules

The revision should follow these rules consistently:

1. Attach only **[-0.2171, -0.0451]** to the frozen -0.1311 primary estimate.
2. State the primary MDE80 (0.1244 log points) close to the headline inference, not only in the appendix.
3. For every paired architecture result whose CI includes zero, write "does not detect a difference" and report its CI/MDE. Do not write "the estimates are the same," "robust across measures," or "economically equivalent."
4. Describe quarterly aggregation, boundary-cell thresholds, time-HAC covariance, and pseudo-breaks as post-outcome exploratory diagnostics.
5. Do not turn the balanced pseudo-break tail into a conventional p-value.
6. Do not claim that the historical simulation resolves the prospective power failure. It rejects one proposed covariance mechanism only.
7. Keep the frozen and repaired chronologies visibly distinct.

## Reproduction and provenance

- Main program: `run_precision_rotation.py`
- SCC launcher: `scc_precision_rotation.sh`
- Reconciliation/audit program: `build_reconciliation_and_audit.py`
- Main execution receipt: `results/MAIN_EXECUTION_RECEIPT.json`
- Output hash manifest: `results/FINAL_OUTPUT_MANIFEST.json`
- Programmatic audit: `results/AUDIT_REPORT.json`

The public receipt contains input hashes rather than private microdata paths or data. No credential is embedded in the code or results.
