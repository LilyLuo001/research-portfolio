import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
RECEIPT = ROOT / "data_raw" / "w5_dose_panel_blocker_receipt.json"


def test_w5_blocker_receipt_is_fail_closed_and_dependency_complete():
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert receipt["status"] == "BLOCKED_MISSING_FROZEN_W3_W4_INPUTS"
    assert set(receipt["input_commits"]) == {
        "seat_c_standard_freeze",
        "price_redteam",
        "gate1_integration",
        "event_evidence",
        "phase_a_contract",
        "phase_a_portability_fix",
    }
    assert receipt["blocking_inputs"]["mapping_a_gdpval"]["status"] == "NOT_EXECUTED"
    assert receipt["blocking_inputs"]["w4_capability_cost_panel"]["status"] == "MISSING"
    result = receipt["fail_closed_result"]
    assert result["real_panel_constructed"] is False
    assert result["private_panel_committed"] is False
    assert result["identification_gate_run"] is False
    assert result["identification_result"] is None
    assert result["outcome_data_opened"] is False
    assert result["post_event_outcomes_opened"] is False
    assert result["synthetic_or_static_scores_substituted"] is False


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
