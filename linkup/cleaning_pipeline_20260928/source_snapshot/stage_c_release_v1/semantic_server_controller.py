#!/usr/bin/env python3
"""Unattended fail-closed bridge from disposition completion to regional release."""
import fcntl, hashlib, json, os, shutil, subprocess, time
from pathlib import Path

PREP = Path("/public/home/lilysharp/linkup_release_v1/disposition_prep_v1")
PREP_CONTROL = PREP / "continuation"
STATE = Path("/public/home/lilysharp/linkup_release_v1/semantic_v1")
KS = STATE / "kunshan"
KS_RELEASE = Path("/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1")
WZ_HOME = "/work/home/lilysharp"
WZ_STATE = WZ_HOME + "/linkup_release_v1/semantic_v1/wuzhen"
WZ_RELEASE = WZ_HOME + "/linkup_analysis_v1/stage_c_release_v1"
WZ_SSH_BASE = ["-p", "65091", "-i", "/public/home/lilysharp/.ssh/scnet_wuzhen_lilysharp",
               "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
               "-o", "UserKnownHostsFile=/public/home/lilysharp/.ssh/wz_known_hosts_20260928",
               "-o", "ConnectTimeout=20", "-o", "ServerAliveInterval=15", "-o", "ServerAliveCountMax=2",
               "-o", "ControlMaster=auto", "-o", "ControlPersist=300",
               "-o", "ControlPath=/tmp/linkup-wz-semantic-%r-%h-%p"]


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp"); temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def run(argv, timeout=120, check=True):
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, timeout=timeout, check=check)


def wz(command, timeout=120, check=True):
    return run(["ssh", "-T"] + WZ_SSH_BASE + ["lilysharp@wuzh02.hpccube.com", command], timeout, check)


def parse_job_id(stdout):
    found = []
    for line in stdout.splitlines():
        token = line.strip().split(";", 1)[0]
        if token.isdigit(): found.append(token)
    return found[0] if len(set(found)) == 1 else None


def parse_named_jobs(text, name):
    jobs = set()
    for line in text.splitlines():
        fields = line.strip().split("|")
        if len(fields) >= 2 and fields[0].isdigit() and fields[1] == name:
            jobs.add(fields[0])
    return jobs


def local_jobs(name):
    active = run(["squeue", "-h", "-n", name, "-o", "%A|%.128j"], check=True).stdout
    history = run(["sacct", "-nX", "-P", "-S", "2026-09-28",
                   "-o", "JobIDRaw,JobName%128"], check=True).stdout
    return sorted(parse_named_jobs(active, name) | parse_named_jobs(history, name), key=int)


def wz_jobs(name):
    active = wz("squeue -h -n %s -o '%%A|%%.128j'" % name).stdout
    history = wz("sacct -nX -P -S 2026-09-28 -o JobIDRaw,JobName%128").stdout
    return sorted(parse_named_jobs(active, name) | parse_named_jobs(history, name), key=int)


def prep_active():
    handle = (PREP_CONTROL / "continuation.lock").open("a+")
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB); fcntl.flock(handle, fcntl.LOCK_UN); return False
    except BlockingIOError:
        return True
    finally:
        handle.close()


def wait_prep():
    complete = PREP_CONTROL / "COMPLETE.json"
    deadline = time.time() + 4 * 24 * 3600
    while time.time() < deadline:
        if complete.is_file():
            doc = json.loads(complete.read_text())
            if doc.get("status") != "complete": raise RuntimeError("invalid prep complete marker")
            return doc
        if not prep_active() and ((PREP_CONTROL / "PAUSED.json").exists() or (PREP_CONTROL / "FAILED.json").exists()):
            atomic_json(STATE / "SEMANTIC_CONTROLLER_PAUSED.json",
                        {"status": "prep_terminal_without_complete", "at": time.time()})
            raise SystemExit(75)
        time.sleep(60)
    raise TimeoutError("prep controller deadline")


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()


def write_jsonl(path, rows):
    path.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in rows))


def split_balanced(rows, count=2):
    """Deterministic raw-row-balanced, mutually exclusive plan split."""
    parts = [[] for _ in range(count)]; totals = [0] * count
    for row in sorted(rows, key=lambda x: (-int(x["raw_rows"]), x["shard_id"])):
        target = min(range(count), key=lambda i: (totals[i], i))
        parts[target].append(row); totals[target] += int(row["raw_rows"])
    full_ids = {x["shard_id"] for x in rows}
    part_ids = [{x["shard_id"] for x in part} for part in parts]
    if len(full_ids) != len(rows) or set().union(*part_ids) != full_ids:
        raise RuntimeError("partition union differs from full plan")
    if any(part_ids[i] & part_ids[j] for i in range(count) for j in range(i + 1, count)):
        raise RuntimeError("partition plans overlap")
    return parts


def prepare_plans():
    combined = PREP / "regional_runner_plan.jsonl"
    rows = [json.loads(line) for line in combined.read_text().splitlines() if line.strip()]
    by_region = {"kunshan": [], "wuzhen": []}
    for row in rows:
        by_region[row["region"]].append(row)
        sidecar = Path(row["sidecar_path"])
        if sidecar.stat().st_size != row["sidecar_bytes"] or sha256(sidecar) != row["sidecar_sha256"]:
            raise RuntimeError("sidecar identity mismatch before regional distribution")
    if len(by_region["kunshan"]) != 1358 or len(by_region["wuzhen"]) != 1106:
        raise RuntimeError("regional plan shard counts differ")
    KS.mkdir(parents=True, exist_ok=True)
    full_plan = KS / "plan.jsonl"; write_jsonl(full_plan, by_region["kunshan"])
    ks_parts = split_balanced(by_region["kunshan"], 2)
    part_paths = []
    for index, part in enumerate(ks_parts):
        path = KS / ("plan.part%d.jsonl" % index); write_jsonl(path, part); part_paths.append(path)
    manifest = {
        "status": "complete", "full_plan": str(full_plan),
        "full_plan_sha256": sha256(full_plan), "full_shards": len(by_region["kunshan"]),
        "full_raw_rows": sum(int(x["raw_rows"]) for x in by_region["kunshan"]),
        "partitions": [{"partition_id": "part%d" % i, "path": str(path),
                        "sha256": sha256(path), "shards": len(ks_parts[i]),
                        "raw_rows": sum(int(x["raw_rows"]) for x in ks_parts[i])}
                       for i, path in enumerate(part_paths)],
    }
    atomic_json(KS / "partition_manifest.json", manifest)
    wz_rows = []
    for row in by_region["wuzhen"]:
        row = dict(row); row["sidecar_path"] = WZ_STATE + "/sidecars/" + Path(row["sidecar_path"]).name; wz_rows.append(row)
    local_wz_plan = STATE / "wuzhen_plan.jsonl"
    local_wz_plan.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in wz_rows))
    return by_region["kunshan"], part_paths, wz_rows, local_wz_plan


def promote_ks_compute_complete(full_plan, part_paths, checkpoints):
    """Publish one global compute marker only after both disjoint parts finish."""
    full_rows = [json.loads(x) for x in Path(full_plan).read_text().splitlines() if x.strip()]
    full_ids = {x["shard_id"] for x in full_rows}
    observed = set(); markers = []
    for index, plan_path in enumerate(part_paths):
        marker_path = Path(checkpoints) / ("REGION_QUEUE_COMPLETE.part%d.json" % index)
        if not marker_path.is_file(): return False
        rows = [json.loads(x) for x in Path(plan_path).read_text().splitlines() if x.strip()]
        ids = {x["shard_id"] for x in rows}; marker = json.loads(marker_path.read_text())
        if observed & ids: raise RuntimeError("completed KS partition plans overlap")
        observed.update(ids)
        if (marker.get("status") != "compute_queue_complete"
                or marker.get("partition_id") != "part%d" % index
                or marker.get("planned_shards") != len(rows)
                or marker.get("completed_plan_shards") != len(rows)
                or marker.get("plan_sha256") != sha256(plan_path)):
            raise RuntimeError("KS partition completion marker mismatch")
        for sid in ids:
            if not ((Path(checkpoints) / (sid + ".queued.json")).is_file()
                    or (Path(checkpoints) / (sid + ".published.json")).is_file()):
                raise RuntimeError("KS partition marker lacks a shard receipt")
        markers.append(marker)
    if observed != full_ids or len(full_ids) != len(full_rows):
        raise RuntimeError("completed KS partition union differs from full plan")
    atomic_json(Path(checkpoints) / "REGION_PARTS_QUEUE_COMPLETE.json", {
        "status": "compute_queue_complete", "planned_shards": len(full_rows),
        "partition_count": len(part_paths), "partition_markers": markers,
        "full_plan_sha256": sha256(full_plan), "final_publication_complete": False,
    })
    return True


def distribute_wz(wz_rows, local_plan):
    marker = STATE / "WZ_DISTRIBUTION_COMPLETE.json"
    if marker.exists(): return
    sidecars = PREP / "sidecars" / "wuzhen"
    wz("python3 -c \"import shutil; from pathlib import Path; p=Path('%s/sidecars.partial'); shutil.rmtree(str(p),ignore_errors=True); p.parent.mkdir(parents=True,exist_ok=True)\"" % WZ_STATE)
    scp_opts = ["-P", "65091", "-i", WZ_SSH_BASE[3]] + WZ_SSH_BASE[4:]
    run(["scp", "-q", "-r"] + scp_opts + [str(sidecars), "lilysharp@wuzh02.hpccube.com:" + WZ_STATE + "/sidecars.partial"], 7200)
    run(["scp", "-q"] + scp_opts + [str(local_plan), "lilysharp@wuzh02.hpccube.com:" + WZ_STATE + "/plan.jsonl.partial"], 600)
    expected = STATE / "wz_sidecar_expected.json"
    atomic_json(expected, {Path(x["sidecar_path"]).name: {"bytes": x["sidecar_bytes"], "sha256": x["sidecar_sha256"]} for x in wz_rows})
    run(["scp", "-q"] + scp_opts + [str(expected), "lilysharp@wuzh02.hpccube.com:" + WZ_STATE + "/expected.json"], 600)
    verify = """import hashlib,json,os,shutil\nfrom pathlib import Path\nr=Path('%s'); p=r/'sidecars.partial'; e=json.loads((r/'expected.json').read_text())\na={x.name for x in p.glob('*.parquet')}\nassert a==set(e)\nfor x in p.glob('*.parquet'):\n h=hashlib.sha256(); f=x.open('rb')\n for b in iter(lambda:f.read(1048576),b''):h.update(b)\n assert x.stat().st_size==e[x.name]['bytes'] and h.hexdigest()==e[x.name]['sha256']\nos.replace(str(p),str(r/'sidecars')); os.replace(str(r/'plan.jsonl.partial'),str(r/'plan.jsonl'))\nprint('verified')""" % WZ_STATE
    wz("source /etc/profile >/dev/null 2>&1 || true; module load python/3.8.10; python3 -c %s" % __import__('shlex').quote(verify), 7200)
    atomic_json(marker, {"status": "complete", "sidecars": len(wz_rows), "plan_sha256": sha256(local_plan)})


def submit_once_local(label, name, script):
    receipt = STATE / (label + ".submission.json")
    if receipt.exists(): return json.loads(receipt.read_text())["job_id"]
    intent = STATE / (label + ".intent.json")
    found = local_jobs(name)
    if len(found) > 1: raise RuntimeError("ambiguous local jobs")
    if found: job_id = found[0]
    else:
        if intent.exists(): raise RuntimeError("prior local submission intent unresolved; refusing retry")
        atomic_json(intent, {"status": "intent", "job_name": name})
        result = run(["sbatch", "--parsable", "--job-name=" + name, str(script)], 90, check=False)
        job_id = parse_job_id(result.stdout)
        if not job_id:
            found = local_jobs(name)
            if len(found) != 1: raise RuntimeError("unknown local submission unresolved")
            job_id = found[0]
    atomic_json(receipt, {"status": "submitted_or_recovered", "job_id": job_id, "job_name": name})
    return job_id


def submit_once_wz():
    receipt = STATE / "wuzhen_semantic.submission.json"; name = "linkup-semantic-wz-v1"
    if receipt.exists(): return json.loads(receipt.read_text())["job_id"]
    intent = STATE / "wuzhen_semantic.intent.json"
    found = wz_jobs(name)
    if len(found) > 1: raise RuntimeError("ambiguous Wuzhen jobs")
    if found: job_id = found[0]
    else:
        if intent.exists(): raise RuntimeError("prior Wuzhen submission intent unresolved; refusing retry")
        atomic_json(intent, {"status": "intent", "job_name": name})
        result = wz("cd %s && sbatch --parsable --job-name=%s run_semantic_wuzhen.sbatch" % (WZ_RELEASE, name), 90, check=False)
        job_id = parse_job_id(result.stdout)
        if not job_id:
            found = wz_jobs(name)
            if len(found) != 1: raise RuntimeError("unknown Wuzhen submission unresolved")
            job_id = found[0]
    atomic_json(receipt, {"status": "submitted_or_recovered", "job_id": job_id, "job_name": name})
    return job_id


def wait_publication(ks_count, ks_part_paths, wz_count):
    deadline = time.time() + 3 * 24 * 3600
    while time.time() < deadline:
        promote_ks_compute_complete(KS / "plan.jsonl", ks_part_paths, KS / "checkpoints")
        ks_marker = KS / "checkpoints" / "REGION_PUBLISHED_COMPLETE.json"
        remote = wz("test -f %s/checkpoints/REGION_PUBLISHED_COMPLETE.json && cat %s/checkpoints/REGION_PUBLISHED_COMPLETE.json || true" % (WZ_STATE, WZ_STATE), 60).stdout.strip()
        if ks_marker.exists() and remote:
            kd = json.loads(ks_marker.read_text()); wd = json.loads(remote)
            if kd.get("published_receipts") == ks_count and wd.get("published_receipts") == wz_count:
                atomic_json(STATE / "ALL_REGIONS_PUBLISHED_COMPLETE.json",
                            {"status": "complete", "kunshan": kd, "wuzhen": wd, "finished_at": time.time()})
                return
        time.sleep(60)
    raise TimeoutError("regional publication deadline")


def main():
    STATE.mkdir(parents=True, exist_ok=True)
    lock = (STATE / "semantic-controller.lock").open("a+")
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit("semantic controller already active")
    wait_prep(); ks_rows, ks_parts, wz_rows, wz_plan = prepare_plans(); distribute_wz(wz_rows, wz_plan)
    ks_jobs = [
        submit_once_local("kunshan_semantic_part0", "linkup-semantic-ks-part0-v1", KS_RELEASE / "run_semantic_kunshan.sbatch"),
        submit_once_local("kunshan_semantic_part1", "linkup-semantic-ks-part1-v1", KS_RELEASE / "run_semantic_kunshan_second.sbatch"),
    ]
    wz_job = submit_once_wz()
    atomic_json(STATE / "SEMANTIC_JOBS_SUBMITTED.json",
                {"status": "submitted", "kunshan_jobs": ks_jobs, "wuzhen_job": wz_job,
                 "final_publication_complete": False})
    wait_publication(len(ks_rows), ks_parts, len(wz_rows))


if __name__ == "__main__":
    try: main()
    except Exception as exc:
        atomic_json(STATE / "SEMANTIC_CONTROLLER_FAILED.json",
                    {"status": "failed", "error_type": type(exc).__name__, "error": str(exc), "at": time.time()})
        raise
