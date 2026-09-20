#!/usr/bin/env python3
"""Validate the small, outcome-blind P2 public-evidence package."""
from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> None:
    manifest = json.loads((ROOT / "SOURCE_MANIFEST.json").read_text())
    receipt = json.loads((ROOT / "RECEIPT.json").read_text())
    assert manifest["scope"]["outcome_blind_only"] is True
    assert receipt["outcome_blind_only"] is True
    assert len(manifest["sources"]) == 9

    with (ROOT / "P2_SUPPORT_TABLE.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 20
    assert {r["evidence_type"] for r in rows} >= {"timeline", "rule", "weight", "fund"}
    assert sum(r["evidence_type"] == "weight" for r in rows) == 9
    assert all(not any(x in " ".join(r.values()).lower() for x in ("return", "price", "earnings", "eps")) for r in rows)

    archived = [source for source in manifest["sources"] if source.get("scc_archive_file")]
    assert len(archived) == 6
    assert all(len(source["sha256"]) == 64 for source in archived)
    assert manifest["scc_public_archive_root"].startswith("/projectnb/econdept/qluo/")
    print(f"PASS: {len(manifest['sources'])} sources, {len(rows)} CSV rows, 9 weight rows")


if __name__ == "__main__":
    main()
