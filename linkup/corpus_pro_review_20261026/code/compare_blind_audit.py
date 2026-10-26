#!/usr/bin/env python3
"""One-time mechanical comparison of 12 blind audit records with primary reviews.

Runs only under a real SLURM allocation. Private rows and quotations remain on
SCNet; the public summary has counts only and makes no accuracy claim.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re


OUTCOME_FIELDS = ("experience_outcomes", "entry_outcomes", "responsibility_outcomes")
CLAUSE_FIELDS = ("object", "strength", "conditionality", "years_min", "years_max",
                 "years_relation", "alternative_group", "alternative_branch")


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_new(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
        stream.write("\n")
    os.chmod(path, 0o600)


def clause_structure(row: dict) -> Counter:
    return Counter(tuple(clause[field] for field in CLAUSE_FIELDS)
                   for clause in row["experience_clauses"])


def normalized_detail(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().casefold())


def clause_detail(row: dict) -> Counter:
    return Counter((tuple(clause[field] for field in CLAUSE_FIELDS),
                    normalized_detail(clause["object_detail"]))
                   for clause in row["experience_clauses"])


def read_index(paths: list[Path], first_only: bool = False) -> dict[str, dict]:
    index: dict[str, dict] = {}
    for path in paths:
        rows = read_jsonl(path)
        if first_only:
            if not rows:
                raise RuntimeError("primary review file is empty")
            rows = rows[:1]
        for row in rows:
            record_id = row["record_id"]
            if record_id in index:
                raise RuntimeError("duplicate record_id in review files")
            index[record_id] = row
    return index


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reviews-dir", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    job_id = os.environ.get("SLURM_JOB_ID")
    if not job_id or not job_id.isdecimal() or args.output_root.name != job_id:
        raise RuntimeError("actual SLURM_JOB_ID/output-root required")
    primary_paths = [args.reviews_dir / f"batch001_packet_{i:04d}_PRIMARY.jsonl"
                     for i in range(1, 13)]
    audit_paths = [args.reviews_dir / f"batch001_AUDIT_{i:02d}.jsonl"
                   for i in range(1, 4)]
    if not all(path.is_file() for path in primary_paths + audit_paths):
        raise RuntimeError("review input absent")
    primary = read_index(primary_paths, first_only=True)
    audit = read_index(audit_paths)
    if len(primary) != 12 or len(audit) != 12 or set(primary) != set(audit):
        raise RuntimeError("expected exactly 12 aligned blind records")
    differences = []
    counts = Counter()
    for record_id in sorted(primary):
        p, a = primary[record_id], audit[record_id]
        if p["context_sha256"] != a["context_sha256"]:
            raise RuntimeError("context SHA mismatch")
        outcome_changes = []
        for family in OUTCOME_FIELDS:
            if set(p[family]) != set(a[family]):
                raise RuntimeError("outcome dimensions differ")
            for dimension in sorted(p[family]):
                if p[family][dimension] != a[family][dimension]:
                    outcome_changes.append({"family": family, "dimension": dimension,
                                            "primary": p[family][dimension],
                                            "audit": a[family][dimension]})
                    counts[family + "." + dimension] += 1
        structure_diff = clause_structure(p) != clause_structure(a)
        detail_diff = clause_detail(p) != clause_detail(a)
        alternatives_diff = p["qualification_alternatives"] != a["qualification_alternatives"]
        entry_item_diff = p["entry_items"] != a["entry_items"]
        if outcome_changes or structure_diff or detail_diff or alternatives_diff or entry_item_diff:
            differences.append({
                "record_id": record_id,
                "context_sha256": p["context_sha256"],
                "outcome_changes": outcome_changes,
                "experience_clause_structure_diff": structure_diff,
                "experience_clause_detail_diff_candidate": detail_diff,
                "qualification_alternatives_diff_candidate": alternatives_diff,
                "entry_items_diff_candidate": entry_item_diff,
                "primary": {key: p[key] for key in OUTCOME_FIELDS +
                            ("experience_clauses", "qualification_alternatives", "entry_items")},
                "audit": {key: a[key] for key in OUTCOME_FIELDS +
                          ("experience_clauses", "qualification_alternatives", "entry_items")},
            })
        if outcome_changes:
            counts["records_with_outcome_changes"] += 1
        if structure_diff:
            counts["records_with_clause_structure_changes"] += 1
        if detail_diff:
            counts["records_with_clause_detail_candidates"] += 1
        if alternatives_diff:
            counts["records_with_alternative_candidates"] += 1
        if entry_item_diff:
            counts["records_with_entry_item_candidates"] += 1
    args.output_root.mkdir(parents=True, exist_ok=False)
    private = args.output_root / "private"
    public = args.output_root / "public"
    private.mkdir(mode=0o700)
    public.mkdir()
    write_new(private / "BLIND_AUDIT_DIFFERENCES_PRIVATE.json", differences)
    aggregate = {
        "version": "blind-audit-difference-v1",
        "slurm_job_id": job_id,
        "aligned_records": 12,
        "records_with_any_candidate_difference": len(differences),
        "counts": dict(sorted(counts.items())),
        "claim_boundary": "Mechanical paired comparison; candidate wording differences require human interpretation; no accuracy or corpus-level inference",
    }
    write_new(public / "BLIND_AUDIT_AGGREGATE_PUBLIC.json", aggregate)
    print(json.dumps(aggregate, sort_keys=True))


if __name__ == "__main__":
    main()
