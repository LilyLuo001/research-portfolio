#!/usr/bin/env python3
"""Fail-closed normalization of sanitized Gate-1 execution receipts.

Only schema-specific public projections and normalized delivery receipts are
published.  Source receipts are never copied to the public leaf, and this
program never opens an aggregate cell table or row-level input.

An arbitrary command written into a terminal transfer configuration is not
runner evidence.  Each source receipt must carry a receipt-native,
runner-recorded, hash-consistent ``execution_command_binding`` whose argv is
an exact immutable module grammar.  Only a fresh, authorized producer run can
emit that evidence; legacy receipts remain ineligible.
"""
from __future__ import annotations

import argparse
import ctypes
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
from typing import Any, Iterable
import unicodedata
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


SPEC_SCHEMA = "yax-gate1-transfer-normalization-spec-v2"
SPEC_STATUS = "TERMINAL_TRANSFER_CONFIG"
COMMAND_POLICY = "receipt_native_exact_sanitized_argv_binding_v2"
COMMAND_BINDING_SCHEMA = "yax-execution-command-binding-v2"
COMMAND_BINDING_STATUS = "RUNNER_RECORDED_HASH_CONSISTENT"
PRE_EXECUTION_AUTHORIZATION_SCHEMA = "yax-gate1-pre-execution-authorization-v1"
PRE_EXECUTION_AUTHORIZATION_STATUS = "AUTHORIZED_FRESH_GATE1_EXECUTION"
REPORT_SCHEMA = "yax-gate1-public-transfer-validation-v3"
PROJECTION_SCHEMA = "yax-gate1-public-receipt-projection-v2"
NORMALIZED_SCHEMA = "yax-normalized-run-receipt-v1"
PASS_STATUS = "PASS_SANITIZED_GATE1_RECEIPT_NORMALIZATION"
MODULE_KEYS = ("cells", "target", "numerical")
SCHEDULER_BOUNDARY_TOLERANCE_SECONDS = 2.0
MAX_FUTURE_CLOCK_SKEW_SECONDS = 300.0
KERNEL_NOREPLACE_METHOD = "atomic_kernel_noreplace"
LOCKED_RENAME_METHOD = "exclusive_lock_same_parent_ordinary_rename"
EXPECTED_PYTHON_RESOLVED_SHA256 = (
    "0887a2530329cef5a3a6b7c83c76590da9730f98f1e68497096bc05f20b92aa7"
)
EXPECTED_GIT_PATH = Path("/usr/bin/git")
EXPECTED_GIT_SHA256 = (
    "507917bbb5d24123c8e11df46df1d32483da1ce6420aa7ba7dd17de8ccd13a9e"
)
EXPECTED_GIT_VERSION = "git version 2.43.7"
EXPECTED_QACCT_SHA256 = (
    "aa8575f51ad1f07673ef862d6dfbe06381ebc53bdb88bb3a0256573ededc37e0"
)
EXPECTED_QACCT_VERSION = "OGS/GE 2011.11p1"
AUTHORIZATION_REL = Path(
    "yax/revision/substantive_v3_20260906/gate1_transfer/"
    "PRE_EXECUTION_AUTHORIZATION.json"
)
CANONICAL_SPEC_REL = Path(
    "yax/revision/substantive_v3_20260906/contracts/specs/"
    "canonical_baseline_reproduction_v2.json"
)
QACCT_EXPORTER_SHA256 = (
    "b7c2ed004001afd8c1db9e628db7b266d3be11d88663ea4442d3a9901ef7d00f"
)
SANITIZED_GIT_ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
IMPORT_AFFECTING_ENVIRONMENT = (
    "PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE", "PYTHONSTARTUP",
)

CANONICAL_BINDING = {
    "id": "yaxspec_v1_83bb387f9fc28e2655db5101c7697989510475027d1dd5a9c361c797ed3925c3",
    "sha256": "34b8a785a267d334643b04d3ff35f47bf30780068e126e0a63dd14b0079c5e8b",
}
CELL_SPEC_ID = "yaxcellspec_v1_e08b69694a4ebb0b15919b6af989cca98cea9e86eea80ef252f93b5cfccaa08b"
CELL_SPEC_SHA256 = "09f49d3f459fd532dd37f76dfd111fc0c0a7aa10e1fffe869b08596cad665a15"
CELL_CODE_PATH = (
    "yax/revision/substantive_v3_20260906/gate1_cells/run_gate1_cells.py"
)
CELL_CODE_SHA256 = "70b9bf3d756536a9d5bf38938235b84a83d9d1a8defcc3dbecb5c19b6916bc34"
CELL_TRANSITIVE_SHA256 = "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
TARGET_SPEC_ID = "yaxtargetspec_v1_e0598066c90d6b7efad743ea68e074b5be2b455fb12eddf4b998430c0081b83b"
TARGET_SPEC_SHA256 = "fa425dce6d75475b6f562aba52898b8e71c7db0269d549f17ef9645720052651"
TARGET_CODE_PATH = (
    "yax/revision/substantive_v3_20260906/gate1_target/"
    "run_exact_target_audit.py"
)
TARGET_CODE_SHA256 = "b62cfd28c71d7c7a933158ba4afefec0fa314be4b1f6bd4d205a0991088e80b9"
NUMERICAL_SPEC_ID = "yaxnumspec_v1_4c784c23726ad5ce258af6151afdf83e1e05efe6d1086d43007e5d06a5843991"
NUMERICAL_SPEC_SHA256 = "152cb4b5a27ff168a0bcfae898ac68b479fb2ae4ae2c811722a145560fc6b2ce"
NUMERICAL_CODE_PATH = (
    "yax/revision/substantive_v3_20260906/numerical_existence/"
    "run_numerical_existence_audit.py"
)
NUMERICAL_CODE_SHA256 = "23f4a4dd70fb1ff5798405248fb742a07e4204a0a42bff9d9e24ad816f47df02"
ARTIFACT_SAFETY_SHA256 = "6c03ad94fb5d4ecb618e3cd0e4f9de6ece0a5f20e633283002f3fc01d1248fd2"
LEGACY_ENGINE_SHA256 = "096f0290b057e565077278ef38b352a9af5551c3b525438015bf9f192087bddf"

TARGET_CODE_HASHES = {
    "dax/memo/power_calcs/young_relative_employment_power.py": LEGACY_ENGINE_SHA256,
    "yax/analysis/run_frozen_v11.py": "e40fdda2353dd0c0d6f92401e7bdfb5874c8a32ffa9d641b38144cc07054ddff",
    "yax/revision/referee_20260905/run_referee_cells.py": "a82b1331153645d438509a71e43080e568838ebdb9cdc509fd98cec257e1d4b0",
    "yax/revision/referee_20260905/run_referee_core.py": "1f084084ba67425f398c6bfa5237d74621bad3c1ba63ffd2df7f0d0954563ade",
    "yax/revision/substantive_r3_20260905/rebuilt_baseline/run_rebuilt_corrected_baseline.py": "4c38abcd43d177819d683a0f8774d9e50e02179bde13f9eaae418c6a1aec1704",
    CELL_CODE_PATH: CELL_CODE_SHA256,
    TARGET_CODE_PATH: TARGET_CODE_SHA256,
}
NUMERICAL_SUBMITTED_CODE_HASHES = {
    "yax/revision/substantive_r3_20260905/dynamics/run_dynamics.py": "df2f54712dd763d2fd747c73ef68f164038e3db0a3a4771846d4bc2b325e8bd2",
    "yax/revision/substantive_r3_20260905/rebuilt_baseline/run_rebuilt_corrected_baseline.py": "4c38abcd43d177819d683a0f8774d9e50e02179bde13f9eaae418c6a1aec1704",
    "yax/revision/substantive_r3_20260905/within_family/run_within_family.py": "b16916bb3484926f15fd195fee2e5bffe8601f695427f52d08440a8c0b201a71",
}

TARGET_ARTIFACTS = {
    "EXACT_TARGET_AUDIT.json",
    "ROW_ACCOUNTING.csv",
    "EXACT_TARGET_AUDIT_REPORT.md",
}
NUMERICAL_ARTIFACTS = {
    "MODEL_AUDIT.json",
    "MODEL_DIAGNOSTICS.csv",
    "FAMILY_MONTH_BOUNDARY_CELLS.csv",
    "BOUNDARY_PROFILING.csv",
    "SOLVER_COMPARISON.csv",
    "TARGET_PROFILE.csv",
    "OPTIMIZER_TRAJECTORIES.json",
    "CONVERGENCE_EXISTENCE_REPORT.md",
}

SHA256 = re.compile(r"^[0-9a-f]{64}$")
CANONICAL_ID = re.compile(r"^yaxspec_v1_[0-9a-f]{64}$")
TYPED_ID = re.compile(r"^yax(?:cell|target|num)spec_v1_[0-9a-f]{64}$")
RUN_ID = re.compile(r"^gate1_(cells|target|numerical)_sge_([1-9][0-9]{0,19})$")
JOB_ID = re.compile(r"^[1-9][0-9]{0,19}$")
SAFE_HOST_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MAXVMEM = re.compile(r"^(?:0|[0-9]+(?:\.[0-9]+)?[KMGTP]?)$")
REQUIRED_PLACEHOLDER = re.compile(r"<REQUIRED_[A-Z0-9_:-]+>")
FORBIDDEN_NAMES = {"aggregate_cells.csv"}

PRIVATE_PATH = re.compile(
    r"(?i)(?:^|[\s\"'=:(])(?:/(?:projectnb|project|usr3|users|home)/|[A-Z]:[\\/]users[\\/]|~/\.?(?:ssh|aws)(?:/|$))"
)
TOKEN_MARKER = re.compile(r"(?i)(?:ghp_|github_pat_|glpat-|sk-[A-Za-z0-9])")
NAMED_SECRET = re.compile(
    r"(?i)(?:password|passwd|api[_ -]?key|access[_ -]?token|auth[_ -]?token|client[_ -]?secret|secret)"
    r"[\"']?\s*(?:=|:)\s*[\"']?[^,;\s\"']+"
)
SECRET_FLAG = re.compile(
    r"(?i)(?:--?(?:password|passwd|api[-_]?key|access[-_]?token|token|secret)|"
    r"sshpass\s+-p|curl\b[^\n]*\s-u)\s*(?:=\s*)?[^\s]+"
)
AUTH_HEADER = re.compile(r"(?i)\b(?:authorization\s*:\s*)?(?:bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
CREDENTIAL_URL = re.compile(r"(?i)https?://[^/@:\s]+:[^/@\s]+@")
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
KNOWN_SECRET_NAME = re.compile(r"(?i)\b(?:IPUMS_API_KEY|BEA_API_KEY)\b")
SECRET_KEY_NAME = re.compile(
    r"(?i)^(?:api[_ -]?key|password|passwd|access[_ -]?token|auth[_ -]?token|"
    r"client[_ -]?secret|secret|token)$"
)
SECRET_KEY_COMPONENT = re.compile(
    r"(?:^|_)(?:api_key|password|passwd|token|secret|private_key|access_key_id)(?:$|_)"
)

SCHEDULER_FIELDS = {
    "jobnumber", "qname", "hostname", "start_time", "end_time", "failed",
    "exit_status", "ru_wallclock", "maxvmem", "qacct_export_provenance",
}
QACCT_EXPORT_PROVENANCE_FIELDS = {
    "status", "role", "qacct_resolved_executable_sha256", "qacct_version",
    "exporter_code_sha256", "join_rule",
}
COMMAND_BINDING_FIELDS = {
    "schema_version", "status", "module_key", "run_id",
    "scheduler_jobnumber", "sanitized_argv", "sanitized_argv_sha256",
    "binding_sha256",
}
PRE_EXECUTION_AUTHORIZATION_FIELDS = {
    "schema_version", "status", "authorization_id",
    "authorization_file_sha256", "authorization_git_commit",
    "authorized_implementation_commit", "issued_at_utc", "not_before_utc",
    "not_after_utc", "module_key", "typed_spec_id", "typed_spec_sha256",
    "code_sha256", "source_registry_sha256",
}

EXPECTED_SANITIZED_ARGV: dict[str, list[str]] = {
    "cells": [
        "<YAX_PYTHON_BIN>", "-I",
        "yax/revision/substantive_v3_20260906/gate1_cells/run_gate1_cells.py",
        "--repo-root", "<YAX_REPO_ROOT>",
        "--microdata", "<INPUT:ipums_cps_extract_9_wide>",
        "--repair-microdata", "<INPUT:ipums_cps_extract_11_march_basic_repair>",
        "--output-parent", "<YAX_V3_RUN_ROOT>",
    ],
    "target": [
        "<YAX_PYTHON_BIN>", "-I",
        "yax/revision/substantive_v3_20260906/gate1_target/run_exact_target_audit.py",
        "--repo-root", "<YAX_REPO_ROOT>",
        "--cells", "<YAX_GATE1_CELLS_LEAF>/aggregate_cells.csv",
        "--cells-receipt", "<YAX_GATE1_CELLS_LEAF>/EXECUTION_RECEIPT.json",
        "--output-parent", "<YAX_V3_RUN_ROOT>",
    ],
    "numerical": [
        "<YAX_PYTHON_BIN>", "-I",
        "yax/revision/substantive_v3_20260906/numerical_existence/run_numerical_existence_audit.py",
        "--canonical-spec",
        "<YAX_REPO_ROOT>/yax/revision/substantive_v3_20260906/contracts/specs/canonical_baseline_reproduction_v2.json",
        "--analysis-spec",
        "<YAX_REPO_ROOT>/yax/revision/substantive_v3_20260906/numerical_existence/ANALYSIS_SPEC.json",
        "--cells", "<YAX_GATE1_CELLS_LEAF>/aggregate_cells.csv",
        "--cells-receipt", "<YAX_GATE1_CELLS_LEAF>/EXECUTION_RECEIPT.json",
        "--legacy-engine",
        "<YAX_REPO_ROOT>/dax/memo/power_calcs/young_relative_employment_power.py",
        "--output-parent", "<YAX_V3_RUN_ROOT>",
    ],
}

MODULE_CONTRACTS: dict[str, dict[str, Any]] = {
    "cells": {
        "receipt_file": "cells/EXECUTION_RECEIPT.json",
        "scheduler_file": "scheduler/cells.json",
        "receipt_schema": "yax-numerical-cells-receipt-v1",
        "receipt_status": "PASS_FRESH_AGGREGATE_REBUILD",
        "mode": "empirical_reestimate",
        "depends_on": [],
        "time_source": "scheduler",
        "generated_at_pointer": "/generated_at_utc",
        "scheduler_boundary_tolerance_seconds": SCHEDULER_BOUNDARY_TOLERANCE_SECONDS,
        "typed_spec": {
            "kind": "cell_build_spec", "id": CELL_SPEC_ID,
            "sha256": CELL_SPEC_SHA256, "id_pointer": "/cell_build_spec_id",
            "sha256_pointer": "/cell_build_spec_sha256",
        },
        "code_hash_pointer": "/builder_code_sha256",
        "code_hash": CELL_CODE_SHA256,
    },
    "target": {
        "receipt_file": "target/EXECUTION_RECEIPT.json",
        "scheduler_file": "scheduler/target.json",
        "receipt_schema": "yax-exact-target-audit-receipt-v1",
        "receipt_status": "PASS_EXACT_TARGET_AUDIT",
        "mode": "aggregate_analysis",
        "depends_on": ["cells"],
        "time_source": "scheduler",
        "generated_at_pointer": "/generated_at_utc",
        "scheduler_boundary_tolerance_seconds": SCHEDULER_BOUNDARY_TOLERANCE_SECONDS,
        "typed_spec": {
            "kind": "target_audit_spec", "id": TARGET_SPEC_ID,
            "sha256": TARGET_SPEC_SHA256, "id_pointer": "/target_audit_spec_id",
            "sha256_pointer": "/target_audit_spec_sha256",
        },
        "code_hash_pointer": (
            "/code_hashes/yax~1revision~1substantive_v3_20260906~1"
            "gate1_target~1run_exact_target_audit.py"
        ),
        "code_hash": TARGET_CODE_SHA256,
    },
    "numerical": {
        "receipt_file": "numerical/EXECUTION_RECEIPT.json",
        "scheduler_file": "scheduler/numerical.json",
        "receipt_schema": "yax-numerical-existence-receipt-v1",
        "receipt_status": "PASS_ALL_CORE_TARGETS_NUMERICALLY_AUDITED",
        "mode": "numerical_analysis",
        "depends_on": ["cells", "target"],
        "time_source": "module_receipt",
        "typed_spec": {
            "kind": "numerical_analysis_spec", "id": NUMERICAL_SPEC_ID,
            "sha256": NUMERICAL_SPEC_SHA256, "id_pointer": "/audit_spec_id",
            "sha256_pointer": "/audit_spec_sha256",
        },
        "code_hash_pointer": "/code_sha256",
        "code_hash": NUMERICAL_CODE_SHA256,
        "start_time_pointer": "/started_at_utc",
        "end_time_pointer": "/finished_at_utc",
        "scheduler_boundary_tolerance_seconds": SCHEDULER_BOUNDARY_TOLERANCE_SECONDS,
    },
}


class TransferBlocked(ValueError):
    """A source, binding, safety, or normalization requirement is not met."""


class NonEchoingArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise TransferBlocked("normalizer command-line grammar is invalid")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def rendered_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False,
        ) + "\n"
    ).encode("utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise TransferBlocked(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite_constant(value: str) -> None:
    raise TransferBlocked(f"nonfinite JSON numeric is forbidden: {value}")


def load_json_bytes(payload: bytes, label: str) -> dict[str, Any]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise TransferBlocked(f"{label} is not UTF-8 JSON") from exc
    try:
        value = json.loads(
            text, object_pairs_hook=_no_duplicate_object,
            parse_constant=_reject_nonfinite_constant,
        )
    except json.JSONDecodeError as exc:
        raise TransferBlocked(f"{label} is malformed JSON") from exc
    if not isinstance(value, dict):
        raise TransferBlocked(f"{label} JSON root must be an object")
    assert_safe_document(value, label)
    return value


def load_json(path: Path) -> dict[str, Any]:
    snapshot = stable_snapshot(path, Path(path.name))
    return load_json_bytes(snapshot.payload, path.name)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(rendered_json_bytes(value))


def require_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str) or not SHA256.fullmatch(value):
        raise TransferBlocked(f"{label} must be a lowercase SHA-256")
    return value


def require_nonempty_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TransferBlocked(f"{label} must be a nonempty string")
    if REQUIRED_PLACEHOLDER.search(value):
        raise TransferBlocked(f"{label} contains an unresolved required placeholder")
    assert_safe_string(value, label)
    return value


def require_exact_int(value: Any, label: str, minimum: int | None = None) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TransferBlocked(f"{label} must be a JSON integer")
    if minimum is not None and value < minimum:
        raise TransferBlocked(f"{label} must be at least {minimum}")
    return value


def require_finite_number(value: Any, label: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise TransferBlocked(f"{label} must be numeric")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise TransferBlocked(f"{label} must be numeric") from exc
    if not math.isfinite(parsed):
        raise TransferBlocked(f"{label} must be finite")
    if minimum is not None and parsed < minimum:
        raise TransferBlocked(f"{label} must be at least {minimum}")
    return parsed


def json_pointer(document: Any, pointer: str, label: str) -> Any:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        raise TransferBlocked(f"{label} must be a non-root RFC 6901 pointer")
    cursor = document
    for raw in pointer[1:].split("/"):
        if re.search(r"~(?![01])", raw):
            raise TransferBlocked(f"{label} contains an invalid RFC 6901 escape")
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cursor, dict) and token in cursor:
            cursor = cursor[token]
        else:
            raise TransferBlocked(f"{label} does not resolve: {pointer}")
    return cursor


def normalized_security_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(char for char in normalized if unicodedata.category(char) != "Cf")


def assert_safe_string(value: str, label: str) -> None:
    text = normalized_security_text(value)
    patterns = (
        PRIVATE_PATH, TOKEN_MARKER, NAMED_SECRET, SECRET_FLAG, AUTH_HEADER,
        CREDENTIAL_URL, PRIVATE_KEY, KNOWN_SECRET_NAME,
    )
    if any(pattern.search(text) for pattern in patterns):
        raise TransferBlocked(f"{label} contains a decoded private path or credential form")
    if "\x00" in text or any(ord(char) < 32 and char not in "\t\n\r" for char in text):
        raise TransferBlocked(f"{label} contains a forbidden control character")


def assert_safe_document(value: Any, label: str = "JSON") -> None:
    """Recursively inspect decoded JSON keys and values, including escapes."""
    if isinstance(value, str):
        assert_safe_string(value, label)
    elif isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):  # JSON guarantees this; keep fail-closed.
                raise TransferBlocked(f"{label} contains a non-string object key")
            normalized_key = normalized_security_text(key).strip()
            component_key = re.sub(
                r"_+", "_", re.sub(r"[^a-z0-9]+", "_", normalized_key.casefold())
            ).strip("_")
            if (
                SECRET_KEY_NAME.fullmatch(normalized_key)
                or SECRET_KEY_COMPONENT.search(component_key)
            ):
                raise TransferBlocked(
                    f"{label} contains a suspicious decoded credential-shaped key"
                )
            assert_safe_string(key, f"{label} key")
            assert_safe_document(child, f"{label}/{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            assert_safe_document(child, f"{label}/{index}")
    elif isinstance(value, float) and not math.isfinite(value):
        raise TransferBlocked(f"{label} contains a nonfinite number")
    elif value is not None and not isinstance(value, (bool, int, float)):
        raise TransferBlocked(f"{label} contains an unsupported JSON value")


def _safe_relative(value: Any, label: str) -> Path:
    if not isinstance(value, str):
        raise TransferBlocked(f"{label} must be a relative file path")
    require_nonempty_string(value, label)
    relative = Path(value)
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise TransferBlocked(f"{label} must be a contained relative file path")
    if relative.name.casefold() in FORBIDDEN_NAMES:
        raise TransferBlocked(f"{label} names a forbidden aggregate artifact")
    return relative


@dataclass(frozen=True)
class FileSnapshot:
    relative: Path
    path: Path
    payload: bytes
    sha256: str
    identity: tuple[int, int, int, int, int, int]


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        info.st_dev, info.st_ino, info.st_mode, info.st_nlink,
        info.st_size, info.st_mtime_ns,
    )


def stable_snapshot(path: Path, relative: Path) -> FileSnapshot:
    try:
        first = path.lstat()
    except OSError as exc:
        raise TransferBlocked(f"source is missing: {relative}") from exc
    if stat.S_ISLNK(first.st_mode) or not stat.S_ISREG(first.st_mode):
        raise TransferBlocked(f"source must be a regular non-symlink file: {relative}")
    if first.st_nlink != 1:
        raise TransferBlocked(f"source hardlinks are forbidden: {relative}")
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise TransferBlocked(f"could not safely open source: {relative}") from exc
    try:
        opened_before = os.fstat(descriptor)
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        opened_after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        final = path.lstat()
    except OSError as exc:
        raise TransferBlocked(f"source disappeared while read: {relative}") from exc
    identities = {_identity(first), _identity(opened_before), _identity(opened_after), _identity(final)}
    if len(identities) != 1:
        raise TransferBlocked(f"source changed while read: {relative}")
    if any(info.st_nlink != 1 for info in (opened_before, opened_after, final)):
        raise TransferBlocked(f"source hardlinks are forbidden: {relative}")
    payload = b"".join(chunks)
    if len(payload) != final.st_size:
        raise TransferBlocked(f"source size changed while read: {relative}")
    return FileSnapshot(relative, path, payload, sha256_bytes(payload), _identity(final))


def contained_path(root: Path, relative: Path) -> Path:
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise TransferBlocked(f"symlink source is forbidden: {relative}")
    try:
        path = cursor.resolve(strict=True)
    except OSError as exc:
        raise TransferBlocked(f"source is missing: {relative}") from exc
    if root != path and root not in path.parents:
        raise TransferBlocked(f"source escapes the receipt root: {relative}")
    return path


def inventory_receipt_directory(root: Path, allowed: set[Path]) -> dict[Path, Path]:
    """Inventory before opening any file, rejecting aggregate data by name."""
    try:
        root = root.resolve(strict=True)
    except OSError as exc:
        raise TransferBlocked("receipt input root does not exist") from exc
    if not root.is_dir():
        raise TransferBlocked("receipt input root must be a directory")
    observed: set[Path] = set()
    observed_directories: set[Path] = set()
    allowed_directories = {
        parent
        for path in allowed
        for parent in path.parents
        if parent != Path(".")
    }
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in dirnames:
            candidate = base / name
            relative_directory = candidate.relative_to(root)
            if candidate.is_symlink():
                raise TransferBlocked(
                    f"symlink directory is forbidden: {relative_directory}"
                )
            observed_directories.add(relative_directory)
        for name in filenames:
            candidate = base / name
            relative = candidate.relative_to(root)
            if candidate.is_symlink():
                raise TransferBlocked(f"symlink source is forbidden: {relative}")
            if relative.name.casefold() in FORBIDDEN_NAMES:
                raise TransferBlocked(
                    f"forbidden aggregate artifact present; it was not opened: {relative}"
                )
            observed.add(relative)
    if observed != allowed or observed_directories != allowed_directories:
        missing = sorted(str(path) for path in allowed - observed)
        unexpected = sorted(str(path) for path in observed - allowed)
        missing_directories = sorted(
            str(path) for path in allowed_directories - observed_directories
        )
        unexpected_directories = sorted(
            str(path) for path in observed_directories - allowed_directories
        )
        raise TransferBlocked(
            "receipt-only staging inventory differs; "
            f"missing={missing}, unexpected={unexpected}, "
            f"missing_directories={missing_directories}, "
            f"unexpected_directories={unexpected_directories}"
        )
    return {relative: contained_path(root, relative) for relative in allowed}


def snapshot_sources(root: Path, allowed: set[Path]) -> dict[Path, FileSnapshot]:
    paths = inventory_receipt_directory(root, allowed)
    return {
        relative: stable_snapshot(path, relative) for relative, path in paths.items()
    }


def final_source_recheck(
    root: Path, allowed: set[Path], snapshots: dict[Path, FileSnapshot]
) -> None:
    paths = inventory_receipt_directory(root, allowed)
    for relative, original in snapshots.items():
        current = stable_snapshot(paths[relative], relative)
        if (
            current.identity != original.identity
            or current.sha256 != original.sha256
            or current.payload != original.payload
        ):
            raise TransferBlocked(f"source changed before publication: {relative}")


def _git_output(arguments: list[str], cwd: Path, *, binary: bool = False) -> bytes | str:
    try:
        result = subprocess.run(
            [str(EXPECTED_GIT_PATH), "-C", str(cwd), *arguments],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=not binary,
            env=SANITIZED_GIT_ENVIRONMENT,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise TransferBlocked("normalizer Git provenance could not be verified") from exc
    if result.stderr not in {"", b""}:
        raise TransferBlocked("normalizer Git provenance emitted unexpected stderr")
    return result.stdout


def verify_normalizer_toolchain() -> dict[str, Any]:
    """Fail unless normalization uses approved isolated Python and pinned Git."""
    if (
        sys.flags.isolated != 1
        or sys.flags.ignore_environment != 1
        or sys.flags.no_user_site != 1
        or not bool(getattr(sys.flags, "safe_path", False))
    ):
        raise TransferBlocked("normalizer Python must be invoked with isolated mode")
    if any(os.environ.get(name) for name in IMPORT_AFFECTING_ENVIRONMENT):
        raise TransferBlocked("import-affecting Python environment variables are forbidden")
    try:
        python_path = Path(sys.executable).resolve(strict=True)
    except OSError as exc:
        raise TransferBlocked("normalizer Python executable cannot be resolved") from exc
    python_hash = sha256_bytes(python_path.read_bytes())
    if python_hash != EXPECTED_PYTHON_RESOLVED_SHA256:
        raise TransferBlocked("normalizer Python executable differs from the pinned runtime")
    if sys.version_info[:3] != (3, 13, 8):
        raise TransferBlocked("normalizer Python version differs from the pinned runtime")
    if not EXPECTED_GIT_PATH.is_file() or EXPECTED_GIT_PATH.is_symlink():
        raise TransferBlocked("pinned Git executable is absent or indirect")
    git_hash = sha256_bytes(EXPECTED_GIT_PATH.read_bytes())
    if git_hash != EXPECTED_GIT_SHA256:
        raise TransferBlocked("normalizer Git executable differs from the pinned runtime")
    completed = subprocess.run(
        [str(EXPECTED_GIT_PATH), "--version"],
        env=SANITIZED_GIT_ENVIRONMENT,
        text=True, capture_output=True, check=False,
    )
    if (
        completed.returncode != 0
        or completed.stderr != ""
        or completed.stdout.strip() != EXPECTED_GIT_VERSION
    ):
        raise TransferBlocked("normalizer Git version differs from the pinned runtime")
    return {
        "python_invocation": "<YAX_PYTHON_BIN>",
        "python_resolved_executable_sha256": python_hash,
        "python_version": "3.13.8",
        "isolated_mode": True,
        "ignore_environment": True,
        "no_user_site": True,
        "safe_path": True,
        "import_affecting_environment_absent": True,
        "git_invocation": "<YAX_GIT_BIN>",
        "git_resolved_executable_sha256": git_hash,
        "git_version": EXPECTED_GIT_VERSION,
        "sanitized_environment": SANITIZED_GIT_ENVIRONMENT,
    }


def capture_normalizer_state(source_path: Path | None = None) -> dict[str, Any]:
    """Verify this exact source is committed and the repository is clean.

    The expected source digest is deliberately not embedded in this source
    file.  Instead, the working-tree bytes must equal the bytes stored at HEAD,
    and the observed SHA-256 is reported with the immutable Git identities.
    """
    source = (source_path or Path(__file__)).resolve(strict=True)
    root_text = _git_output(["rev-parse", "--show-toplevel"], source.parent)
    assert isinstance(root_text, str)
    root = Path(root_text.strip()).resolve(strict=True)
    try:
        relative = source.relative_to(root)
    except ValueError as exc:
        raise TransferBlocked("normalizer source is outside its Git worktree") from exc
    relative_text = relative.as_posix()
    _git_output(["ls-files", "--error-unmatch", "--", relative_text], root)
    status = _git_output(["status", "--porcelain=v1", "--untracked-files=all"], root)
    assert isinstance(status, str)
    if status:
        raise TransferBlocked(
            "normalizer Git worktree is dirty or contains untracked files"
        )
    commit = _git_output(["rev-parse", "--verify", "HEAD^{commit}"], root)
    tree = _git_output(["rev-parse", "--verify", "HEAD^{tree}"], root)
    committed = _git_output(["show", f"HEAD:{relative_text}"], root, binary=True)
    ignored = _git_output(
        ["ls-files", "-z", "--others", "--ignored", "--exclude-standard"],
        root, binary=True,
    )
    tracked = _git_output(["ls-files", "-z"], root, binary=True)
    assert isinstance(commit, str) and isinstance(tree, str)
    assert isinstance(committed, bytes)
    assert isinstance(ignored, bytes) and isinstance(tracked, bytes)
    try:
        ignored_paths = [
            Path(row.decode("utf-8")) for row in ignored.split(b"\0") if row
        ]
    except UnicodeDecodeError as exc:
        raise TransferBlocked("ignored-path inventory is not UTF-8") from exc
    executable_suffixes = {".py", ".pyc", ".pyo", ".pth", ".so", ".dylib"}
    executable_names = {"sitecustomize.py", "usercustomize.py"}
    v3_scope = Path("yax/revision/substantive_v3_20260906")
    forbidden_ignored = [
        path for path in ignored_paths
        if v3_scope in path.parents
        and (path.suffix.casefold() in executable_suffixes or path.name.casefold() in executable_names)
    ]
    if forbidden_ignored:
        raise TransferBlocked(
            "ignored importable or executable artifacts exist in the V3 code scope"
        )
    snapshot = stable_snapshot(source, relative)
    if snapshot.payload != committed:
        raise TransferBlocked("normalizer source bytes differ from committed HEAD bytes")
    state = {
        "source_path": relative_text,
        "source_sha256": snapshot.sha256,
        "committed_source_sha256": sha256_bytes(committed),
        "git_commit": commit.strip(),
        "git_tree": tree.strip(),
        "tracked_at_head": True,
        "tracked_worktree_clean": True,
        "untracked_nonignored_files_absent": True,
        "ignored_path_inventory_count": len([row for row in ignored.split(b"\0") if row]),
        "ignored_path_inventory_sha256": sha256_bytes(ignored),
        "ignored_importable_or_executable_paths_in_v3_scope": 0,
        "tracked_path_inventory_count": len([row for row in tracked.split(b"\0") if row]),
        "tracked_path_inventory_sha256": sha256_bytes(tracked),
    }
    assert_safe_document(state, "normalizer Git provenance")
    return state


@dataclass(frozen=True)
class AuthorizationState:
    public: dict[str, Any]
    snapshot: FileSnapshot
    committed_payload_sha256: str


def _authorization_identifier(document: dict[str, Any]) -> str:
    core = dict(document)
    core.pop("authorization_id", None)
    return "yaxgate1auth_v1_" + sha256_bytes(canonical_bytes(core))


def capture_committed_authorization_state(
    normalizer_state: dict[str, Any],
) -> AuthorizationState:
    """Authenticate the authorization document at the current clean HEAD.

    Receipt-carried summaries are not authority.  This function independently
    opens the committed authorization and canonical source registry, enforces
    the two-commit authorization sequence, and returns the exact public values
    against which all three producer receipts must agree.
    """
    source = Path(__file__).resolve(strict=True)
    root_text = _git_output(["rev-parse", "--show-toplevel"], source.parent)
    assert isinstance(root_text, str)
    root = Path(root_text.strip()).resolve(strict=True)
    if normalizer_state.get("git_commit") != _git_output(
        ["rev-parse", "--verify", "HEAD^{commit}"], root
    ).strip():
        raise TransferBlocked("authorization HEAD differs from normalizer HEAD")
    auth_path = contained_path(root, AUTHORIZATION_REL)
    auth_snapshot = stable_snapshot(auth_path, AUTHORIZATION_REL)
    committed = _git_output(
        ["show", f"HEAD:{AUTHORIZATION_REL.as_posix()}"], root, binary=True
    )
    assert isinstance(committed, bytes)
    if auth_snapshot.payload != committed:
        raise TransferBlocked("authorization bytes differ from committed HEAD bytes")
    document = load_json_bytes(auth_snapshot.payload, "committed authorization")
    expected_fields = {
        "schema_version", "status", "authorization_id", "issued_at_utc",
        "not_before_utc", "not_after_utc", "authorized_implementation_commit",
        "canonical_spec", "source_registry_sha256", "modules",
    }
    if set(document) != expected_fields:
        raise TransferBlocked("committed authorization field set is not exact")
    if (
        document.get("schema_version") != PRE_EXECUTION_AUTHORIZATION_SCHEMA
        or document.get("status") != PRE_EXECUTION_AUTHORIZATION_STATUS
        or document.get("authorization_id") != _authorization_identifier(document)
    ):
        raise TransferBlocked("committed authorization identity is invalid")
    issued = parse_module_time(document.get("issued_at_utc"), "authorization issued_at")
    not_before = parse_module_time(
        document.get("not_before_utc"), "authorization not_before"
    )
    not_after = parse_module_time(
        document.get("not_after_utc"), "authorization not_after"
    )
    if not issued <= not_before <= not_after:
        raise TransferBlocked("committed authorization time window is malformed")

    canonical_path = contained_path(root, CANONICAL_SPEC_REL)
    canonical_snapshot = stable_snapshot(canonical_path, CANONICAL_SPEC_REL)
    canonical_committed = _git_output(
        ["show", f"HEAD:{CANONICAL_SPEC_REL.as_posix()}"], root, binary=True
    )
    assert isinstance(canonical_committed, bytes)
    if canonical_snapshot.payload != canonical_committed:
        raise TransferBlocked("canonical specification differs from committed HEAD")
    canonical = load_json_bytes(canonical_snapshot.payload, "canonical specification")
    canonical_core = dict(canonical)
    canonical_id = canonical_core.pop("spec_id", None)
    expected_canonical_id = "yaxspec_v1_" + sha256_bytes(
        canonical_bytes(canonical_core)
    )
    if (
        canonical_id != expected_canonical_id
        or {"id": canonical_id, "sha256": canonical_snapshot.sha256}
        != CANONICAL_BINDING
    ):
        raise TransferBlocked("authorization canonical specification binding differs")
    sources = canonical.get("data", {}).get("sources")
    if not isinstance(sources, list) or not sources:
        raise TransferBlocked("authorization canonical source registry is absent")
    source_hashes: dict[str, str] = {}
    for row in sources:
        if not isinstance(row, dict):
            raise TransferBlocked("authorization source registry row is malformed")
        source_id = row.get("source_id")
        digest = row.get("sha256")
        if (
            not isinstance(source_id, str)
            or not source_id
            or source_id in source_hashes
            or not isinstance(digest, str)
            or not SHA256.fullmatch(digest)
        ):
            raise TransferBlocked("authorization source registry row is malformed")
        source_hashes[source_id] = digest
    source_registry_sha256 = sha256_bytes(canonical_bytes(source_hashes))
    if document.get("source_registry_sha256") != source_registry_sha256:
        raise TransferBlocked("authorization source registry hash differs")

    expected_modules = {
        key: {
            "typed_spec_id": MODULE_CONTRACTS[key]["typed_spec"]["id"],
            "typed_spec_sha256": MODULE_CONTRACTS[key]["typed_spec"]["sha256"],
            "code_sha256": MODULE_CONTRACTS[key]["code_hash"],
        }
        for key in MODULE_KEYS
    }
    if document.get("modules") != expected_modules:
        raise TransferBlocked("authorization module registry differs")
    head = str(normalizer_state["git_commit"])
    implementation = document.get("authorized_implementation_commit")
    if (
        not isinstance(implementation, str)
        or not re.fullmatch(r"[0-9a-f]{40}", implementation)
        or implementation == head
    ):
        raise TransferBlocked("authorization implementation commit is invalid")
    last_commit = _git_output(
        ["log", "-1", "--format=%H", "--", AUTHORIZATION_REL.as_posix()], root
    )
    parent_commit = _git_output(["rev-parse", "HEAD^"], root)
    changed_paths = _git_output(
        ["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"], root
    )
    assert isinstance(last_commit, str) and isinstance(parent_commit, str)
    assert isinstance(changed_paths, str)
    if (
        last_commit.strip() != head
        or parent_commit.strip() != implementation
        or changed_paths.splitlines() != [AUTHORIZATION_REL.as_posix()]
    ):
        raise TransferBlocked(
            "authorization is not the sole file in a separate current commit"
        )
    public = {
        "schema_version": document["schema_version"],
        "status": document["status"],
        "authorization_id": document["authorization_id"],
        "authorization_file_sha256": auth_snapshot.sha256,
        "authorization_git_commit": head,
        "authorized_implementation_commit": implementation,
        "issued_at_utc": iso_utc(issued),
        "not_before_utc": iso_utc(not_before),
        "not_after_utc": iso_utc(not_after),
        "canonical_spec": dict(CANONICAL_BINDING),
        "source_registry_sha256": source_registry_sha256,
        "modules": expected_modules,
    }
    assert_safe_document(public, "committed authorization provenance")
    return AuthorizationState(public, auth_snapshot, sha256_bytes(committed))


def verify_committed_authorization_state_unchanged(
    expected: AuthorizationState,
) -> None:
    source = Path(__file__).resolve(strict=True)
    root_text = _git_output(["rev-parse", "--show-toplevel"], source.parent)
    assert isinstance(root_text, str)
    root = Path(root_text.strip()).resolve(strict=True)
    current_path = contained_path(root, AUTHORIZATION_REL)
    current = stable_snapshot(current_path, AUTHORIZATION_REL)
    committed = _git_output(
        ["show", f"HEAD:{AUTHORIZATION_REL.as_posix()}"], root, binary=True
    )
    assert isinstance(committed, bytes)
    if (
        current.identity != expected.snapshot.identity
        or current.sha256 != expected.snapshot.sha256
        or current.payload != expected.snapshot.payload
        or sha256_bytes(committed) != expected.committed_payload_sha256
        or committed != current.payload
    ):
        raise TransferBlocked("committed authorization changed before publication")


def verify_normalizer_state_unchanged(expected: dict[str, Any]) -> None:
    """Recheck source bytes plus HEAD commit/tree immediately before publish."""
    source = Path(__file__).resolve(strict=True)
    root_text = _git_output(["rev-parse", "--show-toplevel"], source.parent)
    assert isinstance(root_text, str)
    root = Path(root_text.strip()).resolve(strict=True)
    commit = _git_output(["rev-parse", "--verify", "HEAD^{commit}"], root)
    tree = _git_output(["rev-parse", "--verify", "HEAD^{tree}"], root)
    tracked_status = _git_output(
        ["status", "--porcelain=v1", "--untracked-files=all"], root
    )
    ignored = _git_output(
        ["ls-files", "-z", "--others", "--ignored", "--exclude-standard"],
        root, binary=True,
    )
    tracked = _git_output(["ls-files", "-z"], root, binary=True)
    assert isinstance(commit, str) and isinstance(tree, str)
    assert isinstance(tracked_status, str)
    assert isinstance(ignored, bytes) and isinstance(tracked, bytes)
    if tracked_status:
        raise TransferBlocked("normalizer Git tracked state changed before publication")
    snapshot = stable_snapshot(source, Path(expected["source_path"]))
    if (
        commit.strip() != expected["git_commit"]
        or tree.strip() != expected["git_tree"]
        or snapshot.sha256 != expected["source_sha256"]
        or sha256_bytes(ignored) != expected["ignored_path_inventory_sha256"]
        or sha256_bytes(tracked) != expected["tracked_path_inventory_sha256"]
    ):
        raise TransferBlocked("normalizer Git/source state changed before publication")


def strict_localize(naive: datetime, zone_name: str, label: str) -> datetime:
    try:
        zone = ZoneInfo(zone_name)
    except ZoneInfoNotFoundError as exc:
        raise TransferBlocked("scheduler_time_zone is not installed or valid") from exc
    candidates: list[datetime] = []
    for fold in (0, 1):
        candidate = naive.replace(tzinfo=zone, fold=fold)
        back = candidate.astimezone(timezone.utc).astimezone(zone)
        if back.replace(tzinfo=None) == naive and back.fold == fold:
            candidates.append(candidate)
    distinct = {candidate.astimezone(timezone.utc) for candidate in candidates}
    if not distinct:
        raise TransferBlocked(f"{label} is nonexistent in {zone_name} because of DST")
    if len(distinct) > 1:
        raise TransferBlocked(f"{label} is ambiguous in {zone_name} because of DST")
    return candidates[0]


def parse_scheduler_time(value: Any, zone_name: str, label: str) -> datetime:
    text = require_nonempty_string(value, label).strip()
    parsed: datetime | None = None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        pass
    if parsed is None:
        for pattern in ("%a %b %d %H:%M:%S %Y", "%m/%d/%Y %H:%M:%S"):
            try:
                parsed = datetime.strptime(text, pattern)
                break
            except ValueError:
                continue
    if parsed is None:
        raise TransferBlocked(f"{label} has an unsupported timestamp format")
    if parsed.tzinfo is None:
        parsed = strict_localize(parsed, zone_name, label)
    return parsed.astimezone(timezone.utc)


def parse_module_time(value: Any, label: str) -> datetime:
    text = require_nonempty_string(value, label).strip()
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TransferBlocked(f"{label} is not ISO-8601") from exc
    if parsed.tzinfo is None:
        raise TransferBlocked(f"{label} must include a timezone")
    return parsed.astimezone(timezone.utc)


def iso_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def utc_wall_clock() -> datetime:
    return datetime.now(timezone.utc)


def validate_no_future_scheduler_times(
    schedulers: dict[str, dict[str, Any]],
) -> None:
    latest_allowed = utc_wall_clock() + timedelta(
        seconds=MAX_FUTURE_CLOCK_SKEW_SECONDS
    )
    future = [
        key for key, scheduler in schedulers.items()
        if scheduler["_start"] > latest_allowed or scheduler["_end"] > latest_allowed
    ]
    if future:
        raise TransferBlocked(
            "scheduler record is implausibly future-dated: " + ", ".join(future)
        )


def validate_scheduler(
    scheduler: dict[str, Any], module: dict[str, Any], zone_name: str
) -> dict[str, Any]:
    if set(scheduler) != SCHEDULER_FIELDS:
        raise TransferBlocked(
            "sanitized scheduler record must contain exactly: "
            + ", ".join(sorted(SCHEDULER_FIELDS))
        )
    jobnumber = require_nonempty_string(scheduler["jobnumber"], "scheduler jobnumber")
    if not JOB_ID.fullmatch(jobnumber) or jobnumber != module["expected_jobnumber"]:
        raise TransferBlocked("scheduler jobnumber differs from terminal transfer config")
    for field in ("qname", "hostname"):
        value = require_nonempty_string(scheduler[field], f"scheduler {field}")
        if not SAFE_HOST_TOKEN.fullmatch(value):
            raise TransferBlocked(f"scheduler {field} contains an unsafe token")
    start = parse_scheduler_time(scheduler["start_time"], zone_name, "scheduler start_time")
    end = parse_scheduler_time(scheduler["end_time"], zone_name, "scheduler end_time")
    if end < start:
        raise TransferBlocked("scheduler end_time precedes start_time")
    failed = scheduler["failed"]
    exit_status = scheduler["exit_status"]
    if isinstance(failed, str) and failed.isdigit():
        failed = int(failed)
    if isinstance(exit_status, str) and exit_status.isdigit():
        exit_status = int(exit_status)
    require_exact_int(failed, "scheduler failed", 0)
    require_exact_int(exit_status, "scheduler exit_status", 0)
    if failed != 0 or exit_status != 0:
        raise TransferBlocked("scheduler record does not establish a successful run")
    wallclock = require_finite_number(
        scheduler["ru_wallclock"], "scheduler ru_wallclock", 0.0
    )
    maxvmem = require_nonempty_string(scheduler["maxvmem"], "scheduler maxvmem").strip()
    if not MAXVMEM.fullmatch(maxvmem):
        raise TransferBlocked("scheduler maxvmem has an unsupported sanitized form")
    qacct = scheduler["qacct_export_provenance"]
    expected_qacct = {
        "status": "RUNNER_RECORDED_BYTE_PINNED_CONSISTENCY",
        "role": "scheduler_accounting_export",
        "qacct_resolved_executable_sha256": EXPECTED_QACCT_SHA256,
        "qacct_version": EXPECTED_QACCT_VERSION,
        "exporter_code_sha256": QACCT_EXPORTER_SHA256,
        "join_rule": "one_delimiter_one_record_exact_jobnumber_nonarray",
    }
    if (
        not isinstance(qacct, dict)
        or set(qacct) != QACCT_EXPORT_PROVENANCE_FIELDS
        or qacct != expected_qacct
    ):
        raise TransferBlocked("scheduler qacct export provenance differs")
    return {
        "jobnumber": jobnumber,
        "qname": scheduler["qname"],
        "hostname": scheduler["hostname"],
        "start_utc": iso_utc(start),
        "end_utc": iso_utc(end),
        "failed": failed,
        "exit_status": exit_status,
        "ru_wallclock_seconds": wallclock,
        "maxvmem": maxvmem,
        "qacct_export_provenance": dict(qacct),
        "_start": start,
        "_end": end,
    }


def select_times(
    receipt: dict[str, Any], module: dict[str, Any], scheduler: dict[str, Any]
) -> tuple[str, str, str]:
    contract = MODULE_CONTRACTS[module["key"]]
    if contract["time_source"] == "scheduler":
        return scheduler["start_utc"], scheduler["end_utc"], "scheduler_record"
    start = parse_module_time(
        json_pointer(receipt, contract["start_time_pointer"], "module start pointer"),
        "module start time",
    )
    end = parse_module_time(
        json_pointer(receipt, contract["end_time_pointer"], "module end pointer"),
        "module end time",
    )
    if end < start:
        raise TransferBlocked("module end time precedes module start time")
    tolerance = require_finite_number(
        module["scheduler_boundary_tolerance_seconds"],
        "scheduler boundary tolerance", 0.0,
    )
    if start < scheduler["_start"] - timedelta(seconds=tolerance):
        raise TransferBlocked("module start precedes scheduler start")
    if end > scheduler["_end"] + timedelta(seconds=tolerance):
        raise TransferBlocked("module end follows scheduler end")
    return iso_utc(start), iso_utc(end), "module_receipt"


def validate_generated_at_within_scheduler(
    receipt: dict[str, Any], module: dict[str, Any], scheduler: dict[str, Any]
) -> None:
    """Bind cells/target receipt generation to their scheduler intervals."""
    key = module["key"]
    contract = MODULE_CONTRACTS[key]
    if key not in {"cells", "target"}:
        return
    generated = parse_module_time(
        json_pointer(receipt, contract["generated_at_pointer"], f"{key} generated_at"),
        f"{key} generated_at",
    )
    tolerance = require_finite_number(
        module["scheduler_boundary_tolerance_seconds"],
        f"{key} scheduler boundary tolerance", 0.0,
    )
    if generated < scheduler["_start"] - timedelta(seconds=tolerance):
        raise TransferBlocked(f"{key} generated_at precedes scheduler interval")
    if generated > scheduler["_end"] + timedelta(seconds=tolerance):
        raise TransferBlocked(f"{key} generated_at follows scheduler interval")


def validate_dependency_intervals(
    selected_times: dict[str, tuple[str, str, str]]
) -> None:
    intervals = {
        key: (
            parse_module_time(selected_times[key][0], f"{key} normalized start"),
            parse_module_time(selected_times[key][1], f"{key} normalized end"),
        )
        for key in MODULE_KEYS
    }
    if intervals["cells"][1] > intervals["target"][0]:
        raise TransferBlocked("cells execution must end before target execution starts")
    numerical_start = intervals["numerical"][0]
    if intervals["cells"][1] > numerical_start:
        raise TransferBlocked("cells execution must end before numerical execution starts")
    if intervals["target"][1] > numerical_start:
        raise TransferBlocked("target execution must end before numerical execution starts")


def exact_module_fields(key: str) -> set[str]:
    fields = {
        "key", "run_id", "module_receipt_file", "module_receipt_sha256",
        "scheduler_record_file", "scheduler_record_sha256",
        "expected_jobnumber", "expected_receipt_schema",
        "expected_receipt_status", "canonical_id_pointer",
        "canonical_sha256_pointer", "typed_spec", "code_hash_pointer",
        "expected_code_hash", "mode", "time_source", "depends_on",
        "scheduler_boundary_tolerance_seconds",
    }
    if key in {"cells", "target"}:
        fields.add("generated_at_pointer")
    if key == "numerical":
        fields |= {
            "start_time_pointer", "end_time_pointer",
        }
    return fields


def validate_spec(document: dict[str, Any]) -> list[dict[str, Any]]:
    expected_top = {
        "schema_version", "status", "canonical_spec", "scheduler_time_zone",
        "execution_command_policy", "modules",
    }
    if set(document) != expected_top:
        raise TransferBlocked("transfer spec top-level field set is not exact")
    if document.get("schema_version") != SPEC_SCHEMA:
        raise TransferBlocked(f"transfer spec schema must be {SPEC_SCHEMA}")
    if document.get("status") != SPEC_STATUS:
        raise TransferBlocked(
            "transfer configuration is not terminal; unresolved pre-result template blocks"
        )
    if document.get("execution_command_policy") != COMMAND_POLICY:
        raise TransferBlocked(
            "arbitrary command strings are forbidden; receipt-native exact argv is required"
        )
    if document.get("canonical_spec") != CANONICAL_BINDING:
        raise TransferBlocked("canonical specification binding is not the immutable Gate-1 value")
    if not CANONICAL_ID.fullmatch(CANONICAL_BINDING["id"]):
        raise TransferBlocked("internal canonical ID contract is malformed")
    require_sha256(CANONICAL_BINDING["sha256"], "canonical spec hash")
    zone_name = require_nonempty_string(
        document.get("scheduler_time_zone"), "scheduler_time_zone"
    )
    try:
        ZoneInfo(zone_name)
    except ZoneInfoNotFoundError as exc:
        raise TransferBlocked("scheduler_time_zone is not installed or valid") from exc
    modules = document.get("modules")
    if not isinstance(modules, list) or [
        row.get("key") if isinstance(row, dict) else None for row in modules
    ] != list(MODULE_KEYS):
        raise TransferBlocked("module keys and order must be exactly cells, target, numerical")
    run_ids: list[str] = []
    job_ids: list[str] = []
    file_paths: list[str] = []
    for module in modules:
        key = module["key"]
        contract = MODULE_CONTRACTS[key]
        if set(module) != exact_module_fields(key):
            raise TransferBlocked(f"{key} module field set is not exact")
        fixed = {
            "module_receipt_file": contract["receipt_file"],
            "scheduler_record_file": contract["scheduler_file"],
            "expected_receipt_schema": contract["receipt_schema"],
            "expected_receipt_status": contract["receipt_status"],
            "canonical_id_pointer": "/canonical_spec_id",
            "canonical_sha256_pointer": "/canonical_spec_sha256",
            "typed_spec": contract["typed_spec"],
            "code_hash_pointer": contract["code_hash_pointer"],
            "expected_code_hash": contract["code_hash"],
            "mode": contract["mode"],
            "time_source": contract["time_source"],
            "depends_on": contract["depends_on"],
            "scheduler_boundary_tolerance_seconds": contract[
                "scheduler_boundary_tolerance_seconds"
            ],
        }
        if key in {"cells", "target"}:
            fixed["generated_at_pointer"] = contract["generated_at_pointer"]
        if key == "numerical":
            fixed.update({
                "start_time_pointer": contract["start_time_pointer"],
                "end_time_pointer": contract["end_time_pointer"],
            })
        for field, expected in fixed.items():
            if module.get(field) != expected:
                raise TransferBlocked(f"{key} immutable {field} differs")
        run_id = require_nonempty_string(module.get("run_id"), f"{key} run_id")
        match = RUN_ID.fullmatch(run_id)
        if not match or match.group(1) != key:
            raise TransferBlocked(f"{key} run_id has the wrong immutable prefix or syntax")
        job = require_nonempty_string(
            module.get("expected_jobnumber"), f"{key} expected_jobnumber"
        )
        if not JOB_ID.fullmatch(job):
            raise TransferBlocked(f"{key} expected_jobnumber must be a positive digit string")
        if match.group(2) != job:
            raise TransferBlocked(f"{key} run_id is not derived from expected_jobnumber")
        require_sha256(module.get("module_receipt_sha256"), f"{key} receipt hash")
        require_sha256(module.get("scheduler_record_sha256"), f"{key} scheduler hash")
        receipt_file = str(_safe_relative(module["module_receipt_file"], f"{key} receipt"))
        scheduler_file = str(_safe_relative(module["scheduler_record_file"], f"{key} scheduler"))
        run_ids.append(run_id)
        job_ids.append(job)
        file_paths.extend([receipt_file, scheduler_file])
    if len(set(run_ids)) != len(MODULE_KEYS):
        raise TransferBlocked("module run_id values must be unique")
    if len(set(job_ids)) != len(MODULE_KEYS):
        raise TransferBlocked("scheduler jobnumber values must be unique")
    if len(set(file_paths)) != 2 * len(MODULE_KEYS):
        raise TransferBlocked("receipt and scheduler source paths must all be unique")
    return modules


def validate_command_binding(
    receipt: dict[str, Any], module: dict[str, Any]
) -> dict[str, Any]:
    key = module["key"]
    binding = receipt.get("execution_command_binding")
    if not isinstance(binding, dict):
        raise TransferBlocked(
            f"{key} receipt lacks receipt-native execution_command_binding; "
            "a transfer-spec command string is not runner-recorded evidence"
        )
    if set(binding) != COMMAND_BINDING_FIELDS:
        raise TransferBlocked(f"{key} execution command binding field set is not exact")
    expected = {
        "schema_version": COMMAND_BINDING_SCHEMA,
        "status": COMMAND_BINDING_STATUS,
        "module_key": key,
        "run_id": module["run_id"],
        "scheduler_jobnumber": module["expected_jobnumber"],
    }
    for field, value in expected.items():
        if binding.get(field) != value:
            raise TransferBlocked(f"{key} execution command binding differs: {field}")
    argv = binding.get("sanitized_argv")
    if (
        not isinstance(argv, list)
        or any(not isinstance(token, str) or not token for token in argv)
    ):
        raise TransferBlocked(f"{key} sanitized argv must be an array of nonempty strings")
    for index, token in enumerate(argv):
        assert_safe_string(token, f"{key} sanitized argv/{index}")
    if argv != EXPECTED_SANITIZED_ARGV[key]:
        raise TransferBlocked(f"{key} sanitized argv differs from immutable grammar")
    argv_hash = sha256_bytes(canonical_bytes(argv))
    if binding.get("sanitized_argv_sha256") != argv_hash:
        raise TransferBlocked(f"{key} sanitized argv hash differs")
    core = {field: binding[field] for field in sorted(COMMAND_BINDING_FIELDS - {"binding_sha256"})}
    if binding.get("binding_sha256") != sha256_bytes(canonical_bytes(core)):
        raise TransferBlocked(f"{key} execution command binding self-hash differs")
    return dict(binding)


def require_hash_map(value: Any, expected_keys: Iterable[str], label: str) -> dict[str, str]:
    keys = set(expected_keys)
    if not isinstance(value, dict) or set(value) != keys:
        raise TransferBlocked(f"{label} key set is not exact")
    return {key: require_sha256(value[key], f"{label}/{key}") for key in sorted(keys)}


def validate_execution_runtime(
    receipt: dict[str, Any], key: str,
) -> dict[str, Any]:
    runtime = receipt.get("execution_runtime_authentication")
    if not isinstance(runtime, dict):
        raise TransferBlocked(f"{key} execution runtime authentication is absent")
    expected_fields = {
        "status", "python_invocation", "python_resolved_executable_sha256",
        "python_version", "isolated_mode", "ignore_environment",
        "no_user_site", "safe_path", "git_invocation",
        "git_resolved_executable_sha256", "git_version",
        "import_affecting_environment_absent",
    }
    if key == "numerical":
        expected_fields.add("omp_num_threads")
    if set(runtime) != expected_fields:
        raise TransferBlocked(f"{key} execution runtime field set is not exact")
    expected = {
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
    if key == "numerical":
        expected["omp_num_threads"] = "1"
    if runtime != expected:
        raise TransferBlocked(f"{key} execution runtime differs from the pinned contract")
    return dict(runtime)


def validate_pre_execution_authorization_receipt(
    receipt: dict[str, Any], key: str, typed_id: str,
    typed_sha256: str, code_sha256: str,
) -> dict[str, Any]:
    authorization = receipt.get("pre_execution_authorization")
    if not isinstance(authorization, dict):
        raise TransferBlocked(f"{key} pre-execution authorization is absent")
    if set(authorization) != PRE_EXECUTION_AUTHORIZATION_FIELDS:
        raise TransferBlocked(f"{key} pre-execution authorization field set is not exact")
    if (
        authorization.get("schema_version") != PRE_EXECUTION_AUTHORIZATION_SCHEMA
        or authorization.get("status") != PRE_EXECUTION_AUTHORIZATION_STATUS
        or authorization.get("module_key") != key
        or authorization.get("typed_spec_id") != typed_id
        or authorization.get("typed_spec_sha256") != typed_sha256
        or authorization.get("code_sha256") != code_sha256
    ):
        raise TransferBlocked(f"{key} pre-execution authorization binding differs")
    identifier = authorization.get("authorization_id")
    if not isinstance(identifier, str) or not re.fullmatch(
        r"yaxgate1auth_v1_[0-9a-f]{64}", identifier
    ):
        raise TransferBlocked(f"{key} pre-execution authorization ID is malformed")
    for field in (
        "authorization_file_sha256", "source_registry_sha256",
        "typed_spec_sha256", "code_sha256",
    ):
        require_sha256(authorization.get(field), f"{key} authorization {field}")
    for field in ("authorization_git_commit", "authorized_implementation_commit"):
        if not isinstance(authorization.get(field), str) or not re.fullmatch(
            r"[0-9a-f]{40}", authorization[field]
        ):
            raise TransferBlocked(f"{key} authorization {field} is malformed")
    if (
        authorization["authorization_git_commit"]
        == authorization["authorized_implementation_commit"]
    ):
        raise TransferBlocked(f"{key} authorization was not separately committed")
    issued = parse_module_time(
        authorization.get("issued_at_utc"), f"{key} authorization issued_at"
    )
    not_before = parse_module_time(
        authorization.get("not_before_utc"), f"{key} authorization not_before"
    )
    not_after = parse_module_time(
        authorization.get("not_after_utc"), f"{key} authorization not_after"
    )
    if not issued <= not_before <= not_after:
        raise TransferBlocked(f"{key} authorization time window is malformed")
    return dict(authorization)


def validate_common_receipt(
    receipt: dict[str, Any], module: dict[str, Any]
) -> tuple[dict[str, str], dict[str, Any], dict[str, Any], dict[str, Any]]:
    key = module["key"]
    contract = MODULE_CONTRACTS[key]
    if receipt.get("schema_version") != contract["receipt_schema"]:
        raise TransferBlocked(f"{key} receipt schema differs")
    if receipt.get("status") != contract["receipt_status"]:
        raise TransferBlocked(f"{key} receipt status differs")
    if (
        receipt.get("canonical_spec_id") != CANONICAL_BINDING["id"]
        or receipt.get("canonical_spec_sha256") != CANONICAL_BINDING["sha256"]
    ):
        raise TransferBlocked(f"{key} receipt canonical specification differs")
    typed = contract["typed_spec"]
    observed_id = json_pointer(receipt, typed["id_pointer"], f"{key} typed ID")
    observed_sha = json_pointer(receipt, typed["sha256_pointer"], f"{key} typed SHA")
    if observed_id != typed["id"] or observed_sha != typed["sha256"]:
        raise TransferBlocked(f"{key} receipt typed specification differs")
    if not TYPED_ID.fullmatch(observed_id):
        raise TransferBlocked(f"{key} receipt typed ID is malformed")
    code_hash = json_pointer(receipt, contract["code_hash_pointer"], f"{key} code hash")
    if code_hash != contract["code_hash"]:
        raise TransferBlocked(f"{key} executed-code hash differs")
    require_sha256(code_hash, f"{key} code hash")
    command_binding = validate_command_binding(receipt, module)
    execution_runtime = validate_execution_runtime(receipt, key)
    execution_authorization = validate_pre_execution_authorization_receipt(
        receipt, key, observed_id, observed_sha, code_hash
    )
    return {
        "typed_id": observed_id,
        "typed_sha256": observed_sha,
        "code_hash": code_hash,
    }, command_binding, execution_runtime, execution_authorization


def require_aware_timestamp(receipt: dict[str, Any], field: str, label: str) -> str:
    return iso_utc(parse_module_time(receipt.get(field), f"{label} {field}"))


def project_cells_receipt(
    receipt: dict[str, Any], module: dict[str, Any], receipt_sha256: str
) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    identity, command, execution_runtime, execution_authorization = (
        validate_common_receipt(receipt, module)
    )
    if receipt.get("aggregate_schema_version") != "yax-numerical-cells-v1":
        raise TransferBlocked("cells aggregate schema differs")
    if (
        receipt.get("analysis_spec_id") != NUMERICAL_SPEC_ID
        or receipt.get("analysis_spec_sha256") != NUMERICAL_SPEC_SHA256
    ):
        raise TransferBlocked("cells receipt is not reciprocally bound to the numerical spec")
    if receipt.get("cells_filename") != "aggregate_cells.csv":
        raise TransferBlocked("cells receipt artifact filename differs")
    cells_sha = require_sha256(receipt.get("cells_sha256"), "cells artifact hash")
    if receipt.get("builder_code_sha256") != CELL_CODE_SHA256:
        raise TransferBlocked("cells builder hash differs")
    if receipt.get("builder_transitive_code_sha256") != CELL_TRANSITIVE_SHA256:
        raise TransferBlocked("cells transitive code hash differs")
    if receipt.get("runtime_code_hashes") != {CELL_CODE_PATH: CELL_CODE_SHA256}:
        raise TransferBlocked("cells runtime code-hash map differs")
    assignment_sha = require_sha256(
        receipt.get("assignment_fingerprint_sha256"), "assignment fingerprint"
    )
    assignment_artifact_sha = require_sha256(
        receipt.get("assignment_fingerprint_artifact_sha256"),
        "assignment fingerprint artifact",
    )
    if receipt.get("balanced_grid_complete") is not True:
        raise TransferBlocked("cells receipt does not certify the balanced grid")
    if receipt.get("weight_application_count") != 1:
        raise TransferBlocked("cells receipt does not certify one weight application")
    if receipt.get("contains_resolved_private_paths") is not False:
        raise TransferBlocked("cells receipt does not deny private paths")
    expected_grid = {"occupation_count": 468, "observed_month_count": 114, "row_count": 53352}
    if receipt.get("grid") != expected_grid:
        raise TransferBlocked("cells receipt grid is not the immutable Gate-1 grid")
    if (
        receipt.get("occupation_count") != 468
        or receipt.get("observed_month_count") != 114
        or receipt.get("cells_row_count") != 53352
    ):
        raise TransferBlocked("cells top-level grid counts differ")
    generated = require_aware_timestamp(receipt, "generated_at_utc", "cells receipt")
    projection = {
        "schema_version": PROJECTION_SCHEMA,
        "module_key": "cells",
        "source_receipt_schema": receipt["schema_version"],
        "source_receipt_status": receipt["status"],
        "source_receipt_sha256": receipt_sha256,
        "generated_at_utc": generated,
        "canonical_spec": CANONICAL_BINDING,
        "typed_spec": MODULE_CONTRACTS["cells"]["typed_spec"],
        "numerical_consumer_spec": {
            "id": NUMERICAL_SPEC_ID, "sha256": NUMERICAL_SPEC_SHA256,
        },
        "code_hashes": {
            "builder": CELL_CODE_SHA256, "transitive": CELL_TRANSITIVE_SHA256,
        },
        "aggregate_artifact": {
            "filename": "aggregate_cells.csv", "sha256": cells_sha,
        },
        "assignment_fingerprint_sha256": assignment_sha,
        "assignment_fingerprint_artifact_sha256": assignment_artifact_sha,
        "grid": expected_grid,
        "weight_application_count": 1,
        "execution_command_binding": command,
        "execution_runtime_authentication": execution_runtime,
        "pre_execution_authorization": execution_authorization,
    }
    return projection, identity, command


def project_target_receipt(
    receipt: dict[str, Any], module: dict[str, Any], receipt_sha256: str
) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    identity, command, execution_runtime, execution_authorization = (
        validate_common_receipt(receipt, module)
    )
    if (
        receipt.get("cell_build_spec_id") != CELL_SPEC_ID
        or receipt.get("cell_build_spec_sha256") != CELL_SPEC_SHA256
    ):
        raise TransferBlocked("target receipt cell-spec binding differs")
    cells_sha = require_sha256(
        receipt.get("authenticated_cells_sha256"), "target source-declared cells hash"
    )
    source_receipt_sha = require_sha256(
        receipt.get("source_aggregate_receipt_sha256"),
        "target source aggregate receipt hash",
    )
    if receipt.get("code_hashes") != TARGET_CODE_HASHES:
        raise TransferBlocked("target receipt code-hash map differs from the terminal target spec")
    artifacts = require_hash_map(
        receipt.get("artifact_hashes"), TARGET_ARTIFACTS, "target artifact hashes"
    )
    audit_result_id = receipt.get("audit_result_id")
    if not isinstance(audit_result_id, str) or not re.fullmatch(
        r"yaxtargetaudit_v1_[0-9a-f]{64}", audit_result_id
    ):
        raise TransferBlocked("target audit result ID is malformed")
    generated = require_aware_timestamp(receipt, "generated_at_utc", "target receipt")
    projection = {
        "schema_version": PROJECTION_SCHEMA,
        "module_key": "target",
        "source_receipt_schema": receipt["schema_version"],
        "source_receipt_status": receipt["status"],
        "source_receipt_sha256": receipt_sha256,
        "generated_at_utc": generated,
        "canonical_spec": CANONICAL_BINDING,
        "typed_spec": MODULE_CONTRACTS["target"]["typed_spec"],
        "cell_spec": {"id": CELL_SPEC_ID, "sha256": CELL_SPEC_SHA256},
        "authenticated_cells_sha256": cells_sha,
        "source_aggregate_receipt_sha256": source_receipt_sha,
        "executed_code_sha256": TARGET_CODE_SHA256,
        "audit_result_id": audit_result_id,
        "artifact_hashes": artifacts,
        "execution_command_binding": command,
        "execution_runtime_authentication": execution_runtime,
        "pre_execution_authorization": execution_authorization,
    }
    return projection, identity, command


def project_numerical_receipt(
    receipt: dict[str, Any], module: dict[str, Any], receipt_sha256: str
) -> tuple[dict[str, Any], dict[str, str], dict[str, Any]]:
    identity, command, execution_runtime, execution_authorization = (
        validate_common_receipt(receipt, module)
    )
    cells_sha = require_sha256(receipt.get("cells_sha256"), "numerical cells hash")
    cells_receipt_sha = require_sha256(
        receipt.get("cells_receipt_sha256"), "numerical cells-receipt hash"
    )
    fixed_hashes = {
        "artifact_safety_sha256": ARTIFACT_SAFETY_SHA256,
        "cell_builder_sha256": CELL_CODE_SHA256,
        "legacy_engine_sha256": LEGACY_ENGINE_SHA256,
    }
    for field, expected in fixed_hashes.items():
        if receipt.get(field) != expected:
            raise TransferBlocked(f"numerical receipt {field} differs")
    if receipt.get("submitted_design_source_sha256") != NUMERICAL_SUBMITTED_CODE_HASHES:
        raise TransferBlocked("numerical submitted-design code hashes differ")
    output_hashes = require_hash_map(
        receipt.get("output_hashes"), NUMERICAL_ARTIFACTS,
        "numerical output hashes",
    )
    model_count = require_exact_int(receipt.get("model_count"), "numerical model_count", 1)
    passed_count = require_exact_int(
        receipt.get("passed_model_count"), "numerical passed_model_count", 0
    )
    if model_count != 11 or passed_count != model_count:
        raise TransferBlocked("numerical PASS receipt does not certify all eleven models")
    if receipt.get("protected_microdata_read_by_this_program") is not False:
        raise TransferBlocked("numerical receipt does not deny protected-microdata access")
    start = require_aware_timestamp(receipt, "started_at_utc", "numerical receipt")
    end = require_aware_timestamp(receipt, "finished_at_utc", "numerical receipt")
    if parse_module_time(end, "numerical end") < parse_module_time(start, "numerical start"):
        raise TransferBlocked("numerical receipt end precedes start")
    projection = {
        "schema_version": PROJECTION_SCHEMA,
        "module_key": "numerical",
        "source_receipt_schema": receipt["schema_version"],
        "source_receipt_status": receipt["status"],
        "source_receipt_sha256": receipt_sha256,
        "start_utc": start,
        "end_utc": end,
        "canonical_spec": CANONICAL_BINDING,
        "typed_spec": MODULE_CONTRACTS["numerical"]["typed_spec"],
        "cells_sha256": cells_sha,
        "cells_receipt_sha256": cells_receipt_sha,
        "code_hashes": {
            "numerical_runner": NUMERICAL_CODE_SHA256,
            "artifact_safety": ARTIFACT_SAFETY_SHA256,
            "cell_builder": CELL_CODE_SHA256,
            "legacy_engine": LEGACY_ENGINE_SHA256,
            "submitted_design_sources": NUMERICAL_SUBMITTED_CODE_HASHES,
        },
        "model_count": model_count,
        "passed_model_count": passed_count,
        "output_hashes": output_hashes,
        "execution_command_binding": command,
        "execution_runtime_authentication": execution_runtime,
        "pre_execution_authorization": execution_authorization,
    }
    return projection, identity, command


PROJECTORS = {
    "cells": project_cells_receipt,
    "target": project_target_receipt,
    "numerical": project_numerical_receipt,
}


def validate_cross_receipt_bindings(
    projections: dict[str, dict[str, Any]],
    snapshots: dict[Path, FileSnapshot],
) -> dict[str, bool]:
    cells = projections["cells"]
    target = projections["target"]
    numerical = projections["numerical"]
    cells_receipt_sha = snapshots[Path(MODULE_CONTRACTS["cells"]["receipt_file"])].sha256
    cells_artifact_sha = cells["aggregate_artifact"]["sha256"]
    checks = {
        "target_to_cell_receipt": (
            target["source_aggregate_receipt_sha256"] == cells_receipt_sha
        ),
        "target_to_cell_artifact": (
            target["authenticated_cells_sha256"] == cells_artifact_sha
        ),
        "numerical_to_cell_receipt": (
            numerical["cells_receipt_sha256"] == cells_receipt_sha
        ),
        "numerical_to_cell_artifact": (
            numerical["cells_sha256"] == cells_artifact_sha
        ),
        "cell_to_numerical_spec": (
            cells["numerical_consumer_spec"]
            == {"id": NUMERICAL_SPEC_ID, "sha256": NUMERICAL_SPEC_SHA256}
        ),
    }
    failed = sorted(key for key, value in checks.items() if value is not True)
    if failed:
        raise TransferBlocked(
            "cross-receipt cell hash consistency differs: " + ", ".join(failed)
        )
    return checks


def validate_shared_execution_authorization(
    projections: dict[str, dict[str, Any]],
    schedulers: dict[str, dict[str, Any]],
    committed_authorization: dict[str, Any],
) -> dict[str, bool]:
    """Bind every fresh job to one authorization and its validity window."""
    authorizations = {
        key: projections[key]["pre_execution_authorization"] for key in MODULE_KEYS
    }
    common_fields = (
        "schema_version", "status", "authorization_id",
        "authorization_file_sha256", "authorization_git_commit",
        "authorized_implementation_commit", "issued_at_utc", "not_before_utc",
        "not_after_utc", "source_registry_sha256",
    )
    first = authorizations[MODULE_KEYS[0]]
    checks: dict[str, bool] = {
        f"shared_authorization_{field}": all(
            authorizations[key][field] == first[field] for key in MODULE_KEYS
        )
        for field in common_fields
    }
    not_before = parse_module_time(first["not_before_utc"], "authorization not_before")
    not_after = parse_module_time(first["not_after_utc"], "authorization not_after")
    for key in MODULE_KEYS:
        expected_module = committed_authorization["modules"][key]
        expected_receipt_summary = {
            "schema_version": committed_authorization["schema_version"],
            "status": committed_authorization["status"],
            "authorization_id": committed_authorization["authorization_id"],
            "authorization_file_sha256": committed_authorization[
                "authorization_file_sha256"
            ],
            "authorization_git_commit": committed_authorization[
                "authorization_git_commit"
            ],
            "authorized_implementation_commit": committed_authorization[
                "authorized_implementation_commit"
            ],
            "issued_at_utc": committed_authorization["issued_at_utc"],
            "not_before_utc": committed_authorization["not_before_utc"],
            "not_after_utc": committed_authorization["not_after_utc"],
            "module_key": key,
            "typed_spec_id": expected_module["typed_spec_id"],
            "typed_spec_sha256": expected_module["typed_spec_sha256"],
            "code_sha256": expected_module["code_sha256"],
            "source_registry_sha256": committed_authorization[
                "source_registry_sha256"
            ],
        }
        checks[f"{key}_matches_committed_authorization"] = (
            authorizations[key] == expected_receipt_summary
        )
        checks[f"{key}_scheduler_within_authorization_window"] = (
            schedulers[key]["_start"] >= not_before
            and schedulers[key]["_end"] <= not_after
        )
    failed = sorted(key for key, value in checks.items() if value is not True)
    if failed:
        raise TransferBlocked(
            "execution authorization consistency differs: " + ", ".join(failed)
        )
    return checks


def build_normalized_receipts(
    spec: dict[str, Any], snapshots: dict[Path, FileSnapshot],
    normalizer_state: dict[str, Any],
    committed_authorization: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, bool]]:
    modules = validate_spec(spec)
    zone_name = spec["scheduler_time_zone"]
    projections: dict[str, dict[str, Any]] = {}
    identities: dict[str, dict[str, str]] = {}
    command_bindings: dict[str, dict[str, Any]] = {}
    schedulers: dict[str, dict[str, Any]] = {}
    receipts: dict[str, dict[str, Any]] = {}
    for module in modules:
        key = module["key"]
        receipt_snapshot = snapshots[Path(module["module_receipt_file"])]
        scheduler_snapshot = snapshots[Path(module["scheduler_record_file"])]
        if receipt_snapshot.sha256 != module["module_receipt_sha256"]:
            raise TransferBlocked(f"{key} module receipt byte hash differs")
        if scheduler_snapshot.sha256 != module["scheduler_record_sha256"]:
            raise TransferBlocked(f"{key} scheduler record byte hash differs")
        receipt = load_json_bytes(receipt_snapshot.payload, f"{key} receipt")
        receipts[key] = receipt
        scheduler_raw = load_json_bytes(
            scheduler_snapshot.payload, f"{key} scheduler receipt"
        )
        projection, identity, command_binding = PROJECTORS[key](
            receipt, module, receipt_snapshot.sha256
        )
        projections[key] = projection
        identities[key] = identity
        command_bindings[key] = command_binding
        schedulers[key] = validate_scheduler(scheduler_raw, module, zone_name)
    validate_no_future_scheduler_times(schedulers)
    cross_checks = validate_cross_receipt_bindings(projections, snapshots)
    cross_checks.update(
        validate_shared_execution_authorization(
            projections, schedulers, committed_authorization
        )
    )

    selected_times = {
        module["key"]: select_times(
            receipts[module["key"]], module, schedulers[module["key"]]
        )
        for module in modules
    }
    for module in modules:
        validate_generated_at_within_scheduler(
            receipts[module["key"]], module, schedulers[module["key"]]
        )
    validate_dependency_intervals(selected_times)

    normalized: dict[str, dict[str, Any]] = {}
    for module in modules:
        key = module["key"]
        contract = MODULE_CONTRACTS[key]
        receipt_snapshot = snapshots[Path(module["module_receipt_file"])]
        scheduler_snapshot = snapshots[Path(module["scheduler_record_file"])]
        scheduler = schedulers[key]
        start_utc, end_utc, time_source = selected_times[key]
        dependencies: list[dict[str, Any]] = []
        for upstream in contract["depends_on"]:
            dependencies.append({
                "module_key": upstream,
                "typed_spec_id": normalized[upstream]["typed_spec"]["id"],
                "module_run_fingerprint_sha256": normalized[upstream][
                    "module_run_fingerprint_sha256"
                ],
                "source_receipt_hash_link_present": upstream == "cells",
                "relationship": (
                    "source_receipt_hash_link_and_temporal_dependency"
                    if upstream == "cells"
                    else "temporal_and_topological_dependency_only"
                ),
            })
        core = {
            "command": canonical_bytes(
                command_bindings[key]["sanitized_argv"]
            ).decode("utf-8"),
            "start_utc": start_utc,
            "end_utc": end_utc,
            "exit_code": scheduler["exit_status"],
            "mode": contract["mode"],
            "code_hash": identities[key]["code_hash"],
            "spec_id": CANONICAL_BINDING["id"],
        }
        projection_sha = sha256_bytes(rendered_json_bytes(projections[key]))
        fingerprint_payload = {
            "schema_version": "yax-gate1-module-run-fingerprint-v3",
            "module_key": key,
            "run_id": module["run_id"],
            "canonical_spec": CANONICAL_BINDING,
            "typed_spec": {
                "kind": contract["typed_spec"]["kind"],
                "id": identities[key]["typed_id"],
                "sha256": identities[key]["typed_sha256"],
            },
            "normalized_run_receipt": core,
            "source_bindings": {
                "module_receipt_sha256": receipt_snapshot.sha256,
                "scheduler_record_sha256": scheduler_snapshot.sha256,
                "public_projection_sha256": projection_sha,
                "execution_command_binding_sha256": command_bindings[key][
                    "binding_sha256"
                ],
                "normalizer_source_sha256": normalizer_state["source_sha256"],
                "normalizer_git_commit": normalizer_state["git_commit"],
                "normalizer_git_tree": normalizer_state["git_tree"],
            },
            "scheduler_jobnumber": scheduler["jobnumber"],
            "normalization_dependencies": dependencies,
        }
        fingerprint = sha256_bytes(canonical_bytes(fingerprint_payload))
        normalized[key] = {
            "schema_version": NORMALIZED_SCHEMA,
            **core,
            "run_id": module["run_id"],
            "typed_spec": fingerprint_payload["typed_spec"],
            "time_source": time_source,
            "scheduler": {
                field: value for field, value in scheduler.items()
                if not field.startswith("_")
            },
            "source_bindings": {
                "input_receipt": module["module_receipt_file"],
                "module_receipt_sha256": receipt_snapshot.sha256,
                "scheduler_record": module["scheduler_record_file"],
                "scheduler_record_sha256": scheduler_snapshot.sha256,
                "public_projection": f"receipt_projections/{key}.json",
                "public_projection_sha256": projection_sha,
                "execution_command_binding_sha256": command_bindings[key][
                    "binding_sha256"
                ],
                "normalizer_source_sha256": normalizer_state["source_sha256"],
                "normalizer_git_commit": normalizer_state["git_commit"],
                "normalizer_git_tree": normalizer_state["git_tree"],
            },
            "normalization_dependencies": dependencies,
            "dependency_semantics": (
                "Immutable temporal and topological ordering. "
                "source_receipt_hash_link_present says only whether the downstream source "
                "receipt names that upstream receipt hash; no stronger provenance is implied."
            ),
            "module_run_fingerprint_algorithm": fingerprint_payload["schema_version"],
            "module_run_fingerprint_sha256": fingerprint,
            "scope": (
                "Execution-receipt normalization, public projection, and byte provenance "
                "only; no result, ledger integration, or scientific claim is validated."
            ),
        }
    return normalized, projections, cross_checks


def paths_overlap(left: Path, right: Path) -> bool:
    left = left.resolve(strict=False)
    right = right.resolve(strict=False)
    return left == right or left in right.parents or right in left.parents


class KernelNoReplaceUnavailable(OSError):
    """The mounted filesystem rejects the kernel no-replace primitive."""


def _atomic_rename_noreplace(source: Path, target: Path) -> None:
    """Atomically publish a directory without overwriting a racing target."""
    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    target_bytes = os.fsencode(target)
    if sys.platform.startswith("linux") and hasattr(libc, "renameat2"):
        function = libc.renameat2
        function.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        result = function(-100, source_bytes, -100, target_bytes, 1)  # RENAME_NOREPLACE
    elif sys.platform == "darwin" and hasattr(libc, "renameatx_np"):
        function = libc.renameatx_np
        function.argtypes = [
            ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p,
            ctypes.c_uint,
        ]
        function.restype = ctypes.c_int
        result = function(
            -2, source_bytes, -2, target_bytes, 0x00000004
        )  # AT_FDCWD, RENAME_EXCL
    else:
        raise KernelNoReplaceUnavailable(
            errno.ENOSYS, "platform lacks an atomic no-replace directory rename"
        )
    if result != 0:
        error = ctypes.get_errno()
        if error in {errno.EEXIST, errno.ENOTEMPTY}:
            raise TransferBlocked("output target appeared during publication; refusing overwrite")
        unavailable = {
            errno.EINVAL, errno.ENOSYS,
            getattr(errno, "ENOTSUP", errno.EINVAL),
            getattr(errno, "EOPNOTSUPP", errno.EINVAL),
        }
        if error in unavailable:
            raise KernelNoReplaceUnavailable(
                error, "filesystem does not support atomic no-replace rename"
            )
        raise TransferBlocked(
            f"atomic no-replace publication failed with errno {error}"
        )


def _select_publication_method(parent: Path) -> str:
    """Probe the target filesystem before any public report is rendered."""
    probe_root = Path(tempfile.mkdtemp(prefix=".gate1-rename-probe-", dir=parent))
    source = probe_root / "source"
    target = probe_root / "target"
    source.mkdir(mode=0o700)
    try:
        try:
            _atomic_rename_noreplace(source, target)
        except KernelNoReplaceUnavailable:
            return LOCKED_RENAME_METHOD
        if source.exists() or not target.is_dir():
            raise TransferBlocked("kernel no-replace probe produced an invalid state")
        return KERNEL_NOREPLACE_METHOD
    finally:
        shutil.rmtree(probe_root)


def publication_semantics(method: str) -> dict[str, Any]:
    if method == KERNEL_NOREPLACE_METHOD:
        return {
            "method": KERNEL_NOREPLACE_METHOD,
            "kernel_noreplace_used": True,
            "exclusive_cooperating_publisher_lock_required": True,
            "same_parent_atomic_rename": True,
            "noncooperating_same_user_toctou": "NOT_APPLICABLE_KERNEL_NOREPLACE",
        }
    if method == LOCKED_RENAME_METHOD:
        return {
            "method": LOCKED_RENAME_METHOD,
            "kernel_noreplace_used": False,
            "exclusive_cooperating_publisher_lock_required": True,
            "same_parent_atomic_rename": True,
            "noncooperating_same_user_toctou": (
                "BOUNDED_BUT_NOT_ELIMINATED_BETWEEN_FINAL_ABSENCE_CHECK_AND_RENAME"
            ),
        }
    raise TransferBlocked("publication method is not recognized")


@dataclass
class OutputReservation:
    target: Path
    staging: Path
    lock: Path
    lock_fd: int | None
    lock_identity: tuple[int, int, int, int, int, int]
    publication_method: str
    committed: bool = False
    post_commit_warnings: tuple[str, ...] = ()

    @classmethod
    def reserve(
        cls, target: Path, disjoint_inputs: Iterable[Path]
    ) -> "OutputReservation":
        raw = target.expanduser()
        if raw.name in {"", ".", ".."}:
            raise TransferBlocked("output directory must be a named leaf")
        try:
            parent = raw.parent.resolve(strict=True)
        except OSError as exc:
            raise TransferBlocked("output parent must already exist") from exc
        resolved = parent / raw.name
        for path in disjoint_inputs:
            if paths_overlap(resolved, path):
                raise TransferBlocked("output directory must be disjoint from every input")
        if os.path.lexists(resolved):
            raise TransferBlocked("output directory already exists; refusing overwrite")
        lock = parent / f".{resolved.name}.transfer.lock"
        try:
            lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            raise TransferBlocked(
                "output name is locked; inspect PID/host/time metadata and remove the "
                "lock manually only after confirming no publisher is active"
            ) from exc
        staging: Path | None = None
        try:
            host = socket.gethostname()
            if not SAFE_HOST_TOKEN.fullmatch(host):
                raise TransferBlocked("local hostname cannot be safely recorded in lock")
            lock_metadata = {
                "schema_version": "yax-gate1-transfer-lock-v1",
                "pid": os.getpid(),
                "host": host,
                "created_at_utc": iso_utc(datetime.now(timezone.utc)),
                "target_leaf": resolved.name,
            }
            payload = rendered_json_bytes(lock_metadata)
            written = os.write(lock_fd, payload)
            if written != len(payload):
                raise TransferBlocked("could not write complete transfer lock metadata")
            os.fsync(lock_fd)
            lock_opened = os.fstat(lock_fd)
            lock_current = lock.lstat()
            if (
                _identity(lock_opened) != _identity(lock_current)
                or not stat.S_ISREG(lock_current.st_mode)
                or lock_current.st_nlink != 1
            ):
                raise TransferBlocked("transfer lock identity is invalid")
            if os.path.lexists(resolved):
                raise TransferBlocked("output target appeared during reservation")
            method = _select_publication_method(parent)
            staging = Path(
                tempfile.mkdtemp(prefix=f".{resolved.name}.tmp-", dir=parent)
            )
            os.chmod(staging, 0o700)
        except Exception:
            if staging is not None and staging.exists():
                shutil.rmtree(staging)
            os.close(lock_fd)
            lock.unlink(missing_ok=True)
            raise
        if staging is None:  # pragma: no cover - guarded by successful mkdtemp
            raise AssertionError("internal staging reservation is absent")
        return cls(
            resolved, staging, lock, lock_fd, _identity(lock_current), method
        )

    def _verify_lock_and_absence_for_fallback(self) -> None:
        if self.lock_fd is None:
            raise TransferBlocked("ordinary-rename fallback lacks its open lock")
        try:
            opened = os.fstat(self.lock_fd)
            current = self.lock.lstat()
        except OSError as exc:
            raise TransferBlocked("ordinary-rename fallback lock is missing") from exc
        if (
            _identity(opened) != self.lock_identity
            or _identity(current) != self.lock_identity
            or not stat.S_ISREG(current.st_mode)
            or current.st_nlink != 1
        ):
            raise TransferBlocked("ordinary-rename fallback lock changed")
        if self.staging.parent != self.target.parent:
            raise TransferBlocked("ordinary-rename fallback is not same-parent")
        if os.path.lexists(self.target):
            raise TransferBlocked(
                "output target appeared before locked ordinary rename; refusing overwrite"
            )

    def release(self) -> None:
        if self.lock_fd is not None:
            os.close(self.lock_fd)
            self.lock_fd = None
        self.lock.unlink(missing_ok=True)

    def publish(self) -> tuple[str, ...]:
        if os.path.lexists(self.target):
            raise TransferBlocked("output target appeared before publication")
        for directory, dirnames, filenames in os.walk(
            self.staging, topdown=False, followlinks=False
        ):
            base = Path(directory)
            for name in filenames:
                path = base / name
                if path.is_symlink() or not path.is_file():
                    raise TransferBlocked("staging contains a non-regular output")
                with path.open("rb") as stream:
                    os.fsync(stream.fileno())
            for name in dirnames:
                if (base / name).is_symlink():
                    raise TransferBlocked("staging contains a symlink directory")
            descriptor = os.open(base, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
        # The selected rename is the sole publication commit point.  GPFS can
        # reject renameat2(RENAME_NOREPLACE) with EINVAL.  On that filesystem,
        # an ordinary same-parent rename is used only while the cooperating
        # publisher lock is still open and after an immediate absence recheck.
        if self.publication_method == KERNEL_NOREPLACE_METHOD:
            _atomic_rename_noreplace(self.staging, self.target)
        elif self.publication_method == LOCKED_RENAME_METHOD:
            self._verify_lock_and_absence_for_fallback()
            try:
                os.rename(self.staging, self.target)
            except OSError as exc:
                if os.path.lexists(self.target):
                    raise TransferBlocked(
                        "output collision blocked during locked ordinary rename"
                    ) from exc
                raise TransferBlocked(
                    f"locked ordinary rename failed with errno {exc.errno}"
                ) from exc
        else:
            raise TransferBlocked("publication method changed before publication")
        self.committed = True
        warnings: list[str] = []
        try:
            parent_fd = os.open(self.target.parent, os.O_RDONLY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        except OSError as error:
            warnings.append(f"parent_fsync_errno_{error.errno}")
        # Never raise after the commit point: doing so makes publication state
        # ambiguous to the caller. Surface advisory cleanup failures instead.
        try:
            self.release()
        except OSError as error:
            warnings.append(f"lock_cleanup_errno_{error.errno}")
            self.lock_fd = None
        self.post_commit_warnings = tuple(warnings)
        return self.post_commit_warnings

    def abandon(self) -> None:
        if self.committed:
            return
        if self.staging.exists():
            shutil.rmtree(self.staging)
        self.release()


def validate_staged_json(root: Path, expected: set[Path]) -> dict[str, str]:
    observed: set[Path] = set()
    observed_directories: set[Path] = set()
    expected_directories = {
        parent
        for path in expected
        for parent in path.parents
        if parent != Path(".")
    }
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(directory)
        for name in dirnames:
            candidate = base / name
            relative = candidate.relative_to(root)
            if candidate.is_symlink():
                raise TransferBlocked(f"staged symlink directory is forbidden: {relative}")
            observed_directories.add(relative)
        for name in filenames:
            candidate = base / name
            relative = candidate.relative_to(root)
            if candidate.is_symlink() or not candidate.is_file():
                raise TransferBlocked(f"staged artifact is not a regular file: {relative}")
            observed.add(relative)
    if observed != expected or observed_directories != expected_directories:
        raise TransferBlocked(
            "staged public artifact file/directory inventory differs from the exact contract"
        )
    hashes: dict[str, str] = {}
    for relative in sorted(observed, key=str):
        path = root / relative
        if path.is_symlink() or path.suffix != ".json":
            raise TransferBlocked(f"staged artifact is not a regular JSON file: {relative}")
        snapshot = stable_snapshot(path, relative)
        load_json_bytes(snapshot.payload, f"staged artifact {relative}")
        hashes[str(relative)] = snapshot.sha256
    return hashes


def validate_and_publish(spec_path: Path, input_dir: Path, output_dir: Path) -> dict[str, Any]:
    toolchain = verify_normalizer_toolchain()
    normalizer_state = capture_normalizer_state()
    normalizer_state["toolchain"] = toolchain
    authorization_state = capture_committed_authorization_state(normalizer_state)
    normalizer_state["committed_pre_execution_authorization"] = (
        authorization_state.public
    )
    spec_snapshot = stable_snapshot(spec_path, Path(spec_path.name))
    spec = load_json_bytes(spec_snapshot.payload, "terminal transfer spec")
    modules = validate_spec(spec)
    allowed = {
        Path(module[field])
        for module in modules
        for field in ("module_receipt_file", "scheduler_record_file")
    }
    input_root = input_dir.resolve(strict=True)
    snapshots = snapshot_sources(input_root, allowed)
    normalized, projections, cross_checks = build_normalized_receipts(
        spec, snapshots, normalizer_state, authorization_state.public
    )

    reservation = OutputReservation.reserve(
        output_dir, [input_root, spec_snapshot.path]
    )
    try:
        for key in MODULE_KEYS:
            write_json(
                reservation.staging / "receipt_projections" / f"{key}.json",
                projections[key],
            )
            write_json(
                reservation.staging / "normalized_receipts" / f"{key}.json",
                normalized[key],
            )
        expected_without_report = {
            *(Path("receipt_projections") / f"{key}.json" for key in MODULE_KEYS),
            *(Path("normalized_receipts") / f"{key}.json" for key in MODULE_KEYS),
        }
        artifact_hashes = validate_staged_json(
            reservation.staging, expected_without_report
        )
        report = {
            "schema_version": REPORT_SCHEMA,
            "status": PASS_STATUS,
            "transfer_spec_sha256": spec_snapshot.sha256,
            "canonical_spec_id": CANONICAL_BINDING["id"],
            "canonical_spec_sha256": CANONICAL_BINDING["sha256"],
            "normalized_module_count": len(normalized),
            "module_run_fingerprints": {
                key: normalized[key]["module_run_fingerprint_sha256"]
                for key in MODULE_KEYS
            },
            "cross_receipt_hash_consistency": cross_checks,
            "artifact_hashes_before_validation_report": artifact_hashes,
            "source_receipts_copied": False,
            "schema_specific_public_projections_created": True,
            "aggregate_cells_csv_opened": False,
            "decoded_recursive_enumerated_credential_scan": (
                "PASS_ENUMERATED_FORMS_AND_EXACT_PROJECTION_ALLOWLISTS"
            ),
            "runner_recorded_exact_argv_bindings": "PASS_HASH_CONSISTENT",
            "publication_semantics": publication_semantics(
                reservation.publication_method
            ),
            "normalizer_execution_provenance": normalizer_state,
            "run_ledger_map_generated": False,
            "run_manifest_or_status_updated": False,
            "scientific_validity": "NOT DETERMINED BY THIS NORMALIZER",
        }
        write_json(reservation.staging / "TRANSFER_VALIDATION.json", report)
        expected = expected_without_report | {Path("TRANSFER_VALIDATION.json")}
        validate_staged_json(reservation.staging, expected)

        # Recheck every byte and inode immediately before the no-replace rename.
        current_spec = stable_snapshot(spec_snapshot.path, spec_snapshot.relative)
        if (
            current_spec.identity != spec_snapshot.identity
            or current_spec.payload != spec_snapshot.payload
            or current_spec.sha256 != spec_snapshot.sha256
        ):
            raise TransferBlocked("terminal transfer spec changed before publication")
        final_source_recheck(input_root, allowed, snapshots)
        # The source inventory/re-read is the last nontrivial validation step.
        # Recheck the terminal spec again so a change during that step cannot
        # be hidden behind the earlier check.
        current_spec = stable_snapshot(spec_snapshot.path, spec_snapshot.relative)
        if (
            current_spec.identity != spec_snapshot.identity
            or current_spec.payload != spec_snapshot.payload
            or current_spec.sha256 != spec_snapshot.sha256
        ):
            raise TransferBlocked("terminal transfer spec changed before publication")
        verify_normalizer_state_unchanged(normalizer_state)
        verify_committed_authorization_state_unchanged(authorization_state)
        post_commit_warnings = reservation.publish()
        return {
            **report,
            "post_commit_cleanup_warnings": list(post_commit_warnings),
        }
    except Exception as exc:
        if reservation.committed:
            # The target already exists as the sole atomic commit.  Never
            # report that durable, validated publication as a failed call.
            warning = f"post_commit_internal_{type(exc).__name__}"
            return {
                **report,
                "post_commit_cleanup_warnings": [
                    *reservation.post_commit_warnings, warning,
                ],
            }
        reservation.abandon()
        raise


def parser() -> argparse.ArgumentParser:
    value = NonEchoingArgumentParser(description=__doc__, allow_abbrev=False)
    value.add_argument("--spec", type=Path, required=True)
    value.add_argument("--input-dir", type=Path, required=True)
    value.add_argument("--output-dir", type=Path, required=True)
    return value


def main(argv: list[str] | None = None) -> int:
    if argv is not None:
        raise TransferBlocked(
            "normalizer entry point does not accept a substituted argv source"
        )
    try:
        raw_cli = list(sys.argv[1:])
        original = list(getattr(sys, "orig_argv", []))
        args = parser().parse_args(raw_cli)
        if (
            len(raw_cli) != 6
            or raw_cli[::2] != ["--spec", "--input-dir", "--output-dir"]
            or len(original) != 9
            or original[1] != "-I"
            or original[3:] != raw_cli
            or Path(original[0]).resolve(strict=True)
            != Path(sys.executable).resolve(strict=True)
            or Path(original[2]).resolve(strict=True) != Path(__file__).resolve()
        ):
            raise TransferBlocked("normalizer direct isolated argv grammar is invalid")
        report = validate_and_publish(args.spec, args.input_dir, args.output_dir)
    except (OSError, TransferBlocked) as exc:
        print(f"TRANSFER BLOCKED: {exc}", file=sys.stderr)
        return 2
    try:
        print(json.dumps({
            "status": report["status"],
            "post_commit_cleanup_warnings": report[
                "post_commit_cleanup_warnings"
            ],
        }, sort_keys=True))
    except OSError:
        # Publication already committed; a closed diagnostic stream must not
        # turn durable success into a failed process status.
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
