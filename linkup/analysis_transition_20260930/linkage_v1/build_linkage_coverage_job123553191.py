#!/usr/bin/env python3
"""Aggregate-only Records and snapshot O*NET linkage coverage.

Inputs may be a tiny key projection or full lean ad_status files. The program
never writes row-level joins. Remote rows are deliberately outside this rule.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path

import duckdb
import pyarrow.parquet as pq

KEYS = ["JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW"]
VERSION = "linkage_v1.0.0"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def sql_list(values: list[str]) -> str:
    return ",".join("'" + value.replace("'", "''") + "'" for value in values)


def official_codes(path: Path) -> set[str]:
    with path.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    if not rows:
        raise RuntimeError("official taxonomy is empty")
    names = rows[0].keys()
    field = next((x for x in names if x.lower().replace(" ", "") in {"o*net-soccode", "o*net-soc2019code", "onetsoccode", "onetsoc2019code", "code"}), None)
    if field is None:
        raise RuntimeError("official taxonomy lacks an O*NET-SOC code column")
    return {str(row[field]).strip() for row in rows if str(row.get(field, "")).strip()}


def one(con, query: str) -> dict:
    cur = con.execute(query)
    names = [item[0] for item in cur.description]
    return dict(zip(names, cur.fetchone()))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lean", nargs="+", required=True, help="ad_status/key-only Parquet globs")
    parser.add_argument("--records", nargs="+", required=True, help="narrow Records Parquet files/globs")
    parser.add_argument("--onet", nargs="+", required=True, help="narrow O*NET Parquet files/globs")
    parser.add_argument("--official-codes", type=Path, required=True)
    parser.add_argument("--rules", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--records-lookup-scope", required=True)
    parser.add_argument("--onet-lookup-scope", choices=["complete", "partial"], required=True)
    parser.add_argument("--expected-onet-files", type=int)
    parser.add_argument("--expected-onet-rows", type=int)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--memory-limit", default="8GB")
    args = parser.parse_args()

    rules = json.loads(args.rules.read_text())
    if rules.get("version") != VERSION or rules.get("remote", {}).get("joined") is not False:
        raise RuntimeError("rules identity mismatch")
    codes = sorted(official_codes(args.official_codes))
    onet_footer_rows = sum(pq.ParquetFile(path).metadata.num_rows for path in args.onet)
    record_columns = set(pq.ParquetFile(args.records[0]).schema_arrow.names)
    required_record_columns = {"JOB_HASH", "RECORD_SOURCE_ROW", "COMPANY_ID", "CREATED", "COUNTRY", "STATE"}
    if not required_record_columns.issubset(record_columns):
        raise RuntimeError("Records projection lacks required linkage/company/date columns")
    if args.expected_onet_files is not None and len(args.onet) != args.expected_onet_files:
        raise RuntimeError("O*NET file-count identity mismatch")
    if args.expected_onet_rows is not None and onet_footer_rows != args.expected_onet_rows:
        raise RuntimeError("O*NET footer-row identity mismatch")
    con = duckdb.connect()
    con.execute("SET threads=%d" % args.threads)
    con.execute("SET memory_limit='%s'" % args.memory_limit.replace("'", "''"))
    con.execute("CREATE TEMP TABLE official(code VARCHAR PRIMARY KEY)")
    con.executemany("INSERT INTO official VALUES (?)", [(x,) for x in codes])
    con.execute("CREATE TEMP VIEW lean_input AS SELECT * FROM read_parquet([%s], union_by_name=true)" % sql_list(args.lean))
    base_expr = "BASE_HASH" if "BASE_HASH" in record_columns else "NULL::VARCHAR AS BASE_HASH"
    title_expr = "TITLE" if "TITLE" in record_columns else "NULL::VARCHAR AS TITLE"
    con.execute("CREATE TEMP VIEW records_input AS SELECT JOB_HASH, RECORD_SOURCE_ROW, COMPANY_ID, %s, %s, CREATED, COUNTRY, STATE FROM read_parquet([%s], union_by_name=true)" % (base_expr, title_expr, sql_list(args.records)))
    con.execute("CREATE TEMP VIEW onet_input AS SELECT JOB_HASH, ONET_OCCUPATION_CODE FROM read_parquet([%s], union_by_name=true)" % sql_list(args.onet))
    lean_schema = {row[0] for row in con.execute("DESCRIBE lean_input").fetchall()}
    if not set(KEYS).issubset(lean_schema):
        raise RuntimeError("lean input lacks canonical keys")
    denominator = one(con, "SELECT count(*) ads, count(DISTINCT (JOB_HASH,SOURCE_FILE,SOURCE_ROW,RECORD_SOURCE_ROW)) unique_ads FROM lean_input")
    if denominator["ads"] != denominator["unique_ads"]:
        raise RuntimeError("duplicate canonical semantic key")

    report = one(con, """
      WITH rc AS (
        SELECT l.JOB_HASH,l.SOURCE_FILE,l.SOURCE_ROW,l.RECORD_SOURCE_ROW,
               count(r.JOB_HASH) record_matches,
               max(CASE WHEN r.COMPANY_ID IS NULL AND r.JOB_HASH IS NOT NULL THEN 1 ELSE 0 END) null_company_id,
               max(CASE WHEN r.JOB_HASH IS NOT NULL AND (r.BASE_HASH IS NULL OR trim(cast(r.BASE_HASH AS VARCHAR))='' OR trim(cast(r.BASE_HASH AS VARCHAR)) IN ('0','-1')) THEN 1 ELSE 0 END) null_or_placeholder_base_hash,
               max(CASE WHEN r.JOB_HASH IS NOT NULL AND (r.TITLE IS NULL OR trim(r.TITLE)='') THEN 1 ELSE 0 END) null_or_blank_title
        FROM lean_input l LEFT JOIN records_input r
          ON l.JOB_HASH=r.JOB_HASH AND l.RECORD_SOURCE_ROW=r.RECORD_SOURCE_ROW
        GROUP BY 1,2,3,4
      ), oc AS (
        SELECT l.JOB_HASH,l.SOURCE_FILE,l.SOURCE_ROW,l.RECORD_SOURCE_ROW,
          count(o.JOB_HASH) onet_matches,
          CASE WHEN count(o.JOB_HASH)=0 THEN 'missing_key'
               WHEN count(o.JOB_HASH)>1 THEN 'duplicate_key'
               WHEN max(o.ONET_OCCUPATION_CODE) IS NULL OR trim(max(o.ONET_OCCUPATION_CODE))='' THEN 'blank_code'
               WHEN trim(max(o.ONET_OCCUPATION_CODE))='99-9999.00' THEN 'placeholder_99-9999.00'
               WHEN max(x.code) IS NOT NULL THEN 'official_2019_member'
               ELSE 'other_nonmember' END occupation_state
        FROM lean_input l LEFT JOIN onet_input o ON l.JOB_HASH=o.JOB_HASH
        LEFT JOIN official x ON trim(o.ONET_OCCUPATION_CODE)=x.code
        GROUP BY 1,2,3,4
      )
      SELECT count(*) canonical_semantic_ads,
        sum(CASE WHEN rc.record_matches=0 THEN 1 ELSE rc.record_matches END)::BIGINT records_raw_left_join_rows,
        sum(CASE WHEN oc.onet_matches=0 THEN 1 ELSE oc.onet_matches END)::BIGINT onet_raw_left_join_rows,
        count(*) FILTER (WHERE rc.record_matches=0) records_matches_0,
        count(*) FILTER (WHERE rc.record_matches=1) records_matches_1,
        count(*) FILTER (WHERE rc.record_matches>1) records_matches_gt1,
        sum(rc.null_company_id)::BIGINT null_company_id,
        sum(rc.null_or_placeholder_base_hash)::BIGINT null_or_placeholder_base_hash,
        sum(rc.null_or_blank_title)::BIGINT null_or_blank_title,
        count(*) FILTER (WHERE oc.occupation_state='missing_key') onet_missing_key,
        count(*) FILTER (WHERE oc.occupation_state='blank_code') onet_blank_code,
        count(*) FILTER (WHERE oc.occupation_state='placeholder_99-9999.00') onet_placeholder,
        count(*) FILTER (WHERE oc.occupation_state='other_nonmember') onet_other_nonmember,
        count(*) FILTER (WHERE oc.occupation_state='official_2019_member') onet_official_member,
        count(*) FILTER (WHERE oc.occupation_state='duplicate_key') onet_duplicate_key
      FROM rc JOIN oc USING(JOB_HASH,SOURCE_FILE,SOURCE_ROW,RECORD_SOURCE_ROW)
    """)
    if sum(report[key] for key in ("records_matches_0", "records_matches_1", "records_matches_gt1")) != denominator["ads"]:
        raise RuntimeError("Records cardinality does not conserve denominator")
    if sum(report[key] for key in ("onet_missing_key", "onet_blank_code", "onet_placeholder", "onet_other_nonmember", "onet_official_member", "onet_duplicate_key")) != denominator["ads"]:
        raise RuntimeError("occupation states do not conserve denominator")
    if "BASE_HASH" not in record_columns:
        report["null_or_placeholder_base_hash"] = None
    if "TITLE" not in record_columns:
        report["null_or_blank_title"] = None
    safe = (report["records_matches_gt1"] == 0 and report["onet_duplicate_key"] == 0
            and args.onet_lookup_scope == "complete")
    report.update({
        "status": "complete",
        "version": VERSION,
        "aggregate_row_conservation": True,
        "raw_records_left_join_conservation": report["records_raw_left_join_rows"] == denominator["ads"],
        "raw_onet_left_join_conservation": report["onet_raw_left_join_rows"] == denominator["ads"],
        "linkage_accepted": safe,
        "linkage_acceptance_rule": "Records matches >1 and O*NET duplicate keys must both be zero",
        "records_lookup_scope": args.records_lookup_scope,
        "onet_lookup_scope": args.onet_lookup_scope,
        "missingness_unit": "canonical ads with at least one matched Records row having the condition",
        "base_hash_coverage_status": "measured" if "BASE_HASH" in record_columns else "not_measured_records_projection_lacks_column",
        "title_coverage_status": "measured" if "TITLE" in record_columns else "not_measured_records_projection_lacks_column",
        "job_hash_disagreement_after_record_source_row_match": "not_measured_by_hash-partitioned_narrow_pilot",
        "remote_joined": False,
        "company_id_interpretation": rules["records"]["company_id_meaning"],
        "occupation_time_interpretation": rules["occupation"]["time_meaning"],
        "privacy": "aggregate-only; no row keys or source text emitted",
        "inputs": {
            "lean_file_count": len(args.lean), "records_file_count": len(args.records),
            "onet_file_count": len(args.onet), "official_code_count": len(codes),
            "onet_footer_rows": onet_footer_rows,
            "records_projection_columns": sorted(record_columns),
            "official_codes_sha256": sha256(args.official_codes), "rules_sha256": sha256(args.rules)
        }
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(args.output, report)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
