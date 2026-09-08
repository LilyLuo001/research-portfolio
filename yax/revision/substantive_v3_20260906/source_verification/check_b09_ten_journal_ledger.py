#!/usr/bin/env python3
"""Fail-closed structural check for the dated B09 search ledger."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


HERE = Path(__file__).resolve().parent
LEDGER = HERE / "B09_TEN_JOURNAL_SEARCH_LEDGER.json"
EXPECTED = {
    "AER": "aeaweb.org",
    "QJE": "academic.oup.com",
    "JPE": "journals.uchicago.edu",
    "ECMA": "onlinelibrary.wiley.com",
    "RESTUD": "academic.oup.com",
    "RESTAT": "direct.mit.edu",
    "JEEA": "academic.oup.com",
    "JF": "onlinelibrary.wiley.com",
    "JFE": "sciencedirect.com",
    "RFS": "academic.oup.com",
}


def main() -> None:
    data = json.loads(LEDGER.read_text())
    assert data["search_date"] == "2026-09-08"
    rows = data["journal_searches"]
    assert len(rows) == 10
    assert {row["journal_id"] for row in rows} == set(EXPECTED)

    for row in rows:
        jid = row["journal_id"]
        assert row["publisher_domain"] == EXPECTED[jid]
        assert row["query"].strip()
        assert row["exact_design_located"] is False
        assert row["closest_candidates"]
        for candidate in row["closest_candidates"]:
            assert candidate["publication_status"] == "published"
            assert candidate["authors"].strip()
            assert candidate["title"].strip()
            assert candidate["disposition"].strip()
            host = urlparse(candidate["url"]).hostname or ""
            assert host == EXPECTED[jid] or host.endswith("." + EXPECTED[jid])

    assert data["outside_scope_primary_work"]
    assert "not a systematic review" in data["scope_limit"].lower()
    forbidden = " ".join(data["forbidden_claims"]).lower()
    assert "first public-data study" in forbidden
    assert "proves" in forbidden
    print("PASS: B09 dated ten-journal ledger is complete and claim-qualified")


if __name__ == "__main__":
    main()
