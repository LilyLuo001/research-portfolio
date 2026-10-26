#!/usr/bin/env python3
"""Prepare a bounded next packet from the accepted full-corpus catalog.

Run only as a scheduled SCNet job. This reads complete raw descriptions for
review transport; it makes no semantic judgments and does not change scope.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re

import pyarrow.parquet as pq

KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
CATALOG_SHA = "4265e2469a8d3d35a769faad9c163823b0df32364f88061db5ecc5e131b1eb1e"
REFERENCE_SHA = "733875307de475a296e3da4531ad64ba99351f5e2dff109b757ad80b80b34adb"
NORMALIZER_SHA = "336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd"
SHARDS = 2464
ADS = 204_774_035
VERSION = "corpus-pro-full-context-packets-v1"


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def load_normalizer(path: Path):
    if sha(path) != NORMALIZER_SHA:
        raise RuntimeError("pinned legacy_v5_frozen.py SHA mismatch")
    spec = importlib.util.spec_from_file_location("corpus_pinned_legacy_v5", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._normalize_with_flags


def key(row):
    values = tuple(row[k] for k in KEY)
    if any(x is None for x in values):
        raise RuntimeError("null canonical key")
    return [str(values[0]), str(values[1]), int(values[2]), int(values[3])]


def rows(path: Path, columns, batch_size=8192):
    parquet = pq.ParquetFile(path)
    if not set(columns) <= set(parquet.schema_arrow.names):
        raise RuntimeError("required columns absent from " + str(path))
    offset = 0
    for batch in parquet.iter_batches(batch_size=batch_size, columns=columns):
        data = batch.to_pydict()
        for i in range(batch.num_rows):
            yield offset + i, {name: data[name][i] for name in columns}
        offset += batch.num_rows


def resolve_raw(source_file: str, roots: list[Path]) -> Path | None:
    # SOURCE_FILE is a canonical locator, never a JOB_HASH search target.
    source = Path(source_file)
    if source.is_absolute() or ".." in source.parts:
        raise RuntimeError("unsafe SOURCE_FILE locator")
    matches = []
    for root in roots:
        candidate = root / source
        if candidate.is_file() and candidate not in matches:
            matches.append(candidate)
    if len(matches) > 1:
        raise RuntimeError("ambiguous raw source locator: " + source_file)
    return matches[0] if matches else None


class RawReader:
    def __init__(self, path: Path, body_column: str):
        self.path = path
        self.parquet = pq.ParquetFile(path)
        self.body_column = body_column
        if not {body_column, "JOB_HASH"} <= set(self.parquet.schema_arrow.names):
            raise RuntimeError("raw file missing body/JOB_HASH: " + str(path))
        self.ranges = []
        start = 0
        for index in range(self.parquet.num_row_groups):
            end = start + self.parquet.metadata.row_group(index).num_rows
            self.ranges.append((start, end, index))
            start = end
        self.cached_group = None
        self.cached_table = None

    def get(self, source_row: int, expected_hash: str):
        if source_row < 0 or source_row >= self.parquet.metadata.num_rows:
            raise RuntimeError("SOURCE_ROW outside raw file: " + str(self.path))
        for begin, end, group in self.ranges:
            if begin <= source_row < end:
                if self.cached_group != group:
                    self.cached_table = self.parquet.read_row_group(
                        group, columns=[self.body_column, "JOB_HASH"]
                    )
                    self.cached_group = group
                local = source_row - begin
                actual_hash = self.cached_table.column("JOB_HASH")[local].as_py()
                if str(actual_hash) != expected_hash:
                    raise RuntimeError("raw JOB_HASH mismatch: " + str(self.path))
                return self.cached_table.column(self.body_column)[local].as_py()
        raise AssertionError("raw row group locator failed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--prior-manifests", type=Path, nargs="*", default=[])
    parser.add_argument("--raw-roots", type=Path, nargs="+", required=True)
    parser.add_argument("--normalizer", type=Path, required=True)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    parser.add_argument("--body-column", default="DESCRIPTION")
    parser.add_argument("--count", type=int, default=60)
    parser.add_argument("--start-shard", type=int, default=0)
    parser.add_argument("--start-row", type=int, default=0)
    args = parser.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("scheduled SCNet compute required")
    if args.count < 1 or args.start_shard < 0 or args.start_row < 0:
        raise RuntimeError("invalid count or cursor")
    private = args.private_output.resolve()
    public = args.public_output.resolve()
    if "private" not in private.parts or private == public or private in public.parents or public in private.parents:
        raise RuntimeError("private/public destinations must be distinct")
    if private.exists() or public.exists():
        raise RuntimeError("existing output guard; use new destinations for each run")
    if sha(args.catalog) != CATALOG_SHA or sha(args.reference) != REFERENCE_SHA:
        raise RuntimeError("accepted catalog/reference SHA mismatch")
    normalize = load_normalizer(args.normalizer)
    catalog = [json.loads(line) for line in args.catalog.read_text().splitlines() if line.strip()]
    if len(catalog) != SHARDS or len({x["shard_id"] for x in catalog}) != SHARDS:
        raise RuntimeError("accepted catalog shard gate")
    if sum(int(x["ad_rows"]) for x in catalog) != ADS:
        raise RuntimeError("accepted canonical-US-ad denominator gate")
    if args.start_shard >= SHARDS or args.start_row >= int(catalog[args.start_shard]["ad_rows"]):
        raise RuntimeError("start cursor outside catalog")
    reference_hashes = set()
    reference_keys = {}
    reference_context_keys = {}
    for _, row in rows(args.reference, list(KEY) + ["normalized_context_sha256"]):
        canonical_key = tuple(key(row))
        context = row["normalized_context_sha256"]
        if not isinstance(context, str) or len(context) != 64:
            raise RuntimeError("invalid accepted reference context hash")
        if canonical_key in reference_keys:
            raise RuntimeError("duplicate accepted reference canonical key")
        reference_keys[canonical_key] = context
        reference_hashes.add(context)
        reference_context_keys.setdefault(context, []).append(list(canonical_key))
    if len(reference_keys) != 10_000:
        raise RuntimeError("accepted reference key count gate")

    prior_contexts = {}
    prior_manifest_hashes = []
    for manifest in args.prior_manifests:
        manifest_hash = sha(manifest)
        prior_manifest_hashes.append(manifest_hash)
        with manifest.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                item = json.loads(line)
                context = item.get("context_sha256")
                record_id = item.get("record_id")
                if (not isinstance(context, str) or
                        re.fullmatch(r"[0-9a-f]{64}", context) is None or
                        record_id != "corpus-pro-" + context):
                    raise RuntimeError("invalid prior private packet manifest")
                if context in reference_hashes:
                    raise RuntimeError("prior packet overlaps accepted reference context")
                if context in prior_contexts:
                    if prior_contexts[context]["record_id"] != record_id:
                        raise RuntimeError("conflicting prior packet record IDs")
                    continue
                prior_contexts[context] = {"record_id": record_id,
                                           "source_manifest_sha256": manifest_hash}

    selected = {}
    counts = Counter()
    quarantined = []
    reuse_bindings = []
    unreadable = []
    cursor = {"shard_ordinal": args.start_shard, "row_offset": args.start_row}
    for ordinal in range(args.start_shard, SHARDS):
        item = catalog[ordinal]
        path = Path(item["ad_path"])
        if not path.is_file():
            raise RuntimeError("catalog ad shard unavailable: " + str(path))
        narrow = pq.ParquetFile(path)
        if narrow.metadata.num_rows != int(item["ad_rows"]) or path.stat().st_size != int(item["ad_bytes"]):
            raise RuntimeError("catalog shard footer/size drift: " + str(path))
        start = args.start_row if ordinal == args.start_shard else 0
        # Preflight every SOURCE_FILE before consuming any ad in this shard.
        sources = set()
        for _, row in rows(path, ["SOURCE_FILE"]):
            sources.add(row["SOURCE_FILE"])
        raw_paths = {source: resolve_raw(source, args.raw_roots) for source in sources}
        missing = sorted(source for source, raw in raw_paths.items() if raw is None)
        if missing:
            counts["quarantined_shards"] += 1
            counts["quarantined_ads"] += int(item["ad_rows"]) - start
            quarantined.append({"shard_ordinal": ordinal, "shard_id": item["shard_id"],
                                "remaining_ad_rows": int(item["ad_rows"]) - start,
                                "missing_source_files": missing})
            cursor = {"shard_ordinal": ordinal + 1, "row_offset": 0}
            continue
        readers = {source: RawReader(raw, args.body_column) for source, raw in raw_paths.items()}
        for offset, row in rows(path, KEY):
            if offset < start:
                continue
            canonical_key = key(row)
            counts["canonical_ads_scanned"] += 1
            body = readers[row["SOURCE_FILE"]].get(int(row["SOURCE_ROW"]), canonical_key[0])
            if not isinstance(body, str):
                reason = "null_body" if body is None else "non_string_body"
                counts[reason + "_ads"] += 1
                unreadable.append({"canonical_key": canonical_key, "reason": reason,
                                   "source_file": row["SOURCE_FILE"],
                                   "source_row": int(row["SOURCE_ROW"]),
                                   "shard_ordinal": ordinal, "row_offset": offset})
            else:
                normalized, _flags = normalize(body)
                if not normalized:
                    counts["empty_normalized_ads"] += 1
                    unreadable.append({"canonical_key": canonical_key,
                                       "reason": "empty_after_pinned_normalization",
                                       "source_file": row["SOURCE_FILE"],
                                       "source_row": int(row["SOURCE_ROW"]),
                                       "shard_ordinal": ordinal, "row_offset": offset})
                else:
                    context_sha = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
                    if (tuple(canonical_key) in reference_keys and
                            reference_keys[tuple(canonical_key)] != context_sha):
                        raise RuntimeError("accepted reference key has changed full context")
                    if context_sha in reference_hashes:
                        counts["reference_exact_reuse_ads"] += 1
                        reuse_bindings.append({
                            "canonical_key": canonical_key, "context_sha256": context_sha,
                            "record_id": None, "reuse_source": "accepted_reference_exact_context",
                            "source_manifest_sha256": REFERENCE_SHA,
                            "reference_canonical_keys": reference_context_keys[context_sha],
                            "label_state": "existing_reference_status_preserved",
                            "status_policy": "preserve_original_reference_status;no_new_known",
                            "source_file": row["SOURCE_FILE"],
                            "source_row": int(row["SOURCE_ROW"]),
                            "shard_ordinal": ordinal, "row_offset": offset})
                    elif context_sha in prior_contexts:
                        counts["prior_packet_exact_reuse_ads"] += 1
                        target = prior_contexts[context_sha]
                        reuse_bindings.append({
                            "canonical_key": canonical_key, "context_sha256": context_sha,
                            "record_id": target["record_id"],
                            "reuse_source": "prior_private_packet_exact_context",
                            "source_manifest_sha256": target["source_manifest_sha256"],
                            "label_state": "pending_prior_packet_result_attachment",
                            "status_policy": "prior_packet_read_status_not_inferred;no_new_known",
                            "source_file": row["SOURCE_FILE"],
                            "source_row": int(row["SOURCE_ROW"]),
                            "shard_ordinal": ordinal, "row_offset": offset})
                    elif context_sha in selected:
                        selected[context_sha]["canonical_keys"].append(canonical_key)
                        selected[context_sha]["raw_provenance"].append({
                            "source_file": row["SOURCE_FILE"], "source_row": int(row["SOURCE_ROW"]),
                            "raw_path": str(raw_paths[row["SOURCE_FILE"]])})
                        counts["current_packet_exact_reuse_ads"] += 1
                    elif len(selected) < args.count:
                        selected[context_sha] = {
                            "record_id": "corpus-pro-" + context_sha,
                            "context_sha256": context_sha,
                            "full_document": normalized,
                            "canonical_keys": [canonical_key],
                            "raw_provenance": [{"source_file": row["SOURCE_FILE"],
                                                "source_row": int(row["SOURCE_ROW"]),
                                                "raw_path": str(raw_paths[row["SOURCE_FILE"]])}],
                            "shard_ordinal": ordinal, "row_offset": offset,
                            "shard_id": item["shard_id"]}
                        counts["prepared_contexts"] += 1
            cursor = {"shard_ordinal": ordinal, "row_offset": offset + 1}
            if cursor["row_offset"] == int(item["ad_rows"]):
                cursor = {"shard_ordinal": ordinal + 1, "row_offset": 0}
            if len(selected) >= args.count:
                break
        if len(selected) >= args.count:
            break

    private.mkdir(parents=True)
    public.mkdir(parents=True)
    contexts = list(selected.values())
    packet_files = []
    for index in range(0, len(contexts), 5):
        packet = contexts[index:index + 5]
        packet_path = private / f"packet_{index // 5 + 1:04d}.jsonl"
        write_jsonl(packet_path, [
            {"record_id": x["record_id"], "context_sha256": x["context_sha256"],
             "full_document": x["full_document"],
             "assignment": {"packet_id": packet_path.stem,
                            "reviewer_role": "primary",
                            "provenance": "Frozen corpus queue transport; actual Pro agent/model dispatch recorded separately"}}
            for x in packet])
        packet_files.append({"name": packet_path.name, "records": len(packet),
                             "sha256": sha(packet_path)})
    manifest_path = private / "PACKET_MANIFEST_PRIVATE.jsonl"
    write_jsonl(manifest_path, [
        {k: v for k, v in x.items() if k != "full_document"} for x in contexts])
    reuse_path = private / "REUSE_AD_BINDINGS_PRIVATE.jsonl"
    unreadable_path = private / "UNREADABLE_ADS_PRIVATE.jsonl"
    write_jsonl(reuse_path, reuse_bindings)
    write_jsonl(unreadable_path, unreadable)
    public_receipt = {
        "version": VERSION, "status": "prepared_not_reviewed",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scheduled_job_id": os.environ["SLURM_JOB_ID"],
        "accepted_scope": {"canonical_us_ads": ADS, "catalog_shards": SHARDS},
        "input_sha256": {"catalog": CATALOG_SHA, "reference": REFERENCE_SHA,
                         "normalizer": NORMALIZER_SHA,
                         "prepare_code": sha(Path(__file__)),
                         "prior_manifests": prior_manifest_hashes},
        "prepare_code_sha256": sha(Path(__file__)),
        "packet_manifest_sha256": sha(manifest_path),
        "output_sha256": {"packet_manifest_private": sha(manifest_path),
                          "reuse_ad_bindings_private": sha(reuse_path),
                          "unreadable_ads_private": sha(unreadable_path)},
        "review_contract": {"schema": "linkup/formal800_20261012/FORMAL800_REVIEW_SCHEMA.json",
                            "instructions": "linkup/formal800_20261012/REVIEW_INSTRUCTIONS.md",
                            "field_families": ["experience", "entry", "responsibility", "technology",
                                               "qualification_alternatives", "conditionality", "numeric_years"],
                            "all_fields_pending_new_read": True},
        "packet_capacity": args.count, "packet_size": 5,
        "packet_files": packet_files,
        "prepared_contexts": len(contexts), "prepared_ad_keys": sum(len(x["canonical_keys"]) for x in contexts),
        "reviewed_contexts_this_run": 0, "counts": dict(counts),
        "prior_contexts_indexed": len(prior_contexts),
        "reuse_ad_bindings": len(reuse_bindings),
        "unreadable_ads": len(unreadable),
        "coverage": {"scanned_canonical_ads": counts["canonical_ads_scanned"],
                     "quarantined_canonical_ads": counts["quarantined_ads"],
                     "full_scope_canonical_ads": ADS,
                     "full_scope_shards": SHARDS},
        "quarantined_shards": [{"shard_ordinal": x["shard_ordinal"],
                                 "shard_id": x["shard_id"],
                                 "remaining_ad_rows": x["remaining_ad_rows"],
                                 "missing_source_file_count": len(x["missing_source_files"])}
                                for x in quarantined],
        "start_cursor": {"shard_ordinal": args.start_shard,
                                                              "row_offset": args.start_row},
        "next_cursor": cursor,
        "cursor_exhausted": cursor["shard_ordinal"] == SHARDS,
    }
    write_json(private / "QUARANTINE_PRIVATE.json", quarantined)
    write_json(public / "PACKET_PREPARATION_PUBLIC.json", public_receipt)
    print(json.dumps({"prepared_contexts": len(contexts), "next_cursor": cursor,
                      "quarantined_shards": len(quarantined)}, sort_keys=True))


if __name__ == "__main__":
    main()
