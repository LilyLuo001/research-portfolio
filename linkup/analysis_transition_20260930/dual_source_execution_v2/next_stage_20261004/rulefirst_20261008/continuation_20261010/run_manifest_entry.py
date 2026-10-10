#!/usr/bin/env python3
"""Invoke the immutable D58 runner for one admitted staged manifest entry."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

RUNNER_SHA = "3826142b6cddb549e831c8302be1d460ba3e85ee96bb7736af5549f878b3bf44"


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True); p.add_argument("--index", type=int, required=True)
    p.add_argument("--stage-root", required=True); p.add_argument("--output-root", required=True)
    p.add_argument("--runner", required=True); p.add_argument("--workers", type=int, required=True)
    a = p.parse_args()
    entries = json.loads(Path(a.manifest).read_text())["entries"]
    if not 1 <= a.index <= len(entries):
        raise RuntimeError("task index outside manifest")
    e = entries[a.index - 1]; sid = e["shard_id"]; short = sid[:16]
    runner = Path(a.runner)
    if digest(runner) != RUNNER_SHA:
        raise RuntimeError("frozen runner SHA mismatch")
    ready = Path(a.stage_root)/"ready"/sid
    sr = json.loads((ready/"STAGING_RECEIPT_PUBLIC.json").read_text())
    if (sr.get("status") != "complete" or sr.get("source_sha256") != e["source_sha256_cached"]
            or sr.get("sidecar_sha256") != e["sidecar_sha256"]):
        raise RuntimeError("staging receipt identity mismatch")
    out = Path(a.output_root)/("shard_" + short)
    receipt = Path(a.output_root)/("SHARD_" + short + "_RECEIPT_PUBLIC.json")
    cmd = [sys.executable, str(runner),
           "--raw", str(ready/e["source_file"]),
           "--sidecar", str(ready/(sid + ".sidecar.parquet")),
           "--output-dir", str(out), "--public-receipt", str(receipt),
           "--expected-raw-sha256", e["source_sha256_cached"],
           "--expected-sidecar-sha256", e["sidecar_sha256"],
           "--workers", str(a.workers)]
    subprocess.check_call(cmd)


if __name__ == "__main__":
    main()
