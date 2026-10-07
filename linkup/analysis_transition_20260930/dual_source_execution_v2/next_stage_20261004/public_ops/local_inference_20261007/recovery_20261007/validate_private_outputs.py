#!/usr/bin/env python3
"""Validate raw model JSON and optionally repair exact offsets without semantic edits."""

import argparse
import json
import sys
from pathlib import Path


def read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--measurement-dir", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    sys.path.insert(0, str(args.measurement_dir))
    from validate_extraction_v1_1 import validate_record
    from expand_compact_labels_v1_1 import locate_quote

    source_rows = read_jsonl(args.source)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    final_rows = []
    receipts = []
    for index, source in enumerate(source_rows, 1):
        raw_path = args.raw_dir / f"record_{index:02d}.raw.json"
        raw_text = raw_path.read_text(encoding="utf-8")
        entry = {"index": index, "strict_raw_parse": False, "strict_raw_valid": False,
                 "strict_raw_errors": [], "raw_parse": False, "runtime_envelope_removed": False, "raw_valid": False,
                 "offset_repair_attempted": False, "offset_repair_applied": False,
                 "final_valid": False, "errors": []}
        try:
            strict_record = json.loads(raw_text)
            entry["strict_raw_parse"] = True
            strict_errors = validate_record(strict_record, source["original_text"], str(source["record_id"]))
            entry["strict_raw_errors"] = strict_errors
            entry["strict_raw_valid"] = not strict_errors
        except json.JSONDecodeError as exc:
            entry["strict_raw_errors"] = [f"raw JSON parse: {exc}"]
        try:
            record, consumed = json.JSONDecoder().raw_decode(raw_text.lstrip())
            trailing = raw_text.lstrip()[consumed:].strip()
            if trailing:
                if trailing != "[end of text]":
                    raise json.JSONDecodeError("unexpected non-JSON runtime output", raw_text, consumed)
                entry["runtime_envelope_removed"] = True
            entry["raw_parse"] = True
        except json.JSONDecodeError as exc:
            entry["errors"].append(f"raw JSON parse: {exc}")
            receipts.append(entry)
            continue
        errors = validate_record(record, source["original_text"], str(source["record_id"]))
        if not errors:
            entry["raw_valid"] = True
            entry["final_valid"] = True
            final_rows.append(record)
            receipts.append(entry)
            continue

        entry["errors"].extend(errors)
        entry["offset_repair_attempted"] = True
        try:
            text = source["original_text"]
            spans = []
            for finding in record["experience_findings"]:
                spans.extend(finding["state_evidence"])
                for mention in finding["mentions"]:
                    spans.extend(mention["evidence"])
                    if mention["condition_quote"] is not None:
                        spans.append(mention["condition_quote"])
            for finding in record["technology_findings"]:
                spans.extend(finding["evidence"])
            for span in spans:
                corrected = locate_quote(text, span["text"], span["span_id"])
                span["start"], span["end"] = corrected["start"], corrected["end"]
            repaired_errors = validate_record(record, text, str(source["record_id"]))
            if repaired_errors:
                entry["errors"].extend(f"after offset repair: {value}" for value in repaired_errors)
            else:
                entry["offset_repair_applied"] = True
                entry["final_valid"] = True
                final_rows.append(record)
        except (KeyError, TypeError, ValueError) as exc:
            entry["errors"].append(f"offset repair refused: {type(exc).__name__}: {exc}")
        receipts.append(entry)

    (args.output_dir / "validated_predictions.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in final_rows),
        encoding="utf-8",
    )
    (args.output_dir / "validator_receipt.json").write_text(json.dumps({
        "source_records": len(source_rows),
        "strict_raw_parse_records": sum(item["strict_raw_parse"] for item in receipts),
        "strict_raw_valid_records": sum(item["strict_raw_valid"] for item in receipts),
        "raw_parse_records": sum(item["raw_parse"] for item in receipts),
        "runtime_envelopes_removed": sum(item["runtime_envelope_removed"] for item in receipts),
        "raw_valid_records": sum(item["raw_valid"] for item in receipts),
        "offset_repairs_applied": sum(item["offset_repair_applied"] for item in receipts),
        "valid_records": sum(item["final_valid"] for item in receipts),
        "all_valid": bool(receipts) and all(item["final_valid"] for item in receipts),
        "mechanical_repair_scope": "Only start/end offsets were recomputed from unchanged exact quote text; ambiguous or absent quotes were refused. No conflicting field was cleared or overwritten.",
        "serialization_scope": "The exact llama.cpp trailing marker [end of text] may be removed after preserving the raw output; any other trailing content is refused.",
        "records": receipts,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if receipts and all(item["final_valid"] for item in receipts) else 1


if __name__ == "__main__":
    raise SystemExit(main())
