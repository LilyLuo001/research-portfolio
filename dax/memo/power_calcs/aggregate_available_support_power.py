"""Aggregate parallel failed-coverage power batches without changing the gate."""

from __future__ import annotations

import argparse
import json
import math
import pathlib


PRIMARY_BENCHMARK = math.log(0.81)


def aggregate(records: list[dict]) -> dict:
    if not records:
        raise ValueError("no power batches supplied")
    required_same = [
        "cells_sha256", "lookup_sha256", "repetitions_per_effect", "seed",
        "occupation_clusters", "preperiod_months", "planned_post_months",
        "covered_route_mass_fraction", "effective_occupation_concentration_q1_q5",
    ]
    for field in required_same:
        values = {json.dumps(record.get(field), sort_keys=True) for record in records}
        if len(values) != 1:
            raise ValueError(f"power batches disagree on {field}")
    if any(record.get("status") != "DIAGNOSTIC_AVAILABLE_SUPPORT_ONLY"
           for record in records):
        raise ValueError("every batch must be explicitly diagnostic")
    if any(record.get("design_freeze_permitted") is not False for record in records):
        raise ValueError("a batch improperly permits design freeze")

    rows = [row for record in records for row in record["results"]]
    effects = [float(row["true_log_effect"]) for row in rows]
    if len(effects) != len(set(effects)):
        raise ValueError("duplicate effect across power batches")
    rows.sort(key=lambda row: float(row["true_log_effect"]), reverse=True)
    null = min(rows, key=lambda row: abs(float(row["true_log_effect"])))
    primary = min(
        rows,
        key=lambda row: abs(float(row["true_log_effect"]) - PRIMARY_BENCHMARK),
    )
    if abs(float(null["true_log_effect"])) > 1e-8:
        raise ValueError("effect grid lacks zero")
    if abs(float(primary["true_log_effect"]) - PRIMARY_BENCHMARK) > 1e-8:
        raise ValueError("effect grid lacks the 19-percent benchmark")
    mde_candidates = sorted(
        (abs(float(row["true_log_effect"])), float(row["true_log_effect"]))
        for row in rows
        if float(row["true_log_effect"]) < 0
        and float(row["rejection_probability_zero"]) >= 0.8
    )
    mde = mde_candidates[0][1] if mde_candidates else None
    conditional_pass = (
        float(primary["rejection_probability_zero"]) >= 0.8
        and float(null["benchmark_exclusion_probability"]) >= 0.8
    )
    first = records[0]
    return {
        "status": (
            "DIAGNOSTIC_AVAILABLE_SUPPORT_POWER_PASS"
            if conditional_pass else "DIAGNOSTIC_AVAILABLE_SUPPORT_POWER_FAIL"
        ),
        "design_freeze_permitted": False,
        "reason_design_freeze_blocked": "primary exposure coverage gate failed",
        "post_outcomes_read": False,
        "covered_route_mass_fraction": first["covered_route_mass_fraction"],
        "repetitions_per_effect": first["repetitions_per_effect"],
        "seed": first["seed"],
        "occupation_clusters": first["occupation_clusters"],
        "effective_occupation_concentration_q1_q5": first[
            "effective_occupation_concentration_q1_q5"
        ],
        "preperiod_months": first["preperiod_months"],
        "planned_post_months": first["planned_post_months"],
        "cells_sha256": first["cells_sha256"],
        "lookup_sha256": first["lookup_sha256"],
        "effect_count": len(rows),
        "primary_benchmark_log_effect": PRIMARY_BENCHMARK,
        "primary_benchmark_rejection_probability": primary[
            "rejection_probability_zero"
        ],
        "null_excludes_primary_benchmark_probability": null[
            "benchmark_exclusion_probability"
        ],
        "empirical_mde80_log_effect": mde,
        "empirical_mde80_relative_decline": (
            1.0 - math.exp(mde) if mde is not None else None
        ),
        "results": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("batches", nargs="+", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, required=True)
    args = parser.parse_args()
    records = [json.loads(path.read_text(encoding="utf-8")) for path in args.batches]
    result = aggregate(records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": result["status"],
        "design_freeze_permitted": result["design_freeze_permitted"],
        "effect_count": result["effect_count"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
