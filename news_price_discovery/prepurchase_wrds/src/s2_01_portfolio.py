#!/usr/bin/env python3
"""Approximate each ETF from its reported holdings, and size the single-name signal.

This is a portfolio diagnostic, not a replica of the fund. Holdings arrive
monthly, the fund trades daily, and a reported snapshot is a photograph of
something that has since moved. The point of tracking it is to learn how much
of each ETF's daily variation the reported names actually explain, because that
number bounds how informative a constituent basket can be about the ETF.

Three rules do most of the work here. Weights drift with realised returns
between snapshots rather than being held fixed, since a fixed-weight basket
implies daily rebalancing the fund does not do. Assets that fail to map are not
quietly treated as cash or as zero-return holdings; they leave the covered
sleeve and the coverage is reported. And a later snapshot is never used to
describe an earlier date.
"""
import sys

import numpy as np
import pandas as pd

import ppw

XWALK = ppw.OUT / "s1_etf_security_crosswalk.parquet"
HOLD = ppw.OUT / "holdings_three_etfs.parquet"
EVENTS = ppw.OUT / "s1_earnings_events.parquet"
ETF_PERMNO = {"SPY": 84398, "XLF": 86455, "XLK": 86457}
MAX_REPORT_AGE = 120                      # registered; exclusions are logged
AGE_BINS = [0, 30, 60, 90, 120, 10 ** 6]
AGE_LABELS = ["<=30d", "31-60d", "61-90d", "91-120d", ">120d (excluded)"]
CASH_PAT = r"CASH|MONEY MARKET|MM FD|LIQ RES|LIQUIDITY|TREASURY BILL|REPO"


def daily_returns(permnos):
    fr = []
    for y in range(2018, 2024):
        d = pd.read_parquet(ppw.abspath(f"raw/crsp_dsf_{y}.parquet"),
                            columns=["permno", "date", "ret"])
        fr.append(d[d.permno.isin(permnos)])
    r = pd.concat(fr, ignore_index=True)
    r["date"] = pd.to_datetime(r.date)
    r["ret"] = pd.to_numeric(r.ret, errors="coerce")
    return r.dropna(subset=["ret"]).drop_duplicates(["permno", "date"])


def sleeves(h):
    """Split every holdings line into covered, cash, or unmapped."""
    h = h.copy()
    h["is_cash"] = h.security_name.fillna("").str.upper().str.contains(CASH_PAT, regex=True)
    h["sleeve"] = np.where(h.is_cash, "cash",
                           np.where(h.permno.notna(), "covered", "unmapped"))
    print("=" * 92 + "\nSLEEVE COMPOSITION (share of reported TNA)\n" + "=" * 92)
    print(f"{'etf':<6}{'covered':>10}{'cash':>10}{'unmapped':>11}{'sum':>9}"
          f"{'unmapped names':>16}")
    print("-" * 92)
    for etf, g in h.groupby("etf"):
        per = g.groupby(["report_dt", "eff_dt", "sleeve"]).percent_tna.sum().unstack(fill_value=0)
        med = per.median() / 100
        print(f"{etf:<6}{med.get('covered', 0):>9.2%}{med.get('cash', 0):>10.2%}"
              f"{med.get('unmapped', 0):>11.2%}{med.sum():>9.2%}"
              f"{g[g.sleeve == 'unmapped'].security_name.nunique():>16}")
    print("-" * 92)
    print("  the covered sleeve is reported as a sleeve; it is never renormalised "
          "to 100%\n  and called the fund, and unmapped lines are not treated as "
          "cash or zero-return")
    return h


def consolidate(x):
    """Collapse each report date's eff_dt cells into one complete portfolio.

    A third of SPY's (report_dt, eff_dt) cells carry a single line summing to
    well under 1% of TNA. Every one of them shares its report date with a
    complete listing, so they are amendments to that filing, not standalone
    portfolios. Treated as portfolios they produce one-stock "funds" whose
    return is meaningless against the ETF. The later eff_dt supersedes the
    earlier for any security it restates, and the portfolio is only fully
    available at the latest eff_dt of its report date.
    """
    cell = x.groupby(["etf", "report_dt", "eff_dt"]).weight.sum()
    part = cell[cell < 0.5]
    print(f"\n  amendment cells folded into their report date: {len(part)} of "
          f"{len(cell)} (median summed weight {part.median():.4%})")
    x = x.sort_values("eff_dt")
    x = x.drop_duplicates(["etf", "report_dt", "permno"], keep="last").copy()
    x["avail_dt"] = x.groupby(["etf", "report_dt"]).eff_dt.transform("max")
    return x


def track(x, rets):
    """Buy-and-hold the covered sleeve from each snapshot to the next."""
    out = []
    cal = np.sort(rets.date.unique())
    wide = rets.pivot_table(index="date", columns="permno",
                            values="ret").astype("float64")
    for etf, g in x.groupby("etf"):
        snaps = (g.groupby(["report_dt", "avail_dt"])
                  .apply(lambda d: d.set_index("permno").weight, include_groups=False))
        keys = sorted({(r, e) for r, e in zip(g.report_dt, g.avail_dt)})
        for i, (rdt, edt) in enumerate(keys):
            w0 = snaps.loc[(rdt, edt)].astype("float64")
            w0 = w0[w0.index.isin(wide.columns)]
            if w0.empty:
                continue
            # Availability, at date level: start the day after eff_dt.
            start = cal[np.searchsorted(cal, np.datetime64(edt), side="right")] \
                if np.searchsorted(cal, np.datetime64(edt), side="right") < len(cal) else None
            if start is None:
                continue
            nxt = keys[i + 1][1] if i + 1 < len(keys) else np.datetime64("2023-12-29")
            end = np.datetime64(nxt)
            win = wide.loc[(wide.index >= start) & (wide.index <= end), w0.index]
            if len(win) < 2:
                continue
            r = win.fillna(0.0)                      # a missing day is no return,
            avail = win.notna()                      # and the asset is flagged
            val = w0.values * np.cumprod(1 + r.values, axis=0)
            prev = np.vstack([w0.values, val[:-1]])
            denom = (prev * avail.values).sum(axis=1)
            port = np.where(denom > 0,
                            (prev * r.values * avail.values).sum(axis=1) / np.where(denom > 0, denom, 1),
                            np.nan)
            out.append(pd.DataFrame({
                "etf": etf, "report_dt": rdt, "avail_dt": edt, "date": win.index,
                "port_ret": port, "covered_weight": w0.sum(),
                "n_assets": int(len(w0)),
                "day_in_hold": np.arange(1, len(win) + 1),
                "asset_availability": avail.values.mean(axis=1)}))
    return pd.concat(out, ignore_index=True)


def tracking_diagnostics(tr, rets):
    etf_r = rets[rets.permno.isin(ETF_PERMNO.values())].copy()
    inv = {v: k for k, v in ETF_PERMNO.items()}
    etf_r["etf"] = etf_r.permno.map(inv)
    d = tr.merge(etf_r[["etf", "date", "ret"]].rename(columns={"ret": "etf_ret"}),
                 on=["etf", "date"], how="inner").dropna(subset=["port_ret", "etf_ret"])
    d["te_bps"] = (d.port_ret - d.etf_ret) * 10000

    print("\n" + "=" * 92 + "\nETF vs APPROXIMATE PORTFOLIO, DAILY\n" + "=" * 92)
    print(f"{'etf':<6}{'days':>7}{'corr':>8}{'beta':>8}{'TE sd':>9}{'TE p50':>9}"
          f"{'TE p95':>9}{'cov wt':>9}{'assets':>8}")
    print("-" * 92)
    for etf, g in d.groupby("etf"):
        b = np.polyfit(g.etf_ret, g.port_ret, 1)[0]
        print(f"{etf:<6}{len(g):>7,}{g.port_ret.corr(g.etf_ret):>8.4f}{b:>8.3f}"
              f"{g.te_bps.std():>9.1f}{g.te_bps.abs().median():>9.1f}"
              f"{g.te_bps.abs().quantile(.95):>9.1f}{g.covered_weight.median():>9.2%}"
              f"{g.n_assets.median():>8.0f}")
    print("-" * 92)
    print("  TE in basis points per day; weights are never fitted to improve this")

    print("\n  tracking error by holding age (drift since the snapshot):")
    d["age_bin"] = pd.cut(d.day_in_hold, [0, 5, 10, 20, 40, 10**6],
                          labels=["1-5d", "6-10d", "11-20d", "21-40d", ">40d"])
    t = d.groupby(["etf", "age_bin"], observed=True).te_bps.apply(lambda s: s.abs().median()).unstack()
    print(t.to_string(float_format=lambda v: f"{v:7.1f}"))
    print("  a rising row is the reported snapshot going stale between filings")
    return d


def report_age(ev):
    """Snapshot age at each event, and the two availability labels."""
    obs = pd.read_parquet(ppw.OUT / "s1_etf_event_obs.parquet")
    print("\n" + "=" * 92 + "\nSNAPSHOT REPORT AGE AT EVENT\n" + "=" * 92)
    obs["age_bin"] = pd.cut(obs.report_age_days, AGE_BINS, labels=AGE_LABELS, right=True)
    t = obs.groupby(["etf", "age_bin"], observed=True).size().unstack(fill_value=0)
    t["total"] = t.sum(axis=1)
    print(t.to_string())
    over = obs[obs.report_age_days > MAX_REPORT_AGE]
    print(f"\n  registered rule: snapshots older than {MAX_REPORT_AGE} days are "
          f"excluded from weighted\n  quantities. Excluded: {len(over):,} of "
          f"{len(obs):,} ETF-event rows ({len(over)/len(obs):.2%}).")
    print("  This is a project choice, not proof that a within-limit snapshot "
          "gives the\n  exact event-date weight. Exclusions stay in the ledger "
          "and the rule does not\n  move with the sign of any response.")
    print(f"\n  availability labels (both preserved):")
    print(f"    report_dt before the event (economic-date-prior): {len(obs):,} rows, 100%")
    print(f"    eff_dt   before the event (demonstrably available): "
          f"{int(obs.eff_before_event.sum()):,} rows "
          f"({obs.eff_before_event.mean():.1%})")
    print("    only the second supports a knowable-before-the-event claim")
    over.to_parquet(ppw.OUT / "s2_exclusion_ledger.parquet", index=False)
    return obs


def contributions(ev, obs, rets, names):
    """Realised accounting contribution of each source event to each ETF."""
    r = rets.rename(columns={"ret": "src_ret"})
    e = ev[["permno", "fpedats", "event_date", "session", "surprise_scaled",
            "reaction_date_session", "reaction_date_sameday",
            "reaction_date_nextday", "n_same_reaction_date"]]
    j = obs.merge(e, on=["permno", "fpedats", "event_date"], how="inner")
    j = j[j.report_age_days <= MAX_REPORT_AGE]
    j = j.merge(r, left_on=["permno", "reaction_date_session"],
                right_on=["permno", "date"], how="left")
    j["contribution_bps"] = 10000 * j.weight * j.src_ret
    j = j.dropna(subset=["contribution_bps"])

    print("\n" + "=" * 92 + "\nREALISED ACCOUNTING CONTRIBUTION (development sample)\n"
          + "=" * 92)
    print("  contribution_bps = 10,000 x prior-snapshot weight x source return on")
    print("  its reaction date. This is an accounting decomposition of a realised")
    print("  return. It is not a flow, an AP trade, a causal news effect, a price-")
    print("  discovery share, or a bound on anything.\n")
    print(f"{'etf':<6}{'obs':>8}{'|c| p50':>10}{'|c| p90':>10}{'|c| p99':>10}"
          f"{'max':>10}{'wt p50':>9}{'wt max':>9}")
    print("-" * 92)
    for etf, g in j.groupby("etf"):
        c = g.contribution_bps.abs()
        print(f"{etf:<6}{len(g):>8,}{c.median():>10.2f}{c.quantile(.9):>10.2f}"
              f"{c.quantile(.99):>10.2f}{c.max():>10.1f}"
              f"{g.weight.median():>9.3%}{g.weight.max():>9.2%}")
    print("-" * 92)

    print("\n  by year (median |contribution| in bps):")
    print(j.pivot_table(index=j.event_date.dt.year, columns="etf",
                        values="contribution_bps",
                        aggfunc=lambda s: s.abs().median())
           .to_string(float_format=lambda v: f"{v:7.2f}"))

    print("\n  by verified session (median |contribution| in bps):")
    print(j.pivot_table(index="session", columns="etf", values="contribution_bps",
                        aggfunc=lambda s: s.abs().median())
           .to_string(float_format=lambda v: f"{v:7.2f}"))

    print("\n  largest single-firm median contributions (>=4 events):")
    g = j.groupby(["etf", "permno"]).contribution_bps.agg(
        n="size", med=lambda s: s.abs().median())
    top = g[g.n >= 4].sort_values("med", ascending=False).head(8)
    for (etf, pn), row in top.iterrows():
        print(f"    {etf}  permno {int(pn):<8}{names.get(pn, '')[:30]:<32}"
              f"{row.med:>8.2f} bps  n={int(row.n)}")

    print("\n  simultaneous-earnings ledger:")
    print(f"    ETF-event rows whose reaction date carries other sample releases: "
          f"{(j.n_same_reaction_date > 1).mean():.1%}")
    sim = (j.groupby(["etf", "reaction_date_session"])
             .agg(n_announcers=("permno", "nunique"),
                  total_weight=("weight", "sum"),
                  total_contribution_bps=("contribution_bps", "sum")).reset_index())
    print(f"    distinct ETF-reaction-date cells: {len(sim):,}")
    print(f"    announcers per cell: median {sim.n_announcers.median():.0f}, "
          f"max {sim.n_announcers.max()}")
    print(f"    summed announcing weight per cell: median "
          f"{sim.total_weight.median():.2%}, max {sim.total_weight.max():.2%}")
    sim.to_parquet(ppw.OUT / "s2_simultaneous_ledger.parquet", index=False)
    j.to_parquet(ppw.OUT / "s2_contributions.parquet", index=False)
    return j


def main():
    x = consolidate(pd.read_parquet(XWALK))
    h = pd.read_parquet(HOLD)
    ev = pd.read_parquet(EVENTS)
    sleeves(h)

    permnos = set(x.permno.unique()) | set(ETF_PERMNO.values())
    rets = daily_returns(permnos)
    print(f"\n  daily returns loaded: {len(rets):,} rows, "
          f"{rets.permno.nunique():,} securities, "
          f"{rets.date.min().date()}..{rets.date.max().date()}")
    print("  convention: CRSP RET, which includes distributions; reinvestment is")
    print("  implicit in the compounding and no separate dividend series is added")

    tr = track(x, rets)
    d = tracking_diagnostics(tr, rets)
    obs = report_age(ev)
    names = (h.dropna(subset=['permno'])
              .groupby('permno').security_name.first().to_dict())
    j = contributions(ev, obs, rets, names)

    tr.to_parquet(ppw.OUT / "s2_tracking.parquet", index=False)
    d.to_parquet(ppw.OUT / "s2_tracking_daily.parquet", index=False)
    ppw.provenance("s2_01_portfolio", [XWALK, HOLD, EVENTS],
                   {"tracking_days": int(len(d)), "contribution_rows": int(len(j)),
                    "max_report_age": MAX_REPORT_AGE})
    print("\n  written: s2_tracking.parquet, s2_tracking_daily.parquet, "
          "s2_contributions.parquet,\n           s2_simultaneous_ledger.parquet, "
          "s2_exclusion_ledger.parquet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
