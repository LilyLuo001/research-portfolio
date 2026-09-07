"""Byte-bind the retained A1 replacement and compatibility-failure evidence."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PASS = ROOT / "runs" / "gate1_numerical_a1_pass_7482383"
FAILED = ROOT / "runs" / "gate1_numerical_a1_compat_blocked_7482111"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_successful_receipt_binds_all_outputs_and_models():
    receipt_path = PASS / "numerical" / "EXECUTION_RECEIPT.json"
    audit_path = PASS / "numerical" / "MODEL_AUDIT.json"
    assert digest(receipt_path) == (
        "84aa54a8b194774cddf814baca8d13520382262373682c3732b1dbd739aa4383"
    )
    assert digest(audit_path) == (
        "ffb4364af0bc55026fd6ebf0f0211938e71c41b382e62897263f1d437b4b8f89"
    )
    receipt = load(receipt_path)
    audit = load(audit_path)
    assert receipt["status"] == "PASS_ALL_CORE_TARGETS_NUMERICALLY_AUDITED"
    assert receipt["model_count"] == 11
    assert receipt["passed_model_count"] == 11
    assert receipt["output_hashes"]["MODEL_AUDIT.json"] == digest(audit_path)
    for name, expected in receipt["output_hashes"].items():
        assert digest(PASS / "numerical" / name) == expected
    assert len(audit["models"]) == 11
    assert all(
        row["finite_target_established"] is True
        and row["classification"] == "PASS_FINITE_EXTENDED_MLE_TARGET"
        and row["a1_certification"]["status"] == "PASS_A1_NUMERICAL_CERTIFICATE"
        for row in audit["models"]
    )


def test_failed_compatibility_run_is_retained_and_cannot_certify():
    receipt_path = FAILED / "numerical" / "EXECUTION_RECEIPT.json"
    audit_path = FAILED / "numerical" / "MODEL_AUDIT.json"
    scheduler_path = FAILED / "scheduler" / "numerical.json"
    assert digest(receipt_path) == (
        "d6bd6b5d743c9510c124caeacfad5f3505bafc8cc57af972c05e75420bc7f59e"
    )
    assert digest(audit_path) == (
        "18869185dfecad9f546bb51609e3bbf51d8c85fdb3fef4f6fd6c218032c4fc74"
    )
    assert digest(scheduler_path) == (
        "cc6cc450621b51494b29965958753700d41244b0ca546a1ea1fa22b88479e120"
    )
    receipt = load(receipt_path)
    audit = load(audit_path)
    scheduler = load(scheduler_path)
    assert receipt["status"] == "BLOCKED_ONE_OR_MORE_CORE_TARGETS_NOT_ESTABLISHED"
    assert receipt["passed_model_count"] == 0
    assert len(audit["models"]) == 11
    assert all(
        row["classification"]
        == "BLOCKED_UNEXPECTED_NUMERICAL_FAILURE_NO_SUBSTITUTION"
        and row["finite_target_established"] is False
        for row in audit["models"]
    )
    assert scheduler["failed"] == 0
    assert scheduler["exit_status"] == 2


def test_sanitized_transfer_and_dependency_release_are_complete():
    transfer = load(PASS / "public_transfer" / "TRANSFER_VALIDATION.json")
    release = load(PASS / "DEPENDENCY_RELEASE.json")
    assert transfer["status"] == "PASS_SANITIZED_GATE1_RECEIPT_NORMALIZATION"
    assert transfer["numerical_suite_pass"] is True
    assert transfer["partial_numerical_evidence_transfer"] is False
    assert all(transfer["cross_receipt_hash_consistency"].values())
    target = release["target_dependencies"]
    assert target["status"] == "PASS_ALL_11_MODELS_CERTIFIED"
    assert target["certified_model_count"] == 11
    assert len(target["consumers"]) == 20
    assert all(row["release_status"] == "RELEASED" for row in target["consumers"].values())
    assert len(target["downstream_requirement_releases"]) == 9
    assert all(
        row["release_status"] == "RELEASED"
        for row in target["downstream_requirement_releases"].values()
    )
    assert target["non_model_prerequisites"]["status"] == (
        "PASS_BOUND_NON_MODEL_PREREQUISITES"
    )
    assert target["preoutcome_target_map_binding"]["status"] == (
        "PASS_PREOUTCOME_TARGET_MAP_BYTE_BINDING"
    )
