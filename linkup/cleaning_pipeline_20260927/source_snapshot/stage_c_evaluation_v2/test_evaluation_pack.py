#!/usr/bin/env python3
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def jsonl(path):
    # File iteration splits physical LF records without treating Unicode line
    # separators embedded inside a valid JSON string as record delimiters.
    with Path(path).open() as handle:
        return [json.loads(x) for x in handle if x.strip()]


def main(root):
    root = Path(root)
    manifest = json.loads((root / "sample_manifest.json").read_text())
    assert manifest["target_total"] == 1000
    assert manifest["calibration_rows"] == 600
    assert manifest["sealed_test_rows"] == 400
    assert manifest["human_labels_present"] is False
    assert manifest["automatic_release_allowed"] is False
    for rel, item in manifest["files"].items():
        assert sha(root / rel) == item["sha256"], rel
    calibration = jsonl(root / "calibration/texts.jsonl")
    test = jsonl(root / "sealed_test/texts.jsonl")
    assert len(calibration) == 600 and len(test) == 400
    assert not ({x["annotation_id"] for x in calibration} & {x["annotation_id"] for x in test})
    for row in calibration + test:
        assert set(row) == {"annotation_id", "raw_text"}
        assert "PREDICTED_PATH" not in row and "prediction" not in row
    for rel, n in (("calibration/annotations_blank.csv", 600), ("sealed_test/annotations_blank.csv", 400)):
        with (root / rel).open(newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == n
        for row in rows:
            assert row["annotation_status"] == "unlabeled"
            assert row["adjudication_status"] == "pending"
            assert all(row[k] == "" for k in ("annotator_id", "presence", "strength", "experience_object",
                                                "technology_class", "technology_role", "task_family",
                                                "adjudicated_label"))
    private = jsonl(root / "selection_metadata_private.jsonl")
    assert len(private) == 1000
    assert len({x["JOB_HASH"] for x in private}) == 1000
    assert len({x["EMPLOYER_KEY"] for x in private}) == 1000
    assert len({x["NORMALIZED_TEXT_SHA256"] for x in private}) == 1000
    assert len({x["NEAR_TEMPLATE_SIGNATURE"] for x in private}) == 1000
    assert Counter(x["SELECTION_COMPONENT"] for x in private) == Counter({"probability_core": 800, "prediction_supplement": 200})
    assert Counter(x["SPLIT"] for x in private) == Counter({"calibration": 600, "sealed_test": 400})
    periods = Counter(x["TIME_STRATUM"] for x in private)
    assert periods == Counter({"2015": 100, "2016-17": 130, "2018-19": 130, "2020-22": 160,
                               "2023": 120, "2024": 120, "2025": 120, "2026_partial": 120})
    grouping = json.loads((root / "grouping_quality_report.json").read_text())
    assert grouping["cross_split_employer_overlap"] == 0
    assert grouping["cross_split_exact_template_overlap"] == 0
    assert grouping["cross_split_near_signature_overlap"] == 0
    print(json.dumps({"status": "PASS", "rows": len(private), "periods": periods}))


if __name__ == "__main__":
    main(sys.argv[1])
