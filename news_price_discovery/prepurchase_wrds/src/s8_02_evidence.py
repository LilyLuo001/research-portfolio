#!/usr/bin/env python3
"""Constituent sets, weight provenance, corporate-action flags and quote windows
for the six selected measurement-validation events.

Complete baskets only. An announcing-stock-plus-ETF extract cannot produce the
ETF-minus-portfolio difference that is the registered outcome, so the full
constituent set of the governing snapshot is carried for every event.
"""
import sys

import numpy as np
import pandas as pd

import ppw

ETF_PERMNO = {"SPY": 84398, "XLK": 86457, "XLF": 86455}
CASH_PAT = (r"CASH|MONEY MARKET|MM FD|LIQ RES|LIQUIDITY|TREASURY BILL|REPO")
MAX_AGE = 120
N_CONTROL = 3
PRE_M, POST_M, BASE_M = 5, 15, 60      # minutes
REG_OPEN, REG_CLOSE = pd.Timedelta("9:30:00"), pd.Timedelta("16:00:00")


def calendar():
    d = pd.read_parquet(ppw.abspath("raw/crsp_dsi.parquet"), columns=["date"])
    return pd.DatetimeIndex(sorted(pd.to_datetime(d.date).dt.normalize().unique()))


def snapshots():
    """Holdings folded to one complete portfolio per (etf, report_dt)."""
    h = pd.read_parquet(ppw.OUT / "holdings_three_etfs.parquet")
    h["report_dt"] = pd.to_datetime(h.report_dt)
    h["eff_dt"] = pd.to_datetime(h.eff_dt)
    h["weight"] = h.percent_tna / 100.0
    h = h.sort_values("eff_dt").drop_duplicates(
        ["etf", "report_dt", "security_name", "cusip"], keep="last").copy()
    h["avail_dt"] = h.groupby(["etf", "report_dt"]).eff_dt.transform("max")
    h["is_cash"] = h.security_name.fillna("").str.upper().str.contains(CASH_PAT,
                                                                      regex=True)
    return h


def govern(h, etf, event_date):
    """Latest snapshot of `etf` demonstrably available before `event_date`."""
    g = h[(h.etf == etf) & (h.avail_dt < event_date)]
    if not len(g):
        return None
    rdt = g.report_dt.max()
    g = g[g.report_dt == rdt]
    age = (event_date - rdt).days
    return None if age > MAX_AGE else (rdt, g.avail_dt.max(), age, g)


def coverage(g):
    tot = g.weight.sum()
    cash = g[g.is_cash].weight.sum()
    eq = g[(~g.is_cash) & g.permno.notna()]
    unmapped = g[(~g.is_cash) & g.permno.isna()].weight.sum()
    return {"reported_tna_sum": tot, "equity_mapped": eq.weight.sum(),
            "cash": cash, "unmapped_missing_mass": unmapped,
            "n_lines": len(g), "n_mapped_permno": eq.permno.nunique()}


def corp_actions(permnos, dates):
    """cfacpr / cfacshr changes around each event date: split or distribution."""
    yrs = sorted({d.year for d in dates})
    fr = []
    for y in yrs:
        d = pd.read_parquet(ppw.abspath(f"raw/crsp_dsf_{y}.parquet"),
                            columns=["permno", "date", "cfacpr", "cfacshr"])
        fr.append(d[d.permno.isin(permnos)])
    d = pd.concat(fr, ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    out = []
    for ed in dates:
        w = d[(d.date >= ed - pd.Timedelta("5D")) & (d.date <= ed + pd.Timedelta("5D"))]
        g = w.groupby("permno")[["cfacpr", "cfacshr"]].nunique()
        hit = g[(g.cfacpr > 1) | (g.cfacshr > 1)]
        out.append({"event_date": ed, "n_checked": w.permno.nunique(),
                    "n_with_action": len(hit),
                    "permnos": sorted(hit.index.astype(int).tolist())[:20]})
    return pd.DataFrame(out)


def merge_intervals(d):
    """Union of quote intervals per (security, date); overlaps counted once."""
    d = d.sort_values(["sec_permno", "date", "win_start"])
    keep, cur = [], None
    for r in d.itertuples(index=False):
        if cur and r.sec_permno == cur["sec_permno"] and r.date == cur["date"] \
                and r.win_start <= cur["win_end"]:
            cur["win_end"] = max(cur["win_end"], r.win_end)
            cur["roles"] = cur["roles"] | {r.role}
            cur["events"] = cur["events"] | {r.event_key}
        else:
            if cur:
                keep.append(cur)
            cur = {"sec_permno": r.sec_permno, "date": r.date,
                   "win_start": r.win_start, "win_end": r.win_end,
                   "roles": {r.role}, "events": {r.event_key}}
    if cur:
        keep.append(cur)
    o = pd.DataFrame(keep)
    o["roles"] = o.roles.map(lambda s: ",".join(sorted(s)))
    o["events"] = o.events.map(lambda s: ",".join(sorted(s)))
    o["extended_session"] = ~((o.win_start >= REG_OPEN) & (o.win_end <= REG_CLOSE))
    return o


def main():
    cal = calendar()
    six = pd.read_parquet(ppw.OUT / "s8_six_events.parquet")
    h = snapshots()

    cons, wins, cov_rows = [], [], []
    for _, ev in six.iterrows():
        ed = pd.Timestamp(ev.event_date)
        etfs = list(ETF_PERMNO) if ev.etf == "ALL_THREE" else [ev.etf]
        t = pd.Timedelta(str(ev.clock_raw).split()[-1])
        ctrl = [d for d in cal[cal < ed][::-1]
                if d not in set(pd.to_datetime(six.event_date))][:N_CONTROL]

        for etf in etfs:
            gv = govern(h, etf, ed)
            if gv is None:
                print(f"  !! {ev.key} {etf}: no snapshot inside {MAX_AGE}d")
                continue
            rdt, adt, age, g = gv
            c = coverage(g)
            c |= {"event_key": ev.key, "etf": etf, "event_date": ed,
                  "report_dt": rdt, "avail_dt": adt, "report_age_days": age}
            cov_rows.append(c)

            eq = g[(~g.is_cash) & g.permno.notna()].copy()
            eq["event_key"], eq["event_date"] = ev.key, ed
            cons.append(eq[["event_key", "etf", "event_date", "permno", "cusip",
                            "ticker", "security_name", "weight", "report_dt",
                            "avail_dt"]])

            secs = [(int(p), "constituent") for p in eq.permno.unique()]
            secs.append((ETF_PERMNO[etf], "etf"))
            if pd.notna(ev.permno):
                secs = [(p, "announcer" if p == int(ev.permno) else r)
                        for p, r in secs]
            for d, wt in [(ed, "event")] + [(c, "control") for c in ctrl]:
                for p, role in secs:
                    wins.append({"event_key": ev.key, "sec_permno": p,
                                 "role": role, "date": d, "window_type": wt,
                                 "win_start": t - pd.Timedelta(minutes=PRE_M),
                                 "win_end": t + pd.Timedelta(minutes=POST_M)})
                    wins.append({"event_key": ev.key, "sec_permno": p,
                                 "role": role, "date": d,
                                 "window_type": "baseline",
                                 "win_start": t - pd.Timedelta(minutes=BASE_M),
                                 "win_end": t - pd.Timedelta(minutes=PRE_M)})

    cons = pd.concat(cons, ignore_index=True)
    cv = pd.DataFrame(cov_rows)
    raw = pd.DataFrame(wins)
    mg = merge_intervals(raw)

    print("\n  === weight provenance and coverage per event-ETF ===")
    for _, r in cv.iterrows():
        print(f"    {r.event_key:<30s} {r.etf:<4s} report_dt={str(r.report_dt)[:10]} "
              f"avail={str(r.avail_dt)[:10]} age={r.report_age_days:>3d}d "
              f"lines={r.n_lines:>4d} permno={r.n_mapped_permno:>4d}")
        print(f"       equity mapped {r.equity_mapped:7.4%} | cash {r.cash:7.4%} "
              f"| MISSING MASS {r.unmapped_missing_mass:7.4%} "
              f"| reported sum {r.reported_tna_sum:7.4%}")

    ca = corp_actions(set(cons.permno.astype(int)),
                      sorted(set(pd.to_datetime(six.event_date))))
    print("\n  === corporate actions within +/-5 sessions of each event date ===")
    for _, r in ca.iterrows():
        print(f"    {str(r.event_date)[:10]}  checked {r.n_checked:>4d} securities, "
              f"cfacpr/cfacshr change in {r.n_with_action}  {r.permnos if r.n_with_action else ''}")

    print("\n  === quote windows ===")
    print(f"    raw security-window rows      {len(raw):>7d}")
    print(f"    after dedup/overlap merge     {len(mg):>7d}")
    print(f"    distinct securities           {mg.sec_permno.nunique():>7d}")
    print(f"    distinct dates                {mg.date.nunique():>7d}")
    print(f"    security-days                 {len(mg.groupby(['sec_permno','date'])):>7d}")
    print(f"    extended-session intervals    {mg.extended_session.sum():>7d} "
          f"({mg.extended_session.mean():.1%})")
    tot_min = ((mg.win_end - mg.win_start).dt.total_seconds() / 60).sum()
    print(f"    total quote-minutes requested {tot_min:>7,.0f}")

    for f, d in [("s8_constituents", cons), ("s8_coverage", cv),
                 ("s8_windows", mg), ("s8_corp_actions", ca)]:
        d.to_parquet(ppw.OUT / f"{f}.parquet", index=False)
    ppw.provenance("s8_02_evidence",
                   [ppw.OUT / "s8_six_events.parquet",
                    ppw.OUT / "holdings_three_etfs.parquet"],
                   {"events": len(six), "merged_intervals": len(mg),
                    "securities": int(mg.sec_permno.nunique()),
                    "max_missing_mass": float(cv.unmapped_missing_mass.max())})
    print(f"\n  wrote 4 tables to {ppw.OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
