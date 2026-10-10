#!/usr/bin/env python3
"""D63 descriptive comparison over accepted first-five narrow outputs.

This program aggregates frozen rule-observed fields. It does not extract text,
change a rule, infer a missing concept, or emit row identifiers/evidence text.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import os
import platform
import sys

import pyarrow.parquet as pq


VERSION = "d63-first5-descriptive-comparison-v1"
KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
AI = {"genai", "predictive_ai", "ai_unspecified"}
OBJECTS = {"general_work", "occupation_task", "industry_domain", "tool"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)


def write_csv(path, rows, fields):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def rows(path, columns, batch_size=65536):
    pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=batch_size, columns=columns):
        d = batch.to_pydict()
        names = list(d)
        for i in range(batch.num_rows):
            yield {n: d[n][i] for n in names}


def key(row):
    return tuple(row[x] for x in KEY)


def fraction(a, b):
    return a / b if b else None


def tech_group(feat):
    software = "software" in feat["tech"]
    ai = bool(AI & feat["tech"])
    if software and ai:
        return "software_and_ai"
    if software:
        return "software_only"
    if ai:
        return "ai_only"
    return "neither_observed"


def metric_names():
    return [
        "broad_general_work", "broad_occupation_task", "broad_industry_domain",
        "broad_related", "broad_tool", "broad_general_and_related",
        "narrow_general_work", "narrow_occupation_task", "narrow_industry_domain",
        "narrow_related", "narrow_tool", "narrow_general_and_related",
        "numeric_duration_observed", "conditional_or_alternative_experience_observed",
        "experience_scope_unknown", "unresolved_experience_observed", "independent_judgment_wording",
        "client_responsibility_wording", "people_supervision_wording",
        "d57_current_duty_mentoring_candidate", "supervision_or_current_duty_mentoring",
        "any_frozen_responsibility_wording",
    ]


def metric(feat, name):
    broad, narrow = feat["broad"], feat["narrow"]
    vals = {
        "broad_general_work": "general_work" in broad,
        "broad_occupation_task": "occupation_task" in broad,
        "broad_industry_domain": "industry_domain" in broad,
        "broad_related": bool({"occupation_task", "industry_domain"} & broad),
        "broad_tool": "tool" in broad,
        "broad_general_and_related": "general_work" in broad and bool({"occupation_task", "industry_domain"} & broad),
        "narrow_general_work": "general_work" in narrow,
        "narrow_occupation_task": "occupation_task" in narrow,
        "narrow_industry_domain": "industry_domain" in narrow,
        "narrow_related": bool({"occupation_task", "industry_domain"} & narrow),
        "narrow_tool": "tool" in narrow,
        "narrow_general_and_related": "general_work" in narrow and bool({"occupation_task", "industry_domain"} & narrow),
        "numeric_duration_observed": feat["numeric"],
        "conditional_or_alternative_experience_observed": feat["conditional"],
        "experience_scope_unknown": feat["experience_scope_unknown"],
        "unresolved_experience_observed": feat["unresolved"],
        "independent_judgment_wording": feat["independent"],
        "client_responsibility_wording": feat["client"],
        "people_supervision_wording": feat["supervision"],
        "d57_current_duty_mentoring_candidate": feat["mentoring"],
        "supervision_or_current_duty_mentoring": feat["supervision"] or feat["mentoring"],
        "any_frozen_responsibility_wording": feat["independent"] or feat["client"] or feat["supervision"] or feat["mentoring"],
    }
    return vals[name]


def eligible_arm(group, arm):
    if arm == "software_only":
        return group == "software_only"
    if arm == "any_ai":
        return group in ("ai_only", "software_and_ai")
    if arm == "ai_only":
        return group == "ai_only"
    raise ValueError(arm)


def standardized(features, metadata, left, right, threshold, cell_kind, metrics):
    # Private cell identifiers are used only in memory and are never emitted.
    by_cell = collections.defaultdict(lambda: {left: [], right: []})
    valid_arm_totals = collections.Counter()
    for k, feat in features.items():
        md = metadata[k]
        if md["official_occupation_status"] != "official_code" or not md["ONET_OCCUPATION_CODE"]:
            continue
        arm = left if eligible_arm(feat["tech_group"], left) else right if eligible_arm(feat["tech_group"], right) else None
        if arm is None:
            continue
        valid_arm_totals[arm] += 1
        if cell_kind == "occupation":
            cell = md["ONET_OCCUPATION_CODE"]
        else:
            if md["company_status"] != "observed_company_scrape_entity" or not md["COMPANY_ID"]:
                continue
            cell = (md["COMPANY_ID"], md["ONET_OCCUPATION_CODE"])
        by_cell[cell][arm].append(k)
    kept = {c: v for c, v in by_cell.items() if len(v[left]) >= threshold and len(v[right]) >= threshold}
    total_weight = sum(min(len(v[left]), len(v[right])) for v in kept.values())
    retained = {a: sum(len(v[a]) for v in kept.values()) for a in (left, right)}
    out = []
    for m in metrics:
        row = {
            "comparison": left + "_vs_" + right,
            "cell_kind": cell_kind,
            "threshold_each_arm": threshold,
            "metric": m,
            "eligible_cell_count": len(kept),
            "left_arm": left, "right_arm": right,
            "left_valid_occupation_n": valid_arm_totals[left],
            "right_valid_occupation_n": valid_arm_totals[right],
            "left_retained_n": retained[left], "right_retained_n": retained[right],
            "left_retained_share": fraction(retained[left], valid_arm_totals[left]),
            "right_retained_share": fraction(retained[right], valid_arm_totals[right]),
            "weight_basis": "min(left_cell_n,right_cell_n)_normalized",
            "status": "estimated" if total_weight else "unavailable_no_supported_cells",
        }
        for side, a in (("left", left), ("right", right)):
            full_keys = [k for k, f in features.items()
                         if metadata[k]["official_occupation_status"] == "official_code"
                         and metadata[k]["ONET_OCCUPATION_CODE"] and eligible_arm(f["tech_group"], a)]
            row[side + "_raw_valid_occupation_rate"] = fraction(sum(metric(features[k], m) for k in full_keys), len(full_keys))
            retained_keys = [k for v in kept.values() for k in v[a]]
            row[side + "_raw_common_support_rate"] = fraction(sum(metric(features[k], m) for k in retained_keys), len(retained_keys))
            if total_weight:
                row[side + "_standardized_rate"] = sum(
                    (min(len(v[left]), len(v[right])) / total_weight)
                    * fraction(sum(metric(features[k], m) for k in v[a]), len(v[a]))
                    for v in kept.values())
            else:
                row[side + "_standardized_rate"] = None
        l, r = row.get("left_standardized_rate"), row.get("right_standardized_rate")
        row["difference_right_minus_left_percentage_points"] = (r - l) * 100 if l is not None and r is not None else None
        out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--metadata-qa", required=True)
    ap.add_argument("--decision", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    os.makedirs(args.output, exist_ok=True)
    manifest = json.load(open(args.manifest, encoding="utf-8"))
    decision = json.load(open(args.decision, encoding="utf-8"))
    mdqa = json.load(open(args.metadata_qa, encoding="utf-8"))
    if mdqa.get("status") != "pass" or mdqa.get("output_rows") != 424226:
        raise RuntimeError("metadata QA gate failed")
    if sha256(args.metadata) != mdqa.get("output_sha256"):
        raise RuntimeError("metadata output SHA mismatch")
    if len(manifest.get("shards", [])) != 5:
        raise RuntimeError("exactly five accepted shards required")

    features = {}
    receipt_bindings = []
    posting_columns = list(KEY) + ["processing_status", "flags_json", "d57_current_duty_mentoring_candidate"]
    for shard in manifest["shards"]:
        receipt = json.load(open(shard["production_receipt"], encoding="utf-8"))
        qa = json.load(open(shard["qa_output"], encoding="utf-8"))
        if receipt.get("status") != "complete" or qa.get("status") != "pass":
            raise RuntimeError("accepted production/QA gate failed for " + shard["shard_id"])
        if receipt.get("identity", {}).get("runner_sha256") != shard["expected_runner_sha256"]:
            raise RuntimeError("runner identity mismatch")
        ph = sha256(shard["posting"]); eh = sha256(shard["evidence"])
        if ph != receipt["outputs"]["posting_sha256"] or eh != receipt["outputs"]["evidence_sha256"]:
            raise RuntimeError("actual narrow output hash mismatch")
        receipt_bindings.append({"shard_id": shard["shard_id"], "production_receipt_sha256": sha256(shard["production_receipt"]),
                                 "qa_sha256": sha256(shard["qa_output"]), "posting_sha256": ph, "evidence_sha256": eh})
        for row in rows(shard["posting"], posting_columns):
            k = key(row)
            if k in features:
                raise RuntimeError("duplicate canonical posting key")
            flags = json.loads(row["flags_json"] or "{}")
            features[k] = {
                "processing": row["processing_status"], "flags": flags,
                "mentoring": row["d57_current_duty_mentoring_candidate"] is True,
                "tech": set(), "broad": set(), "narrow": set(), "numeric": False,
                "conditional": False, "experience_scope_unknown": False, "unresolved": False,
                "noexp_any": False, "noexp_unconditional": False, "noexp_conditional": False,
                "noexp_scope_unknown": False,
                "specific_experience_waiver": False,
                "graduate": bool(flags.get("graduate_language")),
                "junior": bool(flags.get("entry_junior_text")),
                "independent": bool(flags.get("task_independent_responsibility")),
                "client": bool(flags.get("task_client_ownership")),
                "supervision": bool(flags.get("task_people_supervision")),
            }
    processing_counts = collections.Counter(f["processing"] for f in features.values())
    if len(features) != 424226 or processing_counts != {"processed": 424225, "invalid_text": 1}:
        raise RuntimeError("posting denominator or accepted processing partition mismatch")

    evidence_columns = list(KEY) + ["kind", "rule", "objects_json", "scope", "duration_kind",
                                    "outcome_status", "technology", "negated"]
    evidence_rows = 0
    for shard in manifest["shards"]:
        for row in rows(shard["evidence"], evidence_columns):
            evidence_rows += 1
            k = key(row)
            if k not in features:
                raise RuntimeError("orphan evidence key")
            f = features[k]
            if row["kind"] == "technology" and row["negated"] is not True and row["technology"]:
                f["tech"].add(row["technology"])
            elif row["kind"] == "experience":
                objs = [x for x in json.loads(row["objects_json"] or "[]") if x in OBJECTS]
                f["broad"].update(objs)
                if len(objs) == 1 and row["outcome_status"] == "explicit_rule_candidate" and row["scope"] == "unconditional_explicit_clause":
                    f["narrow"].add(objs[0])
                if row["duration_kind"]:
                    f["numeric"] = True
                if row["scope"] in ("education_alternative", "other_conditional", "document_multiline_alternative_unresolved"):
                    f["conditional"] = True
                elif row["scope"] != "unconditional_explicit_clause":
                    f["experience_scope_unknown"] = True
                if row["outcome_status"] != "explicit_rule_candidate" or len(objs) != 1:
                    f["unresolved"] = True
            elif row["kind"] == "entry" and row["rule"] == "explicit_no_experience":
                waiver_objects = json.loads(row["objects_json"] or "[]")
                if waiver_objects != ["general_work"]:
                    f["specific_experience_waiver"] = True
                    continue
                f["noexp_any"] = True
                if row["scope"] == "unconditional_explicit_clause":
                    f["noexp_unconditional"] = True
                elif row["scope"] in ("education_alternative", "other_conditional", "document_multiline_alternative_unresolved"):
                    f["noexp_conditional"] = True
                else:
                    f["noexp_scope_unknown"] = True
    analysis_features = {k: f for k, f in features.items() if f["processing"] == "processed"}
    if any(f["noexp_any"] != bool(f["flags"].get("explicit_no_experience")) for f in analysis_features.values()):
        raise RuntimeError("general no-experience evidence does not reconcile to frozen explicit_no_experience flag")
    for f in analysis_features.values():
        f["tech_group"] = tech_group(f)

    metadata = {}
    mdcols = list(KEY) + ["COMPANY_ID", "company_status", "records_join_status", "onet_join_status",
                          "ONET_OCCUPATION_CODE", "official_occupation_status", "geography_status"]
    for row in rows(args.metadata, mdcols):
        k = key(row)
        if k in metadata:
            raise RuntimeError("duplicate metadata key")
        metadata[k] = row
    if len(metadata) != 424226 or set(metadata) != set(features):
        raise RuntimeError("metadata left-join denominator/key mismatch")

    groups = ("software_only", "ai_only", "software_and_ai", "neither_observed")
    partition = collections.Counter(f["tech_group"] for f in analysis_features.values())
    if sum(partition.values()) != len(analysis_features) or set(partition) - set(groups):
        raise RuntimeError("technology partition failure")
    tech_rows = []
    metrics = metric_names()
    for g in groups:
        selected = [f for f in analysis_features.values() if f["tech_group"] == g]
        tech_rows.append({"technology_group": g, "posting_count": len(selected), "denominator": len(analysis_features),
                          "fraction": fraction(len(selected), len(analysis_features)),
                          "meaning": "frozen_nonnegated_lexical_evidence; neither_observed_is_not_absence"})
    raw_rows = []
    for g in groups + ("any_ai", "all_first5"):
        selected = [f for f in analysis_features.values() if (g == "all_first5" or (g == "any_ai" and f["tech_group"] in ("ai_only", "software_and_ai")) or f["tech_group"] == g)]
        for m in metrics:
            n = sum(metric(f, m) for f in selected)
            raw_rows.append({"technology_group": g, "metric": m, "numerator": n, "denominator": len(selected),
                             "fraction": fraction(n, len(selected)), "status": "observed_rule_wording"})

    std = []
    std += standardized(analysis_features, metadata, "software_only", "any_ai", 20, "occupation", metrics)
    std += standardized(analysis_features, metadata, "software_only", "ai_only", 20, "occupation", metrics)
    company = standardized(analysis_features, metadata, "software_only", "any_ai", 5, "company_occupation", metrics)

    entry_markers = {
        "explicit_eligibility_wording_union": lambda f: f["noexp_any"] or f["graduate"],
        "explicit_noexperience_any_scope": lambda f: f["noexp_any"],
        "explicit_noexperience_unconditional": lambda f: f["noexp_unconditional"],
        "explicit_noexperience_conditional_or_alternative": lambda f: f["noexp_conditional"],
        "explicit_noexperience_scope_unknown": lambda f: f["noexp_scope_unknown"],
        "specific_experience_waiver_not_general_eligibility": lambda f: f["specific_experience_waiver"],
        "graduate_scope_not_recorded": lambda f: f["graduate"],
        "combined_junior_wording_title_or_body_unresolved": lambda f: f["junior"],
    }
    responsibility = {
        "independent_judgment_wording": lambda f: f["independent"],
        "client_responsibility_wording": lambda f: f["client"],
        "people_supervision_wording": lambda f: f["supervision"],
        "d57_current_duty_mentoring_candidate": lambda f: f["mentoring"],
        "supervision_or_current_duty_mentoring": lambda f: f["supervision"] or f["mentoring"],
        "any_frozen_responsibility_wording": lambda f: f["independent"] or f["client"] or f["supervision"] or f["mentoring"],
    }
    entry_rows = []
    allf = list(analysis_features.values())
    for marker, mpred in entry_markers.items():
        marked = [f for f in allf if mpred(f)]
        for outcome, opred in responsibility.items():
            a = sum(mpred(f) and opred(f) for f in allf)
            b = sum(mpred(f) and not opred(f) for f in allf)
            c = sum(not mpred(f) and opred(f) for f in allf)
            d = len(allf) - a - b - c
            entry_rows.append({"eligibility_marker": marker, "responsibility_marker": outcome,
                               "marker_population_n": len(marked), "cooccurrence_n": a,
                               "cooccurrence_rate_within_marker": fraction(a, len(marked)),
                               "marker_yes_outcome_yes": a, "marker_yes_outcome_no_observed": b,
                               "marker_no_observed_outcome_yes": c, "marker_no_observed_outcome_no_observed": d,
                               "full_denominator": len(allf),
                               "claim_boundary": "ad-level frozen wording cooccurrence; no-observed is unknown, not semantic absence"})

    coverage = [
        {"metric": "canonical_postings", "count": len(features), "denominator": 424226, "status": "complete"},
        {"metric": "processed_analysis_postings", "count": len(analysis_features), "denominator": len(features), "status": "analysis_denominator"},
        {"metric": "invalid_text", "count": processing_counts["invalid_text"], "denominator": len(features), "status": "retained_coverage_not_classified"},
        {"metric": "metadata_rows_exact_key_match", "count": len(metadata), "denominator": len(features), "status": "complete"},
        {"metric": "official_occupation_code", "count": sum(m["official_occupation_status"] == "official_code" for m in metadata.values()), "denominator": len(features), "status": "observed"},
        {"metric": "company_observed", "count": sum(m["company_status"] == "observed_company_scrape_entity" for m in metadata.values()), "denominator": len(features), "status": "observed"},
        {"metric": "evidence_rows", "count": evidence_rows, "denominator": len(features), "status": "nonadditive_evidence_count"},
    ]

    write_csv(os.path.join(args.output, "TECHNOLOGY_GROUPS_PUBLIC.csv"), tech_rows, list(tech_rows[0]))
    write_csv(os.path.join(args.output, "RAW_OUTCOME_RATES_PUBLIC.csv"), raw_rows, list(raw_rows[0]))
    write_csv(os.path.join(args.output, "OCCUPATION_STANDARDIZED_COMPARISONS_PUBLIC.csv"), std, list(std[0]))
    write_csv(os.path.join(args.output, "COMPANY_OCCUPATION_SENSITIVITY_PUBLIC.csv"), company, list(company[0]))
    write_csv(os.path.join(args.output, "ENTRY_RESPONSIBILITY_COOCCURRENCE_PUBLIC.csv"), entry_rows, list(entry_rows[0]))
    write_csv(os.path.join(args.output, "COVERAGE_PUBLIC.csv"), coverage, list(coverage[0]))

    public_files = ["TECHNOLOGY_GROUPS_PUBLIC.csv", "RAW_OUTCOME_RATES_PUBLIC.csv",
                    "OCCUPATION_STANDARDIZED_COMPARISONS_PUBLIC.csv", "COMPANY_OCCUPATION_SENSITIVITY_PUBLIC.csv",
                    "ENTRY_RESPONSIBILITY_COOCCURRENCE_PUBLIC.csv", "COVERAGE_PUBLIC.csv"]
    summary = {
        "version": VERSION, "status": "complete", "coverage_posting_denominator": len(features),
        "analysis_posting_denominator": len(analysis_features), "processing_status_counts": dict(processing_counts),
        "scope": "accepted first-five canonical US advertisements only",
        "technology_partition": dict(partition), "evidence_rows": evidence_rows,
        "metadata_counts": {"official_occupation": sum(m["official_occupation_status"] == "official_code" for m in metadata.values()),
                            "company_observed": sum(m["company_status"] == "observed_company_scrape_entity" for m in metadata.values())},
        "entry_limitations": ["combined_junior_wording cannot distinguish title from body in the frozen narrow schema",
                              "graduate wording has no stored scope and is not treated as unconditional",
                              "no-observed wording remains unknown rather than semantic absence"],
        "interpretation": decision["claims"],
    }
    atomic_json(os.path.join(args.output, "SUMMARY_PUBLIC.json"), summary)
    public_files.append("SUMMARY_PUBLIC.json")
    receipt = {
        "version": VERSION, "status": "pass", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scheduler": {"job_id": os.environ.get("SLURM_JOB_ID"), "host": platform.node(),
                      "cpus": os.environ.get("SLURM_CPUS_PER_TASK")},
        "runtime": {"python": platform.python_version(), "pyarrow": __import__("pyarrow").__version__},
        "inputs": {"manifest_sha256": sha256(args.manifest), "metadata_sha256": sha256(args.metadata),
                   "metadata_qa_sha256": sha256(args.metadata_qa), "decision_sha256": sha256(args.decision),
                   "shards": receipt_bindings},
        "code_sha256": sha256(__file__), "coverage_posting_denominator": len(features),
        "analysis_posting_denominator": len(analysis_features), "processing_status_counts": dict(processing_counts),
        "evidence_rows": evidence_rows,
        "checks": {"exact_424226": len(features) == 424226, "metadata_exact_key_set": set(metadata) == set(features),
                   "technology_partition_processed_only": sum(partition.values()) == len(analysis_features),
                   "accepted_processing_partition": processing_counts == {"processed": 424225, "invalid_text": 1},
                   "no_row_identifiers_in_public_tables": True},
        "outputs": {p: {"sha256": sha256(os.path.join(args.output, p)), "bytes": os.path.getsize(os.path.join(args.output, p))}
                    for p in public_files},
        "api_calls": 0, "model_calls": 0, "rules_changed": False,
        "claim_boundary": decision["claims"],
    }
    atomic_json(os.path.join(args.output, "RUN_RECEIPT_PUBLIC.json"), receipt)


if __name__ == "__main__":
    main()
