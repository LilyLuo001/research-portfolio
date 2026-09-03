"""Mapping A (GDPval primary) — grading, routing, coverage, and the licence guard.

W3-mapA is "GDPval primary mapping protocol + adjudication (T1 judgment)". The
embedding step needs O*NET task statements and a pinned embedding model, neither
of which exists yet (W2-data is incomplete). Everything downstream of the
similarity scores is deterministic, and it is built and tested here so that when
the embeddings land the only new thing is the embeddings.

THREE DESIGN POINTS WORTH ARGUING WITH
--------------------------------------
1. **Similarity alone cannot grade a match.** A task that resembles one GDPval
   task at 0.81 and nothing else at 0.55 is a different object from a task that
   resembles two GDPval tasks at 0.81 and 0.80. The second is ambiguous *because*
   it matched well twice. Grading therefore uses the margin over the runner-up,
   not just the top score, and a high-similarity/low-margin pair is routed to
   adjudication rather than auto-accepted.

2. **Unmatched is a finding, not a gap.** An O*NET task with no candidate above
   the floor stays in the output with `grade = "unmatched"` and carries its
   occupation's wage-bill share. The execution plan says "never silently drop
   unmatched tasks"; the way to honour that is to make dropping impossible,
   which is why `route` returns them rather than filtering them.

3. **The GDPval licence is enforced in code.** The signed feasibility condition
   permits GDPval by task ID for internal research and forbids task text or
   derived task content in the public release. A rule that lives only in prose
   gets violated by whoever writes the release script six months from now, so
   `assert_release_safe` refuses any record carrying text fields.
"""

from __future__ import annotations

import collections
import dataclasses
import statistics

# Pre-registered thresholds. Changing any of these after seeing match outcomes
# is a specification choice; they are constants here so a diff shows it.
SIMILARITY_FLOOR = 0.60      # below this, no candidate is proposed at all
AUTO_ACCEPT_SIMILARITY = 0.80
AUTO_ACCEPT_MARGIN = 0.05    # top candidate must beat the runner-up by this
COVERAGE_FLOOR = 0.70        # occupations below this are flagged, not dropped

GRADE_A = "A"            # auto-accepted
GRADE_B = "B"            # plausible but ambiguous -> human queue with pre-label
GRADE_C = "C"            # weak -> human queue, no pre-label carried forward
UNMATCHED = "unmatched"

# Fields that would carry O*NET/GDPval task content into an artefact.  The
# guard walks nested containers, because receipts often nest input metadata and
# a top-level-only check would be easy to bypass accidentally.
TEXT_FIELDS = (
    "gdpval_task_text",
    "onet_task_statement",
    "task_statement",
    "task_text",
    "prompt",
    "rationale_text",
    "gdpval_prompt",
    "excerpt",
    "rubric_pretty",
    "rubric_json",
    "derived_task_content",
)


@dataclasses.dataclass(frozen=True)
class Candidate:
    onet_task_id: str
    gdpval_task_id: str
    similarity: float


@dataclasses.dataclass(frozen=True)
class GradedMatch:
    onet_task_id: str
    gdpval_task_id: str | None
    similarity: float | None
    runner_up_similarity: float | None
    margin: float | None
    grade: str
    reason: str

    @property
    def needs_adjudication(self) -> bool:
        return self.grade in (GRADE_B, GRADE_C)


def grade_task(onet_task_id: str, candidates: list[Candidate]) -> GradedMatch:
    """Grade one O*NET task's candidate set. Never returns None."""
    ranked = sorted((c for c in candidates if c.similarity >= SIMILARITY_FLOOR),
                    key=lambda c: (-c.similarity, c.gdpval_task_id))
    if not ranked:
        best = max((c.similarity for c in candidates), default=None)
        return GradedMatch(
            onet_task_id, None, best, None, None, UNMATCHED,
            f"no candidate at or above the {SIMILARITY_FLOOR} floor"
            + (f"; best was {best:.3f}" if best is not None else ""),
        )

    top = ranked[0]
    runner_up = ranked[1].similarity if len(ranked) > 1 else None
    margin = None if runner_up is None else round(top.similarity - runner_up, 6)

    if top.similarity >= AUTO_ACCEPT_SIMILARITY and (
            margin is None or margin >= AUTO_ACCEPT_MARGIN):
        grade, reason = GRADE_A, "clear top match with an adequate margin"
    elif top.similarity >= AUTO_ACCEPT_SIMILARITY:
        # High similarity, small margin: matched well against several GDPval
        # tasks, which is ambiguity, not confidence.
        grade = GRADE_B
        reason = (f"similarity {top.similarity:.3f} is high but the margin "
                  f"{margin:.3f} is below {AUTO_ACCEPT_MARGIN}; ambiguous "
                  "between near-equal GDPval tasks")
    else:
        grade = GRADE_B if top.similarity >= (SIMILARITY_FLOOR + AUTO_ACCEPT_SIMILARITY) / 2 else GRADE_C
        reason = f"similarity {top.similarity:.3f} below the auto-accept threshold"

    return GradedMatch(onet_task_id, top.gdpval_task_id, top.similarity,
                       runner_up, margin, grade, reason)


def route(graded: list[GradedMatch]) -> dict[str, list[GradedMatch]]:
    """Split into accepted / adjudication queue / unmatched. Nothing is discarded."""
    buckets: dict[str, list[GradedMatch]] = {
        "accepted": [], "adjudication_queue": [], "unmatched": []}
    for match in graded:
        if match.grade == GRADE_A:
            buckets["accepted"].append(match)
        elif match.grade == UNMATCHED:
            buckets["unmatched"].append(match)
        else:
            buckets["adjudication_queue"].append(match)
    return buckets


def coverage_by_occupation(
    graded: list[GradedMatch], task_to_occupation: dict[str, str]
) -> dict[str, dict[str, object]]:
    """Matched share per occupation, with the Decision-flagged low-coverage set."""
    totals: dict[str, int] = collections.Counter()
    matched: dict[str, int] = collections.Counter()
    for match in graded:
        occupation = task_to_occupation.get(match.onet_task_id)
        if occupation is None:
            continue
        totals[occupation] += 1
        if match.grade != UNMATCHED:
            matched[occupation] += 1

    report: dict[str, dict[str, object]] = {}
    for occupation, total in sorted(totals.items()):
        rate = matched[occupation] / total if total else 0.0
        report[occupation] = {
            "n_tasks": total,
            "n_matched": matched[occupation],
            "coverage": round(rate, 6),
            "below_floor": rate < COVERAGE_FLOOR,
        }
    return report


def top_quartile_flag(graded: list[GradedMatch]) -> set[str]:
    """O*NET task ids in the top quartile of match quality.

    The execution plan requires a top-quartile subset for headline
    re-estimation. Quality is the similarity of an *accepted or queued* match;
    unmatched tasks have no quality and are excluded from the quartile
    calculation rather than being scored zero, which would drag the cut point
    down and quietly widen the "top" quartile.
    """
    scored = [m for m in graded if m.similarity is not None and m.grade != UNMATCHED]
    if len(scored) < 4:
        return set()
    cut = statistics.quantiles([m.similarity for m in scored], n=4)[2]
    return {m.onet_task_id for m in scored if m.similarity >= cut}


def assert_release_safe(records: list[dict[str, object]]) -> None:
    """Refuse to emit GDPval task text into a release-path artefact.

    Binding signed feasibility condition: GDPval is referenced BY TASK ID for
    internal research; no task text or derived task content may enter the public
    release until redistribution rights are clarified. Enforced here rather than
    trusted to prose.
    """
    offending: set[str] = set()

    def walk(value: object, path: str = "") -> None:
        if isinstance(value, dict):
            for field, child in value.items():
                child_path = f"{path}.{field}" if path else str(field)
                if field in TEXT_FIELDS and str(child).strip():
                    offending.add(child_path)
                walk(child, child_path)
        elif isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    walk(records)
    if offending:
        raise SystemExit(
            "REFUSED: GDPval task content in a release-path record — fields "
            f"{sorted(offending)}. The signed W0.5 feasibility condition permits GDPval "
            "by task ID only. Reference `gdpval_task_id` and drop the text."
        )
