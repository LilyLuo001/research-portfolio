# Exact Confirmatory PPML Inference Algorithm

This document describes the unchanged confirmatory algorithm in
`yax/analysis/run_frozen_v11.py` and
`dax/memo/power_calcs/young_relative_employment_power.py`. It is documentation,
not a new analysis or inference change.

## Estimator and analytic cluster variance

With two age groups, the three-way fixed-effect PPML model is estimated through
its grouped-binomial conditional equivalent. Let `y_i` be the young employment
stock, `n_i` the young-plus-older stock, and `p_hat_i` the fitted young share.
The fitted score residual is

`u_i = y_i - n_i p_hat_i`,

and the information weight is

`W_i = n_i p_hat_i (1-p_hat_i)`.

The slope matrix is absorbed against occupation and month fixed effects under
`W`, producing `R`. The slope information matrix is `H = R'WR`. Occupation
cluster scores are

`g_o = sum_(i in o) R_i u_i`.

The analytic cluster variance is

`G/(G-1) H^(-1) (sum_o g_o g_o') H^(-1)`,

where `G` is the number of occupation clusters. Its diagonal square roots are
the reported analytic cluster standard errors.

## Confirmatory one-step wild-score procedure

For the confirmatory bootstrap, each occupation score contribution is first
mapped through the information inverse:

`psi_o = sqrt(G/(G-1)) g_o' H^(-1)`.

For draw `b`, one Rademacher multiplier `v_bo` in `{-1,+1}` is drawn per
occupation and the centered coefficient shift is

`d_bj = sum_o v_bo psi_oj`.

The procedure therefore perturbs **occupation-cluster score/influence
contributions**. It does not perturb raw residuals or pseudo-outcomes, does not
impose a null-restricted PPML fit, and does not re-estimate PPML or the fixed
effects in each draw. Every confirmatory fit must converge before its one-step
draws are formed; there is consequently no draw-specific convergence filter.
Exactly 999 draws are required.

For a scalar coefficient `j`, the confirmatory code uses the analytic cluster
standard error `se_j` as a fixed studentizer. It computes

`t_b = d_bj / se_j`

and the observed statistic `t_obs = beta_hat_j / se_j`. The finite-sample
corrected two-sided p-value is

`(1 + sum_b 1[|t_b| >= |t_obs|]) / 1000`.

The 95% critical value is the higher empirical quantile of `|t_b|`. The
reported interval is the symmetric studentized interval

`beta_hat_j +/- q_.95(|t_b|) se_j`.

Although earlier manuscript drafts used generic “wild bootstrap” and
“percentile-t” language, this exact implementation is most precisely described
as a **one-step occupation-cluster Rademacher wild-score interval with a fixed
analytic cluster studentizer**.

## Paired beta-alpha procedure

Beta and alpha are fit separately on their pairwise common Rule-A/Webb support.
The same `G`-vector of Rademacher multipliers is applied to both estimators in
each of 999 draws. The code forms

`beta_beta,b* = beta_hat_beta + sum_o v_bo psi_beta,o`

and

`beta_alpha,b* = beta_hat_alpha + sum_o v_bo psi_alpha,o`,

then computes the centered paired shift

`d_Delta,b = (beta_beta,b* - beta_alpha,b*) - Delta_hat`.

Common multipliers preserve the covariance induced by common occupation
clusters. The paired standard error is the sample standard deviation of
`d_Delta,b`. Both the observed and bootstrap paired statistics use that same
fixed paired standard error. The p-value uses the finite-sample correction
above, and the confidence interval is

`Delta_hat +/- q_.95(|d_Delta,b / se_Delta|) se_Delta`.

No numerical economic-equivalence bound enters this procedure.
