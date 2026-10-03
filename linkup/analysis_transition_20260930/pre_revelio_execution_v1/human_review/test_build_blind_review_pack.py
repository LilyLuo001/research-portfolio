#!/usr/bin/env python3
"""Synthetic smoke test; it never persists real text or keys."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

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
        index, parquet, duplicates, text, metadata, heldout = base / "index.csv", base / "joined.parquet", base / "duplicates.parquet", base / "selected.csv", base / "metadata.json", base / "heldout.json"
        private, receipt = base / "private", base / "receipt.json"
        parquet_rows, rows = [], []
        for number in range(48):
            tech = number % 5
            exp = number % 4
            item = {"JOB_HASH": f"{number:032x}", "SOURCE_FILE": f"source-{number % 3}.parquet", "SOURCE_ROW": number, "RECORD_SOURCE_ROW": number + 100,
                    "CREATED": __import__("datetime").datetime(2020 + number % 4, 1, 1), "usable": True, "OCCUPATION_MAJOR": "11" if number % 2 else None,
                    "tech_generative_ai_use_explicit": tech == 0, "tech_generative_ai_develop_explicit": tech == 1, "tech_traditional_software_use_explicit": tech == 2, "tech_traditional_software_develop_explicit": tech == 3,
                    "tech_generative_ai_detected": tech in (0, 1), "tech_predictive_ai_detected": False, "tech_unspecified_ai_detected": False,
                    "exp_specific_tool_main": exp == 0, "exp_industry_domain_main": exp == 1, "exp_general_work_main": exp == 2,
                    "exp_specific_tool_broad": exp in (0, 3), "exp_industry_domain_broad": exp == 1, "exp_general_work_broad": exp == 2,
                    "exp_specific_tool_exact_or_unspecified": number % 11 == 0, "exp_industry_domain_exact_or_unspecified": False, "exp_general_work_exact_or_unspecified": False}
            parquet_rows.append(item)
            private_key = json.dumps([item[name] for name in ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")], separators=(",", ":"))
            tech_label = ("genAI-use", "genAI-develop", "software-use-no-AI", "software-develop-no-AI", "other")[tech]
            exp_label = ("specific_tool", "industry_domain", "general_work", "none")[exp]
            challenge = "binding_broad_not_explicit" if exp == 3 else "exact_or_unspecified_duration" if number % 11 == 0 else ""
            rows.append({"private_key": private_key, "sampling_stratum": tech_label + "|" + exp_label, "first_observation_stratum": str(item["CREATED"].year), "occupation_availability_stratum": "unknown", "challenge_eligible": str(bool(challenge)).lower(), "challenge_stratum": challenge})
        write_csv(index, rows)
        pq.write_table(pa.Table.from_pylist(parquet_rows), parquet)
        pq.write_table(pa.table({"JOB_HASH": pa.array([], type=pa.string())}), duplicates)
        metadata.write_text(json.dumps({"key_namespace": "synthetic_job_key_v1", "stable_key_type": "string", "source_provenance": "synthetic verified full index", "verified_unique_private_keys": True, "verified_full_frame_rows": 48, "source_receipts": ["synthetic-source-receipt"]}), encoding="utf-8")
        heldout.write_text(json.dumps({"key_namespace": "synthetic_job_key_v1", "stable_key_type": "string", "source_provenance": "synthetic heldout manifest", "private_keys": [f"heldout-{number:03d}" for number in range(400)]}), encoding="utf-8")
        command = [sys.executable, str(SCRIPT), "--frame-index", str(index), "--frame-metadata", str(metadata), "--heldout-key-manifest", str(heldout), "--reviewer-schema", str(SCHEMA), "--private-output-dir", str(private), "--public-receipt", str(receipt), "--repo-root", str(ROOT)]
        subprocess.run(command, check=True)
        selection = json.loads((private / "selected_key_manifest.json").read_text(encoding="utf-8"))
        assert len(selection["selected"]) == 40
        assert json.loads(receipt.read_text(encoding="utf-8"))["status"] == "blind_pack_keys_selected_pending_text"
        write_csv(text, [{"private_key": row["private_key"], "original_text": f"Synthetic ad {number}"} for number, row in enumerate(selection["selected"])])
        subprocess.run(command + ["--selected-text", str(text)], check=True)
        result = json.loads(receipt.read_text(encoding="utf-8"))
        assert result["status"] == "blind_pack_built"
        assert result["counts"]["core_selected"] == 32
        assert result["counts"]["challenge_selected"] == 8
        assert result["counts"]["core_dual_review"] == 8
        with (private / "reviewer_pack.csv").open(encoding="utf-8", newline="") as handle:
            pack = list(csv.DictReader(handle))
        assert len(pack) == 40 and all("private_key" not in row for row in pack)
        with (private / "review_assignments.csv").open(encoding="utf-8", newline="") as handle:
            assignments = list(csv.DictReader(handle))
        assert len(assignments) == 48
        try:
            import duckdb  # available in the execution runtime used for full Parquet
        except ImportError:
            duckdb = None
        if duckdb:
            parquet_private, parquet_receipt = base / "parquet-private", base / "parquet-receipt.json"
            parquet_command = [sys.executable, str(SCRIPT), "--frame-parquet", str(parquet), "--duplicate-job-hash-parquet", str(duplicates), "--frame-metadata", str(metadata), "--heldout-key-manifest", str(heldout), "--reviewer-schema", str(SCHEMA), "--private-output-dir", str(parquet_private), "--public-receipt", str(parquet_receipt), "--repo-root", str(ROOT)]
            subprocess.run(parquet_command, check=True)
            parquet_selection = json.loads((parquet_private / "selected_key_manifest.json").read_text(encoding="utf-8"))
            assert parquet_selection["selected"] == selection["selected"]
            assert parquet_selection["core_sizes"] == selection["core_sizes"]
            assert parquet_selection["core_alloc"] == selection["core_alloc"]
        print("synthetic_streaming_smoke_test_ok")


if __name__ == "__main__":
    main()
