#!/usr/bin/env python3
"""Independent D66 engineering QA over the completed private overlay/public tables."""
import argparse
import csv
import hashlib
import json
import math
import os

import pyarrow.parquet as pq


KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
OLD_MAP = {"general_work": "general_work", "tool": "specific_tool", "industry_domain": "industry_domain"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def rows(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def maybe_float(value):
    return None if value in (None, "") else float(value)


def close(a, b, tol=1e-12):
    if a is None or b is None:
        return a is None and b is None
    return math.isclose(a, b, rel_tol=tol, abs_tol=tol)


def truth(value):
    return value is True


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--private-overlay", required=True)
    p.add_argument("--public-dir", required=True)
    p.add_argument("--output", required=True)
    a = p.parse_args()

    needed = list(KEY) + [
        "current_processing_status", "old_match", "old_usable", "current_technology_group",
        "ONET_OCCUPATION_CODE", "official_occupation_status", "old_occupation_task_available",
        "old_occupation_task_broad", "old_occupation_task_main",
        "current_duty_context_restricted_responsibility_candidate", "evidence_locator_sidecar",
        "old_qualification_alternative_candidate", "old_equivalent_experience_candidate",
    ]
    for dim in ("general_work", "tool", "industry_domain", "occupation_task"):
        needed += ["current_%s_broad" % dim, "current_%s_main" % dim]
    for old in OLD_MAP.values():
        needed += ["old_exp_%s_broad" % old, "old_exp_%s_main" % old]
    table = pq.read_table(a.private_overlay, columns=needed)
    data = table.to_pylist()

    keys = [tuple(r[x] for x in KEY) for r in data]
    key_unique = len(keys) == len(set(keys)) == 424226 and all(all(x is not None for x in k) for k in keys)
    occupation_na = all(r["old_occupation_task_available"] is False and
                        r["old_occupation_task_broad"] is None and
                        r["old_occupation_task_main"] is None for r in data)
    unmatched_old_null = all(
        r["old_match"] is True or all(r["old_exp_%s_%s" % (obj, measure)] is None
                                      for obj in OLD_MAP.values() for measure in ("broad", "main"))
        for r in data
    )
    locator_names = {r["evidence_locator_sidecar"] for r in data}
    if len(locator_names) != 1:
        raise SystemExit("private overlay does not bind exactly one evidence locator sidecar")
    locator_path = os.path.join(os.path.dirname(a.private_overlay), next(iter(locator_names)))
    locator_cols = list(KEY) + ["source_version", "kind", "object_or_candidate", "uncertainty_json"]
    locator_rows = pq.read_table(locator_path, columns=locator_cols).to_pylist()
    locators = {}
    for item in locator_rows:
        locators.setdefault(tuple(item[x] for x in KEY), []).append(item)
    relevant_tasks = {"independent_responsibility", "client_ownership", "people_supervision"}
    duty_context_exact = True
    qualification_branches_exact = True
    for r in data:
        k = tuple(r[x] for x in KEY)
        evidence = locators.get(k, [])
        expected_duty = False
        for e in evidence:
            uncertainty = json.loads(e["uncertainty_json"] or "{}")
            if (e["source_version"] == "current_rulefirst_evidence" and e["kind"] == "task" and
                    e["object_or_candidate"] in relevant_tasks and uncertainty.get("section") == "duties" and
                    uncertainty.get("candidate_heading_scope") == "duties"):
                expected_duty = True
        duty_context_exact &= truth(r["current_duty_context_restricted_responsibility_candidate"]) == expected_duty
        audit_uncertainty = [json.loads(e["uncertainty_json"] or "{}") for e in evidence
                             if e["source_version"] == "old_typed_v6_audit"]
        broad = any(e.get("EQUIVALENT_CREDENTIAL") is True or
                    e.get("ALTERNATIVE_TRAINING_OR_EXPERIENCE") is True or
                    e.get("ALTERNATIVE_TRAINING_OR_EDUCATION") is True for e in audit_uncertainty)
        equivalent_experience = any(e.get("EQUIVALENT_EXPERIENCE") is True for e in audit_uncertainty)
        qualification_branches_exact &= (truth(r["old_qualification_alternative_candidate"]) == broad and
                                         truth(r["old_equivalent_experience_candidate"]) == equivalent_experience)

    support_rows = rows(os.path.join(a.public_dir, "COMMON_SUPPORT_PUBLIC.csv"))
    core_rows = rows(os.path.join(a.public_dir, "CORE_EXPERIENCE_COMPARISON_PUBLIC.csv"))
    support_by_pop = {r["population"]: r for r in support_rows}
    expected_pops = {"old_matched_current_processed", "old_usable_current_processed"}
    arithmetic_errors = []
    support_signatures = {}

    for pop in sorted(expected_pops):
        selected = [r for r in data if r["current_processing_status"] == "processed" and r["old_match"] is True
                    and (pop == "old_matched_current_processed" or r["old_usable"] is True)]
        by_occ = {}
        valid = {"software_only": 0, "any_ai": 0}
        for r in selected:
            if r["official_occupation_status"] != "official_code" or not r["ONET_OCCUPATION_CODE"]:
                continue
            group = r["current_technology_group"]
            arm = "software_only" if group == "software_only" else "any_ai" if group in ("ai_only", "software_and_ai") else None
            if arm is None:
                continue
            valid[arm] += 1
            by_occ.setdefault(r["ONET_OCCUPATION_CODE"], {"software_only": [], "any_ai": []})[arm].append(r)
        kept = {o: cell for o, cell in by_occ.items()
                if len(cell["software_only"]) >= 20 and len(cell["any_ai"]) >= 20}
        weights = {o: min(len(cell["software_only"]), len(cell["any_ai"])) for o, cell in kept.items()}
        total_weight = sum(weights.values())
        retained = {arm: sum(len(cell[arm]) for cell in kept.values()) for arm in valid}
        support_signatures[pop] = (tuple(sorted(weights.items())), total_weight)

        sr = support_by_pop.get(pop)
        if sr is None:
            arithmetic_errors.append(pop + ": missing support row")
        else:
            exact = {
                "population_n": len(selected), "occupation_threshold_each_arm": 20,
                "eligible_occupation_count": len(kept),
                "software_only_valid_occupation_n": valid["software_only"],
                "any_ai_valid_occupation_n": valid["any_ai"],
                "software_only_retained_n": retained["software_only"],
                "any_ai_retained_n": retained["any_ai"], "total_min_count_weight": total_weight,
            }
            for field, expected in exact.items():
                if int(sr[field]) != expected:
                    arithmetic_errors.append("%s %s" % (pop, field))
            if total_weight and not close(maybe_float(sr["weight_check_sum"]), 1.0):
                arithmetic_errors.append(pop + " weight_check_sum")

        pop_core = [r for r in core_rows if r["population"] == pop]
        if len(pop_core) != 16:
            arithmetic_errors.append(pop + ": expected 16 core rows")
        for out in pop_core:
            dim, version, measure = out["dimension"], out["measurement_version"], out["measure"]
            if version == "old" and dim == "occupation_task":
                if out["status"] != "unavailable_old_occupation_task_unmeasured" or any(
                    out[x] not in ("", None) for x in ("software_only_raw_common_support_rate",
                    "software_only_standardized_rate", "any_ai_raw_common_support_rate",
                    "any_ai_standardized_rate", "difference_any_ai_minus_software_percentage_points")):
                    arithmetic_errors.append(pop + ": old occupation_task not NA")
                continue
            rates = {}
            for arm in ("software_only", "any_ai"):
                vals = []
                weighted = 0.0
                for occ, cell in kept.items():
                    if version == "old":
                        col = "old_exp_%s_%s" % (OLD_MAP[dim], measure)
                    else:
                        col = "current_%s_%s" % (dim, measure)
                    cell_vals = [truth(r[col]) for r in cell[arm]]
                    vals.extend(cell_vals)
                    weighted += (weights[occ] / total_weight) * (sum(cell_vals) / len(cell_vals)) if total_weight else 0.0
                raw = sum(vals) / len(vals) if vals else None
                std = weighted if total_weight else None
                rates[arm] = std
                if not close(maybe_float(out[arm + "_raw_common_support_rate"]), raw):
                    arithmetic_errors.append("%s %s %s %s raw" % (pop, dim, version, arm))
                if not close(maybe_float(out[arm + "_standardized_rate"]), std):
                    arithmetic_errors.append("%s %s %s %s standardized" % (pop, dim, version, arm))
            diff = (rates["any_ai"] - rates["software_only"]) * 100 if rates["software_only"] is not None else None
            if not close(maybe_float(out["difference_any_ai_minus_software_percentage_points"]), diff):
                arithmetic_errors.append("%s %s %s difference" % (pop, dim, version))

    versions_ok = {r["measurement_version"] for r in core_rows} == {"old", "current"} and all(
        r["technology_group_source"] == "fixed_current_rule_v1_2_nonnegated_lexical_group" and
        r["weight_basis"] == "min(software_only_n,any_ai_n)_normalized" for r in core_rows)
    field_rows = rows(os.path.join(a.public_dir, "FIELD_REUSE_MAP_PUBLIC.csv"))
    wording = " ".join(" ".join(r.values()) for r in field_rows)
    wording_ok = all(x in wording for x in ("old_NA", "must_not_fill_zero", "no fabricated universal minimum",
                                             "no row means not detected", "not degree-or-experience certification"))
    entry_markers = {r["entry_marker"] for r in rows(os.path.join(a.public_dir, "ENTRY_RESPONSIBILITY_COOCCURRENCE_PUBLIC.csv"))}
    invalid_old_unconditional_absent = "old_explicit_noexperience_unconditional_candidate" not in entry_markers

    receipt_path = os.path.join(a.public_dir, "RUN_RECEIPT_PUBLIC.json")
    receipt = json.load(open(receipt_path, encoding="utf-8"))
    hashes_ok = (receipt["private_output"]["sha256"] == sha256(a.private_overlay) and
        receipt["private_evidence_locator_output"]["sha256"] == sha256(locator_path) and all(
        sha256(os.path.join(a.public_dir, name)) == item["sha256"]
        for name, item in receipt["public_outputs"].items()))
    receipt_words = receipt.get("claim_boundary", "") + " " + " ".join(json.load(open(
        os.path.join(a.public_dir, "SUMMARY_PUBLIC.json"), encoding="utf-8")).get("limits", []))
    claim_ok = all(x in receipt_words for x in ("wording candidates", "old occupation/task experience is unmeasured",
                                                 "no-hit means not observed"))

    checks = {
        "key_unique_and_424226_row_conservation": key_unique,
        "unmatched_old_measures_remain_null": unmatched_old_null,
        "old_occupation_task_is_NA_never_zero": occupation_na and not any("old occupation_task not NA" in x for x in arithmetic_errors),
        "common_support_and_weight_arithmetic_recomputed": not arithmetic_errors,
        "old_current_versions_and_fixed_group_labeled": versions_ok,
        "duty_context_uses_only_named_responsibility_families": duty_context_exact,
        "qualification_alternative_and_equivalent_experience_are_separate": qualification_branches_exact,
        "invalid_old_unconditional_noexperience_marker_not_published": invalid_old_unconditional_absent,
        "units_and_claim_wording_bounded": wording_ok and claim_ok,
        "output_hash_bindings": hashes_ok,
    }
    result = {
        "version": "d66-reuse-overlap-independent-qa-v1",
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "arithmetic_errors": arithmetic_errors[:50],
        "private_rows": len(data),
        "scope": "Independent engineering QA only; recomputes key/NA/common-support arithmetic from the completed overlay and does not validate semantics.",
    }
    os.makedirs(os.path.dirname(a.output), exist_ok=True)
    tmp = a.output + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True); f.write("\n")
    os.replace(tmp, a.output)
    if result["status"] != "pass":
        raise SystemExit("independent QA failed: " + json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
