#!/usr/bin/env python3
"""Run R3 SOC2 few-cluster and corrected time-HAC sensitivities.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
SEED = 2026090541
DRAWS = 99999
LAGS = (0, 1, 4, 12, 16)
Z975 = 1.959963984540054
Z80 = 0.8416212335729143


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CORE = import_path("yax_r3_dep_core", ROOT / "yax/revision/referee_20260905/run_referee_core.py")
CELLS = import_path("yax_r3_dep_cells", ROOT / "yax/revision/referee_20260905/run_referee_cells.py")
COMP = import_path(
    "yax_r3_dep_composition",
    ROOT / "yax/revision/referee_round2_20260905/composition_influence/run_composition_influence.py",
)
FROZEN = CORE.FROZEN


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty output {path}")
    fields: list[str] = []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: pathlib.Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def month_number(value: str) -> int:
    return int(value[:4]) * 12 + int(value[5:7]) - 1


def complete_calendar(months: list[str]) -> tuple[list[str], np.ndarray]:
    start, end = month_number(months[0]), month_number(months[-1])
    full = [f"{number // 12:04d}-{number % 12 + 1:02d}" for number in range(start, end + 1)]
    lookup = {month: index for index, month in enumerate(full)}
    return full, np.array([lookup[month] for month in months], int)


def newey_west(values: np.ndarray, lag: int) -> np.ndarray:
    """Unnormalized Bartlett HAC meat for a T by K score array."""
    meat = values.T @ values
    for ell in range(1, lag + 1):
        weight = 1.0 - ell / (lag + 1.0)
        gamma = values[ell:].T @ values[:-ell]
        meat += weight * (gamma + gamma.T)
    return meat


def row_influence_cube(fit, details: dict, n_occ: int, n_month: int) -> np.ndarray:
    residual = details["y"] - details["total"] * fit.fitted_probability
    row_scores = details["rx"] * residual[:, None]
    bread = np.linalg.inv(details["information"])
    row_influence = row_scores @ bread.T
    cube = np.zeros((n_occ, n_month, row_influence.shape[1]))
    np.add.at(cube, (details["occupation"], details["second"]), row_influence)
    return cube


def covariance_components(cube: np.ndarray, months: list[str], lag: int) -> dict:
    n_occ, n_month, n_parameter = cube.shape
    full_months, positions = complete_calendar(months)
    full = np.zeros((n_occ, len(full_months), n_parameter))
    full[:, positions, :] = cube
    occupation_scores = full.sum(axis=1)
    aggregate_time_scores = full.sum(axis=0)
    occupation_meat = occupation_scores.T @ occupation_scores
    time_meat = newey_west(aggregate_time_scores, lag)
    overlap_meat = np.zeros_like(occupation_meat)
    for occupation in range(n_occ):
        overlap_meat += newey_west(full[occupation], lag)
    combined = occupation_meat + time_meat - overlap_meat
    combined = (combined + combined.T) / 2
    finite = n_occ / (n_occ - 1) * combined
    return {
        "full_calendar_months": full_months,
        "observed_positions": positions,
        "occupation_meat": occupation_meat,
        "time_meat": time_meat,
        "overlap_meat": overlap_meat,
        "combined": combined,
        "finite": finite,
    }


def fit_models(data: dict, args: argparse.Namespace):
    exposure = data["exposures"]["dv_rating_beta"]["A"]
    webb = data["computers"]["webb_pct_software"]
    prepared = FROZEN.prepare_model(
        data["panel"], data["occupations"], data["static_months"], exposure, webb, scale="q5_q1"
    )
    support = list(prepared["occupations"])
    cells, _, cell_receipt = CELLS.build_exact_age_cells(args)
    months = [month for month in sorted(cells.month.unique()) if month != "2022-12"]
    if len(support) != 468 or len(months) != 113:
        raise RuntimeError(f"unexpected support/calendar: {len(support)}, {len(months)}")
    young, older = CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65))
    values = np.array([exposure[code] for code in support], float)
    quintiles = FROZEN.weighted_quintiles(values, prepared["weights"])
    webb_values = np.array([webb[code] for code in support], float)
    webb_mean, webb_sd = FROZEN.weighted_scale(webb_values, prepared["weights"])
    webb_z = (webb_values - webb_mean) / webb_sd
    post = np.array([month >= "2023-01" for month in months])
    base_x = np.column_stack([
        *[(((quintiles == q)[:, None]) & post[None, :]).reshape(-1).astype(float) for q in (2, 3, 4, 5)],
        (webb_z[:, None] * post[None, :]).reshape(-1),
    ])
    month_fe = np.tile(np.arange(len(months)), len(support))
    base_fit, _, base_details = COMP.fit_absorbed(young, older, base_x, month_fe)
    base_cube = row_influence_cube(base_fit, base_details, len(support), len(months))

    _, _, major_map = FROZEN.comp_maps(args.computerization)
    majors = np.array([major_map.get(code, "MISSING") for code in support], object)
    levels = sorted(set(majors.tolist()))
    totals = {level: float(prepared["weights"][majors == level].sum()) for level in levels}
    reference = max(levels, key=lambda level: (totals[level], level))
    group_columns = [
        (((majors == level)[:, None]) & post[None, :]).reshape(-1).astype(float)
        for level in levels if level != reference
    ]
    conditional_x = np.column_stack([base_x, *group_columns])
    conditional_fit, _, conditional_details = COMP.fit_absorbed(
        young, older, conditional_x, month_fe
    )
    conditional_cube = row_influence_cube(
        conditional_fit, conditional_details, len(support), len(months)
    )
    return {
        "support": support,
        "months": months,
        "majors": majors,
        "major_levels": levels,
        "major_reference": reference,
        "base_fit": base_fit,
        "base_details": base_details,
        "base_cube": base_cube,
        "conditional_fit": conditional_fit,
        "conditional_details": conditional_details,
        "conditional_cube": conditional_cube,
        "cell_receipt": cell_receipt,
    }


def dependence_rows(objects: dict) -> tuple[list[dict], list[dict]]:
    support, months = objects["support"], objects["months"]
    targets = {
        "corrected_baseline": {
            "estimate": float(objects["base_fit"].beta[3]),
            "cube": objects["base_cube"],
            "target": 3,
            "reported_occupation_se": float(objects["base_fit"].standard_error[3]),
        },
        "SOC2_post_conditioned": {
            "estimate": float(objects["conditional_fit"].beta[3]),
            "cube": objects["conditional_cube"],
            "target": 3,
            "reported_occupation_se": float(objects["conditional_fit"].standard_error[3]),
        },
    }
    delta_cube = (
        objects["conditional_cube"][:, :, 3:4] - objects["base_cube"][:, :, 3:4]
    )
    targets["conditioned_minus_baseline"] = {
        "estimate": targets["SOC2_post_conditioned"]["estimate"] - targets["corrected_baseline"]["estimate"],
        "cube": delta_cube,
        "target": 0,
        "reported_occupation_se": float("nan"),
    }
    rows, conservation = [], []
    for name, item in targets.items():
        cube, target = item["cube"], item["target"]
        occupation_contributions = cube[:, :, target].sum(axis=1)
        occupation_se = math.sqrt(
            len(support) / (len(support) - 1) * float(np.sum(np.square(occupation_contributions)))
        )
        conservation.append({
            "object": name,
            "estimate": item["estimate"],
            "sum_cell_influence": float(cube[:, :, target].sum()),
            "occupation_cluster_se_rebuilt": occupation_se,
            "engine_reported_occupation_cluster_se": item["reported_occupation_se"],
            "absolute_se_difference": (
                abs(occupation_se - item["reported_occupation_se"])
                if np.isfinite(item["reported_occupation_se"]) else ""
            ),
        })
        for lag in LAGS:
            components = covariance_components(cube, months, lag)
            combined = components["combined"]
            finite = components["finite"]
            target_variance = float(finite[target, target])
            se = math.sqrt(target_variance) if target_variance >= 0 else float("nan")
            eigenvalues = np.linalg.eigvalsh(finite)
            rows.append({
                "analysis_status": LABEL,
                "object": name,
                "lag_elapsed_calendar_months": lag,
                "estimate": item["estimate"],
                "occupation_cluster_se_rebuilt": occupation_se,
                "corrected_inclusion_exclusion_se": se,
                "normal_ci_lower": item["estimate"] - Z975 * se if np.isfinite(se) else "",
                "normal_ci_upper": item["estimate"] + Z975 * se if np.isfinite(se) else "",
                "normal_theory_mde80": (Z975 + Z80) * se if np.isfinite(se) else "",
                "occupation_meat_target": float(components["occupation_meat"][target, target]),
                "aggregate_time_HAC_meat_target": float(components["time_meat"][target, target]),
                "within_occupation_HAC_overlap_target": float(components["overlap_meat"][target, target]),
                "combined_meat_target_before_common_factor": float(combined[target, target]),
                "common_finite_factor": len(support) / (len(support) - 1),
                "full_calendar_months": len(components["full_calendar_months"]),
                "observed_model_months": len(months),
                "zero_placeholder_months": len(components["full_calendar_months"]) - len(months),
                "minimum_covariance_eigenvalue": float(eigenvalues.min()),
                "negative_covariance_eigenvalues": int(np.sum(eigenvalues < -1e-12)),
                "PSD_projection_applied": False,
            })
    return rows, conservation


def few_cluster_rows(objects: dict) -> list[dict]:
    levels = objects["major_levels"]
    group_index = {value: index for index, value in enumerate(levels)}
    group = np.array([group_index[value] for value in objects["majors"]], int)
    base_occ = objects["base_cube"][:, :, 3].sum(axis=1)
    conditional_occ = objects["conditional_cube"][:, :, 3].sum(axis=1)
    target_objects = {
        "corrected_baseline": (float(objects["base_fit"].beta[3]), base_occ),
        "SOC2_post_conditioned": (float(objects["conditional_fit"].beta[3]), conditional_occ),
        "conditioned_minus_baseline": (
            float(objects["conditional_fit"].beta[3] - objects["base_fit"].beta[3]),
            conditional_occ - base_occ,
        ),
    }
    rng = np.random.default_rng(SEED)
    rademacher = rng.choice(np.array([-1.0, 1.0]), size=(DRAWS, len(levels)))
    webb_values = np.array([
        -math.sqrt(1.5), -1.0, -math.sqrt(0.5),
        math.sqrt(0.5), 1.0, math.sqrt(1.5),
    ])
    webb = rng.choice(webb_values, size=(DRAWS, len(levels)))
    rows = []
    for name, (estimate, occupation_scores) in target_objects.items():
        family_scores = np.zeros(len(levels))
        np.add.at(family_scores, group, occupation_scores)
        crv1_variance = len(levels) / (len(levels) - 1) * float(np.sum(np.square(family_scores)))
        se = math.sqrt(crv1_variance)
        for distribution, weights in (("Rademacher", rademacher), ("Webb_six_point", webb)):
            shifts = weights @ family_scores
            statistics = np.abs(shifts / se)
            observed = abs(estimate / se)
            pvalue = float((1 + np.sum(statistics >= observed)) / (DRAWS + 1))
            critical = float(np.quantile(statistics, .95, method="higher"))
            rows.append({
                "analysis_status": LABEL,
                "object": name,
                "SOC2_clusters": len(levels),
                "SOC2_cluster_labels_json": json.dumps(levels),
                "estimate": estimate,
                "SOC2_CRV1_se": se,
                "wild_weight_distribution": distribution,
                "wild_score_draws": DRAWS,
                "wild_score_seed": SEED,
                "fixed_studentizer": "SOC2_CRV1_se",
                "wild_score_p_value": pvalue,
                "p_value_monte_carlo_se": math.sqrt(pvalue * (1 - pvalue) / (DRAWS + 1)),
                "wild_score_critical": critical,
                "wild_score_ci_lower": estimate - critical * se,
                "wild_score_ci_upper": estimate + critical * se,
                "normal_theory_mde80": (Z975 + Z80) * se,
                "common_cluster_draws_across_objects": True,
            })
    return rows


def run(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = CORE.load_data(args)
    objects = fit_models(data, args)
    dependence, conservation = dependence_rows(objects)
    few_cluster = few_cluster_rows(objects)
    write_csv(args.output_dir / "CORRECTED_TIME_HAC_RESULTS.csv", dependence)
    write_csv(args.output_dir / "SCORE_CONSERVATION_AUDIT.csv", conservation)
    write_csv(args.output_dir / "SOC2_FEW_CLUSTER_RESULTS.csv", few_cluster)

    public_cell_receipt = dict(objects["cell_receipt"])
    public_cell_receipt["microdata_files"] = [
        pathlib.Path(value).name for value in objects["cell_receipt"].get("microdata_files", [])
    ]
    output_hashes = {
        path.name: sha256(path) for path in sorted(args.output_dir.iterdir())
        if path.is_file() and path.name != "EXECUTION_RECEIPT.json"
    }
    receipt = {
        "record": "YAX R3 dependence and few-cluster audit",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "script_sha256": sha256(pathlib.Path(__file__)),
        "analysis_specification_sha256": sha256(HERE / "ANALYSIS_SPEC.md"),
        "prior_code_audit_sha256": sha256(HERE / "PRIOR_TIME_HAC_CODE_AUDIT.md"),
        "prior_time_HAC_script_sha256": sha256(
            ROOT / "yax/revision/referee_round2_20260905/precision_rotation/run_precision_rotation.py"
        ),
        "input_hashes": data["authenticated"]["hashes"],
        "repair_microdata_sha256": sha256(args.repair_microdata),
        "cell_build": public_cell_receipt,
        "support_occupations": len(objects["support"]),
        "support_hash_sha256": CORE.support_hash(objects["support"]),
        "months": len(objects["months"]),
        "full_elapsed_calendar_months": len(complete_calendar(objects["months"])[0]),
        "SOC2_clusters": len(objects["major_levels"]),
        "SOC2_reference_in_conditioned_model": objects["major_reference"],
        "few_cluster_draws": DRAWS,
        "few_cluster_seed": SEED,
        "PSD_projection_applied": False,
        "output_hashes": output_hashes,
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({
        "status": "PASS_R3_DEPENDENCE_AUDIT",
        "baseline": float(objects["base_fit"].beta[3]),
        "conditional": float(objects["conditional_fit"].beta[3]),
        "time_HAC_rows": len(dependence),
        "few_cluster_rows": len(few_cluster),
    }, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--repair-microdata", type=pathlib.Path, required=True)
    value.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    value.add_argument("--lookup", type=pathlib.Path, default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    value.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    value.add_argument("--rule-b-values", type=pathlib.Path, default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    value.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    value.add_argument("--first-access-receipt", type=pathlib.Path, default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    value.add_argument("--characteristics", type=pathlib.Path, default=ROOT / "yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv")
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    run(parser().parse_args())

