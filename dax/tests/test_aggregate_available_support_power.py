import importlib.util
import math
import pathlib
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "memo" / "power_calcs" / "aggregate_available_support_power.py"
SPEC = importlib.util.spec_from_file_location("aggregate_available_support_power", PATH)
assert SPEC and SPEC.loader
AGG = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AGG
SPEC.loader.exec_module(AGG)


def batch(effect, reject, exclude):
    return {
        "status": "DIAGNOSTIC_AVAILABLE_SUPPORT_ONLY",
        "design_freeze_permitted": False,
        "cells_sha256": "cells",
        "lookup_sha256": "lookup",
        "repetitions_per_effect": 999,
        "seed": 20260826,
        "occupation_clusters": 490,
        "effective_occupation_concentration_q1_q5": 58.42,
        "preperiod_months": 66,
        "planned_post_months": 43,
        "covered_route_mass_fraction": 0.887,
        "results": [{
            "true_log_effect": effect,
            "rejection_probability_zero": reject,
            "benchmark_exclusion_probability": exclude,
        }],
    }


def test_aggregate_stays_blocked_even_when_conditional_power_passes():
    result = AGG.aggregate([
        batch(0.0, 0.05, 0.9),
        batch(math.log(0.81), 0.9, 0.05),
    ])
    assert result["status"] == "DIAGNOSTIC_AVAILABLE_SUPPORT_POWER_PASS"
    assert result["design_freeze_permitted"] is False
    assert result["reason_design_freeze_blocked"] == (
        "primary exposure coverage gate failed"
    )
