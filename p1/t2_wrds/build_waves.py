#!/usr/bin/env python3
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
