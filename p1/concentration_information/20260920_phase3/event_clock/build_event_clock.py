#!/usr/bin/env python3
"""Build P3's public-event-clock evidence table without reading outcomes.

Inputs are the 32 SCC roster event identifiers and economic dates copied below
after a targeted metadata-only roster read. Licensed nominal times are not
copied or exported. The only network retrieval in this script is SEC's
submissions metadata JSON; six issuer-page findings are imported from the
prior bounded public-metadata check. No filing body, exhibit, market data,
earnings value, forecast, price, return, quote, or call-time is fetched.

SEC acceptance time proves when that filing became public on EDGAR; it does
*not* prove the issuer's release was first public then.  It is therefore only
an upper endpoint for the unknown earliest-public-release time.
"""
import csv
import certifi
import hashlib
import json
import ssl
from collections import Counter
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

OUT = Path(__file__).resolve().parent
NY = ZoneInfo("America/New_York")
USER_AGENT = "P1-concentration-information event-clock metadata research contact@example.invalid"

# This is solely the existing safe calendar's public issuer identity and
# economic date. Licensed nominal-time values are intentionally not copied to
# code or Git output.
ISSUERS = [
    (1, "Apple Inc.", "0000320193", ["2023-02-02","2023-05-04","2023-08-03","2023-11-02"]),
    (2, "Microsoft Corp.", "0000789019", ["2023-01-24","2023-04-25","2023-07-25","2023-10-24"]),
    (3, "Alphabet Inc.", "0001652044", ["2023-02-02","2023-04-25","2023-07-25","2023-10-24"]),
    (4, "Amazon.com, Inc.", "0001018724", ["2023-02-02","2023-04-27","2023-08-03","2023-10-26"]),
    (5, "Berkshire Hathaway Inc.", "0001067983", ["2023-02-25","2023-05-06","2023-08-05","2023-11-04"]),
    (6, "UnitedHealth Group Inc.", "0000731766", ["2023-01-13","2023-04-14","2023-07-14","2023-10-13"]),
    (7, "Johnson & Johnson", "0000200406", ["2023-01-24","2023-04-18","2023-07-20","2023-10-17"]),
    (8, "Exxon Mobil Corp.", "0000034088", ["2023-01-31","2023-04-28","2023-07-28","2023-10-27"]),
]

FIELDS = ["event_id","issuer_rank_2022_end","issuer","event_date","session_status","source_url","source_category","source_filing_form","source_filing_items","source_acceptance_utc","source_acceptance_et","issuer_page_url","issuer_page_source_category","issuer_page_publication_evidence","timezone","time_precision","earliest_bound_et","latest_bound_et","bound_basis","first_public_status","supports_1m","supports_5m","supports_15m","supports_60m","pilot_status","evidence_note"]

# Exactly the six pre-specified bounded-follow-up events. Evidence was read
# from publisher metadata only, stopping before page body text.
FOLLOWUP = {
 "P1-2023-08-01": ("https://corporate.exxonmobil.com/news/news-releases/2023/0131_exxonmobil-announces-full-year-2022-results", "ISSUER_NEWSROOM_META", "article:published_time=2023-01-31T11:30:00Z", "2023-01-31T06:30:00-05:00", "2023-01-31T06:30:59-05:00"),
 "P1-2023-06-02": ("https://www.unitedhealthgroup.com/newsroom/2023/2023-04-14-uhg-reports-first-quarter-results.html", "ISSUER_NEWSROOM_META", "articleDate=April 14, 2023; date only, no publication clock", None, None),
 "P1-2023-08-03": ("https://corporate.exxonmobil.com/news/news-releases/2023/0728_exxonmobil-announces-second-quarter-2023-results", "ISSUER_NEWSROOM_META", "article:published_time=2023-07-28T10:00:00Z", "2023-07-28T06:00:00-04:00", "2023-07-28T06:00:59-04:00"),
 "P1-2023-01-01": ("https://www.apple.com/newsroom/2023/02/apple-reports-first-quarter-results/", "ISSUER_NEWSROOM", "No explicit publication clock accepted; existing metadata is date-only.", None, None),
 "P1-2023-02-02": ("https://news.microsoft.com/source/2023/04/25/microsoft-earnings-press-release-available-on-investor-relations-website-18/", "ISSUER_NEWSROOM", "No explicit publication clock accepted in bounded metadata-only check.", None, None),
 "P1-2023-01-03": ("https://www.apple.com/newsroom/2023/08/apple-reports-third-quarter-results/", "ISSUER_NEWSROOM", "No explicit publication clock accepted; existing metadata is date-only.", None, None),
}

def sec_json(cik):
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    req = Request(url, headers={"User-Agent": USER_AGENT})
    # Explicit CA bundle avoids relying on a local Python-install default.
    with urlopen(req, timeout=45, context=ssl.create_default_context(cafile=certifi.where())) as r:
        return url, json.load(r)

def session(day, stamp):
    # Explicitly retains closed dates: it never substitutes the next open.
    if day.weekday() >= 5:
        return "WEEKEND_CLOSED"
    if stamp < time(9,30): return "PRE_OPEN"
    if stamp >= time(16,0): return "AFTER_CLOSE"
    return "RTH"

def select_filing(recent, event_day):
    """Closest same-/next-day 8-K, preferring Item 2.02, from metadata only."""
    candidates=[]
    for i, form in enumerate(recent.get("form", [])):
        fd=recent["filingDate"][i]
        if form != "8-K" or fd not in {event_day.isoformat(), (event_day+timedelta(days=1)).isoformat()}:
            continue
        items=(recent.get("items", [""]*len(recent["form"]))[i] or "")
        accepted=recent.get("acceptanceDateTime", [""]*len(recent["form"]))[i] or ""
        # Metadata row is useful only with an acceptance timestamp.
        if not accepted: continue
        score=(0 if "2.02" in items else 1, 0 if fd == event_day.isoformat() else 1, accepted)
        candidates.append((score,i))
    return min(candidates)[1] if candidates else None

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    records=[]; sec_receipts=[]
    for rank, issuer, cik, events in ISSUERS:
        endpoint, data=sec_json(cik)
        raw=json.dumps(data, sort_keys=True, separators=(",", ":")).encode()
        recent=data["filings"]["recent"]
        sec_receipts.append({"issuer":issuer,"cik":cik,"url":endpoint,"sha256":hashlib.sha256(raw).hexdigest(),"retrieved_utc":datetime.now(timezone.utc).isoformat()})
        for seq,day_s in enumerate(events, 1):
            day=date.fromisoformat(day_s)
            idx=select_filing(recent, day)
            base={"event_id":f"P1-2023-{rank:02d}-{seq:02d}","issuer_rank_2022_end":rank,"issuer":issuer,"event_date":day_s,
                  "session_status":"UNKNOWN_NO_PUBLIC_RELEASE_CLOCK","issuer_page_url":"","issuer_page_source_category":"NOT_CHECKED","issuer_page_publication_evidence":"NOT_CHECKED","timezone":"America/New_York","first_public_status":"UNPROVEN","supports_1m":"NO","supports_5m":"NO","supports_15m":"NO","supports_60m":"NO"}
            if idx is None:
                records.append(base | {"source_url":endpoint,"source_category":"SEC_SUBMISSIONS_METADATA_NO_SAME_NEXT_DAY_8K_MATCH","source_filing_form":"","source_filing_items":"","source_acceptance_utc":"","source_acceptance_et":"","time_precision":"UNKNOWN","earliest_bound_et":"UNKNOWN","latest_bound_et":"UNKNOWN","bound_basis":"No same-/next-day SEC 8-K metadata match; no issuance-time inference.","pilot_status":"NOT_ELIGIBLE_CLOCK_UNKNOWN","evidence_note":"SEC issuer metadata endpoint retained; it yielded no qualifying timestamp."})
                continue
            accession=recent["accessionNumber"][idx]; items=recent.get("items",[""]*len(recent["form"]))[idx] or ""
            acc_utc=datetime.fromisoformat(recent["acceptanceDateTime"][idx].replace("Z","+00:00"))
            acc_et=acc_utc.astimezone(NY)
            accession_nodash=accession.replace("-","")
            filing_url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_nodash}/"
            # A date-only official issuer release may establish the economic
            # date, but cannot tighten the time.  The SEC timestamp is a
            # latest documented public endpoint, not the release's first time.
            records.append(base | {"source_url":filing_url,"source_category":"SEC_SUBMISSIONS_METADATA_8K","source_filing_form":"8-K","source_filing_items":items,
                "source_acceptance_utc":acc_utc.isoformat().replace("+00:00","Z"),"source_acceptance_et":acc_et.isoformat(),"time_precision":"SECOND_FOR_SEC_ACCEPTANCE_ONLY",
                "earliest_bound_et":"UNKNOWN","latest_bound_et":acc_et.isoformat(),"bound_basis":"SEC acceptance timestamp is a public-filing upper endpoint only; issuer release may have been public earlier.",
                "pilot_status":"NOT_ELIGIBLE_EARLIEST_TIME_UNPROVEN","evidence_note":"Do not use filing time, nominal time, or later call time as the earnings-release timestamp."})
    assert len(records)==32
    for row in records:
        if row["event_id"] not in FOLLOWUP: continue
        url, category, evidence, lo, hi = FOLLOWUP[row["event_id"]]
        row.update({"issuer_page_url":url,"issuer_page_source_category":category,"issuer_page_publication_evidence":evidence})
        if lo:
            # :00 in publisher metadata does not establish seconds precision.
            row.update({"time_precision":"MINUTE_ISSUER_PAGE_PUBLICATION_CLOCK","earliest_bound_et":lo,"latest_bound_et":hi,
                        "bound_basis":"Issuer article:published_time metadata represented conservatively as a one-minute interval; first-public status is not independently certified.",
                        "first_public_status":"ISSUER_METADATA_NOT_CERTIFIED_FIRST_PUBLIC","supports_5m":"CONDITIONAL","supports_15m":"CONDITIONAL","supports_60m":"CONDITIONAL","pilot_status":"TECHNICAL_ANCHOR_ONLY_NOT_SCIENTIFICALLY_FREEZABLE"})
            row["session_status"]="PRE_OPEN_FROM_ISSUER_METADATA_TECHNICAL_ANCHOR"
    with (OUT/"CLOCK_EVIDENCE.csv").open("w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(records)
    session_counts=Counter(x["session_status"] for x in records)
    support={h:{"certified_yes":sum(x[f"supports_{h}"]=="YES" for x in records),"conditional_technical_anchor":sum(x[f"supports_{h}"]=="CONDITIONAL" for x in records)} for h in ["1m","5m","15m","60m"]}
    summary={"scope":"Public issuer identity/date plus SEC submissions metadata and imported prior issuer-page metadata findings; licensed nominal times are not exported; no financial values, forecasts, prices, returns, quotes, call times, or outcomes read/stored.",
      "input_roster":"2022-12-30 top-8 / 32 2023 release groups preserved; licensed nominal times not exported","events":len(records),"session_counts":dict(session_counts),"clock_precision_counts":dict(Counter(x["time_precision"] for x in records)),
      "horizon_support_counts":support,"scientifically_freezable_events":0,"conditional_technical_anchor_events":sum(x["pilot_status"]=="TECHNICAL_ANCHOR_ONLY_NOT_SCIENTIFICALLY_FREEZABLE" for x in records),
      "reason_no_event_is_frozen":"SEC acceptance is never substituted for release time. Two issuer-page metadata clocks are retained only as technical anchors because first-public status is not independently certified; four of six remain UNKNOWN.",
      "candidate_pilot_design":"If independent issuer/wire time-stamped releases are later found, prioritize three PRE_OPEN and three AFTER_CLOSE events across winter/summer before looking at any outcomes; this output does not select by response.",
      "provisional_six_to_recheck_before_freeze":["P1-2023-08-01","P1-2023-06-02","P1-2023-08-03","P1-2023-01-01","P1-2023-02-02","P1-2023-01-03"],
      "bounded_followup_result":{"checked":6,"issuer_page_minute_intervals":2,"unknown_after_check":4,"checked_event_ids":list(FOLLOWUP)},
      "sec_metadata_receipts":sec_receipts,"no_next_open_substitution":True,"no_modified_time_used":True,"no_call_time_used":True,"no_price_inference_used":True}
    (OUT/"CLOCK_SUMMARY.json").write_text(json.dumps(summary,indent=2)+"\n")
    report = f"""# P3 event-clock evidence\n\n## Result\n\nThe 2022-12-30 top-eight roster and all 32 2023 release groups are preserved.\nNo event is frozen for the minute-level technical pilot: **0/32** support 1, 5, 15, or 60 minutes. This is a deliberate clock-quality stop, not an outcome-based screen.\n\n## Evidence rule\n\nEach row in `CLOCK_EVIDENCE.csv` has an SEC submissions-metadata URL. For 26 events, the matched same-/next-day Form 8-K supplies an exact EDGAR acceptance timestamp. That timestamp is a documented public filing endpoint, not proof of the earliest issuer release. The remaining 6 rows retain the issuer SEC metadata URL and remain UNKNOWN. Neither `dateModified`, conference-call time, nor any market movement was used.\n\nThe I/B/E/S nominal ET/DST time is retained only to classify the existing calendar (16 AFTER_CLOSE, 12 PRE_OPEN, 4 WEEKEND_CLOSED). It is never promoted to an earliest-public timestamp; closed events are not moved to the next opening.\n\n## Precision and pilot gate\n\n| Layer | Count | Eligible |\n|---|---:|---:|\n| Exact SEC-acceptance timestamp only | 26 | 0 |\n| Unknown (no qualifying matched 8-K) | 6 | 0 |\n| 1 minute | 0 | 0 |\n| 5 minutes | 0 | 0 |\n| 15 minutes | 0 | 0 |\n| 60 minutes | 0 | 0 |\n\nA pre-specified, response-blind six-event recheck set is listed in `CLOCK_SUMMARY.json`; it has **0** currently freezable events. It includes three nominal PRE_OPEN and three nominal AFTER_CLOSE events across winter, spring, and summer. The next permissible action is bounded: obtain an independently time-stamped issuer release or official wire record for those six, then recompute the earliest/latest interval. Do not infer it from the SEC filing, a call, page modification metadata, or price behavior.\n\n## Explicit gap\n\nNo row presently has a defensible earliest-public-release time or sufficiently tight interval. Consequently, P3 can preserve date/session facts and SEC audit links, but it cannot authorize intraday purchase windows or quote-response horizons.\n"""
    report=report.replace("No event is frozen for the minute-level technical pilot: **0/32** support 1, 5, 15, or 60 minutes.", "The bounded six-event issuer-page follow-up found two issuer publication clocks at minute precision. Thus **2/32** support 5, 15, and 60 minutes; none supports 1 minute.")
    report=report.replace("| Exact SEC-acceptance timestamp only | 26 | 0 |", "| Exact SEC-acceptance timestamp only | 24 | 0 |\n| Issuer-page publication clock (one-minute interval) | 2 | 2 for 5m+ |")
    report=report.replace("| 5 minutes | 0 | 0 |\n| 15 minutes | 0 | 0 |\n| 60 minutes | 0 | 0 |", "| 5 minutes | 2 | 2 |\n| 15 minutes | 2 | 2 |\n| 60 minutes | 2 | 2 |")
    report=report.replace("it has **0** currently freezable events.", "it has **2** provisionally freezable events for 5m+ only; the other four remain UNKNOWN.")
    report=report.replace("No row presently has a defensible earliest-public-release time or sufficiently tight interval. Consequently, P3 can preserve date/session facts and SEC audit links, but it cannot authorize intraday purchase windows or quote-response horizons.", "The two Exxon issuer-page clocks are sufficient only for a bounded 5m+ technical recheck. No evidence supports 1-minute endpoints, and four of six selected events still lack a defensible interval. P3 cannot yet freeze the planned six-event cross-session pilot or authorize broad intraday purchase windows.")
    report="""# P3 event-clock evidence

## Result

The 2022-12-30 top-eight roster and all 32 candidate 2023 release groups are preserved. **Zero events are scientifically frozen for intraday response analysis.** Two Exxon issuer pages expose `article:published_time` metadata and are retained as conditional 5m+ technical anchors only; the metadata is not independent proof that this was the first public release.

## Evidence rule

SEC acceptance is a public-filing upper endpoint, never a substitute for the release time. I/B/E/S nominal time is retained only for calendar classification. Closed dates are not moved to the next open. Page modification time, conference-call time, and price behavior are not used.

The two issuer metadata values end in `:00`. The code conservatively represents each as a one-minute interval rather than claiming seconds precision. This rounding convention controls only a technical coverage diagnostic. A scientifically usable event still requires an issuer/wire record whose timestamp and first-public interpretation are documented.

## Gate

| Layer | Count | Scientific eligibility |
|---|---:|---:|
| Candidate release groups | 32 | 0 |
| Conditional issuer-metadata technical anchors | 2 | 0 |
| Other events without a qualifying interval | 30 | 0 |
| Certified 1m/5m/15m/60m events | 0 | 0 |

The next bounded action is to source-lock three AFTER_CLOSE and one additional PRE_OPEN release from the frozen calendar using issuer/wire publication evidence, without looking at responses. The two current anchors and purchased quote windows remain implementation diagnostics, not outcome evidence.
"""
    (OUT/"REPORT.md").write_text(report)
    receipt={"stage":"P3 event clock","status":"COMPLETE_ZERO_SCIENTIFICALLY_FROZEN_TWO_CONDITIONAL_TECHNICAL_ANCHORS","started_and_completed_utc":datetime.now(timezone.utc).isoformat(),"script":"build_event_clock.py","outputs":["CLOCK_EVIDENCE.csv","CLOCK_SUMMARY.json","REPORT.md","RECEIPT.json"],"network_reads_this_execution":"SEC submissions metadata JSON only","imported_prior_public_metadata_findings":"FOLLOWUP dictionary records exactly six pre-specified issuer-page URLs and prior bounded metadata findings; this execution does not refetch issuer pages","prohibited_data_read":False,"spend_usd":0,"unresolved":"First-public status is unproven for both technical anchors; four of six provisional events and 30 of 32 total events lack a qualifying interval."}
    (OUT/"RECEIPT.json").write_text(json.dumps(receipt,indent=2)+"\n")

if __name__ == "__main__": main()
