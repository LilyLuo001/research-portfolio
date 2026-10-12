#!/usr/bin/env python3
"""Mechanically compare primary and blind-audit Formal800 reviews.

This helper never invents labels.  It compares already validated records by
exact context hash, emits private row-level differences, and prepares a root
packet only from audited contexts already present in the supplied linkage.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
from typing import Any

EXP = ("general_work", "occupation_task", "industry_domain", "tool_specific")
ENTRY = ("explicit_no_experience", "explicit_new_graduate",
         "current_student_internship", "explicit_junior_or_entry_label")
RESP = ("independent_judgment", "client_ownership", "people_supervision", "training_mentoring")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rows(path: Path) -> list[dict[str, Any]]:
    out = []
    with path.open(encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise RuntimeError("non-object JSONL row at %s:%d" % (path, n))
                out.append(value)
    return out


def passing(receipt_path: Path, payload_path: Path) -> dict[str, Any]:
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    private = receipt.get("private_outputs", {})
    if receipt.get("status") != "pass" or private.get("validated_sha256") != sha256_file(payload_path):
        raise RuntimeError("validated input does not match a passing receipt: %s" % payload_path)
    if private.get("error_entries", 0) != 0:
        raise RuntimeError("passing receipt reports errors: %s" % payload_path)
    return receipt


def key_set(items: list[dict[str, Any]], keys: tuple[str, ...]) -> set[tuple[Any, ...]]:
    return {tuple(item.get(k) for k in keys) for item in items}


def signature(review: dict[str, Any]) -> dict[str, Any]:
    clauses = key_set(review.get("experience_clauses", []),
                      ("object", "strength", "conditionality", "years_min", "years_max", "years_relation"))
    entries = key_set(review.get("entry_items", []), ("target", "conditionality"))
    duties = key_set(review.get("responsibility_items", []), ("dimension", "subject", "relation"))
    tech = key_set(review.get("technology_items", []), ("family", "role"))
    alternatives = tuple(sorted([(item.get("relation"), len(item.get("branches", [])))
        for item in review.get("qualification_alternatives", [])], key=repr))
    return {
        "experience_outcomes": tuple(review.get("experience_outcomes", {}).get(k) for k in EXP),
        "experience_clauses": tuple(sorted(clauses, key=repr)),
        "entry_outcomes": tuple(review.get("entry_outcomes", {}).get(k) for k in ENTRY),
        "entry_items": tuple(sorted(entries, key=repr)),
        "responsibility_outcomes": tuple(review.get("responsibility_outcomes", {}).get(k) for k in RESP),
        "responsibility_items": tuple(sorted(duties, key=repr)),
        "technology_inventory_status": review.get("technology_inventory_status"),
        "technology_items": tuple(sorted(tech, key=repr)),
        "qualification_alternatives": alternatives,
    }


def field_differences(a: dict[str, Any], b: dict[str, Any]) -> list[str]:
    sa, sb = signature(a), signature(b)
    return [name for name in sa if sa[name] != sb[name]]


def load_linkage(path: Path) -> dict[str, dict[str, Any]]:
    out = {}
    for row in rows(path):
        context = row.get("context_sha256")
        blind = row.get("blind_id") or row.get("record_id")
        if not isinstance(context, str) or not isinstance(blind, str) or not blind:
            raise RuntimeError("hidden linkage rows require context_sha256 and blind_id/record_id")
        if blind in out:
            raise RuntimeError("duplicate blind ID in hidden linkage")
        out[blind] = row
    return out


def load_audit_packet(path: Path) -> dict[str, dict[str, Any]]:
    out = {}
    for row in rows(path):
        required = {"record_id", "context_sha256", "full_document", "assignment"}
        if set(row) != required or not isinstance(row["full_document"], str) or not row["full_document"]:
            raise RuntimeError("audit packet rows must be exact packet records with full text")
        context = row["context_sha256"]
        if context in out:
            raise RuntimeError("duplicate context in audit packet")
        out[context] = row
    return out


def mask_unresolved(review: dict[str, Any], other=None) -> dict[str, Any]:
    """Keep unresolved blind disagreements unknown; originals remain archived."""
    result = json.loads(json.dumps(review))
    if other is not None:
        conflicts = []
        contracts = (
            ("experience_outcomes", EXP, "experience_clauses", "object", ("strength", "conditionality", "years_min", "years_max", "years_relation")),
            ("entry_outcomes", ENTRY, "entry_items", "target", ("conditionality",)),
            ("responsibility_outcomes", RESP, "responsibility_items", "dimension", ("subject", "relation")),
        )
        for outcomes, dims, inventory, selector, attributes in contracts:
            for dim in dims:
                a = key_set([x for x in review[inventory] if x.get(selector) == dim], attributes)
                b = key_set([x for x in other[inventory] if x.get(selector) == dim], attributes)
                if review[outcomes][dim] != other[outcomes][dim] or a != b:
                    result[outcomes][dim] = "unknown"
                    conflicts.append(outcomes + "." + dim)
        a, b = signature(review), signature(other)
        if a["technology_items"] != b["technology_items"] or a["technology_inventory_status"] != b["technology_inventory_status"]:
            result["technology_inventory_status"] = "unknown"
            conflicts.append("technology")
        if a["qualification_alternatives"] != b["qualification_alternatives"]:
            for group in result["qualification_alternatives"]:
                group["relation"] = "unresolved"
            affected = {x["object"] for r in (review, other) for x in r["experience_clauses"] if x.get("alternative_group")}
            for dim in affected & set(EXP):
                result["experience_outcomes"][dim] = "unknown"
            conflicts.append("qualification_alternatives")
        if conflicts:
            result["unresolved_notes"].append("Unadjudicated blind-review disagreement: " + ", ".join(conflicts))
    unknown_exp = {k for k, v in result.get("experience_outcomes", {}).items() if v == "unknown"}
    if unknown_exp:
        result["experience_clauses"] = [c for c in result.get("experience_clauses", []) if c.get("object") not in unknown_exp]
    unknown_entry = {k for k, v in result.get("entry_outcomes", {}).items() if v == "unknown"}
    if unknown_entry:
        result["entry_items"] = [i for i in result.get("entry_items", []) if i.get("target") not in unknown_entry]
    unknown_resp = {k for k, v in result.get("responsibility_outcomes", {}).items() if v == "unknown"}
    if unknown_resp:
        result["responsibility_items"] = [i for i in result.get("responsibility_items", []) if i.get("dimension") not in unknown_resp]
    if result.get("technology_inventory_status") == "unknown":
        result["technology_items"] = []
    for key in ("trusted_assignment", "evidence_resolution", "validation_version", "resolution_status"):
        result.pop(key, None)
    return result


def write_jsonl(path: Path, values: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for value in values:
            f.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    os.umask(0o077)
    p = argparse.ArgumentParser()
    p.add_argument("--primary-validated", type=Path, required=True)
    p.add_argument("--primary-receipt", type=Path, required=True)
    p.add_argument("--audit-validated", type=Path, required=True)
    p.add_argument("--audit-receipt", type=Path, required=True)
    p.add_argument("--audit-packet", type=Path, required=True,
                   help="frozen BLIND_AUDIT_PACKET_PRIVATE.jsonl carrying exact audit text")
    p.add_argument("--hidden-linkage-audit", type=Path, help="optional redundant audit-ID map; full ad linkage is not this file")
    p.add_argument("--output-dir", type=Path, required=True)
    p.add_argument("--root-resolutions", type=Path,
                   help="explicit complete replacement reviews; without this, no final overlay is emitted")
    p.add_argument("--resolution-receipt", type=Path,
                   help="passing receipt for the exact root-resolution JSONL")
    args = p.parse_args()

    passing(args.primary_receipt, args.primary_validated)
    passing(args.audit_receipt, args.audit_validated)
    primary = {r["context_sha256"]: r for r in rows(args.primary_validated)}
    audit = {r["context_sha256"]: r for r in rows(args.audit_validated)}
    if len(primary) != len(rows(args.primary_validated)) or len(audit) != len(rows(args.audit_validated)):
        raise RuntimeError("duplicate context_sha256 in validated inputs")
    audit_packet = load_audit_packet(args.audit_packet)
    if set(audit_packet) != set(audit):
        raise RuntimeError("audit validated contexts must exactly equal frozen audit packet contexts")
    if not set(audit_packet) <= set(primary):
        raise RuntimeError("every audit context must have a primary review")
    for context, source in audit_packet.items():
        if source["record_id"] != audit[context]["record_id"]:
            raise RuntimeError("audit blind ID differs from its frozen packet")
    if args.hidden_linkage_audit:
        linkage = load_linkage(args.hidden_linkage_audit)
        if {r["record_id"]: r["context_sha256"] for r in audit_packet.values()} != {k:r["context_sha256"] for k,r in linkage.items()}:
            raise RuntimeError("optional audit linkage differs from frozen packet")
    common = sorted(set(primary) & set(audit_packet))
    if not common:
        raise RuntimeError("no exact audited contexts match primary validated input")

    differences = []
    counts = collections.Counter()
    for context in common:
        fields = field_differences(primary[context], audit[context])
        if fields:
            priority = 0 if any(f.startswith("technology") for f in fields) else 1 if any(f.startswith("entry") for f in fields) else 2 if any(f.startswith("responsibility") for f in fields) else 3
            counts.update(fields)
            differences.append({"record_id": primary[context]["record_id"], "context_sha256": context,
                                "difference_fields": fields, "priority": priority,
                                "primary_review": primary[context], "audit_review": audit[context]})
    differences.sort(key=lambda x: (x["priority"], x["context_sha256"]))
    agreements = [{"record_id": primary[c]["record_id"], "context_sha256": c}
                  for c in common if not field_differences(primary[c], audit[c])]
    agreements.sort(key=lambda x: x["context_sha256"])
    selected = differences[:36]
    selected.extend(agreements[:min(4, max(0, 40 - len(selected)))])
    if len(selected) < 40:
        used = {item["context_sha256"] for item in selected}
        selected.extend(item for item in differences[36:] if item["context_sha256"] not in used)
        selected = selected[:40]

    out = args.output_dir
    out.mkdir(parents=True, exist_ok=True)
    private = out / "AUDIT_DIFFERENCES_PRIVATE.jsonl"
    write_jsonl(private, differences)
    packet = []
    for item in selected:
        context = item["context_sha256"]
        source = audit_packet[context]
        packet.append({"record_id": primary[context]["record_id"], "context_sha256": context,
                       "full_document": source["full_document"],
                       "assignment": {"packet_id": "root-%s" % context[:16],
                                      "reviewer_role": "primary", "provenance": "root_selected_audit"}})
    write_jsonl(out / "ROOT_REVIEW_PACKET.jsonl", packet)
    # Bundle only the already selected bounded cases for actual root reading.
    # This is private transport, not a second selection or a new semantic label.
    write_jsonl(out / "ROOT_REVIEW_BUNDLE_PRIVATE.jsonl", [
        {"packet": item, "primary_review": primary[item["context_sha256"]],
         "audit_review": audit[item["context_sha256"]],
         "difference_fields": field_differences(primary[item["context_sha256"]], audit[item["context_sha256"]])}
        for item in packet])
    (out / "AUDIT_AGGREGATE.json").write_text(json.dumps({
        "status": "ready_for_root_review", "audited_contexts": len(common),
        "disagreement_contexts": len(differences), "agreement_contexts": len(agreements),
        "disagreement_counts": dict(sorted(counts.items())), "selected_root_records": len(packet),
        "selection": "up to 36 disagreements prioritized technology, entry, duty, then other; fill with agreements to 40",
        "primary_receipt": sha256_file(args.primary_receipt), "audit_receipt": sha256_file(args.audit_receipt)}, indent=2) + "\n", encoding="utf-8")

    if args.root_resolutions:
        if not args.resolution_receipt:
            raise RuntimeError("--root-resolutions requires --resolution-receipt")
        passing(args.resolution_receipt, args.root_resolutions)
        replacements = rows(args.root_resolutions)
        selected_contexts = {item["context_sha256"] for item in selected}
        replacement_contexts = {r.get("context_sha256") for r in replacements}
        if replacement_contexts != selected_contexts:
            raise RuntimeError("root replacements must exactly match the selected root packet set")
        seen = set()
        overlay = []
        final_by_context = {c: mask_unresolved(r, audit.get(c)) for c,r in primary.items()}
        for review in replacements:
            rid, context = review.get("record_id"), review.get("context_sha256")
            if rid in seen or not isinstance(rid, str) or not isinstance(context, str) or context not in primary:
                raise RuntimeError("root replacement is duplicate or not bound to primary")
            if review.get("record_id") != primary[context]["record_id"]:
                raise RuntimeError("root replacement record_id/context binding mismatch")
            seen.add(rid)
            final_by_context[context] = mask_unresolved(review)
            overlay.append({"record_id": rid, "context_sha256": context, "resolved_review": review,
                            "resolution_id": "root-%s" % context[:16]})
        write_jsonl(out / "RESOLVED_OVERLAY.jsonl", overlay)
        (out / "RESOLVED_OVERLAY_RECEIPT.json").write_text(json.dumps({
            "status": "pass", "private_outputs": {"overlay_sha256": sha256_file(out / "RESOLVED_OVERLAY.jsonl"), "error_entries": 0},
            "source_resolution_receipt": sha256_file(args.resolution_receipt)}, indent=2) + "\n", encoding="utf-8")
        write_jsonl(out / "FINAL_REVIEW_RAW_PRIVATE.jsonl",
                    [mask_unresolved(final_by_context[c]) for c in sorted(final_by_context)])


if __name__ == "__main__":
    main()
