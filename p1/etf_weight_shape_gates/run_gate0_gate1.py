#!/usr/bin/env python3
"""Build Gate 0 and holdings-only Gate 1 artifacts on the SCC archive.

The script intentionally constructs only
PseudoCapImpliedWeight_ObservedHoldings because the archive contains no
verified benchmark-weight history. It never calls that diagnostic object a
benchmark wedge and never assigns a final Gate 1 PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import re
from pathlib import Path

import numpy as np
import pandas as pd

from gate_core import (
    PRIMARY_MAX_STALENESS_DAYS,
    align_portfolio_aum,
    classify_weight_style,
    inverse_hhi,
)
from pilot_contract import (
    PilotContractError,
    authorize_local_pilot,
    authorize_manifest,
    candidate_implementation_conformance,
    load_json_document,
)


CODE_ROOT = Path(__file__).resolve().parent
CONFIG_PATH = CODE_ROOT / "gate01_config.json"
DATA_CONTRACT_PATH = CODE_ROOT / "data_contract.json"
ARCHIVE = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902")
WRDS = ARCHIVE / "p1_refraction_wrds_shared"
RAW = WRDS / "raw"
META = WRDS / "meta"
MANIFEST = ARCHIVE / "_migration_meta" / "FINAL_SCC_MANIFEST.tsv"
YEARS = range(2019, 2026)
MAX_STALENESS_AUDIT_DAYS = 180


def require_bound_path(value: str | Path, expected: Path, *, label: str) -> Path:
    """Reject alternate code/config/contract/manifest paths without reading them."""

    supplied = Path(os.path.abspath(os.fspath(value)))
    frozen = Path(os.path.abspath(os.fspath(expected)))
    if supplied != frozen:
        raise PilotContractError(
            f"{label.upper()}_PATH_MISMATCH",
            f"{label} must be the frozen path {frozen}; received {supplied}",
        )
    return frozen


def load_scientific_runtime() -> None:
    """Import full-run-only packages after the data-contract preflight."""
    global LinearRegression, OneHotEncoder, matplotlib, plt, pyarrow, pq
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import pyarrow
    import pyarrow.parquet as pq
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import OneHotEncoder


def parquet_rows(paths: list[Path]) -> int:
    return int(sum(pq.ParquetFile(p).metadata.num_rows for p in paths if p.exists()))


def qends() -> list[pd.Timestamp]:
    return list(pd.date_range("2019-03-31", "2025-12-31", freq="QE"))


def active_name_map(frame: pd.DataFrame, names: pd.DataFrame, date_col: str) -> pd.DataFrame:
    """Effective-date map CIZ name/security attributes without future records."""
    out = frame.copy()
    out[date_col] = pd.to_datetime(out[date_col])
    out["is_us_common"] = False
    out["company_name"] = ""
    out["sic4"] = pd.NA
    by_name = {int(k): g for k, g in names.groupby("permno", sort=False)}
    for permno, idx in out.groupby("permno", sort=False).groups.items():
        g = by_name.get(int(permno))
        if g is None:
            continue
        dates = out.loc[idx, date_col]
        for row in g.itertuples(index=False):
            mask = dates.between(row.namedt, row.nameenddt)
            use = dates.index[mask]
            if not len(use):
                continue
            common = (
                row.sharetype == "NS"
                and row.securitytype == "EQTY"
                and row.securitysubtype == "COM"
                and row.usincflg == "Y"
            )
            out.loc[use, "is_us_common"] = common
            out.loc[use, "company_name"] = row.issuernm or ""
            out.loc[use, "sic4"] = row.siccd
    return out


def load_names() -> pd.DataFrame:
    path = RAW / "rescue" / "newcrsp_crsp_stocknames_v2_full.parquet"
    n = pd.read_parquet(path)
    n["namedt"] = pd.to_datetime(n.namedt, errors="coerce")
    n["nameenddt"] = pd.to_datetime(n.nameenddt, errors="coerce").fillna(pd.Timestamp("2099-12-31"))
    for c in ["sharetype", "securitytype", "securitysubtype", "usincflg"]:
        n[c] = n[c].fillna("").astype(str).str.upper()
    return n


def load_daily() -> tuple[pd.DataFrame, list[dict]]:
    frames, provenance = [], []
    for year in range(2018, 2025):
        p = RAW / "rescue" / f"crsp_dsf_allcols_{year}.parquet"
        d = pd.read_parquet(
            p,
            columns=["permno", "date", "prc", "vol", "ret", "retx", "shrout", "hsiccd"],
        )
        d = d.rename(
            columns={
                "date": "trading_date",
                "prc": "price",
                "vol": "volume",
                "hsiccd": "daily_sic",
            }
        )
        d["source_family"] = "legacy_crsp_dsf_allcols"
        provenance.append(
            {
                "source_file": str(p),
                "source_family": "legacy_crsp_dsf_allcols",
                "selection_role": "primary_2018_2024_daily",
                "rows": len(d),
                "overlap_disposition": "raw/crsp_dsf_YEAR and CIZ-2024 are insurance overlaps not stacked",
            }
        )
        frames.append(d)
    p = RAW / "rescue" / "newcrsp_crsp_dsf_v2_2025.parquet"
    d = pd.read_parquet(
        p,
        columns=["permno", "dlycaldt", "dlyprc", "dlyvol", "dlyret", "dlyretx", "shrout", "siccd"],
    )
    d = d.rename(
        columns={
            "dlycaldt": "trading_date",
            "dlyprc": "price",
            "dlyvol": "volume",
            "dlyret": "ret",
            "dlyretx": "retx",
            "siccd": "daily_sic",
        }
    )
    d["source_family"] = "crsp_ciz_dsf_v2"
    provenance.append(
        {
            "source_file": str(p),
            "source_family": "crsp_ciz_dsf_v2",
            "selection_role": "primary_2025_daily",
            "rows": len(d),
            "overlap_disposition": "crsp_a_stock file is byte-size insurance duplicate and not stacked",
        }
    )
    frames.append(d)
    out = pd.concat(frames, ignore_index=True)
    out["trading_date"] = pd.to_datetime(out.trading_date, errors="coerce")
    for c in ["price", "volume", "ret", "retx", "shrout"]:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out["price"] = out.price.abs()
    out["market_cap"] = out.price * out.shrout * 1000.0
    out["dollar_volume"] = out.price * out.volume.abs()
    out = out.dropna(subset=["permno", "trading_date"]).sort_values(["permno", "trading_date"])
    out = out.drop_duplicates(["permno", "trading_date"], keep="last")
    return out, provenance


def stock_quarters(
    daily: pd.DataFrame, names: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    all_rows = []
    for q in qends():
        recent = daily.loc[
            daily.trading_date.between(q - pd.Timedelta(days=125), q)
        ].copy()
        last = recent.sort_values("trading_date").groupby("permno", as_index=False).tail(1)
        last["market_cap_date_gap_days"] = (q - last.trading_date).dt.days
        last = last.loc[last.market_cap_date_gap_days.between(0, 7)].copy()
        last = active_name_map(last, names, "trading_date")
        last = last.loc[last.is_us_common & last.market_cap.gt(0)].copy()
        last["common_stock_selection_rule"] = (
            "CIZ_EFFECTIVE_DATE_SHARETYPE_NS_SECURITYTYPE_EQTY_"
            "SECURITYSUBTYPE_COM_USINCFLG_Y"
        )
        ids = set(last.permno.astype(int))
        r = recent.loc[recent.permno.isin(ids)].sort_values(["permno", "trading_date"])
        r = r.groupby("permno", as_index=False).tail(60)
        liq = r.groupby("permno").agg(adv=("dollar_volume", "mean")).reset_index()
        a = r.assign(
            amihud_obs=r.ret.abs().div(r.dollar_volume.where(r.dollar_volume.gt(0)))
        )
        av = a.groupby("permno").amihud_obs.mean().rename("amihud").reset_index()
        liq = liq.merge(av, on="permno", how="left")
        last = last.merge(liq, on="permno", how="left")
        last["quarter"] = q
        last["market_cap_rank"] = last.market_cap.rank(
            method="first", ascending=False
        )
        all_rows.append(
            last[
                [
                    "permno",
                    "quarter",
                    "trading_date",
                    "market_cap",
                    "market_cap_rank",
                    "market_cap_date_gap_days",
                    "adv",
                    "amihud",
                    "company_name",
                    "sic4",
                    "daily_sic",
                    "common_stock_selection_rule",
                ]
            ]
        )
    all_stocks = pd.concat(all_rows, ignore_index=True)
    top = all_stocks.loc[all_stocks.market_cap_rank.le(1000)].copy()
    return all_stocks, top


def load_fund_aum() -> tuple[
    pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict]
]:
    hdr_path = RAW / "crsp_fund_hdr_full.parquet"
    hdr = pd.read_parquet(hdr_path)
    h = hdr[
        [
            "crsp_fundno",
            "crsp_portno",
            "et_flag",
            "fund_name",
            "ticker",
            "mgmt_name",
            "adv_name",
            "ncusip",
        ]
    ].copy()
    h = h.sort_values("crsp_fundno").drop_duplicates("crsp_fundno", keep="last")
    frames, provenance = [], []
    for year in range(2018, 2026):
        p = RAW / f"crsp_fund_summary2_{year}.parquet"
        d = pd.read_parquet(p)
        d["caldt"] = pd.to_datetime(d.caldt, errors="coerce")
        d["tna_latest_dt"] = pd.to_datetime(d.tna_latest_dt, errors="coerce")
        d = d.merge(h, on="crsp_fundno", how="left", suffixes=("", "_hdr"))
        for c in [
            "crsp_portno",
            "fund_name",
            "ticker",
            "mgmt_name",
            "adv_name",
            "ncusip",
        ]:
            hc = f"{c}_hdr"
            if hc in d:
                d[c] = d[c].combine_first(d[hc])
        frames.append(d)
        provenance.append(
            {
                "source_file": str(p),
                "source_family": "crsp_fund_summary2",
                "selection_role": (
                    "ETF-class AUM plus all-share-class portfolio AUM and metadata"
                ),
                "rows": len(d),
                "overlap_disposition": "annual files are complementary calendar partitions",
            }
        )
    s_all = pd.concat(frames, ignore_index=True)
    s_all = s_all.loc[
        s_all.crsp_portno.notna() & s_all.tna_latest.notna()
    ].copy()
    s_all["aum_date"] = s_all.tna_latest_dt.fillna(s_all.caldt)
    portfolio_aum_timeline = (
        s_all.sort_values("caldt")
        .drop_duplicates(["crsp_fundno", "aum_date"], keep="last")
        [["crsp_portno", "crsp_fundno", "aum_date", "tna_latest"]]
        .rename(columns={"tna_latest": "aum_million"})
    )
    portfolio_aum_timeline["crsp_portno"] = (
        portfolio_aum_timeline.crsp_portno.astype(int)
    )
    # Do not backfill a missing historical flag from the current fund header:
    # that would classify pre-conversion observations using future ETF status.
    s = s_all.loc[s_all.et_flag.eq("F")].copy()
    etf_aum_timeline = (
        s.sort_values("caldt")
        .drop_duplicates(["crsp_fundno", "aum_date"], keep="last")
        [["crsp_portno", "crsp_fundno", "aum_date", "tna_latest"]]
        .rename(columns={"tna_latest": "aum_million"})
    )
    etf_aum_timeline["crsp_portno"] = etf_aum_timeline.crsp_portno.astype(int)
    rows = []
    for q in qends():
        x = s.loc[
            s.caldt.le(q)
            & s.caldt.ge(q - pd.Timedelta(days=PRIMARY_MAX_STALENESS_DAYS))
        ].copy()
        x = x.sort_values("caldt").groupby("crsp_fundno", as_index=False).tail(1)
        x["aum_date_gap_days"] = (
            q - x.tna_latest_dt.fillna(x.caldt)
        ).dt.days
        for port, g in x.groupby("crsp_portno"):
            rows.append(
                {
                    "crsp_portno": int(port),
                    "quarter": q,
                    "aum_million": float(g.tna_latest.fillna(0).sum()),
                    "aum_date": g.aum_date.min(),
                    "aum_date_gap_days": int(g.aum_date_gap_days.max()),
                    "fund_name": " | ".join(
                        sorted(g.fund_name.dropna().astype(str).unique())[:3]
                    ),
                    "etf_tickers": ";".join(
                        sorted(g.ticker.dropna().astype(str).unique())
                    ),
                    "fund_cusips": ";".join(
                        sorted(g.ncusip.dropna().astype(str).unique())
                    ),
                    "family": (
                        g.mgmt_name.dropna().astype(str).iloc[0]
                        if g.mgmt_name.notna().any()
                        else g.adv_name.dropna().astype(str).iloc[0]
                        if g.adv_name.notna().any()
                        else "UNKNOWN"
                    ),
                    "lipper_asset_cd": ";".join(
                        sorted(g.lipper_asset_cd.dropna().astype(str).unique())
                    ),
                    "lipper_class": ";".join(
                        sorted(g.lipper_class.dropna().astype(str).unique())
                    ),
                    "per_com": (
                        float(g.per_com.dropna().median())
                        if g.per_com.notna().any()
                        else math.nan
                    ),
                }
            )
    return (
        pd.DataFrame(rows),
        etf_aum_timeline,
        portfolio_aum_timeline,
        provenance,
    )


def prior_market_cap(keys: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    left = keys[["permno", "report_dt"]].drop_duplicates().copy()
    left["permno"] = left.permno.astype(int)
    left = left.sort_values(["report_dt", "permno"])
    right = daily[["permno", "trading_date", "market_cap"]].dropna().copy()
    right["permno"] = right.permno.astype(int)
    right = right.sort_values(["trading_date", "permno"])
    return pd.merge_asof(
        left,
        right,
        left_on="report_dt",
        right_on="trading_date",
        by="permno",
        direction="backward",
        tolerance=pd.Timedelta(days=7),
    )


def ols_style(group: pd.DataFrame) -> tuple[float, float, int]:
    g = group.loc[
        group.equity_sleeve_weight.gt(0) & group.market_cap_at_report.gt(0)
    ].copy()
    if len(g) < 30:
        return math.nan, math.nan, len(g)
    x = np.log(g.market_cap_at_report.to_numpy())
    y = np.log(g.equity_sleeve_weight.to_numpy())
    X = np.column_stack([np.ones(len(x)), x])
    coef = np.linalg.lstsq(X, y, rcond=None)[0]
    fit = X @ coef
    tss = np.square(y - y.mean()).sum()
    r2 = 1 - np.square(y - fit).sum() / tss if tss > 0 else math.nan
    return float(coef[1]), float(r2), len(g)


def load_holdings_and_build(
    aum_q: pd.DataFrame,
    etf_aum_timeline: pd.DataFrame,
    portfolio_aum_timeline: pd.DataFrame,
    daily: pd.DataFrame,
    names: pd.DataFrame,
    stocks_top: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, list[dict]]:
    universe_rows = []
    exclusion_rows = []
    style_rows = []
    contrib_frames = []
    mapping_rows = []
    provenance = []
    structure_pat = re.compile(
        r"(?:2x|3x|ultra|inverse|bear|short |buffer|defined outcome|covered call|buywrite|option income)",
        re.I,
    )
    structure_security_pat = re.compile(
        r"(?:option|\bcall\b|\bput\b|swap|future|futures|collar)", re.I
    )
    for year in YEARS:
        # Q1 can legitimately use a prior-December report. Scan the current
        # and immediately preceding partitions; the latest-prior rule below
        # prevents any overlapping snapshots from being stacked.
        paths = []
        for source_year in [year - 1, year]:
            paths.extend(
                sorted(
                    (RAW / "rescue_remaining").glob(
                        f"crsp_holdings_etf_{source_year}_b*/part_*.parquet"
                    )
                )
            )
        provenance.append(
            {
                "source_file": (
                    f"{RAW}/rescue_remaining/crsp_holdings_etf_"
                    f"{{{year - 1},{year}}}_b*/part_*.parquet"
                ),
                "source_family": "crsp_holdings_etf_batches",
                "selection_role": f"periodic ETF holdings {year}",
                "rows": parquet_rows(paths),
                "overlap_disposition": "year/batch parts complementary; co_info and maximal insurance excluded",
            }
        )
        # Deliberately over-include candidate portfolios.  The frozen $100m
        # screen is applied only after every share class is aligned to the
        # selected holdings report date below.
        candidate_window = etf_aum_timeline.loc[
            etf_aum_timeline.aum_date.between(
                pd.Timestamp(year - 1, 1, 1),
                pd.Timestamp(year, 12, 31),
            )
        ]
        candidate_peak = (
            candidate_window.groupby(["crsp_portno", "crsp_fundno"])
            .aum_million.max()
            .groupby("crsp_portno")
            .sum()
        )
        candidates = set(candidate_peak.loc[candidate_peak.ge(100)].index)
        parts = []
        for p in paths:
            d = pd.read_parquet(
                p,
                columns=[
                    "crsp_portno",
                    "report_dt",
                    "eff_dt",
                    "percent_tna",
                    "nbr_shares",
                    "market_val",
                    "security_name",
                    "cusip",
                    "permno",
                    "ticker",
                ],
            )
            d = d.loc[d.crsp_portno.isin(candidates)]
            if len(d):
                parts.append(d)
        holdings = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
        if len(holdings):
            holdings["report_dt"] = pd.to_datetime(
                holdings.report_dt, errors="coerce"
            )
            holdings["permno"] = pd.to_numeric(holdings.permno, errors="coerce")
            holdings["market_val"] = pd.to_numeric(
                holdings.market_val, errors="coerce"
            )
            holdings["percent_tna"] = pd.to_numeric(
                holdings.percent_tna, errors="coerce"
            )
        for q in [x for x in qends() if x.year == year]:
            aq_all = aum_q.loc[aum_q.quarter.eq(q)].copy()
            aq = aq_all
            if holdings.empty:
                chosen = holdings
            else:
                h = holdings.loc[
                    holdings.report_dt.le(q)
                    & holdings.report_dt.ge(
                        q - pd.Timedelta(days=MAX_STALENESS_AUDIT_DAYS)
                    )
                ]
                latest = (
                    h.groupby("crsp_portno")
                    .report_dt.max()
                    .rename("chosen_report_dt")
                    .reset_index()
                )
                chosen = h.merge(latest, on="crsp_portno").loc[
                    lambda z: z.report_dt.eq(z.chosen_report_dt)
                ].copy()
            present = set(chosen.crsp_portno.unique()) if len(chosen) else set()
            for r in aq.loc[~aq.crsp_portno.isin(present)].itertuples():
                reason = (
                    "NO_HOLDINGS_WITHIN_180_DAY_SENSITIVITY_WINDOW"
                    if r.aum_million >= 100
                    else "AUM_BELOW_100_MILLION_NO_HOLDINGS_WITHIN_180_DAYS"
                )
                exclusion_rows.append(
                    {
                        "quarter": q,
                        "crsp_portno": r.crsp_portno,
                        "etf_tickers": r.etf_tickers,
                        "fund_name": r.fund_name,
                        "exclusion_reason": reason,
                        "evidence": (
                            f"Quarter-aligned CRSP ETF-class TNA={r.aum_million:.3f} million; "
                            "no eligible point-in-time report available for report-date AUM alignment"
                        ),
                    }
                )
            if chosen.empty:
                continue
            chosen["mapping_status"] = np.where(
                chosen.permno.notna(), "PERMNO_PRESENT", "PERMNO_MISSING"
            )
            # Mapping coverage must use the full chosen report.  Computing the
            # denominator after dropping missing PERMNOs would mechanically
            # report 100% coverage and silently omit all-unmapped portfolios.
            chosen["positive_position_value"] = chosen.market_val.clip(lower=0)
            chosen["mapped_positive_position_value"] = chosen[
                "positive_position_value"
            ].where(chosen.permno.notna(), 0.0)
            chosen["mapped_percent_tna"] = chosen.percent_tna.where(
                chosen.permno.notna(), 0.0
            )
            # A product-name hit is only a review trigger.  Exclusion requires
            # independent portfolio evidence, so no ETF is excluded solely by
            # an unverified marketing/name string.
            chosen["structure_security_flag"] = chosen.security_name.fillna("").str.contains(
                structure_security_pat, regex=True
            )
            coverage = (
                chosen.groupby("crsp_portno")
                .agg(
                    total_position_value=("positive_position_value", "sum"),
                    mapped_position_value=(
                        "mapped_positive_position_value",
                        "sum",
                    ),
                    reported_percent_tna_sum=("percent_tna", "sum"),
                    mapped_percent_tna_sum=("mapped_percent_tna", "sum"),
                    percent_tna_observations=("percent_tna", "count"),
                    n_positions_raw=("crsp_portno", "size"),
                    report_dt=("report_dt", "max"),
                    structure_security_position_count=(
                        "structure_security_flag",
                        "sum",
                    ),
                )
                .reset_index()
                .set_index("crsp_portno")
            )
            missing = chosen.loc[chosen.permno.isna()].copy()
            if len(missing):
                top_missing = missing.nlargest(min(50, len(missing)), "market_val")
                for r in top_missing.itertuples():
                    mapping_rows.append(
                        {
                            "quarter": q,
                            "crsp_portno": int(r.crsp_portno),
                            "etf_tickers": "",
                            "mapping_status": "TOP_PERMNO_MISSING_BY_VALUE",
                            "position_count": 1,
                            "position_value": r.market_val,
                            "position_value_basis": "RAW_POOLED_PORTFOLIO_HOLDINGS",
                            "mapped_value_share": math.nan,
                            "us_common_value_share": math.nan,
                            "duplicate_permno_positions": math.nan,
                            "security_name": r.security_name,
                            "cusip": r.cusip,
                        }
                    )
            chosen_mapped = active_name_map(
                chosen.loc[chosen.permno.notna()].assign(
                    permno=lambda z: z.permno.astype(int)
                ),
                names,
                "report_dt",
            )
            if chosen_mapped.empty:
                chosen_mapped["market_cap_at_report"] = pd.Series(dtype=float)
            else:
                common_keys = chosen_mapped.loc[chosen_mapped.is_us_common]
                if common_keys.empty:
                    chosen_mapped["market_cap_at_report"] = np.nan
                else:
                    key = prior_market_cap(common_keys, daily)
                    chosen_mapped = chosen_mapped.merge(
                        key.rename(columns={"market_cap": "market_cap_at_report"}),
                        on=["permno", "report_dt"],
                        how="left",
                    )
            for port in sorted(present):
                g = chosen_mapped.loc[chosen_mapped.crsp_portno.eq(port)].copy()
                ar = aq.loc[aq.crsp_portno.eq(port)]
                if ar.empty:
                    continue
                a = ar.iloc[0]
                cov = coverage.loc[port]
                total_value = float(cov.total_position_value)
                common_value = float(
                    g.loc[g.is_us_common, "market_val"].clip(lower=0).sum()
                )
                mapped_value = float(cov.mapped_position_value)
                total_percent_tna = (
                    float(cov.reported_percent_tna_sum)
                    if int(cov.percent_tna_observations) > 0
                    else math.nan
                )
                mapped_percent_tna = (
                    float(cov.mapped_percent_tna_sum)
                    if int(cov.percent_tna_observations) > 0
                    else math.nan
                )
                common_percent_tna = (
                    float(g.loc[g.is_us_common, "percent_tna"].sum())
                    if g.loc[g.is_us_common, "percent_tna"].notna().any()
                    else math.nan
                )
                # CRSP's position-level percent_tna is the contemporaneous
                # PositionValue/FundNetAssets ratio at report_dt.  It is the
                # actual-weight field; quarterly fund_summary2 AUM remains the
                # frozen closest-prior screen and dollar-scaling object.
                eq_share = common_percent_tna / 100.0
                report = cov.report_dt
                staleness = int((q - report).days)
                aligned_etf = align_portfolio_aum(
                    etf_aum_timeline.loc[
                        etf_aum_timeline.crsp_portno.eq(int(port))
                    ],
                    report,
                )
                aligned_portfolio = align_portfolio_aum(
                    portfolio_aum_timeline.loc[
                        portfolio_aum_timeline.crsp_portno.eq(int(port))
                    ],
                    report,
                )
                if aligned_etf.empty:
                    aligned_aum_million = math.nan
                    aligned_aum_date = pd.NaT
                    aligned_aum_gap_days = math.nan
                    aligned_aum_share_class_count = 0
                else:
                    aligned_row = aligned_etf.iloc[0]
                    aligned_aum_million = float(aligned_row.aum_million)
                    aligned_aum_date = aligned_row.aum_date
                    aligned_aum_gap_days = int(aligned_row.aum_date_gap_days)
                    aligned_aum_share_class_count = int(
                        aligned_row.aum_share_class_count
                    )
                if aligned_portfolio.empty:
                    portfolio_aum_million = math.nan
                    portfolio_aum_date = pd.NaT
                    portfolio_aum_date_gap_days = math.nan
                    portfolio_aum_share_class_count = 0
                else:
                    portfolio_row = aligned_portfolio.iloc[0]
                    portfolio_aum_million = float(portfolio_row.aum_million)
                    portfolio_aum_date = portfolio_row.aum_date
                    portfolio_aum_date_gap_days = int(
                        portfolio_row.aum_date_gap_days
                    )
                    portfolio_aum_share_class_count = int(
                        portfolio_row.aum_share_class_count
                    )
                structure_flag = bool(structure_pat.search(a.fund_name or ""))
                structure_position_flag = bool(
                    cov.structure_security_position_count > 0
                )
                reasons = []
                if staleness > PRIMARY_MAX_STALENESS_DAYS:
                    reasons.append("HOLDINGS_STALENESS_EXCEEDS_120_DAYS")
                if not np.isfinite(total_percent_tna):
                    reasons.append("NO_USABLE_HOLDINGS_PERCENT_TNA_FOR_ACTUAL_WEIGHT")
                if not np.isfinite(eq_share) or eq_share < 0.80:
                    reasons.append("US_COMMON_EQUITY_SHARE_BELOW_80PCT")
                if not np.isfinite(aligned_aum_million):
                    reasons.append("NO_ETF_CLASS_AUM_ON_OR_BEFORE_HOLDINGS_REPORT_WITHIN_120_DAYS")
                elif aligned_aum_million < 100:
                    reasons.append("ETF_CLASS_AUM_BELOW_100_MILLION_AT_HOLDINGS_REPORT")
                if not np.isfinite(portfolio_aum_million):
                    reasons.append(
                        "NO_ALL_SHARE_CLASS_PORTFOLIO_AUM_ON_OR_BEFORE_HOLDINGS_REPORT_WITHIN_120_DAYS"
                    )
                elif portfolio_aum_million <= 0:
                    reasons.append("NONPOSITIVE_ALL_SHARE_CLASS_PORTFOLIO_AUM")
                elif (
                    np.isfinite(aligned_aum_million)
                    and portfolio_aum_million + 1e-9 < aligned_aum_million
                ):
                    reasons.append(
                        "ALL_SHARE_CLASS_PORTFOLIO_AUM_BELOW_ETF_CLASS_AUM"
                    )
                if structure_flag and structure_position_flag:
                    reasons.append(
                        "PRODUCT_STRUCTURE_NAME_AND_HOLDINGS_SECURITY_FLAG"
                    )
                include = not reasons
                allocation_ratio = (
                    aligned_aum_million / portfolio_aum_million
                    if np.isfinite(aligned_aum_million)
                    and np.isfinite(portfolio_aum_million)
                    and portfolio_aum_million > 0
                    else math.nan
                )
                allocated_position_value = (
                    aligned_aum_million * 1e6 * total_percent_tna / 100.0
                    if np.isfinite(aligned_aum_million)
                    and np.isfinite(total_percent_tna)
                    else math.nan
                )
                allocated_unmapped_value = (
                    aligned_aum_million
                    * 1e6
                    * (total_percent_tna - mapped_percent_tna)
                    / 100.0
                    if np.isfinite(aligned_aum_million)
                    and np.isfinite(total_percent_tna)
                    and np.isfinite(mapped_percent_tna)
                    else math.nan
                )
                allocated_noncommon_or_unmapped_value = (
                    aligned_aum_million
                    * 1e6
                    * (total_percent_tna - common_percent_tna)
                    / 100.0
                    if np.isfinite(aligned_aum_million)
                    and np.isfinite(total_percent_tna)
                    and np.isfinite(common_percent_tna)
                    else math.nan
                )
                universe_rows.append(
                    {
                        **a.to_dict(),
                        "quarter_aligned_aum_million_diagnostic": a.aum_million,
                        "aum_million": aligned_aum_million,
                        "aum_date": aligned_aum_date,
                        "aum_date_gap_days": aligned_aum_gap_days,
                        "aum_share_class_count": aligned_aum_share_class_count,
                        "aum_alignment_target": "HOLDINGS_REPORT_DATE",
                        "portfolio_aum_million": portfolio_aum_million,
                        "portfolio_aum_date": portfolio_aum_date,
                        "portfolio_aum_date_gap_days": portfolio_aum_date_gap_days,
                        "portfolio_aum_share_class_count": portfolio_aum_share_class_count,
                        "etf_class_share_of_portfolio_aum": allocation_ratio,
                        "position_value_allocation_method": (
                            "CRSP_HOLDINGS_PERCENT_TNA_TIMES_CLOSEST_PRIOR_ETF_CLASS_AUM"
                        ),
                        "holdings_report_date": report,
                        "holdings_staleness_days": staleness,
                        "stale_le_45": staleness <= 45,
                        "stale_le_90": staleness <= 90,
                        "stale_le_120": staleness <= 120,
                        "stale_le_180": staleness <= 180,
                        "raw_pooled_portfolio_position_value_sum": total_value,
                        "reported_percent_tna_sum": total_percent_tna,
                        "mapped_percent_tna_sum": mapped_percent_tna,
                        "us_common_percent_tna_sum": common_percent_tna,
                        "position_value_sum": allocated_position_value,
                        "unmapped_position_value": allocated_unmapped_value,
                        "non_us_common_or_unmapped_position_value": allocated_noncommon_or_unmapped_value,
                        "position_value_to_aum": total_percent_tna / 100.0,
                        "one_minus_position_value_to_aum": (
                            1 - total_percent_tna / 100.0
                            if np.isfinite(total_percent_tna)
                            else math.nan
                        ),
                        "us_common_equity_value_share": eq_share,
                        "mapping_coverage_by_value": (
                            mapped_value / total_value
                            if total_value
                            else math.nan
                        ),
                        "n_positions_raw": int(cov.n_positions_raw),
                        "n_us_common_positions": int(g.is_us_common.sum()),
                        "included": include,
                        "quality_status": "AVAILABLE_BUT_PERIODIC",
                        "structure_name_review_flag": structure_flag,
                        "structure_security_position_count": int(
                            cov.structure_security_position_count
                        ),
                        "screen_notes": (
                            ";".join(reasons)
                            if reasons
                            else "NAME_REVIEW_ONLY_NOT_EXCLUDED"
                            if structure_flag
                            else "PASS_ARCHIVE_SCREEN"
                        ),
                    }
                )
                if reasons:
                    for reason in reasons:
                        exclusion_rows.append(
                            {
                                "quarter": q,
                                "crsp_portno": int(port),
                                "etf_tickers": a.etf_tickers,
                                "fund_name": a.fund_name,
                                "exclusion_reason": reason,
                                "evidence": (
                                    f"US common share={eq_share:.6f}; "
                                    f"ETF-class AUM={aligned_aum_million}; "
                                    f"all-share-class portfolio AUM={portfolio_aum_million}; "
                                    f"name_flag={structure_flag}; "
                                    f"holdings_security_flags="
                                    f"{int(cov.structure_security_position_count)}"
                                ),
                            }
                        )
                    continue
                cg = g.loc[
                    g.is_us_common & g.market_val.gt(0)
                ].copy()
                dup = int(cg.duplicated(["permno"]).sum())
                cg = (
                    cg.groupby("permno", as_index=False)
                    .agg(
                        report_dt=("report_dt", "max"),
                        market_val=("market_val", "sum"),
                        percent_tna=("percent_tna", "sum"),
                        market_cap_at_report=("market_cap_at_report", "max"),
                        company_name=("company_name", "last"),
                        sic4=("sic4", "last"),
                        security_name=("security_name", "last"),
                        ticker=("ticker", "last"),
                    )
                )
                cg["equity_sleeve_weight"] = cg.market_val / cg.market_val.sum()
                cg["actual_weight"] = cg.percent_tna / 100.0
                cg["etf_allocated_position_value"] = (
                    aligned_aum_million * 1e6 * cg.actual_weight
                )
                denom = cg.market_cap_at_report.sum(min_count=1)
                cg["pseudo_cap_implied_weight_observed_holdings"] = (
                    cg.market_cap_at_report / denom
                )
                cg["pseudo_wedge_weight"] = (
                    cg.actual_weight
                    - cg.pseudo_cap_implied_weight_observed_holdings
                )
                beta, r2, nreg = ols_style(cg)
                category, detail = classify_weight_style(
                    beta, r2, benchmark_verified=False
                )
                style_rows.append(
                    {
                        "quarter": q,
                        "crsp_portno": int(port),
                        "etf_tickers": a.etf_tickers,
                        "fund_name": a.fund_name,
                        "family": a.family,
                        "aum_million": aligned_aum_million,
                        "portfolio_aum_million": portfolio_aum_million,
                        "etf_class_share_of_portfolio_aum": allocation_ratio,
                        "holdings_report_date": report,
                        "holdings_staleness_days": staleness,
                        "n_mapped_common_positions": len(cg),
                        "n_regression_positions": nreg,
                        "duplicate_permno_positions_aggregated": dup,
                        "beta_log_weight_on_log_mcap": beta,
                        "r_squared": r2,
                        "mutually_exclusive_category": category,
                        "classification_detail": detail,
                        "benchmark_verified": False,
                    }
                )
                mapping_rows.append(
                    {
                        "quarter": q,
                        "crsp_portno": int(port),
                        "etf_tickers": a.etf_tickers,
                        "mapping_status": "SUMMARY",
                        "position_count": int(cov.n_positions_raw),
                        "position_value": total_value,
                        "position_value_basis": "RAW_POOLED_PORTFOLIO_HOLDINGS",
                        "mapped_value_share": (
                            mapped_value / total_value
                            if total_value
                            else math.nan
                        ),
                        "us_common_value_share": eq_share,
                        "duplicate_permno_positions": dup,
                        "security_name": "",
                        "cusip": "",
                    }
                )
                tq = stocks_top.loc[
                    stocks_top.quarter.eq(q),
                    [
                        "permno",
                        "market_cap",
                        "adv",
                        "amihud",
                        "company_name",
                        "sic4",
                    ],
                ]
                pc = cg.merge(
                    tq, on="permno", how="inner", suffixes=("_report", "_quarter")
                )
                pc["quarter"] = q
                pc["crsp_portno"] = int(port)
                pc["etf_tickers"] = a.etf_tickers
                pc["family"] = a.family
                pc["category"] = category
                pc["aum_million"] = aligned_aum_million
                pc["portfolio_aum_million"] = portfolio_aum_million
                pc["pseudo_wedge_dollar_contribution"] = (
                    aligned_aum_million * 1e6 * pc.pseudo_wedge_weight
                )
                pc["actual_dollar_exposure"] = pc.etf_allocated_position_value
                contrib_frames.append(pc)
    universe = pd.DataFrame(universe_rows)
    exclusions = pd.DataFrame(exclusion_rows)
    styles = pd.DataFrame(style_rows)
    mappings = pd.DataFrame(mapping_rows)
    contrib = (
        pd.concat(contrib_frames, ignore_index=True)
        if contrib_frames
        else pd.DataFrame()
    )
    return universe, exclusions, styles, mappings, contrib, provenance


def add_decile(x: pd.Series) -> pd.Series:
    if x.notna().sum() < 10:
        return pd.Series(pd.NA, index=x.index, dtype="Int64")
    return pd.qcut(
        x.rank(method="first"), 10, labels=False, duplicates="drop"
    ).astype("Int64")


def fit_reduced_regression(
    d: pd.DataFrame, outcome: str, liquidity: str
) -> tuple[dict, pd.DataFrame]:
    x = d.dropna(subset=[outcome, liquidity, "market_cap", "sic4"]).copy()
    x["size_decile"] = x.groupby("quarter").market_cap.transform(add_decile)
    x["liquidity_decile"] = x.groupby("quarter")[liquidity].transform(add_decile)
    x["etf_ownership_decile"] = x.groupby(
        "quarter"
    ).total_etf_ownership.transform(add_decile)
    x["n_etfs_decile"] = x.groupby(
        "quarter"
    ).n_etfs_holding.transform(add_decile)
    x["size_industry"] = (
        x.size_decile.astype(str)
        + "_"
        + x.sic4.fillna(-1).astype(int).astype(str)
    )
    x["quarter_s"] = (
        x.quarter.dt.strftime("%YQ") + x.quarter.dt.quarter.astype(str)
    )
    cats = [
        "size_industry",
        "liquidity_decile",
        "quarter_s",
        "etf_ownership_decile",
        "n_etfs_decile",
    ]
    enc = OneHotEncoder(
        handle_unknown="ignore", drop="first", sparse_output=True
    )
    X = enc.fit_transform(x[cats].astype(str))
    y = x[outcome].to_numpy(dtype=float)
    model = LinearRegression().fit(X, y)
    fit = model.predict(X)
    resid = y - fit
    sse = np.square(resid).sum()
    tss = np.square(y - y.mean()).sum()
    r2 = 1 - sse / tss if tss > 0 else math.nan
    p = X.shape[1] + 1
    n = len(y)
    adj = (
        1 - (1 - r2) * (n - 1) / (n - p)
        if n > p
        else math.nan
    )
    pred = np.full(n, np.nan)
    for q in x.quarter_s.unique():
        test = x.quarter_s.eq(q).to_numpy()
        train = ~test
        if train.sum() <= p:
            continue
        m = LinearRegression().fit(X[train], y[train])
        pred[test] = m.predict(X[test])
    ok = np.isfinite(pred)
    cv_r2 = (
        1
        - np.square(y[ok] - pred[ok]).sum()
        / np.square(y[ok] - y[ok].mean()).sum()
        if ok.any()
        else math.nan
    )
    x["residual"] = resid
    raw_sd = float(np.std(y, ddof=1))
    resid_sd = float(np.std(resid, ddof=1))
    result = {
        "outcome": outcome,
        "liquidity_version": liquidity,
        "specification": "REDUCED_DIAGNOSTIC_NO_INDEX_MEMBERSHIP",
        "status": "BLOCKED_INDEX_MEMBERSHIP",
        "observations": n,
        "quarters": x.quarter.nunique(),
        "adjusted_r_squared": adj,
        "raw_outcome_sd": raw_sd,
        "residual_sd": resid_sd,
        "residual_sd_over_raw_sd": (
            resid_sd / raw_sd if raw_sd else math.nan
        ),
        "residual_p10": float(np.quantile(resid, 0.10)),
        "residual_p50": float(np.quantile(resid, 0.50)),
        "residual_p90": float(np.quantile(resid, 0.90)),
        "residual_p90_minus_p10": float(
            np.quantile(resid, 0.90) - np.quantile(resid, 0.10)
        ),
        "units": (
            "dollars"
            if "dollar" in outcome and "mktcap" not in outcome
            else "market_cap_share"
            if "mktcap" in outcome
            else "share_0_1"
        ),
        "leave_one_quarter_out_predictive_r_squared": cv_r2,
        "index_membership_included": False,
        "benchmark_weight_status": "MISSING",
    }
    return result, x[["permno", "quarter", "residual"]]


def aggregate_stock(
    contrib: pd.DataFrame, stocks_top: pd.DataFrame
) -> pd.DataFrame:
    c = contrib.copy()
    c["non_cap_dollar"] = np.where(
        c.category.eq("CAP_HIGH_FIT"), 0.0, c.actual_dollar_exposure
    )
    agg = (
        c.groupby(["permno", "quarter"])
        .agg(
            total_etf_dollar_exposure=("actual_dollar_exposure", "sum"),
            non_cap_dollar_exposure=("non_cap_dollar", "sum"),
            pseudo_wedge_dollar_observed_holdings=(
                "pseudo_wedge_dollar_contribution",
                "sum",
            ),
            n_etfs_holding=("crsp_portno", "nunique"),
        )
        .reset_index()
    )
    cat = (
        c.pivot_table(
            index=["permno", "quarter"],
            columns="category",
            values="actual_dollar_exposure",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    cat.columns = [
        (
            str(z).lower() + "_dollar_exposure"
            if z not in ["permno", "quarter"]
            else z
        )
        for z in cat.columns
    ]
    out = (
        stocks_top.merge(agg, on=["permno", "quarter"], how="left")
        .merge(cat, on=["permno", "quarter"], how="left")
    )
    for col in [
        "total_etf_dollar_exposure",
        "non_cap_dollar_exposure",
        "pseudo_wedge_dollar_observed_holdings",
        "n_etfs_holding",
    ]:
        out[col] = out[col].fillna(0)
    out["shape"] = out.non_cap_dollar_exposure.div(
        out.total_etf_dollar_exposure.where(
            out.total_etf_dollar_exposure.gt(0)
        )
    )
    out["pseudo_wedge_mktcap_observed_holdings"] = (
        out.pseudo_wedge_dollar_observed_holdings / out.market_cap
    )
    out["total_etf_ownership"] = out.total_etf_dollar_exposure / out.market_cap
    out["wedge_dollar"] = np.nan
    out["wedge_mktcap"] = np.nan
    out["benchmark_weight_status"] = "MISSING"
    out["index_membership_status"] = "BLOCKED_INDEX_MEMBERSHIP"
    return out


def regression_and_diagnostics(
    stock: pd.DataFrame, contrib: pd.DataFrame, outdir: Path
) -> None:
    result_rows, residual_rows, resid_maps = [], [], {}
    for primary_outcome, primary_units in [
        ("wedge_dollar", "dollars"),
        ("wedge_mktcap", "market_cap_share"),
    ]:
        for liq in ["amihud", "adv"]:
            result_rows.append(
                {
                "outcome": primary_outcome,
                "liquidity_version": liq,
                "specification": "PRIMARY_FROZEN_WITH_INDEX_MEMBERSHIP",
                "status": "BLOCKED_BENCHMARK_WEIGHTS_AND_INDEX_MEMBERSHIP",
                "observations": 0,
                "quarters": 0,
                "adjusted_r_squared": np.nan,
                "raw_outcome_sd": np.nan,
                "residual_sd": np.nan,
                "residual_sd_over_raw_sd": np.nan,
                "residual_p10": np.nan,
                "residual_p50": np.nan,
                "residual_p90": np.nan,
                "residual_p90_minus_p10": np.nan,
                "units": primary_units,
                "leave_one_quarter_out_predictive_r_squared": np.nan,
                "index_membership_included": False,
                "benchmark_weight_status": "MISSING",
                }
            )
    for outcome in [
        "shape",
        "pseudo_wedge_dollar_observed_holdings",
        "pseudo_wedge_mktcap_observed_holdings",
    ]:
        for liq in ["amihud", "adv"]:
            res, rr = fit_reduced_regression(stock, outcome, liq)
            result_rows.append(res)
            rr["outcome"] = outcome
            rr["liquidity_version"] = liq
            residual_rows.append(rr)
            resid_maps[(outcome, liq)] = rr
    pd.DataFrame(result_rows).to_csv(
        outdir / "gate1_confounds_regression_results.csv", index=False
    )
    residuals = pd.concat(residual_rows, ignore_index=True)
    dist = []
    for keys, g in residuals.groupby(["outcome", "liquidity_version"]):
        q = g.residual.quantile([0.1, 0.5, 0.9])
        dist.append(
            {
                "outcome": keys[0],
                "liquidity_version": keys[1],
                "n": len(g),
                "p10": q.loc[0.1],
                "p50": q.loc[0.5],
                "p90": q.loc[0.9],
                "p90_minus_p10": q.loc[0.9] - q.loc[0.1],
                "units": (
                    "dollars"
                    if "dollar" in keys[0] and "mktcap" not in keys[0]
                    else "market_cap_share"
                    if "mktcap" in keys[0]
                    else "share_0_1"
                ),
                "status": "REDUCED_DIAGNOSTIC_ONLY",
            }
        )
    pd.DataFrame(dist).to_csv(
        outdir / "gate1_residual_distribution.csv", index=False
    )
    primary = resid_maps[
        ("pseudo_wedge_mktcap_observed_holdings", "amihud")
    ]
    x = stock.merge(primary, on=["permno", "quarter"], how="inner")
    total_var = float(x.pseudo_wedge_mktcap_observed_holdings.var())
    means = x.groupby("permno").pseudo_wedge_mktcap_observed_holdings.mean()
    between = float(means.var())
    within = float(
        x.groupby("permno").pseudo_wedge_mktcap_observed_holdings.var().mean()
    )
    lag = x.sort_values(["permno", "quarter"])
    lag["lag"] = lag.groupby(
        "permno"
    ).pseudo_wedge_mktcap_observed_holdings.shift()
    persistence = float(
        lag[["pseudo_wedge_mktcap_observed_holdings", "lag"]]
        .corr()
        .iloc[0, 1]
    )
    qsq = x.groupby("quarter").residual.apply(lambda z: np.square(z).sum())
    fam = (
        contrib.groupby("family")
        .pseudo_wedge_dollar_contribution.apply(lambda z: np.square(z).sum())
        .sort_values(ascending=False)
    )
    rows = [
        {
            "metric": metric,
            "value": np.nan,
            "measurement_status": "BLOCKED_BENCHMARK_WEIGHTS",
        }
        for metric in [
            "primary_wedge_between_stock_variance",
            "primary_wedge_within_stock_variance",
            "primary_wedge_within_stock_share_total",
            "primary_wedge_quarter_to_quarter_persistence",
            "primary_wedge_top_family_share_squared_residual_variation",
            "primary_wedge_top5_family_share_squared_residual_variation",
            "primary_wedge_top10_family_share_squared_residual_variation",
            "primary_wedge_top_quarter_share_squared_residual_variation",
            "primary_wedge_inverse_hhi_effective_family_count",
            "primary_wedge_inverse_hhi_effective_quarter_count",
        ]
    ] + [
        {
            "metric": "between_stock_variance",
            "value": between,
            "measurement_status": "PSEUDO_WEDGE_DIAGNOSTIC",
        },
        {
            "metric": "within_stock_variance",
            "value": within,
            "measurement_status": "PSEUDO_WEDGE_DIAGNOSTIC",
        },
        {
            "metric": "within_stock_share_total",
            "value": within / total_var if total_var else np.nan,
            "measurement_status": "PSEUDO_WEDGE_DIAGNOSTIC",
        },
        {
            "metric": "quarter_to_quarter_persistence",
            "value": persistence,
            "measurement_status": "PSEUDO_WEDGE_DIAGNOSTIC",
        },
        {
            "metric": "top_family_share_squared_contribution",
            "value": fam.iloc[0] / fam.sum() if len(fam) else np.nan,
            "measurement_status": "PROXY_NOT_RESIDUAL_ATTRIBUTION",
        },
        {
            "metric": "top5_family_share_squared_contribution",
            "value": fam.iloc[:5].sum() / fam.sum() if len(fam) else np.nan,
            "measurement_status": "PROXY_NOT_RESIDUAL_ATTRIBUTION",
        },
        {
            "metric": "top10_family_share_squared_contribution",
            "value": fam.iloc[:10].sum() / fam.sum() if len(fam) else np.nan,
            "measurement_status": "PROXY_NOT_RESIDUAL_ATTRIBUTION",
        },
        {
            "metric": "inverse_hhi_effective_family_count",
            "value": inverse_hhi(fam.values),
            "measurement_status": "PROXY_NOT_RESIDUAL_ATTRIBUTION",
        },
        {
            "metric": "top_quarter_share_squared_residual",
            "value": qsq.max() / qsq.sum(),
            "measurement_status": "REDUCED_DIAGNOSTIC_RESIDUAL",
        },
        {
            "metric": "inverse_hhi_effective_quarter_count",
            "value": inverse_hhi(qsq.values),
            "measurement_status": "REDUCED_DIAGNOSTIC_RESIDUAL",
        },
    ]
    pd.DataFrame(rows).to_csv(
        outdir / "gate1_variation_concentration.csv", index=False
    )
    cmap = contrib.groupby(["permno", "quarter"])

    def contributors(permno, q):
        g = (
            cmap.get_group((permno, q))
            .sort_values(
                "pseudo_wedge_dollar_contribution",
                key=lambda z: z.abs(),
                ascending=False,
            )
            .head(5)
        )
        return " | ".join(
            f"{r.etf_tickers}:{r.category}:{r.pseudo_wedge_dollar_contribution:.2f}"
            for r in g.itertuples()
        )

    x["five_largest_contributing_etfs"] = [
        (
            contributors(r.permno, r.quarter)
            if (r.permno, r.quarter) in cmap.groups
            else ""
        )
        for r in x.itertuples()
    ]
    cols = [
        "permno",
        "company_name",
        "quarter",
        "sic4",
        "market_cap",
        "adv",
        "amihud",
        "index_membership_status",
        "total_etf_dollar_exposure",
        "pseudo_wedge_dollar_observed_holdings",
        "shape",
        "residual",
        "five_largest_contributing_etfs",
    ]
    x["outcome"] = "pseudo_wedge_mktcap_observed_holdings"
    x["measurement_status"] = "REDUCED_DIAGNOSTIC_ONLY"
    cols.extend(["outcome", "measurement_status"])
    x.nlargest(20, "residual")[cols].to_csv(
        outdir / "gate1_extreme_positive_20.csv", index=False
    )
    x.nsmallest(20, "residual")[cols].to_csv(
        outdir / "gate1_extreme_negative_20.csv", index=False
    )
    style = pd.read_csv(outdir / "etf_weight_style_quarter.csv")
    plt.figure(figsize=(8, 5))
    plt.hist(
        style.beta_log_weight_on_log_mcap.dropna(),
        bins=50,
        color="#315a7d",
    )
    for cut, ls in [(-0.15, ":"), (0.15, ":"), (0.85, "--"), (1.15, "--")]:
        plt.axvline(cut, color="black", ls=ls)
    plt.xlabel("beta: log equity-sleeve weight on log market cap")
    plt.ylabel("ETF-quarter count")
    plt.tight_layout()
    plt.savefig(outdir / "gate1_beta_histogram.png", dpi=160)
    plt.close()
    plt.figure(figsize=(8, 5))
    plt.hist(x.residual.dropna(), bins=60, color="#8b4f3d")
    plt.xlabel("Reduced-diagnostic residual: pseudo wedge / market cap")
    plt.ylabel("Stock-quarter count")
    plt.tight_layout()
    plt.savefig(outdir / "gate1_residual_distribution.png", dpi=160)
    plt.close()


def inventory(outdir: Path, provenance: list[dict]) -> None:
    holdings = sorted(
        (RAW / "rescue_remaining").glob(
            "crsp_holdings_etf_20*_b*/part_*.parquet"
        )
    )
    summary = [RAW / f"crsp_fund_summary2_{y}.parquet" for y in range(2018, 2027)]
    daily = [
        RAW / "rescue" / f"crsp_dsf_allcols_{y}.parquet"
        for y in range(2014, 2025)
    ] + [RAW / "rescue" / "newcrsp_crsp_dsf_v2_2025.parquet"]
    actual = [RAW / f"ibes_actuals_eps_{y}.parquet" for y in range(2012, 2027)]
    stats = [RAW / f"ibes_statsumu_eps_{y}.parquet" for y in range(2012, 2027)]
    empty: list[Path] = []
    objects = [
        ("ETF periodic portfolio holdings", "crsp.holdings", str(RAW / "rescue_remaining/crsp_holdings_etf_YYYY_bNNNN/part_*.parquet"), holdings, "report snapshot", "report_dt", "crsp_portno", "PERMNO/CUSIP", "2018-01-31", "2026-06-30", "AVAILABLE_BUT_PERIODIC", "Gate0 weights and preliminary Gate1 only"),
        ("benchmark/index constituent weights", "none", "", empty, "unknown", "unknown", "index", "security", "UNKNOWN", "UNKNOWN", "MISSING", "Blocks final Gate0/Gate1/Gate2"),
        ("daily published PCF", "none", "", empty, "daily", "economic date unknown", "ETF", "security", "UNKNOWN", "UNKNOWN", "EXTERNAL_REQUIRED", "Blocks final Gate2/Gate3"),
        ("actual baskets exchanged with APs", "none", "", empty, "transaction/basket", "order/settlement unknown", "ETF/AP", "security", "UNKNOWN", "UNKNOWN", "EXTERNAL_REQUIRED", "Blocks final Gate2/Gate3 strong"),
        ("multiple custom baskets same date", "none", "", empty, "basket", "timestamp unknown", "ETF/AP", "security", "UNKNOWN", "UNKNOWN", "EXTERNAL_REQUIRED", "Blocks custom-basket coverage"),
        ("ETF AUM/net assets", "crsp.fund_summary2", str(RAW / "crsp_fund_summary2_YYYY.parquet"), summary, "quarterly/monthly summary", "tna_latest_dt", "crsp_fundno/crsp_portno", "none", "2018", "2026-06-30", "AVAILABLE_AND_VERIFIED", "ETF-class screen/scaling and all-share-class pooled holdings denominator"),
        ("daily ETF Shares Outstanding", "CRSP stock shrout not validated", str(RAW / "rescue/*dsf*"), daily, "field appears daily", "trading date", "ETF PERMNO", "none", "2014", "2025", "VISIBLE_NOT_VERIFIED", "Not permitted as primary flow"),
        ("daily net FundFlow", "none", "", empty, "daily", "economic date unknown", "ETF", "none", "UNKNOWN", "UNKNOWN", "EXTERNAL_REQUIRED", "Blocks final Gate2"),
        ("gross daily creations and redemptions", "none", "", empty, "daily", "order/settlement unknown", "ETF/AP", "none", "UNKNOWN", "UNKNOWN", "EXTERNAL_REQUIRED", "Blocks Gate2 gross-route PASS"),
        ("ETF secondary-market dollar volume", "CRSP daily stock", str(RAW / "rescue/*dsf*"), daily, "daily", "trading_date", "ETF PERMNO", "none", "2014", "2025", "AVAILABLE_AND_VERIFIED", "Extreme ceiling only"),
        ("stock daily returns and dollar volume", "CRSP daily stock", str(RAW / "rescue/*dsf*"), daily, "daily", "trading_date", "PERMNO", "none", "2014", "2025", "AVAILABLE_AND_VERIFIED", "Top1000; legacy DSF lacks shrcd, so CIZ effective-date NS/EQTY/COM/Y common-stock flags are used consistently"),
        ("earnings actual consensus date and time", "IBES actu_epsus plus statsumu", str(RAW / "ibes_actuals_eps_YYYY.parquet"), actual + stats, "event plus monthly snapshots", "anndats/statpers", "IBES ticker", "CUSIP", "2012", "2026-05-14", "VISIBLE_NOT_VERIFIED", "Date/actual/consensus usable; anntims timezone unresolved"),
        ("index-membership history", "crsp.stkindmembership_ind", str(RAW / "crsp_stkindmembership_ind_full.parquet"), [RAW / "crsp_stkindmembership_ind_full.parquet"], "interval", "mbrstartdt/mbrenddt", "indno", "PERMNO", "historical", "2025/2026", "VISIBLE_NOT_VERIFIED", "Internal indno lacks verified S&P/Russell name mapping; blocks primary confounds"),
        ("industry classifications", "CRSP CIZ stocknames SIC", str(RAW / "rescue/newcrsp_crsp_stocknames_v2_full.parquet"), [RAW / "rescue/newcrsp_crsp_stocknames_v2_full.parquet"], "effective interval", "namedt/nameenddt", "none", "PERMNO", "historical", "2026", "AVAILABLE_BUT_PROXY", "SIC4 fallback; GICS6 unavailable"),
    ]
    rows = []
    for (
        logical,
        table,
        pattern,
        paths,
        freq,
        date,
        fund,
        sec,
        start,
        end,
        status,
        use,
    ) in objects:
        paths = [p for p in paths if p.exists()]
        rows.append(
            {
                "logical_data_object": logical,
                "source_vendor_schema_table": table,
                "local_path_pattern": pattern,
                "source_files": ";".join(str(p) for p in paths[:10])
                + (f";...+{len(paths)-10}" if len(paths) > 10 else ""),
                "observation_frequency": freq,
                "economic_date": date,
                "publication_availability_timestamp": "UNKNOWN_OR_NOT_DOCUMENTED",
                "fund_identifier": fund,
                "security_identifier": sec,
                "coverage_start": start,
                "coverage_end": end,
                "number_of_files": len(paths),
                "number_of_rows": parquet_rows(paths),
                "point_in_time": (
                    "YES"
                    if "interval" in freq or "snapshot" in freq
                    else "UNKNOWN"
                ),
                "survivorship_free": (
                    "NOT_DOCUMENTED"
                    if status not in ["MISSING", "EXTERNAL_REQUIRED"]
                    else "UNKNOWN"
                ),
                "quality_status": status,
                "permitted_gate_use": use,
            }
        )
    pd.DataFrame(rows).to_csv(
        outdir / "gate0_data_object_inventory.csv", index=False
    )
    prov = pd.DataFrame(provenance)
    prov["economic_date_min"] = "COMPUTED_IN_ANALYSIS_OBJECT_OR_FILE_PARTITION"
    prov["economic_date_max"] = "COMPUTED_IN_ANALYSIS_OBJECT_OR_FILE_PARTITION"
    prov["schema_signature"] = "SEE_PARQUET_AND_META_SCHEMA"
    prov["point_in_time_selection"] = "NO_LATER_THAN_TARGET"
    prov.to_csv(outdir / "source_file_provenance.csv", index=False)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", required=True)
    ap.add_argument("--pilot-pass", required=True)
    ap.add_argument(
        "--config",
        default=str(CONFIG_PATH),
    )
    ap.add_argument(
        "--data-contract",
        default=str(DATA_CONTRACT_PATH),
    )
    ap.add_argument(
        "--code-root",
        default=str(CODE_ROOT),
    )
    ap.add_argument("--manifest", default=str(MANIFEST))
    args = ap.parse_args()
    try:
        require_bound_path(args.code_root, CODE_ROOT, label="code_root")
        require_bound_path(args.config, CONFIG_PATH, label="config")
        require_bound_path(
            args.data_contract,
            DATA_CONTRACT_PATH,
            label="data_contract",
        )
        require_bound_path(args.manifest, MANIFEST, label="manifest")
        config, _ = load_json_document(
            CONFIG_PATH,
            label="gate configuration",
            archive_root=ARCHIVE,
        )
        local_authorization = authorize_local_pilot(
            pilot_pass_path=args.pilot_pass,
            code_root=CODE_ROOT,
            code_files=config["scientific_fileset"],
            config_path=CONFIG_PATH,
            data_contract_path=DATA_CONTRACT_PATH,
            required_invariant_ids=config["required_invariant_ids"],
            archive_root=ARCHIVE,
        )
        candidate_ok, candidate_result = candidate_implementation_conformance(
            config
        )
        if not candidate_ok:
            raise PilotContractError(
                "CANDIDATE_IMPLEMENTATION_STATE_INVALID",
                str(candidate_result),
            )
        # The legacy implementation is intentionally disabled. A future
        # contract-conformant candidate may be piloted with activation enabled;
        # the same config/code hashes and conformance invariant must then match
        # here before the canonical manifest is touched.
        if config.get("full_run_enabled") is not True:
            raise PilotContractError(
                "FULL_RUN_DISABLED_BY_FROZEN_CONFIG",
                str(config.get("full_run_disabled_reason", "unspecified")),
            )
        authorize_manifest(local_authorization, MANIFEST)
    except PilotContractError as exc:
        print(f"P1 full-run preflight refused: {exc}")
        raise SystemExit(exc.exit_code) from exc
    except (KeyError, TypeError, ValueError) as exc:
        refusal = PilotContractError("PREFLIGHT_SCHEMA_ERROR", str(exc))
        print(f"P1 full-run preflight refused: {refusal}")
        raise SystemExit(refusal.exit_code) from exc
    load_scientific_runtime()
    outdir = Path(args.output)
    outdir.mkdir(parents=True, exist_ok=True)
    names = load_names()
    daily, dprov = load_daily()
    _, stocks_top = stock_quarters(daily, names)
    aum, etf_aum_timeline, portfolio_aum_timeline, aprov = load_fund_aum()
    universe, exclusions, styles, mappings, contrib, hprov = load_holdings_and_build(
        aum,
        etf_aum_timeline,
        portfolio_aum_timeline,
        daily,
        names,
        stocks_top,
    )
    universe.to_csv(outdir / "etf_universe_quarter.csv", index=False)
    exclusions.to_csv(outdir / "etf_exclusion_log.csv", index=False)
    mappings.to_csv(outdir / "security_mapping_diagnostics.csv", index=False)
    styles.to_csv(outdir / "etf_weight_style_quarter.csv", index=False)
    summary = (
        styles.groupby("mutually_exclusive_category", dropna=False)
        .agg(
            etf_quarter_count=("crsp_portno", "size"),
            unique_etf_count=("crsp_portno", "nunique"),
            unique_sponsor_family_count=("family", "nunique"),
            total_aum_million=("aum_million", "sum"),
            median_aum_million=("aum_million", "median"),
            median_number_holdings=("n_mapped_common_positions", "median"),
            beta_p10=("beta_log_weight_on_log_mcap", lambda x: x.quantile(0.1)),
            beta_median=("beta_log_weight_on_log_mcap", "median"),
            beta_p90=("beta_log_weight_on_log_mcap", lambda x: x.quantile(0.9)),
            r2_p10=("r_squared", lambda x: x.quantile(0.1)),
            r2_median=("r_squared", "median"),
            r2_p90=("r_squared", lambda x: x.quantile(0.9)),
        )
        .reset_index()
    )
    summary = pd.DataFrame(
        {
            "mutually_exclusive_category": [
                "CAP_HIGH_FIT",
                "CAP_SAMPLED",
                "EQUAL_WEIGHTED",
                "OTHER_WEIGHTED",
            ]
        }
    ).merge(summary, on="mutually_exclusive_category", how="left")
    for count_col in [
        "etf_quarter_count",
        "unique_etf_count",
        "unique_sponsor_family_count",
    ]:
        summary[count_col] = summary[count_col].fillna(0).astype(int)
    summary["total_aum_million"] = summary.total_aum_million.fillna(0.0)
    summary["benchmark_status"] = "MISSING"
    summary.to_csv(outdir / "etf_weight_style_summary.csv", index=False)
    stock = aggregate_stock(contrib, stocks_top)
    stock.to_parquet(outdir / "stock_shape_wedge_quarter.parquet", index=False)
    contrib.to_parquet(outdir / "_work_position_contributions.parquet", index=False)
    regression_and_diagnostics(stock, contrib, outdir)
    inventory(outdir, dprov + aprov + hprov)
    versions = {
        "python": platform.python_version(),
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "pyarrow": pyarrow.__version__,
        "sklearn": "1.5.1",
        "matplotlib": matplotlib.__version__,
    }
    (outdir / "package_versions.json").write_text(
        json.dumps(versions, indent=2) + "\n"
    )
    run = {
        "archive": str(ARCHIVE),
        "manifest": str(MANIFEST),
        "years": list(YEARS),
        "primary_staleness_days": PRIMARY_MAX_STALENESS_DAYS,
        "holdings_alignment": "latest report_dt on or before quarter-end",
        "aum_alignment": (
            "ETF-class AUM and all-share-class pooled-portfolio AUM are each "
            "aligned by latest share-class observation on or before report_dt"
        ),
        "pooled_holdings_allocation": (
            "actual holdings weight = CRSP report-date percent_tna / 100; "
            "ETF dollar exposure = weight * closest-prior ETF-class AUM; "
            "all-share-class AUM retained as an alignment diagnostic"
        ),
        "aum_alignment_gap_rule": "each selected share-class observation <=120 calendar days old",
        "quarter_end_market_cap_max_staleness_days": 7,
        "etf_flag_rule": (
            "historical fund_summary2 et_flag == F; missing values are not "
            "backfilled from current fund headers"
        ),
        "benchmark_weights_found": False,
        "index_membership_name_mapping_verified": False,
        "treatment_coefficients_inspected": False,
    }
    (outdir / "gate1_run_config.json").write_text(
        json.dumps(run, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "universe_rows": len(universe),
                "included": int(universe.included.sum()),
                "style_rows": len(styles),
                "stock_rows": len(stock),
                "contribution_rows": len(contrib),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
