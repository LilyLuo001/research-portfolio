#!/usr/bin/env python3
"""Execute registered YAX R3 within-family analyses FAM-01--FAM-06.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.
Protected inputs and historical results are authenticated and read only.  The
program writes only to the explicitly supplied project-storage output folder.
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
ROOT = pathlib.Path(__file__).resolve().parents[4]
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
EXPECTED_CORRECTED = -0.1345539535732939
DRAWS = 9999
SEED = 2026090517
MDE_FACTOR = 1.959963984540054 + 0.8416212335729143
SOC2_NAMES = {
    "11": "Management",
    "13": "Business and Financial Operations",
    "15": "Computer and Mathematical",
    "17": "Architecture and Engineering",
    "19": "Life, Physical, and Social Science",
    "21": "Community and Social Service",
    "23": "Legal",
    "25": "Educational Instruction and Library",
    "27": "Arts, Design, Entertainment, Sports, and Media",
    "29": "Healthcare Practitioners and Technical",
    "31": "Healthcare Support",
    "33": "Protective Service",
    "35": "Food Preparation and Serving Related",
    "37": "Building and Grounds Cleaning and Maintenance",
    "39": "Personal Care and Service",
    "41": "Sales and Related",
    "43": "Office and Administrative Support",
    "45": "Farming, Fishing, and Forestry",
    "47": "Construction and Extraction",
    "49": "Installation, Maintenance, and Repair",
    "51": "Production",
    "53": "Transportation and Material Moving",
}


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


COMP = import_path(
    "yax_r3_within_family_composition",
    ROOT / "yax/revision/referee_round2_20260905/composition_influence/run_composition_influence.py",
)
CORE = COMP.CORE
FROZEN = COMP.FROZEN
CELLS = COMP.CELLS


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def support_hash(codes) -> str:
    payload = "".join("{}\n".format(code) for code in sorted(codes))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def quantile(values, q):
    try:
        return float(np.quantile(values, q, method="higher"))
    except TypeError:
        return float(np.quantile(values, q, interpolation="higher"))


def write_csv(path: pathlib.Path, rows) -> None:
    if not rows:
        raise RuntimeError("refusing to write empty output {}".format(path))
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: pathlib.Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def weighted_mean(values, weights) -> float:
    return float(np.average(values, weights=weights))


def weighted_sd(values, weights) -> float:
    mean = weighted_mean(values, weights)
    value = float(np.sqrt(np.average(np.square(values - mean), weights=weights)))
    if not np.isfinite(value) or value <= 0:
        raise RuntimeError("weighted standard deviation is not positive")
    return value


def fixed_effect_codes(majors, n_month, structure):
    n_occ = len(majors)
    if structure in ("baseline", "SOC2_x_post"):
        return np.tile(np.arange(n_month), n_occ)
    if structure == "SOC2_x_calendar_month":
        levels = {value: index for index, value in enumerate(sorted(set(majors.tolist())))}
        return np.concatenate([
            levels[majors[index]] * n_month + np.arange(n_month)
            for index in range(n_occ)
        ])
    raise ValueError("unknown structure {}".format(structure))


def assemble_regressors(target_columns, target_labels, webb_z, post, majors,
                        stock, structure):
    columns = [np.asarray(column, float) for column in target_columns]
    labels = list(target_labels)
    columns.append((webb_z[:, None] * post[None, :]).reshape(-1))
    labels.append("Webb_software_z_x_post")
    reference = ""
    if structure == "SOC2_x_post":
        levels = sorted(set(majors.tolist()))
        group_weights = {
            group: float(stock[majors == group].sum()) for group in levels
        }
        reference = max(levels, key=lambda value: (group_weights[value], value))
        for group in levels:
            if group == reference:
                continue
            columns.append(
                (((majors == group)[:, None]) & post[None, :]).reshape(-1).astype(float)
            )
            labels.append("SOC2_{}_x_post".format(group))
    return np.column_stack(columns), labels, reference


def fit_model(model_id, young, older, support, majors, global_indices,
              target_columns, target_labels, webb_z, post, structure,
              signs_global):
    n_occ, n_month = young.shape
    stock = (young + older).sum(axis=1)
    regressors, labels, reference = assemble_regressors(
        target_columns, target_labels, webb_z, post, majors, stock, structure
    )
    second = fixed_effect_codes(majors, n_month, structure)
    fit, influence, details = COMP.fit_absorbed(young, older, regressors, second)
    if influence.shape[0] != n_occ:
        raise RuntimeError("{} lost an occupation after positive-cell filtering".format(model_id))
    signs = signs_global[:, global_indices]
    shifts = signs @ influence
    return {
        "model_id": model_id,
        "structure": structure,
        "support": list(support),
        "majors": majors.copy(),
        "global_indices": np.asarray(global_indices, int),
        "young": young,
        "older": older,
        "stock": stock,
        "regressors": regressors,
        "labels": labels,
        "target_indices": list(range(len(target_labels))),
        "target_labels": list(target_labels),
        "reference": reference,
        "fit": fit,
        "influence": influence,
        "details": details,
        "shifts": shifts,
    }


def information_for_target(model, target_index):
    details = model["details"]
    x = details["x"]
    rx = details["rx"]
    weight = details["weight"]
    target = x[:, target_index]
    raw_mean = weighted_mean(target, weight)
    raw_ss = float(np.sum(weight * np.square(target - raw_mean)))
    fe_ss = float(np.sum(weight * np.square(rx[:, target_index])))
    other = [index for index in range(rx.shape[1]) if index != target_index]
    residual = rx[:, target_index].copy()
    if other:
        z = rx[:, other]
        cross = z.T @ (weight * residual)
        zz = z.T @ (weight[:, None] * z)
        try:
            projection = np.linalg.solve(zz, cross)
        except np.linalg.LinAlgError:
            projection = np.linalg.lstsq(zz, cross, rcond=None)[0]
        residual -= z @ projection
    contribution = np.bincount(
        details["occupation"],
        weights=weight * np.square(residual),
        minlength=details["occupation_count"],
    )
    fisher = float(contribution.sum())
    if fisher <= 0:
        raise RuntimeError("{} target {} has no conditional information".format(
            model["model_id"], target_index
        ))
    shares = contribution / fisher
    top = np.sort(shares)[::-1]
    se = float(model["fit"].standard_error[target_index])
    return {
        "raw_weighted_treatment_ss": raw_ss,
        "fixed_effect_residual_weighted_ss": fe_ss,
        "nuisance_adjusted_fisher_information": fisher,
        "raw_weighted_treatment_sd": float(math.sqrt(raw_ss / weight.sum())),
        "fixed_effect_residual_weighted_sd": float(math.sqrt(fe_ss / weight.sum())),
        "nuisance_adjusted_residual_weighted_sd": float(math.sqrt(fisher / weight.sum())),
        "information_retained_vs_raw": float(fisher / raw_ss) if raw_ss > 0 else np.nan,
        "effective_occupation_information_count": float(1.0 / np.square(shares).sum()),
        "top_five_occupation_information_share": float(top[:5].sum()),
        "nominal_occupation_cluster_count": int(details["occupation_count"]),
        "occupation_cluster_se": se,
        "normal_theory_MDE80": float(MDE_FACTOR * se),
        "independent_cell_information_MDE80": float(MDE_FACTOR / math.sqrt(fisher)),
        "weight_sum": float(weight.sum()),
        "occupation_contribution": contribution,
        "occupation_share": shares,
    }


def scalar_bootstrap(model, target_index, simultaneous_critical=None):
    estimate = float(model["fit"].beta[target_index])
    se = float(model["fit"].standard_error[target_index])
    centered = model["shifts"][:, target_index]
    critical = quantile(np.abs(centered / se), .95)
    result = {
        "coefficient": estimate,
        "occupation_cluster_se": se,
        "bootstrap_se": float(np.std(centered, ddof=1)),
        "pointwise_ci_lower": float(estimate - critical * se),
        "pointwise_ci_upper": float(estimate + critical * se),
        "pointwise_critical": critical,
        "wild_score_p_value": float(
            (1 + np.sum(np.abs(centered / se) >= abs(estimate / se))) /
            (len(centered) + 1)
        ),
        "bootstrap_draws": len(centered),
        "normal_theory_MDE80": float(MDE_FACTOR * se),
    }
    if simultaneous_critical is not None:
        result["simultaneous_ci_lower"] = float(estimate - simultaneous_critical * se)
        result["simultaneous_ci_upper"] = float(estimate + simultaneous_critical * se)
        result["simultaneous_critical"] = float(simultaneous_critical)
    return result


def wald_test(model, restriction, label):
    restriction = np.asarray(restriction, float)
    beta = model["fit"].beta
    covariance = model["influence"].T @ model["influence"]
    estimate = restriction @ beta
    rv = restriction @ covariance @ restriction.T
    inverse = np.linalg.pinv(rv)
    observed = float(estimate @ inverse @ estimate)
    draw_values = model["shifts"] @ restriction.T
    wild = np.einsum("ij,jk,ik->i", draw_values, inverse, draw_values)
    return {
        "model_id": model["model_id"],
        "test": label,
        "restrictions": int(restriction.shape[0]),
        "wald_statistic": observed,
        "wild_score_p_value": float((1 + np.sum(wild >= observed)) / (len(wild) + 1)),
        "bootstrap_draws": len(wild),
        "covariance_rank": int(np.linalg.matrix_rank(rv)),
    }


def profile_summaries(model):
    targets = model["target_indices"]
    ses = model["fit"].standard_error[targets]
    target_shifts = model["shifts"][:, targets]
    simultaneous = quantile(np.max(np.abs(target_shifts / ses[None, :]), axis=1), .95)
    rows = []
    for target, label in zip(targets, model["target_labels"]):
        rows.append({
            "analysis_status": LABEL,
            "model_id": model["model_id"],
            "structure": model["structure"],
            "target": label,
            "support_occupations": len(model["support"]),
            "support_hash_sha256": support_hash(model["support"]),
            "SOC2_groups": len(set(model["majors"].tolist())),
            "SOC2_post_reference": model["reference"],
            **scalar_bootstrap(model, target, simultaneous),
        })
    p = len(model["fit"].beta)
    zero = np.zeros((4, p))
    zero[np.arange(4), targets] = 1.0
    equal = np.zeros((3, p))
    for index in range(3):
        equal[index, targets[index]] = 1.0
        equal[index, targets[index + 1]] = -1.0
    tests = [
        wald_test(model, zero, "Q2_Q3_Q4_Q5_jointly_zero"),
        wald_test(model, equal, "Q2_equals_Q3_equals_Q4_equals_Q5"),
    ]
    # Least-favorable max-t diagnostic of 0 >= b2 >= b3 >= b4 >= b5.
    mono = np.zeros((4, p))
    mono[0, targets[0]] = 1.0
    for index in range(1, 4):
        mono[index, targets[index]] = 1.0
        mono[index, targets[index - 1]] = -1.0
    covariance = model["influence"].T @ model["influence"]
    diff = mono @ model["fit"].beta
    se = np.sqrt(np.maximum(np.diag(mono @ covariance @ mono.T), 1e-20))
    draw_t = (model["shifts"] @ mono.T) / se[None, :]
    observed = float(np.max(diff / se))
    max_draw = np.max(draw_t, axis=1)
    critical = quantile(max_draw, .95)
    pvalue = float((1 + np.sum(max_draw >= observed)) / (len(max_draw) + 1))
    tests.append({
        "model_id": model["model_id"],
        "test": "monotone_nonincreasing_least_favorable_max_t",
        "restrictions": 4,
        "wald_statistic": "",
        "max_t_statistic": observed,
        "one_sided_critical": critical,
        "wild_score_p_value": pvalue,
        "bootstrap_draws": len(max_draw),
        "covariance_rank": int(np.linalg.matrix_rank(mono @ covariance @ mono.T)),
        "verdict": (
            "REJECT_MONOTONE_NONINCREASING_AT_5_PERCENT" if pvalue < .05
            else "UNRESOLVED_NOT_REJECTED_AND_NOT_ESTABLISHED"
        ),
    })
    return rows, tests


def paired_row(left, right, left_target, right_target, contrast_label):
    estimate = float(left["fit"].beta[left_target] - right["fit"].beta[right_target])
    centered = left["shifts"][:, left_target] - right["shifts"][:, right_target]
    se = float(np.std(centered, ddof=1))
    critical = quantile(np.abs(centered / se), .95)
    return {
        "analysis_status": LABEL,
        "contrast": contrast_label,
        "left_model": left["model_id"],
        "right_model": right["model_id"],
        "left_coefficient": float(left["fit"].beta[left_target]),
        "right_coefficient": float(right["fit"].beta[right_target]),
        "coefficient_difference": estimate,
        "paired_bootstrap_se": se,
        "paired_ci_lower": float(estimate - critical * se),
        "paired_ci_upper": float(estimate + critical * se),
        "paired_p_value": float(
            (1 + np.sum(np.abs(centered / se) >= abs(estimate / se))) /
            (len(centered) + 1)
        ),
        "paired_critical": critical,
        "paired_normal_theory_MDE80": float(MDE_FACTOR * se),
        "common_occupation_multipliers": True,
        "bootstrap_draws": len(centered),
    }


def append_information(model, target_index, target_label, information_rows,
                       occupation_rows, family_rows, reference_information=None,
                       include_contributors=True):
    info = information_for_target(model, target_index)
    row = {
        "analysis_status": LABEL,
        "model_id": model["model_id"],
        "structure": model["structure"],
        "target": target_label,
        "support_occupations": len(model["support"]),
        **{key: value for key, value in info.items()
           if key not in ("occupation_contribution", "occupation_share")},
    }
    row["information_relative_to_parent_baseline"] = (
        float(info["nuisance_adjusted_fisher_information"] / reference_information)
        if reference_information is not None else 1.0
    )
    information_rows.append(row)
    if include_contributors:
        family_totals = {}
        for index, code in enumerate(model["support"]):
            group = model["majors"][index]
            contribution = float(info["occupation_contribution"][index])
            occupation_rows.append({
                "analysis_status": LABEL,
                "model_id": model["model_id"],
                "target": target_label,
                "occupation_code": code,
                "SOC2": group,
                "conditional_information": contribution,
                "conditional_information_share": float(info["occupation_share"][index]),
                "full_sample_stock": float(model["stock"][index]),
            })
            family_totals[group] = family_totals.get(group, 0.0) + contribution
        total = info["nuisance_adjusted_fisher_information"]
        for group in sorted(family_totals):
            family_rows.append({
                "analysis_status": LABEL,
                "model_id": model["model_id"],
                "target": target_label,
                "SOC2": group,
                "SOC2_name": SOC2_NAMES.get(group, group),
                "conditional_information": family_totals[group],
                "conditional_information_share": float(family_totals[group] / total),
            })
    return info


def build_findings(path, models, direct_groups, direct_share, within_scale,
                   lofo_rows, failures, family_selection):
    baseline = models["profile_baseline"]
    post = models["profile_SOC2_x_post"]
    month = models["profile_SOC2_x_calendar_month"]
    q5 = 3
    direct = models["direct_SOC2_x_calendar_month"]
    continuous = models["continuous_SOC2_x_calendar_month"]
    lofo_q = [row["coefficient"] for row in lofo_rows
              if row["parent_model"] == "profile_SOC2_x_calendar_month"
              and row["target"] == "Q5_x_post"]
    lofo_c = [row["coefficient"] for row in lofo_rows
              if row["parent_model"] == "continuous_SOC2_x_calendar_month"]
    lines = [
        "# Within-family findings",
        "",
        "**Status:** {}.".format(LABEL),
        "",
        "The corrected-calendar Q5--Q1 coefficient is `{:.6f}`.  Adding SOC2-by-post "
        "terms yields `{:.6f}`, and absorbing SOC2-by-month paths yields `{:.6f}`.  "
        "These are sensitivity comparisons under changed conditioning restrictions, not "
        "causal allocations between AI and composition.".format(
            baseline["fit"].beta[q5], post["fit"].beta[q5], month["fit"].beta[q5]
        ),
        "",
        "The direct-tail benchmark changes the population to Q1/Q5 occupations in the "
        "four families `{}`.  It retains {:.2f}% of full-support preperiod stock; its "
        "SOC2-by-month coefficient is `{:.6f}`.  It should not be compared mechanically "
        "with the full-support coefficient as if only a control changed.".format(
            ", ".join(direct_groups), 100 * direct_share,
            direct["fit"].beta[0]
        ),
        "",
        "The continuous companion uses one employment-weighted within-family beta "
        "standard deviation (`{:.6f}` raw beta units) and imposes a common slope across "
        "families.  Its SOC2-by-month slope is `{:.6f}`.".format(
            within_scale, continuous["fit"].beta[0]
        ),
        "",
        "Leave-one-family-out ranges are `{:.6f}` to `{:.6f}` for the conditional "
        "Q5 coefficient and `{:.6f}` to `{:.6f}` for the continuous slope.  No omitted "
        "family is promoted as a preferred specification.".format(
            min(lofo_q), max(lofo_q), min(lofo_c), max(lofo_c)
        ),
        "",
        "Trajectory families were chosen solely by direct-tail nuisance-adjusted "
        "information: {}.  The output reports young and older stocks separately for "
        "both tails.  No sampling interval is fabricated from aggregate final weights.".format(
            "; ".join("{} ({})".format(row["SOC2"], row["SOC2_name"])
                      for row in family_selection)
        ),
        "",
        "Information is computed exactly as `I=sum h*r^2` after weighted fixed-effect "
        "absorption and projection on every other slope regressor.  Effective occupation "
        "counts and top-five shares describe fitted information concentration; they do "
        "not replace the nominal cluster count or validate a reference distribution.",
        "",
        "Model failures recorded: `{}`.".format(len(failures)),
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = CORE.load_data(args)
    prepared, quintiles, majors, _ = COMP.primary_setup(data, args)
    support = list(prepared["occupations"])
    if len(support) != 468:
        raise RuntimeError("historical support changed from 468 occupations")
    cells, _, cell_build = CELLS.build_exact_age_cells(args)
    months = [month for month in sorted(cells.month.unique()) if month != "2022-12"]
    if len(months) != 113:
        raise RuntimeError("corrected calendar is not 113 months: {}".format(len(months)))
    young, older = CELLS.panel_for_ages(cells, support, months, (22, 25), (26, 65))
    post = np.array([month >= "2023-01" for month in months])
    pre = np.array([month <= "2022-11" for month in months])
    pre_stock = (young[:, pre] + older[:, pre]).sum(axis=1)
    exposure = data["exposures"]["dv_rating_beta"]["A"]
    exposure_values = np.array([exposure[code] for code in support], float)
    webb = data["computers"]["webb_pct_software"]
    webb_values = np.array([webb[code] for code in support], float)
    webb_mean, webb_sd = FROZEN.weighted_scale(webb_values, prepared["weights"])
    webb_z = (webb_values - webb_mean) / webb_sd
    global_indices = np.arange(len(support))
    signs_global = np.random.default_rng(SEED).choice(
        np.array([-1.0, 1.0]), size=(args.draws, len(support))
    )
    # Preserve the exact common sign matrix compactly.  Main-model coefficient
    # shifts are stored below; LOFO shifts are reproducible from these packed
    # signs, the registered code, and the fitted inputs without adding a large
    # outcome artifact to git.
    draw_store = {
        "common_signs_packbits": np.packbits(signs_global > 0, axis=1),
        "common_signs_shape": np.asarray(signs_global.shape, dtype=np.int64),
    }
    failures = []
    models = {}

    profile_columns = [
        ((((quintiles == q)[:, None]) & post[None, :]).reshape(-1).astype(float))
        for q in (2, 3, 4, 5)
    ]
    profile_labels = ["Q{}_x_post".format(q) for q in (2, 3, 4, 5)]
    for structure in ("baseline", "SOC2_x_post", "SOC2_x_calendar_month"):
        model_id = "profile_{}".format(structure)
        models[model_id] = fit_model(
            model_id, young, older, support, majors, global_indices,
            profile_columns, profile_labels, webb_z, post, structure, signs_global
        )
    corrected = float(models["profile_baseline"]["fit"].beta[3])
    if not np.isclose(corrected, EXPECTED_CORRECTED, atol=1e-10, rtol=0):
        raise RuntimeError("corrected baseline failed: {} != {}".format(
            corrected, EXPECTED_CORRECTED
        ))

    # Continuous score is centered within SOC2 and scaled once on preperiod stock.
    within_raw = np.empty(len(support), float)
    for group in sorted(set(majors.tolist())):
        mask = majors == group
        within_raw[mask] = exposure_values[mask] - weighted_mean(
            exposure_values[mask], pre_stock[mask]
        )
    within_scale = weighted_sd(within_raw, pre_stock)
    within_z = within_raw / within_scale
    continuous_columns = [(within_z[:, None] * post[None, :]).reshape(-1)]
    for structure in ("baseline", "SOC2_x_post", "SOC2_x_calendar_month"):
        model_id = "continuous_{}".format(structure)
        models[model_id] = fit_model(
            model_id, young, older, support, majors, global_indices,
            continuous_columns, ["within_SOC2_beta_z_x_post"],
            webb_z, post, structure, signs_global
        )

    # Family-by-quintile support precedes the direct-tail changed population.
    eligible_groups = sorted(
        group for group in set(majors.tolist())
        if np.any((majors == group) & (quintiles == 1))
        and np.any((majors == group) & (quintiles == 5))
    )
    direct_mask = np.isin(majors, eligible_groups) & np.isin(quintiles, [1, 5])
    direct_indices = global_indices[direct_mask]
    direct_support = [support[index] for index in direct_indices]
    direct_major = majors[direct_mask]
    direct_q = quintiles[direct_mask]
    direct_young, direct_older = young[direct_mask], older[direct_mask]
    direct_webb = webb_z[direct_mask]
    direct_columns = [
        (((direct_q == 5)[:, None]) & post[None, :]).reshape(-1).astype(float)
    ]
    for structure in ("baseline", "SOC2_x_post", "SOC2_x_calendar_month"):
        model_id = "direct_{}".format(structure)
        models[model_id] = fit_model(
            model_id, direct_young, direct_older, direct_support, direct_major,
            direct_indices, direct_columns, ["Q5_x_post"], direct_webb,
            post, structure, signs_global
        )
    direct_pre_stock = pre_stock[direct_mask]
    direct_share = float(direct_pre_stock.sum() / pre_stock.sum())

    profile_rows, joint_rows, paired_rows = [], [], []
    information_rows, occupation_rows, family_rows = [], [], []
    profile_info_reference = {}
    for structure in ("baseline", "SOC2_x_post", "SOC2_x_calendar_month"):
        model = models["profile_{}".format(structure)]
        rows, tests = profile_summaries(model)
        profile_rows.extend(rows)
        joint_rows.extend(tests)
        for target, label in zip(model["target_indices"], model["target_labels"]):
            reference = profile_info_reference.get(label)
            info = append_information(
                model, target, label, information_rows, occupation_rows, family_rows,
                reference_information=reference,
            )
            if structure == "baseline":
                profile_info_reference[label] = info["nuisance_adjusted_fisher_information"]
            draw_store["{}__{}".format(model["model_id"], label)] = model["shifts"][:, target]
    baseline_profile = models["profile_baseline"]
    for structure in ("SOC2_x_post", "SOC2_x_calendar_month"):
        model = models["profile_{}".format(structure)]
        for index, label in enumerate(profile_labels):
            paired_rows.append(paired_row(
                model, baseline_profile, index, index,
                "{}_minus_profile_baseline__{}".format(model["model_id"], label),
            ))

    direct_rows = []
    direct_info_reference = None
    for structure in ("baseline", "SOC2_x_post", "SOC2_x_calendar_month"):
        model = models["direct_{}".format(structure)]
        summary = scalar_bootstrap(model, 0)
        direct_rows.append({
            "analysis_status": LABEL,
            "model_id": model["model_id"],
            "structure": structure,
            "changed_population": True,
            "eligible_SOC2_groups": "|".join(eligible_groups),
            "support_occupations": len(direct_support),
            "full_support_occupation_share": float(len(direct_support) / len(support)),
            "preperiod_stock_share_of_full_support": direct_share,
            "SOC2_post_reference": model["reference"],
            **summary,
        })
        info = append_information(
            model, 0, "Q5_x_post", information_rows, occupation_rows, family_rows,
            reference_information=direct_info_reference,
        )
        if structure == "baseline":
            direct_info_reference = info["nuisance_adjusted_fisher_information"]
        draw_store["{}__Q5_x_post".format(model["model_id"])] = model["shifts"][:, 0]
    for structure in ("SOC2_x_post", "SOC2_x_calendar_month"):
        model = models["direct_{}".format(structure)]
        direct_rows[-2 if structure == "SOC2_x_post" else -1].update({
            "paired_change_from_direct_baseline": paired_row(
                model, models["direct_baseline"], 0, 0,
                "{}_minus_direct_baseline".format(model["model_id"]),
            )["coefficient_difference"]
        })
        paired_rows.append(paired_row(
            model, models["direct_baseline"], 0, 0,
            "{}_minus_direct_baseline".format(model["model_id"]),
        ))

    continuous_rows = []
    continuous_info_reference = None
    for structure in ("baseline", "SOC2_x_post", "SOC2_x_calendar_month"):
        model = models["continuous_{}".format(structure)]
        continuous_rows.append({
            "analysis_status": LABEL,
            "model_id": model["model_id"],
            "structure": structure,
            "score_definition": "Eloundou_beta_minus_preperiod_stock_weighted_SOC2_mean",
            "scale_raw_beta_units_per_one_z": within_scale,
            "common_slope_across_SOC2_families": True,
            "support_occupations": len(support),
            "SOC2_post_reference": model["reference"],
            **scalar_bootstrap(model, 0),
        })
        info = append_information(
            model, 0, "within_SOC2_beta_z_x_post", information_rows,
            occupation_rows, family_rows,
            reference_information=continuous_info_reference,
        )
        if structure == "baseline":
            continuous_info_reference = info["nuisance_adjusted_fisher_information"]
        draw_store["{}__within_beta".format(model["model_id"])] = model["shifts"][:, 0]
    for structure in ("SOC2_x_post", "SOC2_x_calendar_month"):
        paired_rows.append(paired_row(
            models["continuous_{}".format(structure)],
            models["continuous_baseline"], 0, 0,
            "continuous_{}_minus_continuous_baseline".format(structure),
        ))

    # Family support includes preperiod support and fitted Q-profile information.
    q_month_info = {}
    for target, label in enumerate(profile_labels):
        info = information_for_target(models["profile_SOC2_x_calendar_month"], target)
        q_month_info[label] = info["occupation_contribution"]
    support_rows = []
    for group in sorted(set(majors.tolist())):
        mask = majors == group
        group_pre = float(pre_stock[mask].sum())
        row = {
            "analysis_status": LABEL,
            "SOC2": group,
            "SOC2_name": SOC2_NAMES.get(group, group),
            "occupations": int(mask.sum()),
            "preperiod_stock": group_pre,
            "preperiod_stock_share": float(group_pre / pre_stock.sum()),
            "beta_min": float(exposure_values[mask].min()),
            "beta_max": float(exposure_values[mask].max()),
            "beta_preperiod_weighted_mean": weighted_mean(exposure_values[mask], pre_stock[mask]),
            "beta_preperiod_weighted_sd": float(np.sqrt(np.average(
                np.square(exposure_values[mask] - weighted_mean(
                    exposure_values[mask], pre_stock[mask]
                )), weights=pre_stock[mask]
            ))),
            "distinct_quintiles": int(len(np.unique(quintiles[mask]))),
            "quintiles_present": "|".join(str(value) for value in sorted(np.unique(quintiles[mask]))),
            "contains_Q1_and_Q5": bool(
                np.any(quintiles[mask] == 1) and np.any(quintiles[mask] == 5)
            ),
            "direct_tail_eligible": group in eligible_groups,
            "indirect_comparison_note": (
                "direct Q1-Q5 within family" if group in eligible_groups
                else "connects only through observed intermediate quintiles under common profile coefficients"
            ),
        }
        for q in range(1, 6):
            qm = mask & (quintiles == q)
            row["Q{}_occupations".format(q)] = int(qm.sum())
            row["Q{}_preperiod_stock_share_within_SOC2".format(q)] = (
                float(pre_stock[qm].sum() / group_pre) if group_pre > 0 else np.nan
            )
        for label in profile_labels:
            value = float(q_month_info[label][mask].sum())
            total = float(q_month_info[label].sum())
            row["{}_conditional_information".format(label)] = value
            row["{}_conditional_information_share".format(label)] = value / total
        support_rows.append(row)

    direct_support_rows = []
    for local, global_index in enumerate(direct_indices):
        code = support[global_index]
        direct_support_rows.append({
            "analysis_status": LABEL,
            "occupation_code": code,
            "occupation_name": data["names"].get(code, ""),
            "SOC2": majors[global_index],
            "SOC2_name": SOC2_NAMES.get(majors[global_index], majors[global_index]),
            "tail": "Q5" if quintiles[global_index] == 5 else "Q1",
            "beta_score": exposure_values[global_index],
            "preperiod_stock": pre_stock[global_index],
            "preperiod_stock_share_in_direct_population": float(
                pre_stock[global_index] / direct_pre_stock.sum()
            ),
            "preperiod_stock_share_in_full_population": float(
                pre_stock[global_index] / pre_stock.sum()
            ),
        })

    # Leave-one-family-out for the four primary within-family models.
    lofo_rows = []
    parents = (
        ("profile_SOC2_x_post", "profile", "SOC2_x_post"),
        ("profile_SOC2_x_calendar_month", "profile", "SOC2_x_calendar_month"),
        ("continuous_SOC2_x_post", "continuous", "SOC2_x_post"),
        ("continuous_SOC2_x_calendar_month", "continuous", "SOC2_x_calendar_month"),
    )
    for parent_id, family, structure in parents:
        parent = models[parent_id]
        for omitted in sorted(set(majors.tolist())):
            keep = majors != omitted
            local_indices = global_indices[keep]
            try:
                if family == "profile":
                    local_q = quintiles[keep]
                    local_columns = [
                        ((((local_q == q)[:, None]) & post[None, :]).reshape(-1).astype(float))
                        for q in (2, 3, 4, 5)
                    ]
                    labels = profile_labels
                else:
                    local_columns = [
                        (within_z[keep, None] * post[None, :]).reshape(-1)
                    ]
                    labels = ["within_SOC2_beta_z_x_post"]
                child_id = "{}_LOFO_SOC2_{}".format(parent_id, omitted)
                child = fit_model(
                    child_id, young[keep], older[keep],
                    [support[index] for index in local_indices], majors[keep],
                    local_indices, local_columns, labels, webb_z[keep], post,
                    structure, signs_global,
                )
                for target, label in zip(child["target_indices"], labels):
                    summary = scalar_bootstrap(child, target)
                    parent_target = labels.index(label)
                    pair = paired_row(
                        child, parent, target, parent_target,
                        "{}_minus_{}".format(child_id, parent_id),
                    )
                    info = information_for_target(child, target)
                    lofo_rows.append({
                        "analysis_status": LABEL,
                        "parent_model": parent_id,
                        "omitted_SOC2": omitted,
                        "omitted_SOC2_name": SOC2_NAMES.get(omitted, omitted),
                        "target": label,
                        "remaining_occupations": int(keep.sum()),
                        "omitted_preperiod_stock_share": float(pre_stock[~keep].sum() / pre_stock.sum()),
                        "quintiles_recomputed": False,
                        "continuous_center_and_scale_recomputed": False,
                        **summary,
                        "movement_from_parent": pair["coefficient_difference"],
                        "paired_movement_se": pair["paired_bootstrap_se"],
                        "paired_movement_ci_lower": pair["paired_ci_lower"],
                        "paired_movement_ci_upper": pair["paired_ci_upper"],
                        "paired_movement_MDE80": pair["paired_normal_theory_MDE80"],
                        "nuisance_adjusted_fisher_information": info[
                            "nuisance_adjusted_fisher_information"
                        ],
                        "effective_occupation_information_count": info[
                            "effective_occupation_information_count"
                        ],
                        "top_five_occupation_information_share": info[
                            "top_five_occupation_information_share"
                        ],
                    })
            except Exception as error:
                failures.append({
                    "analysis_status": LABEL,
                    "stage": "leave_one_family_out",
                    "parent_model": parent_id,
                    "omitted_SOC2": omitted,
                    "error_type": type(error).__name__,
                    "message": str(error),
                })

    # Direct-tail family ranking and separate young/older tail paths.
    direct_month = models["direct_SOC2_x_calendar_month"]
    direct_info = information_for_target(direct_month, 0)
    direct_family_information = {}
    for index, group in enumerate(direct_major):
        direct_family_information[group] = direct_family_information.get(group, 0.0) + float(
            direct_info["occupation_contribution"][index]
        )
    selected_groups = sorted(
        eligible_groups,
        key=lambda group: (-direct_family_information[group], group),
    )
    selection_rows = []
    for rank, group in enumerate(selected_groups, start=1):
        selection_rows.append({
            "analysis_status": LABEL,
            "selection_rank": rank,
            "selection_rule": "descending direct-tail SOC2-by-month Q5 nuisance-adjusted information; ties by SOC2",
            "selected_by_coefficient_sign": False,
            "SOC2": group,
            "SOC2_name": SOC2_NAMES.get(group, group),
            "conditional_information": direct_family_information[group],
            "conditional_information_share": float(
                direct_family_information[group] /
                direct_info["nuisance_adjusted_fisher_information"]
            ),
        })
    trajectory_rows = []
    for group in selected_groups:
        for tail_value, tail_name in ((1, "Q1"), (5, "Q5")):
            mask = (majors == group) & (quintiles == tail_value)
            ys = young[mask].sum(axis=0)
            os = older[mask].sum(axis=0)
            pre_y = float(ys[pre].mean())
            pre_o = float(os[pre].mean())
            for month_index, month in enumerate(months):
                y_value, o_value = float(ys[month_index]), float(os[month_index])
                trajectory_rows.append({
                    "analysis_status": LABEL,
                    "SOC2": group,
                    "SOC2_name": SOC2_NAMES.get(group, group),
                    "tail": tail_name,
                    "month": month,
                    "young_weighted_employment_stock": y_value,
                    "older_weighted_employment_stock": o_value,
                    "young_preperiod_mean_index_100": 100.0 * y_value / pre_y,
                    "older_preperiod_mean_index_100": 100.0 * o_value / pre_o,
                    "log_young_to_older_stock_ratio": (
                        float(math.log(y_value / o_value)) if y_value > 0 and o_value > 0 else np.nan
                    ),
                    "sampling_interval_available": False,
                    "interval_note": "descriptive weighted-stock path; aggregate final weights do not supply a design variance",
                })

    # Add occupation names after all contributor rows are built.
    for row in occupation_rows:
        row["occupation_name"] = data["names"].get(row["occupation_code"], "")

    # Relative information values require reference rows already populated.
    write_csv(args.output_dir / "FAMILY_QUINTILE_SUPPORT.csv", support_rows)
    write_csv(args.output_dir / "PROFILE_COEFFICIENTS.csv", profile_rows)
    write_csv(args.output_dir / "PROFILE_JOINT_TESTS.csv", joint_rows)
    write_csv(args.output_dir / "PAIRED_PROFILE_CHANGES.csv", paired_rows)
    write_csv(args.output_dir / "DIRECT_TAIL_SUPPORT.csv", direct_support_rows)
    write_csv(args.output_dir / "DIRECT_TAIL_MODELS.csv", direct_rows)
    write_csv(args.output_dir / "CONTINUOUS_WITHIN_FAMILY_MODELS.csv", continuous_rows)
    write_csv(args.output_dir / "LEAVE_ONE_FAMILY_OUT.csv", lofo_rows)
    if failures:
        write_csv(args.output_dir / "MODEL_FAILURES.csv", failures)
    else:
        write_csv(args.output_dir / "MODEL_FAILURES.csv", [{
            "analysis_status": LABEL,
            "stage": "all",
            "parent_model": "",
            "omitted_SOC2": "",
            "error_type": "",
            "message": "NO_MODEL_FAILURES",
        }])
    write_csv(args.output_dir / "INFORMATION_DIAGNOSTICS.csv", information_rows)
    write_csv(args.output_dir / "OCCUPATION_INFORMATION.csv", occupation_rows)
    write_csv(args.output_dir / "FAMILY_INFORMATION.csv", family_rows)
    write_csv(args.output_dir / "FAMILY_TAIL_TRAJECTORIES.csv", trajectory_rows)
    write_csv(args.output_dir / "FAMILY_TRAJECTORY_SELECTION.csv", selection_rows)
    np.savez_compressed(args.output_dir / "CENTERED_BOOTSTRAP_DRAWS.npz", **draw_store)

    build_findings(
        args.output_dir / "FINDINGS.md", models, eligible_groups, direct_share,
        within_scale, lofo_rows, failures, selection_rows,
    )
    output_hashes = {
        path.name: sha256(path)
        for path in sorted(args.output_dir.iterdir())
        if path.is_file() and path.name not in ("EXECUTION_RECEIPT.json", "SELF_CHECK.json")
    }
    receipt = {
        "record": "YAX R3 within-family analyses FAM-01 through FAM-06",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "protected_refs": {
            "v1.1-design-freeze": subprocess.check_output(
                ["git", "rev-parse", "v1.1-design-freeze^{}"], cwd=ROOT, text=True
            ).strip(),
            "v1.1-confirmatory-results": subprocess.check_output(
                ["git", "rev-parse", "v1.1-confirmatory-results^{}"], cwd=ROOT, text=True
            ).strip(),
        },
        "input_hashes": {
            **data["authenticated"]["hashes"],
            "repair_microdata": sha256(args.repair_microdata),
        },
        "corrected_calendar_build": cell_build,
        "corrected_calendar_months": months,
        "corrected_baseline_reproduced": corrected,
        "historical_support_occupations": len(support),
        "historical_support_hash": support_hash(support),
        "direct_tail_SOC2_groups": eligible_groups,
        "direct_tail_occupations": len(direct_support),
        "direct_tail_preperiod_stock_share": direct_share,
        "continuous_score": {
            "definition": "beta minus preperiod-stock-weighted SOC2 mean",
            "scale_raw_beta_units": within_scale,
            "common_slope_restriction": True,
        },
        "bootstrap": {
            "draws": args.draws,
            "seed": SEED,
            "common_occupation_Rademacher_multipliers": True,
            "global_sign_matrix_stored": "bit_packed_exactly",
        },
        "information_formula": {
            "fitted_weight": "h_i=T_i*p_i*(1-p_i)",
            "target_residual": "r=M_Z^h A_FE x",
            "fisher_information": "sum_i h_i*r_i^2",
            "effective_occupations": "1/sum_o s_o^2",
            "MDE80": "(z_.975+z_.80)*occupation_cluster_SE",
        },
        "model_failures": failures,
        "implementation": {
            "script": str(pathlib.Path(__file__).resolve().relative_to(ROOT)),
            "script_sha256": sha256(pathlib.Path(__file__).resolve()),
            "spec": str((HERE / "ANALYSIS_SPEC.md").relative_to(ROOT)),
            "spec_sha256": sha256(HERE / "ANALYSIS_SPEC.md"),
        },
        "output_hashes": output_hashes,
        "raw_microdata_written": False,
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({
        "status": "PASS_R3_WITHIN_FAMILY",
        "corrected_baseline": corrected,
        "profile_SOC2_post_Q5": float(models["profile_SOC2_x_post"]["fit"].beta[3]),
        "profile_SOC2_month_Q5": float(models["profile_SOC2_x_calendar_month"]["fit"].beta[3]),
        "direct_SOC2_month": float(models["direct_SOC2_x_calendar_month"]["fit"].beta[0]),
        "continuous_SOC2_month": float(models["continuous_SOC2_x_calendar_month"]["fit"].beta[0]),
        "direct_groups": eligible_groups,
        "lofo_rows": len(lofo_rows),
        "failures": failures,
    }, indent=2, sort_keys=True))


def parser():
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--repair-microdata", type=pathlib.Path, required=True)
    value.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    value.add_argument("--lookup", type=pathlib.Path,
                       default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    value.add_argument("--computerization", type=pathlib.Path,
                       default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    value.add_argument("--rule-b-values", type=pathlib.Path,
                       default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    value.add_argument("--bridge", type=pathlib.Path,
                       default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    value.add_argument("--first-access-receipt", type=pathlib.Path,
                       default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    value.add_argument("--characteristics", type=pathlib.Path,
                       default=ROOT / "yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv")
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    value.add_argument("--draws", type=int, default=DRAWS)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
