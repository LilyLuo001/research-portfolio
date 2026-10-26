#!/usr/bin/env python3
"""Attach accepted fixed10k ad references to the immutable old narrow corpus.

Scheduled SCNet job only. Reads canonical keys from the old base and parent
candidate files, and semantic columns from the accepted 10k Parquet. Never reads
advertisement text. Writes a sparse private sidecar and zero-copy DuckDB views.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

KEY = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
EXPECTED_REFERENCE_SHA = "733875307de475a296e3da4531ad64ba99351f5e2dff109b757ad80b80b34adb"
EXPECTED_CATALOG_SHA = "4265e2469a8d3d35a769faad9c163823b0df32364f88061db5ecc5e131b1eb1e"
# Accepted ordinals 0-15 from design_correction_20261024/results/
# RUN_RECEIPT_PUBLIC.json input_sha256.parent_files; file names are 0-f.parquet.
EXPECTED_PARENT_SHA = (
    "df2c84f4237d823a30e94e6591b90d37b106fe07538a6c9919d1aa29ba0d9c46",
    "50de786ae0f94485695050a244c75b07ef143ff2538b182a43b94145be45cf4f",
    "485b18181e3aafc3bd6f5a7aab0446cc4be346d702289c3937a5244af7727fe4",
    "91175e5a057a5cc40bc00bb18f12ebb33bbf44166a9ee266fcf8df1aadb61c4c",
    "d6d9fff9ade5a66b5b8d0339dc3e9e347a8f2e83af8c693b146ffbd634e5ded5",
    "5e56442ca63c099d83491c98fdb3517e6bc6b86cf9859bec70ccf86fc44ef7fb",
    "148812b90a5ac59ba2f1059a8ffcc18438758375f4e70509b17d6f76168265c0",
    "c87e10d1cbc9026b5be397e91c0934236566b7048d96882cd6efecd16fcc11ed",
    "cc2a6d08a550ebdd3c9766ff51462e78f6e00dbcbc671ba5b581039eea076278",
    "653049cdca1acf872f82aa6ec65618d1a5df774f28d49291d286ac7fe1f1d568",
    "db0fb5fe28fa4701994aaafc0cb3c11bfe4d0ab153f9093b3fc1574aec0cedaa",
    "7c2eade39b76f3ab9cd3883c41fc553a8a86f23ec1a0ede7d73c124daa207f27",
    "d33e2f8cad3c77d6516ea34ed84a0b0e2d7b77a39bdd65ea492c33fdd1942226",
    "8159db66961ffea8dd39824bd8b516b5ccd2b8aaaa290af8e53f85748fbea14f",
    "0ab8185f84b9589606c300b5ef156dfe71247c9d454d6d8fa78e9d5c374911d7",
    "2915aa7cd28f517fd50071ada476fa4c2e3d0e69db9ddb056b58dbe7377bd374",
)
EXPECTED_OLD_ROWS = 204_774_035
VERSION = "accepted-original-ad-reference-overlay-v1"
# Match the accepted research availability rule in
# fixed10k_empirical_20261024/code/run_empirical.py. A not_applicable family
# can carry an accepted zero; preserve the source value (including its own null).
USABLE = {"known", "not_applicable"}

# Explicit compatibility map. Old fields remain old rule candidates in old.*.
# No old field is a fallback for a reference unknown. Occupation-task is absent
# in the old extractor, even if a nullable placeholder is present in its schema.
FAMILIES = {
    "experience_object": ["experience_general_work", "experience_industry_domain", "experience_occupation_task", "experience_tool_specific"],
    "experience_strength": [f"strength_{obj}_{kind}" for obj in ("general_work", "industry_domain", "occupation_task", "tool_specific") for kind in ("required", "preferred", "explicitly_waived")],
    "experience_literal_years": [f"numeric_years_{obj}" for obj in ("general_work", "industry_domain", "occupation_task", "tool_specific")],
    "qualification_conditions_and_alternatives": [f"{kind}_{obj}" for kind in ("conditional", "alternative_branch", "alternative_and_branch", "alternative_or_branch") for obj in ("general_work", "industry_domain", "occupation_task", "tool_specific")],
    "entry_wording_and_scope": ["explicit_new_graduate", "explicit_new_graduate_unconditional", "explicit_no_experience", "explicit_no_experience_unconditional", "graduate_or_noexperience", "graduate_or_noexperience_unconditional"],
    "current_responsibility_subject_and_relation": ["duty_any", "duty_any_conditional", "duty_any_unconditional"] + [f"duty_{obj}{suffix}" for obj in ("client_ownership", "independent_judgment", "people_supervision", "training_mentoring") for suffix in ("", "_conditional", "_unconditional")],
    "technology_category_and_role": ["technology_group"],
}
OLD_COMPATIBILITY = {
    "experience_general_work": "exp_general_work_* are old rule candidates; retain separately",
    "experience_industry_domain": "exp_industry_domain_* are old rule candidates; retain separately",
    "experience_tool_specific": "exp_specific_tool_* are old rule candidates with nonidentical scope; retain separately",
    "experience_occupation_task": "old exp_occupation_task_available=false/NA; never infer negative",
    "technology_group": "old tech_* candidates use old vocabulary; no direct equivalence",
    "all_other_reference_fields": "no compatible old reference field; expose original values only for known or not_applicable family status",
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def q(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def qi(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(str(path) + ".tmp")
    temp.write_text(value, encoding="utf-8")
    os.replace(temp, path)


def key(row):
    values = tuple(row[x] for x in KEY)
    if any(x is None for x in values):
        raise RuntimeError("null canonical key")
    return (str(values[0]), str(values[1]), int(values[2]), int(values[3]))


def inspected_file(path: Path, required: set[str]) -> dict:
    if not path.is_file():
        raise RuntimeError("source file missing: " + str(path))
    pf = pq.ParquetFile(path)
    names = set(pf.schema_arrow.names)
    if not required <= names:
        raise RuntimeError("required columns absent: " + str(path))
    forbidden = {"DESCRIPTION", "JOB_DESCRIPTION", "ORIGINAL_TEXT", "RAW_TEXT", "TEXT", "EVIDENCE_QUOTE"}
    projected = set(KEY) | (required - set(KEY))
    if any(name.upper() in forbidden for name in projected):
        raise RuntimeError("text projection refused")
    return {"rows": pf.metadata.num_rows, "bytes": path.stat().st_size}


def count_matches(con, paths: list[Path], source_label: str) -> dict:
    if not paths:
        raise RuntimeError("empty " + source_label + " lookup file set")
    files = "[" + ",".join(q(str(path)) for path in paths) + "]"
    columns = ",".join("p." + qi(x) for x in KEY)
    using = ",".join(qi(x) for x in KEY)
    sql = ("SELECT " + columns + ",count(*) AS matches FROM read_parquet(" + files +
           ",union_by_name=false) p SEMI JOIN fixed_reference_keys r USING (" + using + ") GROUP BY " + columns)
    rows = con.execute(sql).fetch_arrow_table().to_pylist()
    out = {}
    for row in rows:
        k = key(row)
        if k in out:
            raise RuntimeError("grouped lookup returned duplicate key")
        out[k] = int(row["matches"])
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--reference", type=Path, required=True)
    p.add_argument("--catalog", type=Path, required=True)
    p.add_argument("--parent-candidate-dir", type=Path, required=True,
                   help="Directory containing the accepted 0-f.parquet candidate parents")
    p.add_argument("--private-output", type=Path, required=True)
    p.add_argument("--public-output", type=Path, required=True)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--memory-limit", default="8GB")
    a = p.parse_args()
    if not os.environ.get("SLURM_JOB_ID"):
        raise RuntimeError("scheduled SCNet job required")
    if a.threads < 1 or a.threads > 64:
        raise RuntimeError("invalid thread count")
    private = a.private_output.resolve()
    public = a.public_output.resolve()
    if "private" not in private.parts or private == public:
        raise RuntimeError("separate private output directory required")
    private.mkdir(parents=True, exist_ok=True)
    public.mkdir(parents=True, exist_ok=True)
    sidecar_path = private / "ORIGINAL_AD_REFERENCE_OVERLAY_PRIVATE.parquet"
    sql_path = private / "REFERENCE_ENHANCED_VIEWS_PRIVATE.sql"
    receipt_path = public / "AD_REFERENCE_OVERLAY_RECEIPT_PUBLIC.json"
    if any(x.exists() for x in (sidecar_path, sql_path, receipt_path)):
        raise RuntimeError("existing output guard")
    if digest(a.reference) != EXPECTED_REFERENCE_SHA:
        raise RuntimeError("accepted reference SHA-256 mismatch")
    if digest(a.catalog) != EXPECTED_CATALOG_SHA:
        raise RuntimeError("accepted old catalog SHA-256 mismatch")

    reference_required = set(KEY) | {"normalized_context_sha256"}
    reference_required |= {"status_" + family for family in FAMILIES}
    reference_required |= {field for fields in FAMILIES.values() for field in fields}
    ref_info = inspected_file(a.reference, reference_required)
    if ref_info["rows"] != 10_000:
        raise RuntimeError("reference is not accepted original 10000 frame")
    ref_columns = list(KEY) + ["normalized_context_sha256"] + ["status_" + f for f in FAMILIES] + [x for fields in FAMILIES.values() for x in fields]
    ref = pq.read_table(a.reference, columns=ref_columns)
    rows = ref.to_pylist()
    keys = [key(row) for row in rows]
    if len(set(keys)) != 10_000 or any(not row["normalized_context_sha256"] for row in rows):
        raise RuntimeError("reference key/context identity gate failed")

    parent_paths = [a.parent_candidate_dir / (format(i, "x") + ".parquet") for i in range(16)]
    parent_info = [inspected_file(path, set(KEY)) for path in parent_paths]
    parent_actual_sha = []
    for ordinal, path in enumerate(parent_paths):
        actual = digest(path)
        if actual != EXPECTED_PARENT_SHA[ordinal]:
            raise RuntimeError("accepted parent file SHA-256 mismatch at ordinal %d" % ordinal)
        parent_actual_sha.append(actual)
    catalog = [json.loads(line) for line in a.catalog.read_text().splitlines() if line.strip()]
    if len(catalog) != 2464 or len({x["shard_id"] for x in catalog}) != 2464:
        raise RuntimeError("old catalog shard gate failed")
    if sum(int(x["ad_rows"]) for x in catalog) != EXPECTED_OLD_ROWS:
        raise RuntimeError("old catalog row denominator changed")
    old_paths = [Path(item["ad_path"]) for item in catalog]
    for path in old_paths:
        if not path.is_file():
            raise RuntimeError("catalog old ad file missing: " + str(path))
    old_schema = pq.ParquetFile(old_paths[0]).schema_arrow
    if not set(KEY) <= set(old_schema.names):
        raise RuntimeError("old base lacks canonical key")
    old_lookup_total = 0
    for item, path in zip(catalog, old_paths):
        # Footer-only verification binds catalog paths and accepted row counts.
        n = pq.ParquetFile(path).metadata.num_rows
        if n != item["ad_rows"] or path.stat().st_size != item["ad_bytes"]:
            raise RuntimeError("old catalog footer/size mismatch")
        old_lookup_total += n
    if old_lookup_total != EXPECTED_OLD_ROWS:
        raise RuntimeError("old footer total mismatch")

    con = duckdb.connect()
    con.execute("SET threads=" + str(a.threads))
    con.execute("SET memory_limit=" + q(a.memory_limit))
    con.execute("SET temp_directory=" + q(str(private / "duckdb_tmp")))
    con.register("fixed_reference_keys", ref.select(list(KEY)))
    parent_matches = count_matches(con, parent_paths, "parent")
    old_matches = count_matches(con, old_paths, "old")
    con.unregister("fixed_reference_keys")
    con.close()
    parent_hist = Counter(parent_matches.get(k, 0) for k in keys)
    old_hist = Counter(old_matches.get(k, 0) for k in keys)
    parent_duplicates = sum(count for matches, count in parent_hist.items() if matches > 1)
    old_duplicates = sum(count for matches, count in old_hist.items() if matches > 1)
    if parent_duplicates or old_duplicates:
        raise RuntimeError("duplicate exact canonical reference keys: parent_ads=%d old_ads=%d" %
                           (parent_duplicates, old_duplicates))

    # Only original ads independently present exactly once in both accepted
    # candidate parents and old base can be attached. No context/hash expansion.
    overlay = []
    usable_by_family = {f: Counter() for f in FAMILIES}
    status_by_family = {f: Counter() for f in FAMILIES}
    for row, k in zip(rows, keys):
        if parent_matches.get(k, 0) != 1 or old_matches.get(k, 0) != 1:
            continue
        out = {name: row[name] for name in KEY}
        out.update(reference_normalized_context_sha256=row["normalized_context_sha256"],
                   reference_identity_state="accepted_original_ad_exact_four_key",
                   reference_source="accepted_fixed10k_AD_LEVEL_RESEARCH_PRIVATE")
        for family, fields in FAMILIES.items():
            status = row["status_" + family]
            if not isinstance(status, str) or not status:
                raise RuntimeError("missing accepted family status")
            out["reference_status_" + family] = status
            out["reference_source_" + family] = "accepted_fixed10k_original_ad"
            status_by_family[family][status] += 1
            if status in USABLE:
                usable_by_family[family][status] += 1
            for field in fields:
                # Preserve original source untouched; expose no reference value
                # from unknown/partial/candidate-only/source-unavailable masks.
                # In usable states, preserve each field's original zero or null.
                out["reference_" + field] = row[field] if status in USABLE else None
        overlay.append(out)
    table = pa.Table.from_pylist(overlay)
    if len(overlay) == 0 or len({key(x) for x in overlay}) != len(overlay):
        raise RuntimeError("empty or duplicate sparse overlay")
    temp = Path(str(sidecar_path) + ".tmp")
    pq.write_table(table, temp, compression="zstd")
    os.chmod(temp, 0o600)
    if pq.ParquetFile(temp).metadata.num_rows != len(overlay):
        raise RuntimeError("persisted overlay row mismatch")
    os.replace(temp, sidecar_path)

    old_list = "[\n  " + ",\n  ".join(q(str(path)) for path in old_paths) + "\n]"
    key_using = ", ".join(qi(name) for name in KEY)
    new_cols = [name for name in table.column_names if name not in KEY]
    selected = ",\n  ".join("ov." + qi(name) for name in new_cols)
    sql = ("-- Run in DuckDB. Old 204,774,035 rows stay in original Parquet files.\n"
           "CREATE OR REPLACE VIEW linkup_old_narrow_reference_enhanced_v1 AS\n"
           "SELECT old.*,\n  " + selected + "\nFROM read_parquet(" + old_list + ",union_by_name=false) old\n"
           "LEFT JOIN read_parquet(" + q(str(sidecar_path)) + ") ov USING (" + key_using + ");\n\n"
           "-- All original fixed10k columns, labels, masks and weights remain visible.\n"
           "CREATE OR REPLACE VIEW linkup_reference_original10k_v1 AS\n"
           "SELECT * FROM read_parquet(" + q(str(a.reference)) + ");\n")
    atomic_text(sql_path, sql)
    os.chmod(sql_path, 0o600)

    public_map = public / "FIELD_COMPATIBILITY_PUBLIC.json"
    mapping = {"version": VERSION, "canonical_key": KEY,
               "reference_value_field_count": sum(len(fields) for fields in FAMILIES.values()),
               "usable_original_statuses": sorted(USABLE),
               "families": {f: {"status_column": "status_" + f, "reference_columns": fields,
                                "adoption": "preserve original field value, including zero or null, only when status is known or not_applicable"}
                            for f, fields in FAMILIES.items()},
               "old_comparability": OLD_COMPATIBILITY,
               "old_candidates_are_not_reference_fallback": True,
               "candidate_relation_overlay": "separate candidate-specific layer; not handled by this ad-field attachment"}
    atomic_text(public_map, json.dumps(mapping, indent=2, sort_keys=True) + "\n")
    receipt = {"version": VERSION, "status": "pass", "job_id": os.environ["SLURM_JOB_ID"],
               "created_utc": datetime.now(timezone.utc).isoformat(),
               "code_sha256": digest(Path(__file__)),
               "inputs": {"reference_sha256": EXPECTED_REFERENCE_SHA,
                          "catalog_sha256": EXPECTED_CATALOG_SHA,
                          "old_data_verification": "pinned catalog SHA-256 plus each ad file's size and Parquet footer row count; no fresh full-content SHA-256 of old Parquet",
                          "parent_candidate_files": 16,
                          "parent_candidate_footer_rows": sum(x["rows"] for x in parent_info),
                          "parent_candidate_sha256_by_ordinal_0_to_15": parent_actual_sha,
                          "old_shards": 2464, "old_footer_rows": old_lookup_total},
               "match_counts": {"parent": {str(k): v for k, v in sorted(parent_hist.items())},
                                "old_base": {str(k): v for k, v in sorted(old_hist.items())},
                                "attached_original_ads": len(overlay),
                                "unattached_original_ads": 10_000 - len(overlay)},
               "reference_family_status_counts_on_attached_ads": {f: dict(c) for f, c in status_by_family.items()},
               "usable_family_counts_by_status_on_attached_ads": {f: dict(c) for f, c in usable_by_family.items()},
               "outputs": {"private_sidecar_sha256": digest(sidecar_path),
                           "private_views_sql_sha256": digest(sql_path),
                           "field_compatibility_public_sha256": digest(public_map)},
               "checks": {"original_input_unchanged": True, "exact_four_key_only": True,
                          "old_values_retained_in_view": True, "reference_unknown_not_filled_from_old": True,
                          "no_description_or_quote_read": True, "no_failed_model_predictions": True,
                          "no_complete_input_propagation": True},
               "claim_boundary": "Sparse original-ad attachment only; no whole-corpus fine-semantic coverage or negative inference from old non-detection."}
    atomic_text(receipt_path, json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
