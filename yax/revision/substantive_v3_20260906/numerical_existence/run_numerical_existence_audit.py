#!/usr/bin/env python3
"""Audit existence and convergence of the YAX grouped-binomial models.

This program implements V3 requirements N01--N03.  It does not build CPS
microdata.  It accepts only a balanced, authenticated aggregate cell file and
never writes row-level data.  See ANALYSIS_SPEC_A1.json and README.md.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
import pathlib
import platform
import re
import subprocess
import sys
from typing import Any, Iterable

import numpy as np
import pandas as pd
import pytest

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from artifact_safety import AtomicOutputLeaf, OutputSafetyError

try:
    import scipy
    from scipy import sparse
    from scipy.linalg import qr
    from scipy.optimize import linprog, minimize
    from scipy.sparse.linalg import ArpackNoConvergence, eigsh, splu
    from scipy.special import expit
except ImportError as error:  # pragma: no cover - exercised on an SCC image only
    raise RuntimeError(
        "N03 BLOCKED: scipy is unavailable; do not substitute another objective "
        "or claim a same-objective solver comparison"
    ) from error


AUDIT_SCHEMA = "yax-numerical-existence-audit-v1"
CELL_SCHEMA = "yax-numerical-cells-v1"
RECEIPT_SCHEMA = "yax-numerical-cells-receipt-v1"
SPEC_PREFIX = "yaxspec_v1_"
AUDIT_SPEC_PREFIX = "yaxnumspec_v1_"
PRE_EXECUTION_AUTHORIZATION_SCHEMA = "yax-gate1-pre-execution-authorization-v1"
PRE_EXECUTION_AUTHORIZATION_STATUS = "AUTHORIZED_FRESH_GATE1_EXECUTION"
PRE_EXECUTION_AUTHORIZATION_PREFIX = "yaxgate1auth_v1_"
CELL_SPEC_PREFIX = "yaxcellspec_v1_"
CELL_SPEC_SCHEMA = "yax-gate1-cell-build-spec-v1"
MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
CANONICAL_SPEC_SHA256 = "34b8a785a267d334643b04d3ff35f47bf30780068e126e0a63dd14b0079c5e8b"
COMMAND_TEMPLATE = (
    "<YAX_PYTHON_BIN> -I yax/revision/substantive_v3_20260906/numerical_existence/"
    "run_numerical_existence_audit.py --canonical-spec <YAX_REPO_ROOT>/yax/revision/"
    "substantive_v3_20260906/contracts/specs/canonical_baseline_reproduction_v2.json "
    "--analysis-spec <YAX_REPO_ROOT>/yax/revision/substantive_v3_20260906/"
    "numerical_existence/ANALYSIS_SPEC_A1.json --cells <YAX_GATE1_CELLS_LEAF>/aggregate_cells.csv "
    "--cells-receipt <YAX_GATE1_CELLS_LEAF>/EXECUTION_RECEIPT.json "
    "--legacy-engine <YAX_REPO_ROOT>/dax/memo/power_calcs/young_relative_employment_power.py "
    "--output-parent <YAX_V3_RUN_ROOT>"
)
COMMAND_BINDING_SCHEMA = "yax-execution-command-binding-v2"
COMMAND_BINDING_STATUS = "RUNNER_RECORDED_HASH_CONSISTENT"
MODULE_KEY = "numerical"
JOB_ID_PATTERN = re.compile(r"^[1-9][0-9]{0,19}$")
RUN_ID_PATTERN = re.compile(r"^gate1_numerical_sge_([1-9][0-9]{0,19})$")
EXPECTED_PYTHON_RESOLVED_SHA256 = (
    "0887a2530329cef5a3a6b7c83c76590da9730f98f1e68497096bc05f20b92aa7"
)
EXPECTED_GIT_PATH = pathlib.Path("/usr/bin/git")
EXPECTED_GIT_SHA256 = (
    "507917bbb5d24123c8e11df46df1d32483da1ce6420aa7ba7dd17de8ccd13a9e"
)
EXPECTED_GIT_VERSION = "git version 2.43.7"
SANITIZED_GIT_ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
IMPORT_AFFECTING_ENVIRONMENT = (
    "PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE", "PYTHONSTARTUP",
)
EXPECTED_PRODUCTION_FLAGS = (
    "--canonical-spec", "--analysis-spec", "--cells", "--cells-receipt",
    "--legacy-engine", "--output-parent",
)
PRE_EXECUTION_AUTHORIZATION_REL = pathlib.Path(
    "yax/revision/substantive_v3_20260906/gate1_transfer/"
    "PRE_EXECUTION_AUTHORIZATION.json"
)
CELL_SPEC_REL = pathlib.Path(
    "yax/revision/substantive_v3_20260906/gate1_cells/CELL_BUILD_SPEC.json"
)
TARGET_SPEC_REL = pathlib.Path(
    "yax/revision/substantive_v3_20260906/gate1_target/TARGET_AUDIT_SPEC.json"
)
CELL_CODE_REL = pathlib.Path(
    "yax/revision/substantive_v3_20260906/gate1_cells/run_gate1_cells.py"
)
TARGET_CODE_REL = pathlib.Path(
    "yax/revision/substantive_v3_20260906/gate1_target/run_exact_target_audit.py"
)
A1_SPEC_REL = pathlib.Path(
    "yax/revision/substantive_v3_20260906/numerical_existence/ANALYSIS_SPEC_A1.json"
)
A1_OWNER_AUTHORIZATION_REL = pathlib.Path(
    "yax/revision/substantive_v3_20260906/revision_inputs/"
    "GATE1_NUMERICAL_ADJUDICATION_A1.md"
)
A1_OWNER_AUTHORIZATION_SHA256 = (
    "ff4963e66940741abc8a4eda87fd9050c51cae5cedfabb3ae1ab42c21f5836a9"
)
HIGHS_CERTIFIED_OPTIONS = {
    "presolve": False,
    "primal_feasibility_tolerance": 1e-10,
    "dual_feasibility_tolerance": 1e-10,
    "ipm_optimality_tolerance": 1e-12,
}
LP_CERTIFICATION_TOLERANCE = 1e-11
SENSITIVE_ARTIFACT_PATTERNS = (
    re.compile(r"/(?:Users|home|usr3|project|projectnb)/"),
    re.compile(r"\bghp_[A-Za-z0-9_]+\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]+\b"),
    re.compile(
        r"(?i)(?:^|[^A-Za-z0-9])(?:[A-Za-z0-9]+_)*"
        r"(?:password|api[_ -]?key|access[_ -]?token|secret)"
        r"[\"']?\s*[:=]\s*[\"']?[^,;\s]+"
    ),
    re.compile(r"(?i)\b(?:authorization\s*:\s*)?(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)https?://[^/@:\s]+:[^/@\s]+@"),
)


class AuditBlocked(RuntimeError):
    """Raised before fitting when an authenticated input contract fails."""


class IndependentNewtonFailure(AuditBlocked):
    """Fail-closed standalone-Newton termination with an owned code."""

    def __init__(
        self, termination_code: str, message: str,
        evaluation_counts: dict[str, int] | None = None,
        trajectory: list[dict[str, Any]] | None = None,
        last_metrics: dict[str, Any] | None = None,
    ):
        self.termination_code = termination_code
        self.evaluation_counts = dict(evaluation_counts or {})
        self.trajectory = list(trajectory or [])
        self.last_metrics = dict(last_metrics or {})
        super().__init__(message)


class NonEchoingArgumentParser(argparse.ArgumentParser):
    """Never echo a possibly sensitive argv token in a parser error."""

    def error(self, message: str) -> None:
        raise AuditBlocked("production command-line grammar is invalid")


@dataclass
class ModelBundle:
    model_id: str
    frame: pd.DataFrame
    young: np.ndarray
    total: np.ndarray
    first_labels: np.ndarray
    second_labels: np.ndarray
    regressors: np.ndarray
    regressor_labels: list[str]
    focal_target_label: str
    focal_target_weights: np.ndarray | None = None
    reported_target_weights: dict[str, np.ndarray] | None = None

    @property
    def focal_target(self) -> int:
        if self.focal_target_weights is not None:
            raise AuditBlocked("linear-functional target must be reparameterized before coordinate access")
        return self.regressor_labels.index(self.focal_target_label)


def target_coordinate_bundle(bundle: ModelBundle) -> tuple[ModelBundle, dict[str, Any]]:
    """Make an identified linear slope functional an exact coefficient."""
    if bundle.focal_target_weights is None:
        identity = np.eye(bundle.regressors.shape[1])
        return bundle, {
            "status": "ORIGINAL_COORDINATE_TARGET",
            "target_label": bundle.focal_target_label,
            "original_regressor_labels": bundle.regressor_labels,
            "original_target_weights": [
                1.0 if label == bundle.focal_target_label else 0.0
                for label in bundle.regressor_labels
            ],
            "original_coefficient_functionals_in_current_basis": [
                {
                    "original_index": index,
                    "original_label": label,
                    "weights": identity[index].tolist(),
                }
                for index, label in enumerate(bundle.regressor_labels)
            ],
        }
    weights = np.asarray(bundle.focal_target_weights, float)
    if weights.shape != (bundle.regressors.shape[1],) or not np.isfinite(weights).all():
        raise AuditBlocked("linear-functional target weights are invalid")
    pivot = int(np.argmax(np.abs(weights)))
    if abs(weights[pivot]) <= np.finfo(float).eps:
        raise AuditBlocked("linear-functional target is identically zero")
    remaining = [index for index in range(len(weights)) if index != pivot]
    transform = np.zeros((len(weights), len(weights)), float)
    transform[pivot, 0] = 1.0 / weights[pivot]
    for new_column, original_column in enumerate(remaining, start=1):
        transform[original_column, new_column] = 1.0
        transform[pivot, new_column] = -weights[original_column] / weights[pivot]
    if not np.allclose(weights @ transform, np.r_[1.0, np.zeros(len(weights) - 1)], rtol=0, atol=1e-13):
        raise AuditBlocked("linear-functional target reparameterization identity failed")
    transformed = bundle.regressors @ transform
    labels = [
        bundle.focal_target_label,
        *[f"target_null_basis:{bundle.regressor_labels[index]}" for index in remaining],
    ]
    reported_targets = {
        label: np.asarray(target, float) @ transform
        for label, target in (bundle.reported_target_weights or {}).items()
    }
    return ModelBundle(
        model_id=bundle.model_id,
        frame=bundle.frame,
        young=bundle.young,
        total=bundle.total,
        first_labels=bundle.first_labels,
        second_labels=bundle.second_labels,
        regressors=transformed,
        regressor_labels=labels,
        focal_target_label=bundle.focal_target_label,
        reported_target_weights=reported_targets,
    ), {
        "status": "EXACT_INVERTIBLE_LINEAR_FUNCTIONAL_REPARAMETERIZATION",
        "target_label": bundle.focal_target_label,
        "original_target_weights": weights.tolist(),
        "original_regressor_labels": bundle.regressor_labels,
        "pivot_original_column": pivot,
        "pivot_original_label": bundle.regressor_labels[pivot],
        "original_coefficient_functionals_in_current_basis": [
            {
                "original_index": index,
                "original_label": label,
                "weights": transform[index].tolist(),
            }
            for index, label in enumerate(bundle.regressor_labels)
        ],
        # The matrix is a permuted triangular basis with this determinant.
        # Record it analytically rather than running a large, avoidable dense
        # determinant for the roughly 190-column dynamic design.
        "transform_determinant_absolute": float(1.0 / abs(weights[pivot])),
        "identity_max_absolute_error": float(np.max(np.abs(
            weights @ transform - np.r_[1.0, np.zeros(len(weights) - 1)]
        ))),
    }


@dataclass
class SparseDesign:
    nuisance: sparse.csr_matrix
    full: sparse.csr_matrix
    first_codes: np.ndarray
    second_codes: np.ndarray
    first_levels: list[str]
    second_levels: list[str]
    component_count: int
    component_sizes: list[dict[str, int]]
    second_references: list[str]
    nuisance_column_labels: list[str]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def scheduler_jobnumber(environ: dict[str, str]) -> str:
    job = environ.get("JOB_ID")
    alias = environ.get("SGE_JOB_ID")
    if job is None or not JOB_ID_PATTERN.fullmatch(job):
        raise AuditBlocked("a canonical numeric SCC JOB_ID is required")
    if alias is not None and alias != job:
        raise AuditBlocked("SGE_JOB_ID conflicts with JOB_ID")
    if environ.get("SGE_TASK_ID") not in {None, "", "undefined"}:
        raise AuditBlocked("Grid Engine array jobs are not authorized")
    return job


def require_job_derived_output_leaf(
    args: argparse.Namespace, run_id: str,
) -> None:
    expected = pathlib.Path(args.output_parent) / run_id
    observed = getattr(args, "output_dir", None)
    if (
        observed is None
        or pathlib.Path(observed).resolve(strict=False)
        != expected.resolve(strict=False)
    ):
        raise AuditBlocked(
            "output leaf is not exactly the scheduler-job-derived destination"
        )


def execution_runtime_authentication() -> dict[str, Any]:
    if (
        sys.flags.isolated != 1
        or sys.flags.ignore_environment != 1
        or sys.flags.no_user_site != 1
        or not bool(getattr(sys.flags, "safe_path", False))
    ):
        raise AuditBlocked("production Python must be invoked with isolated mode")
    if any(os.environ.get(name) for name in IMPORT_AFFECTING_ENVIRONMENT):
        raise AuditBlocked("import-affecting Python environment variables are forbidden")
    if os.environ.get("OMP_NUM_THREADS") != "1":
        raise AuditBlocked("OMP_NUM_THREADS=1 is required for the numerical audit")
    try:
        python_path = pathlib.Path(sys.executable).resolve(strict=True)
    except OSError as exc:
        raise AuditBlocked("Python executable cannot be resolved") from exc
    python_hash = sha256_file(python_path)
    if python_hash != EXPECTED_PYTHON_RESOLVED_SHA256:
        raise AuditBlocked("resolved Python executable differs from the pinned runtime")
    if platform.python_version() != "3.13.8":
        raise AuditBlocked("Python version differs from the pinned runtime")
    if not EXPECTED_GIT_PATH.is_file() or EXPECTED_GIT_PATH.is_symlink():
        raise AuditBlocked("pinned Git executable is absent or indirect")
    git_hash = sha256_file(EXPECTED_GIT_PATH)
    if git_hash != EXPECTED_GIT_SHA256:
        raise AuditBlocked("Git executable differs from the pinned runtime")
    completed = subprocess.run(
        [str(EXPECTED_GIT_PATH), "--version"],
        env=SANITIZED_GIT_ENVIRONMENT,
        text=True, capture_output=True, check=False,
    )
    if completed.returncode != 0 or completed.stdout.strip() != EXPECTED_GIT_VERSION:
        raise AuditBlocked("Git version differs from the pinned runtime")
    return {
        "status": "AUTHENTICATED_ISOLATED_PINNED_EXECUTABLES",
        "python_invocation": "<YAX_PYTHON_BIN>",
        "python_resolved_executable_sha256": python_hash,
        "python_version": platform.python_version(),
        "isolated_mode": True,
        "ignore_environment": True,
        "no_user_site": True,
        "safe_path": True,
        "git_invocation": "<YAX_GIT_BIN>",
        "git_resolved_executable_sha256": git_hash,
        "git_version": EXPECTED_GIT_VERSION,
        "import_affecting_environment_absent": True,
        "omp_num_threads": "1",
    }


def build_execution_command_binding(
    args: argparse.Namespace,
    raw_cli_argv: list[str],
    original_argv: list[str],
    environ: dict[str, str],
) -> dict[str, Any]:
    if len(raw_cli_argv) != 2 * len(EXPECTED_PRODUCTION_FLAGS):
        raise AuditBlocked("production command-line grammar is invalid")
    if raw_cli_argv[::2] != list(EXPECTED_PRODUCTION_FLAGS):
        raise AuditBlocked("production command-line grammar is invalid")
    if any(not value or any(ord(char) < 32 for char in value) for value in raw_cli_argv[1::2]):
        raise AuditBlocked("production command-line values are invalid")
    if len(original_argv) != len(raw_cli_argv) + 3 or original_argv[1] != "-I":
        raise AuditBlocked("production must use direct isolated-script invocation")
    try:
        invoked_python = pathlib.Path(original_argv[0]).resolve(strict=True)
        invoked_script = pathlib.Path(original_argv[2]).resolve(strict=True)
    except OSError as exc:
        raise AuditBlocked("production executable or runner cannot be resolved") from exc
    if invoked_python != pathlib.Path(sys.executable).resolve(strict=True):
        raise AuditBlocked("invoked Python differs from the running interpreter")
    if invoked_script != pathlib.Path(__file__).resolve():
        raise AuditBlocked("production runner path is not the authorized script")
    if original_argv[3:] != raw_cli_argv:
        raise AuditBlocked("raw process argv and script argv differ")
    parsed_values = (
        args.canonical_spec, args.analysis_spec, args.cells, args.cells_receipt,
        args.legacy_engine, args.output_parent,
    )
    if any(pathlib.Path(raw).resolve(strict=False) != pathlib.Path(parsed).resolve(strict=False)
           for raw, parsed in zip(raw_cli_argv[1::2], parsed_values)):
        raise AuditBlocked("parsed paths differ from the captured invocation")
    repo = pathlib.Path(__file__).resolve().parents[4]
    expected_paths = (
        repo / "yax/revision/substantive_v3_20260906/contracts/specs/canonical_baseline_reproduction_v2.json",
        repo / A1_SPEC_REL,
        pathlib.Path(args.cells).resolve(strict=False),
        pathlib.Path(args.cells_receipt).resolve(strict=False),
        repo / "dax/memo/power_calcs/young_relative_employment_power.py",
        pathlib.Path(args.output_parent).resolve(strict=False),
    )
    if any(pathlib.Path(value).resolve(strict=False) != expected.resolve(strict=False)
           for value, expected in zip(parsed_values, expected_paths)):
        raise AuditBlocked("production invocation path roles differ from the locked contract")
    cells = pathlib.Path(args.cells).resolve(strict=False)
    cells_receipt = pathlib.Path(args.cells_receipt).resolve(strict=False)
    if (
        cells.name != "aggregate_cells.csv"
        or cells_receipt.name != "EXECUTION_RECEIPT.json"
        or cells.parent != cells_receipt.parent
    ):
        raise AuditBlocked("numerical inputs are not the exact colocated cell artifacts")
    job = scheduler_jobnumber(environ)
    run_id = f"gate1_numerical_sge_{job}"
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise AuditBlocked("derived output run ID is invalid")
    require_job_derived_output_leaf(args, run_id)
    sanitized_argv = [
        "<YAX_PYTHON_BIN>", "-I",
        "yax/revision/substantive_v3_20260906/numerical_existence/"
        "run_numerical_existence_audit.py",
        "--canonical-spec",
        "<YAX_REPO_ROOT>/yax/revision/substantive_v3_20260906/contracts/specs/"
        "canonical_baseline_reproduction_v2.json",
        "--analysis-spec",
        "<YAX_REPO_ROOT>/yax/revision/substantive_v3_20260906/numerical_existence/"
        "ANALYSIS_SPEC_A1.json",
        "--cells", "<YAX_GATE1_CELLS_LEAF>/aggregate_cells.csv",
        "--cells-receipt", "<YAX_GATE1_CELLS_LEAF>/EXECUTION_RECEIPT.json",
        "--legacy-engine",
        "<YAX_REPO_ROOT>/dax/memo/power_calcs/young_relative_employment_power.py",
        "--output-parent", "<YAX_V3_RUN_ROOT>",
    ]
    core = {
        "schema_version": COMMAND_BINDING_SCHEMA,
        "status": COMMAND_BINDING_STATUS,
        "module_key": MODULE_KEY,
        "run_id": run_id,
        "scheduler_jobnumber": job,
        "sanitized_argv": sanitized_argv,
        "sanitized_argv_sha256": hashlib.sha256(
            canonical_bytes(sanitized_argv)
        ).hexdigest(),
    }
    return {
        **core,
        "binding_sha256": hashlib.sha256(canonical_bytes(core)).hexdigest(),
    }


def runtime_payload() -> dict[str, Any]:
    libc_name, libc_version = platform.libc_ver()
    return {
        "architecture": platform.machine(),
        "libc": {"name": libc_name, "version": libc_version},
        "packages": {
            "numpy": np.__version__, "pandas": pd.__version__,
            "pytest": pytest.__version__, "scipy": scipy.__version__,
        },
        "python_compiler": platform.python_compiler(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
    }


def verify_runtime_contract(analysis: dict[str, Any]) -> dict[str, Any]:
    observed = runtime_payload()
    observed_hash = hashlib.sha256(canonical_bytes(observed)).hexdigest()
    expected = analysis["software"]["runtime_contract"]
    if observed != expected["payload"] or observed_hash != expected["payload_sha256"]:
        raise AuditBlocked(
            "dedicated SCC numerical runtime differs from the byte-locked contract"
        )
    return {
        "payload": observed,
        "payload_sha256": observed_hash,
        "kernel_recorded_not_equality_locked": platform.release(),
    }


def expected_spec_id(document: dict[str, Any]) -> str:
    clean = dict(document)
    clean.pop("spec_id", None)
    return SPEC_PREFIX + hashlib.sha256(canonical_bytes(clean)).hexdigest()


def expected_audit_spec_id(document: dict[str, Any]) -> str:
    clean = dict(document)
    clean.pop("audit_spec_id", None)
    return AUDIT_SPEC_PREFIX + hashlib.sha256(canonical_bytes(clean)).hexdigest()


def expected_cell_spec_id(document: dict[str, Any]) -> str:
    clean = dict(document)
    clean.pop("cell_build_spec_id", None)
    return CELL_SPEC_PREFIX + hashlib.sha256(canonical_bytes(clean)).hexdigest()


def expected_target_spec_id(document: dict[str, Any]) -> str:
    clean = dict(document)
    clean.pop("target_audit_spec_id", None)
    return "yaxtargetspec_v1_" + hashlib.sha256(canonical_bytes(clean)).hexdigest()


def expected_pre_execution_authorization_id(document: dict[str, Any]) -> str:
    clean = dict(document)
    clean.pop("authorization_id", None)
    return PRE_EXECUTION_AUTHORIZATION_PREFIX + hashlib.sha256(
        canonical_bytes(clean)
    ).hexdigest()


def validate_pre_execution_authorization(
    repo: pathlib.Path,
    canonical: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    path = repo / PRE_EXECUTION_AUTHORIZATION_REL
    if not path.is_file() or path.is_symlink():
        raise AuditBlocked("pre-execution authorization is absent or indirect")
    document = load_json(path)
    if set(document) != {
        "schema_version", "status", "authorization_id", "issued_at_utc",
        "not_before_utc", "not_after_utc", "authorized_implementation_commit",
        "canonical_spec", "source_registry_sha256", "modules",
    }:
        raise AuditBlocked("pre-execution authorization field set is not exact")
    if (
        document.get("schema_version") != PRE_EXECUTION_AUTHORIZATION_SCHEMA
        or document.get("status") != PRE_EXECUTION_AUTHORIZATION_STATUS
        or document.get("authorization_id")
        != expected_pre_execution_authorization_id(document)
    ):
        raise AuditBlocked("pre-execution authorization identity is invalid")
    try:
        issued = datetime.fromisoformat(str(document["issued_at_utc"]).replace("Z", "+00:00"))
        not_before = datetime.fromisoformat(str(document["not_before_utc"]).replace("Z", "+00:00"))
        not_after = datetime.fromisoformat(str(document["not_after_utc"]).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise AuditBlocked("pre-execution authorization timestamps are invalid") from exc
    if any(value.tzinfo is None for value in (issued, not_before, not_after)):
        raise AuditBlocked("pre-execution authorization timestamps require offsets")
    if not (issued <= not_before <= datetime.now(timezone.utc) <= not_after):
        raise AuditBlocked("execution is outside the authorized time window")
    if document.get("canonical_spec") != {
        "id": canonical["spec_id"], "sha256": CANONICAL_SPEC_SHA256,
    }:
        raise AuditBlocked("authorization canonical binding differs")
    source_hashes = {
        row["source_id"]: row["sha256"] for row in canonical["data"]["sources"]
    }
    source_registry_sha = hashlib.sha256(
        canonical_bytes(source_hashes)
    ).hexdigest()
    if document.get("source_registry_sha256") != source_registry_sha:
        raise AuditBlocked("authorization source registry differs")
    modules = document.get("modules")
    if not isinstance(modules, dict) or set(modules) != {"cells", "target", "numerical"}:
        raise AuditBlocked("authorization module registry is incomplete")
    cell_spec = load_json(repo / CELL_SPEC_REL)
    target_spec = load_json(repo / TARGET_SPEC_REL)
    if cell_spec.get("cell_build_spec_id") != expected_cell_spec_id(cell_spec):
        raise AuditBlocked("authorization cell specification ID is invalid")
    if target_spec.get("target_audit_spec_id") != expected_target_spec_id(target_spec):
        raise AuditBlocked("authorization target specification ID is invalid")
    expected_modules = {
        "cells": {
            "typed_spec_id": cell_spec["cell_build_spec_id"],
            "typed_spec_sha256": sha256_file(repo / CELL_SPEC_REL),
            "code_sha256": sha256_file(repo / CELL_CODE_REL),
        },
        "target": {
            "typed_spec_id": target_spec["target_audit_spec_id"],
            "typed_spec_sha256": sha256_file(repo / TARGET_SPEC_REL),
            "code_sha256": sha256_file(repo / TARGET_CODE_REL),
        },
        "numerical": {
            "typed_spec_id": analysis["audit_spec_id"],
            "typed_spec_sha256": analysis["_loaded_file_sha256"],
            "code_sha256": sha256_file(pathlib.Path(__file__).resolve()),
        },
    }
    if modules != expected_modules:
        raise AuditBlocked("authorization module registry binding differs")
    expected_own = expected_modules["numerical"]
    def git_run(arguments: list[str], *, text: bool = False):
        return subprocess.run(
            [str(EXPECTED_GIT_PATH), *arguments], cwd=repo,
            env=SANITIZED_GIT_ENVIRONMENT, text=text,
            capture_output=True, check=False,
        )
    head_result = git_run(["rev-parse", "HEAD"], text=True)
    if head_result.returncode != 0:
        raise AuditBlocked("authorization Git HEAD cannot be resolved")
    head = head_result.stdout.strip()
    implementation = document.get("authorized_implementation_commit")
    if (
        not isinstance(implementation, str)
        or not re.fullmatch(r"[0-9a-f]{40}", implementation)
        or implementation == head
    ):
        raise AuditBlocked("authorization implementation commit is invalid")
    ancestor = git_run(["merge-base", "--is-ancestor", implementation, head])
    committed = git_run(["show", f"{head}:{PRE_EXECUTION_AUTHORIZATION_REL}"])
    last_commit = git_run(
        ["log", "-1", "--format=%H", "--", str(PRE_EXECUTION_AUTHORIZATION_REL)],
        text=True,
    )
    parent_commit = git_run(["rev-parse", "HEAD^"], text=True)
    changed_paths = git_run(
        ["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"],
        text=True,
    )
    if (
        ancestor.returncode != 0 or committed.returncode != 0
        or committed.stdout != path.read_bytes()
        or last_commit.returncode != 0 or last_commit.stdout.strip() != head
        or parent_commit.returncode != 0
        or parent_commit.stdout.strip() != implementation
        or changed_paths.returncode != 0
        or changed_paths.stdout.splitlines()
        != [str(PRE_EXECUTION_AUTHORIZATION_REL)]
    ):
        raise AuditBlocked(
            "authorization is not the sole file in a separate current commit"
        )
    return {
        "schema_version": PRE_EXECUTION_AUTHORIZATION_SCHEMA,
        "status": PRE_EXECUTION_AUTHORIZATION_STATUS,
        "authorization_id": document["authorization_id"],
        "authorization_file_sha256": sha256_file(path),
        "authorization_git_commit": head,
        "authorized_implementation_commit": implementation,
        "issued_at_utc": document["issued_at_utc"],
        "not_before_utc": document["not_before_utc"],
        "not_after_utc": document["not_after_utc"],
        "module_key": "numerical",
        "typed_spec_id": expected_own["typed_spec_id"],
        "typed_spec_sha256": expected_own["typed_spec_sha256"],
        "code_sha256": expected_own["code_sha256"],
        "source_registry_sha256": source_registry_sha,
    }


def load_json(path: pathlib.Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise AuditBlocked(f"JSON root must be an object: {path}")
    return value


def finite_or_none(value: Any) -> Any:
    if isinstance(value, (np.floating, float)):
        return float(value) if math.isfinite(float(value)) else None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, np.ndarray):
        return [finite_or_none(item) for item in value.tolist()]
    if isinstance(value, dict):
        return {str(key): finite_or_none(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [finite_or_none(child) for child in value]
    return value


def write_json(path: pathlib.Path, value: Any) -> None:
    path.write_text(
        json.dumps(finite_or_none(value), indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: pathlib.Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: finite_or_none(row.get(field)) for field in fields})


def month_range(start: str, end: str) -> list[str]:
    sy, sm = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    result: list[str] = []
    year, month = sy, sm
    while (year, month) <= (ey, em):
        result.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return result


def support_hash(codes: Iterable[str]) -> str:
    payload = "".join(f"{code}\n" for code in sorted(set(codes)))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scientific_target_payload(document: dict[str, Any]) -> dict[str, Any]:
    """Return only the scientific/data/target identity carried across A1."""
    inputs = document.get("input_contract", {})
    execution = inputs.get("cell_builder_execution_contract", {})
    tolerance_names = (
        "conditioning_rank_relative",
        "fitted_probability_max_abs_difference",
        "gradient_infinity_norm_per_total",
        "objective_difference_per_total",
        "standardized_score_absolute",
        "target_coefficient_absolute_difference",
    )
    return {
        "canonical_spec_id": document.get("canonical_spec_id"),
        "canonical_spec_sha256": document.get("canonical_spec_sha256"),
        "aggregate_input": {
            key: inputs.get(key) for key in (
                "aggregate_schema_version",
                "assignment_fingerprint_algorithm",
                "assignment_fingerprint_sha256",
                "balanced_grid_required",
                "expected_balanced_grid_rows",
                "cells_receipt_schema_version",
                "required_columns",
                "support_hash_algorithm",
                "weight_application_count",
            )
        },
        "protected_source_route": {
            key: execution.get(key) for key in (
                "runtime_raw_fields", "runtime_raw_source_ids",
            )
        },
        "likelihood": document.get("likelihood"),
        "boundary_and_separation": document.get("boundary_and_separation"),
        "design_parity": document.get("design_parity"),
        "dynamic_target_scope": document.get("dynamic_target_scope"),
        "models": document.get("models"),
        "normalization": document.get("normalization"),
        "profile": document.get("profile"),
        "final_tolerances": {
            key: document.get("tolerances", {}).get(key)
            for key in tolerance_names
        },
    }


def scientific_target_fingerprint(document: dict[str, Any]) -> str:
    return hashlib.sha256(
        canonical_bytes(scientific_target_payload(document))
    ).hexdigest()


def validate_a1_amendment(
    repo_root: pathlib.Path,
    analysis_path: pathlib.Path,
    analysis: dict[str, Any],
) -> dict[str, Any]:
    """Validate A1 authority, immutable parent, and unchanged science."""
    if analysis_path.resolve(strict=True) != (repo_root / A1_SPEC_REL).resolve(
        strict=True
    ):
        raise AuditBlocked("A1 execution requires the canonical A1 spec path")
    amendment = analysis.get("amendment_a1")
    if not isinstance(amendment, dict):
        raise AuditBlocked("A1 amendment binding is absent")
    authorization = amendment.get("authorization")
    if authorization != {
        "path": A1_OWNER_AUTHORIZATION_REL.as_posix(),
        "sha256": A1_OWNER_AUTHORIZATION_SHA256,
    }:
        raise AuditBlocked("A1 owner authorization binding differs")
    authorization_path = repo_root / A1_OWNER_AUTHORIZATION_REL
    if (
        not authorization_path.is_file()
        or authorization_path.is_symlink()
        or sha256_file(authorization_path) != A1_OWNER_AUTHORIZATION_SHA256
    ):
        raise AuditBlocked("A1 owner authorization file differs")

    parent_binding = amendment.get("parent_numerical_spec")
    if not isinstance(parent_binding, dict):
        raise AuditBlocked("A1 parent numerical specification binding is absent")
    parent_relative = pathlib.Path(str(parent_binding.get("path", "")))
    if parent_relative.is_absolute() or ".." in parent_relative.parts:
        raise AuditBlocked("A1 parent numerical specification path is unsafe")
    parent_path = repo_root / parent_relative
    if not parent_path.is_file() or parent_path.is_symlink():
        raise AuditBlocked("A1 parent numerical specification is absent or indirect")
    parent_sha = sha256_file(parent_path)
    parent = load_json(parent_path)
    if (
        parent_sha != parent_binding.get("sha256")
        or parent.get("audit_spec_id") != parent_binding.get("id")
        or parent.get("audit_spec_id") != expected_audit_spec_id(parent)
    ):
        raise AuditBlocked("A1 parent numerical specification is not authentic")
    parent["_loaded_file_sha256"] = parent_sha

    fingerprint = scientific_target_fingerprint(parent)
    target_binding = amendment.get("scientific_target_fingerprint")
    if (
        not isinstance(target_binding, dict)
        or target_binding.get("algorithm")
        != "SHA-256 of canonical JSON scientific_target_payload_v1"
        or target_binding.get("sha256") != fingerprint
        or scientific_target_fingerprint(analysis) != fingerprint
        or scientific_target_payload(analysis) != scientific_target_payload(parent)
    ):
        raise AuditBlocked("A1 changed the scientific/data/treatment target")

    required_files = {
        "preserved_blocked_run": (
            "numerical_receipt_path", "numerical_receipt_sha256",
        ),
        "authenticated_cell_reuse": ("receipt_path", "receipt_sha256"),
    }
    for section_name, (path_key, hash_key) in required_files.items():
        section = amendment.get(section_name)
        if not isinstance(section, dict):
            raise AuditBlocked(f"A1 {section_name} binding is absent")
        relative = pathlib.Path(str(section.get(path_key, "")))
        if relative.is_absolute() or ".." in relative.parts:
            raise AuditBlocked(f"A1 {section_name} path is unsafe")
        path = repo_root / relative
        if (
            not path.is_file() or path.is_symlink()
            or sha256_file(path) != section.get(hash_key)
        ):
            raise AuditBlocked(f"A1 {section_name} artifact differs")

    blocked = amendment["preserved_blocked_run"]
    blocked_run_relative = pathlib.Path(str(blocked.get("path", "")))
    if (
        blocked_run_relative.is_absolute()
        or ".." in blocked_run_relative.parts
        or not blocked_run_relative.parts
    ):
        raise AuditBlocked("preserved blocked numerical run path is unsafe")
    blocked_run_path = repo_root / blocked_run_relative
    blocked_receipt_path = repo_root / blocked["numerical_receipt_path"]
    expected_blocked_receipt_path = (
        blocked_run_path / "numerical" / "EXECUTION_RECEIPT.json"
    )
    if blocked_receipt_path.resolve() != expected_blocked_receipt_path.resolve():
        raise AuditBlocked("preserved blocked numerical receipt path differs")
    blocked_receipt = load_json(blocked_receipt_path)
    if (
        blocked_receipt.get("status")
        != "BLOCKED_ONE_OR_MORE_CORE_TARGETS_NOT_ESTABLISHED"
        or blocked.get("status") != blocked_receipt.get("status")
        or blocked_receipt.get("audit_spec_id") != parent["audit_spec_id"]
        or blocked_receipt.get("audit_spec_sha256") != parent_sha
        or blocked_receipt.get("git_commit") != blocked.get("producer_commit")
    ):
        raise AuditBlocked("preserved blocked numerical run binding differs")

    blocked_model_audit_path = blocked_run_path / "numerical" / "MODEL_AUDIT.json"
    blocked_model_audit_expected_sha = blocked.get("model_audit_sha256")
    blocked_output_hashes = blocked_receipt.get("output_hashes", {})
    if (
        not blocked_model_audit_path.is_file()
        or blocked_model_audit_path.is_symlink()
        or not isinstance(blocked_model_audit_expected_sha, str)
        or not re.fullmatch(r"[0-9a-f]{64}", blocked_model_audit_expected_sha)
        or sha256_file(blocked_model_audit_path)
        != blocked_model_audit_expected_sha
        or blocked_output_hashes.get("MODEL_AUDIT.json")
        != blocked_model_audit_expected_sha
    ):
        raise AuditBlocked("preserved blocked MODEL_AUDIT bytes differ")
    blocked_model_audit = load_json(blocked_model_audit_path)
    blocked_models = blocked_model_audit.get("models")
    expected_model_ids = [model.get("model_id") for model in parent["models"]]
    actual_model_ids = (
        [model.get("model_id") for model in blocked_models]
        if isinstance(blocked_models, list)
        and all(isinstance(model, dict) for model in blocked_models)
        else None
    )
    passed_model_count = (
        sum(
            model.get("finite_target_established") is True
            for model in blocked_models
        )
        if actual_model_ids is not None else None
    )
    classifications_consistent = bool(
        actual_model_ids is not None
        and all(
            (
                model.get("classification")
                == "PASS_FINITE_EXTENDED_MLE_TARGET"
            )
            == (model.get("finite_target_established") is True)
            and isinstance(model.get("classification"), str)
            and (
                model.get("classification")
                == "PASS_FINITE_EXTENDED_MLE_TARGET"
                or model.get("classification").startswith("BLOCKED_")
            )
            for model in blocked_models
        )
    )
    if (
        blocked_model_audit.get("status") != blocked_receipt.get("status")
        or blocked_model_audit.get("audit_spec_id") != parent["audit_spec_id"]
        or blocked_model_audit.get("canonical_spec_id")
        != parent.get("canonical_spec_id")
        or blocked_model_audit.get("cells_sha256")
        != amendment["authenticated_cell_reuse"].get("cells_sha256")
        or actual_model_ids != expected_model_ids
        or len(set(actual_model_ids or [])) != len(expected_model_ids)
        or blocked_receipt.get("model_count") != len(expected_model_ids)
        or blocked_receipt.get("passed_model_count") != passed_model_count
        or passed_model_count == len(expected_model_ids)
        or not classifications_consistent
    ):
        raise AuditBlocked("preserved blocked MODEL_AUDIT semantics differ")

    cells = amendment["authenticated_cell_reuse"]
    cells_receipt = load_json(repo_root / cells["receipt_path"])
    expected_cell_values = {
        "cells_sha256": cells.get("cells_sha256"),
        "git_commit": cells.get("producer_commit"),
        "git_tree": cells.get("producer_tree"),
        "cell_build_spec_id": cells.get("cell_build_spec_id"),
        "cell_build_spec_sha256": cells.get("cell_build_spec_sha256"),
        "analysis_spec_id": parent["audit_spec_id"],
        "analysis_spec_sha256": parent_sha,
    }
    if any(
        cells_receipt.get(key) != value
        for key, value in expected_cell_values.items()
    ):
        raise AuditBlocked("A1 authenticated-cell reuse binding differs")
    return parent


def validate_specs(
    canonical_path: pathlib.Path, analysis_path: pathlib.Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    canonical = load_json(canonical_path)
    if sha256_file(canonical_path) != CANONICAL_SPEC_SHA256:
        raise AuditBlocked("canonical v2 specification byte hash mismatch")
    observed_id = canonical.get("spec_id")
    if observed_id != expected_spec_id(canonical):
        raise AuditBlocked("canonical spec_id does not match canonical JSON")
    if canonical.get("estimator", {}).get("objective", "").lower().find(
        "grouped-binomial"
    ) < 0:
        raise AuditBlocked("canonical objective is not grouped-binomial")
    analysis = load_json(analysis_path)
    if analysis.get("canonical_spec_id") != observed_id:
        raise AuditBlocked("analysis spec is bound to a different canonical spec_id")
    if analysis.get("canonical_spec_sha256") != CANONICAL_SPEC_SHA256:
        raise AuditBlocked("analysis spec is bound to a different canonical byte hash")
    if analysis.get("audit_spec_id") != expected_audit_spec_id(analysis):
        raise AuditBlocked("audit_spec_id does not match canonical audit JSON")
    analysis["_loaded_file_sha256"] = sha256_file(analysis_path)
    repo_root = pathlib.Path(__file__).resolve().parents[4]
    analysis["_a1_parent_analysis"] = validate_a1_amendment(
        repo_root, analysis_path, analysis,
    )
    observed_runner_hash = sha256_file(pathlib.Path(__file__).resolve())
    if analysis.get("software", {}).get("audit_runner_sha256") != observed_runner_hash:
        raise AuditBlocked(
            "audit runner hash differs from the pre-result analysis specification"
        )
    locked_local_code = {
        HERE / "artifact_safety.py": analysis["software"]["artifact_safety_sha256"],
        HERE / "test_numerical_existence_audit.py": analysis["software"]["synthetic_test_sha256"],
        repo_root / analysis["software"]["cell_builder_path"]: analysis["software"]["cell_builder_sha256"],
    }
    for path, expected_hash in locked_local_code.items():
        if not path.is_file() or sha256_file(path) != expected_hash:
            raise AuditBlocked(f"locked numerical-audit code hash mismatch: {path.name}")
    for relative, expected_hash in analysis.get("design_parity", {}).get(
        "submitted_source_sha256", {}
    ).items():
        path = repo_root / relative
        if not path.is_file() or sha256_file(path) != expected_hash:
            raise AuditBlocked(f"submitted design source hash mismatch: {pathlib.Path(relative).name}")
    declared_list = [row.get("model_id") for row in analysis.get("models", [])]
    declared = set(declared_list)
    expected_models = {
        "pooled", "family_post", "family_month",
        "dynamics_unconditioned", "dynamics_family_month",
        "post_2020_unconditioned", "post_2020_family_month",
        "seasonal_quintile_month_unconditioned",
        "seasonal_quintile_month_family_month",
        "seasonal_occupation_month_unconditioned",
        "seasonal_occupation_month_family_month",
    }
    if declared != expected_models or len(declared_list) != len(expected_models):
        raise AuditBlocked(f"analysis model registry mismatch: {sorted(declared)}")
    expected_dynamic_scope = {
        "reference_quarter": "2022Q4",
        "post_start_month": "2023-01",
        "reported_q5_event_target_count": 38,
        "joint_pretrend_target_count": 23,
        "observed_post_month_count": 42,
        "post_functional_weighting": "equal weight per observed calendar month",
    }
    if analysis.get("dynamic_target_scope") != expected_dynamic_scope:
        raise AuditBlocked("dynamic target-scope contract mismatch")
    execution = analysis.get("input_contract", {}).get(
        "cell_builder_execution_contract", {}
    )
    if execution.get("runtime_raw_source_ids") != [
        "ipums_cps_extract_9_wide",
        "ipums_cps_extract_11_march_basic_repair",
    ]:
        raise AuditBlocked("raw source contract mismatch")
    expected_grid_rows = (
        int(canonical["occupation"]["analysis_subset"]["occupation_count"])
        * int(canonical["calendar"]["observed_window"]["observed_month_count"])
    )
    if analysis.get("input_contract", {}).get(
        "expected_balanced_grid_rows"
    ) != expected_grid_rows:
        raise AuditBlocked("balanced-grid row contract mismatch")
    return canonical, analysis


def assignment_fingerprint(frame: pd.DataFrame) -> str:
    fields = ["occ_code", "family", "beta_quintile", "webb_z"]
    if not set(fields).issubset(frame.columns):
        raise AuditBlocked("assignment fingerprint fields are absent")
    assignments = frame[fields].drop_duplicates().copy()
    assignments["occ_code"] = assignments.occ_code.astype(str).str.zfill(4)
    if assignments.occ_code.duplicated().any():
        raise AuditBlocked("more than one assignment exists for an occupation")
    lines = [
        f"{row.occ_code}\t{str(row.family)}\t{int(row.beta_quintile)}\t"
        f"{float(row.webb_z).hex()}\n"
        for row in assignments.sort_values("occ_code", kind="mergesort").itertuples(index=False)
    ]
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def assignment_authentication_checks(
    observed_fingerprint: str,
    receipt: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, bool]:
    return {
        "assignment_fingerprint_receipt": (
            receipt.get("assignment_fingerprint_sha256") == observed_fingerprint
        ),
        "assignment_fingerprint_contract": (
            observed_fingerprint ==
            analysis["input_contract"]["assignment_fingerprint_sha256"]
        ),
    }


def contains_resolved_private_path(value: Any) -> bool:
    markers = ("/project/", "/projectnb/", "/usr3/", "/Users/", "/home/")
    if isinstance(value, str):
        return any(marker in value for marker in markers)
    if isinstance(value, dict):
        return any(contains_resolved_private_path(child) for child in value.values())
    if isinstance(value, list):
        return any(contains_resolved_private_path(child) for child in value)
    return False


def scan_artifacts_for_sensitive_text(
    root: pathlib.Path,
    expected_names: set[str] | None = None,
) -> dict[str, Any]:
    scanned: list[str] = []
    observed_names = {path.name for path in root.iterdir()}
    if expected_names is not None and observed_names != expected_names:
        raise AuditBlocked("staged artifact name set differs from the declared outputs")
    for path in sorted(root.iterdir(), key=lambda value: value.name):
        if path.is_symlink() or not path.is_file():
            raise AuditBlocked("published artifact set contains a non-file entry")
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as error:
            raise AuditBlocked(f"artifact is not UTF-8 text and cannot be sanitized: {path.name}") from error
        if any(pattern.search(text) for pattern in SENSITIVE_ARTIFACT_PATTERNS):
            raise AuditBlocked(f"sensitive text detected in unpublished artifact: {path.name}")
        scanned.append(path.name)
    return {
        "status": "PASS_ALL_ARTIFACTS_SANITIZED",
        "files_scanned": scanned,
        "file_count": len(scanned),
    }


def cell_receipt_authentication_checks(
    receipt: dict[str, Any],
    cells_path: pathlib.Path,
    canonical: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, bool]:
    canonical_sources = {
        row["source_id"]: row["sha256"] for row in canonical["data"]["sources"]
    }
    expected_lookup_hashes = {
        key: canonical_sources[key] for key in (
            "cps_occupation_exposure_lookup",
            "computerization_measures_census2018",
            "rule_b_values_census2018",
            "census_occ2010_to_2018_bridge",
            "first_post_outcome_access_receipt",
        )
    }
    expected_authenticated_sources = {
        key: value for key, value in canonical_sources.items()
        if key != "historical_preperiod_cells"
    }
    execution = analysis.get("input_contract", {}).get(
        "cell_builder_execution_contract", {}
    )
    runtime = receipt.get("runtime_authentication", {})
    if not isinstance(runtime, dict):
        runtime = {}
    security = receipt.get("freshness_and_security", {})
    if not isinstance(security, dict):
        security = {}
    raw_contract = receipt.get("raw_column_contract", {})
    if not isinstance(raw_contract, dict):
        raw_contract = {}
    committed = receipt.get("git_committed_artifact_hashes", {})
    committed_paths = execution.get("git_committed_paths", [])
    committed_keys_match = (
        isinstance(committed, dict)
        and isinstance(committed_paths, list)
        and set(committed) == set(committed_paths)
    )
    builder_path = analysis.get("software", {}).get("cell_builder_path")
    analysis_path = execution.get("analysis_spec_path")
    cell_spec_path = execution.get("cell_build_spec_path")
    environment_path = execution.get("environment_lock_path")
    authorization = receipt.get("authorization", {})
    if not isinstance(authorization, dict):
        authorization = {}
    authorization_checks = authorization.get("checks", {})
    if not isinstance(authorization_checks, dict):
        authorization_checks = {}
    reference_artifacts = receipt.get("reference_artifacts", {})
    if not isinstance(reference_artifacts, dict):
        reference_artifacts = {}
    return {
        "schema_version": receipt.get("schema_version") == RECEIPT_SCHEMA,
        "status": receipt.get("status") == "PASS_FRESH_AGGREGATE_REBUILD",
        "aggregate_schema_version": receipt.get("aggregate_schema_version") == CELL_SCHEMA,
        "canonical_spec_id": receipt.get("canonical_spec_id") == canonical["spec_id"],
        "canonical_spec_sha256": receipt.get("canonical_spec_sha256") == CANONICAL_SPEC_SHA256,
        "analysis_spec_id": receipt.get("analysis_spec_id") == analysis["audit_spec_id"],
        "analysis_spec_sha256": receipt.get("analysis_spec_sha256") == analysis.get("_loaded_file_sha256"),
        "cells_sha256": receipt.get("cells_sha256") == sha256_file(cells_path),
        "builder_code_sha256": receipt.get("builder_code_sha256") == analysis["software"]["cell_builder_sha256"],
        "builder_transitive_code_sha256": receipt.get("builder_transitive_code_sha256") == analysis["software"]["cell_builder_transitive_sha256"],
        "source_hashes": receipt.get("source_hashes") == canonical_sources,
        "authenticated_source_hashes": (
            receipt.get("authenticated_source_hashes")
            == expected_authenticated_sources
        ),
        "unread_historical_cell_source": (
            receipt.get("unread_canonical_source_ids")
            == ["historical_preperiod_cells"]
        ),
        "lookup_and_bridge_hashes": receipt.get("lookup_and_bridge_hashes") == expected_lookup_hashes,
        "fixed_membership_sha256": receipt.get("fixed_membership_sha256") == canonical["exposure"]["fixed_membership"]["sha256"],
        "reference_membership_sha256": (
            reference_artifacts.get("fixed_membership_sha256")
            == canonical["exposure"]["fixed_membership"]["sha256"]
        ),
        "authorization_chain": bool(
            authorization.get("status") == "PASS_AUTHORIZATION_CHAIN"
            and set(authorization_checks)
            == {"status", "frozen_tag", "microdata_sha256"}
            and all(value is True for value in authorization_checks.values())
            and authorization.get("repair_source_bound_by_canonical_v2") is True
        ),
        "weight_application_count": receipt.get("weight_application_count") == 1,
        "balanced_grid_complete": receipt.get("balanced_grid_complete") is True,
        "contains_resolved_private_paths_flag": receipt.get("contains_resolved_private_paths") is False,
        "receipt_text_has_no_resolved_private_path": not contains_resolved_private_path(receipt),
        "command_template": receipt.get("command_template") == execution.get("command_template"),
        "runtime_environment_lock_path": (
            receipt.get("runtime_environment_lock_path") == environment_path
            and runtime.get("environment_lock_path") == environment_path
        ),
        "runtime_environment_lock_sha256": (
            receipt.get("runtime_environment_lock_sha256")
            == execution.get("environment_lock_sha256")
            and runtime.get("environment_lock_sha256")
            == execution.get("environment_lock_sha256")
        ),
        "runtime_contract_sha256": (
            receipt.get("runtime_contract_sha256")
            == execution.get("runtime_contract_sha256")
            and runtime.get("runtime_contract_sha256")
            == execution.get("runtime_contract_sha256")
        ),
        "runtime_status": runtime.get("status") == "AUTHENTICATED_DECLARED_RUNTIME",
        "runtime_payload": runtime.get("runtime_payload") == execution.get("runtime_payload"),
        "runtime_payload_sha256": (
            receipt.get("runtime_payload_sha256")
            == execution.get("runtime_payload_sha256")
            and runtime.get("runtime_payload_sha256")
            == execution.get("runtime_payload_sha256")
        ),
        "runtime_command_template": runtime.get("command_template") == execution.get("command_template"),
        "runtime_code_hashes": receipt.get("runtime_code_hashes") == {
            builder_path: analysis.get("software", {}).get("cell_builder_sha256")
        },
        "historical_reference_code_hashes": (
            receipt.get("historical_reference_code_hashes")
            == execution.get("historical_reference_code_hashes")
        ),
        "git_status": receipt.get("git_status") == "PASS_COMMITTED_CLEAN_WORKTREE",
        "git_commit_shape": bool(
            re.fullmatch(r"[0-9a-f]{40}", str(receipt.get("git_commit", "")))
        ),
        "git_tree_shape": bool(
            re.fullmatch(r"[0-9a-f]{40}", str(receipt.get("git_tree", "")))
        ),
        "git_required_ancestor_commit": (
            receipt.get("git_required_ancestor_commit")
            == execution.get("git_required_ancestor_commit")
        ),
        "git_worktree_clean": receipt.get("git_worktree_clean") is True,
        "git_porcelain_empty": receipt.get("git_porcelain_sha256") == hashlib.sha256(b"").hexdigest(),
        "git_committed_path_set": committed_keys_match,
        "git_committed_builder": (
            committed_keys_match
            and committed.get(builder_path) == analysis.get("software", {}).get("cell_builder_sha256")
        ),
        "git_committed_analysis_spec": (
            committed_keys_match
            and committed.get(analysis_path) == analysis.get("_loaded_file_sha256")
        ),
        "git_committed_cell_spec": (
            committed_keys_match
            and committed.get(cell_spec_path) == receipt.get("cell_build_spec_sha256")
        ),
        "git_committed_environment_lock": (
            committed_keys_match
            and committed.get(environment_path) == execution.get("environment_lock_sha256")
        ),
        "canonical_six_field_router": (
            raw_contract.get("runtime_fields")
            == execution.get("runtime_raw_fields")
            and raw_contract.get("required_columns_present") is True
            and isinstance(raw_contract.get("source_column_counts"), dict)
            and set(raw_contract["source_column_counts"])
            == set(execution.get("runtime_raw_source_ids", []))
            and all(
                isinstance(value, int) and not isinstance(value, bool) and value >= 6
                for value in raw_contract["source_column_counts"].values()
            )
            and raw_contract.get("rejected_inherited_helper_fields")
            == ["OCC2010", "IND1990"]
            and raw_contract.get("canonical_v2_variable_universe_parity") is True
        ),
        "historical_reference_not_imported": (
            security.get("historical_reference_code_imported_at_runtime") is False
        ),
        "only_six_canonical_raw_fields_read": (
            security.get("only_six_canonical_raw_fields_read") is True
        ),
        "protected_outputs_not_persisted": bool(
            security.get("row_level_microdata_written") is False
            and security.get("historical_preperiod_cells_read") is False
            and security.get("private_paths_persisted") is False
            and security.get("credentials_persisted") is False
        ),
    }


def current_git_receipt_checks(
    repo_root: pathlib.Path,
    receipt: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, bool]:
    """Bind a cell receipt to the exact committed clean checkout consuming it."""
    try:
        head = subprocess.check_output(
            [str(EXPECTED_GIT_PATH), "rev-parse", "HEAD"], cwd=repo_root,
            env=SANITIZED_GIT_ENVIRONMENT, text=True,
        ).strip()
        tree = subprocess.check_output(
            [str(EXPECTED_GIT_PATH), "rev-parse", "HEAD^{tree}"], cwd=repo_root,
            env=SANITIZED_GIT_ENVIRONMENT, text=True,
        ).strip()
        status = subprocess.check_output(
            [str(EXPECTED_GIT_PATH), "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=repo_root,
            env=SANITIZED_GIT_ENVIRONMENT,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return {"current_git_commands": False}
    execution = analysis["input_contract"]["cell_builder_execution_contract"]
    ancestor = subprocess.run(
        [
            str(EXPECTED_GIT_PATH), "merge-base", "--is-ancestor",
            execution["git_required_ancestor_commit"], head,
        ],
        cwd=repo_root,
        env=SANITIZED_GIT_ENVIRONMENT,
        capture_output=True,
        check=False,
    )
    committed = receipt.get("git_committed_artifact_hashes", {})
    artifact_match = True
    for relative in execution["git_committed_paths"]:
        path = repo_root / relative
        try:
            blob = subprocess.check_output(
                [str(EXPECTED_GIT_PATH), "show", f"{head}:{relative}"],
                cwd=repo_root, env=SANITIZED_GIT_ENVIRONMENT,
            )
        except (OSError, subprocess.CalledProcessError):
            artifact_match = False
            continue
        digest = hashlib.sha256(blob).hexdigest()
        if (
            not path.is_file()
            or sha256_file(path) != digest
            or committed.get(relative) != digest
        ):
            artifact_match = False
    return {
        "current_git_commands": True,
        "current_git_head_matches_receipt": head == receipt.get("git_commit"),
        "current_git_tree_matches_receipt": tree == receipt.get("git_tree"),
        "current_git_required_ancestor": ancestor.returncode == 0,
        "current_git_worktree_clean": status == "",
        "current_git_committed_artifacts": artifact_match,
    }


def a1_parent_git_receipt_checks(
    repo_root: pathlib.Path,
    receipt: dict[str, Any],
    parent_analysis: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, bool]:
    """Authenticate reused cells at their historical producer commit.

    A1 changes only the numerical consumer, so equality with the current HEAD
    would incorrectly force a protected-data rebuild.  This instead verifies
    the producer commit/tree and every producer input blob, requires that
    commit to be an ancestor of the authorized A1 checkout, and verifies that
    the unchanged producer files still have those bytes at current HEAD.
    """
    reuse = analysis.get("amendment_a1", {}).get(
        "authenticated_cell_reuse", {}
    )
    producer = str(reuse.get("producer_commit", ""))
    producer_tree = str(reuse.get("producer_tree", ""))
    execution = parent_analysis["input_contract"][
        "cell_builder_execution_contract"
    ]
    committed = receipt.get("git_committed_artifact_hashes", {})
    checks: dict[str, bool] = {
        "a1_producer_commit_binding": producer == receipt.get("git_commit"),
        "a1_producer_tree_binding": producer_tree == receipt.get("git_tree"),
    }
    try:
        head = subprocess.check_output(
            [str(EXPECTED_GIT_PATH), "rev-parse", "HEAD"], cwd=repo_root,
            env=SANITIZED_GIT_ENVIRONMENT, text=True,
        ).strip()
        observed_tree = subprocess.check_output(
            [str(EXPECTED_GIT_PATH), "rev-parse", f"{producer}^{{tree}}"],
            cwd=repo_root, env=SANITIZED_GIT_ENVIRONMENT, text=True,
        ).strip()
        status = subprocess.check_output(
            [
                str(EXPECTED_GIT_PATH), "status", "--porcelain=v1",
                "--untracked-files=all",
            ],
            cwd=repo_root, env=SANITIZED_GIT_ENVIRONMENT, text=True,
        ).strip()
        ancestor = subprocess.run(
            [
                str(EXPECTED_GIT_PATH), "merge-base", "--is-ancestor",
                producer, head,
            ],
            cwd=repo_root, env=SANITIZED_GIT_ENVIRONMENT,
            capture_output=True, check=False,
        )
    except (OSError, subprocess.CalledProcessError):
        return {**checks, "a1_historical_git_commands": False}
    checks.update({
        "a1_historical_git_commands": True,
        "a1_producer_commit_is_current_ancestor": ancestor.returncode == 0,
        "a1_producer_tree_object": observed_tree == producer_tree,
        "a1_current_worktree_clean": status == "",
    })
    exact_blobs = True
    expected_paths = execution.get("git_committed_paths", [])
    if not isinstance(committed, dict) or set(committed) != set(expected_paths):
        exact_blobs = False
    for relative in expected_paths:
        try:
            producer_blob = subprocess.check_output(
                [str(EXPECTED_GIT_PATH), "show", f"{producer}:{relative}"],
                cwd=repo_root, env=SANITIZED_GIT_ENVIRONMENT,
            )
            current_blob = subprocess.check_output(
                [str(EXPECTED_GIT_PATH), "show", f"HEAD:{relative}"],
                cwd=repo_root, env=SANITIZED_GIT_ENVIRONMENT,
            )
            local = (repo_root / relative).read_bytes()
        except (OSError, subprocess.CalledProcessError):
            exact_blobs = False
            continue
        digest = hashlib.sha256(producer_blob).hexdigest()
        if (
            current_blob != producer_blob
            or local != producer_blob
            or committed.get(relative) != digest
        ):
            exact_blobs = False
    checks["a1_historical_producer_blobs_unchanged"] = exact_blobs
    return checks


def current_cell_spec_binding_checks(
    repo_root: pathlib.Path,
    receipt: dict[str, Any],
    canonical: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, bool]:
    """Authenticate the committed producer spec without creating a hash cycle."""
    execution = analysis["input_contract"]["cell_builder_execution_contract"]
    path = repo_root / execution["cell_build_spec_path"]
    try:
        cell_spec = load_json(path)
        observed_hash = sha256_file(path)
    except (OSError, AuditBlocked, json.JSONDecodeError):
        return {"current_cell_spec_readable": False}
    consumer = cell_spec.get("consumer_contract", {})
    if not isinstance(consumer, dict):
        consumer = {}
    return {
        "current_cell_spec_readable": True,
        "current_cell_spec_schema": cell_spec.get("schema_version") == CELL_SPEC_SCHEMA,
        "current_cell_spec_self_id": (
            cell_spec.get("cell_build_spec_id") == expected_cell_spec_id(cell_spec)
        ),
        "receipt_cell_spec_id": (
            receipt.get("cell_build_spec_id") == cell_spec.get("cell_build_spec_id")
        ),
        "receipt_cell_spec_sha256": (
            receipt.get("cell_build_spec_sha256") == observed_hash
        ),
        "current_cell_spec_canonical_id": (
            cell_spec.get("canonical_spec_id") == canonical.get("spec_id")
        ),
        "current_cell_spec_canonical_sha256": (
            cell_spec.get("canonical_spec_sha256") == CANONICAL_SPEC_SHA256
        ),
        "current_cell_spec_analysis_id": (
            consumer.get("analysis_spec_id") == analysis.get("audit_spec_id")
        ),
        "current_cell_spec_analysis_sha256": (
            consumer.get("analysis_spec_sha256") == analysis.get("_loaded_file_sha256")
        ),
        "current_cell_spec_aggregate_schema": (
            cell_spec.get("aggregate_schema_version") == CELL_SCHEMA
        ),
    }


def producer_accounting_checks(
    receipt: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, bool]:
    """Validate physical-record, routing-mass, and weight-once assertions."""
    execution = analysis["input_contract"]["cell_builder_execution_contract"]
    expected_sources = execution.get("runtime_raw_source_ids", [])
    raw = receipt.get("six_field_cell_build_checks", {})
    route = receipt.get("route_checks", {})
    weights = receipt.get("weight_once_checks", {})
    if not isinstance(raw, dict):
        raw = {}
    if not isinstance(route, dict):
        route = {}
    if not isinstance(weights, dict):
        weights = {}

    def nonnegative_integer(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0

    def exact_nonnegative_integer_map(value: Any) -> bool:
        return bool(
            isinstance(value, dict)
            and set(value) == set(expected_sources)
            and all(nonnegative_integer(item) for item in value.values())
        )

    def finite_float(value: Any) -> float | None:
        try:
            converted = float(value)
        except (TypeError, ValueError):
            return None
        return converted if math.isfinite(converted) else None

    def close(left: float, right: float) -> bool:
        return math.isclose(left, right, rel_tol=1e-12, abs_tol=1e-8)

    def reconciliation_row_valid(value: Any) -> bool:
        if not isinstance(value, dict):
            return False
        names = (
            "raw_early_valid_stock", "raw_early_matched_stock",
            "expected_early_routed_stock", "actual_early_routed_stock",
            "raw_current_valid_stock", "actual_current_direct_stock",
            "early_absolute_gap", "early_relative_gap",
            "current_absolute_gap", "current_relative_gap",
            "unmatched_early_stock",
        )
        numbers = {name: finite_float(value.get(name)) for name in names}
        if any(item is None for item in numbers.values()):
            return False
        early_gap = numbers["actual_early_routed_stock"] - numbers["expected_early_routed_stock"]
        current_gap = numbers["actual_current_direct_stock"] - numbers["raw_current_valid_stock"]
        unmatched = numbers["raw_early_valid_stock"] - numbers["raw_early_matched_stock"]
        early_relative = early_gap / max(abs(numbers["expected_early_routed_stock"]), 1.0)
        current_relative = current_gap / max(abs(numbers["raw_current_valid_stock"]), 1.0)
        return bool(
            close(numbers["early_absolute_gap"], early_gap)
            and close(numbers["current_absolute_gap"], current_gap)
            and close(numbers["unmatched_early_stock"], unmatched)
            and close(numbers["early_relative_gap"], early_relative)
            and close(numbers["current_relative_gap"], current_relative)
            and abs(early_relative) < 1e-10
            and abs(current_relative) < 1e-10
            and value.get("route_conservation_pass") is True
        )

    physical_by_source = raw.get("physical_rows_read_by_source", {})
    eligible_by_source = raw.get(
        "eligible_employed_age_22_65_records_by_source", {}
    )
    physical_total = raw.get("physical_rows_read_total")
    eligible_total = raw.get("eligible_employed_age_22_65_records_total")
    total_identities = route.get("total_record_identities", {})
    source_identities = route.get("record_identities_by_source", {})
    source_reconciliation = route.get("source_stock_reconciliation", {})

    partition_names = (
        "invalid_raw_occ_records", "valid_raw_occ_records",
        "early_valid_source_records", "current_valid_source_records",
        "early_matched_source_records", "early_unmatched_source_records",
        "early_expanded_route_descendants",
        "early_fractional_route_contributions",
        "early_unit_route_contributions",
        "early_zero_mass_route_contributions",
        "current_direct_route_contributions", "routed_contribution_rows",
    )
    partition_maps_valid = all(
        nonnegative_integer(raw.get(name))
        and exact_nonnegative_integer_map(raw.get(f"{name}_by_source"))
        and raw.get(name) == sum(raw[f"{name}_by_source"].values())
        for name in partition_names
    )

    recomputed_source_identities: dict[str, dict[str, bool]] = {}
    if partition_maps_valid and exact_nonnegative_integer_map(eligible_by_source):
        for source in expected_sources:
            value = lambda name: raw[f"{name}_by_source"][source]
            recomputed_source_identities[source] = {
                "eligible_equals_invalid_plus_valid": (
                    eligible_by_source[source]
                    == value("invalid_raw_occ_records") + value("valid_raw_occ_records")
                ),
                "valid_equals_early_plus_current": (
                    value("valid_raw_occ_records")
                    == value("early_valid_source_records")
                    + value("current_valid_source_records")
                ),
                "early_equals_matched_plus_unmatched": (
                    value("early_valid_source_records")
                    == value("early_matched_source_records")
                    + value("early_unmatched_source_records")
                ),
                "expanded_descendants_cover_each_matched_record": (
                    value("early_expanded_route_descendants")
                    >= value("early_matched_source_records")
                ),
                "early_descendants_partition_by_route_weight": (
                    value("early_expanded_route_descendants")
                    == value("early_fractional_route_contributions")
                    + value("early_unit_route_contributions")
                    + value("early_zero_mass_route_contributions")
                ),
                "direct_contributions_equal_current_valid_records": (
                    value("current_direct_route_contributions")
                    == value("current_valid_source_records")
                ),
                "routed_contributions_equal_descendants_plus_direct": (
                    value("routed_contribution_rows")
                    == value("early_expanded_route_descendants")
                    + value("current_direct_route_contributions")
                ),
            }
    recomputed_total_identities: dict[str, bool] = {}
    if partition_maps_valid and nonnegative_integer(eligible_total):
        recomputed_total_identities = {
            "physical_total_equals_source_sum": bool(
                nonnegative_integer(physical_total)
                and exact_nonnegative_integer_map(physical_by_source)
                and physical_total == sum(physical_by_source.values())
            ),
            "eligible_total_equals_source_sum": bool(
                exact_nonnegative_integer_map(eligible_by_source)
                and eligible_total == sum(eligible_by_source.values())
            ),
            "eligible_equals_invalid_plus_valid": (
                eligible_total == raw["invalid_raw_occ_records"]
                + raw["valid_raw_occ_records"]
            ),
            "valid_equals_early_plus_current": (
                raw["valid_raw_occ_records"]
                == raw["early_valid_source_records"]
                + raw["current_valid_source_records"]
            ),
            "early_equals_matched_plus_unmatched": (
                raw["early_valid_source_records"]
                == raw["early_matched_source_records"]
                + raw["early_unmatched_source_records"]
            ),
            "early_descendants_partition_by_route_weight": (
                raw["early_expanded_route_descendants"]
                == raw["early_fractional_route_contributions"]
                + raw["early_unit_route_contributions"]
                + raw["early_zero_mass_route_contributions"]
            ),
            "direct_contributions_equal_current_valid_records": (
                raw["current_direct_route_contributions"]
                == raw["current_valid_source_records"]
            ),
            "routed_contributions_equal_descendants_plus_direct": (
                raw["routed_contribution_rows"]
                == raw["early_expanded_route_descendants"]
                + raw["current_direct_route_contributions"]
            ),
        }

    identities_valid = bool(
        recomputed_total_identities
        and all(recomputed_total_identities.values())
        and total_identities == recomputed_total_identities
        and recomputed_source_identities
        and all(
            all(value.values()) for value in recomputed_source_identities.values()
        )
        and source_identities == recomputed_source_identities
    )
    reconciliation_valid = bool(
        isinstance(source_reconciliation, dict)
        and set(source_reconciliation) == set(expected_sources)
        and all(reconciliation_row_valid(value) for value in source_reconciliation.values())
    )
    stock_fields = (
        "raw_early_valid_stock", "raw_early_matched_stock",
        "expected_early_routed_stock", "actual_early_routed_stock",
        "raw_current_valid_stock", "actual_current_direct_stock",
    )
    route_stock_sums_valid = bool(
        reconciliation_valid
        and all(
            finite_float(route.get(name)) is not None
            and close(
                finite_float(route.get(name)),
                sum(finite_float(value.get(name)) for value in source_reconciliation.values()),
            )
            for name in stock_fields
        )
    )
    bridge_min = finite_float(route.get("bridge_mass_min"))
    bridge_max = finite_float(route.get("bridge_mass_max"))
    return {
        "raw_source_ids": raw.get("source_ids") == expected_sources,
        "runtime_raw_fields": raw.get("runtime_raw_fields") == execution.get("runtime_raw_fields"),
        "physical_rows_by_source": exact_nonnegative_integer_map(physical_by_source),
        "physical_rows_total": bool(
            nonnegative_integer(physical_total)
            and physical_total > 0
            and exact_nonnegative_integer_map(physical_by_source)
            and physical_total == sum(physical_by_source.values())
        ),
        "eligible_records_by_source": exact_nonnegative_integer_map(eligible_by_source),
        "eligible_records_total": bool(
            nonnegative_integer(eligible_total)
            and eligible_total > 0
            and exact_nonnegative_integer_map(eligible_by_source)
            and eligible_total == sum(eligible_by_source.values())
        ),
        "raw_record_partition_counters": partition_maps_valid,
        "routed_rows_compatibility": bool(
            nonnegative_integer(raw.get("routed_rows"))
            and raw.get("routed_rows") == raw.get("routed_contribution_rows")
        ),
        "repair_months": raw.get("repair_observed_months") == [
            "2017-03", "2018-03", "2019-03", "2020-03", "2021-03",
        ],
        "march_replacement_positive": bool(
            nonnegative_integer(raw.get("wide_march_rows_explicitly_replaced"))
            and raw.get("wide_march_rows_explicitly_replaced", 0) > 0
            and nonnegative_integer(raw.get("repair_eligible_employed_age_22_65_records"))
            and raw.get("repair_eligible_employed_age_22_65_records", 0) > 0
            and exact_nonnegative_integer_map(eligible_by_source)
            and raw.get("repair_eligible_employed_age_22_65_records")
            == eligible_by_source.get("ipums_cps_extract_11_march_basic_repair")
        ),
        "record_count_identities": identities_valid,
        "route_source_reconciliation": reconciliation_valid,
        "route_total_reconciliation": bool(
            reconciliation_row_valid(route) and route_stock_sums_valid
        ),
        "route_bridge_mass": bool(
            bridge_min is not None and bridge_max is not None
            and abs(bridge_min - 1.0) < 1e-10
            and abs(bridge_max - 1.0) < 1e-10
        ),
        "weight_once_status": weights.get("status") == "PASS_WEIGHT_ONCE",
        "weight_once_count": weights.get("weight_application_count") == 1,
        "weight_once_semantics": bool(
            weights.get("route_weight_is_allocation_not_second_survey_weight") is True
            and weights.get("output_applies_no_additional_weight") is True
            and weights.get("independent_aggregation_max_absolute_gap") == 0.0
        ),
        "weight_once_output_rows": (
            weights.get("rows")
            == int(analysis["input_contract"]["expected_balanced_grid_rows"])
        ),
    }


def authenticate_cells(
    cells_path: pathlib.Path,
    receipt_path: pathlib.Path,
    canonical: dict[str, Any],
    analysis: dict[str, Any],
) -> pd.DataFrame:
    amendment = analysis.get("amendment_a1")
    if isinstance(amendment, dict):
        reuse = amendment.get("authenticated_cell_reuse", {})
        expected_receipt_sha = reuse.get("receipt_sha256")
        if not isinstance(expected_receipt_sha, str) or not re.fullmatch(
            r"[0-9a-f]{64}", expected_receipt_sha,
        ):
            raise AuditBlocked(
                "validated A1 cell-receipt byte-hash binding is absent"
            )
        if (
            not receipt_path.is_file()
            or sha256_file(receipt_path) != expected_receipt_sha
        ):
            raise AuditBlocked(
                "caller-supplied A1 cell receipt bytes differ from the exact "
                "authenticated-cell reuse artifact"
            )
        # Exact byte identity is intentionally established before JSON parsing
        # or semantic checks.  Equivalent reserialization is not substitutable.
    receipt = load_json(receipt_path)
    parent_analysis = analysis.get("_a1_parent_analysis")
    if not isinstance(parent_analysis, dict):
        raise AuditBlocked("validated A1 parent analysis is absent")
    checks = cell_receipt_authentication_checks(
        receipt, cells_path, canonical, parent_analysis,
    )
    failed = sorted(key for key, passed in checks.items() if not passed)
    if failed:
        raise AuditBlocked("aggregate-cell authentication failed: " + ", ".join(failed))
    repo_root = pathlib.Path(__file__).resolve().parents[4]
    cell_spec_checks = current_cell_spec_binding_checks(
        repo_root, receipt, canonical, parent_analysis,
    )
    failed_cell_spec = sorted(
        key for key, passed in cell_spec_checks.items() if not passed
    )
    if failed_cell_spec:
        raise AuditBlocked(
            "aggregate-cell producer-spec authentication failed: "
            + ", ".join(failed_cell_spec)
        )
    accounting_checks = producer_accounting_checks(receipt, parent_analysis)
    failed_accounting = sorted(
        key for key, passed in accounting_checks.items() if not passed
    )
    if failed_accounting:
        raise AuditBlocked(
            "aggregate-cell producer accounting failed: "
            + ", ".join(failed_accounting)
        )
    git_checks = a1_parent_git_receipt_checks(
        repo_root, receipt, parent_analysis, analysis,
    )
    failed_git = sorted(key for key, passed in git_checks.items() if not passed)
    if failed_git:
        raise AuditBlocked(
            "aggregate-cell Git authentication failed: " + ", ".join(failed_git)
        )

    required = analysis["input_contract"]["required_columns"]
    frame = pd.read_csv(
        cells_path, dtype={"occ_code": str, "month": str, "family": str},
        float_precision="round_trip",
    )
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise AuditBlocked(f"aggregate cells lack columns: {missing}")
    if list(frame.columns) != required:
        raise AuditBlocked("aggregate cell columns or order differ from the exact schema")
    frame = frame[required].copy()
    if frame.empty:
        raise AuditBlocked("aggregate cell file is empty")
    if frame["occ_code"].isna().any() or frame["occ_code"].str.fullmatch(r"\d{4}").ne(True).any():
        raise AuditBlocked("occ_code must be a four-digit canonical code")
    if frame[["occ_code", "month"]].duplicated().any():
        raise AuditBlocked("aggregate cells are not unique by occupation and month")
    if frame["month"].map(lambda value: bool(MONTH.fullmatch(value))).eq(False).any():
        raise AuditBlocked("aggregate cells contain invalid YYYY-MM values")
    for field in ("young", "older", "webb_z"):
        frame[field] = pd.to_numeric(frame[field], errors="raise")
    frame["beta_quintile"] = pd.to_numeric(frame["beta_quintile"], errors="raise")
    if not np.isfinite(frame[["young", "older", "webb_z"]].to_numpy(float)).all():
        raise AuditBlocked("aggregate cells contain nonfinite numeric values")
    if (frame[["young", "older"]] < 0).any().any():
        raise AuditBlocked("aggregate employment stocks must be nonnegative")
    weight_receipt = receipt.get("weight_once_checks", {})
    if not isinstance(weight_receipt, dict):
        raise AuditBlocked("weight-once accounting receipt is absent")
    try:
        receipt_young_stock = float(weight_receipt["young_stock"])
        receipt_older_stock = float(weight_receipt["older_stock"])
    except (KeyError, TypeError, ValueError) as error:
        raise AuditBlocked("weight-once stock totals are absent or invalid") from error
    stock_checks = {
        "rows": weight_receipt.get("rows") == len(frame),
        "young_stock": np.isclose(
            float(frame.young.sum()), receipt_young_stock,
            rtol=1e-12, atol=1e-6,
        ),
        "older_stock": np.isclose(
            float(frame.older.sum()), receipt_older_stock,
            rtol=1e-12, atol=1e-6,
        ),
    }
    if not all(stock_checks.values()):
        raise AuditBlocked(
            "aggregate cells differ from weight-once stock accounting: "
            + ", ".join(sorted(key for key, value in stock_checks.items() if not value))
        )
    if not frame["beta_quintile"].isin([1, 2, 3, 4, 5]).all():
        raise AuditBlocked("beta_quintile must be in 1..5")
    frame["beta_quintile"] = frame["beta_quintile"].astype(int)
    if frame["family"].isna().any() or frame["family"].str.len().eq(0).any():
        raise AuditBlocked("family must be nonempty")

    for field in ("family", "beta_quintile", "webb_z"):
        if frame.groupby("occ_code", observed=True)[field].nunique(dropna=False).gt(1).any():
            raise AuditBlocked(f"{field} changes within occupation")
    observed_assignment_fingerprint = assignment_fingerprint(frame)
    checks_after_data = assignment_authentication_checks(
        observed_assignment_fingerprint, receipt, analysis,
    )
    failed_after_data = sorted(key for key, passed in checks_after_data.items() if not passed)
    if failed_after_data:
        raise AuditBlocked("aggregate assignment authentication failed: " + ", ".join(failed_after_data))

    observed_months = sorted(frame["month"].unique())
    window = canonical["calendar"]["observed_window"]
    expected_months = month_range(window["range"][0], window["range"][1])
    expected_months = [
        month for month in expected_months
        if month not in set(canonical["calendar"]["missing_handling"]["missing_months"])
    ]
    if observed_months != expected_months:
        raise AuditBlocked("aggregate month grid differs from canonical observed calendar")
    occupations = sorted(frame["occ_code"].unique())
    expected_occ = int(canonical["occupation"]["analysis_subset"]["occupation_count"])
    if len(occupations) != expected_occ:
        raise AuditBlocked(f"aggregate support has {len(occupations)} rather than {expected_occ} occupations")
    expected_support_hash = canonical["occupation"]["universe"]["content_support_sha256"]
    if support_hash(occupations) != expected_support_hash:
        raise AuditBlocked("aggregate occupation support hash differs from canonical support")
    expected_rows = len(occupations) * len(observed_months)
    if len(frame) != expected_rows:
        raise AuditBlocked(f"balanced grid has {len(frame)} rather than {expected_rows} rows")
    if receipt.get("cells_row_count") != expected_rows:
        raise AuditBlocked("cell receipt row count differs from authenticated balanced grid")
    if receipt.get("occupation_count") != len(occupations):
        raise AuditBlocked("cell receipt occupation count differs from authenticated support")
    if receipt.get("observed_month_count") != len(observed_months):
        raise AuditBlocked("cell receipt month count differs from authenticated calendar")
    if receipt.get("support_hash_sha256") != expected_support_hash:
        raise AuditBlocked("cell receipt support hash differs from canonical support")
    counts = frame.groupby("occ_code", observed=True).month.nunique()
    if not counts.eq(len(observed_months)).all():
        raise AuditBlocked("one or more occupations lack an observed month")
    return frame.sort_values(["occ_code", "month"], kind="mergesort").reset_index(drop=True)


def quarter(month: str) -> str:
    return f"{month[:4]}Q{(int(month[5:7]) - 1) // 3 + 1}"


def pooled_regressors(frame: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
    q = frame["beta_quintile"].to_numpy(int)
    post = frame["month"].ge("2023-01").to_numpy()
    columns = [((q == value) & post).astype(float) for value in (2, 3, 4, 5)]
    labels = [f"Q{value}_x_post" for value in (2, 3, 4, 5)]
    columns.append(frame["webb_z"].to_numpy(float) * post)
    labels.append("Webb_z_x_post")
    return np.column_stack(columns), labels


def model_bundle(frame: pd.DataFrame, model_id: str) -> ModelBundle:
    if model_id.startswith("post_2020_"):
        selected = frame.loc[frame.month.ge("2020-01") & frame.month.ne("2022-12")].copy()
    else:
        selected = frame.loc[frame.month.ne("2022-12")].copy()
    selected = selected.sort_values(["occ_code", "month"], kind="mergesort").reset_index(drop=True)
    first = selected["occ_code"].astype(str).to_numpy(object)
    second = selected["month"].astype(str).to_numpy(object)
    focal = "Q5_x_post"
    focal_weights: np.ndarray | None = None
    reported_targets: dict[str, np.ndarray] | None = None

    static_models = {
        "pooled", "family_month", "family_post",
        "post_2020_unconditioned", "post_2020_family_month",
        "seasonal_quintile_month_unconditioned",
        "seasonal_quintile_month_family_month",
        "seasonal_occupation_month_unconditioned",
        "seasonal_occupation_month_family_month",
    }
    if model_id in static_models:
        x, labels = pooled_regressors(selected)
    elif model_id in {"dynamics_unconditioned", "dynamics_family_month"}:
        q = selected["beta_quintile"].to_numpy(int)
        bins = selected["month"].map(quarter).to_numpy(object)
        reference = "2022Q4"
        if reference not in set(bins):
            raise AuditBlocked("dynamic reference quarter 2022Q4 is absent")
        columns: list[np.ndarray] = []
        labels = []
        for period in sorted(set(bins) - {reference}):
            active = bins == period
            for value in (2, 3, 4, 5):
                columns.append(((q == value) & active).astype(float))
                labels.append(f"Q{value}_x_{period}")
            columns.append(selected["webb_z"].to_numpy(float) * active)
            labels.append(f"Webb_z_x_{period}")
        x = np.column_stack(columns)
        focal = "observed_calendar_month_weighted_post_Q5_functional"
        observed_months = sorted(selected.month.unique().tolist())
        post_months = [value for value in observed_months if value >= "2023-01"]
        if not post_months:
            raise AuditBlocked("dynamic post-functional calendar is empty")
        month_weights = {
            period: sum(quarter(value) == period for value in post_months) /
            len(post_months)
            for period in sorted(set(bins))
        }
        focal_weights = np.array([
            month_weights.get(label.rsplit("_", 1)[1], 0.0)
            if label.startswith("Q5_x_") and label.rsplit("_", 1)[1] >= "2023Q1"
            else 0.0
            for label in labels
        ], float)
        if not np.isclose(focal_weights.sum(), 1.0, rtol=0, atol=1e-14):
            raise AuditBlocked("dynamic post-functional weights do not sum to one")
        reported_targets = {}
        for index, label in enumerate(labels):
            if label.startswith("Q5_x_"):
                target = np.zeros(len(labels), float)
                target[index] = 1.0
                reported_targets[label] = target
    else:
        raise AuditBlocked(f"unknown model_id: {model_id}")

    if model_id == "family_post":
        all_period = selected.copy()
        all_period["stock"] = all_period.young + all_period.older
        weights = all_period.groupby("family", observed=True).stock.sum().to_dict()
        reference = max(sorted(weights), key=lambda value: (weights[value], value))
        post = selected.month.ge("2023-01").to_numpy()
        extra = []
        for family in sorted(set(selected.family) - {reference}):
            extra.append((selected.family.eq(family).to_numpy() & post).astype(float))
            labels.append(f"family_{family}_x_post")
        if extra:
            x = np.column_stack([x, *extra])
    if model_id in {
        "family_month", "dynamics_family_month", "post_2020_family_month",
        "seasonal_quintile_month_family_month",
        "seasonal_occupation_month_family_month",
    }:
        second = (selected["family"] + "|" + selected["month"]).to_numpy(object)
    if model_id in {
        "seasonal_quintile_month_unconditioned",
        "seasonal_quintile_month_family_month",
    }:
        q = selected.beta_quintile.to_numpy(int)
        moy = selected.month.str[5:7].astype(int).to_numpy()
        extra = []
        for value in (2, 3, 4, 5):
            for month_number in range(2, 13):
                extra.append(((q == value) & (moy == month_number)).astype(float))
                labels.append(f"Q{value}_x_month_of_year_{month_number:02d}")
        x = np.column_stack([x, *extra])
    elif model_id in {
        "seasonal_occupation_month_unconditioned",
        "seasonal_occupation_month_family_month",
    }:
        first = (
            selected["occ_code"] + "|m" + selected["month"].str[5:7]
        ).to_numpy(object)

    young = selected.young.to_numpy(float)
    older = selected.older.to_numpy(float)
    return ModelBundle(
        model_id=model_id,
        frame=selected,
        young=young,
        total=young + older,
        first_labels=first,
        second_labels=second,
        regressors=np.asarray(x, float),
        regressor_labels=labels,
        focal_target_label=focal,
        focal_target_weights=focal_weights,
        reported_target_weights=reported_targets,
    )


def dynamic_target_scope_diagnostics(
    bundle: ModelBundle,
    analysis: dict[str, Any],
) -> dict[str, Any]:
    """Authenticate the complete event-study target family and focal scalar."""
    if bundle.focal_target_weights is None:
        return {"status": "NOT_APPLICABLE"}
    contract = analysis.get("dynamic_target_scope")
    if not isinstance(contract, dict):
        return {
            "status": "BLOCKED_DYNAMIC_TARGET_SCOPE_CONTRACT_ABSENT",
        }
    reference = str(contract.get("reference_quarter"))
    post_start = str(contract.get("post_start_month"))
    observed_months = sorted(bundle.frame.month.unique().tolist())
    observed_quarters = sorted({quarter(value) for value in observed_months})
    expected_targets = [
        f"Q5_x_{value}" for value in observed_quarters if value != reference
    ]
    actual_targets = list((bundle.reported_target_weights or {}).keys())
    expected_pretrend = [
        label for label in expected_targets if label.rsplit("_", 1)[1] < reference
    ]
    actual_pretrend = [
        label for label in actual_targets if label.rsplit("_", 1)[1] < reference
    ]
    post_months = [value for value in observed_months if value >= post_start]
    expected_functional_weights = {
        f"Q5_x_{value}": sum(quarter(month) == value for month in post_months) /
        max(1, len(post_months))
        for value in observed_quarters if value >= quarter(post_start)
    }
    actual_functional_weights = {
        label: float(bundle.focal_target_weights[index])
        for index, label in enumerate(bundle.regressor_labels)
        if label.startswith("Q5_x_") and label.rsplit("_", 1)[1] >= quarter(post_start)
    }
    compared_labels = sorted(set(expected_functional_weights) | set(actual_functional_weights))
    weight_error = max((
        abs(expected_functional_weights.get(label, 0.0) -
            actual_functional_weights.get(label, 0.0))
        for label in compared_labels
    ), default=0.0)
    checks = {
        "reported_target_labels_exact": actual_targets == expected_targets,
        "reported_target_count": (
            len(actual_targets) == int(contract.get("reported_q5_event_target_count", -1))
        ),
        "joint_pretrend_labels_exact": actual_pretrend == expected_pretrend,
        "joint_pretrend_count": (
            len(actual_pretrend) == int(contract.get("joint_pretrend_target_count", -1))
        ),
        "observed_post_month_count": (
            len(post_months) == int(contract.get("observed_post_month_count", -1))
        ),
        "post_functional_weights_exact": weight_error <= 1e-14,
        "post_functional_weights_sum_to_one": bool(np.isclose(
            float(np.sum(bundle.focal_target_weights)), 1.0, rtol=0, atol=1e-14,
        )),
    }
    passed = all(checks.values())
    return {
        "status": (
            "PASS_COMPLETE_DYNAMIC_TARGET_SCOPE_CONSTRUCTION"
            if passed else "BLOCKED_INCOMPLETE_DYNAMIC_TARGET_SCOPE_CONSTRUCTION"
        ),
        "declared_primary_target": bundle.focal_target_label,
        "reference_quarter": reference,
        "reported_q5_event_targets": actual_targets,
        "reported_q5_event_target_count": len(actual_targets),
        "joint_pretrend_targets": actual_pretrend,
        "joint_pretrend_target_count": len(actual_pretrend),
        "observed_post_month_count": len(post_months),
        "post_functional_weight_sum": float(np.sum(bundle.focal_target_weights)),
        "post_functional_weight_max_absolute_error": float(weight_error),
        "checks": checks,
    }


def canonical_partition_codes(labels: np.ndarray) -> np.ndarray:
    mapping: dict[str, int] = {}
    result = np.empty(len(labels), dtype=np.int64)
    for index, raw in enumerate(labels):
        value = str(raw)
        if value not in mapping:
            mapping[value] = len(mapping)
        result[index] = mapping[value]
    return result


def normalized_regressor_labels(labels: list[str]) -> list[str]:
    return [
        value.replace("Webb_software_z_x_post", "Webb_z_x_post")
        .replace("family_", "SOC2_")
        .replace("_from_2023-01", "")
        for value in labels
    ]


def design_fingerprint(
    regressors: np.ndarray,
    labels: list[str],
    first: np.ndarray,
    second: np.ndarray,
) -> str:
    matrix = np.ascontiguousarray(np.asarray(regressors, dtype="<f8"))
    first_codes = np.ascontiguousarray(canonical_partition_codes(first), dtype="<i8")
    second_codes = np.ascontiguousarray(canonical_partition_codes(second), dtype="<i8")
    header = canonical_bytes({
        "matrix_shape": list(matrix.shape),
        "labels": normalized_regressor_labels(labels),
        "first_groups": int(first_codes.max()) + 1 if len(first_codes) else 0,
        "second_groups": int(second_codes.max()) + 1 if len(second_codes) else 0,
        "serialization": "little-endian float64 matrix then first-appearance int64 FE partitions",
    })
    return hashlib.sha256(
        header + b"\0" + matrix.tobytes(order="C") + b"\0" +
        first_codes.tobytes(order="C") + b"\0" + second_codes.tobytes(order="C")
    ).hexdigest()


def load_submitted_design_modules(
    repo_root: pathlib.Path, analysis: dict[str, Any],
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    paths = analysis["design_parity"]["submitted_source_sha256"]
    for key, relative in (
        ("baseline", "yax/revision/substantive_r3_20260905/rebuilt_baseline/run_rebuilt_corrected_baseline.py"),
        ("family", "yax/revision/substantive_r3_20260905/within_family/run_within_family.py"),
        ("dynamics", "yax/revision/substantive_r3_20260905/dynamics/run_dynamics.py"),
    ):
        if relative not in paths:
            raise AuditBlocked(f"analysis spec omits parity source: {pathlib.Path(relative).name}")
        result[key] = import_legacy_module(f"yax_v3_parity_{key}", repo_root / relative)
    dynamics_text = (
        repo_root /
        "yax/revision/substantive_r3_20260905/dynamics/run_dynamics.py"
    ).read_text(encoding="utf-8")
    transition_statement = "months = [month for month in setup[\"observed_months\"] if month != TRANSITION]"
    if transition_statement not in dynamics_text:
        raise AuditBlocked("cannot verify submitted dynamics transition-month policy from locked code")
    result["dynamics_transition_source_statement"] = transition_statement
    return result


def import_legacy_module(name: str, path: pathlib.Path):
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:
        raise AuditBlocked(f"cannot import submitted design module {path.name}")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return module


def submitted_design_parity(
    bundle: ModelBundle,
    modules: dict[str, Any],
) -> dict[str, Any]:
    frame = bundle.frame
    occupations = sorted(frame.occ_code.unique())
    months = sorted(frame.month.unique())
    expected_rows = len(occupations) * len(months)
    if len(frame) != expected_rows:
        raise AuditBlocked(f"{bundle.model_id} is not balanced for design parity")
    assignment = frame.drop_duplicates("occ_code").set_index("occ_code").loc[occupations]
    q = assignment.beta_quintile.to_numpy(int)
    webb = assignment.webb_z.to_numpy(float)
    majors = assignment.family.astype(str).to_numpy(object)
    stock = frame.groupby("occ_code", observed=True)[["young", "older"]].sum().sum(axis=1).reindex(occupations).to_numpy(float)
    post = np.array([month >= "2023-01" for month in months])
    n_occ, n_month = len(occupations), len(months)
    submitted_first = np.repeat(np.arange(n_occ), n_month)

    if bundle.model_id == "pooled":
        submitted_x, submitted_labels = modules["baseline"].regressors(q, webb, months)
        submitted_second = np.tile(np.arange(n_month), n_occ)
    elif bundle.model_id in {"family_post", "family_month"}:
        targets = [
            ((((q == value)[:, None]) & post[None, :]).reshape(-1).astype(float))
            for value in (2, 3, 4, 5)
        ]
        target_labels = [f"Q{value}_x_post" for value in (2, 3, 4, 5)]
        structure = "SOC2_x_post" if bundle.model_id == "family_post" else "SOC2_x_calendar_month"
        submitted_x, submitted_labels, _ = modules["family"].assemble_regressors(
            targets, target_labels, webb, post, majors, stock, structure,
        )
        submitted_second = modules["family"].fixed_effect_codes(majors, n_month, structure)
    elif bundle.model_id in {"dynamics_unconditioned", "dynamics_family_month"}:
        if "2022-12" in months:
            raise AuditBlocked("submitted dynamics code excludes 2022-12; parity input retained it")
        submitted_x, submitted_labels, _, _, _ = modules["dynamics"].build_dynamic_regressors(
            q, webb, months
        )
        structure = (
            "SOC2_x_calendar_month"
            if bundle.model_id == "dynamics_family_month" else "unconditioned"
        )
        submitted_second = modules["dynamics"].fe_codes(majors, n_month, structure)
    elif bundle.model_id in {
        "post_2020_unconditioned", "post_2020_family_month",
        "seasonal_quintile_month_unconditioned",
        "seasonal_quintile_month_family_month",
        "seasonal_occupation_month_unconditioned",
        "seasonal_occupation_month_family_month",
    }:
        submitted_x, submitted_labels = modules["dynamics"].build_static_regressors(
            q, webb, months, onset="2023-01",
            quintile_month_of_year=bundle.model_id.startswith("seasonal_quintile_month_"),
        )
        structure = (
            "SOC2_x_calendar_month" if bundle.model_id.endswith("_family_month")
            else "unconditioned"
        )
        submitted_second = modules["dynamics"].fe_codes(majors, n_month, structure)
        if bundle.model_id.startswith("seasonal_occupation_month_"):
            season = np.tile(np.array([int(value[5:7]) - 1 for value in months]), n_occ)
            submitted_first = np.repeat(np.arange(n_occ), n_month) * 12 + season
    else:  # pragma: no cover - registry validation prevents this branch
        raise AuditBlocked(f"no submitted parity definition for {bundle.model_id}")

    own_labels = normalized_regressor_labels(bundle.regressor_labels)
    reference_labels = normalized_regressor_labels(list(submitted_labels))
    matrix_equal = bool(
        bundle.regressors.shape == np.asarray(submitted_x).shape and
        np.array_equal(bundle.regressors, np.asarray(submitted_x, float))
    )
    labels_equal = own_labels == reference_labels
    first_equal = np.array_equal(
        canonical_partition_codes(bundle.first_labels),
        canonical_partition_codes(np.asarray(submitted_first)),
    )
    second_equal = np.array_equal(
        canonical_partition_codes(bundle.second_labels),
        canonical_partition_codes(np.asarray(submitted_second)),
    )
    own_fingerprint = design_fingerprint(
        bundle.regressors, bundle.regressor_labels, bundle.first_labels, bundle.second_labels
    )
    submitted_fingerprint = design_fingerprint(
        np.asarray(submitted_x, float), list(submitted_labels),
        np.asarray(submitted_first), np.asarray(submitted_second),
    )
    passed = matrix_equal and labels_equal and first_equal and second_equal and own_fingerprint == submitted_fingerprint
    return {
        "status": "PASS_EXACT_SUBMITTED_DESIGN_PARITY" if passed else "FAIL_SUBMITTED_DESIGN_PARITY",
        "matrix_exactly_equal": matrix_equal,
        "semantic_labels_equal": labels_equal,
        "first_fe_partition_equal": first_equal,
        "second_fe_partition_equal": second_equal,
        "audit_design_fingerprint_sha256": own_fingerprint,
        "submitted_design_fingerprint_sha256": submitted_fingerprint,
        "months": len(months),
        "transition_2022_12_included": "2022-12" in months,
        "dynamics_transition_adjudication": (
            "locked submitted setup_historical removes TRANSITION=2022-12 before dynamic_model"
            if bundle.model_id.startswith("dynamics_") else "not_applicable"
        ),
    }


def family_month_boundary_rows(bundle: ModelBundle) -> list[dict[str, Any]]:
    frame = bundle.frame[["family", "month", "young", "older"]].copy()
    grouped = frame.groupby(["family", "month"], observed=True, as_index=False).agg(
        young=("young", "sum"), older=("older", "sum"), occupation_cells=("young", "size")
    )
    grouped["total"] = grouped.young + grouped.older
    grouped = grouped.loc[
        grouped.total.gt(0) & (grouped.young.eq(0) | grouped.older.eq(0))
    ]
    return [{
        "model_id": bundle.model_id,
        "family": row.family,
        "month": row.month,
        "occupation_cells": int(row.occupation_cells),
        "young": float(row.young),
        "older": float(row.older),
        "total": float(row.total),
        "zero_young": bool(row.young == 0),
        "zero_older": bool(row.older == 0),
    } for row in grouped.itertuples(index=False)]


def profile_boundary_nuisance(
    bundle: ModelBundle,
    initial_active: np.ndarray | None = None,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    active = bundle.total > 0
    if initial_active is not None:
        if len(initial_active) != len(active):
            raise ValueError("initial boundary-profile mask length mismatch")
        active &= np.asarray(initial_active, bool)
    records: list[dict[str, Any]] = []
    iteration = 0
    while True:
        iteration += 1
        remove = np.zeros(len(active), dtype=bool)
        iteration_records: list[dict[str, Any]] = []
        for partition, labels in (
            ("first_fixed_effect", bundle.first_labels),
            ("second_fixed_effect", bundle.second_labels),
        ):
            for level in sorted(set(labels[active].tolist())):
                mask = active & (labels == level)
                young = float(bundle.young[mask].sum())
                older = float((bundle.total[mask] - bundle.young[mask]).sum())
                if young == 0.0 or older == 0.0:
                    remove |= mask
                    iteration_records.append({
                        "model_id": bundle.model_id,
                        "iteration": iteration,
                        "partition": partition,
                        "group": str(level),
                        "boundary_side": "zero_young" if young == 0.0 else "zero_older",
                        "affected_rows_before_union": int(mask.sum()),
                        "young": young,
                        "older": older,
                        "total": young + older,
                    })
        if not remove.any():
            break
        if np.all(remove[active]):
            records.extend(iteration_records)
            active[:] = False
            break
        records.extend(iteration_records)
        active &= ~remove
    return active, records


class UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))
        self.size = [1] * size

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        left, right = self.find(left), self.find(right)
        if left == right:
            return
        if self.size[left] < self.size[right]:
            left, right = right, left
        self.parent[right] = left
        self.size[left] += self.size[right]


def make_sparse_design(bundle: ModelBundle, active: np.ndarray) -> SparseDesign:
    first_levels, first = np.unique(bundle.first_labels[active].astype(str), return_inverse=True)
    second_levels, second = np.unique(bundle.second_labels[active].astype(str), return_inverse=True)
    first_levels = first_levels.tolist()
    second_levels = second_levels.tolist()
    n_first, n_second = len(first_levels), len(second_levels)
    graph = UnionFind(n_first + n_second)
    for left, right in zip(first, second):
        graph.union(int(left), n_first + int(right))
    components: dict[int, dict[str, set[int]]] = {}
    for index in range(n_first):
        components.setdefault(graph.find(index), {"first": set(), "second": set()})["first"].add(index)
    for index in range(n_second):
        components.setdefault(graph.find(n_first + index), {"first": set(), "second": set()})["second"].add(index)
    ordered_components = sorted(
        components.values(),
        key=lambda item: min(first_levels[index] for index in item["first"]),
    )
    references: set[int] = set()
    component_sizes: list[dict[str, int]] = []
    for item in ordered_components:
        reference = min(item["second"], key=lambda index: second_levels[index])
        references.add(reference)
        component_sizes.append({
            "first_groups": len(item["first"]),
            "second_groups": len(item["second"]),
        })
    second_column: dict[int, int] = {}
    nuisance_column_labels = [f"first_FE:{value}" for value in first_levels]
    cursor = n_first
    for index in range(n_second):
        if index not in references:
            second_column[index] = cursor
            nuisance_column_labels.append(f"second_FE:{second_levels[index]}")
            cursor += 1
    rows = np.arange(len(first), dtype=int)
    row_parts = [rows]
    col_parts = [first.astype(int)]
    second_keep = np.array([value not in references for value in second], dtype=bool)
    if second_keep.any():
        row_parts.append(rows[second_keep])
        col_parts.append(np.array([second_column[int(value)] for value in second[second_keep]], int))
    nuisance = sparse.coo_matrix(
        (
            np.ones(sum(len(value) for value in row_parts), dtype=float),
            (np.concatenate(row_parts), np.concatenate(col_parts)),
        ),
        shape=(len(rows), cursor),
    ).tocsr()
    regressors = sparse.csr_matrix(bundle.regressors[active])
    full = sparse.hstack([nuisance, regressors], format="csr")
    return SparseDesign(
        nuisance=nuisance,
        full=full,
        first_codes=first,
        second_codes=second,
        first_levels=first_levels,
        second_levels=second_levels,
        component_count=len(ordered_components),
        component_sizes=component_sizes,
        second_references=[second_levels[index] for index in sorted(references)],
        nuisance_column_labels=nuisance_column_labels,
    )


def schur_information(
    nuisance: sparse.csr_matrix, regressors: np.ndarray, weight: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    x = np.asarray(regressors, float)
    if x.shape[1] == 0:
        return np.empty((0, 0)), x.copy()
    if nuisance.shape[1] == 0:
        return x.T @ (weight[:, None] * x), x.copy()
    wn = nuisance.multiply(weight[:, None])
    hnn = (nuisance.T @ wn).tocsc()
    cross = np.asarray(nuisance.T @ (weight[:, None] * x), float)
    try:
        factor = splu(hnn)
    except RuntimeError as error:
        raise AuditBlocked("normalized nuisance Hessian is singular") from error
    projected_coefficients = factor.solve(cross)
    residualized = x - nuisance @ projected_coefficients
    information = residualized.T @ (weight[:, None] * residualized)
    return (information + information.T) / 2.0, np.asarray(residualized)


def information_diagnostics(
    design: SparseDesign,
    regressors: np.ndarray,
    weight: np.ndarray,
    focal_target: int,
    relative_tolerance: float,
) -> dict[str, Any]:
    information, _ = schur_information(design.nuisance, regressors, weight)
    eigenvalues = np.linalg.eigvalsh(information) if information.size else np.empty(0)
    largest = float(max(eigenvalues[-1], 0.0)) if len(eigenvalues) else 0.0
    threshold = max(largest * relative_tolerance, np.finfo(float).eps * max(1.0, largest))
    positive = eigenvalues[eigenvalues > threshold]
    rank = int(len(positive))
    condition = float(positive[-1] / positive[0]) if len(positive) else math.inf
    if information.shape[0] == 1:
        target_info = float(information[0, 0])
    else:
        others = [index for index in range(information.shape[0]) if index != focal_target]
        cross = information[np.ix_(others, [focal_target])].reshape(-1)
        other = information[np.ix_(others, others)]
        target_info = float(
            information[focal_target, focal_target] - cross @ np.linalg.pinv(other) @ cross
        )
    if eigenvalues.size:
        _, vectors = np.linalg.eigh(information)
        null = vectors[:, eigenvalues <= threshold]
        focal_null_loading = float(np.max(np.abs(null[focal_target]))) if null.size else 0.0
    else:
        focal_null_loading = math.inf
    return {
        "treatment_information_rank": rank,
        "treatment_information_columns": int(information.shape[0]),
        "treatment_information_eigenvalues": eigenvalues.tolist(),
        "treatment_information_rank_threshold": threshold,
        "treatment_information_condition_positive_spectrum": condition,
        "focal_target_conditional_information": target_info,
        "focal_target_null_space_max_loading": focal_null_loading,
        "focal_target_rank_identified": bool(focal_null_loading <= 1e-8 and target_info > threshold),
    }


def reported_target_information_diagnostics(
    nuisance: sparse.csr_matrix,
    regressors: np.ndarray,
    weight: np.ndarray,
    targets: dict[str, np.ndarray] | None,
    relative_tolerance: float,
) -> dict[str, Any]:
    if not targets:
        return {"status": "NOT_APPLICABLE", "reported_target_count": 0}
    labels = list(targets)
    target_matrix = np.vstack([np.asarray(targets[label], float) for label in labels])
    information, _ = schur_information(nuisance, regressors, weight)
    covariance = target_matrix @ np.linalg.pinv(information) @ target_matrix.T
    covariance = (covariance + covariance.T) / 2.0
    eigen = np.linalg.eigvalsh(covariance)
    largest = float(max(eigen[-1], 0.0)) if len(eigen) else 0.0
    threshold = max(
        largest * relative_tolerance,
        np.finfo(float).eps * max(1.0, largest),
    )
    rank = int(np.sum(eigen > threshold))
    pre_indices = [
        index for index, label in enumerate(labels)
        if label.rsplit("_", 1)[1] < "2022Q4"
    ]
    pre_covariance = covariance[np.ix_(pre_indices, pre_indices)]
    pre_eigen = np.linalg.eigvalsh(pre_covariance)
    pre_largest = float(max(pre_eigen[-1], 0.0)) if len(pre_eigen) else 0.0
    pre_threshold = max(
        pre_largest * relative_tolerance,
        np.finfo(float).eps * max(1.0, pre_largest),
    )
    pre_rank = int(np.sum(pre_eigen > pre_threshold))
    passed = rank == len(labels) and pre_rank == len(pre_indices)
    return {
        "status": (
            "PASS_ALL_REPORTED_TARGETS_AND_JOINT_PRETREND_INFORMATION_RANK"
            if passed else "BLOCKED_REPORTED_TARGET_OR_PRETREND_INFORMATION_RANK"
        ),
        "reported_target_count": len(labels),
        "reported_target_rank": rank,
        "reported_target_rank_threshold": threshold,
        "reported_target_covariance_eigenvalues": eigen.tolist(),
        "joint_pretrend_target_count": len(pre_indices),
        "joint_pretrend_information_rank": pre_rank,
        "joint_pretrend_rank_threshold": pre_threshold,
        "joint_pretrend_covariance_eigenvalues": pre_eigen.tolist(),
    }


def full_hessian_diagnostics(
    design: sparse.csr_matrix,
    weight: np.ndarray,
    expected_rank: int,
    relative_tolerance: float,
    dense_limit: int = 1200,
) -> dict[str, Any]:
    hessian = (design.T @ design.multiply(weight[:, None])).tocsc()
    hessian = (hessian + hessian.T) * 0.5
    columns = hessian.shape[0]
    diagonal = np.asarray(hessian.diagonal(), float)
    if np.any(diagonal <= 0):
        return {
            "columns": columns,
            "rank_from_nuisance_plus_schur": expected_rank,
            "status": "NONPOSITIVE_HESSIAN_DIAGONAL",
            "nonpositive_diagonal_columns": int(np.sum(diagonal <= 0)),
        }

    def spectrum(matrix: sparse.csc_matrix) -> dict[str, Any]:
        conservative_upper = float(np.max(np.asarray(
            np.abs(matrix).sum(axis=1)
        ).reshape(-1), initial=0.0))
        if columns <= dense_limit:
            eigen, vectors = np.linalg.eigh(matrix.toarray())
            smallest = float(eigen[0])
            largest = float(eigen[-1])
            smallest_vector = vectors[:, 0]
            largest_vector = vectors[:, -1]
            method = "dense_eigh_with_explicit_residual_bounds"
        else:
            try:
                small_values, small_vectors = eigsh(
                    matrix, k=1, which="SA", return_eigenvectors=True,
                    tol=0.0, maxiter=max(50_000, columns * 100),
                )
                large_values, large_vectors = eigsh(
                    matrix, k=1, which="LA", return_eigenvectors=True,
                    tol=0.0, maxiter=max(50_000, columns * 100),
                )
                smallest = float(small_values[0])
                largest = float(large_values[0])
                smallest_vector = np.asarray(small_vectors[:, 0], float)
                largest_vector = np.asarray(large_vectors[:, 0], float)
                method = (
                    "sparse_eigsh_SA_LA_machine_tolerance_with_explicit_"
                    "residual_bounds"
                )
            except (ArpackNoConvergence, RuntimeError, ValueError) as error:
                return {
                    "smallest_estimate": math.nan,
                    "largest_estimate": math.nan,
                    "smallest_residual_norm_2": math.inf,
                    "largest_residual_norm_2": math.inf,
                    "smallest_certified_lower_bound": -math.inf,
                    "largest_conservative_upper_bound": conservative_upper,
                    "method": f"FAILED_{type(error).__name__}",
                }
        smallest_residual = float(np.linalg.norm(
            np.asarray(matrix @ smallest_vector).reshape(-1)
            - smallest * smallest_vector
        ))
        largest_residual = float(np.linalg.norm(
            np.asarray(matrix @ largest_vector).reshape(-1)
            - largest * largest_vector
        ))
        return {
            "smallest_estimate": smallest,
            "largest_estimate": largest,
            "smallest_residual_norm_2": smallest_residual,
            "largest_residual_norm_2": largest_residual,
            "smallest_certified_lower_bound": smallest - smallest_residual,
            # The induced infinity norm is a rigorous eigenvalue upper bound
            # for this symmetric matrix and is never replaced by the Ritz
            # estimate when setting the declared relative rank threshold.
            "largest_conservative_upper_bound": conservative_upper,
            "method": method,
        }

    raw_spectrum = spectrum(hessian)
    inv_scale = sparse.diags(1.0 / np.sqrt(diagonal))
    scaled = (inv_scale @ hessian @ inv_scale).tocsc()
    scaled_spectrum = spectrum(scaled)
    smallest = raw_spectrum["smallest_estimate"]
    largest = raw_spectrum["largest_estimate"]
    smallest_lower = raw_spectrum["smallest_certified_lower_bound"]
    largest_upper = raw_spectrum["largest_conservative_upper_bound"]
    scaled_smallest = scaled_spectrum["smallest_estimate"]
    scaled_largest = scaled_spectrum["largest_estimate"]
    scaled_smallest_lower = scaled_spectrum[
        "smallest_certified_lower_bound"
    ]
    scaled_largest_upper = scaled_spectrum[
        "largest_conservative_upper_bound"
    ]
    raw_threshold = max(
        largest_upper * relative_tolerance,
        np.finfo(float).eps * max(1.0, largest_upper),
    ) if math.isfinite(largest_upper) else math.inf
    scaled_threshold = max(
        scaled_largest_upper * relative_tolerance,
        np.finfo(float).eps * max(1.0, scaled_largest_upper),
    ) if math.isfinite(scaled_largest_upper) else math.inf
    spectrum_pass = bool(
        expected_rank == columns and
        math.isfinite(smallest_lower) and math.isfinite(largest_upper) and
        math.isfinite(scaled_smallest_lower) and
        math.isfinite(scaled_largest_upper) and
        smallest_lower > raw_threshold and
        scaled_smallest_lower > scaled_threshold
    )
    return {
        "columns": columns,
        "rank_from_nuisance_plus_schur": expected_rank,
        "rank_deficiency": columns - expected_rank,
        "spectrum_method": raw_spectrum["method"],
        "smallest_positive_or_extreme_eigenvalue": smallest,
        "largest_eigenvalue": largest,
        "smallest_eigenpair_residual_norm_2": raw_spectrum[
            "smallest_residual_norm_2"
        ],
        "largest_eigenpair_residual_norm_2": raw_spectrum[
            "largest_residual_norm_2"
        ],
        "smallest_certified_lower_bound": smallest_lower,
        "largest_conservative_upper_bound": largest_upper,
        "condition_number": (
            largest / smallest if math.isfinite(smallest) and smallest > 0 else math.inf
        ),
        "rank_threshold": raw_threshold,
        "diagonally_scaled_spectrum_method": scaled_spectrum["method"],
        "diagonally_scaled_smallest_positive_or_extreme_eigenvalue": scaled_smallest,
        "diagonally_scaled_largest_eigenvalue": scaled_largest,
        "diagonally_scaled_smallest_eigenpair_residual_norm_2": (
            scaled_spectrum["smallest_residual_norm_2"]
        ),
        "diagonally_scaled_largest_eigenpair_residual_norm_2": (
            scaled_spectrum["largest_residual_norm_2"]
        ),
        "diagonally_scaled_smallest_certified_lower_bound": (
            scaled_smallest_lower
        ),
        "diagonally_scaled_largest_conservative_upper_bound": (
            scaled_largest_upper
        ),
        "diagonally_scaled_condition_number": (
            scaled_largest / scaled_smallest
            if math.isfinite(scaled_smallest) and scaled_smallest > 0 else math.inf
        ),
        "diagonally_scaled_rank_threshold": scaled_threshold,
        "positive_definite_at_declared_tolerance": spectrum_pass,
        "status": (
            "PASS_FULL_HESSIAN_SPECTRUM" if spectrum_pass
            else "BLOCKED_FULL_HESSIAN_SPECTRUM_FAILURE"
        ),
    }


def select_regressor_basis_preserving_focal(
    nuisance: sparse.csr_matrix,
    regressors: np.ndarray,
    weight: np.ndarray,
    focal_target: int,
    geometry: dict[str, Any],
) -> tuple[list[int], dict[str, Any]]:
    columns = regressors.shape[1]
    rank = int(geometry["treatment_information_rank"])
    if rank == columns:
        selected = list(range(columns))
        return selected, {
            "status": "FULL_ORIGINAL_TREATMENT_RANK",
            "selected_original_columns": selected,
            "dropped_dependent_original_columns": [],
        }
    if not geometry["focal_target_rank_identified"]:
        raise AuditBlocked("cannot reduce rank while preserving an unidentified focal coefficient")
    _, residualized = schur_information(nuisance, regressors, weight)
    weighted = np.sqrt(weight)[:, None] * residualized
    focal = weighted[:, focal_target]
    focal_ss = float(focal @ focal)
    if focal_ss <= 0:
        raise AuditBlocked("focal target has zero residual norm during basis construction")
    candidates = [index for index in range(columns) if index != focal_target]
    if rank > 1:
        z = weighted[:, candidates]
        z = z - np.outer(focal, focal @ z / focal_ss)
        _, triangular, pivots = qr(z, mode="economic", pivoting=True)
        diagonal = np.abs(np.diag(triangular))
        tolerance = max(diagonal[0] * 1e-10, np.finfo(float).eps) if len(diagonal) else 0.0
        additional = []
        for position, pivot in enumerate(pivots[:rank - 1]):
            if position < len(diagonal) and diagonal[position] > tolerance:
                additional.append(candidates[int(pivot)])
        if len(additional) != rank - 1:
            raise AuditBlocked("pivoted QR did not recover the declared treatment rank")
    else:
        additional = []
    selected = [focal_target, *additional]
    dropped = [index for index in range(columns) if index not in selected]
    reduced_information, _ = schur_information(nuisance, regressors[:, selected], weight)
    if np.linalg.matrix_rank(reduced_information, tol=max(np.linalg.eigvalsh(reduced_information)[-1] * 1e-10, 1e-14)) != rank:
        raise AuditBlocked("reduced treatment basis failed the full-rank check")
    return selected, {
        "status": "EXACT_COLUMN_SPACE_BASIS_WITH_FOCAL_PRESERVED",
        "selected_original_columns": selected,
        "dropped_dependent_original_columns": dropped,
        "original_columns": columns,
        "reduced_columns": len(selected),
    }


def replace_design_regressors(
    design: SparseDesign, regressors: np.ndarray,
) -> SparseDesign:
    return SparseDesign(
        nuisance=design.nuisance,
        full=sparse.hstack([design.nuisance, sparse.csr_matrix(regressors)], format="csr"),
        first_codes=design.first_codes,
        second_codes=design.second_codes,
        first_levels=design.first_levels,
        second_levels=design.second_levels,
        component_count=design.component_count,
        component_sizes=design.component_sizes,
        second_references=design.second_references,
        nuisance_column_labels=design.nuisance_column_labels,
    )


def lp_primal_certificate(
    solution: np.ndarray,
    objective: np.ndarray,
    reported_objective: float,
    a_ub: sparse.spmatrix | None,
    b_ub: np.ndarray | None,
    a_eq: sparse.spmatrix | None,
    b_eq: np.ndarray | None,
    bounds: list[tuple[float | None, float | None]],
    tolerance: float,
) -> dict[str, Any]:
    """Independently certify a HiGHS candidate on scaled primal residuals."""
    x = np.asarray(solution, float)

    def scaled_rows(
        matrix: sparse.spmatrix | None, rhs: np.ndarray | None, equality: bool,
    ) -> tuple[float, float]:
        if matrix is None or matrix.shape[0] == 0:
            return 0.0, 0.0
        matrix = sparse.csr_matrix(matrix)
        rhs_array = np.asarray(rhs, float)
        residual = np.asarray(matrix @ x).reshape(-1) - rhs_array
        violation = np.abs(residual) if equality else np.maximum(residual, 0.0)
        scale = 1.0 + np.asarray(abs(matrix) @ np.abs(x)).reshape(-1) + np.abs(rhs_array)
        return float(np.max(violation)), float(np.max(violation / scale))

    equality_absolute, equality_scaled = scaled_rows(a_eq, b_eq, True)
    inequality_absolute, inequality_scaled = scaled_rows(a_ub, b_ub, False)
    bound_violation = 0.0
    bound_scaled = 0.0
    for value, (lower, upper) in zip(x, bounds):
        violation = max(
            0.0,
            0.0 if lower is None else lower - value,
            0.0 if upper is None else value - upper,
        )
        bound_violation = max(bound_violation, violation)
        bound_scaled = max(bound_scaled, violation / (1.0 + abs(value)))
    recomputed_objective = float(np.asarray(objective, float) @ x)
    objective_error = abs(recomputed_objective - float(reported_objective))
    objective_scaled = objective_error / (
        1.0 + abs(recomputed_objective) + abs(float(reported_objective))
    )
    finite = bool(
        np.isfinite(x).all() and math.isfinite(recomputed_objective) and
        math.isfinite(float(reported_objective))
    )
    passed = bool(
        finite and equality_scaled <= tolerance and
        inequality_scaled <= tolerance and bound_scaled <= tolerance and
        objective_scaled <= tolerance
    )
    return {
        "status": "PASS_PRIMAL_CERTIFICATE" if passed else "FAIL_PRIMAL_CERTIFICATE",
        "passed": passed,
        "tolerance": tolerance,
        "equality_max_absolute_residual": equality_absolute,
        "equality_max_scaled_residual": equality_scaled,
        "inequality_max_absolute_violation": inequality_absolute,
        "inequality_max_scaled_violation": inequality_scaled,
        "bound_max_absolute_violation": bound_violation,
        "bound_max_scaled_violation": bound_scaled,
        "reported_objective": float(reported_objective),
        "recomputed_objective": recomputed_objective,
        "objective_scaled_discrepancy": objective_scaled,
    }


def separation_lp(
    design: sparse.csr_matrix,
    young: np.ndarray,
    total: np.ndarray,
    focal_column: int,
    margin_tolerance: float,
    column_labels: list[str] | None = None,
    certification_tolerance: float = LP_CERTIFICATION_TOLERANCE,
    additional_target_vectors: dict[str, np.ndarray] | None = None,
) -> dict[str, Any]:
    zero = young == 0.0
    one = young == total
    boundary = zero | one
    interior = ~boundary
    if not boundary.any():
        return {
            "status": "NO_BOUNDARY_ROWS_AFTER_PROFILING",
            "boundary_rows": 0,
            "interior_rows": int(interior.sum()),
            "separation_exists": False,
            "maximum_normalized_recession_gain": 0.0,
            "focal_target_direction_min": 0.0,
            "focal_target_direction_max": 0.0,
            "focal_target_can_move": False,
            "focal_target_direction_audit_complete": True,
            "separation_type": "NONE",
            "strictly_separated_boundary_rows": 0,
            "zero_margin_boundary_rows": 0,
            "strict_boundary_local_indices": [],
            "strict_boundary_margins": [],
            "reported_target_direction_audits": {
                label: {
                    "positive_direction": {"status": "NOT_NEEDED_NO_SEPARATION", "feasible": False},
                    "negative_direction": {"status": "NOT_NEEDED_NO_SEPARATION", "feasible": False},
                    "audit_complete": True,
                    "target_can_move": False,
                }
                for label in (additional_target_vectors or {})
            },
            "all_reported_targets_direction_audit_complete": True,
            "any_reported_target_can_move": False,
        }
    signs = np.where(one[boundary], 1.0, -1.0)
    boundary_design = design[boundary]
    cone = -boundary_design.multiply(signs[:, None])
    gain = np.asarray(boundary_design.T @ signs).reshape(-1)
    equality = design[interior] if interior.any() else None
    result = linprog(
        -gain,
        A_ub=cone,
        b_ub=np.zeros(cone.shape[0]),
        A_eq=equality,
        b_eq=np.zeros(equality.shape[0]) if equality is not None else None,
        bounds=[(-1.0, 1.0)] * design.shape[1],
        method="highs",
        options=HIGHS_CERTIFIED_OPTIONS,
    )
    if not result.success:
        return {
            "status": "LP_SOLVER_FAILURE",
            "message": result.message,
            "boundary_rows": int(boundary.sum()),
            "interior_rows": int(interior.sum()),
            "separation_exists": None,
            "focal_target_can_move": None,
        }
    global_certificate = lp_primal_certificate(
        result.x, -gain, float(result.fun), cone, np.zeros(cone.shape[0]),
        equality, np.zeros(equality.shape[0]) if equality is not None else None,
        [(-1.0, 1.0)] * design.shape[1], certification_tolerance,
    )
    if not global_certificate["passed"]:
        return {
            "status": "LP_NUMERICAL_CERTIFICATION_FAILURE",
            "message": result.message,
            "boundary_rows": int(boundary.sum()),
            "interior_rows": int(interior.sum()),
            "separation_exists": None,
            "focal_target_can_move": None,
            "global_primal_certificate": global_certificate,
        }
    raw_gain = float(gain @ result.x)
    normalized_gain = raw_gain / max(1, int(boundary.sum()))
    separated = normalized_gain > margin_tolerance
    margins = signs * np.asarray(boundary_design @ result.x).reshape(-1)
    strict = margins > margin_tolerance

    def target_direction(direction: float, target_vector: np.ndarray) -> dict[str, Any]:
        if not separated:
            return {"status": "NOT_NEEDED_NO_SEPARATION", "feasible": False}
        target_vector = np.asarray(target_vector, float)
        if target_vector.shape != (design.shape[1],) or not np.isfinite(target_vector).all():
            return {"status": "INVALID_TARGET_VECTOR", "feasible": None}
        target_row = sparse.csr_matrix(target_vector.reshape(1, -1))
        columns = design.shape[1]
        # Minimize an infinity-norm epigraph subject to focal=+/-1. This
        # produces a finite candidate whenever a target-moving cone direction
        # exists, so every affirmative result has a primal witness to certify.
        extended_cone = sparse.hstack(
            [cone, sparse.csr_matrix((cone.shape[0], 1))], format="csr"
        )
        identity = sparse.identity(columns, format="csr")
        epigraph = sparse.vstack([
            sparse.hstack([identity, -np.ones((columns, 1))], format="csr"),
            sparse.hstack([-identity, -np.ones((columns, 1))], format="csr"),
        ], format="csr")
        target_a_ub = sparse.vstack([extended_cone, epigraph], format="csr")
        target_b_ub = np.zeros(target_a_ub.shape[0])
        target_equality = (
            target_row if equality is None else sparse.vstack(
                [equality, target_row], format="csr"
            )
        )
        target_equality = sparse.hstack([
            target_equality,
            sparse.csr_matrix((target_equality.shape[0], 1)),
        ], format="csr")
        target_rhs = np.concatenate([
            np.zeros(0 if equality is None else equality.shape[0]), [direction]
        ])
        target_objective = np.concatenate([np.zeros(columns), [1.0]])
        target_bounds = [(None, None)] * columns + [(0.0, None)]
        feasible = linprog(
            target_objective,
            A_ub=target_a_ub, b_ub=target_b_ub,
            A_eq=target_equality, b_eq=target_rhs,
            bounds=target_bounds, method="highs",
            options=HIGHS_CERTIFIED_OPTIONS,
        )
        if feasible.success:
            certificate = lp_primal_certificate(
                feasible.x, target_objective, float(feasible.fun),
                target_a_ub, target_b_ub, target_equality, target_rhs,
                target_bounds, certification_tolerance,
            )
            if not certificate["passed"]:
                return {
                    "status": "LP_TARGET_CERTIFICATION_FAILURE",
                    "feasible": None,
                    "primal_certificate": certificate,
                }
            direction_vector = np.asarray(feasible.x[:-1], float)
            target_gain = float(gain @ direction_vector)
            normalized = target_gain / max(1, int(boundary.sum()))
            # Every cone-feasible unit-target direction makes the target
            # unbounded on the extended likelihood, even when its gain is
            # exactly zero: zero gain is a likelihood lineality direction,
            # not evidence of a finite or unique target.  The independently
            # certified global LP has already established that this branch is
            # reached on a nontrivial recession face.
            return {
                "status": "FEASIBLE_TARGET_MOVING_RECESSION",
                "feasible": True,
                "raw_recession_gain": target_gain,
                "normalized_recession_gain": normalized,
                "strict_likelihood_improvement": normalized > margin_tolerance,
                "zero_gain_lineality_is_target_moving": normalized <= margin_tolerance,
                "minimum_infinity_norm_for_unit_target": float(feasible.x[-1]),
                "primal_certificate": certificate,
            }
        if int(feasible.status) == 2:
            return {
                "status": "INFEASIBLE_NO_TARGET_DIRECTION",
                "feasible": False,
                "solver_message": str(feasible.message),
            }
        return {
            "status": "LP_TARGET_FEASIBILITY_FAILURE",
            "feasible": None,
            "solver_status": int(feasible.status),
            "solver_message": str(feasible.message),
        }

    primary_target_vector = np.zeros(design.shape[1], float)
    primary_target_vector[focal_column] = 1.0
    positive_target = target_direction(1.0, primary_target_vector)
    negative_target = target_direction(-1.0, primary_target_vector)
    target_audit_complete = all(
        item["status"] not in {
            "LP_TARGET_FEASIBILITY_FAILURE", "LP_TARGET_CERTIFICATION_FAILURE",
        } for item in (positive_target, negative_target)
    )
    can_move = bool(
        positive_target.get("feasible") is True or negative_target.get("feasible") is True
    ) if target_audit_complete else None
    reported_target_audits: dict[str, Any] = {}
    for label, vector in (additional_target_vectors or {}).items():
        positive = target_direction(1.0, vector)
        negative = target_direction(-1.0, vector)
        complete = all(item["status"] not in {
            "LP_TARGET_FEASIBILITY_FAILURE", "LP_TARGET_CERTIFICATION_FAILURE",
            "INVALID_TARGET_VECTOR",
        } for item in (positive, negative))
        reported_target_audits[label] = {
            "positive_direction": positive,
            "negative_direction": negative,
            "audit_complete": complete,
            "target_can_move": (
                bool(positive.get("feasible") is True or negative.get("feasible") is True)
                if complete else None
            ),
        }
    all_reported_complete = all(
        row["audit_complete"] for row in reported_target_audits.values()
    )
    any_reported_can_move = (
        any(row["target_can_move"] is True for row in reported_target_audits.values())
        if all_reported_complete else None
    )
    if column_labels is None:
        column_labels = [f"column_{index}" for index in range(design.shape[1])]
    nonzero_direction = [
        {"column": column_labels[index], "value": float(value)}
        for index, value in enumerate(result.x)
        if abs(float(value)) > margin_tolerance
    ]
    separation_type = "NONE"
    if separated:
        separation_type = (
            "COMPLETE" if not interior.any() and bool(np.all(strict)) else "QUASI"
        )
    boundary_indices = np.flatnonzero(boundary)
    return {
        "status": "PASS",
        "message": result.message,
        "solver_options": HIGHS_CERTIFIED_OPTIONS,
        "global_primal_certificate": global_certificate,
        "boundary_rows": int(boundary.sum()),
        "interior_rows": int(interior.sum()),
        "maximum_recession_gain": raw_gain,
        "maximum_normalized_recession_gain": normalized_gain,
        "separation_exists": separated,
        "separation_type": separation_type,
        "strictly_separated_boundary_rows": int(strict.sum()),
        "zero_margin_boundary_rows": int((~strict).sum()),
        "strict_zero_young_rows": int(np.sum(strict & zero[boundary])),
        "strict_zero_older_rows": int(np.sum(strict & one[boundary])),
        "strict_boundary_local_indices": boundary_indices[strict].astype(int).tolist(),
        "strict_boundary_margins": margins[strict].astype(float).tolist(),
        "maximum_gain_direction_focal_component": float(result.x[focal_column]),
        "maximum_gain_direction_nonzero": nonzero_direction,
        "positive_focal_direction": positive_target,
        "negative_focal_direction": negative_target,
        "focal_target_direction_audit_complete": target_audit_complete,
        "focal_target_can_move": can_move,
        "reported_target_direction_audits": reported_target_audits,
        "all_reported_targets_direction_audit_complete": all_reported_complete,
        "any_reported_target_can_move": any_reported_can_move,
    }


def resolve_extended_likelihood_face(
    bundle: ModelBundle,
    analysis: dict[str, Any],
    original_treatment_functionals: dict[str, np.ndarray] | None = None,
) -> tuple[np.ndarray, SparseDesign | None, dict[str, Any], list[dict[str, Any]]]:
    """Find the finite face while preserving the focal treatment coordinate.

    Pure nuisance-FE boundary groups are first profiled.  If a remaining
    recession direction is proven unable to move the focal coefficient, rows
    made strict by that direction are on the extended-likelihood boundary and
    are profiled as a face.  The process repeats because either operation can
    expose another nuisance boundary.  A target-moving direction or an
    incomplete LP audit blocks the target rather than silently deleting rows.
    """
    tolerance = float(analysis["boundary_and_separation"]["lp_margin_tolerance"])
    rank_tolerance = float(analysis["tolerances"]["conditioning_rank_relative"])
    active, initial_records = profile_boundary_nuisance(bundle)
    pruning: list[dict[str, Any]] = []
    for row in initial_records:
        pruning.append({**row, "face_iteration": 0, "reason": "pure_nuisance_boundary"})
    trace: list[dict[str, Any]] = []
    maximum_iterations = max(int(np.sum(bundle.total > 0)), 1)
    if original_treatment_functionals is None:
        original_treatment_functionals = {
            f"original_treatment::{index}::{label}": np.eye(
                1, bundle.regressors.shape[1], index,
            ).reshape(-1)
            for index, label in enumerate(bundle.regressor_labels)
        }
    if not original_treatment_functionals:
        raise AuditBlocked("original treatment functional family is empty")
    for label, functional in original_treatment_functionals.items():
        vector = np.asarray(functional, float)
        if (
            not label.startswith("original_treatment::")
            or vector.shape != (bundle.regressors.shape[1],)
            or not np.isfinite(vector).all()
        ):
            raise AuditBlocked("original treatment functional family is invalid")

    for face_iteration in range(1, maximum_iterations + 1):
        if not active.any():
            return active, None, {
                "status": "BLOCKED_EMPTY_FINITE_CORE",
                "iterations": face_iteration - 1,
                "trace": trace,
                "focal_target_finite": False,
            }, pruning
        design = make_sparse_design(bundle, active)
        young = bundle.young[active]
        total = bundle.total[active]
        regressors = bundle.regressors[active]
        geometry = information_diagnostics(
            design, regressors, total * 0.25, bundle.focal_target,
            rank_tolerance,
        )
        if not geometry["focal_target_rank_identified"]:
            return active, design, {
                "status": "BLOCKED_FOCAL_TARGET_RANK_UNIDENTIFIED",
                "iterations": face_iteration,
                "trace": trace,
                "geometric_information": geometry,
                "focal_target_finite": False,
            }, pruning
        if (
            bundle.reported_target_weights and
            geometry["treatment_information_rank"] != geometry["treatment_information_columns"]
        ):
            return active, design, {
                "status": "BLOCKED_REPORTED_EVENT_VECTOR_TREATMENT_RANK_DEFICIENT",
                "iterations": face_iteration,
                "trace": trace,
                "geometric_information": geometry,
                "reported_event_target_count": len(bundle.reported_target_weights),
                "focal_target_finite": False,
            }, pruning
        focal_column = design.nuisance.shape[1] + bundle.focal_target
        treatment_direction_labels = list(original_treatment_functionals)
        additional_targets = {
            label: np.r_[
                np.zeros(design.nuisance.shape[1]),
                np.asarray(original_treatment_functionals[label], float),
            ]
            for label in treatment_direction_labels
        }
        additional_targets.update({
            label: np.r_[
                np.zeros(design.nuisance.shape[1]), np.asarray(weights, float)
            ]
            for label, weights in (bundle.reported_target_weights or {}).items()
        })
        separation = separation_lp(
            design.full, young, total, focal_column, tolerance,
            design.nuisance_column_labels + bundle.regressor_labels,
            additional_target_vectors=additional_targets,
        )
        direction_audits = separation.get(
            "reported_target_direction_audits", {}
        )
        treatment_direction_audits = {
            label: direction_audits.get(label, {})
            for label in treatment_direction_labels
        }
        treatment_direction_complete = all(
            row.get("audit_complete") is True
            for row in treatment_direction_audits.values()
        )
        any_treatment_direction_moves = bool(
            treatment_direction_complete
            and any(
                row.get("target_can_move") is True
                for row in treatment_direction_audits.values()
            )
        )
        separation["treatment_column_direction_audits"] = (
            treatment_direction_audits
        )
        separation[
            "all_treatment_columns_direction_audit_complete"
        ] = treatment_direction_complete
        separation["any_treatment_column_can_move"] = (
            any_treatment_direction_moves
            if treatment_direction_complete else None
        )
        step = {
            "face_iteration": face_iteration,
            "rows_before": int(active.sum()),
            "geometric_information": geometry,
            "separation": separation,
        }
        if separation.get("status") not in {
            "PASS", "NO_BOUNDARY_ROWS_AFTER_PROFILING",
        }:
            trace.append(step)
            return active, design, {
                "status": "BLOCKED_RECESSION_CONE_LP_FAILURE",
                "iterations": face_iteration,
                "trace": trace,
                "geometric_information": geometry,
                "separation": separation,
                "focal_target_finite": False,
            }, pruning
        if not separation.get("separation_exists", False):
            step["rows_profiled"] = 0
            trace.append(step)
            return active, design, {
                "status": "PASS_FINITE_FACE_RESOLVED",
                "iterations": face_iteration,
                "trace": trace,
                "geometric_information": geometry,
                "separation": separation,
                "focal_target_finite": True,
            }, pruning
        if separation.get("focal_target_direction_audit_complete") is not True:
            trace.append(step)
            return active, design, {
                "status": "BLOCKED_INCOMPLETE_FOCAL_DIRECTION_AUDIT",
                "iterations": face_iteration,
                "trace": trace,
                "geometric_information": geometry,
                "separation": separation,
                "focal_target_finite": False,
            }, pruning
        if not treatment_direction_complete:
            trace.append(step)
            return active, design, {
                "status": "BLOCKED_INCOMPLETE_TREATMENT_VECTOR_DIRECTION_AUDIT",
                "iterations": face_iteration,
                "trace": trace,
                "geometric_information": geometry,
                "separation": separation,
                "focal_target_finite": False,
            }, pruning
        if separation.get("all_reported_targets_direction_audit_complete") is not True:
            trace.append(step)
            return active, design, {
                "status": "BLOCKED_INCOMPLETE_REPORTED_EVENT_TARGET_DIRECTION_AUDIT",
                "iterations": face_iteration,
                "trace": trace,
                "geometric_information": geometry,
                "separation": separation,
                "focal_target_finite": False,
            }, pruning
        if separation.get("focal_target_can_move") is True:
            trace.append(step)
            return active, design, {
                "status": "BLOCKED_TARGET_MOVING_RECESSION_DIRECTION",
                "iterations": face_iteration,
                "trace": trace,
                "geometric_information": geometry,
                "separation": separation,
                "focal_target_finite": False,
            }, pruning
        if any_treatment_direction_moves:
            trace.append(step)
            return active, design, {
                "status": "BLOCKED_TREATMENT_VECTOR_MOVING_RECESSION_DIRECTION",
                "iterations": face_iteration,
                "trace": trace,
                "geometric_information": geometry,
                "separation": separation,
                "focal_target_finite": False,
            }, pruning
        if separation.get("any_reported_target_can_move") is True:
            trace.append(step)
            return active, design, {
                "status": "BLOCKED_REPORTED_EVENT_TARGET_MOVING_RECESSION_DIRECTION",
                "iterations": face_iteration,
                "trace": trace,
                "geometric_information": geometry,
                "separation": separation,
                "focal_target_finite": False,
            }, pruning

        local_rows = np.asarray(separation.get("strict_boundary_local_indices", []), int)
        margins = separation.get("strict_boundary_margins", [])
        if local_rows.size == 0:
            trace.append(step)
            return active, design, {
                "status": "BLOCKED_RECESSION_DIRECTION_HAS_NO_CERTIFIED_STRICT_ROWS",
                "iterations": face_iteration,
                "trace": trace,
                "geometric_information": geometry,
                "separation": separation,
                "focal_target_finite": False,
            }, pruning
        global_rows = np.flatnonzero(active)[local_rows]
        for position, row_index in enumerate(global_rows):
            young_value = float(bundle.young[row_index])
            total_value = float(bundle.total[row_index])
            pruning.append({
                "model_id": bundle.model_id,
                "iteration": face_iteration,
                "face_iteration": face_iteration,
                "partition": "general_recession_face",
                "group": f"{bundle.first_labels[row_index]}|{bundle.second_labels[row_index]}",
                "boundary_side": (
                    "zero_young" if young_value == 0.0 else "zero_older"
                ),
                "affected_rows_before_union": 1,
                "young": young_value,
                "older": total_value - young_value,
                "total": total_value,
                "reason": "target_invariant_recession_face",
                "strict_margin": float(margins[position]),
                "row_index": int(row_index),
            })
        active[global_rows] = False
        step["rows_profiled"] = int(len(global_rows))

        # A newly exposed all-young/all-older FE group is another exact face,
        # not an arbitrary sparse-cell rule.  Profile it before the next LP.
        active_after_nuisance, cascade = profile_boundary_nuisance(bundle, active)
        for row in cascade:
            pruning.append({
                **row,
                "face_iteration": face_iteration,
                "reason": "cascading_pure_nuisance_boundary",
            })
        step["cascading_nuisance_records"] = len(cascade)
        step["rows_after"] = int(active_after_nuisance.sum())
        trace.append(step)
        if np.array_equal(active_after_nuisance, active):
            # The explicit strict rows were already removed; equality here is
            # expected when no additional nuisance group cascades.
            active = active_after_nuisance
        else:
            active = active_after_nuisance

    return active, None, {
        "status": "BLOCKED_FACE_RESOLUTION_ITERATION_LIMIT",
        "iterations": maximum_iterations,
        "trace": trace,
        "focal_target_finite": False,
    }, pruning


class BinomialObjective:
    def __init__(
        self,
        design: sparse.csr_matrix,
        young: np.ndarray,
        total: np.ndarray,
        offset: np.ndarray | None = None,
    ):
        self.design = design
        self.young = np.asarray(young, float)
        self.total = np.asarray(total, float)
        self.offset = (
            np.zeros(len(self.young), dtype=float)
            if offset is None else np.asarray(offset, float)
        )
        if self.offset.shape != self.young.shape:
            raise AuditBlocked("binomial objective offset has the wrong shape")
        if not np.isfinite(self.offset).all():
            raise AuditBlocked("binomial objective offset is nonfinite")
        self.scale = max(float(self.total.sum()), 1.0)

    def raw_nll(self, theta: np.ndarray) -> float:
        eta = self.offset + np.asarray(self.design @ theta).reshape(-1)
        return float(np.sum(self.total * np.logaddexp(0.0, eta) - self.young * eta))

    def function(self, theta: np.ndarray) -> float:
        return self.raw_nll(theta) / self.scale

    def gradient(self, theta: np.ndarray) -> np.ndarray:
        eta = self.offset + np.asarray(self.design @ theta).reshape(-1)
        residual = self.total * expit(eta) - self.young
        return np.asarray(self.design.T @ residual).reshape(-1) / self.scale

    def hessp(self, theta: np.ndarray, direction: np.ndarray) -> np.ndarray:
        eta = self.offset + np.asarray(self.design @ theta).reshape(-1)
        probability = expit(eta)
        weight = self.total * probability * (1.0 - probability)
        projection = np.asarray(self.design @ direction).reshape(-1)
        return np.asarray(self.design.T @ (weight * projection)).reshape(-1) / self.scale

    def probability(self, theta: np.ndarray) -> np.ndarray:
        return expit(self.offset + np.asarray(self.design @ theta).reshape(-1))


class IndependentGroupedBinomialEvaluator:
    """Standalone algebraically equivalent evaluator for the A1 reference.

    This implementation deliberately does not call ``BinomialObjective`` or
    its score/Hessian methods.  It works in the original parameter coordinates
    and exposes raw objective, raw score, and sparse observed information for
    the independently initialized damped Newton/IRLS path.
    """

    def __init__(
        self,
        design: sparse.csr_matrix,
        young: np.ndarray,
        total: np.ndarray,
        offset: np.ndarray | None = None,
    ):
        self.design = sparse.csr_matrix(design, dtype=float)
        self.successes = np.array(young, dtype=float, copy=True)
        self.trials = np.array(total, dtype=float, copy=True)
        self.offset = (
            np.zeros(self.design.shape[0], dtype=float)
            if offset is None else np.array(offset, dtype=float, copy=True)
        )
        if (
            self.successes.shape != (self.design.shape[0],)
            or self.trials.shape != self.successes.shape
            or self.offset.shape != self.successes.shape
            or not np.isfinite(self.successes).all()
            or not np.isfinite(self.trials).all()
            or not np.isfinite(self.offset).all()
            or np.any(self.trials < 0.0)
            or np.any(self.successes < 0.0)
            or np.any(self.successes > self.trials)
        ):
            raise AuditBlocked("independent grouped-binomial inputs are invalid")
        self.scale = max(float(np.add.reduce(self.trials)), 1.0)
        self.evaluation_counts = {
            "linear_predictor": 0,
            "probability": 0,
            "raw_objective": 0,
            "raw_score": 0,
            "raw_hessian": 0,
            "raw_hessian_product": 0,
        }

    def linear_predictor(self, theta: np.ndarray) -> np.ndarray:
        self.evaluation_counts["linear_predictor"] += 1
        return self.offset + np.asarray(
            self.design.dot(np.asarray(theta, dtype=float))
        ).reshape(-1)

    def probabilities(self, theta: np.ndarray) -> np.ndarray:
        self.evaluation_counts["probability"] += 1
        return expit(self.linear_predictor(theta))

    def raw_objective(self, theta: np.ndarray) -> float:
        self.evaluation_counts["raw_objective"] += 1
        eta = self.linear_predictor(theta)
        # Deliberately use the outcome/failure decomposition rather than the
        # canonical ``n*softplus(eta) - y*eta`` expression.  The two are
        # algebraically equivalent, but this standalone reference therefore
        # does not merely duplicate the canonical evaluator's loss formula.
        failures = self.trials - self.successes
        contributions = (
            self.successes * np.logaddexp(0.0, -eta)
            + failures * np.logaddexp(0.0, eta)
        )
        return float(np.add.reduce(contributions))

    def objective_per_total(self, theta: np.ndarray) -> float:
        return self.raw_objective(theta) / self.scale

    def raw_score(self, theta: np.ndarray) -> np.ndarray:
        self.evaluation_counts["raw_score"] += 1
        eta = self.linear_predictor(theta)
        success_probability = expit(eta)
        failure_probability = expit(-eta)
        failures = self.trials - self.successes
        residual = (
            failures * success_probability
            - self.successes * failure_probability
        )
        return np.asarray(self.design.transpose().dot(residual)).reshape(-1)

    def raw_hessian(self, theta: np.ndarray) -> sparse.csc_matrix:
        self.evaluation_counts["raw_hessian"] += 1
        eta = self.linear_predictor(theta)
        weights = self.trials * expit(eta) * expit(-eta)
        weighted_design = self.design.multiply(weights[:, None])
        hessian = (self.design.transpose() @ weighted_design).tocsc()
        return ((hessian + hessian.transpose()) * 0.5).tocsc()

    def raw_hessian_product(
        self, theta: np.ndarray, direction: np.ndarray,
    ) -> np.ndarray:
        self.evaluation_counts["raw_hessian_product"] += 1
        eta = self.linear_predictor(theta)
        weights = self.trials * expit(eta) * expit(-eta)
        projected = np.asarray(
            self.design.dot(np.asarray(direction, dtype=float))
        ).reshape(-1)
        return np.asarray(
            self.design.transpose().dot(weights * projected)
        ).reshape(-1)


def independent_evaluator_checks(
    objective: BinomialObjective,
    evaluator: IndependentGroupedBinomialEvaluator,
    theta: np.ndarray,
    gradient_tolerance: float,
    objective_tolerance: float,
    probability_tolerance: float,
) -> dict[str, Any]:
    """Check evaluator equivalence plus directional score/Hessian identities."""
    theta = np.asarray(theta, dtype=float)
    columns = len(theta)
    direction = np.cos(np.arange(columns, dtype=float) + 0.5)
    direction /= max(float(np.max(np.abs(direction), initial=0.0)), 1.0)
    step = float(np.cbrt(np.finfo(float).eps) * (1.0 + np.linalg.norm(theta)))
    primary_probability = objective.probability(theta)
    independent_probability = evaluator.probabilities(theta)
    primary_score = objective.gradient(theta)
    independent_score = evaluator.raw_score(theta) / evaluator.scale
    primary_hessian_product = objective.hessp(theta, direction)
    independent_hessian_product = (
        evaluator.raw_hessian_product(theta, direction) / evaluator.scale
    )
    numeric_directional_score = (
        evaluator.objective_per_total(theta + step * direction)
        - evaluator.objective_per_total(theta - step * direction)
    ) / (2.0 * step)
    analytic_directional_score = float(independent_score @ direction)
    numeric_hessian_product = (
        evaluator.raw_score(theta + step * direction)
        - evaluator.raw_score(theta - step * direction)
    ) / (2.0 * step * evaluator.scale)
    objective_gap = abs(
        objective.function(theta) - evaluator.objective_per_total(theta)
    )
    probability_gap = float(np.max(
        np.abs(primary_probability - independent_probability), initial=0.0,
    ))
    score_gap = float(np.max(
        np.abs(primary_score - independent_score), initial=0.0,
    ))
    hessian_gap = float(np.max(
        np.abs(primary_hessian_product - independent_hessian_product),
        initial=0.0,
    ))
    directional_gap = abs(
        numeric_directional_score - analytic_directional_score
    )
    finite_difference_hessian_gap = float(np.max(
        np.abs(numeric_hessian_product - independent_hessian_product),
        initial=0.0,
    ))
    checks = {
        "objective_equivalence": objective_gap <= objective_tolerance,
        "probability_equivalence": probability_gap <= probability_tolerance,
        "score_equivalence": score_gap <= gradient_tolerance,
        "hessian_product_equivalence": hessian_gap <= gradient_tolerance,
        "directional_derivative": directional_gap <= gradient_tolerance,
        "finite_difference_hessian_product": (
            finite_difference_hessian_gap <= gradient_tolerance
        ),
    }
    return {
        "status": (
            "PASS_INDEPENDENT_EVALUATOR_AND_DERIVATIVE_CHECKS"
            if all(checks.values()) else
            "BLOCKED_INDEPENDENT_EVALUATOR_OR_DERIVATIVE_CHECK"
        ),
        "checks": checks,
        "finite_difference_step": step,
        "objective_per_total_absolute_difference": objective_gap,
        "fitted_probability_max_absolute_difference": probability_gap,
        "score_per_total_max_absolute_difference": score_gap,
        "hessian_product_per_total_max_absolute_difference": hessian_gap,
        "directional_derivative_absolute_difference": directional_gap,
        "finite_difference_hessian_product_max_absolute_difference": (
            finite_difference_hessian_gap
        ),
        "objective_tolerance": objective_tolerance,
        "probability_tolerance": probability_tolerance,
        "gradient_or_derivative_tolerance": gradient_tolerance,
        "direction_definition": "cos(j+0.5) normalized to max absolute one",
    }


def independent_evaluator_preflight(
    objective: BinomialObjective,
    gradient_tolerance: float,
    objective_tolerance: float,
    probability_tolerance: float,
) -> dict[str, Any]:
    """Cross-check both evaluators at deterministic, outcome-blind vectors."""
    columns = objective.design.shape[1]
    coordinate = np.arange(columns, dtype=float) + 1.0
    vectors = {
        "exact_zero": np.zeros(columns, dtype=float),
        "bounded_sine_cosine": (
            0.125 * np.sin(coordinate) + 0.075 * np.cos(2.0 * coordinate)
        ),
    }
    evaluator = IndependentGroupedBinomialEvaluator(
        objective.design, objective.young, objective.total, objective.offset,
    )
    checks = {
        label: independent_evaluator_checks(
            objective, evaluator, theta, gradient_tolerance,
            objective_tolerance, probability_tolerance,
        )
        for label, theta in vectors.items()
    }
    passed = all(
        audit["status"]
        == "PASS_INDEPENDENT_EVALUATOR_AND_DERIVATIVE_CHECKS"
        for audit in checks.values()
    )
    return {
        "status": (
            "PASS_DETERMINISTIC_INDEPENDENT_EVALUATOR_PREFLIGHT"
            if passed else
            "BLOCKED_DETERMINISTIC_INDEPENDENT_EVALUATOR_PREFLIGHT"
        ),
        "vectors_are_outcome_blind": True,
        "vector_definitions": {
            "exact_zero": "theta_j = 0",
            "bounded_sine_cosine": (
                "theta_j = 0.125*sin(j+1)+0.075*cos(2*(j+1))"
            ),
        },
        "checks": checks,
    }


def design_only_diagonal_reparameterization(
    objective: BinomialObjective,
) -> tuple[BinomialObjective, np.ndarray, dict[str, Any]]:
    """Normalize columns using the fixed p=.5 geometric information.

    If ``phi = scale * theta``, then ``X theta = (X / scale) phi``.
    This changes only numerical coordinates; the likelihood, fitted means and
    every original-coordinate target are exactly unchanged.  The scale uses no
    fitted probability or outcome share beyond the already-declared totals.
    """
    geometric_weight = objective.total * 0.25 / objective.scale
    diagonal = np.asarray(
        objective.design.multiply(objective.design).T @ geometric_weight
    ).reshape(-1)
    if (
        diagonal.shape != (objective.design.shape[1],)
        or not np.isfinite(diagonal).all()
        or np.any(diagonal <= 0.0)
    ):
        raise AuditBlocked(
            "design-only diagonal optimizer reparameterization is nonpositive"
        )
    parameter_scale = np.sqrt(diagonal)
    transformed_design = (
        objective.design @ sparse.diags(1.0 / parameter_scale)
    ).tocsr()
    transformed = BinomialObjective(
        transformed_design,
        objective.young,
        objective.total,
        objective.offset,
    )
    scale_payload = "".join(f"{float(value).hex()}\n" for value in parameter_scale)
    audit = {
        "status": "DESIGN_ONLY_P_HALF_DIAGONAL_REPARAMETERIZATION",
        "definition": "sqrt(diag(X' diag(total/4) X) / sum(total))",
        "column_count": int(len(parameter_scale)),
        "parameter_scale_min": float(parameter_scale.min()),
        "parameter_scale_max": float(parameter_scale.max()),
        "parameter_scale_sha256": hashlib.sha256(
            scale_payload.encode("utf-8")
        ).hexdigest(),
        "uses_fitted_probabilities": False,
        "changes_linear_predictor_or_likelihood": False,
    }
    return transformed, parameter_scale, audit


def original_coordinate_score_diagnostics(
    objective: BinomialObjective,
    theta: np.ndarray,
    probability: np.ndarray | None = None,
) -> dict[str, Any]:
    probability = (
        objective.probability(theta)
        if probability is None else np.asarray(probability, float)
    )
    gradient = objective.gradient(theta)
    raw_gradient = gradient * objective.scale
    information_weight = objective.total * probability * (1.0 - probability)
    hessian_diagonal = np.asarray(
        objective.design.multiply(objective.design).T @ information_weight
    ).reshape(-1)
    standardized_score = np.divide(
        np.abs(raw_gradient), np.sqrt(hessian_diagonal),
        out=np.full_like(raw_gradient, np.inf), where=hessian_diagonal > 0,
    )
    coordinate_step = np.divide(
        np.abs(raw_gradient), hessian_diagonal,
        out=np.full_like(raw_gradient, np.inf), where=hessian_diagonal > 0,
    )
    return {
        "raw_gradient": raw_gradient,
        "gradient": gradient,
        "hessian_diagonal": hessian_diagonal,
        "standardized_score": standardized_score,
        "coordinate_step": coordinate_step,
        "raw_gradient_infinity_norm": float(np.max(np.abs(raw_gradient))),
        "gradient_infinity_norm_per_total": float(np.max(np.abs(gradient))),
        "standardized_score_max_abs": float(np.max(standardized_score)),
        "coordinate_newton_step_max_abs": float(np.max(coordinate_step)),
    }


def refined_sparse_linear_solve(
    factor: Any,
    matrix: sparse.csc_matrix,
    rhs: np.ndarray,
    relative_tolerance: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Sparse direct solve with original-system iterative refinement.

    The right-hand-side-relative residual is required to meet the declared
    tolerance except where ordinary floating-point sparse dot products cannot
    represent that threshold.  That numerical floor is computed from the
    standard ``gamma_k`` bound using the maximum row sparsity and the observed
    absolute matrix-vector product; it is not a fitted or scientific tolerance.
    The normwise backward-error requirement is never relaxed.
    """
    rhs = np.asarray(rhs, float)
    matrix_norm = float(
        np.max(np.asarray(np.abs(matrix).sum(axis=1)).reshape(-1))
    )
    solution = np.asarray(factor.solve(rhs), float)
    refinements = 0
    for _ in range(8):
        residual = np.asarray(matrix @ solution).reshape(-1) - rhs
        rhs_norm = float(np.max(np.abs(rhs)))
        solution_norm = float(np.max(np.abs(solution)))
        residual_norm = float(np.max(np.abs(residual)))
        rhs_relative = (
            residual_norm / rhs_norm if rhs_norm > 0.0
            else (0.0 if residual_norm == 0.0 else math.inf)
        )
        denominator = matrix_norm * solution_norm + rhs_norm
        backward = (
            residual_norm / denominator if denominator > 0.0
            else (0.0 if residual_norm == 0.0 else math.inf)
        )
        if rhs_relative <= relative_tolerance and backward <= relative_tolerance:
            break
        correction = np.asarray(factor.solve(-residual), float)
        solution = solution + correction
        refinements += 1
    residual = np.asarray(matrix @ solution).reshape(-1) - rhs
    rhs_norm = float(np.max(np.abs(rhs)))
    solution_norm = float(np.max(np.abs(solution)))
    residual_norm = float(np.max(np.abs(residual)))
    rhs_relative = (
        residual_norm / rhs_norm if rhs_norm > 0.0
        else (0.0 if residual_norm == 0.0 else math.inf)
    )
    denominator = matrix_norm * solution_norm + rhs_norm
    backward = (
        residual_norm / denominator if denominator > 0.0
        else (0.0 if residual_norm == 0.0 else math.inf)
    )
    csr_matrix = matrix.tocsr()
    maximum_row_nonzeros = int(np.max(np.diff(csr_matrix.indptr), initial=0))
    machine_epsilon = float(np.finfo(float).eps)
    gamma_denominator = 1.0 - maximum_row_nonzeros * machine_epsilon
    gamma_k = (
        maximum_row_nonzeros * machine_epsilon / gamma_denominator
        if gamma_denominator > 0.0 else math.inf
    )
    absolute_product_norm = float(np.max(
        np.asarray(abs(csr_matrix) @ np.abs(solution)).reshape(-1),
        initial=0.0,
    ))
    rhs_relative_roundoff_floor = (
        gamma_k * (absolute_product_norm + rhs_norm) / rhs_norm
        if rhs_norm > 0.0 else 0.0
    )
    effective_rhs_relative_tolerance = max(
        relative_tolerance, rhs_relative_roundoff_floor,
    )
    passed = bool(
        np.isfinite(solution).all() and np.isfinite(residual).all()
        and rhs_relative <= effective_rhs_relative_tolerance
        and backward <= relative_tolerance
    )
    return solution, {
        "status": (
            "PASS_REFINED_SPARSE_ORIGINAL_SYSTEM_SOLVE"
            if passed else "BLOCKED_REFINED_SPARSE_ORIGINAL_SYSTEM_SOLVE"
        ),
        "iterative_refinement_steps": refinements,
        "rhs_infinity_norm": rhs_norm,
        "solution_infinity_norm": solution_norm,
        "matrix_infinity_norm": matrix_norm,
        "residual_infinity_norm": residual_norm,
        "rhs_relative_residual": rhs_relative,
        "rhs_relative_roundoff_floor": rhs_relative_roundoff_floor,
        "effective_rhs_relative_tolerance": effective_rhs_relative_tolerance,
        "maximum_row_nonzeros": maximum_row_nonzeros,
        "floating_point_gamma_k": gamma_k,
        "normwise_backward_error": backward,
        "relative_tolerance": relative_tolerance,
        "backward_error_tolerance_relaxed": False,
        "rhs_relative_tolerance_uses_only_declared_or_roundoff_floor": True,
    }


def scaled_original_hessian_direction(
    objective: BinomialObjective,
    theta: np.ndarray,
    information_weight: np.ndarray,
    linear_solve_relative_tolerance: float,
) -> tuple[np.ndarray, dict[str, Any], dict[str, Any]]:
    """Solve ``H d = -g`` in diagonally scaled original coordinates.

    The returned residual is recomputed against the unscaled original system;
    a solver status is never accepted as a certificate.
    """
    weight = np.asarray(information_weight, float)
    if (
        weight.shape != objective.total.shape
        or not np.isfinite(weight).all()
        or np.any(weight <= 0.0)
    ):
        raise AuditBlocked("full-Hessian certificate has invalid information weights")
    raw_gradient = objective.gradient(theta) * objective.scale
    hessian = (
        objective.design.T @ objective.design.multiply(weight[:, None])
    ).tocsc()
    hessian = ((hessian + hessian.T) * 0.5).tocsc()
    diagonal = np.asarray(hessian.diagonal(), float)
    if (
        diagonal.shape != raw_gradient.shape
        or not np.isfinite(diagonal).all()
        or np.any(diagonal <= 0.0)
    ):
        raise AuditBlocked("full-Hessian certificate has nonpositive diagonal")
    root_diagonal = np.sqrt(diagonal)
    inverse_scale = sparse.diags(1.0 / root_diagonal)
    scaled_hessian = (inverse_scale @ hessian @ inverse_scale).tocsc()
    scaled_rhs = -raw_gradient / root_diagonal
    try:
        factor = splu(scaled_hessian)
    except RuntimeError as error:
        raise AuditBlocked("full-Hessian certificate system is singular") from error
    scaled_direction, solve_audit = refined_sparse_linear_solve(
        factor, scaled_hessian, scaled_rhs,
        linear_solve_relative_tolerance,
    )
    direction = np.asarray(scaled_direction, float) / root_diagonal
    residual = np.asarray(hessian @ direction).reshape(-1) + raw_gradient
    standardized_residual = np.abs(residual) / root_diagonal
    descent = float(raw_gradient @ direction)
    decrement_squared = float(-descent)
    return direction, {
        "linear_system": "diagonally_scaled_original_full_Hessian",
        "linear_system_residual_max_abs": float(np.max(np.abs(residual))),
        "linear_system_standardized_residual_max_abs": float(
            np.max(standardized_residual)
        ),
        "scaled_rhs_infinity_norm": solve_audit["rhs_infinity_norm"],
        "scaled_solution_infinity_norm": solve_audit["solution_infinity_norm"],
        "scaled_matrix_infinity_norm": solve_audit["matrix_infinity_norm"],
        "scaled_residual_infinity_norm": solve_audit["residual_infinity_norm"],
        "scaled_rhs_relative_residual": solve_audit["rhs_relative_residual"],
        "normwise_backward_error": solve_audit["normwise_backward_error"],
        "linear_solve_relative_tolerance": linear_solve_relative_tolerance,
        "finite_direction_and_residual": bool(
            np.isfinite(direction).all()
            and solve_audit["status"]
            == "PASS_REFINED_SPARSE_ORIGINAL_SYSTEM_SOLVE"
        ),
        "solve_audit": solve_audit,
        "spectral_lower_bound_used": False,
        "dense_conversion_used": False,
        "linear_solve_residual_pass": bool(
            np.isfinite(direction).all()
            and solve_audit["status"]
            == "PASS_REFINED_SPARSE_ORIGINAL_SYSTEM_SOLVE"
        ),
        "directional_derivative": descent,
        "newton_decrement_squared": decrement_squared,
        "half_newton_decrement_squared": decrement_squared / 2.0,
        "direction_max_abs": float(np.max(np.abs(direction))),
    }, {
        "root_diagonal": root_diagonal,
        "scaled_hessian": scaled_hessian,
        "scaled_rhs": scaled_rhs,
        "scaled_direction": scaled_direction,
        "factor": factor,
    }


def deterministic_decreasing_step(
    objective: BinomialObjective,
    theta: np.ndarray,
    direction: np.ndarray,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Select the largest attained decrease on a fixed dyadic grid.

    Returning the first nonincrease can select a point near the far root of a
    convex line restriction and badly understate the attainable improvement.
    Evaluating the complete machine-scale grid makes that failure impossible.
    """
    base = objective.raw_nll(theta)
    if not math.isfinite(base):
        raise AuditBlocked("candidate raw likelihood is nonfinite")
    candidates: list[tuple[float, int, float, np.ndarray]] = []
    for halvings in range(65):
        step = math.ldexp(1.0, -halvings)
        candidate = np.asarray(theta, float) + step * direction
        value = objective.raw_nll(candidate)
        if math.isfinite(value):
            candidates.append((value, halvings, step, candidate))
    improving = [row for row in candidates if row[0] <= base]
    if improving:
        value, halvings, step, candidate = min(
            improving, key=lambda row: (row[0], row[1]),
        )
        return candidate, {
            "status": "PASS_MAXIMUM_DECREASE_ON_COMPLETE_DYADIC_GRID",
            "step_fraction": step,
            "halvings": halvings,
            "finite_grid_points": len(candidates),
            "evaluated_halvings_inclusive": [0, 64],
            "selection_rule": "minimum raw NLL; fewer halvings breaks exact ties",
            "raw_negative_log_likelihood_before": base,
            "raw_negative_log_likelihood_after": value,
            "actual_raw_negative_log_likelihood_decrease": float(base - value),
        }
    raise AuditBlocked("deterministic full-Hessian direction has no finite decrease")


def fisher_scoring_start(
    objective: BinomialObjective,
    start: np.ndarray,
    focal_column: int,
    standardized_score_tolerance: float,
    linear_solve_relative_tolerance: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Construct the L-BFGS-B-only p=.5 full-Hessian start."""
    direction, solve, _context = scaled_original_hessian_direction(
        objective, start, objective.total * 0.25,
        linear_solve_relative_tolerance,
    )
    if (
        not math.isfinite(solve["newton_decrement_squared"])
        or solve["newton_decrement_squared"] < 0.0
        or solve["linear_system_standardized_residual_max_abs"]
        > standardized_score_tolerance
        or solve["linear_solve_residual_pass"] is not True
    ):
        raise AuditBlocked("p=.5 Fisher-scoring start failed its original-system solve")
    candidate, line_search = deterministic_decreasing_step(
        objective, start, direction,
    )
    return candidate, {
        "status": "PASS_L_BFGS_B_ONLY_P_HALF_FULL_HESSIAN_START",
        "shared_with_other_solver": False,
        "uses_fitted_probabilities": False,
        "solve": solve,
        "line_search": line_search,
        "focal_displacement": float(candidate[focal_column] - start[focal_column]),
        "parameter_displacement_max_abs": float(
            np.max(np.abs(candidate - start))
        ),
    }


def full_hessian_stationarity_certificate(
    objective: BinomialObjective,
    theta: np.ndarray,
    target_functionals: dict[str, np.ndarray],
    standardized_score_tolerance: float,
    target_coefficient_tolerance: float,
    raw_likelihood_tolerance: float,
    linear_solve_relative_tolerance: float,
) -> dict[str, Any]:
    """Certify a solver candidate against joint weak directions.

    The candidate is not replaced by the Newton trial.  The trial is used only
    to measure an actual attainable likelihood decrease and target correction.
    """
    probability = objective.probability(theta)
    information_weight = objective.total * probability * (1.0 - probability)
    direction, solve, context = scaled_original_hessian_direction(
        objective, theta, information_weight,
        linear_solve_relative_tolerance,
    )
    _trial, line_search = deterministic_decreasing_step(
        objective, theta, direction,
    )
    root_diagonal = context["root_diagonal"]
    scaled_hessian = context["scaled_hessian"]
    scaled_rhs = context["scaled_rhs"]
    scaled_direction = context["scaled_direction"]
    factor = context["factor"]
    target_audits: dict[str, dict[str, Any]] = {}
    for label, raw_functional in target_functionals.items():
        functional = np.asarray(raw_functional, float)
        if functional.shape != theta.shape or not np.isfinite(functional).all():
            raise AuditBlocked(
                f"full-Hessian certificate target has invalid shape: {label}"
            )
        scaled_functional = functional / root_diagonal
        adjoint_solution, adjoint_solve = refined_sparse_linear_solve(
            factor, scaled_hessian, scaled_functional,
            linear_solve_relative_tolerance,
        )
        primal_correction = float(scaled_functional @ scaled_direction)
        adjoint_correction = float(adjoint_solution @ scaled_rhs)
        agreement = float(abs(primal_correction - adjoint_correction))
        conservative_correction = float(max(
            abs(primal_correction), abs(adjoint_correction),
        ))
        target_audits[label] = {
            "primal_target_correction": primal_correction,
            "adjoint_target_correction": adjoint_correction,
            "primal_adjoint_absolute_disagreement": agreement,
            "conservative_absolute_target_correction": conservative_correction,
            "target_coefficient_tolerance": target_coefficient_tolerance,
            "adjoint_solve": adjoint_solve,
            "adjoint_solve_pass": bool(
                adjoint_solve["status"]
                == "PASS_REFINED_SPARSE_ORIGINAL_SYSTEM_SOLVE"
            ),
            "primal_adjoint_agreement_pass": bool(
                agreement <= target_coefficient_tolerance
            ),
            "target_correction_pass": bool(
                conservative_correction <= target_coefficient_tolerance
            ),
        }
    corrections = {
        label: audit["primal_target_correction"]
        for label, audit in target_audits.items()
    }
    maximum_nominal_target_correction = max((
        audit["conservative_absolute_target_correction"]
        for audit in target_audits.values()
    ), default=0.0)
    maximum_primal_adjoint_disagreement = max((
        audit["primal_adjoint_absolute_disagreement"]
        for audit in target_audits.values()
    ), default=0.0)
    checks = {
        "finite_nonnegative_newton_decrement": bool(
            math.isfinite(solve["newton_decrement_squared"])
            and solve["newton_decrement_squared"] >= 0.0
        ),
        "original_system_residual": bool(
            solve["linear_solve_residual_pass"] is True
            and
            solve["linear_system_standardized_residual_max_abs"]
            <= standardized_score_tolerance
        ),
        "joint_newton_decrement": bool(
            solve["half_newton_decrement_squared"]
            <= raw_likelihood_tolerance
        ),
        "actual_raw_likelihood_decrease": bool(
            line_search["actual_raw_negative_log_likelihood_decrease"]
            <= raw_likelihood_tolerance
        ),
        "all_declared_target_adjoint_solves": all(
            audit["adjoint_solve_pass"]
            for audit in target_audits.values()
        ),
        "all_declared_target_primal_adjoint_agreements": all(
            audit["primal_adjoint_agreement_pass"]
            for audit in target_audits.values()
        ),
        "all_declared_target_corrections": all(
            audit["target_correction_pass"]
            for audit in target_audits.values()
        ),
    }
    passed = all(checks.values())
    return {
        "status": (
            "PASS_ORIGINAL_FULL_HESSIAN_WEAK_DIRECTION_CERTIFICATE"
            if passed else
            "BLOCKED_ORIGINAL_FULL_HESSIAN_WEAK_DIRECTION_CERTIFICATE"
        ),
        "candidate_left_untouched": True,
        "solve": solve,
        "line_search": line_search,
        "target_newton_corrections": corrections,
        "target_primal_adjoint_audits": target_audits,
        "maximum_absolute_target_newton_correction": (
            maximum_nominal_target_correction
        ),
        "maximum_primal_adjoint_absolute_disagreement": (
            maximum_primal_adjoint_disagreement
        ),
        "newton_decrement_squared": solve["newton_decrement_squared"],
        "half_newton_decrement_squared": solve[
            "half_newton_decrement_squared"
        ],
        "certificate_method": (
            "sparse_primal_newton_plus_declared_target_adjoint_solves_"
            "with_original_system_residuals"
        ),
        "spectral_lower_bound_used": False,
        "dense_conversion_used": False,
        "checks": checks,
    }


def fit_independent_sparse_newton(
    objective: BinomialObjective,
    start: np.ndarray,
    max_iterations: int,
    gradient_tolerance: float,
    standardized_score_tolerance: float,
    focal_column: int,
    target_functionals: dict[str, np.ndarray],
    target_coefficient_tolerance: float,
    raw_likelihood_tolerance: float,
    linear_solve_relative_tolerance: float,
    objective_equivalence_tolerance: float,
    probability_equivalence_tolerance: float,
    path_role: str,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Standalone damped sparse Newton/IRLS reference or trust polish.

    The Newton algebra, sparse Hessian construction, solve, and line search are
    coded independently of ``BinomialObjective`` and ``fit_exact_solver``.
    It returns before canonical cross-evaluation; the caller applies the same
    unchanged external certificate to both reference and trust-path candidates.
    """
    evaluator = IndependentGroupedBinomialEvaluator(
        objective.design, objective.young, objective.total, objective.offset,
    )
    line_search_candidate_evaluations = 0
    newton_iterations_evaluated = 0
    trajectory: list[dict[str, Any]] = []
    last_metrics: dict[str, Any] = {}

    def failure(code: str, message: str) -> IndependentNewtonFailure:
        return IndependentNewtonFailure(code, message, {
            **evaluator.evaluation_counts,
            "line_search_candidate_objective": (
                line_search_candidate_evaluations
            ),
            "newton_iterations_evaluated": newton_iterations_evaluated,
        }, trajectory, last_metrics)

    theta = np.array(start, dtype=float, copy=True)
    if theta.shape != (objective.design.shape[1],) or not np.isfinite(theta).all():
        raise failure(
            "A1_NEWTON_INVALID_START", "independent Newton start is invalid",
        )
    if (
        path_role == "standalone_zero_reference"
        and not np.array_equal(theta, np.zeros_like(theta))
    ):
        raise failure(
            "A1_NEWTON_NONZERO_REFERENCE_START",
            "standalone Newton reference must start at exact zero",
        )
    internal_certificate: dict[str, Any] = {
        "status": "BLOCKED_INDEPENDENT_NEWTON_CERTIFICATE_NOT_EVALUATED",
    }
    termination_code = "A1_NEWTON_ITERATION_LIMIT"
    termination_message = (
        "iteration budget exhausted without the complete internal certificate"
    )
    for iteration in range(max_iterations + 1):
        newton_iterations_evaluated += 1
        probability = evaluator.probabilities(theta)
        raw_score = evaluator.raw_score(theta)
        hessian = evaluator.raw_hessian(theta)
        raw_before = evaluator.raw_objective(theta)
        last_metrics = {
            "iteration_zero_based": iteration,
            "parameter_max_abs": float(np.max(np.abs(theta), initial=0.0)),
            "focal_target": float(theta[focal_column]),
            "raw_negative_log_likelihood": raw_before,
            "objective_per_total": raw_before / evaluator.scale,
            "raw_score_max_abs": float(np.max(
                np.abs(raw_score), initial=0.0,
            )),
        }
        diagonal = np.asarray(hessian.diagonal(), dtype=float)
        if (
            diagonal.shape != theta.shape
            or not np.isfinite(diagonal).all()
            or np.any(diagonal <= 0.0)
        ):
            raise failure(
                "A1_NEWTON_INVALID_HESSIAN_DIAGONAL",
                "independent Newton Hessian diagonal is invalid",
            )
        root_diagonal = np.sqrt(diagonal)
        inverse_scale = sparse.diags(1.0 / root_diagonal)
        scaled_hessian = (inverse_scale @ hessian @ inverse_scale).tocsc()
        scaled_rhs = -raw_score / root_diagonal
        try:
            factor = splu(scaled_hessian)
            scaled_direction = np.asarray(
                factor.solve(scaled_rhs), dtype=float,
            )
        except (RuntimeError, ValueError) as error:
            raise failure(
                "A1_NEWTON_SINGULAR_HESSIAN",
                "independent Newton sparse Hessian is singular",
            ) from error
        direction = scaled_direction / root_diagonal
        residual = np.asarray(
            scaled_hessian @ scaled_direction
        ).reshape(-1) - scaled_rhs
        matrix_norm = float(np.max(np.asarray(
            np.abs(scaled_hessian).sum(axis=1)
        ).reshape(-1), initial=0.0))
        residual_norm = float(np.max(np.abs(residual), initial=0.0))
        rhs_norm = float(np.max(np.abs(scaled_rhs), initial=0.0))
        solution_norm = float(np.max(np.abs(scaled_direction), initial=0.0))
        denominator = matrix_norm * solution_norm + rhs_norm
        backward_error = (
            residual_norm / denominator if denominator > 0.0
            else (0.0 if residual_norm == 0.0 else math.inf)
        )
        if (
            not np.isfinite(direction).all()
            or backward_error > linear_solve_relative_tolerance
            or (
                float(np.max(np.abs(raw_score), initial=0.0)) > 0.0
                and float(raw_score @ direction) >= 0.0
            )
        ):
            raise failure(
                "A1_NEWTON_INVALID_DIRECTION",
                "independent Newton direction failed sparse-solve or descent checks",
            )

        candidates: list[tuple[float, int, float, np.ndarray]] = []
        for halvings in range(65):
            fraction = math.ldexp(1.0, -halvings)
            candidate = theta + fraction * direction
            value = evaluator.raw_objective(candidate)
            line_search_candidate_evaluations += 1
            if math.isfinite(value) and value <= raw_before:
                candidates.append((value, halvings, fraction, candidate))
        if not candidates:
            raise failure(
                "A1_NEWTON_LINE_SEARCH_FAILURE",
                "independent Newton line search found no nonincrease",
            )
        raw_after, halvings, fraction, candidate = min(
            candidates, key=lambda row: (row[0], row[1]),
        )
        gradient_max = float(
            np.max(np.abs(raw_score), initial=0.0) / evaluator.scale
        )
        standardized_max = float(np.max(
            np.abs(raw_score) / root_diagonal, initial=0.0,
        ))
        coordinate_step_max = float(np.max(
            np.abs(raw_score) / diagonal, initial=0.0,
        ))
        decrement_squared = float(max(0.0, -raw_score @ direction))
        target_corrections = {
            label: float(np.asarray(functional, float) @ direction)
            for label, functional in target_functionals.items()
        }
        maximum_target_correction = max(
            (abs(value) for value in target_corrections.values()), default=0.0,
        )
        last_metrics.update({
            "scaled_solve_normwise_backward_error": backward_error,
            "newton_decrement_squared": decrement_squared,
            "target_newton_corrections": target_corrections,
            "maximum_absolute_target_newton_correction": (
                maximum_target_correction
            ),
            "selected_line_search_fraction": fraction,
            "selected_line_search_halvings": halvings,
            "candidate_raw_negative_log_likelihood": raw_after,
        })
        internal_checks = {
            "gradient_per_total": gradient_max <= gradient_tolerance,
            "standardized_score": (
                standardized_max <= standardized_score_tolerance
            ),
            "sparse_solve_backward_error": (
                backward_error <= linear_solve_relative_tolerance
            ),
            "half_newton_decrement": (
                decrement_squared / 2.0 <= raw_likelihood_tolerance
            ),
            "actual_raw_likelihood_decrease": (
                raw_before - raw_after <= raw_likelihood_tolerance
            ),
            "all_declared_target_corrections": (
                maximum_target_correction <= target_coefficient_tolerance
            ),
        }
        internal_certificate = {
            "status": (
                "PASS_INDEPENDENT_NEWTON_INTERNAL_CERTIFICATE"
                if all(internal_checks.values()) else
                "BLOCKED_INDEPENDENT_NEWTON_INTERNAL_CERTIFICATE"
            ),
            "checks": internal_checks,
            "gradient_infinity_norm_per_total": gradient_max,
            "standardized_score_max_abs": standardized_max,
            "coordinate_newton_step_max_abs": coordinate_step_max,
            "scaled_solve_normwise_backward_error": backward_error,
            "newton_decrement_squared": decrement_squared,
            "actual_raw_negative_log_likelihood_decrease": (
                raw_before - raw_after
            ),
            "target_newton_corrections": target_corrections,
            "maximum_absolute_target_newton_correction": (
                maximum_target_correction
            ),
        }
        if all(internal_checks.values()):
            termination_code = "A1_NEWTON_INTERNAL_CERTIFICATE_PASS"
            termination_message = (
                "complete standalone Newton internal certificate passed"
            )
            break
        if iteration == max_iterations:
            break
        change = candidate - theta
        trajectory.append({
            "iteration": iteration + 1,
            "path_role": path_role,
            "objective_per_total_before": raw_before / evaluator.scale,
            "objective_per_total": raw_after / evaluator.scale,
            "raw_negative_log_likelihood": raw_after,
            "raw_negative_log_likelihood_decrease": raw_before - raw_after,
            "gradient_infinity_norm_per_total_before": float(
                np.max(np.abs(raw_score), initial=0.0) / evaluator.scale
            ),
            "newton_direction_max_abs": float(
                np.max(np.abs(direction), initial=0.0)
            ),
            "parameter_change_max_abs": float(
                np.max(np.abs(change), initial=0.0)
            ),
            "focal_target": float(candidate[focal_column]),
            "focal_target_change": float(change[focal_column]),
            "dyadic_step_fraction": fraction,
            "dyadic_halvings": halvings,
            "scaled_solve_normwise_backward_error": backward_error,
        })
        theta = np.asarray(candidate, dtype=float)

    probability = evaluator.probabilities(theta)
    final_raw_score = evaluator.raw_score(theta)
    final_hessian_diagonal = np.asarray(
        evaluator.raw_hessian(theta).diagonal(), float,
    )
    final_gradient_max = float(
        np.max(np.abs(final_raw_score), initial=0.0) / evaluator.scale
    )
    final_standardized_max = float(np.max(
        np.divide(
            np.abs(final_raw_score), np.sqrt(final_hessian_diagonal),
            out=np.full_like(final_raw_score, np.inf),
            where=final_hessian_diagonal > 0.0,
        ), initial=0.0,
    ))
    final_coordinate_step = float(np.max(
        np.divide(
            np.abs(final_raw_score), final_hessian_diagonal,
            out=np.full_like(final_raw_score, np.inf),
            where=final_hessian_diagonal > 0.0,
        ), initial=0.0,
    ))
    internally_valid = bool(
        np.isfinite(theta).all() and np.isfinite(probability).all()
        and internal_certificate["status"]
        == "PASS_INDEPENDENT_NEWTON_INTERNAL_CERTIFICATE"
    )
    final_raw_objective = evaluator.raw_objective(theta)
    evaluation_counts = {
        **evaluator.evaluation_counts,
        "line_search_candidate_objective": (
            line_search_candidate_evaluations
        ),
        "newton_iterations_evaluated": newton_iterations_evaluated,
    }
    diagnostics = {
        "method": "independent-damped-sparse-newton-irls",
        "optimizer_options": {
            "max_iterations": max_iterations,
            "dyadic_line_search_candidate_count_per_iteration": 65,
            "line_search_selection": (
                "minimum finite nonincreasing objective; ties by fewer halvings"
            ),
            "gradient_tolerance": gradient_tolerance,
            "standardized_score_tolerance": standardized_score_tolerance,
            "target_coefficient_tolerance": target_coefficient_tolerance,
            "raw_likelihood_tolerance": raw_likelihood_tolerance,
            "linear_solve_relative_tolerance": (
                linear_solve_relative_tolerance
            ),
        },
        "path_role": path_role,
        "independent_zero_start": bool(np.array_equal(
            np.asarray(start, float), np.zeros_like(theta)
        )),
        "uses_scipy_minimize": False,
        "scipy_success": None,
        "scipy_status": None,
        "scipy_status_is_not_acceptance_evidence": True,
        "message": termination_message,
        "implementation_owned_termination_code": termination_code,
        "implementation_owned_termination_message": termination_message,
        "implementation_owned_termination_namespace": (
            "YAX_A1_INDEPENDENT_NEWTON"
        ),
        "iterations": len(trajectory),
        "newton_iterations_evaluated": newton_iterations_evaluated,
        "function_evaluations": evaluation_counts["raw_objective"],
        "gradient_evaluations": evaluation_counts["raw_score"],
        "hessian_evaluations": evaluation_counts["raw_hessian"],
        "line_search_candidate_evaluations": (
            line_search_candidate_evaluations
        ),
        "independent_evaluation_counts": evaluation_counts,
        "last_iteration_metrics": last_metrics,
        "objective_per_total": final_raw_objective / evaluator.scale,
        "raw_negative_log_likelihood": final_raw_objective,
        "raw_gradient_infinity_norm": float(np.max(
            np.abs(final_raw_score), initial=0.0,
        )),
        "gradient_infinity_norm_per_total": final_gradient_max,
        "standardized_score_max_abs": final_standardized_max,
        "coordinate_newton_step_max_abs": final_coordinate_step,
        "transformed_gradient_infinity_norm": None,
        "internal_transformed_gradient_tolerance": None,
        "optimizer_reparameterization": {
            "status": "NOT_USED_INDEPENDENT_ORIGINAL_COORDINATE_NEWTON",
        },
        "optimizer_reparameterization_status": (
            "NOT_USED_INDEPENDENT_ORIGINAL_COORDINATE_NEWTON"
        ),
        "optimizer_parameter_scale_min": None,
        "optimizer_parameter_scale_max": None,
        "optimizer_parameter_scale_sha256": None,
        "optimizer_start": {
            "status": (
                "EXACT_ZERO_INDEPENDENT_REFERENCE_START"
                if path_role == "standalone_zero_reference" else
                "TRUST_CANDIDATE_CONDITIONAL_POLISH_START"
            ),
        },
        "optimizer_start_original_coordinates": np.asarray(
            start, float,
        ).tolist(),
        "optimizer_start_original_coordinates_sha256": hashlib.sha256(
            np.ascontiguousarray(start, dtype="<f8").tobytes()
        ).hexdigest(),
        "independent_internal_stationarity_certificate": internal_certificate,
        "full_hessian_stationarity_certificate": {
            "status": "PENDING_UNCHANGED_EXTERNAL_CERTIFICATE",
            "candidate_left_untouched": True,
        },
        "parameter_max_abs": float(np.max(np.abs(theta), initial=0.0)),
        "focal_target": float(theta[focal_column]),
        "probability_exact_zero": int(np.sum(probability == 0.0)),
        "probability_exact_one": int(np.sum(probability == 1.0)),
        "probability_at_or_below_1e_10": int(np.sum(probability <= 1e-10)),
        "probability_at_or_above_1_minus_1e_10": int(
            np.sum(probability >= 1.0 - 1e-10)
        ),
        "zero_information_weight_rows": int(np.sum(
            evaluator.trials * probability * (1.0 - probability) == 0.0
        )),
        "independent_internal_numerically_valid": internally_valid,
        "numerically_valid": False,
        "acceptance_source": "PENDING_UNCHANGED_EXTERNAL_CERTIFICATE",
        "cross_evaluation_tolerances_reserved_for_external_audit": {
            "objective": objective_equivalence_tolerance,
            "probability": probability_equivalence_tolerance,
            "gradient": gradient_tolerance,
        },
    }
    return diagnostics, theta, probability, trajectory


def externally_certify_independent_output(
    objective: BinomialObjective,
    output: tuple[
        dict[str, Any], np.ndarray, np.ndarray, list[dict[str, Any]]
    ],
    target_functionals: dict[str, np.ndarray],
    gradient_tolerance: float,
    standardized_score_tolerance: float,
    target_coefficient_tolerance: float,
    raw_likelihood_tolerance: float,
    linear_solve_relative_tolerance: float,
    objective_equivalence_tolerance: float,
    probability_equivalence_tolerance: float,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, list[dict[str, Any]]]:
    """Apply unchanged canonical checks only after the independent path ends."""
    diagnostics, theta, probability, trajectory = output
    evaluator = IndependentGroupedBinomialEvaluator(
        objective.design, objective.young, objective.total, objective.offset,
    )
    cross_evaluation = independent_evaluator_checks(
        objective, evaluator, theta, gradient_tolerance,
        objective_equivalence_tolerance, probability_equivalence_tolerance,
    )
    canonical_score = original_coordinate_score_diagnostics(
        objective, theta, objective.probability(theta),
    )
    try:
        stationarity = full_hessian_stationarity_certificate(
            objective, theta, target_functionals,
            standardized_score_tolerance, target_coefficient_tolerance,
            raw_likelihood_tolerance, linear_solve_relative_tolerance,
        )
    except AuditBlocked as error:
        stationarity = {
            "status": "BLOCKED_ORIGINAL_FULL_HESSIAN_CERTIFICATE_EXCEPTION",
            "candidate_left_untouched": True,
            "error_type": type(error).__name__, "message": str(error),
        }
    valid = bool(
        diagnostics["independent_internal_numerically_valid"] is True
        and canonical_score["gradient_infinity_norm_per_total"]
        <= gradient_tolerance
        and canonical_score["standardized_score_max_abs"]
        <= standardized_score_tolerance
        and stationarity["status"]
        == "PASS_ORIGINAL_FULL_HESSIAN_WEAK_DIRECTION_CERTIFICATE"
        and cross_evaluation["status"]
        == "PASS_INDEPENDENT_EVALUATOR_AND_DERIVATIVE_CHECKS"
    )
    certified = {
        **diagnostics,
        "cross_evaluation_under_canonical_and_independent_implementations": (
            cross_evaluation
        ),
        "independent_evaluator_final_checks": cross_evaluation,
        "canonical_external_score": canonical_score,
        "full_hessian_stationarity_certificate": stationarity,
        "numerically_valid": valid,
        "acceptance_source": (
            "ORIGINAL_COORDINATE_DECLARED_KKT_AND_FULL_HESSIAN_CERTIFICATE"
            if valid else "BLOCKED_ORIGINAL_COORDINATE_DECLARED_KKT"
        ),
    }
    return certified, theta, probability, trajectory


def fit_exact_solver(
    objective: BinomialObjective,
    method: str,
    start: np.ndarray,
    max_iterations: int,
    gradient_tolerance: float,
    standardized_score_tolerance: float,
    focal_column: int,
    target_functionals: dict[str, np.ndarray],
    target_coefficient_tolerance: float,
    raw_likelihood_tolerance: float,
    use_fisher_scoring_start: bool,
    linear_solve_relative_tolerance: float,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, list[dict[str, Any]]]:
    transformed, parameter_scale, reparameterization = (
        design_only_diagonal_reparameterization(objective)
    )
    trajectory: list[dict[str, Any]] = []
    previous: np.ndarray | None = None

    def callback(phi: np.ndarray) -> None:
        nonlocal previous
        theta = np.asarray(phi, float) / parameter_scale
        gradient = objective.gradient(theta)
        change = None if previous is None else theta - previous
        trajectory.append({
            "iteration": len(trajectory) + 1,
            "objective_per_total": objective.function(theta),
            "raw_negative_log_likelihood": objective.raw_nll(theta),
            "gradient_infinity_norm_per_total": float(np.max(np.abs(gradient))),
            "parameter_l2_norm": float(np.linalg.norm(theta)),
            "parameter_max_abs": float(np.max(np.abs(theta))),
            "parameter_change_l2": None if change is None else float(np.linalg.norm(change)),
            "parameter_change_max_abs": None if change is None else float(np.max(np.abs(change))),
            "focal_target": float(theta[focal_column]),
            "focal_target_change": None if change is None else float(change[focal_column]),
        })
        previous = np.asarray(theta, float).copy()

    options: dict[str, Any]
    # Disable the optimizers' coordinatewise gradient shortcut.  Acceptance is
    # determined below in original coordinates, including the full-Hessian
    # weak-direction certificate.  A positive internal gtol can stop at zero
    # in a nearly collinear but rank-identified target direction.
    internal_gtol = 0.0
    kwargs: dict[str, Any] = {
        "fun": transformed.function, "jac": transformed.gradient,
    }
    if method == "L-BFGS-B":
        options = {
            "maxiter": max_iterations, "maxls": 50,
            "gtol": internal_gtol, "ftol": 0.0,
            "maxcor": 20,
        }
    elif method == "trust-ncg":
        kwargs["hessp"] = transformed.hessp
        options = {"maxiter": max_iterations, "gtol": internal_gtol}
    else:
        raise ValueError(method)
    optimizer_start = np.asarray(start, float)
    if use_fisher_scoring_start:
        if method != "L-BFGS-B":
            raise AuditBlocked("p=.5 Fisher start is authorized only for L-BFGS-B")
        optimizer_start, start_audit = fisher_scoring_start(
            objective, optimizer_start, focal_column,
            standardized_score_tolerance,
            linear_solve_relative_tolerance,
        )
    else:
        start_audit = {
            "status": "DECLARED_ZERO_OR_CALLER_START_UNCHANGED",
            "shared_with_other_solver": False,
        }
    result = minimize(
        x0=optimizer_start * parameter_scale,
        method=method, callback=callback,
        options=options, **kwargs,
    )
    phi = np.asarray(result.x, float)
    theta = phi / parameter_scale
    probability = objective.probability(theta)
    score = original_coordinate_score_diagnostics(objective, theta, probability)
    try:
        stationarity = full_hessian_stationarity_certificate(
            objective, theta, target_functionals,
            standardized_score_tolerance, target_coefficient_tolerance,
            raw_likelihood_tolerance,
            linear_solve_relative_tolerance,
        )
    except AuditBlocked as error:
        stationarity = {
            "status": "BLOCKED_ORIGINAL_FULL_HESSIAN_CERTIFICATE_EXCEPTION",
            "candidate_left_untouched": True,
            "error_type": type(error).__name__,
            "message": str(error),
        }
    if not trajectory or trajectory[-1]["iteration"] != int(getattr(result, "nit", -1)):
        callback(phi)
    diagnostics = {
        "method": method,
        "optimizer_options": options,
        "optimizer_start_original_coordinates": optimizer_start.tolist(),
        "optimizer_start_original_coordinates_sha256": hashlib.sha256(
            np.ascontiguousarray(optimizer_start, dtype="<f8").tobytes()
        ).hexdigest(),
        "optimizer_start_transformed_coordinates_sha256": hashlib.sha256(
            np.ascontiguousarray(
                optimizer_start * parameter_scale, dtype="<f8",
            ).tobytes()
        ).hexdigest(),
        "scipy_success": bool(result.success),
        "scipy_status": int(result.status),
        "message": str(result.message),
        "iterations": int(getattr(result, "nit", 0)),
        "function_evaluations": int(getattr(result, "nfev", 0)),
        "gradient_evaluations": int(getattr(result, "njev", 0)),
        "objective_per_total": objective.function(theta),
        "raw_negative_log_likelihood": objective.raw_nll(theta),
        "raw_gradient_infinity_norm": score["raw_gradient_infinity_norm"],
        "gradient_infinity_norm_per_total": score[
            "gradient_infinity_norm_per_total"
        ],
        "standardized_score_max_abs": score["standardized_score_max_abs"],
        "coordinate_newton_step_max_abs": score[
            "coordinate_newton_step_max_abs"
        ],
        "transformed_gradient_infinity_norm": float(np.max(np.abs(
            transformed.gradient(phi)
        ))),
        "internal_transformed_gradient_tolerance": float(internal_gtol),
        "optimizer_reparameterization": reparameterization,
        "optimizer_reparameterization_status": reparameterization["status"],
        "optimizer_parameter_scale_min": reparameterization[
            "parameter_scale_min"
        ],
        "optimizer_parameter_scale_max": reparameterization[
            "parameter_scale_max"
        ],
        "optimizer_parameter_scale_sha256": reparameterization[
            "parameter_scale_sha256"
        ],
        "optimizer_start": start_audit,
        "full_hessian_stationarity_certificate": stationarity,
        "parameter_max_abs": float(np.max(np.abs(theta))),
        "focal_target": float(theta[focal_column]),
        "probability_exact_zero": int(np.sum(probability == 0.0)),
        "probability_exact_one": int(np.sum(probability == 1.0)),
        "probability_at_or_below_1e_10": int(np.sum(probability <= 1e-10)),
        "probability_at_or_above_1_minus_1e_10": int(np.sum(probability >= 1.0 - 1e-10)),
        "zero_information_weight_rows": int(np.sum(
            objective.total * probability * (1.0 - probability) == 0.0
        )),
    }
    diagnostics["numerically_valid"] = bool(
        np.isfinite(theta).all() and np.isfinite(probability).all() and
        diagnostics["gradient_infinity_norm_per_total"] <= gradient_tolerance and
        diagnostics["standardized_score_max_abs"] <= standardized_score_tolerance and
        stationarity["status"]
        == "PASS_ORIGINAL_FULL_HESSIAN_WEAK_DIRECTION_CERTIFICATE"
    )
    diagnostics["acceptance_source"] = (
        "ORIGINAL_COORDINATE_DECLARED_KKT_AND_FULL_HESSIAN_CERTIFICATE"
        if diagnostics["numerically_valid"] else
        "BLOCKED_ORIGINAL_COORDINATE_DECLARED_KKT"
    )
    diagnostics["scipy_status_is_not_acceptance_evidence"] = True
    return diagnostics, theta, probability, trajectory


def compare_solvers(
    left: dict[str, Any], left_theta: np.ndarray, left_probability: np.ndarray,
    right: dict[str, Any], right_theta: np.ndarray, right_probability: np.ndarray,
    nuisance_columns: int, focal_target: int, tolerances: dict[str, Any],
    reported_target_weights: dict[str, np.ndarray] | None = None,
    row_identifiers: list[dict[str, Any]] | None = None,
    treatment_labels: list[str] | None = None,
) -> dict[str, Any]:
    if (
        left.get("method") != "L-BFGS-B"
        or right.get("method") != "trust-ncg"
    ):
        raise AuditBlocked(
            "solver comparison requires the declared independent algorithm pair"
        )
    beta_left = left_theta[nuisance_columns:]
    beta_right = right_theta[nuisance_columns:]
    difference = left_probability - right_probability
    argmax = int(np.argmax(np.abs(difference)))
    if row_identifiers is not None and len(row_identifiers) != len(difference):
        raise AuditBlocked("solver-comparison row identifiers have the wrong length")
    argmax_record = {
        "row_position_zero_based": argmax,
        "left_fitted_probability": float(left_probability[argmax]),
        "right_fitted_probability": float(right_probability[argmax]),
        "signed_difference_left_minus_right": float(difference[argmax]),
        "absolute_difference": float(abs(difference[argmax])),
    }
    if row_identifiers is not None:
        argmax_record["row_identifiers"] = row_identifiers[argmax]
    result = {
        "declared_independent_algorithm_pair": True,
        "left_solver": left["method"],
        "right_solver": right["method"],
        "left_valid": left["numerically_valid"],
        "right_valid": right["numerically_valid"],
        "focal_target_left": float(beta_left[focal_target]),
        "focal_target_right": float(beta_right[focal_target]),
        "focal_target_absolute_difference": float(abs(beta_left[focal_target] - beta_right[focal_target])),
        "all_slope_max_abs_difference": float(np.max(np.abs(beta_left - beta_right))),
        "fitted_probability_max_abs_difference": float(np.max(np.abs(difference))),
        "fitted_probability_max_abs_difference_location": argmax_record,
        "fitted_probability_rmse": float(np.sqrt(np.mean(np.square(difference)))),
        "objective_difference_per_total": float(abs(
            left["objective_per_total"] - right["objective_per_total"]
        )),
        "raw_negative_log_likelihood_difference": float(abs(
            left["raw_negative_log_likelihood"] -
            right["raw_negative_log_likelihood"]
        )),
    }
    reported_differences: dict[str, float] = {}
    for label, raw_weights in (reported_target_weights or {}).items():
        weights = np.asarray(raw_weights, float)
        if weights.shape != beta_left.shape:
            raise AuditBlocked(f"reported target has wrong solver-comparison shape: {label}")
        reported_differences[label] = float(
            abs(weights @ beta_left - weights @ beta_right)
        )
    reported_max = max(reported_differences.values(), default=0.0)
    if treatment_labels is None:
        treatment_labels = [
            f"treatment_column_{index}" for index in range(len(beta_left))
        ]
    if len(treatment_labels) != len(beta_left):
        raise AuditBlocked(
            "treatment labels have wrong historical solver-comparison length"
        )
    complete_treatment_differences = {
        label: float(abs(beta_left[index] - beta_right[index]))
        for index, label in enumerate(treatment_labels)
    }
    result.update({
        "reported_target_absolute_differences": reported_differences,
        "reported_target_max_absolute_difference": float(reported_max),
        "reported_target_comparison_pass": bool(
            reported_max <= tolerances["target_coefficient_absolute_difference"]
        ),
        "complete_identified_treatment_vector_absolute_differences": (
            complete_treatment_differences
        ),
        "complete_identified_treatment_vector_count": len(
            complete_treatment_differences
        ),
        "complete_identified_treatment_vector_max_absolute_difference": max(
            complete_treatment_differences.values(), default=0.0,
        ),
    })
    result["comparison_pass"] = bool(
        left["numerically_valid"] and right["numerically_valid"] and
        result["focal_target_absolute_difference"] <= tolerances["target_coefficient_absolute_difference"] and
        result["reported_target_comparison_pass"] and
        result["fitted_probability_max_abs_difference"] <= tolerances["fitted_probability_max_abs_difference"] and
        result["objective_difference_per_total"] <= tolerances["objective_difference_per_total"]
    )
    return result


def target_vector(
    theta: np.ndarray,
    target_functionals: dict[str, np.ndarray],
) -> dict[str, float]:
    return {
        label: float(np.asarray(functional, float) @ theta)
        for label, functional in target_functionals.items()
    }


def audit_lbfgsb_diagnostic_contradictions(
    objective: BinomialObjective,
    lbfgsb_output: tuple[
        dict[str, Any], np.ndarray, np.ndarray, list[dict[str, Any]]
    ] | None,
    trust_path: tuple[
        dict[str, Any], np.ndarray, np.ndarray, list[dict[str, Any]]
    ],
    reference: tuple[
        dict[str, Any], np.ndarray, np.ndarray, list[dict[str, Any]]
    ],
    target_functionals: dict[str, np.ndarray],
    tolerances: dict[str, Any],
    standardized_score_tolerance: float,
    unavailable_failure: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Let a nonessential L-BFGS-B diagnostic falsify, never certify, A1.

    A visibly unfinished diagnostic is not required to agree in coefficients.
    It blocks only if it exposes a lower objective, if the two evaluator
    implementations disagree at its candidate, or if a candidate satisfying
    the unchanged stationarity requirements nevertheless disagrees on a
    declared target.  Thus failure to converge is not elevated into evidence,
    while an actual contradiction cannot be ignored.
    """
    if lbfgsb_output is None:
        return {
            "status": "BLOCKED_LBFGSB_DIAGNOSTIC_NOT_RUN_OR_REPORTED",
            "available": False,
            "binding_pass": False,
            "contradiction_detected": None,
            "unavailable_failure": unavailable_failure,
            "interpretation": (
                "L-BFGS-B need not converge, but the predeclared diagnostic "
                "must be executed and reported for every model"
            ),
        }
    diagnostic, theta, _probability, _trajectory = lbfgsb_output
    _trust_diagnostic, trust_theta, _trust_probability, _ = trust_path
    reference_diagnostic, reference_theta, _reference_probability, _ = reference
    evaluator = IndependentGroupedBinomialEvaluator(
        objective.design, objective.young, objective.total, objective.offset,
    )
    cross_evaluation = independent_evaluator_checks(
        objective, evaluator, theta,
        float(tolerances["gradient_infinity_norm_per_total"]),
        float(tolerances["objective_difference_per_total"]),
        float(tolerances["fitted_probability_max_abs_difference"]),
    )
    canonical_score = original_coordinate_score_diagnostics(
        objective, theta, objective.probability(theta),
    )
    diagnostic_objective = objective.function(theta)
    best_binding_objective = min(
        objective.function(reference_theta),
        objective.function(trust_theta),
    )
    signed_objective_gap = diagnostic_objective - best_binding_objective
    target_differences = {
        label: abs(float(np.asarray(functional, float) @ (
            theta - reference_theta
        )))
        for label, functional in target_functionals.items()
    }
    maximum_target_difference = max(
        target_differences.values(), default=0.0,
    )
    stationarity = diagnostic.get(
        "full_hessian_stationarity_certificate", {},
    )
    independently_stationary = bool(
        canonical_score["gradient_infinity_norm_per_total"]
        <= float(tolerances["gradient_infinity_norm_per_total"])
        and canonical_score["standardized_score_max_abs"]
        <= standardized_score_tolerance
        and stationarity.get("status")
        == "PASS_ORIGINAL_FULL_HESSIAN_WEAK_DIRECTION_CERTIFICATE"
    )
    materially_lower_objective = bool(
        signed_objective_gap
        < -float(tolerances["objective_difference_per_total"])
    )
    derivative_implementation_contradiction = bool(
        cross_evaluation["status"]
        != "PASS_INDEPENDENT_EVALUATOR_AND_DERIVATIVE_CHECKS"
    )
    stationary_target_contradiction = bool(
        independently_stationary
        and maximum_target_difference
        > float(tolerances["target_coefficient_absolute_difference"])
    )
    contradiction = bool(
        materially_lower_objective
        or derivative_implementation_contradiction
        or stationary_target_contradiction
    )
    return {
        "status": (
            "BLOCKED_LBFGSB_DIAGNOSTIC_CONTRADICTION"
            if contradiction else
            "PASS_NO_LBFGSB_DIAGNOSTIC_CONTRADICTION"
        ),
        "available": True,
        "binding_pass": not contradiction,
        "contradiction_detected": contradiction,
        "diagnostic_candidate_numerically_valid": diagnostic.get(
            "numerically_valid"
        ),
        "diagnostic_candidate_independently_stationary": (
            independently_stationary
        ),
        "recomputed_objective_per_total": diagnostic_objective,
        "best_binding_objective_per_total": best_binding_objective,
        "signed_objective_gap_diagnostic_minus_best_binding": (
            signed_objective_gap
        ),
        "target_absolute_differences_vs_reference": target_differences,
        "maximum_declared_target_absolute_difference_vs_reference": (
            maximum_target_difference
        ),
        "canonical_recomputed_score": canonical_score,
        "independent_cross_evaluation": cross_evaluation,
        "checks": {
            "no_materially_lower_diagnostic_objective": (
                not materially_lower_objective
            ),
            "no_derivative_implementation_contradiction": (
                not derivative_implementation_contradiction
            ),
            "no_stationary_declared_target_contradiction": (
                not stationary_target_contradiction
            ),
        },
        "interpretation": (
            "nonstationary target differences do not block; lower objective, "
            "cross-evaluator derivative disagreement, or a stationary target "
            "disagreement does block"
        ),
    }


def dual_candidate_fitted_hessian_audit(
    design: sparse.csr_matrix,
    total: np.ndarray,
    trust_probability: np.ndarray,
    reference_probability: np.ndarray,
    expected_rank: int,
    relative_tolerance: float,
) -> dict[str, Any]:
    """Require raw and diagonally scaled fitted-Hessian PD on both paths."""
    candidates = {}
    for label, probability in (
        ("trust_path", trust_probability),
        ("independent_zero_start_reference", reference_probability),
    ):
        probability = np.asarray(probability, float)
        weight = np.asarray(total, float) * probability * (1.0 - probability)
        candidates[label] = full_hessian_diagnostics(
            design, weight, expected_rank, relative_tolerance,
        )
    checks = {
        label: bool(
            audit.get("status") == "PASS_FULL_HESSIAN_SPECTRUM"
            and audit.get("rank_deficiency") == 0
            and audit.get("positive_definite_at_declared_tolerance") is True
            and math.isfinite(audit.get(
                "smallest_positive_or_extreme_eigenvalue", math.nan,
            ))
            and math.isfinite(audit.get(
                "diagonally_scaled_smallest_positive_or_extreme_eigenvalue",
                math.nan,
            ))
        )
        for label, audit in candidates.items()
    }
    return {
        "status": (
            "PASS_BOTH_CANDIDATE_RAW_AND_SCALED_FITTED_HESSIANS"
            if all(checks.values()) else
            "BLOCKED_CANDIDATE_RAW_OR_SCALED_FITTED_HESSIAN"
        ),
        "expected_full_rank": expected_rank,
        "checks": checks,
        "candidates": candidates,
    }


def a1_shared_problem_binding(
    active: np.ndarray,
    design: SparseDesign,
    treatment_labels: list[str],
    target_functionals: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Hash the one problem instance consumed by both binding A1 paths."""
    active_positions = np.ascontiguousarray(
        np.flatnonzero(np.asarray(active, bool)), dtype="<i8",
    )
    active_hash = hashlib.sha256(
        canonical_bytes({
            "semantic": "zero-based positions in exact input-model row order",
            "count": len(active_positions),
        }) + b"\0" + active_positions.tobytes(order="C")
    ).hexdigest()

    matrix = design.full.copy().tocsr()
    matrix.sort_indices()
    if len(active_positions) != matrix.shape[0]:
        raise AuditBlocked(
            "A1 shared-problem active-row count differs from final design rows"
        )
    matrix_header = canonical_bytes({
        "shape": list(matrix.shape),
        "parameter_labels": design.nuisance_column_labels + treatment_labels,
        "serialization": (
            "CSR little-endian float64 data, int64 indices, int64 indptr"
        ),
    })
    design_hash = hashlib.sha256(
        matrix_header + b"\0"
        + np.ascontiguousarray(matrix.data, dtype="<f8").tobytes()
        + b"\0"
        + np.ascontiguousarray(matrix.indices, dtype="<i8").tobytes()
        + b"\0"
        + np.ascontiguousarray(matrix.indptr, dtype="<i8").tobytes()
    ).hexdigest()

    normalization_payload = {
        "first_levels": design.first_levels,
        "second_levels": design.second_levels,
        "second_references": design.second_references,
        "nuisance_column_labels": design.nuisance_column_labels,
        "component_count": design.component_count,
        "component_sizes": design.component_sizes,
    }
    normalization_hash = hashlib.sha256(
        canonical_bytes(normalization_payload)
    ).hexdigest()

    target_labels = list(target_functionals)
    target_matrix = np.ascontiguousarray(np.vstack([
        np.asarray(target_functionals[label], dtype="<f8")
        for label in target_labels
    ]), dtype="<f8")
    target_hash = hashlib.sha256(
        canonical_bytes({
            "shape": list(target_matrix.shape),
            "labels_in_row_order": target_labels,
            "serialization": "row-major little-endian float64",
        }) + b"\0" + target_matrix.tobytes(order="C")
    ).hexdigest()
    combined = hashlib.sha256(canonical_bytes({
        "active_rows_sha256": active_hash,
        "ordered_sparse_design_sha256": design_hash,
        "nuisance_normalization_sha256": normalization_hash,
        "ordered_target_matrix_sha256": target_hash,
    })).hexdigest()
    return {
        "status": "PASS_SINGLE_HASHED_PROBLEM_SHARED_BY_BOTH_A1_PATHS",
        "active_rows_sha256": active_hash,
        "ordered_sparse_design_sha256": design_hash,
        "nuisance_normalization_sha256": normalization_hash,
        "ordered_target_matrix_sha256": target_hash,
        "combined_problem_sha256": combined,
        "trust_path_problem_sha256": combined,
        "zero_start_reference_problem_sha256": combined,
        "both_paths_receive_same_objective_instance": True,
        "active_row_count": len(active_positions),
        "parameter_count": matrix.shape[1],
        "target_functional_count": len(target_labels),
    }


def conditionally_polish_trust_candidate(
    objective: BinomialObjective,
    trust_output: tuple[
        dict[str, Any], np.ndarray, np.ndarray, list[dict[str, Any]]
    ],
    max_iterations: int,
    gradient_tolerance: float,
    standardized_score_tolerance: float,
    focal_column: int,
    target_functionals: dict[str, np.ndarray],
    target_coefficient_tolerance: float,
    raw_likelihood_tolerance: float,
    linear_solve_relative_tolerance: float,
    objective_equivalence_tolerance: float,
    probability_equivalence_tolerance: float,
) -> tuple[
    tuple[dict[str, Any], np.ndarray, np.ndarray, list[dict[str, Any]]],
    dict[str, Any],
]:
    """Apply the same independent exact-Newton engine only after trust fails."""
    trust_diagnostics, trust_theta, trust_probability, trust_trajectory = (
        trust_output
    )
    before = {
        "numerically_valid": trust_diagnostics["numerically_valid"],
        "acceptance_source": trust_diagnostics["acceptance_source"],
        "certificate_status": trust_diagnostics[
            "full_hessian_stationarity_certificate"
        ]["status"],
        "objective_per_total": trust_diagnostics["objective_per_total"],
        "target_vector": target_vector(trust_theta, target_functionals),
    }
    if trust_diagnostics["numerically_valid"] is True:
        trust_path_diagnostics = {
            **trust_diagnostics,
            "method": "trust-path-unpolished-trust-ncg",
            "trust_candidate_preserved": True,
            "conditional_exact_newton_polish_applied": False,
        }
        return (
            trust_path_diagnostics, trust_theta, trust_probability,
            trust_trajectory,
        ), {
            "status": "PASS_TRUST_EXTERNAL_CERTIFICATE_NO_POLISH_REQUIRED",
            "applied": False,
            "trigger": "trust candidate passed unchanged external certificate",
            "before": before,
            "after": before,
            "trust_candidate_parameter_change_max_abs": 0.0,
        }

    polished_raw = fit_independent_sparse_newton(
        objective, trust_theta, max_iterations, gradient_tolerance,
        standardized_score_tolerance, focal_column, target_functionals,
        target_coefficient_tolerance, raw_likelihood_tolerance,
        linear_solve_relative_tolerance, objective_equivalence_tolerance,
        probability_equivalence_tolerance, "conditional_trust_polish",
    )
    polished = externally_certify_independent_output(
        objective, polished_raw, target_functionals, gradient_tolerance,
        standardized_score_tolerance, target_coefficient_tolerance,
        raw_likelihood_tolerance, linear_solve_relative_tolerance,
        objective_equivalence_tolerance, probability_equivalence_tolerance,
    )
    polished_diagnostics, polished_theta, polished_probability, trajectory = (
        polished
    )
    trust_path_diagnostics = {
        **polished_diagnostics,
        "method": "trust-path-with-independent-exact-newton-polish",
        "trust_candidate_preserved": True,
        "conditional_exact_newton_polish_applied": True,
        "pre_polish_trust_diagnostics": before,
    }
    after = {
        "numerically_valid": polished_diagnostics["numerically_valid"],
        "acceptance_source": polished_diagnostics["acceptance_source"],
        "certificate_status": polished_diagnostics[
            "full_hessian_stationarity_certificate"
        ]["status"],
        "objective_per_total": polished_diagnostics["objective_per_total"],
        "target_vector": target_vector(polished_theta, target_functionals),
    }
    return (
        trust_path_diagnostics, polished_theta, polished_probability, trajectory,
    ), {
        "status": (
            "PASS_CONDITIONAL_TRUST_EXACT_NEWTON_POLISH"
            if polished_diagnostics["numerically_valid"] else
            "BLOCKED_CONDITIONAL_TRUST_EXACT_NEWTON_POLISH"
        ),
        "applied": True,
        "trigger": "trust candidate failed unchanged external certificate",
        "before": before,
        "after": after,
        "trust_candidate_parameter_change_max_abs": float(np.max(
            np.abs(polished_theta - trust_theta), initial=0.0,
        )),
    }


def compare_trust_path_to_reference(
    objective: BinomialObjective,
    trust_path: tuple[
        dict[str, Any], np.ndarray, np.ndarray, list[dict[str, Any]]
    ],
    reference: tuple[
        dict[str, Any], np.ndarray, np.ndarray, list[dict[str, Any]]
    ],
    target_functionals: dict[str, np.ndarray],
    tolerances: dict[str, Any],
    row_identifiers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Binding A1 comparison on every declared target and fitted quantity."""
    trust, trust_theta, trust_probability, _ = trust_path
    ref, ref_theta, ref_probability, _ = reference
    trust_targets = target_vector(trust_theta, target_functionals)
    reference_targets = target_vector(ref_theta, target_functionals)
    target_differences = {
        label: abs(trust_targets[label] - reference_targets[label])
        for label in target_functionals
    }
    maximum_target_difference = max(target_differences.values(), default=0.0)
    identified_treatment_labels = [
        label for label in target_functionals
        if label.startswith("original_treatment::")
    ]
    # Generic synthetic callers may supply only unit-functionals with shorter
    # names.  Production always supplies the explicit treatment_basis family.
    if not identified_treatment_labels:
        identified_treatment_labels = list(target_functionals)
    identified_treatment_differences = {
        label: target_differences[label]
        for label in identified_treatment_labels
    }
    transformed_basis_differences = {
        label: target_differences[label]
        for label in target_functionals
        if label.startswith("treatment_basis::")
    }
    maximum_identified_treatment_difference = max(
        identified_treatment_differences.values(), default=math.inf,
    )
    probability_difference = trust_probability - ref_probability
    fitted_stock_difference = objective.total * probability_difference
    trust_eta = objective.offset + np.asarray(
        objective.design @ trust_theta
    ).reshape(-1)
    reference_eta = objective.offset + np.asarray(
        objective.design @ ref_theta
    ).reshape(-1)
    eta_difference = trust_eta - reference_eta
    argmax = int(np.argmax(np.abs(probability_difference)))
    if row_identifiers is not None and len(row_identifiers) != len(
        probability_difference
    ):
        raise AuditBlocked("A1 comparison row identifiers have the wrong length")
    location: dict[str, Any] = {
        "row_position_zero_based": argmax,
        "trust_path_fitted_probability": float(trust_probability[argmax]),
        "reference_fitted_probability": float(ref_probability[argmax]),
        "absolute_difference": float(abs(probability_difference[argmax])),
    }
    if row_identifiers is not None:
        location["row_identifiers"] = row_identifiers[argmax]
    objective_gap = abs(
        trust["objective_per_total"] - ref["objective_per_total"]
    )
    probability_gap = float(np.max(
        np.abs(probability_difference), initial=0.0,
    ))
    evaluator = IndependentGroupedBinomialEvaluator(
        objective.design, objective.young, objective.total, objective.offset,
    )
    trust_cross_evaluation = independent_evaluator_checks(
        objective, evaluator, trust_theta,
        float(tolerances["gradient_infinity_norm_per_total"]),
        float(tolerances["objective_difference_per_total"]),
        float(tolerances["fitted_probability_max_abs_difference"]),
    )
    reference_cross_evaluation = independent_evaluator_checks(
        objective, evaluator, ref_theta,
        float(tolerances["gradient_infinity_norm_per_total"]),
        float(tolerances["objective_difference_per_total"]),
        float(tolerances["fitted_probability_max_abs_difference"]),
    )
    checks = {
        "trust_path_externally_certified": trust["numerically_valid"] is True,
        "zero_start_reference_externally_certified": (
            ref["numerically_valid"] is True
        ),
        "full_target_vector": (
            maximum_target_difference
            <= tolerances["target_coefficient_absolute_difference"]
        ),
        "full_identified_treatment_vector": (
            maximum_identified_treatment_difference
            <= tolerances["target_coefficient_absolute_difference"]
        ),
        "fitted_probabilities": (
            probability_gap
            <= tolerances["fitted_probability_max_abs_difference"]
        ),
        "objective_per_total": (
            objective_gap <= tolerances["objective_difference_per_total"]
        ),
        "trust_candidate_cross_evaluator_equivalence": (
            trust_cross_evaluation["status"]
            == "PASS_INDEPENDENT_EVALUATOR_AND_DERIVATIVE_CHECKS"
        ),
        "reference_candidate_cross_evaluator_equivalence": (
            reference_cross_evaluation["status"]
            == "PASS_INDEPENDENT_EVALUATOR_AND_DERIVATIVE_CHECKS"
        ),
    }
    return {
        "status": (
            "PASS_A1_TRUST_PATH_VS_ZERO_START_REFERENCE"
            if all(checks.values()) else
            "BLOCKED_A1_TRUST_PATH_VS_ZERO_START_REFERENCE"
        ),
        "left_solver": trust["method"],
        "right_solver": ref["method"],
        "left_valid": trust["numerically_valid"],
        "right_valid": ref["numerically_valid"],
        "trust_path_target_vector": trust_targets,
        "reference_target_vector": reference_targets,
        "target_absolute_differences": target_differences,
        "identified_treatment_target_labels": identified_treatment_labels,
        "identified_treatment_target_count": len(identified_treatment_labels),
        "identified_treatment_absolute_differences": (
            identified_treatment_differences
        ),
        "transformed_basis_absolute_differences_nonbinding_diagnostic": (
            transformed_basis_differences
        ),
        "maximum_absolute_full_identified_treatment_vector_difference": (
            maximum_identified_treatment_difference
        ),
        "reported_target_absolute_differences": target_differences,
        "reported_target_max_absolute_difference": maximum_target_difference,
        "reported_target_comparison_pass": checks["full_target_vector"],
        "focal_target_left": trust_targets.get("focal_target"),
        "focal_target_right": reference_targets.get("focal_target"),
        "focal_target_absolute_difference": target_differences.get(
            "focal_target", 0.0,
        ),
        "all_parameter_max_abs_difference_including_nuisance": float(np.max(
            np.abs(trust_theta - ref_theta), initial=0.0,
        )),
        "all_slope_max_abs_difference": (
            maximum_identified_treatment_difference
        ),
        "fitted_probability_max_abs_difference": probability_gap,
        "fitted_probability_max_abs_difference_location": location,
        "fitted_probability_rmse": float(np.sqrt(np.mean(
            np.square(probability_difference)
        ))),
        "conditional_fitted_stock_mean_max_absolute_difference": float(
            np.max(np.abs(fitted_stock_difference), initial=0.0)
        ),
        "conditional_fitted_stock_mean_rmse": float(np.sqrt(np.mean(
            np.square(fitted_stock_difference)
        ))),
        "normalized_conditional_fitted_mean_max_absolute_difference": (
            probability_gap
        ),
        "normalized_conditional_fitted_mean_comparison_pass": checks[
            "fitted_probabilities"
        ],
        "linear_predictor_all_finite": bool(
            np.isfinite(trust_eta).all()
            and np.isfinite(reference_eta).all()
        ),
        "linear_predictor_max_absolute_difference_nonbinding": float(
            np.max(np.abs(eta_difference), initial=0.0)
        ),
        "linear_predictor_rmse_nonbinding": float(np.sqrt(np.mean(
            np.square(eta_difference)
        ))),
        "objective_difference_per_total": objective_gap,
        "raw_negative_log_likelihood_difference": abs(
            trust["raw_negative_log_likelihood"]
            - ref["raw_negative_log_likelihood"]
        ),
        "checks": checks,
        "trust_candidate_cross_evaluation": trust_cross_evaluation,
        "reference_candidate_cross_evaluation": reference_cross_evaluation,
        "comparison_pass": all(checks.values()),
        "same_final_tolerances": {
            key: tolerances[key] for key in (
                "target_coefficient_absolute_difference",
                "fitted_probability_max_abs_difference",
                "objective_difference_per_total",
            )
        },
    }


def fixed_target_profile(
    objective: BinomialObjective,
    optimum: np.ndarray,
    optimum_diagnostics: dict[str, Any],
    focal_column: int,
    conditional_information: float,
    multipliers: list[float],
    max_iterations: int,
    gradient_tolerance: float,
    standardized_score_tolerance: float,
    raw_rise_tolerance: float,
    linear_solve_relative_tolerance: float,
    objective_equivalence_tolerance: float = 1e-10,
    probability_equivalence_tolerance: float = 1e-7,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if (
        optimum_diagnostics.get("numerically_valid") is not True
        or optimum_diagnostics.get("acceptance_source")
        != "ORIGINAL_COORDINATE_DECLARED_KKT_AND_FULL_HESSIAN_CERTIFICATE"
    ):
        return [], {
            "status": "BLOCKED_FULL_OPTIMUM_NOT_ORIGINAL_KKT_CERTIFIED",
            "two_sided_rise": False,
            "center_source": "UNAVAILABLE",
        }
    if not math.isfinite(conditional_information) or conditional_information <= 0:
        return [], {"status": "BLOCKED_NONPOSITIVE_TARGET_INFORMATION"}
    if 0.0 not in multipliers or multipliers != sorted(multipliers):
        return [], {"status": "BLOCKED_PROFILE_GRID_HAS_NO_EXACT_ORDERED_CENTER"}
    likelihood_se = 1.0 / math.sqrt(conditional_information)
    keep = np.arange(len(optimum)) != focal_column
    reduced_design = objective.design[:, keep]
    target_column = np.asarray(objective.design[:, focal_column].todense()).reshape(-1)
    reduced_start = optimum[keep]
    full_optimum_raw_nll = objective.raw_nll(optimum)
    if not math.isfinite(full_optimum_raw_nll):
        return [], {"status": "BLOCKED_NONFINITE_CERTIFIED_FULL_OPTIMUM"}
    rows: list[dict[str, Any]] = []
    for multiplier in multipliers:
        fixed_value = float(optimum[focal_column] + multiplier * likelihood_se)
        # Preserve any offset already present in the full objective.  The YAX
        # production objective currently has a zero offset, but dropping a
        # nonzero offset here would silently profile a different likelihood.
        offset = objective.offset + target_column * fixed_value
        reduced_objective = BinomialObjective(
            reduced_design, objective.young, objective.total, offset,
        )
        if multiplier == 0.0:
            profile_fit_method = "supplied-certified-full-optimum"
            theta = reduced_start.copy()
            probability = objective.probability(optimum)
            full_score = original_coordinate_score_diagnostics(
                objective, optimum, probability
            )
            nuisance_raw = full_score["raw_gradient"][keep]
            nuisance_standardized = full_score["standardized_score"][keep]
            nuisance_steps = full_score["coordinate_step"][keep]
            center_kkt_valid = bool(
                np.isfinite(probability).all()
                and float(
                    np.max(np.abs(nuisance_raw)) / objective.scale
                    if len(nuisance_raw) else 0.0
                ) <= gradient_tolerance
                and float(
                    np.max(nuisance_standardized)
                    if len(nuisance_standardized) else 0.0
                ) <= standardized_score_tolerance
            )
            diagnostics = {
                "method": "CERTIFIED_FULL_OPTIMUM_CENTER",
                "scipy_success": optimum_diagnostics.get("scipy_success", False),
                "scipy_status": optimum_diagnostics.get("scipy_status", -1),
                "message": "center is the supplied original-KKT-certified full optimum",
                "iterations": optimum_diagnostics.get("iterations", 0),
                "objective_per_total": objective.function(optimum),
                "raw_negative_log_likelihood": full_optimum_raw_nll,
                "raw_gradient_infinity_norm": float(
                    np.max(np.abs(nuisance_raw)) if len(nuisance_raw) else 0.0
                ),
                "gradient_infinity_norm_per_total": float(
                    np.max(np.abs(nuisance_raw)) / objective.scale
                    if len(nuisance_raw) else 0.0
                ),
                "standardized_score_max_abs": float(
                    np.max(nuisance_standardized)
                    if len(nuisance_standardized) else 0.0
                ),
                "coordinate_newton_step_max_abs": float(
                    np.max(nuisance_steps) if len(nuisance_steps) else 0.0
                ),
                "numerically_valid": center_kkt_valid,
                "acceptance_source": (
                    "SUPPLIED_FULL_OPTIMUM_ORIGINAL_COORDINATE_KKT"
                    if center_kkt_valid else
                    "BLOCKED_RECOMPUTED_FULL_OPTIMUM_ORIGINAL_COORDINATE_KKT"
                ),
                "optimizer_reparameterization": optimum_diagnostics.get(
                    "optimizer_reparameterization", {"status": "UNRECORDED"}
                ),
            }
        elif reduced_design.shape[1] == 0:
            profile_fit_method = "vacuous-no-nuisance-parameters"
            theta = np.empty(0, dtype=float)
            probability = reduced_objective.probability(theta)
            diagnostics = {
                "method": "NO_NUISANCE_PARAMETERS",
                "scipy_success": True,
                "scipy_status": 0,
                "message": "fixed target leaves no nuisance parameters",
                "iterations": 0,
                "objective_per_total": reduced_objective.function(theta),
                "raw_negative_log_likelihood": reduced_objective.raw_nll(theta),
                "raw_gradient_infinity_norm": 0.0,
                "gradient_infinity_norm_per_total": 0.0,
                "standardized_score_max_abs": 0.0,
                "coordinate_newton_step_max_abs": 0.0,
                "numerically_valid": True,
                "acceptance_source": "VACUOUS_NO_NUISANCE_KKT",
                "scipy_status_is_not_acceptance_evidence": True,
                "optimizer_reparameterization": {
                    "status": "NOT_APPLICABLE_NO_NUISANCE_PARAMETERS",
                },
            }
        else:
            profile_fit_method = (
                "independent-damped-sparse-newton-irls-from-zero"
            )
            independent_profile = fit_independent_sparse_newton(
                reduced_objective, np.zeros(reduced_design.shape[1]),
                max_iterations, gradient_tolerance,
                standardized_score_tolerance, 0, {}, math.inf,
                raw_rise_tolerance, linear_solve_relative_tolerance,
                objective_equivalence_tolerance,
                probability_equivalence_tolerance,
                "standalone_zero_reference",
            )
            diagnostics, theta, probability, _ = (
                externally_certify_independent_output(
                    reduced_objective, independent_profile, {},
                    gradient_tolerance, standardized_score_tolerance,
                    math.inf, raw_rise_tolerance,
                    linear_solve_relative_tolerance,
                    objective_equivalence_tolerance,
                    probability_equivalence_tolerance,
                )
            )
        target_score = float(
            target_column @ (objective.total * probability - objective.young) /
            objective.scale
        )
        row = {
            "multiplier": float(multiplier),
            "fixed_target": fixed_value,
            "likelihood_curvature_se": likelihood_se,
            "objective_per_total": diagnostics["objective_per_total"],
            "raw_negative_log_likelihood": diagnostics[
                "raw_negative_log_likelihood"
            ],
            "nuisance_raw_gradient_infinity_norm": diagnostics[
                "raw_gradient_infinity_norm"
            ],
            "nuisance_gradient_infinity_norm_per_total": diagnostics[
                "gradient_infinity_norm_per_total"
            ],
            "nuisance_standardized_score_max_abs": diagnostics[
                "standardized_score_max_abs"
            ],
            "nuisance_coordinate_newton_step_max_abs": diagnostics[
                "coordinate_newton_step_max_abs"
            ],
            "target_score_per_total": target_score,
            "success": diagnostics["numerically_valid"],
            "nuisance_fit_method": profile_fit_method,
            "acceptance_source": diagnostics["acceptance_source"],
            "scipy_success": diagnostics["scipy_success"],
            "scipy_status": diagnostics["scipy_status"],
            "scipy_status_is_not_acceptance_evidence": True,
            "message": diagnostics["message"],
            "iterations": diagnostics["iterations"],
            "optimizer_reparameterization": diagnostics[
                "optimizer_reparameterization"
            ],
            "optimizer_reparameterization_status": diagnostics[
                "optimizer_reparameterization"
            ]["status"],
        }
        rows.append(row)
    center = next(row for row in rows if row["multiplier"] == 0.0)
    for row in rows:
        row["objective_rise_from_center_per_total"] = (
            row["objective_per_total"] - full_optimum_raw_nll / objective.scale
        )
        row["raw_negative_log_likelihood_rise_from_center"] = (
            row["raw_negative_log_likelihood"] - full_optimum_raw_nll
        )
    low, high = rows[0], rows[-1]
    minimum_rise = min(
        row["raw_negative_log_likelihood_rise_from_center"] for row in rows
    )
    all_rises_nonnegative = minimum_rise >= -raw_rise_tolerance
    passed = bool(
        all(row["success"] for row in rows) and
        all_rises_nonnegative and
        low["raw_negative_log_likelihood_rise_from_center"] > raw_rise_tolerance and
        high["raw_negative_log_likelihood_rise_from_center"] > raw_rise_tolerance and
        full_optimum_raw_nll <= min(
            row["raw_negative_log_likelihood"] for row in rows
        ) + raw_rise_tolerance
    )
    return rows, {
        "status": "PASS_TWO_SIDED_FINITE_PROFILE" if passed else "BLOCKED_PROFILE_BENCHMARK",
        "likelihood_curvature_se": likelihood_se,
        "two_sided_rise": passed,
        "center_source": (
            "SUPPLIED_INDEPENDENT_ZERO_START_REFERENCE_ORIGINAL_KKT_"
            "CERTIFIED_FULL_OPTIMUM"
        ),
        "noncenter_nuisance_fit_method": (
            "independent-damped-sparse-newton-irls-from-zero"
        ),
        "center_fixed_target_equals_certified_full_optimum": bool(
            center["fixed_target"] == float(optimum[focal_column])
        ),
        "center_raw_negative_log_likelihood": full_optimum_raw_nll,
        "all_grid_rises_nonnegative_within_raw_tolerance": all_rises_nonnegative,
        "minimum_raw_negative_log_likelihood_rise_from_center": minimum_rise,
    }


def import_legacy_engine(path: pathlib.Path, expected_hash: str):
    observed = sha256_file(path)
    if observed != expected_hash:
        raise AuditBlocked(
            f"legacy engine hash mismatch: observed {observed}, expected {expected_hash}"
        )
    module_spec = importlib.util.spec_from_file_location("yax_v3_legacy_engine", path)
    if module_spec is None or module_spec.loader is None:
        raise AuditBlocked(f"cannot import legacy engine {path}")
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = module
    module_spec.loader.exec_module(module)
    return module


def run_legacy_comparator(
    engine,
    young: np.ndarray,
    total: np.ndarray,
    design: SparseDesign,
    regressors: np.ndarray,
    max_iterations: int,
) -> tuple[dict[str, Any], np.ndarray | None, np.ndarray | None]:
    try:
        fit = engine.fit_grouped_logit_fe(
            young, total, design.first_codes, design.second_codes, regressors,
            max_iterations=max_iterations,
        )
        probability = np.asarray(fit.fitted_probability, float)
        beta = np.asarray(fit.beta, float)
        result = {
            "status": "COMPLETED",
            "converged": bool(fit.converged),
            "iterations": int(fit.iterations),
            "beta": beta.tolist(),
            "probability_exact_lower_clip_1e_10": int(np.sum(probability == 1e-10)),
            "probability_exact_upper_clip_1_minus_1e_10": int(np.sum(probability == 1.0 - 1e-10)),
            "probability_min": float(probability.min()),
            "probability_max": float(probability.max()),
            "declared_behavior": "legacy probabilities clipped to [1e-10,1-1e-10], information weights floored at 1e-12, coordinate steps clipped to [-1,1]",
        }
        return result, beta, probability
    except Exception as error:  # retain the exact failure rather than substitute
        return {
            "status": "FAILED_NO_SUBSTITUTION",
            "error_type": type(error).__name__,
            "message": str(error),
        }, None, None


def audit_model(
    bundle: ModelBundle,
    analysis: dict[str, Any],
    legacy_engine,
    parity: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    tolerances = analysis["tolerances"]
    base = {
        "model_id": bundle.model_id,
        "input_rows": len(bundle.frame),
        "positive_total_rows": int(np.sum(bundle.total > 0)),
        "zero_total_rows": int(np.sum(bundle.total == 0)),
        "one_sided_zero_young_rows": int(np.sum((bundle.total > 0) & (bundle.young == 0))),
        "one_sided_zero_older_rows": int(np.sum((bundle.total > 0) & (bundle.young == bundle.total))),
        "profiled_boundary_rows": 0,
        "core_rows": int(np.sum(bundle.total > 0)),
        "regressor_columns": int(bundle.regressors.shape[1]),
        "focal_target_label": bundle.focal_target_label,
        "submitted_design_parity": parity,
    }
    if parity.get("status") != "PASS_EXACT_SUBMITTED_DESIGN_PARITY":
        return ({
            **base, "classification": "BLOCKED_SUBMITTED_DESIGN_PARITY",
            "finite_target_established": False,
            "target_estimability_status": "AUDIT_DESIGN_DIFFERS_FROM_SUBMITTED_IMPLEMENTATION",
        }, [], [], [], {})

    original_bundle = bundle
    dynamic_scope = dynamic_target_scope_diagnostics(original_bundle, analysis)
    if dynamic_scope["status"].startswith("BLOCKED_"):
        return ({
            **base,
            "dynamic_event_target_scope": dynamic_scope,
            "classification": "BLOCKED_DYNAMIC_TARGET_SCOPE_CONSTRUCTION",
            "finite_target_established": False,
            "target_estimability_status": "DECLARED_DYNAMIC_TARGET_FAMILY_IS_INCOMPLETE",
        }, [], [], [], {})
    if dynamic_scope["status"] != "NOT_APPLICABLE":
        base["dynamic_event_target_scope"] = dynamic_scope
    try:
        bundle, target_parameterization = target_coordinate_bundle(bundle)
    except Exception as error:
        return ({
            **base,
            "classification": "BLOCKED_TARGET_REPARAMETERIZATION",
            "finite_target_established": False,
            "target_estimability_status": "DECLARED_LINEAR_FUNCTIONAL_COULD_NOT_BE_REPARAMETERIZED",
            "error_type": type(error).__name__, "message": str(error),
        }, [], [], [], {})
    base["target_parameterization"] = target_parameterization
    original_treatment_functionals = {
        (
            f"original_treatment::{int(row['original_index'])}::"
            f"{row['original_label']}"
        ): np.asarray(row["weights"], float)
        for row in target_parameterization[
            "original_coefficient_functionals_in_current_basis"
        ]
    }

    try:
        active, design, face, pruning = resolve_extended_likelihood_face(
            bundle, analysis, original_treatment_functionals,
        )
    except Exception as error:
        active, recovered = profile_boundary_nuisance(bundle)
        pruning = [
            {**row, "face_iteration": 0, "reason": "recovered_pure_nuisance_boundary_after_face_failure"}
            for row in recovered
        ]
        base["profiled_boundary_rows"] = int(np.sum((bundle.total > 0) & ~active))
        base["core_rows"] = int(active.sum())
        return ({
            **base,
            "classification": "BLOCKED_EXTENDED_FACE_EXCEPTION_NO_SUBSTITUTION",
            "finite_target_established": False,
            "target_estimability_status": "FACE_RESOLUTION_FAILED_AFTER_RETAINED_BOUNDARY_ACCOUNTING",
            "error_type": type(error).__name__, "message": str(error),
        }, pruning, [], [], {})
    base["profiled_boundary_rows"] = int(np.sum((bundle.total > 0) & ~active))
    base["core_rows"] = int(active.sum())
    if design is None or face.get("status") != "PASS_FINITE_FACE_RESOLVED":
        geometry = face.get("geometric_information", {})
        separation = face.get("separation", {})
        return ({
            **base,
            "classification": face.get("status", "BLOCKED_EXTENDED_FACE_RESOLUTION"),
            "finite_target_established": False,
            "target_estimability_status": "FINITE_FOCAL_TARGET_NOT_ESTABLISHED_ON_EXTENDED_LIKELIHOOD_FACE",
            "extended_likelihood_face": face,
            "geometric_information": geometry,
            "separation": separation,
        }, pruning, [], [], {})

    young = bundle.young[active]
    total = bundle.total[active]
    x = bundle.regressors[active]
    original_focal = bundle.focal_target
    original_positive = bundle.total > 0
    original_design = make_sparse_design(bundle, original_positive)
    legacy_original, _, _ = run_legacy_comparator(
        legacy_engine,
        bundle.young[original_positive], bundle.total[original_positive],
        original_design, bundle.regressors[original_positive],
        int(tolerances["optimizer_max_iterations"]),
    )
    original_geometry = face["geometric_information"]
    try:
        selected, basis = select_regressor_basis_preserving_focal(
            design.nuisance, x, total * 0.25, original_focal, original_geometry,
        )
        x = x[:, selected]
        reduced_labels = [bundle.regressor_labels[index] for index in selected]
        focal = selected.index(original_focal)
        design = replace_design_regressors(design, x)
        focal_column = design.nuisance.shape[1] + focal
        geometry = information_diagnostics(
            design, x, total * 0.25, focal,
            float(tolerances["conditioning_rank_relative"]),
        )
        expected_hessian_rank = design.nuisance.shape[1] + geometry["treatment_information_rank"]
        geometric_full_hessian = full_hessian_diagnostics(
            design.full, total * 0.25, expected_hessian_rank,
            float(tolerances["conditioning_rank_relative"]),
        )
        geometric_reported_targets = reported_target_information_diagnostics(
            design.nuisance, x, total * 0.25,
            bundle.reported_target_weights,
            float(tolerances["conditioning_rank_relative"]),
        )
    except Exception as error:
        return ({
            **base,
            "classification": "BLOCKED_GEOMETRY_OR_BASIS_EXCEPTION_NO_SUBSTITUTION",
            "finite_target_established": False,
            "target_estimability_status": "FACE_RESOLVED_BUT_FINAL_DESIGN_GEOMETRY_FAILED",
            "extended_likelihood_face": face,
            "error_type": type(error).__name__, "message": str(error),
        }, pruning, [], [], {})
    result: dict[str, Any] = {
        **base,
        "first_fixed_effect_groups": len(design.first_levels),
        "second_fixed_effect_groups": len(design.second_levels),
        "nuisance_graph_components": design.component_count,
        "nuisance_graph_component_sizes": design.component_sizes,
        "nuisance_rank": int(design.nuisance.shape[1]),
        "nuisance_normalization_references": design.second_references,
        "geometric_information": geometry,
        "original_geometric_information_before_exact_basis_reduction": original_geometry,
        "treatment_basis": {
            **basis,
            "selected_original_labels": reduced_labels,
            "dropped_dependent_original_labels": [
                bundle.regressor_labels[index]
                for index in basis["dropped_dependent_original_columns"]
            ],
            "focal_original_index": original_focal,
            "focal_reduced_index": focal,
        },
        "geometric_full_hessian": geometric_full_hessian,
        "geometric_reported_target_information": geometric_reported_targets,
        "extended_likelihood_face": face,
        "separation": face["separation"],
        "legacy_original_positive_cell_fit": legacy_original,
    }
    if original_bundle.focal_target_weights is not None:
        result["dynamic_event_target_scope"].update({
            "recession_direction_status": (
                "PASS_ALL_REPORTED_Q5_TARGETS_RECESSION_INVARIANT_ON_FINAL_FACE"
                if face.get("status") == "PASS_FINITE_FACE_RESOLVED"
                else "BLOCKED_RECESSION_INVARIANCE_NOT_ESTABLISHED"
            ),
            "geometric_information_status": geometric_reported_targets.get("status"),
            "overall_status": "PENDING_FITTED_INFORMATION_AND_SOLVER_AUDIT",
        })
    rank_ok = (
        geometry["treatment_information_rank"] == geometry["treatment_information_columns"] and
        geometric_full_hessian.get("rank_deficiency") == 0 and
        geometric_full_hessian.get("status") == "PASS_FULL_HESSIAN_SPECTRUM"
        and geometric_reported_targets.get("status") in {
            "NOT_APPLICABLE",
            "PASS_ALL_REPORTED_TARGETS_AND_JOINT_PRETREND_INFORMATION_RANK",
        }
    )
    if not rank_ok or not geometry["focal_target_rank_identified"]:
        result.update({
            "classification": "BLOCKED_REDUCED_DESIGN_RANK_OR_FULL_HESSIAN",
            "finite_target_established": False,
            "target_estimability_status": "NOT_ESTABLISHED_DUE_TO_FINAL_FACE_RANK_OR_FULL_HESSIAN",
        })
        return result, pruning, [], [], {}

    objective = BinomialObjective(design.full, young, total)
    evaluator_preflight = independent_evaluator_preflight(
        objective,
        float(tolerances["gradient_infinity_norm_per_total"]),
        float(tolerances["objective_difference_per_total"]),
        float(tolerances["fitted_probability_max_abs_difference"]),
    )
    result["independent_evaluator_preflight"] = evaluator_preflight
    if (
        evaluator_preflight["status"]
        != "PASS_DETERMINISTIC_INDEPENDENT_EVALUATOR_PREFLIGHT"
    ):
        result.update({
            "classification": (
                "BLOCKED_DETERMINISTIC_INDEPENDENT_EVALUATOR_PREFLIGHT"
            ),
            "finite_target_established": False,
            "target_estimability_status": (
                "INDEPENDENT_REFERENCE_ALGEBRA_FAILED_PREFIT_CROSS_CHECK"
            ),
            "a1_certification": {
                "status": "BLOCKED_A1_NUMERICAL_CERTIFICATE",
            },
        })
        return result, pruning, [], [], {}
    start = np.zeros(design.full.shape[1], dtype=float)
    certificate_targets = {
        "focal_target": np.eye(1, design.full.shape[1], focal_column).reshape(-1),
    }
    dropped_basis_columns = sorted(
        set(range(bundle.regressors.shape[1])) - set(selected)
    )
    for label, raw_functional in original_treatment_functionals.items():
        raw_functional = np.asarray(raw_functional, float)
        if any(
            abs(float(raw_functional[index])) > 1e-13
            for index in dropped_basis_columns
        ):
            raise AuditBlocked(
                "identified original treatment functional requires a dropped "
                "transformed-basis column"
            )
        functional = np.zeros(design.full.shape[1], dtype=float)
        functional[design.nuisance.shape[1]:] = raw_functional[selected]
        certificate_targets[label] = functional
    for treatment_index, treatment_label in enumerate(reduced_labels):
        functional = np.zeros(design.full.shape[1], dtype=float)
        functional[design.nuisance.shape[1] + treatment_index] = 1.0
        certificate_targets[
            f"treatment_basis::{treatment_index}::{treatment_label}"
        ] = functional
    for label, weights in (bundle.reported_target_weights or {}).items():
        raw_weights = np.asarray(weights, float)
        if raw_weights.shape != (x.shape[1],):
            raise AuditBlocked(
                f"reported target has wrong full-Hessian certificate shape: {label}"
            )
        functional = np.zeros(design.full.shape[1], dtype=float)
        functional[design.nuisance.shape[1]:] = raw_weights
        certificate_targets[label] = functional
    shared_problem_binding = a1_shared_problem_binding(
        active, design, reduced_labels, certificate_targets,
    )
    result["a1_shared_problem_binding"] = shared_problem_binding
    solver_outputs: dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray, list[dict[str, Any]]]] = {}
    solver_failures: dict[str, dict[str, str]] = {}
    for method in ("L-BFGS-B", "trust-ncg"):
        try:
            solver_outputs[method] = fit_exact_solver(
                objective, method, start,
                int(tolerances["optimizer_max_iterations"]),
                float(tolerances["gradient_infinity_norm_per_total"]),
                float(tolerances["standardized_score_absolute"]),
                focal_column,
                certificate_targets,
                float(tolerances["target_coefficient_absolute_difference"]),
                float(analysis["profile"]["likelihood_rise_tolerance_raw"]),
                method == "L-BFGS-B",
                float(tolerances["conditioning_rank_relative"]),
            )
        except Exception as error:
            solver_failures[method] = {
                "error_type": type(error).__name__, "message": str(error),
            }
    try:
        reference_raw_output = fit_independent_sparse_newton(
            objective, np.zeros_like(start),
            int(tolerances["optimizer_max_iterations"]),
            float(tolerances["gradient_infinity_norm_per_total"]),
            float(tolerances["standardized_score_absolute"]),
            focal_column, certificate_targets,
            float(tolerances["target_coefficient_absolute_difference"]),
            float(analysis["profile"]["likelihood_rise_tolerance_raw"]),
            float(tolerances["conditioning_rank_relative"]),
            float(tolerances["objective_difference_per_total"]),
            float(tolerances["fitted_probability_max_abs_difference"]),
            "standalone_zero_reference",
        )
        reference_output = externally_certify_independent_output(
            objective, reference_raw_output, certificate_targets,
            float(tolerances["gradient_infinity_norm_per_total"]),
            float(tolerances["standardized_score_absolute"]),
            float(tolerances["target_coefficient_absolute_difference"]),
            float(analysis["profile"]["likelihood_rise_tolerance_raw"]),
            float(tolerances["conditioning_rank_relative"]),
            float(tolerances["objective_difference_per_total"]),
            float(tolerances["fitted_probability_max_abs_difference"]),
        )
        solver_outputs["independent-damped-sparse-newton-irls"] = (
            reference_output
        )
    except Exception as error:
        solver_failures["independent-damped-sparse-newton-irls"] = {
            "error_type": type(error).__name__, "message": str(error),
            "implementation_owned_termination_code": getattr(
                error, "termination_code", None,
            ),
            "independent_evaluation_counts": getattr(
                error, "evaluation_counts", None,
            ),
            "retained_trajectory": getattr(error, "trajectory", None),
            "last_iteration_metrics": getattr(error, "last_metrics", None),
        }
    trajectory = {
        method: output[3] for method, output in solver_outputs.items()
    }
    for method, failure_record in solver_failures.items():
        retained = failure_record.get("retained_trajectory")
        if retained is not None:
            trajectory[method] = retained
    solver_rows = [
        {"model_id": bundle.model_id, **output[0]}
        for output in solver_outputs.values()
    ]
    for method, failure in solver_failures.items():
        solver_rows.append({
            "model_id": bundle.model_id, "method": method,
            "numerically_valid": False, **failure,
        })
    required_methods = {
        "trust-ncg", "independent-damped-sparse-newton-irls",
    }
    required_failures = required_methods & set(solver_failures)
    if required_failures:
        result.update({
            "solvers": {
                **{method: output[0] for method, output in solver_outputs.items()},
                **{method: failure for method, failure in solver_failures.items()},
            },
            "classification": "BLOCKED_EXACT_SOLVER_EXCEPTION_NO_SUBSTITUTION",
            "finite_target_established": False,
            "target_estimability_status": (
                "FINAL_FACE_ESTABLISHED_BUT_A1_TRUST_OR_REFERENCE_PATH_INCOMPLETE"
            ),
            "a1_certification": {
                "status": "BLOCKED_A1_NUMERICAL_CERTIFICATE",
                "required_solver_failures": sorted(required_failures),
            },
        })
        return result, pruning, solver_rows, [], trajectory
    trust_output = solver_outputs["trust-ncg"]
    reference_output = solver_outputs[
        "independent-damped-sparse-newton-irls"
    ]
    try:
        trust_path, trust_polish = conditionally_polish_trust_candidate(
            objective, trust_output,
            int(tolerances["optimizer_max_iterations"]),
            float(tolerances["gradient_infinity_norm_per_total"]),
            float(tolerances["standardized_score_absolute"]),
            focal_column, certificate_targets,
            float(tolerances["target_coefficient_absolute_difference"]),
            float(analysis["profile"]["likelihood_rise_tolerance_raw"]),
            float(tolerances["conditioning_rank_relative"]),
            float(tolerances["objective_difference_per_total"]),
            float(tolerances["fitted_probability_max_abs_difference"]),
        )
    except Exception as error:
        result.update({
            "solvers": {
                **{method: output[0] for method, output in solver_outputs.items()},
            },
            "classification": "BLOCKED_TRUST_POLISH_EXCEPTION_NO_SUBSTITUTION",
            "finite_target_established": False,
            "target_estimability_status": (
                "TRUST_CANDIDATE_RETAINED_BUT_CONDITIONAL_POLISH_FAILED"
            ),
            "error_type": type(error).__name__, "message": str(error),
            "implementation_owned_termination_code": getattr(
                error, "termination_code", None,
            ),
            "independent_evaluation_counts": getattr(
                error, "evaluation_counts", None,
            ),
            "a1_certification": {
                "status": "BLOCKED_A1_NUMERICAL_CERTIFICATE",
            },
        })
        return result, pruning, solver_rows, [], trajectory
    trajectory["trust-path"] = trust_path[3]
    solver_rows.append({"model_id": bundle.model_id, **trust_path[0]})
    try:
        identifier_columns = [
            column for column in ("occ_code", "month", "family")
            if column in bundle.frame.columns
        ]
        active_identifiers = (
            bundle.frame.loc[active, identifier_columns]
            .reset_index(drop=True)
            .to_dict(orient="records")
        )
        comparison = compare_trust_path_to_reference(
            objective, trust_path, reference_output, certificate_targets, tolerances,
            active_identifiers,
        )
        diagnostic_lbfgsb_trust_comparison = None
        if "L-BFGS-B" in solver_outputs:
            diagnostic_lbfgsb_trust_comparison = compare_solvers(
                *solver_outputs["L-BFGS-B"][:3],
                *solver_outputs["trust-ncg"][:3],
                design.nuisance.shape[1], focal, tolerances,
                bundle.reported_target_weights, active_identifiers,
                reduced_labels,
            )
        lbfgsb_contradiction_audit = audit_lbfgsb_diagnostic_contradictions(
            objective, solver_outputs.get("L-BFGS-B"), trust_path,
            reference_output, certificate_targets, tolerances,
            float(tolerances["standardized_score_absolute"]),
            solver_failures.get("L-BFGS-B"),
        )

        reference_diagnostics, reference_theta, reference_probability, _ = (
            reference_output
        )
        trust_path_probability = trust_path[2]
        probability = reference_probability
        fitted_weight = total * probability * (1.0 - probability)
        fitted_information = information_diagnostics(
            design, x, fitted_weight, focal,
            float(tolerances["conditioning_rank_relative"]),
        )
        # Geometry already established a full-column-rank finite-face design.
        # At a genuinely finite logit solution every information weight is
        # positive, so the fitted Hessian must retain that entire rank.  Do
        # not redefine the expected rank downward after numerical underflow.
        fitted_expected_rank = design.full.shape[1]
        dual_fitted_hessian = dual_candidate_fitted_hessian_audit(
            design.full, total, trust_path_probability, reference_probability,
            fitted_expected_rank,
            float(tolerances["conditioning_rank_relative"]),
        )
        trust_path_fitted_full_hessian = dual_fitted_hessian["candidates"][
            "trust_path"
        ]
        reference_fitted_full_hessian = dual_fitted_hessian["candidates"][
            "independent_zero_start_reference"
        ]
        # Retain the historical key as an explicit alias of the primary
        # reporting/reference path while separately binding both candidates.
        fitted_full_hessian = reference_fitted_full_hessian
        fitted_reported_targets = reported_target_information_diagnostics(
            design.nuisance, x, fitted_weight,
            bundle.reported_target_weights,
            float(tolerances["conditioning_rank_relative"]),
        )
    except Exception as error:
        result.update({
            "solvers": {
                **{method: output[0] for method, output in solver_outputs.items()},
                "trust-path": trust_path[0],
            },
            "trust_newton_polish": trust_polish,
            "classification": "BLOCKED_POST_SOLVER_DIAGNOSTIC_EXCEPTION_NO_SUBSTITUTION",
            "finite_target_established": False,
            "target_estimability_status": "SOLVER_TRAJECTORIES_RETAINED_BUT_POST_SOLVER_DIAGNOSTICS_FAILED",
            "error_type": type(error).__name__, "message": str(error),
            "implementation_owned_termination_code": getattr(
                error, "termination_code", None,
            ),
            "independent_evaluation_counts": getattr(
                error, "evaluation_counts", None,
            ),
            "a1_certification": {
                "status": "BLOCKED_A1_NUMERICAL_CERTIFICATE",
            },
        })
        return result, pruning, solver_rows, [], trajectory
    try:
        profile_rows, profile_summary = fixed_target_profile(
            objective, reference_theta, reference_diagnostics, focal_column,
            float(fitted_information["focal_target_conditional_information"]),
            [float(value) for value in analysis["profile"]["grid_standard_error_multipliers"]],
            int(tolerances["profile_max_iterations"]),
            float(tolerances["gradient_infinity_norm_per_total"]),
            float(tolerances["standardized_score_absolute"]),
            float(analysis["profile"]["likelihood_rise_tolerance_raw"]),
            float(tolerances["conditioning_rank_relative"]),
            float(tolerances["objective_difference_per_total"]),
            float(tolerances["fitted_probability_max_abs_difference"]),
        )
    except Exception as error:
        result.update({
            "fitted_information": fitted_information,
            "fitted_full_hessian": fitted_full_hessian,
            "trust_path_fitted_full_hessian": (
                trust_path_fitted_full_hessian
            ),
            "reference_fitted_full_hessian": (
                reference_fitted_full_hessian
            ),
            "dual_candidate_fitted_hessian_audit": dual_fitted_hessian,
            "fitted_reported_target_information": fitted_reported_targets,
            "solvers": {
                **{method: output[0] for method, output in solver_outputs.items()},
                "trust-path": trust_path[0],
            },
            "trust_newton_polish": trust_polish,
            "solver_comparison": comparison,
            "target_profile": {
                "status": "BLOCKED_PROFILE_EXCEPTION_NO_SUBSTITUTION",
                "error_type": type(error).__name__, "message": str(error),
            },
            "classification": "BLOCKED_PROFILE_EXCEPTION_NO_SUBSTITUTION",
            "finite_target_established": False,
            "target_estimability_status": "SOLVERS_COMPLETED_BUT_REQUIRED_TARGET_PROFILE_FAILED",
            "a1_certification": {
                "status": "BLOCKED_A1_NUMERICAL_CERTIFICATE",
            },
        })
        solver_rows.append({
            "model_id": bundle.model_id, "method": "PAIR_COMPARISON", **comparison,
        })
        return result, pruning, solver_rows, [], trajectory
    for row in profile_rows:
        row["model_id"] = bundle.model_id

    legacy_core, legacy_beta, legacy_probability = run_legacy_comparator(
        legacy_engine, young, total, design, x,
        int(tolerances["optimizer_max_iterations"]),
    )
    if legacy_beta is not None and legacy_probability is not None:
        legacy_core["focal_target"] = float(legacy_beta[focal])
        legacy_core["focal_target_minus_a1_reference"] = float(
            legacy_beta[focal]
            - reference_theta[design.nuisance.shape[1] + focal]
        )
        legacy_core[
            "fitted_probability_max_abs_difference_vs_a1_reference"
        ] = float(
            np.max(np.abs(legacy_probability - reference_probability))
        )
        legacy_core["fitted_probability_rmse_vs_a1_reference"] = float(
            np.sqrt(np.mean(np.square(
                legacy_probability - reference_probability
            )))
        )
        if "L-BFGS-B" in solver_outputs:
            lbfg_theta = solver_outputs["L-BFGS-B"][1]
            lbfg_probability = solver_outputs["L-BFGS-B"][2]
            legacy_core["focal_target_minus_lbfgsb_diagnostic"] = float(
                legacy_beta[focal]
                - lbfg_theta[design.nuisance.shape[1] + focal]
            )
            legacy_core[
                "fitted_probability_max_abs_difference_vs_lbfgsb_diagnostic"
            ] = float(np.max(np.abs(
                legacy_probability - lbfg_probability
            )))

    solver_rows.append({
        "model_id": bundle.model_id,
        "method": "A1_TRUST_PATH_REFERENCE_COMPARISON", **comparison,
    })
    if diagnostic_lbfgsb_trust_comparison is not None:
        solver_rows.append({
            "model_id": bundle.model_id,
            "method": "DIAGNOSTIC_LBFGSB_TRUST_COMPARISON",
            **diagnostic_lbfgsb_trust_comparison,
        })
    solver_rows.append({
        "model_id": bundle.model_id,
        "method": "DIAGNOSTIC_LBFGSB_CONTRADICTION_AUDIT",
        **lbfgsb_contradiction_audit,
    })
    hessian_pass = bool(
        dual_fitted_hessian.get("status")
        == "PASS_BOTH_CANDIDATE_RAW_AND_SCALED_FITTED_HESSIANS"
        and all(dual_fitted_hessian.get("checks", {}).values())
        and fitted_information.get("treatment_information_rank")
        == fitted_information.get("treatment_information_columns")
        and fitted_information.get("focal_target_rank_identified") is True
        and fitted_reported_targets.get("status") in {
            "NOT_APPLICABLE",
            "PASS_ALL_REPORTED_TARGETS_AND_JOINT_PRETREND_INFORMATION_RANK",
        }
    )
    passed = bool(
        comparison["comparison_pass"] and
        trust_polish["status"] in {
            "PASS_TRUST_EXTERNAL_CERTIFICATE_NO_POLISH_REQUIRED",
            "PASS_CONDITIONAL_TRUST_EXACT_NEWTON_POLISH",
        } and
        profile_summary["status"] == "PASS_TWO_SIDED_FINITE_PROFILE" and
        hessian_pass and
        lbfgsb_contradiction_audit["binding_pass"] is True
    )
    if original_bundle.focal_target_weights is not None:
        result["dynamic_event_target_scope"].update({
            "fitted_information_status": fitted_reported_targets.get("status"),
            "reported_target_solver_comparison_status": (
                "PASS" if comparison.get("reported_target_comparison_pass") is True
                else "BLOCKED"
            ),
            "overall_status": (
                "PASS_ALL_REPORTED_Q5_EVENT_TARGETS_AND_POST_FUNCTIONAL_FULL_AUDIT"
                if passed else
                "BLOCKED_DYNAMIC_TARGET_EXISTENCE_OR_CONVERGENCE_AUDIT"
            ),
        })
    result.update({
        "fitted_information": fitted_information,
        "fitted_full_hessian": fitted_full_hessian,
        "trust_path_fitted_full_hessian": trust_path_fitted_full_hessian,
        "reference_fitted_full_hessian": reference_fitted_full_hessian,
        "dual_candidate_fitted_hessian_audit": dual_fitted_hessian,
        "fitted_reported_target_information": fitted_reported_targets,
        "solvers": {
            **{method: output[0] for method, output in solver_outputs.items()},
            "trust-path": trust_path[0],
        },
        "trust_newton_polish": trust_polish,
        "solver_comparison": comparison,
        "diagnostic_lbfgsb_trust_comparison": (
            diagnostic_lbfgsb_trust_comparison
        ),
        "lbfgsb_diagnostic_contradiction_audit": (
            lbfgsb_contradiction_audit
        ),
        "target_profile": profile_summary,
        "legacy_profiled_core_comparator": legacy_core,
        "focal_target_estimate": float(reference_theta[focal_column]),
        "numerical_evidence_context": {
            "face_status": face["status"],
            "face_iterations": face["iterations"],
            "profiled_boundary_rows": result["profiled_boundary_rows"],
            "active_rows_sha256": shared_problem_binding[
                "active_rows_sha256"
            ],
            "ordered_final_design_sha256": shared_problem_binding[
                "ordered_sparse_design_sha256"
            ],
            "nuisance_normalization_sha256": shared_problem_binding[
                "nuisance_normalization_sha256"
            ],
            "treatment_basis_status": basis["status"],
            "selected_treatment_labels": reduced_labels,
            "dropped_treatment_labels": result["treatment_basis"][
                "dropped_dependent_original_labels"
            ],
            "optimizer_evidence": {
                method: {
                    "options": output[0].get("optimizer_options"),
                    "start_status": output[0].get(
                        "optimizer_start", {}
                    ).get("status"),
                    "start_original_coordinates_sha256": output[0].get(
                        "optimizer_start_original_coordinates_sha256"
                    ),
                }
                for method, output in solver_outputs.items()
            },
        },
        "a1_certification": {
            "status": (
                "PASS_A1_NUMERICAL_CERTIFICATE"
                if passed else "BLOCKED_A1_NUMERICAL_CERTIFICATE"
            ),
            "primary_path": "trust-path",
            "reference_path": "independent-damped-sparse-newton-irls",
            "shared_problem_binding_pass": (
                shared_problem_binding["status"]
                == "PASS_SINGLE_HASHED_PROBLEM_SHARED_BY_BOTH_A1_PATHS"
                and shared_problem_binding["trust_path_problem_sha256"]
                == shared_problem_binding[
                    "zero_start_reference_problem_sha256"
                ]
            ),
            "deterministic_evaluator_preflight_pass": (
                evaluator_preflight["status"]
                == "PASS_DETERMINISTIC_INDEPENDENT_EVALUATOR_PREFLIGHT"
            ),
            "trust_reference_full_target_vector_pass": comparison[
                "checks"
            ]["full_target_vector"],
            "trust_reference_full_identified_treatment_vector_pass": comparison[
                "checks"
            ]["full_identified_treatment_vector"],
            "identified_treatment_vector_length": comparison[
                "identified_treatment_target_count"
            ],
            "maximum_absolute_full_identified_treatment_vector_difference": (
                comparison[
                    "maximum_absolute_full_identified_treatment_vector_difference"
                ]
            ),
            "trust_reference_fitted_probability_pass": comparison[
                "checks"
            ]["fitted_probabilities"],
            "trust_reference_objective_pass": comparison[
                "checks"
            ]["objective_per_total"],
            "reference_evaluator_checks_pass": (
                reference_diagnostics[
                    "independent_evaluator_final_checks"
                ]["status"]
                == "PASS_INDEPENDENT_EVALUATOR_AND_DERIVATIVE_CHECKS"
            ),
            "reference_external_certificate_pass": (
                reference_diagnostics["numerically_valid"] is True
            ),
            "trust_path_external_certificate_pass": (
                trust_path[0]["numerically_valid"] is True
            ),
            "profile_reference_method_pass": (
                profile_summary["status"] == "PASS_TWO_SIDED_FINITE_PROFILE"
                and profile_summary["noncenter_nuisance_fit_method"]
                == "independent-damped-sparse-newton-irls-from-zero"
            ),
            "fitted_hessian_pass": hessian_pass,
            "both_candidates_raw_scaled_fitted_hessian_pass": hessian_pass,
            "lbfgsb_diagnostic_contradiction_free": (
                lbfgsb_contradiction_audit["binding_pass"] is True
            ),
        },
        "classification": "PASS_FINITE_EXTENDED_MLE_TARGET" if passed else "BLOCKED_NUMERICAL_OR_FULL_HESSIAN_BENCHMARK",
        "finite_target_established": passed,
        "target_estimability_status": (
            "FINITE_TARGET_ESTABLISHED_ON_PROFILED_EXTENDED_LIKELIHOOD"
            if passed else "FINITE_OBJECTIVE_CANDIDATE_BUT_SOLVER_OR_PROFILE_BENCHMARK_FAILED"
        ),
    })
    return result, pruning, solver_rows, profile_rows, trajectory


def git_commit(repo_root: pathlib.Path) -> str | None:
    result = subprocess.run(
        [str(EXPECTED_GIT_PATH), "rev-parse", "HEAD"], cwd=repo_root,
        env=SANITIZED_GIT_ENVIRONMENT,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def authenticated_execution_state(
    args: argparse.Namespace,
    repo_root: pathlib.Path,
    canonical: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    """Capture every mutable input that can affect a production result.

    The numerical run can be long.  A start-only authorization check would
    allow a changed checkout or changed aggregate input to be described by the
    stale receipt.  This snapshot is taken after initial authentication and
    compared with fresh snapshots immediately before publication.  It hashes
    only the already-authorized aggregate artifacts and committed code/specs;
    it never opens protected row-level microdata.
    """
    authorization = validate_pre_execution_authorization(
        repo_root, canonical, analysis,
    )
    runtime = execution_runtime_authentication()
    parity_paths = analysis["design_parity"]["submitted_source_sha256"]
    paths: dict[str, pathlib.Path] = {
        "canonical_spec": args.canonical_spec,
        "analysis_spec": args.analysis_spec,
        "aggregate_cells": args.cells,
        "aggregate_cells_receipt": args.cells_receipt,
        "legacy_engine": args.legacy_engine,
        "numerical_runner": pathlib.Path(__file__).resolve(),
        "artifact_safety": HERE / "artifact_safety.py",
        "cell_build_spec": repo_root / CELL_SPEC_REL,
        "target_audit_spec": repo_root / TARGET_SPEC_REL,
        "cell_builder": repo_root / CELL_CODE_REL,
        "target_auditor": repo_root / TARGET_CODE_REL,
        "pre_execution_authorization": (
            repo_root / PRE_EXECUTION_AUTHORIZATION_REL
        ),
    }
    a1 = analysis.get("amendment_a1")
    if isinstance(a1, dict):
        for label, section, key in (
            ("a1_owner_authorization", a1["authorization"], "path"),
            ("a1_parent_numerical_spec", a1["parent_numerical_spec"], "path"),
            (
                "a1_preserved_blocked_numerical_receipt",
                a1["preserved_blocked_run"], "numerical_receipt_path",
            ),
            (
                "a1_retained_cell_receipt",
                a1["authenticated_cell_reuse"], "receipt_path",
            ),
        ):
            paths[label] = repo_root / section[key]
    for relative in parity_paths:
        paths[f"submitted_design::{relative}"] = repo_root / relative
    hashes: dict[str, str] = {}
    for label, raw_path in sorted(paths.items()):
        path = pathlib.Path(raw_path)
        if not path.is_file() or path.is_symlink():
            raise AuditBlocked(
                f"authenticated execution input became absent or indirect: {label}"
            )
        hashes[label] = sha256_file(path)

    def git(arguments: list[str]) -> str:
        result = subprocess.run(
            [str(EXPECTED_GIT_PATH), *arguments], cwd=repo_root,
            env=SANITIZED_GIT_ENVIRONMENT, text=True,
            capture_output=True, check=False,
        )
        if result.returncode != 0 or result.stderr:
            raise AuditBlocked("authenticated execution Git state cannot be read")
        return result.stdout

    head = git(["rev-parse", "HEAD"]).strip()
    tree = git(["rev-parse", "HEAD^{tree}"]).strip()
    porcelain = git([
        "status", "--porcelain=v1", "--untracked-files=all",
    ])
    if (
        re.fullmatch(r"[0-9a-f]{40}", head) is None
        or re.fullmatch(r"[0-9a-f]{40}", tree) is None
        or porcelain != ""
    ):
        raise AuditBlocked(
            "authenticated execution requires the exact clean authorization checkout"
        )
    return {
        "authorization": authorization,
        "runtime": runtime,
        "input_hashes": hashes,
        "git_head": head,
        "git_tree": tree,
        "git_porcelain_sha256": hashlib.sha256(
            porcelain.encode("utf-8")
        ).hexdigest(),
    }


def require_unchanged_execution_state(
    initial: dict[str, Any],
    args: argparse.Namespace,
    repo_root: pathlib.Path,
    canonical: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    observed = authenticated_execution_state(
        args, repo_root, canonical, analysis,
    )
    if observed != initial:
        raise AuditBlocked(
            "authenticated execution state changed during the numerical audit"
        )
    return {
        "status": "PASS_COMPLETE_PREPUBLICATION_REAUTHENTICATION",
        "state_sha256": hashlib.sha256(canonical_bytes(observed)).hexdigest(),
        "protected_row_level_microdata_reread": False,
        "residual_window": (
            "bounded same-process interval from final recheck through "
            "publication; kernel no-replace is attempted first, while an "
            "unsupported-filesystem fallback adds a disclosed bounded "
            "noncooperating same-user lstat-to-os.rename collision window; "
            "neither interval is claimed eliminated"
        ),
    }


def precommit_publication_protocol() -> dict[str, Any]:
    """Truthfully disclose both allowed backends before the commit point."""
    return {
        "status": "PRECOMMIT_PUBLICATION_METHOD_NOT_YET_OBSERVED",
        "actual_backend_claimed_before_commit": False,
        "selection_order": [
            "kernel_atomic_noreplace",
            "portable_same_parent_atomic_rename_if_filesystem_unsupported",
        ],
        "kernel_path": (
            "renameat2(RENAME_NOREPLACE) or renameatx_np(RENAME_EXCL)"
        ),
        "unsupported_filesystem_fallback": (
            "revalidated exclusive sibling lock, immediate target lstat "
            "absence check, then atomic same-parent os.rename"
        ),
        "fallback_kernel_no_replace_guarantee": False,
        "fallback_target_replacement_prevention": (
            "cooperative lock plus immediate absence recheck; not "
            "kernel-enforced"
        ),
        "fallback_bounded_noncooperating_same_user_toctou": (
            "not eliminated: a noncooperating same-user writer could create "
            "an empty target between final lstat and os.rename"
        ),
        "actual_backend_recording": (
            "attempted in sanitized scheduler stdout after publication commit; "
            "stdout failure cannot reverse or invalidate the committed leaf"
        ),
    }


def publish_after_final_reauthentication(
    reservation: AtomicOutputLeaf,
    initial: dict[str, Any],
    args: argparse.Namespace,
    repo_root: pathlib.Path,
    canonical: dict[str, Any],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    """Make reauthentication the operation immediately preceding publish."""
    require_unchanged_execution_state(
        initial, args, repo_root, canonical, analysis,
    )
    # The input-state race is deliberately bounded to this direct call.  The
    # output collision guarantee is backend-specific: kernel no-replace when
    # supported, otherwise the disclosed cooperative GPFS fallback.
    return reservation.publish()


def emit_final_publication_stdout(
    status: str,
    output_leaf: str,
    post_commit_cleanup_warnings: tuple[str, ...],
    publication_semantics: dict[str, Any],
) -> dict[str, Any]:
    """Emit the actual post-commit backend without ever raising after commit."""
    required = {
        "status", "publication_backend", "same_parent_directory_rename_atomic",
        "kernel_no_replace_guarantee", "portable_gpfs_fallback_used",
        "bounded_noncooperating_same_user_toctou",
    }
    semantics_valid = required.issubset(publication_semantics)
    if semantics_valid and (
        publication_semantics["portable_gpfs_fallback_used"] is True
        and (
            publication_semantics["kernel_no_replace_guarantee"] is not False
            or not publication_semantics[
                "bounded_noncooperating_same_user_toctou"
            ]
        )
    ):
        semantics_valid = False
    payload = {
        "status": status,
        "output_leaf": output_leaf,
        "post_commit_cleanup_warnings": list(post_commit_cleanup_warnings),
        "publication_semantics": publication_semantics,
    }
    if not semantics_valid or contains_resolved_private_path(payload):
        payload = {
            "status": status,
            "output_leaf": (
                output_leaf
                if re.fullmatch(r"gate1_numerical_sge_[0-9]+", output_leaf)
                else "WITHHELD_NONCANONICAL_OUTPUT_LEAF"
            ),
            "post_commit_cleanup_warnings": [
                "publication_semantics_withheld_after_validation_failure"
            ],
            "publication_semantics": {
                "status": "POSTCOMMIT_SEMANTICS_WITHHELD_FAIL_CLOSED",
                "actual_backend_claimed": False,
                "kernel_no_replace_guarantee": None,
                "portable_gpfs_fallback_used": None,
                "bounded_noncooperating_same_user_toctou": (
                    "not claimed eliminated; consult the precommit protocol"
                ),
            },
        }
    payload["scheduler_stdout_emission_status"] = "EMITTED_AFTER_COMMIT"
    try:
        rendered = json.dumps(payload, sort_keys=True)
        print(rendered)
    except Exception as error:
        # Publication has already committed.  A closed scheduler pipe or an
        # unexpected serialization problem must not turn that commit into an
        # ambiguous nonzero process result.  The conservative protocol is
        # already inside the published receipt.
        return {
            "status": status,
            "output_leaf": (
                output_leaf
                if re.fullmatch(r"gate1_numerical_sge_[0-9]+", output_leaf)
                else "WITHHELD_NONCANONICAL_OUTPUT_LEAF"
            ),
            "post_commit_cleanup_warnings": [
                "scheduler_stdout_emission_failed_after_commit"
            ],
            "publication_semantics": {
                "status": "POSTCOMMIT_STDOUT_UNAVAILABLE",
                "actual_backend_claimed": False,
                "kernel_no_replace_guarantee": None,
                "portable_gpfs_fallback_used": None,
                "bounded_noncooperating_same_user_toctou": (
                    "not claimed eliminated; consult the published precommit "
                    "protocol"
                ),
            },
            "scheduler_stdout_emission_status": (
                "FAILED_AFTER_COMMIT_WITHOUT_PROPAGATION"
            ),
            "scheduler_stdout_error_type": type(error).__name__,
        }
    return payload


def exit_code_for_status(status: str) -> int:
    """A blocked numerical finding is never a successful process exit."""
    return 0 if status.startswith("PASS_") else 2


def render_report(audit: dict[str, Any]) -> str:
    lines = [
        "# V3 Gate-1 convergence and existence report",
        "",
        f"Status: **{audit['status']}**",
        "",
        "This is a numerical audit of the exact frequency-weighted grouped-binomial objective. "
        "It does not add pseudocounts, penalties, or a realized-count support rule. Boundary nuisance "
        "groups are profiled to their extended-likelihood supremum and recorded.",
        "",
        "| model | core rows | profiled boundary rows | graph components | treatment rank | separation | focal target | classification |",
        "|---|---:|---:|---:|---:|---|---:|---|",
    ]
    for model in audit["models"]:
        geometry = model.get("geometric_information", {})
        separation = model.get("separation", {})
        estimate = model.get("focal_target_estimate")
        estimate_text = "" if estimate is None else f"{estimate:.9f}"
        lines.append(
            "| {model_id} | {core} | {profiled} | {components} | {rank}/{columns} | {separation} | {estimate} | {classification} |".format(
                model_id=model["model_id"], core=model["core_rows"],
                profiled=model["profiled_boundary_rows"],
                components=model.get("nuisance_graph_components", ""),
                rank=geometry.get("treatment_information_rank", ""),
                columns=geometry.get("treatment_information_columns", ""),
                separation=separation.get("separation_exists", separation.get("status", "")),
                estimate=estimate_text,
                classification=model["classification"],
            )
        )
    lines.extend([
        "",
        "A PASS means rank, recession-direction, two-solver, fitted-mean, gradient, and target-profile "
        "checks all passed at the predeclared tolerances. A BLOCKED result is retained as a numerical "
        "finding and is not replaced by another estimator.",
        "",
    ])
    return "\n".join(lines)


def acquire_execution_attestations(
    args: argparse.Namespace,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Derive attestations only from the live process and pinned executables."""
    raw_cli_argv = list(sys.argv[1:])
    original_argv = list(getattr(sys, "orig_argv", []))
    binding = build_execution_command_binding(
        args, raw_cli_argv, original_argv, dict(os.environ),
    )
    runtime = execution_runtime_authentication()
    return binding, runtime


def run(args: argparse.Namespace) -> int:
    # Receipt attestations are deliberately not parameters.  An imported
    # caller cannot supply claims that were not derived from this process.
    execution_binding, execution_runtime = acquire_execution_attestations(args)
    started = utc_now()
    canonical, analysis = validate_specs(args.canonical_spec, args.analysis_spec)
    runtime = verify_runtime_contract(analysis)
    repo_root = pathlib.Path(__file__).resolve().parents[4]
    pre_execution_authorization = validate_pre_execution_authorization(
        repo_root, canonical, analysis
    )
    initial_execution_state = authenticated_execution_state(
        args, repo_root, canonical, analysis,
    )
    if initial_execution_state["authorization"] != pre_execution_authorization:
        raise AuditBlocked(
            "pre-execution authorization changed during initial authentication"
        )
    frame = authenticate_cells(args.cells, args.cells_receipt, canonical, analysis)
    legacy_path = args.legacy_engine
    legacy_engine = import_legacy_engine(
        legacy_path, analysis["software"]["legacy_engine_sha256"]
    )
    parity_modules = load_submitted_design_modules(repo_root, analysis)
    parity_source_paths = [
        repo_root / relative
        for relative in analysis["design_parity"]["submitted_source_sha256"]
    ]
    require_unchanged_execution_state(
        initial_execution_state, args, repo_root, canonical, analysis,
    )
    reservation = AtomicOutputLeaf.reserve(
        args.output_dir, repo_root,
        [
            args.canonical_spec, args.analysis_spec, args.cells,
            args.cells_receipt, legacy_path, HERE / "artifact_safety.py",
            repo_root / analysis["software"]["cell_builder_path"],
            *parity_source_paths,
        ],
    )
    output_dir = reservation.staging

    try:
        models: list[dict[str, Any]] = []
        boundary_rows: list[dict[str, Any]] = []
        pruning_rows: list[dict[str, Any]] = []
        solver_rows: list[dict[str, Any]] = []
        profile_rows: list[dict[str, Any]] = []
        trajectories: dict[str, Any] = {}
        for registry in analysis["models"]:
            model_id = registry["model_id"]
            bundle = model_bundle(frame, model_id)
            boundary_rows.extend(family_month_boundary_rows(bundle))
            failure_stage = "submitted_design_parity"
            try:
                parity = submitted_design_parity(bundle, parity_modules)
                failure_stage = "extended_likelihood_and_solver_audit"
                result, pruning, solvers, profiles, trajectory = audit_model(
                    bundle, analysis, legacy_engine, parity
                )
            except Exception as error:
                # Recover all exact nuisance-boundary information even if a
                # later numerical stage failed.  Never report zero pruning
                # merely because the downstream solver raised.
                recovered_active, recovered_pruning = profile_boundary_nuisance(bundle)
                pruning = [
                    {**row, "face_iteration": 0, "reason": "recovered_pure_nuisance_boundary_after_failure"}
                    for row in recovered_pruning
                ]
                result = {
                    "model_id": model_id,
                    "classification": "BLOCKED_UNEXPECTED_NUMERICAL_FAILURE_NO_SUBSTITUTION",
                    "finite_target_established": False,
                    "target_estimability_status": "NOT_ESTABLISHED_UNEXPECTED_NUMERICAL_FAILURE",
                    "failure_stage": failure_stage,
                    "error_type": type(error).__name__,
                    "message": str(error),
                    "input_rows": len(bundle.frame),
                    "positive_total_rows": int(np.sum(bundle.total > 0)),
                    "zero_total_rows": int(np.sum(bundle.total == 0)),
                    "one_sided_zero_young_rows": int(np.sum((bundle.total > 0) & (bundle.young == 0))),
                    "one_sided_zero_older_rows": int(np.sum((bundle.total > 0) & (bundle.young == bundle.total))),
                    "profiled_boundary_rows": int(np.sum((bundle.total > 0) & ~recovered_active)),
                    "core_rows": int(recovered_active.sum()),
                    "regressor_columns": int(bundle.regressors.shape[1]),
                    "focal_target_label": bundle.focal_target_label,
                }
                solvers, profiles, trajectory = [], [], {}
            models.append(result)
            pruning_rows.extend(pruning)
            solver_rows.extend(solvers)
            profile_rows.extend(profiles)
            trajectories[model_id] = trajectory

        status = (
            "PASS_ALL_CORE_TARGETS_NUMERICALLY_AUDITED"
            if all(model.get("finite_target_established") is True for model in models)
            else "BLOCKED_ONE_OR_MORE_CORE_TARGETS_NOT_ESTABLISHED"
        )
        audit = {
        "schema_version": AUDIT_SCHEMA,
        "status": status,
        "generated_at_utc": utc_now(),
        "canonical_spec_id": canonical["spec_id"],
        "audit_spec_id": analysis["audit_spec_id"],
        "cells_sha256": sha256_file(args.cells),
        "models": models,
        "interpretation_rule": "no blocked or failed model is replaced by another estimator",
    }
        audit_path = output_dir / "MODEL_AUDIT.json"
        write_json(audit_path, audit)
        write_json(output_dir / "OPTIMIZER_TRAJECTORIES.json", trajectories)

        diagnostic_fields = [
        "model_id", "classification", "finite_target_established", "input_rows",
        "target_estimability_status",
        "positive_total_rows", "zero_total_rows", "one_sided_zero_young_rows",
        "one_sided_zero_older_rows", "profiled_boundary_rows", "core_rows",
        "first_fixed_effect_groups", "second_fixed_effect_groups",
        "nuisance_graph_components", "nuisance_rank", "regressor_columns",
        "focal_target_label", "focal_target_estimate", "error_type", "message",
    ]
        write_csv(output_dir / "MODEL_DIAGNOSTICS.csv", models, diagnostic_fields)
        boundary_fields = [
        "model_id", "family", "month", "occupation_cells", "young", "older",
        "total", "zero_young", "zero_older",
    ]
        write_csv(output_dir / "FAMILY_MONTH_BOUNDARY_CELLS.csv", boundary_rows, boundary_fields)
        pruning_fields = [
        "model_id", "iteration", "partition", "group", "boundary_side",
        "affected_rows_before_union", "young", "older", "total", "face_iteration",
        "reason", "strict_margin", "row_index",
        ]
        write_csv(output_dir / "BOUNDARY_PROFILING.csv", pruning_rows, pruning_fields)
        solver_fields = [
        "model_id", "method", "scipy_success", "scipy_status", "message",
        "iterations", "function_evaluations", "gradient_evaluations",
        "hessian_evaluations", "line_search_candidate_evaluations",
        "newton_iterations_evaluated",
        "implementation_owned_termination_namespace",
        "implementation_owned_termination_code",
        "implementation_owned_termination_message",
        "objective_per_total", "raw_negative_log_likelihood",
        "raw_gradient_infinity_norm", "gradient_infinity_norm_per_total",
        "standardized_score_max_abs", "coordinate_newton_step_max_abs",
        "transformed_gradient_infinity_norm",
        "internal_transformed_gradient_tolerance",
        "optimizer_reparameterization_status",
        "optimizer_options", "optimizer_start_original_coordinates_sha256",
        "optimizer_start_transformed_coordinates_sha256",
        "optimizer_parameter_scale_min", "optimizer_parameter_scale_max",
        "optimizer_parameter_scale_sha256", "acceptance_source",
        "scipy_status_is_not_acceptance_evidence",
        "parameter_max_abs", "focal_target",
        "probability_exact_zero", "probability_exact_one",
        "probability_at_or_below_1e_10", "probability_at_or_above_1_minus_1e_10",
        "zero_information_weight_rows", "numerically_valid", "left_solver",
        "right_solver", "left_valid", "right_valid", "focal_target_left",
        "focal_target_right", "focal_target_absolute_difference",
        "reported_target_max_absolute_difference",
        "reported_target_comparison_pass",
        "all_slope_max_abs_difference", "fitted_probability_max_abs_difference",
        "fitted_probability_rmse",
        "conditional_fitted_stock_mean_max_absolute_difference",
        "conditional_fitted_stock_mean_rmse",
        "normalized_conditional_fitted_mean_max_absolute_difference",
        "normalized_conditional_fitted_mean_comparison_pass",
        "linear_predictor_all_finite",
        "linear_predictor_max_absolute_difference_nonbinding",
        "linear_predictor_rmse_nonbinding",
        "complete_identified_treatment_vector_count",
        "complete_identified_treatment_vector_max_absolute_difference",
        "objective_difference_per_total",
        "raw_negative_log_likelihood_difference", "comparison_pass",
    ]
        write_csv(output_dir / "SOLVER_COMPARISON.csv", solver_rows, solver_fields)
        profile_fields = [
        "model_id", "multiplier", "fixed_target", "likelihood_curvature_se",
        "objective_per_total", "raw_negative_log_likelihood",
        "objective_rise_from_center_per_total",
        "raw_negative_log_likelihood_rise_from_center",
        "nuisance_raw_gradient_infinity_norm",
        "nuisance_gradient_infinity_norm_per_total",
        "nuisance_standardized_score_max_abs",
        "nuisance_coordinate_newton_step_max_abs", "target_score_per_total",
        "success", "nuisance_fit_method", "acceptance_source",
        "scipy_success", "scipy_status",
        "scipy_status_is_not_acceptance_evidence",
        "optimizer_reparameterization_status", "message", "iterations",
    ]
        write_csv(output_dir / "TARGET_PROFILE.csv", profile_rows, profile_fields)
        report_path = output_dir / "CONVERGENCE_EXISTENCE_REPORT.md"
        report_path.write_text(render_report(audit), encoding="utf-8")

        output_paths = [
        audit_path,
        output_dir / "MODEL_DIAGNOSTICS.csv",
        output_dir / "FAMILY_MONTH_BOUNDARY_CELLS.csv",
        output_dir / "BOUNDARY_PROFILING.csv",
        output_dir / "SOLVER_COMPARISON.csv",
        output_dir / "TARGET_PROFILE.csv",
        output_dir / "OPTIMIZER_TRAJECTORIES.json",
        report_path,
        ]
        prepublication_revalidation = require_unchanged_execution_state(
            initial_execution_state, args, repo_root, canonical, analysis,
        )
        receipt = {
        "schema_version": "yax-numerical-existence-receipt-v1",
        "status": status,
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "command_template": COMMAND_TEMPLATE,
        "execution_command_binding": execution_binding,
        "execution_runtime_authentication": execution_runtime,
        "pre_execution_authorization": pre_execution_authorization,
        "prepublication_revalidation": prepublication_revalidation,
        "publication_protocol": precommit_publication_protocol(),
        "canonical_spec_id": canonical["spec_id"],
        "canonical_spec_sha256": sha256_file(args.canonical_spec),
        "audit_spec_id": analysis["audit_spec_id"],
        "audit_spec_sha256": sha256_file(args.analysis_spec),
        "cells_sha256": sha256_file(args.cells),
        "cells_receipt_sha256": sha256_file(args.cells_receipt),
        "code_sha256": sha256_file(pathlib.Path(__file__)),
        "artifact_safety_sha256": sha256_file(HERE / "artifact_safety.py"),
        "cell_builder_sha256": sha256_file(
            repo_root / analysis["software"]["cell_builder_path"]
        ),
        "submitted_design_source_sha256": analysis["design_parity"]["submitted_source_sha256"],
        "legacy_engine_sha256": sha256_file(legacy_path),
        "git_commit": git_commit(repo_root),
        "python": sys.version,
        "platform": platform.platform(),
        "runtime_contract": runtime,
        "packages": {
            "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
        },
        "model_count": len(models),
        "passed_model_count": sum(model.get("finite_target_established") is True for model in models),
        "protected_microdata_read_by_this_program": False,
        "amendment_a1": {
            "owner_authorization_sha256": A1_OWNER_AUTHORIZATION_SHA256,
            "parent_audit_spec_id": analysis["amendment_a1"][
                "parent_numerical_spec"
            ]["id"],
            "parent_audit_spec_sha256": analysis["amendment_a1"][
                "parent_numerical_spec"
            ]["sha256"],
            "scientific_target_fingerprint_sha256": analysis[
                "amendment_a1"
            ]["scientific_target_fingerprint"]["sha256"],
            "reused_authenticated_cells": True,
            "reused_cells_sha256": analysis["amendment_a1"][
                "authenticated_cell_reuse"
            ]["cells_sha256"],
            "reused_cells_receipt_sha256": analysis["amendment_a1"][
                "authenticated_cell_reuse"
            ]["receipt_sha256"],
            "protected_row_level_microdata_rebuilt": False,
        },
        "output_hashes": {path.name: sha256_file(path) for path in output_paths},
        }
        if contains_resolved_private_path(receipt):
            raise AuditBlocked("execution receipt contains a resolved private path")
        receipt_path = output_dir / "EXECUTION_RECEIPT.json"
        write_json(receipt_path, receipt)
        expected_artifacts = {path.name for path in output_paths} | {receipt_path.name}
        try:
            scan_artifacts_for_sensitive_text(output_dir, expected_artifacts)
        except AuditBlocked:
            # A path or credential discovered by the last fail-closed scan
            # must not remain even in an unpublished diagnostic directory.
            reservation.discard()
            raise
        # Recheck once more after every output byte, including the receipt, is
        # final.  Publication is the next state-changing operation.
        publication_semantics = publish_after_final_reauthentication(
            reservation, initial_execution_state, args, repo_root,
            canonical, analysis,
        )
    except Exception:
        reservation.abandon()
        raise
    emit_final_publication_stdout(
        status, args.output_dir.name,
        reservation.post_commit_cleanup_warnings,
        publication_semantics,
    )
    return exit_code_for_status(status)


def parser() -> argparse.ArgumentParser:
    result = NonEchoingArgumentParser(description=__doc__, allow_abbrev=False)
    result.add_argument("--canonical-spec", type=pathlib.Path, required=True)
    result.add_argument("--analysis-spec", type=pathlib.Path, required=True)
    result.add_argument("--cells", type=pathlib.Path, required=True)
    result.add_argument("--cells-receipt", type=pathlib.Path, required=True)
    result.add_argument("--legacy-engine", type=pathlib.Path, required=True)
    result.add_argument("--output-parent", type=pathlib.Path, required=True)
    return result


def main(argv: list[str] | None = None) -> int:
    if argv is not None:
        raise AuditBlocked(
            "production entry point does not accept a substituted argv source"
        )
    raw_cli_argv = list(sys.argv[1:])
    try:
        args = parser().parse_args(raw_cli_argv)
        job = scheduler_jobnumber(dict(os.environ))
        args.output_dir = args.output_parent / f"gate1_numerical_sge_{job}"
        return run(args)
    except (AuditBlocked, OutputSafetyError) as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
