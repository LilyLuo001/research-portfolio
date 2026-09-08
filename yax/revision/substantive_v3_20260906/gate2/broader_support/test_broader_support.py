import importlib.util
import json
import pathlib
import sys

import numpy as np
import pandas as pd


HERE = pathlib.Path(__file__).resolve().parent
MODULE_PATH = HERE / "run_broader_support.py"
MODULE_SPEC = importlib.util.spec_from_file_location("yax_test_broader_support", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
MODULE = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = MODULE
MODULE_SPEC.loader.exec_module(MODULE)

VALIDATOR_PATH = HERE / "validate_broader_support.py"
VALIDATOR_SPEC = importlib.util.spec_from_file_location("yax_test_broader_support_validator", VALIDATOR_PATH)
assert VALIDATOR_SPEC and VALIDATOR_SPEC.loader
VALIDATOR = importlib.util.module_from_spec(VALIDATOR_SPEC)
sys.modules[VALIDATOR_SPEC.name] = VALIDATOR
VALIDATOR_SPEC.loader.exec_module(VALIDATOR)


def test_spec_identity_and_four_model_order():
    spec = json.loads((HERE / "BROADER_SUPPORT_SPEC.json").read_text())
    assert spec["spec_id"] == MODULE.spec_identity(spec)
    assert [row["model_id"] for row in spec["scientific_contract"]["models_in_fixed_order"]] == [
        "primary_with_webb",
        "primary_without_webb",
        "broader_fixed_primary_cuts_without_webb",
        "broader_recomputed_cuts_without_webb",
    ]


def test_fixed_cut_tie_rule_is_left_closed():
    cuts = np.array([1.0, 2.0, 3.0, 4.0])
    values = np.array([0.0, 1.0, 1.0001, 2.0, 3.0, 4.0, 5.0])
    assert MODULE.groups_from_fixed_cuts(values, cuts).tolist() == [1, 1, 2, 2, 3, 4, 5]


def test_direct_tail_requires_both_tails_within_family():
    schemes = {
        "x": {
            "support": ["a", "b", "c", "d"],
            "groups": np.array([1, 5, 1, 3]),
            "weights": np.array([1.0, 2.0, 3.0, 4.0]),
        }
    }
    rows, summary = MODULE.direct_tail_outputs(
        schemes,
        {"a": "A", "b": "B", "c": "C", "d": "D"},
        {"a": "11", "b": "11", "c": "22", "d": "22"},
    )
    by_family = {row["family"]: row for row in rows}
    assert by_family["11"]["direct_q5_q1_supported"] is True
    assert by_family["22"]["direct_q5_q1_supported"] is False
    assert summary[0]["direct_tail_spanning_families"] == 1


def test_paired_difference_uses_covariance_from_common_draws():
    left = {"coefficient": 0.1}
    right = {"coefficient": 0.0}
    common = np.arange(20.0)
    result = MODULE.paired("left", "right", left, right, common + np.linspace(0.1, 0.3, 20), common)
    assert np.isclose(result["coefficient_difference"], 0.1)
    assert result["paired_bootstrap_se"] < 0.1
    assert result["common_multiplier_draws"] is True


def test_support_hash_is_order_invariant_but_membership_sensitive():
    assert MODULE.support_hash(["b", "a"]) == MODULE.support_hash(["a", "b"])
    assert MODULE.support_hash(["a", "b"]) != MODULE.support_hash(["a", "c"])


def test_common_multiplier_subsupport_selects_occupation_columns():
    signs = np.arange(5 * 7, dtype=float).reshape(5, 7)
    selected = MODULE.select_sign_columns(signs, [1, 4, 6])
    assert selected.shape == (5, 3)
    assert np.array_equal(selected, signs[:, [1, 4, 6]])


def test_validator_boolean_parser_does_not_treat_false_string_as_true():
    values = pd.Series(["True", "False", " false ", "TRUE"])
    assert VALIDATOR.boolean_series(values).tolist() == [True, False, False, True]


def test_a1_face_functionals_use_required_original_treatment_namespace():
    values = MODULE.original_treatment_functionals(["Q2_x_post", "Q5_x_post"])
    assert list(values) == [
        "original_treatment::0::Q2_x_post",
        "original_treatment::1::Q5_x_post",
    ]
    assert np.array_equal(values["original_treatment::1::Q5_x_post"], [0.0, 1.0])


def test_complete_numerical_interface_on_synthetic_same_objective_problem():
    repo = HERE.parents[4]
    arch = MODULE.load_module(
        "yax_test_s05_architecture",
        repo / "yax/revision/substantive_r3_20260905/architecture/run_architecture.py",
    )
    frozen = MODULE.load_module(
        "yax_test_s05_frozen",
        repo / "yax/analysis/run_frozen_v11.py",
    )
    numerical = MODULE.load_module(
        "yax_test_s05_numerical",
        repo / "yax/revision/substantive_v3_20260906/numerical_existence/run_numerical_existence_audit.py",
    )
    analysis = json.loads(
        (repo / "yax/revision/substantive_v3_20260906/numerical_existence/ANALYSIS_SPEC_A1.json").read_text()
    )
    months = [f"2022-{month:02d}" for month in range(1, 7)] + [
        f"2023-{month:02d}" for month in range(1, 7)
    ]
    support = [f"{index:04d}" for index in range(1, 16)]
    groups = np.repeat(np.arange(1, 6), 3)
    columns, labels = arch.categorical_design(groups, months, {})
    regressors = np.column_stack([column.reshape(-1) for column in columns])
    occ_effect = np.repeat(np.linspace(-0.7, 0.7, len(support)), len(months))
    month_effect = np.tile(np.linspace(-0.2, 0.2, len(months)), len(support))
    probability = 1.0 / (1.0 + np.exp(-(occ_effect + month_effect + regressors @ [0.02, -0.01, 0.03, -0.08])))
    total = np.full(len(probability), 10_000.0)
    young = (total * probability).reshape(len(support), len(months))
    older = total.reshape(len(support), len(months)) - young
    fit, _ = arch.fit_design(frozen, young, older, columns)
    bundle = MODULE.build_bundle(
        numerical, "synthetic_s05", support, months, young, older, regressors, labels
    )
    audit = MODULE.certify_model(numerical, bundle, analysis, frozen.ENGINE, fit)
    assert audit["status"] == "PASS_SAME_OBJECTIVE_NUMERICAL_CERTIFICATION"
    assert audit["scientific_engine_reference_maximum_absolute_difference"] <= 1e-6
