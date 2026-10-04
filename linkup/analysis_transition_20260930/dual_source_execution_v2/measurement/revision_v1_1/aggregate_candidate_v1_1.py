#!/usr/bin/env python3
"""Build sanitized candidate aggregates with conditional tenure separated."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from validate_extraction_v1_1 import validate_jsonl


OBJECTS = ("general_work", "occupation_task", "industry_domain", "specific_tool")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def duration_payload(mention: dict[str, Any]) -> dict[str, Any]:
    duration = mention["duration"]
    return {key: duration[key] for key in ("interpretation", "stated_value", "lower", "upper")}


def summarize(source: Path, predictions: Path) -> dict[str, Any]:
    source_rows = read_jsonl(source)
    validation = validate_jsonl(source_rows, predictions)
    if not validation["passes_0_99_structure_gate"] or validation["valid_records"] != validation["source_records"]:
        raise ValueError("candidate aggregation requires every source row to pass v1.1 structure/evidence validation")
    rows = read_jsonl(predictions)
    state_counts = {obj: Counter() for obj in OBJECTS}
    unconditional_candidate: dict[str, list[dict[str, Any]]] = defaultdict(list)
    education_substitution: dict[str, list[dict[str, Any]]] = defaultdict(list)
    other_conditional: dict[str, list[dict[str, Any]]] = defaultdict(list)
    excluded_mode = Counter()
    explicit_experience_without_duration = Counter()
    unresolved_scope_duration = Counter()
    for row in rows:
        for finding in row["experience_findings"]:
            obj = finding["object"]
            state_counts[obj][finding["state"]] += 1
            for mention in finding["mentions"]:
                if mention["condition_mode"] != "prior_experience":
                    excluded_mode[mention["condition_mode"]] += 1
                    continue
                if mention["duration"] is None:
                    explicit_experience_without_duration[obj] += 1
                    continue
                scope = mention["qualification_scope"]
                payload = duration_payload(mention)
                if scope == "unconditional":
                    unconditional_candidate[obj].append(payload)
                elif scope == "education_substitution":
                    education_substitution[obj].append(payload)
                elif scope == "other_conditional":
                    other_conditional[obj].append(payload)
                else:
                    unresolved_scope_duration[obj] += 1
    return {
        "version": "candidate_year_aggregate_v1.1.0",
        "status": "development_candidate_not_validated_measurement",
        "records": len(rows),
        "experience_state_counts": {obj: dict(sorted(state_counts[obj].items())) for obj in OBJECTS},
        "candidate_unconditional_prior_experience_year_mentions": {obj: unconditional_candidate[obj] for obj in OBJECTS},
        "conditional_education_substitution_year_mentions": {obj: education_substitution[obj] for obj in OBJECTS},
        "conditional_other_year_mentions": {obj: other_conditional[obj] for obj in OBJECTS},
        "unresolved_scope_year_mention_counts": dict(sorted(unresolved_scope_duration.items())),
        "prior_experience_mentions_without_explicit_duration_counts": dict(sorted(explicit_experience_without_duration.items())),
        "excluded_non_prior_experience_mode_counts": dict(sorted(excluded_mode.items())),
        "zero_policy": "not_mentioned, unresolved, insufficient_text, no explicit duration, and excluded modes are never recoded to zero",
        "candidate_bucket_rule": "Only unconditional prior_experience durations enter this candidate bucket; conditional substitutions remain separate. Structural validity and scope filtering do not constitute formal production-metric acceptance.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = summarize(args.source, args.predictions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
