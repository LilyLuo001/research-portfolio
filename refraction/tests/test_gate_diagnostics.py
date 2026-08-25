"""REFR-R3 Gate-0 diagnostics.

Three properties matter more than the arithmetic:
  1. it cannot see a post-period row;
  2. it cannot invent a threshold;
  3. it cannot recommend anything.
Everything else is the six lines doing what Plan §9 says they do.
"""
import copy
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from refraction.pipeline import gate_diagnostics as gd     # noqa: E402
from refraction.guards.prereg_guard import PreregError      # noqa: E402

BASE = yaml.safe_load((ROOT / "refraction" / "frozen_config.yaml").read_text())


def cfg(**over):
    c = copy.deepcopy(BASE)
    c["gate0_thresholds"].update(over)
    return c


# --------------------------------------------------------------------------- #
# 1. it cannot see a post-period row                                           #
# --------------------------------------------------------------------------- #

def test_a_frame_carrying_post_rows_is_refused_at_the_door():
    panel = pd.DataFrame({"permno": [1, 2], "Post": [False, True], "r_total": [.01, .02]})
    with pytest.raises(PreregError) as e:
        gd.refuse_post_period(panel)
    assert "prereg-before-outcomes" in str(e.value)


def test_pre_only_splits_and_counts_rather_than_dropping_silently():
    panel = pd.DataFrame({"permno": [1, 2, 3], "Post": [False, True, True]})
    pre, dropped = gd.pre_only(panel)
    assert len(pre) == 1 and dropped == 2
    gd.refuse_post_period(pre)          # and the result now passes the door check


def test_a_pre_only_frame_passes():
    panel = pd.DataFrame({"permno": [1, 2], "Post": [False, False]})
    assert len(gd.refuse_post_period(panel)) == 2


# --------------------------------------------------------------------------- #
# 2. it cannot invent a threshold                                              #
# --------------------------------------------------------------------------- #

def test_a_null_threshold_stops_the_diagnostic():
    """The state G4 and G6 were in before 2026-08-19 — R3 must stop, not default."""
    with pytest.raises(gd.MissingThreshold) as e:
        gd.threshold(cfg(d_b_mass_share_min=None), "d_b_mass_share_min")
    assert "specification search" in str(e.value)


def test_a_missing_threshold_stops_the_diagnostic():
    c = copy.deepcopy(BASE)
    del c["gate0_thresholds"]["mde_sigma_max"]
    with pytest.raises(gd.MissingThreshold):
        gd.threshold(c, "mde_sigma_max")


def test_every_line_reads_its_number_from_config():
    assert gd.threshold(BASE, "sd_L_min") == 0.25
    assert gd.threshold(BASE, "surprise_coverage_min") == 0.95
    assert gd.threshold(BASE, "d_b_mass_share_min") == 0.50


# --------------------------------------------------------------------------- #
# G1                                                                           #
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("usable,verdict", [(96, "PASS"), (95, "PASS"), (94, "FAIL")])
def test_g1_coverage_against_the_plan_line(usable, verdict):
    r = gd.g1_surprise_coverage(
        {"n_scheduled": 100, "n_usable_S": usable, "fomc_complete": True}, BASE)
    assert r["verdict"] == verdict


def test_g1_reports_fomc_completeness_separately():
    """Plan §9 makes FOMC unconditional: 'FOMC series complete regardless'."""
    r = gd.g1_surprise_coverage(
        {"n_scheduled": 100, "n_usable_S": 50, "fomc_complete": True}, BASE)
    assert r["verdict"] == "FAIL" and r["facts"]["fomc_series_complete"] is True


# --------------------------------------------------------------------------- #
# G2 — the decisive line                                                       #
# --------------------------------------------------------------------------- #

def sweep(sd_by_w, corr=0.0, se=0.01, n=40, convexp=0.02):
    """Synthesise a sweep whose SD(L̂) at each w is exactly sd_by_w[w].

    ConvExp genuinely varies, as it does in real data: a constant dose makes
    corr(L, ConvExp) undefined, and G2 fails closed on that by design.
    """
    rng = np.random.default_rng(11)
    base = np.linspace(-1, 1, n)
    noise = rng.permutation(base)                    # varies, ~uncorrelated with L
    rows = []
    for w, sd in sd_by_w.items():
        L = base / base.std(ddof=1) * sd
        cx = convexp * (1 + 0.15 * noise) if corr == 0 else convexp * (1 + corr * base)
        for i in range(n):
            rows.append({"w_shrink": w, "permno": 1000 + i, "wave": "W1",
                         "beta_i": 1.0, "se_beta": se, "L": L[i], "ConvExp": cx[i]})
    return pd.DataFrame(rows)


def test_g2_fails_closed_when_the_correlation_is_undefined():
    """Every treated name on an identical dose leaves corr(L, ConvExp) undefined.
    An undefined check is not evidence the condition holds, so a kill-switch must
    fail closed rather than wave it through."""
    s = sweep({0.0: 0.40})
    s["ConvExp"] = 0.02                              # constant dose
    assert gd.g2_shrinkage_window(s, BASE)["facts"]["feasible_w"] == []


def test_g2_finds_a_feasible_window_and_reports_its_width():
    s = sweep({0.0: 0.40, 0.1: 0.35, 0.2: 0.30, 0.3: 0.20})
    r = gd.g2_shrinkage_window(s, BASE)
    assert r["facts"]["feasible_w"] == [0.0, 0.1, 0.2]
    assert r["verdict"] == "PASS"


def test_g2_empty_window_is_a_failure_not_a_shrug():
    """The Plan's own trigger: 'stock-level design fails jointly; portfolio-level
    becomes primary or kill'."""
    r = gd.g2_shrinkage_window(sweep({0.0: 0.10, 0.5: 0.05}), BASE)
    assert r["facts"]["feasible_w"] == [] and r["verdict"] == "FAIL"


def test_g2_knife_edge_window_is_flagged_not_passed():
    """执行手册 §R3: a window narrower than two grid points is FAIL/边缘."""
    r = gd.g2_shrinkage_window(sweep({0.0: 0.40, 0.1: 0.10}), BASE)
    assert r["facts"]["window_width_gridpoints"] == 1 and r["verdict"] == "EDGE"


def test_g2_rejects_a_w_where_the_lever_correlates_with_the_dose():
    """SD(L̂) alone is not enough — L must not just be a relabelled ConvExp."""
    s = sweep({0.0: 0.40}, corr=0.9)
    r = gd.g2_shrinkage_window(s, BASE)
    assert r["facts"]["feasible_w"] == []


def test_g2_rejects_a_w_where_betas_are_too_noisy_to_estimate():
    s = sweep({0.0: 0.40}, se=0.30)      # SE >> ratio_max x SD
    assert gd.g2_shrinkage_window(s, BASE)["facts"]["feasible_w"] == []


def test_g2_only_counts_treated_names():
    s = sweep({0.0: 0.40}, convexp=0.001)          # below convexp_treated_min
    r = gd.g2_shrinkage_window(s, BASE)
    assert r["curve"][0]["n_treated"] == 0 and r["verdict"] == "FAIL"


# --------------------------------------------------------------------------- #
# G3 — and decision D-C                                                        #
# --------------------------------------------------------------------------- #

def test_g3_passes_on_a_healthy_median():
    b = pd.DataFrame({"n_pre_announcements": [30, 40, 50, 60]})
    assert gd.g3_beta_estimability(b, BASE)["verdict"] == "PASS"


def test_g3_failure_is_reported_as_an_empty_g2_window():
    """Decision D-C: median n_pre does not vary with w, so a G3 miss fails at
    every grid point — it is not a standalone line."""
    b = pd.DataFrame({"n_pre_announcements": [5, 6, 7, 8]})
    r = gd.g3_beta_estimability(b, BASE)
    assert r["verdict"] == "FAIL" and r["implies_empty_g2_window"] is True


# --------------------------------------------------------------------------- #
# G4 — the framing gate                                                        #
# --------------------------------------------------------------------------- #

def enriched(pairs):
    return pd.DataFrame([{"permno": p, "ConvExp": cx, "beta_b_loo": loo}
                         for p, cx, loo in pairs])


def test_g4_weighs_by_mass_not_by_headcount():
    """Decision D-A. Three tiny distinct names must not outvote one large
    indistinct one."""
    e = enriched([(1, 0.0006, 1.5), (2, 0.0006, 1.5), (3, 0.0006, 1.5),
                  (4, 0.0200, 1.00)])
    r = gd.g4_basket_distinctiveness(e, None, BASE)
    assert r["facts"]["mass_share_with_D_b_at_or_above_min"] < 0.5
    assert r["verdict"] == "FAIL" and r["framing_gate_triggered"] is True


def test_g4_passes_when_the_majority_of_mass_is_distinct():
    e = enriched([(1, 0.02, 1.4), (2, 0.02, 1.4), (3, 0.01, 1.00)])
    r = gd.g4_basket_distinctiveness(e, None, BASE)
    assert r["verdict"] == "PASS" and r["framing_gate_triggered"] is False


def test_g4_reports_the_factor_tilt_alongside_d_b():
    e = enriched([(1, 0.02, 1.4)])
    basket = pd.DataFrame([{"wave": "W1", "F_tilt": 0.4, "F_tilt_se": 0.1}])
    r = gd.g4_basket_distinctiveness(e, basket, BASE)
    assert r["facts"]["factor_tilt"]["waves_with_F_tilt"] == 1


# --------------------------------------------------------------------------- #
# G5                                                                           #
# --------------------------------------------------------------------------- #

def test_g5_requires_the_decomposed_gammas_not_only_pooled():
    with pytest.raises(gd.MissingThreshold) as e:
        gd.g5_power({"gamma_pooled": 0.2}, BASE)
    assert "gamma_tilt" in str(e.value)


def test_g5_fails_on_the_worst_of_the_three_lines():
    r = gd.g5_power({"gamma_pooled": 0.2, "gamma_tilt": 0.3, "gamma_fac": 0.9}, BASE)
    assert r["verdict"] == "FAIL" and r["facts"]["worst_line"] == 0.9


def test_g5_reports_effective_clusters_as_a_fact_with_no_pass_line():
    """Waves are the clustering dimension and the 2026-08-19 sample decision cut
    their count — so the number is surfaced, but R3 registers no threshold for it."""
    r = gd.g5_power({"gamma_pooled": .2, "gamma_tilt": .2, "gamma_fac": .2},
                    BASE, effective_clusters=6)
    assert r["verdict"] == "PASS"                      # not gated on clusters
    assert r["facts"]["effective_clusters"] == 6
    assert r["cluster_count_below_warning"]


def test_analytic_mde_matches_the_p1_convention_and_falls_with_sample_size():
    small = gd.analytic_mde_sigma(50, 50, 4, 5, 1.5)
    large = gd.analytic_mde_sigma(500, 500, 4, 5, 1.5)
    assert large < small and small > 0


# --------------------------------------------------------------------------- #
# G6                                                                           #
# --------------------------------------------------------------------------- #

def test_holm_adjustment_is_step_down_and_monotone():
    adj = gd.holm_adjust([0.01, 0.04, 0.30])
    assert adj[0] <= adj[1] <= adj[2] and adj[0] == pytest.approx(0.03)


def test_g6_passes_when_all_three_legs_are_flat():
    tests = {leg: {"joint_p": 0.4, "lead_p": [0.5, 0.6]}
             for leg in ("event_time_gamma", "beta_trend", "placebo_in_time")}
    assert gd.g6_pretrend(tests, BASE)["verdict"] == "PASS"


def test_g6_fails_on_a_low_joint_p():
    tests = {"event_time_gamma": {"joint_p": 0.02, "lead_p": [0.5]}}
    assert gd.g6_pretrend(tests, BASE)["verdict"] == "FAIL"


def test_a_significant_individual_lead_fails_even_when_the_joint_test_passes():
    """The second clause of decision D-B, not a footnote."""
    tests = {"event_time_gamma": {"joint_p": 0.9, "lead_p": [0.001, 0.5, 0.6]}}
    r = gd.g6_pretrend(tests, BASE)
    assert r["verdict"] == "FAIL"
    assert r["facts"]["legs"]["event_time_gamma"]["joint_pass"] is True


def test_g6_carries_its_power_caveat_into_the_report():
    tests = {"event_time_gamma": {"joint_p": 0.9, "lead_p": []}}
    assert "failure to reject" in gd.g6_pretrend(tests, BASE)["facts"]["caveat"]


# --------------------------------------------------------------------------- #
# 3. it cannot recommend anything                                              #
# --------------------------------------------------------------------------- #

def all_six():
    return {
        "G1": gd.g1_surprise_coverage({"n_scheduled": 100, "n_usable_S": 97,
                                       "fomc_complete": True}, BASE),
        "G2": gd.g2_shrinkage_window(sweep({0.0: .40, 0.1: .35, 0.2: .30}), BASE),
        "G3": gd.g3_beta_estimability(pd.DataFrame({"n_pre_announcements": [40, 50]}), BASE),
        "G4": gd.g4_basket_distinctiveness(enriched([(1, .02, 1.4), (2, .01, 1.0)]),
                                           None, BASE),
        "G5": gd.g5_power({"gamma_pooled": .2, "gamma_tilt": .3, "gamma_fac": .4},
                          BASE, effective_clusters=40, exit_d_bar=0.25),
        "G6": gd.g6_pretrend({"event_time_gamma": {"joint_p": .4, "lead_p": [.5]}}, BASE),
    }


def test_the_report_states_facts_and_verdicts_and_never_recommends():
    """执行手册 §R3: 报告只陈述事实与 PASS/FAIL, 不写"建议继续/放弃"."""
    md = gd.render_report(all_six(), dropped_post_rows=120).lower()
    for word in ("recommend", "we suggest", "should continue", "should abandon",
                 "建议继续", "建议放弃"):
        assert word not in md


def test_the_report_carries_all_six_sections_for_the_contract():
    md = gd.render_report(all_six())
    for k in ("G1", "G2", "G3", "G4", "G5", "G6"):
        assert re.search(rf"^## {k} — ", md, re.M)


def test_the_report_says_how_many_post_rows_were_excluded():
    assert "120 post-period rows were excluded" in gd.render_report(all_six(), 120)


def test_run_writes_both_artifacts_and_returns_the_verdicts(tmp_path):
    verdicts = gd.run(all_six(), tmp_path, dropped_post_rows=7)
    assert set(verdicts) == {"G1", "G2", "G3", "G4", "G5", "G6"}
    assert (tmp_path / "gate_report.md").exists()
    j = json.loads((tmp_path / "gate_report.json").read_text())
    assert j["dropped_post_rows"] == 7 and j["lines"]["G2"]["verdict"] == "PASS"


def test_the_emitted_report_satisfies_the_frozen_gate_report_contract(tmp_path):
    """End to end: the artifact R3 hands to GATE-PREREG validates mechanically."""
    import subprocess
    gd.run(all_six(), tmp_path)
    r = subprocess.run([sys.executable, str(ROOT / "ops" / "runner" / "contracts.py"),
                        "gate_report", str(tmp_path / "gate_report.md")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
