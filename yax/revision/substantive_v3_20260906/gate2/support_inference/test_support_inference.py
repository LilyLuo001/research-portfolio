import hashlib
import importlib.util
import json
import os
import pathlib
import sys
import copy
import ast
import csv
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import pytest


HERE = pathlib.Path(__file__).resolve().parent
RUNNER = HERE / "run_support_inference.py"
SPEC = HERE / "SUPPORT_INFERENCE_SPEC.json"
module_spec = importlib.util.spec_from_file_location("support_inference_under_test", RUNNER)
si = importlib.util.module_from_spec(module_spec)
sys.modules[module_spec.name] = si
module_spec.loader.exec_module(si)
A1_RUNNER = HERE.parent.parent / "numerical_existence" / "run_numerical_existence_audit.py"
A1_SPEC = HERE.parent.parent / "numerical_existence" / "ANALYSIS_SPEC_A1.json"
A1_ANALYSIS = json.loads(A1_SPEC.read_text())
A1 = si.load_a1(A1_RUNNER, A1_ANALYSIS["software"]["artifact_safety_sha256"])
ARTIFACT_SAFETY, _ = si.verify_artifact_safety_binding(A1, A1_ANALYSIS, A1_RUNNER)


@pytest.fixture(autouse=True)
def _numeric_sge_job(monkeypatch):
    monkeypatch.setenv("JOB_ID", "1")


def _fake_provenance(run_identity=None):
    value = {
        "schema_version": "yax-gate2-support-inference-execution-provenance-v1",
        "status": "PASS_COMMITTED_PRE_EXECUTION_AUTHORIZATION_AND_RUNTIME_BINDING",
        "executing_runner_sha256": si.sha256_file(RUNNER),
        "executing_spec_sha256": si.sha256_file(SPEC),
        "git_head": "1"*40, "git_tree": "2"*40, "repository_clean": True,
        "execution_runtime_authentication": {"status": "AUTHENTICATED_ISOLATED_PINNED_EXECUTABLES"},
        "a1_runtime_payload_sha256": si.EXPECTED_A1_RUNTIME_PAYLOAD_SHA256,
        "pre_execution_authorization": {"status": si.PRE_EXECUTION_AUTHORIZATION_STATUS},
        "authenticated_input_hashes": {"synthetic": "3"*64}}
    if run_identity is not None:
        value["run_identity"] = copy.deepcopy(run_identity)
    value["provenance_id"] = si.content_id(
        "yaxgate2provenance_v1", value, ("provenance_id",))
    return value


def _fake_success_outputs(provenance=None):
    outputs = {}
    for name in si.SUCCESS_OUTPUT_FILES:
        if name.endswith(".csv"):
            outputs[name] = pd.DataFrame({"synthetic": [1]})
        elif name.endswith(".json"):
            outputs[name] = {"synthetic": True}
        else:
            outputs[name] = (("synthetic", np.asarray([1.])),)
    pooled = np.array([[1., 2.], [3., 4.]])
    family = np.array([[2., 3.], [4., 5.]])
    paired = family-pooled
    edge = np.array([[1., 2.], [2., 1.]])
    pair = np.array([[3.], [4.]])
    direct = np.array([[5., 6.]])
    multipliers = np.array([[1., -1.], [-1., 1.]])
    draw = {"occupation_order_sha256": "0"*64,
            "multiplier_matrix_sha256": si.array_sha256(multipliers),
            "pooled_draws_sha256": si.array_sha256(pooled),
            "family_month_draws_sha256": si.array_sha256(family),
            "paired_draws_sha256": si.array_sha256(paired),
            "supported_edge_draws_sha256": si.array_sha256(edge),
            "pairwise_aggregate_draws_sha256": si.array_sha256(pair),
            "direct_tail_functional_draws_sha256": si.array_sha256(direct),
            "heterogeneous_occupation_order_sha256": "1"*64,
            "direct_tail_occupation_order_sha256": "2"*64,
            "identity": "paired_draws == family_month_draws - pooled_draws",
            "identity_storage_exact": True,
            "direct_formula_maximum_absolute_residual": 0.,
            "direct_formula_tolerance": 1e-14,
            "direct_formula_within_tolerance": True,
            "all_inference_draws_use_subsets_of_common_occupation_ordered_multiplier_matrix": True}
    draw["draw_binding_id"] = si.content_id("yaxdrawbinding_v1", draw, ("draw_binding_id",))
    outputs["COMMON_DRAW_BINDING.json"] = draw
    outputs["COMMON_MULTIPLIERS.npz"] = (("occupation_codes", np.asarray(["a", "b"])),
        ("multipliers", multipliers), ("draw_id", np.asarray([draw["draw_binding_id"]])))
    outputs["CENTERED_TARGET_DRAWS.npz"] = (("pooled_Q2_Q5", pooled),
        ("family_month_Q2_Q5", family), ("paired_Q2_Q5", paired))
    outputs["HETEROGENEITY_CENTERED_DRAWS.npz"] = (("supported_edge_draws", edge),
        ("pairwise_aggregate_draws", pair), ("direct_tail_functional_draws", direct))
    validation = {"schema_version": "yax-gate2-support-inference-validation-v1",
                  "checks": {"synthetic_complete_check": {"pass": True}},
                  "failed_checks": [], "status": "PASS_RECOMPUTED_VALIDATION"}
    validation["validation_id"] = si.content_id("yaxvalidation_v1", validation, ("validation_id",))
    outputs["VALIDATION_REPORT.json"] = validation
    component = {"component": "supported_edges_full_89_dimensional_joint_test",
        "disposition": "EXPECTED_STRUCTURAL_RANK_BLOCK", "restriction_count": 89,
        "functional_rank": 50, "maximum_covariance_rank": 50, "covariance_rank": 50,
        "additional_covariance_rank_deficiency": 0,
        "test_status": "BLOCKED_RANK_DEFICIENT_JOINT_TEST",
        "chi2_or_p_value_emitted": False}
    outputs["MODEL_FAILURES.json"] = {"status": "EXPECTED_STRUCTURAL_RANK_BLOCK",
        "numerical_fit_status": "ALL_REQUIRED_A1_CERTIFICATES_PASS",
        "blocked_components": [component]}
    outputs["HETEROGENEITY_JOINT_TESTS.json"] = {
        "supported_edges_rank_aware_joint": {"status": "BLOCKED_RANK_DEFICIENT_JOINT_TEST",
            "restriction_count": 89, "covariance_rank": 50}}
    outputs["EXECUTION_PROVENANCE.json"] = copy.deepcopy(
        provenance if provenance is not None else _fake_provenance())
    return outputs


def _complete_success_outputs(provenance=None):
    outputs = _fake_success_outputs(provenance)
    validation = outputs["VALIDATION_REPORT.json"]
    validation["checks"] = {key: {"pass": True} for key in sorted(si.VALIDATION_CHECK_KEYS)}
    validation["validation_id"] = si.content_id(
        "yaxvalidation_v1", validation, ("validation_id",))
    return outputs


def _fake_failure_outputs():
    failure = si.certification_failure("TEST", "synthetic", "blocked")
    evidence = failure.evidence
    evidence["evidence_id"] = si.content_id(
        "yaxfailureevidence_v1", evidence, ("evidence_id",))
    validation = {"schema_version": "yax-gate2-failure-evidence-validation-v1",
                  "publication_class": si.FAILURE_PUBLICATION,
                  "scientific_result_claims": False, "evidence_id": evidence["evidence_id"],
                  "has_failure_stage": True, "has_model_id": True, "identity_verified": True}
    validation["validation_id"] = si.content_id(
        "yaxfailurevalidation_v1", validation, ("validation_id",))
    return {"FAILURE_EVIDENCE.json": evidence, "FAILURE_VALIDATION.json": validation}


def _args(tmp_path, run_id="gate2_support_inference_sge_1"):
    args = type("Args", (), {"output_parent": tmp_path, "run_id": run_id})()
    args.runtime_contract = {"status": "TEST_RUNTIME"}
    args.artifact_safety = ARTIFACT_SAFETY
    args.artifact_safety_evidence = {"status": "PASS_HASH_PINNED_A1_ARTIFACT_SAFETY"}
    for name in ("canonical_spec", "a1_spec", "a1_runner", "a1_model_audit",
                 "a1_dependency_release", "cells", "cells_receipt", "fixed_membership",
                 "support_matrix", "support_edges", "direct_tail_membership",
                 "pre_execution_authorization"):
        setattr(args, name, RUNNER)
    args.cells_receipt = SPEC
    if si.SAFE_RUN_ID_PATTERN.fullmatch(run_id) is not None:
        args.run_identity = si.build_run_identity(args)
        args.execution_provenance = _fake_provenance(args.run_identity)
        args.initial_execution_provenance = args.execution_provenance
        args.final_execution_provenance = args.execution_provenance
        si.issue_publication_capability(args, args.execution_provenance)
    else:
        args.execution_provenance = _fake_provenance()
    return args


def test_frozen_runner_hash_and_no_historical_solver_import():
    frozen = json.loads(SPEC.read_text())
    observed = hashlib.sha256(RUNNER.read_bytes()).hexdigest()
    assert observed == frozen["implementation_sha256"]
    source = RUNNER.read_text()
    assert "run_within_family" not in source
    assert "historical direct-tail" not in source


def test_spec_id_detects_semantic_mutation_even_if_runner_hash_is_unchanged():
    frozen = json.loads(SPEC.read_text())
    si.validate_frozen_spec(frozen)
    mutated = copy.deepcopy(frozen)
    mutated["inference"]["seed"] += 1
    with pytest.raises(si.Blocked, match="canonical content identity"):
        si.validate_frozen_spec(mutated)


def test_signed_behavior_cannot_be_changed_with_a_recomputed_spec_id():
    frozen = json.loads(SPEC.read_text())
    mutated = copy.deepcopy(frozen)
    mutated["signed_behavior"]["probability_clipping"] = True
    mutated["spec_id"] = si.content_id("yaxgate2spec_v1", mutated, ("spec_id",))
    with pytest.raises(si.Blocked, match="reviewed contract|signed behavior"):
        si.validate_frozen_spec(mutated)


def _leaf_paths(value, path=()):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _leaf_paths(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _leaf_paths(item, path + (index,))
    else:
        yield path


def _mutate_leaf(value):
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + .125
    if value is None:
        return "MUTATED_NONE"
    return str(value) + "__MUTATED"


def _set_path(value, path, replacement):
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement


def _get_path(value, path):
    target = value
    for key in path:
        target = target[key]
    return target


def test_every_spec_leaf_mutation_is_rejected_even_after_resealing_spec_id():
    frozen = json.loads(SPEC.read_text())
    si.validate_frozen_spec(frozen)
    paths = list(_leaf_paths(frozen))
    assert len(paths) >= 75
    for path in paths:
        mutated = copy.deepcopy(frozen)
        _set_path(mutated, path, _mutate_leaf(_get_path(mutated, path)))
        if path != ("spec_id",):
            mutated["spec_id"] = si.content_id("yaxgate2spec_v1", mutated, ("spec_id",))
        with pytest.raises(si.Blocked):
            si.validate_frozen_spec(mutated)


def test_canonical_calendar_is_elapsed_and_missing_safe():
    months = si.observed_months()
    assert len(months) == 114
    assert months[0] == "2017-01" and months[-1] == "2026-07"
    assert "2025-10" not in months
    assert "2022-12" in months
    assert len([m for m in months if m != "2022-12"]) == 113


def test_common_rademacher_is_deterministic_and_shared():
    occupations = ["0010", "0020", "0030"]
    left = si.common_rademacher(occupations, 19, 2026090521)
    right = si.common_rademacher(occupations, 19, 2026090521)
    assert np.array_equal(left, right)
    assert set(np.unique(left)) == {-1.0, 1.0}


def test_rank_aware_joint_test_blocks_singular_covariance():
    result = si.rank_aware_test(np.array([1.0, 1.0]), np.ones((2, 2)))
    assert result["status"] == "BLOCKED_RANK_DEFICIENT_JOINT_TEST"
    assert result["covariance_rank"] == 1


def test_weighted_family_center_and_exact_sd_scaling():
    occ = pd.DataFrame({
        "family": ["11", "11", "13", "13"],
        "rule_A_beta": [0.0, 1.0, 0.2, 0.8],
        "webb_z": [-1.0, 1.0, -0.5, 0.5],
        "pre_stock": [1.0, 3.0, 2.0, 2.0],
    })
    occ["beta_centered"] = si.weighted_family_center(
        occ.rule_A_beta, occ.family, occ.pre_stock)
    for _, group in occ.groupby("family"):
        assert abs(np.sum(group.pre_stock * group.beta_centered)) < 1e-12
    occ["beta_residual"] = si.residualize_on_family_webb(
        occ.rule_A_beta, occ.family, occ.webb_z, occ.pre_stock)
    result = si.exact_sd_reparameterizations(2.5, occ)
    assert result["within_family_sd_effect"] == pytest.approx(
        2.5 * result["within_family_sd"])
    assert result["family_webb_residual_sd_effect"] == pytest.approx(
        2.5 * result["family_webb_residual_sd"])


def _tiny_paths_inputs():
    support = pd.DataFrame({"family": ["11", "11"], "beta_quintile": [1, 5],
                            "cell_has_support": [True, True]})
    rows = []
    for month in si.observed_months():
        for q in (1, 5):
            rows.append({"family": "11", "beta_quintile": q, "month": month,
                         "young": 2.0 if q == 1 else 3.0,
                         "older": 4.0 if q == 1 else 5.0})
    return pd.DataFrame(rows), support


def test_paths_preserve_missing_month_and_transition_labels():
    cells, support = _tiny_paths_inputs()
    monthly, quarterly = si.aggregate_family_quintile_paths(cells, support)
    missing = monthly.loc[monthly.month.eq("2025-10")]
    assert len(missing) == 2
    assert set(missing.calendar_status) == {"MISSING"}
    assert missing[["young", "older"]].isna().all().all()
    assert set(monthly.loc[monthly.month.eq("2022-12"), "calendar_status"]) == {"TRANSITION"}
    q4 = quarterly.loc[quarterly.quarter.eq("2025Q4")]
    assert (q4.observed_estimation_month_count == 2).all()
    assert (q4.calendar_month_count == 3).all()
    transition_q = quarterly.loc[quarterly.quarter.eq("2022Q4")]
    assert (transition_q.observed_estimation_month_count == 2).all()
    assert (transition_q.transition_month_count == 1).all()
    assert (transition_q.defined_log_ratio_month_count == 2).all()


def test_paths_refuse_data_in_canonical_missing_month():
    cells, support = _tiny_paths_inputs()
    cells = pd.concat([cells, pd.DataFrame([{"family": "11", "beta_quintile": 1,
        "month": "2025-10", "young": 1.0, "older": 1.0}])], ignore_index=True)
    with pytest.raises(si.Blocked, match="missing month"):
        si.aggregate_family_quintile_paths(cells, support)


class FakeA1:
    class ModelBundle:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)


def _tiny_cells():
    return pd.DataFrame({
        "occ_code": ["0001", "0001", "0002", "0002", "0003", "0003", "0004", "0004"],
        "month": ["2022-11", "2023-01"] * 4,
        "family": ["11", "11", "11", "11", "13", "13", "13", "13"],
        "young": [2.] * 8, "older": [3.] * 8,
        "beta_quintile": [1, 1, 5, 5, 2, 2, 4, 4],
        "webb_z": [-1., -1., 1., 1., -.5, -.5, .5, .5],
    })


def test_family_heterogeneous_design_uses_family_specific_references():
    support = pd.DataFrame({
        "family": ["11", "11", "13", "13"], "beta_quintile": [1, 5, 2, 4],
        "cell_has_support": [True] * 4})
    bundle = si.build_family_heterogeneous_bundle(FakeA1, _tiny_cells(), support)
    assert bundle.regressor_labels == [
        "family_11:Q5_vs_Q1_x_post", "family_13:Q4_vs_Q2_x_post", "Webb_z_x_post"]
    assert np.array_equal(bundle.regressors[:, :2].sum(axis=0), [1., 1.])


def test_direct_tail_design_has_four_separate_effects():
    cells = pd.concat([_tiny_cells()] * 2, ignore_index=True)
    cells["occ_code"] = [f"{i:04d}" for i in range(1, 9) for _ in range(2)]
    cells["family"] = np.repeat(["27", "29", "31", "41"], 4)
    cells["beta_quintile"] = np.tile([1, 1, 5, 5], 4)
    direct = cells[["family", "occupation_code"]].copy() if "occupation_code" in cells else None
    direct = cells[["family", "occ_code"]].drop_duplicates().rename(columns={"occ_code": "occupation_code"})
    direct["beta_quintile"] = [1, 5] * 4
    direct["preperiod_stock"] = np.arange(1, 9, dtype=float)
    bundle = si.build_direct_tail_bundle(FakeA1, cells, direct)
    assert bundle.regressor_labels[:-1] == [
        "family_27:Q5_vs_Q1_x_post", "family_29:Q5_vs_Q1_x_post",
        "family_31:Q5_vs_Q1_x_post", "family_41:Q5_vs_Q1_x_post"]
    assert bundle.focal_target_label == "fixed_pre_stock_direct_tail_aggregate"
    assert bundle.focal_target_weights[-1] == 0
    assert bundle.focal_target_weights[:-1].sum() == pytest.approx(1)


def test_direct_aggregate_is_exact_coefficient_before_a1_audit():
    a1 = si.load_a1(HERE.parent.parent / "numerical_existence" /
                    "run_numerical_existence_audit.py")
    cells = pd.concat([_tiny_cells()] * 2, ignore_index=True)
    cells["occ_code"] = [f"{i:04d}" for i in range(1, 9) for _ in range(2)]
    cells["family"] = np.repeat(["27", "29", "31", "41"], 4)
    cells["beta_quintile"] = np.tile([1, 1, 5, 5], 4)
    direct = cells[["family", "occ_code"]].drop_duplicates().rename(
        columns={"occ_code": "occupation_code"})
    direct["beta_quintile"] = [1, 5] * 4
    direct["preperiod_stock"] = np.arange(1, 9, dtype=float)
    original = si.build_direct_tail_bundle(a1, cells, direct)
    transformed, parameterization = a1.target_coordinate_bundle(original)
    assert transformed.focal_target_weights is None
    assert transformed.regressor_labels[0] == "fixed_pre_stock_direct_tail_aggregate"
    assert parameterization["status"] == "EXACT_INVERTIBLE_LINEAR_FUNCTIONAL_REPARAMETERIZATION"
    assert parameterization["identity_max_absolute_error"] < 1e-13


def test_publish_failure_does_not_leave_result(monkeypatch, tmp_path):
    args = _args(tmp_path)
    monkeypatch.setattr(si, "write_json", lambda *_: (_ for _ in ()).throw(si.Blocked("boom")))
    with pytest.raises(si.Blocked):
        failure = si.certification_failure("TEST", "synthetic", "boom")
        si.publish_failure_evidence(args, json.loads(SPEC.read_text()), failure)
    assert not (tmp_path / "gate2_support_inference_sge_1").exists()
    assert not (tmp_path / "gate2_support_inference_sge_1__FAILURE_EVIDENCE").exists()
    assert list(tmp_path.glob(".gate2_support_inference_sge_1__FAILURE_EVIDENCE.staging-*"))
    assert (tmp_path / ".gate2_support_inference_sge_1__FAILURE_EVIDENCE.publish.lock").is_file()


def test_publish_binds_filenames_content_result_and_receipt_ids(tmp_path):
    args = _args(tmp_path)
    spec = json.loads(SPEC.read_text())
    destination = si.publish(args, spec, _fake_failure_outputs(), si.FAILURE_PUBLICATION)
    manifest = json.loads((destination / "RESULT_MANIFEST.json").read_text())
    receipt = json.loads((destination / "EXECUTION_RECEIPT.json").read_text())
    assert manifest["result_id"] == si.content_id("yaxresult_v1", manifest, ("result_id",))
    assert receipt["receipt_id"] == si.content_id("yaxreceipt_v1", receipt, ("receipt_id",))
    assert receipt["result_id"] == manifest["result_id"]
    assert receipt["run_identity"] == args.run_identity
    retained_staging = list(tmp_path.glob(
        ".gate2_support_inference_sge_1__FAILURE_EVIDENCE.staging-*"))
    retained_lock = tmp_path / ".gate2_support_inference_sge_1__FAILURE_EVIDENCE.publish.lock"
    assert len(retained_staging) == 1
    assert receipt["retention"] == {
        "staging_leaf_retained": True,
        "sibling_lock_leaf_retained": True,
        "staging_leaf": retained_staging[0].name,
        "sibling_lock_leaf": retained_lock.name,
        "automatic_path_cleanup": False,
        "quota_behavior": "ONE_PRIVATE_STAGING_LEAF_AND_ONE_LOCK_LEAF_RETAINED_PER_PUBLICATION_ATTEMPT",
        "cleanup_authority": "MANUAL_INODE_AUDITED_OPERATOR_CLEANUP_ONLY"}
    assert retained_lock.is_file()
    for artifact in manifest["artifacts"]:
        assert artifact["result_id"] == si.content_id("yaxartifact_v1", artifact, ("result_id",))
        assert artifact["filename"] == pathlib.Path(artifact["filename"]).name
        assert artifact["logical_key"] == pathlib.Path(artifact["filename"]).stem.lower()


@pytest.mark.parametrize("unsafe", ["", ".", "..", "../escape", "a/b", "/absolute", "a\\b", " x", "x y"])
def test_publish_rejects_unsafe_run_id_leaves(tmp_path, unsafe):
    args = _args(tmp_path, unsafe)
    with pytest.raises(si.Blocked, match="safe output leaf"):
        si.publish(args, json.loads(SPEC.read_text()), _fake_failure_outputs(), si.FAILURE_PUBLICATION)
    assert not any(tmp_path.iterdir())


def test_publish_rejects_existing_symlink_destination(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    parent = tmp_path / "outputs"
    parent.mkdir()
    (parent / "gate2_support_inference_sge_1").symlink_to(outside, target_is_directory=True)
    args = _args(parent)
    with pytest.raises(si.Blocked, match="pre-existing output leaf"):
        si.publish(args, json.loads(SPEC.read_text()),
                   _complete_success_outputs(args.execution_provenance))
    assert not (outside / "X.json").exists()


@pytest.mark.parametrize("stage", ["A1_AUDIT_EXCEPTION", "A1_CERTIFICATE",
    "FINITE_FACE_RECONSTRUCTION", "RANK_AND_BASIS_RECONSTRUCTION",
    "REFERENCE_EXTERNAL_CERTIFICATE", "TRUST_EXTERNAL_CERTIFICATE",
    "TRUST_REFERENCE_COMPARISON", "A1_TARGET_CHECKPOINT"])
def test_each_certificate_stage_publishes_only_atomic_nonauthoritative_failure_evidence(
        monkeypatch, tmp_path, stage):
    args = _args(tmp_path)
    spec = json.loads(SPEC.read_text())
    failure = si.certification_failure(stage, "synthetic_model", "injected /Users/private secret=bad",
        audit={"a1_certification": {"status": "BLOCKED_A1_NUMERICAL_CERTIFICATE"}},
        solver_rows=[{"method": "trust-ncg", "numerically_valid": False}])
    monkeypatch.setattr(si, "certified_fit", lambda *_: (_ for _ in ()).throw(failure))
    with pytest.raises(si.Blocked, match="nonauthoritative evidence published"):
        si.certified_fit_or_publish_failure(None, None, {}, args, spec)
    assert not (tmp_path / "gate2_support_inference_sge_1").exists()
    destination = tmp_path / "gate2_support_inference_sge_1__FAILURE_EVIDENCE"
    evidence = json.loads((destination / "FAILURE_EVIDENCE.json").read_text())
    receipt = json.loads((destination / "EXECUTION_RECEIPT.json").read_text())
    manifest = json.loads((destination / "RESULT_MANIFEST.json").read_text())
    assert evidence["failure_stage"] == stage
    assert "Users/private" not in json.dumps(evidence) and "secret=bad" not in json.dumps(evidence)
    assert receipt["status"] == "NONAUTHORITATIVE_FAILURE_EVIDENCE_ONLY"
    assert receipt["scientific_result_claims"] is False
    assert manifest["scientific_result_claims"] is False
    assert sorted(item["filename"] for item in manifest["artifacts"]) == [
        "FAILURE_EVIDENCE.json", "FAILURE_VALIDATION.json"]


def test_full_covariance_and_interval_helpers_preserve_labels():
    covariance = np.diag([1., 4., 9., 16.])
    labels = ["Q2", "Q3", "Q4", "Q5"]
    draws = np.zeros((11, 4))
    rows = si.long_matrix("pooled", covariance, labels, labels)
    intervals = si.interval_rows("pooled", labels, np.arange(4.), covariance, draws)
    assert len(rows) == 16
    assert {(r["row_target"], r["column_target"]) for r in rows} == {
        (left, right) for left in labels for right in labels}
    assert [r["target"] for r in intervals] == labels
    assert all(r["draw_count"] == 11 for r in intervals)


def test_89_edge_system_reports_rank_block_but_intervals_remain_labeled():
    estimates = np.zeros(89)
    covariance = np.ones((89, 89))
    result = si.rank_aware_test(estimates, covariance)
    assert result["restriction_count"] == 89
    assert result["covariance_rank"] == 1
    assert result["status"] == "BLOCKED_RANK_DEFICIENT_JOINT_TEST"


def test_profile_checkpoint_retains_both_fresh_paths_and_differences():
    labels = ["Q2_x_post", "Q3_x_post"]
    fit = type("Fit", (), {"model_id": "pooled", "labels": labels,
        "state_source": {"primary_original_treatment": dict(zip(labels, [1., 2.])),
                         "reference_original_treatment": dict(zip(labels, [1.1, 2.1]))}})()
    audit = {"models": [{"model_id": "pooled", "solver_comparison": {
        "trust_path_target_vector": {"original_treatment::0::Q2_x_post": 1.,
                                     "original_treatment::1::Q3_x_post": 2.},
        "reference_target_vector": {"original_treatment::0::Q2_x_post": 1.1,
                                    "original_treatment::1::Q3_x_post": 2.1}}}]}
    rows = si.profile_checkpoint(fit, audit, 1e-12)
    assert len(rows) == 4
    assert {row["path"] for row in rows} == {
        "trust-path", "independent-damped-sparse-newton-irls"}
    assert all(row["absolute_difference"] == 0 for row in rows)


def _semantic_support_fixture():
    membership = pd.DataFrame({
        "occupation_code": ["1001", "1002", "2001", "2002"],
        "occupation_name": ["a", "b", "c", "d"],
        "preperiod_weight": [10., 30., 20., 40.],
        "rule_A_beta": [.1, .9, .2, .8],
        "beta_quintile": [1, 5, 1, 5], "webb_z": [-1., 1., -.5, .5]})
    cells = pd.DataFrame({"occ_code": membership.occupation_code,
                          "family": ["27", "27", "29", "29"]})
    support_rows = []
    for family, low_code, high_code in (("27", "1001", "1002"), ("29", "2001", "2002")):
        for q in range(1, 6):
            chosen = membership.loc[membership.occupation_code.eq(low_code if q == 1 else high_code)]
            supported = q in (1, 5)
            support_rows.append({"family": family, "beta_quintile": q,
                "occupation_count": int(supported),
                "preperiod_stock": float(chosen.preperiod_weight.iloc[0]) if supported else 0.,
                "exposure_min": float(chosen.rule_A_beta.iloc[0]) if supported else np.nan,
                "exposure_max": float(chosen.rule_A_beta.iloc[0]) if supported else np.nan,
                "cell_has_support": supported})
    support = pd.DataFrame(support_rows)
    edges = pd.DataFrame([
        {"family": family, "quintile_low": 1, "quintile_high": 5,
         "low_occupation_count": 1, "high_occupation_count": 1,
         "low_preperiod_stock": low, "high_preperiod_stock": high,
         "direct_tail_edge": True}
        for family, low, high in (("27", 10., 30.), ("29", 20., 40.))])
    direct = membership.rename(columns={"preperiod_weight": "preperiod_stock"}).copy()
    direct["family"] = ["27", "27", "29", "29"]
    direct["within_family_quintile_preperiod_stock_share"] = 1.
    direct["within_direct_family_tails_preperiod_stock_share"] = [.25, .75, 1/3, 2/3]
    spec = {"expected_counts": {"support_matrix_rows": 10, "supported_cells": 4,
                                 "support_edges": 2, "direct_tail_occupations": 4},
            "direct_tail": {"families": ["27", "29"]}}
    return cells, membership, support, edges, direct, spec


def test_support_semantics_recompute_from_membership_and_cells():
    args = _semantic_support_fixture()
    si.validate_support_artifacts(*args)


def test_support_semantic_mutations_fail_even_when_counts_are_unchanged():
    cells, membership, support, edges, direct, spec = _semantic_support_fixture()
    bad_support = support.copy()
    bad_support.loc[bad_support.cell_has_support.idxmax(), "preperiod_stock"] += 1
    with pytest.raises(si.Blocked, match="stocks differ"):
        si.validate_support_artifacts(cells, membership, bad_support, edges.copy(), direct.copy(), spec)
    bad_direct = direct.copy()
    bad_direct.loc[0, "within_direct_family_tails_preperiod_stock_share"] += .01
    with pytest.raises(si.Blocked, match="shares fail"):
        si.validate_support_artifacts(cells, membership, support.copy(), edges.copy(), bad_direct, spec)


def test_fixed_reference_alignment_blocks_missing_support_and_allows_exact_subset():
    reference = type("Fit", (), {})()
    reference.bundle = type("Bundle", (), {"frame": pd.DataFrame({
        "occ_code": ["a", "b"], "month": ["2023-01", "2023-01"]})})()
    reference.active = np.array([True, True])
    reference.probability = np.array([.2, .3])
    subset = type("Fit", (), {})()
    subset.bundle = type("Bundle", (), {"frame": pd.DataFrame({
        "occ_code": ["b"], "month": ["2023-01"]})})()
    subset.active = np.array([True])
    assert np.array_equal(si.aligned_reference_probability(reference, subset), [.3])
    missing = type("Fit", (), {})()
    missing.bundle = type("Bundle", (), {"frame": pd.DataFrame({
        "occ_code": ["c"], "month": ["2023-01"]})})()
    missing.active = np.array([True])
    with pytest.raises(si.Blocked, match="alignment is incomplete"):
        si.aligned_reference_probability(reference, missing)


def test_array_and_artifact_ids_bind_shape_filename_and_logical_key():
    a = np.arange(6).reshape(2, 3)
    assert si.array_sha256(a) != si.array_sha256(a.reshape(3, 2))
    record = {"logical_key": "table", "filename": "TABLE.csv", "sha256": "0"*64,
              "byte_count": 1}
    original = si.content_id("yaxartifact_v1", record)
    record["filename"] = "RENAMED.csv"
    assert si.content_id("yaxartifact_v1", record) != original


def test_linear_derived_closure_detects_covariance_draw_orientation_and_label_mutations():
    influence = np.array([[1., 0., 1.], [0., 1., -1.], [-1., 0., .5], [0., -1., -.5]])
    correction = len(influence)/(len(influence)-1)
    base_covariance = correction * influence.T @ influence
    functionals = np.array([[1., 2., 0.], [0., -1., 3.]])
    labels = ["first", "second"]
    xi = np.array([[1., -1., 1., -1.], [-1., 1., 1., -1.]])
    derived_if = influence @ functionals.T
    covariance = functionals @ base_covariance @ functionals.T
    draws = np.sqrt(correction) * xi @ derived_if
    result = si.verify_linear_derived_closure(
        "synthetic", labels, labels, functionals, base_covariance, influence,
        xi, covariance, draws)
    assert result["pass"] is True
    with pytest.raises(si.Blocked, match="label order"):
        si.verify_linear_derived_closure("synthetic", labels[::-1], labels, functionals,
            base_covariance, influence, xi, covariance, draws)
    with pytest.raises(si.Blocked, match="closure failed"):
        si.verify_linear_derived_closure("synthetic", labels, labels, functionals,
            base_covariance, influence, xi, covariance + np.eye(2)*1e-4, draws)
    with pytest.raises(si.Blocked, match="orientation"):
        si.verify_linear_derived_closure("synthetic", labels, labels, functionals.T,
            base_covariance, influence, xi, covariance, draws)
    with pytest.raises(si.Blocked, match="closure failed"):
        si.verify_linear_derived_closure("synthetic", labels, labels, functionals,
            base_covariance, influence, xi, covariance, draws[:, ::-1])


def test_success_disposition_discloses_expected_structural_rank_block():
    source = RUNNER.read_text()
    assert "EXPECTED_STRUCTURAL_RANK_BLOCK" in source
    assert "NO_BLOCKED_COMPONENTS_IN_PUBLISHED_RUN" not in source
    blocked = si.rank_aware_test(np.zeros(89), np.ones((89, 89)))
    assert "chi2" not in blocked and "p_value_chi2" not in blocked


def test_cell_schema_and_assignment_semantics_are_recomputed():
    codes = [f"{index:04d}" for index in range(468)]
    membership = pd.DataFrame({"occupation_code": codes,
        "preperiod_weight": np.ones(468), "rule_A_beta": np.linspace(0, 1, 468),
        "beta_quintile": (np.arange(468) % 5) + 1,
        "webb_z": np.linspace(-1, 1, 468)})
    grid = pd.MultiIndex.from_product([codes, si.observed_months()],
                                      names=["occ_code", "month"]).to_frame(index=False)
    grid["family"] = "11"
    grid["young"] = 1.
    grid["older"] = 2.
    mapping = membership.set_index("occupation_code")
    grid["beta_quintile"] = grid.occ_code.map(mapping.beta_quintile)
    grid["webb_z"] = grid.occ_code.map(mapping.webb_z)
    payload = "".join(f"{code}\t11\t{int(mapping.loc[code, 'beta_quintile'])}\t"
                      f"{float(mapping.loc[code, 'webb_z']).hex()}\n" for code in codes)
    fingerprint = hashlib.sha256(payload.encode()).hexdigest()
    receipt = {"schema_version": "yax-numerical-cells-receipt-v1",
               "aggregate_schema_version": "yax-numerical-cells-v1",
               "status": "PASS_FRESH_AGGREGATE_REBUILD", "occupation_count": 468,
               "observed_month_count": 114, "assignment_fingerprint_sha256": fingerprint,
               "assignment_fingerprint": {"sha256": fingerprint}}
    validated = si.validate_cells(grid, receipt, membership)
    assert len(validated) == 468*114
    rounded = grid.copy()
    rounded.loc[rounded.occ_code.eq(codes[0]), "webb_z"] += 5e-13
    assert float(rounded.loc[rounded.occ_code.eq(codes[0]), "webb_z"].iloc[0]).hex() != \
        float(mapping.loc[codes[0], "webb_z"]).hex()
    rounded_validated = si.validate_cells(rounded, receipt, membership)
    assert len(rounded_validated) == 468*114
    drifted = grid.copy()
    drifted.loc[drifted.occ_code.eq(codes[0]), "webb_z"] += 2e-12
    with pytest.raises(si.Blocked, match="cell Webb values differ"):
        si.validate_cells(drifted, receipt, membership)
    mutated = grid.copy()
    mutated.loc[0, "webb_z"] += .1
    with pytest.raises(si.Blocked, match="family or Webb assignment changes"):
        si.validate_cells(mutated, receipt, membership)


def test_fixed_membership_float_parser_matches_gate1_python_float_producer():
    path = HERE.parents[1] / (
        "runs/gate1_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv")
    with path.open("r", encoding="utf-8", newline="") as stream:
        producer_rows = list(csv.DictReader(stream))
    exact = si.read_fixed_membership(path)
    default = pd.read_csv(path, dtype={"occupation_code": str})
    assert len(producer_rows) == len(exact) == 468
    assert any(
        float(row["webb_z"]).hex() != float(value).hex()
        for row, value in zip(producer_rows, default.webb_z)
    )
    assert all(
        float(row["webb_z"]).hex() == float(value).hex()
        for row, value in zip(producer_rows, exact.webb_z)
    )


def test_repaired_public_assignment_payload_matches_gate1_frozen_fingerprint():
    root = HERE.parents[3]
    membership = si.read_fixed_membership(
        HERE.parents[1] /
        "runs/gate1_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv")
    families = pd.read_csv(
        root / "measurement/COMPUTERIZATION_MEASURES_CENSUS2018.csv",
        dtype={"census2018": str})
    families["census2018"] = families.census2018.str.zfill(4)
    assignments = membership[[
        "occupation_code", "beta_quintile", "webb_z"]].merge(
            families[["census2018", "soc_major_group"]],
            left_on="occupation_code", right_on="census2018",
            validate="one_to_one")
    assignments["family"] = assignments.soc_major_group.astype(str)
    payload = "".join(
        f"{str(row.occupation_code).zfill(4)}\t{row.family}\t"
        f"{int(row.beta_quintile)}\t{float(row.webb_z).hex()}\n"
        for row in assignments.sort_values(
            "occupation_code", kind="mergesort").itertuples(index=False))
    cell_spec = json.loads((HERE.parents[1] / "gate1_cells/CELL_BUILD_SPEC.json").read_text())
    assert hashlib.sha256(payload.encode()).hexdigest() == \
        cell_spec["assignment_contract"]["fingerprint_sha256"]


def test_complete_numerical_evidence_redacts_only_occupation_month_identifier():
    evidence = {"comparison_pass": True, "location": {"occ_code": "0010",
        "month": "2023-01", "family": "11", "difference": 1e-9,
        "credential": "not-obviously-secret"}}
    sanitized = si.sanitized_numerical_evidence(evidence)
    assert sanitized["comparison_pass"] is True
    assert sanitized["location"]["status"] == "REDACTED_OCCUPATION_MONTH_IDENTIFIER"
    assert sanitized["location"]["credential"] == "REDACTED_SECRET"
    assert "0010" not in json.dumps(sanitized)


def test_numerical_evidence_redacts_composite_general_recession_cells_and_counts():
    evidence = {
        "partition": "general_recession_face",
        "group": "1234|11|2023-01",
        "row_index": 7,
        "young": 1.0,
        "older": 2.0,
        "total": 3.0,
        "strict_margin": 0.25,
        "reason": "target_invariant_recession_face",
        "status": "PASS_SHOULD_NOT_OVERRIDE_REDACTION",
    }
    sanitized = si.sanitized_numerical_evidence(evidence)
    serialized = json.dumps(sanitized, sort_keys=True)
    assert sanitized["status"] == "REDACTED_OCCUPATION_MONTH_IDENTIFIER"
    assert sanitized["strict_margin"] == 0.25
    assert not ({"group", "row_index", "young", "older", "total"} & set(sanitized))
    assert "1234" not in serialized and "2023-01" not in serialized


@pytest.mark.parametrize("alias", ["group", "label", "location", "cell"])
def test_numerical_evidence_redacts_composite_occupation_month_aliases(alias):
    evidence = {alias: "prefix|0010|29|2024-12", "young": 4, "older": 5, "total": 9}
    sanitized = si.sanitized_numerical_evidence(evidence)
    serialized = json.dumps(sanitized, sort_keys=True)
    assert sanitized["status"] == "REDACTED_OCCUPATION_MONTH_IDENTIFIER"
    assert "0010" not in serialized and "2024-12" not in serialized
    assert not ({"young", "older", "total"} & set(sanitized))


def test_numerical_evidence_redacts_strict_row_index_margin_alignment():
    evidence = {"separation": {
        "strict_boundary_local_indices": [1, 7],
        "strict_boundary_margins": [0.1, 0.2],
        "separation_exists": True,
    }}
    sanitized = si.sanitized_numerical_evidence(evidence)
    row = sanitized["separation"]
    assert row["strict_boundary_local_indices"] == \
        "REDACTED_OCCUPATION_MONTH_ROW_ALIGNMENT"
    assert row["strict_boundary_margins"] == \
        "REDACTED_OCCUPATION_MONTH_ROW_ALIGNMENT"
    assert row["separation_exists"] is True


def test_typed_sanitizer_redacts_embedded_paths_and_generic_credentials():
    evidence = {
        "message": "solver failed while reading /usr3/private/run/input.csv",
        "credential": "ordinary-looking-value",
        "nested": [pathlib.Path("/private/tmp/model"),
                   ValueError("Bearer opaque-session-value"), np.int64(7), b"binary"],
        "relative_label": "family/contrast",
    }
    sanitized = si.sanitized_numerical_evidence(evidence)
    assert sanitized == {
        "message": "REDACTED_PRIVATE_PATH",
        "credential": "REDACTED_SECRET",
        "nested": ["REDACTED_PRIVATE_PATH", "REDACTED_SECRET", 7,
                   "REDACTED_BINARY_VALUE"],
        "relative_label": "family/contrast",
    }
    serialized = json.dumps(sanitized)
    assert "/usr3" not in serialized and "opaque-session-value" not in serialized


def test_staged_scan_rejects_quoted_json_secret_key(tmp_path):
    path = tmp_path / "FAILURE_EVIDENCE.json"
    path.write_text('{"token":"opaque-value"}\n')
    with pytest.raises(si.Blocked, match="unredacted secret field"):
        si.scan_staged_publication(tmp_path, {path.name})


def test_frozen_publication_inventory_is_exact_and_mechanically_equal_to_runner():
    frozen = json.loads(SPEC.read_text())
    assert frozen["outputs"] == {
        "publication_kind_enum": [si.SUCCESS_PUBLICATION, si.FAILURE_PUBLICATION],
        "success_files": sorted(si.SUCCESS_OUTPUT_FILES),
        "failure_files": sorted(si.FAILURE_OUTPUT_FILES),
        "validation_check_keys": sorted(si.VALIDATION_CHECK_KEYS)}
    assert len(si.SUCCESS_OUTPUT_FILES) == 40
    assert si.FAILURE_OUTPUT_FILES == {"FAILURE_EVIDENCE.json", "FAILURE_VALIDATION.json"}
    assigned = set()
    for node in ast.walk(ast.parse(RUNNER.read_text())):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if (isinstance(target, ast.Subscript) and isinstance(target.value, ast.Name) and
                    target.value.id == "outputs" and isinstance(target.slice, ast.Constant) and
                    isinstance(target.slice.value, str)):
                assigned.add(target.slice.value)
    assert assigned == si.SUCCESS_OUTPUT_FILES


@pytest.mark.parametrize("mutation", ["missing", "extra", "fake_status", "failed_check",
                                      "fake_identity", "nonmapping_check"])
def test_success_gate_rejects_incomplete_extra_or_fake_validation(mutation):
    spec = json.loads(SPEC.read_text())
    outputs = _complete_success_outputs()
    if mutation == "missing":
        del outputs["VALIDATION_REPORT.json"]
    elif mutation == "extra":
        outputs["UNSIGNED_EXTRA.json"] = {}
    else:
        validation = outputs["VALIDATION_REPORT.json"]
        if mutation == "fake_status":
            validation["status"] = "PASS_FAKE"
        elif mutation == "failed_check":
            validation["failed_checks"] = [next(iter(si.VALIDATION_CHECK_KEYS))]
        elif mutation == "fake_identity":
            validation["validation_id"] = "yaxvalidation_v1_" + "0"*64
        else:
            validation["checks"][next(iter(si.VALIDATION_CHECK_KEYS))] = True
    with pytest.raises(si.Blocked):
        si.validate_publication_payload(spec, outputs, si.SUCCESS_PUBLICATION)


def test_one_row_synthetic_validation_cannot_publish(tmp_path):
    with pytest.raises(si.Blocked, match="check-key inventory differs"):
        si.publish(_args(tmp_path), json.loads(SPEC.read_text()), _fake_success_outputs())
    assert not any(tmp_path.iterdir())


def test_success_gate_rejects_fake_structural_block_and_mutated_common_draw():
    spec = json.loads(SPEC.read_text())
    outputs = _complete_success_outputs()
    outputs["MODEL_FAILURES.json"]["blocked_components"][0]["functional_rank"] = 51
    with pytest.raises(si.Blocked, match="structural-block"):
        si.validate_publication_payload(spec, outputs, si.SUCCESS_PUBLICATION)
    outputs = _complete_success_outputs()
    arrays = list(outputs["HETEROGENEITY_CENTERED_DRAWS.npz"])
    arrays[0] = (arrays[0][0], arrays[0][1] + 1)
    outputs["HETEROGENEITY_CENTERED_DRAWS.npz"] = tuple(arrays)
    with pytest.raises(si.Blocked, match="stored draws"):
        si.validate_publication_payload(spec, outputs, si.SUCCESS_PUBLICATION)


def test_success_gate_recomputes_exact_stored_paired_draw_identity():
    spec = json.loads(SPEC.read_text())
    outputs = _complete_success_outputs()
    centered = dict(outputs["CENTERED_TARGET_DRAWS.npz"])
    centered["paired_Q2_Q5"] = centered["paired_Q2_Q5"] + 1.
    outputs["CENTERED_TARGET_DRAWS.npz"] = tuple(centered.items())
    draw = outputs["COMMON_DRAW_BINDING.json"]
    draw["paired_draws_sha256"] = si.array_sha256(centered["paired_Q2_Q5"])
    draw["draw_binding_id"] = si.content_id(
        "yaxdrawbinding_v1", draw, ("draw_binding_id",))
    common = dict(outputs["COMMON_MULTIPLIERS.npz"])
    common["draw_id"] = np.asarray([draw["draw_binding_id"]])
    outputs["COMMON_MULTIPLIERS.npz"] = tuple(common.items())
    with pytest.raises(si.Blocked, match="exact stored paired-draw identity"):
        si.validate_publication_payload(spec, outputs, si.SUCCESS_PUBLICATION)


def test_failure_gate_rejects_any_third_file():
    spec = json.loads(SPEC.read_text())
    failure = si.certification_failure("TEST", "synthetic", "blocked")
    evidence = failure.evidence
    evidence["evidence_id"] = si.content_id("yaxfailureevidence_v1", evidence, ("evidence_id",))
    validation = {"publication_class": si.FAILURE_PUBLICATION,
                  "scientific_result_claims": False, "identity_verified": True}
    with pytest.raises(si.Blocked, match="inventory"):
        si.validate_publication_payload(spec, {"FAILURE_EVIDENCE.json": evidence,
            "FAILURE_VALIDATION.json": validation, "EXTRA.json": {}}, si.FAILURE_PUBLICATION)


def test_duplicate_logical_keys_are_rejected_before_semantic_claims(monkeypatch):
    duplicate_inventory = frozenset({"SAME.csv", "SAME.json"})
    monkeypatch.setattr(si, "SUCCESS_OUTPUT_FILES", duplicate_inventory)
    spec = {"outputs": {"success_files": sorted(duplicate_inventory)}}
    with pytest.raises(si.Blocked, match="duplicate logical keys"):
        si.validate_publication_payload(spec, {"SAME.csv": pd.DataFrame({"x": [1]}),
                                                "SAME.json": {}}, si.SUCCESS_PUBLICATION)


def test_descriptor_publication_preserves_competing_filename_without_receipt(monkeypatch, tmp_path):
    args = _args(tmp_path)
    original_link = si.os.link
    raced = False
    destination = tmp_path / "gate2_support_inference_sge_1__FAILURE_EVIDENCE"
    def racing_link(source, name, **kwargs):
        nonlocal raced
        if not raced:
            raced = True
            (destination / pathlib.Path(name).name).write_text("competitor-owned")
        return original_link(source, name, **kwargs)
    monkeypatch.setattr(si.os, "link", racing_link)
    with pytest.raises(si.Blocked, match="competing filename"):
        si.publish(args, json.loads(SPEC.read_text()), _fake_failure_outputs(), si.FAILURE_PUBLICATION)
    assert any(path.read_text() == "competitor-owned" for path in destination.iterdir())
    assert not (destination / "EXECUTION_RECEIPT.json").exists()


def test_reservation_failure_never_unlinks_replacement_lock(monkeypatch, tmp_path):
    target = tmp_path / "gate2_support_inference_sge_1__FAILURE_EVIDENCE"
    lock = tmp_path / f".{target.name}.publish.lock"
    original_mkdir = si.os.mkdir

    def fail_after_replacing_lock(path, mode=0o777, *, dir_fd=None):
        if str(path).startswith(f".{target.name}.staging-"):
            lock.unlink()
            lock.write_text("competitor-owned")
            raise OSError("synthetic staging creation failure")
        return original_mkdir(path, mode=mode, dir_fd=dir_fd)

    monkeypatch.setattr(si.os, "mkdir", fail_after_replacing_lock)
    with pytest.raises(OSError, match="synthetic staging creation failure"):
        si.reserve_output_leaf(ARTIFACT_SAFETY, target, HERE, [])
    assert lock.read_text() == "competitor-owned"
    assert not list(tmp_path.glob(f".{target.name}.staging-*"))


def test_descriptor_publication_detects_directory_swap_to_symlink(monkeypatch, tmp_path):
    args = _args(tmp_path)
    original_link = si.os.link
    destination = tmp_path / "gate2_support_inference_sge_1__FAILURE_EVIDENCE"
    displaced = tmp_path / "displaced_owned_leaf"
    outside = tmp_path / "competitor_directory"
    outside.mkdir()
    raced = False
    def swapping_link(source, name, **kwargs):
        nonlocal raced
        if not raced:
            raced = True
            destination.rename(displaced)
            destination.symlink_to(outside, target_is_directory=True)
        return original_link(source, name, **kwargs)
    monkeypatch.setattr(si.os, "link", swapping_link)
    with pytest.raises(si.Blocked, match="inode identity changed"):
        si.publish(args, json.loads(SPEC.read_text()), _fake_failure_outputs(), si.FAILURE_PUBLICATION)
    assert destination.is_symlink()
    assert not list(outside.iterdir())
    assert not (displaced / "EXECUTION_RECEIPT.json").exists()


def test_receipt_is_the_final_publication_commit_marker(monkeypatch, tmp_path):
    linked = []
    original_link = si.os.link
    def recording_link(source, destination, **kwargs):
        linked.append(pathlib.Path(destination).name)
        return original_link(source, destination, **kwargs)
    monkeypatch.setattr(si.os, "link", recording_link)
    si.publish(_args(tmp_path), json.loads(SPEC.read_text()),
               _fake_failure_outputs(), si.FAILURE_PUBLICATION)
    assert linked[-1] == "EXECUTION_RECEIPT.json"
    assert linked.count("EXECUTION_RECEIPT.json") == 1


@pytest.mark.parametrize("publication_kind", [si.SUCCESS_PUBLICATION,
                                               si.FAILURE_PUBLICATION])
def test_same_inode_in_place_mutation_is_detected_after_receipt_and_owned_links_removed(
        monkeypatch, tmp_path, publication_kind):
    args = _args(tmp_path)
    failure_only = publication_kind == si.FAILURE_PUBLICATION
    outputs = (_fake_failure_outputs() if failure_only else
               _complete_success_outputs(args.execution_provenance))
    if not failure_only:
        monkeypatch.setattr(si, "execution_provenance",
                            lambda *_: copy.deepcopy(args.execution_provenance))
    destination = tmp_path / (args.run_id +
        ("__FAILURE_EVIDENCE" if failure_only else ""))
    original_link = si.os.link
    mutation = {}
    def mutating_link(source, name, **kwargs):
        if pathlib.Path(name).name == "EXECUTION_RECEIPT.json" and not mutation:
            victim = next(path for path in destination.iterdir() if path.is_file())
            before = os.lstat(victim)
            with victim.open("r+b") as stream:
                first = stream.read(1)
                stream.seek(0)
                stream.write(b"\x00" if first != b"\x00" else b"\x01")
                stream.flush()
            after = os.lstat(victim)
            mutation.update({"before": (before.st_dev, before.st_ino),
                             "after": (after.st_dev, after.st_ino)})
        return original_link(source, name, **kwargs)
    monkeypatch.setattr(si.os, "link", mutating_link)
    with pytest.raises(si.Blocked, match="artifact inode, size, or content differs"):
        si.publish(args, json.loads(SPEC.read_text()), outputs, publication_kind)
    assert mutation["before"] == mutation["after"]
    assert destination.is_dir() and not list(destination.iterdir())
    assert not (destination / "EXECUTION_RECEIPT.json").exists()
    assert list(tmp_path.glob(f".{destination.name}.staging-*"))
    assert (tmp_path / f".{destination.name}.publish.lock").is_file()


def test_success_publication_recomputes_and_exactly_matches_live_provenance(
        monkeypatch, tmp_path):
    args = _args(tmp_path)
    outputs = _complete_success_outputs(args.execution_provenance)
    calls = []
    def fresh_provenance(*call_args):
        calls.append(call_args)
        return copy.deepcopy(args.execution_provenance)
    monkeypatch.setattr(si, "execution_provenance", fresh_provenance)
    destination = si.publish(args, json.loads(SPEC.read_text()), outputs)
    assert calls and len(calls) == 1
    assert (destination / "EXECUTION_RECEIPT.json").is_file()


def test_success_publication_rejects_output_provenance_different_from_live_state(
        monkeypatch, tmp_path):
    args = _args(tmp_path)
    outputs = _complete_success_outputs(args.execution_provenance)
    altered = copy.deepcopy(outputs["EXECUTION_PROVENANCE.json"])
    altered["git_tree"] = "9"*40
    altered["provenance_id"] = si.content_id(
        "yaxgate2provenance_v1", altered, ("provenance_id",))
    outputs["EXECUTION_PROVENANCE.json"] = altered
    si.issue_publication_capability(args, altered)
    monkeypatch.setattr(si, "execution_provenance",
                        lambda *_: copy.deepcopy(args.execution_provenance))
    with pytest.raises(si.Blocked, match="prepublication provenance differ"):
        si.publish(args, json.loads(SPEC.read_text()), outputs)
    assert not (tmp_path / args.run_id).exists()


def test_publish_requires_in_process_authenticated_main_capability(tmp_path):
    args = _args(tmp_path)
    del args._publication_capability
    with pytest.raises(si.Blocked, match="in-process authenticated main capability"):
        si.publish(args, json.loads(SPEC.read_text()),
                   _fake_failure_outputs(), si.FAILURE_PUBLICATION)
    assert not any(tmp_path.iterdir())


def test_run_identity_requires_numeric_sge_job_and_exact_run_suffix(monkeypatch, tmp_path):
    args = _args(tmp_path)
    monkeypatch.setenv("JOB_ID", "2")
    with pytest.raises(si.Blocked, match="suffix does not exactly equal"):
        si.build_run_identity(args)
    monkeypatch.setenv("JOB_ID", "not-numeric")
    with pytest.raises(si.Blocked, match="positive numeric SGE JOB_ID"):
        si.build_run_identity(args)


def test_run_identity_is_canonical_and_contains_no_absolute_paths(tmp_path):
    args = _args(tmp_path)
    serialized = json.dumps(args.run_identity, sort_keys=True)
    assert str(tmp_path) not in serialized
    assert args.run_identity["sge_job_id"] == "1"
    assert args.run_identity["intended_run_id"] == args.run_id
    binding = args.run_identity["command_binding"]
    assert binding["command_binding_sha256"] == hashlib.sha256(
        si.canonical_bytes({key: value for key, value in binding.items()
                            if key != "command_binding_sha256"})).hexdigest()


def test_authorization_run_binding_is_exact_and_single_use(tmp_path):
    args = _args(tmp_path)
    run = args.run_identity
    document = {key: copy.deepcopy(run[key]) for key in (
        "intended_run_id", "sge_job_id", "output_parent_identity",
        "command_binding", "single_use_semantics")}
    si.validate_authorized_run_binding(document, run)
    document["output_parent_identity"]["inode"] += 1
    with pytest.raises(si.Blocked, match="authorization run binding differs"):
        si.validate_authorized_run_binding(document, run)


def test_publication_requires_output_outside_repository(tmp_path):
    args = _args(HERE)
    with pytest.raises(si.Blocked, match="outside the Git repository"):
        si.publish(args, json.loads(SPEC.read_text()),
                   _fake_failure_outputs(), si.FAILURE_PUBLICATION)
    assert not (HERE / f"{args.run_id}__FAILURE_EVIDENCE").exists()


def test_publication_requires_output_disjoint_from_every_input(tmp_path):
    args = _args(tmp_path)
    args.cells = tmp_path
    args.run_identity = si.build_run_identity(args)
    args.execution_provenance = _fake_provenance(args.run_identity)
    args.initial_execution_provenance = args.execution_provenance
    args.final_execution_provenance = args.execution_provenance
    si.issue_publication_capability(args, args.execution_provenance)
    with pytest.raises(si.Blocked, match="disjoint from every input"):
        si.publish(args, json.loads(SPEC.read_text()),
                   _fake_failure_outputs(), si.FAILURE_PUBLICATION)
    assert not (tmp_path / f"{args.run_id}__FAILURE_EVIDENCE").exists()


def test_runtime_authentication_rejects_import_affecting_environment(monkeypatch):
    monkeypatch.setenv("PYTHONPATH", "/tmp/injected")
    with pytest.raises(si.Blocked, match="import-affecting"):
        si.execution_runtime_authentication()


def test_numpy_2_5_vstack_probe_and_no_removed_row_stack(monkeypatch):
    analysis = copy.deepcopy(A1_ANALYSIS)
    analysis["software"]["runtime_contract"]["payload"]["packages"]["numpy"] = "2.5.1"
    monkeypatch.setattr(si.np, "__version__", "2.5.1")
    observed = si.numpy_2_5_structural_probe(analysis)
    assert observed["status"] == "PASS_NUMPY_2_5_VSTACK_STRUCTURAL_PROBE"
    assert observed["constructor"] == "numpy.vstack"
    assert "np.row_stack" not in RUNNER.read_text()


def test_hash_pinned_a1_and_independent_runtime_contract_are_both_required(monkeypatch):
    expected = A1_ANALYSIS["software"]["runtime_contract"]
    runtime = {"status": "AUTHENTICATED_ISOLATED_PINNED_EXECUTABLES"}
    calls = []
    class FakeA1:
        @staticmethod
        def execution_runtime_authentication():
            calls.append("execution_runtime_authentication")
            return runtime

        @staticmethod
        def verify_runtime_contract(_analysis):
            calls.append("verify_runtime_contract")
            return {"payload": expected["payload"],
                    "payload_sha256": expected["payload_sha256"]}

    monkeypatch.setattr(si, "independent_runtime_payload", lambda: expected["payload"])
    monkeypatch.setattr(si, "execution_runtime_authentication", lambda: runtime)
    monkeypatch.setattr(si, "numpy_2_5_structural_probe", lambda _:
        {"status": "PASS_NUMPY_2_5_VSTACK_STRUCTURAL_PROBE"})
    observed = si.verify_signed_a1_runtime_contract(FakeA1, A1_ANALYSIS)
    assert calls == ["execution_runtime_authentication", "verify_runtime_contract"]
    assert observed["independently_recomputed_payload_sha256"] == \
        si.EXPECTED_A1_RUNTIME_PAYLOAD_SHA256


def test_hash_pinned_a1_artifact_safety_module_binding_is_exact():
    module, evidence = si.verify_artifact_safety_binding(A1, A1_ANALYSIS, A1_RUNNER)
    expected_path = A1_RUNNER.with_name("artifact_safety.py").resolve(strict=True)
    assert pathlib.Path(module.__file__).resolve(strict=True) == expected_path
    assert si.sha256_file(expected_path) == \
        A1_ANALYSIS["software"]["artifact_safety_sha256"]
    assert evidence["status"] == "PASS_HASH_PINNED_A1_ARTIFACT_SAFETY"


def test_pre_execution_authorization_is_required_and_fail_closed(tmp_path):
    with pytest.raises(si.Blocked, match="absent, indirect, or misplaced"):
        si.validate_pre_execution_authorization(
            tmp_path / "missing.json", tmp_path, json.loads(SPEC.read_text()), {})


def test_authorization_lifetime_and_issue_age_are_each_capped_at_24_hours():
    now = datetime(2026, 9, 7, 12, tzinfo=timezone.utc)
    boundary = {"issued_at_utc": (now-timedelta(hours=24)).isoformat(),
                "not_before_utc": (now-timedelta(hours=24)).isoformat(),
                "not_after_utc": now.isoformat()}
    *_, lifetime = si.validate_authorization_window(boundary, now)
    assert lifetime == timedelta(hours=24)

    overlong = {"issued_at_utc": (now-timedelta(hours=1)).isoformat(),
                "not_before_utc": (now-timedelta(hours=1)).isoformat(),
                "not_after_utc": (now+timedelta(hours=23, seconds=1)).isoformat()}
    with pytest.raises(si.Blocked, match="authorized time window"):
        si.validate_authorization_window(overlong, now)

    stale_issue = {"issued_at_utc": (now-timedelta(hours=25)).isoformat(),
                   "not_before_utc": (now-timedelta(hours=23)).isoformat(),
                   "not_after_utc": (now+timedelta(hours=1)).isoformat()}
    with pytest.raises(si.Blocked, match="authorized time window"):
        si.validate_authorization_window(stale_issue, now)


def test_runtime_and_final_state_bindings_are_exactly_pinned_in_spec_and_runner():
    frozen = json.loads(SPEC.read_text())
    contract = frozen["runtime_and_authorization"]
    assert contract["python_resolved_executable_sha256"] == si.EXPECTED_PYTHON_RESOLVED_SHA256
    assert contract["git_resolved_executable_sha256"] == si.EXPECTED_GIT_SHA256
    assert contract["git_version"] == si.EXPECTED_GIT_VERSION
    assert contract["a1_runtime_payload_sha256"] == si.EXPECTED_A1_RUNTIME_PAYLOAD_SHA256
    assert contract["status_at_freeze"].startswith("PENDING_EXACT_CLEAN_IMPLEMENTATION_COMMIT")
    source = RUNNER.read_text()
    runtime_index = source.index("runtime_contract = verify_signed_a1_runtime_contract")
    authenticate_index = source.index("canonical, analysis, a1_audit, membership, cells")
    assert runtime_index < authenticate_index
    assert source.count("execution_provenance(") >= 4


def test_post_certification_failure_is_sanitized_and_nonauthoritative(monkeypatch, tmp_path):
    args = _args(tmp_path)
    spec = json.loads(SPEC.read_text())
    def fail_after_certification(_argv):
        si.POST_CERTIFICATION_CONTEXT = {"args": args, "spec": spec, "fits": []}
        raise ValueError("private /Users/example token=bad")
    monkeypatch.setattr(si, "_main_impl", fail_after_certification)
    with pytest.raises(si.Blocked, match="nonauthoritative evidence published"):
        si.main([])
    evidence = json.loads((tmp_path / "gate2_support_inference_sge_1__FAILURE_EVIDENCE" /
                           "FAILURE_EVIDENCE.json").read_text())
    assert evidence["failure_stage"] == "POST_CERTIFICATION_PIPELINE"
    assert evidence["scientific_result_claims"] is False
    assert "Users/example" not in json.dumps(evidence) and "token=bad" not in json.dumps(evidence)


def test_authenticated_edge_and_pair_functionals_have_exact_rank_and_weights():
    run = HERE.parent.parent / "runs" / "gate2_support_accounting_authoritative_20260907"
    support = pd.read_csv(run / "SUPPORT_MATRIX.csv", dtype={"family": str})
    edges = pd.read_csv(run / "SUPPORT_EDGES.csv", dtype={"family": str})
    supported = support.loc[support.cell_has_support.map(
        lambda value: str(value).lower() == "true")].copy()
    labels = []
    for family, part in supported.groupby("family", sort=True):
        qs = sorted(part.beta_quintile.astype(int))
        labels.extend([f"family_{str(family).zfill(2)}:Q{q}_vs_Q{min(qs)}_x_post"
                       for q in qs if q != min(qs)])
    labels.append("Webb_z_x_post")
    edge_labels, edge_matrix = si.rebuild_edge_functionals(support, edges, labels)
    assert len(edge_labels) == 89
    assert np.linalg.matrix_rank(edge_matrix, tol=1e-12) == 50
    pair_labels, pair_matrix, weights = si.rebuild_pairwise_aggregate_functionals(
        edges, edge_labels, edge_matrix)
    assert len(pair_labels) == len(pair_matrix) == 10
    assert weights.groupby("functional_label").family_weight.sum().to_dict() == pytest.approx(
        {label: 1. for label in pair_labels})


def test_authenticated_direct_functionals_rebuild_fixed_membership_weights():
    path = HERE.parent.parent / "runs" / "gate2_support_accounting_authoritative_20260907" / \
        "DIRECT_TAIL_MEMBERSHIP.csv"
    direct = pd.read_csv(path, dtype={"family": str, "occupation_code": str})
    coefficient_labels = [f"family_{family}:Q5_vs_Q1_x_post" for family in ["27", "29", "31", "41"]] + [
        "Webb_z_x_post"]
    labels, matrix, weights = si.rebuild_direct_functionals(direct, coefficient_labels)
    assert labels[-1] == "fixed_pre_stock_aggregate"
    assert matrix.shape == (5, 5)
    assert sum(weights.values()) == pytest.approx(1)
    assert np.array_equal(matrix[-1, :4], np.asarray([weights[f] for f in sorted(weights)]))


def test_public_frame_reconstruction_closes_metadata_counts_and_inference_fields():
    expected = pd.DataFrame([{
        "functional_label": "Q5_vs_Q1_fixed_pair_stock",
        "eligible_family_count": 4,
        "estimate_source": "trust-path",
        "estimate": -0.1,
        "standard_error": 0.02,
        "z": -5.0,
        "p_value_normal": 1e-6,
        "weight_rule": "fixed_pair_endpoint_preperiod_stock",
    }])
    numeric = ("estimate", "standard_error", "z", "p_value_normal")
    assert si.verify_public_frame_reconstruction(
        "synthetic", expected.copy(), expected, numeric)["pass"]

    altered_count = expected.copy()
    altered_count.loc[0, "eligible_family_count"] = 5
    assert not si.verify_public_frame_reconstruction(
        "synthetic", altered_count, expected, numeric)["pass"]

    altered_inference = expected.copy()
    altered_inference.loc[0, "standard_error"] += 1e-6
    assert not si.verify_public_frame_reconstruction(
        "synthetic", altered_inference, expected, numeric)["pass"]


def test_success_path_has_no_post_commit_stdout_dependency():
    source = RUNNER.read_text()
    assert "print(destination.name)" not in source
    assert "destination = publish(args, spec, outputs)" not in source
