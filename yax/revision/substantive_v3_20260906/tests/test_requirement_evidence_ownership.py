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
    assert rows["T04"]["status"] == "VERIFIED"
    assert not any(
        marker in entry.get("path", "")
        for entry in rows["T04"].get("evidence", [])
        for marker in d02_markers
    )
    assert {entry["role"] for entry in rows["T04"]["evidence"]} == {
        "verification_report",
        "source_evidence",
    }
    assert rows["T04"]["response_locations"] == [
        "source_verification/T04_DATA_VINTAGE_VERIFICATION.md"
    ]


def test_editorial_and_aioe_evidence_is_attached_to_its_named_requirement():
    ledger = json.loads((ROOT / "requirements_status.json").read_text(encoding="utf-8"))
    rows = {row["id"]: row for row in ledger["requirements"]}

    e04_marker = "editorial/E04_PRECISION_CONSOLIDATION.md"
    e04_owners = {
        requirement_id
        for requirement_id, row in rows.items()
        if e04_marker in [entry.get("path", "") for entry in row.get("evidence", [])]
        or e04_marker in row.get("response_locations", [])
        or (isinstance(row.get("review"), dict) and row["review"].get("report_path") == e04_marker)
    }
    assert e04_owners == {"E04"}
    assert rows["E04"]["status"] == "RUN_UNVALIDATED"
    assert rows["D05"]["status"] == "NOT_STARTED"
    assert not rows["D05"]["evidence"]

    w05_marker = "source_verification/W05_AIOE_UNITS_AND_ATTRIBUTION.md"
    w05_owners = {
        requirement_id
        for requirement_id, row in rows.items()
        if w05_marker in [entry.get("path", "") for entry in row.get("evidence", [])]
        or w05_marker in row.get("response_locations", [])
        or (isinstance(row.get("review"), dict) and row["review"].get("report_path") == w05_marker)
    }
    assert w05_owners == {"W05"}
    assert rows["W05"]["status"] == "RUN_UNVALIDATED"
