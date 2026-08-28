#!/usr/bin/env python3
"""Freeze the private exhaustive Recall@40 sample and public safe receipt."""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd

from mapA_v2_recall_audit import (
    CANDIDATE_K,
    RECALL_SAMPLE_SEED,
    FrozenRecallTask,
    RecallTask,
    freeze_recall_source_tasks,
)
from run_mapA_v2_validation import load_task_metadata, sha256, write_private_csv


PRIVATE_SOURCE_SAMPLE = "mapA_v2_recall_source_tasks.csv"
PRIVATE_PAIR_UNIVERSE = "mapA_v2_recall_pair_universe.csv"
PRIVATE_MANIFEST = "mapA_v2_recall_private_manifest.json"


def rank_band(values: dict[str, float], bands: int) -> dict[str, int]:
    ordered = sorted(values, key=lambda task_id: (values[task_id], task_id))
    return {task_id: min(bands, 1 + index * bands // len(ordered)) for index, task_id in enumerate(ordered)}


def source_retrieval_strata(
    dense: np.ndarray,
    lexical: np.ndarray,
    onet_ids: list[str],
    gdpval_ids: list[str],
) -> tuple[dict[str, int], dict[str, int]]:
    if dense.shape != (len(onet_ids), len(gdpval_ids)) or lexical.shape != dense.shape:
        raise ValueError("retrieval score/ID shape drift")
    if len(gdpval_ids) != 220 or not np.isfinite(dense).all() or not np.isfinite(lexical).all():
        raise ValueError("recall audit requires finite full 220-target retrieval pools")
    agreement: dict[str, float] = {}
    confidence: dict[str, float] = {}
    for index, onet_id in enumerate(onet_ids):
        dense_order = sorted(range(220), key=lambda column: (-float(dense[index, column]), gdpval_ids[column]))
        lexical_order = sorted(range(220), key=lambda column: (-float(lexical[index, column]), gdpval_ids[column]))
        dense_rank = {column: rank for rank, column in enumerate(dense_order, start=1)}
        lexical_rank = {column: rank for rank, column in enumerate(lexical_order, start=1)}
        agreement[onet_id] = float(len(set(dense_order[:40]) & set(lexical_order[:40])))
        confidence[onet_id] = max(
            1.0 / (60 + dense_rank[column]) + 1.0 / (60 + lexical_rank[column])
            for column in range(220)
        )
    return rank_band(agreement, 3), rank_band(confidence, 3)


def execute(args: argparse.Namespace) -> dict[str, object]:
    private_dir = args.private_output.resolve()
    receipt = args.receipt.resolve()
    if private_dir == receipt.parent or private_dir in receipt.parents:
        raise SystemExit("REFUSED: release-safe receipt must be outside private tree")
    private_dir.mkdir(parents=True, exist_ok=True)
    private_dir.chmod(0o700)
    receipt.parent.mkdir(parents=True, exist_ok=True)

    ids = json.loads(args.ordered_ids.read_text(encoding="utf-8"))
    onet_ids = [str(value) for value in ids["onet_task_ids"]]
    gdpval_ids = [str(value) for value in ids["gdpval_task_ids"]]
    scores = np.load(args.full_scores, allow_pickle=False)
    dense = scores["dense"]
    lexical = scores["lexical"]
    agreement, confidence = source_retrieval_strata(dense, lexical, onet_ids, gdpval_ids)

    # Task metadata reconstruction uses only pre-label O*NET family, 2021 mass,
    # and frozen v1-score characteristics.  Task text is unnecessary here.
    v1 = pd.read_csv(args.v1_mapping, dtype={"onet_task_id": str})
    task_to_soc = dict(zip(v1["onet_task_id"].astype(str), v1["onet_soc"].astype(str)))
    if set(onet_ids) - set(task_to_soc):
        raise ValueError("v1 receipt lacks O*NET family metadata")
    onet_stub = pd.DataFrame({"task_id": onet_ids, "onet_soc": [task_to_soc[value] for value in onet_ids]})
    metadata = load_task_metadata(onet_stub, args.wage_allocations, args.v1_mapping)

    with args.frozen_validation_sample.open(newline="", encoding="utf-8") as handle:
        validation_sources = {row["onet_task_id"] for row in csv.DictReader(handle)}
    eligible = [
        RecallTask(
            task.onet_task_id,
            task.major_soc_family,
            task.mass_band,
            task.v1_score_decile,
            agreement[task.onet_task_id],
            confidence[task.onet_task_id],
        )
        for task in metadata
        if task.onet_task_id not in validation_sources
    ]
    frozen = freeze_recall_source_tasks(eligible)

    source_rows = [
        {
            "onet_task_id": task.onet_task_id,
            "major_soc_family": task.major_soc_family,
            "mass_band": task.mass_band,
            "v1_score_decile": task.v1_score_decile,
            "agreement_band": task.agreement_band,
            "retrieval_confidence_band": task.retrieval_confidence_band,
            "batch": task.batch,
            "annotation_status": "FROZEN_NOT_LABELED",
        }
        for task in frozen
    ]
    source_path = private_dir / PRIVATE_SOURCE_SAMPLE
    write_private_csv(source_path, source_rows)
    pair_rows = [
        {
            "onet_task_id": task.onet_task_id,
            "gdpval_task_id": target,
            "batch": task.batch,
            "relation_label": "",
            "annotation_status": "FROZEN_NOT_LABELED",
        }
        for task in frozen
        for target in gdpval_ids
    ]
    pair_path = private_dir / PRIVATE_PAIR_UNIVERSE
    write_private_csv(pair_path, pair_rows)

    def counts(field: str) -> dict[str, int]:
        return dict(sorted(collections.Counter(str(row[field]) for row in source_rows).items()))

    manifest = {
        "status": "RECALL40_PRIMARY_AND_RESERVES_FROZEN_LABELS_ABSENT",
        "seed": RECALL_SAMPLE_SEED,
        "candidate_rule": "union_of_dense_top40_and_lexical_top40_with_ID_tie_break",
        "source_tasks": 100,
        "primary_source_tasks": 60,
        "reserve_source_tasks": 40,
        "target_tasks_per_source": 220,
        "frozen_pair_assessments": 22000,
        "excluded_classifier_validation_source_tasks": len(validation_sources),
        "independent_of_all_classifier_splits": True,
        "counts_by_batch": counts("batch"),
        "counts_by_major_family": counts("major_soc_family"),
        "counts_by_agreement_band": counts("agreement_band"),
        "counts_by_retrieval_confidence_band": counts("retrieval_confidence_band"),
        "counts_by_mass_band": counts("mass_band"),
        "artifacts": {
            PRIVATE_SOURCE_SAMPLE: {"sha256": sha256(source_path), "bytes": source_path.stat().st_size},
            PRIVATE_PAIR_UNIVERSE: {"sha256": sha256(pair_path), "bytes": pair_path.stat().st_size},
        },
    }
    manifest_path = private_dir / PRIVATE_MANIFEST
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path.chmod(0o600)
    safe = {
        **{key: value for key, value in manifest.items() if key != "artifacts"},
        "executed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "candidate_k": CANDIDATE_K,
        "initial_pair_assessments": 13200,
        "reserve_expansion_rule": "20_more_only_if_completed_denominator_has_fewer_than_100_D; never_for_unfavorable_recall; max_100_sources",
        "private_manifest_sha256": sha256(manifest_path),
        "private_artifact_hashes": {key: value["sha256"] for key, value in manifest["artifacts"].items()},
        "labels_present": False,
        "true_D_positives": "NOT_EVALUABLE",
        "recall_at_40": "NOT_EVALUABLE",
        "task_text_committed": False,
        "id_level_artifacts_committed": False,
        "outcomes_opened": False,
    }
    receipt.write_text(json.dumps(safe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return safe


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--full-scores", type=pathlib.Path, required=True)
    value.add_argument("--ordered-ids", type=pathlib.Path, required=True)
    value.add_argument("--frozen-validation-sample", type=pathlib.Path, required=True)
    value.add_argument("--wage-allocations", type=pathlib.Path, required=True)
    value.add_argument("--v1-mapping", type=pathlib.Path, required=True)
    value.add_argument("--private-output", type=pathlib.Path, required=True)
    value.add_argument("--receipt", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    print(json.dumps(execute(parser().parse_args()), indent=2, sort_keys=True))
