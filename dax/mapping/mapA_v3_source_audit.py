#!/usr/bin/env python3
"""Prospective development-only source-side audit for a Mapping A v3 decision.

This diagnostic selects O*NET source tasks without inspecting candidate text,
then materializes every candidate in the frozen union of dense top-10,
lexical top-10, and RRF top-10.  It refuses locked-test sources and excludes
the earlier 60-pair diagnostic sources.  It does not estimate validation
performance or alter Mapping A v2.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import pathlib
import re
from collections.abc import Iterable, Mapping

import numpy as np
import pandas as pd


AUDIT_SEED = "DAX-MAPA-V3-SOURCE-AUDIT-20260823"
ALLOWED_SPLIT = "development"
MODALITIES = ("physical_manual", "interpersonal_service", "technical_analytic")
SOURCES_PER_MODALITY = 2
TOP_K = 10
LABELS = frozenset({"D", "F", "N", "U"})


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _stable(value: str) -> str:
    return hashlib.sha256(f"{AUDIT_SEED}|{value}".encode()).hexdigest()


def classify_modality(statement: str) -> str:
    tokens = set(re.findall(r"[a-z]+", statement.casefold()))
    physical = {
        "operate", "load", "unload", "clean", "repair", "install", "assemble",
        "remove", "move", "cut", "pack", "wash", "drive", "lift", "apply",
        "prepare", "maintain", "adjust", "connect", "fill",
    }
    interpersonal = {
        "advise", "teach", "counsel", "interview", "negotiate", "assist",
        "encourage", "instruct", "care", "communicate", "explain", "serve",
        "supervise", "arbitrate", "respond",
    }
    if tokens & physical:
        return "physical_manual"
    if tokens & interpersonal:
        return "interpersonal_service"
    return "technical_analytic"


def select_sources(
    validation_rows: Iterable[Mapping[str, object]],
    statements: Mapping[str, str],
    excluded_source_ids: set[str],
) -> list[dict[str, str]]:
    development: dict[str, dict[str, str]] = {}
    for original in validation_rows:
        row = {key: str(value).strip() for key, value in original.items()}
        if row.get("split") != ALLOWED_SPLIT:
            continue
        source = row["onet_task_id"]
        if source in excluded_source_ids:
            continue
        if source not in statements:
            raise ValueError("validation source absent from O*NET task universe")
        development[source] = {
            "onet_task_id": source,
            "major_soc_family": row["major_soc_family"],
            "statement": statements[source],
            "modality": classify_modality(statements[source]),
        }

    selected: list[dict[str, str]] = []
    used_families: set[str] = set()
    for modality in MODALITIES:
        pool = [row for row in development.values() if row["modality"] == modality]
        for _ in range(SOURCES_PER_MODALITY):
            available = [row for row in pool if row not in selected]
            if not available:
                raise ValueError(f"insufficient development sources for {modality}")
            winner = min(
                available,
                key=lambda row: (
                    row["major_soc_family"] in used_families,
                    _stable(f'{modality}|{row["onet_task_id"]}'),
                ),
            )
            selected.append(winner)
            used_families.add(winner["major_soc_family"])
    return sorted(selected, key=lambda row: _stable(f'packet-order|{row["onet_task_id"]}'))


def relevant_candidate_indices(dense: np.ndarray, lexical: np.ndarray, target_ids: list[str]) -> list[int]:
    if dense.shape != lexical.shape or dense.ndim != 1 or len(dense) != len(target_ids):
        raise ValueError("candidate score vector drift")
    dense_order = sorted(range(len(target_ids)), key=lambda i: (-float(dense[i]), target_ids[i]))
    lexical_order = sorted(range(len(target_ids)), key=lambda i: (-float(lexical[i]), target_ids[i]))
    dense_rank = {index: rank for rank, index in enumerate(dense_order, start=1)}
    lexical_rank = {index: rank for rank, index in enumerate(lexical_order, start=1)}
    rrf_order = sorted(
        range(len(target_ids)),
        key=lambda i: (-(1 / (60 + dense_rank[i]) + 1 / (60 + lexical_rank[i])), target_ids[i]),
    )
    union = set(dense_order[:TOP_K]) | set(lexical_order[:TOP_K]) | set(rrf_order[:TOP_K])
    return sorted(
        union,
        key=lambda i: (
            -max(1 / (60 + dense_rank[i]), 1 / (60 + lexical_rank[i])),
            target_ids[i],
        ),
    )


def _write_csv(path: pathlib.Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    path.chmod(0o600)


def freeze(args: argparse.Namespace) -> dict[str, object]:
    private_dir = args.private_dir.resolve()
    receipt_path = args.receipt.resolve()
    if private_dir == receipt_path.parent or private_dir in receipt_path.parents:
        raise SystemExit("REFUSED: release receipt must be outside private directory")
    private_dir.mkdir(parents=True, exist_ok=True)
    private_dir.chmod(0o700)

    validation = pd.read_csv(args.validation_pairs, dtype=str).fillna("")
    if "relation_label" in validation and validation["relation_label"].str.strip().ne("").any():
        raise ValueError("source audit refuses any populated validation label")
    diagnostic = pd.read_csv(args.prior_diagnostic_sample, dtype=str).fillna("")
    excluded = set(diagnostic["onet_task_id"])
    onet = pd.read_csv(args.onet_csv, dtype={"task_id": str}).fillna("")
    statements = dict(zip(onet["task_id"].astype(str), onet["task_statement"].astype(str)))
    sources = select_sources(validation.to_dict("records"), statements, excluded)

    ordered_ids = json.loads(args.ordered_ids.read_text(encoding="utf-8"))
    onet_ids = [str(value) for value in ordered_ids["onet_task_ids"]]
    target_ids = [str(value) for value in ordered_ids["gdpval_task_ids"]]
    if len(onet_ids) != 19259 or len(target_ids) != 220:
        raise ValueError("frozen score universe drift")
    score_file = np.load(args.full_scores, allow_pickle=False)
    dense = score_file["dense"]
    lexical = score_file["lexical"]
    if dense.shape != (19259, 220) or lexical.shape != (19259, 220):
        raise ValueError("frozen score matrix drift")
    onet_index = {task_id: index for index, task_id in enumerate(onet_ids)}
    target_index = {task_id: index for index, task_id in enumerate(target_ids)}
    gdpval = pd.read_parquet(args.gdpval_parquet).fillna("")
    gdpval_by_id = {str(row["task_id"]): row for _, row in gdpval.iterrows()}
    if set(target_ids) != set(gdpval_by_id):
        raise ValueError("GDPval universe drift")

    source_rows: list[dict[str, object]] = []
    candidate_rows: list[dict[str, object]] = []
    packets: list[dict[str, object]] = []
    candidate_index = 0
    for source_index, source in enumerate(sources, start=1):
        source_id = source["onet_task_id"]
        row_index = onet_index[source_id]
        candidates = relevant_candidate_indices(dense[row_index], lexical[row_index], target_ids)
        dense_order = sorted(range(220), key=lambda i: (-float(dense[row_index, i]), target_ids[i]))
        lexical_order = sorted(range(220), key=lambda i: (-float(lexical[row_index, i]), target_ids[i]))
        dense_rank = {index: rank for rank, index in enumerate(dense_order, start=1)}
        lexical_rank = {index: rank for rank, index in enumerate(lexical_order, start=1)}
        source_rows.append({
            "source_index": source_index,
            "onet_task_id": source_id,
            "major_soc_family": source["major_soc_family"],
            "modality": source["modality"],
            "relevant_candidates": len(candidates),
        })
        for column in candidates:
            candidate_index += 1
            target_id = target_ids[column]
            target = gdpval_by_id[target_id]
            candidate_rows.append({
                "candidate_index": candidate_index,
                "source_index": source_index,
                "onet_task_id": source_id,
                "gdpval_task_id": target_id,
                "dense_rank": dense_rank[column],
                "lexical_rank": lexical_rank[column],
            })
            packets.append({
                "candidate_index": candidate_index,
                "source_index": source_index,
                "onet_task": {"statement": source["statement"], "modality": source["modality"]},
                "gdpval_task": {
                    "sector": str(target["sector"]),
                    "occupation": str(target["occupation"]),
                    "prompt": str(target["prompt"]),
                    "rubric": str(target["rubric_pretty"]),
                },
                "retrieval_ranks": {"dense": dense_rank[column], "lexical": lexical_rank[column]},
            })

    sources_path = private_dir / "mapA_v3_source_audit_sources.csv"
    candidates_path = private_dir / "mapA_v3_source_audit_candidates.csv"
    packets_path = private_dir / "mapA_v3_source_audit_packets.jsonl"
    template_path = private_dir / "mapA_v3_source_audit_labels_template.csv"
    _write_csv(sources_path, source_rows)
    _write_csv(candidates_path, candidate_rows)
    packets_path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in packets), encoding="utf-8")
    packets_path.chmod(0o600)
    _write_csv(template_path, [
        {"candidate_index": row["candidate_index"], "relation_label": "", "concise_rationale": ""}
        for row in candidate_rows
    ])

    receipt = {
        "status": "V3_SOURCE_SIDE_DIAGNOSTIC_SAMPLE_FROZEN_LABELS_PENDING",
        "scope": "development_sources_only_excluding_prior_diagnostic_sources",
        "seed": AUDIT_SEED,
        "source_tasks": len(source_rows),
        "sources_by_modality": dict(sorted(collections.Counter(row["modality"] for row in source_rows).items())),
        "major_soc_families": len({row["major_soc_family"] for row in source_rows}),
        "candidate_definition": "union_dense_top10_lexical_top10_rrf_top10",
        "candidate_pairs_for_manual_inspection": len(candidate_rows),
        "candidates_per_source": {
            "minimum": min(row["relevant_candidates"] for row in source_rows),
            "maximum": max(row["relevant_candidates"] for row in source_rows),
        },
        "prior_diagnostic_sources_excluded": len(excluded),
        "locked_test_sources_selected": 0,
        "locked_test_labels_opened": False,
        "formal_validation_performance_claimed": False,
        "v2_method_or_threshold_changed": False,
        "incremental_api_spend_usd": 0,
        "private_artifact_hashes": {
            path.name: sha256(path) for path in (sources_path, candidates_path, packets_path, template_path)
        },
        "row_level_data_committed": False,
    }
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def evaluate(args: argparse.Namespace) -> dict[str, object]:
    private_dir = args.private_dir.resolve()
    sources = pd.read_csv(private_dir / "mapA_v3_source_audit_sources.csv", dtype=str).fillna("")
    candidates = pd.read_csv(private_dir / "mapA_v3_source_audit_candidates.csv", dtype=str).fillna("")
    labels = pd.read_csv(args.labels, dtype=str).fillna("")
    required = {"candidate_index", "relation_label", "concise_rationale"}
    if not required <= set(labels):
        raise ValueError("source-audit label schema incomplete")
    labels["relation_label"] = labels["relation_label"].str.upper().str.strip()
    if set(labels["relation_label"]) - LABELS or labels["concise_rationale"].str.strip().eq("").any():
        raise ValueError("invalid or unexplained source-audit label")
    if len(labels) != len(candidates) or labels["candidate_index"].duplicated().any():
        raise ValueError("source-audit labels must cover every frozen candidate once")
    merged = candidates.merge(labels, on="candidate_index", validate="one_to_one")
    if len(merged) != len(candidates):
        raise ValueError("source-audit candidate/label mismatch")
    by_source = []
    for source_index, group in merged.groupby("source_index", sort=True):
        counts = collections.Counter(group["relation_label"])
        source = sources.loc[sources["source_index"] == str(source_index)].iloc[0]
        by_source.append({
            "source_index_release": int(source_index),
            "modality": source["modality"],
            "candidates_inspected": len(group),
            "relation_counts": {label: counts[label] for label in sorted(LABELS)},
            "any_direct_substitute": counts["D"] > 0,
        })
    total = collections.Counter(merged["relation_label"])
    receipt = {
        "status": "V3_SOURCE_SIDE_QUALITATIVE_AUDIT_COMPLETE_NOT_FORMAL_VALIDATION",
        "scope": "development_sources_only_excluding_prior_diagnostic_sources",
        "source_tasks": len(by_source),
        "candidate_pairs_inspected": len(merged),
        "aggregate_relation_counts": {label: total[label] for label in sorted(LABELS)},
        "sources_with_any_plausible_direct_substitute": sum(row["any_direct_substitute"] for row in by_source),
        "source_level_sanitized_results": by_source,
        "interpretation_limits": {
            "formal_validation_performance_claimed": False,
            "candidate_recall_claimed": False,
            "population_prevalence_claimed": False,
            "locked_test_read": False,
            "v2_changed": False,
        },
        "private_input_hashes": {
            "sources_sha256": sha256(private_dir / "mapA_v3_source_audit_sources.csv"),
            "candidates_sha256": sha256(private_dir / "mapA_v3_source_audit_candidates.csv"),
            "labels_sha256": sha256(args.labels.resolve()),
        },
        "row_level_data_committed": False,
        "incremental_api_spend_usd": 0,
    }
    output = args.receipt.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    sub = value.add_subparsers(dest="command", required=True)
    freeze_parser = sub.add_parser("freeze")
    freeze_parser.add_argument("--validation-pairs", type=pathlib.Path, required=True)
    freeze_parser.add_argument("--prior-diagnostic-sample", type=pathlib.Path, required=True)
    freeze_parser.add_argument("--full-scores", type=pathlib.Path, required=True)
    freeze_parser.add_argument("--ordered-ids", type=pathlib.Path, required=True)
    freeze_parser.add_argument("--onet-csv", type=pathlib.Path, required=True)
    freeze_parser.add_argument("--gdpval-parquet", type=pathlib.Path, required=True)
    freeze_parser.add_argument("--private-dir", type=pathlib.Path, required=True)
    freeze_parser.add_argument("--receipt", type=pathlib.Path, required=True)
    evaluate_parser = sub.add_parser("evaluate")
    evaluate_parser.add_argument("--private-dir", type=pathlib.Path, required=True)
    evaluate_parser.add_argument("--labels", type=pathlib.Path, required=True)
    evaluate_parser.add_argument("--receipt", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    arguments = parser().parse_args()
    result = freeze(arguments) if arguments.command == "freeze" else evaluate(arguments)
    print(json.dumps(result, indent=2, sort_keys=True))
