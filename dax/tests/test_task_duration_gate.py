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
    }


def test_complete_expert_annotation_passes():
    report = assert_duration_gate([_annotation()], expected_task_ids=["G1"])
    assert report["status"] == "PASS"


def test_missing_task_blocks_instead_of_constant_filling():
    report = validate_duration_rows([_annotation()], expected_task_ids=["G1", "G2"])
    assert report["status"] == "BLOCKED"
    assert any("missing task rows" in error for error in report["errors"])


def test_llm_only_duration_is_prohibited():
    row = _annotation()
    row["source_type"] = "llm_only"
    with pytest.raises(DurationGateError, match="prohibited or unknown"):
        assert_duration_gate([row], expected_task_ids=["G1"])

def test_observed_timing_requires_three_completions_and_locator():
    row = _annotation()
    row.update(
        source_type="observed_task_timing",
        n_observed_completions=2,
        n_independent_annotators=0,
        adjacent_bin_agreement=0,
    )
    with pytest.raises(DurationGateError, match="fewer than 3 observed completions"):
        assert_duration_gate([row], expected_task_ids=["G1"])


def test_bounds_must_be_ordered_and_positive():
    row = _annotation()
    row["duration_lower_minutes"] = 90
    with pytest.raises(DurationGateError, match="lower <= median <= upper"):
        assert_duration_gate([row], expected_task_ids=["G1"])
