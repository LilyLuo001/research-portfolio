#!/usr/bin/env python3
"""SCC-side minimal historical mapping, denominator, exposure, and liquidity build.

Inputs are the locally selected strictly-preannouncement N-PORT positions and
explicit WRDS mirror files. No earnings values or quote outcomes are read.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd


HERE = Path(__file__).resolve().parent
ARCHIVE = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared")
RAW = ARCHIVE / "raw"
HOLDINGS = HERE / "PREANNOUNCEMENT_HOLDINGS.parquet"
PACKAGES = HERE / "PACKAGE_INPUTS.csv"
STOCKNAMES = RAW / "rescue" / "newcrsp_crsp_stocknames_v2_full.parquet"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def norm(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().upper()


def build_name_indexes(sn: pd.DataFrame):
    sn = sn.copy()
    sn["namedt"] = pd.to_datetime(sn.namedt, errors="coerce")
    sn["nameenddt"] = pd.to_datetime(sn.nameenddt, errors="coerce").fillna(pd.Timestamp("2099-12-31"))
    for c in ["cusip9", "cusip", "ticker", "sharetype", "securitytype", "securitysubtype", "usincflg"]:
        sn[c] = sn[c].map(norm)
    by9, by8 = {}, {}
    for row in sn.itertuples(index=False):
        if row.cusip9:
            by9.setdefault(row.cusip9, []).append(row)
        if row.cusip:
            by8.setdefault(row.cusip[:8], []).append(row)
    return by9, by8


def map_position(row, by9, by8):
    cusip9 = norm(row.cusip9)
    asof = pd.Timestamp(row.pre_report_date)
    def active(rows):
        return [r for r in rows if r.namedt <= asof <= r.nameenddt]
    method = "exact_cusip9"
    cand = active(by9.get(cusip9, []))
    if not cand:
        method = "exact_cusip8"
        cand = active(by8.get(cusip9[:8], []))
    common = [
        r for r in cand if r.sharetype == "NS" and r.securitytype == "EQTY"
        and r.securitysubtype == "COM" and r.usincflg == "Y"
    ]
    permnos = sorted({int(r.permno) for r in common})
    if len(permnos) != 1:
        return {
            "mapping_status": "unmatched" if not cand else ("non_us_common" if not common else "ambiguous"),
            "mapping_method": method if cand else "none",
            "permno": np.nan,
            "crsp_ticker": "",
            "issuer_name_crsp": "",
            "siccd": np.nan,
            "candidate_permnos": ";".join(map(str, permnos)),
        }
    chosen = next(r for r in common if int(r.permno) == permnos[0])
    return {
        "mapping_status": "exact_matched",
        "mapping_method": method,
        "permno": permnos[0],
        "crsp_ticker": chosen.ticker,
        "issuer_name_crsp": chosen.issuernm,
        "siccd": chosen.siccd,
        "candidate_permnos": str(permnos[0]),
    }


def load_daily(wanted: set[int]):
    frames, lineage = [], []
    for year in range(2019, 2025):
        path = RAW / f"crsp_dsf_{year}.parquet"
        d = pd.read_parquet(path, columns=["permno", "date", "prc", "vol", "shrout", "cfacshr"])
        d = d[d.permno.isin(wanted)].copy()
        d["source_year"] = year
        frames.append(d)
        lineage.append({"path": str(path), "sha256": sha256(path), "selected_rows": len(d)})
    out = pd.concat(frames, ignore_index=True)
    out["permno"] = out.permno.astype(int)
    out["date"] = pd.to_datetime(out.date)
    out["prc"] = pd.to_numeric(out.prc, errors="coerce").abs()
    out["vol"] = pd.to_numeric(out.vol, errors="coerce")
    out["shrout"] = pd.to_numeric(out.shrout, errors="coerce")
    out["cfacshr"] = pd.to_numeric(out.cfacshr, errors="coerce")
    out = out.sort_values(["permno", "date"]).drop_duplicates(["permno", "date"], keep="last")
    return out, lineage


def load_shares(wanted: set[int]):
    frames, lineage = [], []
    for year in range(2019, 2025):
        path = RAW / f"crsp_dseshares_{year}.parquet"
        d = pd.read_parquet(path, columns=["permno", "shrout", "shrsdt", "shrenddt", "shrflg"])
        d = d[d.permno.isin(wanted)].copy()
        d["source_year"] = year
        frames.append(d)
        lineage.append({"path": str(path), "sha256": sha256(path), "selected_rows": len(d)})
    out = pd.concat(frames, ignore_index=True)
    out["permno"] = out.permno.astype(int)
    out["shrsdt"] = pd.to_datetime(out.shrsdt, errors="coerce")
    out["shrenddt"] = pd.to_datetime(out.shrenddt, errors="coerce").fillna(pd.Timestamp("2099-12-31"))
    out["shrout"] = pd.to_numeric(out.shrout, errors="coerce")
    return out, lineage


def daily_index(daily):
    out = {}
    for permno, g in daily.groupby("permno", sort=False):
        g = g.sort_values("date")
        out[int(permno)] = (list(g.date), list(g.itertuples(index=False)))
    return out


def prior_daily(index, permno, target, max_gap=7):
    dates, rows = index.get(int(permno), ([], []))
    target = pd.Timestamp(target)
    pos = bisect.bisect_right(dates, target) - 1
    if pos < 0 or (target - dates[pos]).days > max_gap:
        return None
    return rows[pos]


def active_shares(shares, permno, target):
    t = pd.Timestamp(target)
    x = shares[(shares.permno == int(permno)) & (shares.shrsdt <= t) & (t <= shares.shrenddt)]
    if x.empty:
        return None
    # Duplicated annual partitions can carry the same interval; take the latest start and verify agreement.
    x = x.sort_values(["shrsdt", "source_year"]).drop_duplicates(["shrsdt", "shrenddt", "shrout"], keep="last")
    x = x[x.shrsdt == x.shrsdt.max()]
    vals = x.shrout.dropna().unique()
    return float(vals[0]) * 1000.0 if len(vals) == 1 and vals[0] > 0 else None


def empirical_tiers(exposure: pd.DataFrame) -> pd.DataFrame:
    chunks = []
    for wave, g in exposure.groupby("wave_id", sort=True):
        g = g[g.exposure_ownership > 0].sort_values(["exposure_ownership", "permno"]).copy()
        n = len(g)
        q1 = g.exposure_ownership.iloc[math.ceil(n / 3) - 1]
        q2 = g.exposure_ownership.iloc[math.ceil(2 * n / 3) - 1]
        g["q1"] = q1
        g["q2"] = q2
        g["provisional_tier"] = np.where(g.exposure_ownership <= q1, "low", np.where(g.exposure_ownership > q2, "high", "middle"))
        g["tier_rule_status"] = "PROVISIONAL_RECONCILED_CONTRACT_NOT_PI_SIGNED"
        chunks.append(g)
    return pd.concat(chunks, ignore_index=True)


def main():
    holdings = pd.read_parquet(HOLDINGS)
    h = holdings[holdings.is_common_equity_candidate].copy()
    sn = pd.read_parquet(STOCKNAMES)
    by9, by8 = build_name_indexes(sn)
    mapped = pd.DataFrame([map_position(r, by9, by8) for r in h.itertuples(index=False)])
    h = pd.concat([h.reset_index(drop=True), mapped], axis=1)
    h.to_csv(HERE / "POSITION_IDENTIFIER_MAPPING.csv", index=False)
    wanted = set(h.loc[h.mapping_status.eq("exact_matched"), "permno"].dropna().astype(int))
    daily, daily_lineage = load_daily(wanted)
    shares, share_lineage = load_shares(wanted)
    didx = daily_index(daily)
    h["denominator_shares"] = np.nan
    h["denominator_source"] = ""
    h["dsf_date"] = ""
    h["dsf_shrout"] = np.nan
    h["cfacshr"] = np.nan
    for i, row in h[h.mapping_status.eq("exact_matched")].iterrows():
        denom = active_shares(shares, int(row.permno), row.pre_report_date)
        drow = prior_daily(didx, int(row.permno), row.pre_report_date)
        if denom is not None:
            h.at[i, "denominator_shares"] = denom
            h.at[i, "denominator_source"] = "crsp_dseshares_active_at_nport_report_date"
        elif drow is not None and pd.notna(drow.shrout) and drow.shrout > 0:
            h.at[i, "denominator_shares"] = float(drow.shrout) * 1000.0
            h.at[i, "denominator_source"] = "crsp_dsf_prior_fallback"
        if drow is not None:
            h.at[i, "dsf_date"] = drow.date.strftime("%Y-%m-%d")
            h.at[i, "dsf_shrout"] = float(drow.shrout) * 1000.0 if pd.notna(drow.shrout) else np.nan
            h.at[i, "cfacshr"] = drow.cfacshr
    contrib = h[h.mapping_status.eq("exact_matched")].copy()
    contrib["denominator_complete"] = contrib.denominator_shares.notna() & contrib.denominator_shares.gt(0)
    # All included constituent series within a wave were selected on one common report date.
    date_counts = contrib.groupby("wave_id").pre_report_date.nunique()
    if (date_counts > 1).any():
        raise ValueError(f"mixed report dates need split adjustment: {date_counts.to_dict()}")
    grouped = contrib.groupby(["wave_id", "role", "effective_date", "announcement_cutoff", "pre_report_date", "permno", "crsp_ticker", "issuer_name_crsp", "siccd"], dropna=False, as_index=False).agg(
        raw_reported_shares=("raw_reported_shares", "sum"),
        position_value_usd=("position_value_usd", "sum"),
        n_positions=("position_number", "size"),
        n_predecessor_series=("pre_series_id", "nunique"),
        denominator_shares=("denominator_shares", "first"),
        denominator_complete=("denominator_complete", "all"),
        source_cusips=("cusip9", lambda x: ";".join(sorted(set(x)))),
    )
    grouped["exposure_ownership"] = grouped.raw_reported_shares / grouped.denominator_shares
    grouped["primary_ready"] = grouped.denominator_complete & grouped.exposure_ownership.notna() & grouped.exposure_ownership.gt(0)
    tiers = empirical_tiers(grouped[grouped.primary_ready].copy())
    # Prospective liquidity candidates, not a signed selection rule.
    liq = []
    for row in tiers.itertuples(index=False):
        dates, rows = didx.get(int(row.permno), ([], []))
        before = [r for r in rows if r.date < pd.Timestamp(row.announcement_cutoff)]
        window = before[-250:-20] if len(before) >= 21 else []
        vals = [float(r.prc) * float(r.vol) for r in window if pd.notna(r.prc) and pd.notna(r.vol) and r.prc > 0 and r.vol >= 0]
        liq.append({
            "wave_id": row.wave_id,
            "permno": int(row.permno),
            "liquidity_candidate_window": "trading_days_-250_to_-21_before_announcement_cutoff",
            "liquidity_candidate_metric": "median_abs_prc_times_volume",
            "liquidity_observations": len(vals),
            "median_dollar_volume_candidate": float(np.median(vals)) if vals else np.nan,
            "liquidity_rule_status": "DIAGNOSTIC_ONLY_ORIGINAL_PLAN_DID_NOT_FIX_METRIC_WINDOW_OR_TIEBREAK",
        })
    liq = pd.DataFrame(liq)
    tiers = tiers.merge(liq, on=["wave_id", "permno"], how="left", validate="one_to_one")
    h.to_parquet(HERE / "POSITION_MAPPING_AND_DENOMINATORS.parquet", index=False)
    grouped.to_csv(HERE / "PREANNOUNCEMENT_EXPOSURE_ALL.csv", index=False)
    tiers.to_csv(HERE / "PREANNOUNCEMENT_EXPOSURE_PROVISIONAL_TIERS.csv", index=False)
    receipt = {
        "status": "SCC_EXPOSURE_AND_DIAGNOSTIC_LIQUIDITY_COMPLETE",
        "post_quote_outcomes_read": False,
        "earnings_or_return_values_read": False,
        "w021_bond_included": False,
        "position_candidates": len(h),
        "exact_mapped_positions": int(h.mapping_status.eq("exact_matched").sum()),
        "unique_mapped_permnos": len(wanted),
        "exposure_rows": len(grouped),
        "primary_ready_positive_rows": int(grouped.primary_ready.sum()),
        "wave_counts": tiers.groupby(["wave_id", "provisional_tier"]).size().unstack(fill_value=0).to_dict(orient="index"),
        "liquidity_rule_signed": False,
        "input_hashes": {"holdings": sha256(HOLDINGS), "packages": sha256(PACKAGES), "stocknames": sha256(STOCKNAMES)},
        "daily_sources": daily_lineage,
        "share_sources": share_lineage,
    }
    for name in ["POSITION_IDENTIFIER_MAPPING.csv", "POSITION_MAPPING_AND_DENOMINATORS.parquet", "PREANNOUNCEMENT_EXPOSURE_ALL.csv", "PREANNOUNCEMENT_EXPOSURE_PROVISIONAL_TIERS.csv"]:
        receipt.setdefault("output_hashes", {})[name] = sha256(HERE / name)
    (HERE / "SCC_EXPOSURE_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({k: receipt[k] for k in ["status", "position_candidates", "exact_mapped_positions", "unique_mapped_permnos", "exposure_rows", "primary_ready_positive_rows", "wave_counts"]}, indent=2))


if __name__ == "__main__":
    main()
