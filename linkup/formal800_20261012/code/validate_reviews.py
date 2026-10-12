#!/usr/bin/env python3
"""Validate frozen formal800 reviews without creating semantic values.

The packet is trusted for blinded identity, complete text, and reviewer
assignment. Review output supplies only the schema-defined semantic record.
Exact quote offsets are resolved here against Python Unicode strings; every
occurrence is retained and missing quotes invalidate the record.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any

VERSION = "formal800-review-validation-v1.1-shared-condition"
EXP_DIMS = ("general_work", "occupation_task", "industry_domain", "tool_specific")
ENTRY_DIMS = (
    "explicit_no_experience", "explicit_new_graduate",
    "current_student_internship", "explicit_junior_or_entry_label",
)
RESP_DIMS = (
    "independent_judgment", "client_ownership",
    "people_supervision", "training_mentoring",
)
RESP_SUPPORT_RELATIONS = {"current_duty", "required_capability", "prior_experience"}
ASSIGNMENT_ROLES = {"primary", "blind_audit"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    output = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except Exception as exc:
                raise RuntimeError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
            if not isinstance(value, dict):
                raise RuntimeError(f"JSONL row is not an object at {path}:{line_number}")
            output.append(value)
    return output


def atomic_json(path: Path, value: Any, mode: int | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if mode is not None:
        os.chmod(temporary, mode)
    os.replace(temporary, path)


def atomic_jsonl(path: Path, values: list[dict[str, Any]], mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(path) + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        for value in values:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def find_all(text: str, quote: str) -> list[dict[str, int]]:
    """Return all overlapping Unicode-code-point spans for an exact quote."""
    spans = []
    start = 0
    while True:
        position = text.find(quote, start)
        if position < 0:
            return spans
        spans.append({"start": position, "end": position + len(quote)})
        start = position + 1


def quote_arrays(value: Any, path: tuple[Any, ...] = ()):
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = path + (key,)
            if key == "quotes" and isinstance(child, list):
                for index, quote in enumerate(child):
                    yield child_path + (index,), quote
            else:
                yield from quote_arrays(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from quote_arrays(child, path + (index,))


def path_string(path: tuple[Any, ...]) -> str:
    return "/" + "/".join(str(part).replace("~", "~0").replace("/", "~1") for part in path)


def validate_packet(packet: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for row in packet:
        if set(row) != {"record_id", "context_sha256", "full_document", "assignment"}:
            raise RuntimeError("packet rows must contain exactly record_id, context_sha256, full_document, assignment")
        record_id = row["record_id"]
        text = row["full_document"]
        context_sha = row["context_sha256"]
        assignment = row["assignment"]
        if not isinstance(record_id, str) or not record_id or record_id in by_id:
            raise RuntimeError("packet record_id is empty or duplicated")
        if not isinstance(text, str) or not text:
            raise RuntimeError(f"packet full_document is empty for {record_id}")
        if context_sha != sha256_text(text):
            raise RuntimeError(f"packet context hash mismatch for {record_id}")
        if not isinstance(assignment, dict):
            raise RuntimeError(f"packet assignment is not an object for {record_id}")
        required = {"packet_id", "reviewer_role", "provenance"}
        if not required <= set(assignment):
            raise RuntimeError(f"packet trusted assignment fields missing for {record_id}")
        if assignment["reviewer_role"] not in ASSIGNMENT_ROLES:
            raise RuntimeError(f"packet reviewer_role is invalid for {record_id}")
        for field in required:
            if not isinstance(assignment[field], str) or not assignment[field]:
                raise RuntimeError(f"packet assignment {field} is empty for {record_id}")
        by_id[record_id] = row
    if not by_id:
        raise RuntimeError("packet is empty")
    return by_id


def add_error(errors: list[str], condition: bool, message: str) -> None:
    if condition:
        errors.append(message)


def validate_years(clause: dict[str, Any], errors: list[str], index: int) -> None:
    minimum, maximum, relation = clause["years_min"], clause["years_max"], clause["years_relation"]
    prefix = f"experience_clauses[{index}]"
    add_error(errors, minimum is not None and maximum is not None and minimum > maximum,
              f"{prefix}: years_min exceeds years_max")
    expected = {
        "not_stated": minimum is None and maximum is None,
        "at_least": minimum is not None and maximum is None,
        "at_most": minimum is None and maximum is not None,
        "exact": minimum is not None and maximum is not None and minimum == maximum,
        "range": minimum is not None and maximum is not None and minimum <= maximum,
    }
    if relation in expected:
        add_error(errors, not expected[relation], f"{prefix}: bounds disagree with years_relation={relation}")


def validate_cross_fields(review: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    full = review["document_status"] == "reviewed_full"
    outcome_groups = (
        review["experience_outcomes"], review["entry_outcomes"], review["responsibility_outcomes"]
    )
    if not full:
        for group in outcome_groups:
            for name, value in group.items():
                add_error(errors, value == "not_mentioned",
                          f"{name}: not_mentioned requires reviewed_full")
        add_error(errors, review["technology_inventory_status"] == "not_mentioned_after_full_review",
                  "technology nonmention requires reviewed_full")

    clauses = review["experience_clauses"]
    for index, clause in enumerate(clauses):
        validate_years(clause, errors, index)
    for dimension in EXP_DIMS:
        supporting = [
            item for item in clauses
            if item["object"] == dimension and item["strength"] in {"required", "preferred", "unspecified"}
        ]
        outcome = review["experience_outcomes"][dimension]
        add_error(errors, outcome == "present" and not supporting,
                  f"experience {dimension}: present lacks a matching non-waived clause")
        add_error(errors, outcome == "not_mentioned" and bool(supporting),
                  f"experience {dimension}: not_mentioned conflicts with a non-waived clause")

    entry_items = review["entry_items"]
    for dimension in ENTRY_DIMS:
        matching = [item for item in entry_items if item["target"] == dimension]
        outcome = review["entry_outcomes"][dimension]
        add_error(errors, outcome == "present" and not matching,
                  f"entry {dimension}: present lacks a matching item")
        add_error(errors, outcome == "not_mentioned" and bool(matching),
                  f"entry {dimension}: not_mentioned conflicts with a matching item")

    responsibility_items = review["responsibility_items"]
    for dimension in RESP_DIMS:
        supporting = [
            item for item in responsibility_items
            if item["dimension"] == dimension
            and item["subject"] == "advertised_worker"
            and item["relation"] in RESP_SUPPORT_RELATIONS
        ]
        outcome = review["responsibility_outcomes"][dimension]
        add_error(errors, outcome == "present" and not supporting,
                  f"responsibility {dimension}: present lacks applicable advertised-worker support")
        add_error(errors, outcome == "not_mentioned" and bool(supporting),
                  f"responsibility {dimension}: not_mentioned conflicts with applicable support")

    technology_items = review["technology_items"]
    technology_status = review["technology_inventory_status"]
    add_error(errors, technology_status == "explicit_mentions_recorded" and not technology_items,
              "technology status says explicit mentions but inventory is empty")
    add_error(errors, technology_status == "not_mentioned_after_full_review" and bool(technology_items),
              "technology nonmention conflicts with nonempty inventory")
    add_error(errors, bool(technology_items) and technology_status != "explicit_mentions_recorded",
              "nonempty technology inventory requires explicit_mentions_recorded status")

    declared: dict[str, set[str]] = {}
    for index, group in enumerate(review["qualification_alternatives"]):
        name = group["group"]
        add_error(errors, name in declared, f"qualification group is duplicated: {name}")
        branches = group["branches"]
        add_error(errors, not branches, f"qualification group has no branches: {name}")
        branch_names = [branch["branch"] for branch in branches]
        add_error(errors, len(branch_names) != len(set(branch_names)),
                  f"qualification group has duplicate branch names: {name}")
        declared[name] = set(branch_names)
    for index, clause in enumerate(clauses):
        group, branch = clause["alternative_group"], clause["alternative_branch"]
        # A shared condition can govern a genuine alternative group without
        # being another option in it. A branch still requires a declared group.
        add_error(errors, group is None and branch is not None,
                  f"experience_clauses[{index}]: alternative branch requires a group")
        if group is not None:
            add_error(errors, group not in declared,
                      f"experience_clauses[{index}]: undeclared alternative group")
            if group in declared and branch is not None:
                add_error(errors, branch not in declared[group],
                          f"experience_clauses[{index}]: undeclared alternative branch")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--reviews", type=Path, nargs="+", required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--private-validated", type=Path, required=True)
    parser.add_argument("--private-errors", type=Path, required=True)
    parser.add_argument("--public-receipt", type=Path, required=True)
    parser.add_argument("--expected-records", type=int)
    args = parser.parse_args()

    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema with Draft202012Validator is required") from exc

    packet = read_jsonl(args.packet)
    packet_by_id = validate_packet(packet)
    if args.expected_records is not None and len(packet) != args.expected_records:
        raise RuntimeError("packet count does not equal --expected-records")
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    reviews: list[dict[str, Any]] = []
    for path in args.reviews:
        reviews.extend(read_jsonl(path))

    reviews_by_id: dict[str, dict[str, Any]] = {}
    private_errors: list[dict[str, Any]] = []
    for index, review in enumerate(reviews, 1):
        record_id = review.get("record_id")
        if not isinstance(record_id, str) or not record_id:
            private_errors.append({"input_row": index, "record_id": None, "errors": ["missing record_id"]})
            continue
        if record_id in reviews_by_id:
            private_errors.append({"input_row": index, "record_id": record_id, "errors": ["duplicate review record_id"]})
            continue
        reviews_by_id[record_id] = review

    for record_id in sorted(set(reviews_by_id) - set(packet_by_id)):
        private_errors.append({"record_id": record_id, "errors": ["review record_id is outside trusted packet"]})
    for record_id in sorted(set(packet_by_id) - set(reviews_by_id)):
        private_errors.append({"record_id": record_id, "errors": ["trusted packet record has no review"]})

    validated: list[dict[str, Any]] = []
    counters = collections.Counter()
    for record_id in sorted(set(packet_by_id) & set(reviews_by_id)):
        packet_row = packet_by_id[record_id]
        review = reviews_by_id[record_id]
        errors = []
        schema_errors = sorted(validator.iter_errors(review), key=lambda item: list(item.absolute_path))
        for error in schema_errors:
            errors.append(f"schema {path_string(tuple(error.absolute_path))}: {error.message}")
        if not schema_errors:
            if review["context_sha256"] != packet_row["context_sha256"]:
                errors.append("context_sha256 does not match trusted packet")
            errors.extend(validate_cross_fields(review))

        resolutions = []
        if not schema_errors:
            for quote_path, quote in quote_arrays(review):
                spans = find_all(packet_row["full_document"], quote)
                if not spans:
                    errors.append(f"exact quote missing at {path_string(quote_path)}")
                    continue
                counters["quote_instances"] += 1
                counters["quote_occurrences"] += len(spans)
                if len(spans) > 1:
                    counters["ambiguous_quote_instances"] += 1
                resolutions.append({
                    "path": path_string(quote_path),
                    "quote": quote,
                    "occurrences": spans,
                    "repeated_ambiguity": len(spans) > 1,
                    "offset_unit": "Unicode_code_points",
                })
        if errors:
            private_errors.append({"record_id": record_id, "errors": errors})
            continue
        assignment = packet_row["assignment"]
        counters[f"valid_role_{assignment['reviewer_role']}"] += 1
        validated.append({
            **review,
            "trusted_assignment": assignment,
            "evidence_resolution": resolutions,
            "validation_version": VERSION,
        })

    atomic_jsonl(args.private_validated, validated)
    atomic_jsonl(args.private_errors, private_errors)
    status = "pass" if not private_errors and len(validated) == len(packet) else "fail"
    receipt = {
        "version": VERSION,
        "status": status,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs": {
            "packet_sha256": sha256_file(args.packet),
            "review_inputs": [
                {"name": path.name, "sha256": sha256_file(path)} for path in args.reviews
            ],
            "schema_sha256": sha256_file(args.schema),
        },
        "counts": {
            "trusted_packet_records": len(packet),
            "submitted_review_rows": len(reviews),
            "validated_records": len(validated),
            "error_entries": len(private_errors),
            "quote_instances": counters["quote_instances"],
            "quote_occurrences": counters["quote_occurrences"],
            "ambiguous_quote_instances": counters["ambiguous_quote_instances"],
            "valid_primary_records": counters["valid_role_primary"],
            "valid_blind_audit_records": counters["valid_role_blind_audit"],
        },
        "checks": {
            "draft202012_schema": True,
            "trusted_packet_binding": True,
            "trusted_assignment_not_model_authored": True,
            "partial_nonmention_prohibited": True,
            "positive_item_consistency": True,
            "years_and_alternative_references": True,
            "exact_quotes_all_unicode_offsets": True,
            "missing_quotes_rejected": True,
            "no_semantic_fill_or_aggregation": True,
        },
        "private_outputs": {
            "validated_rows": len(validated),
            "validated_sha256": sha256_file(args.private_validated),
            "error_entries": len(private_errors),
            "errors_sha256": sha256_file(args.private_errors),
        },
        "claim_boundary": "identity, schema, cross-field, and exact-evidence validation only; no semantic accuracy or population claim",
    }
    atomic_json(args.public_receipt, receipt)
    if status != "pass":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
