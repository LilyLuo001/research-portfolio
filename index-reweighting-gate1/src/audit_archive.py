#!/usr/bin/env python3
"""Read-only Stage A audit of the SCC WRDS archive.

The program writes only aggregate metadata and coverage results to ``--output-dir``.
It never writes into the archive and never exports licensed row-level observations.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import time
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_RELATIVE = Path("p1_refraction_wrds_shared")
MANIFEST_RELATIVE = Path("_migration_meta/FINAL_SCC_MANIFEST.tsv")
POST_SNAPSHOT_RELATIVE = (
    PROJECT_RELATIVE / "raw/rescue_remaining/near_taq"
)
SCREEN_START = date(2018, 1, 1)
SCREEN_END = date(2025, 12, 31)

CANDIDATE_TICKERS = (
    "XLB",
    "XLC",
    "XLE",
    "XLF",
    "XLI",
    "XLK",
    "XLP",
    "XLRE",
    "XLU",
    "XLV",
    "XLY",
    "QQQ",
)

SELECT_SECTOR_TICKERS = frozenset(CANDIDATE_TICKERS[:-1])

CATALOG_COLUMNS = (
    "evidence_key",
    "status",
    "logical_dataset",
    "source_wrds_table",
    "source_locator",
    "archive_stage",
    "selection_scope",
    "frequency",
    "primary_date_column",
    "entity_key",
    "n_files",
    "n_rows",
    "min_date",
    "max_date",
    "n_unique_entities",
    "n_unique_dates",
    "duplicate_key_rows",
    "schema_hash",
    "available_identifiers",
    "critical_fields",
    "missing_critical_fields",
    "overlap_resolution",
    "research_role",
    "notes",
)

FUND_COLUMNS = (
    "evidence_key",
    "status",
    "screening_coverage_status",
    "assignment_fitness_status",
    "fund_ticker",
    "fund_name",
    "index_family",
    "period",
    "crsp_fundno",
    "crsp_portno",
    "security_permno",
    "fund_cusip8",
    "fund_ncusip",
    "first_offer_date",
    "fund_metadata_start",
    "fund_metadata_end",
    "portfolio_map_start",
    "portfolio_map_end",
    "holdings_first_report_date",
    "holdings_last_report_date",
    "n_holdings_report_dates",
    "expected_report_months",
    "n_missing_report_months",
    "missing_report_months",
    "max_report_gap_days",
    "n_holding_rows",
    "n_distinct_held_securities",
    "mapped_permno_rows",
    "mapped_permno_share",
    "mapped_permno_percent_tna_share",
    "price_match_rows",
    "price_match_share",
    "price_match_percent_tna_share",
    "price_match_definition",
    "duplicate_natural_key_rows",
    "etf_daily_first_date",
    "etf_daily_last_date",
    "etf_daily_n_dates",
    "etf_daily_ret_nonmissing_share",
    "etf_daily_price_nonmissing_share",
    "etf_daily_open_nonmissing_share",
    "etf_daily_bid_ask_nonmissing_share",
    "holdings_source_changes",
    "daily_price_source",
    "critical_missing_fields",
    "source_locator",
    "notes",
)

GAP_COLUMNS = (
    "evidence_key",
    "status",
    "gap_id",
    "scope",
    "affected_dataset_or_funds",
    "required_input",
    "why_needed",
    "next_action",
    "source_locator",
    "notes",
)


@dataclass(frozen=True)
class DatasetSpec:
    evidence_key: str
    status: str
    logical_dataset: str
    source_wrds_table: str
    files: tuple[Path, ...]
    archive_stage: str
    selection_scope: str
    frequency: str
    primary_date_column: str
    entity_key: str
    date_expression: str
    entity_expression: str
    duplicate_key_expression: str | None
    where_expression: str | None
    available_identifiers: str
    critical_fields: str
    missing_critical_fields: str
    overlap_resolution: str
    research_role: str
    notes: str


INTERVAL_END_DATE_EXPRESSIONS = {
    "LOCAL:fund_header_current": "try_cast(end_dt AS DATE)",
    "LOCAL:fund_header_history": "try_cast(chgenddt AS DATE)",
    "LOCAL:fund_portfolio_map": "try_cast(enddt AS DATE)",
    "LOCAL:security_name_history": "try_cast(nameendt AS DATE)",
    "LOCAL:ccm_link_history": "try_cast(linkenddt AS DATE)",
    "LOCAL:comp_index_constituents": "try_cast(thrudate AS DATE)",
    "LOCAL:crsp_stock_industry_membership": "try_cast(mbrenddt AS DATE)",
}


PROHIBITED_PUBLIC_EVIDENCE_KEYS = {
    "archive",
    "baseline_manifest",
    "candidate_identifiers",
    "done_file",
    "done_payload",
    "holdings_batches",
    "hostname",
    "left",
    "left_sha256",
    "output_dir",
    "overlap_comparisons",
    "part_files",
    "pid",
    "platform",
    "post_snapshot_path",
    "python_executable",
    "query_file",
    "right",
    "right_sha256",
    "target_metadata_rows",
    "target_metadata_key_fingerprint",
    "target_keyword_manifest_hits",
    "target_keyword_near_taq_hits",
}

PUBLIC_IDENTIFIER_VALUE = "WITHHELD_LICENSED_IDENTIFIER"


def public_lineage_key(row: dict[str, Any]) -> str:
    key = str(row.get("evidence_key", "UNKEYED"))
    return f"SCC_PRIVATE_LINEAGE:{key}"


def parse_iso_date(value: Any) -> date | None:
    """Parse an ISO-like value to a date without guessing non-ISO formats."""

    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"nan", "nat", "none", "<na>"}:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def month_labels(start: date, end: date) -> list[str]:
    """Return inclusive YYYY-MM labels between two dates."""

    if end < start:
        return []
    year, month = start.year, start.month
    labels: list[str] = []
    while (year, month) <= (end.year, end.month):
        labels.append(f"{year:04d}-{month:02d}")
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
    return labels


def missing_month_labels(
    observed_dates: Iterable[date], start: date, end: date
) -> list[str]:
    observed = {d.strftime("%Y-%m") for d in observed_dates}
    return [label for label in month_labels(start, end) if label not in observed]


def max_gap_days(observed_dates: Iterable[date]) -> int | None:
    ordered = sorted(set(observed_dates))
    if len(ordered) < 2:
        return None
    return max((right - left).days for left, right in zip(ordered, ordered[1:]))


def safe_ratio(numerator: Any, denominator: Any) -> float | None:
    if numerator is None or denominator in (None, 0):
        return None
    try:
        return float(numerator) / float(denominator)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def format_ratio(value: float | None) -> str:
    return "" if value is None else f"{value:.8f}"


def format_value(value: Any) -> str:
    if value is None:
        return ""
    try:
        if value != value:  # NaN / pandas NA where comparison is supported.
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, (datetime, date)):
        return value.isoformat()[:10]
    if hasattr(value, "isoformat") and not isinstance(value, str):
        try:
            return value.isoformat()[:10]
        except (TypeError, ValueError):
            pass
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def schema_fingerprint(schema_descriptions: Iterable[str]) -> str:
    payload = "\n".join(sorted(set(schema_descriptions))).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def schema_descriptions(files: Sequence[Path], pq_module: Any) -> list[str]:
    descriptions: list[str] = []
    for path in files:
        schema = pq_module.ParquetFile(path).schema_arrow
        descriptions.append(
            "|".join(f"{field.name}:{field.type}" for field in schema)
        )
    return descriptions


def ensure_outside_archive(output_dir: Path, archive: Path) -> None:
    output_resolved = output_dir.resolve()
    archive_resolved = archive.resolve()
    if output_resolved == archive_resolved or archive_resolved in output_resolved.parents:
        raise ValueError(
            f"Refusing to write within read-only archive: {output_resolved}"
        )


def ensure_outside_owning_git_worktree(output_dir: Path, source_path: Path) -> None:
    """Refuse detailed licensed lineage anywhere under this source checkout."""

    source_resolved = source_path.resolve()
    git_root = next(
        (
            parent
            for parent in (source_resolved, *source_resolved.parents)
            if (parent / ".git").exists()
        ),
        None,
    )
    if git_root is None:
        return
    output_resolved = output_dir.resolve()
    if output_resolved == git_root or git_root in output_resolved.parents:
        raise ValueError(
            f"Refusing to write private lineage within Git worktree: {output_resolved}"
        )


def write_csv(path: Path, rows: Sequence[dict[str, Any]], columns: Sequence[str]) -> None:
    if not columns or columns[0] != "evidence_key":
        raise ValueError("evidence_key must be the first output column")
    unexpected = sorted({key for row in rows for key in row} - set(columns))
    if unexpected:
        raise ValueError(f"Unexpected output columns for {path.name}: {unexpected}")
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=columns,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({column: format_value(row.get(column)) for column in columns})


def relative_locator(paths: Sequence[Path], project: Path) -> str:
    rels: list[str] = []
    for path in paths:
        try:
            rels.append(str(path.relative_to(project)))
        except ValueError:
            rels.append(str(path))
    if len(rels) <= 8:
        return ";".join(rels)
    parents = sorted({str(Path(item).parent) for item in rels})
    if len(parents) == 1:
        return f"{parents[0]} ({len(rels)} files; enumerated in stage_a_evidence.json)"
    return f"{len(rels)} files enumerated in stage_a_evidence.json; roots=" + ";".join(
        parents[:8]
    )


def integer_tuple(values: Iterable[Any]) -> str:
    ints = sorted({int(float(value)) for value in values if value is not None})
    if not ints:
        return "(NULL)"
    if len(ints) == 1:
        return f"({ints[0]})"
    return "(" + ",".join(str(value) for value in ints) + ")"


def sql_stats(connection: Any, spec: DatasetSpec) -> dict[str, Any]:
    if not spec.files:
        return {
            "n_rows": 0,
            "min_date": None,
            "max_date": None,
            "n_unique_entities": 0,
            "n_unique_dates": 0,
            "duplicate_key_rows": None,
        }
    duplicate_sql = (
        "NULL"
        if spec.duplicate_key_expression is None
        else f"count(*) - count(distinct ({spec.duplicate_key_expression}))"
    )
    where_sql = f"WHERE {spec.where_expression}" if spec.where_expression else ""
    max_date_expression = INTERVAL_END_DATE_EXPRESSIONS.get(
        spec.evidence_key, spec.date_expression
    )
    query = f"""
        SELECT
            count(*) AS n_rows,
            min({spec.date_expression}) AS min_date,
            max({max_date_expression}) AS max_date,
            count(DISTINCT {spec.entity_expression}) AS n_unique_entities,
            count(DISTINCT {spec.date_expression}) AS n_unique_dates,
            {duplicate_sql} AS duplicate_key_rows
        FROM read_parquet(?, union_by_name=true)
        {where_sql}
    """
    row = connection.execute(query, [[str(path) for path in spec.files]]).fetchone()
    return dict(
        zip(
            (
                "n_rows",
                "min_date",
                "max_date",
                "n_unique_entities",
                "n_unique_dates",
                "duplicate_key_rows",
            ),
            row,
            strict=True,
        )
    )


def validate_public_evidence_payload(value: Any, path: str = "root") -> None:
    """Reject known row-level or reversibly encoded target identifiers."""

    if isinstance(value, dict):
        for key, child in value.items():
            if key in PROHIBITED_PUBLIC_EVIDENCE_KEYS:
                raise ValueError(f"prohibited public evidence key at {path}.{key}")
            validate_public_evidence_payload(child, f"{path}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            validate_public_evidence_payload(child, f"{path}[{index}]")


def make_public_catalog(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Remove file locators and schema fingerprints from the repository export."""

    output: list[dict[str, Any]] = []
    for row in rows:
        public_row = dict(row)
        public_row["source_locator"] = public_lineage_key(public_row)
        public_row["schema_hash"] = "WITHHELD_LICENSED_SCHEMA_FINGERPRINT"
        output.append(public_row)
    return output


def make_public_fund_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Retain fund-year aggregates while suppressing licensed identifier values."""

    identifier_columns = (
        "crsp_fundno",
        "crsp_portno",
        "security_permno",
        "fund_cusip8",
        "fund_ncusip",
    )
    output: list[dict[str, Any]] = []
    for row in rows:
        public_row = dict(row)
        public_row["fund_name"] = (
            f"Public ticker label: {public_row.get('fund_ticker', '')} candidate ETF"
        )
        for column in identifier_columns:
            public_row[column] = PUBLIC_IDENTIFIER_VALUE
        public_row["source_locator"] = public_lineage_key(public_row)
        output.append(public_row)
    return output


def make_public_gap_rows(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep gap decisions but not the licensed filesystem provenance string."""

    output: list[dict[str, Any]] = []
    for row in rows:
        public_row = dict(row)
        public_row["source_locator"] = public_lineage_key(public_row)
        output.append(public_row)
    return output


def make_public_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    """Build a public-safe aggregate evidence record from the internal run state."""

    batches = evidence["holdings_batches"]
    comparisons = evidence["overlap_comparisons"]
    inventory = evidence["archive_inventory"]
    identifiers = evidence["candidate_identifiers"]
    run = evidence["run"]
    public = {
        "run": {
            "started_utc": run["started_utc"],
            "finished_utc": run["finished_utc"],
            "elapsed_seconds": run["elapsed_seconds"],
            "archive_location": "AUTHORIZED_SCC_ARCHIVE; exact locator retained outside public repository",
            "output_location": "AUTHORIZED_SCC_RUN_DIRECTORY; exact locator retained outside public repository",
            "archive_write_policy": run["archive_write_policy"],
            "output_profile": "PUBLIC_AGGREGATE_REDACTED",
        },
        "versions": evidence["versions"],
        "archive_inventory": {
            "baseline_manifest_rows": inventory["baseline_manifest_rows"],
            "post_snapshot_file_count": inventory["post_snapshot_file_count"],
            "canonical_midas_file_count": inventory["canonical_midas_file_count"],
            "superseded_midas_file_count": inventory["superseded_midas_file_count"],
            "target_keyword_manifest_hit_count": inventory[
                "target_keyword_manifest_hit_count"
            ],
            "target_keyword_near_taq_hit_count": len(
                inventory["target_keyword_near_taq_hits"]
            ),
        },
        "candidate_scope": {
            "tickers": identifiers["tickers"],
            "candidate_fund_count": len(identifiers["crsp_fundnos"]),
            "candidate_portfolio_count": len(identifiers["crsp_portnos"]),
            "candidate_security_count": len(identifiers["security_permnos"]),
            "licensed_identifier_values_published": False,
        },
        "holdings_batch_audit": {
            "batch_count": len(batches),
            "part_file_count": evidence["holdings_part_file_count"],
            "all_completion_counts_match": all(
                bool(batch["completion_counts_match"]) for batch in batches
            ),
            "licensed_batch_names_paths_timestamps_published": False,
        },
        "overlap_copy_audit": {
            "comparison_pair_count": len(comparisons),
            "byte_identical_pair_count": sum(
                bool(comparison["byte_identical"]) for comparison in comparisons
            ),
            "file_paths_or_hashes_published": False,
        },
        "target_membership_search": evidence["target_membership_search"],
        "output_schemas": evidence["output_schemas"],
        "method_notes": evidence["method_notes"],
    }
    validate_public_evidence_payload(public)
    return public


def build_catalog_row(
    connection: Any,
    spec: DatasetSpec,
    project: Path,
    pq_module: Any,
) -> dict[str, Any]:
    stats = sql_stats(connection, spec)
    fingerprints = schema_descriptions(spec.files, pq_module) if spec.files else []
    return {
        "evidence_key": spec.evidence_key,
        "status": spec.status,
        "logical_dataset": spec.logical_dataset,
        "source_wrds_table": spec.source_wrds_table,
        "source_locator": relative_locator(spec.files, project),
        "archive_stage": spec.archive_stage,
        "selection_scope": spec.selection_scope,
        "frequency": spec.frequency,
        "primary_date_column": spec.primary_date_column,
        "entity_key": spec.entity_key,
        "n_files": len(spec.files),
        **stats,
        "schema_hash": schema_fingerprint(fingerprints) if fingerprints else "",
        "available_identifiers": spec.available_identifiers,
        "critical_fields": spec.critical_fields,
        "missing_critical_fields": spec.missing_critical_fields,
        "overlap_resolution": spec.overlap_resolution,
        "research_role": spec.research_role,
        "notes": spec.notes,
    }


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compare_byte_copies(left: Path, right: Path) -> dict[str, Any]:
    result: dict[str, Any] = {
        "left": str(left),
        "right": str(right),
        "left_size": left.stat().st_size,
        "right_size": right.stat().st_size,
    }
    if result["left_size"] != result["right_size"]:
        result["byte_identical"] = False
        result["comparison"] = "size differs; SHA256 not computed"
        return result
    left_hash = file_sha256(left)
    right_hash = file_sha256(right)
    result.update(
        {
            "left_sha256": left_hash,
            "right_sha256": right_hash,
            "byte_identical": left_hash == right_hash,
            "comparison": "full-file SHA256",
        }
    )
    return result


def load_candidate_metadata(project: Path, pd_module: Any) -> dict[str, Any]:
    current_path = project / "raw/crsp_fund_hdr_full.parquet"
    map_path = project / "raw/crsp_portnomap_full.parquet"
    history_paths = sorted(
        (project / "raw/rescue_remaining/crsp_fund_hdr_hist_full_max").glob(
            "part_*.parquet"
        )
    )
    names_path = project / "raw/crsp_dsenames_full.parquet"
    new_names_path = project / "raw/rescue/newcrsp_crsp_stocknames_v2_full.parquet"

    current = pd_module.read_parquet(current_path)
    port_map = pd_module.read_parquet(map_path)
    history = pd_module.concat(
        [pd_module.read_parquet(path) for path in history_paths], ignore_index=True
    )
    names = pd_module.read_parquet(names_path)
    new_names = pd_module.read_parquet(new_names_path)

    ticker_set = set(CANDIDATE_TICKERS)
    frames = {
        "current": current[
            current["ticker"].astype("string").str.upper().isin(ticker_set)
        ].copy(),
        "port_map": port_map[
            port_map["ticker"].astype("string").str.upper().isin(ticker_set)
        ].copy(),
        "history": history[
            history["ticker"].astype("string").str.upper().isin(ticker_set)
        ].copy(),
        "names": names[
            names["ticker"].astype("string").str.upper().isin(ticker_set)
        ].copy(),
        "new_names": new_names[
            new_names["ticker"].astype("string").str.upper().isin(ticker_set)
        ].copy(),
        "history_paths": history_paths,
    }
    if set(frames["current"]["ticker"].astype(str).str.upper()) != ticker_set:
        missing = sorted(
            ticker_set
            - set(frames["current"]["ticker"].astype(str).str.upper())
        )
        raise RuntimeError(f"Candidate tickers missing from fund header: {missing}")
    duplicated = frames["current"]["ticker"].astype(str).str.upper().duplicated()
    if duplicated.any():
        tickers = frames["current"].loc[duplicated, "ticker"].tolist()
        raise RuntimeError(f"Ambiguous current candidate fund tickers: {tickers}")
    return frames


def create_holdings_table(
    connection: Any,
    project: Path,
    candidate_portnos: Sequence[Any],
    pq_module: Any,
) -> tuple[list[Path], list[dict[str, Any]]]:
    rescue = project / "raw/rescue_remaining"
    query_files: list[Path] = []
    part_files: list[Path] = []
    target_pattern = re.compile(
        r"\b(" + "|".join(str(int(float(x))) for x in candidate_portnos) + r")\b"
    )
    for year in range(SCREEN_START.year, SCREEN_END.year + 1):
        for query_path in sorted(
            rescue.glob(f"crsp_holdings_etf_{year}_b*/QUERY.sql")
        ):
            text = query_path.read_text(encoding="utf-8", errors="replace")
            if target_pattern.search(text):
                query_files.append(query_path)
                part_files.extend(sorted(query_path.parent.glob("part_*.parquet")))
    if not part_files:
        raise FileNotFoundError("No candidate holdings Parquet parts resolved from batch SQL")

    portno_tuple = integer_tuple(candidate_portnos)
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE stage_a_holdings AS
        SELECT
            row_number() OVER () AS holding_row_id,
            try_cast(crsp_portno AS BIGINT) AS crsp_portno,
            try_cast(report_dt AS DATE) AS report_dt,
            try_cast(eff_dt AS DATE) AS eff_dt,
            security_rank,
            percent_tna,
            nbr_shares,
            market_val,
            crsp_company_key,
            security_name,
            cusip,
            try_cast(permno AS BIGINT) AS held_permno,
            try_cast(permco AS BIGINT) AS held_permco,
            ticker AS held_ticker,
            filename AS source_file,
            coalesce(
                cast(try_cast(permno AS BIGINT) AS VARCHAR),
                nullif(trim(cusip), ''),
                nullif(trim(ticker), ''),
                cast(crsp_company_key AS VARCHAR),
                concat('RANK:', cast(security_rank AS VARCHAR))
            ) AS held_key
        FROM read_parquet(?, union_by_name=true, filename=true)
        WHERE try_cast(crsp_portno AS BIGINT) IN {portno_tuple}
          AND try_cast(report_dt AS DATE)
              BETWEEN make_date({SCREEN_START.year}, 1, 1)
                  AND make_date({SCREEN_END.year}, 12, 31)
        """,
        [[str(path) for path in part_files]],
    )
    batches = []
    for query_path in query_files:
        batch_parts = sorted(query_path.parent.glob("part_*.parquet"))
        done_path = query_path.parent / "_DONE.json"
        done_payload = (
            json.loads(done_path.read_text(encoding="utf-8"))
            if done_path.is_file()
            else None
        )
        metadata_rows = sum(
            pq_module.ParquetFile(path).metadata.num_rows for path in batch_parts
        )
        complete_match = bool(
            done_payload is not None
            and int(done_payload.get("parts", -1)) == len(batch_parts)
            and int(done_payload.get("rows", -1)) == metadata_rows
        )
        if not complete_match:
            raise RuntimeError(
                f"Holdings batch completion metadata mismatch: {query_path.parent}"
            )
        batches.append(
            {
                "query_file": str(query_path),
                "part_files": [str(path) for path in batch_parts],
                "done_file": str(done_path),
                "done_present": done_path.is_file(),
                "done_payload": done_payload,
                "parquet_metadata_rows": metadata_rows,
                "completion_counts_match": complete_match,
            }
        )
    return part_files, batches


def create_daily_price_table(
    connection: Any,
    project: Path,
    etf_permnos: Sequence[Any],
) -> dict[str, list[Path]]:
    legacy_files = [
        project / f"raw/crsp_dsf_{year}.parquet"
        for year in range(SCREEN_START.year, 2025)
    ]
    ciz_file = project / "raw/rescue/newcrsp_crsp_dsf_v2_2025.parquet"
    relevant_permnos = connection.execute(
        "SELECT DISTINCT held_permno FROM stage_a_holdings WHERE held_permno IS NOT NULL"
    ).fetchall()
    all_permnos = [row[0] for row in relevant_permnos] + list(etf_permnos)
    permno_tuple = integer_tuple(all_permnos)
    connection.execute(
        f"""
        CREATE OR REPLACE TEMP TABLE stage_a_daily AS
        SELECT
            permno,
            try_cast(date AS DATE) AS price_date,
            ret AS daily_return,
            prc AS price,
            openprc AS open_price,
            bid,
            ask,
            'CRSP_LEGACY_DSF' AS source_family
        FROM read_parquet(?, union_by_name=true)
        WHERE permno IN {permno_tuple}
          AND try_cast(date AS DATE)
              BETWEEN make_date({SCREEN_START.year}, 1, 1) AND make_date(2024, 12, 31)
        UNION ALL
        SELECT
            permno,
            try_cast(dlycaldt AS DATE) AS price_date,
            dlyret AS daily_return,
            dlyprc AS price,
            dlyopen AS open_price,
            dlybid AS bid,
            dlyask AS ask,
            'CRSP_CIZ_DSF_V2' AS source_family
        FROM read_parquet(?)
        WHERE permno IN {permno_tuple}
          AND try_cast(dlycaldt AS DATE)
              BETWEEN make_date(2025, 1, 1) AND make_date(2025, 12, 31)
        """,
        [[str(path) for path in legacy_files], str(ciz_file)],
    )
    connection.execute(
        """
        CREATE OR REPLACE TEMP TABLE stage_a_holdings_price_match AS
        SELECT
            h.holding_row_id,
            max(d.price_date) AS matched_price_date,
            arg_max(d.price, d.price_date) AS matched_price
        FROM stage_a_holdings h
        LEFT JOIN stage_a_daily d
          ON d.permno = h.held_permno
         AND d.price_date BETWEEN h.report_dt - INTERVAL 7 DAY AND h.report_dt
        GROUP BY h.holding_row_id
        """
    )
    return {"legacy": legacy_files, "ciz": [ciz_file]}


def distinct_joined(values: Iterable[Any]) -> str:
    cleaned = sorted(
        {
            str(value).strip()
            for value in values
            if value is not None
            and str(value).strip()
            and str(value).strip().lower() not in {"nan", "nat", "<na>"}
        }
    )
    return "|".join(cleaned)


def overlapping_rows(frame: Any, start_column: str, end_column: str, year: int) -> Any:
    start = frame[start_column].map(parse_iso_date)
    end = frame[end_column].map(parse_iso_date)
    year_start, year_end = date(year, 1, 1), date(year, 12, 31)
    return frame[(start.isna() | (start <= year_end)) & (end.isna() | (end >= year_start))]


def fund_rows(
    connection: Any,
    metadata: dict[str, Any],
    project: Path,
    holdings_files: Sequence[Path],
    daily_files: dict[str, list[Path]],
) -> list[dict[str, Any]]:
    current = metadata["current"].copy()
    port_map = metadata["port_map"].copy()
    history = metadata["history"].copy()
    names = metadata["names"].copy()
    new_names = metadata["new_names"].copy()
    for frame in (current, port_map, history, names, new_names):
        frame["ticker"] = frame["ticker"].astype("string").str.upper()

    holdings_stats = connection.execute(
        """
        WITH base AS (
            SELECT
                h.*,
                year(h.report_dt) AS period,
                p.matched_price_date,
                p.matched_price
            FROM stage_a_holdings h
            LEFT JOIN stage_a_holdings_price_match p USING (holding_row_id)
        )
        SELECT
            crsp_portno,
            period,
            count(*) AS n_holding_rows,
            count(DISTINCT report_dt) AS n_report_dates,
            min(report_dt) AS first_report_dt,
            max(report_dt) AS last_report_dt,
            string_agg(DISTINCT cast(report_dt AS VARCHAR), ',' ORDER BY cast(report_dt AS VARCHAR)) AS report_dates,
            count(DISTINCT held_key) AS n_distinct_held_securities,
            count(*) FILTER (WHERE held_permno IS NOT NULL) AS mapped_permno_rows,
            sum(CASE WHEN held_permno IS NOT NULL THEN abs(coalesce(percent_tna, 0)) ELSE 0 END) AS mapped_percent_tna,
            sum(abs(coalesce(percent_tna, 0))) AS total_percent_tna,
            count(*) FILTER (WHERE matched_price IS NOT NULL) AS price_match_rows,
            sum(CASE WHEN matched_price IS NOT NULL THEN abs(coalesce(percent_tna, 0)) ELSE 0 END) AS price_match_percent_tna,
            count(*) - count(DISTINCT (crsp_portno, report_dt, held_key)) AS duplicate_natural_key_rows,
            count(DISTINCT source_file) AS n_source_files,
            string_agg(DISTINCT source_file, '|' ORDER BY source_file) AS source_files,
            count(DISTINCT typeof(held_permno)) AS n_cast_types
        FROM base
        GROUP BY crsp_portno, period
        ORDER BY crsp_portno, period
        """
    ).df()

    daily_stats = connection.execute(
        """
        SELECT
            permno,
            year(price_date) AS period,
            min(price_date) AS first_date,
            max(price_date) AS last_date,
            count(DISTINCT price_date) AS n_dates,
            count(*) AS n_rows,
            count(*) FILTER (WHERE daily_return IS NOT NULL) AS ret_nonmissing,
            count(*) FILTER (WHERE price IS NOT NULL) AS price_nonmissing,
            count(*) FILTER (WHERE open_price IS NOT NULL) AS open_nonmissing,
            count(*) FILTER (WHERE bid IS NOT NULL AND ask IS NOT NULL) AS bid_ask_nonmissing,
            count(DISTINCT source_family) AS n_source_families,
            string_agg(DISTINCT source_family, '|' ORDER BY source_family) AS source_family
        FROM stage_a_daily
        GROUP BY permno, period
        """
    ).df()

    holdings_lookup = {
        (int(row.crsp_portno), int(row.period)): row
        for row in holdings_stats.itertuples(index=False)
    }
    daily_lookup = {
        (int(row.permno), int(row.period)): row
        for row in daily_stats.itertuples(index=False)
    }

    rows: list[dict[str, Any]] = []
    for ticker in CANDIDATE_TICKERS:
        header = current[current["ticker"] == ticker].iloc[0]
        fundno = int(header["crsp_fundno"])
        fund_map = port_map[port_map["crsp_fundno"] == header["crsp_fundno"]]
        hist = history[history["crsp_fundno"] == header["crsp_fundno"]]
        security_names = names[names["ticker"] == ticker]
        new_security_names = new_names[new_names["ticker"] == ticker]
        security_permnos = sorted(
            {
                int(value)
                for value in list(security_names["permno"].dropna())
                + list(new_security_names["permno"].dropna())
            }
        )
        if len(security_permnos) != 1:
            raise RuntimeError(
                f"Expected one security PERMNO for {ticker}, got {security_permnos}"
            )
        security_permno = security_permnos[0]

        for year in range(SCREEN_START.year, SCREEN_END.year + 1):
            map_overlap = overlapping_rows(fund_map, "begdt", "enddt", year)
            active_map = map_overlap[
                map_overlap["crsp_portno"].map(
                    lambda value: (int(float(value)), year) in holdings_lookup
                    if value is not None
                    else False
                )
            ]
            if active_map.empty:
                # If no holdings exist, retain the latest portfolio map valid in the year.
                active_map = map_overlap.tail(1)
            if active_map.empty:
                continue
            portnos = sorted({int(float(value)) for value in active_map["crsp_portno"]})
            if len(portnos) != 1:
                raise RuntimeError(
                    f"Ambiguous active portfolio number for {ticker} {year}: {portnos}"
                )
            portno = portnos[0]
            hs = holdings_lookup.get((portno, year))
            ds = daily_lookup.get((security_permno, year))

            map_begin_dates = [
                value
                for value in active_map["begdt"].map(parse_iso_date)
                if value is not None
            ]
            map_end_dates = [
                value
                for value in active_map["enddt"].map(parse_iso_date)
                if value is not None
            ]
            eligible_start = max(
                date(year, 1, 1), min(map_begin_dates) if map_begin_dates else date(year, 1, 1)
            )
            eligible_end = min(
                date(year, 12, 31), max(map_end_dates) if map_end_dates else date(year, 12, 31)
            )

            observed_dates: list[date] = []
            if hs is not None and hs.report_dates:
                observed_dates = [
                    parsed
                    for parsed in (
                        parse_iso_date(item) for item in str(hs.report_dates).split(",")
                    )
                    if parsed is not None
                ]
            missing = missing_month_labels(observed_dates, eligible_start, eligible_end)
            expected = month_labels(eligible_start, eligible_end)

            hist_overlap = overlapping_rows(hist, "chgdt", "chgenddt", year)
            hist_begin_dates = [
                value
                for value in hist_overlap.get("chgdt", []).map(parse_iso_date)
                if value is not None
            ]
            hist_end_dates = [
                value
                for value in hist_overlap.get("chgenddt", []).map(parse_iso_date)
                if value is not None
            ]
            metadata_start = max(
                date(year, 1, 1),
                min(hist_begin_dates) if hist_begin_dates else date(year, 1, 1),
            )
            metadata_end = min(
                date(year, 12, 31),
                max(hist_end_dates) if hist_end_dates else date(year, 12, 31),
            )
            fund_names = distinct_joined(hist_overlap.get("fund_name", []))
            if not fund_names:
                fund_names = format_value(header["fund_name"])
            cusip8 = distinct_joined(hist_overlap.get("cusip8", []))
            ncusip = distinct_joined(hist_overlap.get("ncusip", []))

            n_holding_rows = int(hs.n_holding_rows) if hs is not None else 0
            total_tna = float(hs.total_percent_tna) if hs is not None else None
            mapped_rows = int(hs.mapped_permno_rows) if hs is not None else 0
            price_rows = int(hs.price_match_rows) if hs is not None else 0

            missing_fields = [
                "official_index_assignment_weight",
                "uncapped_reference_weight",
                "provider_float_adjustment",
                "holdings_filing_date",
                "holdings_publication_date",
                "holdings_download_date",
                "creation_redemption_basket_indicator",
            ]
            if mapped_rows < n_holding_rows:
                missing_fields.append("held_permno_for_some_positions")
            if price_rows < mapped_rows:
                missing_fields.append("matched_daily_price_for_some_mapped_positions")

            coverage_gap = bool(
                missing
                or hs is None
                or ds is None
                or mapped_rows < n_holding_rows
                or price_rows < mapped_rows
            )
            status = (
                "AVAILABLE_SCREENING_PROXY_WITH_COVERAGE_GAPS"
                if coverage_gap
                else "AVAILABLE_SCREENING_PROXY_ONLY"
            )
            holding_source_paths = (
                [Path(item) for item in str(hs.source_files).split("|") if item]
                if hs is not None and hs.source_files
                else []
            )
            holding_sources = (
                f"{len(holding_source_paths)} contributing parquet part file(s); "
                "no vendor-family transition inferred"
                if holding_source_paths
                else "no holdings rows"
            )
            daily_source = format_value(ds.source_family) if ds is not None else ""
            price_files = (
                [
                    path
                    for path in daily_files["legacy"]
                    if f"_{year}.parquet" in path.name
                ]
                if year <= 2024
                else daily_files["ciz"]
            )

            fund_row = {
                "evidence_key": f"FUND:{ticker}:{year}",
                "status": status,
                "screening_coverage_status": (
                    "COVERAGE_GAPS"
                    if coverage_gap
                    else "COVERAGE_COMPLETE_FOR_RECORDED_SCREEN"
                ),
                "assignment_fitness_status": "NOT_EXACT_INDEX_ASSIGNMENT_INPUT",
                "fund_ticker": ticker,
                "fund_name": fund_names,
                "index_family": (
                    "S&P U.S. Select Sector candidate"
                    if ticker in SELECT_SECTOR_TICKERS
                    else "Nasdaq-100 candidate"
                ),
                "period": year,
                "crsp_fundno": fundno,
                "crsp_portno": portno,
                "security_permno": security_permno,
                "fund_cusip8": cusip8 or format_value(header["cusip8"]),
                "fund_ncusip": ncusip or format_value(header["ncusip"]),
                "first_offer_date": header["first_offer_dt"],
                "fund_metadata_start": metadata_start,
                "fund_metadata_end": metadata_end,
                "portfolio_map_start": eligible_start,
                "portfolio_map_end": eligible_end,
                "holdings_first_report_date": hs.first_report_dt if hs is not None else None,
                "holdings_last_report_date": hs.last_report_dt if hs is not None else None,
                "n_holdings_report_dates": int(hs.n_report_dates) if hs is not None else 0,
                "expected_report_months": len(expected),
                "n_missing_report_months": len(missing),
                "missing_report_months": "|".join(missing),
                "max_report_gap_days": max_gap_days(observed_dates),
                "n_holding_rows": n_holding_rows,
                "n_distinct_held_securities": int(hs.n_distinct_held_securities) if hs is not None else 0,
                "mapped_permno_rows": mapped_rows,
                "mapped_permno_share": format_ratio(safe_ratio(mapped_rows, n_holding_rows)),
                "mapped_permno_percent_tna_share": format_ratio(
                    safe_ratio(hs.mapped_percent_tna, total_tna) if hs is not None else None
                ),
                "price_match_rows": price_rows,
                "price_match_share": format_ratio(safe_ratio(price_rows, n_holding_rows)),
                "price_match_percent_tna_share": format_ratio(
                    safe_ratio(hs.price_match_percent_tna, total_tna)
                    if hs is not None
                    else None
                ),
                "price_match_definition": (
                    "nonmissing CRSP price on latest trading date <= report_dt within 7 calendar days"
                ),
                "duplicate_natural_key_rows": int(hs.duplicate_natural_key_rows) if hs is not None else 0,
                "etf_daily_first_date": ds.first_date if ds is not None else None,
                "etf_daily_last_date": ds.last_date if ds is not None else None,
                "etf_daily_n_dates": int(ds.n_dates) if ds is not None else 0,
                "etf_daily_ret_nonmissing_share": format_ratio(
                    safe_ratio(ds.ret_nonmissing, ds.n_rows) if ds is not None else None
                ),
                "etf_daily_price_nonmissing_share": format_ratio(
                    safe_ratio(ds.price_nonmissing, ds.n_rows) if ds is not None else None
                ),
                "etf_daily_open_nonmissing_share": format_ratio(
                    safe_ratio(ds.open_nonmissing, ds.n_rows) if ds is not None else None
                ),
                "etf_daily_bid_ask_nonmissing_share": format_ratio(
                    safe_ratio(ds.bid_ask_nonmissing, ds.n_rows) if ds is not None else None
                ),
                "holdings_source_changes": holding_sources,
                "daily_price_source": daily_source,
                "critical_missing_fields": "|".join(missing_fields),
                "source_locator": (
                    "raw/crsp_fund_hdr_full.parquet;"
                    "raw/rescue_remaining/crsp_fund_hdr_hist_full_max/part_*.parquet;"
                    "raw/crsp_portnomap_full.parquet;"
                    "raw/crsp_dsenames_full.parquet;"
                    "raw/rescue/newcrsp_crsp_stocknames_v2_full.parquet;"
                    f"{relative_locator(holding_source_paths, project)};"
                    + relative_locator(price_files, project)
                ),
                "notes": (
                    "Index family is the audit's candidate-scope label, not a benchmark field in CRSP. "
                    "Holdings are report-date ETF snapshots and screening evidence only; eff_dt is present "
                    "but is not relabeled as filing/publication/download date. Expected months are calendar "
                    "months during portfolio_map_start/end, not a claim that CRSP promised monthly reports. "
                    "fund_metadata_start/end instead summarize the overlapping historical-header interval. "
                    "percent_tna coverage shares use absolute percent_tna so short/negative positions cannot push coverage above one."
                ),
            }
            rows.append(fund_row)
    return rows


def catalog_specs(
    project: Path,
    holdings_files: Sequence[Path],
    candidate_portnos: Sequence[Any],
) -> list[DatasetSpec]:
    raw = project / "raw"
    rescue = raw / "rescue"
    remaining = raw / "rescue_remaining"
    legacy_dsf = tuple(raw / f"crsp_dsf_{year}.parquet" for year in range(2018, 2025))
    summary2 = tuple(raw / f"crsp_fund_summary2_{year}.parquet" for year in range(2018, 2026))
    dseshares = tuple(raw / f"crsp_dseshares_{year}.parquet" for year in range(2018, 2025))
    hist_parts = tuple(sorted((remaining / "crsp_fund_hdr_hist_full_max").glob("part_*.parquet")))
    company_parts = tuple(sorted((remaining / "crsp_holdings_co_info_full_max").glob("part_*.parquet")))
    midas = tuple(
        sorted(
            path
            for path in (remaining / "near_taq/midas").glob("midas_security_*.parquet")
            if 2018 <= int(path.stem.split("_")[2]) <= 2025
        )
    )
    screen_2018_2025 = (
        "try_cast({column} AS DATE) BETWEEN make_date(2018,1,1) AND make_date(2025,12,31)"
    )
    portno_tuple = integer_tuple(candidate_portnos)
    return [
        DatasetSpec(
            "LOCAL:fund_header_current",
            "AVAILABLE",
            "CRSP fund header (current/as-harvest)",
            "crsp.fund_hdr",
            (raw / "crsp_fund_hdr_full.parquet",),
            "baseline",
            "full local table; candidate rows separately audited",
            "current header snapshot",
            "first_offer_dt;end_dt",
            "crsp_fundno",
            "try_cast(first_offer_dt AS DATE)",
            "crsp_fundno",
            "crsp_fundno",
            None,
            "crsp_fundno|crsp_portno|ticker|cusip8|ncusip",
            "et_flag|index_fund_flag|first_offer_dt|end_dt",
            "historical benchmark name|benchmark assignment history",
            "raw baseline selected; full-file SHA256 comparison to rescue_remaining max copy logged",
            "candidate fund identification",
            "Current header does not by itself establish point-in-time benchmark assignment.",
        ),
        DatasetSpec(
            "LOCAL:fund_header_history",
            "AVAILABLE",
            "CRSP fund header history",
            "crsp.fund_hdr_hist",
            hist_parts,
            "rescue_remaining",
            "full local table",
            "effective-interval records",
            "chgdt;chgenddt",
            "crsp_fundno x effective interval",
            "try_cast(chgdt AS DATE)",
            "crsp_fundno",
            "crsp_fundno,try_cast(chgdt AS DATE),try_cast(chgenddt AS DATE)",
            None,
            "crsp_fundno|crsp_portno|ticker|cusip8|ncusip",
            "chgdt|chgenddt|et_flag|index_fund_flag",
            "historical benchmark name",
            "multi-part logical export; parts concatenated after identical schema inspection",
            "point-in-time fund identifier history",
            "Name, manager, adviser, CUSIP, and flag changes are metadata changes, not index reweightings.",
        ),
        DatasetSpec(
            "LOCAL:fund_portfolio_map",
            "AVAILABLE",
            "CRSP fund-to-portfolio map",
            "crsp.portnomap",
            (raw / "crsp_portnomap_full.parquet",),
            "baseline",
            "full local table",
            "effective-interval records",
            "begdt;enddt",
            "crsp_fundno x crsp_portno x interval",
            "try_cast(begdt AS DATE)",
            "crsp_portno",
            "crsp_fundno,crsp_portno,try_cast(begdt AS DATE),try_cast(enddt AS DATE)",
            None,
            "crsp_fundno|crsp_portno|ticker|cusip8|ncusip",
            "begdt|enddt",
            "index provider benchmark identifier",
            "raw baseline selected; full-file SHA256 comparison to rescue_remaining max copy logged",
            "effective fund-to-holdings portfolio mapping",
            "Effective intervals are enforced in the candidate fund audit.",
        ),
        DatasetSpec(
            "LOCAL:fund_summary2_2018_2025",
            "AVAILABLE",
            "CRSP fund summary2",
            "crsp.fund_summary2",
            summary2,
            "baseline annual partitions",
            "all rows dated 2018-2025",
            "fund summary observations",
            "caldt",
            "crsp_fundno x caldt x summary_period2",
            "try_cast(caldt AS DATE)",
            "crsp_fundno",
            "crsp_fundno,try_cast(caldt AS DATE),summary_period2",
            screen_2018_2025.format(column="caldt"),
            "crsp_fundno|crsp_portno|ticker|cusip8|ncusip",
            "nav_latest|tna_latest|asset_dt|et_flag|index_fund_flag",
            "daily holdings|official index weights",
            "annual partitions are complementary by caldt; not stacked with holdings",
            "fund status and low-frequency metadata",
            "Summary observations are not holdings reports or daily fund returns.",
        ),
        DatasetSpec(
            "LOCAL:candidate_holdings_2018_2025",
            "AVAILABLE_SCREENING_ONLY_WITH_GAPS",
            "CRSP holdings for 12 candidate ETFs",
            "crsp.holdings",
            tuple(holdings_files),
            "rescue_remaining annual portfolio batches",
            "candidate crsp_portno values, report_dt 2018-2025",
            "holdings-report snapshots",
            "report_dt (eff_dt retained separately)",
            "crsp_portno x report_dt x held security",
            "try_cast(report_dt AS DATE)",
            "try_cast(crsp_portno AS BIGINT)",
            "try_cast(crsp_portno AS BIGINT),try_cast(report_dt AS DATE),coalesce(cast(try_cast(permno AS BIGINT) AS VARCHAR),nullif(trim(cusip),''),nullif(trim(ticker),''),cast(crsp_company_key AS VARCHAR),concat('RANK:',cast(security_rank AS VARCHAR)))",
            f"try_cast(crsp_portno AS BIGINT) IN {portno_tuple} AND "
            + screen_2018_2025.format(column="report_dt"),
            "crsp_portno|crsp_company_key|permno|permco|cusip|ticker",
            "report_dt|eff_dt|percent_tna|nbr_shares|market_val",
            "filing date|publication date|download date|official assigned index weight|creation basket flag",
            "only batches whose saved QUERY.sql contains a candidate portno are read; parts are complementary within batch",
            "historical composition screening and validation only",
            "All 24 relevant batch _DONE part/row counts are reconciled to Parquet metadata. Holdings are not daily histories, exact index assignments, or creation/redemption baskets.",
        ),
        DatasetSpec(
            "LOCAL:legacy_daily_stock_2018_2024",
            "AVAILABLE",
            "Legacy CRSP daily stock/security file",
            "crsp.dsf",
            legacy_dsf,
            "baseline annual partitions",
            "all security-days dated 2018-2024; includes ETFs because no SHRCD filter is applied",
            "daily security",
            "date",
            "permno x date",
            "try_cast(date AS DATE)",
            "permno",
            "permno,try_cast(date AS DATE)",
            "try_cast(date AS DATE) BETWEEN make_date(2018,1,1) AND make_date(2024,12,31)",
            "permno|permco|cusip",
            "ret|retx|prc|openprc|bid|ask|cfacpr|cfacshr",
            "2025 in legacy schema",
            "baseline raw/crsp_dsf annual files selected; rescue allcols copies are not stacked",
            "stock and ETF daily return/price coverage; holdings price validation",
            "Open, bid, and ask fields are physically present; nonmissing coverage is measured for candidate ETFs.",
        ),
        DatasetSpec(
            "LOCAL:ciz_daily_stock_2025",
            "AVAILABLE_SCHEMA_TRANSITION",
            "New CRSP/CIZ daily stock/security file",
            "crsp.dsf_v2",
            (rescue / "newcrsp_crsp_dsf_v2_2025.parquet",),
            "rescue",
            "all security-days dated 2025",
            "daily security",
            "dlycaldt",
            "permno x dlycaldt",
            "try_cast(dlycaldt AS DATE)",
            "permno",
            "permno,try_cast(dlycaldt AS DATE)",
            "try_cast(dlycaldt AS DATE) BETWEEN make_date(2025,1,1) AND make_date(2025,12,31)",
            "permno|permco|hdrcusip|cusip|ticker",
            "dlyret|dlyretx|dlyprc|dlyopen|dlybid|dlyask|dlycumfacpr|dlycumfacshr",
            "legacy-named fields without harmonization",
            "newcrsp_crsp_dsf_v2 selected; byte-identical newcrsp_crsp_a_stock copy comparison logged",
            "2025 stock and ETF daily return/price extension",
            "Schema is not silently stacked with legacy DSF; projected fields are explicitly mapped.",
        ),
        DatasetSpec(
            "LOCAL:security_name_history",
            "AVAILABLE",
            "CRSP security name/identifier history",
            "crsp.dsenames",
            (raw / "crsp_dsenames_full.parquet",),
            "baseline",
            "full local table",
            "effective-interval records",
            "namedt;nameendt",
            "permno x name interval",
            "try_cast(namedt AS DATE)",
            "permno",
            "permno,try_cast(namedt AS DATE),try_cast(nameendt AS DATE)",
            None,
            "permno|permco|ncusip|cusip|ticker|tsymbol",
            "namedt|nameendt|shrcd|exchcd",
            "2025 legacy-name interval extension",
            "baseline selected; new CRSP stocknames_v2 used separately to verify 2025 identifiers",
            "effective security identifier mapping",
            "Ticker is an attribute within an effective interval, not the long-history join key.",
        ),
        DatasetSpec(
            "LOCAL:distributions_2018_2024",
            "AVAILABLE",
            "CRSP distributions/corporate actions",
            "crsp.dsedist",
            (raw / "crsp_dsedist.parquet",),
            "baseline",
            "events with exdt in 2018-2024",
            "event records",
            "exdt",
            "permno x exdt x distribution attributes",
            "try_cast(exdt AS DATE)",
            "permno",
            "permno,try_cast(exdt AS DATE),distcd,divamt,facpr,facshr",
            "try_cast(exdt AS DATE) BETWEEN make_date(2018,1,1) AND make_date(2024,12,31)",
            "permno|permco|cusip|acperm|accomp",
            "distcd|divamt|facpr|facshr|dclrdt|exdt|rcrddt|paydt",
            "2025 legacy event extract",
            "baseline full table selected; annual rescue allcols files not stacked",
            "corporate-action consistency screens",
            "Ex-date is used as the economic event date; other date concepts are retained separately.",
        ),
        DatasetSpec(
            "LOCAL:delistings_2018_2024",
            "AVAILABLE",
            "CRSP delistings",
            "crsp.dsedelist",
            (raw / "crsp_dsedelist.parquet",),
            "baseline",
            "events with dlstdt in 2018-2024",
            "event records",
            "dlstdt",
            "permno x dlstdt",
            "try_cast(dlstdt AS DATE)",
            "permno",
            "permno,try_cast(dlstdt AS DATE),dlstcd",
            "try_cast(dlstdt AS DATE) BETWEEN make_date(2018,1,1) AND make_date(2024,12,31)",
            "permno|permco|cusip",
            "dlstcd|dlret|dlretx|dlprc",
            "2025 legacy event extract",
            "baseline full table selected; annual rescue allcols files not stacked",
            "delisting/action screens",
            "Schema is inspected before use; not inferred from filename.",
        ),
        DatasetSpec(
            "LOCAL:share_history_2018_2024",
            "AVAILABLE_NOT_DAILY_FLOW",
            "CRSP share history",
            "crsp.dseshares",
            dseshares,
            "baseline annual partitions",
            "events/as-of records dated 2018-2024",
            "share-history records",
            "shrsdt",
            "permno x shrsdt",
            "try_cast(shrsdt AS DATE)",
            "permno",
            "permno,try_cast(shrsdt AS DATE)",
            "try_cast(shrsdt AS DATE) BETWEEN make_date(2018,1,1) AND make_date(2024,12,31)",
            "permno",
            "shrsdt|shrenddt|shrout|shrflg",
            "daily creation/redemption flow semantics",
            "annual partitions complementary; rescue allcols copies not stacked",
            "corporate-action/share consistency only",
            "Must not be relabeled as daily ETF creation/redemption flows.",
        ),
        DatasetSpec(
            "LOCAL:ccm_link_history",
            "AVAILABLE_EFFECTIVE_DATE_REQUIRED",
            "CRSP/Compustat effective-date link history",
            "crsp.ccmxpf_lnkhist",
            (rescue / "crsp_ccmxpf_lnkhist_full.parquet",),
            "rescue",
            "full local table",
            "effective-interval links",
            "linkdt;linkenddt",
            "gvkey x liid x lpermno x link interval",
            "try_cast(linkdt AS DATE)",
            "lpermno",
            "gvkey,liid,lpermno,try_cast(linkdt AS DATE),try_cast(linkenddt AS DATE),linktype,linkprim",
            None,
            "gvkey|lpermno|lpermco|liid",
            "linkdt|linkenddt|linktype|linkprim",
            "provider-specific float/company assignment mapping",
            "lnkhist selected as interval source; static linktable not stacked",
            "effective security-to-issuer linking",
            "Every historical join must enforce linkdt/linkenddt and resolve multiple valid links.",
        ),
        DatasetSpec(
            "LOCAL:holdings_company_map",
            "AVAILABLE_PARTIAL_IDENTIFIERS",
            "CRSP holdings company/security mapping",
            "crsp.holdings_co_info",
            company_parts,
            "rescue_remaining",
            "full local logical export",
            "mapping snapshot",
            "none",
            "crsp_company_key",
            "NULL",
            "crsp_company_key",
            "crsp_company_key,coalesce(cast(permno AS VARCHAR),cusip,ticker,security_name)",
            None,
            "crsp_company_key|permno|permco|cusip|ticker",
            "security_name",
            "effective dates",
            "multi-part logical export; schemas checked before union",
            "auxiliary holdings identifier mapping",
            "Lack of effective dates prevents treating this as a universal historical issuer crosswalk.",
        ),
        DatasetSpec(
            "LOCAL:comp_index_descriptions",
            "AVAILABLE_METADATA_ONLY",
            "Compustat index description/header",
            "comp.idx_index",
            (raw / "comp_idx_index_full.parquet",),
            "baseline",
            "full local table",
            "index metadata snapshot",
            "none",
            "gvkeyx",
            "NULL",
            "gvkeyx",
            "gvkeyx",
            None,
            "gvkeyx|idx13key|indexid|tic|tici",
            "conm|idxcstflg|idxstat|indexcat|indexgeo|indextype",
            "historical rule-assigned weights",
            "kept distinct from returns and constituent records",
            "identify available Compustat index codes",
            "One Nasdaq 100 metadata row is found; no Select Sector metadata row is found by name search.",
        ),
        DatasetSpec(
            "LOCAL:comp_index_constituents",
            "AVAILABLE_NON_TARGET",
            "Compustat index constituent intervals",
            "comp.indexcst_his",
            (remaining / "comp_indexcst_his_full/part_00001.parquet",),
            "rescue_remaining",
            "full local table; target-name join tested separately",
            "effective-interval membership records",
            "fromdate;thrudate",
            "gvkeyx x gvkey x iid x interval",
            "try_cast(fromdate AS DATE)",
            "gvkeyx",
            "gvkeyx,gvkey,iid,try_cast(fromdate AS DATE),try_cast(thrudate AS DATE)",
            None,
            "gvkeyx|gvkey|iid",
            "fromdate|thrudate",
            "constituent weights|assignment inputs",
            "single completed rescue part; kept distinct from idx_index metadata",
            "generic historical index membership only",
            "Target search finds zero constituent rows for the one Nasdaq 100 metadata key and no Select Sector metadata key.",
        ),
        DatasetSpec(
            "LOCAL:crsp_stock_industry_membership",
            "AVAILABLE_UNRESOLVED_INDEX_CODES",
            "CRSP stock industry/index membership",
            "crsp.stkindmembership_ind",
            (raw / "crsp_stkindmembership_ind_full.parquet",),
            "baseline",
            "full local table",
            "effective-interval membership records",
            "mbrstartdt;mbrenddt",
            "permno x indno x interval",
            "try_cast(mbrstartdt AS DATE)",
            "permno",
            "permno,indno,try_cast(mbrstartdt AS DATE),try_cast(mbrenddt AS DATE),mbrflg,indfam",
            None,
            "permno|indno|indfam",
            "mbrstartdt|mbrenddt|mbrflg",
            "complete index-series header needed to identify target families",
            "not joined to the 24-row Ziman-only index_type_map as if it described all indno values",
            "generic interval membership screening",
            "Suggestive membership rows are not labeled Select Sector or Nasdaq-100 without an authoritative series header.",
        ),
        DatasetSpec(
            "LOCAL:crsp_daily_index_returns",
            "AVAILABLE_NOT_MEMBERSHIP",
            "CRSP daily market index returns",
            "crsp.dsi",
            (raw / "crsp_dsi.parquet",),
            "baseline",
            "rows dated 2018-2024",
            "daily market series",
            "date",
            "date",
            "try_cast(date AS DATE)",
            "try_cast(date AS DATE)",
            "try_cast(date AS DATE)",
            "try_cast(date AS DATE) BETWEEN make_date(2018,1,1) AND make_date(2024,12,31)",
            "none (market series)",
            "vwretd|vwretx|ewretd|ewretx|sprtrn|spindx",
            "constituent identity|constituent weight",
            "kept distinct from membership and index descriptions",
            "market-return diagnostics only",
            "An index return series does not establish historical constituent membership or assignment.",
        ),
        DatasetSpec(
            "LOCAL:midas_security_2018_2025",
            "AVAILABLE_DAILY_NOT_INTRADAY",
            "WRDS MIDAS current security",
            "wrdssec_midas.security",
            midas,
            "post-snapshot near_taq canonical monthly files",
            "canonical monthly files for 2018-2025 only",
            "daily security microstructure",
            "date",
            "security category x ticker x date",
            "try_cast(date AS DATE)",
            "ticker",
            "security,ticker,try_cast(date AS DATE)",
            screen_2018_2025.format(column="date"),
            "ticker (security is a Stock/ETF category, not an identifier)",
            "litvol|ordervol|hidden|cancels|oddlots|daily rate/rank fields",
            "PERMNO|effective ticker link|intraday timestamps|quotes|trades",
            "monthly canonical files only; _superseded quarterly files excluded",
            "daily activity/liquidity screening controls",
            "Ticker is not used as a long-history join key and MIDAS is not intraday TAQ or OIB.",
        ),
    ]


def target_membership_evidence(connection: Any, project: Path) -> dict[str, Any]:
    index_path = project / "raw/comp_idx_index_full.parquet"
    constituents_path = (
        project / "raw/rescue_remaining/comp_indexcst_his_full/part_00001.parquet"
    )
    target_rows = connection.execute(
        """
        SELECT *
        FROM read_parquet(?)
        WHERE regexp_matches(upper(coalesce(conm, '')), 'NASDAQ.?100|SELECT SECTOR|SECTOR SPDR')
        ORDER BY gvkeyx
        """,
        [str(index_path)],
    ).df()
    if len(target_rows):
        quoted_keys = "(" + ",".join(
            "'" + str(value).replace("'", "''") + "'"
            for value in sorted(set(target_rows["gvkeyx"].dropna().astype(str)))
        ) + ")"
        constituent_count = connection.execute(
            f"SELECT count(*) FROM read_parquet(?) WHERE gvkeyx IN {quoted_keys}",
            [str(constituents_path)],
        ).fetchone()[0]
    else:
        constituent_count = 0
    return {
        "target_metadata_match_count": int(len(target_rows)),
        "constituent_rows_for_target_metadata_keys": int(constituent_count),
        "interpretation": (
            "Name search found one Nasdaq 100 metadata row and no Select Sector row; "
            "the Nasdaq metadata key has zero rows in the local comp.indexcst_his extract."
        ),
    }


def catalog_target_row(
    target_evidence: dict[str, Any], project: Path
) -> dict[str, Any]:
    sources = [
        project / "raw/comp_idx_index_full.parquet",
        project / "raw/rescue_remaining/comp_indexcst_his_full/part_00001.parquet",
        project / "raw/crsp_stkindmembership_ind_full.parquet",
    ]
    return {
        "evidence_key": "LOCAL:target_index_membership_search",
        "status": "TARGET_NOT_IDENTIFIED",
        "logical_dataset": "Exact target-family historical constituent membership",
        "source_wrds_table": "cross-table target search",
        "source_locator": relative_locator(sources, project),
        "archive_stage": "baseline + rescue_remaining",
        "selection_scope": "Select Sector and Nasdaq-100 name/key search",
        "frequency": "not established",
        "primary_date_column": "not established",
        "entity_key": "not established",
        "n_files": len(sources),
        "n_rows": target_evidence["constituent_rows_for_target_metadata_keys"],
        "min_date": "",
        "max_date": "",
        "n_unique_entities": 0,
        "n_unique_dates": 0,
        "duplicate_key_rows": "",
        "schema_hash": "",
        "available_identifiers": "one Compustat Nasdaq 100 gvkeyx metadata key; generic CRSP indno values",
        "critical_fields": "target index ID|constituent security ID|membership start/end|assigned weight",
        "missing_critical_fields": "verified target index ID-to-membership rows|assigned weights|rule inputs",
        "overlap_resolution": "tables inspected separately by object type; no inference from suggestive names/codes",
        "research_role": "target historical membership/assignment support",
        "notes": target_evidence["interpretation"]
        + " Holdings remain a screening proxy, not replacement membership.",
    }


def gap_rows(project: Path, fund_audit_rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    missing_snapshot_rows = [
        row["evidence_key"]
        for row in fund_audit_rows
        if int(row["n_missing_report_months"]) > 0
    ]
    common_sources = (
        "_migration_meta/FINAL_SCC_MANIFEST.tsv;"
        "p1_refraction_wrds_shared/raw/rescue_remaining/near_taq (direct scan);"
        "p1_refraction_wrds_shared/raw/comp_idx_index_full.parquet;"
        "p1_refraction_wrds_shared/raw/rescue_remaining/comp_indexcst_his_full/part_00001.parquet;"
        "p1_refraction_wrds_shared/raw/crsp_stkindmembership_ind_full.parquet"
    )
    return [
        {
            "evidence_key": "GAPA:exact_assignment_inputs",
            "status": "MISSING_LOCAL_INPUT",
            "gap_id": "exact_assignment_inputs",
            "scope": "2018-2025 Select Sector candidates and July 2023 Nasdaq-100 cross-check",
            "affected_dataset_or_funds": "XLB|XLC|XLE|XLF|XLI|XLK|XLP|XLRE|XLU|XLV|XLY|QQQ",
            "required_input": "official historical pro forma/assignment files or complete contemporaneous float-adjusted inputs and rule sequence",
            "why_needed": "distinguish exact rule-assigned weights from observed ETF holdings and uncapped reference weights",
            "next_action": "retrieve source-dated official assignment/pro forma files or complete reproducible provider inputs; do not infer from holdings",
            "source_locator": common_sources,
            "notes": "No exact assignment-weight dataset was identified in the executed manifest, post-snapshot, schema, and target-table inspection. This is an archive gap, not proof that assignments do not exist.",
        },
        {
            "evidence_key": "GAPA:target_membership",
            "status": "UNRESOLVED_LOCAL_INPUT",
            "gap_id": "target_membership",
            "scope": "historical Select Sector and Nasdaq-100 constituent intervals",
            "affected_dataset_or_funds": "all candidate funds",
            "required_input": "verified target index identifiers and point-in-time constituent membership intervals",
            "why_needed": "separate fund holdings from index membership and define the contemporaneous comparison universe",
            "next_action": "obtain official point-in-time constituent records or an authorized target-series header plus membership extract",
            "source_locator": common_sources,
            "notes": "The local Compustat header has one Nasdaq 100 metadata row but its key has zero rows in local indexcst_his; no Select Sector header-name match was found. Generic CRSP indno membership cannot be labeled as a target family without the missing series header.",
        },
        {
            "evidence_key": "GAPA:holdings_timing_metadata",
            "status": "MISSING_FIELDS",
            "gap_id": "holdings_timing_metadata",
            "scope": "CRSP candidate ETF holdings snapshots",
            "affected_dataset_or_funds": "all candidate funds",
            "required_input": "filing date, first publication/availability date-time, and download/vintage metadata with documented semantics",
            "why_needed": "prevent report/as-of dates from being misdescribed as information available to traders",
            "next_action": "source provider documentation/vintage metadata or contemporaneous fund publications; preserve report_dt separately",
            "source_locator": "p1_refraction_wrds_shared/raw/rescue_remaining/crsp_holdings_etf_YYYY_bNNNN/part_*.parquet",
            "notes": "Executed schema inspection found report_dt and eff_dt but no filing/publication/download fields; eff_dt is not silently reinterpreted.",
        },
        {
            "evidence_key": "GAPA:holdings_snapshot_gaps",
            "status": "OBSERVED_COVERAGE_GAPS",
            "gap_id": "holdings_snapshot_gaps",
            "scope": "eligible calendar months within candidate portfolio-map intervals",
            "affected_dataset_or_funds": "|".join(missing_snapshot_rows),
            "required_input": "verification whether each absent candidate month is non-reporting, a valid zero-row state, or a missing snapshot",
            "why_needed": "avoid interpolating holdings across potential reweighting dates",
            "next_action": "check saved batch completion metadata and, if design-relevant, authorized source documentation for the specific fund-month",
            "source_locator": "fund_identifier_and_coverage_audit.csv (missing_report_months) and saved crsp_holdings batch _DONE.json files",
            "notes": "Calendar-month absence is a coverage flag, not proof of failed extraction or proof the fund did not report.",
        },
        {
            "evidence_key": "GAPA:provider_issuer_float_mapping",
            "status": "MISSING_LOCAL_INPUT",
            "gap_id": "provider_issuer_float_mapping",
            "scope": "company-level capping and float-adjusted assignment replay",
            "affected_dataset_or_funds": "all candidate target indexes",
            "required_input": "provider-consistent security-line-to-company aggregation and contemporaneous investable-weight/float factors",
            "why_needed": "CRSP PERMCO/CCM links do not automatically reproduce the index provider's company aggregation or float-adjusted capitalization",
            "next_action": "retrieve methodology-version-specific provider mappings/float factors or bound uncertainty explicitly",
            "source_locator": "p1_refraction_wrds_shared/raw/rescue/crsp_ccmxpf_lnkhist_full.parquet;p1_refraction_wrds_shared/raw/rescue_remaining/crsp_holdings_co_info_full_max/part_*.parquet",
            "notes": "Local effective-date issuer links support reconciliation but are not asserted to equal provider assignment inputs.",
        },
    ]


def validate_paths(paths: Iterable[Path]) -> None:
    missing = [str(path) for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError("Required files missing: " + "; ".join(missing))


def parse_manifest(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t", 1)
            if len(parts) != 2:
                raise ValueError(f"Malformed manifest line {line_number}: {line!r}")
            rows.append({"bytes": int(parts[0]), "path": parts[1]})
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--private-output-dir",
        type=Path,
        help=(
            "Optional permission-restricted SCC-only directory for detailed file "
            "lineage and licensed identifiers. Never copy this directory to Git."
        ),
    )
    args = parser.parse_args(argv)

    started = time.time()
    archive = args.archive.resolve()
    project = archive / PROJECT_RELATIVE
    manifest_path = archive / MANIFEST_RELATIVE
    post_snapshot = archive / POST_SNAPSHOT_RELATIVE
    output_dir = args.output_dir.resolve()
    ensure_outside_archive(output_dir, archive)
    private_output_dir = (
        args.private_output_dir.resolve() if args.private_output_dir else None
    )
    if private_output_dir is not None:
        ensure_outside_archive(private_output_dir, archive)
        ensure_outside_owning_git_worktree(private_output_dir, Path(__file__))
        if private_output_dir == output_dir:
            raise ValueError("Public and private output directories must differ")
    validate_paths([manifest_path])
    if not project.is_dir() or not post_snapshot.is_dir():
        raise FileNotFoundError("Archive project or post-snapshot directory is missing")
    output_dir.mkdir(parents=True, exist_ok=True)
    if private_output_dir is not None:
        private_output_dir.mkdir(parents=True, exist_ok=True)
        private_output_dir.chmod(0o700)

    import duckdb
    import pandas as pd
    import pyarrow
    import pyarrow.parquet as pq

    connection = duckdb.connect(database=":memory:")
    connection.execute("SET threads=4")
    connection.execute("SET preserve_insertion_order=false")

    manifest = parse_manifest(manifest_path)
    near_taq_files = sorted(path for path in post_snapshot.rglob("*") if path.is_file())
    canonical_midas_all = sorted((post_snapshot / "midas").glob("midas_security_*.parquet"))
    superseded_midas = sorted((post_snapshot / "_superseded").glob("midas_security_*.parquet"))

    metadata = load_candidate_metadata(project, pd)
    candidate_portnos = sorted(
        {
            int(float(value))
            for value in metadata["current"]["crsp_portno"].dropna()
        }
    )
    candidate_fundnos = sorted(
        {
            int(float(value))
            for value in metadata["current"]["crsp_fundno"].dropna()
        }
    )
    etf_permnos = sorted(
        {
            int(value)
            for value in metadata["names"]["permno"].dropna()
        }
        | {
            int(value)
            for value in metadata["new_names"]["permno"].dropna()
        }
    )
    holdings_files, holding_batches = create_holdings_table(
        connection, project, candidate_portnos, pq
    )
    daily_files = create_daily_price_table(connection, project, etf_permnos)

    specs = catalog_specs(project, holdings_files, candidate_portnos)
    for spec in specs:
        validate_paths(spec.files)
    catalog = [build_catalog_row(connection, spec, project, pq) for spec in specs]

    target_evidence = target_membership_evidence(connection, project)
    catalog.append(catalog_target_row(target_evidence, project))
    catalog.sort(key=lambda row: row["evidence_key"])

    funds = fund_rows(
        connection,
        metadata,
        project,
        holdings_files,
        daily_files,
    )
    funds.sort(key=lambda row: (row["fund_ticker"], int(row["period"])))
    gaps = gap_rows(project, funds)

    comparisons = [
        compare_byte_copies(
            project / "raw/crsp_fund_hdr_full.parquet",
            project / "raw/rescue_remaining/crsp_fund_hdr_full_max/part_00001.parquet",
        ),
        compare_byte_copies(
            project / "raw/crsp_portnomap_full.parquet",
            project / "raw/rescue_remaining/crsp_portnomap_full_max/part_00001.parquet",
        ),
        compare_byte_copies(
            project / "raw/rescue/newcrsp_crsp_dsf_v2_2025.parquet",
            project / "raw/rescue/newcrsp_crsp_a_stock_dsf_v2_2025.parquet",
        ),
    ]

    manifest_paths = [row["path"] for row in manifest]
    target_path_pattern = re.compile(
        r"select.?sector|nasdaq|ndx|reweight|rebalance|indexcst|stkindmembership",
        re.IGNORECASE,
    )
    target_manifest_hits = [path for path in manifest_paths if target_path_pattern.search(path)]
    near_taq_target_hits = [
        str(path.relative_to(project))
        for path in near_taq_files
        if target_path_pattern.search(str(path.relative_to(project)))
    ]

    evidence = {
        "run": {
            "started_utc": datetime.fromtimestamp(started, timezone.utc).isoformat(),
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.time() - started, 3),
            "python": sys.version,
            "archive_write_policy": "read-only; program opens archive files only for reading",
        },
        "versions": {
            "pandas": pd.__version__,
            "pyarrow": pyarrow.__version__,
            "duckdb": duckdb.__version__,
        },
        "archive_inventory": {
            "baseline_manifest": str(manifest_path),
            "baseline_manifest_rows": len(manifest),
            "baseline_manifest_bytes": sum(row["bytes"] for row in manifest),
            "post_snapshot_path": str(post_snapshot),
            "post_snapshot_file_count": len(near_taq_files),
            "canonical_midas_file_count": len(canonical_midas_all),
            "superseded_midas_file_count": len(superseded_midas),
            "target_keyword_manifest_hit_count": len(target_manifest_hits),
            "target_keyword_manifest_hits": target_manifest_hits,
            "target_keyword_near_taq_hits": near_taq_target_hits,
        },
        "candidate_identifiers": {
            "tickers": list(CANDIDATE_TICKERS),
            "crsp_fundnos": candidate_fundnos,
            "crsp_portnos": candidate_portnos,
            "security_permnos": etf_permnos,
        },
        "holdings_batches": holding_batches,
        "holdings_part_file_count": len(holdings_files),
        "overlap_comparisons": comparisons,
        "target_membership_search": target_evidence,
        "output_schemas": {
            "local_data_catalog.csv": list(CATALOG_COLUMNS),
            "fund_identifier_and_coverage_audit.csv": list(FUND_COLUMNS),
            "remaining_input_gaps_stage_a.csv": list(GAP_COLUMNS),
        },
        "method_notes": {
            "price_match": "Latest nonmissing CRSP price on or before holdings report_dt, no more than 7 calendar days earlier.",
            "holding_duplicate_key": "crsp_portno, report_dt, fallback held_key: PERMNO then CUSIP then ticker then company key then security rank.",
            "calendar_month_gaps": "Eligible calendar months under the fund-to-portfolio map; absence is a flag, not a failed-query conclusion.",
            "no_regressions": True,
            "raw_rows_exported": False,
        },
    }

    public_catalog = make_public_catalog(catalog)
    public_funds = make_public_fund_rows(funds)
    public_gaps = make_public_gap_rows(gaps)
    public_evidence = make_public_evidence(evidence)

    write_csv(
        output_dir / "local_data_catalog.csv", public_catalog, CATALOG_COLUMNS
    )
    write_csv(
        output_dir / "fund_identifier_and_coverage_audit.csv", public_funds, FUND_COLUMNS
    )
    write_csv(
        output_dir / "remaining_input_gaps_stage_a.csv", public_gaps, GAP_COLUMNS
    )
    (output_dir / "stage_a_evidence.json").write_text(
        json.dumps(public_evidence, indent=2, sort_keys=True, default=format_value)
        + "\n",
        encoding="utf-8",
    )

    if private_output_dir is not None:
        private_files = (
            (
                "local_data_catalog_private.csv",
                catalog,
                CATALOG_COLUMNS,
            ),
            (
                "fund_identifier_and_coverage_audit_private.csv",
                funds,
                FUND_COLUMNS,
            ),
            (
                "remaining_input_gaps_stage_a_private.csv",
                gaps,
                GAP_COLUMNS,
            ),
        )
        for filename, rows, columns in private_files:
            path = private_output_dir / filename
            write_csv(path, rows, columns)
            path.chmod(0o600)
        private_evidence_path = private_output_dir / "stage_a_private_evidence.json"
        private_evidence_path.write_text(
            json.dumps(evidence, indent=2, sort_keys=True, default=format_value) + "\n",
            encoding="utf-8",
        )
        private_evidence_path.chmod(0o600)

    summary = {
        "catalog_rows": len(catalog),
        "fund_audit_rows": len(funds),
        "gap_rows": len(gaps),
        "holdings_part_files_read": len(holdings_files),
        "candidate_funds": len(CANDIDATE_TICKERS),
        "screen_start": SCREEN_START.isoformat(),
        "screen_end": SCREEN_END.isoformat(),
        "output_profile": "PUBLIC_AGGREGATE_REDACTED",
        "private_lineage_written": private_output_dir is not None,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
