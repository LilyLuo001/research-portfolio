from __future__ import annotations

import csv
import importlib.util
import sys
from datetime import date
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / "src" / "audit_archive.py"
SPEC = importlib.util.spec_from_file_location("audit_archive", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
audit_archive = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit_archive
SPEC.loader.exec_module(audit_archive)


def test_month_labels_and_missing_months_are_inclusive() -> None:
    assert audit_archive.month_labels(date(2018, 1, 15), date(2018, 4, 1)) == [
        "2018-01",
        "2018-02",
        "2018-03",
        "2018-04",
    ]
    observed = [date(2018, 1, 31), date(2018, 2, 28), date(2018, 4, 30)]
    assert audit_archive.missing_month_labels(
        observed, date(2018, 1, 1), date(2018, 4, 30)
    ) == ["2018-03"]


def test_max_gap_days_deduplicates_and_orders() -> None:
    observed = [
        date(2024, 3, 31),
        date(2024, 1, 31),
        date(2024, 3, 31),
        date(2024, 2, 29),
    ]
    assert audit_archive.max_gap_days(observed) == 31
    assert audit_archive.max_gap_days([date(2024, 1, 31)]) is None


def test_parse_iso_date_does_not_guess() -> None:
    assert audit_archive.parse_iso_date("2025-12-31 00:00:00") == date(2025, 12, 31)
    assert audit_archive.parse_iso_date("12/31/2025") is None
    assert audit_archive.parse_iso_date(None) is None


def test_safe_ratio_handles_zero_and_formats_deterministically() -> None:
    assert audit_archive.safe_ratio(1, 4) == 0.25
    assert audit_archive.safe_ratio(1, 0) is None
    assert audit_archive.format_ratio(1 / 3) == "0.33333333"
    assert audit_archive.format_ratio(None) == ""


def test_schema_fingerprint_is_order_and_duplicate_invariant() -> None:
    left = audit_archive.schema_fingerprint(["a:int|b:str", "c:date"])
    right = audit_archive.schema_fingerprint(["c:date", "a:int|b:str", "c:date"])
    assert left == right
    assert left.startswith("sha256:")


def test_output_dir_guard_rejects_archive_descendants(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    with pytest.raises(ValueError, match="read-only archive"):
        audit_archive.ensure_outside_archive(archive / "derived", archive)
    audit_archive.ensure_outside_archive(tmp_path / "external_run", archive)


def test_private_lineage_guard_rejects_owning_git_worktree(tmp_path: Path) -> None:
    git_root = tmp_path / "repo"
    (git_root / ".git").mkdir(parents=True)
    source = git_root / "project" / "src" / "audit_archive.py"
    source.parent.mkdir(parents=True)
    source.write_text("", encoding="utf-8")
    with pytest.raises(ValueError, match="private lineage within Git worktree"):
        audit_archive.ensure_outside_owning_git_worktree(
            git_root / "project" / "private_lineage", source
        )
    audit_archive.ensure_outside_owning_git_worktree(
        tmp_path / "authorized_private_lineage", source
    )


def test_csv_schema_requires_evidence_key_first(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="evidence_key"):
        audit_archive.write_csv(
            tmp_path / "bad.csv",
            [{"status": "AVAILABLE", "evidence_key": "LOCAL:x"}],
            ["status", "evidence_key"],
        )

    path = tmp_path / "good.csv"
    audit_archive.write_csv(
        path,
        [{"evidence_key": "LOCAL:x", "status": "AVAILABLE"}],
        ["evidence_key", "status"],
    )
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == ["evidence_key", "status"]
        assert list(reader) == [
            {"evidence_key": "LOCAL:x", "status": "AVAILABLE"}
        ]
    assert b"\r" not in path.read_bytes()


def test_public_evidence_rejects_raw_target_rows_and_low_entropy_fingerprints() -> None:
    safe = {
        "target_membership_search": {
            "target_metadata_match_count": 1,
            "constituent_rows_for_target_metadata_keys": 0,
        }
    }
    audit_archive.validate_public_evidence_payload(safe)

    with pytest.raises(ValueError, match="target_metadata_rows"):
        audit_archive.validate_public_evidence_payload(
            {"target_membership_search": {"target_metadata_rows": [{"gvkeyx": "1"}]}}
        )


def test_public_export_suppresses_licensed_identifiers_and_file_lineage() -> None:
    funds = audit_archive.make_public_fund_rows(
        [
            {
                "evidence_key": "FUND:XLK:2024",
                "crsp_fundno": 123,
                "crsp_portno": 456,
                "security_permno": 789,
                "fund_cusip8": "12345678",
                "fund_ncusip": "123456789",
                "source_locator": "/private/archive/part.parquet",
            }
        ]
    )
    for column in (
        "crsp_fundno",
        "crsp_portno",
        "security_permno",
        "fund_cusip8",
        "fund_ncusip",
    ):
        assert funds[0][column] == audit_archive.PUBLIC_IDENTIFIER_VALUE
    assert funds[0]["fund_name"] == "Public ticker label:  candidate ETF"
    assert funds[0]["source_locator"] == "SCC_PRIVATE_LINEAGE:FUND:XLK:2024"

    catalog = audit_archive.make_public_catalog(
        [{"source_locator": "/private/a.parquet", "schema_hash": "sha256:abc"}]
    )
    assert catalog[0]["source_locator"] == "SCC_PRIVATE_LINEAGE:UNKEYED"
    assert catalog[0]["schema_hash"] == "WITHHELD_LICENSED_SCHEMA_FINGERPRINT"
    with pytest.raises(ValueError, match="target_metadata_key_fingerprint"):
        audit_archive.validate_public_evidence_payload(
            {
                "target_membership_search": {
                    "target_metadata_key_fingerprint": "sha256:reversible"
                }
            }
        )


def test_interval_catalog_uses_end_date_for_maximum() -> None:
    class FakeResult:
        def fetchone(self):
            return (3, "2018-01-01", "2025-12-31", 2, 2, 0)

    class FakeConnection:
        query = ""

        def execute(self, query, _params):
            self.query = query
            return FakeResult()

    connection = FakeConnection()
    spec = audit_archive.DatasetSpec(
        "LOCAL:fund_portfolio_map",
        "AVAILABLE",
        "map",
        "crsp.portnomap",
        (Path("dummy.parquet"),),
        "baseline",
        "full",
        "interval",
        "begdt;enddt",
        "fund x portfolio x interval",
        "try_cast(begdt AS DATE)",
        "crsp_fundno",
        None,
        None,
        "ids",
        "dates",
        "",
        "none",
        "mapping",
        "",
    )
    result = audit_archive.sql_stats(connection, spec)
    assert "max(try_cast(enddt AS DATE))" in connection.query
    assert result["max_date"] == "2025-12-31"
