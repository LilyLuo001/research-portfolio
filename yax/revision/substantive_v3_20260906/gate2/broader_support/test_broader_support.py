import importlib.util
import json
import pathlib
import sys

import numpy as np


HERE = pathlib.Path(__file__).resolve().parent
MODULE_PATH = HERE / "run_broader_support.py"
MODULE_SPEC = importlib.util.spec_from_file_location("yax_test_broader_support", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
MODULE = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = MODULE
MODULE_SPEC.loader.exec_module(MODULE)


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
