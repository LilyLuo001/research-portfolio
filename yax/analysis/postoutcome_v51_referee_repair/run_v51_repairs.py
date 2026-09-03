#!/usr/bin/env python3
"""Execute the closed YAX V5.1 diagnostics and single joint F+G model."""
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
sys.path.insert(0, str(HERE))
import v51_core as CORE  # noqa: E402


LABEL = "POST-OUTCOME EXPLORATORY — V5.1 CLOSED REFEREE REPAIR"
PARENT = "ed4055eab8d303c2ff48e18562a99dd43b3c7874"
COMMON_SUPPORT_HASH = "1e184b27678b7978d4b15e618db5b44f44b5e9ec1b50b69b53093ec62e0ce462"
FG_SEED = 2026090501
DRAWS = 999


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P3 = import_path("yax_v51_phase3", ROOT / "yax/analysis/postoutcome_phase3_final/run_phase3.py")
FROZEN = P3.FROZEN
V4 = P3.V4
MEASURES = P3.MEASURES


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
        raise RuntimeError(f"refusing to write empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def authenticate(args: argparse.Namespace) -> dict:
    head = git("rev-parse", "HEAD")
    if head != args.pre_result_commit:
        raise RuntimeError(f"V5.1 execution must run at exact pre-result commit {args.pre_result_commit}; got {head}")
    if subprocess.run(["git", "merge-base", "--is-ancestor", PARENT, head], cwd=ROOT).returncode:
        raise RuntimeError("sealed Phase 3/V5 parent is not an ancestor")
    protected = {
        "v1.1-design-freeze": git("rev-parse", "v1.1-design-freeze^{}"),
        "v1.1-confirmatory-results": git("rev-parse", "v1.1-confirmatory-results^{}"),
    }
    expected_protected = {
        "v1.1-design-freeze": "22fbf7924809b7a535e31ae0ab68f5b113ce8078",
        "v1.1-confirmatory-results": "b16109482c3bf5ca176f6f08976e120b04769945",
    }
    if protected != expected_protected:
        raise RuntimeError(f"protected refs moved: {protected}")
    paths = {
        "microdata": args.microdata,
        "weight_patch": args.weight_patch,
        "preperiod_cells": args.preperiod_cells,
        "lookup": args.lookup,
        "computerization": args.computerization,
        "bridge": args.bridge,
        "rule_b": args.rule_b_values,
        "first_access_receipt": args.first_access_receipt,
        "characteristics": args.characteristics,
        "sealed_common_support": args.table5b_results,
        "sealed_confirmatory_results": args.frozen_results,
    }
    actual = {name: sha256(path) for name, path in paths.items()}
    expected = {
        "microdata": FROZEN.MICRODATA_SHA256,
        "weight_patch": "841e13798c34f74a8cd8e0ac1d913742aad5f24fce2c6876793ecf1dd8bd55a8",
        "preperiod_cells": FROZEN.PRE_CELLS_SHA256,
        "lookup": FROZEN.LOOKUP_SHA256,
        "computerization": FROZEN.COMP_SHA256,
        "bridge": FROZEN.BRIDGE_SHA256,
        "rule_b": "8092f0eef57aaf4271a7dc563a4820e2f9a6d13519bcac9372837bc7a2c991e6",
        "characteristics": "88311c3bc26f00fde4aa792888491ae4a1e340c601d1c62147d52727afbf207c",
        "sealed_common_support": "6b51a2a5c0a5f30ea73b1889828b89df460ffc740d069a567c129f6d135e9ca1",
        "first_access_receipt": "d13b1e1635433e8ef8f90c35667dedb24f503f9029d694557351e77b6904d9b3",
        "sealed_confirmatory_results": "4f7df33a530e499c5562dead9464b2a19b87a3e3c6454d52944bc5e00879a831",
    }
    bad = {key: (actual[key], value) for key, value in expected.items() if actual[key] != value}
    if bad:
        raise RuntimeError(f"V5.1 input hash mismatch: {bad}")
    return {"head": head, "protected": protected, "input_hashes": actual}


def correlation_rows(reference: pd.DataFrame) -> list[dict]:
    weights = reference.preperiod_employment_weight.to_numpy(float)
    rows = []
    for metric in ("weighted_pearson", "weighted_average_rank_spearman"):
        values = {
            measure: (
                reference[measure].to_numpy(float)
                if metric == "weighted_pearson"
                else CORE.average_rank(reference[measure].to_numpy(float))
            )
            for measure in MEASURES
        }
        for left in MEASURES:
            for right in MEASURES:
                rows.append({
                    "analysis_status": LABEL,
                    "metric": metric,
                    "measure_1": left,
                    "measure_2": right,
                    "correlation": CORE.weighted_corr(values[left], values[right], weights),
                    "occupations": len(reference),
                    "weighting": "frozen preperiod_employment_weight",
                })
    return rows


def kappa_rows(switches: pd.DataFrame) -> tuple[list[dict], dict]:
    labels = switches[[f"sign__{measure}" for measure in MEASURES]].to_numpy(int)
    rows: list[dict] = []
    for weighting, weights in (
        ("official_LNKFW1MWT", switches.LNKFW1MWT.to_numpy(float)),
        ("unweighted", np.ones(len(switches))),
    ):
        for left_index, right_index in itertools.combinations(range(len(MEASURES)), 2):
            stats = CORE.cohen_kappa(labels[:, left_index], labels[:, right_index], weights)
            non_tie = (labels[:, left_index] != 0) & (labels[:, right_index] != 0)
            rows.append({
                "analysis_status": LABEL,
                "statistic": "pairwise_cohen_kappa",
                "weighting": weighting,
                "measure_1": MEASURES[left_index],
                "measure_2": MEASURES[right_index],
                "switches": len(switches),
                "raw_exact_agreement": stats["raw_exact_agreement"],
                "non_tie_direction_agreement": float(np.average(
                    labels[non_tie, left_index] == labels[non_tie, right_index],
                    weights=weights[non_tie],
                )),
                "opposite_sign_conflict": stats["opposite_sign_conflict"],
                "any_tie": stats["any_tie"],
                "expected_agreement": stats["expected_agreement"],
                "kappa": stats["cohen_kappa"],
                "categories": "-1|0|+1",
            })
    multi = {}
    for weighting, weights in (
        ("official_LNKFW1MWT_descriptive_weighted_analogue", switches.LNKFW1MWT.to_numpy(float)),
        ("unweighted_standard_Fleiss", np.ones(len(switches))),
    ):
        multi[weighting] = CORE.fleiss_kappa(labels, weights)
    return rows, {
        "analysis_status": LABEL,
        "switches": len(switches),
        "architectures": list(MEASURES),
        "categories": [-1, 0, 1],
        "fleiss": multi,
    }


def common_stock_support(data: dict) -> list[str]:
    webb = data["computers"]["webb_pct_software"]
    supports = [
        set(V4.finite_support(sorted(data["occupations"]), data["exposures"][measure]["A"], webb))
        for measure in MEASURES
    ]
    common = sorted(set.intersection(*supports))
    if len(common) != 444 or support_hash(common) != COMMON_SUPPORT_HASH:
        raise RuntimeError("frozen literal common stock support changed")
    return common


def fit_score_objects(young: np.ndarray, older: np.ndarray, regressors: np.ndarray):
    fit, influence = FROZEN.fit_with_influence(young, older, regressors)
    n_occ, n_month = young.shape
    total_full = (young + older).reshape(-1)
    keep = total_full > 0
    occupation_full = np.repeat(np.arange(n_occ), n_month)
    month_full = np.tile(np.arange(n_month), n_occ)
    total = total_full[keep]
    occupation = occupation_full[keep]
    month = month_full[keep]
    x = regressors[keep]
    probability = fit.fitted_probability[keep]
    residual = young.reshape(-1)[keep] - total * probability
    weight = np.maximum(total * probability * (1 - probability), 1e-12)
    rx = FROZEN.ENGINE._weighted_absorb(x, weight, occupation, month, n_occ, n_month)
    bread = np.linalg.inv(rx.T @ (weight[:, None] * rx))
    scores = rx * residual[:, None]
    two_way = CORE.two_way_cluster_covariance(bread, scores, occupation, month)
    return fit, influence, two_way


def joint_fg(data: dict, common: list[str], reference: pd.DataFrame) -> tuple[dict, list[dict]]:
    f_map = dict(zip(reference.census2018, reference.F))
    g_map = dict(zip(reference.census2018, reference.G))
    if any(code not in f_map or code not in g_map for code in common):
        raise RuntimeError("F/G maps are incomplete on frozen common support")
    young, older = FROZEN.panel_arrays(data["panel"], common, data["static_months"])
    weights = (young + older).sum(axis=1)
    webb_map = data["computers"]["webb_pct_software"]
    raw = {
        "F": np.array([f_map[code] for code in common], float),
        "G": np.array([g_map[code] for code in common], float),
        "Webb": np.array([webb_map[code] for code in common], float),
    }
    scale = {name: CORE.weighted_mean_sd(values, weights) for name, values in raw.items()}
    z = {name: (values - scale[name][0]) / scale[name][1] for name, values in raw.items()}
    post = np.array([month >= "2023-01" for month in data["static_months"]])
    regressors = np.column_stack([
        (z[name][:, None] * post[None, :]).reshape(-1) for name in ("F", "G", "Webb")
    ])
    fit, influence, _ = fit_score_objects(young, older, regressors)
    summary = CORE.wild_score_summary(fit.beta[:2], fit.standard_error[:2], influence[:, :2], FG_SEED, DRAWS)
    result_rows = []
    for name, item in zip(("consensus_F_z_x_young_x_post", "between_family_G_z_x_young_x_post"), summary["rows"]):
        result_rows.append({"analysis_status": LABEL, "term": name, **item})
    result = {
        "analysis_status": LABEL,
        "record": "exactly one authorized V5.1 labor-outcome specification",
        "model": "joint continuous consensus F plus between-family disagreement G plus Webb",
        "new_labor_outcome_specification_count": 1,
        "support_occupations": len(common),
        "support_hash_sha256": support_hash(common),
        "months": len(data["static_months"]),
        "transition_excluded": "2022-12",
        "source_gap": "2025-10",
        "component_scaling": {
            name: {"weighted_mean": mean, "weighted_sd": sd}
            for name, (mean, sd) in scale.items()
        },
        "terms": result_rows,
        "centered_bootstrap_covariance_F_G": float(summary["centered_shift_covariance"][0, 1]),
        "centered_bootstrap_correlation_F_G": float(
            summary["centered_shift_covariance"][0, 1]
            / math.sqrt(summary["centered_shift_covariance"][0, 0] * summary["centered_shift_covariance"][1, 1])
        ),
        "joint_null": "beta_F = beta_G = 0",
        "joint_max_abs_t": summary["joint_max_abs_t"],
        "joint_max_abs_t_p_value": summary["joint_max_abs_t_p_value"],
        "wild_score_draws": DRAWS,
        "wild_score_seed": FG_SEED,
        "interpretation_guardrail": "G is only the AIOE-versus-Eloundou family-centroid dimension and is not all architecture-specific disagreement",
    }
    return result, result_rows


def two_way_sensitivity(data: dict, common: list[str], args: argparse.Namespace) -> list[dict]:
    rows = []
    webb = data["computers"]["webb_pct_software"]
    frozen = json.loads(args.frozen_results.read_text())
    primary_key = "dv_rating_beta__RuleA__webb_pct_software__q5_q1"
    expected_primary = frozen["headline"][primary_key]["coefficients"]["AI_Q5_x_post"]["coefficient"]
    specifications = [("primary_beta_Webb_native_strict_support", "dv_rating_beta", None, expected_primary)]
    sealed = pd.read_csv(args.table5b_results).set_index("measure")
    specifications.extend([
        (f"literal_common__{measure}", measure, common, float(sealed.loc[measure, "coefficient_log_points"]))
        for measure in MEASURES
    ])
    for label, measure, support, expected in specifications:
        base = sorted(data["occupations"]) if support is None else support
        prepared = FROZEN.prepare_model(
            data["panel"], base, data["static_months"], data["exposures"][measure]["A"], webb, scale="q5_q1"
        )
        fit, _, two_way = fit_score_objects(prepared["young"], prepared["older"], prepared["regressors"])
        target = prepared["target"]
        coefficient = float(fit.beta[target])
        if not np.isclose(coefficient, expected, atol=1e-10, rtol=0):
            raise RuntimeError(f"sealed point estimate failed to reproduce for {label}: {coefficient} != {expected}")
        variance = float(two_way["covariance"][target, target])
        if not np.isfinite(variance) or variance <= 0:
            raise RuntimeError(f"two-way target variance is invalid for {label}: {variance}")
        se = math.sqrt(variance)
        rows.append({
            "analysis_status": LABEL,
            "specification": label,
            "measure": measure,
            "support": "native strict" if support is None else "literal six-measure common",
            "occupations": len(prepared["occupations"]),
            "months": len(data["static_months"]),
            "coefficient_log_points": coefficient,
            "one_way_occupation_cluster_se": float(fit.standard_error[target]),
            "two_way_occupation_month_cluster_se": se,
            "two_way_normal_ci_lower": coefficient - 1.959963984540054 * se,
            "two_way_normal_ci_upper": coefficient + 1.959963984540054 * se,
            "occupation_clusters": two_way["occupation_clusters"],
            "month_clusters": two_way["month_clusters"],
            "nonzero_cells": two_way["nonzero_cells"],
            "interpretation": "model-based dependence sensitivity; not a survey-design correction",
        })
    return rows


def render_fg_markdown(path: pathlib.Path, result: dict) -> None:
    rows = result["terms"]
    lines = [
        "# YAX V5.1 joint F+G stock-model results", "",
        "**POST-OUTCOME EXPLORATORY.** Exactly one new labor-outcome specification was executed.", "",
        "| Term | Coefficient | Occupation-cluster SE | Wild-score 95% CI | p |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['term']} | {row['coefficient']:.6f} | {row['analytic_cluster_se']:.6f} | "
            f"[{row['wild_score_ci_lower']:.6f}, {row['wild_score_ci_upper']:.6f}] | {row['wild_score_p_value']:.3f} |"
        )
    lines += [
        "",
        f"Centered wild-score covariance of F and G estimates: `{result['centered_bootstrap_covariance_F_G']:.8f}`.",
        f"Joint max-|t| test of beta_F=beta_G=0: p = `{result['joint_max_abs_t_p_value']:.3f}`.",
        "",
        "F is the family-balanced consensus component. G is only the between-family AIOE-versus-Eloundou centroid dimension; it is not all architecture-specific disagreement. This model is observational and does not identify a causal AI effect.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(args: argparse.Namespace) -> dict:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    authentication = authenticate(args)
    reference, moments = P3.load_reference_components(args.characteristics)
    correlations = correlation_rows(reference)

    _, switches, _, link, _, _ = P3.build_switch_frame(args, moments)
    kappas, fleiss = kappa_rows(switches)

    data = V4.load_inputs(args)
    common = common_stock_support(data)
    fg_result, fg_rows = joint_fg(data, common, reference)
    two_way = two_way_sensitivity(data, common, args)

    outputs = {
        "YAX_V51_EXPOSURE_CORRELATIONS.csv": correlations,
        "YAX_V51_KAPPA_AGREEMENT.csv": kappas,
        "YAX_V51_FG_JOINT_MODEL_RESULTS.csv": fg_rows,
        "YAX_V51_TWOWAY_CLUSTER_SENSITIVITY.csv": two_way,
    }
    for name, rows in outputs.items():
        write_csv(args.output_dir / name, rows)
    write_json(args.output_dir / "YAX_V51_KAPPA_SUMMARY.json", fleiss)
    write_json(args.output_dir / "YAX_V51_FG_JOINT_MODEL_RESULTS.json", fg_result)
    render_fg_markdown(args.output_dir / "YAX_V51_FG_JOINT_MODEL_RESULTS.md", fg_result)

    output_paths = [args.output_dir / name for name in outputs]
    output_paths += [
        args.output_dir / "YAX_V51_KAPPA_SUMMARY.json",
        args.output_dir / "YAX_V51_FG_JOINT_MODEL_RESULTS.json",
        args.output_dir / "YAX_V51_FG_JOINT_MODEL_RESULTS.md",
    ]
    receipt = {
        "record": "YAX V5.1 closed referee-repair execution",
        "analysis_status": LABEL,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "parent_commit": PARENT,
        "pre_result_commit": args.pre_result_commit,
        "execution_head": authentication["head"],
        "protected_peeled_commits": authentication["protected"],
        "input_hashes": authentication["input_hashes"],
        "all_new_analyses_executed": [
            "pairwise Cohen kappa and one Fleiss-type diagnostic on frozen switches",
            "six-measure weighted Pearson and weighted average-rank correlation matrices",
            "one joint continuous F+G stock specification",
            "two-way occupation-by-month model-based covariance sensitivity for seven existing stock specifications",
        ],
        "new_labor_outcome_specification_count": 1,
        "new_labor_outcome_specifications": ["joint_continuous_consensus_F_plus_between_family_G_plus_Webb"],
        "new_labor_outcome_specification_executed_successfully": True,
        "fg_seed": FG_SEED,
        "fg_wild_score_draws": DRAWS,
        "common_stock_support_occupations": len(common),
        "common_stock_support_hash_sha256": support_hash(common),
        "switches": len(switches),
        "link_sample": link,
        "artifact_hashes": {path.name: sha256(path) for path in output_paths},
        "prohibited_analysis_executed": False,
    }
    write_json(args.output_dir / "YAX_V51_EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({
        "status": "PASS_V51_CLOSED_EXECUTION",
        "new_labor_outcome_specifications": 1,
        "F": fg_result["terms"][0],
        "G": fg_result["terms"][1],
        "switches": len(switches),
    }, indent=2))
    return receipt


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--pre-result-commit", required=True)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--weight-patch", type=pathlib.Path, required=True)
    value.add_argument("--preperiod-cells", type=pathlib.Path, required=True)
    value.add_argument("--lookup", type=pathlib.Path, default=ROOT / "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv")
    value.add_argument("--computerization", type=pathlib.Path, default=ROOT / "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv")
    value.add_argument("--bridge", type=pathlib.Path, default=ROOT / "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv")
    value.add_argument("--rule-b-values", type=pathlib.Path, default=ROOT / "yax/measurement/RULE_B_VALUES_CENSUS2018.csv")
    value.add_argument("--first-access-receipt", type=pathlib.Path, default=ROOT / "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json")
    value.add_argument("--characteristics", type=pathlib.Path, default=ROOT / "yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv")
    value.add_argument("--table5b-results", type=pathlib.Path, default=ROOT / "yax/analysis/postoutcome_v4_supplementary/TABLE5B_COMMON_SUPPORT_RESULTS.csv")
    value.add_argument("--frozen-results", type=pathlib.Path, default=ROOT / "yax/analysis/outcomes/frozen_v11_corrected_run/FROZEN_RESULTS.json")
    value.add_argument("--output-dir", type=pathlib.Path, default=HERE)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
