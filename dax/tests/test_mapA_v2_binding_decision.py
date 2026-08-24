import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
DECISION = ROOT / "mapping" / "mapA_v2_binding_thresholds_20260821.json"


def test_binding_thresholds_match_prospective_pi_decision():
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    assert decision["decision_commit"] == "4577fecab7b4e142cb28d78d4aec0800637c7b05"
    assert decision["approval_scope"] == "blind_validation_only_not_production"
    assert decision["ppv_floor"] == 0.95
    assert decision["false_positive_rate_ceiling"] == 0.05
    assert decision["candidate_recall_k"] == 40
    assert decision["candidate_recall_floor"] == 0.95
    assert decision["adjudication_rate_ceiling"] == 0.20
    assert decision["task_mass_weighted_coverage_floor"] == 0.80
    assert decision["family_coverage_floor"] == 0.70
    assert decision["u_label_treatment"] == "count_as_non_D_for_ppv_and_fpr"


def test_locked_opening_is_one_time_and_failure_is_fail_closed():
    decision = json.loads(DECISION.read_text(encoding="utf-8"))
    assert "exactly_once" in decision["locked_test_opening"]
    assert "blocks_production" in decision["failure_rule"]
    assert "cannot_be_relaxed_post_result" in decision["failure_rule"]


def test_pi15_transport_bounds_are_carried_without_change():
    bounds = json.loads(DECISION.read_text(encoding="utf-8"))["transport_sensitivity_rule"]
    assert bounds == {
        "source": "PI Decision 15",
        "median_crossing_shift_months_max": 1,
        "p90_crossing_shift_months_max": 3,
        "dose_bin_change_share_max": 0.1,
        "attenuation_factor_min": 0.8,
    }
