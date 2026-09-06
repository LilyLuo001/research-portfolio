from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "validate_public_transfer.py"
SPEC = importlib.util.spec_from_file_location("yax_gate1_transfer_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fixture(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    (run / "results").mkdir(parents=True)
    (run / "audit_logs").mkdir()
    result = b"result\n"
    log = b""
    failures = b"[]\n"
    (run / "results/table.csv").write_bytes(result)
    (run / "audit_logs/runner.stderr.log").write_bytes(log)
    (run / "audit_logs/WRAPPER_FAILURES.json").write_bytes(failures)
    receipt = {
        "status": MODULE.PASS_STATUS,
        "exit_code": 0,
        "private_paths_or_credentials_persisted": False,
        "spec_id": "yaxspec_v1_" + "a" * 64,
        "repository": {"head": "b" * 40},
        "output_hashes": {
            "table.csv": digest(result),
            "EXECUTION_RECEIPT.json": "c" * 64,
        },
        "audit_artifact_hashes": {
            "runner.stderr.log": digest(log),
            "WRAPPER_FAILURES.json": digest(failures),
        },
    }
    payload = (json.dumps(receipt, sort_keys=True) + "\n").encode()
    (run / "EXECUTION_RECEIPT.json").write_bytes(payload)
    (run / "audit_logs/V3_EXECUTION_RECEIPT.json").write_bytes(payload)
    return run


def test_valid_public_transfer(tmp_path: Path):
    report = MODULE.validate(fixture(tmp_path))
    assert report["status"] == "PASS_SANITIZED_GATE1_PUBLIC_TRANSFER"
    assert report["verified_public_result_count"] == 1


def test_changed_result_fails(tmp_path: Path):
    run = fixture(tmp_path)
    (run / "results/table.csv").write_text("changed\n", encoding="utf-8")
    with pytest.raises(MODULE.TransferError, match="hash mismatch"):
        MODULE.validate(run)


def test_private_marker_fails(tmp_path: Path):
    run = fixture(tmp_path)
    payload = b"/project/private"
    (run / "audit_logs/runner.stderr.log").write_bytes(payload)
    receipt = json.loads((run / "EXECUTION_RECEIPT.json").read_text())
    receipt["audit_artifact_hashes"]["runner.stderr.log"] = digest(payload)
    encoded = (json.dumps(receipt, sort_keys=True) + "\n").encode()
    (run / "EXECUTION_RECEIPT.json").write_bytes(encoded)
    (run / "audit_logs/V3_EXECUTION_RECEIPT.json").write_bytes(encoded)
    with pytest.raises(MODULE.TransferError, match="private marker"):
        MODULE.validate(run)


def test_original_runner_receipt_is_refused(tmp_path: Path):
    run = fixture(tmp_path)
    (run / "results/EXECUTION_RECEIPT.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(MODULE.TransferError, match="must not enter"):
        MODULE.validate(run)
