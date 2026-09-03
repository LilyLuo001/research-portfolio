#!/usr/bin/env python3
"""P1-T2 free-path ConvExp — coverage & missingness AUDIT (baseline, offline).

Reads ONLY real repo artifacts produced by p1/t2_free/build_nport_convexp.py and
recomputes fund-level + cell-level coverage, subgroup diagnostics, missingness
severity, and treated-stock counts. No network, no imputation — every number is
derived from a pushed file. This is the read-side auditor for the box's write-side
pipeline; it must never invent a denominator (that is recover_denominators.py's job,
and even that quarantines rather than trusts).

Inputs (all committed):
  p1/conv_exposure_free.parquet            computed cells (has conv_exp + denominators)
  p1/t2_free/NEED_HUMAN_stocks.csv         dropped cells (cusip,ticker,wave_id,reason)
  p1/t2_free/NEED_HUMAN_funds.csv          excluded funds (non-equity)
  p1/events_merged.csv                     fund universe (asset_class, family, AUM)
  p1/t2_wrds/waves.csv                     wave -> effective_date, is_anchor
  p1/t2_wrds/waves_members.csv             wave -> fund -> family (attribution)
  ops/briefs/gate2_human_review_manifest.json   box manifest (cross-check only)

Outputs -> p1/output/convexp_coverage_audit/ (see FILES).

CAVEAT on value-weighting: the pipeline aggregates shares across funds within a
wave and, for DROPPED cells, retains no shares_held/valUSD (only cusip/ticker/wave).
So value-weighted MISSINGNESS is not reconstructable from pushed artifacts; we report
cell-count coverage exactly, and a shares_held-based magnitude only for COMPUTED cells
(clearly labeled). To get true value weights, re-run the pipeline retaining valUSD on
drop, or re-parse the NPORT cache. This limitation is stated in the README + memo.

Usage:
  python p1/output/convexp_coverage_audit/build_coverage_audit.py
  python p1/output/convexp_coverage_audit/build_coverage_audit.py --repo /path/to/repo
"""
from __future__ import annotations
import argparse
import json
import logging
import pathlib
import re
import sys

import pandas as pd

LOG = logging.getLogger("coverage_audit")

# ConvExp treatment thresholds the kill-switch / event study care about.
THRESHOLDS = [0.0025, 0.005, 0.010]   # 0.25%, 0.5%, 1.0%


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #
def load_inputs(repo: pathlib.Path) -> dict:
    p1 = repo / "p1"
    paths = {
        "computed": p1 / "conv_exposure_free.parquet",
        "dropped": p1 / "t2_free" / "NEED_HUMAN_stocks.csv",
        "excluded_funds": p1 / "t2_free" / "NEED_HUMAN_funds.csv",
        "events": p1 / "events_merged.csv",
        "waves": p1 / "t2_wrds" / "waves.csv",
        "wave_members": p1 / "t2_wrds" / "waves_members.csv",
        "manifest": repo / "ops" / "briefs" / "gate2_human_review_manifest.json",
    }
    missing = [k for k, v in paths.items() if not v.exists()]
    if missing:
        LOG.error("MISSING inputs: %s", ", ".join(f"{k}({paths[k]})" for k in missing))
        LOG.error("Cannot audit without the real box outputs. Pull them first; not fabricating.")
        sys.exit(2)

    d = {}
    d["computed"] = pd.read_parquet(paths["computed"])
    d["dropped"] = pd.read_csv(paths["dropped"], dtype=str).fillna("")
    d["excluded_funds"] = pd.read_csv(paths["excluded_funds"], dtype=str).fillna("")
    d["events"] = pd.read_csv(paths["events"], dtype=str).fillna("")
    d["wave_members"] = pd.read_csv(paths["wave_members"], dtype=str).fillna("")
    # NOTE: p1/t2_wrds/waves.csv is committed CORRUPT (two concatenated schemas,
    # a 4-col header + a 7-col header in one file -> unparseable). We therefore
    # derive the canonical wave frame (wave_id, effective_date, is_anchor) from
    # the CLEAN waves_members.csv instead. Anchor = DFA wave W002 (2021-06-11).
    ANCHOR_DATE = "2021-06-11"
    wm = d["wave_members"]
    d["waves"] = (wm[["wave_id", "effective_date"]].drop_duplicates()
                  .assign(is_anchor=lambda x: (x["effective_date"] == ANCHOR_DATE)
                          .map({True: "1", False: "0"}))
                  .reset_index(drop=True))
    if paths["waves"].exists():
        LOG.warning("p1/t2_wrds/waves.csv is corrupt (double-schema); derived waves "
                    "from waves_members.csv instead. FLAGGED for a pipeline fix.")
    d["manifest"] = json.loads(paths["manifest"].read_text())
    LOG.info("loaded: computed=%d dropped=%d excluded_funds=%d events=%d waves=%d members=%d",
             len(d["computed"]), len(d["dropped"]), len(d["excluded_funds"]),
             len(d["events"]), len(d["waves"]), len(d["wave_members"]))
    return d


# --------------------------------------------------------------------------- #
# canonical drop-reason bucket (collapses the per-row conv_exp>1 strings)
# --------------------------------------------------------------------------- #
def drop_bucket(reason: str) -> str:
    r = (reason or "").strip()
    if r.startswith("conv_exp>1"):
        return "conv_exp>1"
    return r.split("(")[0].split(";")[0].strip() or "unknown"


# --------------------------------------------------------------------------- #
# severity classification of a dropped cell (offline, ticker/CUSIP heuristics)
# --------------------------------------------------------------------------- #
_FOREIGN_SUFFIX = re.compile(r"(EUR|GBP|CHF|SEK|NOK|DKK|JPY|CAD|AUD|HKD|CNY|SGD)$")
_ADR_SUFFIX = re.compile(r"Y$")           # ...Y ADR convention (ADRNY, ALIZY)


def severity_class(cusip: str, ticker: str, reason: str) -> str:
    """Coarse, auditable bucket for WHY a denominator is missing.

    foreign_cins_cusip  : CUSIP begins with a letter -> CINS (non-US issuer); CRSP
                          would not cover it either, so it leaves the US universe.
    foreign_listing_tkr : OpenFIGI returned a non-US listing symbol (FX suffix / digits
                          / overlong) -> no US CIK by construction.
    adr_like            : ...Y symbol, typically an ADR line.
    stale_denom_gt1     : denominator so stale/wrong that conv_exp>1 (quarantined).
    no_ticker           : CUSIP never mapped to any ticker.
    us_recoverable_cand : looks like a US-listed common symbol (likely delisted/
                          renamed/acquired, hence absent from CURRENT company_tickers)
                          -> the yfinance/Stooq fallback can plausibly recover it.
    """
    r = (reason or "")
    if r.startswith("conv_exp>1"):
        return "stale_denom_gt1"
    if not ticker:
        return "no_ticker"
    if cusip and cusip[0].isalpha():
        return "foreign_cins_cusip"
    t = ticker.upper()
    if re.search(r"\d", t) or len(t) > 5 or _FOREIGN_SUFFIX.search(t):
        return "foreign_listing_tkr"
    if _ADR_SUFFIX.search(t) and len(t) >= 4:
        return "adr_like"
    return "us_recoverable_cand"


# --------------------------------------------------------------------------- #
# wave -> attributes (year, is_anchor, family set, asset_class set)
# --------------------------------------------------------------------------- #
def wave_attributes(d: dict) -> pd.DataFrame:
    waves = d["waves"].copy()
    waves["year"] = waves["effective_date"].str[:4]
    waves["is_anchor"] = waves["is_anchor"].astype(str)
    # fund -> asset_class from events_merged (key on fund_name)
    ac = dict(zip(d["events"]["fund_name"], d["events"]["asset_class"]))
    m = d["wave_members"].copy()
    m["asset_class"] = m["fund_name"].map(ac).fillna("na")
    fam_by_wave = m.groupby("wave_id")["family"].agg(lambda s: sorted(set(s)))
    ac_by_wave = m.groupby("wave_id")["asset_class"].agg(lambda s: sorted(set(s)))
    waves = waves.set_index("wave_id")
    waves["families"] = fam_by_wave
    waves["asset_classes"] = ac_by_wave
    # single-attribute label where unambiguous, else 'mixed'
    waves["family_label"] = waves["families"].apply(
        lambda x: x[0] if isinstance(x, list) and len(x) == 1 else "MIXED")
    waves["asset_class_label"] = waves["asset_classes"].apply(
        lambda x: x[0] if isinstance(x, list) and len(x) == 1 else "MIXED")
    return waves.reset_index()


# --------------------------------------------------------------------------- #
# core coverage frame: one row per (wave) with computed / dropped counts
# --------------------------------------------------------------------------- #
def cell_coverage_by_wave(d: dict) -> pd.DataFrame:
    comp = d["computed"].groupby("wave_id").size().rename("computed_cells")
    drop = d["dropped"].groupby("wave_id").size().rename("dropped_cells")
    cov = pd.concat([comp, drop], axis=1).fillna(0).astype(int)
    cov["attempted_cells"] = cov["computed_cells"] + cov["dropped_cells"]
    cov["coverage_rate"] = cov["computed_cells"] / cov["attempted_cells"].where(cov["attempted_cells"] > 0)
    return cov.reset_index()


def _rollup(cov_wave: pd.DataFrame, wattr: pd.DataFrame, key: str) -> pd.DataFrame:
    """Aggregate wave-level coverage up to a wave attribute (year/family/asset/anchor)."""
    j = cov_wave.merge(wattr[["wave_id", key]], on="wave_id", how="left")
    g = j.groupby(key).agg(
        waves=("wave_id", "nunique"),
        attempted_cells=("attempted_cells", "sum"),
        computed_cells=("computed_cells", "sum"),
        dropped_cells=("dropped_cells", "sum"),
    ).reset_index()
    g["coverage_rate"] = g["computed_cells"] / g["attempted_cells"].where(g["attempted_cells"] > 0)
    return g.sort_values("attempted_cells", ascending=False)


# --------------------------------------------------------------------------- #
# treated-stock counts at thresholds (distinct stocks, pooled + anchor)
# --------------------------------------------------------------------------- #
def treated_counts(d: dict, wattr: pd.DataFrame) -> pd.DataFrame:
    comp = d["computed"].copy()
    comp["conv_exp"] = pd.to_numeric(comp["conv_exp"], errors="coerce")
    anchor_waves = set(wattr.loc[wattr["is_anchor"] == "1", "wave_id"])
    rows = []
    for label, sub in [("pooled", comp),
                       ("dfa_anchor_W002", comp[comp["wave_id"].isin(anchor_waves)]),
                       ("non_anchor", comp[~comp["wave_id"].isin(anchor_waves)])]:
        rec = {"scope": label, "computed_cells": len(sub),
               "distinct_stocks": sub["cusip"].nunique()}
        for th in THRESHOLDS:
            rec[f"cells_ge_{th*100:g}pct"] = int((sub["conv_exp"] >= th).sum())
            rec[f"stocks_ge_{th*100:g}pct"] = int(sub.loc[sub["conv_exp"] >= th, "cusip"].nunique())
        rows.append(rec)
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# fund-level coverage
# --------------------------------------------------------------------------- #
def fund_coverage(d: dict) -> pd.DataFrame:
    total = len(d["events"])
    excluded = len(d["excluded_funds"])
    resolved = total - excluded
    # equity funds that actually produced >=1 computed cell: waves with computed cells
    # map back to funds via wave_members (a resolved fund contributed if its wave has cells)
    comp_waves = set(d["computed"]["wave_id"])
    excluded_names = set(d["excluded_funds"]["fund_name"])
    resolved_members = d["wave_members"][~d["wave_members"]["fund_name"].isin(excluded_names)]
    funds_with_cells = resolved_members.loc[
        resolved_members["wave_id"].isin(comp_waves), "fund_name"].nunique()
    rows = [
        ("total_conversion_funds", total),
        ("equity_funds_resolved", resolved),
        ("non_equity_funds_excluded", excluded),
        ("resolved_funds_in_a_wave_with_>=1_computed_cell", funds_with_cells),
        ("resolved_funds_in_waves_with_zero_computed_cells", resolved - funds_with_cells),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


# --------------------------------------------------------------------------- #
# baseline summary + drop-reason + severity
# --------------------------------------------------------------------------- #
def baseline_summary(d: dict, cov_wave: pd.DataFrame) -> pd.DataFrame:
    comp = d["computed"]
    n_comp = len(comp)
    n_drop = len(d["dropped"])
    n_att = n_comp + n_drop
    comp_ce = pd.to_numeric(comp["conv_exp"], errors="coerce")
    sh = pd.to_numeric(comp["shares_held"], errors="coerce")
    rows = [
        ("attempted_cells", n_att),
        ("computed_cells", n_comp),
        ("dropped_cells", n_drop),
        ("cell_coverage_rate", round(n_comp / n_att, 4)),
        ("cell_drop_rate", round(n_drop / n_att, 4)),
        ("distinct_stocks_computed", comp["cusip"].nunique()),
        ("conv_exp_max", round(float(comp_ce.max()), 6)),
        ("conv_exp_median", round(float(comp_ce.median()), 6)),
        ("computed_shares_held_total", float(sh.sum())),
        ("VALUE_WEIGHTED_COVERAGE", "NOT_AVAILABLE_dropped_cells_retain_no_shares_or_value"),
    ]
    return pd.DataFrame(rows, columns=["metric", "value"])


def drop_reason_table(d: dict) -> pd.DataFrame:
    dr = d["dropped"].copy()
    dr["bucket"] = dr["reason"].map(drop_bucket)
    n_att = len(d["computed"]) + len(dr)
    g = dr.groupby("bucket").size().rename("count").reset_index()
    g["pct_of_attempted"] = (g["count"] / n_att * 100).round(2)
    g["pct_of_dropped"] = (g["count"] / len(dr) * 100).round(2)
    return g.sort_values("count", ascending=False)


def severity_table(d: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    dr = d["dropped"].copy()
    dr["severity"] = [severity_class(c, t, r) for c, t, r
                      in zip(dr["cusip"], dr["ticker"], dr["reason"])]
    n_drop = len(dr)
    g = dr.groupby("severity").size().rename("count").reset_index()
    g["pct_of_dropped"] = (g["count"] / n_drop * 100).round(2)
    g = g.sort_values("count", ascending=False)
    return g, dr


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> None:
    ap = argparse.ArgumentParser(description="P1-T2 free ConvExp coverage audit (baseline)")
    ap.add_argument("--repo", default=None, help="repo root (default: infer from this file)")
    ap.add_argument("--outdir", default=None, help="output dir (default: alongside this script)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")

    here = pathlib.Path(__file__).resolve()
    repo = pathlib.Path(args.repo).resolve() if args.repo else here.parents[3]
    outdir = pathlib.Path(args.outdir).resolve() if args.outdir else here.parent
    outdir.mkdir(parents=True, exist_ok=True)
    LOG.info("repo=%s outdir=%s", repo, outdir)

    d = load_inputs(repo)
    wattr = wave_attributes(d)
    cov_wave = cell_coverage_by_wave(d)

    def dump(df: pd.DataFrame, name: str) -> None:
        p = outdir / name
        df.to_csv(p, index=False)
        LOG.info("wrote %s (%d rows)", name, len(df))

    # ---- baseline ----
    dump(baseline_summary(d, cov_wave), "coverage_baseline_summary.csv")
    dump(fund_coverage(d), "coverage_baseline_fund_level.csv")
    dump(drop_reason_table(d), "coverage_baseline_by_drop_reason.csv")

    # by-wave (attach year/anchor/labels)
    byw = cov_wave.merge(
        wattr[["wave_id", "effective_date", "year", "is_anchor",
               "family_label", "asset_class_label"]], on="wave_id", how="left"
    ).sort_values("effective_date")
    dump(byw, "coverage_baseline_by_wave.csv")

    dump(_rollup(cov_wave, wattr, "year"), "coverage_baseline_by_year.csv")
    dump(_rollup(cov_wave, wattr, "family_label"), "coverage_baseline_by_family.csv")
    dump(_rollup(cov_wave, wattr, "asset_class_label"), "coverage_baseline_by_asset_class.csv")

    # DFA vs non-DFA
    anchor = _rollup(cov_wave, wattr, "is_anchor").rename(columns={"is_anchor": "is_dfa_anchor"})
    anchor["is_dfa_anchor"] = anchor["is_dfa_anchor"].map({"1": "DFA_anchor_W002", "0": "non_anchor"})
    dump(anchor, "coverage_baseline_dfa_vs_nondfa.csv")

    # top funds/waves by attempted cells (waves are the cell-bearing unit)
    top = byw.sort_values("attempted_cells", ascending=False).head(20)[
        ["wave_id", "effective_date", "family_label", "asset_class_label",
         "attempted_cells", "computed_cells", "dropped_cells", "coverage_rate"]]
    dump(top, "coverage_baseline_top_funds.csv")

    # ---- severity ----
    sev, dr_sev = severity_table(d)
    dump(sev, "coverage_baseline_severity.csv")
    # severity x drop_reason cross-tab for the memo
    dr_sev["bucket"] = dr_sev["reason"].map(drop_bucket)
    xt = pd.crosstab(dr_sev["severity"], dr_sev["bucket"]).reset_index()
    dump(xt, "coverage_baseline_severity_by_reason.csv")

    # remaining dropped cells (full list w/ severity) — the residual after baseline
    rem = dr_sev[["cusip", "ticker", "wave_id", "reason", "bucket", "severity"]].copy()
    dump(rem, "remaining_dropped_cells.csv")

    # ---- treated-stock counts ----
    dump(treated_counts(d, wattr), "treated_stock_counts_by_threshold.csv")

    # ---- cross-check vs box manifest (guards against silent drift) ----
    mo = d["manifest"]["universe_overview"]
    checks = {
        "funds_resolved": (mo["funds_with_holdings_resolved"], len(d["events"]) - len(d["excluded_funds"])),
        "conv_exp_rows": (mo["conv_exp_rows"], len(d["computed"])),
        "stock_cells_need_human": (mo["stock_cells_need_human"], len(d["dropped"])),
        "cells_ge_0_5pct": (mo["cells_ge_0_5pct"],
                            int((pd.to_numeric(d["computed"]["conv_exp"]) >= 0.005).sum())),
        "cells_ge_1pct": (mo["cells_ge_1pct"],
                          int((pd.to_numeric(d["computed"]["conv_exp"]) >= 0.010).sum())),
    }
    ck = pd.DataFrame([(k, v[0], v[1], "OK" if v[0] == v[1] else "MISMATCH")
                       for k, v in checks.items()],
                      columns=["metric", "manifest", "recomputed", "status"])
    dump(ck, "coverage_manifest_crosscheck.csv")
    if (ck["status"] == "MISMATCH").any():
        LOG.warning("MANIFEST CROSS-CHECK MISMATCH:\n%s", ck.to_string(index=False))
    else:
        LOG.info("manifest cross-check: all OK")

    LOG.info("baseline audit complete -> %s", outdir)


if __name__ == "__main__":
    main()
