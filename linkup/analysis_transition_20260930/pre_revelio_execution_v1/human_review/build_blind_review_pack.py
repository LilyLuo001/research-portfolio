#!/usr/bin/env python3
"""Create a blind review pack without loading the full corpus text.

Phase 1 streams a verified, key-only full-frame index repeatedly to count and
select deterministic hash-ranked keys. Phase 2 accepts text only for those
selected keys (at most 40), which an existing source locator must extract.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import heapq
import html
import json
import math
import os
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Optional

import pyarrow.dataset as ds
import pyarrow as pa

SEED = "20261003"
INDEX_FIELDS = {"private_key", "sampling_stratum", "first_observation_stratum",
                "occupation_availability_stratum", "challenge_eligible", "challenge_stratum"}
TEXT_FIELDS = {"private_key", "original_text"}
FORBIDDEN_INDEX_FIELDS = {"extractor_prediction", "extractor_evidence_span",
                          "model_judgment", "aggregate_result", "original_text"}
PARQUET_FIELDS = {"JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW", "CREATED", "usable",
                  "tech_generative_ai_use_explicit", "tech_generative_ai_develop_explicit",
                  "tech_traditional_software_use_explicit", "tech_traditional_software_develop_explicit",
                  "tech_generative_ai_detected", "tech_predictive_ai_detected", "tech_unspecified_ai_detected",
                  "exp_specific_tool_main", "exp_industry_domain_main", "exp_general_work_main",
                  "exp_specific_tool_broad", "exp_industry_domain_broad", "exp_general_work_broad",
                  "exp_specific_tool_exact_or_unspecified", "exp_industry_domain_exact_or_unspecified", "exp_general_work_exact_or_unspecified"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def frame_fingerprint(path: Path) -> str:
    """Fingerprint a Parquet file/directory by metadata, without rereading payloads."""
    if path.is_file():
        return sha256(path)
    inventory = [(str(item.relative_to(path)), item.stat().st_size, item.stat().st_mtime_ns)
                 for item in sorted(path.rglob("*.parquet"))]
    if not inventory:
        raise ValueError("Parquet input directory contains no parquet files")
    return hashlib.sha256(json.dumps(inventory, separators=(",", ":")).encode()).hexdigest()


def main_narrow_parquet_files(path: Path) -> list[str]:
    """Explicitly exclude duration sidecars from the 2,464-shard review frame."""
    if path.is_file():
        if path.name.endswith(".durations.parquet"):
            raise ValueError("duration sidecar cannot be the review frame")
        return [str(path)]
    files = [item for item in path.rglob("*.parquet") if not item.name.endswith(".durations.parquet")]
    if not files:
        raise ValueError("full narrow directory has no main parquet files")
    return [str(item) for item in sorted(files)]


def stable_rank(phase: str, key: str) -> str:
    return hashlib.sha256(f"{SEED}|{phase}|{key}".encode()).hexdigest()


def truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def allocate_proportional(sizes: dict[str, int], total: int) -> dict[str, int]:
    active = {key: value for key, value in sizes.items() if value > 0}
    if not active or total <= 0:
        return {key: 0 for key in active}
    total = min(total, sum(active.values()))
    if len(active) > total:
        raise ValueError(f"{len(active)} nonempty strata exceed sample slots {total}; freeze a coarser sampling_stratum")
    allocation = {key: 1 for key in active}
    remaining = total - len(active)
    weight = sum(active.values())
    quotas = {key: remaining * active[key] / weight for key in active}
    for key in active:
        allocation[key] += min(active[key] - 1, math.floor(quotas[key]))
    left = total - sum(allocation.values())
    order = sorted(active, key=lambda key: (-(quotas[key] - math.floor(quotas[key])), stable_rank("allocation", key)))
    while left:
        progressed = False
        for key in order:
            if allocation[key] < active[key] and left:
                allocation[key] += 1
                left -= 1
                progressed = True
        if not progressed:
            raise RuntimeError("allocation capacity exhausted")
    return allocation


def read_metadata(path: Path, label: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{label} metadata must be a JSON object")
    for field in ("key_namespace", "stable_key_type", "source_provenance"):
        if not isinstance(payload.get(field), str) or not payload[field].strip():
            raise ValueError(f"{label} metadata requires nonblank string {field}")
    if payload["stable_key_type"] != "string":
        raise ValueError(f"{label} stable_key_type must be string")
    return payload


def read_key_manifest(path: Path, label: str, exact_count: int | None = None) -> tuple[set[str], dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("private_keys"), list):
        raise ValueError("heldout manifest must be a JSON object containing private_keys")
    metadata = read_metadata(path, label)
    values = payload["private_keys"]
    if (exact_count is not None and len(values) != exact_count) or any(not isinstance(value, str) or not value for value in values) or len(set(values)) != len(values):
        expectation = f"exactly {exact_count}" if exact_count is not None else "unique"
        raise ValueError(f"{label} manifest must contain {expectation} nonblank private_keys")
    return set(values), metadata


def derived_parquet_row(values: dict[str, list], position: int) -> dict[str, str]:
    get = lambda name: values[name][position]
    key_parts = [get(name) for name in ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")]
    if any(part is None for part in key_parts):
        raise ValueError("Parquet input has nullable canonical key")
    enabled = lambda name: bool(get(name))
    any_ai = any(enabled(name) for name in ("tech_generative_ai_detected", "tech_predictive_ai_detected", "tech_unspecified_ai_detected"))
    if enabled("tech_generative_ai_use_explicit"):
        tech = "genAI-use"
    elif enabled("tech_generative_ai_develop_explicit"):
        tech = "genAI-develop"
    elif enabled("tech_traditional_software_use_explicit") and not any_ai:
        tech = "software-use-no-AI"
    elif enabled("tech_traditional_software_develop_explicit") and not any_ai:
        tech = "software-develop-no-AI"
    else:
        tech = "other"
    if enabled("exp_specific_tool_main"):
        experience = "specific_tool"
    elif enabled("exp_industry_domain_main"):
        experience = "industry_domain"
    elif enabled("exp_general_work_main"):
        experience = "general_work"
    else:
        experience = "none"
    broad_without_explicit = any(enabled("exp_%s_broad" % name) and not enabled("exp_%s_main" % name) for name in ("specific_tool", "industry_domain", "general_work"))
    exact_or_unspecified = any(enabled("exp_%s_exact_or_unspecified" % name) for name in ("specific_tool", "industry_domain", "general_work"))
    challenge = "binding_broad_not_explicit" if broad_without_explicit else "exact_or_unspecified_duration" if exact_or_unspecified else ""
    created = get("CREATED")
    return {"private_key": json.dumps(key_parts, ensure_ascii=False, separators=(",", ":")),
            "sampling_stratum": tech + "|" + experience,
            "first_observation_stratum": str(created.year) if created is not None else "unknown",
            "occupation_availability_stratum": "unknown",
            "challenge_eligible": str(bool(challenge)).lower(), "challenge_stratum": challenge}


def duplicate_database(parquet_path: Path, private_dir: Path) -> tuple[sqlite3.Connection, int]:
    """Keep the global duplicate exclusion list on private disk, never in RAM."""
    database = private_dir / "duplicate_job_hashes.sqlite"
    database.unlink(missing_ok=True)
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE duplicate_hashes (JOB_HASH TEXT PRIMARY KEY)")
    dataset = ds.dataset(parquet_path, format="parquet")
    if "JOB_HASH" not in dataset.schema.names:
        raise ValueError("duplicate Parquet input requires JOB_HASH")
    count = 0
    for batch in dataset.scanner(columns=["JOB_HASH"], batch_size=65536).to_batches():
        hashes = [(value,) for value in batch.column(0).to_pylist()]
        if any(value[0] is None for value in hashes):
            raise ValueError("duplicate JOB_HASH list contains null")
        connection.executemany("INSERT OR IGNORE INTO duplicate_hashes VALUES (?)", hashes)
        count += len(hashes)
    connection.commit()
    return connection, connection.execute("SELECT count(*) FROM duplicate_hashes").fetchone()[0]


def index_rows(args, duplicate_connection: Optional[sqlite3.Connection] = None):
    if args.frame_parquet:
        dataset = ds.dataset(args.frame_parquet, format="parquet")
        missing = PARQUET_FIELDS - set(dataset.schema.names)
        if missing:
            raise ValueError(f"Parquet join input missing fields: {sorted(missing)}")
        for batch in dataset.scanner(columns=sorted(PARQUET_FIELDS), batch_size=65536).to_batches():
            values = batch.to_pydict()
            duplicate_hashes = set()
            if duplicate_connection:
                hashes = [value for value in values["JOB_HASH"] if value is not None]
                for start in range(0, len(hashes), 900):
                    chunk = hashes[start:start + 900]
                    placeholders = ",".join("?" for _ in chunk)
                    duplicate_hashes.update(value[0] for value in duplicate_connection.execute(f"SELECT JOB_HASH FROM duplicate_hashes WHERE JOB_HASH IN ({placeholders})", chunk))
            for position in range(batch.num_rows):
                if not values["usable"][position] or values["JOB_HASH"][position] in duplicate_hashes:
                    continue
                yield derived_parquet_row(values, position)
        return
    with args.frame_index.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or ())
        missing = INDEX_FIELDS - fields
        if missing:
            raise ValueError(f"index missing fields: {sorted(missing)}")
        forbidden = FORBIDDEN_INDEX_FIELDS & fields
        if forbidden:
            raise ValueError(f"index must be key-only, without text/predictions: {sorted(forbidden)}")
        yield from reader


def stream_top(args, exclusions: set[str], allocation: dict[str, int], phase: str, duplicate_connection,
               predicate) -> dict[str, list[dict[str, str]]]:
    """Bounded heap: retains at most the final sample size, never full rows/text."""
    heaps: dict[str, list[tuple[str, str, dict[str, str]]]] = defaultdict(list)
    for row in index_rows(args, duplicate_connection):
        key = row["private_key"]
        stratum = row["sampling_stratum"] if phase == "core" else row["challenge_stratum"]
        if not key or not stratum or key in exclusions or stratum not in allocation or not predicate(row):
            continue
        rank = stable_rank(phase, key)
        # reverse rank makes heap root the worst (largest) retained SHA-256 rank
        inverted = "".join(chr(255 - ord(character)) for character in rank)
        item = (inverted, key, dict(row))
        heap = heaps[stratum]
        if len(heap) < allocation[stratum]:
            heapq.heappush(heap, item)
        elif item[0] > heap[0][0]:
            heapq.heapreplace(heap, item)
    return {stratum: [item[2] for item in sorted(heap, key=lambda item: stable_rank(phase, item[1]))]
            for stratum, heap in heaps.items()}


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_selection_manifest(private_dir: Path, selection: dict) -> None:
    """Both CSV and Parquet selection paths publish the same private manifest."""
    path = private_dir / "selected_key_manifest.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(selection, indent=2) + "\n", encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def select_parquet_fast(args, metadata: dict, exclusions: set[str], private_dir: Path) -> dict:
    """One Arrow scan; DuckDB ranks bounded candidates independently per batch."""
    try:
        import duckdb
    except ImportError as error:
        raise RuntimeError("Parquet fast path requires the existing execution DuckDB runtime") from error
    if not args.duplicate_job_hash_parquet:
        raise ValueError("full Parquet frame requires --duplicate-job-hash-parquet")
    expected = metadata.get("verified_full_frame_rows")
    if not isinstance(expected, int) or expected < 32:
        raise ValueError("frame metadata requires verified_full_frame_rows >= 32")
    con = duckdb.connect()
    con.execute("CREATE TEMP TABLE excluded_keys(private_key VARCHAR PRIMARY KEY)")
    con.executemany("INSERT INTO excluded_keys VALUES (?)", [(key,) for key in exclusions])
    frame_path, duplicate_path = Path(args.frame_parquet), Path(args.duplicate_job_hash_parquet)
    quote = lambda value: "'" + value.replace("'", "''") + "'"
    frame_files = main_narrow_parquet_files(frame_path)
    duplicate_glob = str(duplicate_path) if duplicate_path.is_file() else str(duplicate_path / "**" / "*.parquet")
    con.execute(f"CREATE TEMP TABLE duplicate_hashes AS SELECT DISTINCT JOB_HASH FROM read_parquet({quote(duplicate_glob)}, union_by_name=true)")
    key = 'concat(\'["\',JOB_HASH,\'","\',SOURCE_FILE,\'",\',SOURCE_ROW,\',\',RECORD_SOURCE_ROW,\']\')'
    tech = "CASE WHEN tech_generative_ai_use_explicit THEN 'genAI-use' WHEN tech_generative_ai_develop_explicit THEN 'genAI-develop' WHEN tech_traditional_software_use_explicit AND NOT (tech_generative_ai_detected OR tech_predictive_ai_detected OR tech_unspecified_ai_detected) THEN 'software-use-no-AI' WHEN tech_traditional_software_develop_explicit AND NOT (tech_generative_ai_detected OR tech_predictive_ai_detected OR tech_unspecified_ai_detected) THEN 'software-develop-no-AI' ELSE 'other' END"
    experience = "CASE WHEN exp_specific_tool_main THEN 'specific_tool' WHEN exp_industry_domain_main THEN 'industry_domain' WHEN exp_general_work_main THEN 'general_work' ELSE 'none' END"
    broad = "(exp_specific_tool_broad AND NOT exp_specific_tool_main) OR (exp_industry_domain_broad AND NOT exp_industry_domain_main) OR (exp_general_work_broad AND NOT exp_general_work_main)"
    exact = "exp_specific_tool_exact_or_unspecified OR exp_industry_domain_exact_or_unspecified OR exp_general_work_exact_or_unspecified"
    prepared = f"""SELECT {key} private_key, ({tech}) || '|' || ({experience}) sampling_stratum,
      coalesce(cast(year(CREATED) AS VARCHAR),'unknown') first_observation_stratum, 'unknown' occupation_availability_stratum,
      CASE WHEN {broad} THEN 'binding_broad_not_explicit' WHEN {exact} THEN 'exact_or_unspecified_duration' ELSE NULL END challenge_stratum,
      e.private_key IS NOT NULL is_excluded
      FROM batch_input n ANTI JOIN duplicate_hashes d USING (JOB_HASH)
      LEFT JOIN excluded_keys e ON {key}=e.private_key WHERE usable"""
    dataset = ds.dataset(frame_files, format="parquet")
    missing = PARQUET_FIELDS - set(dataset.schema.names)
    if missing:
        raise ValueError(f"Parquet narrow input missing fields: {sorted(missing)}")
    core_sizes, challenge_sizes, core_heaps, challenge_heaps = defaultdict(int), defaultdict(int), defaultdict(list), defaultdict(list)
    frame_rows = excluded_rows = 0
    def merge(heap, phase, limit, row):
        rank = stable_rank(phase, row["private_key"]); item = ("".join(chr(255 - ord(c)) for c in rank), row["private_key"], row)
        if len(heap) < limit: heapq.heappush(heap, item)
        elif item[0] > heap[0][0]: heapq.heapreplace(heap, item)
    def candidate_row(key_value, stratum, first, occupation, challenge):
        # Match CSV DictReader's string-only canonical frame exactly.
        return {"private_key": key_value, "sampling_stratum": stratum,
                "first_observation_stratum": first, "occupation_availability_stratum": occupation,
                "challenge_eligible": str(challenge is not None).lower(),
                "challenge_stratum": challenge or ""}
    for batch in dataset.scanner(columns=sorted(PARQUET_FIELDS), batch_size=65536).to_batches():
        con.register("batch_input", pa.Table.from_batches([batch]))
        counts = con.execute(f"SELECT sampling_stratum, count(*) frame_n, count(*) FILTER (WHERE NOT is_excluded) active_n, count(*) FILTER (WHERE is_excluded) excluded_n FROM ({prepared}) GROUP BY sampling_stratum").fetchall()
        for stratum, size, active, excluded in counts:
            frame_rows += size; excluded_rows += excluded; core_sizes[stratum] += active
        challenges = con.execute(f"SELECT challenge_stratum, count(*) FROM ({prepared}) WHERE NOT is_excluded AND challenge_stratum IS NOT NULL GROUP BY challenge_stratum").fetchall()
        for stratum, size in challenges: challenge_sizes[stratum] += size
        core_candidates = con.execute(f"SELECT private_key,sampling_stratum,first_observation_stratum,occupation_availability_stratum,challenge_stratum FROM (SELECT *, row_number() OVER (PARTITION BY sampling_stratum ORDER BY sha256('{SEED}|core|' || private_key)) rn FROM ({prepared}) WHERE NOT is_excluded) WHERE rn<=32").fetchall()
        for key_value, stratum, first, occupation, challenge in core_candidates:
            merge(core_heaps[stratum], "core", 32, candidate_row(key_value, stratum, first, occupation, challenge))
        challenge_candidates = con.execute(f"SELECT private_key,sampling_stratum,first_observation_stratum,occupation_availability_stratum,challenge_stratum FROM (SELECT *, row_number() OVER (PARTITION BY challenge_stratum ORDER BY sha256('{SEED}|challenge|' || private_key)) rn FROM ({prepared}) WHERE NOT is_excluded AND challenge_stratum IS NOT NULL) WHERE rn<=40").fetchall()
        for key_value, stratum, first, occupation, challenge in challenge_candidates:
            merge(challenge_heaps[challenge], "challenge", 40, candidate_row(key_value, stratum, first, occupation, challenge))
        con.unregister("batch_input")
    duplicate_count = con.execute("SELECT count(*) FROM duplicate_hashes").fetchone()[0]
    con.close()
    if frame_rows != expected:
        raise ValueError(f"DuckDB review frame rows {frame_rows} differ from verified_full_frame_rows {expected}")
    core_alloc = allocate_proportional(core_sizes, args.core_n)
    core = []
    for stratum, heap in core_heaps.items():
        for _, _, candidate in sorted(heap, key=lambda item: stable_rank("core", item[1]))[:core_alloc.get(stratum, 0)]:
            candidate.update(selection_stratum=stratum, sampling_probability=core_alloc[stratum] / core_sizes[stratum], core_or_challenge="core")
            core.append(candidate)
    if len(core) != args.core_n:
        raise RuntimeError(f"expected {args.core_n} core rows, got {len(core)}")
    core_keys = {row["private_key"] for row in core}
    core_challenge = {row["private_key"]: row["challenge_stratum"] for row in core}
    challenge_sizes = {stratum: size - sum(value == stratum for value in core_challenge.values()) for stratum, size in challenge_sizes.items()}
    challenge_sizes = {key: value for key, value in challenge_sizes.items() if value > 0}
    challenge_alloc = allocate_proportional(challenge_sizes, min(args.challenge_n, sum(challenge_sizes.values())))
    challenge = []
    for stratum, heap in challenge_heaps.items():
        candidates = [dict(item[2]) for item in sorted(heap, key=lambda item: stable_rank("challenge", item[1])) if item[1] not in core_keys]
        for candidate in candidates[:challenge_alloc.get(stratum, 0)]:
            candidate.update(selection_stratum=stratum, sampling_probability=challenge_alloc[stratum] / challenge_sizes[stratum], core_or_challenge="challenge")
            challenge.append(candidate)
    if len(challenge) != sum(challenge_alloc.values()):
        raise RuntimeError("bounded challenge candidates did not cover the fixed allocation")
    selected = sorted(core + challenge, key=lambda row: stable_rank("pack_order", row["private_key"]))
    return {"seed": SEED, "frame_input": str(args.frame_parquet), "selected": selected, "core_sizes": dict(core_sizes), "core_alloc": core_alloc,
            "challenge_sizes": challenge_sizes, "challenge_alloc": challenge_alloc, "frame_rows": frame_rows, "heldout_matches_excluded": excluded_rows,
            "global_duplicate_job_hashes_excluded": duplicate_count}


def write_html_preview(path: Path, reviewer_rows: list[dict]) -> None:
    """Private, inert local preview: source text is escaped rather than rendered."""
    sections = []
    for row in reviewer_rows:
        sections.append(
            "<section><h2>" + html.escape(row["anonymous_review_id"]) + "</h2>"
            "<p><b>Core/challenge:</b> " + html.escape(str(row["core_or_challenge"])) + "</p>"
            "<pre>" + html.escape(row["original_text"]) + "</pre>"
            "<p>Complete the corresponding CSV row; predictions and private keys are unavailable here.</p></section>"
        )
    document = "<!doctype html><meta charset=\"utf-8\"><title>Blind human review pack</title><style>body{font-family:system-ui;max-width:960px;margin:2rem auto}section{border-top:1px solid #bbb;padding:1rem 0}pre{white-space:pre-wrap;font:14px/1.45 ui-monospace,monospace}</style><h1>Blind human review pack</h1>" + "\n".join(sections)
    path.write_text(document, encoding="utf-8")


def write_reviewer_instructions(path: Path) -> None:
    path.write_text("""# 人工盲审说明

请只依据每条原文填写 CSV 中的 `human_` 字段。先独立完成初审；不要查看答案键或推测模型判断。

- 经验：是否明确出现、对象、required/preferred、是否与对象明确绑定。
- 年限：仅填写原文明确绑定的最小/最大值和单位；无法判断请标记并简述原因。
- 技术和角色：仅按原文填写；引用最短必要证据片段。
- 不足以判断时填写 `human_insufficient_text` 或不确定说明，不要猜测。

带 `dual_review_required=true` 的核心条目须由两名人分别独立填写。挑战条目用于诊断，不计入总体准确率。所有文本、键和答案均留在本地私有目录。
""", encoding="utf-8")


def select(args, metadata: dict, exclusions: set[str], private_dir: Path) -> dict:
    if metadata.get("verified_unique_private_keys") is not True:
        raise ValueError("frame metadata must attest verified_unique_private_keys: true")
    expected = metadata.get("verified_full_frame_rows")
    if not isinstance(expected, int) or expected < 32:
        raise ValueError("frame metadata requires verified_full_frame_rows >= 32")
    receipts = metadata.get("source_receipts")
    if not isinstance(receipts, list) or not receipts or not all(isinstance(value, str) and value for value in receipts):
        raise ValueError("frame metadata requires nonempty source_receipts")
    if args.frame_parquet:
        selection = select_parquet_fast(args, metadata, exclusions, private_dir)
        write_selection_manifest(private_dir, selection)
        return selection
    duplicate_connection, duplicate_count = (None, 0)
    core_sizes: dict[str, int] = defaultdict(int)
    frame_rows = excluded = 0
    for row in index_rows(args, duplicate_connection):
        frame_rows += 1
        key, stratum = row["private_key"], row["sampling_stratum"].strip()
        if not key or not stratum:
            raise ValueError("index has blank private_key or sampling_stratum")
        if key in exclusions:
            excluded += 1
        else:
            core_sizes[stratum] += 1
    if frame_rows != expected:
        raise ValueError(f"streamed frame rows {frame_rows} differ from verified_full_frame_rows {expected}")
    core_alloc = allocate_proportional(dict(core_sizes), args.core_n)
    core = []
    for stratum, rows in stream_top(args, exclusions, core_alloc, "core", duplicate_connection, lambda row: True).items():
        for row in rows:
            row.update(selection_stratum=stratum, sampling_probability=core_alloc[stratum] / core_sizes[stratum], core_or_challenge="core")
            core.append(row)
    if len(core) != args.core_n:
        raise RuntimeError(f"expected {args.core_n} core rows, got {len(core)}")
    core_keys = {row["private_key"] for row in core}
    challenge_sizes: dict[str, int] = defaultdict(int)
    for row in index_rows(args, duplicate_connection):
        if row["private_key"] in exclusions or row["private_key"] in core_keys or not truthy(row["challenge_eligible"]):
            continue
        stratum = row["challenge_stratum"].strip()
        if not stratum:
            raise ValueError("challenge-eligible row has blank challenge_stratum")
        challenge_sizes[stratum] += 1
    challenge_alloc = allocate_proportional(dict(challenge_sizes), min(args.challenge_n, sum(challenge_sizes.values())))
    challenge = []
    for stratum, rows in stream_top(args, exclusions | core_keys, challenge_alloc, "challenge", duplicate_connection, lambda row: truthy(row["challenge_eligible"])).items():
        for row in rows:
            row.update(selection_stratum=stratum, sampling_probability=challenge_alloc[stratum] / challenge_sizes[stratum], core_or_challenge="challenge")
            challenge.append(row)
    selected = sorted(core + challenge, key=lambda row: stable_rank("pack_order", row["private_key"]))
    if len(selected) > 40:
        raise RuntimeError("selection exceeds maximum 40")
    selection = {"seed": SEED, "frame_input": str(args.frame_parquet or args.frame_index), "selected": selected,
                 "core_sizes": dict(core_sizes), "core_alloc": core_alloc, "challenge_sizes": dict(challenge_sizes),
                 "challenge_alloc": challenge_alloc, "frame_rows": frame_rows, "heldout_matches_excluded": excluded,
                 "global_duplicate_job_hashes_excluded": duplicate_count}
    write_selection_manifest(private_dir, selection)
    if duplicate_connection:
        duplicate_connection.close()
    return selection


def materialize(args, selection: dict, private_dir: Path) -> int:
    wanted = {row["private_key"] for row in selection["selected"]}
    text_by_key: dict[str, str] = {}
    with args.selected_text.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = TEXT_FIELDS - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f"selected-text input missing fields: {sorted(missing)}")
        for row in reader:
            key = row["private_key"]
            if key not in wanted:
                raise ValueError("selected-text input contains a nonselected key")
            if key in text_by_key or not row["original_text"].strip():
                raise ValueError("selected-text input has duplicate key or blank text")
            text_by_key[key] = row["original_text"]
    if set(text_by_key) != wanted:
        raise ValueError("selected-text input must contain every selected key exactly once")
    schema = json.loads(args.reviewer_schema.read_text(encoding="utf-8"))
    visible, hidden = list(schema["initially_visible_columns"]), set(schema["hidden_until_human_lock"])
    if set(visible) & hidden:
        raise ValueError("reviewer schema exposes a hidden field")
    predictions = {}
    if args.predictions:
        with args.predictions.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if "private_key" not in (reader.fieldnames or ()):
                raise ValueError("prediction file requires private_key")
            for row in reader:
                if row["private_key"] in predictions:
                    raise ValueError("duplicate prediction private_key")
                predictions[row["private_key"]] = {key: value for key, value in row.items() if key != "private_key"}
    dual = {row["private_key"] for row in sorted((row for row in selection["selected"] if row["core_or_challenge"] == "core"), key=lambda row: stable_rank("dual_review", row["private_key"]))[:8]}
    reviewers, answers, assignments = [], [], []
    for row in selection["selected"]:
        key, anon = row["private_key"], "R" + stable_rank("anonymous", row["private_key"])[:12].upper()
        reviewer = {field: "" for field in visible}
        reviewer.update(anonymous_review_id=anon, original_text=text_by_key[key], first_observation_stratum=row["first_observation_stratum"], occupation_availability_stratum=row["occupation_availability_stratum"], core_or_challenge=row["core_or_challenge"], sampling_probability=row["sampling_probability"], review_round="initial_blind")
        reviewers.append(reviewer)
        answers.append({"anonymous_review_id": anon, "private_key": key, "core_or_challenge": row["core_or_challenge"], "selection_stratum": row["selection_stratum"], "model_predictions_json": json.dumps(predictions.get(key, {}), sort_keys=True)})
        for slot in (("A", "B") if key in dual else ("A",)):
            assignments.append({"anonymous_review_id": anon, "reviewer_slot": slot, "dual_review_required": str(key in dual).lower()})
    write_csv(private_dir / "reviewer_pack.csv", reviewers, visible)
    write_csv(private_dir / "private_answer_key.csv", answers, list(answers[0]))
    write_csv(private_dir / "review_assignments.csv", assignments, list(assignments[0]))
    write_html_preview(private_dir / "reviewer_pack_preview.html", reviewers)
    write_reviewer_instructions(private_dir / "REVIEW_INSTRUCTIONS_zh.md")
    for name in ("reviewer_pack.csv", "private_answer_key.csv", "review_assignments.csv", "reviewer_pack_preview.html", "REVIEW_INSTRUCTIONS_zh.md"):
        os.chmod(private_dir / name, 0o600)
    return len(dual)


def main() -> None:
    parser = argparse.ArgumentParser()
    frame = parser.add_mutually_exclusive_group(required=True)
    frame.add_argument("--frame-index", type=Path, help="small, key-only CSV compatibility input")
    frame.add_argument("--frame-parquet", type=Path, help="full joined Parquet file or partition directory")
    parser.add_argument("--duplicate-job-hash-parquet", type=Path,
                        help="private global duplicate JOB_HASH list; required with --frame-parquet")
    parser.add_argument("--frame-metadata", type=Path, required=True)
    parser.add_argument("--heldout-key-manifest", type=Path)
    parser.add_argument("--known-used-key-manifest", type=Path,
                        help="private key-only manifest of prior review cases")
    parser.add_argument("--allow-unverified-heldout-d18", action="store_true",
                        help="explicit D18 exception: diagnostic pack only when heldout-400 is unavailable")
    parser.add_argument("--reviewer-schema", type=Path, required=True)
    parser.add_argument("--selected-text", type=Path, help="existing locator output for selected keys only")
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--private-output-dir", type=Path, required=True)
    parser.add_argument("--public-receipt", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--core-n", type=int, default=32)
    parser.add_argument("--challenge-n", type=int, default=8)
    args = parser.parse_args()
    if args.core_n != 32 or not (0 <= args.challenge_n <= 8):
        raise ValueError("frozen design requires 32 core and at most 8 challenge ads")
    repo, private_dir = args.repo_root.resolve(), args.private_output_dir.resolve()
    if private_dir == repo or repo in private_dir.parents:
        raise ValueError("private output directory must be outside the repository")
    private_dir.mkdir(parents=True, exist_ok=True)
    os.chmod(private_dir, 0o700)
    metadata = read_metadata(args.frame_metadata, "frame")
    if bool(args.heldout_key_manifest) == bool(args.allow_unverified_heldout_d18):
        raise ValueError("provide heldout-400, or explicitly use --allow-unverified-heldout-d18, but not both")
    heldout_keys, heldout_metadata = set(), None
    if args.heldout_key_manifest:
        heldout_keys, heldout_metadata = read_key_manifest(args.heldout_key_manifest, "heldout", exact_count=400)
        if metadata["key_namespace"] != heldout_metadata["key_namespace"]:
            raise ValueError("frame and heldout key_namespace differ")
    known_used_keys, known_used_metadata = set(), None
    if args.known_used_key_manifest:
        known_used_keys, known_used_metadata = read_key_manifest(args.known_used_key_manifest, "known-used")
        if metadata["key_namespace"] != known_used_metadata["key_namespace"]:
            raise ValueError("frame and known-used key_namespace differ")
    if args.allow_unverified_heldout_d18 and not args.known_used_key_manifest:
        raise ValueError("D18 exception requires a private known-used key manifest")
    selection = select(args, metadata, heldout_keys | known_used_keys, private_dir)
    core_n = sum(row["core_or_challenge"] == "core" for row in selection["selected"])
    challenge_n = len(selection["selected"]) - core_n
    receipt = {"status": "blind_pack_keys_selected_pending_text" if not args.selected_text else "blind_pack_built", "seed": SEED,
      "inputs": {"frame_input_kind": "parquet" if args.frame_parquet else "csv_key_only", "frame_input_fingerprint": frame_fingerprint(args.frame_parquet or args.frame_index), "duplicate_job_hash_input_fingerprint": frame_fingerprint(args.duplicate_job_hash_parquet) if args.duplicate_job_hash_parquet else None, "frame_metadata_sha256": sha256(args.frame_metadata), "heldout_key_manifest_sha256": sha256(args.heldout_key_manifest) if args.heldout_key_manifest else None, "known_used_key_manifest_sha256": sha256(args.known_used_key_manifest) if args.known_used_key_manifest else None, "reviewer_schema_sha256": sha256(args.reviewer_schema), "selected_text_sha256": sha256(args.selected_text) if args.selected_text else None, "predictions_sha256": sha256(args.predictions) if args.predictions else None},
      "key_contract": {"key_namespace": metadata["key_namespace"], "stable_key_type": "string", "frame_source_provenance": metadata["source_provenance"], "source_receipts": metadata["source_receipts"], "heldout_source_provenance": heldout_metadata["source_provenance"] if heldout_metadata else None, "known_used_source_provenance": known_used_metadata["source_provenance"] if known_used_metadata else None},
      "counts": {"verified_full_frame_rows": selection["frame_rows"], "global_duplicate_job_hashes_excluded": selection["global_duplicate_job_hashes_excluded"], "heldout_key_count": len(heldout_keys), "known_used_key_count": len(known_used_keys), "prior_review_matches_excluded": selection["heldout_matches_excluded"], "eligible_after_exclusion": selection["frame_rows"] - selection["heldout_matches_excluded"], "core_selected": core_n, "challenge_selected": challenge_n, "unique_ads": len(selection["selected"]), "core_dual_review": 8},
      "core_strata": {key: {"frame_size": selection["core_sizes"][key], "selected": selection["core_alloc"][key], "sampling_probability": selection["core_alloc"][key] / selection["core_sizes"][key]} for key in sorted(selection["core_sizes"])},
      "challenge_strata": {key: {"eligible_size_after_core": selection["challenge_sizes"][key], "selected": selection["challenge_alloc"][key], "sampling_probability": selection["challenge_alloc"][key] / selection["challenge_sizes"][key]} for key in sorted(selection["challenge_sizes"])},
      "blinding": {"model_predictions_in_reviewer_pack": False, "private_key_in_reviewer_pack": False, "raw_text_written_to_public_receipt": False, "challenge_excluded_from_prevalence_estimates": True}, "heldout_exclusion_unverified": bool(args.allow_unverified_heldout_d18), "scope": "limited_human_diagnostic_only" if args.allow_unverified_heldout_d18 else "heldout_excluded_human_diagnostic", "private_outputs": ["selected_key_manifest.json"]}
    if args.selected_text:
        receipt["counts"]["core_dual_review"] = materialize(args, selection, private_dir)
        receipt["private_outputs"] += ["reviewer_pack.csv", "reviewer_pack_preview.html", "REVIEW_INSTRUCTIONS_zh.md", "private_answer_key.csv", "review_assignments.csv"]
    args.public_receipt.parent.mkdir(parents=True, exist_ok=True)
    args.public_receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
