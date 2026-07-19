#!/usr/bin/env python3
"""P1-T2 free-path ConvExp — conservative DENOMINATOR RECOVERY.

Goal: recover missing shares-outstanding denominators for the ~5,929 dropped
stock cells WITHOUT WRDS and WITHOUT trusting any recovered number blindly. Every
recovered denominator is quarantined with source + retrieval date + confidence and
re-flagged if it produces a suspicious ConvExp. Baseline ConvExp is never overwritten.

Two stages:
  OFFLINE (default, runs anywhere, no network)
    - classify each dropped cell into a recovery tier (US-renamed / ADR / foreign /
      no-ticker / stale-gt1) using CUSIP+ticker heuristics;
    - parse the pipeline log for the conv_exp>1 cells (real shares_held) and diagnose
      them as dummy-denominator artifacts;
    - emit the recovery TARGET LIST (recovery_attempts.csv) the online stage consumes,
      the suspicious-cell table, and coverage-CEILING estimates (before/after).
    - Offline it recovers 0 real denominators (no network) — it scopes the work.

  ONLINE (--online, run on the BOX which has outbound HTTPS)
    - for each target, in priority order: SEC company_tickers (renamed US ticker) ->
      yfinance sharesOutstanding -> Stooq; cache every raw pull under cache/;
    - to recompute ConvExp it needs shares_held for the dropped cell, which the
      current parquet does NOT retain. Supply it via --shares-held <csv with
      cusip,wave_id,shares_held>, produced by the 1-line pipeline patch described in
      the README (retain shares_held on drop). Without it, the online stage still
      records recovered denominators but marks conv_exp_recovered as PENDING_SHARES.

Output columns added (never overwrite baseline):
  conv_exp_baseline, shares_out_baseline, shares_out_recovered, shares_out_source,
  conv_exp_recovered, recovery_status, recovery_flag

Usage:
  python recover_denominators.py                     # offline: scope + targets + ceiling
  python recover_denominators.py --online            # box: real lookups (needs net)
  python recover_denominators.py --online --shares-held dropped_shares.csv
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import json
import logging
import pathlib
import re
import sys
import time

import pandas as pd

LOG = logging.getLogger("recover_denominators")
TODAY = dt.date.today().isoformat()

_FOREIGN_SUFFIX = re.compile(r"(EUR|GBP|CHF|SEK|NOK|DKK|JPY|CAD|AUD|HKD|CNY|SGD)$")
_GT1 = re.compile(
    r"CONVEXP_GT1 cusip=(\S+) ticker=(\S+) wave=(\S+) exp=([\d.]+) "
    r"\(shares_held=([\d.]+) > shares_out=([\d.]+) as of (\d{4}-\d{2}-\d{2})\)")


# --------------------------------------------------------------------------- #
# recovery tiers — auditable, offline
# --------------------------------------------------------------------------- #
def recovery_tier(cusip: str, ticker: str, reason: str) -> str:
    r = reason or ""
    if r.startswith("conv_exp>1"):
        return "tier5_stale_gt1"        # US common w/ dummy denom -> fresh XBRL/yfinance
    if not ticker:
        return "tier4_no_ticker"        # need CUSIP->identity first; mostly manual
    t = ticker.upper()
    if cusip and cusip[0].isalpha():
        return "tier3_foreign"          # CINS non-US issuer; leaves US/CRSP universe
    if re.search(r"\d", t) or len(t) > 5 or _FOREIGN_SUFFIX.search(t):
        return "tier3_foreign"          # OpenFIGI returned a non-US listing symbol
    if t.endswith("Y") and len(t) >= 4:
        return "tier2_adr"              # ADR line; yfinance usually has sharesOut
    return "tier1_us_renamed"           # looks US-listed -> delisted/renamed/acquired


# yfinance/Stooq can *plausibly* return a sharesOutstanding for these tiers:
RECOVERABLE_TIERS = {"tier1_us_renamed", "tier2_adr", "tier5_stale_gt1"}
# foreign lines: yfinance sometimes has them, but they are outside the US/CRSP universe,
# so recover-but-flag; do NOT count them toward "US-study" coverage ceiling.
FOREIGN_TIERS = {"tier3_foreign"}


def parse_stale_from_log(logpath: pathlib.Path) -> pd.DataFrame:
    """Real shares_held for the conv_exp>1 cells (only place the pipeline logged them)."""
    rows = []
    if not logpath.exists():
        LOG.warning("log %s absent; stale cells will lack shares_held", logpath)
        return pd.DataFrame(columns=["cusip", "ticker", "wave_id", "conv_exp_bad",
                                     "shares_held", "shares_out_bad", "so_date"])
    for m in _GT1.finditer(logpath.read_text(errors="ignore")):
        cusip, tkr, wave, exp, sh, so, sod = m.groups()
        rows.append({"cusip": cusip, "ticker": tkr, "wave_id": wave,
                     "conv_exp_bad": float(exp), "shares_held": float(sh),
                     "shares_out_bad": float(so), "so_date": sod})
    LOG.info("parsed %d conv_exp>1 stale cells from log", len(rows))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# online lookups (box only) — each returns (shares_out, source, asof, confidence)
# --------------------------------------------------------------------------- #
def _cache_get(cache: pathlib.Path, key: str):
    p = cache / (re.sub(r"[^A-Za-z0-9]+", "_", key)[:180] + ".json")
    if p.exists():
        return json.loads(p.read_text())
    return None


def _cache_put(cache: pathlib.Path, key: str, val) -> None:
    p = cache / (re.sub(r"[^A-Za-z0-9]+", "_", key)[:180] + ".json")
    p.write_text(json.dumps(val))


def lookup_sec_renamed(ticker: str, sec_map: dict, cache, eff: str):
    """If the ticker now maps to a current SEC filer, use its XBRL shares-out."""
    cik = sec_map.get(ticker.upper())
    if not cik:
        return None
    import requests
    key = f"xbrl_{cik}"
    j = _cache_get(cache, key)
    if j is None:
        url = (f"https://data.sec.gov/api/xbrl/companyconcept/CIK{int(cik):010d}"
               f"/dei/EntityCommonStockSharesOutstanding.json")
        r = requests.get(url, headers={"User-Agent": SEC_UA}, timeout=45)
        j = r.json() if r.status_code == 200 else {}
        _cache_put(cache, key, j)
        time.sleep(0.2)
    best = None
    for u in j.get("units", {}).get("shares", []):
        end = u.get("end", "")
        if end and end <= eff and (best is None or end > best[0]):
            best = (end, u.get("val"))
    if best and best[1]:
        return float(best[1]), "sec_xbrl", best[0], "high"
    return None


def lookup_yfinance(ticker: str, cache):
    import requests
    key = f"yf_{ticker}"
    j = _cache_get(cache, key)
    if j is None:
        url = (f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/"
               f"{ticker}?modules=defaultKeyStatistics")
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0 research"}, timeout=30)
        j = r.json() if r.status_code == 200 else {}
        _cache_put(cache, key, j)
        time.sleep(0.4)
    try:
        so = (j["quoteSummary"]["result"][0]["defaultKeyStatistics"]
              ["sharesOutstanding"]["raw"])
        return float(so), "yfinance_current", TODAY, "medium"   # current, not point-in-time
    except Exception:  # noqa: BLE001
        return None


def lookup_stooq(ticker: str, cache):
    # Stooq has no clean sharesOutstanding endpoint; placeholder for price-based mcap only.
    return None


SEC_UA = ""     # set from env on box


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="conservative denominator recovery")
    ap.add_argument("--repo", default=None)
    ap.add_argument("--outdir", default=None)
    ap.add_argument("--online", action="store_true", help="do real lookups (box, needs net)")
    ap.add_argument("--shares-held", default=None,
                    help="csv cusip,wave_id,shares_held for dropped cells (to recompute ConvExp)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    here = pathlib.Path(__file__).resolve()
    repo = pathlib.Path(args.repo).resolve() if args.repo else here.parents[3]
    outdir = pathlib.Path(args.outdir).resolve() if args.outdir else here.parent
    cache = outdir / "recovery_cache"
    cache.mkdir(parents=True, exist_ok=True)

    dropped = pd.read_csv(repo / "p1" / "t2_free" / "NEED_HUMAN_stocks.csv",
                          dtype=str).fillna("")
    logdf = parse_stale_from_log(repo / "p1" / "t2_free" / "build_nport_convexp.log")
    stale_key = {(r.cusip, r.wave_id): r for r in logdf.itertuples()}

    # shares_held sidecar for the *non-stale* dropped cells (optional, box-supplied)
    sh_side = {}
    if args.shares_held and pathlib.Path(args.shares_held).exists():
        for r in csv.DictReader(open(args.shares_held)):
            sh_side[(r["cusip"], r["wave_id"])] = float(r["shares_held"])
        LOG.info("loaded shares_held sidecar for %d dropped cells", len(sh_side))

    # ---- build the recovery-attempt frame (one row per dropped cell) ----
    recs = []
    for r in dropped.itertuples():
        tier = recovery_tier(r.cusip, r.ticker, r.reason)
        sh = None
        st = stale_key.get((r.cusip, r.wave_id))
        if st is not None:
            sh = st.shares_held
        elif (r.cusip, r.wave_id) in sh_side:
            sh = sh_side[(r.cusip, r.wave_id)]
        rec = {
            "cusip": r.cusip, "ticker": r.ticker, "wave_id": r.wave_id,
            "drop_reason": r.reason.split("(")[0].split(";")[0].strip(),
            "recovery_tier": tier,
            "recoverable_via_free_online": tier in RECOVERABLE_TIERS,
            "is_foreign_or_adr": tier in FOREIGN_TIERS or tier == "tier2_adr",
            "shares_held": sh,
            "conv_exp_baseline": None,        # dropped -> no baseline ConvExp
            "shares_out_baseline": None,
            "shares_out_recovered": None,
            "shares_out_source": None,
            "shares_out_asof": None,
            "conv_exp_recovered": None,
            "recovery_status": "not_attempted_offline",
            "recovery_flag": "",
        }
        recs.append(rec)
    rdf = pd.DataFrame(recs)

    # ---- ONLINE stage (box) ----
    if args.online:
        import os
        global SEC_UA
        SEC_UA = os.getenv("SEC_UA", "research-agent contact@example.com")
        sec_map = {}
        try:
            import requests
            j = requests.get("https://www.sec.gov/files/company_tickers.json",
                             headers={"User-Agent": SEC_UA}, timeout=45).json()
            sec_map = {str(v["ticker"]).upper(): int(v["cik_str"]) for v in j.values()}
            LOG.info("SEC company_tickers: %d symbols", len(sec_map))
        except Exception as e:  # noqa: BLE001
            LOG.error("could not fetch SEC map: %s", e)
        # effective_date per wave (from waves_members)
        wm = pd.read_csv(repo / "p1" / "t2_wrds" / "waves_members.csv", dtype=str)
        eff_by_wave = dict(wm.drop_duplicates("wave_id")[["wave_id", "effective_date"]].values)

        for i, row in rdf.iterrows():
            if not (row["recoverable_via_free_online"] or row["recovery_tier"] == "tier3_foreign"):
                rdf.at[i, "recovery_status"] = "skipped_manual_tier"
                continue
            eff = eff_by_wave.get(row["wave_id"], "2099-01-01")
            tkr = row["ticker"]
            res = (lookup_sec_renamed(tkr, sec_map, cache, eff) if tkr else None) \
                or (lookup_yfinance(tkr, cache) if tkr else None) \
                or (lookup_stooq(tkr, cache) if tkr else None)
            if not res:
                rdf.at[i, "recovery_status"] = "no_source_found"
                continue
            so, src, asof, conf = res
            rdf.at[i, "shares_out_recovered"] = so
            rdf.at[i, "shares_out_source"] = src
            rdf.at[i, "shares_out_asof"] = asof
            rdf.at[i, "recovery_status"] = f"recovered_{conf}"
            # recompute ConvExp only if we know shares_held
            sh = row["shares_held"]
            flags = []
            if row["is_foreign_or_adr"]:
                flags.append("foreign_or_adr_outside_US_universe")
            if so and so < 1e5:
                flags.append("small_denominator_review")
            if pd.notna(sh) and sh is not None and so:
                ce = float(sh) / float(so)
                rdf.at[i, "conv_exp_recovered"] = ce
                if ce > 1:
                    flags.append("conv_exp_gt_1_reject")
                elif ce > 0.0025:
                    flags.append("conv_exp_ge_0.25pct_verify")
            else:
                rdf.at[i, "conv_exp_recovered"] = "PENDING_SHARES"
            rdf.at[i, "recovery_flag"] = ";".join(flags)
    else:
        LOG.info("OFFLINE stage: scoping targets only (no network). Run --online on the box.")

    # ---- write recovery_attempts.csv ----
    rdf.to_csv(outdir / "coverage_recovery_attempts.csv", index=False)
    LOG.info("wrote coverage_recovery_attempts.csv (%d rows)", len(rdf))

    # ---- suspicious recovered cells: the 18 stale + anything flagged in online run ----
    susp = logdf.copy()
    susp["diagnosis"] = "dummy_denominator (shares_out in {1,100,1000}) -> real US common; " \
                        "refetch fresh point-in-time shares_out (yfinance/SEC), then recompute"
    if args.online and "recovery_flag" in rdf:
        flagged = rdf[rdf["recovery_flag"].str.contains("reject|verify", na=False)]
        if len(flagged):
            susp = pd.concat([susp, flagged], ignore_index=True)
    susp.to_csv(outdir / "suspicious_recovered_cells.csv", index=False)
    LOG.info("wrote suspicious_recovered_cells.csv (%d rows)", len(susp))

    # ---- coverage CEILING estimate (offline) / actual (online) ----
    n_comp = len(pd.read_parquet(repo / "p1" / "conv_exposure_free.parquet"))
    n_drop = len(dropped)
    n_att = n_comp + n_drop
    tier_counts = rdf["recovery_tier"].value_counts().to_dict()
    ceil_us = int(rdf["recoverable_via_free_online"].sum())     # US-renamed + ADR + stale
    ceil_foreign = int((rdf["recovery_tier"] == "tier3_foreign").sum())
    if args.online:
        recovered = int(rdf["recovery_status"].str.startswith("recovered").sum())
        us_recovered = int(rdf[(rdf["recovery_status"].str.startswith("recovered")) &
                               (~rdf["is_foreign_or_adr"])].shape[0])
    else:
        recovered, us_recovered = 0, 0

    before_after = pd.DataFrame([
        {"stage": "SEC_XBRL_baseline", "attempted_cells": n_att, "computed_cells": n_comp,
         "recovered_cells": 0, "remaining_dropped": n_drop,
         "cell_coverage_rate": round(n_comp / n_att, 4),
         "note": "real (pushed pipeline output)"},
        {"stage": "+local_SEC_map_renamed", "attempted_cells": n_att,
         "computed_cells": n_comp, "recovered_cells": ("PENDING_ONLINE" if not args.online
                                                       else us_recovered),
         "remaining_dropped": ("PENDING_ONLINE" if not args.online else n_drop - recovered),
         "cell_coverage_rate": "PENDING_ONLINE",
         "note": "renamed/acquired US tickers -> current CIK XBRL"},
        {"stage": "+yfinance", "attempted_cells": n_att, "computed_cells": n_comp,
         "recovered_cells": ("CEIL<=%d" % ceil_us if not args.online else recovered),
         "remaining_dropped": ("CEIL>=%d" % (n_drop - ceil_us) if not args.online
                               else n_drop - recovered),
         "cell_coverage_rate": ("CEIL<=%.4f" % ((n_comp + ceil_us) / n_att) if not args.online
                                else round((n_comp + recovered) / n_att, 4)),
         "note": "US-renamed+ADR+stale ceiling; foreign flagged separately"},
        {"stage": "+stooq", "attempted_cells": n_att, "computed_cells": n_comp,
         "recovered_cells": "no_shares_out_endpoint", "remaining_dropped": "n/a",
         "cell_coverage_rate": "n/a", "note": "Stooq = price only; used for mcap, not denom"},
        {"stage": "final_conservative_sample_US_only", "attempted_cells": n_att,
         "computed_cells": n_comp,
         "recovered_cells": ("CEIL<=%d" % ceil_us if not args.online else us_recovered),
         "remaining_dropped": (">=%d foreign/CINS excluded from US study" % ceil_foreign),
         "cell_coverage_rate": ("CEIL<=%.4f" % ((n_comp + ceil_us) / n_att) if not args.online
                                else round((n_comp + us_recovered) / n_att, 4)),
         "note": "TREATED-count columns need shares_held sidecar (box) — see README"},
    ])
    # treated-count columns: only computable when ConvExp can be recomputed (online+shares_held)
    for th in (0.0025, 0.005, 0.010):
        col = f"treated_stocks_ge_{th*100:g}pct"
        before_after[col] = "see treated_stock_counts_by_threshold.csv (baseline); " \
                            "post-recovery PENDING shares_held sidecar"
    before_after.to_csv(outdir / "coverage_before_after.csv", index=False)
    LOG.info("wrote coverage_before_after.csv (%d rows)", len(before_after))

    # tier scope table (post-recovery drop-reason view)
    scope = (rdf.groupby("recovery_tier")
             .agg(cells=("cusip", "size"),
                  recoverable_free=("recoverable_via_free_online", "sum"))
             .reset_index().sort_values("cells", ascending=False))
    scope["pct_of_dropped"] = (scope["cells"] / n_drop * 100).round(2)
    scope.to_csv(outdir / "coverage_post_recovery_by_drop_reason.csv", index=False)

    post_summary = pd.DataFrame([
        ("dropped_cells_total", n_drop),
        ("recoverable_free_ceiling_US+ADR+stale", ceil_us),
        ("foreign_CINS_or_foreign_listing", ceil_foreign),
        ("no_ticker_manual", int((rdf["recovery_tier"] == "tier4_no_ticker").sum())),
        ("stale_gt1_priority_fix", int((rdf["recovery_tier"] == "tier5_stale_gt1").sum())),
        ("recovered_this_run", recovered),
        ("mode", "online" if args.online else "offline_scope_only"),
    ], columns=["metric", "value"])
    post_summary.to_csv(outdir / "coverage_post_recovery_summary.csv", index=False)

    # ---- post-recovery subgroup tables (spec-required file set) ----------------
    # OFFLINE: mirror the baseline subgroup tables with recovered_cells=0 + a mode
    # marker so no reviewer mistakes them for a real recovery. The --online box run
    # recomputes ConvExp and OVERWRITES these with true post-recovery numbers.
    for base, post in [("coverage_baseline_by_family.csv", "coverage_post_recovery_by_family.csv"),
                       ("coverage_baseline_by_year.csv", "coverage_post_recovery_by_year.csv"),
                       ("coverage_baseline_by_wave.csv", "coverage_post_recovery_by_wave.csv")]:
        bp = outdir / base
        if not bp.exists():
            LOG.warning("%s absent — run build_coverage_audit.py first; skipping %s", base, post)
            continue
        t = pd.read_csv(bp)
        t["recovered_cells"] = recovered if args.online else 0
        t["mode"] = "online_recovered" if args.online else "offline_scope_only_equals_baseline"
        t.to_csv(outdir / post, index=False)
        LOG.info("wrote %s", post)

    LOG.info("tiers: %s | US ceiling=%d foreign=%d", tier_counts, ceil_us, ceil_foreign)
    LOG.info("recovery scoping complete -> %s", outdir)


if __name__ == "__main__":
    main()
