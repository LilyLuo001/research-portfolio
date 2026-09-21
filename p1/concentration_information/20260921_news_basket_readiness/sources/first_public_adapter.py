#!/usr/bin/env python3
"""Consume an authorized private view and emit its aggregate receipt.

It accepts only the six whitelisted event IDs and source metadata fields named in
CUSTODIAN_OPERATION_REQUEST.json. Row output remains private; this program writes an
aggregate JSON receipt. Do not run until the request is specifically authorized.
"""
import csv, hashlib, json, re
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REQUEST = json.loads((HERE / "CUSTODIAN_OPERATION_REQUEST.json").read_text())
_EXPECTED_BINDINGS = {
    "P1-2023-08-01": ("EXXONMOBIL", "8b65270af7ea0fbc1b3029f9099c9e12524b4125ac4e280840b1fde47e8691fe"),
    "P1-2023-06-02": ("UNITEDHEALTH", "e575e7011f376549c45dd2fcb21e8a64d0a7d12ae79d82b529116a73eb623112"),
    "P1-2023-08-03": ("EXXONMOBIL", "56403ccd3f40a7053aea2281057cc3de071b68b3d8bf509e9acf7d6e25526fce"),
    "P1-2023-01-01": ("APPLE", "d461fe367503daf9ea33d381f61118d5bb1a79804396920d10f878a4be78836a"),
    "P1-2023-02-02": ("MICROSOFT", "58e5f8d03b52406808e6e8066432e9d2daf421026443abcda31291815b08c61f"),
    "P1-2023-01-03": ("APPLE", "d88d329bba9578a91ec4ae95ef4c204e069880525f1ee77cb84e1f5d31851673"),
}
SOURCE_BINDINGS = {event_id: (row["publisher_or_issuer"], row["url_hash"])
                   for event_id, row in REQUEST["fixed_event_source_bindings"].items()}
if SOURCE_BINDINGS != _EXPECTED_BINDINGS:
    raise RuntimeError("request event/source bindings differ from reviewed adapter bindings")
ALLOWED = set(SOURCE_BINDINGS)
SOURCE_LIST_SHA256 = hashlib.sha256(json.dumps(_EXPECTED_BINDINGS, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
if SOURCE_LIST_SHA256 != REQUEST["fixed_event_source_binding_sha256"]:
    raise RuntimeError("request source-list hash differs from reviewed adapter binding")
ALLOWED_FIELDS = {"event_id", "url_hash", "publisher_or_issuer", "published_time_status", "first_public_status", "interval_precision", "missing_reason"}
ENUMS = {
    "publisher_or_issuer": {"APPLE", "MICROSOFT", "EXXONMOBIL", "UNITEDHEALTH"},
    "published_time_status": {"PRESENT", "ABSENT", "NOT_APPLICABLE"},
    "first_public_status": {"FIRST_PUBLIC_CERTIFIED", "NOT_CERTIFIED", "UNKNOWN_SOURCE_VIEW_UNAVAILABLE"},
    "interval_precision": {"SECOND", "MINUTE", "UNKNOWN"},
    "missing_reason": {"NONE", "NO_HISTORICAL_PROVENANCE_VIEW", "NO_EXPLICIT_FIRST_PUBLIC_ASSERTION", "CONFLICTING_PROVENANCE"},
}

def main(path: str) -> None:
    source = Path(path)
    with source.open(newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        if len(headers) != len(ALLOWED_FIELDS) or set(headers) != ALLOWED_FIELDS:
            raise ValueError("private view headers must be exactly allowlisted")
        rows = list(reader)
    for row in rows:
        if None in row or any(value is None for value in row.values()):
            raise ValueError("ragged or extra private-view cell")
        event_id = row["event_id"]
        if event_id not in ALLOWED or not re.fullmatch(r"[0-9a-f]{64}", row["url_hash"]):
            raise ValueError("unwhitelisted event id or invalid url hash")
        if (row["publisher_or_issuer"], row["url_hash"]) != SOURCE_BINDINGS[event_id]:
            raise ValueError("event/source binding mismatch")
        for field, allowed in ENUMS.items():
            if row[field] not in allowed:
                raise ValueError(f"unsafe value in {field}")
        if row["first_public_status"] == "FIRST_PUBLIC_CERTIFIED":
            if not (row["published_time_status"] == "PRESENT" and row["interval_precision"] in {"SECOND", "MINUTE"} and row["missing_reason"] == "NONE"):
                raise ValueError("contradictory certification")
        elif row["first_public_status"] == "NOT_CERTIFIED":
            if row["missing_reason"] == "NONE":
                raise ValueError("uncertified row cannot have no missing reason")
        elif not (row["published_time_status"] in {"ABSENT", "NOT_APPLICABLE"} and row["interval_precision"] == "UNKNOWN" and row["missing_reason"] == "NO_HISTORICAL_PROVENANCE_VIEW"):
            raise ValueError("contradictory unknown provenance")
    event_ids = [r["event_id"] for r in rows]
    if len(rows) != 6 or set(event_ids) != ALLOWED or len(set(event_ids)) != 6:
        raise ValueError("must contain exactly one row for each fixed recheck event")
    out = {"input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(), "source_list_sha256": SOURCE_LIST_SHA256,
           "adapter_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "rows_private": len(rows),
           "counts_first_public_status": dict(Counter(r["first_public_status"] for r in rows)),
           "counts_interval_precision": dict(Counter(r["interval_precision"] for r in rows)),
           "counts_missing_reason": dict(Counter(r["missing_reason"] for r in rows)),
           "row_output": "SCC_PRIVATE_ONLY"}
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    import sys
    main(sys.argv[1])
