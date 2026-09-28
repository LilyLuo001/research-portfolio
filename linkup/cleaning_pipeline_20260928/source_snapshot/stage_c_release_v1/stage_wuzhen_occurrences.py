#!/usr/bin/env python3
"""Stage the ten frozen Wuzhen key-only occurrence batches on Kunshan."""
from __future__ import annotations

import argparse, hashlib, json, os, subprocess, time
from pathlib import Path
import pyarrow.parquet as pq

BATCHES = {
    "batch_0001": (104074141, 3925934), "batch_0002": (413339136, 15593202),
    "batch_0003": (413578194, 15605035), "batch_0004": (409936578, 15465583),
    "batch_0005": (409815681, 15471764), "batch_0006": (409754207, 15473482),
    "batch_0007": (409804897, 15476740), "batch_0008": (412919605, 15597491),
    "batch_0009": (204643932, 7729719), "batch_0010": (363763982, 13753012),
}
EXPECTED_SCHEMA = {
    "JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "TEXT_STATE", "RAW_UTF8_BYTES",
    "NORMALIZED_UTF8_BYTES", "SCRIPT_HINT", "DESCRIPTION_COMPANY_ID", "RAW_KEY_MATCH",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def scp(args, remote: str, local: Path) -> None:
    command = ["scp", "-P", str(args.port), "-i", str(args.key),
               "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
               "-o", f"UserKnownHostsFile={args.known_hosts}", "-o", "ConnectTimeout=20",
               "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=2",
               "-o", "ControlMaster=auto", "-o", "ControlPersist=300",
               "-o", f"ControlPath={args.control_path}",
               f"{args.user}@{args.host}:{remote}", str(local)]
    last = None
    for attempt in range(3):
        try:
            subprocess.run(command, check=True, timeout=900); return
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            last = exc
            if attempt < 2: time.sleep(5 * (2 ** attempt))
    raise RuntimeError("bounded Wuzhen staging transfer failed") from last


def validate(path: Path, expected_bytes: int, expected_rows: int) -> dict:
    if path.stat().st_size != expected_bytes: raise RuntimeError("occurrence byte mismatch: " + str(path))
    parquet = pq.ParquetFile(path)
    if parquet.metadata.num_rows != expected_rows: raise RuntimeError("occurrence row mismatch: " + str(path))
    if set(parquet.schema_arrow.names) != EXPECTED_SCHEMA: raise RuntimeError("occurrence schema mismatch: " + str(path))
    return {"path": str(path), "bytes": expected_bytes, "rows": expected_rows,
            "row_groups": parquet.num_row_groups, "sha256": sha256(path)}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--remote-root", required=True); p.add_argument("--ks-projection-report", type=Path, required=True)
    p.add_argument("--host", required=True); p.add_argument("--port", type=int, required=True)
    p.add_argument("--user", required=True); p.add_argument("--key", type=Path, required=True)
    p.add_argument("--known-hosts", type=Path, required=True); p.add_argument("--control-path", required=True)
    p.add_argument("--stage-cap-bytes", type=int, default=4_000_000_000)
    args = p.parse_args(); output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    if sum(x[0] for x in BATCHES.values()) > args.stage_cap_bytes: raise RuntimeError("configured stage cap too small")
    receipts = []
    for batch, (expected_bytes, expected_rows) in BATCHES.items():
        directory = output / batch; directory.mkdir(exist_ok=True)
        final = directory / "occurrences.parquet"; manifest = directory / "batch_manifest.json"
        if not manifest.exists():
            partial = Path(str(manifest) + ".partial")
            scp(args, f"{args.remote_root}/{batch}/batch_manifest.json", partial); os.replace(partial, manifest)
        batch_manifest = json.loads(manifest.read_text())
        if batch_manifest["batch_id"] != batch or batch_manifest["occurrence_rows"] != expected_rows:
            raise RuntimeError(batch + ": manifest mismatch")
        if not final.exists():
            current = sum(p.stat().st_size for p in output.rglob("*") if p.is_file())
            if current + expected_bytes > args.stage_cap_bytes: raise RuntimeError("Wuzhen staging cap reached")
            partial = Path(str(final) + ".partial")
            scp(args, f"{args.remote_root}/{batch}/occurrences.parquet", partial)
            validate(partial, expected_bytes, expected_rows); os.replace(partial, final)
        receipts.append({"batch_id": batch, "manifest_sha256": sha256(manifest),
                         "occurrences": validate(final, expected_bytes, expected_rows)})
        atomic_json(output / "STAGING_PROGRESS.json", {"status": "running", "batches": receipts})

    sources = []
    projection = json.loads(args.ks_projection_report.read_text())
    for row in projection["source_counts"]:
        sources.append({"region": "kunshan", "source_file": row["source_file"], "raw_rows": row["rows"]})
    for receipt in receipts:
        manifest = json.loads((output / receipt["batch_id"] / "batch_manifest.json").read_text())
        for row in manifest["source_files"]:
            name = row["name"] if row["name"].endswith(".parquet") else row["name"] + ".parquet"
            sources.append({"region": "wuzhen", "source_file": name,
                            "raw_rows": row["fingerprint"]["runner_source"]["footer_rows"]})
    if sum(x["raw_rows"] for x in sources if x["region"] == "kunshan") != 164581116:
        raise RuntimeError("Kunshan source row conservation failed")
    if sum(x["raw_rows"] for x in sources if x["region"] == "wuzhen") != 134091962:
        raise RuntimeError("Wuzhen source row conservation failed")
    if len({(x["region"], x["source_file"]) for x in sources}) != 2464:
        raise RuntimeError("regional source identity conservation failed")
    atomic_json(output / "expected_source_rows.json", {"status": "complete", "sources": sources})
    atomic_json(output / "COMPLETE.json", {"status": "complete", "batches": receipts,
                                            "occurrence_rows": sum(x[1] for x in BATCHES.values()),
                                            "occurrence_bytes": sum(x[0] for x in BATCHES.values()),
                                            "expected_source_rows": "expected_source_rows.json"})


if __name__ == "__main__": main()
