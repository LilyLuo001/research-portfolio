"""Frozen, outcome-blind Mapping A v2 retrieval and validation sampling.

The module contains no production mapping decision.  It builds a reproducible
private annotation sample from a complete O*NET x GDPval score pool and emits
only IDs, ranks, strata, and split labels.  Task text and labels remain private.
"""

from __future__ import annotations

import collections
import dataclasses
import hashlib
import math
import re
import unicodedata
from collections.abc import Iterable, Sequence

from mapA_v2_candidates import ScoreRow


DENSE_MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
DENSE_MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
DENSE_MODEL_DIMENSION = 384
DENSE_MAX_WORDPIECES = 256
DENSE_POOLING = "attention-mask mean pooling then L2 normalization"
BM25_K1 = 1.2
BM25_B = 0.75
VALIDATION_SEED = "DAX-MAPA-V2-20260821"
TASKS_PER_MAJOR_FAMILY = 20

FORBIDDEN_BLIND_FIELDS = {
    "outcome",
    "employment",
    "hours",
    "w5_dose",
    "power",
    "treatment_effect",
    "model_capability",
    "api_price",
    "occupation_exposure_result",
}


@dataclasses.dataclass(frozen=True)
class TaskMeta:
    onet_task_id: str
    major_soc_family: str
    mass_band: int
    v1_score_decile: int


@dataclasses.dataclass(frozen=True)
class ValidationPair:
    onet_task_id: str
    gdpval_task_id: str
    major_soc_family: str
    mass_band: int
    v1_score_decile: int
    candidate_category: str
    dense_rank: int
    lexical_rank: int
    split: str


def normalize_lexical(value: str) -> list[str]:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.findall(r"[a-z0-9]+", normalized)


def bm25_scores(
    documents: Sequence[str],
    queries: Sequence[str],
    *,
    k1: float = BM25_K1,
    b: float = BM25_B,
) -> list[list[float]]:
    """Return deterministic Okapi BM25 scores, one row per query."""
    if not documents:
        raise ValueError("BM25 requires at least one document")
    if k1 <= 0 or not 0 <= b <= 1:
        raise ValueError("invalid BM25 parameters")
    tokenized = [normalize_lexical(document) for document in documents]
    lengths = [len(tokens) for tokens in tokenized]
    average_length = sum(lengths) / len(lengths)
    if average_length == 0:
        raise ValueError("BM25 document universe has no lexical tokens")

    frequencies = [collections.Counter(tokens) for tokens in tokenized]
    document_frequency: collections.Counter[str] = collections.Counter()
    for frequency in frequencies:
        document_frequency.update(frequency.keys())

    n_documents = len(documents)
    result: list[list[float]] = []
    for query in queries:
        query_terms = set(normalize_lexical(query))
        row = []
        for frequency, length in zip(frequencies, lengths):
            score = 0.0
            for term in query_terms:
                tf = frequency.get(term, 0)
                if not tf:
                    continue
                df = document_frequency[term]
                idf = math.log(1 + (n_documents - df + 0.5) / (df + 0.5))
                denominator = tf + k1 * (1 - b + b * length / average_length)
                score += idf * (tf * (k1 + 1) / denominator)
            row.append(round(score, 10))
        result.append(row)
    return result


def assert_blinded_metadata(record: dict[str, object]) -> None:
    fields = {str(field).casefold() for field in record}
    forbidden = sorted(fields & FORBIDDEN_BLIND_FIELDS)
    if forbidden:
        raise ValueError(f"validation metadata contains forbidden fields: {forbidden}")


def _stable_order(value: str) -> str:
    return hashlib.sha256(f"{VALIDATION_SEED}|{value}".encode()).hexdigest()


def _split(onet_task_id: str) -> str:
    bucket = int(_stable_order(f"split|{onet_task_id}")[:8], 16) % 10
    if bucket < 6:
        return "development"
    if bucket < 8:
        return "calibration"
    return "locked_test"


def select_validation_tasks(
    tasks: Iterable[TaskMeta],
    *,
    tasks_per_major_family: int = TASKS_PER_MAJOR_FAMILY,
) -> list[TaskMeta]:
    """Round-robin across mass-band x v1-score strata within SOC family."""
    if tasks_per_major_family <= 0:
        raise ValueError("tasks_per_major_family must be positive")
    by_family: dict[str, list[TaskMeta]] = collections.defaultdict(list)
    seen: set[str] = set()
    for task in tasks:
        if task.onet_task_id in seen:
            raise ValueError(f"duplicate O*NET task metadata: {task.onet_task_id}")
        if not task.major_soc_family:
            raise ValueError("major SOC family must be non-empty")
        seen.add(task.onet_task_id)
        by_family[task.major_soc_family].append(task)

    selected: list[TaskMeta] = []
    for family in sorted(by_family):
        strata: dict[tuple[int, int], list[TaskMeta]] = collections.defaultdict(list)
        for task in by_family[family]:
            strata[(task.mass_band, task.v1_score_decile)].append(task)
        for values in strata.values():
            values.sort(key=lambda task: _stable_order(f"task|{task.onet_task_id}"))

        family_selected: list[TaskMeta] = []
        keys = sorted(strata)
        while len(family_selected) < min(tasks_per_major_family, len(by_family[family])):
            progressed = False
            for key in keys:
                if strata[key] and len(family_selected) < tasks_per_major_family:
                    family_selected.append(strata[key].pop(0))
                    progressed = True
            if not progressed:
                break
        selected.extend(family_selected)
    return sorted(selected, key=lambda task: (task.major_soc_family, task.onet_task_id))


def _ranks(rows: Sequence[ScoreRow], field: str) -> dict[str, int]:
    ranked = sorted(rows, key=lambda row: (-getattr(row, field), row.gdpval_task_id))
    return {row.gdpval_task_id: index for index, row in enumerate(ranked, start=1)}


def _choose_category_candidates(rows: Sequence[ScoreRow]) -> list[tuple[str, str, int, int]]:
    dense = _ranks(rows, "dense_score")
    lexical = _ranks(rows, "lexical_score")
    ids = sorted(dense)

    predicates = [
        ("agree_high", lambda g: dense[g] <= 10 and lexical[g] <= 10,
         lambda g: (dense[g] + lexical[g], g)),
        ("dense_only_high", lambda g: dense[g] <= 10 and lexical[g] > 40,
         lambda g: (dense[g], -lexical[g], g)),
        ("lexical_only_high", lambda g: lexical[g] <= 10 and dense[g] > 40,
         lambda g: (lexical[g], -dense[g], g)),
        ("medium_uncertain", lambda g: 11 <= dense[g] <= 80 and 11 <= lexical[g] <= 80,
         lambda g: (abs(dense[g] - lexical[g]), dense[g] + lexical[g], g)),
        ("apparent_negative", lambda g: dense[g] > 100 and lexical[g] > 100,
         lambda g: (_stable_order(f"negative|{g}"),)),
        ("rrf_best", lambda g: True,
         lambda g: (-(1 / (60 + dense[g]) + 1 / (60 + lexical[g])), g)),
    ]

    chosen: list[tuple[str, str, int, int]] = []
    used: set[str] = set()
    for category, predicate, key in predicates:
        eligible = [gdpval_id for gdpval_id in ids if gdpval_id not in used and predicate(gdpval_id)]
        if not eligible:
            continue
        winner = min(eligible, key=key)
        used.add(winner)
        chosen.append((category, winner, dense[winner], lexical[winner]))
    return chosen


def build_validation_pairs(
    score_rows: Iterable[ScoreRow],
    selected_tasks: Iterable[TaskMeta],
    *,
    expected_gdpval_task_ids: Sequence[str],
) -> list[ValidationPair]:
    expected = set(expected_gdpval_task_ids)
    by_task: dict[str, list[ScoreRow]] = collections.defaultdict(list)
    for row in score_rows:
        by_task[row.onet_task_id].append(row)

    pairs: list[ValidationPair] = []
    for task in selected_tasks:
        rows = by_task.get(task.onet_task_id, [])
        observed = [row.gdpval_task_id for row in rows]
        if len(observed) != len(set(observed)) or set(observed) != expected:
            raise ValueError(f"incomplete or duplicate score pool for {task.onet_task_id}")
        for category, gdpval_id, dense_rank, lexical_rank in _choose_category_candidates(rows):
            pairs.append(
                ValidationPair(
                    onet_task_id=task.onet_task_id,
                    gdpval_task_id=gdpval_id,
                    major_soc_family=task.major_soc_family,
                    mass_band=task.mass_band,
                    v1_score_decile=task.v1_score_decile,
                    candidate_category=category,
                    dense_rank=dense_rank,
                    lexical_rank=lexical_rank,
                    split=_split(task.onet_task_id),
                )
            )
    return sorted(pairs, key=lambda pair: (pair.split, pair.onet_task_id, pair.candidate_category))
