import importlib.util
import json
import pathlib

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]


def load(name, filename):
    path = ROOT / "capability_panel" / filename
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PLAN = load("w4_plan", "plan.py")
AVAIL = load("w4_availability_for_plan", "availability.py")
REGISTRY = AVAIL.load_registry(ROOT / "capability_panel" / "vintage_registry.json")
HASH = "a" * 64
COMMIT = "b" * 40


def test_authorized_gdpval_receipt_with_no_duration_fields_has_zero_coverage():
    receipt = {
        "n_unique_task_ids": 220,
        "task_completion_duration_fields": [],
        "task_completion_duration_status": "NOT_RELEASED_IN_PUBLIC_PARQUET",
    }
    coverage = PLAN.duration_coverage_from_receipt(receipt)
    assert coverage["covered_task_ids"] == 0
    assert coverage["missing_task_ids"] == 220
    assert coverage["coverage_rate"] == 0


def test_w3_receipt_requires_exact_commit_license_guard_and_adjudication():
    receipt = {
        "mapping_commit": COMMIT,
        "license_guard_status": "PASS_TASK_IDS_ONLY",
        "adjudication_status": "PASS",
        "mapping_sha256": HASH,
        "mapping_row_count": 10,
    }
    PLAN.validate_w3_receipt(receipt, expected_commit=COMMIT)
    broken = dict(receipt, license_guard_status="UNKNOWN")
    with pytest.raises(PLAN.PlanError, match="license guard"):
        PLAN.validate_w3_receipt(broken, expected_commit=COMMIT)


def test_plan_contains_ids_only_and_defers_scoring_when_duration_is_absent():
    availability = AVAIL.audit_registry(REGISTRY, None)
    rows = PLAN.build_run_plan(
        ["task-B", "task-A"],
        REGISTRY,
        availability,
        repetitions=2,
        mapping_commit=COMMIT,
        mapping_receipt_sha256=HASH,
    )
    assert rows
    # Availability still blocks capture: this registry was audited with no key,
    # so every direct row is unprobed. Duration no longer does (amendment s3).
    assert all(row["plan_status"] == "blocked" for row in rows)
    assert not any("blocked_missing_task_duration" in row["blockers"] for row in rows), \
        "duration must no longer appear as a CAPTURE blocker"
    assert all(row["scoring_status"] == "deferred_missing_task_duration" for row in rows)
    assert all("deferred_missing_task_duration" in row["scoring_blockers"] for row in rows)
    serialized = json.dumps(rows)
    assert "task_text" not in serialized and "prompt" not in serialized
    receipt = PLAN.sanitized_plan_receipt(rows)
    assert receipt["unique_task_ids"] == 2
    assert receipt["status_counts"] == {"blocked": len(rows)}


def test_repetition_count_has_no_silent_default():
    availability = AVAIL.audit_registry(REGISTRY, None)
    with pytest.raises(PLAN.PlanError, match="repetitions"):
        PLAN.build_run_plan(
            ["task-A"], REGISTRY, availability, repetitions=0,
            mapping_commit=COMMIT, mapping_receipt_sha256=HASH,
        )


def test_unverified_duration_never_leaks_a_value_into_the_plan():
    """The no-inference rule survives the capture/scoring split.

    A row may now be captured without duration, but an unauthorised value must
    still never reach the plan -- that guarantee is what amendment section 3
    explicitly does NOT relax.
    """
    availability = AVAIL.audit_registry(REGISTRY, None)
    rows = PLAN.build_run_plan(
        ["task-A"],
        REGISTRY,
        availability,
        repetitions=1,
        mapping_commit=COMMIT,
        mapping_receipt_sha256=HASH,
        duration_by_task={
            "task-A": {
                "status": "blocked_missing",
                "value": 99,
                "unit": "minute",
                "source": "unauthorized-placeholder",
            }
        },
    )
    assert rows
    assert all(row["task_duration_status"] == "deferred_scoring" for row in rows)
    assert all(row["task_duration_value"] is None for row in rows)
    assert all(row["task_duration_unit"] is None for row in rows)
    assert all(row["task_duration_source"] == "" for row in rows)
