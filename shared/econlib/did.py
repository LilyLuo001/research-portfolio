"""Difference-in-differences estimators.

Two entry points:
  twfe_did        — the two-way fixed-effects DiD coefficient (+ cluster-robust SE).
  callaway_santanna — group-time ATT(g,t) with a not-yet-treated comparison group,
                      robust to the staggered-adoption bias TWFE suffers under
                      heterogeneous timing (Callaway & Sant'Anna 2021).

Panel convention: long DataFrame with unit, time, outcome columns, plus either a
0/1 treatment-status column `treat` (=1 once unit i is treated at time t) or a
`first_treat` column (the period a unit is first treated; 0 = never treated).
"""
import numpy as np
import pandas as pd
from .ols import ols, cluster_robust_vcov, build_fe_design


def twfe_did(df, y="y", unit="unit", time="time", treat="treat"):
    """Y_it = a_i + b_t + beta*D_it + e. Returns dict with att, se, t.
    SE clusters on `unit`. Unbiased for a homogeneous constant effect; use
    callaway_santanna when effects vary across cohorts/time."""
    X, names = build_fe_design(df, [unit, time], extra={treat: df[treat].values})
    beta, resid = ols(X, df[y].values)
    V = cluster_robust_vcov(X, resid, df[unit].values)
    j = names.index(treat)
    att = float(beta[j])
    se = float(np.sqrt(V[j, j]))
    return {"att": att, "se": se, "t": att / se if se > 0 else np.nan}


def callaway_santanna(df, y="y", unit="unit", time="time", first_treat="first_treat"):
    """Group-time ATT(g,t) with a not-yet-treated (incl. never-treated) control.

    For cohort g (first_treat==g) and t>=g, using baseline period g-1:
        ATT(g,t) = E[Y_t - Y_{g-1} | G=g] - E[Y_t - Y_{g-1} | not yet treated at t]
    Returns dict with per-(g,t) ATTs and a cohort-size-weighted overall ATT.
    """
    wide = df.pivot(index=unit, columns=time, values=y)
    ft = df.groupby(unit)[first_treat].first()
    times = sorted(df[time].unique())
    cohorts = sorted(g for g in ft.unique() if g != 0 and not np.isinf(g))

    att_gt, weights, contribs = {}, [], []
    for g in cohorts:
        base = g - 1
        if base not in wide.columns:
            continue
        treated_units = ft.index[ft == g]
        n_g = len(treated_units)
        for t in times:
            if t < g or t not in wide.columns:
                continue
            # comparison = not yet treated at t (never-treated have first_treat==0)
            comp_units = ft.index[(ft == 0) | (ft > t)]
            if len(comp_units) == 0:
                continue
            dt_treat = (wide.loc[treated_units, t] - wide.loc[treated_units, base]).mean()
            dt_comp = (wide.loc[comp_units, t] - wide.loc[comp_units, base]).mean()
            att = float(dt_treat - dt_comp)
            att_gt[(int(g), int(t))] = att
            contribs.append(att)
            weights.append(n_g)

    overall = float(np.average(contribs, weights=weights)) if contribs else np.nan
    return {"att_gt": att_gt, "overall_att": overall}
