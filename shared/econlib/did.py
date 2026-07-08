"""Difference-in-differences estimators.

Three entry points:
  twfe_did        — the two-way fixed-effects DiD coefficient (+ cluster-robust SE).
  callaway_santanna — group-time ATT(g,t) with a not-yet-treated comparison group,
                      robust to the staggered-adoption bias TWFE suffers under
                      heterogeneous timing (Callaway & Sant'Anna 2021).
  stacked_did     — per-event clean-control stacking (Cengiz et al. 2019 style):
                    each cohort gets its own event window whose controls are
                    clean throughout (never-treated, or first treated after the
                    window ends — no already-treated units), the sub-experiments
                    are stacked, and the pooled effect is estimated with
                    event-saturated unit and time fixed effects. This is P1's
                    main-spec design (stacked DiD by conversion wave).

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


def build_stacked(df, y="y", unit="unit", time="time", first_treat="first_treat",
                  window=(-4, 4)):
    """Assemble the stacked dataset: one sub-experiment per treatment cohort.

    For each cohort g the window is calendar time [g+window[0], g+window[1]].
    Included units: the cohort itself, plus CLEAN controls — units never treated
    or first treated strictly after the window ends. Already-treated units are
    excluded (the contamination stacking exists to avoid). Adds columns:
      stack (=g), event_time (t-g for treated, NaN for controls),
      treated_unit (0/1), post (0/1), D (=treated_unit*post).
    """
    ft = df.groupby(unit)[first_treat].first()
    cohorts = sorted(g for g in ft.unique() if g != 0 and not np.isinf(g))
    lo, hi = window
    frames = []
    for g in cohorts:
        t0, t1 = g + lo, g + hi
        clean = ft.index[(ft == g) | (ft == 0) | (ft > t1)]
        sub = df[df[unit].isin(clean) & df[time].between(t0, t1)].copy()
        if sub.empty:
            continue
        sub["stack"] = g
        tr = sub[unit].map(ft).eq(g)
        sub["treated_unit"] = tr.astype(float)
        sub["post"] = (sub[time] >= g).astype(float)
        sub["D"] = sub["treated_unit"] * sub["post"]
        sub["event_time"] = np.where(tr, sub[time] - g, np.nan)
        frames.append(sub)
    if not frames:
        raise ValueError("no cohorts with a non-empty clean window")
    return pd.concat(frames, ignore_index=True)


def stacked_did(df, y="y", unit="unit", time="time", first_treat="first_treat",
                window=(-4, 4)):
    """Pooled stacked-DiD effect with event-saturated fixed effects.

    Y = a_{i,stack} + b_{t,stack} + beta*D + e, clustered on `unit` (a unit
    appearing in several stacks is one cluster). Returns dict with att, se, t,
    n_stacks, n_obs, and the stacked frame under 'stacked' for event studies.
    """
    s = build_stacked(df, y=y, unit=unit, time=time, first_treat=first_treat,
                      window=window)
    s["_us"] = s[unit].astype(str) + "@" + s["stack"].astype(str)
    s["_ts"] = s[time].astype(str) + "@" + s["stack"].astype(str)
    X, names = build_fe_design(s, ["_us", "_ts"], extra={"D": s["D"].values})
    beta, resid = ols(X, s[y].values)
    V = cluster_robust_vcov(X, resid, s[unit].values)
    j = names.index("D")
    att = float(beta[j])
    se = float(np.sqrt(V[j, j]))
    return {"att": att, "se": se, "t": att / se if se > 0 else np.nan,
            "n_stacks": int(s["stack"].nunique()), "n_obs": len(s), "stacked": s}
