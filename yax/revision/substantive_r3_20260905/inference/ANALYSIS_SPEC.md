# Dependence and few-cluster analysis specification

Status: **post-outcome exploratory; written before the R3 dependence results were produced.**

This module compares three registered corrected-calendar objects on the same 468-occupation support and historical treatment assignment: the baseline Q5--Q1 coefficient; the SOC2-by-young-by-post conditioned Q5--Q1 coefficient; and the paired conditioned-minus-baseline movement.

## Stochastic targets

The existing occupation-cluster covariance treats occupations as the independent shock clusters and permits arbitrary serial dependence within occupation. The SOC2 sensitivity instead permits arbitrary dependence among occupations in each of 22 broad families; it is a few-cluster, model-based economic-shock sensitivity, not CPS design-based inference. The occupation-plus-time-HAC calculation permits additional cross-occupation covariance across nearby calendar months. It is also model-based and must not be combined mechanically with a household-sampling variance.

## Corrected inclusion--exclusion HAC

Let `psi[o,t]` denote nuisance-adjusted estimator-influence contributions in coefficient units. For lag `L`, the uncorrected meat is

`B_occ + HAC_L(sum_o psi[o,t]) - sum_o HAC_L(psi[o,t])`.

The last term removes the entire within-occupation HAC overlap at lags zero through `L`, not only the lag-zero occupation-month cell meat. Elapsed calendar months define lags. December 2022 and October 2025 therefore appear as zero-contribution placeholders in the full January-2017--July-2026 calendar, rather than making November--January or September--November artificially adjacent.

Component meats are first reported without component-specific finite-cluster multipliers. A transparent companion multiplies the final combined covariance by the same `G_occ/(G_occ-1)` factor used for the occupation-cluster comparison. No positive-semidefinite projection or silent clipping is allowed; eigenvalues and target variances are reported as computed.

## SOC2 few-cluster sensitivity

Aggregate the same nuisance-adjusted target contributions to the 22 SOC2 families. Report CRV1 scale and fixed-studentizer wild-score intervals with 99,999 common draws under:

- Rademacher weights; and
- Webb six-point weights `{-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)}` with equal probability.

The procedure is a sensitivity with 22 clusters, not a declaration that SOC2 is the uniquely correct sampling level. Common draws preserve covariance for the paired movement. Monte Carlo error of bootstrap p-values is reported.

## Noncoverage

This module does not claim repeated-CPS-sampling inference. Household/sample-unit cell reconstruction and finite-sample full-refit simulation are separate registered workstreams.

