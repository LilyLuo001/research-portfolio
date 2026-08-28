#!/usr/bin/env python3
"""CRSP corporate-action adjustment — the ONE documented convention for the portfolio.

Two projects need to compare share counts across a date boundary: P1 (holdings around a
conversion wave) and refraction (G9 portfolio continuity). Inferring the meaning of the same
CRSP field twice, independently, is how two halves of one portfolio end up disagreeing about
what a split means. So the semantics are documented HERE, once, and both sides import this
module rather than reimplementing the arithmetic.

Same status discipline as SCHEMA in holdings_pipeline.py: the field NAMES and their
documented meaning are transcribed below; the DIRECTION of the arithmetic is UNVERIFIED
until a live account confirms it, and is confirmed by evidence (verify_direction) rather
than by recollection. Correct it here and nowhere else.

--------------------------------------------------------------------------------------
FIELD SEMANTICS (transcribe from the CRSP data dictionary; do not fill from memory)
--------------------------------------------------------------------------------------
  cfacshr   "cumulative factor to adjust shares outstanding". A per-permno, per-date
            factor that makes share counts comparable across corporate actions. CRSP
            documents both the factor and the base date it is normalized to; which
            direction (multiply or divide) puts two dates on a common basis follows from
            that normalization, and is exactly what verify_direction() settles.
  cfacpr    the price analogue. NOT interchangeable with cfacshr: they differ whenever a
            distribution changes price without changing share count. Never substitute one.
  shrout    shares outstanding, in THOUSANDS (see SHROUT_UNITS_PER_SHARE in
            holdings_pipeline.py). Unrelated to holdings share counts, which are raw.

WHY THIS MATTERS: a 2-for-1 split doubles a share count with no trade. Unadjusted, that
name reads as 100% turnover. Adjusted in the WRONG direction, it reads as 300%. Both are
worse than no measure at all, because both look like data.

--------------------------------------------------------------------------------------
AS-OF DATES: report dates, never filing dates
--------------------------------------------------------------------------------------
Holdings carry two dates and they are not interchangeable:

  report date (crsp.holdings.report_dt; N-PORT/N-CSR "period of report")
      the date the positions were HELD. This is the as-of date. It is what P1's
      holdings_pipeline.py selects on (`report_dt < effective_date`) and the only date
      either project may use to place holdings relative to a conversion.

  filing date (EDGAR acceptance/filed date)
      the date the document reached the SEC — typically 30-60+ days later, and reflecting
      no information about WHEN the portfolio looked like that.

Using a filing date silently shifts every holding by the filing lag: a pre-conversion
portfolio filed after the conversion looks post-conversion, which inverts the very
comparison G9 exists to make. FILING_DATE_FIELDS below names the columns that must never
be passed as an as-of date, and assert_as_of_not_filing_date() refuses them.
"""
from __future__ import annotations

# The canonical fields. Status mirrors holdings_pipeline.SCHEMA.
CORPACTION_SCHEMA = {
    "table": "crsp.dsf / crsp.msf",
    "permno": "permno",
    "date": "date",
    "share_factor": "cfacshr",          # shares — the one this module uses
    "price_factor": "cfacpr",           # price — documented so it is not substituted
    "status": "UNVERIFIED",             # same discipline as holdings_pipeline.SCHEMA
}

HOLDINGS_AS_OF_FIELD = "report_dt"      # crsp.holdings; P1's selection field

# Columns that are FILING dates. Passing one as an as-of date is a silent, systematic
# shift of every holding by the filing lag.
FILING_DATE_FIELDS = frozenset({
    "filing_date", "filed_date", "file_date", "filedt", "filing_dt",
    "acceptance_date", "accepted_date", "acceptance_datetime", "date_filed",
    "nport_filing_date", "edgar_filing_date",
})

DIRECTIONS = {
    "multiply": lambda shares, factor: shares * factor,
    "divide": lambda shares, factor: shares / factor,
}


class ConventionError(Exception):
    """The convention is not established well enough to compute on."""


def verify_direction(probe, tol=0.02):
    """Settle multiply-vs-divide on evidence.

    `probe` is a mapping-of-sequences or DataFrame of names with a KNOWN corporate action
    between two dates and NO trading in between, so correctly adjusted counts must be EQUAL:

        shares_pre | cfacshr_pre | shares_post | cfacshr_post

    Both directions are scored by median |log ratio| of adjusted counts. The winner must sit
    inside `tol` and the loser clearly outside it; anything else means the probe does not
    identify the convention, and the caller must stop rather than pick.
    """
    import numpy as np

    need = ("shares_pre", "cfacshr_pre", "shares_post", "cfacshr_post")
    missing = [c for c in need if c not in probe]
    if missing:
        raise ConventionError("probe is missing %s" % (missing,))
    pre_s = np.asarray(probe["shares_pre"], dtype=float)
    pre_f = np.asarray(probe["cfacshr_pre"], dtype=float)
    post_s = np.asarray(probe["shares_post"], dtype=float)
    post_f = np.asarray(probe["cfacshr_post"], dtype=float)

    scores = {}
    for name, fn in DIRECTIONS.items():
        a, b = fn(pre_s, pre_f), fn(post_s, post_f)
        ok = (a > 0) & (b > 0)
        scores[name] = float(np.median(np.abs(np.log(b[ok] / a[ok])))) if ok.any() else np.inf
    best = min(scores, key=scores.get)
    other = [k for k in scores if k != best][0]
    verified = scores[best] <= tol < scores[other]
    return {
        "direction": best if verified else None,
        "scores": scores, "tol": tol, "n_probe": int(len(pre_s)),
        "status": "VERIFIED" if verified else "UNVERIFIED",
        "field": CORPACTION_SCHEMA["share_factor"],
        "source": "p1/t2_wrds/corpactions.py",
        "reason": "" if verified else (
            "NEED_HUMAN: the probe does not separate the two adjustment directions "
            "(scores %r). Do not guess — a wrong direction reads a split as 100%% turnover "
            "in that name, or hides real trading." % (scores,)),
    }


def adjusted_shares(shares, factor, convention):
    """Put a share count on the common basis. Requires a VERIFIED convention: there is no
    default and no silent identity factor, because unadjusted counts that pass as adjusted
    are worse than no measure at all."""
    if not convention or convention.get("status") != "VERIFIED":
        raise ConventionError(
            "NEED_HUMAN: corporate-action adjustment requires a VERIFIED convention from "
            "corpactions.verify_direction(). Unadjusted or wrongly-signed share counts turn "
            "splits into turnover, which is the exact failure this exists to prevent.")
    if convention.get("field") != CORPACTION_SCHEMA["share_factor"]:
        raise ConventionError(
            "convention was verified on field %r, not %r — cfacpr and cfacshr are not "
            "interchangeable" % (convention.get("field"), CORPACTION_SCHEMA["share_factor"]))
    return DIRECTIONS[convention["direction"]](shares, factor)


def assert_as_of_not_filing_date(columns, what="holdings as-of date"):
    """Refuse a filing date where an as-of date belongs."""
    hits = sorted(c for c in columns if str(c).strip().lower() in FILING_DATE_FIELDS)
    if hits:
        raise ConventionError(
            "%s: %s is a FILING date, not an as-of date. Filing lag is typically 30-60+ days, "
            "so a pre-conversion portfolio filed after the conversion would read as "
            "post-conversion. Use %r (the period of report)."
            % (what, hits, HOLDINGS_AS_OF_FIELD))


def classify_as_of(as_of, effective_date):
    """Where a holdings snapshot sits relative to a conversion.

    P1's rule, reused verbatim: PRE requires the report date STRICTLY before the effective
    date, POST requires it on or after. A snapshot on the effective date itself is POST —
    it already reflects the conversion.
    """
    import pandas as pd

    a, e = pd.Timestamp(as_of), pd.Timestamp(effective_date)
    if pd.isna(a):
        return "unknown"
    return "pre" if a < e else "post"
