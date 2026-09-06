#!/usr/bin/env python3
"""Hou-Moskowitz first-stage delay, D1, on the bounded instrument universe.

This reproduces the first-stage construction of Hou and Moskowitz (2005, RFS
pp. 985-986) and nothing beyond it: weekly returns on the contemporaneous
market plus four weekly lags, and the share of explanatory power that only the
lags supply. The second-stage portfolio sort is not part of this exercise.

What D1 measures is how slowly a security's price absorbs *market-wide*
information at weekly resolution. It is not a firm-news event-speed estimator,
not a causal ETF-to-stock effect, and not evidence about which venue moves
first inside a day. A security can have D1 = 0 here and still lag by seconds.

The ETF application is an adaptation and is labelled as one. The market return
is CRSP's value-weighted index, verified locally in stage 7, so no benchmark
substitution arises and SPY is never regressed on itself.
"""
import sys

import numpy as np
import pandas as pd
from scipy import stats

import ppw

XWALK = ppw.OUT / "s1_etf_security_crosswalk.parquet"
ETF_PERMNO = {"SPY": 84398, "XLF": 86455, "XLK": 86457}
FORMATION = [f"{y}-06-30" for y in range(2019, 2024)]
WEEKS = 52                 # ~one year of weekly returns ending at formation
MIN_ROWS = 40              # pilot engineering choice, not a universal threshold
NLAG = 4
DAILY_WINDOW = 252         # for the fixed-frequency daily sensitivity


def weekly(r, key="permno"):
    """Compound daily total returns into Wednesday-to-Wednesday weeks.

    A week is kept only when the security traded on every session in it, so a
    halted or delisted stretch never enters as a quiet week.
    """
    r = r.copy()
    dow = r.date.dt.dayofweek
    r["week"] = r.date + pd.to_timedelta((2 - dow) % 7, unit="D")
    sess = r.groupby("week").date.nunique().rename("n_sess")
    g = r.groupby([key, "week"]).agg(
        ret=("ret", lambda s: float(np.prod(1.0 + s.values) - 1.0)),
        n=("ret", "size")).reset_index()
    g = g.merge(sess, on="week")
    g["complete"] = g.n == g.n_sess
    return g


def nested_fit(y, X_c, X_u):
    """Restricted and unrestricted fits on identical rows; raw R-squared."""
    n = len(y)
    ybar = y.mean()
    tss = float(((y - ybar) ** 2).sum())
    if tss <= 0:
        return None
    out = {}
    for tag, X in (("c", X_c), ("u", X_u)):
        A = np.column_stack([np.ones(n), X])
        beta, *_ = np.linalg.lstsq(A, y, rcond=None)
        resid = y - A @ beta
        rss = float((resid ** 2).sum())
        out[tag] = (beta, rss, 1.0 - rss / tss)
    b_u, rss_u, r2_u = out["u"]
    _, rss_c, r2_c = out["c"]
    k_u = X_u.shape[1] + 1
    df = n - k_u
    f = ((rss_c - rss_u) / NLAG) / (rss_u / df) if df > 0 and rss_u > 0 else np.nan
    return {"n": n, "r2_c": r2_c, "r2_u": r2_u,
            "beta0": float(b_u[1]), "lags": b_u[2:].astype(float),
            "f_lags": float(f),
            "p_lags": float(1 - stats.f.cdf(f, NLAG, df)) if np.isfinite(f) else np.nan}


def build(panel, mkt, kind, freq, window, label):
    """Run the nested regressions for every security at every formation date."""
    rows = []
    mkt = mkt.sort_values("t").reset_index(drop=True)
    M = {c: mkt.mkt.shift(c).values for c in range(NLAG + 1)}
    mi = pd.Series(np.arange(len(mkt)), index=mkt.t.values)
    for form in FORMATION:
        f = pd.Timestamp(form)
        end = mi.index[mi.index <= f].max()
        j = int(mi.loc[end])
        lo = max(j - window + 1, NLAG)
        ts = mkt.t.values[lo:j + 1]
        Xall = np.column_stack([M[c][lo:j + 1] for c in range(NLAG + 1)])
        ok_m = np.isfinite(Xall).all(axis=1)
        for pid, g in panel.groupby("permno"):
            s = g[g.complete] if "complete" in g else g
            s = s.set_index("t").ret.reindex(ts)
            keep = ok_m & s.notna().values
            if keep.sum() < MIN_ROWS:
                continue
            y = s.values[keep].astype(float)
            X = Xall[keep]
            fit = nested_fit(y, X[:, :1], X)
            if fit is None:
                continue
            denom_ok = fit["r2_u"] > 0.01
            rows.append({
                "kind": kind, "freq": freq, "label": label.get(pid, str(pid)),
                "permno": pid, "formation": f, "n": fit["n"],
                "r2_contemp": fit["r2_c"], "r2_4lag": fit["r2_u"],
                "d1": 1.0 - fit["r2_c"] / fit["r2_u"] if denom_ok else np.nan,
                "denominator_ok": denom_ok, "beta_contemp": fit["beta0"],
                **{f"lag{k+1}": fit["lags"][k] for k in range(NLAG)},
                "f_lags": fit["f_lags"], "p_lags": fit["p_lags"]})
    return pd.DataFrame(rows)


def report(d, title):
    print("\n" + "=" * 92 + f"\n{title}\n" + "=" * 92)
    if d.empty:
        print("  no eligible securities")
        return
    bad = int((~d.denominator_ok).sum())
    print(f"  regressions: {len(d):,}   securities: {d.permno.nunique():,}   "
          f"formation dates: {d.formation.nunique()}")
    print(f"  median regression rows: {d.n.median():.0f} "
          f"(minimum enforced: {MIN_ROWS})")
    print(f"  numerically unstable denominators (R2 with lags <= 0.01): {bad} "
          f"({bad/len(d):.1%}) -> D1 withheld, not winsorised")
    v = d[d.denominator_ok]
    print(f"\n  {'quantity':<22}{'p10':>10}{'p25':>10}{'p50':>10}{'p75':>10}{'p90':>10}")
    for c, nm in (("r2_contemp", "R2 contemporaneous"), ("r2_4lag", "R2 with 4 lags"),
                  ("d1", "D1"), ("beta_contemp", "beta contemporaneous")):
        q = v[c].quantile([.1, .25, .5, .75, .9])
        print(f"  {nm:<22}" + "".join(f"{x:>10.4f}" for x in q))
    print(f"\n  mean D1 {v.d1.mean():.4f}   sd {v.d1.std():.4f}")

    print("\n  lag coefficients (the sign is reported, not selected):")
    print(f"  {'lag':<8}{'mean':>11}{'median':>11}{'share > 0':>12}")
    for k in range(1, NLAG + 1):
        s = v[f"lag{k}"]
        print(f"  {k:<8}{s.mean():>11.4f}{s.median():>11.4f}{(s > 0).mean():>11.1%}")
    print(f"\n  joint test that all four lags are zero: rejected at 5% in "
          f"{(v.p_lags < 0.05).mean():.1%} of regressions")

    print("\n  by formation year:")
    t = v.groupby(v.formation.dt.year).agg(
        n=("d1", "size"), d1_med=("d1", "median"),
        r2c=("r2_contemp", "median"), r2u=("r2_4lag", "median"))
    print(t.to_string(float_format=lambda x: f"{x:9.4f}"))


def main():
    x = pd.read_parquet(XWALK)
    permnos = sorted(set(x.permno.dropna().astype(int)) | set(ETF_PERMNO.values()))
    names = (x.dropna(subset=["permno"]).groupby("permno").security_name.first()
              .to_dict())
    label = {int(k): str(v) for k, v in names.items()}
    label.update({v: k for k, v in ETF_PERMNO.items()})

    fr = []
    for y in range(2017, 2024):            # 2017-2018 is regression warm-up only
        d = pd.read_parquet(ppw.abspath(f"raw/crsp_dsf_{y}.parquet"),
                            columns=["permno", "date", "ret"])
        fr.append(d[d.permno.isin(permnos)])
    r = pd.concat(fr, ignore_index=True)
    r["date"] = pd.to_datetime(r.date)
    r["ret"] = pd.to_numeric(r.ret, errors="coerce")
    r = r.dropna(subset=["ret"]).drop_duplicates(["permno", "date"])

    dsi = pd.read_parquet(ppw.abspath("raw/crsp_dsi.parquet"),
                          columns=["date", "vwretd"])
    dsi["date"] = pd.to_datetime(dsi.date)
    dsi["ret"] = pd.to_numeric(dsi.vwretd, errors="coerce")
    dsi = dsi.dropna(subset=["ret"]).sort_values("date")

    print("=" * 92 + "\nHOU-MOSKOWITZ FIRST-STAGE DELAY (D1)\n" + "=" * 92)
    print("  benchmark   CRSP value-weighted index (vwretd), verified in stage 7;")
    print("              the original-style baseline needs no adaptation and the")
    print("              benchmark is not changed anywhere in this stage")
    print(f"  securities  {len(permnos):,} ({len(permnos)-3:,} constituents + 3 ETFs)")
    print(f"  returns     {r.date.min().date()}..{r.date.max().date()}, "
          f"2017-2018 read as regression warm-up only")
    print("  D1 = 1 - R2(contemporaneous only) / R2(contemporaneous + 4 lags),")
    print("  raw R-squared, identical rows in both models")

    # weekly panel
    wk_s = weekly(r)
    wk_m = weekly(dsi.assign(permno=0))
    wk_m = wk_m[wk_m.complete][["week", "ret"]].rename(columns={"week": "t",
                                                               "ret": "mkt"})
    wk_s = wk_s.rename(columns={"week": "t"})

    stocks = wk_s[~wk_s.permno.isin(ETF_PERMNO.values())]
    etfs = wk_s[wk_s.permno.isin(ETF_PERMNO.values())]
    w_stock = build(stocks, wk_m, "stock", "weekly", WEEKS, label)
    w_etf = build(etfs, wk_m, "etf", "weekly", WEEKS, label)
    report(w_stock, "WEEKLY D1, INDIVIDUAL SOURCE STOCKS")
    report(w_etf, "WEEKLY D1, ETF SECURITIES (ADAPTATION, NOT HM's SAMPLE)")
    if not w_etf.empty:
        print("\n  per instrument:")
        print(w_etf.pivot_table(index="label", columns=w_etf.formation.dt.year,
                                values="d1").to_string(
              float_format=lambda v: f"{v:8.4f}"))

    # daily sensitivity at a fixed frequency, declared in advance, not selected
    d_s = r.rename(columns={"date": "t"})[["permno", "t", "ret"]]
    d_m = dsi.rename(columns={"date": "t"})[["t", "ret"]].rename(
        columns={"ret": "mkt"})
    d_stock = build(d_s[~d_s.permno.isin(ETF_PERMNO.values())], d_m,
                    "stock", "daily", DAILY_WINDOW, label)
    d_etf = build(d_s[d_s.permno.isin(ETF_PERMNO.values())], d_m,
                  "etf", "daily", DAILY_WINDOW, label)
    report(d_stock, "DAILY FOUR-LAG SENSITIVITY, SOURCE STOCKS (FIXED FREQUENCY)")
    report(d_etf, "DAILY FOUR-LAG SENSITIVITY, ETF SECURITIES")

    out = pd.concat([w_stock, w_etf, d_stock, d_etf], ignore_index=True)
    out.to_parquet(ppw.OUT / "s3_delay.parquet", index=False)
    ppw.provenance("s3_01_delay", [XWALK], {
        "regressions": int(len(out)), "min_rows": MIN_ROWS,
        "formation_dates": FORMATION, "benchmark": "crsp_dsi.vwretd"})
    print("\n" + "=" * 92)
    print("  These are market-response delay measures at daily and weekly")
    print("  resolution. They do not estimate firm-news event speed, do not")
    print("  identify a causal ETF-to-stock channel, and cannot establish")
    print("  minute-level or subminute leadership in either direction.")
    print("  written: s3_delay.parquet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
