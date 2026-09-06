#!/usr/bin/env python3
"""Validate the sanitized public transfer of a Gate-1 SCC result bundle."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


PASS_STATUS = "PASS_GATE1_CANONICAL_BASELINE_RECONSTRUCTION"
FORBIDDEN = (
    b"/project/",
    b"/projectnb/",
    b"/usr3/",
    b"/Users/",
    b"ghp_",
    b"github_pat_",
)


class TransferError(ValueError):
    """Raised when the public copy is incomplete, stale, or unsafe."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise TransferError(f"JSON document must be an object: {path.name}")
    return value


def validate(run_dir: Path) -> dict[str, Any]:
    run_dir = run_dir.resolve(strict=True)
    receipt_path = run_dir / "EXECUTION_RECEIPT.json"
    audit_copy = run_dir / "audit_logs/V3_EXECUTION_RECEIPT.json"
    if not receipt_path.is_file() or not audit_copy.is_file():
        raise TransferError("missing wrapper receipt or its audit-log copy")
    if receipt_path.read_bytes() != audit_copy.read_bytes():
        raise TransferError("root wrapper receipt differs from audit-log copy")
    receipt = load_json(receipt_path)
    if receipt.get("status") != PASS_STATUS or receipt.get("exit_code") != 0:
        raise TransferError("wrapper receipt does not establish a passing run")
    if receipt.get("private_paths_or_credentials_persisted") is not False:
        raise TransferError("wrapper receipt does not affirm sanitized persistence")

    result_manifest = receipt.get("output_hashes")
    audit_manifest = receipt.get("audit_artifact_hashes")
    if not isinstance(result_manifest, dict) or not isinstance(audit_manifest, dict):
        raise TransferError("wrapper receipt lacks output hash manifests")

    omitted = "EXECUTION_RECEIPT.json"
    omitted_hash = result_manifest.get(omitted)
    if not isinstance(omitted_hash, str) or len(omitted_hash) != 64:
        raise TransferError("wrapper receipt lacks the retained runner-receipt hash")
    if (run_dir / "results" / omitted).exists():
        raise TransferError("unsanitized runner receipt must not enter the public copy")

    verified_results: dict[str, str] = {}
    for name, expected in sorted(result_manifest.items()):
        if name == omitted:
            continue
        path = run_dir / "results" / name
        if not path.is_file():
            raise TransferError(f"missing public result: {name}")
        observed = sha256_file(path)
        if observed != expected:
            raise TransferError(f"public result hash mismatch: {name}")
        verified_results[name] = observed

    verified_audit: dict[str, str] = {}
    for name, expected in sorted(audit_manifest.items()):
        path = run_dir / "audit_logs" / name
        if not path.is_file():
            raise TransferError(f"missing audit artifact: {name}")
        observed = sha256_file(path)
        if observed != expected:
            raise TransferError(f"audit artifact hash mismatch: {name}")
        verified_audit[name] = observed

    failure_payload = json.loads(
        (run_dir / "audit_logs/WRAPPER_FAILURES.json").read_text(encoding="utf-8")
    )
    if failure_payload != []:
        raise TransferError("passing public bundle has nonempty wrapper failures")

    scan_paths = [path for path in run_dir.rglob("*") if path.is_file()]
    for path in scan_paths:
        payload = path.read_bytes()
        hits = [token.decode("ascii") for token in FORBIDDEN if token in payload]
        if hits:
            raise TransferError(f"private marker in {path.relative_to(run_dir)}: {hits}")

    return {
        "schema_version": "yax-gate1-public-transfer-validation-v1",
        "status": "PASS_SANITIZED_GATE1_PUBLIC_TRANSFER",
        "validated_at_utc": datetime.now(timezone.utc).isoformat(),
        "spec_id": receipt["spec_id"],
        "source_git_head": receipt["repository"]["head"],
        "wrapper_receipt_sha256": sha256_file(receipt_path),
        "verified_public_result_count": len(verified_results),
        "verified_audit_artifact_count": len(verified_audit),
        "verified_public_result_hashes": verified_results,
        "verified_audit_artifact_hashes": verified_audit,
        "excluded_restricted_artifact": {
            "name": omitted,
            "sha256": omitted_hash,
            "reason": "The original R3 runner receipt contains private absolute SCC paths; it remains retained in the authorized SCC run root and is authenticated by the sanitized wrapper receipt.",
        },
        "private_marker_scan": "PASS",
        "scientific_scope": "Transfer and hash integrity only; numerical existence is adjudicated separately by N01-N03.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = validate(args.run_dir)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(json.dumps({"status": report["status"], "report": str(args.report)}))
        return 0
    except (OSError, json.JSONDecodeError, TransferError) as exc:
        print(f"TRANSFER ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
