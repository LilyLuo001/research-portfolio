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
from refraction.gates import g8_preflight as pre    # noqa: E402

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


def make_trading_panel(n_stocks=40, n_days=120, a1=0.0, seed=0, arm="fallback"):
    """The PRIMARY outcome's data-generating process (freeze 1): the trading response scales
    with |CR| x |L|, not with signed CR x |L|. Sign, when the outcome has one, enters through
    the OUTCOME via sign(CR) x OIB — never through the exposure."""
    rng = np.random.default_rng(seed)
    absL = {1000 + i: float(rng.uniform(0, 1)) for i in range(n_stocks)}
    cr_by_day = {t: float(rng.normal(0, 1)) for t in range(n_days)}
    rows = []
    for t in range(n_days):
        cr = cr_by_day[t]
        for i in range(n_stocks):
            p = 1000 + i
            y = a1 * abs(cr) * absL[p] + rng.normal(0, .05)
            rows.append({"permno": p, "fund": "F1",
                         "date": pd.Timestamp("2023-01-02") + pd.Timedelta(days=t),
                         "days_since_conversion": 21 + t, "CR": cr, "absL": absL[p],
                         "abn_vol": y, "OIB": np.sign(cr) * y,
                         "r_resid_lag": rng.normal(0, .05), "mkt": rng.normal(0, .01)})
    df = pd.DataFrame(rows)
    df["y"] = pre.aligned_outcome(df, arm)
    return df


GOOD_G7 = {"signed_trade_classification_available_share": 0.97,
           "intraday_coverage_share_of_volume_sample": 0.99,
           "cross_algorithm_daily_oib_sign_agreement": 0.98}


def audited_config(alpha=0.05, audit_done=True):
    import copy
    cfg = copy.deepcopy(CONFIG)
    cfg["gate0_thresholds"]["first_stage_primary_alpha"] = alpha
    cfg["network_exposure"]["cr_timestamp_audit_complete"] = audit_done
    return cfg


AUDIT_RECORD = {"vendor": "CRSP", "field": "shrout", "as_of_convention": "end of day t",
                "intraday_timestamp_supplied": False, "corporate_action_adjusted": True}


def preflight(cfg, panel, arm_quality=None):
    """The three artefacts verdict() requires, in the order they must actually happen."""
    audit = pre.audit_cr_timestamp(AUDIT_RECORD, cfg)
    cfg["network_exposure"]["cr_timestamp_audit_complete"] = audit["audit_complete"]
    choice = pre.choose_primary_outcome(arm_quality or GOOD_G7, cfg)
    census = pre.cr_event_census(panel, cfg)
    return choice, audit, census


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
    cfg = audited_config()
    panel = make_panel(a1=0.30, seed=9)
    choice, audit, census = preflight(cfg, panel)
    r = g8.pooled_interaction(panel)                      # signed exposure, return outcome
    with pytest.raises(g8.SafeguardViolation) as e:
        g8.verdict(r, cfg, outcome_class="signed_price_response_not_magnitude",
                   outcome_choice=choice, timestamp_audit=audit, census=census)
    assert "primary exposure" in str(e.value) or "TRADING connectivity" in str(e.value)


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
    cfg = audited_config(alpha=None)
    panel = make_trading_panel(a1=0.3, seed=4)
    choice, audit, census = preflight(cfg, panel)
    r = g8.pooled_interaction(panel, y_col="y", exposure="abs_CR_x_absL",
                              outcome_class="trading_connectivity", config=cfg)
    assert CONFIG["gate0_thresholds"]["first_stage_primary_alpha"] is None
    with pytest.raises(g8.SafeguardViolation) as e:
        g8.verdict(r, cfg, outcome_class="trading_connectivity",
                   outcome_choice=choice, timestamp_audit=audit, census=census)
    assert "specification search" in str(e.value)


def _adjudicate(a1, seed, cfg=None):
    cfg = cfg or audited_config()
    panel = make_trading_panel(a1=a1, seed=seed)
    choice, audit, census = preflight(cfg, panel)
    r = g8.pooled_interaction(panel, y_col="y", exposure="abs_CR_x_absL",
                              outcome_class="trading_connectivity", config=cfg)
    return g8.verdict(r, cfg, outcome_class="trading_connectivity",
                      outcome_choice=choice, timestamp_audit=audit, census=census)


def test_the_verdict_is_one_sided_on_the_linear_coefficient():
    licensed = _adjudicate(0.30, 5)
    assert licensed["licensed"] is True and licensed["outcome"] == "licensed"
    # a strongly NEGATIVE slope must not license: the prediction is one-sided
    retired = _adjudicate(-0.30, 6)
    assert retired["licensed"] is False
    assert retired["outcome"] == "retired_from_headline"
    assert "not causal" in retired["note"]


# --------------------------------------------------------------------------- #
# G9 share continuity (clarification 4)                                        #
# --------------------------------------------------------------------------- #

def shares(wave, pairs, cfac=1.0, as_of="2023-01-31"):
    return pd.DataFrame([{"wave": wave, "permno": p, "shares": n, "cfacshr": cfac,
                          "as_of": as_of} for p, n in pairs])


def verified_convention(direction="divide"):
    """A probe of names with a KNOWN split and NO trading between the two dates. The
    direction is READ OFF the probe, not asserted — see verify_adjustment_convention."""
    if direction == "divide":       # 2-for-1: shares double, cfacshr doubles
        probe = pd.DataFrame([{"permno": 1, "shares_pre": 100, "cfacshr_pre": 1.0,
                               "shares_post": 200, "cfacshr_post": 2.0},
                              {"permno": 2, "shares_pre": 300, "cfacshr_pre": 1.0,
                               "shares_post": 900, "cfacshr_post": 3.0}])
    else:                           # the mirror-image encoding
        probe = pd.DataFrame([{"permno": 1, "shares_pre": 100, "cfacshr_pre": 1.0,
                               "shares_post": 200, "cfacshr_post": 0.5},
                              {"permno": 2, "shares_pre": 300, "cfacshr_pre": 1.0,
                               "shares_post": 900, "cfacshr_post": 1 / 3.0}])
    return g9.verify_adjustment_convention(probe)


CONV = verified_convention()


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
                             shares("W1", [(1, 100), (2, 100)]), CONV)
    assert sh.loc[0, "share_turnover"] == pytest.approx(0.0)  # shares say none was traded
    assert sh.loc[0, "share_overlap"] == pytest.approx(1.0)


def test_a_split_is_not_turnover_once_adjusted():
    """A 2-for-1 split doubles the share count with no trade."""
    sh = g9.share_continuity(shares("W1", [(1, 100)], cfac=1.0),
                             shares("W1", [(1, 200)], cfac=2.0), CONV)
    assert sh.loc[0, "share_turnover"] == pytest.approx(0.0)


def test_real_selling_does_show_as_share_turnover():
    sh = g9.share_continuity(shares("W1", [(1, 100), (2, 100)]),
                             shares("W1", [(1, 100)]), CONV)
    assert sh.loc[0, "share_overlap"] == pytest.approx(0.5)
    assert sh.loc[0, "share_turnover"] > 0


def test_a_g9_summary_without_share_continuity_declares_itself_incomplete():
    w = pd.DataFrame([{"wave": "W1", "permno": 1, "weight": 1.0}])
    s_no = g9.summarize(g9.wave_continuity(w, w.copy()), CONFIG)
    assert s_no["share_continuity_reported"] is False
    assert "INCOMPLETE" in s_no["incomplete"]
    sh_pre = shares("W1", [(1, 10)], as_of="2023-01-31")
    sh_post = shares("W1", [(1, 10)], as_of="2023-03-31")
    as_of = g9.check_as_of_dates(sh_pre, sh_post, {"W1": "2023-02-15"})
    s_yes = g9.summarize(g9.wave_continuity(w, w.copy()), CONFIG,
                         shares=g9.share_continuity(sh_pre, sh_post, CONV),
                         as_of=as_of, convention=CONV)
    assert s_yes["share_continuity_reported"] is True and s_yes["incomplete"] is None


# --------------------------------------------------------------------------- #
# 2026-08-28 freezes — preflight (g8_preflight)                                #
# --------------------------------------------------------------------------- #

def test_freeze1_good_data_quality_selects_the_sharper_signed_imbalance_outcome():
    cfg = audited_config()
    choice = pre.choose_primary_outcome(GOOD_G7, cfg)
    assert choice["arm"] == "preferred"
    assert choice["chosen"] == "aligned_signed_order_imbalance_on_cr_days"
    assert choice["exposure"] == "abs_CR_x_absL"
    assert not choice["failures"]
    assert "no G8 treatment coefficient" in choice["basis"]


def test_freeze1_any_single_quality_failure_selects_the_fallback():
    """All-or-nothing on purpose: a partial pass leaves room to argue afterwards about
    which criterion mattered, which is what pre-specification exists to stop."""
    for key in GOOD_G7:
        cfg = audited_config()
        bad = dict(GOOD_G7, **{key: 0.10})
        choice = pre.choose_primary_outcome(bad, cfg)
        assert choice["arm"] == "fallback", key
        assert choice["chosen"] == "constituent_abnormal_volume_on_cr_days"
        assert any(key in f for f in choice["failures"])


def test_freeze1_an_unfinished_timestamp_audit_also_forces_the_fallback():
    choice = pre.choose_primary_outcome(GOOD_G7, audited_config(audit_done=False))
    assert choice["arm"] == "fallback"
    assert any("cr_timestamp_audit_complete" in f for f in choice["failures"])


def test_freeze1_a_missing_quality_measurement_stops_rather_than_defaulting():
    """Meta-rule 4. An absent measurement is not a silent pass and not a silent fail —
    and it may not be filled in later with coefficients on the table."""
    cfg = audited_config()
    with pytest.raises(pre.SafeguardViolation) as e:
        pre.choose_primary_outcome(dict(GOOD_G7, intraday_coverage_share_of_volume_sample=None),
                                   cfg)
    assert "NEED_HUMAN" in str(e.value)


def test_freeze1_the_choice_is_made_once_and_not_re_derived():
    cfg = audited_config()
    cfg["network_exposure"]["first_stage_primary_outcome"] = "already_chosen"
    with pytest.raises(pre.SafeguardViolation) as e:
        pre.choose_primary_outcome(GOOD_G7, cfg)
    assert "made once" in str(e.value)


def test_freeze1_the_sign_enters_through_the_outcome_not_the_exposure():
    """sign(CR) x OIB is positive when constituent flow moves WITH the creation, whatever
    the direction of the creation itself."""
    df = pd.DataFrame({"CR": [2.0, -2.0], "OIB": [0.5, -0.5], "abn_vol": [1.0, 1.0]})
    assert list(pre.aligned_outcome(df, "preferred")) == [0.5, 0.5]
    assert list(pre.aligned_outcome(df, "fallback")) == [1.0, 1.0]


def test_freeze1_the_primary_refuses_the_signed_cr_exposure():
    cfg = audited_config()
    panel = make_trading_panel(a1=0.3, seed=11)
    with pytest.raises(g8.SafeguardViolation) as e:
        g8.pooled_interaction(panel, y_col="y", exposure="signed_CR_x_absL",
                              outcome_class="trading_connectivity", config=cfg)
    assert "counts the flow's sign twice" in str(e.value)


def test_freeze1_the_absolute_exposure_recovers_the_planted_trading_coefficient():
    panel = make_trading_panel(a1=0.30, seed=12)
    r = g8.pooled_interaction(panel, y_col="y", exposure="abs_CR_x_absL",
                              outcome_class="trading_connectivity")
    assert r["a1"] == pytest.approx(0.30, abs=0.05)
    assert r["exposure"] == "abs_CR_x_absL"


def test_freeze2_daily_shares_outstanding_buys_only_the_daily_claim():
    audit = pre.audit_cr_timestamp(AUDIT_RECORD, CONFIG)
    assert audit["resolution"] == "daily"
    assert audit["within_day_ordering_identified"] is False
    assert audit["g8_event_language"].endswith("creation/redemption days")
    assert "around" not in audit["g8_event_language"]


def test_freeze2_a_vendor_supplied_event_time_buys_the_stronger_wording():
    audit = pre.audit_cr_timestamp(dict(AUDIT_RECORD, intraday_timestamp_supplied=True), CONFIG)
    assert audit["resolution"] == "intraday"
    assert "around" in audit["g8_event_language"]
    assert audit["within_day_ordering_identified"] is True


def test_freeze2_a_timestamp_inferred_from_daily_differences_is_refused():
    """Daily Delta(SharesOut) is a difference of two end-of-day stocks. It says a creation
    happened inside the day; it cannot say when."""
    with pytest.raises(pre.SafeguardViolation) as e:
        pre.audit_cr_timestamp(dict(AUDIT_RECORD, intraday_timestamp_supplied=True,
                                    inferred_from_daily_differences=True), CONFIG)
    assert "cannot identify a within-day event time" in str(e.value)


def test_freeze2_an_incomplete_audit_stops_instead_of_assuming_a_convention():
    with pytest.raises(pre.SafeguardViolation) as e:
        pre.audit_cr_timestamp(dict(AUDIT_RECORD, as_of_convention=None), CONFIG)
    assert "NEED_HUMAN" in str(e.value)


def test_freeze2_unaudited_reporting_defaults_to_the_weaker_daily_claim():
    assert pre.event_language(None, CONFIG).endswith("creation/redemption days")


def test_freeze3_realized_basket_weight_is_refused_in_the_baseline():
    cfg = audited_config()
    panel = make_trading_panel(a1=0.3, seed=13)
    panel["realized_creation_basket_weight"] = 0.01
    with pytest.raises(g8.SafeguardViolation) as e:
        g8.pooled_interaction(panel, y_col="y", exposure="abs_CR_x_absL",
                              outcome_class="trading_connectivity", config=cfg,
                              z_controls=("realized_creation_basket_weight",))
    assert "changes the estimand" in str(e.value)


def test_freeze3_the_horse_race_runs_only_under_its_own_declared_estimand():
    cfg = audited_config()
    panel = make_trading_panel(a1=0.3, seed=14)
    panel["realized_creation_basket_weight"] = np.linspace(0, .02, len(panel))
    r = g8.pooled_interaction(panel, y_col="y", exposure="abs_CR_x_absL",
                              outcome_class="trading_connectivity", config=cfg,
                              z_controls=("realized_creation_basket_weight",),
                              estimand="incremental_given_realized_basket")
    assert r["estimand"] == "incremental_given_realized_basket"
    assert "realized_creation_basket_weight" in r["cr_interacted_controls"]


def test_freeze3_predetermined_controls_pass_the_baseline_unchallenged():
    cfg = audited_config()
    panel = make_trading_panel(a1=0.3, seed=15)
    panel["pre_conversion_holding_weight"] = np.linspace(0, .02, len(panel))
    r = g8.pooled_interaction(panel, y_col="y", exposure="abs_CR_x_absL",
                              outcome_class="trading_connectivity", config=cfg,
                              z_controls=("pre_conversion_holding_weight",))
    assert r["estimand"] == "baseline"


def test_freeze4_the_census_counts_events_not_constituent_day_rows():
    """40 stocks x 120 days is 4800 rows off 120 fund-days. If only 3 of those days carry a
    nonzero creation/redemption, the mechanism has 3 events in it, not 4800."""
    panel = make_trading_panel(n_stocks=40, n_days=120, a1=0.3, seed=16)
    live = set(sorted(panel["date"].unique())[:3])
    panel["CR"] = np.where(panel["date"].isin(live), panel["CR"], 0.0)
    c = pre.cr_event_census(panel, CONFIG)
    assert c["n_constituent_day_rows"] == 4800
    assert c["n_fund_days"] == 120
    assert c["n_nonzero_cr_days"] == 3
    assert c["rows_per_event"] == pytest.approx(1600.0)
    assert c["concentration_top1_share"] == pytest.approx(1.0)   # one fund carries all of it


def test_freeze4_the_census_registers_no_minimum_to_pass():
    panel = make_trading_panel(n_stocks=4, n_days=10, seed=17)
    c = pre.cr_event_census(panel, CONFIG)
    assert "no minimum is registered" in c["reporting_only"]
    assert not any(k.endswith("_min") or k.endswith("_max") for k in c)


def test_freeze4_the_census_breaks_out_by_fund_wave_and_adviser():
    panel = make_trading_panel(n_stocks=3, n_days=8, seed=18)
    panel["wave"] = "W1"
    panel["adviser"] = "ADV-A"
    c = pre.cr_event_census(panel, CONFIG)
    for key in CONFIG["network_exposure"]["cr_event_census_by"]:
        assert c["by_" + key] is not None
        assert "n_nonzero_cr_days" in c["by_" + key].columns


def test_the_verdict_refuses_without_each_preflight_artefact():
    """The ordering is enforced by code, not by discipline: all three must exist before a
    treatment coefficient can be adjudicated."""
    cfg = audited_config()
    panel = make_trading_panel(a1=0.30, seed=19)
    choice, audit, census = preflight(cfg, panel)
    r = g8.pooled_interaction(panel, y_col="y", exposure="abs_CR_x_absL",
                              outcome_class="trading_connectivity", config=cfg)
    kw = dict(outcome_class="trading_connectivity", outcome_choice=choice,
              timestamp_audit=audit, census=census)
    for drop, needle in (("outcome_choice", "no registered primary outcome"),
                         ("timestamp_audit", "timestamp audit is not complete"),
                         ("census", "CR event census is required")):
        with pytest.raises(g8.SafeguardViolation) as e:
            g8.verdict(r, cfg, **dict(kw, **{drop: None}))
        assert needle in str(e.value)


def test_the_verdict_refuses_a_sample_with_no_creation_or_redemption_at_all():
    cfg = audited_config()
    panel = make_trading_panel(a1=0.30, seed=20)
    r = g8.pooled_interaction(panel, y_col="y", exposure="abs_CR_x_absL",
                              outcome_class="trading_connectivity", config=cfg)
    choice, audit, _ = preflight(cfg, panel)
    dead = pre.cr_event_census(panel.assign(CR=0.0), CONFIG)
    with pytest.raises(g8.SafeguardViolation) as e:
        g8.verdict(r, cfg, outcome_class="trading_connectivity", outcome_choice=choice,
                   timestamp_audit=audit, census=dead)
    assert "no mechanism variation" in str(e.value)


def test_the_licensed_verdict_carries_its_wording_and_its_event_count():
    v = _adjudicate(0.30, 21)
    assert v["licensed"] is True
    assert v["event_language"].endswith("creation/redemption days")
    assert v["within_day_ordering_identified"] is False
    assert v["n_nonzero_cr_days"] > 0
    assert v["estimand"] == "baseline"


# --------------------------------------------------------------------------- #
# G9 — verified adjustment convention and as-of dates (2026-08-28)             #
# --------------------------------------------------------------------------- #

def test_the_adjustment_direction_is_read_off_a_probe_not_asserted():
    """Both CRSP encodings are plausible from memory; only the probe settles it."""
    assert verified_convention("divide")["direction"] == "divide"
    assert verified_convention("multiply")["direction"] == "multiply"


def test_an_ambiguous_probe_refuses_to_name_a_direction():
    """No corporate action in the probe means both directions score identically — that is
    not evidence for either, so it stops."""
    flat = pd.DataFrame([{"permno": 1, "shares_pre": 100, "cfacshr_pre": 1.0,
                          "shares_post": 100, "cfacshr_post": 1.0}])
    v = g9.verify_adjustment_convention(flat)
    assert v["status"] == "UNVERIFIED" and v["direction"] is None
    assert "NEED_HUMAN" in v["reason"]


def test_share_continuity_refuses_an_unverified_convention():
    with pytest.raises(ValueError) as e:
        g9.share_continuity(shares("W1", [(1, 100)]), shares("W1", [(1, 200)]),
                            g9.CORPORATE_ACTION_CONVENTION)
    assert "NEED_HUMAN" in str(e.value)


def test_the_module_level_convention_ships_unverified_like_p1s_schema():
    assert g9.CORPORATE_ACTION_CONVENTION["status"] == "UNVERIFIED"
    assert g9.CORPORATE_ACTION_CONVENTION["field"] == "cfacshr"
    assert g9.CORPORATE_ACTION_CONVENTION["holdings_as_of_field"] == "report_dt"


def test_as_of_dates_are_reported_and_the_pre_snapshot_must_predate_the_wave():
    """P1's rule, reused: the pre-conversion report date is strictly before the effective
    date. The gap is reported because a six-month-stale snapshot makes 'only the wrapper
    changed' a much weaker statement than a one-month-stale one."""
    a = g9.check_as_of_dates(shares("W1", [(1, 10)], as_of="2023-01-31"),
                             shares("W1", [(1, 10)], as_of="2023-03-31"),
                             {"W1": "2023-02-15"})
    assert bool(a.loc[0, "pre_strictly_before_effective"]) is True
    assert bool(a.loc[0, "post_on_or_after_effective"]) is True
    assert a.loc[0, "pre_gap_days"] == 15

    late = g9.check_as_of_dates(shares("W1", [(1, 10)], as_of="2023-03-01"),
                                shares("W1", [(1, 10)], as_of="2023-03-31"),
                                {"W1": "2023-02-15"})
    assert bool(late.loc[0, "pre_strictly_before_effective"]) is False


def test_a_g9_summary_names_which_piece_is_missing():
    w = pd.DataFrame([{"wave": "W1", "permno": 1, "weight": 1.0}])
    cont = g9.wave_continuity(w, w.copy())
    s = g9.summarize(cont, CONFIG, shares=g9.share_continuity(
        shares("W1", [(1, 10)]), shares("W1", [(1, 10)]), CONV), convention=CONV)
    assert "as-of dates are not reported" in s["incomplete"]
    assert s["adjustment_convention"] == "VERIFIED"
