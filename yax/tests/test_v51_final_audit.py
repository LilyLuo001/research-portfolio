import ast
import csv
import hashlib
import importlib.util
import json
import pathlib
import sys

import numpy as np


ROOT = pathlib.Path(__file__).resolve().parents[2]
RUNNER = ROOT / "yax/analysis/postoutcome_v51_final_audit/run_v51_loco.py"
AUDIT = ROOT / "yax/analysis/postoutcome_v51_final_audit"
RESULTS = AUDIT / "YAX_V51_LOCO_RESULTS.json"
MANUSCRIPT = ROOT / "yax/manuscript/v5_1/YAX_MANUSCRIPT_v5_1_FINAL_SUBMISSION_DRAFT.md"
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


def test_loco_outputs_are_complete_and_hash_authenticated():
    result = json.loads(RESULTS.read_text())
    for filename, expected_rows in (("YAX_V51_LOCO_PRIMARY.csv", 468), ("YAX_V51_LOCO_G.csv", 444)):
        path = AUDIT / filename
        rows = list(csv.DictReader(path.open()))
        assert len(rows) == expected_rows
        assert len({row["deleted_census2018"] for row in rows}) == expected_rows
        assert all(row["treatment_recomputed_after_deletion"] == "False" for row in rows)
        assert hashlib.sha256(path.read_bytes()).hexdigest() == result["output_hashes"][filename]


def test_loco_numerical_decisions_match_machine_results():
    result = json.loads(RESULTS.read_text())
    primary = result["primary"]
    g_result = result["G"]
    assert np.isclose(primary["full_estimate"], -0.13107397642233506)
    assert np.isclose(primary["minimum_leave_one_out_estimate"], -0.1423840941720702)
    assert np.isclose(primary["maximum_leave_one_out_estimate"], -0.11055284331327743)
    assert primary["sign_changes"] == primary["crossed_or_reached_zero"] == 0
    assert np.isclose(g_result["full_estimate"], 0.030893508600474132)
    assert np.isclose(g_result["minimum_leave_one_out_estimate"], 0.025127659608323315)
    assert np.isclose(g_result["maximum_leave_one_out_estimate"], 0.03599317622412187)
    assert g_result["sign_changes"] == g_result["crossed_or_reached_zero"] == 0
    assert result["new_labor_outcome_specification_estimated"] is False
    assert result["leave_one_measure_out_labor_outcome_model_executed"] is False
    assert result["new_bootstrap_multipliers_generated"] is False


def test_final_documents_preserve_interpretation_boundaries():
    decision = (AUDIT / "YAX_V51_LOCO_DECISION.md").read_text()
    framing = (AUDIT / "YAX_V51_FINAL_INTERPRETATION_DECISION.md").read_text()
    ae_note = (AUDIT / "YAX_V51_AE_PRESENTATION_NOTE.md").read_text()
    power = (AUDIT / "YAX_V51_POWER_CODE_AUDIT.md").read_text()
    manuscript = MANUSCRIPT.read_text()
    assert "LOCO-B2" in decision and "LOCO-G1" in decision
    assert "SUBMIT-S1" in framing and "G-PARTIAL" in framing
    assert "not independent evidence" in ae_note
    assert "not wild-score intervals" in ae_note
    assert "POWER-C3" in power and "heuristic design-effect comparison" in power
    for required in (
        "not independent corroborating evidence",
        "not wild-score intervals",
        "LOCO-B2",
        "LOCO-G1",
        "No leave-one-measure-out labor-outcome models were run",
        "ratio of 3.649",
        "ratio of 3.167",
    ):
        assert required in manuscript
