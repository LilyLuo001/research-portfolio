#!/usr/bin/env python3
"""Outcome-blind manifest overlap census for the SCC-private P1 source roster.

This reads Databento download-manifest metadata only. It never opens a DBN
file, price, quote, return, EPS value, or forecast. Row-level identifier and
symbol mappings stay under the SCC roster output root.
"""
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(os.environ.get("P1_MIRROR_ROOT", "/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902/p1_refraction_wrds_shared"))
OUT = Path(os.environ.get("P1_ROSTER_OUT", str(ROOT / "derived/p1_concentration_information/20260920/roster")))
MANIFEST = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914/databento_final_native/control/download_manifest.csv")
NY = ZoneInfo("America/New_York")


def valid_on(frame, date, start, end):
    return (frame[start].isna() | (frame[start] <= date)) & (frame[end].isna() | (frame[end] >= date))


def parse_symbols(value):
    """The native manifest stores explicit semicolon-delimited symbols."""
    if pd.isna(value):
        return []
    return [part.strip().upper() for part in str(value).split(";") if part.strip()]


def union_seconds(intervals, left, right):
    clipped = sorted((max(a, left), min(b, right)) for a, b in intervals if b > left and a < right)
    total, merged_end = 0.0, None
    for a, b in clipped:
        if merged_end is None:
            merged_end, begin = b, a
        elif a > merged_end:
            total += (merged_end - begin).total_seconds()
            begin, merged_end = a, b
        else:
            merged_end = max(merged_end, b)
    if merged_end is not None:
        total += (merged_end - begin).total_seconds()
    return total


def nominal_bucket(value):
    if pd.isna(value):
        return "UNKNOWN_TIME"
    t = str(value).strip()[:8]
    if t < "09:30:00":
        return "PRE_OPEN_COARSE"
    if t < "16:00:00":
        return "RTH_COARSE"
    return "AFTER_CLOSE_COARSE"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    groups = pd.read_parquet(OUT / "private_2023_top8_earnings_release_group_candidates.parquet")
    mapped = pd.read_parquet(OUT / "private_2023_top8_ibes_mapped_source_rows.parquet")
    names = pd.read_parquet(ROOT / "raw/crsp_dsenames_full.parquet",
                            columns=["permno", "permco", "ticker", "namedt", "nameendt", "shrcd"])
    for f, cols in [(groups, ["anndats"]), (mapped, ["anndats"]), (names, ["namedt", "nameendt"])]:
        for col in cols:
            f[col] = pd.to_datetime(f[col], errors="coerce")
    groups = groups.reset_index(names="release_group_id")
    source = mapped.merge(groups[["release_group_id", "issuer_rank", "permco", "anndats", "anntims"]],
                          on=["issuer_rank", "permco", "anndats", "anntims"], how="inner")
    security = source[["release_group_id", "source_row_id", "issuer_rank", "permco", "permno", "anndats", "anntims"]].drop_duplicates()
    sec_names = security.merge(names, on=["permno", "permco"], how="left")
    sec_names = sec_names[valid_on(sec_names, sec_names.anndats, "namedt", "nameendt")].copy()
    sec_names["historical_symbol"] = sec_names.ticker.str.upper().str.strip()
    sec_names = sec_names[sec_names.historical_symbol.notna() & (sec_names.historical_symbol != "")]
    # Preserve every valid security/symbol candidate. There is deliberately no
    # current-ticker fallback and no attempt to force a single share class.
    class_counts = sec_names.groupby("release_group_id").agg(
        valid_permno_candidates=("permno", "nunique"), valid_symbol_candidates=("historical_symbol", "nunique")
    )

    manifest = pd.read_csv(MANIFEST)
    manifest["start"] = pd.to_datetime(manifest.start, utc=True, errors="coerce")
    manifest["end"] = pd.to_datetime(manifest.end, utc=True, errors="coerce")
    manifest = manifest[manifest.start.notna() & manifest.end.notna()].copy()
    manifest["venue"] = manifest.dataset.str.split(".", regex=False).str[0]
    manifest["symbols_list"] = manifest.symbols.map(parse_symbols)
    manifest = manifest.explode("symbols_list").rename(columns={"symbols_list": "historical_symbol"})
    manifest = manifest[manifest.historical_symbol.notna() & (manifest.historical_symbol != "")].copy()
    manifest["historical_symbol"] = manifest.historical_symbol.astype(str).str.upper()
    # All states are metadata claims only; no DBN body validity is inferred.
    security["anndats"] = pd.to_datetime(security.anndats)
    sec_names["anndats"] = pd.to_datetime(sec_names.anndats)
    candidates = sec_names.merge(manifest[["venue", "historical_symbol", "start", "end", "completion_status", "analysis_access"]],
                                 on="historical_symbol", how="left")
    def clock(row):
        if pd.isna(row.anntims):
            return pd.NaT
        try:
            return pd.Timestamp(f"{row.anndats.date()} {str(row.anntims).strip()}").tz_localize(NY).tz_convert("UTC")
        except (TypeError, ValueError):
            return pd.NaT
    groups["candidate_clock_utc"] = groups.apply(clock, axis=1)
    groups["session_bucket"] = groups.anntims.map(nominal_bucket)
    interval_map = groups.set_index("release_group_id")["candidate_clock_utc"].to_dict()
    candidates["candidate_clock_utc"] = candidates.release_group_id.map(interval_map)
    candidates["window_start_utc"] = candidates.candidate_clock_utc - pd.Timedelta(minutes=15)
    candidates["window_end_utc"] = candidates.candidate_clock_utc + pd.Timedelta(minutes=75)
    candidates["manifest_date_et"] = candidates.start.dt.tz_convert(NY).dt.date
    candidates["announcement_date"] = candidates.anndats.dt.date
    candidates["nominal_date_intersection"] = candidates.manifest_date_et == candidates.announcement_date
    candidates["interval_overlap"] = (candidates.start < candidates.window_end_utc) & (candidates.end > candidates.window_start_utc)
    matched = candidates[candidates.venue.notna()].copy()
    rows = []
    for keys, g in matched.groupby(["release_group_id", "permno", "historical_symbol", "venue"], dropna=False):
        clock_value = g.candidate_clock_utc.iloc[0]
        if pd.isna(clock_value):
            seconds = None
        else:
            seconds = union_seconds(zip(g.start, g.end), clock_value - pd.Timedelta(minutes=15), clock_value + pd.Timedelta(minutes=75))
        rows.append((*keys, bool(g.nominal_date_intersection.any()), seconds,
                     int(g.interval_overlap.sum()), int(len(g)),
                     ";".join(sorted(g.completion_status.dropna().unique()))))
    coverage = pd.DataFrame(rows, columns=["release_group_id", "permno", "historical_symbol", "venue", "nominal_date_intersection", "interval_union_seconds", "overlapping_manifest_rows", "matching_manifest_rows", "manifest_statuses"])
    coverage = coverage.merge(groups[["release_group_id", "issuer_rank", "permco", "anndats", "anntims", "session_bucket"]], on="release_group_id", how="left")
    sec_names.to_parquet(OUT / "private_2023_top8_release_security_historical_symbol_candidates.parquet", index=False)
    coverage.to_parquet(OUT / "private_2023_top8_manifest_overlap_by_venue.parquet", index=False)

    # Comparator identities use the same date-effective CRSP name history, not
    # today's ticker mapping. A manifest symbol/date appearance is diagnostic,
    # never proof of quote-body completeness.
    comparators = names[names.ticker.str.upper().isin(["SPY", "QQQ"])].copy()
    comparator_rows = []
    for label in ["SPY", "QQQ"]:
        active = groups.assign(_k=1).merge(comparators[comparators.ticker.str.upper() == label].assign(_k=1), on="_k", how="left")
        active = active[valid_on(active, active.anndats, "namedt", "nameendt")]
        active["historical_symbol"] = active.ticker.str.upper()
        c = active.merge(manifest[["venue", "historical_symbol", "start", "end"]], on="historical_symbol", how="left")
        comparator_rows.append({"comparator": label, "release_groups_with_historical_identity": int(active.release_group_id.nunique()),
                                "release_groups_with_manifest_symbol_match": int(c.loc[c.venue.notna(), "release_group_id"].nunique()),
                                "venue_count_with_manifest_symbol_match": int(c.loc[c.venue.notna(), "venue"].nunique())})
    comparator_summary = pd.DataFrame(comparator_rows)
    comparator_summary.to_parquet(OUT / "private_2023_comparator_identity_manifest_summary.parquet", index=False)

    coverage_events = coverage.groupby("venue").agg(
        release_groups_with_symbol_match=("release_group_id", "nunique"),
        security_symbol_candidates_with_match=("historical_symbol", "size"),
        release_groups_date_intersection=("nominal_date_intersection", lambda x: int(coverage.loc[x.index][coverage.loc[x.index, "nominal_date_intersection"]].release_group_id.nunique())),
        positive_interval_union_candidates=("interval_union_seconds", lambda x: int((x > 0).sum())),
        total_interval_union_seconds=("interval_union_seconds", "sum"),
    ).reset_index()
    summary = {
        "scope": "outcome-blind Databento manifest metadata census; no DBN, price, quote, return, EPS-value, or forecast data read",
        "manifest": {"path": str(MANIFEST), "symbol_syntax": "semicolon-delimited explicit symbols", "body_validity": "UNKNOWN; manifest completion status is not treated as payload validation"},
        "candidate_clock": {"convention": "anntims interpreted under accepted nominal America/New_York ET/DST convention", "window": "[-15,+75] minutes", "earliest_public_release": "UNKNOWN"},
        "session": {"method": "coarse nominal clock buckets only; no archived verified 2023 trading calendar located", "certified": False,
                    "counts": groups.session_bucket.value_counts().to_dict()},
        "actual_counts": {
            "release_group_candidates": int(len(groups)), "historical_security_symbol_candidate_rows": int(len(sec_names)),
            "release_groups_with_multiple_permno_candidates": int((class_counts.valid_permno_candidates > 1).sum()),
            "release_groups_with_multiple_historical_symbol_candidates": int((class_counts.valid_symbol_candidates > 1).sum()),
            "release_groups_with_any_manifest_symbol_match": int(coverage.release_group_id.nunique()) if len(coverage) else 0,
            "manifest_venues_with_any_match": int(coverage.venue.nunique()) if len(coverage) else 0,
        },
        "venue_summary": coverage_events.to_dict(orient="records"),
        "comparators": comparator_summary.to_dict(orient="records"),
        "scc_private_output_paths": ["private_2023_top8_release_security_historical_symbol_candidates.parquet", "private_2023_top8_manifest_overlap_by_venue.parquet", "private_2023_comparator_identity_manifest_summary.parquet"],
    }
    (OUT / "safe_manifest_overlap_summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")


if __name__ == "__main__":
    main()
