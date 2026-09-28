#!/usr/bin/env python3
"""Server-resident, submit-once continuation for disposition preparation."""
from __future__ import annotations

import hashlib
import fcntl
import json
import os
import socket
import shutil
import subprocess
import sys
import time
from pathlib import Path

PREFIXES = "0123456789abcdef"
ROOT = Path("/public/home/lilysharp/linkup_analysis_v1/stage_c_release_v1")
OUTPUT = Path("/public/home/lilysharp/linkup_release_v1/disposition_prep_v1")
STAGE_COMPLETE = Path("/public/home/lilysharp/linkup_release_v1/wz_occurrences_stage/COMPLETE.json")
CONTROL = OUTPUT / "continuation"
PREFIX_SCRIPT = ROOT / "run_disposition_prefix.sbatch"
CONSOLIDATE_SCRIPT = ROOT / "run_disposition_consolidate.sbatch"
REMAINING_SCRIPT = ROOT / "run_disposition_remaining.sbatch"
CONFIG = ROOT / "config_disposition_kunshan.json"
PREP = ROOT / "prepare_release_dispositions.py"
EXPECTED_PREP_SHA = "f672081e7b46a188711786354f786a6e110fd45f58ecea3a7e137bbea091e7bc"
EXPECTED_CONFIG_SHA = "ed5c5239665333ea43c5887f4e0b8e372ad21a8405fd9ea6436b64ff075e7b62"
TERMINAL = {"BOOT_FAIL", "CANCELLED", "COMPLETED", "DEADLINE", "FAILED", "NODE_FAIL", "OUT_OF_MEMORY", "PREEMPTED", "TIMEOUT"}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temp, path)


def log(message: str) -> None:
    line = "%s %s" % (time.strftime("%Y-%m-%dT%H:%M:%S%z"), message)
    print(line, flush=True)


def command(argv, timeout=60):
    return subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, timeout=timeout, check=False)


def parse_job_id(stdout: str) -> str | None:
    found = []
    for line in stdout.splitlines():
        token = line.strip().split(";", 1)[0]
        if token.isdigit():
            found.append(token)
    return found[0] if len(set(found)) == 1 else None


def jobs_named(name: str) -> list[dict]:
    found = {}
    queued = command(["squeue", "-h", "-n", name, "-o", "%A|%.128j|%T"])
    if queued.returncode != 0:
        raise RuntimeError("squeue lookup failed closed for %s: %s" % (name, queued.stdout[-1000:]))
    for line in queued.stdout.splitlines():
        fields = line.strip().split("|")
        if len(fields) == 3 and fields[1] == name:
            found[fields[0]] = {"job_id": fields[0], "state": fields[2]}
    history = command(["sacct", "-nX", "-P", "-S", "2026-09-28",
                       "-o", "JobIDRaw,JobName%128,State"])
    if history.returncode != 0:
        raise RuntimeError("sacct lookup failed closed for %s: %s" % (name, history.stdout[-1000:]))
    for line in history.stdout.splitlines():
        fields = line.strip().split("|")
        if len(fields) >= 3 and fields[1] == name and fields[0].isdigit():
            found.setdefault(fields[0], {"job_id": fields[0], "state": fields[2].split("+")[0]})
    return sorted(found.values(), key=lambda x: int(x["job_id"]))


def submit_once(label: str, name: str, argv: list[str]) -> str:
    receipt_path = CONTROL / (label + ".submission.json")
    if receipt_path.exists():
        return str(json.loads(receipt_path.read_text())["job_id"])
    existing = jobs_named(name)
    if len(existing) > 1:
        raise RuntimeError("multiple jobs found for unique name %s: %s" % (name, existing))
    if existing:
        job_id = existing[0]["job_id"]
        atomic_json(receipt_path, {"status": "recovered_existing", "job_id": job_id,
                                   "job_name": name, "observed_state": existing[0]["state"]})
        return job_id
    intent = CONTROL / (label + ".submission_intent.json")
    if intent.exists():
        atomic_json(CONTROL / "PAUSED.json", {"status": "prior_intent_without_resolved_job",
                                               "label": label, "job_name": name})
        raise RuntimeError("prior submission intent exists without receipt/job; fail closed")
    atomic_json(intent, {"status": "intent", "job_name": name, "argv": argv})
    try:
        result = command(argv, timeout=90)
    except subprocess.TimeoutExpired:
        result = None
    if result is not None and result.returncode == 0:
        job_id = parse_job_id(result.stdout)
        if job_id:
            atomic_json(receipt_path, {"status": "submitted", "job_id": job_id,
                                       "job_name": name, "sbatch_output": result.stdout.strip(),
                                       "sbatch_stderr": result.stderr.strip()})
            return job_id
    # A timeout/error is an unknown submission. Resolve by name; never resubmit here.
    for _ in range(6):
        time.sleep(10)
        existing = jobs_named(name)
        if len(existing) == 1:
            job_id = existing[0]["job_id"]
            atomic_json(receipt_path, {"status": "recovered_after_unknown", "job_id": job_id,
                                       "job_name": name, "observed_state": existing[0]["state"]})
            return job_id
        if len(existing) > 1:
            raise RuntimeError("ambiguous jobs after unknown submission: %s" % existing)
    detail = "timeout" if result is None else result.stdout[-1000:]
    atomic_json(CONTROL / "PAUSED.json", {"status": "unknown_submission_unresolved",
                                           "label": label, "job_name": name, "detail": detail})
    raise RuntimeError("unknown submission unresolved; no retry performed")


def job_state(job_id: str) -> str:
    queued = command(["squeue", "-h", "-j", job_id, "-o", "%T"])
    if queued.returncode == 0:
        states = [x.strip() for x in queued.stdout.splitlines() if x.strip()]
        if states:
            return states[0]
    history = command(["sacct", "-nX", "-P", "-j", job_id, "-o", "State"])
    if history.returncode != 0:
        raise RuntimeError("sacct state lookup failed closed for job %s: %s" %
                           (job_id, history.stdout[-1000:]))
    states = [x.strip().split("+")[0] for x in history.stdout.splitlines() if x.strip()]
    return states[0] if states else "UNKNOWN"


def wait_for_receipt(job_id: str, receipt: Path, label: str) -> dict:
    while True:
        if receipt.exists():
            document = json.loads(receipt.read_text())
            if document.get("status") != "complete":
                raise RuntimeError("non-complete receipt for " + label)
            return document
        state = job_state(job_id)
        if state in TERMINAL:
            atomic_json(CONTROL / "PAUSED.json", {"status": "job_finished_without_receipt",
                                                   "label": label, "job_id": job_id, "job_state": state})
            raise RuntimeError("%s ended %s without receipt" % (label, state))
        log("waiting label=%s job=%s state=%s" % (label, job_id, state))
        time.sleep(60)


def validate_stage() -> None:
    stage = json.loads(STAGE_COMPLETE.read_text())
    if stage.get("status") != "complete" or len(stage.get("batches", [])) != 10:
        raise RuntimeError("Wuzhen staging validation is incomplete")
    rows = sum(x["occurrences"]["rows"] for x in stage["batches"])
    if rows != 134091962:
        raise RuntimeError("Wuzhen staged row total differs from frozen count")
    if digest(PREP) != EXPECTED_PREP_SHA or digest(CONFIG) != EXPECTED_CONFIG_SHA:
        raise RuntimeError("deployed prep code/config SHA differs from frozen identity")
    cfg = json.loads(CONFIG.read_text())
    report = json.loads(Path(cfg["kunshan_projection_report"]).read_text())
    inventory_paths = [Path(x) for x in cfg["source_inventories"]]
    inventory = next(json.loads(x.read_text()) for x in inventory_paths
                     if json.loads(x.read_text())["region"] == "kunshan")
    report_rows = {x["source_file"]: x for x in report["source_counts"]}
    inventory_rows = {x["file_name"]: x for x in inventory["sources"]}
    if (len(report_rows) != 1358 or set(report_rows) != set(inventory_rows)
            or sum(x["rows"] for x in report_rows.values()) != 164581116):
        raise RuntimeError("Kunshan projection report/inventory key conservation failed")
    projection_root = Path(cfg["kunshan_projection_dir"])
    for name, metadata in report_rows.items():
        if metadata["input_bytes"] != inventory_rows[name]["source_bytes"]:
            raise RuntimeError("Kunshan projection/inventory source size differs: " + name)
        projection_name = name if name.endswith(".parquet") else name + ".parquet"
        if not (projection_root / projection_name).is_file():
            raise RuntimeError("Kunshan projection file missing: " + projection_name)


def cleanup_generated_wz_stage() -> None:
    cleanup = CONTROL / "WZ_STAGE_CLEANUP.json"
    if cleanup.exists():
        if json.loads(cleanup.read_text()).get("status") != "complete":
            raise RuntimeError("invalid Wuzhen stage cleanup receipt")
        return
    stage = json.loads(STAGE_COMPLETE.read_text())
    stage_root = STAGE_COMPLETE.parent.resolve()
    deleted = []
    for batch in stage["batches"]:
        item = batch["occurrences"]
        path = Path(item["path"]).resolve()
        if path.parent.parent != stage_root or path.name != "occurrences.parquet":
            raise RuntimeError("refusing to delete path outside generated Wuzhen staging root")
        if path.exists():
            if path.stat().st_size != item["bytes"]:
                raise RuntimeError("staged occurrence size changed before cleanup")
            path.unlink()
        deleted.append({"path": str(path), "bytes": item["bytes"], "sha256": item["sha256"]})
        atomic_json(CONTROL / "WZ_STAGE_CLEANUP_PROGRESS.json", {
            "status": "running", "deleted_files": len(deleted),
            "deleted_bytes": sum(x["bytes"] for x in deleted),
        })
    atomic_json(cleanup, {"status": "complete", "generated_copies_only": True,
                          "raw_sources_deleted": False, "files": deleted,
                          "deleted_bytes": sum(x["bytes"] for x in deleted)})


def prefix_job(prefix: str) -> dict:
    receipt = OUTPUT / "prefix_receipts" / ("prefix_%s.json" % prefix)
    if receipt.exists():
        document = json.loads(receipt.read_text())
        if (document.get("status") != "complete" or not document.get("row_conservation")
                or document.get("script_sha256") != EXPECTED_PREP_SHA
                or document.get("config_sha256") != EXPECTED_CONFIG_SHA):
            raise RuntimeError("invalid existing prefix receipt: " + prefix)
        return document
    label = "prefix_" + prefix
    if prefix == "0":
        external = OUTPUT / "prefix0_submission.json"
        local_submission = CONTROL / (label + ".submission.json")
        if external.exists() and not local_submission.exists():
            adopted = json.loads(external.read_text())
            job_id = str(adopted.get("job_id", ""))
            if not job_id.isdigit() or adopted.get("prefix") != "0":
                raise RuntimeError("invalid externally submitted prefix0 receipt")
            atomic_json(local_submission, {"status": "adopted_external_submission",
                                           "job_id": job_id,
                                           "external_receipt": str(external)})
        # The initial prefix0 attempt is preserved but may have failed before
        # a prefix receipt due to a mechanical runtime error.  One explicitly
        # named recovery is allowed; submit_once remains fail-closed.
        if local_submission.exists():
            old_job = str(json.loads(local_submission.read_text())["job_id"])
            if job_state(old_job) in TERMINAL and not receipt.exists():
                label = "prefix_0_recovery_1"
    name = "linkup-disp-p%s-v1" % prefix
    if label == "prefix_0_recovery_1":
        name = "linkup-disp-p0-v1-r1"
    job_id = submit_once(label, name, ["sbatch", "--parsable", "--job-name=" + name,
        "--export=ALL,PREFIX=" + prefix, str(PREFIX_SCRIPT)])
    log("submitted/resumed prefix=%s job=%s" % (prefix, job_id))
    return wait_for_receipt(job_id, receipt, label)


def main() -> None:
    CONTROL.mkdir(parents=True, exist_ok=True)
    # v1 may remain held by the superseded controller that only polls the
    # known-failed initial job on another load-balanced login node.
    lock_handle = (CONTROL / "continuation_v2.lock").open("w")
    try:
        fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise RuntimeError("another disposition continuation is already running")
    atomic_json(CONTROL / "controller_v2.instance.json", {
        "status": "running", "pid": os.getpid(), "host": socket.gethostname(),
        "controller_sha256": digest(Path(__file__).resolve()),
    })
    validate_stage()
    first = prefix_job("0")
    first_bytes = sum(x["bytes"] for x in first["fragment_files"])
    first_rows = int(first["occurrence_rows"])
    total_rows = 164581116 + 134091962
    projected = (first_bytes * total_rows + first_rows - 1) // first_rows
    projected_with_skew = projected * 5 // 4
    fixed_fragment_budget = 16_000_000_000
    current_fragments = sum(p.stat().st_size for p in (OUTPUT / "prefix_fragments").rglob("*.parquet"))
    free = shutil.disk_usage(OUTPUT).free
    reserve = 3_000_000_000
    fits = (projected_with_skew <= fixed_fragment_budget
            and projected_with_skew <= current_fragments + max(0, free - reserve))
    gate = {"status": "pass" if fits else "pause", "prefix_0_rows": first_rows,
            "prefix_0_fragment_bytes": first_bytes, "linear_projected_fragment_bytes": projected,
            "skew_guarded_projected_fragment_bytes": projected_with_skew,
            "fixed_fragment_budget_bytes": fixed_fragment_budget,
            "current_fragment_bytes": current_fragments, "current_free_bytes": free,
            "free_reserve_bytes": reserve, "all_prefixes_fit_local": fits}
    atomic_json(CONTROL / "PREFIX_0_STORAGE_GATE.json", gate)
    if not fits:
        atomic_json(CONTROL / "PAUSED.json", {"status": "prefix_0_projection_exceeds_local_budget",
                                               "gate": gate})
        log("prefix0 gate paused remaining prefixes")
        return
    remaining_receipt = OUTPUT / "REMAINING_PREFIXES_COMPLETE.json"
    remaining_job = submit_once("remaining_prefixes", "linkup-disp-remaining-v1",
                                ["sbatch", "--parsable", str(REMAINING_SCRIPT)])
    wait_for_receipt(remaining_job, remaining_receipt, "remaining_prefixes")
    cleanup_generated_wz_stage()
    consolidate_receipt = OUTPUT / "CONSOLIDATION_COMPLETE.json"
    job_id = submit_once("consolidate", "linkup-disp-consolidate-v1",
                         ["sbatch", "--parsable", str(CONSOLIDATE_SCRIPT)])
    result = wait_for_receipt(job_id, consolidate_receipt, "consolidate")
    atomic_json(CONTROL / "COMPLETE.json", {"status": "complete", "storage_gate": gate,
                                             "consolidation": result})
    (CONTROL / "PAUSED.json").unlink(missing_ok=True)
    log("disposition preparation complete")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        atomic_json(CONTROL / "FAILED.json", {"status": "failed", "error_type": type(exc).__name__,
                                               "error": str(exc)})
        raise
