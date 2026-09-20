#!/usr/bin/env python3
"""Build the 2022-12-30 CRSP issuer roster and 2023 I/B/E/S event calendar.

Run only on SCC.  All row-level inputs and outputs remain on SCC.  The sole
portable product is `safe_summary.json`, which contains counts and provenance
but no security, company, ticker, earnings, forecast, quote, or return values.
"""
import json
import os
from pathlib import Path

import pandas as pd


ROOT = Path(os.environ.get(
    "P1_MIRROR_ROOT",
    "/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/"
    "p1_refraction_wrds_shared",
))
OUT = Path(os.environ.get(
    "P1_ROSTER_OUT",
    str(ROOT / "derived/p1_concentration_information/20260920/roster"),
))
RAW = ROOT / "raw"
RANK_DATE = "2022-12-30"  # CRSP's last observed US trading date in 2022.


def inclusive(d, start, end):
    return (start.isna() | (start <= d)) & (end.isna() | (end >= d))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    # Read only the ranking ingredients and the historical name interval needed
    # for the SHRCd 10/11 common-stock universe.  `prc` may be signed in CRSP.
    dsf = pd.read_parquet(
        RAW / "crsp_dsf_2022.parquet",
        columns=["permno", "permco", "date", "prc", "shrout"],
        filters=[("date", "==", RANK_DATE)],
    )
    names = pd.read_parquet(
        RAW / "crsp_dsenames_full.parquet",
        columns=["permno", "permco", "namedt", "nameendt", "shrcd"],
    )
    for frame, cols in [(dsf, ["date"]), (names, ["namedt", "nameendt"])]:
        for col in cols:
            frame[col] = pd.to_datetime(frame[col], errors="coerce")
    rank_day = pd.Timestamp(RANK_DATE)
    names = names[inclusive(rank_day, names.namedt, names.nameendt)]
    names = names[names.shrcd.isin([10, 11])]
    identical_active_name_rows_deduplicated = int(names.duplicated(["permno", "permco", "shrcd"]).sum())
    names = names.drop_duplicates(["permno", "permco", "shrcd"])
    # A security may have more than one active name row only if source records
    # overlap. Retain no such silent duplicate; diagnose and select no ranking
    # candidate in that case until it is resolved.
    name_counts = names.groupby("permno").size()
    overlapping_name_permnos = int((name_counts > 1).sum())
    names = names[names.permno.isin(name_counts[name_counts == 1].index)]
    duplicate_dsf_keys = int(dsf.duplicated(["permno", "permco", "date"]).sum())
    dsf = dsf.drop_duplicates(["permno", "permco", "date"], keep=False)
    stock = dsf.merge(names[["permno", "permco", "shrcd"]], on=["permno", "permco"], how="inner")
    stock["market_cap_usd"] = stock.prc.abs() * stock.shrout * 1000.0
    valid = stock.market_cap_usd.notna() & (stock.market_cap_usd > 0) & stock.permco.notna()
    invalid_or_nonpositive_market_cap_rows_excluded = int((~valid).sum())
    stock = stock.loc[valid].copy()
    issuer = (stock.groupby("permco", as_index=False, sort=False)
              .agg(market_cap_usd=("market_cap_usd", "sum"),
                   n_common_share_classes=("permno", "nunique"))
              .sort_values(["market_cap_usd", "permco"], ascending=[False, True])
              .reset_index(drop=True))
    issuer["issuer_rank"] = issuer.index + 1
    if len(issuer) < 500:
        raise RuntimeError("Fewer than 500 qualified issuer market caps; roster is invalid.")
    issuer_pool = issuer.iloc[:500].copy()
    stock_pool = stock.merge(issuer_pool[["permco", "issuer_rank"]], on="permco", how="inner")
    top8 = issuer_pool.iloc[:8].copy()
    top8_securities = stock_pool.merge(top8[["permco", "issuer_rank"]], on=["permco", "issuer_rank"], how="inner")

    # SCC-private CRSP-derived artifacts.  They deliberately are not copied to
    # the local workspace; this includes opaque identifiers and market caps.
    issuer_pool.to_parquet(OUT / "private_top500_permco_marketcap.parquet", index=False)
    stock_pool.to_parquet(OUT / "private_top500_common_shareclasses.parquet", index=False)
    top8[["issuer_rank", "permco", "market_cap_usd", "n_common_share_classes"]].to_parquet(
        OUT / "private_top8_permco_marketcap.parquet", index=False)
    top8_securities[["issuer_rank", "permco", "permno", "shrcd", "market_cap_usd"]].to_parquet(
        OUT / "private_top8_permno_permco.parquet", index=False)

    # Map 2023 EPS actual announcement metadata through the historical
    # CRSP-I/B/E/S link at the source announcement date, never through a
    # current ticker. Values and forecasts are intentionally not read.
    actual = pd.read_parquet(
        RAW / "ibes_actuals_eps_2023.parquet",
        columns=["ticker", "pends", "measure", "pdicity", "anndats", "anntims", "actdats", "acttims", "usfirm"],
    )
    links = pd.read_parquet(
        RAW / "crsp_ibes_link_full.parquet",
        columns=["ticker", "permno", "sdate", "edate", "score"],
    )
    permco_history = pd.read_parquet(
        RAW / "crsp_dsenames_full.parquet",
        columns=["permno", "permco", "namedt", "nameendt"],
    )
    for frame, cols in [(actual, ["anndats", "pends", "actdats"]),
                        (links, ["sdate", "edate"]),
                        (permco_history, ["namedt", "nameendt"])]:
        for col in cols:
            frame[col] = pd.to_datetime(frame[col], errors="coerce")
    actual = actual[actual.anndats.notna() & (actual.anndats.dt.year == 2023)].copy()
    actual["source_row_id"] = range(len(actual))
    linked = actual.merge(links, on="ticker", how="left", suffixes=("", "_link"))
    linked = linked[linked.permno.notna() & inclusive(linked.anndats, linked.sdate, linked.edate)].copy()
    linked = linked.merge(permco_history, on="permno", how="left")
    linked = linked[linked.permco.notna() & inclusive(linked.anndats, linked.namedt, linked.nameendt)].copy()
    # This is the ambiguity audit before source-company restriction: a single
    # I/B/E/S source row can map to more than one valid historical PERMNO or
    # PERMCO. It is reported, never silently resolved.
    global_mapping = linked.groupby("source_row_id").agg(
        valid_permno_alternatives=("permno", "nunique"),
        valid_permco_alternatives=("permco", "nunique"),
    )
    valid_source_ids = set(global_mapping.index)
    top8_permcos = set(top8.permco.astype("int64"))
    calendar_rows = linked[linked.permco.isin(top8_permcos)].copy()
    calendar_rows = calendar_rows.merge(top8[["permco", "issuer_rank"]], on="permco", how="left")
    # Preserve all source rows privately.  A unique event candidate is an
    # issuer/date/time/fiscal-period tuple; time is source metadata, not a
    # validated UTC timestamp.  Ambiguity is measured rather than resolved.
    calendar_rows["link_count_per_source_row"] = calendar_rows.groupby(
        "source_row_id", dropna=False
    )["permno"].transform("nunique")
    metadata_key = ["issuer_rank", "permco", "anndats", "anntims", "pends", "measure", "pdicity"]
    metadata_tuples = (calendar_rows[metadata_key]
              .drop_duplicates()
              .sort_values(["issuer_rank", "anndats", "anntims", "pends"], na_position="last"))
    release_groups = (metadata_tuples.groupby(["issuer_rank", "permco", "anndats", "anntims"], dropna=False,
                                      as_index=False)
                       .agg(source_metadata_tuples=("pends", "size"),
                            distinct_fiscal_periods=("pends", "nunique"),
                            has_quarterly_record=("pdicity", lambda x: bool((x == "QTR").any())),
                            has_annual_record=("pdicity", lambda x: bool((x == "ANN").any())))
                       .sort_values(["issuer_rank", "anndats", "anntims"], na_position="last"))
    calendar_rows.to_parquet(OUT / "private_2023_top8_ibes_mapped_source_rows.parquet", index=False)
    metadata_tuples.to_parquet(OUT / "private_2023_top8_earnings_source_metadata_tuples.parquet", index=False)
    release_groups.to_parquet(OUT / "private_2023_top8_earnings_release_group_candidates.parquet", index=False)

    summary = {
        "run_scope": "2022-12-30 PRE issuer ranking and 2023 I/B/E/S EPS announcement metadata only; no returns, quotes, EPS values, or forecasts read",
        "source_provenance": {
            "ranking": {
                "files": ["raw/crsp_dsf_2022.parquet", "raw/crsp_dsenames_full.parquet"],
                "unit": "security trading-date; aggregated to PERMCO issuer",
                "date": RANK_DATE,
                "market_cap_formula": "abs(prc) * shrout * 1000; CRSP shrout is thousands",
                "common_stock_rule": "active CRSP name history SHRCd in {10,11} at ranking date",
            },
            "calendar": {
                "files": ["raw/ibes_actuals_eps_2023.parquet", "raw/crsp_ibes_link_full.parquet", "raw/crsp_dsenames_full.parquet"],
                "unit": "I/B/E/S actuals source row; release-group candidate is an issuer/date/time tuple, preserving annual/quarterly source-record flags; it is not definitive earliest public-release evidence",
                "mapping": "I/B/E/S ticker joins only to historical CRSP-I/B/E/S link effective at anndats, then historical CRSP PERMNO-PERMCO name interval effective at anndats",
                "economic_date": "anndats (source announcement date)",
                "available_date": "not observed separately; anntims follows the archived W021 nominal Eastern/DST convention, while timestamp precision and earliest-public-release status remain UNKNOWN",
                "physical_partition_audit": "meta/ibes_actuals_eps_2023.sql.txt filters anndats >= 2023-01-01 and < 2024-01-01, usfirm=1, upper(measure)=EPS; this is an anndats partition, not a pends partition",
            },
        },
        "actual_counts": {
            "crsp_rows_at_rank_date_before_common_filter": int(len(dsf)),
            "active_common_security_rows_used": int(len(stock)),
            "active_common_permco_ranked": int(len(issuer)),
            "receiver_pool_permcos_top500": int(len(issuer_pool)),
            "receiver_pool_common_shareclass_rows": int(len(stock_pool)),
            "top8_permcos": int(len(top8)),
            "top8_common_shareclass_rows": int(len(top8_securities)),
            "overlapping_active_name_permnos_excluded": overlapping_name_permnos,
            "identical_active_name_rows_deduplicated": identical_active_name_rows_deduplicated,
            "duplicate_dsf_permno_permco_date_keys_excluded": duplicate_dsf_keys,
            "invalid_or_nonpositive_market_cap_rows_excluded": invalid_or_nonpositive_market_cap_rows_excluded,
            "ibes_2023_actual_rows_with_valid_anndats": int(len(actual)),
            "ibes_joined_rows_effective_link_and_permco_history": int(len(linked)),
            "ibes_source_rows_with_zero_valid_historical_mapping": int(len(actual) - len(valid_source_ids)),
            "ibes_source_rows_with_one_valid_historical_permno_mapping": int((global_mapping.valid_permno_alternatives == 1).sum()),
            "ibes_source_rows_with_multiple_valid_historical_permno_mappings": int((global_mapping.valid_permno_alternatives > 1).sum()),
            "top8_mapped_joined_rows": int(len(calendar_rows)),
            "top8_mapped_distinct_source_rows": int(calendar_rows.source_row_id.nunique()),
            "top8_distinct_source_metadata_tuples": int(len(metadata_tuples)),
            "top8_release_group_candidates_issuer_date_time": int(len(release_groups)),
            "top8_quarterly_source_metadata_tuples": int((metadata_tuples.pdicity == "QTR").sum()),
            "top8_annual_source_metadata_tuples": int((metadata_tuples.pdicity == "ANN").sum()),
            "top8_source_rows_with_multiple_permno_links": int((calendar_rows.link_count_per_source_row > 1).sum()) if len(calendar_rows) else 0,
            "all_2023_source_rows_with_multiple_valid_permno_alternatives": int((global_mapping.valid_permno_alternatives > 1).sum()),
            "all_2023_source_rows_with_multiple_valid_permco_alternatives": int((global_mapping.valid_permco_alternatives > 1).sum()),
            "top8_release_group_candidates_with_missing_anntims": int(release_groups.anntims.isna().sum()) if len(release_groups) else 0,
        },
        "scc_private_output_paths": [
            "private_top500_permco_marketcap.parquet",
            "private_top500_common_shareclasses.parquet",
            "private_top8_permco_marketcap.parquet",
            "private_top8_permno_permco.parquet",
            "private_2023_top8_ibes_mapped_source_rows.parquet",
            "private_2023_top8_earnings_source_metadata_tuples.parquet",
            "private_2023_top8_earnings_release_group_candidates.parquet",
        ],
        "unknowns_not_zero": [
            "I/B/E/S anntims follows the accepted nominal Eastern/DST convention, but its precision and whether it is the earliest public release timestamp remain UNKNOWN",
            "external IR evidence and release-time precision",
            "any event-source-row ambiguity not resolved by the historical link",
        ],
    }
    (OUT / "safe_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
