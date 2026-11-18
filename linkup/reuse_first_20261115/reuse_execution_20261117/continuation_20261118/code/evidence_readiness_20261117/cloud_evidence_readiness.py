"""Bounded read-only audit of already materialized evidence declarations.

No raw documents, new evidence verification, model calls or acceptance changes.
The original validator emits JSON Pointer paths and Unicode-code-point spans.
This code checks only that the retained declaration binds to the same item and
is internally well formed; it does NOT verify any span against source text.
"""
import argparse
import collections
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import signal
import sqlite3
import time


VERSION = "retained-evidence-readiness-v1"
VARIABLE = "lk.evidence.ref"
MAX_ATOMS = 200000
MAX_SECONDS = 300
MAX_HASH_SECONDS = 30
MAX_MEMORY = 1024 ** 3
MAX_VALUE_BYTES = 1024 ** 2
MAX_DISK = 1024 ** 3
BATCH = 100
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class TimeBudgetExceeded(Exception):
    pass


def canon(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def save_json(path, value):
    temporary = Path(str(path) + ".tmp")
    with temporary.open("w") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def safe_child(root, relative):
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("unsafe_relative_input_locator")
    path = (root / relative).resolve()
    if root.resolve() not in path.parents:
        raise ValueError("input_outside_migration_root")
    return path


def fingerprint(path):
    s = path.stat()
    return {"size": s.st_size, "mtime_ns": s.st_mtime_ns,
            "device": s.st_dev, "inode": s.st_ino}


def connect_ro(path):
    db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA query_only=ON")
    db.execute("PRAGMA cache_size=-16384")
    db.execute("PRAGMA temp_store=FILE")
    return db


def quote_pointer(source_path, ordinal):
    """Only the explicit adapter path grammar; no fuzzy or quote-only joins."""
    pattern = r"[A-Za-z_][A-Za-z_0-9]*(?:\[\d+\])*(?:\.[A-Za-z_][A-Za-z_0-9]*(?:\[\d+\])*)*"
    if not isinstance(source_path, str) or not re.fullmatch(pattern, source_path):
        return None
    tokens = re.findall(r"[A-Za-z_][A-Za-z_0-9]*|\d+", source_path)
    return "/" + "/".join(tokens + [str(ordinal)])


def anchor_trace(row):
    """Retained source metadata only; never generates a new item anchor."""
    try:
        anchor = json.loads(row["item_anchor_json"])
    except (ValueError, TypeError):
        return "anchor_json_unavailable", None
    if not isinstance(anchor, dict):
        return "anchor_not_object", None
    expected = {"context_sha256": row["h"], "source_sha": row["source_sha"],
                "source_ordinal": row["source_ordinal"]}
    if (not row["source_d"] or row["source_h"] != row["h"] or
            row["source_k"] != row["k"] or
            not isinstance(row["source_sha"], str) or
            not HEX64.fullmatch(row["source_sha"]) or
            type(row["source_ordinal"]) is not int or row["source_ordinal"] < 0):
        return "source_document_binding_incomplete", anchor
    if (any(anchor.get(k) != v for k, v in expected.items()) or
            not isinstance(anchor.get("anchor_id"), str) or
            not HEX64.fullmatch(anchor["anchor_id"]) or
            type(anchor.get("item_index")) is not int or anchor["item_index"] < 0 or
            not isinstance(anchor.get("array_path"), str)):
        return "anchor_source_binding_inconsistent", anchor
    return "complete_retained_source_anchor_binding", anchor


def inspect_declarations(raw, source_path, anchor):
    """Parses saved labels only; all returned spans remain unverified claims."""
    out = {"state": "needs_structure_review", "quotes_count": 0,
           "bound_quote_declarations": 0, "declared_occurrences": 0,
           "repeated_occurrence_quotes": 0, "declarations": [],
           "quotes_sha256": None, "resolution_sha256": None,
           "source_value_sha256": digest(raw.encode()),
           "full_text_reverified": False, "new_semantic_acceptance": False}
    if len(raw.encode()) > MAX_VALUE_BYTES:
        out["state"] = "payload_over_bounded_parser_limit"
        return out
    try:
        value = json.loads(raw)
    except (ValueError, TypeError):
        out["state"] = "invalid_saved_value_json"
        return out
    if not isinstance(value, dict) or value.get("source_item_anchor") != anchor:
        out["state"] = "value_anchor_mismatch_or_unknown_shape"
        return out
    quotes, resolutions = value.get("quotes"), value.get("evidence_resolution")
    out["resolution_sha256"] = digest(canon(resolutions).encode())
    out["retained_verification_marker"] = value.get("verification")
    if not isinstance(quotes, list) or not all(isinstance(q, str) for q in quotes):
        out["state"] = "saved_quote_list_invalid"
        return out
    out["quotes_count"] = len(quotes)
    out["quotes_sha256"] = digest(canon(quotes).encode())
    if not quotes:
        out["state"] = "empty_quote_list_not_a_negative_or_complete_review"
        return out
    if resolutions in (None, []):
        out["state"] = "retained_quotes_without_offset_declarations"
        return out
    if not isinstance(resolutions, list) or len(resolutions) > 10000:
        out["state"] = "resolution_shape_unrecognized_or_over_limit"
        return out
    indexed = collections.defaultdict(list)
    for resolution in resolutions:
        if isinstance(resolution, dict) and isinstance(resolution.get("path"), str):
            indexed[resolution["path"]].append(resolution)
    inconsistent = False
    for i, quote in enumerate(quotes):
        pointer = quote_pointer(source_path, i)
        candidates = indexed.get(pointer, []) if pointer else []
        # One exact pointer record, not merely an equal quote elsewhere.
        if len(candidates) != 1 or candidates[0].get("quote") != quote:
            continue
        declaration = candidates[0]
        occurrences = declaration.get("occurrences")
        valid = (declaration.get("offset_unit") == "Unicode_code_points" and
                 isinstance(occurrences, list) and 0 < len(occurrences) <= 4096 and
                 type(declaration.get("repeated_ambiguity")) is bool and
                 declaration["repeated_ambiguity"] == (len(occurrences) > 1))
        if valid:
            valid = all(isinstance(span, dict) and type(span.get("start")) is int and
                        type(span.get("end")) is int and span["start"] >= 0 and
                        span["end"] > span["start"] and
                        span["end"] - span["start"] == len(quote)
                        for span in occurrences)
        if not valid:
            inconsistent = True
            continue
        out["bound_quote_declarations"] += 1
        out["declared_occurrences"] += len(occurrences)
        out["repeated_occurrence_quotes"] += len(occurrences) > 1
        out["declarations"].append({"quote_ordinal": i, "quote_sha256": digest(quote.encode()),
            "retained_pointer": pointer, "offset_unit": "Unicode_code_points",
            "occurrences": occurrences, "repeated_ambiguity": declaration["repeated_ambiguity"],
            "verification": "retained_declared_positions_not_reverified"})
    if out["bound_quote_declarations"] == len(quotes):
        out["state"] = ("all_quotes_have_retained_repeated_position_declarations" if
                        out["repeated_occurrence_quotes"] else
                        "all_quotes_have_retained_single_position_declarations")
    elif inconsistent:
        out["state"] = "retained_offsets_present_but_internally_inconsistent"
    elif out["bound_quote_declarations"]:
        out["state"] = "partial_same_item_offset_declarations"
    else:
        out["state"] = "retained_quotes_with_unbound_or_unrecognized_resolution"
    return out


SCHEMA = """
PRAGMA journal_mode=DELETE; PRAGMA synchronous=FULL; PRAGMA cache_size=-16384;
CREATE TABLE IF NOT EXISTS run_metadata(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS evidence_readiness(
 source_rowid INTEGER PRIMARY KEY, source_atom_id TEXT UNIQUE NOT NULL,
 source_document_id TEXT, context_fingerprint TEXT, ad_key TEXT,
 source_path TEXT, item_anchor_json TEXT, source_asset TEXT,
 origin_source_sha TEXT, origin_source_ordinal INTEGER,
 original_measurement_state TEXT, original_workflow_state TEXT,
 original_engineering_state TEXT, original_eligible_scope INTEGER,
 original_mask TEXT, original_metadata_json TEXT,
 source_trace_state TEXT NOT NULL, readiness_state TEXT NOT NULL,
 declaration_summary_json TEXT NOT NULL,
 full_text_reverified INTEGER NOT NULL CHECK(full_text_reverified=0),
 new_semantic_acceptance INTEGER NOT NULL CHECK(new_semantic_acceptance=0));
"""


def run(root, output, max_atoms=MAX_ATOMS, max_seconds=MAX_SECONDS):
    root, output = Path(root).resolve(), Path(output).resolve()
    if not (0 < max_atoms <= MAX_ATOMS and 0 < max_seconds <= MAX_SECONDS):
        raise ValueError("requested_bound_exceeds_authorized_limit")
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (output / "READINESS.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        previous_handler = signal.getsignal(signal.SIGALRM)
        previous_timer = signal.getitimer(signal.ITIMER_REAL)
        def timeout_handler(signum, frame):
            raise TimeBudgetExceeded()
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, max_seconds)
        try:
            return run_locked(root, output, max_atoms, max_seconds)
        finally:
            signal.setitimer(signal.ITIMER_REAL, *previous_timer)
            signal.signal(signal.SIGALRM, previous_handler)


def run_locked(root, output, max_atoms, max_seconds):
    started = time.monotonic()
    source_path = root / "reuse_execution_20261117/run001/LINKUP_REUSED_VARIABLES_V1_PRIVATE.sqlite"
    release_path = source_path.parent / "STEP1_RELEASE_PUBLIC.json"
    state_path = root / "execution_20261116/run001/AZURE_RESEARCH_STATE.json"
    # All required protection sources must exist and have their declared shape.
    release, state = read_json(release_path), read_json(state_path)
    if not release.get("first_materialized_release_complete"):
        raise ValueError("source_release_not_complete")
    runtime_path = safe_child(root, state["runtime_exclusions_relative_to_migration"])
    original_path = safe_child(root, state["database_relative_to_migration"])
    runtime = read_json(runtime_path)
    if not isinstance(runtime, dict) or not isinstance(runtime.get("context_sha256"), list):
        raise ValueError("runtime_exclusion_list_missing_or_invalid")
    if not all(isinstance(h, str) and HEX64.fullmatch(h) for h in runtime["context_sha256"]):
        raise ValueError("runtime_exclusion_identity_invalid")
    source = connect_ro(source_path)
    original = connect_ro(original_path)
    try:
        denied = set(runtime["context_sha256"])
        denied.update(row[0] for row in source.execute(
            "SELECT h FROM context_state WHERE reuse_excluded=1 OR original_protected=1"))
        denied.update(row[0] for row in original.execute("SELECT h FROM protected"))
    except sqlite3.Error:
        raise ValueError("required_protection_table_missing") from None
    finally:
        original.close()
    if not all(isinstance(h, str) and HEX64.fullmatch(h) for h in denied):
        raise ValueError("protection_union_identity_invalid")
    columns = [row[2] for row in source.execute("PRAGMA index_info(variable_key)")]
    contexts = [row[2] for row in source.execute("PRAGMA index_info(variable_context)")]
    if columns != ["variable_key"] or contexts != ["h", "variable_key"]:
        raise ValueError("required_existing_index_not_available_no_full_scan")
    source_fp, original_fp = fingerprint(source_path), fingerprint(original_path)
    if (source_fp["size"] != release["private_output_bytes"] or
            not HEX64.fullmatch(release["private_output_sha256"])):
        raise ValueError("source_release_size_or_digest_declaration_invalid")
    pins = {"version": VERSION, "source_stat": source_fp, "original_protection_source_stat": original_fp,
            "source_database_sha256_from_previous_release": release["private_output_sha256"],
            "source_database_SHA_rehashed_this_run": False,
            "release_sha256": digest(release_path.read_bytes()),
            "state_sha256": digest(state_path.read_bytes()),
            "runtime_exclusions_sha256": digest(runtime_path.read_bytes()),
            "exclusion_union_sha256": digest(canon(sorted(denied)).encode()),
            "max_atoms_cumulative": max_atoms, "max_seconds_cumulative": max_seconds,
            "code_sha256": digest(Path(__file__).read_bytes())}
    destination = output / "EVIDENCE_READINESS_V1_PRIVATE.sqlite"
    db = sqlite3.connect(destination)
    db.executescript(SCHEMA)
    old_pins = db.execute("SELECT value_json FROM run_metadata WHERE key='pins'").fetchone()
    if old_pins and json.loads(old_pins[0]) != pins:
        raise ValueError("existing_readiness_pins_changed_preserve_output")
    if not old_pins:
        db.execute("INSERT INTO run_metadata VALUES('pins',?)", (canon(pins),))
        db.execute("INSERT INTO run_metadata VALUES('progress',?)", (canon({"cursor_rowid": 0,
            "processed_atoms": 0, "elapsed_seconds": 0.0, "state_counts": {}, "trace_counts": {},
            "workflow_counts": {}, "measurement_counts": {}, "status": "initialized"}),))
        db.commit()
    progress = json.loads(db.execute("SELECT value_json FROM run_metadata WHERE key='progress'").fetchone()[0])
    previous_elapsed = progress["elapsed_seconds"]
    deadline = started + max(0, max_seconds - previous_elapsed)
    signal.setitimer(signal.ITIMER_REAL, max(0.001, deadline-time.monotonic()))
    source.create_function("context_allowed", 1, lambda h: int(isinstance(h, str) and h not in denied))
    source.set_progress_handler(lambda: int(time.monotonic() >= deadline), 10000)
    counts_record = db.execute("SELECT value_json FROM run_metadata WHERE key='input_counts'").fetchone()
    if counts_record:
        counts = json.loads(counts_record[0])
    else:
        total = source.execute("SELECT COUNT(*) FROM variable_value INDEXED BY variable_key WHERE variable_key=?", (VARIABLE,)).fetchone()[0]
        excluded = sum(source.execute("SELECT COUNT(*) FROM variable_value INDEXED BY variable_context WHERE h=? AND variable_key=?", (h, VARIABLE)).fetchone()[0] for h in denied)
        null_h = source.execute("SELECT COUNT(*) FROM variable_value INDEXED BY variable_context WHERE h IS NULL AND variable_key=?", (VARIABLE,)).fetchone()[0]
        counts = {"total_evidence_atoms": total, "excluded_evidence_atoms": excluded,
                  "missing_context_identity_atoms": null_h, "processable_evidence_atoms": total-excluded-null_h}
        db.execute("INSERT INTO run_metadata VALUES('input_counts',?)", (canon(counts),))
        db.commit()

    def unchanged():
        return (fingerprint(source_path) == source_fp and fingerprint(original_path) == original_fp and
                digest(runtime_path.read_bytes()) == pins["runtime_exclusions_sha256"] and
                digest(state_path.read_bytes()) == pins["state_sha256"])

    def checkpoint(status):
        progress["status"] = status
        progress["elapsed_seconds"] = previous_elapsed + time.monotonic() - started
        db.execute("UPDATE run_metadata SET value_json=? WHERE key='progress'", (canon(progress),))
        db.commit()

    status = "scanning_existing_evidence_declarations"
    try:
        while progress["processed_atoms"] < min(max_atoms, counts["processable_evidence_atoms"]):
            if time.monotonic() >= deadline:
                status = "time_cap_reached_cursor_preserved"; break
            if not unchanged():
                status = "input_or_protection_changed_preserve_output"; break
            disk = sum(p.stat().st_size for p in (destination, Path(str(destination)+"-journal")) if p.exists())
            if disk >= MAX_DISK:
                status = "output_disk_cap_reached_cursor_preserved"; break
            n = min(BATCH, max_atoms-progress["processed_atoms"])
            # Metadata first. No evidence value is selected before deny/source-anchor checks.
            rows = source.execute("""SELECT v.rowid AS source_rowid,v.id,v.d,v.h,v.k,v.source_path,
                v.item_anchor_json,v.measurement_state,v.workflow_state,v.engineering_state,
                v.eligible_original_scope,v.original_mask,v.metadata_json,
                s.d AS source_d,s.h AS source_h,s.k AS source_k,s.asset,s.source_sha,s.source_ordinal
                FROM variable_value v INDEXED BY variable_key
                LEFT JOIN source_document s ON s.d=v.d
                WHERE v.variable_key=? AND v.rowid>? AND context_allowed(v.h)=1
                ORDER BY v.rowid LIMIT ?""", (VARIABLE, progress["cursor_rowid"], n)).fetchall()
            if not rows:
                status = "source_cursor_exhausted"; break
            traces = {row["source_rowid"]: anchor_trace(row) for row in rows}
            allowed_ids = [row["source_rowid"] for row in rows if traces[row["source_rowid"]][0] == "complete_retained_source_anchor_binding"]
            payloads = {}
            if allowed_ids:
                marks = ",".join("?" for _ in allowed_ids)
                payloads = dict(source.execute("SELECT rowid,CASE WHEN length(value_json)<=? THEN value_json ELSE NULL END FROM variable_value WHERE rowid IN (" + marks + ") AND variable_key=? AND context_allowed(h)=1", (MAX_VALUE_BYTES, *allowed_ids, VARIABLE)))
            # A batch is fully committed with its cursor, or fully rolled back.
            updates = json.loads(canon(progress))
            for row in rows:
                if time.monotonic() >= deadline:
                    raise TimeBudgetExceeded()
                trace, anchor = traces[row["source_rowid"]]
                if trace == "complete_retained_source_anchor_binding" and payloads[row["source_rowid"]] is not None:
                    result = inspect_declarations(payloads[row["source_rowid"]], row["source_path"], anchor)
                elif trace == "complete_retained_source_anchor_binding":
                    result = {"state": "payload_over_bounded_parser_limit",
                              "full_text_reverified": False, "new_semantic_acceptance": False}
                else:
                    result = {"state": "source_trace_incomplete_payload_not_read",
                              "full_text_reverified": False, "new_semantic_acceptance": False}
                values = (row["source_rowid"],row["id"],row["d"],row["h"],row["k"],row["source_path"],
                    row["item_anchor_json"],row["asset"],row["source_sha"],row["source_ordinal"],
                    row["measurement_state"],row["workflow_state"],row["engineering_state"],
                    row["eligible_original_scope"],row["original_mask"],row["metadata_json"],
                    trace,result["state"],canon(result),0,0)
                db.execute("INSERT INTO evidence_readiness VALUES(" + ",".join("?" for _ in values) + ")", values)
                for name, value in (("state_counts", result["state"]), ("trace_counts", trace),
                                    ("workflow_counts", row["workflow_state"]),
                                    ("measurement_counts", row["measurement_state"])):
                    value = str(value)
                    updates[name][value] = updates[name].get(value,0)+1
                updates["processed_atoms"] += 1
                updates["cursor_rowid"] = row["source_rowid"]
            if not unchanged():
                db.rollback(); status="input_or_protection_changed_preserve_output"; break
            progress = updates
            checkpoint("scanning_existing_evidence_declarations")
        if progress["processed_atoms"] == counts["processable_evidence_atoms"]:
            status = "all_current_allowed_evidence_atoms_audited_not_reverified"
        elif progress["processed_atoms"] >= max_atoms:
            status = "atom_cap_reached_cursor_preserved"
    except (sqlite3.OperationalError, TimeBudgetExceeded) as e:
        db.rollback()
        progress = json.loads(db.execute("SELECT value_json FROM run_metadata WHERE key='progress'").fetchone()[0])
        if (not isinstance(e, TimeBudgetExceeded) and "interrupted" not in str(e).lower()
                and time.monotonic() < deadline):
            raise
        status = "time_cap_reached_cursor_preserved"
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        source.set_progress_handler(None, 0)
    checkpoint(status)
    unchanged_end = unchanged()
    if not unchanged_end:
        status = "input_or_protection_changed_preserve_output"
        checkpoint(status)
    actual = db.execute("SELECT COUNT(*) FROM evidence_readiness").fetchone()[0]
    if actual != progress["processed_atoms"]:
        raise ValueError("sidecar_count_cursor_mismatch")
    db.close(); source.close()
    # Only the new sidecar is hashed; source hashing is deliberately not repeated.
    hash_started = time.monotonic()
    output_digest = hashlib.sha256()
    hash_complete = True
    signal.setitimer(signal.ITIMER_REAL, MAX_HASH_SECONDS)
    try:
        with destination.open("rb") as stream:
            for block in iter(lambda: stream.read(4*1024*1024), b""):
                if time.monotonic()-hash_started >= MAX_HASH_SECONDS:
                    hash_complete = False
                    break
                output_digest.update(block)
    except TimeBudgetExceeded:
        hash_complete = False
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
    hash_seconds = time.monotonic()-hash_started
    report = {"version": VERSION, "at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "status": status, **counts, "processed_evidence_atoms": actual,
        "remaining_allowed_evidence_atoms": counts["processable_evidence_atoms"]-actual,
        "cursor_rowid": progress["cursor_rowid"], "excluded_context_union": len(denied),
        "state_counts": progress["state_counts"], "trace_counts": progress["trace_counts"],
        "original_workflow_counts": progress["workflow_counts"],
        "original_measurement_counts": progress["measurement_counts"],
        "elapsed_seconds_cumulative": progress["elapsed_seconds"],
        "max_atoms_cumulative": max_atoms, "max_seconds_cumulative": max_seconds,
        "memory_limit_bytes": MAX_MEMORY, "output_database_bytes": destination.stat().st_size,
        "output_database_sha256": output_digest.hexdigest() if hash_complete else None,
        "output_hash_status": "complete" if hash_complete else "finalization_time_cap_reached_no_digest_claim",
        "output_hash_elapsed_seconds": hash_seconds, "output_hash_separate_time_cap_seconds": MAX_HASH_SECONDS,
        "source_size_and_mtime_unchanged": unchanged_end,
        "source_database_sha256_from_previous_release": pins["source_database_sha256_from_previous_release"],
        "source_database_SHA_rehashed_this_run": False,
        "runtime_exclusions_sha256": pins["runtime_exclusions_sha256"],
        "no_raw_documents_read": True, "offsets_reverified_against_text": False,
        "new_model_calls": 0, "new_production_accepted": 0,
        "original_mask_and_measurement_states_preserved": True,
        "entire_delivery_or_all_variables_complete": False,
        "bounded_order_not_a_probability_sample": True,
        "notes": ["Counts concern evidence atoms, not advertisements or complete variable coverage.",
            "Same-item declared offsets are retained claims, never a new source-text or semantic verification.",
            "Repeated occurrences are all preserved; no occurrence is chosen as the true one.",
            "Current readiness does not change accepted, saved, unknown or protected states."]}
    save_json(output / "EVIDENCE_READINESS_PUBLIC.json", report)
    return report


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path.home()/"migration"))
    parser.add_argument("--output")
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY, MAX_MEMORY))
    root = Path(args.root)
    output = Path(args.output) if args.output else root/"evidence_readiness_20261117/run001"
    try:
        report = run(root, output)
        keys = ("version", "status", "total_evidence_atoms", "processed_evidence_atoms",
                "remaining_allowed_evidence_atoms", "excluded_evidence_atoms",
                "elapsed_seconds_cumulative", "output_database_bytes", "output_database_sha256",
                "output_hash_status", "source_size_and_mtime_unchanged", "new_model_calls",
                "new_production_accepted")
        summary = {k: report[k] for k in keys}
        summary["full_report_sha256"] = digest((output/"EVIDENCE_READINESS_PUBLIC.json").read_bytes())
        print(json.dumps(summary, ensure_ascii=False))
    except Exception as e:
        output.mkdir(parents=True, exist_ok=True, mode=0o700)
        report = {"status":"readiness_preflight_or_execution_failed_preserved",
                  "exception_type":type(e).__name__, "new_model_calls":0,
                  "new_production_accepted":0, "old_source_modified":False}
        save_json(output/"FAILURE_PUBLIC.json", report)
        print(json.dumps(report)); raise SystemExit(2)


if __name__ == "__main__":
    main()
