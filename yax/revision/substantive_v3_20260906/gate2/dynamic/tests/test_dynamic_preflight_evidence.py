from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
DYNAMIC = HERE.parent
ROOT = HERE.parents[3]
RUNNER = DYNAMIC / "run_dynamic_reconciliation.py"
SPEC = DYNAMIC / "DYNAMIC_RECONCILIATION_SPEC.json"
REPORT = DYNAMIC / "evidence/DYNAMIC_PREFLIGHT_REPORT.json"
RECEIPT = DYNAMIC / "evidence/DYNAMIC_PREFLIGHT_STDOUT_RECEIPT.json"

loader = importlib.util.spec_from_file_location("dynamic_preflight", RUNNER)
assert loader is not None and loader.loader is not None
dynamic = importlib.util.module_from_spec(loader)
loader.loader.exec_module(dynamic)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_retained_preflight_artifact_identity_and_scope():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))

    assert sha256(RUNNER) == receipt["runner_sha256"]
    assert spec["spec_id"] == receipt["spec_id"] == dynamic.compute_spec_id(spec)
    assert (
        dynamic.compute_signed_behavior_sha256(spec)
        == receipt["signed_behavior_sha256"]
        == dynamic.EXPECTED_SIGNED_BEHAVIOR_SHA256
    )
    assert sha256(REPORT) == receipt["artifact_sha256"]
    assert receipt["result_id"] == dynamic.compute_result_id(
        spec["spec_id"], REPORT.name, receipt["artifact_sha256"]
    )
    assert receipt["artifact_path"] == "gate2/dynamic/evidence/DYNAMIC_PREFLIGHT_REPORT.json"
    assert report["analysis_status"] == "PRE_RESULT_IMPLEMENTATION_NONAUTHORITATIVE"
    assert report["authoritative_completion"] is False
    assert receipt["authoritative_completion"] is False
    assert receipt["object_bearing_execution_authorized"] is False
    assert report["object_availability"]["full_covariance"] == "MISSING_NOT_FABRICATED"
    assert report["object_availability"]["occupation_influence"] == "MISSING_NOT_FABRICATED"
    assert report["requirement_disposition"]["Y08"].startswith("UNMET:")
    assert report["requirement_disposition"]["T05"].startswith("UNMET:")


def test_preflight_report_contains_no_absolute_paths():
    report = json.loads(REPORT.read_text(encoding="utf-8"))

    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for key, child in value.items():
                yield str(key)
                yield from strings(child)
        elif isinstance(value, list):
            for child in value:
                yield from strings(child)

    assert not any(value.startswith("/") for value in strings(report))
