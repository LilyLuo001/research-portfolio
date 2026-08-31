# YAX V4 Estimand-Alignment Audit

This internal audit is machine-checkable against the listed V4 and v1.1 artifacts. It prevents silent switching among exposure coding, support, outcome, age contrast, estimator, and scale.

| Component | Exposure form | Support | Outcome | Young comparison | Estimator | Scale | Status |
|---|---|---|---|---|---|---|---|
| Headline Table 5A | Measure-specific categorical Q2–Q5; Q1 omitted | Native support for named measure/rule/control; 468 occupations for primary beta/Rule A/Webb | Occupation×age×month weighted stock | Ages 22–25 versus pooled 26–65 | Static grouped-binomial quasi-likelihood score equivalent to profiled PPML | Q5-versus-Q1 log coefficient; exponential ratio translation | Confirmatory v1.1 |
| Original six-measure Table 5B | Six measure-specific categorical Q2–Q5 codings | Native Rule-A/Webb sets: 495, 484, 485, 468, 468, 468 | Same stock | Same | Same static estimator | Q5-versus-Q1 log coefficient | Confirmatory v1.1; appendix in V4 |
| V4 six-measure Table 5B | Six measure-specific categorical Q2–Q5 codings | Literal six-way intersection: identical 444 occupations; hash `1e184b27678b7978d4b15e618db5b44f44b5e9ec1b50b69b53093ec62e0ce462` | Same stock | Same | Same static estimator | Q5-versus-Q1 log coefficient | Post-outcome supplementary V4; main text |
| Residual-support diagnostic | Continuous AI score residualized on continuous computerization | Pair-specific finite support | No outcome | n/a | Employment-weighted linear projection | Residual-variance share and inverse Herfindahl | Pre-outcome design diagnostic |
| Information-support diagnostic | Categorical Q5 target conditional on Q2–Q4 and control | Headline model's actual support | Fitted probabilities enter weights | Ages 22–25 versus pooled 26–65 | Profiled PPML/quasi-likelihood curvature after FE absorption and slope partialling | Conditional-information share and inverse Herfindahl | Post-outcome supplementary V3 |
| Main event study | Static beta/Rule-A/Webb Q1–Q5 classification; Q2–Q5 interacted by month | Same 468 occupations and support hash as primary headline model | Same stock | Same | Dynamic grouped-binomial quasi-likelihood score; Webb interacted by month | Monthly Q5-versus-Q1 log coefficient | Post-outcome supplementary V4 |
| Legacy continuous event study | Continuous standardized beta interacted by month | Beta/Rule-A/Webb, 468 occupations | Same stock | Same | Dynamic grouped-binomial quasi-likelihood score; Webb interacted by month | Monthly log coefficient per weighted SD | Confirmatory legacy series; supplementary joint test; appendix in V4 |
| Paired Test C | Alpha-specific and beta-specific categorical Q2–Q5 codings | Pairwise common Rule-A/Webb support, 468 occupations | Same stock | Same | Two static estimators with common occupation multipliers | Difference between architecture-specific Q5-versus-Q1 log coefficients | Confirmatory v1.1 |

## Machine checks

- Native Table 5B counts and hashes: `TABLE5B_SUPPORT_AUDIT.csv`.
- Literal-intersection result and common hash: `TABLE5B_COMMON_SUPPORT_RESULTS.csv` and `TABLE5B_SUPPORT_RECEIPT.json`.
- Categorical event support, Q5 membership, specification, and pretrend test: `CATEGORICAL_Q5_Q1_EVENT_STUDY_RESULT.json`.
- Confirmatory coefficient authority: immutable v1.1 result JSON and 195-row ledger.
- Quintile weights in the implemented static estimator are young-plus-older stocks over the 108 static estimation months, excluding December 2022. They are not pre-period-only weights.

## Interpretation identity

For the primary coefficient \(\hat\beta_5=-0.1311\), \(100\{\exp(-0.1311)-1\}=-12.3\%\). The economic object is:

> The young employment stock evolved 12.3% less favorably relative to the older-worker stock in Q5 than in Q1 over January 2023–July 2026.

It is not an unconditional decline in young employment and can reflect changes in the young stock, the older stock, or both.
