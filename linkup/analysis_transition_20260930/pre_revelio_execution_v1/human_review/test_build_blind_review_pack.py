#!/usr/bin/env python3
"""Synthetic smoke test; no real ad text or private key is persisted."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = Path(__file__).with_name("build_blind_review_pack.py")
SCHEMA = ROOT / "analysis_transition_20260930/execution_oct02_07/reviewer_pack_schema.json"


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        frame = base / "frame.csv"
        frame_metadata = base / "frame_metadata.json"
        heldout = base / "heldout.json"
        heldout_zero = base / "heldout_zero.json"
        predictions = base / "predictions.csv"
        private = base / "private"
        receipt = base / "receipt.json"
        rows = []
        for index in range(48):
            rows.append({
                "private_key": f"synthetic-{index:03d}",
                "original_text": f"Synthetic advertisement {index}; requires {index % 7} years of experience.",
                "sampling_stratum": f"role{index % 2}|experience{index % 2}",
                "first_observation_stratum": "2018-19" if index % 2 else "2020-22",
                "occupation_availability_stratum": "available",
                "challenge_eligible": "true",
                "challenge_stratum": "duration" if index % 2 else "binding",
            })
        write_csv(frame, rows)
        frame_metadata.write_text(json.dumps({
            "key_namespace": "synthetic_job_key_v1",
            "stable_key_type": "string",
            "source_provenance": "generated synthetic canonical frame",
        }), encoding="utf-8")
        heldout.write_text(json.dumps({
            "key_namespace": "synthetic_job_key_v1",
            "stable_key_type": "string",
            "source_provenance": "generated synthetic heldout manifest",
            "private_keys": [f"synthetic-{index:03d}" for index in range(4)],
        }), encoding="utf-8")
        heldout_zero.write_text(json.dumps({
            "key_namespace": "synthetic_job_key_v1",
            "stable_key_type": "string",
            "source_provenance": "generated disjoint synthetic heldout manifest",
            "private_keys": [f"heldout-only-{index:03d}" for index in range(4)],
        }), encoding="utf-8")
        write_csv(predictions, [
            {"private_key": row["private_key"], "extractor_prediction": "synthetic_hidden"}
            for row in rows
        ])
        subprocess.run([
            sys.executable, str(SCRIPT),
            "--frame", str(frame),
            "--frame-metadata", str(frame_metadata),
            "--heldout-key-manifest", str(heldout),
            "--reviewer-schema", str(SCHEMA),
            "--predictions", str(predictions),
            "--private-output-dir", str(private),
            "--public-receipt", str(receipt),
            "--repo-root", str(ROOT),
        ], check=True)
        result = json.loads(receipt.read_text(encoding="utf-8"))
        assert result["counts"]["core_selected"] == 32
        assert result["counts"]["challenge_selected"] == 8
        assert result["counts"]["core_dual_review"] == 8
        assert result["counts"]["heldout_matches_excluded"] == 4
        with (private / "reviewer_pack.csv").open(encoding="utf-8", newline="") as handle:
            pack = list(csv.DictReader(handle))
        assert len(pack) == 40
        assert all("private_key" not in row for row in pack)
        assert all("extractor_prediction" not in row for row in pack)
        assert all("synthetic_hidden" not in json.dumps(row) for row in pack)
        with (private / "review_assignments.csv").open(encoding="utf-8", newline="") as handle:
            assignments = list(csv.DictReader(handle))
        assert len(assignments) == 48
        private_zero = base / "private_zero"
        receipt_zero = base / "receipt_zero.json"
        subprocess.run([
            sys.executable, str(SCRIPT),
            "--frame", str(frame),
            "--frame-metadata", str(frame_metadata),
            "--heldout-key-manifest", str(heldout_zero),
            "--reviewer-schema", str(SCHEMA),
            "--private-output-dir", str(private_zero),
            "--public-receipt", str(receipt_zero),
            "--repo-root", str(ROOT),
        ], check=True)
        zero_result = json.loads(receipt_zero.read_text(encoding="utf-8"))
        assert zero_result["counts"]["heldout_matches_excluded"] == 0
        assert zero_result["counts"]["heldout_key_count"] == 4
        assert zero_result["counts"]["core_selected"] == 32
        assert zero_result["counts"]["challenge_selected"] == 8
        print("synthetic_smoke_test_ok")


if __name__ == "__main__":
    main()
