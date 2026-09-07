#!/usr/bin/env python3
"""Validate YAX V3 run dependencies and cache fingerprints.

A successful cached run is usable only when its specification, code,
environment, command, upstream result IDs, upstream artifact hashes, and output
hashes match the manifest.  Failed branches remain recorded and block only
their descendants.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

from spec_contract import SPEC_PREFIX, canonical_bytes, sha256_file


SHA256 = re.compile(r"^[0-9a-f]{64}$")
RUN_STATUSES = {"PLANNED", "RUNNING", "SUCCESS", "FAILED", "BLOCKED"}
TARGET_MAP_SCHEMA = "yax-target-dependency-map-v1"
NUMERICAL_AUDIT_SCHEMA = "yax-numerical-existence-audit-v1"
NUMERICAL_RECEIPT_SCHEMA = "yax-numerical-existence-receipt-v1"
NUMERICAL_SPEC = re.compile(r"^yaxnumspec_v1_[0-9a-f]{64}$")
A1_MODEL_PASS_CLASSIFICATION = "PASS_FINITE_EXTENDED_MLE_TARGET"
A1_TARGET_PASS_STATUS = (
    "FINITE_TARGET_ESTABLISHED_ON_PROFILED_EXTENDED_LIKELIHOOD"
)
A1_COMPARISON_PASS_STATUS = "PASS_A1_TRUST_PATH_VS_ZERO_START_REFERENCE"
A1_PROFILE_PASS_STATUS = "PASS_TWO_SIDED_FINITE_PROFILE"
A1_REFERENCE_METHOD = "independent-damped-sparse-newton-irls"
A1_CERTIFICATE_STATUS = "PASS_A1_NUMERICAL_CERTIFICATE"
A1_PRIMARY_PATH = "trust-path"
TARGET_DEPENDENCY_MAP_REL = Path("contracts/TARGET_DEPENDENCY_MAP_A1.json")
PRE_EXECUTION_AUTHORIZATION_REL = Path(
    "gate1_transfer/PRE_EXECUTION_AUTHORIZATION.json"
)
A1_TRUST_METHODS = {
    "trust-path-unpolished-trust-ncg",
    "trust-path-with-independent-exact-newton-polish",
}
A1_COMPARISON_CHECKS = {
    "trust_path_externally_certified",
    "zero_start_reference_externally_certified",
    "full_target_vector",
    "full_identified_treatment_vector",
    "fitted_probabilities",
    "objective_per_total",
    "trust_candidate_cross_evaluator_equivalence",
    "reference_candidate_cross_evaluator_equivalence",
}
A1_CERTIFICATE_CHECKS = {
    "shared_problem_binding_pass",
    "deterministic_evaluator_preflight_pass",
    "trust_reference_full_target_vector_pass",
    "trust_reference_full_identified_treatment_vector_pass",
    "trust_reference_fitted_probability_pass",
    "trust_reference_objective_pass",
    "reference_evaluator_checks_pass",
    "reference_external_certificate_pass",
    "trust_path_external_certificate_pass",
    "profile_reference_method_pass",
    "fitted_hessian_pass",
    "both_candidates_raw_scaled_fitted_hessian_pass",
    "lbfgsb_diagnostic_contradiction_free",
}
RESOLVED_REQUIREMENT_STATUSES = {
    "VERIFIED", "PREMISE_CORRECTED", "INAPPLICABLE_APPROVED",
}


def _frozen_dynamic_q5_targets() -> tuple[list[str], list[str]]:
    all_targets = [
        f"Q5_x_{year}Q{quarter}"
        for year in range(2017, 2027)
        for quarter in range(1, 5)
        if (year, quarter) <= (2026, 3)
        and (year, quarter) != (2022, 4)
    ]
    pretrend = [
        label for label in all_targets
        if label.rsplit("_", 1)[1] < "2022Q4"
    ]
    return all_targets, pretrend


class DependencyError(ValueError):
    pass


def compute_run_fingerprint(run: dict[str, Any]) -> str:
    dependencies = sorted(
        ({k: dep[k] for k in ("run_id", "result_id", "artifact_sha256")}
         for dep in run.get("dependencies", [])),
        key=lambda row: (row["run_id"], row["result_id"]),
    )
    payload = {
        "spec_id": run.get("spec_id"),
        "code_sha256": run.get("code_sha256"),
        "environment_sha256": run.get("environment_sha256"),
        "command": run.get("command"),
        "dependencies": dependencies,
    }
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _contained_file(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or not rel.parts:
        raise DependencyError(f"unsafe artifact path: {relative!r}")
    path = (root / rel).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file() or path.is_symlink():
        raise DependencyError(f"artifact must be a regular contained file: {relative}")
    return path


def validate_manifest(document: Any, root: Path) -> dict[str, dict[str, Any]]:
    root = root.resolve(strict=True)
    if not isinstance(document, dict) or document.get("schema_version") != "yax-run-dag-v1":
        raise DependencyError("manifest schema_version must be yax-run-dag-v1")
    rows = document.get("runs")
    if not isinstance(rows, list):
        raise DependencyError("manifest runs must be a list")
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not row.get("run_id"):
            raise DependencyError("each run needs run_id")
        if row["run_id"] in indexed:
            raise DependencyError(f"duplicate run_id: {row['run_id']}")
        if row.get("status") not in RUN_STATUSES:
            raise DependencyError(f"invalid run status for {row['run_id']}")
        indexed[row["run_id"]] = row

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(run_id: str) -> None:
        if run_id in visiting:
            raise DependencyError(f"dependency cycle includes {run_id}")
        if run_id in visited:
            return
        visiting.add(run_id)
        for dependency in indexed[run_id].get("dependencies", []):
            upstream = dependency.get("run_id")
            if upstream not in indexed:
                raise DependencyError(f"{run_id} has unknown dependency {upstream}")
            visit(upstream)
        visiting.remove(run_id)
        visited.add(run_id)

    for run_id in indexed:
        visit(run_id)

    for run_id, row in indexed.items():
        spec_id = row.get("spec_id", "")
        if not isinstance(spec_id, str) or not spec_id.startswith(SPEC_PREFIX):
            raise DependencyError(f"{run_id} has invalid spec_id")
        for field in ("code_sha256", "environment_sha256"):
            if not SHA256.fullmatch(str(row.get(field, ""))):
                raise DependencyError(f"{run_id} has invalid {field}")
        expected = compute_run_fingerprint(row)
        if row.get("run_fingerprint") != expected:
            raise DependencyError(f"{run_id} cache fingerprint mismatch")
        if row["status"] == "SUCCESS":
            for dependency in row.get("dependencies", []):
                upstream = indexed[dependency["run_id"]]
                if upstream["status"] != "SUCCESS":
                    raise DependencyError(
                        f"{run_id} cannot succeed after {upstream['run_id']} status {upstream['status']}"
                    )
                exported = {item["result_id"]: item for item in upstream.get("outputs", [])}
                actual = exported.get(dependency.get("result_id"))
                if not actual or actual.get("sha256") != dependency.get("artifact_sha256"):
                    raise DependencyError(f"{run_id} dependency fingerprint is stale for {upstream['run_id']}")
            outputs = row.get("outputs")
            if not isinstance(outputs, list) or not outputs:
                raise DependencyError(f"successful run {run_id} has no outputs")
            for output in outputs:
                path = _contained_file(root, output.get("path", ""))
                if sha256_file(path) != output.get("sha256"):
                    raise DependencyError(f"output hash mismatch for {run_id}: {output.get('path')}")
        elif row["status"] == "FAILED":
            failure = row.get("failure")
            if not isinstance(failure, dict) or not failure.get("message") or not failure.get("log_path"):
                raise DependencyError(f"failed run {run_id} lacks retained failure evidence")
            log = _contained_file(root, failure["log_path"])
            if sha256_file(log) != failure.get("log_sha256"):
                raise DependencyError(f"failure-log hash mismatch for {run_id}")
    return indexed


def validate_target_dependency_map(
    document: Any, root: Path,
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    """Validate the narrow A1 model-to-consumer dependency contract.

    This is deliberately not a second general DAG.  It records only which of
    the eleven frozen numerical models a named downstream work unit consumes.
    Non-numerical requirement and run dependencies remain governed by the
    requirements ledger and run manifest.
    """
    root = root.resolve(strict=True)
    if (
        not isinstance(document, dict)
        or document.get("schema_version") != TARGET_MAP_SCHEMA
    ):
        raise DependencyError(
            f"target map schema_version must be {TARGET_MAP_SCHEMA}"
        )
    if document.get("unmapped_consumer_policy") != "FAIL_CLOSED":
        raise DependencyError("target map must fail closed for unmapped consumers")
    if document.get("whole_suite_rule") != (
        "The overall numerical suite remains BLOCKED unless all 11 "
        "registered models are certified, even when individual consumers "
        "are released."
    ):
        raise DependencyError("target map has an invalid whole-suite rule")
    authorization = document.get("authorization")
    if not isinstance(authorization, dict):
        raise DependencyError("target map needs its A1 authorization binding")
    authorization_path = _contained_file(
        root, authorization.get("path", "")
    )
    authorization_sha = authorization.get("sha256")
    if (
        not SHA256.fullmatch(str(authorization_sha or ""))
        or sha256_file(authorization_path) != authorization_sha
    ):
        raise DependencyError("target map A1 authorization hash mismatch")

    contract = document.get("certification_contract")
    if not isinstance(contract, dict):
        raise DependencyError("target map needs certification_contract")
    expected_contract = {
        "audit_schema_version": NUMERICAL_AUDIT_SCHEMA,
        "receipt_schema_version": NUMERICAL_RECEIPT_SCHEMA,
        "model_pass_classification": A1_MODEL_PASS_CLASSIFICATION,
        "target_estimability_pass_status": A1_TARGET_PASS_STATUS,
        "solver_comparison_pass_status": A1_COMPARISON_PASS_STATUS,
        "target_profile_pass_status": A1_PROFILE_PASS_STATUS,
        "reference_method": A1_REFERENCE_METHOD,
        "a1_model_certificate_status": A1_CERTIFICATE_STATUS,
        "primary_path": A1_PRIMARY_PATH,
        "target_absolute_tolerance": 1e-6,
    }
    for key, expected in expected_contract.items():
        if contract.get(key) != expected:
            raise DependencyError(
                f"target map certification_contract has invalid {key}"
            )
    canonical_spec_id = contract.get("canonical_spec_id", "")
    if not (
        isinstance(canonical_spec_id, str)
        and canonical_spec_id.startswith(SPEC_PREFIX)
    ):
        raise DependencyError(
            "target map certification_contract has invalid canonical_spec_id"
        )
    if not NUMERICAL_SPEC.fullmatch(
        str(contract.get("required_a1_audit_spec_id", ""))
    ) or not SHA256.fullmatch(
        str(contract.get("required_a1_audit_spec_sha256", ""))
    ) or not SHA256.fullmatch(
        str(contract.get("required_a1_runner_code_sha256", ""))
    ):
        raise DependencyError(
            "target map needs exact authorized A1 numerical spec and runner bindings"
        )
    forbidden = contract.get("forbidden_audit_spec_ids")
    if (
        not isinstance(forbidden, list)
        or not forbidden
        or any(not NUMERICAL_SPEC.fullmatch(str(value)) for value in forbidden)
        or len(forbidden) != len(set(forbidden))
    ):
        raise DependencyError(
            "target map needs unique forbidden historical audit spec IDs"
        )
    prerequisites = document.get("non_model_prerequisites")
    if not isinstance(prerequisites, dict) or set(prerequisites) != {
        "authenticated_cells", "exact_target_audit",
    }:
        raise DependencyError(
            "target map needs the exact authenticated-cells and target-audit prerequisites"
        )
    for prerequisite_id, prerequisite in prerequisites.items():
        if not isinstance(prerequisite, dict):
            raise DependencyError(
                f"invalid non-model prerequisite: {prerequisite_id}"
            )
        requirement_ids = prerequisite.get("requirement_ids")
        if (
            not isinstance(requirement_ids, list)
            or not requirement_ids
            or any(
                not isinstance(value, str) or not value
                for value in requirement_ids
            )
            or len(requirement_ids) != len(set(requirement_ids))
        ):
            raise DependencyError(
                f"{prerequisite_id} needs its existing requirement_ids"
            )
        for key in (
            "path", "sha256", "receipt_path", "receipt_sha256",
            "expected_status",
        ):
            if not isinstance(prerequisite.get(key), str) or not prerequisite[key]:
                raise DependencyError(
                    f"{prerequisite_id} has invalid {key}"
                )
        if not SHA256.fullmatch(prerequisite["sha256"]) or not SHA256.fullmatch(
            prerequisite["receipt_sha256"]
        ):
            raise DependencyError(
                f"{prerequisite_id} has invalid prerequisite hashes"
            )

    model_ids = document.get("registered_model_ids")
    if (
        not isinstance(model_ids, list)
        or len(model_ids) != 11
        or any(not isinstance(value, str) or not value for value in model_ids)
        or len(model_ids) != len(set(model_ids))
    ):
        raise DependencyError(
            "target map must contain exactly 11 unique registered model IDs"
        )
    known_models = set(model_ids)
    consumers = document.get("consumers")
    if not isinstance(consumers, list) or not consumers:
        raise DependencyError("target map consumers must be a nonempty list")
    indexed: dict[str, dict[str, Any]] = {}
    covered_models: set[str] = set()
    for row in consumers:
        if not isinstance(row, dict):
            raise DependencyError("each target-map consumer must be an object")
        consumer_id = row.get("consumer_id")
        if not isinstance(consumer_id, str) or not consumer_id:
            raise DependencyError("each target-map consumer needs consumer_id")
        if consumer_id in indexed:
            raise DependencyError(f"duplicate consumer_id: {consumer_id}")
        required = row.get("required_model_ids")
        if (
            not isinstance(required, list)
            or not required
            or any(not isinstance(value, str) or not value for value in required)
            or len(required) != len(set(required))
        ):
            raise DependencyError(
                f"{consumer_id} needs unique nonempty required_model_ids"
            )
        unknown = sorted(set(required) - known_models)
        if unknown:
            raise DependencyError(
                f"{consumer_id} has unknown required models: "
                + ", ".join(unknown)
            )
        downstream = row.get("downstream_requirement_ids", [])
        if (
            not isinstance(downstream, list)
            or any(not isinstance(value, str) or not value for value in downstream)
            or len(downstream) != len(set(downstream))
        ):
            raise DependencyError(
                f"{consumer_id} has invalid downstream_requirement_ids"
            )
        covered_models.update(required)
        indexed[consumer_id] = row
    missing_coverage = sorted(known_models - covered_models)
    if missing_coverage:
        raise DependencyError(
            "target map has registered models with no exact consumer: "
            + ", ".join(missing_coverage)
        )
    return model_ids, indexed


def _load_bound_json(
    root: Path, relative: str, expected_sha256: str,
) -> tuple[dict[str, Any], Path]:
    path = _contained_file(root, relative)
    if sha256_file(path) != expected_sha256:
        raise DependencyError(f"bound prerequisite hash mismatch: {relative}")
    try:
        with path.open("r", encoding="utf-8") as stream:
            document = json.load(stream)
    except json.JSONDecodeError as error:
        raise DependencyError(f"bound prerequisite is not JSON: {relative}") from error
    if not isinstance(document, dict):
        raise DependencyError(f"bound prerequisite is not an object: {relative}")
    return document, path


def _git_output(root: Path, arguments: list[str], *, binary: bool = False) -> bytes | str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *arguments], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=not binary,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise DependencyError("pre-outcome target-map Git binding is unavailable") from error
    if completed.stderr not in {"", b""}:
        raise DependencyError("pre-outcome target-map Git check emitted stderr")
    return completed.stdout


def validate_preoutcome_target_map_binding(
    target_map: dict[str, Any], receipt: dict[str, Any], root: Path,
) -> dict[str, Any]:
    """Bind the active map to the numerical run's pre-execution auth commit."""
    summary = receipt.get("pre_execution_authorization")
    if not isinstance(summary, dict):
        raise DependencyError("numerical receipt lacks pre-execution authorization")
    auth_commit = summary.get("authorization_git_commit")
    implementation_commit = summary.get("authorized_implementation_commit")
    if (
        not isinstance(auth_commit, str)
        or not re.fullmatch(r"[0-9a-f]{40}", auth_commit)
        or not isinstance(implementation_commit, str)
        or not re.fullmatch(r"[0-9a-f]{40}", implementation_commit)
        or auth_commit == implementation_commit
    ):
        raise DependencyError("numerical authorization Git chain is malformed")

    repo_text = _git_output(root, ["rev-parse", "--show-toplevel"])
    assert isinstance(repo_text, str)
    repo = Path(repo_text.strip()).resolve(strict=True)
    map_path = _contained_file(root, TARGET_DEPENDENCY_MAP_REL.as_posix())
    try:
        map_repo_rel = map_path.relative_to(repo).as_posix()
        auth_path = (root / PRE_EXECUTION_AUTHORIZATION_REL).resolve(strict=False)
        auth_repo_rel = auth_path.relative_to(repo).as_posix()
    except ValueError as error:
        raise DependencyError("target map is outside its authenticated Git worktree") from error
    current_map_bytes = map_path.read_bytes()
    try:
        parsed_current = json.loads(current_map_bytes)
    except json.JSONDecodeError as error:
        raise DependencyError("current target map is not JSON") from error
    if parsed_current != target_map:
        raise DependencyError("supplied target map differs from the canonical current map")
    committed_map = _git_output(
        repo, ["show", f"{auth_commit}:{map_repo_rel}"], binary=True
    )
    assert isinstance(committed_map, bytes)
    if current_map_bytes != committed_map:
        raise DependencyError(
            "current target map differs from the pre-outcome authorization commit"
        )

    observed_parent = _git_output(repo, ["rev-parse", f"{auth_commit}^"])
    changed = _git_output(
        repo, ["diff-tree", "--no-commit-id", "--name-only", "-r", auth_commit]
    )
    assert isinstance(observed_parent, str) and isinstance(changed, str)
    if (
        observed_parent.strip() != implementation_commit
        or changed.splitlines() != [auth_repo_rel]
    ):
        raise DependencyError(
            "numerical authorization is not a separate auth-only commit over the map"
        )
    auth_bytes = _git_output(
        repo, ["show", f"{auth_commit}:{auth_repo_rel}"], binary=True
    )
    assert isinstance(auth_bytes, bytes)
    try:
        authorization = json.loads(auth_bytes)
    except json.JSONDecodeError as error:
        raise DependencyError("committed pre-execution authorization is not JSON") from error
    if not isinstance(authorization, dict):
        raise DependencyError("committed pre-execution authorization is malformed")
    identifier_core = dict(authorization)
    identifier = identifier_core.pop("authorization_id", None)
    expected_identifier = "yaxgate1auth_v1_" + hashlib.sha256(
        canonical_bytes(identifier_core)
    ).hexdigest()
    module = authorization.get("modules", {}).get("numerical")
    contract = target_map["certification_contract"]
    if (
        authorization.get("schema_version")
        != "yax-gate1-pre-execution-authorization-v1"
        or authorization.get("status") != "AUTHORIZED_FRESH_GATE1_EXECUTION"
        or identifier != expected_identifier
        or authorization.get("authorized_implementation_commit")
        != implementation_commit
        or not isinstance(module, dict)
        or module.get("typed_spec_id") != contract["required_a1_audit_spec_id"]
        or module.get("typed_spec_sha256")
        != contract["required_a1_audit_spec_sha256"]
        or module.get("code_sha256")
        != contract["required_a1_runner_code_sha256"]
    ):
        raise DependencyError("committed numerical authorization binding differs")
    expected_summary = {
        "schema_version": authorization["schema_version"],
        "status": authorization["status"],
        "authorization_id": identifier,
        "authorization_file_sha256": hashlib.sha256(auth_bytes).hexdigest(),
        "authorization_git_commit": auth_commit,
        "authorized_implementation_commit": implementation_commit,
        "issued_at_utc": authorization.get("issued_at_utc"),
        "not_before_utc": authorization.get("not_before_utc"),
        "not_after_utc": authorization.get("not_after_utc"),
        "module_key": "numerical",
        "typed_spec_id": module["typed_spec_id"],
        "typed_spec_sha256": module["typed_spec_sha256"],
        "code_sha256": module["code_sha256"],
        "source_registry_sha256": authorization.get("source_registry_sha256"),
    }
    if summary != expected_summary:
        raise DependencyError(
            "numerical receipt authorization summary differs from its committed authority"
        )
    return {
        "status": "PASS_PREOUTCOME_TARGET_MAP_BYTE_BINDING",
        "authorization_git_commit": auth_commit,
        "authorized_implementation_commit": implementation_commit,
        "target_dependency_map_sha256": hashlib.sha256(current_map_bytes).hexdigest(),
    }


def validate_non_model_prerequisites(
    target_map: dict[str, Any], root: Path, audit: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    """Validate the two already-existing non-model Gate-1 prerequisites."""
    prerequisites = target_map["non_model_prerequisites"]
    cells_binding = prerequisites["authenticated_cells"]
    cells_document, _ = _load_bound_json(
        root, cells_binding["path"], cells_binding["sha256"]
    )
    cells_receipt, _ = _load_bound_json(
        root, cells_binding["receipt_path"],
        cells_binding["receipt_sha256"],
    )
    if cells_document != cells_receipt:
        raise DependencyError(
            "authenticated-cells prerequisite must bind its single retained receipt"
        )
    if (
        cells_receipt.get("schema_version")
        != "yax-numerical-cells-receipt-v1"
        or cells_receipt.get("status") != cells_binding["expected_status"]
    ):
        raise DependencyError("authenticated-cells prerequisite is not PASS")

    target_binding = prerequisites["exact_target_audit"]
    target_audit, _ = _load_bound_json(
        root, target_binding["path"], target_binding["sha256"]
    )
    target_receipt, _ = _load_bound_json(
        root, target_binding["receipt_path"],
        target_binding["receipt_sha256"],
    )
    if (
        target_audit.get("status") != target_binding["expected_status"]
        or target_receipt.get("status") != target_binding["expected_status"]
        or target_receipt.get("schema_version")
        != "yax-exact-target-audit-receipt-v1"
        or target_receipt.get("artifact_hashes", {}).get(
            "EXACT_TARGET_AUDIT.json"
        ) != target_binding["sha256"]
        or target_receipt.get("source_aggregate_receipt_sha256")
        != cells_binding["receipt_sha256"]
    ):
        raise DependencyError("exact-target prerequisite binding is invalid")

    canonical_spec_id = target_map["certification_contract"][
        "canonical_spec_id"
    ]
    cells_sha256 = cells_receipt.get("cells_sha256")
    if not SHA256.fullmatch(str(cells_sha256 or "")):
        raise DependencyError("authenticated cells receipt has invalid cells_sha256")
    if any(
        document.get("canonical_spec_id") != canonical_spec_id
        for document in (
            cells_receipt, target_audit, target_receipt, audit, receipt,
        )
    ):
        raise DependencyError(
            "non-model prerequisite canonical specifications disagree"
        )
    if (
        target_audit.get("authenticated_cells_sha256") != cells_sha256
        or target_receipt.get("authenticated_cells_sha256") != cells_sha256
        or audit.get("cells_sha256") != cells_sha256
        or receipt.get("cells_sha256") != cells_sha256
        or receipt.get("cells_receipt_sha256")
        != cells_binding["receipt_sha256"]
    ):
        raise DependencyError(
            "numerical artifacts do not consume the bound authenticated cells"
        )
    return {
        "status": "PASS_BOUND_NON_MODEL_PREREQUISITES",
        "requirement_ids": list(dict.fromkeys(
            target_binding["requirement_ids"]
            + cells_binding["requirement_ids"]
        )),
        "authenticated_cells_receipt_sha256": cells_binding[
            "receipt_sha256"
        ],
        "exact_target_audit_sha256": target_binding["sha256"],
        "exact_target_receipt_sha256": target_binding["receipt_sha256"],
    }


def requirement_ledger_snapshot(
    document: Any, requirement_ids: list[str],
) -> dict[str, Any]:
    """Report, but do not substitute, stale working-ledger dispositions."""
    if not isinstance(document, dict) or not isinstance(
        document.get("requirements"), list
    ):
        raise DependencyError("requirements ledger must contain requirements")
    indexed: dict[str, dict[str, Any]] = {}
    for row in document["requirements"]:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            raise DependencyError("requirements ledger has an invalid row")
        if row["id"] in indexed:
            raise DependencyError(
                f"requirements ledger has duplicate ID: {row['id']}"
            )
        indexed[row["id"]] = row
    missing = sorted(set(requirement_ids) - set(indexed))
    if missing:
        raise DependencyError(
            "requirements ledger omits non-model prerequisites: "
            + ", ".join(missing)
        )
    statuses = {
        requirement_id: indexed[requirement_id].get("status")
        for requirement_id in requirement_ids
    }
    stale = [
        requirement_id for requirement_id, status in statuses.items()
        if status not in RESOLVED_REQUIREMENT_STATUSES
    ]
    return {
        "statuses": statuses,
        "stale_or_unresolved_requirement_ids": stale,
        "interpretation": (
            "ledger agrees with verified prerequisite artifacts"
            if not stale else
            "working ledger is stale or unresolved; it is not used as PASS "
            "evidence and must be reconciled separately"
        ),
    }


def _a1_model_is_certified(model: dict[str, Any]) -> bool:
    a1_certificate = model.get("a1_certification")
    comparison = model.get("solver_comparison")
    profile = model.get("target_profile")
    fitted_hessian = model.get("fitted_full_hessian")
    fitted_information = model.get("fitted_information")
    reported_information = model.get("fitted_reported_target_information")
    dual_hessian = model.get("dual_candidate_fitted_hessian_audit")
    lbfgsb_audit = model.get("lbfgsb_diagnostic_contradiction_audit")
    if not all(
        isinstance(value, dict)
        for value in (
            comparison, profile, fitted_hessian, fitted_information,
            reported_information,
        )
    ) or not isinstance(a1_certificate, dict):
        return False
    if not _a1_dual_hessian_evidence_passes(dual_hessian):
        return False
    checks = comparison.get("checks")
    target_differences = comparison.get("target_absolute_differences")
    treatment_basis = model.get("treatment_basis")
    target_parameterization = model.get("target_parameterization")
    selected_labels = (
        treatment_basis.get("selected_original_labels")
        if isinstance(treatment_basis, dict) else None
    )
    transformed_labels = (
        {
            f"treatment_basis::{index}::{label}"
            for index, label in enumerate(selected_labels)
        }
        if isinstance(selected_labels, list)
        and all(isinstance(label, str) and label for label in selected_labels)
        else set()
    )
    original_rows = (
        target_parameterization.get(
            "original_coefficient_functionals_in_current_basis"
        ) if isinstance(target_parameterization, dict) else None
    )
    original_regressor_labels = (
        target_parameterization.get("original_regressor_labels")
        if isinstance(target_parameterization, dict) else None
    )
    original_labels: list[str] = []
    if (
        isinstance(original_rows, list)
        and isinstance(original_regressor_labels, list)
        and original_regressor_labels
        and len(original_regressor_labels) == len(set(original_regressor_labels))
        and all(
            isinstance(label, str) and label for label in original_regressor_labels
        )
        and len(original_rows) == len(original_regressor_labels)
        and treatment_basis.get("original_columns") == len(original_regressor_labels)
        if isinstance(treatment_basis, dict) else False
    ):
        for expected_index, row in enumerate(original_rows):
            if (
                not isinstance(row, dict)
                or row.get("original_index") != expected_index
                or row.get("original_label") != original_regressor_labels[expected_index]
                or not isinstance(row.get("weights"), list)
                or len(row["weights"]) != len(original_regressor_labels)
                or any(not _finite_number(weight) for weight in row["weights"])
            ):
                original_labels = []
                break
            original_labels.append(
                f"original_treatment::{expected_index}::{row['original_label']}"
            )
    original_label_set = set(original_labels)
    dynamic_scope = model.get("dynamic_event_target_scope")
    reported_labels = (
        dynamic_scope.get("reported_q5_event_targets")
        if isinstance(dynamic_scope, dict) else []
    )
    if reported_labels is None:
        reported_labels = []
    reported_label_set = (
        set(reported_labels)
        if isinstance(reported_labels, list)
        and len(reported_labels) == len(set(reported_labels))
        and all(isinstance(label, str) and label for label in reported_labels)
        else set()
    )
    expected_target_labels = (
        {"focal_target"} | original_label_set | transformed_labels
        | reported_label_set
    )
    if not _a1_lbfgsb_diagnostic_evidence_passes(
        lbfgsb_audit, expected_target_labels
    ):
        return False
    identified_treatment_labels = comparison.get(
        "identified_treatment_target_labels"
    )
    full_vector_fields = (
        "trust_path_target_vector", "reference_target_vector",
        "reported_target_absolute_differences",
    )
    if (
        not isinstance(checks, dict)
        or set(checks) != A1_COMPARISON_CHECKS
        or any(checks[key] is not True for key in A1_COMPARISON_CHECKS)
        or not isinstance(target_differences, dict)
        or not expected_target_labels
        or not original_labels
        or set(target_differences) != expected_target_labels
        or any(
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0.0
            for value in target_differences.values()
        )
        or not isinstance(identified_treatment_labels, list)
        or identified_treatment_labels != original_labels
        or comparison.get("identified_treatment_target_count")
        != len(original_labels)
        or a1_certificate.get("identified_treatment_vector_length")
        != len(original_labels)
        or any(
            not isinstance(comparison.get(field), dict)
            or set(comparison[field]) != expected_target_labels
            or any(not _finite_number(value) for value in comparison[field].values())
            for field in full_vector_fields
        )
        or not isinstance(
            comparison.get("identified_treatment_absolute_differences"), dict
        )
        or set(comparison["identified_treatment_absolute_differences"])
        != original_label_set
        or not isinstance(
            comparison.get(
                "transformed_basis_absolute_differences_nonbinding_diagnostic"
            ), dict
        )
        or set(comparison[
            "transformed_basis_absolute_differences_nonbinding_diagnostic"
        ]) != transformed_labels
        or any(
            comparison["identified_treatment_absolute_differences"][label]
            != target_differences[label] for label in original_labels
        )
        or any(
            comparison[
                "transformed_basis_absolute_differences_nonbinding_diagnostic"
            ][label] != target_differences[label]
            for label in transformed_labels
        )
        or any(
            comparison["reported_target_absolute_differences"][label]
            != target_differences[label] for label in expected_target_labels
        )
        or any(
            abs(
                comparison["trust_path_target_vector"][label]
                - comparison["reference_target_vector"][label]
            ) != target_differences[label]
            for label in expected_target_labels
        )
        or comparison.get(
            "maximum_absolute_full_identified_treatment_vector_difference"
        ) != max((target_differences[label] for label in original_labels), default=math.inf)
        or comparison.get("reported_target_max_absolute_difference")
        != max(target_differences.values(), default=math.inf)
        or comparison.get("focal_target_absolute_difference")
        != target_differences.get("focal_target")
        or not _a1_cross_evaluation_passes(
            comparison.get("trust_candidate_cross_evaluation")
        )
        or not _a1_cross_evaluation_passes(
            comparison.get("reference_candidate_cross_evaluation")
        )
        or comparison.get("same_final_tolerances") != {
            "target_coefficient_absolute_difference": 1e-6,
            "fitted_probability_max_abs_difference": 1e-7,
            "objective_difference_per_total": 1e-10,
        }
        or not _finite_number(
            comparison.get("fitted_probability_max_abs_difference")
        )
        or comparison["fitted_probability_max_abs_difference"] > 1e-7
        or not _finite_number(comparison.get("objective_difference_per_total"))
        or comparison["objective_difference_per_total"] > 1e-10
        or max(
            (target_differences[label] for label in original_labels),
            default=math.inf,
        ) > 1e-6
    ):
        return False
    if (
        a1_certificate.get("status") != A1_CERTIFICATE_STATUS
        or a1_certificate.get("primary_path") != A1_PRIMARY_PATH
        or a1_certificate.get("reference_path") != A1_REFERENCE_METHOD
        or any(
            a1_certificate.get(key) is not True
            for key in A1_CERTIFICATE_CHECKS
        )
    ):
        return False
    information_rank = fitted_information.get("treatment_information_rank")
    information_columns = fitted_information.get(
        "treatment_information_columns"
    )
    if not (
        model.get("finite_target_established") is True
        and model.get("classification") == A1_MODEL_PASS_CLASSIFICATION
        and model.get("target_estimability_status") == A1_TARGET_PASS_STATUS
        and comparison.get("status") == A1_COMPARISON_PASS_STATUS
        and comparison.get("comparison_pass") is True
        and comparison.get("left_valid") is True
        and comparison.get("right_valid") is True
        and comparison.get("left_solver") in A1_TRUST_METHODS
        and comparison.get("right_solver") == A1_REFERENCE_METHOD
        and profile.get("status") == A1_PROFILE_PASS_STATUS
        and fitted_hessian.get("status") == "PASS_FULL_HESSIAN_SPECTRUM"
        and fitted_hessian.get("rank_deficiency") == 0
        and fitted_information.get("focal_target_rank_identified") is True
        and isinstance(information_rank, int)
        and information_rank == information_columns
        and reported_information.get("status") in {
            "NOT_APPLICABLE",
            "PASS_ALL_REPORTED_TARGETS_AND_JOINT_PRETREND_INFORMATION_RANK",
        }
    ):
        return False
    if model.get("model_id") in {
        "dynamics_unconditioned", "dynamics_family_month",
    } and not _a1_dynamic_scope_passes(dynamic_scope):
        return False
    if dynamic_scope is not None and (
        not isinstance(dynamic_scope, dict)
        or dynamic_scope.get("overall_status")
        != "PASS_ALL_REPORTED_Q5_EVENT_TARGETS_AND_POST_FUNCTIONAL_FULL_AUDIT"
    ):
        return False
    return True


def _a1_dynamic_scope_passes(value: Any) -> bool:
    expected_targets, expected_pretrend = _frozen_dynamic_q5_targets()
    expected_checks = {
        "reported_target_labels_exact", "reported_target_count",
        "joint_pretrend_labels_exact", "joint_pretrend_count",
        "observed_post_month_count", "post_functional_weights_exact",
        "post_functional_weights_sum_to_one",
    }
    if not isinstance(value, dict):
        return False
    checks = value.get("checks")
    return bool(
        value.get("status") == "PASS_COMPLETE_DYNAMIC_TARGET_SCOPE_CONSTRUCTION"
        and value.get("declared_primary_target")
        == "observed_calendar_month_weighted_post_Q5_functional"
        and value.get("reference_quarter") == "2022Q4"
        and value.get("reported_q5_event_targets") == expected_targets
        and value.get("reported_q5_event_target_count") == 38
        and value.get("joint_pretrend_targets") == expected_pretrend
        and value.get("joint_pretrend_target_count") == 23
        and value.get("observed_post_month_count") == 42
        and _finite_number(value.get("post_functional_weight_sum"))
        and abs(value["post_functional_weight_sum"] - 1.0) <= 1e-14
        and _finite_number(
            value.get("post_functional_weight_max_absolute_error")
        )
        and value["post_functional_weight_max_absolute_error"] <= 1e-14
        and isinstance(checks, dict)
        and set(checks) == expected_checks
        and all(checks.get(key) is True for key in expected_checks)
        and value.get("recession_direction_status")
        == "PASS_ALL_REPORTED_Q5_TARGETS_RECESSION_INVARIANT_ON_FINAL_FACE"
        and value.get("geometric_information_status")
        == "PASS_ALL_REPORTED_TARGETS_AND_JOINT_PRETREND_INFORMATION_RANK"
        and value.get("fitted_information_status")
        == "PASS_ALL_REPORTED_TARGETS_AND_JOINT_PRETREND_INFORMATION_RANK"
        and value.get("reported_target_solver_comparison_status") == "PASS"
        and value.get("overall_status")
        == "PASS_ALL_REPORTED_Q5_EVENT_TARGETS_AND_POST_FUNCTIONAL_FULL_AUDIT"
    )


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _a1_cross_evaluation_passes(value: Any) -> bool:
    fields = {
        "status", "checks", "finite_difference_step",
        "objective_per_total_absolute_difference",
        "fitted_probability_max_absolute_difference",
        "score_per_total_max_absolute_difference",
        "hessian_product_per_total_max_absolute_difference",
        "directional_derivative_absolute_difference",
        "finite_difference_hessian_product_max_absolute_difference",
        "objective_tolerance", "probability_tolerance",
        "gradient_or_derivative_tolerance", "direction_definition",
    }
    check_names = {
        "objective_equivalence", "probability_equivalence", "score_equivalence",
        "hessian_product_equivalence", "directional_derivative",
        "finite_difference_hessian_product",
    }
    if not isinstance(value, dict) or set(value) != fields:
        return False
    checks = value.get("checks")
    numeric_fields = fields - {
        "status", "checks", "direction_definition",
    }
    if (
        value.get("status")
        != "PASS_INDEPENDENT_EVALUATOR_AND_DERIVATIVE_CHECKS"
        or not isinstance(checks, dict)
        or set(checks) != check_names
        or any(checks.get(key) is not True for key in check_names)
        or any(not _finite_number(value.get(field)) for field in numeric_fields)
        or value["finite_difference_step"] <= 0
        or value["objective_tolerance"] <= 0
        or value["probability_tolerance"] <= 0
        or value["gradient_or_derivative_tolerance"] <= 0
        or value["objective_per_total_absolute_difference"]
        > value["objective_tolerance"]
        or value["fitted_probability_max_absolute_difference"]
        > value["probability_tolerance"]
        or value["score_per_total_max_absolute_difference"]
        > value["gradient_or_derivative_tolerance"]
        or value["hessian_product_per_total_max_absolute_difference"]
        > value["gradient_or_derivative_tolerance"]
        or value["directional_derivative_absolute_difference"]
        > value["gradient_or_derivative_tolerance"]
        or value["finite_difference_hessian_product_max_absolute_difference"]
        > value["gradient_or_derivative_tolerance"]
        or not isinstance(value.get("direction_definition"), str)
        or not value["direction_definition"]
    ):
        return False
    return True


def _a1_dual_hessian_evidence_passes(value: Any) -> bool:
    """Inspect both fitted-Hessian records; summary booleans are not evidence."""
    labels = {"trust_path", "independent_zero_start_reference"}
    if not isinstance(value, dict) or set(value) != {
        "status", "expected_full_rank", "checks", "candidates",
    }:
        return False
    expected_rank = value.get("expected_full_rank")
    checks = value.get("checks")
    candidates = value.get("candidates")
    if (
        value.get("status")
        != "PASS_BOTH_CANDIDATE_RAW_AND_SCALED_FITTED_HESSIANS"
        or not isinstance(expected_rank, int)
        or isinstance(expected_rank, bool)
        or expected_rank <= 0
        or not isinstance(checks, dict)
        or set(checks) != labels
        or any(checks.get(label) is not True for label in labels)
        or not isinstance(candidates, dict)
        or set(candidates) != labels
    ):
        return False
    for label in labels:
        candidate = candidates[label]
        candidate_fields = {
            "columns", "rank_from_nuisance_plus_schur", "rank_deficiency",
            "spectrum_method", "smallest_positive_or_extreme_eigenvalue",
            "largest_eigenvalue", "smallest_eigenpair_residual_norm_2",
            "largest_eigenpair_residual_norm_2",
            "smallest_certified_lower_bound", "largest_conservative_upper_bound",
            "condition_number", "rank_threshold",
            "diagonally_scaled_spectrum_method",
            "diagonally_scaled_smallest_positive_or_extreme_eigenvalue",
            "diagonally_scaled_largest_eigenvalue",
            "diagonally_scaled_smallest_eigenpair_residual_norm_2",
            "diagonally_scaled_largest_eigenpair_residual_norm_2",
            "diagonally_scaled_smallest_certified_lower_bound",
            "diagonally_scaled_largest_conservative_upper_bound",
            "diagonally_scaled_condition_number",
            "diagonally_scaled_rank_threshold",
            "positive_definite_at_declared_tolerance", "status",
        }
        if not isinstance(candidate, dict) or set(candidate) != candidate_fields:
            return False
        numeric_fields = (
            "smallest_positive_or_extreme_eigenvalue", "largest_eigenvalue",
            "smallest_eigenpair_residual_norm_2",
            "largest_eigenpair_residual_norm_2",
            "smallest_certified_lower_bound",
            "largest_conservative_upper_bound",
            "condition_number",
            "rank_threshold",
            "diagonally_scaled_smallest_positive_or_extreme_eigenvalue",
            "diagonally_scaled_largest_eigenvalue",
            "diagonally_scaled_smallest_eigenpair_residual_norm_2",
            "diagonally_scaled_largest_eigenpair_residual_norm_2",
            "diagonally_scaled_smallest_certified_lower_bound",
            "diagonally_scaled_largest_conservative_upper_bound",
            "diagonally_scaled_condition_number",
            "diagonally_scaled_rank_threshold",
        )
        if (
            candidate.get("status") != "PASS_FULL_HESSIAN_SPECTRUM"
            or candidate.get("columns") != expected_rank
            or candidate.get("rank_from_nuisance_plus_schur") != expected_rank
            or candidate.get("rank_deficiency") != 0
            or candidate.get("positive_definite_at_declared_tolerance") is not True
            or not isinstance(candidate.get("spectrum_method"), str)
            or not candidate["spectrum_method"]
            or not isinstance(candidate.get("diagonally_scaled_spectrum_method"), str)
            or not candidate["diagonally_scaled_spectrum_method"]
            or any(not _finite_number(candidate.get(field)) for field in numeric_fields)
            or candidate["smallest_positive_or_extreme_eigenvalue"]
            <= candidate["rank_threshold"]
            or candidate["smallest_certified_lower_bound"]
            <= candidate["rank_threshold"]
            or candidate[
                "diagonally_scaled_smallest_positive_or_extreme_eigenvalue"
            ] <= candidate["diagonally_scaled_rank_threshold"]
            or candidate[
                "diagonally_scaled_smallest_certified_lower_bound"
            ] <= candidate["diagonally_scaled_rank_threshold"]
            or candidate["smallest_eigenpair_residual_norm_2"] < 0
            or candidate["largest_eigenpair_residual_norm_2"] < 0
            or candidate[
                "diagonally_scaled_smallest_eigenpair_residual_norm_2"
            ] < 0
            or candidate[
                "diagonally_scaled_largest_eigenpair_residual_norm_2"
            ] < 0
            or candidate["largest_conservative_upper_bound"]
            < candidate["largest_eigenvalue"]
            or candidate["diagonally_scaled_largest_conservative_upper_bound"]
            < candidate["diagonally_scaled_largest_eigenvalue"]
            or candidate["largest_eigenvalue"]
            < candidate["smallest_positive_or_extreme_eigenvalue"]
            or candidate["diagonally_scaled_largest_eigenvalue"]
            < candidate[
                "diagonally_scaled_smallest_positive_or_extreme_eigenvalue"
            ]
        ):
            return False
    return True


def _a1_lbfgsb_diagnostic_evidence_passes(
    value: Any, expected_target_labels: set[str],
) -> bool:
    """Require a structurally complete, noncontradictory optional diagnostic."""
    if not isinstance(value, dict):
        return False
    common = {"status", "available", "binding_pass", "contradiction_detected", "interpretation"}
    if (
        value.get("binding_pass") is not True
        or value.get("contradiction_detected") is not False
        or not isinstance(value.get("interpretation"), str)
        or not value["interpretation"]
    ):
        return False
    # A1 downstream release requires the falsification diagnostic to have
    # actually run.  Runner-level unavailability may be nonfatal to producing
    # a blocked leaf, but it is not affirmative consumer-release evidence.
    if value.get("available") is not True:
        return False
    required = common | {
        "diagnostic_candidate_numerically_valid",
        "diagnostic_candidate_independently_stationary",
        "recomputed_objective_per_total",
        "best_binding_objective_per_total",
        "signed_objective_gap_diagnostic_minus_best_binding",
        "target_absolute_differences_vs_reference",
        "maximum_declared_target_absolute_difference_vs_reference",
        "canonical_recomputed_score", "independent_cross_evaluation", "checks",
    }
    if (
        set(value) != required
        or value.get("status") != "PASS_NO_LBFGSB_DIAGNOSTIC_CONTRADICTION"
        or not isinstance(value.get("diagnostic_candidate_numerically_valid"), bool)
        or not isinstance(value.get("diagnostic_candidate_independently_stationary"), bool)
    ):
        return False
    numeric = (
        "recomputed_objective_per_total", "best_binding_objective_per_total",
        "signed_objective_gap_diagnostic_minus_best_binding",
        "maximum_declared_target_absolute_difference_vs_reference",
    )
    differences = value.get("target_absolute_differences_vs_reference")
    checks = value.get("checks")
    expected_checks = {
        "no_materially_lower_diagnostic_objective",
        "no_derivative_implementation_contradiction",
        "no_stationary_declared_target_contradiction",
    }
    if (
        any(not _finite_number(value.get(field)) for field in numeric)
        or not isinstance(differences, dict)
        or set(differences) != expected_target_labels
        or any(
            not isinstance(label, str) or not label
            or not _finite_number(difference) or difference < 0
            for label, difference in differences.items()
        )
        or value["maximum_declared_target_absolute_difference_vs_reference"]
        != max(differences.values())
        or not isinstance(checks, dict)
        or set(checks) != expected_checks
        or any(checks.get(key) is not True for key in expected_checks)
        or not isinstance(value.get("canonical_recomputed_score"), dict)
        or not value["canonical_recomputed_score"]
        or not isinstance(value.get("independent_cross_evaluation"), dict)
        or value["independent_cross_evaluation"].get("status")
        != "PASS_INDEPENDENT_EVALUATOR_AND_DERIVATIVE_CHECKS"
    ):
        return False
    return True


def validate_target_certifications(
    target_map: Any,
    audit: Any,
    receipt: Any,
    root: Path,
    audit_path: str,
    requirements_status: Any | None = None,
) -> dict[str, Any]:
    """Validate A1 model certificates and compute exact consumer releases."""
    root = root.resolve(strict=True)
    model_ids, consumers = validate_target_dependency_map(target_map, root)
    audit_file = _contained_file(root, audit_path)
    if not isinstance(audit, dict) or audit.get("schema_version") != NUMERICAL_AUDIT_SCHEMA:
        raise DependencyError(
            f"model audit schema_version must be {NUMERICAL_AUDIT_SCHEMA}"
        )
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema_version") != NUMERICAL_RECEIPT_SCHEMA
    ):
        raise DependencyError(
            f"numerical receipt schema_version must be {NUMERICAL_RECEIPT_SCHEMA}"
        )
    contract = target_map["certification_contract"]
    preoutcome_map_binding = validate_preoutcome_target_map_binding(
        target_map, receipt, root
    )
    for field in ("status", "canonical_spec_id", "audit_spec_id", "cells_sha256"):
        if audit.get(field) != receipt.get(field):
            raise DependencyError(
                f"numerical audit/receipt disagree on {field}"
            )
    if audit.get("canonical_spec_id") != contract["canonical_spec_id"]:
        raise DependencyError("numerical audit has the wrong canonical spec")
    audit_spec_id = audit.get("audit_spec_id", "")
    if not NUMERICAL_SPEC.fullmatch(str(audit_spec_id)):
        raise DependencyError("numerical audit has invalid audit_spec_id")
    if audit_spec_id in set(contract["forbidden_audit_spec_ids"]):
        raise DependencyError(
            "historical pre-A1 numerical audit cannot release A1 consumers"
        )
    if (
        audit_spec_id != contract["required_a1_audit_spec_id"]
        or receipt.get("audit_spec_sha256")
        != contract["required_a1_audit_spec_sha256"]
        or receipt.get("code_sha256")
        != contract["required_a1_runner_code_sha256"]
    ):
        raise DependencyError(
            "numerical artifacts do not match the exact authorized A1 specification and runner"
        )
    for field in (
        "cells_sha256", "audit_spec_sha256", "code_sha256",
        "canonical_spec_sha256",
    ):
        if not SHA256.fullmatch(str(receipt.get(field, ""))):
            raise DependencyError(f"numerical receipt has invalid {field}")
    output_hashes = receipt.get("output_hashes")
    actual_audit_sha = sha256_file(audit_file)
    if (
        not isinstance(output_hashes, dict)
        or output_hashes.get("MODEL_AUDIT.json") != actual_audit_sha
    ):
        raise DependencyError(
            "numerical receipt does not bind the supplied MODEL_AUDIT.json"
        )
    rows = audit.get("models")
    if not isinstance(rows, list):
        raise DependencyError("model audit models must be a list")
    indexed_models: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("model_id"), str):
            raise DependencyError("each model audit row needs model_id")
        if row["model_id"] in indexed_models:
            raise DependencyError(f"duplicate model audit row: {row['model_id']}")
        indexed_models[row["model_id"]] = row
    if set(indexed_models) != set(model_ids):
        raise DependencyError(
            "model audit registry does not exactly match the frozen 11-model map"
        )
    certified = {
        model_id for model_id, row in indexed_models.items()
        if _a1_model_is_certified(row)
    }
    if receipt.get("model_count") != len(model_ids):
        raise DependencyError("numerical receipt model_count mismatch")
    if receipt.get("passed_model_count") != len(certified):
        raise DependencyError("numerical receipt passed_model_count mismatch")
    expected_suite_status = (
        "PASS_ALL_CORE_TARGETS_NUMERICALLY_AUDITED"
        if len(certified) == len(model_ids)
        else "BLOCKED_ONE_OR_MORE_CORE_TARGETS_NOT_ESTABLISHED"
    )
    if audit.get("status") != expected_suite_status:
        raise DependencyError(
            "numerical suite status is inconsistent with per-model certificates"
        )

    non_model = validate_non_model_prerequisites(
        target_map, root, audit, receipt,
    )

    releases: dict[str, dict[str, Any]] = {}
    for consumer_id, row in consumers.items():
        required = list(row["required_model_ids"])
        blocking = [model_id for model_id in required if model_id not in certified]
        releases[consumer_id] = {
            "numerical_dependency_status": (
                "CERTIFIED" if not blocking else "BLOCKED"
            ),
            "non_model_dependency_status": non_model["status"],
            "release_status": "RELEASED" if not blocking else "BLOCKED",
            "required_model_ids": required,
            "blocking_model_ids": blocking,
            "downstream_requirement_ids": row.get(
                "downstream_requirement_ids", []
            ),
        }
    result = {
        "status": (
            "PASS_ALL_11_MODELS_CERTIFIED"
            if len(certified) == len(model_ids)
            else "BLOCKED_INCOMPLETE_11_MODEL_SUITE"
        ),
        "release_scope": (
            "authorizes reuse of the named certified numerical targets only; "
            "broader requirement completion, inference, and presentation "
            "remain separately governed"
        ),
        "registered_model_count": len(model_ids),
        "certified_model_count": len(certified),
        "certified_model_ids": [
            model_id for model_id in model_ids if model_id in certified
        ],
        "blocked_model_ids": [
            model_id for model_id in model_ids if model_id not in certified
        ],
        "non_model_prerequisites": non_model,
        "preoutcome_target_map_binding": preoutcome_map_binding,
        "consumers": releases,
    }
    if requirements_status is not None:
        result["working_ledger_snapshot"] = requirement_ledger_snapshot(
            requirements_status, non_model["requirement_ids"],
        )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--require-success", nargs="*", default=[])
    parser.add_argument("--target-map", type=Path)
    parser.add_argument("--model-audit", type=Path)
    parser.add_argument("--numerical-receipt", type=Path)
    parser.add_argument("--requirements-status", type=Path)
    parser.add_argument("--require-target", nargs="*", default=[])
    args = parser.parse_args()
    try:
        root = args.root.resolve(strict=True)
        with args.manifest.open("r", encoding="utf-8") as stream:
            indexed = validate_manifest(json.load(stream), root)
        missing = [run_id for run_id in args.require_success
                   if run_id not in indexed or indexed[run_id]["status"] != "SUCCESS"]
        if missing:
            raise DependencyError("gate requirements are not successful: " + ", ".join(missing))
        counts: dict[str, int] = {}
        for row in indexed.values():
            counts[row["status"]] = counts.get(row["status"], 0) + 1
        result: dict[str, Any] = {
            "status": "PASS", "runs": len(indexed),
            "status_counts": counts,
        }
        target_arguments = (
            args.target_map, args.model_audit, args.numerical_receipt
        )
        if any(value is not None for value in target_arguments):
            if not all(value is not None for value in target_arguments):
                raise DependencyError(
                    "--target-map, --model-audit, and --numerical-receipt "
                    "must be supplied together"
                )
            target_map_path = args.target_map.resolve(strict=True)
            model_audit_path = args.model_audit.resolve(strict=True)
            numerical_receipt_path = args.numerical_receipt.resolve(
                strict=True
            )
            for label, path in (
                ("target map", target_map_path),
                ("model audit", model_audit_path),
                ("numerical receipt", numerical_receipt_path),
            ):
                if not path.is_relative_to(root):
                    raise DependencyError(f"{label} must be contained by root")
            with target_map_path.open("r", encoding="utf-8") as stream:
                target_map = json.load(stream)
            with model_audit_path.open("r", encoding="utf-8") as stream:
                audit = json.load(stream)
            with numerical_receipt_path.open("r", encoding="utf-8") as stream:
                receipt = json.load(stream)
            requirements_status = None
            if args.requirements_status is not None:
                requirements_path = args.requirements_status.resolve(
                    strict=True
                )
                if not requirements_path.is_relative_to(root):
                    raise DependencyError(
                        "requirements status must be contained by root"
                    )
                with requirements_path.open("r", encoding="utf-8") as stream:
                    requirements_status = json.load(stream)
            target_result = validate_target_certifications(
                target_map, audit, receipt, root,
                model_audit_path.relative_to(root).as_posix(),
                requirements_status,
            )
            unknown = sorted(
                set(args.require_target) - set(target_result["consumers"])
            )
            if unknown:
                raise DependencyError(
                    "unmapped target consumers fail closed: "
                    + ", ".join(unknown)
                )
            blocked = [
                consumer_id for consumer_id in args.require_target
                if target_result["consumers"][consumer_id]["release_status"]
                != "RELEASED"
            ]
            if blocked:
                details = [
                    consumer_id + " (" + ", ".join(
                        target_result["consumers"][consumer_id][
                            "blocking_model_ids"
                        ]
                    ) + ")"
                    for consumer_id in blocked
                ]
                raise DependencyError(
                    "target numerical prerequisites are not certified: "
                    + "; ".join(details)
                )
            result["target_dependencies"] = target_result
        elif args.require_target:
            raise DependencyError(
                "--require-target needs target map, audit, and receipt"
            )
        print(json.dumps(result, indent=2))
        return 0
    except (OSError, json.JSONDecodeError, DependencyError) as exc:
        print(f"DEPENDENCY ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
