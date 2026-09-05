#!/usr/bin/env python3
"""Run the targeted P1 data-contract golden sample and small pilot.

This program reads only the exact files registered in golden_sample_spec.json.
It never enumerates the holdings archive and it never produces a Gate result.
PILOT_PASS.json is written only when every registered invariant succeeds.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import numpy as np
import pandas as pd
import pyarrow

from pilot_contract import (
    CODE_HASH_ALGORITHM,
    JSON_HASH_ALGORITHM,
    PILOT_SCHEMA_VERSION,
    RAW_HASH_ALGORITHM,
    REQUIRED_PILOT_ARTIFACTS,
    candidate_implementation_conformance,
    canonical_json_bytes,
    canonical_json_hash,
    compute_code_fileset_hash,
    compute_json_file_hash,
    compute_raw_file_hash,
    load_json_document,
    require_regular_file,
)


DEFAULT_ARCHIVE = Path(
    "/projectnb/econdept/qluo/P1_Refraction_WRDS/WRDS_MIRROR_20260902"
)
DEFAULT_MANIFEST = DEFAULT_ARCHIVE / "_migration_meta" / "FINAL_SCC_MANIFEST.tsv"
WRDS_SUBDIR = "p1_refraction_wrds_shared"


def strict_json(
    path: Path,
    *,
    archive_root: Path | None = None,
) -> dict[str, Any]:
    value, _ = load_json_document(
        path,
        label="Pilot JSON input",
        archive_root=archive_root,
    )
    return dict(value)


def json_default(value: Any) -> Any:
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return None if not np.isfinite(value) else float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if value is pd.NA or (isinstance(value, float) and not math.isfinite(value)):
        return None
    raise TypeError(f"cannot serialize {type(value).__name__}")


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            indent=2,
            default=json_default,
        )
        + "\n",
        encoding="utf-8",
    )


def make_public_receipt(pilot_document: dict[str, Any]) -> dict[str, Any]:
    """Return a Git-safe receipt without proprietary invariant result payloads."""

    return {
        "schema_version": pilot_document["schema_version"],
        "status": pilot_document["status"],
        "created_at_utc": pilot_document["created_at_utc"],
        "pilot_run_id": pilot_document["pilot_run_id"],
        "hashes": pilot_document["hashes"],
        "artifacts": pilot_document["artifacts"],
        "golden_sample": {
            "categories": pilot_document["golden_sample"]["categories"],
            "case_count": sum(pilot_document["golden_sample"]["categories"].values()),
            "content_sha256": pilot_document["golden_sample"]["content_sha256"],
        },
        "raw_trace_inspection": {
            "observation_count": pilot_document["raw_trace_inspection"][
                "observation_count"
            ],
            "all_reconciled": pilot_document["raw_trace_inspection"][
                "all_reconciled"
            ],
            "artifact_sha256": pilot_document["raw_trace_inspection"][
                "artifact_sha256"
            ],
        },
        "invariants": [
            {"id": item["id"], "passed": item["passed"]}
            for item in pilot_document["invariants"]
        ],
    }


def safe_raw_path(wrds_root: Path, relative: str) -> Path:
    posix = PurePosixPath(relative)
    if posix.is_absolute() or not posix.parts or any(part in {"", ".", ".."} for part in posix.parts):
        raise ValueError(f"unsafe raw path in golden sample: {relative!r}")
    if posix.parts[0] != "raw":
        raise ValueError(f"golden input must be under raw/: {relative!r}")
    path = wrds_root.joinpath(*posix.parts)
    return require_regular_file(path, label=f"registered raw input {relative}")


def registered_raw_inputs(spec: dict[str, Any]) -> list[str]:
    shared = spec["shared_inputs"]
    paths: set[str] = set()
    for key, value in shared.items():
        if isinstance(value, str):
            paths.add(value)
        elif isinstance(value, list):
            paths.update(value)
        elif isinstance(value, dict):
            paths.update(value.values())
        else:
            raise ValueError(f"unexpected shared input type for {key}")
    paths.update(case["holdings_file"] for case in spec["cases"])
    return sorted(paths)


def manifest_inventory(manifest_path: Path) -> tuple[str, dict[str, int]]:
    digest, _ = compute_raw_file_hash(manifest_path, label="pilot input manifest")
    inventory: dict[str, int] = {}
    for line_no, line in enumerate(manifest_path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            size_text, relative = line.split("\t", 1)
            size = int(size_text)
        except Exception as exc:
            raise ValueError(f"malformed manifest line {line_no}") from exc
        if relative in inventory:
            raise ValueError(f"duplicate manifest entry {relative!r}")
        inventory[relative] = size
    return digest, inventory


def validate_and_hash_inputs(
    wrds_root: Path,
    relative_paths: list[str],
    manifest: dict[str, int],
) -> dict[str, dict[str, Any]]:
    evidence: dict[str, dict[str, Any]] = {}
    for relative in relative_paths:
        path = safe_raw_path(wrds_root, relative)
        if relative not in manifest:
            raise ValueError(f"registered raw input absent from manifest: {relative}")
        actual_size = path.stat().st_size
        if actual_size != manifest[relative]:
            raise ValueError(
                f"manifest size mismatch for {relative}: {manifest[relative]} != {actual_size}"
            )
        digest, _ = compute_raw_file_hash(path, label=f"registered raw input {relative}")
        evidence[relative] = {
            "sha256": digest,
            "bytes": actual_size,
            "manifest_size_match": True,
        }
    return evidence


def read_with_provenance(path: Path, relative: str, columns: list[str] | None = None) -> pd.DataFrame:
    frame = pd.read_parquet(path, columns=columns)
    frame["_source_file"] = relative
    frame["_raw_row_number_zero_based"] = np.arange(len(frame), dtype=np.int64)
    return frame


def dates(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for column in columns:
        if column in frame:
            frame[column] = pd.to_datetime(frame[column], errors="coerce")
    return frame


def active_interval(
    frame: pd.DataFrame,
    date: pd.Timestamp,
    start: str,
    end: str,
) -> pd.DataFrame:
    end_dates = frame[end].fillna(pd.Timestamp("2262-04-11"))
    return frame.loc[frame[start].le(date) & end_dates.ge(date)].copy()


def finite_float(value: Any) -> float | None:
    number = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    return float(number) if pd.notna(number) and np.isfinite(number) else None


def clean_text(value: Any) -> str:
    return "" if pd.isna(value) else str(value)


def snapshot_etf_security(
    fundno: int,
    report_dt: pd.Timestamp,
    headers: pd.DataFrame,
    stocknames: pd.DataFrame,
) -> tuple[int | None, dict[str, Any]]:
    h = active_interval(
        headers.loc[headers.crsp_fundno.eq(fundno)], report_dt, "chgdt", "chgenddt"
    )
    if len(h) != 1:
        return None, {"status": "NO_UNIQUE_EFFECTIVE_HEADER", "header_rows": len(h)}
    row = h.iloc[0]
    ticker = clean_text(row.get("ticker")).upper()
    ncusip = clean_text(row.get("ncusip")).upper()[:8]
    n = active_interval(stocknames, report_dt, "namedt", "nameenddt")
    n = n.loc[
        n.ticker.fillna("").astype(str).str.upper().eq(ticker)
        & n.cusip.fillna("").astype(str).str.upper().str[:8].eq(ncusip)
        & n.securitytype.fillna("").astype(str).str.upper().eq("FUND")
        & n.securitysubtype.fillna("").astype(str).str.upper().eq("ETF")
    ].copy()
    if n.permno.nunique() != 1:
        return None, {
            "status": "NO_UNIQUE_EFFECTIVE_ETF_SECURITY",
            "header_ticker": ticker,
            "header_cusip8": ncusip,
            "stockname_rows": len(n),
        }
    selected = n.sort_values(["namedt", "_raw_row_number_zero_based"]).iloc[-1]
    return int(selected.permno), {
        "status": "VERIFIED",
        "ticker": ticker,
        "cusip8": ncusip,
        "header_source_file": row["_source_file"],
        "header_raw_row": int(row["_raw_row_number_zero_based"]),
        "stockname_source_file": selected["_source_file"],
        "stockname_raw_row": int(selected["_raw_row_number_zero_based"]),
    }


def classify_underlying(
    permno: int,
    report_dt: pd.Timestamp,
    stocknames: pd.DataFrame,
) -> tuple[bool, dict[str, Any]]:
    n = active_interval(
        stocknames.loc[stocknames.permno.eq(permno)],
        report_dt,
        "namedt",
        "nameenddt",
    )
    if n.empty:
        return False, {"status": "NO_EFFECTIVE_STOCKNAME"}
    row = n.sort_values(["namedt", "_raw_row_number_zero_based"]).iloc[-1]
    common = (
        clean_text(row.get("sharetype")).upper() == "NS"
        and clean_text(row.get("securitytype")).upper() == "EQTY"
        and clean_text(row.get("securitysubtype")).upper() == "COM"
        and clean_text(row.get("usincflg")).upper() == "Y"
    )
    return common, {
        "status": "US_COMMON" if common else "NOT_US_COMMON",
        "source_file": row["_source_file"],
        "raw_row": int(row["_raw_row_number_zero_based"]),
    }


def exact_tna_bundle(
    portno: int,
    report_dt: pd.Timestamp,
    mapping: pd.DataFrame,
    headers: pd.DataFrame,
    monthly_by_year: dict[int, pd.DataFrame],
) -> dict[str, Any]:
    active = active_interval(
        mapping.loc[mapping.crsp_portno.eq(portno)], report_dt, "begdt", "enddt"
    )
    mapped_funds = sorted(active.crsp_fundno.dropna().astype(int).unique())
    tna_source = monthly_by_year.get(report_dt.year)
    if tna_source is None:
        candidate_exact = pd.DataFrame()
    else:
        candidate_exact = tna_source.loc[
            tna_source.crsp_fundno.isin(mapped_funds) & tna_source.caldt.eq(report_dt)
        ].copy()
    exact_funds = set(candidate_exact.crsp_fundno.dropna().astype(int)) if len(candidate_exact) else set()
    active_funds: list[int] = []
    affirmatively_inactive: list[int] = []
    unresolved_activity: list[int] = []
    for fundno in mapped_funds:
        history = headers.loc[headers.crsp_fundno.eq(fundno)]
        history_active = active_interval(history, report_dt, "chgdt", "chgenddt")
        if fundno in exact_funds or len(history_active):
            active_funds.append(fundno)
        elif len(history) and history.chgenddt.notna().any() and history.chgenddt.max() < report_dt:
            affirmatively_inactive.append(fundno)
        else:
            unresolved_activity.append(fundno)
    exact = candidate_exact.loc[candidate_exact.crsp_fundno.isin(active_funds)].copy()
    duplicates = (
        exact.groupby("crsp_fundno").size().loc[lambda x: x.gt(1)].index.astype(int).tolist()
        if len(exact)
        else []
    )
    present = sorted(exact.crsp_fundno.dropna().astype(int).unique()) if len(exact) else []
    missing = sorted(set(active_funds) - set(present))
    complete = bool(active_funds) and not missing and not duplicates and not unresolved_activity
    if complete:
        selected = exact.sort_values("_raw_row_number_zero_based").drop_duplicates("crsp_fundno")
        values = pd.to_numeric(selected.mtna, errors="coerce")
        complete = bool(values.notna().all() and values.gt(0).all())
    else:
        selected = exact
        values = pd.Series(dtype=float)
    pooled_million = float(values.sum()) if complete else None
    rows = []
    for _, row in selected.iterrows():
        rows.append(
            {
                "crsp_fundno": int(row["crsp_fundno"]),
                "caldt": pd.Timestamp(row["caldt"]).date().isoformat(),
                "mtna_millions": finite_float(row["mtna"]),
                "source_file": row["_source_file"],
                "raw_row": int(row["_raw_row_number_zero_based"]),
            }
        )
    interval_map_rows = []
    for _, row in active.iterrows():
        interval_map_rows.append(
            {
                "crsp_fundno": int(row["crsp_fundno"]),
                "crsp_portno": int(row["crsp_portno"]),
                "begdt": pd.Timestamp(row["begdt"]).date().isoformat(),
                "enddt": (
                    pd.Timestamp(row["enddt"]).date().isoformat()
                    if pd.notna(row["enddt"])
                    else None
                ),
                "source_file": row["_source_file"],
                "raw_row": int(row["_raw_row_number_zero_based"]),
            }
        )
    map_rows = [
        row for row in interval_map_rows if row["crsp_fundno"] in active_funds
    ]
    return {
        "active_share_class_ids": active_funds,
        "mapped_share_class_ids": mapped_funds,
        "affirmatively_inactive_mapped_fundnos": affirmatively_inactive,
        "unresolved_activity_fundnos": unresolved_activity,
        "active_mapping_rows": map_rows,
        "interval_mapping_rows": interval_map_rows,
        "exact_tna_rows": rows,
        "missing_exact_tna_fundnos": missing,
        "duplicate_exact_tna_fundnos": duplicates,
        "complete": complete,
        "portfolio_tna_millions": pooled_million,
    }


def identity_result(
    snapshot: pd.DataFrame,
    portfolio_tna_millions: float | None,
    config: dict[str, Any],
) -> dict[str, Any]:
    if portfolio_tna_millions is None or portfolio_tna_millions <= 0:
        return {"testable": False, "passed": False, "reason": "NO_EXACT_DATE_COMPLETE_CLASS_TNA"}
    denominator = portfolio_tna_millions * 1_000_000.0
    work = snapshot.loc[snapshot.percent_tna.notna() & snapshot.market_val.notna()].copy()
    work["reported_weight"] = pd.to_numeric(work.percent_tna, errors="coerce") / 100.0
    work["value_weight"] = pd.to_numeric(work.market_val, errors="coerce") / denominator
    work["absolute_residual"] = (work.reported_weight - work.value_weight).abs()
    denominator_rows = work.loc[work.reported_weight.abs().ge(0.001) & work.reported_weight.ne(0)].copy()
    denominator_rows["implied_tna"] = denominator_rows.market_val / denominator_rows.reported_weight
    median_implied = float(denominator_rows.implied_tna.median()) if len(denominator_rows) else math.nan
    median_relative = abs(median_implied / denominator - 1.0) if np.isfinite(median_implied) else math.inf
    max_row = float(work.absolute_residual.max()) if len(work) else math.inf
    row_tol = float(config["tolerances"]["position_weight_absolute"])
    denom_tol = float(config["tolerances"]["median_implied_portfolio_tna_relative"])
    passed = bool(len(work) and len(denominator_rows) and max_row <= row_tol and median_relative <= denom_tol)
    return {
        "testable": True,
        "passed": passed,
        "eligible_position_rows": len(work),
        "denominator_test_rows": len(denominator_rows),
        "position_weight_absolute_tolerance": row_tol,
        "max_position_absolute_residual": max_row,
        "median_implied_tna_relative_tolerance": denom_tol,
        "median_implied_tna_relative_error": median_relative,
        "portfolio_tna_millions": portfolio_tna_millions,
        "reported_percent_tna_sum": float(pd.to_numeric(snapshot.percent_tna, errors="coerce").sum()),
        "market_val_sum_usd": float(pd.to_numeric(snapshot.market_val, errors="coerce").sum()),
    }


def date_scoped_pro_rata_evidence(
    spec: dict[str, Any],
    evidence_id: str | None,
    report_dt: pd.Timestamp,
    active_share_class_count: int,
) -> tuple[bool, str | None]:
    """Require the registered single-UIT or pooled-multiclass SEC evidence rule."""

    if not evidence_id or evidence_id not in spec["external_evidence"]:
        return False, None
    evidence = spec["external_evidence"][evidence_id]
    covered_dates = evidence.get("covered_pilot_dates")
    if (
        evidence.get("review_status") != "VERIFIED"
        or type(covered_dates) is not list
        or report_dt.date().isoformat() not in covered_dates
    ):
        return False, None
    expected_rule = (
        "SINGLE_CLASS_UIT_PRO_RATA"
        if active_share_class_count == 1
        else "POOLED_MULTICLASS_PRO_RATA"
        if active_share_class_count > 1
        else None
    )
    if evidence.get("verification_rule") != expected_rule:
        return False, None
    required_fields = (
        {"prospectus_url"}
        if expected_rule == "SINGLE_CLASS_UIT_PRO_RATA"
        else {
            "statutory_filing_url",
            "multiple_class_plan_url",
            "exact_date_ncsr_url",
        }
        if expected_rule == "POOLED_MULTICLASS_PRO_RATA"
        else set()
    )
    if not required_fields or any(
        type(evidence.get(field)) is not str or not evidence[field].startswith("https://www.sec.gov/")
        for field in required_fields
    ):
        return False, None
    return True, expected_rule


def build_case_results(
    spec: dict[str, Any],
    config: dict[str, Any],
    holdings: dict[str, pd.DataFrame],
    mapping: pd.DataFrame,
    headers: pd.DataFrame,
    stocknames: pd.DataFrame,
    monthly: dict[int, pd.DataFrame],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    results: list[dict[str, Any]] = []
    snapshots: dict[str, dict[str, Any]] = {}
    stale_limit = int(config["date_rules"]["maximum_report_age_at_as_of_days"])
    derivative_threshold = float(
        config["eligibility_rules"]["derivative_gross_percent_tna_threshold"]
    )
    derivative_pattern = re.compile(
        config["eligibility_rules"]["derivative_name_pattern"], re.I
    )
    completeness_floor = float(
        config["eligibility_rules"]["minimum_absolute_reported_percent_tna"]
    )
    for case in spec["cases"]:
        case_id = case["case_id"]
        portno = int(case["crsp_portno"])
        fundno = int(case["etf_crsp_fundno"])
        report_dt = pd.Timestamp(case["report_dt"])
        as_of = pd.Timestamp(case["as_of_date"])
        full = holdings[case["holdings_file"]]
        snapshot = full.loc[
            full.crsp_portno.eq(portno) & full.report_dt.eq(report_dt)
        ].copy()
        if snapshot.empty:
            raise ValueError(f"golden case has no raw rows: {case_id}")
        max_eff = snapshot.eff_dt.max()
        min_eff = snapshot.eff_dt.min()
        report_age = int((as_of - report_dt).days)
        publication_delay = int((max_eff - report_dt).days) if pd.notna(max_eff) else None
        available_from = (
            max_eff.normalize() + pd.Timedelta(days=1) if pd.notna(max_eff) else pd.NaT
        )
        available = bool(pd.notna(available_from) and as_of >= available_from)
        tna = exact_tna_bundle(portno, report_dt, mapping, headers, monthly)
        identity = identity_result(snapshot, tna["portfolio_tna_millions"], config)
        header_active = active_interval(
            headers.loc[headers.crsp_fundno.eq(fundno)], report_dt, "chgdt", "chgenddt"
        )
        historical_f = bool(len(header_active) == 1 and str(header_active.iloc[0].et_flag) == "F")
        etf_security_id, etf_security = snapshot_etf_security(
            fundno, report_dt, headers, stocknames
        )
        external_evidence = case.get("external_pro_rata_evidence")
        evidence_registered, evidence_rule = date_scoped_pro_rata_evidence(
            spec,
            external_evidence,
            report_dt,
            len(tna["active_share_class_ids"]),
        )
        pro_rata = bool(
            identity.get("passed")
            and historical_f
            and etf_security_id is not None
            and evidence_registered
            and fundno in tna["active_share_class_ids"]
        )
        name = snapshot.security_name.fillna("").astype(str)
        derivative_mask = name.str.contains(derivative_pattern, regex=True)
        derivative_gross_pct = float(
            pd.to_numeric(snapshot.loc[derivative_mask, "percent_tna"], errors="coerce")
            .abs()
            .sum()
        )
        non_equity_count = int(snapshot.permno.isna().sum())
        structure_excluded = derivative_gross_pct >= derivative_threshold
        absolute_pct_sum = float(pd.to_numeric(snapshot.percent_tna, errors="coerce").abs().sum())
        reasons: list[str] = []
        if not available:
            reasons.append("HOLDINGS_NOT_YET_AVAILABLE")
        if report_age > stale_limit:
            reasons.append("HOLDINGS_REPORT_AGE_EXCEEDS_120_DAYS")
        if publication_delay is not None and publication_delay > stale_limit:
            reasons.append("PUBLICATION_DELAY_EXCEEDS_120_DAYS")
        if absolute_pct_sum < completeness_floor:
            reasons.append("HOLDINGS_SNAPSHOT_INCOMPLETE")
        if not tna["complete"]:
            reasons.append("NO_EXACT_DATE_COMPLETE_CLASS_TNA")
        elif not identity["passed"]:
            reasons.append("PORTFOLIO_TNA_IDENTITY_FAILED")
        if not historical_f:
            reasons.append("HISTORICAL_ETF_STATUS_UNVERIFIED")
        if etf_security_id is None:
            reasons.append("ETF_SECURITY_CROSSWALK_UNVERIFIED")
        if not evidence_registered:
            reasons.append("EXTERNAL_ETF_FORMAT_EVIDENCE_MISSING")
        if not pro_rata:
            reasons.append("PRO_RATA_CLAIM_UNVERIFIED")
        if structure_excluded:
            reasons.append("DERIVATIVE_OR_NON_EQUITY_PORTFOLIO")
        reasons = sorted(set(reasons))
        final_eligible = not reasons
        expected_reasons = set(case["expected_reasons"])
        expected_match = expected_reasons.issubset(reasons) and (
            bool(case["expected_final_eligible"]) == final_eligible
        )
        result = {
            "case_id": case_id,
            "crsp_portno": portno,
            "etf_crsp_fundno": fundno,
            "etf_security_id": etf_security_id,
            "report_dt": report_dt.date().isoformat(),
            "as_of_date": as_of.date().isoformat(),
            "holdings_rows": len(snapshot),
            "min_eff_dt": min_eff.date().isoformat() if pd.notna(min_eff) else None,
            "max_eff_dt": max_eff.date().isoformat() if pd.notna(max_eff) else None,
            "holdings_available_from": (
                available_from.date().isoformat() if pd.notna(available_from) else None
            ),
            "report_age_days": report_age,
            "publication_delay_days": publication_delay,
            "available_without_intraday_lookahead": available,
            "absolute_reported_percent_tna": absolute_pct_sum,
            "derivative_gross_percent_tna": derivative_gross_pct,
            "missing_permno_position_count": non_equity_count,
            "historical_etf_flag_F": historical_f,
            "etf_security_crosswalk": etf_security,
            "external_evidence_id": external_evidence,
            "external_evidence_rule": evidence_rule,
            "pro_rata_verified": pro_rata,
            "tna_bundle": tna,
            "identity": identity,
            "final_eligible": final_eligible,
            "reasons": reasons,
            "expected_reasons": sorted(expected_reasons),
            "expected_final_eligible": bool(case["expected_final_eligible"]),
            "expected_disposition_match": expected_match,
        }
        results.append(result)
        snapshots[case_id] = {
            "frame": snapshot,
            "case": case,
            "result": result,
        }
    return results, snapshots


def daily_tables(
    spec: dict[str, Any],
    wrds_root: Path,
) -> dict[int, pd.DataFrame]:
    output: dict[int, pd.DataFrame] = {}
    for year in (2020, 2024):
        relative = spec["shared_inputs"].get(f"daily_stock_{year}")
        if not relative:
            continue
        frame = read_with_provenance(
            safe_raw_path(wrds_root, relative),
            relative,
            ["permno", "date", "prc", "cfacpr", "cfacshr", "shrout"],
        )
        output[year] = dates(frame, ["date"])
    return output


def last_price_row(
    daily: pd.DataFrame,
    permno: int,
    report_dt: pd.Timestamp,
    max_calendar_gap_days: int,
) -> pd.Series | None:
    rows = daily.loc[daily.permno.eq(permno) & daily.date.le(report_dt)].sort_values(
        ["date", "_raw_row_number_zero_based"]
    )
    if rows.empty or (report_dt - rows.iloc[-1].date).days > max_calendar_gap_days:
        return None
    return rows.iloc[-1]


def build_traces(
    snapshots: dict[str, dict[str, Any]],
    spec: dict[str, Any],
    config: dict[str, Any],
    stocknames: pd.DataFrame,
    daily: dict[int, pd.DataFrame],
    input_hashes: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    rel_tol = float(config["tolerances"]["market_value_relative"])
    abs_tol = float(config["tolerances"]["market_value_absolute_usd"])
    weight_tol = float(config["tolerances"]["position_weight_absolute"])
    price_gap_limit = int(
        config["date_rules"]["market_value_price_max_calendar_gap_days"]
    )
    for case in spec["cases"]:
        count = int(case.get("trace_positions", 0))
        if count <= 0:
            continue
        item = snapshots[case["case_id"]]
        result = item["result"]
        if not result["final_eligible"] or not result["pro_rata_verified"]:
            raise ValueError(
                f"trace source case is not eligible: {case['case_id']}; "
                f"reasons={result['reasons']}; identity={result['identity']}; "
                f"etf_security={result['etf_security_crosswalk']}; "
                f"tna_bundle={result['tna_bundle']}"
            )
        report_dt = pd.Timestamp(case["report_dt"])
        frame = item["frame"].copy()
        frame["permno"] = pd.to_numeric(frame.permno, errors="coerce")
        frame["market_val"] = pd.to_numeric(frame.market_val, errors="coerce")
        frame = frame.loc[
            frame.permno.notna() & frame.market_val.gt(0) & frame.percent_tna.notna()
        ].copy()
        common_flags = []
        common_evidence = []
        for permno in frame.permno.astype(int):
            flag, evidence = classify_underlying(permno, report_dt, stocknames)
            common_flags.append(flag)
            common_evidence.append(evidence)
        frame["_is_us_common"] = common_flags
        frame["_underlying_evidence"] = common_evidence
        frame = frame.loc[frame._is_us_common].nlargest(count, "market_val")
        if len(frame) != count:
            raise ValueError(f"insufficient trace positions in {case['case_id']}")
        tna_rows = result["tna_bundle"]["exact_tna_rows"]
        etf_tna = [x for x in tna_rows if x["crsp_fundno"] == int(case["etf_crsp_fundno"])]
        if len(etf_tna) != 1:
            raise ValueError(f"no unique ETF-class TNA for trace case {case['case_id']}")
        etf_tna_million = float(etf_tna[0]["mtna_millions"])
        pooled_tna = float(result["tna_bundle"]["portfolio_tna_millions"]) * 1_000_000
        tna_component_rows = []
        for component in tna_rows:
            enriched = dict(component)
            enriched["source_sha256"] = input_hashes[component["source_file"]]["sha256"]
            tna_component_rows.append(enriched)
        mapping_component_rows = []
        for component in result["tna_bundle"]["active_mapping_rows"]:
            enriched = dict(component)
            enriched["source_sha256"] = input_hashes[component["source_file"]]["sha256"]
            mapping_component_rows.append(enriched)
        etf_crosswalk = result["etf_security_crosswalk"]
        external_record = spec["external_evidence"][case["external_pro_rata_evidence"]]
        for _, holding in frame.iterrows():
            permno = int(holding["permno"])
            price = last_price_row(
                daily[report_dt.year], permno, report_dt, price_gap_limit
            )
            if price is None:
                raise ValueError(f"no price row for trace permno {permno} at {report_dt.date()}")
            reported_weight = float(holding["percent_tna"]) / 100.0
            value_weight = float(holding["market_val"]) / pooled_tna
            weight_error = abs(reported_weight - value_weight)
            reconstructed_value = float(holding["nbr_shares"]) * abs(float(price.prc))
            market_error = abs(float(holding["market_val"]) - reconstructed_value)
            market_allowed = max(abs_tol, rel_tol * abs(float(holding["market_val"])))
            exposure = reported_weight * etf_tna_million * 1_000_000.0
            reconciled = bool(
                weight_error <= weight_tol
                and market_error <= market_allowed
                and result["pro_rata_verified"]
            )
            mapping_rows = result["tna_bundle"]["active_mapping_rows"]
            mapping_row = [
                x for x in mapping_rows if x["crsp_fundno"] == int(case["etf_crsp_fundno"])
            ][0]
            underlying = holding["_underlying_evidence"]
            holding_source = holding["_source_file"]
            price_source = price["_source_file"]
            holding_row_number = int(holding["_raw_row_number_zero_based"])
            underlying_position_id = (
                f"{input_hashes[holding_source]['sha256']}:{holding_row_number}"
            )
            rows.append(
                {
                    "final_observation_key": (
                        f"{int(case['crsp_portno'])}|{int(case['etf_crsp_fundno'])}|"
                        f"{result['etf_security_id']}|{permno}|{report_dt.date()}|"
                        f"{finite_float(holding['security_rank'])}"
                    ),
                    "case_id": case["case_id"],
                    "portfolio_id": int(case["crsp_portno"]),
                    "share_class_id": int(case["etf_crsp_fundno"]),
                    "etf_security_id": int(result["etf_security_id"]),
                    "underlying_security_id": permno,
                    "underlying_position_id": underlying_position_id,
                    "underlying_position_rank": finite_float(holding["security_rank"]),
                    "economic_date": report_dt.date().isoformat(),
                    "holdings_eff_dt": pd.Timestamp(holding["eff_dt"]).date().isoformat(),
                    "snapshot_max_eff_dt": result["max_eff_dt"],
                    "availability_timestamp": None,
                    "holdings_available_from": result["holdings_available_from"],
                    "holdings_available_from_rule": "first calendar date strictly after snapshot_max_eff_dt",
                    "tna_availability_timestamp": None,
                    "tna_economic_date": etf_tna[0]["caldt"],
                    "raw_market_val_usd": float(holding["market_val"]),
                    "raw_percent_tna_percent_points": float(holding["percent_tna"]),
                    "raw_nbr_shares": float(holding["nbr_shares"]),
                    "raw_price_usd": abs(float(price.prc)),
                    "price_date": pd.Timestamp(price.date).date().isoformat(),
                    "price_calendar_gap_days": int(
                        (report_dt - pd.Timestamp(price.date)).days
                    ),
                    "portfolio_tna_usd": pooled_tna,
                    "etf_class_tna_usd": etf_tna_million * 1_000_000.0,
                    "reported_portfolio_weight": reported_weight,
                    "market_value_portfolio_weight": value_weight,
                    "weight_absolute_residual": weight_error,
                    "weight_tolerance": weight_tol,
                    "shares_times_price_usd": reconstructed_value,
                    "market_value_absolute_residual_usd": market_error,
                    "market_value_allowed_residual_usd": market_allowed,
                    "etf_class_exposure_usd": exposure,
                    "pro_rata_evidence_id": case["external_pro_rata_evidence"],
                    "pro_rata_evidence_json": json.dumps(
                        external_record, sort_keys=True, separators=(",", ":")
                    ),
                    "holding_source_file": holding_source,
                    "holding_source_sha256": input_hashes[holding_source]["sha256"],
                    "holding_raw_row_zero_based": holding_row_number,
                    "mapping_source_file": mapping_row["source_file"],
                    "mapping_source_sha256": input_hashes[mapping_row["source_file"]]["sha256"],
                    "mapping_raw_row_zero_based": mapping_row["raw_row"],
                    "all_active_mapping_rows_json": json.dumps(
                        mapping_component_rows, sort_keys=True, separators=(",", ":")
                    ),
                    "tna_source_file": etf_tna[0]["source_file"],
                    "tna_source_sha256": input_hashes[etf_tna[0]["source_file"]]["sha256"],
                    "tna_raw_row_zero_based": etf_tna[0]["raw_row"],
                    "portfolio_tna_component_count": len(tna_component_rows),
                    "portfolio_tna_component_rows_json": json.dumps(
                        tna_component_rows, sort_keys=True, separators=(",", ":")
                    ),
                    "price_source_file": price_source,
                    "price_source_sha256": input_hashes[price_source]["sha256"],
                    "price_raw_row_zero_based": int(price["_raw_row_number_zero_based"]),
                    "underlying_name_source_file": underlying["source_file"],
                    "underlying_name_source_sha256": input_hashes[
                        underlying["source_file"]
                    ]["sha256"],
                    "underlying_name_raw_row_zero_based": underlying["raw_row"],
                    "etf_header_source_file": etf_crosswalk["header_source_file"],
                    "etf_header_source_sha256": input_hashes[
                        etf_crosswalk["header_source_file"]
                    ]["sha256"],
                    "etf_header_raw_row_zero_based": etf_crosswalk["header_raw_row"],
                    "etf_security_name_source_file": etf_crosswalk[
                        "stockname_source_file"
                    ],
                    "etf_security_name_source_sha256": input_hashes[
                        etf_crosswalk["stockname_source_file"]
                    ]["sha256"],
                    "etf_security_name_raw_row_zero_based": etf_crosswalk[
                        "stockname_raw_row"
                    ],
                    "reviewer_disposition": "RECONCILED" if reconciled else "FAILED",
                    "reconciled": reconciled,
                }
            )
    return pd.DataFrame(rows)


def history_audit_results(
    spec: dict[str, Any], headers: pd.DataFrame
) -> list[dict[str, Any]]:
    output = []
    for audit in spec["history_audits"]:
        frame = headers.loc[headers.crsp_fundno.eq(int(audit["crsp_fundno"]))].copy()
        pre = frame.loc[frame.ticker.fillna("").astype(str).eq(audit["pre_event_ticker"])]
        post = frame.loc[frame.ticker.fillna("").astype(str).eq(audit["post_event_ticker"])]
        pre_flags = sorted(pre.et_flag.dropna().astype(str).unique())
        post_flags = sorted(post.et_flag.dropna().astype(str).unique())
        passed = bool(
            len(pre)
            and len(post)
            and pre_flags == [audit["expected_pre_event_et_flag"]]
            and post_flags == [audit["expected_post_event_et_flag"]]
        )
        output.append(
            {
                "case_id": audit["case_id"],
                "crsp_fundno": int(audit["crsp_fundno"]),
                "crsp_portno": int(audit["crsp_portno"]),
                "pre_event_ticker": audit["pre_event_ticker"],
                "post_event_ticker": audit["post_event_ticker"],
                "pre_event_et_flags": pre_flags,
                "post_event_et_flags": post_flags,
                "sec_effective_date": audit.get("sec_effective_date"),
                "crsp_header_change_date": audit["crsp_header_change_date"],
                "raw_et_flag_backfill_demonstrated": passed,
                "sec_evidence": audit.get("sec_evidence"),
            }
        )
    return output


def corporate_action_result(
    snapshots: dict[str, dict[str, Any]],
    daily: dict[int, pd.DataFrame],
    config: dict[str, Any],
) -> dict[str, Any]:
    item = snapshots["VOO_NVIDIA_SPLIT_2024_06_30"]
    snapshot = item["frame"]
    nvda = snapshot.loc[
        snapshot.security_name.fillna("").str.contains("NVIDIA", case=False)
    ]
    if len(nvda) != 1:
        return {"passed": False, "reason": "NO_UNIQUE_NVIDIA_HOLDING"}
    holding = nvda.iloc[0]
    permno = int(holding.permno)
    dsf = daily[2024]
    june7 = dsf.loc[dsf.permno.eq(permno) & dsf.date.eq(pd.Timestamp("2024-06-07"))]
    june10 = dsf.loc[dsf.permno.eq(permno) & dsf.date.eq(pd.Timestamp("2024-06-10"))]
    june28 = dsf.loc[dsf.permno.eq(permno) & dsf.date.eq(pd.Timestamp("2024-06-28"))]
    if any(len(x) != 1 for x in (june7, june10, june28)):
        return {"passed": False, "reason": "MISSING_SPLIT_PRICE_ROWS"}
    before, after, report_price = (x.iloc[0] for x in (june7, june10, june28))
    split_factor = float(before.cfacshr) / float(after.cfacshr)
    adjusted_pre = abs(float(before.prc)) / split_factor
    continuity_error = abs(adjusted_pre / abs(float(after.prc)) - 1.0)
    value_error = abs(
        float(holding.market_val) - float(holding.nbr_shares) * abs(float(report_price.prc))
    ) / abs(float(holding.market_val))
    tolerance = float(config["tolerances"]["corporate_action_adjusted_price_relative"])
    passed = bool(
        math.isclose(split_factor, 10.0)
        and math.isclose(float(before.cfacpr) / float(after.cfacpr), 10.0)
        and math.isclose(float(after.shrout) / float(before.shrout), 10.0)
        and continuity_error <= tolerance
        and value_error <= float(config["tolerances"]["market_value_relative"])
    )
    return {
        "passed": passed,
        "underlying_permno": permno,
        "pre_split_date": "2024-06-07",
        "post_split_date": "2024-06-10",
        "holdings_report_date": "2024-06-30",
        "cfacshr_ratio": split_factor,
        "cfacpr_ratio": float(before.cfacpr) / float(after.cfacpr),
        "shrout_ratio": float(after.shrout) / float(before.shrout),
        "adjusted_price_continuity_relative_error": continuity_error,
        "holdings_market_value_relative_error": value_error,
        "tolerance": tolerance,
    }


def rapid_aum_result(monthly: dict[int, pd.DataFrame]) -> dict[str, Any]:
    fundnos = [92756, 102471, 103200]
    frames = [frame.loc[frame.crsp_fundno.isin(fundnos)] for frame in monthly.values()]
    work = pd.concat(frames, ignore_index=True).sort_values(["crsp_fundno", "caldt"])
    work["mtna"] = pd.to_numeric(work.mtna, errors="coerce")
    work["absolute_change_fraction"] = work.groupby("crsp_fundno").mtna.pct_change().abs()
    maxima = (
        work.groupby("crsp_fundno").absolute_change_fraction.max().dropna().to_dict()
    )
    maxima = {str(int(key)): float(value) for key, value in maxima.items()}
    return {
        "passed": bool(maxima and max(maxima.values()) >= 0.5),
        "pre_outcome_threshold": 0.5,
        "maximum_absolute_monthly_change_by_fund": maxima,
    }


def make_invariants(
    config: dict[str, Any],
    contract: dict[str, Any],
    spec: dict[str, Any],
    case_results: list[dict[str, Any]],
    history_results: list[dict[str, Any]],
    traces: pd.DataFrame,
    corporate: dict[str, Any],
    rapid: dict[str, Any],
) -> list[dict[str, Any]]:
    by_case = {item["case_id"]: item for item in case_results}
    exact_testable = [item for item in case_results if item["identity"]["testable"]]
    positive = [item for item in case_results if item["final_eligible"]]
    all_expected = all(item["expected_disposition_match"] for item in case_results)
    category_counts = {key: len(value) for key, value in spec["categories"].items()}
    trace_ok = bool(len(traces) >= 20 and traces.reconciled.eq(True).all())
    distinct_keys = contract["indices"]
    canonical_keys = [value["canonical_key"] for value in distinct_keys.values()]
    candidate_passed, candidate_result = candidate_implementation_conformance(config)
    results: dict[str, tuple[bool, dict[str, Any]]] = {
        "CANDIDATE_IMPLEMENTATION_CONFORMANCE": (
            candidate_passed,
            candidate_result,
        ),
        "INDEX_DOMAINS_DISTINCT": (
            len(canonical_keys) == len(set(canonical_keys)),
            {"canonical_keys": canonical_keys},
        ),
        "MARKET_VAL_ROW_UNIT_VERIFIED": (
            trace_ok,
            {
                "reconciled_trace_rows": int(traces.reconciled.sum()) if len(traces) else 0,
                "max_relative_error": float(
                    (traces.market_value_absolute_residual_usd / traces.raw_market_val_usd.abs()).max()
                )
                if len(traces)
                else None,
                "unit": "USD",
            },
        ),
        "PERCENT_TNA_SEMANTICS_VERIFIED": (
            bool(exact_testable),
            {
                "formula": "percent_tna / 100",
                "denominator": "same-date pooled portfolio TNA",
                "testable_portfolio_dates": len(exact_testable),
            },
        ),
        "PORTFOLIO_AND_SHARE_CLASS_TNA_VERIFIED": (
            by_case["VOO_POOLED_2024_12_31"]["tna_bundle"]["complete"]
            and len(by_case["VOO_POOLED_2024_12_31"]["tna_bundle"]["exact_tna_rows"]) == 4,
            {
                "voo_active_share_classes": by_case["VOO_POOLED_2024_12_31"]["tna_bundle"]["active_share_class_ids"],
                "voo_portfolio_tna_millions": by_case["VOO_POOLED_2024_12_31"]["tna_bundle"]["portfolio_tna_millions"],
                "voo_etf_class_tna_millions": next(
                    row["mtna_millions"]
                    for row in by_case["VOO_POOLED_2024_12_31"]["tna_bundle"]["exact_tna_rows"]
                    if row["crsp_fundno"] == 50485
                ),
            },
        ),
        "DATE_SCOPED_PORTFOLIO_ETF_CLASS_RELATIONSHIP_VERIFIED": (
            by_case["VOO_POOLED_2024_12_31"]["pro_rata_verified"],
            {
                "positive_control": "VOO_POOLED_2024_12_31",
                "economic_date": "2024-12-31",
                "active_share_class_count": len(
                    by_case["VOO_POOLED_2024_12_31"]["tna_bundle"]["active_share_class_ids"]
                ),
                "external_evidence": "SEC_VANGUARD_500_MULTIPLE_CLASS_PLAN",
            },
        ),
        "PERCENT_TNA_IDENTITY_WITH_SAME_DATE_PORTFOLIO_TNA": (
            bool(exact_testable)
            and all(item["identity"]["passed"] for item in exact_testable),
            {
                "testable_golden_cases": len(exact_testable),
                "unique_testable_portfolio_dates": len(
                    {
                        (item["crsp_portno"], item["report_dt"])
                        for item in exact_testable
                    }
                ),
                "row_tolerance": config["tolerances"]["position_weight_absolute"],
                "denominator_tolerance": config["tolerances"]["median_implied_portfolio_tna_relative"],
                "maximum_row_error": max(
                    item["identity"]["max_position_absolute_residual"]
                    for item in exact_testable
                ),
                "maximum_median_denominator_error": max(
                    item["identity"]["median_implied_tna_relative_error"]
                    for item in exact_testable
                ),
            },
        ),
        "ETF_CLASS_EXPOSURE_PRO_RATA_ONLY": (
            trace_ok and all(item["pro_rata_verified"] for item in positive),
            {
                "constructed_observations": len(traces),
                "formula": "percent_tna/100 * exact-date ETF-class TNA",
                "unverified_exposures_constructed": 0,
            },
        ),
        "ECONOMIC_DATE_AND_AVAILABILITY_VERIFIED": (
            by_case["AFLG_NOT_AVAILABLE_2025_03_31"]["available_without_intraday_lookahead"] is False
            and by_case["BBH_482_DAY_PUBLICATION_DELAY_2023_10_31"]["publication_delay_days"] == 482,
            {
                "economic_field": "report_dt",
                "availability_field": "max(eff_dt)",
                "availability_timestamp": "UNKNOWN",
                "bbh_publication_delay_days": by_case[
                    "BBH_482_DAY_PUBLICATION_DELAY_2023_10_31"
                ]["publication_delay_days"],
            },
        ),
        "NO_LOOKAHEAD": (
            "HOLDINGS_NOT_YET_AVAILABLE"
            in by_case["AFLG_NOT_AVAILABLE_2025_03_31"]["reasons"]
            and "HOLDINGS_NOT_YET_AVAILABLE"
            in by_case["BBH_482_DAY_PUBLICATION_DELAY_2023_10_31"]["reasons"],
            {"rejected_future_available_cases": 2},
        ),
        "GOLDEN_SAMPLE_COVERAGE": (
            set(category_counts)
            == {
                "CORPORATE_ACTION",
                "DERIVATIVE_OR_NON_EQUITY_POSITION",
                "ETF_STATUS_TRANSITION_OR_FLAG_HISTORY_ANOMALY",
                "POOLED_ETF_MUTUAL_FUND_PORTFOLIO",
                "PURE_ETF",
                "RAPID_AUM_CHANGE",
                "STALE_REPORT",
            }
            and all(value >= 1 for value in category_counts.values())
            and all_expected,
            {"category_counts": category_counts, "all_expected_dispositions_matched": all_expected},
        ),
        "RAW_TRACE_RECONCILIATION": (
            trace_ok,
            {"observation_count": len(traces), "all_reconciled": trace_ok},
        ),
        "END_TO_END_PILOT_COMPLETED": (
            trace_ok and bool(positive) and all_expected,
            {
                "case_count": len(case_results),
                "eligible_case_count": len(positive),
                "final_exposure_observation_count": len(traces),
            },
        ),
        "STALE_REPORT_REJECTED": (
            not by_case["LVHD_STALE_AT_2020_12_31"]["final_eligible"]
            and not by_case["BBH_482_DAY_PUBLICATION_DELAY_2023_10_31"]["final_eligible"],
            {
                "report_age_negative_control_days": by_case["LVHD_STALE_AT_2020_12_31"][
                    "report_age_days"
                ],
                "publication_delay_negative_control_days": by_case[
                    "BBH_482_DAY_PUBLICATION_DELAY_2023_10_31"
                ]["publication_delay_days"],
            },
        ),
        "ETF_STATUS_TRANSITION_OR_FLAG_HISTORY_HANDLED": (
            all(item["raw_et_flag_backfill_demonstrated"] for item in history_results),
            {
                "history_audits": len(history_results),
                "conclusion": "et_flag F is not accepted as a point-in-time transition date",
            },
        ),
        "CORPORATE_ACTION_HANDLED": (
            bool(corporate["passed"]),
            corporate,
        ),
        "DERIVATIVE_NON_EQUITY_HANDLED": (
            "DERIVATIVE_OR_NON_EQUITY_PORTFOLIO"
            in by_case["NUSI_OPTIONS_AND_CASH_2021_02_28"]["reasons"]
            and by_case["NUSI_OPTIONS_AND_CASH_2021_02_28"]["missing_permno_position_count"] > 0,
            {
                "case_id": "NUSI_OPTIONS_AND_CASH_2021_02_28",
                "derivative_gross_percent_tna": by_case[
                    "NUSI_OPTIONS_AND_CASH_2021_02_28"
                ]["derivative_gross_percent_tna"],
                "missing_permno_positions_retained": by_case[
                    "NUSI_OPTIONS_AND_CASH_2021_02_28"
                ]["missing_permno_position_count"],
            },
        ),
        "RAPID_AUM_CHANGE_HANDLED": (bool(rapid["passed"]), rapid),
    }
    required = config["required_invariant_ids"]
    if sorted(results) != required:
        raise ValueError(
            f"invariant registry mismatch: computed={sorted(results)}, required={required}"
        )
    return [
        {"id": invariant_id, "passed": bool(results[invariant_id][0]), "result": results[invariant_id][1]}
        for invariant_id in required
    ]


def main() -> None:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--code-root", type=Path, default=here)
    parser.add_argument("--config", type=Path, default=here / "gate01_config.json")
    parser.add_argument("--data-contract", type=Path, default=here / "data_contract.json")
    parser.add_argument("--golden-sample", type=Path, default=here / "golden_sample_spec.json")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    config = strict_json(args.config, archive_root=args.archive)
    contract = strict_json(args.data_contract, archive_root=args.archive)
    spec = strict_json(args.golden_sample, archive_root=args.archive)
    if tuple(config.get("required_pilot_artifacts", ())) != REQUIRED_PILOT_ARTIFACTS:
        raise ValueError("configured Pilot artifact registry is not frozen registry")
    expected_golden = args.code_root / config.get("golden_sample_file", "")
    if args.golden_sample.absolute() != expected_golden.absolute():
        raise ValueError("golden sample path is not bound to the configured code file")
    candidate_passed, _ = candidate_implementation_conformance(config)
    if not candidate_passed:
        raise ValueError("candidate implementation activation state is inconsistent")
    if config["required_invariant_ids"] != sorted(config["required_invariant_ids"]):
        raise ValueError("required invariant IDs must be sorted")

    wrds_root = args.archive / WRDS_SUBDIR
    manifest_hash, manifest = manifest_inventory(args.manifest)
    raw_paths = registered_raw_inputs(spec)
    input_hashes = validate_and_hash_inputs(wrds_root, raw_paths, manifest)

    shared = spec["shared_inputs"]
    mapping = dates(
        read_with_provenance(
            safe_raw_path(wrds_root, shared["portfolio_map"]), shared["portfolio_map"]
        ),
        ["begdt", "enddt"],
    )
    header_frames = []
    for relative in shared["historical_headers"]:
        header_frames.append(
            read_with_provenance(safe_raw_path(wrds_root, relative), relative)
        )
    headers = dates(pd.concat(header_frames, ignore_index=True), ["chgdt", "chgenddt"])
    stocknames = dates(
        read_with_provenance(
            safe_raw_path(wrds_root, shared["stock_name_history"]),
            shared["stock_name_history"],
        ),
        ["namedt", "nameenddt"],
    )
    monthly: dict[int, pd.DataFrame] = {}
    for year_text, relative in shared["monthly_tna"].items():
        monthly[int(year_text)] = dates(
            read_with_provenance(safe_raw_path(wrds_root, relative), relative), ["caldt"]
        )
    holdings: dict[str, pd.DataFrame] = {}
    for relative in sorted({case["holdings_file"] for case in spec["cases"]}):
        holdings[relative] = dates(
            read_with_provenance(safe_raw_path(wrds_root, relative), relative),
            ["report_dt", "eff_dt", "maturity_dt"],
        )

    case_results, snapshots = build_case_results(
        spec, config, holdings, mapping, headers, stocknames, monthly
    )
    history_results = history_audit_results(spec, headers)
    daily = daily_tables(spec, wrds_root)
    traces = build_traces(snapshots, spec, config, stocknames, daily, input_hashes)
    corporate = corporate_action_result(snapshots, daily, config)
    rapid = rapid_aum_result(monthly)
    invariants = make_invariants(
        config,
        contract,
        spec,
        case_results,
        history_results,
        traces,
        corporate,
        rapid,
    )

    args.output.mkdir(parents=True, exist_ok=True)
    pass_path = args.output / "PILOT_PASS.json"
    public_path = args.output / "PILOT_PUBLIC_RECEIPT.json"
    fail_path = args.output / "PILOT_FAIL.json"
    for stale_receipt in (pass_path, public_path, fail_path):
        if stale_receipt.exists():
            stale_receipt.unlink()
    cases_path = args.output / "golden_case_results.json"
    histories_path = args.output / "etf_flag_history_audits.json"
    traces_path = args.output / "pilot_raw_trace_inspection.csv"
    exposure_path = args.output / "pilot_exposure_observations.csv"
    inputs_path = args.output / "pilot_input_files.json"
    invariants_path = args.output / "pilot_invariants.json"
    write_json(cases_path, case_results)
    write_json(histories_path, history_results)
    traces.to_csv(traces_path, index=False)
    traces.to_csv(exposure_path, index=False)
    write_json(inputs_path, input_hashes)
    write_json(invariants_path, invariants)

    all_passed = all(item["passed"] is True for item in invariants)
    code_hash, code_files = compute_code_fileset_hash(
        args.code_root,
        config["scientific_fileset"],
        archive_root=args.archive,
    )
    config_hash, _, _ = compute_json_file_hash(
        args.config, label="gate configuration", archive_root=args.archive
    )
    contract_hash, _, _ = compute_json_file_hash(
        args.data_contract, label="data contract", archive_root=args.archive
    )
    golden_hash = canonical_json_hash(spec)
    trace_hash, _ = compute_raw_file_hash(traces_path, label="raw trace inspection ledger")
    artifacts = {}
    for path in [cases_path, histories_path, traces_path, exposure_path, inputs_path, invariants_path]:
        digest, _ = compute_raw_file_hash(path, label=f"pilot artifact {path.name}")
        artifacts[path.name] = {"sha256": digest, "bytes": path.stat().st_size}
    if tuple(sorted(artifacts)) != REQUIRED_PILOT_ARTIFACTS:
        raise ValueError(
            "generated Pilot artifact registry does not match frozen registry"
        )

    pilot_document = {
        "schema_version": PILOT_SCHEMA_VERSION,
        "status": "PASS" if all_passed else "FAIL",
        "created_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "pilot_run_id": spec["golden_sample_id"],
        "hashes": {
            "code": {
                "algorithm": CODE_HASH_ALGORITHM,
                "digest": code_hash,
                "files": list(code_files),
            },
            "config": {"algorithm": JSON_HASH_ALGORITHM, "digest": config_hash},
            "data_contract": {
                "algorithm": JSON_HASH_ALGORITHM,
                "digest": contract_hash,
            },
            "manifest": {"algorithm": RAW_HASH_ALGORITHM, "digest": manifest_hash},
        },
        "required_invariant_ids": config["required_invariant_ids"],
        "invariants": invariants,
        "golden_sample": {
            "categories": {key: len(value) for key, value in spec["categories"].items()},
            "content_sha256": golden_hash,
        },
        "raw_trace_inspection": {
            "observation_count": len(traces),
            "all_reconciled": bool(len(traces) >= 20 and traces.reconciled.eq(True).all()),
            "artifact_sha256": trace_hash,
        },
        "runtime_fingerprint": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "pyarrow": pyarrow.__version__,
        },
        "artifacts": artifacts,
    }
    if all_passed:
        write_json(pass_path, pilot_document)
        public_receipt = make_public_receipt(pilot_document)
        write_json(public_path, public_receipt)
        print(json.dumps({"status": "PASS", "pilot_pass": str(pass_path), "traces": len(traces)}))
    else:
        write_json(fail_path, pilot_document)
        failed = [item["id"] for item in invariants if not item["passed"]]
        raise SystemExit(f"pilot failed; PILOT_PASS.json not written; failed={failed}")


if __name__ == "__main__":
    main()
