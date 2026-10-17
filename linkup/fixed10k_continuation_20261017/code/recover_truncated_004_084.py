#!/usr/bin/env python3
"""Perform the single allowed, locator-bound recovery attempt for Batch004-084."""
import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
from pathlib import Path

import pyarrow.parquet as pq


KEYS = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def sha_text(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def jsonl(path):
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            if line.strip():
                yield json.loads(line)


def atomic(path, value, json_lines=False):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    with open(temp, "w", encoding="utf-8") as stream:
        if json_lines:
            for row in value:
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        else:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    os.chmod(str(temp), 0o600); os.replace(str(temp), str(path))


def normalizer(path):
    spec = importlib.util.spec_from_file_location("frozen_normalizer", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def normalize(module, text):
    result = module._normalize_with_flags(text)
    value = result[0] if isinstance(result, tuple) else result
    if not isinstance(value, str): raise RuntimeError("normalizer returned non-string")
    return value


def locate_row(parquet, index, columns):
    if index < 0 or index >= parquet.metadata.num_rows: raise RuntimeError("SOURCE_ROW outside source shard")
    offset = 0
    for rg in range(parquet.metadata.num_row_groups):
        size = parquet.metadata.row_group(rg).num_rows
        if index < offset + size:
            return parquet.read_row_group(rg, columns=columns).slice(index - offset, 1).to_pylist()[0], rg
        offset += size
    raise RuntimeError("SOURCE_ROW not found")


def main():
    p = argparse.ArgumentParser()
    for name in ("claim_manifest", "packet", "source_map", "normalizer", "attempt_marker", "receipt", "isolation_register"):
        p.add_argument("--" + name.replace("_", "-"), required=True)
    args = p.parse_args(); os.umask(0o077)
    marker = Path(args.attempt_marker)
    if marker.exists() or Path(args.receipt).exists():
        raise RuntimeError("recovery attempt already recorded; refusing a second attempt")
    atomic(marker, {"started_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "attempt_limit": 1})

    target_id = "fixed10k-prod-b004-084"
    manifest = next(x for x in jsonl(args.claim_manifest) if x["record_id"] == target_id)
    packet = next(x for x in jsonl(args.packet) if x["record_id"] == target_id)
    key = manifest["representative_canonical_key"]
    if packet["context_sha256"] != manifest["context_sha256"]:
        raise RuntimeError("packet/manifest context mismatch")
    mapping = {}
    for row in jsonl(args.source_map):
        name, path = row.get("SOURCE_FILE"), Path(row.get("path", ""))
        if not name or name in mapping or not path.is_absolute() or path.name != name:
            raise RuntimeError("invalid source locator")
        mapping[name] = path
    source = mapping.get(str(key["SOURCE_FILE"]))
    if source is None or not source.is_file(): raise RuntimeError("target source shard absent from frozen locator")
    parquet = pq.ParquetFile(source)
    raw, row_group = locate_row(parquet, int(key["SOURCE_ROW"]), ["JOB_HASH", "DESCRIPTION"])
    if str(raw["JOB_HASH"]) != str(key["JOB_HASH"]): raise RuntimeError("source row JOB_HASH mismatch")
    module = normalizer(args.normalizer)
    source_normalized = normalize(module, raw["DESCRIPTION"])
    packet_text = packet["full_document"]
    packet_hash, source_hash = sha_text(packet_text), sha_text(source_normalized)
    if packet_hash != packet["context_sha256"]: raise RuntimeError("packet context hash mismatch")
    more_text = len(source_normalized) > len(packet_text) and source_normalized != packet_text
    if source_hash == packet_hash:
        status = "source_truncated_unrecoverable"
    elif more_text:
        status = "source_recovery_candidate_context_change_requires_root"
    else:
        status = "source_text_differs_without_more_complete_recovery"
    isolation = [{
        "record_id": target_id,
        "normalized_context_sha256": packet_hash,
        "status": status,
        "work_queue_excluded": True,
        "ledger_changed": False,
        "original_queue_changed": False,
        "recovery_attempts": 1,
    }]
    atomic(args.isolation_register, isolation, json_lines=True)
    receipt = {
        "version": "fixed10k-truncated-004-084-recovery-v1",
        "status": status,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "attempts": 1,
        "method": "one source shard, one located SOURCE_ROW, exact JOB_HASH verification, frozen normalization",
        "inputs": {"claim_manifest_sha256": digest(args.claim_manifest), "packet_sha256": digest(args.packet),
                   "source_map_sha256": digest(args.source_map), "normalizer_sha256": digest(args.normalizer),
                   "source_shard_basename": source.name, "source_shard_sha256": digest(source)},
        "comparison": {"packet_normalized_sha256": packet_hash, "source_normalized_sha256": source_hash,
                       "same_normalized_text": source_hash == packet_hash,
                       "source_has_more_normalized_characters": more_text,
                       "packet_normalized_characters": len(packet_text),
                       "source_normalized_characters": len(source_normalized), "source_row_group_read": row_group},
        "disposition": "isolated from work queue; remains unfinished; ledger and predecessor queue unchanged",
    }
    atomic(args.receipt, receipt)


if __name__ == "__main__":
    main()
