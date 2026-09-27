#!/usr/bin/env python3
"""Bounded compact V5 candidate storage trial.

The frozen parser is treated as an input.  Normalized text and repeated complete
candidate JSON are not persisted.  Text-valued evidence fields that are exact
slices of normalized text are reconstructed from the raw source and recorded
coordinates; all other evidence fields are retained through typed columns or a
small exceptional-fields JSON object.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.util
import json
import os
import platform
import resource
import shutil
import sys
import tempfile
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import pyarrow as pa
import pyarrow.parquet as pq

RUNNER_VERSION = "bounded-v5-compact-v1"
FROZEN_PARSER_SHA256 = "336242bed5372e446dbdc2b2d02944e906024ee90138a2fa424b866aee7293dd"
MODULES = ("software", "ai", "experience", "education", "tasks")
DEFAULT_OUTPUT_CAP = 250_000_000
RESERVE_BYTES = 1_000_000

KEY_FIELDS = [
    pa.field("JOB_HASH", pa.string()), pa.field("SOURCE_FILE", pa.string()),
    pa.field("SOURCE_ROW", pa.int64()),
]

SOURCE_SCHEMA = pa.schema(KEY_FIELDS + [
    pa.field("RAW_SHA256", pa.string()), pa.field("NORMALIZED_SHA256", pa.string()),
    pa.field("STATUS", pa.string()), pa.field("HAS_PARSE_ERROR", pa.bool_()),
    pa.field("EVIDENCE_TRUNCATED", pa.bool_()), pa.field("ERROR_COUNT", pa.int32()),
    pa.field("NORMALIZATION_VERSION", pa.string()),
    pa.field("OFFSET_COORDINATE_SYSTEM", pa.string()),
    pa.field("NORMALIZED_TEXT_MODE", pa.string()),
])

AD_SCHEMA = pa.schema(KEY_FIELDS + [
    pa.field("RECORD_KIND", pa.string()), pa.field("CANDIDATE_ONLY", pa.bool_()),
    pa.field("SUMMARY_JSON", pa.string()), pa.field("FORMAT_FLAGS_JSON", pa.string()),
    pa.field("NORMALIZATION_FLAGS_JSON", pa.string()), pa.field("ERRORS_JSON", pa.string()),
    pa.field("EVIDENCE_LIMIT", pa.int64()), pa.field("EVIDENCE_RETURNED_COUNT", pa.int64()),
    pa.field("EVIDENCE_TOTAL_BEFORE_TRUNCATION", pa.int64()),
    pa.field("MODULE_EVIDENCE_TRUNCATED_JSON", pa.string()),
    pa.field("TOP_EXTRAS_JSON", pa.string()),
    pa.field("NORMALIZED_TEXT_FALLBACK", pa.string()),
])

TYPED_EVIDENCE = {
    "module": pa.string(), "candidate_type": pa.string(), "value": pa.string(),
    "start": pa.int64(), "end": pa.int64(), "snippet_start": pa.int64(),
    "snippet_end": pa.int64(), "context": pa.string(),
    "requirement_strength": pa.string(), "is_applicant_requirement": pa.bool_(),
    "is_applicant_qualification_candidate": pa.bool_(), "candidate_only": pa.bool_(),
    "min_years": pa.float64(), "max_years": pa.float64(),
    "min_duration": pa.float64(), "max_duration": pa.float64(),
    "duration_unit": pa.string(), "has_explicit_duration": pa.bool_(),
    "bound_type": pa.string(), "no_experience_explicit": pa.bool_(),
    "scope": pa.string(), "negated": pa.bool_(), "negated_or_optional": pa.bool_(),
    "qualification_scope_start": pa.int64(), "qualification_scope_end": pa.int64(),
}
SLICE_FIELDS = {
    "matched_text": ("start", "end"),
    "snippet": ("snippet_start", "snippet_end"),
    "qualification_scope_text": ("qualification_scope_start", "qualification_scope_end"),
}
EVIDENCE_SCHEMA = pa.schema(KEY_FIELDS + [
    pa.field("EVIDENCE_ORDINAL", pa.int32()),
] + [pa.field(k.upper(), t) for k, t in TYPED_EVIDENCE.items()] + [
    pa.field("PRESENT_KEYS_JSON", pa.string()), pa.field("NUMERIC_TYPES_JSON", pa.string()),
    pa.field("SLICE_FIELDS_JSON", pa.string()), pa.field("EXTRAS_JSON", pa.string()),
])

RELATION_SCHEMA = pa.schema(KEY_FIELDS + [
    pa.field("EVIDENCE_ORDINAL", pa.int32()), pa.field("RELATION_TYPE", pa.string()),
    pa.field("SCOPE_START", pa.int64()), pa.field("SCOPE_END", pa.int64()),
    pa.field("SCOPE_RULE", pa.string()), pa.field("RESOLUTION_STATUS", pa.string()),
    pa.field("COMPLETE_PATH_GRAPH", pa.bool_()),
])

TOP_TYPED = {
    "record_kind", "candidate_only", "normalization_version", "offset_coordinate_system",
    "normalized_text", "source_fingerprint_sha256", "normalized_text_fingerprint_sha256",
    "format_flags", "normalization_flags", "summary", "evidence", "evidence_limit",
    "evidence_truncated", "evidence_total_before_truncation", "module_evidence_truncated", "errors",
}

def canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)

def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def load_parser(path: Path):
    if sha256_file(path) != FROZEN_PARSER_SHA256:
        raise ValueError("frozen parser SHA256 mismatch")
    spec = importlib.util.spec_from_file_location("frozen_v5_parser", str(path))
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load parser")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def aggregate_status(payload: Mapping[str, Any]) -> str:
    if payload.get("errors"):
        return "parse_error"
    summaries = payload.get("summary") or {}
    return "candidate" if any((summaries.get(m) or {}).get("status") == "candidate" for m in MODULES) else "no_candidate"

def error_payload(exc: Exception) -> Dict[str, Any]:
    return {
        "record_kind": "CANDIDATES", "candidate_only": True,
        "normalization_version": "recruitment-html-text-v5",
        "offset_coordinate_system": "unicode_codepoint_offsets_in_normalized_text",
        "normalized_text": "", "source_fingerprint_sha256": None,
        "normalized_text_fingerprint_sha256": sha256_bytes(b""),
        "format_flags": {}, "normalization_flags": {},
        "summary": {m: {"status": "parse_error", "candidate_count": 0} for m in MODULES},
        "evidence": [], "evidence_limit": 0, "evidence_truncated": False,
        "evidence_total_before_truncation": 0,
        "module_evidence_truncated": {m: False for m in MODULES},
        "errors": ["runner caught %s: %s" % (type(exc).__name__, exc)],
    }

def compact_payload(job_hash: Any, raw: Any, source_file: str, source_row: int, parser) -> Tuple[Dict[str, Any], Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    try:
        payload = parser.extract(raw)
        if not isinstance(payload, dict):
            raise TypeError("extract did not return dict")
    except Exception as exc:
        payload = error_payload(exc)
    key = {"JOB_HASH": None if job_hash is None else str(job_hash), "SOURCE_FILE": source_file, "SOURCE_ROW": int(source_row)}
    raw_sha = sha256_bytes(raw.encode("utf-8")) if isinstance(raw, str) else None
    normalized = payload.get("normalized_text")
    normalized_sha = payload.get("normalized_text_fingerprint_sha256")
    errors = list(payload.get("errors") or [])
    if isinstance(raw, str) and payload.get("source_fingerprint_sha256") != raw_sha:
        errors.append("source_fingerprint_sha256 mismatch")
        payload = dict(payload); payload["errors"] = errors
    mode = "fallback"
    fallback = normalized if isinstance(normalized, str) else ""
    if isinstance(raw, str) and isinstance(normalized, str):
        rebuilt = parser._normalize(raw)
        if rebuilt == normalized and sha256_bytes(rebuilt.encode("utf-8")) == normalized_sha:
            mode, fallback = "reconstruct", None
    source = {**key, "RAW_SHA256": raw_sha, "NORMALIZED_SHA256": normalized_sha,
              "STATUS": aggregate_status(payload), "HAS_PARSE_ERROR": bool(errors),
              "EVIDENCE_TRUNCATED": bool(payload.get("evidence_truncated", False)),
              "ERROR_COUNT": len(errors), "NORMALIZATION_VERSION": payload.get("normalization_version"),
              "OFFSET_COORDINATE_SYSTEM": payload.get("offset_coordinate_system"),
              "NORMALIZED_TEXT_MODE": mode}
    top_extras = {k: v for k, v in payload.items() if k not in TOP_TYPED}
    ad = {**key, "RECORD_KIND": payload.get("record_kind"),
          "CANDIDATE_ONLY": payload.get("candidate_only"),
          "SUMMARY_JSON": canonical(payload.get("summary")),
          "FORMAT_FLAGS_JSON": canonical(payload.get("format_flags")),
          "NORMALIZATION_FLAGS_JSON": canonical(payload.get("normalization_flags")),
          "ERRORS_JSON": canonical(payload.get("errors")),
          "EVIDENCE_LIMIT": payload.get("evidence_limit"),
          "EVIDENCE_RETURNED_COUNT": len(payload.get("evidence") or []),
          "EVIDENCE_TOTAL_BEFORE_TRUNCATION": payload.get("evidence_total_before_truncation"),
          "MODULE_EVIDENCE_TRUNCATED_JSON": canonical(payload.get("module_evidence_truncated")),
          "TOP_EXTRAS_JSON": canonical(top_extras), "NORMALIZED_TEXT_FALLBACK": fallback}
    evidence_rows, relation_rows = [], []
    for ordinal, item in enumerate(payload.get("evidence") or []):
        if not isinstance(item, dict):
            raise ValueError("non-object evidence")
        present = sorted(k for k in item if k in TYPED_EVIDENCE or k in SLICE_FIELDS)
        numeric_types = {k: type(item[k]).__name__ for k in TYPED_EVIDENCE if k in item and isinstance(item[k], (int, float)) and not isinstance(item[k], bool)}
        slice_names = []
        for name, (left, right) in SLICE_FIELDS.items():
            if name in item:
                start, end = item.get(left), item.get(right)
                if not isinstance(normalized, str) or not isinstance(start, int) or not isinstance(end, int) or normalized[start:end] != item[name]:
                    raise ValueError("non-reconstructible %s at source row %d evidence %d" % (name, source_row, ordinal))
                slice_names.append(name)
        extras = {k: v for k, v in item.items() if k not in TYPED_EVIDENCE and k not in SLICE_FIELDS}
        ev = {**key, "EVIDENCE_ORDINAL": ordinal,
              "PRESENT_KEYS_JSON": canonical(present), "NUMERIC_TYPES_JSON": canonical(numeric_types),
              "SLICE_FIELDS_JSON": canonical(slice_names), "EXTRAS_JSON": canonical(extras)}
        ev.update({k.upper(): item.get(k) for k in TYPED_EVIDENCE})
        evidence_rows.append(ev)
        relation_type = None
        if item.get("equivalence_type") == "credential_equivalent" or item.get("equivalent_credential"):
            relation_type = "EQUIVALENT_CREDENTIAL_CANDIDATE"
        elif item.get("equivalence_type") == "experience_alternative" or item.get("alternative_training_or_experience") or item.get("alternative_training_or_education") or item.get("equivalent_experience"):
            relation_type = "ALTERNATIVE_PATH_CANDIDATE"
        if relation_type:
            relation_rows.append({**key, "EVIDENCE_ORDINAL": ordinal, "RELATION_TYPE": relation_type,
                "SCOPE_START": item.get("qualification_scope_start", item.get("start")),
                "SCOPE_END": item.get("qualification_scope_end", item.get("end")),
                "SCOPE_RULE": item.get("qualification_scope_rule"),
                "RESOLUTION_STATUS": "unresolved_candidate", "COMPLETE_PATH_GRAPH": False})
    return source, ad, evidence_rows, relation_rows, payload

def reconstruct_payload(source: Mapping[str, Any], ad: Mapping[str, Any], evidence: Sequence[Mapping[str, Any]], raw: Any, parser) -> Dict[str, Any]:
    if source["NORMALIZED_TEXT_MODE"] == "reconstruct":
        if not isinstance(raw, str) or sha256_bytes(raw.encode("utf-8")) != source["RAW_SHA256"]:
            raise ValueError("raw source fingerprint mismatch")
        normalized = parser._normalize(raw)
    else:
        normalized = ad["NORMALIZED_TEXT_FALLBACK"]
    if sha256_bytes(normalized.encode("utf-8")) != source["NORMALIZED_SHA256"]:
        raise ValueError("normalized fingerprint mismatch")
    payload = json.loads(ad["TOP_EXTRAS_JSON"])
    payload.update({
        "record_kind": ad["RECORD_KIND"], "candidate_only": ad["CANDIDATE_ONLY"],
        "normalization_version": source["NORMALIZATION_VERSION"],
        "offset_coordinate_system": source["OFFSET_COORDINATE_SYSTEM"],
        "normalized_text": normalized, "source_fingerprint_sha256": source["RAW_SHA256"],
        "normalized_text_fingerprint_sha256": source["NORMALIZED_SHA256"],
        "format_flags": json.loads(ad["FORMAT_FLAGS_JSON"]),
        "normalization_flags": json.loads(ad["NORMALIZATION_FLAGS_JSON"]),
        "summary": json.loads(ad["SUMMARY_JSON"]), "evidence": [],
        "evidence_limit": ad["EVIDENCE_LIMIT"], "evidence_truncated": source["EVIDENCE_TRUNCATED"],
        "evidence_total_before_truncation": ad["EVIDENCE_TOTAL_BEFORE_TRUNCATION"],
        "module_evidence_truncated": json.loads(ad["MODULE_EVIDENCE_TRUNCATED_JSON"]),
        "errors": json.loads(ad["ERRORS_JSON"]),
    })
    for row in sorted(evidence, key=lambda x: x["EVIDENCE_ORDINAL"]):
        item = json.loads(row["EXTRAS_JSON"])
        present = json.loads(row["PRESENT_KEYS_JSON"])
        types = json.loads(row["NUMERIC_TYPES_JSON"])
        for key in present:
            if key in SLICE_FIELDS:
                continue
            value = row[key.upper()]
            if types.get(key) == "int" and value is not None:
                value = int(value)
            item[key] = value
        for name in json.loads(row["SLICE_FIELDS_JSON"]):
            left, right = SLICE_FIELDS[name]
            item[name] = normalized[item[left]:item[right]]
        payload["evidence"].append(item)
    return payload

def _writers(temp_dir: Path):
    return {
        "source_index": pq.ParquetWriter(temp_dir / "source_index.parquet", SOURCE_SCHEMA, compression="zstd"),
        "ad_status": pq.ParquetWriter(temp_dir / "ad_status.parquet", AD_SCHEMA, compression="zstd"),
        "evidence": pq.ParquetWriter(temp_dir / "evidence.parquet", EVIDENCE_SCHEMA, compression="zstd"),
        "relations": pq.ParquetWriter(temp_dir / "relations.parquet", RELATION_SCHEMA, compression="zstd"),
    }

def _write_batch(writers, sources, ads, evidence, relations):
    writers["source_index"].write_table(pa.Table.from_pylist(sources, schema=SOURCE_SCHEMA))
    writers["ad_status"].write_table(pa.Table.from_pylist(ads, schema=AD_SCHEMA))
    writers["evidence"].write_table(pa.Table.from_pylist(evidence, schema=EVIDENCE_SCHEMA))
    writers["relations"].write_table(pa.Table.from_pylist(relations, schema=RELATION_SCHEMA))

def process_source(source_path: Path, parser_path: Path, out_dir: Path, rows_limit: int, batch_size: int, cap_bytes: int, start_row: int = 0) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=False)
    temp_dir = Path(tempfile.mkdtemp(prefix="tmp.", dir=str(out_dir)))
    parser = load_parser(parser_path)
    writers = _writers(temp_dir)
    started = time.monotonic(); processed = 0; ev_count = 0; rel_count = 0
    statuses = {"candidate": 0, "no_candidate": 0, "parse_error": 0}; truncated = 0
    stop_reason = None
    try:
        pf = pq.ParquetFile(source_path)
        if not {"JOB_HASH", "DESCRIPTION"}.issubset(pf.schema_arrow.names):
            raise ValueError("source missing JOB_HASH or DESCRIPTION")
        physical = 0
        for batch in pf.iter_batches(batch_size=batch_size, columns=["JOB_HASH", "DESCRIPTION"]):
            batch_start, batch_end = physical, physical + batch.num_rows; physical = batch_end
            if batch_end <= start_row:
                continue
            left = max(0, start_row - batch_start)
            selected = batch.slice(left)
            remaining = rows_limit - processed
            if remaining <= 0: break
            selected = selected.slice(0, min(selected.num_rows, remaining))
            sources=[]; ads=[]; evidence=[]; relations=[]
            for offset, row in enumerate(selected.to_pylist()):
                source_row = batch_start + left + offset
                s,a,e,r,_ = compact_payload(row.get("JOB_HASH"), row.get("DESCRIPTION"), str(source_path), source_row, parser)
                sources.append(s); ads.append(a); evidence.extend(e); relations.extend(r)
            estimated = sum(pa.Table.from_pylist(x, schema=s).nbytes for x,s in ((sources,SOURCE_SCHEMA),(ads,AD_SCHEMA),(evidence,EVIDENCE_SCHEMA),(relations,RELATION_SCHEMA)))
            current = sum(p.stat().st_size for p in temp_dir.iterdir())
            if current + estimated + 256_000 > cap_bytes:
                stop_reason = "output_temp_cap_before_batch"
                break
            _write_batch(writers, sources, ads, evidence, relations)
            processed += len(sources); ev_count += len(evidence); rel_count += len(relations)
            for s in sources: statuses[s["STATUS"]] += 1
            truncated += sum(int(s["EVIDENCE_TRUNCATED"]) for s in sources)
            if sum(p.stat().st_size for p in temp_dir.iterdir()) > cap_bytes:
                raise RuntimeError("output+temp cap exceeded after conservative precheck")
        for writer in writers.values(): writer.close()
        writers = {}
        for path in temp_dir.iterdir(): os.replace(path, out_dir / path.name)
        temp_dir.rmdir()
        output_bytes = sum(p.stat().st_size for p in out_dir.glob("*.parquet"))
        next_row = start_row + processed
        receipt = {
            "receipt_version": 1, "status": "stopped_cap" if stop_reason else "complete",
            "stop_reason": stop_reason, "created_utc": datetime.now(timezone.utc).isoformat(),
            "runner_version": RUNNER_VERSION, "runner_sha256": sha256_file(Path(__file__)),
            "parser_sha256": FROZEN_PARSER_SHA256, "source_path": str(source_path),
            "source_stat_size": source_path.stat().st_size, "source_stat_mtime_ns": source_path.stat().st_mtime_ns,
            "start_source_row": start_row, "next_source_row": next_row,
            "requested_rows": rows_limit, "processed_rows": processed,
            "pending_rows": rows_limit - processed, "evidence_rows": ev_count, "relation_rows": rel_count,
            "status_counts": statuses, "truncated_rows": truncated, "output_bytes": output_bytes,
            "output_cap_bytes": cap_bytes, "wall_seconds": time.monotonic()-started,
            "rows_per_wall_second": processed/max(time.monotonic()-started,1e-9),
            "outputs": {p.name: {"bytes":p.stat().st_size,"sha256":sha256_file(p),"rows":pq.ParquetFile(p).metadata.num_rows} for p in out_dir.glob("*.parquet")},
        }
        (out_dir/"CHECKPOINT.json").write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
        return receipt
    except Exception:
        for writer in writers.values(): writer.close()
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise

def verify_roundtrip(source_path: Path, parser_path: Path, out_dir: Path, limit: Optional[int]=None) -> Dict[str, Any]:
    parser=load_parser(parser_path)
    sources=pq.read_table(out_dir/"source_index.parquet").to_pylist()
    ads=pq.read_table(out_dir/"ad_status.parquet").to_pylist()
    evs=pq.read_table(out_dir/"evidence.parquet").to_pylist()
    by_ad={(r["SOURCE_FILE"],r["SOURCE_ROW"]):r for r in ads}
    by_ev={}
    for r in evs: by_ev.setdefault((r["SOURCE_FILE"],r["SOURCE_ROW"]),[]).append(r)
    wanted=sorted({int(r["SOURCE_ROW"]) for r in sources[:limit]})
    raw_rows={}; physical=0; wanted_set=set(wanted); max_wanted=max(wanted) if wanted else -1
    # Read only through the greatest selected physical row. Production checks
    # therefore remain bounded to the same prefix and never materialize a raw
    # provider shard or scan beyond the trial rows.
    for batch in pq.ParquetFile(source_path).iter_batches(batch_size=256,columns=["DESCRIPTION"]):
        for offset,row in enumerate(batch.to_pylist()):
            source_row=physical+offset
            if source_row in wanted_set: raw_rows[source_row]=row["DESCRIPTION"]
        physical += batch.num_rows
        if physical > max_wanted: break
    failures=[]; checked=0
    for source in sources[:limit]:
        key=(source["SOURCE_FILE"],source["SOURCE_ROW"]); raw=raw_rows[source["SOURCE_ROW"]]
        original=parser.extract(raw)
        rebuilt=reconstruct_payload(source,by_ad[key],by_ev.get(key,[]),raw,parser)
        if original != rebuilt: failures.append(source["SOURCE_ROW"])
        checked += 1
    return {"checked_rows":checked,"failure_count":len(failures),"failure_source_rows":failures[:20],"status":"PASS" if not failures else "FAIL"}

def local_trial(args) -> int:
    out=Path(args.output_dir)
    receipt=process_source(Path(args.source),Path(args.parser),out,args.rows,args.batch_size,args.output_cap_bytes)
    check=verify_roundtrip(Path(args.source),Path(args.parser),out)
    # Comparable frozen-V5 storage: one row per payload with the old full JSON shape.
    parser=load_parser(Path(args.parser)); old=[]
    for i,row in enumerate(pq.read_table(args.source,columns=["JOB_HASH","DESCRIPTION"]).slice(0,args.rows).to_pylist()):
        payload=parser.extract(row["DESCRIPTION"])
        old.append({"JOB_HASH":str(row["JOB_HASH"]),"SOURCE_FILE":str(Path(args.source)),"SOURCE_ROW":i,
                    "RAW_SHA256":payload.get("source_fingerprint_sha256"),"NORMALIZED_SHA256":payload.get("normalized_text_fingerprint_sha256"),
                    "STATUS":aggregate_status(payload),"HAS_PARSE_ERROR":bool(payload.get("errors")),
                    "EVIDENCE_TRUNCATED":bool(payload.get("evidence_truncated")),"ERROR_COUNT":len(payload.get("errors") or []),
                    "CANDIDATE_JSON":canonical(payload)})
    baseline=out/"comparison_full_v5_candidate_json.parquet"
    baseline_schema=pa.schema(KEY_FIELDS+[pa.field("RAW_SHA256",pa.string()),pa.field("NORMALIZED_SHA256",pa.string()),pa.field("STATUS",pa.string()),pa.field("HAS_PARSE_ERROR",pa.bool_()),pa.field("EVIDENCE_TRUNCATED",pa.bool_()),pa.field("ERROR_COUNT",pa.int32()),pa.field("CANDIDATE_JSON",pa.string())])
    pq.write_table(pa.Table.from_pylist(old,schema=baseline_schema),baseline,compression="zstd",row_group_size=args.batch_size)
    comparison={"codec":"zstd","row_group_size":args.batch_size,
                "compact_parquet_bytes":receipt["output_bytes"],"full_v5_candidate_json_bytes":baseline.stat().st_size,
                "compact_to_full_ratio":receipt["output_bytes"]/baseline.stat().st_size,"roundtrip":check}
    (out/"LOCAL_TRIAL.json").write_text(json.dumps(comparison,indent=2,sort_keys=True)+"\n")
    print(canonical(comparison)); return 0 if check["status"]=="PASS" else 2

def batch_trial(args) -> int:
    if args.file_count != 4 or args.rows_per_file > 4000 or args.workers > 4 or args.batch_size not in (128, 256):
        raise ValueError("bounded trial requires 4 files, <=4000 rows/file, <=4 workers, batch 128/256")
    if args.output_cap_bytes > DEFAULT_OUTPUT_CAP:
        raise ValueError("compact trial output cap may not exceed 250,000,000 bytes")
    if args.confirmed_headroom_bytes < args.output_cap_bytes + 50_000_000:
        raise ValueError("recent confirmed quota headroom must cover output cap plus 50 MB reserve")
    manifest_path=Path(args.manifest).resolve(); manifest=json.loads(manifest_path.read_text())
    entries=sorted(manifest.get(args.region) or [],key=lambda x:(str(x["file_name"]),str(x["path"])))[:args.file_count]
    if len(entries)!=args.file_count: raise ValueError("manifest lacks four selected sources")
    sources=[]
    for entry in entries:
        path=Path(entry["path"]); stat=path.stat()
        if stat.st_size != int(entry["bytes"]): raise ValueError("source stat differs from audited manifest: %s"%path)
        sources.append({"file_name":entry["file_name"],"path":str(path),"manifest_sha256":entry["sha256"],"stat_size":stat.st_size,"stat_mtime_ns":stat.st_mtime_ns})
    root=Path(args.output_dir).resolve(); root.mkdir(parents=True,exist_ok=False)
    identity={"runner_version":RUNNER_VERSION,"runner_sha256":sha256_file(Path(__file__)),"parser_sha256":sha256_file(Path(args.parser)),
              "manifest_path":str(manifest_path),"manifest_sha256":sha256_file(manifest_path),"region":args.region,
              "selection_rule":"lexical_file_name_then_path_first_n","rows_per_file":args.rows_per_file,"batch_size":args.batch_size,
              "workers":args.workers,"output_cap_bytes":args.output_cap_bytes,"sources":sources}
    identity["job_hash"]=sha256_bytes(canonical(identity).encode())
    (root/"IDENTITY.json").write_text(json.dumps(identity,sort_keys=True,indent=2)+"\n")
    per_cap=(args.output_cap_bytes-RESERVE_BYTES)//args.file_count; started=time.monotonic(); receipts=[]
    tasks=[]
    for index,source in enumerate(sources):
        name="%02d_%s"%(index,source["file_name"].replace(".snappy.parquet","").replace(".parquet",""))
        tasks.append((Path(source["path"]),Path(args.parser),root/name,args.rows_per_file,args.batch_size,per_cap,0))
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        future_map={pool.submit(process_source,*task):task for task in tasks}
        for future in concurrent.futures.as_completed(future_map): receipts.append(future.result())
    roundtrips=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as pool:
        future_map={pool.submit(verify_roundtrip,task[0],task[1],task[2]):task for task in tasks}
        for future in concurrent.futures.as_completed(future_map): roundtrips.append(future.result())
    persistent=sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
    if persistent > args.output_cap_bytes: raise RuntimeError("global persistent output cap exceeded")
    complete={"status":"complete" if all(r["status"]=="complete" for r in receipts) else "stopped_cap",
              "created_utc":datetime.now(timezone.utc).isoformat(),"job_hash":identity["job_hash"],
              "actual_rows":sum(r["processed_rows"] for r in receipts),"pending_rows":sum(r["pending_rows"] for r in receipts),
              "evidence_rows":sum(r["evidence_rows"] for r in receipts),"relation_rows":sum(r["relation_rows"] for r in receipts),
              "roundtrip_checked_rows":sum(r["checked_rows"] for r in roundtrips),
              "roundtrip_failure_count":sum(r["failure_count"] for r in roundtrips),
              "status_counts":{s:sum(r["status_counts"][s] for r in receipts) for s in ("candidate","no_candidate","parse_error")},
              "truncated_rows":sum(r["truncated_rows"] for r in receipts),"persistent_bytes_including_receipts":persistent,
              "persistent_output_cap_bytes":args.output_cap_bytes,"wall_seconds":time.monotonic()-started,
              "rows_per_wall_second":sum(r["processed_rows"] for r in receipts)/max(time.monotonic()-started,1e-9),"workers":sorted(receipts,key=lambda r:r["source_path"])}
    encoded=(json.dumps(complete,sort_keys=True,indent=2)+"\n")
    if persistent+len(encoded.encode())>args.output_cap_bytes: raise RuntimeError("cap leaves no room for COMPLETE receipt")
    (root/"COMPLETE.json").write_text(encoded); print(canonical(complete)); return 0

def main(argv=None) -> int:
    ap=argparse.ArgumentParser(description=__doc__); sub=ap.add_subparsers(dest="command",required=True)
    p=sub.add_parser("process"); p.add_argument("--source",required=True); p.add_argument("--parser",required=True); p.add_argument("--output-dir",required=True); p.add_argument("--rows",type=int,required=True); p.add_argument("--batch-size",type=int,default=256); p.add_argument("--output-cap-bytes",type=int,required=True); p.add_argument("--start-row",type=int,default=0)
    l=sub.add_parser("local-trial"); l.add_argument("--source",required=True); l.add_argument("--parser",required=True); l.add_argument("--output-dir",required=True); l.add_argument("--rows",type=int,default=2926); l.add_argument("--batch-size",type=int,default=128); l.add_argument("--output-cap-bytes",type=int,default=DEFAULT_OUTPUT_CAP)
    v=sub.add_parser("verify"); v.add_argument("--source",required=True); v.add_argument("--parser",required=True); v.add_argument("--output-dir",required=True)
    b=sub.add_parser("batch"); b.add_argument("--region",choices=("kunshan","wuzhen"),required=True); b.add_argument("--manifest",required=True); b.add_argument("--parser",required=True); b.add_argument("--output-dir",required=True); b.add_argument("--file-count",type=int,default=4); b.add_argument("--rows-per-file",type=int,default=4000); b.add_argument("--batch-size",type=int,default=256); b.add_argument("--workers",type=int,default=4); b.add_argument("--output-cap-bytes",type=int,default=DEFAULT_OUTPUT_CAP); b.add_argument("--confirmed-headroom-bytes",type=int,required=True)
    args=ap.parse_args(argv)
    if args.command=="local-trial": return local_trial(args)
    if args.command=="verify":
        report=verify_roundtrip(Path(args.source),Path(args.parser),Path(args.output_dir)); print(canonical(report)); return 0 if report["status"]=="PASS" else 2
    if args.command=="batch": return batch_trial(args)
    receipt=process_source(Path(args.source),Path(args.parser),Path(args.output_dir),args.rows,args.batch_size,args.output_cap_bytes,args.start_row); print(canonical(receipt)); return 0

if __name__ == "__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        print("FATAL: %s: %s"%(type(exc).__name__,exc),file=sys.stderr); traceback.print_exc(); raise SystemExit(2)
