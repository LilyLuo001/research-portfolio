#!/usr/bin/env python3
"""Wait for regional publication, run the global gate, and stage receipt metadata."""
import fcntl
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import tarfile
import time
from pathlib import Path

ROOT = Path("/public/home/lilysharp/linkup_release_v1/semantic_v1")
KS = ROOT / "kunshan"
CP = KS / "checkpoints"
RELEASE = Path("/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1")
PYTHON = "/public/software/apps/python/3.8.10/bin/python3"
TARGET = "/public/home/lilysharp/linkup_analysis_execution_oct02/private/published_receipts"
STATUS = CP / "FINAL_PUBLICATION_ARCHIVE_SUPERVISOR.json"


def atomic(path, value):
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def run(argv, timeout):
    return subprocess.run(argv, check=True, timeout=timeout, universal_newlines=True,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT).stdout


def validate_ks_receipts():
    plan = [json.loads(x) for x in (KS / "plan.jsonl").read_text().splitlines() if x.strip()]
    if len(plan) != 1358 or len({x["shard_id"] for x in plan}) != 1358:
        raise RuntimeError("Kunshan frozen plan mismatch")
    for row in plan:
        sid = row["shard_id"]
        receipt = json.loads((CP / (sid + ".published.json")).read_text())
        complete = receipt.get("shard_complete", {})
        accounting = complete.get("accounting", {})
        if receipt.get("status") != "published_verified" or receipt.get("shard_id") != sid:
            raise RuntimeError(sid + ": invalid published receipt")
        for key in ("source_file", "source_bytes", "source_sha256_cached", "sidecar_sha256", "raw_rows"):
            if accounting.get(key) != row.get(key):
                raise RuntimeError(sid + ": accounting mismatch: " + key)
        if sum(accounting.get("disposition_counts", {}).values()) != row["raw_rows"] or not accounting.get("row_conservation"):
            raise RuntimeError(sid + ": row conservation failure")


def make_archive():
    wz_cp = ROOT / "final_gate_wuzhen" / "checkpoints"
    stage = ROOT / "receipt_archive_20261003"
    if stage.exists():
        shutil.move(str(stage), str(stage) + ".previous.%d" % int(time.time()))
    stage.mkdir(parents=True)
    (stage / "_plans").mkdir()
    (stage / "_gate").mkdir()
    ks_receipts = sorted(CP.glob("*.published.json"))
    wz_receipts = sorted(wz_cp.glob("*.published.json"))
    if (len(ks_receipts), len(wz_receipts)) != (1358, 1106):
        raise RuntimeError("receipt archive counts are not 1358+1106")
    ks_names = {p.name for p in ks_receipts}
    wz_names = {p.name for p in wz_receipts}
    if ks_names & wz_names:
        raise RuntimeError("cross-region receipt filename collision")
    for source in ks_receipts:
        shutil.copy2(str(source), str(stage / source.name))
    for source in wz_receipts:
        shutil.copy2(str(source), str(stage / source.name))
    shutil.copy2(str(KS / "plan.jsonl"), str(stage / "_plans" / "kunshan.plan.jsonl"))
    shutil.copy2(str(ROOT / "final_gate_wuzhen" / "plan.jsonl"), str(stage / "_plans" / "wuzhen.plan.jsonl"))
    shutil.copy2(str(ROOT / "ALL_REGIONS_VERIFIED_COMPLETE.json"), str(stage / "_gate" / "ALL_REGIONS_VERIFIED_COMPLETE.json"))
    files = []
    for path in sorted(stage.rglob("*")):
        if path.is_file():
            files.append({"path": str(path.relative_to(stage)), "bytes": path.stat().st_size, "sha256": sha(path)})
    manifest = {"status": "complete", "kunshan_receipts": 1358, "wuzhen_receipts": 1106,
                "total_receipts": 2464, "files": files, "created_at": time.time()}
    atomic(stage / "ARCHIVE_MANIFEST.json", manifest)
    archive = ROOT / "receipt_archive_20261003.tar.gz"
    temp = Path(str(archive) + ".tmp")
    with tarfile.open(str(temp), "w:gz") as handle:
        handle.add(str(stage), arcname="published_receipts")
    os.replace(temp, archive)
    return archive, sha(archive), manifest


def stage_hz(archive, archive_sha):
    ssh_base = ["ssh", "-T", "-p", "65032", "-i", "/public/home/lilysharp/.ssh/hz_transfer_20260928",
                "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
                "-o", "UserKnownHostsFile=/public/home/lilysharp/.ssh/hz_known_hosts_20260928",
                "-o", "ProxyCommand=/public/home/lilysharp/linkup_release_v1/hz_proxy_command.sh",
                "-o", "ControlMaster=auto", "-o", "ControlPersist=300",
                "-o", "ControlPath=/tmp/linkup-hz-finalarchive-%r-%h-%p", "lilysharp@zzeshell.scnet.cn"]
    remote_tar = TARGET + ".tar.gz.partial"
    preflight = "from pathlib import Path; import os,time; p=Path(%r); p.parent.mkdir(parents=True,exist_ok=True); p.exists() and os.replace(str(p),str(p)+'.stale.'+str(int(time.time())))" % remote_tar
    run(ssh_base + ["python3 -c " + shlex.quote(preflight)], 180)
    scp = ["scp", "-q", "-P", "65032", "-i", "/public/home/lilysharp/.ssh/hz_transfer_20260928",
           "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
           "-o", "UserKnownHostsFile=/public/home/lilysharp/.ssh/hz_known_hosts_20260928",
           "-o", "ProxyCommand=/public/home/lilysharp/linkup_release_v1/hz_proxy_command.sh",
           "-o", "ControlMaster=auto", "-o", "ControlPersist=300",
           "-o", "ControlPath=/tmp/linkup-hz-finalarchive-%r-%h-%p", str(archive),
           "lilysharp@zzeshell.scnet.cn:" + remote_tar]
    run(scp, 1800)
    program = r'''import hashlib,json,os,shutil,sys,tarfile,time
from pathlib import Path
target=Path(sys.argv[1]); archive=Path(sys.argv[2]); expected_sha=sys.argv[3]
h=hashlib.sha256()
with archive.open('rb') as f:
 for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
if h.hexdigest()!=expected_sha: raise SystemExit('archive transfer sha mismatch')
temp=Path(str(target)+'.extracting');
if temp.exists(): shutil.move(str(temp),str(temp)+'.stale.'+str(int(time.time())))
temp.mkdir(parents=True)
with tarfile.open(str(archive),'r:gz') as t: t.extractall(str(temp))
root=temp/'published_receipts'; manifest=json.loads((root/'ARCHIVE_MANIFEST.json').read_text())
if manifest.get('total_receipts')!=2464: raise SystemExit('receipt count marker mismatch')
expected={x['path'] for x in manifest['files']}|{'ARCHIVE_MANIFEST.json'}
actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()}
if actual!=expected: raise SystemExit('archive file set mismatch')
for item in manifest['files']:
 p=root/item['path']; hh=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): hh.update(b)
 if p.stat().st_size!=item['bytes'] or hh.hexdigest()!=item['sha256']: raise SystemExit('archive file mismatch: '+item['path'])
if target.exists(): shutil.move(str(target),str(target)+'.previous.'+str(int(time.time())))
os.replace(str(root),str(target))
# Publish the frozen plans and accepted global marker at the consumer's
# established private-directory paths only after the verified receipt tree is live.
for source_name,dest_name in (('_plans/kunshan.plan.jsonl','kunshan.plan.jsonl'),
                              ('_plans/wuzhen.plan.jsonl','wuzhen.plan.jsonl'),
                              ('_gate/ALL_REGIONS_VERIFIED_COMPLETE.json','ALL_REGIONS_VERIFIED_COMPLETE.json')):
 source=target/source_name; dest=target.parent/dest_name; partial=Path(str(dest)+'.partial')
 shutil.copy2(str(source),str(partial)); os.replace(str(partial),str(dest))
shutil.rmtree(temp); archive.unlink()
print(json.dumps({'status':'complete','target':str(target),'receipts':2464,'archive_sha256':expected_sha}))'''
    return json.loads(run(ssh_base + ["python3 -c %s %s" %
                                      (shlex.quote(program), " ".join(shlex.quote(x) for x in (TARGET, remote_tar, archive_sha)))], 1800))


def main():
    supervisor_lock = (CP / "final-publication-archive-supervisor.lock").open("a+")
    try:
        fcntl.flock(supervisor_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise SystemExit("final publication/archive supervisor already active")
    atomic(STATUS, {"status": "waiting_for_kunshan_publication", "started_at": time.time()})
    deadline = time.time() + 2 * 24 * 3600
    while time.time() < deadline:
        if (CP / "REGION_PUBLISHED_COMPLETE.json").is_file():
            break
        time.sleep(30)
    else:
        raise TimeoutError("Kunshan publication marker deadline")
    validate_ks_receipts()
    atomic(STATUS, {"status": "running_global_gate", "at": time.time()})
    last_error = None
    for attempt in range(1, 6):
        archive_dir = ROOT / "final_gate_wuzhen"
        if archive_dir.exists():
            shutil.move(str(archive_dir), str(archive_dir) + ".previous.%d.attempt%d" % (int(time.time()), attempt))
        result = subprocess.run([PYTHON, str(RELEASE / "final_receipt_gate.py")], universal_newlines=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        if result.returncode == 0 and (ROOT / "ALL_REGIONS_VERIFIED_COMPLETE.json").is_file():
            break
        last_error = result.stdout[-4000:]
        atomic(STATUS, {"status": "global_gate_retry", "attempt": attempt, "last_error": last_error, "at": time.time()})
        time.sleep(min(600, 60 * (2 ** (attempt - 1))))
    else:
        raise RuntimeError("global gate failed after retries: " + str(last_error))
    gate = json.loads((ROOT / "ALL_REGIONS_VERIFIED_COMPLETE.json").read_text())
    if gate.get("status") != "complete" or gate.get("total_shards") != 2464 or not gate.get("final_publication_complete"):
        raise RuntimeError("global gate marker invalid")
    atomic(STATUS, {"status": "building_receipt_archive", "at": time.time()})
    archive, archive_sha, manifest = make_archive()
    hz = stage_hz(archive, archive_sha)
    atomic(STATUS, {"status": "complete", "global_gate": gate, "archive_manifest_sha256": sha(ROOT / "receipt_archive_20261003" / "ARCHIVE_MANIFEST.json"),
                    "archive_files": len(manifest["files"]), "hz": hz, "finished_at": time.time()})


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        atomic(STATUS, {"status": "failed", "type": type(exc).__name__, "error": str(exc), "at": time.time()})
        raise
