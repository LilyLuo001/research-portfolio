#!/usr/bin/env python3
"""Aggregate the fixed-support D67 closing package from existing evidence fields."""
import argparse, collections, csv, datetime as dt, hashlib, json, math, os, platform
from pathlib import Path

import pyarrow.parquet as pq

KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
DIMS = ("general_work", "tool", "industry_domain", "occupation_task")
ARMS = ("software_only", "any_ai")
THRESHOLD = 20
VERSION = "d67-closing-package-v1"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rows(path, columns=None):
    pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=32768, columns=columns):
        data = batch.to_pydict(); names = list(data)
        for i in range(batch.num_rows):
            yield {name: data[name][i] for name in names}


def key(row): return tuple(row[x] for x in KEY)


def arm(value):
    if value == "software_only": return "software_only"
    if value in ("ai_only", "software_and_ai"): return "any_ai"
    return None


def number(value):
    if value is None: return "NA"
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)): return "NA"
    return value


def atomic_json(path, value):
    temp = Path(str(path) + ".tmp"); temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def write_csv(path, values):
    if not values: raise RuntimeError("refusing empty public table " + str(path))
    temp = Path(str(path) + ".tmp")
    with open(temp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(values[0])); writer.writeheader(); writer.writerows(values)
    os.replace(temp, path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--global-manifest", required=True); p.add_argument("--frozen-manifest", required=True)
    p.add_argument("--ks-projection", required=True); p.add_argument("--wz-projection", required=True)
    p.add_argument("--common-support", required=True); p.add_argument("--output", required=True)
    a = p.parse_args(); gm = json.load(open(a.global_manifest)); frozen = json.load(open(a.frozen_manifest))
    if gm.get("status") != "complete" or gm.get("rows") != 5804936 or len(gm.get("shards", [])) != 69: raise RuntimeError("global manifest gate")
    frozen_by_id = {x["shard_id"]: x for x in frozen["shards"]}
    if len(frozen_by_id) != 69: raise RuntimeError("frozen manifest gate")

    cell = collections.Counter(); adnum = collections.Counter(); clauses = collections.Counter(); clause_ads = collections.Counter()
    totals = collections.Counter(); input_receipts = []
    strength_measures = []
    for dim in DIMS:
        for strength in ("required", "preferred", "mixed"):
            strength_measures += [
                ("current", dim, strength + "_any_scope", "current_%s_%s_any_scope" % (dim, strength)),
                ("current", dim, strength + "_unconditional", "current_%s_%s_unconditional" % (dim, strength)),
                ("current", dim, strength + "_conditional_or_alternative", "current_%s_%s_conditional_or_alternative" % (dim, strength)),
                ("current", dim, strength + "_unknown_scope", "current_%s_%s_unknown_scope" % (dim, strength)),
            ]
        strength_measures += [("current", dim, "strength_unknown", "current_%s_strength_unknown" % dim),
                              ("current", dim, "outcome_unknown", "current_%s_outcome_unknown" % dim)]
        if dim != "occupation_task":
            strength_measures += [("old", dim, "required", "old_exp_%s_required" % ("specific_tool" if dim == "tool" else dim)),
                                  ("old", dim, "preferred", "old_exp_%s_preferred" % ("specific_tool" if dim == "tool" else dim)),
                                  ("old", dim, "exact_or_unspecified", "old_exp_%s_exact_or_unspecified" % ("specific_tool" if dim == "tool" else dim))]
    scope_measures = [
        ("current", "conditional_or_alternative", "current_conditional_or_alternative_candidate", "current rule scope candidate"),
        ("current", "experience_unknown", "current_experience_unknown", "current rule scope or outcome unknown"),
        ("old", "qualification_alternative", "old_qualification_alternative_candidate", "selected sparse-audit candidate"),
        ("old", "equivalent_experience", "old_equivalent_experience_candidate", "selected sparse-audit candidate separate from broad alternative"),
        ("old", "qualification_relation_unresolved", "old_qualification_relation_unresolved", "selected sparse-audit candidate"),
        ("old", "mixed_requirement_scope", "old_mixed_requirement_scope", "selected sparse-audit candidate"),
        ("old", "context_conflict", "old_context_conflict", "selected sparse-audit candidate"),
        ("old", "v6_audit_row_present", "old_v6_audit_row_present", "selected sparse-audit coverage marker; absence is not a semantic negative"),
    ]
    enriched_cols = list(KEY) + ["current_processing_status", "old_match", "old_usable", "current_technology_group",
        "ONET_OCCUPATION_CODE", "official_occupation_status"] + sorted({x[3] for x in strength_measures if x[0] == "old"}) + [x[2] for x in scope_measures]
    feature_cols = list(KEY) + sorted({x[3] for x in strength_measures if x[0] == "current"})
    duration_cols = list(KEY) + ["evidence_index", "objects_json", "strength", "scope", "scope_class", "duration_kind",
        "lower_years", "upper_years", "strict_lower", "outcome_status"]

    for item in gm["shards"]:
        sid = item["shard_id"]; shard = frozen_by_id[sid]
        projection = Path(a.wz_projection if shard["region"] == "wuzhen" else a.ks_projection)
        rp = projection / (sid + ".closing.receipt.json"); rec = json.load(open(rp))
        fp = projection / (sid + ".strength_features.parquet"); dp = projection / (sid + ".duration_clauses.parquet")
        if rec.get("status") != "complete" or rec["input_evidence"]["sha256"] != shard["evidence_sha256"]: raise RuntimeError("projection receipt gate " + sid)
        for name, path in (("strength_features", fp), ("duration_clauses", dp)):
            if rec["outputs"][name]["sha256"] != sha(path) or rec["outputs"][name]["rows"] != pq.ParquetFile(path).metadata.num_rows: raise RuntimeError("projection output gate " + sid)
        input_receipts.append({"shard_id": sid, "region": shard["region"], "receipt_sha256": sha(rp), "evidence_sha256": shard["evidence_sha256"]})
        features = {}; duration = collections.defaultdict(list)
        for row in rows(fp, feature_cols):
            k = key(row)
            if k in features: raise RuntimeError("duplicate projected feature key " + sid)
            features[k] = row
        for row in rows(dp, duration_cols): duration[key(row)].append(row)

        n = 0
        for row in rows(item["enriched_path"], enriched_cols):
            n += 1; k = key(row); f = features.pop(k, None); dur = duration.pop(k, [])
            if not (row["current_processing_status"] == "processed" and row["old_match"] is True and row["old_usable"] is True): continue
            totals["ad_population"] += 1; totals["old_v6_audit_row_present"] += row["old_v6_audit_row_present"] is True
            ar = arm(row["current_technology_group"])
            occ = row["ONET_OCCUPATION_CODE"] if row["official_occupation_status"] == "official_code" else None
            if not ar or not occ: continue
            cell[(occ, ar)] += 1
            for version, dim, measure, field in strength_measures:
                value = (f or {}).get(field) if version == "current" else row[field]
                adnum[("strength", occ, ar, version, dim, measure)] += value is True
            for version, measure, field, note in scope_measures:
                adnum[("scope", occ, ar, version, "all_experience", measure)] += row[field] is True
            ad_seen = set()
            for clause in dur:
                raw_objects = json.loads(clause["objects_json"] or "[]")
                dims = [x for x in raw_objects if x in DIMS]
                if len(dims) == 1: duration_dims = dims
                elif len(dims) > 1: duration_dims = ["multiple_objects_unresolved"]
                else: duration_dims = ["object_unresolved_or_empty"]
                totals["common_support_numeric_clauses"] += 1
                for dim in duration_dims:
                    combo = (dim, clause["strength"] or "unknown", clause["scope_class"], clause["scope"] or "unknown",
                             clause["duration_kind"] or "unspecified_numeric", number(clause["lower_years"]),
                             number(clause["upper_years"]), str(clause["strict_lower"]), clause["outcome_status"] or "unknown")
                    clauses[(occ, ar) + combo] += 1; ad_seen.add(combo); totals["common_support_duration_measurement_instances"] += 1
            for combo in ad_seen: clause_ads[(occ, ar) + combo] += 1
        if n != item["rows"] or features or duration: raise RuntimeError("per-shard closing join conservation " + sid)

    occs = {occ for occ, ar in cell}; kept = {occ for occ in occs if cell[(occ, "software_only")] >= THRESHOLD and cell[(occ, "any_ai")] >= THRESHOLD}
    weights = {occ: min(cell[(occ, "software_only")], cell[(occ, "any_ai")]) for occ in kept}; tw = sum(weights.values())
    published = list(csv.DictReader(open(a.common_support, newline="", encoding="utf-8")))
    expected = next(x for x in published if x["population"] == "old_usable_current_processed")
    checks = {
        "eligible_occupation_count": len(kept) == int(expected["eligible_occupation_count"]) == 332,
        "software_retained": sum(cell[(o, "software_only")] for o in kept) == int(expected["software_only_retained_n"]),
        "any_ai_retained": sum(cell[(o, "any_ai")] for o in kept) == int(expected["any_ai_retained_n"]),
        "min_count_weight": tw == int(expected["total_min_count_weight"]),
        "ad_population": totals["ad_population"] == 5804788,
    }
    if not all(checks.values()): raise RuntimeError("published common-support binding failed " + repr(checks))

    def rates(counter, prefix):
        result = {}
        for ar in ARMS:
            numerator = sum(counter[prefix + (occ, ar)] for occ in kept) if False else None
        return result

    def summarize(flag_prefix):
        out = {}
        for ar in ARMS:
            den = sum(cell[(o, ar)] for o in kept); num = sum(adnum[flag_prefix[:1] + (o, ar) + flag_prefix[1:]] for o in kept)
            raw = num / den if den else None
            std = sum(weights[o] / tw * adnum[flag_prefix[:1] + (o, ar) + flag_prefix[1:]] / cell[(o, ar)] for o in kept) if tw else None
            out[ar] = (num, den, raw, std)
        return out

    strength_rows = []
    for version, dim, measure, field in strength_measures:
        z = summarize(("strength", version, dim, measure))
        strength_rows.append({"population": "old_usable_current_processed", "unit": "ad prevalence", "dimension": dim,
            "measurement_version": version, "measure": measure, "status": "estimated_existing_field_candidate",
            "software_only_numerator": z["software_only"][0], "software_only_denominator_ads": z["software_only"][1],
            "software_only_raw_rate": z["software_only"][2], "software_only_standardized_rate": z["software_only"][3],
            "any_ai_numerator": z["any_ai"][0], "any_ai_denominator_ads": z["any_ai"][1],
            "any_ai_raw_rate": z["any_ai"][2], "any_ai_standardized_rate": z["any_ai"][3],
            "difference_any_ai_minus_software_percentage_points": 100 * (z["any_ai"][3] - z["software_only"][3])})
    for measure in ("required", "preferred", "exact_or_unspecified"):
        strength_rows.append({"population": "old_usable_current_processed", "unit": "ad prevalence", "dimension": "occupation_task",
            "measurement_version": "old", "measure": measure, "status": "unavailable_old_occupation_task_unmeasured",
            "software_only_numerator": "NA", "software_only_denominator_ads": "NA", "software_only_raw_rate": "NA", "software_only_standardized_rate": "NA",
            "any_ai_numerator": "NA", "any_ai_denominator_ads": "NA", "any_ai_raw_rate": "NA", "any_ai_standardized_rate": "NA",
            "difference_any_ai_minus_software_percentage_points": "NA"})

    scope_rows = []
    for version, measure, field, note in scope_measures:
        z = summarize(("scope", version, "all_experience", measure))
        scope_rows.append({"population": "old_usable_current_processed", "unit": "ad prevalence", "measurement_version": version,
            "measure": measure, "measurement_note": note, "software_only_numerator": z["software_only"][0],
            "software_only_denominator_ads": z["software_only"][1], "software_only_standardized_rate": z["software_only"][3],
            "any_ai_numerator": z["any_ai"][0], "any_ai_denominator_ads": z["any_ai"][1],
            "any_ai_standardized_rate": z["any_ai"][3],
            "difference_any_ai_minus_software_percentage_points": 100 * (z["any_ai"][3] - z["software_only"][3])})

    combos = sorted({k[2:] for k in clauses}, key=lambda x: tuple(str(v) for v in x))
    duration_rows = []
    for combo in combos:
        row = dict(zip(("dimension", "strength", "scope_class", "scope", "duration_kind", "lower_years", "upper_years", "strict_lower", "outcome_status"), combo))
        values = {}
        for ar in ARMS:
            den = sum(cell[(o, ar)] for o in kept); cn = sum(clauses[(o, ar) + combo] for o in kept); an = sum(clause_ads[(o, ar) + combo] for o in kept)
            cstd = sum(weights[o] / tw * clauses[(o, ar) + combo] / cell[(o, ar)] for o in kept)
            astd = sum(weights[o] / tw * clause_ads[(o, ar) + combo] / cell[(o, ar)] for o in kept)
            values[ar] = (den, cn, an, cstd, astd)
        row.update({"population": "old_usable_current_processed", "measurement_version": "current",
            "clause_unit": "numeric_clause_measurement_instances", "ad_unit": "ads_with_at_least_one_matching_clause",
            "software_only_denominator_ads": values["software_only"][0], "software_only_clause_instances": values["software_only"][1],
            "software_only_ads": values["software_only"][2], "software_only_standardized_clauses_per_ad": values["software_only"][3],
            "software_only_standardized_ad_prevalence": values["software_only"][4],
            "any_ai_denominator_ads": values["any_ai"][0], "any_ai_clause_instances": values["any_ai"][1],
            "any_ai_ads": values["any_ai"][2], "any_ai_standardized_clauses_per_ad": values["any_ai"][3],
            "any_ai_standardized_ad_prevalence": values["any_ai"][4],
            "difference_standardized_clauses_per_100_ads": 100 * (values["any_ai"][3] - values["software_only"][3]),
            "difference_standardized_ad_prevalence_pp": 100 * (values["any_ai"][4] - values["software_only"][4]),
            "interpretation": "existing clause wording and bounds; not a job-level minimum"})
        duration_rows.append(row)

    software_ads = sum(cell[(o,"software_only")] for o in kept); any_ai_ads = sum(cell[(o,"any_ai")] for o in kept)
    denominator_rows = [{"population": "old_usable_current_processed", "denominator_type": "all_ads", "count": totals["ad_population"], "unit": "ads", "reference_denominator": totals["ad_population"], "note": "ad denominator"},
        {"population": "old_usable_current_processed", "denominator_type": "old_v6_audit_rows_present", "count": totals["old_v6_audit_row_present"], "unit": "ads_with_selected_audit_row", "reference_denominator": totals["ad_population"], "note": "sparse selected-audit coverage; no audit row is not a semantic negative"},
        {"population": "common_support", "denominator_type": "eligible_occupations", "count": len(kept), "unit": "occupations", "reference_denominator": len(kept), "note": "same fixed support as D67 final"},
        {"population": "common_support", "denominator_type": "software_only_ads", "count": software_ads, "unit": "ads", "reference_denominator": software_ads, "note": "ad denominator for software-only rates"},
        {"population": "common_support", "denominator_type": "any_ai_ads", "count": any_ai_ads, "unit": "ads", "reference_denominator": any_ai_ads, "note": "ad denominator for any-AI rates"},
        {"population": "common_support_numeric_evidence", "denominator_type": "numeric_experience_clauses", "count": totals["common_support_numeric_clauses"], "unit": "clauses", "reference_denominator": "NA", "note": "current numeric clauses attached to common-support ads; distinct from ad denominator"},
        {"population": "common_support_numeric_evidence", "denominator_type": "duration_measurement_instances", "count": totals["common_support_duration_measurement_instances"], "unit": "clause_measurement_instances", "reference_denominator": "NA", "note": "one per numeric clause; multi-object and empty/unresolved objects remain single unresolved categories"}]
    unavailable = [
        {"measure": "old_clause_level_duration_bounds_full69", "status": "not_projected_in_this_release", "reason": "Old experience and duration sidecars exist, but this closing release reads only D67 enriched old ad-level strength flags and sparse-audit candidates; absence here is not absence from the old release"},
        {"measure": "job_level_minimum_years", "status": "NA_not_defined", "reason": "multiple clauses, scopes, alternatives and ranges are retained; no synthetic job minimum is constructed"},
        {"measure": "old_occupation_task_strength", "status": "NA_unmeasured", "reason": "old measurement version has no occupation_task dimension"},
        {"measure": "company_by_occupation_sensitivity", "status": "not_delivered_out_of_scope", "reason": "closing package is fixed occupation support only"},
    ]
    interpretation_notes = [
        {"topic": "actual_method", "note": "Rule-only extraction reuse plus bounded qualitative adjudication; no medium-model item-by-item semantic decision and no production semantic validation."},
        {"topic": "general_work", "note": "Existing production-rule category requiring an explicit total/overall/general/professional/work/working/employment-experience cue under the frozen rule; it is not an arbitrary no-object fallback, and unfamiliar professional tails can remain unresolved."},
        {"topic": "graduate_language", "note": "The frozen NEWGRAD cue concerns new/recent/fresh graduates or graduates welcome/encouraged; graduate program and graduate of nursing are education evidence and must not be inferred as NEWGRAD from diagnostic examples."},
        {"topic": "multi_experience_or_alternative", "note": "Needs-review and alternative branches remain at their observed clause scope and uncertainty; they are not converted into an unconditional minimum experience requirement."},
    ]
    output = Path(a.output); output.mkdir(parents=True, exist_ok=True)
    names = {"DURATION_CLAUSE_DISTRIBUTION_PUBLIC.csv": duration_rows, "STRENGTH_COMPARISON_PUBLIC.csv": strength_rows,
             "ALTERNATIVE_UNKNOWN_COMPARISON_PUBLIC.csv": scope_rows, "DENOMINATORS_PUBLIC.csv": denominator_rows,
             "UNAVAILABLE_MEASURES_PUBLIC.csv": unavailable, "INTERPRETATION_NOTES_PUBLIC.csv": interpretation_notes}
    for name, value in names.items(): write_csv(output / name, value)
    summary = {"version": VERSION, "status": "complete", "actual_method": "rule-only extraction reuse plus bounded qualitative adjudication",
        "semantic_validation_status": "not_performed; no medium-model item-by-item semantic decision and no production semantic validation",
        "frozen_shards": 69, "ad_population": totals["ad_population"], "eligible_occupations": len(kept),
        "numeric_experience_clauses_on_common_support_ads": totals["common_support_numeric_clauses"],
        "limits": ["clause bounds and conditions are retained without constructing a job-level minimum",
                   "multi-object numeric clauses remain multiple_objects_unresolved rather than being assigned to each object",
                   "old full clause-level duration sidecars were not projected in this release",
                   "old occupation_task is structurally unmeasured", "old sparse-audit non-detection is not semantic absence"]}
    atomic_json(output / "CLOSING_PACKAGE_SUMMARY_PUBLIC.json", summary)
    receipt = {"version": VERSION, "status": "pass", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scheduler": {"job_id": os.environ.get("SLURM_JOB_ID"), "host": platform.node()}, "checks": checks,
        "frozen_shards": 69, "ad_population": totals["ad_population"], "eligible_occupations": len(kept),
        "total_min_count_weight": tw, "projection_receipts": input_receipts,
        "inputs": {"global_manifest_sha256": sha(a.global_manifest), "frozen_manifest_sha256": sha(a.frozen_manifest),
                   "published_common_support_sha256": sha(a.common_support)},
        "actual_method": "rule-only extraction reuse plus bounded qualitative adjudication",
        "semantic_validation_status": "not_performed; no medium-model item-by-item semantic decision and no production semantic validation",
        "code_sha256": sha(__file__), "public_outputs": {name: {"sha256": sha(output/name), "bytes": (output/name).stat().st_size, "rows": len(value)} for name, value in names.items()},
        "api_calls": 0, "model_calls": 0, "full_text_extractions": 0,
        "claim_boundary": "existing-field wording candidates on fixed current technology groups and common occupation support; no accuracy, causal, job-minimum, seniority or authority claim"}
    receipt["public_outputs"]["CLOSING_PACKAGE_SUMMARY_PUBLIC.json"] = {"sha256": sha(output/"CLOSING_PACKAGE_SUMMARY_PUBLIC.json"), "bytes": (output/"CLOSING_PACKAGE_SUMMARY_PUBLIC.json").stat().st_size, "rows": 1}
    atomic_json(output / "CLOSING_PACKAGE_RECEIPT_PUBLIC.json", receipt)


if __name__ == "__main__": main()
