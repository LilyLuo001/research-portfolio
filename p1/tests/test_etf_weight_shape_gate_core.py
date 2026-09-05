import math

import pandas as pd

from p1.etf_weight_shape_gates.gate_core import (
    actual_weight,
    align_portfolio_aum,
    classify_weight_style,
    impact_linear_bps,
    impact_sqrt_bps,
    latest_prior_snapshot,
    nav_shock_notional,
    required_flow_share_of_aum,
    same_and_next_trading_day_mappings,
)


def test_latest_snapshot_never_looks_forward_and_enforces_staleness():
    d = pd.DataFrame({"fund": [1, 1, 2], "date": ["2020-03-01", "2020-04-01", "2019-01-01"]})
    out = latest_prior_snapshot(d, pd.Timestamp("2020-03-31"), date_col="date", id_col="fund")
    assert out.set_index("fund").loc[1, "date"] == pd.Timestamp("2020-03-01")
    assert 2 not in set(out["fund"])


def test_actual_weight_does_not_normalize_missing_assets_away():
    got = actual_weight(pd.Series([20.0, 30.0]), pd.Series([100.0, 100.0]))
    assert got.tolist() == [0.2, 0.3]
    assert got.sum() == 0.5


def test_portfolio_aum_aligns_each_share_class_before_summing():
    d = pd.DataFrame(
        {
            "crsp_portno": [10, 10, 10, 10],
            "crsp_fundno": [1, 1, 2, 2],
            "aum_date": ["2020-02-29", "2020-04-01", "2020-03-15", "2020-04-02"],
            "aum_million": [60.0, 70.0, 45.0, 50.0],
        }
    )
    got = align_portfolio_aum(d, pd.Timestamp("2020-03-31")).iloc[0]
    assert got.aum_million == 105.0
    assert got.aum_date == pd.Timestamp("2020-02-29")
    assert got.aum_date_gap_days == 31
    assert got.aum_share_class_count == 2


def test_low_fit_cap_slope_is_not_called_sampled_without_benchmark():
    assert classify_weight_style(1.0, 0.5, False) == ("OTHER_WEIGHTED", "CAP_LIKE_LOW_FIT")
    assert classify_weight_style(1.0, 0.5, True) == ("CAP_SAMPLED", "CAP_SAMPLED_VERIFIED")


def test_capacity_calibrations_and_nav_label_formula():
    assert nav_shock_notional(1_000_000, 0.02, -0.05) == 1_000
    assert impact_linear_bps(10_000, 1_000_000) == 10.0
    assert impact_sqrt_bps(10_000, 1_000_000) == 10.0


def test_required_flow_inverts_frozen_impact_formula():
    flow = required_flow_share_of_aum(3.0, 1_000_000, 100_000, model="linear")
    assert math.isclose(flow, 0.03)


def test_reaction_date_rules_do_not_skip_monday_after_weekend():
    trading = pd.Series(pd.to_datetime(["2020-01-03", "2020-01-06", "2020-01-07"]))
    announcements = pd.Series(pd.to_datetime(["2020-01-03", "2020-01-04"]))
    same, nxt = same_and_next_trading_day_mappings(announcements, trading)
    assert same.tolist() == [pd.Timestamp("2020-01-03"), pd.Timestamp("2020-01-06")]
    assert nxt.tolist() == [pd.Timestamp("2020-01-06"), pd.Timestamp("2020-01-06")]
