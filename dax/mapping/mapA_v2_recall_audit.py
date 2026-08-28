"""Prospective source-task sampling and expansion rules for Recall@40."""

from __future__ import annotations

import collections
import dataclasses
import hashlib
from collections.abc import Iterable


RECALL_SAMPLE_SEED = "DAX-MAPA-V2-RECALL40-20260821"
INITIAL_SOURCE_TASKS = 60
RESERVE_BATCH_SIZE = 20
MAX_SOURCE_TASKS = 100
TARGET_POSITIVE_DENOMINATOR = 100
CANDIDATE_K = 40


@dataclasses.dataclass(frozen=True)
class RecallTask:
    onet_task_id: str
    major_soc_family: str
    mass_band: int
    v1_score_decile: int
    agreement_band: int
    retrieval_confidence_band: int


@dataclasses.dataclass(frozen=True)
class FrozenRecallTask(RecallTask):
    batch: str


def _stable(value: str) -> str:
    return hashlib.sha256(f"{RECALL_SAMPLE_SEED}|{value}".encode()).hexdigest()


def freeze_recall_source_tasks(tasks: Iterable[RecallTask]) -> list[FrozenRecallTask]:
    """Select 60 primary + two 20-task reserves before any labels exist.

    Selection rotates across major SOC families, then across the label-free
    agreement x retrieval-confidence x mass x v1-score strata within family.
    Stable hashes decide all within-stratum and rotation ties.
    """
    by_family: dict[str, list[RecallTask]] = collections.defaultdict(list)
    seen: set[str] = set()
    for task in tasks:
        if task.onet_task_id in seen:
            raise ValueError("duplicate recall-audit source task")
        if not task.major_soc_family:
            raise ValueError("major SOC family is required")
        if task.mass_band not in {1, 2, 3, 4} or task.v1_score_decile not in set(range(1, 11)):
            raise ValueError("invalid source-task mass/v1 strata")
        if task.agreement_band not in {1, 2, 3} or task.retrieval_confidence_band not in {1, 2, 3}:
            raise ValueError("invalid retrieval stratum")
        seen.add(task.onet_task_id)
        by_family[task.major_soc_family].append(task)
    if len(seen) < MAX_SOURCE_TASKS:
        raise ValueError("fewer than 100 eligible independent source tasks")

    family_queues: dict[str, list[RecallTask]] = {}
    for family, family_tasks in by_family.items():
        strata: dict[tuple[int, int, int, int], list[RecallTask]] = collections.defaultdict(list)
        for task in family_tasks:
            strata[(task.agreement_band, task.retrieval_confidence_band, task.mass_band, task.v1_score_decile)].append(task)
        for values in strata.values():
            values.sort(key=lambda task: _stable(f"task|{task.onet_task_id}"))
        keys = sorted(strata, key=lambda key: _stable(f"stratum|{family}|{key}"))
        ordered: list[RecallTask] = []
        while len(ordered) < len(family_tasks):
            for key in keys:
                if strata[key]:
                    ordered.append(strata[key].pop(0))
        family_queues[family] = ordered

    family_order = sorted(family_queues, key=lambda family: _stable(f"family|{family}"))
    selected: list[RecallTask] = []
    while len(selected) < MAX_SOURCE_TASKS:
        progressed = False
        for family in family_order:
            if family_queues[family] and len(selected) < MAX_SOURCE_TASKS:
                selected.append(family_queues[family].pop(0))
                progressed = True
        if not progressed:
            raise AssertionError("recall sampling exhausted unexpectedly")

    result = []
    for index, task in enumerate(selected):
        batch = "initial_60" if index < 60 else "reserve_1_20" if index < 80 else "reserve_2_20"
        result.append(FrozenRecallTask(**dataclasses.asdict(task), batch=batch))
    return result


def next_recall_batch(*, completed_source_tasks: int, adjudicated_d_positives: int) -> str:
    """Return the only prospectively permitted reserve action."""
    if completed_source_tasks not in {60, 80, 100} or adjudicated_d_positives < 0:
        raise ValueError("invalid recall-audit progress")
    if adjudicated_d_positives >= TARGET_POSITIVE_DENOMINATOR:
        return "STOP_DENOMINATOR_SUFFICIENT"
    if completed_source_tasks == 60:
        return "OPEN_RESERVE_1_20_ONLY"
    if completed_source_tasks == 80:
        return "OPEN_RESERVE_2_20_ONLY"
    return "STOP_MAXIMUM_100_REACHED"
