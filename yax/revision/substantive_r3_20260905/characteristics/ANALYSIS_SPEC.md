# Occupational-characteristic conditioning analysis

Status: **post-outcome exploratory; specified before the R3 characteristic-conditioning results were produced.**

The target is the corrected-calendar beta-exposure Q5--Q1 coefficient for ages 22--25 relative to ages 26--65. Historical frozen quintile assignments and the original Webb-software normalization are retained. The native 468-occupation corrected-calendar baseline is first reproduced. All characteristic models then use one literal common support fixed before fitting, so the effect of sample loss is separated from the effect of conditioning.

## Registered controls and order

Each continuous occupational characteristic is standardized using 2017--2019 employment weights on the common support and interacted with `young x post`. The one-at-a-time panel adds:

1. O\*NET computer-use importance;
2. Dingel--Neiman telework feasibility;
3. preperiod mean occupational wage;
4. externally coded education requirement;
5. Autor--Dorn routine-task intensity;
6. O\*NET manual/physical ability importance;
7. a total-employment pandemic shortfall;
8. a young-relative pandemic-shortfall sensitivity; and
9. SOC2-by-young-by-post controls.

The cumulative economic sequence adds computer use, remotability, the wage/education/routine/manual block, the total-employment pandemic shortfall, and SOC2 controls. A separately registered parsimonious combined model includes computer use, remotability, education requirement, routine-task intensity, total-employment shortfall, and SOC2 controls. Wage is omitted from that parsimonious model because it is an occupational outcome proxy overlapping education; manual content is omitted because it is a broad counter-dimension rather than a parsimonious computerization confound. These omissions are fixed before estimates are read.

## Pandemic shortfall

The primary shortfall is the mean 2020--November-2022 gap between observed total employment and an occupation-specific linear level trend fit during 2017--2019, divided by the occupation's 2017--2019 mean employment. All 36 preperiod months enter, including observed sampling zeros; no log pseudocount, winsorization, or sign-based trimming is used. Positive values mean observed employment fell below the extrapolated trend.

The companion young-relative measure fits a weighted linear trend to the age-22--25 share of employment among ages 22--65 during 2017--2019 and averages predicted-minus-observed shares over 2020--November 2022, weighting by total age-22--65 employment. It is a generated regressor estimated from related CPS outcomes. Main wild-score intervals condition on its realized value and therefore do not capture its first-stage sampling error. That limitation is binding until an appropriate household/sample-unit resampling exercise rebuilds it.

## Reporting and inference

For every model report the coefficient, occupation-clustered SE, common-draw interval, normal-theory 80-percent MDE, support, employment coverage, nuisance-adjusted target information, fixed-effect-adjusted raw target information, information-retention ratio, target VIF-like ratio, effective occupation count, top-five information share, and information-matrix condition number. Report augmented-minus-common-baseline paired differences using identical occupation-level Rademacher multipliers.

Coefficient survival or attenuation is descriptive. These characteristics can be confounders, mediators, or proxies for other occupational evolution. The analysis does not identify an AI causal effect.

