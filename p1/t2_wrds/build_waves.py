#!/usr/bin/env python3
"""P1-T2 — build the conversion WAVE table from events_merged.csv.

A wave is the set of conversions sharing one effective_date (Project_1.md §52-53);
DFA's 2021-06-11 wave is the anchor. This step is data-source agnostic (pure
grouping of T1 output) so it is shared by both the WRDS path and the free
EDGAR path. No paid data, no network.

Only rows with a REAL ISO effective_date enter a wave. Held-back rows (effective
_date == 'NA', carrying only effective_date_approx) are logged and excluded — we
never assign a treated stock to an approximate date (Project_1.md §113: no
interpolation of missing holding periods; same discipline applies to timing).

  python p1/t2_wrds/build_waves.py
Output: p1/t2_wrds/waves.csv  (wave_id | effective_date | n_funds | is_anchor)
        p1/t2_wrds/waves_members.csv  (wave_id | fund_name | source_accession ...)
        p1/t2_wrds/build_waves.log
"""
import csv
import logging
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
HERE = ROOT / "p1" / "t2_wrds"
EVENTS = ROOT / "p1" / "events_merged.csv"
WAVES = HERE / "waves.csv"
MEMBERS = HERE / "waves_members.csv"
ANCHOR = "2021-06-11"  # DFA six-fund conversion — anchor wave
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

HERE.mkdir(parents=True, exist_ok=True)
log = logging.getLogger("build_waves")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout),
              logging.FileHandler(HERE / "build_waves.log", mode="w")])


def main():
    if not EVENTS.exists():
        log.error("MISSING input %s — run T1 first", EVENTS)
        sys.exit(2)
    with open(EVENTS, newline="") as f:
        rows = list(csv.DictReader(f))
    log.info("read %d rows from %s", len(rows), EVENTS.name)

    dated, held = [], []
    for r in rows:
        eff = (r.get("effective_date") or "").strip()
        if ISO.match(eff):
            dated.append(r)
        else:
            held.append(r)
            log.debug("HELD (no ISO date): %s eff=%r approx=%r",
                      r.get("fund_name"), eff, r.get("effective_date_approx"))
    log.info("%d rows with ISO effective_date, %d held-back excluded",
             len(dated), len(held))

    # group by effective_date -> wave
    waves = {}
    for r in dated:
        waves.setdefault(r["effective_date"], []).append(r)
    log.info("%d distinct waves", len(waves))

    # deterministic wave_id: W<seq> ordered by date; keep date in the row too
    ordered = sorted(waves)
    wid = {d: "W{:03d}".format(i + 1) for i, d in enumerate(ordered)}
    if ANCHOR not in waves:
        log.warning("ANCHOR date %s not present as a wave — check T1 coverage",
                    ANCHOR)
    else:
        log.info("anchor wave %s = %s (%d funds)",
                 ANCHOR, wid[ANCHOR], len(waves[ANCHOR]))

    with open(WAVES, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wave_id", "effective_date", "n_funds", "is_anchor"])
        for d in ordered:
            w.writerow([wid[d], d, len(waves[d]), int(d == ANCHOR)])

    with open(MEMBERS, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["wave_id", "effective_date", "fund_name", "family",
                    "mutual_fund_ticker", "etf_ticker", "source_accession",
                    "source_url"])
        for d in ordered:
            for r in waves[d]:
                w.writerow([wid[d], d, r.get("fund_name", ""),
                            r.get("family", ""), r.get("mutual_fund_ticker", ""),
                            r.get("etf_ticker", ""), r.get("source_accession", ""),
                            r.get("source_url", "")])

    log.info("wrote %s (%d waves) and %s (%d members)",
             WAVES.name, len(ordered), MEMBERS.name, len(dated))
    # sanity asserts (Project_1.md §112)
    assert len(ordered) == len(set(ordered)), "duplicate wave dates"
    total_members = sum(len(v) for v in waves.values())
    assert total_members == len(dated), "member count mismatch"
    log.info("OK: waves=%d funds_in_waves=%d held_back=%d",
             len(ordered), total_members, len(held))
"""P1-T2 wave construction (deterministic, no WRDS). A 'wave' is the set of
conversions sharing one effective_date (Project_1.md §T2: 波次 = 同一生效日的一
组转换; DFA 2021-06-11 = 锚波次). Reads p1/events_merged.csv, assigns wave_id,
flags the DFA anchor, and lists each wave's converting funds — the input the WRDS
holdings pipeline needs to know which funds to pull holdings for per wave.

Output: p1/t2_wrds/waves.csv (wave_id, effective_date, n_conversions, is_anchor,
etf_tickers, source_accessions, fund_names). Deterministic + rerunnable.

Only conversions with a verbatim ISO effective_date enter a wave (the study key);
approximate-timing rows in events_merged stay out until their date resolves.
"""
import csv
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
EVENTS = HERE.parent / "events_merged.csv"
OUT = HERE / "waves.csv"
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ANCHOR_DATE = "2021-06-11"          # DFA — first MF->ETF conversions (spec anchor)


def main():
    rows = [r for r in csv.DictReader(EVENTS.open())
            if ISO.match(r.get("effective_date", ""))]
    waves = {}
    for r in rows:
        d = r["effective_date"]
        waves.setdefault(d, []).append(r)

    out = []
    for i, d in enumerate(sorted(waves), start=1):
        g = waves[d]
        out.append({
            "wave_id": f"W{i:03d}",
            "effective_date": d,
            "n_conversions": len(g),
            "is_anchor": "1" if d == ANCHOR_DATE else "0",
            "etf_tickers": "|".join(sorted({r["etf_ticker"] for r in g if r["etf_ticker"] not in ("NA", "")})),
            "source_accessions": "|".join(sorted({r["source_accession"] for r in g})),
            "fund_names": " || ".join(r["fund_name"] for r in g),
        })

    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["wave_id", "effective_date", "n_conversions",
                                           "is_anchor", "etf_tickers", "source_accessions", "fund_names"])
        w.writeheader()
        for r in out:
            w.writerow(r)

    anchor = [w for w in out if w["is_anchor"] == "1"]
    print(f"waves.csv: {len(out)} waves over {len(rows)} dated conversions "
          f"({len(rows) - len(waves)} share a date). "
          f"anchor {ANCHOR_DATE}: {'present, ' + str(anchor[0]['n_conversions']) + ' conversions' if anchor else 'ABSENT'}")


if __name__ == "__main__":
    main()
