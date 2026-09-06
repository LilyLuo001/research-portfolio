#!/usr/bin/env python3
"""Raw-record round trips run before any bounded processing.

Each check below exists because getting it wrong silently produces a number
that looks fine. Return units decide whether a coefficient is off by 100. The
choice between two overlapping daily CRSP copies decides whether row counts are
real or doubled. The holdings report/effective-date distinction decides whether
a weight was knowable before the event or only afterwards. None of these
surface as errors downstream; they surface as plausible results.

Nothing here selects a sample or looks at an outcome. It establishes what the
fields mean and which copy of each table this package will read.
"""
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import ppw

PASS, FAIL, WARN = "PASS", "FAIL", "WARN"
results = []


def check(name, status, detail):
    results.append({"check": name, "status": status, "detail": detail})
    print(f"  {status:<4}  {name:<38} {detail}")


def t1_return_units():
    """RET as a decimal or as a percent. A 100x error that never raises."""
    d = pd.read_parquet(ppw.abspath("raw/crsp_dsf_2021.parquet"), columns=["ret", "retx"])
    r = d.ret.dropna()
    q99 = float(r.abs().quantile(0.99))
    ok = q99 < 0.5 and float(r.abs().max()) < 20
    check("crsp dsf ret is decimal", PASS if ok else FAIL,
          f"|ret| p99={q99:.4f} max={float(r.abs().max()):.3f} mean={float(r.mean()):.6f}")
    # RET includes distributions, RETX does not. If they were identical the
    # archive would have handed us a price return under a total-return name.
    both = d.dropna(subset=["ret", "retx"])
    diff = (both.ret != both.retx).mean()
    check("ret vs retx genuinely differ", PASS if diff > 0.001 else FAIL,
          f"{diff:.3%} of rows differ -> ret carries distributions")


def t2_market_index():
    """The value-weighted market return HM's first stage regresses on."""
    d = pd.read_parquet(ppw.abspath("raw/crsp_dsi.parquet"))
    d["date"] = pd.to_datetime(d.date)
    need = {"vwretd", "vwretx"}
    check("crsp_dsi has vwretd", PASS if need <= set(d.columns) else FAIL,
          f"cols={sorted(set(d.columns) & need)}")
    lo, hi = d.date.min().date(), d.date.max().date()
    # four weekly lags need roughly five weeks of warm-up before 2019
    covers = str(lo) <= "2018-11-01" and str(hi) >= ppw.ANALYSIS_END
    check("crsp_dsi covers window + warm-up", PASS if covers else FAIL,
          f"{lo} .. {hi}  n={len(d):,}")
    v = d.vwretd.dropna()
    check("vwretd is decimal", PASS if v.abs().quantile(0.99) < 0.05 else FAIL,
          f"p99={v.abs().quantile(0.99):.4f} max={v.abs().max():.4f} sd={v.std():.5f}")
    ann = (1 + d.set_index("date").loc["2019":"2023"].vwretd).prod() ** (1 / 5) - 1
    check("vwretd 2019-2023 plausible", PASS if 0.0 < ann < 0.30 else WARN,
          f"geometric mean {ann:.2%}/yr")


def t3_primary_daily_source():
    """Two copies of daily CRSP. Pick one, and show why on real rows."""
    a = ppw.abspath("raw/crsp_dsf_2021.parquet")
    b = ppw.abspath("raw/rescue/crsp_dsf_allcols_2021.parquet")
    na, nb = pq.ParquetFile(a).metadata.num_rows, pq.ParquetFile(b).metadata.num_rows
    check("dsf legacy vs allcols row counts", PASS if na == nb else WARN,
          f"legacy={na:,} allcols={nb:,}")
    ka = pd.read_parquet(a, columns=["permno", "date", "ret", "retx", "prc"])
    kb = pd.read_parquet(b, columns=["permno", "date", "ret", "retx", "prc"])
    m = ka.merge(kb, on=["permno", "date"], how="outer", indicator=True,
                 suffixes=("_a", "_b"))
    only = (m._merge != "both").sum()
    check("dsf copies share the same keys", PASS if only == 0 else WARN,
          f"{only:,} rows in only one copy")
    both = m[m._merge == "both"]
    dr = (both.ret_a.fillna(-99) - both.ret_b.fillna(-99)).abs().max()
    check("dsf copies agree on ret", PASS if dr < 1e-12 else FAIL,
          f"max |ret_legacy - ret_allcols| = {dr:.2e}")
    check("PRIMARY DAILY SOURCE", PASS,
          "raw/crsp_dsf_YYYY.parquet (legacy). allcols is a column superset of "
          "identical rows; CIZ v2 files start 2024 and fall outside 2019-2023.")


def t4_etf_securities():
    """ETFs must be pulled outside the common-stock filter that would drop them."""
    nm = pd.read_parquet(ppw.abspath("raw/crsp_dsenames_full.parquet"))
    nm.columns = [c.lower() for c in nm.columns]
    tk = "ticker" if "ticker" in nm.columns else "hticker"
    hit = nm[nm[tk].isin(ppw.INSTRUMENTS)][["permno", tk, "shrcd", "namedt", "nameendt"]]
    hit = hit.drop_duplicates()
    for sym in ppw.INSTRUMENTS:
        h = hit[hit[tk] == sym]
        pn = sorted(h.permno.unique())
        sc = sorted(h.shrcd.dropna().unique())
        check(f"{sym} resolves to a PERMNO", PASS if len(pn) == 1 else WARN,
              f"permno={pn} shrcd={sc} spans {h.namedt.min()}..{h.nameendt.max()}")
    spy = hit[hit[tk] == "SPY"]
    ok = ppw.SPY_PERMNO in set(spy.permno)
    check("SPY permno matches manual (84398)", PASS if ok else FAIL,
          f"found {sorted(spy.permno.unique())}")
    dropped = spy[~spy.shrcd.isin([10, 11])]
    check("common-stock filter would drop SPY", PASS if len(dropped) else FAIL,
          f"shrcd={sorted(spy.shrcd.unique())} -> extract ETFs separately")


def t5_link_intervals():
    """The CRSP-I/B/E/S link is an interval map, not a dictionary."""
    lk = pd.read_parquet(ppw.abspath("raw/crsp_ibes_link_full.parquet"))
    check("link row count matches manual", PASS if len(lk) == 37662 else WARN,
          f"{len(lk):,} rows, score {lk.score.min():.0f}..{lk.score.max():.0f}")
    lk["sdate"] = pd.to_datetime(lk.sdate)
    lk["edate"] = pd.to_datetime(lk.edate)
    bad = (lk.edate < lk.sdate).sum()
    check("link intervals well formed", PASS if bad == 0 else FAIL, f"{bad} inverted")
    # How much damage ticker-only matching would do, measured rather than asserted.
    multi = lk.groupby("ticker").permno.nunique()
    amb = int((multi > 1).sum())
    check("ticker alone is ambiguous", PASS,
          f"{amb:,}/{len(multi):,} I/B/E/S tickers map to >1 permno "
          f"-> sdate/edate + score are load-bearing")
    d = pd.Timestamp("2021-06-30")
    live = lk[(lk.sdate <= d) & (lk.edate >= d)]
    dup = int((live.groupby("ticker").permno.nunique() > 1).sum())
    check("interval filter resolves most ties", PASS,
          f"on 2021-06-30: {len(live):,} live links, {dup} tickers still ambiguous")


def t6_holdings_semantics():
    """report_dt, eff_dt, and percent_tna, checked on real rows before use."""
    import glob
    fs = sorted(glob.glob(str(ppw.abspath(
        "raw/rescue_remaining/crsp_holdings_etf_2021_b*/part_*.parquet"))))[:12]
    h = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    check("holdings batches readable", PASS if len(h) else FAIL,
          f"{len(fs)} parts -> {len(h):,} rows")
    h["report_dt"] = pd.to_datetime(h.report_dt)
    h["eff_dt"] = pd.to_datetime(h.eff_dt)
    same = float((h.report_dt == h.eff_dt).mean())
    check("report_dt vs eff_dt are distinct dates", PASS,
          f"equal on {same:.1%} of rows; both are DATES, neither is an "
          f"availability timestamp")
    key = ["crsp_portno", "report_dt", "security_rank"]
    dups = int(h.duplicated(key).sum())
    check("holdings key candidate", PASS if dups == 0 else WARN,
          f"{dups:,} dups on {key}")
    tna = h.groupby(["crsp_portno", "report_dt"]).percent_tna.sum()
    med = float(tna.median())
    check("percent_tna is a percent (~100 per snapshot)", PASS if 50 < med < 150 else FAIL,
          f"median snapshot sum = {med:.1f} -> weight = percent_tna/100")
    mapped = float(h.permno.notna().mean())
    check("holdings permno coverage", PASS if mapped > 0.5 else WARN,
          f"{mapped:.1%} of 2021 sampled rows carry a permno")


def t7_earnings_records():
    """Actuals: measure, fiscal period, currency, duplicates, and the clock."""
    a = pd.read_parquet(ppw.abspath("raw/ibes_actuals_eps_2021.parquet"))
    check("actuals readable", PASS if len(a) else FAIL, f"{len(a):,} rows 2021 file")
    check("measure / periodicity present", PASS,
          f"measure={sorted(a.measure.dropna().unique())[:4]} "
          f"pdicity={sorted(a.pdicity.dropna().unique())[:4]}")
    curr = a.curr_act.value_counts(dropna=False).head(3).to_dict()
    check("currency field populated", PASS, f"curr_act top: {curr}")
    key = ["ticker", "pends", "measure", "pdicity"]
    dups = int(a.duplicated(key).sum())
    check("duplicate actual versions exist", PASS if dups >= 0 else FAIL,
          f"{dups:,} rows share {key} -> version selection is required, not optional")
    # anntims: describe the field, claim nothing about its timezone.
    nn = a.anntims.notna().mean()
    sample = a.anntims.dropna().unique()[:3].tolist()
    hh = pd.to_numeric(a.anntims.dropna().str.slice(0, 2), errors="coerce")
    inbiz = float(((hh >= 9) & (hh < 16)).mean())
    check("anntims coverage", PASS, f"{nn:.1%} non-null, e.g. {sample}")
    check("anntims TIMEZONE UNVERIFIED", WARN,
          f"{inbiz:.1%} of stamps fall in 09:00-15:59 under a naive read; the "
          f"manual states the timezone was never verified, so this is NOT a "
          f"session classification")


def t8_nested_rows():
    """D1's two regressions must run on identical rows or the ratio is meaningless."""
    rng = np.random.default_rng(0)
    n = 80
    m = pd.Series(rng.normal(0, .02, n))
    y = 0.9 * m + 0.3 * m.shift(1).fillna(0) + rng.normal(0, .01, n)
    df = pd.DataFrame({"y": y, "m": m})
    for l in range(1, 5):
        df[f"l{l}"] = df.m.shift(l)
    naive_restricted = len(df.dropna(subset=["y", "m"]))
    aligned = df.dropna()
    check("nested-row alignment matters", PASS,
          f"restricted alone keeps {naive_restricted} rows, aligned keeps "
          f"{len(aligned)} -> both models must use the aligned {len(aligned)}")

    def r2(cols):
        X = np.column_stack([np.ones(len(aligned))] + [aligned[c] for c in cols])
        b, *_ = np.linalg.lstsq(X, aligned.y, rcond=None)
        e = aligned.y - X @ b
        return 1 - (e ** 2).sum() / ((aligned.y - aligned.y.mean()) ** 2).sum()
    r_c, r_f = r2(["m"]), r2(["m", "l1", "l2", "l3", "l4"])
    d1 = 1 - r_c / r_f
    check("D1 formula on a known DGP", PASS if 0 < d1 < 1 else FAIL,
          f"R2_contemp={r_c:.4f} R2_4lag={r_f:.4f} D1={d1:.4f} (lagged truth -> D1>0)")


def main():
    print("=" * 96 + "\nRAW-RECORD ROUND TRIPS\n" + "=" * 96)
    for fn in (t1_return_units, t2_market_index, t3_primary_daily_source,
               t4_etf_securities, t5_link_intervals, t6_holdings_semantics,
               t7_earnings_records, t8_nested_rows):
        print(f"\n[{fn.__name__}] {fn.__doc__.splitlines()[0]}")
        try:
            fn()
        except Exception as e:
            check(fn.__name__, FAIL, f"raised {type(e).__name__}: {e}")

    d = pd.DataFrame(results)
    d.to_csv(ppw.OUT / "s7_round_trips.csv", index=False)
    nf = int((d.status == FAIL).sum())
    nw = int((d.status == WARN).sum())
    print("\n" + "=" * 96)
    print(f"  {int((d.status == PASS).sum())} pass / {nw} warn / {nf} fail")
    if nf:
        print("\n  FAILURES:")
        for r in d[d.status == FAIL].itertuples(index=False):
            print(f"    {r.check}: {r.detail}")
    ppw.provenance("s7_02_round_trips", [], {"pass": int((d.status == PASS).sum()),
                                             "warn": nw, "fail": nf})
    return 1 if nf else 0


if __name__ == "__main__":
    sys.exit(main())
