#!/usr/bin/env python3
"""Run the frozen, private Mapping A v2 retrieval and blind-sample build.

All task text, score matrices, IDs, and split manifests remain in the private
output directory.  The repository receipt contains only counts, hashes,
configuration, and non-label diagnostics.  This script never reads W4, W5,
power, treatment-effect, or outcome paths.
"""

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

from mapA_v2_candidates import ScoreRow
from mapA_v2_validation import (
    BM25_B,
    BM25_K1,
    DENSE_MAX_WORDPIECES,
    DENSE_MODEL_DIMENSION,
    DENSE_MODEL_ID,
    DENSE_MODEL_REVISION,
    DENSE_POOLING,
    TASKS_PER_MAJOR_FAMILY,
    VALIDATION_SEED,
    TaskMeta,
    bm25_scores,
    build_validation_pairs,
    select_validation_tasks,
)
PRIVATE_SCORES = "mapA_v2_full_scores.npz"
PRIVATE_ID_MANIFEST = "mapA_v2_ordered_ids.json"
PRIVATE_SAMPLE = "mapA_v2_validation_pairs.csv"
PRIVATE_MANIFEST = "mapA_v2_private_manifest.json"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def rank_band(values: dict[str, float], bands: int) -> dict[str, int]:
    ordered = sorted(values, key=lambda task_id: (values[task_id], task_id))
    n = len(ordered)
    return {
        task_id: min(bands, 1 + index * bands // n)
        for index, task_id in enumerate(ordered)
    } if n else {}


def load_task_metadata(
    onet: pd.DataFrame,
    wage_allocations: pathlib.Path,
    v1_mapping: pathlib.Path,
) -> list[TaskMeta]:
    wages = pd.read_csv(wage_allocations, dtype={"task_id": str})
    required_wage = {"task_id", "vintage", "task_annual_wage_bill_allocation", "allocation_usable"}
    if not required_wage <= set(wages.columns):
        raise ValueError(f"wage allocations missing {sorted(required_wage - set(wages.columns))}")
    usable = wages[
        (pd.to_numeric(wages["vintage"], errors="coerce") == 2021)
        & wages["allocation_usable"].astype(str).str.casefold().eq("true")
    ].copy()
    usable["mass"] = pd.to_numeric(usable["task_annual_wage_bill_allocation"], errors="coerce")
    mass = usable.dropna(subset=["mass"]).groupby("task_id")["mass"].sum().astype(float).to_dict()

    v1 = pd.read_csv(v1_mapping, dtype={"onet_task_id": str})
    if not {"onet_task_id", "similarity"} <= set(v1.columns):
        raise ValueError("v1 mapping lacks onet_task_id/similarity")
    v1_score = dict(zip(v1["onet_task_id"], pd.to_numeric(v1["similarity"], errors="coerce").fillna(-1.0)))

    task_ids = onet["task_id"].astype(str).tolist()
    mass_values = {task_id: float(mass.get(task_id, 0.0)) for task_id in task_ids}
    score_values = {task_id: float(v1_score.get(task_id, -1.0)) for task_id in task_ids}
    mass_bands = rank_band(mass_values, 4)
    score_deciles = rank_band(score_values, 10)
    task_to_soc = dict(zip(onet["task_id"].astype(str), onet["onet_soc"].astype(str)))
    return [
        TaskMeta(
            onet_task_id=task_id,
            major_soc_family=task_to_soc[task_id].split("-")[0],
            mass_band=mass_bands[task_id],
            v1_score_decile=score_deciles[task_id],
        )
        for task_id in task_ids
    ]


def write_private_csv(path: pathlib.Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        raise ValueError("refusing to write empty validation sample")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    path.chmod(0o600)


def execute(args: argparse.Namespace) -> dict[str, object]:
    # The SCC retrieval runtime is intentionally separate from the repository
    # test runtime; import the pinned torch/transformers runner only for a real
    # private execution, not when metadata helpers are unit-tested.
    from run_mapA import PinnedEncoder, read_inputs

    private_dir = args.private_output.resolve()
    receipt = args.receipt.resolve()
    if private_dir == receipt.parent or private_dir in receipt.parents:
        raise SystemExit("REFUSED: sanitized receipt must be outside the private tree")
    private_dir.mkdir(parents=True, exist_ok=True)
    private_dir.chmod(0o700)
    receipt.parent.mkdir(parents=True, exist_ok=True)

    onet, gdpval, _ = read_inputs(args.onet_csv, args.onet_zip, args.gdpval_parquet)
    if len(onet) != 19259 or len(gdpval) != 220:
        raise ValueError(f"universe drift: O*NET={len(onet)}, GDPval={len(gdpval)}")

    encoder = PinnedEncoder(args.cache_dir, args.batch_size)
    onet_vectors = encoder.encode(onet["task_statement"].tolist())
    gdpval_vectors = encoder.encode(gdpval["gdpval_prompt"].tolist())
    dense = np.clip(onet_vectors @ gdpval_vectors.T, 0, 1).astype(np.float32)
    lexical = np.asarray(
        bm25_scores(gdpval["gdpval_prompt"].tolist(), onet["task_statement"].tolist()),
        dtype=np.float32,
    )
    expected_shape = (19259, 220)
    if dense.shape != expected_shape or lexical.shape != expected_shape:
        raise AssertionError(f"score matrix shape drift: dense={dense.shape}, lexical={lexical.shape}")
    if not np.isfinite(dense).all() or not np.isfinite(lexical).all():
        raise ValueError("non-finite retrieval score")

    scores_path = private_dir / PRIVATE_SCORES
    np.savez_compressed(scores_path, dense=dense, lexical=lexical)
    scores_path.chmod(0o600)

    ordered_ids = {
        "onet_task_ids": onet["task_id"].astype(str).tolist(),
        "gdpval_task_ids": gdpval["gdpval_task_id"].astype(str).tolist(),
    }
    ids_path = private_dir / PRIVATE_ID_MANIFEST
    ids_path.write_text(json.dumps(ordered_ids, indent=2) + "\n", encoding="utf-8")
    ids_path.chmod(0o600)

    task_metadata = load_task_metadata(onet, args.wage_allocations, args.v1_mapping)
    selected = select_validation_tasks(task_metadata, tasks_per_major_family=TASKS_PER_MAJOR_FAMILY)
    task_index = {task_id: index for index, task_id in enumerate(ordered_ids["onet_task_ids"])}
    selected_score_rows = []
    for task in selected:
        row_index = task_index[task.onet_task_id]
        selected_score_rows.extend(
            ScoreRow(task.onet_task_id, gdpval_id, float(dense[row_index, column]), float(lexical[row_index, column]))
            for column, gdpval_id in enumerate(ordered_ids["gdpval_task_ids"])
        )
    validation_pairs = build_validation_pairs(
        selected_score_rows,
        selected,
        expected_gdpval_task_ids=ordered_ids["gdpval_task_ids"],
    )
    sample_records = [
        {
            "onet_task_id": pair.onet_task_id,
            "gdpval_task_id": pair.gdpval_task_id,
            "major_soc_family": pair.major_soc_family,
            "mass_band": pair.mass_band,
            "v1_score_decile": pair.v1_score_decile,
            "candidate_category": pair.candidate_category,
            "dense_rank": pair.dense_rank,
            "lexical_rank": pair.lexical_rank,
            "split": pair.split,
            "relation_label": "",
            "annotation_status": "PENDING_BLIND_ANNOTATION",
        }
        for pair in validation_pairs
    ]
    sample_path = private_dir / PRIVATE_SAMPLE
    write_private_csv(sample_path, sample_records)

    counts_by_split = collections.Counter(pair.split for pair in validation_pairs)
    counts_by_category = collections.Counter(pair.candidate_category for pair in validation_pairs)
    counts_by_family = collections.Counter(pair.major_soc_family for pair in validation_pairs)
    manifest = {
        "status": "BLIND_SAMPLE_FROZEN_LABELS_ABSENT",
        "seed": VALIDATION_SEED,
        "selected_onet_tasks": len(selected),
        "validation_pairs": len(validation_pairs),
        "counts_by_split": dict(sorted(counts_by_split.items())),
        "counts_by_category": dict(sorted(counts_by_category.items())),
        "counts_by_major_soc_family": dict(sorted(counts_by_family.items())),
        "artifacts": {
            PRIVATE_SCORES: {"sha256": sha256(scores_path), "bytes": scores_path.stat().st_size},
            PRIVATE_ID_MANIFEST: {"sha256": sha256(ids_path), "bytes": ids_path.stat().st_size},
            PRIVATE_SAMPLE: {"sha256": sha256(sample_path), "bytes": sample_path.stat().st_size},
        },
    }
    manifest_path = private_dir / PRIVATE_MANIFEST
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path.chmod(0o600)

    safe_receipt = {
        "status": "VALIDATION_SAMPLE_PREPARED_PI_THRESHOLDS_AND_LABELS_PENDING",
        "executed_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "universes": {"onet_tasks": len(onet), "gdpval_tasks": len(gdpval), "scored_pairs": int(dense.size)},
        "retrieval": {
            "dense_model": DENSE_MODEL_ID,
            "dense_revision": DENSE_MODEL_REVISION,
            "dense_dimension": DENSE_MODEL_DIMENSION,
            "dense_max_wordpieces": DENSE_MAX_WORDPIECES,
            "dense_pooling": DENSE_POOLING,
            "lexical": "Okapi BM25 over NFKC/casefold/[a-z0-9]+ tokens; no stemming/stop-word deletion",
            "bm25_k1": BM25_K1,
            "bm25_b": BM25_B,
            "occupation_blocking": False,
        },
        "blind_sample": {key: value for key, value in manifest.items() if key != "artifacts"},
        "private_manifest_sha256": sha256(manifest_path),
        "private_artifact_hashes": {key: value["sha256"] for key, value in manifest["artifacts"].items()},
        "labels_present": False,
        "validation_result": "NOT_YET_APPLICABLE",
        "pi_threshold_status": "NEED_HUMAN_BEFORE_LOCKED_TEST_OPEN",
        "outcomes_opened": False,
        "task_text_committed": False,
        "id_level_artifacts_committed": False,
    }
    receipt.write_text(json.dumps(safe_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return safe_receipt


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    value.add_argument("--onet-csv", type=pathlib.Path, required=True)
    value.add_argument("--onet-zip", type=pathlib.Path, required=True)
    value.add_argument("--gdpval-parquet", type=pathlib.Path, required=True)
    value.add_argument("--wage-allocations", type=pathlib.Path, required=True)
    value.add_argument("--v1-mapping", type=pathlib.Path, required=True)
    value.add_argument("--cache-dir", type=pathlib.Path, required=True)
    value.add_argument("--private-output", type=pathlib.Path, required=True)
    value.add_argument("--receipt", type=pathlib.Path, required=True)
    value.add_argument("--batch-size", type=int, default=64)
    return value


if __name__ == "__main__":
    print(json.dumps(execute(parser().parse_args()), indent=2, sort_keys=True))
