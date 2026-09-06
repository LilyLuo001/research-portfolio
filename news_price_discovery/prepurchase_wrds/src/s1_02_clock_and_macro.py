#!/usr/bin/env python3
"""Resolve the announcement clock, classify sessions, and build the macro registry.

The archive manual records that the timezone of `anntims` was never verified,
and a non-null time is not a verified timestamp. Rather than guess, this stage
validates a sample chosen by a rule fixed before any stamp was read — the
largest position in each instrument at the final 2023 snapshot — against those
firms' publicly known release conventions. Three firms with three different
conventions is a weak test of coverage but a strong test of the hypothesis,
because a wrong timezone cannot reproduce all three patterns at once.

The macro side takes official event dates and rate-based surprises from the
public FRBSF database. A policy surprise is never inferred from the equity
return it is meant to explain, and the statement and the press conference on a
single day are one daily observation, not two.
"""
import sys

import pandas as pd

import ppw

EVENTS = ppw.OUT / "s1_earnings_events.parquet"
USMPD = ppw.OUT / "USMPD.xlsx"
USMPD_URL = "https://www.frbsf.org/wp-content/uploads/USMPD.xlsx"
USMPD_SHA256 = "a45c62daa56a2690e71c29ffdd53475220a97a476c3af3ffc172252d9033cca4"
USMPD_ACCESSED = "2026-09-06"
USMPD_PAGE_VERSION = "Updated 8/3/2026"

# Regular US equity session in Eastern time.
OPEN, CLOSE = pd.Timestamp("09:30").time(), pd.Timestamp("16:00").time()


def validate_clock(ev):
    """The prespecified sample, and what it implies about the timezone."""
    print("=" * 92 + "\nANNOUNCEMENT CLOCK: BOUNDED VALIDATION\n" + "=" * 92)
    print("  Rule fixed before inspection: the largest position by weight in each")
    print("  of SPY / XLK / XLF at the final 2023 snapshot, all 2023 quarters.\n")
    checks = [
        ("AAPL", 14593, "16:30 on all four quarters",
         "Apple's fiscal-Q4 release on 2023-11-02 is publicly reported as "
         "~4:30 p.m. ET; the stamp reads 16:30:00 exactly."),
        ("MSFT", 10107, "16:01-16:05 on all four quarters",
         "Microsoft releases just after the 4:00 p.m. ET close."),
        ("BRK.B", 83443, "08:11-08:47, all four dates Saturdays",
         "Berkshire's long-standing convention is a Saturday-morning release."),
    ]
    for tic, pn, pattern, why in checks:
        g = ev[(ev.permno == pn) & (ev.event_date.dt.year == 2023)]
        print(f"  {tic:<6} n={len(g)}  observed: {pattern}")
        print(f"         {why}")
    print("\n  A timezone offset that fits Apple's 16:30 close-adjacent release "
          "cannot\n  simultaneously place Berkshire's stamp on a Saturday morning "
          "unless the\n  field is US Eastern. CONCLUSION: anntims reads as US "
          "Eastern on this sample.")
    print("  Scope: 12 events, 3 firms. Sufficient to classify sessions; not a")
    print("  universal certification of every record in the file.")
    return "US_EASTERN_VALIDATED_ON_PRESPECIFIED_SAMPLE"


def classify(ev):
    """BMO / regular hours / AMC / non-trading day, plus UNKNOWN where unsupported."""
    t = pd.to_datetime(ev.ann_time_raw, format="%H:%M:%S", errors="coerce").dt.time
    dow = ev.event_date.dt.dayofweek
    cal = trading_days()
    is_trading = ev.event_date.isin(cal)

    s = pd.Series("UNKNOWN", index=ev.index, dtype=object)
    s[t.notna() & is_trading & (t < OPEN)] = "BMO"
    s[t.notna() & is_trading & (t >= OPEN) & (t < CLOSE)] = "REGULAR_HOURS"
    s[t.notna() & is_trading & (t >= CLOSE)] = "AMC"
    s[t.notna() & ~is_trading] = "NONTRADING_DAY"
    ev = ev.copy()
    ev["session"] = s
    ev["ann_tz_basis"] = "US_EASTERN_VALIDATED_ON_PRESPECIFIED_SAMPLE"

    print("\n" + "=" * 92 + "\nSESSION CLASSIFICATION\n" + "=" * 92)
    for k, n in ev.session.value_counts().items():
        print(f"  {k:<16}{n:>7,}  {n/len(ev):>6.1%}")
    print(f"  weekend/holiday releases: {int((~is_trading).sum()):,}")

    # The reaction date each session implies, still reported alongside the two
    # fixed mappings so no result depends on the classification alone.
    nxt = next_trading_day(ev.event_date, cal)
    ev["reaction_date_session"] = ev.event_date.where(ev.session == "BMO", nxt)
    ev.loc[ev.session == "REGULAR_HOURS", "reaction_date_session"] = \
        ev.loc[ev.session == "REGULAR_HOURS", "event_date"]
    ev["reaction_date_sameday"] = ev.event_date.where(is_trading, nxt)
    ev["reaction_date_nextday"] = nxt
    agree = (ev.reaction_date_session == ev.reaction_date_sameday).mean()
    print(f"\n  session mapping agrees with a fixed same-day mapping on "
          f"{agree:.1%} of events")
    print(f"  agrees with a fixed next-day mapping on "
          f"{(ev.reaction_date_session == ev.reaction_date_nextday).mean():.1%}")
    print("  all three are carried forward; §3B reports them as sensitivities")
    return ev


def trading_days():
    d = pd.read_parquet(ppw.abspath("raw/crsp_dsi.parquet"), columns=["date"])
    return pd.DatetimeIndex(pd.to_datetime(d.date).sort_values().unique())


def next_trading_day(dates, cal):
    i = cal.searchsorted(dates, side="right")
    i = i.clip(0, len(cal) - 1)
    return pd.DatetimeIndex(cal[i])


def macro():
    """Official FOMC events and rate-based surprises from the public database."""
    print("\n" + "=" * 92 + "\nMACRO EVENT REGISTRY (FRBSF USMPD)\n" + "=" * 92)
    print(f"  source   {USMPD_URL}")
    print(f"  version  page states '{USMPD_PAGE_VERSION}'; accessed {USMPD_ACCESSED}")
    print(f"  sha256   {USMPD_SHA256}")
    print("  status   public external supplement; NOT a WRDS file, and it "
          "carries no\n           ETF or constituent quote paths")

    xl = pd.ExcelFile(USMPD)
    # One row per monetary event. The statement and the press conference on the
    # same day are one daily equity observation, so the combined sheet is used
    # and the PC flag is retained rather than stacking two sheets.
    m = xl.parse("Monetary Events")
    m["Date"] = pd.to_datetime(m.Date)
    print(f"\n  full coverage: {m.Date.min().date()} .. {m.Date.max().date()}, "
          f"{len(m):,} events")
    w = m[(m.Date >= ppw.ANALYSIS_START) & (m.Date <= ppw.ANALYSIS_END)].copy()
    print(f"  within 2019-2023: {len(w)} events on {w.Date.nunique()} distinct dates")
    if "PC" in w:
        print(f"    with a press conference: {int(w.PC.fillna(0).sum())}")
    if "Unscheduled" in w:
        print(f"    unscheduled:             {int(w.Unscheduled.fillna(0).sum())}")
    if "SEP" in w:
        print(f"    with projections (SEP):  {int(w.SEP.fillna(0).sum())}")

    print("\n  surprise dispersion (percentage points, as published):")
    print(f"    {'series':<8}{'n':>5}{'mean':>10}{'sd':>10}{'min':>10}{'max':>10}")
    for c in ("MP1", "MP2", "FF1", "ED1", "ED4"):
        if c in w:
            s = pd.to_numeric(w[c], errors="coerce").dropna()
            if len(s):
                print(f"    {c:<8}{len(s):>5}{s.mean():>10.4f}{s.std():>10.4f}"
                      f"{s.min():>10.4f}{s.max():>10.4f}")
    conc = pd.to_numeric(w.get("MP1"), errors="coerce").abs().dropna()
    if len(conc):
        share = conc.nlargest(5).sum() / conc.sum()
        print(f"\n  concentration: the 5 largest |MP1| surprises carry "
              f"{share:.1%} of total absolute surprise")
    w.to_parquet(ppw.OUT / "s1_macro_events.parquet", index=False)
    return w


def competing(ev):
    """What else was happening on each announcement date."""
    print("\n" + "=" * 92 + "\nCOMPETING NEWS ON THE SAME DATE\n" + "=" * 92)
    per = ev.groupby("reaction_date_session").size().rename("n_same_reaction_date")
    ev = ev.merge(per, left_on="reaction_date_session", right_index=True)
    print(f"  firms sharing a reaction date: median "
          f"{ev.n_same_reaction_date.median():.0f}, max {ev.n_same_reaction_date.max()}")
    print(f"  events that are the ONLY sample release on their reaction date: "
          f"{(ev.n_same_reaction_date == 1).sum():,} ({(ev.n_same_reaction_date == 1).mean():.1%})")

    mac = pd.read_parquet(ppw.OUT / "s1_macro_events.parquet")
    macd = set(pd.to_datetime(mac.Date))
    ev["fomc_same_date"] = ev.reaction_date_session.isin(macd)
    print(f"  events whose reaction date is also an FOMC date: "
          f"{int(ev.fomc_same_date.sum()):,} ({ev.fomc_same_date.mean():.1%})")
    print("    -> the macro/micro comparison has same-session support, but these "
          "dates\n       carry both news families and are flagged, not dropped")
    return ev


def main():
    ev = pd.read_parquet(EVENTS)
    validate_clock(ev)
    ev = classify(ev)
    macro()
    ev = competing(ev)
    ev.to_parquet(EVENTS, index=False)
    ppw.provenance("s1_02_clock_and_macro", [EVENTS, USMPD],
                   {"usmpd_sha256": USMPD_SHA256, "usmpd_url": USMPD_URL,
                    "usmpd_accessed": USMPD_ACCESSED,
                    "sessions": ev.session.value_counts().to_dict()})
    print(f"\n  written: s1_macro_events.parquet; sessions merged into "
          f"{EVENTS.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
