#!/usr/bin/env python3
"""Register the completed 2,464-shard narrow base without reading row data."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pyarrow.parquet as pq

EXPECTED_SHARDS = 2464
EXPECTED_CANONICAL_ROWS = 204_774_035
EXPECTED_USABLE_ROWS = 204_768_752
EXPECTED_VERSION = "pre_revelio_semantic_narrow_v1"
AGGREGATES = (
    "T2_EXPERIENCE_AD_RATES.csv",
    "T2_DURATION_BOUND_DISTRIBUTION.csv",
    "T3_TECHNOLOGY_ROLE.csv",
    "T3_TECHNOLOGY_PAIR_OVERLAP.csv",
    "T3_TECHNOLOGY_EXPERIENCE_COOCCURRENCE.csv",
)
AGGREGATE_HASH_KEYS = {
    "T2_EXPERIENCE_AD_RATES.csv": "ad_rates_sha256",
    "T2_DURATION_BOUND_DISTRIBUTION.csv": "duration_distribution_sha256",
    "T3_TECHNOLOGY_ROLE.csv": "technology_role_sha256",
    "T3_TECHNOLOGY_PAIR_OVERLAP.csv": "technology_pair_sha256",
    "T3_TECHNOLOGY_EXPERIENCE_COOCCURRENCE.csv": "technology_experience_sha256",
}


def load_json(path: Path):
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(str(path) + ".partial")
    temporary.write_text(value)
    os.replace(temporary, path)


def atomic_json(path: Path, value) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def schema_value(schema):
    return [{"name": field.name, "type": str(field.type), "nullable": field.nullable}
            for field in schema]


def sql_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--t1-dir", type=Path, required=True)
    parser.add_argument("--t4-dir", type=Path, required=True)
    parser.add_argument("--t4-receipt", type=Path, required=True)
    parser.add_argument("--candidate-join-manifest", type=Path, required=True)
    parser.add_argument("--expected-shards", type=int, default=EXPECTED_SHARDS)
    parser.add_argument("--expected-canonical-rows", type=int,
                        default=EXPECTED_CANONICAL_ROWS)
    parser.add_argument("--expected-usable-rows", type=int,
                        default=EXPECTED_USABLE_ROWS)
    args = parser.parse_args()

    source = args.source_root.resolve()
    shards = source / "shards"
    output = args.output_root.resolve()
    if output == source or source in output.parents:
        raise RuntimeError("release output must be separate from the immutable source")

    batch_path = source / "BATCH_RECEIPT.json"
    aggregate_receipt_path = source / "aggregate" / "AGGREGATE_RECEIPT.json"
    batch = load_json(batch_path)
    aggregate_receipt = load_json(aggregate_receipt_path)
    if (batch.get("status") != "complete" or
            batch.get("shards") != args.expected_shards or
            batch.get("actions", {}).get("built") != args.expected_shards):
        raise RuntimeError("original batch receipt is not the exact completed release")
    if (aggregate_receipt.get("status") != "complete" or
            aggregate_receipt.get("shards") != args.expected_shards):
        raise RuntimeError("original aggregate receipt is incomplete")
    for key in ("builder_sha256", "gate_sha256", "manifest_sha256",
                "plan_set_sha256", "runner_sha256"):
        if aggregate_receipt.get("identity", {}).get(key) != batch.get(key):
            raise RuntimeError(f"batch/aggregate source identity mismatch: {key}")

    receipts = sorted(shards.glob("*.receipt.json"))
    markers = sorted(shards.glob("*.batch.json"))
    if len(receipts) != args.expected_shards or len(markers) != args.expected_shards:
        raise RuntimeError("exact receipt and marker counts required")

    marker_by_id = {path.name[:-len(".batch.json")]: path for path in markers}
    catalog = []
    ad_schema = None
    duration_schema = None
    total_rows = 0
    total_duration_rows = 0
    usable_rows_from_receipts = 0
    usable_count_available = True
    data_bytes = 0
    duration_bytes = 0
    receipt_versions = Counter()

    for receipt_path in receipts:
        shard_id = receipt_path.name[:-len(".receipt.json")]
        if shard_id not in marker_by_id:
            raise RuntimeError(f"missing marker for {shard_id}")
        ad_path = shards / f"{shard_id}.parquet"
        duration_path = shards / f"{shard_id}.durations.parquet"
        if not ad_path.is_file() or not duration_path.is_file():
            raise RuntimeError(f"missing retained parquet for {shard_id}")

        receipt = load_json(receipt_path)
        marker = load_json(marker_by_id[shard_id])
        if receipt.get("status") != "complete":
            raise RuntimeError(f"invalid original receipt for {shard_id}")
        if marker.get("shard_id") != shard_id:
            raise RuntimeError(f"invalid original marker for {shard_id}")
        if marker.get("receipt_sha256") != sha256(receipt_path):
            raise RuntimeError(f"receipt-marker hash mismatch for {shard_id}")
        if marker.get("output_sha256") != receipt.get("output_sha256"):
            raise RuntimeError(f"ad hash binding mismatch for {shard_id}")
        if marker.get("duration_sha256") != receipt.get("duration_detail_sha256"):
            raise RuntimeError(f"duration hash binding mismatch for {shard_id}")

        ad_parquet = pq.ParquetFile(ad_path)
        duration_parquet = pq.ParquetFile(duration_path)
        ad_footer = ad_parquet.metadata
        duration_footer = duration_parquet.metadata
        if ad_footer.num_rows != receipt.get("output_rows"):
            raise RuntimeError(f"ad footer row mismatch for {shard_id}")
        if duration_footer.num_rows != receipt.get("duration_detail_rows"):
            raise RuntimeError(f"duration footer row mismatch for {shard_id}")

        current_ad_schema = ad_parquet.schema_arrow
        current_duration_schema = duration_parquet.schema_arrow
        if ad_schema is None:
            ad_schema = current_ad_schema
            duration_schema = current_duration_schema
        elif not ad_schema.equals(current_ad_schema, check_metadata=False):
            raise RuntimeError(f"ad schema drift at {shard_id}")
        elif not duration_schema.equals(current_duration_schema, check_metadata=False):
            raise RuntimeError(f"duration schema drift at {shard_id}")

        rows = int(ad_footer.num_rows)
        duration_rows = int(duration_footer.num_rows)
        total_rows += rows
        total_duration_rows += duration_rows
        data_bytes += ad_path.stat().st_size
        duration_bytes += duration_path.stat().st_size
        receipt_versions[str(receipt.get("version"))] += 1
        if "usable_rows" in receipt:
            usable_rows_from_receipts += int(receipt["usable_rows"])
        else:
            usable_count_available = False

        catalog.append({
            "shard_id": shard_id,
            "ad_path": str(ad_path),
            "ad_rows": rows,
            "ad_bytes": ad_path.stat().st_size,
            "ad_sha256_from_original_receipt": receipt["output_sha256"],
            "duration_path": str(duration_path),
            "duration_rows": duration_rows,
            "duration_bytes": duration_path.stat().st_size,
            "duration_sha256_from_original_receipt": receipt["duration_detail_sha256"],
            "original_receipt_path": str(receipt_path),
            "original_receipt_sha256": marker["receipt_sha256"],
        })

    if total_rows != args.expected_canonical_rows:
        raise RuntimeError(f"canonical rows {total_rows} != {args.expected_canonical_rows}")
    if usable_count_available and usable_rows_from_receipts != args.expected_usable_rows:
        raise RuntimeError("usable row total disagrees with frozen accepted denominator")
    if set(receipt_versions) != {EXPECTED_VERSION}:
        raise RuntimeError(f"unexpected receipt versions: {dict(receipt_versions)}")

    reused_dir = output / "reused"
    reused_dir.mkdir(parents=True, exist_ok=True)
    aggregate_hashes = {}
    for name in AGGREGATES:
        source_file = source / "aggregate" / name
        actual = sha256(source_file)
        if aggregate_receipt.get(AGGREGATE_HASH_KEYS[name]) != actual:
            raise RuntimeError(f"aggregate hash mismatch: {name}")
        destination = reused_dir / name
        shutil.copyfile(source_file, destination)
        aggregate_hashes[name] = actual

    t1_files = {}
    for name in ("input_match_canonical_usable_funnel.csv",
                 "created_first_observed_queue_distribution.csv",
                 "technology_experience_candidate_evidence.csv",
                 "CONSERVATION_REPORT.json", "FIRST_WAVE_RUN_RECEIPT.json"):
        source_file = args.t1_dir / name
        destination = reused_dir / name
        shutil.copyfile(source_file, destination)
        t1_files[name] = sha256(destination)
    t1_receipt = load_json(args.t1_dir / "FIRST_WAVE_RUN_RECEIPT.json")
    if (t1_receipt.get("status") != "complete" or
            t1_receipt.get("shards") != args.expected_shards or
            t1_receipt.get("conservation_report_sha256") !=
            sha256(args.t1_dir / "CONSERVATION_REPORT.json")):
        raise RuntimeError("T1 receipt/conservation binding failed")
    if (t1_receipt.get("gate_sha256") != batch.get("gate_sha256") or
            t1_receipt.get("manifest_sha256") != batch.get("manifest_sha256")):
        raise RuntimeError("T1 and narrow batch do not bind the same frozen source")
    conservation = load_json(args.t1_dir / "CONSERVATION_REPORT.json")
    if (conservation.get("status") != "complete" or
            conservation.get("shards") != args.expected_shards or
            conservation.get("funnel", {}).get("canonical_ad_status") !=
            args.expected_canonical_rows or
            conservation.get("funnel", {}).get("usable_nonempty_complete_parse") !=
            args.expected_usable_rows):
        raise RuntimeError("T1 frozen canonical/usable denominator gate failed")

    t4 = load_json(args.t4_receipt)
    if (t4.get("status") != "complete" or
            t4.get("validation_scope") != "production" or
            t4.get("identity", {}).get("expected_shards") != args.expected_shards or
            t4.get("identity", {}).get("expected_canonical_rows") != args.expected_canonical_rows):
        raise RuntimeError("T4 receipt is not the accepted full-corpus production receipt")
    t4_files = {}
    for name, expected_hash in sorted(t4.get("outputs", {}).items()):
        source_file = args.t4_dir / name
        if sha256(source_file) != expected_hash:
            raise RuntimeError(f"T4 output hash mismatch: {name}")
        destination = reused_dir / name
        shutil.copyfile(source_file, destination)
        t4_files[name] = expected_hash

    candidate_join = load_json(args.candidate_join_manifest)
    if (candidate_join.get("status") != "complete" or
            candidate_join.get("version") != "comparison_join_v1" or
            candidate_join.get("candidate_rows") != 6_010_975 or
            candidate_join.get("output_rows") != 6_010_975 or
            candidate_join.get("records_matches") != {"0": 0, "1": 6_010_975, ">1": 0} or
            candidate_join.get("onet_matches") != {"0": 2_842, "1": 6_008_133, ">1": 0}):
        raise RuntimeError("candidate metadata join receipt/cardinality gate failed")
    candidate_paths = []
    candidate_schema = None
    candidate_rows = 0
    for item in candidate_join.get("files", []):
        if not isinstance(item.get("sha256"), str) or len(item["sha256"]) != 64:
            raise RuntimeError("candidate join manifest lacks recorded SHA-256")
        path = Path(item["path"])
        if not path.is_file() or path.stat().st_size != item["size"]:
            raise RuntimeError(f"candidate join file size mismatch: {path.name}")
        parquet = pq.ParquetFile(path)
        if parquet.metadata.num_rows != item["rows"]:
            raise RuntimeError(f"candidate join footer mismatch: {path.name}")
        schema = parquet.schema_arrow
        if candidate_schema is None:
            candidate_schema = schema
        elif not candidate_schema.equals(schema, check_metadata=False):
            raise RuntimeError(f"candidate join schema drift: {path.name}")
        candidate_rows += parquet.metadata.num_rows
        candidate_paths.append(str(path))
    if len(candidate_paths) != 16 or candidate_rows != 6_010_975:
        raise RuntimeError("candidate join exact 16-prefix row gate failed")

    catalog_path = output / "CORPUS_RELEASE_CATALOG_PRIVATE.jsonl"
    atomic_text(catalog_path, "".join(json.dumps(row, sort_keys=True) + "\n" for row in catalog))
    ad_paths = ",\n  ".join(sql_quote(row["ad_path"]) for row in catalog)
    duration_paths = ",\n  ".join(sql_quote(row["duration_path"]) for row in catalog)
    views = (
        "-- Private zero-copy paths; generated from the verified release catalog.\n"
        "CREATE OR REPLACE VIEW linkup_corpus_narrow_v1 AS\n"
        "SELECT * FROM read_parquet([\n  " + ad_paths + "\n], union_by_name=false);\n\n"
        "CREATE OR REPLACE VIEW linkup_corpus_duration_evidence_v1 AS\n"
        "SELECT * FROM read_parquet([\n  " + duration_paths + "\n], union_by_name=false);\n"
        "\n-- Separate candidate-only metadata join; never use as the corpus denominator.\n"
        "CREATE OR REPLACE VIEW linkup_candidate_metadata_join_v1 AS\n"
        "SELECT * FROM read_parquet([\n  " +
        ",\n  ".join(sql_quote(path) for path in candidate_paths) +
        "\n], union_by_name=false);\n"
    )
    views_path = output / "CORPUS_RELEASE_VIEWS_PRIVATE.sql"
    atomic_text(views_path, views)

    schema_public = {
        "release_version": "whole-corpus-old-narrow-v1",
        "ad_schema": schema_value(ad_schema),
        "duration_schema": schema_value(duration_schema),
        "candidate_metadata_join_schema": schema_value(candidate_schema),
        "field_limits": {
            "usable": "engineering parse state, not semantic accuracy",
            "experience_and_technology": "old-version candidate measures, not semantic gold",
            "occupation_task": "structurally unavailable; retain NA, never zero",
            "dates": "observation metadata, not historical text-version proof",
            "predictive_ai": "frozen all-zero/unmeasurable under the old vocabulary",
            "non_detection": "candidate false or non-detection does not establish semantic absence",
        },
    }
    schema_path = output / "SCHEMA_PUBLIC.json"
    atomic_json(schema_path, schema_public)

    receipt = {
        "status": "complete",
        "release_version": "whole-corpus-old-narrow-v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "job_id": os.environ.get("SLURM_JOB_ID"),
        "execution_environment": "SCNet China scheduled job",
        "method": "receipt_and_parquet_footer_verification_only; no column data read",
        "source": {
            "batch_receipt_sha256": sha256(batch_path),
            "aggregate_receipt_sha256": sha256(aggregate_receipt_path),
            "t4_receipt_sha256": sha256(args.t4_receipt),
            "candidate_join_manifest_sha256": sha256(args.candidate_join_manifest),
            "shards": len(catalog),
            "receipt_versions": dict(receipt_versions),
        },
        "coverage": {
            "canonical_us_ads": total_rows,
            "engineering_usable_ads": args.expected_usable_rows,
            "engineering_usable_rate": args.expected_usable_rows / total_rows,
            "duration_evidence_rows": total_duration_rows,
        },
        "storage": {
            "ad_parquet_bytes": data_bytes,
            "duration_parquet_bytes": duration_bytes,
            "new_row_level_data_bytes": 0,
            "zero_copy_views": True,
        },
        "outputs": {
            "private_catalog_sha256": sha256(catalog_path),
            "private_views_sql_sha256": sha256(views_path),
            "schema_public_sha256": sha256(schema_path),
            "reused_aggregate_sha256": aggregate_hashes,
            "reused_t1_sha256": t1_files,
            "reused_t4_sha256": t4_files,
        },
        "metadata_scope": {
            "full_row_level_records_onet_join_included": False,
            "reason": "T4 retained full-corpus aggregates but not its temporary full row-level joined tables",
            "candidate_only_join_excluded_from_corpus_denominator": True,
            "candidate_metadata_join": {
                "rows": candidate_rows,
                "records_match_exactly_one": 6_010_975,
                "onet_match_exactly_one": 6_008_133,
                "onet_missing": 2_842,
                "onet_multiple": 0,
                "separate_view": "linkup_candidate_metadata_join_v1",
                "verification": "manifest-recorded SHA-256 required; files freshly size/footer/schema checked, not freshly SHA-rehashed",
            },
        },
        "limits": list(schema_public["field_limits"].values()),
    }
    atomic_json(output / "CORPUS_RELEASE_RECEIPT.json", receipt)
    print(json.dumps({"status": "complete", "shards": len(catalog),
                      "canonical_rows": total_rows, "output": str(output)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
