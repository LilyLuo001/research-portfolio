from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil

import pytest


HERE = Path(__file__).resolve().parent
VALIDATOR_PATH = HERE.parent / "validate_d02_artifact.py"
loader = importlib.util.spec_from_file_location("d02_validator", VALIDATOR_PATH)
assert loader is not None and loader.loader is not None
validator = importlib.util.module_from_spec(loader)
loader.loader.exec_module(validator)
REPORT_PATH = validator.HERE / "evidence/D02_VALIDATION_REPORT.json"


def test_authoritative_artifact_recomputes_exactly():
    report = validator.validate()
    retained = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert retained == report
    assert report["status"] == (
        "PASS_D02_AUTHORITATIVE_ARTIFACT_VALIDATION_NOT_MANUSCRIPT_VALIDATION"
    )
    assert all(report["checks"].values())
    geometry = report["asserted_geometry_identities"]
    assert geometry["observation_count"] == 52_884
    assert geometry["saturated_indicator_rank"] == 52_884
    assert geometry["augmented_rank"] == 52_884
    assert geometry["residual_max_abs"] == 0
    assert geometry["dense_saturated_matrix_constructed"] is False
    assert geometry["full_scale_residual_measured"] is False
    assert geometry["companion_target_rank"] == 5


def test_retained_report_is_invariant_to_same_blas_revalidation(monkeypatch):
    retained = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    authoritative_audit = validator.d02.load_json(
        validator.DEFAULT_RUN / validator.d02.AUDIT_FILENAME
    )
    monkeypatch.setattr(
        validator.d02,
        "build_audit",
        lambda *args, **kwargs: copy.deepcopy(authoritative_audit),
    )
    assert validator.validate() == retained


def test_receipt_tamper_fails_closed(tmp_path: Path):
    run = tmp_path / "run"
    shutil.copytree(validator.DEFAULT_RUN, run)
    receipt_path = run / validator.d02.RECEIPT_FILENAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["protected_outcomes_opened"] = True
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(validator.D02ValidationError, match="failed"):
        validator.validate(run)


def test_audit_tamper_fails_closed(tmp_path: Path):
    run = tmp_path / "run"
    shutil.copytree(validator.DEFAULT_RUN, run)
    audit_path = run / validator.d02.AUDIT_FILENAME
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    audit["invalid_saturated_single_age_model"]["proof"]["residual_max_abs"] = 1
    audit_path.write_text(json.dumps(audit), encoding="utf-8")
    with pytest.raises(validator.D02ValidationError, match="audit value differs"):
        validator.validate(run)


def test_extra_file_or_symlink_fails_closed(tmp_path: Path):
    run = tmp_path / "run"
    shutil.copytree(validator.DEFAULT_RUN, run)
    (run / "extra.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(validator.D02ValidationError, match="inventory"):
        validator.validate(run)


def test_extra_directory_fails_closed(tmp_path: Path):
    run = tmp_path / "run"
    shutil.copytree(validator.DEFAULT_RUN, run)
    (run / "extra").mkdir()
    with pytest.raises(validator.D02ValidationError, match="inventory"):
        validator.validate(run)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("run_id", "gate2_d02_wrong_leaf"),
        ("run_id", "unsafe run id"),
        ("executed_at_utc", "not-a-time"),
        ("executed_at_utc", "2026-09-07T12:07:44"),
    ],
)
def test_rebound_receipt_metadata_tamper_fails_closed(tmp_path: Path, field, value):
    run = tmp_path / "run"
    shutil.copytree(validator.DEFAULT_RUN, run)
    receipt_path = run / validator.d02.RECEIPT_FILENAME
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt[field] = value
    receipt["receipt_id"] = validator.d02.compute_receipt_id(receipt)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(validator.D02ValidationError, match="failed"):
        validator.validate(run)
