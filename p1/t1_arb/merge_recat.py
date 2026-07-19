#!/usr/bin/env python3
"""BOX-ONLY. Fold deepseek's full-text re-categorization back into
t1_events_final.json. A no_event filing that deepseek now reads as a real
MF->ETF conversion is flipped to event (with the recovered fields); one it
re-confirms as no_event keeps its verdict but records the fresh reason+evidence.
Every change is stamped adjudication_source=recat-fulltext for the audit trail.
Then re-assemble + re-export.

Run (after run_mopup.py P1-T1-recat --live):
  python p1/t1_arb/merge_recat.py
  python ops/runner/contracts.py events_merged p1/events_merged.csv
  git add -f ops/l1/out/P1-T1-recat.json
  git add p1/t1_events_final.json p1/events_merged.csv p1/t1_full_audit.* p1/t1_arb/arb_report.md
  git commit -m "P1-T1: full-text re-categorization recovery" && git push
"""
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / "p1" / "t1_arb"
FINAL = ROOT / "p1" / "t1_events_final.json"
OUTJSON = ROOT / "ops" / "l1" / "out" / "P1-T1-recat.json"
FIELDS = ("fund_name", "family", "mutual_fund_ticker", "etf_ticker", "announce_date",
          "effective_date", "asset_class", "AUM_at_conversion_USD", "confidence", "evidence")


def parse(v):
    if isinstance(v, str):
        try:
            return json.loads(v)
        except ValueError:
            return None
    return v if isinstance(v, dict) else None


def main():
    if not OUTJSON.exists():
        sys.exit(f"missing {OUTJSON} — run run_mopup.py P1-T1-recat --live first")
    out = json.loads(OUTJSON.read_text())
    final = json.loads(FINAL.read_text())
    flipped = confirmed = 0
    for acc, v in out.items():
        if acc in ("S1", "S2", "S3") or acc not in final:
            continue
        obj = parse(v)
        if not obj:
            continue
        cur = final[acc]
        if str(obj.get("verdict", "")).lower() == "event":
            e = {k: str(obj.get(k, "NA")) for k in FIELDS}
            e["source_accession"] = acc
            final[acc] = {"events": [e], "_adjudication": {"source": "recat-fulltext",
                          "deepseek_v2A_was": ("no_event:" + str(cur.get("reason", ""))), "final": "event"}}
            flipped += 1
        else:
            # keep no_event; refresh reason+evidence, clear any recheck_noevent flag
            final[acc] = {"no_event": True, "reason": obj.get("reason", cur.get("reason", "")),
                          "evidence": str(obj.get("evidence", ""))[:200],
                          "_adjudication": {"source": "recat-fulltext",
                                            "deepseek_v2A_was": ("no_event:" + str(cur.get("reason", ""))),
                                            "final": "no_event"}}
            confirmed += 1
    FINAL.write_text(json.dumps(final, indent=1, ensure_ascii=False))
    print(f"re-categorization: {flipped} flipped no_event->event, {confirmed} re-confirmed no_event")
    subprocess.run([sys.executable, str(HERE / "assemble.py")], check=True)
    subprocess.run([sys.executable, str(HERE / "export_full_audit.py")], check=True)


if __name__ == "__main__":
    main()
