#!/usr/bin/env python3
"""Daily earnings-response curves for source stocks and for the three ETFs.

The clock validation in stage 1 supports a session mapping, but no result here
is allowed to depend on it. Every response is estimated three times - under the
session mapping, under a fixed same-day mapping, and under a fixed next-day
mapping - and all three are printed side by side. The more significant one is
not selected, and the bracketed multi-day window is reported so that a reader
who rejects the clock entirely still has a number.

Dependence is the binding constraint on precision, not the number of events.
98.6% of ETF-event rows share their reaction date with another sample release,
and the same firm reappears every quarter, so the resampling unit is the whole
calendar date, drawn jointly across the three ETFs. Treating 13,679 ETF-event
rows as independent would overstate precision by roughly the square root of the
crowding.

Nothing here speaks to within-day ordering. A flat daily lag profile is what a
fast, well-arbitraged market looks like at this resolution; it is not evidence
that no intraday lead exists, and it is not a failed intraday project.
"""
import sys

import numpy as np
import pandas as pd

import ppw

EVENTS = ppw.OUT / "s1_earnings_events.parquet"
CONTRIB = ppw.OUT / "s2_contributions.parquet"
ETF_PERMNO = {"SPY": 84398, "XLF": 86455, "XLK": 86457}
HORIZONS = [0, 1, 2, 5, 10]
DRIFT = (2, 20)                 # reported separately, never merged into CAR(0,h)
MAPPINGS = ["reaction_date_session", "reaction_date_sameday",
            "reaction_date_nextday"]
EST_WIN = (250, 21)             # pre-event market-model window, strictly prior
B = 1000
RNG = np.random.default_rng(20260906)


def returns(permnos):
    fr = []
    for y in range(2018, 2024):
        d = pd.read_parquet(ppw.abspath(f"raw/crsp_dsf_{y}.parquet"),
                            columns=["permno", "date", "ret"])
        fr.append(d[d.permno.isin(permnos)])
    r = pd.concat(fr, ignore_index=True)
    r["date"] = pd.to_datetime(r.date)
    r["ret"] = pd.to_numeric(r.ret, errors="coerce")
    return r.dropna(subset=["ret"]).drop_duplicates(["permno", "date"])


class Cum:
    """Forward cumulative returns on the trading calendar."""

    def __init__(self, r):
        self.w = r.pivot_table(index="date", columns="permno",
                               values="ret").astype("float64")
        self.cal = self.w.index
        self.cols = {p: i for i, p in enumerate(self.w.columns)}
        v = self.w.values
        self.avail = np.isfinite(v)
        self.C = np.cumprod(1.0 + np.nan_to_num(v), axis=0)
        self.R = v

    def loc(self, dates):
        i = self.cal.searchsorted(pd.DatetimeIndex(dates), side="left")
        ok = (i < len(self.cal))
        return np.where(ok, i, 0), ok

    def car(self, permnos, dates, a, b):
        """Cumulative return over [a, b] trading days relative to the mapping."""
        i, ok = self.loc(dates)
        j = np.array([self.cols.get(p, -1) for p in permnos])
        s, e = i + a - 1, i + b
        good = ok & (j >= 0) & (s >= 0) & (e < len(self.cal))
        out = np.full(len(permnos), np.nan)
        if good.any():
            jj, ss, ee = j[good], s[good], e[good]
            base = np.where(ss < 0, 1.0, self.C[np.clip(ss, 0, None), jj])
            out[good] = self.C[ee, jj] / base - 1.0
            # an event is dropped if the security is missing anywhere in the span
            miss = np.array([not self.avail[x + 1:y + 1, c].all()
                             for x, y, c in zip(ss, ee, jj)])
            out[np.where(good)[0][miss]] = np.nan
        return out


def market_model(cum, ev, dsi):
    """Alpha and beta estimated only on data before each event."""
    m = dsi.set_index("date").ret.reindex(cum.cal).values
    ab = {}
    for pn, dt in set(zip(ev.permno, ev.event_date)):
        i = cum.cal.searchsorted(dt)
        j = cum.cols.get(pn, -1)
        lo, hi = i - EST_WIN[0], i - EST_WIN[1]
        if j < 0 or lo < 0 or hi - lo < 100:
            continue
        y, x = cum.R[lo:hi, j], m[lo:hi]
        k = np.isfinite(y) & np.isfinite(x)
        if k.sum() < 100:
            continue
        b = np.polyfit(x[k], y[k], 1)
        ab[(pn, dt)] = (float(b[1]), float(b[0]))
    return ab, m


def ols_block(y, x, dates, label):
    """Slope with a date-block bootstrap; the date is the resampling unit."""
    k = np.isfinite(y) & np.isfinite(x)
    y, x, dates = y[k], x[k], np.asarray(dates)[k]
    if len(y) < 30:
        return None
    b = np.polyfit(x, y, 1)[0]
    idx = pd.Series(np.arange(len(y))).groupby(pd.Series(dates)).apply(
        lambda s: s.values)
    blocks = list(idx.values)
    draws = np.empty(B)
    for t in range(B):
        pick = RNG.integers(0, len(blocks), len(blocks))
        sel = np.concatenate([blocks[p] for p in pick])
        draws[t] = np.polyfit(x[sel], y[sel], 1)[0] if len(set(x[sel])) > 1 else np.nan
    lo, hi = np.nanpercentile(draws, [2.5, 97.5])
    return {"label": label, "n": int(len(y)), "n_dates": int(len(blocks)),
            "beta": float(b), "lo": float(lo), "hi": float(hi),
            "se": float(np.nanstd(draws))}


def leverage(ev, cum):
    """How much of the OLS slope a handful of penny-priced names carry.

    The surprise scale divides an EPS difference by the pre-event price, so a
    sub-dollar stock with a large miss produces a surprise of several hundred
    percent of price. Those events are real and stay in the sample; the point
    is that an OLS slope estimated across them is a statement about two firms,
    not about the 597 in the registry. No observation is winsorised or dropped
    to make the slope behave.
    """
    print("\n" + "=" * 92 + "\nLEVERAGE IN THE RAW SLOPE\n" + "=" * 92)
    s = ev.s.values
    lev = (s - s.mean()) ** 2
    o = np.argsort(-np.abs(s))
    print(f"  |surprise| > 5% of price: {(np.abs(s) > 5).sum()} events; "
          f"> 25%: {(np.abs(s) > 25).sum()}")
    for k in (2, 5, 10, 50):
        print(f"  top {k:>2} events by |surprise| carry "
              f"{lev[o[:k]].sum()/lev.sum():>6.1%} of total regressor variance")
    top = ev.iloc[o[:5]]
    print("\n  the extreme names:")
    for r in top.itertuples(index=False):
        print(f"    {str(r.cname)[:28]:<30}permno {r.permno:<8}"
              f"{str(r.event_date.date()):<12}pre-event price "
              f"{r.prc_pre:>8.2f}  surprise {r.s:>9.1f}% of price")


def deciles(ev, cum):
    """Mean response by surprise decile - the tail-robust descriptive.

    Deciles are formed on the same fixed pre-event scale used everywhere else,
    so this is a different summary of the same variable, not a different
    variable and not a re-chosen specification.
    """
    print("\n" + "=" * 92 + "\nRESPONSE BY SURPRISE DECILE (TAIL-ROBUST DESCRIPTIVE)"
          + "\n" + "=" * 92)
    d = ev.dropna(subset=["reaction_date_session"]).copy()
    d["dec"] = pd.qcut(d.s.rank(method="first"), 10, labels=False) + 1
    for mp in MAPPINGS:
        dd = d.dropna(subset=[mp])
        cars = {h: cum.car(dd.permno.values, dd[mp].values, 0, h) * 10000
                for h in HORIZONS}
        t = pd.DataFrame({"dec": dd.dec.values, "s": dd.s.values, **cars})
        g = t.groupby("dec").agg(n=("s", "size"), s_med=("s", "median"),
                                 **{f"h{h}": (h, "mean") for h in HORIZONS})
        print(f"\n  mapping: {mp.replace('reaction_date_', '')}   "
              f"(mean CAR in bps)")
        print(f"  {'dec':<5}{'n':>7}{'surprise%':>11}" +
              "".join(f"{'h='+str(h):>10}" for h in HORIZONS))
        for i, r in g.iterrows():
            print(f"  {int(i):<5}{int(r.n):>7,}{r.s_med:>11.4f}" +
                  "".join(f"{r['h'+str(h)]:>10.1f}" for h in HORIZONS))
        hi, lo = g.loc[10], g.loc[1]
        print("  " + "-" * 60)
        print(f"  {'D10-D1':<5}{'':>7}{'':>11}" +
              "".join(f"{hi['h'+str(h)]-lo['h'+str(h)]:>10.1f}" for h in HORIZONS))


def curve(rows, title, note):
    print("\n" + "=" * 92 + f"\n{title}\n" + "=" * 92)
    print(f"  {note}")
    print(f"\n  {'mapping':<12}{'h':>4}{'n':>8}{'dates':>7}{'beta':>12}"
          f"{'95% block CI':>26}{'sig':>5}")
    print("-" * 92)
    for r in rows:
        if r is None:
            continue
        mp, h = r["label"]
        sig = "*" if (r["lo"] > 0) or (r["hi"] < 0) else ""
        print(f"  {mp:<12}{h:>4}{r['n']:>8,}{r['n_dates']:>7,}{r['beta']:>12.2f}"
              f"   [{r['lo']:>9.2f}, {r['hi']:>9.2f}]{sig:>5}")
    print("-" * 92)


def main():
    ev = pd.read_parquet(EVENTS)
    j = pd.read_parquet(CONTRIB)
    permnos = set(ev.permno.astype(int)) | set(ETF_PERMNO.values())
    r = returns(permnos)
    dsi = pd.read_parquet(ppw.abspath("raw/crsp_dsi.parquet"),
                          columns=["date", "vwretd"])
    dsi["date"] = pd.to_datetime(dsi.date)
    dsi["ret"] = pd.to_numeric(dsi.vwretd, errors="coerce")
    cum = Cum(r)

    # Fixed surprise scale, normalised only on pre-event information: the
    # actual-minus-consensus difference over the price five trading days
    # before the release, expressed in percent of price.
    ev = ev.dropna(subset=["surprise_scaled"]).copy()
    ev["s"] = ev.surprise_scaled * 100.0
    print("=" * 92 + "\nEARNINGS RESPONSE, SETUP\n" + "=" * 92)
    print(f"  events with a scaled surprise: {len(ev):,} over "
          f"{ev.event_date.nunique():,} dates, {ev.permno.nunique():,} firms")
    q = ev.s.quantile([.01, .25, .5, .75, .99])
    print(f"  surprise (% of pre-event price): p1 {q.iloc[0]:.4f}  p25 "
          f"{q.iloc[1]:.4f}  p50 {q.iloc[2]:.4f}  p75 {q.iloc[3]:.4f}  "
          f"p99 {q.iloc[4]:.4f}")
    print(f"  positive surprises: {(ev.s > 0).mean():.1%}   "
          f"exactly zero: {(ev.s == 0).mean():.1%}")
    print("  the scale is fixed here and never re-chosen after seeing a response")

    # ---------------- source stocks, raw signed response ----------------
    rows = []
    for mp in MAPPINGS:
        d = ev.dropna(subset=[mp])
        for h in HORIZONS:
            y = cum.car(d.permno.values, d[mp].values, 0, h) * 10000
            rows.append(ols_block(y, d.s.values, d[mp].values,
                                  (mp.replace("reaction_date_", ""), h)))
    curve(rows, "SOURCE-STOCK RESPONSE, CAR(0,h) IN BPS PER 1% SURPRISE",
          "raw signed returns; all three reaction-date mappings shown, none selected")
    leverage(ev, cum)
    deciles(ev, cum)

    drift = []
    for mp in MAPPINGS:
        d = ev.dropna(subset=[mp])
        y = cum.car(d.permno.values, d[mp].values, *DRIFT) * 10000
        drift.append(ols_block(y, d.s.values, d[mp].values,
                               (mp.replace("reaction_date_", ""), "+2..+20")))
    curve(drift, "SOURCE-STOCK POST-EVENT DRIFT [+2,+20], REPORTED SEPARATELY",
          "a distinct interval, never folded into CAR(0,h) and never used as a divisor")

    # ---------------- pre-event factor-adjusted diagnostic ----------------
    ab, mret = market_model(cum, ev, dsi)
    print("\n  pre-event market-model coverage: "
          f"{len(ab):,} of {len(set(zip(ev.permno, ev.event_date))):,} "
          f"(alpha, beta) pairs estimated on [-{EST_WIN[0]}, -{EST_WIN[1]}]")
    fa = []
    mp = "reaction_date_session"
    d = ev.dropna(subset=[mp]).copy()
    key = list(zip(d.permno, d.event_date))
    d["a"] = [ab.get(k, (np.nan, np.nan))[0] for k in key]
    d["b"] = [ab.get(k, (np.nan, np.nan))[1] for k in key]
    i, ok = cum.loc(d[mp].values)
    for h in HORIZONS:
        y = cum.car(d.permno.values, d[mp].values, 0, h) * 10000
        mkt = np.array([np.nansum(mret[a:a + h + 1]) for a in i])
        fa.append(ols_block(y - (d.a.values * (h + 1) + d.b.values * mkt) * 10000,
                            d.s.values, d[mp].values, ("factor-adj", h)))
    curve(fa, "SOURCE-STOCK RESPONSE, PRE-EVENT FACTOR-ADJUSTED (DIAGNOSTIC)",
          "accompanies the raw baseline; it does not replace it")

    # ---------------- ETF panel on the aggregated surprise ----------------
    print("\n" + "=" * 92 + "\nETF DAILY PANEL: AGGREGATED WEIGHTED SURPRISE\n"
          + "=" * 92)
    print("  S(f,d) = sum over announcing holdings of prior-snapshot weight x")
    print("  signed surprise, summed to the ETF reaction date. Source-event")
    print("  detail is preserved in s2_contributions.parquet.")
    j = j.dropna(subset=["surprise_scaled"]).copy()
    j["s"] = j.surprise_scaled * 100.0
    j["ws"] = j.weight * j.s
    agg = (j.groupby(["etf", "reaction_date_session"])
             .agg(S=("ws", "sum"), n_ann=("permno", "nunique"),
                  w_ann=("weight", "sum")).reset_index()
             .rename(columns={"reaction_date_session": "date"}))
    print(f"\n  ETF-date cells: {len(agg):,} over {agg.date.nunique():,} "
          f"distinct dates")
    print(f"  announcers per cell: median {agg.n_ann.median():.0f}, "
          f"max {agg.n_ann.max()}")
    print(f"  announcing weight per cell: median {agg.w_ann.median():.2%}, "
          f"p95 {agg.w_ann.quantile(.95):.2%}, max {agg.w_ann.max():.2%}")
    print(f"  S dispersion: sd {agg.S.std():.6f}, "
          f"p5 {agg.S.quantile(.05):.6f}, p95 {agg.S.quantile(.95):.6f}")

    agg["permno"] = agg.etf.map(ETF_PERMNO)
    erows = []
    for h in HORIZONS:
        y = cum.car(agg.permno.values, agg.date.values, 0, h) * 10000
        erows.append(ols_block(y, agg.S.values * 100, agg.date.values,
                               ("etf-agg", h)))
    y = cum.car(agg.permno.values, agg.date.values, *DRIFT) * 10000
    erows.append(ols_block(y, agg.S.values * 100, agg.date.values,
                           ("etf-agg", "+2..+20")))
    curve(erows, "ETF RESPONSE TO THE AGGREGATED WEIGHTED SURPRISE",
          "resampled by whole calendar date jointly across the three ETFs; "
          "duplicated\n  ETF-date rows are not treated as independent shocks")

    print("\n  same specification with each ETF alone (dependence unchanged):")
    print(f"  {'etf':<6}{'h':>4}{'n':>7}{'beta':>12}{'95% block CI':>26}")
    per = []
    for etf, g in agg.groupby("etf"):
        for h in (0, 1):
            y = cum.car(g.permno.values, g.date.values, 0, h) * 10000
            o = ols_block(y, g.S.values * 100, g.date.values, (etf, h))
            if o:
                per.append({**o, "etf": etf, "h": h})
                print(f"  {etf:<6}{h:>4}{o['n']:>7,}{o['beta']:>12.2f}"
                      f"   [{o['lo']:>9.2f}, {o['hi']:>9.2f}]")

    out = pd.DataFrame([x for x in rows + drift + fa + erows if x])
    out["mapping"] = [l[0] for l in out.label]
    out["h"] = [str(l[1]) for l in out.label]
    out = out.drop(columns=["label"])
    out.to_parquet(ppw.OUT / "s3_response.parquet", index=False)
    agg.to_parquet(ppw.OUT / "s3_etf_daily_panel.parquet", index=False)
    ppw.provenance("s3_02_response", [EVENTS, CONTRIB],
                   {"bootstrap_reps": B, "horizons": HORIZONS,
                    "drift": list(DRIFT), "mappings": MAPPINGS,
                    "etf_date_cells": int(len(agg))})
    print("\n" + "=" * 92)
    print("  A daily response coefficient measures how much of a surprise is")
    print("  reflected by a day's close. It does not order the ETF against its")
    print("  constituents inside the day, and a wide or zero-centred interval")
    print("  here is inconclusive about intraday leadership, not evidence")
    print("  against it.")
    print("  written: s3_response.parquet, s3_etf_daily_panel.parquet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
