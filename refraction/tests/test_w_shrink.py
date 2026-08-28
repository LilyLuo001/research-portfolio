"""The w_shrink selection algorithm, frozen before the G2 sweep exists (audit item 6).

These tests are the point of freezing it: they fix the map from feasibility inputs to
w_shrink now, so the realized value is something an algorithm computes rather than something
chosen with the sweep in hand.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from refraction.pipeline import w_shrink as ws   # noqa: E402

CONFIG = yaml.safe_load((ROOT / "refraction" / "frozen_config.yaml").read_text())
GRID = CONFIG["beta"]["w_shrink_sweep_grid"]


def sweep(sd_L=None, corr=None, n_pre=40, se_share=0.8):
    n = len(GRID)
    return pd.DataFrame({
        "w": GRID,
        "sd_L": sd_L if sd_L is not None else [0.30] * n,
        "abs_corr_L_convexp": corr if corr is not None else [0.20] * n,
        "n_pre_median": [n_pre] * n,
        "se_share": [se_share] * n,
    })


def feasible_between(lo_i, hi_i):
    """A sweep feasible exactly on grid indices [lo_i, hi_i]."""
    sd = [0.30 if lo_i <= i <= hi_i else 0.10 for i in range(len(GRID))]
    return sweep(sd_L=sd)


def test_the_algorithm_picks_the_midpoint_of_the_feasible_window():
    r = ws.select(feasible_between(3, 7), CONFIG)
    assert r["chosen_run_w"] == (0.3, 0.7)
    assert r["w_shrink"] == pytest.approx(0.5)


def test_the_chosen_point_sits_as_far_from_failure_as_the_grid_allows():
    """§9 asks for a non-knife-edge window, so the registered point must not abut one."""
    r = ws.select(feasible_between(3, 7), CONFIG)
    assert r["distance_to_nearest_infeasible"] == pytest.approx(0.3)
    # an endpoint would have been adjacent to failure
    assert r["w_shrink"] not in r["chosen_run_w"]


def test_the_longest_run_wins_when_there_are_several():
    sd = [0.30, 0.30, 0.10, 0.30, 0.30, 0.30, 0.30, 0.10, 0.10, 0.10, 0.10]
    r = ws.select(sweep(sd_L=sd), CONFIG)
    assert r["chosen_run_w"] == (0.3, 0.6)          # the 4-wide run, not the 2-wide one
    assert r["n_qualifying_runs"] == 2
    assert len(r["runs_w"]) == 2                    # both are reported, never averaged


def test_ties_break_toward_the_lower_weight():
    """Two equally long runs: the registered tie-break is the earlier one, so the choice is
    deterministic rather than dependent on iteration order."""
    sd = [0.30, 0.30, 0.10, 0.30, 0.30, 0.10, 0.10, 0.10, 0.10, 0.10, 0.10]
    r = ws.select(sweep(sd_L=sd), CONFIG)
    assert r["chosen_run_w"] == (0.0, 0.1)


def test_an_even_length_run_takes_the_lower_centre():
    r = ws.select(feasible_between(2, 5), CONFIG)    # 0.2..0.5, four points
    assert r["w_shrink"] == pytest.approx(0.3)


def test_a_knife_edge_window_fails_the_gate_rather_than_being_used():
    """Plan §R3 G2: a window narrower than 2 grid points is a FAIL, not a narrow pass."""
    with pytest.raises(ws.G2Failure) as e:
        ws.select(feasible_between(4, 4), CONFIG)
    assert "knife-edge" in str(e.value)
    assert "do not relax" in str(e.value)


def test_no_feasible_window_routes_to_the_exit_matrix():
    with pytest.raises(ws.G2Failure):
        ws.select(sweep(sd_L=[0.10] * len(GRID)), CONFIG)


def test_every_one_of_the_four_g2_conditions_can_bind():
    """None of them is decorative — each alone can empty the window."""
    n = len(GRID)
    for kwargs in ({"sd_L": [0.10] * n}, {"corr": [0.90] * n},
                   {"n_pre": 5}, {"se_share": 0.10}):
        with pytest.raises(ws.G2Failure):
            ws.select(sweep(**kwargs), CONFIG)


def test_a_null_threshold_stops_instead_of_being_defaulted():
    import copy
    cfg = copy.deepcopy(CONFIG)
    cfg["gate0_thresholds"]["sd_L_min"] = None
    with pytest.raises(ws.G2Failure) as e:
        ws.select(sweep(), cfg)
    assert "NEED_HUMAN" in str(e.value) and "specification search" in str(e.value)


def test_the_algorithm_introduces_no_thresholds_of_its_own():
    """Every number it uses is read from gate0_thresholds, which are separately pinned."""
    import inspect
    src = inspect.getsource(ws)
    body = src.split('"""', 2)[2]                    # skip the module docstring
    for cond, (_col, _cmp, key) in ws.CONDITIONS.items():
        assert key in CONFIG["gate0_thresholds"], key
    assert "0.25" not in body and "0.30" not in body and "0.70" not in body


def test_the_selection_is_deterministic_and_reports_its_workings():
    a = ws.select(feasible_between(3, 7), CONFIG)
    b = ws.select(feasible_between(3, 7), CONFIG)
    assert a["w_shrink"] == b["w_shrink"]
    for key in CONFIG["beta"]["w_shrink_selection"]["reports"]:
        probe = {"feasible_mask": "feasible_mask", "runs": "runs_w",
                 "chosen_run": "chosen_run_w", "w_shrink": "w_shrink",
                 "distance_to_nearest_infeasible": "distance_to_nearest_infeasible"}[key]
        assert probe in a, key


def test_w_shrink_itself_is_still_unset():
    """The ALGORITHM is frozen; the VALUE waits for real data. Freezing the value now would
    be inventing it."""
    assert CONFIG["beta"]["w_shrink"] is None
    assert CONFIG["beta"]["w_shrink_selection"]["algorithm"] == "midpoint_of_longest_feasible_run"


# --------------------------------------------------------------------------- #
# audit item 3 — the candidate GRID is frozen in stage 1, not just the rule    #
# --------------------------------------------------------------------------- #

def test_the_grid_itself_is_frozen_with_exact_values_range_and_spacing():
    """A "midpoint of the longest feasible run" computed over a grid chosen later is a
    different registration: the grid decides which runs can exist and how wide the
    midpoint's neighbourhood is."""
    spec = CONFIG["beta"]["w_shrink_grid_spec"]
    assert spec["min"] == 0.0 and spec["max"] == 1.0
    assert spec["step"] == 0.1 and spec["n_points"] == 11
    assert spec["endpoints_included"] is True
    assert spec["grid_frozen_at"] == "stage1"
    assert spec["refinement_after_sweep_forbidden"] is True
    # and the literal grid matches the spec, so the two cannot drift apart
    assert GRID == pytest.approx([spec["min"] + i * spec["step"]
                                  for i in range(spec["n_points"])])
    assert len(GRID) == spec["n_points"]


def test_refining_the_grid_after_the_sweep_would_move_the_answer():
    """Why the grid must be frozen: the SAME feasibility region gives a different w_shrink
    on a finer grid, so choosing the grid after seeing the sweep is choosing the answer."""
    import copy
    coarse = ws.select(feasible_between(3, 6), CONFIG)      # 0.3..0.6 on the 0.1 grid
    fine_cfg = copy.deepcopy(CONFIG)
    fine_grid = [round(i * 0.05, 2) for i in range(21)]
    fine_cfg["beta"]["w_shrink_sweep_grid"] = fine_grid
    sd = [0.30 if 0.3 <= w <= 0.6 else 0.10 for w in fine_grid]
    fine_sweep = pd.DataFrame({"w": fine_grid, "sd_L": sd,
                               "abs_corr_L_convexp": [0.20] * len(fine_grid),
                               "n_pre_median": [40] * len(fine_grid),
                               "se_share": [0.8] * len(fine_grid)})
    fine = ws.select(fine_sweep, fine_cfg)
    assert coarse["w_shrink"] != fine["w_shrink"]


def test_the_four_conditions_and_the_run_length_are_all_registered_in_stage_one():
    sel = CONFIG["beta"]["w_shrink_selection"]
    assert set(sel["feasibility_conditions"]) == {
        "sd_L_min", "corr_L_convexp_max", "n_pre_median_min", "se_share_min"}
    assert set(ws.CONDITIONS) == set(sel["feasibility_conditions"])
    assert sel["min_run_length"] == "sweep_window_min_gridpoints"
    assert CONFIG["gate0_thresholds"]["sweep_window_min_gridpoints"] == 2
    assert sel["tie_break_run"] == "earliest_start"
    assert sel["tie_break_midpoint"] == "lower"
    stage1 = CONFIG["prereg"]["stage1"]["contents"]
    assert "w_shrink_selection_algorithm" in stage1
