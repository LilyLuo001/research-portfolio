"""Determinism and containment tests for the Mapping A execution runner."""

import pathlib
import sys

import pytest


# The deterministic runner is tested on SCC under its frozen PyTorch/
# Transformers stack. Generic CI intentionally omits those large model-runtime
# dependencies, so it must skip this module rather than fail during collection.
pytest.importorskip("torch")
pytest.importorskip("transformers")


MAPPING = pathlib.Path(__file__).resolve().parents[1] / "mapping"
sys.path.insert(0, str(MAPPING))

from mapA_adjudication import GRADE_B, GRADE_C, GradedMatch  # noqa: E402
from run_mapA import (  # noqa: E402
    BLOCK_OCCUPATIONS,
    MODEL_DIMENSION,
    MODEL_ID,
    MODEL_REVISION,
    empirical_deciles,
    normalize_label,
)


def _queued(task_id, similarity, grade=GRADE_B):
    return GradedMatch(task_id, "G1", similarity, None, None, grade, "queued")


def test_model_and_blocking_are_exactly_pinned():
    assert MODEL_ID == "sentence-transformers/all-MiniLM-L6-v2"
    assert MODEL_REVISION == "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    assert MODEL_DIMENSION == 384
    assert BLOCK_OCCUPATIONS == 10


def test_empirical_queue_deciles_are_order_invariant_and_complete():
    matches = [_queued(f"T{i:02d}", 0.60 + i / 100) for i in range(20)]
    forward = empirical_deciles(matches)
    reverse = empirical_deciles(list(reversed(matches)))
    assert forward == reverse
    assert set(forward) == {match.onet_task_id for match in matches}
    assert set(forward.values()) == set(range(1, 11))


def test_empirical_queue_deciles_break_score_ties_by_task_id():
    matches = [_queued("T2", 0.7, GRADE_C), _queued("T1", 0.7, GRADE_C)]
    result = empirical_deciles(matches)
    assert result["T1"] < result["T2"]


def test_label_normalization_is_deterministic():
    assert normalize_label("  Data   Scientists ") == "data scientists"
