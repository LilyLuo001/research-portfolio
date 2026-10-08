#!/usr/bin/env python3
"""Integrate Batch 002 primary labels and the independent audit without relabeling."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
STAGE = ROOT.parent
PRIVATE = ROOT / "private" / "batch002"
PRODUCTION = STAGE / "production_standard_20261008"
sys.path.insert(0, str(PRODUCTION))
import export_candidates as exporter  # noqa: E402


OBJECTS = ("general_work", "occupation_task", "industry_domain")
CONDITIONAL_SCOPES = {"education_substitution", "other_conditional"}
LITERAL_UNICODE = re.compile(r"\\u([0-9a-fA-F]{4})")


class IntegrationFailure(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def sha_text(value: str) -> str:
    return sha_bytes(value.encode("utf-8"))


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrationFailure(f"unreadable JSON: {path}") from exc


def read_jsonl_lines(path: Path) -> list[tuple[dict[str, Any], str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise IntegrationFailure(f"unreadable JSONL: {path}") from exc
    rows: list[tuple[dict[str, Any], str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            raise IntegrationFailure(f"blank JSONL line {number}: {path}")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise IntegrationFailure(f"invalid JSONL line {number}: {path}") from exc
        if not isinstance(value, dict):
            raise IntegrationFailure(f"non-object JSONL line {number}: {path}")
        rows.append((value, line))
    return rows


def atomic_write(path: Path, text: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def jsonl_text_from_lines(lines: list[str]) -> str:
    return "".join(line + "\n" for line in lines)


def parsed_differences(left: Any, right: Any, path: str = "$") -> list[tuple[str, Any, Any]]:
    if type(left) is not type(right):
        return [(path, left, right)]
    if isinstance(left, dict):
        if left.keys() != right.keys():
            return [(path, left, right)]
        result: list[tuple[str, Any, Any]] = []
        for key in left:
            result.extend(parsed_differences(left[key], right[key], f"{path}.{key}"))
        return result
    if isinstance(left, list):
        if len(left) != len(right):
            return [(path, left, right)]
        result = []
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            result.extend(parsed_differences(left_item, right_item, f"{path}[{index}]"))
        return result
    return [] if left == right else [(path, left, right)]


def unicode_escape_canonical(value: str) -> str:
    """Decode only literal JSON-style Unicode escapes; do not normalize HTML or content."""
    return LITERAL_UNICODE.sub(lambda match: chr(int(match.group(1), 16)), value)


def encoding_equivalent(left: str, right: str) -> bool:
    return unicode_escape_canonical(left) == unicode_escape_canonical(right)


def find_difference_log(directory: Path) -> Path | None:
    candidates = sorted(directory.glob("PREDICTIONS_NORMAL*DIFF*PRIVATE.json"))
    if len(candidates) > 1:
        raise IntegrationFailure(f"multiple normalization difference logs in {directory}")
    return candidates[0] if candidates else None


def logged_differences(path: Path) -> set[tuple[int, str, str, str]]:
    value = read_json(path)
    entries = value.get("differences", value.get("changes")) if isinstance(value, dict) else None
    if not isinstance(entries, list):
        raise IntegrationFailure(f"normalization log has no difference array: {path}")
    result: set[tuple[int, str, str, str]] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise IntegrationFailure(f"non-object normalization log entry: {path}")
        old = entry.get("raw_quote", entry.get("original"))
        new = entry.get("normalized_quote", entry.get("normalized"))
        line = entry.get("line")
        json_path = entry.get("json_path")
        if not isinstance(line, int) or not isinstance(json_path, str) or not isinstance(old, str) or not isinstance(new, str):
            raise IntegrationFailure(f"incomplete normalization log entry: {path}")
        result.add((line, json_path, old, new))
    if len(result) != len(entries):
        raise IntegrationFailure(f"duplicate normalization log entry: {path}")
    return result


def assess_normalized(first_path: Path, normalized_path: Path, log_path: Path | None) -> dict[str, Any]:
    first = read_jsonl_lines(first_path)
    normalized = read_jsonl_lines(normalized_path)
    if len(first) != len(normalized):
        raise IntegrationFailure(f"normalization row-count mismatch: {normalized_path}")
    actual: set[tuple[int, str, str, str]] = set()
    disallowed_paths: list[dict[str, Any]] = []
    nonencoding: list[dict[str, Any]] = []
    for line, ((left, _), (right, _)) in enumerate(zip(first, normalized), 1):
        for path, old, new in parsed_differences(left, right):
            actual.add((line, path, old, new))
            leaf = path.rsplit(".", 1)[-1]
            if leaf not in {"quote", "state_quote"} or not isinstance(old, str) or not isinstance(new, str):
                disallowed_paths.append({"line": line, "json_path": path})
            elif not encoding_equivalent(old, new):
                nonencoding.append({"line": line, "json_path": path, "original": old, "normalized": new})
    if log_path is None:
        logged: set[tuple[int, str, str, str]] = set()
        log_exact = not actual
    else:
        logged = logged_differences(log_path)
        log_exact = logged == actual
    accepted = bool(actual) and not disallowed_paths and not nonencoding and log_exact
    return {
        "accepted": accepted,
        "first_sha256": sha_file(first_path),
        "normalized_sha256": sha_file(normalized_path),
        "difference_log": log_path.name if log_path else None,
        "difference_log_sha256": sha_file(log_path) if log_path else None,
        "difference_count": len(actual),
        "log_exact": log_exact,
        "disallowed_path_differences": disallowed_paths,
        "non_encoding_equivalent_differences": nonencoding,
        "rejection_reason": None if accepted else (
            "non_encoding_quote_replacement" if nonencoding else
            "difference_log_mismatch" if not log_exact else
            "non_quote_or_non_string_difference" if disallowed_paths else
            "no_logged_encoding_difference"
        ),
    }


def source_rows_from_blocks(directory: Path, expected_rows: int) -> list[dict[str, Any]]:
    block_paths = sorted((directory / "blocks").glob("block_*_PRIVATE.jsonl"))
    if len(block_paths) != 4:
        raise IntegrationFailure(f"expected four source blocks: {directory}")
    rows = [row for path in block_paths for row, _ in read_jsonl_lines(path)]
    if len(rows) != expected_rows:
        raise IntegrationFailure(f"source row count differs from {expected_rows}: {directory}")
    return rows


def verify_order_and_hashes(directory: Path, sources: list[dict[str, Any]]) -> None:
    order = read_json(directory / "ORDER_PRIVATE.json")
    ids = [str(row.get("record_id")) for row in sources]
    if order != ids or len(set(ids)) != len(ids):
        raise IntegrationFailure(f"source/order mismatch: {directory}")
    hash_path = directory / "ORDER_SOURCE_HASHES_PRIVATE.json"
    if hash_path.exists():
        hashes = [sha_text(row["original_text"]) for row in sources]
        if read_json(hash_path) != hashes:
            raise IntegrationFailure(f"source/hash-sidecar mismatch: {directory}")


def select_predictions(directory: Path, sources: list[dict[str, Any]]) -> tuple[list[str], dict[str, Any]]:
    first_path = directory / "PREDICTIONS_FIRST_RAW_PRIVATE.jsonl"
    first = read_jsonl_lines(first_path)
    if len(first) != len(sources):
        raise IntegrationFailure(f"first-output count mismatch: {directory}")
    normalized_path = directory / "PREDICTIONS_NORMALIZED_PRIVATE.jsonl"
    provenance: dict[str, Any] = {
        "first_file": first_path.name,
        "first_sha256": sha_file(first_path),
        "selected_file": first_path.name,
        "selected_sha256": sha_file(first_path),
        "normalization": {"present": False, "accepted": False},
    }
    selected = first
    if normalized_path.exists():
        assessment = assess_normalized(first_path, normalized_path, find_difference_log(directory))
        provenance["normalization"] = {"present": True, **assessment}
        if assessment["accepted"]:
            selected = read_jsonl_lines(normalized_path)
            provenance["selected_file"] = normalized_path.name
            provenance["selected_sha256"] = sha_file(normalized_path)
    return [line for _, line in selected], provenance


def exact_quote_issues(sources: list[dict[str, Any]], prediction_lines: list[str]) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    for position, (source, line) in enumerate(zip(sources, prediction_lines), 1):
        prediction = json.loads(line)
        for finding_index, finding in enumerate(prediction.get("findings", [])):
            state_quote = finding.get("state_quote")
            if isinstance(state_quote, str) and state_quote not in source["original_text"]:
                issues.append({
                    "source_position_1based": position,
                    "record_id": str(source["record_id"]),
                    "json_path": f"$.findings[{finding_index}].state_quote",
                    "error": "state_quote_not_exact_substring",
                })
            for mention_index, mention in enumerate(finding.get("mentions", [])):
                quote = mention.get("quote")
                if isinstance(quote, str) and quote not in source["original_text"]:
                    issues.append({
                        "source_position_1based": position,
                        "record_id": str(source["record_id"]),
                        "json_path": f"$.findings[{finding_index}].mentions[{mention_index}].quote",
                        "error": "quote_not_exact_substring",
                    })
    return issues


def export_selected(
    sources: list[dict[str, Any]],
    prediction_lines: list[str],
    order_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    wrappers = exporter.adapt_reader_outputs(sources, _temporary_prediction_path(prediction_lines), order_path)
    exports = exporter.export_rows(sources, wrappers)
    return wrappers, exports


def _temporary_prediction_path(lines: list[str]) -> Path:
    path = PRIVATE / ".process_batch002_predictions.tmp"
    path.write_text(jsonl_text_from_lines(lines), encoding="utf-8")
    return path


def object_by_name(row: dict[str, Any], name: str) -> dict[str, Any]:
    return next(item for item in row["objects"] if item["object"] == name)


def quote_or_state_errors(obj: dict[str, Any]) -> list[str]:
    return [
        error for error in obj.get("errors", [])
        if error.startswith(("quote:", "state_quote:", "state_shape:"))
    ]


def risk_summary(
    sources: list[dict[str, Any]], prediction_lines: list[str], exports: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    numeric_by_object = Counter()
    conditional_by_object = Counter()
    details: list[dict[str, Any]] = []
    for position, (source, prediction_line, exported) in enumerate(zip(sources, prediction_lines, exports), 1):
        prediction = json.loads(prediction_line)
        findings = {item["object"]: item for item in prediction["findings"]}
        row_reasons: list[str] = []
        for name in OBJECTS:
            raw_finding = findings[name]
            conditional_count = sum(
                mention["qualification_scope"] in CONDITIONAL_SCOPES
                for mention in raw_finding["mentions"]
            )
            if conditional_count:
                conditional_by_object[name] += conditional_count
                row_reasons.append(f"conditional_scope:{name}:{conditional_count}")
            obj = object_by_name(exported, name)
            numeric_errors = sum(
                assessment["status"] == "error" for assessment in obj["duration_assessments"]
            )
            if numeric_errors:
                numeric_by_object[name] += numeric_errors
                row_reasons.append(f"numeric_duration_error:{name}:{numeric_errors}")
            if obj["outcome_status"] == "error":
                row_reasons.append(f"export_error:{name}")
            if quote_or_state_errors(obj):
                row_reasons.append(f"quote_or_state_error:{name}")
        if row_reasons:
            details.append({
                "source_position_1based": position,
                "record_id": str(source["record_id"]),
                "reasons": sorted(set(row_reasons)),
            })
    return {
        "numeric_duration_errors_by_object": {name: numeric_by_object[name] for name in OBJECTS},
        "conditional_mentions_by_object": {name: conditional_by_object[name] for name in OBJECTS},
        "rows_with_any_indicator": len(details),
    }, details


def compare_audit(
    primary_sources: list[dict[str, Any]],
    primary_exports: list[dict[str, Any]],
    audit_sources: list[dict[str, Any]],
    audit_exports: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    primary_by_id = {str(row["record_id"]): row for row in primary_exports}
    source_position = {str(row["record_id"]): index for index, row in enumerate(primary_sources, 1)}
    source_text = {str(row["record_id"]): row["original_text"] for row in primary_sources}
    raw_inequality_counts = Counter()
    resolved_denominators = Counter()
    resolved_matches = Counter()
    resolved_mismatches = Counter()
    joint_null_counts = Counter()
    one_sided_unresolved_counts = Counter()
    state_mismatch_counts = Counter()
    quote_error_counts = Counter()
    comparisons: list[dict[str, Any]] = []
    for audit_source, audit_row in zip(audit_sources, audit_exports):
        record_id = str(audit_source["record_id"])
        if record_id not in primary_by_id or source_text[record_id] != audit_source["original_text"]:
            raise IntegrationFailure("audit source does not bind exactly to primary source")
        primary_row = primary_by_id[record_id]
        objects: list[dict[str, Any]] = []
        for name in OBJECTS:
            left = object_by_name(primary_row, name)
            right = object_by_name(audit_row, name)
            main_match = left["main_prior_required_unconditional"] == right["main_prior_required_unconditional"]
            state_match = left["model_state"] == right["model_state"]
            left_quote_errors = quote_or_state_errors(left)
            right_quote_errors = quote_or_state_errors(right)
            left_resolved = left["main_prior_required_unconditional"] is not None
            right_resolved = right["main_prior_required_unconditional"] is not None
            if not main_match:
                raw_inequality_counts[name] += 1
            if left_resolved and right_resolved:
                resolved_denominators[name] += 1
                if main_match:
                    resolved_matches[name] += 1
                else:
                    resolved_mismatches[name] += 1
            elif not left_resolved and not right_resolved:
                joint_null_counts[name] += 1
            else:
                one_sided_unresolved_counts[name] += 1
            if not state_match:
                state_mismatch_counts[name] += 1
            quote_error_counts[name] += int(bool(left_quote_errors or right_quote_errors))
            objects.append({
                "object": name,
                "primary_main": left["main_prior_required_unconditional"],
                "audit_main": right["main_prior_required_unconditional"],
                "main_match": main_match,
                "primary_state": left["model_state"],
                "audit_state": right["model_state"],
                "state_match": state_match,
                "primary_quote_or_state_errors": left_quote_errors,
                "audit_quote_or_state_errors": right_quote_errors,
            })
        comparisons.append({
            "source_position_1based": source_position[record_id],
            "record_id": record_id,
            "objects": objects,
        })
    jointly_resolved_rows = [
        row for row in comparisons
        if all(
            obj["primary_main"] is not None and obj["audit_main"] is not None
            for obj in row["objects"]
        )
    ]
    jointly_resolved_full_match_rows = sum(
        all(obj["main_match"] for obj in row["objects"])
        for row in jointly_resolved_rows
    )
    aggregate = {
        "audit_rows": len(audit_sources),
        "raw_main_inequality_counts_by_object": {name: raw_inequality_counts[name] for name in OBJECTS},
        "state_mismatch_counts_by_object": {name: state_mismatch_counts[name] for name in OBJECTS},
        "rows_with_quote_or_state_errors_by_object": {name: quote_error_counts[name] for name in OBJECTS},
        "raw_main_equality_rows_including_null_equality": sum(
            all(obj["main_match"] for obj in row["objects"])
            for row in comparisons
        ),
        "main_agreement_resolved_only": {
            "definition": "Agreement uses only pairs where both primary and audit main values are resolved as 0 or 1. Joint-null and one-sided unresolved pairs are reported separately.",
            "by_object": {
                name: {
                    "resolved_denominator": resolved_denominators[name],
                    "resolved_matches": resolved_matches[name],
                    "resolved_mismatches": resolved_mismatches[name],
                    "joint_null": joint_null_counts[name],
                    "one_sided_unresolved": one_sided_unresolved_counts[name],
                    "agreement": (
                        resolved_matches[name] / resolved_denominators[name]
                        if resolved_denominators[name] else None
                    ),
                }
                for name in OBJECTS
            },
            "all_three_objects": {
                "resolved_denominator_rows": len(jointly_resolved_rows),
                "resolved_full_match_rows": jointly_resolved_full_match_rows,
                "rows_with_any_joint_null": sum(
                    any(obj["primary_main"] is None and obj["audit_main"] is None for obj in row["objects"])
                    for row in comparisons
                ),
                "rows_with_any_one_sided_unresolved": sum(
                    any((obj["primary_main"] is None) != (obj["audit_main"] is None) for obj in row["objects"])
                    for row in comparisons
                ),
                "agreement": (
                    jointly_resolved_full_match_rows / len(jointly_resolved_rows)
                    if jointly_resolved_rows else None
                ),
            },
        },
        "unknown_is_null_not_zero": True,
    }
    return aggregate, comparisons


def targeted_candidates(
    primary_details: list[dict[str, Any]],
    audit_comparisons: list[dict[str, Any]],
    rejected_normalizations: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    reasons_by_position: dict[int, set[str]] = {}
    ids_by_position: dict[int, str] = {}
    priority_by_position: dict[int, int] = {}

    def add(position: int, record_id: str, reason: str, priority: int) -> None:
        reasons_by_position.setdefault(position, set()).add(reason)
        ids_by_position[position] = record_id
        priority_by_position[position] = max(priority_by_position.get(position, 0), priority)

    for item in primary_details:
        for reason in item["reasons"]:
            priority = 100 if "quote_or_state_error" in reason or "export_error" in reason else 30
            add(item["source_position_1based"], item["record_id"], reason, priority)
    for row in audit_comparisons:
        for obj in row["objects"]:
            if not obj["main_match"]:
                add(row["source_position_1based"], row["record_id"], f"audit_main_mismatch:{obj['object']}", 90)
            if obj["primary_quote_or_state_errors"] or obj["audit_quote_or_state_errors"]:
                add(row["source_position_1based"], row["record_id"], f"audit_quote_or_state_error:{obj['object']}", 95)
    for item in rejected_normalizations:
        for difference in item.get("non_encoding_equivalent_differences", []):
            local_line = difference["line"]
            global_position = item["group_start_position_1based"] + local_line - 1
            add(global_position, item["record_ids"][local_line - 1], "rejected_nonencoding_normalization", 110)
    ranked = sorted(reasons_by_position, key=lambda pos: (-priority_by_position[pos], pos))[:8]
    return [
        {
            "source_position_1based": position,
            "record_id": ids_by_position[position],
            "priority": priority_by_position[position],
            "reasons": sorted(reasons_by_position[position]),
        }
        for position in ranked
    ]


def main() -> int:
    started = utc_now()
    combined_path = PRIVATE / "COMBINED_SOURCE_PRIVATE.jsonl"
    combined_pairs = read_jsonl_lines(combined_path)
    combined_sources = [row for row, _ in combined_pairs]
    if len(combined_sources) != 128:
        raise IntegrationFailure("combined source does not contain 128 rows")
    combined_hashes = [sha_text(row["original_text"]) for row in combined_sources]
    if combined_hashes != sorted(combined_hashes) or len(set(combined_hashes)) != 128:
        raise IntegrationFailure("combined source is not unique ascending exact-text SHA order")
    staging_receipt = read_json(ROOT / "BATCH002_EXECUTION_RECEIPT.json")
    expected_combined_sha = staging_receipt["private_artifact_sha256"][combined_path.name]
    if sha_file(combined_path) != expected_combined_sha:
        raise IntegrationFailure("combined source hash differs from staging receipt")

    merged_lines: list[str] = []
    group_provenance: list[dict[str, Any]] = []
    concatenated_ids: list[str] = []
    rejected_normalizations: list[dict[str, Any]] = []
    for group_number in range(1, 5):
        directory = PRIVATE / f"group_{group_number:02d}"
        sources = source_rows_from_blocks(directory, 32)
        verify_order_and_hashes(directory, sources)
        lines, provenance = select_predictions(directory, sources)
        start_position = len(merged_lines) + 1
        merged_lines.extend(lines)
        concatenated_ids.extend(str(row["record_id"]) for row in sources)
        provenance.update({
            "group": group_number,
            "group_start_position_1based": start_position,
            "source_count": len(sources),
            "source_character_count": sum(len(row["original_text"]) for row in sources),
            "source_block_sha256": [sha_file(path) for path in sorted((directory / "blocks").glob("block_*_PRIVATE.jsonl"))],
            "order_sha256": sha_file(directory / "ORDER_PRIVATE.json"),
        })
        if provenance["normalization"].get("present") and not provenance["normalization"].get("accepted"):
            rejected_normalizations.append({
                "group": group_number,
                "group_start_position_1based": start_position,
                "record_ids": [str(row["record_id"]) for row in sources],
                **provenance["normalization"],
            })
        group_provenance.append(provenance)
    combined_ids = [str(row["record_id"]) for row in combined_sources]
    if concatenated_ids != combined_ids or len(merged_lines) != 128:
        raise IntegrationFailure("group concatenation differs from combined source order")

    order_path = PRIVATE / "PRIMARY_ORDER_PRIVATE.json"
    predictions_path = PRIVATE / "PRIMARY_PREDICTIONS_SELECTED_PRIVATE.jsonl"
    wrapped_path = PRIVATE / "PRIMARY_WRAPPED_RAW_OUTPUTS_PRIVATE.jsonl"
    candidates_path = PRIVATE / "PRIMARY_CANDIDATES_PRIVATE.jsonl"
    atomic_write(order_path, json_text(combined_ids), 0o600)
    selected_text = jsonl_text_from_lines(merged_lines)
    atomic_write(predictions_path, selected_text, 0o600)
    temporary = _temporary_prediction_path(merged_lines)
    wrappers = exporter.adapt_reader_outputs(combined_sources, temporary, order_path)
    exports = exporter.export_rows(combined_sources, wrappers)
    temporary.unlink(missing_ok=True)
    wrapped_text = exporter.serialize_jsonl(wrappers)
    candidate_text = exporter.serialize_jsonl(exports)
    atomic_write(wrapped_path, wrapped_text, 0o600)
    atomic_write(candidates_path, candidate_text, 0o600)
    adapter_receipt = exporter.build_public_receipt(
        exports, sha_file(combined_path), sha_bytes(selected_text.encode("utf-8"))
    )
    quote_issues = exact_quote_issues(combined_sources, merged_lines)
    risk_counts, primary_details = risk_summary(combined_sources, merged_lines, exports)

    audit_status = "pending_predictions"
    audit_aggregate: dict[str, Any] | None = None
    audit_comparisons: list[dict[str, Any]] = []
    audit_directory = PRIVATE / "audit"
    audit_first = audit_directory / "PREDICTIONS_FIRST_RAW_PRIVATE.jsonl"
    if audit_first.exists():
        audit_sources = [row for row, _ in read_jsonl_lines(audit_directory / "SOURCE16_PRIVATE.jsonl")]
        if len(audit_sources) != 16:
            raise IntegrationFailure("audit source does not contain 16 rows")
        verify_order_and_hashes(audit_directory, audit_sources)
        audit_lines, audit_provenance = select_predictions(audit_directory, audit_sources)
        audit_order_path = PRIVATE / "AUDIT_ORDER_PRIVATE.json"
        atomic_write(audit_order_path, json_text([str(row["record_id"]) for row in audit_sources]), 0o600)
        audit_predictions_path = PRIVATE / "AUDIT_PREDICTIONS_SELECTED_PRIVATE.jsonl"
        audit_selected_text = jsonl_text_from_lines(audit_lines)
        atomic_write(audit_predictions_path, audit_selected_text, 0o600)
        temporary = _temporary_prediction_path(audit_lines)
        audit_wrappers = exporter.adapt_reader_outputs(audit_sources, temporary, audit_order_path)
        audit_exports = exporter.export_rows(audit_sources, audit_wrappers)
        temporary.unlink(missing_ok=True)
        atomic_write(PRIVATE / "AUDIT_WRAPPED_RAW_OUTPUTS_PRIVATE.jsonl", exporter.serialize_jsonl(audit_wrappers), 0o600)
        atomic_write(PRIVATE / "AUDIT_CANDIDATES_PRIVATE.jsonl", exporter.serialize_jsonl(audit_exports), 0o600)
        audit_aggregate, audit_comparisons = compare_audit(
            combined_sources, exports, audit_sources, audit_exports
        )
        audit_aggregate["adapter"] = exporter.build_public_receipt(
            audit_exports,
            sha_file(audit_directory / "SOURCE16_PRIVATE.jsonl"),
            sha_bytes(audit_selected_text.encode("utf-8")),
        )
        atomic_write(PRIVATE / "AUDIT_COMPARISON_PRIVATE.json", json_text({
            "aggregate": audit_aggregate,
            "rows": audit_comparisons,
            "provenance": audit_provenance,
        }), 0o600)
        audit_status = "integrated"

    flags = targeted_candidates(primary_details, audit_comparisons, rejected_normalizations)
    if len(flags) > 8:
        raise IntegrationFailure("targeted candidate list exceeds eight")
    issue_summary = {
        "source_count": len(combined_sources),
        "exact_quote_issues": quote_issues,
        "risk_counts": risk_counts,
        "indicator_rows": primary_details,
        "audit_status": audit_status,
        "audit_main_mismatches": [
            {
                "source_position_1based": row["source_position_1based"],
                "record_id": row["record_id"],
                "objects": [obj for obj in row["objects"] if not obj["main_match"]],
            }
            for row in audit_comparisons if any(not obj["main_match"] for obj in row["objects"])
        ],
    }
    atomic_write(PRIVATE / "PRIMARY_ISSUE_SUMMARY_PRIVATE.json", json_text(issue_summary), 0o600)
    atomic_write(PRIVATE / "TARGETED_REVIEW_CANDIDATES_PRIVATE.json", json_text({
        "status": "candidate_selection_only_no_additional_ai_review_performed",
        "maximum_candidates": 8,
        "selected_count": len(flags),
        "candidates": flags,
    }), 0o600)

    provenance = {
        "processing_order": "ascending exact-text SHA among not-yet-completed texts, first 128; not original randomized queue order",
        "combined_source_sha256": sha_file(combined_path),
        "primary_order_sha256": sha_file(order_path),
        "selected_predictions_sha256": sha_file(predictions_path),
        "wrapped_raw_outputs_sha256": sha_file(wrapped_path),
        "primary_candidates_sha256": sha_file(candidates_path),
        "groups": group_provenance,
        "rejected_normalization_count": len(rejected_normalizations),
        "rejected_normalizations": rejected_normalizations,
        "immutable_first_files_modified": False,
    }
    atomic_write(PRIVATE / "PRIMARY_PROVENANCE_PRIVATE.json", json_text(provenance), 0o600)

    public_aggregate = {
        **adapter_receipt,
        "schema_version": "batch002_primary_aggregate_v1",
        "processing_order": "ascending exact-text SHA among not-yet-completed texts, first 128; not original randomized queue order",
        "strict_main_interpretation": "1 means an explicit prior-experience, required, unconditional clause. A 0 means that strict clause was not encoded; it does not mean the job requires no experience. Conditional degree/year paths remain preserved outside the strict main indicator.",
        "risk_indicators": risk_counts,
        "normalization": {
            "groups_with_normalized_copy": sum(item["normalization"].get("present", False) for item in group_provenance),
            "accepted_encoding_only_normalized_copies": sum(item["normalization"].get("accepted", False) for item in group_provenance),
            "rejected_normalized_copies": len(rejected_normalizations),
            "rejection_rule": "Quote/state_quote path restriction is necessary but not sufficient; only exact logged, reversible Unicode-escape encoding changes are accepted. HTML and semantic content are not normalized.",
        },
        "audit_status": audit_status,
        "independent_audit16": audit_aggregate,
        "targeted_review_candidate_count": len(flags),
        "accuracy_claim": False,
        "population_or_causal_claim": False,
    }
    aggregate_path = ROOT / "PRIMARY_AGGREGATE.json"
    atomic_write(aggregate_path, json_text(public_aggregate), 0o644)

    ended = utc_now()
    group_receipts = [read_json(PRIVATE / f"group_{number:02d}" / "RUN_RECEIPT_PRIVATE.json") for number in range(1, 5)]
    audit_run_receipt = (
        read_json(audit_directory / "RUN_RECEIPT_PRIVATE.json")
        if audit_status == "integrated" and (audit_directory / "RUN_RECEIPT_PRIVATE.json").exists()
        else None
    )
    run_receipt = {
        "schema_version": "batch002_public_run_receipt_v1",
        "integration_start_utc": started,
        "integration_end_utc": ended,
        "primary_inference_start_utc": min(item["actual_start_utc"] for item in group_receipts),
        "primary_inference_end_utc": max(item["actual_end_utc"] for item in group_receipts),
        "audit_inference_start_utc": audit_run_receipt.get("run_start_utc") if audit_run_receipt else None,
        "audit_inference_end_utc": audit_run_receipt.get("run_end_utc") if audit_run_receipt else None,
        "source_count": len(combined_sources),
        "source_characters": sum(len(row["original_text"]) for row in combined_sources),
        "first_output_characters": sum(item["output_characters"] for item in group_receipts),
        "selected_prediction_characters": len(selected_text),
        "candidate_export_characters": len(candidate_text),
        "characters_are_not_tokens": True,
        "exact_inference_tokens": "unavailable",
        "cost": "unavailable",
        "primary_inference_count": len(combined_sources),
        "audit_status": audit_status,
        "audit_inference_count": 16 if audit_status == "integrated" else 0,
        "audit_input_characters": (
            audit_run_receipt.get("input_character_counts", {}).get("total")
            if audit_run_receipt else None
        ),
        "audit_first_output_characters": (
            next(iter(audit_run_receipt.get("output_character_counts", {}).values()), None)
            if audit_run_receipt else None
        ),
        "git_action": False,
    }
    atomic_write(ROOT / "BATCH002_RUN_RECEIPT.json", json_text(run_receipt), 0o644)
    print(json.dumps({
        "status": "primary_integrated" if audit_status != "integrated" else "primary_and_audit_integrated",
        "primary_rows": len(exports),
        "audit_status": audit_status,
        "quote_issues": len(quote_issues),
        "targeted_candidates": len(flags),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IntegrationFailure as exc:
        print(f"integration rejected: {exc}", file=sys.stderr)
        raise SystemExit(2)
