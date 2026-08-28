#!/usr/bin/env python3
"""Gate G8 — does predetermined |L_tilt^pre| predict ETF-arbitrage connectivity?

Plan v2.4 §6.1, with the 2026-08-19 safeguards.

**Preferred design: the POOLED INTERACTION (safeguard 1).** Rather than estimating a noisy
per-stock phi and feeding those point estimates into a second stage as if they were
error-free, the connectivity claim is tested in one regression on the non-FOMC calibration
sample:

  r̃_{i,t+1} = θ·CR_{f,t} + **a₁·(CR_{f,t} × |L_tilt^pre_i|)** + ψ'W_{i,t} + u_{i,t+1}

`a₁` IS the first-stage claim: registered one-sided, a₁ > 0, in the MAGNITUDE of the lever
(refraction/G8_SIGN_PREDICTION.md — connectivity is a magnitude concept; the signed lever
carries direction, which belongs to the headline gamma).

The two-step remains available for reporting, but it must carry first-stage uncertainty
through a bootstrap; using phi-hat as an error-free outcome is refused.

Vendor-free: returns, creation/redemption and the frozen lever arrive as injected frames.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class SafeguardViolation(Exception):
    """Raised when a design the safeguards forbid is attempted."""


def build_calibration_sample(panel: pd.DataFrame, fomc_dates, config: dict) -> pd.DataFrame:
    """Post-conversion, NON-FOMC days only, with the registered seasoning buffer.

    panel: permno | fund | date | days_since_conversion | r_resid | CR | absL
    Excluding every FOMC date and its buffer is what keeps G8 from touching a headline
    outcome — the property that makes the carve-out narrow enough to sign.
    """
    cw = config["network_exposure"]["calibration_window"]
    lo = int(cw["start_trading_days_after_conversion"])
    hi = int(cw["end_trading_days_after_conversion"])
    buf = int(cw["exclude_buffer_trading_days"])

    d = pd.to_datetime(panel["date"])
    keep = panel["days_since_conversion"].between(lo, hi)
    blocked = pd.Series(False, index=panel.index)
    for f in pd.to_datetime(pd.Series(list(fomc_dates))):
        blocked |= (d - f).dt.days.abs() <= buf
    out = panel[keep & ~blocked].copy()
    out.attrs["n_dropped_fomc"] = int((keep & blocked).sum())
    out.attrs["n_dropped_window"] = int((~keep).sum())
    return out


def pooled_interaction(sample: pd.DataFrame, controls=("r_resid_lag", "mkt")):
    """The preferred design. Returns a1, its SE, t, n, and the nuisance flow term."""
    cols = [c for c in controls if c in sample.columns]
    X = np.column_stack([
        np.ones(len(sample)),
        sample["CR"].to_numpy(float),
        (sample["CR"].to_numpy(float) * sample["absL"].to_numpy(float)),   # a1 sits here
        *[sample[c].to_numpy(float) for c in cols],
    ])
    y = sample["r_resid_fwd"].to_numpy(float)
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    dof = len(y) - X.shape[1]
    if dof <= 0:
        raise SafeguardViolation("fewer observations than parameters")
    s2 = float(resid @ resid) / dof
    xtx_inv = np.linalg.inv(X.T @ X)
    se = np.sqrt(s2 * np.diag(xtx_inv))
    return {"a1": float(coef[2]), "se_a1": float(se[2]),
            "t_a1": float(coef[2] / se[2]) if se[2] > 0 else np.nan,
            "flow_main_effect": float(coef[1]), "n": int(len(y)), "design": "pooled_interaction"}


def two_step(sample: pd.DataFrame, propagate_uncertainty: bool):
    """Per-stock phi, then a cross-sectional first stage. REFUSED without uncertainty
    propagation — phi-hat is noisy and treating it as an error-free outcome understates
    the standard error of the thing the paper is claiming."""
    if not propagate_uncertainty:
        raise SafeguardViolation(
            "two-step G8 requires first-stage uncertainty propagation (safeguard 1): "
            "phi-hat estimates are noisy and may not enter the second stage as error-free "
            "outcomes. Use pooled_interaction, or bootstrap through both stages.")
    phis = []
    for (permno, fund), g in sample.groupby(["permno", "fund"]):
        if len(g) < 10 or g["CR"].std() == 0:
            continue
        X = np.column_stack([np.ones(len(g)), g["CR"].to_numpy(float)])
        b, *_ = np.linalg.lstsq(X, g["r_resid_fwd"].to_numpy(float), rcond=None)
        phis.append({"permno": permno, "fund": fund, "phi": float(b[1]),
                     "absL": float(g["absL"].iloc[0]), "n_obs": len(g)})
    return pd.DataFrame(phis)


def verdict(result: dict, config: dict) -> dict:
    """Registered decision rule: one-sided, on the LINEAR coefficient, at the registered
    level. Refuses to decide while that level is unset."""
    ne = config["network_exposure"]
    alpha = config.get("gate0_thresholds", {}).get("first_stage_primary_alpha")
    if alpha is None:
        raise SafeguardViolation(
            "gate0_thresholds.first_stage_primary_alpha is null — G8 cannot be adjudicated "
            "until it is decided. Choosing it now, with a1 in hand, is specification search.")
    if ne["first_stage_functional_form"] != "abs_L_tilt_pre":
        raise SafeguardViolation("registered functional form is |L_tilt^pre| (safeguard 2)")
    from math import erf, sqrt
    t = result["t_a1"]
    p_one_sided = 0.5 * (1 - erf(t / sqrt(2)))          # H1: a1 > 0
    licensed = bool(t > 0 and p_one_sided <= float(alpha))
    return {"a1": result["a1"], "t": t, "p_one_sided": p_one_sided, "alpha": alpha,
            "licensed": licensed,
            "outcome": "licensed" if licensed else "retired_from_headline",
            "note": "predictive association, not causal (Plan §6.1.2)"}
