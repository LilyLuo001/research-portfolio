#!/usr/bin/env python3
"""Mechanically select 4 calibration-core ads per frozen time stratum."""
import argparse
import hashlib
import json
import os
from collections import Counter, defaultdict
from pathlib import Path

SEED = "diagnostic32-20260927"
PERIODS = ["2015", "2016-17", "2018-19", "2020-22", "2023", "2024", "2025", "2026_partial"]


def rank(value):
    return hashlib.sha256((SEED + "\0" + value).encode()).hexdigest()


def read_jsonl(path):
    with Path(path).open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path, rows):
    temp = Path(str(path) + ".tmp")
    with temp.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    os.replace(temp, path)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pack", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    pack, out = Path(a.pack), Path(a.out)
    if out.exists():
        raise RuntimeError("immutable diagnostic output already exists")
    out.mkdir(parents=True)
    texts = {r["annotation_id"]: r["raw_text"] for r in read_jsonl(pack / "calibration/texts.jsonl")}
    metadata = read_jsonl(pack / "selection_metadata_private.jsonl")
    by_period = defaultdict(list)
    for row in metadata:
        if row["SPLIT"] == "calibration" and row["SELECTION_COMPONENT"] == "probability_core":
            by_period[row["TIME_STRATUM"]].append(row)
    selected = []
    for period in PERIODS:
        frame = sorted(by_period[period], key=lambda r: rank(r["JOB_HASH"]))
        if len(frame) < 4:
            raise RuntimeError("calibration core shortfall %s: %d < 4" % (period, len(frame)))
        selected.extend(frame[:4])
    selected = sorted(selected, key=lambda r: rank("id:" + r["JOB_HASH"]))
    public, hidden = [], []
    for i, row in enumerate(selected, 1):
        diagnostic_id = "D%03d" % i
        public.append({"diagnostic_id": diagnostic_id, "raw_text": texts[row["ANNOTATION_ID"]]})
        hidden.append({"diagnostic_id": diagnostic_id, "calibration_annotation_id": row["ANNOTATION_ID"],
                       "time_stratum": row["TIME_STRATUM"], "job_hash": row["JOB_HASH"],
                       "selection_component": row["SELECTION_COMPONENT"]})
    write_jsonl(out / "texts.jsonl", public)
    write_jsonl(out / "hidden_mapping.jsonl", hidden)
    manifest = {"status": "complete", "seed": SEED, "rows": len(public), "per_time_stratum": 4,
                "source_split": "calibration", "source_component": "probability_core",
                "sealed_test_accessed": False,
                "time_counts": dict(sorted(Counter(r["time_stratum"] for r in hidden).items())),
                "texts_sha256": sha(out / "texts.jsonl"), "hidden_mapping_sha256": sha(out / "hidden_mapping.jsonl")}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps(manifest, sort_keys=True))


if __name__ == "__main__":
    main()
