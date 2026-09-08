#!/usr/bin/env python3
"""Combine corrected-shortfall household batches and audit endpoint precision."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


MODES = (
    "fixed_shortfalls_fixed_labels",
    "regenerated_shortfalls_fixed_labels",
    "regenerated_shortfalls_and_labels",
)
CONTROLS = ("total", "young_relative")
TARGETS = ("pooled", "family_month", "family_month_minus_pooled")
STATISTICS = {
    "q5": ("observed_q5", "bootstrap_q5", "q5_shift", True),
    "conditioning_movement": (
        "observed_conditioning_movement",
        "bootstrap_conditioning_movement",
        "conditioning_movement_shift",
        True,
    ),
    "shortfall_z_coefficient": (
        "observed_shortfall_z_coefficient",
        "bootstrap_shortfall_z_coefficient",
        "shortfall_z_coefficient_shift",
        True,
    ),
    "shortfall_raw_coefficient": (
        "observed_shortfall_raw_coefficient",
        "bootstrap_shortfall_raw_coefficient",
        "shortfall_raw_coefficient_shift",
        False,
    ),
}
ENDPOINT_BOOTSTRAP_DRAWS = 1999
ENDPOINT_SEED = 202609084500
ENDPOINT_MCSE_TARGET = 0.01


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    require(bool(rows), f"refusing to write empty {path.name}")
    fields: list[str] = []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def endpoint_monte_carlo_error(shifts: np.ndarray, seed: int) -> tuple[float, float]:
    shifts = np.asarray(shifts, float)
    require(len(shifts) >= 199, "too few successful draws for endpoint audit")
    rng = np.random.default_rng(seed)
    quantiles = np.empty((ENDPOINT_BOOTSTRAP_DRAWS, 2))
    for index in range(ENDPOINT_BOOTSTRAP_DRAWS):
        sample = shifts[rng.integers(0, len(shifts), size=len(shifts))]
        quantiles[index] = np.quantile(sample, [.025, .975])
    return tuple(np.std(quantiles, axis=0, ddof=1).tolist())


def validate_batch_inventory(frame: pd.DataFrame, failures: list[dict[str, Any]],
                             first: int, last: int, label: str) -> None:
    keys = ["draw", "mode", "control", "target"]
    require(not frame.duplicated(keys).any(), f"{label} contains duplicate result rows")
    expected_draws = set(range(first, last + 1))
    require(set(frame.draw.astype(int)).issubset(expected_draws),
            f"{label} contains an out-of-range result draw")
    failure_by_draw: dict[int, set[str]] = {}
    for failure in failures:
        draw = int(failure["draw"])
        require(draw in expected_draws, f"{label} contains an out-of-range failure")
        failure_by_draw.setdefault(draw, set()).add(str(failure["mode"]))
    for draw in expected_draws:
        local = frame.loc[frame.draw.eq(draw)]
        for mode in MODES:
            count = int(local.loc[local["mode"].eq(mode)].shape[0])
            failed = mode in failure_by_draw.get(draw, set()) or "all" in failure_by_draw.get(draw, set())
            require((count == len(CONTROLS) * len(TARGETS) and not failed)
                    or (count == 0 and failed),
                    f"{label} draw {draw}/{mode} is neither complete nor failed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-root", type=Path, required=True)
    parser.add_argument("--through-draw", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(199 <= args.through_draw <= 1999, "invalid shortfall stopping draw")
    require(not args.output_dir.exists(), "refusing to overwrite shortfall summary")
    receipt_paths = sorted(args.batch_root.glob("batch_*/EXECUTION_RECEIPT.json"))
    require(bool(receipt_paths), "no shortfall batch receipts found")
    frames: list[pd.DataFrame] = []
    inventory: list[tuple[int, int]] = []
    receipt_hashes: dict[str, str] = {}
    fixed_observed_hash: str | None = None
    fixed_construction_hash: str | None = None
    all_failures: list[dict[str, Any]] = []
    covered_ranges: list[set[int]] = []
    for path in receipt_paths:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        require(receipt.get("status") in {
            "PASS_SHORTFALL_REFIT_BATCH", "SHORTFALL_REFIT_FAILURES_RETAINED"},
            f"{path.parent.name} receipt status is invalid")
        for name, expected_hash in receipt["output_hashes"].items():
            require(sha256_file(path.parent / name) == expected_hash,
                    f"{path.parent.name}/{name} hash differs")
        first, last = int(receipt["start_draw"]), int(receipt["last_draw"])
        require(last - first + 1 == int(receipt["requested_draws"]),
                f"{path.parent.name} receipt range differs")
        frame = pd.read_csv(path.parent / "SHORTFALL_REFIT_DRAWS.csv")
        failures = json.loads((path.parent / "MODEL_FAILURES.json").read_text(encoding="utf-8"))
        require(len(frame) == int(receipt["successful_rows"]),
                f"{path.parent.name} successful row count differs")
        require(len(failures) == int(receipt["failure_records"]),
                f"{path.parent.name} failure count differs")
        validate_batch_inventory(frame, failures, first, last, path.parent.name)
        local_set = set(range(first, min(last, args.through_draw) + 1))
        if local_set:
            require(not any(local_set & prior for prior in covered_ranges),
                    "shortfall batch draw ranges overlap")
            covered_ranges.append(local_set)
            frames.append(frame.loc[frame.draw.le(args.through_draw)].copy())
            all_failures.extend(
                failure for failure in failures if int(failure["draw"]) <= args.through_draw)
        inventory.append((first, last))
        receipt_hashes[path.parent.name] = sha256_file(path)
        observed_hash = receipt["output_hashes"]["OBSERVED_CORRECTED_SHORTFALL_MODELS.csv"]
        construction_hash = receipt["output_hashes"]["OBSERVED_CONSTRUCTION.json"]
        if fixed_observed_hash is None:
            fixed_observed_hash = observed_hash
            fixed_construction_hash = construction_hash
        require(observed_hash == fixed_observed_hash
                and construction_hash == fixed_construction_hash,
                "observed corrected target changed across batches")
    require(set().union(*covered_ranges) == set(range(1, args.through_draw + 1)),
            "shortfall batch ranges do not cover the requested draws")
    combined = pd.concat(frames, ignore_index=True)
    require(not combined.duplicated(["draw", "mode", "control", "target"]).any(),
            "shortfall result rows overlap")
    require(set(combined["mode"]) <= set(MODES)
            and set(combined.control) <= set(CONTROLS)
            and set(combined.target) <= set(TARGETS),
            "shortfall result labels differ")

    summaries: list[dict[str, Any]] = []
    endpoint_errors: list[float] = []
    for mode_index, mode in enumerate(MODES):
        for control_index, control in enumerate(CONTROLS):
            for target_index, target in enumerate(TARGETS):
                local = combined.loc[
                    combined["mode"].eq(mode)
                    & combined.control.eq(control)
                    & combined.target.eq(target)
                ].sort_values("draw")
                require(len(local) >= 199, f"too few refits for {mode}/{control}/{target}")
                base_row: dict[str, Any] = {
                    "mode": mode, "control": control, "target": target,
                    "requested_draws": args.through_draw,
                    "successful_full_refits": len(local),
                    "failed_or_missing_draws": args.through_draw - len(local),
                    "mean_support_occupations": float(local.support_occupations.mean()),
                    "mean_occupations_reclassified": float(local.occupations_reclassified.mean()),
                    "design_based_CPS_interval": False,
                    "mechanically_combined_with_cluster_variance": False,
                }
                for statistic_index, (statistic, columns) in enumerate(STATISTICS.items()):
                    observed_name, bootstrap_name, shift_name, precision_binding = columns
                    observed = float(local[observed_name].iloc[0])
                    require(np.allclose(local[observed_name], observed, rtol=0, atol=1e-12),
                            f"observed {statistic} changes across draws")
                    shifts = local[shift_name].to_numpy(float)
                    require(np.allclose(
                        local[bootstrap_name].to_numpy(float) - observed,
                        shifts, rtol=0, atol=2e-12),
                        f"{statistic} shift identity differs")
                    q025, q975 = np.quantile(shifts, [.025, .975])
                    lower_error, upper_error = endpoint_monte_carlo_error(
                        shifts,
                        ENDPOINT_SEED + mode_index * 1000 + control_index * 100
                        + target_index * 10 + statistic_index,
                    )
                    if precision_binding:
                        endpoint_errors.extend([lower_error, upper_error])
                    prefix = statistic + "_"
                    base_row.update({
                        prefix + "observed": observed,
                        prefix + "sampling_sensitivity_se": float(np.std(shifts, ddof=1)),
                        prefix + "mean_full_refit_shift": float(np.mean(shifts)),
                        prefix + "basic_ci_lower": float(observed - q975),
                        prefix + "basic_ci_upper": float(observed - q025),
                        prefix + "shift_q025_mcse": lower_error,
                        prefix + "shift_q975_mcse": upper_error,
                        prefix + "endpoint_precision_binding": precision_binding,
                    })
                summaries.append(base_row)
    maximum_error = max(endpoint_errors)
    stopping = {
        "through_draw": args.through_draw,
        "maximum_binding_interval_endpoint_mcse": maximum_error,
        "endpoint_mcse_target_log_point": ENDPOINT_MCSE_TARGET,
        "binding_statistics": [
            statistic for statistic, columns in STATISTICS.items() if columns[3]
        ],
        "passes": maximum_error <= ENDPOINT_MCSE_TARGET,
        "cap_reached": args.through_draw >= 1999,
        "failure_records_through_draw": len(all_failures),
    }
    args.output_dir.mkdir(parents=True)
    summary_path = args.output_dir / "SHORTFALL_REFIT_SUMMARY.csv"
    stopping_path = args.output_dir / "SHORTFALL_STOPPING.json"
    write_csv(summary_path, summaries)
    stopping_path.write_text(
        json.dumps(stopping, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    receipt = {
        "schema_version": "yax-gate3-shortfall-refit-summary-v1",
        "status": ("PASS_SHORTFALL_ENDPOINT_PRECISION" if stopping["passes"]
                   else "SHORTFALL_ENDPOINT_PRECISION_UNRESOLVED"),
        "through_draw": args.through_draw,
        "batch_ranges": inventory,
        "batch_receipt_hashes": receipt_hashes,
        "observed_models_sha256": fixed_observed_hash,
        "observed_construction_sha256": fixed_construction_hash,
        "stopping": stopping,
        "output_hashes": {
            summary_path.name: sha256_file(summary_path),
            stopping_path.name: sha256_file(stopping_path),
        },
        "interpretation": (
            "linked-household full-pipeline sensitivity; not CPS design-based inference "
            "and not mechanically combined with cluster variance"
        ),
    }
    (args.output_dir / "SUMMARY_RECEIPT.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": receipt["status"],
                      "through_draw": args.through_draw,
                      "maximum_endpoint_mcse": maximum_error}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
