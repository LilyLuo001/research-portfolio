#!/usr/bin/env python3
"""Validate and atomically apply one Batch002--004 continuation batch.

The prepared packet is the immutable selection and required-family whitelist.
Formal800 remains the transport/schema and semantic adapter. Only whitelisted
context/family cells are replaced; every other ledger row is preserved.
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
ALLOWED_REQUIRED = {"partial", "candidate_only", "source_unavailable"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rows(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_json(path: Path, value: dict, private: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if private:
        os.chmod(temp, 0o600)
    os.replace(temp, path)


def write_jsonl(path: Path, values: list[dict], private: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    with temp.open("w", encoding="utf-8") as stream:
        for value in values:
            stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    if private:
        os.chmod(temp, 0o600)
    os.replace(temp, path)


def packet_map(packet_path: Path, expected_records: int, batch_number: int) -> dict[str, dict]:
    result = {}
    prefix = "fixed10k-prod-b{:03d}-".format(batch_number)
    for row in rows(packet_path):
        if not CORE_PACKET <= set(row):
            raise RuntimeError("enriched packet misses frozen validator fields")
        record = row["record_id"]
        if record in result or not isinstance(record, str) or not record.startswith(prefix):
            raise RuntimeError("empty, duplicate, or wrong-batch packet record_id")
        assignment = row.get("assignment", {})
        if assignment.get("batch_number") != batch_number or assignment.get("batch_position_1based") not in range(1, 101):
            raise RuntimeError("packet assignment batch identity mismatch")
        required = row.get("required_new_review_families")
        if not isinstance(required, list) or not required or len(required) != len(set(required)) or any(x not in FAMILIES for x in required):
            raise RuntimeError("batch packet has invalid required-family whitelist")
        projections = row.get("existing_family_projections")
        if not isinstance(projections, list) or {x.get("field_family") for x in projections} != set(FAMILIES):
            raise RuntimeError("packet lacks seven preserved field projections")
        projected = {x["field_family"]: x for x in projections}
        if any(projected[x].get("status") not in ALLOWED_REQUIRED for x in required):
            raise RuntimeError("required whitelist includes completed or reviewed-unknown field")
        result[record] = row
    if len(result) != expected_records:
        raise RuntimeError("trusted packet must contain exactly {} records".format(expected_records))
    return result


def make_core(args: argparse.Namespace) -> None:
    packet = packet_map(Path(args.enriched_packet), args.expected_records, args.batch_number)
    core = [{key: row[key] for key in CORE_PACKET} for _, row in sorted(packet.items())]
    write_jsonl(Path(args.output), core)


def load_coverage(path: Path):
    spec = importlib.util.spec_from_file_location("coverage_reconcile", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def require_validation(receipt_paths: list[Path], validated_paths: list[Path], all_reviews: Path, expected: int) -> list[dict]:
    if len(receipt_paths) != 5 or len(validated_paths) != 5:
        raise RuntimeError("continuation batch requires five packet validation receipts and outputs")
    receipts, concatenated = [], []
    for receipt_path, validated_path in zip(receipt_paths, validated_paths):
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("status") != "pass" or receipt.get("counts", {}).get("validated_records") != 20:
            raise RuntimeError("frozen Formal800 packet validation did not pass for 20 records")
        if receipt.get("private_outputs", {}).get("validated_sha256") != digest(validated_path):
            raise RuntimeError("validation receipt does not bind supplied packet reviews")
        receipts.append(receipt)
        concatenated.extend(rows(validated_path))
    if rows(all_reviews) != concatenated or len(concatenated) != expected:
        raise RuntimeError("combined validated reviews do not exactly preserve packet validator outputs")
    return receipts


def require_prior(receipt_path: Path, batch_number: int, paths: dict[str, Path]) -> dict:
    prior = json.loads(receipt_path.read_text(encoding="utf-8"))
    if prior.get("status") != "pass":
        raise RuntimeError("prior finalize receipt is not passing")
    expected_prior = batch_number - 1
    prior_batch = prior.get("record_batch", {}).get("batch_number")
    if expected_prior == 1:
        if prior.get("version") != "fixed10k-semantic-production-batch001-v1":
            raise RuntimeError("Batch002 must chain directly from accepted Batch001")
    elif prior_batch != expected_prior:
        raise RuntimeError("prior receipt record_batch does not match sequential predecessor")
    outputs = prior.get("outputs", {})
    names = {"ledger": "private_ledger_sha256", "queue": "private_queue_sha256", "uncertainty": "private_uncertainty_sha256"}
    actual = {name: digest(path) for name, path in paths.items()}
    if any(outputs.get(key) != actual[name] for name, key in names.items()):
        raise RuntimeError("existing artifacts do not match prior receipt output chain")
    return {"path": str(receipt_path), "sha256": digest(receipt_path), "version": prior.get("version")}


def queue_row(context: str, ledger_rows: list[dict], old_queue_row: dict) -> tuple[dict | None, dict | None]:
    family = {x["field_family"]: x for x in ledger_rows}
    if set(family) != set(FAMILIES):
        raise RuntimeError("target context does not have all seven ledger families")
    statuses = {name: family[name]["status"] for name in FAMILIES}
    required = [name for name in FAMILIES if statuses[name] in ALLOWED_REQUIRED]
    uncertain = [name for name in FAMILIES if statuses[name] == "unknown_or_conflict"]
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
    queued = dict(common, required_new_review_families=required, overlaps_reviewed_uncertainty=bool(uncertain)) if required else None
    uncertain_row = dict(common, reviewed_uncertain_families=uncertain, overlaps_required_new_review=bool(required)) if uncertain else None
    return queued, uncertain_row


def finalize(args: argparse.Namespace) -> None:
    batch_number = args.batch_number
    if batch_number not in (2, 3, 4):
        raise RuntimeError("only Batch002, Batch003, and Batch004 are authorized")
    packet = packet_map(Path(args.enriched_packet), 100, batch_number)
    validation = require_validation([Path(x) for x in args.validation_receipts], [Path(x) for x in args.validated_packets], Path(args.validated_reviews), 100)
    reviews = rows(Path(args.validated_reviews))
    if len(reviews) != 100 or {r.get("record_id") for r in reviews} != set(packet):
        raise RuntimeError("validated reviews do not exactly cover trusted batch packet")
    paths = {"ledger": Path(args.existing_ledger), "queue": Path(args.existing_queue), "uncertainty": Path(args.existing_uncertainty)}
    prior_binding = require_prior(Path(args.prior_receipt), batch_number, paths)
    old_ledger, old_queue, old_uncertainty = (rows(paths[name]) for name in ("ledger", "queue", "uncertainty"))
    target_contexts = {row["context_sha256"] for row in packet.values()}
    expected_contexts = {row["normalized_context_sha256"] for row in old_queue[:100]}
    if target_contexts != expected_contexts:
        raise RuntimeError("batch contexts are not exactly the next100 chained queue contexts")
    old_queue_by_context = {x["normalized_context_sha256"]: x for x in old_queue}
    by_context: dict[str, list[dict]] = collections.defaultdict(list)
    for row in old_ledger:
        by_context[row["normalized_context_sha256"]].append(row)
    packet_by_context = {row["context_sha256"]: row for row in packet.values()}
    for context in target_contexts:
        prior_family = {x["field_family"]: x for x in by_context[context]}
        projected = {x["field_family"]: x for x in packet_by_context[context]["existing_family_projections"]}
        if set(prior_family) != set(FAMILIES):
            raise RuntimeError("target context lacks seven ledger families")
        if any(prior_family[f]["status"] != projected[f]["status"] for f in FAMILIES):
            raise RuntimeError("chained ledger status differs from frozen packet projection")

    coverage = load_coverage(Path(args.coverage_module))
    review_sha = digest(Path(args.validated_reviews))
    additions: dict[str, dict[str, dict]] = {}
    for review in reviews:
        record, context = review["record_id"], review["context_sha256"]
        if context != packet[record]["context_sha256"]:
            raise RuntimeError("validated review context differs from trusted packet")
        converted = {}
        for item in coverage.formal_judgments(review, review_sha):
            item = dict(item)
            item["source"] = "fixed10k_batch{:03d}".format(batch_number)
            item["scope"] = "batch{:03d}_full_document_required_family_whitelist".format(batch_number)
            item["notes"] = list(item.get("notes", [])) + ["validated_new_batch{:03d}".format(batch_number)]
            converted[item["family"]] = item
        if set(converted) != set(FAMILIES):
            raise RuntimeError("Formal800 judgment adapter did not return all seven families")
        additions[context] = converted

    required_by_context = {context: set(packet_by_context[context]["required_new_review_families"]) for context in target_contexts}
    source_name = "fixed10k_batch{:03d}".format(batch_number)
    new_ledger, updated_rows = [], 0
    for row in old_ledger:
        context, family = row["normalized_context_sha256"], row["field_family"]
        if context not in target_contexts or family not in required_by_context[context]:
            new_ledger.append(row)
            continue
        item = additions[context][family]
        replacement = dict(row)
        replacement.update({
            "status": item["status"], "structured_value": item["value"],
            "resolution_rule": "batch{:03d}_validated_required_family_review".format(batch_number),
            "historical_source_exposure": sorted(set(row.get("historical_source_exposure", [])) | {source_name}),
            "provenance": [dict(item, binding_mode="direct_context_assignment")],
        })
        new_ledger.append(replacement)
        updated_rows += 1

    old_identity = {(x["normalized_context_sha256"], x["field_family"], tuple(sorted(x["canonical_key"].items()))): x for x in old_ledger}
    for row in new_ledger:
        identity = (row["normalized_context_sha256"], row["field_family"], tuple(sorted(row["canonical_key"].items())))
        context, family = identity[0], identity[1]
        if context not in target_contexts or family not in required_by_context[context]:
            if row != old_identity[identity]:
                raise RuntimeError("non-required or non-batch ledger row changed")

    new_by_context: dict[str, list[dict]] = collections.defaultdict(list)
    for row in new_ledger:
        new_by_context[row["normalized_context_sha256"]].append(row)
    new_queue = [x for x in old_queue if x["normalized_context_sha256"] not in target_contexts]
    new_uncertainty = [x for x in old_uncertainty if x["normalized_context_sha256"] not in target_contexts]
    for context in sorted(target_contexts):
        queued, uncertain_row = queue_row(context, new_by_context[context], old_queue_by_context[context])
        if queued:
            new_queue.append(queued)
        if uncertain_row:
            new_uncertainty.append(uncertain_row)
    new_queue.sort(key=lambda x: x["normalized_context_sha256"])
    new_uncertainty.sort(key=lambda x: x["normalized_context_sha256"])

    counts = collections.Counter((x["field_family"], x["status"]) for x in new_ledger)
    ledger_rows = len(old_ledger)
    ads_per_family = ledger_rows // len(FAMILIES)
    if ledger_rows % len(FAMILIES) or len(new_ledger) != ledger_rows or any(sum(n for (f, _), n in counts.items() if f == family) != ads_per_family for family in FAMILIES):
        raise RuntimeError("updated ledger does not conserve its seven-family ad frame")
    required_cells = sum(len(x) for x in required_by_context.values())
    reused_cells = len(target_contexts) * len(FAMILIES) - required_cells
    covered_ads = {tuple(sorted(x["canonical_key"].items())) for x in new_ledger if x["normalized_context_sha256"] in target_contexts}
    public = {
        "version": "fixed10k-semantic-production-batch{:03d}-v1".format(batch_number),
        "record_batch": {"batch_number": batch_number, "contexts": 100, "queue_positions_in_predecessor": [1, 100]},
        "claim_boundary": "validated full-document judgments applied only to frozen required families for this direct next100; no new sample, prevalence, accuracy, or full-frame completion claim",
        "batch": {"trusted_contexts": 100, "validated_contexts": 100, "source": source_name, "required_family_cells": required_cells},
        "delta": {
            "updated_contexts": 100, "updated_context_family_cells": required_cells,
            "updated_ad_field_rows": updated_rows, "covered_ads": len(covered_ads),
            "reused_prior_family_cells": reused_cells,
            "final_unknown_contexts_in_batch": sum(any(x["status"] == "unknown_or_conflict" for x in new_by_context[c]) for c in target_contexts),
            "remaining_required_contexts": len(new_queue), "remaining_reviewed_uncertainty_contexts": len(new_uncertainty),
        },
        "field_status_ad_counts": [{"field_family": f, "status": s, "ad_count": n} for (f, s), n in sorted(counts.items())],
        "validation": {"receipt_sha256s": [digest(Path(x)) for x in args.validation_receipts], "validated_reviews_sha256": review_sha,
                       "validator_statuses": [x["status"] for x in validation]},
    }
    write_jsonl(Path(args.private_ledger), new_ledger)
    write_jsonl(Path(args.private_queue), new_queue)
    write_jsonl(Path(args.private_uncertainty), new_uncertainty)
    write_json(Path(args.public_counts), public)
    receipt = {
        "version": public["version"], "record_batch": public["record_batch"], "status": "pass",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "code_sha256": digest(Path(__file__)),
        "prior_receipt": prior_binding,
        "inputs": {"enriched_packet_sha256": digest(Path(args.enriched_packet)), "validated_reviews_sha256": review_sha,
                   "validation_receipt_sha256s": [digest(Path(x)) for x in args.validation_receipts],
                   "existing_ledger_sha256": digest(paths["ledger"]), "existing_queue_sha256": digest(paths["queue"]),
                   "existing_uncertainty_sha256": digest(paths["uncertainty"])},
        "outputs": {"private_ledger_sha256": digest(Path(args.private_ledger)), "private_queue_sha256": digest(Path(args.private_queue)),
                    "private_uncertainty_sha256": digest(Path(args.private_uncertainty)), "public_counts_sha256": digest(Path(args.public_counts))},
        "counts": public["delta"],
        "checks": {"all100_validated": True, "required_family_whitelist_only": True, "non_required_rows_copied_through": True,
                   "non_batch_rows_copied_through": True, "prior_receipt_chain_bound": True,
                   "ledger_rows_conserved": len(new_ledger) == ledger_rows,
                   "each_family_ads_conserved": all(sum(n for (f, _), n in counts.items() if f == family) == ads_per_family for family in FAMILIES)},
    }
    write_json(Path(args.receipt), receipt)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    core = sub.add_parser("core-packet")
    core.add_argument("--enriched-packet", required=True)
    core.add_argument("--output", required=True)
    core.add_argument("--expected-records", type=int, required=True)
    core.add_argument("--batch-number", type=int, required=True)
    final = sub.add_parser("finalize")
    for name in ("enriched_packet", "validated_reviews", "coverage_module", "prior_receipt", "existing_ledger", "existing_queue", "existing_uncertainty", "private_ledger", "private_queue", "private_uncertainty", "public_counts", "receipt"):
        final.add_argument("--" + name.replace("_", "-"), required=True)
    final.add_argument("--batch-number", type=int, required=True)
    final.add_argument("--validation-receipts", nargs="+", required=True)
    final.add_argument("--validated-packets", nargs="+", required=True)
    args = parser.parse_args()
    if args.command == "core-packet":
        make_core(args)
    else:
        finalize(args)


if __name__ == "__main__":
    main()
