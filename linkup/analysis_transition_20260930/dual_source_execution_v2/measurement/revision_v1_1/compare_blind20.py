#!/usr/bin/env python3
"""Aggregate the bounded blind20 two-reader comparison without row disclosure."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


OBJECTS = ("general_work", "occupation_task", "industry_domain", "specific_tool")
AI_CLASSES = {"predictive_ml_ai", "generative_ai", "ai_unspecified"}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def keyed(rows: list[dict[str, Any]], path: Path) -> dict[str, dict[str, Any]]:
    result = {str(row["record_id"]): row for row in rows}
    if len(result) != len(rows):
        raise ValueError(f"duplicate record_id in {path}")
    return result


def findings(row: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {finding["object"]: finding for finding in row["experience_findings"]}


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def duration_signature(row: dict[str, Any], obj: str) -> tuple[tuple[Any, ...], ...]:
    signatures = []
    for mention in findings(row)[obj]["mentions"]:
        duration = mention.get("duration")
        if not duration:
            continue
        value = duration.get("value", duration.get("stated_value"))
        lower, upper = duration.get("lower"), duration.get("upper")
        if not any(is_number(item) for item in (value, lower, upper)):
            continue
        signatures.append((
            obj,
            mention.get("condition_mode"),
            mention.get("strength"),
            mention.get("qualification_scope"),
            duration.get("unit"),
            duration.get("interpretation"),
            value,
            (lower, upper),
            mention.get("branch_relation"),
        ))
    return tuple(sorted(signatures, key=repr))


def nonduration_count(row: dict[str, Any], obj: str) -> int:
    return sum(mention.get("duration") is None for mention in findings(row)[obj]["mentions"])


def technology_signature(row: dict[str, Any]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted({
        (finding["technology_class"], finding["technology_role"])
        for finding in row["technology_findings"]
        if finding.get("state") == "explicit_positive" and finding.get("applicant_context") is True
    }))


def agreement(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    total = len(left)
    agree = sum(left[key] == right[key] for key in left)
    return {"agree_records": agree, "total_records": total, "fraction": agree / total if total else None}


def load_arm_manifest(path: Path, ids: set[str]) -> dict[str, str]:
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        import pyarrow.parquet as pq
        rows = pq.read_table(path).to_pylist()
    elif suffix == ".jsonl":
        rows = read_jsonl(path)
    elif suffix == ".json":
        payload = json.loads(path.read_text(encoding="utf-8"))
        rows = payload if isinstance(payload, list) else payload.get("records", payload.get("rows", []))
    else:
        raise ValueError("--armmanifest must be .parquet, .jsonl, or .json")
    arm_by_id = {}
    for row in rows:
        record_id = str(row.get("record_id", row.get("JOB_HASH", "")))
        if record_id in ids:
            arm_by_id[record_id] = str(row["arm"])
    if set(arm_by_id) != ids:
        raise ValueError("arm manifest does not cover the exact blind20 record set")
    if Counter(arm_by_id.values()) != Counter({"A": 10, "B": 10}):
        raise ValueError("arm manifest does not recover the expected original A10/B10 groups")
    return arm_by_id


def arm_presence(rows: dict[str, dict[str, Any]], arm_by_id: dict[str, str]) -> dict[str, Any]:
    output = {}
    for arm in ("A", "B"):
        arm_ids = [record_id for record_id, value in arm_by_id.items() if value == arm]
        classes: Counter[str] = Counter()
        roles: Counter[str] = Counter()
        pairs: Counter[str] = Counter()
        any_ai = 0
        for record_id in arm_ids:
            ai_pairs = {
                pair for pair in technology_signature(rows[record_id]) if pair[0] in AI_CLASSES
            }
            any_ai += bool(ai_pairs)
            classes.update({pair[0] for pair in ai_pairs})
            roles.update({pair[1] for pair in ai_pairs})
            pairs.update({f"{pair[0]} | {pair[1]}" for pair in ai_pairs})
        output[arm] = {
            "records": len(arm_ids),
            "records_with_any_explicit_positive_ai_class_role": any_ai,
            "class_presence_records": dict(sorted(classes.items())),
            "role_presence_records": dict(sorted(roles.items())),
            "unique_class_role_pair_presence_records": dict(sorted(pairs.items())),
        }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--reviewer", type=Path, required=True)
    parser.add_argument("--armmanifest", type=Path)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("BLIND20_COMPARISON_AGGREGATE.json"))
    args = parser.parse_args()

    source_rows = read_jsonl(args.source)
    candidate_rows = keyed(read_jsonl(args.candidate), args.candidate)
    reviewer_rows = keyed(read_jsonl(args.reviewer), args.reviewer)
    source_ids = {str(row["record_id"]) for row in source_rows}
    if len(source_rows) != 20 or len(source_ids) != 20:
        raise ValueError("source must contain exactly 20 unique records")
    if set(candidate_rows) != source_ids or set(reviewer_rows) != source_ids:
        raise ValueError("source, candidate, and reviewer must have the same exact 20 record IDs")

    state = {}
    duration = {}
    nonduration = {}
    for obj in OBJECTS:
        candidate_state = {key: findings(row)[obj]["state"] for key, row in candidate_rows.items()}
        reviewer_state = {key: findings(row)[obj]["state"] for key, row in reviewer_rows.items()}
        state[obj] = agreement(candidate_state, reviewer_state)
        state[obj]["reader_pair_counts"] = dict(sorted(Counter(
            f"{candidate_state[key]} | {reviewer_state[key]}" for key in source_ids
        ).items()))

        candidate_duration = {key: duration_signature(row, obj) for key, row in candidate_rows.items()}
        reviewer_duration = {key: duration_signature(row, obj) for key, row in reviewer_rows.items()}
        duration[obj] = agreement(candidate_duration, reviewer_duration)
        duration[obj]["candidate_records_with_numeric_duration"] = sum(bool(value) for value in candidate_duration.values())
        duration[obj]["reviewer_records_with_numeric_duration"] = sum(bool(value) for value in reviewer_duration.values())

        candidate_nonduration = {key: nonduration_count(row, obj) for key, row in candidate_rows.items()}
        reviewer_nonduration = {key: nonduration_count(row, obj) for key, row in reviewer_rows.items()}
        nonduration[obj] = agreement(candidate_nonduration, reviewer_nonduration)
        nonduration[obj]["candidate_mentions"] = sum(candidate_nonduration.values())
        nonduration[obj]["reviewer_mentions"] = sum(reviewer_nonduration.values())

    candidate_technology = {key: technology_signature(row) for key, row in candidate_rows.items()}
    reviewer_technology = {key: technology_signature(row) for key, row in reviewer_rows.items()}

    if args.armmanifest:
        arm_map = load_arm_manifest(args.armmanifest, source_ids)
        arm_result: dict[str, Any] = {
            "computed": True,
            "original_group_counts": dict(sorted(Counter(arm_map.values()).items())),
            "candidate": arm_presence(candidate_rows, arm_map),
            "reviewer": arm_presence(reviewer_rows, arm_map),
            "interpretation": "Presence counts use per-record unique explicit-positive applicant-context AI class/role pairs; categories may overlap.",
        }
    else:
        arm_result = {
            "computed": False,
            "reason": "No private arm manifest was supplied; original A10/B10 group presence was not computed.",
        }

    result = {
        "version": "blind20_comparison_aggregate_v1.1.0",
        "status": "bounded_L4_development_comparison_not_truth_accuracy",
        "coverage": {
            "source_records": len(source_rows),
            "candidate_records": len(candidate_rows),
            "reviewer_records": len(reviewer_rows),
            "exact_same_record_set": True,
            "first_pass_structurally_valid_records": {"candidate": 4, "reviewer": 18},
            "final_structurally_valid_records": {"candidate": 20, "reviewer": 20},
            "structural_counts_provenance": "Previously completed frozen v1.1 expansion receipts; this script does not rerun QA.",
        },
        "agreements": {
            "experience_state_by_object": state,
            "numeric_duration_signature_by_object": duration,
            "numeric_duration_signature_definition": [
                "object", "mode", "strength", "scope", "unit", "interpretation", "value", "bounds", "branch_relation"
            ],
            "numeric_duration_signature_note": "Only duration-bearing mentions with at least one numeric value/bound are compared. Local branch IDs are excluded.",
            "technology_unique_class_role_set": agreement(candidate_technology, reviewer_technology),
            "technology_signature_note": "Per-record sets deduplicate identical explicit-positive applicant-context class/role mentions.",
        },
        "nonduration_mention_granularity": {
            "comparison": nonduration,
            "definition": "Per-object counts of mentions without a duration, kept separate from numeric-duration agreement.",
        },
        "original_A10_B10_ai_presence": arm_result,
        "closeout": {
            "root_full_text_verdicts_already_completed": 6,
            "root_verdicts_applied_to_reader_labels": False,
            "D27_decision": "not_accepted_for_unattended_semantic_production",
            "new_diff_queue_created": False,
            "new_semantic_review_or_label_change": False,
        },
        "inputs": {
            "source_sha256": sha256(args.source),
            "candidate_sha256": sha256(args.candidate),
            "reviewer_sha256": sha256(args.reviewer),
            "armmanifest_sha256": sha256(args.armmanifest) if args.armmanifest else None,
        },
        "privacy": "Aggregate only: no record IDs, source text, evidence text, locators, or row-level arm assignments.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
