import pathlib
import sys

import pytest

MAPPING = pathlib.Path(__file__).resolve().parents[1] / "mapping"
sys.path.insert(0, str(MAPPING))

from mapA_v2_candidates import ScoreRow  # noqa: E402
from mapA_v2_validation import (  # noqa: E402
    BM25_B,
    BM25_K1,
    DENSE_MODEL_ID,
    DENSE_MODEL_REVISION,
    TaskMeta,
    assert_blinded_metadata,
    bm25_scores,
    build_validation_pairs,
    select_validation_tasks,
)


def test_protocol_does_not_bind_new_unapproved_thresholds():
    protocol = (MAPPING / "MAPPING_A_V2_VALIDATION_PROTOCOL_2026-08-21.md").read_text(
        encoding="utf-8"
    )
    packet = (MAPPING / "MAPPING_A_V2_DECISION_PACKET_2026-08-21.md").read_text(
        encoding="utf-8"
    )
    assert "Candidate recall must be at least 0.95" not in packet
    assert "candidate recall" in protocol and "NEED_HUMAN" in protocol


def test_dense_model_and_bm25_parameters_are_pinned():
    assert DENSE_MODEL_ID == "sentence-transformers/all-MiniLM-L6-v2"
    assert DENSE_MODEL_REVISION == "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    assert (BM25_K1, BM25_B) == (1.2, 0.75)


def test_bm25_is_deterministic_and_rewards_shared_terms():
    first = bm25_scores(["prepare tax return", "repair diesel engine"], ["tax return"])
    second = bm25_scores(["prepare tax return", "repair diesel engine"], ["tax return"])
    assert first == second
    assert first[0][0] > first[0][1]


def test_blind_metadata_refuses_outcome_or_w5_fields():
    assert_blinded_metadata({"onet_task_id": "O1", "dense_rank": 1})
    for field in ("outcome", "employment", "w5_dose", "power", "model_capability"):
        with pytest.raises(ValueError, match="forbidden"):
            assert_blinded_metadata({field: 1})


def test_task_sampling_is_deterministic_and_stratified():
    tasks = [
        TaskMeta(f"O{i}", "11", i % 2, i % 3) for i in range(12)
    ] + [TaskMeta(f"P{i}", "13", i % 2, i % 3) for i in range(12)]
    first = select_validation_tasks(tasks, tasks_per_major_family=6)
    second = select_validation_tasks(reversed(tasks), tasks_per_major_family=6)
    assert first == second
    assert {family: sum(row.major_soc_family == family for row in first)
            for family in ("11", "13")} == {"11": 6, "13": 6}


def test_validation_pairs_keep_task_in_one_blind_split_and_include_negatives():
    ids = [f"G{i:03d}" for i in range(1, 221)]
    rows = [
        ScoreRow("O1", gdpval_id, 1 / index, 1 / (221 - index))
        for index, gdpval_id in enumerate(ids, start=1)
    ]
    pairs = build_validation_pairs(
        rows,
        [TaskMeta("O1", "11", 1, 5)],
        expected_gdpval_task_ids=ids,
    )
    assert len({pair.split for pair in pairs}) == 1
    assert "apparent_negative" in {pair.candidate_category for pair in pairs}
    assert len({pair.gdpval_task_id for pair in pairs}) == len(pairs)


def test_validation_pairs_fail_closed_on_missing_full_pool():
    with pytest.raises(ValueError, match="incomplete"):
        build_validation_pairs(
            [ScoreRow("O1", "G1", 0.5, 0.5)],
            [TaskMeta("O1", "11", 1, 5)],
            expected_gdpval_task_ids=["G1", "G2"],
        )
