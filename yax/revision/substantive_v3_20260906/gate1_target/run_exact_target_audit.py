#!/usr/bin/env python3
"""Audit the exact observed-data target of the V3 canonical baseline.

This program does not read row-level CPS microdata and does not estimate a
coefficient.  It consumes only the authenticated aggregate-cell product made
by ``gate1_cells``.  Its job is to prove which rows and units enter the static
grouped-binomial criterion and to bind that interpretation to the canonical
V2 contract and inspected R3 implementation.
"""
from __future__ import annotations

import argparse
import ctypes
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import errno
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Iterable

import numpy as np
import pandas as pd


V3_REL = Path("yax/revision/substantive_v3_20260906")
HERE_REL = V3_REL / "gate1_target"
TARGET_SPEC_REL = HERE_REL / "TARGET_AUDIT_SPEC.json"
CANONICAL_SPEC_REL = V3_REL / "contracts/specs/canonical_baseline_reproduction_v2.json"
CELL_SPEC_REL = V3_REL / "gate1_cells/CELL_BUILD_SPEC.json"
REQUIREMENT_SEED_REL = V3_REL / "revision_inputs/requirements_seed.json"
PRE_EXECUTION_AUTHORIZATION_REL = (
    V3_REL / "gate1_transfer/PRE_EXECUTION_AUTHORIZATION.json"
)

TARGET_SPEC_PREFIX = "yaxtargetspec_v1_"
CELL_SPEC_PREFIX = "yaxcellspec_v1_"
NUMERICAL_SPEC_PREFIX = "yaxnumspec_v1_"
TARGET_AUDIT_PREFIX = "yaxtargetaudit_v1_"
TARGET_RECEIPT_SCHEMA = "yax-exact-target-audit-receipt-v1"
EXPECTED_UPSTREAM_RECEIPT_SCHEMA = "yax-numerical-cells-receipt-v1"
EXPECTED_UPSTREAM_STATUS = "PASS_FRESH_AGGREGATE_REBUILD"
EXPECTED_AGGREGATE_SCHEMA = "yax-numerical-cells-v1"

AUDIT_FILENAME = "EXACT_TARGET_AUDIT.json"
ROW_ACCOUNTING_FILENAME = "ROW_ACCOUNTING.csv"
REPORT_FILENAME = "EXACT_TARGET_AUDIT_REPORT.md"
RECEIPT_FILENAME = "EXECUTION_RECEIPT.json"
COMMAND_TEMPLATE = (
    "<YAX_PYTHON_BIN> -I yax/revision/substantive_v3_20260906/gate1_target/"
    "run_exact_target_audit.py --repo-root <YAX_REPO_ROOT> "
    "--cells <YAX_GATE1_CELLS_LEAF>/aggregate_cells.csv "
    "--cells-receipt <YAX_GATE1_CELLS_LEAF>/EXECUTION_RECEIPT.json "
    "--output-parent <YAX_V3_RUN_ROOT>"
)
COMMAND_BINDING_SCHEMA = "yax-execution-command-binding-v2"
COMMAND_BINDING_STATUS = "RUNNER_RECORDED_HASH_CONSISTENT"
PRE_EXECUTION_AUTHORIZATION_SCHEMA = "yax-gate1-pre-execution-authorization-v1"
PRE_EXECUTION_AUTHORIZATION_STATUS = "AUTHORIZED_FRESH_GATE1_EXECUTION"
PRE_EXECUTION_AUTHORIZATION_PREFIX = "yaxgate1auth_v1_"
MODULE_KEY = "target"
JOB_ID_PATTERN = re.compile(r"^[1-9][0-9]{0,19}$")
RUN_ID_PATTERN = re.compile(r"^gate1_target_sge_([1-9][0-9]{0,19})$")
EXPECTED_PYTHON_RESOLVED_SHA256 = (
    "0887a2530329cef5a3a6b7c83c76590da9730f98f1e68497096bc05f20b92aa7"
)
EXPECTED_GIT_PATH = Path("/usr/bin/git")
EXPECTED_GIT_SHA256 = (
    "507917bbb5d24123c8e11df46df1d32483da1ce6420aa7ba7dd17de8ccd13a9e"
)
EXPECTED_GIT_VERSION = "git version 2.43.7"
SANITIZED_GIT_ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
IMPORT_AFFECTING_ENVIRONMENT = (
    "PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE", "PYTHONSTARTUP",
)
EXPECTED_PRODUCTION_FLAGS = (
    "--repo-root", "--cells", "--cells-receipt", "--output-parent",
)

SECRET_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)(?:password|passwd|api[_ -]?key|token)\s*[:=]\s*\S+"),
)
PRIVATE_PATH_PATTERNS = (
    re.compile(r"/(?:project|projectnb|usr\d+|Users|home)/[^\s\"']+"),
)

BUILDER_REL = V3_REL / "gate1_cells/run_gate1_cells.py"
NUMERICAL_SPEC_REL = V3_REL / "numerical_existence/ANALYSIS_SPEC.json"
NUMERICAL_CODE_REL = V3_REL / "numerical_existence/run_numerical_existence_audit.py"
ENVIRONMENT_REL = Path("yax/revision/substantive_r3_20260905/ENVIRONMENT_LOCK.txt")
ASSIGNMENT_FILENAME = "ASSIGNMENT_FINGERPRINT.json"
MARCH_REPAIR_MONTHS = [f"{year}-03" for year in range(2017, 2022)]
RAW_SOURCE_IDS = [
    "ipums_cps_extract_9_wide",
    "ipums_cps_extract_11_march_basic_repair",
]
UNREAD_CANONICAL_SOURCE_IDS = ["historical_preperiod_cells"]
LOOKUP_AND_AUTHORIZATION_SOURCE_IDS = [
    "cps_occupation_exposure_lookup",
    "computerization_measures_census2018",
    "rule_b_values_census2018",
    "census_occ2010_to_2018_bridge",
    "first_post_outcome_access_receipt",
]
PARTITION_COUNT_FIELDS = [
    "invalid_raw_occ_records",
    "valid_raw_occ_records",
    "early_valid_source_records",
    "current_valid_source_records",
    "early_matched_source_records",
    "early_unmatched_source_records",
    "early_expanded_route_descendants",
    "early_fractional_route_contributions",
    "early_unit_route_contributions",
    "early_zero_mass_route_contributions",
    "current_direct_route_contributions",
    "routed_contribution_rows",
]
EXPECTED_RUNTIME_AUTHENTICATION_KEYS = {
    "status",
    "observed",
    "kernel_release_rule",
    "environment_lock_path",
    "environment_lock_sha256",
    "runtime_contract_sha256",
    "runtime_payload",
    "runtime_payload_sha256",
    "command_template",
}
EXPECTED_RUNTIME_OBSERVED_KEYS = {
    "python",
    "python_implementation",
    "python_compiler",
    "numpy",
    "pandas",
    "pytest",
    "scipy",
    "kernel_system",
    "kernel_release",
    "machine",
    "libc_name",
    "libc",
}


class TargetAuditError(RuntimeError):
    """Fail-closed exact-target audit error."""


class NonEchoingArgumentParser(argparse.ArgumentParser):
    """Never echo a possibly sensitive argv token in a parser error."""

    def error(self, message: str) -> None:
        raise TargetAuditError("production command-line grammar is invalid")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def scheduler_jobnumber(environ: dict[str, str]) -> str:
    job = environ.get("JOB_ID")
    alias = environ.get("SGE_JOB_ID")
    if job is None or not JOB_ID_PATTERN.fullmatch(job):
        raise TargetAuditError("a canonical numeric SCC JOB_ID is required")
    if alias is not None and alias != job:
        raise TargetAuditError("SGE_JOB_ID conflicts with JOB_ID")
    if environ.get("SGE_TASK_ID") not in {None, "", "undefined"}:
        raise TargetAuditError("Grid Engine array jobs are not authorized")
    return job


def execution_runtime_authentication() -> dict[str, Any]:
    if (
        sys.flags.isolated != 1
        or sys.flags.ignore_environment != 1
        or sys.flags.no_user_site != 1
        or not bool(getattr(sys.flags, "safe_path", False))
    ):
        raise TargetAuditError("production Python must be invoked with isolated mode")
    if any(os.environ.get(name) for name in IMPORT_AFFECTING_ENVIRONMENT):
        raise TargetAuditError("import-affecting Python environment variables are forbidden")
    try:
        python_path = Path(sys.executable).resolve(strict=True)
    except OSError as exc:
        raise TargetAuditError("Python executable cannot be resolved") from exc
    python_hash = sha256_file(python_path)
    if python_hash != EXPECTED_PYTHON_RESOLVED_SHA256:
        raise TargetAuditError("resolved Python executable differs from the pinned runtime")
    if platform.python_version() != "3.13.8":
        raise TargetAuditError("Python version differs from the pinned runtime")
    if not EXPECTED_GIT_PATH.is_file() or EXPECTED_GIT_PATH.is_symlink():
        raise TargetAuditError("pinned Git executable is absent or indirect")
    git_hash = sha256_file(EXPECTED_GIT_PATH)
    if git_hash != EXPECTED_GIT_SHA256:
        raise TargetAuditError("Git executable differs from the pinned runtime")
    completed = subprocess.run(
        [str(EXPECTED_GIT_PATH), "--version"],
        env=SANITIZED_GIT_ENVIRONMENT,
        text=True, capture_output=True, check=False,
    )
    if completed.returncode != 0 or completed.stdout.strip() != EXPECTED_GIT_VERSION:
        raise TargetAuditError("Git version differs from the pinned runtime")
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
    }


def build_execution_command_binding(
    args: argparse.Namespace,
    raw_cli_argv: list[str],
    original_argv: list[str],
    environ: dict[str, str],
) -> dict[str, Any]:
    if len(raw_cli_argv) != 2 * len(EXPECTED_PRODUCTION_FLAGS):
        raise TargetAuditError("production command-line grammar is invalid")
    if raw_cli_argv[::2] != list(EXPECTED_PRODUCTION_FLAGS):
        raise TargetAuditError("production command-line grammar is invalid")
    if any(not value or any(ord(char) < 32 for char in value) for value in raw_cli_argv[1::2]):
        raise TargetAuditError("production command-line values are invalid")
    if len(original_argv) != len(raw_cli_argv) + 3 or original_argv[1] != "-I":
        raise TargetAuditError("production must use direct isolated-script invocation")
    try:
        invoked_python = Path(original_argv[0]).resolve(strict=True)
        invoked_script = Path(original_argv[2]).resolve(strict=True)
    except OSError as exc:
        raise TargetAuditError("production executable or runner cannot be resolved") from exc
    if invoked_python != Path(sys.executable).resolve(strict=True):
        raise TargetAuditError("invoked Python differs from the running interpreter")
    if invoked_script != Path(__file__).resolve():
        raise TargetAuditError("production runner path is not the authorized script")
    executing_repo = Path(__file__).resolve().parents[4]
    if args.repo_root.resolve(strict=True) != executing_repo:
        raise TargetAuditError("repo-root differs from the executing runner checkout")
    if not os.path.samefile(
        executing_repo / HERE_REL / "run_exact_target_audit.py",
        Path(__file__).resolve(),
    ):
        raise TargetAuditError("executing runner is not the repo-root runner inode")
    if original_argv[3:] != raw_cli_argv:
        raise TargetAuditError("raw process argv and script argv differ")
    parsed_values = (
        args.repo_root, args.cells, args.cells_receipt, args.output_parent,
    )
    if any(Path(raw).resolve(strict=False) != Path(parsed).resolve(strict=False)
           for raw, parsed in zip(raw_cli_argv[1::2], parsed_values)):
        raise TargetAuditError("parsed paths differ from the captured invocation")
    cells = Path(args.cells).resolve(strict=False)
    cells_receipt = Path(args.cells_receipt).resolve(strict=False)
    if (
        cells.name != "aggregate_cells.csv"
        or cells_receipt.name != "EXECUTION_RECEIPT.json"
        or cells.parent != cells_receipt.parent
    ):
        raise TargetAuditError("target inputs are not the exact colocated cell artifacts")
    job = scheduler_jobnumber(environ)
    run_id = f"gate1_target_sge_{job}"
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise TargetAuditError("derived output run ID is invalid")
    sanitized_argv = [
        "<YAX_PYTHON_BIN>", "-I",
        str(HERE_REL / "run_exact_target_audit.py"),
        "--repo-root", "<YAX_REPO_ROOT>",
        "--cells", "<YAX_GATE1_CELLS_LEAF>/aggregate_cells.csv",
        "--cells-receipt", "<YAX_GATE1_CELLS_LEAF>/EXECUTION_RECEIPT.json",
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


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TargetAuditError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(
                stream,
                object_pairs_hook=_unique_pairs,
                parse_constant=lambda token: (_ for _ in ()).throw(
                    TargetAuditError(f"invalid JSON numeric constant: {token}")
                ),
            )
    except OSError as exc:
        raise TargetAuditError(f"cannot read required JSON artifact {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise TargetAuditError(f"JSON root must be an object: {path.name}")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise TargetAuditError(f"refusing empty CSV output: {path.name}")
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def expected_target_spec_id(document: dict[str, Any]) -> str:
    clean = dict(document)
    clean.pop("target_audit_spec_id", None)
    return TARGET_SPEC_PREFIX + hashlib.sha256(canonical_bytes(clean)).hexdigest()


def expected_cell_spec_id(document: dict[str, Any]) -> str:
    clean = dict(document)
    clean.pop("cell_build_spec_id", None)
    return CELL_SPEC_PREFIX + hashlib.sha256(canonical_bytes(clean)).hexdigest()


def expected_numerical_spec_id(document: dict[str, Any]) -> str:
    clean = dict(document)
    clean.pop("audit_spec_id", None)
    return NUMERICAL_SPEC_PREFIX + hashlib.sha256(canonical_bytes(clean)).hexdigest()


def expected_pre_execution_authorization_id(document: dict[str, Any]) -> str:
    clean = dict(document)
    clean.pop("authorization_id", None)
    return PRE_EXECUTION_AUTHORIZATION_PREFIX + hashlib.sha256(
        canonical_bytes(clean)
    ).hexdigest()


def validate_pre_execution_authorization(
    repo: Path,
    canonical: dict[str, Any],
    target: dict[str, Any],
    cell_spec: dict[str, Any],
    code_sha256: str,
) -> dict[str, Any]:
    path = repo / PRE_EXECUTION_AUTHORIZATION_REL
    require_file(path, "pre-execution authorization")
    document = load_json(path)
    if set(document) != {
        "schema_version", "status", "authorization_id", "issued_at_utc",
        "not_before_utc", "not_after_utc", "authorized_implementation_commit",
        "canonical_spec", "source_registry_sha256", "modules",
    }:
        raise TargetAuditError("pre-execution authorization field set is not exact")
    if (
        document.get("schema_version") != PRE_EXECUTION_AUTHORIZATION_SCHEMA
        or document.get("status") != PRE_EXECUTION_AUTHORIZATION_STATUS
        or document.get("authorization_id")
        != expected_pre_execution_authorization_id(document)
    ):
        raise TargetAuditError("pre-execution authorization identity is invalid")
    try:
        issued = datetime.fromisoformat(str(document["issued_at_utc"]).replace("Z", "+00:00"))
        not_before = datetime.fromisoformat(str(document["not_before_utc"]).replace("Z", "+00:00"))
        not_after = datetime.fromisoformat(str(document["not_after_utc"]).replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise TargetAuditError("pre-execution authorization timestamps are invalid") from exc
    if any(value.tzinfo is None for value in (issued, not_before, not_after)):
        raise TargetAuditError("pre-execution authorization timestamps require offsets")
    if not (issued <= not_before <= datetime.now(timezone.utc) <= not_after):
        raise TargetAuditError("execution is outside the authorized time window")
    if document.get("canonical_spec") != {
        "id": canonical["spec_id"], "sha256": sha256_file(repo / CANONICAL_SPEC_REL),
    }:
        raise TargetAuditError("authorization canonical binding differs")
    source_registry_sha = hashlib.sha256(
        canonical_bytes(canonical_source_hashes(canonical))
    ).hexdigest()
    if document.get("source_registry_sha256") != source_registry_sha:
        raise TargetAuditError("authorization source registry differs")
    modules = document.get("modules")
    if not isinstance(modules, dict) or set(modules) != {"cells", "target", "numerical"}:
        raise TargetAuditError("authorization module registry is incomplete")
    numerical_spec = load_json(repo / NUMERICAL_SPEC_REL)
    if numerical_spec.get("audit_spec_id") != expected_numerical_spec_id(numerical_spec):
        raise TargetAuditError("authorization numerical specification ID is invalid")
    expected_modules = {
        "cells": {
            "typed_spec_id": cell_spec["cell_build_spec_id"],
            "typed_spec_sha256": sha256_file(repo / CELL_SPEC_REL),
            "code_sha256": sha256_file(repo / BUILDER_REL),
        },
        "target": {
            "typed_spec_id": target["target_audit_spec_id"],
            "typed_spec_sha256": sha256_file(repo / TARGET_SPEC_REL),
            "code_sha256": code_sha256,
        },
        "numerical": {
            "typed_spec_id": numerical_spec["audit_spec_id"],
            "typed_spec_sha256": sha256_file(repo / NUMERICAL_SPEC_REL),
            "code_sha256": sha256_file(repo / NUMERICAL_CODE_REL),
        },
    }
    if modules != expected_modules:
        raise TargetAuditError("authorization module registry binding differs")
    expected_own = expected_modules["target"]
    git_run = lambda arguments, text=False: subprocess.run(
        [str(EXPECTED_GIT_PATH), *arguments], cwd=repo,
        env=SANITIZED_GIT_ENVIRONMENT, text=text, capture_output=True, check=False,
    )
    head_result = git_run(["rev-parse", "HEAD"], text=True)
    if head_result.returncode != 0:
        raise TargetAuditError("authorization Git HEAD cannot be resolved")
    head = head_result.stdout.strip()
    implementation = document.get("authorized_implementation_commit")
    if (
        not isinstance(implementation, str)
        or not re.fullmatch(r"[0-9a-f]{40}", implementation)
        or implementation == head
    ):
        raise TargetAuditError("authorization implementation commit is invalid")
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
    worktree_status = git_run(
        ["status", "--porcelain=v1", "--untracked-files=all"], text=True
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
        or worktree_status.returncode != 0
        or worktree_status.stdout != ""
    ):
        raise TargetAuditError(
            "authorization is not the sole file in a separate clean current commit"
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
        "module_key": "target",
        "typed_spec_id": expected_own["typed_spec_id"],
        "typed_spec_sha256": expected_own["typed_spec_sha256"],
        "code_sha256": code_sha256,
        "source_registry_sha256": source_registry_sha,
    }


def canonical_source_hashes(canonical: dict[str, Any]) -> dict[str, str]:
    rows = canonical.get("data", {}).get("sources")
    if not isinstance(rows, list) or not rows:
        raise TargetAuditError("canonical V2 source registry is absent")
    result: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise TargetAuditError("canonical V2 source registry contains a malformed row")
        source_id = row.get("source_id")
        digest = row.get("sha256")
        if not isinstance(source_id, str) or not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
            raise TargetAuditError("canonical V2 source registry contains an invalid entry")
        if source_id in result:
            raise TargetAuditError(f"duplicate canonical source identifier: {source_id}")
        result[source_id] = str(digest)
    return result


def get_pointer(document: dict[str, Any], pointer: str) -> Any:
    if not pointer.startswith("/"):
        raise TargetAuditError(f"invalid JSON pointer in target contract: {pointer}")
    value: Any = document
    for raw in pointer.split("/")[1:]:
        key = raw.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or key not in value:
            raise TargetAuditError(f"contract assertion points to missing field: {pointer}")
        value = value[key]
    return value


def validate_assertions(
    document: dict[str, Any], assertions: list[dict[str, Any]], label: str
) -> dict[str, bool]:
    if not assertions:
        raise TargetAuditError(f"{label} assertions are absent")
    checks: dict[str, bool] = {}
    for row in assertions:
        name = row.get("name")
        pointer = row.get("pointer")
        if not isinstance(name, str) or not isinstance(pointer, str) or "equals" not in row:
            raise TargetAuditError(f"malformed {label} assertion")
        if name in checks:
            raise TargetAuditError(f"duplicate {label} assertion name: {name}")
        observed = get_pointer(document, pointer)
        passed = observed == row["equals"]
        if not passed:
            raise TargetAuditError(
                f"{label} semantic assertion failed: {name} at {pointer}"
            )
        checks[name] = True
    return checks


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise TargetAuditError(f"missing required {label}: {path.name}")


def load_and_validate_specs(repo: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    target_path = repo / TARGET_SPEC_REL
    canonical_path = repo / CANONICAL_SPEC_REL
    cell_path = repo / CELL_SPEC_REL
    numerical_path = repo / NUMERICAL_SPEC_REL
    environment_path = repo / ENVIRONMENT_REL
    for path, label in (
        (target_path, "target-audit specification"),
        (canonical_path, "canonical V2 specification"),
        (cell_path, "Gate-1 cell-build specification"),
        (numerical_path, "numerical-existence analysis specification"),
        (environment_path, "declared SCC environment lock"),
    ):
        require_file(path, label)
    target = load_json(target_path)
    canonical = load_json(canonical_path)
    cells = load_json(cell_path)
    numerical = load_json(numerical_path)
    if target.get("target_audit_spec_id") != expected_target_spec_id(target):
        raise TargetAuditError("target-audit specification identifier is invalid")
    if cells.get("cell_build_spec_id") != expected_cell_spec_id(cells):
        raise TargetAuditError("cell-build specification identifier is invalid")
    if numerical.get("audit_spec_id") != expected_numerical_spec_id(numerical):
        raise TargetAuditError("numerical-existence specification identifier is invalid")
    binding = target.get("contract_binding", {})
    if not isinstance(binding, dict):
        raise TargetAuditError("target audit lacks a contract-binding object")
    canonical_id = canonical.get("spec_id")
    cell_id = cells.get("cell_build_spec_id")
    if not isinstance(canonical_id, str) or not canonical_id.startswith("yaxspec_v1_"):
        raise TargetAuditError("canonical V2 specification identifier is invalid")
    if not isinstance(cell_id, str) or not cell_id.startswith(CELL_SPEC_PREFIX):
        raise TargetAuditError("cell-build specification identifier is not terminal")
    if binding.get("canonical_spec_id") != canonical_id:
        raise TargetAuditError("target audit binds a different canonical specification")
    if binding.get("canonical_spec_sha256") != sha256_file(canonical_path):
        raise TargetAuditError("canonical V2 byte hash changed")
    if binding.get("cell_build_spec_id") != cell_id:
        raise TargetAuditError("target audit binds a different cell-build specification")
    if binding.get("cell_build_spec_sha256") != sha256_file(cell_path):
        raise TargetAuditError("cell-build specification byte hash changed")
    consumer = cells.get("consumer_contract")
    if not isinstance(consumer, dict):
        raise TargetAuditError("cell-build specification lacks a consumer contract")
    if consumer.get("analysis_spec_id") != numerical.get("audit_spec_id"):
        raise TargetAuditError("cell and numerical specifications have different IDs")
    if consumer.get("analysis_spec_sha256") != sha256_file(numerical_path):
        raise TargetAuditError("cell and numerical specification byte hashes differ")
    runtime_contract = cells.get("runtime_contract")
    if not isinstance(runtime_contract, dict):
        raise TargetAuditError("cell-build specification lacks a runtime contract")
    if runtime_contract.get("environment_lock_path") != str(ENVIRONMENT_REL):
        raise TargetAuditError("cell-build environment-lock path differs")
    if runtime_contract.get("environment_lock_sha256") != sha256_file(environment_path):
        raise TargetAuditError("declared SCC environment-lock byte hash changed")
    canonical_checks = validate_assertions(
        canonical, target.get("canonical_assertions", []), "canonical"
    )
    upstream_checks = validate_assertions(
        cells, target.get("upstream_assertions", []), "upstream"
    )
    if len(canonical_checks) < 10 or len(upstream_checks) < 8:
        raise TargetAuditError("target contract does not contain the minimum semantic assertions")
    runtime_locks = cells.get("runtime_code_hashes")
    if not isinstance(runtime_locks, dict) or set(runtime_locks) != {str(BUILDER_REL)}:
        raise TargetAuditError("cell-build runtime code lock set is not exact")
    historical_locks = cells.get("historical_reference_code_hashes")
    if not isinstance(historical_locks, dict) or not historical_locks:
        raise TargetAuditError("cell-build historical-reference lock set is absent")
    for label, locks in (("runtime", runtime_locks), ("historical reference", historical_locks)):
        if not all(re.fullmatch(r"[0-9a-f]{64}", str(value)) for value in locks.values()):
            raise TargetAuditError(f"cell-build {label} code lock contains an invalid hash")
    return target, canonical, cells


def authenticate_code(
    repo: Path, target: dict[str, Any], cell_spec: dict[str, Any] | None = None
) -> dict[str, str]:
    locks = target.get("code_hashes")
    if not isinstance(locks, dict) or not locks:
        raise TargetAuditError("target-audit specification lacks code hash locks")
    observed: dict[str, str] = {}
    for relative, expected in locks.items():
        path = repo / relative
        require_file(path, f"code lock {Path(relative).name}")
        digest = sha256_file(path)
        if digest != expected:
            raise TargetAuditError(f"code hash changed: {relative}")
        observed[relative] = digest
    self_key = str(HERE_REL / "run_exact_target_audit.py")
    if self_key not in observed:
        raise TargetAuditError("target-audit runner is absent from its own code lock")
    if cell_spec is not None:
        builder_key = str(BUILDER_REL)
        runtime_locks = cell_spec["runtime_code_hashes"]
        historical_locks = cell_spec["historical_reference_code_hashes"]
        if observed.get(builder_key) != runtime_locks.get(builder_key):
            raise TargetAuditError("target and cell contracts bind different builder code")
        target_historical = {
            key: value
            for key, value in observed.items()
            if key not in {self_key, builder_key}
        }
        if target_historical != historical_locks:
            raise TargetAuditError(
                "target and cell contracts bind different historical reference code"
            )
    return observed


def authenticate_source_evidence(repo: Path, target: dict[str, Any]) -> dict[str, str]:
    rows = target.get("source_evidence")
    if not isinstance(rows, list) or len(rows) < 5:
        raise TargetAuditError("target-audit specification lacks source-evidence locks")
    observed: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise TargetAuditError("malformed source-evidence lock")
        relative = row.get("path")
        expected = row.get("sha256")
        if not isinstance(relative, str) or not re.fullmatch(r"[0-9a-f]{64}", str(expected)):
            raise TargetAuditError("invalid source-evidence lock")
        if relative in observed:
            raise TargetAuditError(f"duplicate source-evidence path: {relative}")
        path = repo / relative
        require_file(path, f"source evidence {Path(relative).name}")
        digest = sha256_file(path)
        if digest != expected:
            raise TargetAuditError(f"source-evidence hash changed: {relative}")
        observed[relative] = digest
    return observed


def validate_requirement_source(repo: Path, target: dict[str, Any]) -> dict[str, Any]:
    seed = load_json(repo / REQUIREMENT_SEED_REL)
    rows = seed.get("requirements")
    if not isinstance(rows, list):
        raise TargetAuditError("immutable requirements seed has no requirement list")
    matches = [row for row in rows if isinstance(row, dict) and row.get("id") == "T01"]
    if len(matches) != 1:
        raise TargetAuditError("immutable requirements seed does not contain exactly one T01")
    source = matches[0]
    declared = target.get("requirement", {})
    checks = {
        "id": source.get("id") == declared.get("id") == "T01",
        "title": source.get("title") == "Define the mean-ratio estimand and observed estimating data",
        "prompt_section": source.get("prompt_section") == declared.get("prompt_section") == "6.1",
        "acceptance_checks": source.get("acceptance_checks") == declared.get("acceptance_checks"),
        "depends_on": source.get("depends_on") == declared.get("depends_on") == ["G03"],
        "empirical_classification": source.get("empirical") is False,
    }
    failed = sorted(name for name, passed in checks.items() if not passed)
    if failed:
        raise TargetAuditError("T01 requirement contract changed: " + ", ".join(failed))
    return {"status": "PASS_T01_REQUIREMENT_BINDING", "checks": checks}


def support_hash(codes: Iterable[str]) -> str:
    normalized = sorted({str(code).zfill(4) for code in codes})
    payload = "".join(f"{code}\n" for code in normalized)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assignment_payload(assignments: pd.DataFrame) -> bytes:
    lines: list[str] = []
    for row in assignments.sort_values("occ_code", kind="mergesort").itertuples(index=False):
        lines.append(
            f"{str(row.occ_code).zfill(4)}\t{str(row.family)}\t"
            f"{int(row.beta_quintile)}\t{float(row.webb_z).hex()}\n"
        )
    return "".join(lines).encode("utf-8")


def assignment_fingerprint(assignments: pd.DataFrame) -> str:
    return hashlib.sha256(assignment_payload(assignments)).hexdigest()


def month_range(start: str, end: str) -> list[str]:
    start_year, start_month = map(int, start.split("-"))
    end_year, end_month = map(int, end.split("-"))
    result: list[str] = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        result.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return result


def expected_observed_months(canonical: dict[str, Any]) -> list[str]:
    observed = canonical["calendar"]["observed_window"]
    missing = set(canonical["calendar"]["missing_handling"]["missing_months"])
    return [month for month in month_range(*observed["range"]) if month not in missing]


def _require_int_count(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TargetAuditError(f"{label} must be a nonnegative physical integer count")
    return value


def _require_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TargetAuditError(f"{label} must be a JSON object")
    return value


def _require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise TargetAuditError(f"{label} must be an exact SHA-256 digest")
    return value


def _require_finite_float(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise TargetAuditError(f"{label} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise TargetAuditError(f"{label} must be a finite number") from exc
    if not math.isfinite(result):
        raise TargetAuditError(f"{label} must be a finite number")
    return result


def _require_exact_hash_map(
    observed: Any, expected: dict[str, str], label: str
) -> dict[str, str]:
    value = _require_mapping(observed, label)
    for key, digest in expected.items():
        _require_sha256(digest, f"expected {label}.{key}")
    if value != expected:
        raise TargetAuditError(f"{label} differs from its exact authenticated map")
    return {str(key): str(digest) for key, digest in value.items()}


def _require_exact_integer_map(
    observed: Any, expected_sources: list[str], label: str
) -> dict[str, int]:
    value = _require_mapping(observed, label)
    if set(value) != set(expected_sources):
        raise TargetAuditError(f"{label} does not contain the exact two source IDs")
    return {
        source: _require_int_count(value[source], f"{label}.{source}")
        for source in expected_sources
    }


def authenticate_producer_sources_and_authorization(
    receipt: dict[str, Any], canonical: dict[str, Any]
) -> dict[str, Any]:
    canonical_sources = canonical_source_hashes(canonical)
    if set(UNREAD_CANONICAL_SOURCE_IDS) - set(canonical_sources):
        raise TargetAuditError("canonical registry lacks the declared unread source")
    authenticated_sources = {
        key: value
        for key, value in canonical_sources.items()
        if key not in UNREAD_CANONICAL_SOURCE_IDS
    }
    lookup_sources = {
        key: canonical_sources[key] for key in LOOKUP_AND_AUTHORIZATION_SOURCE_IDS
    }
    _require_exact_hash_map(receipt.get("source_hashes"), canonical_sources, "source_hashes")
    _require_exact_hash_map(
        receipt.get("authenticated_source_hashes"),
        authenticated_sources,
        "authenticated_source_hashes",
    )
    if receipt.get("unread_canonical_source_ids") != UNREAD_CANONICAL_SOURCE_IDS:
        raise TargetAuditError("unread canonical source declaration is not exact")
    _require_exact_hash_map(
        receipt.get("lookup_and_bridge_hashes"),
        lookup_sources,
        "lookup_and_bridge_hashes",
    )
    authorization = {
        "status": "PASS_AUTHORIZATION_CHAIN",
        "checks": {
            "status": True,
            "frozen_tag": True,
            "microdata_sha256": True,
        },
        "repair_source_bound_by_canonical_v2": True,
    }
    if receipt.get("authorization") != authorization:
        raise TargetAuditError("producer authorization chain or its subchecks differ")
    return {
        "canonical_source_count": len(canonical_sources),
        "authenticated_source_count": len(authenticated_sources),
        "unread_canonical_source_ids": list(UNREAD_CANONICAL_SOURCE_IDS),
        "authorization_status": authorization["status"],
    }


def authenticate_producer_runtime(
    receipt: dict[str, Any], cell_spec: dict[str, Any]
) -> dict[str, Any]:
    contract = _require_mapping(cell_spec.get("runtime_contract"), "runtime contract")
    payload = _require_mapping(contract.get("runtime_payload"), "runtime payload")
    payload_sha = _require_sha256(
        contract.get("runtime_payload_sha256"), "runtime payload SHA-256"
    )
    if hashlib.sha256(canonical_bytes(payload)).hexdigest() != payload_sha:
        raise TargetAuditError("cell-spec runtime payload hash is invalid")
    contract_sha = hashlib.sha256(canonical_bytes(contract)).hexdigest()
    environment_path = contract.get("environment_lock_path")
    environment_sha = _require_sha256(
        contract.get("environment_lock_sha256"), "environment-lock SHA-256"
    )
    command_template = contract.get("command_template")
    if not isinstance(environment_path, str) or not environment_path:
        raise TargetAuditError("runtime environment-lock path is absent")
    if not isinstance(command_template, str) or not command_template:
        raise TargetAuditError("runtime command template is absent")
    expected_top = {
        "command_template": command_template,
        "runtime_environment_lock_path": environment_path,
        "runtime_environment_lock_sha256": environment_sha,
        "runtime_contract_sha256": contract_sha,
        "runtime_payload_sha256": payload_sha,
    }
    for field, expected in expected_top.items():
        if receipt.get(field) != expected:
            raise TargetAuditError(f"producer runtime authentication failed: {field}")

    runtime = _require_mapping(
        receipt.get("runtime_authentication"), "runtime_authentication"
    )
    if set(runtime) != EXPECTED_RUNTIME_AUTHENTICATION_KEYS:
        raise TargetAuditError("runtime authentication field set is not exact")
    expected_runtime_fields = {
        "status": "AUTHENTICATED_DECLARED_RUNTIME",
        "environment_lock_path": environment_path,
        "environment_lock_sha256": environment_sha,
        "runtime_contract_sha256": contract_sha,
        "runtime_payload": payload,
        "runtime_payload_sha256": payload_sha,
        "command_template": command_template,
        "kernel_release_rule": (
            "recorded but nonbinding because SCC compute-node kernel patch levels may differ"
        ),
    }
    for field, expected in expected_runtime_fields.items():
        if runtime.get(field) != expected:
            raise TargetAuditError(f"nested producer runtime authentication failed: {field}")
    observed = _require_mapping(runtime.get("observed"), "runtime observed payload")
    if set(observed) != EXPECTED_RUNTIME_OBSERVED_KEYS:
        raise TargetAuditError("observed SCC runtime field set is not exact")
    packages = _require_mapping(payload.get("packages"), "runtime package payload")
    libc = _require_mapping(payload.get("libc"), "runtime libc payload")
    expected_observed = {
        "python": payload.get("python_version"),
        "python_implementation": payload.get("python_implementation"),
        "python_compiler": payload.get("python_compiler"),
        "numpy": packages.get("numpy"),
        "pandas": packages.get("pandas"),
        "pytest": packages.get("pytest"),
        "scipy": packages.get("scipy"),
        "kernel_system": contract.get("expected_runtime", {}).get("kernel_system"),
        "machine": payload.get("architecture"),
        "libc_name": libc.get("name"),
        "libc": libc.get("version"),
    }
    for field, expected in expected_observed.items():
        if not isinstance(expected, str) or not expected or observed.get(field) != expected:
            raise TargetAuditError(f"observed SCC runtime differs from contract: {field}")
    if not isinstance(observed.get("kernel_release"), str) or not observed["kernel_release"]:
        raise TargetAuditError("observed SCC kernel release was not recorded")

    runtime_code = _require_mapping(cell_spec.get("runtime_code_hashes"), "runtime code locks")
    historical_code = _require_mapping(
        cell_spec.get("historical_reference_code_hashes"),
        "historical reference code locks",
    )
    _require_exact_hash_map(receipt.get("runtime_code_hashes"), runtime_code, "runtime_code_hashes")
    _require_exact_hash_map(
        receipt.get("historical_reference_code_hashes"),
        historical_code,
        "historical_reference_code_hashes",
    )
    builder_key = str(BUILDER_REL)
    if set(runtime_code) != {builder_key}:
        raise TargetAuditError("producer runtime-code map does not contain exactly the builder")
    builder_sha = _require_sha256(runtime_code[builder_key], "builder code SHA-256")
    if receipt.get("builder_code_sha256") != builder_sha:
        raise TargetAuditError("producer builder code hash differs from the cell contract")
    transitive = _require_mapping(
        cell_spec.get("runtime_transitive_code_fingerprint"),
        "runtime transitive-code fingerprint",
    )
    transitive_sha = _require_sha256(
        transitive.get("sha256"), "runtime transitive-code SHA-256"
    )
    if transitive.get("map") != {} or transitive_sha != hashlib.sha256(b"{}").hexdigest():
        raise TargetAuditError("producer runtime transitive-code map is not explicitly empty")
    if receipt.get("builder_transitive_code_sha256") != transitive_sha:
        raise TargetAuditError("producer transitive-code hash differs from the cell contract")
    expected_algorithm = (
        "SHA-256 of canonical JSON runtime path-to-hash map excluding the builder; "
        "the empty map proves that historical reference code is not imported at runtime"
    )
    if receipt.get("builder_transitive_code_sha256_algorithm") != expected_algorithm:
        raise TargetAuditError("producer transitive-code algorithm declaration differs")
    return {
        "status": runtime["status"],
        "runtime_payload": payload,
        "runtime_payload_sha256": payload_sha,
        "environment_lock_path": environment_path,
        "environment_lock_sha256": environment_sha,
        "runtime_contract_sha256": contract_sha,
        "observed_kernel_system": observed["kernel_system"],
        "observed_kernel_release": observed["kernel_release"],
        "builder_code_sha256": builder_sha,
        "builder_transitive_code_sha256": transitive_sha,
    }


def authenticate_producer_execution_entry(
    receipt: dict[str, Any],
    cell_spec: dict[str, Any],
    canonical: dict[str, Any],
    current_authorization: dict[str, Any],
) -> dict[str, Any]:
    """Authenticate the cell runner's non-caller-supplied entry attestations."""
    binding = _require_mapping(
        receipt.get("execution_command_binding"), "execution_command_binding"
    )
    if set(binding) != {
        "schema_version", "status", "module_key", "run_id",
        "scheduler_jobnumber", "sanitized_argv", "sanitized_argv_sha256",
        "binding_sha256",
    }:
        raise TargetAuditError("producer execution-command field set is not exact")
    job = binding.get("scheduler_jobnumber")
    run_id = binding.get("run_id")
    expected_argv = [
        "<YAX_PYTHON_BIN>", "-I",
        str(V3_REL / "gate1_cells/run_gate1_cells.py"),
        "--repo-root", "<YAX_REPO_ROOT>",
        "--microdata", "<INPUT:ipums_cps_extract_9_wide>",
        "--repair-microdata", "<INPUT:ipums_cps_extract_11_march_basic_repair>",
        "--output-parent", "<YAX_V3_RUN_ROOT>",
    ]
    binding_core = {
        key: binding[key] for key in binding if key != "binding_sha256"
    }
    if (
        binding.get("schema_version") != COMMAND_BINDING_SCHEMA
        or binding.get("status") != COMMAND_BINDING_STATUS
        or binding.get("module_key") != "cells"
        or not isinstance(job, str)
        or JOB_ID_PATTERN.fullmatch(job) is None
        or run_id != f"gate1_cells_sge_{job}"
        or binding.get("sanitized_argv") != expected_argv
        or binding.get("sanitized_argv_sha256")
        != hashlib.sha256(canonical_bytes(expected_argv)).hexdigest()
        or binding.get("binding_sha256")
        != hashlib.sha256(canonical_bytes(binding_core)).hexdigest()
    ):
        raise TargetAuditError("producer execution-command binding is invalid")

    runtime = _require_mapping(
        receipt.get("execution_runtime_authentication"),
        "execution_runtime_authentication",
    )
    expected_runtime = {
        "status": "AUTHENTICATED_ISOLATED_PINNED_EXECUTABLES",
        "python_invocation": "<YAX_PYTHON_BIN>",
        "python_resolved_executable_sha256": EXPECTED_PYTHON_RESOLVED_SHA256,
        "python_version": "3.13.8",
        "isolated_mode": True,
        "ignore_environment": True,
        "no_user_site": True,
        "safe_path": True,
        "git_invocation": "<YAX_GIT_BIN>",
        "git_resolved_executable_sha256": EXPECTED_GIT_SHA256,
        "git_version": EXPECTED_GIT_VERSION,
        "import_affecting_environment_absent": True,
    }
    if runtime != expected_runtime:
        raise TargetAuditError("producer isolated-runtime authentication differs")

    producer_authorization = _require_mapping(
        receipt.get("pre_execution_authorization"),
        "pre_execution_authorization",
    )
    common_fields = (
        "schema_version", "status", "authorization_id",
        "authorization_file_sha256", "authorization_git_commit",
        "authorized_implementation_commit", "issued_at_utc",
        "not_before_utc", "not_after_utc", "source_registry_sha256",
    )
    if any(field not in current_authorization for field in common_fields):
        raise TargetAuditError("current authorization summary is incomplete")
    expected_authorization = {
        **{field: current_authorization[field] for field in common_fields},
        "module_key": "cells",
        "typed_spec_id": cell_spec["cell_build_spec_id"],
        "typed_spec_sha256": sha256_file(Path(__file__).resolve().parents[4] / CELL_SPEC_REL),
        "code_sha256": cell_spec["runtime_code_hashes"][str(BUILDER_REL)],
    }
    if producer_authorization != expected_authorization:
        raise TargetAuditError("producer pre-execution authorization differs")
    try:
        generated = datetime.fromisoformat(str(receipt["generated_at_utc"]))
        not_before = datetime.fromisoformat(str(producer_authorization["not_before_utc"]))
        not_after = datetime.fromisoformat(str(producer_authorization["not_after_utc"]))
    except (TypeError, ValueError) as exc:
        raise TargetAuditError("producer authorization timing is malformed") from exc
    if (
        generated.tzinfo is None
        or not_before.tzinfo is None
        or not_after.tzinfo is None
        or not (not_before <= generated <= not_after)
    ):
        raise TargetAuditError("producer generation falls outside its authorization window")
    expected_source_registry = hashlib.sha256(
        canonical_bytes(canonical_source_hashes(canonical))
    ).hexdigest()
    if producer_authorization["source_registry_sha256"] != expected_source_registry:
        raise TargetAuditError("producer authorization source registry differs")
    return {
        "command_binding_sha256": binding["binding_sha256"],
        "scheduler_jobnumber": job,
        "runtime_status": runtime["status"],
        "authorization_id": producer_authorization["authorization_id"],
    }


def verify_producer_git_checkout(
    repo: Path,
    receipt: dict[str, Any],
    expected_hashes: dict[str, str],
    required_ancestor: str,
) -> dict[str, Any]:
    """Resolve producer provenance against Git objects and the consuming checkout."""

    def run(arguments: list[str], *, text: bool = True) -> subprocess.CompletedProcess[Any]:
        return subprocess.run(
            [str(EXPECTED_GIT_PATH), *arguments],
            cwd=repo,
            env=SANITIZED_GIT_ENVIRONMENT,
            capture_output=True,
            text=text,
            check=False,
        )

    commit = receipt["git_commit"]
    tree = receipt["git_tree"]
    exists = run(["cat-file", "-e", f"{commit}^{{commit}}"])
    if exists.returncode != 0:
        raise TargetAuditError("producer Git commit object does not exist")
    actual_tree = run(["rev-parse", f"{commit}^{{tree}}"])
    if actual_tree.returncode != 0 or actual_tree.stdout.strip() != tree:
        raise TargetAuditError("producer Git tree does not match its commit object")
    ancestor = run(["merge-base", "--is-ancestor", required_ancestor, commit])
    if ancestor.returncode != 0:
        raise TargetAuditError("required ancestor is not an ancestor of the producer commit")
    for relative, expected in expected_hashes.items():
        blob = run(["show", f"{commit}:{relative}"], text=False)
        if blob.returncode != 0:
            raise TargetAuditError(f"producer commit lacks declared artifact: {relative}")
        if hashlib.sha256(blob.stdout).hexdigest() != expected:
            raise TargetAuditError(f"producer committed blob hash differs: {relative}")

    head = run(["rev-parse", "HEAD"])
    head_tree = run(["rev-parse", "HEAD^{tree}"])
    if head.returncode != 0 or head.stdout.strip() != commit:
        raise TargetAuditError("consuming checkout HEAD differs from the producer commit")
    if head_tree.returncode != 0 or head_tree.stdout.strip() != tree:
        raise TargetAuditError("consuming checkout tree differs from the producer tree")
    status = run(["status", "--porcelain=v1", "--untracked-files=all"])
    if status.returncode != 0:
        raise TargetAuditError("could not inspect the consuming Git checkout")
    if status.stdout != "":
        raise TargetAuditError("consuming Git checkout is not clean")
    return {
        "commit_object_exists": True,
        "commit_tree_verified": True,
        "required_ancestor_verified": True,
        "committed_blob_hashes_verified": True,
        "consuming_head_matches": True,
        "consuming_tree_matches": True,
        "consuming_worktree_clean": True,
    }


def authenticate_producer_git(
    receipt: dict[str, Any], cell_spec: dict[str, Any], repo: Path
) -> dict[str, Any]:
    contract = _require_mapping(cell_spec.get("git_contract"), "producer Git contract")
    if contract.get("clean_worktree_required") is not True:
        raise TargetAuditError("producer Git contract does not require a clean worktree")
    if contract.get("live_files_must_equal_head_blobs") is not True:
        raise TargetAuditError("producer Git contract does not bind live files to Git blobs")
    if contract.get("runtime_head_and_tree_recorded") is not True:
        raise TargetAuditError("producer Git contract does not require HEAD/tree recording")
    required_ancestor = contract.get("required_ancestor_commit")
    if not isinstance(required_ancestor, str) or not re.fullmatch(
        r"[0-9a-f]{40}", required_ancestor
    ):
        raise TargetAuditError("producer Git required ancestor is invalid")
    committed_paths = contract.get("committed_paths")
    exact_paths = [
        str(BUILDER_REL),
        str(CELL_SPEC_REL),
        str(NUMERICAL_SPEC_REL),
        str(ENVIRONMENT_REL),
    ]
    if not isinstance(committed_paths, list) or set(committed_paths) != set(exact_paths):
        raise TargetAuditError("producer Git committed-path set is not exact")
    expected_hashes = {
        str(BUILDER_REL): cell_spec["runtime_code_hashes"][str(BUILDER_REL)],
        str(CELL_SPEC_REL): receipt.get("cell_build_spec_sha256"),
        str(NUMERICAL_SPEC_REL): cell_spec.get("consumer_contract", {}).get(
            "analysis_spec_sha256"
        ),
        str(ENVIRONMENT_REL): cell_spec["runtime_contract"].get(
            "environment_lock_sha256"
        ),
    }
    for path, digest in expected_hashes.items():
        _require_sha256(digest, f"producer committed hash for {path}")
    _require_exact_hash_map(
        receipt.get("git_committed_artifact_hashes"),
        expected_hashes,
        "git_committed_artifact_hashes",
    )
    if receipt.get("git_status") != "PASS_COMMITTED_CLEAN_WORKTREE":
        raise TargetAuditError("producer Git status is not the declared clean state")
    if receipt.get("git_required_ancestor_commit") != required_ancestor:
        raise TargetAuditError("producer Git ancestor differs from its contract")
    if receipt.get("git_worktree_clean") is not True:
        raise TargetAuditError("producer receipt does not certify a clean worktree")
    if receipt.get("git_porcelain_sha256") != hashlib.sha256(b"").hexdigest():
        raise TargetAuditError("producer Git porcelain was not empty")
    commit = receipt.get("git_commit")
    tree = receipt.get("git_tree")
    if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise TargetAuditError("producer Git commit identifier is malformed")
    if not isinstance(tree, str) or not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise TargetAuditError("producer Git tree identifier is malformed")
    object_checks = verify_producer_git_checkout(
        repo, receipt, expected_hashes, required_ancestor
    )
    return {
        "status": receipt["git_status"],
        "commit": commit,
        "tree": tree,
        "required_ancestor_commit": required_ancestor,
        "committed_artifact_hashes": expected_hashes,
        "object_and_checkout_checks": object_checks,
    }


def _reported_float_matches(observed: Any, expected: float, label: str) -> float:
    value = _require_finite_float(observed, label)
    tolerance = 1e-12 * max(abs(expected), 1.0)
    if abs(value - expected) > tolerance:
        raise TargetAuditError(f"{label} does not reconcile")
    return value


def authenticate_producer_accounting(
    receipt: dict[str, Any], target: dict[str, Any], cell_spec: dict[str, Any]
) -> dict[str, Any]:
    raw = _require_mapping(
        receipt.get("six_field_cell_build_checks"), "six_field_cell_build_checks"
    )
    route = _require_mapping(receipt.get("route_checks"), "route_checks")
    weight = _require_mapping(receipt.get("weight_once_checks"), "weight_once_checks")
    contract = _require_mapping(
        target.get("physical_row_accounting"), "physical-row accounting contract"
    )
    expected_sources = contract.get("source_ids")
    if expected_sources != RAW_SOURCE_IDS or raw.get("source_ids") != expected_sources:
        raise TargetAuditError("six-field producer source order is not exact")
    if contract.get("partition_integer_fields") != PARTITION_COUNT_FIELDS:
        raise TargetAuditError("target partition-count contract is not exact")
    runtime_fields = contract.get("runtime_raw_fields")
    if raw.get("runtime_raw_fields") != runtime_fields:
        raise TargetAuditError("six-field receipt reports a different raw-field universe")

    count_fields = contract.get("upstream_integer_fields")
    if not isinstance(count_fields, list) or not count_fields:
        raise TargetAuditError("target physical-count field registry is absent")
    for field in count_fields:
        if field not in raw:
            raise TargetAuditError(f"aggregate receipt omits physical row count: {field}")
        _require_int_count(raw[field], f"six_field_cell_build_checks.{field}")

    physical_by_source = _require_exact_integer_map(
        raw.get("physical_rows_read_by_source"),
        expected_sources,
        "physical_rows_read_by_source",
    )
    eligible_by_source = _require_exact_integer_map(
        raw.get("eligible_employed_age_22_65_records_by_source"),
        expected_sources,
        "eligible_employed_age_22_65_records_by_source",
    )
    physical_total = raw["physical_rows_read_total"]
    eligible_total = raw["eligible_employed_age_22_65_records_total"]
    if physical_total <= 0 or physical_total != sum(physical_by_source.values()):
        raise TargetAuditError("physical source-row total does not reconcile")
    if eligible_total <= 0 or eligible_total != sum(eligible_by_source.values()):
        raise TargetAuditError("eligible source-record total does not reconcile")

    partition_maps: dict[str, dict[str, int]] = {}
    for field in PARTITION_COUNT_FIELDS:
        total = _require_int_count(raw.get(field), f"six_field_cell_build_checks.{field}")
        values = _require_exact_integer_map(
            raw.get(f"{field}_by_source"),
            expected_sources,
            f"{field}_by_source",
        )
        if total != sum(values.values()):
            raise TargetAuditError(f"{field} does not reconcile to its by-source map")
        partition_maps[field] = values

    recomputed_by_source: dict[str, dict[str, bool]] = {}
    for source in expected_sources:
        value = lambda field: partition_maps[field][source]
        identities = {
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
        if not all(identities.values()):
            failed = sorted(key for key, passed in identities.items() if not passed)
            raise TargetAuditError(
                f"source-record reconciliation failed for {source}: {', '.join(failed)}"
            )
        recomputed_by_source[source] = identities

    recomputed_totals = {
        "physical_total_equals_source_sum": physical_total
        == sum(physical_by_source.values()),
        "eligible_total_equals_source_sum": eligible_total
        == sum(eligible_by_source.values()),
        "eligible_equals_invalid_plus_valid": eligible_total
        == raw["invalid_raw_occ_records"] + raw["valid_raw_occ_records"],
        "valid_equals_early_plus_current": raw["valid_raw_occ_records"]
        == raw["early_valid_source_records"] + raw["current_valid_source_records"],
        "early_equals_matched_plus_unmatched": raw["early_valid_source_records"]
        == raw["early_matched_source_records"] + raw["early_unmatched_source_records"],
        "early_descendants_partition_by_route_weight": raw[
            "early_expanded_route_descendants"
        ]
        == raw["early_fractional_route_contributions"]
        + raw["early_unit_route_contributions"]
        + raw["early_zero_mass_route_contributions"],
        "direct_contributions_equal_current_valid_records": raw[
            "current_direct_route_contributions"
        ]
        == raw["current_valid_source_records"],
        "routed_contributions_equal_descendants_plus_direct": raw[
            "routed_contribution_rows"
        ]
        == raw["early_expanded_route_descendants"]
        + raw["current_direct_route_contributions"],
    }
    if not all(recomputed_totals.values()):
        failed = sorted(key for key, passed in recomputed_totals.items() if not passed)
        raise TargetAuditError("total record reconciliation failed: " + ", ".join(failed))
    if route.get("record_identities_by_source") != recomputed_by_source:
        raise TargetAuditError("producer source-record identity receipt is not exact")
    if route.get("total_record_identities") != recomputed_totals:
        raise TargetAuditError("producer total-record identity receipt is not exact")

    repair_source = "ipums_cps_extract_11_march_basic_repair"
    wide_source = "ipums_cps_extract_9_wide"
    if raw.get("repair_observed_months") != MARCH_REPAIR_MONTHS:
        raise TargetAuditError("repair source does not contain exactly the five March months")
    if raw["repair_eligible_employed_age_22_65_records"] != eligible_by_source[repair_source]:
        raise TargetAuditError("repair eligible count differs from its source component")
    if raw["repair_eligible_employed_age_22_65_records"] > physical_by_source[repair_source]:
        raise TargetAuditError("repair eligible count exceeds repair physical rows")
    replaced = raw["wide_march_rows_explicitly_replaced"]
    replaced_positive = raw["wide_march_positive_weight_rows_explicitly_replaced"]
    if replaced <= 0 or replaced > physical_by_source[wide_source]:
        raise TargetAuditError("wide March replacement count is invalid")
    # The authenticated wide source contains March ASEC samples in these five
    # months.  Every one of those superseded records has WTFINL == 0; the
    # separately authenticated Basic-month source supplies the positive-weight
    # replacement.  Requiring a positive subset here reverses the documented
    # source contract and rejects the genuine producer receipt.  Require the
    # known zero exactly so a future or mismatched source cannot pass silently.
    expected_replaced_positive = contract.get(
        "wide_march_positive_weight_rows_expected"
    )
    if expected_replaced_positive != 0:
        raise TargetAuditError(
            "target contract does not bind the authenticated zero-weight March fact"
        )
    if replaced_positive != expected_replaced_positive:
        raise TargetAuditError(
            "positive-weight replaced-row count differs from the authenticated wide source"
        )
    if eligible_by_source[wide_source] > physical_by_source[wide_source] - replaced:
        raise TargetAuditError("wide eligible records exceed nonreplaced physical rows")
    if raw["routed_rows"] != raw["routed_contribution_rows"]:
        raise TargetAuditError("routed-row compatibility identity failed")
    if raw["aggregate_rows"] > raw["routed_contribution_rows"]:
        raise TargetAuditError("routed aggregates exceed routed contribution rows")
    if raw["observed_month_count"] != cell_spec["grid_contract"]["observed_month_count"]:
        raise TargetAuditError("routed month count differs from the grid contract")

    source_reconciliation = _require_mapping(
        route.get("source_stock_reconciliation"), "source stock reconciliation"
    )
    if set(source_reconciliation) != set(expected_sources):
        raise TargetAuditError("source stock reconciliation source set is not exact")
    stock_base_fields = [
        "raw_early_valid_stock",
        "raw_early_matched_stock",
        "expected_early_routed_stock",
        "actual_early_routed_stock",
        "raw_current_valid_stock",
        "actual_current_direct_stock",
    ]
    expected_source_stock_keys = set(stock_base_fields) | {
        "early_absolute_gap",
        "early_relative_gap",
        "current_absolute_gap",
        "current_relative_gap",
        "unmatched_early_stock",
        "route_conservation_pass",
    }
    parsed_source_stocks: dict[str, dict[str, float]] = {}
    for source, untyped in source_reconciliation.items():
        values = _require_mapping(untyped, f"source stock reconciliation {source}")
        if set(values) != expected_source_stock_keys:
            raise TargetAuditError(f"source stock field set is not exact for {source}")
        parsed = {
            field: _require_finite_float(values.get(field), f"{source}.{field}")
            for field in stock_base_fields
        }
        early_gap = parsed["actual_early_routed_stock"] - parsed[
            "expected_early_routed_stock"
        ]
        current_gap = parsed["actual_current_direct_stock"] - parsed[
            "raw_current_valid_stock"
        ]
        early_scale = max(abs(parsed["expected_early_routed_stock"]), 1.0)
        current_scale = max(abs(parsed["raw_current_valid_stock"]), 1.0)
        unmatched = parsed["raw_early_valid_stock"] - parsed["raw_early_matched_stock"]
        _reported_float_matches(values.get("early_absolute_gap"), early_gap, f"{source}.early_absolute_gap")
        _reported_float_matches(values.get("early_relative_gap"), early_gap / early_scale, f"{source}.early_relative_gap")
        _reported_float_matches(values.get("current_absolute_gap"), current_gap, f"{source}.current_absolute_gap")
        _reported_float_matches(values.get("current_relative_gap"), current_gap / current_scale, f"{source}.current_relative_gap")
        _reported_float_matches(values.get("unmatched_early_stock"), unmatched, f"{source}.unmatched_early_stock")
        if unmatched < -1e-9 or abs(early_gap) / early_scale >= 1e-10 or abs(current_gap) / current_scale >= 1e-10:
            raise TargetAuditError(f"source stock conservation failed for {source}")
        if values.get("route_conservation_pass") is not True:
            raise TargetAuditError(f"source route-conservation flag failed for {source}")
        parsed_source_stocks[source] = parsed

    for field in stock_base_fields:
        expected = sum(values[field] for values in parsed_source_stocks.values())
        _reported_float_matches(route.get(field), expected, f"route_checks.{field}")
    top_expected_early = _require_finite_float(
        route.get("expected_early_routed_stock"), "route expected early stock"
    )
    top_raw_current = _require_finite_float(
        route.get("raw_current_valid_stock"), "route current valid stock"
    )
    top_early_gap = _require_finite_float(
        route.get("actual_early_routed_stock"), "route actual early stock"
    ) - top_expected_early
    top_current_gap = _require_finite_float(
        route.get("actual_current_direct_stock"), "route actual current stock"
    ) - top_raw_current
    top_early_scale = max(abs(top_expected_early), 1.0)
    top_current_scale = max(abs(top_raw_current), 1.0)
    top_unmatched = _require_finite_float(
        route.get("raw_early_valid_stock"), "route raw early stock"
    ) - _require_finite_float(
        route.get("raw_early_matched_stock"), "route matched early stock"
    )
    _reported_float_matches(route.get("early_absolute_gap"), top_early_gap, "route early absolute gap")
    _reported_float_matches(route.get("early_relative_gap"), top_early_gap / top_early_scale, "route early relative gap")
    _reported_float_matches(route.get("current_absolute_gap"), top_current_gap, "route current absolute gap")
    _reported_float_matches(route.get("current_relative_gap"), top_current_gap / top_current_scale, "route current relative gap")
    _reported_float_matches(route.get("unmatched_early_stock"), top_unmatched, "route unmatched early stock")
    if top_unmatched < -1e-9 or abs(top_early_gap) / top_early_scale >= 1e-10 or abs(top_current_gap) / top_current_scale >= 1e-10:
        raise TargetAuditError("total route stock conservation failed")
    if route.get("route_conservation_pass") is not True:
        raise TargetAuditError("total route-conservation flag failed")
    bridge_count = _require_int_count(route.get("bridge_source_count"), "bridge source count")
    bridge_min = _require_finite_float(route.get("bridge_mass_min"), "bridge mass minimum")
    bridge_max = _require_finite_float(route.get("bridge_mass_max"), "bridge mass maximum")
    if bridge_count <= 0 or abs(bridge_min - 1.0) >= 1e-10 or abs(bridge_max - 1.0) >= 1e-10:
        raise TargetAuditError("bridge route-mass contract failed")
    expected_definitions = {
        "physical_rows": "integer input-file records before filtering",
        "eligible_records": "integer employed age-22-through-65 positive-weight source records after explicit March replacement and before occupation routing",
        "expanded_route_descendants": "integer early-period source-to-destination bridge rows after matching; not respondents",
        "fractional_route_contributions": "expanded early bridge rows with route weight strictly between zero and one",
        "aggregate_rows": "unique occupation-month-age-route cells after summing routed contributions",
    }
    if route.get("record_count_definitions") != expected_definitions:
        raise TargetAuditError("producer record-count definitions differ")

    required_weight = {
        "status": "PASS_WEIGHT_ONCE",
        "weight_application_count": 1,
        "survey_weight_field": "WTFINL",
        "route_weight_is_allocation_not_second_survey_weight": True,
        "output_applies_no_additional_weight": True,
        "independent_aggregation_max_absolute_gap": 0.0,
        "rows": cell_spec["grid_contract"]["expected_rows"],
    }
    for field, expected in required_weight.items():
        if weight.get(field) != expected:
            raise TargetAuditError(f"weight-once receipt check failed: {field}")
    if receipt.get("weight_application_count") != 1:
        raise TargetAuditError("producer top-level weight count differs from one")
    for field in ("young_stock", "older_stock"):
        if _require_finite_float(weight.get(field), f"weight-once {field}") < 0:
            raise TargetAuditError(f"weight-once {field} is negative")
    return {
        "physical_rows_read_total": physical_total,
        "physical_rows_read_by_source": physical_by_source,
        "eligible_employed_age_22_65_records_total": eligible_total,
        "eligible_employed_age_22_65_records_by_source": eligible_by_source,
        "repair_observed_months": list(MARCH_REPAIR_MONTHS),
        "route_conservation_pass": True,
        "weight_application_count": 1,
    }


def authenticate_aggregate_receipt(
    receipt_path: Path,
    cells_path: Path,
    target: dict[str, Any],
    canonical: dict[str, Any],
    cell_spec: dict[str, Any],
    repo: Path,
    current_authorization: dict[str, Any],
) -> dict[str, Any]:
    require_file(receipt_path, "aggregate-cell receipt")
    require_file(cells_path, "aggregate-cell file")
    if receipt_path.parent.resolve() != cells_path.parent.resolve():
        raise TargetAuditError("aggregate cells and their receipt must share one authenticated leaf")
    receipt = load_json(receipt_path)
    assert_sanitized(receipt)
    consumer = _require_mapping(cell_spec.get("consumer_contract"), "consumer contract")
    analysis_id = consumer.get("analysis_spec_id")
    analysis_sha = consumer.get("analysis_spec_sha256")
    if not isinstance(analysis_id, str) or not analysis_id.startswith("yaxnumspec_v1_"):
        raise TargetAuditError("cell producer is not bound to a terminal numerical spec ID")
    _require_sha256(analysis_sha, "numerical analysis specification SHA-256")
    expected = {
        "schema_version": EXPECTED_UPSTREAM_RECEIPT_SCHEMA,
        "status": EXPECTED_UPSTREAM_STATUS,
        "aggregate_schema_version": EXPECTED_AGGREGATE_SCHEMA,
        "canonical_spec_id": canonical["spec_id"],
        "canonical_spec_sha256": sha256_file(repo / CANONICAL_SPEC_REL),
        "analysis_spec_id": analysis_id,
        "analysis_spec_sha256": analysis_sha,
        "cell_build_spec_id": cell_spec["cell_build_spec_id"],
        "cell_build_spec_sha256": sha256_file(repo / CELL_SPEC_REL),
        "cells_filename": cells_path.name,
        "cells_sha256": sha256_file(cells_path),
    }
    for field, value in expected.items():
        if receipt.get(field) != value:
            raise TargetAuditError(f"aggregate receipt authentication failed: {field}")
    if cells_path.name != cell_spec["output_contract"]["cells_filename"]:
        raise TargetAuditError("aggregate-cell filename differs from the cell-build contract")
    if not isinstance(receipt.get("generated_at_utc"), str):
        raise TargetAuditError("producer generation timestamp is absent")
    try:
        generated = datetime.fromisoformat(receipt["generated_at_utc"])
    except ValueError as exc:
        raise TargetAuditError("producer generation timestamp is malformed") from exc
    if generated.tzinfo is None:
        raise TargetAuditError("producer generation timestamp lacks a UTC offset")
    source_summary = authenticate_producer_sources_and_authorization(receipt, canonical)
    runtime_summary = authenticate_producer_runtime(receipt, cell_spec)
    execution_entry_summary = authenticate_producer_execution_entry(
        receipt, cell_spec, canonical, current_authorization
    )
    git_summary = authenticate_producer_git(receipt, cell_spec, repo)
    if receipt.get("balanced_grid_complete") is not True:
        raise TargetAuditError("aggregate receipt does not certify a complete balanced grid")
    if receipt.get("contains_resolved_private_paths") is not False:
        raise TargetAuditError("aggregate receipt does not deny resolved private paths")

    required_freshness = {
        "new_output_leaf_required": True,
        "output_outside_repository": True,
        "atomic_directory_publish": True,
        "row_level_microdata_written": False,
        "historical_preperiod_cells_read": False,
        "historical_reference_code_imported_at_runtime": False,
        "only_six_canonical_raw_fields_read": True,
        "private_paths_persisted": False,
        "credentials_persisted": False,
    }
    if receipt.get("freshness_and_security") != required_freshness:
        raise TargetAuditError("aggregate security/freshness field set or value differs")

    raw_columns = _require_mapping(receipt.get("raw_column_contract"), "raw_column_contract")
    expected_raw_keys = {
        "runtime_fields",
        "required_columns_present",
        "source_column_counts",
        "canonical_v2_variable_universe_parity",
        "rejected_inherited_helper_fields",
    }
    if set(raw_columns) != expected_raw_keys:
        raise TargetAuditError("producer raw-column contract field set is not exact")
    if raw_columns.get("runtime_fields") != target["physical_row_accounting"]["runtime_raw_fields"]:
        raise TargetAuditError("receipt raw-column contract is not the canonical six fields")
    if raw_columns.get("required_columns_present") is not True:
        raise TargetAuditError("receipt does not certify required raw columns")
    if raw_columns.get("canonical_v2_variable_universe_parity") is not True:
        raise TargetAuditError("receipt does not certify canonical six-field parity")
    if raw_columns.get("rejected_inherited_helper_fields") != ["OCC2010", "IND1990"]:
        raise TargetAuditError("receipt does not explicitly reject inherited helper fields")
    source_column_counts = _require_exact_integer_map(
        raw_columns.get("source_column_counts"), RAW_SOURCE_IDS, "source_column_counts"
    )
    if any(value < len(target["physical_row_accounting"]["runtime_raw_fields"]) for value in source_column_counts.values()):
        raise TargetAuditError("a producer source column count is smaller than the runtime universe")

    accounting_summary = authenticate_producer_accounting(
        receipt, target, cell_spec
    )
    expected_calendar = {
        "status": "PASS_CALENDAR",
        "observed_month_count": cell_spec["grid_contract"]["observed_month_count"],
        "observed_start": cell_spec["calendar_contract"]["observed_start"],
        "observed_end": cell_spec["calendar_contract"]["observed_end"],
        "missing_months": cell_spec["calendar_contract"]["excluded_missing_months"],
        "transition_2022_12_present": True,
        "october_2025_absent_not_interpolated": True,
        "preperiod_month_count": cell_spec["calendar_contract"]["preperiod_month_count"],
        "restored_march_months": MARCH_REPAIR_MONTHS,
    }
    if receipt.get("calendar_checks") != expected_calendar:
        raise TargetAuditError("producer calendar or repair-month receipt differs")
    expected_grid = cell_spec["grid_contract"]
    if receipt.get("occupation_count") != expected_grid["occupation_count"]:
        raise TargetAuditError("producer top-level occupation count differs")
    if receipt.get("observed_month_count") != expected_grid["observed_month_count"]:
        raise TargetAuditError("producer top-level month count differs")
    if receipt.get("cells_row_count") != expected_grid["expected_rows"]:
        raise TargetAuditError("producer top-level cell-row count differs")
    support_sha = canonical["occupation"]["universe"]["content_support_sha256"]
    if receipt.get("support_hash_sha256") != support_sha:
        raise TargetAuditError("producer top-level support hash differs")

    assignment = {
        "schema_version": "yax-assignment-fingerprint-v1",
        "algorithm": cell_spec["assignment_contract"]["fingerprint_algorithm"],
        "columns": cell_spec["assignment_contract"]["columns"],
        "record_count": cell_spec["assignment_contract"]["record_count"],
        "sha256": cell_spec["assignment_contract"]["fingerprint_sha256"],
    }
    if receipt.get("assignment_fingerprint") != assignment:
        raise TargetAuditError("producer assignment-fingerprint document differs")
    if receipt.get("assignment_fingerprint_sha256") != assignment["sha256"]:
        raise TargetAuditError("producer top-level assignment fingerprint differs")
    assignment_path = receipt_path.parent / ASSIGNMENT_FILENAME
    require_file(assignment_path, "assignment-fingerprint artifact")
    if load_json(assignment_path) != assignment:
        raise TargetAuditError("colocated assignment-fingerprint artifact differs")
    if receipt.get("assignment_fingerprint_artifact_sha256") != sha256_file(assignment_path):
        raise TargetAuditError("assignment-fingerprint artifact hash differs")

    expected_reference = {
        "fixed_membership_sha256": canonical["exposure"]["fixed_membership"]["sha256"]
    }
    if receipt.get("reference_artifacts") != expected_reference:
        raise TargetAuditError("producer reference-artifact receipt differs")
    if receipt.get("fixed_membership_sha256") != expected_reference["fixed_membership_sha256"]:
        raise TargetAuditError("producer fixed-membership hash differs")
    receipt["_target_authentication_summary"] = {
        "sources": source_summary,
        "runtime": runtime_summary,
        "execution_entry": execution_entry_summary,
        "git": git_summary,
        "accounting": accounting_summary,
    }
    return receipt


def read_and_validate_cells(
    cells_path: Path,
    receipt: dict[str, Any],
    target: dict[str, Any],
    canonical: dict[str, Any],
    cell_spec: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    expected_columns = cell_spec["output_contract"]["columns"]
    frame = pd.read_csv(
        cells_path,
        dtype={"occ_code": str, "month": str, "family": str},
        float_precision="round_trip",
    )
    if list(frame.columns) != expected_columns:
        raise TargetAuditError("aggregate-cell columns or column order differ from contract")
    if len(frame) != cell_spec["grid_contract"]["expected_rows"]:
        raise TargetAuditError("aggregate physical row count differs from cell-build contract")
    if frame[["occ_code", "month"]].duplicated().any():
        raise TargetAuditError("aggregate grid has duplicate occupation-month rows")
    if not frame.occ_code.str.fullmatch(r"[0-9]{4}").all():
        raise TargetAuditError("occupation codes are not four-digit Census-2018 strings")
    if not frame.family.str.fullmatch(r"[0-9]{2}").all():
        raise TargetAuditError("family labels are not two-digit SOC major-group strings")
    if not frame.month.str.fullmatch(r"[0-9]{4}-[0-9]{2}").all():
        raise TargetAuditError("month labels are malformed")

    for column in ("young", "older", "beta_quintile", "webb_z"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        if not np.isfinite(frame[column].to_numpy(float)).all():
            raise TargetAuditError(f"aggregate column is nonfinite: {column}")
    if (frame[["young", "older"]] < 0).any().any():
        raise TargetAuditError("aggregate employment stocks must be nonnegative")
    quintiles = frame.beta_quintile.to_numpy(float)
    if not np.equal(quintiles, np.floor(quintiles)).all() or not set(quintiles.astype(int)) <= {1, 2, 3, 4, 5}:
        raise TargetAuditError("beta quintiles must be integers in 1 through 5")
    frame["beta_quintile"] = frame.beta_quintile.astype(int)

    fixed = frame[["occ_code", "family", "beta_quintile", "webb_z"]].drop_duplicates()
    if fixed.occ_code.duplicated().any():
        raise TargetAuditError("treatment or family assignments vary within occupation")
    fixed = fixed.sort_values("occ_code", kind="mergesort").reset_index(drop=True)
    expected_occupations = canonical["occupation"]["analysis_subset"]["occupation_count"]
    if len(fixed) != expected_occupations:
        raise TargetAuditError("aggregate support occupation count differs from canonical V2")
    observed_support_hash = support_hash(fixed.occ_code)
    expected_support_hash = canonical["occupation"]["universe"]["content_support_sha256"]
    if observed_support_hash != expected_support_hash:
        raise TargetAuditError("aggregate occupation support hash differs from canonical V2")
    observed_fingerprint = assignment_fingerprint(fixed)
    if observed_fingerprint != cell_spec["assignment_contract"]["fingerprint_sha256"]:
        raise TargetAuditError("aggregate assignment fingerprint differs from cell-build contract")
    if receipt.get("assignment_fingerprint", {}).get("sha256") != observed_fingerprint:
        raise TargetAuditError("aggregate assignment fingerprint differs from authenticated receipt")

    observed_months = sorted(frame.month.unique())
    expected_months = expected_observed_months(canonical)
    if observed_months != expected_months:
        raise TargetAuditError("aggregate calendar differs from canonical observed months")
    expected_per_occ = len(expected_months)
    if not frame.groupby("occ_code", observed=True).size().eq(expected_per_occ).all():
        raise TargetAuditError("aggregate grid is not balanced by occupation")
    grid = receipt.get("grid", {})
    expected_grid = {
        "occupation_count": len(fixed),
        "observed_month_count": len(expected_months),
        "row_count": len(frame),
    }
    for field, value in expected_grid.items():
        if grid.get(field) != value:
            raise TargetAuditError(f"aggregate receipt grid mismatch: {field}")

    transition = canonical["calendar"]["transition_handling"]
    if transition.get("static_models") != "exclude 2022-12":
        raise TargetAuditError("canonical static transition rule changed")
    static_months = [month for month in observed_months if month != "2022-12"]
    static = frame.loc[frame.month.isin(static_months)].copy()
    expected_static = canonical["calendar"]["estimation_window"]["included_month_count"]
    if len(static_months) != expected_static:
        raise TargetAuditError("static month count differs from canonical V2")
    if len(static) != len(fixed) * expected_static:
        raise TargetAuditError("static occupation-month grid is incomplete")
    if "2022-12" in set(static.month) or "2025-10" in set(static.month):
        raise TargetAuditError("static grid retained an excluded or nonexistent month")

    young_sum = float(frame.young.sum())
    older_sum = float(frame.older.sum())
    weight = receipt["weight_once_checks"]
    for name, observed in (("young_stock", young_sum), ("older_stock", older_sum)):
        expected = float(weight[name])
        scale = max(abs(expected), 1.0)
        if abs(observed - expected) / scale > 1e-12:
            raise TargetAuditError(f"aggregate stock sum differs from weight-once receipt: {name}")

    total = static.young.to_numpy(float) + static.older.to_numpy(float)
    young = static.young.to_numpy(float)
    older = static.older.to_numpy(float)
    positive = total > 0
    one_sided = positive & ((young == 0) ^ (older == 0))
    zero_young_positive_older = (young == 0) & (older > 0)
    positive_young_zero_older = (young > 0) & (older == 0)
    both_zero = total == 0
    noninteger_young = np.abs(young - np.rint(young)) > 1e-9
    noninteger_older = np.abs(older - np.rint(older)) > 1e-9
    if int(positive.sum()) + int(both_zero.sum()) != len(static):
        raise TargetAuditError("static row partition does not reconcile")
    if np.any(one_sided & ~positive):
        raise TargetAuditError("one-sided cell classification is inconsistent")

    selected = static.loc[positive, expected_columns].sort_values(
        ["occ_code", "month"], kind="mergesort"
    )
    content_digest = hashlib.sha256()
    for row in selected.itertuples(index=False, name=None):
        record = dict(zip(expected_columns, row))
        record["beta_quintile"] = int(record["beta_quintile"])
        record["young"] = float(record["young"])
        record["older"] = float(record["older"])
        record["webb_z"] = float(record["webb_z"])
        content_digest.update(canonical_bytes(record) + b"\n")

    post = static.month.ge("2023-01").to_numpy(bool)
    design = {
        "Q1_reference_post_rows": int(
            ((static.beta_quintile.to_numpy(int) == 1) & post & positive).sum()
        ),
        **{
            f"Q{q}_x_post_nonzero_rows": int(
                ((static.beta_quintile.to_numpy(int) == q) & post & positive).sum()
            )
            for q in (2, 3, 4, 5)
        },
    }
    design["Webb_z_x_post_nonzero_rows"] = int(
        ((np.abs(static.webb_z.to_numpy(float)) > 0) & post & positive).sum()
    )
    if design["Q1_reference_post_rows"] == 0 or any(
        design[f"Q{q}_x_post_nonzero_rows"] == 0 for q in (2, 3, 4, 5)
    ):
        raise TargetAuditError("a required canonical target regressor has no nonzero rows")

    facts = {
        "aggregate_rows": int(len(frame)),
        "aggregate_months": int(len(observed_months)),
        "static_grid_rows": int(len(static)),
        "static_months": int(len(static_months)),
        "occupations": int(len(fixed)),
        "positive_total_estimating_rows": int(positive.sum()),
        "one_sided_zero_rows_retained": int(one_sided.sum()),
        "zero_young_positive_older_rows_retained": int(zero_young_positive_older.sum()),
        "positive_young_zero_older_rows_retained": int(positive_young_zero_older.sum()),
        "both_zero_rows_no_criterion_contribution": int(both_zero.sum()),
        "static_young_stock": float(young.sum()),
        "static_older_stock": float(older.sum()),
        "aggregate_young_stock": young_sum,
        "aggregate_older_stock": older_sum,
        "static_young_noninteger_stock_rows": int(noninteger_young.sum()),
        "static_older_noninteger_stock_rows": int(noninteger_older.sum()),
        "support_content_sha256": observed_support_hash,
        "assignment_fingerprint_sha256": observed_fingerprint,
        "estimating_rows_content_sha256": content_digest.hexdigest(),
        "design_nonzero_rows": design,
    }
    return frame, static, facts


def build_row_accounting(
    receipt: dict[str, Any], facts: dict[str, Any]
) -> list[dict[str, Any]]:
    raw = receipt["six_field_cell_build_checks"]
    physical_by_source = raw["physical_rows_read_by_source"]
    eligible_by_source = raw["eligible_employed_age_22_65_records_by_source"]
    rows = [
        {
            "stage": "source_rows_scanned",
            "value": raw["physical_rows_read_total"],
            "unit": "physical input rows",
            "integer_physical_count": True,
            "criterion_role": "upstream only; includes rows later replaced or excluded",
        },
        {
            "stage": "wide_source_rows_scanned",
            "value": physical_by_source["ipums_cps_extract_9_wide"],
            "unit": "physical input rows",
            "integer_physical_count": True,
            "criterion_role": "wide-source component of source_rows_scanned",
        },
        {
            "stage": "repair_source_rows_scanned",
            "value": physical_by_source["ipums_cps_extract_11_march_basic_repair"],
            "unit": "physical input rows",
            "integer_physical_count": True,
            "criterion_role": "March-repair component of source_rows_scanned",
        },
        {
            "stage": "eligible_employed_age_22_65_source_records",
            "value": raw["eligible_employed_age_22_65_records_total"],
            "unit": "physical source records",
            "integer_physical_count": True,
            "criterion_role": "exact target-age routing universe before occupation validity",
        },
        {
            "stage": "wide_eligible_employed_age_22_65_source_records",
            "value": eligible_by_source["ipums_cps_extract_9_wide"],
            "unit": "physical source records",
            "integer_physical_count": True,
            "criterion_role": "wide-source component of exact target-age eligibility",
        },
        {
            "stage": "repair_eligible_employed_age_22_65_source_records",
            "value": raw["repair_eligible_employed_age_22_65_records"],
            "unit": "physical source records",
            "integer_physical_count": True,
            "criterion_role": "repair-source component of exact target-age eligibility",
        },
        {
            "stage": "eligible_records_with_invalid_raw_occupation",
            "value": raw["invalid_raw_occ_records"],
            "unit": "physical source records",
            "integer_physical_count": True,
            "criterion_role": "excluded before occupation routing",
        },
        {
            "stage": "eligible_records_with_valid_raw_occupation",
            "value": raw["valid_raw_occ_records"],
            "unit": "physical source records",
            "integer_physical_count": True,
            "criterion_role": "partitioned into early and current source records",
        },
        {
            "stage": "early_valid_source_records",
            "value": raw["early_valid_source_records"],
            "unit": "physical source records",
            "integer_physical_count": True,
            "criterion_role": "2017–2019 valid records offered to the occupation bridge",
        },
        {
            "stage": "current_valid_source_records",
            "value": raw["current_valid_source_records"],
            "unit": "physical source records",
            "integer_physical_count": True,
            "criterion_role": "2020 onward valid records routed directly",
        },
        {
            "stage": "early_matched_source_records",
            "value": raw["early_matched_source_records"],
            "unit": "physical source records",
            "integer_physical_count": True,
            "criterion_role": "early source records with a bridge route",
        },
        {
            "stage": "early_unmatched_source_records",
            "value": raw["early_unmatched_source_records"],
            "unit": "physical source records",
            "integer_physical_count": True,
            "criterion_role": "early source records excluded for no bridge route",
        },
        {
            "stage": "wide_march_rows_explicitly_replaced",
            "value": raw["wide_march_rows_explicitly_replaced"],
            "unit": "physical input rows",
            "integer_physical_count": True,
            "criterion_role": "wide-source March records removed before target eligibility",
        },
        {
            "stage": "wide_march_positive_weight_rows_explicitly_replaced",
            "value": raw["wide_march_positive_weight_rows_explicitly_replaced"],
            "unit": "physical input rows",
            "integer_physical_count": True,
            "criterion_role": "positive-weight subset of explicitly replaced wide-source rows",
        },
        {
            "stage": "early_expanded_route_descendants",
            "value": raw["early_expanded_route_descendants"],
            "unit": "in-memory bridge-contribution rows",
            "integer_physical_count": True,
            "criterion_role": "not respondents; one matched early source record may have several descendants",
        },
        {
            "stage": "early_fractional_route_contributions",
            "value": raw["early_fractional_route_contributions"],
            "unit": "in-memory bridge-contribution rows",
            "integer_physical_count": True,
            "criterion_role": "strictly positive bridge allocation below one",
        },
        {
            "stage": "early_unit_route_contributions",
            "value": raw["early_unit_route_contributions"],
            "unit": "in-memory bridge-contribution rows",
            "integer_physical_count": True,
            "criterion_role": "bridge allocation exactly one",
        },
        {
            "stage": "early_zero_mass_route_contributions",
            "value": raw["early_zero_mass_route_contributions"],
            "unit": "in-memory bridge-contribution rows",
            "integer_physical_count": True,
            "criterion_role": "bridge allocation exactly zero",
        },
        {
            "stage": "current_direct_route_contributions",
            "value": raw["current_direct_route_contributions"],
            "unit": "in-memory direct-contribution rows",
            "integer_physical_count": True,
            "criterion_role": "one direct route for each valid current source record",
        },
        {
            "stage": "all_routed_contribution_rows",
            "value": raw["routed_contribution_rows"],
            "unit": "in-memory route-contribution rows",
            "integer_physical_count": True,
            "criterion_role": "early descendants plus current direct contributions",
        },
        {
            "stage": "routed_age_level_aggregate_rows",
            "value": raw["aggregate_rows"],
            "unit": "grouped intermediate rows",
            "integer_physical_count": True,
            "criterion_role": "pre-target aggregation",
        },
        {
            "stage": "authenticated_aggregate_grid_rows",
            "value": facts["aggregate_rows"],
            "unit": "occupation-month rows",
            "integer_physical_count": True,
            "criterion_role": "114-month transport grid including 2022-12",
        },
        {
            "stage": "canonical_static_grid_rows",
            "value": facts["static_grid_rows"],
            "unit": "occupation-month rows",
            "integer_physical_count": True,
            "criterion_role": "113-month static grid after excluding 2022-12",
        },
        {
            "stage": "positive_total_estimating_rows",
            "value": facts["positive_total_estimating_rows"],
            "unit": "occupation-month rows",
            "integer_physical_count": True,
            "criterion_role": "rows with a nonzero grouped-binomial criterion contribution",
        },
        {
            "stage": "one_sided_zero_rows_retained",
            "value": facts["one_sided_zero_rows_retained"],
            "unit": "occupation-month rows",
            "integer_physical_count": True,
            "criterion_role": "valid boundary stock observations retained",
        },
        {
            "stage": "both_zero_rows",
            "value": facts["both_zero_rows_no_criterion_contribution"],
            "unit": "occupation-month rows",
            "integer_physical_count": True,
            "criterion_role": "present on balanced grid; excluded because total stock is zero",
        },
        {
            "stage": "young_stock",
            "value": facts["static_young_stock"],
            "unit": "CPS-weighted employed-person stock",
            "integer_physical_count": False,
            "criterion_role": "continuous criterion numerator; not a row count",
        },
        {
            "stage": "older_stock",
            "value": facts["static_older_stock"],
            "unit": "CPS-weighted employed-person stock",
            "integer_physical_count": False,
            "criterion_role": "continuous comparison stock; not a row count",
        },
    ]
    return rows


def exact_target_document(
    target: dict[str, Any],
    canonical: dict[str, Any],
    cell_spec: dict[str, Any],
    receipt: dict[str, Any],
    facts: dict[str, Any],
) -> dict[str, Any]:
    return {
        "status": "PASS_EXACT_TARGET_AUDIT",
        "analysis_status": (
            "post-outcome referee-led target audit; no coefficient estimated by this module"
        ),
        "requirement": "T01",
        "target_audit_spec_id": target["target_audit_spec_id"],
        "canonical_spec_id": canonical["spec_id"],
        "cell_build_spec_id": cell_spec["cell_build_spec_id"],
        "authenticated_cells_sha256": receipt["cells_sha256"],
        "producer_execution_authentication": receipt[
            "_target_authentication_summary"
        ],
        "observed_estimating_data": {
            "grid_key": ["Census-2018 detailed occupation", "calendar month"],
            "stock_columns": {"young": "ages 22-25", "older": "ages 26-65"},
            "stock_unit": "CPS-weighted employed-person stock",
            "survey_weight": "WTFINL enters routed stock once",
            "static_transition_rule": "exclude observed 2022-12",
            "missing_month_rule": "2025-10 is absent and is not interpolated",
            "criterion_rows": "positive young-plus-older total stock",
            "one_sided_zero_rule": "retain",
            "both_zero_rule": "balanced-grid row retained for accounting; no criterion contribution",
            "facts": facts,
        },
        "criterion_and_parameter": {
            "criterion": (
                "sum_over_o,t_with_T_positive [N_y(o,t)*log(p(o,t)) + "
                "N_o(o,t)*log(1-p(o,t))]"
            ),
            "total_stock": "T(o,t) = N_y(o,t) + N_o(o,t)",
            "conditional_mean_share": "p(o,t) = mu_y(o,t) / [mu_y(o,t) + mu_o(o,t)]",
            "linear_predictor": (
                "logit(p(o,t)) = log[mu_y(o,t)/mu_o(o,t)] = alpha_o + lambda_t + "
                "sum_{q=2}^5 beta_q 1{Q_o=q}1{t>=2023-01} + theta WebbZ_o 1{t>=2023-01}"
            ),
            "headline_parameter": (
                "beta_5: Q5-versus-Q1 post-2023 change in the log conditional-mean "
                "young-to-older employment-stock ratio, conditional on the declared nuisance space"
            ),
            "coefficient_unit": "log points",
            "ratio_percent_transform": "100*[exp(beta_5)-1], only when labeled as a ratio change",
        },
        "row_count_reconciliation": {
            "physical_counts": (
                "source rows, routed descendants, grouped rows, and occupation-month rows are "
                "integer counts of stored or in-memory rows"
            ),
            "continuous_quantities": (
                "young and older stocks are real-valued sums after one WTFINL application and, "
                "before 2020, fractional bridge allocation"
            ),
            "route_descendants": (
                "route-expanded rows are not distinct respondents; several descendants can share "
                "one physical source record"
            ),
            "unique_people_or_households": (
                "not recoverable from the sanctioned aggregate schema and not reported by this audit"
            ),
            "respondent_equivalents": (
                "not constructed by the six-field target router, not present in the sanctioned "
                "aggregate schema, and never substituted for physical rows"
            ),
        },
        "interpretation_bounds": {
            "allowed": [
                "conditional-mean employment-stock ratio contrast",
                "grouped-binomial estimating criterion on continuous survey-weighted stocks",
            ],
            "forbidden": [
                "observed log young-to-older ratio in every cell",
                "literal binomial likelihood for independent persons",
                "individual employment probability",
                "employer hiring rate",
                "causal effect of AI",
            ],
        },
        "weight_and_schema_checks": {
            "weight_application_count": 1,
            "output_applies_no_additional_weight": True,
            "route_weight_is_allocation_not_second_survey_weight": True,
            "aggregate_schema_version": EXPECTED_AGGREGATE_SCHEMA,
            "columns": cell_spec["output_contract"]["columns"],
            "canonical_assertions_passed": len(target["canonical_assertions"]),
            "upstream_assertions_passed": len(target["upstream_assertions"]),
        },
    }


def render_report(audit: dict[str, Any], rows: list[dict[str, Any]]) -> str:
    facts = audit["observed_estimating_data"]["facts"]
    lines = [
        "# V3 Gate 1 exact-target audit",
        "",
        "Status: **PASS_EXACT_TARGET_AUDIT**. This module authenticates and describes the",
        "aggregate estimating data; it does not estimate or reproduce a coefficient.",
        "",
        "## Exact target",
        "",
        "The criterion is evaluated on two continuous CPS-weighted employment stocks,",
        "`N_y` for ages 22–25 and `N_o` for ages 26–65. For rows with",
        "`T=N_y+N_o>0`, it is `N_y log(p) + N_o log(1-p)`, where",
        "`logit(p)=log(mu_y/mu_o)`. The Q5 coefficient is therefore a Q5-versus-Q1",
        "post-2023 change in a log ratio of conditional mean stocks. It is not an",
        "observed log ratio, individual employment probability, or hiring rate.",
        "",
        "## Authenticated static grid",
        "",
        f"- Occupations: {facts['occupations']}",
        f"- Static months: {facts['static_months']}",
        f"- Balanced static rows: {facts['static_grid_rows']}",
        f"- Positive-total estimating rows: {facts['positive_total_estimating_rows']}",
        f"- Retained one-sided zero rows: {facts['one_sided_zero_rows_retained']}",
        f"- Both-zero rows with no criterion contribution: {facts['both_zero_rows_no_criterion_contribution']}",
        "",
        "## Row and stock accounting",
        "",
        "| stage | value | unit | criterion role |",
        "|---|---:|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row['stage']} | {row['value']} | {row['unit']} | {row['criterion_role']} |"
        )
    lines.extend(
        [
            "",
            "Physical row counts are integers. Employment stocks are real-valued survey-weighted",
            "quantities and may be fractional. Route-expanded descendants are not unique people;",
            "the aggregate schema cannot recover unique people or households.",
            "",
            "## Weight rule",
            "",
            "`WTFINL` enters routed stock exactly once. A pre-2020 bridge weight allocates that",
            "stock across target occupations and is not a second survey weight. No weight is",
            "applied when the routed stocks are collapsed to the audit grid.",
            "",
        ]
    )
    return "\n".join(lines)


def sanitize_text(text: str, replacements: dict[str, str]) -> str:
    cleaned = text
    for raw, placeholder in sorted(replacements.items(), key=lambda item: -len(item[0])):
        if raw:
            cleaned = cleaned.replace(raw, placeholder)
    for pattern in SECRET_PATTERNS:
        cleaned = pattern.sub("<REDACTED_SECRET>", cleaned)
    for pattern in PRIVATE_PATH_PATTERNS:
        cleaned = pattern.sub("<REDACTED_PRIVATE_PATH>", cleaned)
    return cleaned


def assert_sanitized(value: Any) -> None:
    serialized = json.dumps(value, sort_keys=True, allow_nan=False)
    if any(pattern.search(serialized) for pattern in SECRET_PATTERNS):
        raise TargetAuditError("secret-sanitization check failed")
    if any(pattern.search(serialized) for pattern in PRIVATE_PATH_PATTERNS):
        raise TargetAuditError("private-path sanitization check failed")


def path_is_within(path: Path, parent: Path) -> bool:
    path = path.resolve(strict=False)
    parent = parent.resolve(strict=False)
    return path == parent or parent in path.parents


def reserve_output_leaf(output_leaf: Path, repo: Path, input_leaf: Path) -> Path:
    if os.path.lexists(output_leaf):
        raise TargetAuditError("refusing a pre-existing output leaf")
    output_leaf = Path(os.path.abspath(output_leaf)).resolve(strict=False)
    if os.path.lexists(output_leaf):
        raise TargetAuditError("refusing a pre-existing output leaf")
    repo = repo.resolve()
    input_leaf = input_leaf.resolve()
    if path_is_within(output_leaf, repo):
        raise TargetAuditError("audit output must be outside the Git repository")
    if path_is_within(output_leaf, input_leaf) or path_is_within(input_leaf, output_leaf):
        raise TargetAuditError("audit output and authenticated input leaf must be disjoint")
    if not output_leaf.parent.is_dir():
        raise TargetAuditError("output-leaf parent must already exist")
    return Path(tempfile.mkdtemp(prefix=f".{output_leaf.name}.tmp-", dir=output_leaf.parent))


def fsync_file(path: Path) -> None:
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def atomic_publish(
    staging: Path,
    output_leaf: Path,
    expected_filenames: set[str] | None = None,
) -> tuple[str, ...]:
    if os.path.lexists(output_leaf):
        raise TargetAuditError("output leaf appeared during audit; refusing overwrite")
    observed_filenames: set[str] = set()
    for directory, dirnames, filenames in os.walk(
        staging, topdown=False, followlinks=False
    ):
        base = Path(directory)
        if base != staging or dirnames:
            raise TargetAuditError("staging output must be a flat file set")
        for name in filenames:
            path = base / name
            if path.is_symlink() or not path.is_file():
                raise TargetAuditError("staging contains a non-regular output")
            if path.stat().st_nlink != 1:
                raise TargetAuditError("staging contains a multiply linked output")
            observed_filenames.add(name)
            fsync_file(path)
        for name in dirnames:
            if (base / name).is_symlink():
                raise TargetAuditError("staging contains a symlink directory")
        descriptor = os.open(base, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    if expected_filenames is not None and observed_filenames != expected_filenames:
        raise TargetAuditError("staging output inventory differs from the exact contract")
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(staging)
    target_bytes = os.fsencode(output_leaf)
    if sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        function = libc.renameat2
        function.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        result = function(-100, source_bytes, -100, target_bytes, 1)
    elif sys.platform == "darwin" and hasattr(libc, "renameatx_np"):
        function = libc.renameatx_np
        function.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        result = function(-2, source_bytes, -2, target_bytes, 0x00000004)
    else:
        raise TargetAuditError("platform lacks atomic no-replace directory rename")
    if result != 0:
        error = ctypes.get_errno()
        if error in {errno.EEXIST, errno.ENOTEMPTY}:
            raise TargetAuditError("output leaf appeared during publication; refusing overwrite")
        raise TargetAuditError(f"atomic no-replace publication failed with errno {error}")
    warnings: list[str] = []
    try:
        parent_fd = os.open(output_leaf.parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except OSError as error:
        warnings.append(f"parent_fsync_errno_{error.errno}")
    return tuple(warnings)


def execute(
    args: argparse.Namespace,
) -> dict[str, Any]:
    job = scheduler_jobnumber(dict(os.environ))
    derived_output_leaf = args.output_parent / f"gate1_target_sge_{job}"
    supplied_output_leaf = getattr(args, "output_leaf", derived_output_leaf)
    if supplied_output_leaf.resolve(strict=False) != derived_output_leaf.resolve(strict=False):
        raise TargetAuditError("output leaf is not derived from the scheduler job ID")
    args.output_leaf = derived_output_leaf
    execution_binding = build_execution_command_binding(
        args, list(sys.argv[1:]), list(getattr(sys, "orig_argv", [])),
        dict(os.environ),
    )
    execution_runtime = execution_runtime_authentication()
    repo = args.repo_root.resolve()
    if not ((repo / ".git").is_dir() or (repo / ".git").is_file()):
        raise TargetAuditError("repo-root is not a Git worktree")
    cells_path = args.cells.resolve()
    receipt_path = args.cells_receipt.resolve()
    output_leaf = args.output_leaf.resolve(strict=False)
    replacements = {
        str(repo): "<YAX_REPO_ROOT>",
        str(cells_path.parent): "<YAX_GATE1_CELLS_LEAF>",
        str(output_leaf): "<YAX_TARGET_AUDIT_LEAF>",
    }
    staging: Path | None = None
    try:
        target, canonical, cell_spec = load_and_validate_specs(repo)
        code_hashes = authenticate_code(repo, target, cell_spec)
        pre_execution_authorization = validate_pre_execution_authorization(
            repo, canonical, target, cell_spec,
            code_hashes[str(HERE_REL / "run_exact_target_audit.py")],
        )
        source_evidence_hashes = authenticate_source_evidence(repo, target)
        requirement_binding = validate_requirement_source(repo, target)
        receipt = authenticate_aggregate_receipt(
            receipt_path, cells_path, target, canonical, cell_spec, repo,
            pre_execution_authorization,
        )
        staging = reserve_output_leaf(output_leaf, repo, cells_path.parent)
        _frame, _static, facts = read_and_validate_cells(
            cells_path, receipt, target, canonical, cell_spec
        )
        rows = build_row_accounting(receipt, facts)
        audit = exact_target_document(target, canonical, cell_spec, receipt, facts)
        assert_sanitized(audit)
        write_json(staging / AUDIT_FILENAME, audit)
        write_csv(staging / ROW_ACCOUNTING_FILENAME, rows)
        (staging / REPORT_FILENAME).write_text(
            render_report(audit, rows), encoding="utf-8"
        )
        artifact_hashes = {
            name: sha256_file(staging / name)
            for name in (AUDIT_FILENAME, ROW_ACCOUNTING_FILENAME, REPORT_FILENAME)
        }
        audit_result_id = TARGET_AUDIT_PREFIX + hashlib.sha256(
            canonical_bytes(
                {
                    "target_audit_spec_id": target["target_audit_spec_id"],
                    "cells_sha256": receipt["cells_sha256"],
                    "estimating_rows_content_sha256": facts["estimating_rows_content_sha256"],
                    "artifact_hashes": artifact_hashes,
                }
            )
        ).hexdigest()
        execution_receipt = {
            "schema_version": TARGET_RECEIPT_SCHEMA,
            "status": "PASS_EXACT_TARGET_AUDIT",
            "generated_at_utc": utc_now(),
            "command_template": COMMAND_TEMPLATE,
            "execution_command_binding": execution_binding,
            "execution_runtime_authentication": execution_runtime,
            "pre_execution_authorization": pre_execution_authorization,
            "requirement": "T01",
            "target_audit_spec_id": target["target_audit_spec_id"],
            "target_audit_spec_sha256": sha256_file(repo / TARGET_SPEC_REL),
            "canonical_spec_id": canonical["spec_id"],
            "canonical_spec_sha256": sha256_file(repo / CANONICAL_SPEC_REL),
            "cell_build_spec_id": cell_spec["cell_build_spec_id"],
            "cell_build_spec_sha256": sha256_file(repo / CELL_SPEC_REL),
            "authenticated_cells_sha256": receipt["cells_sha256"],
            "source_aggregate_receipt_sha256": sha256_file(receipt_path),
            "producer_execution_authentication": receipt[
                "_target_authentication_summary"
            ],
            "code_hashes": code_hashes,
            "source_evidence_hashes": source_evidence_hashes,
            "requirement_binding": requirement_binding,
            "audit_result_id": audit_result_id,
            "facts": facts,
            "artifact_hashes": artifact_hashes,
            "security": {
                "output_outside_repository": True,
                "input_and_output_leaves_disjoint": True,
                "new_atomic_output_leaf": True,
                "row_level_microdata_read": False,
                "coefficient_estimated": False,
                "private_paths_persisted": False,
                "credentials_persisted": False,
            },
        }
        assert_sanitized(execution_receipt)
        write_json(staging / RECEIPT_FILENAME, execution_receipt)
        # Re-open all authorization-bound files and the authenticated aggregate
        # at the publication boundary. Reusing start-of-run dictionaries would
        # make a concurrent checkout or input mutation invisible here.
        final_target, final_canonical, final_cell_spec = load_and_validate_specs(repo)
        final_code_hashes = authenticate_code(
            repo, final_target, final_cell_spec
        )
        final_source_evidence_hashes = authenticate_source_evidence(
            repo, final_target
        )
        final_requirement_binding = validate_requirement_source(
            repo, final_target
        )
        boundary_pre_execution_authorization = validate_pre_execution_authorization(
            repo, final_canonical, final_target, final_cell_spec,
            final_code_hashes[str(HERE_REL / "run_exact_target_audit.py")],
        )
        if boundary_pre_execution_authorization != pre_execution_authorization:
            raise TargetAuditError(
                "pre-execution authorization changed before final aggregate authentication"
            )
        final_receipt = authenticate_aggregate_receipt(
            receipt_path,
            cells_path,
            final_target,
            final_canonical,
            final_cell_spec,
            repo,
            boundary_pre_execution_authorization,
        )
        final_pre_execution_authorization = validate_pre_execution_authorization(
            repo, final_canonical, final_target, final_cell_spec,
            final_code_hashes[str(HERE_REL / "run_exact_target_audit.py")],
        )
        if (
            final_pre_execution_authorization != pre_execution_authorization
            or final_target != target
            or final_canonical != canonical
            or final_cell_spec != cell_spec
            or final_code_hashes != code_hashes
            or final_source_evidence_hashes != source_evidence_hashes
            or final_requirement_binding != requirement_binding
            or final_receipt != receipt
        ):
            raise TargetAuditError(
                "authorization-bound execution state changed during target audit"
            )
        post_commit_warnings = atomic_publish(
            staging,
            output_leaf,
            {
                AUDIT_FILENAME,
                ROW_ACCOUNTING_FILENAME,
                REPORT_FILENAME,
                RECEIPT_FILENAME,
            },
        )
        staging = None
        return {
            "status": execution_receipt["status"],
            "audit_result_id": audit_result_id,
            "target_audit_spec_id": target["target_audit_spec_id"],
            "static_grid_rows": facts["static_grid_rows"],
            "positive_total_estimating_rows": facts["positive_total_estimating_rows"],
            "output_leaf": "<YAX_GATE1_TARGET_LEAF>",
            "post_commit_cleanup_warnings": list(post_commit_warnings),
        }
    except Exception as exc:
        if staging is not None and staging.exists():
            shutil.rmtree(staging)
        message = sanitize_text(str(exc), replacements)
        if isinstance(exc, TargetAuditError):
            raise TargetAuditError(message) from exc
        raise TargetAuditError(f"unexpected audit failure: {message}") from exc


def parser() -> argparse.ArgumentParser:
    value = NonEchoingArgumentParser(description=__doc__, allow_abbrev=False)
    value.add_argument("--repo-root", type=Path, required=True)
    value.add_argument("--cells", type=Path, required=True)
    value.add_argument("--cells-receipt", type=Path, required=True)
    value.add_argument("--output-parent", type=Path, required=True)
    return value


def main(argv: list[str] | None = None) -> int:
    replacements: dict[str, str] = {}
    try:
        if argv is not None:
            raise TargetAuditError(
                "production entry point does not accept a substituted argv source"
            )
        raw_cli_argv = list(sys.argv[1:])
        args = parser().parse_args(raw_cli_argv)
        job = scheduler_jobnumber(dict(os.environ))
        args.output_leaf = args.output_parent / f"gate1_target_sge_{job}"
        replacements = {
            str(args.repo_root.resolve(strict=False)): "<YAX_REPO_ROOT>",
            str(args.cells.resolve(strict=False).parent): "<YAX_GATE1_CELLS_LEAF>",
            str(args.output_parent.resolve(strict=False)): "<YAX_V3_RUN_ROOT>",
            str(args.output_leaf.resolve(strict=False)): "<YAX_GATE1_TARGET_LEAF>",
        }
        result = execute(args)
    except Exception as exc:
        print(
            json.dumps(
                {"status": "BLOCKED", "error": sanitize_text(str(exc), replacements)},
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
