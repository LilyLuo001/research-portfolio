#!/usr/bin/env python3
"""Small structural fixture for the bounded release disposition builder."""
import hashlib
import json
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

import prepare_release_dispositions as prep


def write_json(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True) + "\n")


def hash_key(first, fill):
    return first + fill * 31


def main():
    root = Path(tempfile.mkdtemp(prefix="release-disposition-fixture."))
    ks_name = "ks.snappy.parquet"; wz_name = "wz.snappy.parquet"
    inventories = []
    for region, name in (("kunshan", ks_name), ("wuzhen", wz_name)):
        path = root / (region + "_inventory.json")
        write_json(path, {"region": region, "count": 1, "sources": [{
            "region": region, "file_name": name, "source_path": "/raw/" + name,
            "source_bytes": 1, "source_sha256_cached": "0" * 64,
        }]})
        inventories.append(str(path))

    projection = root / "projection"; projection.mkdir()
    ks_keys = [hash_key("0", "1"), hash_key("a", "2")]
    projection_schema = pa.schema([
        ("JOB_HASH", pa.string()), ("DESCRIPTION_COMPANY_ID", pa.decimal128(10, 0)),
        ("SOURCE_ID", pa.int32()),
    ])
    pq.write_table(pa.Table.from_pylist([
        {"JOB_HASH": value, "DESCRIPTION_COMPANY_ID": 10, "SOURCE_ID": 0}
        for value in ks_keys], schema=projection_schema), projection / (ks_name + ".parquet"))
    projection_report = root / "projection_report.json"
    write_json(projection_report, {
        "status": "complete", "description_text_read": False, "files": 1, "rows": 2,
        "source_counts": [{"source_file": ks_name, "source_id": 0, "rows": 2}],
    })

    occurrence_schema = pa.schema([
        ("JOB_HASH", pa.string()), ("SOURCE_FILE", pa.string()), ("SOURCE_ROW", pa.int64()),
        ("DESCRIPTION_COMPANY_ID", pa.decimal128(10, 0)),
    ])
    wz_keys = [hash_key("a", "2"), hash_key("b", "3"), hash_key("d", "4"), hash_key("e", "5")]
    occurrences = root / "occurrences.parquet"
    pq.write_table(pa.Table.from_pylist([
        {"JOB_HASH": value, "SOURCE_FILE": wz_name, "SOURCE_ROW": i,
         "DESCRIPTION_COMPANY_ID": 10} for i, value in enumerate(wz_keys)
    ], schema=occurrence_schema), occurrences)

    records = root / "records"
    record_schema = pa.schema([
        ("JOB_HASH", pa.string()), ("COMPANY_ID", pa.decimal128(10, 0)),
        ("COUNTRY", pa.string()), ("STATE", pa.string()), ("CREATED", pa.timestamp("ms")),
        ("RECORD_SOURCE_ROW", pa.uint64()),
    ])
    rows = {
        "0": [{"JOB_HASH": ks_keys[0], "COMPANY_ID": 10, "COUNTRY": "USA", "STATE": "CA", "CREATED": None, "RECORD_SOURCE_ROW": 1}],
        "a": [{"JOB_HASH": ks_keys[1], "COMPANY_ID": 10, "COUNTRY": "USA", "STATE": "NY", "CREATED": None, "RECORD_SOURCE_ROW": 2}],
        "b": [],
        "d": [{"JOB_HASH": wz_keys[2], "COMPANY_ID": 10, "COUNTRY": None, "STATE": None, "CREATED": None, "RECORD_SOURCE_ROW": 3}],
        "e": [{"JOB_HASH": wz_keys[3], "COMPANY_ID": 10, "COUNTRY": "CAN", "STATE": None, "CREATED": None, "RECORD_SOURCE_ROW": 4}],
        "c": [
            {"JOB_HASH": hash_key("c", "6"), "COMPANY_ID": 10, "COUNTRY": "USA", "STATE": None, "CREATED": None, "RECORD_SOURCE_ROW": 5},
            {"JOB_HASH": hash_key("c", "6"), "COMPANY_ID": 10, "COUNTRY": "USA", "STATE": None, "CREATED": None, "RECORD_SOURCE_ROW": 6},
        ],
    }
    for prefix, values in rows.items():
        directory = records / ("hash_prefix=" + prefix); directory.mkdir(parents=True)
        pq.write_table(pa.Table.from_pylist(values, schema=record_schema), directory / "records.parquet")

    expected = root / "expected.json"
    write_json(expected, {"sources": [
        {"region": "kunshan", "source_file": ks_name, "raw_rows": 2},
        {"region": "wuzhen", "source_file": wz_name, "raw_rows": 4},
    ]})
    cfg_path = root / "config.json"
    cfg = {
        "source_inventories": inventories,
        "kunshan_projection_report": str(projection_report),
        "kunshan_projection_dir": str(projection),
        "wuzhen_occurrence_files": [str(occurrences)], "wuzhen_occurrence_rows": 4,
        "wuzhen_columns": {"job_hash": "JOB_HASH", "source_file": "SOURCE_FILE",
                            "source_row": "SOURCE_ROW", "description_company_id": "DESCRIPTION_COMPANY_ID"},
        "records_index": str(records), "output_root": str(root / "output"),
        "scratch_root": str(root / "scratch"), "duckdb_temp_dir": str(root / "ducktemp"),
        "sidecar_root": str(root / "sidecars"), "expected_source_rows": str(expected),
        "runner_plan": str(root / "plan.jsonl"), "expected_region_rows": {"kunshan": 2, "wuzhen": 4},
        "duckdb_threads": 2, "duckdb_memory_limit": "1GB", "free_reserve_bytes": 1,
    }
    write_json(cfg_path, cfg)
    cfg["_config_sha256"] = prep.sha256(cfg_path)
    cfg["_script_sha256"] = prep.sha256(Path(prep.__file__).resolve())
    for prefix in "0abde":
        prep.process_prefix(cfg, prefix)
    assert prep.process_prefix(cfg, "0")["status"] == "complete"  # verified resume
    ks_receipt = prep.consolidate_shard(cfg, "kunshan", ks_name)
    wz_receipt = prep.consolidate_shard(cfg, "wuzhen", wz_name)
    assert ks_receipt["raw_rows"] == 2 and wz_receipt["raw_rows"] == 4
    all_rows = []
    for receipt in (ks_receipt, wz_receipt):
        all_rows += pq.read_table(receipt["sidecar_path"]).to_pylist()
    by_key = {}
    for row in all_rows:
        by_key.setdefault(row["JOB_HASH"], []).append(row["MATCH_DISPOSITION"])
    assert by_key[ks_keys[0]] == ["matched_usa_canonical"]
    assert by_key[ks_keys[1]] == ["matched_usa_duplicate_quarantine"] * 2
    assert by_key[wz_keys[1]] == ["record_unmatched"]
    assert by_key[wz_keys[2]] == ["matched_country_unknown"]
    assert by_key[wz_keys[3]] == ["matched_non_usa"]
    rejected = False
    try:
        prep.process_prefix(cfg, "c")
    except RuntimeError as error:
        rejected = "duplicate keys" in str(error)
    assert rejected
    assert not (root / "output" / "prefix_fragments" / "prefix_c").exists()
    print(json.dumps({"status": "pass", "rows": len(all_rows),
                      "cross_prefix_same_shard": True, "cross_region_duplicate_quarantine": True,
                      "null_country": True, "non_usa": True, "record_duplicate_rejected": True}, sort_keys=True))


if __name__ == "__main__":
    main()
