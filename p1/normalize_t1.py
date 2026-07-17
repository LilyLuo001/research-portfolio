#!/usr/bin/env python3
"""Mechanical normalization of P1-T1-events channel outputs for arbitration.

Usage (repo root):  python p1/normalize_t1.py
Reads  ops/l1/out/P1-T1-events.json  and  ops/l1/out/P1-T1-events-B.json
Writes p1/t1_normalized/A.json / B.json + a per-channel change log.

Re-runnable and idempotent — re-apply after the channel-B mop-up merges.
Rules (QC report p1/t1_qc_report.md §4; POLICY p1/t1_channelA_wip/POLICY.md):
  dates   : parse to YYYY-MM-DD; month/quarter/prose without a day -> "NA"
            (original preserved in _norm log; policy: vague dates are NA+note)
  tickers : keep only plausible symbols (2-6 chars A-Z, digits allowed after
            first char); fund names / multi-class lists -> "NA" (originals
            preserved in the row's "_raw_<field>" key for the arb to consult)
  keys    : sentinels dropped; only spec IDs pass through
No semantic edits: verdicts (event/no_event), fund names, confidence are
untouched. This is format canonicalization only.
"""
import datetime
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "p1" / "t1_normalized"
SRC = {"A": ROOT / "ops/l1/out/P1-T1-events.json",
       "B": ROOT / "ops/l1/out/P1-T1-events-B.json"}
SENT = {"S1", "S2", "S3"}

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TICKER = re.compile(r"^[A-Z][A-Z0-9]{1,5}$")
MONTHS = {m.lower(): i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}
PROSE_DATE = re.compile(r"^([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})$")
DATE_FIELDS = ("announce_date", "effective_date")
TICK_FIELDS = ("mutual_fund_ticker", "etf_ticker")


def norm_date(v):
    """-> (normalized, changed?). Vague/unparseable dates become NA."""
    s = str(v).strip()
    if s in ("", "NA") or ISO.match(s):
        return (s or "NA"), False
    m = PROSE_DATE.match(s)
    if m and m.group(1).lower() in MONTHS:
        try:
            d = datetime.date(int(m.group(3)), MONTHS[m.group(1).lower()], int(m.group(2)))
            return d.isoformat(), True
        except ValueError:
            pass
    return "NA", True  # month-only, quarter, prose ranges -> NA per policy


def norm_ticker(v):
    s = str(v).strip()
    if s in ("", "NA"):
        return "NA", False
    if TICKER.match(s):
        return s, False
    return "NA", True  # fund names, multi-class lists, lowercase junk


def norm_row(row, log, key):
    for f in DATE_FIELDS:
        if f in row:
            new, ch = norm_date(row[f])
            if ch:
                log.append({"id": key, "field": f, "from": str(row[f]), "to": new})
                row["_raw_" + f] = str(row[f])
                row[f] = new
    for f in TICK_FIELDS:
        if f in row:
            new, ch = norm_ticker(row[f])
            if ch:
                log.append({"id": key, "field": f, "from": str(row[f])[:80], "to": new})
                row["_raw_" + f] = str(row[f])[:120]
                row[f] = new
    return row


def main():
    OUT.mkdir(exist_ok=True)
    for ch, path in SRC.items():
        raw = json.loads(path.read_text())
        norm, log, skipped = {}, [], []
        for k, v in raw.items():
            if k in SENT:
                continue
            if isinstance(v, str):
                try:
                    v = json.loads(v)
                except ValueError:
                    skipped.append(k)
                    continue
            if not isinstance(v, dict):
                skipped.append(k)
                continue
            if v.get("no_event") or v.get("NEED_HUMAN"):
                norm[k] = v
                continue
            if "events" in v and isinstance(v["events"], list):
                v["events"] = [norm_row(dict(e), log, k) for e in v["events"]
                               if isinstance(e, dict)]
                norm[k] = v
            else:
                norm[k] = norm_row(dict(v), log, k)
        (OUT / f"{ch}.json").write_text(json.dumps(norm, indent=1, ensure_ascii=False))
        (OUT / f"{ch}.changes.json").write_text(json.dumps(
            {"source": str(path.relative_to(ROOT)), "n_answers": len(norm),
             "n_changes": len(log), "skipped_unparseable": skipped,
             "changes": log}, indent=1, ensure_ascii=False))
        print(f"channel {ch}: {len(norm)} answers, {len(log)} field normalizations, "
              f"{len(skipped)} unparseable skipped -> p1/t1_normalized/{ch}.json")


if __name__ == "__main__":
    main()
