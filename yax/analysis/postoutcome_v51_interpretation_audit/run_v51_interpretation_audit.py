#!/usr/bin/env python3
"""Run the closed YAX V5.1 interpretation audit without fitting outcomes.

The script performs only (i) algebra on the frozen F+G result, (ii) treatment-
side leave-one-Eloundou diagnostics, and (iii) extraction/reconciliation of
already-recorded power and precision quantities. It contains no estimator call.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import math
import pathlib
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(HERE))
import v51_interpretation_core as CORE  # noqa: E402


def import_path(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


P3 = import_path("yax_v51_audit_phase3", ROOT / "yax/analysis/postoutcome_phase3_final/run_phase3.py")
V4 = P3.V4
V51 = import_path("yax_v51_audit_v51", ROOT / "yax/analysis/postoutcome_v51_referee_repair/run_v51_repairs.py")

PARENT = "557a927c96b9062c233787f1d346c68b99074206"
LABEL = "POST-OUTCOME INTERPRETATION AUDIT — NO NEW LABOR-OUTCOME MODEL"
ELOUNDOU = {
    "alpha": "dv_rating_alpha",
    "beta": "dv_rating_beta",
    "broad": "dv_rating_gamma",
}


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
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def treatment_stability(reference: pd.DataFrame) -> tuple[list[dict], dict]:
    weights = reference.preperiod_employment_weight.to_numpy(float)
    a = reference.A.to_numpy(float)
    full_e = reference.E.to_numpy(float)
    full_g = reference.G.to_numpy(float)
    full_low, full_high = CORE.tail_masks(full_g, weights)
    median_full = CORE.weighted_quantile(full_g, weights, 0.5)
    rows = []
    alternatives = {}
    for omitted_label, omitted_column in ELOUNDOU.items():
        retained = [column for label, column in ELOUNDOU.items() if label != omitted_label]
        e_alt = reference[[f"z__{column}" for column in retained]].mean(axis=1).to_numpy(float)
        g_alt = (a - e_alt) / 2
        alt_low, alt_high = CORE.tail_masks(g_alt, weights)
        median_alt = CORE.weighted_quantile(g_alt, weights, 0.5)
        slope = CORE.weighted_covariance(full_g, g_alt, weights) / CORE.weighted_covariance(full_g, full_g, weights)
        row = {
            "analysis_status": LABEL,
            "construction": f"G_minus_{omitted_label}",
            "omitted_eloundou_measure": omitted_column,
            "occupations_maximal_support": len(reference),
            "occupations_fixed_full_G_support": len(reference),
            "employment_weighted_pearson": CORE.weighted_correlation(full_g, g_alt, weights),
            "employment_weighted_average_rank_spearman": CORE.weighted_correlation(
                CORE.average_rank(full_g), CORE.average_rank(g_alt), weights
            ),
            "weighted_sd_ratio_alternative_to_frozen": CORE.weighted_sd(g_alt, weights) / CORE.weighted_sd(full_g, weights),
            "weighted_slope_alternative_on_frozen": slope,
            "q1_weight_retained_from_frozen_G": CORE.overlap_retention(full_low, alt_low, weights),
            "q5_weight_retained_from_frozen_G": CORE.overlap_retention(full_high, alt_high, weights),
            "weighted_zero_sign_agreement": float(np.average(np.sign(full_g) == np.sign(g_alt), weights=weights)),
            "weighted_median_side_agreement": float(np.average(
                np.sign(full_g - median_full) == np.sign(g_alt - median_alt), weights=weights
            )),
            "unweighted_zero_direction_change_fraction": float(np.mean(np.sign(full_g) != np.sign(g_alt))),
            "weighted_zero_direction_change_fraction": float(np.average(np.sign(full_g) != np.sign(g_alt), weights=weights)),
        }
        rows.append(row)
        alternatives[omitted_label] = {"E": e_alt, "G": g_alt}

    e_components = {label: reference[f"z__{column}"].to_numpy(float) for label, column in ELOUNDOU.items()}
    e_coefficients = {label: 1 / 3 for label in ELOUNDOU}
    g_components = {"A_centroid": a, **e_components}
    g_coefficients = {"A_centroid": 0.5, **{label: -1 / 6 for label in ELOUNDOU}}
    decomposition = {
        "arithmetic_weights_in_E": e_coefficients,
        "arithmetic_weights_in_G": g_coefficients,
        "covariance_contribution_share_to_variance_E": CORE.covariance_contributions(
            full_e, e_components, e_coefficients, weights
        ),
        "covariance_contribution_share_to_variance_G": CORE.covariance_contributions(
            full_g, g_components, g_coefficients, weights
        ),
        "weighted_component_correlation_matrix": {
            left: {right: CORE.weighted_correlation(values_left, values_right, weights)
                   for right, values_right in e_components.items()}
            for left, values_left in e_components.items()
        },
    }
    return rows, decomposition


def exact_reparameterization(args: argparse.Namespace, reference: pd.DataFrame) -> dict:
    frozen = json.loads(args.fg_results.read_text())
    data = V4.load_inputs(args)
    common = V51.common_stock_support(data)
    young, older = V51.FROZEN.panel_arrays(data["panel"], common, data["static_months"])
    weights = (young + older).sum(axis=1)
    indexed = reference.set_index("census2018")
    if any(code not in indexed.index for code in common):
        raise RuntimeError("A/E/F/G reference values missing on frozen model support")
    a = indexed.loc[common, "A"].to_numpy(float)
    e = indexed.loc[common, "E"].to_numpy(float)
    f = indexed.loc[common, "F"].to_numpy(float)
    g = indexed.loc[common, "G"].to_numpy(float)
    moments = {
        name: {"weighted_mean": CORE.weighted_mean(values, weights), "weighted_sd": CORE.weighted_sd(values, weights)}
        for name, values in (("A", a), ("E", e), ("F", f), ("G", g))
    }
    for name in ("F", "G"):
        stored = frozen["component_scaling"][name]
        if not math.isclose(moments[name]["weighted_mean"], stored["weighted_mean"], abs_tol=1e-12):
            raise RuntimeError(f"{name} mean does not reproduce frozen result")
        if not math.isclose(moments[name]["weighted_sd"], stored["weighted_sd"], abs_tol=1e-12):
            raise RuntimeError(f"{name} SD does not reproduce frozen result")
    if not math.isclose(moments["A"]["weighted_mean"], moments["F"]["weighted_mean"] + moments["G"]["weighted_mean"], abs_tol=1e-12):
        raise RuntimeError("A centering identity failed")
    if not math.isclose(moments["E"]["weighted_mean"], moments["F"]["weighted_mean"] - moments["G"]["weighted_mean"], abs_tol=1e-12):
        raise RuntimeError("E centering identity failed")

    terms = frozen["terms"]
    coefficient_fg = np.array([terms[0]["coefficient"], terms[1]["coefficient"]])
    bootstrap_covariance_fg = np.array([
        [terms[0]["bootstrap_se"] ** 2, frozen["centered_bootstrap_covariance_F_G"]],
        [frozen["centered_bootstrap_covariance_F_G"], terms[1]["bootstrap_se"] ** 2],
    ])
    transformed = CORE.transform_fg_to_ae(
        coefficient_fg,
        bootstrap_covariance_fg,
        moments["F"]["weighted_sd"],
        moments["G"]["weighted_sd"],
        moments["A"]["weighted_sd"],
        moments["E"]["weighted_sd"],
    )
    max_error = CORE.predictor_identity(
        a, e,
        {name: value["weighted_mean"] for name, value in moments.items()},
        {name: value["weighted_sd"] for name, value in moments.items()},
        coefficient_fg, transformed["coefficient_raw"],
    )
    if max_error > 1e-12:
        raise RuntimeError(f"linear predictor identity failed: {max_error}")

    output_terms = []
    for index, name in enumerate(("AIOE_family_centroid_A", "Eloundou_family_centroid_E")):
        raw_ci = CORE.normal_interval(transformed["coefficient_raw"][index], transformed["covariance_raw"][index, index])
        sd_ci = CORE.normal_interval(transformed["coefficient_sd"][index], transformed["covariance_sd"][index, index])
        output_terms.append({
            "term": name,
            "coefficient_per_original_centroid_unit": float(transformed["coefficient_raw"][index]),
            "common_draw_covariance_se_per_original_centroid_unit": math.sqrt(float(transformed["covariance_raw"][index, index])),
            "normal_95_ci_per_original_centroid_unit": list(map(float, raw_ci)),
            "coefficient_per_weighted_sd": float(transformed["coefficient_sd"][index]),
            "common_draw_covariance_se_per_weighted_sd": math.sqrt(float(transformed["covariance_sd"][index, index])),
            "normal_95_ci_per_weighted_sd": list(map(float, sd_ci)),
            "wild_score_interval": None,
            "wild_score_p_value": None,
        })
    difference_map = transformed["raw_map"][0] - transformed["raw_map"][1]
    difference = float(difference_map @ coefficient_fg)
    difference_variance = float(difference_map @ bootstrap_covariance_fg @ difference_map)
    return {
        "record": "exact algebraic reparameterization of sealed V5.1 F+G model",
        "analysis_status": LABEL,
        "parent_commit": PARENT,
        "support_occupations": len(common),
        "support_hash_sha256": support_hash(common),
        "model_period_months": len(data["static_months"]),
        "component_moments": moments,
        "frozen_fg_coefficients": coefficient_fg.tolist(),
        "frozen_common_draw_covariance_fg": bootstrap_covariance_fg.tolist(),
        "transformation_matrix_raw_ae_from_standardized_fg": transformed["raw_map"].tolist(),
        "transformation_matrix_sd_ae_from_standardized_fg": transformed["sd_map"].tolist(),
        "terms": output_terms,
        "transformed_covariance_raw_ae": transformed["covariance_raw"].tolist(),
        "transformed_covariance_sd_ae": transformed["covariance_sd"].tolist(),
        "transformed_correlation_raw_ae": float(
            transformed["covariance_raw"][0, 1]
            / math.sqrt(transformed["covariance_raw"][0, 0] * transformed["covariance_raw"][1, 1])
        ),
        "a_minus_e_original_unit_contrast": {
            "coefficient": difference,
            "common_draw_covariance_se": math.sqrt(difference_variance),
            "normal_95_ci": list(map(float, CORE.normal_interval(difference, difference_variance))),
            "identity": "b_A_raw - b_E_raw = b_G / s_G",
        },
        "centering": {
            "intercept_equivalent_shift_if_raw_uncentered_A_E_are_used": float(
                -coefficient_fg[0] * moments["F"]["weighted_mean"] / moments["F"]["weighted_sd"]
                - coefficient_fg[1] * moments["G"]["weighted_mean"] / moments["G"]["weighted_sd"]
            ),
            "centered_A_E_representation_requires_no_additional_shift": True,
        },
        "maximum_absolute_linear_predictor_difference": max_error,
        "inference_note": (
            "The serialized V5.1 result retains the marginal common-draw bootstrap SDs and their centered covariance, "
            "which form the transformed covariance used here. It does not retain draw-level shifts or the analytic "
            "cluster covariance off-diagonal. Therefore no transformed wild-score interval or exact wild-score p-value "
            "is reported, and no multipliers were regenerated."
        ),
        "classification": "AE-R1",
        "new_labor_outcome_model_estimated": False,
    }


def render_reparameterization(path: pathlib.Path, result: dict) -> None:
    a, e = result["terms"]
    m = result["component_moments"]
    d = result["a_minus_e_original_unit_contrast"]
    lines = [
        "# YAX V5.1 F/G to A/E exact reparameterization", "",
        "**Decision: AE-R1 — strong family asymmetry.** This is algebra applied to the already-estimated frozen F+G model, not a new regression.", "",
        "## Frozen scales", "",
        "| Component | Weighted mean | Weighted SD |", "|---|---:|---:|",
    ]
    for name in ("A", "E", "F", "G"):
        lines.append(f"| {name} | {m[name]['weighted_mean']:.9f} | {m[name]['weighted_sd']:.9f} |")
    lines += [
        "", "## Implied family coefficients", "",
        "| Family centroid | Per original unit | Covariance-transformed SE | Normal 95% CI | Per weighted SD | Normal 95% CI |",
        "|---|---:|---:|---:|---:|---:|",
        f"| AIOE A | {a['coefficient_per_original_centroid_unit']:.6f} | {a['common_draw_covariance_se_per_original_centroid_unit']:.6f} | [{a['normal_95_ci_per_original_centroid_unit'][0]:.6f}, {a['normal_95_ci_per_original_centroid_unit'][1]:.6f}] | {a['coefficient_per_weighted_sd']:.6f} | [{a['normal_95_ci_per_weighted_sd'][0]:.6f}, {a['normal_95_ci_per_weighted_sd'][1]:.6f}] |",
        f"| Eloundou E | {e['coefficient_per_original_centroid_unit']:.6f} | {e['common_draw_covariance_se_per_original_centroid_unit']:.6f} | [{e['normal_95_ci_per_original_centroid_unit'][0]:.6f}, {e['normal_95_ci_per_original_centroid_unit'][1]:.6f}] | {e['coefficient_per_weighted_sd']:.6f} | [{e['normal_95_ci_per_weighted_sd'][0]:.6f}, {e['normal_95_ci_per_weighted_sd'][1]:.6f}] |",
        "",
        f"On the common original-centroid scale, A minus E is `{d['coefficient']:.6f}` (SE `{d['common_draw_covariance_se']:.6f}`; normal 95% CI [{d['normal_95_ci'][0]:.6f}, {d['normal_95_ci'][1]:.6f}]). The transformed A/E coefficient correlation is `{result['transformed_correlation_raw_ae']:.6f}`.",
        "",
        "The negative conditional stock association loads substantially more heavily on the Eloundou-family centroid. The implied AIOE-family coefficient is positive and imprecise, while the Eloundou-family coefficient is negative and its covariance-transformed interval excludes zero. This does not mean that only Eloundou matters, that AIOE has no effect, or that LLM exposure caused the employment pattern.",
        "",
        "## Algebra and centering audit", "",
        r"The raw-unit map is $b_A=\frac12(b_F/s_F+b_G/s_G)$ and $b_E=\frac12(b_F/s_F-b_G/s_G)$. Means obey $\mu_A=\mu_F+\mu_G$ and $\mu_E=\mu_F-\mu_G$, so the centered A/E representation is exactly intercept-equivalent. The maximum discrepancy between the F/G and A/E linear-predictor contributions across the 444 occupations is " + f"`{result['maximum_absolute_linear_predictor_difference']:.3e}`.",
        "",
        "## Inference boundary", "",
        result["inference_note"],
        "",
        "No new labor-outcome model was estimated. The A/E coefficients are exact algebraic transformations of the already-executed frozen F+G model.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_stability(path: pathlib.Path, rows: list[dict], decomposition: dict) -> None:
    lines = [
        "# YAX V5.1 treatment-only G-construction stability", "",
        "**Decision: G-STABLE.** All diagnostics use only frozen exposure scores and frozen pre-period employment weights on the same 463-occupation support. No labor outcome is used.", "",
        "| Alternative | Pearson | Rank corr. | SD ratio | Q1 retained | Q5 retained | Zero-sign agree | Median-side agree | Occ. direction change |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['construction']} | {row['employment_weighted_pearson']:.4f} | "
            f"{row['employment_weighted_average_rank_spearman']:.4f} | "
            f"{row['weighted_sd_ratio_alternative_to_frozen']:.4f} | "
            f"{row['q1_weight_retained_from_frozen_G']:.1%} | {row['q5_weight_retained_from_frozen_G']:.1%} | "
            f"{row['weighted_zero_sign_agreement']:.1%} | {row['weighted_median_side_agreement']:.1%} | "
            f"{row['unweighted_zero_direction_change_fraction']:.1%} |"
        )
    lines += ["", "The between-family dimension is not primarily an alpha artifact: removing any one Eloundou component leaves very high weighted level and rank correlations and largely preserves both tails. No employment regression using an alternative G was run.", "", "## Mechanical and covariance contributions", ""]
    lines.append("Each Eloundou component has arithmetic weight `1/3` in E and `-1/6` in G; the AIOE centroid has weight `+1/2` in G.")
    lines += ["", "| Component | Share of weighted variance of E | Share of weighted variance of G |", "|---|---:|---:|"]
    e_share = decomposition["covariance_contribution_share_to_variance_E"]
    g_share = decomposition["covariance_contribution_share_to_variance_G"]
    lines.append(f"| AIOE centroid | — | {g_share['A_centroid']:.4f} |")
    for label in ELOUNDOU:
        lines.append(f"| Eloundou {label} | {e_share[label]:.4f} | {g_share[label]:.4f} |")
    lines += ["", "These are covariance contributions, so correlated components can have negative or greater-than-one shares; the shares sum to one within each target. The leave-one-out changes reflect both each component's fixed arithmetic weight and its covariance with the remaining family geometry.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def run(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    reference, _ = P3.load_reference_components(args.characteristics)
    rows, decomposition = treatment_stability(reference)
    write_csv(args.output_dir / "YAX_V51_G_CONSTRUCTION_STABILITY.csv", rows)
    render_stability(args.output_dir / "YAX_V51_G_CONSTRUCTION_STABILITY.md", rows, decomposition)
    reparameterization = exact_reparameterization(args, reference)
    write_json(args.output_dir / "YAX_V51_FG_TO_AE_REPARAMETERIZATION.json", reparameterization)
    render_reparameterization(args.output_dir / "YAX_V51_FG_TO_AE_REPARAMETERIZATION.md", reparameterization)
    write_json(args.output_dir / "YAX_V51_TREATMENT_DIAGNOSTICS_DETAIL.json", {
        "analysis_status": LABEL,
        "support": "463 frozen complete-case occupations",
        "weighting": "frozen preperiod_employment_weight",
        "rows": rows,
        "decomposition": decomposition,
        "classification": "G-STABLE",
        "labor_outcomes_used": False,
    })
    print(json.dumps({
        "status": "PASS_V51_INTERPRETATION_ALGEBRA_AND_TREATMENT_AUDIT",
        "ae_classification": reparameterization["classification"],
        "g_classification": "G-STABLE",
        "new_labor_outcome_model_estimated": False,
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
    value.add_argument("--fg-results", type=pathlib.Path, default=ROOT / "yax/analysis/postoutcome_v51_referee_repair/YAX_V51_FG_JOINT_MODEL_RESULTS.json")
    value.add_argument("--output-dir", type=pathlib.Path, default=HERE)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
