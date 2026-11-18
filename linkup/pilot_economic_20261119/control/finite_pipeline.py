#!/usr/bin/env python3
"""Finite cloud supervisor. Import/self-test never invokes a model or cloud API."""
from __future__ import annotations

import argparse
import contextlib
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

VERSION = "economic-finite-pipeline-20261119-v1"
CLOUD_RUN = Path("/home/linkup/migration/pilot_economic_20261119/run01")
MAX_PHYSICAL = 10000
MAX_WALL = 48 * 3600
PILOT_CAP_NANO = 150_000_000_000
UNCERTAIN = ("forwarding_uncertain", "transport_uncertain_no_retry")


class StopPipeline(RuntimeError):
    pass


def read(path):
    return json.loads(Path(path).read_text())


def encoded(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")) + "\n").encode()


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def immutable(path, data):
    path = Path(path)
    if path.exists():
        if path.read_bytes() != data:
            raise StopPipeline("immutable_artifact_conflict")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(data)


def atomic(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(encoded(value))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


@contextlib.contextmanager
def controller_lock(directory):
    with (Path(directory) / "control/FINITE_PIPELINE.lock").open("a") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise StopPipeline("finite_controller_already_active") from None
        yield


def active_workers(directory):
    root = Path(directory)
    scripts = {str(root / "runtime/pilot_worker.py").encode(),
               str(root / "runtime_v2/pilot_worker_v2.py").encode(),
               str(root / "runtime_v2/rate_amendment.py").encode()}
    found = []
    for path in Path("/proc").glob("[0-9]*/cmdline"):
        try:
            argv = path.read_bytes().split(b"\0")
        except OSError:
            continue
        if scripts.intersection(argv):
            found.append(int(path.parent.name))
    return sorted(found)


def ledger_snapshot(directory):
    path = Path(directory) / "ADMISSION_PRIVATE.sqlite3"
    conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    try:
        conn.execute("BEGIN")
        meta = dict(conn.execute("SELECT key,value FROM meta"))
        states = dict(conn.execute("SELECT state,COUNT(*) FROM attempts GROUP BY state"))
        claims = sorted(row[0] for row in conn.execute("SELECT DISTINCT context FROM claims"))
        quarantined = sorted(row[0] for row in conn.execute("SELECT context FROM quarantine"))
        reserved = conn.execute("SELECT COALESCE(SUM(dollars_nano),0) FROM attempts").fetchone()[0]
        return {"meta": meta, "states": states, "claims": claims, "quarantined": quarantined,
                "reserved_nano": reserved}
    finally:
        conn.close()


def manifest_chain(directory, *, allow_partial=False):
    root = Path(directory)
    manifests = []
    previous = None
    count = 0
    for folder in sorted((root / "preparation").glob("batch[0-9]*")):
        if not folder.is_dir():
            continue
        manifest_path = folder / "BATCH_MANIFEST_PUBLIC.json"
        if not manifest_path.is_file():
            if allow_partial:
                break
            raise StopPipeline("partial_preparation_directory_requires_inspection")
        value = read(manifest_path)
        if folder.name != "batch%04d" % (len(manifests) + 1) or value["batch_id"] != folder.name:
            raise StopPipeline("actual_manifest_chain_gap")
        if sha(folder / "INPUTS_PRIVATE.jsonl") != value["inputs_sha256"]:
            raise StopPipeline("prepared_input_sha_mismatch")
        count += value["physical_rows"]
        if (type(value["physical_rows"]) is not int or value["physical_rows"] <= 0
                or value["end_cursor_exclusive"]["row_offset"] - value["start_cursor"]["row_offset"] != value["physical_rows"]
                or value["end_cursor_exclusive"]["shard_ordinal"] != value["start_cursor"]["shard_ordinal"]):
            raise StopPipeline("physical_window_cursor_conservation_failed")
        if count != value["cumulative_physical_rows"] or count > MAX_PHYSICAL:
            raise StopPipeline("cumulative_physical_count_mismatch_or_cap")
        if previous:
            if (value["previous_batch_manifest_sha256"] != previous["manifest_sha256"]
                    or value["start_cursor"] != previous["end_cursor_exclusive"]
                    or value["origin_sha256"] != previous["origin_sha256"]):
                raise StopPipeline("actual_cursor_or_origin_chain_mismatch")
        value = dict(value, manifest_path=str(manifest_path), manifest_sha256=sha(manifest_path))
        manifests.append(value)
        previous = value
    return manifests


def next_window(last):
    remaining = MAX_PHYSICAL - last["cumulative_physical_rows"]
    if remaining <= 0:
        raise StopPipeline("physical_pilot_limit_reached")
    cursor = last["end_cursor_exclusive"]
    if cursor["shard_ordinal"] != last["origin"]["shard_ordinal"]:
        raise StopPipeline("shard_binding_change_not_authorized")
    shard_remaining = last["origin"]["shard_rows"] - cursor["row_offset"]
    if shard_remaining <= 0:
        raise StopPipeline("actual_source_shard_boundary_reached")
    return "batch%04d" % (int(last["batch_id"][5:]) + 1), min(1000, remaining, shard_remaining)


def prepare_config(directory, manifests, snapshot):
    """Only actual previous-manifest cursor; accumulated exact input hash links."""
    root = Path(directory)
    batch, count = next_window(manifests[-1])
    links, seen = [], set()
    for manifest in manifests:
        path = root / "preparation" / manifest["batch_id"] / "INPUTS_PRIVATE.jsonl"
        for line in path.read_text().splitlines():
            item = json.loads(line)
            context = item["row"]["context_sha256"]
            if context in seen:
                raise StopPipeline("duplicate_prepared_context_across_batches")
            seen.add(context)
            links.append({"context_sha256": context, "input_case": item["case"], "batch_id": manifest["batch_id"]})
    if len(seen) != manifests[-1]["cumulative_new_unique_contexts"]:
        raise StopPipeline("prior_context_links_not_complete")
    linkpath = root / "preparation" / (batch + "_FINITE_PRIOR_CONTEXT_LINKS_PRIVATE.jsonl")
    immutable(linkpath, b"".join(encoded(item) for item in links))
    exclusionpath = root / "preparation" / (batch + "_FINITE_RUNTIME_EXCLUSIONS_PRIVATE.json")
    immutable(exclusionpath, encoded({"context_sha256": sorted(set(snapshot["claims"]) | seen),
                                     "quarantined_contexts": snapshot["quarantined"]}))
    config = read(root / "preparation/batch0001_CONFIG_PRIVATE.json")
    config["previous_manifest"] = {"path": manifests[-1]["manifest_path"], "sha256": manifests[-1]["manifest_sha256"]}
    config["prior_context_links"] = {"path": str(linkpath), "sha256": sha(linkpath)}
    config["pilot_runtime_exclusions"] = {"path": str(exclusionpath), "sha256": sha(exclusionpath)}
    path = root / "preparation" / (batch + "_FINITE_CONFIG_PRIVATE.json")
    immutable(path, encoded(config))
    return batch, count, path


class Supervisor:
    def __init__(self, args):
        self.args, self.root = args, Path(args.directory).resolve()
        self.control = self.root / "control"
        self.control.mkdir(parents=True, exist_ok=True)
        self.statepath = self.control / "FINITE_PIPELINE_STATE_PUBLIC.json"
        self.stopfile = self.root / "STOP"
        self.policy_sha = sha(self.root / "policy.json")
        self.c5 = self.root.parents[1] / "confirmation_stage5_20261118/execution_v1"
        self.field = self.c5 / "repo/linkup/reuse_first_20261115/measurement_protocol_20261117/code/field_validation.py"
        self.frozen = self.c5 / "repo/linkup/formal800_20261012/code/validate_reviews.py"
        self.scorer = self.c5 / "protocol/field_score.py"
        self.amendment = self.root / "RATE_AMENDMENT_PUBLIC.json"
        files = [Path(__file__), self.root / "policy.json", self.root / "runtime/pilot_worker.py",
                 self.root / "runtime/pilot_common.py", self.root / "runtime_v2/pilot_worker_v2.py",
                 self.root / "runtime_v2/rate_amendment.py", self.root / "preparation/prepare_physical.py",
                 self.root / "preparation/cloud_controller.py", self.root / "preparation/batch0001_CONFIG_PRIVATE.json",
                 self.root / "rules/run_cpu_batch.py", self.root / "rules/cpu_candidates.py",
                 self.root / "rules/frozen_vocabulary.py", self.root / "measurement/publish_physical_v2.py",
                 self.field, self.frozen, self.scorer]
        self.pins = {str(path): sha(path) for path in files}
        immutable(self.control / "FINITE_PIPELINE_CODE_PINS_PUBLIC.json", encoded({"version": VERSION, "sha256": self.pins,
                  "policy_sha256": self.policy_sha, "financial_caps_unchanged": True}))
        if self.statepath.exists():
            self.state = read(self.statepath)
            if self.state["policy_sha256"] != self.policy_sha:
                raise StopPipeline("supervisor_policy_identity_changed")
        else:
            self.state = {"version": VERSION, "policy_sha256": self.policy_sha, "started_epoch": time.time(),
                          "events": 0, "completed_batches": [], "controller_pid": os.getpid()}
        self.deadline = self.state["started_epoch"] + min(args.max_wall_seconds, MAX_WALL)

    def checkpoint(self, status, **extra):
        self.state.update(status=status, at_utc=datetime.now(timezone.utc).isoformat(), controller_pid=os.getpid(), **extra)
        # Report only committed actual manifest cursors, never an attempted offset.
        manifests = manifest_chain(self.root, allow_partial=True)
        if manifests:
            last = manifests[-1]
            self.state.update(last_committed_batch=last["batch_id"], last_committed_manifest_sha256=last["manifest_sha256"],
                              end_cursor_exclusive=last["end_cursor_exclusive"], physical_rows_prepared=last["cumulative_physical_rows"])
        atomic(self.statepath, self.state)

    def guards(self, *, allow_active=False):
        if self.stopfile.exists():
            raise StopPipeline("operator_stop_file")
        if time.time() >= self.deadline:
            immutable(self.stopfile, b"finite_pipeline_wall_limit\n")
            raise StopPipeline("finite_48h_wall_limit")
        if sha(self.root / "policy.json") != self.policy_sha:
            raise StopPipeline("original_policy_changed")
        snapshot = ledger_snapshot(self.root)
        identity = json.loads(snapshot["meta"].get("identity", "{}"))
        if identity.get("policy_sha256") != self.policy_sha:
            raise StopPipeline("shared_ledger_policy_identity_mismatch")
        if snapshot["meta"].get("global_hold"):
            raise StopPipeline("global_admission_hold_preserved")
        if snapshot["states"].get("transport_uncertain_no_retry", 0):
            raise StopPipeline("uncertain_transport_no_retry")
        active = active_workers(self.root)
        if not active and snapshot["states"].get("forwarding_uncertain", 0):
            raise StopPipeline("orphan_forwarding_requires_inspection")
        if not allow_active and active:
            raise StopPipeline("another_model_leg_or_amendment_active")
        if snapshot["reserved_nano"] >= PILOT_CAP_NANO:
            raise StopPipeline("persistent_150usd_pilot_cap_reached")
        return snapshot, active

    def wait_quiescent(self):
        while True:
            _, active = self.guards(allow_active=True)
            if not active:
                self.state["active_worker_pids"] = []
                return
            self.checkpoint("waiting_existing_finite_workers", active_worker_pids=active)
            time.sleep(min(10, max(0.01, self.deadline - time.time())))

    def execute(self, command, stage, *, model=False, timeout=300):
        self.guards()
        for path, expected in self.pins.items():
            if sha(path) != expected:
                raise StopPipeline("pinned_code_changed_during_finite_pipeline")
        self.state["events"] += 1
        number = self.state["events"]
        logfile = self.control / ("FINITE_%04d_%s_PRIVATE.log" % (number, stage))
        self.checkpoint("executing_" + stage, stage=stage)
        with logfile.open("xb") as stream:
            child = subprocess.Popen(command, cwd=self.root, stdin=subprocess.DEVNULL, stdout=stream,
                                     stderr=subprocess.STDOUT, start_new_session=True)
            self.checkpoint("executing_" + stage, child_pid=child.pid, child_log=logfile.name)
            step_deadline = min(self.deadline, time.time() + timeout)
            while child.poll() is None:
                try:
                    self.guards(allow_active=True)
                    if time.time() >= step_deadline:
                        raise StopPipeline("stage_wall_limit_" + stage)
                except StopPipeline:
                    # Never kill an in-flight model request or treat an unknown
                    # transport as retryable. STOP blocks further admissions.
                    if model:
                        if not self.stopfile.exists():
                            immutable(self.stopfile, b"finite_pipeline_bounded_stop\n")
                        self.checkpoint("stopping_worker_new_admissions", child_pid=child.pid)
                    else:
                        child.terminate()
                        try:
                            child.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            child.kill()
                            child.wait(timeout=10)
                    raise
                time.sleep(min(2, max(0.01, step_deadline - time.time())))
        event = {"stage": stage, "returncode": child.returncode, "log_sha256": sha(logfile),
                 "policy_sha256": self.policy_sha, "at_utc": datetime.now(timezone.utc).isoformat()}
        immutable(self.control / ("FINITE_%04d_%s_EXECUTION_PUBLIC.json" % (number, stage)), encoded(event))
        if child.returncode:
            raise StopPipeline("processor_failed_" + stage)

    def ensure_amendment(self):
        self.wait_quiescent()
        script = self.root / "runtime_v2/rate_amendment.py"
        snapshot, _ = self.guards()
        if not snapshot["meta"].get("scheduler_rate_amendment_v2"):
            if not self.args.prepare_and_apply_rate_amendment:
                raise StopPipeline("quiescent_rate_amendment_must_be_registered")
            if not self.amendment.exists():
                self.execute([sys.executable, "-B", str(script), "prepare", "--directory", str(self.root),
                              "--output", str(self.amendment)], "rate_prepare", timeout=180)
            self.execute([sys.executable, "-B", str(script), "apply", "--directory", str(self.root),
                          "--amendment", str(self.amendment), "--amendment-sha256", sha(self.amendment)], "rate_apply", timeout=180)
        snapshot, _ = self.guards()
        registration = json.loads(snapshot["meta"].get("scheduler_rate_amendment_v2", "{}"))
        if registration.get("amendment_sha256") != sha(self.amendment) or registration.get("effective_scheduler_tpm") != 200000:
            raise StopPipeline("rate_amendment_identity_or_200k_mismatch")

    def luna_finished(self, manifest):
        output = self.root / ("OUTPUTS_LUNA_%s_PRIVATE.jsonl" % manifest["batch_id"])
        if not output.exists():
            return False
        rows = [json.loads(line) for line in output.read_text().splitlines()]
        if len(rows) != manifest["new_unique_contexts"]:
            raise StopPipeline("existing_Luna_batch_output_count_mismatch")
        input_path = self.root / "preparation" / manifest["batch_id"] / "INPUTS_PRIVATE.jsonl"
        expected_contexts = {json.loads(line)["row"]["context_sha256"] for line in input_path.read_text().splitlines()}
        if {row.get("context_sha256") for row in rows} != expected_contexts:
            raise StopPipeline("existing_Luna_batch_context_roster_mismatch")
        conn = sqlite3.connect((self.root / "ADMISSION_PRIVATE.sqlite3").as_uri() + "?mode=ro", uri=True)
        try:
            latest = {row[0]: row[1:] for row in conn.execute("SELECT context,state,result_path,result_sha FROM attempts WHERE leg='Luna' ORDER BY id")}
        finally:
            conn.close()
        pending = False
        for row in rows:
            if row.get("policy_sha256") != self.policy_sha or row.get("batch_manifest_sha256") != manifest["manifest_sha256"]:
                raise StopPipeline("existing_Luna_batch_output_identity_mismatch")
            previous = latest.get(row["context_sha256"])
            if previous and previous[1]:
                path = (self.root / previous[1]).resolve()
                if not path.is_relative_to(self.root) or sha(path) != previous[2]:
                    raise StopPipeline("existing_individual_result_sha_mismatch")
                # Existing immutable results will be cache hits even if a prior
                # aggregate was interrupted before it included them.
                if row.get("status") == "unprocessed_bounded_stop":
                    pending = True
            elif row.get("status") == "unprocessed_bounded_stop":
                pending = True
            else:
                raise StopPipeline("batch_row_without_saved_terminal_result")
        return not pending

    def process_batch(self, manifest):
        batch = manifest["batch_id"]
        self.wait_quiescent()
        if not self.luna_finished(manifest):
            prior_output = self.root / ("OUTPUTS_LUNA_%s_PRIVATE.jsonl" % batch)
            if prior_output.exists():
                immutable(self.control / (batch + "_LUNA_PRE_RESUME_" + sha(prior_output) + "_PRIVATE.jsonl"), prior_output.read_bytes())
            command = [sys.executable, "-B", str(self.root / "runtime_v2/pilot_worker_v2.py"),
                "--rate-amendment", str(self.amendment), "--rate-amendment-sha256", sha(self.amendment),
                "--leg", "Luna", "--directory", str(self.root), "--policy", str(self.root / "policy.json"),
                "--batch-manifest", manifest["manifest_path"], "--batch-manifest-sha256", manifest["manifest_sha256"],
                "--field-validator", str(self.field), "--frozen-validator", str(self.frozen),
                "--workflow-directory", str(self.root.parents[1] / "code"), "--max-new-logical", "100" if batch == "batch0001" else "10000",
                "--concurrency", str(self.args.concurrency), "--max-wall-seconds", str(min(14400, max(1, int(self.deadline - time.time())))),
                "--stop-file", str(self.stopfile)]
            self.execute(command, batch + "_luna", model=True, timeout=min(14400, self.deadline - time.time()))
            if not self.luna_finished(manifest):
                raise StopPipeline("worker_exit_without_complete_batch_output")
        final_path = self.root / "LUNA_FINAL_PUBLIC.json"
        if final_path.exists() and read(final_path).get("batch_manifest_sha256") == manifest["manifest_sha256"]:
            immutable(self.control / (batch + "_LUNA_FINAL_ARCHIVE_PUBLIC.json"), final_path.read_bytes())
        folder = self.root / "preparation" / batch
        self.execute([sys.executable, "-B", str(self.root / "rules/run_cpu_batch.py"),
            "--input", str(folder / "INPUTS_PRIVATE.jsonl"), "--output", str(folder / "CPU_RULE_RESULTS_PRIVATE.jsonl"),
            "--receipt", str(folder / "CPU_RULE_RECEIPT_PUBLIC.json"), "--cache", str(self.root / "cache/cpu_rules.sqlite"),
            "--max-records", "10000"], batch + "_cpu", timeout=300)
        projection = self.root / "projection" / batch
        receipt_path = projection / "PHYSICAL_PROJECTION_PUBLIC.json"
        if projection.exists():
            if not receipt_path.is_file():
                raise StopPipeline("existing_projection_without_receipt")
            receipt = read(receipt_path)
            if receipt.get("through_batch") != batch or receipt.get("policy_sha256") != self.policy_sha:
                raise StopPipeline("existing_projection_identity_mismatch")
            if receipt.get("projection_code_sha256") != sha(self.root / "measurement/publish_physical_v2.py"):
                raise StopPipeline("existing_projection_code_version_mismatch")
            for name, expected in receipt["sha256"].items():
                if sha(projection / name) != expected:
                    raise StopPipeline("existing_projection_sha_mismatch")
        else:
            self.execute([sys.executable, "-B", str(self.root / "measurement/publish_physical_v2.py"),
                "--directory", str(self.root), "--through-batch", batch, "--output", str(projection),
                "--scorer", str(self.scorer), "--scorer-sha256", sha(self.scorer),
                "--frozen-validator", str(self.frozen), "--frozen-validator-sha256", sha(self.frozen)], batch + "_projection", timeout=300)
        receipt = read(receipt_path)
        if not receipt.get("physical_row_conservation") or receipt.get("physical_rows") != manifest["cumulative_physical_rows"]:
            raise StopPipeline("projection_physical_conservation_failed")
        archive = {"batch_id": batch, "manifest_sha256": manifest["manifest_sha256"],
                   "end_cursor_exclusive": manifest["end_cursor_exclusive"],
                   "cumulative_physical_rows": manifest["cumulative_physical_rows"],
                   "Luna_output_sha256": sha(self.root / ("OUTPUTS_LUNA_%s_PRIVATE.jsonl" % batch)),
                   "CPU_receipt_sha256": sha(folder / "CPU_RULE_RECEIPT_PUBLIC.json"),
                   "projection_receipt_sha256": sha(receipt_path), "policy_sha256": self.policy_sha,
                   "field_failures_remain_explicit": True, "whole_target_complete": False}
        immutable(self.control / (batch + "_FINITE_COMPLETE_PUBLIC.json"), encoded(archive))
        if batch not in self.state["completed_batches"]:
            self.state["completed_batches"].append(batch)
        self.checkpoint("batch_complete", current_batch=batch, child_pid=None)

    def run(self):
        manifests = manifest_chain(self.root)
        if len(manifests) < 2 or manifests[0]["physical_rows"] != 100 or manifests[1]["physical_rows"] != 900:
            raise StopPipeline("existing_100_plus_900_manifest_prefix_required")
        self.ensure_amendment()
        # Max 11 manifests: initial 100+900, then nine 1000-row windows.
        for _ in range(11):
            manifests = manifest_chain(self.root)
            for manifest in manifests:
                if manifest["batch_id"] not in self.state["completed_batches"]:
                    self.process_batch(manifest)
            snapshot, _ = self.guards()
            batch, count, config = prepare_config(self.root, manifests, snapshot)
            self.execute([sys.executable, "-B", str(self.root / "preparation/prepare_physical.py"),
                "--controller", str(self.root / "preparation/cloud_controller.py"),
                "--controller-sha256", sha(self.root / "preparation/cloud_controller.py"),
                "--config", str(config), "--config-sha256", sha(config), "--batch-id", batch,
                "--row-limit", str(count), "--output", str(self.root / "preparation" / batch)], batch + "_prepare", timeout=300)
        raise StopPipeline("finite_iteration_limit")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=CLOUD_RUN)
    parser.add_argument("--concurrency", type=int, choices=(2, 4), default=2)
    parser.add_argument("--max-wall-seconds", type=int, default=MAX_WALL)
    parser.add_argument("--prepare-and-apply-rate-amendment", action="store_true")
    args = parser.parse_args()
    if args.directory.resolve() != CLOUD_RUN or not 1 <= args.max_wall_seconds <= MAX_WALL:
        parser.error("original cloud run and wall bound <=48h required")
    os.umask(0o077)
    supervisor = None
    try:
        (args.directory / "control").mkdir(parents=True, exist_ok=True)
        with controller_lock(args.directory):
            supervisor = Supervisor(args)
            supervisor.run()
    except Exception as exc:
        reason = str(exc) if isinstance(exc, StopPipeline) else type(exc).__name__
        if supervisor is not None:
            try:
                supervisor.checkpoint("finite_pipeline_stopped", stop_reason=reason)
            except Exception:
                supervisor.state.update(status="finite_pipeline_stopped", stop_reason=reason,
                                        checkpoint_refresh_failed=True)
                atomic(supervisor.statepath, supervisor.state)
        print(json.dumps({"status": "finite_pipeline_stopped", "reason": reason,
                          "whole_target_complete": False, "no_budget_reset": True}), flush=True)
        return 0 if reason in ("physical_pilot_limit_reached", "actual_source_shard_boundary_reached") else 2


if __name__ == "__main__":
    raise SystemExit(main())
