#!/usr/bin/env python3
"""Run the authoritative YAX Gate 2 Y01--Y05 dynamic reconciliation on SCC.

Protected aggregate cells and full fitted designs remain inside SCC.  Only
coefficient, covariance, occupation-influence, inference, and validation
objects declared in the signed specification are eligible for publication.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import chi2, norm


SCHEMA = "yax-gate2-dynamic-core-spec-v1"
SPEC_PREFIX = "yaxgate2dyncore_v1"
RESULT_PREFIX = "yaxresult_v1"
ARTIFACT_PREFIX = "yaxartifact_v1"
RECEIPT_PREFIX = "yaxreceipt_v1"
RUN_ID_RE = re.compile(r"gate2_dynamic_core_sge_[1-9][0-9]*")
CORE_MODELS = (
    "pooled",
    "family_month",
    "dynamics_unconditioned",
    "dynamics_family_month",
)
STRUCTURES = {
    "unconditioned": ("pooled", "dynamics_unconditioned"),
    "family_month": ("family_month", "dynamics_family_month"),
}
COMPONENTS = ("Q2", "Q3", "Q4", "Q5", "Webb_z")
OUTPUT_FILENAMES = {
    "MODEL_CATALOG.json",
    "RECONCILIATION_ESTIMATES.csv",
    "RECONCILIATION_COVARIANCE.csv",
    "DYNAMIC_COEFFICIENTS.csv",
    "DYNAMIC_COVARIANCE.csv",
    "DYNAMIC_INFLUENCE.csv",
    "DYNAMIC_Q5_EVENT_STUDY.csv",
    "DYNAMIC_Q5_CENTERED_DRAWS.npz",
    "PRETREND_TESTS.csv",
    "PRETREND_DIAGNOSTICS.csv",
    "REPARAMETERIZATION_AUDIT.json",
    "NESTING_PROJECTION_AUDIT.json",
    "NUMERICAL_MODEL_AUDITS.json",
    "VALIDATION_REPORT.json",
}


class DynamicCoreError(RuntimeError):
    """A bound input, numerical certificate, or scientific check failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DynamicCoreError(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def array_sha256(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    payload = canonical_bytes({"dtype": array.dtype.str, "shape": list(array.shape)})
    return hashlib.sha256(payload + array.tobytes()).hexdigest()


def content_id(prefix: str, value: dict[str, Any], excluded: Iterable[str]) -> str:
    omitted = set(excluded)
    payload = {key: item for key, item in value.items() if key not in omitted}
    return f"{prefix}_{hashlib.sha256(canonical_bytes(payload)).hexdigest()}"


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DynamicCoreError(f"cannot read JSON object {path.name}: {error}") from error
    require(isinstance(value, dict), f"{path.name} is not a JSON object")
    return value


def import_module(name: str, path: Path):
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise DynamicCoreError(f"cannot import {path.name}")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return module


def validate_spec(spec: dict[str, Any], code_path: Path) -> None:
    require(spec.get("schema_version") == SCHEMA, "dynamic-core spec schema differs")
    require(spec.get("spec_id") == content_id(SPEC_PREFIX, spec, ("spec_id",)),
            "dynamic-core spec ID differs")
    require(spec.get("execution", {}).get("code_sha256") == sha256_file(code_path),
            "dynamic-core runner hash differs")
    require(tuple(spec.get("models", {}).get("core_model_ids", [])) == CORE_MODELS,
            "dynamic-core model inventory differs")
    require(set(spec.get("outputs", {}).get("artifact_filenames", [])) == OUTPUT_FILENAMES,
            "dynamic-core output inventory differs")
    require(spec.get("outputs", {}).get("protected_objects_must_not_be_published") is True,
            "protected-output prohibition differs")
    require(spec.get("requirements") == {
        "Y01": "AUTHORITATIVE_RUN_REQUIRED",
        "Y02": "AUTHORITATIVE_RUN_REQUIRED",
        "Y03": "AUTHORITATIVE_RUN_REQUIRED",
        "Y04": "AUTHORITATIVE_RUN_REQUIRED",
        "Y05": "AUTHORITATIVE_RUN_REQUIRED",
        "Y08": "OUT_OF_SCOPE_REQUIRES_16_ADDITIONAL_ONSET_MODELS",
        "T05": "OUT_OF_SCOPE_REQUIRES_2_ADDITIONAL_ENDPOINT_MODELS",
    }, "dynamic-core requirement scope differs")
    require(spec.get("functionals", {}).get("component_order") == list(COMPONENTS),
            "dynamic component order differs")
    require(spec.get("functionals", {}).get("transition_month") == "2022-12",
            "transition month differs")
    require(spec.get("functionals", {}).get("reference_quarter") == "2022Q4",
            "reference quarter differs")
    require(spec.get("inference", {}).get("cluster") == "occupation",
            "cluster definition differs")
    require(spec.get("inference", {}).get("draws") == 9999,
            "common-draw count differs")


def require_bound_file(path: Path, expected_hash: str, label: str) -> None:
    require(path.is_file() and not path.is_symlink(), f"{label} is absent or indirect")
    require(sha256_file(path) == expected_hash, f"{label} SHA-256 differs")


def input_hashes(args: argparse.Namespace, spec: dict[str, Any]) -> dict[str, str]:
    paths = {
        "support_spec": args.support_spec,
        "dynamic_parent_spec": args.dynamic_parent_spec,
        "dynamic_parent_runner": args.dynamic_parent_runner,
        "canonical_spec": args.canonical_spec,
        "a1_spec": args.a1_spec,
        "a1_runner": args.a1_runner,
        "a1_model_audit": args.a1_model_audit,
        "a1_dependency_release": args.a1_dependency_release,
        "cells": args.cells,
        "cells_receipt": args.cells_receipt,
        "fixed_membership": args.fixed_membership,
        "support_matrix": args.support_matrix,
        "support_edges": args.support_edges,
        "direct_tail_membership": args.direct_tail_membership,
        "support_result_manifest": args.support_result_manifest,
        "common_draw_binding": args.common_draw_binding,
        "common_multipliers": args.common_multipliers,
    }
    expected = spec.get("authenticated_inputs", {})
    require(set(paths) == set(expected), "dynamic-core authenticated input inventory differs")
    observed: dict[str, str] = {}
    for label, path in paths.items():
        expected_hash = expected[label].get("sha256")
        require(isinstance(expected_hash, str) and len(expected_hash) == 64,
                f"{label} expected hash is invalid")
        require_bound_file(path, expected_hash, label)
        observed[label] = expected_hash
    return observed


def check_core_release(audit: dict[str, Any], release: dict[str, Any]) -> None:
    indexed = {row.get("model_id"): row for row in audit.get("models", [])}
    target = release.get("target_dependencies", {})
    require(release.get("status") == "PASS", "A1 dependency release is not PASS")
    require(target.get("status") == "PASS_ALL_11_MODELS_CERTIFIED",
            "A1 dependency release does not certify all frozen models")
    require(target.get("blocked_model_ids") == [],
            "A1 dependency release retains blocked models")
    released = set(target.get("certified_model_ids", []))
    requirement_releases = target.get("downstream_requirement_releases", {})
    for requirement in ("Y01", "Y02", "Y03", "Y04"):
        row = requirement_releases.get(requirement, {})
        require(row.get("release_status") == "RELEASED",
                f"{requirement} numerical prerequisites are not released")
        require(set(row.get("required_model_ids", [])) == set(CORE_MODELS),
                f"{requirement} core model dependency set differs")
    for model_id in CORE_MODELS:
        row = indexed.get(model_id, {})
        require(model_id in released, f"{model_id} is not released")
        require(row.get("classification") == "PASS_FINITE_EXTENDED_MLE_TARGET",
                f"{model_id} finite-target classification differs")
        require(row.get("a1_certification", {}).get("status") ==
                "PASS_A1_NUMERICAL_CERTIFICATE", f"{model_id} lacks A1 certificate")


def load_common_draws(args: argparse.Namespace, cells: pd.DataFrame,
                      spec: dict[str, Any]) -> tuple[list[str], np.ndarray, dict[str, Any]]:
    manifest = load_json(args.support_result_manifest)
    records = {row.get("filename"): row for row in manifest.get("artifacts", [])}
    for filename, path in (
        ("COMMON_MULTIPLIERS.npz", args.common_multipliers),
        ("COMMON_DRAW_BINDING.json", args.common_draw_binding),
    ):
        record = records.get(filename, {})
        require(record.get("sha256") == sha256_file(path),
                f"support manifest does not bind {filename}")
    binding = load_json(args.common_draw_binding)
    archive = np.load(args.common_multipliers, allow_pickle=False)
    require(set(archive.files) == {"occupation_codes", "multipliers", "draw_id"},
            "common multiplier archive keys differ")
    occupations = archive["occupation_codes"].astype(str).tolist()
    xi = np.asarray(archive["multipliers"], float)
    expected_occupations = sorted(cells.occ_code.astype(str).unique())
    require(occupations == expected_occupations, "common-draw occupation order differs")
    require(xi.shape == (spec["inference"]["draws"], len(occupations)),
            "common multiplier dimensions differ")
    require(np.isin(xi, (-1.0, 1.0)).all(), "common multipliers are not Rademacher")
    require(binding.get("occupation_order_sha256") ==
            hashlib.sha256(canonical_bytes(occupations)).hexdigest(),
            "common-draw occupation identity differs")
    require(binding.get("multiplier_matrix_sha256") == array_sha256(xi),
            "common multiplier matrix identity differs")
    return occupations, xi, binding


def scaled_influence(fit) -> np.ndarray:
    count = fit.influence.shape[0]
    require(count > 1, "cluster count is too small")
    value = math.sqrt(count / (count - 1)) * np.asarray(fit.influence, float)
    require(np.allclose(value.T @ value, fit.covariance, rtol=1e-9, atol=1e-12),
            f"{fit.model_id} influence does not reproduce covariance")
    return value


@dataclass(frozen=True)
class LinearTarget:
    estimate: float
    influence: np.ndarray

    def __add__(self, other: "LinearTarget") -> "LinearTarget":
        return LinearTarget(self.estimate + other.estimate, self.influence + other.influence)

    def __sub__(self, other: "LinearTarget") -> "LinearTarget":
        return LinearTarget(self.estimate - other.estimate, self.influence - other.influence)


def target(fit, weights: np.ndarray) -> LinearTarget:
    weights = np.asarray(weights, float)
    require(weights.shape == (len(fit.labels),), f"{fit.model_id} target shape differs")
    return LinearTarget(
        float(weights @ fit.treatment),
        scaled_influence(fit) @ weights,
    )


def temporal_weights(parent_spec: dict[str, Any], dynamic) -> tuple[list[str], dict[str, float], dict[str, float]]:
    labels = dynamic.calendar_contract(parent_spec)["quarter_labels"]
    weights = dynamic.temporal_weights(parent_spec)
    return labels, weights["pre"], weights["post"]


def dynamic_functional(fit, component: str, weights: dict[str, float]) -> np.ndarray:
    result = np.zeros(len(fit.labels))
    for period, weight in weights.items():
        label = f"{component}_x_{period}"
        if label in fit.labels:
            result[fit.labels.index(label)] = float(weight)
        else:
            require(period == "2022Q4", f"dynamic coefficient is missing: {label}")
    return result


def build_reconciliation(fits: dict[str, Any], parent_spec: dict[str, Any], dynamic):
    _, pre, post = temporal_weights(parent_spec, dynamic)
    objects: dict[str, LinearTarget] = {}
    for structure, (static_id, dynamic_id) in STRUCTURES.items():
        static, event = fits[static_id], fits[dynamic_id]
        s = target(static, np.array([label == "Q5_x_post" for label in static.labels], float))
        p = target(event, dynamic_functional(event, "Q5", post))
        d = target(event, dynamic_functional(event, "Q5", {
            **post, **{period: -weight for period, weight in pre.items()}
        }))
        objects[f"{structure}::S"] = s
        objects[f"{structure}::P"] = p
        objects[f"{structure}::D"] = d
        objects[f"{structure}::P_minus_S"] = p - s
        objects[f"{structure}::D_minus_S"] = d - s
        objects[f"{structure}::P_minus_D"] = p - d
    for label in ("S", "P", "D", "P_minus_S", "D_minus_S", "P_minus_D"):
        objects[f"conditioning_family_month_minus_unconditioned::{label}"] = (
            objects[f"family_month::{label}"] - objects[f"unconditioned::{label}"]
        )
    labels = list(objects)
    rows = []
    for label in labels:
        item = objects[label]
        se = float(np.linalg.norm(item.influence))
        require(se > 0 and math.isfinite(se), f"nonpositive reconciliation SE: {label}")
        z = item.estimate / se
        rows.append({"target": label, "estimate": item.estimate, "standard_error": se,
                     "z": z, "p_value_normal": float(2 * norm.sf(abs(z))),
                     "cluster": "occupation", "cluster_count": len(item.influence)})
    covariance = np.vstack([objects[label].influence for label in labels])
    covariance = covariance @ covariance.T
    covariance_rows = [
        {"row_target": row, "column_target": column, "value": float(covariance[i, j])}
        for i, row in enumerate(labels) for j, column in enumerate(labels)
    ]
    return pd.DataFrame(rows), pd.DataFrame(covariance_rows), objects


def full_component(fit, component: str, quarter_labels: Sequence[str]):
    free_labels = [period for period in quarter_labels if period != "2022Q4"]
    positions = [fit.labels.index(f"{component}_x_{period}") for period in free_labels]
    beta = np.asarray(fit.treatment)[positions]
    influence = scaled_influence(fit)[:, positions]
    covariance = influence.T @ influence
    return free_labels, beta, covariance, influence


def rank_wald_with_inference(dynamic, beta: np.ndarray, covariance: np.ndarray,
                             influence: np.ndarray, restrictions: np.ndarray,
                             xi: np.ndarray, parent_spec: dict[str, Any]) -> dict[str, Any]:
    tol = parent_spec["tolerances"]
    result = dynamic.rank_aware_wald(
        beta, covariance, restrictions,
        relative_eigenvalue_tolerance=tol["conditioning_rank_relative"],
        target_range_relative_tolerance=tol["target_range_relative"],
    )
    target = restrictions @ beta
    restricted_covariance = restrictions @ covariance @ restrictions.T
    restricted_covariance = 0.5 * (restricted_covariance + restricted_covariance.T)
    eigenvalues, eigenvectors = np.linalg.eigh(restricted_covariance)
    cutoff = tol["conditioning_rank_relative"] * float(np.max(np.abs(eigenvalues)))
    retained = eigenvalues > cutoff
    vectors = eigenvectors[:, retained]
    values = eigenvalues[retained]
    draws = xi @ influence @ restrictions.T
    projected = draws @ vectors
    bootstrap_statistics = np.sum(np.square(projected) / values, axis=1)
    statistic = float(result["wald_statistic"])
    result["p_value_chi2"] = float(chi2.sf(statistic, result["degrees_of_freedom"]))
    result["p_value_multiplier"] = float(
        (1 + np.sum(bootstrap_statistics >= statistic)) / (len(bootstrap_statistics) + 1)
    )
    result["common_multiplier_draw_count"] = len(bootstrap_statistics)
    result["target_maximum_absolute"] = float(np.max(np.abs(target)))
    result["p_value"] = result["p_value_chi2"]
    result["inferential_procedure_required"] = False
    return result


def build_event_and_pretrend(fits: dict[str, Any], parent_spec: dict[str, Any],
                             dynamic, xi: np.ndarray):
    quarters, _, _ = temporal_weights(parent_spec, dynamic)
    pre_labels = [label for label in quarters if label < "2022Q4"]
    definitions = dynamic.build_y04_restrictions(pre_labels, parent_spec["pretrend"]["windows"])
    coefficient_rows: list[dict[str, Any]] = []
    covariance_rows: list[dict[str, Any]] = []
    influence_rows: list[dict[str, Any]] = []
    event_rows: list[dict[str, Any]] = []
    test_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    draw_output: list[tuple[str, np.ndarray]] = []
    q5_objects: dict[str, tuple[list[str], np.ndarray, np.ndarray, np.ndarray]] = {}

    for structure, (_, dynamic_id) in STRUCTURES.items():
        fit = fits[dynamic_id]
        scaled = scaled_influence(fit)
        for index, label in enumerate(fit.labels):
            coefficient_rows.append({"structure": structure, "model_id": dynamic_id,
                                     "coefficient_label": label,
                                     "estimate": float(fit.treatment[index])})
        for i, row_label in enumerate(fit.labels):
            for j, column_label in enumerate(fit.labels):
                covariance_rows.append({"structure": structure, "model_id": dynamic_id,
                                        "row_label": row_label, "column_label": column_label,
                                        "value": float(fit.covariance[i, j])})
        occupation_codes = sorted(fit.bundle.frame.loc[fit.active, "occ_code"].astype(str).unique())
        require(len(occupation_codes) == scaled.shape[0], "dynamic occupation order differs")
        for i, occupation in enumerate(occupation_codes):
            for j, label in enumerate(fit.labels):
                influence_rows.append({"structure": structure, "model_id": dynamic_id,
                                       "occupation_code": occupation,
                                       "coefficient_label": label,
                                       "scaled_influence": float(scaled[i, j])})

        free, beta, covariance, influence = full_component(fit, "Q5", quarters)
        q5_objects[structure] = (free, beta, covariance, influence)
        draws = xi @ influence
        draw_output.extend([
            (f"{structure}_labels", np.asarray(free)),
            (f"{structure}_centered_draws", draws),
        ])
        full_summary = dynamic.simultaneous_intervals(beta, influence, xi)
        pre_positions = [free.index(label) for label in pre_labels]
        pre_beta = beta[pre_positions]
        pre_covariance = covariance[np.ix_(pre_positions, pre_positions)]
        pre_influence = influence[:, pre_positions]
        pre_summary = dynamic.simultaneous_intervals(pre_beta, pre_influence, xi)
        for period in quarters:
            if period == "2022Q4":
                estimate = se = point_lower = point_upper = 0.0
                sim_lower = sim_upper = 0.0
                pre_sim_lower = pre_sim_upper = np.nan
            else:
                position = free.index(period)
                estimate = float(beta[position])
                se = float(math.sqrt(covariance[position, position]))
                point_lower = estimate - float(norm.ppf(.975)) * se
                point_upper = estimate + float(norm.ppf(.975)) * se
                sim_lower = float(full_summary["lower"][position])
                sim_upper = float(full_summary["upper"][position])
                if period in pre_labels:
                    pre_position = pre_labels.index(period)
                    pre_sim_lower = float(pre_summary["lower"][pre_position])
                    pre_sim_upper = float(pre_summary["upper"][pre_position])
                else:
                    pre_sim_lower = pre_sim_upper = np.nan
            event_rows.append({
                "structure": structure, "model_id": dynamic_id, "quarter": period,
                "reference_quarter": period == "2022Q4", "estimate": estimate,
                "standard_error": se, "pointwise_lower": point_lower,
                "pointwise_upper": point_upper, "simultaneous_full_lower": sim_lower,
                "simultaneous_full_upper": sim_upper,
                "simultaneous_full_critical": full_summary["critical"],
                "simultaneous_pre_lower": pre_sim_lower,
                "simultaneous_pre_upper": pre_sim_upper,
                "simultaneous_pre_critical": pre_summary["critical"],
            })

        for window_name, definition in definitions.items():
            for null_name, matrix_key in (
                ("equality_to_original_2022Q4_reference",
                 "equality_to_original_2022Q4_reference"),
                ("equality_within_selected_block", "equality_within_selected_block"),
            ):
                restrictions = definition[matrix_key]
                result = rank_wald_with_inference(
                    dynamic, pre_beta, pre_covariance, pre_influence,
                    restrictions, xi, parent_spec,
                )
                test_rows.append({
                    "structure": structure, "model_id": dynamic_id,
                    "window": window_name, "null": null_name,
                    "quarter_count": len(definition["quarters"]),
                    "restriction_rows": result["restriction_rows"],
                    "restriction_rank": result["restriction_matrix_rank"],
                    "covariance_rank": result["restricted_covariance_rank"],
                    "degrees_of_freedom": result["degrees_of_freedom"],
                    "wald_statistic": result["wald_statistic"],
                    "p_value_chi2": result["p_value_chi2"],
                    "p_value_multiplier": result["p_value_multiplier"],
                    "target_range_residual_relative": result["target_range_residual_relative"],
                    "status": "PASS_RANK_AWARE_WALD_WITH_COMMON_MULTIPLIERS",
                })

        full_selected = pre_labels
        for null_name, kind in (
            ("full_preperiod_equality_to_reference", "equality_to_reference"),
            ("full_preperiod_equality_within_block", "equality_within_block"),
        ):
            full_restriction = dynamic.restriction_matrix(pre_labels, full_selected, kind)
            full_result = rank_wald_with_inference(
                dynamic, pre_beta, pre_covariance, pre_influence,
                full_restriction, xi, parent_spec,
            )
            for omitted in full_selected:
                remaining = [label for label in full_selected if label != omitted]
                restriction = dynamic.restriction_matrix(pre_labels, remaining, kind)
                result = rank_wald_with_inference(
                    dynamic, pre_beta, pre_covariance, pre_influence,
                    restriction, xi, parent_spec,
                )
                diagnostic_rows.append({
                    "structure": structure, "model_id": dynamic_id,
                    "diagnostic": "leave_one_quarter_out", "contrast": null_name,
                    "omitted_quarter": omitted, "estimate": np.nan,
                    "standard_error": np.nan, "z": np.nan, "p_value_normal": np.nan,
                    "p_value_multiplier": result["p_value_multiplier"],
                    "wald_statistic": result["wald_statistic"],
                    "degrees_of_freedom": result["degrees_of_freedom"],
                    "full_wald_statistic": full_result["wald_statistic"],
                    "wald_change_not_additive_contribution":
                        result["wald_statistic"] - full_result["wald_statistic"],
                    "remaining_quarter_count": len(remaining),
                })

        definitions_y05 = dynamic.build_y05_diagnostic_definitions(pre_labels)
        contrasts = {
            "persistent_level": np.asarray(definitions_y05["persistent_level_contrast"], float),
            "equal_elapsed_quarter_linear_drift": np.asarray(
                definitions_y05["linear_drift_contrast_equal_elapsed_quarters"], float),
            **{name: np.asarray(value, float)
               for name, value in definitions_y05["seasonal_mean_contrasts"].items()},
        }
        for name, contrast in contrasts.items():
            estimate = float(contrast @ pre_beta)
            influence_value = pre_influence @ contrast
            se = float(np.linalg.norm(influence_value))
            z = estimate / se
            centered = xi @ influence_value
            p_multiplier = float((1 + np.sum(np.abs(centered / se) >= abs(z))) / (len(xi) + 1))
            diagnostic_rows.append({
                "structure": structure, "model_id": dynamic_id,
                "diagnostic": "linear_contrast", "contrast": name,
                "omitted_quarter": "", "estimate": estimate,
                "standard_error": se, "z": z,
                "p_value_normal": float(2 * norm.sf(abs(z))),
                "p_value_multiplier": p_multiplier, "wald_statistic": z * z,
                "degrees_of_freedom": 1, "full_wald_statistic": np.nan,
                "wald_change_not_additive_contribution": np.nan,
                "remaining_quarter_count": len(pre_labels),
            })

    return {
        "DYNAMIC_COEFFICIENTS.csv": pd.DataFrame(coefficient_rows),
        "DYNAMIC_COVARIANCE.csv": pd.DataFrame(covariance_rows),
        "DYNAMIC_INFLUENCE.csv": pd.DataFrame(influence_rows),
        "DYNAMIC_Q5_EVENT_STUDY.csv": pd.DataFrame(event_rows),
        "DYNAMIC_Q5_CENTERED_DRAWS.npz": tuple(draw_output),
        "PRETREND_TESTS.csv": pd.DataFrame(test_rows),
        "PRETREND_DIAGNOSTICS.csv": pd.DataFrame(diagnostic_rows),
    }, q5_objects, definitions


def build_reparameterization_audit(q5_objects: dict[str, Any], fits: dict[str, Any],
                                   parent_spec: dict[str, Any], dynamic,
                                   definitions: dict[str, Any]) -> dict[str, Any]:
    quarters, pre, post = temporal_weights(parent_spec, dynamic)
    old_reference = "2022Q4"
    free = [period for period in quarters if period != old_reference]
    d_weights = np.array([post.get(period, 0.0) - pre.get(period, 0.0) for period in free])
    maxima = {
        "target": 0.0, "covariance": 0.0, "influence": 0.0,
        "supplied_transform": 0.0,
    }
    checks = 0
    q5_restriction_checks = 0
    for structure, (_, dynamic_id) in STRUCTURES.items():
        fit = fits[dynamic_id]
        for component in COMPONENTS:
            component_free, beta, covariance, influence = full_component(fit, component, quarters)
            require(component_free == free, "component quarter ordering differs")
            for new_reference in quarters:
                result = dynamic.verify_equivalent_reference_rebase(
                    beta, d_weights[None, :], quarters, old_reference, new_reference,
                    covariance=covariance, influence=influence,
                    relative_tolerance=parent_spec["tolerances"]["reparameterization_relative"],
                    transform_absolute_tolerance=parent_spec["tolerances"][
                        "reference_rebase_transform_absolute"],
                )
                maxima["target"] = max(maxima["target"], result["maximum_relative_target_difference"])
                maxima["covariance"] = max(maxima["covariance"], result["maximum_relative_covariance_difference"])
                maxima["influence"] = max(maxima["influence"], result["maximum_relative_influence_difference"])
                maxima["supplied_transform"] = max(
                    maxima["supplied_transform"], result["maximum_absolute_supplied_transform_difference"])
                checks += 1

        _, q5_beta, q5_covariance, q5_influence = q5_objects[structure]
        old_index = {label: index for index, label in enumerate(free)}
        pre_labels = [label for label in quarters if label < old_reference]
        for definition in definitions.values():
            for key in ("equality_to_original_2022Q4_reference",
                        "equality_within_selected_block"):
                local = definition[key]
                embedded = np.zeros((local.shape[0], len(free)))
                for column, label in enumerate(pre_labels):
                    embedded[:, old_index[label]] = local[:, column]
                for new_reference in quarters:
                    result = dynamic.verify_equivalent_reference_rebase(
                        q5_beta, embedded, quarters, old_reference, new_reference,
                        covariance=q5_covariance, influence=q5_influence,
                        relative_tolerance=parent_spec["tolerances"]["reparameterization_relative"],
                        transform_absolute_tolerance=parent_spec["tolerances"][
                            "reference_rebase_transform_absolute"],
                    )
                    maxima["target"] = max(maxima["target"], result["maximum_relative_target_difference"])
                    maxima["covariance"] = max(maxima["covariance"], result["maximum_relative_covariance_difference"])
                    maxima["influence"] = max(maxima["influence"], result["maximum_relative_influence_difference"])
                    q5_restriction_checks += 1
    tolerance = parent_spec["tolerances"]["reparameterization_relative"]
    require(max(maxima["target"], maxima["covariance"], maxima["influence"]) <= tolerance,
            "reference reparameterization changed a target or uncertainty object")
    return {
        "status": "PASS_FULL_COEFFICIENT_COVARIANCE_INFLUENCE_REFERENCE_REPARAMETERIZATION",
        "structures": list(STRUCTURES), "components": list(COMPONENTS),
        "references_checked": len(quarters),
        "dynamic_functional_checks": checks,
        "q5_pretrend_restriction_checks": q5_restriction_checks,
        "maximum_relative_differences": maxima,
        "relative_tolerance": tolerance,
        "reference_rebase_transform_absolute_tolerance": parent_spec["tolerances"][
            "reference_rebase_transform_absolute"],
    }


def original_full_beta(fit) -> tuple[np.ndarray, float]:
    nuisance_columns = fit.design.nuisance.shape[1]
    beta = np.r_[fit.theta[:nuisance_columns], fit.treatment]
    eta = np.asarray(fit.design.full @ beta).reshape(-1)
    probability = np.empty_like(eta)
    nonnegative = eta >= 0
    probability[nonnegative] = 1.0 / (1.0 + np.exp(-eta[nonnegative]))
    exp_eta = np.exp(eta[~nonnegative])
    probability[~nonnegative] = exp_eta / (1.0 + exp_eta)
    difference = float(np.max(np.abs(probability - fit.probability)))
    require(difference <= 1e-10, f"{fit.model_id} original-coordinate probability differs")
    return beta, difference


def nesting_mapping_audit(static_fit, dynamic_fit) -> dict[str, Any]:
    static_keys = static_fit.bundle.frame.loc[static_fit.active, ["occ_code", "month"]].astype(str)
    dynamic_keys = dynamic_fit.bundle.frame.loc[dynamic_fit.active, ["occ_code", "month"]].astype(str)
    require(static_keys.reset_index(drop=True).equals(dynamic_keys.reset_index(drop=True)),
            "static and dynamic active rows differ")
    require(static_fit.design.nuisance_column_labels == dynamic_fit.design.nuisance_column_labels,
            "static and dynamic nuisance labels differ")
    nuisance_difference = static_fit.design.nuisance - dynamic_fit.design.nuisance
    nuisance_maximum = float(np.max(np.abs(nuisance_difference.data))) if nuisance_difference.nnz else 0.0
    require(nuisance_maximum == 0.0, "static and dynamic nuisance matrices differ")

    triples = [(index, index, 1.0)
               for index in range(static_fit.design.nuisance.shape[1])]
    treatment_residuals = []
    used_dynamic: set[int] = set()
    for static_index, static_label in enumerate(static_fit.labels):
        require(static_label.endswith("_x_post"), "unexpected static treatment label")
        component = static_label[:-len("_x_post")]
        positions = [
            index for index, label in enumerate(dynamic_fit.labels)
            if label.startswith(component + "_x_") and label.rsplit("_", 1)[1] >= "2023Q1"
        ]
        require(positions and not (used_dynamic & set(positions)),
                "predeclared treatment nesting map is incomplete or overlapping")
        used_dynamic |= set(positions)
        reconstructed = np.sum(dynamic_fit.bundle.regressors[dynamic_fit.active][:, positions], axis=1)
        observed = static_fit.bundle.regressors[static_fit.active][:, static_index]
        treatment_residuals.append(float(np.max(np.abs(observed - reconstructed))))
        for dynamic_index in positions:
            triples.append((dynamic_fit.design.nuisance.shape[1] + dynamic_index,
                            static_fit.design.nuisance.shape[1] + static_index, 1.0))
    maximum = max([nuisance_maximum, *treatment_residuals])
    require(maximum == 0.0, "exact predeclared Xs=XdA nesting failed")
    return {
        "status": "PASS_EXACT_PREDECLARED_SPARSE_DESIGN_NESTING",
        "active_rows": len(static_keys),
        "static_columns": static_fit.design.full.shape[1],
        "dynamic_columns": dynamic_fit.design.full.shape[1],
        "nuisance_columns": static_fit.design.nuisance.shape[1],
        "treatment_mapping_nonzeros": len(triples) - static_fit.design.nuisance.shape[1],
        "mapping_nonzeros": len(triples),
        "mapping_rule": "identity nuisance; each static post column is the sum of same-component post-quarter columns",
        "mapping_triplets_sha256": hashlib.sha256(canonical_bytes(triples)).hexdigest(),
        "maximum_absolute_residual": maximum,
    }


def pseudo_projection(a1, static_fit, dynamic_fit, analysis: dict[str, Any]) -> dict[str, Any]:
    static_beta, static_probability_difference = original_full_beta(static_fit)
    _, dynamic_probability_difference = original_full_beta(dynamic_fit)
    total = static_fit.bundle.total[static_fit.active]
    young = static_fit.bundle.young[static_fit.active]
    probability = dynamic_fit.probability
    design = static_fit.design.full
    residual = young - total * probability
    score = np.asarray(design.T @ residual).reshape(-1)
    scale = float(np.sum(total))
    score_per_total = float(np.max(np.abs(score))) / scale
    require(score_per_total <= analysis["tolerances"]["gradient_infinity_norm_per_total"],
            "nested static score moment failed")

    objective = a1.BinomialObjective(design, total * probability, total)
    nuisance = static_fit.design.nuisance.shape[1]
    targets = {}
    for index, label in enumerate(static_fit.labels):
        vector = np.zeros(design.shape[1]); vector[nuisance + index] = 1.0
        targets[label] = vector
    tol = analysis["tolerances"]
    raw = a1.fit_independent_sparse_newton(
        objective, static_beta, int(tol["optimizer_max_iterations"]),
        float(tol["gradient_infinity_norm_per_total"]),
        float(tol["standardized_score_absolute"]), nuisance + static_fit.labels.index("Q5_x_post"),
        targets, float(tol["target_coefficient_absolute_difference"]),
        float(analysis["profile"]["likelihood_rise_tolerance_raw"]),
        float(tol["conditioning_rank_relative"]),
        float(tol["objective_difference_per_total"]),
        float(tol["fitted_probability_max_abs_difference"]),
        "gate2_pseudo_projection_from_certified_static_start",
    )
    certified = a1.externally_certify_independent_output(
        objective, raw, targets,
        float(tol["gradient_infinity_norm_per_total"]),
        float(tol["standardized_score_absolute"]),
        float(tol["target_coefficient_absolute_difference"]),
        float(analysis["profile"]["likelihood_rise_tolerance_raw"]),
        float(tol["conditioning_rank_relative"]),
        float(tol["objective_difference_per_total"]),
        float(tol["fitted_probability_max_abs_difference"]),
    )
    diagnostics, projected_beta, projected_probability, trajectory = certified
    require(diagnostics.get("numerically_valid") is True,
            "pseudo-stock static projection failed its numerical certificate")
    target_difference = float(np.max(np.abs(
        projected_beta[nuisance:nuisance + len(static_fit.labels)] - static_fit.treatment
    )))
    fitted_difference = float(np.max(np.abs(
        projected_probability - static_fit.probability
    )))
    require(target_difference <= tol["target_coefficient_absolute_difference"],
            "pseudo-stock projection changed a static target")
    return {
        "status": "PASS_NESTED_DYNAMIC_SCORE_AND_PSEUDO_STOCK_STATIC_PROJECTION",
        "maximum_static_score_per_total_at_dynamic_probability": score_per_total,
        "maximum_absolute_static_target_projection_difference": target_difference,
        "maximum_absolute_projection_probability_difference_from_observed_static_fit": fitted_difference,
        "static_original_coordinate_probability_maximum_difference": static_probability_difference,
        "dynamic_original_coordinate_probability_maximum_difference": dynamic_probability_difference,
        "projection_iterations": diagnostics["iterations"],
        "projection_score_per_total": diagnostics["canonical_external_score"][
            "gradient_infinity_norm_per_total"],
        "projection_numerical_status": diagnostics["acceptance_source"],
        "trajectory_steps": len(trajectory),
    }


def build_nesting_audit(a1, fits: dict[str, Any], analysis: dict[str, Any]) -> dict[str, Any]:
    structures = {}
    for structure, (static_id, dynamic_id) in STRUCTURES.items():
        nesting = nesting_mapping_audit(fits[static_id], fits[dynamic_id])
        projection = pseudo_projection(a1, fits[static_id], fits[dynamic_id], analysis)
        structures[structure] = {"nesting": nesting, "score_and_projection": projection}
    return {
        "status": "PASS_BOTH_STRUCTURES_EXACT_NESTING_SCORE_AND_PROJECTION",
        "structures": structures,
        "nonclaim": "moment preservation and nonlinear projection check; not a causal estimator",
    }


def sanitized(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitized(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitized(item) for item in value]
    if isinstance(value, np.ndarray):
        return sanitized(value.tolist())
    if isinstance(value, np.generic):
        return sanitized(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def validate_outputs(outputs: dict[str, Any], fits: dict[str, Any]) -> dict[str, Any]:
    require(set(outputs) == OUTPUT_FILENAMES - {"VALIDATION_REPORT.json"},
            "dynamic-core in-memory output inventory differs")
    model_statuses = {
        model_id: fit.audit.get("a1_certification", {}).get("status")
        for model_id, fit in fits.items()
    }
    checks = {
        "all_four_models_a1_certified": all(
            value == "PASS_A1_NUMERICAL_CERTIFICATE" for value in model_statuses.values()),
        "reconciliation_18_targets": len(outputs["RECONCILIATION_ESTIMATES.csv"]) == 18,
        "reconciliation_covariance_complete": len(outputs["RECONCILIATION_COVARIANCE.csv"]) == 18 ** 2,
        "dynamic_coefficient_inventory": len(outputs["DYNAMIC_COEFFICIENTS.csv"]) == 2 * 190,
        "dynamic_covariance_inventory": len(outputs["DYNAMIC_COVARIANCE.csv"]) == 2 * 190 * 190,
        "dynamic_influence_inventory": len(outputs["DYNAMIC_INFLUENCE.csv"]) == 2 * 468 * 190,
        "event_study_inventory": len(outputs["DYNAMIC_Q5_EVENT_STUDY.csv"]) == 2 * 39,
        "pretrend_test_inventory": len(outputs["PRETREND_TESTS.csv"]) == 2 * 4 * 2,
        "pretrend_tests_all_pass": outputs["PRETREND_TESTS.csv"]["status"].eq(
            "PASS_RANK_AWARE_WALD_WITH_COMMON_MULTIPLIERS").all(),
        "reparameterization_pass": outputs["REPARAMETERIZATION_AUDIT.json"].get("status", "").startswith("PASS_"),
        "nesting_projection_pass": outputs["NESTING_PROJECTION_AUDIT.json"].get("status", "").startswith("PASS_"),
    }
    require(all(checks.values()), "dynamic-core output validation failed: " +
            ", ".join(sorted(key for key, value in checks.items() if not value)))
    return {
        "schema_version": "yax-gate2-dynamic-core-validation-v1",
        "status": "PASS_RECOMPUTED_DYNAMIC_CORE_VALIDATION",
        "checks": checks,
        "model_statuses": model_statuses,
        "failed_checks": [],
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(canonical_bytes(sanitized(value)) + b"\n")


def publish(outputs: dict[str, Any], output_parent: Path, run_id: str,
            spec: dict[str, Any], authenticated: dict[str, str], runtime: dict[str, Any]) -> Path:
    require(RUN_ID_RE.fullmatch(run_id) is not None, "run ID differs from declared SGE form")
    require(output_parent.is_dir() and not output_parent.is_symlink(), "output parent is invalid")
    destination = output_parent / run_id
    require(not destination.exists(), "refusing to overwrite a result leaf")
    staging = Path(tempfile.mkdtemp(prefix=f".{run_id}.staging.", dir=output_parent))
    try:
        for filename, value in outputs.items():
            path = staging / filename
            if isinstance(value, pd.DataFrame):
                value.to_csv(path, index=False)
            elif isinstance(value, dict):
                write_json(path, value)
            elif isinstance(value, tuple) and filename.endswith(".npz"):
                np.savez_compressed(path, **dict(value))
            else:
                raise DynamicCoreError(f"unsupported output object: {filename}")
        require({path.name for path in staging.iterdir()} == OUTPUT_FILENAMES,
                "staged artifact inventory differs")
        records = []
        for path in sorted(staging.iterdir()):
            record = {"filename": path.name, "logical_key": path.stem.lower(),
                      "byte_count": path.stat().st_size, "sha256": sha256_file(path)}
            record["result_id"] = content_id(ARTIFACT_PREFIX, record, ("result_id",))
            records.append(record)
        manifest = {
            "schema_version": "yax-gate2-dynamic-core-result-manifest-v1",
            "spec_id": spec["spec_id"], "run_id": run_id,
            "publication_kind": "CERTIFIED_DYNAMIC_CORE_Y01_Y05_RESULTS",
            "scientific_result_claims": True, "artifacts": records,
        }
        manifest["result_id"] = content_id(RESULT_PREFIX, manifest, ("result_id",))
        write_json(staging / "RESULT_MANIFEST.json", manifest)
        manifest_record = {
            "filename": "RESULT_MANIFEST.json", "logical_key": "result_manifest",
            "byte_count": (staging / "RESULT_MANIFEST.json").stat().st_size,
            "sha256": sha256_file(staging / "RESULT_MANIFEST.json"),
        }
        manifest_record["result_id"] = content_id(
            ARTIFACT_PREFIX, manifest_record, ("result_id",))
        git_head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[5],
            text=True, capture_output=True, check=True,
        ).stdout.strip()
        receipt = {
            "schema_version": "yax-gate2-dynamic-core-receipt-v1",
            "status": "CERTIFIED_DYNAMIC_CORE_Y01_Y05_PUBLICATION",
            "run_id": run_id, "sge_job_id": os.environ.get("JOB_ID"),
            "spec_id": spec["spec_id"], "executing_runner_sha256": sha256_file(Path(__file__)),
            "git_head": git_head, "authenticated_input_hashes": authenticated,
            "runtime": runtime, "artifact_count": len(records),
            "result_id": manifest["result_id"], "result_manifest": manifest_record,
            "scientific_result_claims": True,
            "protected_objects_published": False,
        }
        receipt["receipt_id"] = content_id(RECEIPT_PREFIX, receipt, ("receipt_id",))
        write_json(staging / "EXECUTION_RECEIPT.json", receipt)
        staging.rename(destination)
    except Exception:
        # Preserve a failed staging leaf for diagnosis; never publish it under run_id.
        raise
    return destination


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "spec", "support_spec", "dynamic_parent_spec", "dynamic_parent_runner",
        "canonical_spec", "a1_spec", "a1_runner", "a1_model_audit",
        "a1_dependency_release", "cells", "cells_receipt", "fixed_membership",
        "support_matrix", "support_edges", "direct_tail_membership",
        "support_result_manifest", "common_draw_binding", "common_multipliers",
        "output_parent",
    ):
        parser.add_argument("--" + name.replace("_", "-"), type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    spec = load_json(args.spec)
    validate_spec(spec, Path(__file__).resolve())
    authenticated = input_hashes(args, spec)
    support = import_module("yax_gate2_support", args.support_spec.parent / "run_support_inference.py")
    dynamic = import_module("yax_gate2_dynamic_math", args.dynamic_parent_runner)
    support_spec = load_json(args.support_spec)
    dynamic_parent_spec = load_json(args.dynamic_parent_spec)
    dynamic.validate_spec(dynamic_parent_spec, args.dynamic_parent_runner)

    # Reuse the already reviewed Gate 2 producer-side cell and support handshake.
    canonical, analysis, a1_audit, membership, cells, support_matrix, edges, direct = (
        support.authenticate(args, support_spec)
    )
    del canonical, membership, support_matrix, edges, direct
    release = load_json(args.a1_dependency_release)
    check_core_release(a1_audit, release)
    a1 = support.load_a1(args.a1_runner, analysis["software"]["artifact_safety_sha256"])
    runtime = support.verify_signed_a1_runtime_contract(a1, analysis)
    occupations, xi, draw_binding = load_common_draws(args, cells, spec)
    del draw_binding

    fits = {
        model_id: support.certified_fit(a1, a1.model_bundle(cells, model_id), analysis)
        for model_id in CORE_MODELS
    }
    for fit in fits.values():
        observed = sorted(fit.bundle.frame.loc[fit.active, "occ_code"].astype(str).unique())
        require(observed == occupations, f"{fit.model_id} occupation support differs")

    reconciliation, reconciliation_covariance, _ = build_reconciliation(
        fits, dynamic_parent_spec, dynamic)
    event_outputs, q5_objects, definitions = build_event_and_pretrend(
        fits, dynamic_parent_spec, dynamic, xi)
    reparameterization = build_reparameterization_audit(
        q5_objects, fits, dynamic_parent_spec, dynamic, definitions)
    nesting = build_nesting_audit(a1, fits, analysis)
    catalog = {
        "schema_version": "yax-gate2-dynamic-core-model-catalog-v1",
        "models": [{
            "model_id": model_id,
            "a1_certificate": fits[model_id].audit["a1_certification"]["status"],
            "reported_state_source": "trust-path",
            "coefficient_count": len(fits[model_id].labels),
            "active_rows": int(fits[model_id].active.sum()),
            "occupation_clusters": fits[model_id].influence.shape[0],
        } for model_id in CORE_MODELS],
    }
    numerical = {
        "schema_version": "yax-gate2-dynamic-core-fresh-a1-audits-v1",
        "models": [{"model_id": model_id,
                    "audit": support.sanitized_numerical_evidence(fits[model_id].audit)}
                   for model_id in CORE_MODELS],
    }
    outputs: dict[str, Any] = {
        "MODEL_CATALOG.json": catalog,
        "RECONCILIATION_ESTIMATES.csv": reconciliation,
        "RECONCILIATION_COVARIANCE.csv": reconciliation_covariance,
        **event_outputs,
        "REPARAMETERIZATION_AUDIT.json": reparameterization,
        "NESTING_PROJECTION_AUDIT.json": nesting,
        "NUMERICAL_MODEL_AUDITS.json": numerical,
    }
    outputs["VALIDATION_REPORT.json"] = validate_outputs(outputs, fits)
    destination = publish(outputs, args.output_parent, args.run_id, spec, authenticated, runtime)
    print(json.dumps({"status": "PASS", "run_id": args.run_id,
                      "output_leaf": destination.name}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DynamicCoreError as error:
        print(f"BLOCKED: {error}")
        raise SystemExit(2)
