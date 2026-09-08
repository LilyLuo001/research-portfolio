#!/usr/bin/env python3
"""Execute the frozen YAX S05 broader-beta-support comparison.

This is a post-outcome, required-revision analysis.  It does not alter the
scientific estimator.  It separates Webb conditioning, fixed-cutoff support
expansion, and broader-support reclassification in that order.
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
from typing import Any

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
SPEC_PATH = HERE / "BROADER_SUPPORT_SPEC.json"
DRAWS = 9_999
SEED = 2026090851
MDE_FACTOR = 1.959963984540054 + 0.8416212335729143
PRIMARY_COUNT = 468
PRIMARY_HASH = "11ec58ab1004cd83d62c57785f6c0dd3ee5a8abf08b7f71a3b664e91ded8333b"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_module(name: str, path: pathlib.Path):
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise RuntimeError(f"cannot import required module {name}")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[name] = module
    module_spec.loader.exec_module(module)
    return module


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def content_id(prefix: str, value: Any) -> str:
    return f"{prefix}_{hashlib.sha256(canonical_bytes(value)).hexdigest()}"


def spec_identity(spec: dict[str, Any]) -> str:
    payload = dict(spec)
    payload.pop("spec_id", None)
    return content_id("yaxgate2broadsupport_v1", payload)


def support_hash(codes: list[str]) -> str:
    return hashlib.sha256("".join(f"{code}\n" for code in sorted(codes)).encode()).hexdigest()


def write_json(path: pathlib.Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def write_csv(path: pathlib.Path, rows: list[dict[str, Any]]) -> None:
    require(bool(rows), f"refusing to write empty output {path.name}")
    fields: list[str] = []
    for row in rows:
        fields.extend(key for key in row if key not in fields)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def higher_quantile(values: np.ndarray, probability: float) -> float:
    return float(np.quantile(values, probability, method="higher"))


def groups_from_fixed_cuts(values: np.ndarray, cuts: np.ndarray) -> np.ndarray:
    values = np.asarray(values, float)
    cuts = np.asarray(cuts, float)
    require(values.ndim == 1 and np.isfinite(values).all(), "fixed-cut values invalid")
    require(cuts.shape == (4,) and np.isfinite(cuts).all(), "fixed cuts invalid")
    require(bool(np.all(np.diff(cuts) > 0)), "fixed cuts are not strictly increasing")
    return (np.searchsorted(cuts, values, side="left") + 1).astype(int)


def select_sign_columns(signs: np.ndarray, indices: list[int]) -> np.ndarray:
    matrix = np.asarray(signs, float)
    selected = np.asarray(indices, int)
    require(matrix.ndim == 2, "multiplier matrix must be two dimensional")
    require(selected.ndim == 1 and len(selected) > 0, "multiplier column selection is empty")
    require(selected.min() >= 0 and selected.max() < matrix.shape[1], "multiplier column selection is out of range")
    return matrix[:, selected]


def inference(fit, influence: np.ndarray, target: int, signs: np.ndarray) -> tuple[dict[str, Any], np.ndarray]:
    centered = signs @ influence[:, target]
    estimate = float(fit.beta[target])
    analytic_se = float(fit.standard_error[target])
    bootstrap_se = float(np.std(centered, ddof=1))
    require(analytic_se > 0 and bootstrap_se > 0, "nonpositive inference scale")
    critical = higher_quantile(np.abs(centered / analytic_se), 0.95)
    p_value = float((1 + np.sum(np.abs(centered / analytic_se) >= abs(estimate / analytic_se))) / (len(centered) + 1))
    return {
        "coefficient": estimate,
        "analytic_occupation_cluster_se": analytic_se,
        "bootstrap_se": bootstrap_se,
        "ci_lower": estimate - critical * analytic_se,
        "ci_upper": estimate + critical * analytic_se,
        "bootstrap_p_value": p_value,
        "bootstrap_critical": critical,
        "mde80": MDE_FACTOR * analytic_se,
        "draws": len(centered),
        "seed": SEED,
        "converged": bool(fit.converged),
        "iterations": int(fit.iterations),
    }, centered


def paired(left_name: str, right_name: str, left: dict[str, Any], right: dict[str, Any], left_draws: np.ndarray, right_draws: np.ndarray) -> dict[str, Any]:
    centered = np.asarray(left_draws) - np.asarray(right_draws)
    delta = float(left["coefficient"] - right["coefficient"])
    se = float(np.std(centered, ddof=1))
    require(se > 0, "nonpositive paired inference scale")
    critical = higher_quantile(np.abs(centered / se), 0.95)
    return {
        "left": left_name,
        "right": right_name,
        "coefficient_difference": delta,
        "paired_bootstrap_se": se,
        "ci_lower": delta - critical * se,
        "ci_upper": delta + critical * se,
        "paired_bootstrap_p_value": float((1 + np.sum(np.abs(centered / se) >= abs(delta / se))) / (len(centered) + 1)),
        "bootstrap_critical": critical,
        "mde80_difference": MDE_FACTOR * se,
        "common_multiplier_draws": True,
        "draws": len(centered),
        "seed": SEED,
        "interpretation_if_ci_contains_zero": "design does not detect a difference; not economic equivalence",
    }


def build_bundle(NUM, model_id: str, support: list[str], months: list[str], young: np.ndarray, older: np.ndarray, regressors: np.ndarray, labels: list[str]) -> Any:
    rows = len(support) * len(months)
    frame = pd.DataFrame({
        "occ_code": np.repeat(np.asarray(support, object), len(months)),
        "month": np.tile(np.asarray(months, object), len(support)),
    })
    frame["young"] = young.reshape(-1)
    frame["older"] = older.reshape(-1)
    return NUM.ModelBundle(
        model_id=model_id,
        frame=frame,
        young=young.reshape(-1),
        total=(young + older).reshape(-1),
        first_labels=frame.occ_code.to_numpy(object),
        second_labels=frame.month.to_numpy(object),
        regressors=np.asarray(regressors, float),
        regressor_labels=list(labels),
        focal_target_label="Q5_x_post",
    )


def original_treatment_functionals(labels: list[str]) -> dict[str, np.ndarray]:
    identity = np.eye(len(labels))
    return {
        f"original_treatment::{index}::{label}": identity[index]
        for index, label in enumerate(labels)
    }


def certify_model(NUM, bundle: Any, analysis: dict[str, Any], legacy_engine, candidate_fit) -> dict[str, Any]:
    target_functionals = original_treatment_functionals(bundle.regressor_labels)
    active, design, face, _ = NUM.resolve_extended_likelihood_face(bundle, analysis, target_functionals)
    require(design is not None and face.get("status") == "PASS_FINITE_FACE_RESOLVED", f"{bundle.model_id}: finite face not established")
    original_target = bundle.focal_target
    selected, basis = NUM.select_regressor_basis_preserving_focal(
        design.nuisance,
        bundle.regressors[active],
        bundle.total[active] * 0.25,
        original_target,
        face["geometric_information"],
    )
    require(selected == list(range(len(bundle.regressor_labels))), f"{bundle.model_id}: treatment basis changed")
    x = bundle.regressors[active][:, selected]
    design = NUM.replace_design_regressors(design, x)
    nuisance_count = design.nuisance.shape[1]
    target = selected.index(original_target)
    focal_column = nuisance_count + target
    objective = NUM.BinomialObjective(design.full, bundle.young[active], bundle.total[active])
    full_targets: dict[str, np.ndarray] = {}
    for index, label in enumerate(bundle.regressor_labels):
        vector = np.zeros(design.full.shape[1], float)
        vector[nuisance_count + index] = 1.0
        full_targets[label] = vector
    tolerances = analysis["tolerances"]
    profile = analysis["profile"]
    trust_raw = NUM.fit_exact_solver(
        objective, "trust-ncg", np.zeros(design.full.shape[1]),
        int(tolerances["optimizer_max_iterations"]),
        float(tolerances["gradient_infinity_norm_per_total"]),
        float(tolerances["standardized_score_absolute"]),
        focal_column, full_targets,
        float(tolerances["target_coefficient_absolute_difference"]),
        float(profile["likelihood_rise_tolerance_raw"]), False,
        float(tolerances["conditioning_rank_relative"]),
    )
    trust, polish = NUM.conditionally_polish_trust_candidate(
        objective, trust_raw,
        int(tolerances["optimizer_max_iterations"]),
        float(tolerances["gradient_infinity_norm_per_total"]),
        float(tolerances["standardized_score_absolute"]),
        focal_column, full_targets,
        float(tolerances["target_coefficient_absolute_difference"]),
        float(profile["likelihood_rise_tolerance_raw"]),
        float(tolerances["conditioning_rank_relative"]),
        float(tolerances["objective_difference_per_total"]),
        float(tolerances["fitted_probability_max_abs_difference"]),
    )
    reference_raw = NUM.fit_independent_sparse_newton(
        objective, np.zeros(design.full.shape[1]),
        int(tolerances["optimizer_max_iterations"]),
        float(tolerances["gradient_infinity_norm_per_total"]),
        float(tolerances["standardized_score_absolute"]),
        focal_column, full_targets,
        float(tolerances["target_coefficient_absolute_difference"]),
        float(profile["likelihood_rise_tolerance_raw"]),
        float(tolerances["conditioning_rank_relative"]),
        float(tolerances["objective_difference_per_total"]),
        float(tolerances["fitted_probability_max_abs_difference"]),
        "standalone_zero_reference",
    )
    reference = NUM.externally_certify_independent_output(
        objective, reference_raw, full_targets,
        float(tolerances["gradient_infinity_norm_per_total"]),
        float(tolerances["standardized_score_absolute"]),
        float(tolerances["target_coefficient_absolute_difference"]),
        float(profile["likelihood_rise_tolerance_raw"]),
        float(tolerances["conditioning_rank_relative"]),
        float(tolerances["objective_difference_per_total"]),
        float(tolerances["fitted_probability_max_abs_difference"]),
    )
    comparison = NUM.compare_trust_path_to_reference(
        objective, trust, reference, full_targets, tolerances,
        bundle.frame.loc[active, ["occ_code", "month"]].reset_index(drop=True).to_dict(orient="records"),
    )
    reference_beta = reference[1][nuisance_count:nuisance_count + len(bundle.regressor_labels)]
    candidate_beta = np.asarray(candidate_fit.beta, float)
    candidate_gap = float(np.max(np.abs(candidate_beta - reference_beta)))
    require(comparison["comparison_pass"] is True, f"{bundle.model_id}: trust/reference comparison failed")
    require(candidate_gap <= float(tolerances["target_coefficient_absolute_difference"]), f"{bundle.model_id}: scientific engine differs from independent reference")
    return {
        "model_id": bundle.model_id,
        "status": "PASS_SAME_OBJECTIVE_NUMERICAL_CERTIFICATION",
        "input_rows": len(bundle.frame),
        "active_rows": int(active.sum()),
        "profiled_boundary_rows": int(np.sum((bundle.total > 0) & ~active)),
        "treatment_labels": bundle.regressor_labels,
        "scientific_engine_treatment_coefficients": candidate_beta.tolist(),
        "independent_reference_treatment_coefficients": reference_beta.tolist(),
        "scientific_engine_reference_maximum_absolute_difference": candidate_gap,
        "trust_reference_treatment_maximum_absolute_difference": comparison["maximum_absolute_full_identified_treatment_vector_difference"],
        "trust_reference_fitted_probability_maximum_absolute_difference": comparison["fitted_probability_max_abs_difference"],
        "trust_reference_objective_difference_per_total": comparison["objective_difference_per_total"],
        "trust_numerically_valid": bool(trust[0]["numerically_valid"]),
        "reference_numerically_valid": bool(reference[0]["numerically_valid"]),
        "trust_polish_status": polish["status"],
        "face_status": face["status"],
        "treatment_basis_status": basis["status"],
    }


def direct_tail_outputs(schemes: dict[str, dict[str, Any]], names: dict[str, str], families: dict[str, str]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    family_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    for scheme_name, scheme in schemes.items():
        support = scheme["support"]
        groups = np.asarray(scheme["groups"], int)
        weights = np.asarray(scheme["weights"], float)
        family_values = [str(families.get(code, "UNMAPPED")) for code in support]
        total = float(weights.sum())
        for family in sorted(set(family_values)):
            mask = np.asarray([value == family for value in family_values])
            q1 = mask & (groups == 1)
            q5 = mask & (groups == 5)
            supported = bool(q1.any() and q5.any())
            family_rows.append({
                "scheme": scheme_name,
                "family": family,
                "family_occupation_count": int(mask.sum()),
                "family_preperiod_stock": float(weights[mask].sum()),
                "family_national_preperiod_stock_share": float(weights[mask].sum() / total),
                "q1_occupation_count": int(q1.sum()),
                "q5_occupation_count": int(q5.sum()),
                "q1_preperiod_stock": float(weights[q1].sum()),
                "q5_preperiod_stock": float(weights[q5].sum()),
                "direct_q5_q1_supported": supported,
                "q1_occupations": "|".join(f"{code}:{names.get(code, code)}" for code, keep in zip(support, q1) if keep),
                "q5_occupations": "|".join(f"{code}:{names.get(code, code)}" for code, keep in zip(support, q5) if keep),
            })
        rows = [row for row in family_rows if row["scheme"] == scheme_name]
        spanning = {row["family"] for row in rows if row["direct_q5_q1_supported"]}
        in_spanning = np.asarray([family in spanning for family in family_values])
        summary_rows.append({
            "scheme": scheme_name,
            "support_occupations": len(support),
            "support_hash_sha256": support_hash(support),
            "families": len(set(family_values)),
            "direct_tail_spanning_families": len(spanning),
            "direct_tail_spanning_family_list": "|".join(sorted(spanning)),
            "occupations_in_spanning_families": int(in_spanning.sum()),
            "preperiod_stock_share_in_spanning_families": float(weights[in_spanning].sum() / total),
            "q1_occupations": int(np.sum(groups == 1)),
            "q5_occupations": int(np.sum(groups == 5)),
            "q1_preperiod_stock_share": float(weights[groups == 1].sum() / total),
            "q5_preperiod_stock_share": float(weights[groups == 5].sum() / total),
        })
    return family_rows, summary_rows


def run(args: argparse.Namespace) -> None:
    require(not args.output_dir.exists(), "refusing to overwrite an existing output directory")
    args.output_dir.mkdir(parents=True)
    repo = args.repo_root.resolve()
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    require(spec["spec_id"] == spec_identity(spec), "broader-support spec identity mismatch")
    for record in spec["parent_records"].values():
        require(sha256(repo / record["path"]) == record["sha256"], "parent record hash mismatch")

    ARCH = load_module("yax_s05_arch", repo / "yax/revision/substantive_r3_20260905/architecture/run_architecture.py")
    BASE = load_module("yax_s05_base", repo / "yax/revision/substantive_r3_20260905/rebuilt_baseline/run_rebuilt_corrected_baseline.py")
    CELLS = load_module("yax_s05_cells", repo / "yax/revision/referee_20260905/run_referee_cells.py")
    FROZEN = load_module("yax_s05_frozen", repo / "yax/analysis/run_frozen_v11.py")
    NUM = load_module("yax_s05_numerical", repo / "yax/revision/substantive_v3_20260906/numerical_existence/run_numerical_existence_audit.py")
    analysis = json.loads((repo / spec["parent_records"]["numerical_amendment_spec"]["path"]).read_text(encoding="utf-8"))

    data = ARCH.reconstruct_and_validate(args, BASE, CELLS, FROZEN)
    primary = data["support"]
    require(len(primary) == PRIMARY_COUNT and support_hash(primary) == PRIMARY_HASH, "primary support moved")
    broad = ARCH.build_broader_beta_contract(data["cells"], data["exposures"]["dv_rating_beta"]["A"], data["names"], BASE)
    broad_support = list(broad["support"])
    require(set(primary).issubset(broad_support), "primary support is not nested in broader support")
    primary_cuts = np.asarray(data["rebuilt"]["cuts"], float)
    expected_cuts = np.asarray(spec["scientific_contract"]["primary_support"]["raw_beta_cuts"], float)
    require(np.allclose(primary_cuts, expected_cuts, rtol=0, atol=1e-14), "primary raw cut values moved")
    broad_fixed_groups = groups_from_fixed_cuts(broad["beta"], primary_cuts)
    broad_recomputed_groups = np.asarray(broad["quintiles"], int)
    primary_groups = np.asarray(data["rebuilt"]["quintiles"], int)
    broad_index = {code: index for index, code in enumerate(broad_support)}
    require(np.array_equal(primary_groups, broad_fixed_groups[[broad_index[code] for code in primary]]), "fixed-cut extension changed primary labels")

    broad_young, broad_older = CELLS.panel_for_ages(data["cells"], broad_support, data["months"], (22, 25), (26, 65))
    broad_signs = np.random.default_rng(SEED).choice(np.asarray([-1.0, 1.0]), size=(DRAWS, len(broad_support)))
    primary_signs = select_sign_columns(broad_signs, [broad_index[code] for code in primary])
    model_defs = [
        ("primary_with_webb", primary, data["young"], data["older"], primary_groups, {"Webb_software_z": np.asarray(data["rebuilt"]["webb_z"], float)}, primary_signs, primary_cuts),
        ("primary_without_webb", primary, data["young"], data["older"], primary_groups, {}, primary_signs, primary_cuts),
        ("broader_fixed_primary_cuts_without_webb", broad_support, broad_young, broad_older, broad_fixed_groups, {}, broad_signs, primary_cuts),
        ("broader_recomputed_cuts_without_webb", broad_support, broad_young, broad_older, broad_recomputed_groups, {}, broad_signs, np.asarray(broad["cuts"], float)),
    ]
    model_rows: list[dict[str, Any]] = []
    fitted: dict[str, dict[str, Any]] = {}
    numerical: list[dict[str, Any]] = []
    for model_id, support, young, older, groups, nuisance, signs, cuts in model_defs:
        columns, labels = ARCH.categorical_design(groups, data["months"], nuisance)
        fit, influence = ARCH.fit_design(FROZEN, young, older, columns)
        target = labels.index("Q5_x_post")
        summary, draws = inference(fit, influence, target, signs)
        matrix = np.column_stack([np.asarray(column, float).reshape(-1) for column in columns])
        bundle = build_bundle(NUM, model_id, support, data["months"], young, older, matrix, labels)
        audit = certify_model(NUM, bundle, analysis, FROZEN.ENGINE, fit)
        numerical.append(audit)
        row = {
            "model_id": model_id,
            "support_occupations": len(support),
            "support_hash_sha256": support_hash(support),
            "webb_included": bool(nuisance),
            "classification": "primary_fixed" if len(support) == PRIMARY_COUNT else ("broader_fixed_primary_raw_cuts" if model_id.startswith("broader_fixed") else "broader_recomputed_raw_cuts"),
            "raw_beta_cuts_json": json.dumps(np.asarray(cuts, float).tolist()),
            "q1_occupations": int(np.sum(groups == 1)),
            "q5_occupations": int(np.sum(groups == 5)),
            "q1_preperiod_stock_share": float(np.asarray((data["rebuilt"]["weights"] if len(support) == PRIMARY_COUNT else broad["weights"]), float)[groups == 1].sum() / np.asarray((data["rebuilt"]["weights"] if len(support) == PRIMARY_COUNT else broad["weights"]), float).sum()),
            "q5_preperiod_stock_share": float(np.asarray((data["rebuilt"]["weights"] if len(support) == PRIMARY_COUNT else broad["weights"]), float)[groups == 5].sum() / np.asarray((data["rebuilt"]["weights"] if len(support) == PRIMARY_COUNT else broad["weights"]), float).sum()),
            **summary,
        }
        model_rows.append(row)
        fitted[model_id] = {"summary": summary, "draws": draws, "groups": groups, "support": support}

    checkpoint = pd.read_csv(repo / spec["parent_records"]["original_architecture_results"]["path"]).set_index("model")
    checkpoint_map = {
        "primary_with_webb": "beta_with_Webb_fixed_468_support",
        "primary_without_webb": "beta_without_Webb_fixed_468_support",
        "broader_recomputed_cuts_without_webb": "beta_without_Webb_broader_beta_valid_support",
    }
    checkpoint_gaps = {
        model_id: float(fitted[model_id]["summary"]["coefficient"] - checkpoint.at[old_id, "coefficient"])
        for model_id, old_id in checkpoint_map.items()
    }
    require(max(abs(value) for value in checkpoint_gaps.values()) <= 1e-10, "historical S05 checkpoint did not reproduce")

    paired_rows = [
        paired("primary_without_webb", "primary_with_webb", fitted["primary_without_webb"]["summary"], fitted["primary_with_webb"]["summary"], fitted["primary_without_webb"]["draws"], fitted["primary_with_webb"]["draws"]),
        paired("broader_recomputed_cuts_without_webb", "broader_fixed_primary_cuts_without_webb", fitted["broader_recomputed_cuts_without_webb"]["summary"], fitted["broader_fixed_primary_cuts_without_webb"]["summary"], fitted["broader_recomputed_cuts_without_webb"]["draws"], fitted["broader_fixed_primary_cuts_without_webb"]["draws"]),
    ]
    additions = sorted(set(broad_support) - set(primary))
    weights = np.asarray(broad["weights"], float)
    beta = np.asarray(broad["beta"], float)
    membership_rows = []
    primary_set = set(primary)
    primary_map = {code: int(group) for code, group in zip(primary, primary_groups)}
    for index, code in enumerate(broad_support):
        membership_rows.append({
            "occupation_code": code,
            "occupation_name": data["names"].get(code, code),
            "family": str(data["groups"].get(code, "UNMAPPED")),
            "preperiod_stock": float(weights[index]),
            "preperiod_stock_share_of_broader": float(weights[index] / weights.sum()),
            "rule_A_beta": float(beta[index]),
            "in_primary_468": code in primary_set,
            "webb_available": bool(np.isfinite(data["computers"]["webb_pct_software"].get(code, np.nan))),
            "primary_quintile_if_present": primary_map.get(code, ""),
            "broader_fixed_primary_cuts_quintile": int(broad_fixed_groups[index]),
            "broader_recomputed_cuts_quintile": int(broad_recomputed_groups[index]),
            "reclassified_when_cuts_recomputed": bool(broad_fixed_groups[index] != broad_recomputed_groups[index]),
        })
    schemes = {
        "primary_fixed": {"support": primary, "groups": primary_groups, "weights": np.asarray(data["rebuilt"]["weights"], float)},
        "broader_fixed_primary_cuts": {"support": broad_support, "groups": broad_fixed_groups, "weights": weights},
        "broader_recomputed_cuts": {"support": broad_support, "groups": broad_recomputed_groups, "weights": weights},
    }
    family_rows, tail_summary = direct_tail_outputs(schemes, data["names"], data["groups"])
    support_change = {
        "primary_support_occupations": len(primary),
        "broader_support_occupations": len(broad_support),
        "additional_occupations": len(additions),
        "additional_occupation_codes": additions,
        "additional_preperiod_stock_share_of_broader": float(weights[[broad_index[code] for code in additions]].sum() / weights.sum()),
        "fixed_cut_support_expansion_coefficient_change": float(fitted["broader_fixed_primary_cuts_without_webb"]["summary"]["coefficient"] - fitted["primary_without_webb"]["summary"]["coefficient"]),
        "support_change_is_descriptive_not_paired_inference": True,
        "recomputed_cut_reclassification_coefficient_change": float(fitted["broader_recomputed_cuts_without_webb"]["summary"]["coefficient"] - fitted["broader_fixed_primary_cuts_without_webb"]["summary"]["coefficient"]),
        "reclassified_occupations": int(np.sum(broad_fixed_groups != broad_recomputed_groups)),
        "reclassified_preperiod_stock_share": float(weights[broad_fixed_groups != broad_recomputed_groups].sum() / weights.sum()),
        "historical_checkpoint_coefficient_gaps": checkpoint_gaps,
    }

    write_csv(args.output_dir / "MODEL_RESULTS.csv", model_rows)
    write_csv(args.output_dir / "SAME_SUPPORT_PAIRED_COMPARISONS.csv", paired_rows)
    write_json(args.output_dir / "SUPPORT_CHANGE_DECOMPOSITION.json", support_change)
    write_csv(args.output_dir / "BROADER_SUPPORT_MEMBERSHIP.csv", membership_rows)
    write_csv(args.output_dir / "DIRECT_TAIL_BY_FAMILY.csv", family_rows)
    write_csv(args.output_dir / "DIRECT_TAIL_SUMMARY.csv", tail_summary)
    write_json(args.output_dir / "NUMERICAL_AUDITS.json", {"models": numerical, "all_pass": all(row["status"].startswith("PASS_") for row in numerical)})

    model_map = {row["model_id"]: row for row in model_rows}
    tail_map = {row["scheme"]: row for row in tail_summary}
    summary = (
        "# S05 broader-beta support result\n\n"
        "Status: **post-outcome required revision; numerically validated**.\n\n"
        f"The strict beta-valid support contains {len(broad_support)} occupations, {len(additions)} more than the Webb-complete primary support, representing "
        f"{100 * support_change['additional_preperiod_stock_share_of_broader']:.2f}% of broader-support preperiod stock. On the primary support, removing Webb moves the Q5-Q1 estimate from "
        f"{model_map['primary_with_webb']['coefficient']:.6f} to {model_map['primary_without_webb']['coefficient']:.6f}. Extending the unchanged primary raw cutoffs to the broader support gives "
        f"{model_map['broader_fixed_primary_cuts_without_webb']['coefficient']:.6f}; recomputing cutoffs on that same broader support gives {model_map['broader_recomputed_cuts_without_webb']['coefficient']:.6f}.\n\n"
        f"Direct Q1-Q5 support spans {tail_map['primary_fixed']['direct_tail_spanning_families']} families under the primary rule, "
        f"{tail_map['broader_fixed_primary_cuts']['direct_tail_spanning_families']} after support expansion with fixed cuts, and "
        f"{tail_map['broader_recomputed_cuts']['direct_tail_spanning_families']} after broader-support reclassification. The primary-to-broader movement changes the estimation population and is therefore reported descriptively, not as equivalence evidence.\n"
    )
    (args.output_dir / "RESULT_SUMMARY.md").write_text(summary, encoding="utf-8")

    validation = {
        "status": "PASS_S05_BROADER_SUPPORT_VALIDATION",
        "checks": {
            "primary_support_exact": True,
            "primary_raw_cuts_exact": True,
            "primary_labels_unchanged_under_fixed_cut_extension": True,
            "primary_nested_in_broader": True,
            "all_four_models_numerically_certified": all(row["status"].startswith("PASS_") for row in numerical),
            "three_historical_coefficients_reproduced": max(abs(value) for value in checkpoint_gaps.values()) <= 1e-10,
            "fixed_cut_support_expansion_reported_before_reclassification": True,
            "direct_tail_support_compared_across_all_three_schemes": len(tail_summary) == 3,
            "support_changing_comparison_not_labeled_paired_or_equivalent": True,
        },
    }
    require(all(validation["checks"].values()), "S05 validation failed")
    write_json(args.output_dir / "VALIDATION_REPORT.json", validation)

    artifact_names = [name for name in spec["required_public_outputs"] if name not in {"RESULT_MANIFEST.json", "EXECUTION_RECEIPT.json"}]
    artifacts = {name: {"sha256": sha256(args.output_dir / name), "bytes": (args.output_dir / name).stat().st_size} for name in artifact_names}
    manifest_payload = {"schema_version": "yax-gate2-broader-support-result-manifest-v1", "spec_id": spec["spec_id"], "artifacts": artifacts}
    manifest_payload["result_id"] = content_id("yaxresult_v1", manifest_payload)
    write_json(args.output_dir / "RESULT_MANIFEST.json", manifest_payload)
    receipt = {
        "schema_version": "yax-gate2-broader-support-receipt-v1",
        "status": "PASS_S05_BROADER_SUPPORT_EXECUTION",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "git_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip(),
        "spec_id": spec["spec_id"],
        "spec_sha256": sha256(SPEC_PATH),
        "runner_sha256": sha256(pathlib.Path(__file__)),
        "input_hashes": data["input_hashes"],
        "primary_support_hash_sha256": support_hash(primary),
        "broader_support_hash_sha256": support_hash(broad_support),
        "result_id": manifest_payload["result_id"],
        "result_manifest_sha256": sha256(args.output_dir / "RESULT_MANIFEST.json"),
        "protected_cells_published": False,
        "row_microdata_published": False,
    }
    receipt["receipt_id"] = content_id("yaxreceipt_v1", receipt)
    write_json(args.output_dir / "EXECUTION_RECEIPT.json", receipt)
    print(json.dumps({"status": receipt["status"], "result_id": receipt["result_id"], "models": {row["model_id"]: row["coefficient"] for row in model_rows}}, indent=2, sort_keys=True))


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo-root", type=pathlib.Path, required=True)
    value.add_argument("--microdata", type=pathlib.Path, required=True)
    value.add_argument("--repair-microdata", type=pathlib.Path, required=True)
    value.add_argument("--lookup", type=pathlib.Path, required=True)
    value.add_argument("--computerization", type=pathlib.Path, required=True)
    value.add_argument("--rule-b-values", type=pathlib.Path, required=True)
    value.add_argument("--bridge", type=pathlib.Path, required=True)
    value.add_argument("--characteristics", type=pathlib.Path, required=True)
    value.add_argument("--baseline-membership", type=pathlib.Path, required=True)
    value.add_argument("--baseline-normalization", type=pathlib.Path, required=True)
    value.add_argument("--baseline-decomposition", type=pathlib.Path, required=True)
    value.add_argument("--output-dir", type=pathlib.Path, required=True)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
