from __future__ import annotations

import hashlib
import importlib.util
import json
import pathlib

import numpy as np
import pandas as pd


ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "yax" / "analysis" / "postoutcome_v4_supplementary" / "run_v4_alignment.py"
SPEC = importlib.util.spec_from_file_location("v4_alignment_test_module", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_support_hash_is_sorted_newline_sha256() -> None:
    expected = hashlib.sha256(b"0010\n0020\n0100\n").hexdigest()
    assert MODULE.support_hash(["0100", "0010", "0020"]) == expected


def test_finite_support_is_sorted_intersection() -> None:
    base = ["30", "10", "20", "40"]
    exposure = {"10": 1.0, "20": np.nan, "30": 2.0, "40": 3.0}
    webb = {"10": 0.0, "20": 1.0, "30": 1.0, "40": np.nan}
    assert MODULE.finite_support(base, exposure, webb) == ["10", "30"]


def test_authorized_stages_only() -> None:
    text = PATH.read_text()
    assert 'choices=("support_and_common", "categorical_event")' in text
    for forbidden in ("alternative_reference", "alternative_window", "remote_interaction"):
        assert forbidden not in text


def test_categorical_event_includes_q2_through_q5_and_dynamic_webb() -> None:
    text = PATH.read_text()
    assert "for quintile in (2, 3, 4, 5):" in text
    assert 'labels.append(f"Webb_z_x_{month}")' in text
    assert "q5_indices" in text


def test_stored_support_audit_and_common_result() -> None:
    out = PATH.parent
    receipt = json.loads((out / "TABLE5B_SUPPORT_RECEIPT.json").read_text())
    assert receipt["native_support_identical"] is False
    assert receipt["common_support_n"] == 444
    assert np.isclose(receipt["common_support_employment_coverage"], 0.831420875609175)
    assert receipt["all_six_common_result_signs_negative"] is True
    assert receipt["all_six_common_intervals_exclude_zero_negative"] is False
    results = pd.read_csv(out / "TABLE5B_COMMON_SUPPORT_RESULTS.csv")
    assert results["n_occupations"].nunique() == 1
    assert results["support_hash_sha256"].nunique() == 1
    assert (results["coefficient_log_points"] < 0).all()
    assert (results["wild_score_ci_upper"] < 0).sum() == 5


def test_stored_categorical_event_pretrend_result() -> None:
    result = json.loads((PATH.parent / "CATEGORICAL_Q5_Q1_EVENT_STUDY_RESULT.json").read_text())
    assert result["pre_coefficients_tested"] == 65
    assert result["simultaneous_pre_intervals_excluding_zero"] == 0
    assert np.isclose(result["joint_pretrend_wild_score_p_value"], 0.929)
    assert result["q2_q4_monthly_interactions_included"] is True
    assert result["post_pointwise_negative_intervals_excluding_zero"] == 8
    assert result["post_pointwise_positive_intervals_excluding_zero"] == 0
