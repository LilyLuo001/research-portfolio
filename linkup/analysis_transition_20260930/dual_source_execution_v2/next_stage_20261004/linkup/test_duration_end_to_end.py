#!/usr/bin/env python3
"""Bounded end-to-end smoke test for summarize_sample_durations.py."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import duckdb


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def sql_string(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="duration-e2e-") as temporary:
        root = Path(temporary)
        sample = root / "sample.parquet"
        duration = root / "duration.parquet"
        sample_receipt = root / "sample_receipt.json"
        output = root / "output"
        con = duckdb.connect()
        con.execute("""
          CREATE TABLE sample AS
          SELECT CASE WHEN i < 4000 THEN 'A' WHEN i < 8000 THEN 'B' ELSE 'C' END arm,
                 2024 created_year,'11' OCCUPATION_MAJOR,'1' CENSUS_REGION,
                 'job-' || i::VARCHAR JOB_HASH,'file.parquet' SOURCE_FILE,
                 i SOURCE_ROW,i RECORD_SOURCE_ROW,1.0 nested_design_weight,
                 CASE WHEN i < 4000 THEN 0.4 WHEN i < 8000 THEN 0.4 ELSE 0.2 END
                   / CASE WHEN i < 4000 THEN 4000 WHEN i < 8000 THEN 4000 ELSE 2000 END
                   pooled_cell_standardization_weight
          FROM range(10000) t(i)
        """)
        con.execute("COPY sample TO " + sql_string(sample) + " (FORMAT PARQUET)")
        con.execute("""
          CREATE TABLE duration AS
          SELECT * FROM (VALUES
            ('job-0','file.parquet',0,0,1,'general_work',2.0,NULL,'years','minimum','required'),
            ('job-1','file.parquet',1,1,1,'general_work',3.0,5.0,'year','range','required'),
            ('job-4000','file.parquet',4000,4000,1,'industry_domain',NULL,4.0,'years','exact_or_unspecified','preferred'),
            ('job-8000','file.parquet',8000,8000,1,'general_work',1.0,NULL,'years','minimum','required'),
            ('job-2','file.parquet',2,999999,1,'general_work',9.0,NULL,'years','minimum','required')
          ) t(JOB_HASH,SOURCE_FILE,SOURCE_ROW,RECORD_SOURCE_ROW,EVIDENCE_ORDINAL,OBJECT_TYPE,
              MIN_YEARS,MAX_YEARS,DURATION_UNIT,BOUND_TYPE,REQUIREMENT_STRENGTH)
        """)
        con.execute("COPY duration TO " + sql_string(duration) + " (FORMAT PARQUET)")
        con.close()
        sample_receipt.write_text(json.dumps({
            "status": "complete", "counts": {"A": 4000, "B": 4000, "C": 2000},
            "private_key_output": {"sha256": sha256(sample)},
        }))
        subprocess.run([
            sys.executable, str(Path(__file__).with_name("summarize_sample_durations.py")),
            "--sample", str(sample), "--sample-receipt", str(sample_receipt),
            "--duration-glob", str(duration), "--output-dir", str(output),
            "--threads", "1", "--memory-limit", "256MB",
        ], check=True, stdout=subprocess.PIPE, text=True)
        expected = {
            "raw_numeric_detection.csv", "design_weighted_numeric_detection.csv",
            "pooled_cell_standardized_numeric_detection.csv", "raw_numeric_clause_years.csv",
            "design_weighted_numeric_clause_years.csv", "duration_numeric_quality_counts.csv",
        }
        assert expected == {path.name for path in output.glob("*.csv")}
        detection = rows(output / "raw_numeric_detection.csv")
        overall_a = [row for row in detection if row["arm"] == "A" and row["OBJECT_TYPE"] == "general_work" and row["scope"] == "overall"]
        assert len(overall_a) == 1 and overall_a[0]["raw_numeric_detected_ads"] == "2"
        clauses = rows(output / "raw_numeric_clause_years.csv")
        assert {row["BOUND_TYPE"] for row in clauses} == {"minimum", "range", "exact_or_unspecified"}
        assert sum(int(row["raw_clause_rows"]) for row in clauses) == 4
        receipt = json.loads((output / "DURATION_EXECUTION_RECEIPT.json").read_text())
        assert receipt["status"] == "complete" and receipt["matched_numeric_clause_rows"] == 4
        for name in expected:
            assert receipt["outputs"][name] == sha256(output / name)
    print("ok: actual summarizer end-to-end exports, overall numerator, bound separation, four-key exclusion, and receipt hashes")


if __name__ == "__main__":
    main()
