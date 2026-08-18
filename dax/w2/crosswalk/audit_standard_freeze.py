"""Independently audit and freeze the DAX OCC2010/O*NET standard.

The audit consumes private SCC artifacts but emits only aggregate metrics,
hashes, permissions, and pass/fail checks.  No occupation-level rows or source
paths are written to the sanitized receipt.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import pathlib
import stat
import subprocess
from collections import Counter, defaultdict


SENSITIVE_TRACKED_BASENAMES = {
    "cps_onet_crosswalk.csv",
    "onet_25_0_to_2019_fallback_timeshares.csv",
    "task_wage_allocations.csv",
}


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _bool(value: object) -> bool:
    normalized = str(value).strip().lower()
    if normalized not in {"true", "false"}:
        raise ValueError(f"expected true/false, got {value!r}")
    return normalized == "true"


def _code(value: object) -> str:
    return str(value).strip().zfill(4)


def _read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _mode(path: pathlib.Path) -> str:
    return f"{stat.S_IMODE(path.stat().st_mode):04o}"


def _is_restricted(path: pathlib.Path) -> bool:
    return stat.S_IMODE(path.stat().st_mode) & 0o077 == 0


def sensitive_tracked_files(repo_root: pathlib.Path) -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    paths = [path for path in completed.stdout.decode().split("\0") if path]
    violations = []
    for path in paths:
        candidate = pathlib.PurePosixPath(path)
        name = candidate.name.lower()
        suffix = candidate.suffix.lower()
        if "synthetic" in candidate.parts:
            continue
        row_data_suffixes = {".csv", ".dta", ".parquet", ".sav", ".feather"}
        if name in SENSITIVE_TRACKED_BASENAMES:
            violations.append(path)
        elif name.startswith("cps_onet_crosswalk") and suffix in row_data_suffixes:
            violations.append(path)
        elif (name.startswith("onet_25_0_to_2019_fallback_timeshares")
              and suffix in row_data_suffixes):
            violations.append(path)
        elif name.startswith("cps_onet_gap_audit") and suffix == ".csv":
            violations.append(path)
        elif name.startswith("preperiod_cells") and suffix in {".csv", ".dta", ".parquet"}:
            violations.append(path)
        elif "respondent" in name and suffix in {".csv", ".dta", ".parquet"}:
            violations.append(path)
        elif "ipums" in name and suffix in row_data_suffixes:
            violations.append(path)
        elif ({"outcome", "outcomes"} & set(candidate.parts)
              and suffix in row_data_suffixes):
            violations.append(path)
    return sorted(set(violations))


def audit_crosswalk(
    rows: list[dict[str, str]], observed_mass: dict[str, float]
) -> tuple[dict[str, object], list[str]]:
    errors = []
    rows_by_code: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        rows_by_code[_code(row["cps_occ2010"])].append(row)

    bad_weight_sums = {}
    inconsistent_status_codes = []
    eligibility_violations = []
    derived_status_violations = []
    statuses = {}
    for code, code_rows in sorted(rows_by_code.items()):
        weight_sum = sum(float(row["mapping_weight"]) for row in code_rows)
        if not math.isclose(weight_sum, 1.0, abs_tol=1e-9):
            bad_weight_sums[code] = weight_sum
        code_statuses = {row["cps_code_status"] for row in code_rows}
        if len(code_statuses) != 1:
            inconsistent_status_codes.append(code)
            continue
        code_status = code_statuses.pop()
        statuses[code] = code_status
        expected_eligible = code_status == "resolved_employment_weighted"
        if any(_bool(row["downstream_eligible"]) != expected_eligible
               for row in code_rows):
            eligibility_violations.append(code)
        unresolved_weight = sum(
            float(row["mapping_weight"]) for row in code_rows
            if row["route_status"].startswith("unresolved_")
        )
        route_statuses = {row["route_status"] for row in code_rows}
        if unresolved_weight >= 1.0 - 1e-9:
            derived = "unresolved"
        elif unresolved_weight > 1e-9:
            derived = "partial_unresolved"
        elif any(status.startswith("provisional_") for status in route_statuses):
            derived = "provisional_equal_within_soc"
        else:
            derived = "resolved_employment_weighted"
        if code_status != derived:
            derived_status_violations.append(code)

    if bad_weight_sums:
        errors.append("crosswalk contains per-code weights that do not sum to one")
    if inconsistent_status_codes:
        errors.append("crosswalk contains inconsistent whole-code statuses")
    if eligibility_violations:
        errors.append("crosswalk violates fail-closed whole-code eligibility")
    if derived_status_violations:
        errors.append("crosswalk whole-code statuses disagree with route components")

    total_mass = sum(observed_mass.values())
    component_mass: dict[str, float] = defaultdict(float)
    whole_code_mass: dict[str, float] = defaultdict(float)
    unresolved_contribution = {}
    for code, mass in observed_mass.items():
        code_rows = rows_by_code.get(code, [])
        whole_code_mass[statuses.get(code, "absent_from_crosswalk")] += mass
        if not code_rows:
            component_mass["absent_from_crosswalk"] += mass
            unresolved_contribution[code] = mass / total_mass
            continue
        unresolved_weight = 0.0
        for row in code_rows:
            route_status = row["route_status"]
            weight_mass = mass * float(row["mapping_weight"])
            if route_status == "resolved_employment_weighted":
                bucket = "resolved"
            else:
                bucket = route_status
            component_mass[bucket] += weight_mass
            if route_status.startswith("unresolved_"):
                unresolved_weight += float(row["mapping_weight"])
        unresolved_contribution[code] = mass / total_mass * unresolved_weight

    component_shares = {
        key: value / total_mass for key, value in sorted(component_mass.items())
    }
    whole_code_shares = {
        key: value / total_mass for key, value in sorted(whole_code_mass.items())
    }
    resolved_share = component_shares.get("resolved", 0.0)
    provisional_share = sum(
        value for key, value in component_shares.items()
        if key.startswith("provisional_")
    )
    unresolved_share = sum(
        value for key, value in component_shares.items()
        if key.startswith("unresolved_")
    )
    absent_share = component_shares.get("absent_from_crosswalk", 0.0)
    worst_code = max(unresolved_contribution, key=unresolved_contribution.get)
    worst_share = unresolved_contribution[worst_code]

    status_counts = Counter(statuses.values())
    metrics = {
        "n_mapping_rows": len(rows),
        "n_cps_codes": len(rows_by_code),
        "cps_code_status_counts": dict(sorted(status_counts.items())),
        "bad_weight_sums": len(bad_weight_sums),
        "inconsistent_status_codes": len(inconsistent_status_codes),
        "derived_status_violations": len(derived_status_violations),
        "eligibility_violations": len(eligibility_violations),
        "n_point_eligible_codes": sum(
            status == "resolved_employment_weighted" for status in statuses.values()
        ),
        "n_observed_preperiod_codes": len(observed_mass),
        "whole_code_mass_shares": {
            key: round(value, 10) for key, value in whole_code_shares.items()
        },
        "component_mass_shares": {
            key: round(value, 10) for key, value in component_shares.items()
        },
        "fully_resolved_component_mass_share": round(resolved_share, 10),
        "bounded_provisional_component_mass_share": round(provisional_share, 10),
        "mapped_component_mass_share": round(resolved_share + provisional_share, 10),
        "unresolved_component_mass_share": round(unresolved_share, 10),
        "absent_component_mass_share": round(absent_share, 10),
        "max_unresolved_occupation_contribution": round(worst_share, 10),
        "max_unresolved_occupation_code": worst_code,
        "mapped_is_not_fully_resolved": provisional_share > 0,
    }
    return metrics, errors


def audit_fallback(rows: list[dict[str, str]]) -> tuple[dict[str, object], list[str]]:
    errors = []
    rows_by_new: dict[str, list[dict[str, str]]] = defaultdict(list)
    rows_by_source: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    bounds_violations = 0
    for row in rows:
        new = row["onet_soc2019"].strip()
        old = row["onet_soc2010"].strip()
        rows_by_new[new].append(row)
        rows_by_source[(new, old)].append(row)
        if not _bool(row["bounds_required"]):
            bounds_violations += 1

    bad_fallback_sums = 0
    bad_profile_sums = 0
    bad_source_weight_sums = 0
    bad_statuses = 0
    sources_by_new: dict[str, set[str]] = defaultdict(set)
    weights_by_new_source = {}
    for (new, old), source_rows in rows_by_source.items():
        sources_by_new[new].add(old)
        if not math.isclose(
            sum(float(row["legacy_task_time_share"]) for row in source_rows),
            1.0,
            abs_tol=1e-9,
        ):
            bad_profile_sums += 1
        weights = {float(row["legacy_source_weight"]) for row in source_rows}
        if len(weights) != 1:
            bad_source_weight_sums += 1
        else:
            weights_by_new_source[(new, old)] = weights.pop()
    for new, new_rows in rows_by_new.items():
        if not math.isclose(
            sum(float(row["fallback_task_time_share"]) for row in new_rows),
            1.0,
            abs_tol=1e-9,
        ):
            bad_fallback_sums += 1
        source_weight_sum = sum(
            weights_by_new_source.get((new, old), math.nan)
            for old in sources_by_new[new]
        )
        if not math.isclose(source_weight_sum, 1.0, abs_tol=1e-9):
            bad_source_weight_sums += 1
        expected = (
            "legacy_single_source" if len(sources_by_new[new]) == 1
            else "legacy_equal_source_mix"
        )
        if any(row["fallback_status"] != expected for row in new_rows):
            bad_statuses += 1

    if bounds_violations:
        errors.append("legacy fallback contains rows without mandatory bounds")
    if bad_fallback_sums or bad_profile_sums or bad_source_weight_sums:
        errors.append("legacy fallback contains invalid per-code/source weights")
    if bad_statuses:
        errors.append("legacy fallback source-count status is inconsistent")
    metrics = {
        "n_rows": len(rows),
        "n_fallback_onet_soc2019_codes": len(rows_by_new),
        "n_equal_source_mix_codes": sum(
            len(sources) > 1 for sources in sources_by_new.values()
        ),
        "bad_fallback_share_sums": bad_fallback_sums,
        "bad_legacy_profile_share_sums": bad_profile_sums,
        "bad_legacy_source_weight_sums": bad_source_weight_sums,
        "bounds_required_violations": bounds_violations,
        "fallback_status_violations": bad_statuses,
    }
    return metrics, errors


def _observed_mass(path: pathlib.Path) -> dict[str, float]:
    result: dict[str, float] = defaultdict(float)
    for row in _read_csv(path):
        result[_code(row["cps_occ"])] += float(row["weight_sum"])
    return dict(result)


def _compare(actual: object, expected: object, label: str, errors: list[str]) -> None:
    if isinstance(actual, float) and isinstance(expected, (float, int)):
        equal = math.isclose(actual, float(expected), abs_tol=5e-10)
    else:
        equal = actual == expected
    if not equal:
        errors.append(f"receipt mismatch for {label}: {actual!r} != {expected!r}")


def build_receipt(args: argparse.Namespace) -> dict[str, object]:
    crosswalk_rows = _read_csv(args.crosswalk)
    fallback_rows = _read_csv(args.fallback)
    crosswalk_metrics, crosswalk_errors = audit_crosswalk(
        crosswalk_rows, _observed_mass(args.preperiod_cells)
    )
    fallback_metrics, fallback_errors = audit_fallback(fallback_rows)
    errors = crosswalk_errors + fallback_errors
    build_receipt = json.loads(args.build_receipt.read_text(encoding="utf-8"))
    fallback_receipt = json.loads(args.fallback_receipt.read_text(encoding="utf-8"))
    preperiod_receipt = json.loads(
        args.preperiod_receipt.read_text(encoding="utf-8")
    )

    artifact_paths = {
        "crosswalk": args.crosswalk,
        "legacy_fallback": args.fallback,
        "occupation_gap_audit": args.gap_audit,
        "preperiod_cells": args.preperiod_cells,
    }
    artifact_audit = {
        label: {
            "name": path.name,
            "sha256": sha256(path),
            "mode": _mode(path),
            "restricted": _is_restricted(path),
        }
        for label, path in artifact_paths.items()
    }
    if not all(item["restricted"] for item in artifact_audit.values()):
        errors.append("one or more private artifacts have group/world permissions")

    _compare(
        artifact_audit["crosswalk"]["sha256"],
        build_receipt["output_sha256"],
        "crosswalk output hash",
        errors,
    )
    _compare(
        artifact_audit["legacy_fallback"]["sha256"],
        fallback_receipt["output_sha256"],
        "legacy fallback output hash",
        errors,
    )
    _compare(
        artifact_audit["occupation_gap_audit"]["sha256"],
        args.expected_gap_audit_sha256,
        "occupation gap audit hash",
        errors,
    )
    _compare(
        artifact_audit["preperiod_cells"]["sha256"],
        preperiod_receipt["output_sha256"],
        "preperiod cells output hash",
        errors,
    )

    comparisons = {
        "n_mapping_rows": "n_mapping_rows",
        "n_cps_codes": "n_cps_codes",
        "bad_weight_sums": "bad_weight_sums",
        "mapped_component_mass_share": "mapped_component_weight_mass_share",
        "max_unresolved_occupation_contribution": (
            "max_unresolved_occupation_weight_share"
        ),
        "max_unresolved_occupation_code": "max_unresolved_occupation_code",
    }
    for actual_key, expected_key in comparisons.items():
        _compare(
            crosswalk_metrics[actual_key], build_receipt[expected_key],
            f"crosswalk {actual_key}", errors,
        )
    _compare(
        crosswalk_metrics["fully_resolved_component_mass_share"],
        build_receipt["observed_preperiod_component_weight_mass_shares"]["resolved"],
        "fully resolved component mass",
        errors,
    )
    _compare(
        crosswalk_metrics["bounded_provisional_component_mass_share"],
        sum(
            value for status, value in
            build_receipt["observed_preperiod_component_weight_mass_shares"].items()
            if status.startswith("provisional_")
        ),
        "bounded provisional component mass",
        errors,
    )
    _compare(
        crosswalk_metrics["unresolved_component_mass_share"],
        build_receipt["observed_preperiod_component_weight_mass_shares"]
        ["unresolved_no_usable_onet"],
        "unresolved component mass",
        errors,
    )
    _compare(
        crosswalk_metrics["absent_component_mass_share"],
        build_receipt["observed_preperiod_component_weight_mass_shares"]
        ["absent_from_crosswalk"],
        "absent component mass",
        errors,
    )
    for key in ("n_rows", "n_fallback_onet_soc2019_codes",
                "n_equal_source_mix_codes"):
        _compare(fallback_metrics[key], fallback_receipt[key], f"fallback {key}", errors)

    absent_codes = set(build_receipt["observed_codes_absent_from_official_crosswalk"])
    if "7630" not in absent_codes:
        errors.append("OCC2010 7630 is not recorded absent/fail-closed")
    if any(row["cps_occ2010"] == "7630" for row in crosswalk_rows):
        errors.append("OCC2010 7630 unexpectedly appears in the official crosswalk")

    mapped = float(crosswalk_metrics["mapped_component_mass_share"])
    worst = float(crosswalk_metrics["max_unresolved_occupation_contribution"])
    coverage_gate_pass = (
        mapped >= args.coverage_threshold
        and worst < args.max_unresolved_occupation_share
    )
    if not coverage_gate_pass:
        errors.append("approved component coverage gate fails")
    if not crosswalk_metrics["mapped_is_not_fully_resolved"]:
        errors.append("audit did not preserve mapped versus fully-resolved distinction")

    tracked_violations = sensitive_tracked_files(args.repo_root)
    if tracked_violations:
        errors.append("restricted row-level artifacts are tracked by Git")

    receipt = {
        "status": "PASS" if not errors else "FAIL",
        "standard": "DAX_OCC2010_ONET_STANDARD_FREEZE_V1",
        "generated_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "handoff_commit": args.handoff_commit,
        "rules": {
            "point_estimate_eligibility": (
                "Only whole CPS codes with cps_code_status="
                "resolved_employment_weighted may expose an unbounded point estimate."
            ),
            "provisional_components": (
                "Carry min/max across officially linked SOC/O*NET children or "
                "legacy sources; equal weights are a diagnostic center only."
            ),
            "unresolved_and_absent": "Fail closed, including OCC2010 7630.",
            "mapped_interpretation": (
                "Mapped equals resolved plus bounded provisional; mapped must "
                "never be described as fully resolved."
            ),
        },
        "artifacts": artifact_audit,
        "crosswalk_audit": crosswalk_metrics,
        "legacy_fallback_audit": fallback_metrics,
        "gates": {
            "coverage_threshold": args.coverage_threshold,
            "max_unresolved_occupation_share_threshold": (
                args.max_unresolved_occupation_share
            ),
            "coverage_gate_pass": coverage_gate_pass,
            "whole_code_eligibility_pass": (
                crosswalk_metrics["eligibility_violations"] == 0
            ),
            "occ2010_7630_fail_closed": (
                "7630" in absent_codes
                and not any(row["cps_occ2010"] == "7630" for row in crosswalk_rows)
            ),
            "private_permissions_pass": all(
                item["restricted"] for item in artifact_audit.values()
            ),
            "restricted_data_git_hygiene_pass": not tracked_violations,
        },
        "tracked_restricted_artifact_count": len(tracked_violations),
        "error_count": len(errors),
        "errors": errors,
    }
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--crosswalk", type=pathlib.Path, required=True)
    parser.add_argument("--fallback", type=pathlib.Path, required=True)
    parser.add_argument("--gap-audit", type=pathlib.Path, required=True)
    parser.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    parser.add_argument("--build-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--fallback-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--preperiod-receipt", type=pathlib.Path, required=True)
    parser.add_argument("--expected-gap-audit-sha256", required=True)
    parser.add_argument("--repo-root", type=pathlib.Path, required=True)
    parser.add_argument("--handoff-commit", required=True)
    parser.add_argument("--coverage-threshold", type=float, default=0.90)
    parser.add_argument("--max-unresolved-occupation-share", type=float, default=0.01)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    receipt = build_receipt(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
