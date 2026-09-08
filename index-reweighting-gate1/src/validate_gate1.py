#!/usr/bin/env python3
"""Validate the structural and provenance contract for the Gate 1 package.

This script deliberately validates evidence hygiene, not the truth of an
institutional claim. Truth claims still require inspection of the cited raw
locator or public primary source.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


SECRET_PATTERNS = (
    re.compile(r"github_pat_[A-Za-z0-9_]+"),
    re.compile(r"\bghp_[A-Za-z0-9]+"),
)


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def validate_package(root: Path, contract_path: Path) -> list[str]:
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    for directory in contract["required_directories"]:
        if not (root / directory).is_dir():
            errors.append(f"missing required directory: {directory}")

    for document in contract["required_documents"]:
        path = root / document
        if not path.is_file() or not path.read_text(encoding="utf-8").strip():
            errors.append(f"missing or empty required document: {document}")

    observed_keys: set[str] = set()
    for filename, required_columns in contract["required_files"].items():
        path = root / filename
        if not path.is_file():
            errors.append(f"missing required table: {filename}")
            continue
        fields, rows = read_rows(path)
        missing_columns = [column for column in required_columns if column not in fields]
        if missing_columns:
            errors.append(f"{filename}: missing columns {missing_columns}")
        if not rows:
            errors.append(f"{filename}: contains no audit rows")
            continue

        local_keys: set[str] = set()
        for number, row in enumerate(rows, start=2):
            key = (row.get("evidence_key") or "").strip()
            if not key:
                errors.append(f"{filename}:{number}: blank evidence_key")
            elif key in local_keys:
                errors.append(f"{filename}:{number}: duplicate evidence_key {key}")
            else:
                local_keys.add(key)
                observed_keys.add(key)
            if not (row.get("status") or "").strip():
                errors.append(f"{filename}:{number}: blank status")

            if filename == "assignment_doses_and_evidence.csv":
                grade = (row.get("evidence_grade") or "").strip()
                if grade not in contract["allowed_assignment_grades"]:
                    errors.append(f"{filename}:{number}: invalid evidence_grade {grade!r}")

            if "source_url" in fields:
                url = (row.get("source_url") or "").strip()
                if url and not url.startswith(("https://", "http://")):
                    errors.append(f"{filename}:{number}: malformed source_url {url!r}")

    decision_path = root / "FINAL_DECISION.md"
    if decision_path.is_file():
        decision = decision_path.read_text(encoding="utf-8")
        selected = [
            recommendation
            for recommendation in contract["allowed_recommendations"]
            if recommendation in decision
        ]
        if len(selected) != 1:
            errors.append(
                "FINAL_DECISION.md must contain exactly one permitted recommendation; "
                f"found {len(selected)}"
            )

    for path in root.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for pattern in SECRET_PATTERNS:
            if pattern.search(content):
                errors.append(f"possible credential material in {path.relative_to(root)}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--contract", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    contract = args.contract or root / "config" / "output_contract.json"
    errors = validate_package(root, contract)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PASS: Gate 1 package contract validated at {root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
