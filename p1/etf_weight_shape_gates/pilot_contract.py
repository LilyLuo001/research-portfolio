#!/usr/bin/env python3
"""Fail-closed authorization for the P1 Gate 0/1 full run.

Authorization has two phases. Phase one validates only staged, non-archive
files: PILOT_PASS.json, the scientific code fileset, the frozen configuration,
and the data contract. Phase two is the first operation permitted to touch the
canonical archive and reads only the explicitly supplied manifest file to
verify its raw-byte SHA-256.

Callers should catch PilotContractError and exit with its exit_code (78). No
glob, Parquet read, metadata scan, or output construction is permitted until
authorize_full_run returns successfully.

PILOT_PASS.json schema version 1 has these required top-level fields:
schema_version, status, hashes, required_invariant_ids, invariants,
golden_sample, raw_trace_inspection, and artifacts. Optional top-level fields
are created_at_utc, pilot_run_id, and runtime_fingerprint. Unknown
structural fields are rejected.
"""

from __future__ import annotations

import hashlib
import hmac
import csv
import json
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


EXIT_DATA_CONTRACT = 78
PILOT_SCHEMA_VERSION = 1
CODE_HASH_ALGORITHM = "sha256-fileset-path-length-bytes-v1"
JSON_HASH_ALGORITHM = "sha256-canonical-json-v1"
RAW_HASH_ALGORITHM = "sha256-raw-bytes-v1"

REQUIRED_GOLDEN_CATEGORIES = (
    "CORPORATE_ACTION",
    "DERIVATIVE_OR_NON_EQUITY_POSITION",
    "ETF_STATUS_TRANSITION_OR_FLAG_HISTORY_ANOMALY",
    "POOLED_ETF_MUTUAL_FUND_PORTFOLIO",
    "PURE_ETF",
    "RAPID_AUM_CHANGE",
    "STALE_REPORT",
)

REQUIRED_PILOT_ARTIFACTS = (
    "etf_flag_history_audits.json",
    "golden_case_results.json",
    "pilot_exposure_observations.csv",
    "pilot_input_files.json",
    "pilot_invariants.json",
    "pilot_raw_trace_inspection.csv",
)

CANDIDATE_CONTRACT_CONTROLS = (
    "availability_gate",
    "effective_dated_portfolio_mapping",
    "exact_date_tna",
    "no_current_header_backfill",
    "pro_rata_gate",
    "shared_pilot_transform",
)

# A caller may require additional invariants, but it may not omit these audit
# obligations from the current data-contract gate.
MINIMUM_REQUIRED_INVARIANT_IDS = (
    "CANDIDATE_IMPLEMENTATION_CONFORMANCE",
    "ECONOMIC_DATE_AND_AVAILABILITY_VERIFIED",
    "END_TO_END_PILOT_COMPLETED",
    "ETF_CLASS_EXPOSURE_PRO_RATA_ONLY",
    "GOLDEN_SAMPLE_COVERAGE",
    "DATE_SCOPED_PORTFOLIO_ETF_CLASS_RELATIONSHIP_VERIFIED",
    "INDEX_DOMAINS_DISTINCT",
    "MARKET_VAL_ROW_UNIT_VERIFIED",
    "NO_LOOKAHEAD",
    "PERCENT_TNA_IDENTITY_WITH_SAME_DATE_PORTFOLIO_TNA",
    "PERCENT_TNA_SEMANTICS_VERIFIED",
    "PORTFOLIO_AND_SHARE_CLASS_TNA_VERIFIED",
    "RAW_TRACE_RECONCILIATION",
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_AUTHORIZATION_SEAL = object()


class PilotContractError(RuntimeError):
    """A fail-closed Pilot authorization error suitable for exit status 78."""

    exit_code = EXIT_DATA_CONTRACT

    def __init__(self, reason: str, message: str):
        self.reason = reason
        super().__init__(f"{reason}: {message}")


@dataclass(frozen=True)
class LocalPilotAuthorization:
    """Proof that all non-archive Pilot checks succeeded."""

    pilot_pass_path: Path
    code_hash: str
    config_hash: str
    data_contract_hash: str
    expected_manifest_hash: str
    code_files: tuple[str, ...]
    invariant_ids: tuple[str, ...]
    _seal: object = field(repr=False, compare=False)


@dataclass(frozen=True)
class FullRunAuthorization:
    """Proof that local checks and the exact manifest hash both succeeded."""

    local: LocalPilotAuthorization
    manifest_path: Path
    manifest_hash: str
    _seal: object = field(repr=False, compare=False)


def _fail(reason: str, message: str) -> None:
    raise PilotContractError(reason, message)


def _lexical_absolute(path: Path | str) -> Path:
    """Return an absolute path without resolving or touching filesystem nodes."""

    return Path(os.path.abspath(os.fspath(path)))


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _reject_archive_local_path(
    path: Path | str,
    *,
    archive_root: Path | str | None,
    label: str,
) -> None:
    if archive_root is None:
        return
    candidate = _lexical_absolute(path)
    archive = _lexical_absolute(archive_root)
    if _is_within(candidate, archive):
        _fail(
            "LOCAL_INPUT_IN_ARCHIVE",
            f"{label} must be staged outside the canonical archive: {candidate}",
        )


def _lstat_without_symlink_ancestry(path: Path, *, label: str) -> int:
    """Return the final mode after rejecting every symlink in the path chain."""

    if not path.is_absolute():
        _fail("INTERNAL_PATH_ERROR", f"{label} path is not absolute: {path}")
    current = Path(path.anchor)
    parts = path.parts[1:]
    for index, part in enumerate(parts):
        current = current / part
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            reason = (
                "MISSING_FILE"
                if index == len(parts) - 1
                else "MISSING_PATH_COMPONENT"
            )
            _fail(reason, f"{label} path component does not exist: {current}")
        except OSError as exc:
            _fail(
                "UNREADABLE_PATH_COMPONENT",
                f"cannot inspect {label} path component {current}: {exc}",
            )
        if stat.S_ISLNK(mode):
            _fail(
                "SYMLINK_REJECTED",
                f"{label} path ancestry may not contain a symlink: {current}",
            )
    return mode


def _regular_file(
    path: Path | str,
    *,
    label: str,
    archive_root: Path | str | None = None,
) -> Path:
    _reject_archive_local_path(path, archive_root=archive_root, label=label)
    candidate = _lexical_absolute(path)
    mode = _lstat_without_symlink_ancestry(candidate, label=label)
    if not stat.S_ISREG(mode):
        _fail("NOT_REGULAR_FILE", f"{label} is not a regular file: {candidate}")
    return candidate


def require_regular_file(
    path: Path | str,
    *,
    label: str,
    archive_root: Path | str | None = None,
) -> Path:
    """Public safe-path check for targeted Pilot inputs."""

    return _regular_file(path, label=label, archive_root=archive_root)


def _directory(
    path: Path | str,
    *,
    label: str,
    archive_root: Path | str | None = None,
) -> Path:
    _reject_archive_local_path(path, archive_root=archive_root, label=label)
    candidate = _lexical_absolute(path)
    mode = _lstat_without_symlink_ancestry(candidate, label=label)
    if not stat.S_ISDIR(mode):
        _fail("NOT_DIRECTORY", f"{label} is not a directory: {candidate}")
    return candidate


def _canonical_relative_paths(paths: Iterable[str], *, label: str) -> tuple[str, ...]:
    try:
        supplied = list(paths)
    except TypeError:
        _fail("INVALID_PATH_SET", f"{label} must be an iterable of paths")
    if not supplied:
        _fail("INVALID_PATH_SET", f"{label} may not be empty")
    normalized: list[str] = []
    for raw in supplied:
        if type(raw) is not str:
            _fail("INVALID_RELATIVE_PATH", f"every {label} entry must be a string")
        if not raw or raw.startswith("/") or "\\" in raw:
            _fail(
                "INVALID_RELATIVE_PATH",
                f"non-relative or non-POSIX {label} entry: {raw!r}",
            )
        parts = raw.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            _fail("INVALID_RELATIVE_PATH", f"non-canonical {label} entry: {raw!r}")
        normalized.append("/".join(parts))
    if len(set(normalized)) != len(normalized):
        _fail("DUPLICATE_RELATIVE_PATH", f"{label} contains a duplicate")
    return tuple(sorted(normalized))


def compute_code_fileset_hash(
    code_root: Path | str,
    code_files: Iterable[str],
    *,
    archive_root: Path | str | None = None,
) -> tuple[str, tuple[str, ...]]:
    """Hash sorted relative path, byte length, and raw bytes for each code file."""

    root = _directory(code_root, label="code_root", archive_root=archive_root)
    relative_paths = _canonical_relative_paths(code_files, label="code_files")
    digest = hashlib.sha256(b"P1_CODE_FILESET_SHA256_V1\0")
    for relative in relative_paths:
        path = root.joinpath(*relative.split("/"))
        if not _is_within(_lexical_absolute(path), root):
            _fail("CODE_PATH_ESCAPE", f"code path escapes code_root: {relative}")
        path = _regular_file(
            path,
            label=f"code file {relative}",
            archive_root=archive_root,
        )
        try:
            data = path.read_bytes()
        except OSError as exc:
            _fail("UNREADABLE_FILE", f"cannot read code file {path}: {exc}")
        path_bytes = relative.encode("utf-8")
        digest.update(len(path_bytes).to_bytes(8, "big"))
        digest.update(path_bytes)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest(), relative_paths


def canonical_json_bytes(document: Any) -> bytes:
    """Return the frozen UTF-8 representation used for semantic JSON hashes."""

    try:
        text = json.dumps(
            document,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        _fail("NONCANONICAL_JSON", f"JSON cannot be canonicalized: {exc}")
    return text.encode("utf-8")


def canonical_json_hash(document: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(document)).hexdigest()


def _reject_json_constant(value: str) -> None:
    _fail("INVALID_JSON", f"non-standard JSON numeric constant: {value}")


def _reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            _fail("DUPLICATE_JSON_KEY", f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def load_json_value(
    path: Path | str,
    *,
    label: str,
    archive_root: Path | str | None = None,
) -> tuple[Any, Path]:
    """Load strict UTF-8 JSON from a path with no symlink in its ancestry."""

    selected = _regular_file(path, label=label, archive_root=archive_root)
    try:
        text = selected.read_bytes().decode("utf-8")
    except UnicodeDecodeError as exc:
        _fail("INVALID_UTF8", f"{label} is not UTF-8: {exc}")
    except OSError as exc:
        _fail("UNREADABLE_FILE", f"cannot read {label} {selected}: {exc}")
    try:
        document = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_json_constant,
        )
    except PilotContractError:
        raise
    except json.JSONDecodeError as exc:
        _fail("INVALID_JSON", f"cannot parse {label} {selected}: {exc}")
    return document, selected


def load_json_document(
    path: Path | str,
    *,
    label: str,
    archive_root: Path | str | None = None,
) -> tuple[Mapping[str, Any], Path]:
    """Load a strict UTF-8 JSON object from a safe regular file."""

    document, selected = load_json_value(
        path,
        label=label,
        archive_root=archive_root,
    )
    if type(document) is not dict:
        _fail("INVALID_JSON_ROOT", f"{label} must contain a JSON object")
    return document, selected


def compute_json_file_hash(
    path: Path | str,
    *,
    label: str,
    archive_root: Path | str | None = None,
) -> tuple[str, Mapping[str, Any], Path]:
    document, selected = load_json_document(
        path,
        label=label,
        archive_root=archive_root,
    )
    return canonical_json_hash(document), document, selected


def compute_raw_file_hash(
    path: Path | str,
    *,
    label: str = "file",
) -> tuple[str, Path]:
    """Stream the raw bytes of exactly one regular, non-symlink file."""

    selected = _regular_file(path, label=label)
    digest = hashlib.sha256()
    try:
        with selected.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        _fail("UNREADABLE_FILE", f"cannot read {label} {selected}: {exc}")
    return digest.hexdigest(), selected


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if type(value) is not dict:
        _fail("SCHEMA_ERROR", f"{label} must be an object")
    return value


def _exact_keys(
    value: Mapping[str, Any],
    *,
    label: str,
    required: set[str],
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    missing = required - set(value)
    unknown = set(value) - required - optional
    if missing:
        _fail("SCHEMA_ERROR", f"{label} missing fields: {sorted(missing)}")
    if unknown:
        _fail("SCHEMA_ERROR", f"{label} has unknown fields: {sorted(unknown)}")


def _digest(value: Any, label: str) -> str:
    if type(value) is not str or _HEX64.fullmatch(value) is None:
        _fail(
            "SCHEMA_ERROR",
            f"{label} must be 64 lowercase hexadecimal characters",
        )
    return value


def _hash_record(
    hashes: Mapping[str, Any],
    name: str,
    algorithm: str,
    *,
    code_files: tuple[str, ...] | None = None,
) -> str:
    record = _mapping(hashes.get(name), f"hashes.{name}")
    required = {"algorithm", "digest"}
    if code_files is not None:
        required.add("files")
    _exact_keys(record, label=f"hashes.{name}", required=required)
    if record["algorithm"] != algorithm:
        _fail(
            "HASH_ALGORITHM_MISMATCH",
            f"hashes.{name}.algorithm must be {algorithm!r}",
        )
    if code_files is not None:
        if type(record["files"]) is not list or any(
            type(item) is not str for item in record["files"]
        ):
            _fail("SCHEMA_ERROR", "hashes.code.files must be a list of strings")
        recorded_files = tuple(record["files"])
        if recorded_files != code_files:
            _fail(
                "CODE_FILESET_MISMATCH",
                "PILOT_PASS code file list does not equal the current fileset",
            )
    return _digest(record["digest"], f"hashes.{name}.digest")


def _strict_sorted_unique_strings(value: Any, label: str) -> tuple[str, ...]:
    if (
        type(value) is not list
        or not value
        or any(type(item) is not str or not item for item in value)
    ):
        _fail("SCHEMA_ERROR", f"{label} must be a nonempty list of strings")
    result = tuple(value)
    if tuple(sorted(set(result))) != result:
        _fail(
            "SCHEMA_ERROR",
            f"{label} must be sorted and contain no duplicates",
        )
    return result


def candidate_implementation_conformance(
    config: Mapping[str, Any],
) -> tuple[bool, dict[str, Any]]:
    """Validate the hash-bound activation state without launching a full run."""

    candidate = _mapping(
        config.get("candidate_implementation"),
        "candidate_implementation",
    )
    _exact_keys(
        candidate,
        label="candidate_implementation",
        required={
            "status",
            "contract_conformant",
            "activation_permitted",
            "contract_controls",
        },
    )
    controls = _mapping(
        candidate["contract_controls"],
        "candidate_implementation.contract_controls",
    )
    if set(controls) != set(CANDIDATE_CONTRACT_CONTROLS):
        _fail(
            "CANDIDATE_CONTROL_REGISTRY_MISMATCH",
            "candidate implementation controls do not equal the frozen registry",
        )
    if any(type(value) is not bool for value in controls.values()):
        _fail(
            "SCHEMA_ERROR",
            "every candidate implementation control must be boolean",
        )
    enabled = config.get("full_run_enabled")
    if type(enabled) is not bool:
        _fail("SCHEMA_ERROR", "full_run_enabled must be boolean")
    if type(candidate["contract_conformant"]) is not bool or type(
        candidate["activation_permitted"]
    ) is not bool:
        _fail(
            "SCHEMA_ERROR",
            "candidate conformance and activation fields must be boolean",
        )
    enabled_consistent = (
        enabled is True
        and candidate["status"] == "CONTRACT_CONFORMANT_CANDIDATE"
        and candidate["contract_conformant"] is True
        and candidate["activation_permitted"] is True
        and all(controls.values())
    )
    disabled_consistent = (
        enabled is False
        and candidate["status"] == "LEGACY_DISABLED_PENDING_CONTRACT_REWRITE"
        and candidate["contract_conformant"] is False
        and candidate["activation_permitted"] is False
    )
    passed = enabled_consistent or disabled_consistent
    result = {
        "full_run_enabled": enabled,
        "candidate_status": candidate["status"],
        "contract_conformant": candidate["contract_conformant"],
        "activation_permitted": candidate["activation_permitted"],
        "contract_controls_passed": sorted(
            key for key, value in controls.items() if value is True
        ),
        "contract_controls_unmet": sorted(
            key for key, value in controls.items() if value is False
        ),
        "activation_state_consistent": passed,
    }
    return passed, result


def _validate_invariants(
    pilot: Mapping[str, Any],
    expected_ids: tuple[str, ...],
) -> None:
    recorded_required = _strict_sorted_unique_strings(
        pilot["required_invariant_ids"],
        "required_invariant_ids",
    )
    if recorded_required != expected_ids:
        _fail(
            "INVARIANT_REGISTRY_MISMATCH",
            "PILOT_PASS invariant registry does not match the current registry",
        )
    invariants = pilot["invariants"]
    if type(invariants) is not list:
        _fail("SCHEMA_ERROR", "invariants must be a list")
    by_id: dict[str, Mapping[str, Any]] = {}
    for index, raw in enumerate(invariants):
        item = _mapping(raw, f"invariants[{index}]")
        _exact_keys(
            item,
            label=f"invariants[{index}]",
            required={"id", "passed", "result"},
        )
        invariant_id = item["id"]
        if type(invariant_id) is not str or not invariant_id:
            _fail(
                "SCHEMA_ERROR",
                f"invariants[{index}].id must be a nonempty string",
            )
        if invariant_id in by_id:
            _fail(
                "DUPLICATE_INVARIANT",
                f"duplicate invariant result: {invariant_id}",
            )
        if item["passed"] is not True:
            _fail("INVARIANT_FAILED", f"invariant did not pass: {invariant_id}")
        result = _mapping(item["result"], f"invariants[{index}].result")
        if not result:
            _fail("SCHEMA_ERROR", f"invariant result is empty: {invariant_id}")
        canonical_json_bytes(result)
        by_id[invariant_id] = item
    if tuple(sorted(by_id)) != expected_ids:
        missing = sorted(set(expected_ids) - set(by_id))
        extra = sorted(set(by_id) - set(expected_ids))
        _fail(
            "INVARIANT_RESULT_SET_MISMATCH",
            f"invariant result set mismatch; missing={missing}, extra={extra}",
        )


def _validate_golden_sample(
    pilot: Mapping[str, Any],
    *,
    golden_spec: Mapping[str, Any],
    golden_spec_hash: str,
) -> None:
    golden = _mapping(pilot["golden_sample"], "golden_sample")
    _exact_keys(
        golden,
        label="golden_sample",
        required={"categories", "content_sha256"},
    )
    categories = _mapping(golden["categories"], "golden_sample.categories")
    expected = set(REQUIRED_GOLDEN_CATEGORIES)
    if set(categories) != expected:
        _fail(
            "GOLDEN_CATEGORY_MISMATCH",
            "golden sample categories must equal the seven registered categories",
        )
    spec_categories = _mapping(golden_spec.get("categories"), "golden sample spec categories")
    if set(spec_categories) != expected:
        _fail(
            "GOLDEN_SPEC_CATEGORY_MISMATCH",
            "golden sample specification must contain exactly seven categories",
        )
    for category in REQUIRED_GOLDEN_CATEGORIES:
        count = categories[category]
        if type(count) is not int or count < 1:
            _fail(
                "GOLDEN_CATEGORY_EMPTY",
                f"golden sample category must have at least one row: {category}",
            )
        selected_cases = spec_categories[category]
        if type(selected_cases) is not list or any(
            type(case_id) is not str or not case_id for case_id in selected_cases
        ):
            _fail(
                "GOLDEN_SPEC_CATEGORY_INVALID",
                f"golden sample specification category is not a case list: {category}",
            )
        if count != len(selected_cases):
            _fail(
                "GOLDEN_CATEGORY_COUNT_MISMATCH",
                f"receipt count does not match golden specification: {category}",
            )
    recorded_hash = _digest(
        golden["content_sha256"],
        "golden_sample.content_sha256",
    )
    if not hmac.compare_digest(recorded_hash, golden_spec_hash):
        _fail(
            "GOLDEN_SAMPLE_HASH_MISMATCH",
            "receipt does not match the current golden sample specification",
        )


def _validate_raw_trace(pilot: Mapping[str, Any]) -> None:
    trace = _mapping(pilot["raw_trace_inspection"], "raw_trace_inspection")
    _exact_keys(
        trace,
        label="raw_trace_inspection",
        required={"observation_count", "all_reconciled", "artifact_sha256"},
    )
    count = trace["observation_count"]
    if type(count) is not int or count < 20:
        _fail(
            "INSUFFICIENT_RAW_TRACE",
            "raw trace inspection must reconcile at least 20 observations",
        )
    if trace["all_reconciled"] is not True:
        _fail("RAW_TRACE_FAILED", "every inspected raw trace must reconcile")
    _digest(trace["artifact_sha256"], "raw_trace_inspection.artifact_sha256")


def _trace_summary(path: Path) -> tuple[int, bool]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None or len(reader.fieldnames) != len(
                set(reader.fieldnames)
            ):
                _fail(
                    "TRACE_SCHEMA_ERROR",
                    "trace CSV must have a nonempty header with unique columns",
                )
            required = {"final_observation_key", "reconciled"}
            missing = required - set(reader.fieldnames)
            if missing:
                _fail(
                    "TRACE_SCHEMA_ERROR",
                    f"trace CSV missing columns: {sorted(missing)}",
                )
            keys: set[str] = set()
            all_reconciled = True
            rows = 0
            for row in reader:
                rows += 1
                key = (row.get("final_observation_key") or "").strip()
                if not key:
                    _fail(
                        "TRACE_SCHEMA_ERROR",
                        f"trace row {rows} has no final_observation_key",
                    )
                if key in keys:
                    _fail(
                        "TRACE_DUPLICATE_OBSERVATION",
                        f"duplicate final observation in trace CSV: {key}",
                    )
                keys.add(key)
                all_reconciled = all_reconciled and (
                    (row.get("reconciled") or "").strip().lower() == "true"
                )
    except PilotContractError:
        raise
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        _fail("TRACE_READ_ERROR", f"cannot parse trace CSV {path}: {exc}")
    return len(keys), all_reconciled


def _validate_artifacts(
    pilot: Mapping[str, Any],
    pilot_directory: Path,
    *,
    required_artifacts: tuple[str, ...],
    expected_invariants: Sequence[Mapping[str, Any]],
    archive_root: Path | str | None,
) -> None:
    artifacts = _mapping(pilot["artifacts"], "artifacts")
    if tuple(sorted(artifacts)) != required_artifacts:
        _fail(
            "ARTIFACT_REGISTRY_MISMATCH",
            "PILOT_PASS artifacts do not equal the frozen artifact registry",
        )
    required_trace_name = "pilot_raw_trace_inspection.csv"
    selected_artifacts: dict[str, Path] = {}
    for name, raw_record in artifacts.items():
        if (
            type(name) is not str
            or not name
            or "/" in name
            or "\\" in name
            or name in {".", ".."}
        ):
            _fail("INVALID_ARTIFACT_PATH", f"invalid Pilot artifact name: {name!r}")
        record = _mapping(raw_record, f"artifacts.{name}")
        _exact_keys(
            record,
            label=f"artifacts.{name}",
            required={"sha256", "bytes"},
        )
        expected_digest = _digest(record["sha256"], f"artifacts.{name}.sha256")
        expected_size = record["bytes"]
        if type(expected_size) is not int or expected_size < 0:
            _fail("SCHEMA_ERROR", f"artifacts.{name}.bytes must be a nonnegative integer")
        artifact = _regular_file(
            pilot_directory / name,
            label=f"Pilot artifact {name}",
            archive_root=archive_root,
        )
        selected_artifacts[name] = artifact
        if artifact.stat().st_size != expected_size:
            _fail("ARTIFACT_SIZE_MISMATCH", f"Pilot artifact size changed: {name}")
        actual_digest, _ = compute_raw_file_hash(
            artifact,
            label=f"Pilot artifact {name}",
        )
        if not hmac.compare_digest(actual_digest, expected_digest):
            _fail("ARTIFACT_HASH_MISMATCH", f"Pilot artifact changed: {name}")
    trace_digest = artifacts[required_trace_name]["sha256"]
    if not hmac.compare_digest(
        trace_digest,
        pilot["raw_trace_inspection"]["artifact_sha256"],
    ):
        _fail(
            "RAW_TRACE_HASH_MISMATCH",
            "raw trace hash does not match the registered Pilot artifact",
        )
    invariant_value, _ = load_json_value(
        selected_artifacts["pilot_invariants.json"],
        label="Pilot invariant artifact",
        archive_root=archive_root,
    )
    if type(invariant_value) is not list:
        _fail(
            "INVARIANT_ARTIFACT_SCHEMA_ERROR",
            "pilot_invariants.json must contain a JSON array",
        )
    if not hmac.compare_digest(
        canonical_json_bytes(invariant_value),
        canonical_json_bytes(list(expected_invariants)),
    ):
        _fail(
            "INVARIANT_ARTIFACT_MISMATCH",
            "receipt invariant results do not match pilot_invariants.json",
        )
    unique_count, all_reconciled = _trace_summary(
        selected_artifacts[required_trace_name]
    )
    declared_trace = pilot["raw_trace_inspection"]
    if unique_count != declared_trace["observation_count"]:
        _fail(
            "TRACE_COUNT_MISMATCH",
            "receipt trace count does not match unique final observations in CSV",
        )
    if unique_count < 20:
        _fail(
            "INSUFFICIENT_RAW_TRACE",
            "trace CSV must contain at least 20 unique final observations",
        )
    if all_reconciled is not True or declared_trace["all_reconciled"] is not True:
        _fail(
            "RAW_TRACE_FAILED",
            "all trace CSV observations must be reconciled",
        )


def authorize_local_pilot(
    *,
    pilot_pass_path: Path | str,
    code_root: Path | str,
    code_files: Iterable[str],
    config_path: Path | str,
    data_contract_path: Path | str,
    required_invariant_ids: Iterable[str],
    archive_root: Path | str | None,
) -> LocalPilotAuthorization:
    """Validate the Pilot using only files staged outside archive_root."""

    expected_ids = _canonical_relative_paths(
        required_invariant_ids,
        label="required_invariant_ids",
    )
    missing_minimum = set(MINIMUM_REQUIRED_INVARIANT_IDS) - set(expected_ids)
    if missing_minimum:
        _fail(
            "INCOMPLETE_INVARIANT_REGISTRY",
            f"required invariant registry omits: {sorted(missing_minimum)}",
        )

    pilot, selected_pilot = load_json_document(
        pilot_pass_path,
        label="PILOT_PASS.json",
        archive_root=archive_root,
    )
    _exact_keys(
        pilot,
        label="PILOT_PASS.json",
        required={
            "schema_version",
            "status",
            "hashes",
            "required_invariant_ids",
            "invariants",
            "golden_sample",
            "raw_trace_inspection",
            "artifacts",
        },
        optional={
            "created_at_utc",
            "pilot_run_id",
            "runtime_fingerprint",
        },
    )
    if (
        type(pilot["schema_version"]) is not int
        or pilot["schema_version"] != PILOT_SCHEMA_VERSION
    ):
        _fail(
            "SCHEMA_VERSION_MISMATCH",
            f"schema_version must equal {PILOT_SCHEMA_VERSION}",
        )
    if pilot["status"] != "PASS":
        _fail("PILOT_NOT_PASS", "PILOT_PASS status must be exactly 'PASS'")

    current_code_hash, current_code_files = compute_code_fileset_hash(
        code_root,
        code_files,
        archive_root=archive_root,
    )
    current_config_hash, config_document, _ = compute_json_file_hash(
        config_path,
        label="gate configuration",
        archive_root=archive_root,
    )
    current_contract_hash, _, _ = compute_json_file_hash(
        data_contract_path,
        label="data contract",
        archive_root=archive_root,
    )

    hashes = _mapping(pilot["hashes"], "hashes")
    _exact_keys(
        hashes,
        label="hashes",
        required={"code", "config", "data_contract", "manifest"},
    )
    recorded_code_hash = _hash_record(
        hashes,
        "code",
        CODE_HASH_ALGORITHM,
        code_files=current_code_files,
    )
    recorded_config_hash = _hash_record(hashes, "config", JSON_HASH_ALGORITHM)
    recorded_contract_hash = _hash_record(
        hashes,
        "data_contract",
        JSON_HASH_ALGORITHM,
    )
    expected_manifest_hash = _hash_record(
        hashes,
        "manifest",
        RAW_HASH_ALGORITHM,
    )

    if not hmac.compare_digest(recorded_code_hash, current_code_hash):
        _fail("CODE_HASH_MISMATCH", "PILOT_PASS does not match the current code")
    if not hmac.compare_digest(recorded_config_hash, current_config_hash):
        _fail(
            "CONFIG_HASH_MISMATCH",
            "PILOT_PASS does not match the current configuration",
        )
    if not hmac.compare_digest(recorded_contract_hash, current_contract_hash):
        _fail(
            "DATA_CONTRACT_HASH_MISMATCH",
            "PILOT_PASS does not match the current data contract",
        )

    registered_artifacts = _strict_sorted_unique_strings(
        config_document.get("required_pilot_artifacts"),
        "gate configuration required_pilot_artifacts",
    )
    if registered_artifacts != REQUIRED_PILOT_ARTIFACTS:
        _fail(
            "ARTIFACT_REGISTRY_MISMATCH",
            "gate configuration artifact registry is not the frozen registry",
        )
    golden_file = config_document.get("golden_sample_file")
    if type(golden_file) is not str:
        _fail(
            "SCHEMA_ERROR",
            "gate configuration golden_sample_file must be a relative path",
        )
    golden_relative = _canonical_relative_paths(
        [golden_file],
        label="golden_sample_file",
    )[0]
    code_directory = _directory(
        code_root,
        label="code_root",
        archive_root=archive_root,
    )
    golden_hash, golden_spec, _ = compute_json_file_hash(
        code_directory / golden_relative,
        label="golden sample specification",
        archive_root=archive_root,
    )

    _validate_invariants(pilot, expected_ids)
    _validate_golden_sample(
        pilot,
        golden_spec=golden_spec,
        golden_spec_hash=golden_hash,
    )
    _validate_raw_trace(pilot)
    _validate_artifacts(
        pilot,
        selected_pilot.parent,
        required_artifacts=registered_artifacts,
        expected_invariants=pilot["invariants"],
        archive_root=archive_root,
    )
    for optional_object in ("runtime_fingerprint",):
        if optional_object in pilot:
            _mapping(pilot[optional_object], optional_object)

    return LocalPilotAuthorization(
        pilot_pass_path=selected_pilot,
        code_hash=current_code_hash,
        config_hash=current_config_hash,
        data_contract_hash=current_contract_hash,
        expected_manifest_hash=expected_manifest_hash,
        code_files=current_code_files,
        invariant_ids=expected_ids,
        _seal=_AUTHORIZATION_SEAL,
    )


def authorize_manifest(
    local_authorization: LocalPilotAuthorization,
    manifest_path: Path | str,
) -> FullRunAuthorization:
    """Verify the exact raw-byte manifest after local Pilot authorization."""

    if (
        type(local_authorization) is not LocalPilotAuthorization
        or local_authorization._seal is not _AUTHORIZATION_SEAL
    ):
        _fail(
            "LOCAL_AUTHORIZATION_REQUIRED",
            "manifest access requires a valid local Pilot authorization",
        )
    actual_manifest_hash, selected_manifest = compute_raw_file_hash(
        manifest_path,
        label="canonical archive manifest",
    )
    if not hmac.compare_digest(
        actual_manifest_hash,
        local_authorization.expected_manifest_hash,
    ):
        _fail(
            "MANIFEST_HASH_MISMATCH",
            "canonical archive manifest does not match PILOT_PASS",
        )
    return FullRunAuthorization(
        local=local_authorization,
        manifest_path=selected_manifest,
        manifest_hash=actual_manifest_hash,
        _seal=_AUTHORIZATION_SEAL,
    )


def authorize_full_run(
    *,
    pilot_pass_path: Path | str,
    code_root: Path | str,
    code_files: Iterable[str],
    config_path: Path | str,
    data_contract_path: Path | str,
    required_invariant_ids: Iterable[str],
    archive_root: Path | str | None,
    manifest_path: Path | str,
) -> FullRunAuthorization:
    """Authorize a full run, guaranteeing local checks precede manifest I/O."""

    local = authorize_local_pilot(
        pilot_pass_path=pilot_pass_path,
        code_root=code_root,
        code_files=code_files,
        config_path=config_path,
        data_contract_path=data_contract_path,
        required_invariant_ids=required_invariant_ids,
        archive_root=archive_root,
    )
    return authorize_manifest(local, manifest_path)


__all__ = [
    "CODE_HASH_ALGORITHM",
    "CANDIDATE_CONTRACT_CONTROLS",
    "EXIT_DATA_CONTRACT",
    "FullRunAuthorization",
    "JSON_HASH_ALGORITHM",
    "LocalPilotAuthorization",
    "MINIMUM_REQUIRED_INVARIANT_IDS",
    "PILOT_SCHEMA_VERSION",
    "PilotContractError",
    "RAW_HASH_ALGORITHM",
    "REQUIRED_GOLDEN_CATEGORIES",
    "REQUIRED_PILOT_ARTIFACTS",
    "authorize_full_run",
    "authorize_local_pilot",
    "authorize_manifest",
    "candidate_implementation_conformance",
    "canonical_json_bytes",
    "canonical_json_hash",
    "compute_code_fileset_hash",
    "compute_json_file_hash",
    "compute_raw_file_hash",
    "load_json_document",
    "load_json_value",
    "require_regular_file",
]
