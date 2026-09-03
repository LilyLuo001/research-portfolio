import importlib.util
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
