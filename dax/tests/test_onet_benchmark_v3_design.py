import hashlib
import json
import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
MAPPING = ROOT / "mapping"
sys.path.insert(0, str(MAPPING))

from onet_benchmark_v3_contract import (  # noqa: E402
    BenchmarkContractError,
    definition_sha256,
    non_evaluable_mass_bounds,
    validate_model_result,
    validate_task_definition,
)


def private_definition():
    return {
        "benchmark_item_id": "B-PRIVATE-1",
        "source_onet_task_id": "PRIVATE-ID",
        "occupation_task_family": "technical_analytic",
        "required_inputs": ["licensed synthetic ledger"],
        "allowed_tools": ["spreadsheet"],
        "required_deliverable": "reconciled statement",
        "completion_criterion": "balances and required fields pass",
        "scoring_rubric": [{"dimension": "reconciliation", "critical": True}],
        "failure_criterion": "material imbalance",
        "review_requirements": ["independent blinded review"],
        "professional_context_assumptions": "authorized accounting role",
        "evaluable_class": "executable_with_provided_files_data",
        "definition_version": "v1",
    }


def test_private_definition_is_separate_from_model_evaluation():
    definition = private_definition()
    validate_task_definition(definition)
    digest = definition_sha256(definition)
    assert len(digest) == 64
    with pytest.raises(BenchmarkContractError, match="model-evaluation"):
        definition_sha256({**definition, "model_score": 1})


def test_release_definition_forbids_private_source_id():
    definition = private_definition()
    release = dict(definition)
    release.pop("source_onet_task_id")
    release["source_task_ref_hash"] = "opaque-keyed-reference"
    validate_task_definition(release, release_path=True)
    with pytest.raises(BenchmarkContractError, match="private O.NET"):
        validate_task_definition(
            {**release, "source_onet_task_id": "PRIVATE-ID"}, release_path=True
        )


def test_non_evaluable_is_missing_not_zero():
    digest = "a" * 64
    validate_model_result(
        {
            "definition_sha256": digest,
            "evaluation_status": "not_evaluable",
            "model_score": None,
            "model_success": None,
        },
        frozen_definition_sha256=digest,
        evaluable_class="requires_physical_world_action",
    )
    with pytest.raises(BenchmarkContractError, match="zero-scored"):
        validate_model_result(
            {
                "definition_sha256": digest,
                "evaluation_status": "not_evaluable",
                "model_score": 0,
                "model_success": False,
            },
            frozen_definition_sha256=digest,
            evaluable_class="requires_physical_world_action",
        )


def test_missing_mass_bounds_have_no_unsigned_center():
    bounds = non_evaluable_mass_bounds(
        identified_crossing_mass=0.31, non_evaluable_mass=0.24
    )
    assert bounds["lower"] == pytest.approx(0.31)
    assert bounds["center"] is None
    assert bounds["upper"] == pytest.approx(0.55)


def test_design_is_unsigned_and_preserves_all_safeguards():
    design = json.loads((MAPPING / "onet_benchmark_v3_design_20260823.json").read_text())
    assert design["status"] == "DESIGN_PREFLIGHT_COMPLETE_NEED_PROSPECTIVE_PI_SIGNATURE"
    assert design["primary_direction"] == "onet_aligned_bridge_benchmark"
    assert design["robustness_direction"] == "strict_direct_task_substitution"
    assert design["authorized_universe"]["existing_crosswalk_gate_is_not_benchmark_sample_coverage_approval"]
    assert len(design["sampling_options"]) >= 3
    assert [option.get("proposed_sample_size_unsigned") for option in design["sampling_options"][:2]] == [120, 384]
    assert design["sampling_options"][2]["proposed_phase_1_sample_size_unsigned"] == 1067
    assert design["sampling_options"][2]["proposed_phase_2_sample_size_unsigned"] == 384
    assert design["scoring"]["minimum_success_threshold"] is None
    assert design["non_evaluable_rule"]["center"] is None
    assert design["historical_capture"]["paid_calls_in_this_batch"] == 0
    assert design["realized_spend_usd"] == 0
    assert design["recommended_next_step"]["recruitment_or_spend_authorized"] is False
    assert design["recommended_next_step"]["pi_signature_required"] is True
    assert design["signature_state"] == "NEED_HUMAN"
    assert not any(design["downstream"].values())


def test_v2_frozen_files_and_power_standard_are_unchanged():
    design = json.loads((MAPPING / "onet_benchmark_v3_design_20260823.json").read_text())
    for name, expected in design["v2_preservation"]["frozen_artifact_sha256"].items():
        assert hashlib.sha256((MAPPING / name).read_bytes()).hexdigest() == expected
    assert design["v2_preservation"]["locked_test_opened"] is False
    assert design["v2_preservation"]["classifier_fitted"] is False
    assert design["v2_preservation"]["formal_labeling_budget_spent_usd"] == 0
    # The power standard was legitimately FROZEN on 2026-08-24 by W1/W2, which
    # rewrote status, provenance, both baselines and both MDE ceilings. A
    # whole-file hash therefore breaks on correct work and, worse, says nothing
    # about WHAT moved -- re-baselining it each time would quietly retire the
    # guarantee. What this test exists to protect is narrower and permanent:
    # that no benchmark SELECTION was changed while the v3 design was drafted.
    # So pin the selection fields and exclude only the two baselines the
    # freezer is supposed to write.
    power = ROOT / "memo" / "power_calcs" / "power_standard.json"
    benchmark = json.loads(power.read_text())["benchmark"]
    written_by_freeze = {"baseline_employment_rate_22_25",
                         "baseline_hours_unconditional_22_25"}
    selection = {k: v for k, v in benchmark.items() if k not in written_by_freeze}
    assert hashlib.sha256(
        json.dumps(selection, sort_keys=True).encode()).hexdigest() == (
        "51057e3eda01531bc0b421480495a9a3f7a44bf52d84d3c9e050b18dc19f0229"
    ), "the benchmark selection moved; a freeze must not reselect the benchmark"


def test_historical_capture_registry_is_fully_accounted_for():
    design = json.loads((MAPPING / "onet_benchmark_v3_design_20260823.json").read_text())
    registry = json.loads((ROOT / "capability_panel" / "vintage_registry.json").read_text())
    assert design["historical_capture"]["registry_rows"] == len(registry["models"]) == 22
    statuses = [row["status"] for row in registry["models"]]
    assert statuses.count("account_probe_required") == 14
    assert statuses.count("standin_provider_unconfigured") == 2
    assert statuses.count("blocked_missing_approved_snapshot_rule") == 5
    assert statuses.count("excluded_binding") == 1
