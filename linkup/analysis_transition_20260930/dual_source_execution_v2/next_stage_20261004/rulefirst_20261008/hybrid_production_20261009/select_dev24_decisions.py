#!/usr/bin/env python3
"""Select a bounded, development-only relation review packet.

This program does not extract or adjudicate semantic labels. It joins the
frozen dev120 source to the frozen v1.2 rule output, applies six disclosed
mechanical candidate predicates, and writes at most four unique documents per
group for bounded root review.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import socket
from collections import Counter
from pathlib import Path

GROUP_ORDER = [
    "required_general_plus_preferred_industry",
    "degree_experience_alternative",
    "junior_referent",
    "software_use_vs_development",
    "heading_strength_scope",
    "mentorship_vs_receiving_training",
]


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            if line.strip():
                try:
                    yield json.loads(line)
                except Exception as exc:
                    raise RuntimeError(f"invalid JSONL {path}:{line_number}: {exc}")


def sha_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def group_matches(result):
    evidence = result.get("evidence") or []
    experience = [e for e in evidence if e.get("kind") == "experience"]
    education = [e for e in evidence if e.get("kind") == "education"]
    entry = [e for e in evidence if e.get("kind") == "entry"]
    technology = [e for e in evidence if e.get("kind") == "technology"]
    tasks = [e for e in evidence if e.get("kind") == "task"]
    flags = result.get("flags") or {}
    reasons = set(result.get("review_reasons") or [])
    text = result.get("normalized_text") or ""

    req_general = any(
        e.get("strength") == "required" and "general_work" in (e.get("objects") or [])
        for e in experience
    )
    pref_industry = any(
        e.get("strength") == "preferred" and "industry_domain" in (e.get("objects") or [])
        for e in experience
    )
    mixed_relation = any(
        e.get("strength") == "mixed"
        and ({"general_work", "industry_domain"} & set(e.get("objects") or []))
        for e in experience
    )

    alternative = (
        flags.get("multiline_qualification_alternative") is True
        or flags.get("education_experience_alternative") is True
        or "multiline_qualification_alternative" in reasons
        or any(e.get("scope") in {"education_alternative", "document_multiline_alternative_unresolved"}
               for e in experience + education)
    )

    junior = bool(entry) and bool(re.search(r"\b(?:junior|entry[- ]level)\b", text, re.I))

    software_roles = {
        e.get("role_cue") for e in technology
        if e.get("technology") == "software"
    }
    software_relation = bool(software_roles & {"use_cue", "development_cue", "implementation_cue"})

    explicit_strength_words = re.compile(
        r"\b(?:required|requires?|must|mandatory|minimum|preferred|preferably|desired|desirable|nice to have|a plus)\b",
        re.I,
    )
    heading_scope = any(
        e.get("section") in {"required", "preferred"}
        and e.get("strength") == e.get("section")
        and not explicit_strength_words.search(e.get("quote") or "")
        for e in experience
    )

    training_terms = bool(re.search(r"\b(?:mentor(?:ing|s|ed)?|train(?:ing|s|ed)?|coach(?:ing|es|ed)?)\b", text, re.I))
    training_relation = training_terms and (
        any(e.get("task_family") in {"people_supervision", "execution_assistance"} for e in tasks)
        or bool(re.search(r"\b(?:receive|provided|offered|on[- ]the[- ]job)\s+(?:\w+\s+){0,3}training\b", text, re.I))
    )

    matches = {
        "required_general_plus_preferred_industry": req_general and pref_industry or mixed_relation,
        "degree_experience_alternative": alternative,
        "junior_referent": junior,
        "software_use_vs_development": software_relation,
        "heading_strength_scope": heading_scope,
        "mentorship_vs_receiving_training": training_relation,
    }
    details = {
        "required_general_plus_preferred_industry": {
            "required_general_clause": req_general,
            "preferred_industry_clause": pref_industry,
            "mixed_clause": mixed_relation,
        },
        "degree_experience_alternative": {
            "alternative_flag_or_scope": alternative,
        },
        "junior_referent": {
            "entry_evidence_present": bool(entry),
            "junior_or_entry_level_text_present": junior,
        },
        "software_use_vs_development": {
            "observed_software_role_cues": sorted(x for x in software_roles if x),
        },
        "heading_strength_scope": {
            "strength_inherited_from_heading": heading_scope,
        },
        "mentorship_vs_receiving_training": {
            "training_term_present": training_terms,
            "task_or_receiving_training_pattern_present": training_relation,
        },
    }
    return [g for g in GROUP_ORDER if matches[g]], details


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--rule-output", required=True)
    ap.add_argument("--output-dir", required=True)
    ap.add_argument("--per-group", type=int, default=4)
    args = ap.parse_args()
    if args.per_group < 1 or args.per_group > 4:
        raise SystemExit("per-group must be 1..4")

    source_path = Path(args.source)
    rule_path = Path(args.rule_output)
    sources = list(read_jsonl(source_path))
    outputs = list(read_jsonl(rule_path))
    if len(sources) != 120 or len(outputs) != 120:
        raise RuntimeError(f"expected frozen dev120 inputs/outputs, got {len(sources)}/{len(outputs)}")

    source_by_sha = {}
    for row in sources:
        text = row.get("original_text")
        sha = row.get("exact_text_sha256")
        if not isinstance(text, str) or hashlib.sha256(text.encode("utf-8")).hexdigest() != sha:
            raise RuntimeError("development source text/SHA mismatch")
        if sha in source_by_sha:
            raise RuntimeError("duplicate development source SHA")
        source_by_sha[sha] = row

    candidates = {g: [] for g in GROUP_ORDER}
    joined = 0
    for row in outputs:
        if row.get("status") != "complete":
            continue
        sha = row.get("exact_text_sha256")
        source = source_by_sha.get(sha)
        result = row.get("result") or {}
        if source is None or result.get("source_text_sha256") != sha:
            raise RuntimeError("rule output/source binding mismatch")
        normalized = result.get("normalized_text")
        if not isinstance(normalized, str) or hashlib.sha256(normalized.encode("utf-8")).hexdigest() != result.get("normalized_text_sha256"):
            raise RuntimeError("normalized text/SHA mismatch")
        joined += 1
        matches, details = group_matches(result)
        for group in matches:
            candidates[group].append({
                "sha": sha,
                "arm": source.get("arm"),
                "queue_position_1based": source.get("queue_position_1based"),
                "source": source,
                "rule_row": row,
                "matched_groups": matches,
                "predicate_details": details,
            })
    if joined != 120:
        raise RuntimeError(f"only {joined}/120 frozen rule rows completed")

    selected = []
    selected_shas = set()
    for group in GROUP_ORDER:
        ordered = sorted(candidates[group], key=lambda x: (x["sha"], x.get("queue_position_1based") or 0))
        rank = 0
        for item in ordered:
            if item["sha"] in selected_shas:
                continue
            rank += 1
            selected_shas.add(item["sha"])
            result = item["rule_row"]["result"]
            selected.append({
                "selection_index_1based": len(selected) + 1,
                "decision_group": group,
                "group_rank_1based": rank,
                "all_matched_groups": item["matched_groups"],
                "mechanical_predicate_details": item["predicate_details"][group],
                "exact_text_sha256": item["sha"],
                "arm": item["arm"],
                "queue_position_1based": item["queue_position_1based"],
                "review_text_coordinate_system": "normalized_unicode_codepoints",
                "review_text": result["normalized_text"],
                "frozen_rule_version": result.get("version"),
                "frozen_experience_status": result.get("experience_status"),
                "frozen_review_reasons": result.get("review_reasons") or [],
                "frozen_flags": result.get("flags") or {},
                "frozen_evidence": result.get("evidence") or [],
                "review_fields": {
                    "relation_decision": None,
                    "evidence_indices_used": [],
                    "decision_notes": None,
                    "reviewer": None,
                },
            })
            if rank == args.per_group:
                break

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True, mode=0o700)
    packet = outdir / "DEV24_RELATION_DECISIONS_PRIVATE.jsonl"
    with open(packet, "w", encoding="utf-8") as f:
        for row in selected:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    os.chmod(packet, 0o600)

    receipt = {
        "schema_version": "dev24_relation_packet_v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete_selection_only_no_new_semantic_labels",
        "job_id": os.environ.get("JOB_ID"),
        "host": socket.gethostname(),
        "inputs": {
            "source": {"path": str(source_path), "sha256": sha_file(source_path), "rows": len(sources)},
            "frozen_rule_output": {"path": str(rule_path), "sha256": sha_file(rule_path), "rows": len(outputs)},
        },
        "constraints": {
            "development_only": True,
            "eval80_read": False,
            "new_extraction": False,
            "model_calls": 0,
            "maximum_rows": len(GROUP_ORDER) * args.per_group,
            "unique_source_sha_required": True,
        },
        "candidate_counts_before_cross_group_deduplication": {g: len(candidates[g]) for g in GROUP_ORDER},
        "selected_counts": dict(Counter(x["decision_group"] for x in selected)),
        "selected_rows": len(selected),
        "packet": {"path": str(packet), "bytes": packet.stat().st_size, "sha256": sha_file(packet)},
        "interpretation_boundary": "Mechanical candidates for bounded root review; selection predicates and frozen rule evidence are not semantic adjudication or gold labels.",
    }
    receipt_path = outdir / "DEV24_SELECTION_RECEIPT_PUBLIC.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "complete", "selected_rows": len(selected), "receipt": str(receipt_path)}, sort_keys=True))


if __name__ == "__main__":
    main()
