#!/usr/bin/env python3
"""p1/wrds/universe.py — what to pull, derived from committed artifacts.

Runs entirely offline. The WRDS universe is ENDOGENOUS (ops/briefs/
WRDS-access-assessment.md: "you can't hand a seller a frozen file list") — it is
whatever the converting funds held. That is exactly what the free path already
established, so the pull scope is computable NOW, before any account is booked,
from p1/conv_exposure_free.parquet + p1/t2_wrds/waves_members.csv.

Knowing the scope in advance is the whole point of the sprint plan: it turns a
3-6 week on/off rental into a 3-5 day execution window.

  python p1/wrds/universe.py            # print the scope report
  python p1/wrds/universe.py --write    # also write pull_scope.json + lineage
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / "p1" / "wrds"
CONVEXP = ROOT / "p1" / "conv_exposure_free.parquet"
DROPPED = ROOT / "p1" / "t2_free" / "NEED_HUMAN_stocks.csv"
MEMBERS = ROOT / "p1" / "t2_wrds" / "waves_members.csv"
EVENTS = ROOT / "p1" / "events_merged.csv"
SCOPE = HERE / "pull_scope.json"

# Event-window half-widths, from the plan. Spine two's CAR path is [0, +120]
# trading days (docs/基金转换实验_博士研究计划.md §7); we pull a pre-window too
# so the market model and the pre-announcement tests have an estimation period.
PRE_TRADING_DAYS = 250
POST_TRADING_DAYS = 120
# Calendar padding when converting trading days to a date range to hand WRDS.
# 252 trading days ~ 365 calendar days; pad generously, daily data is cheap to
# over-request and expensive to re-request after the account is released.
TRADING_TO_CALENDAR = 1.55
# Fundamentals need a longer runway than prices: the SUE time-series branch takes
# an 8-quarter lookback, and annual book equity for the control match (§107) is
# stamped at a fiscal year end that can sit almost two years before an event in
# the worst alignment. Three years back from the earliest anchor covers both
# without a per-event calculation, and quarterly/annual files are tiny.
FUNDAMENTAL_LOOKBACK_YEARS = 3


def _read_convexp_cusips() -> tuple[set[str], dict]:
    try:
        import pandas as pd
    except ImportError:
        sys.exit("NEED pandas: pip install pandas pyarrow")
    df = pd.read_parquet(CONVEXP)
    stats = {"rows": int(len(df)),
             "distinct_cusips": int(df["cusip"].nunique()),
             "distinct_waves": int(df["wave_id"].nunique())}
    return set(df["cusip"].dropna().astype(str)), stats


def _read_dropped_cusips() -> set[str]:
    """Dropped cells are treated stocks too — they lost a DENOMINATOR, not a
    holding. CRSP has shrout for the US names among them, so the WRDS pull must
    cover them or it reproduces the free path's own gap."""
    if not DROPPED.exists():
        return set()
    with open(DROPPED, newline="") as f:
        return {r["cusip"] for r in csv.DictReader(f) if r.get("cusip")}


def _wave_dates() -> list[str]:
    with open(MEMBERS, newline="") as f:
        return sorted({r["effective_date"] for r in csv.DictReader(f)
                       if r.get("effective_date")})


_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _announce_dates() -> list[str]:
    """Announcement dates from events_merged.csv.

    Load-bearing, and the reason this function exists: the event study anchors
    t=0 on the ANNOUNCEMENT date, not the effective date (plan §6 threat T2 —
    announcement-to-effective is 2-6 months and arbitrageurs can position in
    between; T5 blueprint §5 fixes t=0 = announcement). Scoping the daily pull
    from the earliest EFFECTIVE date silently truncates the market-model
    estimation window for the earliest events: no error is raised, the window is
    just shorter and beta quietly differs.
    """
    with open(EVENTS, newline="") as f:
        return sorted({r["announce_date"] for r in csv.DictReader(f)
                       if _ISO.match(str(r.get("announce_date", "")))})


def build_scope() -> dict:
    computed, stats = _read_convexp_cusips()
    dropped = _read_dropped_cusips()
    dates = _wave_dates()
    announces = _announce_dates()

    # The pull must span BOTH anchors: the estimation window runs back from the
    # earliest announcement (t=0), the post window runs forward from the latest
    # effective date (the conversion itself). Taking the min/max across the two
    # is the only choice that cannot truncate either end.
    lo = min(dt.date.fromisoformat(dates[0]), dt.date.fromisoformat(announces[0]))
    hi = max(dt.date.fromisoformat(dates[-1]), dt.date.fromisoformat(announces[-1]))
    pre = dt.timedelta(days=int(PRE_TRADING_DAYS * TRADING_TO_CALENDAR))
    post = dt.timedelta(days=int(POST_TRADING_DAYS * TRADING_TO_CALENDAR))
    today = dt.date.today()
    # Waves dated in the future are announced-but-not-effective conversions; the
    # daily pull cannot reach past today, so cap it and say so.
    daily_end = min(hi + post, today)

    return {
        "generated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "note": ("Derived from committed artifacts only — no WRDS access needed to "
                 "compute this. Hand it to whoever books the account."),
        "universe": {
            "cusips_with_convexp": len(computed),
            "cusips_dropped_for_missing_denominator": len(dropped),
            "cusips_total_to_map": len(computed | dropped),
            "comment": ("dropped cells must be pulled too — they are missing a "
                        "denominator, not a holding, and CRSP supplies shrout for "
                        "the US names among them"),
        },
        "waves": {
            "n_waves": len(dates),
            "first_effective_date": dates[0],
            "last_effective_date": dates[-1],
            "first_announce_date": announces[0],
            "last_announce_date": announces[-1],
            "future_dated_waves": [d for d in dates if dt.date.fromisoformat(d) > today],
        },
        "windows": {
            "anchor": ("announcement date (t=0, plan §6 threat T2) for the lower bound; "
                       "effective date for the upper bound — whichever is more extreme"),
            "pre_trading_days": PRE_TRADING_DAYS,
            "post_trading_days": POST_TRADING_DAYS,
            "daily_start": (lo - pre).isoformat(),
            "daily_end": daily_end.isoformat(),
            "daily_end_capped_at_today": daily_end == today and (hi + post) > today,
            "monthly_start": (lo - pre).isoformat(),
            "monthly_end": daily_end.isoformat(),
            "fundamentals_start": (lo - pre).replace(
                year=(lo - pre).year - FUNDAMENTAL_LOOKBACK_YEARS).isoformat(),
            "fundamentals_end": daily_end.isoformat(),
            "fundamentals_lookback_years": FUNDAMENTAL_LOOKBACK_YEARS,
        },
        "convexp_stats": stats,
        "sources": {
            "conv_exposure_free.parquet": str(CONVEXP.relative_to(ROOT)),
            "NEED_HUMAN_stocks.csv": str(DROPPED.relative_to(ROOT)),
            "waves_members.csv": str(MEMBERS.relative_to(ROOT)),
            "events_merged.csv": str(EVENTS.relative_to(ROOT)),
        },
    }


def format_scope(s: dict) -> str:
    u, w, win = s["universe"], s["waves"], s["windows"]
    L = ["# P1 WRDS pull scope (derived offline from committed artifacts)", "",
         f"universe to map CUSIP->PERMNO : {u['cusips_total_to_map']:,}",
         f"  of which ConvExp computed   : {u['cusips_with_convexp']:,}",
         f"  of which dropped (no denom) : {u['cusips_dropped_for_missing_denominator']:,}",
         "",
         f"waves                         : {w['n_waves']} "
         f"({w['first_effective_date']} .. {w['last_effective_date']})",
         f"announcements (t=0)           : {w['first_announce_date']} .. "
         f"{w['last_announce_date']}"]
    if w["future_dated_waves"]:
        L.append(f"  future-dated (no post data yet): {len(w['future_dated_waves'])} "
                 f"-> {', '.join(w['future_dated_waves'])}")
    L += ["",
          f"daily  (dsf) date range       : {win['daily_start']} .. {win['daily_end']}"
          + ("  [capped at today]" if win["daily_end_capped_at_today"] else ""),
          f"monthly (msf) date range      : {win['monthly_start']} .. {win['monthly_end']}",
          f"fundamentals (comp) range     : {win['fundamentals_start']} .. "
          f"{win['fundamentals_end']}  "
          f"[{win['fundamentals_lookback_years']}y extra lookback]",
          f"windows                       : -{win['pre_trading_days']} / "
          f"+{win['post_trading_days']} trading days, anchored on the ANNOUNCEMENT "
          f"date at the lower bound",
          "",
          "The daily pull is the big one. Everything else is small. Pull all five in",
          "one sitting, land raw immutable, release the account — see",
          "ops/briefs/P1-WRDS-SPRINT.md."]
    return "\n".join(L)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true",
                    help="write p1/wrds/pull_scope.json + lineage")
    a = ap.parse_args()
    scope = build_scope()
    print(format_scope(scope))
    if a.write:
        SCOPE.write_text(json.dumps(scope, indent=2) + "\n")
        sys.path.insert(0, str(ROOT / "ops" / "runner"))
        from lineage import write_lineage
        write_lineage(SCOPE, [CONVEXP, DROPPED, MEMBERS, EVENTS])
        print(f"\nwrote {SCOPE.relative_to(ROOT)} + lineage")


if __name__ == "__main__":
    main()
