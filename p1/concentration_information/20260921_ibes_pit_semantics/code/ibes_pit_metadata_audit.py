#!/usr/bin/env python3
"""Aggregate-only I/B/E/S PIT metadata audit; never reads financial value columns."""
import argparse
import json
from collections import Counter
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

NULL = "<MISSING>"


def clean(series):
    return series.astype("string").str.strip().str.upper().fillna(NULL)


def date_stats(frame, column):
    parsed = pd.to_datetime(frame[column], errors="coerce") if column in frame else pd.Series(dtype="datetime64[ns]")
    return {"missing_or_unparseable": int(parsed.isna().sum()), "parseable": int(parsed.notna().sum()),
            "min": None if parsed.notna().sum() == 0 else str(parsed.min().date()),
            "max": None if parsed.notna().sum() == 0 else str(parsed.max().date())}


def time_stats(frame, column):
    parsed = pd.to_datetime(frame[column], format="%H:%M:%S", errors="coerce") if column in frame else pd.Series(dtype="datetime64[ns]")
    return {"missing_or_unparseable": int(parsed.isna().sum()), "parseable": int(parsed.notna().sum())}


def category_counts(frame, fields):
    return {field: {str(key): int(value) for key, value in sorted(Counter(clean(frame[field])).items())}
            for field in fields if field in frame}


def order_counts(frame):
    announcement, activation = pd.to_datetime(frame["anndats"], errors="coerce"), pd.to_datetime(frame["actdats"], errors="coerce")
    comparable = announcement.notna() & activation.notna()
    ann_time = pd.to_datetime(frame["anntims"], format="%H:%M:%S", errors="coerce")
    act_time = pd.to_datetime(frame["acttims"], format="%H:%M:%S", errors="coerce")
    same = comparable & activation.eq(announcement)
    time_comparable = same & ann_time.notna() & act_time.notna()
    return {"activation_before_announcement_date": int((comparable & activation.lt(announcement)).sum()),
            "same_date_time_comparable": int(time_comparable.sum()),
            "same_date_activation_before_announcement_raw_time": int((time_comparable & act_time.lt(ann_time)).sum()),
            "same_date_activation_equal_announcement_raw_time": int((time_comparable & act_time.eq(ann_time)).sum()),
            "same_date_activation_after_announcement_raw_time": int((time_comparable & act_time.gt(ann_time)).sum()),
            "same_date_time_missing_or_unparseable": int((same & ~time_comparable).sum()),
            "activation_after_announcement_date": int((comparable & activation.gt(announcement)).sum()),
            "date_order_missing_or_unparseable": int((~comparable).sum())}


def duplicate_count(frame, keys):
    usable = frame[keys].fillna(NULL)
    return int(usable.duplicated(keep=False).sum())


def audit_frames(detail, actual, config):
    detail_fpi = set(config["sources"]["detail_candidate"]["quarterly_fpi_codes"])
    for frame in (detail, actual):
        for field in ["measure", "pdicity", "fpi"]:
            if field in frame:
                frame[field] = clean(frame[field])
        for field in ["ticker", "cusip", "estimator", "analys"]:
            if field in frame:
                frame[field] = frame[field].astype("string").str.strip()
    # Direct Detail's verified footer lacks pdicity: quarterly status is inferred only
    # from the documented quarterly FPI code set and is never fabricated as a field.
    detail_filtered = detail[detail["measure"].eq("EPS") & detail["fpi"].isin(detail_fpi)].copy()
    actual_filtered = actual[actual["measure"].eq("EPS") & actual["pdicity"].eq("QTR")].copy()
    identity = ["ticker", "measure"]
    detail_period = pd.to_datetime(detail_filtered["fpedats"], errors="coerce").astype("string")
    actual_period = pd.to_datetime(actual_filtered["pends"], errors="coerce").astype("string")
    actual_valid = actual_filtered.assign(_period=actual_period).dropna(subset=identity + ["_period"])
    actual_keys = actual_valid.groupby(identity + ["_period"], dropna=False).size()
    dkeys = detail_filtered.assign(_period=detail_period)[identity + ["_period"]]
    dvalid = dkeys.dropna(subset=identity + ["_period"])
    multiplicities = dvalid.apply(lambda row: int(actual_keys.get(tuple(row), 0)), axis=1)
    base = {"detail_period_identity_unmatchable_missing_identity_or_period_records": int(len(dkeys) - len(dvalid)),
            "detail_period_identity_unmatched_records": int(multiplicities.eq(0).sum()),
            "detail_period_identity_unique_actual_records": int(multiplicities.eq(1).sum()),
            "detail_period_identity_ambiguous_actual_records": int(multiplicities.gt(1).sum())}
    def source(frame, filtered, source_name, key, categories):
        return {"source": source_name, "physical_rows": None, "projected_rows": int(len(frame)), "filtered_rows": int(len(filtered)),
                "date": {"announcement": date_stats(filtered, "anndats"), "activation": date_stats(filtered, "actdats")},
                "time": {"announcement": time_stats(filtered, "anntims"), "activation": time_stats(filtered, "acttims")},
                "activation_vs_announcement_date_order": order_counts(filtered), "categories_before_filter": category_counts(frame, categories), "categories_filtered": category_counts(filtered, categories),
                "records_in_candidate_duplicate_key_groups": duplicate_count(filtered, key),
                "schema_currency_present": "curr" in frame.columns,
                "grain": "source records; candidate keys are metadata keys, NOT economic events"}
    result = {"detail_candidate": source(detail, detail_filtered, "detail_candidate", config["sources"]["detail_candidate"]["candidate_key"], ["measure", "pdicity", "fpi", "curr", "usfirm"]),
              "actual": source(actual, actual_filtered, "actual", config["sources"]["actual"]["actual_key"], ["measure", "pdicity", "fpi", "curr"]),
              "period_identity_match": base}
    return result


def load_source(raw_root, spec):
    path = Path(raw_root) / spec["file"]
    available = pq.ParquetFile(path).schema.names
    fields = [field for field in spec["projection_fields"] if field in available]
    return pd.read_parquet(path, columns=fields), pq.ParquetFile(path).metadata.num_row_groups, available


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--raw-root", type=Path)
    parser.add_argument("--private-output", type=Path, required=True)
    parser.add_argument("--private-projections", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    root = args.raw_root or Path(config["raw_root"])
    detail, detail_row_groups, detail_schema = load_source(root, config["sources"]["detail_candidate"])
    actual, actual_row_groups, actual_schema = load_source(root, config["sources"]["actual"])
    result = audit_frames(detail, actual, config)
    for name, spec, schema, groups in [("detail_candidate", config["sources"]["detail_candidate"], detail_schema, detail_row_groups), ("actual", config["sources"]["actual"], actual_schema, actual_row_groups)]:
        result[name]["physical_rows"] = int(pq.ParquetFile(root / spec["file"]).metadata.num_rows)
        result[name]["parquet_row_groups"] = groups
        result[name]["projected_fields_present"] = [field for field in spec["projection_fields"] if field in schema]
        result[name]["projected_fields_missing"] = [field for field in spec["projection_fields"] if field not in schema]
    result["audit_scope"] = {"financial_value_columns_read": False, "select_star_used": False, "year_partitions": config["boundaries"]["year_partitions"], "nominal_clock_note": config["boundaries"]["same_day_time_rule"]}
    args.private_output.parent.mkdir(parents=True, exist_ok=True)
    args.private_output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    # SCC-private whitelist projection supports count reproduction; it contains no values.
    args.private_projections.parent.mkdir(parents=True, exist_ok=True)
    pd.concat([detail.assign(_source="detail_candidate"), actual.assign(_source="actual")], ignore_index=True, sort=False).to_parquet(args.private_projections, index=False)


if __name__ == "__main__":
    main()
