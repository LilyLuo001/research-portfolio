"""Adversarial tests for the custodian-view aggregate adapter."""
from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


STAGE = Path(__file__).resolve().parents[1]
ADAPTER = STAGE / "sources/first_public_adapter.py"
FIELDS = [
    "event_id", "url_hash", "publisher_or_issuer", "published_time_status",
    "first_public_status", "interval_precision", "missing_reason",
]
BINDINGS = {
    "P1-2023-08-01": ("8b65270af7ea0fbc1b3029f9099c9e12524b4125ac4e280840b1fde47e8691fe", "EXXONMOBIL"),
    "P1-2023-06-02": ("e575e7011f376549c45dd2fcb21e8a64d0a7d12ae79d82b529116a73eb623112", "UNITEDHEALTH"),
    "P1-2023-08-03": ("56403ccd3f40a7053aea2281057cc3de071b68b3d8bf509e9acf7d6e25526fce", "EXXONMOBIL"),
    "P1-2023-01-01": ("d461fe367503daf9ea33d381f61118d5bb1a79804396920d10f878a4be78836a", "APPLE"),
    "P1-2023-02-02": ("58e5f8d03b52406808e6e8066432e9d2daf421026443abcda31291815b08c61f", "MICROSOFT"),
    "P1-2023-01-03": ("d88d329bba9578a91ec4ae95ef4c204e069880525f1ee77cb84e1f5d31851673", "APPLE"),
}
ISSUER_LABEL = {
    "Apple Inc.": "APPLE",
    "Microsoft Corp.": "MICROSOFT",
    "UnitedHealth Group Inc.": "UNITEDHEALTH",
    "Exxon Mobil Corp.": "EXXONMOBIL",
}


def safe_rows():
    return [
        {
            "event_id": event_id,
            "url_hash": url_hash,
            "publisher_or_issuer": issuer,
            "published_time_status": "ABSENT",
            "first_public_status": "UNKNOWN_SOURCE_VIEW_UNAVAILABLE",
            "interval_precision": "UNKNOWN",
            "missing_reason": "NO_HISTORICAL_PROVENANCE_VIEW",
        }
        for event_id, (url_hash, issuer) in BINDINGS.items()
    ]


def write_dict_view(path: Path, rows, fields=FIELDS):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def run(path: Path):
    return subprocess.run(
        [sys.executable, str(ADAPTER), str(path)], capture_output=True, text=True
    )


def test_exact_binding_and_receipt_hashes(tmp_path):
    path = tmp_path / "valid.csv"
    write_dict_view(path, safe_rows())
    completed = run(path)
    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(completed.stdout)
    assert receipt["rows_private"] == 6
    assert len(receipt["source_list_sha256"]) == 64
    assert len(receipt["adapter_sha256"]) == 64


def test_binding_matches_retained_six_event_metadata():
    clock = STAGE.parent / "20260920_phase3/event_clock/CLOCK_EVIDENCE.csv"
    with clock.open(newline="", encoding="utf-8") as handle:
        retained = {
            row["event_id"]: (
                hashlib.sha256(row["issuer_page_url"].encode()).hexdigest(),
                ISSUER_LABEL[row["issuer"]],
            )
            for row in csv.DictReader(handle)
            if row["issuer_page_url"]
        }
    assert retained == BINDINGS


def test_rejects_individually_allowlisted_but_mismatched_identity(tmp_path):
    rows = safe_rows()
    rows[0]["publisher_or_issuer"] = "APPLE"
    path = tmp_path / "wrong_issuer.csv"
    write_dict_view(path, rows)
    assert run(path).returncode != 0

    rows = safe_rows()
    rows[0]["url_hash"] = "a" * 64
    path = tmp_path / "wrong_hash.csv"
    write_dict_view(path, rows)
    assert run(path).returncode != 0


def test_rejects_duplicate_allowlisted_header(tmp_path):
    path = tmp_path / "duplicate_header.csv"
    write_dict_view(path, safe_rows(), FIELDS + ["event_id"])
    assert run(path).returncode != 0


def test_rejects_ragged_extra_cell(tmp_path):
    path = tmp_path / "ragged.csv"
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(FIELDS)
        for row in safe_rows():
            writer.writerow([row[field] for field in FIELDS] + ["PROHIBITED_PAYLOAD"])
    assert run(path).returncode != 0


def test_rejects_contradictory_false_certification(tmp_path):
    rows = safe_rows()
    rows[0]["first_public_status"] = "FIRST_PUBLIC_CERTIFIED"
    path = tmp_path / "contradictory.csv"
    write_dict_view(path, rows)
    assert run(path).returncode != 0
