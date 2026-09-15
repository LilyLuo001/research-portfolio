#!/usr/bin/env python3
"""Group same-window single-symbol requests into economical API jobs."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path


ROOT = Path(
    os.environ.get(
        "P1_DATABENTO_OUTPUT",
        Path(__file__).resolve().parent / "databento_acquisition",
    )
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(name: str) -> list[dict]:
    with (ROOT / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write(name: str, rows: list[dict]) -> None:
    with (ROOT / name).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def grouped(rows: list[dict], prefix: str) -> tuple[list[dict], list[dict]]:
    buckets = defaultdict(list)
    for row in rows:
        key = (
            row["bundle"], row["dataset"], row["schema"], row["stype_in"], row["start"], row["end"],
            row["local_date"], row["local_start"], row["local_end"], row["timezone"],
            row["analysis_access"], row["clock_basis"],
        )
        buckets[key].append(row)
    jobs = []
    mapping = []
    for number, (key, members) in enumerate(sorted(buckets.items(), key=lambda x: (x[0][6], x[0][1], x[0][7])), 1):
        bundle, dataset, schema, stype, start, end, local_date, local_start, local_end, tz, access, clock_basis = key
        symbols = sorted({m["symbols"] for m in members})
        job_id = f"{prefix}_{number:05d}"
        jobs.append({
            "job_id": job_id,
            "bundle": bundle,
            "dataset": dataset,
            "schema": schema,
            "symbols": ";".join(symbols),
            "symbol_count": len(symbols),
            "stype_in": stype,
            "start": start,
            "end": end,
            "local_date": local_date,
            "local_start": local_start,
            "local_end": local_end,
            "timezone": tz,
            "analysis_access": access,
            "clock_basis": clock_basis,
            "atomic_request_count": len(members),
        })
        for member in members:
            mapping.append({
                "job_id": job_id,
                "atomic_request_id": member["request_id"],
                "symbol": member["symbols"],
                "bundle": bundle,
            })
    return jobs, mapping


def main() -> None:
    core, core_map = grouped(load("core_xnas_bbo1s_requests.csv"), "COREJOB")
    alt, alt_map = grouped(load("alternative_single_venue_requests.csv"), "ALTJOB")
    write("core_grouped_jobs.csv", core)
    write("core_grouped_job_map.csv", core_map)
    write("alternative_grouped_jobs.csv", alt)
    write("alternative_grouped_job_map.csv", alt_map)
    receipt = {
        "status": "GROUPED_REQUESTS_COMPILED",
        "core_atomic_requests": len(core_map),
        "core_grouped_jobs": len(core),
        "alternative_atomic_requests": len(alt_map),
        "alternative_grouped_jobs": len(alt),
        "output_hashes": {
            name: sha256(ROOT / name)
            for name in [
                "core_grouped_jobs.csv", "core_grouped_job_map.csv",
                "alternative_grouped_jobs.csv", "alternative_grouped_job_map.csv",
            ]
        },
    }
    (ROOT / "grouping_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
