"""Recall-first candidate generation for Mapping A v2.

This module deliberately stops before deciding whether two tasks are
substitutable.  Candidate retrieval and substantive adjudication are different
measurement stages.  The failed v1 run conflated a generic embedding score
with a match decision; v2 keeps the two auditable.

The private runner supplies one score row for every O*NET x GDPval pair.  With
only 220 GDPval tasks, the full pool is small enough that occupation labels do
not need to exclude candidates.  Dense and lexical top-k lists are unioned;
ties are deterministic.  No task text enters this release-safe module.
"""

from __future__ import annotations

import collections
import dataclasses
from collections.abc import Iterable, Sequence


CANDIDATE_RECALL_FLOOR = 0.95


@dataclasses.dataclass(frozen=True)
class ScoreRow:
    onet_task_id: str
    gdpval_task_id: str
    dense_score: float
    lexical_score: float


@dataclasses.dataclass(frozen=True)
class CandidateProposal:
    onet_task_id: str
    gdpval_task_id: str
    dense_rank: int
    lexical_rank: int
    retrieval_channels: tuple[str, ...]


def _rank(rows: Sequence[ScoreRow], field: str) -> dict[str, int]:
    ordered = sorted(
        rows,
        key=lambda row: (-float(getattr(row, field)), row.gdpval_task_id),
    )
    return {row.gdpval_task_id: index for index, row in enumerate(ordered, start=1)}


def generate_candidates(
    rows: Iterable[ScoreRow],
    *,
    expected_gdpval_task_ids: Sequence[str],
    dense_k: int = 20,
    lexical_k: int = 20,
) -> list[CandidateProposal]:
    """Union dense and lexical candidates after checking the full score pool.

    A missing pair is a hard error.  Otherwise a retrieval implementation could
    silently recreate the v1 blocking failure while still producing plausible
    looking top-k output.
    """
    if dense_k <= 0 or lexical_k <= 0:
        raise ValueError("candidate top-k values must be positive")

    expected = tuple(sorted(set(expected_gdpval_task_ids)))
    if not expected:
        raise ValueError("expected GDPval task universe must not be empty")
    if len(expected) != len(expected_gdpval_task_ids):
        raise ValueError("expected GDPval task IDs must be unique")

    grouped: dict[str, list[ScoreRow]] = collections.defaultdict(list)
    for row in rows:
        if not row.onet_task_id or not row.gdpval_task_id:
            raise ValueError("task IDs must be non-empty")
        grouped[row.onet_task_id].append(row)
    if not grouped:
        raise ValueError("score pool must contain at least one O*NET task")

    proposals: list[CandidateProposal] = []
    expected_set = set(expected)
    for onet_task_id in sorted(grouped):
        task_rows = grouped[onet_task_id]
        observed = [row.gdpval_task_id for row in task_rows]
        if len(observed) != len(set(observed)):
            raise ValueError(f"duplicate GDPval score row for O*NET task {onet_task_id}")
        if set(observed) != expected_set:
            missing = sorted(expected_set - set(observed))
            extra = sorted(set(observed) - expected_set)
            raise ValueError(
                f"incomplete GDPval score pool for {onet_task_id}: "
                f"missing={missing}, extra={extra}"
            )

        dense_ranks = _rank(task_rows, "dense_score")
        lexical_ranks = _rank(task_rows, "lexical_score")
        for gdpval_task_id in expected:
            channels = []
            if dense_ranks[gdpval_task_id] <= dense_k:
                channels.append("dense")
            if lexical_ranks[gdpval_task_id] <= lexical_k:
                channels.append("lexical")
            if channels:
                proposals.append(
                    CandidateProposal(
                        onet_task_id=onet_task_id,
                        gdpval_task_id=gdpval_task_id,
                        dense_rank=dense_ranks[gdpval_task_id],
                        lexical_rank=lexical_ranks[gdpval_task_id],
                        retrieval_channels=tuple(channels),
                    )
                )
    return proposals


def candidate_recall(
    proposals: Iterable[CandidateProposal],
    positive_pairs: Iterable[tuple[str, str]],
) -> float:
    """Return recall on independently adjudicated positive task pairs."""
    predicted = {(row.onet_task_id, row.gdpval_task_id) for row in proposals}
    positives = set(positive_pairs)
    if not positives:
        raise ValueError("candidate-recall audit requires at least one positive pair")
    return len(predicted & positives) / len(positives)


def assert_candidate_recall(recall: float, floor: float = CANDIDATE_RECALL_FLOOR) -> None:
    if not 0 <= recall <= 1:
        raise ValueError("candidate recall must lie in [0, 1]")
    if recall < floor:
        raise RuntimeError(
            f"Mapping A v2 candidate gate failed: recall {recall:.4f} < {floor:.4f}"
        )
