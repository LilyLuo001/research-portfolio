#!/usr/bin/env python3
"""Execute deterministic, license-contained Mapping A on private corpora.

Text-bearing inputs, embeddings, ID-level mappings, and the adjudication queue
must stay in the caller-supplied private output directory. Only the aggregate
receipt passed with ``--receipt`` is release-safe.
"""

from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import io
import json
import math
import os
import pathlib
import random
import re
import statistics
import zipfile
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
import torch
from transformers import AutoModel, AutoTokenizer

from mapA_adjudication import (
    AUTO_ACCEPT_MARGIN,
    AUTO_ACCEPT_SIMILARITY,
    COVERAGE_FLOOR,
    GRADE_A,
    GRADE_B,
    GRADE_C,
    SIMILARITY_FLOOR,
    UNMATCHED,
    Candidate,
    GradedMatch,
    assert_release_safe,
    coverage_by_occupation,
    grade_task,
    route,
    top_quartile_flag,
)


MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
MODEL_DIMENSION = 384
MODEL_LICENSE = "Apache-2.0"
MODEL_MAX_LENGTH = 256
BLOCK_OCCUPATIONS = 10
EXPECTED_GDPVAL_ROWS = 220
SEED = 20260819

PRIVATE_MAPPING = "mapping_a_gdpval.csv"
PRIVATE_QUEUE = "mapA_adjudication_queue.csv"
PRIVATE_COVERAGE = "mapA_occupation_coverage.csv"
PRIVATE_MANIFEST = "mapA_private_manifest.json"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def normalize_label(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def masked_mean_pool(last_hidden_state: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
    mask = attention_mask.unsqueeze(-1).expand(last_hidden_state.size()).float()
    summed = torch.sum(last_hidden_state * mask, dim=1)
    counts = torch.clamp(mask.sum(dim=1), min=1e-9)
    return summed / counts


class PinnedEncoder:
    def __init__(self, cache_dir: pathlib.Path, batch_size: int):
        self.cache_dir = cache_dir
        self.batch_size = batch_size
        self.tokenizer = AutoTokenizer.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION, cache_dir=str(cache_dir)
        )
        self.model = AutoModel.from_pretrained(
            MODEL_ID, revision=MODEL_REVISION, cache_dir=str(cache_dir)
        )
        self.model.eval()
        actual_dim = int(self.model.config.hidden_size)
        if actual_dim != MODEL_DIMENSION:
            raise RuntimeError(f"model dimension drift: expected {MODEL_DIMENSION}, got {actual_dim}")

    def encode(self, texts: Sequence[str]) -> np.ndarray:
        chunks: list[np.ndarray] = []
        with torch.no_grad():
            for start in range(0, len(texts), self.batch_size):
                batch = list(texts[start : start + self.batch_size])
                tokens = self.tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    max_length=MODEL_MAX_LENGTH,
                    return_tensors="pt",
                )
                output = self.model(**tokens)
                pooled = masked_mean_pool(output.last_hidden_state, tokens["attention_mask"])
                pooled = torch.nn.functional.normalize(pooled, p=2, dim=1)
                chunks.append(pooled.cpu().numpy().astype(np.float32, copy=False))
        return np.vstack(chunks) if chunks else np.empty((0, MODEL_DIMENSION), dtype=np.float32)


def load_occupation_titles(zip_path: pathlib.Path) -> dict[str, str]:
    member = "db_26_1_text/Occupation Data.txt"
    with zipfile.ZipFile(zip_path) as archive:
        payload = archive.read(member).decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(payload), delimiter="\t")
    result: dict[str, str] = {}
    for row in reader:
        soc = (row.get("O*NET-SOC Code") or "").strip()
        title = (row.get("Title") or "").strip()
        if soc and title:
            result[soc] = title
    return result


def read_inputs(
    onet_csv: pathlib.Path,
    onet_zip: pathlib.Path,
    gdpval_parquet: pathlib.Path,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    onet = pd.read_csv(onet_csv, dtype={"task_id": str, "onet_soc": str})
    required_onet = {"task_id", "task_statement", "onet_soc"}
    if not required_onet <= set(onet.columns):
        raise ValueError(f"O*NET input missing columns: {sorted(required_onet - set(onet.columns))}")
    onet = onet.loc[:, ["task_id", "task_statement", "onet_soc"]].copy()
    for field in onet.columns:
        onet[field] = onet[field].fillna("").astype(str).str.strip()
    if len(onet) != onet["task_id"].nunique() or (onet == "").any().any():
        raise ValueError("O*NET task IDs must be unique and required fields complete")

    table = pq.read_table(gdpval_parquet, columns=["task_id", "occupation", "prompt"])
    gdpval = table.to_pandas()
    gdpval.columns = ["gdpval_task_id", "gdpval_occupation", "gdpval_prompt"]
    for field in gdpval.columns:
        gdpval[field] = gdpval[field].fillna("").astype(str).str.strip()
    if len(gdpval) != EXPECTED_GDPVAL_ROWS:
        raise ValueError(f"GDPval row-count drift: expected {EXPECTED_GDPVAL_ROWS}, got {len(gdpval)}")
    if len(gdpval) != gdpval["gdpval_task_id"].nunique() or (gdpval == "").any().any():
        raise ValueError("GDPval task IDs must be unique and required fields complete")

    titles = load_occupation_titles(onet_zip)
    missing_titles = sorted(set(onet["onet_soc"]) - set(titles))
    if missing_titles:
        raise ValueError(f"missing official occupation titles for {len(missing_titles)} O*NET-SOCs")
    return onet.sort_values("task_id", kind="mergesort").reset_index(drop=True), gdpval, titles


def build_blocks(
    onet: pd.DataFrame,
    gdpval: pd.DataFrame,
    titles: dict[str, str],
    encoder: PinnedEncoder,
) -> dict[str, list[int]]:
    socs = sorted(set(onet["onet_soc"]))
    labels = sorted(set(gdpval["gdpval_occupation"]), key=lambda value: (normalize_label(value), value))
    title_vectors = encoder.encode([titles[soc] for soc in socs])
    label_vectors = encoder.encode(labels)
    similarities = title_vectors @ label_vectors.T
    label_to_rows: dict[str, list[int]] = collections.defaultdict(list)
    for index, label in enumerate(gdpval["gdpval_occupation"]):
        label_to_rows[label].append(index)

    blocks: dict[str, list[int]] = {}
    for row_index, soc in enumerate(socs):
        ranked_labels = sorted(
            range(len(labels)),
            key=lambda index: (
                -float(similarities[row_index, index]),
                normalize_label(labels[index]),
                labels[index],
            ),
        )[:BLOCK_OCCUPATIONS]
        blocks[soc] = sorted(
            (task_index for label_index in ranked_labels for task_index in label_to_rows[labels[label_index]]),
            key=lambda index: gdpval.iloc[index]["gdpval_task_id"],
        )
        if not blocks[soc]:
            raise AssertionError(f"empty candidate block for O*NET-SOC {soc}")
    return blocks


def score_and_grade(
    onet: pd.DataFrame,
    gdpval: pd.DataFrame,
    blocks: dict[str, list[int]],
    encoder: PinnedEncoder,
) -> list[GradedMatch]:
    onet_vectors = encoder.encode(onet["task_statement"].tolist())
    gdpval_vectors = encoder.encode(gdpval["gdpval_prompt"].tolist())
    graded: list[GradedMatch] = []
    for index, row in onet.iterrows():
        block = blocks[row["onet_soc"]]
        scores = onet_vectors[index] @ gdpval_vectors[block].T
        candidates = [
            Candidate(
                onet_task_id=row["task_id"],
                gdpval_task_id=gdpval.iloc[gdpval_index]["gdpval_task_id"],
                # The release contract is [0, 1]; negative cosines contain no
                # threshold-relevant information and are deterministically clipped.
                similarity=round(max(0.0, min(1.0, float(score))), 8),
            )
            for gdpval_index, score in zip(block, scores)
        ]
        graded.append(grade_task(row["task_id"], candidates))
    if len(graded) != len(onet) or len({item.onet_task_id for item in graded}) != len(onet):
        raise AssertionError("grading failed to conserve exactly one row per O*NET task")
    return graded


def load_wage_allocations(path: pathlib.Path | None) -> tuple[dict[str, float], dict[str, float], dict[str, object]]:
    if path is None:
        return {}, {}, {"available": False}
    frame = pd.read_csv(path, dtype={"task_id": str, "onet_soc": str})
    required = {"vintage", "onet_soc", "task_id", "task_annual_wage_bill_allocation", "allocation_usable"}
    if not required <= set(frame.columns):
        raise ValueError(f"wage allocation input missing columns: {sorted(required - set(frame.columns))}")
    usable = frame[
        (pd.to_numeric(frame["vintage"], errors="coerce") == 2021)
        & frame["allocation_usable"].astype(str).str.casefold().eq("true")
    ].copy()
    usable["mass"] = pd.to_numeric(usable["task_annual_wage_bill_allocation"], errors="coerce")
    usable = usable[usable["mass"].notna() & (usable["mass"] >= 0)]
    if usable["task_id"].duplicated().any():
        raise ValueError("2021 usable wage allocations must be unique by task ID")
    task_mass = dict(zip(usable["task_id"].astype(str), usable["mass"].astype(float)))
    occupation_mass = usable.groupby("onet_soc", sort=True)["mass"].sum().astype(float).to_dict()
    total = float(usable["mass"].sum())
    shares = {soc: value / total for soc, value in occupation_mass.items()} if total else {}
    return task_mass, shares, {
        "available": True,
        "vintage": 2021,
        "source_sha256": sha256(path),
        "n_usable_tasks": len(task_mass),
        "total_annual_task_allocation_mass": round(total, 8),
        "interpretation": (
            "OEWS mean annual wage allocated across O*NET tasks; not employment-weighted "
            "dollars per completed task"
        ),
    }


def empirical_deciles(matches: list[GradedMatch]) -> dict[str, int]:
    ranked = sorted(
        matches,
        key=lambda item: (
            float("inf") if item.similarity is None else item.similarity,
            item.onet_task_id,
        ),
    )
    n = len(ranked)
    return {item.onet_task_id: min(10, 1 + (index * 10 // n)) for index, item in enumerate(ranked)} if n else {}


def quantiles(values: Iterable[float]) -> dict[str, float | int | None]:
    array = np.asarray(list(values), dtype=np.float64)
    if not len(array):
        return {"n": 0, "min": None, "p01": None, "p05": None, "p10": None, "p25": None,
                "p50": None, "p75": None, "p90": None, "p95": None, "p99": None, "max": None,
                "mean": None}
    result: dict[str, float | int | None] = {"n": int(len(array))}
    for label, q in [("min", 0), ("p01", .01), ("p05", .05), ("p10", .10), ("p25", .25),
                     ("p50", .50), ("p75", .75), ("p90", .90), ("p95", .95), ("p99", .99), ("max", 1)]:
        result[label] = round(float(np.quantile(array, q)), 8)
    result["mean"] = round(float(array.mean()), 8)
    return result


def model_cache_manifest(cache_dir: pathlib.Path) -> dict[str, object]:
    candidates = list(cache_dir.glob(f"models--sentence-transformers--all-MiniLM-L6-v2/snapshots/{MODEL_REVISION}"))
    if len(candidates) != 1:
        raise RuntimeError("could not resolve exact pinned model snapshot in cache")
    snapshot = candidates[0]
    files = []
    for path in sorted(item for item in snapshot.rglob("*") if item.is_file()):
        files.append({"path": str(path.relative_to(snapshot)), "bytes": path.stat().st_size, "sha256": sha256(path)})
    return {"n_files": len(files), "files": files, "manifest_sha256": canonical_json_sha256(files)}


def write_csv(path: pathlib.Path, fieldnames: list[str], records: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    path.chmod(0o600)


def execute(args: argparse.Namespace) -> dict[str, object]:
    random.seed(SEED)
    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.set_num_threads(args.torch_threads)
    torch.use_deterministic_algorithms(True)

    private_dir = args.private_output.resolve()
    receipt_path = args.receipt.resolve()
    if private_dir == receipt_path.parent or private_dir in receipt_path.parents:
        raise SystemExit("REFUSED: aggregate receipt must not be written inside the private output tree")
    private_dir.mkdir(parents=True, exist_ok=True)
    private_dir.chmod(0o700)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)

    onet, gdpval, titles = read_inputs(args.onet_csv, args.onet_zip, args.gdpval_parquet)
    encoder = PinnedEncoder(args.cache_dir, args.batch_size)
    blocks = build_blocks(onet, gdpval, titles, encoder)
    graded = score_and_grade(onet, gdpval, blocks, encoder)
    buckets = route(graded)
    task_to_soc = dict(zip(onet["task_id"], onet["onet_soc"]))
    coverage = coverage_by_occupation(graded, task_to_soc)
    top_quartile = top_quartile_flag(graded)
    task_mass, occupation_shares, wage_meta = load_wage_allocations(args.wage_allocations)

    model_label = f"{MODEL_ID}@{MODEL_REVISION}"
    mapping_records: list[dict[str, object]] = []
    for item in sorted(graded, key=lambda value: value.onet_task_id):
        soc = task_to_soc[item.onet_task_id]
        mapping_records.append({
            "onet_task_id": item.onet_task_id,
            "gdpval_task_id": item.gdpval_task_id or "",
            "similarity": "" if item.similarity is None else f"{item.similarity:.8f}",
            "runner_up_similarity": "" if item.runner_up_similarity is None else f"{item.runner_up_similarity:.8f}",
            "margin": "" if item.margin is None else f"{item.margin:.8f}",
            "grade": item.grade,
            "reason": item.reason,
            "onet_soc": soc,
            "occupation_coverage": f"{coverage[soc]['coverage']:.6f}",
            "coverage_below_floor": str(coverage[soc]["below_floor"]).lower(),
            "top_quartile_match_quality": str(item.onet_task_id in top_quartile).lower(),
            "adjudication_status": "pending_independent_cross_vendor" if item.needs_adjudication else "not_required",
            "embedding_model": model_label,
        })
    assert_release_safe(mapping_records)
    mapping_path = private_dir / PRIVATE_MAPPING
    write_csv(mapping_path, list(mapping_records[0]), mapping_records)

    queue = buckets["adjudication_queue"]
    deciles = empirical_deciles(queue)
    queue_sorted = sorted(
        queue,
        key=lambda item: (-occupation_shares.get(task_to_soc[item.onet_task_id], -1.0), item.onet_task_id),
    )
    queue_records: list[dict[str, object]] = []
    for queue_order, item in enumerate(queue_sorted, start=1):
        soc = task_to_soc[item.onet_task_id]
        ambiguous = (
            item.grade == GRADE_B
            and item.similarity is not None
            and item.similarity >= AUTO_ACCEPT_SIMILARITY
            and item.margin is not None
            and item.margin < AUTO_ACCEPT_MARGIN
        )
        queue_records.append({
            "queue_order": queue_order,
            "onet_task_id": item.onet_task_id,
            "gdpval_task_id": item.gdpval_task_id or "",
            "similarity": "" if item.similarity is None else f"{item.similarity:.8f}",
            "runner_up_similarity": "" if item.runner_up_similarity is None else f"{item.runner_up_similarity:.8f}",
            "margin": "" if item.margin is None else f"{item.margin:.8f}",
            "grade": item.grade,
            "machine_prelabel": "match" if item.grade == GRADE_B else "",
            "reason": item.reason,
            "onet_soc": soc,
            "occupation_family": soc.split("-")[0],
            "score_decile": deciles[item.onet_task_id],
            "ambiguity_flag": str(ambiguous).lower(),
            "occupation_wage_bill_share": (
                "" if soc not in occupation_shares else f"{occupation_shares[soc]:.12f}"
            ),
            "vendor_a_label": "",
            "vendor_b_label": "",
            "audit_status": "pending_independent_cross_vendor",
            "resolution": "",
        })
    if queue_records:
        assert_release_safe(queue_records)
        queue_path = private_dir / PRIVATE_QUEUE
        write_csv(queue_path, list(queue_records[0]), queue_records)
    else:
        queue_path = private_dir / PRIVATE_QUEUE
        write_csv(queue_path, ["queue_order", "onet_task_id", "gdpval_task_id"], [])

    coverage_records = [
        {
            "onet_soc": soc,
            "n_tasks": values["n_tasks"],
            "n_matched": values["n_matched"],
            "coverage": f"{values['coverage']:.6f}",
            "below_floor": str(values["below_floor"]).lower(),
            "wage_bill_share": "" if soc not in occupation_shares else f"{occupation_shares[soc]:.12f}",
        }
        for soc, values in sorted(coverage.items())
    ]
    coverage_path = private_dir / PRIVATE_COVERAGE
    write_csv(coverage_path, list(coverage_records[0]), coverage_records)

    matched_ids = {item.onet_task_id for item in graded if item.grade != UNMATCHED}
    mass_total = sum(task_mass.values())
    mass_matched = sum(value for task_id, value in task_mass.items() if task_id in matched_ids)
    scores = [item.similarity for item in graded if item.similarity is not None]
    queue_by_grade = collections.Counter(item.grade for item in queue)
    queue_by_decile = collections.Counter(deciles.values())
    queue_by_family = collections.Counter(task_to_soc[item.onet_task_id].split("-")[0] for item in queue)
    ambiguity_count = sum(record["ambiguity_flag"] == "true" for record in queue_records)
    private_outputs = {
        PRIVATE_MAPPING: {"rows": len(mapping_records), "sha256": sha256(mapping_path), "bytes": mapping_path.stat().st_size},
        PRIVATE_QUEUE: {"rows": len(queue_records), "sha256": sha256(queue_path), "bytes": queue_path.stat().st_size},
        PRIVATE_COVERAGE: {"rows": len(coverage_records), "sha256": sha256(coverage_path), "bytes": coverage_path.stat().st_size},
    }
    private_manifest = {
        "status": "PRIVATE_ID_LEVEL_ARTIFACTS_NOT_FOR_RELEASE",
        "outputs": private_outputs,
        "contains_task_text": False,
        "contains_gdpval_task_ids": True,
        "independent_annotation_complete": False,
    }
    manifest_path = private_dir / PRIVATE_MANIFEST
    manifest_path.write_text(json.dumps(private_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path.chmod(0o600)

    receipt: dict[str, object] = {
        "status": "MAPA_EXECUTED_QUEUE_FROZEN_AUDIT_PENDING",
        "executed_at_utc": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "lineage": {
            "controlled_base_sha": "4255f76d08a6afebc51c0d8751eb0f808a5e4069",
            "integration_sha": "dd1f97b51137ce88ad044f86b5453d29a9eed696",
            "source_evidence_sha": "093aba628454d9bf740931654b5a51bc82bfe510",
            "applied_evidence_sha": "bc2d9d3d063041a7981f466b5e9e81b7abb5ab4e",
            "stable_evidence_patch_id": "a59896b6804c00882d62cb768c9232abe8530101",
        },
        "inputs": {
            "onet_timeshares": {"sha256": sha256(args.onet_csv), "rows": len(onet)},
            "onet_source_zip": {"sha256": sha256(args.onet_zip), "occupations": len(titles)},
            "gdpval_open_gold": {"sha256": sha256(args.gdpval_parquet), "rows": len(gdpval)},
            "wage_allocations": wage_meta,
        },
        "model": {
            "id": MODEL_ID,
            "revision": MODEL_REVISION,
            "license": MODEL_LICENSE,
            "dimension": MODEL_DIMENSION,
            "max_length": MODEL_MAX_LENGTH,
            "pooling": "attention-mask mean pooling then L2 normalization",
            "runtime": {"python": "3.10.12", "torch": torch.__version__, "transformers": "4.25.1"},
            "cache_manifest": model_cache_manifest(args.cache_dir),
        },
        "blocking": {
            "method": "top-k semantic adjacency between official O*NET titles and GDPval occupation labels",
            "gdpval_occupation_labels_per_block": BLOCK_OCCUPATIONS,
            "n_onet_occupations": len(blocks),
            "candidate_count": quantiles(len(block) for block in blocks.values()),
        },
        "thresholds": {
            "similarity_floor": SIMILARITY_FLOOR,
            "auto_accept_similarity": AUTO_ACCEPT_SIMILARITY,
            "auto_accept_margin": AUTO_ACCEPT_MARGIN,
            "occupation_coverage_floor": COVERAGE_FLOOR,
        },
        "results": {
            "n_onet_tasks": len(graded),
            "accepted": len(buckets["accepted"]),
            "queued": len(queue),
            "unmatched": len(buckets["unmatched"]),
            "partition_conserved": sum(len(value) for value in buckets.values()) == len(graded),
            "matched_or_queued_coverage": round(len(matched_ids) / len(graded), 8),
            "score_distribution": quantiles(scores),
            "grade_counts": dict(sorted(collections.Counter(item.grade for item in graded).items())),
            "n_occupations": len(coverage),
            "occupations_below_coverage_floor": sum(bool(item["below_floor"]) for item in coverage.values()),
            "top_quartile_flag_count": len(top_quartile),
            "wage_bill_coverage": (
                None if not mass_total else round(mass_matched / mass_total, 8)
            ),
            "wage_bill_usable_task_count": len(task_mass),
        },
        "adjudication_queue": {
            "status": "FROZEN_PENDING_INDEPENDENT_CROSS_VENDOR_ANNOTATION_AND_T1_AUDIT",
            "size": len(queue),
            "grade_counts": dict(sorted(queue_by_grade.items())),
            "score_decile_counts": {str(key): value for key, value in sorted(queue_by_decile.items())},
            "occupation_family_counts": dict(sorted(queue_by_family.items())),
            "ambiguity_count": ambiguity_count,
            "audit_rule": "10% stratified by occupation family, score decile, and ambiguity flag",
            "acceptance_rule": "weighted Cohen kappa >= 0.70 and binary crossing-relevant agreement >= 0.90",
            "machine_judgments_certified_as_audited": False,
        },
        "private_outputs": private_outputs,
        "private_manifest_sha256": sha256(manifest_path),
        "release": {
            "id_level_artifacts_committed": False,
            "reason": "GDPval task-ID redistribution rights not affirmatively documented; manifest only",
            "task_text_committed": False,
            "outcomes_opened": False,
        },
        "remaining_dependency": "independent cross-vendor annotation plus T1 stratified audit of queued B/C judgments",
    }
    assert_release_safe([receipt])
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--onet-csv", type=pathlib.Path, required=True)
    parser.add_argument("--onet-zip", type=pathlib.Path, required=True)
    parser.add_argument("--gdpval-parquet", type=pathlib.Path, required=True)
    parser.add_argument("--wage-allocations", type=pathlib.Path)
    parser.add_argument("--private-output", type=pathlib.Path, required=True)
    parser.add_argument("--receipt", type=pathlib.Path, required=True)
    parser.add_argument("--cache-dir", type=pathlib.Path, required=True)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--torch-threads", type=int, default=4)
    args = parser.parse_args()
    print(json.dumps(execute(args), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
