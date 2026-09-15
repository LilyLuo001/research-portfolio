#!/usr/bin/env python3
"""Quote and download the large P1 acquisition manifest with a hard credit cap.

The API key is read only from DATABENTO_API_KEY and is never printed, written,
or hashed.  Quote mode calls only free metadata endpoints.  Download mode is
guarded by the exact quote receipt, the owner's USD 123 credit-only ceiling,
and an explicit command flag.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
import shlex
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import databento as db


ROOT = Path(
    os.environ.get(
        "P1_DATABENTO_OUTPUT",
        Path(__file__).resolve().parent / "databento_acquisition",
    )
)
GROUPING = ROOT / "grouping_receipt.json"
HARD_CAP = Decimal("123.00")
SCC_HOST = "qluo@scc1.bu.edu"
SCC_ARCHIVE = os.environ.get(
    "P1_DATABENTO_SCC_ARCHIVE",
    "/projectnb/econdept/qluo/P1_Refraction_WRDS/missing_data_round_20260914/databento_native",
)
PRIORITY = [
    "CORE_XNAS_BBO1S_DATE_WIDE",
    "ALTERNATIVE_ARCX.PILLAR_BBO1S_DATE_WIDE",
    "ALTERNATIVE_BATS.PITCH_BBO1S_DATE_WIDE",
    "ALTERNATIVE_XNYS.PILLAR_BBO1S_DATE_WIDE",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def json_write(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")


def csv_read(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def csv_write(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if fields is None:
        fields = list(rows[0]) if rows else []
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def safe_call(fn: Any, **kwargs: Any) -> dict:
    try:
        return {"status": "OK", "value": fn(**kwargs)}
    except Exception as exc:
        return {"status": "ERROR", "error_type": type(exc).__name__, "error": str(exc)}


def load_and_verify_jobs() -> tuple[list[dict], dict]:
    grouping = json.loads(GROUPING.read_text())
    expected = grouping["output_hashes"]
    for name, digest in expected.items():
        if sha256(ROOT / name) != digest:
            raise RuntimeError(f"grouped manifest hash mismatch: {name}")
    jobs = csv_read(ROOT / "core_grouped_jobs.csv") + csv_read(ROOT / "alternative_grouped_jobs.csv")
    if len(jobs) != grouping["core_grouped_jobs"] + grouping["alternative_grouped_jobs"]:
        raise RuntimeError("grouped job count mismatch")
    return jobs, grouping


def client() -> db.Historical:
    key = os.environ.get("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError("DATABENTO_API_KEY is absent; no API call made")
    return db.Historical(key=key)


def quote() -> None:
    jobs, grouping = load_and_verify_jobs()
    c = client()
    datasets = sorted({j["dataset"] for j in jobs})
    catalog = {
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "sdk_version": db.__version__,
        "metadata_only": True,
        "market_data_download_calls": 0,
        "datasets": {},
    }
    prior_catalog_path = ROOT / "catalog_receipt.json"
    if prior_catalog_path.exists():
        catalog = json.loads(prior_catalog_path.read_text())
    else:
        for dataset in datasets:
            catalog["datasets"][dataset] = {
                "schemas": safe_call(c.metadata.list_schemas, dataset=dataset),
                "range": safe_call(c.metadata.get_dataset_range, dataset=dataset),
            }
    def quote_one(job: dict) -> dict:
        # Historical clients are not assumed thread-safe. Each concurrent
        # metadata task receives its own client/session.
        c_job = client()
        symbols = job["symbols"].split(";")
        common = {
            "dataset": job["dataset"],
            "start": job["start"],
            "end": job["end"],
            "symbols": symbols,
            "schema": job["schema"],
            "stype_in": job["stype_in"],
        }
        cost = {"status": "ERROR", "error_type": "NOT_RUN"}
        count = {"status": "ERROR", "error_type": "NOT_RUN"}
        # Metadata queries create no charges. Retry only transient transport
        # failures; persistent range/symbology errors remain explicit.
        for attempt in range(3):
            cost = safe_call(c_job.metadata.get_cost, **common)
            count = safe_call(c_job.metadata.get_record_count, **common)
            transient = {"SSLError", "ProxyError", "ConnectionError", "TimeoutError"}
            error_types = {cost.get("error_type", ""), count.get("error_type", "")}
            if cost["status"] == count["status"] == "OK" or not (error_types & transient):
                break
            time.sleep(0.5 * (attempt + 1))
        status = "OK" if cost["status"] == count["status"] == "OK" else "ERROR"
        return {
            "job_id": job["job_id"],
            "bundle": job["bundle"],
            "dataset": job["dataset"],
            "schema": job["schema"],
            "start": job["start"],
            "end": job["end"],
            "symbols": job["symbols"],
            "symbol_count": job["symbol_count"],
            "status": status,
            "cost_usd": cost.get("value"),
            "record_count": count.get("value"),
            "cost_error_type": cost.get("error_type", ""),
            "count_error_type": count.get("error_type", ""),
            "charges_created": 0,
        }

    expected_by_id = {j["job_id"]: j for j in jobs}
    prior_path = ROOT / "quote_jobs.csv"
    if not prior_path.exists():
        prior_path = ROOT / "quote_jobs_checkpoint.csv"
    prior_rows = csv_read(prior_path) if prior_path.exists() else []
    retained = {
        r["job_id"]: r
        for r in prior_rows
        if r.get("status") == "OK"
        and r.get("job_id") in expected_by_id
        and r.get("dataset") == expected_by_id[r["job_id"]]["dataset"]
        and r.get("schema") == expected_by_id[r["job_id"]]["schema"]
        and r.get("start") == expected_by_id[r["job_id"]]["start"]
        and r.get("end") == expected_by_id[r["job_id"]]["end"]
        and r.get("symbols") == expected_by_id[r["job_id"]]["symbols"]
    }
    rows = list(retained.values())
    pending_jobs = [j for j in jobs if j["job_id"] not in retained]
    # Metadata endpoints are free and independent.  Bound concurrency to avoid
    # thousands of serial network round trips without overwhelming the API.
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {executor.submit(quote_one, job): job["job_id"] for job in pending_jobs}
        for index, future in enumerate(as_completed(futures), 1):
            rows.append(future.result())
            if index % 50 == 0 or index == len(pending_jobs):
                csv_write(ROOT / "quote_jobs_checkpoint.csv", sorted(rows, key=lambda r: r["job_id"]))
    rows = sorted(rows, key=lambda r: r["job_id"])
    csv_write(ROOT / "quote_jobs.csv", rows)
    bundle_rows = []
    for bundle in PRIORITY:
        subset = [r for r in rows if r["bundle"] == bundle]
        success = [r for r in subset if r["status"] == "OK" and r["cost_usd"] is not None]
        total = sum((Decimal(str(r["cost_usd"])) for r in success), Decimal("0"))
        positive_records = sum(int(r["record_count"] or 0) > 0 for r in success)
        bundle_rows.append({
            "bundle": bundle,
            "dataset": subset[0]["dataset"] if subset else "",
            "jobs": len(subset),
            "successful_jobs": len(success),
            "positive_record_jobs": positive_records,
            "estimated_total_usd": str(total) if len(success) == len(subset) and subset else "",
            "complete": len(success) == len(subset) and bool(subset),
            "all_jobs_have_positive_records": positive_records == len(subset) and bool(subset),
        })
    csv_write(ROOT / "bundle_quotes.csv", bundle_rows)
    json_write(ROOT / "catalog_receipt.json", catalog)
    selected = []
    committed = Decimal("0")
    for bundle in PRIORITY:
        row = next(r for r in bundle_rows if r["bundle"] == bundle)
        if str(row["complete"]).lower() != "true" or not row["estimated_total_usd"]:
            continue
        price = Decimal(row["estimated_total_usd"])
        if committed + price <= HARD_CAP:
            selected.append(bundle)
            committed += price
    selection = {
        "status": "QUOTED_SELECTION_FROZEN_NO_DOWNLOAD",
        "selected_bundles": selected,
        "gross_estimated_usage_usd": str(committed),
        "hard_credit_cap_usd": str(HARD_CAP),
        "cash_spending_usd": "0.00",
        "quote_jobs_sha256": sha256(ROOT / "quote_jobs.csv"),
        "bundle_quotes_sha256": sha256(ROOT / "bundle_quotes.csv"),
        "grouping_receipt_sha256": sha256(GROUPING),
        "api_key_serialized_printed_or_hashed": False,
    }
    json_write(ROOT / "selection_receipt.json", selection)
    print(json.dumps(selection, indent=2))


def download(owner_approved: bool, skip_scc_hash_verification: bool = False) -> None:
    if not owner_approved:
        raise RuntimeError("--owner-approved-download required; no market-data call made")
    jobs, _ = load_and_verify_jobs()
    selection_path = ROOT / "selection_receipt.json"
    quote_path = ROOT / "quote_jobs.csv"
    if not selection_path.exists() or not quote_path.exists():
        raise RuntimeError("quote and frozen selection required; no market-data call made")
    selection = json.loads(selection_path.read_text())
    if selection.get("status") != "QUOTED_SELECTION_FROZEN_NO_DOWNLOAD":
        raise RuntimeError("selection is not frozen")
    if selection.get("quote_jobs_sha256") != sha256(quote_path):
        raise RuntimeError("quote receipt hash mismatch")
    total = Decimal(selection["gross_estimated_usage_usd"])
    if total > HARD_CAP or Decimal(selection["hard_credit_cap_usd"]) != HARD_CAP:
        raise RuntimeError("hard credit cap failed")
    selected_bundles = set(selection["selected_bundles"])
    if "CORE_XNAS_BBO1S_DATE_WIDE" not in selected_bundles:
        raise RuntimeError("core bundle absent from selection")
    quotes = {r["job_id"]: r for r in csv_read(quote_path)}
    selected_job_ids = set(selection.get("selected_job_ids", []))
    selected_jobs = (
        [j for j in jobs if j["job_id"] in selected_job_ids]
        if selected_job_ids
        else [j for j in jobs if j["bundle"] in selected_bundles]
    )
    if any(quotes[j["job_id"]]["status"] != "OK" for j in selected_jobs):
        raise RuntimeError("selected job lacks successful exact quote")

    c = client()
    staging = ROOT / "native_staging"
    staging.mkdir(exist_ok=True)
    manifest_path = ROOT / "download_manifest.csv"
    existing = csv_read(manifest_path) if manifest_path.exists() else []
    completed = {
        r["job_id"]
        for r in existing
        if r["completion_status"] in {
            "DOWNLOADED_NATIVE_DBN_VERIFIED_ON_SCC",
            "DOWNLOADED_NATIVE_DBN_TRANSFERRED_TO_SCC_UNVERIFIED",
        }
    }
    prior_submissions = {r["job_id"] for r in existing}
    manifest = list(existing)
    # Include every recorded submission in the reservation, including an
    # interrupted stream. That job is deliberately not retried blindly.
    reserved = sum((Decimal(quotes[j]["cost_usd"]) for j in prior_submissions), Decimal("0"))
    pending: list[tuple[dict, Path, str, str]] = []
    pending_bytes = 0

    def flush_pending() -> None:
        """Transfer a small batch per remote folder and verify all hashes."""
        nonlocal pending, pending_bytes
        if not pending:
            return
        by_folder: dict[str, list[tuple[dict, Path, str]]] = {}
        for row, local_path, remote_folder, remote_path in pending:
            by_folder.setdefault(remote_folder, []).append((row, local_path, remote_path))
        for remote_folder, items in by_folder.items():
            subprocess.run(
                ["ssh", "-o", "BatchMode=yes", SCC_HOST, f"mkdir -p {shlex.quote(remote_folder)}"],
                check=True,
            )
            subprocess.run(
                ["scp", *[str(local_path) for _, local_path, _ in items], f"{SCC_HOST}:{remote_folder}/"],
                check=True,
            )
            remote_hashes = {}
            if not skip_scc_hash_verification:
                hash_command = "shasum -a 256 " + " ".join(shlex.quote(remote_path) for _, _, remote_path in items)
                output = subprocess.run(
                    ["ssh", "-o", "BatchMode=yes", SCC_HOST, hash_command],
                    check=True,
                    text=True,
                    capture_output=True,
                ).stdout.splitlines()
                remote_hashes = {line.split(maxsplit=1)[1]: line.split()[0] for line in output if line.split()}
            for row, local_path, remote_path in items:
                if not skip_scc_hash_verification and remote_hashes.get(remote_path) != row["sha256"]:
                    row["completion_status"] = "REMOTE_HASH_MISMATCH_LOCAL_STAGING_PRESERVED"
                    csv_write(manifest_path, manifest)
                    raise RuntimeError(f"remote transfer hash mismatch: {row['job_id']}")
                local_path.unlink()
                row["local_staging_path"] = "REMOVED_AFTER_VERIFIED_SCC_TRANSFER"
                row["completion_status"] = (
                    "DOWNLOADED_NATIVE_DBN_TRANSFERRED_TO_SCC_UNVERIFIED"
                    if skip_scc_hash_verification
                    else "DOWNLOADED_NATIVE_DBN_VERIFIED_ON_SCC"
                )
        csv_write(manifest_path, manifest)
        pending = []
        pending_bytes = 0

    # Resume already-downloaded local staging files before new API calls. This
    # preserves the no-blind-retry rule following a controlled interruption.
    for row in manifest:
        if row["completion_status"] != "DOWNLOADED_LOCAL_PENDING_SCC_BATCH_TRANSFER":
            continue
        local_path = Path(row["local_staging_path"])
        if not local_path.exists():
            raise RuntimeError(f"staging file missing; no retry: {row['job_id']}")
        remote_path = row["path"]
        pending.append((row, local_path, str(Path(remote_path).parent), remote_path))
        pending_bytes += local_path.stat().st_size
    flush_pending()

    # Interrupted network streams are neither assumed absent nor retried.
    for row in manifest:
        if row["completion_status"] == "SUBMISSION_STARTED_NO_BLIND_RETRY":
            row["completion_status"] = "UNCERTAIN_STREAM_QUARANTINED_NO_RETRY"
    csv_write(manifest_path, manifest)

    for job in selected_jobs:
        if job["job_id"] in prior_submissions:
            continue
        quoted = Decimal(quotes[job["job_id"]]["cost_usd"])
        if reserved + quoted > total or reserved + quoted > HARD_CAP:
            raise RuntimeError("reservation cap breach")
        reserved += quoted
        access_folder = "sealed_post" if job["analysis_access"].startswith("ARCHIVE") else "pre_development"
        remote_folder = f"{SCC_ARCHIVE}/{job['bundle']}/{access_folder}"
        remote_path = f"{remote_folder}/{job['job_id']}.dbn.zst"
        path = staging / f"{job['job_id']}.dbn.zst"
        row = {
            "job_id": job["job_id"],
            "bundle": job["bundle"],
            "dataset": job["dataset"],
            "schema": job["schema"],
            "symbols": job["symbols"],
            "start": job["start"],
            "end": job["end"],
            "analysis_access": job["analysis_access"],
            "quoted_cost_usd": str(quoted),
            "reserved_cumulative_usd": str(reserved),
            "path": remote_path,
            "local_staging_path": str(path),
            "bytes": "",
            "sha256": "",
            "error_type": "",
            "completion_status": "SUBMISSION_STARTED_NO_BLIND_RETRY",
        }
        manifest.append(row)
        csv_write(manifest_path, manifest)
        try:
            c.timeseries.get_range(
                dataset=job["dataset"],
                start=job["start"],
                end=job["end"],
                symbols=job["symbols"].split(";"),
                schema=job["schema"],
                stype_in=job["stype_in"],
                stype_out="instrument_id",
                path=path,
            )
        except Exception as exc:
            flush_pending()
            row["completion_status"] = "UNCERTAIN_OR_PARTIAL_STOPPED_NO_RETRY"
            row["error_type"] = type(exc).__name__
            csv_write(manifest_path, manifest)
            raise
        row["bytes"] = path.stat().st_size
        row["sha256"] = sha256(path)
        row["completion_status"] = "DOWNLOADED_LOCAL_PENDING_SCC_BATCH_TRANSFER"
        pending.append((row, path, remote_folder, remote_path))
        pending_bytes += int(row["bytes"])
        csv_write(manifest_path, manifest)
        if len(pending) >= 25 or pending_bytes >= 500 * 1024 * 1024:
            flush_pending()
    flush_pending()
    receipt = {
        "status": "SELECTED_BUNDLES_DOWNLOADED_NATIVE_PENDING_BILLING_RECONCILIATION",
        "selected_bundles": sorted(selected_bundles),
        "downloaded_jobs": sum(r["completion_status"] in {"DOWNLOADED_NATIVE_DBN_VERIFIED_ON_SCC", "DOWNLOADED_NATIVE_DBN_TRANSFERRED_TO_SCC_UNVERIFIED"} for r in manifest),
        "reserved_gross_usage_usd": str(reserved),
        "hard_credit_cap_usd": str(HARD_CAP),
        "cash_spending_usd": "0.00",
        "download_manifest_sha256": sha256(manifest_path),
        "archive_root": f"{SCC_HOST}:{SCC_ARCHIVE}",
        "scc_hash_verification": not skip_scc_hash_verification,
        "local_staging_policy": "BATCH_UP_TO_25_JOBS_OR_500MB_REMOVE_AFTER_SCP_SUCCESS" if skip_scc_hash_verification else "BATCH_UP_TO_25_JOBS_OR_500MB_REMOVE_ONLY_AFTER_REMOTE_SHA256_MATCH",
        "api_key_serialized_printed_or_hashed": False,
    }
    json_write(ROOT / "download_receipt.json", receipt)
    print(json.dumps(receipt, indent=2))


def freeze_successful_quotes() -> None:
    """Freeze only exact successful quotes; never submit unquoted jobs."""
    jobs, _ = load_and_verify_jobs()
    quote_path = ROOT / "quote_jobs.csv"
    quotes = {r["job_id"]: r for r in csv_read(quote_path)}
    selected_jobs = [
        j for j in jobs
        if quotes.get(j["job_id"], {}).get("status") == "OK"
        and quotes[j["job_id"]].get("cost_usd") not in (None, "")
    ]
    total = sum((Decimal(quotes[j["job_id"]]["cost_usd"]) for j in selected_jobs), Decimal("0"))
    if total > HARD_CAP:
        raise RuntimeError("successful-quote total exceeds hard cap; no download authorized")
    selected_bundles = sorted({j["bundle"] for j in selected_jobs})
    if "CORE_XNAS_BBO1S_DATE_WIDE" not in selected_bundles:
        raise RuntimeError("no successfully quoted core jobs")
    all_ids = {j["job_id"] for j in jobs}
    selected_ids = {j["job_id"] for j in selected_jobs}
    selection = {
        "status": "QUOTED_SELECTION_FROZEN_NO_DOWNLOAD",
        "selection_mode": "EXACT_SUCCESSFUL_JOBS_ONLY",
        "selected_bundles": selected_bundles,
        "selected_job_ids": sorted(selected_ids),
        "excluded_unquoted_or_failed_job_ids": sorted(all_ids - selected_ids),
        "selected_jobs": len(selected_ids),
        "gross_estimated_usage_usd": str(total),
        "hard_credit_cap_usd": str(HARD_CAP),
        "cash_spending_usd": "0.00",
        "quote_jobs_sha256": sha256(quote_path),
        "grouping_receipt_sha256": sha256(GROUPING),
        "api_key_serialized_printed_or_hashed": False,
    }
    json_write(ROOT / "selection_receipt.json", selection)
    print(json.dumps({k: v for k, v in selection.items() if k not in {"selected_job_ids"}}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["quote", "freeze-successful", "download"])
    parser.add_argument("--owner-approved-download", action="store_true")
    parser.add_argument("--skip-scc-hash-verification", action="store_true")
    args = parser.parse_args()
    if args.mode == "quote":
        quote()
    elif args.mode == "freeze-successful":
        freeze_successful_quotes()
    else:
        download(args.owner_approved_download, args.skip_scc_hash_verification)


if __name__ == "__main__":
    main()
