#!/usr/bin/env python3
"""Macro supplement: coarse daily responses to rate news, and a Rigobon check.

The macro side of the question needs a policy surprise that is not read off the
equity return it is meant to explain. The FRBSF event-study database supplies
one, built from rate futures around each announcement. It is a public external
supplement, downloaded and hashed in stage 1; it is not a WRDS file and carries
no ETF or constituent quote path.

Rigobon (2003) identifies a simultaneous system by comparing regimes in which
one shock's variance changes while the transmission between variables does not.
This stage runs only the *relevance* half of that argument: does the covariance
matrix actually move between announcement and calendar-matched nonannouncement
windows, and does it move in a way that could identify anything? A change that
is merely proportional rescales both regimes alike and identifies nothing, and
a near-singular covariance matrix makes the inversion meaningless however large
the variance shift looks. Both failure modes are tested for here.

A calendar-matched covariance contrast is not causal identification, an FOMC
announcement is not a shock to the ETF alone, and finding that the matrix moves
between the macro and micro regimes does not license pooling the two under one
fixed transmission matrix and then claiming the same exercise proves it switches.
"""
import sys

import numpy as np
import pandas as pd
from scipy import linalg, stats

import ppw

MACRO = ppw.OUT / "s1_macro_events.parquet"
PANEL = ppw.OUT / "s3_etf_daily_panel.parquet"
TRACK = ppw.OUT / "s2_tracking_daily.parquet"
ETF_PERMNO = {"SPY": 84398, "XLF": 86455, "XLK": 86457}
# Prespecified control window: 2 to 10 trading days either side of an event,
# excluding event days themselves. Fixed before any covariance was computed.
CTRL_LO, CTRL_HI = 2, 10
RATE = ["MP1", "MP2", "FF1", "ED1", "ED4"]
B = 2000
RNG = np.random.default_rng(20260906)


def windows(cal, ev_dates, lo, hi):
    """Announcement days and the calendar-matched nearby control days."""
    ev = np.array(sorted(set(pd.DatetimeIndex(ev_dates)) & set(cal)))
    i = cal.searchsorted(pd.DatetimeIndex(ev))
    ctrl = set()
    for k in i:
        for d in range(lo, hi + 1):
            for j in (k - d, k + d):
                if 0 <= j < len(cal):
                    ctrl.add(cal[j])
    ctrl -= set(ev)
    return pd.DatetimeIndex(ev), pd.DatetimeIndex(sorted(ctrl))


def cov_block(d, cols, name):
    S = np.cov(d[cols].values.T, ddof=1) * 1e8       # bps^2
    print(f"\n  {name}: n={len(d)} days")
    print(f"    {'':<10}" + "".join(f"{c:>12}" for c in cols))
    for a, c in enumerate(cols):
        print(f"    {c:<10}" + "".join(f"{S[a, b]:>12.1f}" for b in range(len(cols))))
    R = np.corrcoef(d[cols].values.T)
    print(f"    correlation off-diagonal: "
          + ", ".join(f"{cols[a]}~{cols[b]} {R[a, b]:.4f}"
                      for a in range(len(cols)) for b in range(a + 1, len(cols))))
    return S


def regime(rets, cal, ev_dates, cols, family):
    """Compare the covariance matrix across the two prespecified windows."""
    print("\n" + "=" * 92 + f"\nRIGOBON RELEVANCE DIAGNOSTIC: {family}\n" + "=" * 92)
    ev, ctrl = windows(cal, ev_dates, CTRL_LO, CTRL_HI)
    a = rets[rets.date.isin(ev)]
    b = rets[rets.date.isin(ctrl)]
    print(f"  announcement days {len(a)}, control days {len(b)} "
          f"({CTRL_LO}-{CTRL_HI} trading days either side, event days excluded)")
    print("  means are left in; returns are not standardised, because the")
    print("  variance change is the object under study")
    Sa = cov_block(a, cols, "announcement window")
    Sb = cov_block(b, cols, "control window")

    print("\n  variance ratio, announcement / control:")
    for i, c in enumerate(cols):
        r = Sa[i, i] / Sb[i, i]
        print(f"    {c:<10}{r:>8.3f}   (sd {np.sqrt(Sa[i,i]):.1f} vs "
              f"{np.sqrt(Sb[i,i]):.1f} bps)")

    w = linalg.eigvals(np.linalg.solve(Sb, Sa)).real
    w = np.sort(w)[::-1]
    print(f"\n  generalised eigenvalues of Sigma_ann relative to Sigma_ctrl:")
    print("    " + "  ".join(f"{x:.3f}" for x in w))
    spread = w.max() / w.min() if w.min() > 0 else np.inf
    print(f"    spread (max/min) = {spread:.3f}")
    if spread < 1.5:
        print("    -> the change is close to proportional. A proportional")
        print("       rescaling of every direction at once shifts no relative")
        print("       variance and therefore identifies nothing in Rigobon's")
        print("       sense, however large the individual variance ratios are.")
    else:
        print("    -> the change is not proportional; relative variances do move")

    cond = np.linalg.cond(Sa)
    print(f"\n  near-collinearity: condition number of the announcement "
          f"covariance = {cond:,.0f}")
    if cond > 100:
        print("    -> the system is close to singular. The ETF and its own basket")
        print("       are nearly the same series at daily resolution, so any")
        print("       structural matrix recovered by inverting this is dominated")
        print("       by the direction with almost no independent variation.")
    return {"family": family, "n_ann": len(a), "n_ctrl": len(b),
            "eig_spread": float(spread), "cond": float(cond),
            "var_ratio": {c: float(Sa[i, i] / Sb[i, i]) for i, c in enumerate(cols)}}


def rate_response(mac, rets, cal):
    """Coarse daily ETF response to the published rate-based surprise."""
    print("\n" + "=" * 92 + "\nDAILY ETF RESPONSE TO RATE-BASED POLICY SURPRISE\n"
          + "=" * 92)
    print("  the surprise is the published rate-futures move; it is never")
    print("  inferred from the equity return being explained. A statement and")
    print("  its press conference on one day are one daily observation.")
    m = mac.copy()
    m["date"] = pd.to_datetime(m.Date)
    out = []
    print(f"\n  {'series':<7}{'etf':<6}{'n':>5}{'beta bps/bp':>14}"
          f"{'95% bootstrap CI':>26}")
    print("-" * 92)
    for c in RATE:
        if c not in m:
            continue
        for etf in ETF_PERMNO:
            d = m[["date", c]].dropna().merge(
                rets[["date", etf]], on="date", how="inner")
            if len(d) < 20:
                continue
            x = pd.to_numeric(d[c]).values * 100          # pp -> bp
            y = d[etf].values * 10000
            b = np.polyfit(x, y, 1)[0]
            dr = np.array([np.polyfit(x[i], y[i], 1)[0]
                           for i in (RNG.integers(0, len(x), len(x))
                                     for _ in range(B))])
            lo, hi = np.percentile(dr, [2.5, 97.5])
            print(f"  {c:<7}{etf:<6}{len(d):>5}{b:>14.2f}"
                  f"   [{lo:>9.2f}, {hi:>9.2f}]")
            out.append({"series": c, "etf": etf, "n": len(d), "beta": float(b),
                        "lo": float(lo), "hi": float(hi)})
    print("-" * 92)
    print("  a coarse daily elasticity. It says nothing about whether the ETF or")
    print("  its constituents moved first inside the announcement window, and an")
    print("  FOMC decision is a shock to both, not to the ETF alone.")
    return pd.DataFrame(out)


def main():
    mac = pd.read_parquet(MACRO)
    tr = pd.read_parquet(TRACK)

    fr = []
    for y in range(2019, 2024):
        d = pd.read_parquet(ppw.abspath(f"raw/crsp_dsf_{y}.parquet"),
                            columns=["permno", "date", "ret"])
        fr.append(d[d.permno.isin(ETF_PERMNO.values())])
    r = pd.concat(fr, ignore_index=True)
    r["date"] = pd.to_datetime(r.date)
    r["ret"] = pd.to_numeric(r.ret, errors="coerce")
    inv = {v: k for k, v in ETF_PERMNO.items()}
    wide = r.assign(etf=r.permno.map(inv)).pivot_table(
        index="date", columns="etf", values="ret").astype("float64").dropna()

    # the approximate basket, as built in stage 2, aligned to the same days
    bk = (tr.pivot_table(index="date", columns="etf", values="port_ret")
            .astype("float64").rename(columns=lambda c: c + "_basket"))
    rets = wide.join(bk, how="inner").reset_index().dropna()
    cal = pd.DatetimeIndex(sorted(rets.date))

    print("=" * 92 + "\nMACRO SUPPLEMENT (FRBSF USMPD) AND VARIANCE REGIMES\n"
          + "=" * 92)
    print(f"  status    public external supplement, hashed in stage 1; not a")
    print(f"            WRDS file and not a substitute for quote histories")
    print(f"  aligned trading days 2019-2023: {len(rets):,}")
    print(f"  FOMC event days in window: {mac.Date.nunique()}")

    rr = rate_response(mac, rets, cal)

    diag = []
    cols = ["SPY", "SPY_basket", "XLK", "XLF"]
    diag.append(regime(rets, cal, mac.Date, cols, "MONETARY (FOMC)"))

    # the micro family: the earnings-density regime, prespecified as the top
    # quintile of summed announcing weight on the ETF reaction date
    pan = pd.read_parquet(PANEL)
    dens = pan.groupby("date").w_ann.sum()
    hi = dens[dens >= dens.quantile(0.8)].index
    print(f"\n  earnings-dense days: top quintile of summed announcing weight, "
          f"{len(hi)} days")
    diag.append(regime(rets, cal, hi, cols, "MICRO (EARNINGS-DENSE)"))

    print("\n" + "=" * 92)
    print("  Comparing these two families shows only that second moments differ")
    print("  across calendar regimes. It does not identify a transmission matrix,")
    print("  and it is not evidence that one matrix governs both regimes.")

    pd.DataFrame(diag).to_parquet(ppw.OUT / "s4_regimes.parquet", index=False)
    rr.to_parquet(ppw.OUT / "s4_rate_response.parquet", index=False)
    ppw.provenance("s4_01_macro", [MACRO, PANEL, TRACK],
                   {"control_window": [CTRL_LO, CTRL_HI], "bootstrap": B,
                    "regimes": diag})
    print("  written: s4_regimes.parquet, s4_rate_response.parquet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
