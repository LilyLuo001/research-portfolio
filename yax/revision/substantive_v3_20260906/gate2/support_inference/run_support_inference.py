#!/usr/bin/env python3
"""Fail-closed Gate-2 support and inference runner.

This program consumes only authenticated occupation-month aggregates.  It is
deliberately independent of the historical within-family and direct-tail
solvers: numerical fitting is delegated to the hash-pinned A1 implementation
and every newly fitted model must pass the same extended-face, dual-solver,
profile, and fitted-Hessian certificate before any result directory is
published.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import platform
import re
import stat
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pytest
import scipy
from scipy import sparse
from scipy.sparse.linalg import spsolve
from scipy.stats import chi2, norm


HERE = pathlib.Path(__file__).resolve().parent
SPEC_PATH = HERE / "SUPPORT_INFERENCE_SPEC.json"
REVIEWED_SPEC_DIGEST = "a9ce9aad52483ebf9f77ad51ea32d54e8e81ec2950e9cec600481e507d3f482f"
EXPECTED_CANONICAL_SPEC_ID = "yaxspec_v1_83bb387f9fc28e2655db5101c7697989510475027d1dd5a9c361c797ed3925c3"
SAFE_RUN_ID_PATTERN = re.compile(r"gate2_support_inference_sge_[1-9][0-9]{0,19}\Z")
SGE_JOB_ID_PATTERN = re.compile(r"[1-9][0-9]{0,19}\Z")
SUCCESS_PUBLICATION = "CERTIFIED_RESULT_ARTIFACTS_WITH_EXPECTED_STRUCTURAL_RANK_BLOCK"
FAILURE_PUBLICATION = "NONAUTHORITATIVE_NUMERICAL_FAILURE_EVIDENCE_ONLY"
FAILURE_OUTPUT_FILES = frozenset({"FAILURE_EVIDENCE.json", "FAILURE_VALIDATION.json"})
SUCCESS_OUTPUT_FILES = frozenset({
    "A1_PROFILE_CHECKPOINTS.csv", "CENTERED_TARGET_DRAWS.npz", "COMMON_DRAW_BINDING.json",
    "COMMON_MULTIPLIERS.npz", "CONTINUOUS_WITHIN_FAMILY.json",
    "DIRECT_AGGREGATE_FAMILY_INFLUENCE.csv", "DIRECT_AGGREGATE_INFLUENCE_CLOSURE.json",
    "DIRECT_AGGREGATE_OCCUPATION_INFLUENCE.csv", "DIRECT_TAIL_COVARIANCE.csv",
    "DIRECT_TAIL_ESTIMATES.csv", "DIRECT_TAIL_FUNCTIONALS.csv", "EXECUTION_PROVENANCE.json",
    "FAMILY_INFLUENCE.csv", "FAMILY_INFORMATION.csv", "FAMILY_QUINTILE_PATHS_QUARTERLY.csv",
    "HETEROGENEITY_CENTERED_DRAWS.npz", "HETEROGENEITY_JOINT_TESTS.json",
    "INFORMATION_DIAGNOSTICS.csv", "MODEL_CATALOG.json", "MODEL_FAILURES.json",
    "NUMERICAL_MODEL_AUDITS.json", "NUMERICAL_PROFILE_ROWS.csv", "NUMERICAL_SOLVER_ROWS.csv",
    "NUMERICAL_STATE_SOURCES.json", "NUMERICAL_TRAJECTORIES.json", "OCCUPATION_INFLUENCE.csv",
    "OCCUPATION_INFORMATION.csv", "PAIRWISE_AGGREGATES.csv",
    "PAIRWISE_AGGREGATE_COVARIANCE.csv", "PAIRWISE_AGGREGATE_FUNCTIONALS.csv",
    "PATH_SELECTION.json", "PROFILE_COVARIANCE.csv", "PROFILE_ESTIMATES.csv",
    "PROFILE_INTERVALS.csv", "PROFILE_JOINT_TESTS.json", "RAW_FAMILY_QUINTILE_PATHS_MONTHLY.csv",
    "SUPPORTED_EDGE_COVARIANCE.csv", "SUPPORTED_EDGE_FUNCTIONALS.csv",
    "SUPPORTED_PAIRWISE_CONTRASTS.csv", "VALIDATION_REPORT.json",
})
VALIDATION_CHECK_KEYS = frozenset({
    "paired_covariance_identity", "cross_model_covariance_identity",
    "within_model_covariance_identity", "paired_common_draw_identity",
    "profile_common_draws_and_difference", "profile_point_estimate_labels_and_identity",
    "profile_interval_recomputation", "fresh_a1_checkpoint", "fresh_a1_certificates",
    "fresh_two_sided_profiles", "fresh_dual_candidate_fitted_hessians",
    "primary_state_source", "transition_excluded_from_quarterly_estimation",
    "missing_month_blank", "authenticated_edge_functional_reconstruction",
    "edge_functional_covariance_influence_draw_closure",
    "expected_structural_edge_rank_block", "authenticated_direct_functional_reconstruction",
    "direct_functional_covariance_influence_draw_closure",
    "direct_aggregate_influence_identity", "authenticated_pairwise_aggregate_reconstruction",
    "influence_score_closure::pooled", "influence_score_closure::family_month",
    "influence_score_closure::family_heterogeneous_supported",
    "influence_score_closure::direct_tail_four_family",
    "influence_score_closure::continuous_raw_beta_family_month",
})
MAX_AUTHORIZATION_LIFETIME = timedelta(hours=24)
MAX_AUTHORIZATION_ISSUE_AGE = timedelta(hours=24)
EXPECTED_PYTHON_RESOLVED_SHA256 = (
    "0887a2530329cef5a3a6b7c83c76590da9730f98f1e68497096bc05f20b92aa7"
)
EXPECTED_PYTHON_VERSION = "3.13.8"
EXPECTED_GIT_PATH = pathlib.Path("/usr/bin/git")
EXPECTED_GIT_SHA256 = (
    "507917bbb5d24123c8e11df46df1d32483da1ce6420aa7ba7dd17de8ccd13a9e"
)
EXPECTED_GIT_VERSION = "git version 2.43.7"
EXPECTED_A1_RUNTIME_PAYLOAD_SHA256 = (
    "8003414233a40768089a6c584b3ecc4e3a1de9ca89c1c0b6cf5c5810024f7f79"
)
SANITIZED_GIT_ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
IMPORT_AFFECTING_ENVIRONMENT = (
    "PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE", "PYTHONSTARTUP",
)
PRE_EXECUTION_AUTHORIZATION_SCHEMA = (
    "yax-gate2-support-inference-pre-execution-authorization-v2"
)
PRE_EXECUTION_AUTHORIZATION_STATUS = (
    "AUTHORIZED_FRESH_GATE2_SUPPORT_INFERENCE_EXECUTION"
)
RUNNER_REL = pathlib.Path(
    "yax/revision/substantive_v3_20260906/gate2/support_inference/run_support_inference.py"
)
SPEC_REL = pathlib.Path(
    "yax/revision/substantive_v3_20260906/gate2/support_inference/SUPPORT_INFERENCE_SPEC.json"
)
AUTHORIZATION_REL = pathlib.Path(
    "yax/revision/substantive_v3_20260906/gate2/support_inference/"
    "PRE_EXECUTION_AUTHORIZATION.json"
)
COMMAND_PATH_ARGUMENTS = (
    "canonical_spec", "a1_spec", "a1_runner", "a1_model_audit",
    "a1_dependency_release", "cells", "cells_receipt", "fixed_membership",
    "support_matrix", "support_edges", "direct_tail_membership",
    "pre_execution_authorization", "output_parent",
)
SINGLE_USE_SEMANTICS = (
    "ONE_AUTHORIZATION_FOR_ONE_SGE_JOB_ID_RUN_ID_AND_OUTPUT_PARENT; "
    "RETAINED_SIBLING_LOCKS_PREVENT_OUTPUT_LEAF_REUSE"
)
_PUBLICATION_CAPABILITY_SENTINEL = object()


class Blocked(RuntimeError):
    """A contract or numerical condition failed; no claims may be emitted."""


class NumericalCertificationFailure(Blocked):
    def __init__(self, message: str, evidence: dict[str, Any]):
        self.evidence = evidence
        super().__init__(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def content_id(prefix: str, value: Any, excluded_keys: Iterable[str] = ()) -> str:
    if not isinstance(value, dict):
        raise Blocked("content-derived identity requires an object")
    excluded = set(excluded_keys)
    payload = {key: item for key, item in value.items() if key not in excluded}
    return f"{prefix}_{hashlib.sha256(canonical_bytes(payload)).hexdigest()}"


def sanitized_resolved_path_identity(path: pathlib.Path) -> dict[str, Any]:
    try:
        resolved = path.expanduser().resolve(strict=True)
        state = os.lstat(resolved)
    except OSError as error:
        raise Blocked("command path cannot be resolved for run binding") from error
    return {"resolved_path_sha256": hashlib.sha256(
                os.fsencode(resolved)).hexdigest(),
            "device": int(state.st_dev), "inode": int(state.st_ino)}


def build_run_identity(args: argparse.Namespace) -> dict[str, Any]:
    job_id = os.environ.get("JOB_ID")
    if not isinstance(job_id, str) or SGE_JOB_ID_PATTERN.fullmatch(job_id) is None:
        raise Blocked("production publication requires a positive numeric SGE JOB_ID")
    expected_run_id = f"gate2_support_inference_sge_{job_id}"
    if args.run_id != expected_run_id:
        raise Blocked("run_id suffix does not exactly equal SGE JOB_ID")
    output_parent = getattr(args, "output_parent", None)
    if not isinstance(output_parent, pathlib.Path) or output_parent.is_symlink() or not output_parent.is_dir():
        raise Blocked("output parent must be an existing direct directory")
    output_parent_identity = sanitized_resolved_path_identity(output_parent)
    canonical_arguments = []
    for name in COMMAND_PATH_ARGUMENTS:
        value = getattr(args, name, None)
        if not isinstance(value, pathlib.Path):
            raise Blocked("canonical command binding requires every path argument")
        canonical_arguments.append({
            "flag": "--" + name.replace("_", "-"),
            "value_kind": "SANITIZED_RESOLVED_PATH_IDENTITY",
            "value": sanitized_resolved_path_identity(value),
        })
    canonical_arguments.append({"flag": "--run-id", "value_kind": "LITERAL_RUN_ID",
                                "value": args.run_id})
    command_binding = {
        "schema_version": "yax-gate2-support-command-binding-v1",
        "python_invocation": "<YAX_PYTHON_BIN> -I <HASH_PINNED_RUNNER>",
        "runner_sha256": sha256_file(pathlib.Path(__file__).resolve()),
        "canonical_sanitized_argv": canonical_arguments,
    }
    command_binding["command_binding_sha256"] = hashlib.sha256(
        canonical_bytes(command_binding)).hexdigest()
    value = {"schema_version": "yax-gate2-support-run-identity-v1",
             "status": "BOUND_NUMERIC_SGE_JOB_COMMAND_AND_OUTPUT_PARENT",
             "sge_job_id": job_id, "intended_run_id": args.run_id,
             "output_parent_identity": output_parent_identity,
             "command_binding": command_binding,
             "single_use_semantics": SINGLE_USE_SEMANTICS}
    value["run_identity_id"] = content_id(
        "yaxgate2runidentity_v1", value, ("run_identity_id",))
    return value


def issue_publication_capability(args: argparse.Namespace,
                                 provenance: dict[str, Any]) -> None:
    run_identity = getattr(args, "run_identity", None)
    if (not isinstance(run_identity, dict) or not isinstance(provenance, dict) or
            provenance.get("run_identity") != run_identity or
            run_identity.get("run_identity_id") != content_id(
                "yaxgate2runidentity_v1", run_identity, ("run_identity_id",)) or
            provenance.get("provenance_id") != content_id(
                "yaxgate2provenance_v1", provenance, ("provenance_id",))):
        raise Blocked("publication capability requires exact authenticated run provenance")
    args._publication_capability = (
        _PUBLICATION_CAPABILITY_SENTINEL,
        run_identity["run_identity_id"], provenance["provenance_id"])


def verify_publication_capability(args: argparse.Namespace,
                                  run_identity: dict[str, Any],
                                  provenance: dict[str, Any]) -> None:
    capability = getattr(args, "_publication_capability", None)
    if (not isinstance(capability, tuple) or len(capability) != 3 or
            capability[0] is not _PUBLICATION_CAPABILITY_SENTINEL or
            capability[1] != run_identity.get("run_identity_id") or
            capability[2] != provenance.get("provenance_id")):
        raise Blocked("publication lacks the in-process authenticated main capability")


def validate_frozen_spec(spec: dict[str, Any]) -> None:
    expected = content_id("yaxgate2spec_v1", spec, ("spec_id",))
    if spec.get("spec_id") != expected:
        raise Blocked("support-inference spec_id is not its canonical content identity")
    reviewed_payload = {key: value for key, value in spec.items()
                        if key not in {"spec_id", "implementation_sha256"}}
    observed_reviewed_digest = hashlib.sha256(canonical_bytes(reviewed_payload)).hexdigest()
    if observed_reviewed_digest != REVIEWED_SPEC_DIGEST:
        raise Blocked("support-inference spec differs from hardcoded reviewed contract digest")
    if spec.get("implementation_sha256") != sha256_file(pathlib.Path(__file__)):
        raise Blocked("support-inference implementation hash differs from executing runner")
    expected_behavior = {
        "likelihood": "grouped_binomial_young_given_young_plus_older",
        "probability_clipping": False,
        "pseudocount": False,
        "penalty": False,
        "fixed_membership": True,
        "family_fixed_effect_partition": "family_by_calendar_month",
        "post_start": "2023-01",
        "pre_end": "2022-11",
        "static_transition_exclusion": "2022-12",
        "missing_month": "2025-10",
        "resampling_unit": "occupation",
        "multiplier_distribution": "Rademacher {-1,+1}",
        "multiplier_draws": 9999,
        "multiplier_seed": 2026090521,
        "finite_cluster_correction": "G/(G-1)",
        "primary_estimate_path": "trust-path",
        "reference_estimate_path": "independent-damped-sparse-newton-irls",
    }
    if spec.get("signed_behavior") != expected_behavior:
        raise Blocked("signed behavior contract differs from implemented estimands")
    if spec.get("status") != "FROZEN_PRE_RESULT_DESIGN" or spec.get(
            "canonical_spec_id") != EXPECTED_CANONICAL_SPEC_ID:
        raise Blocked("spec status or canonical-spec binding differs from reviewed contract")
    if spec.get("calendar") != {
        "range": ["2017-01", "2026-07"], "missing_month": expected_behavior["missing_month"],
        "static_transition_exclusion": expected_behavior["static_transition_exclusion"],
        "post_start": expected_behavior["post_start"], "pre_end": expected_behavior["pre_end"]}:
        raise Blocked("calendar duplicates do not equal signed behavior")
    inference = spec.get("inference", {})
    if (inference.get("draws"), inference.get("seed"), inference.get("distribution"),
        inference.get("finite_cluster_correction")) != (
            expected_behavior["multiplier_draws"], expected_behavior["multiplier_seed"],
            expected_behavior["multiplier_distribution"], expected_behavior["finite_cluster_correction"]):
        raise Blocked("inference duplicates do not equal signed behavior")
    if spec.get("direct_tail", {}).get("families") != ["27", "29", "31", "41"]:
        raise Blocked("direct-tail family definition differs from reviewed contract")
    if spec.get("expected_counts") != {"occupations": 468, "observed_months": 114,
            "estimation_months": 113, "support_matrix_rows": 110,
            "supported_cells": 72, "support_edges": 89, "direct_tail_occupations": 29}:
        raise Blocked("expected-count contract differs from reviewed values")
    publication = spec.get("publication", {})
    if (publication.get("occupation_by_month_output_forbidden") is not True or
            publication.get("overwrite") is not False or
            publication.get("atomic_directory_visibility_claimed") is not False or
            publication.get("gpfs_ordinary_rename_fallback_used") is not False or
            publication.get("run_id_pattern") !=
            "gate2_support_inference_sge_<positive scheduler job number>" or
            publication.get("output_location") !=
            "existing direct directory outside Git repository and disjoint from every authenticated input" or
            publication.get("sge_run_binding") !=
            "run_id is gate2_support_inference_sge_<JOB_ID> for the positive numeric scheduler JOB_ID" or
            publication.get("automatic_path_cleanup") is not False or
            publication.get("retention_policy") !=
            "close descriptors but retain sibling lock and private staging on success and failure; manual inode-audited operator cleanup only; retained leaves consume quota" or
            publication.get("policy") !=
            "hash-pinned A1 reservation type with local no-unlink descriptor-bound reservation; exclusively mkdir final 0700 leaf; O_DIRECTORY|O_NOFOLLOW descriptor-relative hard links; verify expected inode, byte count, and SHA-256 after every link and for every artifact again after receipt; receipt linked last as commit marker" or
            publication.get("numerical_evidence_redaction") !=
            "typed occupation-month redaction covers explicit keys, composite labels, general-recession counts and row indices, and strict-boundary index-margin alignments" or
            publication.get("post_commit_stdout_required") is not False or
            publication.get("public_frame_field_closure") != [
                "SUPPORTED_PAIRWISE_CONTRASTS.csv",
                "SUPPORTED_EDGE_FUNCTIONALS.csv",
                "DIRECT_TAIL_ESTIMATES.csv",
                "DIRECT_TAIL_FUNCTIONALS.csv",
                "PAIRWISE_AGGREGATES.csv",
                "PAIRWISE_AGGREGATE_FUNCTIONALS.csv",
            ]):
        raise Blocked("publication guards differ from reviewed contract")
    if spec.get("outputs") != {
            "publication_kind_enum": [SUCCESS_PUBLICATION, FAILURE_PUBLICATION],
            "success_files": sorted(SUCCESS_OUTPUT_FILES),
            "failure_files": sorted(FAILURE_OUTPUT_FILES),
            "validation_check_keys": sorted(VALIDATION_CHECK_KEYS)}:
        raise Blocked("exact publication enum or inventory differs from implementation")
    if spec.get("structural_inference") != {
            "supported_cell_count": 72, "family_count": 22,
            "edge_restriction_count": 89, "edge_functional_rank": 50,
            "edge_covariance_maximum_rank": 50,
            "further_covariance_rank_deficiency_rule": "disclose 50 minus observed covariance rank",
            "full_edge_joint_test": "BLOCKED_RANK_DEFICIENT_JOINT_TEST_WITHOUT_CHI2_OR_P_VALUE"}:
        raise Blocked("structural-rank contract differs from reviewed values")
    if spec.get("runtime_and_authorization") != {
            "status_at_freeze": "PENDING_EXACT_CLEAN_IMPLEMENTATION_COMMIT_AND_SEPARATE_AUTHORIZATION_COMMIT",
            "python_invocation": "-I", "python_version": EXPECTED_PYTHON_VERSION,
            "python_resolved_executable_sha256": EXPECTED_PYTHON_RESOLVED_SHA256,
            "git_version": EXPECTED_GIT_VERSION,
            "git_resolved_executable_sha256": EXPECTED_GIT_SHA256,
            "a1_runtime_payload_sha256": EXPECTED_A1_RUNTIME_PAYLOAD_SHA256,
            "a1_artifact_safety_sha256": "6c03ad94fb5d4ecb618e3cd0e4f9de6ece0a5f20e633283002f3fc01d1248fd2",
            "runtime_verification_order": "hash-pinned A1 execution_runtime_authentication and verify_runtime_contract plus independent payload reconstruction and NumPy-2.5-vstack probe before opening aggregate cells",
            "authorization_schema_version": PRE_EXECUTION_AUTHORIZATION_SCHEMA,
            "authorization_status": PRE_EXECUTION_AUTHORIZATION_STATUS,
            "authorization_relative_path": str(AUTHORIZATION_REL),
            "authorization_commit_rule": "time-limited authorization is the sole changed file in HEAD whose parent is the exact clean implementation commit",
            "run_binding": "positive numeric SGE JOB_ID exactly equals run_id suffix; canonical sanitized argv and output-parent path hash/device/inode are authorization-bound and revalidated",
            "single_use_semantics": SINGLE_USE_SEMANTICS,
            "maximum_authorization_lifetime_hours": 24,
            "maximum_authorization_issue_age_hours": 24}:
        raise Blocked("runtime/authorization contract differs from reviewed values")
    if spec.get("requirement_scope", {}).get("S05") != "UNRESOLVED_OUT_OF_SCOPE" or spec.get(
            "requirement_scope", {}).get("L01") != "UNRESOLVED_OUT_OF_SCOPE":
        raise Blocked("out-of-scope requirement disposition changed")


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_run(repo: pathlib.Path, arguments: list[str], *, text: bool = False):
    return subprocess.run(
        [str(EXPECTED_GIT_PATH), *arguments], cwd=repo,
        env=SANITIZED_GIT_ENVIRONMENT, text=text, capture_output=True, check=False,
    )


def execution_runtime_authentication() -> dict[str, Any]:
    if any(os.environ.get(name) for name in IMPORT_AFFECTING_ENVIRONMENT):
        raise Blocked("import-affecting Python environment variables are forbidden")
    if (sys.flags.isolated != 1 or sys.flags.ignore_environment != 1 or
            sys.flags.no_user_site != 1 or not bool(getattr(sys.flags, "safe_path", False))):
        raise Blocked("production Python must be invoked with -I isolated mode")
    if os.environ.get("OMP_NUM_THREADS") != "1":
        raise Blocked("OMP_NUM_THREADS=1 is required")
    try:
        python_path = pathlib.Path(sys.executable).resolve(strict=True)
    except OSError as error:
        raise Blocked("Python executable cannot be resolved") from error
    python_hash = sha256_file(python_path)
    if python_hash != EXPECTED_PYTHON_RESOLVED_SHA256 or platform.python_version() != EXPECTED_PYTHON_VERSION:
        raise Blocked("Python executable/version differs from the pinned runtime")
    if not EXPECTED_GIT_PATH.is_file() or EXPECTED_GIT_PATH.is_symlink():
        raise Blocked("pinned Git executable is absent or indirect")
    git_hash = sha256_file(EXPECTED_GIT_PATH)
    completed = subprocess.run(
        [str(EXPECTED_GIT_PATH), "--version"], env=SANITIZED_GIT_ENVIRONMENT,
        text=True, capture_output=True, check=False,
    )
    if (git_hash != EXPECTED_GIT_SHA256 or completed.returncode != 0 or
            completed.stdout.strip() != EXPECTED_GIT_VERSION):
        raise Blocked("Git executable/version differs from the pinned runtime")
    return {
        "status": "AUTHENTICATED_ISOLATED_PINNED_EXECUTABLES",
        "python_invocation": "<YAX_PYTHON_BIN>",
        "python_resolved_executable_sha256": python_hash,
        "python_version": platform.python_version(), "isolated_mode": True,
        "ignore_environment": True, "no_user_site": True, "safe_path": True,
        "git_invocation": "<YAX_GIT_BIN>",
        "git_resolved_executable_sha256": git_hash,
        "git_version": EXPECTED_GIT_VERSION,
        "import_affecting_environment_absent": True, "omp_num_threads": "1",
    }


def independent_runtime_payload() -> dict[str, Any]:
    libc_name, libc_version = platform.libc_ver()
    return {"architecture": platform.machine(),
            "libc": {"name": libc_name, "version": libc_version},
            "packages": {"numpy": np.__version__, "pandas": pd.__version__,
                         "pytest": pytest.__version__, "scipy": scipy.__version__},
            "python_compiler": platform.python_compiler(),
            "python_implementation": platform.python_implementation(),
            "python_version": platform.python_version()}


def numpy_2_5_structural_probe(analysis: dict[str, Any]) -> dict[str, Any]:
    expected_version = analysis.get("software", {}).get("runtime_contract", {}).get(
        "payload", {}).get("packages", {}).get("numpy")
    left = np.asarray([[1.0, 2.0]])
    right = np.asarray([[3.0, 4.0]])
    stacked = np.vstack((left, right))
    if (expected_version != "2.5.1" or np.__version__ != expected_version or
            stacked.shape != (2, 2) or stacked.dtype != np.dtype("float64") or
            not np.array_equal(stacked, np.asarray([[1.0, 2.0], [3.0, 4.0]]))):
        raise Blocked("NumPy 2.5 vstack structural/runtime probe failed")
    return {"status": "PASS_NUMPY_2_5_VSTACK_STRUCTURAL_PROBE",
            "numpy_version": np.__version__, "constructor": "numpy.vstack",
            "shape": [2, 2], "dtype": stacked.dtype.str,
            "value_sha256": array_sha256(stacked)}


def verify_signed_a1_runtime_contract(a1, analysis: dict[str, Any]) -> dict[str, Any]:
    try:
        a1_execution_runtime = a1.execution_runtime_authentication()
        a1_verification = a1.verify_runtime_contract(analysis)
    except Exception as error:
        raise Blocked("hash-pinned A1 runtime-contract verification failed") from error
    observed = independent_runtime_payload()
    observed_hash = hashlib.sha256(canonical_bytes(observed)).hexdigest()
    expected = analysis.get("software", {}).get("runtime_contract", {})
    independent_execution_runtime = execution_runtime_authentication()
    if (a1_execution_runtime != independent_execution_runtime or
            observed != expected.get("payload") or
            observed_hash != expected.get("payload_sha256") or
            observed_hash != EXPECTED_A1_RUNTIME_PAYLOAD_SHA256 or
            a1_verification.get("payload") != observed or
            a1_verification.get("payload_sha256") != observed_hash):
        raise Blocked("independent runtime payload differs from signed A1 runtime contract")
    probe = numpy_2_5_structural_probe(analysis)
    return {"status": "PASS_A1_AND_INDEPENDENT_RUNTIME_CONTRACT",
            "signed_runtime_contract": expected,
            "hash_pinned_a1_execution_runtime_authentication": a1_execution_runtime,
            "independent_execution_runtime_authentication": independent_execution_runtime,
            "hash_pinned_a1_verification": a1_verification,
            "independently_recomputed_payload": observed,
            "independently_recomputed_payload_sha256": observed_hash,
            "numpy_structural_probe": probe}


def repository_root() -> pathlib.Path:
    result = subprocess.run(
        [str(EXPECTED_GIT_PATH), "-C", str(HERE), "rev-parse", "--show-toplevel"],
        env=SANITIZED_GIT_ENVIRONMENT, text=True, capture_output=True, check=False,
    )
    if result.returncode != 0:
        raise Blocked("support-inference repository root cannot be resolved")
    return pathlib.Path(result.stdout.strip()).resolve(strict=True)


def expected_pre_execution_authorization_id(document: dict[str, Any]) -> str:
    return content_id("yaxgate2supportauth_v2", document, ("authorization_id",))


def validate_authorization_window(
        document: dict[str, Any], now: datetime | None = None
) -> tuple[datetime, datetime, datetime, timedelta]:
    try:
        issued = datetime.fromisoformat(str(document["issued_at_utc"]).replace("Z", "+00:00"))
        not_before = datetime.fromisoformat(str(document["not_before_utc"]).replace("Z", "+00:00"))
        not_after = datetime.fromisoformat(str(document["not_after_utc"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError) as error:
        raise Blocked("pre-execution authorization timestamps are invalid") from error
    observed_now = datetime.now(timezone.utc) if now is None else now
    if any(value.tzinfo is None for value in (issued, not_before, not_after, observed_now)):
        raise Blocked("pre-execution authorization timestamps are invalid")
    lifetime = not_after-not_before
    issue_age = observed_now-issued
    if (not (issued <= not_before <= observed_now <= not_after) or
            not timedelta(0) < lifetime <= MAX_AUTHORIZATION_LIFETIME or
            not timedelta(0) <= issue_age <= MAX_AUTHORIZATION_ISSUE_AGE):
        raise Blocked("execution is outside the authorized time window")
    return issued, not_before, not_after, lifetime


def validate_authorized_run_binding(document: dict[str, Any],
                                    run_identity: dict[str, Any]) -> None:
    if (document.get("intended_run_id") != run_identity.get("intended_run_id") or
            document.get("sge_job_id") != run_identity.get("sge_job_id") or
            document.get("output_parent_identity") !=
            run_identity.get("output_parent_identity") or
            document.get("command_binding") != run_identity.get("command_binding") or
            document.get("single_use_semantics") != SINGLE_USE_SEMANTICS):
        raise Blocked("pre-execution authorization run binding differs")


def validate_pre_execution_authorization(
        path: pathlib.Path, repo: pathlib.Path, spec: dict[str, Any],
        run_identity: dict[str, Any]) -> dict[str, Any]:
    expected_path = (repo / AUTHORIZATION_REL).resolve(strict=False)
    if path.resolve(strict=False) != expected_path or not path.is_file() or path.is_symlink():
        raise Blocked("support-specific pre-execution authorization is absent, indirect, or misplaced")
    document = read_json(path)
    exact_fields = {"schema_version", "status", "authorization_id", "issued_at_utc",
                    "not_before_utc", "not_after_utc", "authorized_implementation_commit",
                    "canonical_spec", "source_registry_sha256", "modules",
                    "intended_run_id", "sge_job_id", "output_parent_identity",
                    "command_binding", "single_use_semantics"}
    if set(document) != exact_fields:
        raise Blocked("pre-execution authorization field set is not exact")
    if (document.get("schema_version") != PRE_EXECUTION_AUTHORIZATION_SCHEMA or
            document.get("status") != PRE_EXECUTION_AUTHORIZATION_STATUS or
            document.get("authorization_id") != expected_pre_execution_authorization_id(document)):
        raise Blocked("pre-execution authorization identity is invalid")
    issued, not_before, not_after, lifetime = validate_authorization_window(document)
    validate_authorized_run_binding(document, run_identity)
    expected_registry = hashlib.sha256(canonical_bytes(spec["authenticated_inputs"])).hexdigest()
    expected_modules = {"support_inference": {
        "typed_spec_id": spec["spec_id"], "typed_spec_sha256": sha256_file(SPEC_PATH),
        "code_sha256": sha256_file(pathlib.Path(__file__).resolve())}}
    expected_canonical = {"id": spec["canonical_spec_id"],
                          "sha256": spec["authenticated_inputs"]["canonical_spec"]["sha256"]}
    if (document.get("canonical_spec") != expected_canonical or
            document.get("source_registry_sha256") != expected_registry or
            document.get("modules") != expected_modules):
        raise Blocked("pre-execution authorization bindings differ")
    head_result = git_run(repo, ["rev-parse", "HEAD"], text=True)
    tree_result = git_run(repo, ["rev-parse", "HEAD^{tree}"], text=True)
    status_result = git_run(repo, ["status", "--porcelain=v1", "--untracked-files=all"], text=True)
    if (head_result.returncode != 0 or tree_result.returncode != 0 or
            status_result.returncode != 0 or status_result.stdout != ""):
        raise Blocked("repository must be at a clean committed HEAD")
    head, tree = head_result.stdout.strip(), tree_result.stdout.strip()
    implementation = document.get("authorized_implementation_commit")
    if (not isinstance(implementation, str) or not re.fullmatch(r"[0-9a-f]{40}", implementation) or
            implementation == head):
        raise Blocked("authorized implementation commit is invalid")
    ancestor = git_run(repo, ["merge-base", "--is-ancestor", implementation, head])
    committed_auth = git_run(repo, ["show", f"{head}:{AUTHORIZATION_REL}"])
    last_commit = git_run(repo, ["log", "-1", "--format=%H", "--", str(AUTHORIZATION_REL)], text=True)
    parent = git_run(repo, ["rev-parse", "HEAD^"], text=True)
    changed = git_run(repo, ["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], text=True)
    committed_runner = git_run(repo, ["show", f"{head}:{RUNNER_REL}"])
    committed_spec = git_run(repo, ["show", f"{head}:{SPEC_REL}"])
    if (ancestor.returncode != 0 or committed_auth.returncode != 0 or
            committed_auth.stdout != path.read_bytes() or last_commit.returncode != 0 or
            last_commit.stdout.strip() != head or parent.returncode != 0 or
            parent.stdout.strip() != implementation or changed.returncode != 0 or
            changed.stdout.splitlines() != [str(AUTHORIZATION_REL)] or
            committed_runner.returncode != 0 or committed_runner.stdout != pathlib.Path(__file__).read_bytes() or
            committed_spec.returncode != 0 or committed_spec.stdout != SPEC_PATH.read_bytes()):
        raise Blocked("authorization is not the sole file in a separate current commit")
    return {"schema_version": PRE_EXECUTION_AUTHORIZATION_SCHEMA,
            "status": PRE_EXECUTION_AUTHORIZATION_STATUS,
            "authorization_id": document["authorization_id"],
            "authorization_file_sha256": sha256_file(path),
            "authorization_git_commit": head,
            "authorized_implementation_commit": implementation,
            "issued_at_utc": document["issued_at_utc"],
            "not_before_utc": document["not_before_utc"],
            "not_after_utc": document["not_after_utc"],
            "maximum_authorization_lifetime_hours": 24,
            "maximum_authorization_issue_age_hours": 24,
            "observed_authorization_lifetime_seconds": lifetime.total_seconds(),
            "run_identity": run_identity,
            "module_key": "support_inference", "typed_spec_id": spec["spec_id"],
            "typed_spec_sha256": sha256_file(SPEC_PATH),
            "code_sha256": sha256_file(pathlib.Path(__file__).resolve()),
            "source_registry_sha256": expected_registry,
            "git_head": head, "git_tree": tree, "repository_clean": True}


def authenticated_input_hashes(args: argparse.Namespace) -> dict[str, str]:
    paths = {"canonical_spec": args.canonical_spec, "a1_spec": args.a1_spec,
             "a1_runner": args.a1_runner, "a1_model_audit": args.a1_model_audit,
             "a1_dependency_release": args.a1_dependency_release, "aggregate_cells": args.cells,
             "cells_receipt": args.cells_receipt, "fixed_membership": args.fixed_membership,
             "support_matrix": args.support_matrix, "support_edges": args.support_edges,
             "direct_tail_membership": args.direct_tail_membership}
    return {label: sha256_file(path) for label, path in sorted(paths.items())}


def execution_provenance(args: argparse.Namespace, spec: dict[str, Any],
                         cells_receipt: dict[str, Any],
                         runtime_contract: dict[str, Any]) -> dict[str, Any]:
    current_run_identity = build_run_identity(args)
    if current_run_identity != getattr(args, "run_identity", None):
        raise Blocked("SGE job, canonical command, or output-parent identity changed")
    runtime = execution_runtime_authentication()
    if (runtime_contract.get("status") != "PASS_A1_AND_INDEPENDENT_RUNTIME_CONTRACT" or
            runtime_contract.get("independently_recomputed_payload_sha256") !=
            EXPECTED_A1_RUNTIME_PAYLOAD_SHA256 or runtime_contract.get(
                "numpy_structural_probe", {}).get("status") !=
            "PASS_NUMPY_2_5_VSTACK_STRUCTURAL_PROBE"):
        raise Blocked("execution provenance lacks the signed and independent runtime verification")
    if cells_receipt.get("runtime_payload_sha256") != EXPECTED_A1_RUNTIME_PAYLOAD_SHA256:
        raise Blocked("authenticated cells receipt differs from the pinned A1 runtime payload")
    expected_upstream_runtime = {
        "status": "AUTHENTICATED_ISOLATED_PINNED_EXECUTABLES",
        "python_invocation": "<YAX_PYTHON_BIN>",
        "python_resolved_executable_sha256": EXPECTED_PYTHON_RESOLVED_SHA256,
        "python_version": EXPECTED_PYTHON_VERSION, "isolated_mode": True,
        "ignore_environment": True, "no_user_site": True, "safe_path": True,
        "git_invocation": "<YAX_GIT_BIN>",
        "git_resolved_executable_sha256": EXPECTED_GIT_SHA256,
        "git_version": EXPECTED_GIT_VERSION,
        "import_affecting_environment_absent": True}
    if cells_receipt.get("execution_runtime_authentication") != expected_upstream_runtime:
        raise Blocked("authenticated cells receipt runtime contract differs from pinned A1 runtime")
    repo = repository_root()
    authorization = validate_pre_execution_authorization(
        args.pre_execution_authorization, repo, spec, current_run_identity)
    observed_hashes = authenticated_input_hashes(args)
    expected_hashes = {key: row["sha256"] for key, row in spec["authenticated_inputs"].items()}
    if observed_hashes != expected_hashes:
        raise Blocked("execution provenance input registry differs from frozen authenticated inputs")
    value = {"schema_version": "yax-gate2-support-inference-execution-provenance-v1",
             "status": "PASS_COMMITTED_PRE_EXECUTION_AUTHORIZATION_AND_RUNTIME_BINDING",
             "executing_runner_sha256": sha256_file(pathlib.Path(__file__).resolve()),
             "executing_spec_sha256": sha256_file(SPEC_PATH),
             "git_head": authorization["git_head"], "git_tree": authorization["git_tree"],
             "repository_clean": authorization["repository_clean"],
             "execution_runtime_authentication": runtime,
             "a1_and_independent_runtime_contract": runtime_contract,
             "artifact_safety_binding": args.artifact_safety_evidence,
             "a1_runtime_payload_sha256": EXPECTED_A1_RUNTIME_PAYLOAD_SHA256,
             "run_identity": current_run_identity,
             "pre_execution_authorization": authorization,
             "authenticated_input_hashes": observed_hashes}
    value["provenance_id"] = content_id("yaxgate2provenance_v1", value, ("provenance_id",))
    return value


def read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise Blocked(f"invalid JSON input: {path.name}") from error
    if not isinstance(value, dict):
        raise Blocked(f"JSON root must be an object: {path.name}")
    return value


def require_file(path: pathlib.Path, expected_hash: str, label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise Blocked(f"{label} is absent or indirect")
    if sha256_file(path) != expected_hash:
        raise Blocked(f"{label} hash mismatch")


def load_a1(path: pathlib.Path, expected_artifact_safety_hash: str | None = None):
    safety_path = path.resolve(strict=True).parent / "artifact_safety.py"
    if expected_artifact_safety_hash is not None:
        require_file(safety_path, expected_artifact_safety_hash, "A1 artifact_safety")
    existing_safety = sys.modules.get("artifact_safety")
    if existing_safety is not None:
        loaded_path = pathlib.Path(getattr(existing_safety, "__file__", "")).resolve(strict=False)
        if loaded_path != safety_path.resolve(strict=True):
            raise Blocked("preloaded artifact_safety module is not the exact A1 sibling")
    else:
        safety_spec = importlib.util.spec_from_file_location("artifact_safety", safety_path)
        if safety_spec is None or safety_spec.loader is None:
            raise Blocked("A1 artifact_safety module cannot be loaded")
        safety_module = importlib.util.module_from_spec(safety_spec)
        sys.modules[safety_spec.name] = safety_module
        safety_spec.loader.exec_module(safety_module)
    spec = importlib.util.spec_from_file_location("gate2_pinned_a1", path)
    if spec is None or spec.loader is None:
        raise Blocked("A1 numerical module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify_artifact_safety_binding(a1, analysis: dict[str, Any],
                                   a1_runner_path: pathlib.Path) -> tuple[Any, dict[str, Any]]:
    module = sys.modules.get(getattr(a1.AtomicOutputLeaf, "__module__", ""))
    expected_path = a1_runner_path.resolve(strict=True).parent / "artifact_safety.py"
    expected_hash = analysis.get("software", {}).get("artifact_safety_sha256")
    if (module is None or pathlib.Path(getattr(module, "__file__", "")).resolve(strict=False) !=
            expected_path.resolve(strict=True) or not isinstance(expected_hash, str) or
            sha256_file(expected_path) != expected_hash or
            a1.OutputSafetyError is not module.OutputSafetyError or
            a1.AtomicOutputLeaf is not module.AtomicOutputLeaf):
        raise Blocked("loaded artifact_safety implementation is not the signed A1 sibling")
    return module, {"status": "PASS_HASH_PINNED_A1_ARTIFACT_SAFETY",
                    "module_sha256": expected_hash,
                    "module_relative_to_a1_runner": "artifact_safety.py",
                    "atomic_output_leaf_identity_exact": True,
                    "output_safety_error_identity_exact": True}


def observed_months(start: str = "2017-01", end: str = "2026-07",
                    missing: Iterable[str] = ("2025-10",)) -> list[str]:
    months = pd.period_range(start, end, freq="M").astype(str).tolist()
    absent = set(missing)
    return [month for month in months if month not in absent]


def validate_cells(cells: pd.DataFrame, receipt: dict[str, Any],
                   membership: pd.DataFrame) -> pd.DataFrame:
    required = {"occ_code", "month", "family", "young", "older",
                "beta_quintile", "webb_z"}
    if not required.issubset(cells.columns):
        raise Blocked("aggregate cells omit required columns")
    frame = cells.copy()
    frame["occ_code"] = frame.occ_code.astype(str).str.zfill(4)
    frame["month"] = frame.month.astype(str)
    frame["family"] = frame.family.astype(str).str.zfill(2)
    for column in ("young", "older", "webb_z"):
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    frame["beta_quintile"] = pd.to_numeric(
        frame.beta_quintile, errors="raise").astype(int)
    if not np.isfinite(frame[["young", "older", "webb_z"]].to_numpy()).all():
        raise Blocked("aggregate cells contain non-finite values")
    if (frame[["young", "older"]] < 0).any().any():
        raise Blocked("aggregate counts are negative")
    expected_months = observed_months()
    occupations = sorted(frame.occ_code.unique())
    if sorted(frame.month.unique()) != expected_months:
        raise Blocked("aggregate calendar differs from canonical calendar")
    if frame.duplicated(["occ_code", "month"]).any():
        raise Blocked("aggregate occupation-month key is not unique")
    if len(frame) != len(occupations) * len(expected_months):
        raise Blocked("aggregate cells are not a balanced observed-month grid")
    if receipt.get("status") != "PASS_FRESH_AGGREGATE_REBUILD":
        raise Blocked("cell receipt did not pass fresh rebuild")
    if receipt.get("schema_version") != "yax-numerical-cells-receipt-v1" or receipt.get(
            "aggregate_schema_version") != "yax-numerical-cells-v1":
        raise Blocked("cell receipt schema is not the signed aggregate contract")
    if int(receipt.get("occupation_count", -1)) != len(occupations):
        raise Blocked("cell receipt occupation count mismatch")
    if int(receipt.get("observed_month_count", -1)) != len(expected_months):
        raise Blocked("cell receipt month count mismatch")
    member = membership.copy()
    member["occupation_code"] = member.occupation_code.astype(str).str.zfill(4)
    member["beta_quintile"] = member.beta_quintile.astype(int)
    required_membership = {"occupation_code", "preperiod_weight", "rule_A_beta",
                           "beta_quintile", "webb_z"}
    if not required_membership.issubset(member.columns):
        raise Blocked("fixed membership omits semantic assignment fields")
    if member.duplicated("occupation_code").any() or len(member) != 468:
        raise Blocked("fixed membership occupation key/count is invalid")
    if set(member.beta_quintile) != {1, 2, 3, 4, 5}:
        raise Blocked("fixed membership quintile domain is invalid")
    if set(occupations) != set(member.occupation_code):
        raise Blocked("cell occupations differ from fixed membership")
    mapped = frame[["occ_code", "beta_quintile"]].drop_duplicates()
    check = mapped.merge(member[["occupation_code", "beta_quintile"]],
                         left_on="occ_code", right_on="occupation_code",
                         suffixes=("_cell", "_fixed"), validate="one_to_one")
    if not (check.beta_quintile_cell == check.beta_quintile_fixed).all():
        raise Blocked("cell quintiles differ from fixed membership")
    stable = frame.groupby("occ_code", as_index=False).agg(
        family_count=("family", "nunique"), webb_count=("webb_z", "nunique"),
        family=("family", "first"), webb_z=("webb_z", "first"))
    if (stable[["family_count", "webb_count"]] != 1).any().any():
        raise Blocked("family or Webb assignment changes within occupation")
    family_domain = r"(?:11|13|15|17|19|21|23|25|27|29|31|33|35|37|39|41|43|45|47|49|51|53)"
    if not stable.family.str.fullmatch(family_domain).all():
        raise Blocked("cell family is outside the signed Census major-family domain")
    semantic = stable.merge(member[["occupation_code", "webb_z"]],
                            left_on="occ_code", right_on="occupation_code",
                            suffixes=("_cell", "_fixed"), validate="one_to_one")
    if not np.allclose(semantic.webb_z_cell, semantic.webb_z_fixed,
                       rtol=0, atol=1e-12, equal_nan=False):
        raise Blocked("cell Webb values differ from fixed membership")
    fingerprint_payload = "".join(
        f"{row.occ_code}\t{row.family}\t{int(row.beta_quintile)}\t{float(row.webb_z).hex()}\n"
        for row in frame[["occ_code", "family", "beta_quintile", "webb_z"]]
        .drop_duplicates("occ_code").sort_values("occ_code").itertuples(index=False))
    fingerprint = hashlib.sha256(fingerprint_payload.encode("utf-8")).hexdigest()
    if fingerprint != receipt.get("assignment_fingerprint_sha256") or fingerprint != receipt.get(
            "assignment_fingerprint", {}).get("sha256"):
        raise Blocked("cell assignment fingerprint does not reproduce its receipt")
    return frame.sort_values(["occ_code", "month"], kind="mergesort").reset_index(drop=True)


def authenticate(args: argparse.Namespace, spec: dict[str, Any]) -> tuple[Any, ...]:
    inputs = spec["authenticated_inputs"]
    named = {
        "canonical_spec": args.canonical_spec,
        "a1_spec": args.a1_spec,
        "a1_runner": args.a1_runner,
        "a1_model_audit": args.a1_model_audit,
        "a1_dependency_release": args.a1_dependency_release,
        "cells_receipt": args.cells_receipt,
        "fixed_membership": args.fixed_membership,
        "support_matrix": args.support_matrix,
        "support_edges": args.support_edges,
        "direct_tail_membership": args.direct_tail_membership,
    }
    for label, path in named.items():
        require_file(path, inputs[label]["sha256"], label)
    receipt = read_json(args.cells_receipt)
    if receipt.get("canonical_spec_sha256") != inputs["canonical_spec"]["sha256"] or receipt.get(
            "fixed_membership_sha256") != inputs["fixed_membership"]["sha256"]:
        raise Blocked("cell receipt does not bind canonical spec and fixed membership")
    cells_hash = receipt.get("cells_sha256")
    if cells_hash != inputs["aggregate_cells"]["sha256"]:
        raise Blocked("cell receipt is not bound to the frozen aggregate hash")
    require_file(args.cells, cells_hash, "aggregate_cells")
    canonical = read_json(args.canonical_spec)
    a1_spec = read_json(args.a1_spec)
    a1_audit = read_json(args.a1_model_audit)
    release = read_json(args.a1_dependency_release)
    if canonical.get("spec_id") != spec["canonical_spec_id"]:
        raise Blocked("canonical spec id mismatch")
    if a1_audit.get("status") != "PASS_ALL_CORE_TARGETS_NUMERICALLY_AUDITED":
        raise Blocked("A1 model audit is not a complete pass")
    certified = {m.get("model_id") for m in a1_audit.get("models", [])
                 if m.get("a1_certification", {}).get("status") ==
                 "PASS_A1_NUMERICAL_CERTIFICATE"}
    if not {"pooled", "family_month"}.issubset(certified):
        raise Blocked("A1 pooled/family-month certificates are absent")
    consumer = release.get("target_dependencies", {}).get("consumers", {}).get(
        "gate2.static.pooled_vs_family_month", {})
    if consumer.get("release_status") != "RELEASED" or "S07" not in consumer.get(
            "downstream_requirement_ids", []):
        raise Blocked("A1 dependency release does not authorize S07")
    membership = pd.read_csv(args.fixed_membership, dtype={"occupation_code": str})
    cells = pd.read_csv(args.cells, dtype={"occ_code": str, "month": str,
                                          "family": str})
    cells = validate_cells(cells, receipt, membership)
    support = pd.read_csv(args.support_matrix, dtype={"family": str})
    edges = pd.read_csv(args.support_edges, dtype={"family": str})
    direct = pd.read_csv(args.direct_tail_membership,
                         dtype={"family": str, "occupation_code": str})
    validate_support_artifacts(cells, membership, support, edges, direct, spec)
    return canonical, a1_spec, a1_audit, membership, cells, support, edges, direct


def validate_support_artifacts(cells: pd.DataFrame, membership: pd.DataFrame,
                               support: pd.DataFrame, edges: pd.DataFrame,
                               direct: pd.DataFrame, spec: dict[str, Any]) -> None:
    if len(support) != spec["expected_counts"]["support_matrix_rows"]:
        raise Blocked("support matrix row count mismatch")
    required_support = {"family", "beta_quintile", "occupation_count",
                        "preperiod_stock", "exposure_min", "exposure_max",
                        "cell_has_support"}
    required_edges = {"family", "quintile_low", "quintile_high",
                      "low_occupation_count", "high_occupation_count",
                      "low_preperiod_stock", "high_preperiod_stock",
                      "direct_tail_edge"}
    required_direct = {"family", "beta_quintile", "occupation_code", "rule_A_beta",
                       "preperiod_stock", "within_family_quintile_preperiod_stock_share",
                       "within_direct_family_tails_preperiod_stock_share"}
    if not required_support.issubset(support.columns) or not required_edges.issubset(edges.columns):
        raise Blocked("support artifacts omit semantic columns")
    if not required_direct.issubset(direct.columns):
        raise Blocked("direct-tail artifact omits semantic columns")
    support["family"] = support.family.astype(str).str.zfill(2)
    support["beta_quintile"] = support.beta_quintile.astype(int)
    if cells.empty or not {"occ_code", "family"}.issubset(cells.columns):
        raise Blocked("semantic support validation requires authenticated cells")
    family_map = cells[["occ_code", "family"]].drop_duplicates().copy()
    family_map["occ_code"] = family_map.occ_code.astype(str).str.zfill(4)
    family_map["family"] = family_map.family.astype(str).str.zfill(2)
    if family_map.duplicated("occ_code").any():
        raise Blocked("authenticated cells do not define one family per occupation")
    expected_families = sorted(family_map.family.unique())
    if sorted(support.family.unique()) != expected_families:
        raise Blocked("support matrix family domain differs from fixed membership")
    expected_grid = {(family, q) for family in expected_families for q in range(1, 6)}
    if set(zip(support.family, support.beta_quintile)) != expected_grid:
        raise Blocked("support matrix is not the complete family-by-quintile grid")
    truth = support.cell_has_support.map(
        lambda value: str(value).strip().lower() == "true")
    if int(truth.sum()) != spec["expected_counts"]["supported_cells"]:
        raise Blocked("supported-cell count mismatch")
    if len(edges) != spec["expected_counts"]["support_edges"]:
        raise Blocked("support-edge count mismatch")
    if edges.duplicated(["family", "quintile_low", "quintile_high"]).any():
        raise Blocked("support edges are not unique")
    supported = {(str(r.family).zfill(2), int(r.beta_quintile))
                 for r in support.loc[truth].itertuples(index=False)}
    member = membership.copy()
    member["occupation_code"] = member.occupation_code.astype(str).str.zfill(4)
    member = member.merge(family_map, left_on="occupation_code", right_on="occ_code",
                          validate="one_to_one")
    member["beta_quintile"] = member.beta_quintile.astype(int)
    recomputed = member.groupby(["family", "beta_quintile"], as_index=False).agg(
        occupation_count=("occupation_code", "nunique"),
        preperiod_stock=("preperiod_weight", "sum"), exposure_min=("rule_A_beta", "min"),
        exposure_max=("rule_A_beta", "max"))
    grid = support.merge(recomputed, on=["family", "beta_quintile"], how="left",
                         suffixes=("_artifact", "_fixed"), validate="one_to_one")
    grid[["occupation_count_fixed", "preperiod_stock_fixed"]] = grid[
        ["occupation_count_fixed", "preperiod_stock_fixed"]].fillna(0)
    if not (grid.occupation_count_artifact.astype(int) == grid.occupation_count_fixed.astype(int)).all():
        raise Blocked("support occupation counts differ from fixed membership")
    if not np.allclose(grid.preperiod_stock_artifact, grid.preperiod_stock_fixed,
                       rtol=1e-12, atol=1e-6):
        raise Blocked("support stocks differ from fixed membership")
    artifact_support = grid.cell_has_support.map(lambda value: str(value).lower() == "true")
    if not np.array_equal(artifact_support.to_numpy(), grid.occupation_count_fixed.gt(0).to_numpy()):
        raise Blocked("support flag is not equivalent to positive occupation count")
    occupied = grid.occupation_count_fixed.gt(0)
    if not np.allclose(grid.loc[occupied, "exposure_min_artifact"],
                       grid.loc[occupied, "exposure_min_fixed"], rtol=0, atol=1e-12) or not np.allclose(
                       grid.loc[occupied, "exposure_max_artifact"],
                       grid.loc[occupied, "exposure_max_fixed"], rtol=0, atol=1e-12):
        raise Blocked("support exposure ranges differ from fixed membership")
    expected_edges = set()
    for family, part in support.loc[truth].groupby("family"):
        qs = sorted(part.beta_quintile.astype(int))
        expected_edges |= {(family, low, high) for i, low in enumerate(qs) for high in qs[i+1:]}
    observed_edges = set(zip(edges.family.astype(str).str.zfill(2),
                             edges.quintile_low.astype(int), edges.quintile_high.astype(int)))
    if observed_edges != expected_edges:
        raise Blocked("support edge set is not exactly all supported within-family pairs")
    lookup = support.set_index(["family", "beta_quintile"])
    for row in edges.itertuples(index=False):
        family, low, high = str(row.family).zfill(2), int(row.quintile_low), int(row.quintile_high)
        if (family, low) not in supported or (family, high) not in supported:
            raise Blocked("support edge references unsupported endpoint")
        low_cell, high_cell = lookup.loc[(family, low)], lookup.loc[(family, high)]
        if int(row.low_occupation_count) != int(low_cell.occupation_count) or int(
                row.high_occupation_count) != int(high_cell.occupation_count):
            raise Blocked("support edge occupation count differs from support matrix")
        if not np.isclose(float(row.low_preperiod_stock), float(low_cell.preperiod_stock),
                          rtol=1e-12, atol=1e-6) or not np.isclose(
                          float(row.high_preperiod_stock), float(high_cell.preperiod_stock),
                          rtol=1e-12, atol=1e-6):
            raise Blocked("support edge stock differs from support matrix")
        declared_direct = str(row.direct_tail_edge).strip().lower() == "true"
        expected_direct_flag = family in spec["direct_tail"]["families"] and low == 1 and high == 5
        if declared_direct != expected_direct_flag:
            raise Blocked("support edge direct-tail flag differs from signed definition")
    direct["family"] = direct.family.astype(str).str.zfill(2)
    direct["occupation_code"] = direct.occupation_code.astype(str).str.zfill(4)
    if sorted(direct.family.unique()) != spec["direct_tail"]["families"]:
        raise Blocked("direct-tail family set mismatch")
    if len(direct) != spec["expected_counts"]["direct_tail_occupations"]:
        raise Blocked("direct-tail occupation count mismatch")
    if set(direct.beta_quintile.astype(int)) != {1, 5}:
        raise Blocked("direct-tail membership contains a non-tail quintile")
    fixed_codes = set(membership.occupation_code.astype(str).str.zfill(4))
    if not set(direct.occupation_code).issubset(fixed_codes):
        raise Blocked("direct-tail occupations are outside fixed membership")
    expected_direct = member.loc[member.family.isin(spec["direct_tail"]["families"]) &
                                 member.beta_quintile.isin([1, 5])].copy()
    if set(direct.occupation_code) != set(expected_direct.occupation_code):
        raise Blocked("direct-tail membership is not the complete fixed Q1/Q5 subset")
    direct_check = direct.merge(expected_direct[["occupation_code", "family", "beta_quintile",
                                                  "rule_A_beta", "preperiod_weight"]],
                                on="occupation_code", suffixes=("_artifact", "_fixed"),
                                validate="one_to_one")
    if not (direct_check.family_artifact == direct_check.family_fixed).all() or not (
            direct_check.beta_quintile_artifact.astype(int) == direct_check.beta_quintile_fixed).all():
        raise Blocked("direct-tail family/quintile assignments differ from fixed membership")
    if not np.allclose(direct_check.rule_A_beta_artifact, direct_check.rule_A_beta_fixed,
                       rtol=0, atol=1e-12) or not np.allclose(
                       direct_check.preperiod_stock, direct_check.preperiod_weight,
                       rtol=1e-12, atol=1e-6):
        raise Blocked("direct-tail exposure/stock differs from fixed membership")
    by_cell = direct.groupby(["family", "beta_quintile"]).preperiod_stock.transform("sum")
    by_family = direct.groupby("family").preperiod_stock.transform("sum")
    expected_within_q = direct.preperiod_stock / by_cell
    expected_within_tail = direct.preperiod_stock / by_family
    if not np.allclose(direct.within_family_quintile_preperiod_stock_share,
                       expected_within_q, rtol=1e-12, atol=1e-12) or not np.allclose(
                       direct.within_direct_family_tails_preperiod_stock_share,
                       expected_within_tail, rtol=1e-12, atol=1e-12):
        raise Blocked("direct-tail stock shares fail semantic closure")


def _static_frame(cells: pd.DataFrame) -> pd.DataFrame:
    return cells.loc[cells.month.ne("2022-12")].sort_values(
        ["occ_code", "month"], kind="mergesort").reset_index(drop=True)


def make_bundle(a1, frame: pd.DataFrame, model_id: str,
                regressors: np.ndarray, labels: list[str],
                focal: str | None = None,
                focal_weights: np.ndarray | None = None,
                reported_targets: dict[str, np.ndarray] | None = None):
    if regressors.ndim != 2 or regressors.shape[0] != len(frame):
        raise Blocked("invalid treatment design dimensions")
    if len(labels) != regressors.shape[1] or len(set(labels)) != len(labels):
        raise Blocked("invalid treatment labels")
    return a1.ModelBundle(
        model_id=model_id, frame=frame,
        young=frame.young.to_numpy(float),
        total=(frame.young + frame.older).to_numpy(float),
        first_labels=frame.occ_code.astype(str).to_numpy(object),
        second_labels=(frame.family.astype(str) + "|" + frame.month.astype(str)).to_numpy(object),
        regressors=np.asarray(regressors, float), regressor_labels=labels,
        focal_target_label=focal or labels[0],
        focal_target_weights=focal_weights,
        reported_target_weights=reported_targets,
    )


def build_family_heterogeneous_bundle(a1, cells: pd.DataFrame,
                                      support: pd.DataFrame):
    frame = _static_frame(cells)
    post = frame.month.ge("2023-01").to_numpy(float)
    support = support.loc[support.cell_has_support.map(
        lambda x: str(x).lower() == "true")].copy()
    columns, labels = [], []
    for family, part in support.groupby("family", sort=True):
        qs = sorted(part.beta_quintile.astype(int).unique())
        reference = min(qs)
        for q in qs:
            if q == reference:
                continue
            columns.append(((frame.family.astype(str).str.zfill(2) == str(family).zfill(2)) &
                            frame.beta_quintile.eq(q)).to_numpy(float) * post)
            labels.append(f"family_{str(family).zfill(2)}:Q{q}_vs_Q{reference}_x_post")
    columns.append(frame.webb_z.to_numpy(float) * post)
    labels.append("Webb_z_x_post")
    return make_bundle(a1, frame, "family_heterogeneous_supported",
                       np.column_stack(columns), labels)


def build_direct_tail_bundle(a1, cells: pd.DataFrame, direct: pd.DataFrame):
    codes = set(direct.occupation_code.astype(str).str.zfill(4))
    frame = _static_frame(cells.loc[cells.occ_code.isin(codes)].copy())
    post = frame.month.ge("2023-01").to_numpy(float)
    columns, labels = [], []
    for family in sorted(direct.family.astype(str).str.zfill(2).unique()):
        columns.append(((frame.family.eq(family)) & frame.beta_quintile.eq(5)).to_numpy(float) * post)
        labels.append(f"family_{family}:Q5_vs_Q1_x_post")
    columns.append(frame.webb_z.to_numpy(float) * post)
    labels.append("Webb_z_x_post")
    weights = direct_weights(direct)
    aggregate = np.array([weights[label.split(":", 1)[0].split("_")[1]]
                          if label.startswith("family_") else 0.0 for label in labels])
    return make_bundle(a1, frame, "direct_tail_four_family",
                       np.column_stack(columns), labels,
                       focal="fixed_pre_stock_direct_tail_aggregate",
                       focal_weights=aggregate,
                       reported_targets={"fixed_pre_stock_direct_tail_aggregate": aggregate})


def rebuild_edge_functionals(support: pd.DataFrame, edges: pd.DataFrame,
                             coefficient_labels: list[str]) -> tuple[list[str], np.ndarray]:
    label_index = {label: index for index, label in enumerate(coefficient_labels)}
    if len(label_index) != len(coefficient_labels):
        raise Blocked("heterogeneous coefficient labels are not unique")
    labels, rows = [], []
    truth = support.cell_has_support.map(lambda value: str(value).strip().lower() == "true")
    for edge in edges.itertuples(index=False):
        family = str(edge.family).zfill(2)
        low, high = int(edge.quintile_low), int(edge.quintile_high)
        supported_q = sorted(support.loc[
            (support.family.astype(str).str.zfill(2) == family) & truth,
            "beta_quintile"].astype(int))
        if low not in supported_q or high not in supported_q:
            raise Blocked("edge reconstruction encountered unsupported endpoint")
        reference = min(supported_q)
        functional = np.zeros(len(coefficient_labels))
        if high != reference:
            key = f"family_{family}:Q{high}_vs_Q{reference}_x_post"
            if key not in label_index:
                raise Blocked("edge reconstruction lacks high-end coefficient")
            functional[label_index[key]] += 1
        if low != reference:
            key = f"family_{family}:Q{low}_vs_Q{reference}_x_post"
            if key not in label_index:
                raise Blocked("edge reconstruction lacks low-end coefficient")
            functional[label_index[key]] -= 1
        labels.append(f"family_{family}:Q{high}_vs_Q{low}")
        rows.append(functional)
    if len(labels) != 89 or len(set(labels)) != 89:
        raise Blocked("authenticated edge reconstruction did not produce 89 unique labels")
    matrix = np.vstack(rows)
    supported_cell_count = int(support.cell_has_support.map(
        lambda value: str(value).strip().lower() == "true").sum())
    family_count = int(support.family.astype(str).str.zfill(2).nunique())
    expected_rank = supported_cell_count-family_count
    rank = int(np.linalg.matrix_rank(matrix, tol=1e-12))
    if supported_cell_count != 72 or family_count != 22 or expected_rank != 50 or rank != expected_rank:
        raise Blocked("edge functional rank is not exactly 72 supported cells minus 22 families")
    return labels, matrix


def rebuild_direct_functionals(direct: pd.DataFrame,
                               coefficient_labels: list[str]) -> tuple[list[str], np.ndarray, dict[str, float]]:
    weights = direct_weights(direct)
    expected_families = sorted(weights)
    labels = [f"family_{family}:Q5_vs_Q1" for family in expected_families] + [
        "fixed_pre_stock_aggregate"]
    rows = []
    for family in expected_families:
        key = f"family_{family}:Q5_vs_Q1_x_post"
        if key not in coefficient_labels:
            raise Blocked("direct reconstruction lacks family coefficient")
        row = np.zeros(len(coefficient_labels)); row[coefficient_labels.index(key)] = 1
        rows.append(row)
    aggregate = sum(weights[family]*rows[index] for index, family in enumerate(expected_families))
    rows.append(aggregate)
    return labels, np.vstack(rows), weights


def rebuild_pairwise_aggregate_functionals(
        edges: pd.DataFrame, edge_labels: list[str], edge_matrix: np.ndarray
) -> tuple[list[str], np.ndarray, pd.DataFrame]:
    edge_index = {label: index for index, label in enumerate(edge_labels)}
    if len(edge_index) != len(edge_labels) or edge_matrix.shape[0] != len(edge_labels):
        raise Blocked("pair aggregation edge label/matrix binding is invalid")
    labels, rows, weight_rows = [], [], []
    for (low, high), part in edges.groupby(["quintile_low", "quintile_high"], sort=True):
        part = part.copy()
        part["family"] = part.family.astype(str).str.zfill(2)
        part["pair_stock"] = part.low_preperiod_stock + part.high_preperiod_stock
        if (part.pair_stock <= 0).any():
            raise Blocked("pair aggregate has a non-positive endpoint stock")
        part["weight"] = part.pair_stock / part.pair_stock.sum()
        label = f"Q{int(high)}_vs_Q{int(low)}_fixed_pair_stock"
        functional = np.zeros(edge_matrix.shape[1])
        for row in part.itertuples(index=False):
            edge_label = f"family_{row.family}:Q{int(high)}_vs_Q{int(low)}"
            if edge_label not in edge_index:
                raise Blocked("pair aggregate cannot bind an authenticated family edge")
            functional += float(row.weight)*edge_matrix[edge_index[edge_label]]
            weight_rows.append({"functional_label": label, "family": row.family,
                "quintile_low": int(low), "quintile_high": int(high),
                "family_pair_stock": float(row.pair_stock),
                "family_weight": float(row.weight), "edge_label": edge_label})
        labels.append(label); rows.append(functional)
    if len(labels) != 10 or len(set(labels)) != 10:
        raise Blocked("pairwise aggregate reconstruction did not produce ten unique pairs")
    return labels, np.vstack(rows), pd.DataFrame(weight_rows)


def weighted_family_center(values: pd.Series, family: pd.Series,
                           weights: pd.Series) -> pd.Series:
    table = pd.DataFrame({"v": values.astype(float), "g": family.astype(str),
                          "w": weights.astype(float)})
    if (table.w < 0).any() or not np.isfinite(table[["v", "w"]]).all().all():
        raise Blocked("invalid weights for family centering")
    denom = table.groupby("g").w.transform("sum")
    if (denom <= 0).any():
        raise Blocked("family has zero pre-period stock")
    means = (table.v * table.w).groupby(table.g).transform("sum") / denom
    centered = table.v - means
    closure = (centered * table.w).groupby(table.g).sum().abs().max()
    if closure > 1e-8 * max(1.0, float(table.w.sum())):
        raise Blocked("weighted family centering failed closure")
    return centered


def residualize_on_family_webb(values: pd.Series, family: pd.Series,
                               webb: pd.Series, weights: pd.Series) -> pd.Series:
    families = sorted(family.astype(str).unique())
    f = family.astype(str)
    x = np.column_stack([np.ones(len(values)),
                         *[(f == g).to_numpy(float) for g in families[1:]],
                         webb.to_numpy(float)])
    w = weights.to_numpy(float)
    gram = x.T @ (w[:, None] * x)
    rhs = x.T @ (w * values.to_numpy(float))
    if np.linalg.matrix_rank(gram) != gram.shape[0]:
        raise Blocked("family-Webb residualization design is rank deficient")
    return pd.Series(values.to_numpy(float) - x @ np.linalg.solve(gram, rhs),
                     index=values.index)


def build_continuous_bundle(a1, cells: pd.DataFrame, membership: pd.DataFrame):
    member = membership.copy()
    member["occupation_code"] = member.occupation_code.astype(str).str.zfill(4)
    frame = _static_frame(cells).merge(
        member[["occupation_code", "rule_A_beta"]], left_on="occ_code",
        right_on="occupation_code", validate="many_to_one")
    stock = frame.loc[frame.month.le("2022-11")].groupby("occ_code").apply(
        lambda x: float((x.young + x.older).sum()), include_groups=False)
    occ = frame[["occ_code", "family", "webb_z", "rule_A_beta"]].drop_duplicates("occ_code")
    occ["pre_stock"] = occ.occ_code.map(stock)
    occ["beta_centered"] = weighted_family_center(
        occ.rule_A_beta, occ.family, occ.pre_stock)
    occ["beta_residual"] = residualize_on_family_webb(
        occ.rule_A_beta, occ.family, occ.webb_z, occ.pre_stock)
    frame = frame.merge(occ[["occ_code", "pre_stock", "beta_centered", "beta_residual"]],
                        on="occ_code", validate="many_to_one")
    post = frame.month.ge("2023-01").to_numpy(float)
    x = np.column_stack([frame.beta_centered.to_numpy(float) * post,
                         frame.webb_z.to_numpy(float) * post])
    return make_bundle(a1, frame, "continuous_raw_beta_family_month", x,
                       ["raw_beta_within_family_x_post", "Webb_z_x_post"]), occ


def _disabled_legacy(*_args, **_kwargs):
    raise Blocked("historical comparator intentionally disabled")


def certification_failure(stage: str, model_id: str, message: str,
                          audit: dict[str, Any] | None = None,
                          pruning: list[dict[str, Any]] | None = None,
                          solver_rows: list[dict[str, Any]] | None = None,
                          profile_rows: list[dict[str, Any]] | None = None,
                          trajectory: dict[str, Any] | None = None,
                          state_source: dict[str, Any] | None = None,
                          error: Exception | None = None) -> NumericalCertificationFailure:
    evidence = {"schema_version": "yax-gate2-nonauthoritative-failure-evidence-v1",
                "publication_class": "NONAUTHORITATIVE_NUMERICAL_FAILURE_EVIDENCE_ONLY",
                "scientific_result_claims": False, "model_id": model_id, "failure_stage": stage,
                "message": message, "audit": audit, "profiled_face_rows": pruning or [],
                "solver_rows": solver_rows or [], "profile_rows": profile_rows or [],
                "trajectory": trajectory or {}, "state_source": state_source or {}}
    if error is not None:
        evidence["error"] = {"type": type(error).__name__, "message": str(error)}
    return NumericalCertificationFailure(message, sanitized_numerical_evidence(evidence))


@dataclass
class Fit:
    model_id: str
    audit: dict[str, Any]
    bundle: Any
    active: np.ndarray
    design: Any
    theta: np.ndarray
    probability: np.ndarray
    treatment: np.ndarray
    labels: list[str]
    influence: np.ndarray
    covariance: np.ndarray
    information: np.ndarray
    pruning: list[dict[str, Any]]
    solver_rows: list[dict[str, Any]]
    profile_rows: list[dict[str, Any]]
    trajectory: dict[str, Any]
    state_source: dict[str, Any]


POST_CERTIFICATION_CONTEXT: dict[str, Any] | None = None


def certified_fit(a1, bundle, analysis: dict[str, Any]) -> Fit:
    reporting_bundle = bundle
    submitted_bundle, reporting_parameterization = a1.target_coordinate_bundle(
        reporting_bundle)
    parity = {"status": "PASS_EXACT_SUBMITTED_DESIGN_PARITY",
              "source": "SUPPORT_INFERENCE_SPEC.json frozen design builder"}
    try:
        audit, pruning, solver_rows, profile_rows, trajectory = a1.audit_model(
            submitted_bundle, analysis, _disabled_legacy, parity)
    except Exception as error:
        raise certification_failure("A1_AUDIT_EXCEPTION", reporting_bundle.model_id,
                                    "fresh A1 audit raised before returning evidence",
                                    error=error) from error
    if audit.get("a1_certification", {}).get("status") != "PASS_A1_NUMERICAL_CERTIFICATE":
        raise certification_failure("A1_CERTIFICATE", reporting_bundle.model_id,
            f"new model failed A1 certificate: {reporting_bundle.model_id}", audit, pruning,
            solver_rows, profile_rows, trajectory)
    transformed, parameterization = a1.target_coordinate_bundle(submitted_bundle)
    functionals = {
        f"original_treatment::{row['original_index']}::{row['original_label']}":
        np.asarray(row["weights"], float)
        for row in parameterization["original_coefficient_functionals_in_current_basis"]
    }
    reporting_functionals = {
        f"original_treatment::reporting::{row['original_index']}::{row['original_label']}":
        np.asarray(row["weights"], float)
        for row in reporting_parameterization["original_coefficient_functionals_in_current_basis"]
    }
    all_functionals = {**functionals, **reporting_functionals}
    try:
        active, design, face, _ = a1.resolve_extended_likelihood_face(
            transformed, analysis, all_functionals)
    except Exception as error:
        raise certification_failure("FINITE_FACE_RECONSTRUCTION", reporting_bundle.model_id,
            "fresh finite-face reconstruction raised", audit, pruning, solver_rows,
            profile_rows, trajectory, error=error) from error
    if design is None or face.get("status") != "PASS_FINITE_FACE_RESOLVED":
        raise certification_failure("FINITE_FACE_RECONSTRUCTION", reporting_bundle.model_id,
            f"finite face not reproducible: {reporting_bundle.model_id}", audit, pruning,
            solver_rows, profile_rows, trajectory, state_source={"face": face})
    x = transformed.regressors[active]
    geometry = a1.information_diagnostics(
        design, x, transformed.total[active] * .25, transformed.focal_target,
        float(analysis["tolerances"]["conditioning_rank_relative"]))
    try:
        selected, basis = a1.select_regressor_basis_preserving_focal(
            design.nuisance, x, transformed.total[active] * .25,
            transformed.focal_target, geometry)
    except Exception as error:
        raise certification_failure("RANK_AND_BASIS_RECONSTRUCTION", reporting_bundle.model_id,
            "fresh treatment-basis reconstruction raised", audit, pruning, solver_rows,
            profile_rows, trajectory, state_source={"geometry": geometry}, error=error) from error
    if basis["dropped_dependent_original_columns"]:
        raise certification_failure("RANK_AND_BASIS_RECONSTRUCTION", reporting_bundle.model_id,
            f"treatment rank reduction would alter claims: {reporting_bundle.model_id}",
            audit, pruning, solver_rows, profile_rows, trajectory,
            state_source={"geometry": geometry, "basis": basis})
    design = a1.replace_design_regressors(design, x[:, selected])
    objective = a1.BinomialObjective(design.full, transformed.young[active],
                                     transformed.total[active])
    targets: dict[str, np.ndarray] = {}
    for label, weights in all_functionals.items():
        vector = np.zeros(design.full.shape[1])
        vector[design.nuisance.shape[1]:] = weights[selected]
        targets[label] = vector
    focal_column = design.nuisance.shape[1] + selected.index(transformed.focal_target)
    targets["focal_target"] = np.eye(1, design.full.shape[1], focal_column).ravel()
    tol = analysis["tolerances"]
    try:
        reference_raw = a1.fit_independent_sparse_newton(
            objective, np.zeros(design.full.shape[1]), int(tol["optimizer_max_iterations"]),
            float(tol["gradient_infinity_norm_per_total"]),
            float(tol["standardized_score_absolute"]), focal_column, targets,
            float(tol["target_coefficient_absolute_difference"]),
            float(analysis["profile"]["likelihood_rise_tolerance_raw"]),
            float(tol["conditioning_rank_relative"]),
            float(tol["objective_difference_per_total"]),
            float(tol["fitted_probability_max_abs_difference"]), "gate2_state_reconstruction")
        reference_certified = a1.externally_certify_independent_output(
            objective, reference_raw, targets, float(tol["gradient_infinity_norm_per_total"]),
            float(tol["standardized_score_absolute"]),
            float(tol["target_coefficient_absolute_difference"]),
            float(analysis["profile"]["likelihood_rise_tolerance_raw"]),
            float(tol["conditioning_rank_relative"]),
            float(tol["objective_difference_per_total"]),
            float(tol["fitted_probability_max_abs_difference"]))
    except Exception as error:
        raise certification_failure("REFERENCE_STATE_RECONSTRUCTION", reporting_bundle.model_id,
            "independent reference state reconstruction raised", audit, pruning, solver_rows,
            profile_rows, trajectory, state_source={"geometry": geometry, "basis": basis},
            error=error) from error
    reference_diagnostics, reference_theta, reference_probability, _ = reference_certified
    if reference_diagnostics.get("numerically_valid") is not True:
        raise certification_failure("REFERENCE_EXTERNAL_CERTIFICATE", reporting_bundle.model_id,
            f"state reconstruction failed A1 external certificate: {reporting_bundle.model_id}",
            audit, pruning, solver_rows, profile_rows, trajectory,
            state_source={"reference_diagnostics": reference_diagnostics})
    try:
        trust_raw = a1.fit_exact_solver(
        objective, "trust-ncg", np.zeros(design.full.shape[1]),
        int(tol["optimizer_max_iterations"]),
        float(tol["gradient_infinity_norm_per_total"]),
        float(tol["standardized_score_absolute"]), focal_column, targets,
        float(tol["target_coefficient_absolute_difference"]),
        float(analysis["profile"]["likelihood_rise_tolerance_raw"]), False,
            float(tol["conditioning_rank_relative"]))
        trust_path, trust_polish = a1.conditionally_polish_trust_candidate(
        objective, trust_raw, int(tol["optimizer_max_iterations"]),
        float(tol["gradient_infinity_norm_per_total"]),
        float(tol["standardized_score_absolute"]), focal_column, targets,
        float(tol["target_coefficient_absolute_difference"]),
        float(analysis["profile"]["likelihood_rise_tolerance_raw"]),
        float(tol["conditioning_rank_relative"]),
        float(tol["objective_difference_per_total"]),
            float(tol["fitted_probability_max_abs_difference"]))
    except Exception as error:
        raise certification_failure("TRUST_STATE_RECONSTRUCTION", reporting_bundle.model_id,
            "trust-path state reconstruction raised", audit, pruning, solver_rows,
            profile_rows, trajectory, state_source={"reference_diagnostics": reference_diagnostics},
            error=error) from error
    trust_diagnostics, theta, probability, _ = trust_path
    if trust_diagnostics.get("numerically_valid") is not True:
        raise certification_failure("TRUST_EXTERNAL_CERTIFICATE", reporting_bundle.model_id,
            f"trust-path reconstruction failed external certificate: {reporting_bundle.model_id}",
            audit, pruning, solver_rows, profile_rows, trajectory,
            state_source={"reference_diagnostics": reference_diagnostics,
                          "trust_diagnostics": trust_diagnostics, "trust_polish": trust_polish})
    target_differences = {label: abs(float(vector @ theta) - float(vector @ reference_theta))
                          for label, vector in targets.items()}
    probability_difference = float(np.max(np.abs(probability-reference_probability)))
    objective_difference = abs(float(objective.function(theta)-objective.function(reference_theta)))
    if max(target_differences.values(), default=0.0) > float(
            tol["target_coefficient_absolute_difference"]) or probability_difference > float(
            tol["fitted_probability_max_abs_difference"]) or objective_difference > float(
            tol["objective_difference_per_total"]):
        raise certification_failure("TRUST_REFERENCE_COMPARISON", reporting_bundle.model_id,
            f"fresh trust/reference state comparison failed: {reporting_bundle.model_id}",
            audit, pruning, solver_rows, profile_rows, trajectory,
            state_source={"reference_diagnostics": reference_diagnostics,
                "trust_diagnostics": trust_diagnostics, "trust_polish": trust_polish,
                "target_absolute_differences": target_differences,
                "fitted_probability_max_absolute_difference": probability_difference,
                "objective_per_total_absolute_difference": objective_difference})
    expected = audit["solver_comparison"]["trust_path_target_vector"]
    for label, vector in targets.items():
        if label in expected and abs(float(vector @ theta) - float(expected[label])) > float(
                tol["target_coefficient_absolute_difference"]):
            raise certification_failure("A1_TARGET_CHECKPOINT", reporting_bundle.model_id,
                f"state reconstruction target mismatch: {reporting_bundle.model_id}", audit,
                pruning, solver_rows, profile_rows, trajectory,
                state_source={"target": label, "fresh_value": float(vector@theta),
                              "a1_value": float(expected[label])})
    original_rows = sorted(
        reporting_parameterization["original_coefficient_functionals_in_current_basis"],
        key=lambda row: int(row["original_index"]))
    original_map = np.vstack([np.asarray(row["weights"], float)[selected]
                                 for row in original_rows])
    transformed_treatment = theta[design.nuisance.shape[1]:]
    treatment = original_map @ transformed_treatment
    reference_treatment = original_map @ reference_theta[design.nuisance.shape[1]:]
    h = transformed.total[active] * probability * (1 - probability)
    residual = residualize_treatment(design.nuisance, x[:, selected], h)
    transformed_info = residual.T @ (h[:, None] * residual)
    inverse = np.linalg.inv(transformed_info)
    scores = residual * (transformed.young[active] - transformed.total[active] * probability)[:, None]
    occupations = transformed.frame.loc[active, "occ_code"].astype(str).to_numpy()
    levels = sorted(set(occupations))
    transformed_influence = np.vstack([inverse @ scores[occupations == level].sum(axis=0)
                                          for level in levels])
    influence = transformed_influence @ original_map.T
    correction = len(levels) / (len(levels) - 1)
    covariance = correction * influence.T @ influence
    original_design = a1.replace_design_regressors(design, reporting_bundle.regressors[active])
    original_residual = residualize_treatment(original_design.nuisance,
                                               reporting_bundle.regressors[active], h)
    information = original_residual.T @ (h[:, None] * original_residual)
    state_source = {
        "declared_primary": "trust-path",
        "reference": "independent-damped-sparse-newton-irls",
        "reporting_parameterization": reporting_parameterization,
        "trust_diagnostics": trust_diagnostics,
        "reference_diagnostics": reference_diagnostics,
        "trust_polish": trust_polish,
        "target_absolute_differences": target_differences,
        "maximum_target_absolute_difference": max(target_differences.values(), default=0.0),
        "fitted_probability_max_absolute_difference": probability_difference,
        "objective_per_total_absolute_difference": objective_difference,
        "reported_state_source": "trust-path",
        "primary_original_treatment": dict(zip(reporting_bundle.regressor_labels, treatment.tolist())),
        "reference_original_treatment": dict(zip(reporting_bundle.regressor_labels, reference_treatment.tolist())),
        "primary_full_parameter_sha256": array_sha256(theta),
        "reference_full_parameter_sha256": array_sha256(reference_theta),
        "primary_fitted_probability_sha256": array_sha256(probability),
        "reference_fitted_probability_sha256": array_sha256(reference_probability),
        "active_rows_sha256": audit["numerical_evidence_context"]["active_rows_sha256"],
        "ordered_final_design_sha256": audit["numerical_evidence_context"]["ordered_final_design_sha256"],
    }
    return Fit(reporting_bundle.model_id, audit, reporting_bundle, active, original_design, theta,
               probability, treatment, list(reporting_bundle.regressor_labels), influence,
               covariance, information, pruning, solver_rows, profile_rows,
               trajectory, state_source)


def residualize_treatment(nuisance: sparse.csr_matrix, x: np.ndarray,
                          weight: np.ndarray) -> np.ndarray:
    gram = nuisance.T @ sparse.diags(weight) @ nuisance
    rhs = np.asarray(nuisance.T @ (weight[:, None] * x))
    residual = np.empty_like(x, dtype=float)
    for column in range(x.shape[1]):
        coefficient = spsolve(gram.tocsc(), rhs[:, column])
        if not np.isfinite(coefficient).all():
            raise Blocked("nuisance residualization linear solve failed")
        residual[:, column] = x[:, column] - nuisance @ coefficient
    return residual


def target_result(fit: Fit, weights: np.ndarray) -> dict[str, Any]:
    weights = np.asarray(weights, float)
    estimate = float(weights @ fit.treatment)
    variance = float(weights @ fit.covariance @ weights)
    if variance <= 0 or not math.isfinite(variance):
        raise Blocked("target has non-positive cluster variance")
    se = math.sqrt(variance)
    return {"estimate_source": "trust-path", "estimate": estimate, "standard_error": se,
            "z": estimate / se, "p_value_normal": 2 * norm.sf(abs(estimate / se))}


def common_rademacher(occupations: list[str], draws: int, seed: int) -> np.ndarray:
    if len(occupations) < 2 or draws < 1 or len(set(occupations)) != len(occupations):
        raise Blocked("invalid common-multiplier dimensions")
    rng = np.random.Generator(np.random.PCG64(seed))
    return rng.choice(np.array([-1.0, 1.0]), size=(draws, len(occupations)))


def rank_aware_test(estimate: np.ndarray, covariance: np.ndarray,
                    draws: np.ndarray | None = None) -> dict[str, Any]:
    estimate = np.asarray(estimate, float)
    covariance = np.asarray(covariance, float)
    eigen = np.linalg.eigvalsh(covariance)
    tolerance = max(float(eigen[-1]) * 1e-10, np.finfo(float).eps)
    rank = int(np.sum(eigen > tolerance))
    result = {"restriction_count": len(estimate), "covariance_rank": rank}
    if rank < len(estimate):
        return {**result, "status": "BLOCKED_RANK_DEFICIENT_JOINT_TEST"}
    statistic = float(estimate @ np.linalg.solve(covariance, estimate))
    result.update({"status": "PASS_FULL_RANK_JOINT_TEST", "chi2": statistic,
                   "df": rank, "p_value_chi2": float(chi2.sf(statistic, rank))})
    if draws is not None:
        inverse = np.linalg.inv(covariance)
        bootstrap = np.einsum("bi,ij,bj->b", draws, inverse, draws)
        result["p_value_multiplier"] = float((1 + np.sum(bootstrap >= statistic)) /
                                               (len(bootstrap) + 1))
    return result


def simultaneous_summary(estimates: np.ndarray, covariance: np.ndarray,
                         centered_draws: np.ndarray, alpha: float = .05) -> dict[str, Any]:
    se = np.sqrt(np.diag(covariance))
    if (se <= 0).any():
        raise Blocked("simultaneous inference has a non-positive marginal variance")
    max_t = np.max(np.abs(centered_draws / se), axis=1)
    critical = float(np.quantile(max_t, 1 - alpha, method="higher"))
    return {"critical_value": critical,
            "lower": (estimates - critical * se).tolist(),
            "upper": (estimates + critical * se).tolist(),
            "pointwise_lower": (estimates - norm.ppf(1-alpha/2) * se).tolist(),
            "pointwise_upper": (estimates + norm.ppf(1-alpha/2) * se).tolist()}


def exact_sd_reparameterizations(slope: float, occ: pd.DataFrame) -> dict[str, float]:
    w = occ.pre_stock.to_numpy(float)
    centered = occ.beta_centered.to_numpy(float)
    residual = occ.beta_residual.to_numpy(float)
    sw = math.sqrt(float(np.sum(w * centered**2) / np.sum(w)))
    sr = math.sqrt(float(np.sum(w * residual**2) / np.sum(w)))
    return {"raw_beta_slope": float(slope), "within_family_sd": sw,
            "within_family_sd_effect": float(slope * sw),
            "family_webb_residual_sd": sr,
            "family_webb_residual_sd_effect": float(slope * sr)}


def aggregate_family_quintile_paths(cells: pd.DataFrame,
                                    support: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    supported = support.loc[support.cell_has_support.map(
        lambda x: str(x).lower() == "true"), ["family", "beta_quintile"]].copy()
    supported["family"] = supported.family.astype(str).str.zfill(2)
    supported["beta_quintile"] = supported.beta_quintile.astype(int)
    calendar = pd.DataFrame({"month": pd.period_range("2017-01", "2026-07", freq="M").astype(str)})
    scaffold = supported.assign(key=1).merge(calendar.assign(key=1), on="key").drop(columns="key")
    grouped = cells.groupby(["family", "beta_quintile", "month"], as_index=False).agg(
        young=("young", "sum"), older=("older", "sum"))
    monthly = scaffold.merge(grouped, on=["family", "beta_quintile", "month"], how="left",
                             validate="one_to_one")
    monthly["calendar_status"] = np.where(monthly.month.eq("2025-10"), "MISSING",
                                   np.where(monthly.month.eq("2022-12"), "TRANSITION", "OBSERVED"))
    if monthly.loc[monthly.calendar_status.eq("MISSING"), ["young", "older"]].notna().any().any():
        raise Blocked("canonical missing month unexpectedly contains observations")
    total = monthly.young + monthly.older
    monthly["young_share"] = monthly.young / total.where(total.gt(0))
    monthly["log_young_older"] = np.where((monthly.young > 0) & (monthly.older > 0),
                                           np.log(monthly.young / monthly.older), np.nan)
    monthly["quarter"] = monthly.month.str[:4] + "Q" + (((monthly.month.str[5:7].astype(int)-1)//3)+1).astype(str)
    estimation = monthly.loc[monthly.calendar_status.eq("OBSERVED")].copy()
    quarterly = estimation.groupby(["family", "beta_quintile", "quarter"], as_index=False).agg(
        young_mean=("young", "mean"), older_mean=("older", "mean"),
        young_share_mean=("young_share", "mean"), log_young_older_mean=("log_young_older", "mean"),
        observed_estimation_month_count=("month", "nunique"),
        defined_log_ratio_month_count=("log_young_older", "count"))
    expected = monthly.groupby(["family", "beta_quintile", "quarter"], as_index=False).month.nunique().rename(
        columns={"month": "calendar_month_count"})
    quarterly = quarterly.merge(expected, on=["family", "beta_quintile", "quarter"], validate="one_to_one")
    transition = monthly.assign(is_transition=monthly.calendar_status.eq("TRANSITION").astype(int)).groupby(
        ["family", "beta_quintile", "quarter"], as_index=False).is_transition.sum().rename(
        columns={"is_transition": "transition_month_count"})
    quarterly = quarterly.merge(transition, on=["family", "beta_quintile", "quarter"], validate="one_to_one")
    quarterly["series_scope"] = "STATIC_ESTIMATION_MONTHS_ONLY"
    return monthly, quarterly


def direct_weights(direct: pd.DataFrame) -> dict[str, float]:
    stock = direct.groupby("family").preperiod_stock.sum().astype(float)
    weights = stock / stock.sum()
    if not np.isclose(weights.sum(), 1.0, rtol=0, atol=1e-14):
        raise Blocked("direct-tail weights do not sum to one")
    return {str(k).zfill(2): float(v) for k, v in weights.items()}


def information_panel(fit: Fit, reference_probability: np.ndarray | None = None,
                      same_support_as_pooled: bool = False) -> pd.DataFrame:
    frame = fit.bundle.frame.loc[fit.active].reset_index(drop=True)
    x = fit.bundle.regressors[fit.active]
    panels = {"half": fit.bundle.total[fit.active] * .25,
              "own": fit.bundle.total[fit.active] * fit.probability * (1-fit.probability)}
    if reference_probability is not None:
        if len(reference_probability) != len(frame):
            raise Blocked("fixed-reference probability alignment mismatch")
        panels["fixed_pooled_within_support"] = fit.bundle.total[fit.active] * reference_probability * (1-reference_probability)
    rows = []
    for name, h in panels.items():
        r = residualize_treatment(fit.design.nuisance, x, h)
        info = r.T @ (h[:, None] * r)
        inv = np.linalg.inv(info)
        for j, label in enumerate(fit.labels):
            value = float(1 / inv[j, j])
            direction = inv[:, j] / inv[j, j]
            exact_target_residual = r @ direction
            contribution = h * exact_target_residual ** 2
            by_occ = pd.Series(contribution).groupby(frame.occ_code).sum()
            shares = by_occ / by_occ.sum()
            raw_ss = float(np.sum(h * (x[:, j]-np.average(x[:, j], weights=h))**2))
            fe_ss = float(np.sum(h * r[:, j] ** 2))
            if not np.isclose(contribution.sum(), value, rtol=1e-8, atol=1e-10):
                raise Blocked("exact target information contribution failed closure")
            rows.append({"model_id": fit.model_id, "panel": name, "target": label,
                         "reference_scope": ("target_model_retained_rows" if name == "fixed_pooled_within_support"
                                             else "target_model"),
                         "absolute_level_comparable_to_full_pooled": bool(
                             name != "fixed_pooled_within_support" or same_support_as_pooled),
                         "sum_h": float(h.sum()), "raw_centered_ss": raw_ss,
                         "raw_centered_sd": float(math.sqrt(raw_ss/h.sum())),
                         "fe_residual_ss": fe_ss,
                         "fe_residual_sd": float(math.sqrt(fe_ss/h.sum())),
                         "all_nuisance_information": value,
                         "all_nuisance_sd": float(1/math.sqrt(value)),
                         "effective_occupation_equivalent": float(1/np.sum(shares**2))})
    return pd.DataFrame(rows)


def aligned_reference_probability(reference: Fit, target: Fit) -> np.ndarray:
    source = reference.bundle.frame.loc[reference.active, ["occ_code", "month"]].copy()
    source["reference_probability"] = reference.probability
    if source.duplicated(["occ_code", "month"]).any():
        raise Blocked("reference probability key is not unique")
    wanted = target.bundle.frame.loc[target.active, ["occ_code", "month"]].copy()
    joined = wanted.merge(source, on=["occ_code", "month"], how="left", validate="one_to_one")
    if joined.reference_probability.isna().any():
        raise Blocked("fixed-reference probability alignment is incomplete")
    return joined.reference_probability.to_numpy(float)


def information_contributions(fit: Fit, panel: str,
                              probability: np.ndarray | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    frame = fit.bundle.frame.loc[fit.active].reset_index(drop=True)
    if panel == "half":
        h = fit.bundle.total[fit.active] * .25
    elif panel == "own":
        h = fit.bundle.total[fit.active] * fit.probability * (1-fit.probability)
    elif panel == "fixed_pooled_within_support" and probability is not None:
        h = fit.bundle.total[fit.active] * probability * (1-probability)
    else:
        raise Blocked("invalid information-contribution panel")
    x = fit.bundle.regressors[fit.active]
    r = residualize_treatment(fit.design.nuisance, x, h)
    info = r.T @ (h[:, None] * r)
    inv = np.linalg.inv(info)
    occ_rows, family_rows = [], []
    for j, label in enumerate(fit.labels):
        direction = inv[:, j] / inv[j, j]
        exact_target_residual = r @ direction
        raw = pd.DataFrame({"occupation_code": frame.occ_code, "family": frame.family,
                            "contribution": h*exact_target_residual**2})
        by_occ = raw.groupby(["occupation_code", "family"], as_index=False).contribution.sum()
        total = float(by_occ.contribution.sum())
        by_occ["share"] = by_occ.contribution / total
        for row in by_occ.itertuples(index=False):
            occ_rows.append({"model_id": fit.model_id, "panel": panel, "target": label,
                             "occupation_code": row.occupation_code, "family": row.family,
                             "information_contribution": row.contribution, "information_share": row.share})
        by_family = by_occ.groupby("family", as_index=False).contribution.sum()
        by_family["share"] = by_family.contribution / total
        for row in by_family.itertuples(index=False):
            family_rows.append({"model_id": fit.model_id, "panel": panel, "target": label,
                                "family": row.family, "information_contribution": row.contribution,
                                "information_share": row.share})
    return pd.DataFrame(occ_rows), pd.DataFrame(family_rows)


def profile_checkpoint(fit: Fit, a1_audit: dict[str, Any], tolerance: float) -> list[dict[str, Any]]:
    record = next((m for m in a1_audit["models"] if m.get("model_id") == fit.model_id), None)
    if record is None:
        raise Blocked(f"A1 checkpoint missing: {fit.model_id}")
    comparison = record["solver_comparison"]
    rows = []
    for index, label in enumerate(fit.labels):
        key = f"original_treatment::{index}::{label}"
        for path, expected_vector, observed_map in (
            ("trust-path", comparison["trust_path_target_vector"],
             fit.state_source["primary_original_treatment"]),
            ("independent-damped-sparse-newton-irls", comparison["reference_target_vector"],
             fit.state_source["reference_original_treatment"])):
            if key not in expected_vector:
                raise Blocked(f"A1 checkpoint target absent: {fit.model_id}/{label}/{path}")
            difference = abs(float(observed_map[label]) - float(expected_vector[key]))
            rows.append({"model_id": fit.model_id, "path": path, "target": label,
                         "fresh_estimate": float(observed_map[label]),
                         "a1_estimate": float(expected_vector[key]),
                         "absolute_difference": difference, "tolerance": tolerance,
                         "pass": difference <= tolerance})
            if difference > tolerance:
                raise Blocked(f"A1 profile reproduction mismatch: {fit.model_id}/{label}/{path}")
    return rows


def long_matrix(matrix_kind: str, matrix: np.ndarray, row_labels: list[str],
                column_labels: list[str]) -> list[dict[str, Any]]:
    if matrix.shape != (len(row_labels), len(column_labels)):
        raise Blocked(f"labeled matrix shape mismatch: {matrix_kind}")
    return [{"matrix_kind": matrix_kind, "row_target": row, "column_target": column,
             "value": float(matrix[i, j])}
            for i, row in enumerate(row_labels) for j, column in enumerate(column_labels)]


def interval_rows(model_id: str, labels: list[str], estimates: np.ndarray,
                  covariance: np.ndarray, draws: np.ndarray,
                  alpha: float = .05) -> list[dict[str, Any]]:
    summary = simultaneous_summary(estimates, covariance, draws, alpha)
    se = np.sqrt(np.diag(covariance))
    rows = []
    for index, label in enumerate(labels):
        rows.append({"model_id": model_id, "target": label,
                     "estimate_source": "trust-path",
                     "estimate": float(estimates[index]), "standard_error": float(se[index]),
                     "pointwise_lower": summary["pointwise_lower"][index],
                     "pointwise_upper": summary["pointwise_upper"][index],
                     "simultaneous_lower": summary["lower"][index],
                     "simultaneous_upper": summary["upper"][index],
                     "simultaneous_critical_value": summary["critical_value"],
                     "alpha": alpha, "draw_count": len(draws)})
    return rows


def array_sha256(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    header = canonical_bytes({"dtype": value.dtype.str, "shape": list(value.shape)})
    return hashlib.sha256(header + value.tobytes(order="C")).hexdigest()


SECRET_KEY_PATTERN = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?key|auth(?:orization)?|bearer|credential|"
    r"password|passwd|private[_-]?key|secret|session[_-]?key|token)"
)
SECRET_VALUE_PATTERN = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?key|auth(?:orization)?|bearer|credential|"
    r"password|passwd|private[_-]?key|secret|session[_-]?key|token)\s*[:= ]\s*\S+|"
    r"\b(?:sk|pk)-[A-Za-z0-9_-]{8,}\b|[a-z][a-z0-9+.-]*://[^\s/:]+:[^\s/@]+@"
)
JSON_SECRET_FIELD_PATTERN = re.compile(
    r'(?i)"(?:api[_-]?key|access[_-]?key|bearer|credential|password|passwd|'
    r'private[_-]?key|secret|session[_-]?key|token)"\s*:\s*'
    r'(?!"REDACTED_SECRET")'
)
ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?:(?<![A-Za-z0-9_.-])/(?:[^\s/'\"<>:]+/)*[^\s/'\"<>:]*)|"
    r"(?:(?<![A-Za-z0-9])[A-Za-z]:\\(?:[^\s\\]+\\)*[^\s\\]*)"
)
MONTH_TOKEN_PATTERN = re.compile(r"(?<![0-9])(?:19|20)[0-9]{2}-(?:0[1-9]|1[0-2])(?![0-9])")
OCCUPATION_TOKEN_PATTERN = re.compile(r"(?<![0-9])[0-9]{4}(?![0-9])")
GENERAL_RECESSION_PRIVATE_KEYS = frozenset({
    "group", "row_index", "young", "older", "total",
})
STRICT_ROW_ALIGNMENT_KEYS = frozenset({
    "strict_boundary_local_indices", "strict_boundary_margins",
})


def sensitive_string_kind(value: str) -> str | None:
    if SECRET_VALUE_PATTERN.search(value):
        return "secret"
    if ABSOLUTE_PATH_PATTERN.search(value):
        return "absolute_path"
    return None


def contains_composite_occupation_month(value: str) -> bool:
    """Detect an occupation token and calendar month encoded in one string."""
    without_month = MONTH_TOKEN_PATTERN.sub("", value)
    return bool(MONTH_TOKEN_PATTERN.search(value) and
                OCCUPATION_TOKEN_PATTERN.search(without_month))


def sanitized_numerical_evidence(value: Any) -> Any:
    """Retain numerical evidence without releasing occupation-by-month cells."""
    if isinstance(value, dict):
        composite_group = any(
            isinstance(item, str) and contains_composite_occupation_month(item)
            for item in value.values()
        )
        general_recession = (
            str(value.get("partition", "")).strip().lower() ==
            "general_recession_face"
        )
        if ("occ_code" in value and "month" in value) or composite_group or general_recession:
            retained = {str(key): ("REDACTED_SECRET" if
                        SECRET_KEY_PATTERN.search(str(key)) else
                        sanitized_numerical_evidence(item))
                        for key, item in value.items()
                        if key not in ({"occ_code", "month", "family", "status"} |
                                       GENERAL_RECESSION_PRIVATE_KEYS |
                                       STRICT_ROW_ALIGNMENT_KEYS)}
            return {**retained, "status": "REDACTED_OCCUPATION_MONTH_IDENTIFIER"}
        retained = {}
        for key, item in value.items():
            label = str(key)
            if label in STRICT_ROW_ALIGNMENT_KEYS:
                retained[label] = "REDACTED_OCCUPATION_MONTH_ROW_ALIGNMENT"
            elif SECRET_KEY_PATTERN.search(label):
                retained[label] = "REDACTED_SECRET"
            else:
                retained[label] = sanitized_numerical_evidence(item)
        return retained
    if isinstance(value, (list, tuple, set)):
        return [sanitized_numerical_evidence(item) for item in value]
    if isinstance(value, pathlib.Path):
        return "REDACTED_PRIVATE_PATH"
    if isinstance(value, bytes):
        return "REDACTED_BINARY_VALUE"
    if isinstance(value, np.generic):
        return sanitized_numerical_evidence(value.item())
    if isinstance(value, Exception):
        return sanitized_numerical_evidence(str(value))
    if isinstance(value, str):
        if contains_composite_occupation_month(value):
            return "REDACTED_OCCUPATION_MONTH_IDENTIFIER"
        kind = sensitive_string_kind(value)
        if kind == "secret":
            return "REDACTED_SECRET"
        if kind == "absolute_path":
            return "REDACTED_PRIVATE_PATH"
    return value


def verify_linear_derived_closure(name: str, observed_labels: list[str],
                                  expected_labels: list[str], functionals: np.ndarray,
                                  base_covariance: np.ndarray, base_influence: np.ndarray,
                                  multipliers: np.ndarray, covariance: np.ndarray,
                                  draws: np.ndarray, tolerance: float = 1e-12) -> dict[str, Any]:
    if observed_labels != expected_labels:
        raise Blocked(f"{name} label order differs from its authenticated functional order")
    if functionals.shape[0] != len(expected_labels) or functionals.shape[1] != base_covariance.shape[0]:
        raise Blocked(f"{name} functional orientation/dimensions are invalid")
    if base_covariance.shape[0] != base_covariance.shape[1] or base_influence.shape[1] != functionals.shape[1]:
        raise Blocked(f"{name} base covariance/influence dimensions are invalid")
    correction = len(base_influence)/(len(base_influence)-1)
    influence = base_influence @ functionals.T
    expected_functional_covariance = functionals @ base_covariance @ functionals.T
    expected_influence_covariance = correction * influence.T @ influence
    expected_draws = math.sqrt(correction) * multipliers @ influence
    residuals = {
        "functional_covariance": float(np.max(np.abs(expected_functional_covariance-covariance))),
        "influence_covariance": float(np.max(np.abs(expected_influence_covariance-covariance))),
        "common_multiplier_draws": float(np.max(np.abs(expected_draws-draws))),
    }
    passed = all(value <= tolerance for value in residuals.values())
    if not passed:
        raise Blocked(f"{name} derived-object closure failed")
    return {"label_order_pass": True, "functional_shape": list(functionals.shape),
            "maximum_absolute_residuals": residuals, "tolerance": tolerance, "pass": True}


def verify_public_frame_reconstruction(
        name: str, observed: pd.DataFrame, expected: pd.DataFrame,
        tolerant_numeric_columns: Iterable[str], tolerance: float = 1e-14,
) -> dict[str, Any]:
    """Close every public field against an independently rebuilt frame."""
    tolerant = list(tolerant_numeric_columns)
    columns_match = list(observed.columns) == list(expected.columns)
    rows_match = len(observed) == len(expected)
    if not columns_match or not rows_match or any(
            column not in expected.columns for column in tolerant):
        return {"frame": name, "columns_match": columns_match,
                "rows_match": rows_match, "maximum_numeric_difference": math.inf,
                "exact_fields_match": False, "tolerance": tolerance, "pass": False}
    exact_columns = [column for column in expected.columns if column not in tolerant]
    exact_fields_match = observed[exact_columns].reset_index(drop=True).equals(
        expected[exact_columns].reset_index(drop=True))
    if tolerant:
        observed_numeric = observed[tolerant].to_numpy(float)
        expected_numeric = expected[tolerant].to_numpy(float)
        finite = bool(np.isfinite(observed_numeric).all() and
                      np.isfinite(expected_numeric).all())
        maximum_difference = float(np.max(np.abs(observed_numeric-expected_numeric)))
        numeric_match = bool(finite and np.allclose(
            observed_numeric, expected_numeric, rtol=0, atol=tolerance))
    else:
        finite, maximum_difference, numeric_match = True, 0.0, True
    return {"frame": name, "columns_match": True, "rows_match": True,
            "exact_fields_match": bool(exact_fields_match),
            "numeric_fields_finite": finite,
            "maximum_numeric_difference": maximum_difference,
            "tolerance": tolerance,
            "pass": bool(exact_fields_match and numeric_match)}


def recompute_validation(fits: list[Fit], pooled: Fit, family_month: Fit,
                         xi: np.ndarray, paired_covariance: np.ndarray,
                         paired_draws: np.ndarray, profile_estimates: pd.DataFrame,
                         profile_intervals: pd.DataFrame, cross_covariance: np.ndarray,
                         pooled_draws: np.ndarray, family_draws: np.ndarray,
                         monthly: pd.DataFrame,
                         quarterly: pd.DataFrame, direct_functional: np.ndarray,
                         direct_aggregate_influence: np.ndarray,
                         direct_family_closure: pd.DataFrame,
                         heterogeneous: Fit, edge_matrix: np.ndarray,
                         edge_covariance: np.ndarray, edge_draws: np.ndarray,
                         hetero_xi: np.ndarray, edge_labels: list[str],
                         direct_fit: Fit, direct_functionals: np.ndarray,
                         direct_covariance: np.ndarray, direct_draws: np.ndarray,
                         direct_xi: np.ndarray, direct_labels: list[str],
                         edge_joint: dict[str, Any],
                         support: pd.DataFrame, edges: pd.DataFrame,
                         direct_membership: pd.DataFrame,
                         edge_estimate_frame: pd.DataFrame,
                         edge_functional_frame: pd.DataFrame,
                         direct_estimate_frame: pd.DataFrame,
                         direct_functional_frame: pd.DataFrame,
                         pair_labels: list[str], pair_functionals: np.ndarray,
                         pair_covariance: np.ndarray, pair_draws: np.ndarray,
                         pair_estimate_frame: pd.DataFrame,
                         pair_weight_frame: pd.DataFrame,
                         pair_functional_frame: pd.DataFrame,
                         checkpoint_rows: list[dict[str, Any]],
                         tolerance: float) -> dict[str, Any]:
    correction = len(pooled.influence) / (len(pooled.influence)-1)
    recomputed_paired_if = family_month.influence[:, :4] - pooled.influence[:, :4]
    checks: dict[str, dict[str, Any]] = {}
    expected_covariance = correction * recomputed_paired_if.T @ recomputed_paired_if
    checks["paired_covariance_identity"] = {
        "maximum_absolute_difference": float(np.max(np.abs(expected_covariance-paired_covariance))),
        "pass": bool(np.allclose(expected_covariance, paired_covariance, rtol=1e-12, atol=1e-14))}
    expected_cross = correction * pooled.influence[:, :4].T @ family_month.influence[:, :4]
    checks["cross_model_covariance_identity"] = {
        "maximum_absolute_difference": float(np.max(np.abs(expected_cross-cross_covariance))),
        "pass": bool(np.allclose(expected_cross, cross_covariance, rtol=1e-12, atol=1e-14))}
    expected_pooled_cov = correction * pooled.influence[:, :4].T @ pooled.influence[:, :4]
    expected_family_cov = correction * family_month.influence[:, :4].T @ family_month.influence[:, :4]
    checks["within_model_covariance_identity"] = {
        "pooled_maximum_absolute_difference": float(np.max(np.abs(
            expected_pooled_cov-pooled.covariance[:4, :4]))),
        "family_month_maximum_absolute_difference": float(np.max(np.abs(
            expected_family_cov-family_month.covariance[:4, :4]))),
        "pass": bool(np.allclose(expected_pooled_cov, pooled.covariance[:4, :4], rtol=1e-12, atol=1e-14)
                     and np.allclose(expected_family_cov, family_month.covariance[:4, :4], rtol=1e-12, atol=1e-14))}
    expected_draws = math.sqrt(correction) * xi @ recomputed_paired_if
    stored_identity_exact = bool(np.array_equal(
        paired_draws, family_draws-pooled_draws))
    checks["paired_common_draw_identity"] = {
        "maximum_absolute_difference": float(np.max(np.abs(expected_draws-paired_draws))),
        "stored_identity_exact": stored_identity_exact,
        "pass": bool(stored_identity_exact and np.allclose(
            expected_draws, paired_draws, rtol=1e-12, atol=1e-14))}
    expected_pooled_draws = math.sqrt(correction) * xi @ pooled.influence[:, :4]
    expected_family_draws = math.sqrt(correction) * xi @ family_month.influence[:, :4]
    checks["profile_common_draws_and_difference"] = {
        "pooled_maximum_absolute_difference": float(np.max(np.abs(expected_pooled_draws-pooled_draws))),
        "family_month_maximum_absolute_difference": float(np.max(np.abs(expected_family_draws-family_draws))),
        "paired_stored_difference_maximum_absolute_difference": float(np.max(np.abs(
            paired_draws-(family_draws-pooled_draws)))),
        "pass": bool(np.allclose(expected_pooled_draws, pooled_draws, rtol=1e-12, atol=1e-14)
                     and np.allclose(expected_family_draws, family_draws, rtol=1e-12, atol=1e-14)
                     and np.array_equal(paired_draws, family_draws-pooled_draws))}
    expected_profile_labels = [f"Q{q}_x_post" for q in range(2, 6)]
    paired_rows = profile_estimates.loc[profile_estimates.model_id.eq("family_month_minus_pooled")]
    expected_paired_labels = [f"delta_Q{q}" for q in range(2, 6)]
    checks["profile_point_estimate_labels_and_identity"] = {
        "pooled_labels": profile_estimates.loc[profile_estimates.model_id.eq("pooled"), "target"].tolist(),
        "family_month_labels": profile_estimates.loc[profile_estimates.model_id.eq("family_month"), "target"].tolist(),
        "paired_labels": paired_rows.target.tolist(),
        "paired_maximum_absolute_difference": float(np.max(np.abs(
            paired_rows.estimate.to_numpy()- (family_month.treatment[:4]-pooled.treatment[:4])))),
        "pass": bool(profile_estimates.loc[profile_estimates.model_id.eq("pooled"), "target"].tolist()
                     == expected_profile_labels and
                     profile_estimates.loc[profile_estimates.model_id.eq("family_month"), "target"].tolist()
                     == expected_profile_labels and paired_rows.target.tolist() == expected_paired_labels and
                     np.allclose(paired_rows.estimate, family_month.treatment[:4]-pooled.treatment[:4],
                                 rtol=0, atol=1e-14))}
    expected_interval_frame = pd.DataFrame(
        interval_rows("pooled", expected_profile_labels, pooled.treatment[:4],
                      pooled.covariance[:4, :4], pooled_draws) +
        interval_rows("family_month", expected_profile_labels, family_month.treatment[:4],
                      family_month.covariance[:4, :4], family_draws) +
        interval_rows("family_month_minus_pooled", expected_paired_labels,
                      family_month.treatment[:4]-pooled.treatment[:4], paired_covariance, paired_draws))
    interval_numeric = ["estimate", "standard_error", "pointwise_lower", "pointwise_upper",
                        "simultaneous_lower", "simultaneous_upper", "simultaneous_critical_value"]
    interval_label_pass = profile_intervals[["model_id", "target"]].to_dict("records") == expected_interval_frame[
        ["model_id", "target"]].to_dict("records")
    interval_difference = float(np.max(np.abs(profile_intervals[interval_numeric].to_numpy(float)-
                                              expected_interval_frame[interval_numeric].to_numpy(float))))
    checks["profile_interval_recomputation"] = {
        "label_order_pass": interval_label_pass, "maximum_absolute_difference": interval_difference,
        "pass": bool(interval_label_pass and interval_difference <= 1e-14)}
    checks["fresh_a1_checkpoint"] = {
        "row_count": len(checkpoint_rows),
        "maximum_absolute_difference": max((row["absolute_difference"] for row in checkpoint_rows), default=math.inf),
        "pass": bool(checkpoint_rows and all(row["pass"] for row in checkpoint_rows))}
    a1_statuses = {fit.model_id: fit.audit.get("a1_certification", {}).get("status") for fit in fits}
    checks["fresh_a1_certificates"] = {
        "statuses": a1_statuses,
        "pass": all(value == "PASS_A1_NUMERICAL_CERTIFICATE" for value in a1_statuses.values())}
    profile_statuses = {fit.model_id: fit.audit.get("target_profile", {}).get("status") for fit in fits}
    checks["fresh_two_sided_profiles"] = {
        "statuses": profile_statuses,
        "pass": all(value == "PASS_TWO_SIDED_FINITE_PROFILE" for value in profile_statuses.values())}
    hessian_statuses = {fit.model_id: fit.audit.get(
        "dual_candidate_fitted_hessian_audit", {}).get("status") for fit in fits}
    checks["fresh_dual_candidate_fitted_hessians"] = {
        "statuses": hessian_statuses,
        "pass": all(value == "PASS_BOTH_CANDIDATE_RAW_AND_SCALED_FITTED_HESSIANS"
                    for value in hessian_statuses.values())}
    state_sources = {fit.model_id: fit.state_source.get("reported_state_source") for fit in fits}
    checks["primary_state_source"] = {
        "sources": state_sources, "pass": all(value == "trust-path" for value in state_sources.values())}
    q4 = quarterly.loc[quarterly.quarter.eq("2022Q4")]
    checks["transition_excluded_from_quarterly_estimation"] = {
        "maximum_estimation_month_count_2022Q4": int(q4.observed_estimation_month_count.max()),
        "minimum_transition_month_count_2022Q4": int(q4.transition_month_count.min()),
        "pass": bool((q4.observed_estimation_month_count == 2).all() and
                     (q4.transition_month_count == 1).all())}
    missing = monthly.loc[monthly.month.eq("2025-10")]
    checks["missing_month_blank"] = {
        "row_count": len(missing), "pass": bool(len(missing) > 0 and
        (missing.calendar_status == "MISSING").all() and missing[["young", "older"]].isna().all().all())}
    if edge_matrix.shape != (89, len(heterogeneous.labels)) or len(edge_labels) != 89 or len(
            set(edge_labels)) != 89:
        raise Blocked("edge functional label/order dimensions are invalid")
    rebuilt_edge_labels, rebuilt_edge_matrix = rebuild_edge_functionals(
        support.copy(), edges.copy(), heterogeneous.labels)
    edge_estimates = edge_matrix @ heterogeneous.treatment
    observed_edge_estimates = edge_estimate_frame.estimate.to_numpy(float)
    expected_edge_frame = pd.DataFrame([
        {"family": str(edge.family).zfill(2),
         "quintile_low": int(edge.quintile_low),
         "quintile_high": int(edge.quintile_high),
         "functional_label": edge_label,
         **target_result(heterogeneous, functional)}
        for edge, edge_label, functional in zip(
            edges.itertuples(index=False), rebuilt_edge_labels, rebuilt_edge_matrix)
    ])
    edge_frame_closure = verify_public_frame_reconstruction(
        "SUPPORTED_PAIRWISE_CONTRASTS.csv", edge_estimate_frame,
        expected_edge_frame, ("estimate", "standard_error", "z", "p_value_normal"))
    expected_edge_functional_frame = pd.DataFrame([
        {"functional_label": rebuilt_edge_labels[i], "coefficient_label": label,
         "weight": float(rebuilt_edge_matrix[i, j])}
        for i in range(len(rebuilt_edge_labels))
        for j, label in enumerate(heterogeneous.labels)
    ])
    edge_functional_frame_closure = verify_public_frame_reconstruction(
        "SUPPORTED_EDGE_FUNCTIONALS.csv", edge_functional_frame,
        expected_edge_functional_frame, ())
    checks["authenticated_edge_functional_reconstruction"] = {
        "label_order_pass": edge_labels == rebuilt_edge_labels,
        "functional_rank": int(np.linalg.matrix_rank(rebuilt_edge_matrix, tol=1e-12)),
        "functional_maximum_absolute_difference": float(np.max(np.abs(
            edge_matrix-rebuilt_edge_matrix))),
        "estimate_maximum_absolute_difference": float(np.max(np.abs(
            observed_edge_estimates-edge_estimates))),
        "public_estimate_frame": edge_frame_closure,
        "public_functional_frame": edge_functional_frame_closure,
        "pass": bool(edge_labels == rebuilt_edge_labels and
                     np.array_equal(edge_matrix, rebuilt_edge_matrix) and
                     np.allclose(observed_edge_estimates, edge_estimates, rtol=0, atol=1e-14) and
                     edge_frame_closure["pass"] and edge_functional_frame_closure["pass"])}
    hetero_correction = len(heterogeneous.influence)/(len(heterogeneous.influence)-1)
    edge_influence = heterogeneous.influence @ edge_matrix.T
    expected_edge_covariance_functional = edge_matrix @ heterogeneous.covariance @ edge_matrix.T
    expected_edge_covariance_influence = hetero_correction * edge_influence.T @ edge_influence
    expected_edge_draws = math.sqrt(hetero_correction) * hetero_xi @ edge_influence
    edge_closure = verify_linear_derived_closure(
        "supported edges", edge_labels, list(edge_labels), edge_matrix,
        heterogeneous.covariance, heterogeneous.influence, hetero_xi,
        edge_covariance, edge_draws, 1e-12)
    checks["edge_functional_covariance_influence_draw_closure"] = {**edge_closure,
        "functional_covariance_maximum_absolute_difference": float(np.max(np.abs(
            expected_edge_covariance_functional-edge_covariance))),
        "influence_covariance_maximum_absolute_difference": float(np.max(np.abs(
            expected_edge_covariance_influence-edge_covariance))),
        "draw_maximum_absolute_difference": float(np.max(np.abs(expected_edge_draws-edge_draws))),
        "label_count": len(edge_labels)}
    checks["expected_structural_edge_rank_block"] = {
        "restriction_count": edge_joint.get("restriction_count"),
        "functional_rank": int(np.linalg.matrix_rank(edge_matrix, tol=1e-12)),
        "covariance_rank": edge_joint.get("covariance_rank"), "status": edge_joint.get("status"),
        "chi2_present": "chi2" in edge_joint, "p_value_present": "p_value_chi2" in edge_joint,
        "pass": bool(edge_joint.get("restriction_count") == 89 and
                     edge_joint.get("status") == "BLOCKED_RANK_DEFICIENT_JOINT_TEST" and
                     int(np.linalg.matrix_rank(edge_matrix, tol=1e-12)) == 50 and
                     0 < int(edge_joint.get("covariance_rank", 0)) <= 50 and
                     "chi2" not in edge_joint and "p_value_chi2" not in edge_joint)}
    expected_direct_labels, rebuilt_direct_functionals, rebuilt_direct_weights = (
        rebuild_direct_functionals(direct_membership.copy(), direct_fit.labels))
    if direct_labels != expected_direct_labels or direct_functionals.shape != (5, len(direct_fit.labels)):
        raise Blocked("direct functional label/order dimensions are invalid")
    observed_direct_estimates = direct_estimate_frame.estimate.to_numpy(float)
    expected_direct_estimates = direct_functionals @ direct_fit.treatment
    expected_direct_rows = [
        {"family": family, "pre_stock_weight": rebuilt_direct_weights[family],
         **target_result(direct_fit, rebuilt_direct_functionals[index])}
        for index, family in enumerate(sorted(rebuilt_direct_weights))
    ]
    expected_direct_rows.append({
        "family": "PRE_STOCK_AGGREGATE", "pre_stock_weight": 1.0,
        **target_result(direct_fit, rebuilt_direct_functionals[-1])})
    direct_frame_closure = verify_public_frame_reconstruction(
        "DIRECT_TAIL_ESTIMATES.csv", direct_estimate_frame,
        pd.DataFrame(expected_direct_rows),
        ("estimate", "standard_error", "z", "p_value_normal"))
    expected_direct_functional_frame = pd.DataFrame([
        {"functional_label": expected_direct_labels[i], "coefficient_label": label,
         "weight": float(rebuilt_direct_functionals[i, j])}
        for i in range(len(expected_direct_labels))
        for j, label in enumerate(direct_fit.labels)
    ])
    direct_functional_frame_closure = verify_public_frame_reconstruction(
        "DIRECT_TAIL_FUNCTIONALS.csv", direct_functional_frame,
        expected_direct_functional_frame, ())
    checks["authenticated_direct_functional_reconstruction"] = {
        "label_order_pass": direct_labels == expected_direct_labels,
        "functional_maximum_absolute_difference": float(np.max(np.abs(
            direct_functionals-rebuilt_direct_functionals))),
        "estimate_maximum_absolute_difference": float(np.max(np.abs(
            observed_direct_estimates-expected_direct_estimates))),
        "weight_sum": float(sum(rebuilt_direct_weights.values())),
        "public_estimate_frame": direct_frame_closure,
        "public_functional_frame": direct_functional_frame_closure,
        "pass": bool(np.array_equal(direct_functionals, rebuilt_direct_functionals) and
                     np.allclose(observed_direct_estimates, expected_direct_estimates,
                                 rtol=0, atol=1e-14) and
                     np.isclose(sum(rebuilt_direct_weights.values()), 1, rtol=0, atol=1e-15) and
                     direct_frame_closure["pass"] and
                     direct_functional_frame_closure["pass"])}
    direct_correction = len(direct_fit.influence)/(len(direct_fit.influence)-1)
    direct_influence = direct_fit.influence @ direct_functionals.T
    expected_direct_covariance_functional = direct_functionals @ direct_fit.covariance @ direct_functionals.T
    expected_direct_covariance_influence = direct_correction * direct_influence.T @ direct_influence
    expected_direct_draws = math.sqrt(direct_correction) * direct_xi @ direct_influence
    direct_closure = verify_linear_derived_closure(
        "direct tail", direct_labels, expected_direct_labels, direct_functionals,
        direct_fit.covariance, direct_fit.influence, direct_xi,
        direct_covariance, direct_draws, 1e-12)
    checks["direct_functional_covariance_influence_draw_closure"] = {**direct_closure,
        "functional_covariance_maximum_absolute_difference": float(np.max(np.abs(
            expected_direct_covariance_functional-direct_covariance))),
        "influence_covariance_maximum_absolute_difference": float(np.max(np.abs(
            expected_direct_covariance_influence-direct_covariance))),
        "draw_maximum_absolute_difference": float(np.max(np.abs(expected_direct_draws-direct_draws))),
        "label_order": direct_labels}
    expected_direct = direct_fit.influence @ direct_functional
    expected_family = pd.DataFrame({"family": direct_fit.bundle.frame.loc[
        direct_fit.active, ["occ_code", "family"]].drop_duplicates().sort_values("occ_code").family.to_numpy(),
                                    "influence": expected_direct}).groupby("family").influence.sum()
    observed_family = direct_family_closure.set_index("family").family_influence.reindex(expected_family.index)
    checks["direct_aggregate_influence_identity"] = {
        "maximum_absolute_difference": float(np.max(np.abs(expected_direct-direct_aggregate_influence))),
        "family_maximum_absolute_difference": float(np.max(np.abs(expected_family-observed_family))),
        "sum": float(np.sum(direct_aggregate_influence)),
        "covariance_from_influence": float(direct_correction*np.sum(direct_aggregate_influence**2)),
        "covariance_from_functional": float(direct_covariance[-1, -1]),
        "pass": bool(np.array_equal(expected_direct, direct_aggregate_influence)
                     and np.allclose(expected_family, observed_family, rtol=0, atol=1e-15)
                     and np.isclose(direct_correction*np.sum(direct_aggregate_influence**2),
                                    direct_covariance[-1, -1], rtol=1e-12, atol=1e-14))}
    rebuilt_pair_labels, rebuilt_pair_functionals, rebuilt_pair_weights = (
        rebuild_pairwise_aggregate_functionals(
            edges.copy(), rebuilt_edge_labels, rebuilt_edge_matrix))
    pair_closure = verify_linear_derived_closure(
        "pairwise aggregate", pair_labels, rebuilt_pair_labels, pair_functionals,
        heterogeneous.covariance, heterogeneous.influence, hetero_xi,
        pair_covariance, pair_draws, 1e-12)
    observed_pair_estimates = pair_estimate_frame.estimate.to_numpy(float)
    expected_pair_estimates = pair_functionals @ heterogeneous.treatment
    weight_columns = ["functional_label", "family", "quintile_low", "quintile_high",
                      "family_pair_stock", "family_weight", "edge_label"]
    observed_weights = pair_weight_frame[weight_columns].reset_index(drop=True)
    expected_weights = rebuilt_pair_weights[weight_columns].reset_index(drop=True)
    expected_pair_rows = []
    for pair_label, functional in zip(rebuilt_pair_labels, rebuilt_pair_functionals):
        selected = rebuilt_pair_weights.loc[
            rebuilt_pair_weights.functional_label.eq(pair_label)]
        expected_pair_rows.append({
            "functional_label": pair_label,
            "quintile_low": int(selected.quintile_low.iloc[0]),
            "quintile_high": int(selected.quintile_high.iloc[0]),
            "eligible_family_count": len(selected),
            **target_result(heterogeneous, functional),
            "weight_rule": "fixed_pair_endpoint_preperiod_stock",
        })
    pair_frame_closure = verify_public_frame_reconstruction(
        "PAIRWISE_AGGREGATES.csv", pair_estimate_frame,
        pd.DataFrame(expected_pair_rows),
        ("estimate", "standard_error", "z", "p_value_normal"))
    expected_pair_functional_frame = pd.concat([
        rebuilt_pair_weights.assign(
            record_type="family_weight", coefficient_label="",
            coefficient_weight=np.nan),
        pd.DataFrame([
            {"record_type": "coefficient_weight",
             "functional_label": rebuilt_pair_labels[i], "family": "",
             "quintile_low": int(rebuilt_pair_weights.loc[
                 rebuilt_pair_weights.functional_label.eq(rebuilt_pair_labels[i]),
                 "quintile_low"].iloc[0]),
             "quintile_high": int(rebuilt_pair_weights.loc[
                 rebuilt_pair_weights.functional_label.eq(rebuilt_pair_labels[i]),
                 "quintile_high"].iloc[0]),
             "family_pair_stock": np.nan, "family_weight": np.nan,
             "edge_label": "", "coefficient_label": label,
             "coefficient_weight": float(rebuilt_pair_functionals[i, j])}
            for i in range(len(rebuilt_pair_labels))
            for j, label in enumerate(heterogeneous.labels)
        ])], ignore_index=True)
    pair_functional_frame_closure = verify_public_frame_reconstruction(
        "PAIRWISE_AGGREGATE_FUNCTIONALS.csv", pair_functional_frame,
        expected_pair_functional_frame, ())
    checks["authenticated_pairwise_aggregate_reconstruction"] = {
        **pair_closure,
        "functional_maximum_absolute_difference": float(np.max(np.abs(
            pair_functionals-rebuilt_pair_functionals))),
        "estimate_maximum_absolute_difference": float(np.max(np.abs(
            observed_pair_estimates-expected_pair_estimates))),
        "weight_rows": len(observed_weights), "label_count": len(pair_labels),
        "public_estimate_frame": pair_frame_closure,
        "public_functional_frame": pair_functional_frame_closure,
        "pass": bool(pair_closure["pass"] and pair_labels == rebuilt_pair_labels and
                     np.array_equal(pair_functionals, rebuilt_pair_functionals) and
                     observed_weights.equals(expected_weights) and
                     np.allclose(observed_pair_estimates, expected_pair_estimates,
                                 rtol=0, atol=1e-14) and pair_frame_closure["pass"] and
                     pair_functional_frame_closure["pass"])}
    for fit in fits:
        checks[f"influence_score_closure::{fit.model_id}"] = {
            "maximum_absolute_sum": float(np.max(np.abs(fit.influence.sum(axis=0)))),
            "tolerance": tolerance,
            "pass": bool(np.max(np.abs(fit.influence.sum(axis=0))) <= tolerance)}
    if set(checks) != set(VALIDATION_CHECK_KEYS):
        raise Blocked("recomputed validation check-key inventory differs from frozen contract")
    failed = [label for label, result in checks.items() if result.get("pass") is not True]
    if failed:
        raise Blocked("recomputed validation failed: " + ", ".join(failed))
    result = {"schema_version": "yax-gate2-support-inference-validation-v1",
              "checks": checks, "failed_checks": failed,
              "status": "PASS_RECOMPUTED_VALIDATION"}
    result["validation_id"] = content_id("yaxvalidation_v1", result, ("validation_id",))
    return result


def write_json(path: pathlib.Path, value: Any) -> None:
    path.write_bytes(canonical_bytes(value) + b"\n")


def validate_publication_payload(spec: dict[str, Any], outputs: dict[str, Any],
                                 publication_kind: str) -> None:
    if publication_kind not in {SUCCESS_PUBLICATION, FAILURE_PUBLICATION}:
        raise Blocked("publication kind is outside the exact signed enum")
    expected = SUCCESS_OUTPUT_FILES if publication_kind == SUCCESS_PUBLICATION else FAILURE_OUTPUT_FILES
    if set(outputs) != set(expected) or len(outputs) != len(expected):
        missing, extra = sorted(expected-set(outputs)), sorted(set(outputs)-expected)
        raise Blocked(f"publication inventory differs; missing={missing}; extra={extra}")
    spec_inventory = spec.get("outputs", {}).get(
        "success_files" if publication_kind == SUCCESS_PUBLICATION else "failure_files")
    if spec_inventory != sorted(expected):
        raise Blocked("publication inventory differs from frozen spec order/content")
    logical_keys = [pathlib.Path(name).stem.lower() for name in outputs]
    if len(logical_keys) != len(set(logical_keys)):
        raise Blocked("publication contains duplicate logical keys")
    if publication_kind == FAILURE_PUBLICATION:
        evidence, validation = outputs["FAILURE_EVIDENCE.json"], outputs["FAILURE_VALIDATION.json"]
        if not isinstance(evidence, dict) or evidence.get("publication_class") != FAILURE_PUBLICATION or evidence.get(
                "scientific_result_claims") is not False or evidence.get("evidence_id") != content_id(
                    "yaxfailureevidence_v1", evidence, ("evidence_id",)):
            raise Blocked("failure evidence is not explicitly nonauthoritative")
        if (not isinstance(validation, dict) or validation.get("publication_class") != FAILURE_PUBLICATION or validation.get(
                "scientific_result_claims") is not False or validation.get("identity_verified") is not True or
                validation.get("evidence_id") != evidence["evidence_id"] or
                validation.get("validation_id") != content_id(
                    "yaxfailurevalidation_v1", validation, ("validation_id",))):
            raise Blocked("failure validation is incomplete")
        return
    validation = outputs["VALIDATION_REPORT.json"]
    if (not isinstance(validation, dict) or
            validation.get("status") != "PASS_RECOMPUTED_VALIDATION" or
            validation.get("failed_checks") != [] or
            validation.get("validation_id") != content_id(
                "yaxvalidation_v1", validation, ("validation_id",)) or
            not isinstance(validation.get("checks"), dict) or
            not validation["checks"] or any(row.get("pass") is not True
                                             for row in validation["checks"].values()
                                             if isinstance(row, dict)) or
            any(not isinstance(row, dict) for row in validation["checks"].values())):
        raise Blocked("success validation report is absent, incomplete, or not self-consistent")
    if (set(validation["checks"]) != set(VALIDATION_CHECK_KEYS) or
            spec.get("outputs", {}).get("validation_check_keys") != sorted(VALIDATION_CHECK_KEYS)):
        raise Blocked("success validation check-key inventory differs from frozen contract")
    failures = outputs["MODEL_FAILURES.json"]
    blocked = failures.get("blocked_components") if isinstance(failures, dict) else None
    if (not isinstance(failures, dict) or
            failures.get("status") != "EXPECTED_STRUCTURAL_RANK_BLOCK" or
            failures.get("numerical_fit_status") != "ALL_REQUIRED_A1_CERTIFICATES_PASS" or
            not isinstance(blocked, list) or len(blocked) != 1):
        raise Blocked("MODEL_FAILURES does not disclose the exact expected structural block")
    component = blocked[0]
    if (not isinstance(component, dict) or
            component.get("component") != "supported_edges_full_89_dimensional_joint_test" or
            component.get("disposition") != "EXPECTED_STRUCTURAL_RANK_BLOCK" or
            component.get("restriction_count") != 89 or component.get("test_status") !=
            "BLOCKED_RANK_DEFICIENT_JOINT_TEST" or component.get("chi2_or_p_value_emitted") is not False or
            component.get("functional_rank") != 50 or component.get("maximum_covariance_rank") != 50 or
            not isinstance(component.get("covariance_rank"), int) or not
            0 < component["covariance_rank"] <= 50 or
            component.get("additional_covariance_rank_deficiency") != 50-component["covariance_rank"]):
        raise Blocked("MODEL_FAILURES structural-block fields differ")
    heterogeneity_tests = outputs["HETEROGENEITY_JOINT_TESTS.json"]
    edge_test = (heterogeneity_tests.get("supported_edges_rank_aware_joint", {})
                 if isinstance(heterogeneity_tests, dict) else {})
    if (edge_test.get("status") != "BLOCKED_RANK_DEFICIENT_JOINT_TEST" or
            edge_test.get("restriction_count") != 89 or "chi2" in edge_test or
            "p_value_chi2" in edge_test or edge_test.get("covariance_rank") !=
            component.get("covariance_rank")):
        raise Blocked("89-edge joint artifact is inconsistent with structural disclosure")
    draw = outputs["COMMON_DRAW_BINDING.json"]
    if (not isinstance(draw, dict) or
            draw.get("draw_binding_id") != content_id("yaxdrawbinding_v1", draw,
            ("draw_binding_id",)) or draw.get("identity_storage_exact") is not True or
            draw.get("direct_formula_within_tolerance") is not True or
            draw.get("all_inference_draws_use_subsets_of_common_occupation_ordered_multiplier_matrix") is not True):
        raise Blocked("common-draw binding is incomplete or inconsistent")
    try:
        common_arrays = dict(outputs["COMMON_MULTIPLIERS.npz"])
        heterogeneity_arrays = dict(outputs["HETEROGENEITY_CENTERED_DRAWS.npz"])
        centered_arrays = dict(outputs["CENTERED_TARGET_DRAWS.npz"])
    except (TypeError, ValueError) as error:
        raise Blocked("stored draw artifacts are malformed") from error
    if (array_sha256(np.asarray(common_arrays.get("multipliers"))) != draw.get("multiplier_matrix_sha256") or
            list(np.asarray(common_arrays.get("draw_id"), dtype=str)) != [draw["draw_binding_id"]] or
            array_sha256(np.asarray(centered_arrays.get("pooled_Q2_Q5"))) != draw.get("pooled_draws_sha256") or
            array_sha256(np.asarray(centered_arrays.get("family_month_Q2_Q5"))) !=
            draw.get("family_month_draws_sha256") or
            array_sha256(np.asarray(centered_arrays.get("paired_Q2_Q5"))) != draw.get("paired_draws_sha256") or
            array_sha256(np.asarray(heterogeneity_arrays.get("supported_edge_draws"))) !=
            draw.get("supported_edge_draws_sha256") or
            array_sha256(np.asarray(heterogeneity_arrays.get("pairwise_aggregate_draws"))) !=
            draw.get("pairwise_aggregate_draws_sha256") or
            array_sha256(np.asarray(heterogeneity_arrays.get("direct_tail_functional_draws"))) !=
            draw.get("direct_tail_functional_draws_sha256")):
        raise Blocked("stored draws differ from the signed common-draw binding")
    try:
        stored_identity_exact = bool(np.array_equal(
            np.asarray(centered_arrays["paired_Q2_Q5"]),
            np.asarray(centered_arrays["family_month_Q2_Q5"])-
            np.asarray(centered_arrays["pooled_Q2_Q5"])))
    except (KeyError, TypeError, ValueError) as error:
        raise Blocked("stored paired-draw identity cannot be reconstructed") from error
    if not stored_identity_exact:
        raise Blocked("exact stored paired-draw identity failed")
    provenance = outputs["EXECUTION_PROVENANCE.json"]
    if (not isinstance(provenance, dict) or provenance.get("status") !=
            "PASS_COMMITTED_PRE_EXECUTION_AUTHORIZATION_AND_RUNTIME_BINDING" or
            provenance.get("provenance_id") != content_id(
                "yaxgate2provenance_v1", provenance, ("provenance_id",)) or
            provenance.get("executing_runner_sha256") != sha256_file(pathlib.Path(__file__)) or
            provenance.get("executing_spec_sha256") != sha256_file(SPEC_PATH) or
            provenance.get("repository_clean") is not True):
        raise Blocked("committed execution provenance is absent")


def publication_input_paths(args: argparse.Namespace) -> list[pathlib.Path]:
    names = ("canonical_spec", "a1_spec", "a1_runner", "a1_model_audit",
             "a1_dependency_release", "cells", "cells_receipt", "fixed_membership",
             "support_matrix", "support_edges", "direct_tail_membership",
             "pre_execution_authorization")
    paths = []
    for name in names:
        value = getattr(args, name, None)
        if not isinstance(value, pathlib.Path):
            raise Blocked("publication requires every authenticated input path")
        paths.append(value)
    safety_module = getattr(args, "artifact_safety", None)
    safety_path = pathlib.Path(getattr(safety_module, "__file__", ""))
    return [*paths, pathlib.Path(__file__).resolve(), SPEC_PATH.resolve(), safety_path]


def scan_staged_publication(staging: pathlib.Path, expected_names: set[str]) -> None:
    observed = {path.name for path in staging.iterdir()}
    if observed != expected_names:
        raise Blocked("staged publication inventory is not exact")
    for path in staging.iterdir():
        if path.is_symlink() or not path.is_file():
            raise Blocked("staged publication contains an indirect or non-file entry")
        if path.suffix in {".json", ".csv"}:
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeError as error:
                raise Blocked("text artifact is not valid UTF-8") from error
            kind = sensitive_string_kind(text)
            if kind is not None:
                raise Blocked(f"staged publication contains {kind}")
            if JSON_SECRET_FIELD_PATTERN.search(text):
                raise Blocked("staged publication contains an unredacted secret field")


def reserve_output_leaf(safety, target: pathlib.Path, repo_root: pathlib.Path,
                        input_paths: list[pathlib.Path]):
    """Reserve the A1-compatible leaf without pathname cleanup on failure.

    The hash-pinned A1 constructor has one reservation-exception branch that
    unlinks the lock by pathname.  This wrapper retains the lock (and any
    staging leaf) on every exception, matching this runner's no-automatic-
    cleanup contract while returning the same authenticated reservation type.
    """
    repo = repo_root.resolve(strict=True)
    raw_target = target.expanduser()
    if raw_target.name in {"", ".", ".."}:
        raise safety.OutputSafetyError("output must be a named leaf")
    parent = raw_target.parent.resolve(strict=True)
    resolved_target = parent / raw_target.name
    if safety.is_within(resolved_target, repo):
        raise safety.OutputSafetyError("output leaf must be outside the Git repository")
    for path in input_paths:
        resolved_input = path.expanduser().resolve(strict=True)
        if safety.paths_overlap(resolved_target, resolved_input):
            raise safety.OutputSafetyError("output leaf must be disjoint from every input path")
    if resolved_target.exists() or resolved_target.is_symlink():
        raise safety.OutputSafetyError("refusing a pre-existing output leaf")

    if any(not hasattr(os, name) for name in ("O_DIRECTORY", "O_NOFOLLOW")):
        raise safety.OutputSafetyError("descriptor-bound reservation is unavailable")
    parent_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        parent_flags |= os.O_CLOEXEC
    parent_fd = os.open(parent, parent_flags)
    lock_fd: int | None = None
    try:
        parent_descriptor = os.fstat(parent_fd)
        parent_path = os.lstat(parent)
        if ((parent_descriptor.st_dev, parent_descriptor.st_ino) !=
                (parent_path.st_dev, parent_path.st_ino)):
            raise safety.OutputSafetyError("output parent inode changed during reservation")
        lock_name = f".{resolved_target.name}.publish.lock"
        staging_name = f".{resolved_target.name}.staging-{uuid.uuid4().hex}"
        lock_token = uuid.uuid4().hex.encode("ascii")
        lock_flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
        if hasattr(os, "O_CLOEXEC"):
            lock_flags |= os.O_CLOEXEC
        try:
            lock_fd = os.open(lock_name, lock_flags, 0o600, dir_fd=parent_fd)
        except FileExistsError as error:
            raise safety.OutputSafetyError(
                "output leaf is already reserved by another run") from error
        os.write(lock_fd, lock_token)
        os.fsync(lock_fd)
        lock_stat = os.fstat(lock_fd)
        os.mkdir(staging_name, mode=0o700, dir_fd=parent_fd)
        staging_stat = os.stat(staging_name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISDIR(staging_stat.st_mode):
            raise safety.OutputSafetyError("reserved staging leaf is not a directory")
        return safety.AtomicOutputLeaf(
            resolved_target, parent / staging_name, parent / lock_name, lock_fd,
            int(lock_stat.st_dev), int(lock_stat.st_ino), lock_token,
            int(staging_stat.st_dev), int(staging_stat.st_ino),
        )
    except Exception:
        if lock_fd is not None:
            try:
                os.close(lock_fd)
            except OSError:
                pass
        raise
    finally:
        os.close(parent_fd)


def verify_reserved_directory_identity(directory_fd: int, destination: pathlib.Path,
                                       expected: tuple[int, int]) -> None:
    try:
        descriptor = os.fstat(directory_fd)
        path_state = os.lstat(destination)
    except OSError as error:
        raise Blocked("reserved output directory cannot be revalidated") from error
    if (not stat.S_ISDIR(descriptor.st_mode) or not stat.S_ISDIR(path_state.st_mode) or
            stat.S_ISLNK(path_state.st_mode) or
            (descriptor.st_dev, descriptor.st_ino) != expected or
            (path_state.st_dev, path_state.st_ino) != expected):
        raise Blocked("reserved output directory inode identity changed")


def sha256_descriptor(descriptor: int) -> str:
    digest = hashlib.sha256()
    while True:
        block = os.read(descriptor, 1 << 20)
        if not block:
            break
        digest.update(block)
    return digest.hexdigest()


def verify_destination_artifact(
        directory_fd: int, name: str, expected_identity: tuple[int, int],
        expected_content: dict[str, Any]) -> None:
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if hasattr(os, "O_CLOEXEC"):
        flags |= os.O_CLOEXEC
    try:
        descriptor = os.open(name, flags, dir_fd=directory_fd)
        try:
            state_before = os.fstat(descriptor)
            observed_hash = sha256_descriptor(descriptor)
            state_after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        path_state = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
    except OSError as error:
        raise Blocked("destination artifact cannot be opened with nofollow") from error
    states = (state_before, state_after, path_state)
    if (any(not stat.S_ISREG(state.st_mode) for state in states) or
            any((int(state.st_dev), int(state.st_ino)) != expected_identity
                for state in states) or
            any(int(state.st_size) != expected_content.get("byte_count")
                for state in states) or
            observed_hash != expected_content.get("sha256")):
        raise Blocked("destination artifact inode, size, or content differs")


def retain_reservation_without_path_cleanup(reservation) -> None:
    """Close only the held descriptor; retain lock/staging under ambiguity."""
    descriptor = getattr(reservation, "lock_fd", None)
    if descriptor is not None:
        try:
            os.close(descriptor)
        except OSError:
            pass
        reservation.lock_fd = None


def commit_with_receipt_marker(
        reservation, ordered_paths: list[pathlib.Path],
        expected_contents: dict[str, dict[str, Any]]) -> pathlib.Path:
    destination = reservation.target
    directory_fd: int | None = None
    owned: dict[str, tuple[int, int]] = {}
    try:
        if ({path.name for path in ordered_paths} != set(expected_contents) or
                not ordered_paths or ordered_paths[-1].name != "EXECUTION_RECEIPT.json"):
            raise Blocked("commit content inventory or receipt ordering is invalid")
        reservation.verify_publication_state()
        try:
            os.mkdir(destination, 0o700)
        except FileExistsError as error:
            raise Blocked("reserved output directory appeared before creation") from error
        required_flags = ("O_DIRECTORY", "O_NOFOLLOW")
        if any(not hasattr(os, name) for name in required_flags):
            raise Blocked("descriptor-relative nofollow publication is unavailable")
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        if hasattr(os, "O_CLOEXEC"):
            flags |= os.O_CLOEXEC
        directory_fd = os.open(destination, flags)
        descriptor = os.fstat(directory_fd)
        expected = (int(descriptor.st_dev), int(descriptor.st_ino))
        verify_reserved_directory_identity(directory_fd, destination, expected)
        for path in ordered_paths:
            reservation.verify_publication_state()
            verify_reserved_directory_identity(directory_fd, destination, expected)
            source = os.lstat(path)
            if not stat.S_ISREG(source.st_mode) or stat.S_ISLNK(source.st_mode):
                raise Blocked("staged publication source is not a direct regular file")
            expected_content = expected_contents[path.name]
            source_identity = (int(source.st_dev), int(source.st_ino))
            source_flags = os.O_RDONLY | os.O_NOFOLLOW
            if hasattr(os, "O_CLOEXEC"):
                source_flags |= os.O_CLOEXEC
            source_fd = os.open(path, source_flags)
            try:
                source_descriptor = os.fstat(source_fd)
                source_hash = sha256_descriptor(source_fd)
            finally:
                os.close(source_fd)
            if (not stat.S_ISREG(source_descriptor.st_mode) or
                    (int(source_descriptor.st_dev), int(source_descriptor.st_ino)) !=
                    source_identity or int(source_descriptor.st_size) !=
                    expected_content.get("byte_count") or
                    source_hash != expected_content.get("sha256")):
                raise Blocked("staged source inode, size, or content changed before link")
            try:
                os.link(path, path.name, dst_dir_fd=directory_fd, follow_symlinks=False)
            except FileExistsError as error:
                raise Blocked("reserved destination contains a competing filename") from error
            linked = os.stat(path.name, dir_fd=directory_fd, follow_symlinks=False)
            linked_identity = (int(linked.st_dev), int(linked.st_ino))
            if linked_identity != source_identity:
                raise Blocked("destination link does not preserve staged source identity")
            owned[path.name] = source_identity
            verify_destination_artifact(
                directory_fd, path.name, source_identity, expected_content)
            verify_reserved_directory_identity(directory_fd, destination, expected)
        verify_reserved_directory_identity(directory_fd, destination, expected)
        for name, identity in owned.items():
            verify_destination_artifact(
                directory_fd, name, identity, expected_contents[name])
        verify_reserved_directory_identity(directory_fd, destination, expected)
    except Exception:
        if directory_fd is not None:
            for name, identity in reversed(tuple(owned.items())):
                try:
                    current = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    if (current.st_dev, current.st_ino) == identity:
                        os.unlink(name, dir_fd=directory_fd)
                except OSError:
                    pass
            try:
                os.close(directory_fd)
            except OSError:
                pass
        retain_reservation_without_path_cleanup(reservation)
        raise
    os.close(directory_fd)
    retain_reservation_without_path_cleanup(reservation)
    return destination


def publish(args: argparse.Namespace, spec: dict[str, Any], outputs: dict[str, Any],
            publication_kind: str = SUCCESS_PUBLICATION) -> pathlib.Path:
    validate_publication_payload(spec, outputs, publication_kind)
    if not isinstance(args.run_id, str) or SAFE_RUN_ID_PATTERN.fullmatch(args.run_id) is None:
        raise Blocked("run_id is not a scheduler-unique safe output leaf")
    run_identity = build_run_identity(args)
    if run_identity != getattr(args, "run_identity", None):
        raise Blocked("publication run identity differs from authenticated execution")
    failure_only = publication_kind == FAILURE_PUBLICATION
    destination_leaf = args.run_id + ("__FAILURE_EVIDENCE" if failure_only else "")
    raw_parent = args.output_parent.expanduser()
    if not raw_parent.is_dir() or raw_parent.is_symlink():
        raise Blocked("output parent must be an existing direct directory")
    output_parent = raw_parent.resolve(strict=True)
    destination = output_parent / destination_leaf
    repo = repository_root()
    input_paths = publication_input_paths(args)
    safety = getattr(args, "artifact_safety", None)
    if safety is None:
        raise Blocked("hash-pinned A1 artifact_safety is absent")
    provenance = (outputs.get("EXECUTION_PROVENANCE.json") if not failure_only else
                  getattr(args, "execution_provenance", None))
    if not isinstance(provenance, dict) or provenance.get(
            "status") != "PASS_COMMITTED_PRE_EXECUTION_AUTHORIZATION_AND_RUNTIME_BINDING":
        raise Blocked("receipt cannot bind absent execution provenance")
    if provenance.get("run_identity") != run_identity:
        raise Blocked("execution provenance does not bind the intended run")
    verify_publication_capability(args, run_identity, provenance)
    try:
        reservation = reserve_output_leaf(safety, destination, repo, input_paths)
    except safety.OutputSafetyError as error:
        raise Blocked(str(error)) from error
    staging = reservation.staging
    try:
        for name, value in outputs.items():
            if pathlib.Path(name).name != name or name in {"RESULT_MANIFEST.json", "EXECUTION_RECEIPT.json"}:
                raise Blocked("output filename is invalid or reserved")
            path = staging / name
            if isinstance(value, pd.DataFrame):
                value.to_csv(path, index=False)
            elif isinstance(value, dict):
                write_json(path, value)
            elif isinstance(value, tuple) and name.endswith(".npz"):
                np.savez_compressed(path, **dict(value))
            else:
                raise Blocked(f"unsupported output object: {name}")
        artifact_records = []
        for path in sorted(staging.iterdir()):
            record = {"logical_key": path.stem.lower(), "filename": path.name,
                      "sha256": sha256_file(path), "byte_count": path.stat().st_size}
            record["result_id"] = content_id("yaxartifact_v1", record, ("result_id",))
            artifact_records.append(record)
        manifest = {"schema_version": "yax-gate2-support-inference-result-manifest-v1",
                    "spec_id": spec["spec_id"], "run_id": args.run_id,
                    "publication_kind": publication_kind,
                    "scientific_result_claims": not failure_only,
                    "artifacts": artifact_records}
        manifest["result_id"] = content_id("yaxresult_v1", manifest, ("result_id",))
        write_json(staging / "RESULT_MANIFEST.json", manifest)
        manifest_record = {"logical_key": "result_manifest", "filename": "RESULT_MANIFEST.json",
                           "sha256": sha256_file(staging / "RESULT_MANIFEST.json"),
                           "byte_count": (staging / "RESULT_MANIFEST.json").stat().st_size}
        manifest_record["result_id"] = content_id("yaxartifact_v1", manifest_record, ("result_id",))
        receipt = {"schema_version": "yax-gate2-support-inference-receipt-v1",
                   "status": ("NONAUTHORITATIVE_FAILURE_EVIDENCE_ONLY" if failure_only else
                              "CERTIFIED_ARTIFACT_PUBLICATION_WITH_EXPECTED_STRUCTURAL_RANK_BLOCK"),
                   "publication_kind": publication_kind,
                   "publication_protocol": "EXCLUSIVE_RESERVED_LEAF_WITH_RECEIPT_COMMIT_MARKER",
                   "scientific_result_claims": not failure_only,
                   "run_id": args.run_id, "spec_id": spec["spec_id"],
                   "spec_sha256": sha256_file(SPEC_PATH),
                   "executing_runner_sha256": provenance["executing_runner_sha256"],
                   "execution_provenance": provenance,
                   "run_identity": run_identity,
                   "authenticated_input_hashes": provenance["authenticated_input_hashes"],
                   "result_id": manifest["result_id"],
                   "result_manifest": manifest_record,
                   "artifact_count": len(artifact_records),
                   "retention": {
                       "staging_leaf_retained": True,
                       "sibling_lock_leaf_retained": True,
                       "staging_leaf": reservation.staging.name,
                       "sibling_lock_leaf": reservation.lock.name,
                       "automatic_path_cleanup": False,
                       "quota_behavior": "ONE_PRIVATE_STAGING_LEAF_AND_ONE_LOCK_LEAF_RETAINED_PER_PUBLICATION_ATTEMPT",
                       "cleanup_authority": "MANUAL_INODE_AUDITED_OPERATOR_CLEANUP_ONLY",
                   }}
        receipt["receipt_id"] = content_id("yaxreceipt_v1", receipt, ("receipt_id",))
        write_json(staging / "EXECUTION_RECEIPT.json", receipt)
        expected_contents = {
            record["filename"]: {"sha256": record["sha256"],
                                 "byte_count": record["byte_count"]}
            for record in artifact_records}
        expected_contents["RESULT_MANIFEST.json"] = {
            "sha256": manifest_record["sha256"],
            "byte_count": manifest_record["byte_count"]}
        expected_contents["EXECUTION_RECEIPT.json"] = {
            "sha256": sha256_file(staging / "EXECUTION_RECEIPT.json"),
            "byte_count": int(os.lstat(
                staging / "EXECUTION_RECEIPT.json").st_size)}
        expected_staging = set(outputs) | {"RESULT_MANIFEST.json", "EXECUTION_RECEIPT.json"}
        scan_staged_publication(staging, expected_staging)
        artifact_by_name = {record["filename"]: record for record in artifact_records}
        if set(artifact_by_name) != set(outputs) or set(expected_contents) != expected_staging:
            raise Blocked("manifest artifact inventory differs from staged outputs")
        for name, record in artifact_by_name.items():
            if (record.get("sha256") != expected_contents[name]["sha256"] or
                    record.get("byte_count") != expected_contents[name]["byte_count"]):
                raise Blocked("manifest content commitment differs from staged output")
        if (manifest_record.get("sha256") !=
                expected_contents["RESULT_MANIFEST.json"]["sha256"] or
                manifest_record.get("byte_count") !=
                expected_contents["RESULT_MANIFEST.json"]["byte_count"]):
            raise Blocked("receipt manifest commitment differs from staged manifest")
        if not failure_only:
            fresh = execution_provenance(
                args, spec, read_json(args.cells_receipt), args.runtime_contract)
            if not (canonical_bytes(fresh) == canonical_bytes(args.initial_execution_provenance) ==
                    canonical_bytes(args.final_execution_provenance) ==
                    canonical_bytes(args.execution_provenance) == canonical_bytes(provenance)):
                raise Blocked("initial, final, output, and prepublication provenance differ")
        ordered = [path for path in sorted(staging.iterdir())
                   if path.name != "EXECUTION_RECEIPT.json"]
        ordered.append(staging / "EXECUTION_RECEIPT.json")
        return commit_with_receipt_marker(reservation, ordered, expected_contents)
    except Exception:
        retain_reservation_without_path_cleanup(reservation)
        raise


def publish_failure_evidence(args: argparse.Namespace, spec: dict[str, Any],
                             failure: NumericalCertificationFailure) -> pathlib.Path:
    evidence = sanitized_numerical_evidence(failure.evidence)
    evidence["evidence_id"] = content_id("yaxfailureevidence_v1", evidence,
                                         ("evidence_id",))
    validation = {"schema_version": "yax-gate2-failure-evidence-validation-v1",
                  "publication_class": "NONAUTHORITATIVE_NUMERICAL_FAILURE_EVIDENCE_ONLY",
                  "scientific_result_claims": False,
                  "evidence_id": evidence["evidence_id"],
                  "has_failure_stage": bool(evidence.get("failure_stage")),
                  "has_model_id": bool(evidence.get("model_id")),
                  "identity_verified": evidence["evidence_id"] == content_id(
                      "yaxfailureevidence_v1", evidence, ("evidence_id",))}
    if not all((validation["has_failure_stage"], validation["has_model_id"],
                validation["identity_verified"])):
        raise Blocked("failure evidence could not be independently validated")
    validation["validation_id"] = content_id("yaxfailurevalidation_v1", validation,
                                             ("validation_id",))
    return publish(args, spec, {"FAILURE_EVIDENCE.json": evidence,
                                "FAILURE_VALIDATION.json": validation},
                   FAILURE_PUBLICATION)


def certified_fit_or_publish_failure(a1, bundle, analysis: dict[str, Any],
                                     args: argparse.Namespace, spec: dict[str, Any]) -> Fit:
    try:
        return certified_fit(a1, bundle, analysis)
    except NumericalCertificationFailure as failure:
        destination = publish_failure_evidence(args, spec, failure)
        raise Blocked(f"numerical certification failed; nonauthoritative evidence published: {destination.name}") from failure


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("canonical_spec", "a1_spec", "a1_runner", "a1_model_audit",
                 "a1_dependency_release", "cells", "cells_receipt", "fixed_membership",
                 "support_matrix", "support_edges", "direct_tail_membership",
                 "pre_execution_authorization", "output_parent"):
        parser.add_argument("--" + name.replace("_", "-"), type=pathlib.Path, required=True)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args(argv)


def _main_impl(argv: list[str] | None = None) -> int:
    global POST_CERTIFICATION_CONTEXT
    args = parse_args(argv)
    spec = read_json(SPEC_PATH)
    validate_frozen_spec(spec)
    if sha256_file(pathlib.Path(__file__)) != spec["implementation_sha256"]:
        raise Blocked("runner hash differs from frozen support-inference spec")
    args.run_identity = build_run_identity(args)
    require_file(args.a1_spec, spec["authenticated_inputs"]["a1_spec"]["sha256"], "a1_spec")
    require_file(args.a1_runner, spec["authenticated_inputs"]["a1_runner"]["sha256"], "a1_runner")
    pre_cell_analysis = read_json(args.a1_spec)
    a1 = load_a1(args.a1_runner, pre_cell_analysis.get("software", {}).get(
        "artifact_safety_sha256"))
    runtime_contract = verify_signed_a1_runtime_contract(a1, pre_cell_analysis)
    artifact_safety, artifact_safety_evidence = verify_artifact_safety_binding(
        a1, pre_cell_analysis, args.a1_runner)
    args.artifact_safety = artifact_safety
    args.artifact_safety_evidence = artifact_safety_evidence
    canonical, analysis, a1_audit, membership, cells, support, edges, direct = authenticate(args, spec)
    if canonical_bytes(analysis) != canonical_bytes(pre_cell_analysis):
        raise Blocked("signed A1 analysis changed while cells were authenticated")
    args.runtime_contract = runtime_contract
    initial_provenance = execution_provenance(
        args, spec, read_json(args.cells_receipt), runtime_contract)
    args.initial_execution_provenance = initial_provenance
    args.execution_provenance = initial_provenance
    issue_publication_capability(args, initial_provenance)
    profile_fits = {model: certified_fit_or_publish_failure(
                        a1, a1.model_bundle(cells, model), analysis, args, spec)
                    for model in ("pooled", "family_month")}
    tol = float(analysis["tolerances"]["target_coefficient_absolute_difference"])
    checkpoint_rows = []
    for fit in profile_fits.values():
        try:
            checkpoint_rows.extend(profile_checkpoint(fit, a1_audit, tol))
        except Exception as error:
            failure = certification_failure("A1_PROFILE_CHECKPOINT", fit.model_id,
                "A1 profile reproduction checkpoint failed", fit.audit, fit.pruning,
                fit.solver_rows, fit.profile_rows, fit.trajectory, fit.state_source, error)
            destination = publish_failure_evidence(args, spec, failure)
            raise Blocked(f"A1 checkpoint failed; nonauthoritative evidence published: {destination.name}") from error
    heterogeneous = certified_fit_or_publish_failure(
        a1, build_family_heterogeneous_bundle(a1, cells, support), analysis, args, spec)
    direct_fit = certified_fit_or_publish_failure(
        a1, build_direct_tail_bundle(a1, cells, direct), analysis, args, spec)
    continuous_bundle, continuous_occ = build_continuous_bundle(a1, cells, membership)
    continuous = certified_fit_or_publish_failure(a1, continuous_bundle, analysis, args, spec)
    occupations = sorted(cells.occ_code.unique())
    xi = common_rademacher(occupations, spec["inference"]["draws"], spec["inference"]["seed"])
    correction = math.sqrt(len(occupations)/(len(occupations)-1))
    outputs: dict[str, Any] = {}
    catalog = []
    all_fits = [*profile_fits.values(), heterogeneous, direct_fit, continuous]
    POST_CERTIFICATION_CONTEXT = {"args": args, "spec": spec, "fits": all_fits}
    for fit in all_fits:
        catalog.append({"model_id": fit.model_id, "a1_certificate": fit.audit["a1_certification"],
                        "labels": fit.labels, "reported_state_source": "trust-path",
                        "reference_state_source": "independent-damped-sparse-newton-irls",
                        "fresh_solver_comparison_status": fit.audit["solver_comparison"]["status"],
                        "fresh_profile_status": fit.audit["target_profile"]["status"],
                        "fresh_fitted_hessian_status": fit.audit["dual_candidate_fitted_hessian_audit"]["status"]})
    outputs["MODEL_CATALOG.json"] = {"schema_version": "yax-gate2-model-catalog-v1",
                                     "primary_estimate_source": "trust-path", "models": catalog}
    outputs["NUMERICAL_MODEL_AUDITS.json"] = {
        "schema_version": "yax-gate2-fresh-a1-model-audits-v1",
        "occupation_month_identifiers": "REDACTED_BY_CONTRACT",
        "models": [{"model_id": fit.model_id,
                    "audit": sanitized_numerical_evidence(fit.audit),
                    "profiled_face_rows": sanitized_numerical_evidence(fit.pruning)}
                   for fit in all_fits]}
    outputs["NUMERICAL_SOLVER_ROWS.csv"] = pd.DataFrame(
        [sanitized_numerical_evidence(row) for fit in all_fits for row in fit.solver_rows])
    outputs["NUMERICAL_PROFILE_ROWS.csv"] = pd.DataFrame(
        [row for fit in all_fits for row in fit.profile_rows])
    outputs["NUMERICAL_TRAJECTORIES.json"] = {
        "schema_version": "yax-gate2-fresh-a1-trajectories-v1",
        "models": {fit.model_id: fit.trajectory for fit in all_fits}}
    outputs["NUMERICAL_STATE_SOURCES.json"] = {
        "schema_version": "yax-gate2-state-sources-v1",
        "models": {fit.model_id: sanitized_numerical_evidence(fit.state_source)
                   for fit in all_fits}}
    outputs["A1_PROFILE_CHECKPOINTS.csv"] = pd.DataFrame(checkpoint_rows)
    profile_rows = []
    for fit in profile_fits.values():
        for index, label in enumerate(fit.labels[:4]):
            profile_rows.append({"model_id": fit.model_id, "target": label,
                                 **target_result(fit, np.eye(len(fit.labels))[index])})
    pooled, fam = profile_fits["pooled"], profile_fits["family_month"]
    pooled_occupations = sorted(pooled.bundle.frame.loc[pooled.active, "occ_code"].astype(str).unique())
    family_occupations = sorted(fam.bundle.frame.loc[fam.active, "occ_code"].astype(str).unique())
    if pooled_occupations != occupations or family_occupations != occupations:
        raise Blocked("S07 paired inference requires the complete common occupation order")
    paired_est = fam.treatment[:4] - pooled.treatment[:4]
    paired_if = fam.influence[:, :4] - pooled.influence[:, :4]
    paired_cov = len(occupations)/(len(occupations)-1) * paired_if.T @ paired_if
    paired_draws_direct = correction * xi @ paired_if
    for index, q in enumerate(range(2, 6)):
        variance = float(paired_cov[index, index])
        if variance <= 0:
            raise Blocked("paired movement has non-positive cluster variance")
        se = math.sqrt(variance)
        profile_rows.append({"model_id": "family_month_minus_pooled", "target": f"delta_Q{q}",
                             "estimate_source": "paired trust-path difference",
                             "estimate": float(paired_est[index]), "standard_error": se,
                             "z": float(paired_est[index]/se),
                             "p_value_normal": float(2*norm.sf(abs(paired_est[index]/se)))})
    profile_estimate_frame = pd.DataFrame(profile_rows)
    outputs["PROFILE_ESTIMATES.csv"] = profile_estimate_frame
    profile_labels = [f"Q{q}_x_post" for q in range(2, 6)]
    pooled_if = pooled.influence[:, :4]
    family_if = fam.influence[:, :4]
    pooled_covariance = pooled.covariance[:4, :4]
    family_covariance = fam.covariance[:4, :4]
    cross_covariance = len(occupations)/(len(occupations)-1) * pooled_if.T @ family_if
    covariance_rows = []
    covariance_rows += long_matrix("pooled", pooled_covariance, profile_labels, profile_labels)
    covariance_rows += long_matrix("family_month", family_covariance, profile_labels, profile_labels)
    covariance_rows += long_matrix("pooled_rows_by_family_month_columns", cross_covariance,
                                   profile_labels, profile_labels)
    covariance_rows += long_matrix("family_month_rows_by_pooled_columns", cross_covariance.T,
                                   profile_labels, profile_labels)
    covariance_rows += long_matrix("family_month_minus_pooled", paired_cov,
                                   [f"delta_Q{q}" for q in range(2, 6)],
                                   [f"delta_Q{q}" for q in range(2, 6)])
    outputs["PROFILE_COVARIANCE.csv"] = pd.DataFrame(covariance_rows)
    pooled_draws = correction * xi @ pooled_if
    family_draws = correction * xi @ family_if
    paired_draws = family_draws - pooled_draws
    if not np.allclose(paired_draws_direct, paired_draws, rtol=1e-12, atol=1e-14):
        raise Blocked("paired draws are not the exact common-draw difference")
    interval_output = []
    interval_output += interval_rows("pooled", profile_labels, pooled.treatment[:4],
                                     pooled_covariance, pooled_draws)
    interval_output += interval_rows("family_month", profile_labels, fam.treatment[:4],
                                     family_covariance, family_draws)
    interval_output += interval_rows("family_month_minus_pooled",
                                     [f"delta_Q{q}" for q in range(2, 6)], paired_est,
                                     paired_cov, paired_draws)
    profile_interval_frame = pd.DataFrame(interval_output)
    outputs["PROFILE_INTERVALS.csv"] = profile_interval_frame
    outputs["PROFILE_JOINT_TESTS.json"] = {
        "pooled": rank_aware_test(pooled.treatment[:4], pooled_covariance, pooled_draws),
        "pooled_simultaneous": simultaneous_summary(pooled.treatment[:4], pooled_covariance, pooled_draws),
        "family_month": rank_aware_test(fam.treatment[:4], family_covariance, family_draws),
        "family_month_simultaneous": simultaneous_summary(fam.treatment[:4], family_covariance, family_draws),
        "paired_movement": rank_aware_test(paired_est, paired_cov, paired_draws),
        "paired_simultaneous": simultaneous_summary(paired_est, paired_cov, paired_draws)}
    draw_binding = {"occupation_order_sha256": hashlib.sha256(canonical_bytes(occupations)).hexdigest(),
                    "multiplier_matrix_sha256": array_sha256(xi),
                    "pooled_draws_sha256": array_sha256(pooled_draws),
                    "family_month_draws_sha256": array_sha256(family_draws),
                    "paired_draws_sha256": array_sha256(paired_draws),
                    "identity": "paired_draws == family_month_draws - pooled_draws",
                    "identity_storage_exact": bool(np.array_equal(
                        paired_draws, family_draws-pooled_draws)),
                    "direct_formula_maximum_absolute_residual": float(np.max(np.abs(
                        paired_draws-paired_draws_direct))),
                    "direct_formula_tolerance": 1e-14,
                    "direct_formula_within_tolerance": bool(np.allclose(
                        paired_draws, paired_draws_direct, rtol=1e-12, atol=1e-14))}
    draw_binding["draw_binding_id"] = content_id("yaxdrawbinding_v1", draw_binding,
                                                 ("draw_binding_id",))
    outputs["COMMON_DRAW_BINDING.json"] = draw_binding
    edge_labels, edge_matrix = rebuild_edge_functionals(support, edges, heterogeneous.labels)
    edge_rows = []
    for edge, edge_label, functional in zip(edges.itertuples(index=False), edge_labels, edge_matrix):
        edge_rows.append({"family": str(edge.family).zfill(2),
                          "quintile_low": int(edge.quintile_low),
                          "quintile_high": int(edge.quintile_high),
                          "functional_label": edge_label,
                          **target_result(heterogeneous, functional)})
    outputs["SUPPORTED_PAIRWISE_CONTRASTS.csv"] = pd.DataFrame(edge_rows)
    outputs["SUPPORTED_EDGE_FUNCTIONALS.csv"] = pd.DataFrame([
        {"functional_label": edge_labels[i], "coefficient_label": label,
         "weight": float(edge_matrix[i, j])}
        for i in range(len(edge_labels)) for j, label in enumerate(heterogeneous.labels)])
    edge_covariance = edge_matrix @ heterogeneous.covariance @ edge_matrix.T
    outputs["SUPPORTED_EDGE_COVARIANCE.csv"] = pd.DataFrame(
        long_matrix("supported_edges", edge_covariance, edge_labels, edge_labels))
    pair_labels, pair_functionals, pair_weights = rebuild_pairwise_aggregate_functionals(
        edges, edge_labels, edge_matrix)
    aggregate_rows = []
    for pair_label, functional in zip(pair_labels, pair_functionals):
        selected = pair_weights.loc[pair_weights.functional_label.eq(pair_label)]
        aggregate_rows.append({"functional_label": pair_label,
                               "quintile_low": int(selected.quintile_low.iloc[0]),
                               "quintile_high": int(selected.quintile_high.iloc[0]),
                               "eligible_family_count": len(selected),
                               **target_result(heterogeneous, functional),
                               "weight_rule": "fixed_pair_endpoint_preperiod_stock"})
    outputs["PAIRWISE_AGGREGATES.csv"] = pd.DataFrame(aggregate_rows)
    outputs["PAIRWISE_AGGREGATE_FUNCTIONALS.csv"] = pd.concat([
        pair_weights.assign(record_type="family_weight", coefficient_label="", coefficient_weight=np.nan),
        pd.DataFrame([{"record_type": "coefficient_weight", "functional_label": pair_labels[i],
                       "family": "", "quintile_low": int(pair_weights.loc[
                           pair_weights.functional_label.eq(pair_labels[i]), "quintile_low"].iloc[0]),
                       "quintile_high": int(pair_weights.loc[
                           pair_weights.functional_label.eq(pair_labels[i]), "quintile_high"].iloc[0]),
                       "family_pair_stock": np.nan,
                       "family_weight": np.nan, "edge_label": "",
                       "coefficient_label": label, "coefficient_weight": float(pair_functionals[i, j])}
                      for i in range(len(pair_labels))
                      for j, label in enumerate(heterogeneous.labels)])], ignore_index=True)
    pair_covariance = pair_functionals @ heterogeneous.covariance @ pair_functionals.T
    outputs["PAIRWISE_AGGREGATE_COVARIANCE.csv"] = pd.DataFrame(
        long_matrix("pairwise_aggregates", pair_covariance, pair_labels, pair_labels))
    direct_labels, direct_functionals, weights = rebuild_direct_functionals(direct, direct_fit.labels)
    w = direct_functionals[-1]
    direct_rows = []
    for family, value, unit in zip(sorted(weights), [weights[key] for key in sorted(weights)],
                                   direct_functionals[:-1]):
        direct_rows.append({"family": family, "pre_stock_weight": value,
                            **target_result(direct_fit, unit)})
    direct_rows.append({"family": "PRE_STOCK_AGGREGATE", "pre_stock_weight": 1.0,
                        **target_result(direct_fit, w)})
    outputs["DIRECT_TAIL_ESTIMATES.csv"] = pd.DataFrame(direct_rows)
    outputs["DIRECT_TAIL_FUNCTIONALS.csv"] = pd.DataFrame([
        {"functional_label": direct_labels[i], "coefficient_label": label,
         "weight": float(direct_functionals[i, j])}
        for i in range(len(direct_labels)) for j, label in enumerate(direct_fit.labels)])
    direct_functional_covariance = direct_functionals @ direct_fit.covariance @ direct_functionals.T
    outputs["DIRECT_TAIL_COVARIANCE.csv"] = pd.DataFrame(
        long_matrix("direct_tail_functionals", direct_functional_covariance,
                    direct_labels, direct_labels))
    continuous_result = target_result(continuous, np.eye(len(continuous.labels))[0])
    scaled = exact_sd_reparameterizations(continuous.treatment[0], continuous_occ)
    scaled["raw_beta_standard_error"] = continuous_result["standard_error"]
    scaled["within_family_sd_standard_error"] = (
        continuous_result["standard_error"] * scaled["within_family_sd"])
    scaled["family_webb_residual_sd_standard_error"] = (
        continuous_result["standard_error"] * scaled["family_webb_residual_sd"])
    outputs["CONTINUOUS_WITHIN_FAMILY.json"] = scaled
    reference_probabilities = {fit.model_id: aligned_reference_probability(pooled, fit)
                               for fit in all_fits}
    pooled_keys = set(map(tuple, pooled.bundle.frame.loc[pooled.active, ["occ_code", "month"]].to_numpy()))
    same_support = {fit.model_id: set(map(tuple, fit.bundle.frame.loc[
        fit.active, ["occ_code", "month"]].to_numpy())) == pooled_keys for fit in all_fits}
    outputs["INFORMATION_DIAGNOSTICS.csv"] = pd.concat(
        [information_panel(fit, reference_probabilities[fit.model_id], same_support[fit.model_id])
         for fit in all_fits],
        ignore_index=True)
    occ_info, fam_info = [], []
    for fit in all_fits:
        for panel, probability in (("half", None), ("own", None),
                                   ("fixed_pooled_within_support", reference_probabilities[fit.model_id])):
            oi, fi = information_contributions(fit, panel, probability)
            occ_info.append(oi)
            fam_info.append(fi)
    outputs["OCCUPATION_INFORMATION.csv"] = pd.concat(occ_info, ignore_index=True)
    outputs["FAMILY_INFORMATION.csv"] = pd.concat(fam_info, ignore_index=True)
    influence_rows, family_rows = [], []
    for fit in [pooled, fam, heterogeneous, direct_fit, continuous]:
        fit_occs = sorted(fit.bundle.frame.loc[fit.active, "occ_code"].astype(str).unique())
        for oi, occ in enumerate(fit_occs):
            for ti, label in enumerate(fit.labels):
                influence_rows.append({"model_id": fit.model_id, "occupation_code": occ,
                                       "target": label, "raw_influence": fit.influence[oi, ti],
                                       "approx_delete_change": -fit.influence[oi, ti]})
        temp = pd.DataFrame(fit.influence, index=fit_occs, columns=fit.labels)
        fammap = fit.bundle.frame[["occ_code", "family"]].drop_duplicates().set_index("occ_code").family
        temp["family"] = temp.index.map(fammap)
        grouped = temp.groupby("family").sum(numeric_only=True)
        for family, row in grouped.iterrows():
            for label in fit.labels:
                family_rows.append({"model_id": fit.model_id, "family": family,
                                    "target": label, "family_influence": row[label]})
    outputs["OCCUPATION_INFLUENCE.csv"] = pd.DataFrame(influence_rows)
    outputs["FAMILY_INFLUENCE.csv"] = pd.DataFrame(family_rows)
    direct_codes = sorted(direct_fit.bundle.frame.loc[direct_fit.active, "occ_code"].astype(str).unique())
    direct_family_map = direct_fit.bundle.frame[["occ_code", "family"]].drop_duplicates().set_index(
        "occ_code").family
    direct_aggregate_influence = direct_fit.influence @ w
    direct_aggregate_rows = pd.DataFrame({"occupation_code": direct_codes,
        "family": [direct_family_map.loc[code] for code in direct_codes],
        "raw_influence": direct_aggregate_influence,
        "approx_delete_change": -direct_aggregate_influence})
    direct_family_closure = direct_aggregate_rows.groupby("family", as_index=False).raw_influence.sum().rename(
        columns={"raw_influence": "family_influence"})
    outputs["DIRECT_AGGREGATE_OCCUPATION_INFLUENCE.csv"] = direct_aggregate_rows
    outputs["DIRECT_AGGREGATE_FAMILY_INFLUENCE.csv"] = direct_family_closure
    outputs["DIRECT_AGGREGATE_INFLUENCE_CLOSURE.json"] = {
        "occupation_sum": float(direct_aggregate_rows.raw_influence.sum()),
        "family_sum": float(direct_family_closure.family_influence.sum()),
        "absolute_difference": float(abs(direct_aggregate_rows.raw_influence.sum()-
                                         direct_family_closure.family_influence.sum())),
        "pass": bool(np.isclose(direct_aggregate_rows.raw_influence.sum(),
                                direct_family_closure.family_influence.sum(), rtol=0, atol=1e-15))}
    family_influence_frame = pd.DataFrame(family_rows)
    pooled_q5 = family_influence_frame.loc[(family_influence_frame.model_id == "pooled") &
                                            (family_influence_frame.target == "Q5_x_post")]
    family_q5 = family_influence_frame.loc[(family_influence_frame.model_id == "family_month") &
                                            (family_influence_frame.target == "Q5_x_post")]
    paired_family = pooled_q5[["family", "family_influence"]].merge(
        family_q5[["family", "family_influence"]], on="family", suffixes=("_pooled", "_family"))
    paired_family["family_influence"] = paired_family.family_influence_family - paired_family.family_influence_pooled
    selected_families: set[str] = set()
    selection_records = []
    for target, table in (("pooled_Q5", pooled_q5), ("paired_Q5_movement", paired_family)):
        for direction, index in (("largest_positive", table.family_influence.idxmax()),
                                 ("largest_negative", table.family_influence.idxmin())):
            family = str(table.loc[index, "family"])
            selected_families.add(family)
            selection_records.append({"target": target, "direction": direction, "family": family,
                                      "family_influence": float(table.loc[index, "family_influence"])})
    outputs["PATH_SELECTION.json"] = {"rule": "positive/negative extremes for pooled and paired Q5; deduplicated",
                                      "selected_families": sorted(selected_families),
                                      "records": selection_records}
    monthly, quarterly = aggregate_family_quintile_paths(cells, support)
    outputs["RAW_FAMILY_QUINTILE_PATHS_MONTHLY.csv"] = monthly
    outputs["FAMILY_QUINTILE_PATHS_QUARTERLY.csv"] = quarterly
    outputs["COMMON_MULTIPLIERS.npz"] = (("occupation_codes", np.asarray(occupations)),
                                         ("multipliers", xi),
                                         ("draw_id", np.asarray([draw_binding["draw_binding_id"]])))
    outputs["CENTERED_TARGET_DRAWS.npz"] = (
        ("pooled_labels", np.asarray(profile_labels)),
        ("family_month_labels", np.asarray(profile_labels)),
        ("paired_labels", np.asarray([f"delta_Q{q}" for q in range(2, 6)])),
        ("paired_Q2_Q5", paired_draws),
        ("pooled_Q2_Q5", pooled_draws),
        ("family_month_Q2_Q5", family_draws))
    direct_positions = [occupations.index(code) for code in direct_codes]
    direct_xi = xi[:, direct_positions]
    direct_functional_draws = math.sqrt(len(direct_codes)/(len(direct_codes)-1)) * (
        direct_xi @ direct_fit.influence @ direct_functionals.T)
    direct_draws = direct_functional_draws[:, :4]
    hetero_codes = sorted(heterogeneous.bundle.frame.loc[heterogeneous.active, "occ_code"].astype(str).unique())
    hetero_positions = [occupations.index(code) for code in hetero_codes]
    hetero_xi = xi[:, hetero_positions]
    hetero_correction = math.sqrt(len(hetero_codes)/(len(hetero_codes)-1))
    hetero_draws = hetero_correction * hetero_xi @ heterogeneous.influence[:, :-1]
    edge_estimates = edge_matrix @ heterogeneous.treatment
    edge_draws = hetero_correction * hetero_xi @ heterogeneous.influence @ edge_matrix.T
    pair_draws = hetero_correction * hetero_xi @ heterogeneous.influence @ pair_functionals.T
    draw_binding.pop("draw_binding_id", None)
    draw_binding.update({
        "supported_edge_draws_sha256": array_sha256(edge_draws),
        "pairwise_aggregate_draws_sha256": array_sha256(pair_draws),
        "direct_tail_functional_draws_sha256": array_sha256(direct_functional_draws),
        "heterogeneous_occupation_order_sha256": hashlib.sha256(
            canonical_bytes(hetero_codes)).hexdigest(),
        "direct_tail_occupation_order_sha256": hashlib.sha256(
            canonical_bytes(direct_codes)).hexdigest(),
        "all_inference_draws_use_subsets_of_common_occupation_ordered_multiplier_matrix": True,
    })
    draw_binding["draw_binding_id"] = content_id(
        "yaxdrawbinding_v1", draw_binding, ("draw_binding_id",))
    outputs["COMMON_MULTIPLIERS.npz"] = (
        ("occupation_codes", np.asarray(occupations)), ("multipliers", xi),
        ("draw_id", np.asarray([draw_binding["draw_binding_id"]])))
    edge_functional_rank = int(np.linalg.matrix_rank(edge_matrix, tol=1e-12))
    edge_joint = rank_aware_test(edge_estimates, edge_covariance, edge_draws)
    edge_covariance_rank = int(edge_joint.get("covariance_rank", -1))
    if edge_functional_rank != 50 or not 0 < edge_covariance_rank <= edge_functional_rank:
        raise Blocked("edge functional/covariance rank violates the exact structural bound")
    if not (edge_joint.get("status") == "BLOCKED_RANK_DEFICIENT_JOINT_TEST" and
            edge_joint.get("restriction_count") == 89 and
            0 < edge_covariance_rank <= 50 and
            "chi2" not in edge_joint and "p_value_chi2" not in edge_joint):
        raise Blocked("89-edge joint-test disposition differs from expected structural rank block")
    outputs["HETEROGENEITY_JOINT_TESTS.json"] = {
        "family_heterogeneous_exposure_coefficients": rank_aware_test(
            heterogeneous.treatment[:-1], heterogeneous.covariance[:-1, :-1], hetero_draws),
        "supported_edges_rank_aware_joint": edge_joint,
        "supported_edges_simultaneous": simultaneous_summary(
            edge_estimates, edge_covariance, edge_draws),
        "direct_tail_four_family_effects": rank_aware_test(
            direct_fit.treatment[:4], direct_fit.covariance[:4, :4], direct_draws),
        "direct_tail_simultaneous": simultaneous_summary(
            direct_fit.treatment[:4], direct_fit.covariance[:4, :4], direct_draws)}
    outputs["HETEROGENEITY_CENTERED_DRAWS.npz"] = (
        ("supported_edge_labels", np.asarray(edge_labels)), ("supported_edge_draws", edge_draws),
        ("pairwise_aggregate_labels", np.asarray(pair_labels)),
        ("pairwise_aggregate_draws", pair_draws),
        ("direct_tail_labels", np.asarray(direct_labels)),
        ("direct_tail_functional_draws", direct_functional_draws))
    outputs["MODEL_FAILURES.json"] = {
        "status": "EXPECTED_STRUCTURAL_RANK_BLOCK",
        "numerical_fit_status": "ALL_REQUIRED_A1_CERTIFICATES_PASS",
        "artifact_publication_status": "ELIGIBLE_WITH_DISCLOSED_INFERENCE_LIMITATION",
        "blocked_components": [{"component": "supported_edges_full_89_dimensional_joint_test",
            "disposition": "EXPECTED_STRUCTURAL_RANK_BLOCK",
            "restriction_count": edge_joint["restriction_count"],
            "functional_rank": edge_functional_rank,
            "maximum_covariance_rank": edge_functional_rank,
            "covariance_rank": edge_joint["covariance_rank"],
            "additional_covariance_rank_deficiency": edge_functional_rank-edge_covariance_rank,
            "test_status": edge_joint["status"], "chi2_or_p_value_emitted": False}],
        "note": "The 89 edge functionals have exact rank 50 (=72 supported cells - 22 families); covariance rank cannot exceed 50. Any further covariance deficiency is disclosed; no full 89-dimensional chi-square or p-value is emitted."}
    validation = recompute_validation(
        all_fits, pooled, fam, xi, paired_cov, paired_draws, profile_estimate_frame,
        profile_interval_frame, cross_covariance, pooled_draws, family_draws,
        monthly, quarterly, w, direct_aggregate_influence, direct_family_closure,
        heterogeneous, edge_matrix, edge_covariance, edge_draws, hetero_xi, edge_labels,
        direct_fit, direct_functionals, direct_functional_covariance, direct_functional_draws,
        direct_xi, direct_labels, edge_joint, support, edges, direct,
        outputs["SUPPORTED_PAIRWISE_CONTRASTS.csv"], outputs["SUPPORTED_EDGE_FUNCTIONALS.csv"],
        outputs["DIRECT_TAIL_ESTIMATES.csv"], outputs["DIRECT_TAIL_FUNCTIONALS.csv"],
        pair_labels, pair_functionals, pair_covariance, pair_draws,
        outputs["PAIRWISE_AGGREGATES.csv"], pair_weights,
        outputs["PAIRWISE_AGGREGATE_FUNCTIONALS.csv"], checkpoint_rows, tol)
    validation["requirement_scope"] = {
        "S03": "support-respecting family heterogeneity and direct-tail estimands",
        "S04": "continuous exposure and information diagnostics",
        "S06": "occupation/family influence and calendar-safe descriptive paths",
        "S07": "pooled versus family-month profile with paired simultaneous inference",
        "S05": "UNRESOLVED_OUT_OF_SCOPE",
        "L01": "UNRESOLVED_OUT_OF_SCOPE"}
    validation["validation_id"] = content_id("yaxvalidation_v1", validation,
                                             ("validation_id",))
    outputs["VALIDATION_REPORT.json"] = validation
    final_provenance = execution_provenance(
        args, spec, read_json(args.cells_receipt), runtime_contract)
    if canonical_bytes(final_provenance) != canonical_bytes(initial_provenance):
        raise Blocked("repository, runtime, authorization, or authenticated inputs changed during execution")
    args.final_execution_provenance = final_provenance
    args.execution_provenance = final_provenance
    outputs["EXECUTION_PROVENANCE.json"] = final_provenance
    publish(args, spec, outputs)
    POST_CERTIFICATION_CONTEXT = None
    return 0


def main(argv: list[str] | None = None) -> int:
    global POST_CERTIFICATION_CONTEXT
    try:
        return _main_impl(argv)
    except Exception as error:
        context = POST_CERTIFICATION_CONTEXT
        POST_CERTIFICATION_CONTEXT = None
        if context is None:
            raise
        fits: list[Fit] = context["fits"]
        failure = certification_failure(
            "POST_CERTIFICATION_PIPELINE", "support_inference_pipeline",
            "post-certification state, influence, information, derived-validation, or publication failure",
            audit={"models": [{"model_id": fit.model_id, "audit": fit.audit} for fit in fits]},
            pruning=[row for fit in fits for row in fit.pruning],
            solver_rows=[row for fit in fits for row in fit.solver_rows],
            profile_rows=[row for fit in fits for row in fit.profile_rows],
            trajectory={fit.model_id: fit.trajectory for fit in fits},
            state_source={fit.model_id: fit.state_source for fit in fits}, error=error)
        try:
            destination = publish_failure_evidence(context["args"], context["spec"], failure)
        except Exception as publication_error:
            raise Blocked(
                f"post-certification pipeline failed and nonauthoritative evidence could not be published: "
                f"{publication_error}") from error
        raise Blocked(
            f"post-certification pipeline failed; nonauthoritative evidence published: "
            f"{destination.name}") from error


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Blocked as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
