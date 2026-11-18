"""One explicitly authorized engineering segment; retained declarations only.

The run001 database is SHA-pinned and copied, never edited. Historical pins and
elapsed time remain intact. Only later source row IDs are inspected using the
unchanged, SHA-pinned v1 declaration parser. No raw text, models, new semantic
acceptance, or source-text offset reverification occurs here.
"""
import argparse
from contextlib import contextmanager
from dataclasses import dataclass
import datetime
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import signal
import sqlite3
import time


VERSION = "retained-evidence-readiness-resume-v2"
LEGACY_CODE_SHA256 = "4f302676a07a62d4ac0cc80316963d86d7aad4c5ce2072d68ca66f693955c2a1"
DB_NAME = "EVIDENCE_READINESS_V1_PRIVATE.sqlite"
REPORT_NAME = "EVIDENCE_READINESS_PUBLIC.json"
PRIVATE_PROVENANCE_NAME = "RESUME_PROVENANCE_PRIVATE.json"
MAX_SECONDS = 300
MAX_ATOMS = 200000
MAX_MEMORY = 1024 ** 3
MAX_DISK = 1024 ** 3
FINALIZATION_RESERVE_SECONDS = 30
MAX_INVENTORY_ENTRIES = 10000
MAX_INVENTORY_DEPTH = 16


@dataclass(frozen=True)
class Checkpoint:
    database_sha256: str
    report_sha256: str
    database_bytes: int
    total_atoms: int
    processed_atoms: int
    remaining_atoms: int
    elapsed_seconds: float
    status: str = "time_cap_reached_cursor_preserved"


PRODUCTION_CHECKPOINT = Checkpoint(
    "d0193724c1d5c6d95d42c03872bf18d55b6b4e4b5fc6125cf0ec358176821bf8",
    "8674bc8c7a778513cc7b83a531af7c9a1ba0236b7450a223f44886ddaca8aef3",
    487383040, 180888, 126000, 54888, 300.158792429138)


class WindowExceeded(Exception):
    pass


def check_time(deadline):
    if time.monotonic() >= deadline:
        raise WindowExceeded("authorized_additional_window_exhausted")


def file_sha(path, deadline):
    result = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            check_time(deadline)
            result.update(block)
    check_time(deadline)
    return result.hexdigest()


def load_legacy(path):
    path = Path(path).resolve()
    code = path.read_bytes()
    if hashlib.sha256(code).hexdigest() != LEGACY_CODE_SHA256:
        raise ValueError("legacy_code_sha256_changed")
    spec = importlib.util.spec_from_file_location("sha_pinned_evidence_readiness_v1", path)
    module = importlib.util.module_from_spec(spec)
    # Execute exactly the verified source bytes. Do not read or create .pyc files
    # inside the preserved prior run, even when the caller omitted Python -B.
    exec(compile(code, str(path), "exec"), module.__dict__)
    return module


@contextmanager
def alarm(deadline):
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    def timeout_handler(signum, frame):
        raise WindowExceeded("authorized_additional_scan_window_exhausted")
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.setitimer(signal.ITIMER_REAL, max(.001, deadline - time.monotonic()))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer)
        signal.signal(signal.SIGALRM, previous_handler)


def inventory(directory, legacy):
    records = {}
    pending = [(directory, 0)]
    while pending:
        parent, depth = pending.pop()
        for path in sorted(parent.iterdir()):
            if len(records) >= MAX_INVENTORY_ENTRIES:
                raise ValueError("prior_directory_inventory_entry_limit")
            if path.is_symlink():
                raise ValueError("prior_directory_has_unsupported_member")
            relative = str(path.relative_to(directory))
            if path.is_dir():
                if depth + 1 > MAX_INVENTORY_DEPTH:
                    raise ValueError("prior_directory_inventory_depth_limit")
                records[relative] = {"kind": "directory", **legacy.fingerprint(path)}
                pending.append((path, depth + 1))
            elif path.is_file():
                if path.name.endswith(("-journal", "-wal", "-shm")):
                    raise ValueError("prior_database_not_closed_snapshot")
                records[relative] = {"kind": "file", **legacy.fingerprint(path)}
            else:
                raise ValueError("prior_directory_has_unsupported_member")
    return records


def load_checkpoint(prior, expected, legacy, deadline):
    destination = prior / DB_NAME
    if destination.stat().st_size != expected.database_bytes:
        raise ValueError("prior_database_size_changed")
    if file_sha(destination, deadline) != expected.database_sha256:
        raise ValueError("prior_database_sha256_changed")
    if file_sha(prior / REPORT_NAME, deadline) != expected.report_sha256:
        raise ValueError("prior_report_sha256_changed")
    report = legacy.read_json(prior / REPORT_NAME)
    required_report = {
        "status": expected.status, "total_evidence_atoms": expected.total_atoms,
        "processed_evidence_atoms": expected.processed_atoms,
        "remaining_allowed_evidence_atoms": expected.remaining_atoms,
        "elapsed_seconds_cumulative": expected.elapsed_seconds,
        "output_database_sha256": expected.database_sha256,
        "output_database_bytes": expected.database_bytes,
        "new_model_calls": 0, "new_production_accepted": 0,
        "offsets_reverified_against_text": False, "output_hash_status": "complete"}
    if any(report.get(k) != v for k, v in required_report.items()):
        raise ValueError("prior_report_checkpoint_mismatch")
    with legacy.connect_ro(destination) as db:
        metadata = {r[0]: json.loads(r[1]) for r in db.execute("SELECT key,value_json FROM run_metadata")}
        if set(metadata) != {"pins", "progress", "input_counts"}:
            raise ValueError("prior_metadata_not_original_v1_checkpoint")
        pins, progress, counts = (metadata[k] for k in ("pins", "progress", "input_counts"))
        actual, maximum = db.execute("SELECT COUNT(*),MAX(source_rowid) FROM evidence_readiness").fetchone()
    db.close()
    if (pins.get("code_sha256") != LEGACY_CODE_SHA256 or
            pins.get("version") != legacy.VERSION or
            not 0 < pins.get("max_atoms_cumulative", 0) <= MAX_ATOMS or
            not 0 < pins.get("max_seconds_cumulative", 0) <= MAX_SECONDS):
        raise ValueError("prior_code_or_resource_pins_invalid")
    if (actual != expected.processed_atoms or progress["processed_atoms"] != actual or
            (maximum or 0) != progress["cursor_rowid"] or
            report["cursor_rowid"] != progress["cursor_rowid"] or
            progress["elapsed_seconds"] != expected.elapsed_seconds or
            progress["status"] != expected.status or
            counts["total_evidence_atoms"] != expected.total_atoms or
            counts["processable_evidence_atoms"] - actual != expected.remaining_atoms):
        raise ValueError("prior_count_cursor_or_elapsed_mismatch")
    for name in ("state_counts", "trace_counts", "workflow_counts", "measurement_counts"):
        if sum(progress[name].values()) != actual:
            raise ValueError("prior_aggregate_counts_inconsistent")
    if actual >= pins["max_atoms_cumulative"]:
        raise ValueError("inherited_atom_cap_already_exhausted_no_extension")
    return metadata


def current_sources(root, pins, legacy):
    source_path = root / "reuse_execution_20261117/run001/LINKUP_REUSED_VARIABLES_V1_PRIVATE.sqlite"
    release_path = source_path.parent / "STEP1_RELEASE_PUBLIC.json"
    state_path = root / "execution_20261116/run001/AZURE_RESEARCH_STATE.json"
    release, state = legacy.read_json(release_path), legacy.read_json(state_path)
    runtime_path = legacy.safe_child(root, state["runtime_exclusions_relative_to_migration"])
    original_path = legacy.safe_child(root, state["database_relative_to_migration"])
    # Fail before any saved value read if the materialization/guard snapshot moved.
    current = dict(pins)
    current.update({
        "source_stat": legacy.fingerprint(source_path),
        "original_protection_source_stat": legacy.fingerprint(original_path),
        "release_sha256": legacy.digest(release_path.read_bytes()),
        "state_sha256": legacy.digest(state_path.read_bytes()),
        "runtime_exclusions_sha256": legacy.digest(runtime_path.read_bytes()),
        "source_database_sha256_from_previous_release": release["private_output_sha256"],
        "code_sha256": legacy.digest(Path(legacy.__file__).read_bytes())})
    if current != pins or not release.get("first_materialized_release_complete"):
        raise ValueError("current_source_protection_or_code_pins_changed")
    if release["private_output_bytes"] != current["source_stat"]["size"]:
        raise ValueError("current_source_release_size_mismatch")
    runtime = legacy.read_json(runtime_path)
    if (not isinstance(runtime, dict) or not isinstance(runtime.get("context_sha256"), list) or
            not all(isinstance(h, str) and legacy.HEX64.fullmatch(h) for h in runtime["context_sha256"])):
        raise ValueError("runtime_protection_shape_invalid")
    source = legacy.connect_ro(source_path)
    try:
        with legacy.connect_ro(original_path) as original:
            denied = set(runtime["context_sha256"])
            denied.update(r[0] for r in source.execute(
                "SELECT h FROM context_state WHERE reuse_excluded=1 OR original_protected=1"))
            denied.update(r[0] for r in original.execute("SELECT h FROM protected"))
        original.close()
        if (not all(isinstance(h, str) and legacy.HEX64.fullmatch(h) for h in denied) or
                legacy.digest(legacy.canon(sorted(denied)).encode()) != pins["exclusion_union_sha256"]):
            raise ValueError("current_protection_union_changed")
        if ([r[2] for r in source.execute("PRAGMA index_info(variable_key)")] != ["variable_key"] or
                [r[2] for r in source.execute("PRAGMA index_info(variable_context)")] != ["h", "variable_key"]):
            raise ValueError("required_existing_index_not_available_no_full_scan")
    except BaseException:
        source.close()
        raise
    def unchanged():
        return (legacy.fingerprint(source_path) == pins["source_stat"] and
                legacy.fingerprint(original_path) == pins["original_protection_source_stat"] and
                legacy.digest(runtime_path.read_bytes()) == pins["runtime_exclusions_sha256"] and
                legacy.digest(state_path.read_bytes()) == pins["state_sha256"] and
                legacy.digest(release_path.read_bytes()) == pins["release_sha256"] and
                legacy.digest(Path(legacy.__file__).read_bytes()) == LEGACY_CODE_SHA256)
    return source, denied, unchanged


def clone_closed_database(prior, destination, expected, deadline):
    result = hashlib.sha256()
    with prior.open("rb") as src, destination.open("xb") as dst:
        for block in iter(lambda: src.read(4 * 1024 * 1024), b""):
            check_time(deadline)
            dst.write(block)
            result.update(block)
        dst.flush()
        os.fsync(dst.fileno())
    if result.hexdigest() != expected:
        raise ValueError("copied_prior_database_sha256_mismatch")


def process_segment(source, db, destination, denied, unchanged, progress,
                    counts, cap, legacy, started, historical_elapsed, deadline):
    source.create_function("context_allowed", 1, lambda h: int(isinstance(h, str) and h not in denied))
    source.set_progress_handler(lambda: int(time.monotonic() >= deadline), 10000)
    def checkpoint(status):
        progress["status"] = status
        progress["elapsed_seconds"] = historical_elapsed + time.monotonic() - started
        db.execute("UPDATE run_metadata SET value_json=? WHERE key='progress'", (legacy.canon(progress),))
        db.commit()
    status = "scanning_remaining_retained_evidence_declarations"
    try:
        with alarm(deadline):
            while progress["processed_atoms"] < min(cap, counts["processable_evidence_atoms"]):
                check_time(deadline)
                if not unchanged():
                    status = "input_or_protection_changed_preserve_output"; break
                disk = sum(p.stat().st_size for p in (destination, Path(str(destination) + "-journal")) if p.exists())
                if disk >= MAX_DISK:
                    status = "output_disk_cap_reached_cursor_preserved"; break
                n = min(legacy.BATCH, cap - progress["processed_atoms"])
                # Exact v1 metadata-first query and parser, cursor strictly increases.
                rows = source.execute("""SELECT v.rowid AS source_rowid,v.id,v.d,v.h,v.k,v.source_path,
                    v.item_anchor_json,v.measurement_state,v.workflow_state,v.engineering_state,
                    v.eligible_original_scope,v.original_mask,v.metadata_json,
                    s.d AS source_d,s.h AS source_h,s.k AS source_k,s.asset,s.source_sha,s.source_ordinal
                    FROM variable_value v INDEXED BY variable_key
                    LEFT JOIN source_document s ON s.d=v.d
                    WHERE v.variable_key=? AND v.rowid>? AND context_allowed(v.h)=1
                    ORDER BY v.rowid LIMIT ?""", (legacy.VARIABLE, progress["cursor_rowid"], n)).fetchall()
                if not rows:
                    status = "source_cursor_exhausted"; break
                traces = {row["source_rowid"]: legacy.anchor_trace(row) for row in rows}
                allowed_ids = [row["source_rowid"] for row in rows if traces[row["source_rowid"]][0] == "complete_retained_source_anchor_binding"]
                payloads = {}
                if allowed_ids:
                    marks = ",".join("?" for _ in allowed_ids)
                    payloads = dict(source.execute("SELECT rowid,CASE WHEN length(value_json)<=? THEN value_json ELSE NULL END FROM variable_value WHERE rowid IN (" + marks + ") AND variable_key=? AND context_allowed(h)=1", (legacy.MAX_VALUE_BYTES, *allowed_ids, legacy.VARIABLE)))
                updates = json.loads(legacy.canon(progress))
                db.execute("BEGIN")
                for row in rows:
                    check_time(deadline)
                    trace, anchor = traces[row["source_rowid"]]
                    if trace == "complete_retained_source_anchor_binding" and payloads[row["source_rowid"]] is not None:
                        result = legacy.inspect_declarations(payloads[row["source_rowid"]], row["source_path"], anchor)
                    elif trace == "complete_retained_source_anchor_binding":
                        result = {"state": "payload_over_bounded_parser_limit", "full_text_reverified": False, "new_semantic_acceptance": False}
                    else:
                        result = {"state": "source_trace_incomplete_payload_not_read", "full_text_reverified": False, "new_semantic_acceptance": False}
                    values = (row["source_rowid"],row["id"],row["d"],row["h"],row["k"],row["source_path"],
                        row["item_anchor_json"],row["asset"],row["source_sha"],row["source_ordinal"],
                        row["measurement_state"],row["workflow_state"],row["engineering_state"],
                        row["eligible_original_scope"],row["original_mask"],row["metadata_json"],
                        trace,result["state"],legacy.canon(result),0,0)
                    db.execute("INSERT INTO evidence_readiness VALUES(" + ",".join("?" for _ in values) + ")", values)
                    for name, value in (("state_counts", result["state"]), ("trace_counts", trace),
                                        ("workflow_counts", row["workflow_state"]), ("measurement_counts", row["measurement_state"])):
                        value = str(value)
                        updates[name][value] = updates[name].get(value, 0) + 1
                    updates["processed_atoms"] += 1
                    updates["cursor_rowid"] = row["source_rowid"]
                check_time(deadline)
                if not unchanged():
                    db.rollback(); status = "input_or_protection_changed_preserve_output"; break
                progress = updates
                checkpoint("scanning_remaining_retained_evidence_declarations")
            if progress["processed_atoms"] == counts["processable_evidence_atoms"]:
                status = "all_current_allowed_evidence_atoms_audited_not_reverified"
            elif progress["processed_atoms"] >= cap:
                status = "atom_cap_reached_cursor_preserved"
    except (sqlite3.OperationalError, WindowExceeded, legacy.TimeBudgetExceeded) as error:
        db.rollback()
        progress = json.loads(db.execute("SELECT value_json FROM run_metadata WHERE key='progress'").fetchone()[0])
        if (isinstance(error, sqlite3.OperationalError) and "interrupted" not in str(error).lower()
                and time.monotonic() < deadline):
            raise
        status = "time_cap_reached_cursor_preserved"
    finally:
        source.set_progress_handler(None, 0)
    checkpoint(status)
    return progress


def run(root, prior, output, legacy_code, additional_seconds=MAX_SECONDS,
        expected=PRODUCTION_CHECKPOINT):
    started = time.monotonic()
    if not 0 < additional_seconds <= MAX_SECONDS:
        raise ValueError("additional_window_exceeds_authorized_limit")
    deadline = started + additional_seconds
    scan_deadline = deadline - min(FINALIZATION_RESERVE_SECONDS, additional_seconds * .2)
    root, prior, output = map(lambda p: Path(p).resolve(), (root, prior, output))
    if root not in prior.parents or root not in output.parents or prior == output:
        raise ValueError("run_directories_must_be_distinct_children_of_root")
    if output.exists():
        raise FileExistsError("existing_run002_preserved_no_restart_or_overwrite")
    legacy = load_legacy(legacy_code)
    # Lock the old runner without creating or writing a single run001 file.
    with (prior / "READINESS.lock").open("rb") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        prior_inventory = inventory(prior, legacy)
        with alarm(scan_deadline):
            metadata = load_checkpoint(prior, expected, legacy, scan_deadline)
            pins, progress, counts = (metadata[k] for k in ("pins", "progress", "input_counts"))
            source, denied, unchanged = current_sources(root, pins, legacy)
        db = None
        try:
            with alarm(scan_deadline):
                output.mkdir(parents=True, mode=0o700, exist_ok=False)
                destination = output / DB_NAME
                clone_closed_database(prior / DB_NAME, destination, expected.database_sha256, scan_deadline)
                provenance = {
                    "version": VERSION, "authorization": "user_continue_2026-11-18_Asia_Shanghai",
                    "prior_directory_relative_to_root": str(prior.relative_to(root)),
                    "prior_database_sha256": expected.database_sha256,
                    "prior_report_sha256": expected.report_sha256,
                    "inherited_pins": json.loads(legacy.canon(pins)),
                    "inherited_progress": json.loads(legacy.canon(progress)),
                    "inherited_input_counts": json.loads(legacy.canon(counts)),
                    "inherited_elapsed_seconds": progress["elapsed_seconds"],
                    "additional_window_seconds": additional_seconds,
                    "additional_window_includes_preflight_clone_scan_and_hash": True,
                    "effective_cumulative_time_cap_seconds": progress["elapsed_seconds"] + additional_seconds,
                    "max_atoms_cumulative_unchanged": pins["max_atoms_cumulative"],
                    "legacy_parser_code_sha256": LEGACY_CODE_SHA256,
                    "resume_code_sha256": legacy.digest(Path(__file__).read_bytes()),
                    "financial_envelope_usd_unchanged": 450,
                    "raw_documents_read": False, "new_model_calls": 0,
                    "new_semantic_acceptance": 0, "offsets_reverified_against_text": False}
                db = sqlite3.connect(destination)
                db.executescript("PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL; PRAGMA cache_size=-16384; PRAGMA temp_store=FILE;")
                db.execute("INSERT INTO run_metadata VALUES('resume_segment_v2',?)", (legacy.canon(provenance),))
                db.commit()
                legacy.save_json(output / PRIVATE_PROVENANCE_NAME, provenance)
            history_elapsed = progress["elapsed_seconds"]
            inherited_count, inherited_cursor = progress["processed_atoms"], progress["cursor_rowid"]
            progress = process_segment(source, db, destination, denied, unchanged, progress,
                counts, pins["max_atoms_cumulative"], legacy, started, history_elapsed, scan_deadline)
            source_unchanged = unchanged()
            prior_unchanged = inventory(prior, legacy) == prior_inventory
            if not source_unchanged or not prior_unchanged:
                progress["status"] = "input_or_prior_checkpoint_changed_preserve_output"
                db.execute("UPDATE run_metadata SET value_json=? WHERE key='progress'", (legacy.canon(progress),))
                db.commit()
            actual, cursor = db.execute("SELECT COUNT(*),MAX(source_rowid) FROM evidence_readiness").fetchone()
            if actual != progress["processed_atoms"] or (cursor or 0) != progress["cursor_rowid"]:
                raise ValueError("new_sidecar_count_cursor_mismatch")
            db.close(); db = None
            source.close()
            try:
                output_sha = file_sha(destination, deadline)
                hash_status = "complete"
            except WindowExceeded:
                output_sha = None
                hash_status = "additional_window_exhausted_no_digest_claim"
            report = {
                "version": VERSION, "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "status": progress["status"], **counts,
                "processed_evidence_atoms": actual,
                "remaining_allowed_evidence_atoms": counts["processable_evidence_atoms"] - actual,
                "inherited_processed_evidence_atoms": inherited_count,
                "newly_audited_evidence_atoms": actual - inherited_count,
                "inherited_cursor_rowid": inherited_cursor, "cursor_rowid": progress["cursor_rowid"],
                "elapsed_seconds_cumulative": progress["elapsed_seconds"],
                "historical_elapsed_seconds_preserved": history_elapsed,
                "additional_engineering_elapsed_seconds": progress["elapsed_seconds"] - history_elapsed,
                "additional_window_wall_seconds": time.monotonic() - started,
                "additional_window_seconds": additional_seconds,
                "effective_cumulative_time_cap_seconds": history_elapsed + additional_seconds,
                "inherited_original_time_cap_seconds": pins["max_seconds_cumulative"],
                "max_atoms_cumulative": pins["max_atoms_cumulative"], "memory_limit_bytes": MAX_MEMORY,
                "excluded_context_union": len(denied), "state_counts": progress["state_counts"],
                "trace_counts": progress["trace_counts"], "original_workflow_counts": progress["workflow_counts"],
                "original_measurement_counts": progress["measurement_counts"],
                "output_database_bytes": destination.stat().st_size, "output_database_sha256": output_sha,
                "output_hash_status": hash_status, "prior_directory_stat_unchanged": prior_unchanged,
                "source_size_and_mtime_unchanged": source_unchanged,
                "source_database_sha256_from_previous_release": pins["source_database_sha256_from_previous_release"],
                "source_database_SHA_rehashed_this_run": False,
                "runtime_exclusions_sha256": pins["runtime_exclusions_sha256"],
                "no_raw_documents_read": True, "offsets_reverified_against_text": False,
                "new_model_calls": 0, "new_production_accepted": 0,
                "original_mask_and_measurement_states_preserved": True,
                "entire_delivery_or_all_variables_complete": False,
                "bounded_order_not_a_probability_sample": True,
                "resume_provenance": {
                    "version": VERSION, "authorization": provenance["authorization"],
                    "prior_database_sha256": expected.database_sha256,
                    "prior_report_sha256": expected.report_sha256,
                    "private_provenance_sha256": legacy.digest((output / PRIVATE_PROVENANCE_NAME).read_bytes()),
                    "inherited_elapsed_seconds": history_elapsed,
                    "additional_window_seconds": additional_seconds,
                    "effective_cumulative_time_cap_seconds": history_elapsed + additional_seconds,
                    "max_atoms_cumulative_unchanged": pins["max_atoms_cumulative"],
                    "legacy_parser_code_sha256": LEGACY_CODE_SHA256,
                    "resume_code_sha256": provenance["resume_code_sha256"],
                    "financial_envelope_usd_unchanged": 450},
                "notes": ["Evidence atoms are not distinct advertisements or complete field coverage.",
                    "Saved offsets remain unverified declarations; no new semantic acceptance is granted.",
                    "Original pins remain historical. The separate explicit resume authorization controls this segment.",
                    "The finalized database hash is computed only after SQLite closes; no digest is claimed on timeout."]}
            legacy.save_json(output / REPORT_NAME, report)
            return report
        finally:
            if db is not None:
                db.close()
            source.close()


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path.home() / "migration"))
    parser.add_argument("--prior")
    parser.add_argument("--output")
    parser.add_argument("--legacy-code", required=True)
    parser.add_argument("--additional-seconds", type=float, default=MAX_SECONDS)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY, MAX_MEMORY))
    root = Path(args.root)
    prior = Path(args.prior) if args.prior else root / "evidence_readiness_20261117/run001"
    output = Path(args.output) if args.output else root / "evidence_readiness_20261117/run002"
    try:
        report = run(root, prior, output, args.legacy_code, args.additional_seconds)
        keys = ("version", "status", "inherited_processed_evidence_atoms", "newly_audited_evidence_atoms",
                "processed_evidence_atoms", "remaining_allowed_evidence_atoms", "elapsed_seconds_cumulative",
                "additional_window_wall_seconds", "output_database_sha256", "output_hash_status",
                "source_size_and_mtime_unchanged", "prior_directory_stat_unchanged", "new_model_calls", "new_production_accepted")
        summary = {k: report[k] for k in keys}
        summary["full_report_sha256"] = hashlib.sha256((output / REPORT_NAME).read_bytes()).hexdigest()
        print(json.dumps(summary, ensure_ascii=False))
    except Exception as error:
        # Do not write over a prior or partially completed run on any failure.
        print(json.dumps({"status": "resume_preflight_or_execution_failed_preserved",
            "exception_type": type(error).__name__, "error_code": str(error)[:180],
            "new_model_calls": 0, "new_production_accepted": 0}))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
