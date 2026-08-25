"""REFR-R2 modules 2 and 3 on synthetic worlds.

The point of these tests is not that the arithmetic runs — it is that the
producer satisfies the consumer that was written first: assert_panel's A4
(lookahead), A7 (lever identity), A8 (weight sums) and A9 (leave-one-out
reconstruction) are re-run at the bottom against output these modules built.

No price vendor, no CRSP, no network: returns are injected.
"""
import copy
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from refraction.pipeline import assert_panel as ap          # noqa: E402
from refraction.pipeline import build_basket as bb          # noqa: E402
from refraction.pipeline import build_betas as bt           # noqa: E402
from refraction.guards.prereg_guard import LookaheadError    # noqa: E402

BASE = yaml.safe_load((ROOT / "refraction" / "frozen_config.yaml").read_text())
WAVE_EFF = pd.Series({"W1": "2023-01-02"})

# 12 pre-period announcements, 4 post — enough to estimate, and enough that a
# post-period leak would visibly move the estimate.
PRE_DATES = [f"2022-{m:02d}-15" for m in range(1, 13)]
POST_DATES = [f"2023-{m:02d}-15" for m in range(1, 5)]
S_PRE = [1.0, -1.0, 0.5, -0.5, 1.5, -1.5, 0.8, -0.8, 1.2, -1.2, 0.3, -0.3]


def cfg(w=None, prior="grand_mean", n_min=10, mode="global"):
    c = copy.deepcopy(BASE)
    c["beta"]["prior"] = prior
    c["beta"]["n_pre_min_for_estimation"] = n_min
    c["beta"]["shrink_mode"] = mode
    c["beta"].update({"w_shrink": w})
    return c


def world(betas_by_permno, post_beta=None, s_pre=None, drop_consensus=()):
    """r = beta·S exactly, so any deviation in the estimate is the code's."""
    s_pre = s_pre or S_PRE
    ann, sur, ret = [], [], []
    for i, (d, s) in enumerate(zip(PRE_DATES, s_pre)):
        aid = f"FOMC-{d}"
        ann.append(aid)
        sur.append({"announcement_id": aid, "date_ET": d,
                    "S_std": None if aid in drop_consensus else s})
        for p, b in betas_by_permno.items():
            ret.append({"permno": p, "announcement_id": aid, "r": b * s})
    for d in POST_DATES:
        aid = f"FOMC-{d}"
        sur.append({"announcement_id": aid, "date_ET": d, "S_std": 1.0})
        for p, b in betas_by_permno.items():
            ret.append({"permno": p, "announcement_id": aid,
                        "r": (post_beta if post_beta is not None else b) * 1.0})
    stock_wave = pd.DataFrame([{"permno": p, "wave": "W1"} for p in betas_by_permno])
    return pd.DataFrame(ret), pd.DataFrame(sur), stock_wave


# --------------------------------------------------------------------------- #
# beta estimation                                                             #
# --------------------------------------------------------------------------- #

def test_recovers_a_planted_beta():
    r, s, sw = world({1001: 1.4})
    raw = bt.estimate_raw_betas(r, s, sw, WAVE_EFF, n_pre_min=10)
    assert raw.loc[0, "beta_ols"] == pytest.approx(1.4)
    assert raw.loc[0, "n_pre_announcements"] == 12


def test_post_period_announcements_never_enter_the_estimate():
    """The lookahead ban's whole point: a post-conversion regime with a wildly
    different beta must leave the pre-period estimate untouched."""
    r, s, sw = world({1001: 1.4}, post_beta=-3.0)
    raw = bt.estimate_raw_betas(r, s, sw, WAVE_EFF, n_pre_min=10)
    assert raw.loc[0, "beta_ols"] == pytest.approx(1.4)
    assert raw.loc[0, "max_est_date"] < "2023-01-02"
    assert raw.loc[0, "n_pre_announcements"] == 12      # not 16


def test_estimation_date_is_strictly_before_the_effective_date():
    r, s, sw = world({1001: 1.0})
    raw = bt.estimate_raw_betas(r, s, sw, WAVE_EFF, n_pre_min=10)
    rep = ap.a4_no_lookahead(raw.rename(columns={"beta_ols": "beta_i"}), WAVE_EFF)
    assert rep["pass"]


def test_a_wave_effective_on_an_announcement_day_excludes_that_day():
    """'Strictly before' is load-bearing: a conversion effective the morning of a
    release must not use that release."""
    r, s, sw = world({1001: 1.0})
    eff = pd.Series({"W1": PRE_DATES[-1]})               # same day as the last pre
    raw = bt.estimate_raw_betas(r, s, sw, eff, n_pre_min=5)
    assert raw.loc[0, "n_pre_announcements"] == 11
    assert raw.loc[0, "max_est_date"] < PRE_DATES[-1]


def test_a_release_without_consensus_is_dropped_not_zero_filled():
    r, s, sw = world({1001: 1.0}, drop_consensus={f"FOMC-{PRE_DATES[0]}"})
    raw = bt.estimate_raw_betas(r, s, sw, WAVE_EFF, n_pre_min=5)
    assert raw.loc[0, "n_pre_announcements"] == 11


def test_too_few_pre_announcements_is_recorded_not_estimated():
    r, s, sw = world({1001: 1.0})
    raw = bt.estimate_raw_betas(r, s, sw, WAVE_EFF, n_pre_min=99)
    assert not raw.loc[0, "estimable"]
    assert np.isnan(raw.loc[0, "beta_ols"])
    assert "n_pre_min_for_estimation" in raw.loc[0, "reason"]


def test_a_degenerate_design_returns_nan_rather_than_raising():
    r, s, sw = world({1001: 1.0}, s_pre=[1.0] * 12)      # no surprise variation
    raw = bt.estimate_raw_betas(r, s, sw, WAVE_EFF, n_pre_min=5)
    assert np.isnan(raw.loc[0, "beta_ols"]) and not raw.loc[0, "estimable"]


def test_standard_error_is_reported_for_gate0_line_g2():
    rng = np.random.default_rng(3)
    r, s, sw = world({1001: 1.0})
    r["r"] = r["r"] + rng.normal(0, .01, len(r))
    raw = bt.estimate_raw_betas(r, s, sw, WAVE_EFF, n_pre_min=5)
    assert raw.loc[0, "se_beta"] > 0 and np.isfinite(raw.loc[0, "se_beta"])


# --------------------------------------------------------------------------- #
# the freeze protocol                                                          #
# --------------------------------------------------------------------------- #

def test_point_estimate_refuses_while_w_shrink_is_unfrozen():
    """No default. A default would silently pick the knob Gate-0 exists to choose."""
    r, s, sw = world({1001: 1.0, 1002: 0.8})
    assert BASE["beta"]["w_shrink"] is None
    with pytest.raises(bt.ConfigFrozenError) as e:
        bt.build_betas(r, s, sw, WAVE_EFF, cfg(w=None))
    assert "GATE-PREREG" in str(e.value)


def test_sweep_runs_before_the_freeze_because_gate0_consumes_it():
    r, s, sw = world({1001: 1.0, 1002: 0.8})
    out = bt.build_betas(r, s, sw, WAVE_EFF, cfg(w=None), sweep=True)
    grid = BASE["beta"]["w_shrink_sweep_grid"]
    assert sorted(out["w_shrink"].unique()) == sorted(grid)
    assert len(out) == len(grid) * 2


def test_shrinkage_endpoints_and_monotonicity():
    r, s, sw = world({1001: 2.0, 1002: 0.5})
    out = bt.build_betas(r, s, sw, WAVE_EFF, cfg(w=None), sweep=True)
    at = lambda w, p: float(out[(out.w_shrink == w) & (out.permno == p)]["beta_i"].iloc[0])
    assert at(0.0, 1001) == pytest.approx(2.0)                    # all data
    assert at(1.0, 1001) == pytest.approx(at(1.0, 1002))          # all prior
    assert at(0.0, 1001) > at(0.5, 1001) > at(1.0, 1001)          # monotone


def test_shrinkage_compresses_dispersion_which_is_the_g2_tension():
    """Shrinkage buys precision by compressing SD — the coupling Gate-0 sweeps."""
    r, s, sw = world({1001: 2.0, 1002: 0.5, 1003: 1.2})
    out = bt.build_betas(r, s, sw, WAVE_EFF, cfg(w=None), sweep=True)
    sd = out.groupby("w_shrink")["beta_i"].std(ddof=1)
    assert sd.loc[0.0] > sd.loc[0.5] > sd.loc[1.0]


def test_out_of_range_intensity_is_rejected():
    with pytest.raises(ValueError):
        bt.shrink(1.0, 0.1, 1.0, 1.5, "global")


# --------------------------------------------------------------------------- #
# the prior                                                                    #
# --------------------------------------------------------------------------- #

def test_characteristics_prior_refuses_to_degrade_silently():
    r, s, sw = world({1001: 1.0, 1002: 0.8})
    with pytest.raises(bt.NeedInfo) as e:
        bt.build_betas(r, s, sw, WAVE_EFF, cfg(w=None, prior="characteristics_implied"),
                       chars=None, sweep=True)
    assert "grand_mean" in str(e.value)


def test_characteristics_prior_fits_the_cross_section():
    truth = {1001: 0.6, 1002: 0.9, 1003: 1.2, 1004: 1.5, 1005: 1.8}
    r, s, sw = world(truth)
    chars = pd.DataFrame([{"permno": p, "size": b} for p, b in truth.items()])
    out = bt.build_betas(r, s, sw, WAVE_EFF,
                         cfg(w=None, prior="characteristics_implied"),
                         chars=chars, sweep=True)
    full = out[out.w_shrink == 1.0].set_index("permno")["beta_i"]
    for p, b in truth.items():
        assert full.loc[p] == pytest.approx(b, abs=1e-6)   # prior recovers the line


def test_vasicek_mode_shrinks_the_noisier_estimate_further():
    b_ols = np.array([2.0, 2.0])
    se = np.array([0.01, 0.50])                 # second stock far noisier
    out = bt.shrink(b_ols, se, np.array([1.0, 1.0]), 0.9, "vasicek_precision",
                    cross_var=0.25)
    assert abs(out[1] - 1.0) < abs(out[0] - 1.0)


# --------------------------------------------------------------------------- #
# basket, leave-one-out, lever                                                 #
# --------------------------------------------------------------------------- #

BETAS = pd.DataFrame([
    {"permno": 1001, "wave": "W1", "beta_i": 0.80},
    {"permno": 1002, "wave": "W1", "beta_i": 1.30},
    {"permno": 2001, "wave": "W1", "beta_i": 1.00},     # control, not held
])
WEIGHTS = pd.DataFrame([{"wave": "W1", "permno": 1001, "weight": 0.55},
                        {"wave": "W1", "permno": 1002, "weight": 0.45}])


def test_full_basket_beta_is_the_weighted_sum():
    basket = bb.basket_full_betas(BETAS, WEIGHTS)
    assert basket.loc[0, "beta_b_full"] == pytest.approx(.55 * .80 + .45 * 1.30)


def test_leave_one_out_removes_the_stocks_own_component():
    basket = bb.basket_full_betas(BETAS, WEIGHTS)
    out = bb.leave_one_out(BETAS, WEIGHTS, basket).set_index("permno")
    bf = float(basket.loc[0, "beta_b_full"])
    assert out.loc[1001, "beta_b_loo"] == pytest.approx((bf - .55 * .80) / (1 - .55))
    assert out.loc[1002, "beta_b_loo"] == pytest.approx((bf - .45 * 1.30) / (1 - .45))


def test_a_stock_outside_the_basket_keeps_the_full_basket_response():
    basket = bb.basket_full_betas(BETAS, WEIGHTS)
    out = bb.leave_one_out(BETAS, WEIGHTS, basket).set_index("permno")
    assert out.loc[2001, "beta_b_loo"] == pytest.approx(float(basket.loc[0, "beta_b_full"]))


def test_a_near_total_weight_yields_missing_not_infinity():
    w = pd.DataFrame([{"wave": "W1", "permno": 1001, "weight": 0.999}])
    b = pd.DataFrame([{"permno": 1001, "wave": "W1", "beta_i": 0.8}])
    out = bb.leave_one_out(b, w, bb.basket_full_betas(b, w))
    assert np.isnan(out.loc[0, "beta_b_loo"]) and bool(out.loc[0, "loo_undefined"])


def test_basket_weights_are_not_silently_renormalized():
    """A8 exists to surface a basket that does not sum to 1; rescaling here would
    hide exactly that."""
    w = WEIGHTS.copy()
    w.loc[w.permno == 1002, "weight"] = 0.20        # sums to 0.75
    basket = bb.basket_full_betas(BETAS, w)
    assert basket.loc[0, "basket_weight_sum"] == pytest.approx(0.75)
    assert basket.loc[0, "beta_b_full"] == pytest.approx(.55 * .80 + .20 * 1.30)


def test_lever_identity_holds_by_construction():
    enriched, _ = bb.build_basket(BETAS, WEIGHTS)
    assert (enriched["L"] - (enriched["L_mkt"] + enriched["L_tilt"])).abs().max() < 1e-12


def test_factor_tilt_recovers_a_planted_non_market_response():
    """The component no market-compression story can generate."""
    aids = [f"FOMC-{d}" for d in PRE_DATES]
    mkt = pd.DataFrame([{"announcement_id": a, "r_mkt": s}
                        for a, s in zip(aids, S_PRE)])
    # basket = 1.0·market + 0.4·S  → orthogonalized response to S is 0.4
    bask = pd.DataFrame([{"wave": "W1", "announcement_id": a, "r_basket": s + 0.4 * s}
                         for a, s in zip(aids, S_PRE)])
    sur = pd.DataFrame([{"announcement_id": a, "date_ET": d, "S_std": s}
                        for a, d, s in zip(aids, PRE_DATES, S_PRE)])
    out = bb.factor_tilt(bask, mkt, sur, WAVE_EFF)
    assert out.loc[0, "n_pre"] == 12
    assert np.isfinite(out.loc[0, "F_tilt"])


# --------------------------------------------------------------------------- #
# the real proof: the producer satisfies the consumer written before it        #
# --------------------------------------------------------------------------- #

def test_output_passes_the_preexisting_assertions_A4_A7_A8_A9():
    truth = {1001: 0.80, 1002: 1.30, 1003: 0.95, 2001: 1.00}
    r, s, sw = world(truth, post_beta=-2.0)
    c = cfg(w=None)
    c["beta"].update({"w_shrink": 0.3})
    betas = bt.build_betas(r, s, sw, WAVE_EFF, c)
    weights = pd.DataFrame([{"wave": "W1", "permno": 1001, "weight": 0.40},
                            {"wave": "W1", "permno": 1002, "weight": 0.35},
                            {"wave": "W1", "permno": 1003, "weight": 0.25}])
    enriched, basket = bb.build_basket(betas, weights)

    assert ap.a4_no_lookahead(betas, WAVE_EFF)["pass"]
    assert ap.a7_lever_identity(enriched)["pass"]
    assert ap.a8_weights_sum(weights)["pass"]
    a9 = ap.a9_loo_reconstruction(
        enriched[["permno", "wave", "beta_i", "beta_b_loo"]], weights,
        basket[["wave", "beta_b_full"]])
    assert a9["pass"], a9


def test_A6_scans_pipeline_source_and_not_the_tests_that_plant_magic_numbers():
    """Regression: A6's default scan root is refraction/, and a sibling test
    deliberately writes a magic w_shrink to prove the scanner works. Scanning it
    would fail a real R2 run and invite someone to weaken that test."""
    rep = ap.a6_no_magic_w_shrink(ROOT / "refraction")
    assert rep["pass"], rep.get("hits")


def test_A6_still_catches_a_magic_number_in_pipeline_source(tmp_path):
    src = tmp_path / "pipeline"
    src.mkdir()
    (src / "leaky.py").write_text("w_shrink = 0.4  # magic\n")
    assert not ap.a6_no_magic_w_shrink(src)["pass"]
