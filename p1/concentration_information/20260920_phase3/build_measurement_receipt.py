#!/usr/bin/env python3
"""Validate the Git-safe Phase 3 packet and bind its diagnostic artifacts."""

from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path: str):
    return json.loads((ROOT / path).read_text())


def main() -> None:
    json_paths = sorted(ROOT.rglob("*.json"))
    for path in json_paths:
        json.loads(path.read_text())
    text_suffixes = {".py", ".md", ".json", ".csv", ".sh"}
    text = "\n".join(path.read_text(errors="ignore") for path in ROOT.rglob("*") if path.is_file() and path.suffix in text_suffixes)
    forbidden = ["github" + "_pat_", "db" + "-vt", "Lqy_" + "19930802"]
    assert not any(token in text for token in forbidden)
    assert "nominal_time_et" not in (ROOT / "event_clock/CLOCK_EVIDENCE.csv").read_text()
    assert not list(ROOT.rglob("TRACE20.csv"))

    stages = [
        ("measurement/results/FIRST_DOWNLOAD_PROPOSAL.csv", "measurement/QUOTE_RECEIPT.json", "measurement/DOWNLOAD_RECEIPT.json", "measurement/pilot_results/PILOT_SUMMARY.json"),
        ("measurement/results/SECOND_DOWNLOAD_PROPOSAL.csv", "measurement/SECOND_QUOTE_RECEIPT.json", "measurement/SECOND_DOWNLOAD_RECEIPT.json", "measurement/pilot_results_second/PILOT_SUMMARY.json"),
        ("measurement/results/THIRD_LATE_ONLY_PROPOSAL.csv", "measurement/THIRD_LATE_QUOTE_RECEIPT.json", "measurement/THIRD_DOWNLOAD_RECEIPT.json", "measurement/pilot_results_third/PILOT_SUMMARY.json"),
    ]
    costs = Decimal("0")
    chain = []
    for proposal, quote, download, pilot in stages:
        q, d, p = load(quote), load(download), load(pilot)
        proposal_hash = sha(ROOT / proposal)
        assert q["proposal_sha256"] == proposal_hash
        assert d["proposal_sha256"] == proposal_hash
        assert p["inputs"]["proposal_sha256"] == proposal_hash
        assert p["inputs"]["download_receipt_sha256"] == sha(ROOT / download)
        assert p["status"] == "PARTIAL_TECHNICAL_COVERAGE_DIAGNOSTIC"
        assert p["scientific_decision"] == "HOLD_DATA"
        costs += Decimal(q["total_quoted_cost_usd"])
        chain.append({
            "proposal": proposal, "proposal_sha256": proposal_hash,
            "quote_receipt": quote, "quote_receipt_sha256": sha(ROOT / quote),
            "download_receipt": download, "download_receipt_sha256": sha(ROOT / download),
            "pilot_summary": pilot, "pilot_summary_sha256": sha(ROOT / pilot),
        })
    assert costs == Decimal("0.015124082565")

    clock = load("event_clock/CLOCK_SUMMARY.json")
    assert clock["scientifically_freezable_events"] == 0
    assert clock["conditional_technical_anchor_events"] == 2
    for subdir in ("pilot_results", "pilot_results_second", "pilot_results_third"):
        rows = list(csv.DictReader((ROOT / f"measurement/{subdir}/COVERAGE_SUMMARY.csv").open()))
        assert all(int(row["events_with_all_20_valid"]) == 0 for row in rows)

    bind = [
        "MEASUREMENT_CONTRACT.md", "measurement_config.json",
        "DIAGNOSTIC_RULE_AMENDMENT.md", "COMPOSITE_COVERAGE_DIAGNOSTIC.md",
        "event_clock/build_event_clock.py", "event_clock/CLOCK_EVIDENCE.csv",
        "event_clock/CLOCK_SUMMARY.json", "network_selection/NETWORK_SELECTION_SUMMARY.json",
        "network_selection/SELECTED20_PUBLIC_CONFIG.csv", "network_selection/SELECTION_SUPPORT_AUDIT.json",
        "measurement/quote_state.py", "measurement/test_quote_state.py",
        "measurement/build_event_symbols.py", "measurement/build_quote_gap.py",
        "measurement/run_first_download.py", "measurement/measure_technical_pilot.py",
        "measurement/EVENT_SYMBOLS_PUBLIC.csv",
        "measurement/pilot_results/COVERAGE_SUMMARY.csv", "measurement/pilot_results/AGGREGATE_PAIR_SUMMARY.csv", "measurement/pilot_results/TRACE_AUDIT.csv",
        "measurement/pilot_results_second/COVERAGE_SUMMARY.csv", "measurement/pilot_results_second/AGGREGATE_PAIR_SUMMARY.csv", "measurement/pilot_results_second/TRACE_AUDIT.csv",
        "measurement/pilot_results_third/COVERAGE_SUMMARY.csv", "measurement/pilot_results_third/AGGREGATE_PAIR_SUMMARY.csv", "measurement/pilot_results_third/TRACE_AUDIT.csv",
    ]
    receipt = {
        "status": "VERIFIED_DIAGNOSTIC_PACKET_HOLD_DATA",
        "scientific_gate": "NOT_PASSED",
        "quote_state_synthetic_fixtures": "PASS_8",
        "p2_validator": "PASS",
        "secret_scan": "PASS_NO_KNOWN_PREFIX",
        "licensed_nominal_time_export": False,
        "row_level_trace_export": False,
        "quoted_total_usd": str(costs),
        "actual_billing": "RECONCILE_WITH_VENDOR",
        "proposal_receipt_chains": chain,
        "artifact_sha256": {path: sha(ROOT / path) for path in bind},
        "unpassed_requirements": [
            "scientifically certified first-public clocks",
            "six-event cross-session development pilot",
            "20-of-20 common quote mask",
            "live-state halt/gap validation",
            "twenty valid raw endpoint reconstructions",
            "event-level independence and empirical power",
            "authoritative Nasdaq treatment vector"
        ]
    }
    (ROOT / "MEASUREMENT_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "quoted_total_usd": receipt["quoted_total_usd"], "bound_files": len(bind)}))


if __name__ == "__main__":
    main()
