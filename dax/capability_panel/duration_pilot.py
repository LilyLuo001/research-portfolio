"""Prospectively frozen GDPval qualified-human duration-pilot mechanics."""

from __future__ import annotations

import collections
import dataclasses
import hashlib
import math
import statistics
from collections.abc import Iterable, Mapping, Sequence


PILOT_SEED = "DAX-TD-PILOT40-20260821-BOUNCE-AMENDMENT"
PILOT_TASKS = 40
ROUND1_ANNOTATORS_PER_TASK = 3
MIN_PILOT_ADJACENT_PASS_TASKS = 32
PILOT_ADJACENT_AGREEMENT_FLOOR = 0.80
DURATION_BINS_MINUTES = (5, 15, 30, 60, 120, 240, 480, 960, 1920)
FAMILY_FAILURE_MIN_TASKS = 3
FAMILY_FAILURE_MIN_FAILURES = 2
FAMILY_FAILURE_PASS_SHARE_FLOOR = 0.60


@dataclasses.dataclass(frozen=True)
class PilotCandidate:
    task_id: str
    task_family: str
    occupation: str
    anticipated_duration_band: str
    task_format: str
    complexity_score: float


def _stable(value: str) -> str:
    return hashlib.sha256(f"{PILOT_SEED}|{value}".encode()).hexdigest()


def select_pilot(candidates: Iterable[PilotCandidate], *, size: int = PILOT_TASKS) -> list[PilotCandidate]:
    """Greedily balance pre-label strata with deterministic SHA tie-breaking.

    New occupations are preferred first; then the least represented family,
    anticipated-duration band, format, and joint stratum.  No duration label or
    model/downstream field is accepted by this function.
    """
    pool = list(candidates)
    if len({row.task_id for row in pool}) != len(pool) or len(pool) < size:
        raise ValueError("pilot candidates require unique IDs and enough tasks")
    if any(not all((row.task_family, row.occupation, row.anticipated_duration_band, row.task_format)) for row in pool):
        raise ValueError("pilot candidate strata must be complete")

    selected: list[PilotCandidate] = []
    occupation_count: collections.Counter[str] = collections.Counter()
    family_count: collections.Counter[str] = collections.Counter()
    duration_count: collections.Counter[str] = collections.Counter()
    format_count: collections.Counter[str] = collections.Counter()
    joint_count: collections.Counter[tuple[str, str, str]] = collections.Counter()
    while len(selected) < size:
        def priority(row: PilotCandidate) -> tuple[object, ...]:
            joint = (row.task_family, row.anticipated_duration_band, row.task_format)
            return (
                int(occupation_count[row.occupation] > 0),
                family_count[row.task_family],
                duration_count[row.anticipated_duration_band],
                format_count[row.task_format],
                joint_count[joint],
                _stable(row.task_id),
            )

        chosen = min(pool, key=priority)
        pool.remove(chosen)
        selected.append(chosen)
        occupation_count[chosen.occupation] += 1
        family_count[chosen.task_family] += 1
        duration_count[chosen.anticipated_duration_band] += 1
        format_count[chosen.task_format] += 1
        joint_count[(chosen.task_family, chosen.anticipated_duration_band, chosen.task_format)] += 1
    return selected


def bin_index(minutes: float) -> int:
    """Map a positive estimate to the frozen log-spaced bin index."""
    value = float(minutes)
    if not math.isfinite(value) or value <= 0:
        raise ValueError("duration minutes must be positive and finite")
    for index, boundary in enumerate(DURATION_BINS_MINUTES):
        if value <= boundary:
            return index
    return len(DURATION_BINS_MINUTES) - 1


def evaluate_pilot(
    rows: Iterable[Mapping[str, object]],
    *,
    expected_task_ids: Sequence[str],
) -> dict[str, object]:
    """Evaluate round-1 pilot agreement without changing labels or rules."""
    expected = set(expected_task_ids)
    if len(expected) != PILOT_TASKS or len(expected) != len(expected_task_ids):
        raise ValueError("evaluation requires the exact 40 unique frozen pilot tasks")
    records = list(rows)
    by_task: dict[str, list[Mapping[str, object]]] = collections.defaultdict(list)
    for row in records:
        task_id = str(row.get("gdpval_task_id", "")).strip()
        if task_id in expected:
            by_task[task_id].append(row)

    missing_or_incomplete = 0
    ordering_invalid = 0
    exact_pass = 0
    adjacent_pass = 0
    task_summaries: list[dict[str, object]] = []
    annotator_deviations: dict[str, list[float]] = collections.defaultdict(list)
    for task_id in sorted(expected):
        task_rows = by_task.get(task_id, [])
        annotator_codes = [str(row.get("private_annotator_code", "")).strip() for row in task_rows]
        complete = len(task_rows) == 3 and len(set(annotator_codes)) == 3 and all(annotator_codes)
        medians: list[float] = []
        median_bins: list[int] = []
        family = ""
        if complete:
            for row in task_rows:
                family = str(row.get("task_family", "")).strip()
                try:
                    lower = float(row["duration_lower_minutes"])
                    median = float(row["duration_median_minutes"])
                    upper = float(row["duration_upper_minutes"])
                except (KeyError, TypeError, ValueError):
                    complete = False
                    break
                if not (0 < lower <= median <= upper):
                    ordering_invalid += 1
                    complete = False
                    break
                if str(row.get("qualification_status", "")).upper() != "PASS":
                    complete = False
                    break
                medians.append(median)
                median_bins.append(bin_index(median))
        if not complete or not family:
            missing_or_incomplete += 1
            task_summaries.append({"task_id": task_id, "complete": False, "family": family})
            continue
        exact = len(set(median_bins)) == 1
        adjacent = max(median_bins) - min(median_bins) <= 1
        exact_pass += int(exact)
        adjacent_pass += int(adjacent)
        center_bin = statistics.median(median_bins)
        for code, value in zip(annotator_codes, median_bins):
            annotator_deviations[code].append(value - center_bin)
        task_summaries.append(
            {
                "task_id": task_id,
                "complete": True,
                "family": family,
                "exact": exact,
                "adjacent": adjacent,
                "median_ratio": max(medians) / min(medians),
            }
        )

    family_metrics: dict[str, dict[str, object]] = {}
    family_failures = []
    for family in sorted({str(row.get("family", "")) for row in task_summaries if row.get("family")}):
        family_rows = [row for row in task_summaries if row.get("family") == family and row.get("complete")]
        passing = sum(bool(row.get("adjacent")) for row in family_rows)
        failures = len(family_rows) - passing
        share = passing / len(family_rows) if family_rows else 0.0
        systematic_failure = (
            len(family_rows) >= FAMILY_FAILURE_MIN_TASKS
            and failures >= FAMILY_FAILURE_MIN_FAILURES
            and share < FAMILY_FAILURE_PASS_SHARE_FLOOR
        )
        if systematic_failure:
            family_failures.append(family)
        family_metrics[family] = {
            "complete_tasks": len(family_rows),
            "adjacent_pass_tasks": passing,
            "adjacent_pass_share": share,
            "systematic_failure": systematic_failure,
        }

    complete_summaries = [row for row in task_summaries if row.get("complete")]
    systematic_annotators = sum(
        len(values) >= 5 and abs(statistics.mean(values)) >= 1.0
        for values in annotator_deviations.values()
    )
    evaluable = len(complete_summaries) == PILOT_TASKS and missing_or_incomplete == 0 and ordering_invalid == 0
    passed = evaluable and adjacent_pass >= MIN_PILOT_ADJACENT_PASS_TASKS and not family_failures
    return {
        "status": "PASS" if passed else "FAIL" if evaluable else "NOT_EVALUABLE",
        "expected_tasks": PILOT_TASKS,
        "complete_tasks": len(complete_summaries),
        "exact_agreement_tasks": exact_pass,
        "exact_agreement_share": exact_pass / PILOT_TASKS,
        "adjacent_agreement_tasks": adjacent_pass,
        "adjacent_agreement_share": adjacent_pass / PILOT_TASKS,
        "binding_adjacent_floor": PILOT_ADJACENT_AGREEMENT_FLOOR,
        "binding_minimum_pass_tasks": MIN_PILOT_ADJACENT_PASS_TASKS,
        "median_of_task_max_to_min_median_ratios": (
            statistics.median(row["median_ratio"] for row in complete_summaries) if complete_summaries else None
        ),
        "ordering_invalid": ordering_invalid,
        "missing_or_incomplete_tasks": missing_or_incomplete,
        "family_metrics": family_metrics,
        "systematic_family_failures": family_failures,
        "systematically_deviating_annotator_count": systematic_annotators,
        "adjudication_cannot_change_round1_pilot_agreement": True,
    }
