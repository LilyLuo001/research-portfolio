#!/usr/bin/env python3
"""D66 bounded old/current overlap comparison for the accepted first five shards.

Reads only retained narrow/evidence products.  It does not read full text, run a
model, expand rules, or impute old occupation/task experience.
"""
import argparse
import collections
import csv
import datetime as dt
import glob
import hashlib
import json
import os
import platform

import pyarrow as pa
import pyarrow.parquet as pq


VERSION = "d66-reuse-first5-overlap-v1"
KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
AI = {"genai", "predictive_ai", "ai_unspecified"}
CURRENT_OBJECTS = {"general_work", "occupation_task", "industry_domain", "tool"}
OLD_TO_CURRENT = {"general_work": "general_work", "specific_tool": "tool", "industry_domain": "industry_domain"}
FULL_IDS = (
    "b605d84d410013b172391b85e09af6012057c75aaf85003a43d4847379931e38",
    "b9376a87ec3e8b7c72d028e376524926a10980d849cb84cc3c34e5ef2e254102",
    "fc4fc3a546b62738be0ed236bb15399906a678796d0cbb08f26c2dfca6ea28aa",
    "3d07a85fc3160eed1d085e92ec5d7ba2be42240429c786b68b6b1ad62533f0fe",
    "41305ab79b0f9fcd190f6cbd169bb7f15d05babf7c1e2fe54f17d64a3b0394be",
)


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


def write_csv(path, rows, fields=None):
    if fields is None:
        fields = list(rows[0])
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(rows)
    os.replace(tmp, path)


def iter_rows(paths, columns, batch_size=65536):
    if isinstance(paths, str):
        paths = [paths]
    for path in paths:
        pf = pq.ParquetFile(path)
        for batch in pf.iter_batches(batch_size=batch_size, columns=columns):
            data = batch.to_pydict(); names = list(data)
            for i in range(batch.num_rows):
                yield {name: data[name][i] for name in names}


def key(row):
    return tuple(row[x] for x in KEY)


def frac(a, b):
    return a / b if b else None


def current_group(feature):
    software = "software" in feature["tech"]
    ai = bool(AI & feature["tech"])
    if software and ai: return "software_and_ai"
    if software: return "software_only"
    if ai: return "ai_only"
    return "neither_observed"


def in_arm(group, arm):
    if arm == "software_only": return group == "software_only"
    if arm == "any_ai": return group in ("ai_only", "software_and_ai")
    raise ValueError(arm)


def evidence_locator(row, source, fields):
    out = {"source": source}
    for name in fields:
        value = row.get(name)
        if value is not None:
            out[name] = value
    return out


class LocatorSink:
    """Bounded-memory private evidence provenance writer."""
    schema = pa.schema([
        ("JOB_HASH", pa.string()), ("SOURCE_FILE", pa.string()), ("SOURCE_ROW", pa.int64()),
        ("RECORD_SOURCE_ROW", pa.int64()), ("source_version", pa.string()), ("kind", pa.string()),
        ("evidence_ordinal", pa.int32()), ("start", pa.int64()), ("end", pa.int64()),
        ("quote_or_context", pa.string()), ("object_or_candidate", pa.string()),
        ("min_years", pa.float64()), ("max_years", pa.float64()), ("bound_or_duration", pa.string()),
        ("scope_or_relation", pa.string()), ("outcome_or_strength", pa.string()),
        ("applicant_context_candidate", pa.bool_()), ("uncertainty_json", pa.string()),
    ])
    def __init__(self, path):
        self.path = path; self.tmp = path + ".tmp"; self.buffer = []; self.rows = 0
        self.writer = pq.ParquetWriter(self.tmp, self.schema, compression="zstd")
    def add(self, canonical_key, source, kind, ordinal, start, end, quote, object_name,
            lower, upper, bound, scope, outcome, applicant, uncertainty):
        self.buffer.append(dict(zip(KEY, canonical_key), source_version=source, kind=kind,
            evidence_ordinal=ordinal, start=start, end=end, quote_or_context=quote,
            object_or_candidate=object_name, min_years=lower, max_years=upper,
            bound_or_duration=bound, scope_or_relation=scope, outcome_or_strength=outcome,
            applicant_context_candidate=applicant,
            uncertainty_json=json.dumps(uncertainty, separators=(",", ":"), sort_keys=True)))
        if len(self.buffer) >= 32768: self.flush()
    def flush(self):
        if self.buffer:
            self.writer.write_table(pa.Table.from_pylist(self.buffer, schema=self.schema)); self.rows += len(self.buffer); self.buffer = []
    def close(self):
        self.flush(); self.writer.close(); os.replace(self.tmp, self.path)


def current_value(f, dimension, measure):
    return dimension in f["current_" + measure]


def old_value(f, dimension, measure):
    old_obj = {v: k for k, v in OLD_TO_CURRENT.items()}[dimension]
    return f.get("old_exp_%s_%s" % (old_obj, measure))


def responsibility_value(f, marker):
    if marker == "current_independent_work_or_responsibility_wording": return f["independent"]
    if marker == "current_client_responsibility_wording": return f["client"]
    if marker == "current_people_supervision_wording": return f["supervision"]
    if marker == "current_d57_duty_mentoring_candidate": return f["mentoring"]
    if marker == "current_any_broad_responsibility_wording":
        return f["independent"] or f["client"] or f["supervision"] or f["mentoring"]
    if marker == "current_duty_context_restricted_responsibility_candidate": return f["duty_context_responsibility"]
    raise ValueError(marker)


def population_keys(features, name):
    if name == "old_matched_current_processed":
        return [k for k, f in features.items() if f["current_processed"] and f["old_match"]]
    if name == "old_usable_current_processed":
        return [k for k, f in features.items() if f["current_processed"] and f["old_match"] and f["old_usable"]]
    raise ValueError(name)


def standardize(features, metadata, population_name, threshold=20):
    keys = population_keys(features, population_name)
    by_occ = collections.defaultdict(lambda: {"software_only": [], "any_ai": []})
    arm_valid = collections.Counter()
    for k in keys:
        md = metadata[k]; f = features[k]
        if md["official_occupation_status"] != "official_code" or not md["ONET_OCCUPATION_CODE"]:
            continue
        arm = "software_only" if in_arm(f["current_technology_group"], "software_only") else \
              "any_ai" if in_arm(f["current_technology_group"], "any_ai") else None
        if arm is None: continue
        arm_valid[arm] += 1
        by_occ[md["ONET_OCCUPATION_CODE"]][arm].append(k)
    kept = {o: v for o, v in by_occ.items()
            if len(v["software_only"]) >= threshold and len(v["any_ai"]) >= threshold}
    total_weight = sum(min(len(v["software_only"]), len(v["any_ai"])) for v in kept.values())
    retained = {a: sum(len(v[a]) for v in kept.values()) for a in ("software_only", "any_ai")}
    outcomes = []
    for dimension in ("general_work", "tool", "industry_domain", "occupation_task"):
        versions = (("old", "broad"), ("current", "broad"), ("old", "main"), ("current", "main"))
        for version, measure in versions:
            available = not (version == "old" and dimension == "occupation_task")
            row = {
                "population": population_name,
                "comparison": "software_only_vs_any_ai",
                "technology_group_source": "fixed_current_rule_v1_2_nonnegated_lexical_group",
                "occupation_threshold_each_arm": threshold,
                "eligible_occupation_count": len(kept),
                "weight_basis": "min(software_only_n,any_ai_n)_normalized",
                "dimension": dimension,
                "measurement_version": version,
                "measure": measure,
                "status": "estimated_candidate_wording" if available and total_weight else
                          "unavailable_old_occupation_task_unmeasured" if not available else "unavailable_no_supported_cells",
                "software_only_valid_occupation_n": arm_valid["software_only"],
                "any_ai_valid_occupation_n": arm_valid["any_ai"],
                "software_only_retained_n": retained["software_only"],
                "any_ai_retained_n": retained["any_ai"],
                "total_min_count_weight": total_weight,
            }
            for arm in ("software_only", "any_ai"):
                values = []
                weighted = 0.0
                for occ, cell in kept.items():
                    vals = [old_value(features[k], dimension, measure) if version == "old"
                            else current_value(features[k], dimension, measure) for k in cell[arm]] if available else []
                    if available:
                        values.extend(vals)
                        weighted += (min(len(cell["software_only"]), len(cell["any_ai"])) / total_weight) * frac(sum(vals), len(vals))
                row[arm + "_raw_common_support_rate"] = frac(sum(values), len(values)) if available else None
                row[arm + "_standardized_rate"] = weighted if available and total_weight else None
            left, right = row["software_only_standardized_rate"], row["any_ai_standardized_rate"]
            row["difference_any_ai_minus_software_percentage_points"] = (right-left)*100 if left is not None else None
            outcomes.append(row)
    support = {
        "population": population_name,
        "population_n": len(keys),
        "occupation_threshold_each_arm": threshold,
        "eligible_occupation_count": len(kept),
        "software_only_valid_occupation_n": arm_valid["software_only"],
        "any_ai_valid_occupation_n": arm_valid["any_ai"],
        "software_only_retained_n": retained["software_only"],
        "any_ai_retained_n": retained["any_ai"],
        "software_only_retained_share": frac(retained["software_only"], arm_valid["software_only"]),
        "any_ai_retained_share": frac(retained["any_ai"], arm_valid["any_ai"]),
        "total_min_count_weight": total_weight,
        "weight_check_sum": sum(min(len(v["software_only"]), len(v["any_ai"])) / total_weight for v in kept.values()) if total_weight else None,
    }
    return outcomes, support


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--current-manifest", required=True)
    ap.add_argument("--metadata", required=True)
    ap.add_argument("--old-stage", required=True)
    ap.add_argument("--contract", required=True)
    ap.add_argument("--private-output", required=True)
    ap.add_argument("--public-output", required=True)
    args = ap.parse_args()
    os.makedirs(args.private_output, exist_ok=True); os.makedirs(args.public_output, exist_ok=True)
    manifest = json.load(open(args.current_manifest, encoding="utf-8"))
    contract = json.load(open(args.contract, encoding="utf-8"))
    if len(manifest.get("shards", [])) != 5: raise RuntimeError("exactly five current shards required")
    locator_path = os.path.join(args.private_output, "FIRST5_OLD_CURRENT_EVIDENCE_LOCATORS_PRIVATE.parquet")
    locator_sink = LocatorSink(locator_path)

    features = {}
    posting_cols = list(KEY) + ["processing_status", "flags_json", "d57_current_duty_mentoring_candidate"]
    for shard in manifest["shards"]:
        for row in iter_rows(shard["posting"], posting_cols):
            k = key(row)
            if k in features: raise RuntimeError("duplicate current canonical key")
            flags = json.loads(row["flags_json"] or "{}")
            features[k] = {
                "current_processed": row["processing_status"] == "processed",
                "current_processing_status": row["processing_status"],
                "tech": set(), "current_broad": set(), "current_main": set(),
                "current_numeric": False, "current_conditional": False,
                "current_experience_unknown": False, "current_noexp": False,
                "current_noexp_unconditional": False, "current_graduate": bool(flags.get("graduate_language")),
                "independent": bool(flags.get("task_independent_responsibility")),
                "client": bool(flags.get("task_client_ownership")),
                "supervision": bool(flags.get("task_people_supervision")),
                "mentoring": row["d57_current_duty_mentoring_candidate"] is True,
                "duty_context_responsibility": False,
                "old_match": False, "old_usable": False, "old_audit_row_present": False,
                "old_noexperience_explicit": False, "old_noexperience_applicant_context": False,
                "old_noexperience_unconditional": False, "old_noexperience_negated_or_optional": False,
                "old_qualification_alternative_candidate": False, "old_equivalent_experience": False,
                "old_qualification_relation_unresolved": False, "old_mixed_requirement_scope": False,
                "old_context_conflict": False, "old_numeric_literal_candidate": False,
            }
    if len(features) != 424226: raise RuntimeError("current canonical denominator changed")

    evcols = list(KEY) + ["evidence_index", "kind", "rule", "start", "end", "quote", "section", "objects_json", "scope",
                                  "duration_kind", "lower_years", "upper_years", "outcome_status", "technology",
                                  "negated", "task_family", "candidate_heading_scope", "heading_scope_status"]
    current_evidence_rows = 0
    for shard in manifest["shards"]:
        for row in iter_rows(shard["evidence"], evcols):
            current_evidence_rows += 1; k = key(row)
            if k not in features: raise RuntimeError("orphan current evidence")
            f = features[k]
            if row["kind"] == "technology" and row["negated"] is not True and row["technology"]:
                f["tech"].add(row["technology"])
            elif row["kind"] == "experience":
                objs = [x for x in json.loads(row["objects_json"] or "[]") if x in CURRENT_OBJECTS]
                f["current_broad"].update(objs)
                if len(objs) == 1 and row["outcome_status"] == "explicit_rule_candidate" and row["scope"] == "unconditional_explicit_clause":
                    f["current_main"].add(objs[0])
                f["current_numeric"] |= bool(row["duration_kind"] or row["lower_years"] is not None or row["upper_years"] is not None)
                f["current_conditional"] |= row["scope"] in ("education_alternative", "other_conditional", "document_multiline_alternative_unresolved")
                f["current_experience_unknown"] |= row["scope"] not in ("unconditional_explicit_clause", "education_alternative", "other_conditional", "document_multiline_alternative_unresolved") or row["outcome_status"] != "explicit_rule_candidate"
            elif row["kind"] == "entry" and row["rule"] == "explicit_no_experience":
                if json.loads(row["objects_json"] or "[]") == ["general_work"]:
                    f["current_noexp"] = True
                    f["current_noexp_unconditional"] |= row["scope"] == "unconditional_explicit_clause"
            if row["kind"] == "task":
                f["duty_context_responsibility"] |= (row["task_family"] in
                    ("independent_responsibility", "client_ownership", "people_supervision")
                    and row["section"] == "duties" and row["candidate_heading_scope"] == "duties")
            if row["kind"] in ("experience", "entry", "task"):
                locator_sink.add(k, "current_rulefirst_evidence", row["kind"], row["evidence_index"], row["start"], row["end"], row["quote"],
                    row["objects_json"] if row["kind"] != "task" else row["task_family"], row["lower_years"], row["upper_years"], row["duration_kind"],
                    row["scope"], row["outcome_status"], None,
                    {"rule":row["rule"], "section":row["section"], "candidate_heading_scope":row["candidate_heading_scope"],
                     "heading_scope_status":row["heading_scope_status"]})
    for f in features.values(): f["current_technology_group"] = current_group(f)

    narrow_root = os.path.join(args.old_stage, "linkup_analysis_execution_oct02/private/semantic_narrow_v1/shards")
    old_cols = list(KEY) + ["usable"] + ["exp_%s_%s" % (obj, measure)
        for obj in ("general_work", "specific_tool", "industry_domain") for measure in ("main", "required", "preferred", "broad", "exact_or_unspecified")]
    old_rows = 0; old_only = 0
    old_paths = [os.path.join(narrow_root, fid + ".parquet") for fid in FULL_IDS]
    if any(not os.path.isfile(p) for p in old_paths): raise RuntimeError("missing one or more staged old narrow shards")
    for row in iter_rows(old_paths, old_cols):
        old_rows += 1; k = key(row)
        if k not in features: old_only += 1; continue
        f = features[k]
        if f["old_match"]: raise RuntimeError("duplicate old canonical key")
        f["old_match"] = True; f["old_usable"] = row["usable"] is True
        for name in old_cols[5:]: f["old_" + name] = row[name]

    typed_root = os.path.join(args.old_stage, "linkup_release_v1/full_semantic_v1")
    old_exp_cols = list(KEY) + ["EVIDENCE_ORDINAL", "CLAUSE_START", "CLAUSE_END", "OBJECT_START", "OBJECT_END",
                                "OBJECT_TYPE", "MIN_YEARS", "MAX_YEARS", "DURATION_UNIT", "BOUND_TYPE",
                                "BINDING_STATUS", "RELATION", "OPTIONAL", "CONTEXT", "APPLICANT_CONTEXT_CANDIDATE", "REQUIREMENT_STRENGTH"]
    old_exp_paths = []
    for fid in FULL_IDS:
        found = sorted(glob.glob(os.path.join(typed_root, fid, "chunk_*", "experience.parquet")))
        if not found: raise RuntimeError("missing staged old experience files for " + fid)
        old_exp_paths += found
    old_experience_rows = 0
    for row in iter_rows(old_exp_paths, old_exp_cols):
        old_experience_rows += 1; k = key(row)
        if k not in features: continue
        features[k]["old_numeric_literal_candidate"] |= row["MIN_YEARS"] is not None or row["MAX_YEARS"] is not None
        locator_sink.add(k, "old_typed_experience", "experience", row["EVIDENCE_ORDINAL"], row["CLAUSE_START"], row["CLAUSE_END"], row["CONTEXT"],
            row["OBJECT_TYPE"], row["MIN_YEARS"], row["MAX_YEARS"], row["BOUND_TYPE"], row["RELATION"], row["REQUIREMENT_STRENGTH"],
            row["APPLICANT_CONTEXT_CANDIDATE"], {"object_start":row["OBJECT_START"], "object_end":row["OBJECT_END"],
            "binding_status":row["BINDING_STATUS"], "optional":row["OPTIONAL"], "duration_unit":row["DURATION_UNIT"]})

    aud_cols = list(KEY) + ["EVIDENCE_ORDINAL", "MODULE", "START", "END", "CANDIDATE_TYPE", "VALUE", "DEGREE_LEVEL",
        "EDUCATION_STATUS", "ATTAINED_DEGREE", "MIN_YEARS", "MAX_YEARS", "DURATION_UNIT", "BOUND_TYPE",
        "NO_EXPERIENCE_EXPLICIT", "REQUIREMENT_STRENGTH", "APPLICANT_CONTEXT_CANDIDATE", "IS_APPLICANT_REQUIREMENT",
        "IS_UNCONDITIONAL_EXPERIENCE_REQUIREMENT", "NEGATED", "NEGATED_OR_OPTIONAL", "EQUIVALENCE_TYPE",
        "EQUIVALENT_EXPERIENCE", "EQUIVALENT_CREDENTIAL", "ALTERNATIVE_TRAINING_OR_EXPERIENCE",
        "ALTERNATIVE_TRAINING_OR_EDUCATION", "QUALIFICATION_RELATION_UNRESOLVED", "MIXED_REQUIREMENT_SCOPE",
        "QUALIFICATION_SCOPE_START", "QUALIFICATION_SCOPE_END", "LOCAL_PATH_SCOPE_APPLIED", "CONTEXT_CONFLICT",
        "AMBIGUOUS_DEGREE_ABBREVIATION", "EDUCATION_ENROLLMENT_MENTION_CANDIDATE", "QUALIFICATION_PRESENCE_RULE", "CONTEXT"]
    aud_paths = []
    for fid in FULL_IDS:
        found = sorted(glob.glob(os.path.join(typed_root, fid, "chunk_*", "v6_audit.parquet")))
        if not found: raise RuntimeError("missing staged old v6_audit files for " + fid)
        aud_paths += found
    old_audit_rows = 0
    for row in iter_rows(aud_paths, aud_cols):
        old_audit_rows += 1; k = key(row)
        if k not in features: continue
        f = features[k]; f["old_audit_row_present"] = True
        noexp = row["NO_EXPERIENCE_EXPLICIT"] is True
        f["old_noexperience_explicit"] |= noexp
        f["old_noexperience_applicant_context"] |= noexp and row["APPLICANT_CONTEXT_CANDIDATE"] is True
        f["old_noexperience_unconditional"] |= noexp and row["IS_UNCONDITIONAL_EXPERIENCE_REQUIREMENT"] is True
        f["old_noexperience_negated_or_optional"] |= noexp and row["NEGATED_OR_OPTIONAL"] is True
        f["old_qualification_alternative_candidate"] |= any(row[x] is True for x in
            ("EQUIVALENT_CREDENTIAL", "ALTERNATIVE_TRAINING_OR_EXPERIENCE", "ALTERNATIVE_TRAINING_OR_EDUCATION"))
        f["old_equivalent_experience"] |= row["EQUIVALENT_EXPERIENCE"] is True
        f["old_qualification_relation_unresolved"] |= row["QUALIFICATION_RELATION_UNRESOLVED"] is True
        f["old_mixed_requirement_scope"] |= row["MIXED_REQUIREMENT_SCOPE"] is True
        f["old_context_conflict"] |= row["CONTEXT_CONFLICT"] is True
        f["old_numeric_literal_candidate"] |= row["MIN_YEARS"] is not None or row["MAX_YEARS"] is not None
        locator_sink.add(k, "old_typed_v6_audit", row["MODULE"], row["EVIDENCE_ORDINAL"], row["START"], row["END"], row["CONTEXT"],
            row["CANDIDATE_TYPE"], row["MIN_YEARS"], row["MAX_YEARS"], row["BOUND_TYPE"], row["EQUIVALENCE_TYPE"],
            row["REQUIREMENT_STRENGTH"], row["APPLICANT_CONTEXT_CANDIDATE"],
            {x:row[x] for x in ("NO_EXPERIENCE_EXPLICIT","IS_APPLICANT_REQUIREMENT","IS_UNCONDITIONAL_EXPERIENCE_REQUIREMENT",
             "NEGATED","NEGATED_OR_OPTIONAL","EQUIVALENT_EXPERIENCE","EQUIVALENT_CREDENTIAL","ALTERNATIVE_TRAINING_OR_EXPERIENCE",
             "ALTERNATIVE_TRAINING_OR_EDUCATION","QUALIFICATION_RELATION_UNRESOLVED","MIXED_REQUIREMENT_SCOPE","CONTEXT_CONFLICT")})
    locator_sink.close()

    metadata = {}
    mdcols = list(KEY) + ["ONET_OCCUPATION_CODE", "official_occupation_status"]
    for row in iter_rows(args.metadata, mdcols):
        k = key(row)
        if k in metadata: raise RuntimeError("duplicate metadata key")
        metadata[k] = row
    if set(metadata) != set(features): raise RuntimeError("metadata/current exact key mismatch")

    private_rows = []
    for k, f in features.items():
        row = dict(zip(KEY, k))
        row.update({
            "current_processing_status": f["current_processing_status"], "old_match": f["old_match"], "old_usable": f["old_usable"],
            "current_technology_group": f["current_technology_group"], "ONET_OCCUPATION_CODE": metadata[k]["ONET_OCCUPATION_CODE"],
            "official_occupation_status": metadata[k]["official_occupation_status"],
            "current_general_work_broad": "general_work" in f["current_broad"], "current_general_work_main": "general_work" in f["current_main"],
            "current_tool_broad": "tool" in f["current_broad"], "current_tool_main": "tool" in f["current_main"],
            "current_industry_domain_broad": "industry_domain" in f["current_broad"], "current_industry_domain_main": "industry_domain" in f["current_main"],
            "current_occupation_task_broad": "occupation_task" in f["current_broad"], "current_occupation_task_main": "occupation_task" in f["current_main"],
            "old_occupation_task_available": False, "old_occupation_task_broad": None, "old_occupation_task_main": None,
            "current_numeric_literal_candidate": f["current_numeric"], "current_conditional_or_alternative_candidate": f["current_conditional"],
            "current_experience_unknown": f["current_experience_unknown"], "current_explicit_noexperience_candidate": f["current_noexp"],
            "current_explicit_noexperience_unconditional_candidate": f["current_noexp_unconditional"], "current_graduate_wording_candidate": f["current_graduate"],
            "old_audit_row_present": f["old_audit_row_present"], "old_explicit_noexperience_candidate": f["old_noexperience_explicit"],
            "old_explicit_noexperience_applicant_context_candidate": f["old_noexperience_applicant_context"],
            "old_explicit_noexperience_unconditional_source_flag_not_applicable": f["old_noexperience_unconditional"],
            "old_explicit_noexperience_negated_or_optional": f["old_noexperience_negated_or_optional"],
            "old_qualification_alternative_candidate": f["old_qualification_alternative_candidate"],
            "old_equivalent_experience_candidate": f["old_equivalent_experience"],
            "old_qualification_relation_unresolved": f["old_qualification_relation_unresolved"],
            "old_mixed_requirement_scope": f["old_mixed_requirement_scope"], "old_context_conflict": f["old_context_conflict"],
            "old_numeric_literal_candidate": f["old_numeric_literal_candidate"],
            "current_independent_work_or_responsibility_wording": f["independent"], "current_client_responsibility_wording": f["client"],
            "current_people_supervision_wording": f["supervision"], "current_d57_duty_mentoring_candidate": f["mentoring"],
            "current_duty_context_restricted_responsibility_candidate": f["duty_context_responsibility"],
            "evidence_locator_sidecar": os.path.basename(locator_path),
            "semantic_interpretation": "candidate_wording_or_unknown;not_gold",
        })
        for obj in ("general_work", "specific_tool", "industry_domain"):
            for measure in ("main", "required", "preferred", "broad", "exact_or_unspecified"):
                row["old_exp_%s_%s" % (obj, measure)] = f.get("old_exp_%s_%s" % (obj, measure))
        private_rows.append(row)
    private_path = os.path.join(args.private_output, "FIRST5_OLD_CURRENT_OVERLAY_PRIVATE.parquet")
    tmp = private_path + ".tmp"
    pq.write_table(pa.Table.from_pylist(private_rows), tmp, compression="zstd", row_group_size=32768)
    os.replace(tmp, private_path)

    matched = sum(f["old_match"] for f in features.values()); usable = sum(f["old_match"] and f["old_usable"] for f in features.values())
    coverage = [
        {"metric": "current_canonical_rows", "count": len(features), "denominator": len(features), "fraction": 1.0, "status": "complete"},
        {"metric": "current_processed_rows", "count": sum(f["current_processed"] for f in features.values()), "denominator": len(features), "fraction": frac(sum(f["current_processed"] for f in features.values()), len(features)), "status": "observed"},
        {"metric": "exact_key_old_match", "count": matched, "denominator": len(features), "fraction": frac(matched, len(features)), "status": "observed_preserve_unmatched"},
        {"metric": "old_engineering_usable", "count": usable, "denominator": matched, "fraction": frac(usable, matched), "status": "engineering_completeness_not_semantic_truth"},
        {"metric": "old_v6_audit_row_present", "count": sum(f["old_audit_row_present"] for f in features.values()), "denominator": matched, "fraction": frac(sum(f["old_audit_row_present"] for f in features.values()), matched), "status": "selected_audit_coverage"},
        {"metric": "old_typed_experience_evidence_rows", "count": old_experience_rows, "denominator": matched, "fraction": None, "status": "nonadditive_evidence_rows"},
        {"metric": "old_v6_audit_evidence_rows", "count": old_audit_rows, "denominator": matched, "fraction": None, "status": "nonadditive_evidence_rows"},
        {"metric": "current_evidence_rows", "count": current_evidence_rows, "denominator": len(features), "fraction": None, "status": "nonadditive_evidence_rows"},
    ]

    disagreement = []
    comparable_keys = population_keys(features, "old_usable_current_processed")
    for dimension in ("general_work", "tool", "industry_domain"):
        for old_measure, current_measure in (("broad", "broad"), ("main", "main")):
            a = sum(old_value(features[k], dimension, old_measure) and current_value(features[k], dimension, current_measure) for k in comparable_keys)
            b = sum(old_value(features[k], dimension, old_measure) and not current_value(features[k], dimension, current_measure) for k in comparable_keys)
            c = sum(not old_value(features[k], dimension, old_measure) and current_value(features[k], dimension, current_measure) for k in comparable_keys)
            d = len(comparable_keys)-a-b-c
            disagreement.append({"population": "old_usable_current_processed", "dimension": dimension,
                "old_measure": old_measure, "current_measure": current_measure, "both_candidate": a,
                "old_only_candidate": b, "current_only_candidate": c, "neither_rule_observed_candidate": d,
                "denominator": len(comparable_keys), "interpretation": "rule_disagreement_not_accuracy;no_hit_is_not_semantic_absence"})
    disagreement.append({"population": "old_usable_current_processed", "dimension": "occupation_task",
        "old_measure": "unavailable", "current_measure": "main", "both_candidate": None, "old_only_candidate": None,
        "current_only_candidate": None, "neither_rule_observed_candidate": None, "denominator": len(comparable_keys),
        "interpretation": "old_occupation_task_unmeasured_NA_not_zero"})

    core = []; supports = []
    for pop in ("old_matched_current_processed", "old_usable_current_processed"):
        rows, support = standardize(features, metadata, pop, 20); core += rows; supports.append(support)

    responsibilities = ("current_independent_work_or_responsibility_wording", "current_client_responsibility_wording",
        "current_people_supervision_wording", "current_d57_duty_mentoring_candidate", "current_any_broad_responsibility_wording",
        "current_duty_context_restricted_responsibility_candidate")
    marker_predicates = {
        "old_explicit_noexperience_candidate": lambda f: f["old_noexperience_explicit"],
        "old_explicit_noexperience_applicant_context_candidate": lambda f: f["old_noexperience_applicant_context"],
        "current_explicit_noexperience_candidate": lambda f: f["current_noexp"],
        "current_explicit_noexperience_unconditional_candidate": lambda f: f["current_noexp_unconditional"],
        "current_graduate_wording_candidate_scope_unknown": lambda f: f["current_graduate"],
        "current_noexperience_or_graduate_wording_union": lambda f: f["current_noexp"] or f["current_graduate"],
    }
    entry_keys = population_keys(features, "old_matched_current_processed")
    entry = []
    for marker, pred in marker_predicates.items():
        for resp in responsibilities:
            a=sum(pred(features[k]) and responsibility_value(features[k],resp) for k in entry_keys)
            b=sum(pred(features[k]) and not responsibility_value(features[k],resp) for k in entry_keys)
            c=sum(not pred(features[k]) and responsibility_value(features[k],resp) for k in entry_keys)
            d=len(entry_keys)-a-b-c
            entry.append({"population":"old_matched_current_processed", "entry_marker":marker, "responsibility_marker":resp,
                "entry_yes_responsibility_yes":a, "entry_yes_responsibility_no_observed":b,
                "entry_no_observed_responsibility_yes":c, "neither_rule_observed":d, "denominator":len(entry_keys),
                "cooccurrence_rate_within_entry_marker":frac(a,a+b),
                "interpretation":"wording_candidate_cooccurrence;not_eligibility_authority_or_seniority"})

    reuse = [
        {"research_field":"canonical_identity", "old_source":"ad narrow four-key", "current_source":"posting narrow four-key", "reuse_status":"exact_key_reused", "old_semantic_limit":"identity_only"},
        {"research_field":"engineering_status", "old_source":"usable and four failure flags", "current_source":"processing_status", "reuse_status":"versioned_side_by_side", "old_semantic_limit":"completeness_not_truth"},
        {"research_field":"general_work_experience", "old_source":"old exp_general_work_*", "current_source":"current evidence object general_work", "reuse_status":"versioned_candidate_comparison", "old_semantic_limit":"different binding taxonomy"},
        {"research_field":"tool_experience", "old_source":"old exp_specific_tool_*", "current_source":"current evidence object tool", "reuse_status":"versioned_candidate_comparison", "old_semantic_limit":"different object vocabulary"},
        {"research_field":"industry_domain_experience", "old_source":"old exp_industry_domain_*", "current_source":"current evidence object industry_domain", "reuse_status":"versioned_candidate_comparison", "old_semantic_limit":"different rule semantics"},
        {"research_field":"occupation_task_experience", "old_source":"not measured", "current_source":"current evidence object occupation_task", "reuse_status":"old_NA", "old_semantic_limit":"must_not_fill_zero"},
        {"research_field":"literal_numeric_experience", "old_source":"typed experience MIN/MAX and v6 audit literals", "current_source":"duration fields", "reuse_status":"candidate_coverage_only", "old_semantic_limit":"no fabricated universal minimum"},
        {"research_field":"explicit_noexperience", "old_source":"v6 audit NO_EXPERIENCE_EXPLICIT plus uncertainty flags", "current_source":"entry evidence explicit_no_experience", "reuse_status":"versioned_candidates", "old_semantic_limit":"selected audit; no row means not detected"},
        {"research_field":"qualification_alternative", "old_source":"equivalence/alternative flags", "current_source":"experience scope", "reuse_status":"versioned_candidates", "old_semantic_limit":"not degree-or-experience certification"},
        {"research_field":"responsibility", "old_source":"not complete in old frozen release", "current_source":"current flags and duty-context filter", "reuse_status":"current_only_wording_candidates", "old_semantic_limit":"no confirmed authority/seniority"},
    ]

    files = {
        "FIELD_REUSE_MAP_PUBLIC.csv": (reuse, None), "OVERLAP_COVERAGE_PUBLIC.csv": (coverage, None),
        "DISAGREEMENT_2X2_PUBLIC.csv": (disagreement, None), "COMMON_SUPPORT_PUBLIC.csv": (supports, None),
        "CORE_EXPERIENCE_COMPARISON_PUBLIC.csv": (core, None), "ENTRY_RESPONSIBILITY_COOCCURRENCE_PUBLIC.csv": (entry, None),
    }
    for name, (rows_, fields) in files.items(): write_csv(os.path.join(args.public_output,name), rows_, fields)

    summary = {"version":VERSION, "status":"complete", "current_rows":len(features), "old_rows":old_rows,
        "old_only_rows":old_only, "exact_key_matches":matched, "old_usable_matches":usable,
        "fixed_current_technology_groups":dict(collections.Counter(f["current_technology_group"] for f in features.values() if f["current_processed"])),
        "scope":"accepted first-five source-shard subset; not a probability sample",
        "limits":["old occupation/task experience is unmeasured and remains NA", "old/current differences are rule disagreements, not accuracy or AI effects",
                  "technology groups are held fixed from current lexical evidence", "responsibility outputs are wording candidates only",
                  "no-hit means not observed under that rule; semantic truth remains unknown"],
        "contract_decision":contract["decision"]}
    atomic_json(os.path.join(args.public_output,"SUMMARY_PUBLIC.json"),summary)
    public_names=list(files)+["SUMMARY_PUBLIC.json"]
    staged_files=old_paths+old_exp_paths+aud_paths
    receipt={"version":VERSION,"status":"pass","created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "scheduler":{"job_id":os.environ.get("SLURM_JOB_ID"),"host":platform.node(),"cpus":os.environ.get("SLURM_CPUS_PER_TASK")},
        "runtime":{"python":platform.python_version(),"pyarrow":__import__("pyarrow").__version__},
        "inputs":{"current_manifest_sha256":sha256(args.current_manifest),"metadata_sha256":sha256(args.metadata),
                  "contract_sha256":sha256(args.contract),"old_staged_files":len(staged_files),
                  "old_staged_bytes":sum(os.path.getsize(p) for p in staged_files)},
        "counts":{"current_rows":len(features),"old_rows":old_rows,"old_only_rows":old_only,"exact_key_matches":matched,
                  "old_usable_matches":usable,"current_evidence_rows":current_evidence_rows,"old_experience_rows":old_experience_rows,
                  "old_v6_audit_rows":old_audit_rows},
        "checks":{"current_key_unique":True,"old_key_unique":True,"metadata_exact_key_set":True,
                  "private_row_conservation":pq.ParquetFile(private_path).metadata.num_rows==len(features),
                  "old_occupation_task_all_null_and_unavailable":True,"fixed_current_group_used":True,
                  "same_population_and_weights_within_each_outcome_version":True},
        "private_output":{"path":private_path,"sha256":sha256(private_path),"bytes":os.path.getsize(private_path)},
        "private_evidence_locator_output":{"path":locator_path,"sha256":sha256(locator_path),"bytes":os.path.getsize(locator_path),"rows":locator_sink.rows},
        "public_outputs":{n:{"sha256":sha256(os.path.join(args.public_output,n)),"bytes":os.path.getsize(os.path.join(args.public_output,n))} for n in public_names},
        "api_calls":0,"model_calls":0,"full_text_reads":0,"rules_changed":False,
        "claim_boundary":"wording candidates in accepted first-five shards; no causal, adoption, seniority, authority, semantic-gold, or accuracy claim"}
    atomic_json(os.path.join(args.public_output,"RUN_RECEIPT_PUBLIC.json"),receipt)


if __name__ == "__main__":
    main()
