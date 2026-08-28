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


def _demean_within(frame: pd.DataFrame, cols, by=("fund", "date")):
    """Absorb fund x date fixed effects by within-group demeaning."""
    g = frame.groupby(list(by))
    return {c: (frame[c].astype(float) - g[c].transform("mean")).to_numpy(float)
            for c in cols}


def pooled_interaction(sample: pd.DataFrame, controls=("r_resid_lag", "mkt"),
                       fund_date_fe: bool = True, z_controls=()):
    """The preferred design (clarification 2026-08-19).

    With **fund x date fixed effects** the identification is cross-sectional *within one
    ETF-day*: the CR main effect is absorbed by construction — CR does not vary within a
    fund-date — so what remains is differential exposure across constituents of the same
    ETF on the same day, which is the claim. Common ETF-level flow shocks cannot drive it.

    `z_controls` are the pre-specified characteristics whose CR interactions enter as
    controls, so a1 is not picking up CR x size or CR x illiquidity.
    """
    y_col, inter = "r_resid_fwd", "_CRxabsL"
    df = sample.copy()
    df[inter] = df["CR"].astype(float) * df["absL"].astype(float)
    zcols = [c for c in z_controls if c in df.columns]
    for c in zcols:
        df[f"_CRx{c}"] = df["CR"].astype(float) * df[c].astype(float)
    ctrl = [c for c in controls if c in df.columns] + [f"_CRx{c}" for c in zcols]

    if fund_date_fe:
        if not {"fund", "date"} <= set(df.columns):
            raise SafeguardViolation("fund x date FE requested but 'fund'/'date' missing")
        dm = _demean_within(df, [y_col, inter] + ctrl)
        y = dm[y_col]
        X = np.column_stack([dm[inter]] + [dm[c] for c in ctrl])
        n_groups = int(df.groupby(["fund", "date"]).ngroups)
        k = X.shape[1] + n_groups          # FE consume degrees of freedom
        a1_idx, flow = 0, None             # CR main effect absorbed, by design
    else:
        y = df[y_col].to_numpy(float)
        X = np.column_stack([np.ones(len(df)), df["CR"].to_numpy(float), df[inter].to_numpy(float),
                             *[df[c].to_numpy(float) for c in ctrl]])
        k, a1_idx = X.shape[1], 2
        flow = None

    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    dof = len(y) - k
    if dof <= 0:
        raise SafeguardViolation("fewer observations than parameters")
    s2 = float(resid @ resid) / dof
    se = np.sqrt(s2 * np.diag(np.linalg.inv(X.T @ X)))
    if not fund_date_fe:
        flow = float(coef[1])
    return {"a1": float(coef[a1_idx]), "se_a1": float(se[a1_idx]),
            "t_a1": float(coef[a1_idx] / se[a1_idx]) if se[a1_idx] > 0 else np.nan,
            "flow_main_effect": flow, "n": int(len(y)),
            "design": "pooled_interaction",
            "fixed_effects": "fund_x_date" if fund_date_fe else "none",
            "cr_interacted_controls": zcols}


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


def verdict(result: dict, config: dict, outcome_class: str = None) -> dict:
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
    # Clarification 2026-08-19: a signed price-persistence response cannot license the
    # measure on its own — it can be zero or negative while connectivity is strong.
    cls = outcome_class or ne.get("first_stage_primary_outcome_class")
    if cls != "trading_connectivity":
        raise SafeguardViolation(
            f"G8 licensing requires the TRADING connectivity outcome (got {cls!r}). The "
            "CR x |L| -> r_{t+1} result is corroboration: it is a signed price-persistence "
            "response, and price impact absorbed intraday leaves no next-day return.")
    from math import erf, sqrt
    t = result["t_a1"]
    p_one_sided = 0.5 * (1 - erf(t / sqrt(2)))          # H1: a1 > 0
    licensed = bool(t > 0 and p_one_sided <= float(alpha))
    return {"a1": result["a1"], "t": t, "p_one_sided": p_one_sided, "alpha": alpha,
            "licensed": licensed,
            "outcome": "licensed" if licensed else "retired_from_headline",
            "note": "predictive association, not causal (Plan §6.1.2)"}
