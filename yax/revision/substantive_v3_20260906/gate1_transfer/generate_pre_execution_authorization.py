#!/usr/bin/env python3
"""Generate, but never commit, the one-shot Gate-1 execution authorization.

Run this only after the complete implementation has been reviewed and committed.
The generated JSON must then be reviewed and committed as the sole file in the
immediately following commit.  The three producers enforce that two-commit
sequence and the authorization time window before opening their inputs.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import tempfile
from typing import Any


V3_REL = Path("yax/revision/substantive_v3_20260906")
AUTHORIZATION_REL = V3_REL / "gate1_transfer/PRE_EXECUTION_AUTHORIZATION.json"
CANONICAL_REL = V3_REL / "contracts/specs/canonical_baseline_reproduction_v2.json"
CELL_SPEC_REL = V3_REL / "gate1_cells/CELL_BUILD_SPEC.json"
TARGET_SPEC_REL = V3_REL / "gate1_target/TARGET_AUDIT_SPEC.json"
NUMERICAL_SPEC_REL = V3_REL / "numerical_existence/ANALYSIS_SPEC.json"
CELL_CODE_REL = V3_REL / "gate1_cells/run_gate1_cells.py"
TARGET_CODE_REL = V3_REL / "gate1_target/run_exact_target_audit.py"
NUMERICAL_CODE_REL = V3_REL / "numerical_existence/run_numerical_existence_audit.py"

SCHEMA = "yax-gate1-pre-execution-authorization-v1"
STATUS = "AUTHORIZED_FRESH_GATE1_EXECUTION"
IDENTIFIER_PREFIX = "yaxgate1auth_v1_"
EXPECTED_GIT_PATH = Path("/usr/bin/git")
EXPECTED_PYTHON_RESOLVED_SHA256 = (
    "0887a2530329cef5a3a6b7c83c76590da9730f98f1e68497096bc05f20b92aa7"
)
EXPECTED_GIT_SHA256 = (
    "507917bbb5d24123c8e11df46df1d32483da1ce6420aa7ba7dd17de8ccd13a9e"
)
EXPECTED_GIT_VERSION = "git version 2.43.7"
SANITIZED_GIT_ENVIRONMENT = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
IMPORT_AFFECTING_ENVIRONMENT = (
    "PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE", "PYTHONSTARTUP",
)
COMMIT = re.compile(r"^[0-9a-f]{40}$")
MAX_ISSUED_CLOCK_SKEW_SECONDS = 300
MAX_AUTHORIZATION_WINDOW = timedelta(hours=24)


class AuthorizationGenerationError(RuntimeError):
    """Fail-closed authorization-generation error."""


class NonEchoingArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise AuthorizationGenerationError("authorization command-line grammar is invalid")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def rendered_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise AuthorizationGenerationError(f"duplicate JSON key in {path.name}")
            result[key] = value
        return result

    try:
        value = json.loads(
            path.read_bytes(), object_pairs_hook=unique_pairs,
            parse_constant=lambda _token: (_ for _ in ()).throw(
                AuthorizationGenerationError("nonfinite JSON value is forbidden")
            ),
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise AuthorizationGenerationError(f"cannot read required {path.name}") from exc
    if not isinstance(value, dict):
        raise AuthorizationGenerationError(f"required {path.name} is not an object")
    return value


def canonical_utc(value: str, label: str) -> tuple[str, datetime]:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise AuthorizationGenerationError(f"{label} is not ISO-8601") from exc
    if parsed.tzinfo is None:
        raise AuthorizationGenerationError(f"{label} requires a timezone")
    canonical = parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if value != canonical:
        raise AuthorizationGenerationError(f"{label} must use canonical UTC Z form")
    return canonical, parsed.astimezone(timezone.utc)


def expected_identifier(document: dict[str, Any]) -> str:
    core = dict(document)
    core.pop("authorization_id", None)
    return IDENTIFIER_PREFIX + hashlib.sha256(canonical_bytes(core)).hexdigest()


def self_id(document: dict[str, Any], field: str, prefix: str) -> str:
    core = dict(document)
    identifier = core.pop(field, None)
    expected = prefix + hashlib.sha256(canonical_bytes(core)).hexdigest()
    if identifier != expected:
        raise AuthorizationGenerationError(f"{field} is not self-consistent")
    return str(identifier)


def git_output(repo: Path, *arguments: str) -> str:
    completed = subprocess.run(
        [str(EXPECTED_GIT_PATH), *arguments], cwd=repo,
        env=SANITIZED_GIT_ENVIRONMENT, text=True, capture_output=True, check=False,
    )
    if completed.returncode != 0 or completed.stderr != "":
        raise AuthorizationGenerationError("Git state cannot be authenticated")
    return completed.stdout.strip()


def verify_authorization_inputs_at_head(repo: Path) -> None:
    """Reject indirect, hardlinked, changing, or non-HEAD authorization inputs."""
    required = (
        CANONICAL_REL, CELL_SPEC_REL, TARGET_SPEC_REL, NUMERICAL_SPEC_REL,
        CELL_CODE_REL, TARGET_CODE_REL, NUMERICAL_CODE_REL,
        Path(__file__).resolve(strict=True).relative_to(repo.resolve(strict=True)),
    )
    for relative in required:
        path = repo / relative
        first = path.lstat()
        if stat.S_ISLNK(first.st_mode) or not stat.S_ISREG(first.st_mode):
            raise AuthorizationGenerationError(
                f"authorization input is not a regular direct file: {relative}"
            )
        if first.st_nlink != 1:
            raise AuthorizationGenerationError(
                f"authorization input is hardlinked: {relative}"
            )
        payload = path.read_bytes()
        final = path.lstat()
        if (
            first.st_dev, first.st_ino, first.st_mode, first.st_nlink,
            first.st_size, first.st_mtime_ns,
        ) != (
            final.st_dev, final.st_ino, final.st_mode, final.st_nlink,
            final.st_size, final.st_mtime_ns,
        ):
            raise AuthorizationGenerationError(
                f"authorization input changed while read: {relative}"
            )
        committed = subprocess.run(
            [str(EXPECTED_GIT_PATH), "show", f"HEAD:{relative.as_posix()}"],
            cwd=repo, env=SANITIZED_GIT_ENVIRONMENT,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if (
            committed.returncode != 0
            or committed.stderr != b""
            or committed.stdout != payload
        ):
            raise AuthorizationGenerationError(
                f"authorization input differs from committed HEAD: {relative}"
            )


def verify_toolchain() -> None:
    if (
        sys.flags.isolated != 1
        or sys.flags.ignore_environment != 1
        or sys.flags.no_user_site != 1
        or not bool(getattr(sys.flags, "safe_path", False))
    ):
        raise AuthorizationGenerationError("generator Python must use isolated mode")
    if any(os.environ.get(name) for name in IMPORT_AFFECTING_ENVIRONMENT):
        raise AuthorizationGenerationError(
            "import-affecting Python environment variables are forbidden"
        )
    python_path = Path(sys.executable).resolve(strict=True)
    if sha256_file(python_path) != EXPECTED_PYTHON_RESOLVED_SHA256:
        raise AuthorizationGenerationError(
            "Python executable differs from the pinned SCC runtime"
        )
    if platform.python_version() != "3.13.8":
        raise AuthorizationGenerationError(
            "Python version differs from the pinned SCC runtime"
        )
    if not EXPECTED_GIT_PATH.is_file() or EXPECTED_GIT_PATH.is_symlink():
        raise AuthorizationGenerationError("pinned Git executable is absent or indirect")
    if sha256_file(EXPECTED_GIT_PATH) != EXPECTED_GIT_SHA256:
        raise AuthorizationGenerationError("Git executable differs from the pinned SCC runtime")
    if git_output(Path.cwd(), "--version") != EXPECTED_GIT_VERSION:
        raise AuthorizationGenerationError("Git version differs from the pinned SCC runtime")


def build_document(
    repo: Path,
    implementation_commit: str,
    issued_at_utc: str,
    not_before_utc: str,
    not_after_utc: str,
) -> dict[str, Any]:
    issued_text, issued = canonical_utc(issued_at_utc, "issued_at_utc")
    before_text, before = canonical_utc(not_before_utc, "not_before_utc")
    after_text, after = canonical_utc(not_after_utc, "not_after_utc")
    if not issued <= before <= after:
        raise AuthorizationGenerationError("authorization time window is not ordered")
    now = datetime.now(timezone.utc)
    if abs((issued - now).total_seconds()) > MAX_ISSUED_CLOCK_SKEW_SECONDS:
        raise AuthorizationGenerationError(
            "issued_at_utc is implausibly distant from the current UTC clock"
        )
    if before > now + timedelta(seconds=MAX_ISSUED_CLOCK_SKEW_SECONDS):
        raise AuthorizationGenerationError(
            "not_before_utc is implausibly future-dated"
        )
    if after - before > MAX_AUTHORIZATION_WINDOW:
        raise AuthorizationGenerationError(
            "authorization window may not exceed twenty-four hours"
        )
    if after <= now:
        raise AuthorizationGenerationError("authorization window is already expired")
    if not COMMIT.fullmatch(implementation_commit):
        raise AuthorizationGenerationError("implementation commit is malformed")

    canonical = load_json(repo / CANONICAL_REL)
    cell_spec = load_json(repo / CELL_SPEC_REL)
    target_spec = load_json(repo / TARGET_SPEC_REL)
    numerical_spec = load_json(repo / NUMERICAL_SPEC_REL)
    canonical_id = self_id(canonical, "spec_id", "yaxspec_v1_")
    cell_id = self_id(cell_spec, "cell_build_spec_id", "yaxcellspec_v1_")
    target_id = self_id(target_spec, "target_audit_spec_id", "yaxtargetspec_v1_")
    numerical_id = self_id(numerical_spec, "audit_spec_id", "yaxnumspec_v1_")
    sources = canonical.get("data", {}).get("sources")
    if not isinstance(sources, list) or not sources:
        raise AuthorizationGenerationError("canonical source registry is absent")
    source_hashes: dict[str, str] = {}
    for row in sources:
        if not isinstance(row, dict):
            raise AuthorizationGenerationError("canonical source registry row is invalid")
        source_id, digest = row.get("source_id"), row.get("sha256")
        if (
            not isinstance(source_id, str) or source_id in source_hashes
            or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise AuthorizationGenerationError("canonical source registry row is invalid")
        source_hashes[source_id] = digest

    document: dict[str, Any] = {
        "schema_version": SCHEMA,
        "status": STATUS,
        "issued_at_utc": issued_text,
        "not_before_utc": before_text,
        "not_after_utc": after_text,
        "authorized_implementation_commit": implementation_commit,
        "canonical_spec": {
            "id": canonical_id,
            "sha256": sha256_file(repo / CANONICAL_REL),
        },
        "source_registry_sha256": hashlib.sha256(
            canonical_bytes(source_hashes)
        ).hexdigest(),
        "modules": {
            "cells": {
                "typed_spec_id": cell_id,
                "typed_spec_sha256": sha256_file(repo / CELL_SPEC_REL),
                "code_sha256": sha256_file(repo / CELL_CODE_REL),
            },
            "target": {
                "typed_spec_id": target_id,
                "typed_spec_sha256": sha256_file(repo / TARGET_SPEC_REL),
                "code_sha256": sha256_file(repo / TARGET_CODE_REL),
            },
            "numerical": {
                "typed_spec_id": numerical_id,
                "typed_spec_sha256": sha256_file(repo / NUMERICAL_SPEC_REL),
                "code_sha256": sha256_file(repo / NUMERICAL_CODE_REL),
            },
        },
    }
    document["authorization_id"] = expected_identifier(document)
    return document


def publish_new_file(path: Path, payload: bytes) -> tuple[str, ...]:
    if os.path.lexists(path):
        raise AuthorizationGenerationError("authorization file already exists")
    parent = path.parent.resolve(strict=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".PRE_EXECUTION_AUTHORIZATION.tmp-", dir=parent
    )
    temporary = Path(temporary_name)
    committed = False
    warnings: list[str] = []
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise AuthorizationGenerationError("authorization file appeared; refusing overwrite") from exc
        committed = True
        try:
            temporary.unlink()
        except OSError as exc:
            warnings.append(f"temporary_cleanup_errno_{exc.errno}")
        try:
            parent_fd = os.open(parent, os.O_RDONLY)
            try:
                os.fsync(parent_fd)
            finally:
                os.close(parent_fd)
        except OSError as exc:
            warnings.append(f"parent_fsync_errno_{exc.errno}")
        return tuple(warnings)
    finally:
        if not committed:
            temporary.unlink(missing_ok=True)


def parser() -> argparse.ArgumentParser:
    result = NonEchoingArgumentParser(description=__doc__, allow_abbrev=False)
    result.add_argument("--implementation-commit", required=True)
    result.add_argument("--issued-at-utc", required=True)
    result.add_argument("--not-before-utc", required=True)
    result.add_argument("--not-after-utc", required=True)
    return result


def main() -> int:
    try:
        raw = list(os.sys.argv[1:])
        expected_flags = [
            "--implementation-commit", "--issued-at-utc", "--not-before-utc",
            "--not-after-utc",
        ]
        if len(raw) != 8 or raw[::2] != expected_flags:
            raise AuthorizationGenerationError("authorization command-line grammar is invalid")
        original = list(getattr(sys, "orig_argv", []))
        if (
            len(original) != len(raw) + 3 or original[1] != "-I"
            or original[3:] != raw
            or Path(original[0]).resolve(strict=True)
            != Path(sys.executable).resolve(strict=True)
            or Path(original[2]).resolve(strict=True) != Path(__file__).resolve()
        ):
            raise AuthorizationGenerationError(
                "generator requires direct isolated-script invocation"
            )
        args = parser().parse_args(raw)
        repo = Path(__file__).resolve().parents[4]
        verify_toolchain()
        head = git_output(repo, "rev-parse", "HEAD")
        if head != args.implementation_commit:
            raise AuthorizationGenerationError("implementation commit must equal current HEAD")
        if git_output(repo, "status", "--porcelain=v1", "--untracked-files=all"):
            raise AuthorizationGenerationError("implementation worktree must be clean")
        verify_authorization_inputs_at_head(repo)
        document = build_document(
            repo, args.implementation_commit, args.issued_at_utc,
            args.not_before_utc, args.not_after_utc,
        )
        warnings = publish_new_file(repo / AUTHORIZATION_REL, rendered_bytes(document))
    except (OSError, AuthorizationGenerationError) as exc:
        print(f"AUTHORIZATION BLOCKED: {exc}", file=os.sys.stderr)
        return 2
    try:
        print(json.dumps({
            "status": "GENERATED_UNCOMMITTED_REVIEW_REQUIRED",
            "authorization_id": document["authorization_id"],
            "authorization_file": str(AUTHORIZATION_REL),
            "post_commit_cleanup_warnings": list(warnings),
        }, sort_keys=True))
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
