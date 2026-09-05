#!/usr/bin/env python3
"""Run the post-outcome YAX referee-revision core analyses.

POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1.

This program leaves the protected design and result artifacts immutable.  It
authenticates the same inputs used by the frozen estimator, reproduces the
frozen primary coefficient, and then runs only analyses declared in
ANALYSIS_SPEC_BEFORE_EXECUTION.md before this program was executed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import itertools
import json
import math
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
LABEL = "POST-OUTCOME EXPLORATORY -- NOT PART OF CONFIRMATORY YAX v1.1"
MEASURES = (
    "aioe_admin_equal", "aioe_ability_direct", "aioe_oews2018_source_weighted",
    "dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma",
)
AIOE = MEASURES[:3]
ELOUNDOU = MEASURES[3:]
DRAWS = 999
SEED = 2026090500
PERMUTATION_SEED = 2026090502
PRIMARY_EXPECTED = -0.13107397642233506
COMMON_SUPPORT_HASH = "1e184b27678b7978d4b15e618db5b44f44b5e9ec1b50b69b53093ec62e0ce462"


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


FROZEN = import_path("yax_revision_frozen", ROOT / "yax/analysis/run_frozen_v11.py")
V4 = import_path(
    "yax_revision_v4", ROOT / "yax/analysis/postoutcome_v4_supplementary/run_v4_alignment.py"
)
P3 = import_path(
    "yax_revision_phase3", ROOT / "yax/analysis/postoutcome_phase3_final/run_phase3.py"
)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def support_hash(codes: list[str]) -> str:
    return hashlib.sha256("".join(f"{code}\n" for code in sorted(codes)).encode()).hexdigest()


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"refusing to write empty output {path}")
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def weighted_mean(values: np.ndarray, weights: np.ndarray) -> float:
    return float(np.average(values, weights=weights))


def weighted_sd(values: np.ndarray, weights: np.ndarray) -> float:
    mean = weighted_mean(values, weights)
    return float(np.sqrt(np.average(np.square(values - mean), weights=weights)))


def weighted_corr(left: np.ndarray, right: np.ndarray, weights: np.ndarray) -> float:
    lm, rm = weighted_mean(left, weights), weighted_mean(right, weights)
    numerator = np.sum(weights * (left - lm) * (right - rm))
    denominator = math.sqrt(
        float(np.sum(weights * np.square(left - lm)) * np.sum(weights * np.square(right - rm)))
    )
    return float(numerator / denominator)


def bootstrap_linear(
    fit, influence: np.ndarray, contrast: np.ndarray, signs: np.ndarray
) -> tuple[dict, np.ndarray]:
    estimate = float(contrast @ fit.beta)
    vector = influence @ contrast
    centered = signs @ vector
    analytic_cov = np.diag(np.square(fit.standard_error))
    # The estimator exposes marginal SEs, while paired inference is based on
    # the common multiplier covariance, which is the relevant joint object.
    bootstrap_se = float(np.std(centered, ddof=1))
    if np.count_nonzero(contrast) == 1:
        analytic_se = float(fit.standard_error[np.flatnonzero(contrast)[0]])
    else:
        analytic_se = bootstrap_se
    studentizer = analytic_se if analytic_se > 0 else bootstrap_se
    critical = float(np.quantile(np.abs(centered / studentizer), .95, method="higher"))
    pvalue = float((1 + np.sum(np.abs(centered / studentizer) >= abs(estimate / studentizer))) /
                   (len(centered) + 1))
    return ({
        "coefficient": estimate,
        "analytic_or_paired_se": analytic_se,
        "paired_bootstrap_se": bootstrap_se,
        "ci_lower": estimate - critical * studentizer,
        "ci_upper": estimate + critical * studentizer,
        "bootstrap_p_value": pvalue,
        "bootstrap_critical": critical,
        "draws": len(centered),
    }, centered)


def fit_group_model(
    panel: pd.DataFrame,
    support: list[str],
    months: list[str],
    groups: np.ndarray,
    webb_map: dict,
):
    young, older = FROZEN.panel_arrays(panel, support, months)
    weights = (young + older).sum(axis=1)
    webb = np.array([webb_map[code] for code in support], float)
    webb = (webb - weighted_mean(webb, weights)) / weighted_sd(webb, weights)
    post = np.array([month >= "2023-01" for month in months])
    levels = sorted(int(value) for value in np.unique(groups))
    base = levels[0]
    columns, labels = [], []
    for level in levels[1:]:
        columns.append((((groups == level)[:, None]) & post[None, :]).reshape(-1).astype(float))
        labels.append(f"group_{level}_vs_{base}_x_post")
    columns.append((webb[:, None] * post[None, :]).reshape(-1))
    labels.append("Webb_software_z_x_post")
    fit, influence = FROZEN.fit_with_influence(young, older, np.column_stack(columns))
    return fit, influence, weights, labels


def weighted_quintile_with_cuts(values: np.ndarray, weights: np.ndarray):
    order = np.argsort(values, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    cuts = np.array([
        values[order[min(np.searchsorted(cumulative, share * cumulative[-1], side="left"),
                         len(values) - 1)]]
        for share in (.2, .4, .6, .8)
    ])
    if np.any(cuts[:-1] >= cuts[1:]):
        raise ValueError(f"collapsed employment-weighted cuts: {cuts.tolist()}")
    return np.searchsorted(cuts, values, side="left") + 1, cuts


def load_data(args: argparse.Namespace) -> dict:
    data = V4.load_inputs(args)
    baseline = FROZEN.prepare_model(
        data["panel"], data["occupations"], data["static_months"],
        data["exposures"]["dv_rating_beta"]["A"],
        data["computers"]["webb_pct_software"], scale="q5_q1",
    )
    fit, _ = FROZEN.fit_with_influence(
        baseline["young"], baseline["older"], baseline["regressors"]
    )
    reproduced = float(fit.beta[baseline["target"]])
    if not np.isclose(reproduced, PRIMARY_EXPECTED, atol=1e-10, rtol=0):
        raise RuntimeError(f"frozen primary failed: {reproduced} != {PRIMARY_EXPECTED}")
    data["baseline_reproduced"] = reproduced
    return data


def characteristics_frame(args: argparse.Namespace) -> pd.DataFrame:
    frame = pd.read_csv(args.characteristics, dtype={"census2018": str})
    frame["census2018"] = frame.census2018.str.zfill(4)
    return frame.set_index("census2018", drop=False)


def run_placebos(args: argparse.Namespace, data: dict, chars: pd.DataFrame) -> dict:
    names = {
        "beta_ai": "dv_rating_beta",
        "wage": "log_mean_annual_wage",
        "education": "required_education_category_index",
        "cognitive": "cognitive_ability_importance",
        "telework": "dingel_neiman_telework",
        "stem": "stem_major_group_share",
    }
    webb_map = data["computers"]["webb_pct_software"]
    support = sorted(code for code in data["occupations"] if code in chars.index and
                     np.isfinite(webb_map.get(code, np.nan)) and
                     all(np.isfinite(chars.at[code, column]) for column in names.values()))
    young, older = FROZEN.panel_arrays(data["panel"], support, data["static_months"])
    weights = (young + older).sum(axis=1)
    signs = np.random.default_rng(SEED + 10).choice(
        np.array([-1., 1.]), size=(DRAWS, len(support))
    )
    result_rows, member_rows, draws_by_name, top_sets = [], [], {}, {}
    failures = []
    for order_index, (label, column) in enumerate(names.items()):
        values = chars.loc[support, column].to_numpy(float)
        grouping = "employment_weighted_tie_preserving_quintiles"
        cuts = None
        try:
            groups, cuts = weighted_quintile_with_cuts(values, weights)
        except ValueError as error:
            failures.append({"architecture": label, "requested": "quintiles", "reason": str(error)})
            if label == "telework":
                groups = np.where(values == 0, 1, np.where(values < 1, 2, 3))
                grouping = "natural_groups_zero_partial_full"
            elif label == "stem":
                groups = np.where(values <= 0, 1, 2)
                grouping = "natural_groups_non_STEM_STEM_major_group"
            else:
                raise
        fit, influence, _, labels = fit_group_model(
            data["panel"], support, data["static_months"], groups, webb_map
        )
        target = len(labels) - 2
        contrast = np.zeros(len(labels)); contrast[target] = 1
        summary, centered = bootstrap_linear(fit, influence, contrast, signs)
        draws_by_name[label] = centered
        top = int(np.max(groups)); bottom = int(np.min(groups))
        top_sets[label] = {code for code, group in zip(support, groups) if group == top}
        result_rows.append({
            "analysis_status": LABEL, "architecture": label, "source_column": column,
            "grouping": grouping, "support_occupations": len(support),
            "support_hash_sha256": support_hash(support), "bottom_group": bottom,
            "top_group": top, "cuts_json": json.dumps(cuts.tolist()) if cuts is not None else "",
            "top_occupation_count": int(np.sum(groups == top)),
            "top_employment_share": float(weights[groups == top].sum() / weights.sum()),
            **summary,
        })
        for code, value, group, weight in zip(support, values, groups, weights):
            member_rows.append({
                "architecture": label, "occupation_code": code,
                "occupation_name": data["names"].get(code, code), "raw_value": value,
                "group": int(group), "employment_weight": float(weight),
            })
    paired_rows = []
    ai_row = next(row for row in result_rows if row["architecture"] == "beta_ai")
    for label in names:
        if label == "beta_ai":
            continue
        delta = ai_row["coefficient"] - next(
            row["coefficient"] for row in result_rows if row["architecture"] == label
        )
        centered = draws_by_name["beta_ai"] - draws_by_name[label]
        se = float(np.std(centered, ddof=1))
        critical = float(np.quantile(np.abs(centered / se), .95, method="higher"))
        paired_rows.append({
            "analysis_status": LABEL, "contrast": f"beta_ai_minus_{label}",
            "coefficient_difference": delta, "paired_se": se,
            "ci_lower": delta - critical * se, "ci_upper": delta + critical * se,
            "paired_p_value": float((1 + np.sum(np.abs(centered / se) >= abs(delta / se))) /
                                     (DRAWS + 1)),
            "q_top_jaccard": len(top_sets["beta_ai"] & top_sets[label]) /
                             len(top_sets["beta_ai"] | top_sets[label]),
            "common_multipliers": True,
        })
    write_csv(args.output_dir / "PLACEBO_BENCHMARK.csv", result_rows)
    write_csv(args.output_dir / "PLACEBO_PAIRED_DIFFERENCES.csv", paired_rows)
    write_csv(args.output_dir / "PLACEBO_MEMBERSHIP.csv", member_rows)
    write_json(args.output_dir / "PLACEBO_GROUPING_FAILURES.json", failures)
    return {"support": len(support), "results": result_rows, "paired": paired_rows,
            "failures": failures}


def run_reference_and_exclusions(args: argparse.Namespace, data: dict) -> dict:
    exposure = data["exposures"]["dv_rating_beta"]["A"]
    webb = data["computers"]["webb_pct_software"]
    prepared = FROZEN.prepare_model(
        data["panel"], data["occupations"], data["static_months"], exposure, webb,
        scale="q5_q1",
    )
    fit, influence = FROZEN.fit_with_influence(
        prepared["young"], prepared["older"], prepared["regressors"]
    )
    signs = np.random.default_rng(SEED + 20).choice(
        np.array([-1., 1.]), size=(DRAWS, len(prepared["occupations"]))
    )
    contrasts = {
        "Q5_minus_Q1": np.array([0., 0., 0., 1., 0.]),
        "Q5_minus_Q2": np.array([-1., 0., 0., 1., 0.]),
        "Q5_minus_Q4": np.array([0., 0., -1., 1., 0.]),
        "Q4_minus_Q2": np.array([-1., 0., 1., 0., 0.]),
        "Q5_minus_Q3": np.array([0., -1., 0., 1., 0.]),
    }
    contrast_rows = []
    for label, contrast in contrasts.items():
        item, _ = bootstrap_linear(fit, influence, contrast, signs)
        contrast_rows.append({"analysis_status": LABEL, "contrast": label,
                              "support_occupations": len(prepared["occupations"]), **item})
    # The same fitted model re-expressed relative to Q3.
    for q, index in ((1, None), (2, 0), (3, 1), (4, 2), (5, 3)):
        if q == 3:
            estimate = 0.0
        elif q == 1:
            estimate = -float(fit.beta[1])
        else:
            estimate = float(fit.beta[index] - fit.beta[1])
        contrast_rows.append({"analysis_status": LABEL, "contrast": f"Q{q}_minus_Q3",
                              "support_occupations": len(prepared["occupations"]),
                              "coefficient": estimate, "re_reference_only": True})
    write_csv(args.output_dir / "REFERENCE_CONTRASTS.csv", contrast_rows)

    values = np.array([exposure[code] for code in prepared["occupations"]], float)
    quintiles = FROZEN.weighted_quintiles(values, prepared["weights"])
    young, older = FROZEN.panel_arrays(
        data["panel"], prepared["occupations"], data["all_months"]
    )
    paths = []
    for q in (1, 5):
        mask = quintiles == q
        y, o = young[mask].sum(axis=0), older[mask].sum(axis=0)
        ratio = np.divide(y, o, out=np.full_like(y, np.nan), where=o > 0)
        series = {"young_stock": y, "older_stock": o, "young_older_ratio": ratio}
        for normalization, base_months in (
            ("mean_observed_2019", [i for i, m in enumerate(data["all_months"]) if m[:4] == "2019"]),
            ("mean_observed_2022", [i for i, m in enumerate(data["all_months"]) if m[:4] == "2022"]),
        ):
            for object_name, array in series.items():
                denominator = float(np.nanmean(array[base_months]))
                for month, raw in zip(data["all_months"], array):
                    paths.append({
                        "analysis_status": LABEL, "quintile": q, "month": month,
                        "object": object_name, "normalization": normalization,
                        "raw_value": float(raw), "index_100": float(100 * raw / denominator),
                    })
    write_csv(args.output_dir / "Q1_Q5_STOCK_PATHS.csv", paths)

    _, _, groups = FROZEN.comp_maps(args.computerization)
    exclusion_rows = []
    for group, description in (("35", "food_preparation_and_serving"),
                               ("15", "computer_and_mathematical"),
                               ("43", "office_and_administrative_support")):
        support = [code for code in data["occupations"] if groups.get(code) != group]
        model, *_ = FROZEN.estimate_static(
            data["panel"], support, data["static_months"], exposure, webb,
            scale="q5_q1", seed=SEED + 30 + int(group),
        )
        item = model["coefficients"][model["target_label"]]
        exclusion_rows.append({
            "analysis_status": LABEL, "exclusion": description, "major_group": group,
            "support_occupations": model["occupations"], **item,
        })
    write_csv(args.output_dir / "BROAD_GROUP_EXCLUSIONS.csv", exclusion_rows)
    return {"contrasts": contrast_rows, "paths": len(paths), "exclusions": exclusion_rows}


def standardize(values: np.ndarray, weights: np.ndarray):
    mean, sd = weighted_mean(values, weights), weighted_sd(values, weights)
    return (values - mean) / sd, mean, sd


def continuous_fit(data: dict, support: list[str], raw_columns: dict[str, np.ndarray],
                   weights: np.ndarray, signs: np.ndarray, standardize_columns: bool = True):
    young, older = FROZEN.panel_arrays(data["panel"], support, data["static_months"])
    post = np.array([month >= "2023-01" for month in data["static_months"]])
    z, moments = {}, {}
    for name, values in raw_columns.items():
        standardized, mean, sd = standardize(values, weights)
        z[name] = standardized if standardize_columns else values
        moments[name] = {"mean": mean, "sd": sd}
    x = np.column_stack([(z[name][:, None] * post[None, :]).reshape(-1) for name in raw_columns])
    fit, influence = FROZEN.fit_with_influence(young, older, x)
    rows, draw_map = [], {}
    for index, name in enumerate(raw_columns):
        contrast = np.zeros(len(raw_columns)); contrast[index] = 1
        item, centered = bootstrap_linear(fit, influence, contrast, signs)
        rows.append({"term": name, **item})
        draw_map[name] = centered
    return fit, influence, rows, draw_map, moments


def run_family_models(args: argparse.Namespace, data: dict, chars: pd.DataFrame) -> dict:
    webb_map = data["computers"]["webb_pct_software"]
    support_sets = [set(code for code in data["occupations"]
                        if np.isfinite(data["exposures"][m]["A"].get(code, np.nan)) and
                        np.isfinite(webb_map.get(code, np.nan))) for m in MEASURES]
    common = sorted(set.intersection(*support_sets))
    if len(common) != 444 or support_hash(common) != COMMON_SUPPORT_HASH:
        raise RuntimeError("literal common support changed")
    pre_weights = chars.loc[common, "preperiod_employment_weight"].to_numpy(float)
    measure_z = {}
    primitive_moments = {}
    for measure in MEASURES:
        values = np.array([data["exposures"][measure]["A"][code] for code in common], float)
        measure_z[measure], mean, sd = standardize(values, pre_weights)
        primitive_moments[measure] = {"mean": mean, "sd": sd}
    webb = np.array([webb_map[code] for code in common], float)
    signs = np.random.default_rng(SEED + 40).choice(np.array([-1., 1.]), size=(DRAWS, len(common)))

    deletion_order = ["dv_rating_alpha", *[m for m in MEASURES if m != "dv_rating_alpha"], None]
    rows, model_records = [], {}
    full_fit = full_draws = full_moments = None

    # First reproduce the previously reported Phase-3/V5.1 F/G construction
    # exactly: primitive z moments are formed on its 463-occupation reference
    # universe, then F/G/Webb are standardized with static outcome stocks on
    # the literal 444-occupation outcome support.
    original_reference, _ = P3.load_reference_components(args.characteristics)
    original_reference = original_reference.set_index("census2018")
    original_F = original_reference.loc[common, "F"].to_numpy(float)
    original_G = original_reference.loc[common, "G"].to_numpy(float)
    original_young, original_older = FROZEN.panel_arrays(
        data["panel"], common, data["static_months"]
    )
    original_outcome_weights = (original_young + original_older).sum(axis=1)
    original_fit, _, original_terms, original_draws, original_moments = continuous_fit(
        data, common, {"F": original_F, "G": original_G, "Webb": webb},
        original_outcome_weights, signs,
    )
    expected_original = (-0.040358886215281616, 0.030893508600474132)
    if not np.allclose(original_fit.beta[:2], expected_original, atol=1e-10, rtol=0):
        raise RuntimeError(
            f"original F/G model did not reproduce: {original_fit.beta[:2]} != {expected_original}"
        )
    for term in original_terms[:2]:
        rows.append({
            "analysis_status": LABEL, "specification": "original_phase3_exact",
            "omitted": "", "term": term["term"], "family_A_count": 3,
            "family_E_count": 3, "support_occupations": len(common),
            "support_hash_sha256": support_hash(common),
            "F_raw_sd": original_moments["F"]["sd"],
            "G_raw_sd": original_moments["G"]["sd"],
            "F_G_weighted_correlation": weighted_corr(original_F, original_G, original_outcome_weights),
            "normalization_universe": "463 primitive reference; 444 outcome-stock F/G scaling",
            **{key: value for key, value in term.items() if key != "term"},
        })
    for omitted in deletion_order:
        aioe = [m for m in AIOE if m != omitted]
        eloundou = [m for m in ELOUNDOU if m != omitted]
        if not aioe or not eloundou:
            raise RuntimeError("leave-one-out removed an entire family")
        A = np.mean(np.column_stack([measure_z[m] for m in aioe]), axis=1)
        E = np.mean(np.column_stack([measure_z[m] for m in eloundou]), axis=1)
        F, G = (A + E) / 2, (A - E) / 2
        fit, influence, terms, draws, moments = continuous_fit(
            data, common, {"F": F, "G": G, "Webb": webb}, pre_weights, signs
        )
        label = "full_six" if omitted is None else f"omit_{omitted}"
        for term in terms[:2]:
            rows.append({
                "analysis_status": LABEL, "specification": label, "omitted": omitted or "",
                "term": term["term"], "family_A_count": len(aioe),
                "family_E_count": len(eloundou), "support_occupations": len(common),
                "support_hash_sha256": support_hash(common),
                "F_raw_sd": moments["F"]["sd"], "G_raw_sd": moments["G"]["sd"],
                "F_G_weighted_correlation": weighted_corr(F, G, pre_weights), **{
                    key: value for key, value in term.items() if key != "term"
                },
            })
        model_records[label] = {"moments": moments, "terms": terms[:2]}
        if omitted is None:
            full_fit, full_draws, full_moments = fit, draws, moments

    # Representative-family and primitive specifications, all on the same support.
    auxiliary = {}
    raw_specs = {
        "representative_AIOE_beta": {
            "AIOE_admin": measure_z["aioe_admin_equal"],
            "Eloundou_beta": measure_z["dv_rating_beta"], "Webb": webb,
        },
        "direct_D_S": {
            "D_alpha": np.array([data["exposures"]["dv_rating_alpha"]["A"][c] for c in common]),
            "S_gamma_minus_alpha": np.array([
                data["exposures"]["dv_rating_gamma"]["A"][c] -
                data["exposures"]["dv_rating_alpha"]["A"][c] for c in common
            ]), "Webb": webb,
        },
    }
    for label, raw in raw_specs.items():
        fit, influence, terms, draws, moments = continuous_fit(
            data, common, raw, pre_weights, signs
        )
        auxiliary[label] = {"terms": terms, "moments": moments}

    # Exact A/E change of basis from full F/G, with all multiplier draws transformed.
    bF, bG = float(full_fit.beta[0]), float(full_fit.beta[1])
    sF, sG = full_moments["F"]["sd"], full_moments["G"]["sd"]
    gamma_A = .5 * (bF / sF + bG / sG)
    gamma_E = .5 * (bF / sF - bG / sG)
    draw_A = .5 * (full_draws["F"] / sF + full_draws["G"] / sG)
    draw_E = .5 * (full_draws["F"] / sF - full_draws["G"] / sG)
    change_basis = {
        "gamma_A_original_family_unit": gamma_A,
        "gamma_E_original_family_unit": gamma_E,
        "paired_se_A": float(np.std(draw_A, ddof=1)),
        "paired_se_E": float(np.std(draw_E, ddof=1)),
        "formula": "0.5*(bF/sF +/- bG/sG)",
        "draws_transformed_consistently": True,
        "basis": "recomputed-on-444 construction sensitivity; the original Phase-3 basis is separately reproduced",
    }

    # Lambda construction grid.  Categorical ranks do not depend on positive
    # rescaling; continuous fixed and restandardized units are both reported.
    D = np.array([data["exposures"]["dv_rating_alpha"]["A"][c] for c in common], float)
    broad = np.array([data["exposures"]["dv_rating_gamma"]["A"][c] for c in common], float)
    S = broad - D
    beta_values = D + .5 * S
    beta_mean, beta_sd = weighted_mean(beta_values, pre_weights), weighted_sd(beta_values, pre_weights)
    grid_rows, member_rows = [], []
    for index, lam in enumerate((0., .25, .5, .75, 1.)):
        raw = D + lam * S
        q, cuts = weighted_quintile_with_cuts(raw, pre_weights)
        fit_q, inf_q, _, labels = fit_group_model(data["panel"], common, data["static_months"], q, webb_map)
        contrast = np.zeros(len(labels)); contrast[len(labels) - 2] = 1
        q_item, _ = bootstrap_linear(fit_q, inf_q, contrast, signs)
        fixed = (raw - beta_mean) / beta_sd
        restd, mean, sd = standardize(raw, pre_weights)
        for normalization, value in (("fixed_beta_scale", fixed), ("restandardized", restd)):
            fit_c, inf_c, terms, _, _ = continuous_fit(
                data, common,
                {"X_lambda": value, "Webb": (webb - weighted_mean(webb, pre_weights)) /
                                             weighted_sd(webb, pre_weights)},
                pre_weights, signs, standardize_columns=False,
            )
            grid_rows.append({
                "analysis_status": LABEL, "lambda": lam, "normalization": normalization,
                "raw_mean": mean, "raw_sd": sd, "beta_anchor_mean": beta_mean,
                "beta_anchor_sd": beta_sd, "q5_vs_q1_coefficient": q_item["coefficient"],
                "q5_vs_q1_ci_lower": q_item["ci_lower"],
                "q5_vs_q1_ci_upper": q_item["ci_upper"],
                "continuous_coefficient": terms[0]["coefficient"],
                "continuous_ci_lower": terms[0]["ci_lower"],
                "continuous_ci_upper": terms[0]["ci_upper"],
                "q_cuts_json": json.dumps(cuts.tolist()),
            })
        for code, group in zip(common, q):
            member_rows.append({"lambda": lam, "occupation_code": code, "quintile": int(group)})
    write_csv(args.output_dir / "FG_LEAVE_ONE_OUT_RESULTS.csv", rows)
    write_json(args.output_dir / "FG_ADDITIONAL_MODELS.json", auxiliary)
    write_json(args.output_dir / "FG_AE_CHANGE_OF_BASIS.json", change_basis)
    write_csv(args.output_dir / "LAMBDA_GRID_RESULTS.csv", grid_rows)
    write_csv(args.output_dir / "LAMBDA_GRID_MEMBERSHIP.csv", member_rows)
    write_json(args.output_dir / "FG_PRIMITIVE_MOMENTS.json", primitive_moments)
    return {"leave_one_out": rows, "auxiliary": auxiliary,
            "change_basis": change_basis, "lambda": grid_rows}


def run_tail_stability(args: argparse.Namespace, data: dict) -> dict:
    webb = data["computers"]["webb_pct_software"]
    supports = [set(code for code in data["occupations"]
                    if np.isfinite(data["exposures"][m]["A"].get(code, np.nan)) and
                    np.isfinite(webb.get(code, np.nan))) for m in MEASURES]
    common = sorted(set.intersection(*supports))
    young, older = FROZEN.panel_arrays(data["panel"], common, data["static_months"])
    weights = (young + older).sum(axis=1)
    signs = np.random.default_rng(SEED + 60).choice(np.array([-1., 1.]), size=(DRAWS, len(common)))
    memberships, influence_share = {}, {}
    for measure in MEASURES:
        prepared = FROZEN.prepare_model(data["panel"], common, data["static_months"],
                                        data["exposures"][measure]["A"], webb, scale="q5_q1")
        values = np.array([data["exposures"][measure]["A"][code] for code in common], float)
        memberships[measure] = FROZEN.weighted_quintiles(values, weights)
        fit, influence = FROZEN.fit_with_influence(prepared["young"], prepared["older"],
                                                   prepared["regressors"])
        target_influence = influence[:, prepared["target"]]
        denom = float(np.sum(np.square(target_influence)))
        influence_share[measure] = np.square(target_influence) / denom
    rows = []
    matrix = np.column_stack([memberships[m] for m in MEASURES])
    for index, code in enumerate(common):
        qs = matrix[index]
        if np.all(qs == 1): classification = "stable_Q1"
        elif np.all(qs == 5): classification = "stable_Q5"
        elif np.any(qs == 1) or np.any(qs == 5): classification = "reclassified_tail_or_middle"
        else: classification = "stable_middle_range"
        rows.append({
            "analysis_status": LABEL, "occupation_code": code,
            "occupation_name": data["names"].get(code, code), "classification": classification,
            "employment_weight": float(weights[index]),
            "mean_squared_influence_share": float(np.mean([influence_share[m][index] for m in MEASURES])),
            **{f"q_{m}": int(memberships[m][index]) for m in MEASURES},
        })
    summary = []
    frame = pd.DataFrame(rows)
    for classification, selected in frame.groupby("classification"):
        summary.append({
            "classification": classification, "occupations": len(selected),
            "employment_share": float(selected.employment_weight.sum() / frame.employment_weight.sum()),
            "mean_estimator_influence_share": float(selected.mean_squared_influence_share.sum()),
        })
    write_csv(args.output_dir / "TAIL_STABILITY_OCCUPATIONS.csv", rows)
    write_csv(args.output_dir / "TAIL_STABILITY_SUMMARY.csv", summary)
    return {"summary": summary}


def run_permutations(args: argparse.Namespace, data: dict) -> dict:
    exposure = data["exposures"]["dv_rating_beta"]["A"]
    webb = data["computers"]["webb_pct_software"]
    _, _, major = FROZEN.comp_maps(args.computerization)
    support = sorted(code for code in data["occupations"]
                     if np.isfinite(exposure.get(code, np.nan)) and np.isfinite(webb.get(code, np.nan)))
    young, older = FROZEN.panel_arrays(data["panel"], support, data["static_months"])
    weights = (young + older).sum(axis=1)
    observed = np.array([exposure[c] for c in support], float)
    observed_q = FROZEN.weighted_quintiles(observed, weights)
    fit, influence, _, labels = fit_group_model(data["panel"], support, data["static_months"],
                                                observed_q, webb)
    observed_beta = float(fit.beta[len(labels) - 2])
    groups = {}
    for index, code in enumerate(support):
        groups.setdefault(major.get(code, "missing"), []).append(index)
    rng = np.random.default_rng(PERMUTATION_SEED)
    rows, failures = [], []
    for draw in range(DRAWS):
        permuted = observed.copy()
        for indices in groups.values():
            permuted[indices] = rng.permutation(permuted[indices])
        try:
            q = FROZEN.weighted_quintiles(permuted, weights)
            fit_draw, _, _, labels_draw = fit_group_model(
                data["panel"], support, data["static_months"], q, webb
            )
            coefficient = float(fit_draw.beta[len(labels_draw) - 2])
            rows.append({"draw": draw + 1, "coefficient": coefficient, "converged": True})
        except Exception as error:  # failure stays visible rather than being silently replaced
            failures.append({"draw": draw + 1, "error": type(error).__name__, "message": str(error)})
    coefficients = np.array([row["coefficient"] for row in rows])
    result = {
        "analysis_status": LABEL, "interpretation": "assumption-dependent within-SOC2 permutation diagnostic",
        "seed": PERMUTATION_SEED, "requested_draws": DRAWS, "successful_draws": len(rows),
        "failed_draws": len(failures), "observed_coefficient": observed_beta,
        "permutation_mean": float(coefficients.mean()), "permutation_sd": float(coefficients.std(ddof=1)),
        "lower_tail_probability": float((1 + np.sum(coefficients <= observed_beta)) / (len(rows) + 1)),
        "two_sided_centered_probability": float((1 + np.sum(np.abs(coefficients - coefficients.mean()) >=
                                               abs(observed_beta - coefficients.mean()))) / (len(rows) + 1)),
        "exchangeability_not_established": True,
    }
    write_csv(args.output_dir / "WITHIN_SOC2_PERMUTATION_DRAWS.csv", rows)
    write_json(args.output_dir / "WITHIN_SOC2_PERMUTATION_FAILURES.json", failures)
    write_json(args.output_dir / "WITHIN_SOC2_PERMUTATION_SUMMARY.json", result)
    return result


def run(args: argparse.Namespace) -> dict:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = load_data(args)
    chars = characteristics_frame(args)
    outputs = {}
    if args.stage in ("core", "all"):
        outputs["placebo"] = run_placebos(args, data, chars)
        outputs["reference"] = run_reference_and_exclusions(args, data)
        outputs["family"] = run_family_models(args, data, chars)
        outputs["tails"] = run_tail_stability(args, data)
    if args.stage in ("permutation", "all"):
        outputs["permutation"] = run_permutations(args, data)
    receipt = {
        "record": "YAX referee revision core execution",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "protected_refs": {
            "v1.1-design-freeze": subprocess.check_output(
                ["git", "rev-parse", "v1.1-design-freeze^{}"], cwd=ROOT, text=True).strip(),
            "v1.1-confirmatory-results": subprocess.check_output(
                ["git", "rev-parse", "v1.1-confirmatory-results^{}"], cwd=ROOT, text=True).strip(),
        },
        "baseline_coefficient_reproduced": data["baseline_reproduced"],
        "stage": args.stage,
        "input_hashes": data["authenticated"]["hashes"],
        "output_hashes": {path.name: sha256(path) for path in args.output_dir.iterdir()
                          if path.is_file() and path.name != "EXECUTION_RECEIPT.json"},
        "sections": outputs,
    }
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({"status": "PASS_REFEREE_CORE", "stage": args.stage,
                      "baseline": data["baseline_reproduced"],
                      "files": len(receipt["output_hashes"])}, indent=2))
    return receipt


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--stage", choices=("core", "permutation", "all"), default="core")
    value.add_argument("--microdata", type=pathlib.Path, required=True)
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
