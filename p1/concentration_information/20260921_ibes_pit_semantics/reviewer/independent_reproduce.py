#!/usr/bin/env python3
"""Independent, metadata-only reproduction for the 2023 I/B/E/S PIT audit.

This program reads only the SCC-private whitelist projection produced by the
engineering audit. It refuses unexpected columns and emits aggregate counts;
it never emits row data or reads forecast/actual values, prices, or returns.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


QUARTERLY_FPI = frozenset({"6", "7", "8", "9", "N", "O", "P", "Q", "R", "S", "T", "L", "Y"})
ALLOWED_COLUMNS = frozenset(
    {
        "ticker",
        "cusip",
        "analys",
        "estimator",
        "fpedats",
        "fpi",
        "pdicity",
        "measure",
        "usfirm",
        "curr",
        "anndats",
        "anntims",
        "actdats",
        "acttims",
        "pends",
        "_source",
    }
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def norm(series: pd.Series) -> pd.Series:
    """Upper-case/trim metadata and make both null and blank invalid."""
    out = series.astype("string").str.strip().str.upper()
    return out.mask(out.eq(""))


def parsed_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.normalize()


def parsed_time(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, format="%H:%M:%S", errors="coerce")


def date_summary(series: pd.Series) -> dict[str, object]:
    dates = parsed_date(series)
    return {
        "parseable": int(dates.notna().sum()),
        "missing_or_unparseable": int(dates.isna().sum()),
        "min": None if dates.notna().sum() == 0 else str(dates.min().date()),
        "max": None if dates.notna().sum() == 0 else str(dates.max().date()),
    }


def clock_summary(frame: pd.DataFrame) -> dict[str, int]:
    ann_date = parsed_date(frame["anndats"])
    act_date = parsed_date(frame["actdats"])
    ann_time = parsed_time(frame["anntims"])
    act_time = parsed_time(frame["acttims"])
    date_ok = ann_date.notna() & act_date.notna()
    same_day = date_ok & ann_date.eq(act_date)
    time_ok = same_day & ann_time.notna() & act_time.notna()
    return {
        "activation_before_date": int((date_ok & act_date.lt(ann_date)).sum()),
        "same_date_time_comparable": int(time_ok.sum()),
        "same_date_activation_before_announcement_raw_time": int((time_ok & act_time.lt(ann_time)).sum()),
        "same_date_activation_equal_announcement_raw_time": int((time_ok & act_time.eq(ann_time)).sum()),
        "same_date_activation_after_announcement_raw_time": int((time_ok & act_time.gt(ann_time)).sum()),
        "same_date_time_missing_or_unparseable": int((same_day & ~time_ok).sum()),
        "activation_after_date": int((date_ok & act_date.gt(ann_date)).sum()),
        "date_order_missing_or_unparseable": int((~date_ok).sum()),
    }


def frequency(series: pd.Series) -> dict[str, int]:
    normalized = norm(series).fillna("<MISSING>")
    return {str(k): int(v) for k, v in sorted(Counter(normalized).items())}


def duplicate_records(frame: pd.DataFrame, keys: list[str]) -> int:
    work = frame[keys].copy()
    for column in keys:
        if column in {"ticker", "measure", "fpi", "pdicity", "estimator", "analys"}:
            work[column] = norm(work[column])
    return int(work.duplicated(keep=False).sum())


def source_summary(frame: pd.DataFrame) -> dict[str, object]:
    activation = parsed_date(frame["actdats"])
    return {
        "rows": int(len(frame)),
        "announcement": date_summary(frame["anndats"]),
        "activation": date_summary(frame["actdats"]),
        "activation_vs_announcement": clock_summary(frame),
        "activation_after_2023": int(activation.gt(pd.Timestamp("2023-12-31")).sum()),
        "activation_after_2023_min": (
            None if not activation.gt(pd.Timestamp("2023-12-31")).any()
            else str(activation[activation.gt(pd.Timestamp("2023-12-31"))].min().date())
        ),
        "activation_after_2023_max": (
            None if not activation.gt(pd.Timestamp("2023-12-31")).any()
            else str(activation[activation.gt(pd.Timestamp("2023-12-31"))].max().date())
        ),
        "currency": frequency(frame["curr"]),
    }


def audit_projection(frame: pd.DataFrame) -> dict[str, object]:
    columns = set(frame.columns)
    unexpected = sorted(columns - ALLOWED_COLUMNS)
    required = {"_source", "ticker", "measure", "fpedats", "pends", "fpi", "pdicity", "curr", "anndats", "anntims", "actdats", "acttims"}
    missing = sorted(required - columns)
    if unexpected or missing:
        raise ValueError(f"projection schema refused: unexpected={unexpected}, missing={missing}")

    source = norm(frame["_source"])
    detail = frame.loc[source.eq("DETAIL_CANDIDATE")].copy()
    actual = frame.loc[source.eq("ACTUAL")].copy()
    if len(detail) + len(actual) != len(frame):
        raise ValueError("projection contains unknown or blank _source rows")

    detail_measure = norm(detail["measure"])
    actual_measure = norm(actual["measure"])
    detail_fpi = norm(detail["fpi"])
    actual_pdicity = norm(actual["pdicity"])
    d = detail.loc[detail_measure.eq("EPS") & detail_fpi.isin(QUARTERLY_FPI)].copy()
    a = actual.loc[actual_measure.eq("EPS") & actual_pdicity.eq("QTR")].copy()

    d_ticker, a_ticker = norm(d["ticker"]), norm(a["ticker"])
    d_measure, a_measure = norm(d["measure"]), norm(a["measure"])
    d_period, a_period = parsed_date(d["fpedats"]), parsed_date(a["pends"])
    d_key = pd.DataFrame({"ticker": d_ticker, "measure": d_measure, "period": d_period}, index=d.index)
    a_key = pd.DataFrame({"ticker": a_ticker, "measure": a_measure, "period": a_period}, index=a.index)
    d_valid_mask = d_key.notna().all(axis=1)
    a_valid_mask = a_key.notna().all(axis=1)
    actual_counts = a_key.loc[a_valid_mask].groupby(["ticker", "measure", "period"], dropna=False).size()
    multiplicity = d_key.loc[d_valid_mask].apply(lambda row: int(actual_counts.get(tuple(row), 0)), axis=1)

    detail_keys = ["ticker", "estimator", "analys", "fpedats", "fpi", "measure", "anndats", "anntims", "actdats", "acttims"]
    actual_keys = ["ticker", "pends", "measure", "pdicity", "anndats", "anntims", "actdats", "acttims"]

    return {
        "projection_rows": int(len(frame)),
        "quarterly_fpi_codes": sorted(QUARTERLY_FPI),
        "detail_candidate": {
            "all_projection": source_summary(detail),
            "filtered": source_summary(d),
            "filtered_rows": int(len(d)),
            "fpi_before_filter": frequency(detail["fpi"]),
            "fpi_filtered": frequency(d["fpi"]),
            "candidate_duplicate_key_group_records": duplicate_records(d, detail_keys),
            "invalid_blank_or_null_ticker": int(norm(d["ticker"]).isna().sum()),
            "invalid_period": int(parsed_date(d["fpedats"]).isna().sum()),
        },
        "actual": {
            "all_projection": source_summary(actual),
            "filtered": source_summary(a),
            "filtered_rows": int(len(a)),
            "pdicity_before_filter": frequency(actual["pdicity"]),
            "actual_duplicate_key_group_records": duplicate_records(a, actual_keys),
            "invalid_blank_or_null_ticker": int(norm(a["ticker"]).isna().sum()),
            "invalid_period": int(parsed_date(a["pends"]).isna().sum()),
            "period_identity_keys_with_multiple_actual_records": int((actual_counts > 1).sum()),
        },
        "period_identity_match": {
            "detail_period_identity_unmatchable_missing_or_blank_identity_or_period_records": int((~d_valid_mask).sum()),
            "detail_period_identity_unmatched_records": int(multiplicity.eq(0).sum()),
            "detail_period_identity_unique_actual_records": int(multiplicity.eq(1).sum()),
            "detail_period_identity_ambiguous_actual_records": int(multiplicity.gt(1).sum()),
        },
        "scope": {
            "financial_value_columns_read": False,
            "prices_returns_outcomes_read": False,
            "licensed_rows_emitted": False,
            "source_record_unit": True,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--projection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    schema = pq.ParquetFile(args.projection).schema.names
    unexpected = sorted(set(schema) - ALLOWED_COLUMNS)
    if unexpected:
        raise SystemExit(f"Refusing unexpected projection columns: {unexpected}")
    frame = pd.read_parquet(args.projection, columns=schema)
    result = audit_projection(frame)
    result["projection_sha256"] = sha256(args.projection)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
