"""Audit the public GDPval gold subset for task-level duration metadata.

The row-level audit is private because it contains benchmark task identifiers.
Only aggregate counts, schema names, locators, and hashes enter the repository.
No prompt, rubric, reference, or deliverable content is read or emitted.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Iterable


EXPECTED_TASKS = 220
DURATION_FIELD_CANDIDATES = {
    "duration",
    "duration_minutes",
    "duration_hours",
    "completion_time",
    "completion_time_minutes",
    "completion_time_hours",
    "human_completion_time",
    "human_completion_time_minutes",
    "human_completion_time_hours",
    "time_to_complete",
    "time_to_complete_minutes",
    "time_to_complete_hours",
}
GDPVAL_PAPER_URL = (
    "https://cdn.openai.com/pdf/"
    "d5eb7428-c4e9-4a33-bd86-86dd4bcf12ce/GDPval.pdf"
)


class DurationAuditError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_duration_fields(field_names: Iterable[str]) -> list[str]:
    normalized = {str(name).strip().lower() for name in field_names}
    return sorted(normalized & DURATION_FIELD_CANDIDATES)


def build_private_rows(
    task_ids: Iterable[str],
    *,
    dataset_revision: str,
) -> list[dict[str, str]]:
    ids = [str(task_id).strip() for task_id in task_ids]
    if len(ids) != EXPECTED_TASKS:
        raise DurationAuditError(f"expected {EXPECTED_TASKS} tasks, found {len(ids)}")
    if any(not task_id for task_id in ids):
        raise DurationAuditError("blank GDPval task ID")
    if len(set(ids)) != len(ids):
        raise DurationAuditError("duplicate GDPval task ID")
    return [
        {
            "gdpval_task_id": task_id,
            "dataset_revision": dataset_revision,
            "source_category": "gdpval_validated_self_report",
            "match_status": "unavailable_task_level_in_public_release",
            "duration_value": "",
            "duration_unit": "",
            "duration_basis": "validated_self_report",
            "transformation": "none_no_value_released",
            "source_locator": "GDPval Appendix A.2.4, printed pp. 12-13",
            "remaining_action": "obtain_exact_task_level_values_from_gdpval_authors",
        }
        for task_id in ids
    ]


def write_private_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_receipt(
    *,
    parquet_path: Path,
    dataset_revision: str,
    schema_fields: list[str],
    duration_fields: list[str],
    private_csv_path: Path,
    paper_sha256: str,
) -> dict[str, object]:
    available = bool(duration_fields)
    return {
        "audit_id": "DAX-TD-SOURCE-AUDIT-20260821",
        "status": "PENDING_FIELD_VALIDATION" if available else "BLOCKED_TASK_LEVEL_NOT_PUBLIC",
        "expected_tasks": EXPECTED_TASKS,
        "public_rows_audited": EXPECTED_TASKS,
        "exact_task_level_durations_available": EXPECTED_TASKS if available else 0,
        "near_or_semantic_matches_used": 0,
        "imputed_rows": 0,
        "constant_fill_used": False,
        "task_text_committed": False,
        "outcomes_read": False,
        "public_dataset": {
            "revision": dataset_revision,
            "parquet_sha256": sha256_file(parquet_path),
            "schema_fields": sorted(schema_fields),
            "duration_fields_found": duration_fields,
        },
        "primary_evidence": {
            "paper_url": GDPVAL_PAPER_URL,
            "paper_sha256": paper_sha256,
            "definition_locator": "Appendix A.2.4, printed pp. 12-13",
            "aggregate_locator": "Appendix A.4 Table 3, printed p. 19",
            "definition": "validated self-reported real-world professional completion time",
            "gold_subset_aggregate_minutes": 404,
            "gold_subset_table_mean_hours": 9.49,
            "aggregate_values_used_as_task_values": False,
        },
        "private_row_audit": {
            "row_count": EXPECTED_TASKS,
            "sha256": sha256_file(private_csv_path),
            "task_ids_committed": False,
        },
        "remaining_action": (
            "Request the exact 220 task-level validated self-reported completion times, "
            "task IDs, dataset revision, units, and dated provenance from the GDPval authors; "
            "otherwise execute the prospectively approved qualified-human annotation fallback."
        ),
        "gate_result": "BLOCKED",
        "reason": "The paper documents the measure and aggregates, but the public parquet omits task-level values.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--parquet", required=True, type=Path)
    parser.add_argument("--dataset-revision", required=True)
    parser.add_argument("--paper-sha256", required=True)
    parser.add_argument("--private-csv", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()

    import pyarrow.parquet as pq  # Private SCC runtime dependency.

    schema_fields = pq.read_schema(args.parquet).names
    if "task_id" not in schema_fields:
        raise DurationAuditError("public GDPval parquet has no task_id field")
    task_ids = pq.read_table(args.parquet, columns=["task_id"])["task_id"].to_pylist()
    rows = build_private_rows(task_ids, dataset_revision=args.dataset_revision)
    write_private_csv(rows, args.private_csv)
    receipt = make_receipt(
        parquet_path=args.parquet,
        dataset_revision=args.dataset_revision,
        schema_fields=schema_fields,
        duration_fields=find_duration_fields(schema_fields),
        private_csv_path=args.private_csv,
        paper_sha256=args.paper_sha256,
    )
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "gate_result": receipt["gate_result"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
