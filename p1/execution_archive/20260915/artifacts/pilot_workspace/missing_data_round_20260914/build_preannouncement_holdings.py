#!/usr/bin/env python3
"""Select and parse cached N-PORT reports strictly before package cutoffs.

This script reads immutable local SEC XML caches only. It does not read POST
quotes, market responses, earnings values, or the network.
"""
from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
FIXED = HERE.parent
CACHE_RECEIPT = FIXED / "evaluation_20260914" / "cached_filing_metadata_receipt.json"
PACKAGE_INPUTS = HERE / "PACKAGE_INPUTS.csv"
OUT_HOLDINGS = HERE / "PREANNOUNCEMENT_HOLDINGS.parquet"
OUT_FILINGS = HERE / "SELECTED_PREANNOUNCEMENT_FILINGS.csv"
OUT_AUDIT = HERE / "PREANNOUNCEMENT_PARSE_AUDIT.csv"
OUT_RECEIPT = HERE / "PREANNOUNCEMENT_HOLDINGS_RECEIPT.json"
CUSIP_RE = re.compile(r"^[A-Z0-9]{9}$")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def lname(tag: str) -> str:
    return tag.split("}", 1)[-1]


def first(parent: ET.Element | None, name: str) -> ET.Element | None:
    if parent is None:
        return None
    return next((x for x in parent.iter() if lname(x.tag) == name), None)


def text(parent: ET.Element | None, name: str) -> str:
    node = first(parent, name)
    return (node.text or "").strip() if node is not None else ""


def number(value: str):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ident(sec: ET.Element, kind: str) -> str:
    ids = first(sec, "identifiers")
    if ids is None:
        return ""
    for node in ids.iter():
        if lname(node.tag) == kind:
            return (node.attrib.get("value") or node.text or "").strip()
    return ""


def valid_cusip(value: str) -> bool:
    value = (value or "").strip().upper()
    return bool(CUSIP_RE.fullmatch(value)) and len(set(value)) > 1


def select_filings() -> pd.DataFrame:
    specs = pd.read_csv(PACKAGE_INPUTS)
    specs = specs[specs.include_in_equity_package.astype(str).str.lower().eq("true")].copy()
    receipt = json.loads(CACHE_RECEIPT.read_text())
    indexed = {x["pre_series_id"]: x for x in receipt["series"]}
    rows = []
    for spec in specs.itertuples(index=False):
        series = indexed[spec.pre_series_id]
        eligible = [
            x for x in series["all_geninfo_sources"]
            if x["report_date"] < spec.announcement_cutoff
        ]
        if not eligible:
            raise ValueError(f"no cached report before cutoff: {spec.pre_series_id}")
        chosen = max(eligible, key=lambda x: x["report_date"])
        path = Path(chosen["path"])
        rows.append({
            "wave_id": spec.wave_id,
            "role": spec.role,
            "effective_date": spec.effective_date,
            "announcement_cutoff": spec.announcement_cutoff,
            "cutoff_precision": spec.cutoff_precision,
            "cutoff_status": spec.cutoff_status,
            "pre_series_id": spec.pre_series_id,
            "pre_series_name": spec.pre_series_name,
            "pre_cik": series["pre_cik"],
            "report_date": chosen["report_date"],
            "cache_path": str(path),
            "cache_sha256": sha256(path),
            "source_locator": spec.source_locator,
        })
    out = pd.DataFrame(rows).sort_values(["wave_id", "pre_series_id"])
    if not (pd.to_datetime(out.report_date) < pd.to_datetime(out.announcement_cutoff)).all():
        raise ValueError("strict preannouncement selection failure")
    return out


def parse(selected: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    holdings, audits = [], []
    for row in selected.itertuples(index=False):
        root = ET.parse(row.cache_path).getroot()
        gen = first(root, "genInfo")
        fund = first(root, "fundInfo")
        actual_series = text(gen, "seriesId")
        actual_report = text(gen, "repPdDate")
        if actual_series != row.pre_series_id or actual_report != row.report_date:
            raise ValueError(f"series/report mismatch: {row.pre_series_id}")
        positions = [x for x in root.iter() if lname(x.tag) == "invstOrSec"]
        common_count = 0
        for pos_no, sec in enumerate(positions, 1):
            units = text(sec, "units")
            asset = text(sec, "assetCat")
            payoff = text(sec, "payoffProfile")
            balance = number(text(sec, "balance"))
            cusip = text(sec, "cusip").upper()
            is_common = bool(
                units == "NS" and asset in ("", "EC") and payoff in ("", "Long")
                and balance is not None and balance > 0 and valid_cusip(cusip)
            )
            common_count += int(is_common)
            holdings.append({
                "wave_id": row.wave_id,
                "role": row.role,
                "effective_date": row.effective_date,
                "announcement_cutoff": row.announcement_cutoff,
                "cutoff_status": row.cutoff_status,
                "pre_series_id": row.pre_series_id,
                "pre_series_name": row.pre_series_name,
                "pre_cik": row.pre_cik,
                "pre_report_date": actual_report,
                "cache_path": row.cache_path,
                "cache_sha256": row.cache_sha256,
                "position_number": pos_no,
                "issuer_name": text(sec, "name"),
                "security_title": text(sec, "title"),
                "cusip9": cusip,
                "isin": ident(sec, "isin"),
                "nport_ticker": ident(sec, "ticker").upper(),
                "raw_reported_shares": balance if units == "NS" else None,
                "units": units,
                "currency": text(sec, "curCd"),
                "position_value_usd": number(text(sec, "valUSD")),
                "pct_value_reported": number(text(sec, "pctVal")),
                "payoff_profile": payoff,
                "asset_category": asset,
                "issuer_category": text(sec, "issuerCat"),
                "investment_country": text(sec, "invCountry"),
                "is_common_equity_candidate": is_common,
            })
        audits.append({
            "wave_id": row.wave_id,
            "pre_series_id": row.pre_series_id,
            "report_date": actual_report,
            "announcement_cutoff": row.announcement_cutoff,
            "strictly_preannouncement": actual_report < row.announcement_cutoff,
            "positions": len(positions),
            "common_equity_candidates": common_count,
            "fund_total_assets_usd": number(text(fund, "totAssets")),
            "fund_net_assets_usd": number(text(fund, "netAssets")),
        })
    return pd.DataFrame(holdings), pd.DataFrame(audits)


def main() -> int:
    selected = select_filings()
    holdings, audit = parse(selected)
    if not audit.strictly_preannouncement.all():
        raise ValueError("parse audit failed")
    selected.to_csv(OUT_FILINGS, index=False)
    audit.to_csv(OUT_AUDIT, index=False)
    holdings.to_parquet(OUT_HOLDINGS, index=False)
    receipt = {
        "status": "LOCAL_CACHED_PREANNOUNCEMENT_HOLDINGS_PARSED",
        "outcome_fields_read": False,
        "post_quotes_read": False,
        "network_calls": False,
        "selected_series": len(selected),
        "selected_waves": int(selected.wave_id.nunique()),
        "excluded_w021_bond_series": "S000003492",
        "positions": len(holdings),
        "common_equity_candidates": int(holdings.is_common_equity_candidate.sum()),
        "input_hashes": {
            "PACKAGE_INPUTS.csv": sha256(PACKAGE_INPUTS),
            "cached_filing_metadata_receipt.json": sha256(CACHE_RECEIPT),
        },
        "output_hashes": {
            OUT_FILINGS.name: sha256(OUT_FILINGS),
            OUT_AUDIT.name: sha256(OUT_AUDIT),
            OUT_HOLDINGS.name: sha256(OUT_HOLDINGS),
        },
    }
    OUT_RECEIPT.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
