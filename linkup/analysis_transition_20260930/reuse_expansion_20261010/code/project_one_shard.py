#!/usr/bin/env python3
"""Build one D67 additive old/current advertisement table from retained products."""
import argparse
import collections
import datetime as dt
import glob
import hashlib
import json
import os
import platform
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

VERSION = "d67-additive-overlay-v1"
KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
CURRENT_OBJECTS = {"general_work", "occupation_task", "industry_domain", "tool"}
AI = {"genai", "predictive_ai", "ai_unspecified"}
OLD_OBJECTS = ("general_work", "specific_tool", "industry_domain")
OLD_MEASURES = ("main", "required", "preferred", "broad", "exact_or_unspecified")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def iter_rows(paths, columns, batch_size=65536):
    if isinstance(paths, (str, Path)): paths = [paths]
    for path in paths:
        parquet = pq.ParquetFile(path)
        missing = set(columns) - set(parquet.schema_arrow.names)
        if missing: raise RuntimeError("input lacks columns: " + ",".join(sorted(missing)))
        for batch in parquet.iter_batches(batch_size=batch_size, columns=columns):
            values = batch.to_pydict(); names = list(values)
            for i in range(batch.num_rows):
                yield {name: values[name][i] for name in names}


def row_key(row): return tuple(row[x] for x in KEY)


def technology_group(values):
    software = "software" in values; ai = bool(AI & values)
    if software and ai: return "software_and_ai"
    if software: return "software_only"
    if ai: return "ai_only"
    return "neither_observed"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True); p.add_argument("--region", required=True)
    p.add_argument("--index", type=int, required=True); p.add_argument("--old-narrow-root", required=True)
    p.add_argument("--old-v6-root", required=True); p.add_argument("--old-v6-inventory", required=True)
    p.add_argument("--output-root", required=True)
    args = p.parse_args()
    manifest = json.load(open(args.manifest, encoding="utf-8"))
    shards = [x for x in manifest["shards"] if x["region"] == args.region]
    if not 0 <= args.index < len(shards): raise RuntimeError("index outside frozen regional manifest")
    shard = shards[args.index]; shard_id = shard["shard_id"]
    if shard["status"] != "complete" or shard["qa_status"] != "pass": raise RuntimeError("current shard not accepted")
    posting = shard["posting"]; evidence = shard["evidence"]
    if sha256(posting) != shard["posting_sha256"] or sha256(evidence) != shard["evidence_sha256"]:
        raise RuntimeError("current input identity mismatch")
    features = {}
    posting_cols = list(KEY) + ["processing_status", "flags_json", "d57_current_duty_mentoring_candidate"]
    for row in iter_rows(posting, posting_cols):
        k = row_key(row)
        if k in features: raise RuntimeError("duplicate current canonical key")
        flags = json.loads(row["flags_json"] or "{}")
        features[k] = {
            "current_processing_status": row["processing_status"], "tech": set(), "broad": set(), "main": set(),
            "current_numeric": False, "current_conditional": False, "current_unknown": False,
            "current_noexp": False, "current_noexp_unconditional": False,
            "graduate": bool(flags.get("graduate_language")),
            "independent": bool(flags.get("task_independent_responsibility")),
            "client": bool(flags.get("task_client_ownership")),
            "supervision": bool(flags.get("task_people_supervision")),
            "mentoring": row["d57_current_duty_mentoring_candidate"] is True,
            "strict_duty_responsibility": False, "old_match": False, "old_usable": None,
            "old_audit_row_present": False, "old_noexp": False, "old_noexp_applicant": False,
            "old_noexp_negated_optional": False, "old_qualification_alternative": False,
            "old_equivalent_experience": False, "old_unresolved": False, "old_mixed": False,
            "old_context_conflict": False, "old_audit_numeric": False,
        }
    if len(features) != shard["posting_rows"]: raise RuntimeError("posting denominator changed")
    evidence_cols = list(KEY) + ["kind", "rule", "section", "objects_json", "scope", "duration_kind",
        "lower_years", "upper_years", "outcome_status", "technology", "negated", "task_family",
        "candidate_heading_scope"]
    evidence_rows = 0
    for row in iter_rows(evidence, evidence_cols):
        evidence_rows += 1; k = row_key(row)
        if k not in features: raise RuntimeError("orphan current evidence")
        f = features[k]
        if row["kind"] == "technology" and row["negated"] is not True and row["technology"]:
            f["tech"].add(row["technology"])
        elif row["kind"] == "experience":
            objects = [x for x in json.loads(row["objects_json"] or "[]") if x in CURRENT_OBJECTS]
            f["broad"].update(objects)
            if len(objects) == 1 and row["outcome_status"] == "explicit_rule_candidate" and row["scope"] == "unconditional_explicit_clause":
                f["main"].add(objects[0])
            f["current_numeric"] |= bool(row["duration_kind"] or row["lower_years"] is not None or row["upper_years"] is not None)
            f["current_conditional"] |= row["scope"] in ("education_alternative", "other_conditional", "document_multiline_alternative_unresolved")
            f["current_unknown"] |= row["scope"] not in ("unconditional_explicit_clause", "education_alternative", "other_conditional", "document_multiline_alternative_unresolved") or row["outcome_status"] != "explicit_rule_candidate"
        elif row["kind"] == "entry" and row["rule"] == "explicit_no_experience":
            if json.loads(row["objects_json"] or "[]") == ["general_work"]:
                f["current_noexp"] = True; f["current_noexp_unconditional"] |= row["scope"] == "unconditional_explicit_clause"
        if row["kind"] == "task":
            f["strict_duty_responsibility"] |= (row["task_family"] in ("independent_responsibility", "client_ownership", "people_supervision")
                and row["section"] == "duties" and row["candidate_heading_scope"] == "duties")
    if evidence_rows != shard["evidence_rows"]: raise RuntimeError("evidence denominator changed")

    old_path = Path(args.old_narrow_root) / (shard_id + ".parquet")
    if not old_path.is_file() or sha256(old_path) != shard["old_narrow_sha256"]: raise RuntimeError("old narrow identity mismatch")
    old_cols = list(KEY) + ["usable"] + ["exp_%s_%s" % (o, m) for o in OLD_OBJECTS for m in OLD_MEASURES]
    old_rows = old_only = matches = 0
    for row in iter_rows(old_path, old_cols):
        old_rows += 1; k = row_key(row)
        if k not in features: old_only += 1; continue
        f = features[k]
        if f["old_match"]: raise RuntimeError("duplicate exact old match")
        f["old_match"] = True; f["old_usable"] = row["usable"] is True; matches += 1
        for name in old_cols[5:]: f["old_" + name] = row[name]
    if old_rows != shard["old_narrow_rows"]: raise RuntimeError("old narrow denominator changed")

    audit_cols = list(KEY) + ["MIN_YEARS", "MAX_YEARS", "NO_EXPERIENCE_EXPLICIT",
        "APPLICANT_CONTEXT_CANDIDATE", "NEGATED_OR_OPTIONAL", "EQUIVALENT_EXPERIENCE",
        "EQUIVALENT_CREDENTIAL", "ALTERNATIVE_TRAINING_OR_EXPERIENCE", "ALTERNATIVE_TRAINING_OR_EDUCATION",
        "QUALIFICATION_RELATION_UNRESOLVED", "MIXED_REQUIREMENT_SCOPE", "CONTEXT_CONFLICT"]
    audit_paths = sorted(glob.glob(str(Path(args.old_v6_root) / shard_id / "chunk_*" / "v6_audit.parquet")))
    if not audit_paths: raise RuntimeError("old v6 audit input absent")
    v6_inventory = json.load(open(args.old_v6_inventory, encoding="utf-8"))
    expected_v6 = {x["relative_path"]: x for x in v6_inventory["files"] if x["relative_path"].startswith(shard_id + "/")}
    actual_relative = {str(Path(path).relative_to(args.old_v6_root)) for path in audit_paths}
    if actual_relative != set(expected_v6): raise RuntimeError("old v6 staged path inventory mismatch")
    for path in audit_paths:
        relative = str(Path(path).relative_to(args.old_v6_root)); item = expected_v6[relative]
        if os.path.getsize(path) != item["bytes"] or sha256(path) != item["sha256"]:
            raise RuntimeError("old v6 staged file identity mismatch: " + relative)
    audit_rows = 0
    for row in iter_rows(audit_paths, audit_cols):
        audit_rows += 1; k = row_key(row)
        if k not in features: continue
        f = features[k]; f["old_audit_row_present"] = True
        noexp = row["NO_EXPERIENCE_EXPLICIT"] is True
        f["old_noexp"] |= noexp; f["old_noexp_applicant"] |= noexp and row["APPLICANT_CONTEXT_CANDIDATE"] is True
        f["old_noexp_negated_optional"] |= noexp and row["NEGATED_OR_OPTIONAL"] is True
        f["old_qualification_alternative"] |= any(row[x] is True for x in ("EQUIVALENT_CREDENTIAL", "ALTERNATIVE_TRAINING_OR_EXPERIENCE", "ALTERNATIVE_TRAINING_OR_EDUCATION"))
        f["old_equivalent_experience"] |= row["EQUIVALENT_EXPERIENCE"] is True
        f["old_unresolved"] |= row["QUALIFICATION_RELATION_UNRESOLVED"] is True
        f["old_mixed"] |= row["MIXED_REQUIREMENT_SCOPE"] is True
        f["old_context_conflict"] |= row["CONTEXT_CONFLICT"] is True
        f["old_audit_numeric"] |= row["MIN_YEARS"] is not None or row["MAX_YEARS"] is not None

    output_rows = []
    for k, f in features.items():
        row = dict(zip(KEY, k)); row.update({
            "shard_id": shard_id, "source_region": args.region, "overlay_version": VERSION,
            "current_processing_status": f["current_processing_status"], "old_match_status": "exact_key_match" if f["old_match"] else "old_key_not_matched",
            "old_match": f["old_match"], "old_usable": f["old_usable"],
            "current_technology_group": technology_group(f["tech"]),
            "current_general_work_broad": "general_work" in f["broad"], "current_general_work_main": "general_work" in f["main"],
            "current_tool_broad": "tool" in f["broad"], "current_tool_main": "tool" in f["main"],
            "current_industry_domain_broad": "industry_domain" in f["broad"], "current_industry_domain_main": "industry_domain" in f["main"],
            "current_occupation_task_broad": "occupation_task" in f["broad"], "current_occupation_task_main": "occupation_task" in f["main"],
            "old_occupation_task_available": False, "old_occupation_task_broad": None, "old_occupation_task_main": None,
            "current_numeric_literal_candidate": f["current_numeric"], "current_conditional_or_alternative_candidate": f["current_conditional"],
            "current_experience_unknown": f["current_unknown"], "current_explicit_noexperience_candidate": f["current_noexp"],
            "current_explicit_noexperience_unconditional_candidate": f["current_noexp_unconditional"],
            "current_graduate_wording_candidate": f["graduate"],
            "current_independent_responsibility_wording": f["independent"], "current_client_ownership_wording": f["client"],
            "current_people_supervision_wording": f["supervision"], "current_d57_duty_mentoring_candidate": f["mentoring"],
            "current_strict_duty_responsibility_candidate": f["strict_duty_responsibility"],
            "old_v6_audit_row_present": f["old_audit_row_present"],
            "old_v6_no_audit_row_status": "audit_row_observed" if f["old_audit_row_present"] else "candidate_not_detected_sparse_audit_not_semantic_absence",
            "old_explicit_noexperience_candidate": f["old_noexp"], "old_explicit_noexperience_applicant_context_candidate": f["old_noexp_applicant"],
            "old_explicit_noexperience_negated_or_optional": f["old_noexp_negated_optional"],
            "old_qualification_alternative_candidate": f["old_qualification_alternative"],
            "old_equivalent_experience_candidate": f["old_equivalent_experience"],
            "old_qualification_relation_unresolved": f["old_unresolved"], "old_mixed_requirement_scope": f["old_mixed"],
            "old_context_conflict": f["old_context_conflict"],
            "old_audit_only_numeric_literal_candidate": f["old_audit_numeric"],
            "old_full_numeric_literal_projection_status": "not_projected_in_D67_use_D66_only_for_first5_scope",
            "metadata_status": "pending_targeted_projection", "metadata_source_status_at_freeze": shard["metadata_status_at_freeze"],
            "COMPANY_ID": None, "ONET_OCCUPATION_CODE": None,
            "CREATED": None, "STATE": None,
            "evidence_locator_status": "retained_in_hash_bound_current_evidence_and_old_v6_sources",
            "semantic_interpretation": "wording_candidates_or_unknown_not_gold",
        })
        for obj in OLD_OBJECTS:
            for measure in OLD_MEASURES: row["old_exp_%s_%s" % (obj, measure)] = f.get("old_exp_%s_%s" % (obj, measure))
        output_rows.append(row)
    output_root = Path(args.output_root); output_root.mkdir(parents=True, exist_ok=True)
    output = output_root / (shard_id + ".additive.parquet"); temp = Path(str(output) + ".tmp")
    table = pa.Table.from_pylist(output_rows)
    typed_nulls = {"old_occupation_task_broad": pa.bool_(), "old_occupation_task_main": pa.bool_(),
                   "COMPANY_ID": pa.string(), "ONET_OCCUPATION_CODE": pa.string(),
                   "CREATED": pa.timestamp("ms"), "STATE": pa.string()}
    for name, value_type in typed_nulls.items():
        position = table.schema.get_field_index(name)
        table = table.set_column(position, name, pa.nulls(table.num_rows, type=value_type))
    pq.write_table(table, temp, compression="zstd", row_group_size=32768); os.replace(temp, output)
    if pq.ParquetFile(output).metadata.num_rows != len(features): raise RuntimeError("output row conservation failed")
    atomic_json(output_root / (shard_id + ".additive.receipt.json"), {
        "version": VERSION, "status": "complete", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "shard_id": shard_id, "region": args.region, "source_file": shard["source_file"],
        "input_versions": {"runner_sha256": shard["runner_sha256"], "rule_engine_sha256": shard["rule_engine_sha256"],
                           "overlay_sha256": shard["overlay_sha256"], "old_narrow_version": shard["old_narrow_version"]},
        "inputs": {"posting_sha256": shard["posting_sha256"], "evidence_sha256": shard["evidence_sha256"],
                   "old_narrow_sha256": shard["old_narrow_sha256"], "old_v6_files": len(audit_paths),
                   "old_v6_transfer_manifest_sha256": sha256(args.old_v6_inventory)},
        "counts": {"current_rows": len(features), "current_evidence_rows": evidence_rows, "old_rows": old_rows,
                   "old_only_rows": old_only, "exact_old_matches": matches, "old_v6_audit_rows": audit_rows,
                   "metadata_verified_rows_at_projection": 0, "metadata_pending_rows_at_projection": len(features)},
        "checks": {"current_key_unique": True, "output_row_conservation": True,
                   "old_occupation_task_all_null_and_unavailable": True, "old_audit_nondetection_explicitly_not_semantic_absence": True,
                   "technology_groups_fixed_from_current_rules": True},
        "output": {"path": str(output), "rows": len(features), "bytes": output.stat().st_size, "sha256": sha256(output)},
        "source_evidence": {"current_path": evidence, "current_sha256": shard["evidence_sha256"],
                            "old_v6_root": str(Path(args.old_v6_root) / shard_id)},
        "scheduler": {"job_id": os.environ.get("SLURM_JOB_ID"), "array_task_id": os.environ.get("SLURM_ARRAY_TASK_ID"), "host": platform.node()},
        "api_calls": 0, "model_calls": 0, "full_text_reads": 0, "rules_changed": False,
        "claim_boundary": "candidate wording in frozen completed shards; no semantic accuracy, causal, seniority or authority claim",
    })


if __name__ == "__main__": main()
