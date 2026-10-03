#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
MATERIALIZER = HERE.parents[1] / "pre_revelio_execution_v1" / "materialize_selected_text.py"


def row(i, source):
    return {"JOB_HASH": f"h{i:03d}", "SOURCE_FILE": source, "SOURCE_ROW": i, "RECORD_SOURCE_ROW": i + 1000}


def run(root, plans, expect_ok=True):
    command = [sys.executable, str(HERE / "prepare_dev_text_adapter.py"), "--development", str(root / "dev.parquet"), "--config-compare", str(root / "config.parquet"), "--output-dir", str(root / "outside_git")]
    for plan in plans:
        command += ["--source-plan", str(plan)]
    result = subprocess.run(command, text=True, capture_output=True)
    if (result.returncode == 0) != expect_ok:
        raise AssertionError(result.stderr)
    return result


def main():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        dev = [row(i, "ks.parquet" if i % 2 == 0 else "wz.parquet") for i in range(200)]
        config = dev[:80]
        pq.write_table(pa.Table.from_pylist(dev), root / "dev.parquet")
        pq.write_table(pa.Table.from_pylist(config), root / "config.parquet")
        ks_source = [row(i, "ks.parquet") | {"DESCRIPTION": f"ks text {i}"} for i in range(200)]
        wz_source = [row(i, "wz.parquet") | {"DESCRIPTION": f"wz text {i}"} for i in range(200)]
        pq.write_table(pa.Table.from_pylist(ks_source), root / "ks.parquet")
        pq.write_table(pa.Table.from_pylist(wz_source), root / "wz.parquet")
        ks = root / "ks.plan.jsonl"
        wz = root / "wz.plan.jsonl"
        ks.write_text(json.dumps({"region": "kunshan", "source_file": "ks.parquet", "source_path": str(root / "ks.parquet")}) + "\n")
        wz.write_text(json.dumps({"region": "wuzhen", "source_file": "wz.parquet", "source_path": str(root / "wz.parquet")}) + "\n")
        run(root, [ks, wz])
        receipt = json.loads((root / "outside_git" / "DEV_TEXT_ADAPTER_RECEIPT_PRIVATE.json").read_text())
        assert receipt["region_counts"]["kunshan"]["development"] == 100
        assert receipt["region_counts"]["wuzhen"]["development"] == 100
        selected = []
        for region in ("kunshan", "wuzhen"):
            selected += json.loads((root / "outside_git" / f"development_200_{region}.selection.json").read_text())["selected"]
            subprocess.run([
                sys.executable, str(MATERIALIZER),
                "--selection", str(root / "outside_git" / f"development_200_{region}.selection.json"),
                "--source-map", str(root / "outside_git" / f"development_200_{region}.source_map.jsonl"),
                "--output", str(root / "outside_git" / f"{region}.text.csv"),
                "--receipt", str(root / "outside_git" / f"{region}.receipt.json"),
                "--text-column", "DESCRIPTION", "--max-rows", "200",
            ], check=True)
        assert len(selected) == 200 and len({x["private_key"] for x in selected}) == 200

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        dev = [row(i, "ks.parquet") for i in range(200)]
        pq.write_table(pa.Table.from_pylist(dev), root / "dev.parquet")
        pq.write_table(pa.Table.from_pylist(dev[:80]), root / "config.parquet")
        bad = root / "bad.plan.jsonl"
        bad.write_text(json.dumps({"region": "unknown", "source_file": "ks.parquet", "source_path": "/raw/ks.parquet"}) + "\n")
        result = run(root, [bad], expect_ok=False)
        assert "unknown region" in result.stderr
    print("PASS: 200/80 key conservation, config subset, regional maps, unknown-region failure")


if __name__ == "__main__":
    main()
