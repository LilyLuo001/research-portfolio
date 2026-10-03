#!/usr/bin/env python3
"""R0 reference extractor. It is deliberately inert until actual mappings are verified.

It samples persons deterministically, then extracts every career row for each selected
person.  It supports CSV only as a portable reference implementation; source owners may
replace the reader after recording an equivalent schema/cardinality audit.  Do not run
against individual data unless --protected-output is an approved non-repository path.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path


def require(value, label):
    if value is None or value == "":
        raise ValueError(f"missing mapping: {label}")
    return value


def rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def header(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return set(csv.DictReader(handle).fieldnames or [])


def rank(person_id, seed):
    return hashlib.sha256(f"{seed}:{person_id}".encode()).hexdigest()


def is_inside_git_worktree(path):
    """Reject a raw-output destination nested in any Git worktree."""
    resolved = path.resolve()
    return any((parent / ".git").exists() for parent in (resolved, *resolved.parents))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--protected-output", required=True)
    parser.add_argument("--sample-size", type=int, default=10000)
    parser.add_argument("--seed", default="revelio_r0_v2_20261004")
    args = parser.parse_args()
    if args.sample_size <= 0:
        raise ValueError("sample-size must be positive")
    mapping = json.loads(Path(args.mapping).read_text())
    if mapping.get("schema_verified") is not True:
        raise ValueError("schema_verified must be true after the source schema audit")
    person = mapping["person_frame"]
    career = mapping["career"]
    out_cfg = mapping["output"]
    if out_cfg.get("allow_raw_extract") is not True:
        raise ValueError("allow_raw_extract must be explicitly true for an approved protected run")
    approved_destination = require(out_cfg.get("protected_destination"), "output.protected_destination")
    if Path(args.protected_output).resolve() != Path(approved_destination).resolve():
        raise ValueError("--protected-output must equal the mapping's approved protected_destination")
    if is_inside_git_worktree(Path(approved_destination)):
        raise ValueError("protected_destination must be outside every Git worktree")
    if person.get("format") not in (None, "csv") or career.get("format") not in (None, "csv"):
        raise ValueError("this reference implementation supports CSV only")
    person_path = require(person.get("path"), "person_frame.path")
    career_path = require(career.get("path"), "career.path")
    pid = require(person.get("person_id_column"), "person_frame.person_id_column")
    career_pid = require(career.get("person_id_column"), "career.person_id_column")
    person_header = header(person_path)
    career_header = header(career_path)
    if pid not in person_header:
        raise ValueError("person_frame.person_id_column is absent from the source header")
    if career_pid not in career_header:
        raise ValueError("career.person_id_column is absent from the source header")
    for semantic, actual in career.get("required_columns", {}).items():
        actual = require(actual, f"career.required_columns.{semantic}")
        if actual not in career_header:
            raise ValueError(f"mapped career column is absent: {semantic}")
    eligibility = person.get("eligibility_column")
    eligible_value = person.get("eligible_value")
    if bool(eligibility) != (eligible_value is not None):
        raise ValueError("eligibility_column and eligible_value must be supplied together, or both omitted")
    if eligibility and eligibility not in person_header:
        raise ValueError("person_frame.eligibility_column is absent from the source header")
    candidates = set()
    frame_person_ids = set()
    duplicate_frame_person_ids = 0
    missing_frame_id = 0
    for row in rows(person_path):
        value = row.get(pid, "").strip()
        if not value:
            missing_frame_id += 1
            continue
        if value in frame_person_ids:
            duplicate_frame_person_ids += 1
            continue
        frame_person_ids.add(value)
        if eligibility and row.get(eligibility) != str(eligible_value):
            continue
        candidates.add(value)
    if duplicate_frame_person_ids:
        raise ValueError(f"person frame has {duplicate_frame_person_ids} duplicate stable person-ID rows")
    selected = sorted(candidates, key=lambda x: rank(x, args.seed))[:args.sample_size]
    selected_set = set(selected)
    extracted = []
    career_rows_by_person = {value: 0 for value in selected}
    career_missing_person_id = 0
    for row in rows(career_path):
        value = row.get(career_pid, "").strip()
        if not value:
            career_missing_person_id += 1
        elif value in selected_set:
            extracted.append(row)
            career_rows_by_person[value] += 1
    destination = Path(approved_destination)
    destination.mkdir(parents=True, exist_ok=True)
    with (destination / "sampled_all_careers.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(extracted[0]) if extracted else [career_pid])
        writer.writeheader()
        writer.writerows(extracted)
    with (destination / "sampled_person_keys.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=[pid, "visible_career_row_count"])
        writer.writeheader()
        writer.writerows({pid: value, "visible_career_row_count": career_rows_by_person[value]} for value in selected)
    receipt = {
        "sample_size_requested": args.sample_size,
        "distinct_eligible_persons": len(candidates),
        "selected_persons": len(selected),
        "career_rows_extracted": len(extracted),
        "persons_with_zero_career_rows": sum(count == 0 for count in career_rows_by_person.values()),
        "missing_person_id_in_frame": missing_frame_id,
        "missing_person_id_in_career": career_missing_person_id,
        "seed": args.seed,
        "privacy_note": "No identifiers are included in this receipt."
    }
    (destination / "r0_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt))


if __name__ == "__main__":
    main()
