"""Tests for Mapping A (GDPval) grading, routing, coverage and the licence guard."""

import pathlib
import sys

import pytest

MAPPING = pathlib.Path(__file__).resolve().parents[1] / "mapping"
sys.path.insert(0, str(MAPPING))

from mapA_adjudication import (  # noqa: E402
    AUTO_ACCEPT_MARGIN, COVERAGE_FLOOR, GRADE_A, GRADE_B, GRADE_C, UNMATCHED,
    Candidate, assert_release_safe, coverage_by_occupation, grade_task, route,
    top_quartile_flag,
)


def _c(onet, gdpval, similarity):
    return Candidate(onet_task_id=onet, gdpval_task_id=gdpval, similarity=similarity)


# --- grading ----------------------------------------------------------------

def test_clear_top_match_with_margin_is_auto_accepted():
    match = grade_task("T1", [_c("T1", "G1", 0.91), _c("T1", "G2", 0.62)])
    assert match.grade == GRADE_A
    assert match.gdpval_task_id == "G1"


def test_high_similarity_with_thin_margin_is_ambiguous_not_confident():
    """Matching two GDPval tasks near-equally is ambiguity, however high the score.

    This is the case a similarity-only rule gets wrong: it would auto-accept.
    """
    match = grade_task("T2", [_c("T2", "G1", 0.88), _c("T2", "G2", 0.86)])
    assert match.grade == GRADE_B, "thin margin must route to adjudication"
    assert match.margin == pytest.approx(0.02)
    assert match.margin < AUTO_ACCEPT_MARGIN
    assert "ambiguous" in match.reason


def test_single_candidate_has_no_margin_and_can_still_auto_accept():
    match = grade_task("T3", [_c("T3", "G1", 0.95)])
    assert match.margin is None
    assert match.grade == GRADE_A, "nothing to be ambiguous against"


def test_weak_top_match_grades_c():
    match = grade_task("T4", [_c("T4", "G1", 0.62)])
    assert match.grade == GRADE_C


def test_unmatched_task_is_retained_with_its_best_score():
    """'Never silently drop unmatched tasks' — so they come back, not filtered."""
    match = grade_task("T5", [_c("T5", "G1", 0.41)])
    assert match.grade == UNMATCHED
    assert match.gdpval_task_id is None
    assert match.similarity == pytest.approx(0.41), \
        "the best sub-floor score is reported, not discarded"


def test_task_with_no_candidates_at_all_is_still_returned():
    match = grade_task("T6", [])
    assert match.grade == UNMATCHED
    assert match.similarity is None


def test_grading_is_deterministic_under_tied_similarity():
    """Ties break on gdpval_task_id so two runs cannot disagree."""
    first = grade_task("T7", [_c("T7", "G2", 0.9), _c("T7", "G1", 0.9)])
    second = grade_task("T7", [_c("T7", "G1", 0.9), _c("T7", "G2", 0.9)])
    assert first.gdpval_task_id == second.gdpval_task_id == "G1"


# --- routing ----------------------------------------------------------------

def test_routing_conserves_every_task():
    graded = [
        grade_task("A", [_c("A", "G1", 0.95)]),
        grade_task("B", [_c("B", "G1", 0.88), _c("B", "G2", 0.87)]),
        grade_task("C", [_c("C", "G1", 0.61)]),
        grade_task("D", [_c("D", "G1", 0.30)]),
    ]
    buckets = route(graded)
    total = sum(len(v) for v in buckets.values())
    assert total == len(graded), "routing must partition, never filter"
    assert len(buckets["accepted"]) == 1
    assert len(buckets["adjudication_queue"]) == 2
    assert len(buckets["unmatched"]) == 1


# --- coverage ---------------------------------------------------------------

def test_coverage_flags_occupations_below_the_floor():
    graded = [grade_task(f"T{i}", [_c(f"T{i}", "G1", 0.95)]) for i in range(7)]
    graded += [grade_task(f"U{i}", [_c(f"U{i}", "G1", 0.10)]) for i in range(3)]
    mapping = {f"T{i}": "29-1141" for i in range(7)}
    mapping.update({f"U{i}": "29-1141" for i in range(3)})

    report = coverage_by_occupation(graded, mapping)["29-1141"]
    assert report["coverage"] == pytest.approx(0.70)
    assert report["below_floor"] is False, "the floor is strict; exactly 0.70 passes"

    mapping["T6"] = "OTHER"
    report = coverage_by_occupation(graded, mapping)["29-1141"]
    assert report["coverage"] < COVERAGE_FLOOR
    assert report["below_floor"] is True


# --- match quality ----------------------------------------------------------

def test_unmatched_tasks_do_not_drag_down_the_top_quartile_cut():
    """Scoring unmatched as zero would widen the 'top' quartile silently."""
    matched = [grade_task(f"T{i}", [_c(f"T{i}", "G1", s)])
               for i, s in enumerate([0.95, 0.90, 0.85, 0.82, 0.81, 0.80])]
    with_unmatched = matched + [grade_task(f"U{i}", [_c(f"U{i}", "G1", 0.1)])
                                for i in range(20)]
    assert top_quartile_flag(matched) == top_quartile_flag(with_unmatched)


def test_top_quartile_needs_enough_scored_matches():
    assert top_quartile_flag([grade_task("T1", [_c("T1", "G1", 0.9)])]) == set()


# --- the GDPval licence guard ----------------------------------------------

def test_release_guard_refuses_gdpval_task_text():
    with pytest.raises(SystemExit, match="REFUSED"):
        assert_release_safe([{"onet_task_id": "T1", "gdpval_task_id": "G1",
                              "gdpval_task_text": "Draft a quarterly filing..."}])


def test_release_guard_allows_id_only_records():
    assert_release_safe([{"onet_task_id": "T1", "gdpval_task_id": "G1",
                          "similarity": 0.91, "grade": "A"}])


def test_release_guard_ignores_empty_text_fields():
    """A blank column is not a licence violation; only content is."""
    assert_release_safe([{"onet_task_id": "T1", "gdpval_task_id": "G1",
                          "gdpval_task_text": ""}])
