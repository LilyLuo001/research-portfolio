"""DiD estimators recover a known constant treatment effect, and report ~0 when
there is none."""
from econlib.did import twfe_did, callaway_santanna, stacked_did, build_stacked
from toydata import staggered_panel


def test_twfe_recovers_tau():
    df = staggered_panel(n_units=60, T=6, tau=2.0, seed=1)
    res = twfe_did(df)
    assert abs(res["att"] - 2.0) < 0.3
    assert res["se"] > 0 and res["t"] > 3   # strong, precisely estimated


def test_callaway_santanna_recovers_tau():
    df = staggered_panel(n_units=60, T=6, tau=2.0, seed=1)
    res = callaway_santanna(df)
    assert abs(res["overall_att"] - 2.0) < 0.3
    assert res["att_gt"]                     # non-empty group-time grid


def test_did_null_is_near_zero():
    df = staggered_panel(n_units=60, T=6, tau=0.0, seed=2)
    assert abs(twfe_did(df)["att"]) < 0.3
    assert abs(callaway_santanna(df)["overall_att"]) < 0.3


def test_stacked_did_recovers_tau():
    df = staggered_panel(n_units=90, T=8, tau=2.0, seed=2)
    res = stacked_did(df, window=(-2, 2))
    assert abs(res["att"] - 2.0) < 0.3
    assert res["n_stacks"] == 2 and res["se"] > 0


def test_stacked_controls_are_clean():
    """No already-treated unit may sit in a stack's control group."""
    df = staggered_panel(n_units=90, T=8, tau=2.0, seed=2)
    s = build_stacked(df, window=(-2, 2))
    ft = df.groupby("unit")["first_treat"].first()
    for g, sub in s.groupby("stack"):
        t1 = sub["time"].max()
        controls = sub.loc[sub["treated_unit"] == 0, "unit"].unique()
        for u in controls:
            assert ft[u] == 0 or ft[u] > t1   # never-treated or treated after window


def test_stacked_null_is_near_zero():
    df = staggered_panel(n_units=90, T=8, tau=0.0, seed=3)
    assert abs(stacked_did(df, window=(-2, 2))["att"]) < 0.3
