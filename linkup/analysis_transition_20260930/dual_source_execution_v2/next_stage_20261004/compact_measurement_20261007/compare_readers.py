#!/usr/bin/env python3
"""Compare two compact readers while keeping source identities out of public output."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from collections import Counter
from pathlib import Path
from typing import Any

from expand_and_validate import OBJECTS, SCHEMA_VALIDATOR, sha256_text, validate_and_expand


EXPECTED_COUNT = 20
OBJECT_ORDER = ("general_work", "occupation_task", "industry_domain")
METRICS = ("object_state", "main_estimand_presence", "label_signature", "duration_bound_signature")


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl_strict(path: Path, expected: int = EXPECTED_COUNT) -> list[Any]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if any(not line.strip() for line in lines):
        raise ValueError(f"{path}: blank JSONL lines are not allowed")
    if len(lines) != expected:
        raise ValueError(f"{path}: expected exactly {expected} rows, found {len(lines)}")
    rows = []
    for index, line in enumerate(lines, 1):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}: line {index} is invalid JSON: {exc.msg}") from exc
    return rows


def read_order_ids(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    try:
        whole = json.loads(text)
    except json.JSONDecodeError:
        whole = None
    if isinstance(whole, dict) and set(whole) == {"record_ids"}:
        values = whole["record_ids"]
    elif isinstance(whole, list):
        values = whole
    else:
        values = read_jsonl_strict(path)
    if not isinstance(values, list) or len(values) != EXPECTED_COUNT:
        raise ValueError(f"{path}: order sidecar must contain exactly {EXPECTED_COUNT} IDs")
    result = []
    for index, value in enumerate(values, 1):
        if isinstance(value, dict) and set(value) in ({"record_id"}, {"index", "record_id"}):
            if "index" in value and value["index"] != index - 1:
                raise ValueError(f"{path}: order sidecar row {index} has a nonsequential index")
            value = value["record_id"]
        if not isinstance(value, (str, int)):
            raise ValueError(f"{path}: order sidecar row {index} is not an ID")
        result.append(str(value))
    return result


def write_precondition_failure(public_path: Path, private_path: Path, category: str, detail: str) -> None:
    public_path.parent.mkdir(parents=True, exist_ok=True)
    private_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_text(json.dumps({
        "status": "failed_precondition",
        "comparison_performed": False,
        "failure_category": category,
        "scope": "No partial agreement counts were computed.",
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    private_path.write_text(json.dumps({
        "status": "failed_precondition",
        "comparison_performed": False,
        "failure_category": category,
        "detail": detail,
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(private_path, 0o600)


def load_and_bind_sources(source_path: Path, manifest_path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sources = read_jsonl_strict(source_path)
    manifest = read_jsonl_strict(manifest_path)
    seen_ids, seen_hashes = set(), set()
    heldout_counts = Counter()
    development = 0
    for index, (source, key) in enumerate(zip(sources, manifest), 1):
        if not isinstance(source, dict) or set(source) != {"record_id", "original_text"}:
            raise ValueError(f"source row {index}: expected only record_id and original_text")
        if not isinstance(source["record_id"], (str, int)) or not isinstance(source["original_text"], str):
            raise ValueError(f"source row {index}: invalid record_id or original_text type")
        if not isinstance(key, dict):
            raise ValueError(f"manifest row {index}: expected object")
        review_id = str(source["record_id"])
        digest = sha256_text(source["original_text"])
        if str(key.get("review_id")) != review_id or key.get("source_text_sha256") != digest:
            raise ValueError(f"row {index}: source and unblind manifest order/binding mismatch")
        if review_id in seen_ids or digest in seen_hashes:
            raise ValueError(f"row {index}: duplicate source identity or exact text")
        seen_ids.add(review_id)
        seen_hashes.add(digest)
        split, arm = key.get("split"), key.get("arm")
        if split == "development":
            development += 1
        elif split == "heldout" and arm in {"A", "B"}:
            heldout_counts[arm] += 1
        else:
            raise ValueError(f"manifest row {index}: invalid split/arm")
    if development != 4 or heldout_counts != Counter({"A": 8, "B": 8}):
        raise ValueError(f"manifest split invariant failed: development={development}, heldout={dict(heldout_counts)}")
    return sources, manifest


def normalize_prediction(raw: Any, expected_record_id: str) -> tuple[dict[str, Any] | None, list[str], str]:
    if not isinstance(raw, dict):
        return None, ["transport: row is not a JSON object"], "invalid"
    if set(raw) == {"findings"}:
        return raw, [], "positional"
    if set(raw) == {"record_id", "prediction"} and isinstance(raw.get("prediction"), dict):
        if str(raw["record_id"]) != expected_record_id:
            return None, ["binding: caller envelope record_id does not match source order"], "envelope"
        return raw["prediction"], [], "envelope"
    if set(raw) == {"record_id", "findings"}:
        if str(raw["record_id"]) != expected_record_id:
            return None, ["binding: caller record_id does not match source order"], "caller_id"
        return {"findings": raw["findings"]}, [], "caller_id"
    return raw, [], "positional"


def canonical_duration(duration: dict[str, Any] | None) -> tuple[Any, ...]:
    if duration is None:
        return ("none",)
    if duration["kind"] == "range":
        return ("range", duration["lower"], duration["upper"])
    return (duration["kind"], duration["value"])


def semantic_view(prediction: dict[str, Any] | None) -> tuple[dict[str, dict[str, Any]] | None, list[str]]:
    if prediction is None:
        return None, ["semantic_shape: prediction unavailable"]
    schema_errors = sorted(SCHEMA_VALIDATOR.iter_errors(prediction), key=lambda item: str(list(item.absolute_path)))
    if schema_errors:
        return None, ["semantic_shape: schema invalid"]
    findings = prediction["findings"]
    by_object = {finding["object"]: finding for finding in findings}
    if len(by_object) != 3 or set(by_object) != OBJECTS:
        return None, ["semantic_shape: compact objects are not exactly unique"]
    view: dict[str, dict[str, Any]] = {}
    for obj in OBJECT_ORDER:
        finding = by_object[obj]
        mentions = finding["mentions"]
        labels = sorted(
            (mention["strength"], mention["condition_mode"], mention["qualification_scope"])
            for mention in mentions
        )
        duration_bound = sorted(
            (
                mention["strength"], mention["condition_mode"], mention["qualification_scope"],
                canonical_duration(mention["duration"]),
            )
            for mention in mentions
        )
        view[obj] = {
            "object_state": finding["state"],
            "main_estimand_presence": any(
                mention["strength"] == "required"
                and mention["condition_mode"] == "prior_experience"
                and mention["qualification_scope"] == "unconditional"
                for mention in mentions
            ),
            "label_signature": labels,
            "duration_bound_signature": duration_bound,
        }
    return view, []


def public_error_category(error: str) -> str:
    if error.startswith("transport:"):
        return "transport"
    if error.startswith("binding:"):
        return "binding"
    if error.startswith("schema:"):
        return "schema"
    if "not an exact source substring" in error:
        return "quote_missing"
    if "quote occurs" in error:
        return "quote_ambiguous"
    if "bare duration" in error:
        return "quote_duration_only"
    if ".duration:" in error:
        return "duration_support"
    if "findings must contain" in error:
        return "object_set"
    if "requires" in error or "cannot carry" in error:
        return "state_shape"
    return "other_validation"


def empty_metric() -> dict[str, Any]:
    return {
        "by_object": {obj: {"agree": 0, "comparable": 0} for obj in OBJECT_ORDER},
        "all_objects": {"agree": 0, "comparable": 0},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--unblind-manifest", type=Path, required=True)
    parser.add_argument("--reader", action="append", required=True, metavar="NAME=PATH")
    parser.add_argument("--reader-order", action="append", required=True, metavar="NAME=ORDER_PRIVATE_PATH")
    parser.add_argument("--public-output", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    args = parser.parse_args()

    reader_paths: dict[str, Path] = {}
    for item in args.reader:
        if "=" not in item:
            parser.error("--reader must be NAME=PATH")
        name, raw_path = item.split("=", 1)
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", name) or name in reader_paths:
            parser.error("reader names must be unique and contain only letters, numbers, dot, underscore, or hyphen")
        reader_paths[name] = Path(raw_path)
    if len(reader_paths) != 2:
        parser.error("exactly two --reader arguments are required")

    order_paths: dict[str, Path] = {}
    for item in args.reader_order:
        if "=" not in item:
            parser.error("--reader-order must be NAME=PATH")
        name, raw_path = item.split("=", 1)
        if name in order_paths:
            parser.error("reader-order names must be unique")
        order_paths[name] = Path(raw_path)
    if set(order_paths) != set(reader_paths):
        parser.error("--reader-order names must match the two --reader names exactly")

    try:
        sources, manifest = load_and_bind_sources(args.source, args.unblind_manifest)
    except (OSError, ValueError) as exc:
        write_precondition_failure(args.public_output, args.private_output, "source_manifest_binding", str(exc))
        return 2
    try:
        raw_readers = {name: read_jsonl_strict(path) for name, path in reader_paths.items()}
    except (OSError, ValueError) as exc:
        write_precondition_failure(args.public_output, args.private_output, "reader_jsonl_structure", str(exc))
        return 2
    try:
        expected_ids = [str(source["record_id"]) for source in sources]
        for name, path in order_paths.items():
            if read_order_ids(path) != expected_ids:
                raise ValueError(f"{name}: ORDER_PRIVATE IDs do not match source positions")
    except (OSError, ValueError) as exc:
        write_precondition_failure(args.public_output, args.private_output, "reader_order_binding", str(exc))
        return 2
    reader_names = list(reader_paths)
    groups = {
        "overall": list(range(EXPECTED_COUNT)),
        "heldout_A": [index for index, row in enumerate(manifest) if row["split"] == "heldout" and row["arm"] == "A"],
        "heldout_B": [index for index, row in enumerate(manifest) if row["split"] == "heldout" and row["arm"] == "B"],
    }
    if len(groups["heldout_A"]) != 8 or len(groups["heldout_B"]) != 8:
        raise ValueError("heldout A/B group counts changed after binding")

    records = []
    transport_modes = {name: Counter() for name in reader_names}
    for index, (source, key) in enumerate(zip(sources, manifest)):
        per_reader: dict[str, Any] = {}
        for name in reader_names:
            prediction, transport_errors, mode = normalize_prediction(raw_readers[name][index], str(source["record_id"]))
            transport_modes[name][mode] += 1
            exact_record, exact_errors = (None, transport_errors)
            if not transport_errors and prediction is not None:
                exact_record, exact_errors = validate_and_expand(prediction, source)
            view, view_errors = semantic_view(prediction if not transport_errors else None)
            per_reader[name] = {
                "prediction": prediction,
                "exact_valid": exact_record is not None and not exact_errors,
                "exact_errors": exact_errors,
                "semantic_view": view,
                "semantic_shape_errors": view_errors,
                "transport_mode": mode,
            }
        left, right = (per_reader[name] for name in reader_names)
        disagreements: dict[str, Any] = {}
        if left["semantic_view"] is not None and right["semantic_view"] is not None:
            for metric in METRICS:
                values = {
                    obj: {reader_names[0]: left["semantic_view"][obj][metric], reader_names[1]: right["semantic_view"][obj][metric]}
                    for obj in OBJECT_ORDER
                    if left["semantic_view"][obj][metric] != right["semantic_view"][obj][metric]
                }
                if values:
                    disagreements[metric] = values
        else:
            disagreements["semantic_comparison"] = "unavailable_for_at_least_one_reader"
        records.append({
            "source_position_1based": index + 1,
            "review_id": str(source["record_id"]),
            "source_text_sha256": key["source_text_sha256"],
            "split": key["split"],
            "arm": key["arm"],
            "canonical_key": key.get("canonical_key"),
            "readers": per_reader,
            "disagreements": disagreements,
        })

    public_groups: dict[str, Any] = {}
    for group_name, indices in groups.items():
        agreement = {metric: empty_metric() for metric in METRICS}
        exact_validation = {}
        for name in reader_names:
            errors = [error for index in indices for error in records[index]["readers"][name]["exact_errors"]]
            valid = sum(records[index]["readers"][name]["exact_valid"] for index in indices)
            exact_validation[name] = {
                "records": len(indices),
                "valid": valid,
                "failed": len(indices) - valid,
                "error_category_counts": dict(sorted(Counter(public_error_category(error) for error in errors).items())),
            }
        for index in indices:
            left = records[index]["readers"][reader_names[0]]["semantic_view"]
            right = records[index]["readers"][reader_names[1]]["semantic_view"]
            for metric in METRICS:
                if left is None or right is None:
                    continue
                object_agreements = []
                for obj in OBJECT_ORDER:
                    same = left[obj][metric] == right[obj][metric]
                    agreement[metric]["by_object"][obj]["comparable"] += 1
                    agreement[metric]["by_object"][obj]["agree"] += int(same)
                    object_agreements.append(same)
                agreement[metric]["all_objects"]["comparable"] += 1
                agreement[metric]["all_objects"]["agree"] += int(all(object_agreements))
        public_groups[group_name] = {
            "records": len(indices),
            "exact_validator": exact_validation,
            "reader_agreement_counts": agreement,
        }

    public = {
        "status": "complete",
        "scope": "two-reader descriptive diagnostic agreement; not accuracy, a population rate, or technology-arm validation",
        "binding": {
            "source_records": EXPECTED_COUNT,
            "source_manifest_order_and_hash_match": True,
            "source_record_ids_unique": True,
            "source_exact_texts_unique": True,
            "reader_rows_each": EXPECTED_COUNT,
            "reader_order_sidecars_match_source_positions": True,
            "reader_transport_modes": {name: dict(sorted(counts.items())) for name, counts in transport_modes.items()},
        },
        "metric_definitions": {
            "object_state": "exact state equality for each economic object",
            "main_estimand_presence": "presence of at least one required, unconditional, prior_experience mention, compared separately by bound object",
            "label_signature": "multiset equality of strength, condition_mode, and qualification_scope tuples for mentions bound to each object",
            "duration_bound_signature": "multiset equality of label tuples plus duration kind/value(s), still bound to each object",
            "exact_validator": "strict source-quote and duration validation reported separately from semantic-label agreement",
        },
        "groups": public_groups,
        "input_sha256": {
            "source20": file_sha256(args.source),
            "private_unblind_manifest": file_sha256(args.unblind_manifest),
            "readers": {name: file_sha256(path) for name, path in reader_paths.items()},
            "reader_order_sidecars": {name: file_sha256(path) for name, path in order_paths.items()},
        },
        "privacy": "No source text, review ID, canonical key, or record-level result appears in this public aggregate.",
    }
    private_records = []
    for record in records:
        has_validation_failure = any(not record["readers"][name]["exact_valid"] for name in reader_names)
        if not record["disagreements"] and not has_validation_failure:
            continue
        private_records.append({
            "source_position_1based": record["source_position_1based"],
            "review_id": record["review_id"],
            "source_text_sha256": record["source_text_sha256"],
            "split": record["split"],
            "arm": record["arm"],
            "canonical_key": record["canonical_key"],
            "readers": {
                name: {
                    "exact_valid": record["readers"][name]["exact_valid"],
                    "exact_errors": record["readers"][name]["exact_errors"],
                    "semantic_shape_errors": record["readers"][name]["semantic_shape_errors"],
                    "semantic_view": record["readers"][name]["semantic_view"],
                }
                for name in reader_names
            },
            "disagreements": record["disagreements"],
        })
    private = {
        "status": "complete",
        "reader_names": reader_names,
        "records_with_disagreement_or_validation_failure": len(private_records),
        "records": private_records,
        "note": "Contains source identifiers and detailed validator errors, but no source text or raw model output.",
    }

    args.public_output.parent.mkdir(parents=True, exist_ok=True)
    args.private_output.parent.mkdir(parents=True, exist_ok=True)
    args.public_output.write_text(json.dumps(public, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    args.private_output.write_text(json.dumps(private, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(args.private_output, 0o600)
    print(json.dumps({"status": "complete", "public": str(args.public_output), "private": str(args.private_output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
