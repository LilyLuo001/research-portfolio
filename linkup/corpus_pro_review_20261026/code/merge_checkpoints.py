#!/usr/bin/env python3
"""Merge completed per-batch Pro checkpoints without changing review values."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time

from checkpoint_reviews import has_unknown_outcome, write_json_new, write_jsonl_new
from validate_reviews import read_jsonl, sha256_file


VERSION = "corpus-pro-merged-checkpoint-v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def utc(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def pointer_value(record: dict, pointer: str):
    require(isinstance(pointer, str) and pointer.startswith("/"), "invalid audit JSON Pointer")
    value = record
    for encoded in pointer[1:].split("/"):
        part = encoded.replace("~1", "/").replace("~0", "~")
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoints", type=Path, nargs=3, required=True)
    parser.add_argument("--source-reviews-dir", type=Path, required=True)
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--mechanical-provenance", type=Path, required=True)
    parser.add_argument("--audit-overlay", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    job_id = os.environ.get("SLURM_JOB_ID")
    require(bool(job_id) and job_id.isdecimal(), "actual SLURM_JOB_ID required")
    require(args.output_root.name == job_id and args.output_root.parent.name == "merged_checkpoints",
            "output-root must be merged_checkpoints/<SLURM_JOB_ID>")
    for path in (args.mechanical_provenance, args.audit_overlay):
        require(path.is_file(), "provenance input absent: " + str(path))

    contexts, keys = set(), set()
    merged_ledger, merged_reference = [], []
    receipt_hashes = []
    packet_counts = Counter()
    for checkpoint in args.checkpoints:
        receipt_path = checkpoint / "public" / "CHECKPOINT_RECEIPT_PUBLIC.json"
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        require(receipt["status"] == "complete", "per-batch checkpoint is incomplete")
        counts = receipt["counts"]
        require(counts["pending_packets"] == counts["failed_packets"] == 0,
                "per-batch checkpoint has pending or failed packets")
        ledger_path = checkpoint / "private" / "CONTEXT_LEDGER_PRIVATE.jsonl"
        reference_path = checkpoint / "private" / "AD_LEVEL_PRO_REFERENCE_PRIVATE.jsonl"
        require(sha256_file(ledger_path) == receipt["outputs"]["context_ledger_sha256"],
                "checkpoint ledger SHA mismatch")
        require(sha256_file(reference_path) == receipt["outputs"]["ad_level_reference_sha256"],
                "checkpoint ad-level reference SHA mismatch")
        ledger = read_jsonl(ledger_path)
        reference = read_jsonl(reference_path)
        require(len(ledger) == counts["accepted_contexts"] and
                len(reference) == counts["accepted_ad_keys"],
                "checkpoint row counts mismatch")
        for row in ledger:
            context = row["context_sha256"]
            require(context not in contexts, "context duplicated across batches")
            contexts.add(context)
            merged_ledger.append(row)
        for row in reference:
            key = tuple(str(value) for value in row["canonical_key"])
            require(key not in keys, "canonical ad key duplicated across batches")
            keys.add(key)
            merged_reference.append(row)
        receipt_hashes.append({"checkpoint_job_id": receipt["slurm_job_id"],
                               "receipt_sha256": sha256_file(receipt_path),
                               "ledger_sha256": sha256_file(ledger_path),
                               "ad_reference_sha256": sha256_file(reference_path)})
        packet_counts["accepted"] += counts["accepted_packets"]
        packet_counts["pending"] += counts["pending_packets"]
        packet_counts["failed"] += counts["failed_packets"]

    original_files = sorted(args.source_reviews_dir.glob("batch00[123]_packet_*_PRIMARY.jsonl"))
    require(len(original_files) == 36, "expected 36 original PRIMARY files")
    original_index = {}
    original_hashes = {}
    for path in original_files:
        file_sha = sha256_file(path)
        original_hashes[path.name] = file_sha
        for row in read_jsonl(path):
            record_id = row["record_id"]
            require(record_id not in original_index, "original PRIMARY record ID duplicated")
            original_index[record_id] = {"context_sha256": row["context_sha256"],
                                         "source_primary_sha256": file_sha}
    require(len(original_index) == len(merged_ledger),
            "original PRIMARY row count differs from merged ledger")
    mtimes = [path.stat().st_mtime for path in original_files]
    audit_files = sorted(args.audit_dir.glob("batch001_AUDIT_*.jsonl"))
    require(audit_files, "blind audit source files absent")
    audit_rows = sum(len(read_jsonl(path)) for path in audit_files)
    require(audit_rows == 12, "expected 12 independent blind audit rereads")
    audit_hashes = [{"name": path.name, "sha256": sha256_file(path)} for path in audit_files]

    merged_by_id = {row["record_id"]: row for row in merged_ledger}
    require(len(merged_by_id) == len(merged_ledger), "merged record ID duplicated")
    overlay_document = json.loads(args.audit_overlay.read_text(encoding="utf-8"))
    audit_overlay = overlay_document["decisions"]
    require(len(audit_overlay) == 5, "expected five frozen audit adjudications")
    overlay_patch_count = retained_count = 0
    for decision in audit_overlay:
        record_id = decision["record_id"]
        require(record_id in merged_by_id and record_id in original_index,
                "audit adjudication has no merged PRIMARY record")
        require(decision["context_sha256"] == merged_by_id[record_id]["context_sha256"] ==
                original_index[record_id]["context_sha256"],
                "audit adjudication context binding differs")
        require(decision["source_primary_sha256"] ==
                original_index[record_id]["source_primary_sha256"],
                "audit adjudication original PRIMARY SHA differs")
        patches = decision["patches"]
        require(isinstance(patches, list) and patches,
                "audit adjudication has no asserted patch or retention")
        for patch in patches:
            require(pointer_value(merged_by_id[record_id], patch["path"]) == patch["new"],
                    "audit adjudication new value absent from merged ledger")
            overlay_patch_count += 1
        for retention in decision["retained_decisions"]:
            require(pointer_value(merged_by_id[record_id], retention["path"]) == retention["value"],
                    "audit retained value absent from merged ledger")
            retained_count += 1

    merged_ledger.sort(key=lambda row: row["context_sha256"])
    merged_reference.sort(key=lambda row: tuple(str(x) for x in row["canonical_key"]))
    status_counts = Counter(row["document_status"] for row in merged_ledger)
    unknown_contexts = {row["context_sha256"] for row in merged_ledger
                        if has_unknown_outcome(row)}
    unknown_ad_keys = sum(row["context_sha256"] in unknown_contexts
                          for row in merged_reference)
    require(len(merged_ledger) == 180 and len(merged_reference) == 180,
            "expected 180 new primary contexts and ad keys")

    root = args.output_root
    root.mkdir(parents=True, exist_ok=False)
    (root / "private").mkdir(mode=0o700)
    (root / "public").mkdir()
    ledger_output = root / "private" / "CONTEXT_LEDGER_PRIVATE.jsonl"
    reference_output = root / "private" / "AD_LEVEL_PRO_REFERENCE_PRIVATE.jsonl"
    write_jsonl_new(ledger_output, merged_ledger)
    write_jsonl_new(reference_output, merged_reference)
    result = {
        "version": VERSION,
        "status": "complete",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "slurm_job_id": job_id,
        "counts": {
            "new_primary_contexts": len(merged_ledger),
            "new_primary_ad_keys": len(merged_reference),
            "reviewed_full_contexts": status_counts["reviewed_full"],
            "reviewed_partial_contexts": status_counts["reviewed_partial"],
            "unresolved_document_contexts": status_counts["unresolved"],
            "contexts_with_any_unknown_outcome": len(unknown_contexts),
            "ad_keys_with_any_unknown_outcome": unknown_ad_keys,
            "accepted_packets": packet_counts["accepted"],
            "pending_packets": packet_counts["pending"],
            "failed_packets": packet_counts["failed"],
            "independent_blind_audit_rereads": audit_rows,
            "audit_adjudication_records_verified": len(audit_overlay),
            "audit_patch_values_verified": overlay_patch_count,
            "audit_retained_values_verified": retained_count,
        },
        "original_primary_authoring_window": {
            "file_count": len(original_files),
            "first_saved_utc": utc(min(mtimes)),
            "last_saved_utc": utc(max(mtimes)),
            "span_seconds": round(max(mtimes) - min(mtimes), 3),
            "meaning": "file save-time window only; not steady-state inference throughput",
            "file_sha256": [{"name": path.name, "sha256": original_hashes[path.name]}
                            for path in original_files],
        },
        "inputs": {
            "per_batch_checkpoints": receipt_hashes,
            "mechanical_patch_provenance_sha256": sha256_file(args.mechanical_provenance),
            "audit_overlay_sha256": sha256_file(args.audit_overlay),
            "blind_audit_files": audit_hashes,
            "merge_code_sha256": sha256_file(Path(__file__)),
        },
        "outputs": {"context_ledger_sha256": sha256_file(ledger_output),
                    "ad_level_reference_sha256": sha256_file(reference_output)},
        "merge_job_elapsed_seconds": round(time.monotonic() - started, 3),
        "actual_model_token_usage": "unavailable",
        "claim_boundary": "mechanical merged checkpoint only; no semantic accuracy certification or inference throughput claim",
    }
    receipt_output = root / "public" / "MERGED_RECEIPT_PUBLIC.json"
    write_json_new(receipt_output, result)
    print(json.dumps({"counts": result["counts"],
                      "receipt_sha256": sha256_file(receipt_output)}, sort_keys=True))


if __name__ == "__main__":
    main()
