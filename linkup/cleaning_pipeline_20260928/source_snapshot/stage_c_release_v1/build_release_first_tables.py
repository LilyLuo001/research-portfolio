#!/usr/bin/env python3
"""Build additive anonymous shard summaries and merge the first release tables."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import pyarrow.parquet as pq

VERSION = "release_first_tables_v1"
KEYS = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
TECH_DIMS = ("ROW_KIND", "STATUS", "TECHNOLOGY_TYPE", "ROLE", "TECH_BINDING_STATUS",
             "TECHNOLOGY_AMBIGUITY", "TECH_CONTEXT", "EXPERIENCE_OBJECT_TYPE",
             "EXPERIENCE_BINDING_STATUS", "EXPERIENCE_RELATION", "EXPERIENCE_OPTIONAL",
             "EXPERIENCE_STRENGTH", "EXPERIENCE_CONTEXT")
DATE_DIMS = ("CREATED_MONTH", "CREATED_QUARTER", "ANALYSIS_PERIOD", "DENOMINATOR")


def key(row):
    return tuple(row.get(name) for name in KEYS)


def counter_rows(counter, names):
    return [{**dict(zip(names, values)), "ADS": count}
            for values, count in sorted(counter.items(), key=lambda x: tuple(str(v) for v in x[0]))]


def rows_counter(rows, names):
    return Counter({tuple(row.get(name) for name in names): int(row["ADS"]) for row in rows})


def receipt_complete(receipt):
    if receipt.get("status") == "published_verified":
        complete = receipt.get("shard_complete")
    elif receipt.get("status") == "complete" and "accounting" in receipt:
        complete = receipt
    else:
        complete = None
    if not isinstance(complete, dict) or complete.get("status") != "complete":
        raise ValueError("receipt does not contain a completed shard")
    return complete


def iter_rows(shard, name):
    paths = sorted(shard.glob("chunk_*/%s.parquet" % name))
    if not paths:
        raise FileNotFoundError("missing typed lean table: " + name)
    for path in paths:
        for batch in pq.ParquetFile(path).iter_batches(batch_size=65536):
            yield from batch.to_pylist()


def quality(ad):
    statuses = []
    if ad["DESCRIPTION_EMPTY"]: statuses.append("empty_description")
    if ad["PARSE_ERROR"]: statuses.append("parse_error")
    if ad["INPUT_EVIDENCE_TRUNCATED"]: statuses.append("input_evidence_truncated")
    if ad["ENRICHMENT_INCOMPLETE"]: statuses.append("enrichment_incomplete")
    return statuses, not statuses


def period(value):
    if value is None:
        return "unknown", "unknown", "date_unknown"
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    month = "%04d-%02d" % (value.year, value.month)
    quarter = "%04dQ%d" % (value.year, (value.month - 1) // 3 + 1)
    if value.year < 2026 or (value.year == 2026 and value.month <= 6):
        analysis = "complete_queues_through_2026Q2"
    elif value.year == 2026 and value.month <= 9:
        analysis = "2026Q3_partial"
    else:
        analysis = "outside_primary_window"
    return month, quarter, analysis


def sentinel(status, technology):
    if technology:
        return (status, "unknown", "unknown", None, "unknown")
    return (status, "unknown", "unknown", None, "unknown", "unknown")


def shard_summary(shard, receipt_path):
    receipt = json.loads(receipt_path.read_text())
    complete = receipt_complete(receipt); accounting = complete["accounting"]
    dispositions = Counter(accounting["disposition_counts"])
    if sum(dispositions.values()) != accounting["raw_rows"] or not accounting.get("row_conservation"):
        raise RuntimeError("receipt disposition conservation failed")

    ads = {}; funnel = Counter(); dates = Counter(); tech_cross = Counter()
    for ad in iter_rows(shard, "ad_status"):
        ad_key = key(ad)
        if ad_key in ads: raise RuntimeError("duplicate ad key within shard")
        ads[ad_key] = ad
    if len(ads) != accounting["canonical_usa_rows"]:
        raise RuntimeError("canonical receipt/ad_status conservation failed")

    exp = defaultdict(set); tech = defaultdict(set); audit = defaultdict(set)
    exp_rows = tech_rows = audit_rows = 0
    for row in iter_rows(shard, "experience"):
        exp_rows += 1
        if key(row) not in ads: raise RuntimeError("experience evidence key absent from ad_status")
        if row["APPLICANT_CONTEXT_CANDIDATE"]:
            exp[key(row)].add((row["OBJECT_TYPE"] or "unknown", row["BINDING_STATUS"] or "unknown",
                               row["RELATION"] or "unknown", row["OPTIONAL"],
                               row["REQUIREMENT_STRENGTH"] or "unknown", row["CONTEXT"] or "unknown"))
    for row in iter_rows(shard, "technology"):
        tech_rows += 1
        if key(row) not in ads: raise RuntimeError("technology evidence key absent from ad_status")
        if row["APPLICANT_CONTEXT_CANDIDATE"]:
            tech[key(row)].add((row["TECHNOLOGY_TYPE"] or "unknown", row["ROLE"] or "unknown",
                                row["BINDING_STATUS"] or "unknown", row["TECHNOLOGY_AMBIGUITY"],
                                row["CONTEXT"] or "unknown"))
    for row in iter_rows(shard, "v6_audit"):
        audit_rows += 1
        if key(row) not in ads: raise RuntimeError("audit evidence key absent from ad_status")
        if row["MODULE"] == "education": audit[key(row)].add("education_candidate")
        if row["MODULE"] == "experience" and row["NO_EXPERIENCE_EXPLICIT"]:
            audit[key(row)].add("no_experience_phrase_candidate")

    for ad_key, ad in ads.items():
        statuses, usable = quality(ad)
        funnel["canonical_ad_status"] += 1
        funnel["usable_nonempty_complete_parse"] += int(usable)
        for status in statuses: funnel[status] += 1
        funnel["audit_only_education_candidate"] += int("education_candidate" in audit[ad_key])
        funnel["audit_only_no_experience_phrase_candidate"] += int(
            "no_experience_phrase_candidate" in audit[ad_key])

        month, quarter, analysis = period(ad["CREATED"])
        dates[(month, quarter, analysis, "canonical_usa")] += 1
        if usable: dates[(month, quarter, analysis, "usable_nonempty_complete_parse")] += 1

        for status in ("all_canonical",) + tuple(statuses) + (("usable",) if usable else ()):
            tech_cross[("denominator_status", status) + (None,) * (len(TECH_DIMS) - 2)] += 1
        if not usable:
            failure = "insufficient_" + "+".join(statuses)
            tech_values = {sentinel(failure, True)}; exp_values = {sentinel(failure, False)}
        else:
            tech_values = tech[ad_key]
            if not tech_values:
                status = ("no_applicant_context_candidate" if ad["TECHNOLOGY_EVIDENCE_COUNT"] else
                          "no_detection")
                tech_values = {sentinel(status, True)}
            exp_values = exp[ad_key]
            if not exp_values:
                status = ("no_applicant_context_candidate" if ad["EXPERIENCE_EVIDENCE_COUNT"] else
                          "no_detection")
                exp_values = {sentinel(status, False)}
        for t in tech_values:
            for e in exp_values:
                tech_cross[("evidence_cross", "candidate_evidence") + t + e] += 1

    funnel.update({
        "raw_input_rows": accounting["raw_rows"],
        "record_matched_rows": accounting["raw_rows"] - dispositions["record_unmatched"],
        "record_unmatched_rows": dispositions["record_unmatched"],
        "matched_non_usa_rows": dispositions["matched_non_usa"],
        "matched_country_unknown_rows": dispositions["matched_country_unknown"],
        "matched_usa_rows": dispositions["matched_usa_canonical"] + dispositions["matched_usa_duplicate_quarantine"],
        "matched_usa_unique_canonical_rows": dispositions["matched_usa_canonical"],
        "matched_usa_duplicate_quarantine_rows": dispositions["matched_usa_duplicate_quarantine"],
    })
    summary_id = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    return {
        "version": VERSION, "leaf_summary_ids": [summary_id], "shards": 1,
        "funnel": dict(funnel), "technology_experience": counter_rows(tech_cross, TECH_DIMS),
        "created_queue": counter_rows(dates, DATE_DIMS),
        "evidence_rows": {"experience": exp_rows, "technology": tech_rows, "v6_audit": audit_rows},
        "notes": {"ad_identity": "local composite key used only for within-shard deduplication; not released",
                  "global_identity": "global uniqueness derives from the verified disposition contract, not this local test",
                  "education_no_experience": "audit-only candidate counts",
                  "created": "delivery-snapshot first-observed queue; not historical text or causal time"},
    }


def merge_summaries(paths):
    funnel = Counter(); tech = Counter(); dates = Counter(); evidence = Counter(); leaf_ids = set(); shards = 0
    for path in paths:
        item = json.loads(path.read_text())
        if item.get("version") != VERSION: raise ValueError("summary version mismatch")
        ids = set(item["leaf_summary_ids"])
        if len(ids) != len(item["leaf_summary_ids"]) or leaf_ids & ids:
            raise RuntimeError("duplicate shard summary in merge")
        leaf_ids.update(ids); shards += int(item["shards"]); funnel.update(item["funnel"])
        tech.update(rows_counter(item["technology_experience"], TECH_DIMS))
        dates.update(rows_counter(item["created_queue"], DATE_DIMS)); evidence.update(item["evidence_rows"])
    if shards != len(leaf_ids): raise RuntimeError("leaf/shard summary conservation failed")
    if funnel["matched_usa_unique_canonical_rows"] != funnel["canonical_ad_status"]:
        raise RuntimeError("merged canonical/ad_status conservation failed")
    return {"version": VERSION, "leaf_summary_ids": sorted(leaf_ids), "shards": shards,
            "funnel": dict(funnel), "technology_experience": counter_rows(tech, TECH_DIMS),
            "created_queue": counter_rows(dates, DATE_DIMS), "evidence_rows": dict(evidence)}


def write_csv(path, rows, fields):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader(); writer.writerows(rows)


def write_merged(output, merged):
    output.mkdir(parents=True, exist_ok=False)
    funnel_rows = [{"METRIC": key, "ADS": value,
                    "INTERPRETATION": "audit_only" if key.startswith("audit_only_") else "release_funnel"}
                   for key, value in sorted(merged["funnel"].items())]
    write_csv(output / "input_match_canonical_usable_funnel.csv", funnel_rows,
              ("METRIC", "ADS", "INTERPRETATION"))
    write_csv(output / "technology_experience_candidate_evidence.csv", merged["technology_experience"],
              TECH_DIMS + ("ADS",))
    created = [{**row, "TIME_INTERPRETATION": "delivery_snapshot_first_observed_queue_not_historical_text_or_causal"}
               for row in merged["created_queue"]]
    write_csv(output / "created_first_observed_queue_distribution.csv", created,
              DATE_DIMS + ("ADS", "TIME_INTERPRETATION"))
    report = {"status": "complete", "version": VERSION, "shards": merged["shards"],
              "anonymous_leaf_summaries": len(merged["leaf_summary_ids"]),
              "funnel": merged["funnel"], "evidence_rows": merged["evidence_rows"],
              "conservation": {
                  "raw_equals_dispositions": True,
                  "canonical_equals_ad_status": (merged["funnel"]["matched_usa_unique_canonical_rows"] ==
                                                  merged["funnel"]["canonical_ad_status"]),
                  "ad_level_evidence_deduplication": True,
              },
              "limits": ["candidate evidence; cells may be nonexclusive for multi-valued ads",
                         "education and no-experience are audit-only",
                         "CREATED is a delivery-snapshot first-observed queue, not historical text or causality",
                         "no occupation or Revelio worker-flow inference"]}
    (output / "CONSERVATION_REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    (output / "MERGED_SUMMARY.json").write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="mode", required=True)
    shard = sub.add_parser("shard"); shard.add_argument("--shard-dir", type=Path, required=True)
    shard.add_argument("--receipt", type=Path, required=True); shard.add_argument("--output", type=Path, required=True)
    merge = sub.add_parser("merge"); merge.add_argument("--summaries", type=Path, nargs="+", required=True)
    merge.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.mode == "shard":
        value = shard_summary(args.shard_dir, args.receipt)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp = Path(str(args.output) + ".tmp"); temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        os.replace(temp, args.output)
    else:
        write_merged(args.output_dir, merge_summaries(args.summaries))


if __name__ == "__main__":
    main()
