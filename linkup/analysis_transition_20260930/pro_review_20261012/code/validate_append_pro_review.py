#!/usr/bin/env python3
"""Validate bounded Pro-conversation reviews and build an additive overlay.

The scheduled job calls no model and never changes the frozen packet. It binds
each review to one packet record, validates the frozen JOINT schema and exact
Unicode quote offsets, preserves candidate labels, and writes private overlays
plus a sanitized public receipt. Root adjudication patches are deliberately not
merged by this batch validator.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import socket
from collections import Counter
from pathlib import Path

PACKET_SHA256 = "4c3121398c7a95d12f38461211215c00895640f883e9b46040c5b338c7175328"
PACKET_ROWS = 19
OVERLAY_VERSION = "pro-semantic-review-overlay-v1"
REVIEW_SCOPE = "five_core_dimensions_not_exhaustive_task_inventory"
EXPECTED_REVIEWER = {"model": "gpt-5.6-sol", "effort": "medium", "execution": "Pro_conversation"}
BINDING_FIELDS = ("selection_index_1based", "exact_text_sha256", "decision_group", "frozen_rule_version")
ASSERTED_ARRAYS = ("experience_requirements", "technology_roles", "task_responsibilities")


def sha_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception as exc:
                raise RuntimeError("invalid JSONL {}:{}: {}".format(path, line_number, exc))
            if not isinstance(row, dict):
                raise RuntimeError("JSONL row must be an object {}:{}".format(path, line_number))
            rows.append(row)
    return rows


def json_type_ok(value, expected):
    if expected == "null": return value is None
    if expected == "object": return isinstance(value, dict)
    if expected == "array": return isinstance(value, list)
    if expected == "string": return isinstance(value, str)
    if expected == "integer": return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number": return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean": return isinstance(value, bool)
    raise RuntimeError("unsupported schema type {}".format(expected))


def validate_schema(value, schema, pointer="$"):
    """Validate the JSON-schema subset used by frozen JOINT_SCHEMA.json."""
    expected = schema.get("type")
    if expected is not None:
        choices = expected if isinstance(expected, list) else [expected]
        if not any(json_type_ok(value, choice) for choice in choices):
            raise RuntimeError("{} has wrong type; expected {}".format(pointer, choices))
    if "enum" in schema and value not in schema["enum"]:
        raise RuntimeError("{} is outside frozen enum".format(pointer))
    if isinstance(value, dict):
        missing = [key for key in schema.get("required", []) if key not in value]
        if missing:
            raise RuntimeError("{} missing required fields {}".format(pointer, missing))
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(properties))
            if extra:
                raise RuntimeError("{} has unexpected fields {}".format(pointer, extra))
        for key, child in value.items():
            if key in properties:
                validate_schema(child, properties[key], pointer + "." + key)
    elif isinstance(value, list) and "items" in schema:
        for index, child in enumerate(value):
            validate_schema(child, schema["items"], "{}[{}]".format(pointer, index))


def collect_and_validate_spans(value, text, pointer="$.review"):
    spans = []
    if isinstance(value, dict):
        keys, present = {"start", "end", "quote"}, {"start", "end", "quote"} & set(value)
        if present:
            if present != keys:
                raise RuntimeError("{} has incomplete evidence span".format(pointer))
            start, end, quote = value["start"], value["end"], value["quote"]
            if not isinstance(start, int) or isinstance(start, bool) or not isinstance(end, int) or isinstance(end, bool):
                raise RuntimeError("{} offsets must be integers".format(pointer))
            if not isinstance(quote, str) or start < 0 or end <= start or end > len(text):
                raise RuntimeError("{} has invalid quote or offsets".format(pointer))
            if text[start:end] != quote:
                raise RuntimeError("{} quote/offset mismatch".format(pointer))
            spans.append((start, end, quote))
        for key, child in value.items():
            spans.extend(collect_and_validate_spans(child, text, pointer + "." + key))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            spans.extend(collect_and_validate_spans(child, text, "{}[{}]".format(pointer, index)))
    return spans


def require_asserted_evidence(review):
    for field in ASSERTED_ARRAYS:
        for index, item in enumerate(review[field]):
            if not item.get("evidence"):
                raise RuntimeError("$.review.{}[{}] asserted item has no evidence".format(field, index))
    for group_index, group in enumerate(review["qualification_alternatives"]):
        for branch_index, branch in enumerate(group["branches"]):
            if not branch.get("evidence"):
                raise RuntimeError("qualification group {} branch {} has no evidence".format(group_index, branch_index))
    if review["entry_target"] not in {"not_stated", "unresolved"} and not review["entry_evidence"]:
        raise RuntimeError("asserted entry_target has no entry_evidence")


def binding_key(row):
    return tuple(row.get(field) for field in BINDING_FIELDS)


def parse_number_set(value, name):
    result = {int(item) for item in value.split(",") if item.strip()}
    if not result:
        raise RuntimeError("{} is empty".format(name))
    return result


def write_private_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + ".tmp.{}".format(os.getpid()))
    with open(temporary, "w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    return path


def read_json(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("expected JSON object: {}".format(path))
    return value


def validate_lane_provenance(lane, first_path, revised_path, change_path):
    first_rows, revised_rows = read_jsonl(first_path), read_jsonl(revised_path)
    if len(first_rows) != 7 or len(revised_rows) != 7:
        raise RuntimeError("lane {} must contain exactly seven first/final rows".format(lane))
    first_by_selection = {row.get("selection_index_1based"): row for row in first_rows}
    revised_by_selection = {row.get("selection_index_1based"): row for row in revised_rows}
    if len(first_by_selection) != 7 or set(first_by_selection) != set(revised_by_selection):
        raise RuntimeError("lane {} first/final selection bindings differ".format(lane))
    for selection in first_by_selection:
        before, after = first_by_selection[selection], revised_by_selection[selection]
        for field in BINDING_FIELDS:
            if before.get(field) != after.get(field):
                raise RuntimeError("lane {} revision changed binding field {}".format(lane, field))
        if before.get("reviewer") != after.get("reviewer"):
            raise RuntimeError("lane {} revision changed reviewer provenance".format(lane))
        if before.get("review_scope") != after.get("review_scope"):
            raise RuntimeError("lane {} revision changed review scope".format(lane))

    first_sha, revised_sha, change_sha = sha_file(first_path), sha_file(revised_path), sha_file(change_path)
    change = read_json(change_path)
    if lane == "A":
        if (change.get("input") or {}).get("sha256") != first_sha:
            raise RuntimeError("lane A changefile/input SHA mismatch")
        if (change.get("output") or {}).get("sha256") != revised_sha:
            raise RuntimeError("lane A changefile/output SHA mismatch")
        if not (change.get("provenance") or {}).get("original_preserved"):
            raise RuntimeError("lane A original-preserved gate failed")
    elif lane == "B":
        if change.get("source_sha256") != first_sha or change.get("revised_sha256") != revised_sha:
            raise RuntimeError("lane B changefile source/revised SHA mismatch")
        if not change.get("original_preserved_immutable") or change.get("schema_or_parser_changed"):
            raise RuntimeError("lane B preservation/schema gate failed")
    else:
        raise RuntimeError("unknown lane")

    changed = set()
    for field in ("changes", "root_final_evidence_locator_corrections"):
        values = change.get(field) or []
        if not isinstance(values, list):
            raise RuntimeError("lane {} {} is not a list".format(lane, field))
        for item in values:
            if not isinstance(item, dict) or not isinstance(item.get("selection_index_1based"), int):
                raise RuntimeError("lane {} change entry lacks selection binding".format(lane))
            changed.add(item["selection_index_1based"])
    if not changed <= set(revised_by_selection):
        raise RuntimeError("lane {} changefile references another lane".format(lane))
    return {
        "lane": lane,
        "first_rows": first_rows,
        "revised_rows": revised_rows,
        "selection_numbers": set(revised_by_selection),
        "changed_selection_numbers": changed,
        "first_sha256": first_sha,
        "revised_sha256": revised_sha,
        "changefile_sha256": change_sha,
    }


def add_semantic_counts(counts, review):
    counts["document_status"][review["document_status"]] += 1
    counts["experience_nonmention_status"][review["experience_nonmention_status"]] += 1
    counts["entry_target"][review["entry_target"]] += 1
    for item in review["experience_requirements"]:
        counts["experience_object"][item["object"]] += 1
        counts["experience_strength"][item["strength"]] += 1
        counts["experience_years_relation"][item["years_relation"]] += 1
    for item in review["qualification_alternatives"]:
        counts["qualification_relation"][item["relation"]] += 1
    for item in review["technology_roles"]:
        counts["technology_family"][item["family"]] += 1
        counts["technology_role"][item["role"]] += 1
    for item in review["task_responsibilities"]:
        counts["task_dimension"][item["dimension"]] += 1
        counts["task_responsibility_status"][item["advertised_worker_responsibility"]] += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True)
    parser.add_argument("--reviews", required=True)
    parser.add_argument("--firstpass-a", required=True)
    parser.add_argument("--firstpass-b", required=True)
    parser.add_argument("--revised-a", required=True)
    parser.add_argument("--revised-b", required=True)
    parser.add_argument("--changes-a", required=True)
    parser.add_argument("--changes-b", required=True)
    parser.add_argument("--root-spotcheck", required=True)
    parser.add_argument("--root-acceptance", required=True)
    parser.add_argument("--review-schema", required=True)
    parser.add_argument("--output-overlay", required=True)
    parser.add_argument("--output-coverage", required=True)
    parser.add_argument("--private-summary", required=True)
    parser.add_argument("--public-receipt", required=True)
    parser.add_argument("--public-summary", required=True)
    parser.add_argument("--expected-selection-numbers", required=True)
    parser.add_argument("--previously-full-selection-numbers", required=True)
    parser.add_argument("--previously-partial-selection-numbers", required=True)
    args = parser.parse_args()

    packet_path, review_path, schema_path = Path(args.packet), Path(args.reviews), Path(args.review_schema)
    packet_sha = sha_file(packet_path)
    if packet_sha != PACKET_SHA256:
        raise RuntimeError("frozen DEV24 packet SHA mismatch")
    packet = read_jsonl(packet_path)
    if len(packet) != PACKET_ROWS:
        raise RuntimeError("frozen DEV24 packet row count mismatch")
    by_selection, packet_keys = {}, set()
    for source in packet:
        selection, key = source.get("selection_index_1based"), binding_key(source)
        if not isinstance(selection, int) or selection in by_selection or None in key or key in packet_keys:
            raise RuntimeError("packet binding is missing or non-unique")
        if not isinstance(source.get("review_text"), str) or source.get("review_text_coordinate_system") != "normalized_unicode_codepoints":
            raise RuntimeError("packet review-text coordinate contract mismatch")
        by_selection[selection], packet_keys = source, packet_keys | {key}

    expected = parse_number_set(args.expected_selection_numbers, "expected selection set")
    previous_full = parse_number_set(args.previously_full_selection_numbers, "previous full set")
    previous_partial = parse_number_set(args.previously_partial_selection_numbers, "previous partial set")
    if expected & previous_full or expected & previous_partial or previous_full & previous_partial:
        raise RuntimeError("review-scope selection sets overlap")
    if expected | previous_full | previous_partial != set(by_selection):
        raise RuntimeError("review-scope sets do not cover frozen packet")

    lane_a = validate_lane_provenance("A", args.firstpass_a, args.revised_a, args.changes_a)
    lane_b = validate_lane_provenance("B", args.firstpass_b, args.revised_b, args.changes_b)
    if lane_a["selection_numbers"] & lane_b["selection_numbers"]:
        raise RuntimeError("A/B revised lanes overlap")
    acceptance = read_json(args.root_acceptance)
    if acceptance.get("status") != "accepted_for_bounded_overlay_not_population_certification":
        raise RuntimeError("root acceptance status is not approved")
    if acceptance.get("expected_records") != 14 or acceptance.get("reviewer_model") != "gpt-5.6-sol":
        raise RuntimeError("root acceptance count/model mismatch")
    if acceptance.get("reviewer_effort") != "medium" or acceptance.get("root_spotcheck_records") != 4:
        raise RuntimeError("root acceptance effort/spotcheck mismatch")
    if acceptance.get("schemas_unchanged") is not True or acceptance.get("originals_preserved") is not True:
        raise RuntimeError("root acceptance preservation gate failed")
    spotcheck = read_json(args.root_spotcheck)
    if not isinstance(spotcheck.get("documents"), list) or len(spotcheck["documents"]) != 4:
        raise RuntimeError("root private spotcheck count mismatch")
    acceptance_sha, spotcheck_sha = sha_file(args.root_acceptance), sha_file(args.root_spotcheck)

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    reviews = read_jsonl(review_path)
    revised_rows = lane_a["revised_rows"] + lane_b["revised_rows"]
    if reviews != revised_rows:
        raise RuntimeError("combined final review file is not exact A-then-B revised concatenation")
    if len(reviews) != len(expected):
        raise RuntimeError("review count does not match expected bounded set")
    if lane_a["selection_numbers"] | lane_b["selection_numbers"] != expected:
        raise RuntimeError("A/B revised lanes do not equal expected selection set")
    lane_by_selection = {selection: lane_a for selection in lane_a["selection_numbers"]}
    lane_by_selection.update({selection: lane_b for selection in lane_b["selection_numbers"]})
    allowed_fields = set(BINDING_FIELDS) | {"reviewer", "review_scope", "review", "candidate_resolutions", "root_attention"}
    new_rows, reviewed = [], set()
    status_counts, disposition_counts = Counter(), Counter()
    semantic_counts = {name: Counter() for name in (
        "document_status", "experience_nonmention_status", "entry_target", "experience_object",
        "experience_strength", "experience_years_relation", "qualification_relation",
        "technology_family", "technology_role", "task_dimension", "task_responsibility_status",
    )}
    span_count = root_attention_count = 0
    for record in reviews:
        extra, missing = sorted(set(record) - allowed_fields), sorted(allowed_fields - set(record))
        if extra or missing:
            raise RuntimeError("review wrapper mismatch; extra={} missing={}".format(extra, missing))
        selection = record["selection_index_1based"]
        if selection not in expected or selection in reviewed:
            raise RuntimeError("review selection is unexpected or duplicate")
        source = by_selection[selection]
        for field in BINDING_FIELDS:
            if record[field] != source[field]:
                raise RuntimeError("review/source binding mismatch: selection {} {}".format(selection, field))
        if record["reviewer"] != EXPECTED_REVIEWER or record["review_scope"] != REVIEW_SCOPE:
            raise RuntimeError("review provenance or scope does not match locked contract")

        review = record["review"]
        validate_schema(review, schema)
        require_asserted_evidence(review)
        spans = collect_and_validate_spans(review, source["review_text"])
        span_count += len(spans)
        status_counts[review["document_status"]] += 1
        add_semantic_counts(semantic_counts, review)

        resolutions = record["candidate_resolutions"]
        if not isinstance(resolutions, list):
            raise RuntimeError("candidate_resolutions must be a list")
        resolution_indices = set()
        for resolution in resolutions:
            if not isinstance(resolution, dict) or set(resolution) != {"frozen_evidence_index_0based", "disposition", "reason"}:
                raise RuntimeError("candidate resolution shape mismatch")
            evidence_index = resolution["frozen_evidence_index_0based"]
            if not isinstance(evidence_index, int) or isinstance(evidence_index, bool):
                raise RuntimeError("candidate resolution index must be an integer")
            if evidence_index < 0 or evidence_index >= len(source.get("frozen_evidence") or []) or evidence_index in resolution_indices:
                raise RuntimeError("candidate resolution index invalid or duplicate")
            resolution_indices.add(evidence_index)
            if resolution["disposition"] not in {"confirmed", "corrected", "unresolved"}:
                raise RuntimeError("candidate resolution disposition outside locked enum")
            if not isinstance(resolution["reason"], str) or not resolution["reason"].strip():
                raise RuntimeError("candidate resolution reason is empty")
            disposition_counts[resolution["disposition"]] += 1
        attention = record["root_attention"]
        if not isinstance(attention, list) or not all(isinstance(item, str) and item.strip() for item in attention):
            raise RuntimeError("root_attention must be a list of nonempty strings")
        root_attention_count += len(attention)

        binding = {field: source[field] for field in BINDING_FIELDS}
        lane = lane_by_selection[selection]
        new_rows.append({
            "schema_version": OVERLAY_VERSION,
            "binding": binding,
            "source_identity": {"packet_sha256": packet_sha, "review_text_coordinate_system": source["review_text_coordinate_system"]},
            "review_status": "reviewed_in_pro_batch01",
            "review_scope": REVIEW_SCOPE,
            "propagation_status": "not_propagated_beyond_exact_bound_record",
            "frozen_candidate_snapshot": {
                "all_matched_groups": source.get("all_matched_groups") or [],
                "frozen_experience_status": source.get("frozen_experience_status"),
                "frozen_review_reasons": source.get("frozen_review_reasons") or [],
                "frozen_flags": source.get("frozen_flags") or {},
                "frozen_evidence": source.get("frozen_evidence") or [],
            },
            "reviewer": record["reviewer"],
            "semantic_review": review,
            "candidate_resolutions": resolutions,
            "root_attention": attention,
            "root_adjudication": {
                "status": "root-directed revisions accepted",
                "record_change_present": selection in lane["changed_selection_numbers"],
                "changefile_sha256": lane["changefile_sha256"],
                "acceptance_sha256": acceptance_sha,
                "independent_spotcheck_sha256": spotcheck_sha,
                "patch_merge_status": "accepted_revised_record_used; no separate nested patch applied",
            },
            "validation": {
                "exact_source_binding": True,
                "frozen_joint_schema": True,
                "evidence_quote_offsets_exact": True,
                "evidence_span_count": len(spans),
                "asserted_items_have_evidence": True,
            },
        })
        reviewed.add(selection)
    if reviewed != expected or len({binding_key(row["binding"]) for row in new_rows}) != len(new_rows):
        raise RuntimeError("review set incomplete or output binding duplicate")
    new_rows.sort(key=lambda row: row["binding"]["selection_index_1based"])
    output_path = write_private_jsonl(args.output_overlay, new_rows)

    coverage_rows = []
    for selection in sorted(by_selection):
        source = by_selection[selection]
        status = ("reviewed_in_pro_batch01" if selection in expected else
                  "excluded_previously_fully_reviewed" if selection in previous_full else
                  "excluded_previously_partially_reviewed")
        coverage_rows.append({
            "schema_version": "pro-semantic-review-coverage-v1",
            "binding": {field: source[field] for field in BINDING_FIELDS},
            "batch_status": status,
            "overlay_row_present": selection in expected,
            "review_scope": REVIEW_SCOPE if selection in expected else None,
        })
    coverage_path = write_private_jsonl(args.output_coverage, coverage_rows)

    private_summary = {
        "schema_version": "pro-semantic-review-private-summary-v1",
        "packet_sha256": packet_sha,
        "review_input_sha256": sha_file(review_path),
        "root_acceptance_sha256": acceptance_sha,
        "root_independent_spotcheck_sha256": spotcheck_sha,
        "version_trace": {
            "A": {key: lane_a[key] for key in ("first_sha256", "revised_sha256", "changefile_sha256")},
            "B": {key: lane_b[key] for key in ("first_sha256", "revised_sha256", "changefile_sha256")},
        },
        "reviewed_selection_numbers": sorted(reviewed),
        "previously_fully_reviewed_selection_numbers": sorted(previous_full),
        "previously_partially_reviewed_selection_numbers": sorted(previous_partial),
        "review_scope": REVIEW_SCOPE,
        "reviewer": EXPECTED_REVIEWER,
        "document_status_counts": dict(sorted(status_counts.items())),
        "candidate_disposition_counts": dict(sorted(disposition_counts.items())),
        "evidence_spans_validated": span_count,
        "root_attention_items": root_attention_count,
        "root_adjudication_status": "root-directed revisions accepted; revised records used",
        "propagation_status": "not_propagated_to_69_shards_or_full_corpus",
    }
    private_summary_path = Path(args.private_summary)
    private_summary_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    private_summary_path.write_text(json.dumps(private_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(private_summary_path, 0o600)

    receipt = {
        "schema_version": "pro-semantic-review-validation-receipt-v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "pass",
        "scheduler": {"job_id": os.environ.get("SLURM_JOB_ID"), "host": socket.gethostname()},
        "method": "bounded Pro conversation semantic decisions validated and assembled by scheduled code",
        "reviewer": EXPECTED_REVIEWER,
        "review_scope": REVIEW_SCOPE,
        "inputs": {
            "packet": {"sha256": packet_sha, "rows": len(packet)},
            "reviews_combined_final": {"sha256": sha_file(review_path), "rows": len(reviews)},
            "review_schema": {"sha256": sha_file(schema_path)},
            "root_acceptance": {"sha256": acceptance_sha, "status": acceptance["status"]},
            "root_independent_spotcheck": {"sha256": spotcheck_sha, "rows": 4},
            "lane_A": {key: lane_a[key] for key in ("first_sha256", "revised_sha256", "changefile_sha256")},
            "lane_B": {key: lane_b[key] for key in ("first_sha256", "revised_sha256", "changefile_sha256")},
        },
        "checks": {"exact_source_binding": True, "expected_selection_set_exact": True, "frozen_joint_schema": True, "unicode_quote_offsets_exact": True, "asserted_items_have_evidence": True, "candidate_resolution_indices_in_range": True, "old_candidate_labels_preserved": True},
        "reviewed_rows": len(reviews),
        "overlay_rows": len(new_rows),
        "packet_rows_not_reviewed_in_this_batch": len(packet) - len(new_rows),
        "evidence_spans_validated": span_count,
        "document_status_counts": dict(sorted(status_counts.items())),
        "candidate_disposition_counts": dict(sorted(disposition_counts.items())),
        "semantic_label_counts": {name: dict(sorted(values.items())) for name, values in sorted(semantic_counts.items())},
        "root_attention_items": root_attention_count,
        "output_overlay": {"rows": len(new_rows), "bytes": output_path.stat().st_size, "sha256": sha_file(output_path)},
        "output_coverage": {"rows": len(coverage_rows), "bytes": coverage_path.stat().st_size, "sha256": sha_file(coverage_path)},
        "compute_model_calls": 0,
        "limits": ["conversation-model reviews are not human gold labels", "development-selected records are not a population accuracy sample", "the overlay is additive and does not rewrite frozen candidate labels", "no review is propagated to the 69-shard or full-corpus population", "one reviewed development advertisement explicitly targets Canada and is not a US research observation", "first-pass outputs required root-directed corrections; revised outputs are used"],
    }
    receipt_path = Path(args.public_receipt)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    public_summary = {
        "schema_version": "pro-semantic-review-batch01-summary-v1",
        "status": acceptance["status"],
        "method": receipt["method"],
        "reviewed_records": len(reviews),
        "root_spotcheck_records": 4,
        "evidence_spans_validated": span_count,
        "candidate_disposition_counts": receipt["candidate_disposition_counts"],
        "semantic_label_counts": receipt["semantic_label_counts"],
        "root_attention_items": root_attention_count,
        "interpretation": "aggregate counts from actual bounded Pro reviews after root-directed revisions; not accuracy or population prevalence",
        "propagation_status": "not_propagated_to_69_shards_or_full_corpus",
    }
    summary_path = Path(args.public_summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(public_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "pass", "reviewed_rows": len(reviews), "overlay_rows": len(new_rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
