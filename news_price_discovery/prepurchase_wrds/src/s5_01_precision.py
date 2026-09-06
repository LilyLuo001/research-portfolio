#!/usr/bin/env python3
"""Observed daily precision, a conditional planning grid, and what to buy.

Two things are kept strictly apart here. What was measured is the precision of
the daily and weekly quantities this project actually estimated, taken from the
observed data with the dependence structure the sample really has. What is
assumed is everything about the intraday horizon: the residual dispersion grid
below is a set of hypotheses, not an extrapolation of the daily numbers.

The daily ETF-minus-basket dispersion is NOT rescaled to a shorter horizon.
Multiplying a daily standard deviation by the square root of elapsed trading
time would assert exactly the intraday variance structure the project exists to
measure, and would make the planning table a restatement of its own assumption.
The grid is therefore stated as an assumption grid and the daily figure is
reported beside it only for scale.

The noise that matters is the dispersion of the ETF-minus-basket difference,
which nets out the common factor and is far smaller than either leg. Adding two
return variances as if they were independent would overstate it by roughly an
order of magnitude at this correlation.

No price is quoted, no vendor is contacted, no trial is assumed, and nothing is
bought. The manifest states specifications; pricing is a separate step for the
owner.
"""
import sys

import numpy as np
import pandas as pd

import ppw

EVENTS = ppw.OUT / "s1_earnings_events.parquet"
CONTRIB = ppw.OUT / "s2_contributions.parquet"
XWALK = ppw.OUT / "s1_etf_security_crosswalk.parquet"
MACRO = ppw.OUT / "s1_macro_events.parquet"
TRACK = ppw.OUT / "s2_tracking_daily.parquet"
RESP = ppw.OUT / "s3_response.parquet"

SD_GRID = [0.5, 1.0, 2.0, 5.0, 10.0]        # assumed bps per event, NOT measured
# One prespecified future horizon, declared before the manifest is built.
HORIZON = "release time T to T+15 minutes, quote-clock sampled at 1 second"
PRE, POST = 5, 15                            # minutes before / after the stamp
N_EARN, N_FOMC = 60, 12                      # the charter's small batch
MIN_PRICE = 5.0                              # pre-event screen, outcome-independent
RNG = np.random.default_rng(20260906)
OPEN, CLOSE = pd.Timestamp("09:30").time(), pd.Timestamp("16:00").time()


def observed_precision():
    """What the daily and weekly estimates actually achieved."""
    print("=" * 92 + "\nOBSERVED PRECISION OF THE DAILY QUANTITIES (MEASURED)\n"
          + "=" * 92)
    tr = pd.read_parquet(TRACK)
    print("  ETF minus approximate basket, daily, in bps:")
    print(f"  {'etf':<6}{'days':>8}{'sd':>9}{'p50 |.|':>10}{'p95 |.|':>10}"
          f"{'corr':>9}")
    for etf, g in tr.groupby("etf"):
        print(f"  {etf:<6}{len(g):>8,}{g.te_bps.std():>9.1f}"
              f"{g.te_bps.abs().median():>10.1f}{g.te_bps.abs().quantile(.95):>10.1f}"
              f"{g.port_ret.corr(g.etf_ret):>9.4f}")
    print("\n  this is the difference series, so the common factor is already")
    print("  netted out; it is not the sum of two independent return variances")
    print("  and it is NOT rescaled to any shorter horizon anywhere below")

    r = pd.read_parquet(RESP)
    e = r[r.mapping == "etf-agg"]
    print("\n  achieved 95% interval half-widths on the ETF daily response")
    print("  (block-resampled by calendar date, the dependence the sample has):")
    for x in e.itertuples(index=False):
        print(f"    h={str(x.h):<8}beta {x.beta:>8.2f}   half-width "
              f"{(x.hi - x.lo)/2:>8.2f} bps per unit surprise   n={x.n:,} rows "
              f"on {x.n_dates:,} dates")
    return tr


def dependence(j):
    """How many independent observations the sample really contains."""
    print("\n" + "=" * 92 + "\nDEPENDENCE: WHAT COUNTS AS AN OBSERVATION\n" + "=" * 92)
    n_rows = len(j)
    n_ev = j.groupby(["permno", "fpedats"]).ngroups
    n_dt = j.reaction_date_session.nunique()
    print(f"  ETF-event rows                         {n_rows:,}")
    print(f"  distinct source events                 {n_ev:,}")
    print(f"  distinct reaction dates                {n_dt:,}")
    print(f"  distinct source firms                  {j.permno.nunique():,}")
    per = j.groupby("reaction_date_session").size()
    hhi = (per / per.sum()) ** 2
    print(f"  inverse-HHI effective number of dates  {1/hhi.sum():.0f}")
    print("\n  the inverse HHI is a descriptive concentration number. It does not")
    print("  prove the dates are independent and it does not substitute for the")
    print("  clustered intervals reported in stage 3.")
    print("  Replicating one source event across three ETFs does not create three")
    print("  shocks, so the row count is never used as the sample size below.")
    return {"rows": n_rows, "events": n_ev, "dates": n_dt}


def select_batch(ev, j, mac):
    """Outcome-independent selection of the prospective intraday batch.

    Strata are built only from information available before each release: the
    pre-event return volatility of the source stock, its weight in the ETF at
    the prior snapshot, and the announcement session. Realised returns and
    realised contributions are not consulted, so the batch cannot be the set of
    events that happened to move the most.
    """
    print("\n" + "=" * 92 + "\nOUTCOME-INDEPENDENT SELECTION OF THE INTRADAY BATCH\n"
          + "=" * 92)
    d = j.merge(ev[["permno", "fpedats", "prc_pre", "ann_time_raw", "cname",
                    "ticker", "cusip"]], on=["permno", "fpedats"], how="left")
    d = d[d.eff_before_event & (d.prc_pre.abs() >= MIN_PRICE)]
    d = d[d.session.isin(["BMO", "AMC"])].copy()
    print(f"  eligible after pre-event screens: {len(d):,} ETF-event rows")
    print(f"    holdings demonstrably available before the event (eff_dt), "
          f"price >= ${MIN_PRICE:.0f},\n    session verified as BMO or AMC, "
          f"snapshot age within 120 days")

    pv = pre_event_vol(d)
    d["pre_vol"] = d.set_index(["permno", "event_date"]).index.map(pv)
    d = d.dropna(subset=["pre_vol"])
    d["vol_t"] = pd.qcut(d.pre_vol, 3, labels=["lo", "mid", "hi"])
    d["wt_t"] = pd.qcut(d.weight.rank(method="first"), 3,
                        labels=["lo", "mid", "hi"])
    d["stratum"] = (d.etf.astype(str) + "|" + d.session + "|"
                    + d.vol_t.astype(str) + "|" + d.wt_t.astype(str))
    ev_lvl = (d.sort_values("weight", ascending=False)
               .drop_duplicates(["permno", "fpedats"]))
    print(f"  distinct source events available: {len(ev_lvl):,} in "
          f"{ev_lvl.stratum.nunique()} strata")

    take = []
    for s, g in ev_lvl.groupby("stratum"):
        k = max(1, round(N_EARN * len(g) / len(ev_lvl)))
        take.append(g.iloc[RNG.permutation(len(g))[:k]])
    batch = pd.concat(take).head(N_EARN).copy()
    print(f"  earnings events drawn: {len(batch)} across "
          f"{batch.stratum.nunique()} strata, {batch.permno.nunique()} firms, "
          f"{batch.event_date.dt.year.nunique()} years")
    print(f"    by session: "
          + ", ".join(f"{k} {v}" for k, v in batch.session.value_counts().items()))

    m = mac.copy()
    m["year"] = pd.to_datetime(m.Date).dt.year
    fom = []
    for y, g in m.groupby("year"):
        k = max(1, round(N_FOMC * len(g) / len(m)))
        fom.append(g.iloc[RNG.permutation(len(g))[:k]])
    fomc = pd.concat(fom)
    if len(fomc) < N_FOMC:                 # proportional rounding can undershoot
        rest = m[~m.index.isin(fomc.index)]
        fomc = pd.concat([fomc, rest.iloc[RNG.permutation(len(rest))[
            :N_FOMC - len(fomc)]]])
    fomc = fomc.head(N_FOMC)
    print(f"  FOMC events drawn: {len(fomc)} stratified by year, "
          f"{fomc.year.nunique()} years")
    print("  the draw is seeded and stratified on pre-event information only;")
    print("  it is not the set of events with the largest realised contributions")
    return batch, fomc


def pre_event_vol(d):
    """Return sd over [-60, -6] trading days, strictly before each event."""
    fr = []
    for y in range(2018, 2024):
        x = pd.read_parquet(ppw.abspath(f"raw/crsp_dsf_{y}.parquet"),
                            columns=["permno", "date", "ret"])
        fr.append(x[x.permno.isin(set(d.permno))])
    r = pd.concat(fr, ignore_index=True)
    r["date"] = pd.to_datetime(r.date)
    r["ret"] = pd.to_numeric(r.ret, errors="coerce")
    w = r.pivot_table(index="date", columns="permno",
                      values="ret").astype("float64")
    cal, cols = w.index, {p: i for i, p in enumerate(w.columns)}
    v = w.values
    out = {}
    for pn, dt in set(zip(d.permno, d.event_date)):
        i, j = cal.searchsorted(dt), cols.get(pn, -1)
        if j < 0 or i < 60:
            continue
        s = v[i - 60:i - 5, j]
        s = s[np.isfinite(s)]
        if len(s) >= 30:
            out[(pn, dt)] = float(np.std(s, ddof=1))
    return out


def planning_table(batch, j):
    """MDE80 over an assumed residual-dispersion grid. Assumptions, not data."""
    print("\n" + "=" * 92 + "\nCONDITIONAL PLANNING TABLE (ASSUMPTIONS, NOT MEASUREMENTS)\n"
          + "=" * 92)
    print(f"  prespecified horizon: {HORIZON}")
    print("  every number in this table is conditional on an ASSUMED per-event")
    print("  residual dispersion of the ETF-minus-basket difference. None of")
    print("  these values is estimated from the daily data, and the daily")
    print("  dispersion is deliberately not rescaled into them.")

    s = batch.surprise_scaled.astype(float).values
    z = (s - np.mean(s)) / np.std(s, ddof=1)
    # residualise on ETF indicators so a common ETF level is not counted as signal
    X = pd.get_dummies(batch.etf).values.astype(float)
    zr = z - X @ np.linalg.lstsq(X, z, rcond=None)[0]
    ssq_ev = float((zr ** 2).sum())

    dates = batch.reaction_date_session.values
    agg = pd.Series(zr).groupby(pd.Series(dates)).sum()
    ssq_dt = float((agg.values ** 2).sum())
    rows_ssq = ssq_ev * (len(j) / j.groupby(["permno", "fpedats"]).ngroups)

    print(f"\n  sum of squared residualised standardised surprises in the batch:")
    print(f"    event level (one row per source event, {len(batch)} events): "
          f"{ssq_ev:.2f}")
    print(f"    date level (events summed to {len(agg)} reaction dates): "
          f"{ssq_dt:.2f}")
    print(f"    if ETF rows were counted as independent (NOT recommended): "
          f"{rows_ssq:.2f}")

    print(f"\n  MDE80 = (1.96 + 0.84) x assumed_residual_SD / "
          f"sqrt(sum(residualised standardised surprise^2))")
    print(f"\n  {'assumed resid SD':>18}{'event-level':>14}{'date-level':>14}"
          f"{'rows-independent':>19}")
    print(f"  {'(bps/event)':>18}{'MDE80 (bps)':>14}{'MDE80 (bps)':>14}"
          f"{'MDE80 (bps)':>19}")
    print("-" * 92)
    out = []
    for sd in SD_GRID:
        a = 2.80 * sd / np.sqrt(ssq_ev)
        b = 2.80 * sd / np.sqrt(ssq_dt)
        c = 2.80 * sd / np.sqrt(rows_ssq)
        print(f"  {sd:>18.1f}{a:>14.3f}{b:>14.3f}{c:>19.3f}")
        out.append({"assumed_sd_bps": sd, "mde80_event": a, "mde80_date": b,
                    "mde80_rows_independent": c})
    print("-" * 92)
    print("  the three columns are dependence scenarios, not alternative")
    print("  estimates. The rows-independent column is shown only to size the")
    print("  overstatement that treating replicated ETF rows as shocks produces.")
    print("\n  Reading the table: a response-gap contrast between the ETF and its")
    print("  basket is worth buying only if the gap the project cares about is")
    print("  larger than the MDE80 in the row matching the dispersion the data")
    print("  turn out to have. This is a requirement statement, not a final MDE")
    print("  and not a pass/fail gate.")
    return pd.DataFrame(out)


def manifest(batch, fomc, x):
    """Exact security-time intervals to request, counted as a union."""
    print("\n" + "=" * 92 + "\nACQUISITION MANIFEST\n" + "=" * 92)
    rows = []
    for r in batch.itertuples(index=False):
        t = pd.to_datetime(str(r.ann_time_raw), format="%H:%M:%S",
                           errors="coerce")
        if pd.isna(t):
            continue
        start = (t - pd.Timedelta(minutes=PRE)).time()
        end = (t + pd.Timedelta(minutes=POST)).time()
        ext = not (OPEN <= start < CLOSE and OPEN < end <= CLOSE)
        # the source stock and the ETF itself
        for pn, role in ((int(r.permno), "source_stock"),
                         (int({"SPY": 84398, "XLF": 86455,
                               "XLK": 86457}[r.etf]), "etf")):
            rows.append({"family": "earnings", "etf": r.etf, "permno": pn,
                         "role": role, "date": r.reaction_date_session,
                         "win_start": str(start), "win_end": str(end),
                         "extended_session": ext,
                         "source_event": f"{int(r.permno)}|{r.fpedats}"})
        # the complete constituent basket at the snapshot actually used
        b = x[(x.etf == r.etf) & (x.report_dt == r.report_dt)]
        for pn in b.permno.dropna().astype(int).unique():
            rows.append({"family": "earnings", "etf": r.etf, "permno": int(pn),
                         "role": "basket_constituent",
                         "date": r.reaction_date_session,
                         "win_start": str(start), "win_end": str(end),
                         "extended_session": ext,
                         "source_event": f"{int(r.permno)}|{r.fpedats}"})
    for r in fomc.itertuples(index=False):
        d = pd.to_datetime(r.Date)
        for etf, pn in (("SPY", 84398), ("XLF", 86455), ("XLK", 86457)):
            rows.append({"family": "monetary", "etf": etf, "permno": pn,
                         "role": "etf", "date": d, "win_start": "13:55:00",
                         "win_end": "14:15:00", "extended_session": False,
                         "source_event": f"FOMC|{d.date()}"})
            b = x[(x.etf == etf) & (x.report_dt <= d)]
            if b.empty:
                continue
            b = b[b.report_dt == b.report_dt.max()]
            for c in b.permno.dropna().astype(int).unique():
                rows.append({"family": "monetary", "etf": etf, "permno": int(c),
                             "role": "basket_constituent", "date": d,
                             "win_start": "13:55:00", "win_end": "14:15:00",
                             "extended_session": False,
                             "source_event": f"FOMC|{d.date()}"})
    m = pd.DataFrame(rows)

    # control windows: same clock times, previous trading day, no sample event
    ctl = m.copy()
    ctl["date"] = ctl.date - pd.Timedelta(days=1)
    ctl["role"] = "matched_control"
    m = pd.concat([m, ctl], ignore_index=True)

    print(f"  requested rows before de-duplication: {len(m):,}")
    u = m.drop_duplicates(["permno", "date", "win_start", "win_end"])
    print(f"  union of distinct security-time intervals: {len(u):,}")
    print(f"    overlapping event windows are counted once, not purchased twice")
    print(f"  distinct securities: {m.permno.nunique():,}")
    print(f"  distinct dates: {m.date.nunique():,}")
    print(f"  security-days: {u.groupby(['permno','date']).ngroups:,}")
    print(f"  intervals needing extended-hours coverage: "
          f"{int(u.extended_session.sum()):,} ({u.extended_session.mean():.1%})")
    print(f"\n  by family and role (union rows):")
    print(u.groupby(["family", "role"]).size().to_string())

    lean = u[u.role != "basket_constituent"]
    print(f"\n  a minimal variant covering only the ETFs, the announcing stocks")
    print(f"  and their controls would be {len(lean):,} intervals; the full")
    print(f"  basket variant above is {len(u):,}. Both are stated so the cost")
    print(f"  of the basket leg is visible before anything is priced.")
    m.to_parquet(ppw.OUT / "s5_acquisition_manifest.parquet", index=False)
    return m, u


def gaps(j, batch):
    """Historical-weight gaps, listed separately from the data request."""
    print("\n" + "=" * 92 + "\nHISTORICAL-WEIGHT GAPS (SEPARATE FROM THE QUOTE REQUEST)\n"
          + "=" * 92)
    obs = pd.read_parquet(ppw.OUT / "s1_etf_event_obs.parquet")
    print(f"  ETF-event rows whose snapshot is older than 120 days: "
          f"{int((obs.report_age_days > 120).sum()):,}")
    print(f"  rows where eff_dt is NOT before the event, so the weight is not")
    print(f"  demonstrably knowable in advance: "
          f"{int((~obs.eff_before_event).sum()):,} ({(~obs.eff_before_event).mean():.1%})")
    print(f"  median snapshot age at event: {obs.report_age_days.median():.0f} days")
    print("\n  These are gaps in the historical weight record, not in the quote")
    print("  data. Buying quotes does not close them; a holdings source with a")
    print("  shorter reporting lag would. They are listed here so the two are")
    print("  not confused in a purchase decision.")


def product_spec():
    print("\n" + "=" * 92 + "\nPRODUCT SPECIFICATION REQUIRED (NO PRICING, NO VENDOR CONTACT)\n"
          + "=" * 92)
    for line in [
        "REQUIRED   quote updates, or a clock-sampled bid/ask series, with an",
        "           exchange or SIP timestamp and quote condition codes",
        "REQUIRED   coverage of the extended session for the AMC and BMO windows",
        "           flagged above; a regular-hours-only product cannot see them",
        "SUFFICIENT a one-second bid/ask grid, for a descriptive contrast at 10",
        "           seconds or coarser, which is the horizon prespecified here",
        "NOT ENOUGH trade-only OHLC bars: within-bar quote leadership is exactly",
        "           what a bar aggregates away",
        "NOT ENOUGH a trade-triggered BBO sample, which observes the quote only",
        "           when a trade happens and is not the quote update stream",
        "NOT ENOUGH any one-second product for a millisecond-resolution claim",
        "NOT NEEDED full depth of book, order imbalance, or message-level data",
    ]:
        print("  " + line)
    print("\n  Specifications are to be confirmed with the owner before any")
    print("  vendor is approached. No unit price is quoted here, no trial")
    print("  credit is assumed, no claim is made that any sample product covers")
    print("  these historical dates, and nothing has been purchased.")


def main():
    ev = pd.read_parquet(EVENTS)
    j = pd.read_parquet(CONTRIB)
    x = pd.read_parquet(XWALK)
    mac = pd.read_parquet(MACRO)

    observed_precision()
    dependence(j)
    batch, fomc = select_batch(ev, j, mac)
    tab = planning_table(batch, j)
    m, u = manifest(batch, fomc, x)
    gaps(j, batch)
    product_spec()

    tab.to_parquet(ppw.OUT / "s5_planning_table.parquet", index=False)
    batch.to_parquet(ppw.OUT / "s5_batch_earnings.parquet", index=False)
    fomc.to_parquet(ppw.OUT / "s5_batch_fomc.parquet", index=False)
    ppw.provenance("s5_01_precision", [EVENTS, CONTRIB, XWALK, MACRO],
                   {"sd_grid": SD_GRID, "horizon": HORIZON,
                    "n_earnings": int(len(batch)), "n_fomc": int(len(fomc)),
                    "manifest_union_intervals": int(len(u))})
    print("\n  written: s5_planning_table.parquet, s5_acquisition_manifest.parquet,")
    print("           s5_batch_earnings.parquet, s5_batch_fomc.parquet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
