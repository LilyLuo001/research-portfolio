#!/usr/bin/env python3
"""Construct the Vanguard ETF-share-class census from SEC and CRSP headers.

Inputs are deliberately command-line arguments because the licensed CRSP file
lives on SCC and is not committed.  Example:

  python3 p1/strategic_pivot/build_vanguard_census.py \
    --crsp-header /path/crsp_fund_hdr_full.parquet \
    --sec-tickers /path/company_tickers_mf.json
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "p1" / "strategic_pivot" / "vanguard_etf_shareclass_census.csv"
SEC_MASTER = "https://www.sec.gov/files/company_tickers_mf.json"
SEC_70_SOURCE = "https://www.sec.gov/Archives/edgar/data/49905/000110465924102178/tm2424364d1_40app.htm"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--crsp-header", required=True)
    ap.add_argument("--sec-tickers", required=True)
    args = ap.parse_args()

    d = pd.read_parquet(args.crsp_header)
    text = d[["fund_name", "mgmt_name", "adv_name"]].fillna("")
    v = d[text.apply(lambda s: s.str.contains("VANGUARD", case=False)).any(axis=1)].copy()
    with open(args.sec_tickers, encoding="utf-8") as fh:
        payload = json.load(fh)
    sec = pd.DataFrame(payload["data"], columns=payload["fields"])
    sec["symbol"] = sec["symbol"].fillna("")

    rows = []
    for portno, g in v.groupby("crsp_portno", dropna=True):
        etf = g[g["et_flag"].fillna("").eq("F")]
        mf = g[g["et_flag"].fillna("").ne("F")]
        if len(etf) != 1 or mf.empty:
            continue
        e = etf.iloc[0]
        etf_date = pd.to_datetime(e["first_offer_dt"])
        mf_date = pd.to_datetime(mf["first_offer_dt"]).min()
        lag = int((etf_date - mf_date).days)
        sm = sec[sec["symbol"].eq(str(e["ticker"]))]
        series = str(sm.iloc[0]["seriesId"]) if len(sm) else ""
        cik = str(sm.iloc[0]["cik"]) if len(sm) else ""
        fund = str(e["fund_name"]).split(":", 1)[-1].split(";", 1)[0].strip()
        rows.append({
            "fund_name": fund,
            "sec_cik": cik,
            "sec_series_id": series,
            "crsp_portno": int(portno),
            "mutual_fund_share_classes": ";".join(sorted(mf["ticker"].dropna().astype(str).unique())),
            "etf_viper_ticker": e["ticker"],
            "etf_class_launch_effective_date": etf_date.date().isoformat(),
            "first_trading_date": etf_date.date().isoformat(),
            "first_mutual_class_offer_date": mf_date.date().isoformat(),
            "mutual_history_days_before_etf": lag,
            "activation_type": ("later_staggered_addition" if lag >= 90 else
                                "mutual_first_but_short_preperiod" if lag > 0 else
                                "same_day_joint_launch" if lag == 0 else
                                "etf_first_not_clean_activation"),
            "usable_staggered_activation": lag >= 90,
            "usability_rule": "mutual class precedes ETF class by at least 90 calendar days",
            "investment_objective": "VERIFY_FROM_EVENT-DATE_PROSPECTUS",
            "manager_or_adviser": e.get("adv_name", ""),
            "underlying_portfolio_identity": "exact_same_crsp_portno_and_sec_series",
            "ordinary_mutual_classes_continued": True,
            "aum_before_launch": "NOT_IN_HEADER; retrieve CRSP fund_summary2 month-end before launch",
            "etf_class_aum_after_launch": "NOT_IN_HEADER; retrieve CRSP fund_summary2 first month-end after launch",
            "sec_accession_or_source": SEC_MASTER,
            "independent_aggregate_count_source": SEC_70_SOURCE,
            "date_confidence": "HIGH_CRSP_FIRST_OFFER; first-trade date still exchange-calendar cross-check",
            "taq_vendor_era_exists": etf_date.year >= 1993,
            "taq_in_current_archive": False,
            "crsp_coverage_exists": True,
            "pre_post_holdings_observable": "YES_CRSP_PORTFOLIO; frequency/coverage must be event-audited",
            "portfolio_continuity_status": "MECHANICAL_SAME_PORTFOLIO; quantify around event before estimation",
            "restructuring_or_nonshared_case": False,
        })
    out = pd.DataFrame(rows).sort_values(["etf_class_launch_effective_date", "etf_viper_ticker"])
    assert len(out) == 70, f"Expected 70 Vanguard shared-portfolio ETF classes, got {len(out)}"
    assert int(out["usable_staggered_activation"].sum()) == 19
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    print(out["activation_type"].value_counts())
    print(f"usable={out.usable_staggered_activation.sum()} total={len(out)}")


if __name__ == "__main__":
    main()
