#!/usr/bin/env python3
"""Run only the declared YAX V4.1 quintile-weight sensitivity.

POST-OUTCOME SUPPLEMENTARY QUINTILE-WEIGHT SENSITIVITY — NOT PART OF
CONFIRMATORY YAX v1.1.

The historical confirmatory estimator is imported but never modified.  The
primary stage changes only the employment window used to form AI-exposure
quintiles.  The optional common-support stage applies the same single change to
the already-fixed V4 six-way intersection.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import inspect
import json
import math
import pathlib
import subprocess
import sys
from datetime import datetime, timezone

import numpy as np


LABEL = (
    "POST-OUTCOME SUPPLEMENTARY QUINTILE-WEIGHT SENSITIVITY — "
    "NOT PART OF CONFIRMATORY YAX v1.1"
)
DECLARATION_COMMIT = "caf2b41"
PRIMARY_SUPPORT_HASH = "11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b"
COMMON_SUPPORT_HASH = "1e184b27678b7978d4b15e618db5b44f44b5e9ec1b50b69b53093ec62e0ce462"
ROOT = pathlib.Path(__file__).resolve().parents[3]
FROZEN_PATH = ROOT / "yax" / "analysis" / "run_frozen_v11.py"
SPEC = importlib.util.spec_from_file_location("yax_v41_frozen_reader", FROZEN_PATH)
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


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def support_hash(codes: list[str]) -> str:
    return text_hash("".join(f"{code}\n" for code in sorted(codes)))


def git_head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def write_json(path: pathlib.Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: pathlib.Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"refusing to write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def weighted_cuts(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """Return the four cut values under the immutable weighted-quintile rule."""
    order = np.argsort(values, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    return np.array([
        values[order[min(np.searchsorted(cumulative, share * cumulative[-1], side="left"),
                         len(values) - 1)]]
        for share in (0.2, 0.4, 0.6, 0.8)
    ])


def jaccard(left: set[str], right: set[str]) -> float:
    return len(left & right) / len(left | right)


def weighted_correlation(left: np.ndarray, right: np.ndarray, weights: np.ndarray) -> float:
    left_mean = float(np.average(left, weights=weights))
    right_mean = float(np.average(right, weights=weights))
    left_centered = left - left_mean
    right_centered = right - right_mean
    covariance = float(np.average(left_centered * right_centered, weights=weights))
    denominator = math.sqrt(
        float(np.average(left_centered ** 2, weights=weights))
        * float(np.average(right_centered ** 2, weights=weights))
    )
    return covariance / denominator


def load_inputs(args: argparse.Namespace) -> dict:
    authenticated = FROZEN.validate_inputs(args)
    pre, frozen_occupations, pre_months = FROZEN.read_preperiod(args.preperiod_cells)
    panel, occupations, all_months, post_receipt = FROZEN.read_full_cells(
        args.microdata, args.bridge, pre, frozen_occupations, pre_months
    )
    exposures = FROZEN.exposure_maps(args.lookup, args.rule_b_values)
    computers, _, _ = FROZEN.comp_maps(args.computerization)
    static_months = [month for month in all_months if month != FROZEN.TRANSITION]
    if "2025-10" in static_months:
        raise RuntimeError("documented October 2025 gap unexpectedly present")
    return {
        "authenticated": authenticated,
        "panel": panel,
        "occupations": sorted(occupations),
        "pre_months": sorted(pre_months),
        "static_months": static_months,
        "all_months": all_months,
        "exposures": exposures,
        "computers": computers,
        "post_receipt": post_receipt,
    }


def finite_support(base: list[str], exposure: dict, control: dict) -> list[str]:
    return [
        code for code in base
        if np.isfinite(exposure.get(code, np.nan))
        and np.isfinite(control.get(code, np.nan))
    ]


def occupation_weights(panel: dict, occupations: list[str], months: list[str]) -> np.ndarray:
    young, older = FROZEN.panel_arrays(panel, occupations, months)
    return (young + older).sum(axis=1)


def classifications(data: dict, support: list[str], exposure: dict) -> dict:
    values = np.array([exposure[code] for code in support], dtype=float)
    full_weights = occupation_weights(data["panel"], support, data["static_months"])
    pre_weights = occupation_weights(data["panel"], support, data["pre_months"])
    full_q = FROZEN.weighted_quintiles(values, full_weights)
    pre_q = FROZEN.weighted_quintiles(values, pre_weights)
    return {
        "values": values,
        "full_weights": full_weights,
        "pre_weights": pre_weights,
        "full_cuts": weighted_cuts(values, full_weights),
        "pre_cuts": weighted_cuts(values, pre_weights),
        "full_q": full_q,
        "pre_q": pre_q,
    }


def classification_outputs(output: pathlib.Path, support: list[str], classified: dict) -> dict:
    full_q = classified["full_q"]
    pre_q = classified["pre_q"]
    full_weights = classified["full_weights"]
    pre_weights = classified["pre_weights"]
    full_q1 = {code for code, q in zip(support, full_q) if q == 1}
    pre_q1 = {code for code, q in zip(support, pre_q) if q == 1}
    full_q5 = {code for code, q in zip(support, full_q) if q == 5}
    pre_q5 = {code for code, q in zip(support, pre_q) if q == 5}
    metrics = {
        "q1_jaccard": jaccard(full_q1, pre_q1),
        "q5_jaccard": jaccard(full_q5, pre_q5),
        "occupations_changing_quintile": int(np.sum(full_q != pre_q)),
        "moving_into_q1": len(pre_q1 - full_q1),
        "moving_out_of_q1": len(full_q1 - pre_q1),
        "moving_into_q5": len(pre_q5 - full_q5),
        "moving_out_of_q5": len(full_q5 - pre_q5),
        "weighted_quintile_code_correlation_preweights": weighted_correlation(
            full_q.astype(float), pre_q.astype(float), pre_weights
        ),
        "exposure_rank_correlation": 1.0,
    }
    rows = []
    for scheme, q_values, weights, cuts in (
        ("full_static_108_month", full_q, full_weights, classified["full_cuts"]),
        ("preperiod_only", pre_q, pre_weights, classified["pre_cuts"]),
    ):
        for quintile in range(1, 6):
            rows.append({
                "analysis_status": LABEL,
                "scheme": scheme,
                "quintile": quintile,
                "lower_bound_exclusive": "-inf" if quintile == 1 else float(cuts[quintile - 2]),
                "upper_cut_inclusive": "inf" if quintile == 5 else float(cuts[quintile - 1]),
                "occupation_count": int(np.sum(q_values == quintile)),
                "within_window_employment_share": float(weights[q_values == quintile].sum() / weights.sum()),
                **metrics,
            })
    write_csv(output / "YAX_V41_QUINTILE_CLASSIFICATION_COMPARISON.csv", rows)
    membership = []
    for index, code in enumerate(support):
        membership.append({
            "analysis_status": LABEL,
            "occ_code": code,
            "exposure_value": classified["values"][index],
            "full_static_weight": full_weights[index],
            "preperiod_weight": pre_weights[index],
            "full_static_quintile": int(full_q[index]),
            "preperiod_quintile": int(pre_q[index]),
            "changed_quintile": bool(full_q[index] != pre_q[index]),
        })
    write_csv(output / "YAX_V41_QUINTILE_MEMBERSHIP.csv", membership)
    return metrics


def estimate_with_classification(
    data: dict,
    support: list[str],
    exposure: dict,
    control: dict,
    quintiles: np.ndarray,
    seed: int,
) -> tuple[dict, dict]:
    prepared = FROZEN.prepare_model(
        data["panel"], support, data["static_months"], exposure, control, scale="q5_q1"
    )
    if prepared["occupations"] != support:
        raise RuntimeError("support changed inside the frozen model preparer")
    post = np.array([month >= "2023-01" for month in data["static_months"]])
    regressors = prepared["regressors"].copy()
    for column, quintile in enumerate((2, 3, 4, 5)):
        regressors[:, column] = (
            (quintiles[:, None] == quintile) & post[None, :]
        ).reshape(-1).astype(float)
    fit, influence = FROZEN.fit_with_influence(
        prepared["young"], prepared["older"], regressors
    )
    target = 3
    result, _, _ = FROZEN.bootstrap_summary(fit, influence, target, seed)
    result["target_label"] = "AI_Q5_x_post"
    result["occupations"] = len(support)
    result["months"] = len(data["static_months"])
    return result, prepared


def run_primary(args: argparse.Namespace, data: dict) -> None:
    output = args.output_dir
    exposure = data["exposures"]["dv_rating_beta"]["A"]
    webb = data["computers"]["webb_pct_software"]
    support = finite_support(data["occupations"], exposure, webb)
    if len(support) != 468 or support_hash(support) != PRIMARY_SUPPORT_HASH:
        raise RuntimeError("primary support does not match the V4 headline support")
    classified = classifications(data, support, exposure)
    metrics = classification_outputs(output, support, classified)

    pre_result, prepared = estimate_with_classification(
        data, support, exposure, webb, classified["pre_q"], FROZEN.BOOTSTRAP_SEED + 3
    )
    frozen = json.loads((ROOT / "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json").read_text())
    key = "dv_rating_beta__RuleA__webb_pct_software__q5_q1"
    confirmatory = frozen["headline"][key]["coefficients"]["AI_Q5_x_post"]
    delta = pre_result["coefficient"] - confirmatory["coefficient"]
    row = {
        "analysis_status": LABEL,
        "specification": "dv_rating_beta__RuleA__webb_pct_software__q5_q1",
        "support_occupations": len(support),
        "support_hash_sha256": support_hash(support),
        "confirmatory_full_weight_coefficient": confirmatory["coefficient"],
        "preperiod_weight_coefficient": pre_result["coefficient"],
        "delta_preweight_minus_fullweight": delta,
        "preperiod_weight_analytic_cluster_se": pre_result["analytic_cluster_se"],
        "preperiod_weight_wild_score_ci_lower": pre_result["ci_lower"],
        "preperiod_weight_wild_score_ci_upper": pre_result["ci_upper"],
        "preperiod_weight_wild_score_p_value": pre_result["bootstrap_p_value"],
        "preperiod_weight_exponential_percent": 100 * (math.exp(pre_result["coefficient"]) - 1),
        **metrics,
    }
    write_csv(output / "YAX_V41_PRIMARY_PREPERIOD_WEIGHT_SENSITIVITY.csv", [row])

    receipt = {
        "record": "YAX V4.1 primary quintile-weight implementation receipt",
        "analysis_status": LABEL,
        "design_verdict": "Verdict 3 — Freeze ambiguity",
        "declaration_commit": DECLARATION_COMMIT,
        "implementation_commit": args.implementation_commit,
        "execution_head": git_head(),
        "historical_production_function": "yax.analysis.run_frozen_v11.prepare_model",
        "historical_quintile_function": "yax.analysis.run_frozen_v11.weighted_quintiles",
        "historical_quintile_function_sha256": text_hash(inspect.getsource(FROZEN.weighted_quintiles)),
        "historical_prepare_model_function_sha256": text_hash(inspect.getsource(FROZEN.prepare_model)),
        "sensitivity_script_sha256": sha256(pathlib.Path(__file__)),
        "input_hashes": data["authenticated"]["hashes"],
        "input_employment_stock_file": str(args.microdata),
        "support_rule": "Eloundou beta Rule A strict intersect Webb finite support",
        "support_occupations": len(support),
        "support_hash_sha256": support_hash(support),
        "weight_construction_order": "finite support first; then sum young-plus-older stocks within the selected month window",
        "full_static_weight_window": {
            "first_month": data["static_months"][0],
            "last_month": data["static_months"][-1],
            "included_months": len(data["static_months"]),
            "december_2022_excluded": FROZEN.TRANSITION not in data["static_months"],
            "october_2025_absent": "2025-10" not in data["static_months"],
            "young_and_older_summed": True,
            "total_weight": float(classified["full_weights"].sum()),
        },
        "preperiod_weight_window": {
            "first_month": data["pre_months"][0],
            "last_month": data["pre_months"][-1],
            "included_months": len(data["pre_months"]),
            "postperiod_months_included": 0,
            "young_and_older_summed": True,
            "total_weight": float(classified["pre_weights"].sum()),
        },
        "weighted_quintile_algorithm": (
            "stable mergesort; cumulative employment cuts at 0.2/0.4/0.6/0.8 "
            "with left search; equal scores assigned together by left search"
        ),
        "full_static_cut_values": classified["full_cuts"].tolist(),
        "preperiod_cut_values": classified["pre_cuts"].tolist(),
        "classification_metrics": metrics,
        "confirmatory_coefficient": confirmatory["coefficient"],
        "preperiod_weight_result": pre_result,
        "delta_preweight_minus_fullweight": delta,
        "same_weighting_code_table5a": True,
        "same_weighting_code_native_table5b": True,
        "same_weighting_code_paired_test_c": True,
        "v4_categorical_event_uses_same_static_primary_classification": True,
        "v4_literal_common_support_uses_same_weighting_helper_but_measure_specific_support_input": True,
        "classification_comparison_sha256": sha256(output / "YAX_V41_QUINTILE_CLASSIFICATION_COMPARISON.csv"),
        "membership_sha256": sha256(output / "YAX_V41_QUINTILE_MEMBERSHIP.csv"),
        "primary_result_sha256": sha256(output / "YAX_V41_PRIMARY_PREPERIOD_WEIGHT_SENSITIVITY.csv"),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "protected_confirmatory_artifacts_modified": False,
    }
    write_json(output / "YAX_V41_QUINTILE_WEIGHT_IMPLEMENTATION_RECEIPT.json", receipt)


def run_common(args: argparse.Namespace, data: dict) -> None:
    output = args.output_dir
    webb = data["computers"]["webb_pct_software"]
    supports = {
        measure: set(finite_support(data["occupations"], data["exposures"][measure]["A"], webb))
        for measure in AI_MEASURES
    }
    common = sorted(set.intersection(*supports.values()))
    if len(common) != 444 or support_hash(common) != COMMON_SUPPORT_HASH:
        raise RuntimeError("common support does not match the immutable V4 intersection")
    v4 = {
        row["measure"]: row
        for row in csv.DictReader((
            ROOT / "yax/analysis/postoutcome_v4_supplementary/TABLE5B_COMMON_SUPPORT_RESULTS.csv"
        ).open(encoding="utf-8"))
    }
    rows = []
    for index, measure in enumerate(AI_MEASURES):
        exposure = data["exposures"][measure]["A"]
        classified = classifications(data, common, exposure)
        result, _ = estimate_with_classification(
            data, common, exposure, webb, classified["pre_q"], 20270831 + index
        )
        full_q5 = {code for code, q in zip(common, classified["full_q"]) if q == 5}
        pre_q5 = {code for code, q in zip(common, classified["pre_q"]) if q == 5}
        full_q1 = {code for code, q in zip(common, classified["full_q"]) if q == 1}
        pre_q1 = {code for code, q in zip(common, classified["pre_q"]) if q == 1}
        old = v4[measure]
        rows.append({
            "analysis_status": LABEL,
            "measure": measure,
            "support_occupations": len(common),
            "support_hash_sha256": support_hash(common),
            "full_weight_coefficient": float(old["coefficient_log_points"]),
            "full_weight_ci_lower": float(old["wild_score_ci_lower"]),
            "full_weight_ci_upper": float(old["wild_score_ci_upper"]),
            "preperiod_weight_coefficient": result["coefficient"],
            "preperiod_weight_analytic_cluster_se": result["analytic_cluster_se"],
            "preperiod_weight_ci_lower": result["ci_lower"],
            "preperiod_weight_ci_upper": result["ci_upper"],
            "preperiod_weight_p_value": result["bootstrap_p_value"],
            "delta_preweight_minus_fullweight": result["coefficient"] - float(old["coefficient_log_points"]),
            "q5_jaccard": jaccard(full_q5, pre_q5),
            "q1_jaccard": jaccard(full_q1, pre_q1),
            "occupations_changing_quintile": int(np.sum(classified["full_q"] != classified["pre_q"])),
            "full_sign_negative": float(old["coefficient_log_points"]) < 0,
            "preperiod_sign_negative": result["coefficient"] < 0,
        })
    write_csv(output / "YAX_V41_SIX_MEASURE_COMMON_SUPPORT_WEIGHTING_COMPARISON.csv", rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("primary", "common_support"))
    parser.add_argument("--microdata", required=True, type=pathlib.Path)
    parser.add_argument("--preperiod-cells", required=True, type=pathlib.Path)
    parser.add_argument("--implementation-commit", required=True)
    parser.add_argument("--lookup", type=pathlib.Path, default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    parser.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    parser.add_argument("--rule-b-values", type=pathlib.Path, default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    parser.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    parser.add_argument("--first-access-receipt", type=pathlib.Path, default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    parser.add_argument("--output-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    data = load_inputs(args)
    if args.stage == "primary":
        run_primary(args, data)
    else:
        run_common(args, data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
