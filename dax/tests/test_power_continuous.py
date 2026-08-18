"""Tests for the D1 primary power engine and the D3 frozen standard.

These pin the two properties that make the rebuilt engine trustworthy: it
cannot read post-event outcomes, and it cannot invent its own pass bar.
"""

import datetime as dt
import json
import pathlib
import sys

import pytest

POWER = pathlib.Path(__file__).resolve().parents[1] / "memo" / "power_calcs"
sys.path.insert(0, str(POWER))

import simulate_power_continuous as spc  # noqa: E402
from simulate_power import Cell, Dose     # noqa: E402


def _cell(occ, month, employment=0.7):
    return Cell(cps_occ=occ, month=month, industry="IND1", education_group="college",
                n_unweighted=100, weight_sum=100.0, weight_sq_sum=120.0,
                employment_rate=employment, hours_mean=30.0, hours_variance=100.0,
                employment_hours_covariance=1.0, dose_sd=0.01, max_crosswalk_weight=0.9)


def _dose(occ, month, increment, prior=0.0):
    return Dose(event_id=f"E{month.isoformat()}", event_month=month,
                cps_occ=occ, increment=increment, prior_dax=prior)


# --- the seal ---------------------------------------------------------------

def test_refuses_cells_at_or_after_the_first_event():
    """Post-event moments must never enter a pre-gate power calculation."""
    cells = [_cell("OCC1", dt.date(2023, 5, 1))]
    with pytest.raises(SystemExit, match="REFUSED"):
        spc.assert_seal(cells, dt.date(2023, 3, 1))


def test_accepts_strictly_pre_event_cells():
    spc.assert_seal([_cell("OCC1", dt.date(2022, 5, 1))], dt.date(2023, 3, 1))


# --- the dose path ----------------------------------------------------------

def test_dax_path_is_cumulative_and_steps_at_event_months():
    months = spc.month_sequence(dt.date(2023, 1, 1), dt.date(2023, 6, 1))
    doses = [_dose("OCC1", dt.date(2023, 3, 1), 0.04),
             _dose("OCC1", dt.date(2023, 5, 1), 0.06)]
    path = spc.dax_paths(doses, months)["OCC1"]
    assert list(path[:2]) == [0.0, 0.0], "no dose before the first event"
    assert path[2] == pytest.approx(0.04), "steps at the event month, not after"
    assert path[4] == pytest.approx(0.10), "increments accumulate"
    assert all(b >= a for a, b in zip(path, path[1:])), "primary path is monotone"


def test_dose_profile_rank_detects_a_degenerate_common_path():
    """If every occupation moves proportionally, identification is one contrast."""
    months = spc.month_sequence(dt.date(2023, 1, 1), dt.date(2023, 6, 1))
    proportional = [_dose(o, dt.date(2023, 3, 1), inc)
                    for o, inc in (("A", 0.02), ("B", 0.04), ("C", 0.08))]
    assert spc.dose_profile_rank(spc.dax_paths(proportional, months))["effective_rank"] == 1

    staggered = proportional + [_dose("A", dt.date(2023, 5, 1), 0.05)]
    assert spc.dose_profile_rank(spc.dax_paths(staggered, months))["effective_rank"] > 1


# --- D3: the frozen bar -----------------------------------------------------

def test_unfrozen_standard_yields_no_verdict():
    sample = {"employment": {"mde80_per_0.10_dax": 0.02},
              "hours": {"mde80_per_0.10_dax": 0.5}}
    spc.judge(sample, {"status": "PLACEHOLDER_REQUIRES_REAL_CPS",
                       "standard": {"employment_mde_ceiling": None,
                                    "hours_mde_ceiling": None,
                                    "max_mde_fraction_of_benchmark": 0.5},
                       "benchmark": {"relative_decline": 0.13}})
    assert sample["employment"]["adequately_powered"] is None
    assert "not FROZEN" in sample["employment"]["reason"]


def test_break_even_inverts_the_ceiling_formula():
    sample = {"employment": {"mde80_per_0.10_dax": 0.0325},
              "hours": {"mde80_per_0.10_dax": 1.0}}
    spc.judge(sample, {"status": "PLACEHOLDER_REQUIRES_REAL_CPS",
                       "standard": {"employment_mde_ceiling": None,
                                    "hours_mde_ceiling": None,
                                    "max_mde_fraction_of_benchmark": 0.5},
                       "benchmark": {"relative_decline": 0.13}})
    # ceiling = 0.5 * 0.13 * baseline  ->  baseline = mde / 0.065
    assert sample["employment"]["break_even_baseline"] == pytest.approx(0.5, abs=1e-6)


def test_frozen_standard_produces_a_real_verdict():
    sample = {"employment": {"mde80_per_0.10_dax": 0.02},
              "hours": {"mde80_per_0.10_dax": 0.5}}
    spc.judge(sample, {"status": "FROZEN",
                       "standard": {"employment_mde_ceiling": 0.03,
                                    "hours_mde_ceiling": 0.4,
                                    "max_mde_fraction_of_benchmark": 0.5},
                       "benchmark": {"relative_decline": 0.13}})
    assert sample["employment"]["adequately_powered"] is True
    assert sample["hours"]["adequately_powered"] is False


def test_shipped_standard_is_unfrozen_and_carries_no_numbers():
    """The repository must not ship a guessed constant."""
    standard = json.loads((POWER / "power_standard.json").read_text())
    assert standard["status"] == "PLACEHOLDER_REQUIRES_REAL_CPS"
    assert standard["benchmark"]["baseline_employment_rate_22_25"] is None
    assert standard["standard"]["employment_mde_ceiling"] is None
    assert standard["frozen_window"]["end_month"] < "2023-03", \
        "the frozen window must end before the first eligible event"


def test_stacked_engine_no_longer_sets_its_own_bar():
    """D3 regression: the secondary engine must not derive a threshold."""
    source = (POWER / "simulate_power.py").read_text(encoding="utf-8")
    # Check executable assignments, not prose: the module deliberately quotes
    # the old formula in a comment explaining why it was removed.
    code = [line.split("#")[0] for line in source.splitlines()]
    assignments = [line for line in code if "threshold =" in line]
    assert assignments, "expected the threshold to still be assigned somewhere"
    for line in assignments:
        assert "baseline_gap" not in line and "baseline_hours_gap" not in line, \
            f"sample-derived pass bar is back, D3 forbids it: {line.strip()}"
        assert "_standard[" in line, \
            f"threshold must come from the frozen standard: {line.strip()}"
