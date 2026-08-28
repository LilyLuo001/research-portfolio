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

    # ---- the scaled regressor, for MAGNITUDE use only -------------------------------
    lo, hi = [q / 100.0 for q in d["winsorize_pct"]]
    df["CR"] = df.groupby(d["winsorize_within"])["CR_raw"].transform(
        lambda v: v.clip(v.quantile(lo), v.quantile(hi)))
    if d["standardize_within_fund"]:
        if d["standardize_mode"] != "sd_only":
            raise SafeguardViolation(
                "standardization must be SD-ONLY (%r registered). Mean-centring would make a "
                "positive creation BELOW the fund's average creation rate read as negative."
                % d["standardize_mode"])
        # scale only, no mean shift: 0 stays 0 and the sign is untouched
        df["CR"] = df.groupby("fund")["CR"].transform(
            lambda v: v / v.std(ddof=0) if v.std(ddof=0) > 0 else v * 0.0)
    return df.drop(columns=["_S", "_gap"])


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
    # A daily-refresh series can legitimately show unchanged days — funds do go a day without
    # creations. What staleness looks like is LONG identical runs ending in a jump, and it is
    # the pattern, not the count, that the human reads.
    looks_stale = bool(longest >= 3 and median_unchanged > 0.5)
    return {
        "stated_update_frequency": stated,
        "by_fund": tab,
        "median_share_of_days_unchanged": median_unchanged,
        "longest_unchanged_run_days": longest,
        "looks_like_carryforward": looks_stale,
        "consistent_with_daily_refresh": bool(stated == "daily" and not looks_stale),
        "implication": (
            "a jump after a run of identical values dates the WHOLE accumulated flow on the "
            "refresh day; treat those as interval events, not dated ones, and report how "
            "many CR events are affected" if looks_stale else
            "no carry-forward fingerprint; CR event dates are as precise as the refresh"),
        "needs_human_review": looks_stale or stated != "daily",
    }
