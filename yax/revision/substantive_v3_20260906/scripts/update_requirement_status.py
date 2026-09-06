#!/usr/bin/env python3
"""Update mutable ledger fields while preserving the immutable seed contract."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


IMMUTABLE = (
    "title", "source_refs", "prompt_section", "kind", "priority",
    "acceptance_checks", "depends_on", "minimum_verified_evidence_roles", "empirical",
)


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--status", type=Path, required=True)
    parser.add_argument("--id", required=True)
    parser.add_argument("--patch", type=Path, required=True,
                        help="JSON object containing mutable replacement fields")
    args = parser.parse_args()
    seed = load(args.seed)
    status = load(args.status)
    patch = load(args.patch)
    if any(field in patch for field in IMMUTABLE + ("id",)):
        raise ValueError("patch attempts to change an immutable field")
    seed_rows = {row["id"]: row for row in seed["requirements"]}
    rows = {row["id"]: row for row in status["requirements"]}
    if args.id not in rows or args.id not in seed_rows:
        raise ValueError(f"unknown requirement: {args.id}")
    for field in IMMUTABLE:
        if rows[args.id].get(field) != seed_rows[args.id].get(field):
            raise ValueError(f"working ledger already changed immutable field {field}")
    rows[args.id].update(patch)
    for row in status["requirements"]:
        for field in IMMUTABLE:
            if row.get(field) != seed_rows[row["id"]].get(field):
                raise ValueError(f"immutable field mismatch for {row['id']}: {field}")
    temporary = args.status.with_suffix(args.status.suffix + ".tmp")
    temporary.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(args.status)
    print(json.dumps({"id": args.id, "status": rows[args.id]["status"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
