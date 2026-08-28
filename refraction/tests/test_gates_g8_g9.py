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
    """r_resid_fwd = 0.1*CR + a1*(CR*absL) + noise."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_stocks):
        absL = float(rng.uniform(0, 1))
        for t in range(n_days):
            cr = float(rng.normal(0, 1))
            rows.append({"permno": 1000 + i, "fund": "F1",
                         "date": pd.Timestamp("2023-01-02") + pd.Timedelta(days=t),
                         "days_since_conversion": 21 + t, "CR": cr, "absL": absL,
                         "r_resid_fwd": 0.1 * cr + a1 * cr * absL + rng.normal(0, .05),
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
        g8.verdict(r, CONFIG)
    assert "specification search" in str(e.value)


def test_the_verdict_is_one_sided_on_the_linear_coefficient():
    import copy
    cfg = copy.deepcopy(CONFIG)
    cfg["gate0_thresholds"]["first_stage_primary_alpha"] = 0.05
    licensed = g8.verdict(g8.pooled_interaction(make_panel(a1=0.30, seed=5)), cfg)
    assert licensed["licensed"] is True and licensed["outcome"] == "licensed"
    # a strongly NEGATIVE slope must not license: the prediction is one-sided
    retired = g8.verdict(g8.pooled_interaction(make_panel(a1=-0.30, seed=6)), cfg)
    assert retired["licensed"] is False
    assert retired["outcome"] == "retired_from_headline"
    assert "not causal" in retired["note"]
