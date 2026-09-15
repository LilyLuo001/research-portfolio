#!/usr/bin/env python3
"""Build outcome-blind necessary-support aggregates for the fixed P1 pilot."""

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--analyst", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    if args.out.exists():
        raise FileExistsError(args.out)

    metadata_header = pd.read_csv(args.metadata, nrows=0).columns
    key_column = (
        "accounting_period_date_key"
        if "accounting_period_date_key" in metadata_header
        else "event_key"
    )
    metadata = pd.read_csv(
        args.metadata,
        usecols=["candidate_id", "provisional_tier", "event_side", key_column],
    ).rename(columns={key_column: "event_key"}).drop_duplicates()
    analyst = pd.read_csv(
        args.analyst,
        usecols=["event_key", "scope", "family", "rule", "coverage_class"],
    ).drop_duplicates()
    analyst = analyst.loc[analyst["scope"].eq("W021")]

    joined = metadata.merge(analyst, on="event_key", how="inner", validate="many_to_many")
    grouped = (
        joined.groupby(
            ["provisional_tier", "event_side", "family", "rule", "coverage_class"],
            dropna=False,
        )
        .agg(event_keys=("event_key", "nunique"), stocks=("candidate_id", "nunique"))
        .reset_index()
        .sort_values(
            ["provisional_tier", "event_side", "family", "rule", "coverage_class"]
        )
    )

    args.out.mkdir(parents=True)
    output = args.out / "w021_analyst_support_by_tier_side.csv"
    grouped.to_csv(output, index=False)
    receipt = {
        "status": "COMPLETE",
        "purpose": "P1_NECESSARY_SUPPORT_EARLY_STOP_ONLY",
        "metadata_sha256": sha256(args.metadata),
        "analyst_sha256": sha256(args.analyst),
        "code_sha256": sha256(Path(__file__)),
        "output_sha256": sha256(output),
        "joined_event_keys": int(joined["event_key"].nunique()),
        "financial_values_read": False,
        "prices_or_returns_read": False,
        "row_level_exported": False,
    }
    (args.out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
