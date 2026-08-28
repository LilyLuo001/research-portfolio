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


# Freeze 1 (2026-08-28): the exposure is part of the registration, and it is tied to the
# outcome. |CR| x |L| is the PRIMARY form for both trading-outcome arms; signed CR x |L|
# belongs to the signed return corroboration and nowhere else.
#
# Final audit: BOTH forms are built from the two registered columns rather than from a
# single column plus abs()/sign(). The magnitude comes from CR_mag (|CR_raw| taken first,
# then clipped above and SD-scaled, so zeros survive); the sign comes from CR_raw. Calling
# np.abs() on a winsorized signed column was the bug — it left the lower-tail clip alive in
# magnitude form, giving a zero-event day a positive exposure.
EXPOSURES = {
    "abs_CR_x_absL": lambda mag, sign, absl: mag * absl,
    "signed_CR_x_absL": lambda mag, sign, absl: sign * mag * absl,
}


def _cr_columns(df: pd.DataFrame, config: dict = None):
    """The registered magnitude and sign columns, never derived from one another.

    Falls back to CR_mag/CR_raw by name when no config is passed, so callers that already
    hold a built frame do not need one; it refuses rather than reconstructing a magnitude
    from a signed column, because that reconstruction is precisely the bug.
    """
    d = (config or {}).get("network_exposure", {}).get("cr_definition", {})
    mag_col = d.get("exposure_magnitude_column", "CR_mag")
    sign_col = d.get("exposure_sign_column", "CR_raw")
    missing = [c for c in (mag_col, sign_col) if c not in df.columns]
    if missing:
        raise SafeguardViolation(
            "exposure needs the registered CR columns %s; missing %s. Do not substitute "
            "abs() of a winsorized signed column — a lower-tail clip survives that and gives "
            "zero-event days a positive exposure magnitude."
            % ([mag_col, sign_col], missing))
    return (df[mag_col].astype(float).to_numpy(),
            np.sign(df[sign_col].astype(float).to_numpy()))


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
    mag, sign = _cr_columns(df, config)
    df[inter] = EXPOSURES[exposure](mag, sign, df["absL"].astype(float).to_numpy())
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
            "outcome_class": outcome_class, "estimand": estimand,
            # freeze 6: the variation that actually identifies a1. Under fund x date FE the
            # exposure is demeaned within the ETF-day, so this is the dispersion the
            # coefficient is estimated off — not the raw column's SD, and not the row count.
            "within_fund_date_exposure_sd": float(np.std(X[:, a1_idx])),
            "exposure_sd_raw": float(np.std(df[inter].to_numpy(float))),
            "sd_outcome": float(np.std(y))}


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

    # Freeze 6: LOW POWER IS NOT MECHANISM FAILURE. Checked BEFORE the p-value, so a sparse
    # sample cannot be read as evidence of absence — and so the coefficient's own size can
    # never influence which branch is taken.
    ident = identifying_variation(result, census, config)

    # timing rule (2026-08-28) — the same-day primary takes DATED events only
    tcfg = ne["cr_event_timing"]
    if timestamp_audit.get("resolution") is not None:
        tc = census.get("timing")
        if tc is None:
            raise SafeguardViolation(
                "NEED_HUMAN: the CR event timing census is missing. The same-day aligned-OIB "
                "primary is registered %s, so interval events must be classified and excluded "
                "before it is estimated — pairing them with the vendor's update day dates "
                "constituent trading to the one day guaranteed to carry a printed share "
                "change." % tcfg["primary_sample"])
        # Non-relaxation: if the vendor lacks the freshness metadata, the standard does not
        # bend to keep a sample. The same-day primary is simply not identified.
        if tc.get("n_dated_events") == 0 and tc.get("n_interval_events"):
            return _report(result, census, ident, config, outcome_choice,
                           timestamp_audit, alpha, t, p_one_sided) | {
                "licensed": None,
                "outcome": "INSUFFICIENT_IDENTIFYING_VARIATION",
                "classification_basis": "no dated CR events",
                "reasons": [
                    "every CR event is interval-localized (%d of them): no observation "
                    "carries economic as-of freshness against a documented daily cutoff, so "
                    "the same-day aligned-OIB primary has no events it may use. The "
                    "freshness standard is not relaxed to manufacture one."
                    % tc["n_interval_events"]],
                "diagnostics": {"timing": tc},
                "note": ne["insufficient_variation_response"].strip()}
        if tc.get("n_interval_events") and tcfg["interval_events_in_primary"] == "excluded":
            # the sample must already have been filtered; verdict refuses to bless one that
            # still carries them
            raise SafeguardViolation(
                "%d interval event(s) are still in the primary sample. Apply "
                "g8_preflight.primary_timing_sample() first; interval events belong to the "
                "interval-level robustness outcome (%s), not to the same-day primary."
                % (tc["n_interval_events"], tcfg["interval_robustness"]["outcome"]))


    report = _report(result, census, ident, config, outcome_choice, timestamp_audit,
                     alpha, t, p_one_sided)

    if ident["insufficient"]:
        report.update({
            "licensed": None,
            "outcome": "INSUFFICIENT_IDENTIFYING_VARIATION",
            "classification_basis": "numerical degeneracy",
            "reasons": ident["reasons"], "diagnostics": ident["diagnostics"],
            "note": ne["insufficient_variation_response"].strip()})
        return report

    licensed = bool(t > 0 and p_one_sided <= float(alpha))
    report.update({
        "licensed": licensed,
        "outcome": ("licensed" if licensed
                    else _non_licensed_state(report, config)),
        "reasons": [], "diagnostics": ident["diagnostics"],
        "headline_use": "permitted" if licensed else "blocked",
        "note": "predictive association, not causal (Plan §6.1.2)"})
    return report


def _non_licensed_state(report: dict, config: dict) -> str:
    """Absence of evidence, or evidence of absence? (audit item 2)

    "Retired" asserts the effect is smaller than something worth caring about. That is a
    claim, and making it needs an equivalence margin on the outcome's own scale — the
    quantity that vanished when the 0.5-sigma line was withdrawn as belonging to the headline
    gamma. Without one, a non-significant a1 is INCONCLUSIVE, whether it is a precise zero or
    a hopelessly wide interval, and the CI and MDE in the report are what tell them apart.

    The GOVERNANCE consequence is the same either way: the measure does not enter the
    headline. Only what the paper may SAY differs.
    """
    ne = config["network_exposure"]
    margin = ne.get("first_stage_equivalence_margin")
    if margin is None:
        if ne.get("first_stage_retirement_requires_equivalence_margin", True):
            return "not_licensed_inconclusive"
        return "retired_from_headline"
    # equivalence: the whole reporting interval must sit inside +/- margin, in SD units
    sd_y = report.get("mde_sigma") and report["se_a1"] and report["a1"] is not None
    lo, hi = report.get("ci_low"), report.get("ci_high")
    scale = report.get("sd_outcome") or 1.0
    if lo is None or hi is None or not sd_y:
        return "not_licensed_inconclusive"
    m = float(margin) * float(scale)
    return "retired_from_headline" if (-m <= lo and hi <= m) else "not_licensed_inconclusive"


def identifying_variation(result: dict, census: dict, config: dict) -> dict:
    """Is there enough creation/redemption activity for the mechanism test to say anything?

    Freeze 6 (2026-08-28). Three ways the answer is no, and none of them is a finding about
    the mechanism:

      (a) fewer than 2 nonzero-CR fund-days. Structural, not a threshold: with one event
          there is no variation ACROSS events for anything to be estimated off.
      (b) degenerate exposure within fund-date. Under fund x date FE the CR level is
          absorbed, so if |L| does not vary across constituents of the same ETF-day the
          interaction is collinear with the fixed effects and a1 is not identified at all.
      (c) the minimum detectable effect is too large to be informative. This one is a power
          line, and it deliberately inherits Plan v2.1 §9's existing MDE convention
          (mde_sigma_max, in SD units) rather than inventing a second standard.

    MDE is computed from the ESTIMATED standard error, which is a property of the design and
    the sample — not of a1. The branch therefore cannot be steered by the coefficient's size.
    """
    from math import sqrt
    rules = config["network_exposure"]["first_stage_insufficient_variation_rules"]
    alpha = config.get("gate0_thresholds", {}).get("first_stage_primary_alpha")
    reasons = []

    n_events = int(census.get("n_nonzero_cr_days") or 0)
    if n_events < int(rules["min_nonzero_cr_days"]):
        reasons.append(
            "only %d nonzero creation/redemption fund-day(s); at least %d are needed for any "
            "variation across events to exist (%d constituent-day rows do not substitute)"
            % (n_events, rules["min_nonzero_cr_days"], census.get("n_constituent_day_rows", 0)))

    sd_x = float(result.get("within_fund_date_exposure_sd") or 0.0)
    sd_raw = float(result.get("exposure_sd_raw") or 0.0)
    # Relative, at machine scale: perfect collinearity with the fixed effects leaves
    # floating-point dust rather than an exact zero.
    rank_ratio = (sd_x / sd_raw) if sd_raw > 0 else 0.0
    if rank_ratio <= float(rules["degenerate_exposure_rank_tol"]):
        reasons.append(
            "the exposure has no within-fund-date variation (within/raw SD = %.3g): under "
            "fund x date fixed effects it is collinear with the fixed effects and there is "
            "nothing left for a1 to be identified off" % rank_ratio)

    # MDE is ALWAYS computed and ALWAYS reported (audit item 3). Whether it CLASSIFIES
    # anything is a separate question, and today the answer is no: the 0.5-sigma line was
    # WITHDRAWN in the 2026-08-28 audit, because Plan v2.1 §9 defined it for the HEADLINE
    # gamma — a different outcome, sample and clustering. Reporting a number is not the same
    # act as adjudicating on it.
    z_a = _z_one_sided(float(alpha)) if alpha is not None else None
    z_b = _z_one_sided(1.0 - float(rules["power_target"]))
    se, sd_y = result.get("se_a1"), result.get("sd_outcome")
    mde_sigma = None
    if z_a is not None and se and sd_y:
        mde_sigma = float((z_a + z_b) * se / sd_y)      # smallest a1 detectable, in SDs of y
    floor = rules.get("mde_sigma_max")
    power_active = bool(config["network_exposure"].get("first_stage_power_trigger_active"))
    if power_active and floor is not None and mde_sigma is not None and mde_sigma > float(floor):
        reasons.append(
            "MDE is %.3f SD of the outcome at alpha=%s and power=%s, above the registered G8 "
            "floor of %.2f SD" % (mde_sigma, alpha, rules["power_target"], floor))

    return {
        # BOTH triggers are numerical DEGENERACY checks. Clearing them is not a finding that
        # the sample is adequate, and 2 events is not "enough events" — adequacy is read off
        # the CI and MDE, which the report carries in every case.
        "insufficient": bool(reasons),
        "degeneracy_only": True,
        "power_trigger_active": power_active,
        "power_floor": floor,
        "reasons": reasons,
        "diagnostics": {"n_nonzero_cr_days": n_events,
                        "within_fund_date_exposure_sd": sd_x,
                        "exposure_sd_raw": sd_raw, "exposure_rank_ratio": rank_ratio,
                        "se_a1": se, "sd_outcome": sd_y, "mde_sigma": mde_sigma,
                        "power_target": rules["power_target"],
                        "rows_per_event": census.get("rows_per_event")},
    }


def _report(result, census, ident, config, outcome_choice, timestamp_audit, alpha,
            t, p_one_sided):
    """The G8 report line, IDENTICAL for all three outcomes (audit item 3).

    INSUFFICIENT_IDENTIFYING_VARIATION is an evidentiary CLASSIFICATION, not a replacement
    for inference: the coefficient, its interval, the MDE, the event counts, the
    concentration and the effective cluster counts are reported whichever branch is taken.
    A reader must be able to see how sparse the design was AND what it estimated.
    """
    from math import sqrt
    level = float(config["network_exposure"].get("first_stage_ci_level", 0.90))
    z = _z_one_sided((1.0 - level) / 2.0)            # two-sided reporting interval
    se = result.get("se_a1")
    a1 = result["a1"]
    return {
        "a1": a1, "se_a1": se, "t_a1": t, "p_one_sided": p_one_sided,
        "ci_level": level,
        "ci_low": (a1 - z * se) if se else None,
        "ci_high": (a1 + z * se) if se else None,
        "mde_sigma": ident["diagnostics"]["mde_sigma"],
        "power_target": ident["diagnostics"]["power_target"],
        "power_trigger_active": ident["power_trigger_active"],
        "alpha": alpha,
        "n_obs": result.get("n"),
        "sd_outcome": result.get("sd_outcome"),
        "n_nonzero_cr_days": census["n_nonzero_cr_days"],
        "share_of_fund_days_nonzero": census.get("share_of_fund_days_nonzero"),
        "concentration_top1_share": census.get("concentration_top1_share"),
        "concentration_top5_share": census.get("concentration_top5_share"),
        "n_effective_fund_clusters": census.get("n_effective_fund_clusters"),
        "n_effective_adviser_clusters": census.get("n_effective_adviser_clusters"),
        "n_effective_event_clusters": census.get("n_effective_event_clusters"),
        "timing": census.get("timing"),
        "n_funds_with_any_cr": census["n_funds_with_any_cr"],
        "within_fund_date_exposure_sd": result.get("within_fund_date_exposure_sd"),
        "registered_outcome": outcome_choice["chosen"],
        "outcome_arm": outcome_choice["arm"],
        "exposure": result["exposure"],
        "estimand": result.get("estimand", "baseline"),
        "event_language": timestamp_audit["g8_event_language"],
        "within_day_ordering_identified": timestamp_audit["within_day_ordering_identified"],
        # A DATED event is day-localized only. Both the share change and the constituent
        # order imbalance are measured over the same day and either could precede the other,
        # so the same-day result is mechanism association and calibration — not a causal
        # sequence — unless true AP transaction timestamps exist.
        "dated_means": config["network_exposure"]["cr_event_timing"]["dated_means"],
        "same_day_status": config["network_exposure"]["cr_event_timing"]["same_day_g8_status"],
        "within_day_ordering_requires": config["network_exposure"]["cr_event_timing"][
            "within_day_ordering_requires"],
    }


def _z_one_sided(p: float) -> float:
    """Upper-tail normal quantile. Bisection rather than a SciPy dependency — this runs on
    the box's stdlib-only venv, same constraint as scan.py."""
    from math import erf, sqrt
    lo, hi = -10.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2.0
        if 0.5 * (1 - erf(mid / sqrt(2))) > p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0
