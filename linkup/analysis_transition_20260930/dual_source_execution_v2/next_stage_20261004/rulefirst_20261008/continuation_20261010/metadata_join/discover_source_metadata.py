#!/usr/bin/env python3
"""Retrieve only small source-side inventory/control files through strict SSH."""
import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import subprocess
from pathlib import Path

ROOTS = {
    "records": "/public/home/lilysharp/linkup_analysis_v1/stage_b/records_index_v1",
    "onet": "/public/home/lilysharp/dewey_downloads/data/dewey_ONET_tables",
}
TOKENS = ("inventory", "manifest", "complete", "receipt", "metadata", "_success", "sha256")
MAX_FILE_BYTES = 20_000_000


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def run_ssh(base, command, binary=False):
    return subprocess.check_output(base + [command], text=not binary)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--credential-dir", required=True)
    ap.add_argument("--private-output", required=True)
    ap.add_argument("--public-receipt", required=True)
    args = ap.parse_args()
    cred = Path(args.credential_dir)
    private = Path(args.private_output)
    public = Path(args.public_receipt)
    if (cred.stat().st_mode & 0o077) != 0:
        raise RuntimeError("credential directory must be private")
    for name in ("source_ks_id", "known_hosts"):
        p = cred / name
        if not p.is_file() or (p.stat().st_mode & 0o077) != 0:
            raise RuntimeError("missing or non-private credential file: " + name)
    ssh = [
        "ssh", "-i", str(cred / "source_ks_id"), "-p", "65023",
        "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
        "-o", "ConnectTimeout=20", "-o", "ServerAliveInterval=20",
        "-o", "ServerAliveCountMax=3",
        "-o", "UserKnownHostsFile=" + str(cred / "known_hosts"),
        "cancon.hpccube.com",
    ]
    private.mkdir(parents=True, exist_ok=True)
    os.chmod(private, 0o700)
    discovered = []
    retrieved = []
    for kind, root in ROOTS.items():
        # Discovery is bounded to control files near the known roots; Parquet is excluded.
        cmd = "find %s -maxdepth 2 -type f ! -name '*.parquet' -printf '%%s\\t%%p\\n'" % shlex.quote(root)
        lines = run_ssh(ssh, cmd).splitlines()
        for line in lines:
            size_text, path = line.split("\t", 1)
            size = int(size_text)
            discovered.append({"source_kind": kind, "path": path, "bytes": size})
            low = Path(path).name.lower()
            if size > MAX_FILE_BYTES or not any(token in low for token in TOKENS):
                continue
            data = run_ssh(ssh, "cat -- " + shlex.quote(path), binary=True)
            if len(data) != size:
                raise RuntimeError("source metadata size changed during read: " + path)
            rel = "%s_%04d_%s" % (kind, len(retrieved) + 1, Path(path).name)
            dest = private / rel
            dest.write_bytes(data)
            os.chmod(dest, 0o600)
            text = data.decode("utf-8", "replace")
            retrieved.append({
                "source_kind": kind,
                "source_path": path,
                "bytes": size,
                "sha256": sha256(dest),
                "stored_name": rel,
                "contains_sha256_label": "sha256" in text.lower(),
                "sha256_hex_token_count": sum(
                    1 for token in text.replace('"', ' ').replace("'", " ").split()
                    if len(token.strip(" ,:[]{}")) == 64
                    and all(c in "0123456789abcdefABCDEF" for c in token.strip(" ,:[]{}"))
                ),
            })
    private_inventory = private / "SOURCE_METADATA_DISCOVERY_PRIVATE.json"
    private_inventory.write_text(json.dumps({"discovered_nonparquet": discovered, "retrieved": retrieved}, indent=2, sort_keys=True) + "\n")
    os.chmod(private_inventory, 0o600)
    receipt = {
        "version": "d59-source-metadata-discovery-v1",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "complete",
        "scope": "maxdepth2 small metadata/control-file discovery; Parquet excluded; no raw table analysis",
        "roots": ROOTS,
        "discovered_nonparquet_files": len(discovered),
        "retrieved_candidate_files": len(retrieved),
        "retrieved_candidate_bytes": sum(x["bytes"] for x in retrieved),
        "retrieved_files": retrieved,
        "private_inventory_sha256": sha256(private_inventory),
        "per_file_sha_inventory_candidate_found": any(
            x["contains_sha256_label"] or x["sha256_hex_token_count"] > 0 for x in retrieved
        ),
    }
    public.parent.mkdir(parents=True, exist_ok=True)
    public.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
