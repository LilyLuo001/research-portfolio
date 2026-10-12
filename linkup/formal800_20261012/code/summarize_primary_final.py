#!/usr/bin/env python3
"""Compare same-sample primary-only and final Formal800 aggregate outputs.

This script reads public aggregates only. It never relabels records or
re-estimates outcomes. Outer joins preserve cells that enter or leave support
after audit-conflict masking and bounded root adjudication.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any


TABLES = (
    ("COMPARISON_1_EXPERIENCE.csv", "Q1_PRIMARY_VS_FINAL.csv",
     ("estimand", "scope", "measure", "group_a", "group_b")),
    ("COMPARISON_2_ENTRY_DUTY.csv", "Q2_PRIMARY_VS_FINAL.csv",
     ("estimand", "scope", "technology_scope", "entry_definition", "duty_dimension")),
    ("T3_OLD_ARM_TO_SEMANTIC_TRANSITION.csv", "T3_PRIMARY_VS_FINAL.csv",
     ("estimand", "old_candidate_arm", "reviewed_semantic_group")),
    ("T1_OCCUPATION_SUPPORT.csv", "SUPPORT_PRIMARY_VS_FINAL.csv",
     ("occupation_major", "semantic_group")),
)
OWNED_OUTPUTS = tuple(item[1] for item in TABLES)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            value.update(block)
    return value.hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is None:
            raise RuntimeError(f"aggregate has no header: {path}")
        return list(reader.fieldnames), list(reader)


def write_csv(path: Path, fields: list[str], rows: list[dict[str, Any]]) -> None:
    temporary = Path(str(path) + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def numeric(value: Any) -> float | None:
    if value in (None, "", "None", "null", "NA"):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def indexed(rows: list[dict[str, str]], keys: tuple[str, ...], path: Path) -> dict[tuple[str, ...], dict[str, str]]:
    result = {}
    for row in rows:
        key = tuple(row.get(name, "") for name in keys)
        if key in result:
            raise RuntimeError(f"duplicate comparison key in {path}: {key}")
        result[key] = row
    return result


def outer_compare(baseline_path: Path, final_path: Path, output_path: Path,
                  keys: tuple[str, ...]) -> dict[str, int]:
    baseline_fields, baseline_rows = read_csv(baseline_path)
    final_fields, final_rows = read_csv(final_path)
    if any(key not in baseline_fields or key not in final_fields for key in keys):
        raise RuntimeError(f"comparison key missing from {baseline_path.name}")
    baseline = indexed(baseline_rows, keys, baseline_path)
    final = indexed(final_rows, keys, final_path)
    value_fields = [name for name in baseline_fields + final_fields if name not in keys]
    # Preserve first-seen source order without requiring identical schemas.
    value_fields = list(dict.fromkeys(value_fields))
    output_fields = [*keys, "row_status"]
    for name in value_fields:
        output_fields.extend(("baseline_" + name, "final_" + name, "delta_final_minus_baseline_" + name))
    output_rows = []
    statuses = {"both": 0, "baseline_only": 0, "final_only": 0}
    for key in sorted(set(baseline) | set(final)):
        before, after = baseline.get(key), final.get(key)
        status = "both" if before is not None and after is not None else "baseline_only" if before is not None else "final_only"
        statuses[status] += 1
        out: dict[str, Any] = {name: value for name, value in zip(keys, key)}
        out["row_status"] = status
        for name in value_fields:
            before_value = None if before is None else before.get(name)
            after_value = None if after is None else after.get(name)
            before_number, after_number = numeric(before_value), numeric(after_value)
            out["baseline_" + name] = before_value
            out["final_" + name] = after_value
            out["delta_final_minus_baseline_" + name] = (
                after_number - before_number
                if before_number is not None and after_number is not None else None)
        output_rows.append(out)
    write_csv(output_path, output_fields, output_rows)
    return {"rows": len(output_rows), **statuses}


def require_receipt(directory: Path) -> dict[str, Any]:
    receipt_path = directory / "ANALYSIS_RECEIPT.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("status") != "complete":
        raise RuntimeError(f"analysis receipt is not complete: {receipt_path}")
    for source_name, _, _ in TABLES:
        source = directory / source_name
        if receipt.get("outputs", {}).get(source_name) != digest(source):
            raise RuntimeError(f"aggregate does not bind analysis receipt: {source}")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--final-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    receipt_path = args.output_dir / "PRIMARY_VS_FINAL_RECEIPT.json"
    if receipt_path.exists():
        receipt_path.unlink()
    for name in OWNED_OUTPUTS:
        path = args.output_dir / name
        if path.exists():
            path.unlink()

    baseline_receipt = require_receipt(args.baseline_dir)
    final_receipt = require_receipt(args.final_dir)
    for field in ("version", "code_sha256", "main_weight", "estimand"):
        if baseline_receipt.get(field) != final_receipt.get(field):
            raise RuntimeError(f"baseline and final analysis receipts differ on {field}")
    for field in ("sampled_ad_map_sha256",):
        if baseline_receipt.get("inputs", {}).get(field) != final_receipt.get("inputs", {}).get(field):
            raise RuntimeError(f"baseline and final use different {field}")
    for field in ("eligible_frame_ads", "sampled_ads", "validated_context_records"):
        if baseline_receipt.get("counts", {}).get(field) != final_receipt.get("counts", {}).get(field):
            raise RuntimeError(f"baseline and final differ on {field}")

    summaries = {}
    for source_name, output_name, keys in TABLES:
        summaries[output_name] = outer_compare(
            args.baseline_dir / source_name, args.final_dir / source_name,
            args.output_dir / output_name, keys)

    receipt = {
        "version": "formal800-primary-vs-final-summary-v1",
        "status": "complete",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "code_sha256": digest(Path(__file__)),
        "same_sample_contract": {
            "eligible_frame_ads": final_receipt["counts"]["eligible_frame_ads"],
            "sampled_ads": final_receipt["counts"]["sampled_ads"],
            "validated_context_records": final_receipt["counts"]["validated_context_records"],
            "sampled_ad_map_sha256": final_receipt["inputs"]["sampled_ad_map_sha256"],
            "analysis_code_sha256": final_receipt["code_sha256"],
            "main_weight": final_receipt["main_weight"],
        },
        "inputs": {
            "baseline_analysis_receipt_sha256": digest(args.baseline_dir / "ANALYSIS_RECEIPT.json"),
            "final_analysis_receipt_sha256": digest(args.final_dir / "ANALYSIS_RECEIPT.json"),
        },
        "tables": summaries,
        "outputs": {name: digest(args.output_dir / name) for name in OWNED_OUTPUTS},
        "interpretation": (
            "Same-sample descriptive changes after bounded root adjudication and field-level masking "
            "of observed blind-review conflicts. Deltas are not error-correction estimates or accuracy "
            "measures. Technology classification, comparison membership, and common-support cells may change."
        ),
        "missing_cell_policy": "outer join; baseline_only and final_only rows retained; missing values are never zero-filled",
    }
    temporary = Path(str(receipt_path) + ".tmp")
    temporary.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, receipt_path)


if __name__ == "__main__":
    main()
