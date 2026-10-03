#!/usr/bin/env python3
"""Local-only preparation, offline validation, and scale receipts for L2."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from validate_extraction import SCHEMA_PATH, sha256_text, validate_jsonl


HERE = Path(__file__).resolve().parent
PROMPT_PATH = HERE / "prompts" / "extraction_v1.md"
GATE_PATH = HERE / "config" / "batch_api_gate.template.json"
LOCATOR_FIELDS = ("JOB_HASH", "SOURCE_FILE", "SOURCE_ROW", "RECORD_SOURCE_ROW")
TEXT_ALIASES = ("original_text", "text", "DESCRIPTION", "description")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix in {".jsonl", ".ndjson"}:
        rows = []
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if line.strip():
                    value = json.loads(line)
                    if not isinstance(value, dict):
                        raise ValueError(f"line {line_number} is not an object")
                    rows.append(value)
        return rows
    if suffix == ".parquet":
        try:
            import pyarrow.parquet as pq
        except ImportError as exc:
            raise RuntimeError("Parquet input requires pyarrow") from exc
        return pq.read_table(path).to_pylist()
    raise ValueError("input must be .jsonl, .ndjson, or .parquet")


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def resolve_text_column(rows: list[dict[str, Any]], requested: str | None) -> str:
    if not rows:
        raise ValueError("input has no rows")
    candidates = (requested,) if requested else TEXT_ALIASES
    for name in candidates:
        if name and all(name in row for row in rows):
            return name
    raise ValueError(f"text column not found; tried {', '.join(name for name in candidates if name)}")


def normalized_pack(rows: list[dict[str, Any]], text_column: str) -> tuple[list[dict[str, Any]], list[str]]:
    errors: list[str] = []
    pack: list[dict[str, Any]] = []
    record_ids: set[str] = set()
    locators: set[tuple[str, str, str]] = set()
    for index, row in enumerate(rows):
        missing = [field for field in LOCATOR_FIELDS if field not in row]
        if missing:
            errors.append(f"row {index}: missing locator fields {missing}")
            continue
        record_id = str(row["JOB_HASH"])
        text = row[text_column]
        if not record_id:
            errors.append(f"row {index}: empty JOB_HASH")
        if record_id in record_ids:
            errors.append(f"row {index}: duplicate JOB_HASH={record_id}")
        record_ids.add(record_id)
        locator = (str(row["SOURCE_FILE"]), str(row["SOURCE_ROW"]), record_id)
        if locator in locators:
            errors.append(f"row {index}: duplicate exact source locator={locator}")
        locators.add(locator)
        if not isinstance(text, str):
            errors.append(f"row {index}: text is not a string")
            continue
        control_count = sum(ord(char) < 32 and char not in "\n\r\t" for char in text)
        if not text.strip():
            errors.append(f"row {index}: text is empty or whitespace")
        if text and control_count / len(text) > 0.01:
            errors.append(f"row {index}: more than 1% unsupported control characters")
        pack.append({
            "record_id": record_id,
            "JOB_HASH": record_id,
            "SOURCE_FILE": str(row["SOURCE_FILE"]),
            "SOURCE_ROW": row["SOURCE_ROW"],
            "RECORD_SOURCE_ROW": row["RECORD_SOURCE_ROW"],
            "source_text_sha256": sha256_text(text),
            "original_text": text,
        })
    return pack, errors


def private_output_guard(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    if resolved == HERE or HERE in resolved.parents:
        raise ValueError("raw-text packs cannot be written inside measurement/; choose a private output directory")


def comparison_ids(path: Path) -> list[str]:
    rows = read_rows(path)
    ids = [str(row.get("JOB_HASH", row.get("record_id", ""))) for row in rows]
    if len(ids) != 80 or any(not value for value in ids) or len(set(ids)) != 80:
        raise ValueError("L1 comparison manifest must contain exactly 80 unique JOB_HASH/record_id values")
    return ids


def validate_evaluation_lock(path: Path, input_path: Path, pack: list[dict[str, Any]]) -> dict[str, Any]:
    receipt = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "status": "locked_for_single_reveal",
        "input_sha256": file_sha256(input_path),
        "record_count": len(pack),
        "text_hash_grouping_verified": True,
        "within_evaluation_duplicate_groups": 0,
        "development_text_overlap_groups": 0,
        "historical_text_overlap_groups": 0,
        "excluded_key_manifests_verified": True,
    }
    mismatches = [key for key, expected in required.items() if receipt.get(key) != expected]
    if mismatches:
        raise ValueError(f"evaluation lock receipt failed required fields: {mismatches}")
    text_hashes = [row["source_text_sha256"] for row in pack]
    if len(set(text_hashes)) != len(text_hashes):
        raise ValueError("evaluation input contains duplicate full-text hash groups")
    return receipt


def command_prepare(args: argparse.Namespace) -> int:
    private_output_guard(args.output_dir)
    if args.mode == "evaluation" and args.comparison_manifest:
        raise ValueError("configuration comparison manifest is development-only")
    rows = read_rows(args.input)
    if len(rows) != args.expected_count:
        raise ValueError(f"expected {args.expected_count} rows, found {len(rows)}")
    text_column = resolve_text_column(rows, args.text_column)
    pack, errors = normalized_pack(rows, text_column)
    if errors:
        raise ValueError("input audit failed:\n" + "\n".join(errors[:25]))
    evaluation_lock = None
    if args.mode == "evaluation":
        if args.evaluation_lock_receipt is None:
            raise ValueError("evaluation preparation refused: --evaluation-lock-receipt is required")
        evaluation_lock = validate_evaluation_lock(args.evaluation_lock_receipt, args.input, pack)
    comparison_rows: list[dict[str, Any]] | None = None
    comparison_manifest_sha256 = None
    if args.mode == "development" and args.comparison_manifest:
        selected_ids = comparison_ids(args.comparison_manifest)
        pack_by_id = {row["record_id"]: row for row in pack}
        missing_ids = [record_id for record_id in selected_ids if record_id not in pack_by_id]
        if missing_ids:
            raise ValueError(f"L1 comparison manifest contains IDs outside development pack: {missing_ids[:5]}")
        comparison_rows = [pack_by_id[record_id] for record_id in selected_ids]
        comparison_manifest_sha256 = file_sha256(args.comparison_manifest)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    pack_name = f"{args.mode}_{len(pack)}.pack.jsonl"
    pack_path = args.output_dir / pack_name
    write_jsonl(pack_path, pack)
    comparison_path: Path | None = None
    comparison_count = 0
    if comparison_rows is not None:
        comparison_path = args.output_dir / "development_config_compare_80.pack.jsonl"
        write_jsonl(comparison_path, comparison_rows)
        comparison_count = 80
    lengths = [len(row["original_text"]) for row in pack]
    receipt = {
        "version": "local_pack_receipt_v1.0.0",
        "created_at_utc": utc_now(),
        "mode": args.mode,
        "route": "agent_assisted_bounded_development" if args.mode == "development" else "locked_offline_evaluation",
        "input": {"path": str(args.input.resolve()), "sha256": file_sha256(args.input), "text_column": text_column},
        "counts": {"records": len(pack), "unique_job_hash": len({r["record_id"] for r in pack}), "comparison_records": comparison_count},
        "text_readability": {
            "all_nonempty_unicode_strings": True,
            "characters_min": min(lengths),
            "characters_median": statistics.median(lengths),
            "characters_max": max(lengths),
            "characters_total": sum(lengths),
        },
        "outputs": {
            "pack_path": str(pack_path), "pack_sha256": file_sha256(pack_path),
            "comparison_path": str(comparison_path) if comparison_path else None,
            "comparison_sha256": file_sha256(comparison_path) if comparison_path else None,
            "comparison_manifest_sha256": comparison_manifest_sha256,
        },
        "evaluation_lock": {
            "receipt_path": str(args.evaluation_lock_receipt.resolve()) if args.evaluation_lock_receipt else None,
            "receipt_sha256": file_sha256(args.evaluation_lock_receipt) if args.evaluation_lock_receipt else None,
            "lock_id": evaluation_lock.get("lock_id") if evaluation_lock else None,
        },
        "versions": {"schema_sha256": file_sha256(SCHEMA_PATH), "prompt_sha256": file_sha256(PROMPT_PATH)},
        "privacy": {"raw_text_external_transfer": False, "raw_text_written_inside_measurement": False},
        "claims": {"model_labels_generated": False, "batch_api_run": False, "production_l3_started": False},
    }
    receipt_path = args.output_dir / f"{args.mode}_pack_receipt.json"
    write_json(receipt_path, receipt)
    print(receipt_path)
    return 0


def load_source_pack(path: Path) -> list[dict[str, Any]]:
    rows = read_rows(path)
    required = {"record_id", "original_text", "source_text_sha256"}
    for index, row in enumerate(rows):
        if not required <= set(row):
            raise ValueError(f"source pack row {index} lacks {sorted(required - set(row))}")
        if sha256_text(row["original_text"]) != row["source_text_sha256"]:
            raise ValueError(f"source pack row {index} text hash mismatch")
    return rows


def command_validate(args: argparse.Namespace) -> int:
    source_rows = load_source_pack(args.source)
    result = validate_jsonl(source_rows, args.predictions)
    result.update({
        "version": "offline_validation_receipt_v1.0.0",
        "created_at_utc": utc_now(),
        "source_sha256": file_sha256(args.source),
        "predictions_sha256": file_sha256(args.predictions),
    })
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.receipt, result)
    print(args.receipt)
    return 0 if not result["parse_errors"] and not result["record_errors"] and not result["missing_prediction_ids"] else 1


def command_cost(args: argparse.Namespace) -> int:
    rows = load_source_pack(args.source)
    prompt_characters = len(PROMPT_PATH.read_text(encoding="utf-8"))
    input_characters = [len(row["original_text"]) + prompt_characters for row in rows]
    proxy_tokens = [math.ceil(value / args.characters_per_token) for value in input_characters]
    mean_proxy = statistics.mean(proxy_tokens)
    receipt = {
        "version": "development_cost_scale_receipt_v1.0.0",
        "created_at_utc": utc_now(),
        "route": "local_agent_assisted_workload_estimate_or_offline_import",
        "observed_source_records": len(rows),
        "observed_source_sha256": file_sha256(args.source),
        "input_characters_including_prompt": {"total": sum(input_characters), "mean": statistics.mean(input_characters), "min": min(input_characters), "max": max(input_characters)},
        "token_proxy": {
            "method": f"ceil(UTF-8-decoded characters/{args.characters_per_token}); not tokenizer output",
            "total_input_tokens_proxy": sum(proxy_tokens),
            "mean_input_tokens_proxy": mean_proxy,
            "scale_count": args.scale_count,
            "scaled_input_tokens_proxy": math.ceil(mean_proxy * args.scale_count),
        },
        "actual_usage": {"input_tokens": None, "output_tokens": None, "elapsed_seconds": None, "failed_requests": None},
        "billing": {"currency": "USD", "input_price_per_million": None, "output_price_per_million": None, "billed_cost": None},
        "api_state": "unavailable_no_api",
        "production_l3_started": False,
        "caveat": "Scale is a local workload proxy from actual text lengths. It is not an API cost benchmark, quote, bill, or completed model run."
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.receipt, receipt)
    print(args.receipt)
    return 0


def command_gate(args: argparse.Namespace) -> int:
    gate = json.loads(args.config.read_text(encoding="utf-8"))
    allowed = gate.get("production_l3_allowed") is True and gate.get("status") == "available_verified"
    result = {
        "version": "batch_gate_check_v1.0.0", "checked_at_utc": utc_now(),
        "production_l3_allowed": allowed, "status": gate.get("status"), "reason": gate.get("reason")
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if allowed else 2


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    sub = root.add_subparsers(dest="command", required=True)
    prepare = sub.add_parser("prepare", help="audit actual local text and prepare a private bounded pack")
    prepare.add_argument("--mode", choices=("development", "evaluation"), required=True)
    prepare.add_argument("--input", type=Path, required=True)
    prepare.add_argument("--output-dir", type=Path, required=True)
    prepare.add_argument("--expected-count", type=int, default=200)
    prepare.add_argument("--comparison-manifest", type=Path)
    prepare.add_argument("--evaluation-lock-receipt", type=Path)
    prepare.add_argument("--text-column")
    prepare.set_defaults(func=command_prepare)
    validate = sub.add_parser("validate", help="validate offline JSONL outputs against exact local source")
    validate.add_argument("--source", type=Path, required=True)
    validate.add_argument("--predictions", type=Path, required=True)
    validate.add_argument("--receipt", type=Path, required=True)
    validate.set_defaults(func=command_validate)
    cost = sub.add_parser("cost", help="write a local length/token-proxy scale receipt")
    cost.add_argument("--source", type=Path, required=True)
    cost.add_argument("--receipt", type=Path, required=True)
    cost.add_argument("--characters-per-token", type=float, default=4.0)
    cost.add_argument("--scale-count", type=int, default=40300)
    cost.set_defaults(func=command_cost)
    gate = sub.add_parser("gate", help="check recorded batch availability without making a request")
    gate.add_argument("--config", type=Path, default=GATE_PATH)
    gate.set_defaults(func=command_gate)
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        return args.func(args)
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
