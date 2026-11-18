#!/usr/bin/env python3
"""Cloud-only private JSONL harness for CPU candidates; no model/network calls."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import time

try:
    from . import cpu_candidates as engine
except ImportError:
    import cpu_candidates as engine


DEFAULT_MISSING_FIELDS = engine.EXPERIENCE_FIELDS + (
    "education", "technology", "entry.explicit_no_experience")


def digest(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=True, sort_keys=True, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def check_evidence(result, text):
    if not result.get("candidate_only") or result.get("resolved_fields") or result.get("field_updates"):
        raise ValueError("noncandidate_result_forbidden")
    def check(value):
        if isinstance(value, dict):
            if {"start", "end", "quote"} <= value.keys():
                left, right = value["start"], value["end"]
                if not isinstance(left, int) or not isinstance(right, int) or not 0 <= left <= right <= len(text) or text[left:right] != value["quote"]:
                    raise ValueError("evidence_offset_mismatch")
            for item in value.values():
                check(item)
        elif isinstance(value, list):
            for item in value:
                check(item)
    check(result.get("candidates", []))
    check(result.get("excluded_spans", []))


def run_batch(input_path, output_path, receipt_path, cache_path, *, max_records=10000,
              default_missing_fields=DEFAULT_MISSING_FIELDS):
    """Read {case, row:{context_sha256,full_document,...}, missing_fields?}.

    Missing-field selection precedence is row.missing_fields, envelope
    missing_fields, then the explicitly declared default. No case or record ID
    enters the public receipt. Every input line produces a private output row,
    including schema failures. A failed row makes the aggregate run incomplete.
    """
    os.umask(0o077)
    input_path, output_path, receipt_path, cache_path = map(Path, (input_path, output_path, receipt_path, cache_path))
    if not 1 <= max_records <= 10000:
        raise ValueError("pilot_record_limit_must_be_1_to_10000")
    if len({p.resolve() for p in (input_path, output_path, receipt_path, cache_path)}) != 4:
        raise ValueError("input_output_receipt_cache_paths_must_differ")
    input_sha = digest(input_path)
    if output_path.exists() or receipt_path.exists():
        if output_path.is_file() and receipt_path.is_file():
            prior = json.loads(receipt_path.read_text())
            if (prior.get("status") == "completed" and prior.get("input_sha256") == input_sha
                    and prior.get("engine_sha256") == engine.ENGINE_SHA256
                    and prior.get("output_sha256") == digest(output_path)
                    and prior.get("default_missing_fields") == list(default_missing_fields)):
                return dict(prior, already_complete=True)
        raise FileExistsError("existing_output_not_overwritten_use_new_run_path_or_inspect_receipt")
    for path in (output_path, receipt_path, cache_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    cpu_start = time.process_time()
    started_at = datetime.now(timezone.utc).isoformat()
    status_counts, kind_counts, field_counts = Counter(), Counter(), Counter()
    cache_hits = cache_misses = invalid_cache = failed_rows = processed_rows = 0
    candidate_total = retained_total = nohit_rows = truncated_rows = 0
    field_selection_counts = Counter()
    output_hash = hashlib.sha256()
    observed_input_hash = hashlib.sha256()
    partial_path = output_path.with_name(output_path.name + ".partial")
    if partial_path.exists():
        raise FileExistsError("partial_output_exists_use_new_run_path_or_inspect_checkpoint")
    conn = sqlite3.connect(cache_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("CREATE TABLE IF NOT EXISTS rule_cache (cache_key TEXT PRIMARY KEY, result_json TEXT NOT NULL, result_sha256 TEXT NOT NULL)")
    conn.commit()
    fatal_code = None
    try:
        with input_path.open("rb") as source, partial_path.open("xb") as target:
            for row_number, raw in enumerate(source, 1):
                observed_input_hash.update(raw)
                if row_number > max_records:
                    fatal_code = "input_record_limit_exceeded"
                    break
                context_sha = None
                try:
                    envelope = json.loads(raw)
                    if not isinstance(envelope, dict):
                        raise ValueError("input_envelope_not_object")
                    record = envelope.get("row", envelope)
                    if not isinstance(record, dict):
                        raise ValueError("input_row_not_object")
                    text = record.get("full_document")
                    context_sha = record.get("context_sha256")
                    if not isinstance(text, str):
                        raise ValueError("missing_string_full_document")
                    if not isinstance(context_sha, str) or context_sha != engine._source_sha(text):
                        raise ValueError("context_sha256_mismatch")
                    if "missing_fields" in record:
                        fields = record["missing_fields"]
                        selection = "row_missing_fields"
                    elif "missing_fields" in envelope:
                        fields = envelope["missing_fields"]
                        selection = "envelope_missing_fields"
                    else:
                        fields = default_missing_fields
                        selection = "declared_default_all_rule_fields"
                    fields = engine._requested_fields(fields)
                    field_selection_counts[selection] += 1
                    key = engine.cache_key(text, fields)
                    cached = conn.execute("SELECT result_json,result_sha256 FROM rule_cache WHERE cache_key=?", (key,)).fetchone()
                    result = None
                    if cached:
                        try:
                            encoded, value_sha = cached
                            if hashlib.sha256(encoded.encode()).hexdigest() != value_sha:
                                raise ValueError("cache_payload_sha_mismatch")
                            saved = json.loads(encoded)
                            if (saved.get("cache_key") != key or saved.get("source_text_sha256") != context_sha
                                    or saved.get("engine_sha256") != engine.ENGINE_SHA256
                                    or saved.get("requested_fields") != list(fields)):
                                raise ValueError("cache_identity_mismatch")
                            check_evidence(saved, text)
                            result = saved
                            cache_hits += 1
                        except (ValueError, TypeError, KeyError):
                            invalid_cache += 1
                    if result is None:
                        result = engine.extract(text, fields)
                        check_evidence(result, text)
                        encoded = canonical(result)
                        conn.execute("INSERT OR REPLACE INTO rule_cache VALUES (?,?,?)", (key, encoded, hashlib.sha256(encoded.encode()).hexdigest()))
                        cache_misses += 1
                    if result["status"] not in ("processed", "no_fields_requested"):
                        failed_rows += 1
                    status_counts[result["status"]] += 1
                    candidate_total += result["candidate_count_before_limit"]
                    retained_total += len(result["candidates"])
                    truncated_rows += bool(result["candidates_truncated"])
                    nohit_rows += not result["candidates"]
                    kind_counts.update(item["kind"] for item in result["candidates"])
                    for field, value in result["field_status"].items():
                        field_counts[(field, value["state"])] += 1
                except (ValueError, TypeError, KeyError, UnicodeError) as exc:
                    failed_rows += 1
                    code = str(exc) if str(exc) in {
                        "input_envelope_not_object", "input_row_not_object", "missing_string_full_document",
                        "context_sha256_mismatch", "evidence_offset_mismatch", "noncandidate_result_forbidden",
                    } else type(exc).__name__
                    result = {"candidate_only": True, "status": "invalid_input_record", "failure_code": code,
                              "candidates": [], "resolved_fields": [], "field_updates": {}, "field_status": {}}
                    status_counts["invalid_input_record"] += 1
                private_row = {"input_row_number": row_number,
                               "input_record_sha256": hashlib.sha256(raw).hexdigest(),
                               "context_sha256": context_sha, "result": result}
                data = (canonical(private_row) + "\n").encode()
                target.write(data)
                output_hash.update(data)
                processed_rows += 1
                if processed_rows % 100 == 0:
                    conn.commit()
                    target.flush()
            target.flush()
            os.fsync(target.fileno())
        conn.commit()
        if fatal_code is None and observed_input_hash.hexdigest() != input_sha:
            fatal_code = "input_changed_during_processing"
    finally:
        conn.close()
    elapsed = time.perf_counter() - start
    if fatal_code is None:
        os.replace(partial_path, output_path)
    receipt = {
        "kind": "public_cpu_candidate_run_receipt", "status": "completed" if not fatal_code and not failed_rows else "incomplete",
        "failure_code": fatal_code, "started_at_utc": started_at,
        "finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "engine_version": engine.VERSION, "engine_sha256": engine.ENGINE_SHA256,
        "harness_sha256": digest(__file__), "input_sha256": input_sha,
        "output_sha256": output_hash.hexdigest() if fatal_code is None else None,
        "output_published": fatal_code is None, "input_rows_processed": processed_rows,
        "failed_or_limited_rows": failed_rows, "max_records": max_records,
        "cache_hits": cache_hits, "cache_misses": cache_misses, "invalid_cache_entries": invalid_cache,
        "default_missing_fields": list(default_missing_fields),
        "field_selection_counts": dict(sorted(field_selection_counts.items())),
        "candidate_count_before_limit": candidate_total, "retained_candidate_count": retained_total,
        "records_without_retained_candidates": nohit_rows, "candidate_limited_records": truncated_rows,
        "result_status_counts": dict(sorted(status_counts.items())), "candidate_kind_counts": dict(sorted(kind_counts.items())),
        "field_status_counts": [{"field": field, "state": state, "records": count}
                                for (field, state), count in sorted(field_counts.items())],
        "wall_seconds": elapsed, "process_cpu_seconds": time.process_time() - cpu_start,
        "records_per_wall_second": processed_rows / elapsed if elapsed else None,
        "python_version": sys.version.split()[0], "network_calls": 0, "model_calls": 0,
        "scope": "Bounded CPU candidate extraction only; this run does not establish semantic accuracy, high recall, or whole-target completion.",
    }
    atomic_json(receipt_path, receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--max-records", type=int, default=10000)
    parser.add_argument("--default-missing-fields", default=",".join(DEFAULT_MISSING_FIELDS),
                        help="Only for records lacking missing_fields; explicit comma-separated field roots")
    args = parser.parse_args()
    receipt = run_batch(args.input, args.output, args.receipt, args.cache, max_records=args.max_records,
                        default_missing_fields=tuple(value for value in args.default_missing_fields.split(",") if value))
    print(json.dumps(receipt, ensure_ascii=True, sort_keys=True))
    return 0 if receipt["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
