#!/usr/bin/env python3
"""Resume the frozen P1 acquisition directly on SCC.

The API key is accepted only from DATABENTO_API_KEY.  This worker never
serializes, prints, or hashes it.  Previously submitted job IDs are skipped,
including uncertain streams, so a restart cannot blindly incur duplicate
streaming charges.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
import warnings
from collections import deque
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from decimal import Decimal
from pathlib import Path

import databento as db


CONTROL = Path(os.environ.get(
    "P1_DATABENTO_CONTROL",
    "/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914/databento_final_native/control",
))
ARCHIVE = Path(os.environ.get(
    "P1_DATABENTO_ARCHIVE",
    "/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914/databento_final_native",
))
CAP = Decimal("123.00")
MAX_WORKERS = 4
MAX_CONSECUTIVE_ERRORS = 3
FIELDS = [
    "job_id", "bundle", "dataset", "schema", "symbols", "start", "end",
    "analysis_access", "quoted_cost_usd", "reserved_cumulative_usd", "path",
    "local_staging_path", "bytes", "sha256", "error_type",
    "completion_status", "warning_count", "warning_types",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def atomic_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", newline="", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        tmp = Path(handle.name)
    tmp.replace(path)


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False
    ) as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        tmp = Path(handle.name)
    tmp.replace(path)


def download_one(job: dict, row: dict) -> tuple[dict, list[str]]:
    client = db.Historical(key=os.environ["DATABENTO_API_KEY"])
    path = Path(row["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    caught: list[str] = []
    try:
        with warnings.catch_warnings(record=True) as seen:
            warnings.simplefilter("always")
            client.timeseries.get_range(
                dataset=job["dataset"],
                start=job["start"],
                end=job["end"],
                symbols=job["symbols"].split(";"),
                schema=job["schema"],
                stype_in=job["stype_in"],
                stype_out="instrument_id",
                path=path,
            )
            caught = sorted({f"{type(w.message).__name__}:{w.message}" for w in seen})
        if not path.exists() or path.stat().st_size == 0:
            raise RuntimeError("download returned without a nonempty DBN file")
        row["bytes"] = str(path.stat().st_size)
        row["completion_status"] = "DOWNLOADED_NATIVE_DBN_ON_SCC_UNVERIFIED"
    except Exception as exc:
        row["error_type"] = type(exc).__name__
        row["completion_status"] = "UNCERTAIN_OR_PARTIAL_STOPPED_NO_RETRY"
    row["warning_count"] = str(len(caught))
    row["warning_types"] = " | ".join(caught)
    return row, caught


def main() -> None:
    if not os.environ.get("DATABENTO_API_KEY"):
        raise RuntimeError("DATABENTO_API_KEY absent; no market-data call made")

    grouping = json.loads((CONTROL / "grouping_receipt.json").read_text())
    for name, digest in grouping["output_hashes"].items():
        if sha256(CONTROL / name) != digest:
            raise RuntimeError(f"grouped manifest hash mismatch: {name}")
    quote_path = CONTROL / "quote_jobs.csv"
    selection = json.loads((CONTROL / "selection_receipt.json").read_text())
    if selection["quote_jobs_sha256"] != sha256(quote_path):
        raise RuntimeError("quote receipt hash mismatch")
    if Decimal(selection["gross_estimated_usage_usd"]) > CAP:
        raise RuntimeError("frozen selection exceeds hard cap")

    jobs = read_csv(CONTROL / "core_grouped_jobs.csv") + read_csv(CONTROL / "alternative_grouped_jobs.csv")
    quotes = {r["job_id"]: r for r in read_csv(quote_path)}
    selected = set(selection["selected_job_ids"])
    jobs = [j for j in jobs if j["job_id"] in selected]
    if any(quotes[j["job_id"]]["status"] != "OK" for j in jobs):
        raise RuntimeError("selected job lacks exact successful quote")

    manifest_path = CONTROL / "download_manifest.csv"
    manifest = read_csv(manifest_path)
    for row in manifest:
        row.setdefault("warning_count", "")
        row.setdefault("warning_types", "")
    ids = [r["job_id"] for r in manifest]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate job ID in prior manifest")
    submitted = set(ids)
    reserved = sum((Decimal(quotes[j]["cost_usd"]) for j in submitted), Decimal("0"))
    remaining = [j for j in jobs if j["job_id"] not in submitted]

    in_flight = {}
    consecutive_errors = 0
    completed_this_run = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        while remaining or in_flight:
            while remaining and len(in_flight) < MAX_WORKERS and consecutive_errors < MAX_CONSECUTIVE_ERRORS:
                job = remaining.pop(0)
                quoted = Decimal(quotes[job["job_id"]]["cost_usd"])
                if reserved + quoted > Decimal(selection["gross_estimated_usage_usd"]) or reserved + quoted > CAP:
                    raise RuntimeError("reservation cap breach")
                reserved += quoted
                access = "sealed_post" if job["analysis_access"].startswith("ARCHIVE") else "pre_development"
                path = ARCHIVE / job["bundle"] / access / f"{job['job_id']}.dbn.zst"
                row = {
                    "job_id": job["job_id"], "bundle": job["bundle"],
                    "dataset": job["dataset"], "schema": job["schema"],
                    "symbols": job["symbols"], "start": job["start"], "end": job["end"],
                    "analysis_access": job["analysis_access"],
                    "quoted_cost_usd": str(quoted), "reserved_cumulative_usd": str(reserved),
                    "path": str(path), "local_staging_path": "DIRECT_ON_SCC",
                    "bytes": "", "sha256": "", "error_type": "",
                    "completion_status": "SCC_SUBMISSION_STARTED_NO_BLIND_RETRY",
                    "warning_count": "", "warning_types": "",
                }
                manifest.append(row)
                atomic_csv(manifest_path, manifest)
                in_flight[executor.submit(download_one, job, row)] = row

            if not in_flight:
                break
            done, _ = wait(in_flight, return_when=FIRST_COMPLETED)
            for future in done:
                row, _ = future.result()
                in_flight.pop(future)
                completed_this_run += row["completion_status"] == "DOWNLOADED_NATIVE_DBN_ON_SCC_UNVERIFIED"
                if row["completion_status"] == "DOWNLOADED_NATIVE_DBN_ON_SCC_UNVERIFIED":
                    consecutive_errors = 0
                else:
                    consecutive_errors += 1
                atomic_csv(manifest_path, manifest)

    counts: dict[str, int] = {}
    for row in manifest:
        counts[row["completion_status"]] = counts.get(row["completion_status"], 0) + 1
    status = "COMPLETE_WITH_EXPLICIT_GAPS" if not remaining and not in_flight else "STOPPED_BY_CONSECUTIVE_ERROR_CIRCUIT_BREAKER"
    atomic_json(CONTROL / "scc_direct_receipt.json", {
        "status": status,
        "sdk_version": db.__version__,
        "max_workers": MAX_WORKERS,
        "scc_hash_verification": False,
        "completed_this_run": completed_this_run,
        "manifest_rows": len(manifest),
        "state_counts": counts,
        "remaining_unsubmitted": len(remaining),
        "reserved_gross_usage_usd": str(reserved),
        "hard_credit_cap_usd": str(CAP),
        "cash_spending_usd": "0.00",
        "manifest_sha256": sha256(manifest_path),
        "api_key_serialized_printed_or_hashed": False,
    })
    print(json.dumps({"status": status, "completed_this_run": completed_this_run,
                      "remaining_unsubmitted": len(remaining), "reserved": str(reserved)}, indent=2))


if __name__ == "__main__":
    main()
