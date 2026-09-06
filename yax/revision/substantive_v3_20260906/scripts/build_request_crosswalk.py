#!/usr/bin/env python3
"""Expand the immutable requirement seed into an atomic acceptance-check map."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


FIELDS = (
    "atomic_id", "requirement_id", "title", "atomic_request", "source_refs",
    "prompt_section", "priority", "kind", "empirical", "depends_on",
    "inherited_from_previous_prompt", "seed_status", "disposition_note",
)


def rows_from_seed(document: dict) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for requirement in document["requirements"]:
        checks = requirement.get("acceptance_checks", [])
        if not checks:
            raise ValueError(f"{requirement.get('id')} has no acceptance checks")
        for index, check in enumerate(checks, start=1):
            refs = requirement.get("source_refs", [])
            rows.append({
                "atomic_id": f"{requirement['id']}.{index}",
                "requirement_id": requirement["id"],
                "title": requirement["title"],
                "atomic_request": check,
                "source_refs": ";".join(refs),
                "prompt_section": str(requirement.get("prompt_section", "")),
                "priority": requirement["priority"],
                "kind": requirement["kind"],
                "empirical": str(bool(requirement.get("empirical"))).lower(),
                "depends_on": ";".join(requirement.get("depends_on", [])),
                "inherited_from_previous_prompt": str(any(ref.startswith("P0:") for ref in refs)).lower(),
                "seed_status": requirement["status"],
                "disposition_note": "Tracked in requirements_status.json; no retirement inferred.",
            })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("seed", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.seed.open("r", encoding="utf-8") as stream:
        document = json.load(stream)
    rows = rows_from_seed(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({
        "requirements": len(document["requirements"]),
        "atomic_acceptance_rows": len(rows),
        "output": str(args.output),
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
