import ast
import importlib.util
import pathlib
import sys

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNNER = ROOT / "yax/analysis/postoutcome_v51_final_audit/run_v51_loco.py"
SPEC = importlib.util.spec_from_file_location("yax_v51_final_loco_test", RUNNER)
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_delete_occupation_preserves_frozen_regressor_rows():
    young = np.arange(12.0).reshape(3, 4)
    older = young + 20
    regressors = np.arange(24.0).reshape(12, 2)
    y, o, x = MODULE.delete_occupation(young, older, regressors, 1)
    assert np.array_equal(y, young[[0, 2]])
    assert np.array_equal(o, older[[0, 2]])
    assert np.array_equal(x, regressors.reshape(3, 4, 2)[[0, 2]].reshape(8, 2))


def test_loco_loop_does_not_reconstruct_treatment():
    source = RUNNER.read_text()
    tree = ast.parse(source)
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "loco_rows")
    body = ast.get_source_segment(source, function)
    for prohibited in ("prepare_model", "weighted_quintiles", "weighted_mean_sd", "default_rng", "bootstrap"):
        assert prohibited not in body


def test_exactly_two_loco_calls_are_declared():
    source = RUNNER.read_text()
    tree = ast.parse(source)
    run = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "run")
    calls = [node for node in ast.walk(run) if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "loco_rows"]
    assert len(calls) == 2


def test_runner_generates_no_bootstrap_multipliers():
    source = RUNNER.read_text()
    for prohibited in ("default_rng(", "rng.choice(", "bootstrap_summary(", "wild_score_summary("):
        assert prohibited not in source


def test_sealed_targets_and_support_are_literal():
    assert MODULE.PRIMARY_EXPECTED == -0.13107397642233506
    assert MODULE.G_EXPECTED == 0.030893508600474132
    assert MODULE.COMMON_HASH == "1e184b27678b7978d4b15e618db5b44f44b5e9ec1b50b69b53093ec62e0ce462"
