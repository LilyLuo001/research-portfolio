#!/usr/bin/env python3
"""Export one exact non-array Grid Engine accounting record as safe JSON."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile
from typing import Any


QACCT_PATH = Path(
    "/usr/local/ogs-ge2011.11.p1/sge_root/bin/linux-x64/qacct"
)
QACCT_SHA256 = "aa8575f51ad1f07673ef862d6dfbe06381ebc53bdb88bb3a0256573ededc37e0"
QACCT_VERSION = "OGS/GE 2011.11p1"
EXPECTED_PYTHON_RESOLVED_SHA256 = (
    "0887a2530329cef5a3a6b7c83c76590da9730f98f1e68497096bc05f20b92aa7"
)
QACCT_ENVIRONMENT = {
    "PATH": "/usr/bin:/bin",
    "LC_ALL": "C",
    "SGE_ROOT": "/usr/local/sge/sge_root",
}
IMPORT_AFFECTING_ENVIRONMENT = (
    "PYTHONHOME", "PYTHONPATH", "PYTHONUSERBASE", "PYTHONSTARTUP",
)
JOB_ID = re.compile(r"^[1-9][0-9]{0,19}$")
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
MAXVMEM = re.compile(r"^(?:0|[0-9]+(?:\.[0-9]+)?[KMGTP]?)$")
KEY = re.compile(r"^[a-z][a-z0-9_]*$")
DELIMITER = re.compile(r"^={10,}$")
OUTPUT_FIELDS = {
    "jobnumber", "qname", "hostname", "start_time", "end_time", "failed",
    "exit_status", "ru_wallclock", "maxvmem", "qacct_export_provenance",
}


class QacctExportError(RuntimeError):
    """Fail-closed qacct export error."""


class NonEchoingArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise QacctExportError("qacct-export command-line grammar is invalid")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_time(value: str, label: str) -> str:
    try:
        parsed = datetime.strptime(value, "%a %b %d %H:%M:%S %Y")
    except ValueError as exc:
        raise QacctExportError(f"qacct {label} has an unsupported form") from exc
    return parsed.strftime("%a %b %d %H:%M:%S %Y")


def parse_exact_record(payload: str, requested_job: str) -> dict[str, Any]:
    """Require one delimiter and one exact, non-array accounting record."""
    lines = [line.rstrip() for line in payload.splitlines() if line.strip()]
    delimiters = [index for index, line in enumerate(lines) if DELIMITER.fullmatch(line)]
    if delimiters != [0]:
        raise QacctExportError("qacct output is not exactly one delimited record")
    fields: dict[str, str] = {}
    for line in lines[1:]:
        parts = line.split(None, 1)
        if len(parts) != 2 or not KEY.fullmatch(parts[0]) or not parts[1].strip():
            raise QacctExportError("qacct record contains a malformed field")
        key, value = parts[0], parts[1].strip()
        if key in fields:
            raise QacctExportError("qacct record contains a duplicate field")
        fields[key] = value
    required = {
        "jobnumber", "qname", "hostname", "taskid", "start_time", "end_time",
        "failed", "exit_status", "ru_wallclock", "maxvmem",
    }
    if not required.issubset(fields):
        raise QacctExportError("qacct record lacks a required field")
    if fields["jobnumber"] != requested_job or not JOB_ID.fullmatch(fields["jobnumber"]):
        raise QacctExportError("qacct jobnumber does not exactly join the requested job")
    if fields["taskid"] != "undefined":
        raise QacctExportError("qacct array-task records are not authorized")
    for field in ("qname", "hostname"):
        if not SAFE_TOKEN.fullmatch(fields[field]):
            raise QacctExportError(f"qacct {field} is unsafe")
    integer_fields: dict[str, int] = {}
    for field in ("failed", "exit_status"):
        if not re.fullmatch(r"[0-9]+", fields[field]):
            raise QacctExportError(f"qacct {field} is not an integer")
        integer_fields[field] = int(fields[field])
    try:
        wallclock = float(fields["ru_wallclock"])
    except ValueError as exc:
        raise QacctExportError("qacct ru_wallclock is not numeric") from exc
    if not math.isfinite(wallclock) or wallclock < 0:
        raise QacctExportError("qacct ru_wallclock is not finite and nonnegative")
    if not MAXVMEM.fullmatch(fields["maxvmem"]):
        raise QacctExportError("qacct maxvmem has an unsupported form")
    result: dict[str, Any] = {
        "jobnumber": requested_job,
        "qname": fields["qname"],
        "hostname": fields["hostname"],
        "start_time": canonical_time(fields["start_time"], "start_time"),
        "end_time": canonical_time(fields["end_time"], "end_time"),
        "failed": integer_fields["failed"],
        "exit_status": integer_fields["exit_status"],
        "ru_wallclock": wallclock,
        "maxvmem": fields["maxvmem"],
        "qacct_export_provenance": {
            "status": "RUNNER_RECORDED_BYTE_PINNED_CONSISTENCY",
            "role": "scheduler_accounting_export",
            "qacct_resolved_executable_sha256": QACCT_SHA256,
            "qacct_version": QACCT_VERSION,
            "exporter_code_sha256": sha256_file(Path(__file__).resolve()),
            "join_rule": "one_delimiter_one_record_exact_jobnumber_nonarray",
        },
    }
    if set(result) != OUTPUT_FIELDS:
        raise AssertionError("internal qacct output field contract is inconsistent")
    return result


def query_qacct(job_id: str) -> dict[str, Any]:
    if (
        sys.flags.isolated != 1
        or sys.flags.ignore_environment != 1
        or sys.flags.no_user_site != 1
        or not bool(getattr(sys.flags, "safe_path", False))
    ):
        raise QacctExportError("qacct exporter Python must use isolated mode")
    if any(os.environ.get(name) for name in IMPORT_AFFECTING_ENVIRONMENT):
        raise QacctExportError("import-affecting Python environment variables are forbidden")
    python_path = Path(sys.executable).resolve(strict=True)
    if (
        sha256_file(python_path) != EXPECTED_PYTHON_RESOLVED_SHA256
        or platform.python_version() != "3.13.8"
    ):
        raise QacctExportError("qacct exporter Python differs from the pinned SCC runtime")
    if not QACCT_PATH.is_file() or QACCT_PATH.is_symlink():
        raise QacctExportError("pinned qacct executable is absent or indirect")
    if sha256_file(QACCT_PATH) != QACCT_SHA256:
        raise QacctExportError("qacct executable differs from the pinned runtime")
    help_result = subprocess.run(
        [str(QACCT_PATH), "-help"], env=QACCT_ENVIRONMENT,
        text=True, capture_output=True, check=False,
    )
    help_lines = help_result.stdout.splitlines()
    if (
        help_result.returncode != 0 or help_result.stderr != ""
        or not help_lines or help_lines[0] != QACCT_VERSION
    ):
        raise QacctExportError("qacct observed version differs from the pinned runtime")
    completed = subprocess.run(
        [str(QACCT_PATH), "-j", job_id], env=QACCT_ENVIRONMENT,
        text=True, capture_output=True, check=False,
    )
    if completed.returncode != 0 or completed.stderr != "":
        raise QacctExportError("qacct did not return a completed accounting record")
    return parse_exact_record(completed.stdout, job_id)


def rendered_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")


def publish_new_file(path: Path, payload: bytes) -> tuple[str, ...]:
    if os.path.lexists(path):
        raise QacctExportError("scheduler output already exists; refusing overwrite")
    parent = path.parent.resolve(strict=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.tmp-", dir=parent)
    temporary = Path(name)
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
            raise QacctExportError("scheduler output appeared; refusing overwrite") from exc
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
    result.add_argument("--job-id", required=True)
    result.add_argument("--output", type=Path, required=True)
    return result


def main() -> int:
    try:
        raw = list(sys.argv[1:])
        original = list(getattr(sys, "orig_argv", []))
        if raw[::2] != ["--job-id", "--output"] or len(raw) != 4:
            raise QacctExportError("qacct-export command-line grammar is invalid")
        if (
            len(original) != 7 or original[1] != "-I" or original[3:] != raw
            or Path(original[0]).resolve(strict=True)
            != Path(sys.executable).resolve(strict=True)
            or Path(original[2]).resolve(strict=True) != Path(__file__).resolve()
        ):
            raise QacctExportError("qacct exporter requires direct isolated invocation")
        args = parser().parse_args(raw)
        if not JOB_ID.fullmatch(args.job_id):
            raise QacctExportError("job ID must be a positive digit string")
        record = query_qacct(args.job_id)
        warnings = publish_new_file(args.output, rendered_bytes(record))
    except (OSError, QacctExportError) as exc:
        print(f"QACCT EXPORT BLOCKED: {exc}", file=sys.stderr)
        return 2
    try:
        print(json.dumps({
            "status": "EXPORTED_SANITIZED_QACCT_RECORD",
            "jobnumber": args.job_id,
            "post_commit_cleanup_warnings": list(warnings),
        }, sort_keys=True))
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
