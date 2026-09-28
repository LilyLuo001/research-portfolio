#!/usr/bin/env python3
"""Publish one generated shard to a remote sink with exact verification."""
from __future__ import annotations

import argparse, hashlib, json, os, re, shlex, shutil, subprocess
from pathlib import Path
import pyarrow.parquet as pq


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def run(argv: list[str], capture: bool, timeout: int) -> str:
    result = subprocess.run(argv, check=True, text=True, timeout=timeout,
                            stdout=subprocess.PIPE if capture else None)
    return result.stdout if capture else ""


def ssh_argv(args, command: str) -> list[str]:
    argv = ["ssh", "-T", "-p", str(args.port), "-i", str(args.key),
            "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
            "-o", f"UserKnownHostsFile={args.known_hosts}",
            "-o", "ConnectTimeout=20", "-o", "ServerAliveInterval=15",
            "-o", "ServerAliveCountMax=2"]
    if args.control_path:
        argv += ["-o", "ControlMaster=auto", "-o", "ControlPersist=300",
                 "-o", f"ControlPath={args.control_path}"]
    return argv + [f"{args.user}@{args.host}", command]


def local_manifest(source: Path) -> dict:
    files = []
    for path in sorted(source.rglob("*")):
        if not path.is_file() or path.name == "TRANSFER_MANIFEST.json":
            continue
        item = {"path": path.relative_to(source).as_posix(),
                "bytes": path.stat().st_size, "sha256": sha256(path)}
        if path.suffix == ".parquet":
            parquet = pq.ParquetFile(path)
            item["parquet"] = {"rows": parquet.metadata.num_rows,
                               "row_groups": parquet.num_row_groups,
                               "schema": str(parquet.schema_arrow)}
        files.append(item)
    return {"version": 1, "files": files,
            "total_bytes": sum(item["bytes"] for item in files)}


REMOTE_LIBRARY = r'''
import fcntl,hashlib,json,os,shutil,sys
from pathlib import Path
def verify(root,expected_manifest_sha):
 manifest_bytes=(root/'TRANSFER_MANIFEST.json').read_bytes()
 manifest_sha=hashlib.sha256(manifest_bytes).hexdigest()
 if manifest_sha!=expected_manifest_sha: raise SystemExit('remote/local manifest mismatch')
 manifest=json.loads(manifest_bytes)
 expected=set(x['path'] for x in manifest['files'])|{'TRANSFER_MANIFEST.json'}
 actual=set(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file())
 if actual!=expected: raise SystemExit('remote file-set mismatch')
 for item in manifest['files']:
  p=root/item['path']
  if not p.is_file() or p.stat().st_size!=item['bytes']: raise SystemExit('byte mismatch: '+item['path'])
  h=hashlib.sha256()
  with p.open('rb') as handle:
   for block in iter(lambda:handle.read(1024*1024),b''): h.update(block)
  if h.hexdigest()!=item['sha256']: raise SystemExit('sha mismatch: '+item['path'])
 return {'files':len(manifest['files']),'bytes':manifest['total_bytes'],'manifest_sha256':manifest_sha}
def ledger_open(root,cap):
 lock=(root/'.storage.lock').open('a+'); fcntl.flock(lock,fcntl.LOCK_EX)
 path=root/'STORAGE_LEDGER.json'
 ledger=json.loads(path.read_text()) if path.exists() else {'cap_bytes':cap,'reserved':{},'published':{}}
 if ledger.get('cap_bytes')!=cap: raise SystemExit('remote cap changed')
 return lock,path,ledger
def ledger_write(path,ledger):
 used=sum(ledger['reserved'].values())+sum(ledger['published'].values())
 if used>ledger['cap_bytes']: raise SystemExit('remote release cap exceeded')
 temp=Path(str(path)+'.tmp'); temp.write_text(json.dumps(ledger,indent=2,sort_keys=True)+'\n'); os.replace(temp,path)
 return used
'''

REMOTE_BEGIN = REMOTE_LIBRARY + r'''
root=Path(sys.argv[1]).resolve(); shard=sys.argv[2]; amount=int(sys.argv[3]); cap=int(sys.argv[4]); expected=sys.argv[5]
root.mkdir(parents=True,exist_ok=True)
partial=root/(shard+'.partial'); uploading=root/(shard+'.partial.uploading'); final=root/shard
for p in (partial,uploading,final):
 if p.parent!=root: raise SystemExit('unsafe shard path')
lock,ledger_path,ledger=ledger_open(root,cap)
known=ledger['reserved'].get(shard,ledger['published'].get(shard))
if known is not None and known!=amount: raise SystemExit('shard byte reservation changed')
if final.exists():
 result=verify(final,expected); ledger['reserved'].pop(shard,None); ledger['published'][shard]=amount
 result.update({'action':'existing_verified','accounted_bytes':ledger_write(ledger_path,ledger)}); print(json.dumps(result)); raise SystemExit(0)
ledger['reserved'][shard]=amount
accounted=ledger_write(ledger_path,ledger)
for p in (partial,uploading):
 if p.exists(): shutil.rmtree(p)
print(json.dumps({'action':'upload','accounted_bytes':accounted}))
'''

REMOTE_COMMIT = REMOTE_LIBRARY + r'''
root=Path(sys.argv[1]).resolve(); shard=sys.argv[2]; amount=int(sys.argv[3]); cap=int(sys.argv[4]); expected=sys.argv[5]
partial=root/(shard+'.partial'); uploading=root/(shard+'.partial.uploading'); final=root/shard
result=verify(uploading,expected)
if final.exists(): raise SystemExit('final appeared during upload')
os.replace(uploading,partial); os.replace(partial,final)
if verify(final,expected)!=result: raise SystemExit('verification changed after publish')
lock,ledger_path,ledger=ledger_open(root,cap)
if ledger['reserved'].get(shard)!=amount: raise SystemExit('missing/mismatched reservation')
ledger['reserved'].pop(shard,None); ledger['published'][shard]=amount
result.update({'action':'published_verified','accounted_bytes':ledger_write(ledger_path,ledger)})
print(json.dumps(result))
'''


def remote_call(args, program: str, values: list[str]) -> dict:
    command = "python3 -c %s %s" % (shlex.quote(program), " ".join(shlex.quote(v) for v in values))
    output = run(ssh_argv(args, command), True, args.command_timeout_seconds)
    return json.loads(output)


def write_receipt(args, source: Path, result: dict, manifest_sha: str,
                  complete_sha: str, complete: dict) -> None:
    receipt = {"status": "published_verified", "shard_id": args.shard_id,
               "remote_path": args.remote_root.rstrip("/") + "/" + args.shard_id,
               "files": result["files"], "bytes": result["bytes"],
               "source_manifest_sha256": manifest_sha,
               "shard_complete_sha256": complete_sha, "shard_complete": complete,
               "remote_storage_accounted_bytes": result["accounted_bytes"],
               "source_deleted_after_verification": True}
    atomic_json(args.local_receipt.resolve(), receipt)
    shutil.rmtree(source)
    print(json.dumps(receipt, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--allowed-source-root", type=Path, required=True)
    parser.add_argument("--local-receipt", type=Path, required=True)
    parser.add_argument("--host", required=True); parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--user", required=True); parser.add_argument("--key", type=Path, required=True)
    parser.add_argument("--known-hosts", type=Path, required=True)
    parser.add_argument("--control-path")
    parser.add_argument("--remote-root", required=True); parser.add_argument("--shard-id", required=True)
    parser.add_argument("--remote-cap-bytes", type=int, default=420_000_000_000)
    parser.add_argument("--command-timeout-seconds", type=int, default=180)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.shard_id):
        raise ValueError("shard_id must be a safe path component")
    source = args.source.resolve(); allowed = args.allowed_source_root.resolve()
    if source == allowed or allowed not in source.parents or source.is_symlink():
        raise ValueError("generated source must be a non-symlink child of allowed source root")
    if not (source / "SHARD_COMPLETE.json").is_file():
        raise ValueError("SHARD_COMPLETE.json required before transfer")
    for path, label in ((args.key, "transfer key"), (args.known_hosts, "dedicated known_hosts")):
        if not path.is_file() or (path.stat().st_mode & 0o077):
            raise ValueError(label + " missing or permissions are not 0600-style")

    transfer = local_manifest(source)
    atomic_json(source / "TRANSFER_MANIFEST.json", transfer)
    manifest_sha = sha256(source / "TRANSFER_MANIFEST.json")
    complete_sha = sha256(source / "SHARD_COMPLETE.json")
    complete = json.loads((source / "SHARD_COMPLETE.json").read_text())
    accounted = sum(p.stat().st_size for p in source.rglob("*") if p.is_file())
    if accounted > args.remote_cap_bytes: raise ValueError("single shard exceeds remote cap")
    values = [args.remote_root, args.shard_id, str(accounted), str(args.remote_cap_bytes), manifest_sha]
    begin = remote_call(args, REMOTE_BEGIN, values)
    if begin["action"] == "existing_verified":
        write_receipt(args, source, begin, manifest_sha, complete_sha, complete); return
    if begin["action"] != "upload": raise RuntimeError("unknown remote begin action")

    uploading = args.remote_root.rstrip("/") + "/" + args.shard_id + ".partial.uploading"
    scp = ["scp", "-q", "-r", "-P", str(args.port), "-i", str(args.key),
           "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
           "-o", f"UserKnownHostsFile={args.known_hosts}", "-o", "ConnectTimeout=20",
           "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=2"]
    if args.control_path:
        scp += ["-o", "ControlMaster=auto", "-o", "ControlPersist=300",
                "-o", f"ControlPath={args.control_path}"]
    scp += [str(source), f"{args.user}@{args.host}:{uploading}"]
    run(scp, False, args.command_timeout_seconds)
    committed = remote_call(args, REMOTE_COMMIT, values)
    if committed["action"] != "published_verified": raise RuntimeError("remote commit did not publish")
    write_receipt(args, source, committed, manifest_sha, complete_sha, complete)


if __name__ == "__main__": main()
