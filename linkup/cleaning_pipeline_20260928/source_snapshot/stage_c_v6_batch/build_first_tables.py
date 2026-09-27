#!/usr/bin/env python3
"""Build bounded exploratory ad-level and aggregate tables from compact V6 output."""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq


def strength_flags(items, module):
    relevant = [x for x in items if x.get("MODULE") == module and x.get("IS_APPLICANT_QUALIFICATION_CANDIDATE")]
    strengths = {x.get("REQUIREMENT_STRENGTH") for x in relevant}
    return {
        module + "_required": "required" in strengths,
        module + "_preferred": "preferred" in strengths,
        module + "_expected": "expected_unspecified_mandatoriness" in strengths,
        module + "_unspecified": "unspecified" in strengths,
        module + "_strength_conflict": len(strengths) > 1 or any(bool(x.get("CONTEXT_CONFLICT")) for x in relevant),
    }


def module_status(summary, module, parse_error, incomplete, truncated):
    if parse_error or incomplete or truncated:
        return "insufficient_parse_or_truncated"
    value = summary.get(module) or {}
    if module == "experience" and value.get("no_experience_explicit"):
        return "detected_no_experience_phrase_candidate"
    if value.get("applicant_qualification_candidate_count", 0) > 0:
        return "detected_candidate"
    return "candidate_no_detection"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-dir", required=True); ap.add_argument("--compact-dir", required=True)
    ap.add_argument("--output-dir", required=True)
    args = ap.parse_args()
    sample_dir, compact_dir, output = Path(args.sample_dir), Path(args.compact_dir), Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=False)
    metadata = {x["JOB_HASH"]: x for x in pq.read_table(sample_dir / "sample_metadata.parquet").to_pylist()}
    ads, sources, evidence = [], [], []
    for chunk in sorted(compact_dir.glob("chunk_*")):
        ads.extend(pq.read_table(chunk / "ad_status.parquet").to_pylist())
        sources.extend(pq.read_table(chunk / "source_index.parquet").to_pylist())
        for row in pq.read_table(chunk / "evidence.parquet").to_pylist():
            extras = json.loads(row["EXTRAS_JSON"])
            row["CONTEXT_CONFLICT"] = bool(extras.get("context_conflict"))
            evidence.append(row)
    source_by_key = {x["JOB_HASH"]: x for x in sources}
    evidence_by_key = defaultdict(list)
    for row in evidence:
        evidence_by_key[row["JOB_HASH"]].append(row)
    ad_rows = []
    for ad in ads:
        key = ad["JOB_HASH"]; meta = metadata[key]; source = source_by_key[key]
        summary = json.loads(ad["SUMMARY_JSON"]); extras = json.loads(ad["TOP_EXTRAS_JSON"])
        ev = evidence_by_key.get(key, [])
        parse_error = bool(source["HAS_PARSE_ERROR"])
        truncated = bool(source["EVIDENCE_TRUNCATED"])
        incomplete = bool(extras.get("v6_candidate_incomplete"))
        created_status = meta["CREATED_QUEUE_STATUS"]
        if created_status == "2026Q3_partial":
            analysis_period = "2026Q3_partial"
        elif created_status.endswith("_complete_queue"):
            analysis_period = "complete_queues_through_2026Q2"
        else:
            analysis_period = "date_unknown_or_outside_primary"
        software = summary.get("software") or {}; ai = summary.get("ai") or {}
        exp = summary.get("experience") or {}; edu = summary.get("education") or {}
        row = {
            "JOB_HASH": key, "SOURCE_FILE": meta["SOURCE_FILE"], "SOURCE_ROW": meta["SOURCE_ROW"],
            "SOURCE_ROW_GROUP": meta["SOURCE_ROW_GROUP"], "ROW_IN_GROUP": meta["ROW_IN_GROUP"],
            "RECORD_SOURCE_ROW": meta["RECORD_SOURCE_ROW"], "STATE": meta["STATE"],
            "CREATED": meta["CREATED"], "LAST_UPDATED": meta["LAST_UPDATED"],
            "LAST_CHECKED": meta["LAST_CHECKED"], "DELETE_DATE": meta["DELETE_DATE"],
            "CREATED_QUEUE_STATUS": created_status, "ANALYSIS_PERIOD": analysis_period,
            "COMPANY_ID_MATCH": meta["COMPANY_ID_MATCH"],
            "DESCRIPTION_UTF8_BYTES": meta["DESCRIPTION_UTF8_BYTES"],
            "PARSE_ERROR": parse_error, "EVIDENCE_TRUNCATED": truncated,
            "V6_CANDIDATE_INCOMPLETE": incomplete,
            "EDUCATION_STATUS": module_status(summary, "education", parse_error, incomplete, truncated),
            "EXPERIENCE_STATUS": module_status(summary, "experience", parse_error, incomplete, truncated),
            "EDUCATION_CANDIDATE_COUNT": edu.get("applicant_qualification_candidate_count", 0),
            "EXPERIENCE_CANDIDATE_COUNT": exp.get("applicant_qualification_candidate_count", 0),
            "NO_EXPERIENCE_EXPLICIT": bool(exp.get("no_experience_explicit")),
            "EDUCATION_RELATION_UNRESOLVED_COUNT": edu.get("qualification_relation_unresolved_count", 0),
            "EXPERIENCE_RELATION_UNRESOLVED_COUNT": exp.get("qualification_relation_unresolved_count", 0),
            "EDUCATION_ALTERNATIVE_PATH_COUNT": edu.get("alternative_path_candidate_count", 0),
            "EXPERIENCE_ALTERNATIVE_PATH_COUNT": exp.get("alternative_path_candidate_count", 0),
            "SOFTWARE_GENERIC_MENTION_COUNT": software.get("candidate_count", 0),
            "SOFTWARE_APPLICANT_CONTEXT_COUNT": software.get("applicant_qualification_candidate_count", 0),
            "AI_GENERIC_MENTION_COUNT": ai.get("candidate_count", 0),
            "AI_APPLICANT_CONTEXT_COUNT": ai.get("applicant_qualification_candidate_count", 0),
            "OCCUPATION_STATUS": "unknown_not_joined",
            "AI_ROLE_STATUS": "unknown_unvalidated",
            "TEXT_TIME_EVIDENCE": "delivery_snapshot_grouped_by_created_queue_not_historical_text",
        }
        row.update(strength_flags(ev, "education")); row.update(strength_flags(ev, "experience"))
        ad_rows.append(row)
    if len(ad_rows) != len(metadata) or len({x["JOB_HASH"] for x in ad_rows}) != len(ad_rows):
        raise RuntimeError("ad-level conservation/uniqueness failure")
    pq.write_table(pa.Table.from_pylist(ad_rows), output / "candidate_ad_level.parquet",
                   compression="zstd", row_group_size=4096)

    coverage = Counter()
    for row in ad_rows:
        coverage[(row["ANALYSIS_PERIOD"], row["CREATED_QUEUE_STATUS"], row["PARSE_ERROR"],
                  row["EVIDENCE_TRUNCATED"], row["V6_CANDIDATE_INCOMPLETE"],
                  row["COMPANY_ID_MATCH"], row["DESCRIPTION_UTF8_BYTES"] in (None, 0))] += 1
    coverage_rows = [{"ANALYSIS_PERIOD": k[0], "CREATED_QUEUE_STATUS": k[1], "PARSE_ERROR": k[2],
                      "EVIDENCE_TRUNCATED": k[3], "V6_CANDIDATE_INCOMPLETE": k[4],
                      "COMPANY_ID_MATCH": k[5], "EMPTY_DESCRIPTION": k[6], "ADS": n}
                     for k, n in sorted(coverage.items(), key=lambda x: str(x[0]))]

    joint = Counter((x["ANALYSIS_PERIOD"], x["CREATED_QUEUE_STATUS"],
                     x["EDUCATION_STATUS"], x["EXPERIENCE_STATUS"]) for x in ad_rows)
    joint_rows = [{"ANALYSIS_PERIOD": k[0], "CREATED_QUEUE_STATUS": k[1],
                   "EDUCATION_STATUS": k[2], "EXPERIENCE_STATUS": k[3], "ADS": n}
                  for k, n in sorted(joint.items())]

    strength = Counter()
    for row in ad_rows:
        for module in ("education", "experience"):
            for name in ("required", "preferred", "expected", "unspecified", "strength_conflict"):
                if row[module + "_" + name]:
                    strength[(row["ANALYSIS_PERIOD"], row["CREATED_QUEUE_STATUS"], module, name)] += 1
    strength_rows = [{"ANALYSIS_PERIOD": k[0], "CREATED_QUEUE_STATUS": k[1],
                      "MODULE": k[2], "STRENGTH_OR_FLAG": k[3], "ADS": n}
                     for k, n in sorted(strength.items())]

    technology = Counter()
    for row in ad_rows:
        if row["PARSE_ERROR"] or row["EVIDENCE_TRUNCATED"] or row["V6_CANDIDATE_INCOMPLETE"]:
            tech_status = "insufficient_parse_or_truncated"
        else:
            bits = []
            if row["SOFTWARE_APPLICANT_CONTEXT_COUNT"]: bits.append("software_applicant_context")
            elif row["SOFTWARE_GENERIC_MENTION_COUNT"]: bits.append("software_generic_only")
            if row["AI_APPLICANT_CONTEXT_COUNT"]: bits.append("ai_applicant_context")
            elif row["AI_GENERIC_MENTION_COUNT"]: bits.append("ai_generic_only")
            tech_status = "+".join(bits) if bits else "no_technology_candidate_detection"
        technology[(row["ANALYSIS_PERIOD"], row["CREATED_QUEUE_STATUS"], tech_status,
                    row["EXPERIENCE_STATUS"])] += 1
    technology_rows = [{"ANALYSIS_PERIOD": k[0], "CREATED_QUEUE_STATUS": k[1],
                        "TECHNOLOGY_CANDIDATE_STATUS": k[2], "EXPERIENCE_STATUS": k[3], "ADS": n,
                        "AI_ROLE_STATUS": "unknown_unvalidated"}
                       for k, n in sorted(technology.items())]
    tables = {"coverage_by_created_queue": coverage_rows, "education_experience_joint": joint_rows,
              "qualification_strength_multivalued": strength_rows,
              "technology_experience_cross": technology_rows}
    for name, rows in tables.items():
        pq.write_table(pa.Table.from_pylist(rows), output / (name + ".parquet"), compression="zstd")
        if rows:
            table = pa.Table.from_pylist(rows)
            import pyarrow.csv as csv
            csv.write_csv(table, output / (name + ".csv"))
    report = {"status": "complete", "ad_rows": len(ad_rows), "evidence_rows": len(evidence),
              "parse_errors": sum(x["PARSE_ERROR"] for x in ad_rows),
              "truncated_or_incomplete": sum(x["EVIDENCE_TRUNCATED"] or x["V6_CANDIDATE_INCOMPLETE"] for x in ad_rows),
              "primary_complete_queue_ads": sum(x["ANALYSIS_PERIOD"] == "complete_queues_through_2026Q2" for x in ad_rows),
              "partial_2026q3_ads": sum(x["ANALYSIS_PERIOD"] == "2026Q3_partial" for x in ad_rows),
              "interpretation": "Exploratory delivery-snapshot candidate tables; not historical text, population estimates, validated accuracy, vacancies, or hires.",
              "measurement_audit_limits": "NEW48 model diagnostic found education candidate detection in 17/30 model-positive rows and experience detection in 32/35; education/joint counts are measurement-audit candidate detections, not true prevalence. Parser no-experience phrases are unvalidated candidates, not true absence rates.",
              "occupation_status": "unknown_not_joined", "ai_role_status": "unknown_unvalidated",
              "outputs": sorted(p.name for p in output.iterdir())}
    (output / "TABLE_REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
