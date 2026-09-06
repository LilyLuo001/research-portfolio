"""Regression tests for immutable YAX V3 specification identifiers."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import spec_contract as contract


H = "a" * 64


def fixture() -> dict:
    return {
        "schema_version": contract.SCHEMA_VERSION,
        "analysis": {"name": "fixture", "status": "test"},
        "data": {
            "sources": [{"source_id": "cells", "vintage": "test", "sha256": H,
                         "access_class": "synthetic"}],
            "microdata_eligibility": {"ages": [22, 65]},
            "variable_universe": ["AGE", "EMPSTAT"],
        },
        "occupation": {
            "taxonomy": "Census 2018",
            "family_assignment": {"rule": "SOC2"},
            "crosswalk": {"version": "test", "sha256": H, "allocation_rule": "fixed"},
            "universe": {"rule": "fixed", "membership_sha256": H},
            "analysis_subset": {"rule": "same as universe"},
            "subgroup_eligibility": {"rule": "none"},
        },
        "outcome": {"units": "weighted stock", "cell_construction": "sum weights",
                    "age_groups": {"young": [22, 25], "older": [26, 65]}},
        "calendar": {"observed_window": ["2017-01", "2026-07"],
                     "estimation_window": ["2017-01", "2026-07"],
                     "transition_handling": "drop 2022-12",
                     "missing_handling": "no interpolation"},
        "exposure": {
            "version": "beta", "raw_scale": "0-1", "construction_weights": "preperiod stock",
            "construction_age_universe": [22, 65], "training_dates": "published vintage",
            "cutoffs": [0.1, 0.2, 0.3, 0.4], "tie_rule": "left",
            "fixed_membership": {"sha256": H},
            "webb_normalization": {"mean": 0.0, "sd": 1.0, "window": "preperiod"},
        },
        "estimator": {
            "objective": "grouped binomial log likelihood",
            "nuisance_column_space": ["occupation FE", "month FE"],
            "identifying_normalizations": "sum-to-zero",
            "separation_treatment": "none",
            "boundary_handling": "declared probability clipping",
            "solver": {"name": "fixture", "tolerance": 1e-8},
        },
        "target": {"contrast": "Q5-post relative Q1", "temporal_weights": "likelihood implied"},
        "uncertainty": {"source": "cluster sandwich", "resampling_unit": "occupation",
                        "multiplier_matrix": {"draws": 99, "seed": 1},
                        "generated_objects": {"membership": "held fixed"}},
        "dependencies": [{"role": "cells", "artifact_sha256": H}],
        "execution": {"command": "fixture", "code_sha256": H, "environment_sha256": H},
        "outputs": {"locations": ["results/fixture.json"]},
    }


class SpecContractTests(unittest.TestCase):
    def test_stamp_and_validate(self):
        spec = contract.stamp_spec(fixture())
        self.assertEqual(contract.validate_spec(spec)["spec_id"], spec["spec_id"])

    def test_key_order_does_not_change_id(self):
        spec = fixture()
        reordered = {key: spec[key] for key in reversed(list(spec))}
        self.assertEqual(contract.compute_spec_id(spec), contract.compute_spec_id(reordered))

    def test_endpoint_change_changes_id(self):
        left = fixture()
        right = copy.deepcopy(left)
        right["calendar"]["estimation_window"][1] = "2024-12"
        self.assertNotEqual(contract.compute_spec_id(left), contract.compute_spec_id(right))

    def test_age_objective_and_membership_changes_change_id(self):
        base = fixture()
        for path, value in [
            (("outcome", "age_groups", "young"), [18, 25]),
            (("estimator", "objective"), "poisson pseudo likelihood"),
            (("exposure", "fixed_membership", "sha256"), "b" * 64),
        ]:
            changed = copy.deepcopy(base)
            cursor = changed
            for part in path[:-1]:
                cursor = cursor[part]
            cursor[path[-1]] = value
            self.assertNotEqual(contract.compute_spec_id(base), contract.compute_spec_id(changed))

    def test_tampered_stamped_spec_fails(self):
        spec = contract.stamp_spec(fixture())
        spec["calendar"]["transition_handling"] = "retain all"
        with self.assertRaises(contract.ContractError):
            contract.validate_spec(spec)

    def test_missing_field_fails(self):
        spec = fixture()
        del spec["target"]["temporal_weights"]
        with self.assertRaises(contract.ContractError):
            contract.stamp_spec(spec)

    def test_null_and_nonfinite_fail(self):
        spec = fixture()
        spec["target"]["temporal_weights"] = None
        with self.assertRaises(contract.ContractError):
            contract.stamp_spec(spec)
        spec = fixture()
        spec["exposure"]["cutoffs"][0] = float("nan")
        with self.assertRaises(contract.ContractError):
            contract.stamp_spec(spec)

    def test_duplicate_json_key_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"schema_version":"one","schema_version":"two"}', encoding="utf-8")
            with self.assertRaises(contract.ContractError):
                contract.load_json(path)

    def test_incompatible_module_inputs_fail(self):
        left = contract.stamp_spec(fixture())
        changed = fixture()
        changed["exposure"]["cutoffs"] = [0.11, 0.2, 0.3, 0.4]
        right = contract.stamp_spec(changed)
        with self.assertRaises(contract.ContractError):
            contract.assert_compatible(left, right, ["exposure.cutoffs"])

    def test_result_id_binds_artifact_selector_and_spec(self):
        spec = contract.stamp_spec(fixture())
        first = contract.compute_result_id(spec["spec_id"], "beta", H, "/coefficient")
        second = contract.compute_result_id(spec["spec_id"], "beta", H, "/se")
        self.assertNotEqual(first, second)

    def test_refuse_contract_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "spec.json"
            path.write_text("existing", encoding="utf-8")
            with self.assertRaises(contract.ContractError):
                contract.write_new_json(path, contract.stamp_spec(fixture()))


if __name__ == "__main__":
    unittest.main()
