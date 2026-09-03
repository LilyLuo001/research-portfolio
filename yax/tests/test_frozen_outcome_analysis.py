import importlib.util
import pathlib
import sys

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[2]
PATH = ROOT / "yax/analysis/run_frozen_v11.py"
SPEC = importlib.util.spec_from_file_location("run_frozen_v11", PATH)
MOD = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


def test_weighted_quintiles_keep_ties_and_cover_five_groups():
    values = np.arange(10, dtype=float)
    weights = np.ones(10)
    groups = MOD.weighted_quintiles(values, weights)
    assert set(groups) == {1, 2, 3, 4, 5}
    assert np.all(np.diff(groups) >= 0)


def test_conditional_ppml_recovers_injected_static_gradient():
    rng = np.random.default_rng(4)
    n_occ, n_month = 40, 18
    exposure = np.linspace(-1.5, 1.5, n_occ)
    post = np.arange(n_month) >= 10
    total = np.full((n_occ, n_month), 500.0)
    occ_effect = rng.normal(scale=0.3, size=n_occ)
    month_effect = rng.normal(scale=0.15, size=n_month)
    eta = occ_effect[:, None] + month_effect[None, :] - 0.08 * exposure[:, None] * post
    young = total / (1 + np.exp(-eta))
    x = (exposure[:, None] * post).reshape(-1, 1)
    fit, influence = MOD.fit_with_influence(young, total - young, x)
    assert fit.converged
    assert abs(fit.beta[0] + 0.08) < 1e-5
    assert influence.shape == (n_occ, 1)


def test_static_transition_is_not_part_of_frozen_post_list():
    assert MOD.TRANSITION == "2022-12"
    assert all(month >= "2023-01" for month in MOD.EXPECTED_POST)
    assert "2025-10" not in MOD.EXPECTED_POST
    assert MOD.EVENT_REFERENCE == "2022-10"
