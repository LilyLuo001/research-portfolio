from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


HERE = Path(__file__).resolve().parent
MODULE_PATH = HERE.parent / "run_dynamic_reconciliation.py"
SPEC_PATH = HERE.parent / "DYNAMIC_RECONCILIATION_SPEC.json"
LOADER = importlib.util.spec_from_file_location("gate2_dynamic_reconciliation", MODULE_PATH)
assert LOADER and LOADER.loader
DYN = importlib.util.module_from_spec(LOADER)
LOADER.loader.exec_module(DYN)
ROOT = HERE.parents[2]


def signed_spec() -> dict:
    return DYN.load_json(SPEC_PATH)


def test_signed_spec_and_calendar_freeze_exact_observed_month_weights():
    spec = signed_spec()
    DYN.validate_spec(spec, MODULE_PATH)
    calendar = DYN.calendar_contract(spec)
    assert len(calendar["pre_months"]) == 71
    assert len(calendar["post_months"]) == 42
    assert len(calendar["fit_months"]) == 113
    assert calendar["reference_months"] == ["2022-10", "2022-11"]
    assert "2022-12" not in calendar["fit_months"]
    assert "2025-10" not in calendar["observed_months"]
    assert calendar["quarter_month_counts"]["2025Q4"] == 2
    assert calendar["quarter_month_counts"]["2026Q3"] == 1
    weights = DYN.temporal_weights(spec)
    assert np.isclose(sum(weights["pre"].values()), 1.0)
    assert np.isclose(sum(weights["post"].values()), 1.0)
    assert weights["pre"]["2022Q4"] == pytest.approx(2 / 71)
    assert weights["post"]["2025Q4"] == pytest.approx(2 / 42)
    assert weights["post"]["2026Q3"] == pytest.approx(1 / 42)


def test_actual_a1_artifacts_support_point_reconciliation_but_not_inference():
    spec = signed_spec()
    audit = DYN.load_json(
        ROOT / "runs/gate1_numerical_a1_pass_7482383/numerical/MODEL_AUDIT.json"
    )
    release = DYN.load_json(
        ROOT / "runs/gate1_numerical_a1_pass_7482383/DEPENDENCY_RELEASE.json"
    )
    report = DYN.preflight_report(audit, release, spec)
    point = report["point_reconciliation"]
    assert point["status"] == "PASS_CERTIFIED_POINT_RECONCILIATION_ONLY"
    assert point["structures"]["unconditioned"]["S_static"] == pytest.approx(
        -0.1321094507921904
    )
    assert point["structures"]["unconditioned"][
        "P_published_reference_post"
    ] == pytest.approx(-0.11988876533150447, abs=1e-12)
    assert point["structures"]["family_month"]["S_static"] == pytest.approx(
        -0.021674952018246887
    )
    assert point["structures"]["family_month"][
        "P_published_reference_post"
    ] == pytest.approx(-0.20743368917400506, abs=1e-12)
    assert point["conditioning_movements_family_month_minus_unconditioned"][
        "S_static"
    ] > 0
    assert point["conditioning_movements_family_month_minus_unconditioned"][
        "P_published_reference_post"
    ] < 0
    assert report["object_availability"]["full_covariance"] == "MISSING_NOT_FABRICATED"
    assert report["requirement_disposition"]["Y08"].startswith("UNMET")
    assert "16 fresh onset fits" in report["requirement_disposition"]["Y08"]
    assert report["requirement_disposition"]["T05"].startswith("UNMET")
    assert report["authoritative_completion"] is False


def test_every_bound_input_hash_is_checked_and_mutation_fails(tmp_path: Path):
    spec = signed_spec()
    paths = {
        "dependency_release": ROOT / "runs/gate1_numerical_a1_pass_7482383/DEPENDENCY_RELEASE.json",
        "model_audit": ROOT / "runs/gate1_numerical_a1_pass_7482383/numerical/MODEL_AUDIT.json",
        "a1_spec": ROOT / "numerical_existence/ANALYSIS_SPEC_A1.json",
        "canonical_spec": ROOT / "contracts/specs/canonical_baseline_reproduction_v2.json",
        "target_dependency_map": ROOT / "contracts/TARGET_DEPENDENCY_MAP_A1.json",
        "focal_target_source_audit": ROOT / "runs/gate1_numerical_a1_pass_7482383/FOCAL_TARGET_SOURCE_AUDIT.json",
        "execution_prompt": ROOT / "revision_inputs/EXECUTION_PROMPT_V3.md",
        "requirements_seed": ROOT / "revision_inputs/requirements_seed.json",
    }
    DYN.validate_input_hashes(paths, spec)
    changed = tmp_path / "changed.json"
    changed.write_bytes(paths["dependency_release"].read_bytes() + b"\n")
    bad = dict(paths)
    bad["dependency_release"] = changed
    with pytest.raises(DYN.DynamicGateError, match="hash mismatch"):
        DYN.validate_input_hashes(bad, spec)


def test_actual_contract_ids_and_focal_target_sources_are_cross_bound():
    spec = signed_spec()
    audit = DYN.load_json(
        ROOT / "runs/gate1_numerical_a1_pass_7482383/numerical/MODEL_AUDIT.json"
    )
    source = DYN.load_json(
        ROOT / "runs/gate1_numerical_a1_pass_7482383/FOCAL_TARGET_SOURCE_AUDIT.json"
    )
    DYN.validate_contract_metadata(
        DYN.load_json(ROOT / "contracts/specs/canonical_baseline_reproduction_v2.json"),
        DYN.load_json(ROOT / "numerical_existence/ANALYSIS_SPEC_A1.json"),
        DYN.load_json(ROOT / "contracts/TARGET_DEPENDENCY_MAP_A1.json"),
        source,
        audit,
        DYN.load_json(ROOT / "revision_inputs/requirements_seed.json"),
        spec,
    )
    changed = copy.deepcopy(source)
    changed["models"][0]["reported_value"] += 1e-5
    with pytest.raises(DYN.DynamicGateError, match="reported focal target value differs"):
        DYN.validate_contract_metadata(
            DYN.load_json(ROOT / "contracts/specs/canonical_baseline_reproduction_v2.json"),
            DYN.load_json(ROOT / "numerical_existence/ANALYSIS_SPEC_A1.json"),
            DYN.load_json(ROOT / "contracts/TARGET_DEPENDENCY_MAP_A1.json"),
            changed,
            audit,
            DYN.load_json(ROOT / "revision_inputs/requirements_seed.json"),
            spec,
        )


def test_spec_id_and_result_id_bind_content():
    spec = signed_spec()
    assert spec["spec_id"] == DYN.compute_spec_id(spec)
    changed = copy.deepcopy(spec)
    changed["functionals"]["conditioning_movement"] = "changed"
    assert DYN.compute_spec_id(changed) != spec["spec_id"]
    first = DYN.compute_result_id(spec["spec_id"], "x", "0" * 64)
    second = DYN.compute_result_id(spec["spec_id"], "x", "1" * 64)
    assert first.startswith("yaxresult_v1_")
    assert first != second


def test_full_reparameterization_preserves_covariance_influence_and_functional():
    labels = ["2021Q1", "2021Q2", "2021Q3", "2021Q4"]
    old_reference = "2021Q4"
    new_reference = "2021Q2"
    beta = np.array([0.2, -0.1, 0.4])
    influence = np.array([
        [0.10, 0.02, -0.03],
        [-0.04, 0.08, 0.01],
        [0.03, -0.02, 0.06],
        [-0.02, -0.01, -0.04],
    ])
    covariance = influence.T @ influence
    transform = DYN.free_rebase_matrix(labels, old_reference, new_reference)
    beta_new, covariance_new, influence_new = DYN.transform_parameterization(
        beta, covariance, influence, transform
    )
    assert covariance_new is not None and influence_new is not None
    assert np.allclose(covariance_new, influence_new.T @ influence_new)

    expected = np.array([0.3, 0.5, 0.1])
    assert np.allclose(beta_new, expected)

    # A common contrast and its variance are invariant after transforming both
    # coefficients and the full covariance/influence objects.
    l_old = np.array([1.0, -0.5, -0.5])
    l_new = np.linalg.solve(transform.T, l_old)
    assert l_old @ beta == pytest.approx(l_new @ beta_new)
    assert l_old @ covariance @ l_old == pytest.approx(l_new @ covariance_new @ l_new)
    assert np.allclose(influence @ l_old, influence_new @ l_new)

    restrictions = np.array([[1.0, -1.0, 0.0], [0.0, 1.0, -1.0]])
    equivalent = DYN.verify_equivalent_linear_reparameterization(
        beta, restrictions, transform, covariance, influence
    )
    assert equivalent["status"] == "PASS_EQUIVALENT_GENERIC_LINEAR_REPARAMETERIZATION"
    assert equivalent["uncertainty_objects_checked"] is True
    assert equivalent["maximum_absolute_target_difference"] <= 1e-12
    assert equivalent["maximum_absolute_covariance_difference"] <= 1e-12
    assert equivalent["maximum_absolute_influence_difference"] <= 1e-12
    assert equivalent["maximum_relative_target_difference"] <= 1e-12
    assert equivalent["maximum_relative_covariance_difference"] <= 1e-12
    assert equivalent["maximum_relative_influence_difference"] <= 1e-12

    rebased = DYN.verify_equivalent_reference_rebase(
        beta,
        restrictions,
        labels,
        old_reference,
        new_reference,
        transform=transform,
        covariance=covariance,
        influence=influence,
    )
    assert rebased["status"] == "PASS_EQUIVALENT_REFERENCE_REBASE_RESTRICTIONS"
    assert rebased["old_reference"] == old_reference
    assert rebased["new_reference"] == new_reference
    assert rebased["maximum_absolute_supplied_transform_difference"] == 0.0
    assert rebased["transform_used"] == "EXACT_LABEL_DERIVED_FREE_REBASE_MATRIX"


@pytest.mark.parametrize(
    "bad_transform",
    [
        pytest.param(2.0 * np.eye(3), id="twice_identity"),
        pytest.param(np.eye(3)[[1, 0, 2]], id="permutation"),
        pytest.param(np.diag([-1.0, 1.0, 1.0]), id="sign_change"),
        pytest.param(
            np.random.default_rng(20260907).normal(size=(3, 3)),
            id="random_nonsingular",
        ),
    ],
)
def test_reference_rebase_rejects_invertible_but_semantically_wrong_transform(
    bad_transform: np.ndarray,
):
    labels = ["2021Q1", "2021Q2", "2021Q3", "2021Q4"]
    assert abs(np.linalg.det(bad_transform)) > 1e-8
    with pytest.raises(
        DYN.DynamicGateError,
        match="does not equal unique reference-rebase map",
    ):
        DYN.verify_equivalent_reference_rebase(
            np.array([0.2, -0.1, 0.4]),
            np.array([[1.0, -1.0, 0.0], [0.0, 1.0, -1.0]]),
            labels,
            "2021Q4",
            "2021Q2",
            transform=bad_transform,
        )


def test_reference_rebase_accepts_randomized_correct_old_new_reference_pairs():
    rng = np.random.default_rng(20260907)
    labels = [f"202{i}Q{q}" for i in range(1, 3) for q in range(1, 5)]
    for _ in range(32):
        old_reference, new_reference = rng.choice(labels, size=2, replace=False)
        beta = rng.normal(size=len(labels) - 1)
        restrictions = rng.normal(size=(4, len(labels) - 1))
        expected = DYN.free_rebase_matrix(labels, old_reference, new_reference)
        result = DYN.verify_equivalent_reference_rebase(
            beta,
            restrictions,
            labels,
            old_reference,
            new_reference,
            transform=expected,
        )
        assert result["status"] == "PASS_EQUIVALENT_REFERENCE_REBASE_RESTRICTIONS"
        assert result["maximum_absolute_supplied_transform_difference"] == 0.0
        assert result["maximum_relative_target_difference"] <= 1e-12


def test_reparameterization_checks_are_invariant_to_coefficient_units():
    labels = ["2021Q1", "2021Q2", "2021Q3", "2021Q4"]
    transform = DYN.free_rebase_matrix(labels, "2021Q4", "2021Q2")
    beta = np.array([0.2, -0.1, 0.4])
    influence = np.array([
        [0.10, 0.02, -0.03],
        [-0.04, 0.08, 0.01],
        [0.03, -0.02, 0.06],
        [-0.02, -0.01, -0.04],
    ])
    restrictions = np.array([[1.0, -1.0, 0.0], [0.0, 1.0, -1.0]])
    for scale in (1e-6, 1.0, 1e4):
        scaled_beta = beta * scale
        scaled_influence = influence * scale
        result = DYN.verify_equivalent_reference_rebase(
            scaled_beta,
            restrictions,
            labels,
            "2021Q4",
            "2021Q2",
            transform=transform,
            covariance=scaled_influence.T @ scaled_influence,
            influence=scaled_influence,
        )
        assert result["maximum_relative_target_difference"] <= 1e-12
        assert result["maximum_relative_covariance_difference"] <= 1e-12
        assert result["maximum_relative_influence_difference"] <= 1e-12


def test_reference_invariant_D_but_published_reference_P_moves():
    labels = ["2022Q1", "2022Q2", "2022Q3", "2022Q4", "2023Q1", "2023Q2"]
    values = np.array([0.1, 0.2, -0.1, 0.0, -0.3, -0.2])
    pre = {label: 0.25 for label in labels[:4]}
    post = {label: 0.5 for label in labels[4:]}
    result = DYN.verify_reference_invariance(values, labels, pre, post)
    assert result["status"] == "PASS_COEFFICIENT_REFERENCE_INVARIANCE"
    assert result["maximum_absolute_rebase_difference"] <= 1e-12
    published_old = (values[4] + values[5]) / 2
    rebased = values - values[1]
    published_new = (rebased[4] + rebased[5]) / 2
    assert published_new != pytest.approx(published_old)


def test_exact_nesting_score_and_pseudo_stock_projection():
    x_dynamic = np.array([
        [1.0, 0.0, 0.0],
        [1.0, 1.0, 0.0],
        [1.0, 0.0, 1.0],
        [1.0, 1.0, 1.0],
        [1.0, 2.0, -1.0],
        [1.0, -1.0, 2.0],
    ])
    mapping = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 0.5]])
    x_static = x_dynamic @ mapping
    nesting = DYN.validate_design_nesting(x_static, x_dynamic, mapping)
    assert nesting["status"] == "PASS_EXACT_DESIGN_NESTING"
    beta = np.array([-0.2, 0.35])
    total = np.repeat(100.0, len(x_static))
    probability = DYN._sigmoid(x_static @ beta)
    young = total * probability
    score = DYN.validate_static_score_moment(
        x_static, young, total, probability, tolerance=1e-12
    )
    assert score["maximum_score_per_total"] <= 1e-12
    projection = DYN.validate_pseudo_stock_projection(
        x_static, total, probability, beta, [1], target_tolerance=1e-10
    )
    assert projection["status"] == "PASS_PSEUDO_STOCK_STATIC_TARGET_PROJECTION"
    assert projection["maximum_absolute_target_difference"] <= 1e-10
    broken = x_static.copy()
    broken[0, 1] += 0.1
    with pytest.raises(DYN.DynamicGateError, match="nesting failed"):
        DYN.validate_design_nesting(broken, x_dynamic, mapping)
    with pytest.raises(DYN.DynamicGateError, match="predeclared mapping"):
        DYN.validate_design_nesting(x_static, x_dynamic)


def test_nesting_uses_per_column_relative_residuals():
    x_dynamic = np.eye(2)
    x_static = np.array([[1e-12, 0.0], [0.0, 1e6]])
    mapping = x_static.copy()
    result = DYN.validate_design_nesting(x_static, x_dynamic, mapping, tolerance=1e-12)
    assert np.array_equal(result["column_scales"], np.array([1e-12, 1e6]))
    broken = mapping.copy()
    broken[0, 0] += 1e-20
    with pytest.raises(DYN.DynamicGateError, match="nesting failed"):
        DYN.validate_design_nesting(x_static, x_dynamic, broken, tolerance=1e-10)


def test_y04_builds_both_nulls_with_declared_rank_and_counts():
    labels = [f"{year}Q{quarter}" for year in range(2017, 2023) for quarter in range(1, 5)]
    labels.remove("2022Q4")
    blocks = DYN.build_y04_restrictions(labels, DYN.EXPECTED_PRETREND_WINDOWS)
    assert blocks["full_preperiod"]["reference_restrictions"] == 23
    assert blocks["full_preperiod"]["within_restrictions"] == 22
    assert blocks["2017Q1_2019Q4"]["reference_restrictions"] == 12
    assert blocks["2017Q1_2019Q4"]["within_restrictions"] == 11
    assert blocks["2021Q1_2022Q3"]["reference_restrictions"] == 7
    assert blocks["full_excluding_2020Q2_2020Q4"]["reference_restrictions"] == 20
    for row in blocks.values():
        assert row["reference_matrix_rank"] == row["reference_restrictions"]
        assert row["within_matrix_rank"] == row["within_restrictions"]


def test_rank_aware_wald_uses_covariance_rank_not_restriction_count():
    beta = np.array([0.2, 0.2, 0.2])
    covariance = np.ones((3, 3))
    restrictions = np.eye(3)
    result = DYN.rank_aware_wald(beta, covariance, restrictions)
    assert result["restriction_rows"] == 3
    assert result["restricted_covariance_rank"] == 1
    assert result["degrees_of_freedom"] == 1
    assert result["rank_deficient"] is True
    assert result["single_eigendecomposition_used"] is True
    assert result["retained_eigenvalue_count"] == result["degrees_of_freedom"]
    assert len(result["covariance_null_space_target_component"]) == 3
    assert result["covariance_null_space_target_component_l2"] >= 0
    assert result["target_in_estimable_covariance_range"] is True
    assert result["target_range_residual_relative"] <= result[
        "target_range_relative_tolerance"
    ]
    assert result["wald_statistic"] >= 0
    assert result["p_value"] is None


def test_rank_aware_wald_blocks_material_target_outside_covariance_range():
    with pytest.raises(
        DYN.DynamicGateError,
        match="BLOCKED_TARGET_OUTSIDE_ESTIMABLE_COVARIANCE_RANGE",
    ):
        DYN.rank_aware_wald(
            np.array([0.2, -0.1, 0.3]), np.ones((3, 3)), np.eye(3)
        )


def test_rank_aware_wald_allows_roundoff_range_residual_and_is_scale_invariant():
    beta = np.array([0.2, 0.2 + 1e-8, 0.2 - 1e-8])
    covariance = np.ones((3, 3))
    baseline = DYN.rank_aware_wald(beta, covariance, np.eye(3))
    scale = 1e-9
    rescaled = DYN.rank_aware_wald(
        beta * scale, covariance * scale ** 2, np.eye(3)
    )
    assert baseline["target_range_residual_relative"] == pytest.approx(
        rescaled["target_range_residual_relative"], rel=1e-8, abs=1e-18
    )
    assert baseline["wald_statistic"] == pytest.approx(rescaled["wald_statistic"])
    assert baseline["degrees_of_freedom"] == rescaled["degrees_of_freedom"] == 1


def test_rank_aware_wald_is_rescaling_invariant_and_retains_small_covariance():
    beta = np.array([0.2, -0.15])
    covariance = np.array([[4e-8, 1e-8], [1e-8, 9e-8]])
    restrictions = np.eye(2)
    baseline = DYN.rank_aware_wald(beta, covariance, restrictions)
    multiplier = 1e-16
    scaled = DYN.rank_aware_wald(
        beta * np.sqrt(multiplier), covariance * multiplier, restrictions
    )
    assert baseline["wald_statistic"] == pytest.approx(scaled["wald_statistic"])
    assert baseline["restricted_covariance_rank"] == scaled["restricted_covariance_rank"] == 2
    assert scaled["restricted_covariance_spectral_scale"] < 1e-20
    assert scaled["restricted_covariance_eigenvalue_cutoff"] == pytest.approx(
        1e-10 * scaled["restricted_covariance_spectral_scale"]
    )

    tiny = DYN.rank_aware_wald(
        np.array([1e-12, -2e-12]), np.diag([1e-24, 2e-24]), np.eye(2)
    )
    assert tiny["restricted_covariance_rank"] == 2
    assert np.isfinite(tiny["wald_statistic"])


@pytest.mark.parametrize(
    "covariance, message",
    [
        (np.array([[1.0, 0.2], [0.1, 1.0]]), "symmetric"),
        (np.array([[1.0, 0.0], [0.0, -0.1]]), "positive semidefinite"),
        (np.array([[1.0, np.nan], [np.nan, 1.0]]), "finite"),
    ],
)
def test_rank_aware_wald_rejects_invalid_restricted_covariance(covariance, message):
    with pytest.raises(DYN.DynamicGateError, match=message):
        DYN.rank_aware_wald(np.array([0.1, -0.1]), covariance, np.eye(2))


def test_y05_simultaneous_and_leave_label_diagnostics_use_common_draws():
    beta = np.array([0.1, -0.2, 0.05])
    influence = np.array([
        [0.10, 0.00, 0.02],
        [-0.05, 0.08, -0.01],
        [0.02, -0.04, 0.05],
        [-0.03, -0.04, -0.06],
    ])
    signs = np.array([
        [1, 1, 1, 1], [1, -1, 1, -1], [-1, 1, -1, 1], [-1, -1, -1, -1]
    ])
    with pytest.raises(DYN.DynamicGateError, match="too few common multiplier draws"):
        DYN.simultaneous_intervals(beta, influence, signs)
    rng = np.random.default_rng(20260907)
    signs = rng.choice(np.array([-1.0, 1.0]), size=(9999, influence.shape[0]))
    intervals = DYN.simultaneous_intervals(beta, influence, signs)
    assert intervals["common_draws_used"] is True
    assert intervals["draws"] == 9999
    assert intervals["minimum_draws"] == 9999
    assert intervals["achieved_quantile_order_statistic_index_zero_based"] == 9499
    assert intervals["achieved_empirical_coverage"] >= 0.95
    assert np.all(intervals["lower"] <= intervals["upper"])
    covariance = influence.T @ influence
    rows = DYN.leave_one_label_out_diagnostics(
        beta, covariance, ["a", "b", "c"], ["a", "b", "c"],
        "equality_to_reference",
    )
    assert len(rows) == 3
    assert all(row["rebuilt_restriction_rows"] == 2 for row in rows)
    assert all("not_additive_contribution" in next(
        key for key in row if "not_additive_contribution" in key
    ) for row in rows)


def test_leave_one_label_rebuilds_within_block_null_when_anchor_is_omitted():
    labels = ["a", "b", "c", "d"]
    beta = np.array([0.1, 0.2, -0.1, 0.0])
    covariance = np.diag([0.04, 0.05, 0.06, 0.07])
    rows = DYN.leave_one_label_out_diagnostics(
        beta, covariance, labels, ["a", "b", "c"], "equality_within_block"
    )
    anchor_omitted = next(row for row in rows if row["omitted_label"] == "a")
    assert anchor_omitted["full_anchor"] == "a"
    assert anchor_omitted["rebuilt_anchor"] == "b"
    assert anchor_omitted["remaining_labels"] == ["b", "c"]
    assert np.array_equal(
        anchor_omitted["rebuilt_restriction_matrix"],
        np.array([[0.0, -1.0, 1.0, 0.0]]),
    )
    assert anchor_omitted["rebuilt_restriction_rows"] == 1


@pytest.mark.parametrize("field", ["design", "young", "total", "probability"])
def test_score_moment_rejects_nonfinite_objects(field):
    values = {
        "design": np.array([[1.0], [1.0]]),
        "young": np.array([1.0, 1.0]),
        "total": np.array([2.0, 2.0]),
        "probability": np.array([0.5, 0.5]),
    }
    values[field] = values[field].copy()
    values[field].flat[0] = np.nan
    with pytest.raises(DYN.DynamicGateError, match="must be finite"):
        DYN.validate_static_score_moment(
            values["design"], values["young"], values["total"],
            values["probability"], tolerance=1e-12,
        )


@pytest.mark.parametrize("field", ["design", "pseudo_young", "total", "start"])
def test_projection_fit_rejects_nonfinite_objects(field):
    values = {
        "design": np.array([[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]]),
        "pseudo_young": np.array([1.0, 1.5, 2.0]),
        "total": np.array([3.0, 3.0, 3.0]),
        "start": np.array([0.0, 0.0]),
    }
    values[field] = values[field].copy()
    values[field].flat[0] = np.inf
    with pytest.raises(DYN.DynamicGateError, match="must be finite"):
        DYN.fit_grouped_logit_projection(
            values["design"], values["pseudo_young"], values["total"],
            start=values["start"],
        )


def test_pseudo_stock_wrapper_rejects_nonfinite_probability_before_multiplication():
    with pytest.raises(DYN.DynamicGateError, match="must be finite"):
        DYN.validate_pseudo_stock_projection(
            np.array([[1.0], [1.0]]), np.array([2.0, 2.0]),
            np.array([0.5, np.nan]), np.array([0.0]), [0],
        )


def test_output_basename_is_frozen_and_result_key_uses_that_name(tmp_path: Path):
    spec = signed_spec()
    declared = tmp_path / "DYNAMIC_PREFLIGHT_REPORT.json"
    assert DYN.validate_output_path(declared, spec) == declared.name
    with pytest.raises(DYN.DynamicGateError, match="basename differs"):
        DYN.validate_output_path(tmp_path / "other.json", spec)
    artifact_hash = "a" * 64
    result_id = DYN.compute_result_id(spec["spec_id"], declared.name, artifact_hash)
    assert result_id != DYN.compute_result_id(spec["spec_id"], "other.json", artifact_hash)


def test_resealed_behavior_mutations_fail_semantic_validation():
    mutations = []
    changed = copy.deepcopy(signed_spec())
    changed["tolerances"]["target_absolute"] = 2e-6
    mutations.append((changed, "tolerances"))
    changed = copy.deepcopy(signed_spec())
    changed["tolerances"]["target_range_relative"] = 2e-5
    mutations.append((changed, "tolerances"))
    changed = copy.deepcopy(signed_spec())
    changed["tolerances"]["reparameterization_relative"] = 2e-12
    mutations.append((changed, "tolerances"))
    changed = copy.deepcopy(signed_spec())
    changed["tolerances"]["reference_rebase_transform_absolute"] = 2e-12
    mutations.append((changed, "tolerances"))
    changed = copy.deepcopy(signed_spec())
    changed["reparameterization"]["reference_rebase_transform_tolerance"] = \
        "reparameterization_relative"
    mutations.append((changed, "reparameterization semantics"))
    changed = copy.deepcopy(signed_spec())
    changed["nesting"]["available_now"] = True
    mutations.append((changed, "availability"))
    changed = copy.deepcopy(signed_spec())
    changed["pretrend"]["windows"]["full_excluding_2020Q2_2020Q4"][
        "excluded_quarters"
    ] = ["2020Q2", "2020Q3"]
    mutations.append((changed, "pretrend windows"))
    changed = copy.deepcopy(signed_spec())
    changed["execution"]["mode"] = "authoritative"
    mutations.append((changed, "execution mode"))
    changed = copy.deepcopy(signed_spec())
    changed["outputs"]["authoritative_output_forbidden_before_object_amendment"] = False
    mutations.append((changed, "output guard"))
    changed = copy.deepcopy(signed_spec())
    changed["requirements"]["Y08"] = "VERIFIED"
    mutations.append((changed, "requirement dispositions"))
    changed = copy.deepcopy(signed_spec())
    changed["execution"]["production_runtime_pin"] = "invented"
    mutations.append((changed, "runtime pin"))
    for changed, message in mutations:
        changed["spec_id"] = DYN.compute_spec_id(changed)
        with pytest.raises(DYN.DynamicGateError, match=message):
            DYN.validate_spec(changed, MODULE_PATH)


def test_covariance_without_influence_is_rejected_not_fabricated():
    with pytest.raises(DYN.DynamicGateError, match="supplied together"):
        DYN.transform_parameterization(
            np.array([1.0, 2.0]), np.eye(2), None, np.eye(2)
        )


def test_duplicate_json_keys_fail_closed(tmp_path: Path):
    path = tmp_path / "duplicate.json"
    path.write_text('{"a": 1, "a": 2}', encoding="utf-8")
    with pytest.raises(DYN.DynamicGateError, match="duplicate JSON key"):
        DYN.load_json(path)
