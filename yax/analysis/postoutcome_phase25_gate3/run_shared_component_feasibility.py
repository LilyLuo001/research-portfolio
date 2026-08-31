#!/usr/bin/env python3
"""Audit shared versus architecture-specific exposure structure.

POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1.
Uses frozen exposure measures, pre-period occupation weights, and existing
occupation characteristics only. No labor outcome is read or estimated.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import pathlib

import numpy as np
import pandas as pd


LABEL = "POST-OUTCOME EXPLORATORY — NOT PART OF CONFIRMATORY YAX v1.1"
AIOE = ["aioe_admin_equal", "aioe_ability_direct", "aioe_oews2018_source_weighted"]
ELOUNDOU = ["dv_rating_alpha", "dv_rating_beta", "dv_rating_gamma"]
MEASURES = AIOE + ELOUNDOU
CHARACTERISTICS = [
    "cognitive_ability_importance", "manual_physical_ability_importance",
    "rti_autor_dorn", "required_education_category_index", "log_mean_annual_wage",
    "dingel_neiman_telework", "stem_major_group_share", "onet_computers_importance",
]


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def weighted_mean_sd(values: np.ndarray, weights: np.ndarray) -> tuple[float, float]:
    mean = float(np.average(values, weights=weights))
    sd = float(np.sqrt(np.average((values - mean) ** 2, weights=weights)))
    return mean, sd


def weighted_standardize(values: np.ndarray, weights: np.ndarray) -> np.ndarray:
    mean, sd = weighted_mean_sd(values, weights)
    if not sd > 0:
        raise ValueError("cannot standardize a constant exposure")
    return (values - mean) / sd


def weighted_corr(x: np.ndarray, y: np.ndarray, weights: np.ndarray) -> float:
    xz, yz = weighted_standardize(x, weights), weighted_standardize(y, weights)
    return float(np.average(xz * yz, weights=weights))


def family_balanced_shared(frame: pd.DataFrame, weights: np.ndarray,
                           aioe: list[str] = AIOE,
                           eloundou: list[str] = ELOUNDOU) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return equally weighted AIOE family, Eloundou family, and shared scores."""
    if not aioe or not eloundou:
        raise ValueError("both construction families are required")
    standardized = {
        measure: weighted_standardize(frame[measure].to_numpy(float), weights)
        for measure in [*aioe, *eloundou]
    }
    aioe_score = np.mean([standardized[measure] for measure in aioe], axis=0)
    eloundou_score = np.mean([standardized[measure] for measure in eloundou], axis=0)
    aioe_score = weighted_standardize(aioe_score, weights)
    eloundou_score = weighted_standardize(eloundou_score, weights)
    shared = weighted_standardize((aioe_score + eloundou_score) / 2, weights)
    return aioe_score, eloundou_score, shared


def weighted_correlation_matrix(frame: pd.DataFrame, columns: list[str],
                                weights: np.ndarray, rank: bool = False) -> np.ndarray:
    values = []
    for column in columns:
        vector = frame[column].rank(method="average").to_numpy(float) if rank else frame[column].to_numpy(float)
        values.append(weighted_standardize(vector, weights))
    z = np.column_stack(values)
    return (z * (weights / weights.sum())[:, None]).T @ z


def pca(correlation: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    values, vectors = np.linalg.eigh(correlation)
    order = np.argsort(values)[::-1]
    values, vectors = values[order], vectors[:, order]
    for column in range(vectors.shape[1]):
        if vectors[:, column].sum() < 0:
            vectors[:, column] *= -1
    return values, vectors


def run(characteristics_path: pathlib.Path, output_dir: pathlib.Path) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(characteristics_path, dtype={"census2018": str})
    required = ["census2018", "occupation", "preperiod_employment_weight", *MEASURES]
    frame = raw[required + [column for column in CHARACTERISTICS if column in raw]].dropna(subset=required).copy()
    frame["census2018"] = frame.census2018.str.zfill(4)
    weights = frame.preperiod_employment_weight.to_numpy(float)
    if np.any(~np.isfinite(weights)) or np.any(weights <= 0):
        raise ValueError("pre-period weights must be positive and finite")

    diagnostics: list[dict] = []
    loadings: list[dict] = []
    stability: list[dict] = []
    pearson = weighted_correlation_matrix(frame, MEASURES, weights)
    spearman = weighted_correlation_matrix(frame, MEASURES, weights, rank=True)
    unweighted = frame[MEASURES].corr().to_numpy(float)
    unweighted_rank = frame[MEASURES].corr(method="spearman").to_numpy(float)
    for left_index, left in enumerate(MEASURES):
        for right_index, right in enumerate(MEASURES):
            if right_index < left_index:
                continue
            for metric, matrix in (
                ("weighted_pearson", pearson), ("weighted_spearman", spearman),
                ("unweighted_pearson", unweighted), ("unweighted_spearman", unweighted_rank),
            ):
                diagnostics.append({
                    "analysis_status": LABEL, "section": "correlation", "metric": metric,
                    "item_1": left, "item_2": right, "value": float(matrix[left_index, right_index]),
                    "occupations": len(frame), "note": "literal six-measure complete support",
                })

    eigenvalues, eigenvectors = pca(pearson)
    for index, value in enumerate(eigenvalues, start=1):
        diagnostics.append({
            "analysis_status": LABEL, "section": "pca", "metric": "weighted_correlation_eigenvalue",
            "item_1": f"PC{index}", "item_2": "", "value": float(value),
            "occupations": len(frame), "note": f"cumulative variance share={eigenvalues[:index].sum()/len(MEASURES):.8f}",
        })
    diagnostics.extend([
        {"analysis_status": LABEL, "section": "pca", "metric": "one_factor_variance_share",
         "item_1": "PC1", "item_2": "", "value": float(eigenvalues[0] / len(MEASURES)),
         "occupations": len(frame), "note": "descriptive PCA, not a latent true-exposure model"},
        {"analysis_status": LABEL, "section": "pca", "metric": "two_factor_variance_share",
         "item_1": "PC1+PC2", "item_2": "", "value": float(eigenvalues[:2].sum() / len(MEASURES)),
         "occupations": len(frame), "note": "descriptive PCA, not a latent true-exposure model"},
    ])
    for component in range(2):
        component_loadings = eigenvectors[:, component] * np.sqrt(eigenvalues[component])
        for measure, value in zip(MEASURES, component_loadings):
            loadings.append({
                "analysis_status": LABEL, "model": "six_measure_weighted_pca",
                "component": f"PC{component + 1}", "measure": measure,
                "family": "AIOE" if measure in AIOE else "Eloundou", "loading": float(value),
                "occupations": len(frame),
            })

    aioe_score, eloundou_score, shared = family_balanced_shared(frame, weights)
    family_corr = weighted_corr(aioe_score, eloundou_score, weights)
    diagnostics.append({
        "analysis_status": LABEL, "section": "family_balanced", "metric": "family_composite_correlation",
        "item_1": "AIOE family", "item_2": "Eloundou family", "value": family_corr,
        "occupations": len(frame), "note": "each construction family receives total weight 1/2",
    })
    for name, values in (("AIOE_family", aioe_score), ("Eloundou_family", eloundou_score)):
        diagnostics.append({
            "analysis_status": LABEL, "section": "family_balanced", "metric": "correlation_with_shared_component",
            "item_1": name, "item_2": "family_balanced_shared", "value": weighted_corr(values, shared, weights),
            "occupations": len(frame), "note": "shared component is standardized equal-family average",
        })

    # Leave one measure out while retaining both construction families.
    for omitted in MEASURES:
        aioe = [measure for measure in AIOE if measure != omitted]
        eloundou = [measure for measure in ELOUNDOU if measure != omitted]
        _, _, candidate = family_balanced_shared(frame, weights, aioe, eloundou)
        stability.append({
            "analysis_status": LABEL, "diagnostic": "leave_one_measure_out",
            "omitted": omitted, "families_retained": "AIOE|Eloundou",
            "correlation_with_full_family_balanced_component": weighted_corr(candidate, shared, weights),
            "family_total_weights": "AIOE=0.5;Eloundou=0.5",
            "identifies_cross_family_shared_dimension": True,
            "note": "all calculations stay on literal six-measure complete support",
        })

    for omitted, remaining, score in (
        ("AIOE family", "Eloundou family only", eloundou_score),
        ("Eloundou family", "AIOE family only", aioe_score),
    ):
        stability.append({
            "analysis_status": LABEL, "diagnostic": "leave_one_family_out_limitation",
            "omitted": omitted, "families_retained": remaining,
            "correlation_with_full_family_balanced_component": weighted_corr(score, shared, weights),
            "family_total_weights": "not defined across families",
            "identifies_cross_family_shared_dimension": False,
            "note": "one remaining construction family cannot identify a cross-family common component",
        })

    # Architecture-specific residuals from a weighted projection on the shared
    # component. Associations use only characteristics already in Test A.
    design = np.column_stack([np.ones(len(frame)), shared])
    root_w = np.sqrt(weights / weights.mean())
    family_contrast = weighted_standardize(aioe_score - eloundou_score, weights)
    for measure in MEASURES:
        y = weighted_standardize(frame[measure].to_numpy(float), weights)
        coefficient = np.linalg.lstsq(design * root_w[:, None], y * root_w, rcond=None)[0]
        residual = y - design @ coefficient
        residual_sd = weighted_mean_sd(residual, weights)[1]
        diagnostics.append({
            "analysis_status": LABEL, "section": "architecture_specific_residual",
            "metric": "residual_sd", "item_1": measure, "item_2": "shared component",
            "value": residual_sd, "occupations": len(frame),
            "note": "weighted linear projection; descriptive, no labor outcome",
        })
        diagnostics.append({
            "analysis_status": LABEL, "section": "architecture_specific_residual",
            "metric": "correlation_with_family_contrast", "item_1": measure,
            "item_2": "AIOE minus Eloundou family composite",
            "value": weighted_corr(residual, family_contrast, weights), "occupations": len(frame),
            "note": "construction-family diagnostic",
        })
        for characteristic in CHARACTERISTICS:
            if characteristic not in frame:
                continue
            valid = frame[characteristic].notna().to_numpy()
            if valid.sum() < 10:
                continue
            diagnostics.append({
                "analysis_status": LABEL, "section": "residual_interpretability",
                "metric": "weighted_pearson", "item_1": measure, "item_2": characteristic,
                "value": weighted_corr(residual[valid], frame.loc[valid, characteristic].to_numpy(float), weights[valid]),
                "occupations": int(valid.sum()), "note": "existing Test-A occupation characteristic only",
            })

    diagnostics_path = output_dir / "YAX_EXPOSURE_FACTOR_DIAGNOSTICS.csv"
    loadings_path = output_dir / "YAX_EXPOSURE_FACTOR_LOADINGS.csv"
    stability_path = output_dir / "YAX_EXPOSURE_FACTOR_STABILITY.csv"
    pd.DataFrame(diagnostics).to_csv(diagnostics_path, index=False, quoting=csv.QUOTE_MINIMAL)
    pd.DataFrame(loadings).to_csv(loadings_path, index=False, quoting=csv.QUOTE_MINIMAL)
    pd.DataFrame(stability).to_csv(stability_path, index=False, quoting=csv.QUOTE_MINIMAL)
    receipt = {
        "record": "YAX shared-component feasibility execution receipt",
        "analysis_status": LABEL, "input": str(characteristics_path),
        "input_sha256": sha256(characteristics_path), "occupations": len(frame),
        "support_definition": "finite values on all six frozen exposures and positive pre-period weight",
        "weighting_rule": "preperiod_employment_weight; each family gets total weight 1/2",
        "measures": MEASURES, "existing_characteristics_only": CHARACTERISTICS,
        "labor_outcomes_read": [], "labor_outcome_regressions": [],
        "outputs": {path.name: sha256(path) for path in [diagnostics_path, loadings_path, stability_path]},
    }
    receipt_path = output_dir / "YAX_SHARED_COMPONENT_EXECUTION_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "occupations": len(frame), "family_composite_correlation": family_corr,
        "pc1_share": float(eigenvalues[0] / len(MEASURES)),
        "pc1_pc2_share": float(eigenvalues[:2].sum() / len(MEASURES)),
        "minimum_lomo_correlation": min(row["correlation_with_full_family_balanced_component"]
                                        for row in stability if row["diagnostic"] == "leave_one_measure_out"),
    }, indent=2))
    return receipt


def main() -> int:
    root = pathlib.Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--characteristics", type=pathlib.Path,
                        default=root / "yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv")
    parser.add_argument("--output-dir", type=pathlib.Path,
                        default=pathlib.Path(__file__).resolve().parent)
    args = parser.parse_args()
    run(args.characteristics, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
