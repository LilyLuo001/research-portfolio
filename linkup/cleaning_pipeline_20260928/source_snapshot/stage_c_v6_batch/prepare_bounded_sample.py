#!/usr/bin/env python3
"""Build a deterministic, parser-independent <=100k USA sample.

The frame is the fixed 32-shard projection created by stage_c_evaluation_v2.
Description text is decoded only after selection.  The frame is regional and
does not support national/population claims.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import shutil
from collections import Counter, defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

PREFIXES = "0123456789abcdef"
SNAPSHOT = dt.datetime(2026, 9, 6, 23, 59, 59)
SAMPLE_SCHEMA = pa.schema([
    ("JOB_HASH", pa.string()), ("DESCRIPTION_COMPANY_ID", pa.decimal128(10, 0)),
    ("SOURCE_FILE", pa.string()), ("SOURCE_ROW", pa.int64()),
    ("SOURCE_FILE_BYTES", pa.int64()), ("SOURCE_FILE_ROWS", pa.int64()),
    ("DESCRIPTION_RANK_HASH", pa.string()), ("SAMPLE_RANK_HASH", pa.string()),
    ("RECORD_COMPANY_ID", pa.decimal128(10, 0)), ("COUNTRY", pa.string()),
    ("STATE", pa.string()), ("CREATED", pa.timestamp("ms")),
    ("LAST_UPDATED", pa.timestamp("ms")), ("LAST_CHECKED", pa.timestamp("ms")),
    ("DELETE_DATE", pa.timestamp("ms")), ("RECORD_SOURCE_ROW", pa.uint64()),
])
TEXT_SCHEMA = pa.schema(list(SAMPLE_SCHEMA) + [
    ("SOURCE_ROW_GROUP", pa.int32()), ("ROW_IN_GROUP", pa.int64()),
    ("DESCRIPTION", pa.string()), ("DESCRIPTION_UTF8_BYTES", pa.int64()),
])


def atomic_json(path, value):
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")
    os.replace(temp, path)


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tree_bytes(path):
    return sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file())


def check_cap(path, cap):
    used = tree_bytes(path)
    if used > cap:
        raise RuntimeError("sample output cap exceeded: %d > %d" % (used, cap))
    return used


def rank(seed, job_hash):
    return hashlib.sha256((seed + "\0" + job_hash).encode()).hexdigest()


def join_prefix(args):
    prefix, key_path, records_index, scratch, seed, sample_size = args
    pa.set_cpu_count(2)
    desc = pq.read_table(key_path)
    hashes = desc["JOB_HASH"].to_pylist()
    seen = {}
    duplicate_rows = 0
    for i, value in enumerate(hashes):
        pointer = (desc["SOURCE_FILE"][i].as_py(), desc["SOURCE_ROW"][i].as_py())
        if value in seen:
            duplicate_rows += 1
            if pointer < seen[value][0]:
                seen[value] = (pointer, i)
        else:
            seen[value] = (pointer, i)
    take = pa.array(sorted(v[1] for v in seen.values()), type=pa.int64())
    unique = desc.take(take)
    files = sorted((Path(records_index) / ("hash_prefix=" + prefix)).glob("*.parquet"))
    columns = ["JOB_HASH", "COMPANY_ID", "COUNTRY", "STATE", "CREATED",
               "LAST_UPDATED", "LAST_CHECKED", "DELETE_DATE", "RECORD_SOURCE_ROW"]
    records = pq.read_table(files, columns=columns, use_threads=True)
    if pc.count_distinct(records["JOB_HASH"]).as_py() != records.num_rows:
        raise RuntimeError("Records index prefix is not unique: " + prefix)
    index = pc.index_in(unique["JOB_HASH"], value_set=records["JOB_HASH"])
    aligned = {name: pc.take(records[name], index).to_pylist() for name in columns[1:]}
    source = {name: unique[name].to_pylist() for name in unique.column_names}
    counts = Counter(projected_rows=desc.num_rows, unique_description_keys=unique.num_rows,
                     duplicate_description_rows=duplicate_rows)
    eligible = []
    for i in range(unique.num_rows):
        if index[i].as_py() is None:
            counts["record_unmatched"] += 1
            continue
        counts["record_matched"] += 1
        country = aligned["COUNTRY"][i]
        if country != "USA":
            counts["record_matched_non_usa"] += 1
            continue
        counts["eligible_unique_usa"] += 1
        row = {
            "JOB_HASH": source["JOB_HASH"][i],
            "DESCRIPTION_COMPANY_ID": source["DESCRIPTION_COMPANY_ID"][i],
            "SOURCE_FILE": source["SOURCE_FILE"][i], "SOURCE_ROW": source["SOURCE_ROW"][i],
            "SOURCE_FILE_BYTES": source["SOURCE_FILE_BYTES"][i],
            "SOURCE_FILE_ROWS": source["SOURCE_FILE_ROWS"][i],
            "DESCRIPTION_RANK_HASH": source["RANK_HASH"][i],
            "SAMPLE_RANK_HASH": rank(seed, source["JOB_HASH"][i]),
            "RECORD_COMPANY_ID": aligned["COMPANY_ID"][i], "COUNTRY": country,
            "STATE": aligned["STATE"][i], "CREATED": aligned["CREATED"][i],
            "LAST_UPDATED": aligned["LAST_UPDATED"][i],
            "LAST_CHECKED": aligned["LAST_CHECKED"][i], "DELETE_DATE": aligned["DELETE_DATE"][i],
            "RECORD_SOURCE_ROW": aligned["RECORD_SOURCE_ROW"][i],
        }
        eligible.append(row)
    selected = sorted(eligible, key=lambda x: (x["SAMPLE_RANK_HASH"], x["JOB_HASH"]))[:sample_size]
    destination = Path(scratch) / ("prefix_%s.parquet" % prefix)
    pq.write_table(pa.Table.from_pylist(selected, schema=SAMPLE_SCHEMA), destination,
                   compression="zstd", row_group_size=4096)
    report = dict(counts)
    report.update({"prefix": prefix, "retained_for_global_merge": len(selected),
                   "records_index_rows_read": records.num_rows})
    atomic_json(Path(scratch) / ("prefix_%s.json" % prefix), report)
    return report


def decode_text(selected, source_manifest):
    paths = {row["file_name"]: Path(row["path"]) for row in source_manifest["sources"]}
    by_file = defaultdict(list)
    for row in selected:
        by_file[row["SOURCE_FILE"]].append(row)
    output, decoded_groups = [], 0
    for name, rows in sorted(by_file.items()):
        pf = pq.ParquetFile(paths[name])
        offsets, cursor = [], 0
        for group in range(pf.num_row_groups):
            count = pf.metadata.row_group(group).num_rows
            offsets.append((cursor, cursor + count, group))
            cursor += count
        wanted = defaultdict(list)
        for row in rows:
            for low, high, group in offsets:
                if low <= row["SOURCE_ROW"] < high:
                    wanted[group].append((row, row["SOURCE_ROW"] - low))
                    break
            else:
                raise RuntimeError("source row outside shard")
        for group, pairs in wanted.items():
            decoded_groups += 1
            table = pf.read_row_group(group, columns=["JOB_HASH", "DESCRIPTION"])
            for row, within in pairs:
                if table["JOB_HASH"][within].as_py() != row["JOB_HASH"]:
                    raise RuntimeError("source pointer mismatch")
                text = table["DESCRIPTION"][within].as_py()
                item = dict(row)
                item.update({"SOURCE_ROW_GROUP": group, "ROW_IN_GROUP": within,
                             "DESCRIPTION": text,
                             "DESCRIPTION_UTF8_BYTES": None if text is None else len(text.encode("utf-8"))})
                output.append(item)
    return output, decoded_groups


def date_status(value):
    if value is None:
        return "created_missing"
    if getattr(value, "tzinfo", None):
        value = value.astimezone(dt.timezone.utc).replace(tzinfo=None)
    if value > SNAPSHOT:
        return "created_after_snapshot"
    if value.year < 2015:
        return "created_pre_2015"
    quarter = (value.month - 1) // 3 + 1
    if value.year == 2026 and quarter == 3:
        return "2026Q3_partial"
    return "%dQ%d_complete_queue" % (value.year, quarter)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    output = Path(cfg["output_dir"])
    output.mkdir(parents=True, exist_ok=False)
    scratch = output / "prefix_scratch"
    scratch.mkdir()
    frame = Path(cfg["frame_dir"])
    checkpoint = json.loads((frame / "projection_checkpoint.json").read_text())
    if checkpoint.get("status") != "complete":
        raise RuntimeError("projection checkpoint is not complete")
    complete = json.loads(Path(cfg["records_index_complete"]).read_text())
    manifest_path = Path(cfg["records_index_complete"]).parent / complete["manifest"]
    if complete["sha256"] != sha_file(manifest_path):
        raise RuntimeError("Records index manifest hash mismatch")
    tasks = [(prefix, str(frame / "keys_by_prefix" / ("prefix_%s.parquet" % prefix)),
              cfg["records_index"], str(scratch), cfg["seed"], cfg["sample_size"])
             for prefix in PREFIXES]
    workers = min(cfg["join_workers"], max(1, int(os.environ.get("SLURM_CPUS_PER_TASK", "1")) // 2))
    with cf.ProcessPoolExecutor(max_workers=workers) as pool:
        reports = list(pool.map(join_prefix, tasks))
    check_cap(output, cfg["max_sample_bytes"])
    candidates = []
    for prefix in PREFIXES:
        candidates.extend(pq.read_table(scratch / ("prefix_%s.parquet" % prefix)).to_pylist())
    selected = sorted(candidates, key=lambda x: (x["SAMPLE_RANK_HASH"], x["JOB_HASH"]))[:cfg["sample_size"]]
    if len(selected) != cfg["sample_size"] or len({x["JOB_HASH"] for x in selected}) != len(selected):
        raise RuntimeError("selected sample size/uniqueness failure")
    source_manifest = json.loads((frame / "source_selection_manifest.json").read_text())
    with_text, decoded_groups = decode_text(selected, source_manifest)
    with_text.sort(key=lambda x: (x["SAMPLE_RANK_HASH"], x["JOB_HASH"]))
    pq.write_table(pa.Table.from_pylist(with_text, schema=TEXT_SCHEMA),
                   output / "selected_ads_with_text.parquet", compression="zstd", row_group_size=2048)
    metadata_rows = []
    for row in with_text:
        item = {k: v for k, v in row.items() if k != "DESCRIPTION"}
        item["CREATED_QUEUE_STATUS"] = date_status(row["CREATED"])
        item["COMPANY_ID_MATCH"] = row["DESCRIPTION_COMPANY_ID"] == row["RECORD_COMPANY_ID"]
        metadata_rows.append(item)
    pq.write_table(pa.Table.from_pylist(metadata_rows), output / "sample_metadata.parquet",
                   compression="zstd", row_group_size=4096)
    totals = Counter()
    for report in reports:
        totals.update({k: v for k, v in report.items() if isinstance(v, int)})
    date_counts = Counter(x["CREATED_QUEUE_STATUS"] for x in metadata_rows)
    report = {
        "status": "complete", "seed": cfg["seed"],
        "selection_rule": "bottom SHA256(seed + NUL + JOB_HASH) among unique Records-matched USA keys",
        "prediction_or_text_selected": False, "sample_rows": len(with_text),
        "eligible_unique_usa": totals["eligible_unique_usa"],
        "projected_description_rows": totals["projected_rows"],
        "unique_description_keys": totals["unique_description_keys"],
        "duplicate_description_rows": totals["duplicate_description_rows"],
        "record_matched": totals["record_matched"], "record_unmatched": totals["record_unmatched"],
        "record_matched_non_usa": totals["record_matched_non_usa"],
        "decoded_description_row_groups": decoded_groups,
        "selected_empty_description": sum(not x["DESCRIPTION"] for x in with_text),
        "selected_company_id_mismatch": sum(not x["COMPANY_ID_MATCH"] for x in metadata_rows),
        "created_queue_status_counts": dict(sorted(date_counts.items())),
        "source_manifest_sha256": sha_file(frame / "source_selection_manifest.json"),
        "projection_checkpoint_sha256": sha_file(frame / "projection_checkpoint.json"),
        "records_index_complete_sha256": sha_file(cfg["records_index_complete"]),
        "scope_warning": "Exploratory sample from 32 fixed Kunshan-held description shards; not national or population representative.",
        "text_time_warning": "Delivery snapshot text grouped by Records CREATED queue; not historical text at CREATED.",
    }
    shutil.rmtree(scratch)
    report["persistent_bytes"] = check_cap(output, cfg["max_sample_bytes"])
    atomic_json(output / "SAMPLE_REPORT.json", report)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
