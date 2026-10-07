#!/usr/bin/env python3
"""Build compact public tables from completed duration aggregate CSVs only."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def number(value: str) -> float:
    return float(value) if value else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    raw_detection = {
        (r["arm"], r["OBJECT_TYPE"]): r
        for r in read_csv(args.input / "raw_numeric_detection.csv") if r["scope"] == "overall"
    }
    weighted_detection = {
        (r["arm"], r["OBJECT_TYPE"]): r
        for r in read_csv(args.input / "design_weighted_numeric_detection.csv") if r["scope"] == "overall"
    }
    standardized_detection = {
        (r["arm"], r["OBJECT_TYPE"]): r
        for r in read_csv(args.input / "pooled_cell_standardized_numeric_detection.csv")
    }
    keys = sorted(raw_detection)
    if {arm for arm, _ in keys} != {"A", "B", "C"} or set(keys) != set(weighted_detection) or set(keys) != set(standardized_detection):
        raise RuntimeError("detection inputs do not contain matching A/B/C arm-object rows")
    detection_rows = []
    for key in keys:
        raw, weighted, standardized = raw_detection[key], weighted_detection[key], standardized_detection[key]
        detection_rows.append({
            "arm": key[0], "OBJECT_TYPE": key[1],
            "raw_sample_ads": raw["raw_sample_ads"],
            "raw_numeric_detected_ads": raw["raw_numeric_detected_ads"],
            "raw_numeric_detected_share": raw["raw_numeric_detected_share"],
            "design_weighted_ads": weighted["weighted_ads"],
            "design_weighted_numeric_detected_ads": weighted["weighted_numeric_detected_ads"],
            "design_weighted_numeric_detected_share": weighted["design_weighted_numeric_detected_share"],
            "pooled_cell_standardized_numeric_detected_share": standardized["pooled_cell_standardized_numeric_detected_share"],
            "pooled_cell_weight_sum": standardized["pooled_cell_weight_sum"],
            "supported_cells": standardized["supported_cells"],
        })
    detection_fields = list(detection_rows[0])
    write_csv(args.output / "experience_numeric_detection.csv", detection_fields, detection_rows)

    raw_groups: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in read_csv(args.input / "raw_numeric_clause_years.csv"):
        key = (row["arm"], row["OBJECT_TYPE"], row["REQUIREMENT_STRENGTH"], row["BOUND_TYPE"])
        group = raw_groups[key]
        clauses = number(row["raw_clause_rows"])
        max_clauses = number(row["raw_clauses_with_max_years"])
        group["raw_clause_rows"] += clauses
        group["raw_distinct_ads"] += number(row["raw_distinct_ads"])
        group["stored_bound_numerator"] += clauses * number(row["raw_mean_stored_bound_value_years"])
        group["raw_clauses_with_max_years"] += max_clauses
        group["max_numerator"] += max_clauses * number(row["raw_mean_max_years"])

    weighted_groups: dict[tuple[str, str, str, str], dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in read_csv(args.input / "design_weighted_numeric_clause_years.csv"):
        key = (row["arm"], row["OBJECT_TYPE"], row["REQUIREMENT_STRENGTH"], row["BOUND_TYPE"])
        group = weighted_groups[key]
        mass = number(row["design_weighted_clause_mass"])
        max_mass = number(row["design_weighted_clause_mass_with_max"])
        group["design_weighted_clause_mass"] += mass
        group["stored_bound_numerator"] += mass * number(row["design_weighted_mean_stored_bound_value_years"])
        group["design_weighted_clause_mass_with_max"] += max_mass
        group["max_numerator"] += max_mass * number(row["design_weighted_mean_max_years"])

    if set(raw_groups) != set(weighted_groups):
        raise RuntimeError("raw and design-weighted clause strata differ")
    year_rows = []
    for key in sorted(raw_groups):
        raw, weighted = raw_groups[key], weighted_groups[key]
        raw_count = raw["raw_clause_rows"]
        raw_max_count = raw["raw_clauses_with_max_years"]
        weighted_mass = weighted["design_weighted_clause_mass"]
        weighted_max_mass = weighted["design_weighted_clause_mass_with_max"]
        year_rows.append({
            "arm": key[0], "OBJECT_TYPE": key[1], "REQUIREMENT_STRENGTH": key[2], "BOUND_TYPE": key[3],
            "raw_clause_rows": int(raw_count), "raw_distinct_ads": int(raw["raw_distinct_ads"]),
            "raw_mean_stored_bound_value_years": raw["stored_bound_numerator"] / raw_count,
            "raw_clauses_with_max_years": int(raw_max_count),
            "raw_mean_max_years": raw["max_numerator"] / raw_max_count if raw_max_count else "",
            "design_weighted_clause_mass": weighted_mass,
            "design_weighted_mean_stored_bound_value_years": weighted["stored_bound_numerator"] / weighted_mass,
            "design_weighted_clause_mass_with_max": weighted_max_mass,
            "design_weighted_mean_max_years": weighted["max_numerator"] / weighted_max_mass if weighted_max_mass else "",
        })
    year_fields = list(year_rows[0])
    write_csv(args.output / "explicit_numeric_years_by_interpretation.csv", year_fields, year_rows)

    notes = [
        {"topic": "sample", "note": "Fixed actual sample: A=4,000; B=4,000; C=2,000."},
        {"topic": "C_scope", "note": "C is a residual within the prefiltered technology-candidate frame, not broad occupation background."},
        {"topic": "detection_denominator", "note": "Detection rows use advertisement denominators; absence of a matched valid numeric clause is not zero experience."},
        {"topic": "year_denominator", "note": "Year rows use valid numeric clause denominators; multiple clauses are retained and are not summed within advertisements."},
        {"topic": "interpretation", "note": "OBJECT_TYPE, REQUIREMENT_STRENGTH, and BOUND_TYPE remain separate; means are never averaged across these interpretations."},
        {"topic": "stored_bound_value", "note": "Stored value is coalesce(MIN_YEARS,MAX_YEARS): exact value, lower endpoint for minimum/range, or upper endpoint for maximum-only, with BOUND_TYPE explicit."},
        {"topic": "measurement_status", "note": "These are legacy-rule numeric diagnostics, not a model upgrade or validated semantic extraction."},
        {"topic": "standardization", "note": "Pooled-cell standardization is available for detection only; year summaries report raw and nested-design-weighted clause results."},
    ]
    write_csv(args.output / "DENOMINATOR_AND_SCOPE_NOTES.csv", ["topic", "note"], notes)

    source_files = sorted(args.input.glob("*.csv")) + [args.input / "DURATION_EXECUTION_RECEIPT.json"]
    outputs = [
        args.output / "experience_numeric_detection.csv",
        args.output / "explicit_numeric_years_by_interpretation.csv",
        args.output / "DENOMINATOR_AND_SCOPE_NOTES.csv",
    ]
    receipt = {
        "status": "complete", "source_directory": str(args.input),
        "source_sha256": {path.name: sha256(path) for path in source_files},
        "output_sha256": {path.name: sha256(path) for path in outputs},
        "detection_rows": len(detection_rows), "year_interpretation_rows": len(year_rows),
        "privacy": "public aggregate inputs and outputs only; no row-level keys or advertisement text",
    }
    (args.output / "RESULTS_BUILD_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
