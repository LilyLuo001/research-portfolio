#!/usr/bin/env python3
"""Aggregate two bounded development reviews without exposing row-level data publicly."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from run_local import file_sha256, load_source_pack, write_json, write_jsonl
from expand_compact_labels import expand_record
from validate_extraction import validate_record


OBJECTS = ("general_work", "occupation_task", "industry_domain", "specific_tool")
UNKNOWN_STATES = {"unresolved", "insufficient_text"}


def read_annotations(paths: list[Path], label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                record_id = str(row.get("record_id", ""))
                if not record_id:
                    raise ValueError(f"{label} {path}:{line_number} missing record_id")
                if record_id in result:
                    raise ValueError(f"{label} duplicate record_id: {record_id}")
                result[record_id] = row
    if not result:
        raise ValueError(f"{label} has no completed records")
    return result


def experience_map(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {finding["object"]: finding for finding in row["experience_findings"]}


def state_signature(row: dict[str, Any], obj: str) -> str:
    return experience_map(row)[obj]["state"]


def mode_signature(row: dict[str, Any], obj: str) -> tuple[bool, tuple[str, ...]]:
    modes = {mention["condition_mode"] for mention in experience_map(row)[obj]["mentions"]}
    return "prior_experience" in modes, tuple(sorted(modes - {"prior_experience"}))


def duration_branch_signature(row: dict[str, Any], obj: str) -> tuple[Any, ...]:
    finding = experience_map(row)[obj]
    mentions = [item for item in finding["mentions"] if item["duration"] is not None]
    groups: dict[str, str] = {}
    normalized = []
    for mention in mentions:
        group = mention["alternative_group"]
        if group is not None and group not in groups:
            groups[group] = f"g{len(groups) + 1}"
        duration = mention["duration"]
        duration_tuple = (
            duration["unit"], duration["interpretation"], duration["stated_value"],
            duration["lower"], duration["upper"],
        )
        normalized.append((
            mention["condition_mode"], mention["strength"], mention["branch_relation"],
            groups.get(group), duration_tuple,
        ))
    return tuple(normalized)


def technology_signature(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(sorted({
        (item["technology_class"], item["state"], item["technology_role"])
        for item in row["technology_findings"]
    }))


def mention_granularity_signature(row: dict[str, Any], obj: str) -> int:
    return len(experience_map(row)[obj]["mentions"])


def compare_metric(
    ids: list[str], digests: dict[str, str], terra: dict[str, dict[str, Any]], sol: dict[str, dict[str, Any]],
    signature: Callable[[dict[str, Any]], Any],
) -> dict[str, Any]:
    record_agree = sum(signature(terra[record_id]) == signature(sol[record_id]) for record_id in ids)
    by_digest: dict[str, list[str]] = defaultdict(list)
    for record_id in ids:
        by_digest[digests[record_id]].append(record_id)
    text_agree = 0
    within_model_inconsistent = {"terra": 0, "sol": 0}
    for group_ids in by_digest.values():
        terra_values = {repr(signature(terra[record_id])) for record_id in group_ids}
        sol_values = {repr(signature(sol[record_id])) for record_id in group_ids}
        within_model_inconsistent["terra"] += len(terra_values) > 1
        within_model_inconsistent["sol"] += len(sol_values) > 1
        text_agree += len(terra_values) == 1 and terra_values == sol_values
    return {
        "record_level": {"agree": record_agree, "total": len(ids), "fraction": record_agree / len(ids)},
        "distinct_text_level": {"agree": text_agree, "total": len(by_digest), "fraction": text_agree / len(by_digest)},
        "within_model_duplicate_text_inconsistency_groups": within_model_inconsistent,
    }


def disagreement_reasons(terra: dict[str, Any], sol: dict[str, Any]) -> tuple[list[str], int]:
    reasons, score = [], 0
    if technology_signature(terra) != technology_signature(sol):
        reasons.append("technology_class_role")
        score += 100
    for obj in OBJECTS:
        if state_signature(terra, obj) != state_signature(sol, obj):
            reasons.append(f"{obj}:state")
            score += 80
        if mode_signature(terra, obj) != mode_signature(sol, obj):
            reasons.append(f"{obj}:prior_vs_other_mode")
            score += 60
        if duration_branch_signature(terra, obj) != duration_branch_signature(sol, obj):
            reasons.append(f"{obj}:duration_branch")
            score += 50
    return reasons, score


def stable_rank(record_id: str, phase: str) -> str:
    return hashlib.sha256(f"20261004|{phase}|{record_id}".encode()).hexdigest()


def agreement_bundle(
    ids: list[str], digests: dict[str, str], first: dict[str, dict[str, Any]], second: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    return {
        "experience_state": {obj: compare_metric(ids, digests, first, second, lambda row, obj=obj: state_signature(row, obj)) for obj in OBJECTS},
        "prior_experience_vs_other_modes": {obj: compare_metric(ids, digests, first, second, lambda row, obj=obj: mode_signature(row, obj)) for obj in OBJECTS},
        "duration_and_branch": {obj: compare_metric(ids, digests, first, second, lambda row, obj=obj: duration_branch_signature(row, obj)) for obj in OBJECTS},
        "mention_granularity": {obj: compare_metric(ids, digests, first, second, lambda row, obj=obj: mention_granularity_signature(row, obj)) for obj in OBJECTS},
        "technology_class_role": compare_metric(ids, digests, first, second, technology_signature),
    }


def semantic_change_counts(ids: list[str], before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "experience_state_records": {obj: sum(state_signature(before[record_id], obj) != state_signature(after[record_id], obj) for record_id in ids) for obj in OBJECTS},
        "condition_mode_records": {obj: sum(mode_signature(before[record_id], obj) != mode_signature(after[record_id], obj) for record_id in ids) for obj in OBJECTS},
        "duration_branch_records": {obj: sum(duration_branch_signature(before[record_id], obj) != duration_branch_signature(after[record_id], obj) for record_id in ids) for obj in OBJECTS},
        "technology_class_role_records": sum(technology_signature(before[record_id]) != technology_signature(after[record_id]) for record_id in ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--terra", type=Path, action="append", required=True)
    parser.add_argument("--sol", type=Path, action="append", required=True)
    parser.add_argument("--terra-first-pass", type=Path, action="append")
    parser.add_argument("--sol-first-pass", type=Path, action="append")
    parser.add_argument("--public-output", type=Path, required=True)
    parser.add_argument("--private-queue", type=Path, required=True)
    parser.add_argument("--max-disagreements", type=int, default=32)
    parser.add_argument("--max-agreements", type=int, default=8)
    args = parser.parse_args()
    if not 0 <= args.max_disagreements <= 32 or not 0 <= args.max_agreements <= 8:
        raise ValueError("queue caps are at most 32 disagreements and 8 agreements")

    sources = load_source_pack(args.source)
    source_by_id = {str(row["record_id"]): row for row in sources}
    terra = read_annotations(args.terra, "terra")
    sol = read_annotations(args.sol, "sol")
    if set(terra) != set(sol):
        raise ValueError("Terra and Sol completed record_id sets differ")
    unknown_ids = set(terra) - set(source_by_id)
    if unknown_ids:
        raise ValueError(f"review record_ids absent from frozen source pack: {sorted(unknown_ids)[:3]}")
    ids = sorted(terra)
    for label, annotations in (("terra", terra), ("sol", sol)):
        for record_id in ids:
            errors = validate_record(annotations[record_id], source_by_id[record_id]["original_text"], record_id)
            if errors:
                raise ValueError(f"{label} {record_id} failed frozen validation: {errors[:3]}")

    digests = {record_id: source_by_id[record_id]["source_text_sha256"] for record_id in ids}
    digest_groups: dict[str, list[str]] = defaultdict(list)
    for record_id in ids:
        digest_groups[digests[record_id]].append(record_id)

    agreement = agreement_bundle(ids, digests, terra, sol)
    first_pass = None
    if bool(args.terra_first_pass) != bool(args.sol_first_pass):
        raise ValueError("provide first-pass compact files for both models or neither")
    if args.terra_first_pass:
        terra_first = read_annotations(args.terra_first_pass, "terra_first_pass")
        sol_first = read_annotations(args.sol_first_pass, "sol_first_pass")
        if set(terra_first) != set(sol_first) or set(terra_first) != set(ids):
            raise ValueError("first-pass and quote-repaired record_id sets must match exactly")
        quote_valid = {}
        for label, annotations in (("terra", terra_first), ("sol", sol_first)):
            valid = 0
            for record_id in ids:
                try:
                    expanded = expand_record(annotations[record_id], source_by_id[record_id]["original_text"])
                    valid += not validate_record(expanded, source_by_id[record_id]["original_text"], record_id)
                except (KeyError, TypeError, ValueError):
                    pass
            quote_valid[label] = {"valid_records": valid, "total_records": len(ids), "fraction": valid / len(ids)}
        first_pass = {
            "quote_expansion_validity": quote_valid,
            "model_agreement_before_quote_repair": agreement_bundle(ids, digests, terra_first, sol_first),
            "semantic_changes_during_quote_repair": {
                "terra": semantic_change_counts(ids, terra_first, terra),
                "sol": semantic_change_counts(ids, sol_first, sol),
            },
            "interpretation": "Quote repair is mechanical only; any nonzero semantic-change count is a protocol deviation and is not used to improve first-pass agreement.",
        }
    unknown = {}
    for label, annotations in (("terra", terra), ("sol", sol)):
        unknown[label] = {
            "experience_by_object": {
                obj: {
                    "records": sum(state_signature(annotations[record_id], obj) in UNKNOWN_STATES for record_id in ids),
                    "fraction": sum(state_signature(annotations[record_id], obj) in UNKNOWN_STATES for record_id in ids) / len(ids),
                    "distinct_text_groups": sum(any(state_signature(annotations[record_id], obj) in UNKNOWN_STATES for record_id in group_ids) for group_ids in digest_groups.values()),
                }
                for obj in OBJECTS
            },
            "records_with_any_technology_unknown": sum(
                any(item["state"] in UNKNOWN_STATES for item in annotations[record_id]["technology_findings"])
                for record_id in ids
            ),
        }

    candidates = []
    for record_id in ids:
        reasons, score = disagreement_reasons(terra[record_id], sol[record_id])
        candidates.append({"record_id": record_id, "digest": digests[record_id], "reasons": reasons, "score": score})
    per_digest = {}
    for item in candidates:
        previous = per_digest.get(item["digest"])
        rank = (-item["score"], stable_rank(item["record_id"], "adjudication"))
        if previous is None or rank < previous[0]:
            per_digest[item["digest"]] = (rank, item)
    unique_candidates = [value[1] for value in per_digest.values()]
    disagreements = sorted((item for item in unique_candidates if item["reasons"]), key=lambda item: (-item["score"], stable_rank(item["record_id"], "disagreement")))[:args.max_disagreements]
    agreements = sorted((item for item in unique_candidates if not item["reasons"]), key=lambda item: stable_rank(item["record_id"], "agreement"))[:args.max_agreements]
    queue_rows = []
    for selection_type, selected in (("high_impact_disagreement", disagreements), ("agreement_common_error_check", agreements)):
        for item in selected:
            record_id = item["record_id"]
            queue_rows.append({
                "queue_rank": len(queue_rows) + 1, "selection_type": selection_type,
                "record_id": record_id, "source_text_sha256": item["digest"],
                "original_text": source_by_id[record_id]["original_text"], "reasons": item["reasons"],
                "terra_annotation": terra[record_id], "sol_annotation": sol[record_id],
            })
    args.private_queue.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.private_queue, queue_rows)
    os.chmod(args.private_queue, 0o600)

    public = {
        "version": "development_comparison_aggregate_v1.0.0",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "partial_completed_same_record_set" if len(ids) < 80 else "frozen_80_development_set",
        "configurations": {"terra": "gpt-5.6-terra/medium", "sol": "gpt-5.6-sol/medium"},
        "coverage": {
            "records_each": len(ids), "exact_unique_record_ids_each": True,
            "same_record_id_set": True, "distinct_texts": len(digest_groups),
            "duplicate_text_groups": sum(len(group) > 1 for group in digest_groups.values()),
            "rows_in_duplicate_text_groups": sum(len(group) for group in digest_groups.values() if len(group) > 1),
        },
        "validation": {"terra_frozen_schema_and_evidence_valid": len(ids), "sol_frozen_schema_and_evidence_valid": len(ids)},
        "first_pass_diagnostics": first_pass,
        "agreement_diagnostics": agreement,
        "unknown_diagnostics": unknown,
        "adjudication_queue": {
            "high_impact_disagreements": len(disagreements), "agreement_common_error_checks": len(agreements),
            "total": len(queue_rows), "distinct_text_only": True, "private_queue_sha256": file_sha256(args.private_queue),
        },
        "privacy": {
            "authorized_conversation_agents_received_text": True,
            "no_separate_batch_api": True,
            "no_microdata_or_record_ids_in_public_output": True,
        },
        "limits": [
            "development model-versus-model diagnostic, not truth accuracy or a population error rate",
            "duplicate text is reported at record and distinct-text levels and is not independent evidence",
            "72 known review JOB_HASH values were excluded upstream; cross-key historical same-text and unavailable heldout-400 contamination remain incompletely verified",
            "no evaluation labels or formal economic results are included",
        ],
        "inputs": {
            "source_sha256": file_sha256(args.source),
            "terra_files_sha256": [file_sha256(path) for path in args.terra],
            "sol_files_sha256": [file_sha256(path) for path in args.sol],
        },
    }
    args.public_output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.public_output, public)
    print(args.public_output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
