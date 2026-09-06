#!/usr/bin/env python3
"""Extract the three portfolios' holdings, then walk one earnings event end to end.

Running one event by hand before running hundreds is what catches the errors
that survive schema checks: a weight read from the wrong snapshot, a surprise
whose actual and estimate are on different split bases, a link resolved to the
right company in the wrong decade. If the single event does not survive
inspection, nothing built on top of it will.

The event is chosen here for size and clarity of the mechanics, before any
response has been estimated. It is a plumbing test, not a result.
"""
import glob
import sys

import pandas as pd
import pyarrow.parquet as pq

import ppw

PORTNO = {"SPY": 1021980.0, "XLF": 1026006.0, "XLK": 1026008.0}
PERMNO = {"SPY": 84398, "XLF": 86455, "XLK": 86457}
HOLD_OUT = ppw.OUT / "holdings_three_etfs.parquet"
HOLD_COLS = ["crsp_portno", "report_dt", "eff_dt", "percent_tna", "nbr_shares",
             "market_val", "security_name", "cusip", "permno", "ticker",
             "security_rank", "maturity_dt"]


def extract_holdings():
    """Read only our three portfolios out of the batched holdings tree."""
    if HOLD_OUT.exists():
        h = pd.read_parquet(HOLD_OUT)
        print(f"  reusing checkpoint: {len(h):,} rows")
        return h
    years = range(2018, 2024)          # 2018 gives a pre-2019 prior snapshot
    parts = sorted(p for y in years for p in glob.glob(str(ppw.abspath(
        f"raw/rescue_remaining/crsp_holdings_etf_{y}_b*/part_*.parquet"))))
    print(f"  scanning {len(parts):,} holdings parts for 3 portfolios")
    keep, hit_files = [], 0
    for i, f in enumerate(parts, 1):
        pf = pq.ParquetFile(f)
        cols = [c for c in HOLD_COLS if c in pf.schema_arrow.names]
        d = pd.read_parquet(f, columns=cols)
        d = d[d.crsp_portno.isin(PORTNO.values())]
        if len(d):
            keep.append(d)
            hit_files += 1
        if i % 500 == 0:
            print(f"    {i:,}/{len(parts):,} parts, {hit_files} with our portfolios")
    h = pd.concat(keep, ignore_index=True)
    h["report_dt"] = pd.to_datetime(h.report_dt)
    h["eff_dt"] = pd.to_datetime(h.eff_dt)
    inv = {v: k for k, v in PORTNO.items()}
    h["etf"] = h.crsp_portno.map(inv)
    tmp = HOLD_OUT.with_suffix(".tmp")
    h.to_parquet(tmp, index=False)
    tmp.replace(HOLD_OUT)
    print(f"  {hit_files} parts contained our portfolios -> {len(h):,} rows")
    return h


def describe_holdings(h):
    print("\n" + "-" * 92)
    print(f"{'etf':<5}{'snapshots':>10}{'rows':>9}{'first':>13}{'last':>13}"
          f"{'permno%':>9}{'tna sum':>9}")
    print("-" * 92)
    for etf, d in h.groupby("etf"):
        snaps = d.groupby(["report_dt", "eff_dt"]).ngroups
        tna = d.groupby(["report_dt", "eff_dt"]).percent_tna.sum().median()
        print(f"{etf:<5}{snaps:>10}{len(d):>9,}"
              f"{str(d.report_dt.min().date()):>13}{str(d.report_dt.max().date()):>13}"
              f"{d.permno.notna().mean():>8.1%}{tna:>9.1f}")
    print("-" * 92)
    g = h.groupby(["etf", "report_dt"]).eff_dt.nunique()
    print(f"  eff_dt per (etf, report_dt): max={g.max()}, "
          f"{(g > 1).mean():.1%} of report dates carry more than one")
    if g.max() > 1:
        ex = g[g > 1].head(1)
        e, r = ex.index[0]
        sub = h[(h.etf == e) & (h.report_dt == r)]
        print(f"    example {e} report_dt={r.date()}: eff_dt="
              f"{sorted(str(x.date()) for x in sub.eff_dt.unique())}")
        print("    -> the snapshot unit is (portno, report_dt, eff_dt), not report_dt")


def one_event(h):
    """Walk a single large-cap earnings announcement through the whole chain."""
    print("\n" + "=" * 92 + "\nSINGLE EVENT ROUND TRIP\n" + "=" * 92)

    # 1. pick the largest XLK position at the last snapshot before mid-2021
    snap = h[(h.etf == "XLK") & (h.report_dt <= "2021-06-30")]
    last = snap.report_dt.max()
    snap = snap[snap.report_dt == last]
    snap = snap[snap.eff_dt == snap.eff_dt.max()]
    top = snap.sort_values("percent_tna", ascending=False).iloc[1]
    print(f"  snapshot        XLK report_dt={last.date()} eff_dt={top.eff_dt.date()}")
    print(f"  position        {top.security_name} ticker={top.ticker} "
          f"permno={top.permno:.0f} weight={top.percent_tna / 100:.4%}")

    # 2. resolve the I/B/E/S ticker through the dated link, not by ticker text
    lk = pd.read_parquet(ppw.abspath("raw/crsp_ibes_link_full.parquet"))
    lk["sdate"] = pd.to_datetime(lk.sdate)
    lk["edate"] = pd.to_datetime(lk.edate)
    cand = lk[(lk.permno == int(top.permno))]
    print(f"  link rows for permno {int(top.permno)}: {len(cand)} "
          f"({sorted(cand.ticker.unique())}, score {sorted(cand.score.unique())})")

    # 3. the first actual EPS announced after the snapshot
    act = pd.read_parquet(ppw.abspath("raw/ibes_actuals_eps_2021.parquet"))
    act["anndats"] = pd.to_datetime(act.anndats)
    act = act[act.ticker.isin(cand.ticker) & (act.pdicity == "QTR")
              & (act.measure == "EPS") & (act.curr_act == "USD")]
    live = cand.set_index("ticker")
    act = act[[bool(((live.loc[[t]].sdate <= d) & (live.loc[[t]].edate >= d)).any())
               for t, d in zip(act.ticker, act.anndats)]]
    act = act[act.anndats > last].sort_values("anndats")
    if act.empty:
        print("  NO eligible actual found after the snapshot")
        return
    e = act.iloc[0]
    print(f"  actual          pends={e.pends} anndats={e.anndats.date()} "
          f"anntims={e.anntims} value={e.value} curr={e.curr_act}")
    print(f"  link check      interval covers anndats -> permno {int(top.permno)} "
          f"confirmed for THIS date, not assumed from the ticker")

    # 4. pre-release consensus: the last summary snapshot strictly before release
    su = None
    for p in sorted(glob.glob(str(ppw.abspath("raw/ibes_statsum*2021*.parquet")))
                    + glob.glob(str(ppw.abspath("raw/ibes_statsumu*.parquet")))):
        pf = pq.ParquetFile(p)
        if "statpers" in pf.schema_arrow.names:
            su = p
            break
    print(f"  consensus file  {su.split('/')[-1] if su else 'NOT RESOLVED HERE'}")

    # 5. daily returns around the announcement, from the selected primary source
    dsf = pd.read_parquet(ppw.abspath("raw/crsp_dsf_2021.parquet"),
                          columns=["permno", "date", "ret", "retx", "prc"])
    dsf["date"] = pd.to_datetime(dsf.date)
    win = dsf[(dsf.permno == int(top.permno))
              & (dsf.date >= e.anndats - pd.Timedelta(days=4))
              & (dsf.date <= e.anndats + pd.Timedelta(days=6))].sort_values("date")
    print("\n  daily returns around the release "
          "(h is ambiguous until the clock is verified):")
    for r in win.itertuples(index=False):
        tag = "  <- anndats" if r.date == e.anndats else ""
        print(f"    {r.date.date()}  ret={r.ret:+.4f}  retx={r.retx:+.4f}{tag}")

    same = win[win.date == e.anndats]
    nxt = win[win.date > e.anndats]
    if len(same) and len(nxt):
        r0, r1 = float(same.ret.iloc[0]), float(nxt.ret.iloc[0])
        w = top.percent_tna / 100
        print(f"\n  contribution_bps = 10000 * w * source_return")
        print(f"    same-day mapping  w={w:.4%} r={r0:+.4f} -> "
              f"{10000 * w * r0:+.3f} bps")
        print(f"    next-day mapping  w={w:.4%} r={r1:+.4f} -> "
              f"{10000 * w * r1:+.3f} bps")
        print("    the two mappings differ; with the clock unverified BOTH are "
              "reported, neither is chosen")

    # 6. the ETF's own return on those days, for scale
    etf = dsf[(dsf.permno == PERMNO["XLK"])
              & (dsf.date.isin(win.date))].sort_values("date")
    print("\n  XLK own daily return on the same days:")
    for r in etf.itertuples(index=False):
        print(f"    {r.date.date()}  ret={r.ret:+.4f}")


def main():
    h = extract_holdings()
    describe_holdings(h)
    one_event(h)
    ppw.provenance("s7_03_selected_event", [HOLD_OUT],
                   {"holdings_rows": int(len(h)),
                    "portnos": {k: v for k, v in PORTNO.items()}})
    print(f"\n  checkpoint: {HOLD_OUT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
