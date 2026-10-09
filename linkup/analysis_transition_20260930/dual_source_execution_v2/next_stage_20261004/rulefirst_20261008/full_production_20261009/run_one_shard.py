#!/usr/bin/env python3
"""Stream one real canonical-USA corpus shard through frozen v1.2 rules.

This is deterministic rule execution, not model inference.  It writes narrow
posting and evidence Parquet tables without duplicating full advertisement text.
"""
import argparse
import collections
import datetime as dt
import hashlib
import json
import multiprocessing as mp
import os
import socket
import sys
import time
import traceback
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

import relation_overlay
import rule_engine

VERSION = "full-production-one-shard-v1"
D57_EXCLUDED_SECTIONS = {"required", "preferred", "qualification_unspecified", "background"}
DISPOSITIONS = {
    "matched_usa_canonical", "matched_usa_duplicate_quarantine", "matched_non_usa",
    "matched_country_unknown", "record_unmatched",
}

POSTING_SCHEMA = pa.schema([
    ("JOB_HASH", pa.string()), ("SOURCE_FILE", pa.string()), ("SOURCE_ROW", pa.int64()),
    ("RECORD_SOURCE_ROW", pa.int64()), ("CREATED", pa.timestamp("ms")),
    ("COUNTRY", pa.string()), ("STATE", pa.string()),
    ("COMPANY_ID", pa.string()), ("ONET_OCCUPATION_CODE", pa.string()),
    ("metadata_join_status", pa.string()), ("source_text_sha256", pa.string()),
    ("normalized_text_sha256", pa.string()), ("normalization", pa.string()),
    ("coordinate_system", pa.string()),
    ("rule_version", pa.string()), ("overlay_version", pa.string()),
    ("processing_status", pa.string()), ("experience_status", pa.string()),
    ("normalization_flags_json", pa.string()), ("excluded_context_clause_count", pa.int32()),
    ("flags_json", pa.string()), ("review_reasons_json", pa.string()),
    ("overlay_rules_json", pa.string()), ("evidence_count", pa.int32()),
    ("d57_current_duty_mentoring_candidate", pa.bool_()),
    ("mentoring_referent_or_prior_experience_marker", pa.bool_()),
    ("processing_error", pa.string()),
])

EVIDENCE_SCHEMA = pa.schema([
    ("JOB_HASH", pa.string()), ("SOURCE_FILE", pa.string()), ("SOURCE_ROW", pa.int64()),
    ("RECORD_SOURCE_ROW", pa.int64()), ("evidence_index", pa.int32()),
    ("kind", pa.string()), ("rule", pa.string()), ("start", pa.int64()),
    ("end", pa.int64()), ("quote", pa.string()), ("section", pa.string()),
    ("coordinate_system", pa.string()),
    ("objects_json", pa.string()), ("strength", pa.string()), ("scope", pa.string()),
    ("duration_kind", pa.string()), ("lower_years", pa.float64()),
    ("upper_years", pa.float64()), ("strict_lower", pa.bool_()),
    ("outcome_status", pa.string()), ("review_reasons_json", pa.string()),
    ("technology", pa.string()), ("role_cue", pa.string()), ("negated", pa.bool_()),
    ("task_family", pa.string()), ("overlay_annotations_json", pa.string()),
    ("candidate_heading_scope", pa.string()), ("heading_scope_status", pa.string()),
    ("d57_current_duty_mentoring_candidate", pa.bool_()),
    ("mentoring_referent_or_prior_experience_marker", pa.bool_()),
])


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def j(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def arrow_rows(value):
    """Convert old and new PyArrow Table/RecordBatch objects to row dicts."""
    columns = value.to_pydict()
    names = list(columns)
    count = len(columns[names[0]]) if names else 0
    return [{name: columns[name][i] for name in names} for i in range(count)]


def rows_table(rows, schema):
    """Build a table without relying on newer Table.from_pylist."""
    arrays = [pa.array([row.get(field.name) for row in rows], type=field.type) for field in schema]
    return pa.Table.from_arrays(arrays, schema=schema)


def is_usa(value):
    x = " ".join(str(value or "").strip().upper().replace(".", "").split())
    return x in {"US", "USA", "UNITED STATES", "UNITED STATES OF AMERICA"}


def d57_classifications(evidence, overlay):
    by_index = collections.defaultdict(list)
    for item in overlay.get("annotations", []):
        idx = item.get("evidence_index")
        if not isinstance(idx, int) or idx < 0 or idx >= len(evidence):
            raise ValueError("overlay evidence index out of range")
        e = evidence[idx]
        if (item.get("start"), item.get("end"), item.get("kind")) != (e.get("start"), e.get("end"), e.get("kind")):
            raise ValueError("overlay evidence identity mismatch")
        by_index[idx].append(item)
    out = {}
    for idx, items in by_index.items():
        e = evidence[idx]
        current = prior = False
        for item in items:
            anns = item.get("annotations") or []
            if not any(a.get("rule") == "mentoring_other_people" for a in anns):
                continue
            heading_scope = (item.get("candidate_heading") or {}).get("scope")
            span_kinds = {
                x.get("kind") for x in evidence
                if (x.get("start"), x.get("end")) == (e.get("start"), e.get("end"))
            }
            accepted = (heading_scope == "duties"
                        and not (span_kinds & {"experience", "knowledge", "education"})
                        and e.get("section") not in D57_EXCLUDED_SECTIONS)
            current |= accepted
            prior |= not accepted
        out[idx] = (current, prior)
    return by_index, out


def process_one(task):
    locator, text = task
    try:
        result = rule_engine.extract(text)
        if result.get("status") == "processed":
            normalized = result.get("normalized_text")
            if result.get("coordinate_system") != "normalized_unicode_codepoints":
                raise ValueError("unexpected evidence coordinate system")
            if not isinstance(normalized, str) or hashlib.sha256(normalized.encode("utf-8")).hexdigest() != result.get("normalized_text_sha256"):
                raise ValueError("normalized text hash mismatch")
            for e in result.get("evidence", []):
                a, b = e.get("start"), e.get("end")
                if not isinstance(a, int) or not isinstance(b, int) or not (0 <= a <= b <= len(normalized)) or normalized[a:b] != e.get("quote"):
                    raise ValueError("evidence span mismatch")
        overlay = relation_overlay.apply(result) if result.get("status") == "processed" else {
            "version": relation_overlay.VERSION, "annotations": []}
        evidence = result.get("evidence") or []
        by_index, d57 = d57_classifications(evidence, overlay)
        overlay_rules = sorted({a.get("rule") for xs in by_index.values() for item in xs for a in item.get("annotations", []) if a.get("rule")})
        current_any = any(x[0] for x in d57.values())
        prior_any = any(x[1] for x in d57.values())
        posting = dict(locator)
        posting.update({
            "COMPANY_ID": None, "ONET_OCCUPATION_CODE": None,
            "metadata_join_status": "pending_no_verified_metadata_join",
            "source_text_sha256": result.get("source_text_sha256") or (hashlib.sha256(text.encode("utf-8")).hexdigest() if isinstance(text, str) else None),
            "normalized_text_sha256": result.get("normalized_text_sha256"),
            "normalization": result.get("normalization"),
            "coordinate_system": result.get("coordinate_system"),
            "rule_version": rule_engine.VERSION,
            "overlay_version": relation_overlay.VERSION, "processing_status": result.get("status", "unknown"),
            "experience_status": result.get("experience_status", "unknown"),
            "normalization_flags_json": j(result.get("normalization_flags") or {}),
            "excluded_context_clause_count": result.get("excluded_context_clause_count", 0),
            "flags_json": j(result.get("flags") or {}),
            "review_reasons_json": j(result.get("review_reasons") or []),
            "overlay_rules_json": j(overlay_rules), "evidence_count": len(evidence),
            "d57_current_duty_mentoring_candidate": current_any,
            "mentoring_referent_or_prior_experience_marker": prior_any,
            "processing_error": None,
        })
        evidence_rows = []
        for idx, e in enumerate(evidence):
            duration = e.get("duration") or {}
            items = by_index.get(idx, [])
            anns = [a for item in items for a in item.get("annotations", [])]
            headings = [item.get("candidate_heading") for item in items if item.get("candidate_heading")]
            statuses = sorted({item.get("heading_scope_status") for item in items if item.get("heading_scope_status")})
            cur, prior = d57.get(idx, (False, False))
            evidence_rows.append({
                "JOB_HASH": locator["JOB_HASH"], "SOURCE_FILE": locator["SOURCE_FILE"],
                "SOURCE_ROW": locator["SOURCE_ROW"], "RECORD_SOURCE_ROW": locator["RECORD_SOURCE_ROW"],
                "evidence_index": idx, "kind": e.get("kind"), "rule": e.get("rule"),
                "start": e.get("start"), "end": e.get("end"), "quote": e.get("quote"),
                "section": e.get("section"),
                "coordinate_system": result.get("coordinate_system"),
                "objects_json": j(e.get("objects") or []),
                "strength": e.get("strength"), "scope": e.get("scope"),
                "duration_kind": duration.get("kind"), "lower_years": duration.get("lower_years"),
                "upper_years": duration.get("upper_years"), "strict_lower": duration.get("strict_lower"),
                "outcome_status": e.get("outcome_status"),
                "review_reasons_json": j(e.get("review_reasons") or []),
                "technology": e.get("technology"), "role_cue": e.get("role_cue"),
                "negated": e.get("negated"), "task_family": e.get("task_family"),
                "overlay_annotations_json": j(anns),
                "candidate_heading_scope": headings[-1].get("scope") if headings else None,
                "heading_scope_status": ",".join(statuses) if statuses else "not_applicable_no_overlay_annotation",
                "d57_current_duty_mentoring_candidate": cur,
                "mentoring_referent_or_prior_experience_marker": prior,
            })
        return posting, evidence_rows, None
    except Exception as exc:
        return None, None, "%s: %s" % (type(exc).__name__, str(exc)[:500])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True); ap.add_argument("--sidecar", required=True)
    ap.add_argument("--output-dir", required=True); ap.add_argument("--public-receipt", required=True)
    ap.add_argument("--expected-raw-sha256", required=True); ap.add_argument("--expected-sidecar-sha256", required=True)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(); started = time.time()
    raw, sidecar = Path(args.raw), Path(args.sidecar); out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True, mode=0o700)
    posting_final, evidence_final = out / "POSTING_NARROW_PRIVATE.parquet", out / "EVIDENCE_PRIVATE.parquet"
    receipt_path = Path(args.public_receipt)
    code_paths = [Path(__file__), Path(rule_engine.__file__), Path(relation_overlay.__file__), Path(rule_engine.legacy.__file__)]
    identity = {
        "raw_sha256": digest(raw), "sidecar_sha256": digest(sidecar),
        "runner_sha256": digest(__file__), "rule_engine_sha256": digest(rule_engine.__file__),
        "legacy_sha256": digest(rule_engine.legacy.__file__), "overlay_sha256": digest(relation_overlay.__file__),
    }
    if identity["raw_sha256"] != args.expected_raw_sha256 or identity["sidecar_sha256"] != args.expected_sidecar_sha256:
        raise RuntimeError("input digest differs from frozen manifest")
    prior = out / "RUN_RECEIPT_PRIVATE.json"
    if prior.exists():
        old = json.loads(prior.read_text())
        if old.get("status") == "complete" and old.get("identity") == identity and posting_final.exists() and evidence_final.exists():
            if old.get("outputs", {}).get("posting_sha256") == digest(posting_final) and old.get("outputs", {}).get("evidence_sha256") == digest(evidence_final):
                atomic_json(receipt_path, old["public_receipt"])
                atomic_json(out / "PROGRESS_PUBLIC.json", {
                    "status": "complete", "job_id": os.environ.get("JOB_ID"),
                    "source_file": raw.name,
                    "canonical_rows_written": old["outputs"]["posting_rows"],
                    "evidence_rows_written": old["outputs"]["evidence_rows"],
                    "resume_verified": True,
                    "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                })
                return
        raise RuntimeError("existing output identity is incomplete or mismatched; refusing append/overwrite")

    st = pq.read_table(sidecar)
    capabilities = {
        "parquetfile_iter_batches": hasattr(pq.ParquetFile, "iter_batches"),
        "table_to_pydict": hasattr(st, "to_pydict"),
        "table_from_arrays": hasattr(pa.Table, "from_arrays"),
        "zstd_codec": bool(hasattr(pa, "Codec") and hasattr(pa.Codec, "is_available")
                           and pa.Codec.is_available("zstd")),
    }
    if not all(capabilities.values()):
        raise RuntimeError("runtime capability preflight failed: " + j(capabilities))
    print(j({"runtime_preflight": "passed", "python_version": sys.version.split()[0],
             "pyarrow_version": pa.__version__, "capabilities": capabilities}), flush=True)
    required = {"SOURCE_ROW", "JOB_HASH", "MATCH_DISPOSITION", "RECORD_SOURCE_ROW", "CREATED", "COUNTRY", "STATE", "SOURCE_FILE"}
    if required - set(st.column_names): raise RuntimeError("sidecar schema missing required columns")
    side_rows = arrow_rows(st); raw_pf = pq.ParquetFile(raw)
    if len(side_rows) != raw_pf.metadata.num_rows: raise RuntimeError("raw/sidecar row count mismatch")
    by_row = {}; dispositions = collections.Counter()
    for row in side_rows:
        pos, disp = row["SOURCE_ROW"], row["MATCH_DISPOSITION"]
        if not isinstance(pos, int) or pos in by_row or disp not in DISPOSITIONS: raise RuntimeError("invalid/duplicate sidecar source row or disposition")
        if (disp != "record_unmatched") != (row["RECORD_SOURCE_ROW"] is not None): raise RuntimeError("sidecar match/record locator mismatch")
        if disp in {"matched_usa_canonical", "matched_usa_duplicate_quarantine"} and not is_usa(row["COUNTRY"]): raise RuntimeError("USA disposition country mismatch")
        if disp in {"matched_non_usa", "matched_country_unknown"} and is_usa(row["COUNTRY"]): raise RuntimeError("non-USA disposition country mismatch")
        by_row[pos] = row; dispositions[disp] += 1
    if set(by_row) != set(range(raw_pf.metadata.num_rows)): raise RuntimeError("sidecar positions not contiguous")
    if len({r["SOURCE_FILE"] for r in side_rows}) != 1 or side_rows[0]["SOURCE_FILE"] != raw.name: raise RuntimeError("sidecar source file mismatch")

    ptmp, etmp = Path(str(posting_final) + ".tmp"), Path(str(evidence_final) + ".tmp")
    for x in (ptmp, etmp): x.unlink(missing_ok=True)
    pw = pq.ParquetWriter(ptmp, POSTING_SCHEMA, compression="zstd")
    ew = pq.ParquetWriter(etmp, EVIDENCE_SCHEMA, compression="zstd")
    counters = collections.Counter(); seen_keys = set(); seen_job_hashes = set(); source_row = 0; errors = []
    progress_path = out / "PROGRESS_PUBLIC.json"
    try:
        ctx = mp.get_context("fork")
        with ctx.Pool(processes=args.workers) as pool:
            for batch_no, raw_batch in enumerate(raw_pf.iter_batches(batch_size=256, columns=["JOB_HASH", "DESCRIPTION"]), 1):
                raw_rows = arrow_rows(raw_batch)
                tasks = []
                for item in raw_rows:
                    side = by_row[source_row]
                    if item["JOB_HASH"] != side["JOB_HASH"]: raise RuntimeError("raw/sidecar JOB_HASH mismatch")
                    if side["MATCH_DISPOSITION"] == "matched_usa_canonical":
                        locator = {k: side[k] for k in ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW", "CREATED", "COUNTRY", "STATE")}
                        key = (locator["JOB_HASH"], locator["SOURCE_FILE"], locator["SOURCE_ROW"], locator["RECORD_SOURCE_ROW"])
                        if key in seen_keys: raise RuntimeError("duplicate canonical locator")
                        if locator["JOB_HASH"] in seen_job_hashes: raise RuntimeError("duplicate canonical JOB_HASH within shard")
                        seen_keys.add(key); seen_job_hashes.add(locator["JOB_HASH"])
                        tasks.append((locator, item["DESCRIPTION"]))
                    source_row += 1
                postings, evidences = [], []
                for posting, evrows, err in pool.imap(process_one, tasks, chunksize=16):
                    if err: errors.append(err); continue
                    postings.append(posting); evidences.extend(evrows)
                    counters["canonical_rows"] += 1; counters["evidence_rows"] += len(evrows)
                    counters["processing_" + str(posting["processing_status"])] += 1
                    counters["experience_" + str(posting["experience_status"])] += 1
                    if posting["d57_current_duty_mentoring_candidate"]: counters["d57_current_duty_mentoring_candidate"] += 1
                    if posting["mentoring_referent_or_prior_experience_marker"]: counters["mentoring_referent_or_prior_experience_marker"] += 1
                if postings: pw.write_table(rows_table(postings, POSTING_SCHEMA))
                if evidences: ew.write_table(rows_table(evidences, EVIDENCE_SCHEMA))
                atomic_json(progress_path, {
                    "status": "running", "job_id": os.environ.get("JOB_ID"),
                    "source_file": raw.name, "raw_rows_scanned": source_row,
                    "canonical_rows_written": counters["canonical_rows"],
                    "evidence_rows_written": counters["evidence_rows"],
                    "batches_completed": batch_no,
                    "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                })
        pw.close(); ew.close()
        if errors: raise RuntimeError("row processing failures=%d; first=%s" % (len(errors), errors[0]))
        expected = dispositions["matched_usa_canonical"]
        if (counters["canonical_rows"] != expected or len(seen_keys) != expected
                or len(seen_job_hashes) != expected):
            raise RuntimeError("canonical output conservation/uniqueness failure")
        os.replace(ptmp, posting_final); os.replace(etmp, evidence_final)
    except Exception:
        pw.close(); ew.close(); ptmp.unlink(missing_ok=True); etmp.unlink(missing_ok=True); raise

    elapsed = time.time() - started
    outputs = {"posting_rows": counters["canonical_rows"], "evidence_rows": counters["evidence_rows"],
               "posting_bytes": posting_final.stat().st_size, "evidence_bytes": evidence_final.stat().st_size,
               "posting_sha256": digest(posting_final), "evidence_sha256": digest(evidence_final)}
    public = {
        "status": "complete", "version": VERSION, "decision": "D58-incremental-narrow-production",
        "scope": "one deterministic real corpus shard; not fixed7635 and not full corpus",
        "source_file": raw.name, "raw_rows": raw_pf.metadata.num_rows,
        "disposition_counts": dict(sorted(dispositions.items())), "canonical_usa_rows": counters["canonical_rows"],
        "row_conservation": sum(dispositions.values()) == raw_pf.metadata.num_rows,
        "canonical_locator_unique_within_shard": len(seen_keys) == counters["canonical_rows"],
        "canonical_job_hash_unique_within_shard": len(seen_job_hashes) == counters["canonical_rows"],
        "metadata_join_status": "pending_no_verified_metadata_join",
        "evidence_coordinate_system": "normalized_unicode_codepoints",
        "counts": dict(sorted(counters.items())), "outputs": outputs,
        "identity": identity, "elapsed_seconds": round(elapsed, 3),
        "rows_per_second": round(counters["canonical_rows"] / elapsed, 3) if elapsed else None,
        "host": socket.gethostname(), "job_id": os.environ.get("JOB_ID"),
        "requested_workers": args.workers, "api_calls": 0, "model_calls": 0,
        "runtime": {
            "python_version": sys.version.split()[0],
            "pyarrow_version": pa.__version__,
            "capabilities": capabilities,
        },
        "claim_boundary": "rule-observed candidates; no-match remains unknown; metadata linkage pending",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    private = {"status": "complete", "identity": identity, "outputs": outputs, "public_receipt": public,
               "private_output_paths": [str(posting_final), str(evidence_final)]}
    atomic_json(prior, private); atomic_json(receipt_path, public)
    atomic_json(progress_path, {
        "status": "complete", "job_id": os.environ.get("JOB_ID"),
        "source_file": raw.name, "raw_rows_scanned": source_row,
        "canonical_rows_written": counters["canonical_rows"],
        "evidence_rows_written": counters["evidence_rows"],
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    })


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # A wrapper trap also records scheduler context.  Never publish complete on failure.
        print("FATAL", type(exc).__name__, str(exc), file=__import__("sys").stderr)
        traceback.print_exc()
        raise
