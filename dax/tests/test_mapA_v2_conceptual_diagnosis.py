import hashlib
import json
import pathlib
import sys

import numpy as np

MAPPING = pathlib.Path(__file__).resolve().parents[1] / "mapping"
sys.path.insert(0, str(MAPPING))

from mapA_v3_source_audit import (  # noqa: E402
    classify_modality,
    relevant_candidate_indices,
    select_sources,
)


def test_source_modality_is_mechanical_and_stable():
    assert classify_modality("Operate and clean production machinery") == "physical_manual"
    assert classify_modality("Advise clients regarding available services") == "interpersonal_service"
    assert classify_modality("Analyze data and write technical reports") == "technical_analytic"


def test_relevant_candidates_are_union_of_three_top_ten_lists():
    targets = [f"G{i:02d}" for i in range(25)]
    dense = np.arange(25, dtype=float)
    lexical = dense[::-1].copy()
    selected = relevant_candidate_indices(dense, lexical, targets)
    assert set(range(15, 25)) <= set(selected)
    assert set(range(10)) <= set(selected)
    assert len(selected) <= 25


def test_source_selection_uses_development_only_and_excludes_prior_sources():
    statements = {
        "P1": "Operate machinery", "P2": "Clean equipment", "P3": "Load products",
        "I1": "Advise clients", "I2": "Teach students", "I3": "Counsel families",
        "T1": "Analyze records", "T2": "Research systems", "T3": "Write reports",
    }
    rows = []
    for index, source in enumerate(statements):
        rows.append({
            "onet_task_id": source,
            "major_soc_family": f"{index + 10}",
            "split": "development" if source != "T3" else "locked_test",
        })
    rows.append({"onet_task_id": "T3", "major_soc_family": "99", "split": "development"})
    selected = select_sources(rows, statements, {"P3", "I3", "T3"})
    assert len(selected) == 6
    assert {row["modality"] for row in selected} == {
        "physical_manual", "interpersonal_service", "technical_analytic"
    }
    assert not ({"P3", "I3", "T3"} & {row["onet_task_id"] for row in selected})


def test_release_receipts_and_version_history_preserve_v2():
    diagnosis = json.loads((MAPPING / "mapA_v2_conceptual_diagnosis_receipt_20260823.json").read_text())
    source = json.loads((MAPPING / "mapA_v3_source_audit_result_receipt_20260823.json").read_text())
    history = json.loads((MAPPING / "mapping_version_status_20260823.json").read_text())
    assert diagnosis["relation_counts_unchanged"] == {"D": 0, "F": 24, "N": 36, "U": 0}
    assert diagnosis["overlapping_structural_cause_counts"]["taxonomy_definition_too_strict"] == 0
    assert source["source_tasks"] == 6
    assert source["candidate_pairs_inspected"] == 108
    assert source["sources_with_any_plausible_direct_substitute"] == 1
    assert source["interpretation_limits"]["formal_validation_performance_claimed"] is False
    assert history["mapping_versions"]["v1"]["status"] == "FAILED_EMPIRICALLY_PRESERVED"
    v2 = history["mapping_versions"]["v2"]
    assert v2["status"] == "UNCHANGED_UNVALIDATED_FORMAL_RUN_NOT_LAUNCHED"
    assert v2["formal_labeling_budget_spent_usd"] == 0
    assert v2["locked_test_opened"] is v2["classifier_fitted"] is False
    for name, expected in v2["frozen_artifact_sha256"].items():
        observed = hashlib.sha256((MAPPING / name).read_bytes()).hexdigest()
        assert observed == expected
    assert history["mapping_versions"]["v3"]["production_method_selected"] is False


def test_v3_execution_receipt_records_zero_spend_and_no_production_choice():
    receipt = json.loads((MAPPING / "mapA_v3_predecision_execution_receipt_20260823.json").read_text())
    assert receipt["realized_spend_usd"] == 0
    assert receipt["production_mapping_selected"] is False
    assert receipt["v2_preservation"]["formal_labeling_budget_spent_usd"] == 0
    assert receipt["v2_preservation"]["locked_test_opened"] is False
    assert receipt["v2_preservation"]["classifier_fitted"] is False
    assert not any(receipt["downstream"].values())
