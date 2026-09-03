import importlib.util
import json
import pathlib

import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "capability_panel" / "preflight.py"
SPEC = importlib.util.spec_from_file_location("w4_preflight", PATH)
assert SPEC and SPEC.loader
PREFLIGHT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PREFLIGHT)


def test_missing_budget_file_is_not_a_zero_or_implicit_ceiling(tmp_path):
    assert PREFLIGHT.signed_budget_ceiling(tmp_path / "absent.json") is None


def test_budget_requires_pi_signature_and_positive_usd(tmp_path):
    path = tmp_path / "budget.json"
    path.write_text(json.dumps({"status": "DRAFT", "usd_ceiling": 10}), encoding="utf-8")
    with pytest.raises(PREFLIGHT.PreflightError, match="PI_SIGNED"):
        PREFLIGHT.signed_budget_ceiling(path)
    path.write_text(json.dumps({
        "status": "PI_SIGNED", "usd_ceiling": 10,
        "signed_by": "PI", "signed_at_utc": "2026-08-19T00:00:00Z",
    }), encoding="utf-8")
    assert PREFLIGHT.signed_budget_ceiling(path)["usd_ceiling"] == 10


def test_projection_is_explicitly_per_repetition_and_excludes_standins():
    registry = json.loads((ROOT / "capability_panel" / "vintage_registry.json").read_text())
    projection = PREFLIGHT.direct_api_upper_bound(
        registry, ROOT / "data_built" / "price_histories.csv", task_count=220,
    )
    assert projection["direct_model_rows"] == 14
    assert projection["missing_price_model_rows"] == []
    assert projection["usd_upper_bound_per_repetition"] == pytest.approx(640.876544)
    formula = PREFLIGHT.run_plan_formula(registry, task_universe=220)
    assert formula["maximum_rows_per_repetition_at_task_universe"] == 18480


# --- amendment section 3a: the preservation route ---------------------------

GDPVAL_SHA = "f8422fab9b21d90c0ee5f0659842ab666d418cb8940842918f9f4b0df7ae0202"


def _preflight(tmp_path, extra, duration_covered=0, task_ids=220):
    """Run main() with everything satisfied except what the test varies."""
    avail = tmp_path / "avail.json"
    avail.write_text(json.dumps({
        "account_probe_performed": True,
        "status_counts": {"account_available": 14},
        "matrix": [],
    }))
    dur = tmp_path / "dur.json"
    dur.write_text(json.dumps({
        "n_unique_task_ids": task_ids,
        "task_completion_duration_status": "VERIFIED" if duration_covered else "MISSING",
        "task_completion_duration_fields": ["minutes"] if duration_covered else [],
    }))
    budget = tmp_path / "budget.json"
    budget.write_text(json.dumps({"status": "PI_SIGNED", "usd_ceiling": 100.0,
                                  "signed_by": "owner",
                                  "signed_at_utc": "2026-08-24T00:00:00Z"}))
    out = tmp_path / "receipt.json"
    PREFLIGHT.main([
        "--registry", str(ROOT / "capability_panel" / "vintage_registry.json"),
        "--prices", str(ROOT / "data_built" / "price_histories.csv"),
        "--availability", str(avail), "--duration-receipt", str(dur),
        "--budget-file", str(budget), "--output", str(out),
        "--base-commit", "a" * 40, "--integration-commit", "b" * 40,
        "--evidence-source-commit", "c" * 40, "--evidence-applied-commit", "d" * 40,
        "--evidence-patch-id", "e" * 40,
    ] + extra)
    return json.loads(out.read_text())


def test_duration_no_longer_blocks_capture_but_still_blocks_scoring(tmp_path):
    r = _preflight(tmp_path, ["--w3-status", "pushed_validated", "--w3-commit", "f" * 40])
    assert "task_duration_complete" not in r["gates"]
    assert r["scoring_gates"]["task_duration_complete"] is False
    assert r["scoring_allowed"] is False
    assert r["full_capture_allowed"] is True, "capture must proceed without duration"


def test_preservation_route_makes_the_w3_gate_not_applicable(tmp_path):
    """PRESERVE-2. The mapping is never consumed, so the gate cannot apply."""
    r = _preflight(tmp_path, [
        "--w3-status", "not_pushed",
        "--preservation-stimulus", f"gdpval_open_220:{GDPVAL_SHA}:220"])
    assert r["gates"]["w3_exact_commit"] == "not_applicable"
    assert r["full_capture_allowed"] is True
    assert r["preservation_route"]["label"] == "gdpval_open_220"
    assert r["preservation_route"]["task_count"] == 220


def test_a_mapping_run_keeps_the_w3_gate_unweakened(tmp_path):
    """The narrowing applies only to a declared preservation route."""
    r = _preflight(tmp_path, ["--w3-status", "not_pushed"])
    assert r["gates"]["w3_exact_commit"] is False
    assert r["full_capture_allowed"] is False


def test_preservation_task_count_comes_from_the_stimulus_not_the_duration_receipt(tmp_path):
    """PRESERVE-1. The duration receipt is what is being deferred."""
    r = _preflight(tmp_path, [
        "--w3-status", "not_pushed",
        "--preservation-stimulus", f"gdpval_open_220:{GDPVAL_SHA}:220"], task_ids=0)
    assert r["run_plan"]["task_universe_upper_bound"] == 220
    assert r["cost_projection"]["task_count_upper_bound"] == 220


def test_a_malformed_stimulus_is_refused(tmp_path):
    import pytest as _pytest
    for bad in ["nosha", f"label:{GDPVAL_SHA}", f"label:notahash:220",
                f"label:{GDPVAL_SHA}:0"]:
        with _pytest.raises(PREFLIGHT.PreflightError):
            _preflight(tmp_path, ["--w3-status", "not_pushed",
                                  "--preservation-stimulus", bad])
