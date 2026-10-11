#!/usr/bin/env python3
"""Project existing current evidence for the bounded D67 closing package."""
import argparse, datetime as dt, hashlib, json, os
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
DIMS = ("general_work", "tool", "industry_domain", "occupation_task")
STRENGTHS = ("required", "preferred", "mixed")
SCOPES = ("unconditional", "conditional_or_alternative", "unknown_scope")
VERSION = "d67-closing-evidence-v1"


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def key(row):
    return tuple(row[x] for x in KEY)


def batches(path, columns):
    pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=32768, columns=columns):
        data = batch.to_pydict(); names = list(data)
        for i in range(batch.num_rows):
            yield {name: data[name][i] for name in names}


def scope_class(value):
    if value == "unconditional_explicit_clause":
        return "unconditional"
    if value in ("education_alternative", "other_conditional", "document_multiline_alternative_unresolved"):
        return "conditional_or_alternative"
    return "unknown_scope"


def feature_names():
    names = []
    for dim in DIMS:
        for strength in STRENGTHS:
            names.append("current_%s_%s_any_scope" % (dim, strength))
            for scope in SCOPES:
                names.append("current_%s_%s_%s" % (dim, strength, scope))
        names += ["current_%s_strength_unknown" % dim, "current_%s_outcome_unknown" % dim]
    return names


def feature_schema():
    return pa.schema([
        pa.field("JOB_HASH", pa.string()), pa.field("SOURCE_FILE", pa.string()),
        pa.field("SOURCE_ROW", pa.int64()), pa.field("RECORD_SOURCE_ROW", pa.int64()),
    ] + [pa.field(name, pa.bool_()) for name in feature_names()])


DURATION_SCHEMA = pa.schema([
    pa.field("JOB_HASH", pa.string()), pa.field("SOURCE_FILE", pa.string()),
    pa.field("SOURCE_ROW", pa.int64()), pa.field("RECORD_SOURCE_ROW", pa.int64()),
    pa.field("evidence_index", pa.int32()), pa.field("rule", pa.string()),
    pa.field("start", pa.int64()), pa.field("end", pa.int64()), pa.field("quote", pa.string()),
    pa.field("section", pa.string()), pa.field("objects_json", pa.string()),
    pa.field("strength", pa.string()), pa.field("scope", pa.string()), pa.field("scope_class", pa.string()),
    pa.field("duration_kind", pa.string()), pa.field("lower_years", pa.float64()),
    pa.field("upper_years", pa.float64()), pa.field("strict_lower", pa.bool_()),
    pa.field("outcome_status", pa.string()), pa.field("review_reasons_json", pa.string()),
])


def write_atomic(path, table):
    temp = Path(str(path) + ".tmp")
    pq.write_table(table, temp, compression="zstd")
    os.replace(temp, path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", required=True); p.add_argument("--region", required=True)
    p.add_argument("--index", required=True, type=int); p.add_argument("--output-root", required=True)
    a = p.parse_args()
    manifest = json.load(open(a.manifest)); shards = [x for x in manifest["shards"] if x["region"] == a.region]
    if not 0 <= a.index < len(shards): raise RuntimeError("index outside regional frozen manifest")
    shard = shards[a.index]; evidence = shard["evidence"]
    if shard.get("status") != "complete" or shard.get("qa_status") != "pass": raise RuntimeError("unaccepted shard")
    if sha(evidence) != shard["evidence_sha256"]: raise RuntimeError("evidence SHA mismatch")

    names = list(KEY) + ["evidence_index", "kind", "rule", "start", "end", "quote", "section",
        "objects_json", "strength", "scope", "duration_kind", "lower_years", "upper_years",
        "strict_lower", "outcome_status", "review_reasons_json"]
    features = {}; scanned = exp_rows = numeric_rows = 0
    out = Path(a.output_root); out.mkdir(parents=True, exist_ok=True)
    duration_path = out / (shard["shard_id"] + ".duration_clauses.parquet")
    duration_temp = Path(str(duration_path) + ".tmp"); writer = None; duration_buffer = []

    def flush():
        nonlocal writer, duration_buffer
        if not duration_buffer: return
        table = pa.Table.from_pylist(duration_buffer, schema=DURATION_SCHEMA)
        if writer is None: writer = pq.ParquetWriter(duration_temp, DURATION_SCHEMA, compression="zstd")
        writer.write_table(table); duration_buffer = []

    for row in batches(evidence, names):
        scanned += 1
        if row["kind"] != "experience": continue
        exp_rows += 1; sc = scope_class(row["scope"])
        objects = [x for x in json.loads(row["objects_json"] or "[]") if x in DIMS]
        if row["duration_kind"] or row["lower_years"] is not None or row["upper_years"] is not None:
            numeric_rows += 1
            duration_row = {name: row.get(name) for name in DURATION_SCHEMA.names if name != "scope_class"}
            duration_row["scope_class"] = sc; duration_buffer.append(duration_row)
            if len(duration_buffer) >= 20000: flush()
        if not objects: continue
        k = key(row); f = features.setdefault(k, set())
        explicit = row["outcome_status"] == "explicit_rule_candidate"
        strength = (row["strength"] or "").strip().lower()
        for dim in objects:
            if not explicit: f.add("current_%s_outcome_unknown" % dim)
            elif strength in STRENGTHS:
                f.add("current_%s_%s_any_scope" % (dim, strength))
                f.add("current_%s_%s_%s" % (dim, strength, sc))
            else: f.add("current_%s_strength_unknown" % dim)
    flush()
    if writer is None:
        write_atomic(duration_path, pa.Table.from_pylist([], schema=DURATION_SCHEMA))
    else:
        writer.close(); os.replace(duration_temp, duration_path)
    if scanned != shard["evidence_rows"]: raise RuntimeError("evidence row denominator changed")

    fnames = feature_names(); rows = []
    for k, flags in features.items():
        row = dict(zip(KEY, k)); row.update({name: name in flags for name in fnames}); rows.append(row)
    feature_path = out / (shard["shard_id"] + ".strength_features.parquet")
    write_atomic(feature_path, pa.Table.from_pylist(rows, schema=feature_schema()))
    receipt = {
        "version": VERSION, "status": "complete", "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "shard_id": shard["shard_id"], "region": a.region, "source_file": shard["source_file"],
        "input_evidence": {"path": evidence, "sha256": shard["evidence_sha256"], "rows": scanned},
        "experience_evidence_rows": exp_rows, "numeric_clause_rows": numeric_rows,
        "outputs": {
            "strength_features": {"path": str(feature_path), "rows": len(rows), "bytes": feature_path.stat().st_size, "sha256": sha(feature_path)},
            "duration_clauses": {"path": str(duration_path), "rows": numeric_rows, "bytes": duration_path.stat().st_size, "sha256": sha(duration_path)},
        },
        "semantics": "existing evidence projection; no parser, lexicon, model, or text re-extraction",
    }
    rp = out / (shard["shard_id"] + ".closing.receipt.json"); temp = Path(str(rp) + ".tmp")
    temp.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n"); os.replace(temp, rp)


if __name__ == "__main__": main()
