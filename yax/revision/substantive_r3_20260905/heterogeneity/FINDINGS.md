# CHAR-03/CHAR-04 findings

Status: **completed post-outcome exploratory analysis; not part of confirmatory YAX v1.1.** The treatment, samples, controls, and inference targets were written at pre-results commit `3d30996933a848872bd71795d87618b0f12e27c9`. Final SCC job 7469280 passed 81/81 automated checks. Restricted records remain on SCC.

## Pipeline checkpoint

The independent microdata rebuild reproduces the fully rebuilt corrected BASE-03 coefficient at `-0.1321094507921903` (target `-0.1321094508`). It scans 9,843,021 source rows, explicitly replaces the wide-file March 2017--2021 samples before eligibility, routes the pre-2020 occupation codes with conserved bridge mass, and fits the registered 113-month calendar. December 2022 remains excluded and nonexistent October 2025 is not interpolated. The model uses 468 occupations; its workstream-specific 9,999-draw interval is `[-0.219789, -0.044429]`. The manuscript should use the established canonical BASE-03 interval rather than create another headline interval from this checkpoint draw set.

## CHAR-03: a defensible microdata industry model is estimable

All 468 BASE-03 occupations and all 13 predeclared historical broad-industry groups enter the fixed risk set. Every industry contains all five exposure quintiles. The pre-outcome connectivity rule retains 3,127 occupation-by-industry strata, 99.09 percent of preperiod weighted stock and 98.91 percent of postperiod weighted stock. Of 353,351 possible stratum-month cells, 229,745 have positive total stock and 123,606 are zero; 123,264 positive cells have fewer than five respondent-equivalent source records. This sparsity is visible, but the target retains substantial fitted information.

| Model | Q5 coefficient | Occupation-cluster SE | 95% wild-score CI | MDE80 | Relative information |
|---|---:|---:|---:|---:|---:|
| Valid-industry records, aggregated to occupation-month | -0.132209 | 0.045356 | [-0.221165, -0.043254] | 0.127070 | 0.9946 |
| Occupation-industry-month cells | -0.137591 | 0.046016 | [-0.227517, -0.047665] | 0.128919 | 0.9760 |
| Plus broad-industry-by-young-by-post slopes | -0.098681 | 0.046239 | [-0.187981, -0.009380] | 0.129543 | 0.8243 |

Disaggregating the records changes the coefficient by `-0.005382`, with paired interval `[-0.013792, 0.003029]`. Adding broad-industry post slopes then moves it by `+0.038910`, paired interval `[0.008170, 0.069651]`, paired MDE80 `0.044417`. Relative to the valid-industry aggregate model, the combined movement is `+0.033529`, paired interval `[0.001270, 0.065787]`. The observed paired movement can have an interval excluding zero even though it is below the normal-theory 80-percent-power MDE; the MDE is a precision description, not a rejection threshold.

The conditioned coefficient remains negative and its interval excludes zero in this procedure, while the conditioning movement is distinguishable from zero. The correct interpretation is sensitivity to allowing different young-relative post changes across broad industries. It is not a causal share attributed to industry: the industry slopes can absorb AI-related and non-AI-related channels, and the model remains an occupation-exposure association.

## CHAR-04: education heterogeneity is not resolved

`EDUC` has complete valid coverage in this employed analysis sample. The pre-outcome common-support rule retains 429 occupations and 99.26 percent of preperiod weighted stock (99.31 percent postperiod). The common-support pooled coefficient is `-0.131363`.

| Education risk set | Q5 coefficient | Occupation-cluster SE | Pointwise 95% CI | Simultaneous 95% CI | MDE80 | Relative information |
|---|---:|---:|---:|---:|---:|---:|
| BA+ young versus BA+ older | -0.137986 | 0.070316 | [-0.274841, -0.001131] | [-0.293236, 0.017265] | 0.196997 | 0.1861 |
| Non-BA young versus non-BA older | -0.122630 | 0.054451 | [-0.230905, -0.014355] | [-0.242852, -0.002408] | 0.152549 | 0.5604 |

The paired BA-minus-non-BA difference is `-0.015356`, SE `0.071875`, interval `[-0.155703, 0.124991]`, and MDE80 `0.201364`. Thus the point estimates are similar, but the design cannot rule out economically meaningful education heterogeneity in either direction. It must not say the strata are equivalent or that education composition has been explained away. BA+ status is person-level attained education and differs from the occupation-level education-requirement control in CHAR-01.

Among employed ages 22--25, the BA+ share rises from 9.00 to 10.79 percent in Q1 and from 52.17 to 55.98 percent in Q5 between the pre/post aggregates. Enrollment among valid responses is nearly unchanged in Q1 (12.15 to 12.05 percent) and falls from 16.33 to 14.53 percent in Q5. These are descriptive composition changes among employed people, not measures of the supply of all young workers and not causal adjustments.

## Single-age profile: nonmonotone and multiplicity-sensitive

The exact-age common support contains 439 occupations and 99.30 percent of weighted stock in both periods. The pooled coefficient on that support is `-0.131437`. The single-age coefficients for ages 22, 23, 24, and 25 are respectively `-0.092928`, `-0.139994`, `-0.222028`, and `-0.082030`. Their simultaneous 95-percent intervals are respectively `[-0.238779, 0.052923]`, `[-0.279643, -0.000344]`, `[-0.394045, -0.050011]`, and `[-0.211551, 0.047492]`.

An asymptotic common-score Wald test of equality across the four coefficients gives chi-square `8.2064` on 3 degrees of freedom (`p=0.0419`). Pointwise, age 24 differs from the pooled ages-22--25 coefficient by `-0.090591`, with interval `[-0.178789, -0.002393]`. However, the predeclared simultaneous max-|t| interval for that paired difference is `[-0.201416, 0.020235]`; all four simultaneous age-minus-pooled intervals include zero. The multiplicity adjustment therefore changes the interpretation: the profile is suggestive and nonmonotone, but no individual age departure from the pooled coefficient is robust to the four-comparison simultaneous procedure. This cannot be converted into a labor-market-experience or cohort mechanism.

The mean age of employed 22--25-year-olds changes by less than 0.02 year in both Q1 and Q5 across the broad pre/post periods. `YEAR - AGE` is stored only as an approximate birth-year composition diagnostic. With repeated cross sections and no exact birth date, age, calendar time, and cohort cannot be separately identified; no cohort coefficient is claimed.

## Permanent limits

- The intervals target occupation-cluster economic-shock uncertainty. They are not full CPS survey-design inference.
- Broad historical `IND1990` groups are not modern NAICS supersectors.
- Industry conditioning changes the cell objective from occupation-month to occupation-industry-month; the paired aggregate-to-cell result separately records this change.
- Education is contemporaneous attained education and can itself change at ages 22--25.
- The older ages 26--65 are a comparison population, not an untreated group.
- Neither coefficient survival nor attenuation identifies an AI, industry, education, or cohort causal mechanism.

The numerical source of truth is `results/HETEROGENEITY_MODEL_RESULTS.csv`, with paired differences, stored occupation influence vectors, covariance matrices, risk-set membership, coverage, and composition files alongside it.
