#!/usr/bin/env python3
"""Apply Human Gate 1 (P1-T1-spotcheck) owner rulings to t1_events_final.json.

Owner reviewed p1/t1_spotcheck_sample.json (57 rows: all 47 M/L + 10% of H) and
flagged false positives — un-refereed deepseek rows that never went through qwen
arbitration. Each ruling is recorded here with its disposition; the patch is
auditable and rerunnable (idempotent). Dispositions the assembler excludes from
events_merged.csv: filing-level no_event (ETF_TO_ETF), or an event tagged
_spotcheck.disposition in {not_event, recheck, defer}.

The over-merge that corrupted 'Emerging Markets Portfolio' announce_date is NOT
patched here — it is fixed structurally in assemble.py (grouping key now includes
family, so Sanford C. Bernstein's Portfolio no longer merges with Mirae's Fund).
"""
import json
import pathlib

FINAL = pathlib.Path(__file__).resolve().parents[1] / "t1_events_final.json"

# whole single-fund conversions ruled ETF-to-ETF (all filings of each) -> no_event
ETF2ETF_FILINGS = {
    "0000894189-19-007768": "American Energy Independence ETF — Target Fund is an ETF (evidence: 'Both are ETFs')",
    "0000894189-19-006521": "Cambria Core Equity ETF — Target Fund is an ETF",
    "0000894189-19-007642": "Cambria Core Equity ETF — Target Fund is an ETF",
    "0000894189-21-001425": "American Customer Satisfaction ETF — ETF trust move (Tidal)",
    "0000894189-21-002216": "American Customer Satisfaction ETF — ETF trust move (Tidal)",
    "0001999371-24-004354": "Nationwide Nasdaq-100 Risk-Managed Income ETF — Target is an actively-managed ETF",
}
# per-event dispositions inside multi-fund filings (fund_name match within a filing)
PER_EVENT = {
    # iM multi-fund N-14s: the two DBi ETFs are ETF-to-ETF; the Corporate Bond FUND is unconfirmed
    ("0001193125-21-250290", "iM DBi Managed Futures Strategy ETF"): ("not_event", "ETF_TO_ETF: target is an ETF"),
    ("0001193125-21-250290", "iM DBi Hedge Strategy ETF"): ("not_event", "ETF_TO_ETF: target is an ETF"),
    ("0001193125-21-217182", "iM DBi Managed Futures Strategy ETF"): ("not_event", "ETF_TO_ETF: target is an ETF"),
    ("0001193125-21-217182", "iM DBi Hedge Strategy ETF"): ("not_event", "ETF_TO_ETF: target is an ETF"),
    ("0001193125-21-250290", "iM Dolan McEniry Corporate Bond Fund"): ("recheck", "evidence describes the DBi ETFs, not this fund; confirm target was a mutual fund"),
    ("0001193125-21-217182", "iM Dolan McEniry Corporate Bond Fund"): ("recheck", "evidence describes the DBi ETFs, not this fund; confirm target was a mutual fund"),
}
# whole conversions deferred (all filings, all funds) — source future-dated vs gate 2026-07-18
DEFER_FUNDS = {"Zevenbergen Growth Fund", "Zevenbergen Genea Fund"}
DEFER_REASON = "source filed 2026-07-28 (>gate 2026-07-18); cannot verify as of gate date"


def main():
    final = json.loads(FINAL.read_text())
    n_noevent = n_event_tag = n_defer = 0

    for fid in ETF2ETF_FILINGS:
        v = final.get(fid)
        if not v or v.get("no_event"):
            continue
        final[fid] = {"no_event": True, "reason": "ETF_TO_ETF",
                      "evidence": ETF2ETF_FILINGS[fid],
                      "_adjudication": {"source": "owner-gate-spotcheck",
                                        "deepseek_v2A_was": "event", "final": "no_event"}}
        n_noevent += 1

    for fid, v in final.items():
        if fid == "_meta" or v.get("no_event") or "events" not in v:
            continue
        for e in v["events"]:
            fn = str(e.get("fund_name"))
            key = (fid, fn)
            if key in PER_EVENT:
                disp, reason = PER_EVENT[key]
                e["_spotcheck"] = {"disposition": disp, "reason": reason, "by": "owner-gate"}
                n_event_tag += 1
            elif fn in DEFER_FUNDS:
                e["_spotcheck"] = {"disposition": "defer", "reason": DEFER_REASON, "by": "owner-gate"}
                n_defer += 1

    FINAL.write_text(json.dumps(final, indent=1, ensure_ascii=False))
    print(f"applied: {n_noevent} filings -> no_event (ETF_TO_ETF); "
          f"{n_event_tag} events tagged (not_event/recheck); {n_defer} events deferred.")


if __name__ == "__main__":
    main()
