import importlib.util
import pathlib
import sys

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[2]
V51 = ROOT / "yax/analysis/postoutcome_v51_referee_repair"
SPEC = importlib.util.spec_from_file_location("yax_v51_core_test", V51 / "v51_core.py")
CORE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CORE
SPEC.loader.exec_module(CORE)


def test_cohen_kappa_includes_three_frozen_direction_categories():
    a = np.array([-1, -1, 0, 0, 1, 1])
    b = np.array([-1, 1, 0, 1, 1, -1])
    result = CORE.cohen_kappa(a, b, np.ones(len(a)))
    assert np.isclose(result["raw_exact_agreement"], 0.5)
    assert np.isclose(result["opposite_sign_conflict"], 2 / 6)
    assert np.isclose(result["any_tie"], 2 / 6)
    assert np.isfinite(result["cohen_kappa"])


def test_cohen_kappa_is_one_for_nonconstant_identical_labels():
    labels = np.array([-1, 0, 1, -1, 1])
    result = CORE.cohen_kappa(labels, labels, np.arange(1, 6, dtype=float))
    assert np.isclose(result["cohen_kappa"], 1.0)
    assert np.isclose(result["raw_exact_agreement"], 1.0)


def test_fleiss_kappa_is_one_for_unanimous_varied_items():
    labels = np.array([
        [-1, -1, -1, -1, -1, -1],
        [0, 0, 0, 0, 0, 0],
        [1, 1, 1, 1, 1, 1],
    ])
    result = CORE.fleiss_kappa(labels, np.ones(3))
    assert np.isclose(result["fleiss_kappa"], 1.0)
    assert np.isclose(result["observed_pair_agreement"], 1.0)


def test_weighted_average_rank_correlation_is_distinct_and_deterministic():
    x = np.array([3.0, 1.0, 1.0, 4.0])
    y = np.array([2.0, 0.0, 1.0, 5.0])
    weights = np.array([1.0, 2.0, 3.0, 4.0])
    first = CORE.weighted_corr(CORE.average_rank(x), CORE.average_rank(y), weights)
    second = CORE.weighted_corr(CORE.average_rank(x), CORE.average_rank(y), weights)
    assert np.isclose(first, second)
    assert -1 <= first <= 1


def test_two_way_covariance_uses_inclusion_exclusion_and_is_symmetric():
    bread = np.eye(2)
    scores = np.array([
        [1.0, 0.5], [-0.3, 0.2], [0.1, -0.4], [-0.8, -0.3],
    ])
    occupation = np.array([0, 0, 1, 1])
    month = np.array([0, 1, 0, 1])
    result = CORE.two_way_cluster_covariance(bread, scores, occupation, month)
    assert result["occupation_clusters"] == 2
    assert result["month_clusters"] == 2
    assert result["nonzero_cells"] == 4
    assert np.allclose(result["covariance"], result["covariance"].T)


def test_wild_score_summary_uses_common_reproducible_multipliers():
    estimates = np.array([-0.2, 0.05])
    ses = np.array([0.08, 0.04])
    influence = np.array([
        [0.02, 0.01], [-0.01, 0.02], [0.03, -0.01], [-0.02, -0.02],
    ])
    first = CORE.wild_score_summary(estimates, ses, influence, 2026090501, 99)
    second = CORE.wild_score_summary(estimates, ses, influence, 2026090501, 99)
    assert first["rows"] == second["rows"]
    assert np.allclose(first["centered_shift_covariance"], second["centered_shift_covariance"])


def test_fg_plan_freezes_one_continuous_model_and_prohibits_search():
    plan = (V51 / "YAX_V51_FG_JOINT_MODEL_PLAN.md").read_text()
    assert "Exactly one new labor-outcome specification is authorized" in plan
    assert "F_z × Post" in plan and "G_z × Post" in plan and "Webb_z × Post" in plan
    assert "999 common multiplier draws" in plan
    assert "No F/G rotation" in plan
    execution = (V51 / "YAX_V51_EXECUTION_PLAN.md").read_text()
    assert "This is a closed, post-outcome exploratory repair" in execution
    assert "No other new labor-outcome regression may be executed" in execution


def test_runner_declares_one_new_model_and_fixed_output_names():
    source = (V51 / "run_v51_repairs.py").read_text()
    assert '"new_labor_outcome_specification_count": 1' in source
    assert "joint_continuous_consensus_F_plus_between_family_G_plus_Webb" in source
    assert "YAX_V51_KAPPA_AGREEMENT.csv" in source
    assert "YAX_V51_TWOWAY_CLUSTER_SENSITIVITY.csv" in source
    assert "FG_SEED = 2026090501" in source


def test_v51_result_bundle_is_all_absent_before_execution_or_complete_afterward():
    result_names = [
        "YAX_V51_FG_JOINT_MODEL_RESULTS.json",
        "YAX_V51_KAPPA_AGREEMENT.csv",
        "YAX_V51_TWOWAY_CLUSTER_SENSITIVITY.csv",
        "YAX_V51_EXECUTION_RECEIPT.json",
    ]
    existing = [(V51 / name).exists() for name in result_names]
    assert not any(existing) or all(existing)
    if all(existing):
        import json

        receipt = json.loads((V51 / "YAX_V51_EXECUTION_RECEIPT.json").read_text())
        assert receipt["new_labor_outcome_specification_count"] == 1
        assert receipt["pre_result_commit"]
