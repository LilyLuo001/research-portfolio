#!/usr/bin/env python3
"""Pre-result Gate 2 static/dynamic reconciliation.

The module consumes only byte-bound Gate 1 certification artifacts.  It can
produce the point reconciliation that those artifacts support.  Covariance,
influence, design, score, and fitted-stock checks remain fail-closed until a
future immutable amendment binds those objects by hash.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import tempfile
from typing import Any, Iterable, Sequence

import numpy as np


SPEC_SCHEMA = "yax-gate2-dynamic-reconciliation-spec-v1"
SPEC_PREFIX = "yaxgate2dyn_v1_"
RECEIPT_SCHEMA = "yax-gate2-dynamic-reconciliation-receipt-v1"
CORE_MODELS = (
    "pooled",
    "family_month",
    "dynamics_unconditioned",
    "dynamics_family_month",
)
EVENT_COMPONENTS = ("Q2", "Q3", "Q4", "Q5", "Webb_z")
EXPECTED_SIGNED_BEHAVIOR_SHA256 = "f144dba560a6bbfd0b9a6eb6fa7bcfa7eddffd2ac5e6f56b91be903016779215"
REQUIREMENT_DISPOSITIONS = {
    "Y01": "IMPLEMENTED_POINT_ONLY; paired conditioning uncertainty blocked by missing cross-model influence/common draws",
    "Y02": "IMPLEMENTED_UNRUN; exact nesting, score, and pseudo-stock projection require missing bound design/fitted objects",
    "Y03": "IMPLEMENTED_COEFFICIENT_ONLY; covariance/influence/common-draw rebasing and numerical joint-Wald invariance are blocked by missing objects",
    "Y04": "IMPLEMENTED_DEFINITIONS_ONLY; numerical tests require covariance and inferential procedure objects",
    "Y05": "IMPLEMENTED_DEFINITIONS_ONLY; simultaneous and leave-block diagnostics require influence/common draws",
    "N04": "SIX A1 coding-stable/seasonality models are numerically certified; this does not supply onset-grid or endpoint fits",
    "Y08": "UNMET: requires 16 fresh onset fits (8 starts November 2022 through June 2023 times 2 structures) with same-objective numerical certification; the dependency map complete_onset label binds only six post-2020/seasonality fits and is insufficient",
    "T05": "UNMET: requires 2 through-December-2024 fits (pooled and family-month) with fixed preperiod labels and same-objective numerical certification",
}
EXPECTED_TOLERANCES = {
    "target_absolute": 1e-6,
    "fitted_probability_max_absolute": 1e-7,
    "objective_per_total_absolute": 1e-10,
    "conditioning_rank_relative": 1e-10,
    "target_range_relative": 1e-5,
    "coefficient_rebase_absolute": 1e-12,
    "design_nesting_relative": 1e-12,
}
EXPECTED_PRETREND_WINDOWS = {
    "full_preperiod": {
        "span": ["2017Q1", "2022Q3"],
        "excluded_quarters": [],
        "expected_quarter_count": 23,
    },
    "2017Q1_2019Q4": {
        "span": ["2017Q1", "2019Q4"],
        "excluded_quarters": [],
        "expected_quarter_count": 12,
    },
    "2021Q1_2022Q3": {
        "span": ["2021Q1", "2022Q3"],
        "excluded_quarters": [],
        "expected_quarter_count": 7,
    },
    "full_excluding_2020Q2_2020Q4": {
        "span": ["2017Q1", "2022Q3"],
        "excluded_quarters": ["2020Q2", "2020Q3", "2020Q4"],
        "expected_quarter_count": 20,
    },
}
EXPECTED_REPARAMETERIZATION = {
    "coefficient_rule": "beta_new = B beta_old over every quarter and all five interacted components",
    "covariance_rule": "V_new = B V_old B'",
    "influence_rule": "IF_new = IF_old B'",
    "restriction_rule": "R_new = R_old B^{-1}",
    "reference_rebase_ground_truth": (
        "B is the unique free_rebase_matrix(period_labels, old_reference, "
        "new_reference) derived independently from labels"
    ),
    "reference_rebase_transform_tolerance": "coefficient_rebase_absolute",
    "generic_linear_transform_scope": (
        "arbitrary invertible transforms may pass only generic linear equivalence "
        "and cannot certify a reference rebase"
    ),
    "common_draw_rule": (
        "transform the full occupation influence/common-draw vector, never a "
        "pointwise covariance submatrix"
    ),
    "available_now": "full certified dynamic coefficient vectors only",
    "unavailable_now": [
        "full covariance", "occupation influence", "common multiplier matrix"
    ],
}


class DynamicGateError(ValueError):
    """A signed input or declared mathematical invariant failed."""


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DynamicGateError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(
                stream,
                object_pairs_hook=_unique_pairs,
                parse_constant=lambda token: (_ for _ in ()).throw(
                    DynamicGateError(f"non-finite JSON constant: {token}")
                ),
            )
    except json.JSONDecodeError as exc:
        raise DynamicGateError(f"invalid JSON in {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise DynamicGateError(f"{path.name} must contain a JSON object")
    return value


def compute_spec_id(spec: dict[str, Any]) -> str:
    payload = dict(spec)
    payload.pop("spec_id", None)
    return SPEC_PREFIX + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def compute_result_id(spec_id: str, logical_key: str, artifact_sha256: str) -> str:
    payload = {
        "spec_id": spec_id,
        "logical_key": logical_key,
        "artifact_sha256": artifact_sha256,
    }
    return "yaxresult_v1_" + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def compute_signed_behavior_sha256(spec: dict[str, Any]) -> str:
    payload = json.loads(canonical_bytes(spec).decode("utf-8"))
    payload.pop("spec_id", None)
    execution = payload.get("execution")
    if isinstance(execution, dict):
        execution.pop("code_sha256", None)
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def month_range(start: str, end: str) -> list[str]:
    year, month = map(int, start.split("-"))
    end_year, end_month = map(int, end.split("-"))
    result: list[str] = []
    while (year, month) <= (end_year, end_month):
        result.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year += 1
            month = 1
    return result


def quarter(month: str) -> str:
    return f"{month[:4]}Q{(int(month[5:7]) - 1) // 3 + 1}"


def calendar_contract(spec: dict[str, Any]) -> dict[str, Any]:
    calendar = spec["calendar"]
    observed = [
        month for month in month_range(*calendar["observed_window"])
        if month not in set(calendar["missing_months"])
    ]
    pre = [
        month for month in observed
        if calendar["preperiod"][0] <= month <= calendar["preperiod"][1]
    ]
    post = [
        month for month in observed
        if calendar["postperiod"][0] <= month <= calendar["postperiod"][1]
    ]
    fit = [m for m in observed if m != calendar["transition_month"]]
    reference = [m for m in fit if quarter(m) == calendar["reference_quarter"]]
    expected = calendar["expected_month_counts"]
    actual = {
        "observed": len(observed), "fit": len(fit), "pre": len(pre),
        "post": len(post), "reference": len(reference),
    }
    if actual != expected:
        raise DynamicGateError(f"signed calendar counts differ: {actual}")
    if calendar["transition_month"] not in observed:
        raise DynamicGateError("transition month is not observed")
    if "2025-10" in observed:
        raise DynamicGateError("October 2025 must remain genuinely absent")
    if reference != ["2022-10", "2022-11"]:
        raise DynamicGateError("reference quarter must contain exactly Oct-Nov 2022")
    counts: dict[str, int] = {}
    for month in fit:
        counts[quarter(month)] = counts.get(quarter(month), 0) + 1
    labels = sorted(counts)
    if counts.get("2026Q3") != 1 or counts.get("2025Q4") != 2:
        raise DynamicGateError("partial-quarter month counts differ")
    return {
        "observed_months": observed, "fit_months": fit, "pre_months": pre,
        "post_months": post, "reference_months": reference,
        "quarter_labels": labels, "quarter_month_counts": counts,
    }


def temporal_weights(spec: dict[str, Any]) -> dict[str, dict[str, float]]:
    calendar = calendar_contract(spec)
    reference = spec["calendar"]["reference_quarter"]
    counts = calendar["quarter_month_counts"]
    pre_total = len(calendar["pre_months"])
    post_total = len(calendar["post_months"])
    pre = {
        label: counts[label] / pre_total
        for label in calendar["quarter_labels"] if label <= reference
    }
    post = {
        label: counts[label] / post_total
        for label in calendar["quarter_labels"] if label >= "2023Q1"
    }
    if not math.isclose(sum(pre.values()), 1.0, abs_tol=1e-15):
        raise DynamicGateError("pre weights do not sum to one")
    if not math.isclose(sum(post.values()), 1.0, abs_tol=1e-15):
        raise DynamicGateError("post weights do not sum to one")
    return {"pre": pre, "post": post}


def validate_requirement_dispositions(spec: dict[str, Any]) -> None:
    if spec.get("requirements") != REQUIREMENT_DISPOSITIONS:
        raise DynamicGateError("closed requirement dispositions changed")
    if not spec["requirements"]["Y08"].startswith("UNMET:"):
        raise DynamicGateError("Y08 must remain explicitly unmet")
    if not spec["requirements"]["T05"].startswith("UNMET:"):
        raise DynamicGateError("T05 must remain explicitly unmet")


def validate_spec(spec: dict[str, Any], code_path: Path) -> None:
    required = {
        "schema_version", "spec_id", "status", "canonical_contract",
        "authenticated_inputs", "calendar", "models", "functionals",
        "reparameterization", "nesting", "pretrend", "requirements",
        "tolerances", "execution", "outputs",
    }
    if set(spec) != required:
        raise DynamicGateError(
            f"spec keys differ: missing={sorted(required-set(spec))}, "
            f"extra={sorted(set(spec)-required)}"
        )
    if spec["schema_version"] != SPEC_SCHEMA:
        raise DynamicGateError("dynamic reconciliation spec schema differs")
    if spec["spec_id"] != compute_spec_id(spec):
        raise DynamicGateError("dynamic reconciliation spec_id mismatch")
    if spec["execution"]["code_sha256"] != sha256_file(code_path):
        raise DynamicGateError("runner byte hash differs from immutable spec")
    if tuple(spec["models"]["certified_core_model_ids"]) != CORE_MODELS:
        raise DynamicGateError("four-model core differs")
    calendar_contract(spec)
    weights = temporal_weights(spec)
    if set(weights["pre"]) != set(spec["functionals"]["pre_quarter_weights"]):
        raise DynamicGateError("frozen pre weight labels differ")
    if set(weights["post"]) != set(spec["functionals"]["post_quarter_weights"]):
        raise DynamicGateError("frozen post weight labels differ")
    for side in ("pre", "post"):
        declared = spec["functionals"][f"{side}_quarter_weights"]
        for label, value in weights[side].items():
            if not math.isclose(float(declared[label]), value, abs_tol=1e-15):
                raise DynamicGateError(f"frozen {side} weight differs for {label}")
    if spec["tolerances"] != EXPECTED_TOLERANCES:
        raise DynamicGateError("signed A1 and reconciliation tolerances changed")
    if not math.isclose(
        spec["tolerances"]["target_range_relative"],
        math.sqrt(spec["tolerances"]["conditioning_rank_relative"]),
        rel_tol=0.0,
        abs_tol=np.finfo(float).eps,
    ):
        raise DynamicGateError("signed target-range tolerance is not sqrt rank tolerance")
    if spec["functionals"].get("gaps") != ["P_minus_S", "D_minus_S", "P_minus_D"]:
        raise DynamicGateError("signed S/P/D gap definitions changed")
    if spec["reparameterization"] != EXPECTED_REPARAMETERIZATION:
        raise DynamicGateError("signed reparameterization semantics changed")
    nesting = spec["nesting"]
    if nesting.get("available_now") is not False:
        raise DynamicGateError("nesting availability flag must remain false")
    if nesting.get("predeclared_mapping_required") is not True:
        raise DynamicGateError("exact nesting must require a predeclared mapping")
    if nesting.get("target_tolerance") != spec["tolerances"]["target_absolute"]:
        raise DynamicGateError("nesting target tolerance differs from A1")
    if not isinstance(nesting.get("missing_objects"), list) or not nesting["missing_objects"]:
        raise DynamicGateError("nesting missing-object declaration is absent")
    pretrend = spec["pretrend"]
    if pretrend.get("windows") != EXPECTED_PRETREND_WINDOWS:
        raise DynamicGateError("signed pretrend windows changed")
    if pretrend.get("minimum_common_multiplier_draws") != 9999:
        raise DynamicGateError("minimum common multiplier draws changed")
    if pretrend.get("nulls_per_window") != [
        "all selected coefficients equal the original 2022Q4 reference",
        "all selected coefficients equal one another within the selected block",
    ]:
        raise DynamicGateError("pretrend null definitions changed")
    validate_requirement_dispositions(spec)
    execution = spec["execution"]
    if execution.get("mode") != "preflight point reconciliation only; no authoritative result claim":
        raise DynamicGateError("execution mode permits an undeclared operation")
    if execution.get("production_runtime_pin") != "UNAVAILABLE_REQUIRES_PREEXECUTION_BINDING":
        raise DynamicGateError("production runtime pin state changed")
    runtime = execution.get("runtime_requirements")
    if runtime != {"python": ">=3.10", "numpy": ">=1.22"}:
        raise DynamicGateError("runtime requirements changed")
    tested = execution.get("tested_runtime")
    if tested != {"python": "3.10.5", "numpy": "1.22.4"}:
        raise DynamicGateError("tested runtime record changed")
    outputs = spec["outputs"]
    if outputs.get("authoritative_output_forbidden_before_object_amendment") is not True:
        raise DynamicGateError("authoritative output guard changed")
    if outputs.get("never_imply_requirement_completion") is not True:
        raise DynamicGateError("requirement-completion output guard changed")
    if outputs.get("declared_preflight_file") != "DYNAMIC_PREFLIGHT_REPORT.json":
        raise DynamicGateError("declared preflight filename changed")
    if outputs.get("identity_rule") != (
        "any material output receives yaxresult_v1 SHA-256 identity over spec_id, "
        "logical key, and artifact hash"
    ):
        raise DynamicGateError("output result-identity rule changed")
    if compute_signed_behavior_sha256(spec) != EXPECTED_SIGNED_BEHAVIOR_SHA256:
        raise DynamicGateError("signed behavior contract differs from reviewed bytes")


def validate_input_hashes(paths: dict[str, Path], spec: dict[str, Any]) -> None:
    bindings = spec["authenticated_inputs"]
    if set(paths) != set(bindings):
        raise DynamicGateError("caller input roles differ from immutable bindings")
    for role, path in paths.items():
        expected = bindings[role]["sha256"]
        observed = sha256_file(path)
        if observed != expected:
            raise DynamicGateError(
                f"authenticated input hash mismatch for {role}: {observed}"
            )


def validate_release(release: dict[str, Any], spec: dict[str, Any]) -> None:
    target = release.get("target_dependencies")
    if release.get("status") != "PASS" or not isinstance(target, dict):
        raise DynamicGateError("dependency release lacks PASS target dependencies")
    if target.get("status") != "PASS_ALL_11_MODELS_CERTIFIED":
        raise DynamicGateError("dependency release does not certify all registered models")
    certified = target.get("certified_model_ids")
    if not isinstance(certified, list) or not set(CORE_MODELS).issubset(certified):
        raise DynamicGateError("dependency release omits a core model")
    if target.get("blocked_model_ids") != []:
        raise DynamicGateError("dependency release contains blocked models")
    map_binding = target.get("preoutcome_target_map_binding", {})
    expected_map = spec["authenticated_inputs"]["target_dependency_map"]["sha256"]
    if map_binding.get("target_dependency_map_sha256") != expected_map:
        raise DynamicGateError("dependency release target-map binding differs")
    releases = target.get("downstream_requirement_releases", {})
    for requirement in ("Y01", "Y02", "Y03", "Y04"):
        row = releases.get(requirement, {})
        if row.get("release_status") != "RELEASED":
            raise DynamicGateError(f"numerical prerequisites not released: {requirement}")
        if set(row.get("required_model_ids", [])) != set(CORE_MODELS):
            raise DynamicGateError(f"core prerequisite set differs: {requirement}")


def validate_contract_metadata(
    canonical_spec: dict[str, Any],
    a1_spec: dict[str, Any],
    target_map: dict[str, Any],
    focal_source_audit: dict[str, Any],
    model_audit: dict[str, Any],
    requirements_seed: dict[str, Any],
    spec: dict[str, Any],
) -> None:
    if canonical_spec.get("spec_id") != spec["canonical_contract"]["spec_id"]:
        raise DynamicGateError("canonical input spec_id differs")
    if a1_spec.get("audit_spec_id") != spec["models"]["a1_audit_spec_id"]:
        raise DynamicGateError("A1 input audit_spec_id differs")
    if a1_spec.get("canonical_spec_id") != spec["canonical_contract"]["spec_id"]:
        raise DynamicGateError("A1 input canonical_spec_id differs")
    certification = target_map.get("certification_contract", {})
    if certification.get("canonical_spec_id") != spec["canonical_contract"]["spec_id"]:
        raise DynamicGateError("target map canonical spec_id differs")
    if certification.get("required_a1_audit_spec_id") != spec["models"]["a1_audit_spec_id"]:
        raise DynamicGateError("target map A1 audit spec_id differs")
    if focal_source_audit.get("status") != (
        "PASS_REPORTED_FOCAL_TARGET_IS_REFERENCE_PATH_FOR_ALL_11_MODELS"
    ):
        raise DynamicGateError("focal-target source audit status differs")
    if focal_source_audit.get("source_model_audit", {}).get("sha256") != (
        spec["authenticated_inputs"]["model_audit"]["sha256"]
    ):
        raise DynamicGateError("focal-target source audit model hash differs")
    source_rows = focal_source_audit.get("models")
    if not isinstance(source_rows, list):
        raise DynamicGateError("focal-target source audit models are absent")
    source_index = {row.get("model_id"): row for row in source_rows if isinstance(row, dict)}
    model_index = {
        row.get("model_id"): row for row in model_audit.get("models", [])
        if isinstance(row, dict)
    }
    for model_id in CORE_MODELS:
        source = source_index.get(model_id, {})
        model = model_index.get(model_id, {})
        if source.get("reported_equals_reference") is not True:
            raise DynamicGateError(f"reported focal target source differs: {model_id}")
        if source.get("reported_value") != model.get("focal_target_estimate"):
            raise DynamicGateError(f"reported focal target value differs: {model_id}")
    rows = requirements_seed.get("requirements")
    if not isinstance(rows, list):
        raise DynamicGateError("requirements seed rows are absent")
    requirement_ids = {row.get("id") for row in rows if isinstance(row, dict)}
    expected_requirements = {"Y01", "Y02", "Y03", "Y04", "Y05", "N04", "Y08", "T05"}
    if not expected_requirements.issubset(requirement_ids):
        raise DynamicGateError("requirements seed omits a governed requirement")


def _model_index(model_audit: dict[str, Any], spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if model_audit.get("schema_version") != spec["authenticated_inputs"]["model_audit"]["expected_schema"]:
        raise DynamicGateError("model audit schema differs")
    if model_audit.get("status") != spec["authenticated_inputs"]["model_audit"]["expected_status"]:
        raise DynamicGateError("model audit status differs")
    if model_audit.get("canonical_spec_id") != spec["canonical_contract"]["spec_id"]:
        raise DynamicGateError("model audit canonical spec_id differs")
    if model_audit.get("audit_spec_id") != spec["models"]["a1_audit_spec_id"]:
        raise DynamicGateError("model audit A1 spec_id differs")
    if model_audit.get("cells_sha256") != spec["models"]["cells_sha256"]:
        raise DynamicGateError("model audit cells hash differs")
    models = model_audit.get("models")
    if not isinstance(models, list):
        raise DynamicGateError("model audit models are not a list")
    ids = [row.get("model_id") for row in models if isinstance(row, dict)]
    if len(ids) != len(models) or len(ids) != len(set(ids)):
        raise DynamicGateError("model audit has missing or duplicate model IDs")
    indexed = {row["model_id"]: row for row in models}
    for model_id in CORE_MODELS:
        row = indexed.get(model_id)
        if row is None:
            raise DynamicGateError(f"core model absent: {model_id}")
        if row.get("a1_certification", {}).get("status") != "PASS_A1_NUMERICAL_CERTIFICATE":
            raise DynamicGateError(f"core model lacks A1 certificate: {model_id}")
        if row.get("classification") != "PASS_FINITE_EXTENDED_MLE_TARGET":
            raise DynamicGateError(f"core model finite-target class differs: {model_id}")
        comparison = row.get("solver_comparison", {})
        if comparison.get("status") != "PASS_A1_TRUST_PATH_VS_ZERO_START_REFERENCE":
            raise DynamicGateError(f"core model same-objective comparison differs: {model_id}")
        if comparison.get("comparison_pass") is not True:
            raise DynamicGateError(f"core model comparison did not pass: {model_id}")
    return indexed


def _event_vector(model: dict[str, Any], quarter_labels: Sequence[str]) -> dict[str, np.ndarray]:
    values = model["solver_comparison"].get("reference_target_vector", {})
    parsed: dict[str, dict[str, float]] = {component: {} for component in EVENT_COMPONENTS}
    for key, value in values.items():
        if not key.startswith("original_treatment::"):
            continue
        label = key.split("::", 2)[-1]
        if "_x_" not in label:
            continue
        component, period = label.split("_x_", 1)
        if component in parsed:
            if period in parsed[component]:
                raise DynamicGateError(f"duplicate dynamic target label: {label}")
            parsed[component][period] = float(value)
    reference = "2022Q4"
    output: dict[str, np.ndarray] = {}
    expected_nonreference = set(quarter_labels) - {reference}
    for component in EVENT_COMPONENTS:
        if set(parsed[component]) != expected_nonreference:
            raise DynamicGateError(
                f"dynamic {component} quarter labels differ: "
                f"missing={sorted(expected_nonreference-set(parsed[component]))}, "
                f"extra={sorted(set(parsed[component])-expected_nonreference)}"
            )
        output[component] = np.array([
            0.0 if label == reference else parsed[component][label]
            for label in quarter_labels
        ], dtype=float)
    return output


def _weighted(vector: np.ndarray, labels: Sequence[str], weights: dict[str, float]) -> float:
    index = {label: position for position, label in enumerate(labels)}
    return float(sum(weight * vector[index[label]] for label, weight in weights.items()))


def build_point_reconciliation(model_audit: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    indexed = _model_index(model_audit, spec)
    calendar = calendar_contract(spec)
    labels = calendar["quarter_labels"]
    weights = temporal_weights(spec)
    structures = {
        "unconditioned": ("pooled", "dynamics_unconditioned"),
        "family_month": ("family_month", "dynamics_family_month"),
    }
    rows: dict[str, dict[str, float]] = {}
    vectors: dict[str, dict[str, np.ndarray]] = {}
    tolerance = float(spec["tolerances"]["target_absolute"])
    for structure, (static_id, dynamic_id) in structures.items():
        vectors[structure] = _event_vector(indexed[dynamic_id], labels)
        q5 = vectors[structure]["Q5"]
        static = float(indexed[static_id]["focal_target_estimate"])
        published = _weighted(q5, labels, weights["post"])
        pre_average = _weighted(q5, labels, weights["pre"])
        invariant = published - pre_average
        certified_published = float(indexed[dynamic_id]["focal_target_estimate"])
        if abs(published - certified_published) > tolerance:
            raise DynamicGateError(
                f"rebuilt published-reference functional differs for {dynamic_id}"
            )
        rows[structure] = {
            "S_static": static,
            "P_published_reference_post": published,
            "D_reference_invariant_post_minus_pre": invariant,
            "pre_average_relative_2022Q4": pre_average,
            "P_minus_S": published - static,
            "D_minus_S": invariant - static,
            "P_minus_D": published - invariant,
        }
    movement = {
        key: rows["family_month"][key] - rows["unconditioned"][key]
        for key in (
            "S_static", "P_published_reference_post",
            "D_reference_invariant_post_minus_pre", "P_minus_S", "D_minus_S",
        )
    }
    return {
        "status": "PASS_CERTIFIED_POINT_RECONCILIATION_ONLY",
        "quarter_labels": labels,
        "weights": weights,
        "structures": rows,
        "conditioning_movements_family_month_minus_unconditioned": movement,
        "event_vectors": vectors,
    }


def free_rebase_matrix(period_labels: Sequence[str], old_reference: str, new_reference: str) -> np.ndarray:
    labels = list(period_labels)
    if len(labels) != len(set(labels)) or old_reference not in labels or new_reference not in labels:
        raise DynamicGateError("invalid period labels or reference")
    old_free = [label for label in labels if label != old_reference]
    new_free = [label for label in labels if label != new_reference]
    old_index = {label: i for i, label in enumerate(old_free)}
    matrix = np.zeros((len(new_free), len(old_free)), dtype=float)
    for row, label in enumerate(new_free):
        if label != old_reference:
            matrix[row, old_index[label]] += 1.0
        if new_reference != old_reference:
            matrix[row, old_index[new_reference]] -= 1.0
    if np.linalg.matrix_rank(matrix) != len(old_free):
        raise DynamicGateError("rebasing matrix is not invertible")
    return matrix


def transform_parameterization(
    beta: np.ndarray,
    covariance: np.ndarray | None,
    influence: np.ndarray | None,
    transform: np.ndarray,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
    beta = np.asarray(beta, dtype=float)
    transform = np.asarray(transform, dtype=float)
    if transform.shape[1] != beta.shape[0]:
        raise DynamicGateError("coefficient transform shape differs")
    if not np.all(np.isfinite(beta)) or not np.all(np.isfinite(transform)):
        raise DynamicGateError("coefficient transform objects must be finite")
    transformed_beta = transform @ beta
    transformed_covariance = None
    transformed_influence = None
    if (covariance is None) != (influence is None):
        raise DynamicGateError("covariance and influence must be supplied together")
    if covariance is not None and influence is not None:
        covariance = np.asarray(covariance, dtype=float)
        influence = np.asarray(influence, dtype=float)
        if covariance.shape != (len(beta), len(beta)):
            raise DynamicGateError("covariance shape differs")
        if influence.ndim != 2 or influence.shape[1] != len(beta):
            raise DynamicGateError("influence shape differs")
        if not np.all(np.isfinite(covariance)) or not np.all(np.isfinite(influence)):
            raise DynamicGateError("covariance and influence must be finite")
        if not np.allclose(
            covariance, influence.T @ influence, rtol=1e-9, atol=1e-12,
        ):
            raise DynamicGateError("covariance is not reproduced by influence")
        transformed_covariance = transform @ covariance @ transform.T
        transformed_influence = influence @ transform.T
        if not np.allclose(
            transformed_covariance,
            transformed_influence.T @ transformed_influence,
            rtol=1e-9, atol=1e-12,
        ):
            raise DynamicGateError("transformed influence does not reproduce covariance")
    return transformed_beta, transformed_covariance, transformed_influence


def transform_restrictions(restrictions: np.ndarray, transform: np.ndarray) -> np.ndarray:
    """Map R beta=0 to R B^{-1} beta_new=0 when beta_new=B beta."""
    restrictions = np.asarray(restrictions, dtype=float)
    transform = np.asarray(transform, dtype=float)
    if transform.ndim != 2 or transform.shape[0] != transform.shape[1]:
        raise DynamicGateError("restriction transform is not square")
    if restrictions.ndim != 2 or restrictions.shape[1] != transform.shape[1]:
        raise DynamicGateError("restriction transform shape differs")
    if not np.all(np.isfinite(restrictions)) or not np.all(np.isfinite(transform)):
        raise DynamicGateError("restriction transform objects must be finite")
    try:
        inverse = np.linalg.inv(transform)
    except np.linalg.LinAlgError as exc:
        raise DynamicGateError("restriction transform is singular") from exc
    return restrictions @ inverse


def verify_equivalent_linear_reparameterization(
    beta: np.ndarray,
    restrictions: np.ndarray,
    transform: np.ndarray,
    covariance: np.ndarray | None = None,
    influence: np.ndarray | None = None,
    tolerance: float = 1e-12,
) -> dict[str, Any]:
    if not np.isfinite(tolerance) or tolerance < 0:
        raise DynamicGateError("linear-reparameterization tolerance is invalid")
    beta_new, covariance_new, influence_new = transform_parameterization(
        beta, covariance, influence, transform
    )
    restrictions = np.asarray(restrictions, dtype=float)
    restrictions_new = transform_restrictions(restrictions, transform)
    old_target = restrictions @ np.asarray(beta, dtype=float)
    new_target = restrictions_new @ beta_new
    maximum = float(np.max(np.abs(old_target - new_target))) if old_target.size else 0.0
    if maximum > tolerance:
        raise DynamicGateError("equivalent restriction target changed after linear reparameterization")
    covariance_difference = None
    influence_difference = None
    if covariance is not None and influence is not None:
        old_covariance = restrictions @ covariance @ restrictions.T
        new_covariance = restrictions_new @ covariance_new @ restrictions_new.T
        covariance_difference = float(np.max(np.abs(old_covariance - new_covariance)))
        old_influence = influence @ restrictions.T
        new_influence = influence_new @ restrictions_new.T
        influence_difference = float(np.max(np.abs(old_influence - new_influence)))
        if covariance_difference > tolerance or influence_difference > tolerance:
            raise DynamicGateError(
                "equivalent restriction uncertainty changed after linear reparameterization"
            )
    return {
        "status": "PASS_EQUIVALENT_GENERIC_LINEAR_REPARAMETERIZATION",
        "maximum_absolute_target_difference": maximum,
        "maximum_absolute_covariance_difference": covariance_difference,
        "maximum_absolute_influence_difference": influence_difference,
        "uncertainty_objects_checked": covariance is not None,
    }


def verify_equivalent_reference_rebase(
    beta: np.ndarray,
    restrictions: np.ndarray,
    period_labels: Sequence[str],
    old_reference: str,
    new_reference: str,
    transform: np.ndarray | None = None,
    covariance: np.ndarray | None = None,
    influence: np.ndarray | None = None,
    tolerance: float = 1e-12,
) -> dict[str, Any]:
    """Certify restriction equivalence under the unique label-defined rebase."""
    if not np.isfinite(tolerance) or tolerance < 0:
        raise DynamicGateError("reference-rebase tolerance is invalid")
    expected_transform = free_rebase_matrix(
        period_labels, old_reference, new_reference
    )
    transform_difference = 0.0
    if transform is not None:
        supplied_transform = np.asarray(transform, dtype=float)
        if supplied_transform.shape != expected_transform.shape:
            raise DynamicGateError(
                "supplied transform does not equal unique reference-rebase map"
            )
        if not np.all(np.isfinite(supplied_transform)):
            raise DynamicGateError(
                "supplied transform does not equal unique reference-rebase map"
            )
        transform_difference = float(
            np.max(np.abs(supplied_transform - expected_transform))
        )
        if transform_difference > tolerance:
            raise DynamicGateError(
                "supplied transform does not equal unique reference-rebase map"
            )
    result = verify_equivalent_linear_reparameterization(
        beta,
        restrictions,
        expected_transform,
        covariance,
        influence,
        tolerance,
    )
    return {
        **result,
        "status": "PASS_EQUIVALENT_REFERENCE_REBASE_RESTRICTIONS",
        "old_reference": old_reference,
        "new_reference": new_reference,
        "period_labels": list(period_labels),
        "maximum_absolute_supplied_transform_difference": transform_difference,
        "transform_used": "EXACT_LABEL_DERIVED_FREE_REBASE_MATRIX",
    }


def verify_reference_invariance(
    full_coefficients: np.ndarray,
    period_labels: Sequence[str],
    pre_weights: dict[str, float],
    post_weights: dict[str, float],
    tolerance: float = 1e-12,
) -> dict[str, Any]:
    coefficients = np.asarray(full_coefficients, dtype=float)
    labels = list(period_labels)
    if coefficients.shape != (len(labels),):
        raise DynamicGateError("full-series coefficient shape differs")
    if not np.all(np.isfinite(coefficients)):
        raise DynamicGateError("full-series coefficients must be finite")
    def functional(values: np.ndarray) -> float:
        return _weighted(values, labels, post_weights) - _weighted(values, labels, pre_weights)
    baseline = functional(coefficients)
    differences = {}
    for new_reference in labels:
        rebased = coefficients - coefficients[labels.index(new_reference)]
        differences[new_reference] = functional(rebased) - baseline
    maximum = max(abs(value) for value in differences.values())
    if not np.isfinite(tolerance) or tolerance < 0:
        raise DynamicGateError("reference-invariance tolerance is invalid")
    if maximum > tolerance:
        raise DynamicGateError("reference-invariant contrast changed after rebasing")
    return {
        "status": "PASS_COEFFICIENT_REFERENCE_INVARIANCE",
        "functional": baseline,
        "maximum_absolute_rebase_difference": maximum,
        "references_checked": len(labels),
    }


def validate_design_nesting(
    x_static: np.ndarray,
    x_dynamic: np.ndarray,
    mapping: np.ndarray | None = None,
    tolerance: float = 1e-12,
) -> dict[str, Any]:
    xs = np.asarray(x_static, dtype=float)
    xd = np.asarray(x_dynamic, dtype=float)
    if xs.ndim != 2 or xd.ndim != 2 or xs.shape[0] != xd.shape[0]:
        raise DynamicGateError("static and dynamic design row dimensions differ")
    if mapping is None:
        raise DynamicGateError("exact nesting requires a caller-supplied predeclared mapping")
    mapping = np.asarray(mapping, dtype=float)
    if mapping.shape != (xd.shape[1], xs.shape[1]):
        raise DynamicGateError("nesting map shape differs")
    if not all(np.all(np.isfinite(value)) for value in (xs, xd, mapping)):
        raise DynamicGateError("nesting objects must be finite")
    if not np.isfinite(tolerance) or tolerance < 0:
        raise DynamicGateError("nesting tolerance must be finite and nonnegative")
    residual = xs - xd @ mapping
    maximum_by_column = np.max(np.abs(residual), axis=0) if residual.size else np.zeros(xs.shape[1])
    scale_by_column = np.max(np.abs(xs), axis=0) if xs.size else np.zeros(xs.shape[1])
    relative_by_column = np.array([
        maximum / scale if scale > 0 else (0.0 if maximum == 0 else math.inf)
        for maximum, scale in zip(maximum_by_column, scale_by_column)
    ])
    maximum = float(np.max(maximum_by_column)) if maximum_by_column.size else 0.0
    maximum_relative = float(np.max(relative_by_column)) if relative_by_column.size else 0.0
    rank_static = int(np.linalg.matrix_rank(xs))
    rank_dynamic = int(np.linalg.matrix_rank(xd))
    passed = bool(np.all(relative_by_column <= tolerance))
    if not passed:
        raise DynamicGateError("exact Xs=XdA nesting failed")
    return {
        "status": "PASS_EXACT_DESIGN_NESTING",
        "maximum_absolute_residual": maximum,
        "relative_maximum_residual": maximum_relative,
        "column_maximum_absolute_residuals": maximum_by_column,
        "column_scales": scale_by_column,
        "column_relative_residuals": relative_by_column,
        "static_rank": rank_static,
        "dynamic_rank": rank_dynamic,
        "mapping_rank": int(np.linalg.matrix_rank(mapping)),
        "mapping": mapping,
    }


def validate_static_score_moment(
    x_static: np.ndarray,
    young: np.ndarray,
    total: np.ndarray,
    p_dynamic: np.ndarray,
    tolerance: float,
) -> dict[str, Any]:
    xs = np.asarray(x_static, dtype=float)
    y = np.asarray(young, dtype=float)
    total = np.asarray(total, dtype=float)
    probability = np.asarray(p_dynamic, dtype=float)
    if (
        xs.ndim != 2 or y.ndim != 1 or total.ndim != 1 or probability.ndim != 1
        or xs.shape[0] != len(y) or y.shape != total.shape
        or y.shape != probability.shape
    ):
        raise DynamicGateError("score-moment object shapes differ")
    if not all(np.all(np.isfinite(value)) for value in (xs, y, total, probability)):
        raise DynamicGateError("score-moment objects must be finite")
    if not np.isfinite(tolerance) or tolerance < 0:
        raise DynamicGateError("score-moment tolerance must be finite and nonnegative")
    if (
        np.any(total < 0) or np.any(y < 0) or np.any(y > total)
        or np.any((probability < 0) | (probability > 1))
    ):
        raise DynamicGateError("invalid young stock, total, or fitted probability")
    score = xs.T @ (y - total * probability)
    scale = max(1.0, float(np.sum(total)))
    maximum = float(np.max(np.abs(score))) if score.size else 0.0
    if maximum / scale > tolerance:
        raise DynamicGateError("static score moment is not preserved")
    return {
        "status": "PASS_STATIC_SCORE_MOMENT_PRESERVATION",
        "maximum_absolute_score": maximum,
        "maximum_score_per_total": maximum / scale,
    }


def _sigmoid(eta: np.ndarray) -> np.ndarray:
    result = np.empty_like(eta, dtype=float)
    positive = eta >= 0
    result[positive] = 1.0 / (1.0 + np.exp(-eta[positive]))
    exp_eta = np.exp(eta[~positive])
    result[~positive] = exp_eta / (1.0 + exp_eta)
    return result


def fit_grouped_logit_projection(
    design: np.ndarray,
    pseudo_young: np.ndarray,
    total: np.ndarray,
    start: np.ndarray | None = None,
    max_iterations: int = 200,
    score_tolerance: float = 1e-12,
) -> dict[str, Any]:
    x = np.asarray(design, dtype=float)
    y = np.asarray(pseudo_young, dtype=float)
    total = np.asarray(total, dtype=float)
    if (
        x.ndim != 2 or y.ndim != 1 or total.ndim != 1
        or len(y) != x.shape[0] or y.shape != total.shape
    ):
        raise DynamicGateError("projection input shapes differ")
    if not all(np.all(np.isfinite(value)) for value in (x, y, total)):
        raise DynamicGateError("projection inputs must be finite")
    if (
        not isinstance(max_iterations, int) or max_iterations <= 0
        or not np.isfinite(score_tolerance) or score_tolerance < 0
    ):
        raise DynamicGateError("projection iteration and score tolerances are invalid")
    if np.any(total <= 0) or np.any(y < 0) or np.any(y > total):
        raise DynamicGateError("projection requires positive totals and valid pseudo-stocks")
    if np.linalg.matrix_rank(x) != x.shape[1]:
        raise DynamicGateError("projection design is not full column rank")
    beta = np.zeros(x.shape[1]) if start is None else np.asarray(start, dtype=float).copy()
    if beta.shape != (x.shape[1],):
        raise DynamicGateError("projection start shape differs")
    if not np.all(np.isfinite(beta)):
        raise DynamicGateError("projection start must be finite")
    total_scale = max(1.0, float(np.sum(total)))
    for iteration in range(1, max_iterations + 1):
        eta = x @ beta
        if not np.all(np.isfinite(eta)):
            raise DynamicGateError("projection linear predictor is nonfinite")
        probability = _sigmoid(eta)
        score = x.T @ (y - total * probability)
        if not np.all(np.isfinite(score)):
            raise DynamicGateError("projection score is nonfinite")
        score_norm = float(np.max(np.abs(score))) / total_scale
        if score_norm <= score_tolerance:
            return {
                "status": "PASS_PSEUDO_STOCK_PROJECTION_CONVERGED",
                "beta": beta, "probability": probability,
                "iterations": iteration - 1, "score_per_total": score_norm,
            }
        information = x.T @ ((total * probability * (1.0 - probability))[:, None] * x)
        if not np.all(np.isfinite(information)):
            raise DynamicGateError("projection information is nonfinite")
        try:
            step = np.linalg.solve(information, score)
        except np.linalg.LinAlgError as exc:
            raise DynamicGateError("projection information is singular") from exc
        old_nll = float(np.sum(total * np.logaddexp(0.0, eta) - y * eta))
        accepted = False
        for power in range(40):
            candidate = beta + step / (2.0 ** power)
            candidate_eta = x @ candidate
            nll = float(np.sum(total * np.logaddexp(0.0, candidate_eta) - y * candidate_eta))
            if np.isfinite(nll) and nll <= old_nll + 1e-12:
                beta = candidate
                accepted = True
                break
        if not accepted:
            raise DynamicGateError("projection line search failed")
    raise DynamicGateError("pseudo-stock projection did not converge")


def validate_pseudo_stock_projection(
    x_static: np.ndarray,
    total: np.ndarray,
    p_dynamic: np.ndarray,
    certified_static_beta: np.ndarray,
    target_indices: Sequence[int],
    target_tolerance: float = 1e-6,
) -> dict[str, Any]:
    total = np.asarray(total, dtype=float)
    probability = np.asarray(p_dynamic, dtype=float)
    certified = np.asarray(certified_static_beta, dtype=float)
    if not all(np.all(np.isfinite(value)) for value in (total, probability, certified)):
        raise DynamicGateError("pseudo-stock projection objects must be finite")
    if not np.isfinite(target_tolerance) or target_tolerance < 0:
        raise DynamicGateError("projection target tolerance must be finite and nonnegative")
    pseudo_young = total * probability
    fit = fit_grouped_logit_projection(
        x_static, pseudo_young, total,
        start=certified,
    )
    targets = np.asarray(list(target_indices), dtype=int)
    if targets.ndim != 1 or targets.size == 0 or np.any(targets < 0) or np.any(targets >= len(certified)):
        raise DynamicGateError("projection target index differs")
    maximum = float(np.max(np.abs(fit["beta"][targets] - certified[targets])))
    if maximum > target_tolerance:
        raise DynamicGateError("pseudo-stock projection target differs from static target")
    return {
        "status": "PASS_PSEUDO_STOCK_STATIC_TARGET_PROJECTION",
        "maximum_absolute_target_difference": maximum,
        "iterations": fit["iterations"],
        "score_per_total": fit["score_per_total"],
    }


def restriction_matrix(
    all_labels: Sequence[str], selected_labels: Sequence[str], kind: str,
) -> np.ndarray:
    labels = list(all_labels)
    selected = list(selected_labels)
    if len(selected) != len(set(selected)) or not set(selected).issubset(labels):
        raise DynamicGateError("restriction labels are invalid")
    if not selected:
        raise DynamicGateError("restriction block is empty")
    index = {label: i for i, label in enumerate(labels)}
    if kind == "equality_to_reference":
        matrix = np.zeros((len(selected), len(labels)))
        for row, label in enumerate(selected):
            matrix[row, index[label]] = 1.0
    elif kind == "equality_within_block":
        if len(selected) < 2:
            return np.zeros((0, len(labels)))
        matrix = np.zeros((len(selected) - 1, len(labels)))
        anchor = index[selected[0]]
        for row, label in enumerate(selected[1:]):
            matrix[row, index[label]] = 1.0
            matrix[row, anchor] = -1.0
    else:
        raise DynamicGateError(f"unknown restriction kind: {kind}")
    return matrix


def build_y04_restrictions(
    pre_labels: Sequence[str], window_contract: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    labels = list(pre_labels)
    if window_contract != EXPECTED_PRETREND_WINDOWS:
        raise DynamicGateError("Y04 window contract differs from the frozen specification")
    result: dict[str, dict[str, Any]] = {}
    for name, contract in window_contract.items():
        start, end = contract["span"]
        excluded = set(contract["excluded_quarters"])
        selected = [
            label for label in labels if start <= label <= end and label not in excluded
        ]
        if not excluded.issubset({label for label in labels if start <= label <= end}):
            raise DynamicGateError(f"Y04 exclusion lies outside its span: {name}")
        if len(selected) != contract["expected_quarter_count"]:
            raise DynamicGateError(f"Y04 window count differs: {name}")
        reference = restriction_matrix(labels, selected, "equality_to_reference")
        within = restriction_matrix(labels, selected, "equality_within_block")
        result[name] = {
            "quarters": selected,
            "equality_to_original_2022Q4_reference": reference,
            "equality_within_selected_block": within,
            "reference_restrictions": reference.shape[0],
            "reference_matrix_rank": int(np.linalg.matrix_rank(reference)),
            "within_restrictions": within.shape[0],
            "within_matrix_rank": int(np.linalg.matrix_rank(within)),
        }
    return result


def rank_aware_wald(
    beta: np.ndarray,
    covariance: np.ndarray,
    restrictions: np.ndarray,
    relative_eigenvalue_tolerance: float = 1e-10,
    target_range_relative_tolerance: float = 1e-5,
) -> dict[str, Any]:
    beta = np.asarray(beta, dtype=float)
    covariance = np.asarray(covariance, dtype=float)
    restrictions = np.asarray(restrictions, dtype=float)
    if (
        beta.ndim != 1 or covariance.shape != (len(beta), len(beta))
        or restrictions.ndim != 2 or restrictions.shape[1] != len(beta)
    ):
        raise DynamicGateError("Wald object shapes differ")
    if not all(np.all(np.isfinite(value)) for value in (beta, covariance, restrictions)):
        raise DynamicGateError("Wald objects must be finite")
    if relative_eigenvalue_tolerance != EXPECTED_TOLERANCES["conditioning_rank_relative"]:
        raise DynamicGateError("Wald relative eigenvalue tolerance differs from signed value")
    if target_range_relative_tolerance != EXPECTED_TOLERANCES["target_range_relative"]:
        raise DynamicGateError("Wald target-range tolerance differs from signed value")
    if not math.isclose(
        target_range_relative_tolerance,
        math.sqrt(relative_eigenvalue_tolerance),
        rel_tol=0.0,
        abs_tol=np.finfo(float).eps,
    ):
        raise DynamicGateError("Wald target-range tolerance must equal sqrt eigenvalue tolerance")
    target = restrictions @ beta
    target_covariance = restrictions @ covariance @ restrictions.T
    if target_covariance.size == 0:
        raise DynamicGateError("Wald test has no restrictions")
    if not np.all(np.isfinite(target_covariance)):
        raise DynamicGateError("restricted covariance must be finite")
    entry_scale = float(np.max(np.abs(target_covariance)))
    symmetry_error = float(np.max(np.abs(target_covariance - target_covariance.T)))
    symmetry_cutoff = relative_eigenvalue_tolerance * entry_scale
    if symmetry_error > symmetry_cutoff:
        raise DynamicGateError("restricted covariance must be symmetric")
    symmetric_covariance = 0.5 * (target_covariance + target_covariance.T)
    # This is the sole spectral decomposition. Its scale-relative cutoff
    # controls the PSD check, retained inverse eigenvalues, rank, and df.
    eigenvalues, eigenvectors = np.linalg.eigh(symmetric_covariance)
    spectral_scale = float(np.max(np.abs(eigenvalues)))
    eigenvalue_cutoff = relative_eigenvalue_tolerance * spectral_scale
    minimum_eigenvalue = float(eigenvalues[0])
    if minimum_eigenvalue < -eigenvalue_cutoff:
        raise DynamicGateError("restricted covariance must be positive semidefinite")
    retained = eigenvalues > eigenvalue_cutoff
    rank = int(np.count_nonzero(retained))
    if rank == 0:
        raise DynamicGateError("restricted covariance has zero rank")
    retained_vectors = eigenvectors[:, retained]
    retained_eigenvalues = eigenvalues[retained]
    null_projection = eigenvectors[:, ~retained].T @ target
    null_component = eigenvectors[:, ~retained] @ null_projection
    null_projection_maximum = (
        float(np.max(np.abs(null_projection))) if null_projection.size else 0.0
    )
    null_component_l2 = float(np.linalg.norm(null_component))
    target_range_scale = max(
        float(np.linalg.norm(target)),
        math.sqrt(max(0.0, float(eigenvalues[-1]))),
        np.finfo(float).tiny,
    )
    target_range_residual_relative = null_component_l2 / target_range_scale
    if target_range_residual_relative > target_range_relative_tolerance:
        raise DynamicGateError(
            "BLOCKED_TARGET_OUTSIDE_ESTIMABLE_COVARIANCE_RANGE: "
            f"relative_null_residual={target_range_residual_relative:.17g}, "
            f"tolerance={target_range_relative_tolerance:.17g}"
        )
    projected_target = retained_vectors.T @ target
    statistic = float(np.sum(np.square(projected_target) / retained_eigenvalues))
    if not np.isfinite(statistic) or statistic < 0:
        raise DynamicGateError("Wald statistic is nonfinite or negative")
    statistic = max(0.0, statistic)
    return {
        "wald_statistic": statistic,
        "restriction_rows": int(restrictions.shape[0]),
        "restriction_matrix_rank": int(np.linalg.matrix_rank(restrictions)),
        "restricted_covariance_rank": rank,
        "degrees_of_freedom": rank,
        "rank_deficient": rank < restrictions.shape[0],
        "restricted_covariance_symmetry_error": symmetry_error,
        "restricted_covariance_symmetry_cutoff": symmetry_cutoff,
        "restricted_covariance_spectral_scale": spectral_scale,
        "restricted_covariance_eigenvalue_cutoff": eigenvalue_cutoff,
        "restricted_covariance_minimum_eigenvalue": minimum_eigenvalue,
        "restricted_covariance_maximum_eigenvalue": float(eigenvalues[-1]),
        "retained_eigenvalue_count": rank,
        "covariance_null_space_target_projection": null_projection.tolist(),
        "covariance_null_space_target_component": null_component.tolist(),
        "covariance_null_space_target_component_l2": null_component_l2,
        "null_space_target_projection_maximum_absolute": null_projection_maximum,
        "target_range_scale": target_range_scale,
        "target_range_residual_relative": target_range_residual_relative,
        "target_range_relative_tolerance": target_range_relative_tolerance,
        "target_in_estimable_covariance_range": True,
        "relative_eigenvalue_tolerance": relative_eigenvalue_tolerance,
        "single_eigendecomposition_used": True,
        "p_value": None,
        "inferential_procedure_required": True,
    }


def simultaneous_intervals(
    beta: np.ndarray, influence: np.ndarray, multiplier_signs: np.ndarray,
    alpha: float = 0.05,
) -> dict[str, Any]:
    beta = np.asarray(beta, dtype=float)
    influence = np.asarray(influence, dtype=float)
    signs = np.asarray(multiplier_signs, dtype=float)
    if influence.ndim != 2 or influence.shape[1] != len(beta):
        raise DynamicGateError("simultaneous influence shape differs")
    if signs.ndim != 2 or signs.shape[1] != influence.shape[0]:
        raise DynamicGateError("common multiplier matrix shape differs")
    if not all(np.all(np.isfinite(value)) for value in (beta, influence, signs)):
        raise DynamicGateError("simultaneous interval objects must be finite")
    if not np.isfinite(alpha) or not (0 < alpha < 1):
        raise DynamicGateError("simultaneous interval alpha is invalid")
    minimum_draws = 9999
    if signs.shape[0] < minimum_draws:
        raise DynamicGateError("too few common multiplier draws")
    if not np.isin(signs, (-1.0, 1.0)).all():
        raise DynamicGateError("multiplier matrix is not Rademacher")
    covariance = influence.T @ influence
    se = np.sqrt(np.maximum(np.diag(covariance), 0.0))
    if np.any(se <= 0):
        raise DynamicGateError("simultaneous interval has nonpositive SE")
    draws = signs @ influence
    maxima = np.max(np.abs(draws / se[None, :]), axis=1)
    quantile_index = int(math.ceil((len(maxima) - 1) * (1.0 - alpha)))
    critical = float(np.sort(maxima)[quantile_index])
    return {
        "critical": critical,
        "lower": beta - critical * se,
        "upper": beta + critical * se,
        "standard_errors": se,
        "draws": int(signs.shape[0]),
        "minimum_draws": minimum_draws,
        "achieved_quantile_order_statistic_index_zero_based": quantile_index,
        "achieved_empirical_coverage": (quantile_index + 1) / len(maxima),
        "common_draws_used": True,
    }


def leave_one_label_out_diagnostics(
    beta: np.ndarray,
    covariance: np.ndarray,
    all_labels: Sequence[str],
    selected_labels: Sequence[str],
    kind: str,
) -> list[dict[str, Any]]:
    labels = list(all_labels)
    selected = list(selected_labels)
    if len(labels) != len(beta) or len(labels) != len(set(labels)):
        raise DynamicGateError("leave-label-out coefficient labels differ")
    if len(selected) != len(set(selected)) or not set(selected).issubset(labels):
        raise DynamicGateError("leave-label-out selected labels differ")
    minimum = 3 if kind == "equality_within_block" else 2
    if len(selected) < minimum:
        raise DynamicGateError("leave-label-out null has too few selected labels")
    full_restrictions = restriction_matrix(labels, selected, kind)
    full = rank_aware_wald(beta, covariance, full_restrictions)
    rows = []
    for omitted_label in selected:
        remaining = [label for label in selected if label != omitted_label]
        rebuilt = restriction_matrix(labels, remaining, kind)
        result = rank_aware_wald(beta, covariance, rebuilt)
        rows.append({
            "omitted_label": omitted_label,
            "null_kind": kind,
            "remaining_labels": remaining,
            "full_anchor": selected[0] if kind == "equality_within_block" else None,
            "rebuilt_anchor": remaining[0] if kind == "equality_within_block" else None,
            "rebuilt_restriction_matrix": rebuilt,
            "rebuilt_restriction_rows": int(rebuilt.shape[0]),
            "full_wald": full["wald_statistic"],
            "leave_label_out_wald": result["wald_statistic"],
            "descriptive_wald_change_not_additive_contribution": (
                result["wald_statistic"] - full["wald_statistic"]
            ),
            "degrees_of_freedom": result["degrees_of_freedom"],
        })
    return rows


def build_y05_diagnostic_definitions(pre_labels: Sequence[str]) -> dict[str, Any]:
    labels = list(pre_labels)
    if len(labels) != 23:
        raise DynamicGateError("Y05 diagnostics require all 23 pre quarters")
    times = np.arange(len(labels), dtype=float)
    centered = times - times.mean()
    drift = centered / float(centered @ centered)
    level = np.repeat(1.0 / len(labels), len(labels))
    seasonal: dict[str, list[float]] = {}
    for q in (2, 3, 4):
        q1 = np.array([label.endswith("Q1") for label in labels], dtype=float)
        target = np.array([label.endswith(f"Q{q}") for label in labels], dtype=float)
        contrast = target / target.sum() - q1 / q1.sum()
        seasonal[f"Q{q}_minus_Q1_mean"] = contrast.tolist()
    return {
        "simultaneous_intervals": (
            "maximum absolute studentized common-draw statistic over the frozen grid"
        ),
        "leave_one_quarter_out": (
            "rebuild the declared null on the remaining quarter labels after omitting each quarter, "
            "including selection of a new within-block anchor when the old anchor is omitted; "
            "the Wald change is descriptive and is not an additive contribution"
        ),
        "persistent_level_contrast": level.tolist(),
        "linear_drift_contrast_equal_elapsed_quarters": drift.tolist(),
        "seasonal_mean_contrasts": seasonal,
        "pandemic_attribution_rule": (
            "dates alone never establish that COVID drives rejection"
        ),
        "selection_rule": "retain full grid; do not choose a window from viewed p-values",
    }


def preflight_report(
    model_audit: dict[str, Any], dependency_release: dict[str, Any], spec: dict[str, Any],
) -> dict[str, Any]:
    validate_requirement_dispositions(spec)
    validate_release(dependency_release, spec)
    reconciliation = build_point_reconciliation(model_audit, spec)
    weights = reconciliation["weights"]
    invariance = {}
    event_vectors = reconciliation.pop("event_vectors")
    for structure, vectors in event_vectors.items():
        invariance[structure] = {}
        for component, vector in vectors.items():
            invariance[structure][component] = verify_reference_invariance(
                vector, reconciliation["quarter_labels"], weights["pre"], weights["post"],
                tolerance=spec["tolerances"]["coefficient_rebase_absolute"],
            )
    pre_labels = [label for label in reconciliation["quarter_labels"] if label < "2022Q4"]
    y04 = build_y04_restrictions(pre_labels, spec["pretrend"]["windows"])
    restriction_reparameterization: dict[str, Any] = {}
    all_labels = reconciliation["quarter_labels"]
    old_reference = spec["calendar"]["reference_quarter"]
    old_free = [label for label in all_labels if label != old_reference]
    old_free_index = {label: index for index, label in enumerate(old_free)}
    for structure, vectors in event_vectors.items():
        beta = np.array([
            vectors["Q5"][all_labels.index(label)] for label in old_free
        ])
        maximum = 0.0
        checks = 0
        for window in y04.values():
            for kind in (
                "equality_to_original_2022Q4_reference",
                "equality_within_selected_block",
            ):
                local = window[kind]
                embedded = np.zeros((local.shape[0], len(old_free)))
                for column, label in enumerate(pre_labels):
                    embedded[:, old_free_index[label]] = local[:, column]
                for new_reference in all_labels:
                    check = verify_equivalent_reference_rebase(
                        beta,
                        embedded,
                        all_labels,
                        old_reference,
                        new_reference,
                        tolerance=spec["tolerances"]["coefficient_rebase_absolute"],
                    )
                    maximum = max(maximum, check["maximum_absolute_target_difference"])
                    checks += 1
        restriction_reparameterization[structure] = {
            "status": "PASS_ALL_Y04_RESTRICTION_TARGETS_REPARAMETERIZED",
            "checks": checks,
            "maximum_absolute_target_difference": maximum,
            "covariance_influence_checks": "BLOCKED_MISSING_OBJECTS",
        }
    y04_serializable = {
        window: {
            **{key: value for key, value in row.items() if not isinstance(value, np.ndarray)},
            "equality_to_original_2022Q4_reference": row[
                "equality_to_original_2022Q4_reference"
            ].tolist(),
            "equality_within_selected_block": row[
                "equality_within_selected_block"
            ].tolist(),
        }
        for window, row in y04.items()
    }
    return {
        "schema_version": RECEIPT_SCHEMA,
        "analysis_status": "PRE_RESULT_IMPLEMENTATION_NONAUTHORITATIVE",
        "spec_id": spec["spec_id"],
        "point_reconciliation": reconciliation,
        "coefficient_reparameterization": invariance,
        "restriction_reparameterization": restriction_reparameterization,
        "y04_restriction_definitions": y04_serializable,
        "y05_diagnostic_definitions": build_y05_diagnostic_definitions(pre_labels),
        "object_availability": {
            "certified_full_dynamic_coefficients": "AVAILABLE_IN_BOUND_MODEL_AUDIT",
            "full_covariance": "MISSING_NOT_FABRICATED",
            "occupation_influence": "MISSING_NOT_FABRICATED",
            "common_multiplier_matrix": "MISSING_NOT_FABRICATED",
            "full_static_and_dynamic_designs": "MISSING_NOT_FABRICATED",
            "dynamic_fitted_probabilities": "MISSING_NOT_FABRICATED",
            "static_full_parameter_vector": "MISSING_NOT_FABRICATED",
            "authenticated_aggregate_cells": "HASH_BOUND_BUT_BYTES_NOT_IN_PUBLIC_RELEASE",
            "upstream_model_result_ids": "MISSING_NOT_FABRICATED; TARGETS_ARE_BOUND_BY_AUDIT_HASH_AND_MODEL_ID",
        },
        "requirement_disposition": dict(REQUIREMENT_DISPOSITIONS),
        "authoritative_completion": False,
    }


def validate_output_path(output: Path, spec: dict[str, Any]) -> str:
    declared = spec["outputs"]["declared_preflight_file"]
    if output.name != declared:
        raise DynamicGateError("output basename differs from declared preflight file")
    if output.exists():
        raise DynamicGateError("refusing to overwrite an existing output")
    return declared


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--dependency-release", type=Path, required=True)
    parser.add_argument("--model-audit", type=Path, required=True)
    parser.add_argument("--a1-spec", type=Path, required=True)
    parser.add_argument("--canonical-spec", type=Path, required=True)
    parser.add_argument("--target-dependency-map", type=Path, required=True)
    parser.add_argument("--focal-target-source-audit", type=Path, required=True)
    parser.add_argument("--execution-prompt", type=Path, required=True)
    parser.add_argument("--requirements-seed", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    spec = load_json(args.spec)
    validate_spec(spec, Path(__file__).resolve())
    paths = {
        "dependency_release": args.dependency_release,
        "model_audit": args.model_audit,
        "a1_spec": args.a1_spec,
        "canonical_spec": args.canonical_spec,
        "target_dependency_map": args.target_dependency_map,
        "focal_target_source_audit": args.focal_target_source_audit,
        "execution_prompt": args.execution_prompt,
        "requirements_seed": args.requirements_seed,
    }
    validate_input_hashes(paths, spec)
    model_audit = load_json(args.model_audit)
    dependency_release = load_json(args.dependency_release)
    requirements_seed = load_json(args.requirements_seed)
    validate_contract_metadata(
        load_json(args.canonical_spec), load_json(args.a1_spec),
        load_json(args.target_dependency_map), load_json(args.focal_target_source_audit),
        model_audit, requirements_seed, spec,
    )
    report = preflight_report(
        model_audit, dependency_release, spec,
    )
    if args.output is None:
        print(json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return 0
    logical_name = validate_output_path(args.output, spec)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(report) + b"\n"
    with tempfile.NamedTemporaryFile("wb", dir=args.output.parent, delete=False) as stream:
        stream.write(payload)
        temporary = Path(stream.name)
    temporary.replace(args.output)
    digest = sha256_file(args.output)
    result_id = compute_result_id(spec["spec_id"], logical_name, digest)
    print(json.dumps({"path": str(args.output), "sha256": digest, "result_id": result_id}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
