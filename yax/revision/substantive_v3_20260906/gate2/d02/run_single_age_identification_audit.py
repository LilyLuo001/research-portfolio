#!/usr/bin/env python3
"""Outcome-free identification audit for the Gate 2 D02 single-age design.

The authoritative invocation consumes only frozen specification and membership
metadata.  It never accepts an outcome or row-level-data argument.  The central
proof uses a bijection between panel rows and occupation-by-month indicator
pivots; it never materializes the 52,884 by 52,884 saturated design matrix.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import tempfile
from typing import Any, Sequence

import numpy as np


SPEC_SCHEMA = "yax-gate2-d02-identification-spec-v1"
AUDIT_SCHEMA = "yax-gate2-d02-identification-audit-v1"
RECEIPT_SCHEMA = "yax-gate2-d02-identification-receipt-v1"
SPEC_PREFIX = "yaxgate2d02spec_v1_"
RESULT_PREFIX = "yaxresult_v1_"
RECEIPT_PREFIX = "yaxgate2d02receipt_v1_"
AUDIT_FILENAME = "SINGLE_AGE_IDENTIFICATION_AUDIT.json"
RECEIPT_FILENAME = "EXECUTION_RECEIPT.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_RE = re.compile(r"^gate2_d02_[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")

REQUIRED_MEMBERSHIP_COLUMNS = (
    "occupation_code",
    "occupation_name",
    "preperiod_weight",
    "rule_A_beta",
    "beta_quintile",
    "webb_pct_software",
    "webb_z",
    "beta_tied_at_cut",
)
EXPOSURE_COLUMNS = (
    "q2_post",
    "q3_post",
    "q4_post",
    "q5_post",
    "webb_z_post",
)


class D02AuditError(RuntimeError):
    """A fail-closed D02 contract or authentication failure."""


def _reject_nonfinite(value: Any, path: str = "$") -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise D02AuditError(f"non-finite value at {path}")
    if isinstance(value, dict):
        for key, child in value.items():
            _reject_nonfinite(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_nonfinite(child, f"{path}[{index}]")


def canonical_bytes(value: Any) -> bytes:
    _reject_nonfinite(value)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> Any:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise D02AuditError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    with path.open("r", encoding="utf-8") as stream:
        return json.load(
            stream,
            object_pairs_hook=unique_object,
            parse_constant=lambda token: (_ for _ in ()).throw(
                D02AuditError(f"invalid JSON number: {token}")
            ),
        )


def compute_spec_id(spec: dict[str, Any]) -> str:
    payload = dict(spec)
    payload.pop("spec_id", None)
    return SPEC_PREFIX + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def compute_result_id(spec_id: str, logical_filename: str, artifact_sha256: str) -> str:
    _require_prefixed_digest(spec_id, SPEC_PREFIX, "spec_id")
    _require_digest(artifact_sha256, "artifact_sha256")
    if not logical_filename or Path(logical_filename).name != logical_filename:
        raise D02AuditError("logical filename must be a nonempty basename")
    payload = {
        "artifact_sha256": artifact_sha256,
        "logical_filename": logical_filename,
        "spec_id": spec_id,
    }
    return RESULT_PREFIX + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def compute_receipt_id(receipt: dict[str, Any]) -> str:
    payload = dict(receipt)
    payload.pop("receipt_id", None)
    return RECEIPT_PREFIX + hashlib.sha256(canonical_bytes(payload)).hexdigest()


def _require_digest(value: Any, label: str) -> None:
    if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
        raise D02AuditError(f"{label} must be a lowercase SHA-256 digest")


def _require_prefixed_digest(value: Any, prefix: str, label: str) -> None:
    if not isinstance(value, str) or not value.startswith(prefix):
        raise D02AuditError(f"{label} has the wrong prefix")
    _require_digest(value[len(prefix):], label)


def validate_spec(spec: Any, code_path: Path | None = None) -> dict[str, Any]:
    if not isinstance(spec, dict) or spec.get("schema_version") != SPEC_SCHEMA:
        raise D02AuditError("wrong or missing D02 specification schema")
    _require_prefixed_digest(spec.get("spec_id"), SPEC_PREFIX, "spec_id")
    if spec["spec_id"] != compute_spec_id(spec):
        raise D02AuditError("D02 spec_id mismatch")
    if spec.get("execution_state") != "PRE_RESULTS_FROZEN_NOT_EXECUTED":
        raise D02AuditError("specification is not marked pre-results and unexecuted")

    expected_inputs = {
        "canonical_spec",
        "membership",
        "support_accounting_spec",
        "support_accounting_receipt",
        "support_accounting_validation",
    }
    authenticated = spec.get("authenticated_inputs")
    if not isinstance(authenticated, dict) or set(authenticated) != expected_inputs:
        raise D02AuditError("authenticated input inventory differs")
    for key, entry in authenticated.items():
        if not isinstance(entry, dict):
            raise D02AuditError(f"authenticated_inputs.{key} must be an object")
        _require_digest(entry.get("sha256"), f"authenticated_inputs.{key}.sha256")

    calendar = spec.get("calendar", {})
    months = calendar.get("exact_estimation_months")
    if not isinstance(months, list) or len(months) != 113 or len(set(months)) != 113:
        raise D02AuditError("specification must serialize 113 unique estimation months")
    if calendar.get("expected_estimation_month_count") != len(months):
        raise D02AuditError("expected estimation month count differs from serialized calendar")
    month_digest = hashlib.sha256(canonical_bytes(months)).hexdigest()
    if month_digest != calendar.get("exact_estimation_months_sha256"):
        raise D02AuditError("serialized estimation calendar digest mismatch")
    design = spec.get("design", {})
    if tuple(design.get("exposure_post_columns", ())) != EXPOSURE_COLUMNS:
        raise D02AuditError("declared exposure-by-post columns differ")
    if design.get("post_definition") != (
        "1 for 2023-01 through 2026-07 among included months and 0 otherwise"
    ):
        raise D02AuditError("declared post definition differs from runner behavior")
    if design.get("q1_normalization") != (
        "Q1-by-post is omitted; q2_post through q5_post are relative to Q1."
    ):
        raise D02AuditError("declared Q1 normalization differs from runner behavior")
    membership = spec.get("membership", {})
    if membership.get("expected_occupation_count") != 468:
        raise D02AuditError("expected occupation count must be 468")
    if membership.get("expected_panel_row_count") != 468 * len(months):
        raise D02AuditError("expected panel row count differs from occupation-month product")
    proof = spec.get("proof_contract", {})
    if proof.get("dense_saturated_matrix_permitted") is not False:
        raise D02AuditError("dense saturated matrix must be forbidden")
    if proof.get("fixture_materialization_limit") != 64:
        raise D02AuditError("fixture materialization limit differs from runner behavior")
    if spec.get("interpretation", {}).get("age_coefficient_additivity") != (
        "Separate age-specific coefficients need not add to the nonlinear grouped-binomial headline."
    ):
        raise D02AuditError("required non-additivity interpretation is absent")
    execution = spec.get("execution", {})
    if execution.get("authoritative_output_executed_at_spec_freeze") is not False:
        raise D02AuditError("specification must remain unexecuted at freeze")
    if execution.get("atomic_new_leaf") is not True or execution.get("overwrite_existing_leaf") is not False:
        raise D02AuditError("output leaf policy differs from runner behavior")
    outputs = spec.get("outputs", {})
    if tuple(outputs.get("files", ())) != (AUDIT_FILENAME, RECEIPT_FILENAME):
        raise D02AuditError("declared output inventory differs from runner behavior")
    if outputs.get("audit_schema_version") != AUDIT_SCHEMA:
        raise D02AuditError("declared audit schema differs from runner behavior")
    if outputs.get("receipt_schema_version") != RECEIPT_SCHEMA:
        raise D02AuditError("declared receipt schema differs from runner behavior")
    code_hash = execution.get("code_sha256")
    _require_digest(code_hash, "execution.code_sha256")
    if code_path is not None and sha256_file(code_path) != code_hash:
        raise D02AuditError("runner SHA-256 differs from the frozen specification")
    return spec


def inclusive_months(start: str, end: str) -> list[str]:
    match_start = re.fullmatch(r"(\d{4})-(\d{2})", start)
    match_end = re.fullmatch(r"(\d{4})-(\d{2})", end)
    if match_start is None or match_end is None:
        raise D02AuditError("calendar endpoints must use YYYY-MM")
    year, month = map(int, match_start.groups())
    end_year, end_month = map(int, match_end.groups())
    if not 1 <= month <= 12 or not 1 <= end_month <= 12:
        raise D02AuditError("calendar endpoint month is invalid")
    result: list[str] = []
    while (year, month) <= (end_year, end_month):
        result.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            year += 1
            month = 1
    if not result:
        raise D02AuditError("calendar range is reversed")
    return result


def authenticate_calendar(
    spec: dict[str, Any], canonical: dict[str, Any], support_spec: dict[str, Any]
) -> list[str]:
    canonical_calendar = canonical.get("calendar", {})
    estimation = canonical_calendar.get("estimation_window", {})
    start, end = estimation.get("range", [None, None])
    missing = canonical_calendar.get("missing_handling", {}).get("missing_months")
    static_rule = canonical_calendar.get("transition_handling", {}).get("static_models")
    transition = support_spec.get("calendar", {}).get("transition_month")
    if estimation.get("included_month_count") != 113:
        raise D02AuditError("canonical static month count is not 113")
    if missing != ["2025-10"] or static_rule != "exclude 2022-12":
        raise D02AuditError("canonical missing/transition rule differs")
    if transition != "2022-12":
        raise D02AuditError("support-accounting transition month differs")
    expected = [month for month in inclusive_months(start, end) if month not in {transition, *missing}]
    if expected != spec["calendar"]["exact_estimation_months"]:
        raise D02AuditError("canonical and serialized exact calendars differ")

    support_calendar = support_spec.get("calendar", {})
    observed = [
        month
        for month in inclusive_months(*support_calendar.get("observed_window", [None, None]))
        if month not in set(support_calendar.get("missing_months", []))
    ]
    if len(observed) != 114 or [month for month in observed if month != transition] != expected:
        raise D02AuditError("support-accounting and static estimation calendars differ")
    return expected


def read_and_authenticate_membership(path: Path, spec: dict[str, Any]) -> list[dict[str, Any]]:
    if sha256_file(path) != spec["authenticated_inputs"]["membership"]["sha256"]:
        raise D02AuditError("membership SHA-256 differs")
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if tuple(reader.fieldnames or ()) != REQUIRED_MEMBERSHIP_COLUMNS:
            raise D02AuditError("membership columns or column order differ")
        raw_rows = list(reader)
    if len(raw_rows) != spec["membership"]["expected_occupation_count"]:
        raise D02AuditError("membership row count differs")

    rows: list[dict[str, Any]] = []
    codes: list[str] = []
    for index, row in enumerate(raw_rows):
        code = row["occupation_code"]
        if not re.fullmatch(r"\d{4}", code):
            raise D02AuditError(f"invalid occupation code at membership row {index + 2}")
        try:
            quintile = int(row["beta_quintile"])
            beta = float(row["rule_A_beta"])
            webb_z = float(row["webb_z"])
            weight = float(row["preperiod_weight"])
        except ValueError as exc:
            raise D02AuditError(f"non-numeric membership field at row {index + 2}") from exc
        if quintile not in range(1, 6) or not all(map(math.isfinite, (beta, webb_z, weight))):
            raise D02AuditError(f"invalid membership value at row {index + 2}")
        if weight <= 0:
            raise D02AuditError(f"nonpositive membership weight at row {index + 2}")
        codes.append(code)
        rows.append({"occupation_code": code, "beta_quintile": quintile, "webb_z": webb_z})
    if len(set(codes)) != len(codes):
        raise D02AuditError("membership contains duplicate occupation codes")
    if codes != sorted(codes):
        raise D02AuditError("membership occupation order is not canonical ascending order")
    code_digest = hashlib.sha256(canonical_bytes(codes)).hexdigest()
    if code_digest != spec["membership"]["ordered_occupation_codes_sha256"]:
        raise D02AuditError("ordered occupation membership digest differs")
    return rows


def authenticate_inputs(
    spec: dict[str, Any],
    canonical_path: Path,
    membership_path: Path,
    support_spec_path: Path,
    support_receipt_path: Path,
    support_validation_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str], dict[str, str]]:
    paths = {
        "canonical_spec": canonical_path,
        "membership": membership_path,
        "support_accounting_spec": support_spec_path,
        "support_accounting_receipt": support_receipt_path,
        "support_accounting_validation": support_validation_path,
    }
    actual_hashes = {key: sha256_file(path) for key, path in paths.items()}
    for key, actual in actual_hashes.items():
        if actual != spec["authenticated_inputs"][key]["sha256"]:
            raise D02AuditError(f"{key} SHA-256 differs")

    canonical = load_json(canonical_path)
    support_spec = load_json(support_spec_path)
    support_receipt = load_json(support_receipt_path)
    support_validation = load_json(support_validation_path)
    binding = spec["upstream_binding"]
    if canonical.get("spec_id") != binding["canonical_spec_id"]:
        raise D02AuditError("canonical spec_id differs")
    if support_spec.get("spec_id") != binding["support_accounting_spec_id"]:
        raise D02AuditError("support-accounting spec_id differs")
    if support_receipt.get("spec_id") != support_spec.get("spec_id"):
        raise D02AuditError("support receipt is not bound to its specification")
    if support_receipt.get("spec_sha256") != actual_hashes["support_accounting_spec"]:
        raise D02AuditError("support receipt records a different specification hash")
    if support_receipt.get("status") != binding["support_accounting_receipt_status"]:
        raise D02AuditError("support receipt status differs")
    if support_receipt.get("occupation_count") != 468:
        raise D02AuditError("support receipt occupation count differs")
    if support_receipt.get("authenticated_inputs", {}).get("membership", {}).get("sha256") != actual_hashes["membership"]:
        raise D02AuditError("support receipt authenticates a different membership")
    if support_validation.get("status") != binding["support_accounting_validation_status"]:
        raise D02AuditError("support validation status differs")
    if support_validation.get("execution_receipt_sha256") != actual_hashes["support_accounting_receipt"]:
        raise D02AuditError("support validation authenticates a different receipt")

    months = authenticate_calendar(spec, canonical, support_spec)
    membership = read_and_authenticate_membership(membership_path, spec)
    return canonical, membership, months, actual_hashes


def row_pivot_mapping(
    occupation_codes: Sequence[str], months: Sequence[str]
) -> tuple[list[tuple[str, str]], dict[tuple[str, str], int]]:
    if not occupation_codes or len(set(occupation_codes)) != len(occupation_codes):
        raise D02AuditError("occupation keys must be nonempty and unique")
    if not months or len(set(months)) != len(months):
        raise D02AuditError("month keys must be nonempty and unique")
    rows = [(occupation, month) for occupation in occupation_codes for month in months]
    pivots = {key: index for index, key in enumerate(rows)}
    if len(pivots) != len(rows):
        raise D02AuditError("occupation-month keys do not map bijectively to pivots")
    return rows, pivots


def exposure_matrix(membership: Sequence[dict[str, Any]], months: Sequence[str]) -> np.ndarray:
    values = np.empty((len(membership) * len(months), len(EXPOSURE_COLUMNS)), dtype=float)
    row = 0
    for occupation in membership:
        profile = [float(occupation["beta_quintile"] == q) for q in range(2, 6)]
        profile.append(float(occupation["webb_z"]))
        for month in months:
            post = float(month >= "2023-01")
            values[row, :] = np.asarray(profile) * post
            row += 1
    if not np.isfinite(values).all():
        raise D02AuditError("non-finite exposure-by-post value")
    return values


def companion_additive_geometry(
    membership: Sequence[dict[str, Any]], months: Sequence[str]
) -> dict[str, Any]:
    occupation_features = np.asarray(
        [
            [*(float(row["beta_quintile"] == q) for q in range(2, 6)), float(row["webb_z"])]
            for row in membership
        ],
        dtype=float,
    )
    post = np.asarray([float(month >= "2023-01") for month in months])
    centered_features = occupation_features - occupation_features.mean(axis=0)
    centered_post = post - post.mean()
    singular_values = np.linalg.svd(centered_features, compute_uv=False)
    tolerance = max(centered_features.shape) * np.finfo(float).eps * singular_values[0]
    rank = int(np.sum(singular_values > tolerance))
    if not np.any(centered_post) or rank != len(EXPOSURE_COLUMNS):
        raise D02AuditError("possible additive occupation-plus-month companion lacks full target rank")
    # On the complete balanced panel, double-demeaning e_o * post_t gives
    # (e_o - mean(e)) * (post_t - mean(post)); only the small 468 x 5 feature
    # matrix is needed to establish target rank.
    return {
        "nuisance": "additive occupation fixed effects plus additive calendar-month fixed effects",
        "residual_formula": "(exposure_o - mean_o exposure) * (post_t - mean_t post)",
        "target_column_count": len(EXPOSURE_COLUMNS),
        "residual_target_rank": rank,
        "rank_tolerance": float(tolerance),
        "occupation_feature_singular_values": [float(value) for value in singular_values],
        "status": "PASS_POSSIBLE_COMPANION_TARGET_COLUMNS_NOT_ABSORBED",
        "limit": "This outcome-free rank check does not estimate, validate, or equate age-specific coefficients.",
    }


def saturated_absorption_proof(
    membership: Sequence[dict[str, Any]], months: Sequence[str]
) -> dict[str, Any]:
    occupations = [row["occupation_code"] for row in membership]
    rows, pivots = row_pivot_mapping(occupations, months)
    expected_rows = len(occupations) * len(months)
    if len(rows) != expected_rows or set(pivots.values()) != set(range(expected_rows)):
        raise D02AuditError("row-to-pivot map is not a permutation")
    row_key_digest = hashlib.sha256(
        canonical_bytes([[occupation, month] for occupation, month in rows])
    ).hexdigest()
    # X is intentionally only n by 5.  The saturated Z is characterized by
    # the pivot map and is never allocated as an n by n object.
    x = exposure_matrix(membership, months)
    if x.shape != (expected_rows, len(EXPOSURE_COLUMNS)):
        raise D02AuditError("exposure matrix dimensions differ")
    return {
        "status": "PASS_EXACT_SATURATED_ABSORPTION",
        "observation_count": expected_rows,
        "saturated_indicator_column_count": expected_rows,
        "saturated_indicator_rank": expected_rows,
        "augmented_rank": expected_rows,
        "exposure_post_column_count": len(EXPOSURE_COLUMNS),
        "exposure_post_columns": list(EXPOSURE_COLUMNS),
        "row_pivot_bijection": True,
        "row_pivot_mapping_sha256": row_key_digest,
        "saturated_matrix_nnz_implied": expected_rows,
        "dense_saturated_matrix_constructed": False,
        "factorization": "X = Z B, where B[pivot(o,t),k] = X[(o,t),k]",
        "residual_identity": "M_Z X = X - Z(Z'Z)^(-1)Z'X = 0",
        "residual_max_abs": 0,
        "rank_identity": "rank([Z,X]) = rank(Z)",
        "proof_basis": (
            "Each single-age occupation-month observation has its own unrestricted "
            "occupation-by-month indicator and a unique pivot. Thus Z is a row/column "
            "permutation of the identity, spans R^n, and absorbs every possible row-level "
            "column, including every declared exposure-by-post column."
        ),
    }


def materialize_fixture_designs(
    row_keys: Sequence[tuple[str, str]], x: np.ndarray, *, maximum_rows: int = 64
) -> tuple[np.ndarray, Any]:
    """Materialize dense/sparse saturated Z only for deliberately tiny tests."""
    if len(row_keys) == 0 or len(row_keys) > maximum_rows:
        raise D02AuditError("fixture materialization is limited to small nonempty panels")
    if len(set(row_keys)) != len(row_keys) or x.shape[0] != len(row_keys):
        raise D02AuditError("fixture rows must be unique and conformable with X")
    from scipy import sparse

    indices = np.arange(len(row_keys))
    dense = np.zeros((len(row_keys), len(row_keys)), dtype=float)
    dense[indices, indices] = 1.0
    sparse_z = sparse.csr_matrix(
        (np.ones(len(row_keys)), (indices, indices)), shape=dense.shape
    )
    return dense, sparse_z


def build_audit(
    spec: dict[str, Any],
    membership: Sequence[dict[str, Any]],
    months: Sequence[str],
    authenticated_hashes: dict[str, str],
) -> dict[str, Any]:
    proof = saturated_absorption_proof(membership, months)
    companion = companion_additive_geometry(membership, months)
    return {
        "schema_version": AUDIT_SCHEMA,
        "status": "PASS_D02_SINGLE_AGE_IDENTIFICATION_AUDIT",
        "spec_id": spec["spec_id"],
        "authenticated_inputs": {
            key: {"sha256": value} for key, value in sorted(authenticated_hashes.items())
        },
        "protected_outcomes_opened": False,
        "row_level_data_opened": False,
        "coefficient_estimated": False,
        "calendar_authentication": {
            "estimation_month_count": len(months),
            "exact_estimation_months_sha256": hashlib.sha256(canonical_bytes(list(months))).hexdigest(),
            "first_month": months[0],
            "last_month": months[-1],
            "excluded_transition_month": "2022-12",
            "genuinely_missing_month": "2025-10",
        },
        "membership_authentication": {
            "occupation_count": len(membership),
            "ordered_occupation_codes_sha256": hashlib.sha256(
                canonical_bytes([row["occupation_code"] for row in membership])
            ).hexdigest(),
        },
        "invalid_saturated_single_age_model": {
            "nuisance": "unrestricted occupation-by-calendar-month indicators",
            "disposition": "INVALID_TARGET_NOT_IDENTIFIED",
            "reason": "the nuisance spans every single-age occupation-month row",
            "proof": proof,
        },
        "possible_separate_age_companion": companion,
        "interpretation": {
            "headline": "nonlinear jointly estimated grouped-binomial conditional-mean stock-ratio contrast",
            "companion": "separate age-specific log-stock projection with a distinct additive occupation-plus-month nuisance space",
            "additivity": "Separate age-specific coefficients need not add to the nonlinear grouped-binomial headline.",
            "claimed_coefficient_identity": False,
        },
    }


def _write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def execute(args: argparse.Namespace) -> Path:
    spec = validate_spec(load_json(args.spec), Path(__file__).resolve())
    _, membership, months, hashes = authenticate_inputs(
        spec,
        args.canonical_spec,
        args.membership,
        args.support_spec,
        args.support_receipt,
        args.support_validation,
    )
    audit = build_audit(spec, membership, months, hashes)
    if not RUN_ID_RE.fullmatch(args.run_id):
        raise D02AuditError("run-id must be a bounded gate2_d02_* identifier")
    output_parent = args.output_parent.resolve()
    output_parent.mkdir(parents=True, exist_ok=True)
    final = output_parent / args.run_id
    if final.exists():
        raise D02AuditError("refusing to overwrite an existing output leaf")
    staging = Path(tempfile.mkdtemp(prefix=f".{args.run_id}-", dir=output_parent))
    try:
        _write_json(staging / AUDIT_FILENAME, audit)
        audit_hash = sha256_file(staging / AUDIT_FILENAME)
        result_id = compute_result_id(spec["spec_id"], AUDIT_FILENAME, audit_hash)
        receipt: dict[str, Any] = {
            "schema_version": RECEIPT_SCHEMA,
            "status": "PASS_D02_SINGLE_AGE_IDENTIFICATION_AUDIT",
            "run_id": args.run_id,
            "executed_at_utc": datetime.now(timezone.utc).isoformat(),
            "spec_id": spec["spec_id"],
            "spec_sha256": sha256_file(args.spec),
            "code_sha256": sha256_file(Path(__file__).resolve()),
            "authenticated_inputs": {
                key: {"sha256": value} for key, value in sorted(hashes.items())
            },
            "protected_outcomes_opened": False,
            "row_level_data_opened": False,
            "coefficient_estimated": False,
            "output_hashes": {AUDIT_FILENAME: audit_hash},
            "result_ids": {AUDIT_FILENAME: result_id},
        }
        receipt["receipt_id"] = compute_receipt_id(receipt)
        _write_json(staging / RECEIPT_FILENAME, receipt)
        os.rename(staging, final)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return final


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--spec", required=True, type=Path)
    result.add_argument("--canonical-spec", required=True, type=Path)
    result.add_argument("--membership", required=True, type=Path)
    result.add_argument("--support-spec", required=True, type=Path)
    result.add_argument("--support-receipt", required=True, type=Path)
    result.add_argument("--support-validation", required=True, type=Path)
    result.add_argument("--output-parent", required=True, type=Path)
    result.add_argument("--run-id", required=True)
    return result


def main() -> int:
    try:
        final = execute(parser().parse_args())
    except (D02AuditError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"GATE 2 D02 BLOCKED: {exc}")
        return 2
    print(json.dumps({"status": "PASS", "output": str(final)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
