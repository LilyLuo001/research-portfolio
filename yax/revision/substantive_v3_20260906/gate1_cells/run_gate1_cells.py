#!/usr/bin/env python3
"""Build the authenticated V3 Gate-1 aggregate cell panel.

The production path implements the narrow canonical-V2 target router locally:
it reads exactly six CPS fields, retains employed respondents ages 22--65,
routes raw occupation codes, and writes only a balanced occupation-month
aggregate outside the repository. Historical general-purpose builders are
byte-locked references for synthetic parity tests and are never imported here.
No row-level CPS record is ever written by this program.
"""
from __future__ import annotations

import argparse
import ctypes
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
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
HERE_REL = V3_REL / "gate1_cells"
CELL_SPEC_REL = HERE_REL / "CELL_BUILD_SPEC.json"
CANONICAL_SPEC_REL = V3_REL / "contracts/specs/canonical_baseline_reproduction_v2.json"
NUMERICAL_SPEC_REL = V3_REL / "numerical_existence/ANALYSIS_SPEC.json"
TARGET_SPEC_REL = V3_REL / "gate1_target/TARGET_AUDIT_SPEC.json"
TARGET_CODE_REL = V3_REL / "gate1_target/run_exact_target_audit.py"
NUMERICAL_CODE_REL = V3_REL / "numerical_existence/run_numerical_existence_audit.py"
PRE_EXECUTION_AUTHORIZATION_REL = (
    V3_REL / "gate1_transfer/PRE_EXECUTION_AUTHORIZATION.json"
)

R3_BASELINE_REL = Path(
    "yax/revision/substantive_r3_20260905/rebuilt_baseline/"
    "run_rebuilt_corrected_baseline.py"
)
R3_CELLS_REL = Path("yax/revision/referee_20260905/run_referee_cells.py")
R3_CORE_REL = Path("yax/revision/referee_20260905/run_referee_core.py")
FROZEN_REL = Path("yax/analysis/run_frozen_v11.py")
ENGINE_REL = Path("dax/memo/power_calcs/young_relative_employment_power.py")
ENVIRONMENT_REL = Path("yax/revision/substantive_r3_20260905/ENVIRONMENT_LOCK.txt")
MEMBERSHIP_REL = Path(
    "yax/revision/substantive_r3_20260905/rebuilt_baseline/results/"
    "REBUILT_TREATMENT_MEMBERSHIP.csv"
)

REPO_SOURCE_PATHS = {
    "cps_occupation_exposure_lookup": Path(
        "yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv"
    ),
    "computerization_measures_census2018": Path(
        "yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv"
    ),
    "rule_b_values_census2018": Path(
        "yax/measurement/RULE_B_VALUES_CENSUS2018.csv"
    ),
    "census_occ2010_to_2018_bridge": Path(
        "yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv"
    ),
    "first_post_outcome_access_receipt": Path(
        "yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json"
    ),
}

RAW_SOURCE_ARGUMENTS = {
    "ipums_cps_extract_9_wide": "microdata",
    "ipums_cps_extract_11_march_basic_repair": "repair_microdata",
}

EXPECTED_CANONICAL_SPEC_ID = (
    "yaxspec_v1_83bb387f9fc28e2655db5101c7697989510475027d1dd5a9c361c797ed3925c3"
)
CELL_SCHEMA = "yax-numerical-cells-v1"
RECEIPT_SCHEMA = "yax-numerical-cells-receipt-v1"
CELL_SPEC_PREFIX = "yaxcellspec_v1_"
NUMERICAL_SPEC_PREFIX = "yaxnumspec_v1_"
TARGET_SPEC_PREFIX = "yaxtargetspec_v1_"
CELLS_FILENAME = "aggregate_cells.csv"
RECEIPT_FILENAME = "EXECUTION_RECEIPT.json"
ASSIGNMENT_FILENAME = "ASSIGNMENT_FINGERPRINT.json"

REQUIRED_RAW_COLUMNS = (
    "YEAR",
    "MONTH",
    "AGE",
    "EMPSTAT",
    "OCC",
    "WTFINL",
)
OUTPUT_COLUMNS = (
    "occ_code",
    "month",
    "family",
    "young",
    "older",
    "beta_quintile",
    "webb_z",
)
RUNTIME_CODE_PATHS = {
    str(HERE_REL / "run_gate1_cells.py"),
}
REFERENCE_CODE_PATHS = {
    str(ENGINE_REL),
    str(FROZEN_REL),
    str(R3_CELLS_REL),
    str(R3_CORE_REL),
    str(R3_BASELINE_REL),
}
MARCH_REPAIR_MONTHS = {f"{year}-03" for year in range(2017, 2022)}
COMMAND_TEMPLATE = (
    "<YAX_PYTHON_BIN> -I yax/revision/substantive_v3_20260906/gate1_cells/"
    "run_gate1_cells.py --repo-root <YAX_REPO_ROOT> "
    "--microdata <INPUT:ipums_cps_extract_9_wide> "
    "--repair-microdata <INPUT:ipums_cps_extract_11_march_basic_repair> "
    "--output-parent <YAX_V3_RUN_ROOT>"
)
COMMAND_BINDING_SCHEMA = "yax-execution-command-binding-v2"
COMMAND_BINDING_STATUS = "RUNNER_RECORDED_HASH_CONSISTENT"
PRE_EXECUTION_AUTHORIZATION_SCHEMA = "yax-gate1-pre-execution-authorization-v1"
PRE_EXECUTION_AUTHORIZATION_STATUS = "AUTHORIZED_FRESH_GATE1_EXECUTION"
PRE_EXECUTION_AUTHORIZATION_PREFIX = "yaxgate1auth_v1_"
MODULE_KEY = "cells"
JOB_ID_PATTERN = re.compile(r"^[1-9][0-9]{0,19}$")
RUN_ID_PATTERN = re.compile(r"^gate1_cells_sge_([1-9][0-9]{0,19})$")
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
    "--repo-root", "--microdata", "--repair-microdata", "--output-parent",
)

SECRET_PATTERNS = (
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)(?:password|passwd|api[_ -]?key|token)\s*[:=]\s*\S+"),
)
PRIVATE_PATH_PATTERNS = (
    re.compile(r"/(?:project|projectnb|usr\d+|Users)/[^\s\"']+"),
)


class CellBuildError(RuntimeError):
    """Fail-closed aggregate-cell construction error."""


class NonEchoingArgumentParser(argparse.ArgumentParser):
    """Never echo a possibly sensitive argv token in a parser error."""

    def error(self, message: str) -> None:
        raise CellBuildError("production command-line grammar is invalid")


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
    """Return the non-array Grid Engine job ID without persisting raw env."""
    job = environ.get("JOB_ID")
    alias = environ.get("SGE_JOB_ID")
    if job is None or not JOB_ID_PATTERN.fullmatch(job):
        raise CellBuildError("a canonical numeric SCC JOB_ID is required")
    if alias is not None and alias != job:
        raise CellBuildError("SGE_JOB_ID conflicts with JOB_ID")
    task = environ.get("SGE_TASK_ID")
    if task not in {None, "", "undefined"}:
        raise CellBuildError("Grid Engine array jobs are not authorized")
    return job


def execution_runtime_authentication() -> dict[str, Any]:
    """Verify the byte-pinned isolated Python and Git executables."""
    if (
        sys.flags.isolated != 1
        or sys.flags.ignore_environment != 1
        or sys.flags.no_user_site != 1
        or not bool(getattr(sys.flags, "safe_path", False))
    ):
        raise CellBuildError("production Python must be invoked with isolated mode")
    if any(os.environ.get(name) for name in IMPORT_AFFECTING_ENVIRONMENT):
        raise CellBuildError("import-affecting Python environment variables are forbidden")
    try:
        python_path = Path(sys.executable).resolve(strict=True)
    except OSError as exc:
        raise CellBuildError("Python executable cannot be resolved") from exc
    python_hash = sha256_file(python_path)
    if python_hash != EXPECTED_PYTHON_RESOLVED_SHA256:
        raise CellBuildError("resolved Python executable differs from the pinned runtime")
    if platform.python_version() != "3.13.8":
        raise CellBuildError("Python version differs from the pinned runtime")
    if not EXPECTED_GIT_PATH.is_file() or EXPECTED_GIT_PATH.is_symlink():
        raise CellBuildError("pinned Git executable is absent or indirect")
    git_hash = sha256_file(EXPECTED_GIT_PATH)
    if git_hash != EXPECTED_GIT_SHA256:
        raise CellBuildError("Git executable differs from the pinned runtime")
    completed = subprocess.run(
        [str(EXPECTED_GIT_PATH), "--version"],
        env=SANITIZED_GIT_ENVIRONMENT,
        text=True, capture_output=True, check=False,
    )
    if completed.returncode != 0 or completed.stdout.strip() != EXPECTED_GIT_VERSION:
        raise CellBuildError("Git version differs from the pinned runtime")
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
    """Bind the receipt to the exact direct invocation, token by token."""
    expected_length = 2 * len(EXPECTED_PRODUCTION_FLAGS)
    if len(raw_cli_argv) != expected_length:
        raise CellBuildError("production command-line grammar is invalid")
    if raw_cli_argv[::2] != list(EXPECTED_PRODUCTION_FLAGS):
        raise CellBuildError("production command-line grammar is invalid")
    if any(not value or any(ord(char) < 32 for char in value) for value in raw_cli_argv[1::2]):
        raise CellBuildError("production command-line values are invalid")
    if len(original_argv) != len(raw_cli_argv) + 3 or original_argv[1] != "-I":
        raise CellBuildError("production must use direct isolated-script invocation")
    try:
        invoked_python = Path(original_argv[0]).resolve(strict=True)
        invoked_script = Path(original_argv[2]).resolve(strict=True)
    except OSError as exc:
        raise CellBuildError("production executable or runner cannot be resolved") from exc
    if invoked_python != Path(sys.executable).resolve(strict=True):
        raise CellBuildError("invoked Python differs from the running interpreter")
    if invoked_script != Path(__file__).resolve():
        raise CellBuildError("production runner path is not the authorized script")
    executing_repo = Path(__file__).resolve().parents[4]
    if args.repo_root.resolve(strict=True) != executing_repo:
        raise CellBuildError("repo-root differs from the executing runner checkout")
    if not os.path.samefile(
        executing_repo / HERE_REL / "run_gate1_cells.py", Path(__file__).resolve()
    ):
        raise CellBuildError("executing runner is not the repo-root runner inode")
    if original_argv[3:] != raw_cli_argv:
        raise CellBuildError("raw process argv and script argv differ")
    parsed_values = (
        args.repo_root, args.microdata, args.repair_microdata, args.output_parent,
    )
    if any(Path(raw).resolve(strict=False) != Path(parsed).resolve(strict=False)
           for raw, parsed in zip(raw_cli_argv[1::2], parsed_values)):
        raise CellBuildError("parsed paths differ from the captured invocation")
    job = scheduler_jobnumber(environ)
    run_id = f"gate1_cells_sge_{job}"
    if RUN_ID_PATTERN.fullmatch(run_id) is None:
        raise CellBuildError("derived output run ID is invalid")
    sanitized_argv = [
        "<YAX_PYTHON_BIN>", "-I",
        str(HERE_REL / "run_gate1_cells.py"),
        "--repo-root", "<YAX_REPO_ROOT>",
        "--microdata", "<INPUT:ipums_cps_extract_9_wide>",
        "--repair-microdata", "<INPUT:ipums_cps_extract_11_march_basic_repair>",
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
            raise CellBuildError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(
            stream,
            object_pairs_hook=_unique_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                CellBuildError(f"invalid JSON numeric constant: {token}")
            ),
        )
    if not isinstance(value, dict):
        raise CellBuildError("JSON root must be an object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def expected_cell_spec_id(document: dict[str, Any]) -> str:
    clean = dict(document)
    clean.pop("cell_build_spec_id", None)
    return CELL_SPEC_PREFIX + hashlib.sha256(canonical_bytes(clean)).hexdigest()


def expected_numerical_spec_id(document: dict[str, Any]) -> str:
    clean = dict(document)
    clean.pop("audit_spec_id", None)
    return NUMERICAL_SPEC_PREFIX + hashlib.sha256(canonical_bytes(clean)).hexdigest()


def expected_target_spec_id(document: dict[str, Any]) -> str:
    clean = dict(document)
    clean.pop("target_audit_spec_id", None)
    return TARGET_SPEC_PREFIX + hashlib.sha256(canonical_bytes(clean)).hexdigest()


def expected_pre_execution_authorization_id(document: dict[str, Any]) -> str:
    clean = dict(document)
    clean.pop("authorization_id", None)
    return PRE_EXECUTION_AUTHORIZATION_PREFIX + hashlib.sha256(
        canonical_bytes(clean)
    ).hexdigest()


def validate_pre_execution_authorization(
    repo: Path,
    canonical: dict[str, Any],
    cell_spec: dict[str, Any],
    code_sha256: str,
    git_state: dict[str, Any],
    source_hashes: dict[str, str],
) -> dict[str, Any]:
    """Require a separately committed, live execution-window authorization."""
    path = repo / PRE_EXECUTION_AUTHORIZATION_REL
    require_file(path, "pre-execution authorization")
    document = load_json(path)
    expected_fields = {
        "schema_version", "status", "authorization_id", "issued_at_utc",
        "not_before_utc", "not_after_utc", "authorized_implementation_commit",
        "canonical_spec", "source_registry_sha256", "modules",
    }
    if set(document) != expected_fields:
        raise CellBuildError("pre-execution authorization field set is not exact")
    if (
        document.get("schema_version") != PRE_EXECUTION_AUTHORIZATION_SCHEMA
        or document.get("status") != PRE_EXECUTION_AUTHORIZATION_STATUS
        or document.get("authorization_id")
        != expected_pre_execution_authorization_id(document)
    ):
        raise CellBuildError("pre-execution authorization identity is invalid")
    try:
        issued = datetime.fromisoformat(
            str(document["issued_at_utc"]).replace("Z", "+00:00")
        )
        not_before = datetime.fromisoformat(
            str(document["not_before_utc"]).replace("Z", "+00:00")
        )
        not_after = datetime.fromisoformat(
            str(document["not_after_utc"]).replace("Z", "+00:00")
        )
    except (TypeError, ValueError) as exc:
        raise CellBuildError("pre-execution authorization timestamps are invalid") from exc
    if any(value.tzinfo is None for value in (issued, not_before, not_after)):
        raise CellBuildError("pre-execution authorization timestamps require offsets")
    now = datetime.now(timezone.utc)
    if not (issued <= not_before <= now <= not_after):
        raise CellBuildError("execution is outside the authorized time window")
    canonical_binding = {
        "id": canonical["spec_id"],
        "sha256": sha256_file(repo / CANONICAL_SPEC_REL),
    }
    if document.get("canonical_spec") != canonical_binding:
        raise CellBuildError("authorization canonical binding differs")
    source_registry_sha = hashlib.sha256(
        canonical_bytes(source_hashes)
    ).hexdigest()
    if document.get("source_registry_sha256") != source_registry_sha:
        raise CellBuildError("authorization source registry differs")
    modules = document.get("modules")
    if not isinstance(modules, dict) or set(modules) != {"cells", "target", "numerical"}:
        raise CellBuildError("authorization module registry is incomplete")
    target_spec = load_json(repo / TARGET_SPEC_REL)
    numerical_spec = load_json(repo / NUMERICAL_SPEC_REL)
    if target_spec.get("target_audit_spec_id") != expected_target_spec_id(target_spec):
        raise CellBuildError("authorization target specification ID is invalid")
    if numerical_spec.get("audit_spec_id") != expected_numerical_spec_id(numerical_spec):
        raise CellBuildError("authorization numerical specification ID is invalid")
    expected_modules = {
        "cells": {
            "typed_spec_id": cell_spec["cell_build_spec_id"],
            "typed_spec_sha256": sha256_file(repo / CELL_SPEC_REL),
            "code_sha256": code_sha256,
        },
        "target": {
            "typed_spec_id": target_spec["target_audit_spec_id"],
            "typed_spec_sha256": sha256_file(repo / TARGET_SPEC_REL),
            "code_sha256": sha256_file(repo / TARGET_CODE_REL),
        },
        "numerical": {
            "typed_spec_id": numerical_spec["audit_spec_id"],
            "typed_spec_sha256": sha256_file(repo / NUMERICAL_SPEC_REL),
            "code_sha256": sha256_file(repo / NUMERICAL_CODE_REL),
        },
    }
    if modules != expected_modules:
        raise CellBuildError("authorization module registry binding differs")
    expected_own = expected_modules["cells"]
    head = git_state["git_commit"]
    implementation = document.get("authorized_implementation_commit")
    if (
        not isinstance(implementation, str)
        or not re.fullmatch(r"[0-9a-f]{40}", implementation)
        or implementation == head
    ):
        raise CellBuildError("authorization implementation commit is invalid")
    ancestor = subprocess.run(
        [str(EXPECTED_GIT_PATH), "merge-base", "--is-ancestor", implementation, head],
        cwd=repo, env=SANITIZED_GIT_ENVIRONMENT, capture_output=True, check=False,
    )
    committed = subprocess.run(
        [str(EXPECTED_GIT_PATH), "show", f"{head}:{PRE_EXECUTION_AUTHORIZATION_REL}"],
        cwd=repo, env=SANITIZED_GIT_ENVIRONMENT, capture_output=True, check=False,
    )
    last_commit = subprocess.run(
        [str(EXPECTED_GIT_PATH), "log", "-1", "--format=%H", "--",
         str(PRE_EXECUTION_AUTHORIZATION_REL)],
        cwd=repo, env=SANITIZED_GIT_ENVIRONMENT, text=True,
        capture_output=True, check=False,
    )
    parent_commit = subprocess.run(
        [str(EXPECTED_GIT_PATH), "rev-parse", "HEAD^"],
        cwd=repo, env=SANITIZED_GIT_ENVIRONMENT, text=True,
        capture_output=True, check=False,
    )
    changed_paths = subprocess.run(
        [str(EXPECTED_GIT_PATH), "diff-tree", "--no-commit-id", "--name-only",
         "-r", "HEAD"],
        cwd=repo, env=SANITIZED_GIT_ENVIRONMENT, text=True,
        capture_output=True, check=False,
    )
    if (
        ancestor.returncode != 0
        or committed.returncode != 0
        or committed.stdout != path.read_bytes()
        or last_commit.returncode != 0
        or last_commit.stdout.strip() != head
        or parent_commit.returncode != 0
        or parent_commit.stdout.strip() != implementation
        or changed_paths.returncode != 0
        or changed_paths.stdout.splitlines()
        != [str(PRE_EXECUTION_AUTHORIZATION_REL)]
    ):
        raise CellBuildError(
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
        "module_key": "cells",
        "typed_spec_id": expected_own["typed_spec_id"],
        "typed_spec_sha256": expected_own["typed_spec_sha256"],
        "code_sha256": code_sha256,
        "source_registry_sha256": source_registry_sha,
    }


def support_hash(codes: Iterable[str]) -> str:
    normalized = sorted({str(code).zfill(4) for code in codes})
    payload = "".join(f"{code}\n" for code in normalized)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def month_range(start: str, end: str) -> list[str]:
    sy, sm = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    values: list[str] = []
    year, month = sy, sm
    while (year, month) <= (ey, em):
        values.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year, month = year + 1, 1
    return values


def path_is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise CellBuildError(f"missing required {label}")


def load_and_validate_specs(repo: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    cell_spec_path = repo / CELL_SPEC_REL
    canonical_path = repo / CANONICAL_SPEC_REL
    require_file(cell_spec_path, "cell-build specification")
    require_file(canonical_path, "canonical V2 specification")
    cell_spec = load_json(cell_spec_path)
    canonical = load_json(canonical_path)
    if cell_spec.get("cell_build_spec_id") != expected_cell_spec_id(cell_spec):
        raise CellBuildError("cell-build specification identifier is invalid")
    if canonical.get("spec_id") != EXPECTED_CANONICAL_SPEC_ID:
        raise CellBuildError("canonical V2 specification identifier changed")
    if cell_spec.get("canonical_spec_id") != canonical.get("spec_id"):
        raise CellBuildError("cell-build specification binds a different canonical contract")
    if cell_spec.get("canonical_spec_sha256") != sha256_file(canonical_path):
        raise CellBuildError("canonical V2 specification byte hash changed")
    if cell_spec.get("aggregate_schema_version") != CELL_SCHEMA:
        raise CellBuildError("cell-build specification has an incompatible output schema")
    grid = cell_spec.get("grid_contract", {})
    expected_occ = int(canonical["occupation"]["analysis_subset"]["occupation_count"])
    expected_months = int(canonical["calendar"]["observed_window"]["observed_month_count"])
    if grid.get("occupation_count") != expected_occ:
        raise CellBuildError("cell-build occupation count differs from canonical")
    if grid.get("observed_month_count") != expected_months:
        raise CellBuildError("cell-build month count differs from canonical")
    if grid.get("expected_rows") != expected_occ * expected_months:
        raise CellBuildError("cell-build row count is not occupation count times month count")
    reference = cell_spec.get("reference_artifacts", {})
    if reference.get("fixed_membership_sha256") != canonical["exposure"][
        "fixed_membership"
    ]["sha256"]:
        raise CellBuildError("cell-build membership lock differs from canonical")
    if reference.get("support_content_sha256") != canonical["occupation"]["universe"][
        "content_support_sha256"
    ]:
        raise CellBuildError("cell-build support lock differs from canonical")
    return cell_spec, canonical


def authenticate_hash_map(
    repo: Path,
    locks: Any,
    expected_paths: set[str],
    label: str,
) -> dict[str, str]:
    if not isinstance(locks, dict) or set(locks) != expected_paths:
        raise CellBuildError(f"cell-build specification has an incomplete {label} lock set")
    observed: dict[str, str] = {}
    for relative, expected in locks.items():
        path = repo / relative
        require_file(path, f"{label} lock {Path(relative).name}")
        digest = sha256_file(path)
        if digest != expected:
            raise CellBuildError(f"{label} hash changed: {relative}")
        observed[relative] = digest
    return observed


def authenticate_code(repo: Path, cell_spec: dict[str, Any]) -> dict[str, dict[str, str]]:
    return {
        "runtime": authenticate_hash_map(
            repo,
            cell_spec.get("runtime_code_hashes"),
            RUNTIME_CODE_PATHS,
            "runtime code",
        ),
        "historical_reference": authenticate_hash_map(
            repo,
            cell_spec.get("historical_reference_code_hashes"),
            REFERENCE_CODE_PATHS,
            "historical reference code",
        ),
    }


def transitive_code_fingerprint(code_hashes: dict[str, str]) -> str:
    builder_key = str(HERE_REL / "run_gate1_cells.py")
    transitive = {
        key: value for key, value in code_hashes.items() if key != builder_key
    }
    if builder_key not in code_hashes:
        raise CellBuildError("cannot fingerprint an incomplete runtime code lock")
    return hashlib.sha256(canonical_bytes(transitive)).hexdigest()


def validate_consumer_contract(
    repo: Path,
    cell_spec: dict[str, Any],
    canonical: dict[str, Any],
) -> dict[str, Any]:
    path = repo / NUMERICAL_SPEC_REL
    require_file(path, "numerical-existence analysis specification")
    analysis = load_json(path)
    if analysis.get("audit_spec_id") != expected_numerical_spec_id(analysis):
        raise CellBuildError("numerical-existence analysis specification ID is invalid")
    if analysis.get("canonical_spec_id") != canonical.get("spec_id"):
        raise CellBuildError("numerical-existence analysis uses another canonical contract")
    expected = cell_spec.get("consumer_contract", {})
    if analysis.get("audit_spec_id") != expected.get("analysis_spec_id"):
        raise CellBuildError("numerical-existence analysis specification ID changed")
    if sha256_file(path) != expected.get("analysis_spec_sha256"):
        raise CellBuildError("numerical-existence analysis specification byte hash changed")
    input_contract = analysis.get("input_contract", {})
    checks = {
        "aggregate_schema_version": input_contract.get("aggregate_schema_version")
        == CELL_SCHEMA,
        "cells_receipt_schema_version": input_contract.get("cells_receipt_schema_version")
        == RECEIPT_SCHEMA,
        "required_columns": input_contract.get("required_columns") == list(OUTPUT_COLUMNS),
        "weight_application_count": input_contract.get("weight_application_count") == 1,
        "balanced_grid_required": input_contract.get("balanced_grid_required") is True,
    }
    failed = sorted(key for key, passed in checks.items() if not passed)
    if failed:
        raise CellBuildError(
            "numerical-existence input contract is incompatible: " + ", ".join(failed)
        )
    return {
        "analysis_spec_id": analysis["audit_spec_id"],
        "analysis_spec_sha256": sha256_file(path),
        "input_contract_checks": checks,
    }


def parse_scc_environment_lock(text: str) -> dict[str, str]:
    patterns = {
        "python": r"^Python: ([^ ]+)",
        "python_compiler": r"^Python: [^ ]+ \((.+)\)$",
        "numpy": r"^numpy: (.+)$",
        "pandas": r"^pandas: (.+)$",
        "pytest": r"^pytest: (.+)$",
        "kernel_system": r"^SCC operating system: ([^ ]+)",
        "kernel_release": r"^SCC operating system: [^ ]+ ([^ ]+)",
        "machine": r"^SCC operating system: [^ ]+ [^ ]+ ([^,]+),",
        "libc": r"^SCC operating system: .+, glibc (.+)$",
    }
    result: dict[str, str] = {}
    for key, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.MULTILINE)
        if not match:
            raise CellBuildError(f"environment lock lacks required SCC field: {key}")
        result[key] = match.group(1).strip()
    return result


def observed_runtime() -> dict[str, str]:
    libc_name, libc_version = platform.libc_ver()
    return {
        "python": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "python_compiler": platform.python_compiler(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "pytest": importlib.metadata.version("pytest"),
        "scipy": importlib.metadata.version("scipy"),
        "kernel_system": platform.system(),
        "kernel_release": platform.release(),
        "machine": platform.machine(),
        "libc_name": libc_name,
        "libc": libc_version,
    }


def compare_runtime(expected: dict[str, str], observed: dict[str, str]) -> dict[str, Any]:
    mismatches = {
        key: {"observed": observed.get(key), "expected": value}
        for key, value in expected.items()
        if key != "kernel_release" and observed.get(key) != value
    }
    if observed.get("libc_name") != "glibc":
        mismatches["libc_name"] = {
            "observed": observed.get("libc_name"),
            "expected": "glibc",
        }
    if mismatches:
        raise CellBuildError(
            "runtime differs from authenticated SCC environment lock: "
            + json.dumps(mismatches, sort_keys=True)
        )
    return {
        "status": "AUTHENTICATED_DECLARED_RUNTIME",
        "observed": observed,
        "kernel_release_rule": (
            "recorded but nonbinding because SCC compute-node kernel patch levels may differ"
        ),
    }


def authenticate_runtime(repo: Path, cell_spec: dict[str, Any]) -> dict[str, Any]:
    contract = cell_spec.get("runtime_contract", {})
    if contract.get("command_template") != COMMAND_TEMPLATE:
        raise CellBuildError("sanitized command template differs from the immutable contract")
    if contract.get("kernel_release_binding") is not False:
        raise CellBuildError("SCC kernel patch must be recorded but explicitly nonbinding")
    path = repo / ENVIRONMENT_REL
    require_file(path, "SCC environment lock")
    digest = sha256_file(path)
    if contract.get("environment_lock_path") != str(ENVIRONMENT_REL):
        raise CellBuildError("environment-lock path differs from the immutable contract")
    if contract.get("environment_lock_sha256") != digest:
        raise CellBuildError("SCC environment-lock hash changed")
    expected = parse_scc_environment_lock(path.read_text(encoding="utf-8"))
    if contract.get("expected_runtime") != expected:
        raise CellBuildError("cell specification runtime values differ from its environment lock")
    observed = observed_runtime()
    result = compare_runtime(expected, observed)
    payload = {
        "architecture": observed["machine"],
        "libc": {
            "name": observed["libc_name"],
            "version": observed["libc"],
        },
        "packages": {
            "numpy": observed["numpy"],
            "pandas": observed["pandas"],
            "pytest": observed["pytest"],
            "scipy": observed["scipy"],
        },
        "python_compiler": observed["python_compiler"],
        "python_implementation": observed["python_implementation"],
        "python_version": observed["python"],
    }
    payload_hash = hashlib.sha256(canonical_bytes(payload)).hexdigest()
    if contract.get("runtime_payload") != payload:
        raise CellBuildError("runtime package payload differs from immutable contract")
    if contract.get("runtime_payload_sha256") != payload_hash:
        raise CellBuildError("runtime package payload hash differs from immutable contract")
    return {
        **result,
        "environment_lock_path": str(ENVIRONMENT_REL),
        "environment_lock_sha256": digest,
        "runtime_contract_sha256": hashlib.sha256(
            canonical_bytes(contract)
        ).hexdigest(),
        "runtime_payload": payload,
        "runtime_payload_sha256": payload_hash,
        "command_template": COMMAND_TEMPLATE,
    }


def git_command(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        [str(EXPECTED_GIT_PATH), *arguments],
        cwd=repo,
        env=SANITIZED_GIT_ENVIRONMENT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise CellBuildError(f"Git contract command failed: {' '.join(arguments)}")
    return completed.stdout.strip()


def git_blob_sha256(repo: Path, commit: str, relative: str) -> str:
    completed = subprocess.run(
        [str(EXPECTED_GIT_PATH), "show", f"{commit}:{relative}"],
        cwd=repo,
        env=SANITIZED_GIT_ENVIRONMENT,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise CellBuildError(f"required committed artifact is absent: {relative}")
    return hashlib.sha256(completed.stdout).hexdigest()


def authenticate_git(repo: Path, cell_spec: dict[str, Any]) -> dict[str, Any]:
    contract = cell_spec.get("git_contract", {})
    if contract.get("clean_worktree_required") is not True:
        raise CellBuildError("Git contract must require a clean worktree")
    if contract.get("live_files_must_equal_head_blobs") is not True:
        raise CellBuildError("Git contract must bind live files to committed blobs")
    if contract.get("runtime_head_and_tree_recorded") is not True:
        raise CellBuildError("Git contract must record runtime HEAD and tree")
    required_ancestor = contract.get("required_ancestor_commit")
    if not isinstance(required_ancestor, str) or not re.fullmatch(r"[0-9a-f]{40}", required_ancestor):
        raise CellBuildError("Git contract has an invalid required ancestor")
    head = git_command(repo, "rev-parse", "HEAD")
    tree = git_command(repo, "rev-parse", "HEAD^{tree}")
    if not re.fullmatch(r"[0-9a-f]{40}", head) or not re.fullmatch(r"[0-9a-f]{40}", tree):
        raise CellBuildError("Git HEAD or tree identifier is invalid")
    ancestor = subprocess.run(
        [str(EXPECTED_GIT_PATH), "merge-base", "--is-ancestor", required_ancestor, head],
        cwd=repo,
        env=SANITIZED_GIT_ENVIRONMENT,
        capture_output=True,
        check=False,
    )
    if ancestor.returncode != 0:
        raise CellBuildError("runtime Git HEAD does not descend from the required ancestor")
    status = git_command(repo, "status", "--porcelain=v1", "--untracked-files=all")
    if status:
        raise CellBuildError("runtime Git worktree is not clean")
    committed_paths = contract.get("committed_paths")
    expected_paths = {
        str(HERE_REL / "run_gate1_cells.py"),
        str(CELL_SPEC_REL),
        str(NUMERICAL_SPEC_REL),
        str(ENVIRONMENT_REL),
    }
    if not isinstance(committed_paths, list) or set(committed_paths) != expected_paths:
        raise CellBuildError("Git committed-path contract is incomplete")
    committed_hashes: dict[str, str] = {}
    for relative in committed_paths:
        live = sha256_file(repo / relative)
        committed = git_blob_sha256(repo, head, relative)
        if committed != live:
            raise CellBuildError(f"working file differs from committed Git blob: {relative}")
        committed_hashes[relative] = committed
    return {
        "git_status": "PASS_COMMITTED_CLEAN_WORKTREE",
        "git_commit": head,
        "git_tree": tree,
        "git_required_ancestor_commit": required_ancestor,
        "git_worktree_clean": True,
        "git_porcelain_sha256": hashlib.sha256(status.encode("utf-8")).hexdigest(),
        "git_committed_artifact_hashes": committed_hashes,
    }


def canonical_source_hashes(canonical: dict[str, Any]) -> dict[str, str]:
    sources = canonical.get("data", {}).get("sources", [])
    result: dict[str, str] = {}
    for row in sources:
        source_id = row.get("source_id")
        digest = row.get("sha256")
        if not isinstance(source_id, str) or not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
            raise CellBuildError("canonical source registry contains an invalid entry")
        if source_id in result:
            raise CellBuildError(f"duplicate canonical source identifier: {source_id}")
        result[source_id] = str(digest)
    return result


def authenticate_sources(
    repo: Path,
    canonical: dict[str, Any],
    microdata: Path,
    repair_microdata: Path,
) -> tuple[dict[str, str], dict[str, str]]:
    expected = canonical_source_hashes(canonical)
    observed: dict[str, str] = {}
    supplied = {
        "ipums_cps_extract_9_wide": microdata,
        "ipums_cps_extract_11_march_basic_repair": repair_microdata,
        **{key: repo / value for key, value in REPO_SOURCE_PATHS.items()},
    }
    for source_id, path in supplied.items():
        if source_id not in expected:
            raise CellBuildError(f"canonical source registry omits {source_id}")
        require_file(path, f"source {source_id}")
        digest = sha256_file(path)
        if digest != expected[source_id]:
            raise CellBuildError(f"source hash mismatch: {source_id}")
        observed[source_id] = digest
    # `source_hashes` in the downstream receipt is the complete canonical
    # registry. `observed` separately distinguishes files this builder actually
    # hashed from the historical aggregate that it deliberately did not read.
    return expected, observed


def validate_authorization(repo: Path, source_hashes: dict[str, str]) -> dict[str, Any]:
    receipt = load_json(repo / REPO_SOURCE_PATHS["first_post_outcome_access_receipt"])
    checks = {
        "status": receipt.get("status") == "AUTHORIZED_FIRST_POST_FREEZE_OUTCOME_ACCESS",
        "frozen_tag": receipt.get("frozen_tag") == "v1.1-design-freeze",
        "microdata_sha256": receipt.get("microdata_sha256")
        == source_hashes["ipums_cps_extract_9_wide"],
    }
    failed = sorted(key for key, passed in checks.items() if not passed)
    if failed:
        raise CellBuildError("first-access authorization failed: " + ", ".join(failed))
    return {
        "status": "PASS_AUTHORIZATION_CHAIN",
        "checks": checks,
        "repair_source_bound_by_canonical_v2": True,
    }


def inspect_required_raw_columns(path: Path, source_id: str) -> list[str]:
    try:
        columns = list(pd.read_csv(path, nrows=0).columns)
    except Exception as exc:
        raise CellBuildError(f"could not read the {source_id} header: {exc}") from exc
    missing = sorted(set(REQUIRED_RAW_COLUMNS) - set(columns))
    if missing:
        raise CellBuildError(f"{source_id} lacks canonical-V2 raw fields: {missing}")
    return columns


def load_bridge(path: Path) -> tuple[pd.DataFrame, dict[str, float]]:
    bridge = pd.read_csv(path, dtype={"census_2010": str, "census_2018": str})
    required = ["census_2010", "census_2018", "bridge_weight"]
    if not set(required).issubset(bridge.columns):
        raise CellBuildError("authenticated bridge lacks required route columns")
    bridge = bridge[required].copy()
    bridge["census_2010"] = bridge.census_2010.str.zfill(4)
    bridge["census_2018"] = bridge.census_2018.str.zfill(4)
    bridge["bridge_weight"] = pd.to_numeric(bridge.bridge_weight, errors="raise")
    if not np.isfinite(bridge.bridge_weight).all() or (bridge.bridge_weight < 0).any():
        raise CellBuildError("bridge weights must be finite and nonnegative")
    if bridge[["census_2010", "census_2018"]].duplicated().any():
        raise CellBuildError("bridge contains duplicate source-target routes")
    mass = bridge.groupby("census_2010", observed=True).bridge_weight.sum()
    if not np.isfinite(mass).all() or not np.allclose(
        mass.to_numpy(float), 1.0, rtol=0.0, atol=1e-12
    ):
        raise CellBuildError("bridge route mass differs from one")
    return bridge, {str(key): float(value) for key, value in mass.items()}


def month_string(frame: pd.DataFrame) -> pd.Series:
    year = pd.to_numeric(frame.YEAR, errors="raise").astype(int)
    month = pd.to_numeric(frame.MONTH, errors="raise").astype(int)
    if not month.between(1, 12).all():
        raise CellBuildError("raw CPS month is outside 1 through 12")
    return year.astype(str) + "-" + month.astype(str).str.zfill(2)


def build_six_field_target_cells(
    microdata: Path,
    repair_microdata: Path,
    bridge_path: Path,
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, Any]]:
    """Reconstruct only target stocks with the canonical six CPS fields.

    `OCC2010` and `IND1990` in the historical general-purpose builder fed
    outputs that this Gate-1 object discarded. This target router therefore
    implements only the operative raw-OCC route and age-stock aggregation.
    """
    bridge, route_mass = load_bridge(bridge_path)
    pieces: list[pd.DataFrame] = []
    per_source_counter_names = (
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
    )
    counters: dict[str, Any] = {
        "source_ids": list(RAW_SOURCE_ARGUMENTS),
        "physical_rows_read_total": 0,
        "physical_rows_read_by_source": {
            source_id: 0 for source_id in RAW_SOURCE_ARGUMENTS
        },
        "eligible_employed_age_22_65_records_total": 0,
        "eligible_employed_age_22_65_records_by_source": {
            source_id: 0 for source_id in RAW_SOURCE_ARGUMENTS
        },
        "invalid_raw_occ_records": 0,
        "wide_march_rows_explicitly_replaced": 0,
        "wide_march_positive_weight_rows_explicitly_replaced": 0,
        "repair_eligible_employed_age_22_65_records": 0,
        "routed_rows": 0,
        **{
            f"{name}_by_source": {
                source_id: 0 for source_id in RAW_SOURCE_ARGUMENTS
            }
            for name in per_source_counter_names
        },
    }
    conservation = {
        "raw_early_valid_stock": 0.0,
        "raw_early_matched_stock": 0.0,
        "expected_early_routed_stock": 0.0,
        "raw_current_valid_stock": 0.0,
    }
    conservation_by_source = {
        source_id: {
            "raw_early_valid_stock": 0.0,
            "raw_early_matched_stock": 0.0,
            "expected_early_routed_stock": 0.0,
            "actual_early_routed_stock": 0.0,
            "raw_current_valid_stock": 0.0,
            "actual_current_direct_stock": 0.0,
        }
        for source_id in RAW_SOURCE_ARGUMENTS
    }
    repair_observed_months: set[str] = set()
    inputs = (
        ("ipums_cps_extract_9_wide", microdata, True),
        ("ipums_cps_extract_11_march_basic_repair", repair_microdata, False),
    )
    for source_id, path, is_primary in inputs:
        for chunk in pd.read_csv(path, usecols=list(REQUIRED_RAW_COLUMNS), chunksize=500_000):
            counters["physical_rows_read_total"] += len(chunk)
            counters["physical_rows_read_by_source"][source_id] += len(chunk)
            chunk = chunk.copy()
            chunk["month"] = month_string(chunk)
            weight = pd.to_numeric(chunk.WTFINL, errors="coerce")
            if is_primary:
                replaced = chunk.month.isin(MARCH_REPAIR_MONTHS)
                counters["wide_march_rows_explicitly_replaced"] += int(replaced.sum())
                counters["wide_march_positive_weight_rows_explicitly_replaced"] += int(
                    (replaced & np.isfinite(weight) & weight.gt(0)).sum()
                )
            else:
                repair_observed_months.update(chunk.month.unique())
                if not chunk.month.isin(MARCH_REPAIR_MONTHS).all():
                    raise CellBuildError("March repair extract contains a non-repair month")
                replaced = pd.Series(False, index=chunk.index, dtype=bool)
            age = pd.to_numeric(chunk.AGE, errors="coerce")
            employed = pd.to_numeric(chunk.EMPSTAT, errors="coerce").isin([10, 12])
            keep = age.between(22, 65) & employed & np.isfinite(weight) & weight.gt(0) & ~replaced
            chunk = chunk.loc[keep].copy()
            if not is_primary:
                counters["repair_eligible_employed_age_22_65_records"] += len(chunk)
            counters["eligible_employed_age_22_65_records_total"] += len(chunk)
            counters["eligible_employed_age_22_65_records_by_source"][source_id] += len(
                chunk
            )
            chunk["age"] = age.loc[chunk.index].astype(int)
            chunk["survey_stock"] = weight.loc[chunk.index].astype(float)
            occ = pd.to_numeric(chunk.OCC, errors="coerce")
            valid = occ.notna() & occ.between(0, 9999) & occ.mod(1).eq(0)
            invalid_count = int((~valid).sum())
            valid_count = int(valid.sum())
            counters["invalid_raw_occ_records"] += invalid_count
            counters["invalid_raw_occ_records_by_source"][source_id] += invalid_count
            counters["valid_raw_occ_records_by_source"][source_id] += valid_count
            chunk = chunk.loc[valid].copy()
            chunk["source_occ"] = occ.loc[chunk.index].astype(int).map(
                lambda value: f"{value:04d}"
            )

            early_input = chunk.loc[pd.to_numeric(chunk.YEAR, errors="raise").le(2019)].copy()
            current = chunk.loc[pd.to_numeric(chunk.YEAR, errors="raise").ge(2020)].copy()
            early_valid_count = len(early_input)
            current_valid_count = len(current)
            counters["early_valid_source_records_by_source"][source_id] += early_valid_count
            counters["current_valid_source_records_by_source"][source_id] += current_valid_count
            conservation["raw_early_valid_stock"] += float(early_input.survey_stock.sum())
            conservation_by_source[source_id]["raw_early_valid_stock"] += float(
                early_input.survey_stock.sum()
            )
            early_input["route_mass"] = early_input.source_occ.map(route_mass)
            matched = early_input.route_mass.notna()
            matched_count = int(matched.sum())
            unmatched_count = int((~matched).sum())
            counters["early_matched_source_records_by_source"][source_id] += matched_count
            counters["early_unmatched_source_records_by_source"][source_id] += unmatched_count
            conservation["raw_early_matched_stock"] += float(
                early_input.loc[matched, "survey_stock"].sum()
            )
            conservation_by_source[source_id]["raw_early_matched_stock"] += float(
                early_input.loc[matched, "survey_stock"].sum()
            )
            conservation["expected_early_routed_stock"] += float(
                (
                    early_input.loc[matched, "survey_stock"]
                    * early_input.loc[matched, "route_mass"]
                ).sum()
            )
            conservation_by_source[source_id]["expected_early_routed_stock"] += float(
                (
                    early_input.loc[matched, "survey_stock"]
                    * early_input.loc[matched, "route_mass"]
                ).sum()
            )
            early = early_input.loc[matched].merge(
                bridge,
                left_on="source_occ",
                right_on="census_2010",
                how="inner",
                validate="many_to_many",
            )
            early["occ_code"] = early.census_2018
            early["stock"] = early.survey_stock * early.bridge_weight
            early["route_kind"] = "probabilistic_2010_to_2018"
            bridge_weight = early.bridge_weight.to_numpy(float)
            zero_route = bridge_weight == 0.0
            unit_route = bridge_weight == 1.0
            fractional_route = (bridge_weight > 0.0) & (bridge_weight < 1.0)
            if np.any(bridge_weight < 0.0) or np.any(bridge_weight > 1.0):
                raise CellBuildError("bridge contribution lies outside zero through one")
            if int(zero_route.sum() + unit_route.sum() + fractional_route.sum()) != len(early):
                raise CellBuildError("early route-contribution classification failed")
            counters["early_expanded_route_descendants_by_source"][source_id] += len(early)
            counters["early_fractional_route_contributions_by_source"][source_id] += int(
                fractional_route.sum()
            )
            counters["early_unit_route_contributions_by_source"][source_id] += int(
                unit_route.sum()
            )
            counters["early_zero_mass_route_contributions_by_source"][source_id] += int(
                zero_route.sum()
            )
            conservation_by_source[source_id]["actual_early_routed_stock"] += float(
                early.stock.sum()
            )
            conservation["raw_current_valid_stock"] += float(current.survey_stock.sum())
            conservation_by_source[source_id]["raw_current_valid_stock"] += float(
                current.survey_stock.sum()
            )
            current["occ_code"] = current.source_occ
            current["stock"] = current.survey_stock
            current["route_kind"] = "direct_2018"
            counters["current_direct_route_contributions_by_source"][source_id] += len(
                current
            )
            conservation_by_source[source_id]["actual_current_direct_stock"] += float(
                current.stock.sum()
            )
            routed = pd.concat(
                [
                    early[["occ_code", "month", "age", "route_kind", "stock"]],
                    current[["occ_code", "month", "age", "route_kind", "stock"]],
                ],
                ignore_index=True,
            )
            counters["routed_rows"] += len(routed)
            counters["routed_contribution_rows_by_source"][source_id] += len(routed)
            pieces.append(
                routed.groupby(
                    ["occ_code", "month", "age", "route_kind"],
                    as_index=False,
                    observed=True,
                ).stock.sum()
            )
    if repair_observed_months != MARCH_REPAIR_MONTHS:
        raise CellBuildError("March repair extract does not contain exactly the five repair months")
    if not pieces:
        raise CellBuildError("six-field target router produced no pieces")

    for name in per_source_counter_names:
        counters[name] = int(sum(counters[f"{name}_by_source"].values()))
    # Keep the historical field but make its meaning and identity explicit.
    if counters["routed_rows"] != counters["routed_contribution_rows"]:
        raise CellBuildError("routed-row compatibility counter changed meaning")

    record_identities_by_source: dict[str, dict[str, bool]] = {}
    for source_id in RAW_SOURCE_ARGUMENTS:
        eligible = counters["eligible_employed_age_22_65_records_by_source"][source_id]
        invalid = counters["invalid_raw_occ_records_by_source"][source_id]
        valid_records = counters["valid_raw_occ_records_by_source"][source_id]
        early_valid = counters["early_valid_source_records_by_source"][source_id]
        current_valid = counters["current_valid_source_records_by_source"][source_id]
        early_matched = counters["early_matched_source_records_by_source"][source_id]
        early_unmatched = counters["early_unmatched_source_records_by_source"][source_id]
        descendants = counters["early_expanded_route_descendants_by_source"][source_id]
        fractional = counters["early_fractional_route_contributions_by_source"][source_id]
        unit = counters["early_unit_route_contributions_by_source"][source_id]
        zero_mass = counters["early_zero_mass_route_contributions_by_source"][source_id]
        direct = counters["current_direct_route_contributions_by_source"][source_id]
        routed = counters["routed_contribution_rows_by_source"][source_id]
        identities = {
            "eligible_equals_invalid_plus_valid": eligible == invalid + valid_records,
            "valid_equals_early_plus_current": valid_records == early_valid + current_valid,
            "early_equals_matched_plus_unmatched": early_valid == early_matched + early_unmatched,
            "expanded_descendants_cover_each_matched_record": (
                descendants >= early_matched
            ),
            "early_descendants_partition_by_route_weight": (
                descendants == fractional + unit + zero_mass
            ),
            "direct_contributions_equal_current_valid_records": direct == current_valid,
            "routed_contributions_equal_descendants_plus_direct": (
                routed == descendants + direct
            ),
        }
        if not all(identities.values()):
            failed = sorted(key for key, passed in identities.items() if not passed)
            raise CellBuildError(
                f"source-record reconciliation failed for {source_id}: {failed}"
            )
        record_identities_by_source[source_id] = identities

    total_record_identities = {
        "physical_total_equals_source_sum": counters["physical_rows_read_total"]
        == sum(counters["physical_rows_read_by_source"].values()),
        "eligible_total_equals_source_sum": counters[
            "eligible_employed_age_22_65_records_total"
        ]
        == sum(counters["eligible_employed_age_22_65_records_by_source"].values()),
        "eligible_equals_invalid_plus_valid": counters[
            "eligible_employed_age_22_65_records_total"
        ]
        == counters["invalid_raw_occ_records"] + counters["valid_raw_occ_records"],
        "valid_equals_early_plus_current": counters["valid_raw_occ_records"]
        == counters["early_valid_source_records"] + counters["current_valid_source_records"],
        "early_equals_matched_plus_unmatched": counters["early_valid_source_records"]
        == counters["early_matched_source_records"]
        + counters["early_unmatched_source_records"],
        "early_descendants_partition_by_route_weight": counters[
            "early_expanded_route_descendants"
        ]
        == counters["early_fractional_route_contributions"]
        + counters["early_unit_route_contributions"]
        + counters["early_zero_mass_route_contributions"],
        "direct_contributions_equal_current_valid_records": counters[
            "current_direct_route_contributions"
        ]
        == counters["current_valid_source_records"],
        "routed_contributions_equal_descendants_plus_direct": counters[
            "routed_contribution_rows"
        ]
        == counters["early_expanded_route_descendants"]
        + counters["current_direct_route_contributions"],
    }
    if not all(total_record_identities.values()):
        failed = sorted(key for key, passed in total_record_identities.items() if not passed)
        raise CellBuildError("total source-record reconciliation failed: " + ", ".join(failed))
    cells = pd.concat(pieces, ignore_index=True).groupby(
        ["occ_code", "month", "age", "route_kind"],
        as_index=False,
        observed=True,
    ).stock.sum()
    actual_early = float(
        cells.loc[cells.route_kind.eq("probabilistic_2010_to_2018"), "stock"].sum()
    )
    actual_current = float(cells.loc[cells.route_kind.eq("direct_2018"), "stock"].sum())
    early_gap = actual_early - conservation["expected_early_routed_stock"]
    current_gap = actual_current - conservation["raw_current_valid_stock"]
    early_scale = max(abs(conservation["expected_early_routed_stock"]), 1.0)
    current_scale = max(abs(conservation["raw_current_valid_stock"]), 1.0)
    source_stock_reconciliation: dict[str, dict[str, Any]] = {}
    for source_id, values in conservation_by_source.items():
        early_source_gap = (
            values["actual_early_routed_stock"]
            - values["expected_early_routed_stock"]
        )
        current_source_gap = (
            values["actual_current_direct_stock"]
            - values["raw_current_valid_stock"]
        )
        early_source_scale = max(abs(values["expected_early_routed_stock"]), 1.0)
        current_source_scale = max(abs(values["raw_current_valid_stock"]), 1.0)
        source_stock_reconciliation[source_id] = {
            **values,
            "early_absolute_gap": early_source_gap,
            "early_relative_gap": early_source_gap / early_source_scale,
            "current_absolute_gap": current_source_gap,
            "current_relative_gap": current_source_gap / current_source_scale,
            "unmatched_early_stock": (
                values["raw_early_valid_stock"] - values["raw_early_matched_stock"]
            ),
            "route_conservation_pass": (
                abs(early_source_gap) / early_source_scale < 1e-10
                and abs(current_source_gap) / current_source_scale < 1e-10
            ),
        }
    route_receipt = {
        **conservation,
        "actual_early_routed_stock": actual_early,
        "actual_current_direct_stock": actual_current,
        "early_absolute_gap": early_gap,
        "early_relative_gap": early_gap / early_scale,
        "current_absolute_gap": current_gap,
        "current_relative_gap": current_gap / current_scale,
        "unmatched_early_stock": (
            conservation["raw_early_valid_stock"]
            - conservation["raw_early_matched_stock"]
        ),
        "bridge_source_count": len(route_mass),
        "bridge_mass_min": min(route_mass.values()),
        "bridge_mass_max": max(route_mass.values()),
        "record_count_definitions": {
            "physical_rows": "integer input-file records before filtering",
            "eligible_records": "integer employed age-22-through-65 positive-weight source records after explicit March replacement and before occupation routing",
            "expanded_route_descendants": "integer early-period source-to-destination bridge rows after matching; not respondents",
            "fractional_route_contributions": "expanded early bridge rows with route weight strictly between zero and one",
            "aggregate_rows": "unique occupation-month-age-route cells after summing routed contributions",
        },
        "record_identities_by_source": record_identities_by_source,
        "total_record_identities": total_record_identities,
        "source_stock_reconciliation": source_stock_reconciliation,
        "route_conservation_pass": (
            abs(early_gap) / early_scale < 1e-10
            and abs(current_gap) / current_scale < 1e-10
            and all(
                value["route_conservation_pass"]
                for value in source_stock_reconciliation.values()
            )
        ),
    }
    if route_receipt["route_conservation_pass"] is not True:
        raise CellBuildError("six-field source-route conservation failed")
    counters.update(
        {
            "aggregate_rows": len(cells),
            "observed_month_count": int(cells.month.nunique()),
            "repair_observed_months": sorted(repair_observed_months),
            "runtime_raw_fields": list(REQUIRED_RAW_COLUMNS),
        }
    )
    return cells, counters, route_receipt


def load_measure_maps(
    lookup_path: Path,
    computerization_path: Path,
) -> tuple[dict[str, float], dict[str, float], dict[str, str], dict[str, str]]:
    lookup = pd.read_csv(lookup_path, dtype={"occ_code": str})
    required_lookup = {
        "lookup_role",
        "occ_code",
        "dv_rating_beta",
        "dv_rating_beta_covered_route_mass",
    }
    if not required_lookup.issubset(lookup.columns):
        raise CellBuildError("exposure lookup lacks strict Rule-A beta fields")
    lookup = lookup.loc[lookup.lookup_role.eq("raw_occ_main_2020_plus")].copy()
    lookup["occ_code"] = lookup.occ_code.str.zfill(4)
    if lookup.occ_code.duplicated().any():
        raise CellBuildError("exposure lookup duplicates Census-2018 occupation codes")
    mass = pd.to_numeric(lookup.dv_rating_beta_covered_route_mass, errors="coerce")
    beta = pd.to_numeric(lookup.dv_rating_beta, errors="coerce").where(
        np.isclose(mass, 1.0)
    )
    beta_map = dict(zip(lookup.occ_code, beta))

    comp = pd.read_csv(computerization_path, dtype={"census2018": str})
    required_comp = {"census2018", "occupation", "soc_major_group", "webb_pct_software"}
    if not required_comp.issubset(comp.columns):
        raise CellBuildError("computerization lookup lacks Webb or SOC2 fields")
    comp["census2018"] = comp.census2018.str.zfill(4)
    if comp.census2018.duplicated().any():
        raise CellBuildError("computerization lookup duplicates Census-2018 codes")
    webb = pd.to_numeric(comp.webb_pct_software, errors="coerce")
    return (
        beta_map,
        dict(zip(comp.census2018, webb)),
        dict(zip(comp.census2018, comp.occupation.astype(str))),
        dict(zip(comp.census2018, comp.soc_major_group.astype(str))),
    )


def weighted_contract(
    values: np.ndarray,
    weights: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float, float]:
    if len(values) != len(weights) or len(values) == 0:
        raise CellBuildError("weighted contract inputs are empty or unaligned")
    if not np.isfinite(values).all() or not np.isfinite(weights).all() or np.any(weights <= 0):
        raise CellBuildError("weighted contract requires finite values and positive weights")
    order = np.argsort(values, kind="mergesort")
    cumulative = np.cumsum(weights[order])
    cuts = np.array(
        [
            values[
                order[
                    min(
                        np.searchsorted(cumulative, share * cumulative[-1], side="left"),
                        len(values) - 1,
                    )
                ]
            ]
            for share in (0.2, 0.4, 0.6, 0.8)
        ],
        dtype=float,
    )
    if np.any(cuts[:-1] >= cuts[1:]):
        raise CellBuildError("employment-weighted beta cutoffs collapse")
    groups = np.searchsorted(cuts, values, side="left") + 1
    mean = float(np.average(values, weights=weights))
    sd = float(np.sqrt(np.average(np.square(values - mean), weights=weights)))
    if not math.isfinite(sd) or sd <= 0:
        raise CellBuildError("weighted normalization has zero variance")
    return groups.astype(int), cuts, mean, sd


def build_recomputed_contract(
    cells: pd.DataFrame,
    beta_map: dict[str, float],
    webb_map: dict[str, float],
    names: dict[str, str],
) -> dict[str, Any]:
    expected_pre = month_range("2017-01", "2022-11")
    observed_pre = sorted(
        cells.loc[cells.month.between(expected_pre[0], expected_pre[-1]), "month"].unique()
    )
    if observed_pre != expected_pre:
        raise CellBuildError("six-field router lacks the exact 71-month preperiod")
    pre = cells.loc[cells.month.isin(expected_pre)].copy()
    pre["age_group"] = np.where(
        pre.age.between(22, 25),
        "young",
        np.where(pre.age.between(26, 65), "older", "drop"),
    )
    pre = pre.loc[pre.age_group.ne("drop")]
    totals = pre.groupby(["occ_code", "age_group"], observed=True).stock.sum().unstack(
        fill_value=0.0
    )
    for group in ("young", "older"):
        if group not in totals:
            totals[group] = 0.0
    support = []
    for code in sorted(totals.index):
        if (
            float(totals.at[code, "young"]) > 0
            and float(totals.at[code, "older"]) > 0
            and np.isfinite(beta_map.get(code, np.nan))
            and np.isfinite(webb_map.get(code, np.nan))
        ):
            support.append(code)
    if not support:
        raise CellBuildError("fresh six-field support is empty")
    weights = np.array(
        [float(totals.loc[code, ["young", "older"]].sum()) for code in support]
    )
    beta_values = np.array([float(beta_map[code]) for code in support])
    webb_values = np.array([float(webb_map[code]) for code in support])
    quintiles, cuts, beta_mean, beta_sd = weighted_contract(beta_values, weights)
    _, _, webb_mean, webb_sd = weighted_contract(webb_values, weights)
    webb_z = (webb_values - webb_mean) / webb_sd
    membership = [
        {
            "occupation_code": code,
            "occupation_name": names.get(code, code),
            "preperiod_weight": float(weight),
            "rule_A_beta": float(beta),
            "beta_quintile": int(quintile),
            "webb_pct_software": float(webb),
            "webb_z": float(wz),
        }
        for code, weight, beta, quintile, webb, wz in zip(
            support, weights, beta_values, quintiles, webb_values, webb_z
        )
    ]
    return {
        "support": support,
        "membership": membership,
        "cuts": cuts,
        "normalization": {
            "construction_months": 71,
            "construction_start": "2017-01",
            "construction_end": "2022-11",
            "beta_weighted_mean": beta_mean,
            "beta_weighted_sd": beta_sd,
            "webb_weighted_mean": webb_mean,
            "webb_weighted_sd": webb_sd,
            "total_preperiod_stock": float(weights.sum()),
            "no_postperiod_stock_used": True,
            "postperiod_stock_used": 0.0,
        },
    }


def panel_for_ages(
    cells: pd.DataFrame,
    support: list[str],
    months: list[str],
    young_range: tuple[int, int],
    older_range: tuple[int, int],
) -> tuple[np.ndarray, np.ndarray]:
    selected = cells.loc[cells.occ_code.isin(support) & cells.month.isin(months)].copy()
    selected["age_group"] = np.where(
        selected.age.between(*young_range),
        "young",
        np.where(selected.age.between(*older_range), "older", "drop"),
    )
    selected = selected.loc[selected.age_group.ne("drop")]
    grouped = selected.groupby(
        ["occ_code", "month", "age_group"], as_index=False, observed=True
    ).stock.sum()
    index = pd.MultiIndex.from_product([support, months], names=["occ_code", "month"])
    pivot = grouped.pivot_table(
        index=["occ_code", "month"],
        columns="age_group",
        values="stock",
        aggfunc="sum",
        fill_value=0.0,
    ).reindex(index, fill_value=0.0)
    for group in ("young", "older"):
        if group not in pivot:
            pivot[group] = 0.0
    return (
        pivot.young.to_numpy().reshape(len(support), len(months)),
        pivot.older.to_numpy().reshape(len(support), len(months)),
    )


def load_fixed_assignments(
    repo: Path,
    canonical: dict[str, Any],
    family_map: dict[str, str],
) -> pd.DataFrame:
    path = repo / MEMBERSHIP_REL
    require_file(path, "fixed treatment membership")
    expected = canonical["exposure"]["fixed_membership"]["sha256"]
    if sha256_file(path) != expected:
        raise CellBuildError("fixed treatment-membership hash changed")
    with path.open("r", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    required = {"occupation_code", "beta_quintile", "webb_z"}
    if not rows or not required.issubset(rows[0]):
        raise CellBuildError("fixed membership lacks required assignment columns")
    assignments = []
    for row in rows:
        code = str(row["occupation_code"]).zfill(4)
        family = family_map.get(code)
        if family is None or not re.fullmatch(r"\d{2}", str(family)):
            raise CellBuildError(f"missing SOC2 family for canonical occupation {code}")
        try:
            quintile = int(row["beta_quintile"])
            webb_z = float(row["webb_z"])
        except (TypeError, ValueError) as exc:
            raise CellBuildError(f"invalid fixed assignment for occupation {code}") from exc
        if quintile not in {1, 2, 3, 4, 5} or not math.isfinite(webb_z):
            raise CellBuildError(f"invalid fixed assignment for occupation {code}")
        assignments.append(
            {
                "occ_code": code,
                "family": str(family),
                "beta_quintile": quintile,
                "webb_z": webb_z,
            }
        )
    frame = pd.DataFrame(assignments).sort_values("occ_code", kind="mergesort")
    if frame.occ_code.duplicated().any():
        raise CellBuildError("fixed membership contains duplicate occupation codes")
    expected_count = int(canonical["occupation"]["analysis_subset"]["occupation_count"])
    if len(frame) != expected_count:
        raise CellBuildError("fixed membership occupation count changed")
    expected_support = canonical["occupation"]["universe"]["content_support_sha256"]
    if support_hash(frame.occ_code) != expected_support:
        raise CellBuildError("fixed membership support hash changed")
    return frame.reset_index(drop=True)


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


def validate_rebuilt_contract(
    rebuilt: dict[str, Any],
    fixed: pd.DataFrame,
    canonical: dict[str, Any],
    cell_spec: dict[str, Any],
) -> dict[str, Any]:
    rebuilt_rows = {
        str(row["occupation_code"]).zfill(4): row for row in rebuilt["membership"]
    }
    fixed_codes = fixed.occ_code.tolist()
    if sorted(rebuilt_rows) != fixed_codes:
        raise CellBuildError("fresh preperiod support differs from fixed membership")
    quintile_mismatches: list[str] = []
    webb_differences: list[float] = []
    for row in fixed.itertuples(index=False):
        rebuilt_row = rebuilt_rows[row.occ_code]
        if int(rebuilt_row["beta_quintile"]) != int(row.beta_quintile):
            quintile_mismatches.append(row.occ_code)
        webb_differences.append(abs(float(rebuilt_row["webb_z"]) - float(row.webb_z)))
    if quintile_mismatches:
        raise CellBuildError("fresh beta-quintile assignments differ from the fixed contract")
    tolerance = float(cell_spec["assignment_contract"]["rebuild_webb_z_tolerance"])
    max_webb_gap = max(webb_differences, default=0.0)
    if max_webb_gap > tolerance:
        raise CellBuildError("fresh Webb normalization differs from the fixed contract")

    observed_cuts = [float(value) for value in rebuilt["cuts"]]
    expected_cuts = [float(value) for value in canonical["exposure"]["cutoffs"]]
    if observed_cuts != expected_cuts:
        raise CellBuildError("fresh beta cutoffs differ from the canonical contract")
    normalization = rebuilt["normalization"]
    expected_webb = canonical["exposure"]["webb_normalization"]
    if float(normalization["webb_weighted_mean"]) != float(expected_webb["mean"]):
        raise CellBuildError("fresh Webb weighted mean differs from canonical")
    if float(normalization["webb_weighted_sd"]) != float(expected_webb["sd"]):
        raise CellBuildError("fresh Webb weighted SD differs from canonical")
    return {
        "fresh_support_matches_fixed": True,
        "fresh_quintiles_match_fixed": True,
        "fresh_webb_z_matches_fixed_within_declared_tolerance": True,
        "maximum_webb_z_absolute_difference": max_webb_gap,
        "rebuild_webb_z_tolerance": tolerance,
        "beta_quintile_cuts": observed_cuts,
        "webb_weighted_mean": float(normalization["webb_weighted_mean"]),
        "webb_weighted_sd": float(normalization["webb_weighted_sd"]),
        "construction_month_count": int(normalization["construction_months"]),
        "no_postperiod_stock_used": normalization["no_postperiod_stock_used"] is True,
    }


def expected_observed_months(canonical: dict[str, Any]) -> list[str]:
    observed = canonical["calendar"]["observed_window"]
    missing = set(canonical["calendar"]["missing_handling"]["missing_months"])
    return [month for month in month_range(*observed["range"]) if month not in missing]


def validate_calendar(cells: pd.DataFrame, canonical: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    observed = sorted(str(value) for value in cells.month.unique())
    expected = expected_observed_months(canonical)
    if observed != expected:
        raise CellBuildError("fresh routed cells differ from the canonical observed calendar")
    preperiod = [month for month in observed if "2017-01" <= month <= "2022-11"]
    expected_preperiod = month_range("2017-01", "2022-11")
    if preperiod != expected_preperiod:
        raise CellBuildError("fresh routed cells lack the exact 71-month preperiod")
    repaired_march = [f"{year}-03" for year in range(2017, 2022)]
    if not set(repaired_march).issubset(observed):
        raise CellBuildError("March Basic repair months are incomplete")
    return observed, {
        "status": "PASS_CALENDAR",
        "observed_month_count": len(observed),
        "observed_start": observed[0],
        "observed_end": observed[-1],
        "missing_months": canonical["calendar"]["missing_handling"]["missing_months"],
        "transition_2022_12_present": "2022-12" in observed,
        "october_2025_absent_not_interpolated": "2025-10" not in observed,
        "preperiod_month_count": len(preperiod),
        "restored_march_months": repaired_march,
    }


def build_balanced_output(
    routed_cells: pd.DataFrame,
    fixed: pd.DataFrame,
    months: list[str],
) -> tuple[pd.DataFrame, dict[str, Any]]:
    support = fixed.occ_code.tolist()
    young, older = panel_for_ages(
        routed_cells, support, months, (22, 25), (26, 65)
    )
    expected_shape = (len(support), len(months))
    if young.shape != expected_shape or older.shape != expected_shape:
        raise CellBuildError("R3 panel builder returned an unexpected shape")
    if not np.isfinite(young).all() or not np.isfinite(older).all():
        raise CellBuildError("aggregate stocks contain nonfinite values")
    if np.any(young < 0) or np.any(older < 0):
        raise CellBuildError("aggregate stocks contain negative values")

    # Independent grouped-sum identity: the survey weight is already embedded
    # once in routed_cells.stock.  No second multiplication is performed here.
    selected = routed_cells.loc[
        routed_cells.occ_code.isin(support) & routed_cells.month.isin(months)
    ].copy()
    selected["age_group"] = np.where(
        selected.age.between(22, 25),
        "young",
        np.where(selected.age.between(26, 65), "older", "drop"),
    )
    selected = selected.loc[selected.age_group.ne("drop")]
    grouped = selected.groupby(
        ["occ_code", "month", "age_group"], as_index=False, observed=True
    ).stock.sum()
    grid = pd.MultiIndex.from_product([support, months], names=["occ_code", "month"])
    pivot = grouped.pivot_table(
        index=["occ_code", "month"],
        columns="age_group",
        values="stock",
        aggfunc="sum",
        fill_value=0.0,
    ).reindex(grid, fill_value=0.0)
    for column in ("young", "older"):
        if column not in pivot:
            pivot[column] = 0.0
    independent_young = pivot.young.to_numpy().reshape(expected_shape)
    independent_older = pivot.older.to_numpy().reshape(expected_shape)
    max_gap = max(
        float(np.max(np.abs(independent_young - young))),
        float(np.max(np.abs(independent_older - older))),
    )
    if max_gap != 0.0:
        raise CellBuildError("weight-once independent aggregation identity failed")

    result = pd.DataFrame(
        {
            "occ_code": np.repeat(np.asarray(support, object), len(months)),
            "month": np.tile(np.asarray(months, object), len(support)),
            "young": young.reshape(-1),
            "older": older.reshape(-1),
        }
    )
    result = result.merge(fixed, on="occ_code", how="left", validate="many_to_one")
    result = result[list(OUTPUT_COLUMNS)].sort_values(
        ["occ_code", "month"], kind="mergesort"
    ).reset_index(drop=True)
    expected_rows = len(support) * len(months)
    if len(result) != expected_rows or result[["occ_code", "month"]].duplicated().any():
        raise CellBuildError("balanced output grid is incomplete or duplicated")
    for column in ("family", "beta_quintile", "webb_z"):
        if result.groupby("occ_code", observed=True)[column].nunique(dropna=False).ne(1).any():
            raise CellBuildError(f"{column} is not fixed within occupation")
    return result, {
        "status": "PASS_WEIGHT_ONCE",
        "weight_application_count": 1,
        "survey_weight_field": "WTFINL",
        "route_weight_is_allocation_not_second_survey_weight": True,
        "output_applies_no_additional_weight": True,
        "independent_aggregation_max_absolute_gap": max_gap,
        "rows": expected_rows,
        "young_stock": float(young.sum()),
        "older_stock": float(older.sum()),
    }


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
        raise CellBuildError("receipt secret-sanitization check failed")
    if any(pattern.search(serialized) for pattern in PRIVATE_PATH_PATTERNS):
        raise CellBuildError("receipt private-path sanitization check failed")


def fsync_file(path: Path) -> None:
    with path.open("rb") as stream:
        os.fsync(stream.fileno())


def reserve_staging_leaf(output_leaf: Path, repo: Path) -> Path:
    repo = repo.resolve()
    if os.path.lexists(output_leaf):
        raise CellBuildError("refusing a pre-existing output leaf; choose a unique new leaf")
    output_leaf = output_leaf.resolve(strict=False)
    if path_is_within(output_leaf, repo):
        raise CellBuildError("protected aggregate output must be outside the repository")
    if os.path.lexists(output_leaf):
        raise CellBuildError("refusing a pre-existing output leaf; choose a unique new leaf")
    parent = output_leaf.parent
    if not parent.is_dir():
        raise CellBuildError("output-leaf parent must already exist")
    staging = Path(tempfile.mkdtemp(prefix=f".{output_leaf.name}.tmp-", dir=parent))
    return staging


def atomic_publish(
    staging: Path,
    output_leaf: Path,
    expected_filenames: set[str] | None = None,
) -> tuple[str, ...]:
    if os.path.lexists(output_leaf):
        raise CellBuildError("output leaf appeared during construction; refusing overwrite")
    observed_filenames: set[str] = set()
    for directory, dirnames, filenames in os.walk(
        staging, topdown=False, followlinks=False
    ):
        base = Path(directory)
        if base != staging or dirnames:
            raise CellBuildError("staging output must be a flat file set")
        for name in filenames:
            path = base / name
            if path.is_symlink() or not path.is_file():
                raise CellBuildError("staging contains a non-regular output")
            if path.stat().st_nlink != 1:
                raise CellBuildError("staging contains a multiply linked output")
            observed_filenames.add(name)
            fsync_file(path)
        for name in dirnames:
            if (base / name).is_symlink():
                raise CellBuildError("staging contains a symlink directory")
        directory_fd = os.open(base, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    if expected_filenames is not None and observed_filenames != expected_filenames:
        raise CellBuildError("staging output inventory differs from the exact contract")
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
        raise CellBuildError("platform lacks atomic no-replace directory rename")
    if result != 0:
        error = ctypes.get_errno()
        if error in {errno.EEXIST, errno.ENOTEMPTY}:
            raise CellBuildError("output leaf appeared during publication; refusing overwrite")
        raise CellBuildError(f"atomic no-replace publication failed with errno {error}")
    # The rename above is the commit point. A post-commit durability attempt
    # is best effort and cannot be raised as an ambiguous pre-publication error.
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
    derived_output_leaf = args.output_parent / f"gate1_cells_sge_{job}"
    supplied_output_leaf = getattr(args, "output_leaf", derived_output_leaf)
    if supplied_output_leaf.resolve(strict=False) != derived_output_leaf.resolve(strict=False):
        raise CellBuildError("output leaf is not derived from the scheduler job ID")
    args.output_leaf = derived_output_leaf
    execution_binding = build_execution_command_binding(
        args, list(sys.argv[1:]), list(getattr(sys, "orig_argv", [])),
        dict(os.environ),
    )
    execution_runtime = execution_runtime_authentication()
    repo = args.repo_root.resolve()
    if not (repo / ".git").exists():
        # A linked worktree has a .git file, while an ordinary checkout has a directory.
        if not (repo / ".git").is_file():
            raise CellBuildError("repo-root is not a Git worktree")
    output_leaf = args.output_leaf.resolve(strict=False)
    staging = reserve_staging_leaf(output_leaf, repo)
    replacements = {
        str(args.microdata.resolve(strict=False)): "<INPUT:ipums_cps_extract_9_wide>",
        str(args.repair_microdata.resolve(strict=False)):
            "<INPUT:ipums_cps_extract_11_march_basic_repair>",
        str(repo): "<YAX_REPO_ROOT>",
        str(output_leaf): "<YAX_GATE1_CELLS_LEAF>",
        str(staging): "<YAX_GATE1_CELLS_STAGING>",
    }
    try:
        cell_spec, canonical = load_and_validate_specs(repo)
        code_hashes = authenticate_code(repo, cell_spec)
        consumer = validate_consumer_contract(repo, cell_spec, canonical)
        runtime = authenticate_runtime(repo, cell_spec)
        git_state = authenticate_git(repo, cell_spec)
        source_hashes = canonical_source_hashes(canonical)
        pre_execution_authorization = validate_pre_execution_authorization(
            repo, canonical, cell_spec,
            code_hashes["runtime"][str(HERE_REL / "run_gate1_cells.py")],
            git_state, source_hashes,
        )
        # No protected input byte is opened before the complete execution
        # authorization has been authenticated above.
        source_hashes, authenticated_source_hashes = authenticate_sources(
            repo, canonical, args.microdata, args.repair_microdata
        )
        authorization = validate_authorization(repo, authenticated_source_hashes)
        raw_columns = {
            source_id: inspect_required_raw_columns(
                getattr(args, argument), source_id
            )
            for source_id, argument in RAW_SOURCE_ARGUMENTS.items()
        }

        routed_cells, raw_cell_receipt, route_receipt = build_six_field_target_cells(
            args.microdata,
            args.repair_microdata,
            repo / REPO_SOURCE_PATHS["census_occ2010_to_2018_bridge"],
        )
        if not np.isfinite(routed_cells.stock.to_numpy(float)).all():
            raise CellBuildError("six-field routed cells contain nonfinite stock")
        if (routed_cells.stock < 0).any():
            raise CellBuildError("six-field routed cells contain negative stock")

        beta_map, webb_map, names, family_map = load_measure_maps(
            repo / REPO_SOURCE_PATHS["cps_occupation_exposure_lookup"],
            repo / REPO_SOURCE_PATHS["computerization_measures_census2018"],
        )
        rebuilt = build_recomputed_contract(
            routed_cells,
            beta_map,
            webb_map,
            names,
        )
        fixed = load_fixed_assignments(repo, canonical, family_map)
        contract_checks = validate_rebuilt_contract(rebuilt, fixed, canonical, cell_spec)
        fingerprint = assignment_fingerprint(fixed)
        expected_fingerprint = cell_spec["assignment_contract"]["fingerprint_sha256"]
        if fingerprint != expected_fingerprint:
            raise CellBuildError("per-occupation assignment fingerprint changed")

        months, calendar_checks = validate_calendar(routed_cells, canonical)
        aggregate, weight_checks = build_balanced_output(routed_cells, fixed, months)
        expected_rows = int(cell_spec["grid_contract"]["expected_rows"])
        if len(aggregate) != expected_rows:
            raise CellBuildError("aggregate row count differs from the pre-result grid contract")

        cells_path = staging / CELLS_FILENAME
        aggregate.to_csv(
            cells_path,
            index=False,
            columns=list(OUTPUT_COLUMNS),
            lineterminator="\n",
            float_format="%.17g",
        )
        assignment_document = {
            "schema_version": "yax-assignment-fingerprint-v1",
            "algorithm": (
                "SHA-256 of occ_code, family, integer beta_quintile, and "
                "float.hex(webb_z), tab-delimited and sorted by occ_code, with one LF per row"
            ),
            "columns": ["occ_code", "family", "beta_quintile", "webb_z"],
            "record_count": len(fixed),
            "sha256": fingerprint,
        }
        write_json(staging / ASSIGNMENT_FILENAME, assignment_document)
        receipt = {
            "schema_version": RECEIPT_SCHEMA,
            "status": "PASS_FRESH_AGGREGATE_REBUILD",
            "aggregate_schema_version": CELL_SCHEMA,
            "canonical_spec_id": canonical["spec_id"],
            "canonical_spec_sha256": sha256_file(repo / CANONICAL_SPEC_REL),
            "analysis_spec_id": consumer["analysis_spec_id"],
            "analysis_spec_sha256": consumer["analysis_spec_sha256"],
            "cell_build_spec_id": cell_spec["cell_build_spec_id"],
            "cell_build_spec_sha256": sha256_file(repo / CELL_SPEC_REL),
            "generated_at_utc": utc_now(),
            "cells_filename": CELLS_FILENAME,
            "cells_sha256": sha256_file(cells_path),
            "source_hashes": source_hashes,
            "authenticated_source_hashes": authenticated_source_hashes,
            "unread_canonical_source_ids": ["historical_preperiod_cells"],
            "runtime_code_hashes": code_hashes["runtime"],
            "historical_reference_code_hashes": code_hashes["historical_reference"],
            "builder_code_sha256": code_hashes["runtime"][
                str(HERE_REL / "run_gate1_cells.py")
            ],
            "builder_transitive_code_sha256": transitive_code_fingerprint(
                code_hashes["runtime"]
            ),
            "builder_transitive_code_sha256_algorithm": (
                "SHA-256 of canonical JSON runtime path-to-hash map excluding the builder; "
                "the empty map proves that historical reference code is not imported at runtime"
            ),
            "command_template": COMMAND_TEMPLATE,
            "execution_command_binding": execution_binding,
            "execution_runtime_authentication": execution_runtime,
            "pre_execution_authorization": pre_execution_authorization,
            "runtime_environment_lock_sha256": runtime["environment_lock_sha256"],
            "runtime_environment_lock_path": runtime["environment_lock_path"],
            "runtime_contract_sha256": runtime["runtime_contract_sha256"],
            "runtime_payload_sha256": runtime["runtime_payload_sha256"],
            "runtime_authentication": runtime,
            **git_state,
            "lookup_and_bridge_hashes": {
                source_id: source_hashes[source_id]
                for source_id in (
                    "cps_occupation_exposure_lookup",
                    "computerization_measures_census2018",
                    "rule_b_values_census2018",
                    "census_occ2010_to_2018_bridge",
                    "first_post_outcome_access_receipt",
                )
            },
            "reference_artifacts": {
                "fixed_membership_sha256": sha256_file(repo / MEMBERSHIP_REL)
            },
            "fixed_membership_sha256": sha256_file(repo / MEMBERSHIP_REL),
            "authorization": authorization,
            "raw_column_contract": {
                "runtime_fields": list(REQUIRED_RAW_COLUMNS),
                "required_columns_present": True,
                "source_column_counts": {
                    source_id: len(columns) for source_id, columns in raw_columns.items()
                },
                "canonical_v2_variable_universe_parity": True,
                "rejected_inherited_helper_fields": ["OCC2010", "IND1990"],
            },
            "six_field_cell_build_checks": raw_cell_receipt,
            "route_checks": route_receipt,
            "calendar_checks": calendar_checks,
            "support_checks": {
                **contract_checks,
                "occupation_count": len(fixed),
                "content_support_sha256": support_hash(fixed.occ_code),
            },
            "assignment_fingerprint": assignment_document,
            "assignment_fingerprint_sha256": fingerprint,
            "assignment_fingerprint_artifact_sha256": sha256_file(
                staging / ASSIGNMENT_FILENAME
            ),
            "weight_application_count": 1,
            "weight_once_checks": weight_checks,
            "balanced_grid_complete": True,
            "occupation_count": len(fixed),
            "observed_month_count": len(months),
            "cells_row_count": len(aggregate),
            "support_hash_sha256": support_hash(fixed.occ_code),
            "contains_resolved_private_paths": False,
            "grid": {
                "occupation_count": len(fixed),
                "observed_month_count": len(months),
                "row_count": len(aggregate),
            },
            "freshness_and_security": {
                "new_output_leaf_required": True,
                "output_outside_repository": True,
                "atomic_directory_publish": True,
                "row_level_microdata_written": False,
                "historical_preperiod_cells_read": False,
                "historical_reference_code_imported_at_runtime": False,
                "only_six_canonical_raw_fields_read": True,
                "private_paths_persisted": False,
                "credentials_persisted": False,
            },
        }
        assert_sanitized(receipt)
        write_json(staging / RECEIPT_FILENAME, receipt)
        # Re-open and re-authenticate every authorization-bound input at the
        # publication boundary. Reusing start-of-run objects would not detect
        # a concurrent source, code, specification, or HEAD change.
        final_cell_spec, final_canonical = load_and_validate_specs(repo)
        final_code_hashes = authenticate_code(repo, final_cell_spec)
        final_consumer = validate_consumer_contract(
            repo, final_cell_spec, final_canonical
        )
        final_git_state = authenticate_git(repo, final_cell_spec)
        final_source_registry = canonical_source_hashes(final_canonical)
        boundary_pre_execution_authorization = validate_pre_execution_authorization(
            repo, final_canonical, final_cell_spec,
            final_code_hashes["runtime"][str(HERE_REL / "run_gate1_cells.py")],
            final_git_state, final_source_registry,
        )
        if boundary_pre_execution_authorization != pre_execution_authorization:
            raise CellBuildError(
                "pre-execution authorization changed before final source authentication"
            )
        final_source_hashes, final_authenticated_source_hashes = authenticate_sources(
            repo, final_canonical, args.microdata, args.repair_microdata
        )
        final_pre_execution_authorization = validate_pre_execution_authorization(
            repo, final_canonical, final_cell_spec,
            final_code_hashes["runtime"][str(HERE_REL / "run_gate1_cells.py")],
            final_git_state, final_source_hashes,
        )
        if (
            final_pre_execution_authorization != pre_execution_authorization
            or final_cell_spec != cell_spec
            or final_canonical != canonical
            or final_code_hashes != code_hashes
            or final_consumer != consumer
            or final_git_state != git_state
            or final_source_hashes != source_hashes
            or final_authenticated_source_hashes != authenticated_source_hashes
        ):
            raise CellBuildError(
                "authorization-bound execution state changed during cell construction"
            )
        post_commit_warnings = atomic_publish(
            staging,
            output_leaf,
            {CELLS_FILENAME, RECEIPT_FILENAME, ASSIGNMENT_FILENAME},
        )
        return {
            "status": receipt["status"],
            "schema_version": receipt["aggregate_schema_version"],
            "rows": len(aggregate),
            "occupations": len(fixed),
            "months": len(months),
            "cells_sha256": receipt["cells_sha256"],
            "assignment_fingerprint_sha256": fingerprint,
            "output_leaf": "<YAX_GATE1_CELLS_LEAF>",
            "post_commit_cleanup_warnings": list(post_commit_warnings),
        }
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def parser() -> argparse.ArgumentParser:
    value = NonEchoingArgumentParser(description=__doc__, allow_abbrev=False)
    value.add_argument("--repo-root", type=Path, required=True)
    value.add_argument("--microdata", type=Path, required=True)
    value.add_argument("--repair-microdata", type=Path, required=True)
    value.add_argument("--output-parent", type=Path, required=True)
    return value


def main(argv: list[str] | None = None) -> int:
    replacements: dict[str, str] = {}
    try:
        if argv is not None:
            raise CellBuildError(
                "production entry point does not accept a substituted argv source"
            )
        raw_cli_argv = list(sys.argv[1:])
        args = parser().parse_args(raw_cli_argv)
        job = scheduler_jobnumber(dict(os.environ))
        args.output_leaf = args.output_parent / f"gate1_cells_sge_{job}"
        replacements = {
            str(args.microdata.resolve(strict=False)):
                "<INPUT:ipums_cps_extract_9_wide>",
            str(args.repair_microdata.resolve(strict=False)):
                "<INPUT:ipums_cps_extract_11_march_basic_repair>",
            str(args.repo_root.resolve(strict=False)): "<YAX_REPO_ROOT>",
            str(args.output_parent.resolve(strict=False)): "<YAX_V3_RUN_ROOT>",
            str(args.output_leaf.resolve(strict=False)): "<YAX_GATE1_CELLS_LEAF>",
        }
        result = execute(args)
    except Exception as exc:
        message = sanitize_text(str(exc), replacements)
        print(json.dumps({"status": "BLOCKED", "error": message}, sort_keys=True), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
