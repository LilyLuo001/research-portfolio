#!/usr/bin/env python3
"""Gate G9 — portfolio continuity across the wrapper switch (Plan v2.4 §9).

The design's central premise is that only the wrapper changed. G9 verifies that rather
than asserting it, per wave: holdings overlap, portfolio-weight correlation, turnover.

**Reported CONTINUOUSLY with a threshold-sensitivity curve.** Safeguard 6: an arbitrary
cutoff is not an economic law, so this module never returns a bare pass/fail. It returns
the continuous measures, plus the sample that survives at each candidate threshold, so the
confirmatory restriction can be read off a curve rather than legislated.

If continuity fails materially the CONFIRMATORY response is to restrict to high-continuity
waves; "wrapper-plus-portfolio change" is a SECONDARY interpretation reported separately
and may not silently replace the clean-wrapper headline.

Vendor-free: pre and post holdings arrive as injected frames
(wave | permno | weight), so this runs the moment holdings exist.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------------------- #
# Corporate-action adjustment — REUSED, not reinvented (2026-08-28).                        #
#                                                                                           #
# P1's holdings pipeline (p1/t2_wrds/holdings_pipeline.py) sets the house pattern: the CRSP #
# schema lives in ONE place, is marked UNVERIFIED until a live account confirms it, and is  #
# corrected there and nowhere else. The adjustment convention follows the same rule. Its    #
# DIRECTION is not asserted from memory — it is determined empirically by                   #
# verify_adjustment_convention() against names with a known corporate action and no trading #
# between the two as-of dates, which is the only evidence that settles it.                  #
# --------------------------------------------------------------------------------------- #
CORPORATE_ACTION_CONVENTION = {
    "vendor": "CRSP",
    "source": "crsp.msf / crsp.dsf",
    "field": "cfacshr",                 # cumulative factor to adjust shares outstanding
    "formula": "shares_adj = shares * cfacshr",   # common basis; direction VERIFIED below
    "status": "UNVERIFIED",
    "verify_with": "verify_adjustment_convention()",
    "holdings_as_of_field": "report_dt",          # same field P1 uses (SCHEMA['holdings'])
    "as_of_rule": "pre as-of STRICTLY before the wave effective date (P1 convention)",
}

_DIRECTIONS = {"multiply": lambda sh, f: sh * f, "divide": lambda sh, f: sh / f}


def verify_adjustment_convention(probe: pd.DataFrame, tol: float = 0.02) -> dict:
    """Settle the adjustment direction on evidence, not recollection.

    `probe` holds names with a KNOWN corporate action between two as-of dates and no trading
    in between, so correctly adjusted share counts must be EQUAL:

        permno | shares_pre | cfacshr_pre | shares_post | cfacshr_post

    Both directions are scored by median |log ratio| of adjusted counts. The winner must be
    inside `tol` and the loser clearly outside; anything else means the probe does not
    identify the convention and the caller must stop rather than pick one.
    """
    need = {"shares_pre", "cfacshr_pre", "shares_post", "cfacshr_post"}
    if not need <= set(probe.columns):
        raise ValueError("probe is missing %s" % sorted(need - set(probe.columns)))
    scores = {}
    for name, fn in _DIRECTIONS.items():
        a = fn(probe["shares_pre"].astype(float), probe["cfacshr_pre"].astype(float))
        b = fn(probe["shares_post"].astype(float), probe["cfacshr_post"].astype(float))
        ok = (a > 0) & (b > 0)
        scores[name] = (float(np.median(np.abs(np.log(b[ok] / a[ok]))))
                        if ok.any() else np.inf)
    best = min(scores, key=scores.get)
    other = [k for k in scores if k != best][0]
    verified = scores[best] <= tol < scores[other]
    return {
        "direction": best if verified else None,
        "scores": scores, "tol": tol, "n_probe": int(len(probe)),
        "status": "VERIFIED" if verified else "UNVERIFIED",
        "reason": "" if verified else (
            "NEED_HUMAN: the probe does not separate the two adjustment directions "
            "(scores %r). Do not guess — a wrong direction reads a split as 100%% turnover "
            "in that name, or hides real trading." % (scores,)),
    }


def _adjusted_shares(frame: pd.DataFrame, convention: dict) -> pd.Series:
    fn = _DIRECTIONS[convention["direction"]]
    return fn(frame["shares"].astype(float), frame["cfacshr"].astype(float))


def check_as_of_dates(pre: pd.DataFrame, post: pd.DataFrame,
                      wave_effective: dict) -> pd.DataFrame:
    """Holdings as-of dates are DATA, and they are reported. P1's rule — the pre-conversion
    report date is STRICTLY before the wave's effective date — is reused verbatim; the gap
    between as-of and effective date is reported because a six-month-stale pre snapshot makes
    "only the wrapper changed" a much weaker statement than a one-month-stale one."""
    rows = []
    for wave, eff in sorted(wave_effective.items()):
        eff = pd.Timestamp(eff)
        a = pd.to_datetime(pre.loc[pre["wave"] == wave, "as_of"], errors="coerce")
        b = pd.to_datetime(post.loc[post["wave"] == wave, "as_of"], errors="coerce")
        pre_as_of = a.max() if len(a.dropna()) else pd.NaT
        post_as_of = b.min() if len(b.dropna()) else pd.NaT
        rows.append({
            "wave": wave, "effective_date": eff,
            "pre_as_of": pre_as_of, "post_as_of": post_as_of,
            "pre_gap_days": (eff - pre_as_of).days if pd.notna(pre_as_of) else np.nan,
            "post_gap_days": (post_as_of - eff).days if pd.notna(post_as_of) else np.nan,
            "pre_strictly_before_effective": bool(pd.notna(pre_as_of) and pre_as_of < eff),
            "post_on_or_after_effective": bool(pd.notna(post_as_of) and post_as_of >= eff),
        })
    return pd.DataFrame(rows)


def share_continuity(pre: pd.DataFrame, post: pd.DataFrame,
                     convention: dict = None) -> pd.DataFrame:
    """Corporate-action-adjusted SHARE continuity (clarification 2026-08-19).

    Weight overlap alone cannot separate trading from price movement: a portfolio whose
    manager did nothing at all will show weight drift purely because constituent prices
    moved. Shares held do not drift with price — they change only when someone trades —
    so share continuity is the measure that isolates actual portfolio change.

    Shares must be CORPORATE-ACTION ADJUSTED first: a 2-for-1 split doubles the share
    count with no trade, and would otherwise read as 100% turnover in that name.

    Frames: wave | permno | shares | cfacshr | as_of.

    `convention` must be a VERIFIED record from verify_adjustment_convention() — there is no
    default and no silent identity factor, because unadjusted shares that quietly pass as
    adjusted are worse than no measure at all: they read corporate actions as trading.
    """
    if convention is None or convention.get("status") != "VERIFIED":
        raise ValueError(
            "NEED_HUMAN: share continuity requires a VERIFIED corporate-action convention "
            "(g9_continuity.verify_adjustment_convention). An unadjusted or wrongly-signed "
            "share count turns splits into turnover, which is the exact failure this measure "
            "exists to avoid.")
    for name, f in (("pre", pre), ("post", post)):
        missing = {"shares", "cfacshr"} - set(f.columns)
        if missing:
            raise ValueError("%s holdings missing %s" % (name, sorted(missing)))
    rows = []
    for wave in sorted(set(pre["wave"]) | set(post["wave"])):
        a = pre[pre["wave"] == wave]
        b = post[post["wave"] == wave]
        if a.empty or b.empty:
            rows.append({"wave": wave, "share_overlap": np.nan, "share_turnover": np.nan,
                         "names_retained": np.nan, "reason": "missing pre or post holdings"})
            continue
        sa = _adjusted_shares(a, convention).groupby(a["permno"]).sum()
        sb = _adjusted_shares(b, convention).groupby(b["permno"]).sum()
        idx = sa.index.union(sb.index)
        sa, sb = sa.reindex(idx).fillna(0.0), sb.reindex(idx).fillna(0.0)
        retained = float(np.minimum(sa, sb).sum())
        base = float(sa.sum())
        rows.append({
            "wave": wave,
            # share of the pre-conversion share base still held after the switch
            "share_overlap": retained / base if base > 0 else np.nan,
            # one-way share turnover: what fraction of the position base was traded
            "share_turnover": float((sb - sa).abs().sum() / (2 * base)) if base > 0 else np.nan,
            "names_retained": float((np.minimum(sa, sb) > 0).sum() / max(len(idx), 1)),
            "reason": "",
        })
    return pd.DataFrame(rows)


def wave_continuity(pre: pd.DataFrame, post: pd.DataFrame) -> pd.DataFrame:
    """Per-wave WEIGHT continuity. Frames: wave | permno | weight.

    Reported alongside share continuity, never instead of it — see share_continuity().
    """
    rows = []
    for wave in sorted(set(pre["wave"]) | set(post["wave"])):
        a = pre[pre["wave"] == wave].set_index("permno")["weight"].astype(float)
        b = post[post["wave"] == wave].set_index("permno")["weight"].astype(float)
        if a.empty or b.empty:
            rows.append({"wave": wave, "overlap_weight": np.nan, "overlap_count": np.nan,
                         "weight_corr": np.nan, "turnover": np.nan,
                         "reason": "missing pre or post holdings"})
            continue
        common = a.index.intersection(b.index)
        # Overlap measured in WEIGHT, not name count: dropping 40% of names that carry 2%
        # of the portfolio is not the same event as dropping 5% that carry 40%.
        overlap_w = float(min(a.reindex(common).sum(), b.reindex(common).sum()))
        overlap_n = float(len(common) / max(len(a.index.union(b.index)), 1))
        joined = pd.concat([a.reindex(a.index.union(b.index)).fillna(0.0),
                            b.reindex(a.index.union(b.index)).fillna(0.0)], axis=1)
        corr = float(joined.corr().iloc[0, 1]) if joined.iloc[:, 0].std() > 0 \
            and joined.iloc[:, 1].std() > 0 else np.nan
        # One-way turnover: half the L1 distance between weight vectors.
        turnover = float(0.5 * (joined.iloc[:, 1] - joined.iloc[:, 0]).abs().sum())
        rows.append({"wave": wave, "overlap_weight": overlap_w, "overlap_count": overlap_n,
                     "weight_corr": corr, "turnover": turnover, "reason": ""})
    return pd.DataFrame(rows)


def threshold_sensitivity(cont: pd.DataFrame, grid=None) -> pd.DataFrame:
    """How much sample survives at each candidate continuity threshold.

    This is the object the confirmatory restriction is read off — it makes the cost of
    each cutoff visible instead of letting one number stand in for an economic law.
    """
    grid = grid if grid is not None else [round(x, 2) for x in np.arange(0.50, 1.00, 0.05)]
    ok = cont.dropna(subset=["overlap_weight"])
    return pd.DataFrame([{
        "threshold": t,
        "waves_retained": int((ok["overlap_weight"] >= t).sum()),
        "waves_total": int(len(cont)),
        "share_retained": float((ok["overlap_weight"] >= t).mean()) if len(ok) else np.nan,
    } for t in grid])


def summarize(cont: pd.DataFrame, config: dict, shares: pd.DataFrame = None,
              as_of: pd.DataFrame = None, convention: dict = None) -> dict:
    """Facts, and the registered responses — never a bare verdict.

    `shares` is the corporate-action-adjusted share-continuity frame. It is optional only
    so the weight measures can be inspected early; a G9 report WITHOUT it is incomplete,
    and the returned dict says so.
    """
    g0 = config.get("gate0_thresholds", {})
    ok = cont.dropna(subset=["overlap_weight"])
    anchor = g0.get("portfolio_overlap_min")
    return {
        "waves": int(len(cont)),
        "waves_measurable": int(len(ok)),
        "median_overlap_weight": float(ok["overlap_weight"].median()) if len(ok) else None,
        "median_weight_corr": float(ok["weight_corr"].median()) if len(ok) else None,
        "median_turnover": float(ok["turnover"].median()) if len(ok) else None,
        "anchor_threshold": anchor,
        "waves_at_or_above_anchor": (int((ok["overlap_weight"] >= anchor).sum())
                                     if anchor is not None and len(ok) else None),
        "confirmatory_response": g0.get("g9_confirmatory_response"),
        "secondary_interpretation": g0.get("g9_secondary_interpretation"),
        "reporting": g0.get("g9_reporting"),
        "share_continuity_reported": shares is not None,
        "median_share_overlap": (float(shares["share_overlap"].median())
                                 if shares is not None and len(shares.dropna(
                                     subset=["share_overlap"])) else None),
        "median_share_turnover": (float(shares["share_turnover"].median())
                                  if shares is not None and len(shares.dropna(
                                      subset=["share_turnover"])) else None),
        "adjustment_convention": (convention or {}).get("status", "ABSENT"),
        "adjustment_direction": (convention or {}).get("direction"),
        "as_of_reported": as_of is not None,
        "max_pre_gap_days": (float(as_of["pre_gap_days"].max())
                             if as_of is not None and len(as_of) else None),
        "waves_with_pre_as_of_not_before_effective": (
            [] if as_of is None else
            sorted(as_of.loc[~as_of["pre_strictly_before_effective"], "wave"].tolist())),
        "incomplete": _incomplete_reasons(shares, as_of, convention),
    }


def _incomplete_reasons(shares, as_of, convention):
    """A G9 report is incomplete until all three are present. Named separately so the
    message says WHICH piece is missing rather than just that something is."""
    why = []
    if shares is None:
        why.append("weight measures only — weight drift reflects price movement even with "
                   "zero trading, so corporate-action-adjusted share continuity is required")
    if convention is None or convention.get("status") != "VERIFIED":
        why.append("the corporate-action adjustment convention is not verified")
    if as_of is None:
        why.append("holdings as-of dates are not reported — the pre snapshot's staleness "
                   "determines how strong 'only the wrapper changed' can be")
    return None if not why else "G9 INCOMPLETE: " + "; ".join(why) + "."
