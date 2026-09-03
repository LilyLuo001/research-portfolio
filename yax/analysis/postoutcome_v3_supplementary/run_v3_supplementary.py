#!/usr/bin/env python3
"""Run the predeclared YAX V3 referee-requested supplementary analyses.

POST-OUTCOME SUPPLEMENTARY ANALYSIS — NOT PART OF CONFIRMATORY YAX v1.1.

The immutable confirmatory code is imported, never modified. Each stage writes
only below yax/analysis/postoutcome_v3_supplementary/ (or the explicitly passed
output directory) and marks every machine-readable row as post-outcome
supplementary.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import importlib.util
import json
import math
import pathlib
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


LABEL = "POST-OUTCOME SUPPLEMENTARY ANALYSIS — NOT PART OF CONFIRMATORY YAX v1.1"
DECLARATION_COMMIT = "e863122f93a4a2007d85ed8c6a3cfc1abde27d00"
ROOT = pathlib.Path(__file__).resolve().parents[3]
FROZEN_PATH = ROOT / "yax/analysis/run_frozen_v11.py"
SPEC = importlib.util.spec_from_file_location("yax_v3_frozen_reader", FROZEN_PATH)
FROZEN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FROZEN
SPEC.loader.exec_module(FROZEN)


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def generated_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: pathlib.Path, rows: list[dict], columns: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def rank_correlation(left: np.ndarray, right: np.ndarray) -> float:
    left_rank = pd.Series(left).rank(method="average").to_numpy(float)
    right_rank = pd.Series(right).rank(method="average").to_numpy(float)
    if np.std(left_rank) <= 0 or np.std(right_rank) <= 0:
        return float("nan")
    return float(np.corrcoef(left_rank, right_rank)[0, 1])


def effective_support(shares: np.ndarray) -> float:
    return float(1.0 / np.square(shares).sum())


def information_contributions(
    young: np.ndarray,
    older: np.ndarray,
    regressors: np.ndarray,
    fitted_probability: np.ndarray,
    target: int,
) -> dict:
    """Decompose target conditional expected information by occupation.

    Reproduces the fitted-information fixed-effect absorption used by the
    confirmatory estimator and then partials the target absorbed slope column
    on all other absorbed slope columns. Returned contributions sum to the
    target Schur complement.
    """
    n_occ, n_month = young.shape
    total_full = (young + older).reshape(-1)
    occ_full = np.repeat(np.arange(n_occ), n_month)
    month_full = np.tile(np.arange(n_month), n_occ)
    keep = total_full > 0
    total = total_full[keep]
    occ = occ_full[keep]
    month = month_full[keep]
    x = regressors[keep]
    probability = fitted_probability[keep]
    weight = np.maximum(total * probability * (1.0 - probability), 1e-12)
    residualized = FROZEN.ENGINE._weighted_absorb(
        x, weight, occ, month, n_occ, n_month
    )
    information = residualized.T @ (weight[:, None] * residualized)
    bread = np.linalg.inv(information)
    nuisance = [index for index in range(x.shape[1]) if index != target]
    target_column = residualized[:, target]
    if nuisance:
        nuisance_matrix = residualized[:, nuisance]
        nuisance_information = nuisance_matrix.T @ (weight[:, None] * nuisance_matrix)
        projection_rhs = nuisance_matrix.T @ (weight * target_column)
        projection = np.linalg.solve(nuisance_information, projection_rhs)
        partial_target = target_column - nuisance_matrix @ projection
    else:
        partial_target = target_column
    cell_information = weight * np.square(partial_target)
    by_occupation = np.zeros(n_occ)
    np.add.at(by_occupation, occ, cell_information)
    total_information = float(cell_information.sum())
    schur_from_bread = float(1.0 / bread[target, target])
    relative_gap = abs(total_information - schur_from_bread) / max(abs(total_information), 1.0)
    if relative_gap > 1e-8:
        raise RuntimeError(
            f"headline information decomposition failed Schur check: {relative_gap}"
        )
    if not np.isfinite(total_information) or total_information <= 0:
        raise RuntimeError("non-positive target conditional information")
    shares = by_occupation / total_information
    return {
        "shares": shares,
        "occupation_information": by_occupation,
        "total_information": total_information,
        "schur_from_bread": schur_from_bread,
        "relative_schur_gap": relative_gap,
        "effective_support": effective_support(shares),
    }


def continuous_residual_support(
    panel: pd.DataFrame,
    occupations: list[str],
    pre_months: list[str],
    exposure: dict,
    computerization: dict,
) -> dict:
    young, older = FROZEN.panel_arrays(panel, occupations, pre_months)
    weights = (young + older).sum(axis=1)
    ai = np.array([exposure[code] for code in occupations], dtype=float)
    comp = np.array([computerization[code] for code in occupations], dtype=float)
    design = np.column_stack([np.ones(len(occupations)), comp])
    root_weight = np.sqrt(weights / weights.mean())
    coefficient, *_ = np.linalg.lstsq(
        design * root_weight[:, None], ai * root_weight, rcond=None
    )
    residual = ai - design @ coefficient
    contribution = weights * np.square(residual)
    shares = contribution / contribution.sum()
    return {
        "shares": shares,
        "residual": residual,
        "effective_support": effective_support(shares),
        "top_five_share": float(np.sort(shares)[-5:].sum()),
    }


def load_analysis_inputs(args: argparse.Namespace) -> dict:
    authenticated = FROZEN.validate_inputs(args)
    pre, frozen_occupations, pre_months = FROZEN.read_preperiod(args.preperiod_cells)
    panel, occupations, all_months, post_receipt = FROZEN.read_full_cells(
        args.microdata, args.bridge, pre, frozen_occupations, pre_months
    )
    exposures = FROZEN.exposure_maps(args.lookup, args.rule_b_values)
    computers, names, major_groups = FROZEN.comp_maps(args.computerization)
    return {
        "authenticated": authenticated,
        "pre": pre,
        "pre_months": pre_months,
        "panel": panel,
        "occupations": occupations,
        "all_months": all_months,
        "static_months": [month for month in all_months if month != FROZEN.TRANSITION],
        "exposures": exposures,
        "computers": computers,
        "names": names,
        "major_groups": major_groups,
        "post_receipt": post_receipt,
    }


def top_rows(occupations: list[str], names: dict, shares: np.ndarray, count: int = 5) -> list[dict]:
    order = np.argsort(shares)[::-1]
    return [
        {
            "occ_code": occupations[index],
            "occupation": names.get(occupations[index], occupations[index]),
            "share": float(shares[index]),
            "rank": rank,
        }
        for rank, index in enumerate(order[:count], 1)
    ]


def run_headline_support(args: argparse.Namespace, data: dict) -> None:
    output = args.output_dir
    frozen_results = json.loads(
        (ROOT / "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json").read_text(
            encoding="utf-8"
        )
    )
    test_b = json.loads(
        (ROOT / "yax/measurement/computerization_support_66m_receipt.json").read_text(
            encoding="utf-8"
        )
    )
    test_b_pairs = {
        (row["ai_measure"], row["computerization_measure"]): row
        for row in test_b["pairs"]
    }
    summary_rows = []
    occupation_rows = []
    bridge_rows = []
    for measure in ("dv_rating_beta", "dv_rating_alpha"):
        for rule in ("A", "B", "C"):
            for comp_measure in ("webb_pct_software", "onet_computers_importance"):
                key = f"{measure}__Rule{rule}__{comp_measure}__q5_q1"
                prepared = FROZEN.prepare_model(
                    data["panel"], data["occupations"], data["static_months"],
                    data["exposures"][measure][rule], data["computers"][comp_measure],
                    scale="q5_q1",
                )
                fit, _ = FROZEN.fit_with_influence(
                    prepared["young"], prepared["older"], prepared["regressors"]
                )
                target = prepared["target"]
                frozen_coefficient = frozen_results["headline"][key]["coefficients"][
                    "AI_Q5_x_post"
                ]["coefficient"]
                coefficient_gap = abs(float(fit.beta[target]) - float(frozen_coefficient))
                if coefficient_gap > 1e-10:
                    raise RuntimeError(f"{key} does not reproduce confirmatory coefficient")
                info = information_contributions(
                    prepared["young"], prepared["older"], prepared["regressors"],
                    fit.fitted_probability, target,
                )
                shares = info["shares"]
                top = top_rows(prepared["occupations"], data["names"], shares)
                top_five_share = float(sum(row["share"] for row in top))
                summary_rows.append({
                    "analysis_status": LABEL,
                    "specification": key,
                    "ai_measure": measure,
                    "coverage_rule": rule,
                    "computerization_measure": comp_measure,
                    "occupations": len(prepared["occupations"]),
                    "q5_coefficient_log_points": float(fit.beta[target]),
                    "headline_information_effective_occupations": info["effective_support"],
                    "headline_information_top_five_share": top_five_share,
                    "conditional_information": info["total_information"],
                    "schur_complement_check": info["schur_from_bread"],
                    "relative_schur_gap": info["relative_schur_gap"],
                    "top_five_occupations": "; ".join(row["occupation"] for row in top),
                })
                rank = np.empty(len(shares), dtype=int)
                rank[np.argsort(shares)[::-1]] = np.arange(1, len(shares) + 1)
                for index, code in enumerate(prepared["occupations"]):
                    occupation_rows.append({
                        "analysis_status": LABEL,
                        "specification": key,
                        "occ_code": code,
                        "occupation": data["names"].get(code, code),
                        "headline_information": float(info["occupation_information"][index]),
                        "headline_information_share": float(shares[index]),
                        "headline_information_rank": int(rank[index]),
                    })

                if rule == "A":
                    continuous = continuous_residual_support(
                        data["panel"], prepared["occupations"], data["pre_months"],
                        data["exposures"][measure][rule], data["computers"][comp_measure],
                    )
                    stored = test_b_pairs[(measure, comp_measure)]
                    effective_gap = abs(
                        continuous["effective_support"]
                        - float(stored["effective_number_identifying_ai"])
                    )
                    stored_top_five = sum(
                        float(row["residual_variance_share"])
                        for row in stored["named_divergence_occupations"][
                            "largest_residual_variance_contributors"
                        ][:5]
                    )
                    top_share_gap = abs(continuous["top_five_share"] - stored_top_five)
                    if effective_gap > 1e-6 or top_share_gap > 1e-8:
                        raise RuntimeError(
                            f"{key} continuous Test-B reproduction failed: "
                            f"effective gap={effective_gap}; top-five gap={top_share_gap}"
                        )
                    continuous_top = top_rows(
                        prepared["occupations"], data["names"], continuous["shares"]
                    )
                    continuous_set = {row["occ_code"] for row in continuous_top}
                    headline_set = {row["occ_code"] for row in top}
                    union = continuous_set | headline_set
                    bridge_rows.append({
                        "analysis_status": LABEL,
                        "specification": key,
                        "continuous_effective_occupations": continuous["effective_support"],
                        "headline_effective_occupations": info["effective_support"],
                        "continuous_top_five_share": continuous["top_five_share"],
                        "headline_top_five_share": top_five_share,
                        "occupation_share_spearman": rank_correlation(
                            continuous["shares"], shares
                        ),
                        "top_five_intersection": len(continuous_set & headline_set),
                        "top_five_jaccard": len(continuous_set & headline_set) / len(union),
                        "continuous_top_five": "; ".join(
                            row["occupation"] for row in continuous_top
                        ),
                        "headline_top_five": "; ".join(row["occupation"] for row in top),
                        "stored_test_b_effective_gap": effective_gap,
                        "stored_test_b_top_five_gap": top_share_gap,
                    })

    write_csv(output / "HEADLINE_INFORMATION_SUPPORT_SUMMARY.csv", summary_rows, list(summary_rows[0]))
    write_csv(output / "HEADLINE_INFORMATION_SUPPORT_BY_OCCUPATION.csv", occupation_rows, list(occupation_rows[0]))
    write_csv(output / "CONTINUOUS_VS_HEADLINE_SUPPORT.csv", bridge_rows, list(bridge_rows[0]))
    receipt = {
        "analysis_status": LABEL,
        "analysis_id": "S1",
        "generated_at_utc": generated_at(),
        "declaration_commit": DECLARATION_COMMIT,
        "formula": {
            "cell_weight": "N_i * p_hat_i * (1-p_hat_i)",
            "target_partialling": "absorbed Q5xPost residualized on all other absorbed slope columns under fitted information weights",
            "occupation_information": "sum_i_in_o W_i*z_i^2",
            "effective_support": "1/sum_o(h_o^2)",
        },
        "interpretation": "conditional expected-information support for Q5 relative to Q1; not leverage, influence, or coefficient decomposition",
        "models": len(summary_rows),
        "bridges": len(bridge_rows),
        "inputs": data["authenticated"]["hashes"],
        "outputs": {
            name: sha256(output / name)
            for name in (
                "HEADLINE_INFORMATION_SUPPORT_SUMMARY.csv",
                "HEADLINE_INFORMATION_SUPPORT_BY_OCCUPATION.csv",
                "CONTINUOUS_VS_HEADLINE_SUPPORT.csv",
            )
        },
    }
    write_json(output / "HEADLINE_INFORMATION_SUPPORT_RECEIPT.json", receipt)


def weighted_standardize(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    mean = float(np.average(values, weights=weights))
    sd = float(np.sqrt(np.average(np.square(values - mean), weights=weights)))
    if not np.isfinite(sd) or sd <= 0:
        raise RuntimeError("zero-variance validator")
    return (values - mean) / sd


def validator_projection(frame: pd.DataFrame, measure: str, validators: list[str]) -> dict:
    weights = frame["preperiod_employment_weight"].to_numpy(float)
    y = weighted_standardize(frame[measure].to_numpy(float), weights)
    x = np.column_stack([
        np.ones(len(frame)),
        *[weighted_standardize(frame[column].to_numpy(float), weights) for column in validators],
    ])
    root_weight = np.sqrt(weights / weights.mean())
    coefficient, *_ = np.linalg.lstsq(x * root_weight[:, None], y * root_weight, rcond=None)
    residual = y - x @ coefficient
    residual_variance = weights * np.square(residual)
    shares = residual_variance / residual_variance.sum()
    r_squared = 1.0 - float(np.average(np.square(residual), weights=weights))
    return {
        "r_squared": r_squared,
        "residual_sd": float(np.sqrt(np.average(np.square(residual), weights=weights))),
        "shares": shares,
        "effective_support": effective_support(shares),
    }


def run_validator_split(args: argparse.Namespace) -> None:
    output = args.output_dir
    source = ROOT / "yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv"
    frame = pd.read_csv(source, dtype={"census2018": str})
    measures = list(FROZEN.AI_MEASURES)
    linked = [
        "cognitive_ability_importance",
        "manual_physical_ability_importance",
        "required_education_category_index",
        "onet_computers_importance",
    ]
    external = [
        "rti_autor_dorn",
        "log_mean_annual_wage",
        "dingel_neiman_telework",
        "stem_major_group_share",
    ]
    complete = frame[["census2018", "occupation", "preperiod_employment_weight", *measures, *linked, *external]].dropna().copy()
    if len(complete) != 348:
        raise RuntimeError(f"Test-A common support changed: {len(complete)}")
    summary_rows = []
    occupation_rows = []
    for measure in measures:
        for group, variables in (("construction_linked_onet", linked), ("more_external", external)):
            result = validator_projection(complete, measure, variables)
            top = top_rows(
                complete["census2018"].tolist(),
                complete.set_index("census2018")["occupation"].to_dict(),
                result["shares"],
            )
            summary_rows.append({
                "analysis_status": LABEL,
                "ai_measure": measure,
                "validator_group": group,
                "validators": "; ".join(variables),
                "occupations": len(complete),
                "weighted_r_squared": result["r_squared"],
                "residual_sd": result["residual_sd"],
                "effective_residual_support": result["effective_support"],
                "top_five_residual_variance_share": float(sum(row["share"] for row in top)),
                "top_five_occupations": "; ".join(row["occupation"] for row in top),
            })
            ranks = np.empty(len(complete), dtype=int)
            ranks[np.argsort(result["shares"])[::-1]] = np.arange(1, len(complete) + 1)
            for index, row in complete.reset_index(drop=True).iterrows():
                occupation_rows.append({
                    "analysis_status": LABEL,
                    "ai_measure": measure,
                    "validator_group": group,
                    "census2018": row["census2018"],
                    "occupation": row["occupation"],
                    "residual_variance_share": float(result["shares"][index]),
                    "rank": int(ranks[index]),
                })
    write_csv(output / "TEST_A_VALIDATOR_SPLIT_SUMMARY.csv", summary_rows, list(summary_rows[0]))
    write_csv(output / "TEST_A_VALIDATOR_SPLIT_BY_OCCUPATION.csv", occupation_rows, list(occupation_rows[0]))
    write_json(output / "TEST_A_VALIDATOR_SPLIT_RECEIPT.json", {
        "analysis_status": LABEL,
        "analysis_id": "S2",
        "generated_at_utc": generated_at(),
        "declaration_commit": DECLARATION_COMMIT,
        "source": {"path": str(source.relative_to(ROOT)), "sha256": sha256(source)},
        "common_support_occupations": len(complete),
        "validator_taxonomy": {
            "construction_linked_onet": linked,
            "more_external": external,
            "classification_note": "Education and computer use are not AIOE inputs, but are conservatively grouped with same-source O*NET variables.",
        },
        "outputs": {
            name: sha256(output / name)
            for name in ("TEST_A_VALIDATOR_SPLIT_SUMMARY.csv", "TEST_A_VALIDATOR_SPLIT_BY_OCCUPATION.csv")
        },
    })


def read_gzip_header(path: pathlib.Path) -> list[str]:
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as handle:
        return next(csv.reader(handle))


def run_survey_feasibility(args: argparse.Namespace) -> None:
    output = args.output_dir
    columns = read_gzip_header(args.microdata)
    spec_path = ROOT / "dax/memo/power_calcs/ipums_ai_telework_extract_v1.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    variables = list(spec.get("variables", {}))
    categories = {
        "person_panel_identifiers": [name for name in ("CPSIDP",) if name in columns],
        "rotation_identifiers": [name for name in ("MISH",) if name in columns],
        "household_identifiers": [name for name in ("CPSID", "HRHHID", "HRHHID2", "SERIAL") if name in columns],
        "stratum_identifiers": [name for name in ("STRATA", "STRATUM") if name in columns],
        "psu_identifiers": [name for name in ("PSU", "CLUSTER") if name in columns],
        "replicate_weights": [name for name in columns if "REPW" in name.upper() or "REPLICATE" in name.upper()],
        "final_weight": [name for name in ("WTFINL",) if name in columns],
    }
    design_fields_available = bool(
        categories["stratum_identifiers"]
        and categories["psu_identifiers"]
        and categories["replicate_weights"]
    )
    conclusion = (
        "No design-consistent first-stage CPS survey resampling is implemented: "
        "the extract contains CPSID, SERIAL, CPSIDP, and MISH, but no public "
        "stratum/PSU variables or replicate weights. The available household, "
        "person-panel, and rotation identifiers can represent repeated-sample "
        "dependence, but cannot reconstruct the CPS multistage sample design or "
        "calibration-weight uncertainty."
        if not design_fields_available
        else "Required survey-design fields appear present; a separate method audit is required before resampling."
    )
    receipt = {
        "analysis_status": LABEL,
        "analysis_id": "S3",
        "generated_at_utc": generated_at(),
        "declaration_commit": DECLARATION_COMMIT,
        "microdata_header_sha256": hashlib.sha256(",".join(columns).encode()).hexdigest(),
        "extract_spec": {"path": str(spec_path.relative_to(ROOT)), "sha256": sha256(spec_path)},
        "microdata_columns": columns,
        "spec_variables": variables,
        "available_identifier_categories": categories,
        "design_consistent_resampling_feasible": design_fields_available,
        "resampling_executed": False,
        "conclusion": conclusion,
        "confirmatory_inference_scope": "Occupation-cluster intervals condition on realized CPS weighted employment-stock cells; they do not separately propagate first-stage survey sampling, household rotation dependence, or calibration-weight uncertainty.",
    }
    write_json(output / "CPS_SURVEY_UNCERTAINTY_FEASIBILITY.json", receipt)
    (output / "CPS_SURVEY_UNCERTAINTY_FEASIBILITY.md").write_text(
        "# CPS Survey-Uncertainty Feasibility\n\n"
        f"> **{LABEL}**\n\n"
        f"{conclusion}\n\n"
        "Accordingly, no ad hoc microdata bootstrap was run. Reported confirmatory confidence intervals remain conditional on the realized CPS weighted employment-stock estimates and do not separately propagate first-stage survey-sampling uncertainty.\n",
        encoding="utf-8",
    )


def run_remote_interaction(args: argparse.Namespace, data: dict) -> None:
    output = args.output_dir
    exposure = data["exposures"]["dv_rating_beta"]["A"]
    comp = data["computers"]["webb_pct_software"]
    remote = data["exposures"]["dingel_neiman_telework"]["A"]
    support = [
        code for code in data["occupations"]
        if np.isfinite(exposure.get(code, np.nan))
        and np.isfinite(comp.get(code, np.nan))
        and np.isfinite(remote.get(code, np.nan))
    ]
    young, older = FROZEN.panel_arrays(data["panel"], support, data["static_months"])
    weights = (young + older).sum(axis=1)
    ai = np.array([exposure[code] for code in support], float)
    cv = np.array([comp[code] for code in support], float)
    rv = np.array([remote[code] for code in support], float)
    ai = (ai - FROZEN.weighted_scale(ai, weights)[0]) / FROZEN.weighted_scale(ai, weights)[1]
    cv = (cv - FROZEN.weighted_scale(cv, weights)[0]) / FROZEN.weighted_scale(cv, weights)[1]
    rv = (rv - FROZEN.weighted_scale(rv, weights)[0]) / FROZEN.weighted_scale(rv, weights)[1]
    post = np.array([month >= "2023-01" for month in data["static_months"]])
    regressors = np.column_stack([
        (ai[:, None] * post).reshape(-1),
        (cv[:, None] * post).reshape(-1),
        (rv[:, None] * post).reshape(-1),
        ((ai * rv)[:, None] * post).reshape(-1),
    ])
    fit, influence = FROZEN.fit_with_influence(young, older, regressors)
    seed = 20260830 + 11000
    labels = ["AI_z_x_post", "Webb_z_x_post", "Remote_z_x_post", "AI_z_x_Remote_z_x_post"]
    coefficients = {}
    for index, label in enumerate(labels):
        summary, _, _ = FROZEN.bootstrap_summary(fit, influence, index, seed + index)
        coefficients[label] = summary
    write_json(output / "REMOTE_INTERACTION_RESULT.json", {
        "analysis_status": LABEL,
        "analysis_id": "S4",
        "generated_at_utc": generated_at(),
        "declaration_commit": DECLARATION_COMMIT,
        "specification": "Rule-A beta + Webb + Dingel-Neiman, all continuous standardized, plus beta-by-remotability interaction, static saturated model",
        "occupations": len(support),
        "months": len(data["static_months"]),
        "seed_base": seed,
        "bootstrap_algorithm": "confirmatory one-step occupation-cluster Rademacher wild-score/influence procedure",
        "coefficients": coefficients,
        "interpretation_limit": "Occupational remotability heterogeneity; not realized individual telework or causal mechanism proof.",
        "inputs": data["authenticated"]["hashes"],
    })


def run_joint_pretrend(args: argparse.Namespace, data: dict) -> None:
    output = args.output_dir
    exposure = data["exposures"]["dv_rating_beta"]["A"]
    comp = data["computers"]["webb_pct_software"]
    support = [
        code for code in data["occupations"]
        if np.isfinite(exposure.get(code, np.nan)) and np.isfinite(comp.get(code, np.nan))
    ]
    young, older = FROZEN.panel_arrays(data["panel"], support, data["all_months"])
    weights = (young + older).sum(axis=1)
    ai = np.array([exposure[code] for code in support], float)
    cv = np.array([comp[code] for code in support], float)
    ai = (ai - FROZEN.weighted_scale(ai, weights)[0]) / FROZEN.weighted_scale(ai, weights)[1]
    cv = (cv - FROZEN.weighted_scale(cv, weights)[0]) / FROZEN.weighted_scale(cv, weights)[1]
    event_months = [month for month in data["all_months"] if month != FROZEN.EVENT_REFERENCE]
    columns = []
    for month in event_months:
        indicator = np.array([value == month for value in data["all_months"]])
        columns.append((ai[:, None] * indicator[None, :]).reshape(-1))
    for month in event_months:
        indicator = np.array([value == month for value in data["all_months"]])
        columns.append((cv[:, None] * indicator[None, :]).reshape(-1))
    fit, influence = FROZEN.fit_with_influence(young, older, np.column_stack(columns))
    frozen_rows = {
        row["event_month"]: row
        for row in json.loads(
            (ROOT / "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json").read_text(encoding="utf-8")
        )["event_study"]["rows"]
    }
    maximum_coefficient_gap = max(
        abs(float(fit.beta[index]) - float(frozen_rows[month]["coefficient"]))
        for index, month in enumerate(event_months)
    )
    if maximum_coefficient_gap > 1e-10:
        raise RuntimeError("supplementary joint test does not reproduce confirmatory event coefficients")
    pre_indices = [index for index, month in enumerate(event_months) if month < "2022-12"]
    if len(pre_indices) != 65:
        raise RuntimeError(f"expected 65 pretrend coefficients, found {len(pre_indices)}")
    beta = fit.beta[pre_indices]
    analytic_se = fit.standard_error[pre_indices]
    observed_t = np.abs(beta / analytic_se)
    observed_max_t = float(observed_t.max())
    seed = 20260830 + 12000
    rng = np.random.default_rng(seed)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(FROZEN.BOOTSTRAP_DRAWS, len(support)))
    shifts = signs @ influence[:, pre_indices]
    draw_max_t = np.max(np.abs(shifts / analytic_se[None, :]), axis=1)
    critical = float(np.quantile(draw_max_t, 0.95, method="higher"))
    pvalue = float((1 + np.sum(draw_max_t >= observed_max_t)) / (FROZEN.BOOTSTRAP_DRAWS + 1))
    rows = []
    for local_index, event_index in enumerate(pre_indices):
        month = event_months[event_index]
        coefficient = float(beta[local_index])
        se = float(analytic_se[local_index])
        rows.append({
            "analysis_status": LABEL,
            "event_month": month,
            "coefficient": coefficient,
            "analytic_cluster_se": se,
            "simultaneous_ci_lower": coefficient - critical * se,
            "simultaneous_ci_upper": coefficient + critical * se,
        })
    write_csv(output / "JOINT_PRETREND_SIMULTANEOUS_BANDS.csv", rows, list(rows[0]))
    write_json(output / "JOINT_PRETREND_RESULT.json", {
        "analysis_status": LABEL,
        "analysis_id": "S5",
        "generated_at_utc": generated_at(),
        "declaration_commit": DECLARATION_COMMIT,
        "specification": "Primary Rule-A beta-by-Webb continuous event study; all 65 non-reference pre-December-2022 AI event coefficients",
        "reference_month": FROZEN.EVENT_REFERENCE,
        "occupations": len(support),
        "tested_coefficients": len(pre_indices),
        "test": "max absolute analytic-studentized coefficient with occupation-cluster wild-score reference distribution",
        "observed_max_abs_t": observed_max_t,
        "bootstrap_p_value": pvalue,
        "simultaneous_95_critical": critical,
        "simultaneous_intervals_excluding_zero": sum(
            row["simultaneous_ci_lower"] > 0 or row["simultaneous_ci_upper"] < 0
            for row in rows
        ),
        "bootstrap_draws": FROZEN.BOOTSTRAP_DRAWS,
        "seed": seed,
        "maximum_confirmatory_coefficient_reproduction_gap": maximum_coefficient_gap,
        "bands_output_sha256": sha256(output / "JOINT_PRETREND_SIMULTANEOUS_BANDS.csv"),
        "inputs": data["authenticated"]["hashes"],
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage",
        choices=("headline_support", "validator_split", "survey_feasibility", "remote_interaction", "joint_pretrend"),
    )
    parser.add_argument("--microdata", type=pathlib.Path)
    parser.add_argument("--preperiod-cells", type=pathlib.Path)
    parser.add_argument("--lookup", type=pathlib.Path, default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    parser.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    parser.add_argument("--rule-b-values", type=pathlib.Path, default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    parser.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    parser.add_argument("--first-access-receipt", type=pathlib.Path, default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.stage == "validator_split":
        run_validator_split(args)
        return 0
    required = ("microdata", "preperiod_cells")
    missing = [name for name in required if getattr(args, name) is None]
    if missing:
        parser.error(f"stage {args.stage} requires: {', '.join(missing)}")
    if args.stage == "survey_feasibility":
        run_survey_feasibility(args)
        return 0
    data = load_analysis_inputs(args)
    if args.stage == "headline_support":
        run_headline_support(args, data)
    elif args.stage == "remote_interaction":
        run_remote_interaction(args, data)
    elif args.stage == "joint_pretrend":
        run_joint_pretrend(args, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
