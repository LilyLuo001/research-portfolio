"""Build the W5 analysis panel from IPUMS extract 7.

Distinct from `build_cps_preevent.py`, which is scoped to the frozen
2021-11..2023-02 power window and must not be reused: its window restriction
and its narrower recode set are both wrong for a panel running to 2026-07.

Written against a read inventory of extract 7 rather than against the pre-event
builder's assumptions. Three findings from that inventory drive the design.

**EMPSTAT carries eight codes, not two.** 1 (armed forces, arriving as "1" not
"01"), 10, 12, 21, 22, 32, 34, 36. `{10, 12}` describes what the pre-event
builder *retained as employed*, not what the data holds. A builder that
filtered to it would drop 41.5% of rows -- the unemployed, those not in the
labour force, and the armed forces -- which for an employment-rate outcome
would silently delete the entire denominator. Nothing is filtered here: every
row is retained and employment is flagged.

**UHRSWORKT mixes sentinels with a real zero.** 999 is not-in-universe and 997
is "hours vary", but genuine values span 0 to 172, and a real 0 is an employed
person who worked no hours that week. Treating 0 as missing would be as wrong
as treating 997 as zero.

**One calendar month is absent from the source.** There is no `cps2025_10`
sample. The panel covers 57 calendar months from 2021-11 to 2026-07 in 56
samples. Any lag, difference or event-window built by treating consecutive rows
as consecutive months silently spans that gap and produces a two-month step
labelled as one. The panel therefore carries an absolute
`calendar_month_index` and a `prev_month_present` flag, so the hazard lives in
the data rather than only in a receipt someone may not read.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import pathlib
import sys
from collections import Counter

REQUIRED_SOURCE = {"YEAR", "MONTH", "AGE", "WTFINL", "EMPSTAT", "UHRSWORKT",
                   "CPSIDP", "OCC2010"}
EPOCH_YEAR = 2000


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _codes(spec: str) -> set[int]:
    out: set[int] = set()
    for part in (p.strip() for p in spec.split(",")):
        if not part:
            continue
        if "-" in part[1:]:
            lo, _, hi = part.partition("-")
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    return out


def month_index(month: str) -> int:
    """Absolute months since EPOCH_YEAR-01, so a gap shows as an index jump."""
    y, m = month.split("-")
    return (int(y) - EPOCH_YEAR) * 12 + int(m) - 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extract", type=pathlib.Path, required=True,
                    help="IPUMS extract 7 data file (.csv or .csv.gz)")
    ap.add_argument("--receipt", type=pathlib.Path,
                    default=pathlib.Path("dax/memo/power_calcs/ipums_analysis_extract_receipt.json"))
    ap.add_argument("--output", type=pathlib.Path,
                    default=pathlib.Path("dax/data_built/cps_extract.parquet"))
    ap.add_argument("--employed-codes", required=True,
                    help="EMPSTAT values meaning employed; never guessed")
    ap.add_argument("--hours-missing-codes", default="999")
    ap.add_argument("--hours-vary-codes", default="997")
    args = ap.parse_args(argv)

    try:
        import pandas as pd
    except ImportError:
        print("NEED_HUMAN: pandas is required", file=sys.stderr)
        return 2
    if not args.extract.is_file():
        print(f"NEED_HUMAN: extract not found at {args.extract}", file=sys.stderr)
        return 2

    provenance = {"extract_path": str(args.extract),
                  "extract_sha256": _sha256(args.extract)}
    if args.receipt.is_file():
        rec = json.loads(args.receipt.read_text(encoding="utf-8"))
        pinned = (rec.get("files", {}).get("data", {}) or {}).get("sha256")
        provenance["pinned_sha256"] = pinned
        if pinned and pinned != provenance["extract_sha256"]:
            print(f"NEED_HUMAN: extract sha256 {provenance['extract_sha256'][:12]} "
                  f"does not match the pinned {pinned[:12]}", file=sys.stderr)
            return 2

    opener = gzip.open if args.extract.suffix == ".gz" else open
    with opener(args.extract, "rt") as fh:
        frame = pd.read_csv(fh)
    frame.columns = [c.upper() for c in frame.columns]
    missing = REQUIRED_SOURCE - set(frame.columns)
    if missing:
        print(f"NEED_HUMAN: extract lacks {sorted(missing)}; columns are "
              f"{sorted(frame.columns)}", file=sys.stderr)
        return 2

    # ASEC rows would carry different weights and a different universe.
    asec_rows = 0
    if "ASECFLAG" in frame.columns:
        asec_rows = int((frame["ASECFLAG"].fillna(0).astype(float) == 1).sum())
        if asec_rows:
            print(f"NEED_HUMAN: {asec_rows} ASEC rows present. The basic monthly "
                  f"universe and weights differ; mixing them is not a filter "
                  f"decision this builder makes.", file=sys.stderr)
            return 2

    employed = _codes(args.employed_codes)
    hours_missing = _codes(args.hours_missing_codes)
    hours_vary = _codes(args.hours_vary_codes)
    emp_seen = Counter(int(v) for v in frame["EMPSTAT"].dropna())
    if not (employed & set(emp_seen)):
        print(f"NEED_HUMAN: none of --employed-codes {sorted(employed)} occur. "
              f"Observed EMPSTAT: {sorted(emp_seen)}", file=sys.stderr)
        return 2

    frame["month"] = (frame["YEAR"].astype(int).astype(str) + "-"
                      + frame["MONTH"].astype(int).astype(str).str.zfill(2))
    is_emp = frame["EMPSTAT"].astype(int).isin(employed)
    frame["employed"] = is_emp.astype(int)

    raw_hours = frame["UHRSWORKT"].astype(int)
    contradictory = int((is_emp & raw_hours.isin(hours_missing)).sum())
    if contradictory:
        print(f"NEED_HUMAN: {contradictory} employed rows carry a "
              f"not-in-universe hours code {sorted(hours_missing)}",
              file=sys.stderr)
        return 2
    vary = is_emp & raw_hours.isin(hours_vary)
    frame["hours_observed"] = (~vary).astype(int)
    hours = raw_hours.astype(float).where(
        ~raw_hours.isin(hours_missing | hours_vary), other=float("nan"))
    frame["hours_unconditional"] = hours.where(is_emp, 0.0)
    frame.loc[vary, "hours_unconditional"] = float("nan")

    # --- the calendar gap, made structural rather than documentary
    months = sorted(frame["month"].unique())
    frame["calendar_month_index"] = frame["month"].map(month_index)
    present = {month_index(m) for m in months}
    gaps = [i for i in range(min(present), max(present) + 1) if i not in present]
    frame["prev_month_present"] = frame["calendar_month_index"].map(
        lambda i: int((i - 1) in present))

    def _label(i: int) -> str:
        return f"{EPOCH_YEAR + i // 12}-{i % 12 + 1:02d}"

    out_cols = ["month", "calendar_month_index", "prev_month_present", "age",
                "wtfinl", "employed", "hours_unconditional", "hours_observed",
                "cpsidp", "occ2010"]
    out = frame.rename(columns={"AGE": "age", "WTFINL": "wtfinl",
                                "CPSIDP": "cpsidp", "OCC2010": "occ2010"})
    for extra in ("MISH", "SEX", "RACE", "HISPAN", "EDUC", "IND1990"):
        if extra in out.columns:
            out = out.rename(columns={extra: extra.lower()})
            out_cols.append(extra.lower())
    out = out[out_cols]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.output, index=False)

    receipt = {
        "receipt_version": "dax-w2-cps-analysis-panel-v1",
        "scope": "W5 ANALYSIS PANEL. Not the pre-event power panel, which is "
                 "frozen at 2021-11..2023-02 and feeds power_standard.json.",
        "provenance": provenance,
        "rows": int(len(out)),
        "months_present": len(months),
        "month_first": months[0], "month_last": months[-1],
        "calendar_months_spanned": max(present) - min(present) + 1,
        "missing_months": [_label(i) for i in gaps],
        "missing_month_rule": (
            "these calendar months have no CPS sample. calendar_month_index is "
            "absolute and prev_month_present flags rows whose preceding month "
            "is absent, so a lag or difference must filter on it. Treating "
            "consecutive ROWS as consecutive months produces a multi-month step "
            "labelled as one."),
        "recodes": {
            "employed_empstat_codes": sorted(employed),
            "empstat_treated_not_employed": sorted(c for c in emp_seen
                                                   if c not in employed),
            "hours_missing_uhrsworkt_codes": sorted(hours_missing),
            "hours_vary_uhrsworkt_codes": sorted(hours_vary),
            "hours_rule": "unconditional weekly hours, zero for the non-employed; "
                          "employed-with-hours-vary UNOBSERVED, never zero; a "
                          "genuine 0 is a real value and is retained",
        },
        "observed_empstat": dict(sorted(emp_seen.items())),
        "n_employed_hours_unobserved": int(vary.sum()),
        "asec_rows": asec_rows,
        "output_sha256": _sha256(args.output),
    }
    args.output.with_suffix(".receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output} — {len(out):,} rows, {len(months)} months "
          f"{months[0]}..{months[-1]}")
    if gaps:
        print(f"  MISSING MONTHS: {[_label(i) for i in gaps]} — "
              f"prev_month_present flags the affected rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
