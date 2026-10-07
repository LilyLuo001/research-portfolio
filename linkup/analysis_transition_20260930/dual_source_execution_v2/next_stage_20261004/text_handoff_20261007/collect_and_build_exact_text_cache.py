#!/usr/bin/env python3
"""Collect completed regional materializations, then verify and build cache."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REGIONS = {
    "kunshan": {
        "host": "lilysharp@cancon.hpccube.com", "port": "65023", "job": "123910578",
        "remote": "/public/home/lilysharp/linkup_analysis_execution_oct02/private/next_stage_20261004/text_handoff_20261007/run-123660254",
    },
    "wuzhen": {
        "host": "lilysharp@wuzh02.hpccube.com", "port": "65091", "job": "46027883",
        "remote": "/work/home/lilysharp/private/next_stage_20261004/text_handoff_20261007/run-123660254",
    },
}


def options(port: str, identity: Path | None, control_path: str | None) -> list[str]:
    value = ["-p", port, "-o", "BatchMode=yes"]
    if identity:
        value += ["-i", str(identity)]
    if control_path:
        value += ["-o", f"ControlPath={control_path}"]
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--handoff-dir", type=Path, required=True)
    parser.add_argument("--materialized-dir", type=Path, required=True)
    parser.add_argument("--public-receipt", type=Path, required=True)
    parser.add_argument("--kunshan-identity", type=Path)
    parser.add_argument("--wuzhen-identity", type=Path)
    parser.add_argument("--kunshan-control-path")
    parser.add_argument("--wuzhen-control-path")
    parser.add_argument("--status-timeout", type=int, default=60)
    parser.add_argument("--transfer-timeout", type=int, default=1800)
    parser.add_argument("--builder-timeout", type=int, default=600)
    args = parser.parse_args()
    args.materialized_dir.mkdir(parents=True, exist_ok=True)

    for region, config in REGIONS.items():
        identity = getattr(args, f"{region}_identity")
        control_path = getattr(args, f"{region}_control_path")
        ssh_options = options(config["port"], identity, control_path)
        state = subprocess.run(
            ["ssh", "-T", *ssh_options, config["host"],
             f"sacct -j {config['job']} --starttime 2026-10-07 --noheader --parsable2 --format=State | head -1"],
            check=True, text=True, stdout=subprocess.PIPE, timeout=args.status_timeout,
        ).stdout.strip()
        if state != "COMPLETED":
            raise RuntimeError(f"{region} job {config['job']} is {state or 'UNKNOWN'}; no files collected")
        for suffix in ("text.csv", "materialize_receipt.json"):
            name = f"fixed10000_{region}.{suffix}"
            scp_options = ["-P" if item == "-p" else item for item in ssh_options]
            subprocess.run(
                ["scp", "-q", *scp_options, f"{config['host']}:{config['remote']}/{name}", str(args.materialized_dir / name)],
                check=True, timeout=args.transfer_timeout,
            )

    builder = Path(__file__).with_name("build_exact_text_cache.py")
    result = subprocess.run([
        sys.executable, str(builder), "--sample", str(args.sample),
        "--handoff-dir", str(args.handoff_dir), "--materialized-dir", str(args.materialized_dir),
        "--public-receipt", str(args.public_receipt),
    ], check=True, text=True, stdout=subprocess.PIPE, timeout=args.builder_timeout)
    receipt = json.loads(result.stdout)
    if receipt.get("status") != "complete" or receipt.get("sample_rows") != 10000:
        raise RuntimeError("cache builder did not return a complete 10,000-row receipt")
    print(json.dumps(receipt, sort_keys=True))


if __name__ == "__main__":
    main()
