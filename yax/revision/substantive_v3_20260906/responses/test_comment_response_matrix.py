from __future__ import annotations

import csv
from copy import deepcopy
import hashlib
import json
from pathlib import Path

from build_comment_response_matrix import CROSSWALK, OUT, RECEIPT, ROOT, STATUS, main


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def test_matrix_is_a_lossless_join_to_current_requirement_status() -> None:
    main()
    source = read_csv(CROSSWALK)
    output = read_csv(OUT)
    ledger = json.loads(STATUS.read_text(encoding="utf-8"))
    requirements = {row["id"]: row for row in ledger["requirements"]}
    assert [row["atomic_id"] for row in output] == [
        row["atomic_id"] for row in source
    ]
    assert len(output) == 297
    assert {row["requirement_id"] for row in output} == set(requirements)
    for row in output:
        requirement = requirements[row["requirement_id"]]
        assert row["current_status"] == requirement["status"]
        if row["requirement_id"] == "E09":
            assert json.loads(row["evidence_json"]) == []
            assert row["self_reference_evidence_omitted"] == "true"
        else:
            assert json.loads(row["evidence_json"]) == requirement["evidence"]
            assert row["self_reference_evidence_omitted"] == "false"
        assert json.loads(row["response_locations_json"]) == requirement[
            "response_locations"
        ]


def test_no_unresolved_status_is_rendered_as_completed() -> None:
    main()
    for row in read_csv(OUT):
        allowed = row["current_status"] in {
            "VERIFIED",
            "PREMISE_CORRECTED",
            "INAPPLICABLE_APPROVED",
        }
        assert row["completion_claim_permitted"] == str(allowed).lower()


def test_receipt_authenticates_inputs_and_output_and_preserves_g02_boundary() -> None:
    main()
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS_CURRENT_LEDGER_MATRIX"
    assert receipt["crosswalk_sha256"] == sha(CROSSWALK)
    status = json.loads(STATUS.read_text(encoding="utf-8"))
    projection = deepcopy(status)
    for requirement in projection["requirements"]:
        if requirement["id"] == "E09":
            requirement["evidence"] = []
    expected_projection = hashlib.sha256(
        (
            json.dumps(projection, sort_keys=True, separators=(",", ":")) + "\n"
        ).encode("utf-8")
    ).hexdigest()
    assert receipt["requirements_status_projection_sha256"] == expected_projection
    assert receipt["comment_response_matrix_sha256"] == sha(OUT)
    assert receipt["remaining_dependency"] == {
        "requirement_id": "G02",
        "status": "SPECIFIED",
    }
