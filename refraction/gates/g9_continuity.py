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


def share_continuity(pre: pd.DataFrame, post: pd.DataFrame) -> pd.DataFrame:
    """Corporate-action-adjusted SHARE continuity (clarification 2026-08-19).

    Weight overlap alone cannot separate trading from price movement: a portfolio whose
    manager did nothing at all will show weight drift purely because constituent prices
    moved. Shares held do not drift with price — they change only when someone trades —
    so share continuity is the measure that isolates actual portfolio change.

    Shares must be CORPORATE-ACTION ADJUSTED first: a 2-for-1 split doubles the share
    count with no trade, and would otherwise read as 100% turnover in that name.

    Frames: wave | permno | shares | adj_factor  (adjusted shares = shares / adj_factor,
    with the factor on a common basis across the pre/post boundary).
    """
    rows = []
    for wave in sorted(set(pre["wave"]) | set(post["wave"])):
        a = pre[pre["wave"] == wave]
        b = post[post["wave"] == wave]
        if a.empty or b.empty:
            rows.append({"wave": wave, "share_overlap": np.nan, "share_turnover": np.nan,
                         "names_retained": np.nan, "reason": "missing pre or post holdings"})
            continue
        sa = (a["shares"].astype(float) / a.get("adj_factor", 1.0)).groupby(a["permno"]).sum()
        sb = (b["shares"].astype(float) / b.get("adj_factor", 1.0)).groupby(b["permno"]).sum()
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


def summarize(cont: pd.DataFrame, config: dict, shares: pd.DataFrame = None) -> dict:
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
        "incomplete": None if shares is not None else
        "G9 INCOMPLETE: weight measures only. Weight drift reflects price movement even "
        "with zero trading; corporate-action-adjusted share continuity is required.",
    }
