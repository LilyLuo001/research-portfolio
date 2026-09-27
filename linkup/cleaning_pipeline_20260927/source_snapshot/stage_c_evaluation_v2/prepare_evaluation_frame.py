#!/usr/bin/env python3
"""Build a bounded, deterministic USA evaluation candidate pool.

This is sampling infrastructure, not a parser evaluation. It scans only key
columns in a fixed set of previously unused description shards, joins the
existing compact Records index, retains bottom-k USA keys by frozen time
stratum, and decodes text only for the retained candidate pool.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import hashlib
import heapq
import json
import os
import shutil
from collections import defaultdict
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

PREFIXES = "0123456789abcdef"
SNAPSHOT = dt.datetime(2026, 9, 6, 23, 59, 59)
KEY_SCHEMA = pa.schema([
    ("JOB_HASH", pa.string()), ("DESCRIPTION_COMPANY_ID", pa.decimal128(10, 0)),
    ("SOURCE_FILE", pa.string()), ("SOURCE_ROW", pa.int64()),
    ("SOURCE_FILE_BYTES", pa.int64()), ("SOURCE_FILE_ROWS", pa.int64()),
    ("RANK_HASH", pa.string()),
])
CANDIDATE_SCHEMA = pa.schema(list(KEY_SCHEMA) + [
    ("RECORD_MATCH", pa.bool_()), ("RECORD_COMPANY_ID", pa.decimal128(10, 0)),
    ("COUNTRY", pa.string()), ("STATE", pa.string()), ("CREATED", pa.timestamp("ms")),
    ("LAST_UPDATED", pa.timestamp("ms")), ("LAST_CHECKED", pa.timestamp("ms")),
    ("DELETE_DATE", pa.timestamp("ms")), ("RECORD_SOURCE_ROW", pa.uint64()),
    ("TIME_STRATUM", pa.string()),
])
POOL_SCHEMA = pa.schema(list(CANDIDATE_SCHEMA) + [
    ("SOURCE_ROW_GROUP", pa.int32()), ("ROW_IN_GROUP", pa.int64()),
    ("DESCRIPTION", pa.string()), ("DESCRIPTION_UTF8_BYTES", pa.int64()),
    ("FRAME_STRATUM_DENOMINATOR", pa.int64()), ("POOL_STRATUM_N", pa.int32()),
])


def atomic_json(path, obj):
    tmp = Path(str(path) + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n")
    os.replace(tmp, path)


def sha_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def tree_bytes(path):
    return sum(p.stat().st_size for p in Path(path).rglob("*") if p.is_file())


def check_cap(path, cap):
    used = tree_bytes(path)
    if used > cap:
        raise RuntimeError("output cap exceeded: %d > %d" % (used, cap))
    return used


def stable_rank(seed, *parts):
    return hashlib.sha256((seed + "\0" + "\0".join(map(str, parts))).encode()).hexdigest()


def source_info(path):
    path = Path(path)
    pf = pq.ParquetFile(path)
    st = path.stat()
    return {"file_name": path.name, "path": str(path), "bytes": st.st_size,
            "mtime_ns": st.st_mtime_ns, "rows": pf.metadata.num_rows,
            "row_groups": pf.metadata.num_row_groups,
            "schema_sha256": hashlib.sha256(str(pf.schema_arrow).encode()).hexdigest()}


def source_fingerprint(items):
    stable = [(x["file_name"], x["bytes"], x["mtime_ns"], x["rows"], x["schema_sha256"])
              for x in items]
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()


def clean_dt(value):
    if value is None:
        return None
    if getattr(value, "tzinfo", None):
        return value.astimezone(dt.timezone.utc).replace(tzinfo=None)
    return value


def time_stratum(created):
    created = clean_dt(created)
    if created is None or created > SNAPSHOT:
        return None
    year = created.year
    if year == 2015:
        return "2015"
    if 2016 <= year <= 2017:
        return "2016-17"
    if 2018 <= year <= 2019:
        return "2018-19"
    if 2020 <= year <= 2022:
        return "2020-22"
    if year in (2023, 2024, 2025):
        return str(year)
    if year == 2026:
        return "2026_partial"
    return None


def choose_sources(cfg):
    paths = [Path(x) for x in Path(cfg["description_manifest"]).read_text().splitlines() if x.strip()]
    if len(paths) != len(set(map(str, paths))):
        raise RuntimeError("duplicate path in description manifest")
    prior = json.loads(Path(cfg["prior_source_selection_manifest"]).read_text())
    used = {x["file_name"] for x in prior["sources"]}
    eligible = [p for p in paths if p.name not in used]
    chosen_paths = sorted(eligible, key=lambda p: (stable_rank(cfg["seed"], "source", p.name), p.name))[:cfg["selected_source_files"]]
    if len(chosen_paths) != cfg["selected_source_files"]:
        raise RuntimeError("insufficient unused source shards")
    return len(paths), len(eligible), [source_info(p) for p in chosen_paths], sorted(used)


def project_keys(chosen, out, cfg):
    keydir = out / "keys_by_prefix"
    keydir.mkdir(parents=True, exist_ok=True)
    writers, temps, counts = {}, {}, defaultdict(int)
    try:
        for info in chosen:
            pf = pq.ParquetFile(info["path"])
            source_row = 0
            for batch in pf.iter_batches(columns=["JOB_HASH", "COMPANY_ID"],
                                         batch_size=cfg["batch_rows"], use_threads=True):
                hashes = batch.column(0)
                if hashes.null_count or not pc.all(pc.match_substring_regex(hashes, r"^[0-9a-f]{32}$")).as_py():
                    raise RuntimeError("null or malformed JOB_HASH in " + info["file_name"])
                values = hashes.to_pylist()
                first = np.asarray(pc.utf8_slice_codeunits(hashes, 0, 1).to_numpy(zero_copy_only=False))
                ranks = [stable_rank(cfg["seed"], "ad", h, info["file_name"], source_row + i)
                         for i, h in enumerate(values)]
                base = pa.Table.from_arrays([
                    hashes, batch.column(1), pa.array([info["file_name"]] * batch.num_rows),
                    pa.array(np.arange(source_row, source_row + batch.num_rows, dtype=np.int64)),
                    pa.array([info["bytes"]] * batch.num_rows, type=pa.int64()),
                    pa.array([info["rows"]] * batch.num_rows, type=pa.int64()), pa.array(ranks),
                ], schema=KEY_SCHEMA)
                for prefix in PREFIXES:
                    idx = np.flatnonzero(first == prefix)
                    if not idx.size:
                        continue
                    if prefix not in writers:
                        temp = keydir / ("prefix_%s.parquet.tmp" % prefix)
                        temps[prefix] = temp
                        writers[prefix] = pq.ParquetWriter(temp, KEY_SCHEMA, compression="zstd", use_dictionary=True)
                    part = base.take(pa.array(idx, type=pa.int64()))
                    writers[prefix].write_table(part)
                    counts[prefix] += part.num_rows
                source_row += batch.num_rows
            if source_row != info["rows"]:
                raise RuntimeError("source row conservation failed")
            check_cap(out, cfg["max_output_bytes"])
    finally:
        for writer in writers.values():
            writer.close()
    for prefix, temp in temps.items():
        final = temp.with_suffix("")
        if pq.ParquetFile(temp).metadata.num_rows != counts[prefix]:
            raise RuntimeError("prefix footer mismatch")
        os.replace(temp, final)
    return dict(counts)


def join_prefix(args):
    prefix, keyfile, indexdir, outdir, pool_per_stratum = args
    pa.set_cpu_count(2)
    desc = pq.read_table(keyfile)
    files = sorted((Path(indexdir) / ("hash_prefix=" + prefix)).glob("*.parquet"))
    cols = ["JOB_HASH", "COMPANY_ID", "COUNTRY", "STATE", "CREATED", "LAST_UPDATED",
            "LAST_CHECKED", "DELETE_DATE", "RECORD_SOURCE_ROW"]
    rec = pq.read_table(files, columns=cols, use_threads=True)
    idx = pc.index_in(desc["JOB_HASH"], value_set=rec["JOB_HASH"])
    aligned = {c: pc.take(rec[c], idx).to_pylist() for c in cols[1:]}
    d = {c: desc[c].to_pylist() for c in desc.column_names}
    heaps, denoms, serial = defaultdict(list), defaultdict(int), 0
    for i in range(desc.num_rows):
        if idx[i].as_py() is None or aligned["COUNTRY"][i] != "USA":
            continue
        stratum = time_stratum(aligned["CREATED"][i])
        if stratum is None:
            continue
        denoms[stratum] += 1
        row = {c: d[c][i] for c in d}
        row.update({"RECORD_MATCH": True, "RECORD_COMPANY_ID": aligned["COMPANY_ID"][i],
                    "COUNTRY": "USA", "STATE": aligned["STATE"][i], "CREATED": aligned["CREATED"][i],
                    "LAST_UPDATED": aligned["LAST_UPDATED"][i], "LAST_CHECKED": aligned["LAST_CHECKED"][i],
                    "DELETE_DATE": aligned["DELETE_DATE"][i], "RECORD_SOURCE_ROW": aligned["RECORD_SOURCE_ROW"][i],
                    "TIME_STRATUM": stratum})
        value = int(row["RANK_HASH"], 16)
        serial += 1
        item = (-value, serial, row)
        heap = heaps[stratum]
        if len(heap) < pool_per_stratum:
            heapq.heappush(heap, item)
        elif value < -heap[0][0]:
            heapq.heapreplace(heap, item)
    rows = [item[2] for heap in heaps.values() for item in heap]
    dest = Path(outdir) / ("candidates_%s.parquet" % prefix)
    temp = Path(str(dest) + ".tmp")
    pq.write_table(pa.Table.from_pylist(rows, schema=CANDIDATE_SCHEMA), temp, compression="zstd")
    os.replace(temp, dest)
    meta = {"prefix": prefix, "projected_description_rows": desc.num_rows,
            "record_index_rows_read": rec.num_rows, "candidate_rows": len(rows),
            "usa_time_frame_denominators": dict(denoms)}
    atomic_json(Path(outdir) / ("prefix_%s.json" % prefix), meta)
    return meta


def merge_pool(out, cfg):
    canddir = out / "prefix_candidates"
    denoms, heaps, serial = defaultdict(int), defaultdict(list), 0
    for path in sorted(canddir.glob("prefix_?.json")):
        for key, n in json.loads(path.read_text())["usa_time_frame_denominators"].items():
            denoms[key] += n
    for path in sorted(canddir.glob("candidates_?.parquet")):
        for row in pq.read_table(path).to_pylist():
            stratum = row["TIME_STRATUM"]
            value = int(row["RANK_HASH"], 16)
            serial += 1
            item = (-value, serial, row)
            heap = heaps[stratum]
            if len(heap) < cfg["pool_per_stratum"]:
                heapq.heappush(heap, item)
            elif value < -heap[0][0]:
                heapq.heapreplace(heap, item)
    rows = []
    for stratum, heap in sorted(heaps.items()):
        selected = sorted((x[2] for x in heap), key=lambda r: r["RANK_HASH"])
        for row in selected:
            row["_DENOM"] = denoms[stratum]
            row["_POOL_N"] = len(selected)
            rows.append(row)
    return rows, denoms


def fetch_text(rows, chosen, out):
    by_file = defaultdict(list)
    for row in rows:
        by_file[row["SOURCE_FILE"]].append(row)
    manifest = {x["file_name"]: Path(x["path"]) for x in chosen}
    final, decoded_groups = [], 0
    for name, items in sorted(by_file.items()):
        pf = pq.ParquetFile(manifest[name])
        offsets, cursor = [], 0
        for group in range(pf.metadata.num_row_groups):
            n = pf.metadata.row_group(group).num_rows
            offsets.append((cursor, cursor + n, group))
            cursor += n
        wanted = defaultdict(list)
        for row in items:
            for low, high, group in offsets:
                if low <= row["SOURCE_ROW"] < high:
                    wanted[group].append((row, row["SOURCE_ROW"] - low))
                    break
        for group, pairs in wanted.items():
            decoded_groups += 1
            table = pf.read_row_group(group, columns=["JOB_HASH", "DESCRIPTION"])
            for row, within in pairs:
                if table["JOB_HASH"][within].as_py() != row["JOB_HASH"]:
                    raise RuntimeError("source pointer mismatch")
                text = table["DESCRIPTION"][within].as_py()
                item = {k: v for k, v in row.items() if not k.startswith("_")}
                item.update({"SOURCE_ROW_GROUP": group, "ROW_IN_GROUP": within, "DESCRIPTION": text,
                             "DESCRIPTION_UTF8_BYTES": None if text is None else len(text.encode("utf-8")),
                             "FRAME_STRATUM_DENOMINATOR": row["_DENOM"], "POOL_STRATUM_N": row["_POOL_N"]})
                final.append(item)
    dest = out / "candidate_pool.parquet"
    temp = Path(str(dest) + ".tmp")
    pq.write_table(pa.Table.from_pylist(final, schema=POOL_SCHEMA), temp, compression="zstd")
    os.replace(temp, dest)
    return len(final), decoded_groups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    cfg = json.loads(Path(args.config).read_text())
    out = Path(cfg["output_dir"])
    out.mkdir(parents=True, exist_ok=True)
    lock = out / ".lock"
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        complete = Path(cfg["records_index_complete"])
        marker = json.loads(complete.read_text())
        manifest_path = complete.parent / marker["manifest"]
        if marker["sha256"] != sha_file(manifest_path):
            raise RuntimeError("Records index manifest hash mismatch")
        available, unused, chosen, prior_sources = choose_sources(cfg)
        fp = source_fingerprint(chosen)
        atomic_json(out / "source_selection_manifest.json", {
            "seed": cfg["seed"], "available_kunshan_sources": available,
            "unused_after_prior_pilot": unused, "selected_unused_sources": len(chosen),
            "prior_pilot_source_count": len(prior_sources), "source_fingerprint": fp,
            "sources": chosen,
            "scope_warning": cfg["scope_warning"],
        })
        checkpoint = out / "projection_checkpoint.json"
        if not checkpoint.exists():
            counts = project_keys(chosen, out, cfg)
            atomic_json(checkpoint, {"status": "complete", "source_fingerprint": fp,
                                     "rows": sum(counts.values()), "prefix_rows": counts})
        elif json.loads(checkpoint.read_text()).get("source_fingerprint") != fp:
            raise RuntimeError("checkpoint source mismatch")
        canddir = out / "prefix_candidates"
        canddir.mkdir(exist_ok=True)
        tasks = []
        for prefix in PREFIXES:
            keyfile = out / "keys_by_prefix" / ("prefix_%s.parquet" % prefix)
            if keyfile.exists() and not (canddir / ("prefix_%s.json" % prefix)).exists():
                tasks.append((prefix, str(keyfile), cfg["records_index"], str(canddir), cfg["pool_per_stratum"]))
        workers = min(cfg["join_workers"], max(1, int(os.environ.get("SLURM_CPUS_PER_TASK", "1")) // 2))
        if tasks:
            with cf.ProcessPoolExecutor(max_workers=workers) as pool:
                for _ in pool.map(join_prefix, tasks):
                    check_cap(out, cfg["max_output_bytes"])
        rows, denoms = merge_pool(out, cfg)
        actual, decoded_groups = fetch_text(rows, chosen, out)
        if actual != len(rows) or len({r["JOB_HASH"] for r in rows}) != len(rows):
            raise RuntimeError("candidate pool conservation/uniqueness failure")
        after = [source_info(x["path"]) for x in chosen]
        if source_fingerprint(after) != fp:
            raise RuntimeError("source fingerprint changed during run")
        report = {
            "status": "complete", "seed": cfg["seed"], "selected_unused_source_files": len(chosen),
            "selected_source_rows": sum(x["rows"] for x in chosen), "candidate_pool_rows": actual,
            "candidate_pool_counts": dict(sorted((k, sum(r["TIME_STRATUM"] == k for r in rows)) for k in denoms)),
            "frame_denominators_by_time": dict(sorted(denoms.items())),
            "decoded_description_row_groups": decoded_groups, "source_total_row_groups": sum(x["row_groups"] for x in chosen),
            "raw_text_read_policy": "Key columns scanned in selected unused shards; DESCRIPTION decoded only in row groups containing retained pool rows.",
            "occupation_status": "Not joined: no bounded job-level O*NET lookup index was available. Occupation coverage is an explicit pack limitation.",
            "scope_warning": cfg["scope_warning"], "output_bytes": check_cap(out, cfg["max_output_bytes"]),
            "completed_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        }
        atomic_json(out / "frame_report.json", report)
        atomic_json(out / "FRAME_COMPLETE", {"status": "complete", "report_sha256": sha_file(out / "frame_report.json")})
        print(json.dumps(report, sort_keys=True))
    finally:
        os.close(fd)
        if lock.exists():
            lock.unlink()


if __name__ == "__main__":
    main()
