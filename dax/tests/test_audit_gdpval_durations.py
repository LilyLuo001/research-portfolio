import pytest

from dax.capability_panel.audit_gdpval_durations import (
    DurationAuditError,
    EXPECTED_TASKS,
    build_private_rows,
    find_duration_fields,
)


def _ids():
    return [f"task-{index:03d}" for index in range(EXPECTED_TASKS)]


def test_public_schema_without_duration_field_is_detected():
    fields = ["task_id", "sector", "occupation", "prompt", "rubric_json"]
    assert find_duration_fields(fields) == []


def test_duration_field_detection_is_explicit_not_fuzzy():
    fields = ["task_id", "time_to_complete_hours", "prompt_runtime_note"]
    assert find_duration_fields(fields) == ["time_to_complete_hours"]


def test_private_audit_has_all_ids_but_no_task_text_or_imputation():
    rows = build_private_rows(_ids(), dataset_revision="abc123")
    assert len(rows) == EXPECTED_TASKS
    assert {row["match_status"] for row in rows} == {
        "unavailable_task_level_in_public_release"
    }
    assert all(row["duration_value"] == "" for row in rows)
    assert all("prompt" not in row and "rubric" not in row for row in rows)


def test_duplicate_or_incomplete_task_universe_blocks():
    with pytest.raises(DurationAuditError, match="expected 220"):
        build_private_rows(_ids()[:-1], dataset_revision="abc123")
    duplicated = _ids()
    duplicated[-1] = duplicated[0]
    with pytest.raises(DurationAuditError, match="duplicate"):
        build_private_rows(duplicated, dataset_revision="abc123")
