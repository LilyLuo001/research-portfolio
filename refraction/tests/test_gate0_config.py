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
           "portfolio_turnover_max"}

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
    unclassified = (set(G0) - set(PLAN_COMMITTED) - set(DELEGATED) - PENDING
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
    proxies has no economic foundation and is not a test."""
    ne = CONFIG["network_exposure"]
    assert isinstance(ne["first_stage_primary_outcome"], str)
    assert "first_stage_majority_min" not in CONFIG["gate0_thresholds"]
    assert len(ne["first_stage_secondary_outcomes"]) == 4


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


def test_the_fomc_event_definition_is_frozen_with_the_presser_separate():
    """Otherwise delayed press-conference news reads as slow price adjustment, which
    is fatal to the half-life spine."""
    sh = CONFIG["shock"]
    assert sh["primary_event"] == "statement_window"
    assert sh["press_conference"] == "separate_registered_event"
    assert sh["minutes"] == "excluded_from_primary"
    assert sh["halflife_controls_press_conference"] is True


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
    assert CONFIG["prereg"]["registered_spec"] == "SPEC-MAIN-v2.3"
    assert CONFIG["prereg"]["osf_timestamp"] is None      # still a free redesign
