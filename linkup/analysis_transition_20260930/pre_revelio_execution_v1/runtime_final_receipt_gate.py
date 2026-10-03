#!/usr/bin/env python3
"""Validate every regional publication receipt before the global release marker."""
import fcntl, hashlib, json, os, shlex, subprocess, time
from pathlib import Path

KS = Path("/public/home/lilysharp/linkup_release_v1/semantic_v1/kunshan")
ROOT = KS.parent
WZ = "/work/home/lilysharp/linkup_release_v1/semantic_v1/wuzhen"
WZ_OPTS = ["-p", "65091", "-i", "/public/home/lilysharp/.ssh/scnet_wuzhen_lilysharp",
           "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
           "-o", "UserKnownHostsFile=/public/home/lilysharp/.ssh/wz_known_hosts_20260928",
           "-o", "ControlMaster=auto", "-o", "ControlPersist=300",
           "-o", "ControlPath=/tmp/linkup-wz-final-%r-%h-%p"]
CODE = {"parser": "d8df533693cb9c01f169df51cac184f144888a1595bb28207deb82952ad2f744",
        "enrichment": "cf0cf8fae3451d463430c14ebe6bf2a6dcc72b8239589ed2fbeb20ef0c4451c6",
        "lean_writer": "67c22e5db1d61f7a909235150a0254f9af9bd2ccd6f1958aa6d7a555e32b99d5"}


def atomic(path, value):
    temp = Path(str(path) + ".tmp"); temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n"); os.replace(temp, path)


def run(argv, timeout=600):
    return subprocess.run(argv, check=True, timeout=timeout, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def wz(command, timeout=120):
    return run(["ssh", "-T"] + WZ_OPTS + ["lilysharp@wuzh02.hpccube.com", command], timeout).stdout


def load_plan(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def validate_region(plan, checkpoints, marker, region, expectations=None):
    published = json.loads(Path(marker).read_text())
    if published.get("status") != "complete" or published.get("published_receipts") != len(plan):
        raise RuntimeError(region + " publication marker mismatch")
    raw = canonical = 0; seen = set()
    for row in plan:
        sid = row["shard_id"]; receipt = json.loads((Path(checkpoints) / (sid + ".published.json")).read_text())
        complete = receipt.get("shard_complete", {}); accounting = complete.get("accounting", {})
        if sid in seen or receipt.get("status") != "published_verified" or receipt.get("shard_id") != sid:
            raise RuntimeError(region + " receipt identity mismatch")
        seen.add(sid)
        expected = {"code_sha256": CODE} if expectations is None else expectations[sid]
        if complete.get("code_sha256") != expected["code_sha256"]:
            raise RuntimeError(region + " code identity mismatch")
        if "dcu_provenance" in expected:
            if complete.get("lean_complete", {}).get("dcu_provenance") != expected["dcu_provenance"]:
                raise RuntimeError(region + " DCU provenance mismatch")
        for key in ("source_file", "source_bytes", "source_sha256_cached", "sidecar_sha256", "raw_rows"):
            if accounting.get(key) != row[key]: raise RuntimeError(region + " accounting mismatch: " + key)
        if sum(accounting["disposition_counts"].values()) != row["raw_rows"] or not accounting.get("row_conservation"):
            raise RuntimeError(region + " disposition conservation failure")
        raw += row["raw_rows"]; canonical += accounting["canonical_usa_rows"]
    return {"region": region, "shards": len(plan), "raw_rows": raw,
            "canonical_usa_singleton_rows": canonical, "published_receipts": len(seen)}


def load_wz_expectations(checkpoints, plan):
    path = Path(checkpoints) / "WZ_CODE_EXPECTATIONS.json"
    value = json.loads(path.read_text())
    expected = {}
    for group in value.get("groups", []):
        item = {"code_sha256": group["code_sha256"]}
        if "dcu_provenance" in group: item["dcu_provenance"] = group["dcu_provenance"]
        for sid in group["shard_ids"]:
            if sid in expected: raise RuntimeError("Wuzhen expectation groups overlap")
            expected[sid] = item
    plan_ids = {row["shard_id"] for row in plan}
    if set(expected) != plan_ids: raise RuntimeError("Wuzhen expectation groups do not cover frozen plan")
    queue = json.loads((Path(checkpoints) / "REGION_QUEUE_COMPLETE.json").read_text())
    if queue.get("code_expectations_sha256") != hashlib.sha256(path.read_bytes()).hexdigest():
        raise RuntimeError("Wuzhen expectation digest mismatch")
    return expected


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    lock = (ROOT / "final-gate.lock").open("a+")
    try: fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit("final gate already active")
    deadline = time.time() + 4 * 24 * 3600
    ks_marker = KS / "checkpoints" / "REGION_PUBLISHED_COMPLETE.json"
    archive = ROOT / "final_gate_wuzhen"
    staged_wz_marker = archive / "checkpoints" / "REGION_PUBLISHED_COMPLETE.json"
    while time.time() < deadline:
        remote_ready = "yes" if staged_wz_marker.is_file() else wz(
            "test -f %s/checkpoints/REGION_PUBLISHED_COMPLETE.json && echo yes || true" % WZ).strip()
        if ks_marker.exists() and remote_ready == "yes": break
        time.sleep(60)
    else: raise TimeoutError("publication markers deadline")
    archive.mkdir(exist_ok=True)
    if not staged_wz_marker.is_file() or not (archive / "plan.jsonl").is_file():
        scp = ["scp", "-q", "-r", "-P", "65091", "-i", WZ_OPTS[3]] + WZ_OPTS[4:]
        run(scp + ["lilysharp@wuzh02.hpccube.com:" + WZ + "/checkpoints", str(archive / "checkpoints.partial")], 3600)
        run(scp + ["lilysharp@wuzh02.hpccube.com:" + WZ + "/plan.jsonl", str(archive / "plan.jsonl")], 600)
        os.replace(archive / "checkpoints.partial", archive / "checkpoints")
    ks_result = validate_region(load_plan(KS / "plan.jsonl"), KS / "checkpoints", ks_marker, "kunshan")
    wz_plan = load_plan(archive / "plan.jsonl")
    wz_expectations = load_wz_expectations(archive / "checkpoints", wz_plan)
    wz_result = validate_region(wz_plan, archive / "checkpoints",
                                archive / "checkpoints" / "REGION_PUBLISHED_COMPLETE.json",
                                "wuzhen", wz_expectations)
    gate = {"status": "complete", "code_sha256": CODE, "regions": [ks_result, wz_result],
            "total_shards": ks_result["shards"] + wz_result["shards"],
            "total_raw_description_rows": ks_result["raw_rows"] + wz_result["raw_rows"],
            "final_publication_complete": True, "finished_at": time.time()}
    local = ROOT / "ALL_REGIONS_VERIFIED_COMPLETE.json"; atomic(local, gate)
    digest = hashlib.sha256(local.read_bytes()).hexdigest()
    hz_opts = ["-P", "65032", "-i", "/public/home/lilysharp/.ssh/hz_transfer_20260928",
               "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
               "-o", "UserKnownHostsFile=/public/home/lilysharp/.ssh/hz_known_hosts_20260928",
               "-o", "ProxyCommand=/public/home/lilysharp/linkup_release_v1/hz_proxy_command.sh"]
    remote = "/public/home/lilysharp/linkup_release_v1/full_semantic_v1/ALL_REGIONS_VERIFIED_COMPLETE.json"
    run(["scp", "-q"] + hz_opts + [str(local), "lilysharp@zzeshell.scnet.cn:" + remote + ".partial"], 300)
    program = "import hashlib,os; p=%r; assert hashlib.sha256(open(p+'.partial','rb').read()).hexdigest()==%r; os.replace(p+'.partial',p)" % (remote, digest)
    run(["ssh", "-T", "-p", "65032", "-i", "/public/home/lilysharp/.ssh/hz_transfer_20260928",
         "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
         "-o", "UserKnownHostsFile=/public/home/lilysharp/.ssh/hz_known_hosts_20260928",
         "-o", "ProxyCommand=/public/home/lilysharp/linkup_release_v1/hz_proxy_command.sh",
         "lilysharp@zzeshell.scnet.cn", "python3 -c " + shlex.quote(program)], 300)


if __name__ == "__main__":
    try: main()
    except Exception as exc:
        atomic(ROOT / "FINAL_GATE_FAILED.json", {"status": "failed", "error": str(exc), "type": type(exc).__name__})
        raise
