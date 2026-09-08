#!/usr/bin/env python3
"""Run the deterministic two-fold household shortfall bias diagnostic."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SPLIT_SEED = 202609084900
BRIDGE_SHA256 = "0bd2f63c72e24bed2cc1cb414395c3cbddf7c00011e47ec1c1de6ae534fd1dcc"
CONTROLS = ("total", "young_relative")
TARGETS = ("pooled", "family_month", "family_month_minus_pooled")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BATCH = load_module("yax_shortfall_batch_for_crossfit", HERE / "run_shortfall_refit_batch.py")
SHORT = BATCH.SHORT
HH = BATCH.HH


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


def standardized(raw: dict[str, Any], support: np.ndarray) -> tuple[dict[str, np.ndarray],
                                                                      dict[str, dict[str, float]]]:
    z: dict[str, np.ndarray] = {}
    scaling: dict[str, dict[str, float]] = {}
    for control in CONTROLS:
        z[control], scaling[control] = SHORT.weighted_standardize(
            raw[control], raw["pre_weight"], support)
    return z, scaling


def flatten_results(sample: str, fitted: dict[str, dict[str, Any]],
                    scaling: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for control in CONTROLS:
        for target in TARGETS:
            baseline = fitted["baseline"][target]
            augmented = fitted[control][target]
            rows.append({
                "sample": sample,
                "control": control,
                "target": target,
                "baseline_q5": baseline["q5"],
                "augmented_q5": augmented["q5"],
                "conditioning_movement": augmented["q5"] - baseline["q5"],
                "shortfall_z_coefficient": augmented["shortfall_z"],
                "shortfall_raw_coefficient": (
                    augmented["shortfall_z"] / scaling[control]["weighted_sd"]),
            })
    return rows


def average_directions(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index = {(row["control"], row["target"]): row for row in right}
    result: list[dict[str, Any]] = []
    for row in left:
        other = index[(row["control"], row["target"])]
        averaged = {"sample": "equal_weight_crossfit_average",
                    "control": row["control"], "target": row["target"]}
        for name in ("baseline_q5", "augmented_q5", "conditioning_movement",
                     "shortfall_z_coefficient", "shortfall_raw_coefficient"):
            averaged[name] = .5 * (float(row[name]) + float(other[name]))
        result.append(averaged)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-calibration", type=Path, required=True)
    parser.add_argument("--calibration-receipt", type=Path, required=True)
    parser.add_argument("--bridge", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.exists(), "refusing to overwrite shortfall cross-fit output")
    receipt = json.loads(args.calibration_receipt.read_text(encoding="utf-8"))
    require(receipt.get("status") == "PASS_PRIVATE_CALIBRATION_BUILD",
            "calibration receipt does not pass")
    require(receipt.get("private_npz_sha256") == sha256_file(args.private_calibration),
            "private calibration hash differs")
    require(sha256_file(args.bridge) == BRIDGE_SHA256, "occupation bridge hash differs")
    bridge = pd.read_csv(args.bridge, dtype=str)
    with np.load(args.private_calibration, allow_pickle=False) as loaded:
        arrays = {name: loaded[name] for name in loaded.files}
    n_occ, n_month = len(arrays["occupations"]), len(arrays["months"])
    household_count = int(arrays["household_count"][0])
    require(household_count == receipt["route_counts"]["analysis_contributing_CPSID_units"],
            "household count differs")
    require(len(arrays["household_code"]) == len(arrays["cellage"])
            == len(arrays["route_stock"]), "household route arrays differ")

    rng = np.random.default_rng(SPLIT_SEED)
    permutation = rng.permutation(household_count)
    fold = np.empty(household_count, dtype=np.int8)
    fold[permutation[:household_count // 2]] = 0
    fold[permutation[household_count // 2:]] = 1
    multipliers = [(fold == value).astype(float) for value in (0, 1)]
    cells = []
    for multiplier in multipliers:
        young, older = HH.cells_from_multiplier(arrays, multiplier)
        cells.append((young.reshape(n_occ, n_month), older.reshape(n_occ, n_month)))
    full_young = cells[0][0] + cells[1][0]
    full_older = cells[0][1] + cells[1][1]
    structural = SHORT.one_to_one_mask(arrays["occupations"], bridge)
    raw = [SHORT.corrected_shortfalls(young, older, arrays["months"].tolist())
           for young, older in cells]
    full_raw = SHORT.corrected_shortfalls(
        full_young, full_older, arrays["months"].tolist())
    support = structural & raw[0]["finite_support"] & raw[1]["finite_support"]
    require(np.all(full_raw["finite_support"][support]),
            "cross-fit support is not finite in the full sample")
    require(int(support.sum()) >= 250, "cross-fit common support is too small")
    z = []
    scaling = []
    for value in raw:
        current_z, current_scaling = standardized(value, support)
        z.append(current_z)
        scaling.append(current_scaling)
    full_z, full_scaling = standardized(full_raw, support)

    common = (arrays["quintiles"], arrays["webb_z"])
    full_fitted = BATCH.fit_collection(
        full_young, full_older, arrays, support, *common, full_z)
    direction_01 = BATCH.fit_collection(
        cells[1][0], cells[1][1], arrays, support, *common, z[0])
    direction_10 = BATCH.fit_collection(
        cells[0][0], cells[0][1], arrays, support, *common, z[1])
    full_rows = flatten_results("full_in_sample_same_support", full_fitted, full_scaling)
    rows_01 = flatten_results("construct_fold0_estimate_fold1", direction_01, scaling[0])
    rows_10 = flatten_results("construct_fold1_estimate_fold0", direction_10, scaling[1])
    average_rows = average_directions(rows_01, rows_10)
    reference = {(row["control"], row["target"]): row for row in full_rows}
    for row in rows_01 + rows_10 + average_rows:
        base = reference[(row["control"], row["target"])]
        row["conditioning_movement_minus_full_in_sample"] = (
            row["conditioning_movement"] - base["conditioning_movement"])
        row["augmented_q5_minus_full_in_sample"] = (
            row["augmented_q5"] - base["augmented_q5"])
    for row in full_rows:
        row["conditioning_movement_minus_full_in_sample"] = 0.0
        row["augmented_q5_minus_full_in_sample"] = 0.0

    construction = {
        "schema_version": "yax-gate3-shortfall-crossfit-construction-v1",
        "split_seed": SPLIT_SEED,
        "split_unit": "encoded positive CPSID; all months, co-residents, and route descendants remain together",
        "households": household_count,
        "fold_households": [int(np.sum(fold == value)) for value in (0, 1)],
        "common_support_occupations": int(support.sum()),
        "structural_one_to_one_occupations": int(structural.sum()),
        "fold_preperiod_weights": [float(value["pre_weight"][support].sum()) for value in raw],
        "full_preperiod_weight": float(full_raw["pre_weight"][support].sum()),
        "fold_scaling": scaling,
        "full_scaling": full_scaling,
        "fold_total_negative_predictions_before_bound": [
            int(value["total_negative_predictions_before_bound"][support].sum())
            for value in raw
        ],
        "fold_share_out_of_bounds_predictions_before_bound": [
            int(value["share_out_of_bounds_predictions_before_bound"][support].sum())
            for value in raw
        ],
        "interpretation": (
            "descriptive two-direction household split diagnostic for shared first- and "
            "second-stage error; not CPS design-based inference"
        ),
    }
    args.output_dir.mkdir(parents=True)
    result_path = args.output_dir / "SHORTFALL_CROSSFIT_RESULTS.csv"
    construction_path = args.output_dir / "SHORTFALL_CROSSFIT_CONSTRUCTION.json"
    write_csv(result_path, full_rows + rows_01 + rows_10 + average_rows)
    construction_path.write_text(
        json.dumps(construction, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output_hashes = {
        result_path.name: sha256_file(result_path),
        construction_path.name: sha256_file(construction_path),
    }
    output_receipt = {
        "schema_version": "yax-gate3-shortfall-crossfit-receipt-v1",
        "status": "PASS_SHORTFALL_HOUSEHOLD_SPLIT_DIAGNOSTIC",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"],
                                             cwd=ROOT, text=True).strip(),
        "sge_job_id": os.environ.get("JOB_ID"),
        "private_calibration_sha256": receipt["private_npz_sha256"],
        "calibration_receipt_sha256": sha256_file(args.calibration_receipt),
        "bridge_sha256": sha256_file(args.bridge),
        "support_occupations": int(support.sum()),
        "result_rows": len(full_rows + rows_01 + rows_10 + average_rows),
        "output_hashes": output_hashes,
        "privacy": "outputs contain coefficients and aggregate diagnostics only",
    }
    (args.output_dir / "EXECUTION_RECEIPT.json").write_text(
        json.dumps(output_receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": output_receipt["status"],
                      "support_occupations": int(support.sum())}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
