"""Gate-0 threshold integrity.

Two failure modes this pins, both of which turn a pre-registered kill-switch into
a post-hoc one:

  * a threshold DRIFTS from the number Plan v2.1 §9 pre-committed;
  * a threshold that has never been decided gets silently defaulted by whoever
    writes R3, instead of stopping.

The null thresholds here are not an oversight. Plan §9 states G4's mass line and
G6's flatness line qualitatively only, so there is nothing to transcribe, and
picking a number after seeing the diagnostic is specification search.
"""
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG = yaml.safe_load((ROOT / "refraction" / "frozen_config.yaml").read_text())
G0 = CONFIG["gate0_thresholds"]

# Transcribed from Plan v2.1 §9 / 执行手册 §R3. Changing one of these is a
# pre-registration deviation and must be disclosed, never a quiet edit.
PLAN_COMMITTED = {
    "surprise_coverage_min": 0.95,     # §9 week 1
    "sd_L_min": 0.25,                  # §9 weeks 1-2 (joint window)
    "corr_L_convexp_max": 0.30,        # §9 weeks 1-2
    "se_share_min": 0.70,              # §9 weeks 1-2
    "n_pre_median_min": 30,            # §9 weeks 1-2 / §R3 G3 — see the conflict note
    "d_b_min": 0.10,                   # §9 week 2
    "mde_sigma_max": 0.5,              # §9 weeks 2-3
    "convexp_treated_min": 0.005,      # §5 treated line, 0.5%
    "sweep_window_min_gridpoints": 2,  # §R3 G2 "宽度<网格 2 格 → FAIL"
    "intraday_coverage_min": 0.70,     # v2.2 §9 G7 — blocking as of v2.2
}

# v2.2 added two lines with no number anywhere to transcribe. Same treatment G4 and
# G6 got: null, so R3 stops rather than inventing one.
PENDING = {"first_stage_primary_alpha", "intraday_vendor_agreement_tol",
           "portfolio_overlap_min", "portfolio_weight_corr_min",
           "portfolio_turnover_max",
           "vecm_min_effective_obs_per_event"}          # safeguard 4

# Decided 2026-08-19 under delegation. Each must stay traceable to its memo and
# to ops/decisions.md; a silent edit to one of these is a prereg deviation.
DELEGATED = {
    "d_b_mass_share_min": 0.50,
    "pretrend_joint_p_min": 0.10,
    "pretrend_individual_lead_adjust": "holm",
}
MEMO = ROOT / "refraction" / "DECISIONS-2026-08-19.md"


@pytest.mark.parametrize("key,expected", sorted(DELEGATED.items()))
def test_delegated_decision_holds_its_recorded_value(key, expected):
    assert G0[key] == expected, (
        f"{key} is {G0[key]}, the delegated decision recorded {expected}. Changing it "
        "is a pre-registration deviation requiring disclosure.")


@pytest.mark.parametrize("key", sorted(DELEGATED))
def test_delegated_decision_is_traceable_to_a_memo_and_the_decision_log(key):
    """A number nobody can trace is indistinguishable from a number somebody
    invented after seeing a diagnostic."""
    assert MEMO.exists(), "the delegated-decision memo is missing"
    assert key in MEMO.read_text(), f"{key} not explained in {MEMO.name}"
    assert key in (ROOT / "ops" / "decisions.md").read_text(), \
        f"{key} not recorded in ops/decisions.md"


def test_the_memo_still_requires_counter_signature():
    """These were made under delegation, not by the PI. Until signed they bind
    nothing — the same standing DAX's D1 memo carries."""
    text = MEMO.read_text().lower()
    assert "counter-sign" in text or "counter-signature" in text


def test_every_gate0_threshold_is_classified():
    """A new threshold must be classified, so none can appear unnoticed."""
    # g9_reporting / g9_failure_response are POLICY entries, not numeric thresholds.
    POLICY = {"g9_reporting", "g9_failure_response", "g9_confirmatory_response",
              "g9_secondary_interpretation", "g7_tests_vecm_estimability",
              "estimator_fallback_if_vecm_unstable"}
    unclassified = (set(G0) - set(PLAN_COMMITTED) - set(DELEGATED) - PENDING - POLICY
                    - {"se_to_sdL_ratio_max"})
    assert not unclassified, f"unclassified Gate-0 threshold(s): {sorted(unclassified)}"


@pytest.mark.parametrize("key", sorted(PENDING))
def test_v22_pending_thresholds_stay_null_until_decided(key):
    """G7's vendor tolerance and G8's first-stage majority are undecided. If one
    acquires a value it must arrive with an owner decision, not from whoever is
    writing the diagnostic with the first stage already in front of them."""
    assert key in G0
    if G0[key] is not None:
        assert key in (ROOT / "ops" / "decisions.md").read_text(), (
            f"{key} was given the value {G0[key]} with no owner decision recorded.")


def test_the_operationalization_of_much_less_than_is_flagged_as_a_judgement():
    """Plan §9 writes SE(β̂) ≪ SD(L̂) without defining ≪. The config defines it as
    a ratio, which is a judgement the config makes explicit rather than hides."""
    assert G0["se_to_sdL_ratio_max"] == pytest.approx(0.3333, abs=1e-4)
    assert "operationalizes" in (ROOT / "refraction" / "frozen_config.yaml").read_text()


# --------------------------------------------------------------------------- #
# sample frame — the invariant that replaces a hand-set waves_end              #
# --------------------------------------------------------------------------- #

def _add_quarters(datestr, quarters):
    """Add whole quarters to an ISO date, clamping to the target month's length
    (a naive min(day, 28) would make the bound stricter than the rule)."""
    import calendar, datetime
    d = datetime.date(*map(int, str(datestr).split("-")))
    m = d.month - 1 + 3 * quarters
    year, month = d.year + m // 12, m % 12 + 1
    return datetime.date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def test_waves_end_leaves_every_wave_its_required_post_period():
    """The bug this pins: waves_end was 2025-12-31 against announcements_end
    2026-06-30, leaving the last waves ~2 post-quarters for a design that needs
    4 — and assert A2 CANNOT catch it, because A2 measures coverage against a
    calendar truncated at the same announcements_end."""
    sample, panel = CONFIG["sample"], CONFIG["panel"]
    last_wave_needs = _add_quarters(sample["waves_end"], panel["post_quarters_required"])
    assert last_wave_needs.isoformat() <= str(sample["announcements_end"]), (
        f"a wave on waves_end {sample['waves_end']} would need announcements through "
        f"{last_wave_needs}, past announcements_end {sample['announcements_end']} — "
        f"fewer than {panel['post_quarters_required']} post-quarters")


def test_wave_window_sits_inside_the_announcement_window():
    sample = CONFIG["sample"]
    assert str(sample["announcements_start"]) < str(sample["waves_start"])
    assert str(sample["waves_end"]) < str(sample["announcements_end"])


def test_pre_and_post_coverage_requirements_are_both_declared():
    panel = CONFIG["panel"]
    assert panel["pre_quarters_required"] == 8
    assert panel["post_quarters_required"] == 4      # asymmetric by decision


def test_assert_A2_reads_the_post_bound_instead_of_mirroring_the_pre_bound():
    """A2 defaulted to a symmetric ±pre_quarters window; with an asymmetric rule
    that would have silently demanded coverage the sample frame excludes."""
    import inspect, sys
    sys.path.insert(0, str(ROOT))
    from refraction.pipeline import assert_panel as ap
    sig = inspect.signature(ap.a2_treated_coverage)
    assert "post_quarters" in sig.parameters
    src = inspect.getsource(ap.run_all)
    assert "post_quarters_required" in src and "post_quarters=post_q" in src


def test_w_shrink_is_still_unfrozen_before_gate_prereg():
    """Filling it early is the one edit that silently unblocks R6+."""
    assert CONFIG["beta"]["w_shrink"] is None
    assert CONFIG["prereg"]["osf_timestamp"] is None


# --------------------------------------------------------------------------- #
# v2.2 structural commitments — guards against drift back to the v2.1 design   #
# --------------------------------------------------------------------------- #

def test_the_core_design_is_fomc_only_with_cpi_nfp_as_generalization():
    """An unfocused all-macro panel was one of the crowding problems the collision
    review identified (Plan v2.2 §5.1 item 5, §7.6)."""
    panel = CONFIG["panel"]
    assert panel["announcement_types"] == ["FOMC"]
    assert set(panel["generalization_types"]) == {"CPI", "NFP"}


def test_an_announcement_day_dummy_is_forbidden_as_the_treatment():
    """Bernanke-Kuttner: the shock is the UNEXPECTED component of policy."""
    assert CONFIG["shock"]["announcement_day_dummy_allowed"] is False
    assert CONFIG["shock"]["primary"] == "S_mp"
    assert CONFIG["shock"]["companion"] == "S_cbi"


def test_the_shock_decomposition_is_marked_unverified():
    """Every v2.2 reference is owner-supplied; REFR-R0 still owes the first-hand sweep."""
    assert CONFIG["shock"]["decomposition_status"] == "OWNER_SUPPLIED_UNVERIFIED"


def test_the_network_measure_may_not_be_named_before_it_is_licensed():
    """Plan §6.1: mechanism must be measured, not named."""
    ne = CONFIG["network_exposure"]
    assert ne["licensed"] is None
    assert ne["naming_allowed_before_licensing"] is False
    assert ne["candidate"] == "L_tilt_pre"        # v2.3: predetermined, explicitly


# --------------------------------------------------------------------------- #
# v2.3 hardening — each test pins a correction, not a preference               #
# --------------------------------------------------------------------------- #

def test_the_first_stage_turns_on_one_primary_outcome_not_a_vote():
    """v2.2 required a 'majority of five proxies'. A vote across heterogeneous
    proxies has no economic foundation and is not a test.

    Freeze 1 (2026-08-28): the primary is now null pending the recorded choice, and there
    are exactly TWO named candidates with a rule between them — still one primary, chosen
    on data quality before any coefficient, never a vote over outcomes."""
    ne = CONFIG["network_exposure"]
    assert ne["first_stage_primary_outcome"] is None       # resolved by the decision record
    assert set(ne["first_stage_primary_candidates"]) == {"preferred", "fallback"}
    assert "first_stage_majority_min" not in CONFIG["gate0_thresholds"]
    assert len(ne["first_stage_secondary_outcomes"]) == 4


# --------------------------------------------------------------------------- #
# 2026-08-28 freezes                                                           #
# --------------------------------------------------------------------------- #

def test_freeze1_both_candidate_outcomes_take_the_absolute_cr_exposure():
    """A signed flow against an unsigned volume outcome tests nothing; against the
    sign(CR)-aligned imbalance it counts the sign twice. The sign lives in the OUTCOME."""
    ne = CONFIG["network_exposure"]
    assert ne["first_stage_primary_exposure"] == "abs_CR_x_absL"
    assert ne["first_stage_signed_cr_exposure_forbidden_for_primary"] is True
    for arm in ("preferred", "fallback"):
        assert ne["first_stage_primary_candidates"][arm]["exposure"] == "abs_CR_x_absL"
    # the signed form survives only where it belongs: the signed return corroboration
    assert ne["first_stage_corroborating_exposure"] == "signed_CR_x_absL"


def test_freeze1_the_fallback_rule_keys_only_on_data_quality():
    """Every criterion must be a fact about coverage or agreement. A criterion mentioning
    an outcome, a coefficient or significance would make the choice specification search."""
    rule = CONFIG["network_exposure"]["first_stage_outcome_choice_rule"]
    assert rule["decided_before_any_treatment_coefficient"] is True
    assert rule["otherwise"] == "fallback"
    banned = ("a1", "coeff", "t_stat", "significan", "p_value", "alpha")
    for k in rule["use_preferred_iff_all"]:
        assert not any(b in k.lower() for b in banned), k


def test_freeze1_the_primary_trading_outcome_is_measured_on_the_cr_day():
    """The AP's own footprint is same-day; the t+1 lag belongs to the return corroboration."""
    ne = CONFIG["network_exposure"]
    assert ne["first_stage_primary_outcome_lag_days"] == 0
    assert ne["first_stage_response_lag_days"] == 1


def test_freeze2_the_cr_timestamp_is_unaudited_and_defaults_to_the_weaker_claim():
    ne = CONFIG["network_exposure"]
    assert ne["cr_timestamp_audit_complete"] is False
    assert ne["cr_timestamp_resolution"] is None          # NEED_INFO, not assumed
    assert ne["cr_intraday_timestamp_supplied_by_vendor"] is None
    assert ne["g8_event_language"]["default_when_unaudited"] == "daily"
    assert "days" in ne["g8_event_language"]["daily"]
    assert "around" in ne["g8_event_language"]["intraday"]


def test_freeze3_the_baseline_control_vector_is_predetermined_only():
    """Realized creation-basket weight is chosen by the AP after conversion. Conditioning
    on it silently changes the estimand, so it lives in the horse race, not the baseline."""
    ne = CONFIG["network_exposure"]
    z = ne["first_stage_cr_interacted_controls"]
    assert "pre_conversion_holding_weight" in z
    assert "basket_weight" not in z
    for banned in ne["first_stage_post_treatment_controls_forbidden_in_baseline"]:
        assert banned not in z
    hr = ne["first_stage_mechanism_horse_race"]
    assert hr["added_control"] == "realized_creation_basket_weight"
    assert hr["may_replace_baseline"] is False
    assert "incremental" in hr["estimand"]


def test_freeze4_the_cr_event_census_is_required_and_carries_no_threshold():
    """Mechanism variation is CR events, not constituent-day rows. A minimum chosen now,
    with the data in hand, would be the specification search the plan forbids."""
    ne = CONFIG["network_exposure"]
    assert ne["cr_event_census_required_before_estimation"] is True
    assert set(ne["cr_event_census_by"]) == {"fund", "wave", "adviser"}
    assert "n_nonzero_cr_days" in ne["cr_event_census_reports"]
    assert not any("min" in k for k in ne if k.startswith("cr_event_census"))


def test_basket_weight_is_not_the_primary_validation_outcome():
    """It is near-mechanical in holdings — it would pass by construction."""
    ne = CONFIG["network_exposure"]
    assert ne["first_stage_primary_outcome"] != "basket_inclusion_or_weight"
    assert "basket_inclusion_or_weight" in ne["first_stage_secondary_outcomes"]


def test_the_redefine_escape_hatch_is_gone():
    """v2.2 allowed rebuilding NetExp from whichever proxies worked — post-treatment
    data mining. Re-entry is now only via an external sample or cross-fitting."""
    routes = CONFIG["network_exposure"]["redesign_reentry_routes"]
    assert set(routes) == {"external_etf_training_sample", "prespecified_split_or_crossfit"}


def test_the_post_conversion_carveout_is_unsigned_and_whitelisted():
    """G8 is the one Gate-0 line touching post-conversion data, because the arbitrage
    observables do not exist while the fund is still a mutual fund. Narrow and signed,
    or it does not run."""
    ne = CONFIG["network_exposure"]
    assert ne["post_conversion_carveout_signed"] is False
    wl = ne["post_conversion_whitelist"]
    assert len(wl) == 5
    for banned in ("r_total", "conv_exp", "beta_i", "L"):
        assert banned not in wl        # no study outcome may enter the carve-out


def test_the_jk_decomposition_names_two_series_not_one():
    """A one-dimensional surprise does not split. Both legs are NEED_INFO until R1a."""
    sh = CONFIG["shock"]
    assert "policy_instrument_series" in sh and "equity_series" in sh
    assert sh["policy_instrument_series"] is None and sh["equity_series"] is None
    assert sh["classification"] == "sign_pair"


def test_the_fomc_event_is_two_distinct_episodes():
    """v2.4: press conferences carry major policy news, so treating them as a nuisance
    window would discard much of the shock in the recent sample."""
    sh = CONFIG["shock"]
    assert sh["primary_episodes"] == ["statement_30m", "press_conference_70m"]
    assert sh["minutes"] == "excluded_from_primary"
    assert sh["combined_event"] == "overall_transmission_summary_robustness"


def test_statement_halflife_stops_at_the_press_conference():
    """The presser is a NEW shock; anything measured across it is news arrival, not
    slow propagation. Truncation by construction, not by robustness check."""
    assert CONFIG["shock"]["statement_halflife_truncated_at_presser_start"] is True


def test_inference_does_not_take_power_from_intraday_rows():
    inf = CONFIG["inference"]
    assert inf["small_cluster_primary"] == "wild_cluster_bootstrap"
    assert inf["sponsor_level"] == "adviser_not_trust"
    assert inf["effective_clusters_recomputed_after"] == "G7"
    assert inf["report_effective_clusters_in_every_table"] is True


def test_the_wedge_is_demoted_and_its_construction_is_unchanged():
    """Demoted to diagnostic, but the horizons the machinery already builds stay put."""
    w = CONFIG["wedge"]
    assert w["status"] == "dynamic_diagnostic_not_headline"
    assert w["horizons_days"] == [1, 5, 20, 60]


def test_the_registered_spec_points_at_v22():
    assert CONFIG["prereg"]["registered_spec"] == "SPEC-MAIN-v2.4"
    assert CONFIG["prereg"]["osf_timestamp"] is None      # still a free redesign


# --------------------------------------------------------------------------- #
# v2.4 — the final freeze                                                      #
# --------------------------------------------------------------------------- #

def test_g8_runs_on_a_non_fomc_calibration_window():
    """The change that makes the post-conversion carve-out narrow enough to sign:
    mechanism validation never touches a headline outcome."""
    cw = CONFIG["network_exposure"]["calibration_window"]
    assert cw["start_trading_days_after_conversion"] == 21     # seasoning buffer
    assert cw["end_trading_days_after_conversion"] == 252
    assert cw["exclude_buffer_trading_days"] >= 1
    for d in ("fomc_statement_dates", "fomc_press_conference_dates", "fomc_minutes_dates"):
        assert d in cw["exclude"]


def test_the_first_stage_uses_a_lag_and_disclaims_causality():
    """Contemporaneous creation/redemption and returns are jointly determined — a
    same-day regression measures simultaneity, not connectivity."""
    ne = CONFIG["network_exposure"]
    assert ne["first_stage_response_lag_days"] == 1
    assert ne["first_stage_claim_is_causal"] is False
    assert ne["first_stage_residualization"] == "pre_conversion_market_and_industry_loadings"


def test_the_dependence_model_is_frozen_and_names_all_three_sources():
    """A ladder of procedures is not a specification."""
    dep = CONFIG["inference"]["dependence_sources"]
    assert set(dep) == {"common_event_shock", "repeated_stock", "treatment_shock"}
    assert dep["treatment_shock"] == "cluster_on_adviser"


def test_the_small_cluster_procedure_is_left_unresolved_on_purpose():
    """Clarification 2026-08-19: adviser-only resampling does not address common event
    dependence, and the right multiway procedure depends on the actual identifying
    FOMC-event and adviser counts, which G7 and G9 determine. Defaulting to adviser-only
    in the meantime is explicitly forbidden."""
    inf = CONFIG["inference"]
    assert inf["bootstrap_resamples"] is None
    assert inf["bootstrap_resamples_default_forbidden"] == "adviser_only"
    assert inf["bootstrap"]["impose_null"] is True          # the one part already fixed
    assert set(inf["identifying_advisers_recomputed_after"]) == {"G7", "G9"}


def test_g9_reports_continuously_rather_than_on_an_arbitrary_cutoff():
    g0 = CONFIG["gate0_thresholds"]
    assert g0["g9_reporting"] == "continuous_with_threshold_sensitivity"
    assert set(g0["g9_failure_response"]) == {"restrict_to_high_continuity_waves",
                                              "relabel_treatment"}


def test_the_usmpd_series_are_a_freeze_task_not_an_availability_unknown():
    sh = CONFIG["shock"]
    assert sh["series_availability"] == "CONFIRMED_OWNER_SUPPLIED"
    assert sh["policy_instrument_series"] is None      # still to be FROZEN by R1a
    assert sh["equity_series"] is None


def test_the_adviser_map_bounds_the_cluster_count(tmp_path):
    """Trust strings mislead in both directions; the mapping must return a RANGE and
    flag the series trusts rather than emit a false point estimate."""
    import sys
    sys.path.insert(0, str(ROOT / "refraction" / "inference"))
    import adviser_map as am
    rows = am.build()
    summ = am.summarize(rows)
    assert summ["adviser_count_lower_bound"] <= summ["adviser_count_upper_bound"]
    assert summ["funds_needing_filing_lookup"] > 0     # series trusts are unresolved
    assert summ["adviser_count_upper_bound"] < 46      # fewer than trust-level families
    # a known multi-trust adviser must collapse
    assert am.classify("Fidelity Salem Street Trust")[0] == "Fidelity"
    assert am.classify("Fidelity Summer Street Trust")[0] == "Fidelity"
    # a series trust must NOT be treated as one adviser
    assert am.classify("Northern Lights Fund Trust IV")[1] is True
    assert am.classify("The RBB Fund, Inc.")[1] is True


# --------------------------------------------------------------------------- #
# implementation safeguards (2026-08-19), pinned before headline estimation     #
# --------------------------------------------------------------------------- #

def test_g8_prefers_the_pooled_interaction_over_a_noisy_two_step():
    """Safeguard 1: phi-hat estimates are noisy and must not enter a second stage as
    error-free outcomes."""
    ne = CONFIG["network_exposure"]
    assert ne["first_stage_design"] == "pooled_interaction"
    assert ne["two_step_requires_uncertainty_propagation"] is True
    assert ne["shares_outstanding_audit_required"] is True


def test_the_g8_functional_form_is_registered_as_a_magnitude():
    """Safeguard 2: connectivity is a magnitude concept; the signed lever carries the
    direction of macro-response pull, which belongs to the headline gamma, not to a
    flow-sensitivity outcome. Reasoning: refraction/G8_SIGN_PREDICTION.md."""
    ne = CONFIG["network_exposure"]
    assert ne["first_stage_functional_form"] == "abs_L_tilt_pre"
    assert ne["first_stage_sided"] == "one_sided"
    assert ne["first_stage_decision_keys_on"] == "linear_coefficient"
    assert "signed_L_tilt_pre" in ne["first_stage_secondary_forms"]
    assert (ROOT / "refraction" / "G8_SIGN_PREDICTION.md").exists()


def test_the_episode_multiplicity_rule_is_registered_before_results():
    """Safeguard 3: two co-primary episodes need a multiplicity rule fixed in advance,
    and statement adjustment across a new arrival is CENSORED, not a half-life."""
    sh = CONFIG["shock"]
    assert "episode_multiplicity_rule" in sh          # null until decided; must exist
    assert sh["statement_adjustment_is_censored_at_presser"] is True


def test_g7_tests_estimability_not_only_coverage():
    """Safeguard 4: coverage is not the same as enough effective observations for a
    short-window VECM."""
    g0 = CONFIG["gate0_thresholds"]
    assert g0["g7_tests_vecm_estimability"] is True
    assert set(g0["estimator_fallback_if_vecm_unstable"]) == {
        "arbitrage_gap_convergence", "lead_lag"}


def test_the_bootstrap_must_be_multiway_compatible():
    """Safeguard 5: adviser-only resampling does not address common event dependence."""
    inf = CONFIG["inference"]
    assert inf["bootstrap_multiway_compatible"] is True
    assert "bootstrap_multiway_procedure" in inf      # null until named
    assert inf["leave_one_adviser_out_diagnostics"] is True
    assert set(inf["identifying_advisers_recomputed_after"]) == {"G7", "G9"}


def test_relabelling_cannot_silently_replace_the_clean_wrapper_headline():
    """Safeguard 6: restriction is the confirmatory response; relabelling is secondary."""
    g0 = CONFIG["gate0_thresholds"]
    assert g0["g9_confirmatory_response"] == "restrict_to_high_continuity_waves"
    assert "separately" in g0["g9_secondary_interpretation"]


def test_the_g8_outcome_choice_record_exists_and_is_still_unresolved():
    """The decision record is the artefact `verdict()` keys on. While it says unresolved,
    G8 has not been adjudicated — and that must be visible, not inferred."""
    rec = ROOT / CONFIG["network_exposure"]["first_stage_outcome_choice_rule"]["decision_record"]
    assert rec.exists(), "the G8 outcome decision record is missing"
    text = rec.read_text()
    assert "NOT YET RESOLVED" in text
    assert CONFIG["network_exposure"]["first_stage_primary_outcome"] is None
    # every floor in the config must appear in the record, so the two cannot drift apart
    for key, floor in CONFIG["network_exposure"][
            "first_stage_outcome_choice_rule"]["use_preferred_iff_all"].items():
        assert key.replace("_min", "") in text, key   # the record names the FACT
        if isinstance(floor, float):
            assert ("%.2f" % floor) in text, key


# --------------------------------------------------------------------------- #
# freezes 5 and 6 (2026-08-28)                                                 #
# --------------------------------------------------------------------------- #

def test_freeze5_the_outcome_unit_is_frozen_and_carries_no_size():
    """A raw dollar imbalance scales with the stock's size, and |L_tilt^pre| is not
    independent of size — so the unit is part of the registration, not an afterthought."""
    n = CONFIG["network_exposure"]["first_stage_outcome_normalization"]
    assert n["numerator"] == "signed_dollar_imbalance"
    assert n["denominator"] == "adv_dollar_pre"
    assert n["log_transform"] is False          # a log would drop the imbalance's sign
    assert list(n["winsorize_outcome_pct"]) == [1, 99]
    lo, hi = n["adv_window_trading_days"]
    assert lo < hi < 0, "the ADV window must be entirely pre-conversion"


def test_the_cr_definition_is_frozen_once_with_every_element_specified():
    """Audit item 1. Freeze 5 had registered a TNA-scaled CR while Plan v2.4 §6.1.2 had
    already frozen a share-growth rate; they differ by the fund's own NAV return. The plan's
    definition wins and the TNA form is deleted."""
    ne = CONFIG["network_exposure"]
    assert "first_stage_exposure_normalization" not in ne, "the deleted TNA block is back"
    d = ne["cr_definition"]
    assert d["formula"] == "CR_{f,t} = (S_{f,t} - S_{f,t-1}) / S_{f,t-1}"
    assert d["numerator"] == "etf_shares_outstanding_difference"
    assert d["numerator_uses_price_or_nav"] is False        # no NAV, no price
    assert d["denominator_timing"] == "t_minus_1"
    assert d["sign_convention"] == "positive_is_creation_inflow"
    assert d["shares_corporate_action_adjusted"] is True
    assert d["further_rescaling_forbidden"] is True
    assert "cr_over_tna" in d["dollar_or_tna_scaled_forms_forbidden"]


def test_freeze6_g8_has_three_outcomes_and_low_power_is_not_failure():
    ne = CONFIG["network_exposure"]
    assert "INSUFFICIENT_IDENTIFYING_VARIATION" in ne["first_stage_outcomes"]
    assert ne["insufficient_variation_is_not_mechanism_failure"] is True
    resp = ne["insufficient_variation_response"]
    assert "neither" in resp and "UNTESTED" in resp
    assert "never" in resp                      # no re-entry by lowering the bar


def test_the_headline_gammas_mde_line_stays_with_the_headline_gamma():
    """Audit item 4. G0's 0.5-sigma bar is defined in Plan v2.1 §9 for the power simulation
    on the joint (ConvExp, NetExp, S) distribution, wave-clustered, for gamma pooled /
    gamma_tilt / gamma_fac. It is not a generic mechanism-test floor and does not travel."""
    rules = CONFIG["network_exposure"]["first_stage_insufficient_variation_rules"]
    assert G0["mde_sigma_max"] == 0.5                    # unchanged where it belongs
    assert rules["mde_sigma_max"] is None                # and NOT transplanted
    assert CONFIG["network_exposure"]["first_stage_power_trigger_active"] is False
    # both surviving triggers are numerical degeneracy checks, not sufficiency bars
    assert rules["min_nonzero_cr_days"] == 2
    assert rules["degenerate_exposure_rank_tol"] <= 1e-8


def test_the_frozen_spec_carries_a_timestamped_hash_and_is_not_mistaken_for_the_osf_prereg():
    """The repo-local freeze record. It makes "frozen before outcomes" checkable now; it is
    NOT the pre-registration, which is a human gate downstream of the Gate-0 report."""
    import json
    rec = json.loads((ROOT / "refraction" / "frozen_config.yaml.lineage.json").read_text())
    assert rec["registered_spec"] == CONFIG["prereg"]["registered_spec"]
    assert rec["output_sha256"] and rec["timestamp"] and rec["code_version"] != "unknown"
    assert "REFR-GATE-OSF" in rec["what_this_is_NOT"]
    # and the real gate is still shut
    assert CONFIG["prereg"]["osf_timestamp"] is None
    assert CONFIG["beta"]["w_shrink"] is None


def test_the_g8_report_always_carries_inference_alongside_the_classification():
    """Audit item 3: INSUFFICIENT_IDENTIFYING_VARIATION is an evidentiary classification,
    not a replacement for reporting the estimate."""
    ne = CONFIG["network_exposure"]
    always = set(ne["first_stage_report_always"])
    for key in ("a1", "ci_low", "ci_high", "mde_sigma", "n_nonzero_cr_days",
                "concentration_top1_share", "n_effective_fund_clusters",
                "n_effective_adviser_clusters", "n_effective_event_clusters"):
        assert key in always, key
    assert 0 < ne["first_stage_ci_level"] < 1


def test_the_preregistration_is_two_stage_and_stage_one_needs_no_data():
    """Audit item 6. A single-stage prereg leaves the scientific content unregistered during
    the exact period when data is being touched."""
    pr = CONFIG["prereg"]
    assert pr["two_stage"] is True
    assert pr["stage1"]["blocked_on"] == "nothing_data_related"
    for item in ("hypotheses", "estimators", "gate_algorithms", "decision_rules",
                 "cr_definition", "w_shrink_selection_algorithm"):
        assert item in pr["stage1"]["contents"], item
    # stage 2 carries only what an algorithm computes; discretion belongs to stage 1
    assert pr["stage2"]["every_entry_must_be"] == "mechanically_determined_by_a_stage1_algorithm"
    for banned in ("new_hypotheses", "changed_estimators", "changed_decision_rules",
                   "changed_thresholds"):
        assert banned in pr["stage2"]["contents_forbidden"], banned
    assert "realized_w_shrink" in pr["stage2"]["contents_allowed"]
    assert "g8_outcome_arm_selected" in pr["stage2"]["contents_allowed"]


def test_the_w_shrink_algorithm_is_frozen_even_though_the_value_is_not():
    """The minimum item 6 asks for: the MAP from feasibility inputs to w_shrink."""
    sel = CONFIG["beta"]["w_shrink_selection"]
    assert CONFIG["beta"]["w_shrink"] is None              # the value still waits for data
    assert sel["algorithm"] == "midpoint_of_longest_feasible_run"
    assert sel["on_no_feasible_run"] == "FAIL_G2"          # never a relaxed condition
    assert sel["tie_break_run"] and sel["tie_break_midpoint"]   # deterministic
    assert set(sel["feasibility_conditions"]) <= set(G0)       # no new thresholds
    assert (ROOT / "refraction" / "pipeline" / "w_shrink.py").exists()


def test_the_g8_classification_separates_absence_of_evidence_from_evidence_of_absence():
    """Audit item 2. Without an outcome-specific equivalence margin, a non-significant
    estimate cannot be called retirement — and the software says so."""
    ne = CONFIG["network_exposure"]
    assert set(ne["first_stage_outcomes"]) == {
        "licensed", "not_licensed_inconclusive", "retired_from_headline",
        "INSUFFICIENT_IDENTIFYING_VARIATION"}
    assert ne["first_stage_equivalence_margin"] is None
    assert ne["first_stage_retirement_requires_equivalence_margin"] is True
    assert ne["first_stage_classification_is_governance_not_inference"] is True
    # the governance consequence is unchanged: only "licensed" reaches the headline
    assert ne["first_stage_headline_use_blocked_unless"] == "licensed"


def test_raw_cr_owns_the_sign_and_the_scaled_column_does_not():
    """Audit item 1."""
    d = CONFIG["network_exposure"]["cr_definition"]
    assert d["raw_column"] == "CR_raw"
    assert d["magnitude_raw_column"] == "CR_mag_raw"
    assert d["analysis_column"] == "CR_mag"
    assert d["exposure_magnitude_column"] == "CR_mag"
    assert d["exposure_sign_column"] == "CR_raw"
    assert d["analysis_column_sign_is_not_economic"] is True
    # the transformation, which the final decision reduced to the identity
    assert d["magnitude_first"] is True
    assert d["winsorize_signed_series_forbidden"] is True
    prim = d["primary_exposure_transform"]
    assert prim["transform"] == "identity"
    assert prim["centering"] == prim["scaling"] == prim["winsorization"] == "none"
    assert d["standardize_within_fund"] is False
    rob = d["robustness_exposure_transform"]
    assert rob["role"] == "robustness_only" and rob["may_replace_primary"] is False
    assert rob["clip_estimated_on"] == "nonzero_event_magnitudes_only"
    assert rob["min_nonzero_events_for_fund_specific_cap"] > 0
    assert rob["pooled_cap_fallback"] is True
    assert rob["preserve_zero_exactly"] is True
    assert rob["never_zero_a_genuine_event"] is True
    assert set(d["invariants"]) == {"zero_iff_zero", "non_negative", "symmetric", "monotone"}
    assert d["census_uses_raw_pre_winsorized"] is True
    for job in ("sign", "creation_vs_redemption", "zero_event_status", "event_census",
                "concentration_statistics", "aligned_outcome_sign"):
        assert job in d["raw_defines"], job
    assert d["standardize_mode"] == "none"      # withdrawn from both specifications


def test_the_shares_refresh_frequency_audit_is_registered_and_open():
    """Audit item 4: a delayed vendor update must not be labelled a precisely dated event."""
    ne = CONFIG["network_exposure"]
    assert ne["shares_update_frequency_audit_required"] is True
    assert ne["shares_update_frequency"] is None
    assert ne["shares_stale_carryforward_detected"] is None
    assert ne["shares_repeated_value_runs_are_events"] is False


def test_the_cr_event_timing_rule_is_binding_on_the_same_day_primary():
    """A CR change localizable only to a multi-day interval may not be paired with same-day
    constituent order imbalance."""
    t = CONFIG["network_exposure"]["cr_event_timing"]
    assert t["primary_sample"] == "dated_only"
    assert t["interval_events_in_primary"] == "excluded"
    assert t["interval_events_may_be_matched_same_day"] is False
    assert t["on_unaudited_refresh"] == "all_events_interval"
    assert t["absent_freshness_evidence"] == "interval"
    # CORRECTED: dated turns on per-observation freshness evidence, not on the value pattern
    assert set(t["dated_requires"]) == {"economic_as_of_freshness_at_t",
                                        "economic_as_of_freshness_at_t_minus_1"}
    fe = t["freshness_evidence"]
    assert fe["sufficient"] == ["per_observation_economic_as_of_date"]
    assert fe["also_required"] == "documented_daily_economic_cutoff"
    assert fe["publication_timestamp_is_not_freshness"] is True
    for pub in ("vendor_file_publication_timestamp", "api_response_timestamp",
                "vendor_refresh_flag"):
        assert pub in fe["insufficient_alone"], pub
    assert t["primary_additionally_requires"] == "cr_oib_interval_alignment"
    assert set(t["classes"]) == {"dated", "interval",
                                 "zero_net_verified", "zero_net_unverified"}
    z = t["zero_cr_observations"]
    assert z["zero_net_verified"]["primary_eligible"] is True
    assert z["zero_net_unverified"]["primary_eligible"] is False
    # a verified zero is a zero NET observation; offsetting flows are unobserved
    assert z["zero_net_verified"]["does_not_establish"] == "zero_gross_ap_activity"
    assert z["zero_net_verified"]["may_be_interpreted_as_no_ap_activity_control"] is False
    assert z["offsetting_flows_within_the_interval_are_unobserved"] is True
    assert z["unverified_zeros_in_primary"] == "excluded"
    assert z["unverified_zeros_may_be_treated_as_no_creation"] is False
    al = t["cr_oib_interval_alignment"]
    assert al["calendar_date_equality_is_not_alignment"] is True
    assert al["oib_measurement_interval_must_match"] is True
    assert al["coverage_required_for_every_class"] is True
    assert al["exact_alignment_requires_full_window_oib"] is True
    ctc = al["classes"]["close_to_close_rth_declared"]
    assert ctc["oib_window"] == "rth_session_day_t"
    assert ctc["exact_interval_alignment_claimed"] is False
    assert ctc["uncovered_portion_of_cr_interval"] == "overnight_and_pre_market"
    assert ctc["requires_complete_oib_coverage_over_registered_window"] is True
    assert al["classes"]["aligned_cutoff_to_cutoff"]["oib_window"] == \
        "cutoff_t_minus_1_to_cutoff_t"
    assert al["classes"]["aligned_cutoff_to_cutoff"][
        "requires_complete_oib_coverage_over_interval"] is True
    assert al["classes"]["aligned_cutoff_to_cutoff"]["partial_coverage_response"] == \
        "downgrade_to_interval_robustness"
    assert al["classes"]["unaligned_unknown_cutoff"]["primary_eligible"] is False
    assert al["classes"]["unaligned_unknown_cutoff"]["claim_forbidden"] == \
        "exact_same_day_interval_alignment"
    assert set(al["primary_requires_alignment_in"]) == {"close_to_close_rth_declared",
                                                        "aligned_cutoff_to_cutoff"}
    assert al["misaligned_events_go_to"] == "interval_robustness"
    assert t["dated_means"] == "day_localized_only"
    assert t["dated_establishes_within_day_ordering"] is False
    assert t["same_day_g8_status"] == "mechanism_association_and_calibration"
    assert t["insufficient_freshness_metadata_response"] == "INSUFFICIENT_IDENTIFYING_VARIATION"
    assert t["rule_may_not_be_relaxed_for_data_availability"] is True
    assert t["equal_value_runs_are_diagnostic_only"] is True
    assert t["equal_value_run_is_sufficient_proof_of_carryforward"] is False
    assert t["verified_freshness_zero_days_stay_zero_days"] is True
    r = t["interval_robustness"]
    assert r["role"] == "robustness_only" and r["may_replace_primary"] is False
    assert r["interpretation"] == "net_interval_association"
    assert r["recovers_gross_ap_activity"] is False
    assert r["recovers_event_timing_within_interval"] is False
    for k in ("n_dated_events", "n_interval_events", "median_interval_width_days",
              "share_of_events_dated"):
        assert k in t["report"], k


def test_cross_fund_comparability_is_attributed_to_the_ratio_not_the_fixed_effects():
    """Correction: CR is comparable across funds because it is a unitless proportional
    change. The fixed effects absorb fund-day common components; the interaction is
    identified from constituent-level |L_i| variation within the fund-day."""
    text = (ROOT / "refraction" / "frozen_config.yaml").read_text()
    assert "UNITLESS PROPORTIONAL" in text
    assert "fund-day COMMON COMPONENTS" in text
    doc = (ROOT / "refraction" / "STAGE1_PREREG.md").read_text()
    assert "unitless proportional change" in doc
    assert "do not normalize the interaction" in doc
    assert "constituent-level" in doc
