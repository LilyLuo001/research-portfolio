#!/usr/bin/env python3
"""Export field-level candidate measurements from explicitly bound raw outputs.

The source and raw-output JSONL files must have the same number and order of rows.
Every raw-output row repeats its one-based position, record ID, and source-text SHA.
Count, order, or identity ambiguity rejects the complete run; a declared hash mismatch
quarantines its row. Validation failures are isolated to the affected measurement
object, and duration failures are isolated from otherwise valid binary indicators.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent
COMPACT_DIR = ROOT.parent / "compact_measurement_20261007"
sys.path.insert(0, str(COMPACT_DIR))
import expand_and_validate as compact  # noqa: E402


EXPORT_SCHEMA_VERSION = "linkup_field_candidate_export_v1.0.0"
PUBLIC_RECEIPT_VERSION = "linkup_field_candidate_public_receipt_v1.0.0"
OVERRIDE_RECEIPT_VERSION = "linkup_external_review_override_receipt_v1.0.0"
OBJECT_ORDER = ("general_work", "occupation_task", "industry_domain")

FINDING_SCHEMA = {
    "$schema": compact.SCHEMA["$schema"],
    "$defs": compact.SCHEMA["$defs"],
    "$ref": "#/$defs/finding",
}
DURATION_SCHEMA = {
    "$schema": compact.SCHEMA["$schema"],
    "$defs": compact.SCHEMA["$defs"],
    "$ref": "#/$defs/duration",
}
FINDING_VALIDATOR = Draft202012Validator(FINDING_SCHEMA)
DURATION_VALIDATOR = Draft202012Validator(DURATION_SCHEMA)


class InputFailure(ValueError):
    """A deterministic input or binding precondition failed."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def strict_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    """Read JSONL without dropping blank or malformed rows."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise InputFailure(f"{label}_unreadable", f"cannot read {label} JSONL") from exc
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            raise InputFailure(f"{label}_blank_line", f"{label} line {line_number} is blank")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise InputFailure(
                f"{label}_invalid_json",
                f"{label} line {line_number} is invalid JSON",
            ) from exc
        if not isinstance(row, dict):
            raise InputFailure(
                f"{label}_non_object_row",
                f"{label} line {line_number} is not a JSON object",
            )
        rows.append(row)
    return rows


def strict_jsonl_preserve_lines(path: Path, label: str) -> list[tuple[dict[str, Any], str]]:
    """Read JSONL objects and retain each decoded line without reserialization."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise InputFailure(f"{label}_unreadable", f"cannot read {label} JSONL") from exc
    parsed: list[tuple[dict[str, Any], str]] = []
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            raise InputFailure(f"{label}_blank_line", f"{label} line {line_number} is blank")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise InputFailure(
                f"{label}_invalid_json",
                f"{label} line {line_number} is invalid JSON",
            ) from exc
        if not isinstance(value, dict):
            raise InputFailure(
                f"{label}_non_object_row",
                f"{label} line {line_number} is not a JSON object",
            )
        parsed.append((value, line))
    return parsed


def read_order(path: Path) -> list[str]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise InputFailure("order_invalid", "order file is not readable JSON") from exc
    if not isinstance(value, list) or any(
        not isinstance(item, (str, int)) or isinstance(item, bool) for item in value
    ):
        raise InputFailure("order_invalid", "order file must be an array of record IDs")
    order = [str(item) for item in value]
    if len(set(order)) != len(order):
        raise InputFailure("order_duplicate_id", "order file contains duplicate record IDs")
    return order


def adapt_reader_outputs(
    sources: list[dict[str, Any]], prediction_path: Path, order_path: Path
) -> list[dict[str, Any]]:
    """Bind bare reader lines to sources through an exact external order manifest."""
    prediction_lines = strict_jsonl_preserve_lines(prediction_path, "reader_prediction")
    order = read_order(order_path)
    if len(sources) != len(order) or len(sources) != len(prediction_lines):
        raise InputFailure(
            "adapter_row_count_mismatch",
            "source, order, and reader-prediction row counts differ",
        )
    source_ids = [_record_id(row, "source", index + 1) for index, row in enumerate(sources)]
    if source_ids != order:
        raise InputFailure("adapter_order_mismatch", "source IDs do not exactly equal the order manifest")
    wrappers: list[dict[str, Any]] = []
    for offset in range(len(sources)):
        position = offset + 1
        text = sources[offset].get("original_text")
        if not isinstance(text, str):
            raise InputFailure("source_text_missing", f"source row {position} requires string original_text")
        _, raw_line = prediction_lines[offset]
        wrappers.append({
            "processing_position_1based": position,
            "record_id": source_ids[offset],
            "source_text_sha256": sha256_text(text),
            "raw_output_line_sha256": sha256_text(raw_line),
            "raw_output": raw_line,
        })
    return wrappers


def _record_id(row: dict[str, Any], label: str, position: int) -> str:
    value = row.get("record_id")
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        raise InputFailure(
            f"{label}_record_id_missing",
            f"{label} row {position} requires a string or integer record_id",
        )
    return str(value)


def bind_rows(
    sources: list[dict[str, Any]], raw_rows: list[dict[str, Any]]
) -> list[tuple[dict[str, Any], dict[str, Any], str, str, list[str]]]:
    """Fail closed unless count, position, identity, order, and hashes all agree."""
    if len(sources) != len(raw_rows):
        raise InputFailure(
            "row_count_mismatch",
            f"source/raw-output row counts differ: {len(sources)} != {len(raw_rows)}",
        )
    seen_source_ids: set[str] = set()
    seen_raw_ids: set[str] = set()
    bound: list[tuple[dict[str, Any], dict[str, Any], str, str, list[str]]] = []
    for offset in range(len(sources)):
        position = offset + 1
        source = sources[offset]
        raw_row = raw_rows[offset]
        source_id = _record_id(source, "source", position)
        raw_id = _record_id(raw_row, "raw_output", position)
        if source_id in seen_source_ids or raw_id in seen_raw_ids:
            raise InputFailure("duplicate_record_id", f"duplicate record_id at row {position}")
        seen_source_ids.add(source_id)
        seen_raw_ids.add(raw_id)
        declared_position = raw_row.get("processing_position_1based")
        if declared_position != position:
            raise InputFailure("raw_output_position_mismatch", f"raw-output position mismatch at row {position}")
        source_position = source.get("processing_position_1based", position)
        if source_position != position:
            raise InputFailure("source_position_mismatch", f"source position mismatch at row {position}")
        if raw_id != source_id:
            raise InputFailure("record_order_mismatch", f"record order mismatch at row {position}")
        text = source.get("original_text")
        if not isinstance(text, str):
            raise InputFailure("source_text_missing", f"source row {position} requires string original_text")
        source_sha = sha256_text(text)
        binding_errors: list[str] = []
        for key in ("source_text_sha256", "exact_text_sha256"):
            declared_source_sha = source.get(key)
            if declared_source_sha is not None and declared_source_sha != source_sha:
                binding_errors.append(f"source_{key}_mismatch")
        if raw_row.get("source_text_sha256") != source_sha:
            binding_errors.append("raw_output_source_text_sha256_mismatch")
        raw_output = raw_row.get("raw_output")
        if not isinstance(raw_output, str):
            raise InputFailure("raw_output_missing", f"raw-output row {position} requires string raw_output")
        bound.append((source, raw_row, source_id, source_sha, binding_errors))
    return bound


def _schema_errors(validator: Draft202012Validator, value: Any, prefix: str) -> list[str]:
    errors = sorted(validator.iter_errors(value), key=lambda item: str(list(item.absolute_path)))
    return [
        f"{prefix}:{'/'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in errors
    ]


def _error_object(code: str, errors: list[str], model_state: Any = None) -> dict[str, Any]:
    return {
        "object": code,
        "outcome_status": "error",
        "model_state": model_state,
        "main_prior_required_unconditional": None,
        "evidence": [],
        "state_evidence": None,
        "auxiliary_positive_state_quote_evidence": None,
        "duration_assessments": [],
        "normalizations": [],
        "errors": errors,
    }


def _finding_base_for_schema(finding: dict[str, Any]) -> dict[str, Any]:
    """Normalize only the two explicitly allowed mechanical differences."""
    normalized = json.loads(json.dumps(finding, ensure_ascii=False))
    if normalized.get("state") == "positive" and isinstance(normalized.get("state_quote"), str):
        normalized["state_quote"] = None
    mentions = normalized.get("mentions")
    if isinstance(mentions, list):
        for mention in mentions:
            if isinstance(mention, dict) and "duration" in mention:
                mention["duration"] = None
    return normalized


def validate_finding(finding: dict[str, Any], object_name: str, text: str) -> dict[str, Any]:
    model_state = finding.get("state")
    errors = _schema_errors(FINDING_VALIDATOR, _finding_base_for_schema(finding), "structure")
    evidence_atoms: list[dict[str, Any]] = []
    duration_assessments: list[dict[str, Any]] = []
    normalizations: list[dict[str, Any]] = []
    state_evidence = None
    auxiliary_positive_state_quote_evidence = None

    if errors:
        result = _error_object(object_name, errors, model_state)
        return result

    state = finding["state"]
    mentions = finding["mentions"]
    state_quote = finding["state_quote"]
    if state == "positive":
        if not mentions:
            errors.append("state_shape:positive requires at least one mention")
        if state_quote is not None:
            if not isinstance(state_quote, str) or not state_quote:
                errors.append("state_shape:positive redundant state_quote must be a nonempty exact quote")
            else:
                located, quote_errors = compact.locate_unique(
                    text, state_quote, f"{object_name}.state_quote"
                )
                errors.extend(f"state_quote:{error}" for error in quote_errors)
                if located is not None:
                    located["span_id"] = f"s_{object_name}_positive_auxiliary"
                    auxiliary_positive_state_quote_evidence = located
                    normalizations.append({
                        "code": "positive_redundant_state_quote_preserved_as_auxiliary",
                        "semantic_change": False,
                    })
    elif state == "not_mentioned":
        if state_quote is not None or mentions:
            errors.append("state_shape:not_mentioned requires null state_quote and no mentions")
    else:
        if not isinstance(state_quote, str) or not state_quote:
            errors.append(f"state_shape:{state} requires a nonempty exact state_quote")
        if mentions:
            errors.append(f"state_shape:{state} cannot carry positive mentions")
        if isinstance(state_quote, str) and state_quote:
            located, quote_errors = compact.locate_unique(text, state_quote, f"{object_name}.state_quote")
            errors.extend(f"state_quote:{error}" for error in quote_errors)
            if located is not None:
                located["span_id"] = f"s_{object_name}_state"
                state_evidence = located

    for index, mention in enumerate(mentions):
        path = f"{object_name}.mentions[{index}]"
        quote = mention["quote"]
        if compact.BARE_DURATION_QUOTE.fullmatch(quote):
            errors.append(f"quote:{path}: quote is a bare duration without object binding")
        located, quote_errors = compact.locate_unique(text, quote, f"{path}.quote")
        errors.extend(f"quote:{error}" for error in quote_errors)
        if mention["qualification_scope"] in {"education_substitution", "other_conditional"} and len(quote) < 8:
            errors.append(f"quote:{path}: conditional scope quote is too short")
        if located is not None:
            evidence_atoms.append({
                "mention_index_0based": index,
                "condition_mode": mention["condition_mode"],
                "strength": mention["strength"],
                "qualification_scope": mention["qualification_scope"],
                "start": located["start"],
                "end": located["end"],
                "text": located["text"],
                "span_id": f"m_{object_name}_{index + 1}",
            })

        duration = mention["duration"]
        duration_errors: list[str] = []
        if duration is not None:
            duration_errors.extend(_schema_errors(DURATION_VALIDATOR, duration, "duration_structure"))
            if not duration_errors:
                duration_errors.extend(
                    compact.duration_errors(duration, quote, mention["condition_mode"], f"{path}.duration")
                )
        duration_assessments.append({
            "mention_index_0based": index,
            "status": "error" if duration_errors else "candidate",
            "model_duration": duration,
            "errors": duration_errors,
        })

    if errors:
        return {
            "object": object_name,
            "outcome_status": "error",
            "model_state": state,
            "main_prior_required_unconditional": None,
            "evidence": evidence_atoms,
            "state_evidence": state_evidence,
            "auxiliary_positive_state_quote_evidence": auxiliary_positive_state_quote_evidence,
            "duration_assessments": duration_assessments,
            "normalizations": normalizations,
            "errors": errors,
        }

    if state == "unknown":
        outcome_status = "unknown"
        binary = None
    elif state in {"not_mentioned", "no_experience"}:
        outcome_status = "candidate"
        binary = 0
    else:
        definite_positive = any(
            mention["condition_mode"] == "prior_experience"
            and mention["strength"] == "required"
            and mention["qualification_scope"] == "unconditional"
            for mention in mentions
        )
        unresolved = any(
            "unknown" in (
                mention["condition_mode"],
                mention["strength"],
                mention["qualification_scope"],
            )
            for mention in mentions
        )
        if definite_positive:
            outcome_status, binary = "candidate", 1
        elif unresolved:
            outcome_status, binary = "unknown", None
        else:
            outcome_status, binary = "candidate", 0

    return {
        "object": object_name,
        "outcome_status": outcome_status,
        "model_state": state,
        "main_prior_required_unconditional": binary,
        "evidence": evidence_atoms,
        "state_evidence": state_evidence,
        "auxiliary_positive_state_quote_evidence": auxiliary_positive_state_quote_evidence,
        "duration_assessments": duration_assessments,
        "normalizations": normalizations,
        "errors": [],
    }


def export_bound_row(
    source: dict[str, Any],
    raw_row: dict[str, Any],
    record_id: str,
    source_sha: str,
    binding_errors: list[str],
) -> dict[str, Any]:
    raw_output = raw_row["raw_output"]
    row_errors: list[str] = list(binding_errors)
    findings_by_object: dict[str, list[dict[str, Any]]] = {name: [] for name in OBJECT_ORDER}
    try:
        prediction = json.loads(raw_output)
    except json.JSONDecodeError:
        prediction = None
        row_errors.append("raw_output_invalid_json")

    if prediction is not None and not binding_errors:
        if not isinstance(prediction, dict):
            row_errors.append("raw_output_root_not_object")
        else:
            extra_keys = sorted(set(prediction) - {"findings"})
            if extra_keys:
                row_errors.append("raw_output_root_additional_properties")
            findings = prediction.get("findings")
            if not isinstance(findings, list):
                row_errors.append("findings_missing_or_not_array")
            else:
                for finding in findings:
                    if not isinstance(finding, dict):
                        row_errors.append("finding_not_object")
                        continue
                    object_name = finding.get("object")
                    if object_name not in findings_by_object:
                        row_errors.append("finding_unknown_object")
                        continue
                    findings_by_object[object_name].append(finding)

    objects: list[dict[str, Any]] = []
    text = source["original_text"]
    for object_name in OBJECT_ORDER:
        matches = findings_by_object[object_name]
        if prediction is None or not isinstance(prediction, dict) or not isinstance(prediction.get("findings"), list):
            objects.append(_error_object(object_name, ["row_structure:raw output cannot supply findings"]))
        elif len(matches) == 0:
            objects.append(_error_object(object_name, ["structure:object finding is missing"]))
        elif len(matches) > 1:
            objects.append(_error_object(object_name, ["structure:object finding is duplicated"]))
        else:
            objects.append(validate_finding(matches[0], object_name, text))

    if row_errors:
        for obj in objects:
            if obj["outcome_status"] != "error":
                obj["outcome_status"] = "error"
                obj["main_prior_required_unconditional"] = None
                obj["errors"].append("row_structure:unmapped root-level structure error")
    object_statuses = [obj["outcome_status"] for obj in objects]
    if all(status == "candidate" for status in object_statuses):
        row_status = "candidate"
    elif all(status == "error" for status in object_statuses):
        row_status = "error"
    else:
        row_status = "partial"
    return {
        "export_schema_version": EXPORT_SCHEMA_VERSION,
        "processing_position_1based": raw_row["processing_position_1based"],
        "record_id": record_id,
        "source_text_sha256": source_sha,
        "raw_output_sha256": sha256_text(raw_output),
        "raw_output": raw_output,
        "offset_convention": "zero_based_start_end_exclusive_unicode_code_points",
        "row_status": row_status,
        "row_errors": row_errors,
        "objects": objects,
        "interpretation_note": "not_mentioned is a model absence claim, not objective truth; unknown and error remain in the denominator with null outcomes",
    }


def export_rows(
    sources: list[dict[str, Any]], raw_rows: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    bound = bind_rows(sources, raw_rows)
    return [export_bound_row(*item) for item in bound]


def build_public_receipt(
    exports: list[dict[str, Any]], source_file_sha256: str, raw_file_sha256: str
) -> dict[str, Any]:
    object_summary: dict[str, Any] = {}
    for object_name in OBJECT_ORDER:
        object_rows = [
            next(obj for obj in row["objects"] if obj["object"] == object_name)
            for row in exports
        ]
        status_counts = Counter(obj["outcome_status"] for obj in object_rows)
        binary_counts = Counter(
            "null" if obj["main_prior_required_unconditional"] is None
            else str(obj["main_prior_required_unconditional"])
            for obj in object_rows
        )
        duration_counts = Counter(
            assessment["status"]
            for obj in object_rows
            for assessment in obj["duration_assessments"]
        )
        object_summary[object_name] = {
            "eligible_denominator_rows": len(exports),
            "outcome_status_counts": {
                key: status_counts.get(key, 0) for key in ("candidate", "unknown", "error")
            },
            "main_prior_required_unconditional_counts": {
                key: binary_counts.get(key, 0) for key in ("1", "0", "null")
            },
            "duration_assessment_counts": {
                key: duration_counts.get(key, 0) for key in ("candidate", "error")
            },
        }
    return {
        "schema_version": PUBLIC_RECEIPT_VERSION,
        "status": "exported" if all(row["row_status"] == "candidate" for row in exports)
        else "exported_with_unresolved_or_quarantined_fields",
        "row_count": len(exports),
        "source_jsonl_sha256": source_file_sha256,
        "raw_output_jsonl_sha256": raw_file_sha256,
        "private_export_sha256": sha256_text(serialize_jsonl(exports)),
        "row_status_counts": dict(sorted(Counter(row["row_status"] for row in exports).items())),
        "objects": object_summary,
        "normalization_counts": dict(sorted(Counter(
            normalization["code"]
            for row in exports
            for obj in row["objects"]
            for normalization in obj["normalizations"]
        ).items())),
        "privacy": "Aggregate receipt contains no record IDs, source text, evidence quotes, raw model output, or record-level results.",
        "denominator_rule": "Every bound source row remains in every object denominator; unknown and error outcomes are null, never zero or omitted.",
        "absence_rule": "A not_mentioned state is the model's absence claim and is not asserted as objective truth.",
    }


def validate_override_layer(
    override_rows: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate and preserve an external-review layer without applying it."""
    source_by_id: dict[str, tuple[str, str]] = {}
    for position, source in enumerate(sources, 1):
        record_id = _record_id(source, "source", position)
        text = source.get("original_text")
        if not isinstance(text, str):
            raise InputFailure("source_text_missing", f"source row {position} requires string original_text")
        source_by_id[record_id] = (text, sha256_text(text))
    validated: list[dict[str, Any]] = []
    seen_targets: set[tuple[str, str, str, str]] = set()
    required = {
        "override_version", "record_id", "source_text_sha256", "object", "field",
        "corrected_value", "reason", "source_quote",
    }
    for position, row in enumerate(override_rows, 1):
        missing = sorted(required - set(row))
        if missing:
            raise InputFailure("override_missing_fields", f"override row {position} lacks required fields")
        record_id = str(row["record_id"])
        if record_id not in source_by_id:
            raise InputFailure("override_unknown_record", f"override row {position} has unknown record")
        if row["object"] not in OBJECT_ORDER:
            raise InputFailure("override_unknown_object", f"override row {position} has unknown object")
        if not isinstance(row["override_version"], str) or not row["override_version"].strip():
            raise InputFailure("override_version_missing", f"override row {position} lacks a version")
        if not isinstance(row["field"], str) or not row["field"].strip():
            raise InputFailure("override_field_missing", f"override row {position} lacks a field")
        if not isinstance(row["reason"], str) or not row["reason"].strip():
            raise InputFailure("override_reason_missing", f"override row {position} lacks a reason")
        quote = row["source_quote"]
        if not isinstance(quote, str) or not quote:
            raise InputFailure("override_quote_missing", f"override row {position} lacks a source quote")
        text, source_sha = source_by_id[record_id]
        if row["source_text_sha256"] != source_sha:
            raise InputFailure("override_hash_mismatch", f"override row {position} source hash differs")
        evidence, errors = compact.locate_unique(text, quote, f"override[{position}].source_quote")
        if errors:
            raise InputFailure("override_quote_invalid", f"override row {position} quote is not uniquely exact")
        target = (row["override_version"], record_id, row["object"], row["field"])
        if target in seen_targets:
            raise InputFailure("override_duplicate_target", f"override row {position} duplicates a target")
        seen_targets.add(target)
        validated.append({
            **row,
            "source_evidence": evidence,
            "application_status": "received_unapplied",
        })
    return {
        "schema_version": OVERRIDE_RECEIPT_VERSION,
        "status": "received_unapplied",
        "override_count": len(validated),
        "overrides": validated,
        "note": "External semantic corrections are a separate versioned layer. Raw outputs and candidate exports were not overwritten.",
    }


def serialize_jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )


def atomic_write(path: Path, content: str, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="ordered source JSONL")
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--raw-outputs", type=Path, help="explicitly bound raw-output JSONL")
    input_group.add_argument("--reader-predictions", type=Path, help="bare reader JSONL to bind through --order")
    parser.add_argument("--order", type=Path, help="record-ID array for --reader-predictions")
    parser.add_argument("--wrapped-raw-outputs", type=Path, help="new wrapper JSONL written by adapter mode")
    parser.add_argument("--private-output", type=Path, required=True, help="private candidate JSONL")
    parser.add_argument("--public-receipt", type=Path, required=True, help="aggregate receipt without IDs or raw data")
    parser.add_argument("--review-overrides", type=Path, help="optional external-review override JSONL")
    parser.add_argument("--override-receipt", type=Path, help="required private receipt when overrides are supplied")
    args = parser.parse_args()
    if bool(args.review_overrides) != bool(args.override_receipt):
        parser.error("--review-overrides and --override-receipt must be supplied together")
    if args.reader_predictions and (not args.order or not args.wrapped_raw_outputs):
        parser.error("--reader-predictions requires --order and --wrapped-raw-outputs")
    if args.raw_outputs and (args.order or args.wrapped_raw_outputs):
        parser.error("--order and --wrapped-raw-outputs apply only to --reader-predictions")

    try:
        sources = strict_jsonl(args.source, "source")
        if args.reader_predictions:
            if args.wrapped_raw_outputs.exists():
                raise InputFailure(
                    "adapter_output_exists",
                    "wrapped raw-output target already exists; refusing to overwrite it",
                )
            raw_rows = adapt_reader_outputs(sources, args.reader_predictions, args.order)
            raw_input_bytes = args.reader_predictions.read_bytes()
        else:
            raw_rows = strict_jsonl(args.raw_outputs, "raw_output")
            raw_input_bytes = args.raw_outputs.read_bytes()
        exports = export_rows(sources, raw_rows)
        override_receipt = None
        if args.review_overrides:
            override_rows = strict_jsonl(args.review_overrides, "override")
            override_receipt = validate_override_layer(override_rows, sources)
    except InputFailure as exc:
        failure_receipt = {
            "schema_version": PUBLIC_RECEIPT_VERSION,
            "status": "input_rejected",
            "failure_category": exc.code,
            "private_output_written": False,
            "privacy": "No record IDs, source text, raw model output, or record-level results are included.",
        }
        atomic_write(args.public_receipt, json.dumps(failure_receipt, indent=2, sort_keys=True) + "\n", 0o644)
        print(f"input rejected: {exc.code}", file=sys.stderr)
        return 2

    private_content = serialize_jsonl(exports)
    receipt = build_public_receipt(
        exports,
        sha256_bytes(args.source.read_bytes()),
        sha256_bytes(raw_input_bytes),
    )
    if args.reader_predictions:
        atomic_write(args.wrapped_raw_outputs, serialize_jsonl(raw_rows), 0o600)
    atomic_write(args.private_output, private_content, 0o600)
    atomic_write(args.public_receipt, json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", 0o644)
    if override_receipt is not None:
        atomic_write(
            args.override_receipt,
            json.dumps(override_receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            0o600,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
