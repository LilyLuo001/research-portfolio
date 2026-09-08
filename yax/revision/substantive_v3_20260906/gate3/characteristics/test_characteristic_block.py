from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUN = load_module("test_gate3_characteristic_runner", HERE / "run_characteristic_block.py")


def test_public_characteristic_support_counts_match_specification():
    root = HERE.parents[4]
    membership = pd.read_csv(
        root / "yax/revision/substantive_v3_20260906/runs/gate1_baseline/results/REBUILT_TREATMENT_MEMBERSHIP.csv",
        dtype={"occupation_code": str},
    )
    characteristics = pd.read_csv(
        root / "yax/measurement/test_a/TEST_A_OCCUPATION_CHARACTERISTICS.csv",
        dtype={"census2018": str},
    )
    membership["occupation_code"] = membership.occupation_code.str.zfill(4)
    characteristics["census2018"] = characteristics.census2018.str.zfill(4)
    frame = membership.merge(characteristics, left_on="occupation_code",
                             right_on="census2018", how="left", validate="one_to_one")
    columns = list(RUN.CHARACTERISTICS.values())
    assert frame.onet_computers_importance.notna().sum() == 455
    assert frame.dingel_neiman_telework.notna().sum() == 408
    assert frame[columns].notna().all(axis=1).sum() == 347


def test_weighted_scaling_is_centered_and_unit_variance():
    value = np.array([1.0, 2.0, 6.0, 8.0])
    weight = np.array([2.0, 1.0, 3.0, 4.0])
    z, details = RUN.weighted_scale(value, weight)
    assert abs(np.average(z, weights=weight)) < 1e-14
    assert abs(np.average(z * z, weights=weight) - 1.0) < 1e-14
    assert details["standardization_weight"] == 10.0


def test_augment_design_adds_only_post_interaction():
    q = np.array([1, 2, 3, 4, 5])
    webb = np.linspace(-1, 1, 5)
    family = np.array(["11", "11", "13", "13", "15"])
    months = ["2022-11", "2023-01"]
    base = RUN.CORE.build_design(q, webb, family, months, "pooled")
    control = np.arange(5, dtype=float)
    augmented = RUN.augment_design(base, {"computer_use": control}, months)
    assert augmented.regressors.shape == (10, 6)
    assert augmented.regressor_labels[-1] == "computer_use_z_x_post"
    assert np.array_equal(augmented.regressors[:, -1].reshape(5, 2)[:, 0],
                          np.zeros(5))
    assert np.array_equal(augmented.regressors[:, -1].reshape(5, 2)[:, 1],
                          control)


def test_support_hash_is_order_sensitive_and_stable():
    codes = np.array(["0010", "0020", "0030"])
    assert RUN.support_hash(codes) == RUN.support_hash(codes.copy())
    assert RUN.support_hash(codes) != RUN.support_hash(codes[::-1])
