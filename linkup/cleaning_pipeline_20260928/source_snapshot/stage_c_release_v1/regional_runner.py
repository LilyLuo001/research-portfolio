#!/usr/bin/env python3
"""Resume a region plan one raw shard at a time with bounded rolling output."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from prepare_shard_input import atomic_json, prepare


def read_jsonl(path: Path) -> list[dict]:
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


def tree_bytes(path: Path) -> int:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) if path.exists() else 0


def run(argv: list[str], timeout: Optional[int] = None) -> None:
    subprocess.run(argv, check=True, timeout=timeout)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--buffer-root", type=Path, required=True)
    parser.add_argument("--checkpoint-root", type=Path, required=True)
    parser.add_argument("--parser", type=Path, required=True)
    parser.add_argument("--enrichment", type=Path, required=True)
    parser.add_argument("--lean-writer", type=Path, required=True)
    parser.add_argument("--transfer-mode", choices=("direct", "queue"), default="direct")
    parser.add_argument("--transfer", type=Path)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--per-shard-output-cap-bytes", type=int, required=True)
    parser.add_argument("--buffer-cap-bytes", type=int, required=True)
    parser.add_argument("--free-reserve-bytes", type=int, required=True)
    parser.add_argument("--transfer-host"); parser.add_argument("--transfer-port")
    parser.add_argument("--transfer-user"); parser.add_argument("--transfer-key")
    parser.add_argument("--transfer-known-hosts")
    parser.add_argument("--transfer-control-path")
    parser.add_argument("--remote-root")
    parser.add_argument("--remote-cap-bytes", type=int, default=420_000_000_000)
    parser.add_argument("--transfer-attempts", type=int, default=3)
    parser.add_argument("--transfer-command-timeout-seconds", type=int, default=75)
    parser.add_argument("--transfer-attempt-timeout-seconds", type=int, default=90)
    args = parser.parse_args()

    if args.transfer_mode == "direct":
        direct_required = {
            "transfer": args.transfer, "transfer_host": args.transfer_host,
            "transfer_port": args.transfer_port, "transfer_user": args.transfer_user,
            "transfer_key": args.transfer_key,
            "transfer_known_hosts": args.transfer_known_hosts,
            "remote_root": args.remote_root,
        }
        missing = sorted(name for name, value in direct_required.items() if value is None)
        if missing:
            parser.error("direct transfer mode requires: " + ", ".join(missing))

    buffer_root = args.buffer_root.resolve(); checkpoint_root = args.checkpoint_root.resolve()
    buffer_root.mkdir(parents=True, exist_ok=True); checkpoint_root.mkdir(parents=True, exist_ok=True)
    rows = read_jsonl(args.plan.resolve())
    code_sha256 = {
        "parser": sha256(args.parser.resolve()),
        "enrichment": sha256(args.enrichment.resolve()),
        "lean_writer": sha256(args.lean_writer.resolve()),
    }
    if len({row["shard_id"] for row in rows}) != len(rows):
        raise ValueError("duplicate shard_id in plan")

    for row in rows:
        shard_id = row["shard_id"]
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", shard_id):
            raise ValueError(f"unsafe shard_id: {shard_id!r}")
        done = checkpoint_root / (shard_id + ".published.json")
        if done.exists():
            receipt = json.loads(done.read_text())
            complete = receipt.get("shard_complete", {})
            accounting = complete.get("accounting", {})
            if not (
                receipt.get("status") == "published_verified"
                and receipt.get("shard_id") == shard_id
                and complete.get("code_sha256") == code_sha256
                and accounting.get("source_file") == row["source_file"]
                and accounting.get("source_bytes") == row["source_bytes"]
                and accounting.get("source_sha256_cached") == row["source_sha256_cached"]
                and accounting.get("sidecar_sha256") == row["sidecar_sha256"]
                and accounting.get("raw_rows") == row["raw_rows"]
            ):
                raise RuntimeError(f"{shard_id}: published receipt does not match frozen plan/code")
            continue
        raw = Path(row["source_path"])
        sidecar = Path(row["sidecar_path"])
        if not raw.is_file() or raw.stat().st_size != row["source_bytes"]:
            raise ValueError(f"{shard_id}: source size/path differs from cached verified inventory")
        if not sidecar.is_file():
            raise FileNotFoundError(f"{shard_id}: disposition sidecar missing")
        if sidecar.stat().st_size != row["sidecar_bytes"]:
            raise RuntimeError(f"{shard_id}: disposition sidecar size differs from frozen plan")
        sidecar_sha256 = sha256(sidecar)
        if sidecar_sha256 != row["sidecar_sha256"]:
            raise RuntimeError(f"{shard_id}: disposition sidecar SHA differs from frozen plan")
        work = buffer_root / (shard_id + ".work")
        output = buffer_root / shard_id
        if output.exists() and not (output / "SHARD_COMPLETE.json").exists():
            raise RuntimeError(f"{shard_id}: incomplete output exists; inspect before resume")
        if output.exists():
            prior = json.loads((output / "SHARD_COMPLETE.json").read_text())
            prior_accounting = prior.get("accounting", {})
            if not (
                prior.get("code_sha256") == code_sha256
                and prior_accounting.get("source_file") == row["source_file"]
                and prior_accounting.get("source_bytes") == row["source_bytes"]
                and prior_accounting.get("source_sha256_cached") == row["source_sha256_cached"]
                and prior_accounting.get("sidecar_sha256") == sidecar_sha256
                and prior_accounting.get("raw_rows") == row["raw_rows"]
            ):
                raise RuntimeError(f"{shard_id}: retained output differs from frozen plan/code")
        if not output.exists():
            if tree_bytes(buffer_root) > args.buffer_cap_bytes:
                raise RuntimeError("local generated buffer cap reached; resume after successful transfers")
            if shutil.disk_usage(buffer_root).free < args.free_reserve_bytes:
                raise RuntimeError("local free-space reserve reached")
            if work.exists(): shutil.rmtree(work)
            work.mkdir()
            staged = work / "canonical_usa.parquet"
            accounting = prepare(raw, sidecar, staged)
            if accounting["raw_rows"] != row["raw_rows"]:
                raise RuntimeError(f"{shard_id}: raw row count differs from frozen plan")
            if accounting["sidecar_source_files"] != [row["source_file"]]:
                raise RuntimeError(f"{shard_id}: sidecar SOURCE_FILE differs from frozen plan")
            accounting.update({
                "shard_id": shard_id, "region": row["region"],
                "source_file": row["source_file"], "source_bytes": row["source_bytes"],
                "source_sha256_cached": row["source_sha256_cached"],
                "source_hash_recomputed": False,
                "sidecar_sha256": sidecar_sha256,
            })
            atomic_json(work / "ACCOUNTING.json", accounting)
            lean = work / "lean"
            run([sys.executable, str(args.lean_writer), "--source", str(staged),
                 "--parser", str(args.parser), "--enrichment", str(args.enrichment),
                 "--output-dir", str(lean), "--workers", str(args.workers),
                 "--output-cap-bytes", str(args.per_shard_output_cap_bytes)])
            complete = json.loads((lean / "COMPLETE.json").read_text())
            if complete["processed_rows"] != accounting["canonical_usa_rows"]:
                raise RuntimeError(f"{shard_id}: canonical input/lean output conservation failure")
            os.replace(lean, output)
            atomic_json(output / "SHARD_COMPLETE.json", {
                "status": "complete", "accounting": accounting,
                "lean_complete": complete,
                "code_sha256": code_sha256,
            })
            shutil.rmtree(work)

        if args.transfer_mode == "queue":
            complete_path = output / "SHARD_COMPLETE.json"
            queued = checkpoint_root / (shard_id + ".queued.json")
            queue_receipt = {
                "status": "sealed_for_transfer",
                "schema_version": 1,
                "shard_id": shard_id,
                "region": row["region"],
                "generated_output": str(output),
                "generated_output_bytes": tree_bytes(output),
                "shard_complete": str(complete_path),
                "shard_complete_sha256": sha256(complete_path),
                "source_file": row["source_file"],
                "source_bytes": row["source_bytes"],
                "source_sha256_cached": row["source_sha256_cached"],
                "sidecar_sha256": row["sidecar_sha256"],
                "raw_rows": row["raw_rows"],
                "code_sha256": code_sha256,
                "compute_waited_for_transfer": False,
            }
            if queued.exists() and json.loads(queued.read_text()) != queue_receipt:
                raise RuntimeError(f"{shard_id}: queued receipt differs from sealed output/plan/code")
            if not queued.exists():
                atomic_json(queued, queue_receipt)
            continue

        transfer_args = [
            sys.executable, str(args.transfer), "--source", str(output),
            "--allowed-source-root", str(buffer_root), "--local-receipt", str(done),
            "--host", args.transfer_host, "--port", args.transfer_port,
            "--user", args.transfer_user, "--key", args.transfer_key,
            "--known-hosts", args.transfer_known_hosts,
            "--remote-root", args.remote_root, "--shard-id", shard_id,
            "--remote-cap-bytes", str(args.remote_cap_bytes),
            "--command-timeout-seconds", str(args.transfer_command_timeout_seconds),
        ]
        if args.transfer_control_path:
            transfer_args += ["--control-path", args.transfer_control_path]
        last_error = None
        for attempt in range(1, args.transfer_attempts + 1):
            try:
                run(transfer_args, timeout=args.transfer_attempt_timeout_seconds)
                last_error = None; break
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                last_error = exc
                if attempt < args.transfer_attempts:
                    time.sleep(min(60, 5 * (2 ** (attempt - 1))))
        if last_error is not None:
            atomic_json(checkpoint_root / "REGION_PAUSED.json", {
                "status": "paused_transfer_unavailable",
                "shard_id": shard_id,
                "transfer_attempts": args.transfer_attempts,
                "generated_output_retained": str(output),
                "resume_recomputes_shard": False,
            })
            print(json.dumps({"status": "paused_transfer_unavailable", "shard_id": shard_id}, sort_keys=True))
            raise SystemExit(75) from last_error
        (checkpoint_root / "REGION_PAUSED.json").unlink(missing_ok=True)
    if args.transfer_mode == "queue":
        atomic_json(checkpoint_root / "REGION_QUEUE_COMPLETE.json", {
            "status": "compute_queue_complete", "planned_shards": len(rows),
            "queued_receipts": len(list(checkpoint_root.glob("*.queued.json"))),
            "published_receipts": len(list(checkpoint_root.glob("*.published.json"))),
            "final_publication_complete": False,
        })
    else:
        atomic_json(checkpoint_root / "REGION_COMPLETE.json", {
            "status": "complete", "planned_shards": len(rows),
            "published_receipts": len(list(checkpoint_root.glob("*.published.json"))),
        })


if __name__ == "__main__":
    main()
