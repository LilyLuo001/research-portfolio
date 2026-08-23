import json
import pathlib
import sys
from types import SimpleNamespace

import pandas as pd
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MAPPING = ROOT / "mapping"
sys.path.insert(0, str(MAPPING))

from run_s1_construct_validity import draw, evaluate, prestratum  # noqa: E402


def spec():
    return json.loads((MAPPING / "s1_construct_validity_spec_20260823.json").read_text())


def synthetic_inputs(tmp_path):
    onet_rows = []
    wage_rows = []
    families = [f"{value:02d}" for value in range(11, 33)]
    verbs = ["Operate", "Interview", "Analyze", "Monitor", "Write", "Repair"]
    task_id = 0
    for family in families:
        for within in range(10):
            task_id += 1
            identifier = str(task_id)
            soc = f"{family}-1000.00"
            onet_rows.append({
                "onet_soc": soc,
                "task_id": identifier,
                "task_statement": f"{verbs[within % len(verbs)]} records for task {within}",
                "task_type": "Core" if within < 7 else "Supplemental",
                "primary_usable": "true",
            })
            for vintage in ("2019", "2021"):
                wage_rows.append({
                    "vintage": vintage,
                    "onet_soc": soc,
                    "task_id": identifier,
                    "task_annual_wage_bill_allocation": str(1 + within),
                    "allocation_usable": "true",
                })
    onet = tmp_path / "onet.csv"
    wage = tmp_path / "wage.csv"
    pd.DataFrame(onet_rows).to_csv(onet, index=False)
    pd.DataFrame(wage_rows).to_csv(wage, index=False)
    frozen = spec()
    frozen["sample_provenance"]["frame_expected_unique_tasks"] = 220
    frozen_path = tmp_path / "spec.json"
    frozen_path.write_text(json.dumps(frozen))
    return frozen_path, onet, wage


def test_prestratum_priority_is_frozen():
    frozen = spec()
    assert prestratum("Operate equipment and write logs", frozen) == "physical_manual"
    assert prestratum("Interview and advise clients", frozen) == "interpersonal_service"
    assert prestratum("Analyze data and prepare reports", frozen) == "document_data"
    assert prestratum("Monitor conditions", frozen) == "other"


def test_one_draw_has_120_unique_tasks_and_no_replacement(tmp_path):
    frozen, onet, wage = synthetic_inputs(tmp_path)
    private = tmp_path / "private"
    receipt = draw(SimpleNamespace(
        spec=frozen,
        onet_timeshares=onet,
        task_wage_allocations=wage,
        private_dir=private,
        receipt=tmp_path / "receipt.json",
    ))
    sample = pd.read_csv(private / "s1_sample_120.csv", dtype=str)
    assert len(sample) == sample["onet_task_id"].nunique() == 120
    assert sample["major_family"].nunique() == 22
    assert sorted(sample.groupby("major_family").size().unique()) == [5, 6]
    assert receipt["task_replacement_count"] == 0
    assert receipt["selected_task_text_inspected_before_draw"] is False


def test_non_evaluable_rows_cannot_smuggle_constructed_instances(tmp_path):
    frozen, onet, wage = synthetic_inputs(tmp_path)
    private = tmp_path / "private"
    draw(SimpleNamespace(
        spec=frozen,
        onet_timeshares=onet,
        task_wage_allocations=wage,
        private_dir=private,
        receipt=tmp_path / "draw.json",
    ))
    annotations = pd.read_csv(private / "s1_construct_annotations_template.csv", dtype=str).fillna("")
    annotations["evaluable_class"] = "requires_physical_world_action"
    annotations["scoring_class"] = "not_currently_scoreable"
    annotations["construct_status"] = "NON_EVALUABLE"
    annotations["main_failure_mode"] = "physical_world_action"
    annotations["concise_rationale"] = "Complete task requires physical execution."
    annotations["task_boundary_fidelity"] = "not_applicable"
    annotations["work_product_fidelity"] = "not_applicable"
    annotations["domain_context_fidelity"] = "not_applicable"
    annotations["tool_input_fidelity"] = "not_applicable"
    annotations["difficulty_distortion"] = "not_applicable"
    annotations["added_task_content_risk"] = "not_applicable"
    annotations["omitted_essential_content_risk"] = "not_applicable"
    annotations_path = private / "annotations.csv"
    annotations.to_csv(annotations_path, index=False)
    receipt = evaluate(SimpleNamespace(
        spec=frozen,
        private_dir=private,
        annotations=annotations_path,
        recommendation="NOT_YET_EVALUABLE",
        receipt=tmp_path / "result.json",
    ))
    assert receipt["non_evaluable_total"] == 120
    assert receipt["construct_status_counts"]["PASS"] == 0
    assert receipt["formal_s1_gate_result"] == "UNRESOLVED"
    annotations.loc[0, "occupational_activity"] = "A substitute digital task"
    annotations.to_csv(annotations_path, index=False)
    with pytest.raises(ValueError, match="substitute instance"):
        evaluate(SimpleNamespace(
            spec=frozen,
            private_dir=private,
            annotations=annotations_path,
            recommendation="NOT_YET_EVALUABLE",
            receipt=tmp_path / "bad.json",
        ))


def test_protocol_keeps_threshold_unsigned_and_hard_stops_closed():
    frozen = spec()
    assert frozen["threshold"] is None
    assert frozen["threshold_status"] == "NEED_PROSPECTIVE_PI_THRESHOLD_SIGNATURE"
    assert not any(frozen["hard_stops"].values())


def test_real_s1_receipts_are_aggregate_only_and_unresolved():
    draw_receipt = json.loads((MAPPING / "s1_draw_receipt_20260823.json").read_text())
    result = json.loads((MAPPING / "s1_construct_validity_result_receipt_20260823.json").read_text())
    assert draw_receipt["sample_tasks"] == 120
    assert draw_receipt["frame_tasks"] == 15274
    assert draw_receipt["task_replacement_count"] == 0
    assert draw_receipt["selected_task_text_inspected_before_draw"] is False
    assert result["evaluable_class_counts"] == {
        "directly_executable_digital": 0,
        "executable_with_construct_valid_simulated_inputs": 14,
        "executable_with_supplied_files_data": 10,
        "otherwise_not_currently_evaluable": 2,
        "requires_interpersonal_interaction": 57,
        "requires_physical_world_action": 35,
        "requires_unavailable_proprietary_system": 2,
    }
    assert result["construct_status_counts"] == {
        "NON_EVALUABLE": 96, "PASS": 13, "REVISE": 11
    }
    assert result["formal_s1_gate_result"] == "UNRESOLVED"
    assert result["threshold"] is None
    assert result["recommendation"] == "PARTIAL_IDENTIFICATION_ONLY"
    assert result["model_or_api_calls"] == 0
    assert result["outcomes_opened"] is False
    assert result["realized_spend_usd"] == 0
    encoded = json.dumps({"draw": draw_receipt, "result": result})
    assert "task_statement" not in encoded
    assert "occupational_activity" not in encoded
    assert "/usr3/" not in encoded
