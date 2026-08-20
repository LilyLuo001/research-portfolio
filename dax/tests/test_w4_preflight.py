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
