#!/usr/bin/env python3
"""The w_shrink selection algorithm — frozen BEFORE the G2 sweep runs (audit item 6).

w_shrink cannot be set until the shrinkage-intensity sweep has been computed on real betas.
The MAP from sweep output to w_shrink can be, and freezing it now is the whole point: it
turns the realized value into a quantity a committed algorithm computes, rather than a
choice made with the sweep sitting in front of whoever makes it. That is what lets
pre-registration split into a stage 1 with no data in it and a stage 2 that adds only
mechanically determined numbers.

Plan v2.1 §9's G2 line asks for "a non-empty, non-knife-edge window of weights" in which
four conditions hold jointly. So:

  feasible(w)  <=>  SD(L_hat) >= sd_L_min
               and  |corr(L, ConvExp)| <= corr_L_convexp_max
               and  median pre-period announcements >= n_pre_median_min
               and  share with SE(beta_i) << SD(L_hat) >= se_share_min

  w_shrink  =  the MIDPOINT of the LONGEST run of consecutive feasible grid points,
               where runs shorter than sweep_window_min_gridpoints do not qualify.

Midpoint of the longest run, rather than (say) the smallest feasible weight, because §9's
requirement is about being far from the boundary: an endpoint sits adjacent to failure, and
a window one grid step wide was already declared a FAIL. Nothing here introduces a number —
every threshold is read from gate0_thresholds.

Vendor-free: the sweep arrives as an injected frame, so this runs the moment G2 does.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class G2Failure(Exception):
    """No feasible window. Routes to the exit matrix; never to a relaxed condition."""


CONDITIONS = {
    # name -> (sweep column, comparison, threshold key in gate0_thresholds)
    "sd_L_min":            ("sd_L", "ge", "sd_L_min"),
    "corr_L_convexp_max":  ("abs_corr_L_convexp", "le", "corr_L_convexp_max"),
    "n_pre_median_min":    ("n_pre_median", "ge", "n_pre_median_min"),
    "se_share_min":        ("se_share", "ge", "se_share_min"),
}


def feasible_mask(sweep: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Which grid points satisfy ALL four G2 conditions, and which one fails where.

    `sweep`: w | sd_L | abs_corr_L_convexp | n_pre_median | se_share — one row per grid
    point, produced by the G2 shrinkage-intensity sweep.
    """
    g0 = config["gate0_thresholds"]
    names = config["beta"]["w_shrink_selection"]["feasibility_conditions"]
    out = sweep.copy().sort_values("w").reset_index(drop=True)
    ok = pd.Series(True, index=out.index)
    for name in names:
        col, cmp_, key = CONDITIONS[name]
        thr = g0.get(key)
        if thr is None:
            raise G2Failure(
                "NEED_HUMAN: gate0 threshold %r is null — feasibility cannot be evaluated, "
                "and deciding it now with the sweep in hand is specification search." % key)
        if col not in out.columns:
            raise G2Failure("sweep is missing column %r for condition %r" % (col, name))
        passes = out[col] >= float(thr) if cmp_ == "ge" else out[col] <= float(thr)
        out["ok_" + name] = passes
        ok &= passes
    out["feasible"] = ok
    return out


def _runs(mask) -> list:
    """Contiguous runs of True, as (start, end) inclusive index pairs."""
    runs, start = [], None
    for i, v in enumerate(list(mask) + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            runs.append((start, i - 1))
            start = None
    return runs


def select(sweep: pd.DataFrame, config: dict) -> dict:
    """Apply the frozen algorithm. Returns the chosen w_shrink and everything behind it."""
    sel = config["beta"]["w_shrink_selection"]
    g0 = config["gate0_thresholds"]
    min_len = int(g0[sel["min_run_length"]]) if isinstance(sel["min_run_length"], str) \
        else int(sel["min_run_length"])

    table = feasible_mask(sweep, config)
    all_runs = _runs(table["feasible"].tolist())
    qualifying = [r for r in all_runs if (r[1] - r[0] + 1) >= min_len]

    if not qualifying:
        raise G2Failure(
            "G2 FAIL: no feasible window of at least %d grid points (runs found: %s). Plan "
            "§9 calls a window narrower than this knife-edge; route to the exit matrix — "
            "do not relax a condition to manufacture one."
            % (min_len, [(float(table.w[a]), float(table.w[b])) for a, b in all_runs]))

    # longest run; ties -> earliest start (lower w)
    best = max(qualifying, key=lambda r: (r[1] - r[0] + 1, -r[0]))
    lo, hi = best
    mid = (lo + hi) // 2                    # even-length run -> the LOWER of the two centres
    w = float(table.loc[mid, "w"])

    infeasible_w = table.loc[~table["feasible"], "w"].to_numpy(float)
    distance = (float(np.min(np.abs(infeasible_w - w))) if len(infeasible_w)
                else float("inf"))          # every grid point feasible
    return {
        "w_shrink": w,
        "algorithm": sel["algorithm"],
        "chosen_run_w": (float(table.loc[lo, "w"]), float(table.loc[hi, "w"])),
        "chosen_run_length": int(hi - lo + 1),
        "runs_w": [(float(table.w[a]), float(table.w[b])) for a, b in all_runs],
        "n_qualifying_runs": len(qualifying),
        "min_run_length": min_len,
        "distance_to_nearest_infeasible": distance,
        "feasible_mask": table,
        "determined_by": "frozen algorithm; no discretion at selection time",
    }
