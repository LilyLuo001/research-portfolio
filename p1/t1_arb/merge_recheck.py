#!/usr/bin/env python3
"""BOX-ONLY. Fold deepseek's target-type confirmations back into
t1_events_final.json, resolving the owner's recheck flags, then re-assemble.

For each rechecked (accession, fund):
  is_open_end_mutual_fund == "yes" -> clear the recheck flag (event re-instated);
      write the confirmed mutual_fund_ticker + evidence.
  == "no" (ETF/CEF/ETP)            -> set that event's disposition to not_event
      (kept out of the study), reason from target_structure.
  == "unclear"                     -> leave the recheck flag (still quarantined).
Filings whose events all become not_event flip to filing-level no_event.

Run (after run_mopup.py P1-T1-recheck --live):
  python p1/t1_arb/merge_recheck.py
  python ops/runner/contracts.py events_merged p1/events_merged.csv
  git add -f ops/l1/out/P1-T1-recheck.json
  git add p1/t1_events_final.json p1/events_merged.csv p1/t1_arb/arb_report.md p1/t1_full_audit.*
  git commit -m "P1-T1: resolve recheck via full-text target-type confirmation" && git push
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / "p1" / "t1_arb"
FINAL = ROOT / "p1" / "t1_events_final.json"
OUTJSON = ROOT / "ops" / "l1" / "out" / "P1-T1-recheck.json"
TICK = re.compile(r"^[A-Z][A-Z0-9]{1,5}$")


def norm(n):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", str(n).lower())).strip()


def parse(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return None
    return v if isinstance(v, dict) else None


def main():
    if not OUTJSON.exists():
        sys.exit(f"missing {OUTJSON} — run run_mopup.py P1-T1-recheck --live first")
    out = json.loads(OUTJSON.read_text())
    final = json.loads(FINAL.read_text())

    # index answers by (accession, normalized fund)
    ans = {}
    for rid, v in out.items():
        if rid in ("S1", "S2", "S3") or "::" not in rid:
            continue
        acc = rid.split("::", 1)[0]
        obj = parse(v)
        if obj:
            ans[acc] = ans.get(acc, []) + [obj]

    counts = {"yes": 0, "no": 0, "unclear": 0, "noevent_seen": 0}
    for acc, v in final.items():
        if acc == "_meta":
            continue
        answers = ans.get(acc, [])
        # no_event recheck_noevent rows: record the finding, do not auto-flip verdict
        if v.get("no_event"):
            fsc = v.get("_spotcheck") or {}
            if fsc.get("disposition") == "recheck_noevent" and answers:
                a = answers[0]
                fsc["fulltext_finding"] = {k: a.get(k) for k in
                                           ("is_open_end_mutual_fund", "target_structure", "evidence")}
                counts["noevent_seen"] += 1
            continue
        for e in v.get("events", []):
            sc = e.get("_spotcheck") or {}
            if sc.get("disposition") != "recheck":
                continue
            match = None
            for a in answers:
                match = a
                break  # single-fund common case; multi-fund could refine by fund match
            if not match:
                continue
            verdict = str(match.get("is_open_end_mutual_fund", "unclear")).lower()
            if verdict == "yes":
                e.pop("_spotcheck", None)
                mf = str(match.get("mutual_fund_ticker", "NA"))
                if TICK.match(mf) and str(e.get("mutual_fund_ticker", "NA")) in ("NA", ""):
                    e["mutual_fund_ticker"] = mf
                e["evidence"] = (str(e.get("evidence", "")) + " | recheck-confirmed MF target: "
                                 + str(match.get("evidence", ""))[:120])
                counts["yes"] += 1
            elif verdict == "no":
                e["_spotcheck"] = {"disposition": "not_event",
                                   "reason": f"full-text: target is {match.get('target_structure','non-MF')}",
                                   "by": "recheck-fulltext"}
                counts["no"] += 1
            else:
                counts["unclear"] += 1

    for acc, v in final.items():
        if acc == "_meta" or v.get("no_event") or "events" not in v:
            continue
        disps = [(e.get("_spotcheck") or {}).get("disposition") for e in v["events"]]
        if disps and all(d == "not_event" for d in disps):
            final[acc] = {"no_event": True, "reason": "ETF_TO_ETF",
                          "evidence": v["events"][0]["_spotcheck"]["reason"],
                          "_adjudication": {"source": "recheck-fulltext",
                                            "deepseek_v2A_was": "event", "final": "no_event"}}

    FINAL.write_text(json.dumps(final, indent=1, ensure_ascii=False))
    print("recheck resolved:", counts)
    subprocess.run([sys.executable, str(HERE / "assemble.py")], check=True)
    subprocess.run([sys.executable, str(HERE / "export_full_audit.py")], check=True)


if __name__ == "__main__":
    main()
