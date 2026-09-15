#!/usr/bin/env python3
"""Build exact 8-PRE/4-POST companion inputs for the supported acquisition roster.

The script is intended to run on SCC.  Licensed actual/forecast values remain
there.  The exportable event manifest contains identifiers, dates, clocks, and
coverage flags only; it contains no EPS, forecast, price, return, or quote value.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


ROOT = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914")
RAW = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared/raw")
ROSTER = Path(os.environ.get("P1_ACQUISITION_ROSTER", ROOT / "supported_roster/PILOT_STOCKS_40_SUPPORTED.csv"))
LINK = RAW / "crsp_ibes_link_full.parquet"
OUT = Path(os.environ.get("P1_ACQUISITION_OUTPUT", ROOT / "supported_earnings_inputs"))
EXPECTED_ROSTER_SHA256 = os.environ.get(
    "P1_ACQUISITION_ROSTER_SHA256",
    "eeb3ab2f522fc611dc614aceed79b95c2e9ccb772fec11f6fa1db5d6c29323be",
)
EXPECTED_ROSTER_ROWS = int(os.environ.get("P1_ACQUISITION_ROSTER_ROWS", "40"))

SEARCH = {
    "W002": ("2019-01-01", "2022-12-31"),
    "W013": ("2020-01-01", "2024-03-31"),
    "W016": ("2020-01-01", "2024-09-30"),
    "W021": ("2020-01-01", "2024-12-31"),
    "W025": ("2020-01-01", "2024-12-31"),
}
POST_THRESHOLD = {
    "W002": "2021-07-13", "W013": "2022-11-29", "W016": "2023-04-11",
    "W021": "2023-08-28", "W025": "2023-12-19",
}

ACTUAL_COLUMNS = [
    "ticker", "cusip", "pends", "pdicity", "anndats", "anntims",
    "actdats", "acttims", "value", "curr_act", "usfirm",
]
FORECAST_COLUMNS = [
    "ticker", "cusip", "actdats", "estimator", "analys", "currfl",
    "pdf", "fpi", "measure", "value", "curr", "usfirm", "fpedats",
    "acttims", "revdats", "revtims", "anndats", "anntims", "report_curr",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def normalize_cusip(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.upper()


def main() -> None:
    if sha256(ROSTER) != EXPECTED_ROSTER_SHA256:
        raise ValueError("supported roster hash mismatch")
    if OUT.exists():
        raise FileExistsError(f"preserve existing output: {OUT}")
    OUT.mkdir(parents=True)

    roster = pd.read_csv(ROSTER)
    roster["permno"] = roster.permno.astype(int)
    if len(roster) != EXPECTED_ROSTER_ROWS or roster.wave_id.nunique() != 5:
        raise ValueError(f"expected {EXPECTED_ROSTER_ROWS} rows across five waves")
    permnos = set(roster.permno)

    links = pq.read_table(
        LINK,
        columns=["permno", "ncusip", "sdate", "edate", "score"],
        filters=[("permno", "in", sorted(permnos))],
    ).to_pandas()
    links = links[links.permno.isin(permnos)].copy()
    links["cusip"] = normalize_cusip(links.ncusip)
    links["sdate"] = pd.to_datetime(links.sdate)
    links["edate"] = pd.to_datetime(links.edate).fillna(pd.Timestamp("2099-12-31"))
    cusips = set(links.cusip.dropna())

    actual_parts = []
    actual_inputs = []
    for year in range(2019, 2025):
        path = RAW / f"ibes_actuals_eps_{year}.parquet"
        missing = [c for c in ACTUAL_COLUMNS if c not in pq.read_schema(path).names]
        if missing:
            raise ValueError(f"missing actual columns {path}: {missing}")
        frame = pd.read_parquet(path, columns=ACTUAL_COLUMNS)
        frame["cusip"] = normalize_cusip(frame.cusip)
        frame = frame[frame.cusip.isin(cusips)].copy()
        frame["source_partition"] = path.name
        actual_parts.append(frame)
        actual_inputs.append({"path": str(path), "sha256": sha256(path), "selected_rows": len(frame)})

    actuals = pd.concat(actual_parts, ignore_index=True)
    actuals["anndats"] = pd.to_datetime(actuals.anndats)
    actuals["pends"] = pd.to_datetime(actuals.pends)
    joined = actuals.merge(links, on="cusip", how="inner")
    joined = joined[
        (joined.sdate <= joined.anndats)
        & (joined.anndats <= joined.edate)
        & joined.pdicity.astype(str).str.upper().eq("QTR")
    ].copy()
    source_key = ["cusip", "pends", "anndats", "anntims"]
    joined["mapped_permnos"] = joined.groupby(source_key, dropna=False).permno.transform("nunique")

    candidates = []
    selected = []
    for row in roster.itertuples(index=False):
        lo, hi = SEARCH[row.wave_id]
        stock = joined[
            (joined.permno == row.permno)
            & joined.anndats.between(lo, hi)
        ].copy()
        period_rows = []
        for pends, group in stock.groupby("pends"):
            release_dates = sorted({d.strftime("%Y-%m-%d") for d in group.anndats.dropna()})
            release_times = sorted({str(v) for v in group.anntims.dropna()})
            release_date = release_dates[0] if len(release_dates) == 1 else None
            mapping_status = "UNAMBIGUOUS" if group.mapped_permnos.max() == 1 else "AMBIGUOUS"
            period_rows.append({
                "wave_id": row.wave_id,
                "permno": row.permno,
                "roster_ticker": row.historical_ticker,
                "tier": row.tier,
                "liquidity_stratum": row.liquidity_stratum,
                "pends": pends.strftime("%Y-%m-%d"),
                "announcement_date": release_date,
                "announcement_dates_all": ";".join(release_dates),
                "announcement_times_all": ";".join(release_times),
                "source_rows": len(group),
                "mapping_status": mapping_status,
                "announcement_cutoff": row.announcement_cutoff,
                "post_20_session_threshold": getattr(
                    row, "post_20_session_threshold", POST_THRESHOLD[row.wave_id]
                ),
            })
        periods = pd.DataFrame(period_rows)
        if periods.empty:
            raise ValueError(f"no quarterly metadata for {row.wave_id}/{row.permno}")
        candidates.append(periods)
        eligible = periods[
            periods.announcement_date.notna() & periods.mapping_status.eq("UNAMBIGUOUS")
        ].copy()
        eligible["announcement_date_dt"] = pd.to_datetime(eligible.announcement_date)
        pre = eligible[
            eligible.announcement_date_dt < pd.Timestamp(row.announcement_cutoff)
        ].sort_values(["announcement_date_dt", "pends"]).tail(8).copy()
        post = eligible[
            eligible.announcement_date_dt >= pd.Timestamp(
                getattr(row, "post_20_session_threshold", POST_THRESHOLD[row.wave_id])
            )
        ].sort_values(["announcement_date_dt", "pends"]).head(4).copy()
        if len(pre) != 8 or len(post) != 4:
            raise ValueError(f"support invariant failed {row.wave_id}/{row.permno}: {len(pre)}/{len(post)}")
        pre["sample_period"] = "PRE"
        post["sample_period"] = "POST"
        selected.extend([pre, post])

    all_candidates = pd.concat(candidates, ignore_index=True)
    chosen = pd.concat(selected, ignore_index=True)
    chosen = chosen.sort_values(["wave_id", "permno", "sample_period", "announcement_date", "pends"])
    chosen["association_id"] = chosen.apply(
        lambda r: f"{r.wave_id}_{int(r.permno)}_{r.sample_period}_{r.pends.replace('-', '')}", axis=1
    )
    expected_associations = EXPECTED_ROSTER_ROWS * 12
    if len(chosen) != expected_associations or chosen.association_id.nunique() != expected_associations:
        raise ValueError(f"expected {expected_associations} unique stock-period associations")

    # Attach a date-valid CRSP raw symbol for vendor request compilation.
    name_parts = []
    name_sources = [
        RAW / "rescue/newcrsp_crsp_a_stock_stocknames_v2_full.parquet",
        RAW / "rescue/newcrsp_crsp_stocknames_v2_full.parquet",
    ]
    for path in name_sources:
        required = ["permno", "ticker", "cusip", "namedt", "nameenddt"]
        if path.exists() and all(c in pq.read_schema(path).names for c in required):
            frame = pd.read_parquet(path, columns=required)
            frame = frame.rename(columns={"cusip": "ncusip", "nameenddt": "nameendt"})
            name_parts.append(frame[frame.permno.isin(permnos)])
    if not name_parts:
        raise FileNotFoundError("date-valid CRSP stocknames source not found")
    names = pd.concat(name_parts, ignore_index=True).drop_duplicates()
    names["namedt"] = pd.to_datetime(names.namedt)
    names["nameendt"] = pd.to_datetime(names.nameendt).fillna(pd.Timestamp("2099-12-31"))
    names["ncusip"] = normalize_cusip(names.ncusip)
    tmp = chosen.merge(names, on="permno", how="left")
    tmp["announcement_date_dt"] = pd.to_datetime(tmp.announcement_date)
    tmp = tmp[
        (tmp.namedt <= tmp.announcement_date_dt) & (tmp.announcement_date_dt <= tmp.nameendt)
    ].copy()
    symbol_counts = tmp.groupby("association_id", dropna=False).ticker.nunique(dropna=True)
    bad_symbols = set(symbol_counts[symbol_counts != 1].index)
    chosen = chosen.merge(
        tmp[~tmp.association_id.isin(bad_symbols)][["association_id", "ticker", "ncusip"]].drop_duplicates("association_id"),
        on="association_id",
        how="left",
    ).rename(columns={"ticker": "date_valid_raw_symbol", "ncusip": "date_valid_ncusip"})
    chosen["symbol_status"] = chosen.date_valid_raw_symbol.notna().map(
        {True: "DATE_VALID_UNIQUE", False: "MISSING_OR_AMBIGUOUS"}
    )

    # Keep licensed actual values only for the selected PERMNO/fiscal-period pairs.
    keys = chosen[["permno", "pends"]].copy()
    keys["pends"] = pd.to_datetime(keys.pends)
    actual_selected = joined.merge(keys.drop_duplicates(), on=["permno", "pends"], how="inner")
    actual_selected.to_parquet(OUT / "licensed_actuals_selected.parquet", index=False)

    release_lookup = {
        (int(r.permno), pd.Timestamp(r.pends)): pd.Timestamp(r.announcement_date)
        for r in chosen.itertuples(index=False)
    }
    selected_pends = set(pd.to_datetime(chosen.pends))
    forecast_parts = []
    forecast_inputs = []
    for year in range(2019, 2025):
        path = RAW / f"ibes_detu_eps_{year}.parquet"
        missing = [c for c in FORECAST_COLUMNS if c not in pq.read_schema(path).names]
        if missing:
            raise ValueError(f"missing forecast columns {path}: {missing}")
        frame = pd.read_parquet(path, columns=FORECAST_COLUMNS)
        frame["cusip"] = normalize_cusip(frame.cusip)
        frame["fpedats"] = pd.to_datetime(frame.fpedats)
        frame = frame[frame.cusip.isin(cusips) & frame.fpedats.isin(selected_pends)].copy()
        frame["source_partition"] = path.name
        forecast_parts.append(frame)
        forecast_inputs.append({"path": str(path), "sha256": sha256(path), "candidate_rows": len(frame)})
    forecasts = pd.concat(forecast_parts, ignore_index=True)
    forecasts["anndats"] = pd.to_datetime(forecasts.anndats)
    forecast_joined = forecasts.merge(links, on="cusip", how="inner")
    forecast_joined = forecast_joined[
        (forecast_joined.sdate <= forecast_joined.fpedats)
        & (forecast_joined.fpedats <= forecast_joined.edate)
        & forecast_joined.permno.isin(permnos)
    ].copy()
    forecast_joined["release_date"] = forecast_joined.apply(
        lambda r: release_lookup.get((int(r.permno), pd.Timestamp(r.fpedats))), axis=1
    )
    forecast_joined = forecast_joined[
        forecast_joined.release_date.notna()
        & (forecast_joined.anndats < forecast_joined.release_date)
        & (forecast_joined.anndats >= forecast_joined.release_date - pd.Timedelta(days=90))
    ].copy()
    forecast_joined.to_parquet(OUT / "licensed_forecasts_90d_selected.parquet", index=False)

    # Output-blind analyst counts are permitted coverage metadata.
    analyst = forecast_joined.groupby(["permno", "fpedats"]).analys.nunique().rename("analyst_count_90d")
    chosen["pends_dt"] = pd.to_datetime(chosen.pends)
    chosen = chosen.merge(
        analyst.reset_index(), left_on=["permno", "pends_dt"], right_on=["permno", "fpedats"], how="left"
    ).drop(columns=["fpedats", "pends_dt"])
    chosen["analyst_count_90d"] = chosen.analyst_count_90d.fillna(0).astype(int)
    chosen["sue_analyst_min2_coverage"] = chosen.analyst_count_90d.ge(2)
    export_columns = [
        "association_id", "wave_id", "permno", "roster_ticker", "date_valid_raw_symbol",
        "date_valid_ncusip", "symbol_status", "tier", "liquidity_stratum", "sample_period",
        "pends", "announcement_date", "announcement_times_all", "source_rows", "mapping_status",
        "announcement_cutoff", "post_20_session_threshold", "analyst_count_90d",
        "sue_analyst_min2_coverage",
    ]
    chosen[export_columns].to_csv(OUT / "selected_event_metadata.csv", index=False)
    all_candidates.to_csv(OUT / "all_quarterly_event_candidates_metadata.csv", index=False)

    counts = chosen.groupby(["wave_id", "sample_period"]).size().unstack(fill_value=0).reset_index()
    counts.to_csv(OUT / "event_counts_by_wave.csv", index=False)
    receipt = {
        "status": "SUPPORTED_EARNINGS_INPUTS_ACQUIRED_SCC_ONLY",
        "roster_sha256": sha256(ROSTER),
        "roster_rows": len(roster),
        "selected_event_associations": len(chosen),
        "selected_unique_stock_periods": chosen[["permno", "pends"]].drop_duplicates().shape[0],
        "pre_associations": int(chosen.sample_period.eq("PRE").sum()),
        "post_associations": int(chosen.sample_period.eq("POST").sum()),
        "unique_date_valid_symbols": int(chosen.date_valid_raw_symbol.nunique()),
        "symbol_failures": int(chosen.symbol_status.ne("DATE_VALID_UNIQUE").sum()),
        "associations_with_at_least_2_analysts": int(chosen.sue_analyst_min2_coverage.sum()),
        "selected_actual_source_rows": len(actual_selected),
        "forecast_rows_90d": len(forecast_joined),
        "event_metadata_sha256": sha256(OUT / "selected_event_metadata.csv"),
        "actuals_sha256": sha256(OUT / "licensed_actuals_selected.parquet"),
        "forecasts_sha256": sha256(OUT / "licensed_forecasts_90d_selected.parquet"),
        "actual_inputs": actual_inputs,
        "forecast_inputs": forecast_inputs,
        "financial_values_exported_from_scc": False,
        "price_quote_return_values_read": False,
        "post_treatment_effect_estimated": False,
    }
    (OUT / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
