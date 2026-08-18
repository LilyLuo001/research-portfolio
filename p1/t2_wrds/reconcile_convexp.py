#!/usr/bin/env python3
"""P1-T2 — reconcile the two independent ConvExp constructions.

The free EDGAR path (N-PORT holdings ÷ SEC-XBRL shares outstanding, CUSIP-keyed)
and the WRDS path (CRSP MF holdings ÷ CRSP shrout, permno-keyed) measure the SAME
quantity from disjoint sources. That makes them a dual-channel pair in the
portfolio's own idiom, and their agreement is the strongest validation either one
can get — stronger than any internal assertion, because the two share no code, no
vendor, and no failure mode.

**Why this file exists before the data does.** Agreement bands chosen after seeing
the numbers are not a check, they are a rationalisation. The classification below
is fixed as of this commit; git history is the timestamp. If a band is ever
changed, it is a disclosed deviation, not a tweak.

Two stages:

  --build-map   BOX/WRDS. One query against the security-names table to emit
                permno_cusip_map.csv (permno, ncusip). No licensed rows beyond an
                identifier bridge, which the data policy permits as a locator.

  (default)     OFFLINE. Joins the two parquets through that map and reports
                agreement. Runs anywhere, including a Claude Code session.

Outputs: reconciliation_report.md, reconciliation_cells.csv
"""
import argparse
import csv
import pathlib
import sys
from datetime import datetime, timezone

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from holdings_pipeline import SCHEMA, Recorder, connect, _inlist  # noqa: E402

FREE_PARQUET = HERE.parent / "conv_exposure_free.parquet"
WRDS_PARQUET = HERE.parent / "conv_exposure.parquet"
MAP_CSV = HERE / "permno_cusip_map.csv"
REPORT = HERE / "reconciliation_report.md"
CELLS = HERE / "reconciliation_cells.csv"

# ---- PRE-COMMITTED CLASSIFICATION (frozen before any number was seen) ------ #
# Relative gap = |free - wrds| / max(free, wrds). The bands are deliberately
# loose, because the two paths are NOT expected to agree exactly and pretending
# otherwise would manufacture alarm:
#   * different holdings snapshots (N-PORT monthly vs CRSP MF report dates),
#   * different shares-outstanding as-of dates,
#   * different fund coverage within a wave.
# What must agree is the ECONOMIC content: which stocks are treated, and how they
# rank. A cell inside AGREE_BAND is noise; ≥ INVESTIGATE_BAND is a finding.
AGREE_BAND = 0.01          # ≤1% relative gap: agreement
CLOSE_BAND = 0.10          # ≤10%: close, explainable by snapshot timing
INVESTIGATE_BAND = 0.10    # >10%: investigate before either number is used
TREATED_LINE = 0.005       # the 0.5% line the study actually keys on
# The pre-committed headline test: of cells computed by BOTH paths, the share that
# agree on the treated/not-treated call. Anything below this is a red flag that
# must be explained before T5, not a knob to widen.
TREATED_AGREEMENT_FLOOR = 0.95


def normalize_cusip(c):
    """CRSP `ncusip` is the 8-character historical CUSIP; N-PORT carries the
    9-character CUSIP including its check digit. Comparing them raw silently
    matches nothing, which would read as 'the two paths share no stocks' — a
    conclusion produced entirely by a check digit."""
    c = (str(c or "").strip().upper())
    return c[:8] if len(c) >= 8 else ""


# --------------------------------------------------------------------------- #
# stage 1 — the identifier bridge (box)                                        #
# --------------------------------------------------------------------------- #
def sql_permno_cusip_map(permnos=None):
    s = SCHEMA["security_names"]
    preds = [f"{s['ncusip']} is not null"]
    if permnos:
        preds.append(f"{s['permno']} in ({_inlist(sorted(permnos))})")
    return (f"select distinct {s['permno']}, {s['ncusip']} "
            f"from {s['table']} where " + " and ".join(preds))


def build_map(db, permnos=None, path=MAP_CSV):
    """Emit permno -> ncusip. A security can carry several historical CUSIPs; all
    are kept, because the free path's CUSIP is whatever the fund reported at the
    time, not today's."""
    rec = db if isinstance(db, Recorder) else Recorder(db)
    s = SCHEMA["security_names"]
    df = rec.raw_sql(sql_permno_cusip_map(permnos), label="permno_cusip_map")
    rows = [{"permno": int(getattr(r, s["permno"])),
             "ncusip": normalize_cusip(getattr(r, s["ncusip"]))}
            for r in df.itertuples()]
    rows = [r for r in rows if r["ncusip"]]
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["permno", "ncusip"])
        w.writeheader()
        w.writerows(rows)
    return rows, rec


# --------------------------------------------------------------------------- #
# stage 2 — the comparison (offline)                                           #
# --------------------------------------------------------------------------- #
def classify(free, wrds):
    if free is None or wrds is None:
        return "one_sided"
    hi = max(abs(free), abs(wrds))
    if hi == 0:
        return "agree"
    gap = abs(free - wrds) / hi
    if gap <= AGREE_BAND:
        return "agree"
    if gap <= CLOSE_BAND:
        return "close"
    return "investigate"


def reconcile(free_rows, wrds_rows, permno_cusip):
    """free_rows: (cusip, wave_id, conv_exp) · wrds_rows: (permno, wave_id, conv_exp)."""
    by_permno = {}
    for permno, ncusip in permno_cusip:
        by_permno.setdefault(int(permno), set()).add(normalize_cusip(ncusip))

    free_by = {(normalize_cusip(r["cusip"]), r["wave_id"]): float(r["conv_exp"])
               for r in free_rows if normalize_cusip(r["cusip"])}
    used = set()
    cells = []
    for r in wrds_rows:
        permno, wave = int(r["permno"]), r["wave_id"]
        w = float(r["conv_exp"])
        hit_key = None
        for cu in sorted(by_permno.get(permno, ())):
            if (cu, wave) in free_by:
                hit_key = (cu, wave)
                break
        f = free_by.get(hit_key) if hit_key else None
        if hit_key:
            used.add(hit_key)
        cells.append({"permno": permno, "cusip": hit_key[0] if hit_key else "",
                      "wave_id": wave, "conv_exp_free": "" if f is None else f,
                      "conv_exp_wrds": w,
                      "status": classify(f, w) if f is not None else "wrds_only",
                      "treated_free": "" if f is None else int(f >= TREATED_LINE),
                      "treated_wrds": int(w >= TREATED_LINE)})
    for (cu, wave), f in sorted(free_by.items()):
        if (cu, wave) not in used:
            cells.append({"permno": "", "cusip": cu, "wave_id": wave,
                          "conv_exp_free": f, "conv_exp_wrds": "",
                          "status": "free_only", "treated_free": int(f >= TREATED_LINE),
                          "treated_wrds": ""})
    return cells


def summarize(cells):
    both = [c for c in cells if c["status"] in ("agree", "close", "investigate")]
    by_status = {}
    for c in cells:
        by_status[c["status"]] = by_status.get(c["status"], 0) + 1
    agree_treated = sum(1 for c in both if c["treated_free"] == c["treated_wrds"])
    share = (agree_treated / len(both)) if both else None
    return {
        "cells_total": len(cells),
        "cells_both_paths": len(both),
        "by_status": dict(sorted(by_status.items())),
        "treated_call_agreement": None if share is None else round(share, 4),
        "treated_floor": TREATED_AGREEMENT_FLOOR,
        "verdict": ("NO_OVERLAP" if not both else
                    "PASS" if share >= TREATED_AGREEMENT_FLOOR else "FLAG"),
    }


def write_report(cells, summary, report=REPORT, cells_csv=CELLS):
    fields = ["permno", "cusip", "wave_id", "conv_exp_free", "conv_exp_wrds",
              "status", "treated_free", "treated_wrds"]
    with cells_csv.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(cells)

    L = ["# ConvExp reconciliation — free EDGAR path vs WRDS/CRSP path", "",
         f"generated: {datetime.now(timezone.utc).isoformat()}", "",
         "Two independent constructions of the same quantity, sharing no code, no",
         "vendor and no failure mode. Bands were fixed before any number existed",
         f"(agree ≤{AGREE_BAND:.0%}, close ≤{CLOSE_BAND:.0%}, investigate above);",
         "changing one now is a disclosed deviation, not a tweak.", "",
         f"- cells compared: **{summary['cells_total']}**",
         f"- computed by both paths: **{summary['cells_both_paths']}**",
         f"- agreement on the treated call (ConvExp ≥ {TREATED_LINE:.1%}): "
         f"**{summary['treated_call_agreement']}** "
         f"(pre-committed floor {summary['treated_floor']})",
         f"- **verdict: {summary['verdict']}**", "",
         "## by status", "", "| status | cells |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in summary["by_status"].items()]
    L += ["", "`free_only` / `wrds_only` are coverage differences, not "
              "disagreements — the paths drop different things for different "
              "reasons, and that asymmetry is itself the interesting output.",
          "", "Per-cell detail: `reconciliation_cells.csv`."]
    report.write_text("\n".join(L) + "\n")


def _read_rows(parquet, columns):
    import pandas as pd
    df = pd.read_parquet(parquet)
    return df[columns].to_dict("records")


def main(argv=None):
    ap = argparse.ArgumentParser(description="reconcile free vs WRDS ConvExp")
    ap.add_argument("--build-map", action="store_true",
                    help="BOX/WRDS: emit permno_cusip_map.csv, then stop")
    a = ap.parse_args(argv)

    if a.build_map:
        rows, _ = build_map(connect())
        print(f"permno_cusip_map.csv: {len(rows)} identifier pairs")
        return 0

    for p in (FREE_PARQUET, WRDS_PARQUET, MAP_CSV):
        if not p.exists():
            sys.exit(f"NEED_INPUT: {p} does not exist yet — reconciliation needs "
                     "both ConvExp builds and the identifier map (--build-map).")
    free_rows = _read_rows(FREE_PARQUET, ["cusip", "wave_id", "conv_exp"])
    wrds_rows = _read_rows(WRDS_PARQUET, ["permno", "wave_id", "conv_exp"])
    pmap = [(r["permno"], r["ncusip"]) for r in csv.DictReader(MAP_CSV.open())]

    cells = reconcile(free_rows, wrds_rows, pmap)
    summary = summarize(cells)
    write_report(cells, summary)
    print(f"reconciliation: {summary['verdict']} — {summary['cells_both_paths']} "
          f"cells on both paths, treated-call agreement "
          f"{summary['treated_call_agreement']} -> {REPORT.name}")
    return 0 if summary["verdict"] != "FLAG" else 1


if __name__ == "__main__":
    sys.exit(main())
