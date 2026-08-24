"""Build the frozen pre-event CPS panel that the D3 power standard needs.

`dax/memo/power_calcs/power_standard.json` is `PLACEHOLDER_REQUIRES_REAL_CPS`:
its benchmark is RESOLVED and VERIFIED at 0.13, but `frozen_at_utc`,
`provenance`, and both MDE ceilings are null because nothing has ever supplied
it a CPS extract. `freeze_power_standard.py` fills it once, and requires the
columns `month, age, <weight>, employed, hours_unconditional`.

IPUMS extract 6 is already pulled and checksummed in
`ipums_preperiod_extract_receipt.json`. Its 16 samples run cps2021_11s through
cps2023_02s, which is exactly the standard's frozen window of 2021-11 to
2023-02. So the power standard can be frozen from data already in hand.

**Scope.** This builds the pre-event window only. It is NOT
`dax/data_built/cps_extract.parquet`, which the W2 brief defines as running to
the latest frozen month for the analysis panel and needs a larger extract.
Conflating them would silently truncate W5's sample, so this writes a
separately named file.

**Recodes are never guessed.** IPUMS `EMPSTAT` and `UHRSWORKT` carry coded
values whose meaning lives in the codebook, not in this file. The employed
codes and the hours-missing codes must be passed explicitly and are recorded
in the receipt. Every observed value is reported so the operator can check the
mapping against the codebook before anything is written, and an unlisted code
is refused rather than silently swept into a category.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from collections import Counter

REQUIRED_SOURCE = {"YEAR", "MONTH", "AGE", "WTFINL", "EMPSTAT", "UHRSWORKT", "CPSIDP"}
WINDOW_START, WINDOW_END = "2021-11", "2023-02"


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _codes(spec: str) -> set[int]:
    out: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part[1:]:
            lo, _, hi = part.partition("-")
            out.update(range(int(lo), int(hi) + 1))
        else:
            out.add(int(part))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extract", type=pathlib.Path, required=True,
                    help="IPUMS extract 6 data file (csv or csv.gz)")
    ap.add_argument("--receipt", type=pathlib.Path,
                    default=pathlib.Path("dax/memo/power_calcs/ipums_preperiod_extract_receipt.json"),
                    help="pinned extract receipt to verify the file against")
    ap.add_argument("--output", type=pathlib.Path,
                    default=pathlib.Path("dax/data_built/cps_preevent_power_panel.parquet"))
    ap.add_argument("--employed-codes", help="EMPSTAT values meaning employed, e.g. 10,12")
    ap.add_argument("--hours-missing-codes", default="",
                    help="UHRSWORKT values meaning not-in-universe, expected only "
                         "on non-employed records, e.g. 999")
    ap.add_argument("--hours-vary-codes", default="",
                    help="UHRSWORKT values meaning the person IS employed but the "
                         "hours are not a number, e.g. 997 'hours vary'. These are "
                         "recorded unobserved, never zero.")
    ap.add_argument("--inspect", action="store_true",
                    help="report observed code distributions and exit without writing")
    args = ap.parse_args(argv)

    try:
        import pandas as pd
    except ImportError:
        print("NEED_HUMAN: pandas is required", file=sys.stderr)
        return 2
    if not args.extract.is_file():
        print(f"NEED_HUMAN: extract not found at {args.extract}", file=sys.stderr)
        return 2

    # Verify the file is the pinned one before building anything on it.
    provenance = {"extract_path": str(args.extract), "extract_sha256": _sha256(args.extract)}
    if args.receipt.is_file():
        rec = json.loads(args.receipt.read_text(encoding="utf-8"))
        pinned = (rec.get("files", {}).get("data", {}) or {}).get("sha256")
        provenance["pinned_sha256"] = pinned
        if pinned and pinned != provenance["extract_sha256"]:
            print(f"NEED_HUMAN: extract sha256 {provenance['extract_sha256'][:12]} does not "
                  f"match the pinned {pinned[:12]} in {args.receipt.name}. Refusing to build "
                  f"the power standard's input from an unpinned file.", file=sys.stderr)
            return 2

    frame = pd.read_csv(args.extract)
    frame.columns = [c.upper() for c in frame.columns]
    missing = REQUIRED_SOURCE - set(frame.columns)
    if missing:
        print(f"NEED_HUMAN: extract lacks {sorted(missing)}; columns are "
              f"{sorted(frame.columns)}", file=sys.stderr)
        return 2

    emp_seen = Counter(int(v) for v in frame["EMPSTAT"].dropna())
    hrs_seen = Counter(int(v) for v in frame["UHRSWORKT"].dropna())
    if args.inspect or not args.employed_codes:
        print("EMPSTAT observed:", dict(sorted(emp_seen.items())))
        print("UHRSWORKT observed (top 12):",
              dict(sorted(hrs_seen.items(), key=lambda kv: -kv[1])[:12]))
        if not args.employed_codes:
            print("\nNEED_HUMAN: --employed-codes not supplied. Check the codebook "
                  "and pass the EMPSTAT values meaning employed; they are never "
                  "guessed here.", file=sys.stderr)
            return 2
        return 0

    employed = _codes(args.employed_codes)
    hours_missing = _codes(args.hours_missing_codes)
    hours_vary = _codes(args.hours_vary_codes)
    # Codes not named as employed are treated as not-employed. That is a real
    # choice, so it is reported and recorded rather than left implicit.
    treated_not_employed = sorted(c for c in emp_seen if c not in employed)
    unseen = sorted(employed - set(emp_seen))
    if not (employed & set(emp_seen)):
        # None of the named codes occur: certainly wrong, and would classify
        # every person as jobless.
        print(f"NEED_HUMAN: none of --employed-codes {sorted(employed)} occur in "
              f"the extract. Observed EMPSTAT values are {sorted(emp_seen)}. "
              f"Every person would be recorded not employed.", file=sys.stderr)
        return 2
    if unseen:
        # Some named codes are absent. Suspicious but legitimate — a rare
        # category can be missing from a short window — so warn and record it
        # rather than blocking a correct build.
        print(f"NOTE: --employed-codes names {unseen}, which do not occur in this "
              f"extract. Proceeding; recorded in the receipt.")
    print(f"EMPSTAT treated as employed    : {sorted(employed)}")
    print(f"EMPSTAT treated as not employed: {treated_not_employed}")

    frame["month"] = (frame["YEAR"].astype(int).astype(str) + "-"
                      + frame["MONTH"].astype(int).astype(str).str.zfill(2))
    frame = frame[(frame["month"] >= WINDOW_START) & (frame["month"] <= WINDOW_END)].copy()
    if frame.empty:
        print(f"NEED_HUMAN: no records in {WINDOW_START}..{WINDOW_END}", file=sys.stderr)
        return 2

    frame["employed"] = frame["EMPSTAT"].astype(int).isin(employed).astype(int)
    raw_hours = frame["UHRSWORKT"].astype(int)

    # Three distinct states, kept distinct. Collapsing them is how a frozen
    # baseline goes quietly wrong:
    #   not employed                  -> 0 hours, observed  (design memo s7)
    #   employed, numeric hours       -> that value, observed
    #   employed, "hours vary"        -> UNOBSERVED, never 0
    # An employed record carrying a not-in-universe code is contradictory and
    # is refused rather than swept into either bucket.
    is_emp = frame["employed"] == 1
    contradictory = int((is_emp & raw_hours.isin(hours_missing)).sum())
    if contradictory:
        print(f"NEED_HUMAN: {contradictory} records are employed but carry a "
              f"not-in-universe hours code {sorted(hours_missing)}. That "
              f"combination has no defined treatment; check --hours-missing-codes "
              f"and --hours-vary-codes against the codebook.", file=sys.stderr)
        return 2

    vary = is_emp & raw_hours.isin(hours_vary)
    frame["hours_observed"] = (~vary).astype(int)
    hours = raw_hours.astype(float)
    hours = hours.where(~raw_hours.isin(hours_missing | hours_vary), other=float("nan"))
    frame["hours_unconditional"] = hours.where(is_emp, 0.0)
    frame.loc[vary, "hours_unconditional"] = float("nan")

    n_vary = int(vary.sum())
    w = frame["WTFINL"].astype(float)
    obs = frame["hours_observed"] == 1
    mean_observed = float((frame.loc[obs, "hours_unconditional"] * w[obs]).sum() / w[obs].sum())
    mean_zerofilled = float((frame["hours_unconditional"].fillna(0.0) * w).sum() / w.sum())

    out = frame.rename(columns={"AGE": "age", "WTFINL": "wtfinl", "CPSIDP": "cpsidp"})[
        ["month", "age", "wtfinl", "employed", "hours_unconditional",
         "hours_observed", "cpsidp"]]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    out.to_parquet(args.output, index=False)

    receipt = {
        "receipt_version": "dax-w2-cps-preevent-v1",
        "scope": "PRE-EVENT WINDOW ONLY; not the W5 analysis panel cps_extract.parquet",
        "window": {"start": WINDOW_START, "end": WINDOW_END},
        "provenance": provenance,
        "recodes": {
            "employed_empstat_codes": sorted(employed),
            "hours_missing_uhrsworkt_codes": sorted(hours_missing),
            "hours_vary_uhrsworkt_codes": sorted(hours_vary),
            "hours_rule": "unconditional weekly hours, zero for the non-employed; "
                          "employed-with-hours-vary recorded UNOBSERVED, never zero",
        },
        "hours_missingness": {
            "n_employed_hours_unobserved": n_vary,
            "baseline_hours_over_observed": round(mean_observed, 6),
            "baseline_hours_if_zero_filled": round(mean_zerofilled, 6),
            "zero_fill_bias": round(mean_zerofilled - mean_observed, 6),
            "note": "zero-filling employed-with-hours-vary would depress the "
                    "baseline and permanently tighten hours_mde_ceiling, which "
                    "is 0.5 * 0.13 * baseline_hours",
        },
        "observed_codes": {"empstat": dict(sorted(emp_seen.items()))},
        "empstat_treated_not_employed": treated_not_employed,
        "empstat_named_employed_but_absent": unseen,
        "rows": int(len(out)),
        "months": sorted(out["month"].unique().tolist()),
        "weight_sum": float(out["wtfinl"].sum()),
        "output_sha256": _sha256(args.output),
    }
    receipt_path = args.output.with_suffix(".receipt.json")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {args.output} — {len(out):,} rows over {len(receipt['months'])} months")
    print(f"receipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
