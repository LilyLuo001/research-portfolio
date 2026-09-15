"""Source-side aggregate only; never exports IBES row values."""
import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--projection-receipt", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError("Preserve prior aggregate receipt; choose a new output path")

    columns = ["cusip", "pends", "pdicity", "anndats", "anntims", "actdats", "acttims", "source_partition"]
    frame = pd.read_csv(args.metadata, usecols=columns, dtype="string")
    announced = pd.to_datetime(frame["anndats"], errors="coerce")
    announced_time = pd.to_datetime(frame["anntims"], format="%H:%M:%S", errors="coerce")
    period = frame[["cusip", "pends", "pdicity"]].fillna("<NULL>")
    source_key = frame[["cusip", "pends", "pdicity", "anndats", "anntims", "actdats", "acttims"]].fillna("<NULL>")
    repeated_source_rows = int(source_key.duplicated(keep=False).sum())
    duplicate_period_rows = int(period.duplicated(keep=False).sum())
    annual = frame.groupby("source_partition", dropna=False).size().sort_index()
    output = {
        "status": "METADATA_PROJECTED_ECONOMIC_EVENT_RULE_PENDING",
        "metadata_sha256": sha256(args.metadata),
        "projection_receipt_sha256": sha256(args.projection_receipt),
        "source_record_count": int(len(frame)),
        "candidate_cusips_with_source_records": int(frame["cusip"].nunique(dropna=True)),
        "announcement_date_parseable_records": int(announced.notna().sum()),
        "announcement_date_unparseable_or_missing_records": int(announced.isna().sum()),
        "announcement_time_parseable_records": int(announced_time.notna().sum()),
        "announcement_time_unparseable_or_missing_records": int(announced_time.isna().sum()),
        "records_in_exact_duplicate_source_key_groups": repeated_source_rows,
        "records_in_same_security_period_groups": duplicate_period_rows,
        "annual_partition_record_counts": {str(key): int(value) for key, value in annual.items()},
        "economic_event_count": None,
        "session_support": "NOT_ASSESSED_TIMEZONE_AND_CALENDAR_RULE_PENDING",
        "forbidden_value_fields_read_or_exported": False,
        "metadata_columns_read": columns,
    }
    args.output.write_text(json.dumps(output, indent=2) + "\n")


if __name__ == "__main__":
    main()
