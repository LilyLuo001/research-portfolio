import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "yax/analysis/postoutcome_v3_supplementary/run_v3_supplementary.py"
SPEC = importlib.util.spec_from_file_location("yax_v3_supplementary_test", SCRIPT)
V3 = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = V3
SPEC.loader.exec_module(V3)


def test_headline_information_decomposition_matches_schur_complement():
    n_occ, n_month = 10, 8
    post = np.array([False, False, False, False, True, True, True, True])
    quintile = np.array([1, 1, 2, 2, 3, 3, 4, 4, 5, 5])
    computerization = np.linspace(-1.5, 1.5, n_occ)
    columns = []
    for value in (2, 3, 4, 5):
        columns.append(((quintile[:, None] == value) & post[None, :]).reshape(-1).astype(float))
    columns.append((computerization[:, None] * post[None, :]).reshape(-1))
    regressors = np.column_stack(columns)

    occ_effect = np.linspace(-0.35, 0.35, n_occ)[:, None]
    month_effect = np.linspace(-0.18, 0.18, n_month)[None, :]
    linear = occ_effect + month_effect + (regressors @ np.array([0.03, -0.02, -0.06, -0.11, 0.04])).reshape(n_occ, n_month)
    probability = 1.0 / (1.0 + np.exp(-linear))
    total = np.full((n_occ, n_month), 250.0)
    young = total * probability
    older = total - young

    fit, _ = V3.FROZEN.fit_with_influence(young, older, regressors)
    result = V3.information_contributions(
        young, older, regressors, fit.fitted_probability, target=3
    )
    assert fit.converged
    assert np.isclose(result["shares"].sum(), 1.0)
    assert np.all(result["shares"] >= 0)
    assert result["relative_schur_gap"] < 1e-10
    assert np.isclose(result["total_information"], result["schur_from_bread"])
    assert 1 <= result["effective_support"] <= n_occ


def test_paired_mde_is_log_scale_and_relative_translation_is_distinct():
    artifact = json.loads((ROOT / "yax/power/PAIRED_DIFFERENCE_PRECISION_v2.json").read_text())
    log_points = artifact["mde_delta_80"]["log_points"]
    relative = artifact["mde_delta_80"]["relative_magnitude"]
    assert math.isclose(100.0 * (math.exp(log_points) - 1.0), 100.0 * relative)
    assert not math.isclose(log_points, relative)


def test_supplementary_plan_declares_exactly_one_remote_form_and_pretrend_test():
    plan = (
        ROOT
        / "yax/analysis/postoutcome_v3_supplementary/POSTOUTCOME_V3_ANALYSIS_PLAN.md"
    ).read_text()
    assert "Run exactly one model" in plan
    assert "AI_z x Remote_z" in plan
    assert "all 65 non-reference" in plan
    assert "max_k |beta_hat_k / analytic_SE_k|" in plan
    assert V3.LABEL in plan


def test_survey_feasibility_conclusion_does_not_erase_available_household_ids():
    source = SCRIPT.read_text()
    assert "the extract contains CPSID, SERIAL, CPSIDP, and MISH" in source
    assert '"stratum/PSU variables or replicate weights.' in source


def test_completed_headline_support_outputs_are_complete_and_schur_valid():
    out = ROOT / "yax/analysis/postoutcome_v3_supplementary"
    summary = pd.read_csv(out / "HEADLINE_INFORMATION_SUPPORT_SUMMARY.csv")
    bridge = pd.read_csv(out / "CONTINUOUS_VS_HEADLINE_SUPPORT.csv")
    assert len(summary) == 12
    assert len(bridge) == 4
    assert set(summary["analysis_status"]) == {V3.LABEL}
    assert set(bridge["analysis_status"]) == {V3.LABEL}
    assert summary["relative_schur_gap"].max() < 1e-8
    assert bridge["stored_test_b_effective_gap"].max() < 1e-6
    assert bridge["stored_test_b_top_five_gap"].max() < 1e-8


def test_completed_validator_split_and_survey_gate_are_complete():
    out = ROOT / "yax/analysis/postoutcome_v3_supplementary"
    split = pd.read_csv(out / "TEST_A_VALIDATOR_SPLIT_SUMMARY.csv")
    survey = json.loads((out / "CPS_SURVEY_UNCERTAINTY_FEASIBILITY.json").read_text())
    assert len(split) == 12
    assert set(split["occupations"]) == {348}
    assert set(split["analysis_status"]) == {V3.LABEL}
    assert survey["design_consistent_resampling_feasible"] is False
    assert survey["resampling_executed"] is False
    assert survey["available_identifier_categories"]["household_identifiers"] == ["CPSID", "SERIAL"]
    assert survey["available_identifier_categories"]["psu_identifiers"] == []
    assert survey["available_identifier_categories"]["stratum_identifiers"] == []


def test_remote_and_joint_pretrend_are_single_predeclared_executions():
    out = ROOT / "yax/analysis/postoutcome_v3_supplementary"
    remote = json.loads((out / "REMOTE_INTERACTION_RESULT.json").read_text())
    joint = json.loads((out / "JOINT_PRETREND_RESULT.json").read_text())
    assert remote["analysis_status"] == V3.LABEL
    assert remote["analysis_id"] == "S4"
    assert remote["occupations"] == 408
    assert set(remote["coefficients"]) == {
        "AI_z_x_post",
        "Webb_z_x_post",
        "Remote_z_x_post",
        "AI_z_x_Remote_z_x_post",
    }
    assert joint["analysis_status"] == V3.LABEL
    assert joint["analysis_id"] == "S5"
    assert joint["tested_coefficients"] == 65
    assert joint["maximum_confirmatory_coefficient_reproduction_gap"] == 0
    assert 0 <= joint["bootstrap_p_value"] <= 1
