#!/usr/bin/env python3
"""Owner-authorized recovery of the three explicitly quarantined P1 jobs."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
import warnings
from decimal import Decimal
from pathlib import Path

import databento as db


CONTROL = Path("/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914/databento_final_native/control")
TARGETS = {"COREJOB_00623", "COREJOB_00758", "ALTJOB_00372"}
CAP = Decimal("123.00")
FIELDS = [
    "job_id", "bundle", "dataset", "schema", "symbols", "start", "end",
    "analysis_access", "quoted_cost_usd", "reserved_cumulative_usd", "path",
    "local_staging_path", "bytes", "sha256", "error_type",
    "completion_status", "warning_count", "warning_types",
]


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def atomic_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with tempfile.NamedTemporaryFile(mode="w", newline="", encoding="utf-8", dir=path.parent, delete=False) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        tmp = Path(handle.name)
    tmp.replace(path)


def atomic_json(path: Path, value: dict) -> None:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        tmp = Path(handle.name)
    tmp.replace(path)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError("DATABENTO_API_KEY absent; no market-data call made")

    selection = json.loads((CONTROL / "selection_receipt.json").read_text())
    quotes = {r["job_id"]: r for r in read_csv(CONTROL / "quote_jobs.csv")}
    jobs = {
        r["job_id"]: r
        for name in ("core_grouped_jobs.csv", "alternative_grouped_jobs.csv")
        for r in read_csv(CONTROL / name)
        if r["job_id"] in TARGETS
    }
    manifest_path = CONTROL / "download_manifest.csv"
    manifest = read_csv(manifest_path)
    original = {r["job_id"]: r for r in manifest if r["job_id"] in TARGETS}
    if set(jobs) != TARGETS or set(original) != TARGETS:
        raise RuntimeError("target set mismatch; no retry made")
    if any(quotes[j]["status"] != "OK" for j in TARGETS):
        raise RuntimeError("target lacks successful exact quote")
    if any("UNCERTAIN" not in original[j]["completion_status"] for j in TARGETS):
        raise RuntimeError("target is not an explicit uncertain gap")

    retry_cost = sum((Decimal(quotes[j]["cost_usd"]) for j in TARGETS), Decimal("0"))
    worst_case = Decimal(selection["gross_estimated_usage_usd"]) + retry_cost
    if worst_case > CAP:
        raise RuntimeError("worst-case retry cost exceeds hard cap")

    retry_path = CONTROL / "gap_retry_manifest.csv"
    retries: list[dict] = []
    client = db.Historical(key=key)
    for job_id in sorted(TARGETS):
        job = jobs[job_id]
        target = Path(original[job_id]["path"])
        if target.exists():
            raise RuntimeError(f"target already exists; no retry: {job_id}")
        row = {
            "job_id": job_id,
            "original_status": original[job_id]["completion_status"],
            "quoted_retry_cost_usd": quotes[job_id]["cost_usd"],
            "target_path": str(target),
            "bytes": "",
            "warning_count": "",
            "warning_types": "",
            "error_type": "",
            "retry_status": "AUTHORIZED_RETRY_SUBMISSION_STARTED_NO_BLIND_RETRY",
        }
        retries.append(row)
        atomic_csv(retry_path, retries, list(row))
        caught: list[str] = []
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with warnings.catch_warnings(record=True) as seen:
                warnings.simplefilter("always")
                client.timeseries.get_range(
                    dataset=job["dataset"], start=job["start"], end=job["end"],
                    symbols=job["symbols"].split(";"), schema=job["schema"],
                    stype_in=job["stype_in"], stype_out="instrument_id", path=target,
                )
                caught = sorted({f"{type(w.message).__name__}:{w.message}" for w in seen})
            if not target.exists() or target.stat().st_size == 0:
                raise RuntimeError("retry returned without a nonempty DBN file")
            row["bytes"] = str(target.stat().st_size)
            row["retry_status"] = "RECOVERED_ON_SCC_UNVERIFIED"
            original[job_id]["completion_status"] = "RECOVERED_BY_AUTHORIZED_RETRY_ON_SCC_UNVERIFIED"
            original[job_id]["bytes"] = row["bytes"]
            original[job_id]["local_staging_path"] = "DIRECT_ON_SCC_AUTHORIZED_RETRY"
            original[job_id]["warning_count"] = str(len(caught))
            original[job_id]["warning_types"] = " | ".join(caught)
            original[job_id]["error_type"] = ""
        except Exception as exc:
            row["error_type"] = type(exc).__name__
            row["retry_status"] = "RETRY_UNCERTAIN_STOPPED_NO_FURTHER_RETRY"
            atomic_csv(retry_path, retries, list(row))
            raise
        row["warning_count"] = str(len(caught))
        row["warning_types"] = " | ".join(caught)
        atomic_csv(retry_path, retries, list(row))
        atomic_csv(manifest_path, manifest, FIELDS)

    atomic_json(CONTROL / "gap_recovery_receipt.json", {
        "status": "RECOVERY_COMPLETE",
        "recovered_job_ids": sorted(TARGETS),
        "retry_quote_total_usd": str(retry_cost),
        "original_frozen_estimate_usd": selection["gross_estimated_usage_usd"],
        "worst_case_total_if_interrupted_streams_were_fully_billed_usd": str(worst_case),
        "hard_credit_cap_usd": str(CAP),
        "cash_spending_usd": "0.00",
        "scc_hash_verification": False,
        "download_manifest_sha256": digest(manifest_path),
        "gap_retry_manifest_sha256": digest(retry_path),
        "api_key_serialized_printed_or_hashed": False,
    })
    print(json.dumps({"status": "RECOVERY_COMPLETE", "recovered": sorted(TARGETS),
                      "retry_quote_total_usd": str(retry_cost),
                      "worst_case_total_usd": str(worst_case)}, indent=2))


if __name__ == "__main__":
    main()
