"""Wild cluster bootstrap-t rejects a real effect and fails to reject a null."""
import numpy as np
from econlib.ols import build_fe_design
from econlib.wildboot import wild_cluster_bootstrap
from toydata import staggered_panel


def _design(df):
    X, names = build_fe_design(df, ["unit", "time"], extra={"treat": df["treat"].values})
    return X, df["y"].values, df["unit"].values, names.index("treat")


def test_rejects_strong_effect():
    df = staggered_panel(n_units=60, T=6, tau=2.0, seed=1)
    X, y, clusters, j = _design(df)
    res = wild_cluster_bootstrap(X, y, clusters, test_col=j, B=499, seed=7)
    assert res["p_value"] < 0.05
    assert abs(res["t_obs"]) > 3


def test_does_not_reject_null():
    df = staggered_panel(n_units=60, T=6, tau=0.0, seed=3)
    X, y, clusters, j = _design(df)
    res = wild_cluster_bootstrap(X, y, clusters, test_col=j, B=499, seed=7)
    assert res["p_value"] > 0.10
