from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil

import pytest


HERE = Path(__file__).resolve().parent
VALIDATOR_PATH = HERE.parent / "validate_authoritative_result.py"
module_spec = importlib.util.spec_from_file_location("support_result_validator", VALIDATOR_PATH)
assert module_spec is not None and module_spec.loader is not None
validator = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(validator)
REPORT_PATH = HERE.parent / "evidence/POSTRUN_VALIDATION_REPORT.json"


def test_authoritative_result_recomputes():
    report = validator.validate()
    retained = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert report["status"] == (
        "PASS_AUTHORITATIVE_RESULT_AND_PUBLIC_NUMERIC_RECONSTRUCTION_NOT_PRESENTATION"
    )
    assert retained["result_id"] == report["result_id"]
    assert retained["receipt_id"] == report["receipt_id"]
    assert retained["inventory"] == report["inventory"]
    assert retained["scope"] == report["scope"]
    assert retained["expected_structural_rank_block"] == report["expected_structural_rank_block"]
    assert max(retained["numeric_reconstruction"].values()) <= 1e-12
    assert report["inventory"] == {
        "total_files": 42,
        "manifest_artifacts": 40,
        "artifact_hash_and_id_checks": 40,
    }
    assert report["producer_validation"]["passing_check_count"] == 26
    assert report["model_certificates"]["model_count"] == 5
    assert report["scope"]["S05"] == "UNRESOLVED_OUT_OF_SCOPE"
    assert max(report["numeric_reconstruction"].values()) <= 1e-12


def test_artifact_tamper_fails(tmp_path: Path):
    run = tmp_path / "run"
    shutil.copytree(validator.DEFAULT_RUN, run)
    target = run / "PROFILE_ESTIMATES.csv"
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(validator.SupportResultValidationError, match="byte count differs"):
        validator.validate(run)


def test_receipt_rebinding_does_not_hide_manifest_tamper(tmp_path: Path):
    run = tmp_path / "run"
    shutil.copytree(validator.DEFAULT_RUN, run)
    manifest_path = run / "RESULT_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["publication_kind"] = "NOT_A_RESULT"
    manifest["result_id"] = validator._content_id("yaxresult_v1", manifest, ("result_id",))
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(validator.SupportResultValidationError, match="receipt result ID differs"):
        validator.validate(run)


def test_published_numeric_tamper_fails_after_manifest_rebinding(tmp_path: Path):
    run = tmp_path / "run"
    shutil.copytree(validator.DEFAULT_RUN, run)
    estimate_path = run / "PROFILE_ESTIMATES.csv"
    rows = estimate_path.read_text(encoding="utf-8").splitlines()
    fields = rows[1].split(",")
    fields[3] = str(float(fields[3]) + 0.01)
    rows[1] = ",".join(fields)
    estimate_path.write_text("\n".join(rows) + "\n", encoding="utf-8")

    manifest_path = run / "RESULT_MANIFEST.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    record = next(item for item in manifest["artifacts"] if item["filename"] == estimate_path.name)
    record["byte_count"] = estimate_path.stat().st_size
    record["sha256"] = validator._sha256(estimate_path)
    record["result_id"] = validator._content_id("yaxartifact_v1", record, ("result_id",))
    manifest["result_id"] = validator._content_id("yaxresult_v1", manifest, ("result_id",))
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    receipt_path = run / "EXECUTION_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["result_id"] = manifest["result_id"]
    receipt["result_manifest"]["byte_count"] = manifest_path.stat().st_size
    receipt["result_manifest"]["sha256"] = validator._sha256(manifest_path)
    receipt["result_manifest"]["result_id"] = validator._content_id(
        "yaxartifact_v1", receipt["result_manifest"], ("result_id",)
    )
    receipt["receipt_id"] = validator._content_id("yaxreceipt_v1", receipt, ("receipt_id",))
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(validator.SupportResultValidationError, match="paired point-estimate identity"):
        validator.validate(run)
