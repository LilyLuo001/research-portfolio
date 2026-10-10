#!/usr/bin/env python3
"""Targeted Records/O*NET linkage for frozen D58 posting outputs.

All research-data operations are designed for scheduled BU execution. Source
Parquet files are admitted in bounded staging batches, projected to matching
keys, and represented by hash-bound receipts. Finalization preserves every
posting key and reports missing, one-to-one, one-to-many and unofficial states.
"""
import argparse
import collections
import csv
import datetime as dt
import fcntl
import hashlib
import json
import os
import platform
import re
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

VERSION = "d58-targeted-metadata-join-v1"
PREFIXES = "0123456789abcdef"
CANONICAL_KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
RECORD_KEY = ("JOB_HASH", "RECORD_SOURCE_ROW")
DEFAULT_CAP = 10_000_000_000

KEY_SCHEMA = pa.schema([
    ("JOB_HASH", pa.string()), ("SOURCE_FILE", pa.string()),
    ("SOURCE_ROW", pa.int64()), ("RECORD_SOURCE_ROW", pa.int64()),
    ("POSTING_CREATED", pa.timestamp("ms")), ("POSTING_STATE", pa.string()),
])
RECORD_HIT_SCHEMA = pa.schema([
    ("JOB_HASH", pa.string()), ("RECORD_SOURCE_ROW", pa.int64()),
    ("COMPANY_ID", pa.string()), ("CREATED", pa.timestamp("ms")),
    ("LAST_CHECKED", pa.timestamp("ms")), ("DELETE_DATE", pa.timestamp("ms")),
    ("STATE", pa.string()),
])
ONET_HIT_SCHEMA = pa.schema([
    ("JOB_HASH", pa.string()), ("ONET_OCCUPATION_CODE", pa.string()),
])
FINAL_SCHEMA = pa.schema([
    ("JOB_HASH", pa.string()), ("SOURCE_FILE", pa.string()),
    ("SOURCE_ROW", pa.int64()), ("RECORD_SOURCE_ROW", pa.int64()),
    ("records_match_count", pa.int32()), ("records_join_status", pa.string()),
    ("COMPANY_ID", pa.string()), ("company_status", pa.string()),
    ("POSTING_CREATED", pa.timestamp("ms")), ("RECORD_CREATED", pa.timestamp("ms")),
    ("created_alignment_status", pa.string()),
    ("LAST_CHECKED", pa.timestamp("ms")), ("DELETE_DATE", pa.timestamp("ms")),
    ("RECORD_STATE", pa.string()), ("CENSUS_REGION", pa.string()),
    ("geography_status", pa.string()),
    ("onet_match_count", pa.int32()), ("onet_join_status", pa.string()),
    ("ONET_OCCUPATION_CODE", pa.string()),
    ("official_occupation_status", pa.string()), ("OCCUPATION_MAJOR", pa.string()),
    ("metadata_complete_for_occ_region", pa.bool_()),
    ("metadata_complete_for_company_occ_region", pa.bool_()),
])


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def arrow_rows(batch):
    columns = batch.to_pydict()
    names = list(columns)
    count = len(columns[names[0]]) if names else 0
    return [{name: columns[name][i] for name in names} for i in range(count)]


def rows_table(rows, schema):
    arrays = [pa.array([row.get(field.name) for row in rows], type=field.type)
              for field in schema]
    return pa.Table.from_arrays(arrays, schema=schema)


def runtime():
    return {
        "python": platform.python_version(), "pyarrow": pa.__version__,
        "capabilities": {
            "parquetfile_iter_batches": hasattr(pq.ParquetFile, "iter_batches"),
            "table_from_arrays": hasattr(pa.Table, "from_arrays"),
            "table_to_pydict": hasattr(pa.Table, "to_pydict"),
            "zstd_codec": pa.Codec.is_available("zstd"),
        },
        "duckdb": "not_required_by_this_pyarrow_streaming_implementation",
    }


def check_runtime():
    value = runtime()
    if tuple(int(x) for x in platform.python_version_tuple()[:2]) < (3, 8):
        raise RuntimeError("Python 3.8 or newer is required")
    if not all(value["capabilities"].values()):
        raise RuntimeError("required PyArrow streaming/compression capability is unavailable")
    return value


def lock(directory, name):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    handle = (directory / name).open("w")
    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    return handle


def valid_job_hash(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{32}", value) is not None


def clean_string(value):
    if value is None:
        return None
    value = str(value).strip()
    return value if value else None


def write_parquet_atomic(path, rows, schema):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.unlink(missing_ok=True)
    writer = pq.ParquetWriter(temp, schema, compression="zstd")
    try:
        for block in rows:
            if block:
                writer.write_table(rows_table(block, schema))
        writer.close()
        os.replace(temp, path)
    except Exception:
        writer.close()
        temp.unlink(missing_ok=True)
        raise


def read_manifest(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("status") not in (None, "ready", "complete"):
        raise RuntimeError("manifest status is not ready/complete")
    return value


def prepare_keys(args):
    manifest_path = Path(args.postings_manifest)
    manifest = read_manifest(manifest_path)
    entries = manifest.get("postings")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("postings manifest has no entries")
    key_dir = Path(args.key_dir)
    key_dir.mkdir(parents=True, exist_ok=True)
    _lock = lock(key_dir, ".prepare.lock")
    private_receipt = key_dir / "KEY_PREP_RECEIPT_PRIVATE.json"
    public_receipt = Path(args.public_receipt)
    code_sha = sha256(__file__)
    files = []
    for entry in entries:
        path = Path(entry["path"])
        actual_sha = sha256(path)
        if actual_sha != entry.get("sha256"):
            raise RuntimeError("posting file digest differs from manifest")
        files.append({"path": str(path), "sha256": actual_sha,
                      "rows": pq.ParquetFile(path).metadata.num_rows})
    identity = {"version": VERSION, "code_sha256": code_sha,
                "postings_manifest_sha256": sha256(manifest_path),
                "posting_files": files, "expected_rows": args.expected_rows}
    if private_receipt.exists():
        old = json.loads(private_receipt.read_text(encoding="utf-8"))
        outputs = old.get("outputs") or []
        if (old.get("status") == "complete" and old.get("identity") == identity and
                all(Path(x["path"]).is_file() and sha256(x["path"]) == x["sha256"]
                    for x in outputs)):
            atomic_json(public_receipt, old["public_receipt"])
            return
        raise RuntimeError("existing key preparation has mismatched identity")

    by_prefix = {prefix: [] for prefix in PREFIXES}
    seen_locator = set()
    seen_job_hash = set()
    total = 0
    for entry in entries:
        parquet = pq.ParquetFile(entry["path"])
        required = set(CANONICAL_KEY) | {"CREATED", "STATE"}
        if required - set(parquet.schema_arrow.names):
            raise RuntimeError("posting lacks required key/metadata columns")
        for batch in parquet.iter_batches(batch_size=8192,
                                          columns=list(CANONICAL_KEY) + ["CREATED", "STATE"]):
            for row in arrow_rows(batch):
                locator = tuple(row[x] for x in CANONICAL_KEY)
                job_hash = row["JOB_HASH"]
                if (not valid_job_hash(job_hash) or locator in seen_locator or
                        job_hash in seen_job_hash or not isinstance(row["SOURCE_ROW"], int) or
                        row["SOURCE_ROW"] < 0 or not isinstance(row["RECORD_SOURCE_ROW"], int) or
                        row["RECORD_SOURCE_ROW"] < 0):
                    raise RuntimeError("invalid or duplicate canonical posting key")
                source_file = row["SOURCE_FILE"]
                if (not isinstance(source_file, str) or not source_file or
                        "/" in source_file or "\\" in source_file):
                    raise RuntimeError("invalid source-file namespace")
                seen_locator.add(locator)
                seen_job_hash.add(job_hash)
                by_prefix[job_hash[0]].append({
                    "JOB_HASH": job_hash, "SOURCE_FILE": source_file,
                    "SOURCE_ROW": row["SOURCE_ROW"],
                    "RECORD_SOURCE_ROW": row["RECORD_SOURCE_ROW"],
                    "POSTING_CREATED": row.get("CREATED"),
                    "POSTING_STATE": clean_string(row.get("STATE")),
                })
                total += 1
    if total != args.expected_rows:
        raise RuntimeError("posting key denominator differs from expected")

    outputs = []
    for prefix in PREFIXES:
        path = key_dir / ("keys_%s.parquet" % prefix)
        write_parquet_atomic(path, [by_prefix[prefix]], KEY_SCHEMA)
        outputs.append({"prefix": prefix, "path": str(path),
                        "rows": len(by_prefix[prefix]), "bytes": path.stat().st_size,
                        "sha256": sha256(path)})
    if sum(x["rows"] for x in outputs) != total:
        raise RuntimeError("prefix key outputs do not conserve denominator")
    public = {
        "status": "complete", "version": VERSION, "stage": "prepare_keys",
        "posting_rows": total, "canonical_locator_unique": len(seen_locator) == total,
        "canonical_job_hash_unique": len(seen_job_hash) == total,
        "prefix_counts": {x["prefix"]: x["rows"] for x in outputs},
        "key_files": [{"prefix": x["prefix"], "rows": x["rows"],
                       "bytes": x["bytes"], "sha256": x["sha256"]} for x in outputs],
        "key_output_bytes": sum(x["bytes"] for x in outputs),
        "identity": {k: v for k, v in identity.items() if k != "posting_files"},
        "runtime": runtime(), "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    atomic_json(private_receipt, {"status": "complete", "identity": identity,
                                  "outputs": outputs, "public_receipt": public})
    atomic_json(public_receipt, public)


def validate_key_cache(key_dir, key_receipt_path):
    receipt = json.loads(Path(key_receipt_path).read_text(encoding="utf-8"))
    if receipt.get("status") != "complete" or receipt.get("stage") != "prepare_keys":
        raise RuntimeError("key preparation receipt is not complete")
    entries = receipt.get("key_files")
    if not isinstance(entries, list) or len(entries) != len(PREFIXES):
        raise RuntimeError("key receipt does not enumerate all prefixes")
    by_prefix = {x.get("prefix"): x for x in entries}
    if set(by_prefix) != set(PREFIXES):
        raise RuntimeError("key receipt prefix inventory mismatch")
    total = 0
    for prefix in PREFIXES:
        path = Path(key_dir) / ("keys_%s.parquet" % prefix)
        entry = by_prefix[prefix]
        if (path.stat().st_size != entry.get("bytes") or
                sha256(path) != entry.get("sha256") or
                pq.ParquetFile(path).metadata.num_rows != entry.get("rows")):
            raise RuntimeError("key cache file differs from receipt")
        total += int(entry["rows"])
    if total != receipt.get("posting_rows"):
        raise RuntimeError("key cache denominator differs from receipt")
    return receipt


def load_key_sets(key_dir, key_receipt_path):
    validate_key_cache(key_dir, key_receipt_path)
    records = set()
    jobs = set()
    for prefix in PREFIXES:
        path = Path(key_dir) / ("keys_%s.parquet" % prefix)
        parquet = pq.ParquetFile(path)
        if parquet.schema_arrow != KEY_SCHEMA:
            raise RuntimeError("key file schema mismatch")
        for batch in parquet.iter_batches(batch_size=8192,
                                          columns=["JOB_HASH", "RECORD_SOURCE_ROW"]):
            for row in arrow_rows(batch):
                records.add((row["JOB_HASH"], row["RECORD_SOURCE_ROW"]))
                jobs.add(row["JOB_HASH"])
    return records, jobs


def extract_batch(args):
    spec_path = Path(args.batch_spec)
    spec = read_manifest(spec_path)
    kind = spec.get("kind")
    if kind not in {"records", "onet"}:
        raise RuntimeError("batch kind must be records or onet")
    inputs = spec.get("input_files")
    if not isinstance(inputs, list) or not inputs:
        raise RuntimeError("batch has no input files")
    cap = int(spec.get("staging_cap_bytes", DEFAULT_CAP))
    if cap > DEFAULT_CAP:
        raise RuntimeError("batch specification exceeds frozen 10GB rolling cap")
    verified_inputs = []
    total_bytes = 0
    for item in inputs:
        path = Path(item["path"])
        size = path.stat().st_size
        digest = sha256(path)
        source_id = item.get("source_id")
        if (not isinstance(source_id, str) or not source_id or
                size != item.get("size_bytes") or digest != item.get("sha256")):
            raise RuntimeError("staged source file identity mismatch")
        total_bytes += size
        verified_inputs.append({"source_id": source_id, "path": str(path),
                                "size_bytes": size, "sha256": digest})
    if total_bytes > cap:
        raise RuntimeError("staged batch exceeds declared byte cap")

    output = Path(spec["output"])
    receipt_path = Path(spec["receipt"])
    output.parent.mkdir(parents=True, exist_ok=True)
    _lock = lock(output.parent, ".%s.lock" % spec.get("batch_id", "batch"))
    identity = {
        "version": VERSION, "code_sha256": sha256(__file__), "kind": kind,
        "batch_id": spec.get("batch_id"), "batch_spec_sha256": sha256(spec_path),
        "key_receipt_sha256": sha256(spec["key_receipt"]),
        "inputs": verified_inputs,
    }
    if receipt_path.exists():
        old = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (old.get("status") == "complete" and old.get("identity") == identity and
                output.exists() and old.get("output_sha256") == sha256(output)):
            return
        raise RuntimeError("existing batch receipt has mismatched identity")

    record_keys, job_keys = load_key_sets(spec["key_dir"], spec["key_receipt"])
    schema = RECORD_HIT_SCHEMA if kind == "records" else ONET_HIT_SCHEMA
    temp = Path(str(output) + ".tmp")
    temp.unlink(missing_ok=True)
    writer = pq.ParquetWriter(temp, schema, compression="zstd")
    scanned = hits = 0
    try:
        for item in verified_inputs:
            parquet = pq.ParquetFile(item["path"])
            columns = (["JOB_HASH", "RECORD_SOURCE_ROW", "COMPANY_ID", "CREATED",
                        "LAST_CHECKED", "DELETE_DATE", "STATE"] if kind == "records"
                       else ["JOB_HASH", "ONET_OCCUPATION_CODE"])
            missing = set(columns) - set(parquet.schema_arrow.names)
            if missing:
                raise RuntimeError("staged source schema missing required columns")
            for batch in parquet.iter_batches(batch_size=16384, columns=columns):
                selected = []
                for row in arrow_rows(batch):
                    scanned += 1
                    keep = ((row["JOB_HASH"], row["RECORD_SOURCE_ROW"]) in record_keys
                            if kind == "records" else row["JOB_HASH"] in job_keys)
                    if not keep:
                        continue
                    if kind == "records":
                        selected.append({
                            "JOB_HASH": row["JOB_HASH"],
                            "RECORD_SOURCE_ROW": row["RECORD_SOURCE_ROW"],
                            "COMPANY_ID": clean_string(row.get("COMPANY_ID")),
                            "CREATED": row.get("CREATED"), "LAST_CHECKED": row.get("LAST_CHECKED"),
                            "DELETE_DATE": row.get("DELETE_DATE"),
                            "STATE": clean_string(row.get("STATE")),
                        })
                    else:
                        selected.append({"JOB_HASH": row["JOB_HASH"],
                                         "ONET_OCCUPATION_CODE": clean_string(row.get("ONET_OCCUPATION_CODE"))})
                if selected:
                    writer.write_table(rows_table(selected, schema))
                    hits += len(selected)
        writer.close()
        os.replace(temp, output)
    except Exception:
        writer.close()
        temp.unlink(missing_ok=True)
        raise
    receipt = {
        "status": "complete", "version": VERSION, "stage": "extract_%s" % kind,
        "identity": identity, "source_rows_scanned": scanned, "hit_rows": hits,
        "staged_input_bytes": total_bytes, "staging_cap_bytes": cap,
        "output_bytes": output.stat().st_size, "output_sha256": sha256(output),
            "runtime": runtime(), "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    atomic_json(receipt_path, receipt)


def official_codes(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        names = reader.fieldnames or []
        field = next((x for x in names if x.lower().replace(" ", "") in
                      {"o*net-soccode", "o*net-soc2019code", "onetsoccode",
                       "onetsoc2019code", "code"}), None)
        if field is None:
            raise RuntimeError("official occupation file lacks code column")
        return {str(row[field]).strip() for row in reader if row.get(field) and str(row[field]).strip()}


def census_region(state):
    state = clean_string(state)
    if state is None:
        return None
    state = state.upper()
    groups = {
        "Northeast": "CT ME MA NH RI VT NJ NY PA",
        "Midwest": "IN IL MI OH WI IA KS MN MO NE ND SD",
        "South": "DE FL GA MD NC SC VA DC WV AL KY MS TN AR LA OK TX",
        "West": "AZ CO ID NM MT UT NV WY AK CA HI OR WA",
    }
    for label, codes in groups.items():
        if state in codes.split():
            return label
    return None


def load_extraction_manifest(path, kind, expected_source_bytes):
    manifest_path = Path(path)
    manifest = read_manifest(manifest_path)
    if manifest.get("kind") != kind:
        raise RuntimeError("extraction manifest kind mismatch")
    batches = manifest.get("batches")
    if not isinstance(batches, list) or not batches:
        raise RuntimeError("extraction manifest has no batches")
    frozen_inventory_sha256 = manifest.get("frozen_source_inventory_sha256")
    if (not isinstance(frozen_inventory_sha256, str) or
            re.fullmatch(r"[0-9a-f]{64}", frozen_inventory_sha256) is None):
        raise RuntimeError("extraction manifest lacks frozen source inventory digest")
    source_ids = set()
    total_source_bytes = 0
    hit_files = []
    max_batch_bytes = 0
    for batch in batches:
        receipt_path = Path(batch["receipt"])
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("status") != "complete" or receipt.get("stage") != "extract_%s" % kind:
            raise RuntimeError("batch extraction receipt is not complete")
        if sha256(receipt_path) != batch.get("receipt_sha256"):
            raise RuntimeError("batch receipt digest mismatch")
        identity = receipt.get("identity") or {}
        for source in identity.get("inputs") or []:
            source_id = source.get("source_id")
            if not isinstance(source_id, str) or not source_id:
                raise RuntimeError("batch receipt lacks stable source_id")
            if source_id in source_ids:
                raise RuntimeError("source file repeated across extraction batches")
            source_ids.add(source_id)
            total_source_bytes += int(source["size_bytes"])
        max_batch_bytes = max(max_batch_bytes, int(receipt.get("staged_input_bytes", 0)))
        output = Path(batch["output"])
        if sha256(output) != receipt.get("output_sha256"):
            raise RuntimeError("batch hit output digest mismatch")
        hit_files.append(output)
    if total_source_bytes != expected_source_bytes:
        raise RuntimeError("source inventory bytes differ from frozen expected total")
    return {"manifest_path": manifest_path, "manifest_sha256": sha256(manifest_path),
            "frozen_source_inventory_sha256": frozen_inventory_sha256,
            "files": hit_files, "hit_bytes": sum(x.stat().st_size for x in hit_files),
            "source_files": len(source_ids),
            "source_bytes": total_source_bytes, "max_batch_bytes": max_batch_bytes}


def finalize(args):
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    _lock = lock(output.parent, ".finalize.lock")
    private_receipt = Path(args.private_receipt)
    public_receipt = Path(args.public_receipt)
    key_receipt_path = Path(args.key_receipt)
    key_receipt = json.loads(key_receipt_path.read_text(encoding="utf-8"))
    if key_receipt.get("status") != "complete" or key_receipt.get("posting_rows") != args.expected_rows:
        raise RuntimeError("key preparation receipt incomplete or wrong denominator")
    validate_key_cache(args.key_dir, key_receipt_path)
    records = load_extraction_manifest(args.records_manifest, "records", args.expected_records_bytes)
    onet = load_extraction_manifest(args.onet_manifest, "onet", args.expected_onet_bytes)
    if records["frozen_source_inventory_sha256"] != args.expected_records_inventory_sha256:
        raise RuntimeError("Records frozen source inventory digest mismatch")
    if onet["frozen_source_inventory_sha256"] != args.expected_onet_inventory_sha256:
        raise RuntimeError("O*NET frozen source inventory digest mismatch")
    official_path = Path(args.official_codes)
    official = official_codes(official_path)
    source_cache_bytes = records["source_bytes"] + onet["source_bytes"] + official_path.stat().st_size
    if source_cache_bytes > args.source_cache_cap_bytes:
        raise RuntimeError("retained metadata source cache exceeds D59 cap")
    identity = {
        "version": VERSION, "code_sha256": sha256(__file__),
        "key_receipt_sha256": sha256(key_receipt_path),
        "records_manifest_sha256": records["manifest_sha256"],
        "records_source_inventory_sha256": records["frozen_source_inventory_sha256"],
        "onet_manifest_sha256": onet["manifest_sha256"],
        "onet_source_inventory_sha256": onet["frozen_source_inventory_sha256"],
        "official_codes_sha256": sha256(official_path),
        "expected_rows": args.expected_rows,
        "expected_records_bytes": args.expected_records_bytes,
        "expected_onet_bytes": args.expected_onet_bytes,
    }
    if private_receipt.exists():
        old = json.loads(private_receipt.read_text(encoding="utf-8"))
        if (old.get("status") == "complete" and old.get("identity") == identity and
                output.exists() and old.get("output_sha256") == sha256(output)):
            atomic_json(public_receipt, old["public_receipt"])
            return
        raise RuntimeError("existing final metadata join has mismatched identity")

    record_hits = collections.defaultdict(list)
    for path in records["files"]:
        parquet = pq.ParquetFile(path)
        if parquet.schema_arrow != RECORD_HIT_SCHEMA:
            raise RuntimeError("records hit schema mismatch")
        for batch in parquet.iter_batches(batch_size=8192):
            for row in arrow_rows(batch):
                record_hits[(row["JOB_HASH"], row["RECORD_SOURCE_ROW"])].append(row)
    onet_hits = collections.defaultdict(list)
    for path in onet["files"]:
        parquet = pq.ParquetFile(path)
        if parquet.schema_arrow != ONET_HIT_SCHEMA:
            raise RuntimeError("O*NET hit schema mismatch")
        for batch in parquet.iter_batches(batch_size=8192):
            for row in arrow_rows(batch):
                onet_hits[row["JOB_HASH"]].append(row)

    counters = collections.Counter()
    seen = set()
    temp = Path(str(output) + ".tmp")
    temp.unlink(missing_ok=True)
    writer = pq.ParquetWriter(temp, FINAL_SCHEMA, compression="zstd")
    try:
        for prefix in PREFIXES:
            key_path = Path(args.key_dir) / ("keys_%s.parquet" % prefix)
            for batch in pq.ParquetFile(key_path).iter_batches(batch_size=4096):
                out = []
                for key in arrow_rows(batch):
                    locator = tuple(key[x] for x in CANONICAL_KEY)
                    if locator in seen:
                        raise RuntimeError("duplicate locator during finalization")
                    seen.add(locator)
                    ritems = record_hits.get((key["JOB_HASH"], key["RECORD_SOURCE_ROW"]), [])
                    oitems = onet_hits.get(key["JOB_HASH"], [])
                    rn, on = len(ritems), len(oitems)
                    r = ritems[0] if rn == 1 else None
                    o = oitems[0] if on == 1 else None
                    rstatus = "matched_one" if rn == 1 else ("missing" if rn == 0 else "one_to_many_unresolved")
                    ostatus = "matched_one" if on == 1 else ("missing" if on == 0 else "one_to_many_unresolved")
                    company = clean_string(r.get("COMPANY_ID")) if r else None
                    if rn == 0: company_status = "record_missing"
                    elif rn > 1: company_status = "record_one_to_many_unresolved"
                    elif company is None: company_status = "company_missing"
                    else: company_status = "observed_company_scrape_entity"
                    record_created = r.get("CREATED") if r else None
                    posting_created = key.get("POSTING_CREATED")
                    if rn == 0: created_status = "record_missing"
                    elif rn > 1: created_status = "record_one_to_many_unresolved"
                    elif record_created is None: created_status = "record_created_missing"
                    elif posting_created is None: created_status = "posting_created_missing"
                    elif record_created.date() == posting_created.date(): created_status = "same_calendar_date"
                    else: created_status = "calendar_date_disagreement"
                    state = clean_string(r.get("STATE")) if r else None
                    region = census_region(state)
                    if rn == 0: geography_status = "record_missing"
                    elif rn > 1: geography_status = "record_one_to_many_unresolved"
                    elif state is None: geography_status = "state_missing"
                    elif region is None: geography_status = "state_unmapped"
                    else: geography_status = "mapped_region"
                    code = clean_string(o.get("ONET_OCCUPATION_CODE")) if o else None
                    if on == 0: official_status = "no_onet_row"
                    elif on > 1: official_status = "onet_one_to_many_unresolved"
                    elif code is None: official_status = "blank_code"
                    elif code == "99-9999.00": official_status = "placeholder_99-9999.00"
                    elif code not in official: official_status = "unofficial_code"
                    else: official_status = "official_code"
                    major = code[:2] if official_status == "official_code" else None
                    complete_or = major is not None and region is not None
                    complete_company = complete_or and company is not None
                    row = {
                        "JOB_HASH": key["JOB_HASH"], "SOURCE_FILE": key["SOURCE_FILE"],
                        "SOURCE_ROW": key["SOURCE_ROW"], "RECORD_SOURCE_ROW": key["RECORD_SOURCE_ROW"],
                        "records_match_count": rn, "records_join_status": rstatus,
                        "COMPANY_ID": company, "company_status": company_status,
                        "POSTING_CREATED": posting_created, "RECORD_CREATED": record_created,
                        "created_alignment_status": created_status,
                        "LAST_CHECKED": r.get("LAST_CHECKED") if r else None,
                        "DELETE_DATE": r.get("DELETE_DATE") if r else None,
                        "RECORD_STATE": state, "CENSUS_REGION": region,
                        "geography_status": geography_status,
                        "onet_match_count": on, "onet_join_status": ostatus,
                        "ONET_OCCUPATION_CODE": code,
                        "official_occupation_status": official_status,
                        "OCCUPATION_MAJOR": major,
                        "metadata_complete_for_occ_region": complete_or,
                        "metadata_complete_for_company_occ_region": complete_company,
                    }
                    out.append(row)
                    counters["records_" + rstatus] += 1
                    counters["onet_" + ostatus] += 1
                    counters["company_" + company_status] += 1
                    counters["geography_" + geography_status] += 1
                    counters["occupation_" + official_status] += 1
                    counters["created_" + created_status] += 1
                    if complete_or: counters["complete_occ_region"] += 1
                    if complete_company: counters["complete_company_occ_region"] += 1
                if out:
                    writer.write_table(rows_table(out, FINAL_SCHEMA))
        writer.close()
    except Exception:
        writer.close()
        temp.unlink(missing_ok=True)
        raise
    cardinality_failures = (counters["records_one_to_many_unresolved"] +
                            counters["onet_one_to_many_unresolved"])
    created_disagreements = counters["created_calendar_date_disagreement"]
    if cardinality_failures or created_disagreements:
        temp.unlink(missing_ok=True)
        atomic_json(output.parent / "CARDINALITY_FAILURE_PRIVATE.json", {
            "status": "blocked", "version": VERSION,
            "records_one_to_many": counters["records_one_to_many_unresolved"],
            "onet_one_to_many": counters["onet_one_to_many_unresolved"],
            "created_calendar_date_disagreement": created_disagreements,
            "posting_denominator_preserved_in_audit": len(seen),
            "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        })
        raise RuntimeError("metadata linkage cardinality/date-alignment gate failed")
    os.replace(temp, output)
    output_rows = pq.ParquetFile(output).metadata.num_rows
    if output_rows != args.expected_rows or len(seen) != args.expected_rows:
        raise RuntimeError("final metadata output does not preserve posting denominator")
    public = {
        "status": "complete", "version": VERSION, "stage": "finalize",
        "posting_denominator": args.expected_rows, "output_rows": output_rows,
        "row_conservation": output_rows == args.expected_rows,
        "counts": dict(sorted(counters.items())),
        "source_inventory": {
            "records_files": records["source_files"], "records_bytes": records["source_bytes"],
            "onet_files": onet["source_files"], "onet_bytes": onet["source_bytes"],
            "official_codes_bytes": official_path.stat().st_size,
            "retained_source_cache_bytes": source_cache_bytes,
            "records_hit_bytes": records["hit_bytes"],
            "onet_hit_bytes": onet["hit_bytes"],
            "maximum_staged_batch_bytes": max(records["max_batch_bytes"], onet["max_batch_bytes"]),
            "rolling_extraction_batch_cap_bytes": DEFAULT_CAP,
            "retained_source_cache_cap_bytes": args.source_cache_cap_bytes,
        },
        "identity": identity, "output_bytes": output.stat().st_size,
        "output_sha256": sha256(output), "runtime": runtime(),
        "claim_boundary": "metadata mapping for frozen posting keys; current O*NET snapshot and Records observation metadata; no semantic relabeling or historical-text inference",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    atomic_json(private_receipt, {"status": "complete", "identity": identity,
                                  "output_path": str(output), "output_sha256": public["output_sha256"],
                                  "public_receipt": public})
    atomic_json(public_receipt, public)


def parser():
    root = argparse.ArgumentParser()
    subs = root.add_subparsers(dest="command", required=True)
    prepare = subs.add_parser("prepare-keys")
    prepare.add_argument("--postings-manifest", required=True)
    prepare.add_argument("--key-dir", required=True)
    prepare.add_argument("--public-receipt", required=True)
    prepare.add_argument("--expected-rows", type=int, default=424226)
    prepare.set_defaults(func=prepare_keys)
    extract = subs.add_parser("extract-batch")
    extract.add_argument("--batch-spec", required=True)
    extract.set_defaults(func=extract_batch)
    final = subs.add_parser("finalize")
    final.add_argument("--key-dir", required=True)
    final.add_argument("--key-receipt", required=True)
    final.add_argument("--records-manifest", required=True)
    final.add_argument("--onet-manifest", required=True)
    final.add_argument("--official-codes", required=True)
    final.add_argument("--output", required=True)
    final.add_argument("--private-receipt", required=True)
    final.add_argument("--public-receipt", required=True)
    final.add_argument("--expected-rows", type=int, default=424226)
    final.add_argument("--expected-records-bytes", type=int, default=15415489237)
    final.add_argument("--expected-onet-bytes", type=int, default=11190966290)
    final.add_argument("--expected-records-inventory-sha256", required=True)
    final.add_argument("--expected-onet-inventory-sha256", required=True)
    final.add_argument("--source-cache-cap-bytes", type=int, default=35000000000)
    final.set_defaults(func=finalize)
    return root


if __name__ == "__main__":
    check_runtime()
    arguments = parser().parse_args()
    arguments.func(arguments)
