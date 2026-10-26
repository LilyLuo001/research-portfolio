#!/usr/bin/env python3
"""Create a private, cumulative checkpoint from received Formal800 Pro reviews.

This is a mechanical binding step. It calls validate_reviews.py unchanged and
never infers, repairs, or replaces a reviewer's semantic fields. Run on SCNet
under a real SLURM job, with a new --output-root for every snapshot.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

from validate_reviews import read_jsonl, sha256_file, validate_packet


VERSION = "corpus-pro-review-checkpoint-v1"
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
OUTCOME_FAMILIES = ("experience_outcomes", "entry_outcomes", "responsibility_outcomes")


def packet_stem(name: str) -> str:
    require(name.endswith(".jsonl"), "invalid packet filename")
    return name[:-6]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def write_json_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")


def write_jsonl_new(path: Path, rows: list[dict]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    os.chmod(path, 0o600)


def checked_private_manifest(path: Path, packets: dict[str, dict]) -> dict[str, dict]:
    manifest = {}
    canonical_keys = set()
    for row in read_jsonl(path):
        context = row.get("context_sha256")
        record_id = row.get("record_id")
        require(isinstance(context, str) and HEX64.fullmatch(context) is not None,
                "invalid private manifest context SHA")
        require(record_id == "corpus-pro-" + context, "invalid private manifest record ID")
        require(context not in manifest, "duplicate private manifest context SHA")
        keys = row.get("canonical_keys")
        require(isinstance(keys, list) and bool(keys), "private manifest has no canonical keys")
        for key in keys:
            require(isinstance(key, list) and len(key) == 4,
                    "invalid private manifest canonical key")
            frozen = tuple(str(x) for x in key)
            require(frozen not in canonical_keys, "duplicate private manifest canonical key")
            canonical_keys.add(frozen)
        manifest[context] = row
    all_contexts = [row["context_sha256"] for packet in packets.values() for row in packet["rows"]]
    require(len(all_contexts) == len(set(all_contexts)), "context repeated across packets")
    packet_contexts = set(all_contexts)
    require(set(manifest) == packet_contexts, "private manifest and packets differ")
    for packet in packets.values():
        for row in packet["rows"]:
            require(manifest[row["context_sha256"]]["record_id"] == row["record_id"],
                    "private manifest record ID and packet differ")
    return manifest


def read_prior(path: Path | None, current: dict[str, dict], manifest_sha: str,
               schema_sha: str, validator_sha: str, dispatcher_sha: str) -> dict[str, dict]:
    if path is None:
        return {}
    receipt_path = path / "public" / "CHECKPOINT_RECEIPT_PUBLIC.json"
    prior = json.loads(receipt_path.read_text(encoding="utf-8"))
    require(prior.get("version") == VERSION, "prior checkpoint version differs")
    inputs = prior.get("inputs", {})
    for name, actual in (("packet_manifest_sha256", manifest_sha),
                         ("schema_sha256", schema_sha),
                         ("validator_sha256", validator_sha),
                         ("dispatcher_sha256", dispatcher_sha)):
        require(inputs.get(name) == actual, "prior checkpoint " + name + " differs")
    accepted = {}
    for item in prior.get("packets", []):
        if item.get("status") != "accepted":
            continue
        name = item["name"]
        require(name in current, "previously accepted packet is absent")
        require(item["packet_sha256"] == current[name]["sha256"],
                "previously accepted packet changed: " + name)
        validated = path / "private" / packet_stem(name) / "VALIDATED_PRIVATE.jsonl"
        errors = path / "private" / packet_stem(name) / "ERRORS_PRIVATE.jsonl"
        validator_receipt = path / "public" / packet_stem(name) / "VALIDATION_RECEIPT_PUBLIC.json"
        for file, field in ((validated, "validated_sha256"),
                            (errors, "errors_sha256"),
                            (validator_receipt, "validator_receipt_sha256")):
            require(file.is_file() and sha256_file(file) == item[field],
                    "prior accepted output changed: " + name)
        accepted[name] = item
    return accepted


def summary_counts(rows: list[dict]) -> dict:
    counts = Counter({"document_status." + status: 0 for status in
                      ("reviewed_full", "reviewed_partial", "unresolved")})
    counts.update({"technology_inventory_status." + status: 0 for status in
                   ("explicit_mentions_recorded", "not_mentioned_after_full_review", "unknown")})
    dimensions = {
        "experience_outcomes": ("general_work", "occupation_task", "industry_domain", "tool_specific"),
        "entry_outcomes": ("explicit_no_experience", "explicit_new_graduate",
                           "current_student_internship", "explicit_junior_or_entry_label"),
        "responsibility_outcomes": ("independent_judgment", "client_ownership",
                                    "people_supervision", "training_mentoring"),
    }
    counts.update({family + "." + dim + "." + status: 0
                   for family, dims in dimensions.items() for dim in dims
                   for status in ("present", "not_mentioned", "unknown")})
    for row in rows:
        counts["document_status." + row["document_status"]] += 1
        counts["technology_inventory_status." + row["technology_inventory_status"]] += 1
        for family in OUTCOME_FAMILIES:
            for dimension, value in row[family].items():
                counts[family + "." + dimension + "." + value] += 1
    return dict(sorted(counts.items()))


def has_unknown_outcome(row: dict) -> bool:
    return (row["technology_inventory_status"] == "unknown" or
            any(value == "unknown" for family in OUTCOME_FAMILIES
                for value in row[family].values()))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-dir", type=Path, required=True,
                        help="batch directory containing private/ and public/")
    parser.add_argument("--reviews-dir", type=Path, required=True,
                        help="directory containing batchNNN_packet_NNNN_PRIMARY.jsonl")
    parser.add_argument("--output-root", type=Path, required=True,
                        help="new checkpoints/<SLURM_JOB_ID> directory")
    parser.add_argument("--dispatcher-file", type=Path, required=True,
                        help="frozen model/agent dispatcher provenance file")
    parser.add_argument("--legacy-manifest-sha-file", type=Path,
                        help="independently frozen batch001 manifest SHA JSON; required only for old receipt")
    parser.add_argument("--prior-checkpoint", type=Path,
                        help="previous checkpoint whose accepted packet outputs may be reused")
    args = parser.parse_args()
    started = time.monotonic()
    job_id = os.environ.get("SLURM_JOB_ID")
    require(bool(job_id) and job_id.isdecimal(), "actual SLURM_JOB_ID required")
    require(args.output_root.name == job_id, "output-root must end in SLURM_JOB_ID")
    require(args.output_root.parent.name == "checkpoints",
            "output-root must be checkpoints/<SLURM_JOB_ID>")
    require(args.batch_dir.name.startswith("batch"), "batch-dir must be a named batch")
    code_dir = Path(__file__).resolve().parent
    schema = code_dir / "FORMAL800_REVIEW_SCHEMA.json"
    validator = code_dir / "validate_reviews.py"
    for path in (schema, validator, args.dispatcher_file):
        require(path.is_file(), "required source is absent: " + str(path))
    schema_sha, validator_sha = sha256_file(schema), sha256_file(validator)
    dispatcher_sha = sha256_file(args.dispatcher_file)

    private_batch = args.batch_dir / "private"
    public_batch = args.batch_dir / "public"
    prep_receipt_path = public_batch / "PACKET_PREPARATION_PUBLIC.json"
    manifest_path = private_batch / "PACKET_MANIFEST_PRIVATE.jsonl"
    prep = json.loads(prep_receipt_path.read_text(encoding="utf-8"))
    require(prep.get("status") == "prepared_not_reviewed", "unexpected preparation status")
    manifest_sha = sha256_file(manifest_path)
    receipt_manifest_sha = prep.get("packet_manifest_sha256")
    manifest_sha_source = {"kind": "prepared_public_receipt",
                           "source_sha256": sha256_file(prep_receipt_path)}
    if receipt_manifest_sha is None:
        require(args.batch_dir.name == "batch001", "new batch receipt lacks manifest SHA")
        require(args.legacy_manifest_sha_file is not None,
                "batch001 needs independent frozen manifest SHA file")
        frozen_path = args.legacy_manifest_sha_file
        require(frozen_path.resolve() != manifest_path.resolve(),
                "legacy SHA source cannot be the private manifest itself")
        frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
        receipt_manifest_sha = frozen.get("batch001_manifest_sha256")
        provenance = frozen.get("batch001_manifest_sha_source")
        require(isinstance(provenance, str) and bool(provenance.strip()),
                "legacy manifest SHA source provenance missing")
        manifest_sha_source = {"kind": "independent_frozen_file",
                               "source_sha256": sha256_file(frozen_path),
                               "provenance": provenance}
    require(isinstance(receipt_manifest_sha, str) and
            HEX64.fullmatch(receipt_manifest_sha) is not None and
            receipt_manifest_sha == manifest_sha, "prepared manifest SHA mismatch")
    packet_meta = prep.get("packet_files")
    require(isinstance(packet_meta, list) and packet_meta, "preparation lists no packets")
    packets = {}
    for item in packet_meta:
        name = item["name"]
        require(re.fullmatch(r"packet_\d{4}\.jsonl", name) is not None,
                "invalid prepared packet name")
        require(name not in packets, "duplicate prepared packet")
        path = private_batch / name
        require(path.is_file() and sha256_file(path) == item["sha256"],
                "prepared packet SHA mismatch: " + name)
        rows = read_jsonl(path)
        by_id = validate_packet(rows)
        require(len(rows) == item["records"], "prepared packet count mismatch: " + name)
        require(all(row["assignment"]["packet_id"] == path.stem and
                    row["assignment"]["reviewer_role"] == "primary" for row in rows),
                "unexpected packet assignment: " + name)
        packets[name] = {"path": path, "sha256": item["sha256"],
                         "records": len(by_id), "rows": rows}
    manifest = checked_private_manifest(manifest_path, packets)
    require(len(manifest) == prep.get("prepared_contexts"),
            "preparation context count and private manifest differ")
    require(sum(len(row["canonical_keys"]) for row in manifest.values()) == prep.get("prepared_ad_keys"),
            "preparation ad-key count and private manifest differ")
    prior = read_prior(args.prior_checkpoint, packets, manifest_sha, schema_sha, validator_sha,
                       dispatcher_sha)

    # Refuse input changes before creating the new snapshot. Missing new review
    # files remain pending; an accepted review cannot disappear or change.
    review_paths = {}
    for name in packets:
        review_name = args.batch_dir.name + "_" + packet_stem(name) + "_PRIMARY.jsonl"
        path = args.reviews_dir / review_name
        review_paths[name] = path if path.is_file() else None
        if name in prior:
            require(path.is_file(), "previously accepted review is absent: " + name)
            require(sha256_file(path) == prior[name]["review_sha256"],
                    "previously accepted review changed: " + name)
    unexpected = sorted(p.name for p in args.reviews_dir.glob(args.batch_dir.name + "_packet_*_PRIMARY.jsonl")
                        if p.name not in {x.name for x in review_paths.values() if x is not None})
    require(not unexpected, "unexpected primary review files in batch: " + ", ".join(unexpected))

    root = args.output_root
    root.mkdir(parents=True, exist_ok=False)
    (root / "private").mkdir(mode=0o700)
    (root / "public").mkdir()
    packet_status = []
    accepted_rows = []
    for name, packet in sorted(packets.items()):
        stem = packet_stem(name)
        review = review_paths[name]
        item = {"name": name, "packet_sha256": packet["sha256"],
                "expected_records": packet["records"]}
        if review is None:
            item["status"] = "pending"
            packet_status.append(item)
            continue
        item["review_sha256"] = sha256_file(review)
        private_out, public_out = root / "private" / stem, root / "public" / stem
        private_out.mkdir(mode=0o700)
        public_out.mkdir()
        validated = private_out / "VALIDATED_PRIVATE.jsonl"
        errors = private_out / "ERRORS_PRIVATE.jsonl"
        receipt = public_out / "VALIDATION_RECEIPT_PUBLIC.json"
        if name in prior:
            old_private = args.prior_checkpoint / "private" / stem
            old_public = args.prior_checkpoint / "public" / stem
            shutil.copyfile(old_private / validated.name, validated)
            shutil.copyfile(old_private / errors.name, errors)
            shutil.copyfile(old_public / receipt.name, receipt)
            os.chmod(validated, 0o600)
            os.chmod(errors, 0o600)
            item["reused_prior_validation"] = True
            return_code = 0
        else:
            command = [sys.executable, str(validator), "--packet", str(packet["path"]),
                       "--reviews", str(review), "--schema", str(schema),
                       "--private-validated", str(validated),
                       "--private-errors", str(errors), "--public-receipt", str(receipt),
                       "--expected-records", str(packet["records"])]
            result = subprocess.run(command, text=True, capture_output=True)
            return_code = result.returncode
            if result.stdout or result.stderr:
                write_json_new(private_out / "VALIDATOR_PROCESS_PRIVATE.json",
                               {"return_code": return_code, "stdout": result.stdout,
                                "stderr": result.stderr})
            item["reused_prior_validation"] = False
        if not all(x.is_file() for x in (validated, errors, receipt)):
            item.update(status="failed", failure_kind="validator_process_failure",
                        validator_return_code=return_code)
            packet_status.append(item)
            continue
        validator_receipt = json.loads(receipt.read_text(encoding="utf-8"))
        valid_rows = read_jsonl(validated)
        error_rows = read_jsonl(errors)
        item.update(validated_records=len(valid_rows), error_entries=len(error_rows),
                    validated_sha256=sha256_file(validated),
                    errors_sha256=sha256_file(errors),
                    validator_receipt_sha256=sha256_file(receipt),
                    validator_return_code=return_code)
        if return_code == 0 and validator_receipt.get("status") == "pass" and not error_rows \
                and len(valid_rows) == packet["records"]:
            item["status"] = "accepted"
            accepted_rows.extend(valid_rows)
        else:
            item["status"] = "failed"
            item["failure_kind"] = "private_validation_errors"
        packet_status.append(item)

    # Only fully accepted packets enter cumulative outputs. Context and ad keys
    # come solely from the frozen private manifest and are joined by exact SHA.
    seen_contexts, seen_ad_keys = set(), set()
    ledger, ad_reference = [], []
    for review in accepted_rows:
        context = review["context_sha256"]
        require(context in manifest and context not in seen_contexts,
                "accepted context missing or duplicated in manifest")
        seen_contexts.add(context)
        keys = manifest[context]["canonical_keys"]
        ledger.append({**review, "canonical_keys": keys})
        for key in keys:
            frozen = tuple(str(x) for x in key)
            require(frozen not in seen_ad_keys, "duplicate accepted canonical key")
            seen_ad_keys.add(frozen)
            ad_reference.append({"canonical_key": key, **review})
    ledger.sort(key=lambda x: x["context_sha256"])
    ad_reference.sort(key=lambda x: tuple(str(v) for v in x["canonical_key"]))
    ledger_path = root / "private" / "CONTEXT_LEDGER_PRIVATE.jsonl"
    reference_path = root / "private" / "AD_LEVEL_PRO_REFERENCE_PRIVATE.jsonl"
    write_jsonl_new(ledger_path, ledger)
    write_jsonl_new(reference_path, ad_reference)
    counts = Counter(item["status"] for item in packet_status)
    unknown_contexts = {row["context_sha256"] for row in accepted_rows
                        if has_unknown_outcome(row)}
    unknown_ad_keys = sum(len(manifest[context]["canonical_keys"])
                          for context in unknown_contexts)
    document_counts = Counter(row["document_status"] for row in accepted_rows)
    public_packets = []
    for item in packet_status:
        # Packet names and hashes are public; record IDs, quote text and errors are private.
        public_packets.append(item)
    receipt_value = {
        "version": VERSION,
        "status": "complete" if counts["accepted"] == len(packets) else "in_progress",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "slurm_job_id": job_id,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "inputs": {
            "prepared_receipt_sha256": sha256_file(prep_receipt_path),
            "packet_manifest_sha256": manifest_sha,
            "packet_manifest_sha_source": manifest_sha_source,
            "schema_sha256": schema_sha,
            "validator_sha256": validator_sha,
            "dispatcher_sha256": dispatcher_sha,
            "checkpoint_code_sha256": sha256_file(Path(__file__)),
            "prior_checkpoint_receipt_sha256": (
                sha256_file(args.prior_checkpoint / "public" / "CHECKPOINT_RECEIPT_PUBLIC.json")
                if args.prior_checkpoint else None),
        },
        "counts": {
            "prepared_packets": len(packets), "accepted_packets": counts["accepted"],
            "pending_packets": counts["pending"], "failed_packets": counts["failed"],
            "prepared_contexts": len(manifest), "accepted_contexts": len(ledger),
            "accepted_ad_keys": len(ad_reference),
            "reviewed_full_contexts": document_counts["reviewed_full"],
            "reviewed_partial_contexts": document_counts["reviewed_partial"],
            "unresolved_document_contexts": document_counts["unresolved"],
            "contexts_with_any_unknown_outcome": len(unknown_contexts),
            "ad_keys_with_any_unknown_outcome": unknown_ad_keys,
            "reused_accepted_packets": sum(x.get("reused_prior_validation", False)
                                           for x in packet_status),
        },
        "field_status_counts": summary_counts(accepted_rows),
        "packets": public_packets,
        "outputs": {"context_ledger_sha256": sha256_file(ledger_path),
                    "ad_level_reference_sha256": sha256_file(reference_path)},
        "claim_boundary": "mechanical schema, binding and exact-quote validation; no semantic accuracy claim",
    }
    write_json_new(root / "public" / "CHECKPOINT_RECEIPT_PUBLIC.json", receipt_value)
    print(json.dumps({"status": receipt_value["status"], "counts": receipt_value["counts"],
                      "receipt_sha256": sha256_file(root / "public" / "CHECKPOINT_RECEIPT_PUBLIC.json")},
                     sort_keys=True))


if __name__ == "__main__":
    main()
