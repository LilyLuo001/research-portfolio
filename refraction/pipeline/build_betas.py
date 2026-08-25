#!/usr/bin/env python3
"""REFR-R2 module 2 — announcement-regime betas with shrinkage toward a
characteristics-implied prior.

Per C0-R: beta_i is estimated from the stock's PRE-CONVERSION announcement-day
responses only — r_i regressed on S_std, pooled over pre-period announcements,
then shrunk. The lookahead ban is not a convention here, it is enforced: every
(permno, wave) estimate calls guards.prereg_guard.assert_no_lookahead with the
latest date it actually consumed, and the emitted `max_est_date` is what
assert A4 re-checks downstream.

Data seam: returns arrive as an injected frame. Building them from CRSP is
module 1's job and needs a price vendor; everything here is vendor-free and
therefore testable today.

THE FREEZE PROTOCOL IS ENFORCED, NOT DOCUMENTED
-----------------------------------------------
`beta.w_shrink` is null until REFR-GATE-PREREG. So:
  * point mode (one w) REFUSES to run while it is null — there is no default,
    because a default would silently pick the knob Gate-0 exists to choose;
  * sweep mode runs anyway, over `beta.w_shrink_sweep_grid`, because producing
    the sweep is precisely what Gate-0 line G2 consumes.

Emits the frame `assert_panel` expects:
  permno | wave | beta_i | se_beta | n_pre_announcements | max_est_date
plus `beta_ols` and `prior` for audit, and `w_shrink` in sweep mode.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from refraction.guards.prereg_guard import assert_no_lookahead  # noqa: E402


class NeedInfo(Exception):
    """Raised instead of substituting an input nobody supplied."""


class ConfigFrozenError(Exception):
    """Raised when a point estimate is attempted before w_shrink is frozen."""


def _ols(x: np.ndarray, y: np.ndarray):
    """Slope, its standard error, and n for y = a + b·x. Returns (nan, nan, n)
    when the design is degenerate rather than raising — a stock with no surprise
    variation has no announcement beta, which is a fact to record, not an error."""
    n = len(x)
    if n < 3 or np.allclose(x, x[0]):
        return np.nan, np.nan, n
    X = np.column_stack([np.ones(n), x])
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    dof = n - 2
    if dof <= 0:
        return float(coef[1]), np.nan, n
    s2 = float(resid @ resid) / dof
    xtx_inv = np.linalg.inv(X.T @ X)
    return float(coef[1]), float(np.sqrt(s2 * xtx_inv[1, 1])), n


def estimate_raw_betas(returns_ann: pd.DataFrame, surprises: pd.DataFrame,
                       stock_wave: pd.DataFrame, wave_effective: pd.Series,
                       n_pre_min: int) -> pd.DataFrame:
    """Unshrunk announcement-regime betas, pre-period only.

    returns_ann: permno | announcement_id | r
    surprises:   announcement_id | date_ET | S_std      (S_std NULL rows dropped —
                 a release with no consensus carries no surprise to regress on)
    stock_wave:  permno | wave
    """
    s = surprises.dropna(subset=["S_std"])[["announcement_id", "date_ET", "S_std"]]
    df = returns_ann.merge(s, on="announcement_id", how="inner").merge(
        stock_wave, on="permno", how="inner")
    df["date_ET"] = pd.to_datetime(df["date_ET"])

    rows = []
    for (permno, wave), g in df.groupby(["permno", "wave"], sort=True):
        eff = pd.Timestamp(wave_effective.loc[wave])
        pre = g[g["date_ET"] < eff]          # STRICTLY before — the lookahead ban
        n = len(pre)
        if n < n_pre_min:
            rows.append({"permno": permno, "wave": wave, "beta_ols": np.nan,
                         "se_beta": np.nan, "n_pre_announcements": n,
                         "max_est_date": None,
                         "estimable": False,
                         "reason": f"n_pre {n} < n_pre_min_for_estimation {n_pre_min}"})
            continue
        b, se, _ = _ols(pre["S_std"].to_numpy(float), pre["r"].to_numpy(float))
        max_date = pre["date_ET"].max().date()
        # The ban as a program invariant, per (permno, wave), on the data actually used.
        assert_no_lookahead(max_date, eff.date(), what="announcement-regime beta",
                            permno=permno, wave=wave)
        rows.append({"permno": permno, "wave": wave, "beta_ols": b, "se_beta": se,
                     "n_pre_announcements": n, "max_est_date": max_date.isoformat(),
                     "estimable": bool(np.isfinite(b)),
                     "reason": "" if np.isfinite(b) else "degenerate design"})
    return pd.DataFrame(rows)


def characteristics_prior(raw: pd.DataFrame, chars: pd.DataFrame | None,
                          prior_mode: str) -> pd.Series:
    """Prior belief about each stock's beta, per config `beta.prior`.

    characteristics_implied: cross-sectional OLS of the estimable raw betas on
    the supplied characteristics, evaluated for every stock. The characteristics
    must themselves be pre-period — that is the caller's contract, and A4 checks
    the estimation dates that feed it.

    grand_mean is available but is NOT a silent fallback: asking for
    characteristics without supplying them raises, because quietly degrading the
    prior would change every shrunk beta with no trace.
    """
    est = raw[raw["estimable"]]
    if prior_mode == "grand_mean":
        return pd.Series(float(est["beta_ols"].mean()), index=raw.index)
    if prior_mode != "characteristics_implied":
        raise NeedInfo(f"NEED_INFO: unknown beta.prior {prior_mode!r}; "
                       "frozen_config is the only legal source for this choice.")
    if chars is None or chars.empty:
        raise NeedInfo(
            "NEED_INFO: beta.prior is 'characteristics_implied' but no "
            "characteristics were supplied. Provide a permno-keyed frame of "
            "PRE-PERIOD characteristics, or set beta.prior to 'grand_mean' in "
            "frozen_config — this will not degrade silently.")
    cols = [c for c in chars.columns if c != "permno"]
    m = raw.merge(chars, on="permno", how="left")
    fit = m[m["estimable"] & m[cols].notna().all(axis=1)]
    if len(fit) < len(cols) + 2:
        raise NeedInfo(f"NEED_INFO: only {len(fit)} stocks carry both an estimable "
                       f"beta and complete characteristics — too few to fit a "
                       f"{len(cols)}-characteristic prior.")
    X = np.column_stack([np.ones(len(fit))] + [fit[c].to_numpy(float) for c in cols])
    coef, *_ = np.linalg.lstsq(X, fit["beta_ols"].to_numpy(float), rcond=None)
    Xall = np.column_stack([np.ones(len(m))] + [m[c].to_numpy(float) for c in cols])
    pred = Xall @ coef
    # A stock missing a characteristic gets the fitted mean, not a NaN that would
    # silently drop it from the panel.
    pred = np.where(np.isfinite(pred), pred, float(fit["beta_ols"].mean()))
    return pd.Series(pred, index=raw.index)


def shrink(beta_ols, se_beta, prior, w, mode: str, cross_var: float | None = None):
    """Shrink toward the prior with intensity w ∈ [0, 1].

    mode 'global'  — beta = w·prior + (1−w)·beta_ols, one knob for every stock.
      This is what C0-R describes ("收缩权重 w_shrink 是全局配置项") and what
      Gate-0's G2 sweeps.
    mode 'vasicek_precision' — the same knob scaling a classic Vasicek weight,
      so noisier estimates shrink further. Available for the §8.4 battery.
      NOTE: the two modes trace different SD(L̂) paths across the sweep, so which
      one Gate-0 runs is a design choice, not an implementation detail; it is
      recorded in frozen_config as beta.shrink_mode.
    """
    if not 0.0 <= float(w) <= 1.0:
        raise ValueError(f"shrinkage intensity must be in [0, 1], got {w}")
    if mode == "global":
        k = float(w)
    elif mode == "vasicek_precision":
        if cross_var is None or not np.isfinite(cross_var) or cross_var <= 0:
            raise NeedInfo("NEED_INFO: vasicek_precision needs a positive "
                           "cross-sectional variance of the raw betas.")
        se2 = np.square(np.asarray(se_beta, dtype=float))
        k = float(w) * (se2 / (se2 + cross_var))
    else:
        raise NeedInfo(f"NEED_INFO: unknown beta.shrink_mode {mode!r}.")
    return k * np.asarray(prior, dtype=float) + (1 - k) * np.asarray(beta_ols, dtype=float)


def build_betas(returns_ann, surprises, stock_wave, wave_effective, config,
                chars=None, sweep: bool = False) -> pd.DataFrame:
    """The R2 module-2 entry point. Returns the betas frame assert_panel consumes."""
    beta_cfg = config["beta"]
    raw = estimate_raw_betas(returns_ann, surprises, stock_wave, wave_effective,
                             int(beta_cfg["n_pre_min_for_estimation"]))
    if raw.empty:
        return raw
    prior = characteristics_prior(raw, chars, beta_cfg["prior"])
    mode = beta_cfg.get("shrink_mode", "global")
    cross_var = float(raw.loc[raw["estimable"], "beta_ols"].var(ddof=1)) \
        if raw["estimable"].sum() > 1 else np.nan

    def one(w):
        out = raw.copy()
        out["prior"] = prior.to_numpy()
        out["beta_i"] = shrink(out["beta_ols"], out["se_beta"], out["prior"],
                               w, mode, cross_var)
        out["w_shrink"] = float(w)
        return out

    if sweep:
        grid = beta_cfg["w_shrink_sweep_grid"]
        return pd.concat([one(w) for w in grid], ignore_index=True)

    w = beta_cfg["w_shrink"]
    if w is None:
        raise ConfigFrozenError(
            "beta.w_shrink is null: it is frozen at REFR-GATE-PREREG, inside the "
            "G2 feasible window. Point estimates are illegal until then — run "
            "sweep mode, which is what Gate-0 consumes. There is deliberately no "
            "default.")
    return one(w)
