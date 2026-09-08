#!/usr/bin/env python3
"""Run the current-contract equal-occupation objective companion."""
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
DRAWS = 9_999
SEED = 202609088101
EXPECTED_POOLED = -0.13210945079219025
EXPECTED_FAMILY = -0.021674952018246537


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


MAP = load_module("yax_equal_occupation_mapping_helpers",
                  HERE.parent / "mapping" / "run_mapping_sensitivity.py")
CORE = MAP.CORE


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


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def equal_occupation_cells(young: np.ndarray, older: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    total = np.asarray(young, float) + np.asarray(older, float)
    positive = total > 0
    positive_months = positive.sum(axis=1)
    require(np.all(positive_months > 0), "an occupation has no positive-employment month")
    objective_total = np.where(positive, (1.0 / positive_months)[:, None], 0.0)
    share = np.divide(young, total, out=np.zeros_like(total), where=positive)
    objective_young = objective_total * share
    objective_older = objective_total * (1.0 - share)
    require(np.max(np.abs(objective_total.sum(axis=1) - 1.0)) <= 1e-12,
            "equal occupation objective weights do not sum to one")
    return objective_young, objective_older, objective_total


def paired_row(left: dict[str, Any], right: dict[str, Any],
               multipliers: dict[str, np.ndarray], structure: str) -> dict[str, Any]:
    estimate = (left["row"]["coefficient_Q5_x_post"] -
                right["row"]["coefficient_Q5_x_post"])
    occupation_influence = left["occupation_influence"] - right["occupation_influence"]
    family_influence = left["family_influence"] - right["family_influence"]
    occ = CORE.multiplier_interval(estimate, occupation_influence,
                                   multipliers["occupation"])
    fam = CORE.multiplier_interval(estimate, family_influence,
                                   multipliers["family"])
    return {
        "comparison_id": f"equal_occupation_minus_stock_{structure}",
        "structure": structure,
        "left_model": left["row"]["model_id"], "right_model": right["row"]["model_id"],
        "estimate_left_minus_right": estimate,
        "occupation_se": occ["se"], "occupation_ci_lower": occ["lower"],
        "occupation_ci_upper": occ["upper"], "occupation_multiplier_p": occ["p_value"],
        "family_se": fam["se"], "family_ci_lower": fam["lower"],
        "family_ci_upper": fam["upper"], "family_multiplier_p": fam["p_value"],
        "common_draws_preserve_covariance": True,
        "interpretation_if_interval_contains_zero":
            "design does not detect a difference; not equivalence",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-calibration", type=Path, required=True)
    parser.add_argument("--calibration-receipt", type=Path, required=True)
    parser.add_argument("--membership", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output_dir.exists(), "refusing to overwrite equal-occupation output")
    require(sha256_file(args.membership) == MAP.MEMBERSHIP_SHA256,
            "membership hash differs")
    receipt = json.loads(args.calibration_receipt.read_text(encoding="utf-8"))
    require(receipt.get("status") == "PASS_PRIVATE_CALIBRATION_BUILD",
            "private calibration receipt does not pass")
    require(sha256_file(args.private_calibration) == receipt.get("private_npz_sha256"),
            "private calibration hash differs")
    with np.load(args.private_calibration, allow_pickle=False) as loaded:
        arrays = {name: loaded[name] for name in loaded.files}
    occupations = arrays["occupations"].astype(str)
    families = arrays["families"].astype(str)
    months = arrays["months"].astype(str).tolist()
    require(len(occupations) == 468 and len(months) == 113,
            "protected contract dimensions differ")
    n_cell = len(occupations) * len(months)
    by_age = np.bincount(arrays["cellage"], weights=arrays["route_stock"],
                         minlength=2 * n_cell)
    young = by_age[:n_cell].reshape(len(occupations), len(months))
    older = by_age[n_cell:].reshape(len(occupations), len(months))
    require(np.allclose((young + older).reshape(-1), arrays["total"], rtol=0, atol=1e-7),
            "protected age stocks do not reproduce totals")
    membership = pd.read_csv(args.membership, dtype={"occupation_code": str},
                             float_precision="round_trip")
    membership["occupation_code"] = membership.occupation_code.str.zfill(4)
    membership = membership.set_index("occupation_code").reindex(occupations)
    require(not membership.isna().any().any(), "membership does not align")
    quintiles = membership.beta_quintile.to_numpy(int)
    webb_z = membership.webb_z.to_numpy(float)
    require(np.array_equal(quintiles, arrays["quintiles"]), "quintiles differ")
    require(np.allclose(webb_z, arrays["webb_z"], rtol=0, atol=1e-12),
            "Webb normalization differs")
    equal_young, equal_older, objective_weight = equal_occupation_cells(young, older)
    global_families = sorted(set(families.tolist()))
    draws = CORE.draw_multiplier_matrices(DRAWS, len(occupations), len(global_families), SEED)
    multipliers = {"occupation": draws["occupation_rademacher"],
                   "family": draws["family_rademacher"]}
    all_keep = np.ones(len(occupations), bool)
    models: dict[str, dict[str, Any]] = {}
    model_rows: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    try:
        for objective, y_value, o_value in (
            ("employment_stock_weighted", young, older),
            ("equal_occupation", equal_young, equal_older),
        ):
            for structure in ("pooled", "family_month"):
                model_id = f"{objective}_{structure}"
                model = MAP.fit_model(
                    model_id, structure, y_value, o_value, all_keep, quintiles, webb_z,
                    families, occupations, months, multipliers,
                    {"objective": objective,
                     "changed_estimand": objective == "equal_occupation",
                     "WTFINL_retained_in_within_cell_share": True})
                models[model_id] = model
                model_rows.append(model["row"])
    except Exception as error:
        failures.append({"error": repr(error)})
        raise
    require(abs(models["employment_stock_weighted_pooled"]["row"]["coefficient_Q5_x_post"]
                - EXPECTED_POOLED) <= 1e-8, "pooled stock objective does not reproduce")
    require(abs(models["employment_stock_weighted_family_month"]["row"]["coefficient_Q5_x_post"]
                - EXPECTED_FAMILY) <= 1e-8, "family stock objective does not reproduce")
    pair_rows = [
        paired_row(models[f"equal_occupation_{structure}"],
                   models[f"employment_stock_weighted_{structure}"],
                   multipliers, structure)
        for structure in ("pooled", "family_month")
    ]
    weight_rows = []
    stock_total = young + older
    for index, code in enumerate(occupations):
        positive = stock_total[index] > 0
        weight_rows.append({
            "occupation_code": code,
            "occupation_name": membership.occupation_name.iloc[index],
            "positive_employment_months": int(positive.sum()),
            "equal_objective_weight_sum": float(objective_weight[index].sum()),
            "minimum_positive_month_weight": float(objective_weight[index, positive].min()),
            "maximum_positive_month_weight": float(objective_weight[index, positive].max()),
            "employment_stock_sum": float(stock_total[index].sum()),
            "WTFINL_retained_in_within_cell_share": True,
        })
    influence_rows: list[dict[str, Any]] = []
    for model in models.values():
        for code, value in zip(occupations, model["occupation_influence"]):
            influence_rows.append({"model_id": model["row"]["model_id"],
                                   "cluster_type": "occupation", "cluster_id": code,
                                   "target_influence": float(value)})
        for code, value in zip(global_families, model["family_influence"]):
            influence_rows.append({"model_id": model["row"]["model_id"],
                                   "cluster_type": "family", "cluster_id": code,
                                   "target_influence": float(value)})
    args.output_dir.mkdir(parents=True)
    outputs = {
        "MODEL_RESULTS.csv": model_rows,
        "PAIRED_COMPARISONS.csv": pair_rows,
        "OBJECTIVE_WEIGHTS.csv": weight_rows,
        "MODEL_INFLUENCE.csv": influence_rows,
    }
    for name, rows in outputs.items():
        write_csv(args.output_dir / name, rows)
    write_json(args.output_dir / "MODEL_FAILURES.json", failures)
    output_names = [*outputs, "MODEL_FAILURES.json"]
    run_receipt = {
        "schema_version": "yax-gate3-equal-occupation-v1",
        "status": "PASS_GATE3_EQUAL_OCCUPATION",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                              text=True).strip(),
        "sge_job_id": os.environ.get("JOB_ID"),
        "input_hashes": {
            "private_calibration": sha256_file(args.private_calibration),
            "calibration_receipt": sha256_file(args.calibration_receipt),
            "membership": sha256_file(args.membership),
            "specification": sha256_file(HERE / "EQUAL_OCCUPATION_SPEC.md"),
            "runner": sha256_file(Path(__file__)),
        },
        "canonical_identity": {
            "support_occupations": len(occupations), "analysis_months": len(months),
            "pooled": models["employment_stock_weighted_pooled"]["row"]["coefficient_Q5_x_post"],
            "family_month":
                models["employment_stock_weighted_family_month"]["row"]["coefficient_Q5_x_post"],
        },
        "equal_objective_weight_maximum_absolute_sum_gap": float(
            np.max(np.abs(objective_weight.sum(axis=1) - 1.0))),
        "WTFINL_removed": False,
        "WTFINL_role": "constructs within-occupation-month employment shares",
        "model_count": len(model_rows), "paired_comparison_count": len(pair_rows),
        "model_failure_count": len(failures), "draws": DRAWS, "seed": SEED,
        "common_draws_across_objectives": True,
        "protected_microdata_or_identifiers_written": False,
        "output_hashes": {name: sha256_file(args.output_dir / name) for name in output_names},
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", run_receipt)
    print(json.dumps({"status": run_receipt["status"], "models": len(model_rows),
                      "pairs": len(pair_rows)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
