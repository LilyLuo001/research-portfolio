# YAX V5.1 two-way cluster sensitivity

This model-based dependence sensitivity uses the standard inclusion–exclusion covariance

\[
V_{o,t}=V_o+V_t-V_{o\cap t},
\]

with absorbed observation scores, finite-cluster corrections for occupation and calendar month, and the occupation-month cell as the intersection. It changes no point estimate or regressor. It is not a reconstruction of the CPS survey design.

| Specification | Coefficient | Occupation-cluster SE | Two-way SE | Two-way normal 95% CI |
|---|---:|---:|---:|---:|
| Primary beta + Webb, native strict support | -0.13107 | 0.04441 | 0.04493 | [-0.21914, -0.04300] |
| AIOE administrative, common support | -0.07386 | 0.04090 | 0.04106 | [-0.15433, 0.00661] |
| AIOE ability, common support | -0.10285 | 0.03811 | 0.03810 | [-0.17754, -0.02817] |
| AIOE source weighted, common support | -0.10210 | 0.04223 | 0.04213 | [-0.18467, -0.01953] |
| Eloundou alpha, common support | -0.10132 | 0.04171 | 0.04127 | [-0.18221, -0.02042] |
| Eloundou beta, common support | -0.12896 | 0.04517 | 0.04578 | [-0.21869, -0.03923] |
| Eloundou broad, common support | -0.14652 | 0.04522 | 0.04504 | [-0.23480, -0.05823] |

There are 108 month clusters, 468 occupations in the primary model, and 444 occupations in each common-support model. Point estimates reproduce the sealed coefficients to `1e-10`. The sensitivity leaves the primary inference and the five-versus-one common-support interval pattern unchanged.
