#!/usr/bin/env python3
"""Claim the first 100 frozen queue contexts and build five private review packets.

This scheduled program only binds already-frozen inputs.  It does not make or
modify semantic judgments.
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

import pyarrow.parquet as pq


VERSION = "fixed10k-semantic-production-batch001-prep-v1"
KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
FAMILIES = (
    "technology_category_and_role", "experience_object", "experience_strength",
    "experience_literal_years", "qualification_conditions_and_alternatives",
    "entry_wording_and_scope", "current_responsibility_subject_and_relation",
)
QUEUE_SHA = "42741690264ada733f19da8991db5617d64b5d75577db260476cf9f0c1803428"
LEDGER_SHA = "481cf6f844cae9377d3be4d1ce51a25fdcab277e1d9e8280957615946d1e3756"
FRAME_SHA = "e6083ccacbdfe5a64548168a22ceb11fdce9d6d4bb89943a11f4bae54a17de35"
NORMALIZER_SHA = "336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd"
COVERAGE_RECEIPT_SHA = "4828cb68cab7a78dab112e6a80f37afdef0eb6f5da693d7989fc59495979a588"
COVERAGE_CODE_SHA = "4697d56d9660cdd7ea5c26505ab3d917466c6f67d2552c5d39a0a7ceee1e9110"
ALLOWED_REQUIRED = {"partial", "candidate_only", "source_unavailable"}


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
            if not line.strip(): raise RuntimeError("blank JSONL line {}:{}".format(path, number))
            value = json.loads(line)
            if not isinstance(value, dict): raise RuntimeError("non-object JSONL row")
            rows.append(value)
    return rows


def atomic_json(path, value, mode=0o600):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(str(temp), mode); os.replace(str(temp), str(path))


def atomic_jsonl(path, rows, mode=0o600):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    with open(temp, "w", encoding="utf-8") as stream:
        for row in rows: stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    os.chmod(str(temp), mode); os.replace(str(temp), str(path))


def load_normalizer(path):
    if sha_file(path) != NORMALIZER_SHA: raise RuntimeError("normalizer SHA mismatch")
    spec = importlib.util.spec_from_file_location("batch001_normalizer", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def normalize(module, text):
    result = module._normalize_with_flags(text)
    value = result[0] if isinstance(result, tuple) else result
    if not isinstance(value, str): raise RuntimeError("normalizer returned non-string")
    return value


def canonical_key(value):
    return tuple(value[name] for name in KEY)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--queue", required=True); p.add_argument("--ledger", required=True)
    p.add_argument("--coverage-receipt", required=True); p.add_argument("--frame", required=True)
    p.add_argument("--normalizer", required=True); p.add_argument("--formal-schema", required=True)
    p.add_argument("--formal-instructions", required=True); p.add_argument("--formal-validator", required=True)
    p.add_argument("--private-output", required=True); p.add_argument("--public-receipt", required=True)
    p.add_argument("--repository-commit", default="d3e508b")
    args = p.parse_args(); os.umask(0o077)
    expected = {"queue": QUEUE_SHA, "ledger": LEDGER_SHA, "coverage_receipt": COVERAGE_RECEIPT_SHA,
                "frame": FRAME_SHA, "normalizer": NORMALIZER_SHA}
    paths = {name: getattr(args, name) for name in expected}
    hashes = {name: sha_file(path) for name, path in paths.items()}
    for name, digest in expected.items():
        if hashes[name] != digest: raise RuntimeError("frozen input SHA mismatch: " + name)
    coverage = json.load(open(args.coverage_receipt, encoding="utf-8"))
    if coverage.get("status") != "pass" or coverage.get("code", {}).get("sha256") != COVERAGE_CODE_SHA:
        raise RuntimeError("coverage receipt/code binding mismatch")
    if coverage.get("outputs", {}).get("private_queue", {}).get("sha256") != QUEUE_SHA:
        raise RuntimeError("coverage receipt does not bind queue")
    if coverage.get("counts", {}).get("required_new_review_contexts") != 6899:
        raise RuntimeError("coverage receipt queue count mismatch")

    queue_all = read_jsonl(args.queue)
    if len(queue_all) != 6899: raise RuntimeError("frozen queue row count mismatch")
    claimed = queue_all[:100]
    if len({row["normalized_context_sha256"] for row in claimed}) != 100:
        raise RuntimeError("first100 queue contexts are not unique")
    for position, row in enumerate(claimed, 1):
        required = row.get("required_new_review_families")
        if not isinstance(required, list) or not required or len(set(required)) != len(required):
            raise RuntimeError("queue row lacks unique required families")
        if any(f not in FAMILIES or row["family_status"].get(f) not in ALLOWED_REQUIRED for f in required):
            raise RuntimeError("queue required family violates frozen status contract")
        if any(row["family_status"].get(f) == "unknown_or_conflict" for f in required):
            raise RuntimeError("reviewed uncertainty entered production claim")

    representative = {canonical_key(row["representative_canonical_key"]): row for row in claimed}
    if len(representative) != 100: raise RuntimeError("representative keys are not unique")
    needed = set(representative); frame_rows = {}
    parquet = pq.ParquetFile(args.frame)
    columns = list(KEY) + ["exact_text_sha256", "original_text"]
    for batch in parquet.iter_batches(columns=columns, batch_size=2048):
        for row in batch.to_pylist():
            key = tuple(row[name] for name in KEY)
            if key in needed:
                if key in frame_rows: raise RuntimeError("duplicate representative frame key")
                if sha_text(row["original_text"]) != row["exact_text_sha256"]: raise RuntimeError("frame text hash mismatch")
                frame_rows[key] = row
    if set(frame_rows) != needed: raise RuntimeError("claimed representative key absent from frame")

    ledger_index = collections.defaultdict(dict)
    for row in read_jsonl(args.ledger):
        key = canonical_key(row["canonical_key"])
        if key in needed:
            family = row["field_family"]
            if family in ledger_index[key]: raise RuntimeError("duplicate ledger family")
            ledger_index[key][family] = row
    if any(set(ledger_index[key]) != set(FAMILIES) for key in needed):
        raise RuntimeError("representative ledger does not contain seven families")

    normalizer = load_normalizer(args.normalizer)
    outdir = Path(args.private_output); packet_dir = outdir / "packets"; template_dir = outdir / "templates"
    manifest = []; packets = [[] for _ in range(5)]; templates = [[] for _ in range(5)]
    required_counts = collections.Counter(); required_combinations = collections.Counter()
    existing_counts = collections.Counter(); unknown_projection_contexts = 0
    for queue_position, qrow in enumerate(claimed, 1):
        key = canonical_key(qrow["representative_canonical_key"]); frame = frame_rows[key]
        normalized = normalize(normalizer, frame["original_text"])
        context = sha_text(normalized)
        if context != qrow["normalized_context_sha256"]: raise RuntimeError("queue/frame normalized context mismatch")
        ledger = ledger_index[key]
        projections = []
        has_unknown = False
        for family in FAMILIES:
            item = ledger[family]
            if item["normalized_context_sha256"] != context or item["status"] != qrow["family_status"][family]:
                raise RuntimeError("queue/ledger family binding mismatch")
            existing_counts[(family, item["status"])] += 1
            has_unknown = has_unknown or item["status"] == "unknown_or_conflict"
            projections.append({"field_family": family, "status": item["status"],
                                "structured_value": item.get("structured_value"),
                                "resolution_rule": item.get("resolution_rule"),
                                "historical_source_exposure": item.get("historical_source_exposure", []),
                                "historical_development_evaluation_exposure": bool(item.get("historical_development_evaluation_exposure"))})
        unknown_projection_contexts += has_unknown
        required = qrow["required_new_review_families"]
        required_counts.update(required); required_combinations["|".join(required)] += 1
        packet_number = (queue_position - 1) // 20 + 1; packet_position = (queue_position - 1) % 20 + 1
        record_id = "fixed10k-prod-b001-{:03d}".format(queue_position)
        assignment = {"packet_id": "fixed10k-prod-b001-p{:02d}".format(packet_number),
                      "reviewer_role": "primary", "provenance": VERSION,
                      "queue_position_1based": queue_position, "packet_position_1based": packet_position}
        packet = {"schema_version": VERSION, "record_id": record_id, "context_sha256": context,
                  "full_document": normalized, "assignment": assignment,
                  "required_new_review_families": required,
                  "existing_family_projections": projections}
        template = {"record_id": record_id, "context_sha256": context, "document_status": None,
                    "reviewed_families": required,
                    "family_updates": [{"family": family, "value": None} for family in required],
                    "unresolved_notes": []}
        packets[packet_number - 1].append(packet); templates[packet_number - 1].append(template)
        manifest.append({"queue_position_1based": queue_position, "packet_number": packet_number,
                         "packet_position_1based": packet_position, "record_id": record_id,
                         "context_sha256": context, "representative_canonical_key": qrow["representative_canonical_key"],
                         "required_new_review_families": required})

    packet_receipts = []
    for index in range(5):
        packet_path = packet_dir / "PACKET_{:02d}_PRIVATE.jsonl".format(index + 1)
        template_path = template_dir / "REVIEW_TEMPLATE_{:02d}_PRIVATE.jsonl".format(index + 1)
        atomic_jsonl(packet_path, packets[index]); atomic_jsonl(template_path, templates[index])
        packet_receipts.append({"packet_number": index + 1, "rows": 20,
                                "packet_path": str(packet_path), "packet_sha256": sha_file(packet_path),
                                "template_path": str(template_path), "template_sha256": sha_file(template_path)})
    manifest_path = outdir / "CLAIM_MANIFEST_PRIVATE.jsonl"; atomic_jsonl(manifest_path, manifest)
    source_artifacts = {name: {"path": path, "sha256": sha_file(path)} for name, path in
                        (("formal_schema", args.formal_schema), ("formal_instructions", args.formal_instructions),
                         ("formal_validator", args.formal_validator))}
    receipt = {"version": VERSION, "status": "pass", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
               "scheduler": {"job_id": os.environ.get("SLURM_JOB_ID"), "host": platform.node()},
               "repository_commit": args.repository_commit,
               "inputs": {name: {"path": paths[name], "sha256": hashes[name]} for name in paths},
               "reused_formal_artifacts": source_artifacts,
               "claim": {"rule": "first100 rows in frozen queue order", "contexts": 100, "packets": 5,
                         "rows_per_packet": 20, "queue_positions": [1, 100],
                         "reviewed_unknown_families_claimed": 0,
                         "contexts_with_preserved_unknown_projection": unknown_projection_contexts},
               "required_family_counts": {k: required_counts[k] for k in FAMILIES},
               "required_family_combinations": dict(sorted(required_combinations.items())),
               "existing_family_status_counts": {"{}|{}".format(k[0], k[1]): v for k, v in sorted(existing_counts.items())},
               "outputs": {"private_manifest": {"path": str(manifest_path), "rows": 100, "sha256": sha_file(manifest_path)},
                           "packets": packet_receipts},
               "checks": {"queue_hash_pinned": True, "coverage_receipt_and_code_pinned": True,
                          "queue_order_preserved": True, "five_packets_of_twenty": True,
                          "full_normalized_document_hash_exact": True, "representative_frame_key_exact": True,
                          "seven_existing_family_projections_present": True,
                          "only_partial_missing_source_unavailable_claimed": True,
                          "reviewed_unknown_not_claimed": True},
               "claim_boundary": "mechanical preparation only; no semantic reading, new sample, taxonomy, parser, or reviewed-unknown re-entry"}
    atomic_json(args.public_receipt, receipt, mode=0o644)


if __name__ == "__main__":
    main()
