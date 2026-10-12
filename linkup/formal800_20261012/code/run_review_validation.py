#!/usr/bin/env python3
"""Orchestrate validation of explicitly assigned Formal800 review files.

This wrapper performs transport/assignment binding only. Semantic validation,
quote resolution, and schema checks remain in validate_reviews.py.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ASSIGNMENT_FIELDS = {"packet_id", "packet_filename", "review_filename", "model", "effort", "agent_id", "role"}
ROLES = {"primary", "blind_audit"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    values = []
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise RuntimeError("%s:%d is not a JSON object" % (path, number))
                values.append(value)
    return values


def contained(root: Path, candidate: Path) -> Path:
    root = root.resolve()
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise RuntimeError("path escapes its assigned directory: %s" % candidate) from exc
    if not candidate.is_file():
        raise RuntimeError("assigned file does not exist: %s" % candidate)
    return candidate


def atomic_json(path: Path, value: Any) -> None:
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    os.umask(0o077)
    parser = argparse.ArgumentParser()
    parser.add_argument("--assignments", type=Path, required=True)
    parser.add_argument("--packet-dir", type=Path, required=True)
    parser.add_argument("--review-dir", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    try:
        import jsonschema
        jsonschema.Draft202012Validator({})
    except Exception as exc:
        raise RuntimeError("runtime jsonschema Draft202012Validator is unavailable") from exc

    assignments = read_jsonl(args.assignments)
    if not assignments:
        raise RuntimeError("assignment file is empty")
    if len({a.get("role") for a in assignments}) != 1:
        raise RuntimeError("primary and blind-audit assignments must be validated separately")
    seen_ids = set()
    packet_paths: list[Path] = []
    review_paths: list[Path] = []
    packet_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    assignment_meta = []
    for assignment in assignments:
        if set(assignment) != ASSIGNMENT_FIELDS:
            raise RuntimeError("assignment rows must contain exactly the seven required fields")
        packet_id = assignment["packet_id"]
        if not isinstance(packet_id, str) or not packet_id or packet_id in seen_ids:
            raise RuntimeError("assignment packet_id is empty or duplicated")
        if assignment["role"] not in ROLES:
            raise RuntimeError("assignment role must be primary or blind_audit")
        for field in ("packet_filename", "review_filename", "model", "effort", "agent_id"):
            if not isinstance(assignment[field], str) or not assignment[field]:
                raise RuntimeError("assignment %s is empty" % field)
        seen_ids.add(packet_id)
        packet_path = contained(args.packet_dir, args.packet_dir / assignment["packet_filename"])
        review_path = contained(args.review_dir, args.review_dir / assignment["review_filename"])
        packet_paths.append(packet_path)
        review_paths.append(review_path)
        packet = read_jsonl(packet_path)
        reviews = read_jsonl(review_path)
        if not packet:
            raise RuntimeError("assigned packet is empty: %s" % packet_path)
        for row in packet:
            if set(row) != {"record_id", "context_sha256", "full_document", "assignment"}:
                raise RuntimeError("assigned packet row has unexpected fields: %s" % packet_path)
            bound = dict(row["assignment"])
            if bound.get("packet_id") != packet_id or bound.get("reviewer_role") != assignment["role"]:
                raise RuntimeError("assignment differs from frozen packet ID or role")
            bound.update({"packet_id": packet_id, "reviewer_role": assignment["role"],
                          "provenance": "model=%s;effort=%s;agent_id=%s" %
                          (assignment["model"], assignment["effort"], assignment["agent_id"])})
            row = dict(row)
            row["assignment"] = bound
            packet_rows.append(row)
        review_rows.extend(reviews)
        assignment_meta.append({**assignment, "packet_sha256": sha256_file(packet_path),
                                "review_sha256": sha256_file(review_path),
                                "packet_rows": len(packet), "review_rows": len(reviews)})

    args.output_dir.mkdir(parents=True, exist_ok=True)
    validator = Path(__file__).with_name("validate_reviews.py")
    with tempfile.TemporaryDirectory(prefix="formal800-validation-") as temp_name:
        temp = Path(temp_name)
        combined_packet = temp / "packet.jsonl"
        combined_reviews = temp / "reviews.jsonl"
        with combined_packet.open("w", encoding="utf-8") as stream:
            for row in packet_rows:
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        with combined_reviews.open("w", encoding="utf-8") as stream:
            for row in review_rows:
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        validated = args.output_dir / "validated_reviews.jsonl"
        errors = args.output_dir / "validation_errors.jsonl"
        receipt = args.output_dir / "validation_receipt.json"
        command = [sys.executable, str(validator), "--packet", str(combined_packet),
                   "--reviews", str(combined_reviews), "--schema", str(args.schema),
                   "--private-validated", str(validated), "--private-errors", str(errors),
                   "--public-receipt", str(receipt), "--expected-records", str(len(packet_rows))]
        result = subprocess.run(command, check=False)
        if result.returncode != 0:
            raise SystemExit(result.returncode)
        if json.loads(receipt.read_text())["status"] != "pass":
            raise RuntimeError("validator did not pass")

    public = {
        "version": "formal800-review-validation-orchestration-v1",
        "status": "pass",
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "runtime_job_id": os.environ.get("SLURM_JOB_ID") or os.environ.get("JOB_ID"),
        "assignment_sha256": sha256_file(args.assignments),
        "assigned_packets": len(assignments),
        "assigned_packet_rows": len(packet_rows),
        "assigned_review_rows": len(review_rows),
        "coverage_scope": "assigned_packets_only",
        "complete_formal800_coverage": False,
        "coverage_note": "Context rows are not ads; full coverage requires a separate join to the frozen 800-ad map.",
        "assignments": assignment_meta,
        "validator_receipt": str(receipt),
        "validator_receipt_sha256": sha256_file(receipt),
    }
    atomic_json(args.output_dir / "PUBLIC_VALIDATION_ORCHESTRATION_RECEIPT.json", public)


if __name__ == "__main__":
    main()
