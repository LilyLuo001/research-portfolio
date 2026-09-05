#!/usr/bin/env python3
"""Run the two authorized fixed-treatment YAX V5.1 LOCO influence loops."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import pathlib
import sys

import numpy as np


HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P3 = import_path("yax_v51_final_phase3", ROOT / "yax/analysis/postoutcome_phase3_final/run_phase3.py")
V4 = P3.V4
FROZEN = P3.FROZEN
V51 = import_path("yax_v51_final_v51", ROOT / "yax/analysis/postoutcome_v51_referee_repair/run_v51_repairs.py")

LABEL = "POST-OUTCOME FIXED-TREATMENT LOCO INFLUENCE AUDIT"
PARENT = "e9ba86a6e51e4045940ee244bd394b0111b71a02"
PRIMARY_EXPECTED = -0.13107397642233506
G_EXPECTED = 0.030893508600474132
COMMON_HASH = "1e184b27678b7978d4b15e618db5b44f44b5e9ec1b50b69b53093ec62e0ce462"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def support_hash(codes: list[str]) -> str:
    return hashlib.sha256("".join(f"{code}\n" for code in sorted(codes)).encode()).hexdigest()


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError("refusing to write empty LOCO output")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fit_point(young: np.ndarray, older: np.ndarray, regressors: np.ndarray, target: int) -> float:
    n_occ, n_month = young.shape
    total = (young + older).reshape(-1)
    occupation = np.repeat(np.arange(n_occ), n_month)
    month = np.tile(np.arange(n_month), n_occ)
    fit = FROZEN.ENGINE.fit_grouped_logit_fe(
        young.reshape(-1), total, occupation, month, regressors, max_iterations=5000
    )
    if not fit.converged:
        raise RuntimeError("LOCO grouped-binomial fit did not converge")
    value = float(fit.beta[target])
    if not np.isfinite(value):
        raise RuntimeError("LOCO target coefficient is non-finite")
    return value


def delete_occupation(
    young: np.ndarray,
    older: np.ndarray,
    regressors: np.ndarray,
    index: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n_occ, n_month = young.shape
    if regressors.shape[0] != n_occ * n_month:
        raise ValueError("regressor rows do not match frozen occupation-month panel")
    cube = regressors.reshape(n_occ, n_month, regressors.shape[1])
    keep = np.arange(n_occ) != index
    return young[keep], older[keep], cube[keep].reshape((n_occ - 1) * n_month, regressors.shape[1])


def loco_rows(
    target_name: str,
    occupations: list[str],
    names: dict[str, str],
    young: np.ndarray,
    older: np.ndarray,
    regressors: np.ndarray,
    target: int,
    full_estimate: float,
) -> list[dict]:
    weights = (young + older).sum(axis=1)
    rows = []
    for deletion_order, code in enumerate(occupations, start=1):
        y, o, x = delete_occupation(young, older, regressors, deletion_order - 1)
        estimate = fit_point(y, o, x, target)
        movement = estimate - full_estimate
        rows.append({
            "analysis_status": LABEL,
            "target": target_name,
            "deletion_order": deletion_order,
            "deleted_census2018": code,
            "deleted_occupation": names.get(code, ""),
            "frozen_full_estimate": full_estimate,
            "leave_one_out_estimate": estimate,
            "signed_movement": movement,
            "absolute_movement": abs(movement),
            "relative_absolute_movement": abs(movement) / abs(full_estimate),
            "deleted_full_sample_stock_weight": float(weights[deletion_order - 1]),
            "deleted_full_sample_stock_weight_share": float(weights[deletion_order - 1] / weights.sum()),
            "sign_changed": bool(np.sign(estimate) != np.sign(full_estimate)),
            "crossed_or_reached_zero": bool(estimate * full_estimate <= 0),
            "treatment_recomputed_after_deletion": False,
        })
    return rows


def weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    index = min(int(np.searchsorted(cumulative, q * cumulative[-1], side="left")), len(values) - 1)
    return float(values[order[index]])


def summarize(rows: list[dict]) -> dict:
    estimate = np.array([row["leave_one_out_estimate"] for row in rows], float)
    movement = np.array([row["signed_movement"] for row in rows], float)
    absolute = np.abs(movement)
    weights = np.array([row["deleted_full_sample_stock_weight"] for row in rows], float)
    order = np.argsort(-absolute, kind="mergesort")
    quantiles = {
        str(q): weighted_quantile(movement, weights, q)
        for q in (0.0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1.0)
    }
    return {
        "full_estimate": rows[0]["frozen_full_estimate"],
        "deletions": len(rows),
        "minimum_leave_one_out_estimate": float(estimate.min()),
        "maximum_leave_one_out_estimate": float(estimate.max()),
        "maximum_absolute_movement": float(absolute.max()),
        "maximum_relative_movement": float(max(row["relative_absolute_movement"] for row in rows)),
        "sign_changes": int(sum(row["sign_changed"] for row in rows)),
        "crossed_or_reached_zero": int(sum(row["crossed_or_reached_zero"] for row in rows)),
        "crossed_or_reached_zero_fraction": float(np.mean([row["crossed_or_reached_zero"] for row in rows])),
        "weighted_signed_movement_quantiles": quantiles,
        "top_ten": [rows[index] for index in order[:10]],
    }


def frozen_primary(data: dict) -> dict:
    prepared = FROZEN.prepare_model(
        data["panel"], sorted(data["occupations"]), data["static_months"],
        data["exposures"]["dv_rating_beta"]["A"], data["computers"]["webb_pct_software"],
        scale="q5_q1",
    )
    if len(prepared["occupations"]) != 468 or prepared["target"] != 3:
        raise RuntimeError("primary frozen support or target changed")
    full = fit_point(prepared["young"], prepared["older"], prepared["regressors"], prepared["target"])
    if not np.isclose(full, PRIMARY_EXPECTED, atol=1e-10, rtol=0):
        raise RuntimeError(f"primary sealed estimate failed to reproduce: {full}")
    return {**prepared, "full_estimate": full}


def frozen_g(data: dict, reference) -> dict:
    common = V51.common_stock_support(data)
    if len(common) != 444 or support_hash(common) != COMMON_HASH:
        raise RuntimeError("literal common support changed")
    indexed = reference.set_index("census2018")
    young, older = FROZEN.panel_arrays(data["panel"], common, data["static_months"])
    weights = (young + older).sum(axis=1)
    raw = {
        "F": indexed.loc[common, "F"].to_numpy(float),
        "G": indexed.loc[common, "G"].to_numpy(float),
        "Webb": np.array([data["computers"]["webb_pct_software"][code] for code in common], float),
    }
    scale = {name: V51.CORE.weighted_mean_sd(values, weights) for name, values in raw.items()}
    frozen_scale = json.loads((ROOT / "yax/analysis/postoutcome_v51_referee_repair/YAX_V51_FG_JOINT_MODEL_RESULTS.json").read_text())["component_scaling"]
    for name in raw:
        if not np.isclose(scale[name][0], frozen_scale[name]["weighted_mean"], atol=1e-12, rtol=0):
            raise RuntimeError(f"{name} frozen mean changed")
        if not np.isclose(scale[name][1], frozen_scale[name]["weighted_sd"], atol=1e-12, rtol=0):
            raise RuntimeError(f"{name} frozen SD changed")
    z = {name: (raw[name] - scale[name][0]) / scale[name][1] for name in raw}
    post = np.array([month >= "2023-01" for month in data["static_months"]])
    regressors = np.column_stack([
        (z[name][:, None] * post[None, :]).reshape(-1) for name in ("F", "G", "Webb")
    ])
    full = fit_point(young, older, regressors, 1)
    if not np.isclose(full, G_EXPECTED, atol=1e-10, rtol=0):
        raise RuntimeError(f"G sealed estimate failed to reproduce: {full}")
    return {
        "occupations": common,
        "young": young,
        "older": older,
        "regressors": regressors,
        "target": 1,
        "full_estimate": full,
        "scaling": {name: {"mean": scale[name][0], "sd": scale[name][1]} for name in scale},
    }


def run(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = V4.load_inputs(args)
    reference, _ = P3.load_reference_components(args.characteristics)
    primary = frozen_primary(data)
    g = frozen_g(data, reference)
    primary_rows = loco_rows(
        "primary_beta_webb_q5_q1", primary["occupations"], data["names"],
        primary["young"], primary["older"], primary["regressors"],
        primary["target"], primary["full_estimate"],
    )
    g_rows = loco_rows(
        "joint_F_G_between_family_G", g["occupations"], data["names"],
        g["young"], g["older"], g["regressors"], g["target"], g["full_estimate"],
    )
    write_csv(args.output_dir / "YAX_V51_LOCO_PRIMARY.csv", primary_rows)
    write_csv(args.output_dir / "YAX_V51_LOCO_G.csv", g_rows)
    result = {
        "record": "YAX V5.1 two-target fixed-treatment delete-one-occupation influence audit",
        "analysis_status": LABEL,
        "parent_commit": PARENT,
        "input_hashes": data["authenticated"]["hashes"],
        "deletion_order": "lexicographically sorted Census-2018 occupation codes",
        "treatment_recomputed_after_deletion": False,
        "new_labor_outcome_specification_estimated": False,
        "new_bootstrap_multipliers_generated": False,
        "leave_one_measure_out_labor_outcome_model_executed": False,
        "primary": summarize(primary_rows),
        "G": summarize(g_rows),
        "G_scaling": g["scaling"],
        "output_hashes": {
            "YAX_V51_LOCO_PRIMARY.csv": sha256(args.output_dir / "YAX_V51_LOCO_PRIMARY.csv"),
            "YAX_V51_LOCO_G.csv": sha256(args.output_dir / "YAX_V51_LOCO_G.csv"),
        },
    }
    write_json(args.output_dir / "YAX_V51_LOCO_RESULTS.json", result)
    print(json.dumps({
        "status": "PASS_TWO_TARGET_FIXED_TREATMENT_LOCO",
        "primary": result["primary"],
        "G": result["G"],
    }, indent=2))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    value.add_argument("--lookup", type=pathlib.Path, default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    value.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    value.add_argument("--rule-b-values", type=pathlib.Path, default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    value.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    value.add_argument("--first-access-receipt", type=pathlib.Path, default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    value.add_argument("--characteristics", type=pathlib.Path, default=ROOT / "yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv")
    value.add_argument("--output-dir", type=pathlib.Path, default=HERE)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
