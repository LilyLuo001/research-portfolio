#!/usr/bin/env python3
"""Validate the retained authoritative D02 artifact without trusting its flags."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import math
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
RUNNER_PATH = HERE / "run_single_age_identification_audit.py"
REPO_ROOT = HERE.parents[4]
V3 = REPO_ROOT / "yax/revision/substantive_v3_20260906"
DEFAULT_RUN = V3 / "runs/gate2_d02_authoritative_20260907"
EXPECTED_FILES = {"EXECUTION_RECEIPT.json", "SINGLE_AGE_IDENTIFICATION_AUDIT.json"}
SEMANTIC_RELATIVE_TOLERANCE = 1e-12
SEMANTIC_ABSOLUTE_TOLERANCE = 1e-15
SEMANTIC_MAXIMUM_ABSOLUTE_DIFFERENCE_BOUND = 1e-12


module_spec = importlib.util.spec_from_file_location("d02_runner", RUNNER_PATH)
if module_spec is None or module_spec.loader is None:
    raise RuntimeError("cannot import D02 runner")
d02 = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(d02)


class D02ValidationError(RuntimeError):
    """The retained D02 artifact failed an independently recomputed check."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise D02ValidationError(message)


def _strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield str(key)
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def _semantic_compare(observed: Any, expected: Any, path: str = "$") -> tuple[int, float]:
    """Compare structure exactly and finite floats at a cross-BLAS tolerance."""
    if type(observed) is not type(expected):
        raise D02ValidationError(f"audit type differs at {path}")
    if isinstance(expected, dict):
        if set(observed) != set(expected):
            raise D02ValidationError(f"audit keys differ at {path}")
        count = 0
        maximum = 0.0
        for key in sorted(expected):
            child_count, child_maximum = _semantic_compare(
                observed[key], expected[key], f"{path}.{key}"
            )
            count += child_count
            maximum = max(maximum, child_maximum)
        return count, maximum
    if isinstance(expected, list):
        if len(observed) != len(expected):
            raise D02ValidationError(f"audit list length differs at {path}")
        count = 0
        maximum = 0.0
        for index, (left, right) in enumerate(zip(observed, expected)):
            child_count, child_maximum = _semantic_compare(
                left, right, f"{path}[{index}]"
            )
            count += child_count
            maximum = max(maximum, child_maximum)
        return count, maximum
    if isinstance(expected, float):
        if not math.isfinite(observed) or not math.isclose(
            observed,
            expected,
            rel_tol=SEMANTIC_RELATIVE_TOLERANCE,
            abs_tol=SEMANTIC_ABSOLUTE_TOLERANCE,
        ):
            raise D02ValidationError(f"audit float differs at {path}")
        return 1, abs(observed - expected)
    if observed != expected:
        raise D02ValidationError(f"audit value differs at {path}")
    return 0, 0.0


def validate(run_dir: Path = DEFAULT_RUN) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    _require(run_dir.is_dir(), "D02 run directory is absent")
    entries = list(run_dir.iterdir())
    inventory = {path.name for path in entries}
    _require(
        inventory == EXPECTED_FILES,
        f"D02 run inventory differs: {sorted(inventory)}",
    )
    _require(
        all(path.is_file() and not path.is_symlink() for path in entries),
        "D02 run directory contains a non-regular entry",
    )

    spec_path = HERE / "D02_IDENTIFICATION_SPEC.json"
    canonical_path = V3 / "contracts/specs/canonical_baseline_reproduction_v2.json"
    membership_path = (
        REPO_ROOT
        / "yax/revision/substantive_r3_20260905/rebuilt_baseline/results/"
        "REBUILT_TREATMENT_MEMBERSHIP.csv"
    )
    support_spec_path = V3 / "gate2/SUPPORT_ACCOUNTING_SPEC.json"
    support_receipt_path = (
        V3 / "runs/gate2_support_accounting_authoritative_20260907/EXECUTION_RECEIPT.json"
    )
    support_validation_path = (
        V3 / "gate2/evidence/SUPPORT_ACCOUNTING_VALIDATION_REPORT.json"
    )

    spec = d02.validate_spec(d02.load_json(spec_path), RUNNER_PATH)
    _, membership, months, input_hashes = d02.authenticate_inputs(
        spec,
        canonical_path,
        membership_path,
        support_spec_path,
        support_receipt_path,
        support_validation_path,
    )
    audit_path = run_dir / d02.AUDIT_FILENAME
    receipt_path = run_dir / d02.RECEIPT_FILENAME
    audit = d02.load_json(audit_path)
    receipt = d02.load_json(receipt_path)
    expected_audit = d02.build_audit(spec, membership, months, input_hashes)
    compared_float_count, maximum_float_difference = _semantic_compare(
        audit, expected_audit
    )
    semantic_comparison_within_bound = (
        compared_float_count > 0
        and maximum_float_difference <= SEMANTIC_MAXIMUM_ABSOLUTE_DIFFERENCE_BOUND
    )

    checks: dict[str, bool] = {}
    checks["audit_semantics_recomputed_cross_platform"] = (
        semantic_comparison_within_bound
    )
    checks["receipt_schema"] = receipt.get("schema_version") == d02.RECEIPT_SCHEMA
    checks["receipt_status"] = (
        receipt.get("status") == "PASS_D02_SINGLE_AGE_IDENTIFICATION_AUDIT"
    )
    run_id = receipt.get("run_id")
    checks["receipt_run_id"] = (
        isinstance(run_id, str)
        and d02.RUN_ID_RE.fullmatch(run_id) is not None
        and run_id == run_dir.name
    )
    try:
        executed = datetime.fromisoformat(receipt.get("executed_at_utc", ""))
        valid_timestamp = (
            executed.tzinfo is not None
            and executed.utcoffset() == timezone.utc.utcoffset(executed)
        )
    except (TypeError, ValueError):
        valid_timestamp = False
    checks["receipt_utc_timestamp"] = valid_timestamp
    checks["receipt_spec_id"] = receipt.get("spec_id") == spec["spec_id"]
    checks["receipt_spec_hash"] = receipt.get("spec_sha256") == d02.sha256_file(spec_path)
    checks["receipt_code_hash"] = receipt.get("code_sha256") == d02.sha256_file(RUNNER_PATH)
    checks["receipt_input_hashes"] = receipt.get("authenticated_inputs") == {
        key: {"sha256": value} for key, value in sorted(input_hashes.items())
    }
    audit_hash = d02.sha256_file(audit_path)
    checks["audit_hash"] = receipt.get("output_hashes") == {
        d02.AUDIT_FILENAME: audit_hash
    }
    expected_result_id = d02.compute_result_id(
        spec["spec_id"], d02.AUDIT_FILENAME, audit_hash
    )
    checks["result_id"] = receipt.get("result_ids") == {
        d02.AUDIT_FILENAME: expected_result_id
    }
    checks["receipt_id"] = receipt.get("receipt_id") == d02.compute_receipt_id(receipt)
    checks["no_protected_outcomes"] = (
        receipt.get("protected_outcomes_opened") is False
        and audit.get("protected_outcomes_opened") is False
    )
    checks["no_row_level_data"] = (
        receipt.get("row_level_data_opened") is False
        and audit.get("row_level_data_opened") is False
    )
    checks["no_coefficient_estimated"] = (
        receipt.get("coefficient_estimated") is False
        and audit.get("coefficient_estimated") is False
    )
    checks["no_absolute_path_disclosure"] = not any(
        value.startswith("/") for value in [*_strings(audit), *_strings(receipt)]
    )
    failed = sorted(key for key, value in checks.items() if value is not True)
    _require(not failed, "D02 validation checks failed: " + ", ".join(failed))

    proof = audit["invalid_saturated_single_age_model"]["proof"]
    companion = audit["possible_separate_age_companion"]
    return {
        "schema_version": "yax-gate2-d02-validation-v1",
        "status": "PASS_D02_AUTHORITATIVE_ARTIFACT_VALIDATION_NOT_MANUSCRIPT_VALIDATION",
        "run_inventory": sorted(inventory),
        "execution_receipt_sha256": d02.sha256_file(receipt_path),
        "audit_sha256": audit_hash,
        "spec_id": spec["spec_id"],
        "result_id": expected_result_id,
        "receipt_id": receipt["receipt_id"],
        "checks": checks,
        "cross_platform_numeric_comparison": {
            "finite_float_count": compared_float_count,
            "relative_tolerance": SEMANTIC_RELATIVE_TOLERANCE,
            "absolute_tolerance": SEMANTIC_ABSOLUTE_TOLERANCE,
            "maximum_absolute_difference_bound": (
                SEMANTIC_MAXIMUM_ABSOLUTE_DIFFERENCE_BOUND
            ),
            "maximum_absolute_difference_within_bound": (
                semantic_comparison_within_bound
            ),
            "reason": "SVD singular values may differ by floating-point roundoff across BLAS implementations.",
        },
        "asserted_geometry_identities": {
            "observation_count": proof["observation_count"],
            "saturated_indicator_rank": proof["saturated_indicator_rank"],
            "augmented_rank": proof["augmented_rank"],
            "residual_max_abs": proof["residual_max_abs"],
            "dense_saturated_matrix_constructed": proof[
                "dense_saturated_matrix_constructed"
            ],
            "full_scale_residual_measured": False,
            "companion_target_rank": companion["residual_target_rank"],
            "companion_smallest_singular_value": min(
                companion["occupation_feature_singular_values"]
            ),
        },
        "limits": [
            "This validates an outcome-free identification artifact, not an estimated coefficient.",
            "It does not validate an outcome-bearing additive companion model.",
            "The semantic validator permits bounded cross-BLAS roundoff; byte-exact evidence hashes are checked separately by the requirements ledger.",
            "Manuscript and appendix presentation remain unvalidated.",
        ],
    }


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    result.add_argument("--output", type=Path)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        report = validate(args.run_dir)
        rendered = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(rendered)
        else:
            print(rendered, end="")
    except (D02ValidationError, d02.D02AuditError, OSError, KeyError, TypeError, ValueError) as exc:
        print(f"D02 VALIDATION BLOCKED: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
