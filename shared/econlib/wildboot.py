"""Wild cluster bootstrap-t (Cameron, Gelbach & Miller 2008).

The right inference tool when the number of clusters is small — exactly the
regime P1 (funds), E2 (issuers) and DAX (occupations) all live in. Imposes the
null on the residuals (the WCR bootstrap), then resamples with cluster-level
Rademacher weights and compares the bootstrap t-distribution to the observed t.
"""
import numpy as np
from .ols import ols, cluster_robust_vcov


def _tstat(X, y, clusters, j):
    beta, resid = ols(X, y)
    V = cluster_robust_vcov(X, resid, clusters)
    se = np.sqrt(V[j, j])
    return beta[j] / se if se > 0 else 0.0, beta, resid


def wild_cluster_bootstrap(X, y, clusters, test_col, B=999, seed=0):
    """Test H0: beta[test_col] = 0 via the restricted wild cluster bootstrap-t.

    Returns dict with t_obs and a two-sided bootstrap p-value. `X` includes the
    tested column; the null is imposed by re-fitting without it and resampling
    that model's fitted values + residuals.
    """
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    clusters = np.asarray(clusters)
    rng = np.random.default_rng(seed)

    t_obs, _, _ = _tstat(X, y, clusters, test_col)

    # restricted fit: impose the null by dropping the tested regressor
    keep = [c for c in range(X.shape[1]) if c != test_col]
    Xr = X[:, keep]
    beta_r, resid_r = ols(Xr, y)
    fitted_r = Xr @ beta_r

    groups = np.unique(clusters)
    count = 0
    for _ in range(B):
        w = rng.choice([-1.0, 1.0], size=len(groups))
        wmap = dict(zip(groups, w))
        wvec = np.array([wmap[c] for c in clusters])
        y_star = fitted_r + wvec * resid_r
        t_star, _, _ = _tstat(X, y_star, clusters, test_col)
        if abs(t_star) >= abs(t_obs):
            count += 1
    p = (count + 1) / (B + 1)  # +1 keeps the p-value valid (never exactly 0)
    return {"t_obs": float(t_obs), "p_value": float(p), "B": B}
