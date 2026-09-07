from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import shutil

import numpy as np
import pytest


MODULE_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[6]
RUNNER = MODULE_DIR / "run_single_age_identification_audit.py"
SPEC_PATH = MODULE_DIR / "D02_IDENTIFICATION_SPEC.json"
CANONICAL_PATH = (
    REPO_ROOT
    / "yax/revision/substantive_v3_20260906/contracts/specs/canonical_baseline_reproduction_v2.json"
)
MEMBERSHIP_PATH = (
    REPO_ROOT
    / "yax/revision/substantive_r3_20260905/rebuilt_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv"
)
SUPPORT_SPEC_PATH = (
    REPO_ROOT / "yax/revision/substantive_v3_20260906/gate2/SUPPORT_ACCOUNTING_SPEC.json"
)
SUPPORT_RECEIPT_PATH = (
    REPO_ROOT
    / "yax/revision/substantive_v3_20260906/runs/"
    "gate2_support_accounting_authoritative_20260907/EXECUTION_RECEIPT.json"
)
SUPPORT_VALIDATION_PATH = (
    REPO_ROOT
    / "yax/revision/substantive_v3_20260906/gate2/evidence/"
    "SUPPORT_ACCOUNTING_VALIDATION_REPORT.json"
)

module_spec = importlib.util.spec_from_file_location("d02_identification", RUNNER)
assert module_spec is not None and module_spec.loader is not None
d02 = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(d02)


def load_frozen():
    spec = d02.validate_spec(d02.load_json(SPEC_PATH), RUNNER)
    _, membership, months, hashes = d02.authenticate_inputs(
        spec,
        CANONICAL_PATH,
        MEMBERSHIP_PATH,
        SUPPORT_SPEC_PATH,
        SUPPORT_RECEIPT_PATH,
        SUPPORT_VALIDATION_PATH,
    )
    return spec, membership, months, hashes


def test_frozen_spec_id_and_runner_hash_validate():
    spec = d02.load_json(SPEC_PATH)
    assert d02.compute_spec_id(spec) == spec["spec_id"]
    assert d02.sha256_file(RUNNER) == spec["execution"]["code_sha256"]
    assert spec["execution"]["authoritative_output_executed_at_spec_freeze"] is False
    d02.validate_spec(spec, RUNNER)


def test_actual_calendar_and_membership_are_exactly_authenticated():
    spec, membership, months, hashes = load_frozen()
    assert len(membership) == 468
    assert len({row["occupation_code"] for row in membership}) == 468
    assert len(months) == 113
    assert months[0] == "2017-01"
    assert months[-1] == "2026-07"
    assert "2022-12" not in months
    assert "2025-10" not in months
    assert 468 * 113 == 52_884
    assert hashes["membership"] == spec["authenticated_inputs"]["membership"]["sha256"]


def test_actual_row_pivot_proof_establishes_both_exact_identities():
    _, membership, months, _ = load_frozen()
    proof = d02.saturated_absorption_proof(membership, months)
    assert proof["observation_count"] == 52_884
    assert proof["saturated_indicator_rank"] == 52_884
    assert proof["augmented_rank"] == proof["saturated_indicator_rank"]
    assert proof["residual_max_abs"] == 0
    assert proof["row_pivot_bijection"] is True
    assert proof["dense_saturated_matrix_constructed"] is False
    assert proof["exposure_post_columns"] == list(d02.EXPOSURE_COLUMNS)


def test_actual_additive_occupation_plus_month_companion_has_target_rank():
    _, membership, months, _ = load_frozen()
    companion = d02.companion_additive_geometry(membership, months)
    assert companion["residual_target_rank"] == 5
    assert companion["target_column_count"] == 5
    assert companion["status"] == "PASS_POSSIBLE_COMPANION_TARGET_COLUMNS_NOT_ABSORBED"
    assert "additive occupation fixed effects" in companion["nuisance"]


def test_audit_keeps_invalid_saturation_distinct_from_possible_companion():
    spec, membership, months, hashes = load_frozen()
    audit = d02.build_audit(spec, membership, months, hashes)
    invalid = audit["invalid_saturated_single_age_model"]
    companion = audit["possible_separate_age_companion"]
    assert invalid["disposition"] == "INVALID_TARGET_NOT_IDENTIFIED"
    assert "occupation-by-calendar-month" in invalid["nuisance"]
    assert companion["residual_target_rank"] == len(d02.EXPOSURE_COLUMNS)
    assert audit["interpretation"]["claimed_coefficient_identity"] is False
    assert "need not add" in audit["interpretation"]["additivity"]
    assert audit["protected_outcomes_opened"] is False
    assert audit["row_level_data_opened"] is False


def test_small_dense_adversarial_fixture_has_zero_residual_and_unchanged_rank():
    # Repeated, zero, negative, and linearly dependent X columns are deliberate:
    # saturation must absorb every column regardless of its own rank or values.
    keys = [
        ("9000", "2022-11"),
        ("1000", "2023-01"),
        ("9000", "2023-01"),
        ("1000", "2022-11"),
    ]
    x = np.asarray(
        [[0.0, -2.0, 0.0], [1.0, 5.0, 2.0], [1.0, 5.0, 2.0], [0.0, -2.0, 0.0]]
    )
    z, _ = d02.materialize_fixture_designs(keys, x)
    residual = x - z @ np.linalg.solve(z.T @ z, z.T @ x)
    assert np.array_equal(residual, np.zeros_like(x))
    assert np.linalg.matrix_rank(np.column_stack((z, x))) == np.linalg.matrix_rank(z)


def test_small_sparse_adversarial_fixture_has_zero_residual_and_unchanged_rank():
    keys = [(f"{occupation:04d}", month) for occupation in (1, 2, 3) for month in ("p0", "p1")]
    x = np.asarray(
        [[0.0, 0.0], [1.0, 9.0], [0.0, 0.0], [3.0, -4.0], [0.0, 0.0], [-7.0, 2.0]]
    )
    _, sparse_z = d02.materialize_fixture_designs(keys, x)
    residual = x - sparse_z @ (sparse_z.T @ x)
    assert sparse_z.nnz == len(keys)
    assert np.array_equal(residual, np.zeros_like(x))
    augmented = np.column_stack((sparse_z.toarray(), x))
    assert np.linalg.matrix_rank(augmented) == np.linalg.matrix_rank(sparse_z.toarray())


def test_fixture_materialization_rejects_production_sized_or_duplicate_rows():
    with pytest.raises(d02.D02AuditError, match="limited to small"):
        d02.materialize_fixture_designs(
            [(f"{index:04d}", "m") for index in range(65)], np.ones((65, 1))
        )
    with pytest.raises(d02.D02AuditError, match="unique"):
        d02.materialize_fixture_designs(
            [("0001", "m"), ("0001", "m")], np.ones((2, 1))
        )


def test_row_pivot_mapping_rejects_duplicate_axis_keys():
    with pytest.raises(d02.D02AuditError, match="occupation keys"):
        d02.row_pivot_mapping(["0001", "0001"], ["2023-01"])
    with pytest.raises(d02.D02AuditError, match="month keys"):
        d02.row_pivot_mapping(["0001"], ["2023-01", "2023-01"])


def test_membership_tamper_fails_closed_before_parsing(tmp_path: Path):
    spec = d02.validate_spec(d02.load_json(SPEC_PATH), RUNNER)
    tampered = tmp_path / "membership.csv"
    shutil.copyfile(MEMBERSHIP_PATH, tampered)
    raw = tampered.read_text(encoding="utf-8")
    tampered.write_text(raw.replace("Chief executives", "Chief executive", 1), encoding="utf-8")
    with pytest.raises(d02.D02AuditError, match="SHA-256 differs"):
        d02.read_and_authenticate_membership(tampered, spec)


def test_calendar_tamper_fails_spec_id_and_calendar_digest():
    spec = d02.load_json(SPEC_PATH)
    spec["calendar"]["exact_estimation_months"][0] = "2016-12"
    with pytest.raises(d02.D02AuditError, match="spec_id mismatch"):
        d02.validate_spec(spec)
    spec["spec_id"] = d02.compute_spec_id(spec)
    with pytest.raises(d02.D02AuditError, match="calendar digest mismatch"):
        d02.validate_spec(spec)


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("calendar", "expected_estimation_month_count"), 112, "expected estimation month count"),
        (("membership", "expected_panel_row_count"), 52_883, "expected panel row count"),
        (("design", "post_definition"), "post begins 2023-02", "post definition"),
        (("design", "q1_normalization"), "Q5 omitted", "Q1 normalization"),
        (("proof_contract", "fixture_materialization_limit"), 65, "fixture materialization limit"),
        (("outputs", "files"), [d02.AUDIT_FILENAME], "output inventory"),
        (("outputs", "audit_schema_version"), "wrong", "audit schema"),
        (("outputs", "receipt_schema_version"), "wrong", "receipt schema"),
        (("execution", "authoritative_output_executed_at_spec_freeze"), True, "unexecuted at freeze"),
        (("execution", "atomic_new_leaf"), False, "output leaf policy"),
        (("execution", "overwrite_existing_leaf"), True, "output leaf policy"),
    ],
)
def test_rehashed_behavioral_spec_mutations_fail_closed(path, value, message):
    spec = d02.load_json(SPEC_PATH)
    parent = spec
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = value
    spec["spec_id"] = d02.compute_spec_id(spec)
    with pytest.raises(d02.D02AuditError, match=message):
        d02.validate_spec(spec)


def test_result_and_receipt_ids_are_hash_bound_and_tamper_sensitive():
    spec = d02.validate_spec(d02.load_json(SPEC_PATH), RUNNER)
    digest_a = "a" * 64
    digest_b = "b" * 64
    result_a = d02.compute_result_id(spec["spec_id"], d02.AUDIT_FILENAME, digest_a)
    result_b = d02.compute_result_id(spec["spec_id"], d02.AUDIT_FILENAME, digest_b)
    assert result_a.startswith(d02.RESULT_PREFIX)
    assert result_a != result_b
    receipt = {
        "schema_version": d02.RECEIPT_SCHEMA,
        "spec_id": spec["spec_id"],
        "output_hashes": {d02.AUDIT_FILENAME: digest_a},
    }
    receipt_id = d02.compute_receipt_id(receipt)
    receipt["receipt_id"] = receipt_id
    assert d02.compute_receipt_id(receipt) == receipt_id
    receipt["output_hashes"][d02.AUDIT_FILENAME] = digest_b
    assert d02.compute_receipt_id(receipt) != receipt_id


def test_authoritative_cli_has_no_outcome_or_row_level_input_surface():
    actions = {action.dest for action in d02.parser()._actions}
    assert actions == {
        "help",
        "spec",
        "canonical_spec",
        "membership",
        "support_spec",
        "support_receipt",
        "support_validation",
        "output_parent",
        "run_id",
    }
    forbidden = {"cells", "young", "older", "outcome", "microdata"}
    assert actions.isdisjoint(forbidden)
