"""assert_panel.py — E2-T6a: the 15-assertion battery (A1–A15 from the E2 manual).

The contract check (ops/contracts/panel_daily.yaml) is the cross-task *handshake*
subset; this is the full gate. `run_assertions(panel, ctx)` executes all 15 and
returns per-assertion results. The panel is fit to be written ONLY if none FAIL.

Rule (from the manual): never mutate upstream data to pass an assertion — an
upstream problem is reported as UPSTREAM_ISSUE, not patched away.

Assertions that need an upstream frame (flows, registry, decomposition, manifest)
report SKIP when it isn't supplied, so the battery is still meaningful when run on
a bare panel file; a real T6a run supplies the full ctx and nothing skips.
"""
import sys, json, pathlib
import numpy as np
import pandas as pd

REQUIRED = ["market_id", "date", "gross_usd", "net_usd", "lambda", "utilization",
            "borrow_apy", "supply_apy", "rwa_apy", "spread", "hhi", "top10_share",
            "contract_share", "nav", "nav_source", "oracle_staleness_hours", "is_active"]


class Result:
    def __init__(self, aid, desc, status, detail=""):
        self.aid, self.desc, self.status, self.detail = aid, desc, status, detail


def _ok(aid, desc, detail=""):   return Result(aid, desc, "PASS", detail)
def _no(aid, desc, detail):      return Result(aid, desc, "FAIL", detail)
def _skip(aid, desc, detail):    return Result(aid, desc, "SKIP", detail)


def run_assertions(panel, ctx=None):
    ctx = ctx or {}
    p = panel
    R = []

    # A1 — primary key uniqueness
    dup = int(p.duplicated(["market_id", "date"]).sum())
    R.append(_ok("A1", "PK (market_id,date) unique") if dup == 0
             else _no("A1", "PK unique", f"{dup} duplicate (market_id,date) rows"))

    # A2 — no date gaps per market (inactive days still present)
    gaps = []
    for mid, g in p.groupby("market_id"):
        d = pd.to_datetime(g["date"]).sort_values()
        full = pd.date_range(d.min(), d.max(), freq="D")
        if len(full) != d.nunique():
            gaps.append(f"{mid}: {len(full) - d.nunique()} missing days")
    R.append(_ok("A2", "no date gaps per market") if not gaps
             else _no("A2", "no date gaps per market", "; ".join(gaps)))

    # A3 — gross >= net >= 0 and lambda = gross/net when net>0
    bad = p[(p.net_usd < 0) | (p.gross_usd < p.net_usd)]
    m = p.net_usd > 0
    lam_err = (p.loc[m, "lambda"] - p.loc[m, "gross_usd"] / p.loc[m, "net_usd"]).abs()
    lam_bad = int((lam_err > 1e-9 * (1 + p.loc[m, "gross_usd"] / p.loc[m, "net_usd"])).sum())
    if len(bad) == 0 and lam_bad == 0:
        R.append(_ok("A3", "gross>=net>=0; lambda=gross/net"))
    else:
        R.append(_no("A3", "gross>=net>=0; lambda=gross/net",
                     f"{len(bad)} ordering viol, {lam_bad} lambda mismatches"))

    # A4 — utilization in [0,1], borrow_apy in [0,5]  (lltv<->events: needs events)
    u_bad = int(((p.utilization < 0) | (p.utilization > 1)).sum())
    b_bad = int(((p.borrow_apy < 0) | (p.borrow_apy > 5)).sum())
    lltv = "lltv/events check skipped (no events frame)" if "events" not in ctx else ""
    R.append(_ok("A4", "utilization∈[0,1]; borrow_apy∈[0,5]", lltv) if u_bad == b_bad == 0
             else _no("A4", "utilization∈[0,1]; borrow_apy∈[0,5]",
                      f"{u_bad} util oob, {b_bad} apy oob"))

    # A5 — amounts in USD; nav_source non-null
    nsrc = int(p.nav_source.isna().sum())
    amt_bad = int((~np.isfinite(p[["gross_usd", "net_usd"]].to_numpy(float))).sum())
    R.append(_ok("A5", "USD amounts; nav_source non-null") if nsrc == amt_bad == 0
             else _no("A5", "USD amounts; nav_source non-null",
                      f"{nsrc} null nav_source, {amt_bad} non-finite amounts"))

    # A6 — post-launch NAV coverage >= 95% per market
    low = []
    for mid, g in p.groupby("market_id"):
        cov = g.nav.notna().mean()
        if cov < 0.95:
            low.append(f"{mid}: {cov:.1%}")
    R.append(_ok("A6", "NAV coverage >=95%") if not low
             else _no("A6", "NAV coverage >=95%", "; ".join(low)))

    # A7 — accrual NAV monotone (ex-dividend); rebasing NAV in [0.98,1.02]
    if "registry" in ctx:
        reg = ctx["registry"].set_index("market_id")["accrual"].to_dict()
        probs = []
        for mid, g in p.groupby("market_id"):
            nav = g.sort_values("date")["nav"].to_numpy(float)
            if reg.get(mid):
                drops = int((np.diff(nav) < -1e-9).sum())
                if drops:
                    probs.append(f"{mid}: {drops} NAV decreases")
            else:
                oob = int(((nav < 0.98) | (nav > 1.02)).sum())
                if oob:
                    probs.append(f"{mid}: {oob} rebasing NAV out of [0.98,1.02]")
        R.append(_ok("A7", "NAV regime (accrual monotone / rebasing band)") if not probs
                 else _no("A7", "NAV regime", "; ".join(probs)))
    else:
        R.append(_skip("A7", "NAV regime", "no registry frame in ctx"))

    # A8 — no future oracle data (staleness measured backwards, so >= 0)
    o_bad = int((p.oracle_staleness_hours < 0).sum())
    R.append(_ok("A8", "oracle timestamps not in the future") if o_bad == 0
             else _no("A8", "oracle not future", f"{o_bad} negative staleness"))

    # A9 — hhi∈(0,1]; top10_share∈(0,1]; contract_share∈[0,1]  (active rows)
    a = p[p.is_active]
    h_bad = int(((a.hhi <= 0) | (a.hhi > 1)).sum())
    t_bad = int(((a.top10_share <= 0) | (a.top10_share > 1)).sum())
    c_bad = int(((a.contract_share < 0) | (a.contract_share > 1)).sum())
    R.append(_ok("A9", "concentration shares in range") if h_bad == t_bad == c_bad == 0
             else _no("A9", "concentration shares in range",
                      f"hhi {h_bad}, top10 {t_bad}, contract {c_bad} oob"))

    # A10 — gross day-over-day change reconciles with flows (<0.5%)
    if "flows" in ctx:
        f = ctx["flows"].set_index(["market_id", "date"])["net_flow_usd"]
        worst = 0.0
        for mid, g in p.groupby("market_id"):
            g = g.sort_values("date")
            dgross = g.gross_usd.diff().fillna(g.gross_usd)
            fl = f.reindex([(mid, d) for d in g.date]).to_numpy(float)
            denom = np.maximum(1.0, g.gross_usd.to_numpy(float))
            worst = max(worst, float(np.max(np.abs(dgross.to_numpy(float) - fl) / denom)))
        R.append(_ok("A10", "gross change reconciles with flows", f"max rel err {worst:.2e}")
                 if worst < 0.005 else _no("A10", "gross vs flows", f"max rel err {worst:.2%}"))
    else:
        R.append(_skip("A10", "gross vs flows", "no flows frame in ctx"))

    # A11 — spread = rwa_apy - borrow_apy, recomputable per row
    s_err = float((p.spread - (p.rwa_apy - p.borrow_apy)).abs().max())
    R.append(_ok("A11", "spread = rwa_apy - borrow_apy") if s_err <= 1e-9
             else _no("A11", "spread identity", f"max abs err {s_err:.2e}"))

    # A12 — lambda decomposition k matches decomposition.parquet config
    if "decomposition" in ctx:
        dk = ctx["decomposition"].set_index("market_id")["k"].to_dict()
        mism = []
        for mid, g in p.groupby("market_id"):
            if not np.allclose(g.lambda_k.to_numpy(float), dk.get(mid, np.nan), equal_nan=False):
                mism.append(mid)
        R.append(_ok("A12", "lambda_k matches decomposition config") if not mism
                 else _no("A12", "lambda_k vs decomposition", f"mismatch: {mism}"))
    else:
        R.append(_skip("A12", "lambda_k vs decomposition", "no decomposition frame in ctx"))

    # A13 — row count = sum of per-market interval days (manifest)
    if "manifest" in ctx:
        man = ctx["manifest"]
        exp = man.get("total_rows")
        per_ok = all(int((p.market_id == mid).sum()) == meta["interval_days"]
                     for mid, meta in man.get("markets", {}).items())
        R.append(_ok("A13", "row count matches manifest", f"{len(p)} rows")
                 if len(p) == exp and per_ok else
                 _no("A13", "row count vs manifest", f"got {len(p)}, manifest {exp}, per_market_ok={per_ok}"))
    else:
        R.append(_skip("A13", "row count vs manifest", "no manifest in ctx"))

    # A14 — no column entirely NaN; record per-column missing rates
    allnan = [c for c in p.columns if p[c].isna().all()]
    miss = {c: round(float(p[c].isna().mean()), 4) for c in p.columns}
    if "manifest" in ctx:
        ctx["manifest"]["missing_rates"] = miss
    R.append(_ok("A14", "no all-NaN column; missing rates recorded",
                 f"max missing {max(miss.values()):.1%}") if not allnan
             else _no("A14", "no all-NaN column", f"all-NaN: {allnan}"))

    # A15 — trace 20 random rows back to source (recompute derived cols)
    rng = np.random.default_rng(0)
    idx = rng.choice(len(p), size=min(20, len(p)), replace=False)
    sample = p.iloc[idx]
    active = sample[sample.net_usd > 0]
    net_err = float((active.net_usd - active.gross_usd / active["lambda"]).abs().max() or 0.0)
    sp_err = float((sample.spread - (sample.rwa_apy - sample.borrow_apy)).abs().max())
    R.append(_ok("A15", "20-row source trace", f"net err {net_err:.1e}, spread err {sp_err:.1e}")
             if net_err <= 1e-6 and sp_err <= 1e-9
             else _no("A15", "20-row source trace", f"net err {net_err:.1e}, spread err {sp_err:.1e}"))

    return R


def format_results(results):
    lines = ["  15-assertion battery (E2-T6a):"]
    for r in results:
        mark = {"PASS": "✓", "FAIL": "✗", "SKIP": "•"}[r.status]
        lines.append(f"   {mark} [{r.status}] {r.aid}  {r.desc}"
                     + (f"  — {r.detail}" if r.detail else ""))
    n_fail = sum(r.status == "FAIL" for r in results)
    n_skip = sum(r.status == "SKIP" for r in results)
    lines.append(f"  => {len(results) - n_fail - n_skip} pass, {n_fail} fail, {n_skip} skip")
    return "\n".join(lines)


def _read(path):
    p = pathlib.Path(path)
    if p.suffix == ".parquet":
        return pd.read_parquet(p)
    if p.suffix in (".csv", ".tsv"):
        return pd.read_csv(p, sep="\t" if p.suffix == ".tsv" else ",", parse_dates=["date"])
    raise SystemExit(f"cannot read {p.suffix}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="run the 15-assertion panel battery")
    ap.add_argument("panel", help="path to panel_daily (.parquet/.csv)")
    a = ap.parse_args()
    results = run_assertions(_read(a.panel), ctx=None)   # bare file: ctx-dependent ones SKIP
    print(format_results(results))
    sys.exit(1 if any(r.status == "FAIL" for r in results) else 0)
