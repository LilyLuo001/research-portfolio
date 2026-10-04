#!/usr/bin/env python3
"""Summarize legacy-rule numeric year clauses for the fixed research sample."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

import duckdb


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def sql_string(value: object) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def export(con, query: str, path: Path) -> None:
    con.execute(f"COPY ({query}) TO {sql_string(path)} (HEADER, DELIMITER ',')")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--sample-receipt", type=Path, required=True)
    parser.add_argument("--duration-glob", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--memory-limit", default="8GB")
    args = parser.parse_args()
    if not args.memory_limit[:-2].isdigit() or args.memory_limit[-2:] not in {"GB", "MB"}:
        raise ValueError("memory limit must be an integer followed by GB or MB")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    sample_receipt = json.loads(args.sample_receipt.read_text())
    if sample_receipt.get("status") != "complete" or sample_receipt.get("counts") != {"A": 4000, "B": 4000, "C": 2000}:
        raise RuntimeError("sample receipt is not a complete fixed 4,000/4,000/2,000 run")
    if sample_receipt.get("private_key_output", {}).get("sha256") != sha256(args.sample):
        raise RuntimeError("sample receipt SHA-256 does not bind the supplied private sample")

    con = duckdb.connect()
    con.execute(f"PRAGMA threads={args.threads}")
    con.execute(f"PRAGMA memory_limit='{args.memory_limit}'")
    con.execute(f"CREATE VIEW sample AS SELECT * FROM read_parquet({sql_string(args.sample)})")
    con.execute(f"CREATE VIEW duration_source AS SELECT * FROM read_parquet({sql_string(args.duration_glob)}, union_by_name=true)")
    con.execute("""
      CREATE TABLE matched_all AS
      SELECT s.arm,s.created_year,s.OCCUPATION_MAJOR,s.CENSUS_REGION,
             s.JOB_HASH,s.nested_design_weight,s.pooled_cell_standardization_weight,
             d.EVIDENCE_ORDINAL,d.OBJECT_TYPE,d.MIN_YEARS,d.MAX_YEARS,
             d.DURATION_UNIT,d.BOUND_TYPE,d.REQUIREMENT_STRENGTH
      FROM sample s JOIN duration_source d
        USING (JOB_HASH,SOURCE_FILE,SOURCE_ROW,RECORD_SOURCE_ROW)
      WHERE d.OBJECT_TYPE IN ('general_work','industry_domain')
    """)
    con.execute("""
      CREATE TABLE matched AS SELECT * FROM matched_all
      WHERE lower(DURATION_UNIT) IN ('year','years') AND coalesce(MIN_YEARS,MAX_YEARS) IS NOT NULL
        AND (MIN_YEARS IS NULL OR MIN_YEARS>=0) AND (MAX_YEARS IS NULL OR MAX_YEARS>=0)
        AND (MIN_YEARS IS NULL OR MAX_YEARS IS NULL OR MAX_YEARS>=MIN_YEARS)
    """)
    con.execute("""
      CREATE TABLE detected AS
      SELECT DISTINCT arm,created_year,OCCUPATION_MAJOR,CENSUS_REGION,JOB_HASH,
             nested_design_weight,pooled_cell_standardization_weight,OBJECT_TYPE
      FROM matched
    """)
    sample_n = con.execute("SELECT count(*) FROM sample").fetchone()[0]
    arm_counts = dict(con.execute("SELECT arm,count(*) FROM sample GROUP BY arm ORDER BY arm").fetchall())
    if sample_n != 10000 or arm_counts != {"A": 4000, "B": 4000, "C": 2000}:
        raise RuntimeError(f"duration job requires complete 10,000 sample, found {arm_counts}")

    objects = "(SELECT * FROM (VALUES ('general_work'),('industry_domain')) v(OBJECT_TYPE))"
    raw_detection = f"""
      WITH denom AS (
        SELECT arm,'overall' scope,NULL::INTEGER created_year,count(*) ads FROM sample GROUP BY arm
        UNION ALL SELECT arm,'created_year',created_year,count(*) FROM sample GROUP BY arm,created_year
      ), numer AS (
        SELECT arm,OBJECT_TYPE,'overall' scope,NULL::INTEGER created_year,count(DISTINCT JOB_HASH) detected_ads FROM detected GROUP BY arm,OBJECT_TYPE
        UNION ALL SELECT arm,OBJECT_TYPE,'created_year',created_year,count(DISTINCT JOB_HASH) FROM detected GROUP BY arm,OBJECT_TYPE,created_year
      )
      SELECT d.arm,o.OBJECT_TYPE,d.scope,d.created_year,d.ads raw_sample_ads,
             coalesce(n.detected_ads,0) raw_numeric_detected_ads,
             coalesce(n.detected_ads,0)::DOUBLE/d.ads raw_numeric_detected_share
      FROM denom d CROSS JOIN {objects} o
      LEFT JOIN numer n ON d.arm=n.arm AND o.OBJECT_TYPE=n.OBJECT_TYPE AND d.scope=n.scope
       AND d.created_year IS NOT DISTINCT FROM n.created_year
      ORDER BY arm,OBJECT_TYPE,scope,created_year
    """
    weighted_detection = f"""
      WITH denom AS (
        SELECT arm,'overall' scope,NULL::INTEGER created_year,sum(nested_design_weight) weighted_ads FROM sample GROUP BY arm
        UNION ALL SELECT arm,'created_year',created_year,sum(nested_design_weight) FROM sample GROUP BY arm,created_year
      ), numer AS (
        SELECT arm,OBJECT_TYPE,'overall' scope,NULL::INTEGER created_year,sum(nested_design_weight) weighted_detected_ads FROM detected GROUP BY arm,OBJECT_TYPE
        UNION ALL SELECT arm,OBJECT_TYPE,'created_year',created_year,sum(nested_design_weight) FROM detected GROUP BY arm,OBJECT_TYPE,created_year
      )
      SELECT d.arm,o.OBJECT_TYPE,d.scope,d.created_year,d.weighted_ads,
             coalesce(n.weighted_detected_ads,0) weighted_numeric_detected_ads,
             coalesce(n.weighted_detected_ads,0)/d.weighted_ads design_weighted_numeric_detected_share
      FROM denom d CROSS JOIN {objects} o
      LEFT JOIN numer n ON d.arm=n.arm AND o.OBJECT_TYPE=n.OBJECT_TYPE AND d.scope=n.scope
       AND d.created_year IS NOT DISTINCT FROM n.created_year
      ORDER BY arm,OBJECT_TYPE,scope,created_year
    """
    standardized_detection = f"""
      WITH cells AS (
        SELECT arm,OCCUPATION_MAJOR,CENSUS_REGION,created_year,
               max(pooled_cell_standardization_weight) W_h,count(*) n
        FROM sample GROUP BY 1,2,3,4
      ), hits AS (
        SELECT arm,OBJECT_TYPE,OCCUPATION_MAJOR,CENSUS_REGION,created_year,count(DISTINCT JOB_HASH) hit
        FROM detected GROUP BY 1,2,3,4,5
      )
      SELECT c.arm,o.OBJECT_TYPE,sum(c.W_h*coalesce(h.hit,0)::DOUBLE/c.n) pooled_cell_standardized_numeric_detected_share,
             sum(c.W_h) pooled_cell_weight_sum,count(*) supported_cells
      FROM cells c CROSS JOIN {objects} o
      LEFT JOIN hits h USING (arm,OBJECT_TYPE,OCCUPATION_MAJOR,CENSUS_REGION,created_year)
      GROUP BY c.arm,o.OBJECT_TYPE ORDER BY c.arm,o.OBJECT_TYPE
    """
    raw_clauses = """
      SELECT arm,OBJECT_TYPE,created_year,REQUIREMENT_STRENGTH,BOUND_TYPE,
             count(*) raw_clause_rows,count(DISTINCT JOB_HASH) raw_distinct_ads,
             avg(coalesce(MIN_YEARS,MAX_YEARS)) raw_mean_stored_bound_value_years,
             quantile_cont(coalesce(MIN_YEARS,MAX_YEARS),0.25) raw_p25_stored_bound_value_years,
             quantile_cont(coalesce(MIN_YEARS,MAX_YEARS),0.5) raw_median_stored_bound_value_years,
             quantile_cont(coalesce(MIN_YEARS,MAX_YEARS),0.75) raw_p75_stored_bound_value_years,
             count(MAX_YEARS) raw_clauses_with_max_years,avg(MAX_YEARS) raw_mean_max_years
      FROM matched GROUP BY 1,2,3,4,5 ORDER BY 1,2,3,4,5
    """
    weighted_clauses = """
      SELECT arm,OBJECT_TYPE,created_year,REQUIREMENT_STRENGTH,BOUND_TYPE,
             sum(nested_design_weight) design_weighted_clause_mass,
             sum(nested_design_weight*coalesce(MIN_YEARS,MAX_YEARS))/sum(nested_design_weight) design_weighted_mean_stored_bound_value_years,
             sum(nested_design_weight) FILTER (WHERE MAX_YEARS IS NOT NULL) design_weighted_clause_mass_with_max,
             sum(nested_design_weight*MAX_YEARS) FILTER (WHERE MAX_YEARS IS NOT NULL)
               /sum(nested_design_weight) FILTER (WHERE MAX_YEARS IS NOT NULL) design_weighted_mean_max_years
      FROM matched GROUP BY 1,2,3,4,5 ORDER BY 1,2,3,4,5
    """
    quality = """
      SELECT arm,OBJECT_TYPE,created_year,REQUIREMENT_STRENGTH,coalesce(BOUND_TYPE,'<NULL>') BOUND_TYPE,
             count(*) clause_rows,
             count(*) FILTER (WHERE lower(DURATION_UNIT) IN ('year','years') AND coalesce(MIN_YEARS,MAX_YEARS) IS NOT NULL
               AND (MIN_YEARS IS NULL OR MIN_YEARS>=0) AND (MAX_YEARS IS NULL OR MAX_YEARS>=0)
               AND (MIN_YEARS IS NULL OR MAX_YEARS IS NULL OR MAX_YEARS>=MIN_YEARS)) valid_numeric_year_clause_rows,
             count(*) FILTER (WHERE MIN_YEARS IS NULL AND MAX_YEARS IS NULL) missing_numeric_value_rows,
             count(*) FILTER (WHERE DURATION_UNIT IS NULL OR lower(DURATION_UNIT) NOT IN ('year','years')) non_year_unit_rows,
             count(*) FILTER (WHERE MIN_YEARS<0 OR MAX_YEARS<0 OR (MIN_YEARS IS NOT NULL AND MAX_YEARS IS NOT NULL AND MAX_YEARS<MIN_YEARS)) invalid_numeric_rows,
             count(*) FILTER (WHERE BOUND_TYPE IS NULL OR BOUND_TYPE NOT IN ('minimum','range','exact_or_unspecified')) unknown_bound_rows
      FROM matched_all GROUP BY 1,2,3,4,5 ORDER BY 1,2,3,4,5
    """
    outputs = {
        "raw_numeric_detection.csv": raw_detection,
        "design_weighted_numeric_detection.csv": weighted_detection,
        "pooled_cell_standardized_numeric_detection.csv": standardized_detection,
        "raw_numeric_clause_years.csv": raw_clauses,
        "design_weighted_numeric_clause_years.csv": weighted_clauses,
        "duration_numeric_quality_counts.csv": quality,
    }
    for name, query in outputs.items():
        export(con, query, args.output_dir / name)
    matched_rows = con.execute("SELECT count(*) FROM matched").fetchone()[0]
    matched_ads = con.execute("SELECT count(DISTINCT JOB_HASH) FROM matched").fetchone()[0]
    con.close()
    receipt = {
        "status": "complete", "sample_rows": sample_n, "arm_counts": arm_counts,
        "matched_numeric_clause_rows": matched_rows, "matched_distinct_ads": matched_ads,
        "objects_executed": ["general_work", "industry_domain"],
        "occupation_task": "unavailable in frozen legacy duration sidecars; no values fabricated",
        "interpretation": "legacy-rule numeric clause summaries, not validated semantic measurements",
        "denominators": "detection tables use ads; clause-year tables retain every valid numeric clause and also report distinct ads; quality table counts missing, non-year, invalid, and unknown-bound rows",
        "absence": "no matched duration sidecar row means no legacy-rule numeric duration detected; it is not zero experience",
        "multiple_durations": "retained as separate clause rows; no cross-clause ad-level minimum/maximum collapse; BOUND_TYPE remains a grouping column",
        "stored_bound_value_semantics": "coalesce(MIN_YEARS,MAX_YEARS): stored value for exact_or_unspecified, lower endpoint for minimum/range, and upper endpoint for maximum-only; BOUND_TYPE stays explicit",
        "canonical_join": "JOB_HASH + SOURCE_FILE + SOURCE_ROW + RECORD_SOURCE_ROW",
        "accepted_year_units": ["year", "years"],
        "weights": "design-weighted files use nested inverse inclusion probability; standardized file separately applies original pooled-cell W_h",
        "sample_sha256": sha256(args.sample),
        "sample_receipt_sha256": sha256(args.sample_receipt),
        "outputs": {name: sha256(args.output_dir / name) for name in outputs},
    }
    atomic_json(args.output_dir / "DURATION_EXECUTION_RECEIPT.json", receipt)
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
