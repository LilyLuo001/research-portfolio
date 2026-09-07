# V3 Gate-1 convergence and existence report

Status: **PASS_ALL_CORE_TARGETS_NUMERICALLY_AUDITED**

This is a numerical audit of the exact frequency-weighted grouped-binomial objective. It does not add pseudocounts, penalties, or a realized-count support rule. Boundary nuisance groups are profiled to their extended-likelihood supremum and recorded.

| model | core rows | profiled boundary rows | graph components | treatment rank | separation | focal target | classification |
|---|---:|---:|---:|---:|---|---:|---|
| pooled | 51891 | 0 | 1 | 5/5 | False | -0.132109451 | PASS_FINITE_EXTENDED_MLE_TARGET |
| family_post | 51891 | 0 | 1 | 26/26 | False | -0.021598985 | PASS_FINITE_EXTENDED_MLE_TARGET |
| family_month | 51891 | 0 | 22 | 5/5 | False | -0.021674952 | PASS_FINITE_EXTENDED_MLE_TARGET |
| dynamics_unconditioned | 51891 | 0 | 1 | 190/190 | False | -0.119888765 | PASS_FINITE_EXTENDED_MLE_TARGET |
| dynamics_family_month | 51891 | 0 | 22 | 190/190 | False | -0.207433689 | PASS_FINITE_EXTENDED_MLE_TARGET |
| post_2020_unconditioned | 35014 | 77 | 1 | 5/5 | False | -0.118069092 | PASS_FINITE_EXTENDED_MLE_TARGET |
| post_2020_family_month | 35014 | 77 | 22 | 5/5 | False | -0.030402197 | PASS_FINITE_EXTENDED_MLE_TARGET |
| seasonal_quintile_month_unconditioned | 51891 | 0 | 1 | 49/49 | False | -0.132600724 | PASS_FINITE_EXTENDED_MLE_TARGET |
| seasonal_quintile_month_family_month | 51891 | 0 | 22 | 49/49 | False | -0.022570213 | PASS_FINITE_EXTENDED_MLE_TARGET |
| seasonal_occupation_month_unconditioned | 51121 | 770 | 12 | 5/5 | False | -0.132373672 | PASS_FINITE_EXTENDED_MLE_TARGET |
| seasonal_occupation_month_family_month | 51121 | 770 | 264 | 5/5 | False | -0.020605758 | PASS_FINITE_EXTENDED_MLE_TARGET |

A PASS means rank, recession-direction, two-solver, fitted-mean, gradient, and target-profile checks all passed at the predeclared tolerances. A BLOCKED result is retained as a numerical finding and is not replaced by another estimator.
