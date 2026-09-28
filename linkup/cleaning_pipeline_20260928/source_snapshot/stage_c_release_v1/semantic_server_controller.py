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


def local_jobs(name):
    return [x.strip() for x in run(["squeue", "-h", "-n", name, "-o", "%A"], check=True).stdout.splitlines() if x.strip().isdigit()]


def wz_jobs(name):
    return [x.strip() for x in wz("squeue -h -n %s -o '%%A'" % name).stdout.splitlines() if x.strip().isdigit()]


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
    (KS / "plan.jsonl").write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in by_region["kunshan"]));
    wz_rows = []
    for row in by_region["wuzhen"]:
        row = dict(row); row["sidecar_path"] = WZ_STATE + "/sidecars/" + Path(row["sidecar_path"]).name; wz_rows.append(row)
    local_wz_plan = STATE / "wuzhen_plan.jsonl"
    local_wz_plan.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in wz_rows))
    return by_region["kunshan"], wz_rows, local_wz_plan


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
    found = local_jobs(name)
    if len(found) > 1: raise RuntimeError("ambiguous local jobs")
    if found: job_id = found[0]
    else:
        atomic_json(STATE / (label + ".intent.json"), {"status": "intent", "job_name": name})
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
    found = wz_jobs(name)
    if len(found) > 1: raise RuntimeError("ambiguous Wuzhen jobs")
    if found: job_id = found[0]
    else:
        atomic_json(STATE / "wuzhen_semantic.intent.json", {"status": "intent", "job_name": name})
        result = wz("cd %s && sbatch --parsable --job-name=%s run_semantic_wuzhen.sbatch" % (WZ_RELEASE, name), 90, check=False)
        job_id = parse_job_id(result.stdout)
        if not job_id:
            found = wz_jobs(name)
            if len(found) != 1: raise RuntimeError("unknown Wuzhen submission unresolved")
            job_id = found[0]
    atomic_json(receipt, {"status": "submitted_or_recovered", "job_id": job_id, "job_name": name})
    return job_id


def wait_publication(ks_count, wz_count):
    deadline = time.time() + 3 * 24 * 3600
    while time.time() < deadline:
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
    wait_prep(); ks_rows, wz_rows, wz_plan = prepare_plans(); distribute_wz(wz_rows, wz_plan)
    ks_job = submit_once_local("kunshan_semantic", "linkup-semantic-ks-v1", KS_RELEASE / "run_semantic_kunshan.sbatch")
    wz_job = submit_once_wz()
    atomic_json(STATE / "SEMANTIC_JOBS_SUBMITTED.json",
                {"status": "submitted", "kunshan_job": ks_job, "wuzhen_job": wz_job,
                 "final_publication_complete": False})
    wait_publication(len(ks_rows), len(wz_rows))


if __name__ == "__main__":
    try: main()
    except Exception as exc:
        atomic_json(STATE / "SEMANTIC_CONTROLLER_FAILED.json",
                    {"status": "failed", "error_type": type(exc).__name__, "error": str(exc), "at": time.time()})
        raise
