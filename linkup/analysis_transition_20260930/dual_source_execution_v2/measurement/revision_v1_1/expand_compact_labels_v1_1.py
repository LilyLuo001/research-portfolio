#!/usr/bin/env python3
"""Add exact offsets and hashes to compact v1.1 labels without changing semantics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from validate_extraction_v1_1 import sha256_text, validate_record


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


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
            evidence_id = f"e{finding_index + 1}m{mention_index + 1}"
            mention["evidence"] = [locate_quote(source_text, quote, evidence_id)]
            condition = mention.pop("condition_quote", None)
            mention["condition_quote"] = None if condition is None else locate_quote(source_text, condition, evidence_id + "c")
            if mention.get("duration") is not None:
                duration = dict(mention["duration"])
                duration["evidence_span_id"] = evidence_id
                mention["duration"] = duration
            mentions.append(mention)
        state_quote = finding.pop("quote", None)
        finding["state_evidence"] = [] if state_quote is None else [locate_quote(source_text, state_quote, f"e{finding_index + 1}s")]
        finding["mentions"] = mentions
        experiences.append(finding)
    technologies = []
    for index, source_finding in enumerate(compact["technology_findings"]):
        finding = dict(source_finding)
        quote = finding.pop("quote", None)
        finding["evidence"] = [] if quote is None else [locate_quote(source_text, quote, f"t{index + 1}")]
        technologies.append(finding)
    return {
        "schema_version": "linkup_measurement_v1.1.0",
        "prompt_version": "linkup_extraction_prompt_v1.1.0",
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
    source_rows = read_jsonl(args.source)
    source_by_id = {str(row["record_id"]): row["original_text"] for row in source_rows}
    if len(source_by_id) != len(source_rows) or any(not isinstance(text, str) for text in source_by_id.values()):
        raise ValueError("source requires unique record_id and string original_text")
    compact_rows = read_jsonl(args.compact_labels)
    compact_ids = [str(row.get("record_id", "")) for row in compact_rows]
    if "" in compact_ids or len(set(compact_ids)) != len(compact_ids):
        raise ValueError("compact labels require unique nonempty record_id")
    missing = sorted(set(source_by_id) - set(compact_ids))
    extra = sorted(set(compact_ids) - set(source_by_id))
    if missing or extra:
        raise ValueError(f"compact/source record_id sets differ: missing={missing}, extra={extra}")
    expanded, failures = [], []
    for line_number, compact in enumerate(compact_rows, 1):
        record_id = str(compact.get("record_id", f"line-{line_number}"))
        try:
            if record_id not in source_by_id:
                raise ValueError("record_id has no source row")
            record = expand_record(compact, source_by_id[record_id])
            errors = validate_record(record, source_by_id[record_id], record_id)
            if errors:
                raise ValueError("; ".join(errors))
            expanded.append(record)
        except (KeyError, TypeError, ValueError) as exc:
            failures.append({"record_id": record_id, "stage": "expand_or_validate", "error_type": type(exc).__name__, "message": str(exc)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output, expanded)
    args.receipt.write_text(json.dumps({
        "version": "compact_label_expansion_v1.1.0",
        "source_records": len(source_rows), "expanded_records": len(expanded), "failed_records": len(failures),
        "failures": failures, "semantic_change": False,
        "note": "Mechanical expansion filled exact offsets, hashes, span IDs, and duration references only."
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if not failures and len(expanded) == len(source_rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
