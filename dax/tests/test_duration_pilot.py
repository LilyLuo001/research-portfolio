import collections

from dax.capability_panel.duration_pilot import (
    PILOT_TASKS,
    PilotCandidate,
    bin_index,
    evaluate_pilot,
    select_pilot,
)


def candidates():
    return [
        PilotCandidate(
            task_id=f"T{index:03d}",
            task_family=f"family-{index % 9}",
            occupation=f"occupation-{index % 44}",
            anticipated_duration_band=("anticipated_short_proxy", "anticipated_medium_proxy", "anticipated_long_proxy")[index % 3],
            task_format=("document", "spreadsheet_tabular", "presentation", "mixed")[index % 4],
            complexity_score=float(index),
        )
        for index in range(220)
    ]


def test_selection_is_deterministic_balanced_and_occupation_diverse():
    first = select_pilot(candidates())
    second = select_pilot(reversed(candidates()))
    assert first == second
    assert len(first) == 40
    assert len({row.occupation for row in first}) == 40
    assert len({row.task_family for row in first}) == 9
    assert set(collections.Counter(row.anticipated_duration_band for row in first)) == {
        "anticipated_short_proxy", "anticipated_medium_proxy", "anticipated_long_proxy"
    }


def test_frozen_duration_bins():
    assert bin_index(5) == 0
    assert bin_index(6) == 1
    assert bin_index(1920) == 8
    assert bin_index(10000) == 8


def pilot_rows(*, concentrated_failure=False):
    rows = []
    for task in range(PILOT_TASKS):
        family = f"family-{task // 5}"
        for annotator in range(3):
            median = 60
            if concentrated_failure and task < 3 and annotator == 2:
                median = 480
            rows.append(
                {
                    "gdpval_task_id": f"T{task:03d}",
                    "private_annotator_code": f"A{annotator}",
                    "task_family": family,
                    "duration_lower_minutes": 30,
                    "duration_median_minutes": median,
                    "duration_upper_minutes": max(120, median),
                    "qualification_status": "PASS",
                }
            )
    return rows


def test_complete_agreeing_pilot_passes():
    result = evaluate_pilot(pilot_rows(), expected_task_ids=[f"T{index:03d}" for index in range(40)])
    assert result["status"] == "PASS"
    assert result["adjacent_agreement_tasks"] == 40
    assert result["exact_agreement_tasks"] == 40


def test_family_concentrated_failure_fails_without_lowering_floor():
    result = evaluate_pilot(
        pilot_rows(concentrated_failure=True),
        expected_task_ids=[f"T{index:03d}" for index in range(40)],
    )
    assert result["status"] == "FAIL"
    assert result["adjacent_agreement_tasks"] == 37
    assert result["systematic_family_failures"] == ["family-0"]


def test_missing_human_response_is_not_evaluable():
    result = evaluate_pilot(pilot_rows()[:-1], expected_task_ids=[f"T{index:03d}" for index in range(40)])
    assert result["status"] == "NOT_EVALUABLE"
    assert result["missing_or_incomplete_tasks"] == 1
