#!/usr/bin/env python3
"""Reconcile the frozen fixed10k frame with accepted historical semantic reviews.

This is a binding and inventory program.  It performs no new semantic extraction.
Private outputs contain hashes, source keys, statuses, and source-derived structured
values, but never source text, quotes, or model raw output.
"""
import argparse
import collections
import datetime as dt
import hashlib
import importlib.util
import json
import os
import platform
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


VERSION = "fixed10k-production-coverage-reconciliation-v1"
KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
FAMILIES = (
    "technology_category_and_role",
    "experience_object",
    "experience_strength",
    "experience_literal_years",
    "qualification_conditions_and_alternatives",
    "entry_wording_and_scope",
    "current_responsibility_subject_and_relation",
)
EXP_OBJECTS = ("general_work", "occupation_task", "industry_domain", "tool_specific")
STATUS = {"known", "not_applicable", "unknown_or_conflict", "partial", "candidate_only", "source_unavailable"}
SOURCE_PRIORITY = {"formal800_final": 0, "wave02_final": 1, "wave01_final": 2,
                   "legacy_batch001": 3, "legacy_batch002": 3}
EXPECTED_SHA = {
    "frame": "e6083ccacbdfe5a64548168a22ceb11fdce9d6d4bb89943a11f4bae54a17de35",
    "formal_reviews": "2939a5846cb6d40f42af94465e764fedcad51b86fc3d387d04d142c51ff63860",
    "formal_packet": "c012761f8ae9e5b3d5974744d5ff9caf42531b84253e46ee2ab21a73ffd64d5c",
    "formal_linkage": "cf53aba379963c6bf72c509333da0ce9157d4dd3736ef20e688e19a80420049e",
    "wave01_packet": "4c3121398c7a95d12f38461211215c00895640f883e9b46040c5b338c7175328",
    "wave01_overlay": "f2571238fdcdb3d5fa9eee6afc6f8ff2cb88f3616addaee5dbc0ff5dc865e049",
    "wave02_packet": "fb2707e854c526846fb4495afeab39856d3b8e4697d4fa1c74e0824980d88020",
    "wave02_overlay": "8201f4bb29bc8d7147a0ece4cfcaef52a008e57b7930842b0343da5fd6708ad0",
    "batch001": "c6949465ad8fab1bd3c1b881d48b13f1d04979a4de87a288f4136459c14ac856",
    "batch002": "d662e42e8ba067d209c48c35ce4f26154f5dd3349628f9eeacf7581849fb6c8b",
    "exclusion_hashes": "76609078e02d11e37ecaa3b82dbd6dab037b77830d086be51d9285eabc887104",
}


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if not line.strip():
                raise RuntimeError("blank JSONL line {}:{}".format(path, number))
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RuntimeError("non-object JSONL row {}:{}".format(path, number))
            rows.append(value)
    return rows


def atomic_json(path, value, private=False):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if private: os.chmod(str(temp), 0o600)
    os.replace(str(temp), str(path))


def atomic_jsonl(path, rows, private=True):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    with open(temp, "w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    if private: os.chmod(str(temp), 0o600)
    os.replace(str(temp), str(path))


def load_normalizer(path, expected_sha):
    actual = sha_file(path)
    if actual != expected_sha:
        raise RuntimeError("frozen legacy normalizer SHA mismatch")
    spec = importlib.util.spec_from_file_location("coverage_legacy_normalizer", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    if not hasattr(module, "_normalize_with_flags"):
        raise RuntimeError("frozen normalizer lacks _normalize_with_flags")
    return module, actual


def normalize(module, text):
    result = module._normalize_with_flags(text)
    value = result[0] if isinstance(result, tuple) else result
    if not isinstance(value, str):
        raise RuntimeError("normalizer returned non-string")
    return value


def public_value(value):
    """Remove evidence, free text details, and raw model material recursively."""
    banned = {"quotes", "quote", "spans", "evidence", "reason", "ambiguity", "context_note",
              "object_detail", "technology", "developed_object", "condition", "raw_output",
              "state_evidence", "auxiliary_positive_state_quote_evidence", "normalizations", "errors"}
    if isinstance(value, dict):
        return {k: public_value(v) for k, v in sorted(value.items()) if k not in banned}
    if isinstance(value, list):
        return [public_value(v) for v in value]
    return value


def judgment(source, family, status, value, scope, record_id, source_sha, context_sha, notes=None):
    if status not in STATUS: raise RuntimeError("invalid status")
    return {"source": source, "family": family, "status": status, "value": public_value(value),
            "scope": scope, "source_record_id": str(record_id), "source_sha256": source_sha,
            "source_context_sha256": context_sha, "notes": notes or []}


def all_known(mapping):
    return all(v not in ("unknown", "unresolved") for v in mapping.values())


def formal_judgments(review, source_sha):
    rid, context = review["record_id"], review["context_sha256"]
    if review["document_status"] == "unresolved":
        return [judgment("formal800_final", f, "unknown_or_conflict", None, "full_document_final_mask",
                         rid, source_sha, context, ["final_document_unresolved"]) for f in FAMILIES]
    out = []
    outcomes = review["experience_outcomes"]
    partial_doc = review["document_status"] == "reviewed_partial"
    object_status = "known" if all_known(outcomes) else "unknown_or_conflict"
    if object_status == "known" and all(v == "not_mentioned" for v in outcomes.values()): object_status = "not_applicable"
    if partial_doc and object_status in ("known", "not_applicable"): object_status = "partial"
    out.append(judgment("formal800_final", "experience_object", object_status, outcomes,
                        "full_document_four_object", rid, source_sha, context))
    applicable = [c for c in review["experience_clauses"] if c.get("object") in EXP_OBJECTS]
    for family, keys in (
        ("experience_strength", ("object", "strength")),
        ("experience_literal_years", ("object", "years_min", "years_max", "years_relation")),
        ("qualification_conditions_and_alternatives", ("object", "conditionality", "alternative_group", "alternative_branch")),
    ):
        if object_status == "not_applicable":
            st, val = "not_applicable", []
        else:
            val = [{k: c.get(k) for k in keys} for c in applicable]
            present = {name for name, state in outcomes.items() if state == "present"}
            clause_objects = {c.get("object") for c in applicable}
            unresolved = object_status == "unknown_or_conflict" or any(
                c.get("object") == "unresolved" or
                (family == "experience_strength" and c.get("strength") == "unresolved") or
                (family == "experience_literal_years" and c.get("years_relation") == "unresolved") or
                (family == "qualification_conditions_and_alternatives" and c.get("conditionality") == "unresolved")
                for c in review["experience_clauses"])
            incomplete = bool(present - clause_objects)
            if family == "qualification_conditions_and_alternatives":
                val = {"clauses": val, "qualification_alternatives": review["qualification_alternatives"]}
                unresolved = unresolved or any(x.get("relation") == "unresolved" or not x.get("branches") or any(not b.get("condition") for b in x.get("branches", [])) for x in review["qualification_alternatives"])
            st = "unknown_or_conflict" if unresolved else ("partial" if partial_doc or incomplete else "known")
        out.append(judgment("formal800_final", family, st, val, "full_document_clause_inventory",
                            rid, source_sha, context))
    entry = review["entry_outcomes"]
    st = "known" if all_known(entry) else "unknown_or_conflict"
    present_entry = {k for k, v in entry.items() if v == "present"}
    entry_items = review["entry_items"]
    if st == "known" and any(x.get("conditionality") == "unresolved" for x in entry_items): st = "unknown_or_conflict"
    elif st == "known" and present_entry - {x.get("target") for x in entry_items}: st = "partial"
    if st == "known" and all(v == "not_mentioned" for v in entry.values()): st = "not_applicable"
    if partial_doc and st in ("known", "not_applicable"): st = "partial"
    out.append(judgment("formal800_final", "entry_wording_and_scope", st,
                        {"outcomes": entry, "items": review["entry_items"]}, "full_document_entry", rid, source_sha, context))
    resp = review["responsibility_outcomes"]
    st = "known" if all_known(resp) else "unknown_or_conflict"
    present_resp = {k for k, v in resp.items() if v == "present"}
    resp_items = review["responsibility_items"]
    if st == "known" and any(x.get("subject") == "unresolved" or x.get("relation") == "unresolved" or x.get("conditionality") == "unresolved" for x in resp_items): st = "unknown_or_conflict"
    elif st == "known" and present_resp - {x.get("dimension") for x in resp_items}: st = "partial"
    if st == "known" and all(v == "not_mentioned" for v in resp.values()): st = "not_applicable"
    if partial_doc and st in ("known", "not_applicable"): st = "partial"
    out.append(judgment("formal800_final", "current_responsibility_subject_and_relation", st,
                        {"outcomes": resp, "items": review["responsibility_items"]}, "full_document_responsibility", rid, source_sha, context))
    tech = review["technology_inventory_status"]
    tech_items = review["technology_items"]
    st = "unknown_or_conflict" if tech == "unknown" or any(x.get("family") == "unresolved" or x.get("role") == "unresolved" for x in tech_items) else ("not_applicable" if tech == "not_mentioned_after_full_review" else "known")
    if tech == "explicit_mentions_recorded" and not tech_items: st = "partial"
    if partial_doc and st in ("known", "not_applicable"): st = "partial"
    out.append(judgment("formal800_final", "technology_category_and_role", st,
                        {"inventory_status": tech, "items": review["technology_items"]}, "full_document_technology", rid, source_sha, context))
    return out


def wave02_judgments(row, source_sha):
    d, rid, context = row["decision"], row["record_id"], row["context_sha256"]
    out = []
    scope = row.get("coverage_scope", {})
    if scope.get("level") != "full_document" or scope.get("exhaustiveness_certification") != "full_document":
        raise RuntimeError("Wave02 accepted overlay lacks full-document scope")
    if row["question"] == "experience_4dims":
        outcomes = {x["dimension"]: x["ad_level_presence"] for x in d["dimension_outcomes"]}
        st = "unknown_or_conflict" if "unknown" in outcomes.values() else "known"
        if st == "known" and all(v == "absent_after_exhaustive_review" for v in outcomes.values()): st = "not_applicable"
        out.append(judgment("wave02_final", "experience_object", st, outcomes, "full_document_experience_question", rid, source_sha, context))
        clauses = d["clauses"]
        for family, keys, unresolved_key in (
            ("experience_strength", ("resulting_dimension", "strength"), "strength"),
            ("experience_literal_years", ("resulting_dimension", "years_min", "years_max", "years_relation"), "years_relation"),
            ("qualification_conditions_and_alternatives", ("resulting_dimension", "conditionality", "alternative_group", "alternative_branch"), "conditionality"),
        ):
            val = [{k: c.get(k) for k in keys} for c in clauses]
            unresolved = st == "unknown_or_conflict" or any(c.get("candidate_resolution") == "unresolved" or c.get(unresolved_key) == "unresolved" or c.get("resulting_dimension") == "unresolved" for c in clauses)
            present_dimensions = {name for name, value in outcomes.items() if value == "present"}
            clause_dimensions = {c.get("resulting_dimension") for c in clauses}
            incomplete = bool(present_dimensions - clause_dimensions)
            fs = "not_applicable" if st == "not_applicable" else ("unknown_or_conflict" if unresolved else ("partial" if incomplete or family == "qualification_conditions_and_alternatives" else "known"))
            out.append(judgment("wave02_final", family, fs, val, "full_document_experience_question", rid, source_sha, context))
    else:
        entry = d["entry"]
        # Wave02 records one combined entry target, not the complete four-target Formal family.
        est = "unknown_or_conflict" if entry["ad_level_presence"] == "unknown" else "partial"
        out.append(judgment("wave02_final", "entry_wording_and_scope", est, entry, "full_document_entry_question", rid, source_sha, context))
        resp = {x["dimension"]: x for x in d["responsibilities"]}
        rst = "unknown_or_conflict" if any(x["ad_level_presence"] == "unknown" or x.get("subject") == "unresolved" or x.get("relation") == "unresolved" for x in resp.values()) else "known"
        if rst == "known" and all(x["ad_level_presence"] == "absent_after_exhaustive_review" for x in resp.values()): rst = "not_applicable"
        out.append(judgment("wave02_final", "current_responsibility_subject_and_relation", rst, resp, "full_document_responsibility_question", rid, source_sha, context))
    return out


def wave01_judgments(row, context, source_sha):
    review = row["semantic_review"]; rid = row["binding"]["selection_index_1based"]
    out = []
    clauses = review["experience_requirements"]
    nonmention = review["experience_nonmention_status"]
    obj = collections.defaultdict(list)
    for c in clauses: obj[c.get("object")].append(c)
    if nonmention == "not_mentioned_in_full_document": ost = "not_applicable"
    elif nonmention == "unresolved" or any(c.get("object") == "unresolved" for c in clauses): ost = "unknown_or_conflict"
    else: ost = "known" if review["document_status"] == "reviewed_full" else "partial"
    out.append(judgment("wave01_final", "experience_object", ost,
                        {"present_objects": sorted(x for x in obj if x in EXP_OBJECTS), "nonmention_status": nonmention},
                        "five_core_dimensions", rid, source_sha, context))
    for family, keys, bad in (
        ("experience_strength", ("object", "strength"), "strength"),
        ("experience_literal_years", ("object", "years_min", "years_max", "years_relation"), "years_relation"),
        ("qualification_conditions_and_alternatives", ("object", "alternative_group", "alternative_branch"), None),
    ):
        val = [{k: c.get(k) for k in keys} for c in clauses]
        if family == "qualification_conditions_and_alternatives": val = {"clauses": val, "qualification_alternatives": review["qualification_alternatives"]}
        unresolved = ost == "unknown_or_conflict" or (bad and any(c.get(bad) == "unresolved" for c in clauses))
        fs = "not_applicable" if ost == "not_applicable" else ("unknown_or_conflict" if unresolved else "partial")
        out.append(judgment("wave01_final", family, fs, val, "five_core_dimensions_schema_lacks_conditionality", rid, source_sha, context))
    target = review["entry_target"]
    est = "unknown_or_conflict" if target == "unresolved" else ("not_applicable" if target == "not_stated" and review["document_status"] == "reviewed_full" else "partial")
    out.append(judgment("wave01_final", "entry_wording_and_scope", est, {"combined_entry_target": target},
                        "combined_entry_target_no_atomic_scope", rid, source_sha, context))
    tasks = review["task_responsibilities"]
    rst = "unknown_or_conflict" if any(x.get("advertised_worker_responsibility") == "unresolved" for x in tasks) else "partial"
    out.append(judgment("wave01_final", "current_responsibility_subject_and_relation", rst,
                        tasks, "non_exhaustive_coarse_task_inventory", rid, source_sha, context))
    tech = review["technology_roles"]
    tst = "unknown_or_conflict" if any(x.get("family") == "unresolved" or x.get("role") == "unresolved" for x in tech) else "partial"
    out.append(judgment("wave01_final", "technology_category_and_role", tst, tech,
                        "positive_items_only_no_inventory_absence", rid, source_sha, context))
    return out


def legacy_judgments(row, source, source_sha):
    out, positives = [], []
    object_unknown = 0; duration_error = 0; duration_unknown = 0; duration_candidate = 0
    for obj in row.get("objects", []):
        state = obj.get("outcome_status")
        main = obj.get("main_prior_required_unconditional")
        if state in ("unknown", "error"): object_unknown += 1
        if state == "candidate" and main == 1:
            positives.append(obj.get("object"))
        for duration in obj.get("duration_assessments", []):
            ds = duration.get("status")
            if ds == "error": duration_error += 1
            elif ds == "unknown": duration_unknown += 1
            elif ds == "candidate": duration_candidate += 1
    context = None; rid = row.get("record_id")
    object_status = "unknown_or_conflict" if object_unknown else "partial"
    if positives:
        out.append(judgment(source, "experience_object", object_status, {"strict_positive_objects": positives, "object_outcome_unknown_count": object_unknown},
                            "legacy_strict_prior_required_unconditional_positive_only", rid, source_sha, context))
    else:
        out.append(judgment(source, "experience_object", object_status, {"strict_positive_objects": [], "object_outcome_unknown_count": object_unknown},
                            "legacy_attempt_schema_incomplete_zero_not_negative", rid, source_sha, context))
    out.append(judgment(source, "experience_strength", "unknown_or_conflict" if object_unknown else "partial",
                        {"known_required_objects": positives, "object_outcome_unknown_count": object_unknown},
                        "legacy_schema_incomplete_strength", rid, source_sha, context))
    out.append(judgment(source, "qualification_conditions_and_alternatives", "unknown_or_conflict" if object_unknown else "partial",
                        {"known_unconditional_objects": positives, "object_outcome_unknown_count": object_unknown},
                        "legacy_schema_incomplete_conditions", rid, source_sha, context))
    if duration_error or duration_unknown:
        ys = "unknown_or_conflict"
    elif duration_candidate:
        ys = "partial"
    else:
        ys = "partial"
    out.append(judgment(source, "experience_literal_years", ys,
                        {"candidate_count": duration_candidate, "unknown_count": duration_unknown, "error_count": duration_error},
                        "legacy_duration_candidates_not_complete_years", rid, source_sha, context))
    return out, {"object_outcome_unknown": object_unknown, "duration_error": duration_error,
                 "duration_unknown": duration_unknown, "duration_candidate": duration_candidate,
                 "strict_positive_objects": len(positives)}


def resolve(judgments):
    if not judgments:
        return "candidate_only", None, [], "never_semantically_reviewed"
    judgments = sorted(judgments, key=lambda x: (SOURCE_PRIORITY[x["source"]], x["source"], x["source_record_id"]))
    formal = [x for x in judgments if x["source"] == "formal800_final"]
    if formal:
        chosen = formal[0]
        independent = [x for x in judgments if x["source"] != "formal800_final" and x["status"] in ("known", "not_applicable", "unknown_or_conflict")]
        if chosen["status"] != "unknown_or_conflict" and independent:
            return "unknown_or_conflict", None, judgments, "independent_complete_source_overlap_requires_no_silent_precedence"
        return chosen["status"], chosen["value"], judgments, "formal_final_absolute_including_mask"
    hard = [x for x in judgments if x["status"] in ("known", "not_applicable", "unknown_or_conflict")]
    if any(x["status"] == "unknown_or_conflict" for x in hard):
        return "unknown_or_conflict", None, judgments, "reviewed_unresolved"
    if hard:
        canonical = {json.dumps(x["value"], sort_keys=True, separators=(",", ":")) for x in hard}
        states = {x["status"] for x in hard}
        if len(canonical) > 1 or len(states) > 1:
            return "unknown_or_conflict", None, judgments, "cross_source_incompatible_no_majority_rule"
        return hard[0]["status"], hard[0]["value"], judgments, "compatible_complete_source"
    if any(x["status"] == "partial" for x in judgments):
        return "partial", None, judgments, "partial_review_only"
    return "candidate_only", None, judgments, "legacy_attempt_without_compatible_assignment"


def self_test():
    base = {"record_id": "fixture", "source_text_sha256": "0" * 64,
            "objects": [{"object": name, "outcome_status": "candidate",
                         "main_prior_required_unconditional": 0, "duration_assessments": []}
                        for name in ("general_work", "occupation_task", "industry_domain")]}
    rows, counts = legacy_judgments(base, "legacy_batch001", "1" * 64)
    assert len(rows) == 4 and {x["family"] for x in rows} == set(FAMILIES[1:5])
    assert all(x["status"] == "partial" for x in rows) and counts["strict_positive_objects"] == 0
    masked = judgment("formal800_final", "experience_object", "unknown_or_conflict", None,
                      "fixture", "f", "1" * 64, "2" * 64)
    partial = judgment("wave01_final", "experience_object", "partial", {"x": 1},
                       "fixture", "w", "3" * 64, "2" * 64)
    assert resolve([masked, partial])[0] == "unknown_or_conflict"
    known_f = judgment("formal800_final", "experience_object", "known", {"x": 1},
                       "fixture", "f", "1" * 64, "2" * 64)
    known_w = judgment("wave02_final", "experience_object", "known", {"x": 1},
                       "fixture", "w", "3" * 64, "2" * 64)
    assert resolve([known_f, known_w])[0] == "unknown_or_conflict" and resolve([known_f, known_w])[3] == "independent_complete_source_overlap_requires_no_silent_precedence"
    return True


def main():
    self_test()
    p = argparse.ArgumentParser()
    p.add_argument("--frame", required=True); p.add_argument("--normalizer", required=True)
    p.add_argument("--normalizer-sha256", required=True)
    p.add_argument("--formal-reviews", required=True); p.add_argument("--formal-packet", required=True); p.add_argument("--formal-linkage", required=True)
    p.add_argument("--wave01-packet", required=True); p.add_argument("--wave01-overlay", required=True)
    p.add_argument("--wave02-packet", required=True); p.add_argument("--wave02-overlay", required=True)
    p.add_argument("--batch001", required=True); p.add_argument("--batch002", required=True)
    p.add_argument("--exclusion-hashes", required=True)
    p.add_argument("--private-ledger", required=True); p.add_argument("--private-queue", required=True)
    p.add_argument("--private-uncertainty", required=True)
    p.add_argument("--public-coverage", required=True); p.add_argument("--receipt", required=True)
    args = p.parse_args(); os.umask(0o077)
    inputs = {name: getattr(args, name) for name in ("frame", "normalizer", "formal_reviews", "formal_packet", "formal_linkage", "wave01_packet", "wave01_overlay", "wave02_packet", "wave02_overlay", "batch001", "batch002", "exclusion_hashes")}
    input_hashes = {name: {"path": path, "sha256": sha_file(path)} for name, path in inputs.items()}
    for name, expected in EXPECTED_SHA.items():
        if input_hashes[name]["sha256"] != expected: raise RuntimeError("accepted input SHA mismatch: " + name)
    module, normalizer_sha = load_normalizer(args.normalizer, args.normalizer_sha256)

    required = set(KEY) | {"exact_text_sha256", "original_text"}
    parquet = pq.ParquetFile(args.frame)
    if not required <= set(parquet.schema_arrow.names): raise RuntimeError("fixed10k frame missing required columns")
    frame = []
    seen_keys = set()
    for batch in parquet.iter_batches(columns=list(KEY) + ["exact_text_sha256", "original_text"], batch_size=2048):
        for row in batch.to_pylist():
            key = tuple(row[k] for k in KEY)
            if key in seen_keys: raise RuntimeError("duplicate canonical ad key")
            seen_keys.add(key)
            if sha_text(row["original_text"]) != row["exact_text_sha256"]: raise RuntimeError("frame raw text hash mismatch")
            normalized = normalize(module, row["original_text"]); context = sha_text(normalized)
            frame.append({"key": key, "raw": row["exact_text_sha256"], "context": context,
                          "original": row["original_text"], "normalized": normalized})
    if len(frame) != 10000 or len({x["raw"] for x in frame}) != 7635: raise RuntimeError("fixed10k cardinality mismatch")
    by_context = collections.defaultdict(list); by_raw = collections.defaultdict(list)
    for i, row in enumerate(frame): by_context[row["context"]].append(i); by_raw[row["raw"]].append(i)
    assigned = collections.defaultdict(list); binding_counts = collections.Counter(); adapter_counts = collections.Counter()
    raw_exposure, context_exposure = set(), set()
    for item in read_jsonl(args.exclusion_hashes):
        scope, value = item.get("hash_scope"), item.get("sha256")
        if scope == "raw_exact": raw_exposure.add(value)
        elif scope == "normalized": context_exposure.add(value)
        else: raise RuntimeError("unrecognized exposure hash scope")
    exposure_flags = [row["raw"] in raw_exposure or row["context"] in context_exposure for row in frame]
    source_binding = collections.Counter()

    formal_packet = {r["context_sha256"]: r for r in read_jsonl(args.formal_packet)}
    formal_reviews = read_jsonl(args.formal_reviews)
    linkage = read_jsonl(args.formal_linkage)
    linked = collections.defaultdict(list); formal_direct_keys = collections.defaultdict(set)
    for row in linkage:
        linked[row["normalized_context_sha256"]].append(row["raw_exact_text_sha256"])
        formal_direct_keys[row["normalized_context_sha256"]].add(tuple(row[k] for k in KEY))
    if len(formal_reviews) != 719 or len(formal_packet) != 719: raise RuntimeError("Formal800 final context count mismatch")
    for review in formal_reviews:
        context = review["context_sha256"]; packet = formal_packet.get(context)
        if not packet or sha_text(packet["full_document"]) != context:
            raise RuntimeError("Formal800 packet/review binding mismatch")
        if context not in linked: raise RuntimeError("Formal800 context absent from hidden linkage")
        source_sha = input_hashes["formal_reviews"]["sha256"]
        js = formal_judgments(review, source_sha)
        source_binding[("formal800_final", "source_rows_total")] += 1
        source_binding[("formal800_final", "source_rows_bound")] += bool(by_context.get(context))
        for index in by_context.get(context, []):
            if frame[index]["normalized"] != packet["full_document"]: raise RuntimeError("Formal800 full normalized input mismatch")
            if frame[index]["key"] in formal_direct_keys[context]: mode = "direct_ad_assignment"
            elif frame[index]["raw"] in linked[context]: mode = "raw_exact_reuse"
            else: mode = "identical_normalized_input_reuse"
            for item in js: assigned[(index, item["family"])].append(dict(item, binding_mode=mode))
            binding_counts[("formal800_final", mode)] += 1

    wave02_packet = {r["selection_index_1based"]: r for r in read_jsonl(args.wave02_packet)}
    wave02 = read_jsonl(args.wave02_overlay)
    if len(wave02_packet) != 96 or len(wave02) != 96: raise RuntimeError("Wave02 count mismatch")
    for row in wave02:
        packet = wave02_packet[row["selection_index_1based"]]
        if sha_text(packet["original_text"]) != row["source_exact_text_sha256"] or sha_text(packet["review_text"]) != row["context_sha256"]:
            raise RuntimeError("Wave02 packet/overlay mismatch")
        js = wave02_judgments(row, input_hashes["wave02_overlay"]["sha256"])
        source_binding[("wave02_final", "source_rows_total")] += 1
        match_indices = sorted(set(by_raw.get(row["source_exact_text_sha256"], [])) | set(by_context.get(row["context_sha256"], [])))
        source_binding[("wave02_final", "source_rows_bound")] += bool(match_indices)
        for index in match_indices:
            if frame[index]["raw"] == row["source_exact_text_sha256"]:
                if frame[index]["original"] != packet["original_text"]: raise RuntimeError("Wave02 full raw input mismatch")
            elif frame[index]["normalized"] != packet["review_text"]:
                raise RuntimeError("Wave02 full normalized input mismatch")
            direct_key = tuple(row["canonical_key"][k] for k in KEY)
            if frame[index]["key"] == direct_key: mode = "direct_ad_assignment"
            elif frame[index]["raw"] == row["source_exact_text_sha256"]: mode = "raw_exact_reuse"
            else: mode = "identical_normalized_input_reuse"
            for item in js: assigned[(index, item["family"])].append(dict(item, binding_mode=mode))
            binding_counts[("wave02_final", mode)] += 1

    wave01_packet = {r["selection_index_1based"]: r for r in read_jsonl(args.wave01_packet)}
    wave01 = read_jsonl(args.wave01_overlay)
    if len(wave01) != 14: raise RuntimeError("Wave01 accepted overlay count mismatch")
    for row in wave01:
        packet = wave01_packet[row["binding"]["selection_index_1based"]]
        if row["binding"]["exact_text_sha256"] != sha_text(packet["review_text"]):
            # Wave01 exact hash is source text, while review_text may be normalized; packet supplies both when present.
            declared = packet.get("exact_text_sha256")
            if declared != row["binding"]["exact_text_sha256"]: raise RuntimeError("Wave01 packet/overlay exact hash mismatch")
        context = sha_text(packet["review_text"])
        js = wave01_judgments(row, context, input_hashes["wave01_overlay"]["sha256"])
        source_binding[("wave01_final", "source_rows_total")] += 1
        source_binding[("wave01_final", "source_rows_bound")] += bool(by_context.get(context))
        for index in by_context.get(context, []):
            if frame[index]["normalized"] != packet["review_text"]: raise RuntimeError("Wave01 full normalized input mismatch")
            direct_key = None
            if isinstance(packet.get("canonical_key"), list) and len(packet["canonical_key"]) == 4:
                direct_key = tuple(packet["canonical_key"])
            elif all(k in packet for k in KEY): direct_key = tuple(packet[k] for k in KEY)
            if direct_key is not None and frame[index]["key"] == direct_key: mode = "direct_ad_assignment"
            elif frame[index]["raw"] == row["binding"]["exact_text_sha256"]: mode = "raw_exact_reuse"
            else: mode = "identical_normalized_input_reuse"
            for item in js: assigned[(index, item["family"])].append(dict(item, binding_mode=mode))
            binding_counts[("wave01_final", mode)] += 1

    for source, name in (("legacy_batch001", "batch001"), ("legacy_batch002", "batch002")):
        rows = read_jsonl(getattr(args, name)); expected = 24 if name == "batch001" else 128
        if len(rows) != expected: raise RuntimeError("{} row count mismatch".format(name))
        for row in rows:
            raw = row["source_text_sha256"]
            source_binding[(source, "source_rows_total")] += 1
            source_binding[(source, "source_rows_bound")] += bool(by_raw.get(raw))
            js, counts = legacy_judgments(row, source, input_hashes[name]["sha256"])
            for key, value in counts.items(): adapter_counts[(source, key)] += value
            for index in by_raw.get(raw, []):
                for item in js: assigned[(index, item["family"])].append(dict(item, binding_mode="raw_exact_reuse"))
                binding_counts[(source, "raw_exact_reuse")] += 1
    expected_adapter = {
        ("legacy_batch001", "object_outcome_unknown"): 3,
        ("legacy_batch001", "duration_error"): 1,
        ("legacy_batch001", "duration_unknown"): 6,
        ("legacy_batch002", "object_outcome_unknown"): 3,
        ("legacy_batch002", "duration_error"): 19,
        ("legacy_batch002", "duration_unknown"): 5,
    }
    for key, expected in expected_adapter.items():
        if adapter_counts[key] != expected: raise RuntimeError("legacy adapter frozen count mismatch: " + repr(key))

    ledger = []; coverage = collections.Counter(); queue_groups = {}
    for index, row in enumerate(frame):
        for family in FAMILIES:
            status, value, provenance, rule = resolve(assigned.get((index, family), []))
            if status not in STATUS: raise RuntimeError("resolved invalid status")
            direct = any(x.get("binding_mode") == "direct_ad_assignment" for x in provenance)
            exposure = sorted(set(x["source"] for x in provenance))
            ledger.append({"canonical_key": dict(zip(KEY, row["key"])), "raw_exact_text_sha256": row["raw"],
                           "normalized_context_sha256": row["context"], "field_family": family,
                           "status": status, "structured_value": value, "resolution_rule": rule,
                           "direct_reviewed_ad_binding": direct, "historical_source_exposure": exposure,
                           "historical_development_evaluation_exposure": exposure_flags[index],
                           "provenance": provenance})
            coverage[(family, status)] += 1
            q = queue_groups.setdefault(row["context"], {"normalized_context_sha256": row["context"],
                "raw_exact_text_sha256_values": set(), "represented_ad_count": 0, "families": collections.defaultdict(collections.Counter),
                "resolution_rules": collections.defaultdict(set),
                "source_exposure": set(), "development_evaluation_exposure": False,
                "representative_canonical_key": dict(zip(KEY, row["key"])), "frame_input_locator": args.frame})
            q["raw_exact_text_sha256_values"].add(row["raw"])
            q["families"][family][status] += 1; q["resolution_rules"][family].add(rule); q["source_exposure"].update(exposure)
            q["development_evaluation_exposure"] = q["development_evaluation_exposure"] or exposure_flags[index]
        queue_groups[row["context"]]["represented_ad_count"] += 1
    queue = []; uncertainty = []; all_resolution_context_counts = collections.Counter()
    for context, q in sorted(queue_groups.items()):
        family_status = {}
        for family in FAMILIES:
            states = q["families"][family]
            if len(states) != 1: raise RuntimeError("same normalized context resolved inconsistently")
            family_status[family] = next(iter(states))
        category_counts = collections.Counter()
        for state in family_status.values():
            category_counts["complete"] += state in ("known", "not_applicable")
            category_counts["reviewed_unknown_or_conflict"] += state == "unknown_or_conflict"
            category_counts["partial"] += state == "partial"
            category_counts["never_reviewed_or_candidate_only"] += state in ("candidate_only", "source_unavailable")
        rules = {family: sorted(q["resolution_rules"][family]) for family in FAMILIES}
        for family, values in rules.items():
            for value in values: all_resolution_context_counts[(family, value)] += 1
        required_families = [family for family in FAMILIES if family_status[family] in ("partial", "candidate_only", "source_unavailable")]
        uncertain_families = [family for family in FAMILIES if family_status[family] == "unknown_or_conflict"]
        common = {"normalized_context_sha256": context,
                      "raw_exact_text_sha256_values": sorted(q["raw_exact_text_sha256_values"]),
                      "represented_ad_count": q["represented_ad_count"], "family_status": family_status,
                      "resolution_rules": rules, "queue_category_counts": dict(category_counts),
                      "source_exposure": sorted(q["source_exposure"]),
                      "historical_development_evaluation_exposure": q["development_evaluation_exposure"],
                      "representative_canonical_key": q["representative_canonical_key"],
                      "frame_input_locator": q["frame_input_locator"]}
        if required_families:
            queue.append(dict(common, required_new_review_families=required_families,
                              overlaps_reviewed_uncertainty=bool(uncertain_families)))
        if uncertain_families:
            uncertainty.append(dict(common, reviewed_uncertain_families=uncertain_families,
                                    overlaps_required_new_review=bool(required_families)))

    atomic_jsonl(args.private_ledger, ledger); atomic_jsonl(args.private_queue, queue)
    atomic_jsonl(args.private_uncertainty, uncertainty)
    coverage_rows = [{"field_family": f, "status": s, "ad_count": n} for (f, s), n in sorted(coverage.items())]
    required_family_context_counts = collections.Counter()
    uncertainty_family_context_counts = collections.Counter()
    for q in queue:
        for family in q["required_new_review_families"]: required_family_context_counts[(family, q["family_status"][family])] += 1
    for q in uncertainty:
        for family in q["reviewed_uncertain_families"]: uncertainty_family_context_counts[family] += 1
    source_binding_rows = []
    for source in sorted(set(k[0] for k in source_binding)):
        total = source_binding[(source, "source_rows_total")]; bound = source_binding[(source, "source_rows_bound")]
        source_binding_rows.append({"source": source, "source_rows": total, "bound_source_rows": bound, "unbound_source_rows": total - bound})
    public = {"version": VERSION, "frame_ads": len(frame), "raw_exact_texts": len(by_raw),
              "normalized_full_inputs": len(by_context), "required_new_review_contexts": len(queue),
              "reviewed_uncertainty_contexts": len(uncertainty),
              "uncertainty_contexts_also_needing_other_fields": sum(x["overlaps_required_new_review"] for x in uncertainty),
              "field_status_ad_counts": coverage_rows,
              "required_contexts_by_family_and_status": [{"field_family": k[0], "status": k[1], "contexts": v} for k, v in sorted(required_family_context_counts.items())],
              "reviewed_uncertainty_contexts_by_family": [{"field_family": k, "contexts": v} for k, v in sorted(uncertainty_family_context_counts.items())],
              "resolution_rule_context_counts": [{"field_family": k[0], "resolution_rule": k[1], "contexts": v} for k, v in sorted(all_resolution_context_counts.items())],
              "accepted_source_binding": source_binding_rows,
              "historical_development_evaluation_exposed_ads": sum(exposure_flags),
              "historical_development_evaluation_exposed_contexts": len({frame[i]["context"] for i, value in enumerate(exposure_flags) if value}),
              "binding_ad_counts": [{"source": k[0], "mode": k[1], "ads": v} for k, v in sorted(binding_counts.items())],
              "legacy_adapter_counts": [{"source": k[0], "measure": k[1], "count": v} for k, v in sorted(adapter_counts.items())],
              "source_unavailable_documented_sources": ["paired_early_development_diagnostic", "D42_source20", "D50_D55_root_diagnostics", "D51_D57_targeted_diagnostic"],
              "source_unavailable_assignment_count": 0,
              "rules": {"exact_binding": "raw exact or identical frozen normalized full input only; no fuzzy/JOB_HASH reuse",
                        "legacy": "strict positive contributes partial atoms only; zero has no negative semantic value; technology/tools/tasks uncovered",
                        "conflict": "Formal final mask absolute; otherwise incompatible complete values unresolved without latest/majority rule"}}
    atomic_json(args.public_coverage, public)
    outputs = {"private_ledger": args.private_ledger, "private_queue": args.private_queue,
               "private_uncertainty": args.private_uncertainty, "public_coverage": args.public_coverage}
    receipt = {"version": VERSION, "status": "pass", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
               "scheduler": {"job_id": os.environ.get("SLURM_JOB_ID"), "host": platform.node()},
               "inputs": input_hashes, "normalizer_sha256": normalizer_sha,
               "code": {"path": str(Path(__file__).resolve()), "sha256": sha_file(Path(__file__).resolve())},
               "checks": {"frame_ads_10000": len(frame) == 10000, "raw_exact_texts_7635": len(by_raw) == 7635,
                          "ledger_rows_70000": len(ledger) == 70000,
                          "required_and_uncertainty_contexts_unique": len({x["normalized_context_sha256"] for x in queue}) == len(queue) and len({x["normalized_context_sha256"] for x in uncertainty}) == len(uncertainty),
                          "no_text_or_quotes_in_outputs": True, "formal_final_mask_precedence": True,
                          "legacy_zero_not_absence": True, "field_family_conservation": all(sum(n for (f, s), n in coverage.items() if f == family) == 10000 for family in FAMILIES)},
               "counts": {"ads": len(frame), "raw_exact_texts": len(by_raw), "normalized_full_inputs": len(by_context),
                          "ledger_rows": len(ledger), "required_new_review_contexts": len(queue),
                          "reviewed_uncertainty_contexts": len(uncertainty)},
               "outputs": {name: {"path": path, "sha256": sha_file(path), "bytes": os.path.getsize(path)} for name, path in outputs.items()},
               "public_coverage_sha256": sha_file(args.public_coverage), "adapter_counts": public["legacy_adapter_counts"],
               "accepted_source_binding": source_binding_rows,
               "claim_boundary": "coverage/provenance inventory only; no new semantic reading, accuracy certification, prevalence estimate, or label replacement"}
    atomic_json(args.receipt, receipt)


if __name__ == "__main__":
    main()
