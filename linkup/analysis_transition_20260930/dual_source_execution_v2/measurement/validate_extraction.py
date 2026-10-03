#!/usr/bin/env python3
"""JSON Schema plus source-binding checks for LinkUp measurement v1."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent
SCHEMA_PATH = ROOT / "schema" / "extraction_v1.schema.json"
OBJECTS = {"general_work", "occupation_task", "industry_domain", "specific_tool"}
AI_CLASSES = {"predictive_ml_ai", "generative_ai", "ai_unspecified"}


def load_schema() -> dict[str, Any]:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return schema


SCHEMA = load_schema()
SCHEMA_VALIDATOR = Draft202012Validator(SCHEMA)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _span_errors(span: dict[str, Any], source_text: str, path: str) -> list[str]:
    start, end = span["start"], span["end"]
    errors: list[str] = []
    if end <= start:
        errors.append(f"{path}: end must be greater than start")
    elif end > len(source_text):
        errors.append(f"{path}: end {end} exceeds source length {len(source_text)}")
    elif source_text[start:end] != span["text"]:
        errors.append(f"{path}: offsets do not reproduce exact source text")
    return errors


def _duration_errors(duration: dict[str, Any], span_ids: set[str], path: str) -> list[str]:
    errors: list[str] = []
    if duration["evidence_span_id"] not in span_ids:
        errors.append(f"{path}: duration is not bound to an evidence span in its own mention")
    kind = duration["interpretation"]
    stated, lower, upper = duration["stated_value"], duration["lower"], duration["upper"]
    valid_shape = {
        "minimum": stated is not None and lower == stated and upper is None,
        "maximum": stated is not None and lower is None and upper == stated,
        "exact": stated is not None and lower == stated and upper == stated,
        "range": stated is None and lower is not None and upper is not None and lower <= upper,
        "stated_unspecified": stated is not None and lower is None and upper is None,
    }[kind]
    if not valid_shape:
        errors.append(f"{path}: bounds do not match interpretation={kind}")
    return errors


def validate_record(record: dict[str, Any], source_text: str, expected_record_id: str | None = None) -> list[str]:
    """Return all structural and semantic validation errors for one record."""
    errors = [
        f"schema:{'/'.join(str(part) for part in error.absolute_path) or '$'}: {error.message}"
        for error in sorted(SCHEMA_VALIDATOR.iter_errors(record), key=lambda e: list(e.absolute_path))
    ]
    if errors:
        return errors
    if expected_record_id is not None and record["record_id"] != expected_record_id:
        errors.append("record_id does not match source record")
    if record["source_text_sha256"] != sha256_text(source_text):
        errors.append("source_text_sha256 does not match exact source text")

    findings = record["experience_findings"]
    found_objects = [item["object"] for item in findings]
    if set(found_objects) != OBJECTS or len(set(found_objects)) != 4:
        errors.append("experience_findings must contain each of the four objects exactly once")

    all_ids: set[str] = set()
    for finding_index, finding in enumerate(findings):
        base = f"experience_findings[{finding_index}]"
        state = finding["state"]
        mentions = finding["mentions"]
        state_evidence = finding["state_evidence"]
        if state == "explicit_positive" and not mentions:
            errors.append(f"{base}: explicit_positive requires at least one mention")
        if state in {"explicit_positive", "explicit_negative"} and not finding["state_applicant_context"]:
            errors.append(f"{base}: positive/negative state must be applicant-facing")
        if state in {"not_mentioned", "insufficient_text"} and finding["state_applicant_context"]:
            errors.append(f"{base}: {state} cannot assert applicant context")
        if state != "explicit_positive" and mentions:
            errors.append(f"{base}: {state} cannot carry positive mentions or duration values")
        if state == "explicit_negative" and not state_evidence:
            errors.append(f"{base}: explicit_negative requires exact source evidence")
        if state in {"not_mentioned", "insufficient_text"} and state_evidence:
            errors.append(f"{base}: {state} cannot be supported by a fabricated positive/negative span")
        for span_index, span in enumerate(state_evidence):
            errors.extend(_span_errors(span, source_text, f"{base}.state_evidence[{span_index}]"))
        for mention_index, mention in enumerate(mentions):
            mention_path = f"{base}.mentions[{mention_index}]"
            if mention["mention_id"] in all_ids:
                errors.append(f"{mention_path}: duplicate mention_id")
            all_ids.add(mention["mention_id"])
            if not mention["applicant_context"]:
                errors.append(f"{mention_path}: non-applicant evidence cannot support an experience positive")
            if mention["branch_relation"] in {"or", "equivalent"} and not mention["alternative_group"]:
                errors.append(f"{mention_path}: OR/equivalent branch requires alternative_group")
            if mention["branch_relation"] in {"standalone", "and"} and mention["alternative_group"] is not None:
                errors.append(f"{mention_path}: standalone/AND branch cannot carry alternative_group")
            span_ids: set[str] = set()
            for span_index, span in enumerate(mention["evidence"]):
                if span["span_id"] in span_ids:
                    errors.append(f"{mention_path}: duplicate span_id inside mention")
                span_ids.add(span["span_id"])
                errors.extend(_span_errors(span, source_text, f"{mention_path}.evidence[{span_index}]"))
            if mention["duration"] is not None:
                errors.extend(_duration_errors(mention["duration"], span_ids, f"{mention_path}.duration"))

    technology_ids: set[str] = set()
    for finding_index, finding in enumerate(record["technology_findings"]):
        base = f"technology_findings[{finding_index}]"
        state, evidence = finding["state"], finding["evidence"]
        if finding["finding_id"] in technology_ids:
            errors.append(f"{base}: duplicate finding_id")
        technology_ids.add(finding["finding_id"])
        if state in {"explicit_positive", "explicit_negative"} and not evidence:
            errors.append(f"{base}: {state} requires exact source evidence")
        if state in {"explicit_positive", "explicit_negative"} and not finding["applicant_context"]:
            errors.append(f"{base}: positive/negative technology state must be applicant-facing")
        if state in {"not_mentioned", "insufficient_text"} and evidence:
            errors.append(f"{base}: {state} cannot carry a positive/negative evidence span")
        for span_index, span in enumerate(evidence):
            errors.extend(_span_errors(span, source_text, f"{base}.evidence[{span_index}]"))
        basis, role, tech_class = finding["ai_role_basis"], finding["technology_role"], finding["technology_class"]
        expected_role = {
            "develop_or_train_ai": "develop_train",
            "implement_or_integrate_ai": "implement_integrate",
            "use_ai_to_write_software": "use_operate",
            "use_ai_other": "use_operate",
            "evaluate_or_govern_ai": "evaluate_govern",
        }.get(basis)
        if expected_role is not None and role != expected_role:
            errors.append(f"{base}: ai_role_basis={basis} requires technology_role={expected_role}")
        if basis in {"develop_or_train_ai", "implement_or_integrate_ai", "use_ai_to_write_software", "use_ai_other", "evaluate_or_govern_ai"} and tech_class not in AI_CLASSES:
            errors.append(f"{base}: AI role basis requires an AI technology class")
        if basis == "use_ai_to_write_software" and role == "develop_train":
            errors.append(f"{base}: using AI to write software is not developing/training AI")
        if tech_class in AI_CLASSES and basis == "not_ai":
            errors.append(f"{base}: AI class cannot use ai_role_basis=not_ai")
    return errors


def validate_jsonl(source_rows: list[dict[str, Any]], prediction_path: Path) -> dict[str, Any]:
    source_by_id = {str(row["record_id"]): row for row in source_rows}
    predictions: dict[str, dict[str, Any]] = {}
    parse_errors: list[str] = []
    with prediction_path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                parse_errors.append(f"line {line_number}: invalid JSON: {exc.msg}")
                continue
            record_id = str(record.get("record_id", ""))
            if not record_id:
                parse_errors.append(f"line {line_number}: missing record_id")
            elif record_id in predictions:
                parse_errors.append(f"line {line_number}: duplicate record_id={record_id}")
            else:
                predictions[record_id] = record
    record_errors: dict[str, list[str]] = {}
    for record_id, record in predictions.items():
        if record_id not in source_by_id:
            record_errors[record_id] = ["prediction has no matching source record"]
            continue
        source = source_by_id[record_id]
        found = validate_record(record, source["original_text"], record_id)
        if found:
            record_errors[record_id] = found
    missing = sorted(set(source_by_id) - set(predictions))
    valid_count = len(predictions) - len(record_errors)
    denominator = len(source_by_id)
    return {
        "schema_version": SCHEMA["properties"]["schema_version"]["const"],
        "source_records": denominator,
        "prediction_records": len(predictions),
        "valid_records": valid_count,
        "structured_output_valid_fraction": valid_count / denominator if denominator else None,
        "missing_prediction_ids": missing,
        "parse_errors": parse_errors,
        "record_errors": record_errors,
        "passes_0_99_structure_gate": bool(denominator and valid_count / denominator >= 0.99 and not missing and not parse_errors),
        "semantic_note": "This validates structure and source binding; it is not a truth-accuracy estimate."
    }
