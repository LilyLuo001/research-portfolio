import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
MAPPING = ROOT / "mapping"


def load(name):
    return json.loads((MAPPING / name).read_text(encoding="utf-8"))


def test_recall_freeze_is_independent_and_not_evaluated():
    receipt = load("mapA_v2_recall_audit_receipt.json")
    assert receipt["source_tasks"] == 100
    assert receipt["primary_source_tasks"] == 60
    assert receipt["reserve_source_tasks"] == 40
    assert receipt["initial_pair_assessments"] == 13200
    assert receipt["frozen_pair_assessments"] == 22000
    assert receipt["excluded_classifier_validation_source_tasks"] == 440
    assert receipt["independent_of_all_classifier_splits"] is True
    assert receipt["labels_present"] is False
    assert receipt["recall_at_40"] == "NOT_EVALUABLE"


def test_labeling_preflight_stops_before_spend_and_budget_covers_upper():
    receipt = load("mapA_v2_labeling_preflight_receipt.json")
    assert receipt["status"] == "NEED_PI_BUDGET_AUTHORIZATION"
    assert receipt["realized_spend_usd"] == 0
    assert receipt["inference_calls_made"] == 0
    assert receipt["providers"]["true_vendor_family_independence"] is True
    upper = receipt["aggregate_maximum_100"]["estimated_cost_usd"]["upper_no_cache_all_third_adjudication"]
    assert receipt["requested_budget_cap_usd"] >= upper * 1.5


def test_provider_probe_was_metadata_only_and_no_subscription_lane_is_claimed():
    receipt = load("mapA_v2_provider_metadata_preflight_20260821.json")
    assert receipt["free_metadata_probe"]["inference_calls"] == 0
    assert receipt["incremental_cost_certified_zero"] is False
    assert receipt["independence_assessment"]["achievable"] is True
    assert not any(receipt["provider_subscription_clis_on_scc"].values())


def test_fitting_runner_has_no_locked_label_argument_or_outcome_path():
    source = (MAPPING / "freeze_mapA_v2_prediction.py").read_text(encoding="utf-8")
    assert "--locked" not in source
    assert "dax/analysis/outcomes" not in source
    assert 'allowed_splits={"development", "calibration"}' in source


def test_duration_monitor_preserves_wait_and_zero_coverage():
    receipt = json.loads((ROOT / "capability_panel" / "gdpval_duration_monitor_20260821.json").read_text())
    assert receipt["fallback_eligibility_utc"] == "2026-09-04T13:04:55Z"
    assert receipt["old_waiting_rule_superseded"] is True
    assert receipt["fallback_launched"] is True
    assert receipt["pilot_annotation_launched"] is False
    assert receipt["task_duration_coverage"] == {"covered_tasks": 0, "expected_tasks": 220}
