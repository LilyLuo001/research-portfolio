#!/usr/bin/env python3
"""Resume the fixed earnings download concurrently without duplicating completed files."""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import threading
from pathlib import Path

import databento as db


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for part in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(part)
    return h.hexdigest()


def put(path: Path, value: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temp.replace(path)


def spec(row: dict) -> dict:
    return {"dataset": row["dataset"], "schema": "mbp-1", "symbols": row["resolved_symbols"], "stype_in": row["stype_in"], "stype_out": "instrument_id", "start": row["start_utc"], "end": row["end_utc"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quote", required=True, type=Path)
    ap.add_argument("--receipt", required=True, type=Path)
    ap.add_argument("--raw-root", required=True, type=Path)
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()
    key = os.getenv("DATABENTO_API_KEY")
    if not key:
        raise RuntimeError("DATABENTO_API_KEY absent")
    quote = json.loads(args.quote.read_text())
    if quote.get("status") != "QUOTED_NO_DOWNLOAD" or len(quote.get("requests", [])) != 288:
        raise RuntimeError("completed fixed quote required")
    old = json.loads(args.receipt.read_text()) if args.receipt.exists() else {"files": []}
    completed = {r["request_id"]: r for r in old.get("files", []) if r.get("status") in {"DOWNLOADED_NATIVE_DBN_ON_SCC", "REUSED_EXISTING_NATIVE_DBN_ON_SCC"} and Path(r["path"]).exists() and Path(r["path"]).stat().st_size > 0}
    interrupted = [r for r in old.get("files", []) if r.get("status") == "SUBMISSION_STARTED_NO_BLIND_RETRY"]
    quarantined = []
    for row in interrupted:
        path = Path(row["path"])
        if path.exists():
            quarantine = path.with_suffix(path.suffix + ".interrupted")
            path.replace(quarantine)
            quarantined.append({"request_id": row["request_id"], "quarantine": str(quarantine), "bytes": quarantine.stat().st_size})
    pending = [r for r in quote["requests"] if r["request_id"] not in completed]
    lock = threading.Lock()
    failures = []
    state = {"status": "PARALLEL_RESUME_IN_PROGRESS", "quoted_total_usd": quote["total_quoted_cost_usd"], "completed_before_resume": len(completed), "interrupted_attempts": [r["request_id"] for r in interrupted], "quarantined_partials": quarantined, "files": list(completed.values()), "failures": failures}
    put(args.receipt, state)

    def run(row: dict) -> dict:
        target = args.raw_root / f"{row['request_id']}.dbn.zst"
        if target.exists():
            raise RuntimeError(f"untracked target exists: {target}")
        client = db.Historical(key)
        client.timeseries.get_range(**spec(row), path=target)
        if not target.exists() or target.stat().st_size == 0:
            raise RuntimeError(f"download produced no file: {target}")
        return {**row, "path": str(target), "status": "DOWNLOADED_NATIVE_DBN_ON_SCC", "bytes": target.stat().st_size, "sha256": digest(target)}

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(run, row): row for row in pending}
        for future in concurrent.futures.as_completed(futures):
            row = futures[future]
            with lock:
                try:
                    result = future.result()
                    completed[result["request_id"]] = result
                except Exception as exc:
                    failures.append({"request_id": row["request_id"], "error_type": type(exc).__name__, "error": str(exc)[:500]})
                state["files"] = list(completed.values())
                put(args.receipt, state)
    state["files"] = [completed[r["request_id"]] for r in quote["requests"] if r["request_id"] in completed]
    state["status"] = "COMPLETE_NATIVE_DBN_ON_SCC" if len(completed) == 288 and not failures else "PARTIAL_WITH_RECORDED_FAILURES"
    put(args.receipt, state)
    print(json.dumps({"status": state["status"], "completed": len(completed), "failures": len(failures), "workers": args.workers}, sort_keys=True))


if __name__ == "__main__":
    main()
