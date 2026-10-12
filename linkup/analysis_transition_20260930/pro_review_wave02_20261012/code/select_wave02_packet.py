#!/usr/bin/env python3
"""Count D67 comparison strata and select a bounded KS13 Pro-review packet.

This reuses frozen row-level outputs.  It does not run a parser, classifier, or
model.  Selection is purposeful and is not an accuracy sample.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import heapq
import json
import math
import os
import platform
from pathlib import Path

import pyarrow.parquet as pq
from legacy_v5_frozen import _normalize_with_flags

KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
ARMS = ("software_only", "any_ai")
DIMS = ("general_work", "tool", "industry_domain", "occupation_task")
VERSION = "pro-wave02-ks13-purposeful-v1"
SEED = "pro-wave02-20261012-fixed"
QUOTAS = {
    "experience": {
        "experience_unresolved": 10,
        "conditional_or_alternative": 6,
        "clear_rule_candidate": 8,
        "no_rule_candidate": 6,
    },
    "entry_responsibility": {
        "entry_and_responsibility": 6,
        "entry_only": 4,
        "responsibility_only": 4,
        "neither_rule_candidate": 4,
    },
}


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def key(row):
    return tuple(row[x] for x in KEY)


def batches(path, columns):
    pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=32768, columns=columns):
        data = batch.to_pydict()
        for i in range(batch.num_rows):
            yield {name: data[name][i] for name in data}


def arm(value):
    if value == "software_only":
        return value
    if value in ("ai_only", "software_and_ai"):
        return "any_ai"
    return None


def atomic_json(path, value):
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n")
    os.replace(temp, path)


def atomic_jsonl(path, values):
    temp = Path(str(path) + ".tmp")
    with open(temp, "w", encoding="utf-8") as f:
        for value in values:
            f.write(json.dumps(value, sort_keys=True, ensure_ascii=False) + "\n")
    os.replace(temp, path)


def write_csv(path, values):
    if not values:
        raise RuntimeError("refusing empty table " + str(path))
    temp = Path(str(path) + ".tmp")
    with open(temp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(values[0]))
        w.writeheader(); w.writerows(values)
    os.replace(temp, path)


def load_hashes(path):
    result = set()
    if not path:
        return result
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            value = row.get("exact_text_sha256") or row.get("source_text_sha256")
            if value:
                result.add(value)
    return result


def rank(candidate):
    raw = SEED + "|" + candidate["question_group"] + "|" + candidate["selection_stratum"] + "|" + "|".join(map(str, candidate["canonical_key"]))
    return hashlib.sha256(raw.encode()).hexdigest()


def retain(pool, bucket, candidate, limit=80):
    score = int(rank(candidate), 16)
    heap = pool[bucket]
    item = (-score, rank(candidate), candidate)
    if len(heap) < limit:
        heapq.heappush(heap, item)
    elif item > heap[0]:
        heapq.heapreplace(heap, item)


def feature_summary(row):
    if row is None:
        return {"required": False, "preferred": False, "mixed": False,
                "strength_unknown": False, "outcome_unknown": False}
    return {
        "required": any(row.get("current_%s_required_any_scope" % d) is True for d in DIMS),
        "preferred": any(row.get("current_%s_preferred_any_scope" % d) is True for d in DIMS),
        "mixed": any(row.get("current_%s_mixed_any_scope" % d) is True for d in DIMS),
        "strength_unknown": any(row.get("current_%s_strength_unknown" % d) is True for d in DIMS),
        "outcome_unknown": any(row.get("current_%s_outcome_unknown" % d) is True for d in DIMS),
    }


def selected_evidence(row):
    return {name: row.get(name) for name in (
        "evidence_index", "kind", "rule", "start", "end", "quote", "section",
        "coordinate_system", "objects_json", "strength", "scope", "duration_kind",
        "lower_years", "upper_years", "strict_lower", "outcome_status",
        "review_reasons_json", "technology", "role_cue", "negated", "task_family",
        "overlay_annotations_json", "candidate_heading_scope", "heading_scope_status",
        "d57_current_duty_mentoring_candidate",
        "mentoring_referent_or_prior_experience_marker")}


def extract_raw_text(raw_path, source_rows):
    """Read only row groups containing selected SOURCE_ROW positions."""
    pf = pq.ParquetFile(raw_path)
    wanted = sorted(set(source_rows))
    if not wanted:
        return {}
    if wanted[0] < 0 or wanted[-1] >= pf.metadata.num_rows:
        raise RuntimeError("selected SOURCE_ROW outside raw parquet " + raw_path)
    starts = []
    pos = 0
    for rg in range(pf.num_row_groups):
        n = pf.metadata.row_group(rg).num_rows
        starts.append((pos, pos + n, rg)); pos += n
    result = {}
    by_rg = collections.defaultdict(list)
    for idx in wanted:
        for lo, hi, rg in starts:
            if lo <= idx < hi:
                by_rg[rg].append((idx, idx - lo)); break
    for rg, requests in by_rg.items():
        table = pf.read_row_group(rg, columns=["DESCRIPTION", "JOB_HASH"])
        desc = table.column("DESCRIPTION").to_pylist(); hashes = table.column("JOB_HASH").to_pylist()
        for absolute, local in requests:
            result[absolute] = {"original_text": desc[local], "raw_job_hash": hashes[local]}
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--global-manifest", required=True)
    p.add_argument("--frozen-manifest", required=True)
    p.add_argument("--closing-root", required=True)
    p.add_argument("--raw-root", required=True)
    p.add_argument("--exclude-eval80", required=True)
    p.add_argument("--exclude-prior", required=True)
    p.add_argument("--private-output", required=True)
    p.add_argument("--public-output", required=True)
    a = p.parse_args()
    gm = json.load(open(a.global_manifest)); frozen = json.load(open(a.frozen_manifest))
    if gm.get("status") != "complete" or gm.get("rows") != 5804936 or len(gm.get("shards", [])) != 69:
        raise RuntimeError("D67 global manifest gate")
    frozen_by_id = {x["shard_id"]: x for x in frozen["shards"]}
    if len(frozen_by_id) != 69:
        raise RuntimeError("D67 frozen manifest gate")
    ks_items = [x for x in gm["shards"] if x["region"] == "kunshan"]
    if len(ks_items) != 13 or sum(x["rows"] for x in ks_items) != 1097202:
        raise RuntimeError("KS13 frozen subset gate")

    excluded_eval = load_hashes(a.exclude_eval80)
    excluded_prior = load_hashes(a.exclude_prior)
    if len(excluded_eval) != 80:
        raise RuntimeError("locked eval80 exclusion does not have 80 unique hashes")

    enriched_columns = list(KEY) + [
        "current_processing_status", "old_usable", "current_technology_group",
        "ONET_OCCUPATION_CODE", "official_occupation_status",
        "current_general_work_broad", "current_tool_broad", "current_industry_domain_broad",
        "current_occupation_task_broad", "current_numeric_literal_candidate",
        "current_conditional_or_alternative_candidate", "current_experience_unknown",
        "current_explicit_noexperience_candidate",
        "current_explicit_noexperience_unconditional_candidate",
        "current_graduate_wording_candidate", "current_independent_responsibility_wording",
        "current_client_ownership_wording", "current_people_supervision_wording",
        "current_d57_duty_mentoring_candidate", "current_strict_duty_responsibility_candidate"]

    # Recreate the published full-69 occupation support and min-count weights.
    global_cells = collections.Counter(); ks_cells = collections.Counter()
    for item in gm["shards"]:
        if sha(item["enriched_path"]) != item["enriched_sha256"]:
            raise RuntimeError("enriched SHA mismatch " + item["shard_id"])
        n = 0
        for row in batches(item["enriched_path"], ["current_processing_status", "old_usable",
                                                   "current_technology_group", "ONET_OCCUPATION_CODE",
                                                   "official_occupation_status"]):
            n += 1
            ar = arm(row["current_technology_group"])
            if (row["current_processing_status"] == "processed" and row["old_usable"] is True and ar and
                    row["official_occupation_status"] == "official_code" and row["ONET_OCCUPATION_CODE"]):
                global_cells[(row["ONET_OCCUPATION_CODE"], ar)] += 1
                if item["region"] == "kunshan":
                    ks_cells[(row["ONET_OCCUPATION_CODE"], ar)] += 1
        if n != item["rows"]:
            raise RuntimeError("enriched row mismatch " + item["shard_id"])
    full_support = {o for o, ar in global_cells if all(global_cells[(o, x)] >= 20 for x in ARMS)}
    if len(full_support) != 332:
        raise RuntimeError("published 332 occupation support not reproduced")
    full_weights = {o: min(global_cells[(o, x)] for x in ARMS) for o in full_support}
    if sum(full_weights.values()) != 103820:
        raise RuntimeError("published min-count weights not reproduced")
    local_support = {o for o in full_support if all(ks_cells[(o, x)] > 0 for x in ARMS)}
    local_weight_sum = sum(full_weights[o] for o in local_support)
    if not local_support or not local_weight_sum:
        raise RuntimeError("no local both-arm occupation support")

    feature_names = []
    for dim in DIMS:
        for strength in ("required", "preferred", "mixed"):
            feature_names.append("current_%s_%s_any_scope" % (dim, strength))
        feature_names += ["current_%s_strength_unknown" % dim, "current_%s_outcome_unknown" % dim]
    feature_columns = list(KEY) + feature_names
    evidence_columns = list(KEY) + [
        "evidence_index", "kind", "rule", "start", "end", "quote", "section",
        "coordinate_system", "objects_json", "strength", "scope", "duration_kind",
        "lower_years", "upper_years", "strict_lower", "outcome_status",
        "review_reasons_json", "technology", "role_cue", "negated", "task_family",
        "overlay_annotations_json", "candidate_heading_scope", "heading_scope_status",
        "d57_current_duty_mentoring_candidate",
        "mentoring_referent_or_prior_experience_marker"]
    posting_columns = list(KEY) + ["source_text_sha256", "normalized_text_sha256", "normalization",
                                   "coordinate_system", "rule_version", "overlay_version", "processing_status"]

    counts = collections.Counter(); occ_counts = collections.Counter(); pool = collections.defaultdict(list)
    scanned = collections.Counter()
    for item in ks_items:
        sid = item["shard_id"]; shard = frozen_by_id[sid]
        if shard["region"] != "kunshan" or shard["status"] != "complete" or shard["qa_status"] != "pass":
            raise RuntimeError("unaccepted KS shard " + sid)
        if sha(shard["posting"]) != shard["posting_sha256"] or sha(shard["evidence"]) != shard["evidence_sha256"]:
            raise RuntimeError("posting/evidence SHA mismatch " + sid)
        feature_path = Path(a.closing_root) / (sid + ".strength_features.parquet")
        receipt_path = Path(a.closing_root) / (sid + ".closing.receipt.json")
        receipt = json.load(open(receipt_path))
        if receipt.get("status") != "complete" or receipt["outputs"]["strength_features"]["sha256"] != sha(feature_path):
            raise RuntimeError("closing feature gate " + sid)
        postings = {}
        for row in batches(shard["posting"], posting_columns):
            k = key(row)
            if k in postings: raise RuntimeError("duplicate posting key " + sid)
            postings[k] = row
        features = {}
        for row in batches(feature_path, feature_columns):
            k = key(row)
            if k in features: raise RuntimeError("duplicate feature key " + sid)
            features[k] = row
        evidence = collections.defaultdict(list)
        for row in batches(shard["evidence"], evidence_columns):
            scanned["evidence_rows"] += 1
            if row["kind"] in ("experience", "task"):
                evidence[key(row)].append(selected_evidence(row))
        if scanned["evidence_rows"] > sum(x["evidence_rows"] for x in frozen["shards"] if x["region"] == "kunshan"):
            raise RuntimeError("evidence denominator exceeded")
        n = 0
        for row in batches(item["enriched_path"], enriched_columns):
            n += 1; k = key(row); post = postings.pop(k, None)
            if post is None: raise RuntimeError("posting join missing " + sid)
            ar = arm(row["current_technology_group"]); occ = row["ONET_OCCUPATION_CODE"]
            if not (row["current_processing_status"] == "processed" and row["old_usable"] is True and ar and
                    row["official_occupation_status"] == "official_code" and occ in local_support):
                continue
            scanned["eligible_ks_ads"] += 1
            ev = evidence.get(k, []); exp_ev = [x for x in ev if x["kind"] == "experience"]
            task_ev = [x for x in ev if x["kind"] == "task"]
            fsum = feature_summary(features.get(k))
            broad = any(row["current_%s_broad" % d] is True for d in DIMS)
            # Keep the purposeful strata mutually exclusive.  Conditionality is
            # a separate question from strength/outcome uncertainty, so assign
            # it first and leave the remaining uncertainty in its own stratum.
            if row["current_conditional_or_alternative_candidate"] is True:
                estratum = "conditional_or_alternative"
            elif row["current_experience_unknown"] is True or fsum["outcome_unknown"] or fsum["strength_unknown"]:
                estratum = "experience_unresolved"
            elif broad or exp_ev:
                estratum = "clear_rule_candidate"
            else:
                estratum = "no_rule_candidate"
            entry = (row["current_explicit_noexperience_candidate"] is True or
                     row["current_graduate_wording_candidate"] is True)
            responsibility = any(row[x] is True for x in (
                "current_independent_responsibility_wording", "current_client_ownership_wording",
                "current_people_supervision_wording", "current_d57_duty_mentoring_candidate"))
            if entry and responsibility: rstratum = "entry_and_responsibility"
            elif entry: rstratum = "entry_only"
            elif responsibility: rstratum = "responsibility_only"
            else: rstratum = "neither_rule_candidate"
            base = {
                "canonical_key": list(k), "shard_id": sid, "source_file": item["source_file"],
                "source_text_sha256": post["source_text_sha256"],
                "normalized_text_sha256": post["normalized_text_sha256"],
                "posting_provenance": {x: post[x] for x in ("normalization", "coordinate_system", "rule_version", "overlay_version", "processing_status")},
                "technology_arm": ar, "occupation_code": occ,
                "full69_fixed_min_count_weight": full_weights[occ],
                "baseline_flags": {x: row[x] for x in enriched_columns if x.startswith("current_")},
                "strength_summary": fsum,
            }
            counts[("experience", ar, estratum)] += 1
            occ_counts[("experience", ar, estratum, occ)] += 1
            c = dict(base, question_group="experience", selection_stratum=estratum,
                     review_scope=["experience_object", "requirement_strength", "conditional_scope"],
                     evidence=exp_ev,
                     absence_review_status=("unknown_requires_full_text" if estratum == "no_rule_candidate" else "not_an_absence_claim"))
            if post["source_text_sha256"] not in excluded_eval | excluded_prior:
                retain(pool, ("experience", ar, estratum), c)
            counts[("entry_responsibility", ar, rstratum)] += 1
            occ_counts[("entry_responsibility", ar, rstratum, occ)] += 1
            c = dict(base, question_group="entry_responsibility", selection_stratum=rstratum,
                     review_scope=["explicit_entry_target", "responsibility_subject_and_dimension"],
                     evidence=exp_ev + task_ev,
                     absence_review_status=("unknown_requires_full_text" if rstratum == "neither_rule_candidate" else "not_an_absence_claim"))
            if post["source_text_sha256"] not in excluded_eval | excluded_prior:
                retain(pool, ("entry_responsibility", ar, rstratum), c)
        if n != item["rows"] or postings:
            raise RuntimeError("KS posting/enriched conservation failed " + sid)

    expected_evidence = sum(x["evidence_rows"] for x in frozen["shards"] if x["region"] == "kunshan")
    if scanned["evidence_rows"] != expected_evidence:
        raise RuntimeError("KS evidence row conservation failed")

    # Greedy deterministic selection with source-text uniqueness and diversity caps.
    selected = []; used_hash = set(); occ_n = collections.Counter(); shard_n = collections.Counter()
    for ar in ARMS:
        for group in ("experience", "entry_responsibility"):
            for stratum, quota in QUOTAS[group].items():
                candidates = [x[2] for x in sorted(pool[(group, ar, stratum)], key=lambda z: z[1])]
                taken = 0
                for cap_occ, cap_shard in ((2, 12), (3, 16), (5, 24)):
                    for c in candidates:
                        h = c["source_text_sha256"]
                        if h in used_hash or occ_n[c["occupation_code"]] >= cap_occ or shard_n[c["shard_id"]] >= cap_shard:
                            continue
                        c["selection_rank_sha256"] = rank(c); selected.append(c); used_hash.add(h)
                        occ_n[c["occupation_code"]] += 1; shard_n[c["shard_id"]] += 1; taken += 1
                        if taken == quota: break
                    if taken == quota: break
                if taken != quota:
                    raise RuntimeError("quota unavailable %s %s %s %s/%s" % (group, ar, stratum, taken, quota))
    if len(selected) != 96 or len(used_hash) != 96:
        raise RuntimeError("selection must contain 96 unique source contexts")

    # Bounded raw retrieval: read only row groups containing the 96 selected SOURCE_ROW values.
    by_source = collections.defaultdict(list)
    for c in selected: by_source[c["source_file"]].append(c)
    raw_files = []
    for source_file, candidates in by_source.items():
        raw_path = str(Path(a.raw_root) / source_file)
        texts = extract_raw_text(raw_path, [int(c["canonical_key"][2]) for c in candidates])
        raw_files.append({"source_file": source_file, "path": raw_path, "selected_rows": len(candidates)})
        for c in candidates:
            record = texts[int(c["canonical_key"][2])]
            if record["raw_job_hash"] != c["canonical_key"][0]:
                raise RuntimeError("raw JOB_HASH mismatch")
            text = record["original_text"]
            text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if text_sha != c["source_text_sha256"]:
                raise RuntimeError("raw exact text SHA mismatch")
            normalized, normalization_flags = _normalize_with_flags(text)
            if hashlib.sha256(normalized.encode("utf-8")).hexdigest() != c["normalized_text_sha256"]:
                raise RuntimeError("frozen normalized text SHA mismatch")
            c["original_text"] = text
            c["review_text"] = normalized
            c["normalization_flags"] = normalization_flags
            c["full_text_verified"] = True
            c["review_instruction"] = "Answer ad-level no only after reviewing this complete text and all supplied target evidence; keep unknown when scope or subject remains unresolved."
            for e in c["evidence"]:
                start, end = e["start"], e["end"]
                if not isinstance(start, int) or not isinstance(end, int) or normalized[start:end] != e["quote"]:
                    raise RuntimeError("evidence Unicode slice mismatch")

    selected.sort(key=lambda x: (ARMS.index(x["technology_arm"]), x["question_group"], x["selection_stratum"], x["selection_rank_sha256"]))
    for i, c in enumerate(selected, 1): c["selection_index_1based"] = i

    private_out = Path(a.private_output); public_out = Path(a.public_output)
    private_out.mkdir(parents=True, exist_ok=True); public_out.mkdir(parents=True, exist_ok=True)
    packet = private_out / "WAVE02_ACTUAL96_PACKET_PRIVATE.jsonl"
    atomic_jsonl(packet, selected)
    selection_manifest = private_out / "WAVE02_SELECTION_MANIFEST_PRIVATE.json"
    atomic_json(selection_manifest, {"version": VERSION, "status": "complete", "records": 96,
        "distinct_source_text_sha256": len(used_hash), "excluded_eval80_hashes": len(excluded_eval),
        "excluded_prior_hashes": len(excluded_prior), "packet_sha256": sha(packet),
        "raw_files": raw_files})

    count_rows = []
    for group in ("experience", "entry_responsibility"):
        for ar in ARMS:
            den = sum(ks_cells[(o, ar)] for o in local_support)
            for stratum in QUOTAS[group]:
                num = counts[(group, ar, stratum)]
                std = sum((full_weights[o] / local_weight_sum) *
                          occ_counts[(group, ar, stratum, o)] / ks_cells[(o, ar)]
                          for o in local_support)
                count_rows.append({"scope": "KS13_old_usable_processed_local_both_arm_support",
                    "question_group": group, "technology_arm": ar, "stratum": stratum,
                    "numerator_ads": num, "denominator_ads": den, "raw_rate": num / den if den else "NA",
                    "standardized_rate": std,
                    "interpretation": "rule-field mass; unknown/no-rule is not unusable or semantic absence"})
    write_csv(public_out / "KS13_FIELD_SPECIFIC_COUNTS_PUBLIC.csv", count_rows)
    support_rows = [{"scope": "full69_published_support", "eligible_occupations": len(full_support),
        "total_min_count_weight": sum(full_weights.values()), "software_only_ads": sum(global_cells[(o,"software_only")] for o in full_support),
        "any_ai_ads": sum(global_cells[(o,"any_ai")] for o in full_support), "note": "published D67 baseline; not the KS13 review subset"},
        {"scope": "KS13_local_both_arm_subset", "eligible_occupations": len(local_support),
        "total_min_count_weight": local_weight_sum, "software_only_ads": sum(ks_cells[(o,"software_only")] for o in local_support),
        "any_ai_ads": sum(ks_cells[(o,"any_ai")] for o in local_support),
        "note": "full69 fixed occupation weights restricted to occupations present in both KS arms and renormalized once"},
        {"scope": "KS13_absent_from_one_or_both_arms", "eligible_occupations": len(full_support-local_support),
        "total_min_count_weight": sum(full_weights[o] for o in full_support-local_support),
        "software_only_ads": sum(ks_cells[(o,"software_only")] for o in full_support-local_support),
        "any_ai_ads": sum(ks_cells[(o,"any_ai")] for o in full_support-local_support),
        "note": "absent support cells reported as absent, never zero outcomes"}]
    write_csv(public_out / "SUPPORT_SCOPE_PUBLIC.csv", support_rows)
    quota_rows = []
    for ar in ARMS:
        for group in QUOTAS:
            for stratum, q in QUOTAS[group].items():
                quota_rows.append({"technology_arm": ar, "question_group": group, "selection_stratum": stratum,
                    "available_ads": counts[(group, ar, stratum)], "selected_contexts": q,
                    "design": "purposeful_balanced_not_population_accuracy"})
    write_csv(public_out / "SELECTION_QUOTAS_PUBLIC.csv", quota_rows)
    receipt = {"version": VERSION, "status": "pass", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scheduler": {"job_id": os.environ.get("SLURM_JOB_ID"), "host": platform.node()},
        "scope": {"region": "kunshan", "shards": 13, "frozen_rows": 1097202,
                  "eligible_support": "full69 332 support restricted to occupations with both KS arms",
                  "purposeful_review_contexts": 96},
        "checks": {"global_manifest_69": True, "full69_rows": True, "ks13_rows": True,
                   "published_332_support_reproduced": True, "published_weight_sum_reproduced": True,
                   "posting_evidence_sha": True, "canonical_join_conservation": True,
                   "locked_eval80_excluded": True, "prior_review_hashes_excluded": True,
                   "source_text_unique": True, "full_text_sha_and_job_hash": True,
                   "evidence_unicode_slices": True},
        "method": "rule-only frozen-field counting and purposeful selection; no model/API/CLI inference",
        "claim_boundary": "KS13 actual comparison subset; selection is not an accuracy sample and is not the 5.8m full69 estimate",
        "outputs": {"WAVE02_ACTUAL96_PACKET_PRIVATE.jsonl": {"path": str(packet), "rows": 96, "sha256": sha(packet)},
                    "WAVE02_SELECTION_MANIFEST_PRIVATE.json": {"path": str(selection_manifest), "sha256": sha(selection_manifest)},
                    **{name: {"sha256": sha(public_out/name), "bytes": (public_out/name).stat().st_size}
                       for name in ("KS13_FIELD_SPECIFIC_COUNTS_PUBLIC.csv", "SUPPORT_SCOPE_PUBLIC.csv", "SELECTION_QUOTAS_PUBLIC.csv")}},
        "unresolved_policy": "unknown/no-rule is not semantic absence or an unusable ad; before/after can change only exact reviewed rows"}
    atomic_json(public_out / "RUN_RECEIPT_PUBLIC.json", receipt)


if __name__ == "__main__":
    main()
