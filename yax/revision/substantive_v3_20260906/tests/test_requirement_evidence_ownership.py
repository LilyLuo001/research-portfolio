"""Prevent requirement-specific evidence from being attached to the wrong row."""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_d02_evidence_is_owned_only_by_d02():
    ledger = json.loads((ROOT / "requirements_status.json").read_text(encoding="utf-8"))
    rows = {row["id"]: row for row in ledger["requirements"]}
    d02_markers = ("gate2/d02/", "runs/gate2_d02_", "GATE2_D02_")
    owners: set[str] = set()
    for requirement_id, row in rows.items():
        paths = [entry.get("path", "") for entry in row.get("evidence", [])]
        paths.extend(row.get("response_locations", []))
        review = row.get("review")
        if isinstance(review, dict):
            paths.append(review.get("report_path", ""))
        if any(marker in path for path in paths for marker in d02_markers):
            owners.add(requirement_id)
    assert owners == {"D02"}

    d02 = rows["D02"]
    assert d02["status"] == "RUN_UNVALIDATED"
    assert {entry["role"] for entry in d02["evidence"]}.issuperset(
        {"specification", "code", "run_receipt", "result", "validation_report"}
    )
    assert "D02" not in rows["T04"]["summary"]
    assert rows["T04"]["status"] == "NOT_STARTED"
    assert rows["T04"]["evidence"] == []
    assert rows["T04"]["response_locations"] == []
    assert rows["T04"]["review"] is None
