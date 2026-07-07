"""Toy panels with known ground truth, so each estimator can be checked against a
number we set rather than against another estimator."""
import numpy as np
import pandas as pd


def staggered_panel(n_units=60, T=6, tau=2.0, seed=0):
    """Balanced staggered-adoption panel with a HOMOGENEOUS CONSTANT effect tau.

    Cohorts: a third never-treated (first_treat=0), a third treated at g1, a third
    at g2. Y_it = alpha_i + gamma_t + tau*1[t>=first_treat] + noise. TWFE is
    unbiased here (homogeneous constant effect), so both twfe_did and
    callaway_santanna should recover tau.
    """
    rng = np.random.default_rng(seed)
    g1, g2 = T // 3 + 1, T // 2 + 1
    alpha = rng.normal(0, 1, n_units)
    gamma = rng.normal(0, 1, T)
    rows = []
    for i in range(n_units):
        bucket = i % 3
        ft = 0 if bucket == 0 else (g1 if bucket == 1 else g2)
        for t in range(T):
            treated_now = 1 if (ft != 0 and t >= ft) else 0
            y = alpha[i] + gamma[t] + tau * treated_now + rng.normal(0, 0.3)
            rows.append((i, t, y, treated_now, ft))
    return pd.DataFrame(rows, columns=["unit", "time", "y", "treat", "first_treat"])


def single_cohort_panel(n_units=60, T=8, g=4, tau=1.0, seed=0, dynamic=True):
    """One treated cohort (half the units treated at g) vs never-treated controls.

    dynamic=True: effect at event time k = tau*(k+1) for k>=0, 0 before — so the
    event study should recover ~0 on the leads and ~tau*(k+1) on lag k.
    """
    rng = np.random.default_rng(seed)
    alpha = rng.normal(0, 1, n_units)
    gamma = rng.normal(0, 1, T)
    rows = []
    for i in range(n_units):
        treated_unit = (i % 2 == 0)
        ft = g if treated_unit else 0
        for t in range(T):
            eff = 0.0
            if treated_unit and t >= g:
                k = t - g
                eff = tau * (k + 1) if dynamic else tau
            y = alpha[i] + gamma[t] + eff + rng.normal(0, 0.3)
            rows.append((i, t, y, int(treated_unit and t >= g), ft))
    return pd.DataFrame(rows, columns=["unit", "time", "y", "treat", "first_treat"])


def two_period(n=40, tau=3.0, seed=0):
    """Simple pre/post design: half treated. Returns (pre, post, treat)."""
    rng = np.random.default_rng(seed)
    treat = np.array([1, 0] * (n // 2))
    pre = rng.normal(5, 1, n)
    post = pre + rng.normal(0, 0.3, n) + tau * treat
    return pre, post, treat
