#!/usr/bin/env python3
"""Freeze completed Kunshan receipts and split the remaining plan four ways."""
from __future__ import annotations

import argparse, hashlib, json, os, subprocess, time
from pathlib import Path

CODE = {
    "parser": "d8df533693cb9c01f169df51cac184f144888a1595bb28207deb82952ad2f744",
    "enrichment": "cf0cf8fae3451d463430c14ebe6bf2a6dcc72b8239589ed2fbeb20ef0c4451c6",
    "lean_writer": "67c22e5db1d61f7a909235150a0254f9af9bd2ccd6f1958aa6d7a555e32b99d5",
}
TERMINAL = {"BOOT_FAIL", "CANCELLED", "COMPLETED", "DEADLINE", "FAILED",
            "NODE_FAIL", "OUT_OF_MEMORY", "PREEMPTED", "TIMEOUT"}


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def rows(path): return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
def atomic(path, value):
    path = Path(path); temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n"); os.replace(temp, path)
def write_jsonl(path, values):
    path = Path(path); temp = Path(str(path) + ".tmp")
    temp.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in values)); os.replace(temp, path)


def complete_for(row, checkpoints):
    sid = row["shard_id"]; published = checkpoints / (sid + ".published.json")
    queued = checkpoints / (sid + ".queued.json")
    complete = None; saw_receipt = False; last_error = None
    for attempt in range(5):
        try:
            if published.is_file():
                saw_receipt = True; wrapper = json.loads(published.read_text())
                if wrapper.get("status") != "published_verified" or wrapper.get("shard_id") != sid:
                    raise RuntimeError(sid + ": invalid published receipt")
                complete = wrapper.get("shard_complete", {}); break
            if queued.is_file():
                saw_receipt = True; wrapper = json.loads(queued.read_text())
                path = Path(wrapper.get("shard_complete", ""))
                if (wrapper.get("status") != "sealed_for_transfer" or not path.is_file()
                        or sha(path) != wrapper.get("shard_complete_sha256")):
                    raise RuntimeError(sid + ": invalid queued receipt")
                complete = json.loads(path.read_text()); break
            if not saw_receipt: return None
        except (OSError, ValueError, RuntimeError) as exc:
            last_error = exc
        if attempt < 4: time.sleep(0.25)
    if complete is None:
        raise RuntimeError(sid + ": receipt transition did not settle") from last_error
    accounting = complete.get("accounting", {})
    if complete.get("code_sha256") != CODE:
        raise RuntimeError(sid + ": completed receipt has unexpected code identity")
    for key in ("source_file", "source_bytes", "source_sha256_cached", "sidecar_sha256", "raw_rows"):
        if accounting.get(key) != row[key]: raise RuntimeError(sid + ": accounting mismatch: " + key)
    return complete


def run_before_deadline(command, deadline, **kwargs):
    remaining = deadline - time.monotonic()
    if remaining <= 0: raise TimeoutError("handoff metadata exceeded time limit")
    return subprocess.run(command, timeout=remaining, **kwargs)


def wait_stopped(job_ids, deadline):
    run_before_deadline(["scancel"] + job_ids, deadline, check=False)
    while time.monotonic() < deadline:
        active = run_before_deadline(
            ["squeue", "-h", "-j", ",".join(job_ids), "-o", "%A"], deadline,
            check=True, text=True, stdout=subprocess.PIPE).stdout.strip()
        if not active: break
        time.sleep(2)
    else: raise TimeoutError("old Kunshan jobs did not stop before handoff deadline")
    states = {}
    for job in job_ids:
        output = run_before_deadline(
            ["sacct", "-nX", "-P", "-j", job, "-o", "State"], deadline,
            check=True, text=True, stdout=subprocess.PIPE).stdout
        state = next((x.split("+", 1)[0].strip().split()[0] for x in output.splitlines() if x.strip()), "")
        if state not in TERMINAL: raise RuntimeError("old job terminal state not confirmed: " + job)
        states[job] = state
    return states


def split_balanced(values, count=4):
    parts = [[] for _ in range(count)]; totals = [0] * count
    for row in sorted(values, key=lambda x: (-int(x["raw_rows"]), x["shard_id"])):
        target = min(range(count), key=lambda i: (totals[i], i))
        parts[target].append(row); totals[target] += int(row["raw_rows"])
    return parts, totals


def prepare(args):
    deadline = time.monotonic() + args.max_prepare_seconds
    full = rows(args.full_plan)
    if len(full) != 1358 or len({x["shard_id"] for x in full}) != len(full):
        raise RuntimeError("frozen Kunshan plan must contain 1358 unique shards")
    # If the old workers finished while this allocation waited, leave them and
    # the existing completion path untouched.
    initial_complete = []
    for row in full:
        if time.monotonic() >= deadline: raise TimeoutError("handoff metadata exceeded time limit")
        if complete_for(row, args.checkpoint_root): initial_complete.append(row)
    if len(initial_complete) == len(full):
        atomic(args.output_root / "KS_4WAY_HANDOFF.json",
               {"status": "already_complete", "full_plan_sha256": sha(args.full_plan)})
        return
    states = wait_stopped(args.old_job_ids, deadline)
    completed = []; remaining = []
    for row in full:
        if time.monotonic() >= deadline: raise TimeoutError("handoff metadata exceeded time limit")
        (completed if complete_for(row, args.checkpoint_root) else remaining).append(row)
    if time.monotonic() >= deadline: raise TimeoutError("handoff metadata exceeded time limit")
    parts, raw_totals = split_balanced(remaining)
    complete_ids = {x["shard_id"] for x in completed}
    part_ids = [{x["shard_id"] for x in part} for part in parts]
    if (any(complete_ids & ids for ids in part_ids)
            or any(part_ids[i] & part_ids[j] for i in range(4) for j in range(i))
            or complete_ids | set().union(*part_ids) != {x["shard_id"] for x in full}):
        raise RuntimeError("completed plus four parts do not form an exclusive full-plan cover")
    args.output_root.mkdir(parents=True, exist_ok=True)
    completed_path = args.output_root / "plan.completed_before_4way.jsonl"
    write_jsonl(completed_path, completed)
    part_records = []
    for index, part in enumerate(parts):
        path = args.output_root / ("plan.ks_split%d.jsonl" % index); write_jsonl(path, part)
        part_records.append({"partition_id": "ks_split%d" % index, "path": str(path),
                             "sha256": sha(path), "shards": len(part), "raw_rows": raw_totals[index]})
    atomic(args.output_root / "KS_4WAY_HANDOFF.json", {
        "status": "prepared", "full_plan": str(args.full_plan),
        "full_plan_sha256": sha(args.full_plan), "full_shards": len(full),
        "completed_plan": str(completed_path), "completed_plan_sha256": sha(completed_path),
        "completed_shards": len(completed), "remaining_shards": len(remaining),
        "old_job_terminal_states": states, "parts": part_records,
        "code_sha256": CODE, "prepared_at": time.time(),
    })


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--full-plan", type=Path, required=True)
    ap.add_argument("--checkpoint-root", type=Path, required=True)
    ap.add_argument("--output-root", type=Path, required=True)
    ap.add_argument("--old-job-ids", nargs=2, required=True)
    ap.add_argument("--max-prepare-seconds", type=int, default=300)
    prepare(ap.parse_args())


if __name__ == "__main__": main()
