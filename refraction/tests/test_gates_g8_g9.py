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


def _cfg_no_std():
    """The registered formula with standardization switched off, so the raw growth rate is
    visible. Standardization is tested separately."""
    import copy
    cfg = copy.deepcopy(CONFIG)
    cfg["network_exposure"]["cr_definition"]["standardize_within_fund"] = False
    cfg["network_exposure"]["cr_definition"]["winsorize_pct"] = [0, 100]
    return cfg


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


def test_a_sample_with_no_creation_or_redemption_is_uninformative_not_a_failure():
    """Freeze 6: low power is not mechanism failure. A dead sample returns
    INSUFFICIENT_IDENTIFYING_VARIATION — the measure is untested, not retired."""
    cfg = audited_config()
    panel = make_trading_panel(a1=0.30, seed=20)
    r = g8.pooled_interaction(panel, y_col="y", exposure="abs_CR_x_absL",
                              outcome_class="trading_connectivity", config=cfg)
    choice, audit, _ = preflight(cfg, panel)
    dead = pre.cr_event_census(panel.assign(CR=0.0), CONFIG)
    v = g8.verdict(r, cfg, outcome_class="trading_connectivity", outcome_choice=choice,
                   timestamp_audit=audit, census=dead)
    assert v["outcome"] == "INSUFFICIENT_IDENTIFYING_VARIATION"
    assert v["licensed"] is None                 # neither licensed NOR retired
    assert any("nonzero creation/redemption" in r_ for r_ in v["reasons"])
    # audit item 3: the classification does NOT replace inference
    assert v["p_one_sided"] is not None and v["ci_low"] is not None
    assert v["mde_sigma"] is not None


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


# --------------------------------------------------------------------------- #
# freeze 5 — the outcome's unit                                                #
# --------------------------------------------------------------------------- #

def liquidity_panel(n=200, seed=0, size_spread=1000.0, noise=0.0, frac=0.02):
    """A panel where |L| is CORRELATED WITH SIZE and there is NO arbitrage channel at all.
    Each stock's imbalance is a constant fraction of its OWN liquidity, so the true
    normalized relation is exactly zero. Raw dollar imbalance is proportional to size, so a
    raw outcome manufactures a1 > 0 from the size distribution alone.

    `noise=0` gives a DETERMINISTIC fixture, where "the relation was removed" means the
    recovered coefficient is zero to numerical precision — not merely insignificant.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        size = 1.0 + size_spread * rng.random()      # dollar ADV
        absl = 0.1 + 0.8 * (size / (1.0 + size_spread))   # big names sit closer to basket
        for t in range(6):
            cr = float(rng.normal(0, 1))
            f = frac + (rng.normal(0, noise) if noise else 0.0)
            rows.append({"permno": 1000 + i, "fund": "F1",
                         "date": pd.Timestamp("2023-01-02") + pd.Timedelta(days=t),
                         "CR": cr, "absL": absl, "adv_dollar_pre": size,
                         "signed_dollar_imbalance": np.sign(cr) * f * size,
                         "dollar_volume": size * (1 + f)})
    return pd.DataFrame(rows)


def _fit(df, ycol):
    return g8.pooled_interaction(df, controls=(), y_col=ycol, exposure="abs_CR_x_absL",
                                 outcome_class="trading_connectivity")


def test_freeze5_a_raw_dollar_outcome_manufactures_the_result_from_size_alone():
    """Documents WHY the unit is frozen. DETERMINISTIC fixture: the true normalized relation
    is exactly zero, yet the RAW outcome recovers a large POSITIVE coefficient — the size
    artefact, in the coefficient itself and not merely in a t-statistic."""
    df = liquidity_panel(seed=31, noise=0.0)
    df["y_raw"] = np.sign(df["CR"]) * df["signed_dollar_imbalance"]
    raw = _fit(df, "y_raw")
    # the artefact is a real effect on the raw scale: a1 is a sizeable positive number
    assert raw["a1"] > 0.5 * df["adv_dollar_pre"].mean() * 0.02 * 0.1, raw["a1"]
    assert raw["a1"] / raw["within_fund_date_exposure_sd"] > 1.0


def test_freeze5_the_registered_unit_recovers_exactly_zero_on_a_deterministic_fixture():
    """|t| < 3 would only say "not significant". With no noise in the fixture the planted
    relation is exactly zero, so the recovered coefficient must be zero to numerical
    precision — a far stronger statement, and the one actually being claimed."""
    df = liquidity_panel(seed=31, noise=0.0)
    df["y"] = pre.aligned_outcome(df, "preferred", CONFIG)
    norm = _fit(df, "y")
    # y is identically 0.02 for every row, so the within-fund-date demeaned outcome is 0
    assert abs(norm["a1"]) < 1e-9, norm["a1"]
    assert norm["sd_outcome"] < 1e-9


def test_freeze5_the_registered_unit_holds_its_nominal_size_under_simulation():
    """The stochastic counterpart: repeat the null design and check the REJECTION RATE
    against the nominal level, rather than eyeballing one t-statistic against an arbitrary
    cutoff. Under a true null a correctly-sized one-sided 5% test rejects ~5% of the time.

    The comparison that matters is against the raw outcome on the SAME draws, which rejects
    essentially always — the artefact is not subtle, and a size-controlled test is exactly
    what removing it looks like."""
    from math import erf, sqrt
    reps, alpha = 200, 0.05
    rej_norm = rej_raw = 0
    for k in range(reps):
        df = liquidity_panel(n=40, seed=1000 + k, noise=0.004)
        df["y"] = pre.aligned_outcome(df, "preferred", CONFIG)
        df["y_raw"] = np.sign(df["CR"]) * df["signed_dollar_imbalance"]
        for col, hit in (("y", "norm"), ("y_raw", "raw")):
            t = _fit(df, col)["t_a1"]
            if 0.5 * (1 - erf(t / sqrt(2))) <= alpha:      # one-sided, H1: a1 > 0
                if hit == "norm":
                    rej_norm += 1
                else:
                    rej_raw += 1
    rate = rej_norm / reps
    # 99% binomial band for 200 draws at p=0.05 is roughly [0.01, 0.11]
    assert 0.01 <= rate <= 0.11, "normalized outcome size = %.3f (expected ~%.2f)" % (rate, alpha)
    assert rej_raw / reps > 0.90, "the raw outcome should reject almost always"


def test_freeze5_the_registered_unit_still_detects_a_real_relation():
    """Size control is worthless if it also removes true signal. Plant a genuine
    connectivity effect in the NORMALIZED outcome and check it is recovered."""
    df = liquidity_panel(n=60, seed=77, noise=0.004)
    df["y"] = pre.aligned_outcome(df, "preferred", CONFIG)
    df["y"] = df["y"] + 0.05 * np.abs(df["CR"]) * df["absL"]
    fit = _fit(df, "y")
    assert fit["a1"] == pytest.approx(0.05, abs=0.02)
    assert fit["t_a1"] > 3


def test_freeze5_the_outcome_refuses_to_build_without_the_predetermined_denominator():
    df = liquidity_panel(seed=32).drop(columns=["adv_dollar_pre"])
    with pytest.raises(pre.SafeguardViolation) as e:
        pre.aligned_outcome(df, "preferred", CONFIG)
    assert "predetermined ADV$" in str(e.value)


def test_freeze5_a_zero_or_missing_denominator_drops_rather_than_floors():
    df = liquidity_panel(seed=33)
    df.loc[df.index[:5], "adv_dollar_pre"] = 0.0
    with pytest.raises(pre.SafeguardViolation) as e:
        pre.aligned_outcome(df, "preferred", CONFIG)
    assert "never floor them" in str(e.value)


def test_freeze5_both_arms_share_the_same_denominator():
    """If the arms used different denominators, a switch between them would change the
    unit as well as the outcome."""
    n = CONFIG["network_exposure"]["first_stage_outcome_normalization"]
    assert n["denominator"] == "adv_dollar_pre"
    for arm in ("preferred", "fallback"):
        expr = CONFIG["network_exposure"]["first_stage_primary_candidates"][arm][
            "outcome_expression"]
        assert "ADV_pre_i" in expr, arm


def test_freeze5_the_adv_window_is_entirely_pre_conversion():
    """A contemporaneous denominator is moved by the very trading being measured; a
    post-conversion one is post-treatment besides."""
    n = CONFIG["network_exposure"]["first_stage_outcome_normalization"]
    lo, hi = n["adv_window_trading_days"]
    assert lo < hi < 0, "the ADV window must close strictly before the conversion"
    assert n["adv_statistic"] == "median"
    assert n["adv_min_nonzero_days"] > 0


def test_freeze5_predetermined_adv_uses_only_pre_conversion_days():
    daily = pd.DataFrame([{"permno": 1, "date": pd.Timestamp("2023-01-01") + pd.Timedelta(days=d),
                           "dollar_volume": 100.0 if d < 300 else 9e9} for d in range(400)])
    adv = pre.predetermined_adv(daily, {1: pd.Timestamp("2023-01-01") + pd.Timedelta(days=300)},
                                CONFIG)
    assert adv.loc[0, "adv_dollar_pre"] == pytest.approx(100.0)   # the 9e9 spike is post
    assert bool(adv.loc[0, "usable"]) is True


def test_freeze5_a_stock_with_too_few_pre_days_is_marked_unusable():
    daily = pd.DataFrame([{"permno": 1, "date": pd.Timestamp("2023-01-01") + pd.Timedelta(days=d),
                           "dollar_volume": 100.0} for d in range(30)])
    adv = pre.predetermined_adv(daily, {1: pd.Timestamp("2023-06-01")}, CONFIG)
    assert bool(adv.loc[0, "usable"]) is False


# --------------------------------------------------------------------------- #
# CR — the one definition (reconciliation audit)                               #
# --------------------------------------------------------------------------- #

def shares_frame(counts, fund="F1", start="2023-01-02", cfac=None, freq="D"):
    return pd.DataFrame({"fund": fund,
                         "date": pd.date_range(start, periods=len(counts), freq=freq),
                         "shares_outstanding": [float(c) for c in counts],
                         "cfacshr": cfac or [1.0] * len(counts)})


def test_cr_is_the_share_growth_rate_the_plan_froze():
    """CR_{f,t} = (S_t - S_{t-1}) / S_{t-1}: no price, no NAV, denominator at t-1."""
    raw = pre.build_cr(shares_frame([100, 110, 99]), _cfg_no_std(), CONV)
    assert np.isnan(raw.loc[0, "CR"])                       # no prior day
    assert raw.loc[1, "CR"] == pytest.approx(0.10)          # +10% creation
    assert raw.loc[2, "CR"] == pytest.approx(-0.10)         # -10% redemption


def test_cr_sign_is_positive_for_a_creation():
    cr = pre.build_cr(shares_frame([100, 120]), _cfg_no_std(), CONV)["CR"]
    assert cr.iloc[1] > 0


def test_cr_denominator_is_the_prior_day_not_the_current_one():
    """100 -> 200 is +100% on a t-1 base and +50% on a t base. The distinction is the whole
    content of 'denominator timing'."""
    cr = pre.build_cr(shares_frame([100, 200]), _cfg_no_std(), CONV)["CR"]
    assert cr.iloc[1] == pytest.approx(1.0)
    assert cr.iloc[1] != pytest.approx(0.5)


def test_cr_uses_no_price_or_nav_anywhere():
    """The deleted TNA form differs from this one by the fund's own NAV return. Doubling
    every price must leave CR untouched."""
    import inspect
    src = inspect.getsource(pre.build_cr)
    for token in ("nav", "price", "tna"):
        assert token not in src.lower().split("\"\"\"")[2].lower(), token
    base = pre.build_cr(shares_frame([100, 110]), _cfg_no_std(), CONV)["CR"].iloc[1]
    assert base == pytest.approx(0.10)


def test_cr_is_undefined_across_a_missing_trading_day():
    """A two-day share difference over a one-day base is a different variable with the same
    name, so a gap leaves CR undefined rather than spanning it."""
    f = shares_frame([100, 110, 120])
    f = f.drop(index=1).reset_index(drop=True)     # the middle day is missing
    cr = pre.build_cr(f, _cfg_no_std(), CONV)["CR"]
    assert np.isnan(cr.iloc[0])
    # the surviving row still differences against its own previous OBSERVED day, and the
    # config records that convention explicitly
    assert CONFIG["network_exposure"]["cr_definition"]["undefined_on_missing_prior_day"] is True


def test_cr_requires_corporate_action_adjusted_shares():
    """A 2-for-1 split doubles S with no creation; unadjusted it reads as a 100% creation."""
    with pytest.raises(pre.SafeguardViolation) as e:
        pre.build_cr(shares_frame([100, 200]).drop(columns=["cfacshr"]), _cfg_no_std(), CONV)
    assert "no creation" in str(e.value)
    split = pre.build_cr(shares_frame([100, 200], cfac=[1.0, 2.0]), _cfg_no_std(), CONV)
    assert split["CR"].iloc[1] == pytest.approx(0.0)


def test_cr_is_standardized_within_fund_and_not_rescaled_again():
    d = CONFIG["network_exposure"]["cr_definition"]
    assert d["standardize_within_fund"] is True
    assert d["further_rescaling_forbidden"] is True
    out = pre.build_cr(shares_frame([100, 110, 99, 105, 100]), CONFIG, CONV)
    assert out["CR"].dropna().std(ddof=0) == pytest.approx(1.0)


def test_a_tna_or_dollar_scaled_cr_is_refused():
    """The deleted form must not be able to re-enter through a side door."""
    df = pd.DataFrame({"CR": [0.1, -0.1], "tna_lag": [1e9, 1e9]})
    with pytest.raises(pre.SafeguardViolation) as e:
        pre.assert_cr_definition(df, CONFIG)
    assert "different variable" in str(e.value)
    pre.assert_cr_definition(pd.DataFrame({"CR": [0.1], "absL": [0.5]}), CONFIG)


def test_no_file_carries_a_second_cr_definition():
    """The audit's actual claim: one formula, everywhere. Scans config, code, memo and
    tests for the deleted TNA/dollar-scaled forms."""
    import re
    banned = re.compile(r"CR\s*/\s*TNA|cr_over_tna|fraction_of_fund_net_assets"
                        r"|dollar_CR\s*/|delta_shares_times_nav")
    roots = [ROOT / "refraction", ROOT / "docs" / "MacroEvent_Chapter_Plan_v2_4.md"]
    offenders = []
    for root in roots:
        files = sorted(root.rglob("*")) if root.is_dir() else [root]
        for f in files:
            if f.suffix not in (".py", ".yaml", ".md") or not f.is_file():
                continue
            if f.name == Path(__file__).name:      # the scanner names them to ban them
                continue
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                stripped = line.strip()
                # prose ABOUT the deleted form is the audit trail; only live settings count
                if stripped.startswith("#") or stripped.startswith("*"):
                    continue
                if banned.search(line) and "forbidden" not in line.lower() \
                        and "may_not" not in line and "deleted" not in line.lower():
                    offenders.append("%s:%d: %s" % (f.relative_to(ROOT), i, stripped))
    assert not offenders, "a second CR definition is live:\n" + "\n".join(offenders)


def test_freeze5_size_is_defended_twice_and_neither_substitutes():
    ne = CONFIG["network_exposure"]
    assert set(ne["first_stage_size_defence"]) == {"outcome_normalization",
                                                   "cr_interacted_size_control"}
    assert "size" in ne["first_stage_cr_interacted_controls"]


# --------------------------------------------------------------------------- #
# freeze 6 — INSUFFICIENT_IDENTIFYING_VARIATION                                #
# --------------------------------------------------------------------------- #

def test_freeze6_a_single_event_is_uninformative_not_a_rejection():
    cfg = audited_config()
    panel = make_trading_panel(a1=0.30, seed=40)
    one_day = sorted(panel["date"].unique())[0]
    panel["CR"] = np.where(panel["date"] == one_day, panel["CR"], 0.0)
    r = g8.pooled_interaction(panel, y_col="y", exposure="abs_CR_x_absL",
                              outcome_class="trading_connectivity", config=cfg)
    choice, audit, _ = preflight(cfg, panel)
    v = g8.verdict(r, cfg, outcome_class="trading_connectivity", outcome_choice=choice,
                   timestamp_audit=audit, census=pre.cr_event_census(panel, CONFIG))
    assert v["outcome"] == "INSUFFICIENT_IDENTIFYING_VARIATION"
    assert v["licensed"] is None
    assert "UNTESTED" in v["note"]


def test_freeze6_a_degenerate_exposure_is_uninformative():
    """If |L| does not vary across constituents of the same ETF-day, the interaction is
    collinear with the fixed effects and a1 is not identified at all."""
    cfg = audited_config()
    panel = make_trading_panel(a1=0.30, seed=41)
    panel["absL"] = 0.5                          # every constituent identical
    r = g8.pooled_interaction(panel, y_col="y", exposure="abs_CR_x_absL",
                              outcome_class="trading_connectivity", config=cfg)
    choice, audit, census = preflight(cfg, panel)
    v = g8.verdict(r, cfg, outcome_class="trading_connectivity", outcome_choice=choice,
                   timestamp_audit=audit, census=census)
    assert v["outcome"] == "INSUFFICIENT_IDENTIFYING_VARIATION"
    assert any("within-fund-date variation" in x for x in v["reasons"])


def test_freeze6_the_withdrawn_mde_line_is_not_inherited_from_the_headline_gamma():
    """Audit item 4. Plan v2.1 §9's 0.5-sigma line is the HEADLINE gamma power bar — a
    different outcome, sample and clustering. It may not be transplanted to a
    constituent-trading coefficient, and the code must not fire on it."""
    ne = CONFIG["network_exposure"]
    rules = ne["first_stage_insufficient_variation_rules"]
    assert rules["mde_sigma_max"] is None
    assert rules["mde_sigma_max"] != CONFIG["gate0_thresholds"]["mde_sigma_max"]
    assert rules["mde_sigma_max_may_not_inherit_from"] == "gate0_thresholds.mde_sigma_max"
    assert ne["first_stage_power_trigger_active"] is False
    assert ne["insufficient_variation_is_not_mechanism_failure"] is True


def test_freeze6_a_noisy_sample_reports_a_large_mde_without_being_reclassified():
    """Audit items 3 and 4. A tiny, noisy design has a huge MDE — and that is REPORTED, not
    used to reclassify: no G8-specific power floor is registered, so the power trigger is
    inert. The reader is given the MDE and the CI and draws the conclusion."""
    cfg = audited_config()
    panel = make_trading_panel(n_stocks=6, n_days=4, a1=0.0, seed=42)
    panel["y"] = panel["y"] + np.random.default_rng(1).normal(0, 5, len(panel))
    r = g8.pooled_interaction(panel, y_col="y", exposure="abs_CR_x_absL",
                              outcome_class="trading_connectivity", config=cfg)
    choice, audit, census = preflight(cfg, panel)
    v = g8.verdict(r, cfg, outcome_class="trading_connectivity", outcome_choice=choice,
                   timestamp_audit=audit, census=census)
    assert v["power_trigger_active"] is False
    assert v["mde_sigma"] is not None and v["mde_sigma"] > 0.5
    assert not any("MDE" in x for x in v["reasons"])
    assert v["outcome"] in ("licensed", "retired_from_headline")


def test_freeze6_the_classification_never_replaces_inference():
    """Audit item 3: every G8 verdict carries the coefficient, its interval, the MDE, the
    event counts, the concentration and the effective cluster counts — INSUFFICIENT included."""
    cfg = audited_config()
    panel = make_trading_panel(a1=0.30, seed=45)
    panel["adviser"] = "ADV-A"
    one_day = sorted(panel["date"].unique())[0]
    panel["CR"] = np.where(panel["date"] == one_day, panel["CR"], 0.0)
    r = g8.pooled_interaction(panel, y_col="y", exposure="abs_CR_x_absL",
                              outcome_class="trading_connectivity", config=cfg)
    choice, audit, census = preflight(cfg, panel)
    insufficient = g8.verdict(r, cfg, outcome_class="trading_connectivity",
                              outcome_choice=choice, timestamp_audit=audit, census=census)
    assert insufficient["outcome"] == "INSUFFICIENT_IDENTIFYING_VARIATION"
    assert insufficient["classification_basis"] == "numerical degeneracy"
    licensed = _adjudicate(0.30, 46)
    for key in CONFIG["network_exposure"]["first_stage_report_always"]:
        for v in (insufficient, licensed):
            assert key in v, "%s missing from a %s verdict" % (key, v["outcome"])
    assert insufficient["ci_low"] < insufficient["a1"] < insufficient["ci_high"]
    assert insufficient["n_effective_fund_clusters"] == 1
    assert insufficient["n_effective_adviser_clusters"] == 1
    assert insufficient["n_effective_event_clusters"] == 1


def test_two_events_is_not_a_sufficiency_claim():
    """The degeneracy check is arithmetic, not a bar that certifies adequacy. A sample that
    merely CLEARS it is still reported with its CI and MDE, and is not declared adequate."""
    rules = CONFIG["network_exposure"]["first_stage_insufficient_variation_rules"]
    assert rules["min_nonzero_cr_days"] == 2
    cfg = audited_config()
    panel = make_trading_panel(a1=0.30, seed=47)
    live = set(sorted(panel["date"].unique())[:2])       # exactly 2 events: clears the check
    panel["CR"] = np.where(panel["date"].isin(live), panel["CR"], 0.0)
    r = g8.pooled_interaction(panel, y_col="y", exposure="abs_CR_x_absL",
                              outcome_class="trading_connectivity", config=cfg)
    choice, audit, census = preflight(cfg, panel)
    v = g8.verdict(r, cfg, outcome_class="trading_connectivity", outcome_choice=choice,
                   timestamp_audit=audit, census=census)
    assert v["outcome"] != "INSUFFICIENT_IDENTIFYING_VARIATION"   # cleared the arithmetic
    assert v["n_effective_event_clusters"] == 2                   # and the report says so
    assert v["mde_sigma"] is not None and v["ci_low"] is not None
    assert "adequate" not in str(v).lower()


def test_freeze6_a_well_powered_null_still_retires_the_measure():
    """The escape hatch must not swallow genuine rejections: with real power, a null is a
    finding and the measure is retired."""
    v = _adjudicate(-0.30, 43)
    assert v["outcome"] == "retired_from_headline"
    assert v["mde_sigma"] is not None and v["mde_sigma"] <= 0.5


def test_freeze6_the_power_branch_is_taken_before_the_p_value_is_read():
    """MDE is built from the SE and the outcome SD — properties of the design, not of a1 —
    so the coefficient's size can never steer which branch is taken."""
    import inspect
    src = inspect.getsource(g8.verdict)
    assert src.index("identifying_variation(") < src.index("licensed = bool(")
    ident = inspect.getsource(g8.identifying_variation)
    assert '"a1"' not in ident and "result['a1']" not in ident


def test_freeze6_a_licensed_verdict_reports_its_mde():
    v = _adjudicate(0.30, 44)
    assert v["outcome"] == "licensed" and v["mde_sigma"] is not None


def test_freeze6_all_three_outcomes_are_registered():
    assert set(CONFIG["network_exposure"]["first_stage_outcomes"]) == {
        "licensed", "retired_from_headline", "INSUFFICIENT_IDENTIFYING_VARIATION"}


# --------------------------------------------------------------------------- #
# G9 — one convention shared with P1, and as-of placement                      #
# --------------------------------------------------------------------------- #

def test_g9_and_p1_run_the_same_adjustment_code_not_two_copies():
    """Integration: documentation fixes the semantics, this fixes the implementation."""
    import sys as _sys
    _sys.path.insert(0, str(ROOT / "p1" / "t2_wrds"))
    import corpactions as ca
    assert g9.verify_adjustment_convention.__module__ == g9.__name__
    assert g9.ca is ca                                    # the same module object
    assert g9.CORPORATE_ACTION_CONVENTION["owned_by"] == "p1/t2_wrds/corpactions.py"
    assert g9.CORPORATE_ACTION_CONVENTION["field"] == ca.CORPACTION_SCHEMA["share_factor"]
    # and the same numbers, not merely the same names
    p = pd.DataFrame([{"shares_pre": 100, "cfacshr_pre": 1.0,
                       "shares_post": 200, "cfacshr_post": 2.0}])
    assert g9.verify_adjustment_convention(p) == ca.verify_direction(p)


def test_g9_refuses_filing_dates_where_as_of_dates_belong():
    a = shares("W1", [(1, 10)], as_of="2023-01-31").assign(filing_date="2023-04-30")
    b = shares("W1", [(1, 10)], as_of="2023-03-31")
    with pytest.raises(Exception) as e:
        g9.check_as_of_dates(a, b, {"W1": "2023-02-15"})
    assert "FILING date" in str(e.value)


def test_g9_confirms_pre_holdings_precede_and_post_holdings_follow_the_conversion():
    a = g9.check_as_of_dates(shares("W1", [(1, 10)], as_of="2023-01-31"),
                             shares("W1", [(1, 10)], as_of="2023-03-31"),
                             {"W1": "2023-02-15"})
    assert a.loc[0, "pre_side"] == "pre" and a.loc[0, "post_side"] == "post"
    assert bool(a.loc[0, "as_of_ok"]) is True
    assert a.loc[0, "as_of_field"] == "report_dt"


def test_g9_picks_the_tightest_snapshot_pair_around_the_conversion():
    """The latest pre snapshot and the earliest post one — so the comparison is about the
    wrapper rather than months of unrelated drift."""
    pre_h = pd.concat([shares("W1", [(1, 10)], as_of="2022-06-30"),
                       shares("W1", [(1, 10)], as_of="2023-01-31")])
    post_h = pd.concat([shares("W1", [(1, 10)], as_of="2023-03-31"),
                        shares("W1", [(1, 10)], as_of="2023-12-31")])
    a = g9.check_as_of_dates(pre_h, post_h, {"W1": "2023-02-15"})
    assert a.loc[0, "pre_as_of"] == pd.Timestamp("2023-01-31")
    assert a.loc[0, "post_as_of"] == pd.Timestamp("2023-03-31")


def test_g9_flags_a_wave_whose_snapshots_sit_on_the_wrong_side():
    a = g9.check_as_of_dates(shares("W1", [(1, 10)], as_of="2023-03-01"),   # after the switch
                             shares("W1", [(1, 10)], as_of="2023-03-31"),
                             {"W1": "2023-02-15"})
    assert bool(a.loc[0, "as_of_ok"]) is False
    w = pd.DataFrame([{"wave": "W1", "permno": 1, "weight": 1.0}])
    s = g9.summarize(g9.wave_continuity(w, w.copy()), CONFIG, as_of=a, convention=CONV)
    assert s["waves_failing_as_of_placement"] == ["W1"]


def test_a_post_snapshot_dated_on_the_conversion_day_is_flagged(): 
    """Audit item 5: whether a snapshot dated exactly on the effective date reflects the
    converted portfolio depends on the fund's reporting convention, which the as-of date
    does not reveal. It counts as post (P1's rule) and is flagged."""
    a = g9.check_as_of_dates(shares("W1", [(1, 10)], as_of="2023-01-31"),
                             shares("W1", [(1, 10)], as_of="2023-02-15"),
                             {"W1": "2023-02-15"})
    assert bool(a.loc[0, "post_as_of_equals_effective"]) is True
    assert a.loc[0, "post_side"] == "post"          # still post, per the P1 rule
    assert bool(a.loc[0, "as_of_ok"]) is True       # not an error — an ambiguity


def test_the_strictly_after_sensitivity_is_available_where_a_later_snapshot_exists():
    post = pd.concat([shares("W1", [(1, 10)], as_of="2023-02-15"),
                      shares("W1", [(1, 10)], as_of="2023-03-31")])
    a = g9.check_as_of_dates(shares("W1", [(1, 10)], as_of="2023-01-31"), post,
                             {"W1": "2023-02-15"})
    assert a.loc[0, "post_as_of"] == pd.Timestamp("2023-02-15")        # the headline choice
    assert a.loc[0, "post_as_of_strict"] == pd.Timestamp("2023-03-31")  # the sensitivity
    s = g9.effective_date_sensitivity(a)
    assert s["waves_affected"] == ["W1"]
    assert s["waves_with_a_strictly_after_alternative"] == ["W1"]
    assert s["waves_lost_under_strictly_after"] == []


def test_a_wave_with_no_later_snapshot_is_reported_as_lost_not_absorbed():
    a = g9.check_as_of_dates(shares("W1", [(1, 10)], as_of="2023-01-31"),
                             shares("W1", [(1, 10)], as_of="2023-02-15"),
                             {"W1": "2023-02-15"})
    s = g9.effective_date_sensitivity(a)
    assert s["waves_lost_under_strictly_after"] == ["W1"]
    assert s["sensitivity_required"] is True


def test_the_sensitivity_is_reported_even_when_nothing_is_flagged():
    """A sensitivity mentioned only when it bites is not a sensitivity."""
    a = g9.check_as_of_dates(shares("W1", [(1, 10)], as_of="2023-01-31"),
                             shares("W1", [(1, 10)], as_of="2023-03-31"),
                             {"W1": "2023-02-15"})
    w = pd.DataFrame([{"wave": "W1", "permno": 1, "weight": 1.0}])
    s = g9.summarize(g9.wave_continuity(w, w.copy()), CONFIG, as_of=a, convention=CONV)
    assert s["effective_date_sensitivity"]["sensitivity_required"] is False
    assert s["effective_date_sensitivity"]["n_waves"] == 1
