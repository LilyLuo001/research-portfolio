#!/usr/bin/env python3
"""Expand short offline labels into extraction_v1 without changing semantics."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from run_local import read_rows, write_json, write_jsonl
from validate_extraction import sha256_text, validate_record


def locate_quote(text: str, value: Any, span_id: str) -> dict[str, Any]:
    if isinstance(value, str):
        quote, occurrence = value, None
    elif isinstance(value, dict):
        quote, occurrence = value.get("quote"), value.get("occurrence")
    else:
        raise ValueError(f"{span_id}: quote must be a string or quote/occurrence object")
    if not isinstance(quote, str) or not quote:
        raise ValueError(f"{span_id}: quote is empty")
    starts: list[int] = []
    position = text.find(quote)
    while position >= 0:
        starts.append(position)
        position = text.find(quote, position + 1)
    if not starts:
        raise ValueError(f"{span_id}: quote is not an exact source substring")
    if len(starts) > 1 and occurrence is None:
        raise ValueError(f"{span_id}: quote occurs {len(starts)} times; supply zero-based occurrence or label unresolved")
    selected = 0 if occurrence is None else occurrence
    if not isinstance(selected, int) or selected < 0 or selected >= len(starts):
        raise ValueError(f"{span_id}: occurrence is outside 0..{len(starts) - 1}")
    start = starts[selected]
    return {"span_id": span_id, "start": start, "end": start + len(quote), "text": quote}


def expand_record(compact: dict[str, Any], source_text: str) -> dict[str, Any]:
    experiences = []
    for finding_index, source_finding in enumerate(compact["experience_findings"]):
        finding = dict(source_finding)
        mentions = []
        for mention_index, source_mention in enumerate(finding.pop("mentions", [])):
            mention = dict(source_mention)
            quote = mention.pop("quote")
            span_id = f"e{finding_index + 1}m{mention_index + 1}"
            mention["evidence"] = [locate_quote(source_text, quote, span_id)]
            duration = mention.get("duration")
            if duration is not None:
                duration = dict(duration)
                duration["evidence_span_id"] = span_id
                mention["duration"] = duration
            mentions.append(mention)
        state_quote = finding.pop("quote", None)
        finding["state_evidence"] = [] if state_quote is None else [locate_quote(source_text, state_quote, f"e{finding_index + 1}s")]
        finding["mentions"] = mentions
        experiences.append(finding)
    technologies = []
    for finding_index, source_finding in enumerate(compact["technology_findings"]):
        finding = dict(source_finding)
        quote = finding.pop("quote", None)
        finding["evidence"] = [] if quote is None else [locate_quote(source_text, quote, f"t{finding_index + 1}")]
        technologies.append(finding)
    return {
        "schema_version": "linkup_measurement_v1.0.0",
        "prompt_version": "linkup_extraction_prompt_v1.0.0",
        "record_id": compact["record_id"],
        "source_text_sha256": sha256_text(source_text),
        "record_text_state": compact["record_text_state"],
        "experience_findings": experiences,
        "technology_findings": technologies,
        "record_note": compact.get("record_note"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--compact-labels", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    source_rows = read_rows(args.source)
    seen_ids: set[str] = set()
    for index, row in enumerate(source_rows):
        if not {"record_id", "original_text"} <= set(row):
            raise ValueError(f"source row {index} requires record_id and original_text")
        record_id = str(row["record_id"])
        if not record_id or record_id in seen_ids:
            raise ValueError(f"source row {index} has empty or duplicate record_id")
        if not isinstance(row["original_text"], str):
            raise ValueError(f"source row {index} original_text is not a string")
        seen_ids.add(record_id)
    source_by_id = {str(row["record_id"]): row["original_text"] for row in source_rows}
    expanded, errors = [], {}
    with args.compact_labels.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            record_id = f"line-{line_number}"
            try:
                compact = json.loads(line)
                record_id = str(compact.get("record_id", record_id))
                if record_id not in source_by_id:
                    raise ValueError("record_id has no source row")
                record = expand_record(compact, source_by_id[record_id])
                validation_errors = validate_record(record, source_by_id[record_id], record_id)
                if validation_errors:
                    raise ValueError("; ".join(validation_errors))
                expanded.append(record)
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                errors[record_id] = str(exc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output, expanded)
    receipt = {
        "version": "compact_label_expansion_v1.0.0",
        "source_records": len(source_rows), "expanded_records": len(expanded), "errors": errors,
        "semantic_change": False,
        "note": "Program filled source hash and unique quote offsets only; it did not infer or revise labels."
    }
    write_json(args.receipt, receipt)
    print(args.receipt)
    return 0 if not errors and len(expanded) == len(source_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
