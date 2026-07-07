"""Event-study (dynamic DiD) estimates and plotting.

Regresses the outcome on unit + calendar-time fixed effects and a set of
event-time (relative-to-treatment) indicators, with one pre-period held out as
the reference. The leads are the pre-trend test; the lags are the dynamic path.
Never-treated units contribute identification but no event-time dummies.
"""
import numpy as np
import pandas as pd
from .ols import ols, cluster_robust_vcov, build_fe_design


def event_study(df, y="y", unit="unit", time="time", first_treat="first_treat",
                window=(-4, 4), ref=-1):
    """Return per-event-time coefficients with cluster-robust SEs and 95% CIs.

    Result is a DataFrame indexed by event time k in [window[0], window[1]]
    (excluding ref), with columns coef, se, ci_low, ci_high. Event time
    k = time - first_treat; never-treated (first_treat==0) get no event dummies
    (baseline).
    """
    d = df.copy()
    ft = d[first_treat].values
    treated = (ft != 0) & (~np.isinf(ft))
    k = np.where(treated, d[time].values - ft, np.nan)
    d["_k"] = k

    lo, hi = window
    ks = [j for j in range(lo, hi + 1) if j != ref]
    extra = {}
    for j in ks:
        extra[f"k{j}"] = ((d["_k"] == j).astype(float)).values

    X, names = build_fe_design(d, [unit, time], extra=extra)
    beta, resid = ols(X, d[y].values)
    V = cluster_robust_vcov(X, resid, d[unit].values)

    rows = {}
    for j in ks:
        idx = names.index(f"k{j}")
        coef = float(beta[idx])
        se = float(np.sqrt(V[idx, idx]))
        rows[j] = {"coef": coef, "se": se,
                   "ci_low": coef - 1.96 * se, "ci_high": coef + 1.96 * se}
    out = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    out.index.name = "event_time"
    # the reference period is normalized to zero by construction
    out.loc[ref] = {"coef": 0.0, "se": 0.0, "ci_low": 0.0, "ci_high": 0.0}
    return out.sort_index()


def plot_event_study(es, ax=None, title="Event study"):
    """Plot coefficients with 95% CIs. matplotlib is imported lazily so the core
    library (and CI) never needs it installed."""
    import matplotlib.pyplot as plt  # noqa: local, optional dependency
    if ax is None:
        _, ax = plt.subplots(figsize=(6, 4))
    ax.axhline(0, color="0.7", lw=1)
    ax.axvline(-0.5, color="0.7", ls="--", lw=1)
    ax.errorbar(es.index, es["coef"],
                yerr=[es["coef"] - es["ci_low"], es["ci_high"] - es["coef"]],
                fmt="o-", capsize=3)
    ax.set_xlabel("event time")
    ax.set_ylabel("coefficient")
    ax.set_title(title)
    return ax
