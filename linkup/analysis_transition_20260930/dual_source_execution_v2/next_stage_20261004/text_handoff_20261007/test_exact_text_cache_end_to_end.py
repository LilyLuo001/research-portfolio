#!/usr/bin/env python3
"""Synthetic 10,000-row QA for exact-text cache construction."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

KEYS = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
REGIONS = (("kunshan", 0, 5495), ("wuzhen", 5495, 10000))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    builder = Path(__file__).with_name("build_exact_text_cache.py")
    with tempfile.TemporaryDirectory(prefix="exact-cache-qa-") as temporary:
        root = Path(temporary)
        handoff = root / "handoff"
        selections = handoff / "private" / "run-123660254"
        materialized = root / "materialized"
        selections.mkdir(parents=True)
        materialized.mkdir()
        sample = root / "sample.parquet"
        public_receipt = root / "PUBLIC_RECEIPT.json"

        arrays = [
            pa.array([f"job-{i}" for i in range(10000)], type=pa.string()),
            pa.array([f"pack-{i % 7}.parquet" for i in range(10000)], type=pa.string()),
            pa.array(range(10000), type=pa.int64()),
            pa.array([i + 10000 for i in range(10000)], type=pa.int64()),
            pa.array(["A" if i < 4000 else "B" if i < 8000 else "C" for i in range(10000)], type=pa.string()),
            pa.array([0.25] * 10000, type=pa.float64()),
            pa.array([4.0] * 10000, type=pa.float64()),
            pa.array([0.5] * 10000, type=pa.float32()),
            pa.array([0.0001] * 10000, type=pa.float64()),
            pa.array([None] * 10000, type=pa.int32()),
        ]
        names = [*KEYS, "arm", "inclusion_probability", "design_weight", "pi", "W_h", "typed_all_null"]
        sample_table = pa.Table.from_arrays(arrays, names=names)
        pq.write_table(sample_table, sample)

        long_text = "L" * 200000
        for region, start, stop in REGIONS:
            selected = []
            output = materialized / f"fixed10000_{region}.text.csv"
            selection = selections / f"fixed10000_{region}.selection.json"
            source_map = selections / f"fixed10000_{region}.source_map.jsonl"
            with output.open("w", encoding="utf-8", newline="") as handle:
                fields = ["private_key", "original_text", *KEYS, "ORIGINAL_TEXT"]
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader()
                for i in range(start, stop):
                    parts = [f"job-{i}", f"pack-{i % 7}.parquet", i, i + 10000]
                    key = json.dumps(parts, separators=(",", ":"))
                    text = long_text if i == 0 else f"same-text-{i % 99}"
                    selected.append({"private_key": key})
                    writer.writerow({
                        "private_key": key, "original_text": text,
                        **dict(zip(KEYS, parts)), "ORIGINAL_TEXT": text,
                    })
            selection.write_text(json.dumps({"selected": selected}))
            source_map.write_text("{}\n")
            receipt = {
                "status": "complete", "rows": stop - start,
                "selection_sha256": sha256(selection), "source_map_sha256": sha256(source_map),
                "output_sha256": sha256(output),
            }
            (materialized / f"fixed10000_{region}.materialize_receipt.json").write_text(json.dumps(receipt))

        command = [
            sys.executable, str(builder), "--sample", str(sample), "--handoff-dir", str(handoff),
            "--materialized-dir", str(materialized), "--public-receipt", str(public_receipt),
        ]
        subprocess.run(command, check=True, timeout=120, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        receipt = json.loads(public_receipt.read_text())
        assert receipt["status"] == "complete" and receipt["sample_rows"] == 10000
        assert receipt["unique_exact_texts_for_inference"] == 100
        assert receipt["probability_weight_fields_retained"] == ["inclusion_probability", "design_weight", "pi", "W_h"]
        assert receipt["sample_arrow_schema_preserved"] is True

        merged = pq.read_table(materialized / "MERGED_FIXED10000_EXACT_TEXT_PRIVATE.parquet")
        assert merged.num_rows == 10000
        assert merged.schema.names[:len(sample_table.schema)] == sample_table.schema.names
        assert all(merged.schema.field(i).type == sample_table.schema.field(i).type for i in range(len(sample_table.schema)))
        assert merged.column("typed_all_null").type == pa.int32() and merged.column("typed_all_null").null_count == 10000
        assert set(zip(*(merged.column(key).to_pylist() for key in KEYS))) == set(zip(*(sample_table.column(key).to_pylist() for key in KEYS)))

        manifest = pq.read_table(materialized / "EXACT_TEXT_SHA_CACHE_MANIFEST_PRIVATE.parquet")
        assert manifest.num_rows == 10000 and {"pi", "W_h", "inclusion_probability", "design_weight"} <= set(manifest.schema.names)
        assert manifest.column("pi").to_pylist() == sample_table.column("pi").to_pylist()
        cache = pq.read_table(materialized / "UNIQUE_EXACT_TEXT_INFERENCE_CACHE_PRIVATE.parquet")
        assert cache.num_rows == 100 and long_text in cache.column("original_text").to_pylist()

        tampered = materialized / "fixed10000_wuzhen.text.csv"
        with tampered.open("a") as handle:
            handle.write("\n")
        rejected = subprocess.run(command, timeout=120, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert rejected.returncode != 0

    qa = {
        "status": "PASS",
        "fixture_rows": 10000,
        "regional_rows": {"kunshan": 5495, "wuzhen": 4505},
        "checks": [
            "long CSV field parsed without truncation", "exact 10,000-key conservation",
            "exact duplicate text cached once", "original Arrow field types retained including typed all-null column",
            "pi, W_h, probability, and weight values retained", "tampered regional CSV rejected by receipt hash",
        ],
        "builder_sha256": sha256(builder),
        "test_sha256": sha256(Path(__file__)),
        "privacy": "synthetic fixture only; no private sample keys, probabilities, paths, or text read or printed",
    }
    args.receipt.write_text(json.dumps(qa, indent=2, sort_keys=True) + "\n")
    print("ok: synthetic 10,000-row exact-text cache QA passed")


if __name__ == "__main__":
    main()
