import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "data_raw" / "w5_dose_panel_blocker_receipt.json"
W3_RECEIPT = ROOT / "mapping" / "mapA_run_receipt.json"
W4_RECEIPT = ROOT / "data_raw" / "w4_preflight_receipt.json"


def test_w5_blocker_receipt_is_fail_closed_and_dependency_complete():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert receipt["status"] == "BLOCKED_UNQUALIFIED_W3_AND_MISSING_W4_MEASUREMENTS"
    assert set(receipt["input_commits"]) == {
        "seat_c_standard_freeze",
        "price_redteam",
        "gate1_integration",
        "event_evidence",
        "phase_a_contract",
        "phase_a_portability_fix",
        "w3_mapping_a",
        "w4_capability_panel",
    }
    assert receipt["input_commits"]["w3_mapping_a"] == (
        "48cfdcacbf24e07a3185e8253785bd31cc65d1f2"
    )
    assert receipt["input_commits"]["w4_capability_panel"] == (
        "2c634087447af61bbd2cdf3031ebe41a9aa4909e"
    )
    mapping = receipt["blocking_inputs"]["mapping_a_gdpval"]
    assert mapping["status"] == "EXECUTED_AUDIT_PENDING_NOT_ACCEPTED"
    assert mapping["total_rows"] == 19259
    assert mapping["accepted_rows"] == 0
    assert mapping["unaudited_grade_c_queue_rows"] == 37
    assert mapping["unmatched_rows"] == 19222
    assert (
        mapping["accepted_rows"]
        + mapping["unaudited_grade_c_queue_rows"]
        + mapping["unmatched_rows"]
        == mapping["total_rows"]
    )
    capability = receipt["blocking_inputs"]["w4_capability_cost_panel"]
    assert capability["status"] == "PREFLIGHT_BLOCKED_NO_REAL_MEASUREMENTS"
    assert capability["task_universe_rows"] == 220
    assert capability["duration_covered_rows"] == 0
    assert capability["duration_missing_rows"] == 220
    assert capability["captured_rows"] == 0
    assert capability["blocked_rows"] == 220
    assert capability["realized_cost_usd"] == 0
    assert capability["full_capture_allowed"] is False
    result = receipt["fail_closed_result"]
    assert result["real_panel_constructed"] is False
    assert result["private_panel_committed"] is False
    assert result["identification_gate_run"] is False
    assert result["identification_result"] is None
    assert result["outcome_data_opened"] is False
    assert result["post_event_outcomes_opened"] is False
    assert result["synthetic_or_static_scores_substituted"] is False


def test_w5_blocker_counts_reconcile_to_integrated_w3_w4_receipts():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    w3 = json.loads(W3_RECEIPT.read_text(encoding="utf-8"))
    w4 = json.loads(W4_RECEIPT.read_text(encoding="utf-8"))
    mapping = receipt["blocking_inputs"]["mapping_a_gdpval"]
    capability = receipt["blocking_inputs"]["w4_capability_cost_panel"]

    assert mapping["accepted_rows"] == w3["results"]["accepted"] == 0
    assert mapping["unaudited_grade_c_queue_rows"] == w3["results"]["queued"] == 37
    assert mapping["unmatched_rows"] == w3["results"]["unmatched"] == 19222
    assert w3["adjudication_queue"]["machine_judgments_certified_as_audited"] is False
    assert capability["duration_covered_rows"] == w4["duration"]["covered_task_ids"] == 0
    assert capability["duration_missing_rows"] == w4["duration"]["missing_task_ids"] == 220
    assert capability["captured_rows"] == w4["captured_rows"] == 0
    assert capability["blocked_rows"] == w4["blocked_rows"] == 220
    assert capability["realized_cost_usd"] == w4["budget"]["realized_cost_usd"] == 0


def test_w5_blocker_receipt_keeps_mapped_and_resolved_mass_distinct():
    summary = json.loads(RECEIPT.read_text(encoding="utf-8"))[
        "qualified_input_summary"
    ]
    assert summary["mapped_component_mass_share"] > summary[
        "fully_resolved_component_mass_share"
    ]
    assert summary["bounded_provisional_component_mass_share"] > 0
    total = sum(summary[field] for field in (
        "fully_resolved_component_mass_share",
        "bounded_provisional_component_mass_share",
        "unresolved_component_mass_share",
        "absent_component_mass_share",
    ))
    assert abs(total - 1.0) < 1e-9
