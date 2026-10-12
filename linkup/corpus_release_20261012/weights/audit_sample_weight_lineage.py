#!/usr/bin/env python3
"""Audit existing fixed10k probability metadata without producing estimates.

Private record keys and text never leave the process.  The output contains only
aggregate counts, numerical tolerances, source hashes, and design decisions.
"""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path

import pyarrow.parquet as pq

KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
CELL = ("OCCUPATION_MAJOR", "CENSUS_REGION", "created_year", "arm")
EXPECTED_ARMS = {"A": 4000, "B": 4000, "C": 2000}
EXPECTED_PARENT = {"A": 10075, "B": 1064428, "C": 83070}
TOL = 1e-8


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temp, path)


def canonical(row):
    return tuple(str(row[name]) for name in KEY)


def load_allocation(path):
    result = {}
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            key = (str(row["OCCUPATION_MAJOR"]), row["CENSUS_REGION"], str(int(row["created_year"])), row["arm"])
            if key in result:
                raise RuntimeError("duplicate allocation cell: " + repr(key))
            result[key] = {
                "N": int(row["frame_cell_arm_N"]),
                "n": int(row["selected_cell_arm_n"]),
                "original_pi": float(row["original_inclusion_probability"]),
                "conditional_pi": float(row["conditional_inclusion_probability"]),
                "total_pi": float(row["total_inclusion_probability"]),
            }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--frame", required=True)
    parser.add_argument("--allocation", required=True)
    parser.add_argument("--hidden-linkage", required=True)
    parser.add_argument("--freeze-receipt", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    allocation = load_allocation(args.allocation)
    with open(args.freeze_receipt, encoding="utf-8") as handle:
        freeze_receipt = json.load(handle)
    required = set(KEY + CELL) | {
        "nested_frame_cell_arm_N",
        "next_selected_cell_arm_n", "original_inclusion_probability",
        "conditional_inclusion_probability", "total_inclusion_probability",
        "nested_design_weight", "inclusion_probability", "design_weight",
    }
    table = pq.read_table(args.frame, columns=sorted(required))
    rows = table.to_pylist()
    failures = []
    actual_frame_sha256 = sha256(args.frame)
    if freeze_receipt.get("status") != "pass" or freeze_receipt.get("version") != "formal800-ad-sample-v1":
        failures.append("freeze receipt status/version is not the accepted Formal800 freeze")
    frozen_frame = freeze_receipt.get("frame", {})
    if frozen_frame.get("rows") != 10000 or frozen_frame.get("sha256") != actual_frame_sha256:
        failures.append("freeze receipt is not bound to the audited fixed10k frame")
    if len(rows) != 10000:
        failures.append("fixed sample row count is not 10000")
    null_key_rows = sum(any(row.get(name) in (None, "") for name in KEY) for row in rows)
    if null_key_rows:
        failures.append("fixed10k contains null canonical key components")
    keys = [canonical(row) for row in rows]
    if len(set(keys)) != len(keys):
        failures.append("canonical keys are not unique")

    arm_counts = collections.Counter(str(row["arm"]) for row in rows)
    if dict(arm_counts) != EXPECTED_ARMS:
        failures.append("arm counts differ from 4000/4000/2000")
    if len(allocation) != 207 or collections.Counter(key[3] for key in allocation) != {"A": 69, "B": 69, "C": 69}:
        failures.append("allocation is not 207 rows with 69 cells per arm")

    by_cell = collections.Counter()
    max_errors = collections.defaultdict(float)
    dedicated_missing = collections.Counter()
    legacy_null = collections.Counter()
    sample_by_key = {}
    for row in rows:
        arm = str(row["arm"])
        cell = (str(row["OCCUPATION_MAJOR"]), row["CENSUS_REGION"], str(int(row["created_year"])), arm)
        by_cell[cell] += 1
        sample_by_key[canonical(row)] = row
        alloc = allocation.get(cell)
        if alloc is None:
            failures.append("sample cell absent from allocation: " + repr(cell))
            continue
        values = (row["original_inclusion_probability"], row["conditional_inclusion_probability"], row["total_inclusion_probability"], row["nested_design_weight"])
        if any(value is None for value in values):
            dedicated_missing[arm] += 1
            continue
        op, cp, tp, weight = map(float, values)
        if not all(math.isfinite(x) for x in (op, cp, tp, weight)) or not (0 < op <= 1 and 0 < cp <= 1 and 0 < tp <= 1 and weight > 0):
            failures.append("invalid dedicated probability/weight in arm " + arm)
        max_errors["total_pi_minus_product"] = max(max_errors["total_pi_minus_product"], abs(tp - op * cp))
        max_errors["weight_times_pi_minus_one"] = max(max_errors["weight_times_pi_minus_one"], abs(weight * tp - 1.0))
        max_errors["row_N_minus_allocation_N"] = max(max_errors["row_N_minus_allocation_N"], abs(int(row["nested_frame_cell_arm_N"]) - alloc["N"]))
        max_errors["row_n_minus_allocation_n"] = max(max_errors["row_n_minus_allocation_n"], abs(int(row["next_selected_cell_arm_n"]) - alloc["n"]))
        max_errors["row_original_pi_minus_allocation"] = max(max_errors["row_original_pi_minus_allocation"], abs(op - alloc["original_pi"]))
        max_errors["row_conditional_pi_minus_allocation"] = max(max_errors["row_conditional_pi_minus_allocation"], abs(cp - alloc["conditional_pi"]))
        max_errors["row_total_pi_minus_allocation"] = max(max_errors["row_total_pi_minus_allocation"], abs(tp - alloc["total_pi"]))
        if row["inclusion_probability"] is None or row["design_weight"] is None:
            legacy_null[arm] += 1

    if dedicated_missing:
        failures.append("dedicated probabilities or weights are missing")
    if any(by_cell[key] != alloc["n"] for key, alloc in allocation.items()):
        failures.append("sample cell counts do not reconcile to allocation")
    if any(error > TOL for name, error in max_errors.items() if "_N_" not in name and "_n_" not in name):
        failures.append("probability reconciliation exceeds tolerance")
    if max_errors["row_N_minus_allocation_N"] or max_errors["row_n_minus_allocation_n"]:
        failures.append("row N/n metadata differ from allocation")

    parent_counts = {}
    fixed_stage_counts = {}
    for arm in EXPECTED_ARMS:
        cells = [value for key, value in allocation.items() if key[3] == arm]
        fixed_stage_counts[arm] = sum(value["N"] for value in cells)
        reconstructed = sum(value["N"] / value["original_pi"] for value in cells)
        parent_counts[arm] = {"reconstructed": reconstructed, "expected": EXPECTED_PARENT[arm], "absolute_error": abs(reconstructed - EXPECTED_PARENT[arm])}
        if abs(reconstructed - EXPECTED_PARENT[arm]) > TOL:
            failures.append("parent count reconstruction failed for arm " + arm)

    frozen_exclusions = freeze_receipt.get("exclusions", {})
    frozen_excluded_by_source = frozen_exclusions.get("excluded_ads_by_source_arm_and_reason", {})
    frozen_exposure_counts = {
        arm: int(frozen_excluded_by_source.get(arm + "|prior_exposed_exact_context", 0))
        for arm in EXPECTED_ARMS
    }
    if sum(frozen_exposure_counts.values()) != 718 or frozen_exclusions.get("eligible_ads") != 9282:
        failures.append("freeze receipt does not contain the accepted 718/9282 exclusion counts")

    hidden = []
    with open(args.hidden_linkage, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                hidden.append(json.loads(line))
    hidden_keys = [canonical(row) for row in hidden]
    hidden_arm_counts = collections.Counter(row["formal_arm"] for row in hidden)
    hidden_errors = collections.Counter()
    hidden_missing_pi12 = collections.Counter()
    hidden_null_key_rows = sum(any(row.get(name) in (None, "") for name in KEY) for row in hidden)
    if hidden_null_key_rows:
        failures.append("hidden linkage contains null canonical key components")
    if len(hidden) != 800 or len(set(hidden_keys)) != 800:
        failures.append("hidden linkage is not 800 unique ads")
    if hidden_arm_counts != {"A": 320, "B": 320, "C": 160}:
        failures.append("hidden linkage arm counts differ from 320/320/160")
    for link, key in zip(hidden, hidden_keys):
        source = sample_by_key.get(key)
        if source is None:
            hidden_errors["key_absent_from_fixed10k"] += 1
            continue
        if str(link.get("formal_arm")) != str(source.get("arm")):
            hidden_errors["formal_arm_source_arm_mismatch"] += 1
        if link.get("pi12") is None:
            hidden_missing_pi12[str(link["formal_arm"])] += 1
        elif not math.isclose(float(link["pi12"]), float(source["total_inclusion_probability"]), rel_tol=TOL, abs_tol=TOL):
            hidden_errors["pi12_mismatch"] += 1
        if link.get("nested_design_weight") is None:
            hidden_missing_pi12[str(link["formal_arm"])] += 1
        elif not math.isclose(float(link["nested_design_weight"]), float(source["nested_design_weight"]), rel_tol=TOL, abs_tol=TOL):
            hidden_errors["nested_weight_mismatch"] += 1
    if hidden_errors:
        failures.append("hidden linkage does not reconcile to fixed10k")

    status = "pass" if not failures else "fail"
    receipt = {
        "version": "formal800-weight-lineage-audit-v1",
        "status": status,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "scheduler": {"job_id": os.getenv("SLURM_JOB_ID"), "environment": "WZ_SCNet_scheduled_compute", "cpus": os.getenv("SLURM_CPUS_PER_TASK")},
        "scope": "metadata-only verification; no resampling, review, semantic outcome calculation, reweighting, or parent estimate",
        "source_hashes": {
            "fixed10k_parquet": actual_frame_sha256,
            "accepted_cell_allocation_csv": sha256(args.allocation),
            "formal800_hidden_linkage": sha256(args.hidden_linkage),
            "formal800_freeze_receipt": sha256(args.freeze_receipt),
        },
        "fixed10k": {
            "rows": len(rows), "unique_canonical_keys": len(set(keys)), "null_canonical_key_rows": null_key_rows, "arm_counts": dict(arm_counts),
            "allocation_rows": len(allocation), "allocation_cells_by_arm": dict(collections.Counter(key[3] for key in allocation)),
            "fixed_stage_frame_counts": fixed_stage_counts, "reconstructed_parent_candidate_counts": parent_counts,
        },
        "probability_lineage": {
            "dedicated_missing_by_arm": dict(dedicated_missing), "legacy_null_by_arm": dict(legacy_null),
            "max_absolute_errors": dict(max_errors), "tolerance": TOL,
            "interpretation": "legacy inclusion_probability/design_weight are A/B-only; dedicated total probability and nested weight govern all three arms",
        },
        "prior_exposure_exclusions": {
            "verification_scope": "attributed to hashed frozen Formal800 receipt; not recomputed in this metadata audit",
            "unweighted_by_arm": frozen_exposure_counts, "unweighted_total": sum(frozen_exposure_counts.values()),
            "eligible_fixed10k_rows": frozen_exclusions.get("eligible_ads"),
            "excluded_weight_mass": "not audited: no retained full excluded-key map was used",
        },
        "formal800_linkage": {"rows": len(hidden), "unique_canonical_keys": len(set(hidden_keys)), "null_canonical_key_rows": hidden_null_key_rows, "arm_counts": dict(hidden_arm_counts), "missing_legacy_pi12_or_weight_by_arm": dict(hidden_missing_pi12), "reconciliation_errors": dict(hidden_errors)},
        "decision": {
            "published_estimand": "retain finite post-exclusion 9282-ad fixed10k estimand using w3=1/pi3 unchanged",
            "c_weight_claim": "correct prior missing-weight wording only if this receipt status is pass",
            "parent_inference": "disabled; recovered lineage does not resolve post-draw exclusions or the restricted technology-screened frame",
        },
        "failures": failures,
        "privacy": "aggregate counts, weight masses, tolerances, and cryptographic hashes only; no record keys, text, contexts, or outcomes",
    }
    atomic_json(args.output, receipt)
    print(json.dumps({"status": status, "output": args.output, "failures": failures}, sort_keys=True))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
