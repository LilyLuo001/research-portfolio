#!/usr/bin/env python3
"""Fetch free Databento dataset-condition metadata for requested UTC dates.

This script never calls a billed time-series endpoint and never serializes the
API key.  It is intended to run only after the fixed-order download command
has returned in the already-authenticated shell.
"""

from __future__ import annotations

import csv
import json
import os
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import databento as db


HERE = Path(__file__).resolve().parent


def main() -> None:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise SystemExit("DATABENTO_API_KEY is not configured")

    with (HERE / "DOWNLOAD_MANIFEST.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))

    requested: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        requested[row["dataset"]].add(row["start"][:10])

    client = db.Historical(key)
    output = {
        "endpoint": "metadata.get_dataset_condition",
        "billing_class": "FREE_METADATA_ONLY",
        "datasets": {},
    }
    for dataset, dates in sorted(requested.items()):
        first = min(dates)
        last = max(dates)
        # The SDK documents end_date as inclusive.
        response = client.metadata.get_dataset_condition(
            dataset=dataset,
            start_date=first,
            end_date=last,
        )
        by_date = {
            str(item.get("date")): item
            for item in response
            if str(item.get("date")) in dates
        }
        output["datasets"][dataset] = {
            "requested_dates": sorted(dates),
            "conditions": [
                by_date.get(day, {"date": day, "condition": "NOT_RETURNED_UNKNOWN"})
                for day in sorted(dates)
            ],
        }

    (HERE / "DATASET_CONDITIONS.json").write_text(
        json.dumps(output, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {
                "datasets": len(output["datasets"]),
                "requested_dates": sum(
                    len(value["requested_dates"])
                    for value in output["datasets"].values()
                ),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
