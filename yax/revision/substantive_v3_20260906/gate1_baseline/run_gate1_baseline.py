#!/usr/bin/env python3
"""Run the V3 Gate-1 BASE-03 reconstruction under its canonical contract.

This wrapper does not implement or tune the estimator.  It authenticates the
declared contract, inputs, code, reference dependencies, and SCC runtime;
invokes the existing R3 BASE-03 program once; invokes its existing self-check;
and only then compares fresh artifacts with the frozen contract and the
authenticated R3 diagnostic checkpoints.

Resolved paths are execution-only information.  The persisted logs and V3
receipt contain placeholders, hashes, and basenames, never private paths.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import subprocess
import sys
import traceback
from typing import Any, Iterable


V3_REL = Path("yax/revision/substantive_v3_20260906")
SPEC_REL = V3_REL / "contracts/specs/canonical_baseline_reproduction_v2.json"
SPEC_TOOL_REL = V3_REL / "scripts/spec_contract.py"
R3_REL = Path("yax/revision/substantive_r3_20260905")
RUNNER_REL = R3_REL / "rebuilt_baseline/run_rebuilt_corrected_baseline.py"
SELFCHECK_REL = R3_REL / "rebuilt_baseline/selfcheck.py"
REFERENCE_REL = R3_REL / "rebuilt_baseline/results"
ENVIRONMENT_REL = R3_REL / "ENVIRONMENT_LOCK.txt"
TRANSITIVE_LOCK_REL = V3_REL / "gate1_baseline/TRANSITIVE_CODE_LOCK.json"

REPO_SOURCE_PATHS = {
    "cps_occupation_exposure_lookup": Path("yax/measurement/CPS_OCCUPATION_EXPOSURE_LOOKUP.csv"),
    "computerization_measures_census2018": Path("yax/measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv"),
    "rule_b_values_census2018": Path("yax/measurement/RULE_B_VALUES_CENSUS2018.csv"),
    "census_occ2010_to_2018_bridge": Path("yax/measurement/CENSUS_OCC2010_TO_2018_BRIDGE.csv"),
    "first_post_outcome_access_receipt": Path("yax/analysis/FIRST_OUTCOME_ACCESS_RECEIPT.json"),
}
PRIVATE_SOURCE_ARGUMENTS = {
    "ipums_cps_extract_9_wide": "microdata",
    "ipums_cps_extract_11_march_basic_repair": "repair_microdata",
    "historical_preperiod_cells": "historical_preperiod_cells",
}
DEPENDENCY_ROLE_PATHS = {
    "reference rebuilt fixed-membership vector for checkpoint comparison":
        Path("REBUILT_TREATMENT_MEMBERSHIP.csv"),
    "R3 prefit gate reference": Path("PREFIT_GATE.json"),
}
CHECKPOINT_ROWS = (
    "historical_108_historical_treatment",
    "corrected_113_historical_treatment",
    "corrected_113_recomputed_preperiod_treatment",
)
CHECKPOINT_FIELDS = (
    "coefficient",
    "analytic_cluster_se",
    "bootstrap_se",
    "ci_lower",
    "ci_upper",
    "bootstrap_p_value",
)
FLOAT_ABS_TOL = 1e-10
FLOAT_REL_TOL = 1e-10
CUT_ABS_TOL = 1e-12
RECEIPT_SCHEMA = "yax-v3-empirical-run-receipt-v1"
EXPECTED_SPEC_ID = "yaxspec_v1_83bb387f9fc28e2655db5101c7697989510475027d1dd5a9c361c797ed3925c3"
EXPECTED_SPEC_SHA256 = "34b8a785a267d334643b04d3ff35f47bf30780068e126e0a63dd14b0079c5e8b"
EXPECTED_TRANSITIVE_LOCK_SHA256 = "b4fdbca971ff398d5563aa2972c2bda7d8eb8863351da81e71a41753b568197d"
EXPECTED_SPEC_TOOL_SHA256 = "de2b607202e4b93b3d712e0f930f13d2da00cee7c4696ccf2fec9dc1e46cdcc8"
EXPECTED_REFERENCE_RECEIPT_SHA256 = "e3379ea442fa36d92fbc652f7a4a28b66fdef12c3e6c21a2462d1a7765574d21"
EXPECTED_REFERENCE_SELFCHECK_SHA256 = "3c1f6ee3b86499cb573cab829efefc6cea48fbfc04a32479e4b28fb75abaa26b"
WRAPPER_COMMAND_TEMPLATE = (
    "<YAX_PYTHON_BIN> yax/revision/substantive_v3_20260906/gate1_baseline/"
    "run_gate1_baseline.py --repo-root <YAX_REPO_ROOT> --python-bin <YAX_PYTHON_BIN> "
    "--microdata <INPUT:ipums_cps_extract_9_wide> "
    "--repair-microdata <INPUT:ipums_cps_extract_11_march_basic_repair> "
    "--historical-preperiod-cells <INPUT:historical_preperiod_cells> "
    "--output-dir <YAX_V3_RUN_ROOT>/gate1_baseline/results "
    "--audit-dir <YAX_V3_RUN_ROOT>/gate1_baseline/audit"
)


class Gate1Error(RuntimeError):
    """A fail-closed Gate-1 validation or execution failure."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            raise Gate1Error(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(
            stream,
            object_pairs_hook=_unique_pairs,
            parse_constant=lambda value: (_ for _ in ()).throw(
                Gate1Error(f"invalid JSON numeric constant: {value}")
            ),
        )


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise Gate1Error(f"missing required {label}")


def require_new_or_empty(path: Path, label: str, create: bool = False) -> None:
    if path.exists() and not path.is_dir():
        raise Gate1Error(f"{label} exists and is not a directory")
    if path.is_dir() and any(path.iterdir()):
        raise Gate1Error(f"refusing nonempty {label}")
    if create:
        path.mkdir(parents=True, exist_ok=True)


def reserve_new_directory(path: Path, label: str) -> None:
    """Atomically reserve a run leaf; even a pre-existing empty leaf is refused."""
    try:
        path.mkdir(parents=True, exist_ok=False)
    except FileExistsError as exc:
        raise Gate1Error(f"refusing pre-existing {label}; use a unique new run path") from exc


def path_is_within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise Gate1Error(f"cannot load required module {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_and_validate_contract(repo: Path, spec_path: Path) -> dict[str, Any]:
    """Validate the canonical JSON and recompute its immutable spec identifier."""
    require_file(spec_path, "canonical specification")
    tool_path = repo / SPEC_TOOL_REL
    require_file(tool_path, "specification validator")
    if sha256_file(tool_path) != EXPECTED_SPEC_TOOL_SHA256:
        raise Gate1Error("specification validator differs from the pre-results implementation lock")
    tool = _load_module("yax_v3_spec_contract_gate1", tool_path)
    try:
        value = tool.load_json(spec_path)
        tool.validate_spec(value, require_id=True)
    except Exception as exc:  # preserve the validator's fail-closed semantics
        raise Gate1Error(f"canonical specification validation failed: {exc}") from exc
    if value.get("spec_id") != EXPECTED_SPEC_ID:
        raise Gate1Error("wrapper refuses a substituted or restamped canonical specification")
    if sha256_file(spec_path) != EXPECTED_SPEC_SHA256:
        raise Gate1Error("canonical specification byte hash differs from the pre-results lock")
    return value


def support_hash(codes: Iterable[str]) -> str:
    payload = "".join(f"{str(code).zfill(4)}\n" for code in sorted(str(code).zfill(4) for code in codes))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def output_hashes(directory: Path) -> dict[str, str]:
    return {
        path.name: sha256_file(path)
        for path in sorted(directory.iterdir())
        if path.is_file()
    }


def verify_result_bundle(directory: Path, label: str) -> dict[str, Any]:
    """Authenticate one BASE-03 bundle from its runner receipt and self-check."""
    receipt_path = directory / "EXECUTION_RECEIPT.json"
    selfcheck_path = directory / "SELF_CHECK.json"
    require_file(receipt_path, f"{label} BASE-03 receipt")
    require_file(selfcheck_path, f"{label} BASE-03 self-check")
    receipt = load_json(receipt_path)
    selfcheck = load_json(selfcheck_path)
    expected = receipt.get("output_hashes")
    if not isinstance(expected, dict) or not expected:
        raise Gate1Error(f"{label} receipt has no output hash manifest")
    forbidden = sorted({"EXECUTION_RECEIPT.json", "SELF_CHECK.json"}.intersection(expected))
    if forbidden:
        raise Gate1Error(f"{label} receipt has circular output hashes: {forbidden}")
    failures: dict[str, dict[str, str]] = {}
    for name, expected_hash in expected.items():
        if Path(name).name != name or not re.fullmatch(r"[0-9a-f]{64}", str(expected_hash)):
            raise Gate1Error(f"{label} receipt contains an invalid output-manifest entry")
        path = directory / name
        if not path.is_file():
            failures[name] = {"observed": "MISSING", "expected": str(expected_hash)}
            continue
        observed = sha256_file(path)
        if observed != expected_hash:
            failures[name] = {"observed": observed, "expected": str(expected_hash)}
    if failures:
        raise Gate1Error(f"{label} output authentication failed: {json.dumps(failures, sort_keys=True)}")
    checks = selfcheck.get("checks")
    if selfcheck.get("status") != "PASS_BASE_03_SELF_CHECK" or not isinstance(checks, dict):
        raise Gate1Error(f"{label} self-check does not report PASS_BASE_03_SELF_CHECK")
    failed_checks = sorted(name for name, passed in checks.items() if passed is not True)
    if failed_checks:
        raise Gate1Error(f"{label} self-check contains failures: {failed_checks}")
    if selfcheck.get("verified_output_hashes") != expected:
        raise Gate1Error(f"{label} self-check hash manifest differs from its runner receipt")
    return {
        "receipt": receipt,
        "receipt_sha256": sha256_file(receipt_path),
        "selfcheck_sha256": sha256_file(selfcheck_path),
        "manifest": expected,
    }


def authenticate_dependencies(
    contract: dict[str, Any], reference_dir: Path,
) -> dict[str, dict[str, str]]:
    """Hash declared reference dependencies without reading checkpoint values."""
    dependencies = contract.get("dependencies", [])
    observed: dict[str, dict[str, str]] = {}
    seen_roles: set[str] = set()
    for dependency in dependencies:
        role = dependency["role"]
        if role in seen_roles:
            raise Gate1Error(f"duplicate declared dependency role: {role}")
        if role not in DEPENDENCY_ROLE_PATHS:
            raise Gate1Error(f"no authenticated path mapping for declared dependency role: {role}")
        path = reference_dir / DEPENDENCY_ROLE_PATHS[role]
        require_file(path, f"dependency {role}")
        digest = sha256_file(path)
        if digest != dependency["artifact_sha256"]:
            raise Gate1Error(f"declared dependency hash mismatch for role: {role}")
        observed[role] = {"sha256": digest, "status": "AUTHENTICATED"}
        seen_roles.add(role)
    missing_roles = sorted(set(DEPENDENCY_ROLE_PATHS) - seen_roles)
    if missing_roles:
        raise Gate1Error(f"canonical contract omitted required baseline dependencies: {missing_roles}")
    return observed


def authenticate_reference_bundle(
    contract: dict[str, Any], reference_dir: Path, expected_source_commit: str,
) -> dict[str, Any]:
    """Authenticate the full R3 bundle only after the fresh self-check passes."""
    receipt_path = reference_dir / "EXECUTION_RECEIPT.json"
    selfcheck_path = reference_dir / "SELF_CHECK.json"
    require_file(receipt_path, "pinned reference BASE-03 receipt")
    require_file(selfcheck_path, "pinned reference BASE-03 self-check")
    if sha256_file(receipt_path) != EXPECTED_REFERENCE_RECEIPT_SHA256:
        raise Gate1Error("reference BASE-03 receipt differs from the pinned checkpoint bundle")
    if sha256_file(selfcheck_path) != EXPECTED_REFERENCE_SELFCHECK_SHA256:
        raise Gate1Error("reference BASE-03 self-check differs from the pinned checkpoint bundle")
    authenticated = verify_result_bundle(reference_dir, "reference")
    receipt = authenticated["receipt"]
    if receipt.get("script_sha256") != contract["execution"]["code_sha256"]:
        raise Gate1Error("reference BASE-03 receipt was produced by code outside the canonical contract")
    if receipt.get("git_head") != expected_source_commit:
        raise Gate1Error("reference BASE-03 git head differs from the transitive-code source commit")
    return {
        "reference_receipt_sha256": authenticated["receipt_sha256"],
        "reference_selfcheck_sha256": authenticated["selfcheck_sha256"],
        "reference_output_manifest_authenticated": True,
        "reference_source_commit": expected_source_commit,
        "reference_receipt": receipt,
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
            raise Gate1Error(f"environment lock does not expose required SCC field: {key}")
        result[key] = match.group(1).strip()
    return result


RUNTIME_PROBE = r"""
import importlib.metadata
import json
import platform
import sys
import numpy
import pandas
libc_name, libc_version = platform.libc_ver()
print(json.dumps({
  "python": platform.python_version(),
  "python_compiler": platform.python_compiler(),
  "numpy": numpy.__version__,
  "pandas": pandas.__version__,
  "pytest": importlib.metadata.version("pytest"),
  "kernel_system": platform.system(),
  "kernel_release": platform.release(),
  "machine": platform.machine(),
  "libc_name": libc_name,
  "libc": libc_version,
}, sort_keys=True))
"""


def authenticate_runtime(python_bin: str, lock_path: Path, expected_hash: str) -> dict[str, Any]:
    require_file(lock_path, "execution environment lock")
    digest = sha256_file(lock_path)
    if digest != expected_hash:
        raise Gate1Error("execution environment lock hash differs from canonical contract")
    expected = parse_scc_environment_lock(lock_path.read_text(encoding="utf-8"))
    completed = subprocess.run(
        [python_bin, "-c", RUNTIME_PROBE], text=True, capture_output=True, check=False,
    )
    if completed.returncode != 0:
        raise Gate1Error("unable to probe the declared Python execution environment")
    try:
        observed = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise Gate1Error("Python runtime probe did not return valid JSON") from exc
    comparable = {
        "python": observed.get("python"),
        "python_compiler": observed.get("python_compiler"),
        "numpy": observed.get("numpy"),
        "pandas": observed.get("pandas"),
        "pytest": observed.get("pytest"),
        "kernel_system": observed.get("kernel_system"),
        "kernel_release": observed.get("kernel_release"),
        "machine": observed.get("machine"),
        "libc": observed.get("libc"),
    }
    mismatches = {
        key: {"observed": comparable.get(key), "expected": value}
        for key, value in expected.items()
        if key != "kernel_release" and comparable.get(key) != value
    }
    # The lock writes the architecture as a separate field, while Linux's
    # platform.release() appends the same architecture to this kernel build.
    # Treat only that duplicated suffix as a formatting normalization.
    kernel_observed = comparable.get("kernel_release")
    kernel_expected = expected["kernel_release"]
    accepted_kernel_forms = {kernel_expected, f"{kernel_expected}.{expected['machine']}"}
    if kernel_observed not in accepted_kernel_forms:
        mismatches["kernel_release"] = {
            "observed": kernel_observed, "expected": sorted(accepted_kernel_forms),
        }
    if observed.get("libc_name") != "glibc":
        mismatches["libc_name"] = {"observed": observed.get("libc_name"), "expected": "glibc"}
    if mismatches:
        raise Gate1Error(f"runtime differs from authenticated SCC environment lock: {json.dumps(mismatches, sort_keys=True)}")
    return {
        "environment_lock_sha256": digest,
        "runtime": observed,
        "kernel_release_comparison": {
            "lock": kernel_expected,
            "runtime": kernel_observed,
            "rule": "allow only duplicate dot-machine suffix already declared separately",
        },
        "status": "AUTHENTICATED_DECLARED_RUNTIME",
    }


def authenticate_declared_sources(
    contract: dict[str, Any], repo: Path, args: argparse.Namespace,
) -> dict[str, dict[str, str]]:
    sources = contract["data"]["sources"]
    expected_ids = {source["source_id"] for source in sources}
    mapped_ids = set(REPO_SOURCE_PATHS) | set(PRIVATE_SOURCE_ARGUMENTS)
    if expected_ids != mapped_ids:
        raise Gate1Error(
            "declared source mapping is incomplete or stale: "
            + json.dumps({"declared_only": sorted(expected_ids - mapped_ids),
                          "mapped_only": sorted(mapped_ids - expected_ids)})
        )
    expected = {source["source_id"]: source["sha256"] for source in sources}
    paths: dict[str, Path] = {
        source_id: repo / relative for source_id, relative in REPO_SOURCE_PATHS.items()
    }
    for source_id, argument in PRIVATE_SOURCE_ARGUMENTS.items():
        paths[source_id] = Path(getattr(args, argument))

    # Repository and authorization artifacts are checked before restricted
    # microdata.  A stale analysis checkout therefore fails without reading
    # the licensed files.
    order = list(REPO_SOURCE_PATHS) + list(PRIVATE_SOURCE_ARGUMENTS)
    result: dict[str, dict[str, str]] = {}
    for source_id in order:
        path = paths[source_id]
        require_file(path, f"declared source {source_id}")
        digest = sha256_file(path)
        if digest != expected[source_id]:
            raise Gate1Error(f"declared source hash mismatch: {source_id}")
        result[source_id] = {"sha256": digest, "status": "AUTHENTICATED"}
    return result


def git_blob_sha256(repo: Path, commit: str, path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"], cwd=repo, capture_output=True, check=False,
    )
    if completed.returncode != 0:
        raise Gate1Error(f"transitive code path is absent from authenticated source commit: {path}")
    return hashlib.sha256(completed.stdout).hexdigest()


def authenticate_code(repo: Path, contract: dict[str, Any]) -> dict[str, Any]:
    runner = repo / RUNNER_REL
    selfcheck = repo / SELFCHECK_REL
    analysis_spec = repo / R3_REL / "rebuilt_baseline/ANALYSIS_SPEC.md"
    for path, label in ((runner, "BASE-03 runner"), (selfcheck, "BASE-03 self-check"),
                        (analysis_spec, "BASE-03 analysis specification")):
        require_file(path, label)
    runner_hash = sha256_file(runner)
    if runner_hash != contract["execution"]["code_sha256"]:
        raise Gate1Error("BASE-03 runner code hash differs from canonical contract")
    lock_path = repo / TRANSITIVE_LOCK_REL
    require_file(lock_path, "Gate-1 transitive code lock")
    if sha256_file(lock_path) != EXPECTED_TRANSITIVE_LOCK_SHA256:
        raise Gate1Error("Gate-1 transitive code lock differs from the pre-results wrapper lock")
    lock = load_json(lock_path)
    if lock.get("schema_version") != "yax-gate1-transitive-code-lock-v1":
        raise Gate1Error("unrecognized Gate-1 transitive code-lock schema")
    source_commit = lock.get("source_commit")
    if not isinstance(source_commit, str) or not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise Gate1Error("invalid source commit in Gate-1 transitive code lock")
    files = lock.get("files")
    if not isinstance(files, dict) or not files:
        raise Gate1Error("Gate-1 transitive code lock has no files")
    transitive: dict[str, dict[str, str]] = {}
    for relative, expected in files.items():
        path = repo / relative
        require_file(path, f"transitive code {relative}")
        working_hash = sha256_file(path)
        commit_hash = git_blob_sha256(repo, source_commit, relative)
        if working_hash != expected or commit_hash != expected:
            raise Gate1Error(f"transitive code authentication failed: {relative}")
        transitive[relative] = {
            "sha256": expected,
            "source_commit": source_commit,
            "status": "AUTHENTICATED_TO_REFERENCE_SOURCE_COMMIT",
        }
    companions = lock.get("companion_files")
    if not isinstance(companions, dict) or not companions:
        raise Gate1Error("Gate-1 transitive code lock has no companion files")
    companion_receipt: dict[str, dict[str, str]] = {}
    for relative, expected in companions.items():
        path = repo / relative
        require_file(path, f"BASE-03 companion {relative}")
        observed = sha256_file(path)
        if observed != expected:
            raise Gate1Error(f"BASE-03 companion-code authentication failed: {relative}")
        companion_receipt[relative] = {"sha256": observed, "status": "AUTHENTICATED"}
    return {
        "runner_sha256": runner_hash,
        "selfcheck_sha256": sha256_file(selfcheck),
        "analysis_spec_sha256": sha256_file(analysis_spec),
        "specification_validator_sha256": sha256_file(repo / SPEC_TOOL_REL),
        "transitive_code_lock_sha256": sha256_file(lock_path),
        "transitive_source_commit": source_commit,
        "transitive_imports": transitive,
        "companion_files": companion_receipt,
        "status": "AUTHENTICATED",
    }


def authenticate_command_input(
    historical_preperiod_cells: Path, first_access_receipt: Path,
) -> dict[str, str]:
    require_file(historical_preperiod_cells, "historical preperiod cells")
    require_file(first_access_receipt, "authenticated first-access receipt")
    authorization = load_json(first_access_receipt)
    expected = authorization.get("preperiod_cells_sha256")
    if not isinstance(expected, str):
        raise Gate1Error("first-access receipt does not authenticate historical preperiod cells")
    digest = sha256_file(historical_preperiod_cells)
    if digest != expected:
        raise Gate1Error("historical preperiod-cell hash mismatch")
    return {"sha256": digest, "status": "AUTHENTICATED_SUPPLEMENTAL_COMMAND_INPUT"}


def values_close(left: float, right: float, *, atol: float = FLOAT_ABS_TOL) -> bool:
    return math.isclose(float(left), float(right), rel_tol=FLOAT_REL_TOL, abs_tol=atol)


def _compare_float(label: str, observed: Any, expected: Any, failures: list[str], *, atol: float = FLOAT_ABS_TOL) -> None:
    try:
        passed = values_close(float(observed), float(expected), atol=atol)
    except (TypeError, ValueError):
        passed = False
    if not passed:
        failures.append(f"{label}: observed={observed!r}, expected={expected!r}")


def compare_fresh_outputs(
    contract: dict[str, Any], fresh: Path, reference: Path,
) -> dict[str, Any]:
    """Compare outputs after estimation; this function never invokes a model."""
    failures: list[str] = []
    fresh_membership = fresh / "REBUILT_TREATMENT_MEMBERSHIP.csv"
    fresh_norm = fresh / "REBUILT_NORMALIZATION_AND_CUTS.json"
    fresh_calendar = fresh / "CALENDAR_RECEIPT.json"
    fresh_models = fresh / "BASELINE_DECOMPOSITION.csv"
    fresh_failures = fresh / "MODEL_FAILURES.json"
    for path in (fresh_membership, fresh_norm, fresh_calendar, fresh_models, fresh_failures):
        require_file(path, f"fresh checkpoint {path.name}")

    members = csv_rows(fresh_membership)
    codes = [row["occupation_code"].zfill(4) for row in members]
    observed_support_hash = support_hash(codes)
    norm = load_json(fresh_norm)
    calendar = load_json(fresh_calendar)
    ref_norm = load_json(reference / "REBUILT_NORMALIZATION_AND_CUTS.json")
    ref_calendar = load_json(reference / "CALENDAR_RECEIPT.json")
    model_rows = csv_rows(fresh_models)
    ref_model_rows = csv_rows(reference / "BASELINE_DECOMPOSITION.csv")
    models = {row["row_id"]: row for row in model_rows}
    ref_models = {row["row_id"]: row for row in ref_model_rows}
    if len(models) != len(model_rows) or len(ref_models) != len(ref_model_rows):
        failures.append("fresh or reference checkpoint table contains duplicate row_id values")
    if set(models) != set(ref_models):
        failures.append("fresh checkpoint row set differs from authenticated reference")

    expected_membership_sha = contract["exposure"]["fixed_membership"]["sha256"]
    membership_sha = sha256_file(fresh_membership)
    if membership_sha != expected_membership_sha:
        failures.append("fresh fixed-membership file hash differs from canonical contract")
    expected_count = int(contract["occupation"]["analysis_subset"]["occupation_count"])
    if len(members) != expected_count or len(set(codes)) != expected_count:
        failures.append(
            f"fresh membership count/uniqueness differs: rows={len(members)}, "
            f"unique={len(set(codes))}, expected={expected_count}"
        )
    expected_support_hash = contract["occupation"]["universe"]["content_support_sha256"]
    if observed_support_hash != expected_support_hash:
        failures.append("fresh occupation support hash differs from canonical contract")
    if norm.get("support_hash_sha256") != expected_support_hash:
        failures.append("fresh normalization support hash differs from canonical contract")
    if int(norm.get("support_occupations", -1)) != expected_count:
        failures.append("fresh normalization occupation count differs from canonical contract")

    observed_months = calendar.get("all_observed_months", [])
    observed_contract = contract["calendar"]["observed_window"]
    estimation_contract = contract["calendar"]["estimation_window"]
    if len(observed_months) != int(observed_contract["observed_month_count"]):
        failures.append("fresh observed-month count differs from canonical contract")
    if not observed_months or [observed_months[0], observed_months[-1]] != observed_contract["range"]:
        failures.append("fresh observed-month range differs from canonical contract")
    if observed_months != ref_calendar.get("all_observed_months"):
        failures.append("fresh observed-month sequence differs from authenticated reference")
    if calendar.get("corrected_static_month_count") != estimation_contract["included_month_count"]:
        failures.append("fresh static-month count differs from canonical contract")
    if not observed_months or [observed_months[0], observed_months[-1]] != estimation_contract["range"]:
        failures.append("fresh estimation-month range differs from canonical contract")
    transition = contract["calendar"]["transition_handling"]
    if transition["static_models"] == "exclude 2022-12" and not calendar.get("december_2022_excluded_static"):
        failures.append("fresh calendar did not exclude the declared static transition month")
    missing = contract["calendar"]["missing_handling"]["missing_months"]
    for month in missing:
        if month in observed_months:
            failures.append(f"declared missing month appears in fresh observed calendar: {month}")
    if calendar.get("october_2025_interpolated") is not False:
        failures.append("fresh calendar interpolated or did not explicitly reject interpolation of 2025-10")

    exposure = contract["exposure"]
    if norm.get("construction_start") != exposure["construction_weights"]["window"][0]:
        failures.append("fresh exposure construction start differs from canonical contract")
    if norm.get("construction_end") != exposure["construction_weights"]["window"][1]:
        failures.append("fresh exposure construction end differs from canonical contract")
    if norm.get("construction_months") != 71:
        failures.append("fresh exposure construction does not contain 71 preperiod months")
    if norm.get("no_postperiod_stock_used") is not True or float(norm.get("postperiod_stock_used", math.nan)) != 0.0:
        failures.append("fresh exposure construction used or did not account for postperiod stock")
    observed_cuts = norm.get("beta_quintile_cuts", [])
    expected_cuts = exposure["cutoffs"]
    if len(observed_cuts) != len(expected_cuts):
        failures.append("fresh quintile-cut vector has the wrong length")
    else:
        for index, (observed, expected) in enumerate(zip(observed_cuts, expected_cuts), start=1):
            _compare_float(f"beta cut {index}", observed, expected, failures, atol=CUT_ABS_TOL)
    webb = exposure["webb_normalization"]
    _compare_float("Webb weighted mean", norm.get("webb_weighted_mean"), webb["mean"], failures)
    _compare_float("Webb weighted SD", norm.get("webb_weighted_sd"), webb["sd"], failures)
    for field in ("beta_weighted_mean", "beta_weighted_sd", "total_preperiod_stock"):
        _compare_float(field, norm.get(field), ref_norm.get(field), failures)

    checkpoint_report: dict[str, Any] = {}
    for row_id in CHECKPOINT_ROWS:
        if row_id not in models or row_id not in ref_models:
            failures.append(f"checkpoint row missing: {row_id}")
            continue
        observed_row = models[row_id]
        reference_row = ref_models[row_id]
        row_report: dict[str, Any] = {}
        for field in CHECKPOINT_FIELDS:
            _compare_float(f"{row_id}.{field}", observed_row.get(field), reference_row.get(field), failures)
            row_report[field] = {
                "fresh": float(observed_row[field]),
                "reference": float(reference_row[field]),
            }
        for field in ("support_hash_sha256", "months", "first_month", "last_month"):
            if observed_row.get(field) != reference_row.get(field):
                failures.append(f"{row_id}.{field} differs from authenticated reference")
        row_report["support_hash_sha256"] = observed_row.get("support_hash_sha256")
        row_report["months"] = int(observed_row["months"])
        checkpoint_report[row_id] = row_report

    recorded_failures = load_json(fresh_failures)
    if recorded_failures != []:
        failures.append("BASE-03 MODEL_FAILURES.json is nonempty")
    if failures:
        raise Gate1Error("fresh checkpoint comparison failed: " + " | ".join(failures))
    return {
        "status": "PASS_POST_RUN_CHECKPOINT_COMPARISON",
        "comparison_order": "runner_exit_then_selfcheck_then_checkpoint_comparison",
        "no_estimator_retuning_or_retry": True,
        "membership": {
            "file_sha256": membership_sha,
            "occupation_count": len(members),
            "support_hash_sha256": observed_support_hash,
        },
        "calendar": {
            "observed_month_count": len(observed_months),
            "static_month_count": calendar["corrected_static_month_count"],
            "first_month": observed_months[0],
            "last_month": observed_months[-1],
            "december_2022_excluded": calendar["december_2022_excluded_static"],
            "october_2025_missing_not_interpolated":
                calendar["october_2025_missing"] and not calendar["october_2025_interpolated"],
        },
        "normalization": {
            "construction_start": norm["construction_start"],
            "construction_end": norm["construction_end"],
            "construction_months": norm["construction_months"],
            "beta_quintile_cuts": norm["beta_quintile_cuts"],
            "beta_weighted_mean": norm["beta_weighted_mean"],
            "beta_weighted_sd": norm["beta_weighted_sd"],
            "webb_weighted_mean": norm["webb_weighted_mean"],
            "webb_weighted_sd": norm["webb_weighted_sd"],
            "total_preperiod_stock": norm["total_preperiod_stock"],
        },
        "checkpoints": checkpoint_report,
    }


def validate_fresh_execution_receipt(
    contract: dict[str, Any], output_dir: Path, source_auth: dict[str, dict[str, str]],
    preperiod_auth: dict[str, str], code_auth: dict[str, Any],
) -> dict[str, Any]:
    receipt = load_json(output_dir / "EXECUTION_RECEIPT.json")
    failures: list[str] = []
    if receipt.get("script_sha256") != code_auth["runner_sha256"]:
        failures.append("fresh receipt runner hash differs from authenticated code")
    if receipt.get("analysis_spec_sha256") != code_auth["analysis_spec_sha256"]:
        failures.append("fresh receipt analysis-spec hash differs from authenticated code")
    runner_inputs = receipt.get("input_hashes", {})
    source_to_runner = {
        "ipums_cps_extract_9_wide": "microdata",
        "ipums_cps_extract_11_march_basic_repair": "repair_microdata",
        "cps_occupation_exposure_lookup": "lookup",
        "computerization_measures_census2018": "computerization",
        "rule_b_values_census2018": "rule_b_values",
        "census_occ2010_to_2018_bridge": "bridge",
    }
    for source_id, runner_key in source_to_runner.items():
        if runner_inputs.get(runner_key) != source_auth[source_id]["sha256"]:
            failures.append(f"fresh receipt input hash differs: {source_id}")
    if runner_inputs.get("historical_preperiod_cells") != preperiod_auth["sha256"]:
        failures.append("fresh receipt historical preperiod-cell hash differs")
    bootstrap = receipt.get("bootstrap", {})
    multipliers = contract["uncertainty"]["multiplier_matrix"]
    if bootstrap.get("draws") != multipliers["draws"]:
        failures.append("fresh receipt bootstrap draw count differs from contract")
    if bootstrap.get("seed") != multipliers["seed"]:
        failures.append("fresh receipt bootstrap seed differs from contract")
    if bootstrap.get("common_multipliers_only_on_exact_common_support") is not True:
        failures.append("fresh receipt does not preserve declared common multipliers")
    for row in receipt.get("model_rows", []):
        if row.get("draws") != multipliers["draws"] or row.get("seed") != multipliers["seed"]:
            failures.append(f"fresh model row has undeclared draw/seed: {row.get('row_id')}")
    for row in receipt.get("paired_comparisons", []):
        if (row.get("draws") != multipliers["draws"] or row.get("seed") != multipliers["seed"]
                or row.get("common_multipliers") is not True):
            failures.append(f"fresh paired row violates common-draw contract: {row.get('contrast')}")
    if failures:
        raise Gate1Error("fresh execution-receipt integrity failed: " + " | ".join(failures))
    return {
        "status": "PASS_FRESH_EXECUTION_RECEIPT_INTEGRITY",
        "git_head": receipt.get("git_head"),
        "runner_sha256": receipt["script_sha256"],
        "analysis_spec_sha256": receipt["analysis_spec_sha256"],
        "input_hashes_authenticated": True,
        "draws": bootstrap["draws"],
        "seed": bootstrap["seed"],
        "common_draw_semantics_authenticated": True,
    }


def compute_checkpoint_result_ids(
    repo: Path, contract: dict[str, Any], output_dir: Path,
) -> dict[str, str]:
    tool_path = repo / SPEC_TOOL_REL
    if sha256_file(tool_path) != EXPECTED_SPEC_TOOL_SHA256:
        raise Gate1Error("specification validator changed during Gate-1 execution")
    tool = _load_module("yax_v3_spec_contract_gate1_result_ids", tool_path)
    artifact_hash = sha256_file(output_dir / "BASELINE_DECOMPOSITION.csv")
    return {
        row_id: tool.compute_result_id(
            contract["spec_id"],
            f"gate1_baseline.{row_id}.coefficient",
            artifact_hash,
            json.dumps(checkpoint_selector(row_id), sort_keys=True, separators=(",", ":")),
        )
        for row_id in CHECKPOINT_ROWS
    }


def checkpoint_selector(row_id: str) -> dict[str, Any]:
    """Return the canonical result-ledger selector for one checkpoint."""
    if row_id not in CHECKPOINT_ROWS:
        raise Gate1Error(f"unknown checkpoint row for result selector: {row_id}")
    return {
        "kind": "csv_key",
        "keys": {"row_id": row_id},
        "column": "coefficient",
    }


def git_state(repo: Path) -> dict[str, Any]:
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"], cwd=repo, text=True,
    )
    return {
        "head": head,
        "worktree_clean": not bool(status),
        "porcelain_status_sha256": hashlib.sha256(status.encode("utf-8")).hexdigest(),
        "status_entry_count": len(status.splitlines()),
    }


def redaction_map(args: argparse.Namespace, repo: Path) -> dict[str, str]:
    candidates = {
        str(repo.resolve()): "<YAX_REPO_ROOT>",
        str(Path(args.microdata).resolve()): "<INPUT:ipums_cps_extract_9_wide>",
        str(Path(args.repair_microdata).resolve()): "<INPUT:ipums_cps_extract_11_march_basic_repair>",
        str(Path(args.historical_preperiod_cells).resolve()): "<INPUT:historical_preperiod_cells>",
        str(Path(args.output_dir).resolve()): "<YAX_V3_RUN_ROOT>/gate1_baseline/results",
        str(Path(args.audit_dir).resolve()): "<YAX_V3_RUN_ROOT>/gate1_baseline/audit",
    }
    python_path = Path(args.python_bin)
    if python_path.is_absolute():
        candidates[str(python_path.resolve())] = "<YAX_PYTHON_BIN>"
    return dict(sorted(candidates.items(), key=lambda item: len(item[0]), reverse=True))


SECRET_PATTERNS = (
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"ghp_[A-Za-z0-9]+"),
    re.compile(r"(?i)(api[_ -]?key|password|token)\s*[:=]\s*[^\s,;]+"),
    re.compile(r"https?://[^/@\s]+@"),
)


def sanitize_text(value: str, replacements: dict[str, str]) -> str:
    result = value
    for literal, placeholder in replacements.items():
        result = result.replace(literal, placeholder)
    result = re.sub(r"/(?:project|projectnb)/[^\s'\"\]\[{}(),;]+", "<REDACTED_SCC_PATH>", result)
    result = re.sub(r"/usr3/graduate/[^\s'\"\]\[{}(),;]+", "<REDACTED_SCC_USER_PATH>", result)
    result = re.sub(r"/Users/[^\s'\"\]\[{}(),;]+", "<REDACTED_LOCAL_PATH>", result)
    for pattern in SECRET_PATTERNS:
        result = pattern.sub("<REDACTED_SECRET>", result)
    return result


def sanitize_value(value: Any, replacements: dict[str, str]) -> Any:
    if isinstance(value, str):
        return sanitize_text(value, replacements)
    if isinstance(value, list):
        return [sanitize_value(item, replacements) for item in value]
    if isinstance(value, dict):
        return {key: sanitize_value(item, replacements) for key, item in value.items()}
    return value


def assert_public_artifact(value: Any) -> None:
    serialized = json.dumps(value, sort_keys=True)
    forbidden = [
        r"/project/", r"/projectnb/", r"/Users/", r"/usr3/", r"github_pat_", r"ghp_",
    ]
    hits = [token for token in forbidden if token in serialized]
    if hits:
        raise Gate1Error(f"refusing receipt containing private path or credential markers: {hits}")


def run_subprocess(
    command: list[str], cwd: Path, stdout_path: Path, stderr_path: Path,
    replacements: dict[str, str],
) -> dict[str, Any]:
    started = utc_now()
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False)
    ended = utc_now()
    stdout_path.write_text(sanitize_text(completed.stdout, replacements), encoding="utf-8")
    stderr_path.write_text(sanitize_text(completed.stderr, replacements), encoding="utf-8")
    return {
        "started_at_utc": started,
        "ended_at_utc": ended,
        "exit_code": completed.returncode,
        "stdout_file": stdout_path.name,
        "stdout_sha256": sha256_file(stdout_path),
        "stderr_file": stderr_path.name,
        "stderr_sha256": sha256_file(stderr_path),
    }


def build_runner_command(args: argparse.Namespace, repo: Path) -> list[str]:
    return [
        args.python_bin,
        str(repo / RUNNER_REL),
        "--repo-root", str(repo),
        "--microdata", str(Path(args.microdata)),
        "--repair-microdata", str(Path(args.repair_microdata)),
        "--historical-preperiod-cells", str(Path(args.historical_preperiod_cells)),
        "--lookup", str(repo / REPO_SOURCE_PATHS["cps_occupation_exposure_lookup"]),
        "--computerization", str(repo / REPO_SOURCE_PATHS["computerization_measures_census2018"]),
        "--rule-b-values", str(repo / REPO_SOURCE_PATHS["rule_b_values_census2018"]),
        "--bridge", str(repo / REPO_SOURCE_PATHS["census_occ2010_to_2018_bridge"]),
        "--first-access-receipt", str(repo / REPO_SOURCE_PATHS["first_post_outcome_access_receipt"]),
        "--output-dir", str(Path(args.output_dir)),
    ]


def execute(args: argparse.Namespace) -> int:
    repo = Path(args.repo_root).resolve()
    # Resolve caller-relative execution paths before subprocesses change cwd.
    args.microdata = Path(args.microdata).resolve()
    args.repair_microdata = Path(args.repair_microdata).resolve()
    args.historical_preperiod_cells = Path(args.historical_preperiod_cells).resolve()
    args.output_dir = Path(args.output_dir).resolve()
    args.audit_dir = Path(args.audit_dir).resolve()
    spec_path = Path(args.spec).resolve() if args.spec else repo / SPEC_REL
    reference_dir = Path(args.reference_results).resolve() if args.reference_results else repo / REFERENCE_REL
    output_dir = args.output_dir
    audit_dir = args.audit_dir
    if output_dir == audit_dir or output_dir in audit_dir.parents or audit_dir in output_dir.parents:
        raise Gate1Error("result and wrapper-audit directories must be disjoint")
    if path_is_within(audit_dir, repo):
        raise Gate1Error("wrapper-audit directory must be outside the repository")
    reserve_new_directory(audit_dir, "wrapper-audit directory")
    replacements = redaction_map(args, repo)
    log_paths = {
        name: audit_dir / name for name in (
            "runner.stdout.log", "runner.stderr.log", "selfcheck.stdout.log",
            "selfcheck.stderr.log", "wrapper.stderr.log",
        )
    }
    for path in log_paths.values():
        path.write_text("", encoding="utf-8")

    started = utc_now()
    receipt: dict[str, Any] = {
        "schema_version": RECEIPT_SCHEMA,
        "record": "YAX V3 Gate-1 canonical BASE-03 reconstruction",
        "analysis_status": "post-outcome referee-led diagnostic; checkpoint reproduction, not a confirmatory result",
        "started_at_utc": started,
        "status": "RUNNING",
        "exit_code": None,
        "spec_id": None,
        "failures": [],
        "private_paths_or_credentials_persisted": False,
    }
    failures: list[dict[str, str]] = []
    exit_code = 1
    try:
        # Atomic reservation precedes all protected-input hashing and prevents
        # concurrent jobs from interleaving into one output leaf.
        if path_is_within(output_dir, repo):
            raise Gate1Error("BASE-03 result directory must be outside the repository")
        reserve_new_directory(output_dir, "BASE-03 result directory")
        contract = load_and_validate_contract(repo, spec_path)
        receipt["spec_id"] = contract["spec_id"]
        receipt["specification_sha256"] = sha256_file(spec_path)
        receipt["wrapper_code_sha256"] = sha256_file(Path(__file__))
        receipt["command_template"] = contract["execution"]["command"]
        receipt["wrapper_command_template"] = WRAPPER_COMMAND_TEMPLATE
        receipt["repository"] = git_state(repo)

        code_auth = authenticate_code(repo, contract)
        dependency_auth = authenticate_dependencies(contract, reference_dir)
        environment_auth = authenticate_runtime(
            args.python_bin, repo / ENVIRONMENT_REL,
            contract["execution"]["environment_sha256"],
        )
        source_auth = authenticate_declared_sources(contract, repo, args)
        preperiod_auth = authenticate_command_input(
            Path(args.historical_preperiod_cells),
            repo / REPO_SOURCE_PATHS["first_post_outcome_access_receipt"],
        )
        receipt["authentication"] = {
            "code": code_auth,
            "environment": environment_auth,
            "declared_sources": source_auth,
            "historical_preperiod_cross_authentication": {
                "historical_preperiod_cells": preperiod_auth
            },
            "dependencies": dependency_auth,
            "reference": {"status": "NOT_READ_BEFORE_FRESH_RUN"},
            "status": "PASS_ALL_PRE_RUN_AUTHENTICATION",
        }

        runner_record = run_subprocess(
            build_runner_command(args, repo), repo,
            log_paths["runner.stdout.log"], log_paths["runner.stderr.log"], replacements,
        )
        receipt["runner"] = runner_record
        if runner_record["exit_code"] != 0:
            raise Gate1Error(f"BASE-03 runner exited {runner_record['exit_code']}")

        selfcheck_record = run_subprocess(
            [args.python_bin, str(repo / SELFCHECK_REL), "--output-dir", str(output_dir)],
            repo, log_paths["selfcheck.stdout.log"], log_paths["selfcheck.stderr.log"], replacements,
        )
        receipt["selfcheck"] = selfcheck_record
        if selfcheck_record["exit_code"] != 0:
            raise Gate1Error(f"BASE-03 self-check exited {selfcheck_record['exit_code']}")

        fresh_auth = verify_result_bundle(output_dir, "fresh")
        reference_auth = authenticate_reference_bundle(
            contract, reference_dir, code_auth["transitive_source_commit"],
        )
        fresh_receipt_integrity = validate_fresh_execution_receipt(
            contract, output_dir, source_auth, preperiod_auth, code_auth,
        )
        checkpoint = compare_fresh_outputs(contract, output_dir, reference_dir)
        receipt["fresh_bundle_authentication"] = {
            "runner_receipt_sha256": fresh_auth["receipt_sha256"],
            "selfcheck_sha256": fresh_auth["selfcheck_sha256"],
            "runner_output_manifest_authenticated": True,
            "execution_receipt_integrity": fresh_receipt_integrity,
        }
        receipt["authentication"]["reference"] = {
            "receipt_sha256": reference_auth["reference_receipt_sha256"],
            "selfcheck_sha256": reference_auth["reference_selfcheck_sha256"],
            "output_manifest_authenticated": True,
            "read_only_after_fresh_selfcheck": True,
        }
        receipt["checkpoint_comparison"] = checkpoint
        receipt["result_ids"] = compute_checkpoint_result_ids(repo, contract, output_dir)
        receipt["result_selectors"] = {
            row_id: checkpoint_selector(row_id) for row_id in CHECKPOINT_ROWS
        }
        receipt["result_id"] = receipt["result_ids"][
            "corrected_113_recomputed_preperiod_treatment"
        ]
        receipt["output_hashes"] = output_hashes(output_dir)
        receipt["status"] = "PASS_GATE1_CANONICAL_BASELINE_RECONSTRUCTION"
        receipt["exit_code"] = 0
        exit_code = 0
    except Exception as exc:
        message = sanitize_text(str(exc), replacements)
        failures.append({
            "exception_type": type(exc).__name__,
            "message": message,
            "recorded_at_utc": utc_now(),
        })
        log_paths["wrapper.stderr.log"].write_text(
            sanitize_text(traceback.format_exc(), replacements), encoding="utf-8",
        )
        receipt["status"] = "FAIL_GATE1_CANONICAL_BASELINE_RECONSTRUCTION"
        receipt["exit_code"] = 1
        receipt["failures"] = failures
    finally:
        receipt["ended_at_utc"] = utc_now()
        if output_dir.is_dir():
            observed_hashes = output_hashes(output_dir)
            if receipt["exit_code"] == 0:
                receipt["output_hashes"] = observed_hashes
            else:
                receipt["observed_result_directory_hashes_at_failure"] = observed_hashes
        write_json(audit_dir / "WRAPPER_FAILURES.json", failures)
        for path in log_paths.values():
            # Apply the sanitizer a second time after every process has exited,
            # then fail rather than knowingly retain a recognized private
            # marker in a transferable audit log.
            path.write_text(
                sanitize_text(path.read_text(encoding="utf-8"), replacements),
                encoding="utf-8",
            )
            assert_public_artifact({"log": path.read_text(encoding="utf-8")})
        assert_public_artifact(failures)
        receipt["audit_artifact_hashes"] = {
            path.name: sha256_file(path)
            for path in sorted(log_paths.values())
        }
        receipt["audit_artifact_hashes"]["WRAPPER_FAILURES.json"] = sha256_file(
            audit_dir / "WRAPPER_FAILURES.json"
        )
        safe_receipt = sanitize_value(receipt, replacements)
        assert_public_artifact(safe_receipt)
        write_json(audit_dir / "V3_EXECUTION_RECEIPT.json", safe_receipt)
        print(json.dumps({
            "status": safe_receipt["status"],
            "spec_id": safe_receipt.get("spec_id"),
            "exit_code": safe_receipt["exit_code"],
            "audit_artifacts": [
                "V3_EXECUTION_RECEIPT.json", "WRAPPER_FAILURES.json",
                "runner.stdout.log", "runner.stderr.log",
                "selfcheck.stdout.log", "selfcheck.stderr.log", "wrapper.stderr.log",
            ],
        }, indent=2, sort_keys=True))
    return exit_code


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo-root", type=Path, required=True)
    value.add_argument("--spec", type=Path)
    value.add_argument("--reference-results", type=Path)
    value.add_argument("--python-bin", default=sys.executable)
    value.add_argument("--microdata", type=Path, required=True)
    value.add_argument("--repair-microdata", type=Path, required=True)
    value.add_argument("--historical-preperiod-cells", type=Path, required=True)
    value.add_argument("--output-dir", type=Path, required=True)
    value.add_argument("--audit-dir", type=Path, required=True)
    return value


if __name__ == "__main__":
    sys.exit(execute(parser().parse_args()))
