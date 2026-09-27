#!/usr/bin/env python3
"""Create frozen 600-calibration/400-convention-sealed annotation packs.

Parser output is used only to allocate an explicitly flagged supplemental
component. Predictions never appear in labeler-facing text or templates.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import re
import runpy
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow.parquet as pq

TIME_ORDER = ["2015", "2016-17", "2018-19", "2020-22", "2023", "2024", "2025", "2026_partial"]


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    return sha_bytes(Path(path).read_bytes())


def rank(seed, *parts):
    return sha_bytes((seed + "\0" + "\0".join(map(str, parts))).encode())


def atomic_json(path, obj):
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n")
    os.replace(temp, path)


def normalize_text(text):
    text = "" if text is None else str(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\\n", "\n")
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def near_signature(normalized):
    # Conservative template signature: preserve words, mask long numerals and
    # common location tokens. It is only an audit/grouping aid, not semantic dedup.
    value = re.sub(r"\b\d{2,}\b", "#", normalized)
    value = re.sub(r"\b(?:street|st|avenue|ave|road|rd|boulevard|blvd|suite)\s+[a-z0-9-]+\b", "<address>", value)
    tokens = re.findall(r"[a-z]+|#", value)
    return sha_bytes(" ".join(tokens).encode())


def prediction_path(result):
    summary = result.get("summary", {})
    exp = summary.get("experience", {})
    edu = summary.get("education", {})
    complex_n = sum(int(x.get(k, 0) or 0) for x in (exp, edu)
                    for k in ("alternative_path_candidate_count", "qualification_relation_unresolved_count"))
    if complex_n or bool(edu.get("has_equivalent_experience_path")):
        return "predicted_complex"
    candidate = 0
    for module in ("experience", "education", "software", "ai"):
        item = summary.get(module, {})
        candidate += int(item.get("requirement_candidate_count", 0) or 0)
        candidate += int(item.get("applicant_qualification_candidate_count", 0) or 0)
    return "predicted_candidate" if candidate else "predicted_noncandidate"


def allocate(n, labels):
    weights = {"predicted_complex": 0.20, "predicted_candidate": 0.50, "predicted_noncandidate": 0.30}
    raw = {x: n * weights[x] for x in labels}
    out = {x: int(raw[x]) for x in labels}
    for x in sorted(labels, key=lambda z: (-(raw[z] - out[z]), z))[:n - sum(out.values())]:
        out[x] += 1
    return out


def write_jsonl(path, rows):
    with Path(str(path) + ".tmp").open("w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    os.replace(Path(str(path) + ".tmp"), path)


def public_row(row):
    return {"annotation_id": row["ANNOTATION_ID"], "raw_text": row["DESCRIPTION"]}


def annotation_row(row):
    return {
        "annotation_id": row["ANNOTATION_ID"], "annotator_id": "", "annotation_status": "unlabeled",
        "presence": "", "strength": "", "experience_object": "", "technology_class": "",
        "technology_role": "", "task_family": "", "binding_status": "", "relation": "",
        "duration_min_value": "", "duration_max_value": "", "duration_unit": "", "duration_bound_type": "",
        "clause_id": "", "object_span_id": "", "relation_group_id": "", "span_start": "", "span_end": "",
        "evidence_quote": "", "context": "", "uncertainty_reason": "", "reviewer_notes": "",
        "adjudication_status": "pending", "adjudicated_label": "",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--config", required=True)
    a = p.parse_args()
    cfg = json.loads(Path(a.config).read_text())
    out = Path(cfg["output_dir"])
    if out.exists():
        raise RuntimeError("immutable output directory already exists")
    out.mkdir(parents=True)
    (out / "calibration").mkdir()
    (out / "sealed_test").mkdir()
    rows = pq.read_table(cfg["candidate_pool"]).to_pylist()
    exclusions = json.loads(Path(cfg["exclusion_bundle"]).read_text())
    excluded_jobs, excluded_templates = set(exclusions["job_hashes"]), set(exclusions["normalized_text_sha256"])
    excluded_employers = set(exclusions["employer_ids"])
    parser_ns = runpy.run_path(cfg["parser_path"])
    extract = parser_ns["extract"]
    parser_normalize = parser_ns["_normalize"]
    audit = Counter()
    eligible = []
    for row in rows:
        audit["pool_rows"] += 1
        normalized = parser_normalize(row["DESCRIPTION"])
        template_sha = sha_bytes(normalized.encode())
        employer = None if row["RECORD_COMPANY_ID"] is None else str(row["RECORD_COMPANY_ID"])
        if row["JOB_HASH"] in excluded_jobs:
            audit["excluded_job_hash"] += 1
            continue
        if template_sha in excluded_templates:
            audit["excluded_exact_template"] += 1
            continue
        if employer in excluded_employers:
            audit["excluded_employer"] += 1
            continue
        result = extract(row["DESCRIPTION"])
        row.update({"RAW_TEXT_SHA256": sha_bytes((row["DESCRIPTION"] or "").encode()),
                    "NORMALIZED_TEXT_SHA256": template_sha, "NEAR_TEMPLATE_SIGNATURE": near_signature(normalized),
                    "EMPLOYER_KEY": employer or ("missing:" + row["JOB_HASH"]),
                    "PREDICTED_PATH": prediction_path(result)})
        eligible.append(row)
    # One representative per employer, exact template, and conservative near signature.
    deduped, seen_employer, seen_exact, seen_near = [], set(), set(), set()
    for row in sorted(eligible, key=lambda r: rank(cfg["seed"], "dedup", r["JOB_HASH"])):
        reason = None
        if row["EMPLOYER_KEY"] in seen_employer:
            reason = "same_employer"
        elif row["NORMALIZED_TEXT_SHA256"] in seen_exact:
            reason = "exact_template"
        elif row["NEAR_TEMPLATE_SIGNATURE"] in seen_near:
            reason = "conservative_near_signature"
        if reason:
            audit["dedup_" + reason] += 1
            continue
        seen_employer.add(row["EMPLOYER_KEY"])
        seen_exact.add(row["NORMALIZED_TEXT_SHA256"])
        seen_near.add(row["NEAR_TEMPLATE_SIGNATURE"])
        deduped.append(row)
    by_time = defaultdict(list)
    for row in deduped:
        by_time[row["TIME_STRATUM"]].append(row)
    selected = []
    strata_report = {}
    for period in TIME_ORDER:
        target = int(cfg["target_by_time"][period])
        supplemental_n = int(cfg["supplemental_by_time"][period])
        core_n = target - supplemental_n
        frame = sorted(by_time[period], key=lambda r: rank(cfg["seed"], "core", r["JOB_HASH"]))
        if len(frame) < target:
            raise RuntimeError("shortfall in %s: %d eligible groups for target %d" % (period, len(frame), target))
        core = frame[:core_n]
        core_ids = {r["JOB_HASH"] for r in core}
        remaining = [r for r in frame if r["JOB_HASH"] not in core_ids]
        allocation = allocate(supplemental_n, ["predicted_complex", "predicted_candidate", "predicted_noncandidate"])
        supplement = []
        path_report = {}
        for path_name, n in allocation.items():
            path_frame = sorted([r for r in remaining if r["PREDICTED_PATH"] == path_name],
                                key=lambda r: rank(cfg["seed"], "supplement", path_name, r["JOB_HASH"]))
            take = path_frame[:n]
            if len(take) < n:
                raise RuntimeError("supplement shortfall %s %s: %d < %d" % (period, path_name, len(take), n))
            for row in take:
                row["SELECTION_COMPONENT"] = "prediction_supplement"
                row["CORE_SELECTION_PROBABILITY_CONDITIONAL"] = None
                row["SUPPLEMENT_SELECTION_PROBABILITY_CONDITIONAL"] = n / len(path_frame)
            supplement.extend(take)
            path_report[path_name] = {"eligible_after_core": len(path_frame), "selected": n,
                                      "conditional_probability": n / len(path_frame)}
        for row in core:
            row["SELECTION_COMPONENT"] = "probability_core"
            row["CORE_SELECTION_PROBABILITY_CONDITIONAL"] = core_n / len(frame)
            row["SUPPLEMENT_SELECTION_PROBABILITY_CONDITIONAL"] = None
        chosen = core + supplement
        if len(chosen) != target:
            raise RuntimeError("period target mismatch")
        selected.extend(chosen)
        strata_report[period] = {"eligible_conservative_groups": len(frame), "target": target,
                                  "core_selected": core_n, "core_probability_conditional": core_n / len(frame),
                                  "supplement": path_report}
    if len(selected) != cfg["target_total"]:
        raise RuntimeError("total sample mismatch")
    # Unique employer rows make group-preserving 60/40 split exact. Stratify each period.
    calibration, test = [], []
    for period in TIME_ORDER:
        part = sorted([r for r in selected if r["TIME_STRATUM"] == period],
                      key=lambda r: rank(cfg["seed"], "split", r["EMPLOYER_KEY"]))
        cal_n = int(cfg["calibration_by_time"][period])
        calibration.extend(part[:cal_n])
        test.extend(part[cal_n:])
    if len(calibration) != 600 or len(test) != 400:
        raise RuntimeError("split size mismatch")
    # Assign opaque IDs only after split; IDs do not encode period or parser path.
    for split, prefix in ((calibration, "C"), (test, "T")):
        for i, row in enumerate(sorted(split, key=lambda r: rank(cfg["seed"], "id", r["JOB_HASH"])), 1):
            row["ANNOTATION_ID"] = "%s%04d" % (prefix, i)
    calibration = sorted(calibration, key=lambda r: r["ANNOTATION_ID"])
    test = sorted(test, key=lambda r: r["ANNOTATION_ID"])
    write_jsonl(out / "calibration/texts.jsonl", [public_row(r) for r in calibration])
    write_jsonl(out / "sealed_test/texts.jsonl", [public_row(r) for r in test])
    fields = list(annotation_row(calibration[0]).keys())
    for name, part in (("calibration", calibration), ("sealed_test", test)):
        temp = out / name / "annotations_blank.csv.tmp"
        with temp.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(annotation_row(r) for r in part)
        os.replace(temp, out / name / "annotations_blank.csv")
    private_fields = ["ANNOTATION_ID", "JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "SOURCE_ROW_GROUP",
                      "ROW_IN_GROUP", "RECORD_COMPANY_ID", "STATE", "CREATED", "TIME_STRATUM",
                      "RAW_TEXT_SHA256", "NORMALIZED_TEXT_SHA256", "NEAR_TEMPLATE_SIGNATURE",
                      "EMPLOYER_KEY", "SELECTION_COMPONENT", "CORE_SELECTION_PROBABILITY_CONDITIONAL",
                      "SUPPLEMENT_SELECTION_PROBABILITY_CONDITIONAL", "PREDICTED_PATH"]
    private_rows = []
    for split_name, part in (("calibration", calibration), ("sealed_test", test)):
        for row in part:
            item = {k: row.get(k) for k in private_fields}
            item["SPLIT"] = split_name
            private_rows.append(item)
    write_jsonl(out / "selection_metadata_private.jsonl", private_rows)
    grouping_report = {
        "algorithm": "one representative per observed Records.COMPANY_ID company-scrape key, exact V5-normalized SHA256, and conservative masked-token signature",
        "group_unit": "Records.COMPANY_ID is a company-scrape identifier; parent employer/subsidiary/site harmonization is unverified.",
        "algorithm_limit": "The masked signature catches some near-identical boilerplate with changed long numerals/simple addresses. It is a conservative approximation, not exhaustive near-duplicate or semantic similarity detection.",
        "residual_leakage": "Related parent/subsidiary/site entities with different company-scrape IDs and paraphrased/cross-employer templates may remain across splits.",
        "eligible_before_grouping": len(eligible), "eligible_after_grouping": len(deduped),
        "removals": {k: v for k, v in sorted(audit.items()) if k.startswith("dedup_")},
        "selected_unique_employers": len({r["EMPLOYER_KEY"] for r in selected}),
        "selected_unique_exact_templates": len({r["NORMALIZED_TEXT_SHA256"] for r in selected}),
        "selected_unique_near_signatures": len({r["NEAR_TEMPLATE_SIGNATURE"] for r in selected}),
        "cross_split_employer_overlap": len({r["EMPLOYER_KEY"] for r in calibration} & {r["EMPLOYER_KEY"] for r in test}),
        "cross_split_exact_template_overlap": len({r["NORMALIZED_TEXT_SHA256"] for r in calibration} & {r["NORMALIZED_TEXT_SHA256"] for r in test}),
        "cross_split_near_signature_overlap": len({r["NEAR_TEMPLATE_SIGNATURE"] for r in calibration} & {r["NEAR_TEMPLATE_SIGNATURE"] for r in test}),
        "quality_status": "algorithmic grouping audit only; no human duplicate-pair review completed",
    }
    atomic_json(out / "grouping_quality_report.json", grouping_report)
    coverage_report = {
        "time_counts": dict(sorted(Counter(r["TIME_STRATUM"] for r in selected).items())),
        "source_file_counts": dict(sorted(Counter(r["SOURCE_FILE"] for r in selected).items())),
        "source_files_represented": len({r["SOURCE_FILE"] for r in selected}),
        "selection_component_counts": dict(sorted(Counter(r["SELECTION_COMPONENT"] for r in selected).items())),
        "private_predicted_path_counts": dict(sorted(Counter(r["PREDICTED_PATH"] for r in selected).items())),
        "occupation_coverage_status": "not_measured_no_bounded_job_level_onet_index",
        "coverage_claim": "regional selected-shard annotation coverage only; no national/full-corpus prevalence claim",
    }
    atomic_json(out / "coverage_report.json", coverage_report)
    manifest = {
        "status": "annotation_pack_prepared_human_labels_pending", "target_total": len(selected),
        "calibration_rows": len(calibration), "sealed_test_rows": len(test),
        "human_labels_present": False, "automatic_release_allowed": False,
        "sealed_by_convention": True,
        "sealed_test_rule": "Do not inspect texts or run/inspect parser predictions until calibration changes are frozen. This is workflow separation, not cryptographic access control.",
        "sample_scope": cfg["scope_warning"], "time_strata": TIME_ORDER,
        "selection": strata_report, "exclusion_audit": dict(audit),
        "dedup_and_split_rule": "Exclude frozen prior cases/templates/company-scrape IDs; select at most one ad per observed Records.COMPANY_ID, exact normalized template, and conservative masked-token signature. Chosen observed IDs/signatures do not cross splits. Parent/subsidiary/site harmonization and exhaustive near-duplicate detection remain unverified.",
        "normalization_version": "recruitment-html-text-v5 (parser _normalize)",
        "parser_sha256": sha_file(cfg["parser_path"]),
        "near_group_algorithm": "V5 normalize; mask numerals with >=2 digits and simple street-address tokens; SHA256 exact signature; conservative approximation that may miss paraphrases and cross-entity templates",
        "prediction_use": "V5 predictions allocated only the flagged 200-row supplement. The 800-row core is prediction-independent. Predictions are private and absent from labeler-facing files.",
        "occupation_coverage": "Unavailable in this pack because no bounded job-level O*NET index was available; no national/occupation-representative claim is permitted.",
        "time_semantics": "Delivery snapshot text linked to Records.CREATED cohort; not verified historical point-in-time text.",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "files": {},
    }
    for rel in ["calibration/texts.jsonl", "calibration/annotations_blank.csv",
                "sealed_test/texts.jsonl", "sealed_test/annotations_blank.csv",
                "selection_metadata_private.jsonl", "grouping_quality_report.json", "coverage_report.json"]:
        manifest["files"][rel] = {"sha256": sha_file(out / rel), "bytes": (out / rel).stat().st_size}
    atomic_json(out / "sample_manifest.json", manifest)
    atomic_json(out / "PACK_COMPLETE", {"status": "complete", "manifest_sha256": sha_file(out / "sample_manifest.json")})
    print(json.dumps({"status": "complete", "calibration": len(calibration), "sealed_test": len(test),
                      "manifest_sha256": sha_file(out / "sample_manifest.json")}))


if __name__ == "__main__":
    main()
