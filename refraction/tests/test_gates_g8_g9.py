"""G8 and G9 runners on synthetic data — so both execute the day their inputs land.

Neither gate can be MEASURED yet: post-conversion holdings and ETF shares outstanding do
not exist in the repo. What is tested here is that the machinery implements the registered
safeguards, including the ones that make it refuse.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from refraction.gates import g8_first_stage as g8   # noqa: E402
from refraction.gates import g9_continuity as g9    # noqa: E402

CONFIG = yaml.safe_load((ROOT / "refraction" / "frozen_config.yaml").read_text())


# --------------------------------------------------------------------------- #
# G9                                                                           #
# --------------------------------------------------------------------------- #

def holdings(wave, pairs):
    return pd.DataFrame([{"wave": wave, "permno": p, "weight": w} for p, w in pairs])


def test_an_unchanged_portfolio_scores_perfect_continuity():
    pre = holdings("W1", [(1, .5), (2, .3), (3, .2)])
    c = g9.wave_continuity(pre, pre.copy())
    assert c.loc[0, "overlap_weight"] == pytest.approx(1.0)
    assert c.loc[0, "weight_corr"] == pytest.approx(1.0)
    assert c.loc[0, "turnover"] == pytest.approx(0.0)


def test_a_wholesale_portfolio_change_is_caught():
    pre = holdings("W1", [(1, .5), (2, .5)])
    post = holdings("W1", [(3, .5), (4, .5)])
    c = g9.wave_continuity(pre, post)
    assert c.loc[0, "overlap_weight"] == pytest.approx(0.0)
    assert c.loc[0, "turnover"] == pytest.approx(1.0)


def test_overlap_is_weighted_not_counted():
    """Dropping many tiny names is not the same event as dropping a few big ones."""
    pre = holdings("W1", [(1, .90), (2, .04), (3, .03), (4, .03)])
    post = holdings("W1", [(1, .90), (5, .10)])          # 3 of 4 names gone, 90% weight kept
    c = g9.wave_continuity(pre, post)
    assert c.loc[0, "overlap_weight"] > 0.85
    assert c.loc[0, "overlap_count"] < 0.35


def test_a_wave_missing_one_side_is_recorded_not_scored():
    c = g9.wave_continuity(holdings("W1", [(1, 1.0)]), holdings("W2", [(1, 1.0)]))
    assert c["reason"].str.contains("missing").any()
    assert c["overlap_weight"].isna().any()


def test_the_threshold_sensitivity_curve_shows_the_cost_of_each_cutoff():
    """Safeguard 6: the restriction is read off a curve, not legislated by one number."""
    pre = holdings("W1", [(1, 1.0)])
    frames = [g9.wave_continuity(pre, holdings("W1", [(1, w), (9, 1 - w)]))
              .assign(wave=f"W{i}") for i, w in enumerate([0.55, 0.75, 0.95])]
    cont = pd.concat(frames, ignore_index=True)
    curve = g9.threshold_sensitivity(cont, grid=[0.5, 0.7, 0.9])
    assert list(curve["waves_retained"]) == [3, 2, 1]      # monotone, and visible


def test_summarize_reports_the_registered_responses_not_a_bare_verdict():
    pre = holdings("W1", [(1, 1.0)])
    s = g9.summarize(g9.wave_continuity(pre, pre.copy()), CONFIG)
    assert s["confirmatory_response"] == "restrict_to_high_continuity_waves"
    assert "separately" in s["secondary_interpretation"]
    assert "verdict" not in s


# --------------------------------------------------------------------------- #
# G8                                                                           #
# --------------------------------------------------------------------------- #

def make_panel(n_stocks=40, n_days=120, a1=0.0, seed=0):
    """r_resid_fwd = 0.1*CR + a1*(CR*absL) + noise.

    CR is a FUND-level variable: every constituent of the ETF shares the same
    creation/redemption on a given day. That structure is the whole point of the
    fund x date fixed effects — it absorbs the common flow shock and leaves
    identification to cross-sectional differences in |L| within one ETF-day.
    """
    rng = np.random.default_rng(seed)
    absL = {1000 + i: float(rng.uniform(0, 1)) for i in range(n_stocks)}
    cr_by_day = {t: float(rng.normal(0, 1)) for t in range(n_days)}
    rows = []
    for t in range(n_days):
        cr = cr_by_day[t]                       # one flow per fund-day, shared
        for i in range(n_stocks):
            p = 1000 + i
            rows.append({"permno": p, "fund": "F1",
                         "date": pd.Timestamp("2023-01-02") + pd.Timedelta(days=t),
                         "days_since_conversion": 21 + t, "CR": cr, "absL": absL[p],
                         "r_resid_fwd": 0.1 * cr + a1 * cr * absL[p] + rng.normal(0, .05),
                         "r_resid_lag": rng.normal(0, .05), "mkt": rng.normal(0, .01)})
    return pd.DataFrame(rows)


def test_the_calibration_sample_excludes_fomc_dates_and_the_seasoning_window():
    panel = make_panel(n_stocks=2, n_days=300)
    fomc = [pd.Timestamp("2023-02-01")]
    s = g8.build_calibration_sample(panel, fomc, CONFIG)
    assert s.attrs["n_dropped_fomc"] > 0
    assert s["days_since_conversion"].min() >= 21
    assert s["days_since_conversion"].max() <= 252
    assert not (pd.to_datetime(s["date"]) == fomc[0]).any()


def test_the_pooled_interaction_recovers_a_planted_connectivity_slope():
    r = g8.pooled_interaction(make_panel(a1=0.30, seed=1))
    assert r["a1"] == pytest.approx(0.30, abs=0.05)
    assert r["t_a1"] > 3 and r["design"] == "pooled_interaction"


def test_fund_date_fixed_effects_absorb_the_common_flow_shock():
    """Identification must come from differential exposure WITHIN one ETF-day, not from
    common ETF-level flow. With CR constant within a fund-date, its main effect is
    absorbed by construction — so it is reported as None rather than as an estimate."""
    r = g8.pooled_interaction(make_panel(a1=0.30, seed=7))
    assert r["fixed_effects"] == "fund_x_date"
    assert r["flow_main_effect"] is None
    # and the interaction still identifies
    assert r["t_a1"] > 3


def test_cr_interacted_controls_are_carried_when_supplied():
    panel = make_panel(a1=0.30, seed=8)
    panel["size"] = np.tile(np.linspace(1, 2, 40), 120)
    r = g8.pooled_interaction(panel, z_controls=("size",))
    assert r["cr_interacted_controls"] == ["size"]
    assert r["a1"] == pytest.approx(0.30, abs=0.06)


def test_licensing_refuses_on_the_corroborating_return_outcome():
    """Clarification 2026-08-19: a signed price-persistence response cannot license the
    measure — it can be zero or negative while connectivity is strong."""
    import copy
    cfg = copy.deepcopy(CONFIG)
    cfg["gate0_thresholds"]["first_stage_primary_alpha"] = 0.05
    r = g8.pooled_interaction(make_panel(a1=0.30, seed=9))
    with pytest.raises(g8.SafeguardViolation) as e:
        g8.verdict(r, cfg, outcome_class="signed_price_response_not_magnitude")
    assert "TRADING connectivity" in str(e.value)


def test_the_pooled_interaction_finds_nothing_when_there_is_nothing():
    r = g8.pooled_interaction(make_panel(a1=0.0, seed=2))
    assert abs(r["t_a1"]) < 3


def test_the_two_step_is_refused_without_uncertainty_propagation():
    """Safeguard 1: phi-hat is noisy and may not enter a second stage as an error-free
    outcome."""
    with pytest.raises(g8.SafeguardViolation) as e:
        g8.two_step(make_panel(), propagate_uncertainty=False)
    assert "uncertainty propagation" in str(e.value)


def test_the_two_step_runs_when_uncertainty_is_propagated():
    phis = g8.two_step(make_panel(a1=0.3, seed=3), propagate_uncertainty=True)
    assert len(phis) > 10 and {"phi", "absL", "n_obs"} <= set(phis.columns)


def test_the_verdict_refuses_while_the_significance_level_is_undecided():
    """The state the config is in today: alpha is null, so G8 cannot be adjudicated."""
    r = g8.pooled_interaction(make_panel(a1=0.3, seed=4))
    assert CONFIG["gate0_thresholds"]["first_stage_primary_alpha"] is None
    with pytest.raises(g8.SafeguardViolation) as e:
        g8.verdict(r, CONFIG, outcome_class="trading_connectivity")
    assert "specification search" in str(e.value)


def test_the_verdict_is_one_sided_on_the_linear_coefficient():
    import copy
    cfg = copy.deepcopy(CONFIG)
    cfg["gate0_thresholds"]["first_stage_primary_alpha"] = 0.05
    licensed = g8.verdict(g8.pooled_interaction(make_panel(a1=0.30, seed=5)), cfg,
                          outcome_class="trading_connectivity")
    assert licensed["licensed"] is True and licensed["outcome"] == "licensed"
    # a strongly NEGATIVE slope must not license: the prediction is one-sided
    retired = g8.verdict(g8.pooled_interaction(make_panel(a1=-0.30, seed=6)), cfg,
                         outcome_class="trading_connectivity")
    assert retired["licensed"] is False
    assert retired["outcome"] == "retired_from_headline"
    assert "not causal" in retired["note"]


# --------------------------------------------------------------------------- #
# G9 share continuity (clarification 4)                                        #
# --------------------------------------------------------------------------- #

def shares(wave, pairs, adj=1.0):
    return pd.DataFrame([{"wave": wave, "permno": p, "shares": n, "adj_factor": adj}
                         for p, n in pairs])


def test_price_drift_alone_does_not_look_like_portfolio_change():
    """The reason share continuity is required: a manager who did nothing still shows
    weight drift when constituent prices move."""
    pre_w = pd.DataFrame([{"wave": "W1", "permno": 1, "weight": .5},
                          {"wave": "W1", "permno": 2, "weight": .5}])
    post_w = pd.DataFrame([{"wave": "W1", "permno": 1, "weight": .7},   # stock 1 rallied
                           {"wave": "W1", "permno": 2, "weight": .3}])
    w = g9.wave_continuity(pre_w, post_w)
    assert w.loc[0, "turnover"] == pytest.approx(0.2)        # weights say 20% turnover
    sh = g9.share_continuity(shares("W1", [(1, 100), (2, 100)]),
                             shares("W1", [(1, 100), (2, 100)]))
    assert sh.loc[0, "share_turnover"] == pytest.approx(0.0)  # shares say none was traded
    assert sh.loc[0, "share_overlap"] == pytest.approx(1.0)


def test_a_split_is_not_turnover_once_adjusted():
    """A 2-for-1 split doubles the share count with no trade."""
    sh = g9.share_continuity(shares("W1", [(1, 100)], adj=1.0),
                             shares("W1", [(1, 200)], adj=2.0))
    assert sh.loc[0, "share_turnover"] == pytest.approx(0.0)


def test_real_selling_does_show_as_share_turnover():
    sh = g9.share_continuity(shares("W1", [(1, 100), (2, 100)]),
                             shares("W1", [(1, 100)]))
    assert sh.loc[0, "share_overlap"] == pytest.approx(0.5)
    assert sh.loc[0, "share_turnover"] > 0


def test_a_g9_summary_without_share_continuity_declares_itself_incomplete():
    pre = pd.DataFrame([{"wave": "W1", "permno": 1, "weight": 1.0}])
    s_no = g9.summarize(g9.wave_continuity(pre, pre.copy()), CONFIG)
    assert s_no["share_continuity_reported"] is False
    assert "INCOMPLETE" in s_no["incomplete"]
    s_yes = g9.summarize(g9.wave_continuity(pre, pre.copy()), CONFIG,
                         shares=g9.share_continuity(shares("W1", [(1, 10)]),
                                                    shares("W1", [(1, 10)])))
    assert s_yes["share_continuity_reported"] is True and s_yes["incomplete"] is None
