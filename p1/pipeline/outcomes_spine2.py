#!/usr/bin/env python3
"""outcomes_spine2.py — Spine-two outcome builder: the earnings fingerprint.

What this module computes
-------------------------
docs/基金转换实验_博士研究计划.md §7 defines spine two entirely from first
principles — no literature package required for the 口径. Spines one and four
wait on the 文献包; spine two ships now.

Variables (all units are decimal CAR relative to market-model prediction):
  car_t0 … car_t120   : cumulative abnormal return at each trading day from
                        event day 0 through day +120 (121 columns, 0-indexed).
                        Day 0 is the announcement date for own-announcement
                        events, or the first peer's announcement for peer events.
  permanent           : CAR(+120) — how much of the initial move persists.
  reversal            : the same-direction-decaying part of CAR(+5) − CAR(+120).
                        Defined as sign(CAR₅) × max(0, sign(CAR₅)×(CAR₅−CAR₁₂₀)).
                        Zero when CAR(+120) ≥ CAR(+5) for a positive initial move
                        (or ≤ for a negative one); positive when a gain was
                        partially given back; negative when a loss was partly
                        recovered.
  var_ratio_5_1       : Jegadeesh-style variance ratio — Var(5-day) / (5×Var(1-day))
                        computed within each (permno, treated) cell.  Near 1 =
                        random walk; < 1 = mean-reversion (short-term reversal).

Event types (two separate runs, §7):
  own                 : the stock's own earnings announcement.
  peer                : announcement by a same-basket peer that has already
                        announced before this stock's own announcement date.

DiD wedge (aggregated, not per-event):
  did_wedge_t         : mean CAR_t(treated) − mean CAR_t(control), for each
                        path point t ∈ {0, …, 120}.  These are the points on
                        the "treated − control wedge plot" (§7).  T5 runs the
                        stacked-DiD regression on top of the per-event data;
                        the wedge here is the raw, unadjusted mean difference.

I/O contract
------------
Input DataFrames must have at minimum:
  returns_df  : [permno, date, ret, mktrf]
                ret   — daily net return, decimal (0.01 = 1 %)
                mktrf — market excess return same day, decimal
  events_df   : [permno, event_date, event_type]
                event_type ∈ {'own', 'peer'}
  treatment_df: [permno, treated]
                treated — bool or 0/1; 1 if this stock is treated (conv_exp > 0)

Output:
  event_cars  : per-event parquet [permno, event_date, event_type, treated,
                car_t0 … car_t120, permanent, reversal]
  wedge       : CSV [event_type, t, did_wedge, n_treated, n_control]
  var_ratios  : CSV [permno, treated, var_ratio_5_1, n_days]

Why offline-first
-----------------
This module never calls WRDS or any network resource.  It takes DataFrames so
it can be unit-tested on synthetic data.  The actual pull happens in
p1/wrds/pull.py; this module consumes whatever daily returns land in
p1/wrds/raw/dsf.parquet.
"""
from __future__ import annotations

import math
import os
import sys
from pathlib import Path

import pandas as pd
import numpy as np

HERE = Path(__file__).parent
REPO = HERE.parent.parent

# ── output paths (override via env for tests) ─────────────────────────────────
_DEFAULT_OUT = REPO / "p1" / "output" / "spine2"
SPINE2_OUT = Path(os.environ.get("SPINE2_OUT", str(_DEFAULT_OUT)))
EVENT_CARS_PATH = SPINE2_OUT / "event_cars.parquet"
WEDGE_PATH = SPINE2_OUT / "wedge.csv"
VAR_RATIOS_PATH = SPINE2_OUT / "var_ratios.csv"

# ── §7 constants (frozen) ─────────────────────────────────────────────────────
CAR_WINDOW_END: int = 120        # §7: CAR path [0, +120]
REVERSAL_SHOULDER: int = 5       # §7: reversal uses CAR(+5) as the "initial" point
DEFAULT_EST_WINDOW: tuple[int, int] = (-252, -21)   # pre-event beta estimation window
MIN_POST_OBS: int = 10           # skip event if fewer post-event days in sample


# ── market-model helpers ──────────────────────────────────────────────────────

def _ols_slope(x: np.ndarray, y: np.ndarray) -> float:
    """OLS slope of y on x.  Falls back to 1.0 on degenerate input (beta = 1)."""
    denom = float(np.dot(x, x))
    return float(np.dot(x, y)) / denom if denom > 1e-14 else 1.0


def _fit_market_model(
    ret: pd.Series,
    mktrf: pd.Series,
    event_date: pd.Timestamp,
    trading_dates: pd.DatetimeIndex,
    est_window: tuple[int, int],
) -> tuple[float, float]:
    """Fit alpha, beta over the estimation window.

    Falls back to (0.0, 1.0) when fewer than 5 observations are available.
    """
    ed_pos = trading_dates.searchsorted(event_date)
    lo = int(max(0, ed_pos + est_window[0]))
    hi = int(max(0, ed_pos + est_window[1]))
    est_dates = trading_dates[lo:hi]
    y_all = ret.reindex(est_dates)
    x_all = mktrf.reindex(est_dates)
    mask = y_all.notna() & x_all.notna()
    y = y_all[mask].values
    x = x_all[mask].values
    if len(y) < 5:
        return 0.0, 1.0
    beta = _ols_slope(x - x.mean(), y - y.mean())
    alpha = float(y.mean()) - beta * float(x.mean())
    return alpha, beta


# ── core CAR computation ──────────────────────────────────────────────────────

def compute_car_path(
    ret: pd.Series,
    mktrf: pd.Series,
    event_date: pd.Timestamp,
    trading_dates: pd.DatetimeIndex,
    window_end: int = CAR_WINDOW_END,
    est_window: tuple[int, int] = DEFAULT_EST_WINDOW,
) -> list[float] | None:
    """Compute the cumulative abnormal return path from day 0 to day +window_end.

    Returns a list of length (window_end + 1) where index t corresponds to CAR
    at trading-day t relative to event_date, or None if fewer than MIN_POST_OBS
    post-event trading days exist.

    Abnormal return at day t: AR_t = ret_t - alpha - beta × mktrf_t.
    CAR at day t: cumsum of AR_0 … AR_t.
    Missing returns within the event window are left as NaN in the path so
    downstream callers can distinguish gaps from computed zeros.
    """
    event_date = pd.Timestamp(event_date)
    ed_pos = int(trading_dates.searchsorted(event_date))
    if ed_pos >= len(trading_dates):
        return None

    # Post-event slice: days 0 through +window_end
    end_pos = min(ed_pos + window_end + 1, len(trading_dates))
    if end_pos - ed_pos < MIN_POST_OBS:
        return None

    alpha, beta = _fit_market_model(ret, mktrf, event_date, trading_dates, est_window)

    event_slice = trading_dates[ed_pos:end_pos]
    ar = ret.reindex(event_slice) - alpha - beta * mktrf.reindex(event_slice)

    # Build a full-length path (window_end + 1), NaN-padding if the stock
    # has no return on some days within the event window
    path = np.full(window_end + 1, np.nan)
    for i, d in enumerate(event_slice):
        if i <= window_end:
            path[i] = ar.get(d, np.nan)

    # CumSum — NaN propagates so a gap mid-path taints all subsequent values
    car = np.nancumsum(path)
    # Restore NaN where the input was NaN (nancumsum skips; we want propagation)
    nan_mask = np.isnan(path)
    for i in range(1, len(nan_mask)):
        if nan_mask[i]:
            car[i:] = np.nan
            break

    return car.tolist()


# ── §7 decomposition ──────────────────────────────────────────────────────────

def decompose_permanent_reversal(car: list[float]) -> tuple[float, float]:
    """Extract permanent and reversal components from a CAR path.

    §7 (docs/基金转换实验_博士研究计划.md):
      permanent = CAR(+120)
      reversal  = same-direction-decaying part of CAR(+5) − CAR(+120)
                = sign(CAR₅) × max(0, sign(CAR₅) × (CAR₅ − CAR₁₂₀))

    This is zero when the initial move did not reverse; positive when a gain
    was partially given back; negative when a loss was partially recovered.
    The magnitude equals the amount of the initial move that disappeared by
    day +120.

    Returns (permanent, reversal).  Either may be NaN if the path is short or
    the relevant day has missing data.
    """
    if len(car) <= CAR_WINDOW_END or len(car) <= REVERSAL_SHOULDER:
        return (float("nan"), float("nan"))

    permanent = car[CAR_WINDOW_END]
    car5 = car[REVERSAL_SHOULDER]

    if math.isnan(permanent):
        return (float("nan"), float("nan"))
    if math.isnan(car5) or abs(car5) < 1e-14:
        return (permanent, 0.0)

    initial_sign = 1 if car5 > 0 else -1
    decay = car5 - permanent          # positive = move that was given back
    reversal = initial_sign * max(0.0, initial_sign * decay)
    return (permanent, reversal)


# ── spine-two builder ─────────────────────────────────────────────────────────

def build_spine2(
    returns_df: pd.DataFrame,
    events_df: pd.DataFrame,
    treatment_df: pd.DataFrame,
    est_window: tuple[int, int] = DEFAULT_EST_WINDOW,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Build all spine-two outcome variables.

    Parameters
    ----------
    returns_df   : [permno, date, ret, mktrf]
    events_df    : [permno, event_date, event_type] — event_type ∈ {'own','peer'}
    treatment_df : [permno, treated]   — treated is bool or 0/1
    est_window   : pre-event market-model estimation window (trading days)

    Returns
    -------
    event_cars : per-event DataFrame with car_t0 … car_t120, permanent, reversal
    wedge      : per-path-point DiD wedge DataFrame
    var_ratios : per-permno variance-ratio DataFrame
    """
    # ── input validation ──────────────────────────────────────────────────────
    _req(returns_df,   ("permno", "date", "ret", "mktrf"), "returns_df")
    _req(events_df,    ("permno", "event_date", "event_type"), "events_df")
    _req(treatment_df, ("permno", "treated"), "treatment_df")

    bad_types = set(events_df["event_type"].unique()) - {"own", "peer"}
    if bad_types:
        raise ValueError(f"Unknown event_type values (expected 'own'/'peer'): {bad_types!r}")

    # ── return series indexed by date, keyed by permno ────────────────────────
    returns_df = returns_df.copy()
    returns_df["date"] = pd.to_datetime(returns_df["date"])
    all_trading_dates = pd.DatetimeIndex(sorted(returns_df["date"].unique()))

    ret_by: dict[int, pd.Series] = {}
    mkt_by: dict[int, pd.Series] = {}
    for permno, grp in returns_df.groupby("permno"):
        g = grp.set_index("date").sort_index()
        ret_by[int(permno)] = g["ret"]
        mkt_by[int(permno)] = g["mktrf"]

    # ── treatment lookup ──────────────────────────────────────────────────────
    treated_map: dict[int, bool] = {
        int(row["permno"]): bool(row["treated"])
        for _, row in treatment_df.iterrows()
    }

    # ── per-event CAR computation ─────────────────────────────────────────────
    events_df = events_df.copy()
    events_df["event_date"] = pd.to_datetime(events_df["event_date"])

    rows: list[dict] = []
    for _, ev in events_df.iterrows():
        permno = int(ev["permno"])
        if permno not in ret_by:
            continue    # no return history — not an error, just skip

        mkt = mkt_by.get(permno, pd.Series(dtype=float))
        car = compute_car_path(
            ret_by[permno], mkt,
            ev["event_date"], all_trading_dates,
            window_end=CAR_WINDOW_END, est_window=est_window,
        )
        if car is None:
            continue

        permanent, reversal = decompose_permanent_reversal(car)
        row: dict = {
            "permno": permno,
            "event_date": ev["event_date"],
            "event_type": str(ev["event_type"]),
            "treated": treated_map.get(permno, False),
            "permanent": permanent,
            "reversal": reversal,
        }
        for t, v in enumerate(car):
            row[f"car_t{t}"] = v
        rows.append(row)

    _car_cols = [f"car_t{t}" for t in range(CAR_WINDOW_END + 1)]
    _base_cols = ["permno", "event_date", "event_type", "treated",
                  "permanent", "reversal"]
    if rows:
        event_cars = pd.DataFrame(rows)[_base_cols + _car_cols]
    else:
        event_cars = pd.DataFrame(columns=_base_cols + _car_cols)

    # ── DiD wedge — raw mean difference at each path point ───────────────────
    wedge_rows: list[dict] = []
    if not event_cars.empty:
        for etype in ("own", "peer"):
            sub = event_cars[event_cars["event_type"] == etype]
            if sub.empty:
                continue
            trt = sub[sub["treated"].astype(bool)]
            ctl = sub[~sub["treated"].astype(bool)]
            n_t, n_c = len(trt), len(ctl)
            for t in range(CAR_WINDOW_END + 1):
                col = f"car_t{t}"
                t_mean = float(trt[col].mean()) if n_t > 0 else float("nan")
                c_mean = float(ctl[col].mean()) if n_c > 0 else float("nan")
                wedge_rows.append({
                    "event_type": etype, "t": t,
                    "did_wedge": t_mean - c_mean,
                    "n_treated": n_t, "n_control": n_c,
                })
    wedge = (
        pd.DataFrame(wedge_rows)
        if wedge_rows
        else pd.DataFrame(columns=["event_type", "t", "did_wedge",
                                    "n_treated", "n_control"])
    )

    # ── variance ratio (Jegadeesh reversal test, §7) ──────────────────────────
    # Var(5-day non-overlapping) / (5 × Var(1-day)) within each permno.
    # Pre/post split requires effective_date which lives in treatment_df; that
    # conditioning is done in T5's regression, not here.  This gives the full-
    # sample ratio as a baseline; the caller can filter by event date if needed.
    vr_rows: list[dict] = []
    for permno, ret_s in ret_by.items():
        if len(ret_s) < 10:
            continue
        vals = ret_s.dropna().values
        if len(vals) < 10:
            continue
        var_1 = float(np.var(vals, ddof=1)) if len(vals) > 1 else float("nan")
        five_day = np.array([
            vals[i:i + 5].sum() for i in range(0, len(vals) - 4, 5)
        ])
        var_5 = float(np.var(five_day, ddof=1)) if len(five_day) > 1 else float("nan")
        if math.isnan(var_1) or var_1 < 1e-14:
            continue
        vr_rows.append({
            "permno": permno,
            "treated": treated_map.get(permno, False),
            "var_ratio_5_1": var_5 / (5 * var_1),
            "n_days": len(vals),
        })
    var_ratios = (
        pd.DataFrame(vr_rows)
        if vr_rows
        else pd.DataFrame(columns=["permno", "treated", "var_ratio_5_1", "n_days"])
    )

    return event_cars, wedge, var_ratios


# ── helpers ────────────────────────────────────────────────────────────────────

def _req(df: pd.DataFrame, cols: tuple[str, ...], name: str) -> None:
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"{name} missing required columns: {missing}")


# ── CLI entry point ────────────────────────────────────────────────────────────

def run(
    returns_path: Path,
    events_path: Path,
    treatment_path: Path,
    out_dir: Path = SPINE2_OUT,
) -> None:
    """Read inputs, compute spine-two, write outputs."""
    out_dir.mkdir(parents=True, exist_ok=True)

    def _read(p: Path) -> pd.DataFrame:
        return pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p)

    print(f"[spine2] returns:   {returns_path}")
    returns_df = _read(returns_path)
    print(f"[spine2] events:    {events_path}")
    events_df = _read(events_path)
    print(f"[spine2] treatment: {treatment_path}")
    treatment_df = _read(treatment_path)

    event_cars, wedge, var_ratios = build_spine2(returns_df, events_df, treatment_df)
    print(f"[spine2] events computed: {len(event_cars)}")
    print(f"[spine2] wedge rows:      {len(wedge)}")
    print(f"[spine2] var-ratio rows:  {len(var_ratios)}")

    event_cars.to_parquet(out_dir / "event_cars.parquet", index=False)
    wedge.to_csv(out_dir / "wedge.csv", index=False, lineterminator="\n")
    var_ratios.to_csv(out_dir / "var_ratios.csv", index=False, lineterminator="\n")
    print(f"[spine2] outputs written to {out_dir}")


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: outcomes_spine2.py <returns> <events> <treatment> [out_dir]")
        sys.exit(1)
    run(
        Path(sys.argv[1]),
        Path(sys.argv[2]),
        Path(sys.argv[3]),
        Path(sys.argv[4]) if len(sys.argv) > 4 else SPINE2_OUT,
    )
