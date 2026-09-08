#!/usr/bin/env python3
"""Build the atomic V3 comment-response matrix from the immutable crosswalk.

The output reports current evidence and blockers. It never upgrades a task or
turns an implemented, run-unvalidated, or blocked task into a completion claim.
"""

from __future__ import annotations

import csv
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CROSSWALK = ROOT / "ACCEPTANCE_CHECK_CROSSWALK.csv"
STATUS = ROOT / "requirements_status.json"
OUT = ROOT / "responses" / "COMMENT_RESPONSE_MATRIX.csv"
RECEIPT = ROOT / "responses" / "COMMENT_RESPONSE_MATRIX_VALIDATION.json"
RESOLVED = {"VERIFIED", "PREMISE_CORRECTED", "INAPPLICABLE_APPROVED"}


def digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def compact(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def main() -> None:
    status_document = json.loads(STATUS.read_text(encoding="utf-8"))
    requirements = {row["id"]: row for row in status_document["requirements"]}
    with CROSSWALK.open(newline="", encoding="utf-8") as stream:
        atomic = list(csv.DictReader(stream))

    expected_atomic_ids = [row["atomic_id"] for row in atomic]
    if len(expected_atomic_ids) != len(set(expected_atomic_ids)):
        raise AssertionError("atomic request IDs are not unique")
    if set(row["requirement_id"] for row in atomic) != set(requirements):
        raise AssertionError("atomic crosswalk and live requirement ledger disagree")

    fieldnames = list(atomic[0]) + [
        "current_status",
        "completion_claim_permitted",
        "requirement_summary",
        "response_locations_json",
        "evidence_json",
        "review_json",
        "blocker_json",
        "dependency_status_json",
        "self_reference_evidence_omitted",
    ]
    rows: list[dict[str, str]] = []
    for source in atomic:
        requirement = requirements[source["requirement_id"]]
        dependencies = {
            dependency: requirements[dependency]["status"]
            for dependency in requirement.get("depends_on", [])
        }
        row = dict(source)
        evidence = requirement.get("evidence", [])
        self_reference_omitted = source["requirement_id"] == "E09"
        if self_reference_omitted:
            # E09 owns this matrix. Embedding the matrix's own hash inside the
            # matrix would create an impossible recursive digest contract.
            evidence = []
        row.update(
            {
                "current_status": requirement["status"],
                "completion_claim_permitted": str(
                    requirement["status"] in RESOLVED
                ).lower(),
                "requirement_summary": requirement.get("summary", ""),
                "response_locations_json": compact(
                    requirement.get("response_locations", [])
                ),
                "evidence_json": compact(evidence),
                "review_json": compact(requirement.get("review")),
                "blocker_json": compact(requirement.get("blocker")),
                "dependency_status_json": compact(dependencies),
                "self_reference_evidence_omitted": str(
                    self_reference_omitted
                ).lower(),
            }
        )
        rows.append(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    status_counts: dict[str, int] = {}
    for requirement in requirements.values():
        status_counts[requirement["status"]] = (
            status_counts.get(requirement["status"], 0) + 1
        )
    status_projection = deepcopy(status_document)
    for requirement in status_projection["requirements"]:
        if requirement["id"] == "E09":
            requirement["evidence"] = []
    status_projection_sha256 = sha256(
        (compact(status_projection) + "\n").encode("utf-8")
    ).hexdigest()
    receipt = {
        "schema": "yax.comment_response_matrix_validation.v1",
        "status": "PASS_CURRENT_LEDGER_MATRIX",
        "atomic_request_rows": len(rows),
        "unique_atomic_ids": len(set(expected_atomic_ids)),
        "requirements_represented": len(set(row["requirement_id"] for row in rows)),
        "live_requirements": len(requirements),
        "status_counts": dict(sorted(status_counts.items())),
        "crosswalk_sha256": digest(CROSSWALK),
        "requirements_status_projection_sha256": status_projection_sha256,
        "comment_response_matrix_sha256": digest(OUT),
        "completion_boundary": (
            "Only VERIFIED, PREMISE_CORRECTED, and INAPPLICABLE_APPROVED rows "
            "permit a completion claim. The matrix does not establish G02 "
            "source-request exhaustiveness or scientific validity."
        ),
        "self_reference_rule": (
            "E09 evidence is omitted from its own matrix row and status "
            "projection so the matrix and receipt can be hash-pinned by E09."
        ),
        "remaining_dependency": {
            "requirement_id": "G02",
            "status": requirements["G02"]["status"],
        },
    }
    RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(
        compact(
            {
                "status": receipt["status"],
                "atomic_request_rows": len(rows),
                "requirements_represented": len(requirements),
            }
        )
    )


if __name__ == "__main__":
    main()
