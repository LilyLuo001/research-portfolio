#!/usr/bin/env python3
"""Freeze the Gate-0 universe and extract exact strictly-PRE N-PORT holdings.

This stage deliberately does not map securities or calculate treatment.  It
reads only the PRE accession selected by ``nport_gate0.py``, verifies the
filing-internal series id and report date again, and emits an auditable long
position table for the SCC/WRDS mapping stage.

The SEC cache is immutable input.  ``cache_file_mtime_utc`` records the best
available retrieval-time witness in the legacy cache; it is labelled as a file
mtime rather than promoted to an HTTP timestamp that the cache did not retain.
"""
from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
P1 = ROOT / "p1"
GATE0 = P1 / "t2_free" / "nport_gate0_event_level.csv"
CONTINUITY = P1 / "t2_free" / "gate0_predecessor_continuity.csv"
CACHE = P1 / "t2_free" / "cache" / "nport"
OUTDIR = P1 / "exposure"

PASS_OUT = OUTDIR / "exposure_universe_gate0_pass.csv"
PENDING_OUT = OUTDIR / "exposure_pending_missing_post.csv"
HOLDINGS_OUT = OUTDIR / "nport_pre_holdings_long.parquet"
PARSE_AUDIT_OUT = OUTDIR / "nport_pre_parse_audit.csv"

LONG_HANDOFF_EVENTS = {"P1E000055869", "P1E000055870"}
_CUSIP_RE = re.compile(r"^[A-Z0-9]{9}$")


def lname(tag: str) -> str:
    return tag.split("}", 1)[-1]


def first(parent: ET.Element, name: str) -> ET.Element | None:
    return next((x for x in parent.iter() if lname(x.tag) == name), None)


def text(parent: ET.Element, name: str) -> str:
    node = first(parent, name)
    return (node.text or "").strip() if node is not None else ""


def number(value: str):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def valid_cusip(value: str) -> bool:
    value = (value or "").strip().upper()
    return bool(_CUSIP_RE.fullmatch(value)) and len(set(value)) > 1


def identifier_value(sec: ET.Element, kind: str) -> str:
    ids = first(sec, "identifiers")
    if ids is None:
        return ""
    for node in ids.iter():
        if lname(node.tag) == kind:
            return (node.attrib.get("value") or node.text or "").strip()
    return ""


def cache_path(row) -> Path:
    cik = str(int(row.pre_cik))
    accession = str(row.pre_accession).replace("-", "")
    return CACHE / f"{cik}_{accession}.xml"


def source_url(row) -> str:
    cik = str(int(row.pre_cik))
    accession = str(row.pre_accession).replace("-", "")
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/primary_doc.xml"


def parse_selected_filing(row) -> tuple[list[dict], dict]:
    path = cache_path(row)
    if not path.exists():
        raise FileNotFoundError(f"selected PRE cache missing: {path}")

    root = ET.parse(path).getroot()
    gen = first(root, "genInfo")
    fund = first(root, "fundInfo")
    if gen is None:
        raise ValueError(f"{row.event_id}: N-PORT has no genInfo")

    actual_series = text(gen, "seriesId")
    actual_report = text(gen, "repPdDate")
    if actual_series != row.pre_series_id:
        raise ValueError(
            f"{row.event_id}: filing series {actual_series!r} != selected {row.pre_series_id!r}"
        )
    if actual_report != row.pre_report_date:
        raise ValueError(
            f"{row.event_id}: report date {actual_report!r} != selected {row.pre_report_date!r}"
        )
    if not actual_report or actual_report >= row.effective_date:
        raise ValueError(
            f"{row.event_id}: PRE leakage ({actual_report!r} !< {row.effective_date!r})"
        )

    stat = path.stat()
    common = {
        "event_id": row.event_id,
        "wave_id": row.wave_id,
        "effective_date": row.effective_date,
        "adviser": row.adviser,
        "is_dimensional": bool("dimensional" in str(row.adviser).lower()),
        "long_handoff_flag": bool(row.event_id in LONG_HANDOFF_EVENTS),
        "predecessor_reported_after_event_flag": bool(
            getattr(row, "days_after_event", -1) > 0
        ),
        "predecessor_last_report": getattr(row, "last_pre_series_report", ""),
        "predecessor_days_after_event": getattr(row, "days_after_event", ""),
        "many_to_one_successor_flag": bool(row.many_to_one_successor_flag),
        "pre_series_id": row.pre_series_id,
        "pre_series_name": row.pre_series_name,
        "pre_cik": int(row.pre_cik),
        "post_series_id": row.post_series_id,
        "post_series_name": row.post_series_name,
        "post_cik": int(row.post_cik) if pd.notna(row.post_cik) else None,
        "registrant_name": text(gen, "regName"),
        "registrant_cik_in_filing": text(gen, "regCik"),
        "pre_report_date": actual_report,
        "pre_period_end": text(gen, "repPdEnd"),
        "pre_accession": row.pre_accession,
        "pre_filing_date": row.pre_filing_date,
        "source_url": source_url(row),
        "cache_file": str(path.relative_to(ROOT)),
        "cache_file_mtime_utc": datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat(),
        "fund_total_assets_usd": number(text(fund, "totAssets")) if fund is not None else None,
        "fund_net_assets_usd": number(text(fund, "netAssets")) if fund is not None else None,
    }

    rows = []
    positions = [x for x in root.iter() if lname(x.tag) == "invstOrSec"]
    for position_number, sec in enumerate(positions, 1):
        units = text(sec, "units")
        asset_cat = text(sec, "assetCat")
        payoff = text(sec, "payoffProfile")
        balance = number(text(sec, "balance"))
        cusip = text(sec, "cusip").upper()
        is_common = bool(
            units == "NS"
            and asset_cat in ("", "EC")
            and payoff in ("", "Long")
            and balance is not None
            and balance > 0
            and valid_cusip(cusip)
        )
        rows.append(
            {
                **common,
                "position_number": position_number,
                "issuer_name": text(sec, "name"),
                "security_title": text(sec, "title"),
                "issuer_lei": text(sec, "lei"),
                "cusip": cusip,
                "isin": identifier_value(sec, "isin"),
                "nport_ticker": identifier_value(sec, "ticker").upper(),
                "balance": balance,
                "units": units,
                "currency": text(sec, "curCd"),
                "position_value_usd": number(text(sec, "valUSD")),
                "pct_value_reported": number(text(sec, "pctVal")),
                "payoff_profile": payoff,
                "asset_category": asset_cat,
                "issuer_category": text(sec, "issuerCat"),
                "investment_country": text(sec, "invCountry"),
                "restricted_security": text(sec, "isRestrictedSec"),
                "fair_value_level": text(sec, "fairValLevel"),
                "is_common_equity_candidate": is_common,
                "raw_reported_shares": balance if units == "NS" else None,
            }
        )

    audit = {
        "event_id": row.event_id,
        "wave_id": row.wave_id,
        "pre_series_id": row.pre_series_id,
        "pre_accession": row.pre_accession,
        "pre_report_date": actual_report,
        "effective_date": row.effective_date,
        "strictly_pre_pass": actual_report < row.effective_date,
        "series_id_pass": actual_series == row.pre_series_id,
        "positions": len(rows),
        "common_equity_candidates": sum(r["is_common_equity_candidate"] for r in rows),
        "position_value_usd": sum((r["position_value_usd"] or 0.0) for r in rows),
        "common_equity_value_usd": sum(
            (r["position_value_usd"] or 0.0)
            for r in rows
            if r["is_common_equity_candidate"]
        ),
        "source_url": common["source_url"],
    }
    return rows, audit


def freeze_universe(gate0: pd.DataFrame, continuity: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    gate0 = gate0.copy()
    gate0["effective_date"] = gate0["effective_date"].astype(str)
    gate0["pre_report_date"] = gate0["pre_report_date"].fillna("").astype(str)
    post_counts = gate0.groupby("post_series_id", dropna=False)["event_id"].transform("size")
    gate0["many_to_one_successor_flag"] = post_counts.gt(1)
    gate0["long_handoff_flag"] = gate0.event_id.isin(LONG_HANDOFF_EVENTS)
    gate0 = gate0.merge(
        continuity[
            ["event_id", "last_pre_series_report", "days_after_event", "n_unreadable"]
        ],
        on="event_id",
        how="left",
        validate="one_to_one",
    )
    gate0["predecessor_reported_after_event_flag"] = gate0.days_after_event.fillna(-1).gt(0)
    passed = gate0.loc[gate0.gate0.eq("PASS")].copy()
    pending = gate0.loc[gate0.gate0.ne("PASS")].copy()
    if len(passed) != 71 or len(pending) != 3:
        raise ValueError(f"frozen Gate0 count changed: pass={len(passed)}, pending={len(pending)}")
    return passed, pending


def build() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    gate0 = pd.read_csv(GATE0)
    continuity = pd.read_csv(CONTINUITY)
    passed, pending = freeze_universe(gate0, continuity)
    passed.to_csv(PASS_OUT, index=False)
    pending.to_csv(PENDING_OUT, index=False)

    holdings: list[dict] = []
    audits: list[dict] = []
    for row in passed.itertuples(index=False):
        event_rows, audit = parse_selected_filing(row)
        holdings.extend(event_rows)
        audits.append(audit)
    long = pd.DataFrame(holdings)
    audit = pd.DataFrame(audits)
    if long.empty:
        raise ValueError("no N-PORT positions extracted")
    if not audit.strictly_pre_pass.all() or not audit.series_id_pass.all():
        raise ValueError("PRE leakage or series mismatch in parse audit")
    long.to_parquet(HOLDINGS_OUT, index=False)
    audit.to_csv(PARSE_AUDIT_OUT, index=False)
    print(
        f"Gate0 frozen: {len(passed)} pass / {len(pending)} pending; "
        f"{len(long)} N-PORT positions, "
        f"{int(long.is_common_equity_candidate.sum())} common-equity candidates"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args(argv)
    build()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
