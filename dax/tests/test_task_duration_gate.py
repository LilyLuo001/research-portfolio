import pytest

from dax.capability_panel.task_duration_gate import (
    DurationGateError,
    PROTOCOL_VERSION,
    assert_duration_gate,
    validate_duration_rows,
)


def _annotation(task_id="G1"):
    return {
        "gdpval_task_id": task_id,
        "duration_lower_minutes": 30,
        "duration_median_minutes": 60,
        "duration_upper_minutes": 120,
        "source_type": "expert_annotation",
        "source_locator": "private-manifest-sha256:abc",
        "n_independent_annotators": 3,
        "n_observed_completions": 0,
        "adjacent_bin_agreement": 0.9,
        "adjudication_status": "PASS",
        "protocol_version": PROTOCOL_VERSION,
        "duration_unit": "minutes",
        "duration_basis": "expert_estimate",
        "match_status": "not_applicable_direct_annotation",
        "imputation_method": "none",
    }


def test_complete_expert_annotation_passes():
    report = assert_duration_gate(
        [_annotation()],
        expected_task_ids=["G1"],
        pi_approved_adjacent_bin_agreement_floor=0.8,
    )
    assert report["status"] == "PASS"


def test_missing_task_blocks_instead_of_constant_filling():
    report = validate_duration_rows(
        [_annotation()],
        expected_task_ids=["G1", "G2"],
        pi_approved_adjacent_bin_agreement_floor=0.8,
    )
    assert report["status"] == "BLOCKED"
    assert any("missing task rows" in error for error in report["errors"])


def test_llm_only_duration_is_prohibited():
    row = _annotation()
    row["source_type"] = "llm_only"
    with pytest.raises(DurationGateError, match="prohibited or unknown"):
        assert_duration_gate(
            [row], expected_task_ids=["G1"], pi_approved_adjacent_bin_agreement_floor=0.8
        )

def test_observed_timing_requires_three_completions_and_locator():
    row = _annotation()
    row.update(
        source_type="observed_task_timing",
        n_observed_completions=2,
        n_independent_annotators=0,
        adjacent_bin_agreement=0,
        duration_basis="observed_completion",
        match_status="exact_task_id_version",
    )
    with pytest.raises(DurationGateError, match="fewer than 3 observed completions"):
        assert_duration_gate([row], expected_task_ids=["G1"])


def test_gdpval_validated_self_report_requires_exact_version_and_validators():
    row = _annotation()
    row.update(
        source_type="gdpval_validated_self_report",
        duration_basis="validated_self_report",
        match_status="exact_task_id_version",
        n_independent_validators=2,
    )
    assert assert_duration_gate([row], expected_task_ids=["G1"])["status"] == "PASS"
    row["n_independent_validators"] = 1
    with pytest.raises(DurationGateError, match="fewer than 2 independent validators"):
        assert_duration_gate([row], expected_task_ids=["G1"])


def test_bounds_must_be_ordered_and_positive():
    row = _annotation()
    row["duration_lower_minutes"] = 90
    with pytest.raises(DurationGateError, match="lower <= median <= upper"):
        assert_duration_gate(
            [row], expected_task_ids=["G1"], pi_approved_adjacent_bin_agreement_floor=0.8
        )


def test_unapproved_agreement_floor_blocks():
    with pytest.raises(DurationGateError, match="PI-approved adjacent-bin"):
        assert_duration_gate([_annotation()], expected_task_ids=["G1"])


def test_invalid_unit_blocks():
    row = _annotation()
    row["duration_unit"] = "hours"
    with pytest.raises(DurationGateError, match="duration_unit"):
        assert_duration_gate(
            [row], expected_task_ids=["G1"], pi_approved_adjacent_bin_agreement_floor=0.8
        )


def test_unsupported_match_blocks():
    row = _annotation()
    row["match_status"] = "semantic_near_match"
    with pytest.raises(DurationGateError, match="unsupported expert-annotation match"):
        assert_duration_gate(
            [row], expected_task_ids=["G1"], pi_approved_adjacent_bin_agreement_floor=0.8
        )


def test_silent_imputation_blocks():
    row = _annotation()
    row["imputation_method"] = "occupation_mean"
    with pytest.raises(DurationGateError, match="imputation is prohibited"):
        assert_duration_gate(
            [row], expected_task_ids=["G1"], pi_approved_adjacent_bin_agreement_floor=0.8
        )


def test_constant_fill_signature_blocks_multiple_tasks():
    rows = [_annotation("G1"), _annotation("G2")]
    with pytest.raises(DurationGateError, match="constant-fill signature"):
        assert_duration_gate(
            rows,
            expected_task_ids=["G1", "G2"],
            pi_approved_adjacent_bin_agreement_floor=0.8,
        )
