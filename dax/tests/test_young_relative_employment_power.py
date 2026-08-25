import importlib.util
import math
import pathlib
import sys

import pandas as pd
import pytest


ROOT = pathlib.Path(__file__).resolve().parents[1]
PATH = ROOT / "memo" / "power_calcs" / "young_relative_employment_power.py"
SPEC = importlib.util.spec_from_file_location("young_relative_employment_power", PATH)
assert SPEC and SPEC.loader
POWER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = POWER
SPEC.loader.exec_module(POWER)


def test_post_calendar_preserves_october_2025_gap():
    months = POWER.planned_post_months()
    assert len(months) == 43
    assert months[0] == "2022-12" and months[-1] == "2026-07"
    assert "2025-10" not in months


def test_donor_rotation_never_accepts_post_outcomes():
    with pytest.raises(ValueError, match="post-period outcomes"):
        POWER.donor_rotation(["2022-11", "2022-12"], ["2023-01"])
    mapping = POWER.donor_rotation(["2022-10", "2022-11"], ["2022-12", "2023-01"])
    assert mapping == {"2022-12": "2022-10", "2023-01": "2022-11"}


def test_effect_injection_hits_only_q5_young_post():
    frame = pd.DataFrame({
        "age_group": ["young_22_25", "older_26_65", "young_22_25", "young_22_25"],
        "exposure_quintile": [5, 5, 1, 5],
        "is_post": [True, True, True, False],
        "mean_headcount": [100.0, 100.0, 100.0, 100.0],
    })
    result = POWER.inject_log_mean_effect(frame, math.log(0.81))
    assert result["mean_headcount"].tolist() == pytest.approx([81.0, 100.0, 100.0, 100.0])


def test_wild_draw_is_cluster_constant_and_deterministic():
    first = POWER.draw_rademacher_by_cluster([10, 10, 20, 30], seed=20260825)
    second = POWER.draw_rademacher_by_cluster([30, 20, 10], seed=20260825)
    assert first == second
    assert set(first.values()) <= {-1.0, 1.0}


def test_real_power_is_disabled_even_if_c1_placeholder_claims_pass():
    with pytest.raises(POWER.RealPowerBlocked, match="until C1"):
        POWER.assert_real_power_blocked(None)
    with pytest.raises(POWER.RealPowerBlocked, match="remains disabled"):
        POWER.assert_real_power_blocked({"status": "PASS"})


def test_synthetic_receipt_cannot_be_mistaken_for_power():
    receipt = POWER.synthetic_smoke()
    assert receipt["status"] == "SYNTHETIC_ENGINE_VALIDATION_NOT_POWER"
    assert receipt["real_power_executed"] is False
    assert receipt["post_outcomes_read"] is False
    assert receipt["primary_benchmark_log"] == round(math.log(0.81), 9)
    assert receipt["q5_young_shifted_headcount"] == 81.0
