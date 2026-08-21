import pathlib
import sys

import pytest

MAPPING = pathlib.Path(__file__).resolve().parents[1] / "mapping"
sys.path.insert(0, str(MAPPING))

from mapA_v2_candidates import (  # noqa: E402
    CandidateProposal,
    ScoreRow,
    assert_candidate_recall,
    candidate_recall,
    generate_candidates,
)


def _pool():
    return [
        ScoreRow("O1", "G1", 0.9, 0.1),
        ScoreRow("O1", "G2", 0.8, 0.9),
        ScoreRow("O1", "G3", 0.7, 0.8),
    ]


def test_dense_and_lexical_top_k_are_unioned():
    rows = generate_candidates(
        _pool(), expected_gdpval_task_ids=["G1", "G2", "G3"], dense_k=1, lexical_k=1
    )
    assert {(row.gdpval_task_id, row.retrieval_channels) for row in rows} == {
        ("G1", ("dense",)),
        ("G2", ("lexical",)),
    }


def test_candidate_generation_refuses_incomplete_full_pool():
    with pytest.raises(ValueError, match="incomplete GDPval score pool"):
        generate_candidates(
            _pool()[:-1], expected_gdpval_task_ids=["G1", "G2", "G3"]
        )


def test_ties_break_on_task_id():
    pool = [ScoreRow("O1", "G2", 0.9, 0.9), ScoreRow("O1", "G1", 0.9, 0.9)]
    rows = generate_candidates(
        pool, expected_gdpval_task_ids=["G1", "G2"], dense_k=1, lexical_k=1
    )
    assert [row.gdpval_task_id for row in rows] == ["G1"]


def test_candidate_recall_gate_is_independent_of_similarity_thresholds():
    proposals = [CandidateProposal("O1", "G1", 1, 2, ("dense",))]
    assert candidate_recall(proposals, [("O1", "G1")]) == 1.0
    with pytest.raises(RuntimeError, match="candidate gate failed"):
        assert_candidate_recall(0.94, pi_approved_floor=0.95)


def test_candidate_recall_gate_has_no_unapproved_default():
    with pytest.raises(TypeError):
        assert_candidate_recall(0.99)
