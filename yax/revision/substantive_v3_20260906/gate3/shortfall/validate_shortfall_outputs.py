#!/usr/bin/env python3
"""Independently validate public corrected-shortfall refit outputs."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

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
ENDPOINT_DRAWS = 1999
ENDPOINT_SEED = 202609084500


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def close(left: float, right: float, tolerance: float = 2e-12) -> None:
    require(math.isclose(float(left), float(right), rel_tol=tolerance, abs_tol=tolerance),
            f"numerical mismatch: {left} versus {right}")


def endpoint_error(shifts: np.ndarray, seed: int) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    quantiles = np.empty((ENDPOINT_DRAWS, 2))
    for index in range(ENDPOINT_DRAWS):
        sample = shifts[rng.integers(0, len(shifts), size=len(shifts))]
        quantiles[index] = np.quantile(sample, [.025, .975])
    return tuple(np.std(quantiles, axis=0, ddof=1).tolist())


def read_batches(run_dir: Path, through: int) -> tuple[pd.DataFrame, list[dict], dict[str, str]]:
    frames: list[pd.DataFrame] = []
    failures: list[dict] = []
    receipt_hashes: dict[str, str] = {}
    covered: list[set[int]] = []
    observed_model_hash: str | None = None
    construction_hash: str | None = None
    for directory in sorted(run_dir.glob("batch_*")):
        receipt_path = directory / "EXECUTION_RECEIPT.json"
        if not receipt_path.exists():
            continue
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        require(receipt["status"] in {
            "PASS_SHORTFALL_REFIT_BATCH", "SHORTFALL_REFIT_FAILURES_RETAINED"},
            f"{directory.name} status differs")
        for name, expected in receipt["output_hashes"].items():
            require(sha256_file(directory / name) == expected,
                    f"{directory.name}/{name} hash differs")
        first, last = int(receipt["start_draw"]), int(receipt["last_draw"])
        require(last - first + 1 == int(receipt["requested_draws"]),
                f"{directory.name} range differs")
        frame = pd.read_csv(directory / "SHORTFALL_REFIT_DRAWS.csv")
        local_failures = json.loads((directory / "MODEL_FAILURES.json").read_text())
        require(len(frame) == int(receipt["successful_rows"])
                and len(local_failures) == int(receipt["failure_records"]),
                f"{directory.name} row accounting differs")
        require(not frame.duplicated(["draw", "mode", "control", "target"]).any(),
                f"{directory.name} contains duplicates")
        for draw in range(first, last + 1):
            failure_modes = {
                str(item["mode"]) for item in local_failures if int(item["draw"]) == draw
            }
            local = frame.loc[frame.draw.eq(draw)]
            for mode in MODES:
                count = int(local.loc[local["mode"].eq(mode)].shape[0])
                failed = mode in failure_modes or "all" in failure_modes
                require((count == 6 and not failed) or (count == 0 and failed),
                        f"{directory.name} draw {draw}/{mode} accounting differs")
        applicable = set(range(first, min(last, through) + 1))
        if applicable:
            require(not any(applicable & previous for previous in covered),
                    "batch draw ranges overlap")
            covered.append(applicable)
            frames.append(frame.loc[frame.draw.le(through)].copy())
            failures.extend(
                item for item in local_failures if int(item["draw"]) <= through)
        receipt_hashes[directory.name] = sha256_file(receipt_path)
        current_model_hash = receipt["output_hashes"]["OBSERVED_CORRECTED_SHORTFALL_MODELS.csv"]
        current_construction_hash = receipt["output_hashes"]["OBSERVED_CONSTRUCTION.json"]
        if observed_model_hash is None:
            observed_model_hash = current_model_hash
            construction_hash = current_construction_hash
        require(current_model_hash == observed_model_hash
                and current_construction_hash == construction_hash,
                "observed corrected construction changes across batches")
    require(covered and set().union(*covered) == set(range(1, through + 1)),
            "batch ranges do not cover requested draws")
    combined = pd.concat(frames, ignore_index=True)
    return combined, failures, receipt_hashes


def validate_within_draw_identities(frame: pd.DataFrame) -> float:
    maximum_gap = 0.0
    for row in frame.itertuples(index=False):
        identities = (
            (row.observed_conditioning_movement,
             row.observed_q5 - row.observed_baseline_q5),
            (row.bootstrap_conditioning_movement,
             row.bootstrap_q5 - row.bootstrap_baseline_q5),
            (row.q5_shift, row.bootstrap_q5 - row.observed_q5),
            (row.conditioning_movement_shift,
             row.bootstrap_conditioning_movement - row.observed_conditioning_movement),
            (row.shortfall_z_coefficient_shift,
             row.bootstrap_shortfall_z_coefficient - row.observed_shortfall_z_coefficient),
            (row.shortfall_raw_coefficient_shift,
             row.bootstrap_shortfall_raw_coefficient - row.observed_shortfall_raw_coefficient),
            (row.bootstrap_shortfall_raw_coefficient,
             row.bootstrap_shortfall_z_coefficient / row.shortfall_weighted_sd),
        )
        for left, right in identities:
            gap = abs(float(left) - float(right))
            maximum_gap = max(maximum_gap, gap)
            close(left, right)
    for (_, mode, control), local in frame.groupby(["draw", "mode", "control"]):
        require(set(local.target) == set(TARGETS), "a target triplet is incomplete")
        indexed = local.set_index("target")
        for prefix in ("observed_q5", "bootstrap_q5", "observed_baseline_q5",
                       "bootstrap_baseline_q5", "observed_conditioning_movement",
                       "bootstrap_conditioning_movement",
                       "observed_shortfall_z_coefficient",
                       "bootstrap_shortfall_z_coefficient",
                       "observed_shortfall_raw_coefficient",
                       "bootstrap_shortfall_raw_coefficient"):
            expected = indexed.at["family_month", prefix] - indexed.at["pooled", prefix]
            close(indexed.at["family_month_minus_pooled", prefix], expected)
        require(local.support_occupations.nunique() == 1
                and local.occupations_reclassified.nunique() == 1,
                "target triplet construction diagnostics differ")
    for (draw, mode, target), local in frame.groupby(["draw", "mode", "target"]):
        require(len(local) == len(CONTROLS), "control pair is incomplete")
        require(local.observed_baseline_q5.nunique() == 1
                and local.bootstrap_baseline_q5.nunique() == 1,
                f"baseline differs across controls at {draw}/{mode}/{target}")
    fixed_modes = frame.loc[frame["mode"].isin(MODES[:2])]
    for (draw, target), local in fixed_modes.groupby(["draw", "target"]):
        require(local.groupby("mode").bootstrap_baseline_q5.first().nunique() == 1,
                f"fixed-label baseline differs across modes at {draw}/{target}")
    return maximum_gap


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    summary_dir = args.run_dir / "summary"
    receipt_path = summary_dir / "SUMMARY_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    through = int(receipt["through_draw"])
    require(receipt["status"] in {
        "PASS_SHORTFALL_ENDPOINT_PRECISION", "SHORTFALL_ENDPOINT_PRECISION_UNRESOLVED"},
        "summary status differs")
    for name, expected in receipt["output_hashes"].items():
        require(sha256_file(summary_dir / name) == expected,
                f"summary {name} hash differs")
    combined, failures, batch_hashes = read_batches(args.run_dir, through)
    require(receipt["batch_receipt_hashes"] == batch_hashes,
            "summary batch binding differs")
    require(not combined.duplicated(["draw", "mode", "control", "target"]).any(),
            "combined shortfall rows overlap")
    identity_gap = validate_within_draw_identities(combined)
    summary = pd.read_csv(summary_dir / "SHORTFALL_REFIT_SUMMARY.csv")
    stopping = json.loads((summary_dir / "SHORTFALL_STOPPING.json").read_text())
    require(len(summary) == len(MODES) * len(CONTROLS) * len(TARGETS),
            "shortfall summary inventory differs")
    maximum_summary_gap = 0.0
    endpoint_errors: list[float] = []
    for mode_index, mode in enumerate(MODES):
        for control_index, control in enumerate(CONTROLS):
            for target_index, target in enumerate(TARGETS):
                local = combined.loc[
                    combined["mode"].eq(mode)
                    & combined.control.eq(control)
                    & combined.target.eq(target)
                ].sort_values("draw")
                row = summary.loc[
                    summary["mode"].eq(mode)
                    & summary.control.eq(control)
                    & summary.target.eq(target)
                ]
                require(len(row) == 1, f"summary row differs for {mode}/{control}/{target}")
                row = row.iloc[0]
                close(row.successful_full_refits, len(local))
                close(row.failed_or_missing_draws, through - len(local))
                for statistic_index, (statistic, columns) in enumerate(STATISTICS.items()):
                    observed_name, _, shift_name, binding = columns
                    observed = float(local[observed_name].iloc[0])
                    shifts = local[shift_name].to_numpy(float)
                    q025, q975 = np.quantile(shifts, [.025, .975])
                    expected_values = {
                        "observed": observed,
                        "sampling_sensitivity_se": float(np.std(shifts, ddof=1)),
                        "mean_full_refit_shift": float(np.mean(shifts)),
                        "basic_ci_lower": float(observed - q975),
                        "basic_ci_upper": float(observed - q025),
                    }
                    for suffix, value in expected_values.items():
                        actual = float(row[statistic + "_" + suffix])
                        maximum_summary_gap = max(maximum_summary_gap, abs(actual - value))
                        close(actual, value)
                    lower_error, upper_error = endpoint_error(
                        shifts,
                        ENDPOINT_SEED + mode_index * 1000 + control_index * 100
                        + target_index * 10 + statistic_index,
                    )
                    close(row[statistic + "_shift_q025_mcse"], lower_error)
                    close(row[statistic + "_shift_q975_mcse"], upper_error)
                    if binding:
                        endpoint_errors.extend([lower_error, upper_error])
    maximum_endpoint_error = max(endpoint_errors)
    close(stopping["maximum_binding_interval_endpoint_mcse"], maximum_endpoint_error)
    require(stopping["failure_records_through_draw"] == len(failures),
            "failure denominator differs")
    expected_pass = maximum_endpoint_error <= stopping["endpoint_mcse_target_log_point"]
    require(bool(stopping["passes"]) == expected_pass,
            "shortfall stopping decision differs")
    result = {
        "schema_version": "yax-gate3-shortfall-independent-validation-v1",
        "status": "PASS_SHORTFALL_PUBLIC_OUTPUT_VALIDATION",
        "through_draw": through,
        "result_rows": len(combined),
        "failure_records": len(failures),
        "maximum_recomputed_identity_gap": identity_gap,
        "maximum_recomputed_summary_gap": maximum_summary_gap,
        "maximum_recomputed_binding_endpoint_mcse": maximum_endpoint_error,
        "endpoint_precision_pass": expected_pass,
        "batch_receipt_hashes": batch_hashes,
        "summary_hashes": {
            name: sha256_file(summary_dir / name)
            for name in ("SHORTFALL_REFIT_SUMMARY.csv", "SHORTFALL_STOPPING.json",
                         "SUMMARY_RECEIPT.json")
        },
    }
    output = summary_dir / "INDEPENDENT_VALIDATION.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n",
                      encoding="utf-8")
    print(json.dumps({"status": result["status"], "through_draw": through,
                      "endpoint_precision_pass": expected_pass}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
