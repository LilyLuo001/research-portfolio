#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def write(path, rows): pq.write_table(pa.Table.from_pylist(rows), path)


with tempfile.TemporaryDirectory() as d:
    d = Path(d); root = Path(__file__).resolve().parent
    keys = [{"JOB_HASH": "a1", "SOURCE_FILE": "s", "SOURCE_ROW": i, "RECORD_SOURCE_ROW": i} for i in range(1, 7)]
    write(d / "lean.parquet", keys)
    write(d / "records.parquet", [
        {"JOB_HASH": "a1", "RECORD_SOURCE_ROW": i, "COMPANY_ID": None if i == 1 else i,
         "BASE_HASH": None if i == 2 else "b", "TITLE": "" if i == 3 else "t",
         "CREATED": None, "COUNTRY": "USA", "STATE": "MA"} for i in range(1, 6)
    ])
    write(d / "onet.parquet", [
        {"JOB_HASH": "a1", "ONET_OCCUPATION_CODE": "11-1011.00"},
    ])
    (d / "official.csv").write_text("O*NET-SOC Code,Title\n11-1011.00,Chief Executives\n")
    out = d / "report.json"
    subprocess.run([sys.executable, str(root / "build_linkage_coverage.py"),
        "--lean", str(d / "lean.parquet"), "--records", str(d / "records.parquet"),
        "--onet", str(d / "onet.parquet"), "--official-codes", str(d / "official.csv"),
        "--rules", str(root / "RULES.json"), "--output", str(out),
        "--records-lookup-scope", "complete_fixture", "--onet-lookup-scope", "complete"], check=True)
    value = json.loads(out.read_text())
    assert value["canonical_semantic_ads"] == 6
    assert value["records_matches_1"] == 5 and value["records_matches_0"] == 1
    assert value["onet_official_member"] == 6 and value["onet_duplicate_key"] == 0
    assert value["null_company_id"] == value["null_or_placeholder_base_hash"] == value["null_or_blank_title"] == 1
    assert value["aggregate_row_conservation"] and value["linkage_accepted"]
print("PASS")
