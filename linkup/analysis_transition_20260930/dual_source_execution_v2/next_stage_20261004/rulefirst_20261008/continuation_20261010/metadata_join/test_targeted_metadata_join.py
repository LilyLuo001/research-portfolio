#!/usr/bin/env python3
"""Synthetic BU regression for D59 metadata linkage; contains no research data."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pyarrow.parquet as pq

import targeted_metadata_join as join


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def parquet(path, rows, schema):
    join.write_parquet_atomic(path, [rows], schema)


def run(root, duplicate_onet=False):
    hashes = ["%032x" % x for x in range(1, 5)]
    posting_schema = join.pa.schema(list(join.KEY_SCHEMA) + [
        join.pa.field("CREATED", join.pa.timestamp("ms")),
        join.pa.field("STATE", join.pa.string()),
    ])
    postings = []
    for index, job_hash in enumerate(hashes):
        postings.append({
            "JOB_HASH": job_hash, "SOURCE_FILE": "synthetic.parquet",
            "SOURCE_ROW": index, "RECORD_SOURCE_ROW": 100 + index,
            "POSTING_CREATED": None, "POSTING_STATE": None,
            "CREATED": None, "STATE": None,
        })
    posting_path = root / "posting.parquet"
    parquet(posting_path, postings, posting_schema)
    posting_manifest = root / "postings.json"
    dump(posting_manifest, {"status": "ready", "postings": [
        {"path": str(posting_path), "sha256": sha(posting_path)}]})
    key_dir = root / "keys"
    key_receipt = root / "KEYS_PUBLIC.json"
    subprocess.check_call([sys.executable, join.__file__, "prepare-keys",
                           "--postings-manifest", str(posting_manifest),
                           "--key-dir", str(key_dir), "--public-receipt", str(key_receipt),
                           "--expected-rows", "4"])

    records_path = root / "records.parquet"
    parquet(records_path, [
        {"JOB_HASH": hashes[0], "RECORD_SOURCE_ROW": 100, "COMPANY_ID": "A",
         "CREATED": None, "LAST_CHECKED": None, "DELETE_DATE": None, "STATE": "NY"},
        {"JOB_HASH": hashes[2], "RECORD_SOURCE_ROW": 102, "COMPANY_ID": None,
         "CREATED": None, "LAST_CHECKED": None, "DELETE_DATE": None, "STATE": "ZZ"},
        {"JOB_HASH": hashes[3], "RECORD_SOURCE_ROW": 103, "COMPANY_ID": "D",
         "CREATED": None, "LAST_CHECKED": None, "DELETE_DATE": None, "STATE": "CA"},
    ], join.RECORD_HIT_SCHEMA)
    onet_rows = [
        {"JOB_HASH": hashes[0], "ONET_OCCUPATION_CODE": "11-1011.00"},
        {"JOB_HASH": hashes[2], "ONET_OCCUPATION_CODE": None},
        {"JOB_HASH": hashes[3], "ONET_OCCUPATION_CODE": "12-3456.00"},
    ]
    if duplicate_onet:
        onet_rows.append({"JOB_HASH": hashes[0], "ONET_OCCUPATION_CODE": "11-1011.00"})
    onet_path = root / "onet.parquet"
    parquet(onet_path, onet_rows, join.ONET_HIT_SCHEMA)

    batch_results = {}
    for kind, source in (("records", records_path), ("onet", onet_path)):
        output = root / (kind + "_hits.parquet")
        receipt = root / (kind + "_receipt.json")
        source_id = "synthetic-%s" % kind
        spec = root / (kind + "_spec.json")
        dump(spec, {"status": "ready", "kind": kind, "batch_id": source_id,
                    "staging_cap_bytes": 10000000000,
                    "key_dir": str(key_dir), "key_receipt": str(key_receipt),
                    "output": str(output), "receipt": str(receipt),
                    "input_files": [{"source_id": source_id, "path": str(source),
                                     "size_bytes": source.stat().st_size,
                                     "sha256": sha(source)}]})
        subprocess.check_call([sys.executable, join.__file__, "extract-batch",
                               "--batch-spec", str(spec)])
        batch_results[kind] = (output, receipt, source, source_id)

    inventory_sha = {"records": "a" * 64, "onet": "b" * 64}
    manifests = {}
    for kind in ("records", "onet"):
        output, receipt, source, source_id = batch_results[kind]
        path = root / (kind + "_manifest.json")
        dump(path, {"status": "complete", "kind": kind,
                    "frozen_source_inventory_sha256": inventory_sha[kind],
                    "batches": [{"receipt": str(receipt), "receipt_sha256": sha(receipt),
                                 "output": str(output)}]})
        manifests[kind] = path
    official = root / "official.csv"
    official.write_text("O*NET-SOC Code\n11-1011.00\n")
    output = root / "final.parquet"
    private = root / "FINAL_PRIVATE.json"
    public = root / "FINAL_PUBLIC.json"
    command = [sys.executable, join.__file__, "finalize", "--key-dir", str(key_dir),
               "--key-receipt", str(key_receipt),
               "--records-manifest", str(manifests["records"]),
               "--onet-manifest", str(manifests["onet"]),
               "--official-codes", str(official), "--output", str(output),
               "--private-receipt", str(private), "--public-receipt", str(public),
               "--expected-rows", "4",
               "--expected-records-bytes", str(records_path.stat().st_size),
               "--expected-onet-bytes", str(onet_path.stat().st_size),
               "--expected-records-inventory-sha256", inventory_sha["records"],
               "--expected-onet-inventory-sha256", inventory_sha["onet"]]
    result = subprocess.run(command)
    if duplicate_onet:
        assert result.returncode != 0 and not output.exists()
        assert (root / "CARDINALITY_FAILURE_PRIVATE.json").is_file()
        return
    assert result.returncode == 0
    rows = join.arrow_rows(pq.read_table(output))
    assert len(rows) == 4
    by_hash = {row["JOB_HASH"]: row for row in rows}
    assert by_hash[hashes[0]]["official_occupation_status"] == "official_code"
    assert by_hash[hashes[0]]["OCCUPATION_MAJOR"] == "11"
    assert by_hash[hashes[1]]["records_join_status"] == "missing"
    assert by_hash[hashes[1]]["official_occupation_status"] == "no_onet_row"
    assert by_hash[hashes[2]]["official_occupation_status"] == "blank_code"
    assert by_hash[hashes[2]]["geography_status"] == "state_unmapped"
    assert by_hash[hashes[3]]["official_occupation_status"] == "unofficial_code"
    assert json.loads(public.read_text())["row_conservation"] is True


if __name__ == "__main__":
    with tempfile.TemporaryDirectory() as temp:
        run(Path(temp) / "pass")
    with tempfile.TemporaryDirectory() as temp:
        run(Path(temp) / "duplicate", duplicate_onet=True)
    print("synthetic metadata join: PASS")
