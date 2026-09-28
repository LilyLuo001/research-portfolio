#!/usr/bin/env python3
"""Lean sparse writer for frozen V6 plus explicit-relation enrichment."""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import importlib.util
import json
import os
import resource
import shutil
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

KEYS = [("JOB_HASH", pa.string()), ("SOURCE_FILE", pa.string()), ("SOURCE_ROW", pa.int64()),
        ("RECORD_SOURCE_ROW", pa.int64())]
AD_SCHEMA = pa.schema(KEYS + [
    ("CREATED", pa.timestamp("ms")), ("COUNTRY", pa.string()), ("STATE", pa.string()),
    ("DESCRIPTION_EMPTY", pa.bool_()),
    ("NORMALIZATION_VERSION", pa.string()), ("PARSE_ERROR", pa.bool_()),
    ("INPUT_EVIDENCE_TRUNCATED", pa.bool_()), ("ENRICHMENT_INCOMPLETE", pa.bool_()),
    ("EXPERIENCE_EVIDENCE_COUNT", pa.int32()), ("TECHNOLOGY_EVIDENCE_COUNT", pa.int32()),
    ("V6_AUDIT_EVIDENCE_COUNT", pa.int32()),
])
EXP_SCHEMA = pa.schema(KEYS + [("EVIDENCE_ORDINAL", pa.int32()),
    ("CLAUSE_START", pa.int64()), ("CLAUSE_END", pa.int64()),
    ("OBJECT_START", pa.int64()), ("OBJECT_END", pa.int64()),
    ("OBJECT_TYPE", pa.string()), ("MIN_YEARS", pa.float64()), ("MAX_YEARS", pa.float64()),
    ("DURATION_UNIT", pa.string()), ("BOUND_TYPE", pa.string()),
    ("BINDING_STATUS", pa.string()), ("RELATION", pa.string()), ("OPTIONAL", pa.bool_()),
    ("CONTEXT", pa.string()), ("APPLICANT_CONTEXT_CANDIDATE", pa.bool_()),
    ("REQUIREMENT_STRENGTH", pa.string()),
])
TECH_SCHEMA = pa.schema(KEYS + [("EVIDENCE_ORDINAL", pa.int32()),
    ("TECHNOLOGY_START", pa.int64()), ("TECHNOLOGY_END", pa.int64()),
    ("TECHNOLOGY_TYPE", pa.string()), ("TECHNOLOGY_NAME", pa.string()),
    ("ROLE_START", pa.int64()), ("ROLE_END", pa.int64()), ("ROLE", pa.string()),
    ("BINDING_STATUS", pa.string()), ("ROLE_CANDIDATE", pa.bool_()),
    ("TECHNOLOGY_AMBIGUITY", pa.string()), ("CONTEXT", pa.string()),
    ("APPLICANT_CONTEXT_CANDIDATE", pa.bool_()),
])
AUDIT_SCHEMA = pa.schema(KEYS + [("EVIDENCE_ORDINAL", pa.int32()),
    ("MODULE", pa.string()), ("START", pa.int64()), ("END", pa.int64()),
    ("CANDIDATE_TYPE", pa.string()), ("VALUE", pa.string()),
    ("DEGREE_LEVEL", pa.string()), ("EDUCATION_STATUS", pa.string()),
    ("ATTAINED_DEGREE", pa.bool_()), ("MIN_YEARS", pa.float64()),
    ("MAX_YEARS", pa.float64()), ("DURATION_UNIT", pa.string()),
    ("BOUND_TYPE", pa.string()), ("NO_EXPERIENCE_EXPLICIT", pa.bool_()),
    ("CONTEXT", pa.string()), ("REQUIREMENT_STRENGTH", pa.string()),
    ("APPLICANT_CONTEXT_CANDIDATE", pa.bool_()),
    ("IS_APPLICANT_REQUIREMENT", pa.bool_()),
    ("IS_UNCONDITIONAL_EDUCATION_REQUIREMENT", pa.bool_()),
    ("IS_UNCONDITIONAL_EXPERIENCE_REQUIREMENT", pa.bool_()),
    ("NEGATED", pa.bool_()), ("NEGATED_OR_OPTIONAL", pa.bool_()),
    ("EQUIVALENCE_TYPE", pa.string()), ("EQUIVALENT_EXPERIENCE", pa.bool_()),
    ("EQUIVALENT_CREDENTIAL", pa.bool_()),
    ("ALTERNATIVE_TRAINING_OR_EXPERIENCE", pa.bool_()),
    ("ALTERNATIVE_TRAINING_OR_EDUCATION", pa.bool_()),
    ("QUALIFICATION_RELATION_UNRESOLVED", pa.bool_()),
    ("MIXED_REQUIREMENT_SCOPE", pa.bool_()),
    ("QUALIFICATION_SCOPE_START", pa.int64()),
    ("QUALIFICATION_SCOPE_END", pa.int64()),
    ("LOCAL_PATH_SCOPE_APPLIED", pa.bool_()),
    ("CONTEXT_CONFLICT", pa.bool_()),
    ("AMBIGUOUS_DEGREE_ABBREVIATION", pa.bool_()),
    ("EDUCATION_ENROLLMENT_MENTION_CANDIDATE", pa.bool_()),
    ("QUALIFICATION_PRESENCE_RULE", pa.string()),
])

AUDIT_FIELDS = [field.name for field in AUDIT_SCHEMA if field.name not in dict(KEYS)]


def v6_audit_rows(payload, incomplete):
    """Retain frozen V6 audit candidates without copying evidence text."""
    if incomplete:
        return []
    selected = []
    for ordinal, item in enumerate(payload.get("evidence", [])):
        module = item.get("module")
        keep = module == "education" or (
            module == "experience" and (
                item.get("no_experience_explicit")
                or item.get("alternative_training_or_education")
                or item.get("qualification_relation_unresolved")
                or item.get("mixed_requirement_scope")
            )
        )
        if not keep:
            continue
        row = {name: None for name in AUDIT_FIELDS}
        row.update({
            "EVIDENCE_ORDINAL": ordinal,
            "MODULE": module,
            "START": item.get("start"), "END": item.get("end"),
            "CANDIDATE_TYPE": item.get("candidate_type"), "VALUE": item.get("value"),
            "DEGREE_LEVEL": item.get("degree_level"),
            "EDUCATION_STATUS": item.get("education_status"),
            "ATTAINED_DEGREE": item.get("attained_degree"),
            "MIN_YEARS": item.get("min_years"), "MAX_YEARS": item.get("max_years"),
            "DURATION_UNIT": item.get("duration_unit"), "BOUND_TYPE": item.get("bound_type"),
            "NO_EXPERIENCE_EXPLICIT": item.get("no_experience_explicit"),
            "CONTEXT": item.get("context"), "REQUIREMENT_STRENGTH": item.get("requirement_strength"),
            "APPLICANT_CONTEXT_CANDIDATE": item.get("is_applicant_qualification_candidate"),
            "IS_APPLICANT_REQUIREMENT": item.get("is_applicant_requirement"),
            "IS_UNCONDITIONAL_EDUCATION_REQUIREMENT": item.get("is_unconditional_education_requirement"),
            "IS_UNCONDITIONAL_EXPERIENCE_REQUIREMENT": item.get("is_unconditional_experience_requirement"),
            "NEGATED": item.get("negated"), "NEGATED_OR_OPTIONAL": item.get("negated_or_optional"),
            "EQUIVALENCE_TYPE": item.get("equivalence_type"),
            "EQUIVALENT_EXPERIENCE": item.get("equivalent_experience"),
            "EQUIVALENT_CREDENTIAL": item.get("equivalent_credential"),
            "ALTERNATIVE_TRAINING_OR_EXPERIENCE": item.get("alternative_training_or_experience"),
            "ALTERNATIVE_TRAINING_OR_EDUCATION": item.get("alternative_training_or_education"),
            "QUALIFICATION_RELATION_UNRESOLVED": item.get("qualification_relation_unresolved"),
            "MIXED_REQUIREMENT_SCOPE": item.get("mixed_requirement_scope"),
            "QUALIFICATION_SCOPE_START": item.get("qualification_scope_start"),
            "QUALIFICATION_SCOPE_END": item.get("qualification_scope_end"),
            "LOCAL_PATH_SCOPE_APPLIED": item.get("local_path_scope_applied"),
            "CONTEXT_CONFLICT": item.get("context_conflict"),
            "AMBIGUOUS_DEGREE_ABBREVIATION": item.get("ambiguous_degree_abbreviation"),
            "EDUCATION_ENROLLMENT_MENTION_CANDIDATE": item.get("education_enrollment_mention_candidate"),
            "QUALIFICATION_PRESENCE_RULE": item.get("qualification_presence_rule"),
        })
        selected.append(row)
    return selected


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


def iter_range(path, start, count):
    pf = pq.ParquetFile(path); stop = start + count; cursor = 0
    columns = ["JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW",
               "CREATED", "COUNTRY", "STATE", "DESCRIPTION"]
    for group in range(pf.num_row_groups):
        n = pf.metadata.row_group(group).num_rows
        low, high = cursor, cursor + n; cursor = high
        if high <= start: continue
        if low >= stop: break
        table = pf.read_row_group(group, columns=columns)
        left = max(0, start - low); right = min(n, stop - low)
        for row in table.slice(left, right - left).to_pylist():
            yield row


def worker(args):
    source, parser_path, enrichment_path, out_dir, start, count, cap = args
    parser = load(Path(parser_path), "frozen_v6_worker")
    enrichment = load(Path(enrichment_path), "enrichment_worker")
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=False)
    temp = Path(tempfile.mkdtemp(prefix="tmp.", dir=str(out)))
    writers = {"ad_status": pq.ParquetWriter(temp / "ad_status.parquet", AD_SCHEMA, compression="zstd"),
               "experience": pq.ParquetWriter(temp / "experience.parquet", EXP_SCHEMA, compression="zstd"),
               "technology": pq.ParquetWriter(temp / "technology.parquet", TECH_SCHEMA, compression="zstd"),
               "v6_audit": pq.ParquetWriter(temp / "v6_audit.parquet", AUDIT_SCHEMA, compression="zstd")}
    buffers = {"ad_status": [], "experience": [], "technology": [], "v6_audit": []}
    schemas = {"ad_status": AD_SCHEMA, "experience": EXP_SCHEMA, "technology": TECH_SCHEMA,
               "v6_audit": AUDIT_SCHEMA}

    def flush(force=False):
        for name in buffers:
            if buffers[name] and (force or len(buffers[name]) >= 512):
                writers[name].write_table(pa.Table.from_pylist(buffers[name], schema=schemas[name]))
                buffers[name] = []
    processed = exp_n = tech_n = audit_n = parse_n = trunc_n = incomplete_n = empty_n = 0; started = time.monotonic()
    try:
        for row in iter_range(Path(source), start, count):
            payload = parser.extract(row["DESCRIPTION"])
            result = enrichment.enrich(payload); flags = result["flags"]
            key = {name: row.get(name) for name, _ in KEYS}
            description_empty = not isinstance(row.get("DESCRIPTION"), str) or not row["DESCRIPTION"].strip()
            audits = [{**key, **item} for item in v6_audit_rows(payload, flags["enrichment_incomplete"])]
            ads = [{**key, "CREATED": row.get("CREATED"), "COUNTRY": row.get("COUNTRY"),
                    "STATE": row.get("STATE"), "DESCRIPTION_EMPTY": description_empty,
                    "NORMALIZATION_VERSION": payload.get("normalization_version"),
                    "PARSE_ERROR": flags["input_parse_error"],
                    "INPUT_EVIDENCE_TRUNCATED": flags["input_evidence_truncated"],
                    "ENRICHMENT_INCOMPLETE": flags["enrichment_incomplete"],
                    "EXPERIENCE_EVIDENCE_COUNT": len(result["experience_evidence"]),
                    "TECHNOLOGY_EVIDENCE_COUNT": len(result["technology_evidence"]),
                    "V6_AUDIT_EVIDENCE_COUNT": len(audits)}]
            exps = [{**key, **{k.upper(): v for k, v in item.items()}}
                    for item in result["experience_evidence"]]
            techs = [{**key, **{k.upper(): v for k, v in item.items()}}
                     for item in result["technology_evidence"]]
            buffers["ad_status"].extend(ads); buffers["experience"].extend(exps); buffers["technology"].extend(techs)
            buffers["v6_audit"].extend(audits)
            flush()
            processed += 1; exp_n += len(exps); tech_n += len(techs); audit_n += len(audits)
            empty_n += int(description_empty)
            parse_n += int(flags["input_parse_error"]); trunc_n += int(flags["input_evidence_truncated"])
            incomplete_n += int(flags["enrichment_incomplete"])
        flush(force=True)
        for writer in writers.values(): writer.close()
        writers = {}
        bytes_out = sum(p.stat().st_size for p in temp.iterdir())
        if bytes_out > cap: raise RuntimeError("chunk cap exceeded")
        for p in temp.iterdir(): os.replace(p, out / p.name)
        temp.rmdir()
        outputs = {}
        for p in sorted(out.glob("*.parquet")):
            pf = pq.ParquetFile(p)
            outputs[p.name] = {"bytes": p.stat().st_size, "sha256": sha(p),
                               "rows": pf.metadata.num_rows, "row_groups": pf.num_row_groups,
                               "schema": str(pf.schema_arrow)}
        receipt = {"status": "complete", "start": start, "requested_rows": count,
                   "processed_rows": processed, "description_empty_rows": empty_n,
                   "experience_rows": exp_n, "technology_rows": tech_n, "v6_audit_rows": audit_n,
                   "parse_errors": parse_n, "truncated_rows": trunc_n,
                   "enrichment_incomplete_rows": incomplete_n, "output_bytes": bytes_out,
                   "wall_seconds": time.monotonic() - started, "outputs": outputs}
        (out / "COMPLETE.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        return receipt
    except Exception:
        for writer in writers.values(): writer.close()
        shutil.rmtree(temp, ignore_errors=True)
        raise


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True); ap.add_argument("--parser", required=True)
    ap.add_argument("--enrichment", required=True); ap.add_argument("--output-dir", required=True)
    ap.add_argument("--workers", type=int, default=8); ap.add_argument("--output-cap-bytes", type=int, required=True)
    args = ap.parse_args()
    root = Path(args.output_dir); root.mkdir(parents=True, exist_ok=False)
    total = pq.ParquetFile(args.source).metadata.num_rows
    # A shard may legitimately have no canonical matched-USA rows.  Emit the
    # same three empty Parquet tables plus receipts so the regional runner can
    # conserve that shard without special-casing or silently skipping it.
    workers = max(1, min(args.workers, total)); chunk = (total + workers - 1) // workers
    tasks = []
    if total == 0:
        tasks.append((args.source, args.parser, args.enrichment, root / "chunk_00",
                      0, 0, args.output_cap_bytes))
    for i in range(workers):
        start = i * chunk; count = min(chunk, total - start)
        if count:
            tasks.append((args.source, args.parser, args.enrichment, root / ("chunk_%02d" % i),
                          start, count, args.output_cap_bytes // workers))
    started = time.monotonic()
    try:
        with cf.ProcessPoolExecutor(max_workers=workers) as pool: receipts = list(pool.map(worker, tasks))
        output_bytes = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
        if output_bytes > args.output_cap_bytes: raise RuntimeError("global cap exceeded")
        complete = {"status": "complete", "created_utc": datetime.now(timezone.utc).isoformat(),
                    "source": str(Path(args.source).resolve()), "source_bytes": Path(args.source).stat().st_size,
                    "source_sha256": sha(args.source), "parser_sha256": sha(args.parser),
                    "enrichment_sha256": sha(args.enrichment), "processed_rows": sum(x["processed_rows"] for x in receipts),
                    "experience_rows": sum(x["experience_rows"] for x in receipts),
                    "technology_rows": sum(x["technology_rows"] for x in receipts),
                    "v6_audit_rows": sum(x["v6_audit_rows"] for x in receipts),
                    "description_empty_rows": sum(x["description_empty_rows"] for x in receipts),
                    "parse_errors": sum(x["parse_errors"] for x in receipts),
                    "truncated_rows": sum(x["truncated_rows"] for x in receipts),
                    "enrichment_incomplete_rows": sum(x["enrichment_incomplete_rows"] for x in receipts),
                    "output_bytes": output_bytes, "output_cap_bytes": args.output_cap_bytes,
                    "wall_seconds": time.monotonic() - started, "workers": workers,
                    "max_rss_kb": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
                    "schemas": {"ad_status": str(AD_SCHEMA), "experience": str(EXP_SCHEMA),
                                "technology": str(TECH_SCHEMA), "v6_audit": str(AUDIT_SCHEMA)},
                    "chunks": receipts}
        (root / "COMPLETE.json").write_text(json.dumps(complete, indent=2, sort_keys=True) + "\n")
        print(json.dumps(complete, sort_keys=True))
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


if __name__ == "__main__": main()
