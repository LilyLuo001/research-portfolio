#!/usr/bin/env python3
"""G8 preflight — the three things that must be settled BEFORE any treatment coefficient.

Freezes 1, 2 and 4 of 2026-08-28. None of this looks at an outcome-on-exposure coefficient;
all of it is data description and registration. `g8_first_stage.verdict()` refuses to license
the measure unless each piece is present, so the ordering is enforced by code rather than by
discipline.

  freeze 1  choose_primary_outcome()  — one exact outcome, by a rule keyed ONLY on G7 data
                                        quality, resolved before estimation
  freeze 2  audit_cr_timestamp()      — what the vendor actually supplies, and therefore
                                        which claim G8 is allowed to make
  freeze 4  cr_event_census()         — how many CR EVENTS carry the mechanism

Vendor-free: every input arrives as an injected frame or an explicit audit record.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_P1 = Path(__file__).resolve().parents[2] / "p1" / "t2_wrds"
if str(_P1) not in sys.path:
    sys.path.insert(0, str(_P1))
import corpactions as ca                                          # noqa: E402


# Machine-scale tolerance for "this series has no dispersion". Not an economic threshold:
# identical values leave floating-point dust rather than an exact zero SD.
SD_DEGENERATE_TOL = 1e-12


class SafeguardViolation(Exception):
    """Raised when a design the safeguards forbid is attempted."""


# --------------------------------------------------------------------------- freeze 1
def choose_primary_outcome(g7_quality: dict, config: dict) -> dict:
    """Resolve the registered primary G8 outcome from G7's DATA-QUALITY report.

    `g7_quality` carries measured coverage/agreement facts and nothing about treatment:

        signed_trade_classification_available_share : float
        intraday_coverage_share_of_volume_sample    : float
        cross_algorithm_daily_oib_sign_agreement    : float

    The rule is all-or-nothing on purpose. A partial pass would leave room to argue after the
    fact about which criterion mattered, which is the thing pre-specification exists to stop.
    """
    ne = config["network_exposure"]
    rule = ne["first_stage_outcome_choice_rule"]
    cands = ne["first_stage_primary_candidates"]
    req = dict(rule["use_preferred_iff_all"])

    if ne.get("first_stage_primary_outcome") is not None:
        raise SafeguardViolation(
            "first_stage_primary_outcome is already set to %r — the choice is made once, from "
            "the recorded decision, and is not re-derived later."
            % (ne["first_stage_primary_outcome"],))

    checks, failures = {}, []
    pairs = [
        ("signed_trade_classification_available_share",
         "signed_trade_classification_available_share_min"),
        ("intraday_coverage_share_of_volume_sample",
         "intraday_coverage_share_of_volume_sample_min"),
        ("cross_algorithm_daily_oib_sign_agreement",
         "cross_algorithm_daily_oib_sign_agreement_min"),
    ]
    for fact, key in pairs:
        floor = req[key]
        if fact not in g7_quality or g7_quality[fact] is None:
            # meta-rule 4: an absent measurement is not a pass and not a fail-by-default
            raise SafeguardViolation(
                "NEED_HUMAN: G7 quality report is missing %s — the outcome choice cannot be "
                "resolved, and it may not be resolved later with G8 coefficients in hand." % fact)
        got = float(g7_quality[fact])
        checks[fact] = {"value": got, "floor": floor, "pass": got >= floor}
        if got < floor:
            failures.append("%s = %.4f < %.4f" % (fact, got, floor))

    audited = bool(config["network_exposure"].get("cr_timestamp_audit_complete"))
    checks["cr_timestamp_audit_complete"] = {"value": audited, "floor": True, "pass": audited}
    if not audited:
        failures.append("cr_timestamp_audit_complete is False (freeze 2 not done)")

    chosen = cands["preferred"] if not failures else cands["fallback"]
    return {
        "chosen": chosen["name"],
        "arm": "preferred" if not failures else "fallback",
        "outcome_expression": chosen["outcome_expression"],
        "exposure": chosen["exposure"],
        "sided": chosen["sided"],
        "outcome_class": ne["first_stage_primary_outcome_class"],
        "checks": checks,
        "failures": failures,
        "decision_record": rule["decision_record"],
        "basis": "G7 data quality only; no G8 treatment coefficient was computed",
    }


def predetermined_adv(daily: pd.DataFrame, effective_dates: dict, config: dict) -> pd.DataFrame:
    """The frozen liquidity denominator (freeze 5): median PRE-conversion dollar volume.

    `daily`: permno | date | dollar_volume, with FOMC dates already flagged or absent.
    `effective_dates`: permno-or-fund -> conversion effective date. The window is taken
    relative to the conversion, in TRADING days, and it stops 22 trading days before it, so
    the run-up into the switch cannot enter the denominator.

    Predetermined is the whole point. A contemporaneous or trailing-window ADV is moved by
    the very trading being measured — a large AP day inflates its own denominator and shrinks
    its own outcome, biasing a1 toward zero — and any post-conversion window is post-treatment
    besides. Stocks with too few nonzero pre-conversion days are DROPPED, not floored: a
    floored denominator invents an outcome for a stock whose liquidity was never observed.
    """
    n = config["network_exposure"]["first_stage_outcome_normalization"]
    lo, hi = n["adv_window_trading_days"]
    stat, min_days = n["adv_statistic"], int(n["adv_min_nonzero_days"])
    rows = []
    for permno, g in daily.groupby("permno"):
        eff = effective_dates.get(permno)
        if eff is None:
            continue
        g = g.sort_values("date")
        g = g[pd.to_datetime(g["date"]) < pd.Timestamp(eff)]
        if "is_fomc" in g.columns:
            g = g[~g["is_fomc"].astype(bool)]
        # trading-day offsets counted back from the conversion
        g = g.iloc[max(0, len(g) + lo):len(g) + hi] if len(g) + hi > 0 else g.iloc[0:0]
        vol = g["dollar_volume"].astype(float)
        nz = vol[vol > 0]
        rows.append({
            "permno": permno,
            "adv_dollar_pre": float(getattr(nz, stat)()) if len(nz) else np.nan,
            "n_nonzero_pre_days": int(len(nz)),
            "usable": bool(len(nz) >= min_days),
        })
    return pd.DataFrame(rows)


def _winsorize_within_date(frame: pd.DataFrame, col: str, pct) -> np.ndarray:
    lo, hi = float(pct[0]) / 100.0, float(pct[1]) / 100.0
    out = frame[col].astype(float).copy()
    for _, idx in frame.groupby("date").groups.items():
        v = out.loc[idx]
        out.loc[idx] = v.clip(v.quantile(lo), v.quantile(hi))
    return out.to_numpy(float)


def aligned_outcome(frame: pd.DataFrame, arm: str, config: dict = None) -> np.ndarray:
    """Build the registered primary outcome, in its registered UNIT (freeze 5).

    preferred: sign(CR) * (signed DOLLAR imbalance / predetermined ADV$) — the flow's sign
               enters through the OUTCOME, so a positive value means constituent order flow
               moved WITH the creation/redemption.
    fallback:  (dollar volume - ADV$) / ADV$, unsigned.

    Both are scaled by the same predetermined denominator, so neither carries size units. A
    RAW dollar imbalance would scale with the stock's size, and |L_tilt^pre| is not
    independent of size — large index-heavy names sit closer to their basket's beta — so a
    raw outcome could deliver a1 > 0 out of the size distribution with no arbitrage channel
    in it at all.

    `config=None` returns the UNNORMALIZED construction, and is for unit-testing the sign
    algebra only; verdict() will not license a result built that way.
    """
    if arm not in ("preferred", "fallback"):
        raise SafeguardViolation("unknown outcome arm %r" % (arm,))
    if config is None:
        return (np.sign(frame["CR"].to_numpy(float)) * frame["OIB"].to_numpy(float)
                if arm == "preferred" else frame["abn_vol"].to_numpy(float))
    sign_cr = np.sign(cr_raw(frame, config)) if arm == "preferred" else None

    n = config["network_exposure"]["first_stage_outcome_normalization"]
    if "adv_dollar_pre" not in frame.columns:
        raise SafeguardViolation(
            "the registered outcome is scaled by predetermined ADV$ (freeze 5); the frame "
            "carries no 'adv_dollar_pre'. Raw dollar flow scales with stock size, and size "
            "is not independent of |L_tilt^pre|.")
    adv = frame["adv_dollar_pre"].astype(float)
    if (adv <= 0).any() or adv.isna().any():
        raise SafeguardViolation(
            "non-positive or missing ADV$ denominators present — drop those stocks "
            "(adv_min_nonzero_days), never floor them.")
    if arm == "preferred":
        # sign from CR_raw (audit item 1): the scaled column's sign is not economic
        raw = sign_cr * (frame["signed_dollar_imbalance"].astype(float) / adv)
    else:
        raw = (frame["dollar_volume"].astype(float) - adv) / adv
    work = frame.assign(_y=raw.to_numpy(float))
    return _winsorize_within_date(work, "_y", n["winsorize_outcome_pct"])


def build_cr(shares: pd.DataFrame, config: dict, convention: dict = None) -> pd.DataFrame:
    """CR, built from the ONE registered formula (reconciliation audit 2026-08-28).

        CR_{f,t} = (S_{f,t} - S_{f,t-1}) / S_{f,t-1}

    `shares`: fund | date | shares_outstanding [| cfacshr]. S is the ETF's own shares
    outstanding, corporate-action adjusted; NO price and NO NAV enters the numerator. The
    denominator is the PRIOR TRADING DAY's count for that fund — a gap leaves CR undefined
    rather than spanning it, because a two-day difference divided by a one-day base is a
    different variable that happens to have the same name.

    Positive is a creation (inflow). The sign is preserved here; |CR| is taken later, in the
    exposure, and never at this step.

    Then winsorized within fund and standardized within fund, per §6.1.2 — which is why the
    result must not be rescaled again. An earlier draft divided a DOLLAR creation by lagged
    TNA; that is a different variable (it carries the fund's own NAV return) and is refused
    by assert_cr_definition().
    """
    d = config["network_exposure"]["cr_definition"]
    need = {"fund", "date", "shares_outstanding"}
    if not need <= set(shares.columns):
        raise SafeguardViolation("shares frame missing %s" % sorted(need - set(shares.columns)))

    df = shares.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["fund", "date"])

    if d["shares_corporate_action_adjusted"]:
        if "cfacshr" not in df.columns:
            raise SafeguardViolation(
                "CR needs corporate-action ADJUSTED shares outstanding: a split changes S "
                "with no creation, and would read as a huge creation. Supply 'cfacshr' and a "
                "VERIFIED convention (p1/t2_wrds/corpactions.py).")
        df["_S"] = ca.adjusted_shares(df["shares_outstanding"].astype(float),
                                      df["cfacshr"].astype(float), convention)
    else:
        df["_S"] = df["shares_outstanding"].astype(float)

    g = df.groupby("fund", sort=False)
    prev_S = g["_S"].shift(1)
    prev_date = g["date"].shift(1)
    # "previous TRADING day for that fund": the trading calendar is the fund's own observed
    # sequence, so a missing row is a gap and the row is dropped, never spanned or filled.
    df["_gap"] = prev_date.isna() | (g.cumcount() == 0)
    df["CR_raw"] = (df["_S"] - prev_S) / prev_S
    df.loc[df["_gap"], "CR_raw"] = np.nan
    if (prev_S <= 0).any():
        raise SafeguardViolation("non-positive prior shares outstanding in the CR denominator")

    # ---- the exposure magnitude ----------------------------------------------------
    # PRIMARY: |CR_raw|, and nothing else. No centring, no within-fund SD scaling, no
    # winsorization. Every invariant then holds by construction rather than by guard, and —
    # the reason this is the primary — no fund-specific tuning can distort a sparse event
    # series it never touches. A within-fund 99th percentile on a series that is 99% zeros
    # IS ZERO, which clipped both genuine events of a 2-event fund to zero exposure.
    if not d.get("magnitude_first", True):
        raise SafeguardViolation("magnitude_first is registered true; the signed series may "
                                 "not be winsorized (winsorize_signed_series_forbidden)")
    prim = d["primary_exposure_transform"]
    for key in ("centering", "scaling", "winsorization"):
        if prim.get(key) != "none":
            raise SafeguardViolation(
                "the PRIMARY exposure carries no %s (%r registered). Fund-specific tuning is "
                "robustness, never the primary — it is what destroyed sparse funds."
                % (key, prim.get(key)))
    if prim.get("transform") != "identity":
        raise SafeguardViolation("primary exposure transform must be identity, got %r"
                                 % prim.get("transform"))
    if d.get("standardize_within_fund"):
        raise SafeguardViolation(
            "within-fund SD scaling is withdrawn from both specifications. Zero within-fund "
            "CR dispersion does not mean a1 is unidentified: under fund x date fixed effects "
            "it is identified by CR x |L| varying ACROSS CONSTITUENTS in an event fund-day.")

    df["CR_mag_raw"] = df["CR_raw"].abs()
    df["CR_mag"] = df["CR_mag_raw"]                 # the primary IS the raw magnitude

    # ROBUSTNESS column, built alongside and never substituted for the primary.
    df["CR_mag_capped"] = capped_magnitude(df, config)

    out = df.drop(columns=["_S", "_gap"])
    assert_cr_invariants(out, config)
    return out


def capped_magnitude(df: pd.DataFrame, config: dict) -> pd.Series:
    """The robustness variant: an upper-tail cap that cannot annihilate a sparse fund.

    Three guardrails, each answering a way the naive version failed:

      * the cap is estimated on NONZERO EVENT MAGNITUDES ONLY. A percentile of the
        zero-padded full series is dominated by the zeros — for a fund with 2 events in 250
        days the 99th percentile is 0, and clipping to it deletes both events.
      * a fund needs `min_nonzero_events_for_fund_specific_cap` events before it gets its
        OWN cap; below that the pooled cross-fund cap is used, because a percentile of three
        numbers is noise wearing a threshold's clothes.
      * the cap is floored at the smallest nonzero magnitude, so clipping can never drive a
        genuine event to zero. Asserted afterwards rather than assumed.
    """
    r = config["network_exposure"]["cr_definition"]["robustness_exposure_transform"]
    if r["clip"] != "upper_tail_only":
        raise SafeguardViolation(
            "robustness clipping must be UPPER TAIL ONLY (%r registered): on a non-negative "
            "series a lower clip can only lift genuine zeros off zero." % r["clip"])
    q = float(r["clip_pct"]) / 100.0
    min_events = int(r["min_nonzero_events_for_fund_specific_cap"])

    mag = df["CR_mag_raw"].astype(float)
    nonzero_all = mag[mag > 0]
    pooled_cap = float(nonzero_all.quantile(q)) if len(nonzero_all) else np.inf

    out = mag.copy()
    for fund, idx in df.groupby("fund").groups.items():
        v = mag.loc[idx]
        nz = v[v > 0]
        if len(nz) >= min_events:
            cap = float(nz.quantile(q))
        elif r["pooled_cap_fallback"]:
            cap = pooled_cap
        else:
            cap = np.inf                    # too few events and no fallback: do not clip
        # Never let a cap zero a genuine event. Upper clipping can only do that if the cap
        # itself is zero (or negative), so the guard fires THERE and nowhere else — an
        # unconditional floor at the fund's smallest event would lift the cap above a
        # single-event fund's only observation and stop the clip biting at all.
        if len(nz) and not (cap > 0):
            cap = float(nz.min())
        out.loc[idx] = v.clip(upper=cap)
    return out


def assert_cr_invariants(frame: pd.DataFrame, config: dict, tol: float = 1e-12) -> None:
    """The four properties the transformation must have, checked on every build.

    They are asserted rather than assumed because each one failed at least once during
    development: the zero-preservation invariant is exactly what the winsorize-then-abs
    order broke, silently, while every sign-level test still passed.
    """
    d = config["network_exposure"]["cr_definition"]
    raw = frame[d["raw_column"]].to_numpy(float)
    mag = frame[d["analysis_column"]].to_numpy(float)
    live = ~np.isnan(raw)
    r, m = raw[live], mag[live]

    if (m < -tol).any():
        raise SafeguardViolation("CR_mag must be non-negative")
    bad_zero = (np.abs(r) <= tol) & (np.abs(m) > tol)
    if bad_zero.any():
        raise SafeguardViolation(
            "%d zero-event day(s) acquired a non-zero exposure magnitude — CR_raw == 0 must "
            "imply CR_mag == 0, or a non-event is weighted like a real creation."
            % int(bad_zero.sum()))
    bad_nonzero = (np.abs(r) > tol) & (np.abs(m) <= tol)
    if bad_nonzero.any():
        raise SafeguardViolation(
            "%d real creation/redemption(s) were driven to zero magnitude"
            % int(bad_nonzero.sum()))
    # the primary is the identity, so it also has to BE the identity
    if not np.allclose(m, np.abs(r), equal_nan=True):
        raise SafeguardViolation("the primary exposure must equal |CR_raw| exactly")
    # and the robustness column must obey the same two invariants
    rob = config["network_exposure"]["cr_definition"]["robustness_exposure_transform"]
    col = rob["column"]
    if col in frame.columns:
        c = frame[col].to_numpy(float)[live]
        if (c < -tol).any():
            raise SafeguardViolation("%s must be non-negative" % col)
        if rob["preserve_zero_exactly"] and ((np.abs(r) <= tol) & (np.abs(c) > tol)).any():
            raise SafeguardViolation("%s gave a zero-event day non-zero exposure" % col)
        if rob["never_zero_a_genuine_event"] and ((np.abs(r) > tol) & (np.abs(c) <= tol)).any():
            raise SafeguardViolation(
                "%s clipped %d genuine creation/redemption event(s) to zero — a sparse-event "
                "percentile must never do that" % (col, int(((np.abs(r) > tol) & (np.abs(c) <= tol)).sum())))


def cr_raw(frame: pd.DataFrame, config: dict) -> np.ndarray:
    """The economic CR: unwinsorized, unscaled. Everything about SIGN and EVENT STATUS reads
    this column, never the analysis column.

    SD-only standardization preserves zero and sign; WINSORIZATION DOES NOT. In a fund that
    creates on almost every day the 1st percentile is positive, so clipping pushes a genuine
    redemption and a genuine zero-event day to a positive number — a non-event recorded as a
    large creation, and a redemption recorded as a creation.
    """
    col = config["network_exposure"]["cr_definition"]["raw_column"]
    if col not in frame.columns:
        raise SafeguardViolation(
            "%r is required for anything sign- or event-valued (audit item 1). The scaled "
            "column is winsorized, and winsorizing a mostly-creating fund flips the sign of "
            "its redemptions and destroys its zero-event days." % col)
    return frame[col].to_numpy(float)


def assert_cr_definition(frame: pd.DataFrame, config: dict) -> None:
    """Refuse a frame carrying a CR built to any other definition.

    The columns named here are the fingerprints of the deleted TNA/dollar forms. Their
    presence beside a CR column means two definitions are live at once, which is the state
    this audit exists to end."""
    d = config["network_exposure"]["cr_definition"]
    if not d["further_rescaling_forbidden"]:
        return
    fingerprints = {"tna_lag", "tna", "cr_dollar", "cr_usd", "dollar_cr", "nav", "nav_lag"}
    hits = sorted(fingerprints & set(map(str, frame.columns)))
    if hits and "CR" in frame.columns:
        raise SafeguardViolation(
            "columns %s sit beside CR. The registered CR is %s — a share-growth rate that "
            "carries no price or NAV. A dollar/TNA-scaled CR differs from it by the fund's "
            "own NAV return and is a different variable. Forbidden forms: %s."
            % (hits, d["formula"], d["dollar_or_tna_scaled_forms_forbidden"]))


# --------------------------------------------------------------------------- freeze 2
def audit_cr_timestamp(record: dict, config: dict) -> dict:
    """What the vendor supplies, and therefore what G8 may claim.

    `record` is a hand-filled audit of the actual data dictionary:

        vendor                        : str        e.g. "CRSP daily ETF shares outstanding"
        field                         : str        the exact column
        intraday_timestamp_supplied   : bool       does the VENDOR give an event time?
        as_of_convention              : str        e.g. "end of day t, effective t"
        corporate_action_adjusted     : bool

    Daily Delta(SharesOut) is a *difference of two end-of-day stocks*. It says a creation
    happened somewhere inside the day; it does not say when, and nothing about the AP's
    within-day sequencing can be recovered from it. Inferring a time from it is forbidden.
    """
    ne = config["network_exposure"]
    for k in ("vendor", "field", "intraday_timestamp_supplied", "as_of_convention"):
        if record.get(k) is None:
            raise SafeguardViolation(
                "NEED_HUMAN: shares-outstanding audit is missing %r. The timestamp convention "
                "is a fact about the vendor's data dictionary, not something to assume." % k)
    if record.get("inferred_from_daily_differences"):
        raise SafeguardViolation(
            "an intraday CR timestamp INFERRED from daily share differences is not a "
            "timestamp — daily Delta(SharesOut) cannot identify a within-day event time.")

    intraday = bool(record["intraday_timestamp_supplied"])
    resolution = "intraday" if intraday else "daily"
    lang = ne["g8_event_language"][resolution]
    return {
        "vendor": record["vendor"],
        "field": record["field"],
        "resolution": resolution,
        "as_of_convention": record["as_of_convention"],
        "corporate_action_adjusted": bool(record.get("corporate_action_adjusted", False)),
        "audit_complete": True,
        "g8_event_language": lang,
        "within_day_ordering_identified": intraday,
        "note": (ne["cr_daily_timing_implication"] if not intraday else
                 "vendor-supplied event times permit a within-day window; the window itself "
                 "must still be registered before outcomes are opened"),
    }


def event_language(audit: dict | None, config: dict) -> str:
    """The phrase every G8 table, figure and sentence must use. Unaudited defaults to the
    weaker daily claim — never to the stronger one."""
    ne = config["network_exposure"]
    if audit is None or not audit.get("audit_complete"):
        return ne["g8_event_language"][ne["g8_event_language"]["default_when_unaudited"]]
    return audit["g8_event_language"]


# --------------------------------------------------------------------------- freeze 4
def cr_event_census(panel: pd.DataFrame, config: dict, zero_tol: float = 0.0) -> dict:
    """How many creation/redemption EVENTS carry the mechanism, and how concentrated they are.

    Effective mechanism variation is CR events, not constituent-day rows: a panel of a million
    constituent-days built off twelve nonzero-CR fund-days has twelve events in it. This is a
    reporting requirement with no threshold attached — a minimum chosen now, with the data in
    hand, would be exactly the specification search the plan forbids.

    panel: fund | date | CR [| wave | adviser | permno]
    """
    d = config["network_exposure"]["cr_definition"]
    col = d["raw_column"] if d.get("census_uses_raw_pre_winsorized", True) else "CR"
    if col not in panel.columns:
        raise SafeguardViolation(
            "the CR event census must be computed on %r (audit item 1). Winsorized CR turns "
            "zero-event days in a mostly-creating fund into nonzero values, so the count of "
            "creation/redemption EVENTS — and every concentration statistic built on it — "
            "would be wrong in the direction that flatters the design." % col)
    fd = (panel[[c for c in ("fund", "date", "wave", "adviser", col) if c in panel.columns]]
          .rename(columns={col: "CR"})
          .drop_duplicates(subset=["fund", "date"]).copy())
    fd["nonzero"] = fd["CR"].astype(float).abs() > zero_tol
    nz = fd[fd["nonzero"]]

    def _by(key):
        if key not in fd.columns:
            return None
        g = fd.groupby(key)
        out = pd.DataFrame({
            "n_fund_days": g.size(),
            "n_nonzero_cr_days": fd[fd["nonzero"]].groupby(key).size().reindex(g.size().index).fillna(0),
        })
        out["share_of_fund_days_nonzero"] = out["n_nonzero_cr_days"] / out["n_fund_days"]
        out["median_abs_cr_on_nonzero_days"] = (
            nz.assign(a=nz["CR"].abs()).groupby(key)["a"].median().reindex(out.index))
        return out.reset_index()

    n_nz = int(len(nz))
    per_fund = nz.groupby("fund").size().sort_values(ascending=False) if n_nz else pd.Series(dtype=int)
    # EFFECTIVE clusters: only units that actually carry a nonzero CR contribute to a1, so a
    # fund sitting in the panel with no creation all year is not an identifying cluster and
    # must not be counted as one when the inference is written up.
    eff = {"n_effective_fund_clusters": int(nz["fund"].nunique()) if n_nz else 0,
           "n_effective_event_clusters": n_nz,
           "n_effective_adviser_clusters": (int(nz["adviser"].nunique())
                                            if n_nz and "adviser" in nz.columns else None)}
    return {
        "n_fund_days": int(len(fd)),
        "n_constituent_day_rows": int(len(panel)),
        "n_nonzero_cr_days": n_nz,
        "share_of_fund_days_nonzero": (n_nz / len(fd)) if len(fd) else np.nan,
        "n_funds_with_any_cr": int(nz["fund"].nunique()) if n_nz else 0,
        "concentration_top1_share": float(per_fund.iloc[:1].sum() / n_nz) if n_nz else np.nan,
        "concentration_top5_share": float(per_fund.iloc[:5].sum() / n_nz) if n_nz else np.nan,
        "median_abs_cr_on_nonzero_days": float(nz["CR"].abs().median()) if n_nz else np.nan,
        "by_fund": _by("fund"),
        "by_wave": _by("wave"),
        "by_adviser": _by("adviser"),
        "rows_per_event": (len(panel) / n_nz) if n_nz else np.nan,
        "reporting_only": "no minimum is registered; the census is reported, not passed",
        "computed_on": col,
        "timing": (timing_census(panel, config) if "cr_timing" in panel.columns else None),
        **eff,
    }


def shares_update_audit(shares: pd.DataFrame, record: dict, config: dict) -> dict:
    """How often does the vendor actually REFRESH shares outstanding? (audit item 4)

    Distinct from the timestamp question. If a stale value is carried forward for three days
    and then catches up, differencing reads three zero-event days followed by one large
    creation — a precisely dated event that did not happen on that date, and the false
    precision lands exactly where the design is most sensitive.

    Staleness leaves a fingerprint in the series: runs of identical S followed by a jump. So
    it is MEASURED here rather than taken on trust, and the vendor's stated frequency is
    checked against what the data does.

    `record` must state the vendor's documented refresh frequency; `shares` is
    fund | date | shares_outstanding.
    """
    stated = record.get("update_frequency")
    if stated is None:
        raise SafeguardViolation(
            "NEED_HUMAN: the vendor's documented shares-outstanding refresh frequency is "
            "missing. It is a fact about the data dictionary, and a delayed update read as a "
            "dated creation is not recoverable after the fact.")
    df = shares.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["fund", "date"])
    per_fund, runs_all = [], []
    for fund, g in df.groupby("fund"):
        v = g["shares_outstanding"].astype(float).to_numpy()
        if len(v) < 2:
            continue
        same = v[1:] == v[:-1]
        # lengths of consecutive-identical runs, in days held constant
        runs, cur = [], 0
        for flag in list(same) + [False]:
            if flag:
                cur += 1
            elif cur:
                runs.append(cur + 1)
                cur = 0
        changed = int((~same).sum())
        per_fund.append({"fund": fund, "n_days": int(len(v)),
                         "share_of_days_unchanged": float(same.mean()),
                         "longest_unchanged_run": int(max(runs)) if runs else 1,
                         "n_changes": changed})
        runs_all.extend(runs)

    tab = pd.DataFrame(per_fund)
    longest = int(max(runs_all)) if runs_all else 1
    median_unchanged = float(tab["share_of_days_unchanged"].median()) if len(tab) else np.nan
    # A DIAGNOSTIC, and only that (corrected 2026-08-28). A genuinely daily series is
    # CONSTANT on every day without a creation or redemption, which for most funds is most
    # days — so long identical runs are equally consistent with a quiet fund and with a
    # stale feed, and this function cannot tell them apart. It flags a pattern worth a
    # human's attention; it never establishes carry-forward, and the timing classification
    # does not consult it. Freshness comes from per-observation vendor evidence
    # (observation_freshness), which is a different kind of fact.
    run_flag = bool(longest >= 3 and median_unchanged > 0.5)
    return {
        "stated_update_frequency": stated,
        "by_fund": tab,
        "median_share_of_days_unchanged": median_unchanged,
        "longest_unchanged_run_days": longest,
        "run_diagnostic_suggests_review": run_flag,
        "is_proof_of_carryforward": False,          # never, by construction
        "diagnostic_only": True,
        "freshness_must_come_from": "per-observation vendor as-of / refresh evidence",
        "implication": (
            "long identical runs — consistent with a quiet fund OR a stale feed. This does "
            "not classify anything; check the vendor's as-of/refresh field per observation"
            if run_flag else
            "no long identical runs; still no evidence either way about per-observation "
            "freshness, which is what the timing rule reads"),
        "needs_human_review": run_flag or stated != "daily",
    }


# --------------------------------------------------------------------------- timing rule
PUBLICATION_ONLY_COLUMNS = ("refresh_flag", "file_updated_at", "file_last_modified",
                            "api_response_timestamp", "published_at", "row_republished",
                            "ingested_at", "is_fresh")


def observation_freshness(shares: pd.DataFrame, config: dict,
                          freshness_record: dict = None) -> dict:
    """Is each observation's ECONOMIC as-of date the day it sits on?

    THE DISTINCTION (correction 2026-08-28). A feed can restamp, republish or re-serve a row
    every day while the SharesOut figure it carries still refers to an earlier economic as-of
    date. A publication or refresh timestamp certifies that the PIPELINE ran; it says nothing
    about when the shares were counted. Columns in PUBLICATION_ONLY_COLUMNS are therefore
    never sufficient, and their presence alone yields no fresh observations.

    Freshness requires BOTH:
      * a per-observation ECONOMIC as-of date (`shares_as_of`) equal to the observation
        date, and
      * `freshness_record` attesting a DOCUMENTED DAILY ECONOMIC CUTOFF for this field —
        what "as of day t" means for it. Without that, an as-of date equal to the row's date
        cannot be read as a same-day economic measurement.

    Returns {"fresh": bool array, "evidence": str, "reason": str}. Absent either
    requirement the array is all-False: conservative by construction, because absent
    evidence is not evidence of freshness.
    """
    fe = config["network_exposure"]["cr_event_timing"]["freshness_evidence"]
    n = len(shares)
    none = np.zeros(n, dtype=bool)
    pub_only = [c for c in PUBLICATION_ONLY_COLUMNS if c in shares.columns]

    if "shares_as_of" not in shares.columns:
        return {"fresh": none, "evidence": "none",
                "reason": ("no per-observation economic as-of date"
                           + (" — %s record(s) the pipeline, not the measurement" % pub_only
                              if pub_only else ""))}
    if fe.get("economic_cutoff_must_be_documented"):
        rec = freshness_record or {}
        if not rec.get("economic_cutoff_documented"):
            return {"fresh": none, "evidence": "as_of_without_documented_cutoff",
                    "reason": ("NEED_HUMAN: a documented daily economic cutoff for this field "
                               "is required (%s). An as-of date equal to the row's date "
                               "cannot be read as a same-day economic measurement without "
                               "one." % fe["also_required"])}
        if rec.get("economic_cutoff_cadence") not in (None, "daily"):
            return {"fresh": none, "evidence": "non_daily_economic_cutoff",
                    "reason": "the documented economic cutoff is %r, not daily"
                              % rec.get("economic_cutoff_cadence")}

    as_of = pd.to_datetime(shares["shares_as_of"], errors="coerce")
    obs = pd.to_datetime(shares["date"], errors="coerce")
    fresh = (as_of.notna() & (as_of.dt.normalize() == obs.dt.normalize())).to_numpy()
    return {"fresh": fresh, "evidence": "economic_as_of_with_documented_daily_cutoff",
            "reason": "", "publication_only_columns_ignored": pub_only}


def interval_alignment(freshness_record: dict, config: dict) -> dict:
    """Do the CR and OIB measurement intervals actually coincide? (final check, 2026-08-28)

    A documented daily economic cutoff fixes the as-of DATE. It does not align the two
    measurement windows, and calendar equality is not alignment. CR differences two cutoff
    snapshots, so it spans (cutoff at t-1, cutoff at t]; OIB spans a trading session. Those
    are the same window only when the cutoff IS the market close.

    `freshness_record` should carry `cutoff_time` — either the literal "market_close" or a
    documented clock time — and optionally `cutoff_is_market_close`.

    Returns the alignment class, the OIB window the primary must be built over, and whether
    the primary may use these events at all. An unknown cutoff time yields
    `unaligned_unknown_cutoff`: knowing the as-of DATE licenses day localization, not a claim
    of exact same-day interval alignment.
    """
    al = config["network_exposure"]["cr_event_timing"]["cr_oib_interval_alignment"]
    rec = freshness_record or {}
    cutoff = rec.get("cutoff_time")
    is_close = rec.get("cutoff_is_market_close")
    if is_close is None:
        is_close = (str(cutoff).strip().lower() in ("market_close", "market close", "close"))

    if cutoff and is_close:
        cls = "aligned_trading_day"
    elif cutoff:
        cls = "aligned_cutoff_to_cutoff"
    else:
        cls = "unaligned_unknown_cutoff"

    spec = al["classes"][cls]
    return {
        "alignment_class": cls,
        "cutoff_time": cutoff,
        "oib_window": spec["oib_window"],
        "primary_eligible": bool(spec["primary_eligible"]),
        "oib_must_be_constructed_over_that_window": bool(
            spec.get("oib_must_be_constructed_over_that_window")),
        "reason": ("" if spec["primary_eligible"] else
                   "NEED_HUMAN: the economic cutoff TIME is not documented. The as-of date "
                   "gives day localization; it does not license a claim of exact same-day "
                   "interval alignment between CR and OIB, so these events may not enter "
                   "the same-day primary (%s)." % spec["interpretation"]),
    }


def classify_cr_event_timing(shares: pd.DataFrame, audit: dict, config: dict,
                             freshness_record: dict = None) -> pd.DataFrame:
    """Label every CR change DATED or INTERVAL (corrected rule, 2026-08-28).

    THE CORRECTION. An earlier version treated "preceded by a run of unchanged shares" as
    proof of carry-forward. It is not: a genuinely daily series stays CONSTANT on every day
    without a creation or redemption, which for most funds is most days. "Same value" and
    "stale observation" are different claims, and the share series alone cannot separate
    them — which is precisely why freshness must come from the vendor.

    So DATED requires PER-OBSERVATION freshness evidence at BOTH endpoints of the change:
    the value at t was published for t, and the value at t-1 was published for t-1. Only then
    is the change localized to day t. If t-1 was carried forward, the change could have
    occurred any time since the last fresh observation, and the interval runs back to it.

    Under verified daily freshness a constant stretch is simply a run of genuine zero-CR
    days, and the change that ends it is still DATED.

    Runs of equal values are carried through as a DIAGNOSTIC (`equal_value_run_before`),
    reported but never used to classify.

    `shares`: fund | date | shares_outstanding, plus one freshness column (see
    observation_freshness). Returns fund | date | cr_timing | cr_interval_days |
    cr_interval_start | freshness_evidence | equal_value_run_before.
    """
    t = config["network_exposure"]["cr_event_timing"]
    if t.get("equal_value_run_is_sufficient_proof_of_carryforward"):
        raise SafeguardViolation(
            "a run of equal shares outstanding is a staleness DIAGNOSTIC, not proof of "
            "carry-forward: a daily series is constant whenever no creation or redemption "
            "occurs.")
    df = shares.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["fund", "date"]).reset_index(drop=True)
    fr = observation_freshness(df, config, freshness_record)
    fresh_all, kind, reason = fr["fresh"], fr["evidence"], fr["reason"]
    al = interval_alignment(freshness_record, config)

    rows = []
    for fund, g in df.groupby("fund", sort=False):
        idx = g.index.to_numpy()
        v = g["shares_outstanding"].astype(float).to_numpy()
        dates = g["date"].to_numpy()
        fresh = fresh_all[idx]
        last_fresh = None                   # position of the most recent fresh observation
        run = 0                             # equal-value run length: DIAGNOSTIC only
        for i in range(len(v)):
            changed = i > 0 and v[i] != v[i - 1]
            run = run + 1 if (i > 0 and not changed) else 0
            # Endpoint evidence is the SAME requirement for a zero day as for an event:
            # "no creation happened" is a claim, and an unchanged value under carry-forward
            # is an absence of measurement rather than an observed no-creation day.
            endpoints_measured = bool(fresh[i]) and last_fresh == i - 1
            timing, width, start = "zero_unverified", np.nan, pd.NaT
            if i == 0:
                timing = "zero_unverified"      # no prior endpoint exists
            elif changed:
                if endpoints_measured:
                    timing, width, start = "dated", 1.0, dates[i]
                else:
                    timing = "interval"
                    back = last_fresh if last_fresh is not None else 0
                    width = float(i - back) if last_fresh is not None else float(i + 1)
                    start = dates[back]
            else:
                timing = "zero_verified" if endpoints_measured else "zero_unverified"
            if fresh[i]:
                last_fresh = i
            rows.append({"fund": fund, "date": dates[i], "cr_timing": timing,
                         "cr_interval_days": width, "cr_interval_start": start,
                         "freshness_evidence": kind,
                         "freshness_reason": reason,
                         "alignment_class": al["alignment_class"],
                         "oib_window": al["oib_window"],
                         "primary_eligible": al["primary_eligible"],
                         "observation_is_fresh": bool(fresh[i]),
                         "equal_value_run_before": int(run)})
    return pd.DataFrame(rows)


def primary_timing_sample(panel: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Restrict the same-day aligned-OIB primary to DATED events (and non-event days).

    Interval events are removed from the primary rather than silently paired with the
    vendor's update day. They are not discarded from the paper: they carry their own
    interval-level outcome, registered under cr_event_timing.interval_robustness.
    """
    t = config["network_exposure"]["cr_event_timing"]
    if t["primary_sample"] != "dated_only":
        raise SafeguardViolation("primary_sample is registered dated_only, got %r"
                                 % t["primary_sample"])
    if "cr_timing" not in panel.columns:
        raise SafeguardViolation(
            "the same-day primary requires cr_timing (classify_cr_event_timing). An interval "
            "event paired with same-day order imbalance dates constituent trading to the "
            "vendor's update day, which is the one day in the interval guaranteed to carry a "
            "printed share change.")
    z = t["zero_cr_observations"]
    al = t["cr_oib_interval_alignment"]
    drop = panel["cr_timing"].eq("interval")

    # Unverified zeros: an unchanged SharesOut whose endpoints were not both freshly
    # measured is an absence of measurement, not an observed no-creation day. Letting it in
    # as a zero-exposure control dilutes the estimate with days nobody looked at.
    n_unverified_zeros = 0
    if z["unverified_zeros_in_primary"] == "excluded":
        unver = panel["cr_timing"].eq("zero_unverified")
        n_unverified_zeros = int(
            panel.loc[unver, ["fund", "date"]].drop_duplicates().shape[0])
        drop = drop | unver

    # Partial OIB coverage over a cutoff-to-cutoff window: a known cutoff does not make the
    # outcome aligned if the trading feed covers only part of the required interval. The
    # gap is systematic — feeds stop at the close — so the partial quantity is a different
    # variable, not a noisier version of the registered one.
    cov_col = al.get("oib_coverage_column", "oib_interval_coverage_complete")
    n_partial = 0
    needs_cov = (panel.get("alignment_class") is not None
                 and al["classes"]["aligned_cutoff_to_cutoff"].get(
                     "requires_complete_oib_coverage_over_interval"))
    if needs_cov:
        cutoff_rows = panel["alignment_class"].eq("aligned_cutoff_to_cutoff")
        if cutoff_rows.any():
            if cov_col not in panel.columns:
                raise SafeguardViolation(
                    "alignment class 'aligned_cutoff_to_cutoff' requires %r: OIB must cover "
                    "the WHOLE cutoff-to-cutoff interval. A known cutoff does not make a "
                    "partial-session imbalance aligned with a full-interval CR." % cov_col)
            partial = cutoff_rows & ~panel[cov_col].astype(bool)
            n_partial = int(panel.loc[partial, ["fund", "date"]].drop_duplicates().shape[0])
            drop = drop | partial

    n_misaligned = 0
    if "primary_eligible" in panel.columns:
        # Alignment is a SEPARATE condition from datedness: a day-localized event whose
        # cutoff time is unknown is still interval-misaligned, and the same-day primary may
        # not use it.
        misaligned = panel["cr_timing"].eq("dated") & ~panel["primary_eligible"].astype(bool)
        n_misaligned = int(panel.loc[misaligned, ["fund", "date"]].drop_duplicates().shape[0])
        drop = drop | misaligned
    out = panel[~drop].copy()
    out.attrs["n_interval_events_excluded"] = int(
        panel.loc[panel["cr_timing"].eq("interval"), ["fund", "date"]]
        .drop_duplicates().shape[0])
    out.attrs["n_misaligned_events_excluded"] = n_misaligned
    out.attrs["n_unverified_zeros_excluded"] = n_unverified_zeros
    out.attrs["n_partial_oib_coverage_excluded"] = n_partial
    return out


def timing_census(panel: pd.DataFrame, config: dict) -> dict:
    """Reported whichever way the counts fall — a rule that only surfaces when it bites is
    not a rule."""
    work = panel.copy()
    if "cr_interval_days" not in work.columns:
        work["cr_interval_days"] = np.nan     # a dated-only panel carries no widths
    if "primary_eligible" not in work.columns:
        work["primary_eligible"] = True       # no alignment column -> nothing to exclude
    work["_eligible"] = work["primary_eligible"].astype(bool)
    ev = work[work["cr_timing"].isin(("dated", "interval"))][
        ["fund", "date", "cr_timing", "cr_interval_days", "_eligible"]].drop_duplicates(
            subset=["fund", "date"])
    n_dated = int((ev["cr_timing"] == "dated").sum())
    n_int = int((ev["cr_timing"] == "interval").sum())
    total = n_dated + n_int
    t = config["network_exposure"]["cr_event_timing"]
    return {
        "n_dated_events": n_dated,
        "dated_means": t["dated_means"],
        "alignment_class": (panel["alignment_class"].iloc[0]
                            if "alignment_class" in panel.columns and len(panel) else None),
        "oib_window": (panel["oib_window"].iloc[0]
                       if "oib_window" in panel.columns and len(panel) else None),
        # counted on EVENTS (fund-days), never on constituent-day rows
        "n_zero_verified": int((work["cr_timing"] == "zero_verified").sum()),
        "n_zero_unverified": int((work["cr_timing"] == "zero_unverified").sum()),
        "n_partial_oib_coverage_events": int(
            (work["alignment_class"].eq("aligned_cutoff_to_cutoff")
             & ~work.get(t["cr_oib_interval_alignment"].get(
                 "oib_coverage_column", "oib_interval_coverage_complete"),
                 pd.Series(True, index=work.index)).astype(bool)).sum()
            if "alignment_class" in work.columns else 0),
        "n_aligned_dated_events": int((ev["cr_timing"].eq("dated") & ev["_eligible"]).sum()),
        "n_misaligned_dated_events": int(
            (ev["cr_timing"].eq("dated") & ~ev["_eligible"]).sum()),
        "same_day_status": t["same_day_g8_status"],
        "within_day_ordering_requires": t["within_day_ordering_requires"],
        "n_interval_events": n_int,
        "share_of_events_dated": (n_dated / total) if total else np.nan,
        "median_interval_width_days": (
            float(ev.loc[ev["cr_timing"] == "interval", "cr_interval_days"].median())
            if n_int else np.nan),
        "primary_sample": t["primary_sample"],
        "interval_outcome": t["interval_robustness"]["outcome"],
    }
