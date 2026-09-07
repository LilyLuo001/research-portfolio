#!/usr/bin/env python3
"""Synthetic-data tests for the V3 N01--N03 numerical audit."""
from __future__ import annotations

import importlib.util
import copy
import hashlib
import inspect
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
SAFETY = sys.modules[AUDIT.AtomicOutputLeaf.__module__]


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


def fit_solver(
    objective, method, start, max_iterations, gradient_tolerance,
    standardized_score_tolerance, focal_column, *, fisher_start=False,
    targets=None,
):
    if targets is None:
        focal = np.zeros(objective.design.shape[1], dtype=float)
        focal[focal_column] = 1.0
        targets = {"focal_target": focal}
    return AUDIT.fit_exact_solver(
        objective, method, start, max_iterations, gradient_tolerance,
        standardized_score_tolerance, focal_column, targets, 1e-6, 1e-4,
        fisher_start, 1e-10,
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

    def test_focal_invariant_but_nonfocal_treatment_separation_blocks(self):
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
        self.assertEqual(
            face["status"],
            "BLOCKED_TREATMENT_VECTOR_MOVING_RECESSION_DIRECTION",
        )
        self.assertEqual(int(active.sum()), 8)
        self.assertIsNotNone(design)
        self.assertEqual(pruning, [])
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

    def test_nonfocal_original_treatment_recession_blocks_face_profiling(self):
        regressors = np.array([
            [0, 1], [0, -1], [0, -1], [0, 1],
            [1, 0], [-1, 0], [-1, 0], [1, 0],
        ], float)
        model = bundle(
            young=[10, 0, 0, 10, 5, 5, 5, 5], total=[10] * 8,
            first=["all"] * 8, second=["all"] * 8,
            regressors=regressors, label="focal",
        )
        model.regressor_labels = ["focal", "nonfocal"]
        original_targets = {
            "original_treatment::0::focal": np.array([1.0, 0.0]),
            "original_treatment::1::nonfocal": np.array([0.0, 1.0]),
        }

        def synthetic_separation(
            design, young, total, focal_column, margin_tolerance,
            column_labels=None, certification_tolerance=None,
            additional_target_vectors=None,
        ):
            self.assertEqual(set(additional_target_vectors), set(original_targets))
            audits = {
                label: {
                    "audit_complete": True,
                    "target_can_move": label.endswith("::nonfocal"),
                }
                for label in additional_target_vectors
            }
            return {
                "status": "PASS", "separation_exists": True,
                "focal_target_direction_audit_complete": True,
                "focal_target_can_move": False,
                "reported_target_direction_audits": audits,
                "all_reported_targets_direction_audit_complete": True,
                "any_reported_target_can_move": True,
            }

        with mock.patch.object(
            AUDIT, "separation_lp", side_effect=synthetic_separation,
        ):
            _active, _design, face, pruning = (
                AUDIT.resolve_extended_likelihood_face(
                    model, {
                        "boundary_and_separation": {
                            "lp_margin_tolerance": 1e-9,
                        },
                        "tolerances": {"conditioning_rank_relative": 1e-10},
                    }, original_targets,
                )
            )
        self.assertEqual(
            face["status"],
            "BLOCKED_TREATMENT_VECTOR_MOVING_RECESSION_DIRECTION",
        )
        self.assertEqual(pruning, [])
        self.assertFalse(face["separation"][
            "treatment_column_direction_audits"
        ]["original_treatment::0::focal"]["target_can_move"])
        self.assertTrue(face["separation"][
            "treatment_column_direction_audits"
        ]["original_treatment::1::nonfocal"]["target_can_move"])

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
        left = fit_solver(
            objective, "L-BFGS-B", np.zeros(2), 1000, 1e-7, 1e-4, 1,
        )
        right = fit_solver(
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
        self.assertEqual(left[0]["optimizer_options"]["maxls"], 50)
        self.assertRegex(
            left[0]["optimizer_start_original_coordinates_sha256"],
            r"^[0-9a-f]{64}$",
        )

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
            "method": "L-BFGS-B", "numerically_valid": True,
            "objective_per_total": 0.5,
            "raw_negative_log_likelihood": 10.0,
        }
        right_diagnostics = {
            **diagnostics, "method": "trust-ncg",
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

    def test_historical_solver_comparison_labels_complete_treatment_vector(self):
        left = {
            "method": "L-BFGS-B", "numerically_valid": False,
            "objective_per_total": 0.5, "raw_negative_log_likelihood": 10.0,
        }
        right = {
            **left, "method": "trust-ncg", "numerically_valid": True,
        }
        result = AUDIT.compare_solvers(
            left, np.array([0.0, 0.1, 0.2]), np.array([0.4, 0.6]),
            right, np.array([0.0, 0.11, 0.18]), np.array([0.4, 0.6]),
            nuisance_columns=1, focal_target=0,
            tolerances={
                "target_coefficient_absolute_difference": 1e-6,
                "fitted_probability_max_abs_difference": 1e-7,
                "objective_difference_per_total": 1e-10,
            }, treatment_labels=["event_a", "event_b"],
        )
        differences = result[
            "complete_identified_treatment_vector_absolute_differences"
        ]
        self.assertEqual(set(differences), {"event_a", "event_b"})
        self.assertAlmostEqual(differences["event_a"], 0.01)
        self.assertAlmostEqual(differences["event_b"], 0.02)
        self.assertEqual(
            result["complete_identified_treatment_vector_count"], 2,
        )

    def test_solver_comparison_records_raw_objective_and_argmax_location(self):
        left = {
            "method": "L-BFGS-B", "numerically_valid": True,
            "objective_per_total": 0.5,
            "raw_negative_log_likelihood": 100.25,
        }
        right = {
            "method": "trust-ncg", "numerically_valid": True,
            "objective_per_total": 0.5001,
            "raw_negative_log_likelihood": 100.75,
        }
        result = AUDIT.compare_solvers(
            left, np.array([0.0, 0.1]), np.array([0.4, 0.5]),
            right, np.array([0.0, 0.1]), np.array([0.4, 0.5002]),
            nuisance_columns=1, focal_target=0,
            tolerances={
                "target_coefficient_absolute_difference": 1e-6,
                "fitted_probability_max_abs_difference": 1e-7,
                "objective_difference_per_total": 1e-10,
            },
            row_identifiers=[
                {"occ_code": "0001", "month": "2023-01", "family": "11"},
                {"occ_code": "0002", "month": "2023-02", "family": "13"},
            ],
        )
        self.assertEqual(result["raw_negative_log_likelihood_difference"], 0.5)
        location = result["fitted_probability_max_abs_difference_location"]
        self.assertEqual(location["row_position_zero_based"], 1)
        self.assertEqual(location["row_identifiers"]["occ_code"], "0002")

    def test_solver_comparison_rejects_duplicate_or_substituted_algorithm(self):
        diagnostics = {
            "method": "L-BFGS-B", "numerically_valid": True,
            "objective_per_total": 0.5,
            "raw_negative_log_likelihood": 10.0,
        }
        with self.assertRaisesRegex(
            AUDIT.AuditBlocked, "independent algorithm pair",
        ):
            AUDIT.compare_solvers(
                diagnostics, np.array([0.0, 0.1]), np.array([0.4, 0.5]),
                diagnostics, np.array([0.0, 0.1]), np.array([0.4, 0.5]),
                nuisance_columns=1, focal_target=0,
                tolerances={
                    "target_coefficient_absolute_difference": 1e-6,
                    "fitted_probability_max_abs_difference": 1e-7,
                    "objective_difference_per_total": 1e-10,
                },
            )

    def test_design_only_reparameterization_preserves_objective_and_chain_rule(self):
        rng = np.random.default_rng(8501)
        dense = np.column_stack([
            np.ones(50), rng.normal(size=50), 1e-4 * rng.normal(size=50),
        ])
        total = rng.integers(10, 200, size=50).astype(float)
        young = total * rng.uniform(0.1, 0.9, size=50)
        offset = rng.normal(scale=0.2, size=50)
        objective = AUDIT.BinomialObjective(
            sparse.csr_matrix(dense), young, total, offset,
        )
        transformed, parameter_scale, audit = (
            AUDIT.design_only_diagonal_reparameterization(objective)
        )
        theta = rng.normal(size=3)
        phi = parameter_scale * theta
        self.assertEqual(
            objective.raw_nll(theta).hex(), transformed.raw_nll(phi).hex()
        )
        np.testing.assert_allclose(
            transformed.gradient(phi),
            objective.gradient(theta) / parameter_scale,
            rtol=2e-15, atol=2e-15,
        )
        direction = rng.normal(size=3)
        np.testing.assert_allclose(
            transformed.hessp(phi, direction),
            objective.hessp(theta, direction / parameter_scale) /
            parameter_scale,
            rtol=2e-15, atol=2e-15,
        )
        np.testing.assert_allclose(
            objective.probability(theta), transformed.probability(phi),
            rtol=0, atol=2e-16,
        )
        self.assertFalse(audit["uses_fitted_probabilities"])
        self.assertFalse(audit["changes_linear_predictor_or_likelihood"])

    def test_large_weight_weak_column_fixture_passes_original_kkt_for_both_solvers(self):
        rng = np.random.default_rng(7391)
        x = np.linspace(-2.0, 2.0, 120)
        weak = np.zeros(len(x))
        weak[-3:] = [0.5, 1.0, 1.5]
        dense = np.column_stack([np.ones(len(x)), x, weak])
        total = np.full(len(x), 1.0e8)
        total[-3:] = [1.0e3, 2.0e3, 3.0e3]
        truth = np.array([-0.35, 0.42, -0.8])
        young = total * expit(dense @ truth)
        objective = AUDIT.BinomialObjective(sparse.csr_matrix(dense), young, total)
        fits = [
            fit_solver(
                objective, method, np.zeros(3), 3000, 1e-7, 1e-4, 1,
            )
            for method in ("L-BFGS-B", "trust-ncg")
        ]
        for diagnostics, theta, _probability, _trajectory in fits:
            self.assertTrue(diagnostics["numerically_valid"], diagnostics)
            self.assertEqual(
                diagnostics["acceptance_source"],
                "ORIGINAL_COORDINATE_DECLARED_KKT_AND_FULL_HESSIAN_CERTIFICATE",
            )
            np.testing.assert_allclose(theta, truth, rtol=0, atol=2e-6)

    def test_near_collinear_false_pass_is_detected_and_native_solvers_recover(self):
        n = 200
        total_per_row = 1.0e6
        index = np.arange(n)
        z = np.sqrt(2.0) * np.cos(2.0 * np.pi * index / n)
        orthogonal = np.sqrt(2.0) * np.sin(4.0 * np.pi * index / n)
        epsilon = 2.2e-5
        dense = np.column_stack([z, z + epsilon * orthogonal])
        total = np.full(n, total_per_row)
        delta = np.sqrt(4.0 * 0.0015 / (total_per_row * n)) / epsilon
        truth = np.array([delta, -delta])
        young = total * expit(dense @ truth)
        objective = AUDIT.BinomialObjective(
            sparse.csr_matrix(dense), young, total,
        )
        focal = np.array([1.0, 0.0])

        zero_certificate = AUDIT.full_hessian_stationarity_certificate(
            objective, np.zeros(2), {"focal_target": focal},
            1e-4, 1e-6, 1e-4, 1e-10,
        )
        self.assertEqual(
            zero_certificate["status"],
            "BLOCKED_ORIGINAL_FULL_HESSIAN_WEAK_DIRECTION_CERTIFICATE",
        )
        self.assertGreater(
            zero_certificate["line_search"][
                "actual_raw_negative_log_likelihood_decrease"
            ],
            1e-4,
        )
        self.assertGreater(
            abs(zero_certificate["target_newton_corrections"]["focal_target"]),
            0.24,
        )
        weak_solve = zero_certificate["solve"]["solve_audit"]
        self.assertGreater(
            weak_solve["rhs_relative_residual"],
            weak_solve["relative_tolerance"],
        )
        self.assertLessEqual(
            weak_solve["rhs_relative_residual"],
            weak_solve["rhs_relative_roundoff_floor"],
        )
        self.assertLessEqual(
            weak_solve["normwise_backward_error"],
            weak_solve["relative_tolerance"],
        )
        self.assertFalse(weak_solve["backward_error_tolerance_relaxed"])

        left = fit_solver(
            objective, "L-BFGS-B", np.zeros(2), 2000,
            1e-7, 1e-4, 0, fisher_start=True,
        )
        right = fit_solver(
            objective, "trust-ncg", np.zeros(2), 2000,
            1e-7, 1e-4, 0,
        )
        for fit in (left, right):
            self.assertTrue(fit[0]["numerically_valid"], fit[0])
            self.assertEqual(
                fit[0]["full_hessian_stationarity_certificate"]["status"],
                "PASS_ORIGINAL_FULL_HESSIAN_WEAK_DIRECTION_CERTIFICATE",
            )
            np.testing.assert_allclose(fit[1], truth, rtol=0, atol=2e-6)
        self.assertEqual(
            left[0]["optimizer_start"]["status"],
            "PASS_L_BFGS_B_ONLY_P_HALF_FULL_HESSIAN_START",
        )
        self.assertEqual(
            right[0]["optimizer_start"]["status"],
            "DECLARED_ZERO_OR_CALLER_START_UNCHANGED",
        )

    def test_full_hessian_solve_rejects_zero_or_wrong_direction(self):
        dense = np.column_stack([
            np.ones(20), np.linspace(-1.0, 1.0, 20),
        ])
        total = np.full(20, 100.0)
        young = total * expit(dense @ np.array([-0.3, 0.6]))
        objective = AUDIT.BinomialObjective(
            sparse.csr_matrix(dense), young, total,
        )

        class ZeroFactor:
            @staticmethod
            def solve(rhs):
                return np.zeros_like(rhs)

        with mock.patch.object(AUDIT, "splu", return_value=ZeroFactor()):
            direction, solve, _scale = AUDIT.scaled_original_hessian_direction(
                objective, np.zeros(2), total * 0.25, 1e-10,
            )
            certificate = AUDIT.full_hessian_stationarity_certificate(
                objective, np.zeros(2),
                {"focal_target": np.array([0.0, 1.0])},
                1e-4, 1e-6, 1e-4, 1e-10,
            )
        np.testing.assert_array_equal(direction, np.zeros(2))
        self.assertEqual(solve["scaled_rhs_relative_residual"], 1.0)
        self.assertFalse(solve["linear_solve_residual_pass"])
        self.assertEqual(
            certificate["status"],
            "BLOCKED_ORIGINAL_FULL_HESSIAN_WEAK_DIRECTION_CERTIFICATE",
        )

    def test_target_adjoint_catches_omitted_weak_primal_solve_component(self):
        weak_eigenvalue = 1.2e-10
        correlation = 1.0 - weak_eigenvalue
        scaled_hessian = np.array([
            [1.0, correlation], [correlation, 1.0],
        ])
        dense = np.linalg.cholesky(scaled_hessian).T
        total = np.full(2, 4.0)
        strong = np.array([1.0, 1.0]) / np.sqrt(2.0)
        weak = np.array([1.0, -1.0]) / np.sqrt(2.0)
        scaled_rhs = 9.0e-5 * strong + 6.0e-15 * weak
        young = total * 0.5 + np.linalg.solve(dense.T, scaled_rhs)
        objective = AUDIT.BinomialObjective(
            sparse.csr_matrix(dense), young, total,
        )

        class OmitWeakFactor:
            @staticmethod
            def solve(rhs):
                strong_eigenvalue = 2.0 - weak_eigenvalue
                return strong * (strong @ rhs) / strong_eigenvalue

        with mock.patch.object(AUDIT, "splu", return_value=OmitWeakFactor()):
            direction, solve, _context = AUDIT.scaled_original_hessian_direction(
                objective, np.zeros(2), total * 0.25, 1e-10,
            )
            certificate = AUDIT.full_hessian_stationarity_certificate(
                objective, np.zeros(2), {"weak_target": weak},
                1e-4, 1e-6, 1e-4, 1e-10,
            )
        self.assertLessEqual(solve["scaled_rhs_relative_residual"], 1e-10)
        self.assertTrue(solve["linear_solve_residual_pass"])
        self.assertLess(abs(weak @ direction), 1e-12)
        target = certificate["target_primal_adjoint_audits"]["weak_target"]
        self.assertEqual(
            target["adjoint_solve"]["status"],
            "BLOCKED_REFINED_SPARSE_ORIGINAL_SYSTEM_SOLVE",
        )
        self.assertGreater(target["adjoint_solve"]["rhs_relative_residual"], 0.9)
        self.assertFalse(
            certificate["checks"]["all_declared_target_adjoint_solves"]
        )
        self.assertEqual(
            certificate["status"],
            "BLOCKED_ORIGINAL_FULL_HESSIAN_WEAK_DIRECTION_CERTIFICATE",
        )

    def test_nonminimum_iterative_ritz_pair_cannot_enter_certificate_path(self):
        weak_eigenvalue = 1.0e-12
        scaled_hessian = np.array([
            [1.0, 1.0 - weak_eigenvalue, 0.0],
            [1.0 - weak_eigenvalue, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ])
        dense = np.linalg.cholesky(scaled_hessian).T
        total = np.full(3, 4.0)
        young = total * 0.5 + np.array([1e-6, -1e-6, 1e-6])
        objective = AUDIT.BinomialObjective(
            sparse.csr_matrix(dense), young, total,
        )
        fake_nonminimum = (
            np.array([1.0]), np.array([[0.0], [0.0], [1.0]]),
        )
        with mock.patch.object(AUDIT, "eigsh", return_value=fake_nonminimum) as ritz:
            _direction, solve, _context = AUDIT.scaled_original_hessian_direction(
                objective, np.zeros(3), total * 0.25, 1e-10,
            )
        ritz.assert_not_called()
        self.assertFalse(solve["spectral_lower_bound_used"])
        self.assertFalse(solve["dense_conversion_used"])

    def test_sparse_8000_column_certificate_solve_has_no_dense_or_eigen_path(self):
        columns = 8000
        objective = AUDIT.BinomialObjective(
            sparse.eye(columns, format="csr"),
            np.full(columns, 2.0),
            np.full(columns, 4.0),
        )
        with (
            mock.patch.object(
                AUDIT, "eigsh", side_effect=AssertionError("eigsh forbidden")
            ) as ritz,
            mock.patch.object(
                sparse.csc_matrix, "toarray",
                side_effect=AssertionError("dense conversion forbidden"),
            ) as dense_conversion,
        ):
            direction, solve, context = AUDIT.scaled_original_hessian_direction(
                objective, np.zeros(columns), np.ones(columns), 1e-10,
            )
        ritz.assert_not_called()
        dense_conversion.assert_not_called()
        np.testing.assert_array_equal(direction, np.zeros(columns))
        self.assertEqual(context["scaled_hessian"].shape, (columns, columns))
        self.assertTrue(solve["linear_solve_residual_pass"])
        self.assertFalse(solve["spectral_lower_bound_used"])
        self.assertFalse(solve["dense_conversion_used"])

    def test_complete_dyadic_grid_does_not_accept_far_root_nonincrease(self):
        objective = mock.Mock()
        objective.raw_nll.side_effect = lambda theta: float(
            (np.asarray(theta)[0] - 0.5) ** 2
        )
        candidate, audit = AUDIT.deterministic_decreasing_step(
            objective, np.array([0.0]), np.array([1.0]),
        )
        np.testing.assert_array_equal(candidate, np.array([0.5]))
        self.assertEqual(audit["step_fraction"], 0.5)
        self.assertEqual(
            audit["actual_raw_negative_log_likelihood_decrease"], 0.25,
        )

    def test_uniform_frequency_weight_rescaling_does_not_change_fit(self):
        x = np.linspace(-1.8, 1.8, 90)
        dense = np.column_stack([np.ones(len(x)), x])
        total = np.linspace(20.0, 100.0, len(x))
        truth = np.array([-0.2, 0.6])
        young = total * expit(dense @ truth)
        base = fit_solver(
            AUDIT.BinomialObjective(sparse.csr_matrix(dense), young, total),
            "L-BFGS-B", np.zeros(2), 2000, 1e-9, 1e-4, 1,
        )
        scaled = fit_solver(
            AUDIT.BinomialObjective(
                sparse.csr_matrix(dense), young * 1e7, total * 1e7,
            ),
            "L-BFGS-B", np.zeros(2), 2000, 1e-9, 1e-4, 1,
        )
        self.assertTrue(base[0]["numerically_valid"])
        self.assertTrue(scaled[0]["numerically_valid"])
        np.testing.assert_allclose(base[1], scaled[1], rtol=0, atol=2e-8)
        np.testing.assert_allclose(base[2], scaled[2], rtol=0, atol=2e-9)

    def test_scipy_success_or_stopping_message_cannot_override_original_kkt(self):
        design = sparse.csr_matrix(np.ones((10, 1)))
        objective = AUDIT.BinomialObjective(
            design, np.zeros(10), np.full(10, 10.0)
        )

        stopping_cases = (
            (True, 0, "CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH"),
            (False, 1, "STOP: TOTAL NO. OF ITERATIONS REACHED LIMIT"),
            (True, 0, "CONVERGENCE: NORM OF PROJECTED GRADIENT <= PGTOL"),
        )
        for success, status, message in stopping_cases:
            with self.subTest(message=message):
                result = type("SyntheticStop", (), {
                    "x": np.zeros(1), "success": success, "status": status,
                    "message": message, "nit": 0, "nfev": 1, "njev": 1,
                })()
                with mock.patch.object(AUDIT, "minimize", return_value=result):
                    diagnostics, _theta, _probability, _trajectory = fit_solver(
                        objective, "L-BFGS-B", np.zeros(1), 1, 1e-7, 1e-4, 0,
                    )
                self.assertFalse(diagnostics["numerically_valid"])
                self.assertEqual(
                    diagnostics["acceptance_source"],
                    "BLOCKED_ORIGINAL_COORDINATE_DECLARED_KKT",
                )
                self.assertTrue(diagnostics["scipy_status_is_not_acceptance_evidence"])

    def test_fixed_target_profile_requires_kkt_and_has_no_material_negative_rises(self):
        x = np.linspace(-2.0, 2.0, 100)
        dense = np.column_stack([np.ones(len(x)), x])
        total = np.full(len(x), 50.0)
        truth = np.array([-0.3, 0.7])
        young = total * expit(dense @ truth)
        objective = AUDIT.BinomialObjective(sparse.csr_matrix(dense), young, total)
        fit = fit_solver(
            objective, "L-BFGS-B", np.zeros(2), 2000, 1e-9, 1e-6, 1,
        )
        probability = fit[2]
        weight = total * probability * (1.0 - probability)
        information, _ = AUDIT.schur_information(
            sparse.csr_matrix(dense[:, [0]]), dense[:, [1]], weight,
        )
        rows, summary = AUDIT.fixed_target_profile(
            objective, fit[1], fit[0], 1, float(information[0, 0]),
            [-2.0, -1.0, 0.0, 1.0, 2.0], 1000,
            1e-7, 1e-4, 1e-4, 1e-10,
        )
        self.assertEqual(summary["status"], "PASS_TWO_SIDED_FINITE_PROFILE")
        self.assertTrue(summary["all_grid_rises_nonnegative_within_raw_tolerance"])
        self.assertTrue(all(row["success"] for row in rows))
        self.assertTrue(all(
            row["nuisance_standardized_score_max_abs"] <= 1e-4
            for row in rows
        ))
        self.assertTrue(all(
            row["acceptance_source"]
            == "ORIGINAL_COORDINATE_DECLARED_KKT_AND_FULL_HESSIAN_CERTIFICATE"
            for row in rows if row["multiplier"] != 0.0
        ))
        self.assertTrue(all(
            row["nuisance_fit_method"]
            == "independent-damped-sparse-newton-irls-from-zero"
            for row in rows if row["multiplier"] != 0.0
        ))
        self.assertEqual(
            summary["noncenter_nuisance_fit_method"],
            "independent-damped-sparse-newton-irls-from-zero",
        )
        self.assertEqual(
            next(row for row in rows if row["multiplier"] == 0.0)[
                "acceptance_source"
            ],
            "SUPPLIED_FULL_OPTIMUM_ORIGINAL_COORDINATE_KKT",
        )

    def test_fixed_target_profile_blocks_a_material_negative_grid_rise(self):
        design = sparse.csr_matrix(np.column_stack([
            np.ones(8), np.linspace(-1.0, 1.0, 8),
        ]))
        total = np.full(8, 10.0)
        young = np.full(8, 5.0)
        objective = AUDIT.BinomialObjective(design, young, total)
        center_raw = objective.raw_nll(np.zeros(2))
        raw_values = iter([
            center_raw + 2.0, center_raw - 1.0,
            center_raw + 1.0, center_raw + 3.0,
        ])

        def synthetic_profile_fit(reduced, start, *args, **kwargs):
            raw = next(raw_values)
            theta = np.asarray(start, float)
            probability = reduced.probability(theta)
            diagnostics = {
                "method": "independent-damped-sparse-newton-irls",
                "scipy_success": True,
                "scipy_status": 0,
                "message": "synthetic KKT fixture",
                "iterations": 1,
                "objective_per_total": raw / reduced.scale,
                "raw_negative_log_likelihood": raw,
                "raw_gradient_infinity_norm": 0.0,
                "gradient_infinity_norm_per_total": 0.0,
                "standardized_score_max_abs": 0.0,
                "coordinate_newton_step_max_abs": 0.0,
                "numerically_valid": True,
                "acceptance_source": "ORIGINAL_COORDINATE_DECLARED_KKT_AND_FULL_HESSIAN_CERTIFICATE",
                "optimizer_reparameterization": {"status": "SYNTHETIC"},
            }
            return diagnostics, theta, probability, []

        with (
            mock.patch.object(
                AUDIT, "fit_independent_sparse_newton",
                side_effect=synthetic_profile_fit,
            ),
            mock.patch.object(
                AUDIT, "externally_certify_independent_output",
                side_effect=lambda objective, output, *args, **kwargs: output,
            ),
        ):
            rows, summary = AUDIT.fixed_target_profile(
                objective, np.zeros(2), {
                    "numerically_valid": True,
                    "acceptance_source": "ORIGINAL_COORDINATE_DECLARED_KKT_AND_FULL_HESSIAN_CERTIFICATE",
                }, 1, 1.0,
                [-2.0, -1.0, 0.0, 1.0, 2.0], 100,
                1e-7, 1e-4, 1e-4, 1e-10,
            )
        self.assertEqual(summary["status"], "BLOCKED_PROFILE_BENCHMARK")
        self.assertFalse(summary["all_grid_rises_nonnegative_within_raw_tolerance"])
        self.assertEqual(
            min(row["raw_negative_log_likelihood_rise_from_center"] for row in rows),
            -1.0,
        )

    def test_profile_zero_multiplier_uses_supplied_full_optimum_not_reoptimization(self):
        design = sparse.csr_matrix(np.column_stack([
            np.ones(10), np.linspace(-1.0, 1.0, 10),
        ]))
        total = np.full(10, 20.0)
        young = np.full(10, 10.0)
        objective = AUDIT.BinomialObjective(design, young, total)
        optimum = np.zeros(2)
        center_raw = objective.raw_nll(optimum)
        calls = []

        def constrained_fit(reduced, start, *args, **kwargs):
            calls.append(reduced.offset.copy())
            raw = center_raw + 2.0
            theta = np.asarray(start, float)
            diagnostics = {
                "method": "independent-damped-sparse-newton-irls",
                "scipy_success": True, "scipy_status": 0,
                "message": "fixture", "iterations": 1,
                "objective_per_total": raw / reduced.scale,
                "raw_negative_log_likelihood": raw,
                "raw_gradient_infinity_norm": 0.0,
                "gradient_infinity_norm_per_total": 0.0,
                "standardized_score_max_abs": 0.0,
                "coordinate_newton_step_max_abs": 0.0,
                "numerically_valid": True,
                "acceptance_source": "ORIGINAL_COORDINATE_DECLARED_KKT_AND_FULL_HESSIAN_CERTIFICATE",
                "optimizer_reparameterization": {"status": "SYNTHETIC"},
            }
            return diagnostics, theta, reduced.probability(theta), []

        with (
            mock.patch.object(
                AUDIT, "fit_independent_sparse_newton",
                side_effect=constrained_fit,
            ),
            mock.patch.object(
                AUDIT, "externally_certify_independent_output",
                side_effect=lambda objective, output, *args, **kwargs: output,
            ),
        ):
            rows, summary = AUDIT.fixed_target_profile(
                objective, optimum,
                {
                    "numerically_valid": True, "scipy_success": True,
                    "scipy_status": 0, "iterations": 1,
                    "acceptance_source": "ORIGINAL_COORDINATE_DECLARED_KKT_AND_FULL_HESSIAN_CERTIFICATE",
                    "optimizer_reparameterization": {"status": "FULL"},
                },
                1, 1.0, [-1.0, 0.0, 1.0], 100,
                1e-7, 1e-4, 1e-4, 1e-10,
            )
        self.assertEqual(len(calls), 2)
        center = next(row for row in rows if row["multiplier"] == 0.0)
        self.assertEqual(center["raw_negative_log_likelihood"], center_raw)
        self.assertEqual(
            center["acceptance_source"],
            "SUPPLIED_FULL_OPTIMUM_ORIGINAL_COORDINATE_KKT",
        )
        self.assertEqual(summary["center_raw_negative_log_likelihood"], center_raw)

    def test_profile_preserves_existing_offset_exactly(self):
        x = np.linspace(-1.5, 1.5, 60)
        dense = np.column_stack([np.ones(len(x)), x])
        offset = 0.15 * np.sin(x)
        total = np.full(len(x), 40.0)
        truth = np.array([-0.25, 0.55])
        young = total * expit(offset + dense @ truth)
        objective = AUDIT.BinomialObjective(
            sparse.csr_matrix(dense), young, total, offset,
        )
        fit = fit_solver(
            objective, "L-BFGS-B", np.zeros(2), 2000, 1e-9, 1e-6, 1,
        )
        probability = fit[2]
        information, _ = AUDIT.schur_information(
            sparse.csr_matrix(dense[:, [0]]), dense[:, [1]],
            total * probability * (1.0 - probability),
        )
        rows, summary = AUDIT.fixed_target_profile(
            objective, fit[1], fit[0], 1, float(information[0, 0]),
            [-1.0, 0.0, 1.0], 1000, 1e-7, 1e-4, 1e-4, 1e-10,
        )
        center = next(row for row in rows if row["multiplier"] == 0.0)
        self.assertEqual(summary["status"], "PASS_TWO_SIDED_FINITE_PROFILE")
        self.assertEqual(
            center["raw_negative_log_likelihood"].hex(),
            objective.raw_nll(fit[1]).hex(),
        )

    def test_profile_rejects_uncertified_or_false_kkt_center(self):
        design = sparse.csr_matrix(np.column_stack([
            np.ones(10), np.linspace(-1.0, 1.0, 10),
        ]))
        objective = AUDIT.BinomialObjective(
            design, np.zeros(10), np.full(10, 10.0),
        )
        for diagnostics in (
            {"numerically_valid": True},
            {
                "numerically_valid": True,
                "acceptance_source": "SCIPY_SUCCESS",
            },
        ):
            with self.subTest(diagnostics=diagnostics):
                rows, summary = AUDIT.fixed_target_profile(
                    objective, np.zeros(2), diagnostics, 1, 1.0,
                    [-1.0, 0.0, 1.0], 100, 1e-7, 1e-4, 1e-4, 1e-10,
                )
                self.assertEqual(rows, [])
                self.assertEqual(
                    summary["status"],
                    "BLOCKED_FULL_OPTIMUM_NOT_ORIGINAL_KKT_CERTIFIED",
                )
        rows, summary = AUDIT.fixed_target_profile(
            objective, np.zeros(2), {
                "numerically_valid": True,
                "acceptance_source": "ORIGINAL_COORDINATE_DECLARED_KKT_AND_FULL_HESSIAN_CERTIFICATE",
                "optimizer_reparameterization": {"status": "SYNTHETIC"},
            }, 1, 1.0, [-1.0, 0.0, 1.0], 100,
            1e-7, 1e-4, 1e-4, 1e-10,
        )
        center = next(row for row in rows if row["multiplier"] == 0.0)
        self.assertFalse(center["success"])
        self.assertEqual(
            center["acceptance_source"],
            "BLOCKED_RECOMPUTED_FULL_OPTIMUM_ORIGINAL_COORDINATE_KKT",
        )
        self.assertEqual(summary["status"], "BLOCKED_PROFILE_BENCHMARK")

    def test_retained_one_sided_cells_have_finite_exact_fit(self):
        x = np.linspace(-2.0, 2.0, 7)
        design = sparse.csr_matrix(np.column_stack([np.ones(len(x)), x]))
        total = np.full(len(x), 10.0)
        young = np.array([0.0, 6.0, 3.0, 5.0, 7.0, 4.0, 10.0])
        objective = AUDIT.BinomialObjective(design, young, total)
        fit = fit_solver(
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
        audited = fit_solver(
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

    def test_sparse_extreme_certificate_blocks_below_threshold_eigenvalue(self):
        columns = 1201
        diagonal = np.ones(columns)
        diagonal[0] = 5.0e-11
        design = sparse.diags(np.sqrt(diagonal), format="csr")
        result = AUDIT.full_hessian_diagnostics(
            design, np.ones(columns), columns, 1e-10, dense_limit=1200,
        )
        self.assertEqual(
            result["status"], "BLOCKED_FULL_HESSIAN_SPECTRUM_FAILURE",
        )
        self.assertIn("machine_tolerance", result["spectrum_method"])
        self.assertTrue(np.isfinite(
            result["smallest_eigenpair_residual_norm_2"]
        ))
        self.assertLessEqual(
            result["smallest_certified_lower_bound"],
            result["rank_threshold"],
        )
        self.assertGreaterEqual(
            result["largest_conservative_upper_bound"], 1.0,
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


class A1IndependentReferenceTests(unittest.TestCase):
    @staticmethod
    def problem():
        x = np.linspace(-1.75, 1.75, 120)
        dense = np.column_stack([np.ones(len(x)), x, x * x - np.mean(x * x)])
        total = np.linspace(30.0, 90.0, len(x))
        truth = np.array([-0.25, 0.55, -0.20])
        young = total * expit(dense @ truth)
        objective = AUDIT.BinomialObjective(
            sparse.csr_matrix(dense), young, total,
        )
        targets = {
            f"treatment_basis::{index}::b{index}": np.eye(3)[index]
            for index in range(3)
        }
        return objective, truth, targets

    @staticmethod
    def raw_reference(objective, targets, max_iterations=100):
        return AUDIT.fit_independent_sparse_newton(
            objective, np.zeros(objective.design.shape[1]), max_iterations,
            1e-9, 1e-6, 1, targets, 1e-6, 1e-4, 1e-10,
            1e-10, 1e-7, "standalone_zero_reference",
        )

    @staticmethod
    def certify(objective, raw, targets):
        return AUDIT.externally_certify_independent_output(
            objective, raw, targets, 1e-9, 1e-6, 1e-6, 1e-4,
            1e-10, 1e-10, 1e-7,
        )

    def test_independent_loss_is_algebraically_distinct_and_stable_at_extremes(self):
        eta = np.array([-1000.0, -50.0, 0.0, 50.0, 1000.0])
        design = sparse.eye(len(eta), format="csr")
        total = np.array([9.0, 12.0, 15.0, 18.0, 21.0])
        young = np.array([9.0, 4.0, 7.5, 12.0, 0.0])
        canonical = AUDIT.BinomialObjective(design, young, total)
        independent = AUDIT.IndependentGroupedBinomialEvaluator(
            design, young, total,
        )
        expected = np.sum(
            young * np.logaddexp(0.0, -eta)
            + (total - young) * np.logaddexp(0.0, eta)
        )
        self.assertTrue(np.isfinite(independent.raw_objective(eta)))
        self.assertEqual(independent.raw_objective(eta), float(expected))
        self.assertAlmostEqual(
            independent.raw_objective(eta), canonical.raw_nll(eta),
            delta=1e-10,
        )
        source = inspect.getsource(
            AUDIT.IndependentGroupedBinomialEvaluator.raw_objective
        )
        self.assertIn("self.successes * np.logaddexp(0.0, -eta)", source)
        self.assertNotIn("self.trials * np.logaddexp", source)

    def test_independent_score_hessian_and_directional_checks(self):
        rng = np.random.default_rng(2107)
        dense = np.column_stack([np.ones(80), rng.normal(size=(80, 3))])
        total = rng.integers(10, 80, size=80).astype(float)
        young = total * rng.uniform(0.05, 0.95, size=80)
        objective = AUDIT.BinomialObjective(sparse.csr_matrix(dense), young, total)
        evaluator = AUDIT.IndependentGroupedBinomialEvaluator(
            objective.design, young, total,
        )
        theta = rng.normal(scale=0.25, size=4)
        eta = dense @ theta
        success_probability = expit(eta)
        failure_probability = expit(-eta)
        hand_score = dense.T @ (
            (total - young) * success_probability
            - young * failure_probability
        )
        hand_hessian = dense.T @ (
            (total * success_probability * failure_probability)[:, None]
            * dense
        )
        np.testing.assert_allclose(
            evaluator.raw_score(theta), hand_score, rtol=2e-15, atol=2e-13,
        )
        np.testing.assert_allclose(
            evaluator.raw_hessian(theta).toarray(), hand_hessian,
            rtol=2e-15, atol=2e-13,
        )
        checks = AUDIT.independent_evaluator_checks(
            objective, evaluator, theta, 2e-7, 1e-12, 1e-12,
        )
        self.assertEqual(
            checks["status"],
            "PASS_INDEPENDENT_EVALUATOR_AND_DERIVATIVE_CHECKS",
        )
        self.assertTrue(all(checks["checks"].values()))
        np.testing.assert_allclose(
            evaluator.raw_hessian(theta).toarray(),
            evaluator.raw_hessian(theta).toarray().T, rtol=0, atol=0,
        )
        preflight = AUDIT.independent_evaluator_preflight(
            objective, 2e-7, 1e-12, 1e-12,
        )
        self.assertEqual(
            preflight["status"],
            "PASS_DETERMINISTIC_INDEPENDENT_EVALUATOR_PREFLIGHT",
        )
        self.assertEqual(
            set(preflight["checks"]), {"exact_zero", "bounded_sine_cosine"},
        )

    def test_zero_start_reference_does_not_call_canonical_evaluator_or_minimize(self):
        objective, truth, targets = self.problem()
        forbidden = AssertionError("canonical evaluator entered independent path")
        with (
            mock.patch.object(AUDIT, "minimize", side_effect=forbidden) as minimize,
            mock.patch.object(AUDIT.BinomialObjective, "raw_nll", side_effect=forbidden),
            mock.patch.object(AUDIT.BinomialObjective, "function", side_effect=forbidden),
            mock.patch.object(AUDIT.BinomialObjective, "gradient", side_effect=forbidden),
            mock.patch.object(AUDIT.BinomialObjective, "hessp", side_effect=forbidden),
            mock.patch.object(AUDIT.BinomialObjective, "probability", side_effect=forbidden),
        ):
            raw = self.raw_reference(objective, targets)
        minimize.assert_not_called()
        self.assertTrue(raw[0]["independent_zero_start"])
        self.assertTrue(raw[0]["independent_internal_numerically_valid"])
        self.assertFalse(raw[0]["numerically_valid"])
        self.assertEqual(
            raw[0]["acceptance_source"],
            "PENDING_UNCHANGED_EXTERNAL_CERTIFICATE",
        )
        certified = self.certify(objective, raw, targets)
        self.assertTrue(certified[0]["numerically_valid"])
        np.testing.assert_allclose(certified[1], truth, rtol=0, atol=2e-8)

    def test_reference_damping_is_deterministic_and_iteration_limit_fails_closed(self):
        objective, _truth, targets = self.problem()
        left = self.raw_reference(objective, targets)
        right = self.raw_reference(objective, targets)
        self.assertEqual(left[3], right[3])
        self.assertTrue(all(
            row["dyadic_step_fraction"] == 2.0 ** (-row["dyadic_halvings"])
            for row in left[3]
        ))
        counts = left[0]["independent_evaluation_counts"]
        evaluated = left[0]["newton_iterations_evaluated"]
        self.assertEqual(
            left[0]["implementation_owned_termination_code"],
            "A1_NEWTON_INTERNAL_CERTIFICATE_PASS",
        )
        self.assertIsNone(left[0]["scipy_status"])
        self.assertEqual(counts["line_search_candidate_objective"], 65 * evaluated)
        self.assertEqual(counts["raw_objective"], 66 * evaluated + 1)
        self.assertEqual(counts["raw_score"], evaluated + 1)
        self.assertEqual(counts["raw_hessian"], evaluated + 1)
        self.assertEqual(counts["probability"], evaluated + 1)
        self.assertEqual(left[0]["function_evaluations"], counts["raw_objective"])
        self.assertEqual(left[0]["gradient_evaluations"], counts["raw_score"])
        self.assertEqual(left[0]["hessian_evaluations"], counts["raw_hessian"])
        self.assertTrue(all(
            isinstance(value, int) and value >= 0 for value in counts.values()
        ))
        stopped = self.raw_reference(objective, targets, max_iterations=0)
        self.assertFalse(stopped[0]["independent_internal_numerically_valid"])
        self.assertFalse(stopped[0]["numerically_valid"])
        np.testing.assert_array_equal(stopped[1], np.zeros(3))
        self.assertEqual(
            stopped[0]["implementation_owned_termination_code"],
            "A1_NEWTON_ITERATION_LIMIT",
        )
        self.assertEqual(
            stopped[0]["independent_evaluation_counts"]["raw_objective"], 67,
        )

    def test_rank_deficient_reference_blocks_instead_of_regularizing(self):
        x = np.linspace(-1.0, 1.0, 50)
        design = sparse.csr_matrix(np.column_stack([np.ones(50), x, x]))
        total = np.full(50, 40.0)
        young = total * expit(0.4 * x)
        objective = AUDIT.BinomialObjective(design, young, total)
        targets = {
            f"treatment_basis::{j}::b{j}": np.eye(3)[j] for j in range(3)
        }
        with self.assertRaisesRegex(AUDIT.AuditBlocked, "singular") as caught:
            self.raw_reference(objective, targets)
        self.assertEqual(
            caught.exception.termination_code, "A1_NEWTON_SINGULAR_HESSIAN",
        )
        self.assertTrue(all(
            isinstance(value, int) and value >= 0
            for value in caught.exception.evaluation_counts.values()
        ))

    def test_line_search_failure_retains_owned_code_counts_and_last_metrics(self):
        objective, _truth, targets = self.problem()
        calls = 0

        def no_candidate(_evaluator, _theta):
            nonlocal calls
            calls += 1
            return 0.0 if calls == 1 else np.inf

        with mock.patch.object(
            AUDIT.IndependentGroupedBinomialEvaluator,
            "raw_objective", no_candidate,
        ):
            with self.assertRaises(AUDIT.IndependentNewtonFailure) as caught:
                self.raw_reference(objective, targets)
        error = caught.exception
        self.assertEqual(
            error.termination_code, "A1_NEWTON_LINE_SEARCH_FAILURE",
        )
        self.assertEqual(
            error.evaluation_counts["line_search_candidate_objective"], 65,
        )
        self.assertEqual(error.evaluation_counts["newton_iterations_evaluated"], 1)
        self.assertEqual(error.trajectory, [])
        self.assertEqual(error.last_metrics["iteration_zero_based"], 0)
        self.assertIn("raw_score_max_abs", error.last_metrics)

    def test_one_sided_finite_and_nearly_collinear_fixtures_are_certified(self):
        x = np.linspace(-2.0, 2.0, 9)
        objective = AUDIT.BinomialObjective(
            sparse.csr_matrix(np.column_stack([np.ones(9), x])),
            np.array([0.0, 3.0, 5.0, 8.0, 4.0, 6.0, 7.0, 9.0, 10.0]),
            np.full(9, 10.0),
        )
        targets = {
            f"treatment_basis::{j}::b{j}": np.eye(2)[j] for j in range(2)
        }
        one_sided = self.certify(
            objective, self.raw_reference(objective, targets), targets,
        )
        self.assertTrue(one_sided[0]["numerically_valid"])
        self.assertGreater(one_sided[2].min(), 0.0)
        self.assertLess(one_sided[2].max(), 1.0)

        n = 200
        trials = 1.0e6
        index = np.arange(n, dtype=float)
        z = np.sqrt(2.0) * np.cos(2.0 * np.pi * index / n)
        e = np.sqrt(2.0) * np.sin(4.0 * np.pi * index / n)
        epsilon = 2.2e-5
        dense = np.column_stack([z, z + epsilon * e])
        delta = np.sqrt(4.0 * 0.0015 / (trials * n)) / epsilon
        truth = np.array([delta, -delta])
        near = AUDIT.BinomialObjective(
            sparse.csr_matrix(dense),
            np.full(n, trials) * expit(dense @ truth),
            np.full(n, trials),
        )
        near_targets = {
            f"treatment_basis::{j}::b{j}": np.eye(2)[j] for j in range(2)
        }
        certified = self.certify(
            near, self.raw_reference(near, near_targets), near_targets,
        )
        self.assertTrue(certified[0]["numerically_valid"])
        np.testing.assert_allclose(certified[1], truth, rtol=0, atol=2e-6)

    def test_conditional_polish_only_runs_after_failed_external_certificate(self):
        objective, _truth, targets = self.problem()
        trust = fit_solver(
            objective, "trust-ncg", np.zeros(3), 1000, 1e-9, 1e-6, 1,
            targets=targets,
        )
        untouched, no_polish = AUDIT.conditionally_polish_trust_candidate(
            objective, trust, 100, 1e-9, 1e-6, 1, targets, 1e-6,
            1e-4, 1e-10, 1e-10, 1e-7,
        )
        self.assertFalse(no_polish["applied"])
        np.testing.assert_array_equal(untouched[1], trust[1])

        failed_diagnostic = copy.deepcopy(trust[0])
        failed_diagnostic["numerically_valid"] = False
        failed_diagnostic["acceptance_source"] = "BLOCKED_TEST_FIXTURE"
        failed_diagnostic["full_hessian_stationarity_certificate"]["status"] = (
            "BLOCKED_TEST_FIXTURE"
        )
        failed = (failed_diagnostic, trust[1] + 0.01, trust[2], trust[3])
        polished, audit = AUDIT.conditionally_polish_trust_candidate(
            objective, failed, 100, 1e-9, 1e-6, 1, targets, 1e-6,
            1e-4, 1e-10, 1e-10, 1e-7,
        )
        self.assertTrue(audit["applied"])
        self.assertIn("before", audit)
        self.assertIn("after", audit)
        self.assertTrue(polished[0]["numerically_valid"])
        self.assertEqual(
            audit["status"], "PASS_CONDITIONAL_TRUST_EXACT_NEWTON_POLISH",
        )

    def test_full_identified_treatment_vector_and_both_cross_evaluations_bind(self):
        objective, _truth, targets = self.problem()
        reference = self.certify(
            objective, self.raw_reference(objective, targets), targets,
        )
        trust_diagnostic = {
            **reference[0], "method": "trust-path-unpolished-trust-ncg",
        }
        perturbed_theta = reference[1].copy()
        perturbed_theta[2] += 2.0e-6
        perturbed_probability = objective.probability(perturbed_theta)
        trust_diagnostic["objective_per_total"] = objective.function(
            perturbed_theta
        )
        trust_diagnostic["raw_negative_log_likelihood"] = objective.raw_nll(
            perturbed_theta
        )
        trust = (trust_diagnostic, perturbed_theta, perturbed_probability, [])
        tolerances = {
            "gradient_infinity_norm_per_total": 1e-6,
            "target_coefficient_absolute_difference": 1e-6,
            "fitted_probability_max_abs_difference": 1e-3,
            "objective_difference_per_total": 1e-8,
        }
        with mock.patch.object(
            AUDIT, "independent_evaluator_checks",
            wraps=AUDIT.independent_evaluator_checks,
        ) as cross_check:
            comparison = AUDIT.compare_trust_path_to_reference(
                objective, trust, reference, targets, tolerances,
            )
        self.assertEqual(cross_check.call_count, 2)
        self.assertEqual(comparison["identified_treatment_target_count"], 3)
        self.assertGreater(
            comparison[
                "maximum_absolute_full_identified_treatment_vector_difference"
            ], 1e-6,
        )
        self.assertFalse(
            comparison["checks"]["full_identified_treatment_vector"]
        )
        self.assertFalse(comparison["comparison_pass"])

        blocked_cross = copy.deepcopy(reference[0])
        blocked_cross["method"] = "trust-path-unpolished-trust-ncg"
        same = (blocked_cross, reference[1], reference[2], [])
        pass_check = {
            "status": "PASS_INDEPENDENT_EVALUATOR_AND_DERIVATIVE_CHECKS"
        }
        fail_check = {
            "status": "BLOCKED_INDEPENDENT_EVALUATOR_OR_DERIVATIVE_CHECK"
        }
        with mock.patch.object(
            AUDIT, "independent_evaluator_checks",
            side_effect=[pass_check, fail_check],
        ) as cross_check:
            contradiction = AUDIT.compare_trust_path_to_reference(
                objective, same, reference, targets, tolerances,
            )
        self.assertEqual(cross_check.call_count, 2)
        self.assertFalse(
            contradiction["checks"][
                "reference_candidate_cross_evaluator_equivalence"
            ]
        )
        self.assertFalse(contradiction["comparison_pass"])

    def test_original_dynamic_coordinates_bind_when_transformed_basis_would_pass(self):
        x = np.linspace(-1.0, 1.0, 40)
        model = bundle(
            young=np.full(40, 5.0), total=np.full(40, 10.0),
            first=["all"] * 40, second=["all"] * 40,
            regressors=np.column_stack([np.ones(40), x]), label="unused",
        )
        model.regressor_labels = ["event_a", "event_b"]
        model.focal_target_label = "post_average"
        model.focal_target_weights = np.array([0.5, 0.5])
        transformed, parameterization = AUDIT.target_coordinate_bundle(model)
        objective = AUDIT.BinomialObjective(
            sparse.csr_matrix(transformed.regressors),
            model.young, model.total,
        )
        targets = {}
        for row in parameterization[
            "original_coefficient_functionals_in_current_basis"
        ]:
            targets[
                f"original_treatment::{row['original_index']}::"
                f"{row['original_label']}"
            ] = np.asarray(row["weights"], float)
        targets.update({
            "treatment_basis::0::post_average": np.array([1.0, 0.0]),
            "treatment_basis::1::null": np.array([0.0, 1.0]),
        })
        reference_theta = np.zeros(2)
        trust_theta = np.array([0.75e-6, -0.75e-6])
        reference_diagnostic = {
            "method": "independent-damped-sparse-newton-irls",
            "numerically_valid": True,
            "objective_per_total": objective.function(reference_theta),
            "raw_negative_log_likelihood": objective.raw_nll(reference_theta),
        }
        trust_diagnostic = {
            **reference_diagnostic,
            "method": "trust-path-unpolished-trust-ncg",
            "objective_per_total": objective.function(trust_theta),
            "raw_negative_log_likelihood": objective.raw_nll(trust_theta),
        }
        comparison = AUDIT.compare_trust_path_to_reference(
            objective,
            (
                trust_diagnostic, trust_theta,
                objective.probability(trust_theta), [],
            ),
            (
                reference_diagnostic, reference_theta,
                objective.probability(reference_theta), [],
            ),
            targets, {
                "gradient_infinity_norm_per_total": 1.0,
                "target_coefficient_absolute_difference": 1e-6,
                "fitted_probability_max_abs_difference": 1.0,
                "objective_difference_per_total": 1.0,
            },
        )
        self.assertLessEqual(
            max(comparison[
                "transformed_basis_absolute_differences_nonbinding_diagnostic"
            ].values()), 1e-6,
        )
        self.assertGreater(
            comparison[
                "maximum_absolute_full_identified_treatment_vector_difference"
            ], 1e-6,
        )
        self.assertFalse(
            comparison["checks"]["full_identified_treatment_vector"]
        )
        self.assertFalse(comparison["comparison_pass"])

    def test_trust_reference_comparison_reports_stock_mean_and_eta_diagnostics(self):
        objective, _truth, targets = self.problem()
        reference = self.certify(
            objective, self.raw_reference(objective, targets), targets,
        )
        theta = reference[1] + np.array([1e-8, -2e-8, 1e-8])
        probability = objective.probability(theta)
        diagnostic = {
            **reference[0], "method": "trust-path-unpolished-trust-ncg",
            "objective_per_total": objective.function(theta),
            "raw_negative_log_likelihood": objective.raw_nll(theta),
        }
        result = AUDIT.compare_trust_path_to_reference(
            objective, (diagnostic, theta, probability, []), reference,
            targets, {
                "gradient_infinity_norm_per_total": 1e-6,
                "target_coefficient_absolute_difference": 1e-6,
                "fitted_probability_max_abs_difference": 1e-7,
                "objective_difference_per_total": 1e-10,
            },
        )
        probability_gap = probability - reference[2]
        fitted_gap = objective.total * probability_gap
        self.assertAlmostEqual(
            result[
                "normalized_conditional_fitted_mean_max_absolute_difference"
            ], np.max(np.abs(probability_gap)),
        )
        self.assertAlmostEqual(
            result["conditional_fitted_stock_mean_max_absolute_difference"],
            np.max(np.abs(fitted_gap)),
        )
        self.assertAlmostEqual(
            result["conditional_fitted_stock_mean_rmse"],
            np.sqrt(np.mean(fitted_gap ** 2)),
        )
        self.assertTrue(result["linear_predictor_all_finite"])
        self.assertGreaterEqual(
            result["linear_predictor_max_absolute_difference_nonbinding"], 0,
        )

    def test_shared_problem_binding_hashes_rows_design_normalization_and_targets(self):
        objective, _truth, targets = self.problem()
        active = np.ones(objective.design.shape[0], dtype=bool)
        active[-1] = False
        design = AUDIT.SparseDesign(
            nuisance=objective.design[active, :1].tocsr(),
            full=objective.design[active].copy().tocsr(),
            first_codes=np.zeros(int(active.sum()), dtype=int),
            second_codes=np.zeros(int(active.sum()), dtype=int),
            first_levels=["all"], second_levels=["all"],
            component_count=1,
            component_sizes=[{"first": 1, "second": 1}],
            second_references=["all"], nuisance_column_labels=["intercept"],
        )
        left = AUDIT.a1_shared_problem_binding(
            active, design, ["x", "x2"], targets,
        )
        right = AUDIT.a1_shared_problem_binding(
            active.copy(), design, ["x", "x2"], targets,
        )
        self.assertEqual(left, right)
        self.assertEqual(
            left["trust_path_problem_sha256"],
            left["zero_start_reference_problem_sha256"],
        )
        changed_active = np.ones_like(active)
        changed_active[0] = False
        changed = AUDIT.a1_shared_problem_binding(
            changed_active, design, ["x", "x2"], targets,
        )
        self.assertNotEqual(
            left["active_rows_sha256"], changed["active_rows_sha256"],
        )

    def test_dual_fitted_hessian_requires_raw_and_scaled_pd_for_both_candidates(self):
        objective, _truth, _targets = self.problem()
        probability = objective.probability(np.array([-0.25, 0.55, -0.20]))
        audit = AUDIT.dual_candidate_fitted_hessian_audit(
            objective.design, objective.total, probability, probability.copy(),
            objective.design.shape[1], 1e-10,
        )
        self.assertEqual(
            audit["status"],
            "PASS_BOTH_CANDIDATE_RAW_AND_SCALED_FITTED_HESSIANS",
        )
        self.assertTrue(all(audit["checks"].values()))
        for candidate in audit["candidates"].values():
            self.assertEqual(candidate["status"], "PASS_FULL_HESSIAN_SPECTRUM")
            self.assertEqual(candidate["rank_deficiency"], 0)
            self.assertTrue(candidate["positive_definite_at_declared_tolerance"])
            self.assertGreater(
                candidate["smallest_positive_or_extreme_eigenvalue"],
                candidate["rank_threshold"],
            )
            self.assertGreater(
                candidate[
                    "diagonally_scaled_smallest_positive_or_extreme_eigenvalue"
                ],
                candidate["diagonally_scaled_rank_threshold"],
            )

        blocked = AUDIT.dual_candidate_fitted_hessian_audit(
            objective.design, objective.total, np.ones_like(probability),
            probability, objective.design.shape[1], 1e-10,
        )
        self.assertEqual(
            blocked["status"],
            "BLOCKED_CANDIDATE_RAW_OR_SCALED_FITTED_HESSIAN",
        )
        self.assertFalse(blocked["checks"]["trust_path"])
        self.assertTrue(
            blocked["checks"]["independent_zero_start_reference"]
        )

    def test_lbfgsb_diagnostic_can_falsify_but_is_not_indispensable(self):
        objective, _truth, targets = self.problem()
        reference = self.certify(
            objective, self.raw_reference(objective, targets), targets,
        )
        trust = (
            {**reference[0], "method": "trust-path-unpolished-trust-ncg"},
            reference[1], reference[2], [],
        )
        tolerances = {
            "gradient_infinity_norm_per_total": 1e-7,
            "target_coefficient_absolute_difference": 1e-6,
            "fitted_probability_max_abs_difference": 1e-7,
            "objective_difference_per_total": 1e-10,
        }
        unavailable = AUDIT.audit_lbfgsb_diagnostic_contradictions(
            objective, None, trust, reference, targets, tolerances, 1e-4,
            {"error_type": "Synthetic", "message": "not available"},
        )
        self.assertFalse(unavailable["binding_pass"])
        self.assertFalse(unavailable["available"])
        self.assertEqual(
            unavailable["status"],
            "BLOCKED_LBFGSB_DIAGNOSTIC_NOT_RUN_OR_REPORTED",
        )

        unfinished_theta = np.zeros(3)
        unfinished_diagnostic = copy.deepcopy(reference[0])
        unfinished_diagnostic.update({
            "method": "L-BFGS-B", "numerically_valid": False,
        })
        unfinished_diagnostic[
            "full_hessian_stationarity_certificate"
        ]["status"] = "BLOCKED_TEST_NONSTATIONARY"
        unfinished = (
            unfinished_diagnostic, unfinished_theta,
            objective.probability(unfinished_theta), [],
        )
        unfinished_audit = AUDIT.audit_lbfgsb_diagnostic_contradictions(
            objective, unfinished, trust, reference, targets, tolerances, 1e-4,
        )
        self.assertTrue(unfinished_audit["binding_pass"])
        self.assertGreater(
            unfinished_audit[
                "maximum_declared_target_absolute_difference_vs_reference"
            ], 1e-6,
        )
        self.assertFalse(
            unfinished_audit["diagnostic_candidate_independently_stationary"]
        )

        # A lower recomputed likelihood is a contradiction even if the
        # purported binding candidates were marked valid by stale metadata.
        zero_diagnostic = copy.deepcopy(reference[0])
        zero_diagnostic["objective_per_total"] = objective.function(
            unfinished_theta
        )
        zero_diagnostic["raw_negative_log_likelihood"] = objective.raw_nll(
            unfinished_theta
        )
        zero_binding = (
            zero_diagnostic, unfinished_theta,
            objective.probability(unfinished_theta), [],
        )
        lower = AUDIT.audit_lbfgsb_diagnostic_contradictions(
            objective, reference, zero_binding, zero_binding, targets,
            tolerances, 1e-4,
        )
        self.assertFalse(lower["binding_pass"])
        self.assertFalse(
            lower["checks"]["no_materially_lower_diagnostic_objective"]
        )

        with mock.patch.object(
            AUDIT, "independent_evaluator_checks",
            return_value={
                "status": "BLOCKED_INDEPENDENT_EVALUATOR_OR_DERIVATIVE_CHECK"
            },
        ):
            derivative = AUDIT.audit_lbfgsb_diagnostic_contradictions(
                objective, unfinished, trust, reference, targets, tolerances,
                1e-4,
            )
        self.assertFalse(derivative["binding_pass"])
        self.assertFalse(
            derivative["checks"][
                "no_derivative_implementation_contradiction"
            ]
        )

    def test_stationary_lbfgsb_target_contradiction_blocks(self):
        objective, _truth, targets = self.problem()
        reference = self.certify(
            objective, self.raw_reference(objective, targets), targets,
        )
        trust = (
            {**reference[0], "method": "trust-path-unpolished-trust-ncg"},
            reference[1], reference[2], [],
        )
        theta = reference[1].copy()
        theta[2] += 2.0e-6
        diagnostic = copy.deepcopy(reference[0])
        diagnostic["method"] = "L-BFGS-B"
        output = (diagnostic, theta, objective.probability(theta), [])
        audit = AUDIT.audit_lbfgsb_diagnostic_contradictions(
            objective, output, trust, reference, targets, {
                "gradient_infinity_norm_per_total": 1.0,
                "target_coefficient_absolute_difference": 1e-6,
                "fitted_probability_max_abs_difference": 1.0,
                "objective_difference_per_total": 1e-10,
            }, 1.0,
        )
        self.assertTrue(
            audit["diagnostic_candidate_independently_stationary"]
        )
        self.assertFalse(
            audit["checks"]["no_stationary_declared_target_contradiction"]
        )
        self.assertFalse(audit["binding_pass"])


class AuthenticationAndSafetyTests(unittest.TestCase):
    def test_a1_cli_cell_receipt_requires_exact_bytes_before_json_loading(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            receipt_path = root / "receipt.json"
            payload = {"status": "same semantics", "nested": {"value": 1}}
            original_bytes = json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            receipt_path.write_bytes(original_bytes)
            analysis = {
                "amendment_a1": {
                    "authenticated_cell_reuse": {
                        "receipt_sha256": hashlib.sha256(
                            original_bytes
                        ).hexdigest(),
                    },
                },
                "_a1_parent_analysis": {},
            }
            # Reformatting changes only bytes, not parsed JSON semantics.
            receipt_path.write_text(
                json.dumps(payload, indent=2, sort_keys=False) + "\n",
                encoding="utf-8",
            )
            self.assertEqual(json.loads(original_bytes), json.loads(
                receipt_path.read_text(encoding="utf-8")
            ))
            with (
                mock.patch.object(AUDIT, "load_json") as loader,
                mock.patch.object(AUDIT, "cell_receipt_authentication_checks")
                as semantic_checks,
            ):
                with self.assertRaisesRegex(
                    AUDIT.AuditBlocked, "receipt bytes differ",
                ):
                    AUDIT.authenticate_cells(
                        root / "cells.csv", receipt_path, {}, analysis,
                    )
            loader.assert_not_called()
            semantic_checks.assert_not_called()

    def test_run_cannot_accept_caller_supplied_receipt_attestations(self):
        self.assertEqual(
            list(inspect.signature(AUDIT.run).parameters), ["args"],
        )
        with mock.patch.object(AUDIT, "acquire_execution_attestations") as acquire:
            with self.assertRaises(TypeError):
                AUDIT.run(
                    mock.Mock(),
                    {"status": "FABRICATED_BINDING"},
                    {"status": "FABRICATED_RUNTIME"},
                )
        acquire.assert_not_called()

    def test_attestation_acquisition_uses_live_process_boundaries(self):
        args = mock.Mock()
        binding = {"status": "AUTHENTICATED_BINDING"}
        runtime = {"status": "AUTHENTICATED_RUNTIME"}
        with (
            mock.patch.object(
                AUDIT, "build_execution_command_binding",
                return_value=binding,
            ) as build,
            mock.patch.object(
                AUDIT, "execution_runtime_authentication",
                return_value=runtime,
            ) as authenticate_runtime,
            mock.patch.object(AUDIT.sys, "argv", ["runner.py", "--flag", "value"]),
            mock.patch.object(
                AUDIT.sys, "orig_argv",
                ["python", "-I", "runner.py", "--flag", "value"],
                create=True,
            ),
            mock.patch.dict(AUDIT.os.environ, {"JOB_ID": "123"}, clear=True),
        ):
            observed = AUDIT.acquire_execution_attestations(args)
        self.assertEqual(observed, (binding, runtime))
        build.assert_called_once_with(
            args, ["--flag", "value"],
            ["python", "-I", "runner.py", "--flag", "value"],
            {"JOB_ID": "123"},
        )
        authenticate_runtime.assert_called_once_with()

    def test_scheduler_binding_rejects_mismatched_output_leaf(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = pathlib.Path(temporary)
            args = mock.Mock(
                output_parent=parent,
                output_dir=parent / "gate1_numerical_sge_999",
            )
            AUDIT.require_job_derived_output_leaf(
                args, "gate1_numerical_sge_999",
            )
            args.output_dir = parent / "fabricated-leaf"
            with self.assertRaisesRegex(
                AUDIT.AuditBlocked, "scheduler-job-derived",
            ):
                AUDIT.require_job_derived_output_leaf(
                    args, "gate1_numerical_sge_999",
                )

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

    def test_prepublication_state_reauthenticates_every_mutable_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            repo = root / "repo"
            external = root / "external"
            repo.mkdir(); external.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=repo, check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "YAX test"],
                cwd=repo, check=True,
            )
            repo_paths = [
                AUDIT.CELL_SPEC_REL, AUDIT.TARGET_SPEC_REL,
                AUDIT.CELL_CODE_REL, AUDIT.TARGET_CODE_REL,
                AUDIT.PRE_EXECUTION_AUTHORIZATION_REL,
                pathlib.Path("submitted/baseline.py"),
            ]
            for relative in repo_paths:
                path = repo / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(str(relative) + "\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=repo, check=True)
            subprocess.run(
                ["git", "commit", "-qm", "fixture"], cwd=repo, check=True,
            )
            external_paths = {}
            for name in (
                "canonical_spec", "analysis_spec", "cells", "cells_receipt",
                "legacy_engine",
            ):
                path = external / name
                path.write_text(name + "\n", encoding="utf-8")
                external_paths[name] = path
            args = mock.Mock(
                canonical_spec=external_paths["canonical_spec"],
                analysis_spec=external_paths["analysis_spec"],
                cells=external_paths["cells"],
                cells_receipt=external_paths["cells_receipt"],
                legacy_engine=external_paths["legacy_engine"],
            )
            analysis = {"design_parity": {"submitted_source_sha256": {
                "submitted/baseline.py": "fixture-hash",
            }}}
            canonical = {"spec_id": "fixture"}
            authorization = {"authorization_id": "fixture-auth"}
            runtime = {"status": "fixture-runtime"}
            with (
                mock.patch.object(
                    AUDIT, "validate_pre_execution_authorization",
                    return_value=authorization,
                ),
                mock.patch.object(
                    AUDIT, "execution_runtime_authentication",
                    return_value=runtime,
                ),
            ):
                initial = AUDIT.authenticated_execution_state(
                    args, repo, canonical, analysis,
                )
                passed = AUDIT.require_unchanged_execution_state(
                    initial, args, repo, canonical, analysis,
                )
                self.assertEqual(
                    passed["status"],
                    "PASS_COMPLETE_PREPUBLICATION_REAUTHENTICATION",
                )
                external_paths["cells"].write_text(
                    "mutated aggregate\n", encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    AUDIT.AuditBlocked, "state changed",
                ):
                    AUDIT.require_unchanged_execution_state(
                        initial, args, repo, canonical, analysis,
                    )
                external_paths["cells"].write_text(
                    "cells\n", encoding="utf-8",
                )
                (repo / AUDIT.TARGET_CODE_REL).write_text(
                    "changed target code\n", encoding="utf-8",
                )
                with self.assertRaisesRegex(
                    AUDIT.AuditBlocked, "clean authorization checkout",
                ):
                    AUDIT.authenticated_execution_state(
                        args, repo, canonical, analysis,
                    )

    def test_prepublication_state_rejects_any_changed_snapshot(self):
        with mock.patch.object(
            AUDIT, "authenticated_execution_state",
            return_value={"state": "changed"},
        ):
            with self.assertRaisesRegex(AUDIT.AuditBlocked, "state changed"):
                AUDIT.require_unchanged_execution_state(
                    {"state": "initial"}, mock.Mock(), pathlib.Path("."),
                    {}, {},
                )

    def test_post_receipt_mutation_blocks_before_publication(self):
        reservation = mock.Mock()
        with mock.patch.object(
            AUDIT, "require_unchanged_execution_state",
            side_effect=AUDIT.AuditBlocked("synthetic post-receipt mutation"),
        ):
            with self.assertRaisesRegex(
                AUDIT.AuditBlocked, "post-receipt mutation",
            ):
                AUDIT.publish_after_final_reauthentication(
                    reservation, {"initial": True}, mock.Mock(),
                    pathlib.Path("."), {}, {},
                )
        reservation.publish.assert_not_called()

    def test_final_reauthentication_directly_precedes_publication(self):
        events = []
        reservation = mock.Mock()
        semantics = {"status": "PASS_SYNTHETIC_PUBLICATION"}
        reservation.publish.side_effect = lambda: (
            events.append("publish") or semantics
        )
        with mock.patch.object(
            AUDIT, "require_unchanged_execution_state",
            side_effect=lambda *args: events.append("reauthenticate"),
        ):
            observed = AUDIT.publish_after_final_reauthentication(
                reservation, {"initial": True}, mock.Mock(),
                pathlib.Path("."), {}, {},
            )
        self.assertEqual(events, ["reauthenticate", "publish"])
        self.assertIs(observed, semantics)

    def test_production_publication_discloses_fallback_in_stdout_not_receipt_claim(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            repo = root / "repo"
            outside = root / "outside"
            repo.mkdir(); outside.mkdir()
            source = outside / "input.csv"
            source.write_text("input", encoding="utf-8")
            reservation = AUDIT.AtomicOutputLeaf.reserve(
                outside / "gate1_numerical_sge_67890", repo, [source],
            )
            precommit_protocol = AUDIT.precommit_publication_protocol()
            receipt = {
                "prepublication_revalidation": {
                    "residual_window": (
                        "bounded through publication; backend not yet observed"
                    ),
                },
                "publication_protocol": precommit_protocol,
            }
            (reservation.staging / "EXECUTION_RECEIPT.json").write_text(
                json.dumps(receipt, sort_keys=True) + "\n", encoding="utf-8",
            )
            with (
                mock.patch.object(
                    SAFETY, "_try_kernel_atomic_rename_noreplace",
                    return_value=(
                        False, "linux_renameat2_RENAME_NOREPLACE",
                        SAFETY.errno.EINVAL,
                    ),
                ),
                mock.patch.object(
                    AUDIT, "require_unchanged_execution_state",
                    return_value={
                        "status": "PASS_COMPLETE_PREPUBLICATION_REAUTHENTICATION"
                    },
                ),
            ):
                actual_semantics = AUDIT.publish_after_final_reauthentication(
                    reservation, {"initial": True}, mock.Mock(), repo, {}, {},
                )
            with mock.patch("builtins.print") as output:
                payload = AUDIT.emit_final_publication_stdout(
                    "PASS_ALL_CORE_TARGETS_NUMERICALLY_AUDITED",
                    reservation.target.name,
                    reservation.post_commit_cleanup_warnings,
                    actual_semantics,
                )
            printed = json.loads(output.call_args.args[0])
            self.assertEqual(printed, payload)
            self.assertEqual(
                printed["publication_semantics"]["status"],
                "PASS_PORTABLE_GPFS_SAME_PARENT_PUBLICATION",
            )
            self.assertFalse(
                printed["publication_semantics"][
                    "kernel_no_replace_guarantee"
                ]
            )
            self.assertIn(
                "not eliminated",
                printed["publication_semantics"][
                    "bounded_noncooperating_same_user_toctou"
                ],
            )
            published_receipt = json.loads(
                (reservation.target / "EXECUTION_RECEIPT.json").read_text(
                    encoding="utf-8"
                )
            )
            protocol = published_receipt["publication_protocol"]
            self.assertFalse(protocol["actual_backend_claimed_before_commit"])
            self.assertFalse(protocol["fallback_kernel_no_replace_guarantee"])
            self.assertIn(
                "not eliminated",
                protocol[
                    "fallback_bounded_noncooperating_same_user_toctou"
                ],
            )
            self.assertNotIn("publication_semantics", published_receipt)

    def test_final_stdout_downgrades_overclaim_without_postcommit_exception(self):
        with mock.patch("builtins.print") as output:
            payload = AUDIT.emit_final_publication_stdout(
                "PASS", "gate1_numerical_sge_1", (), {
                    "status": "PASS_BAD_FIXTURE",
                    "publication_backend": "bad",
                    "same_parent_directory_rename_atomic": True,
                    "kernel_no_replace_guarantee": True,
                    "portable_gpfs_fallback_used": True,
                    "bounded_noncooperating_same_user_toctou": None,
                },
            )
        self.assertEqual(json.loads(output.call_args.args[0]), payload)
        self.assertEqual(
            payload["publication_semantics"]["status"],
            "POSTCOMMIT_SEMANTICS_WITHHELD_FAIL_CLOSED",
        )
        self.assertIsNone(
            payload["publication_semantics"]["kernel_no_replace_guarantee"]
        )

    def test_final_stdout_broken_pipe_never_raises_after_commit(self):
        valid_semantics = {
            "status": "PASS_PORTABLE_GPFS_SAME_PARENT_PUBLICATION",
            "publication_backend": (
                "posix_os_rename_under_exclusive_sibling_lock"
            ),
            "same_parent_directory_rename_atomic": True,
            "kernel_no_replace_guarantee": False,
            "portable_gpfs_fallback_used": True,
            "bounded_noncooperating_same_user_toctou": (
                "not eliminated: synthetic bounded lstat-to-rename race"
            ),
        }
        with mock.patch(
            "builtins.print", side_effect=BrokenPipeError("closed scheduler pipe"),
        ):
            result = AUDIT.emit_final_publication_stdout(
                "PASS", "gate1_numerical_sge_2", (), valid_semantics,
            )
        self.assertEqual(
            result["scheduler_stdout_emission_status"],
            "FAILED_AFTER_COMMIT_WITHOUT_PROPAGATION",
        )
        self.assertEqual(result["scheduler_stdout_error_type"], "BrokenPipeError")
        self.assertEqual(
            result["publication_semantics"]["status"],
            "POSTCOMMIT_STDOUT_UNAVAILABLE",
        )

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
            with self.assertRaisesRegex(
                AUDIT.OutputSafetyError, "already reserved",
            ):
                AUDIT.AtomicOutputLeaf.reserve(target, repo, [source])
            (reservation.staging / "done.txt").write_text("complete", encoding="utf-8")
            reservation.publish()
            self.assertEqual((target / "done.txt").read_text(encoding="utf-8"), "complete")
            self.assertFalse(reservation.staging.exists())
            self.assertTrue(
                reservation.publication_semantics[
                    "same_parent_directory_rename_atomic"
                ]
            )

    def test_gpfs_einval_uses_truthful_portable_atomic_rename_semantics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            repo = root / "repo"
            outside = root / "outside"
            repo.mkdir(); outside.mkdir()
            source = outside / "input.csv"
            source.write_text("input", encoding="utf-8")
            reservation = AUDIT.AtomicOutputLeaf.reserve(
                outside / "gate1_numerical_sge_12345", repo, [source],
            )
            (reservation.staging / "done.txt").write_text(
                "complete", encoding="utf-8",
            )
            with mock.patch.object(
                SAFETY, "_try_kernel_atomic_rename_noreplace",
                return_value=(
                    False, "linux_renameat2_RENAME_NOREPLACE",
                    SAFETY.errno.EINVAL,
                ),
            ):
                publication_receipt = reservation.publish()
            semantics = json.loads(json.dumps(publication_receipt))
            self.assertEqual(semantics, reservation.publication_semantics)
            self.assertEqual(
                semantics["status"],
                "PASS_PORTABLE_GPFS_SAME_PARENT_PUBLICATION",
            )
            self.assertTrue(semantics["portable_gpfs_fallback_used"])
            self.assertTrue(semantics["same_parent_directory_rename_atomic"])
            self.assertFalse(semantics["kernel_no_replace_guarantee"])
            self.assertTrue(
                semantics[
                    "target_absence_rechecked_immediately_before_portable_rename"
                ]
            )
            self.assertIn(
                "not eliminated",
                semantics["bounded_noncooperating_same_user_toctou"],
            )
            self.assertIn(
                "not kernel-enforced",
                semantics["target_replacement_prevention"],
            )
            self.assertEqual(
                (reservation.target / "done.txt").read_text(encoding="utf-8"),
                "complete",
            )
            self.assertFalse(reservation.lock.exists())

    def test_portable_fallback_collision_recheck_precedes_os_rename(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = pathlib.Path(temporary)
            source = parent / "staging"
            target = parent / "target"
            source.mkdir()
            original_rename = SAFETY.os.rename
            guard_calls = 0

            def guard():
                nonlocal guard_calls
                guard_calls += 1
                if guard_calls == 2:
                    target.mkdir()
                return {"status": "PASS_SYNTHETIC_GUARD"}

            with (
                mock.patch.object(
                    SAFETY, "_try_kernel_atomic_rename_noreplace",
                    return_value=(
                        False, "linux_renameat2_RENAME_NOREPLACE",
                        SAFETY.errno.EINVAL,
                    ),
                ),
                mock.patch.object(
                    SAFETY.os, "rename", wraps=original_rename,
                ) as portable_rename,
            ):
                with self.assertRaisesRegex(
                    AUDIT.OutputSafetyError, "portable publication recheck",
                ):
                    SAFETY.atomic_publish_same_parent(source, target, guard)
            portable_rename.assert_not_called()
            self.assertEqual(guard_calls, 2)
            self.assertTrue(source.is_dir())
            self.assertTrue(target.is_dir())

    def test_kernel_noreplace_is_attempted_before_portable_rename(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = pathlib.Path(temporary)
            source = parent / "staging"
            target = parent / "target"
            source.mkdir()
            original_rename = SAFETY.os.rename

            def kernel_commit(source_path, target_path):
                original_rename(source_path, target_path)
                return True, "synthetic_kernel_noreplace", None

            with (
                mock.patch.object(
                    SAFETY, "_try_kernel_atomic_rename_noreplace",
                    side_effect=kernel_commit,
                ) as kernel,
                mock.patch.object(SAFETY.os, "rename") as portable_rename,
            ):
                semantics = SAFETY.atomic_publish_same_parent(
                    source, target,
                    lambda: {"status": "PASS_SYNTHETIC_GUARD"},
                )
            kernel.assert_called_once_with(source, target)
            portable_rename.assert_not_called()
            self.assertTrue(semantics["kernel_no_replace_guarantee"])
            self.assertFalse(semantics["portable_gpfs_fallback_used"])
            self.assertIsNone(
                semantics["bounded_noncooperating_same_user_toctou"]
            )
            self.assertTrue(target.is_dir())

    def test_publication_lock_and_staging_inode_state_are_revalidated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            repo = root / "repo"
            outside = root / "outside"
            repo.mkdir(); outside.mkdir()
            source = outside / "input.csv"
            source.write_text("input", encoding="utf-8")
            reservation = AUDIT.AtomicOutputLeaf.reserve(
                outside / "gate1_numerical_sge_54321", repo, [source],
            )
            state = reservation.verify_publication_state()
            self.assertEqual(
                state["status"],
                "PASS_EXCLUSIVE_SIBLING_LOCK_AND_STAGING_INODE",
            )
            replacement = reservation.staging.with_name(
                reservation.staging.name + "-original"
            )
            SAFETY.os.rename(reservation.staging, replacement)
            reservation.staging.mkdir()
            with self.assertRaisesRegex(
                AUDIT.OutputSafetyError, "staging inode identity changed",
            ):
                reservation.verify_publication_state()
            reservation.staging.rmdir()
            SAFETY.os.rename(replacement, reservation.staging)
            SAFETY.os.pwrite(
                reservation.lock_fd,
                b"X" * len(reservation.lock_token), 0,
            )
            with self.assertRaisesRegex(
                AUDIT.OutputSafetyError, "lock token changed",
            ):
                reservation.verify_publication_state()
            SAFETY.os.pwrite(
                reservation.lock_fd, reservation.lock_token, 0,
            )
            reservation.lock.unlink()
            reservation.lock.write_bytes(reservation.lock_token)
            with self.assertRaisesRegex(
                AUDIT.OutputSafetyError, "lock inode identity changed",
            ):
                reservation.verify_publication_state()
            SAFETY.os.close(reservation.lock_fd)
            reservation.lock_fd = None
            reservation.lock.unlink()
            SAFETY.shutil.rmtree(reservation.staging)

    def test_atomic_output_leaf_never_raises_after_publication_commit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            repo = root / "repo"
            outside = root / "outside"
            repo.mkdir(); outside.mkdir()
            source = outside / "input.csv"
            source.write_text("input", encoding="utf-8")
            reservation = AUDIT.AtomicOutputLeaf.reserve(
                outside / "committed-run", repo, [source]
            )
            (reservation.staging / "done.txt").write_text(
                "complete", encoding="utf-8"
            )
            def fail_cleanup_after_closing() -> None:
                if reservation.lock_fd is not None:
                    import os
                    os.close(reservation.lock_fd)
                    reservation.lock_fd = None
                raise OSError(5, "synthetic cleanup failure")

            with mock.patch.object(
                reservation, "release_lock", side_effect=fail_cleanup_after_closing
            ):
                reservation.publish()
            self.assertTrue(reservation.published)
            self.assertEqual(
                (reservation.target / "done.txt").read_text(encoding="utf-8"),
                "complete",
            )
            self.assertEqual(
                reservation.post_commit_cleanup_warnings,
                ("lock_cleanup_errno_5",),
            )
            reservation.release_lock()


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
        analysis = json.loads((HERE / "ANALYSIS_SPEC_A1.json").read_text())
        contract = analysis["software"]["runtime_contract"]
        observed = AUDIT.hashlib.sha256(AUDIT.canonical_bytes(contract["payload"])).hexdigest()
        self.assertEqual(observed, contract["payload_sha256"])

    def test_analysis_spec_identifier_is_valid(self):
        spec = json.loads((HERE / "ANALYSIS_SPEC_A1.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["audit_spec_id"], AUDIT.expected_audit_spec_id(spec))

    def test_a1_spec_preserves_parent_scientific_target_and_cell_identity(self):
        repo = HERE.parents[3]
        spec = json.loads((HERE / "ANALYSIS_SPEC_A1.json").read_text())
        parent = json.loads((HERE / "ANALYSIS_SPEC.json").read_text())
        self.assertEqual(
            AUDIT.scientific_target_payload(spec),
            AUDIT.scientific_target_payload(parent),
        )
        self.assertEqual(
            AUDIT.scientific_target_fingerprint(spec),
            spec["amendment_a1"]["scientific_target_fingerprint"]["sha256"],
        )
        validated_parent = AUDIT.validate_a1_amendment(
            repo, HERE / "ANALYSIS_SPEC_A1.json", spec,
        )
        self.assertEqual(
            validated_parent["audit_spec_id"], parent["audit_spec_id"]
        )
        retained = json.loads((
            repo
            / spec["amendment_a1"]["authenticated_cell_reuse"]["receipt_path"]
        ).read_text())
        self.assertEqual(
            retained["analysis_spec_id"], parent["audit_spec_id"]
        )
        self.assertNotEqual(
            retained["analysis_spec_id"], spec["audit_spec_id"]
        )

    def test_a1_scientific_or_authority_change_fails_closed(self):
        repo = HERE.parents[3]
        spec = json.loads((HERE / "ANALYSIS_SPEC_A1.json").read_text())
        changed = copy.deepcopy(spec)
        changed["models"][0]["calendar"] = "changed scientific calendar"
        with self.assertRaisesRegex(AUDIT.AuditBlocked, "scientific"):
            AUDIT.validate_a1_amendment(
                repo, HERE / "ANALYSIS_SPEC_A1.json", changed,
            )
        changed = copy.deepcopy(spec)
        changed["amendment_a1"]["authorization"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(AUDIT.AuditBlocked, "authorization"):
            AUDIT.validate_a1_amendment(
                repo, HERE / "ANALYSIS_SPEC_A1.json", changed,
            )

    def test_a1_preserved_blocked_model_audit_is_byte_and_semantic_bound(self):
        source_repo = HERE.parents[3]
        source_spec_path = source_repo / AUDIT.A1_SPEC_REL
        source_spec = json.loads(source_spec_path.read_text())
        blocked = source_spec["amendment_a1"]["preserved_blocked_run"]
        relative_paths = (
            AUDIT.A1_SPEC_REL,
            AUDIT.A1_OWNER_AUTHORIZATION_REL,
            pathlib.Path(
                source_spec["amendment_a1"]["parent_numerical_spec"]["path"]
            ),
            pathlib.Path(blocked["numerical_receipt_path"]),
            pathlib.Path(blocked["path"]) / "numerical" / "MODEL_AUDIT.json",
            pathlib.Path(
                source_spec["amendment_a1"]["authenticated_cell_reuse"][
                    "receipt_path"
                ]
            ),
        )
        with tempfile.TemporaryDirectory() as temporary:
            repo = pathlib.Path(temporary)
            for relative in relative_paths:
                destination = repo / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes((source_repo / relative).read_bytes())
            spec_path = repo / AUDIT.A1_SPEC_REL
            spec = json.loads(spec_path.read_text())
            AUDIT.validate_a1_amendment(repo, spec_path, spec)

            model_path = (
                repo / pathlib.Path(blocked["path"])
                / "numerical" / "MODEL_AUDIT.json"
            )
            model_path.write_bytes(model_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                AUDIT.AuditBlocked, "MODEL_AUDIT bytes",
            ):
                AUDIT.validate_a1_amendment(repo, spec_path, spec)

            model_document = json.loads(
                (source_repo / pathlib.Path(blocked["path"])
                 / "numerical" / "MODEL_AUDIT.json").read_text()
            )
            model_document["models"][0]["classification"] = (
                "PASS_FINITE_EXTENDED_MLE_TARGET"
            )
            model_path.write_text(
                json.dumps(model_document, indent=2, sort_keys=True) + "\n"
            )
            changed_model_sha = AUDIT.sha256_file(model_path)
            receipt_path = repo / pathlib.Path(blocked["numerical_receipt_path"])
            receipt = json.loads(receipt_path.read_text())
            receipt["output_hashes"]["MODEL_AUDIT.json"] = changed_model_sha
            receipt_path.write_text(
                json.dumps(receipt, indent=2, sort_keys=True) + "\n"
            )
            changed = copy.deepcopy(spec)
            changed["amendment_a1"]["preserved_blocked_run"][
                "model_audit_sha256"
            ] = changed_model_sha
            changed["amendment_a1"]["preserved_blocked_run"][
                "numerical_receipt_sha256"
            ] = AUDIT.sha256_file(receipt_path)
            with self.assertRaisesRegex(
                AUDIT.AuditBlocked, "MODEL_AUDIT semantics",
            ):
                AUDIT.validate_a1_amendment(repo, spec_path, changed)

    def test_analysis_spec_is_bound_to_canonical_spec_and_runner(self):
        canonical = HERE.parent / "contracts/specs/canonical_baseline_reproduction_v2.json"
        loaded, audit = AUDIT.validate_specs(canonical, HERE / "ANALYSIS_SPEC_A1.json")
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
        models = json.loads((HERE / "ANALYSIS_SPEC_A1.json").read_text())["models"]
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
        analysis = json.loads((HERE / "ANALYSIS_SPEC_A1.json").read_text())
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
        analysis = json.loads((HERE / "ANALYSIS_SPEC_A1.json").read_text())
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
        analysis = json.loads((HERE / "ANALYSIS_SPEC_A1.json").read_text())
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
