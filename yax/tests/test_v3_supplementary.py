import importlib.util
import json
import math
import sys
from pathlib import Path

import numpy as np


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
