#!/usr/bin/env python3
"""Cloud-resident, resumable source staging with exclusive per-shard locks."""
import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

VERSION = "d59-cloud-staging-v1"


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def tree_bytes(root):
    return sum(p.stat().st_size for p in Path(root).rglob("*") if p.is_file())


def require_private_credentials(root):
    root = Path(root)
    if not root.is_dir() or stat.S_IMODE(root.stat().st_mode) & 0o077:
        raise RuntimeError("credential directory permissions are not private")
    for name in ("source_ks_id", "source_wz_id", "known_hosts"):
        path = root/name
        mode = path.stat().st_mode
        if not stat.S_ISREG(mode) or stat.S_IMODE(mode) & 0o077:
            raise RuntimeError("credential file permissions are not private: " + name)


def missing_transfer_bytes(stage, entries):
    total = 0
    for e in entries:
        final = stage/"ready"/e["shard_id"]
        if final.exists() and validated_ready(final, e):
            continue
        partial = stage/"partial"/e["shard_id"]
        for path, expected in (
                (partial/(e["source_file"] + ".partial"), e["source_bytes"]),
                (partial/(e["shard_id"] + ".sidecar.parquet.partial"), e["sidecar_bytes"])):
            size = path.stat().st_size if path.exists() else 0
            if size > expected:
                raise RuntimeError("oversize partial blocks admission")
            total += expected - size
    return total


def validated_ready(final, entry):
    receipt = final / "STAGING_RECEIPT_PUBLIC.json"
    try:
        r = json.loads(receipt.read_text())
        raw = final / entry["source_file"]
        side = final / (entry["shard_id"] + ".sidecar.parquet")
        return (r.get("status") == "complete"
                and r.get("source_sha256") == entry["source_sha256_cached"]
                and r.get("sidecar_sha256") == entry["sidecar_sha256"]
                and raw.stat().st_size == entry["source_bytes"]
                and side.stat().st_size == entry["sidecar_bytes"]
                and digest(raw) == entry["source_sha256_cached"]
                and digest(side) == entry["sidecar_sha256"])
    except (OSError, ValueError, KeyError):
        return False


def transfer(entry, kind, partial, expected_size, expected_sha, ssh_base):
    remote = entry["source_path"] if kind == "raw" else entry["sidecar_path"]
    partial.parent.mkdir(parents=True, exist_ok=True)
    size = partial.stat().st_size if partial.exists() else 0
    if size > expected_size:
        bad = Path(str(partial) + ".oversize")
        if bad.exists():
            raise RuntimeError("oversize quarantine already exists")
        os.replace(partial, bad); size = 0
    if size < expected_size:
        command = ssh_base + ["tail -c +%d -- %s" % (size + 1, shlex.quote(remote))]
        last_rc = None
        for attempt in range(1, 4):
            with open(partial, "ab") as target:
                proc = subprocess.run(command, stdout=target)
            last_rc = proc.returncode
            if last_rc == 0:
                break
            size = partial.stat().st_size if partial.exists() else 0
            command = ssh_base + ["tail -c +%d -- %s" % (size + 1, shlex.quote(remote))]
        if last_rc:
            raise RuntimeError("%s transfer ssh exit=%d after max3 transient attempts" % (kind, last_rc))
    actual_size = partial.stat().st_size
    if actual_size != expected_size:
        raise RuntimeError("%s transfer size=%d expected=%d" % (kind, actual_size, expected_size))
    actual_sha = digest(partial)
    if actual_sha != expected_sha:
        bad = Path(str(partial) + ".hash_mismatch")
        if bad.exists():
            raise RuntimeError("hash-mismatch quarantine already exists")
        os.replace(partial, bad)
        raise RuntimeError("%s transfer digest mismatch" % kind)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True)
    p.add_argument("--stage-root", required=True)
    p.add_argument("--credential-dir", required=True)
    p.add_argument("--cap-bytes", type=int, required=True)
    p.add_argument("--public-receipt", required=True)
    a = p.parse_args()
    manifest = json.loads(Path(a.manifest).read_text())
    script_sha = digest(__file__)
    manifest_sha = digest(a.manifest)
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("manifest entries missing")
    if len({x["shard_id"] for x in entries}) != len(entries):
        raise RuntimeError("duplicate shard_id in staging manifest")
    expected = sum(x["source_bytes"] + x["sidecar_bytes"] for x in entries)
    if expected > a.cap_bytes:
        raise RuntimeError("batch exceeds staging cap")
    stage = Path(a.stage_root)
    locks, partials, ready = stage/"locks", stage/"partial", stage/"ready"
    for path in (locks, partials, ready):
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
    current_bytes = tree_bytes(stage)
    missing_bytes = missing_transfer_bytes(stage, entries)
    if current_bytes > a.cap_bytes:
        raise RuntimeError("existing staging tree already exceeds cap")
    if current_bytes + missing_bytes > a.cap_bytes:
        raise RuntimeError("current staging plus admitted missing bytes exceeds cap")
    credentials = Path(a.credential_dir)
    require_private_credentials(credentials)
    endpoints = {
        "kunshan": ("cancon.hpccube.com", "65023", credentials/"source_ks_id"),
        "wuzhen": ("wuzh02.hpccube.com", "65091", credentials/"source_wz_id"),
    }
    results = []
    for entry in entries:
        sid = entry["shard_id"]; final = ready/sid
        if final.exists():
            if not validated_ready(final, entry):
                raise RuntimeError("published ready shard fails identity check: " + sid)
            results.append({"shard_id": sid[:16], "status": "resumed_ready",
                            "bytes": entry["source_bytes"] + entry["sidecar_bytes"]})
            continue
        lock = locks/(sid + ".lock")
        try:
            lock.mkdir()
        except FileExistsError:
            raise RuntimeError("exclusive staging lock already held: " + sid)
        try:
            current_bytes = tree_bytes(stage)
            remaining = missing_transfer_bytes(stage, [entry])
            if current_bytes + remaining > a.cap_bytes:
                raise RuntimeError("per-shard admission would exceed staging cap")
            if entry["region"] not in endpoints:
                raise RuntimeError("unsupported source region")
            host, port, key = endpoints[entry["region"]]
            ssh_base = ["ssh", "-i", str(key), "-p", port, "-o", "BatchMode=yes",
                        "-o", "StrictHostKeyChecking=yes", "-o",
                        "UserKnownHostsFile=" + str(credentials/"known_hosts"),
                        "-o", "ConnectTimeout=20", "-o", "ServerAliveInterval=20", "-o", "ServerAliveCountMax=3", "lilysharp@" + host]
            shard_partial = partials/sid
            shard_partial.mkdir(parents=True, exist_ok=True)
            raw_partial = shard_partial/(entry["source_file"] + ".partial")
            side_partial = shard_partial/(sid + ".sidecar.parquet.partial")
            transfer(entry, "raw", raw_partial, entry["source_bytes"],
                     entry["source_sha256_cached"], ssh_base)
            transfer(entry, "sidecar", side_partial, entry["sidecar_bytes"],
                     entry["sidecar_sha256"], ssh_base)
            temp = ready/("." + sid + ".tmp." + str(os.environ.get("JOB_ID", os.getpid())))
            temp.mkdir()
            raw_final = temp/entry["source_file"]
            side_final = temp/(sid + ".sidecar.parquet")
            os.replace(raw_partial, raw_final); os.replace(side_partial, side_final)
            receipt = {
                "status": "complete", "version": VERSION, "shard_id": sid[:16],
                "source_file": entry["source_file"], "raw_rows": entry["raw_rows"],
                "source_bytes": entry["source_bytes"], "sidecar_bytes": entry["sidecar_bytes"],
                "source_sha256": entry["source_sha256_cached"],
                "sidecar_sha256": entry["sidecar_sha256"],
                "source_region": entry["region"], "source_preserved": True,
                "stage_script_sha256": script_sha, "manifest_sha256": manifest_sha,
                "staging_cap_bytes": a.cap_bytes,
                "stage_tree_bytes_at_receipt": tree_bytes(stage),
                "job_id": os.environ.get("JOB_ID"),
                "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            }
            atomic_json(temp/"STAGING_RECEIPT_PUBLIC.json", receipt)
            os.replace(temp, final)
            try:
                shard_partial.rmdir()
            except OSError:
                pass
            results.append({"shard_id": sid[:16], "status": "staged",
                            "bytes": entry["source_bytes"] + entry["sidecar_bytes"]})
        finally:
            try:
                lock.rmdir()
            except OSError:
                pass
    aggregate = {
        "status": "complete", "version": VERSION, "batch_id": manifest["batch_id"],
        "stage_script_sha256": script_sha, "manifest_sha256": manifest_sha,
        "shard_count": len(entries), "expected_file_bytes": expected,
        "stage_tree_bytes": tree_bytes(stage), "cap_bytes": a.cap_bytes,
        "results": results, "job_id": os.environ.get("JOB_ID"),
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "credential_policy": "private identities outside code/release; no secret values logged",
    }
    atomic_json(a.public_receipt, aggregate)


if __name__ == "__main__":
    main()
