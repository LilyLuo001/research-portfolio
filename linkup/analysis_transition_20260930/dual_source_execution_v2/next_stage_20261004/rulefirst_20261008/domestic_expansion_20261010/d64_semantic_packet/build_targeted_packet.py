#!/usr/bin/env python3
import datetime as dt
import hashlib
import json
import os
from pathlib import Path

import pyarrow.parquet as pq


BASE = Path("/work/home/lilysharp/linkup_rulefirst_20261008/domestic_expansion_20261010")
WAVE = BASE / "wz_wave_0001"
OUT = BASE / "d64_semantic_packet"
PRIVATE = OUT / "private" / "TARGETED_SEMANTIC_PACKET_PRIVATE.json"
PUBLIC = OUT / "public" / "TARGETED_SEMANTIC_PACKET_RECEIPT_PUBLIC.json"

CATEGORIES = (
    "general_experience",
    "related_experience",
    "tool_numeric_condition",
    "graduate_no_experience",
    "independent_supervision",
    "technology_genai",
)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, obj, mode=0o600):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    os.chmod(tmp, mode)
    os.replace(tmp, path)


def text(v):
    return "" if v is None else str(v)


def categories(row):
    rule = text(row.get("rule")).lower()
    quote = text(row.get("quote")).lower()
    kind = text(row.get("kind")).lower()
    tech = text(row.get("technology")).lower()
    objects = text(row.get("objects_json"))
    numeric = row.get("lower_years") is not None or row.get("upper_years") is not None
    found = []
    if "experience" in kind and "related" not in rule and "related" not in quote and (
        "general" in rule or "prior_experience" in rule or "experience" in rule
    ):
        found.append("general_experience")
    if "related" in rule or ("experience" in kind and "related" in quote):
        found.append("related_experience")
    if numeric and (objects not in ("", "[]", "null", "None") or tech or "tool" in rule):
        found.append("tool_numeric_condition")
    if ("graduate" in quote or "graduation" in quote) and not numeric:
        found.append("graduate_no_experience")
    if any(x in quote or x in rule for x in ("independent", "independently", "supervision", "supervised")):
        found.append("independent_supervision")
    if tech in ("genai", "generative_ai", "generative ai") or "genai" in tech:
        found.append("technology_genai")
    return found


def row_context(source_path, source_row, quote):
    pf = pq.ParquetFile(source_path)
    idx = int(source_row)
    offset = 0
    description = ""
    for rg in range(pf.num_row_groups):
        n = pf.metadata.row_group(rg).num_rows
        if offset <= idx < offset + n:
            table = pf.read_row_group(rg, columns=["DESCRIPTION"])
            description = text(table.column("DESCRIPTION")[idx - offset].as_py())
            break
        offset += n
    q = text(quote)
    pos = description.find(q)
    if pos < 0:
        pos = description.lower().find(q.lower())
    if pos < 0:
        return {"context": None, "context_match": False}
    return {
        "context": description[max(0, pos - 300):min(len(description), pos + len(q) + 300)],
        "context_match": True,
    }


def main():
    manifest = json.load(open(WAVE / "private/WAVE_0001_MANIFEST_PRIVATE.json", encoding="utf-8"))
    by_file = {Path(x["source_path"]).name: x for x in manifest["selected_entries"]}
    selected = {k: [] for k in CATEGORIES}
    cols = [
        "JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW", "evidence_index",
        "kind", "rule", "quote", "section", "objects_json", "strength", "scope",
        "duration_kind", "lower_years", "upper_years", "strict_lower", "outcome_status",
        "review_reasons_json", "technology", "role_cue", "negated", "task_family",
        "overlay_annotations_json", "candidate_heading_scope", "heading_scope_status",
        "d57_current_duty_mentoring_candidate", "mentoring_referent_or_prior_experience_marker",
    ]
    scanned = 0
    files = sorted((WAVE / "output").glob("shard_*/EVIDENCE_PRIVATE.parquet"))
    for path in files:
        pf = pq.ParquetFile(path)
        for batch in pf.iter_batches(batch_size=8192, columns=cols):
            for row in batch.to_pylist():
                scanned += 1
                for category in categories(row):
                    if len(selected[category]) >= 2:
                        continue
                    source = by_file.get(Path(text(row["SOURCE_FILE"])).name)
                    if not source:
                        continue
                    item = dict(row)
                    item["category"] = category
                    item["evidence_parquet"] = str(path)
                    item["source_path"] = source["source_path"]
                    item.update(row_context(source["source_path"], row["SOURCE_ROW"], row["quote"]))
                    selected[category].append(item)
            if all(len(v) >= 2 for v in selected.values()):
                break
        if all(len(v) >= 2 for v in selected.values()):
            break
    packet = {
        "version": "d64-targeted-semantic-diagnostic-v1",
        "purpose": "directed diagnostic sample; not an accuracy estimate",
        "source_wave": 1,
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "rows_scanned_until_complete_or_eof": scanned,
        "categories": selected,
    }
    atomic_json(PRIVATE, packet, 0o600)
    receipt = {
        "version": "d64-targeted-semantic-diagnostic-receipt-v1",
        "status": "retrieval_complete_not_semantically_validated" if all(len(v) == 2 for v in selected.values()) else "retrieval_partial_not_semantically_validated",
        "purpose": packet["purpose"],
        "interpretation": "Directed retrieval buckets only; bucket membership is not a validated feature label and this packet is not an accuracy estimate.",
        "private_packet_path": str(PRIVATE),
        "private_packet_sha256": sha256(PRIVATE),
        "source_wave": 1,
        "evidence_files": len(files),
        "rows_scanned_until_complete_or_eof": scanned,
        "retrieval_bucket_counts": {k: len(v) for k, v in selected.items()},
        "context_match_counts": {k: sum(bool(x["context_match"]) for x in v) for k, v in selected.items()},
        "retrieved_kind_rule": [
            {"retrieval_bucket": bucket, "kind": row.get("kind"), "rule": row.get("rule")}
            for bucket, rows in selected.items() for row in rows
        ],
        "created_utc": packet["created_utc"],
    }
    atomic_json(PUBLIC, receipt, 0o644)
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
