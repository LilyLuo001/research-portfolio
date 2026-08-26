"""Tests for the YAX gate runner.

The gates exist to catch two specific mistakes: freezing on a power simulation
that is describing its own smoothness, and committing an outcome before the
pre-registration is sealed. Both are cheap to get wrong and impossible to undo,
so the checks themselves are worth testing.

The invariant that matters most: BLOCKED must never be reported as PASS, and
must never produce a zero exit status.
"""

import importlib.util
import json
import math
import pathlib

MODULE = pathlib.Path(__file__).resolve().parents[1] / "gates.py"
SPEC = importlib.util.spec_from_file_location("yax_gates", MODULE)
assert SPEC and SPEC.loader
gates = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gates)


def agg(points, null_size=0.05, coverage=0.95, **extra):
    """Build a power aggregate. `points` is [(relative_decline, power), ...]."""
    rows = [{"true_log_effect": 0.0, "rejection_probability_zero": null_size,
             "coverage_95": coverage}]
    for d, p in points:
        rows.append({"true_log_effect": math.log(1 - d),
                     "rejection_probability_zero": p, "coverage_95": coverage})
    return dict(results=rows, **extra)


# ------------------------------------------------------------ gradient

def test_ceiling_power_at_smallest_effect_is_an_engine_bug():
    """The exact failure the plan warns about: flat power across the grid."""
    r = gates.gate_gradient(agg([(0.01, 0.999), (0.05, 1.0), (0.19, 1.0)]))
    assert r.status == "FAIL"
    assert "SMALLEST" in r.detail and "engine bug" in r.detail


def test_gradient_passes_and_interpolates_the_mde():
    r = gates.gate_gradient(agg([(0.01, 0.40), (0.02, 0.80), (0.03, 0.95)]))
    assert r.status == "PASS"
    assert "MDE80" in r.detail and "2." in r.detail


def test_underpowered_design_is_distinguished_from_engine_bug():
    r = gates.gate_gradient(agg([(0.01, 0.05), (0.05, 0.12), (0.19, 0.30)]))
    assert r.status == "FAIL"
    assert "underpowered" in r.detail
    assert "engine bug" not in r.detail


def test_gradient_blocked_without_an_aggregate():
    assert gates.gate_gradient(None).status == "BLOCKED"


def test_gradient_blocked_on_too_few_points():
    assert gates.gate_gradient(agg([(0.02, 0.8)])).status == "BLOCKED"


# ------------------------------------------------------------ calibration

def test_oversized_inference_without_bootstrap_fails():
    r = gates.gate_calibration(agg([(0.02, 0.8)], null_size=0.066, coverage=0.935))
    assert r.status == "FAIL"
    assert "bootstrap" in r.detail


def test_oversized_inference_with_bootstrap_passes():
    r = gates.gate_calibration(
        agg([(0.02, 0.8)], null_size=0.066, bootstrap_mde80_relative=0.021))
    assert r.status == "PASS"


def test_well_calibrated_engine_passes_without_bootstrap():
    assert gates.gate_calibration(agg([(0.02, 0.8)], null_size=0.052)).status == "PASS"


# ------------------------------------------------------------ coverage rule

def test_failed_coverage_gate_may_not_unlock_the_freeze():
    r = gates.gate_coverage_rule(
        agg([(0.02, 0.8)], design_freeze_permitted=True,
            covered_route_mass_fraction=0.8870))
    assert r.status == "FAIL"
    assert "must not" in r.detail


def test_coverage_rule_passes_when_prespec_declares_all_three():
    assert gates.gate_coverage_rule(None).status == "PASS"


# ------------------------------------------------------------ runner

def test_blocked_never_exits_zero(capsys):
    """The invariant. 'Not checked' must not read as 'fine'."""
    code = gates.main(["--freeze-tag", "tag-that-does-not-exist"])
    out = capsys.readouterr().out
    assert code == 1
    assert "BLOCKED" in out
    assert "not the same as" in out


def test_json_output_is_parseable(capsys):
    gates.main(["--json", "--freeze-tag", "tag-that-does-not-exist"])
    payload = json.loads(capsys.readouterr().out)
    assert {r["gate"] for r in payload} >= {"gradient", "seal", "freeze_doc"}
    assert all(r["status"] in ("PASS", "FAIL", "BLOCKED") for r in payload)


def test_seal_gate_reports_current_repository_state():
    """No outcomes are committed in this repository and no tag exists."""
    r = gates.gate_seal("v1.0-preregistered")
    assert r.status == "PASS"
