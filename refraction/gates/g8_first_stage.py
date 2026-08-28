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


EXPOSURES = {
    # freeze 1 (2026-08-28): the exposure is part of the registration, and it is tied to the
    # outcome. |CR| x |L| is the PRIMARY form for both trading-outcome arms; signed CR x |L|
    # belongs to the signed return corroboration and nowhere else.
    "abs_CR_x_absL": lambda cr, absl: np.abs(cr) * absl,
    "signed_CR_x_absL": lambda cr, absl: cr * absl,
}


def _check_exposure(exposure: str, outcome_class: str) -> None:
    if exposure not in EXPOSURES:
        raise SafeguardViolation("unregistered exposure %r" % (exposure,))
    if outcome_class == "trading_connectivity" and exposure != "abs_CR_x_absL":
        raise SafeguardViolation(
            "the primary trading outcome takes |CR| x |L| (freeze 1). Signed CR x |L| is "
            "forbidden for the primary: against unsigned abnormal volume it tests nothing, "
            "and against the sign(CR)-aligned imbalance it counts the flow's sign twice — "
            "the sign enters through the OUTCOME.")


def pooled_interaction(sample: pd.DataFrame, controls=("r_resid_lag", "mkt"),
                       fund_date_fe: bool = True, z_controls=(),
                       y_col: str = "r_resid_fwd",
                       exposure: str = "signed_CR_x_absL",
                       outcome_class: str = "signed_price_response_not_magnitude",
                       config: dict = None,
                       estimand: str = "baseline"):
    """The preferred design (clarification 2026-08-19; freezes 1 and 3 of 2026-08-28).

    With **fund x date fixed effects** the identification is cross-sectional *within one
    ETF-day*: the CR main effect is absorbed by construction — CR does not vary within a
    fund-date — so what remains is differential exposure across constituents of the same
    ETF on the same day, which is the claim. Common ETF-level flow shocks cannot drive it.

    `exposure` must match the outcome (freeze 1): the trading-connectivity primary takes
    |CR| x |L|; only the signed return corroboration takes signed CR x |L|.

    `z_controls` are the pre-specified characteristics whose CR interactions enter as
    controls, so a1 is not picking up CR x size or CR x illiquidity. In the BASELINE they
    must all be PREDETERMINED (freeze 3). Realized post-conversion basket weight is
    post-treatment: adding it changes the estimand to "incremental to the realized basket",
    so it is admitted only under `estimand="incremental_given_realized_basket"`, which is
    reported as a mechanism benchmark and can never replace the baseline row.
    """
    _check_exposure(exposure, outcome_class)
    inter = "_exposure"
    df = sample.copy()
    df[inter] = EXPOSURES[exposure](df["CR"].astype(float).to_numpy(),
                                    df["absL"].astype(float).to_numpy())
    zcols = [c for c in z_controls if c in df.columns]
    _check_baseline_controls(zcols, estimand, config)
    for c in zcols:
        df["_CRx" + c] = df["CR"].astype(float) * df[c].astype(float)
    ctrl = [c for c in controls if c in df.columns] + ["_CRx" + c for c in zcols]

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
            "cr_interacted_controls": zcols,
            "outcome_column": y_col, "exposure": exposure,
            "outcome_class": outcome_class, "estimand": estimand}


def _check_baseline_controls(zcols, estimand: str, config: dict) -> None:
    """Freeze 3: the baseline control vector is predetermined only."""
    if config is None:
        return
    ne = config["network_exposure"]
    banned = set(ne.get("first_stage_post_treatment_controls_forbidden_in_baseline") or [])
    hit = [c for c in zcols if c in banned]
    if not hit:
        return
    if estimand != "incremental_given_realized_basket":
        raise SafeguardViolation(
            "post-treatment control(s) %s in the BASELINE control vector (freeze 3). The AP "
            "chooses the realized creation basket, so conditioning on it silently changes the "
            "estimand. Run it as the mechanism horse race with "
            "estimand='incremental_given_realized_basket', and report it alongside — never "
            "instead of — the predetermined baseline." % (hit,))
    hr = ne.get("first_stage_mechanism_horse_race") or {}
    if hr.get("may_replace_baseline"):
        raise SafeguardViolation("the horse race may not be registered as the baseline")


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


def verdict(result: dict, config: dict, outcome_class: str = None,
            outcome_choice: dict = None, timestamp_audit: dict = None,
            census: dict = None) -> dict:
    """Registered decision rule: one-sided, on the LINEAR coefficient, at the registered
    level. Refuses to decide while that level is unset.

    The three preflight artefacts (freezes 1, 2, 4 of 2026-08-28) are required arguments in
    all but name. They are all things that must be settled BEFORE a treatment coefficient
    exists, so requiring them here is what makes the ordering enforceable rather than
    aspirational — see refraction/gates/g8_preflight.py.
    """
    ne = config["network_exposure"]
    # freeze 1 — one exact outcome, chosen on G7 data quality, before any coefficient
    if outcome_choice is None:
        raise SafeguardViolation(
            "NEED_HUMAN: no registered primary outcome. g8_preflight.choose_primary_outcome() "
            "must resolve the signed-imbalance vs abnormal-volume arm from G7's data-quality "
            "report and be committed to %s before G8 is adjudicated."
            % ne["first_stage_outcome_choice_rule"]["decision_record"])
    if result.get("exposure") != ne["first_stage_primary_exposure"]:
        raise SafeguardViolation(
            "G8 licensing requires the registered primary exposure %r, got %r (freeze 1)."
            % (ne["first_stage_primary_exposure"], result.get("exposure")))
    if outcome_choice.get("exposure") != result.get("exposure"):
        raise SafeguardViolation("estimated exposure does not match the registered choice")
    # freeze 2 — the claim G8 is allowed to make about timing
    if timestamp_audit is None or not timestamp_audit.get("audit_complete"):
        raise SafeguardViolation(
            "NEED_HUMAN: the ETF shares-outstanding timestamp audit is not complete "
            "(freeze 2). Daily Delta(SharesOut) does not identify a creation/redemption "
            "time, and G8's wording depends on what the vendor actually supplies.")
    # freeze 4 — how many CR EVENTS carry the mechanism
    if census is None:
        raise SafeguardViolation(
            "NEED_HUMAN: the CR event census is required before estimation (freeze 4). "
            "Mechanism variation comes from nonzero-CR fund-days, not constituent-day rows.")
    if not census.get("n_nonzero_cr_days"):
        raise SafeguardViolation(
            "the calibration sample contains no nonzero creation/redemption days — there is "
            "no mechanism variation to test, whatever the row count says.")
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
            "registered_outcome": outcome_choice["chosen"],
            "outcome_arm": outcome_choice["arm"],
            "exposure": result["exposure"],
            "estimand": result.get("estimand", "baseline"),
            "n_nonzero_cr_days": census["n_nonzero_cr_days"],
            "n_funds_with_any_cr": census["n_funds_with_any_cr"],
            "event_language": timestamp_audit["g8_event_language"],
            "within_day_ordering_identified": timestamp_audit["within_day_ordering_identified"],
            "note": "predictive association, not causal (Plan §6.1.2)"}
