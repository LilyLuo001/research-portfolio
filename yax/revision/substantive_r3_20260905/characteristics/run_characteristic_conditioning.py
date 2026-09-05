#!/usr/bin/env python3
"""Run registered R3 occupational-characteristic conditioning models.

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
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[3]
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
DRAWS = 9999
SEED = 2026090531
Z975 = 1.959963984540054
Z80 = 0.8416212335729143

STATIC_CHARACTERISTICS = {
    "computer_use": "onet_computers_importance",
    "remotability": "dingel_neiman_telework",
    "wage": "log_mean_annual_wage",
    "education_requirement": "required_education_category_index",
    "routine_task_intensity": "rti_autor_dorn",
    "manual_physical": "manual_physical_ability_importance",
}


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


CORE = import_path("yax_r3_chars_core", ROOT / "yax/revision/referee_20260905/run_referee_core.py")
CELLS = import_path("yax_r3_chars_cells", ROOT / "yax/revision/referee_20260905/run_referee_cells.py")
COMP = import_path(
    "yax_r3_chars_composition",
    ROOT / "yax/revision/referee_round2_20260905/composition_influence/run_composition_influence.py",
)
FROZEN = CORE.FROZEN


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: pathlib.Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


def weighted_scale(values: np.ndarray, weights: np.ndarray) -> tuple[float, float]:
    mean = float(np.average(values, weights=weights))
    sd = float(np.sqrt(np.average(np.square(values - mean), weights=weights)))
    if not np.isfinite(sd) or sd <= 0:
        raise ValueError("nonpositive weighted standard deviation")
    return mean, sd


def weighted_corr(left: np.ndarray, right: np.ndarray, weights: np.ndarray) -> float:
    lm, _ = weighted_scale(left, weights)
    rm, _ = weighted_scale(right, weights)
    numerator = float(np.sum(weights * (left - lm) * (right - rm)))
    denominator = math.sqrt(
        float(np.sum(weights * np.square(left - lm)))
        * float(np.sum(weights * np.square(right - rm)))
    )
    return numerator / denominator


def pandemic_shortfalls(cells: pd.DataFrame, support: list[str]) -> tuple[dict, list[dict]]:
    months = sorted(
        month for month in cells.month.unique()
        if "2017-01" <= month <= "2022-11"
    )
    if len(months) != 71:
        raise RuntimeError(f"expected 71 shortfall months, found {len(months)}")
    pre = np.array([month <= "2019-12" for month in months])
    pandemic = np.array([month >= "2020-01" for month in months])
    time = np.arange(len(months), dtype=float)
    centered_time = time - float(np.mean(time[pre]))
    x_pre = np.column_stack([np.ones(int(pre.sum())), centered_time[pre]])

    selected = cells.loc[
        cells.occ_code.isin(support) & cells.month.isin(months) & cells.age.between(18, 65)
    ]
    total_frame = selected.groupby(["occ_code", "month"], as_index=False).stock.sum()
    index = pd.MultiIndex.from_product([support, months], names=["occ_code", "month"])
    total = (
        total_frame.pivot_table(index=["occ_code", "month"], values="stock", aggfunc="sum")
        .reindex(index, fill_value=0.0).stock.to_numpy().reshape(len(support), len(months))
    )
    young, older = CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65))
    age_total = young + older

    total_shortfall: dict[str, float] = {}
    relative_shortfall: dict[str, float] = {}
    rows: list[dict] = []
    for index_occ, code in enumerate(support):
        series = total[index_occ]
        mean_pre = float(np.mean(series[pre]))
        total_value = np.nan
        negative_predictions = 0
        if np.isfinite(mean_pre) and mean_pre > 0:
            normalized = series / mean_pre
            coef = np.linalg.lstsq(x_pre, normalized[pre], rcond=None)[0]
            prediction = np.column_stack([np.ones(len(months)), centered_time]) @ coef
            total_value = float(np.mean(prediction[pandemic] - normalized[pandemic]))
            negative_predictions = int(np.sum(prediction[pandemic] < 0))
        total_shortfall[code] = total_value

        y = young[index_occ]
        n = age_total[index_occ]
        valid_pre = pre & (n > 0)
        valid_post = pandemic & (n > 0)
        relative_value = np.nan
        out_of_bounds = 0
        if int(valid_pre.sum()) >= 24 and int(valid_post.sum()) > 0:
            share = np.divide(y, n, out=np.zeros_like(y), where=n > 0)
            x = np.column_stack([np.ones(int(valid_pre.sum())), centered_time[valid_pre]])
            root_weight = np.sqrt(n[valid_pre])
            coef = np.linalg.lstsq(x * root_weight[:, None], share[valid_pre] * root_weight, rcond=None)[0]
            prediction = np.column_stack([np.ones(len(months)), centered_time]) @ coef
            relative_value = float(np.average(
                prediction[valid_post] - share[valid_post], weights=n[valid_post]
            ))
            out_of_bounds = int(np.sum((prediction[valid_post] < 0) | (prediction[valid_post] > 1)))
        relative_shortfall[code] = relative_value
        rows.append({
            "occupation_code": code,
            "preperiod_mean_total_employment": mean_pre,
            "total_employment_shortfall": total_value,
            "young_relative_shortfall": relative_value,
            "preperiod_positive_age_cells": int(valid_pre.sum()),
            "pandemic_positive_age_cells": int(valid_post.sum()),
            "negative_total_trend_predictions": negative_predictions,
            "out_of_bounds_young_share_predictions": out_of_bounds,
            "total_preperiod_zero_months": int(np.sum(series[pre] == 0)),
            "total_pandemic_zero_months": int(np.sum(series[pandemic] == 0)),
        })
    return {
        "pandemic_total_shortfall": total_shortfall,
        "pandemic_young_relative_shortfall": relative_shortfall,
    }, rows


def build_base_design(
    support: list[str], months: list[str], q_map: dict[str, int], webb_z_map: dict[str, float]
) -> tuple[np.ndarray, list[str]]:
    quintiles = np.array([q_map[code] for code in support], int)
    webb_z = np.array([webb_z_map[code] for code in support], float)
    post = np.array([month >= "2023-01" for month in months])
    columns = [
        (((quintiles == q)[:, None]) & post[None, :]).reshape(-1).astype(float)
        for q in (2, 3, 4, 5)
    ]
    labels = [f"Q{q}_x_post" for q in (2, 3, 4, 5)]
    columns.append((webb_z[:, None] * post[None, :]).reshape(-1))
    labels.append("Webb_software_z_x_post")
    return np.column_stack(columns), labels


def group_post_columns(
    support: list[str], months: list[str], major_map: dict[str, str], weights: np.ndarray
) -> tuple[list[np.ndarray], list[str], str]:
    majors = np.array([major_map.get(code, "MISSING") for code in support], object)
    levels = sorted(set(majors.tolist()))
    totals = {level: float(weights[majors == level].sum()) for level in levels}
    reference = max(levels, key=lambda level: (totals[level], level))
    post = np.array([month >= "2023-01" for month in months])
    columns, labels = [], []
    for level in levels:
        if level == reference:
            continue
        columns.append((((majors == level)[:, None]) & post[None, :]).reshape(-1).astype(float))
        labels.append(f"SOC2_{level}_x_post")
    return columns, labels, reference


def summarize_model(
    name: str, panel: str, fit, influence: np.ndarray, details: dict,
    target: int, signs: np.ndarray, support: list[str], primary_weights: dict[str, float],
    labels: list[str], reference_soc2: str = "",
) -> tuple[dict, np.ndarray, np.ndarray, dict]:
    summary, centered = COMP.scalar_summary(fit, influence, target, signs)
    info = COMP.conditional_information(details, target)
    raw = float(np.sum(details["weight"] * np.square(details["rx"][:, target])))
    conditional = float(info["conditional_target_information"])
    row = {
        "analysis_status": LABEL,
        "specification": name,
        "panel": panel,
        "target": labels[target],
        "support_occupations": len(support),
        "support_hash_sha256": CORE.support_hash(support),
        "primary_support_employment_coverage": float(
            sum(primary_weights[code] for code in support) / sum(primary_weights.values())
        ),
        "regressor_count": len(labels),
        "regressor_labels_json": json.dumps(labels),
        "SOC2_post_reference": reference_soc2,
        "fixed_effect_adjusted_raw_target_information": raw,
        "conditional_target_information": conditional,
        "information_retention_conditional_over_raw": conditional / raw,
        "target_vif_like_raw_over_conditional": raw / conditional,
        "effective_occupation_information_count": info["effective_occupation_information_count"],
        "top_five_information_share": info["top_five_information_share"],
        "information_matrix_rank": info["information_matrix_rank"],
        "information_matrix_columns": info["information_matrix_columns"],
        "information_matrix_condition_number_positive_spectrum": info[
            "information_matrix_condition_number_positive_spectrum"
        ],
        "normal_theory_mde80": (Z975 + Z80) * summary["analytic_cluster_se"],
        **summary,
    }
    return row, centered, influence[:, target], info


def paired_row(
    name: str, estimate: float, vector: np.ndarray, signs: np.ndarray, support: list[str],
    reference: str = "common_support_baseline",
) -> dict:
    centered = signs @ vector
    se = float(np.sqrt(np.sum(np.square(vector))))
    critical = float(np.quantile(np.abs(centered / se), .95, method="higher"))
    return {
        "analysis_status": LABEL,
        "contrast": f"{name}_minus_{reference}",
        "support_occupations": len(support),
        "support_hash_sha256": CORE.support_hash(support),
        "coefficient_difference": estimate,
        "paired_se": se,
        "paired_ci_lower": estimate - critical * se,
        "paired_ci_upper": estimate + critical * se,
        "paired_p_value": float(
            (1 + np.sum(np.abs(centered / se) >= abs(estimate / se))) / (len(centered) + 1)
        ),
        "normal_theory_mde80": (Z975 + Z80) * se,
        "common_occupation_multipliers": True,
        "draws": len(centered),
    }


def run(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = CORE.load_data(args)
    exposure = data["exposures"]["dv_rating_beta"]["A"]
    webb = data["computers"]["webb_pct_software"]
    prepared = FROZEN.prepare_model(
        data["panel"], data["occupations"], data["static_months"], exposure, webb, scale="q5_q1"
    )
    primary_support = list(prepared["occupations"])
    if len(primary_support) != 468:
        raise RuntimeError(f"expected 468 primary occupations, found {len(primary_support)}")
    primary_weights = {code: float(weight) for code, weight in zip(primary_support, prepared["weights"])}
    q_values = np.array([exposure[code] for code in primary_support], float)
    q_full = FROZEN.weighted_quintiles(q_values, prepared["weights"])
    q_map = {code: int(q) for code, q in zip(primary_support, q_full)}
    webb_values = np.array([webb[code] for code in primary_support], float)
    webb_mean, webb_sd = FROZEN.weighted_scale(webb_values, prepared["weights"])
    webb_z_map = {code: float((webb[code] - webb_mean) / webb_sd) for code in primary_support}

    cells, _, cell_receipt = CELLS.build_exact_age_cells(args)
    months = [month for month in sorted(cells.month.unique()) if month != "2022-12"]
    if len(months) != 113:
        raise RuntimeError(f"expected 113 corrected months, found {len(months)}")

    chars = pd.read_csv(args.characteristics, dtype={"census2018": str})
    chars["census2018"] = chars.census2018.str.zfill(4)
    chars = chars.set_index("census2018", drop=False)
    shortfall_maps, shortfall_rows = pandemic_shortfalls(cells, primary_support)
    raw_maps: dict[str, dict[str, float]] = {
        name: pd.to_numeric(chars[column], errors="coerce").to_dict()
        for name, column in STATIC_CHARACTERISTICS.items()
    }
    raw_maps.update(shortfall_maps)
    common_support = sorted(
        code for code in primary_support
        if code in chars.index and all(np.isfinite(values.get(code, np.nan)) for values in raw_maps.values())
    )
    if len(common_support) < 100:
        raise RuntimeError(f"characteristic common support implausibly small: {len(common_support)}")

    pre_cells = cells.loc[
        cells.occ_code.isin(primary_support)
        & cells.month.between("2017-01", "2019-12")
        & cells.age.between(18, 65)
    ]
    pre_weights_series = pre_cells.groupby("occ_code").stock.sum()
    pre_weight_map = {
        code: float(pre_weights_series.get(code, 0.0)) for code in primary_support
    }
    pre_weights = np.array([float(pre_weights_series.get(code, 0.0)) for code in common_support])
    if np.any(pre_weights <= 0):
        raise RuntimeError("common support contains occupation with zero 2017-2019 employment")
    z_maps: dict[str, dict[str, float]] = {}
    scale_rows = []
    for name, values in raw_maps.items():
        vector = np.array([values[code] for code in common_support], float)
        mean, sd = weighted_scale(vector, pre_weights)
        z_maps[name] = {code: float((values[code] - mean) / sd) for code in common_support}
        scale_rows.append({
            "characteristic": name,
            "support_rule": "literal_all_characteristics_common_support",
            "support_hash_sha256": CORE.support_hash(common_support),
            "source_column": STATIC_CHARACTERISTICS.get(name, "generated_from_corrected_CPS_cells"),
            "weighted_mean": mean,
            "weighted_sd": sd,
            "scaling_weights": "2017-2019 total employment ages 18-65",
            "support_occupations": len(common_support),
        })

    corr_names = ["beta_exposure", *raw_maps]
    corr_values = {"beta_exposure": np.array([exposure[c] for c in common_support], float)}
    corr_values.update({name: np.array([values[c] for c in common_support], float) for name, values in raw_maps.items()})
    corr_rows = []
    for left in corr_names:
        for right in corr_names:
            corr_rows.append({
                "left": left,
                "right": right,
                "employment_weighted_correlation": weighted_corr(corr_values[left], corr_values[right], pre_weights),
                "support_occupations": len(common_support),
            })

    _, _, major_map = FROZEN.comp_maps(args.computerization)
    failures: list[dict] = []
    model_rows: list[dict] = []
    paired_rows: list[dict] = []
    information_rows: list[dict] = []
    coefficient_rows: list[dict] = []

    def fit_registered(
        name: str, panel: str, support: list[str], control_names: list[str], add_soc2: bool,
        signs: np.ndarray, control_z_maps: dict[str, dict[str, float]] | None = None,
    ):
        young, older = CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65))
        x, labels = build_base_design(support, months, q_map, webb_z_map)
        post = np.array([month >= "2023-01" for month in months])
        columns = [x]
        selected_z_maps = z_maps if control_z_maps is None else control_z_maps
        for control in control_names:
            values = np.array([selected_z_maps[control][code] for code in support], float)
            columns.append((values[:, None] * post[None, :]).reshape(-1, 1))
            labels.append(f"{control}_z_x_post")
        reference = ""
        if add_soc2:
            weights = np.array([primary_weights[code] for code in support], float)
            group_columns, group_labels, reference = group_post_columns(
                support, months, major_map, weights
            )
            if group_columns:
                columns.append(np.column_stack(group_columns))
                labels.extend(group_labels)
        regressors = np.column_stack(columns)
        second_fe = np.tile(np.arange(len(months)), len(support))
        fit, influence, details = COMP.fit_absorbed(young, older, regressors, second_fe)
        row, centered, target_vector, info = summarize_model(
            name, panel, fit, influence, details, 3, signs, support, primary_weights, labels, reference
        )
        model_rows.append(row)
        for coefficient_index, coefficient_label in enumerate(labels):
            coefficient_summary, _ = COMP.scalar_summary(
                fit, influence, coefficient_index, signs
            )
            coefficient_rows.append({
                "analysis_status": LABEL,
                "specification": name,
                "panel": panel,
                "coefficient_label": coefficient_label,
                "is_Q5_target": coefficient_index == 3,
                "support_occupations": len(support),
                "support_hash_sha256": CORE.support_hash(support),
                "normal_theory_mde80": (
                    (Z975 + Z80) * coefficient_summary["analytic_cluster_se"]
                ),
                **coefficient_summary,
            })
        contributions = info["occupation_information"]
        for code, contribution in zip(support, contributions):
            information_rows.append({
                "specification": name,
                "occupation_code": code,
                "occupation_name": data["names"].get(code, ""),
                "SOC2": major_map.get(code, "MISSING"),
                "frozen_beta_quintile": q_map[code],
                "conditional_target_information": float(contribution),
                "conditional_target_information_share": float(contribution / contributions.sum()),
                "primary_employment_weight": primary_weights[code],
            })
        return row, centered, target_vector

    native_signs = np.random.default_rng(SEED).choice(
        np.array([-1.0, 1.0]), size=(DRAWS, len(primary_support))
    )
    try:
        fit_registered("native_corrected_baseline", "native_468", primary_support, [], False, native_signs)
    except Exception as error:
        failures.append({"specification": "native_corrected_baseline", "error": repr(error)})
        raise

    signs = np.random.default_rng(SEED + 1).choice(
        np.array([-1.0, 1.0]), size=(DRAWS, len(common_support))
    )
    common_baseline, _, common_vector = fit_registered(
        "common_support_baseline", "literal_characteristic_common", common_support, [], False, signs
    )

    specifications = [
        ("one_at_a_time_computer_use", "one_at_a_time", ["computer_use"], False),
        ("one_at_a_time_remotability", "one_at_a_time", ["remotability"], False),
        ("one_at_a_time_wage", "one_at_a_time", ["wage"], False),
        ("one_at_a_time_education", "one_at_a_time", ["education_requirement"], False),
        ("one_at_a_time_routine", "one_at_a_time", ["routine_task_intensity"], False),
        ("one_at_a_time_manual", "one_at_a_time", ["manual_physical"], False),
        ("one_at_a_time_pandemic_total", "one_at_a_time", ["pandemic_total_shortfall"], False),
        ("one_at_a_time_pandemic_young_relative", "one_at_a_time", ["pandemic_young_relative_shortfall"], False),
        ("one_at_a_time_SOC2_post", "one_at_a_time", [], True),
        ("cumulative_computer", "cumulative", ["computer_use"], False),
        ("cumulative_computer_remote", "cumulative", ["computer_use", "remotability"], False),
        ("cumulative_human_task_block", "cumulative", [
            "computer_use", "remotability", "wage", "education_requirement",
            "routine_task_intensity", "manual_physical",
        ], False),
        ("cumulative_plus_pandemic", "cumulative", [
            "computer_use", "remotability", "wage", "education_requirement",
            "routine_task_intensity", "manual_physical", "pandemic_total_shortfall",
        ], False),
        ("cumulative_plus_pandemic_SOC2", "cumulative", [
            "computer_use", "remotability", "wage", "education_requirement",
            "routine_task_intensity", "manual_physical", "pandemic_total_shortfall",
        ], True),
        ("parsimonious_combined_SOC2", "parsimonious", [
            "computer_use", "remotability", "education_requirement",
            "routine_task_intensity", "pandemic_total_shortfall",
        ], True),
    ]
    for name, panel, controls, add_soc2 in specifications:
        try:
            row, _, vector = fit_registered(
                name, panel, common_support, controls, add_soc2, signs
            )
            paired_rows.append(paired_row(
                name,
                row["coefficient"] - common_baseline["coefficient"],
                vector - common_vector,
                signs,
                common_support,
            ))
        except Exception as error:
            failures.append({
                "specification": name,
                "panel": panel,
                "controls": controls,
                "SOC2_post": add_soc2,
                "error_type": type(error).__name__,
                "error": str(error),
            })

    support_specific_specs = [
        ("computer_use", False),
        ("remotability", False),
        ("wage", False),
        ("education_requirement", False),
        ("routine_task_intensity", False),
        ("manual_physical", False),
        ("pandemic_total_shortfall", False),
        ("pandemic_young_relative_shortfall", False),
        ("SOC2_post", True),
    ]
    support_specific_meta = []
    for control_index, (control, add_soc2) in enumerate(support_specific_specs):
        try:
            if add_soc2:
                control_support = list(primary_support)
                local_z_maps: dict[str, dict[str, float]] = {}
                local_mean = local_sd = np.nan
            else:
                control_support = sorted(
                    code for code in primary_support
                    if pre_weight_map[code] > 0
                    and np.isfinite(raw_maps[control].get(code, np.nan))
                )
                values = np.array([raw_maps[control][code] for code in control_support], float)
                weights = np.array([pre_weight_map[code] for code in control_support], float)
                local_mean, local_sd = weighted_scale(values, weights)
                local_z_maps = {
                    control: {
                        code: float((raw_maps[control][code] - local_mean) / local_sd)
                        for code in control_support
                    }
                }
                scale_rows.append({
                    "characteristic": control,
                    "support_rule": f"maximal_finite_{control}_support",
                    "support_hash_sha256": CORE.support_hash(control_support),
                    "source_column": STATIC_CHARACTERISTICS.get(
                        control, "generated_from_corrected_CPS_cells"
                    ),
                    "weighted_mean": local_mean,
                    "weighted_sd": local_sd,
                    "scaling_weights": "2017-2019 total employment ages 18-65",
                    "support_occupations": len(control_support),
                })
            local_signs = np.random.default_rng(SEED + 100 + control_index).choice(
                np.array([-1.0, 1.0]), size=(DRAWS, len(control_support))
            )
            baseline_name = f"support_specific_{control}_baseline"
            augmented_name = f"support_specific_{control}_augmented"
            local_baseline, _, local_baseline_vector = fit_registered(
                baseline_name,
                "support_specific_one_at_a_time",
                control_support,
                [],
                False,
                local_signs,
                local_z_maps,
            )
            augmented_controls = [] if add_soc2 else [control]
            local_augmented, _, local_augmented_vector = fit_registered(
                augmented_name,
                "support_specific_one_at_a_time",
                control_support,
                augmented_controls,
                add_soc2,
                local_signs,
                local_z_maps,
            )
            paired_rows.append(paired_row(
                augmented_name,
                local_augmented["coefficient"] - local_baseline["coefficient"],
                local_augmented_vector - local_baseline_vector,
                local_signs,
                control_support,
                baseline_name,
            ))
            support_specific_meta.append({
                "control": control,
                "support_occupations": len(control_support),
                "support_hash_sha256": CORE.support_hash(control_support),
                "primary_support_employment_coverage": float(
                    sum(primary_weights[code] for code in control_support)
                    / sum(primary_weights.values())
                ),
                "baseline_specification": baseline_name,
                "augmented_specification": augmented_name,
                "characteristic_weighted_mean": local_mean,
                "characteristic_weighted_sd": local_sd,
            })
        except Exception as error:
            failures.append({
                "specification": f"support_specific_{control}",
                "panel": "support_specific_one_at_a_time",
                "error_type": type(error).__name__,
                "error": str(error),
            })

    quintile_rows = []
    total_primary_weight = sum(primary_weights.values())
    for label, support in (("primary_native", primary_support), ("characteristic_common", common_support)):
        for q in range(1, 6):
            codes = [code for code in support if q_map[code] == q]
            quintile_rows.append({
                "support": label,
                "quintile": q,
                "occupations": len(codes),
                "primary_employment_weight": sum(primary_weights[code] for code in codes),
                "primary_employment_share": sum(primary_weights[code] for code in codes) / total_primary_weight,
            })

    write_csv(args.output_dir / "CHARACTERISTIC_MODEL_RESULTS.csv", model_rows)
    write_csv(args.output_dir / "ALL_MODEL_COEFFICIENTS.csv", coefficient_rows)
    write_csv(args.output_dir / "CHARACTERISTIC_PAIRED_DIFFERENCES.csv", paired_rows)
    write_csv(args.output_dir / "CHARACTERISTIC_INFORMATION_BY_OCCUPATION.csv", information_rows)
    write_csv(args.output_dir / "CHARACTERISTIC_CORRELATIONS.csv", corr_rows)
    write_csv(args.output_dir / "CHARACTERISTIC_SCALING.csv", scale_rows)
    write_csv(args.output_dir / "CHARACTERISTIC_SUPPORT_BY_QUINTILE.csv", quintile_rows)
    write_csv(args.output_dir / "SUPPORT_SPECIFIC_MODEL_MAP.csv", support_specific_meta)
    write_csv(args.output_dir / "PANDEMIC_SHORTFALL_DIAGNOSTICS.csv", shortfall_rows)
    write_json(args.output_dir / "MODEL_FAILURES.json", failures)

    output_hashes = {
        path.name: sha256(path) for path in sorted(args.output_dir.iterdir())
        if path.is_file() and path.name != "EXECUTION_RECEIPT.json"
    }
    public_cell_receipt = dict(cell_receipt)
    public_cell_receipt["microdata_files"] = [
        pathlib.Path(value).name for value in cell_receipt.get("microdata_files", [])
    ]
    receipt = {
        "record": "YAX R3 occupational-characteristic conditioning",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "registered_specification": str((HERE / "ANALYSIS_SPEC.md").relative_to(ROOT)),
        "registered_specification_sha256": sha256(HERE / "ANALYSIS_SPEC.md"),
        "support_amendment_sha256": sha256(HERE / "ANALYSIS_SPEC_AMENDMENT_1.md"),
        "initial_common_support_results_commit": "8e3b876266e09679467b5a0c640c3c16b0c51974",
        "script_sha256": sha256(pathlib.Path(__file__)),
        "input_hashes": data["authenticated"]["hashes"],
        "repair_microdata_sha256": sha256(args.repair_microdata),
        "cell_build": public_cell_receipt,
        "primary_support_occupations": len(primary_support),
        "common_support_occupations": len(common_support),
        "common_support_hash_sha256": CORE.support_hash(common_support),
        "common_support_primary_employment_coverage": float(
            sum(primary_weights[code] for code in common_support) / sum(primary_weights.values())
        ),
        "quintile_assignments": "historical frozen primary assignments retained",
        "webb_normalization": "historical frozen primary normalization retained",
        "characteristic_normalization": "2017-2019 total employment weights on literal common support",
        "pandemic_shortfall_generated_regressor_uncertainty": "not captured by conditional wild-score intervals",
        "bootstrap": {
            "draws": DRAWS,
            "seed_native": SEED,
            "seed_common": SEED + 1,
            "common_occupation_Rademacher_multipliers": True,
        },
        "model_failures": failures,
        "output_hashes": output_hashes,
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({
        "status": "PASS_R3_CHARACTERISTIC_CONDITIONING" if not failures else "COMPLETE_WITH_FAILURES",
        "primary_support": len(primary_support),
        "common_support": len(common_support),
        "models_completed": len(model_rows),
        "failures": failures,
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
