"""Tests that stale and failed upstream runs cannot pass downstream gates."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dependency_guard as guard


H = "a" * 64
SPEC = "yaxspec_v1_" + "b" * 64


class DependencyGuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "upstream.json").write_text('{"value":1}\n', encoding="utf-8")
        (self.root / "downstream.json").write_text('{"value":2}\n', encoding="utf-8")
        up_sha = hashlib.sha256((self.root / "upstream.json").read_bytes()).hexdigest()
        down_sha = hashlib.sha256((self.root / "downstream.json").read_bytes()).hexdigest()
        self.up = {
            "run_id": "up", "spec_id": SPEC, "status": "SUCCESS",
            "code_sha256": H, "environment_sha256": H, "command": "run up",
            "dependencies": [],
            "outputs": [{"result_id": "result-up", "path": "upstream.json", "sha256": up_sha}],
        }
        self.up["run_fingerprint"] = guard.compute_run_fingerprint(self.up)
        self.down = {
            "run_id": "down", "spec_id": SPEC, "status": "SUCCESS",
            "code_sha256": H, "environment_sha256": H, "command": "run down",
            "dependencies": [{"run_id": "up", "result_id": "result-up", "artifact_sha256": up_sha}],
            "outputs": [{"result_id": "result-down", "path": "downstream.json", "sha256": down_sha}],
        }
        self.down["run_fingerprint"] = guard.compute_run_fingerprint(self.down)

    def tearDown(self):
        self.tmp.cleanup()

    def document(self):
        return {"schema_version": "yax-run-dag-v1", "runs": [self.up, self.down]}

    def test_valid_dependency_chain(self):
        guard.validate_manifest(self.document(), self.root)

    def test_upstream_hash_change_invalidates_downstream(self):
        document = copy.deepcopy(self.document())
        document["runs"][0]["outputs"][0]["sha256"] = "c" * 64
        with self.assertRaises(guard.DependencyError):
            guard.validate_manifest(document, self.root)

    def test_fingerprint_detects_command_change(self):
        document = copy.deepcopy(self.document())
        document["runs"][1]["command"] = "changed command"
        with self.assertRaises(guard.DependencyError):
            guard.validate_manifest(document, self.root)

    def test_failed_upstream_blocks_only_descendant(self):
        document = copy.deepcopy(self.document())
        log = self.root / "failure.log"
        log.write_text("retained failure\n", encoding="utf-8")
        failed = document["runs"][0]
        failed["status"] = "FAILED"
        failed["failure"] = {
            "message": "synthetic failure", "log_path": "failure.log",
            "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        }
        failed["run_fingerprint"] = guard.compute_run_fingerprint(failed)
        independent_file = self.root / "independent.json"
        independent_file.write_text("{}\n", encoding="utf-8")
        independent = {
            "run_id": "independent", "spec_id": SPEC, "status": "SUCCESS",
            "code_sha256": H, "environment_sha256": H, "command": "run independent",
            "dependencies": [], "outputs": [{"result_id": "result-independent",
              "path": "independent.json",
              "sha256": hashlib.sha256(independent_file.read_bytes()).hexdigest()}],
        }
        independent["run_fingerprint"] = guard.compute_run_fingerprint(independent)
        document["runs"].append(independent)
        with self.assertRaises(guard.DependencyError):
            guard.validate_manifest(document, self.root)
        # Removing only the invalid descendant leaves the failed record and
        # independent successful branch structurally valid.
        document["runs"] = [failed, independent]
        guard.validate_manifest(document, self.root)

    def test_cycle_fails(self):
        document = self.document()
        document["runs"][0]["dependencies"] = [{
            "run_id": "down", "result_id": "result-down",
            "artifact_sha256": document["runs"][1]["outputs"][0]["sha256"],
        }]
        document["runs"][0]["run_fingerprint"] = guard.compute_run_fingerprint(document["runs"][0])
        with self.assertRaises(guard.DependencyError):
            guard.validate_manifest(document, self.root)


class TargetDependencyGuardTests(unittest.TestCase):
    MODEL_IDS = [
        "pooled",
        "family_post",
        "family_month",
        "dynamics_unconditioned",
        "dynamics_family_month",
        "post_2020_unconditioned",
        "post_2020_family_month",
        "seasonal_quintile_month_unconditioned",
        "seasonal_quintile_month_family_month",
        "seasonal_occupation_month_unconditioned",
        "seasonal_occupation_month_family_month",
    ]
    CANONICAL = SPEC
    CELLS_SHA = "c" * 64
    AUDIT_SPEC = "yaxnumspec_v1_" + "d" * 64
    OLD_AUDIT_SPEC = "yaxnumspec_v1_" + "e" * 64

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "authorization.md").write_text(
            "owner-authorized A1\n", encoding="utf-8"
        )
        authorization_sha = self.digest("authorization.md")

        cells = {
            "schema_version": "yax-numerical-cells-receipt-v1",
            "status": "PASS_FRESH_AGGREGATE_REBUILD",
            "canonical_spec_id": self.CANONICAL,
            "cells_sha256": self.CELLS_SHA,
        }
        self.write_json("cells_receipt.json", cells)
        cells_receipt_sha = self.digest("cells_receipt.json")
        target_audit = {
            "status": "PASS_EXACT_TARGET_AUDIT",
            "canonical_spec_id": self.CANONICAL,
            "authenticated_cells_sha256": self.CELLS_SHA,
        }
        self.write_json("target_audit.json", target_audit)
        target_audit_sha = self.digest("target_audit.json")
        target_receipt = {
            "schema_version": "yax-exact-target-audit-receipt-v1",
            "status": "PASS_EXACT_TARGET_AUDIT",
            "canonical_spec_id": self.CANONICAL,
            "authenticated_cells_sha256": self.CELLS_SHA,
            "source_aggregate_receipt_sha256": cells_receipt_sha,
            "artifact_hashes": {
                "EXACT_TARGET_AUDIT.json": target_audit_sha,
            },
        }
        self.write_json("target_receipt.json", target_receipt)

        consumers = [
            {
                "consumer_id": f"use.{model_id}",
                "required_model_ids": [model_id],
                "downstream_requirement_ids": [],
            }
            for model_id in self.MODEL_IDS
        ]
        consumers.append({
            "consumer_id": "compare.pooled.family_month",
            "required_model_ids": ["pooled", "family_month"],
            "downstream_requirement_ids": ["Y01"],
        })
        self.target_map = {
            "schema_version": guard.TARGET_MAP_SCHEMA,
            "authorization": {
                "path": "authorization.md", "sha256": authorization_sha,
            },
            "unmapped_consumer_policy": "FAIL_CLOSED",
            "whole_suite_rule": (
                "The overall numerical suite remains BLOCKED unless all 11 "
                "registered models are certified, even when individual "
                "consumers are released."
            ),
            "downstream_requirement_model_contract": {
                "Y01": ["pooled", "family_month"],
            },
            "certification_contract": {
                "audit_schema_version": guard.NUMERICAL_AUDIT_SCHEMA,
                "receipt_schema_version": guard.NUMERICAL_RECEIPT_SCHEMA,
                "canonical_spec_id": self.CANONICAL,
                "required_a1_audit_spec_id": self.AUDIT_SPEC,
                "required_a1_audit_spec_sha256": H,
                "required_a1_runner_code_sha256": H,
                "forbidden_audit_spec_ids": [self.OLD_AUDIT_SPEC],
                "model_pass_classification": (
                    guard.A1_MODEL_PASS_CLASSIFICATION
                ),
                "target_estimability_pass_status": guard.A1_TARGET_PASS_STATUS,
                "solver_comparison_pass_status": (
                    guard.A1_COMPARISON_PASS_STATUS
                ),
                "target_profile_pass_status": guard.A1_PROFILE_PASS_STATUS,
                "reference_method": guard.A1_REFERENCE_METHOD,
                "a1_model_certificate_status": guard.A1_CERTIFICATE_STATUS,
                "primary_path": guard.A1_PRIMARY_PATH,
                "target_absolute_tolerance": 1e-6,
            },
            "non_model_prerequisites": {
                "authenticated_cells": {
                    "requirement_ids": ["T02", "T03"],
                    "path": "cells_receipt.json",
                    "sha256": cells_receipt_sha,
                    "receipt_path": "cells_receipt.json",
                    "receipt_sha256": cells_receipt_sha,
                    "expected_status": "PASS_FRESH_AGGREGATE_REBUILD",
                },
                "exact_target_audit": {
                    "requirement_ids": ["T01"],
                    "path": "target_audit.json",
                    "sha256": target_audit_sha,
                    "receipt_path": "target_receipt.json",
                    "receipt_sha256": self.digest("target_receipt.json"),
                    "expected_status": "PASS_EXACT_TARGET_AUDIT",
                },
            },
            "registered_model_ids": list(self.MODEL_IDS),
            "consumers": consumers,
        }
        map_path = self.root / guard.TARGET_DEPENDENCY_MAP_REL
        map_path.parent.mkdir(parents=True)
        self.write_json(guard.TARGET_DEPENDENCY_MAP_REL.as_posix(), self.target_map)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "synthetic@example.invalid"],
            cwd=self.root, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Synthetic Test"],
            cwd=self.root, check=True,
        )
        subprocess.run(["git", "add", "."], cwd=self.root, check=True)
        subprocess.run(
            ["git", "commit", "-qm", "pre-outcome implementation"],
            cwd=self.root, check=True,
        )
        self.implementation_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, check=True,
            text=True, capture_output=True,
        ).stdout.strip()
        authorization = {
            "schema_version": "yax-gate1-pre-execution-authorization-v1",
            "status": "AUTHORIZED_FRESH_GATE1_EXECUTION",
            "issued_at_utc": "2026-09-07T00:00:00Z",
            "not_before_utc": "2026-09-07T00:00:00Z",
            "not_after_utc": "2026-09-08T00:00:00Z",
            "authorized_implementation_commit": self.implementation_commit,
            "canonical_spec": {"id": self.CANONICAL, "sha256": H},
            "source_registry_sha256": H,
            "modules": {
                "numerical": {
                    "typed_spec_id": self.AUDIT_SPEC,
                    "typed_spec_sha256": H,
                    "code_sha256": H,
                },
            },
        }
        authorization["authorization_id"] = (
            "yaxgate1auth_v1_" + hashlib.sha256(
                guard.canonical_bytes(authorization)
            ).hexdigest()
        )
        auth_path = self.root / guard.PRE_EXECUTION_AUTHORIZATION_REL
        auth_path.parent.mkdir(parents=True)
        self.write_json(
            guard.PRE_EXECUTION_AUTHORIZATION_REL.as_posix(), authorization
        )
        subprocess.run(
            ["git", "add", guard.PRE_EXECUTION_AUTHORIZATION_REL.as_posix()],
            cwd=self.root, check=True,
        )
        subprocess.run(
            ["git", "commit", "-qm", "authorize execution"],
            cwd=self.root, check=True,
        )
        self.authorization_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=self.root, check=True,
            text=True, capture_output=True,
        ).stdout.strip()
        self.authorization = authorization
        self.authorization_file_sha256 = self.digest(
            guard.PRE_EXECUTION_AUTHORIZATION_REL.as_posix()
        )
        self.models = [self.certified_model(model_id) for model_id in self.MODEL_IDS]
        self.audit = {}
        self.receipt = {}
        self.write_numerical_artifacts()

    def tearDown(self):
        self.tmp.cleanup()

    def write_json(self, relative, value):
        (self.root / relative).write_text(
            json.dumps(value, indent=2) + "\n", encoding="utf-8"
        )

    def digest(self, relative):
        return hashlib.sha256((self.root / relative).read_bytes()).hexdigest()

    def certified_model(self, model_id):
        labels = ["Q2_x_post", "Q5_x_post"]
        cross_evaluation = {
            "status": "PASS_INDEPENDENT_EVALUATOR_AND_DERIVATIVE_CHECKS",
            "checks": {
                "objective_equivalence": True,
                "probability_equivalence": True,
                "score_equivalence": True,
                "hessian_product_equivalence": True,
                "directional_derivative": True,
                "finite_difference_hessian_product": True,
            },
            "finite_difference_step": 1e-6,
            "objective_per_total_absolute_difference": 0.0,
            "fitted_probability_max_absolute_difference": 0.0,
            "score_per_total_max_absolute_difference": 0.0,
            "hessian_product_per_total_max_absolute_difference": 0.0,
            "directional_derivative_absolute_difference": 0.0,
            "finite_difference_hessian_product_max_absolute_difference": 0.0,
            "objective_tolerance": 1e-10,
            "probability_tolerance": 1e-7,
            "gradient_or_derivative_tolerance": 1e-7,
            "direction_definition": "deterministic synthetic direction",
        }
        original_rows = [
            {
                "original_index": index,
                "original_label": label,
                "weights": [1.0 if column == index else 0.0 for column in range(len(labels))],
            }
            for index, label in enumerate(labels)
        ]
        original_target_labels = [
            f"original_treatment::{index}::{label}"
            for index, label in enumerate(labels)
        ]
        transformed_target_labels = [
            f"treatment_basis::{index}::{label}"
            for index, label in enumerate(labels)
        ]
        frozen_dynamic_targets, frozen_dynamic_pretrend = (
            guard._frozen_dynamic_q5_targets()
        )
        reported_target_labels = (
            frozen_dynamic_targets if model_id.startswith("dynamics_") else []
        )
        all_target_labels = [
            "focal_target", *original_target_labels,
            *transformed_target_labels, *reported_target_labels,
        ]
        target_differences = {label: 0.0 for label in all_target_labels}
        model = {
            "model_id": model_id,
            "classification": guard.A1_MODEL_PASS_CLASSIFICATION,
            "finite_target_established": True,
            "target_estimability_status": guard.A1_TARGET_PASS_STATUS,
            "target_parameterization": {
                "original_regressor_labels": labels,
                "original_coefficient_functionals_in_current_basis": original_rows,
            },
            "treatment_basis": {
                "selected_original_labels": labels,
                "original_columns": len(labels),
            },
            "a1_certification": {
                "status": guard.A1_CERTIFICATE_STATUS,
                "primary_path": guard.A1_PRIMARY_PATH,
                "reference_path": guard.A1_REFERENCE_METHOD,
                "identified_treatment_vector_length": len(labels),
                **{key: True for key in guard.A1_CERTIFICATE_CHECKS},
            },
            "solver_comparison": {
                "status": guard.A1_COMPARISON_PASS_STATUS,
                "comparison_pass": True,
                "left_valid": True,
                "right_valid": True,
                "left_solver": "trust-path-unpolished-trust-ncg",
                "right_solver": guard.A1_REFERENCE_METHOD,
                "checks": {
                    key: True for key in guard.A1_COMPARISON_CHECKS
                },
                "trust_path_target_vector": {
                    label: 0.0 for label in all_target_labels
                },
                "reference_target_vector": {
                    label: 0.0 for label in all_target_labels
                },
                "target_absolute_differences": target_differences,
                "identified_treatment_target_labels": original_target_labels,
                "identified_treatment_target_count": len(original_target_labels),
                "identified_treatment_absolute_differences": {
                    label: 0.0 for label in original_target_labels
                },
                "transformed_basis_absolute_differences_nonbinding_diagnostic": {
                    label: 0.0 for label in transformed_target_labels
                },
                "reported_target_absolute_differences": {
                    label: 0.0 for label in all_target_labels
                },
                "maximum_absolute_full_identified_treatment_vector_difference": 0.0,
                "reported_target_max_absolute_difference": 0.0,
                "focal_target_absolute_difference": 0.0,
                "fitted_probability_max_abs_difference": 0.0,
                "objective_difference_per_total": 0.0,
                "same_final_tolerances": {
                    "target_coefficient_absolute_difference": 1e-6,
                    "fitted_probability_max_abs_difference": 1e-7,
                    "objective_difference_per_total": 1e-10,
                },
                "trust_candidate_cross_evaluation": copy.deepcopy(
                    cross_evaluation
                ),
                "reference_candidate_cross_evaluation": copy.deepcopy(
                    cross_evaluation
                ),
            },
            "target_profile": {"status": guard.A1_PROFILE_PASS_STATUS},
            "fitted_full_hessian": {
                "status": "PASS_FULL_HESSIAN_SPECTRUM",
                "rank_deficiency": 0,
            },
            "fitted_information": {
                "focal_target_rank_identified": True,
                "treatment_information_rank": 2,
                "treatment_information_columns": 2,
            },
            "fitted_reported_target_information": {
                "status": "NOT_APPLICABLE",
            },
            "dual_candidate_fitted_hessian_audit": {
                "status": "PASS_BOTH_CANDIDATE_RAW_AND_SCALED_FITTED_HESSIANS",
                "expected_full_rank": 12,
                "checks": {
                    "trust_path": True,
                    "independent_zero_start_reference": True,
                },
                "candidates": {
                    label: {
                        "columns": 12,
                        "rank_from_nuisance_plus_schur": 12,
                        "rank_deficiency": 0,
                        "status": "PASS_FULL_HESSIAN_SPECTRUM",
                        "positive_definite_at_declared_tolerance": True,
                        "spectrum_method": "dense_eigh_with_explicit_residual_bounds",
                        "smallest_positive_or_extreme_eigenvalue": 0.2,
                        "largest_eigenvalue": 3.0,
                        "smallest_eigenpair_residual_norm_2": 1e-14,
                        "largest_eigenpair_residual_norm_2": 1e-14,
                        "smallest_certified_lower_bound": 0.19999999999999,
                        "largest_conservative_upper_bound": 3.1,
                        "condition_number": 15.0,
                        "rank_threshold": 1e-10,
                        "diagonally_scaled_smallest_positive_or_extreme_eigenvalue": 0.3,
                        "diagonally_scaled_largest_eigenvalue": 2.0,
                        "diagonally_scaled_smallest_eigenpair_residual_norm_2": 1e-14,
                        "diagonally_scaled_largest_eigenpair_residual_norm_2": 1e-14,
                        "diagonally_scaled_smallest_certified_lower_bound": 0.29999999999999,
                        "diagonally_scaled_largest_conservative_upper_bound": 2.1,
                        "diagonally_scaled_condition_number": 6.666666666666667,
                        "diagonally_scaled_spectrum_method": "dense_eigh_with_explicit_residual_bounds",
                        "diagonally_scaled_rank_threshold": 1e-10,
                    }
                    for label in (
                        "trust_path", "independent_zero_start_reference"
                    )
                },
            },
            "lbfgsb_diagnostic_contradiction_audit": {
                "status": "PASS_NO_LBFGSB_DIAGNOSTIC_CONTRADICTION",
                "available": True,
                "binding_pass": True,
                "contradiction_detected": False,
                "diagnostic_candidate_numerically_valid": False,
                "diagnostic_candidate_independently_stationary": False,
                "recomputed_objective_per_total": 0.52,
                "best_binding_objective_per_total": 0.51,
                "signed_objective_gap_diagnostic_minus_best_binding": 0.01,
                "target_absolute_differences_vs_reference": {
                    label: (0.02 if label == "focal_target" else 0.0)
                    for label in all_target_labels
                },
                "maximum_declared_target_absolute_difference_vs_reference": 0.02,
                "canonical_recomputed_score": {"gradient_infinity_norm_per_total": 0.1},
                "independent_cross_evaluation": {
                    "status": "PASS_INDEPENDENT_EVALUATOR_AND_DERIVATIVE_CHECKS",
                },
                "checks": {
                    "no_materially_lower_diagnostic_objective": True,
                    "no_derivative_implementation_contradiction": True,
                    "no_stationary_declared_target_contradiction": True,
                },
                "interpretation": "nonstationary diagnostic is contradiction-free",
            },
        }
        if model_id.startswith("dynamics_"):
            model["fitted_reported_target_information"]["status"] = (
                "PASS_ALL_REPORTED_TARGETS_AND_JOINT_PRETREND_INFORMATION_RANK"
            )
            model["dynamic_event_target_scope"] = {
                "status": "PASS_COMPLETE_DYNAMIC_TARGET_SCOPE_CONSTRUCTION",
                "declared_primary_target": (
                    "observed_calendar_month_weighted_post_Q5_functional"
                ),
                "reference_quarter": "2022Q4",
                "overall_status": (
                    "PASS_ALL_REPORTED_Q5_EVENT_TARGETS_AND_POST_FUNCTIONAL_FULL_AUDIT"
                ),
                "reported_q5_event_targets": reported_target_labels,
                "reported_q5_event_target_count": 38,
                "joint_pretrend_targets": frozen_dynamic_pretrend,
                "joint_pretrend_target_count": 23,
                "observed_post_month_count": 42,
                "post_functional_weight_sum": 1.0,
                "post_functional_weight_max_absolute_error": 0.0,
                "checks": {
                    "reported_target_labels_exact": True,
                    "reported_target_count": True,
                    "joint_pretrend_labels_exact": True,
                    "joint_pretrend_count": True,
                    "observed_post_month_count": True,
                    "post_functional_weights_exact": True,
                    "post_functional_weights_sum_to_one": True,
                },
                "recession_direction_status": (
                    "PASS_ALL_REPORTED_Q5_TARGETS_RECESSION_INVARIANT_ON_FINAL_FACE"
                ),
                "geometric_information_status": (
                    "PASS_ALL_REPORTED_TARGETS_AND_JOINT_PRETREND_INFORMATION_RANK"
                ),
                "fitted_information_status": (
                    "PASS_ALL_REPORTED_TARGETS_AND_JOINT_PRETREND_INFORMATION_RANK"
                ),
                "reported_target_solver_comparison_status": "PASS",
            }
        return model

    def write_numerical_artifacts(self):
        certified_count = sum(
            guard._a1_model_is_certified(model) for model in self.models
        )
        status = (
            "PASS_ALL_CORE_TARGETS_NUMERICALLY_AUDITED"
            if certified_count == len(self.MODEL_IDS)
            else "BLOCKED_ONE_OR_MORE_CORE_TARGETS_NOT_ESTABLISHED"
        )
        self.audit = {
            "schema_version": guard.NUMERICAL_AUDIT_SCHEMA,
            "status": status,
            "canonical_spec_id": self.CANONICAL,
            "audit_spec_id": self.AUDIT_SPEC,
            "cells_sha256": self.CELLS_SHA,
            "models": self.models,
        }
        self.write_json("MODEL_AUDIT.json", self.audit)
        self.receipt = {
            "schema_version": guard.NUMERICAL_RECEIPT_SCHEMA,
            "status": status,
            "canonical_spec_id": self.CANONICAL,
            "audit_spec_id": self.AUDIT_SPEC,
            "cells_sha256": self.CELLS_SHA,
            "cells_receipt_sha256": self.target_map[
                "non_model_prerequisites"
            ]["authenticated_cells"]["receipt_sha256"],
            "audit_spec_sha256": H,
            "code_sha256": H,
            "canonical_spec_sha256": H,
            "model_count": len(self.MODEL_IDS),
            "passed_model_count": certified_count,
            "output_hashes": {
                "MODEL_AUDIT.json": self.digest("MODEL_AUDIT.json"),
            },
            "pre_execution_authorization": {
                "schema_version": self.authorization["schema_version"],
                "status": self.authorization["status"],
                "authorization_id": self.authorization["authorization_id"],
                "authorization_file_sha256": self.authorization_file_sha256,
                "authorization_git_commit": self.authorization_commit,
                "authorized_implementation_commit": self.implementation_commit,
                "issued_at_utc": self.authorization["issued_at_utc"],
                "not_before_utc": self.authorization["not_before_utc"],
                "not_after_utc": self.authorization["not_after_utc"],
                "module_key": "numerical",
                "typed_spec_id": self.AUDIT_SPEC,
                "typed_spec_sha256": H,
                "code_sha256": H,
                "source_registry_sha256": H,
            },
        }

    def evaluate(self, ledger=None):
        return guard.validate_target_certifications(
            self.target_map, self.audit, self.receipt, self.root,
            "MODEL_AUDIT.json", ledger,
        )

    def test_all_models_release_exact_consumers(self):
        result = self.evaluate()
        self.assertEqual(result["status"], "PASS_ALL_11_MODELS_CERTIFIED")
        self.assertEqual(result["certified_model_count"], 11)
        self.assertTrue(all(
            row["release_status"] == "RELEASED"
            for row in result["consumers"].values()
        ))
        self.assertEqual(
            result["downstream_requirement_releases"]["Y01"][
                "release_status"
            ],
            "RELEASED",
        )

    def test_consumer_cannot_claim_requirement_without_full_model_contract(self):
        weakened = copy.deepcopy(self.target_map)
        consumer = next(
            row for row in weakened["consumers"]
            if row["consumer_id"] == "compare.pooled.family_month"
        )
        consumer["required_model_ids"] = ["pooled"]
        with self.assertRaisesRegex(
            guard.DependencyError, "full declared model prerequisite set",
        ):
            guard.validate_target_dependency_map(weakened, self.root)

    def test_requirement_release_blocks_when_any_contract_model_is_blocked(self):
        row = next(
            model for model in self.models
            if model["model_id"] == "family_month"
        )
        row["a1_certification"]["status"] = (
            "BLOCKED_A1_NUMERICAL_CERTIFICATE"
        )
        self.write_numerical_artifacts()
        result = self.evaluate()
        self.assertEqual(
            result["consumers"]["use.pooled"]["release_status"],
            "RELEASED",
        )
        requirement = result["downstream_requirement_releases"]["Y01"]
        self.assertEqual(requirement["release_status"], "BLOCKED")
        self.assertEqual(requirement["blocking_model_ids"], ["family_month"])
        self.assertEqual(
            requirement["consumer_ids"], ["compare.pooled.family_month"],
        )

    def test_unresolved_seasonal_blocks_only_its_consumers(self):
        seasonal = "seasonal_quintile_month_unconditioned"
        row = next(model for model in self.models if model["model_id"] == seasonal)
        row["a1_certification"]["status"] = "BLOCKED_A1_NUMERICAL_CERTIFICATE"
        self.write_numerical_artifacts()
        result = self.evaluate()
        self.assertEqual(
            result["status"], "BLOCKED_INCOMPLETE_11_MODEL_SUITE"
        )
        self.assertEqual(result["certified_model_count"], 10)
        self.assertEqual(
            result["consumers"]["use.pooled"]["release_status"],
            "RELEASED",
        )
        self.assertEqual(
            result["consumers"][f"use.{seasonal}"]["release_status"],
            "BLOCKED",
        )
        self.assertEqual(
            result["consumers"]["compare.pooled.family_month"][
                "release_status"
            ],
            "RELEASED",
        )

    def test_paired_consumer_requires_both_exact_models(self):
        row = next(
            model for model in self.models if model["model_id"] == "family_month"
        )
        row["solver_comparison"]["comparison_pass"] = False
        self.write_numerical_artifacts()
        result = self.evaluate()
        self.assertEqual(
            result["consumers"]["use.pooled"]["release_status"],
            "RELEASED",
        )
        paired = result["consumers"]["compare.pooled.family_month"]
        self.assertEqual(paired["release_status"], "BLOCKED")
        self.assertEqual(paired["blocking_model_ids"], ["family_month"])

    def test_historical_audit_spec_cannot_release(self):
        self.audit["audit_spec_id"] = self.OLD_AUDIT_SPEC
        self.receipt["audit_spec_id"] = self.OLD_AUDIT_SPEC
        self.write_json("MODEL_AUDIT.json", self.audit)
        self.receipt["output_hashes"]["MODEL_AUDIT.json"] = self.digest(
            "MODEL_AUDIT.json"
        )
        with self.assertRaises(guard.DependencyError):
            self.evaluate()

    def test_receipt_must_bind_model_audit(self):
        self.receipt["output_hashes"]["MODEL_AUDIT.json"] = "f" * 64
        with self.assertRaises(guard.DependencyError):
            self.evaluate()

    def test_non_model_prerequisite_hash_is_binding(self):
        (self.root / "target_audit.json").write_text(
            "{}\n", encoding="utf-8"
        )
        with self.assertRaises(guard.DependencyError):
            self.evaluate()

    def test_missing_full_target_vector_fails_model_only(self):
        row = next(model for model in self.models if model["model_id"] == "pooled")
        del row["solver_comparison"]["target_absolute_differences"][
            "treatment_basis::1::Q5_x_post"
        ]
        self.write_numerical_artifacts()
        result = self.evaluate()
        self.assertNotIn("pooled", result["certified_model_ids"])
        self.assertEqual(
            result["consumers"]["use.family_month"]["release_status"],
            "RELEASED",
        )

    def test_missing_original_treatment_entry_fails_model_only(self):
        row = next(model for model in self.models if model["model_id"] == "pooled")
        label = row["solver_comparison"]["identified_treatment_target_labels"][0]
        del row["solver_comparison"]["target_absolute_differences"][label]
        self.write_numerical_artifacts()
        result = self.evaluate()
        self.assertNotIn("pooled", result["certified_model_ids"])
        self.assertEqual(
            result["consumers"]["use.family_month"]["release_status"],
            "RELEASED",
        )

    def test_false_raw_scaled_hessian_check_blocks_model_only(self):
        row = next(model for model in self.models if model["model_id"] == "pooled")
        row["a1_certification"][
            "both_candidates_raw_scaled_fitted_hessian_pass"
        ] = False
        self.write_numerical_artifacts()
        result = self.evaluate()
        self.assertNotIn("pooled", result["certified_model_ids"])
        self.assertEqual(
            result["consumers"]["use.family_month"]["release_status"],
            "RELEASED",
        )

    def test_missing_lbfgsb_contradiction_check_blocks_model_only(self):
        row = next(model for model in self.models if model["model_id"] == "pooled")
        del row["a1_certification"][
            "lbfgsb_diagnostic_contradiction_free"
        ]
        self.write_numerical_artifacts()
        result = self.evaluate()
        self.assertNotIn("pooled", result["certified_model_ids"])
        self.assertEqual(
            result["consumers"]["use.family_month"]["release_status"],
            "RELEASED",
        )

    def test_true_hessian_summary_cannot_hide_blocked_nested_candidate(self):
        row = next(model for model in self.models if model["model_id"] == "pooled")
        self.assertTrue(row["a1_certification"][
            "both_candidates_raw_scaled_fitted_hessian_pass"
        ])
        candidate = row["dual_candidate_fitted_hessian_audit"]["candidates"][
            "trust_path"
        ]
        candidate["status"] = "BLOCKED_FULL_HESSIAN_SPECTRUM_FAILURE"
        self.write_numerical_artifacts()
        result = self.evaluate()
        self.assertNotIn("pooled", result["certified_model_ids"])
        self.assertEqual(
            result["consumers"]["use.family_month"]["release_status"],
            "RELEASED",
        )

    def test_true_hessian_summary_cannot_hide_missing_nested_evidence(self):
        row = next(model for model in self.models if model["model_id"] == "pooled")
        del row["dual_candidate_fitted_hessian_audit"]["candidates"][
            "independent_zero_start_reference"
        ]
        self.write_numerical_artifacts()
        result = self.evaluate()
        self.assertNotIn("pooled", result["certified_model_ids"])

    def test_optimistic_hessian_estimate_cannot_hide_failed_certified_lower_bound(self):
        row = next(model for model in self.models if model["model_id"] == "pooled")
        candidate = row["dual_candidate_fitted_hessian_audit"]["candidates"][
            "trust_path"
        ]
        self.assertGreater(
            candidate["smallest_positive_or_extreme_eigenvalue"],
            candidate["rank_threshold"],
        )
        candidate["smallest_certified_lower_bound"] = candidate["rank_threshold"]
        self.write_numerical_artifacts()
        result = self.evaluate()
        self.assertNotIn("pooled", result["certified_model_ids"])

    def test_true_lbfgsb_summary_cannot_hide_nested_contradiction(self):
        row = next(model for model in self.models if model["model_id"] == "pooled")
        self.assertTrue(row["a1_certification"][
            "lbfgsb_diagnostic_contradiction_free"
        ])
        nested = row["lbfgsb_diagnostic_contradiction_audit"]
        nested.update({
            "status": "BLOCKED_LBFGSB_DIAGNOSTIC_CONTRADICTION",
            "binding_pass": False,
            "contradiction_detected": True,
        })
        self.write_numerical_artifacts()
        result = self.evaluate()
        self.assertNotIn("pooled", result["certified_model_ids"])
        self.assertEqual(
            result["consumers"]["use.family_month"]["release_status"],
            "RELEASED",
        )

    def test_true_lbfgsb_summary_cannot_hide_missing_nested_evidence(self):
        row = next(model for model in self.models if model["model_id"] == "pooled")
        del row["lbfgsb_diagnostic_contradiction_audit"]
        self.write_numerical_artifacts()
        result = self.evaluate()
        self.assertNotIn("pooled", result["certified_model_ids"])

    def test_unavailable_lbfgsb_diagnostic_cannot_release_model(self):
        row = next(model for model in self.models if model["model_id"] == "pooled")
        row["lbfgsb_diagnostic_contradiction_audit"] = {
            "status": "PASS_NONESSENTIAL_LBFGSB_DIAGNOSTIC_UNAVAILABLE",
            "available": False,
            "binding_pass": True,
            "contradiction_detected": False,
            "unavailable_failure": {
                "error_type": "Synthetic", "message": "unavailable",
            },
            "interpretation": "not executed",
        }
        self.write_numerical_artifacts()
        result = self.evaluate()
        self.assertNotIn("pooled", result["certified_model_ids"])

    def test_lbfgsb_diagnostic_must_cover_exact_full_target_family(self):
        row = next(model for model in self.models if model["model_id"] == "pooled")
        differences = row["lbfgsb_diagnostic_contradiction_audit"][
            "target_absolute_differences_vs_reference"
        ]
        del differences[next(label for label in differences if label.startswith(
            "original_treatment::"
        ))]
        self.write_numerical_artifacts()
        result = self.evaluate()
        self.assertNotIn("pooled", result["certified_model_ids"])

    def test_receipt_runner_hash_must_match_target_map_exactly(self):
        self.receipt["code_sha256"] = "f" * 64
        with self.assertRaisesRegex(
            guard.DependencyError, "exact authorized A1 specification and runner"
        ):
            self.evaluate()

    def test_post_run_weakened_target_map_cannot_release(self):
        weakened = copy.deepcopy(self.target_map)
        consumer = next(
            row for row in weakened["consumers"]
            if row["consumer_id"] == "compare.pooled.family_month"
        )
        consumer["required_model_ids"] = ["pooled"]
        weakened["downstream_requirement_model_contract"]["Y01"] = [
            "pooled"
        ]
        self.target_map = weakened
        self.write_json(
            guard.TARGET_DEPENDENCY_MAP_REL.as_posix(), self.target_map
        )
        with self.assertRaisesRegex(
            guard.DependencyError, "pre-outcome authorization commit"
        ):
            self.evaluate()

    def test_stale_ledger_is_reported_but_not_pass_evidence(self):
        ledger = {
            "requirements": [
                {"id": "T01", "status": "RUN_UNVALIDATED"},
                {"id": "T02", "status": "VERIFIED"},
                {"id": "T03", "status": "VERIFIED"},
            ],
        }
        result = self.evaluate(ledger)
        snapshot = result["working_ledger_snapshot"]
        self.assertEqual(
            snapshot["stale_or_unresolved_requirement_ids"], ["T01"]
        )
        self.assertEqual(
            result["non_model_prerequisites"]["status"],
            "PASS_BOUND_NON_MODEL_PREREQUISITES",
        )


if __name__ == "__main__":
    unittest.main()
