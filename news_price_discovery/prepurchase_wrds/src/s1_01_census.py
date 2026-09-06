#!/usr/bin/env python3
"""Event registry and ETF/security crosswalk for the three bounded instruments.

The source-stock universe is whatever SPY, XLK, and XLF actually reported
holding between 2018 and 2023 — not today's constituents, and not the archive's
wider fund population. Membership is dated, because a firm that entered XLK in
2022 has no XLK exposure to an announcement it made in 2019.

Expectations and actuals are taken from the same I/B/E/S summary row. That is
deliberate: the row carries one `estflag` and one `curcode`, so the consensus
and the realised number are guaranteed to share a split and adjustment basis.
Pairing an actuals-file value against a separately pulled summary estimate is
the standard way to end up with a surprise that is really a stock split.

Announcement timing is left unresolved. `anntims` is populated but its timezone
is unverified in the archive, so this stage records the raw stamp, publishes a
date-level census, and refuses to emit a session label it cannot support.
"""
import glob
import sys

import numpy as np
import pandas as pd

import ppw

HOLD = ppw.OUT / "holdings_three_etfs.parquet"
XWALK = ppw.OUT / "s1_etf_security_crosswalk.parquet"
EVENTS = ppw.OUT / "s1_earnings_events.parquet"
YEARS = range(2019, 2024)
CONSENSUS_MAX_AGE_DAYS = 100   # one quarterly cycle plus slack; registered, fixed


def crosswalk():
    """Dated ETF-to-source-security membership, one row per (etf, permno, snapshot)."""
    h = pd.read_parquet(HOLD)
    h = h[h.permno.notna()].copy()
    h["permno"] = h.permno.astype(int)
    h["weight"] = h.percent_tna / 100.0
    # A PERMNO can appear on several holdings lines in one snapshot; the
    # portfolio weight on that security is their sum, not any single line.
    x = (h.groupby(["etf", "crsp_portno", "report_dt", "eff_dt", "permno"], as_index=False)
           .agg(weight=("weight", "sum"),
                n_lines=("weight", "size"),
                market_val=("market_val", "sum"),
                security_name=("security_name", "first"),
                ticker=("ticker", "first")))
    x["source"] = "crsp.holdings via rescue_remaining/crsp_holdings_etf_YYYY_b*"
    x.to_parquet(XWALK, index=False)

    print("=" * 92 + "\nETF / SECURITY CROSSWALK\n" + "=" * 92)
    print(f"{'etf':<5}{'snapshots':>10}{'rows':>9}{'securities':>12}"
          f"{'med holdings':>14}{'top weight':>12}{'top5 wt':>10}")
    print("-" * 92)
    for etf, d in x.groupby("etf"):
        per = d.groupby(["report_dt", "eff_dt"])
        top = per.weight.max().median()
        top5 = per.weight.apply(lambda s: s.nlargest(5).sum()).median()
        print(f"{etf:<5}{per.ngroups:>10}{len(d):>9,}{d.permno.nunique():>12}"
              f"{per.size().median():>14.0f}{top:>11.2%}{top5:>10.2%}")
    print("-" * 92)
    print(f"  union of source securities across all three: {x.permno.nunique():,} PERMNOs")
    ov = x.groupby("permno").etf.nunique().value_counts().sort_index()
    print("  securities held by n of the three ETFs: "
          + ", ".join(f"{n}->{c:,}" for n, c in ov.items()))
    return x


def earnings(universe):
    """Quarterly EPS events with the last consensus published before release."""
    frames = []
    for y in YEARS:
        s = pd.read_parquet(ppw.abspath(f"raw/ibes_statsum_eps_{y}.parquet"))
        frames.append(s[(s.fiscalp == "QTR") & (s.measure == "EPS")
                        & (s.usfirm == 1) & (s.curcode == "USD")
                        & (s.curr_act == "USD")])
    s = pd.concat(frames, ignore_index=True)
    for c in ("statpers", "fpedats", "anndats_act", "actdats_act"):
        s[c] = pd.to_datetime(s[c])
    s = s.dropna(subset=["actual", "anndats_act", "meanest", "medest"])
    n_all = len(s)

    # The consensus must predate the release it is meant to be surprised by.
    s = s[s.statpers < s.anndats_act]
    ev = (s.sort_values("statpers")
            .groupby(["ticker", "fpedats"], as_index=False).last())
    print(f"\n  summary rows 2019-2023 (QTR/EPS/USD, actual present): {n_all:,}")
    print(f"  after requiring statpers < anndats_act:                 {len(s):,}")
    print(f"  latest pre-release consensus per (ticker, fiscal end):  {len(ev):,}")

    lag = (ev.anndats_act - ev.statpers).dt.days
    print(f"  consensus age at release: median {lag.median():.0f}d, "
          f"p90 {lag.quantile(.9):.0f}d, max {lag.max()}d")
    # "Latest before release" is not the same as "legitimate". Where the summary
    # series stops long before the release, the last surviving snapshot is a
    # stale forecast of a different information set, not a pre-release consensus.
    # The cap is a registered project choice, fixed before any response is seen.
    stale = ev[lag > CONSENSUS_MAX_AGE_DAYS]
    ev = ev[lag <= CONSENSUS_MAX_AGE_DAYS]
    print(f"  consensus older than {CONSENSUS_MAX_AGE_DAYS}d dropped to a ledger: "
          f"{len(stale):,} ({len(stale)/(len(stale)+len(ev)):.1%})")

    # Effective-dated link. Never ticker alone.
    lk = pd.read_parquet(ppw.abspath("raw/crsp_ibes_link_full.parquet"))
    lk["sdate"] = pd.to_datetime(lk.sdate)
    lk["edate"] = pd.to_datetime(lk.edate)
    # 7,337 of the link's 37,662 rows carry no PERMNO at all, and 760 carry no
    # edate. A missing PERMNO is a link that does not resolve, so it is logged
    # rather than filled; a missing edate is read as an open-ended interval,
    # which is how CRSP marks a link still current at extract time.
    print(f"  link rows lacking a permno: {int(lk.permno.isna().sum()):,}; "
          f"lacking an edate: {int(lk.edate.isna().sum()):,} (read as open-ended)")
    m = ev.merge(lk[["ticker", "permno", "sdate", "edate", "score"]], on="ticker",
                 how="left")
    m["link_ok"] = (m.permno.notna()
                    & (m.sdate <= m.anndats_act)
                    & (m.edate.isna() | (m.edate >= m.anndats_act)))
    m["link_ok"] = m.link_ok.fillna(False).astype(bool)
    unlinked = ev[~ev.ticker.isin(m.loc[m.link_ok, "ticker"])]
    m = m[m.link_ok].copy()
    open_ended = int(m.edate.isna().sum())
    cnt = m.groupby(["ticker", "fpedats"]).permno.nunique()
    ambiguous = cnt[cnt > 1]
    print(f"  events with no interval-valid link: {len(unlinked):,} "
          f"(logged, not force-matched)")
    print(f"  events resolved via an open-ended edate: {open_ended:,}")
    print(f"  events whose link stays ambiguous:  {len(ambiguous):,}")
    m = m[~m.set_index(["ticker", "fpedats"]).index.isin(ambiguous.index)]
    m["permno"] = m.permno.astype(int)

    keep = set(universe.permno.unique())
    ev = m[m.permno.isin(keep)].copy()
    print(f"  events on securities held by SPY/XLK/XLF:              {len(ev):,}")

    # Duplicate release records for one fiscal period: keep the first stamp and
    # record that a later one existed rather than dropping it silently.
    ev = ev.sort_values(["permno", "fpedats", "anndats_act"])
    ev["n_versions"] = ev.groupby(["permno", "fpedats"]).anndats_act.transform("size")
    ev = ev.groupby(["permno", "fpedats"], as_index=False).first()

    # The 2023 summary file carries fiscal periods announced in early 2024.
    # Those fall outside the authorised analysis window and are cut here, before
    # any outcome is read. Disclosure: a count-level view of them was produced
    # incidentally on the first run (550 events over 49 dates, no returns), so
    # early 2024 is not claimed to be uninspected. Nothing later in 2024 or 2025
    # has been touched.
    n_pre = len(ev)
    ev = ev[(ev.anndats_act >= ppw.ANALYSIS_START)
            & (ev.anndats_act <= ppw.ANALYSIS_END)]
    print(f"  outside the {ppw.ANALYSIS_START[:4]}-{ppw.ANALYSIS_END[:4]} window, "
          f"removed: {n_pre - len(ev):,}")

    ev["surprise_raw"] = ev.actual - ev.medest
    ev["event_date"] = ev.anndats_act
    ev["ann_time_raw"] = ev.anntims_act
    ev["ann_time_tz_status"] = "UNVERIFIED"
    return ev, unlinked, ambiguous


def scale_surprise(ev):
    """Fixed scale: surprise per dollar of pre-event price. Normalisation uses
    only information dated before the release."""
    px = []
    for y in range(2018, 2024):
        d = pd.read_parquet(ppw.abspath(f"raw/crsp_dsf_{y}.parquet"),
                            columns=["permno", "date", "prc"])
        px.append(d[d.permno.isin(ev.permno.unique())])
    px = pd.concat(px, ignore_index=True)
    px["date"] = pd.to_datetime(px.date)
    px["prc"] = px.prc.abs()          # CRSP negates a bid/ask average
    px = px.dropna(subset=["prc"]).sort_values(["permno", "date"])

    # price 5 trading days before the release, strictly pre-event
    out = []
    for pn, g in px.groupby("permno"):
        e = ev[ev.permno == pn]
        if e.empty:
            continue
        idx = np.searchsorted(g.date.values, e.event_date.values, side="left") - 5
        ok = idx >= 0
        p = np.full(len(e), np.nan)
        p[ok] = g.prc.values[idx[ok]]
        out.append(pd.DataFrame({"permno": pn, "fpedats": e.fpedats.values,
                                 "prc_pre": p}))
    ev = ev.merge(pd.concat(out, ignore_index=True), on=["permno", "fpedats"],
                  how="left")
    ev["surprise_scaled"] = ev.surprise_raw / ev.prc_pre
    print(f"\n  pre-event price found for {ev.prc_pre.notna().mean():.1%} of events "
          f"(t-5 trading days, strictly pre-release)")
    return ev


def census(ev, x):
    print("\n" + "=" * 92 + "\nEARNINGS EVENT CENSUS 2019-2023\n" + "=" * 92)
    print(f"  unique news events (firm x fiscal quarter): {len(ev):,}")
    print(f"  unique source firms (PERMNO):               {ev.permno.nunique():,}")
    print(f"  unique calendar announcement dates:         {ev.event_date.nunique():,}")
    print(f"  repeated source firms: median {ev.groupby('permno').size().median():.0f} "
          f"events per firm, max {ev.groupby('permno').size().max()}")

    print("\n  by year:")
    for y, g in ev.groupby(ev.event_date.dt.year):
        print(f"    {y}  {len(g):>6,} events  {g.permno.nunique():>4} firms  "
              f"{g.event_date.nunique():>4} dates")

    # An ETF-event observation exists only where the ETF held the firm then.
    obs = etf_event_obs(ev, x)
    print("\n  ETF-event observations (ETF held the firm at the prior snapshot):")
    for etf, g in obs.groupby("etf"):
        print(f"    {etf}  {len(g):>6,} obs  {g.permno.nunique():>4} firms  "
              f"{g.event_date.nunique():>4} dates")
    print(f"    total {len(obs):,} ETF-event rows over "
          f"{obs.event_date.nunique():,} distinct dates")
    print("    these are NOT independent shocks: one firm's release appears once "
          "per holding ETF")

    # Concentration of announcement dates.
    per_date = ev.groupby("event_date").size()
    hhi = ((per_date / per_date.sum()) ** 2).sum()
    print(f"\n  announcement-date concentration: {len(per_date):,} dates, "
          f"busiest {per_date.max()} events, median {per_date.median():.0f}")
    print(f"    inverse HHI over dates = {1/hhi:,.0f} effective dates "
          f"(descriptive only; not a count of independent observations)")

    # Simultaneous announcers: the ledger the daily ETF regression needs.
    sim = per_date.rename("n_announcers_same_date").reset_index()
    ev2 = ev.merge(sim, on="event_date")
    share_clean = (ev2.n_announcers_same_date == 1).mean()
    print(f"\n  events sharing their date with another sample firm: "
          f"{1 - share_clean:.1%}")
    print(f"    (recorded, not eliminated; the daily ETF panel must aggregate "
          f"these, not treat them as separate observations)")
    return obs, ev2


def etf_event_obs(ev, x):
    """Attach each event to every ETF that held the firm at its prior snapshot."""
    rows = []
    for etf, g in x.groupby("etf"):
        snaps = g[["report_dt", "eff_dt", "permno", "weight"]].copy()
        e = ev[["permno", "fpedats", "event_date"]].copy()
        j = e.merge(snaps, on="permno", how="inner")
        j = j[j.report_dt < j.event_date]
        j = j.sort_values("report_dt").groupby(["permno", "fpedats"], as_index=False).last()
        j["etf"] = etf
        j["report_age_days"] = (j.event_date - j.report_dt).dt.days
        j["eff_before_event"] = j.eff_dt < j.event_date
        rows.append(j)
    return pd.concat(rows, ignore_index=True)


def main():
    x = crosswalk()
    ev, unlinked, ambiguous = earnings(x)
    ev = scale_surprise(ev)
    obs, ev2 = census(ev, x)

    ev2.to_parquet(EVENTS, index=False)
    obs.to_parquet(ppw.OUT / "s1_etf_event_obs.parquet", index=False)
    unlinked.to_parquet(ppw.OUT / "s1_unlinked_events.parquet", index=False)
    ppw.provenance("s1_01_census", [HOLD],
                   {"events": int(len(ev2)), "firms": int(ev2.permno.nunique()),
                    "etf_event_obs": int(len(obs)),
                    "unlinked": int(len(unlinked)),
                    "ambiguous_links": int(len(ambiguous))})
    print(f"\n  written: {EVENTS.name}, s1_etf_event_obs.parquet, "
          f"s1_unlinked_events.parquet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
