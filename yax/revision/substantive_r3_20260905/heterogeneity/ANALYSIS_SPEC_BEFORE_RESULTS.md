# CHAR-03/CHAR-04 industry and education heterogeneity

Status: **post-outcome exploratory; fixed before any CHAR-03/CHAR-04 post-period estimate was computed.**

This amendment responds to the integrated R3 revision plan and the referees' requests for an actual microdata industry comparison and transparent education/age composition evidence. It does not alter the corrected baseline or any prior result. The analysis is descriptive: industry and education can be confounders, mediators, or population definitions, and none of the models below identifies an AI effect.

## Common treatment, calendar, and inference contract

All models use the fully rebuilt BASE-03 treatment contract in `rebuilt_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv`: 468 Census-2018 occupations, beta quintiles and Webb-software normalization constructed only from January 2017--November 2022 employment. Memberships, cuts, and Webb normalization are held fixed. The outcome calendar is the corrected 113-month static calendar from January 2017 through July 2026: the five replacement Basic Monthly March samples are used, December 2022 is excluded as the transition month, and nonexistent October 2025 is neither inserted nor interpolated.

All source records must satisfy ages 22--65, employed `EMPSTAT` 10 or 12, finite positive `WTFINL`, a valid occupation, and membership in the fixed 468-occupation contract. Pre-2020 occupation records are routed through the audited Census-2010-to-2018 bridge; every fractional descendant inherits its source record's industry, age, and education status and receives the same bridge share of `WTFINL`. Records in the wide `03s` files for March 2017--2021 are explicitly replaced before eligibility filtering by the separately hashed `03b` Basic Monthly repair extract. One-sided zero outcome cells remain in the likelihood. There is no minimum realized young-cell rule.

The model is the same grouped-binomial young-relative employment-stock model used in BASE-03. All reported intervals use 9,999 common occupation-level Rademacher score multipliers (seed 2026090551). When a model contains occupation-by-industry strata, scores are summed to the occupation before resampling, so split industries of the same occupation never become independent clusters. Paired differences use the same multipliers and the joint score covariance. Report occupation-cluster SEs, bootstrap confidence intervals, normal-theory two-sided 5-percent 80-percent MDEs, nuisance-adjusted target information, effective information occupations, top-five information share, and matrix rank/condition. MDEs describe precision and are not decision thresholds. Nondetection is not equivalence.

## CHAR-03: industry conditioning in the microdata

`IND1990` is used because it is a time-consistent IPUMS recode and is observed on the employed risk set. The following broad groups are fixed from the documented 1990 code blocks before outcomes are read:

| Group | IND1990 codes |
|---|---|
| agriculture | 010--032 |
| mining | 040--050 |
| construction | 060 |
| manufacturing | 100--392 |
| transport/communications/utilities | 400--472 |
| wholesale trade | 500--571 |
| retail trade | 580--691 |
| finance/insurance/real estate | 700--712 |
| business and repair services | 721--760 |
| personal and lodging services | 761--791 |
| entertainment and recreation | 800--810 |
| professional and related services | 812--893 |
| public administration | 900--932 |

Codes 000 (not in universe), 940--960 (armed forces), and 998 (unknown) are excluded and their record and weighted-stock shares are reported. The labels are broad historical-industry groups, not modern NAICS supersectors.

The estimable occupation-by-industry risk set is selected using only January 2017--November 2022 data: retain an occupation-by-broad-industry stratum if it has positive preperiod stock for both ages 22--25 and ages 26--65. This is a pre-outcome connectivity rule, not a realized post-cell-size screen. Report the stock retained by period, quintile, and industry, every group's occupation/quintile span, the number and share of zero and thin occupation-industry-month cells, and the residual Q5 information after controls.

Estimate three models on exactly the records admitted by that fixed risk set:

1. aggregate those records back to occupation by month and fit the BASE-03 specification (`valid-industry aggregate baseline`);
2. retain occupation-by-industry-by-month cells, absorb occupation-by-industry and calendar-month fixed effects, and fit the same quintile-by-post and Webb-by-post slopes (`industry-cell baseline`);
3. add broad-industry-by-young-by-post slopes, omitting the industry with the largest preperiod stock (`industry-conditioned`).

The occupation-by-industry fixed effect absorbs the time-invariant occupation, industry, and occupation-industry lower-order terms in the young-relative ratio; calendar-month fixed effects absorb the common young-relative time path. Model 3's industry-by-post slopes are the requested lower-dimensional industry-specific young-relative post changes. Report paired changes from model 1 to 2 (changed cell objective), model 2 to 3 (industry conditioning on that objective), and model 1 to 3 (combined change). Do not call model 3 a causal decomposition. A dominant-industry proxy and occupation exclusions are not substitutes and will not be used.

The feasibility result is evidence-led, not threshold-selected. Estimation proceeds if at least two broad industries remain, the Q5 target retains positive nuisance-adjusted information, the slope matrix is full rank, and the estimator converges. Otherwise the exact rank, support, or convergence failure becomes the CHAR-03 blocker. Low retained stock or a large MDE makes the model uninformative but does not license another support rule.

## CHAR-04: education, enrollment composition, and age sensitivity

Educational attainment is measured with the person-level IPUMS `EDUC` code, not the occupation-level education-requirement characteristic used in CHAR-01. BA+ is fixed as codes 111 and 120--125 (bachelor's or postgraduate education); non-BA is codes 002--110. Codes 000, 001, and 999 are excluded, and their stock share is reported. Attainment is potentially changing for ages 22--25, so this is a population-stratified description, not a predetermined treatment or a labor-supply decomposition.

The paired education risk set is the intersection of BASE-03 occupations with positive January 2017--November 2022 young and older stock in **both** BA+ and non-BA strata. On this one pre-outcome common support, estimate:

1. the pooled 22--25 versus 26--65 model;
2. the BA+ 22--25 versus BA+ 26--65 model;
3. the non-BA 22--25 versus non-BA 26--65 model.

Report both stratum coefficients; the paired BA-minus-non-BA difference; each stratum-minus-pooled difference; common-support coverage; stock/risk-set counts; information and MDEs; and simultaneous max-|t| intervals for the two stratum coefficients. A paired interval containing zero means only that the analysis does not detect heterogeneity.

For age sensitivity, define a separate pre-outcome common support with positive 2017--November-2022 stock at every single age 22, 23, 24, and 25 and in the common older group ages 26--65. Estimate the pooled 22--25 model and four single-age-versus-26--65 models on that identical support. Report common-draw paired differences from the pooled estimate, simultaneous intervals, and a joint Wald test that the four single-age Q5 coefficients are equal. The older population is a comparison group, not an untreated group.

`SCHLCOLL` is used only for composition, because its codes describe contemporaneous enrollment and not completed education. For ages 22--25, codes 1--4 mean enrolled and code 5 means not enrolled; code 0 is out of universe or unavailable. Report by calendar year, beta quintile, and pre/post period the weighted BA+ share, enrolled share among valid enrollment responses, exact age mix, and an approximate birth-year measure `YEAR - AGE`. Because birth month and exact birth year are unavailable and age, period, and cohort are mechanically linked in repeated cross sections, no separately identified cohort effect will be estimated or claimed.

## Permanent limitations and outputs

Required outputs are industry/education support tables, model and paired-difference tables, age-profile and composition tables, influence/information tables, covariance/draw representations sufficient to reproduce paired and simultaneous inference, input/output hashes, an SCC execution receipt and log, automated self-checks, findings, and registry/ledger entries. Restricted microdata and identifiers remain on SCC and are never copied to the repository. Any implementation failure is serialized before repair; no failed specification is silently replaced.

Official construct documentation consulted before execution:

- IPUMS CPS `IND1990`: <https://cps.ipums.org/cps-action/variables/IND1990>
- IPUMS CPS `EDUC`: <https://cps.ipums.org/cps-action/variables/EDUC>
- IPUMS CPS `SCHLCOLL`: <https://cps.ipums.org/cps-action/variables/SCHLCOLL>
