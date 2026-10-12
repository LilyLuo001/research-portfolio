#!/usr/bin/env python3
"""Validate Wave02 conversation reviews and emit a private additive overlay.

This performs identity/schema/evidence checks only. It never creates or fills a
semantic decision and does not aggregate research outcomes.
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

VERSION = "wave02-compact-review-validation-v1"
KEY_NAMES = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
EXP_DIMS = ("general_work", "occupation_task", "industry_domain", "tool_specific")
RESP_DIMS = ("independent_judgment", "client_ownership", "people_supervision", "training_mentoring")
QUESTION_MAP = {"experience": "experience_4dims", "entry_responsibility": "entry_responsibility_4dims"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def text_sha256(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if line.strip():
                try:
                    rows.append(json.loads(line))
                except Exception as exc:
                    raise RuntimeError("invalid JSONL {}:{}: {}".format(path, line_number, exc))
    return rows


def atomic_json(path, value, mode=None):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if mode is not None: os.chmod(str(temp), mode)
    os.replace(str(temp), str(path))


def atomic_jsonl(path, values, mode=None):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    with open(temp, "w", encoding="utf-8") as stream:
        for value in values:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    if mode is not None: os.chmod(str(temp), mode)
    os.replace(str(temp), str(path))


def packet_key(row):
    key = row.get("canonical_key")
    if not isinstance(key, list) or len(key) != 4:
        raise RuntimeError("packet canonical_key must be a four-item list")
    return tuple(key)


def review_key(row):
    key = row.get("canonical_key")
    if not isinstance(key, dict) or set(key) != set(KEY_NAMES):
        raise RuntimeError("review canonical_key must contain exactly the canonical four keys")
    return tuple(key[name] for name in KEY_NAMES)


def iter_spans(value):
    if isinstance(value, dict):
        if set(("start", "end", "quote")).issubset(value):
            yield value
        for child in value.values():
            for span in iter_spans(child): yield span
    elif isinstance(value, list):
        for child in value:
            for span in iter_spans(child): yield span


def lookup_frozen(packet, field):
    if field in packet.get("baseline_flags", {}): return packet["baseline_flags"][field]
    if field in packet.get("strength_summary", {}): return packet["strength_summary"][field]
    if field in packet: return packet[field]
    if field.startswith("baseline_flags."):
        return packet.get("baseline_flags", {})[field.split(".", 1)[1]]
    if field.startswith("strength_summary."):
        return packet.get("strength_summary", {})[field.split(".", 1)[1]]
    raise KeyError(field)


def validate_manual_shape(review):
    required = ("record_id", "canonical_key", "source_exact_text_sha256", "context_sha256", "question",
                "coverage_scope", "frozen_before", "decision", "reviewer")
    missing = [name for name in required if name not in review]
    if missing: raise RuntimeError("review missing fields: " + ",".join(missing))
    decision = review["decision"]
    if decision.get("question") != review["question"]: raise RuntimeError("top-level and decision questions differ")
    partial = review["coverage_scope"].get("level") == "partial_context"
    if review["question"] == "experience_4dims":
        outcomes = decision.get("dimension_outcomes", [])
        if [x.get("dimension") for x in outcomes] != list(EXP_DIMS):
            raise RuntimeError("experience dimension outcomes must be the exact four ordered dimensions")
        clauses = decision.get("clauses")
        if not isinstance(clauses, list): raise RuntimeError("experience clauses must be an array")
        for outcome in outcomes:
            presence = outcome.get("ad_level_presence")
            if presence not in ("present", "absent_after_exhaustive_review", "unknown"):
                raise RuntimeError("invalid experience presence")
            if partial and presence == "absent_after_exhaustive_review":
                raise RuntimeError("partial context cannot establish experience absence")
            if presence == "present":
                supporting = [x for x in clauses if x.get("resulting_dimension") == outcome["dimension"] and list(iter_spans(x))]
                if not supporting: raise RuntimeError("positive experience dimension lacks a matching evidenced clause")
    elif review["question"] == "entry_responsibility_4dims":
        entry = decision.get("entry", {})
        responsibilities = decision.get("responsibilities", [])
        if [x.get("dimension") for x in responsibilities] != list(RESP_DIMS):
            raise RuntimeError("responsibilities must be the exact four ordered dimensions")
        values = [entry] + responsibilities
        for item in values:
            presence = item.get("ad_level_presence")
            if presence not in ("present", "absent_after_exhaustive_review", "unknown"):
                raise RuntimeError("invalid entry/responsibility presence")
            if partial and presence == "absent_after_exhaustive_review":
                raise RuntimeError("partial context cannot establish entry/responsibility absence")
            if presence == "present" and not list(iter_spans(item)):
                raise RuntimeError("positive entry/responsibility outcome lacks evidence")
        if entry.get("ad_level_presence") == "present" and entry.get("target") in ("not_stated", "unresolved"):
            raise RuntimeError("positive entry outcome has no affirmative target")
        for item in responsibilities:
            if item.get("ad_level_presence") == "present" and item.get("subject") != "advertised_worker":
                raise RuntimeError("positive responsibility must concern the advertised worker")
            if item.get("relation") not in ("current_duty", "required_capability", "prior_experience", "other_person", "employer_description", "unresolved"):
                raise RuntimeError("invalid responsibility relation")
    else:
        raise RuntimeError("unknown review question")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--packet", required=True)
    parser.add_argument("--review-a", required=True)
    parser.add_argument("--review-b", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--private-overlay", required=True)
    parser.add_argument("--public-receipt", required=True)
    parser.add_argument("--expected-records", type=int, default=96)
    args = parser.parse_args()

    packet = read_jsonl(args.packet)
    if len(packet) != args.expected_records: raise RuntimeError("packet is not the exact selected record count")
    packet_by_id = {}; packet_by_match = {}; selection_indices = set()
    for row in packet:
        index = row.get("selection_index_1based")
        if not isinstance(index, int) or index in selection_indices: raise RuntimeError("invalid/duplicate packet selection index")
        selection_indices.add(index)
        if row.get("question_group") not in QUESTION_MAP: raise RuntimeError("invalid packet question group")
        key = packet_key(row); match = (key, QUESTION_MAP[row["question_group"]])
        if match in packet_by_match: raise RuntimeError("duplicate packet canonical-key/question")
        if row.get("full_text_verified") is not True: raise RuntimeError("Wave02 packet must bind verified full text")
        if text_sha256(row.get("review_text", "")) != row.get("normalized_text_sha256"):
            raise RuntimeError("packet normalized review-text SHA mismatch")
        if text_sha256(row.get("original_text", "")) != row.get("source_text_sha256"):
            raise RuntimeError("packet source exact-text SHA mismatch")
        packet_by_match[match] = row; packet_by_id[index] = row
    if selection_indices != set(range(1, args.expected_records + 1)):
        raise RuntimeError("packet selection indices must be exactly 1..expected")

    reviews = read_jsonl(args.review_a) + read_jsonl(args.review_b)
    if len(reviews) != args.expected_records: raise RuntimeError("A/B reviews do not cover exactly the selected packet")
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("jsonschema Draft202012Validator is required; manual fallback is not accepted") from exc
    schema = json.load(open(args.schema, encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    jsonschema_available = True

    seen_match = set(); record_ids = set(); overlay = []; counts = collections.Counter()
    for review in reviews:
        if validator is not None:
            errors = sorted(validator.iter_errors(review), key=lambda x: list(x.path))
            if errors: raise RuntimeError("schema failure {}: {}".format(review.get("record_id"), errors[0].message))
        validate_manual_shape(review)
        key = review_key(review); match = (key, review["question"])
        if match not in packet_by_match: raise RuntimeError("review is outside the selected 96")
        if match in seen_match: raise RuntimeError("duplicate reviewed canonical-key/question")
        seen_match.add(match)
        if review["record_id"] in record_ids: raise RuntimeError("duplicate review record_id")
        record_ids.add(review["record_id"]); source = packet_by_match[match]; text = source["review_text"]
        if review["source_exact_text_sha256"] != source["source_text_sha256"]:
            raise RuntimeError("source exact-text SHA mismatch")
        if review["context_sha256"] != text_sha256(text): raise RuntimeError("review context SHA mismatch")
        if review["question"] != QUESTION_MAP[source["question_group"]]: raise RuntimeError("review question mismatch")
        expected_record_id = "wave02-{:03d}".format(source["selection_index_1based"])
        if review["record_id"] != expected_record_id: raise RuntimeError("review record_id does not bind selection index")
        scope = review["coverage_scope"]
        if scope.get("level") != "full_document" or scope.get("exhaustiveness_certification") != "full_document":
            raise RuntimeError("this packet supplies verified full text; review must record full_document coverage")
        snapshots = review["frozen_before"]["field_snapshot"]
        expected_snapshot_fields = set(source.get("baseline_flags", {})) | set(
            "strength_summary." + name for name in source.get("strength_summary", {}))
        if set(x["field"] for x in snapshots) != expected_snapshot_fields or len(snapshots) != len(expected_snapshot_fields):
            raise RuntimeError("frozen-before snapshot field set is not exact")
        expected_evidence_indices = sorted(x["evidence_index"] for x in source.get("evidence", []))
        if sorted(review["frozen_before"]["candidate_evidence_indices_0based"]) != expected_evidence_indices:
            raise RuntimeError("frozen-before candidate evidence indices are not exact")
        for snap in snapshots:
            try: expected = lookup_frozen(source, snap["field"])
            except KeyError: raise RuntimeError("unknown frozen-before field: " + snap["field"])
            if snap["value"] != expected: raise RuntimeError("frozen-before value mismatch: " + snap["field"])
        for span in iter_spans(review["decision"]):
            start, end, quote = span["start"], span["end"], span["quote"]
            if not isinstance(start, int) or not isinstance(end, int) or start < 0 or end <= start or text[start:end] != quote:
                raise RuntimeError("evidence span does not exactly slice normalized full text")
        counts[(review["question"], review["decision"]["question_status"])] += 1
        overlay.append({
            "selection_index_1based": source["selection_index_1based"],
            "technology_arm": source["technology_arm"],
            "occupation_code": source["occupation_code"],
            "selection_stratum": source["selection_stratum"],
            "full69_fixed_min_count_weight": source["full69_fixed_min_count_weight"],
            **review
        })
    if seen_match != set(packet_by_match): raise RuntimeError("selected records missing from A/B reviews")
    overlay.sort(key=lambda x: x["selection_index_1based"])
    atomic_jsonl(args.private_overlay, overlay, mode=0o600)
    receipt = {
        "version": VERSION, "status": "pass", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "inputs": {"packet_sha256": sha256(args.packet), "review_a_sha256": sha256(args.review_a),
                   "review_b_sha256": sha256(args.review_b), "schema_sha256": sha256(args.schema)},
        "counts": {"selected_records": len(packet), "review_records": len(reviews),
                   "by_question_status": {"{}|{}".format(k[0], k[1]): v for k, v in sorted(counts.items())}},
        "checks": {"exact_selected_96_only": True, "canonical_key_and_question_unique": True,
                   "source_and_context_hashes_exact": True, "question_matches_packet": True,
                   "schema_validated": validator is not None, "manual_critical_checks": True,
                   "quote_offsets_exact": True, "exact_four_target_statuses": True,
                   "positive_requires_evidence": True, "partial_context_cannot_negate": True,
                   "no_missing_reviews_filled": True},
        "environment": {"jsonschema_available": jsonschema_available},
        "private_overlay": {"path": str(Path(args.private_overlay)), "rows": len(overlay),
                            "sha256": sha256(args.private_overlay)},
        "claim_boundary": "review validation and additive row overlay only; no population aggregation or automatic labels"
    }
    atomic_json(args.public_receipt, receipt)


if __name__ == "__main__":
    main()
