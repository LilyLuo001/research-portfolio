#!/usr/bin/env python3
"""Synthetic-data tests for the V3 N01--N03 numerical audit."""
from __future__ import annotations

import importlib.util
import copy
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.special import expit


HERE = pathlib.Path(__file__).resolve().parent
MODULE_PATH = HERE / "run_numerical_existence_audit.py"
SPEC = importlib.util.spec_from_file_location("yax_v3_numerical_audit", MODULE_PATH)
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


def bundle(
    young,
    total,
    first,
    second,
    regressors=None,
    label="target",
):
    young = np.asarray(young, float)
    total = np.asarray(total, float)
    n = len(young)
    if regressors is None:
        regressors = np.arange(n, dtype=float).reshape(-1, 1)
    frame = pd.DataFrame({
        "family": ["11"] * n,
        "month": [f"2023-{index + 1:02d}" for index in range(n)],
        "young": young,
        "older": total - young,
    })
    return AUDIT.ModelBundle(
        model_id="synthetic",
        frame=frame,
        young=young,
        total=total,
        first_labels=np.asarray(first, object),
        second_labels=np.asarray(second, object),
        regressors=np.asarray(regressors, float),
        regressor_labels=[label],
        focal_target_label=label,
    )


class BoundaryTests(unittest.TestCase):
    def test_one_sided_cell_is_retained_when_neither_fe_group_is_boundary(self):
        model = bundle(
            young=[0, 5, 4, 5],
            total=[10, 10, 10, 10],
            first=["a", "a", "b", "b"],
            second=["m1", "m2", "m1", "m2"],
        )
        active, records = AUDIT.profile_boundary_nuisance(model)
        self.assertTrue(active.all())
        self.assertEqual(records, [])

    def test_all_zero_nuisance_group_is_profiled_and_recorded(self):
        model = bundle(
            young=[0, 0, 4, 5, 5, 6],
            total=[10] * 6,
            first=["boundary", "boundary", "b", "b", "c", "c"],
            second=["m1", "m2", "m1", "m2", "m1", "m2"],
        )
        active, records = AUDIT.profile_boundary_nuisance(model)
        self.assertEqual(int(active.sum()), 4)
        self.assertTrue(all(not active[index] for index in (0, 1)))
        hit = [row for row in records if row["group"] == "boundary"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["boundary_side"], "zero_young")

    def test_all_older_nuisance_group_is_profiled_and_recorded(self):
        model = bundle(
            young=[10, 10, 4, 5, 5, 6],
            total=[10] * 6,
            first=["boundary", "boundary", "b", "b", "c", "c"],
            second=["m1", "m2", "m1", "m2", "m1", "m2"],
        )
        active, records = AUDIT.profile_boundary_nuisance(model)
        self.assertEqual(int(active.sum()), 4)
        hit = [row for row in records if row["group"] == "boundary"]
        self.assertEqual(len(hit), 1)
        self.assertEqual(hit[0]["boundary_side"], "zero_older")

    def test_boundary_profiling_cascades_after_opposite_side_groups_leave(self):
        model = bundle(
            young=[0, 0, 10, 10, 0, 5],
            total=[10] * 6,
            first=["a", "a", "c", "c", "b", "b"],
            second=["m1", "m2", "m1", "m2", "m1", "m2"],
        )
        active, records = AUDIT.profile_boundary_nuisance(model)
        self.assertEqual(int(active.sum()), 1)
        self.assertTrue(active[5])
        self.assertGreaterEqual(max(row["iteration"] for row in records), 2)
        self.assertTrue(any(row["group"] == "m1" and row["iteration"] == 2 for row in records))

    def test_zero_total_has_no_likelihood_role_and_is_not_called_boundary_profile(self):
        model = bundle(
            young=[0, 4, 5, 6],
            total=[0, 10, 10, 10],
            first=["a", "a", "b", "b"],
            second=["m1", "m2", "m1", "m2"],
        )
        active, _ = AUDIT.profile_boundary_nuisance(model)
        self.assertFalse(active[0])


class GraphAndSeparationTests(unittest.TestCase):
    def test_disconnected_graph_gets_one_normalization_per_component(self):
        model = bundle(
            young=[4, 6], total=[10, 10],
            first=["a", "b"], second=["x", "y"],
            regressors=np.array([[0.0], [1.0]]),
        )
        design = AUDIT.make_sparse_design(model, np.ones(2, dtype=bool))
        self.assertEqual(design.component_count, 2)
        self.assertEqual(design.nuisance.shape[1], 2 + 2 - 2)
        self.assertEqual(np.linalg.matrix_rank(design.nuisance.toarray()), 2)

    def test_lp_detects_target_separation(self):
        design = sparse.csr_matrix(np.array([[1.0], [-1.0]]))
        result = AUDIT.separation_lp(
            design,
            young=np.array([1.0, 0.0]),
            total=np.array([1.0, 1.0]),
            focal_column=0,
            margin_tolerance=1e-9,
        )
        self.assertTrue(result["separation_exists"])
        self.assertTrue(result["focal_target_can_move"])
        self.assertEqual(result["separation_type"], "COMPLETE")
        self.assertEqual(result["strictly_separated_boundary_rows"], 2)

    def test_lp_classifies_quasi_separation_with_an_interior_zero_row(self):
        design = sparse.csr_matrix(np.array([[1.0], [-1.0], [0.0]]))
        result = AUDIT.separation_lp(
            design,
            young=np.array([1.0, 0.0, 1.0]),
            total=np.array([1.0, 1.0, 2.0]),
            focal_column=0,
            margin_tolerance=1e-9,
        )
        self.assertTrue(result["separation_exists"])
        self.assertEqual(result["separation_type"], "QUASI")
        self.assertEqual(result["strictly_separated_boundary_rows"], 2)

    def test_lp_rejects_separation_with_interior_rows(self):
        design = sparse.csr_matrix(np.array([[1.0], [-1.0], [2.0]]))
        result = AUDIT.separation_lp(
            design,
            young=np.array([1.0, 0.0, 1.0]),
            total=np.array([1.0, 1.0, 2.0]),
            focal_column=0,
            margin_tolerance=1e-9,
        )
        self.assertFalse(result["separation_exists"])

    def test_direct_target_lp_finds_lower_gain_target_direction(self):
        count = 20
        design = sparse.csr_matrix(np.vstack([
            np.tile([1.0, -1.0], (count, 1)),
            [0.0, 1.0],
        ]))
        result = AUDIT.separation_lp(
            design,
            young=np.ones(count + 1),
            total=np.ones(count + 1),
            focal_column=1,
            margin_tolerance=1e-9,
        )
        self.assertTrue(result["separation_exists"])
        self.assertTrue(result["focal_target_can_move"])
        self.assertAlmostEqual(result["maximum_gain_direction_focal_component"], 0.0)
        self.assertEqual(
            result["positive_focal_direction"]["status"],
            "FEASIBLE_TARGET_MOVING_RECESSION",
        )
        self.assertTrue(result["positive_focal_direction"]["primal_certificate"]["passed"])

    def test_nearly_dependent_interior_constraints_cannot_false_certify_separation(self):
        for epsilon in (1e-8, 1e-9):
            design = sparse.csr_matrix(np.array([
                [1.0, 0.0], [1.0, epsilon], [1.0, 1.0],
            ]))
            result = AUDIT.separation_lp(
                design,
                young=np.array([0.5, 0.5, 1.0]),
                total=np.array([1.0, 1.0, 1.0]),
                focal_column=1,
                margin_tolerance=1e-9,
            )
            self.assertIsNot(result.get("separation_exists"), True, epsilon)
            if epsilon == 1e-9:
                self.assertEqual(result["status"], "LP_NUMERICAL_CERTIFICATION_FAILURE")
                self.assertFalse(result["global_primal_certificate"]["passed"])

    def test_target_invariant_separation_is_profiled_to_finite_face(self):
        # Boundary checkerboard is separated by the second regressor.  Four
        # duplicated interior cells identify the focal checkerboard regressor,
        # so the recession direction cannot move the target.
        young = [10, 0, 0, 10, 5, 5, 5, 5]
        total = [10] * 8
        first = ["a", "a", "b", "b"] * 2
        second = ["m1", "m2", "m1", "m2"] * 2
        regressors = np.array([
            [0, 1], [0, -1], [0, -1], [0, 1],
            [1, 0], [-1, 0], [-1, 0], [1, 0],
        ], float)
        model = bundle(young, total, first, second, regressors, label="target")
        model.regressor_labels = ["target", "separating_nuisance_slope"]
        settings = {
            "boundary_and_separation": {"lp_margin_tolerance": 1e-9},
            "tolerances": {"conditioning_rank_relative": 1e-10},
        }
        active, design, face, pruning = AUDIT.resolve_extended_likelihood_face(
            model, settings,
        )
        self.assertEqual(face["status"], "PASS_FINITE_FACE_RESOLVED")
        self.assertEqual(int(active.sum()), 4)
        self.assertIsNotNone(design)
        self.assertEqual(sum(row["reason"] == "target_invariant_recession_face" for row in pruning), 4)
        self.assertTrue(face["geometric_information"]["focal_target_rank_identified"])

    def test_reported_event_target_movement_blocks_focal_only_face_profiling(self):
        design = sparse.csr_matrix(np.array([
            [0, 1], [0, -1], [0, -1], [0, 1],
            [1, 0], [-1, 0], [-1, 0], [1, 0],
        ], float))
        result = AUDIT.separation_lp(
            design,
            young=np.array([10, 0, 0, 10, 5, 5, 5, 5], float),
            total=np.full(8, 10.0),
            focal_column=0,
            margin_tolerance=1e-9,
            additional_target_vectors={"reported_event": np.array([0.0, 1.0])},
        )
        self.assertFalse(result["focal_target_can_move"])
        self.assertTrue(result["any_reported_target_can_move"])
        self.assertTrue(
            result["reported_target_direction_audits"]["reported_event"]["target_can_move"]
        )

    def test_zero_gain_lineality_with_unit_target_is_target_moving(self):
        # The first coordinate strictly separates the boundary row.  The
        # second coordinate leaves every likelihood contribution unchanged,
        # but can diverge; zero gain therefore cannot be treated as a finite
        # target or as an incomplete audit.
        result = AUDIT.separation_lp(
            sparse.csr_matrix(np.array([[1.0, 0.0]])),
            young=np.array([1.0]), total=np.array([1.0]),
            focal_column=1, margin_tolerance=1e-9,
        )
        self.assertTrue(result["separation_exists"])
        self.assertTrue(result["focal_target_direction_audit_complete"])
        self.assertTrue(result["focal_target_can_move"])
        direction = result["positive_focal_direction"]
        self.assertEqual(direction["status"], "FEASIBLE_TARGET_MOVING_RECESSION")
        self.assertTrue(direction["zero_gain_lineality_is_target_moving"])


class ObjectiveTests(unittest.TestCase):
    def test_two_unclipped_solvers_match_same_objective(self):
        x = np.linspace(-1.5, 1.5, 80)
        design = sparse.csr_matrix(np.column_stack([np.ones(len(x)), x]))
        total = np.full(len(x), 40.0)
        true = np.array([-0.4, 0.7])
        young = total * expit(design @ true)
        objective = AUDIT.BinomialObjective(design, young, total)
        left = AUDIT.fit_exact_solver(
            objective, "L-BFGS-B", np.zeros(2), 1000, 1e-7, 1e-4, 1,
        )
        right = AUDIT.fit_exact_solver(
            objective, "trust-ncg", np.zeros(2), 1000, 1e-7, 1e-4, 1,
        )
        comparison = AUDIT.compare_solvers(
            left[0], left[1], left[2], right[0], right[1], right[2],
            nuisance_columns=1, focal_target=0,
            tolerances={
                "target_coefficient_absolute_difference": 1e-6,
                "fitted_probability_max_abs_difference": 1e-7,
                "objective_difference_per_total": 1e-10,
            },
        )
        self.assertTrue(left[0]["numerically_valid"])
        self.assertTrue(right[0]["numerically_valid"])
        self.assertTrue(comparison["comparison_pass"])
        self.assertAlmostEqual(left[1][1], true[1], places=6)
        self.assertEqual(left[0]["probability_at_or_below_1e_10"], 0)
        self.assertEqual(left[0]["probability_at_or_above_1_minus_1e_10"], 0)

    def test_schur_information_matches_dense_weighted_projection(self):
        nuisance = sparse.csr_matrix(np.array([
            [1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0],
        ]))
        x = np.array([[0.0], [1.0], [0.5], [1.5]])
        weight = np.array([1.0, 2.0, 3.0, 4.0])
        info, residual = AUDIT.schur_information(nuisance, x, weight)
        dense_coef = np.linalg.solve(
            nuisance.toarray().T @ (weight[:, None] * nuisance.toarray()),
            nuisance.toarray().T @ (weight[:, None] * x),
        )
        expected_residual = x - nuisance.toarray() @ dense_coef
        expected = expected_residual.T @ (weight[:, None] * expected_residual)
        np.testing.assert_allclose(residual, expected_residual, rtol=0, atol=1e-12)
        np.testing.assert_allclose(info, expected, rtol=0, atol=1e-12)

    def test_solver_comparison_binds_every_reported_event_target(self):
        diagnostics = {
            "method": "left", "numerically_valid": True,
            "objective_per_total": 0.5,
        }
        right_diagnostics = {
            **diagnostics, "method": "right",
        }
        tolerances = {
            "target_coefficient_absolute_difference": 1e-6,
            "fitted_probability_max_abs_difference": 1e-7,
            "objective_difference_per_total": 1e-10,
        }
        result = AUDIT.compare_solvers(
            diagnostics, np.array([0.0, -0.2, 0.3]), np.array([0.4, 0.6]),
            right_diagnostics, np.array([0.0, -0.2, 0.31]), np.array([0.4, 0.6]),
            nuisance_columns=1, focal_target=0, tolerances=tolerances,
            reported_target_weights={"Q5_x_2023Q1": np.array([0.0, 1.0])},
        )
        self.assertTrue(result["focal_target_absolute_difference"] == 0.0)
        self.assertFalse(result["reported_target_comparison_pass"])
        self.assertFalse(result["comparison_pass"])

    def test_retained_one_sided_cells_have_finite_exact_fit(self):
        x = np.linspace(-2.0, 2.0, 7)
        design = sparse.csr_matrix(np.column_stack([np.ones(len(x)), x]))
        total = np.full(len(x), 10.0)
        young = np.array([0.0, 6.0, 3.0, 5.0, 7.0, 4.0, 10.0])
        objective = AUDIT.BinomialObjective(design, young, total)
        fit = AUDIT.fit_exact_solver(
            objective, "L-BFGS-B", np.zeros(2), 2000, 1e-7, 1e-4, 1,
        )
        self.assertTrue(fit[0]["numerically_valid"])
        self.assertTrue(np.isfinite(fit[1]).all())
        self.assertGreater(fit[2].min(), 0.0)
        self.assertLess(fit[2].max(), 1.0)

    def test_analytic_gradient_and_hessp_match_finite_differences(self):
        rng = np.random.default_rng(514)
        dense = np.column_stack([np.ones(30), rng.normal(size=(30, 3))])
        design = sparse.csr_matrix(dense)
        total = rng.integers(5, 40, size=30).astype(float)
        young = rng.uniform(0.05, 0.95, size=30) * total
        objective = AUDIT.BinomialObjective(design, young, total)
        theta = rng.normal(scale=0.3, size=4)
        direction = rng.normal(size=4)
        epsilon = 1e-6
        numeric_gradient = np.array([
            (
                objective.function(theta + epsilon * np.eye(4)[index]) -
                objective.function(theta - epsilon * np.eye(4)[index])
            ) / (2 * epsilon)
            for index in range(4)
        ])
        numeric_hessp = (
            objective.gradient(theta + epsilon * direction) -
            objective.gradient(theta - epsilon * direction)
        ) / (2 * epsilon)
        np.testing.assert_allclose(objective.gradient(theta), numeric_gradient, rtol=2e-7, atol=2e-9)
        np.testing.assert_allclose(objective.hessp(theta, direction), numeric_hessp, rtol=2e-7, atol=2e-9)

    def test_exact_solver_matches_independent_dense_newton_reference(self):
        rng = np.random.default_rng(1802)
        dense = np.column_stack([np.ones(80), rng.normal(size=(80, 2))])
        total = rng.integers(20, 80, size=80).astype(float)
        truth = np.array([-0.25, 0.55, -0.35])
        young = total * expit(dense @ truth)
        objective = AUDIT.BinomialObjective(sparse.csr_matrix(dense), young, total)
        audited = AUDIT.fit_exact_solver(
            objective, "L-BFGS-B", np.zeros(3), 2000, 1e-9, 1e-6, 1,
        )
        reference = np.zeros(3)
        for _ in range(100):
            probability = expit(dense @ reference)
            score = dense.T @ (total * probability - young)
            weight = total * probability * (1.0 - probability)
            step = np.linalg.solve(dense.T @ (weight[:, None] * dense), score)
            reference -= step
            if np.max(np.abs(step)) < 1e-13:
                break
        np.testing.assert_allclose(audited[1], reference, rtol=0, atol=2e-8)

    def test_full_hessian_diagnostics_match_dense_spectrum(self):
        design = sparse.csr_matrix(np.array([
            [1.0, 0.0, -1.0], [1.0, 1.0, 0.5],
            [0.0, 1.0, 1.5], [1.0, -1.0, 0.25],
        ]))
        weight = np.array([1.0, 2.0, 3.0, 4.0])
        expected = design.toarray().T @ (weight[:, None] * design.toarray())
        eigen = np.linalg.eigvalsh(expected)
        result = AUDIT.full_hessian_diagnostics(design, weight, 3, 1e-12)
        self.assertEqual(result["status"], "PASS_FULL_HESSIAN_SPECTRUM")
        self.assertAlmostEqual(result["smallest_positive_or_extreme_eigenvalue"], eigen[0], places=11)
        self.assertAlmostEqual(result["largest_eigenvalue"], eigen[-1], places=11)

    def test_full_hessian_does_not_discard_a_null_eigenvalue(self):
        design = sparse.csr_matrix(np.array([
            [1.0, 1.0], [1.0, 1.0], [1.0, 1.0],
        ]))
        result = AUDIT.full_hessian_diagnostics(
            design, np.ones(3), expected_rank=1, relative_tolerance=1e-10,
        )
        self.assertEqual(result["rank_deficiency"], 1)
        self.assertEqual(result["status"], "BLOCKED_FULL_HESSIAN_SPECTRUM_FAILURE")
        self.assertLessEqual(
            result["smallest_positive_or_extreme_eigenvalue"],
            result["rank_threshold"],
        )

    def test_rank_reduction_preserves_identified_focal_original_column(self):
        nuisance = sparse.csr_matrix(np.ones((8, 1)))
        focal = np.array([-2, -1, 0, 1, 2, -1.5, 0.5, 1.5], float)
        other = np.array([1, 0, -1, 0, 1, -2, 2, -1], float)
        regressors = np.column_stack([focal, other, 2.0 * other])
        weight = np.arange(1, 9, dtype=float)
        stub = type("Design", (), {"nuisance": nuisance})()
        geometry = AUDIT.information_diagnostics(
            stub, regressors, weight, 0, 1e-10,
        )
        self.assertEqual(geometry["treatment_information_rank"], 2)
        self.assertTrue(geometry["focal_target_rank_identified"])
        selected, audit = AUDIT.select_regressor_basis_preserving_focal(
            nuisance, regressors, weight, 0, geometry,
        )
        self.assertEqual(selected[0], 0)
        self.assertEqual(len(selected), 2)
        self.assertEqual(audit["status"], "EXACT_COLUMN_SPACE_BASIS_WITH_FOCAL_PRESERVED")

    def test_linear_functional_reparameterization_is_exact(self):
        rng = np.random.default_rng(411)
        regressors = rng.normal(size=(20, 4))
        weights = np.array([0.0, 0.25, 0.0, 0.75])
        model = bundle(
            young=np.full(20, 4.0), total=np.full(20, 10.0),
            first=np.repeat(["a", "b"], 10),
            second=np.tile([f"m{i}" for i in range(10)], 2),
            regressors=regressors, label="unused",
        )
        model.regressor_labels = ["a", "b", "c", "d"]
        model.focal_target_label = "weighted_target"
        model.focal_target_weights = weights
        transformed, audit = AUDIT.target_coordinate_bundle(model)
        pivot = audit["pivot_original_column"]
        self.assertEqual(transformed.focal_target, 0)
        np.testing.assert_allclose(
            transformed.regressors[:, 0], regressors[:, pivot] / weights[pivot],
            rtol=0, atol=1e-14,
        )
        beta = rng.normal(size=4)
        gamma = np.linalg.solve(
            np.linalg.lstsq(regressors, transformed.regressors, rcond=None)[0], beta
        )
        np.testing.assert_allclose(transformed.regressors @ gamma, regressors @ beta, atol=1e-11)
        self.assertAlmostEqual(gamma[0], float(weights @ beta), places=11)


class AuthenticationAndSafetyTests(unittest.TestCase):
    def test_receipt_authentication_detects_each_load_bearing_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            cells = pathlib.Path(temporary) / "cells.csv"
            cells.write_text("x\n1\n", encoding="utf-8")
            source_ids = [
                "cps_occupation_exposure_lookup", "computerization_measures_census2018",
                "rule_b_values_census2018", "census_occ2010_to_2018_bridge",
                "first_post_outcome_access_receipt", "ipums_cps_extract_9_wide",
                "ipums_cps_extract_11_march_basic_repair",
                "historical_preperiod_cells",
            ]
            sources = {key: f"hash-{key}" for key in source_ids}
            canonical = {
                "spec_id": "canonical", "data": {"sources": [
                    {"source_id": key, "sha256": value} for key, value in sources.items()
                ]},
                "exposure": {"fixed_membership": {"sha256": "membership"}},
            }
            analysis = {
                "audit_spec_id": "audit", "_loaded_file_sha256": "analysis-sha",
                "software": {
                    "cell_builder_path": "builder.py",
                    "cell_builder_sha256": "builder",
                    "cell_builder_transitive_sha256": "transitive",
                },
                "input_contract": {"cell_builder_execution_contract": {
                    "analysis_spec_path": "analysis.json",
                    "cell_build_spec_path": "cell.json",
                    "command_template": "<SANITIZED COMMAND>",
                    "environment_lock_path": "env.txt",
                    "environment_lock_sha256": "env-sha",
                    "runtime_contract_sha256": "runtime-contract-sha",
                    "runtime_payload": {"python_version": "3.13.8"},
                    "runtime_payload_sha256": "runtime-payload-sha",
                    "git_required_ancestor_commit": "a" * 40,
                    "git_committed_paths": [
                        "builder.py", "cell.json", "analysis.json", "env.txt",
                    ],
                    "runtime_raw_fields": [
                        "YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "WTFINL",
                    ],
                    "runtime_raw_source_ids": [
                        "ipums_cps_extract_9_wide",
                        "ipums_cps_extract_11_march_basic_repair",
                    ],
                    "historical_reference_code_hashes": {"old.py": "old-sha"},
                }},
            }
            receipt = {
                "schema_version": AUDIT.RECEIPT_SCHEMA,
                "status": "PASS_FRESH_AGGREGATE_REBUILD",
                "aggregate_schema_version": AUDIT.CELL_SCHEMA,
                "canonical_spec_id": "canonical",
                "canonical_spec_sha256": AUDIT.CANONICAL_SPEC_SHA256,
                "analysis_spec_id": "audit", "analysis_spec_sha256": "analysis-sha",
                "cells_sha256": AUDIT.sha256_file(cells),
                "builder_code_sha256": "builder",
                "builder_transitive_code_sha256": "transitive",
                "source_hashes": sources,
                "authenticated_source_hashes": {
                    key: value for key, value in sources.items()
                    if key != "historical_preperiod_cells"
                },
                "unread_canonical_source_ids": ["historical_preperiod_cells"],
                "lookup_and_bridge_hashes": {key: sources[key] for key in source_ids[:5]},
                "fixed_membership_sha256": "membership",
                "reference_artifacts": {"fixed_membership_sha256": "membership"},
                "authorization": {
                    "status": "PASS_AUTHORIZATION_CHAIN",
                    "checks": {"status": True, "frozen_tag": True, "microdata_sha256": True},
                    "repair_source_bound_by_canonical_v2": True,
                },
                "weight_application_count": 1, "balanced_grid_complete": True,
                "contains_resolved_private_paths": False,
                "cell_build_spec_sha256": "cell-sha",
                "command_template": "<SANITIZED COMMAND>",
                "runtime_environment_lock_path": "env.txt",
                "runtime_environment_lock_sha256": "env-sha",
                "runtime_contract_sha256": "runtime-contract-sha",
                "runtime_payload_sha256": "runtime-payload-sha",
                "runtime_authentication": {
                    "status": "AUTHENTICATED_DECLARED_RUNTIME",
                    "environment_lock_path": "env.txt",
                    "environment_lock_sha256": "env-sha",
                    "runtime_contract_sha256": "runtime-contract-sha",
                    "runtime_payload": {"python_version": "3.13.8"},
                    "runtime_payload_sha256": "runtime-payload-sha",
                    "command_template": "<SANITIZED COMMAND>",
                },
                "runtime_code_hashes": {"builder.py": "builder"},
                "historical_reference_code_hashes": {"old.py": "old-sha"},
                "git_status": "PASS_COMMITTED_CLEAN_WORKTREE",
                "git_commit": "b" * 40,
                "git_tree": "c" * 40,
                "git_required_ancestor_commit": "a" * 40,
                "git_worktree_clean": True,
                "git_porcelain_sha256": hashlib.sha256(b"").hexdigest(),
                "git_committed_artifact_hashes": {
                    "builder.py": "builder", "cell.json": "cell-sha",
                    "analysis.json": "analysis-sha", "env.txt": "env-sha",
                },
                "raw_column_contract": {
                    "runtime_fields": [
                        "YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "WTFINL",
                    ],
                    "required_columns_present": True,
                    "source_column_counts": {
                        "ipums_cps_extract_9_wide": 27,
                        "ipums_cps_extract_11_march_basic_repair": 9,
                    },
                    "rejected_inherited_helper_fields": ["OCC2010", "IND1990"],
                    "canonical_v2_variable_universe_parity": True,
                },
                "freshness_and_security": {
                    "historical_reference_code_imported_at_runtime": False,
                    "only_six_canonical_raw_fields_read": True,
                    "row_level_microdata_written": False,
                    "historical_preperiod_cells_read": False,
                    "private_paths_persisted": False,
                    "credentials_persisted": False,
                },
            }
            self.assertTrue(all(AUDIT.cell_receipt_authentication_checks(receipt, cells, canonical, analysis).values()))
            for field in (
                "analysis_spec_sha256", "builder_code_sha256",
                "builder_transitive_code_sha256", "source_hashes",
                "authenticated_source_hashes", "unread_canonical_source_ids",
                "lookup_and_bridge_hashes", "fixed_membership_sha256",
                "reference_artifacts", "authorization",
                "command_template", "runtime_environment_lock_sha256",
                "runtime_contract_sha256", "runtime_payload_sha256",
                "runtime_code_hashes", "historical_reference_code_hashes",
                "git_status", "git_commit", "git_tree",
                "git_required_ancestor_commit", "git_worktree_clean",
                "git_porcelain_sha256", "git_committed_artifact_hashes",
                "raw_column_contract", "freshness_and_security",
            ):
                mutated = copy.deepcopy(receipt)
                mutated[field] = "mutated"
                checks = AUDIT.cell_receipt_authentication_checks(mutated, cells, canonical, analysis)
                self.assertFalse(all(checks.values()), field)
            for field in (
                "status", "environment_lock_path", "environment_lock_sha256",
                "runtime_contract_sha256", "runtime_payload",
                "runtime_payload_sha256", "command_template",
            ):
                mutated = copy.deepcopy(receipt)
                mutated["runtime_authentication"][field] = "mutated"
                checks = AUDIT.cell_receipt_authentication_checks(
                    mutated, cells, canonical, analysis
                )
                self.assertFalse(all(checks.values()), f"runtime_authentication.{field}")

    def test_current_git_receipt_binding_requires_exact_clean_committed_checkout(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = pathlib.Path(temporary) / "repo"
            repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=repo, check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "YAX test"], cwd=repo, check=True,
            )
            paths = ["builder.py", "cell.json", "analysis.json", "env.txt"]
            for relative in paths:
                (repo / relative).write_text(relative + "\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
            head = subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=repo, text=True
            ).strip()
            tree = subprocess.check_output(
                ["git", "rev-parse", "HEAD^{tree}"], cwd=repo, text=True
            ).strip()
            hashes = {
                relative: AUDIT.sha256_file(repo / relative) for relative in paths
            }
            analysis = {"input_contract": {"cell_builder_execution_contract": {
                "git_required_ancestor_commit": head,
                "git_committed_paths": paths,
            }}}
            receipt = {
                "git_commit": head,
                "git_tree": tree,
                "git_committed_artifact_hashes": hashes,
            }
            self.assertTrue(all(AUDIT.current_git_receipt_checks(
                repo, receipt, analysis
            ).values()))
            (repo / "builder.py").write_text("changed\n", encoding="utf-8")
            checks = AUDIT.current_git_receipt_checks(repo, receipt, analysis)
            self.assertFalse(checks["current_git_worktree_clean"])
            self.assertFalse(checks["current_git_committed_artifacts"])

    def test_assignment_authentication_detects_tuple_mutations(self):
        frame = pd.DataFrame({
            "occ_code": ["0001", "0002"], "family": ["11", "13"],
            "beta_quintile": [1, 5], "webb_z": [0.25, -0.5],
        })
        fingerprint = AUDIT.assignment_fingerprint(frame)
        receipt = {"assignment_fingerprint_sha256": fingerprint}
        analysis = {"input_contract": {"assignment_fingerprint_sha256": fingerprint}}
        self.assertTrue(all(AUDIT.assignment_authentication_checks(fingerprint, receipt, analysis).values()))
        for field, value in (("family", "99"), ("beta_quintile", 3), ("webb_z", 0.251)):
            mutated = frame.copy()
            mutated.loc[0, field] = value
            observed = AUDIT.assignment_fingerprint(mutated)
            self.assertFalse(all(AUDIT.assignment_authentication_checks(observed, receipt, analysis).values()))

    def test_atomic_output_leaf_rejects_overwrite_repo_and_overlap_then_publishes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            repo = root / "repo"
            outside = root / "outside"
            repo.mkdir(); outside.mkdir()
            source = outside / "input.csv"
            source.write_text("input", encoding="utf-8")
            with self.assertRaises(AUDIT.OutputSafetyError):
                AUDIT.AtomicOutputLeaf.reserve(repo / "run", repo, [source])
            preexisting = outside / "existing"
            preexisting.mkdir()
            with self.assertRaises(AUDIT.OutputSafetyError):
                AUDIT.AtomicOutputLeaf.reserve(preexisting, repo, [source])
            with self.assertRaises(AUDIT.OutputSafetyError):
                AUDIT.AtomicOutputLeaf.reserve(outside, repo, [source])
            target = outside / "new-run"
            reservation = AUDIT.AtomicOutputLeaf.reserve(target, repo, [source])
            (reservation.staging / "done.txt").write_text("complete", encoding="utf-8")
            reservation.publish()
            self.assertEqual((target / "done.txt").read_text(encoding="utf-8"), "complete")
            self.assertFalse(reservation.staging.exists())


class ArtifactPublicationTests(unittest.TestCase):
    def test_whole_artifact_scan_rejects_paths_and_common_secret_forms(self):
        unsafe_payloads = (
            "/projectnb/econdept/private/result.csv\n",
            "IPUMS_API_KEY=not-a-real-key\n",
            "github_pat_notarealcredential\n",
            "Authorization: Bearer notarealcredentialvalue\n",
            "Basic dXNlcjpwYXNzd29yZA==\n",
            "-----BEGIN OPENSSH PRIVATE KEY-----\n",
            "https://someone:password@example.invalid/path\n",
        )
        for index, payload in enumerate(unsafe_payloads):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as temporary:
                root = pathlib.Path(temporary)
                (root / "artifact.txt").write_text(payload, encoding="utf-8")
                with self.assertRaises(AUDIT.AuditBlocked):
                    AUDIT.scan_artifacts_for_sensitive_text(root)

    def test_whole_artifact_scan_accepts_sanitized_text_set(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "a.json").write_text('{"status":"PASS"}\n', encoding="utf-8")
            (root / "b.csv").write_text("model,value\npooled,-0.1\n", encoding="utf-8")
            result = AUDIT.scan_artifacts_for_sensitive_text(root)
            self.assertEqual(result["status"], "PASS_ALL_ARTIFACTS_SANITIZED")
            self.assertEqual(result["file_count"], 2)
            with self.assertRaises(AUDIT.AuditBlocked):
                AUDIT.scan_artifacts_for_sensitive_text(root, {"a.json"})

    def test_sensitive_staging_leaf_can_be_discarded_before_publication(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            repo = root / "repo"
            outside = root / "outside"
            repo.mkdir(); outside.mkdir()
            source = outside / "input.csv"
            source.write_text("input", encoding="utf-8")
            reservation = AUDIT.AtomicOutputLeaf.reserve(
                outside / "new-run", repo, [source],
            )
            (reservation.staging / "receipt.json").write_text(
                '{"IPUMS_API_KEY":"not-a-real-key"}\n', encoding="utf-8",
            )
            with self.assertRaises(AUDIT.AuditBlocked):
                AUDIT.scan_artifacts_for_sensitive_text(reservation.staging)
            reservation.discard()
            self.assertFalse(reservation.staging.exists())
            self.assertFalse(reservation.lock.exists())

    def test_blocked_status_is_nonzero_and_no_report_only_escape_exists(self):
        self.assertEqual(AUDIT.exit_code_for_status("PASS_ALL_MODELS"), 0)
        self.assertEqual(AUDIT.exit_code_for_status("BLOCKED_ONE_OR_MORE_MODELS"), 2)
        destinations = {action.dest for action in AUDIT.parser()._actions}
        self.assertNotIn("report_only", destinations)


class CellSpecBindingTests(unittest.TestCase):
    def test_current_cell_spec_id_hash_and_consumer_binding_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            repo = pathlib.Path(temporary)
            relative = "gate1_cells/CELL_BUILD_SPEC.json"
            path = repo / relative
            path.parent.mkdir()
            analysis = {
                "audit_spec_id": "audit-id",
                "_loaded_file_sha256": "analysis-sha",
                "input_contract": {"cell_builder_execution_contract": {
                    "cell_build_spec_path": relative,
                }},
            }
            canonical = {"spec_id": "canonical-id"}
            cell_spec = {
                "schema_version": AUDIT.CELL_SPEC_SCHEMA,
                "aggregate_schema_version": AUDIT.CELL_SCHEMA,
                "canonical_spec_id": "canonical-id",
                "canonical_spec_sha256": AUDIT.CANONICAL_SPEC_SHA256,
                "consumer_contract": {
                    "analysis_spec_id": "audit-id",
                    "analysis_spec_sha256": "analysis-sha",
                },
                "cell_build_spec_id": "pending",
            }
            cell_spec["cell_build_spec_id"] = AUDIT.expected_cell_spec_id(cell_spec)
            path.write_text(
                json.dumps(cell_spec, sort_keys=True) + "\n", encoding="utf-8",
            )
            receipt = {
                "cell_build_spec_id": cell_spec["cell_build_spec_id"],
                "cell_build_spec_sha256": AUDIT.sha256_file(path),
            }
            baseline = AUDIT.current_cell_spec_binding_checks(
                repo, receipt, canonical, analysis,
            )
            self.assertTrue(all(baseline.values()), baseline)

            for field in ("cell_build_spec_id", "cell_build_spec_sha256"):
                mutated_receipt = copy.deepcopy(receipt)
                mutated_receipt[field] = "mutated"
                checks = AUDIT.current_cell_spec_binding_checks(
                    repo, mutated_receipt, canonical, analysis,
                )
                self.assertFalse(all(checks.values()), field)

            mutated_spec = copy.deepcopy(cell_spec)
            mutated_spec["consumer_contract"]["analysis_spec_sha256"] = "mutated"
            path.write_text(
                json.dumps(mutated_spec, sort_keys=True) + "\n", encoding="utf-8",
            )
            checks = AUDIT.current_cell_spec_binding_checks(
                repo, receipt, canonical, analysis,
            )
            self.assertFalse(all(checks.values()))


class ProducerAccountingTests(unittest.TestCase):
    @staticmethod
    def fixture():
        sources = [
            "ipums_cps_extract_9_wide",
            "ipums_cps_extract_11_march_basic_repair",
        ]
        values = {
            "invalid_raw_occ_records": [1, 0],
            "valid_raw_occ_records": [9, 4],
            "early_valid_source_records": [5, 2],
            "current_valid_source_records": [4, 2],
            "early_matched_source_records": [4, 2],
            "early_unmatched_source_records": [1, 0],
            "early_expanded_route_descendants": [6, 3],
            "early_fractional_route_contributions": [4, 2],
            "early_unit_route_contributions": [2, 1],
            "early_zero_mass_route_contributions": [0, 0],
            "current_direct_route_contributions": [4, 2],
            "routed_contribution_rows": [10, 5],
        }
        raw = {
            "source_ids": sources,
            "runtime_raw_fields": [
                "YEAR", "MONTH", "AGE", "EMPSTAT", "OCC", "WTFINL",
            ],
            "physical_rows_read_total": 28,
            "physical_rows_read_by_source": dict(zip(sources, [20, 8])),
            "eligible_employed_age_22_65_records_total": 14,
            "eligible_employed_age_22_65_records_by_source": dict(zip(sources, [10, 4])),
            "wide_march_rows_explicitly_replaced": 3,
            "repair_eligible_employed_age_22_65_records": 4,
            "repair_observed_months": [
                "2017-03", "2018-03", "2019-03", "2020-03", "2021-03",
            ],
        }
        for name, counts in values.items():
            raw[f"{name}_by_source"] = dict(zip(sources, counts))
            raw[name] = sum(counts)
        raw["routed_rows"] = raw["routed_contribution_rows"]

        source_identities = {}
        for source in sources:
            get = lambda name: raw[f"{name}_by_source"][source]
            eligible = raw["eligible_employed_age_22_65_records_by_source"][source]
            source_identities[source] = {
                "eligible_equals_invalid_plus_valid": eligible == get("invalid_raw_occ_records") + get("valid_raw_occ_records"),
                "valid_equals_early_plus_current": get("valid_raw_occ_records") == get("early_valid_source_records") + get("current_valid_source_records"),
                "early_equals_matched_plus_unmatched": get("early_valid_source_records") == get("early_matched_source_records") + get("early_unmatched_source_records"),
                "expanded_descendants_cover_each_matched_record": get("early_expanded_route_descendants") >= get("early_matched_source_records"),
                "early_descendants_partition_by_route_weight": get("early_expanded_route_descendants") == get("early_fractional_route_contributions") + get("early_unit_route_contributions") + get("early_zero_mass_route_contributions"),
                "direct_contributions_equal_current_valid_records": get("current_direct_route_contributions") == get("current_valid_source_records"),
                "routed_contributions_equal_descendants_plus_direct": get("routed_contribution_rows") == get("early_expanded_route_descendants") + get("current_direct_route_contributions"),
            }
        total_identities = {
            "physical_total_equals_source_sum": True,
            "eligible_total_equals_source_sum": True,
            "eligible_equals_invalid_plus_valid": True,
            "valid_equals_early_plus_current": True,
            "early_equals_matched_plus_unmatched": True,
            "early_descendants_partition_by_route_weight": True,
            "direct_contributions_equal_current_valid_records": True,
            "routed_contributions_equal_descendants_plus_direct": True,
        }
        source_reconciliation = {
            sources[0]: {
                "raw_early_valid_stock": 110.0,
                "raw_early_matched_stock": 100.0,
                "expected_early_routed_stock": 100.0,
                "actual_early_routed_stock": 100.0,
                "raw_current_valid_stock": 50.0,
                "actual_current_direct_stock": 50.0,
                "early_absolute_gap": 0.0,
                "early_relative_gap": 0.0,
                "current_absolute_gap": 0.0,
                "current_relative_gap": 0.0,
                "unmatched_early_stock": 10.0,
                "route_conservation_pass": True,
            },
            sources[1]: {
                "raw_early_valid_stock": 40.0,
                "raw_early_matched_stock": 40.0,
                "expected_early_routed_stock": 40.0,
                "actual_early_routed_stock": 40.0,
                "raw_current_valid_stock": 20.0,
                "actual_current_direct_stock": 20.0,
                "early_absolute_gap": 0.0,
                "early_relative_gap": 0.0,
                "current_absolute_gap": 0.0,
                "current_relative_gap": 0.0,
                "unmatched_early_stock": 0.0,
                "route_conservation_pass": True,
            },
        }
        receipt = {
            "six_field_cell_build_checks": raw,
            "route_checks": {
                "total_record_identities": total_identities,
                "record_identities_by_source": source_identities,
                "source_stock_reconciliation": source_reconciliation,
                "raw_early_valid_stock": 150.0,
                "raw_early_matched_stock": 140.0,
                "expected_early_routed_stock": 140.0,
                "actual_early_routed_stock": 140.0,
                "raw_current_valid_stock": 70.0,
                "actual_current_direct_stock": 70.0,
                "early_absolute_gap": 0.0,
                "route_conservation_pass": True,
                "early_relative_gap": 0.0,
                "current_absolute_gap": 0.0,
                "current_relative_gap": 0.0,
                "unmatched_early_stock": 10.0,
                "bridge_mass_min": 1.0,
                "bridge_mass_max": 1.0,
            },
            "weight_once_checks": {
                "status": "PASS_WEIGHT_ONCE",
                "weight_application_count": 1,
                "route_weight_is_allocation_not_second_survey_weight": True,
                "output_applies_no_additional_weight": True,
                "independent_aggregation_max_absolute_gap": 0.0,
                "rows": 42,
            },
        }
        analysis = {"input_contract": {
            "expected_balanced_grid_rows": 42,
            "cell_builder_execution_contract": {
                "runtime_raw_source_ids": sources,
                "runtime_raw_fields": raw["runtime_raw_fields"],
            },
        }}
        return receipt, analysis

    def test_physical_route_and_weight_assertions_are_recomputed(self):
        receipt, analysis = self.fixture()
        baseline = AUDIT.producer_accounting_checks(receipt, analysis)
        self.assertTrue(all(baseline.values()), baseline)
        mutations = (
            lambda value: value["six_field_cell_build_checks"].__setitem__("physical_rows_read_total", 29),
            lambda value: value["six_field_cell_build_checks"]["early_expanded_route_descendants_by_source"].__setitem__("ipums_cps_extract_9_wide", 7),
            lambda value: value["route_checks"]["total_record_identities"].__setitem__("valid_equals_early_plus_current", False),
            lambda value: value["route_checks"].__setitem__("early_relative_gap", 0.1),
            lambda value: value["weight_once_checks"].__setitem__("weight_application_count", 2),
        )
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                changed = copy.deepcopy(receipt)
                mutate(changed)
                self.assertFalse(all(
                    AUDIT.producer_accounting_checks(changed, analysis).values()
                ))


class FailureRetentionTests(unittest.TestCase):
    @staticmethod
    def analysis_settings():
        return {
            "boundary_and_separation": {
                "lp_margin_tolerance": 1e-9,
            },
            "profile": {
                "grid_standard_error_multipliers": [-2, -1, 0, 1, 2],
                "likelihood_rise_tolerance_raw": 1e-4,
            },
            "tolerances": {
                "conditioning_rank_relative": 1e-10,
                "optimizer_max_iterations": 1000,
                "profile_max_iterations": 500,
                "gradient_infinity_norm_per_total": 1e-7,
                "standardized_score_absolute": 1e-4,
                "target_coefficient_absolute_difference": 1e-6,
                "fitted_probability_max_abs_difference": 1e-7,
                "objective_difference_per_total": 1e-10,
            },
        }

    def test_face_exception_retains_preceding_boundary_pruning(self):
        model = bundle(
            young=[0, 0, 4, 5, 5, 6], total=[10] * 6,
            first=["boundary", "boundary", "b", "b", "c", "c"],
            second=["m1", "m2", "m1", "m2", "m1", "m2"],
        )
        parity = {"status": "PASS_EXACT_SUBMITTED_DESIGN_PARITY"}
        with mock.patch.object(
            AUDIT, "resolve_extended_likelihood_face", side_effect=RuntimeError("synthetic face failure")
        ):
            result, pruning, solvers, profiles, trajectory = AUDIT.audit_model(
                model, self.analysis_settings(), object(), parity,
            )
        self.assertEqual(result["profiled_boundary_rows"], 2)
        self.assertGreater(len(pruning), 0)
        self.assertEqual(result["classification"], "BLOCKED_EXTENDED_FACE_EXCEPTION_NO_SUBSTITUTION")
        self.assertEqual((solvers, profiles, trajectory), ([], [], {}))

    def test_second_solver_exception_retains_first_solver_trajectory(self):
        model = bundle(
            young=[3, 6, 4, 7, 5, 6], total=[10] * 6,
            first=["a", "a", "a", "b", "b", "b"],
            second=["m1", "m2", "m3", "m1", "m2", "m3"],
            regressors=np.array([[-1.0], [0.0], [1.0], [-0.5], [0.8], [-0.2]]),
        )
        parity = {"status": "PASS_EXACT_SUBMITTED_DESIGN_PARITY"}
        original = AUDIT.fit_exact_solver

        def one_success(objective, method, *args, **kwargs):
            if method == "trust-ncg":
                raise RuntimeError("synthetic second-solver failure")
            return original(objective, method, *args, **kwargs)

        with mock.patch.object(AUDIT, "fit_exact_solver", side_effect=one_success):
            result, _, solvers, _, trajectory = AUDIT.audit_model(
                model, self.analysis_settings(), object(), parity,
            )
        self.assertEqual(result["classification"], "BLOCKED_EXACT_SOLVER_EXCEPTION_NO_SUBSTITUTION")
        self.assertIn("L-BFGS-B", trajectory)
        self.assertGreater(len(trajectory["L-BFGS-B"]), 0)
        self.assertTrue(any(row.get("method") == "trust-ncg" for row in solvers))


class RegistryTests(unittest.TestCase):
    def test_declared_scc_runtime_payload_hash_is_canonical(self):
        analysis = json.loads((HERE / "ANALYSIS_SPEC.json").read_text())
        contract = analysis["software"]["runtime_contract"]
        observed = AUDIT.hashlib.sha256(AUDIT.canonical_bytes(contract["payload"])).hexdigest()
        self.assertEqual(observed, contract["payload_sha256"])

    def test_analysis_spec_identifier_is_valid(self):
        spec = json.loads((HERE / "ANALYSIS_SPEC.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["audit_spec_id"], AUDIT.expected_audit_spec_id(spec))

    def test_analysis_spec_is_bound_to_canonical_spec_and_runner(self):
        canonical = HERE.parent / "contracts/specs/canonical_baseline_reproduction_v2.json"
        loaded, audit = AUDIT.validate_specs(canonical, HERE / "ANALYSIS_SPEC.json")
        self.assertEqual(audit["canonical_spec_id"], loaded["spec_id"])

    def test_all_predeclared_models_build_on_balanced_synthetic_grid(self):
        months = [
            f"{year:04d}-{month:02d}"
            for year in range(2022, 2024) for month in range(1, 13)
        ]
        rows = []
        for index in range(10):
            for month in months:
                rows.append({
                    "occ_code": f"{index:04d}",
                    "month": month,
                    "family": "11" if index < 5 else "13",
                    "young": 20.0 + (index % 3),
                    "older": 80.0 + (index % 4),
                    "beta_quintile": index % 5 + 1,
                    "webb_z": (index - 4.5) / 3.0,
                })
        frame = pd.DataFrame(rows)
        models = json.loads((HERE / "ANALYSIS_SPEC.json").read_text())["models"]
        for registry in models:
            built = AUDIT.model_bundle(frame, registry["model_id"])
            self.assertGreater(len(built.young), 0)
            if built.focal_target_weights is None:
                self.assertIn(built.focal_target_label, built.regressor_labels)
            else:
                self.assertAlmostEqual(float(built.focal_target_weights.sum()), 1.0)
                transformed, target_audit = AUDIT.target_coordinate_bundle(built)
                self.assertEqual(transformed.focal_target, 0)
                self.assertEqual(
                    target_audit["status"],
                    "EXACT_INVERTIBLE_LINEAR_FUNCTIONAL_REPARAMETERIZATION",
                )
            self.assertEqual(built.regressors.shape[0], len(built.young))

    def test_all_eleven_designs_match_byte_locked_submitted_implementations(self):
        analysis = json.loads((HERE / "ANALYSIS_SPEC.json").read_text())
        repo = HERE.parents[3]
        modules = AUDIT.load_submitted_design_modules(repo, analysis)
        months = [
            f"{year:04d}-{month:02d}"
            for year in range(2020, 2024) for month in range(1, 13)
        ]
        rows = []
        for index in range(10):
            for month in months:
                rows.append({
                    "occ_code": f"{index:04d}", "month": month,
                    "family": "11" if index < 5 else "13",
                    "young": 20.0 + index % 3, "older": 80.0 + index % 4,
                    "beta_quintile": index % 5 + 1,
                    "webb_z": (index - 4.5) / 3.0,
                })
        frame = pd.DataFrame(rows)
        for registry in analysis["models"]:
            built = AUDIT.model_bundle(frame, registry["model_id"])
            parity = AUDIT.submitted_design_parity(built, modules)
            self.assertEqual(parity["status"], "PASS_EXACT_SUBMITTED_DESIGN_PARITY", registry["model_id"])
            if registry["model_id"].startswith("dynamics_"):
                self.assertFalse(parity["transition_2022_12_included"])

    def test_family_post_reference_matches_submitted_all_period_stock_on_ranking_switch(self):
        months = ["2022-10", "2022-11", "2023-01", "2023-02"]
        rows = []
        for index in range(10):
            family = "11" if index < 5 else "13"
            for month in months:
                pre = month < "2023-01"
                stock = (
                    200.0 if family == "11" and pre else
                    2.0 if family == "11" else
                    5.0 if pre else 500.0
                )
                rows.append({
                    "occ_code": f"{index:04d}", "month": month, "family": family,
                    "young": stock * 0.2, "older": stock * 0.8,
                    "beta_quintile": index % 5 + 1,
                    "webb_z": (index - 4.5) / 3.0,
                })
        frame = pd.DataFrame(rows)
        analysis = json.loads((HERE / "ANALYSIS_SPEC.json").read_text())
        modules = AUDIT.load_submitted_design_modules(HERE.parents[3], analysis)
        built = AUDIT.model_bundle(frame, "family_post")
        parity = AUDIT.submitted_design_parity(built, modules)
        self.assertEqual(parity["status"], "PASS_EXACT_SUBMITTED_DESIGN_PARITY")
        self.assertIn("family_11_x_post", built.regressor_labels)
        self.assertNotIn("family_13_x_post", built.regressor_labels)

    def test_full_calendar_dynamic_registry_covers_38_q5_targets_and_23_pretrends(self):
        months = [
            f"{year:04d}-{month:02d}"
            for year in range(2017, 2027) for month in range(1, 13)
            if "2017-01" <= f"{year:04d}-{month:02d}" <= "2026-07"
            and f"{year:04d}-{month:02d}" != "2025-10"
        ]
        rows = []
        for index in range(10):
            for month in months:
                rows.append({
                    "occ_code": f"{index:04d}", "month": month,
                    "family": "11" if index < 5 else "13",
                    "young": 20.0 + index % 3, "older": 80.0 + index % 4,
                    "beta_quintile": index % 5 + 1,
                    "webb_z": (index - 4.5) / 3.0,
                })
        built = AUDIT.model_bundle(pd.DataFrame(rows), "dynamics_unconditioned")
        targets = built.reported_target_weights
        self.assertIsNotNone(targets)
        self.assertEqual(len(targets), 38)
        self.assertEqual(sum(label.rsplit("_", 1)[1] < "2022Q4" for label in targets), 23)
        self.assertAlmostEqual(float(built.focal_target_weights.sum()), 1.0)
        self.assertEqual(sum(month >= "2023-01" and month != "2022-12" for month in months), 42)
        analysis = json.loads((HERE / "ANALYSIS_SPEC.json").read_text())
        scope = AUDIT.dynamic_target_scope_diagnostics(built, analysis)
        self.assertEqual(
            scope["status"], "PASS_COMPLETE_DYNAMIC_TARGET_SCOPE_CONSTRUCTION"
        )
        self.assertTrue(all(scope["checks"].values()))

        missing = copy.deepcopy(built)
        missing.reported_target_weights.pop(next(iter(missing.reported_target_weights)))
        failed = AUDIT.dynamic_target_scope_diagnostics(missing, analysis)
        self.assertEqual(
            failed["status"], "BLOCKED_INCOMPLETE_DYNAMIC_TARGET_SCOPE_CONSTRUCTION"
        )


if __name__ == "__main__":
    unittest.main()
