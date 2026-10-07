#!/usr/bin/env python3
"""Apply a separate root-adjudication layer to field-level candidate exports.

This script changes only derived object status/main values and requested duration
statuses. It preserves the candidate-before state and raw model output, and it never
rewrites model labels, quotes, source text, or the immutable full queue.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from export_candidates import OBJECT_ORDER, InputFailure, serialize_jsonl, sha256_text, strict_jsonl


FINAL_SCHEMA_VERSION = "linkup_field_candidate_final_v1.0.0"
FINAL_RECEIPT_VERSION = "linkup_batch001_final_aggregate_v1.0.0"
DECISION_KEYS = {
    "record_id",
    "source_text_sha256",
    "object",
    "reason",
    "evidence_quotes",
    "main_override",
    "duration_overrides",
    "ancillary_notes",
}
MAIN_OVERRIDE_KEYS = {"value", "status"}
DURATION_OVERRIDE_KEYS = {"mention_index_0based", "status", "reason"}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_decisions(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputFailure("decisions_invalid_json", "decision file is not readable JSON") from exc
    if not isinstance(value, list):
        raise InputFailure("decisions_not_array", "decision file must contain one JSON array")
    if any(not isinstance(item, dict) for item in value):
        raise InputFailure("decision_not_object", "every decision must be a JSON object")
    return value


def exact_occurrences(text: str, quote: str) -> list[dict[str, Any]]:
    starts: list[int] = []
    position = text.find(quote)
    while position >= 0:
        starts.append(position)
        position = text.find(quote, position + 1)
    return [
        {"start": start, "end": start + len(quote), "text": quote}
        for start in starts
    ]


def validate_main_override(value: Any, position: int) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != MAIN_OVERRIDE_KEYS:
        raise InputFailure("main_override_invalid", f"decision {position} has invalid main_override shape")
    status = value["status"]
    result = value["value"]
    if status == "candidate":
        if isinstance(result, bool) or result not in (0, 1):
            raise InputFailure(
                "main_override_invalid",
                f"decision {position} candidate main override requires value 0 or 1",
            )
    elif status == "unknown":
        if result is not None:
            raise InputFailure(
                "main_override_invalid",
                f"decision {position} unknown main override requires null value",
            )
    else:
        raise InputFailure(
            "main_override_invalid",
            f"decision {position} main override status must be candidate or unknown",
        )
    return copy.deepcopy(value)


def validate_duration_overrides(value: Any, mention_count: int, position: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise InputFailure(
            "duration_overrides_invalid",
            f"decision {position} duration_overrides must be an array",
        )
    validated: list[dict[str, Any]] = []
    seen_indices: set[int] = set()
    for override in value:
        if not isinstance(override, dict) or set(override) != DURATION_OVERRIDE_KEYS:
            raise InputFailure(
                "duration_override_invalid",
                f"decision {position} has an invalid duration override shape",
            )
        index = override["mention_index_0based"]
        if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < mention_count:
            raise InputFailure(
                "duration_override_index_invalid",
                f"decision {position} duration override index is outside the object mentions",
            )
        if index in seen_indices:
            raise InputFailure(
                "duration_override_duplicate_index",
                f"decision {position} repeats a duration override index",
            )
        seen_indices.add(index)
        if override["status"] not in {"candidate", "unknown"}:
            raise InputFailure(
                "duration_override_status_invalid",
                f"decision {position} duration override status is invalid",
            )
        if not isinstance(override["reason"], str) or not override["reason"].strip():
            raise InputFailure(
                "duration_override_reason_missing",
                f"decision {position} duration override requires a reason",
            )
        validated.append(copy.deepcopy(override))
    return validated


def validate_candidates_and_sources(
    sources: list[dict[str, Any]], candidates: list[dict[str, Any]], expected_rows: int
) -> dict[str, tuple[str, dict[str, Any]]]:
    if len(sources) != expected_rows or len(candidates) != expected_rows:
        raise InputFailure(
            "finalize_row_count_mismatch",
            f"source and candidate inputs must each contain exactly {expected_rows} rows",
        )
    source_index: dict[str, tuple[str, dict[str, Any]]] = {}
    seen_candidate_ids: set[str] = set()
    for offset in range(expected_rows):
        position = offset + 1
        source = sources[offset]
        candidate = candidates[offset]
        source_id = source.get("record_id")
        candidate_id = candidate.get("record_id")
        if not isinstance(source_id, (str, int)) or isinstance(source_id, bool):
            raise InputFailure("source_record_id_invalid", f"source row {position} has invalid record_id")
        source_id = str(source_id)
        if candidate_id != source_id:
            raise InputFailure("candidate_order_mismatch", f"candidate row {position} does not match source order")
        if source_id in source_index or source_id in seen_candidate_ids:
            raise InputFailure("duplicate_record_id", f"duplicate record_id at row {position}")
        seen_candidate_ids.add(source_id)
        text = source.get("original_text")
        if not isinstance(text, str):
            raise InputFailure("source_text_missing", f"source row {position} lacks original_text")
        source_sha = sha256_text(text)
        if candidate.get("source_text_sha256") != source_sha:
            raise InputFailure("candidate_source_hash_mismatch", f"candidate row {position} has wrong source hash")
        if candidate.get("processing_position_1based") != position:
            raise InputFailure("candidate_position_mismatch", f"candidate row {position} has wrong position")
        raw_output = candidate.get("raw_output")
        if not isinstance(raw_output, str) or candidate.get("raw_output_sha256") != sha256_text(raw_output):
            raise InputFailure("candidate_raw_output_mismatch", f"candidate row {position} raw output is not intact")
        objects = candidate.get("objects")
        if not isinstance(objects, list) or len(objects) != len(OBJECT_ORDER):
            raise InputFailure("candidate_objects_invalid", f"candidate row {position} must contain three objects")
        object_names = [item.get("object") if isinstance(item, dict) else None for item in objects]
        if len(set(object_names)) != len(OBJECT_ORDER) or set(object_names) != set(OBJECT_ORDER):
            raise InputFailure(
                "candidate_duplicate_or_missing_object",
                f"candidate row {position} has duplicate, missing, or unknown objects",
            )
        for item in objects:
            if item.get("outcome_status") not in {"candidate", "unknown", "error"}:
                raise InputFailure("candidate_status_invalid", f"candidate row {position} has invalid status")
            binary = item.get("main_prior_required_unconditional")
            if isinstance(binary, bool) or binary not in (0, 1, None):
                raise InputFailure("candidate_main_invalid", f"candidate row {position} has invalid main value")
            assessments = item.get("duration_assessments")
            if not isinstance(assessments, list):
                raise InputFailure("candidate_durations_invalid", f"candidate row {position} lacks durations")
            indices = [entry.get("mention_index_0based") if isinstance(entry, dict) else None for entry in assessments]
            if indices != list(range(len(assessments))):
                raise InputFailure(
                    "candidate_duration_indices_invalid",
                    f"candidate row {position} duration indices are not contiguous",
                )
            if any(entry.get("status") not in {"candidate", "unknown", "error"} for entry in assessments):
                raise InputFailure(
                    "candidate_duration_status_invalid",
                    f"candidate row {position} has invalid duration status",
                )
        source_index[source_id] = (text, source)
    return source_index


def validate_decisions(
    decisions: list[dict[str, Any]],
    source_index: dict[str, tuple[str, dict[str, Any]]],
    candidates_by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    validated: list[dict[str, Any]] = []
    seen_targets: set[tuple[str, str]] = set()
    for position, decision in enumerate(decisions, 1):
        if set(decision) != DECISION_KEYS:
            raise InputFailure("decision_shape_invalid", f"decision {position} has missing or additional fields")
        record_id = decision["record_id"]
        if not isinstance(record_id, (str, int)) or isinstance(record_id, bool):
            raise InputFailure("decision_record_id_invalid", f"decision {position} has invalid record_id")
        record_id = str(record_id)
        if record_id not in source_index:
            raise InputFailure("decision_record_unknown", f"decision {position} refers to an unknown record")
        object_name = decision["object"]
        if object_name not in OBJECT_ORDER:
            raise InputFailure("decision_object_invalid", f"decision {position} has invalid object")
        target = (record_id, object_name)
        if target in seen_targets:
            raise InputFailure("decision_duplicate_object", f"decision {position} duplicates a record/object")
        seen_targets.add(target)
        text, _ = source_index[record_id]
        source_sha = sha256_text(text)
        if decision["source_text_sha256"] != source_sha:
            raise InputFailure("decision_hash_mismatch", f"decision {position} has wrong source hash")
        reason = decision["reason"]
        if not isinstance(reason, str) or not reason.strip():
            raise InputFailure("decision_reason_missing", f"decision {position} requires a reason")
        ancillary = decision["ancillary_notes"]
        if not isinstance(ancillary, list) or any(not isinstance(note, str) for note in ancillary):
            raise InputFailure("decision_ancillary_notes_invalid", f"decision {position} has invalid notes")
        evidence_quotes = decision["evidence_quotes"]
        if not isinstance(evidence_quotes, list) or not evidence_quotes or any(
            not isinstance(quote, str) or not quote for quote in evidence_quotes
        ):
            raise InputFailure("decision_evidence_invalid", f"decision {position} requires exact evidence quotes")
        evidence: list[dict[str, Any]] = []
        for quote in evidence_quotes:
            occurrences = exact_occurrences(text, quote)
            if not occurrences:
                raise InputFailure(
                    "decision_quote_not_exact",
                    f"decision {position} contains a nonexact source quote",
                )
            evidence.append({"quote": quote, "occurrences": occurrences})
        candidate_object = next(
            item for item in candidates_by_id[record_id]["objects"] if item["object"] == object_name
        )
        main_override = validate_main_override(decision["main_override"], position)
        duration_overrides = validate_duration_overrides(
            decision["duration_overrides"],
            len(candidate_object["duration_assessments"]),
            position,
        )
        validated.append({
            **copy.deepcopy(decision),
            "record_id": record_id,
            "main_override": main_override,
            "duration_overrides": duration_overrides,
            "evidence_offsets": evidence,
        })
    return validated


def row_status(objects: list[dict[str, Any]]) -> str:
    statuses = [item["outcome_status"] for item in objects]
    if all(status == "candidate" for status in statuses):
        return "candidate"
    if all(status == "error" for status in statuses):
        return "error"
    return "partial"


def finalize_rows(
    sources: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    expected_rows: int = 24,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_index = validate_candidates_and_sources(sources, candidates, expected_rows)
    candidates_by_id = {row["record_id"]: row for row in candidates}
    validated_decisions = validate_decisions(decisions, source_index, candidates_by_id)
    decisions_by_target = {
        (decision["record_id"], decision["object"]): decision
        for decision in validated_decisions
    }
    final_rows: list[dict[str, Any]] = []
    for candidate in candidates:
        final_row = copy.deepcopy(candidate)
        before = {
            "row_status": candidate["row_status"],
            "objects": copy.deepcopy(candidate["objects"]),
        }
        applied: list[dict[str, Any]] = []
        for item in final_row["objects"]:
            decision = decisions_by_target.get((candidate["record_id"], item["object"]))
            if decision is None:
                continue
            if decision["main_override"] is not None:
                item["outcome_status"] = decision["main_override"]["status"]
                item["main_prior_required_unconditional"] = decision["main_override"]["value"]
            for override in decision["duration_overrides"]:
                assessment = item["duration_assessments"][override["mention_index_0based"]]
                assessment["status"] = override["status"]
            applied.append({
                "object": decision["object"],
                "reason": decision["reason"],
                "evidence_quotes": decision["evidence_quotes"],
                "evidence_offsets": decision["evidence_offsets"],
                "main_override": decision["main_override"],
                "duration_overrides": decision["duration_overrides"],
                "ancillary_notes": decision["ancillary_notes"],
            })
        final_row["finalization_schema_version"] = FINAL_SCHEMA_VERSION
        final_row["candidate_before_adjudication"] = before
        final_row["adjudication"] = {
            "layer": "root_explicit_adjudication",
            "decisions_applied": applied,
            "external_truth_claim": False,
        }
        final_row["row_status"] = row_status(final_row["objects"])
        if final_row["raw_output"] != candidate["raw_output"] or final_row["raw_output_sha256"] != candidate["raw_output_sha256"]:
            raise RuntimeError("raw output changed during finalization")
        final_rows.append(final_row)
    return final_rows, validated_decisions


def _binary_key(value: Any) -> str:
    return "null" if value is None else str(value)


def build_receipt(
    final_rows: list[dict[str, Any]],
    validated_decisions: list[dict[str, Any]],
    source_sha: str,
    candidates_sha: str,
    decisions_sha: str,
) -> dict[str, Any]:
    object_summary: dict[str, Any] = {}
    total_changed_main = 0
    for object_name in OBJECT_ORDER:
        raw_objects = [
            next(item for item in row["candidate_before_adjudication"]["objects"] if item["object"] == object_name)
            for row in final_rows
        ]
        final_objects = [next(item for item in row["objects"] if item["object"] == object_name) for row in final_rows]
        raw_main = Counter(_binary_key(item["main_prior_required_unconditional"]) for item in raw_objects)
        final_main = Counter(_binary_key(item["main_prior_required_unconditional"]) for item in final_objects)
        raw_status = Counter(item["outcome_status"] for item in raw_objects)
        final_status = Counter(item["outcome_status"] for item in final_objects)
        changed_main = sum(
            raw_objects[index]["main_prior_required_unconditional"]
            != final_objects[index]["main_prior_required_unconditional"]
            for index in range(len(raw_objects))
        )
        total_changed_main += changed_main
        raw_duration = Counter(
            assessment["status"] for item in raw_objects for assessment in item["duration_assessments"]
        )
        final_duration = Counter(
            assessment["status"] for item in final_objects for assessment in item["duration_assessments"]
        )
        object_summary[object_name] = {
            "eligible_denominator_rows": len(final_rows),
            "raw_outcome_status_counts": {key: raw_status.get(key, 0) for key in ("candidate", "unknown", "error")},
            "final_outcome_status_counts": {key: final_status.get(key, 0) for key in ("candidate", "unknown", "error")},
            "raw_main_counts": {key: raw_main.get(key, 0) for key in ("1", "0", "null")},
            "final_main_counts": {key: final_main.get(key, 0) for key in ("1", "0", "null")},
            "changed_main_count": changed_main,
            "raw_duration_status_counts": {
                key: raw_duration.get(key, 0) for key in ("candidate", "unknown", "error")
            },
            "final_duration_status_counts": {
                key: final_duration.get(key, 0) for key in ("candidate", "unknown", "error")
            },
        }
    reason_counts = Counter(sha256_text(decision["reason"]) for decision in validated_decisions)
    duration_reason_counts = Counter(
        sha256_text(override["reason"])
        for decision in validated_decisions
        for override in decision["duration_overrides"]
    )
    return {
        "schema_version": FINAL_RECEIPT_VERSION,
        "status": "finalized_explicit_adjudication_layer",
        "eligible_rows": len(final_rows),
        "eligible_object_fields": len(final_rows) * len(OBJECT_ORDER),
        "decision_count": len(validated_decisions),
        "changed_main_count": total_changed_main,
        "decision_reason_sha256_counts": dict(sorted(reason_counts.items())),
        "duration_override_reason_sha256_counts": dict(sorted(duration_reason_counts.items())),
        "objects": object_summary,
        "source_jsonl_sha256": source_sha,
        "candidate_jsonl_sha256": candidates_sha,
        "root_decisions_json_sha256": decisions_sha,
        "final_private_jsonl_sha256": sha256_text(serialize_jsonl(final_rows)),
        "privacy": "Aggregate receipt contains no record IDs, source text, evidence quotes, raw model output, or record-level results.",
        "denominator_rule": f"All {len(final_rows)} source rows remain in each of the three object denominators; unknown and error remain null rather than being removed.",
        "root_notes": [
            "This is an explicit root adjudication layer over preserved model outputs, not an external ground-truth validation.",
            "A final candidate value remains a candidate measurement and does not establish objective truth or an economic conclusion.",
            "Analysts must use a model_duration only when its final duration status is candidate; retained error or unknown model_duration content is provenance, not an analysis value.",
            "The immutable full queue is outside this finalizer and is not modified.",
        ],
    }


def atomic_write(path: Path, content: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    parser.add_argument(
        "--expected-rows",
        type=int,
        default=24,
        help="exact logical batch size; defaults to batch001's 24 and may be set to 128 later",
    )
    args = parser.parse_args()
    if args.expected_rows <= 0:
        parser.error("--expected-rows must be positive")
    try:
        sources = strict_jsonl(args.source, "source")
        candidates = strict_jsonl(args.candidates, "candidate")
        decisions = read_decisions(args.decisions)
        final_rows, validated_decisions = finalize_rows(
            sources, candidates, decisions, expected_rows=args.expected_rows
        )
        receipt = build_receipt(
            final_rows,
            validated_decisions,
            sha256_bytes(args.source.read_bytes()),
            sha256_bytes(args.candidates.read_bytes()),
            sha256_bytes(args.decisions.read_bytes()),
        )
    except InputFailure as exc:
        print(f"input rejected: {exc.code}", file=sys.stderr)
        return 2
    atomic_write(args.output, serialize_jsonl(final_rows), 0o600)
    atomic_write(args.receipt, json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", 0o644)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
