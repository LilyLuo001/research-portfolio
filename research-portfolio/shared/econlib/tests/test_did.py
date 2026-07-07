"""DiD estimators recover a known constant treatment effect, and report ~0 when
there is none."""
from econlib.did import twfe_did, callaway_santanna
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
