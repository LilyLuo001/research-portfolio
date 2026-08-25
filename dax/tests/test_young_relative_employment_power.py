import importlib.util
import json
import math
import pathlib
import sys

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


def test_real_entry_requires_authenticated_beta_lookup(tmp_path):
    lookup = tmp_path / "lookup.csv"
    lookup.write_text("occ2010,exposure_quintile\n100,1\n", encoding="utf-8")
    receipt_path = tmp_path / "c1.json"
    receipt_path.write_text(json.dumps({"status": "BLOCKED"}), encoding="utf-8")
    with pytest.raises(POWER.RealPowerBlocked, match="status is PASS"):
        POWER.authenticate_c1(receipt_path, lookup)

    receipt_path.write_text(json.dumps({
        "status": "PASS",
        "outputs": {
            POWER.LOOKUP_OUTPUT_KEY: {"sha256": POWER.sha256_file(lookup)}
        },
        "design": {"primary_exposure": "aioe"},
    }), encoding="utf-8")
    with pytest.raises(POWER.RealPowerBlocked, match="dv_rating_beta"):
        POWER.authenticate_c1(receipt_path, lookup)

    receipt_path.write_text(json.dumps({
        "status": "PASS",
        "outputs": {
            POWER.LOOKUP_OUTPUT_KEY: {"sha256": POWER.sha256_file(lookup)}
        },
        "design": {"primary_exposure": "dv_rating_beta"},
    }), encoding="utf-8")
    assert POWER.authenticate_c1(receipt_path, lookup)["status"] == "PASS"


def test_cells_authentication_requires_audited_split(tmp_path):
    cells = tmp_path / "cells.csv"
    cells.write_text("month,occ2010\n2021-01,100\n", encoding="utf-8")
    receipt = tmp_path / "cells.json"
    receipt.write_text(json.dumps({
        "status": "PASS_PREPERIOD_CELLS",
        "post_outcomes_read": False,
        "source_seal": {"audited_split_status": "NOT_SUPPLIED_LIBRARY_CALL"},
        "cells_sha256": POWER.sha256_file(cells),
    }), encoding="utf-8")
    with pytest.raises(POWER.RealPowerBlocked, match="audited pre-period split"):
        POWER.authenticate_cells(receipt, cells)


def test_synthetic_validation_recovers_registered_effect_and_is_not_real_power():
    receipt = POWER.synthetic_validation()
    assert receipt["status"] == (
        "PASS_SYNTHETIC_REAL_ENGINE_VALIDATION_NOT_REAL_POWER"
    )
    assert receipt["real_power_executed"] is False
    assert receipt["post_outcomes_read"] is False
    assert receipt["conditional_ppml_equivalence_exercised"] is True
    assert receipt["injected_log_effect"] == -0.2
    assert receipt["recovered_log_effect"] == pytest.approx(-0.2, abs=1e-5)
    assert receipt["recovery_absolute_error"] < 1e-5
    assert receipt["simulation_smoke_effects"] == 2


def test_effect_grid_contains_all_authenticated_benchmarks():
    assert 0.0 in POWER.DEFAULT_EFFECTS
    for decline in (0.13, 0.16, 0.19):
        assert any(
            math.isclose(effect, math.log(1 - decline), abs_tol=1e-12)
            for effect in POWER.DEFAULT_EFFECTS
        )
