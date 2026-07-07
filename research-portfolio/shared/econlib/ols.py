"""Small OLS core with cluster-robust inference and fixed-effect design helpers.

Everything downstream (DiD, event study, wild bootstrap) builds on these so the
linear algebra lives in exactly one place. numpy + pandas only — no statsmodels,
so the whole library installs with the packages CI already has.
"""
import numpy as np
import pandas as pd


def ols(X, y):
    """Return (beta, resid) for y = X beta + e via least squares."""
    X = np.asarray(X, float)
    y = np.asarray(y, float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return beta, resid


def cluster_robust_vcov(X, resid, clusters):
    """Cluster-robust (CR1) sandwich covariance, clustering on `clusters`.

    V = c (X'X)^-1 [ sum_g X_g' u_g u_g' X_g ] (X'X)^-1, with the standard
    G/(G-1) * (N-1)/(N-K) small-sample correction.
    """
    X = np.asarray(X, float)
    resid = np.asarray(resid, float)
    clusters = np.asarray(clusters)
    n, k = X.shape
    XtX_inv = np.linalg.pinv(X.T @ X)
    meat = np.zeros((k, k))
    groups = np.unique(clusters)
    for g in groups:
        idx = clusters == g
        Xg = X[idx]
        ug = resid[idx]
        s = Xg.T @ ug
        meat += np.outer(s, s)
    G = len(groups)
    c = (G / (G - 1.0)) * ((n - 1.0) / (n - k)) if G > 1 and n > k else 1.0
    return c * (XtX_inv @ meat @ XtX_inv)


def dummies(series, drop_first=True, prefix="d"):
    """One-hot design block for a categorical/fixed-effect column."""
    d = pd.get_dummies(pd.Series(series).astype("category"), prefix=prefix,
                       drop_first=drop_first, dtype=float)
    return d


def build_fe_design(df, columns, extra=None, add_const=True):
    """Stack an intercept, fixed-effect dummy blocks (one per column, first level
    dropped for identification), and any `extra` numeric columns into one matrix.
    Returns (X, names)."""
    blocks, names = [], []
    n = len(df)
    if add_const:
        blocks.append(np.ones((n, 1)))
        names.append("const")
    for col in columns:
        d = dummies(df[col], drop_first=True, prefix=col)
        blocks.append(d.values)
        names.extend(list(d.columns))
    if extra is not None:
        for name, vals in extra.items():
            blocks.append(np.asarray(vals, float).reshape(-1, 1))
            names.append(name)
    return np.hstack(blocks), names
