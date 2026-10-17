#!/usr/bin/env python3
"""Validate and atomically apply the first 100 fixed10k full reviews.

This program creates no semantic values.  It converts only the enriched trusted
packet into the frozen Formal800 validator's four-field packet, then applies
validated reviews to the corresponding context/family cells of the existing
coverage inventory.  All non-batch ledger, queue, and uncertainty rows are
copied through without reinterpretation.
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path

FAMILIES = (
    "technology_category_and_role", "experience_object", "experience_strength",
    "experience_literal_years", "qualification_conditions_and_alternatives",
    "entry_wording_and_scope", "current_responsibility_subject_and_relation",
)
CORE_PACKET = {"record_id", "context_sha256", "full_document", "assignment"}
FROZEN_COVERAGE_SHA = {
    "ledger": "481cf6f844cae9377d3be4d1ce51a25fdcab277e1d9e8280957615946d1e3756",
    "queue": "42741690264ada733f19da8991db5617d64b5d75577db260476cf9f0c1803428",
    "uncertainty": "46d439f8ddd3b9d67d4ab5fe178667602d5da5257d3e6e0246b38f6bdafb2b27",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_json(path: Path, value: dict, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if private: os.chmod(temp, 0o600)
    os.replace(temp, path)


def write_jsonl(path: Path, values: list[dict], private: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    with temp.open("w", encoding="utf-8") as f:
        for value in values:
            f.write(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    if private: os.chmod(temp, 0o600)
    os.replace(temp, path)


def packet_map(packet_path: Path, expected_records: int) -> dict[str, dict]:
    result = {}
    for row in rows(packet_path):
        if not CORE_PACKET <= set(row):
            raise RuntimeError("enriched packet misses frozen validator fields")
        record = row["record_id"]
        if record in result or not isinstance(record, str) or not record:
            raise RuntimeError("empty or duplicate enriched packet record_id")
        if set(row.get("required_new_review_families", [])) != set(FAMILIES):
            raise RuntimeError("batch packet is not the approved all-seven-family first100")
        projections = row.get("existing_family_projections")
        if not isinstance(projections, list) or {x.get("field_family") for x in projections} != set(FAMILIES):
            raise RuntimeError("first100 packet lacks its seven preserved field projections")
        if any(x.get("status") == "unknown_or_conflict" for x in projections):
            raise RuntimeError("reviewed-unknown projection entered this batch")
        result[record] = row
    if len(result) != expected_records:
        raise RuntimeError(f"trusted packet must contain exactly {expected_records} records")
    return result


def make_core(args: argparse.Namespace) -> None:
    packet = packet_map(Path(args.enriched_packet), args.expected_records)
    core = [{k: row[k] for k in CORE_PACKET} for _, row in sorted(packet.items())]
    write_jsonl(Path(args.output), core)


def load_coverage(path: Path):
    spec = importlib.util.spec_from_file_location("coverage_reconcile", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def require_validation(receipt_paths: list[Path], validated_paths: list[Path], all_reviews: Path, expected: int) -> list[dict]:
    if len(receipt_paths) != 5 or len(validated_paths) != 5:
        raise RuntimeError("batch001 requires five packet validation receipts and outputs")
    receipts = []
    concatenated = []
    for receipt_path, validated_path in zip(receipt_paths, validated_paths):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("status") != "pass" or receipt.get("counts", {}).get("validated_records") != 20:
            raise RuntimeError("frozen Formal800 packet validation did not pass for 20 records")
        if receipt.get("private_outputs", {}).get("validated_sha256") != digest(validated_path):
            raise RuntimeError("validation receipt does not bind supplied packet reviews")
        receipts.append(receipt)
        concatenated.extend(rows(validated_path))
    all_rows = rows(all_reviews)
    if len(concatenated) != expected or all_rows != concatenated:
        raise RuntimeError("combined validated reviews do not exactly preserve packet validator outputs")
    return receipts


def queue_row(context: str, ledger_rows: list[dict], old_queue_row: dict) -> tuple[dict | None, dict | None]:
    family = {x["field_family"]: x for x in ledger_rows}
    if set(family) != set(FAMILIES):
        raise RuntimeError("target context does not have all seven ledger families")
    statuses = {name: row["status"] for name, row in family.items()}
    required = [name for name in FAMILIES if statuses[name] in ("partial", "candidate_only", "source_unavailable")]
    uncertain = [name for name in FAMILIES if statuses[name] == "unknown_or_conflict"]
    first = next(iter(family.values()))
    common = {
        "normalized_context_sha256": context,
        "raw_exact_text_sha256_values": sorted({x["raw_exact_text_sha256"] for x in ledger_rows}),
        "represented_ad_count": len({tuple(sorted(x["canonical_key"].items())) for x in ledger_rows}),
        "family_status": statuses,
        "resolution_rules": {name: [family[name]["resolution_rule"]] for name in FAMILIES},
        "queue_category_counts": {
            "complete": sum(v in ("known", "not_applicable") for v in statuses.values()),
            "reviewed_unknown_or_conflict": len(uncertain),
            "partial": sum(v == "partial" for v in statuses.values()),
            "never_reviewed_or_candidate_only": sum(v in ("candidate_only", "source_unavailable") for v in statuses.values()),
        },
        "source_exposure": sorted({p["source"] for row in ledger_rows for p in row.get("provenance", [])}),
        "historical_development_evaluation_exposure": any(x.get("historical_development_evaluation_exposure", False) for x in ledger_rows),
        "representative_canonical_key": old_queue_row["representative_canonical_key"],
        "frame_input_locator": old_queue_row["frame_input_locator"],
    }
    q = dict(common, required_new_review_families=required, overlaps_reviewed_uncertainty=bool(uncertain)) if required else None
    u = dict(common, reviewed_uncertain_families=uncertain, overlaps_required_new_review=bool(required)) if uncertain else None
    return q, u


def finalize(args: argparse.Namespace) -> None:
    packet = packet_map(Path(args.enriched_packet), 100)
    validation = require_validation([Path(x) for x in args.validation_receipts], [Path(x) for x in args.validated_packets], Path(args.validated_reviews), len(packet))
    reviews = rows(Path(args.validated_reviews))
    if len(reviews) != len(packet) or {r.get("record_id") for r in reviews} != set(packet):
        raise RuntimeError("validated reviews do not exactly cover trusted first100 packet")
    coverage = load_coverage(Path(args.coverage_module))
    review_sha = digest(Path(args.validated_reviews))
    additions: dict[str, dict[str, dict]] = {}
    for review in reviews:
        record = review["record_id"]; context = review["context_sha256"]
        if context != packet[record]["context_sha256"]:
            raise RuntimeError("validated review context differs from trusted packet")
        converted = {}
        for item in coverage.formal_judgments(review, review_sha):
            item = dict(item)
            item["source"] = "fixed10k_batch001"
            item["scope"] = "batch001_full_document_all_required_families"
            item["notes"] = list(item.get("notes", [])) + ["validated_new_batch001"]
            converted[item["family"]] = item
        if set(converted) != set(FAMILIES):
            raise RuntimeError("Formal800 judgment adapter did not return all required families")
        additions[context] = converted
    paths = {"ledger": Path(args.existing_ledger), "queue": Path(args.existing_queue), "uncertainty": Path(args.existing_uncertainty)}
    if {name: digest(path) for name, path in paths.items()} != FROZEN_COVERAGE_SHA:
        raise RuntimeError("existing coverage artifacts do not match the frozen d3e508b reconciliation receipt")
    old_ledger = rows(paths["ledger"]); old_queue = rows(paths["queue"]); old_uncertainty = rows(paths["uncertainty"])
    target_contexts = set(additions)
    expected_contexts = {x["normalized_context_sha256"] for x in old_queue[:100]}
    if target_contexts != expected_contexts:
        raise RuntimeError("batch packet contexts are not exactly the first100 frozen queue contexts")
    old_queue_by_context = {x["normalized_context_sha256"]: x for x in old_queue}
    by_context: dict[str, list[dict]] = collections.defaultdict(list)
    for row in old_ledger: by_context[row["normalized_context_sha256"]].append(row)
    if not target_contexts <= set(by_context):
        raise RuntimeError("a reviewed batch context is absent from existing coverage ledger")
    # Contract: every selected context initially needs all seven families and has no
    # reviewed-unknown projection. Never overwrite a known/not-applicable/unknown row.
    for context in target_contexts:
        prior = {x["field_family"]: x for x in by_context[context]}
        if set(prior) != set(FAMILIES) or any(x["status"] not in ("candidate_only", "partial", "source_unavailable") for x in prior.values()):
            raise RuntimeError("target context violates preserved-status batch contract")
    new_ledger = []
    for row in old_ledger:
        context, family = row["normalized_context_sha256"], row["field_family"]
        if context not in target_contexts:
            new_ledger.append(row); continue
        item = additions[context][family]
        replacement = dict(row)
        replacement.update({"status": item["status"], "structured_value": item["value"],
                            "resolution_rule": "fixed10k_batch001_validated_full_review",
                            "historical_source_exposure": sorted(set(row.get("historical_source_exposure", [])) | {"fixed10k_batch001"}),
                            "provenance": [dict(item, binding_mode="direct_context_assignment")]})
        new_ledger.append(replacement)
    new_by_context: dict[str, list[dict]] = collections.defaultdict(list)
    for row in new_ledger: new_by_context[row["normalized_context_sha256"]].append(row)
    new_queue = [x for x in old_queue if x["normalized_context_sha256"] not in target_contexts]
    new_uncertainty = [x for x in old_uncertainty if x["normalized_context_sha256"] not in target_contexts]
    for context in sorted(target_contexts):
        q, u = queue_row(context, new_by_context[context], old_queue_by_context[context])
        if q: new_queue.append(q)
        if u: new_uncertainty.append(u)
    new_queue.sort(key=lambda x: x["normalized_context_sha256"]); new_uncertainty.sort(key=lambda x: x["normalized_context_sha256"])
    counts = collections.Counter((x["field_family"], x["status"]) for x in new_ledger)
    if len(new_ledger) != 70000 or any(sum(n for (f, _), n in counts.items() if f == family) != 10000 for family in FAMILIES):
        raise RuntimeError("updated ledger does not conserve 10,000 ads across all seven families")
    covered_ads = {tuple(sorted(x["canonical_key"].items())) for x in new_ledger if x["normalized_context_sha256"] in target_contexts}
    updated_ad_field_rows = sum(1 for x in new_ledger if x["normalized_context_sha256"] in target_contexts)
    public = {
        "version": "fixed10k-semantic-production-batch001-v1",
        "claim_boundary": "validated full-document semantic judgments for the direct first100 contexts only; no new sample, prevalence, accuracy, or full-frame completion claim",
        "batch": {"trusted_contexts": len(packet), "validated_contexts": len(reviews), "source": "fixed10k_batch001", "all_required_families": list(FAMILIES)},
        "delta": {"updated_contexts": len(target_contexts), "updated_context_family_cells": len(target_contexts) * len(FAMILIES),
                  "updated_ad_field_rows": updated_ad_field_rows, "covered_ads": len(covered_ads),
                  "reused_prior_family_cells": 0,
                  "final_unknown_contexts_in_batch": sum(any(x["status"] == "unknown_or_conflict" for x in new_by_context[c]) for c in target_contexts),
                  "remaining_required_contexts": len(new_queue), "remaining_reviewed_uncertainty_contexts": len(new_uncertainty)},
        "field_status_ad_counts": [{"field_family": f, "status": s, "ad_count": n} for (f, s), n in sorted(counts.items())],
        "validation": {"receipt_sha256s": [digest(Path(x)) for x in args.validation_receipts], "validated_reviews_sha256": review_sha,
                       "validator_statuses": [x["status"] for x in validation]},
    }
    write_jsonl(Path(args.private_ledger), new_ledger); write_jsonl(Path(args.private_queue), new_queue); write_jsonl(Path(args.private_uncertainty), new_uncertainty)
    write_json(Path(args.public_counts), public)
    receipt = {"version": public["version"], "status": "pass", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
               "code_sha256": digest(Path(__file__)), "inputs": {"enriched_packet_sha256": digest(Path(args.enriched_packet)), "validated_reviews_sha256": review_sha,
               "validation_receipt_sha256s": [digest(Path(x)) for x in args.validation_receipts], "existing_ledger_sha256": digest(Path(args.existing_ledger)),
               "existing_queue_sha256": digest(Path(args.existing_queue)), "existing_uncertainty_sha256": digest(Path(args.existing_uncertainty))},
               "outputs": {"private_ledger_sha256": digest(Path(args.private_ledger)), "private_queue_sha256": digest(Path(args.private_queue)),
               "private_uncertainty_sha256": digest(Path(args.private_uncertainty)), "public_counts_sha256": digest(Path(args.public_counts))},
               "counts": public["delta"], "checks": {"all100_validated": len(reviews) == 100, "all7_family_replacement": len(target_contexts) * len(FAMILIES) == 700,
               "no_prior_known_not_applicable_or_unknown_overwritten": True, "non_batch_rows_copied_through": True,
               "ledger_rows_70000": len(new_ledger) == 70000,
               "each_family_ads_10000": all(sum(n for (f, _), n in counts.items() if f == family) == 10000 for family in FAMILIES)}}
    write_json(Path(args.receipt), receipt)


def main() -> None:
    p = argparse.ArgumentParser(); sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("core-packet"); c.add_argument("--enriched-packet", required=True); c.add_argument("--output", required=True); c.add_argument("--expected-records", type=int, required=True)
    f = sub.add_parser("finalize")
    for name in ("enriched_packet", "validated_reviews", "coverage_module", "existing_ledger", "existing_queue", "existing_uncertainty", "private_ledger", "private_queue", "private_uncertainty", "public_counts", "receipt"):
        f.add_argument("--" + name.replace("_", "-"), required=True)
    f.add_argument("--validation-receipts", nargs="+", required=True)
    f.add_argument("--validated-packets", nargs="+", required=True)
    args = p.parse_args()
    if args.command == "core-packet": make_core(args)
    else: finalize(args)


if __name__ == "__main__": main()
