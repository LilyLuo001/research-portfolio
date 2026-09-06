import importlib.util
import json
import pathlib
import sys

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[2]
CORE_PATH = ROOT / "yax/analysis/postoutcome_v51_interpretation_audit/v51_interpretation_core.py"
RUNNER_PATH = ROOT / "yax/analysis/postoutcome_v51_interpretation_audit/run_v51_interpretation_audit.py"
SPEC = importlib.util.spec_from_file_location("v51_interpretation_core_test", CORE_PATH)
CORE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CORE
SPEC.loader.exec_module(CORE)


def test_fg_ae_reparameterization_preserves_linear_predictor():
    b = np.array([-0.04, 0.03])
    cov = np.array([[0.0002, -0.00008], [-0.00008, 0.00022]])
    result = CORE.transform_fg_to_ae(b, cov, 0.88, 0.32, 1.05, 0.71)
    a = np.array([-1.0, 0.2, 1.4])
    e = np.array([0.1, -0.8, 1.2])
    means = {"A": 0.2, "E": -0.1, "F": 0.05, "G": 0.15}
    scales = {"A": 1.05, "E": 0.71, "F": 0.88, "G": 0.32}
    assert CORE.predictor_identity(a, e, means, scales, b, result["coefficient_raw"]) < 1e-14


def test_covariance_transform_is_symmetric_positive():
    result = CORE.transform_fg_to_ae(
        np.array([-0.04, 0.03]),
        np.array([[0.0002, -0.00008], [-0.00008, 0.00022]]),
        0.88, 0.32, 1.05, 0.71,
    )
    assert np.allclose(result["covariance_raw"], result["covariance_raw"].T)
    assert np.linalg.eigvalsh(result["covariance_raw"]).min() > 0


def test_runner_contains_no_outcome_estimator_call_or_new_multiplier_generation():
    source = RUNNER_PATH.read_text()
    prohibited = (
        "fit_with_influence(",
        "fit_grouped_logit_fe(",
        "wild_score_summary(",
        "rng.choice(",
        "default_rng(",
    )
    for token in prohibited:
        assert token not in source


def test_weighted_covariance_contributions_sum_to_one():
    weights = np.array([1.0, 2.0, 3.0])
    x = np.array([-1.0, 0.0, 2.0])
    y = np.array([0.5, 1.5, -0.5])
    target = 0.25 * x + 0.75 * y
    shares = CORE.covariance_contributions(target, {"x": x, "y": y}, {"x": 0.25, "y": 0.75}, weights)
    assert abs(sum(shares.values()) - 1) < 1e-12


def test_committed_reparameterization_is_exact_and_bounded():
    directory = ROOT / "yax/analysis/postoutcome_v51_interpretation_audit"
    result = json.loads((directory / "YAX_V51_FG_TO_AE_REPARAMETERIZATION.json").read_text())
    assert result["classification"] == "AE-R1"
    assert result["new_labor_outcome_model_estimated"] is False
    assert result["support_occupations"] == 444
    assert result["maximum_absolute_linear_predictor_difference"] < 1e-12
    assert result["terms"][0]["normal_95_ci_per_weighted_sd"][0] < 0
    assert result["terms"][0]["normal_95_ci_per_weighted_sd"][1] > 0
    assert result["terms"][1]["normal_95_ci_per_weighted_sd"][1] < 0
    assert result["terms"][0]["wild_score_interval"] is None
    assert result["a_minus_e_original_unit_contrast"]["exact_transformed_existing_G_wild_score_95_ci"][0] > 0


def test_treatment_stability_is_partial_and_uses_no_labor_outcome():
    directory = ROOT / "yax/analysis/postoutcome_v51_interpretation_audit"
    result = json.loads((directory / "YAX_V51_TREATMENT_DIAGNOSTICS_DETAIL.json").read_text())
    assert result["classification"] == "G-PARTIAL"
    assert result["labor_outcomes_used"] is False
    rows = {row["construction"]: row for row in result["rows"]}
    assert rows["G_minus_alpha"]["employment_weighted_pearson"] < 0.90
    assert rows["G_minus_beta"]["employment_weighted_pearson"] > 0.99
    assert rows["G_minus_broad"]["employment_weighted_pearson"] > 0.97


def test_decision_and_manuscript_preserve_bounded_frame():
    directory = ROOT / "yax/analysis/postoutcome_v51_interpretation_audit"
    decision = (directory / "YAX_V51_G_STORY_DECISION.md").read_text()
    manuscript = (ROOT / "yax/manuscript/v5_1/YAX_MANUSCRIPT_v5_1_INTERPRETATION_AUDIT.md").read_text()
    original_title = (ROOT / "yax/manuscript/v5_1/YAX_MANUSCRIPT_v5_1_CLEAN.md").read_text().splitlines()[0]
    assert "Decision: FRAME-G2" in decision
    assert manuscript.splitlines()[0] == original_title
    assert "No new labor-outcome model" in decision
    assert "G-PARTIAL" in manuscript
    assert "does not imply that AIOE has no effect" in manuscript


def test_power_reconciliation_discloses_both_optimistic_ratios():
    text = (ROOT / "yax/analysis/postoutcome_v51_interpretation_audit/YAX_V51_POWER_CALIBRATION_RECONCILIATION.md").read_text()
    assert "HEADLINE-P2" in text
    assert "PAIRED-P2" in text
    assert "3.649" in text
    assert "3.167" in text
    assert "does not isolate a unique cause" in text


def test_loco_is_feasibility_only_and_not_executed():
    text = (ROOT / "yax/analysis/postoutcome_v51_interpretation_audit/YAX_V51_LOCO_FEASIBILITY_NOTE.md").read_text()
    assert "LOCO-WORTH-OWNER-DECISION" in text
    assert "LOCO was not executed" in text
