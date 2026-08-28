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

import sys
from pathlib import Path

import numpy as np
import pandas as pd


# --------------------------------------------------------------------------------------- #
# Corporate-action adjustment — IMPORTED, not reimplemented (2026-08-28).                   #
#                                                                                           #
# The convention lives in p1/t2_wrds/corpactions.py, which owns the CRSP field semantics    #
# for the whole portfolio. G9 does not infer the meaning of cfacshr a second time: two       #
# independent readings of one field is how two halves of one portfolio end up disagreeing   #
# about what a split means. Documentation fixes the semantics; the integration test in      #
# refraction/tests/test_gates_g8_g9.py verifies that this module and P1 run the SAME code.  #
# --------------------------------------------------------------------------------------- #
_P1 = Path(__file__).resolve().parents[2] / "p1" / "t2_wrds"
if str(_P1) not in sys.path:
    sys.path.insert(0, str(_P1))
import corpactions as ca                                          # noqa: E402

CORPORATE_ACTION_CONVENTION = {
    "vendor": "CRSP",
    "source": ca.CORPACTION_SCHEMA["table"],
    "field": ca.CORPACTION_SCHEMA["share_factor"],
    "formula": "shares_adj = <direction>(shares, cfacshr); direction from verify_direction()",
    "status": ca.CORPACTION_SCHEMA["status"],
    "owned_by": "p1/t2_wrds/corpactions.py",
    "verify_with": "corpactions.verify_direction()",
    "holdings_as_of_field": ca.HOLDINGS_AS_OF_FIELD,
    "as_of_rule": "pre as-of STRICTLY before the wave effective date (P1 convention)",
}


def verify_adjustment_convention(probe, tol: float = 0.02) -> dict:
    """Thin delegation to P1's canonical verifier — kept so G9's callers have one name for
    it, and so a future divergence has to be deliberate rather than accidental."""
    return ca.verify_direction(probe, tol=tol)


def _adjusted_shares(frame: pd.DataFrame, convention: dict) -> pd.Series:
    return ca.adjusted_shares(frame["shares"].astype(float),
                              frame["cfacshr"].astype(float), convention)


def check_as_of_dates(pre: pd.DataFrame, post: pd.DataFrame,
                      wave_effective: dict) -> pd.DataFrame:
    """Holdings as-of dates are DATA, and they are reported. P1's rule — the pre-conversion
    report date is STRICTLY before the wave's effective date — is reused verbatim; the gap
    between as-of and effective date is reported because a six-month-stale pre snapshot makes
    "only the wrapper changed" a much weaker statement than a one-month-stale one."""
    ca.assert_as_of_not_filing_date(pre.columns, "pre-conversion holdings")
    ca.assert_as_of_not_filing_date(post.columns, "post-conversion holdings")
    rows = []
    for wave, eff in sorted(wave_effective.items()):
        eff = pd.Timestamp(eff)
        a = pd.to_datetime(pre.loc[pre["wave"] == wave, "as_of"], errors="coerce")
        b = pd.to_datetime(post.loc[post["wave"] == wave, "as_of"], errors="coerce")
        # PRE takes the LATEST snapshot still strictly before the conversion, POST the
        # EARLIEST on or after it: the tightest pair around the switch, so the comparison
        # is about the wrapper and not about months of unrelated drift.
        pre_as_of = a[a < eff].max() if len(a.dropna()) else pd.NaT
        post_as_of = b[b >= eff].min() if len(b.dropna()) else pd.NaT
        # the strictly-after alternative, for the item-5 sensitivity
        strict_post = b[b > eff].min() if len(b.dropna()) else pd.NaT
        rows.append({
            "wave": wave, "effective_date": eff,
            "pre_as_of": pre_as_of, "post_as_of": post_as_of,
            "pre_gap_days": (eff - pre_as_of).days if pd.notna(pre_as_of) else np.nan,
            "post_gap_days": (post_as_of - eff).days if pd.notna(post_as_of) else np.nan,
            "pre_strictly_before_effective": bool(pd.notna(pre_as_of) and pre_as_of < eff),
            "post_on_or_after_effective": bool(pd.notna(post_as_of) and post_as_of >= eff),
            "pre_side": ca.classify_as_of(pre_as_of, eff),
            "post_side": ca.classify_as_of(post_as_of, eff),
            "as_of_field": ca.HOLDINGS_AS_OF_FIELD,
            # Audit item 5. A post snapshot dated EXACTLY on the effective date is the
            # ambiguous case: whether it reflects the converted portfolio depends on the
            # fund's own reporting convention, which the as-of date does not reveal. It is
            # counted as post (P1's rule) and FLAGGED, so a strictly-after sensitivity can
            # be run on the waves it affects.
            "post_as_of_equals_effective": bool(pd.notna(post_as_of) and post_as_of == eff),
            "post_as_of_strictly_after": bool(pd.notna(strict_post)),
            "post_as_of_strict": strict_post,
            "post_gap_days_strict": ((strict_post - eff).days
                                     if pd.notna(strict_post) else np.nan),
        })
    out = pd.DataFrame(rows)
    # The confirmation the design rests on: pre holdings are held BEFORE the conversion and
    # first-post holdings AFTER it. A wave that fails this is reported, never silently used.
    out["as_of_ok"] = (out["pre_side"] == "pre") & (out["post_side"] == "post")
    return out


def effective_date_sensitivity(as_of: pd.DataFrame) -> dict:
    """Audit item 5: which waves rest on a post snapshot dated ON the conversion date, and
    can the analysis be re-run without them?

    Reported whether or not any wave is affected — a sensitivity that is only mentioned when
    it bites is not a sensitivity, it is an excuse.
    """
    flagged = as_of.loc[as_of["post_as_of_equals_effective"]]
    recoverable = flagged.loc[flagged["post_as_of_strictly_after"]]
    return {
        "n_waves": int(len(as_of)),
        "n_waves_post_as_of_equals_effective": int(len(flagged)),
        "waves_affected": sorted(flagged["wave"].tolist()),
        "waves_with_a_strictly_after_alternative": sorted(recoverable["wave"].tolist()),
        "waves_lost_under_strictly_after": sorted(
            flagged.loc[~flagged["post_as_of_strictly_after"], "wave"].tolist()),
        "sensitivity_required": bool(len(flagged)),
        "how": ("re-run continuity using post_as_of_strict for the affected waves and report "
                "both columns; waves with no strictly-after snapshot drop out of the "
                "sensitivity and that loss is reported, not absorbed"),
    }


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
        "effective_date_sensitivity": (None if as_of is None
                                       else effective_date_sensitivity(as_of)),
        "waves_failing_as_of_placement": (
            [] if as_of is None else sorted(as_of.loc[~as_of["as_of_ok"], "wave"].tolist())),
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
