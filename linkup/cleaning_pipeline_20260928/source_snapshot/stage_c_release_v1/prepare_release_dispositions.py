#!/usr/bin/env python3
"""Bounded keys-only regional census and release disposition builder.

The program processes exactly one first-hex JOB_HASH prefix at a time.  It
reuses the complete Kunshan key projection and the complete Wuzhen occurrence
sidecars; it never reads description text.  A matched-USA JOB_HASH observed
more than once is wholly quarantined because key equality does not establish
body/version identity.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from collections import Counter
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

PREFIXES = "0123456789abcdef"
KEY_SCHEMA = pa.schema([
    ("JOB_HASH", pa.string()), ("DESCRIPTION_COMPANY_ID", pa.decimal128(10, 0)),
    ("REGION", pa.string()), ("SOURCE_FILE", pa.string()),
    ("SOURCE_ROW", pa.int64()), ("SHARD_ID", pa.string()),
])
SIDECAR_SCHEMA = pa.schema([
    ("SOURCE_ROW", pa.int64()), ("JOB_HASH", pa.string()),
    ("MATCH_DISPOSITION", pa.string()), ("RECORD_SOURCE_ROW", pa.int64()),
    ("CREATED", pa.timestamp("ms")), ("COUNTRY", pa.string()),
    ("STATE", pa.string()), ("SOURCE_FILE", pa.string()),
    ("GLOBAL_KEY_OCCURRENCES", pa.int32()),
    ("DESCRIPTION_COMPANY_ID", pa.decimal128(10, 0)),
    ("RECORD_COMPANY_ID", pa.decimal128(10, 0)),
    ("COMPANY_ID_MATCH", pa.bool_()),
])
DISPOSITIONS = {
    "matched_usa_canonical", "matched_usa_duplicate_quarantine",
    "matched_non_usa", "matched_country_unknown", "record_unmatched",
}


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n")
    os.replace(temp, path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def shard_id(region: str, source_file: str) -> str:
    return hashlib.sha256((region + "\0" + source_file).encode()).hexdigest()


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def projection_path(root: Path, source_file: str) -> Path:
    """Map a raw shard name to its cached projection without double suffixes."""
    return root / (source_file if source_file.endswith(".parquet") else source_file + ".parquet")


def load_config(path: Path) -> dict:
    return json.loads(path.read_text())


def verified_prefix_receipt(path: Path, cfg: dict):
    if not path.exists():
        return None
    receipt = json.loads(path.read_text())
    if (receipt.get("status") != "complete"
            or receipt.get("config_sha256") != cfg["_config_sha256"]
            or receipt.get("script_sha256") != cfg["_script_sha256"]):
        raise RuntimeError("existing prefix receipt has a different code/config identity")
    for item in receipt.get("fragment_files", []):
        fragment = Path(item["path"])
        if (not fragment.is_file() or fragment.stat().st_size != item["bytes"]
                or pq.ParquetFile(fragment).metadata.num_rows != item["rows"]
                or sha256(fragment) != item["sha256"]):
            raise RuntimeError("existing prefix fragment failed receipt validation")
    return receipt


def load_inventory(paths) -> tuple[dict, dict]:
    sources, aliases = {}, {}
    for path in paths:
        document = json.loads(Path(path).read_text())
        region = document["region"]
        if document["count"] != len(document["sources"]):
            raise ValueError("inventory count mismatch: " + str(path))
        for source in document["sources"]:
            name = source["file_name"]
            key = (region, name)
            if key in sources:
                raise ValueError("duplicate inventory source: %r" % (key,))
            item = dict(source)
            item["shard_id"] = shard_id(region, name)
            sources[key] = item
            without_parquet = name[:-8] if name.endswith(".parquet") else name
            for alias in (name, without_parquet):
                alias_key = (region, alias)
                if alias_key in aliases and aliases[alias_key] != name:
                    raise ValueError("ambiguous source alias: %r" % (alias_key,))
                aliases[alias_key] = name
    return sources, aliases


def validate_hashes(hashes: pa.Array, label: str) -> None:
    if hashes.null_count or not pc.all(pc.match_substring_regex(hashes, r"^[0-9a-f]{32}$")).as_py():
        raise ValueError("null or malformed JOB_HASH in " + label)


def append_keys(writer, hashes, company_ids, region, source_file, source_rows) -> int:
    count = len(hashes)
    if not count:
        return 0
    table = pa.Table.from_arrays([
        hashes, company_ids,
        pa.array([region] * count), pa.array([source_file] * count),
        pa.array(source_rows, type=pa.int64()),
        pa.array([shard_id(region, source_file)] * count),
    ], schema=KEY_SCHEMA)
    writer.write_table(table)
    return count


def stage_kunshan_prefix(cfg: dict, prefix: str, writer) -> tuple[int, dict]:
    report = json.loads(Path(cfg["kunshan_projection_report"]).read_text())
    if report.get("status") != "complete" or report.get("description_text_read") is not False:
        raise ValueError("Kunshan projection is not a complete keys-only artifact")
    root = Path(cfg["kunshan_projection_dir"])
    rows = selected = 0
    for source in report["source_counts"]:
        source_file = source["source_file"]
        path = projection_path(root, source_file)
        pf = pq.ParquetFile(path)
        if pf.metadata.num_rows != source["rows"]:
            raise ValueError("Kunshan projection footer mismatch: " + source_file)
        offset = 0
        for batch in pf.iter_batches(columns=["JOB_HASH", "DESCRIPTION_COMPANY_ID", "SOURCE_ID"],
                                      batch_size=cfg.get("batch_rows", 65536)):
            hashes = batch.column(0)
            validate_hashes(hashes, source_file)
            ids = batch.column(2)
            if ids.null_count or not pc.all(pc.equal(ids, pa.scalar(source["source_id"], ids.type))).as_py():
                raise ValueError("Kunshan SOURCE_ID mismatch: " + source_file)
            mask = pc.starts_with(hashes, prefix)
            indices = pc.indices_nonzero(mask)
            if len(indices):
                chosen_hashes = pc.take(hashes, indices)
                companies = pc.take(batch.column(1), indices)
                source_rows = [offset + value.as_py() for value in indices]
                selected += append_keys(writer, chosen_hashes, companies, "kunshan", source_file, source_rows)
            offset += batch.num_rows
        if offset != source["rows"]:
            raise ValueError("Kunshan row conservation failure: " + source_file)
        rows += offset
    if rows != report["rows"]:
        raise ValueError("Kunshan projection total differs from report")
    return selected, {"projection_rows": rows, "projection_files": report["files"]}


def stage_wuzhen_prefix(cfg: dict, prefix: str, writer, aliases: dict) -> tuple[int, dict]:
    spec = cfg["wuzhen_columns"]
    columns = [spec["job_hash"], spec["source_file"], spec["source_row"]]
    company_column = spec.get("description_company_id")
    if company_column:
        columns.append(company_column)
    rows = selected = 0
    seen_files = set()
    for path_string in cfg["wuzhen_occurrence_files"]:
        path = Path(path_string)
        pf = pq.ParquetFile(path)
        for batch in pf.iter_batches(columns=columns, batch_size=cfg.get("batch_rows", 65536)):
            names = {name: batch.column(i) for i, name in enumerate(columns)}
            hashes = names[spec["job_hash"]]
            validate_hashes(hashes, path.name)
            mask = pc.starts_with(hashes, prefix)
            indices = pc.indices_nonzero(mask)
            if len(indices):
                selected_rows = pc.take(names[spec["source_row"]], indices).to_pylist()
                selected_files = pc.take(names[spec["source_file"]], indices).to_pylist()
                selected_hashes = pc.take(hashes, indices)
                if company_column:
                    selected_companies = pc.take(names[company_column], indices)
                else:
                    selected_companies = pa.nulls(len(indices), type=pa.decimal128(10, 0))
                # A batch can contain several source shards; retain its order and
                # write contiguous source runs without building a regional list.
                run_start = 0
                while run_start < len(selected_files):
                    alias = selected_files[run_start]
                    canonical = aliases.get(("wuzhen", alias))
                    if canonical is None:
                        raise ValueError("Wuzhen source absent from frozen inventory: %r" % alias)
                    run_end = run_start + 1
                    while run_end < len(selected_files) and selected_files[run_end] == alias:
                        run_end += 1
                    selected += append_keys(
                        writer, selected_hashes.slice(run_start, run_end - run_start),
                        selected_companies.slice(run_start, run_end - run_start),
                        "wuzhen", canonical, selected_rows[run_start:run_end],
                    )
                    seen_files.add(canonical)
                    run_start = run_end
            rows += batch.num_rows
    expected = cfg.get("wuzhen_occurrence_rows")
    if expected is not None and rows != expected:
        raise ValueError("Wuzhen occurrence total differs from frozen receipt")
    return selected, {"occurrence_rows": rows, "occurrence_files": len(cfg["wuzhen_occurrence_files"]),
                      "selected_source_files": len(seen_files)}


def disposition_sql() -> str:
    return """
    SELECT k.REGION, k.SOURCE_FILE, k.SHARD_ID, k.SOURCE_ROW, k.JOB_HASH,
           CASE WHEN r.JOB_HASH IS NULL THEN 'record_unmatched'
                WHEN r.COUNTRY IS NULL OR trim(r.COUNTRY) = '' THEN 'matched_country_unknown'
                WHEN r.COUNTRY <> 'USA' THEN 'matched_non_usa'
                WHEN count(*) OVER (PARTITION BY k.JOB_HASH) > 1
                     THEN 'matched_usa_duplicate_quarantine'
                ELSE 'matched_usa_canonical' END AS MATCH_DISPOSITION,
           CAST(r.RECORD_SOURCE_ROW AS BIGINT) AS RECORD_SOURCE_ROW,
           r.CREATED, r.COUNTRY, r.STATE,
           CAST(count(*) OVER (PARTITION BY k.JOB_HASH) AS INTEGER) AS GLOBAL_KEY_OCCURRENCES,
           k.DESCRIPTION_COMPANY_ID, r.COMPANY_ID AS RECORD_COMPANY_ID,
           CASE WHEN k.DESCRIPTION_COMPANY_ID IS NULL OR r.COMPANY_ID IS NULL THEN NULL
                ELSE k.DESCRIPTION_COMPANY_ID = r.COMPANY_ID END AS COMPANY_ID_MATCH
    FROM keys k LEFT JOIN records r USING (JOB_HASH)
    """


def write_fragment_stream(connection, sql: str, root: Path, prefix: str) -> tuple[int, dict, list]:
    reader = connection.execute(sql + " ORDER BY REGION, SOURCE_FILE, SOURCE_ROW").fetch_record_batch(65536)
    current = None
    writer = None
    temp = final = None
    total = 0
    disposition_counts = Counter()
    fragments = []
    try:
        for batch in reader:
            table = pa.Table.from_batches([batch])
            keys = list(zip(table["REGION"].to_pylist(), table["SOURCE_FILE"].to_pylist()))
            start = 0
            while start < table.num_rows:
                key = keys[start]
                end = start + 1
                while end < table.num_rows and keys[end] == key:
                    end += 1
                if key != current:
                    if writer:
                        writer.close(); os.replace(temp, final)
                        fragments.append({"path": str(final), "bytes": final.stat().st_size,
                                          "rows": pq.ParquetFile(final).metadata.num_rows,
                                          "sha256": sha256(final)})
                    current = key
                    sid = shard_id(*key)
                    final = root / key[0] / sid / ("prefix_%s.parquet" % prefix)
                    final.parent.mkdir(parents=True, exist_ok=True)
                    if final.exists() or Path(str(final) + ".tmp").exists():
                        raise FileExistsError(str(final))
                    temp = Path(str(final) + ".tmp")
                    writer = pq.ParquetWriter(temp, SIDECAR_SCHEMA, compression="zstd")
                part = table.slice(start, end - start)
                normalized = part.select(SIDECAR_SCHEMA.names).cast(SIDECAR_SCHEMA)
                writer.write_table(normalized)
                disposition_counts.update(part["MATCH_DISPOSITION"].to_pylist())
                total += part.num_rows
                start = end
        if writer:
            writer.close(); writer = None; os.replace(temp, final)
            fragments.append({"path": str(final), "bytes": final.stat().st_size,
                              "rows": pq.ParquetFile(final).metadata.num_rows,
                              "sha256": sha256(final)})
    finally:
        if writer:
            writer.close()
    return total, dict(sorted(disposition_counts.items())), fragments


def process_prefix(cfg: dict, prefix: str) -> dict:
    if prefix not in PREFIXES or len(prefix) != 1:
        raise ValueError("prefix must be one lowercase hex character")
    root = Path(cfg["output_root"]); scratch = Path(cfg["scratch_root"])
    receipt_path = root / "prefix_receipts" / ("prefix_%s.json" % prefix)
    existing = verified_prefix_receipt(receipt_path, cfg)
    if existing is not None:
        return existing
    scratch.mkdir(parents=True, exist_ok=True)
    free_reserve = int(cfg.get("free_reserve_bytes", 8_000_000_000))
    if shutil.disk_usage(scratch).free < free_reserve:
        raise RuntimeError("free-space reserve would be violated")
    attempt_id = "%s.%s" % (os.environ.get("SLURM_JOB_ID") or "local", os.getpid())
    attempt_root = root / "prefix_attempts" / ("prefix_%s.%s" % (prefix, attempt_id))
    attempt_root.mkdir(parents=True, exist_ok=False)
    key_final = scratch / ("prefix_%s.%s.keys.parquet" % (prefix, attempt_id))
    key_temp = Path(str(key_final) + ".tmp")
    if key_final.exists() or key_temp.exists():
        raise FileExistsError(str(key_final))
    _, aliases = load_inventory(cfg["source_inventories"])
    writer = pq.ParquetWriter(key_temp, KEY_SCHEMA, compression="zstd")
    try:
        ks_rows, ks_meta = stage_kunshan_prefix(cfg, prefix, writer)
        wz_rows, wz_meta = stage_wuzhen_prefix(cfg, prefix, writer, aliases)
        writer.close(); writer = None; os.replace(key_temp, key_final)
    finally:
        if writer:
            writer.close()
    if key_final.stat().st_size > int(cfg.get("max_prefix_key_bytes", 1_000_000_000)):
        raise RuntimeError("prefix key staging cap exceeded")
    connection = duckdb.connect()
    threads = int(cfg.get("duckdb_threads", 16))
    memory_limit = str(cfg.get("duckdb_memory_limit", "72GB"))
    if threads < 1 or not re.fullmatch(r"[1-9][0-9]*(?:MB|GB)", memory_limit):
        raise ValueError("invalid DuckDB resource limits")
    connection.execute("SET threads=%d" % threads)
    connection.execute("SET memory_limit='%s'" % memory_limit)
    temp_dir = str(Path(cfg["duckdb_temp_dir"]) / ("prefix_" + prefix))
    Path(temp_dir).mkdir(parents=True, exist_ok=True)
    connection.execute("SET temp_directory=" + sql_literal(temp_dir))
    records_glob = str(Path(cfg["records_index"]) / ("hash_prefix=" + prefix) / "*.parquet")
    connection.execute("CREATE VIEW keys AS SELECT * FROM read_parquet(%s)" % sql_literal(str(key_final)))
    connection.execute("CREATE VIEW records AS SELECT JOB_HASH,COMPANY_ID,COUNTRY,STATE,CREATED,RECORD_SOURCE_ROW FROM read_parquet(%s)" % sql_literal(records_glob))
    duplicate_record_keys = connection.execute(
        "SELECT count(*) FROM (SELECT JOB_HASH FROM records GROUP BY JOB_HASH HAVING count(*) <> 1)"
    ).fetchone()[0]
    if duplicate_record_keys:
        raise RuntimeError("Records index contains duplicate keys for prefix %s" % prefix)
    sql = disposition_sql()
    summary_rows = connection.execute(
        "SELECT MATCH_DISPOSITION,count(*) FROM (" + sql + ") GROUP BY MATCH_DISPOSITION"
    ).fetchall()
    summary = dict(summary_rows)
    duplicate_keys = connection.execute(
        "SELECT count(*) FROM (SELECT JOB_HASH FROM keys GROUP BY JOB_HASH HAVING count(*) > 1)"
    ).fetchone()[0]
    rows, streamed_counts, fragments = write_fragment_stream(
        connection, sql, attempt_root / "fragments", prefix)
    connection.close()
    if summary != streamed_counts or rows != ks_rows + wz_rows:
        raise RuntimeError("prefix disposition conservation failure")
    if sum(item["bytes"] for item in fragments) > int(cfg.get("max_prefix_fragment_bytes", 5_000_000_000)):
        raise RuntimeError("prefix fragment cap exceeded")
    key_final.unlink()
    published_root = root / "prefix_fragments" / ("prefix_" + prefix)
    published_root.parent.mkdir(parents=True, exist_ok=True)
    if published_root.exists():
        raise FileExistsError(str(published_root))
    os.replace(attempt_root / "fragments", published_root)
    published_fragments = []
    for item in fragments:
        source = Path(item["path"])
        relative = source.relative_to(attempt_root / "fragments")
        published = dict(item); published["path"] = str(published_root / relative)
        published_fragments.append(published)
    receipt = {
        "status": "complete", "prefix": prefix,
        "prefix_contract": "JOB_HASH first lowercase hexadecimal character; no rehash",
        "kunshan_rows": ks_rows, "wuzhen_rows": wz_rows, "occurrence_rows": rows,
        "global_duplicate_keys": duplicate_keys,
        "disposition_counts": summary, "row_conservation": sum(summary.values()) == rows,
        "records_duplicate_keys": duplicate_record_keys,
        "fragment_files": published_fragments,
        "fragment_rows": sum(x["rows"] for x in published_fragments),
        "kunshan_projection": ks_meta, "wuzhen_occurrences": wz_meta,
        "config_sha256": cfg["_config_sha256"], "script_sha256": cfg["_script_sha256"],
    }
    atomic_json(receipt_path, receipt)
    return receipt


def consolidate_shard(cfg: dict, region: str, source_file: str) -> dict:
    sources, _ = load_inventory(cfg["source_inventories"])
    source = sources[(region, source_file)]
    sid = source["shard_id"]
    output = Path(cfg["sidecar_root"]) / region / (sid + ".parquet")
    receipt_path = output.with_suffix(".complete.json")
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if (receipt.get("status") == "complete" and output.is_file()
                and receipt.get("sidecar_sha256") == sha256(output)):
            return receipt
        raise RuntimeError("existing sidecar receipt failed validation")
    fragment_root = Path(cfg["output_root"]) / "prefix_fragments"
    fragments = sorted(fragment_root.glob("prefix_?/%s/%s/prefix_?.parquet" % (region, sid)))
    if not fragments:
        raise FileNotFoundError("no fragments for " + source_file)
    table = pq.read_table(fragments, schema=SIDECAR_SCHEMA)
    order = pc.sort_indices(table, sort_keys=[("SOURCE_ROW", "ascending")])
    table = pc.take(table, order)
    rows = table["SOURCE_ROW"].to_pylist()
    expected_rows_path = Path(cfg["expected_source_rows"])
    expected_rows_document = json.loads(expected_rows_path.read_text())
    expected_lookup = {(x["region"], x["source_file"]): x["raw_rows"]
                       for x in expected_rows_document["sources"]}
    expected_rows = expected_lookup.get((region, source_file))
    if expected_rows is None:
        raise ValueError("source absent from expected-row receipt")
    if len(rows) != expected_rows or rows != list(range(expected_rows)):
        raise RuntimeError("SOURCE_ROW is not complete/unique for " + source_file)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise FileExistsError(str(output))
    temp = Path(str(output) + ".tmp")
    pq.write_table(table, temp, compression="zstd", row_group_size=8192)
    os.replace(temp, output)
    counts = Counter(table["MATCH_DISPOSITION"].to_pylist())
    if set(counts) - DISPOSITIONS:
        raise RuntimeError("unknown disposition in consolidated sidecar")
    receipt = {
        "status": "complete", "shard_id": sid, "region": region,
        "source_file": source_file, "raw_rows": table.num_rows,
        "disposition_counts": dict(sorted(counts.items())),
        "sidecar_path": str(output), "sidecar_bytes": output.stat().st_size,
        "sidecar_sha256": sha256(output), "fragment_count": len(fragments),
        "source_path": source["source_path"], "source_bytes": source["source_bytes"],
        "source_sha256_cached": source["source_sha256_cached"],
    }
    atomic_json(receipt_path, receipt)
    if cfg.get("delete_fragments_after_sidecar_seal", False):
        for fragment in fragments:
            fragment.unlink()
        receipt["generated_fragments_deleted_after_sidecar_seal"] = True
        atomic_json(receipt_path, receipt)
    return receipt


def finalize(cfg: dict) -> dict:
    sources, _ = load_inventory(cfg["source_inventories"])
    sidecar_root = Path(cfg["sidecar_root"])
    receipts = []
    for (region, source_file), source in sorted(sources.items()):
        path = sidecar_root / region / (source["shard_id"] + ".complete.json")
        receipt = json.loads(path.read_text())
        sidecar = Path(receipt["sidecar_path"])
        if (receipt.get("status") != "complete" or receipt["source_file"] != source_file
                or receipt["sidecar_sha256"] != sha256(sidecar)):
            raise RuntimeError("invalid sidecar receipt: " + source_file)
        receipts.append(receipt)
    plan = Path(cfg["runner_plan"])
    plan.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(plan) + ".tmp")
    with temp.open("w") as stream:
        for receipt in receipts:
            stream.write(json.dumps({key: receipt[key] for key in (
                "shard_id", "region", "source_path", "source_file", "source_bytes",
                "source_sha256_cached", "raw_rows", "sidecar_path", "sidecar_bytes",
                "sidecar_sha256")}, sort_keys=True) + "\n")
    os.replace(temp, plan)
    totals = Counter()
    for receipt in receipts:
        totals.update(receipt["disposition_counts"])
    prefix_receipts = [json.loads((Path(cfg["output_root"]) / "prefix_receipts" /
                                  ("prefix_%s.json" % prefix)).read_text()) for prefix in PREFIXES]
    prefix_totals = Counter()
    for receipt in prefix_receipts:
        prefix_totals.update(receipt["disposition_counts"])
    if totals != prefix_totals:
        raise RuntimeError("prefix/sidecar global disposition totals differ")
    expected_regions = cfg["expected_region_rows"]
    observed_regions = Counter()
    for receipt in receipts:
        observed_regions[receipt["region"]] += receipt["raw_rows"]
    if dict(observed_regions) != expected_regions:
        raise RuntimeError("regional raw-row totals differ from frozen receipts")
    result = {
        "status": "complete", "planned_shards": len(receipts),
        "raw_occurrences": sum(totals.values()), "region_rows": dict(sorted(observed_regions.items())),
        "disposition_counts": dict(sorted(totals.items())),
        "global_duplicate_keys": sum(x["global_duplicate_keys"] for x in prefix_receipts),
        "ambiguous_duplicate_policy": "all matched-USA occurrences quarantined; no canonical body chosen",
        "runner_plan": str(plan), "runner_plan_sha256": sha256(plan),
    }
    atomic_json(plan.with_suffix(".complete.json"), result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["prefix", "consolidate-shard", "finalize"])
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--prefix")
    parser.add_argument("--region")
    parser.add_argument("--source-file")
    args = parser.parse_args(); cfg = load_config(args.config)
    cfg["_config_sha256"] = sha256(args.config)
    cfg["_script_sha256"] = sha256(Path(__file__).resolve())
    if args.mode == "prefix":
        result = process_prefix(cfg, args.prefix)
    elif args.mode == "consolidate-shard":
        result = consolidate_shard(cfg, args.region, args.source_file)
    else:
        result = finalize(cfg)
    print(json.dumps(result, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
