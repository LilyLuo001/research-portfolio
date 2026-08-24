import collections
import pathlib
import sys

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mapping"))
from mapA_v2_recall_audit import RecallTask, freeze_recall_source_tasks, next_recall_batch  # noqa: E402


def universe():
    return [
        RecallTask(
            onet_task_id=f"o{index:04d}",
            major_soc_family=f"{11 + 2 * (index % 22):02d}",
            mass_band=1 + index % 4,
            v1_score_decile=1 + index % 10,
            agreement_band=1 + index % 3,
            retrieval_confidence_band=1 + (index // 3) % 3,
        )
        for index in range(440)
    ]


def test_primary_and_both_reserves_are_frozen_deterministically():
    first = freeze_recall_source_tasks(universe())
    second = freeze_recall_source_tasks(reversed(universe()))
    assert first == second
    assert collections.Counter(task.batch for task in first) == {
        "initial_60": 60,
        "reserve_1_20": 20,
        "reserve_2_20": 20,
    }
    assert len({task.major_soc_family for task in first[:60]}) == 22
    assert len({task.agreement_band for task in first[:60]}) == 3
    assert len({task.retrieval_confidence_band for task in first[:60]}) == 3


def test_expansion_is_only_for_small_positive_denominator():
    assert next_recall_batch(completed_source_tasks=60, adjudicated_d_positives=100) == "STOP_DENOMINATOR_SUFFICIENT"
    assert next_recall_batch(completed_source_tasks=60, adjudicated_d_positives=99) == "OPEN_RESERVE_1_20_ONLY"
    assert next_recall_batch(completed_source_tasks=80, adjudicated_d_positives=99) == "OPEN_RESERVE_2_20_ONLY"
    assert next_recall_batch(completed_source_tasks=100, adjudicated_d_positives=0) == "STOP_MAXIMUM_100_REACHED"
    with pytest.raises(ValueError):
        next_recall_batch(completed_source_tasks=61, adjudicated_d_positives=0)
