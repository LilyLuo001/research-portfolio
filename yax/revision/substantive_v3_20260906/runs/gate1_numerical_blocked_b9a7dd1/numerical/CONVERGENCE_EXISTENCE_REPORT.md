# V3 Gate-1 convergence and existence report

Status: **BLOCKED_ONE_OR_MORE_CORE_TARGETS_NOT_ESTABLISHED**

This is a numerical audit of the exact frequency-weighted grouped-binomial objective. It does not add pseudocounts, penalties, or a realized-count support rule. Boundary nuisance groups are profiled to their extended-likelihood supremum and recorded.

| model | core rows | profiled boundary rows | graph components | treatment rank | separation | focal target | classification |
|---|---:|---:|---:|---:|---|---:|---|
| pooled | 51891 | 0 | 1 | 5/5 | False | -0.132109461 | BLOCKED_NUMERICAL_OR_FULL_HESSIAN_BENCHMARK |
| family_post | 51891 | 0 | 1 | 26/26 | False | -0.021598877 | BLOCKED_NUMERICAL_OR_FULL_HESSIAN_BENCHMARK |
| family_month | 51891 | 0 | 22 | 5/5 | False | -0.021675189 | BLOCKED_NUMERICAL_OR_FULL_HESSIAN_BENCHMARK |
| dynamics_unconditioned | 51891 | 0 | 1 | 190/190 | False | -0.119890085 | BLOCKED_NUMERICAL_OR_FULL_HESSIAN_BENCHMARK |
| dynamics_family_month | 51891 | 0 | 22 | 190/190 | False | -0.207442767 | BLOCKED_NUMERICAL_OR_FULL_HESSIAN_BENCHMARK |
| post_2020_unconditioned | 35014 | 77 | 1 | 5/5 | False | -0.118069091 | BLOCKED_NUMERICAL_OR_FULL_HESSIAN_BENCHMARK |
| post_2020_family_month | 35014 | 77 | 22 | 5/5 | False | -0.030402463 | BLOCKED_NUMERICAL_OR_FULL_HESSIAN_BENCHMARK |
| seasonal_quintile_month_unconditioned | 51891 | 0 | 1 | 49/49 | False | -0.132600705 | BLOCKED_NUMERICAL_OR_FULL_HESSIAN_BENCHMARK |
| seasonal_quintile_month_family_month | 51891 | 0 | 22 | 49/49 | False | -0.022570245 | BLOCKED_NUMERICAL_OR_FULL_HESSIAN_BENCHMARK |
| seasonal_occupation_month_unconditioned | 51121 | 770 | 12 | 5/5 | False | -0.132373675 | BLOCKED_NUMERICAL_OR_FULL_HESSIAN_BENCHMARK |
| seasonal_occupation_month_family_month | 51121 | 770 | 264 | 5/5 | False | -0.020605719 | BLOCKED_NUMERICAL_OR_FULL_HESSIAN_BENCHMARK |

A PASS means rank, recession-direction, two-solver, fitted-mean, gradient, and target-profile checks all passed at the predeclared tolerances. A BLOCKED result is retained as a numerical finding and is not replaced by another estimator.
