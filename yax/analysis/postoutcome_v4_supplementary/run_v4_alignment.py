#!/usr/bin/env python3
"""Execute only the predeclared YAX V4 estimand-alignment analyses.

POST-OUTCOME SUPPLEMENTARY ANALYSIS — NOT PART OF CONFIRMATORY YAX v1.1.

The immutable confirmatory estimator is imported and never modified. Outputs
are written only to the V4 supplementary namespace.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import pathlib
import sys
from datetime import datetime, timezone

import numpy as np


LABEL = "POST-OUTCOME SUPPLEMENTARY ANALYSIS — NOT PART OF CONFIRMATORY YAX v1.1"
DECLARATION_COMMIT = "b775621bb6aa8c459f1de54c981a861bf6979148"
ROOT = pathlib.Path(__file__).resolve().parents[3]
FROZEN_PATH = ROOT / "yax/analysis/run_frozen_v11.py"
SPEC = importlib.util.spec_from_file_location("yax_v4_frozen_reader", FROZEN_PATH)
FROZEN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = FROZEN
SPEC.loader.exec_module(FROZEN)

AI_MEASURES = (
    "aioe_admin_equal",
    "aioe_ability_direct",
    "aioe_oews2018_source_weighted",
    "dv_rating_alpha",
    "dv_rating_beta",
    "dv_rating_gamma",
)
EVENT_SEED = 20280831
COMMON_SUPPORT_SEED = 20270831


def generated_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def support_hash(codes: list[str]) -> str:
    canonical = "".join(f"{code}\n" for code in sorted(codes)).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: pathlib.Path, rows: list[dict], columns: list[str] | None = None) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    fields = columns or list(rows[0])
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def load_inputs(args: argparse.Namespace) -> dict:
    authenticated = FROZEN.validate_inputs(args)
    pre, frozen_occupations, pre_months = FROZEN.read_preperiod(args.preperiod_cells)
    panel, occupations, all_months, post_receipt = FROZEN.read_full_cells(
        args.microdata, args.bridge, pre, frozen_occupations, pre_months
    )
    exposures = FROZEN.exposure_maps(args.lookup, args.rule_b_values)
    computers, names, _ = FROZEN.comp_maps(args.computerization)
    return {
        "authenticated": authenticated,
        "panel": panel,
        "occupations": occupations,
        "all_months": all_months,
        "static_months": [month for month in all_months if month != FROZEN.TRANSITION],
        "pre_months": pre_months,
        "exposures": exposures,
        "computers": computers,
        "names": names,
        "post_receipt": post_receipt,
    }


def finite_support(base: list[str], exposure: dict, webb: dict) -> list[str]:
    return sorted(
        code for code in base
        if np.isfinite(exposure.get(code, np.nan)) and np.isfinite(webb.get(code, np.nan))
    )


def occupation_weights(panel, occupations: list[str], months: list[str]) -> np.ndarray:
    young, older = FROZEN.panel_arrays(panel, occupations, months)
    return (young + older).sum(axis=1)


def run_support_and_common(args: argparse.Namespace, data: dict) -> None:
    output = args.output_dir
    webb = data["computers"]["webb_pct_software"]
    base = sorted(data["occupations"])
    base_weights = occupation_weights(data["panel"], base, data["static_months"])
    base_total = float(base_weights.sum())
    supports = {
        measure: finite_support(base, data["exposures"][measure]["A"], webb)
        for measure in AI_MEASURES
    }
    hashes = {measure: support_hash(codes) for measure, codes in supports.items()}
    identical = len(set(hashes.values())) == 1
    audit_rows = []
    for measure in AI_MEASURES:
        codes = supports[measure]
        retained = float(occupation_weights(data["panel"], codes, data["static_months"]).sum())
        audit_rows.append({
            "analysis_status": LABEL,
            "measure": measure,
            "n_occupations": len(codes),
            "support_hash_sha256": hashes[measure],
            "employment_coverage": retained / base_total,
            "support_rule": "Rule A plus finite Webb",
            "identical_six_way_support": identical,
            "occupation_codes_json": json.dumps(codes, separators=(",", ":")),
        })
    write_csv(output / "TABLE5B_SUPPORT_AUDIT.csv", audit_rows)
    if identical:
        raise RuntimeError("unexpected identical Table 5B support; S2 was triggered by frozen unequal counts")

    common = sorted(set.intersection(*(set(codes) for codes in supports.values())))
    common_hash = support_hash(common)
    common_weights = occupation_weights(data["panel"], common, data["static_months"])
    common_coverage = float(common_weights.sum() / base_total)
    result_rows = []
    membership_rows = []
    for measure_index, measure in enumerate(AI_MEASURES):
        exposure = data["exposures"][measure]["A"]
        prepared = FROZEN.prepare_model(
            data["panel"], common, data["static_months"], exposure, webb, scale="q5_q1"
        )
        if prepared["occupations"] != common:
            raise RuntimeError(f"common support changed inside estimator for {measure}")
        fit, influence = FROZEN.fit_with_influence(
            prepared["young"], prepared["older"], prepared["regressors"]
        )
        target = prepared["target"]
        result, _, _ = FROZEN.bootstrap_summary(
            fit, influence, target, COMMON_SUPPORT_SEED + measure_index
        )
        values = np.array([exposure[code] for code in common], dtype=float)
        quintiles = FROZEN.weighted_quintiles(values, prepared["weights"])
        q5_codes = [code for code, quintile in zip(common, quintiles) if quintile == 5]
        result_rows.append({
            "analysis_status": LABEL,
            "measure": measure,
            "n_occupations": len(common),
            "support_hash_sha256": common_hash,
            "employment_coverage": common_coverage,
            "coefficient_log_points": result["coefficient"],
            "analytic_cluster_se": result["analytic_cluster_se"],
            "wild_score_ci_lower": result["ci_lower"],
            "wild_score_ci_upper": result["ci_upper"],
            "wild_score_p_value": result["bootstrap_p_value"],
            "wild_score_draws": result["bootstrap_draws"],
            "q5_occupation_count": len(q5_codes),
            "q5_membership_hash_sha256": support_hash(q5_codes),
        })
        for code, quintile in zip(common, quintiles):
            membership_rows.append({
                "analysis_status": LABEL,
                "measure": measure,
                "occupation_code": code,
                "occupation_name": data["names"].get(code, code),
                "quintile": int(quintile),
                "is_q5": bool(quintile == 5),
            })
    write_csv(output / "TABLE5B_COMMON_SUPPORT_RESULTS.csv", result_rows)
    write_csv(output / "TABLE5B_COMMON_SUPPORT_MEMBERSHIP.csv", membership_rows)
    write_json(output / "TABLE5B_SUPPORT_RECEIPT.json", {
        "analysis_status": LABEL,
        "analysis_ids": ["S1", "S2"],
        "generated_at_utc": generated_at(),
        "declaration_commit": DECLARATION_COMMIT,
        "native_support_identical": identical,
        "native_counts": {measure: len(codes) for measure, codes in supports.items()},
        "native_hashes": hashes,
        "common_support_n": len(common),
        "common_support_hash_sha256": common_hash,
        "common_support_employment_coverage": common_coverage,
        "all_six_common_result_signs_negative": all(row["coefficient_log_points"] < 0 for row in result_rows),
        "all_six_common_intervals_exclude_zero_negative": all(row["wild_score_ci_upper"] < 0 for row in result_rows),
        "quintile_weighting": "young-plus-older weighted stocks over 108 static estimation months; December 2022 excluded",
        "inputs": data["authenticated"]["hashes"],
        "output_hashes": {
            "audit": sha256(output / "TABLE5B_SUPPORT_AUDIT.csv"),
            "results": sha256(output / "TABLE5B_COMMON_SUPPORT_RESULTS.csv"),
            "membership": sha256(output / "TABLE5B_COMMON_SUPPORT_MEMBERSHIP.csv"),
        },
    })


def run_categorical_event(args: argparse.Namespace, data: dict) -> None:
    output = args.output_dir
    exposure = data["exposures"]["dv_rating_beta"]["A"]
    webb = data["computers"]["webb_pct_software"]
    support = finite_support(data["occupations"], exposure, webb)

    static_prepared = FROZEN.prepare_model(
        data["panel"], support, data["static_months"], exposure, webb, scale="q5_q1"
    )
    values = np.array([exposure[code] for code in support], dtype=float)
    quintiles = FROZEN.weighted_quintiles(values, static_prepared["weights"])

    young, older = FROZEN.panel_arrays(data["panel"], support, data["all_months"])
    event_weights = (young + older).sum(axis=1)
    webb_values = np.array([webb[code] for code in support], dtype=float)
    webb_mean, webb_sd = FROZEN.weighted_scale(webb_values, event_weights)
    webb_z = (webb_values - webb_mean) / webb_sd
    event_months = [month for month in data["all_months"] if month != FROZEN.EVENT_REFERENCE]
    columns = []
    labels = []
    q5_indices = []
    for month in event_months:
        indicator = np.array([value == month for value in data["all_months"]])
        for quintile in (2, 3, 4, 5):
            columns.append((((quintiles == quintile)[:, None]) & indicator[None, :]).reshape(-1).astype(float))
            labels.append(f"AI_Q{quintile}_x_{month}")
            if quintile == 5:
                q5_indices.append(len(columns) - 1)
    for month in event_months:
        indicator = np.array([value == month for value in data["all_months"]])
        columns.append((webb_z[:, None] * indicator[None, :]).reshape(-1))
        labels.append(f"Webb_z_x_{month}")

    regressors = np.column_stack(columns)
    fit, influence = FROZEN.fit_with_influence(young, older, regressors)
    rng = np.random.default_rng(EVENT_SEED)
    signs = rng.choice(
        np.array([-1.0, 1.0]), size=(FROZEN.BOOTSTRAP_DRAWS, len(support))
    )
    q5_shifts = signs @ influence[:, q5_indices]
    q5_beta = fit.beta[q5_indices]
    q5_se = fit.standard_error[q5_indices]
    rows = []
    for local_index, month in enumerate(event_months):
        se = float(q5_se[local_index])
        coefficient = float(q5_beta[local_index])
        critical = float(np.quantile(
            np.abs(q5_shifts[:, local_index] / se), 0.95, method="higher"
        ))
        rows.append({
            "analysis_status": LABEL,
            "event_month": month,
            "coefficient_q5_vs_q1": coefficient,
            "analytic_cluster_se": se,
            "pointwise_wild_score_ci_lower": coefficient - critical * se,
            "pointwise_wild_score_ci_upper": coefficient + critical * se,
            "simultaneous_pre_ci_lower": "",
            "simultaneous_pre_ci_upper": "",
            "reference_month": False,
            "transition_month": month == FROZEN.TRANSITION,
        })
    rows.append({
        "analysis_status": LABEL,
        "event_month": FROZEN.EVENT_REFERENCE,
        "coefficient_q5_vs_q1": 0.0,
        "analytic_cluster_se": 0.0,
        "pointwise_wild_score_ci_lower": 0.0,
        "pointwise_wild_score_ci_upper": 0.0,
        "simultaneous_pre_ci_lower": "",
        "simultaneous_pre_ci_upper": "",
        "reference_month": True,
        "transition_month": False,
    })

    pre_local = [index for index, month in enumerate(event_months) if month < FROZEN.TRANSITION]
    if len(pre_local) != 65:
        raise RuntimeError(f"expected 65 categorical Q5 pre coefficients, found {len(pre_local)}")
    observed_max_t = float(np.max(np.abs(q5_beta[pre_local] / q5_se[pre_local])))
    draw_max_t = np.max(
        np.abs(q5_shifts[:, pre_local] / q5_se[pre_local][None, :]), axis=1
    )
    simultaneous_critical = float(np.quantile(draw_max_t, 0.95, method="higher"))
    pvalue = float(
        (1 + np.sum(draw_max_t >= observed_max_t)) / (FROZEN.BOOTSTRAP_DRAWS + 1)
    )
    row_by_month = {row["event_month"]: row for row in rows}
    for local_index in pre_local:
        month = event_months[local_index]
        coefficient = float(q5_beta[local_index])
        se = float(q5_se[local_index])
        row_by_month[month]["simultaneous_pre_ci_lower"] = coefficient - simultaneous_critical * se
        row_by_month[month]["simultaneous_pre_ci_upper"] = coefficient + simultaneous_critical * se
    rows = sorted(rows, key=lambda row: row["event_month"])
    write_csv(output / "CATEGORICAL_Q5_Q1_EVENT_STUDY.csv", rows)

    post_indices = [index for index, month in enumerate(event_months) if month >= "2023-01"]
    pointwise_negative = sum(
        float(q5_beta[index]) < 0
        and row_by_month[event_months[index]]["pointwise_wild_score_ci_upper"] < 0
        for index in post_indices
    )
    pointwise_positive = sum(
        float(q5_beta[index]) > 0
        and row_by_month[event_months[index]]["pointwise_wild_score_ci_lower"] > 0
        for index in post_indices
    )
    simultaneous_excluding = sum(
        row_by_month[event_months[index]]["simultaneous_pre_ci_lower"] > 0
        or row_by_month[event_months[index]]["simultaneous_pre_ci_upper"] < 0
        for index in pre_local
    )
    write_json(output / "CATEGORICAL_Q5_Q1_EVENT_STUDY_RESULT.json", {
        "analysis_status": LABEL,
        "analysis_id": "S3",
        "generated_at_utc": generated_at(),
        "declaration_commit": DECLARATION_COMMIT,
        "specification": "Eloundou beta Rule A Q2-Q5-by-month interactions with Q1 omitted; Webb-z-by-month interactions; October 2022 reference",
        "occupations": len(support),
        "support_hash_sha256": support_hash(support),
        "q5_membership_hash_sha256": support_hash([
            code for code, quintile in zip(support, quintiles) if quintile == 5
        ]),
        "q5_occupation_count": int(np.sum(quintiles == 5)),
        "quintile_weighting": "exact primary static classification using young-plus-older stocks over 108 static estimation months; December 2022 excluded",
        "event_months_estimated": len(event_months),
        "reference_month": FROZEN.EVENT_REFERENCE,
        "transition_month": FROZEN.TRANSITION,
        "q2_q4_monthly_interactions_included": True,
        "webb_dynamic_treatment": "standardized Webb-by-young-by-month interaction for each non-reference month",
        "bootstrap_draws": FROZEN.BOOTSTRAP_DRAWS,
        "seed": EVENT_SEED,
        "pre_coefficients_tested": len(pre_local),
        "observed_max_abs_t": observed_max_t,
        "joint_pretrend_wild_score_p_value": pvalue,
        "simultaneous_95_critical": simultaneous_critical,
        "simultaneous_pre_intervals_excluding_zero": simultaneous_excluding,
        "post_months": len(post_indices),
        "post_pointwise_negative_intervals_excluding_zero": pointwise_negative,
        "post_pointwise_positive_intervals_excluding_zero": pointwise_positive,
        "inputs": data["authenticated"]["hashes"],
        "event_csv_sha256": sha256(output / "CATEGORICAL_Q5_Q1_EVENT_STUDY.csv"),
    })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("support_and_common", "categorical_event"))
    parser.add_argument("--microdata", required=True, type=pathlib.Path)
    parser.add_argument("--preperiod-cells", required=True, type=pathlib.Path)
    parser.add_argument("--lookup", type=pathlib.Path, default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    parser.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    parser.add_argument("--rule-b-values", type=pathlib.Path, default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    parser.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    parser.add_argument("--first-access-receipt", type=pathlib.Path, default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = load_inputs(args)
    if args.stage == "support_and_common":
        run_support_and_common(args, data)
    else:
        run_categorical_event(args, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
