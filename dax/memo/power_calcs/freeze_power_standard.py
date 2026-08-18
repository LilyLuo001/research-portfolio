"""Freeze the D3 power standard once, from the frozen pre-event CPS extract.

The constant this writes is the pass bar for the whole power analysis. It is
computed from a single fixed window that ends before the first eligible event,
pooled across occupations, so it depends on neither the dose definition nor the
event set — that independence is the entire point of D3.

Run once, on a host that has the real extract:

    python dax/memo/power_calcs/freeze_power_standard.py \
        --extract dax/data_built/cps_extract.parquet

It refuses to overwrite a frozen file without --force, so the bar cannot drift
as the analysis develops.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
STANDARD = HERE / "power_standard.json"


def sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def compute(extract: pathlib.Path, start_month: str, end_month: str,
            weight_column: str) -> dict[str, object]:
    """Person-weighted employment rate and mean unconditional hours, ages 22-25."""
    import pandas as pd

    frame = pd.read_parquet(extract) if extract.suffix == ".parquet" else pd.read_csv(extract)
    required = {"month", "age", weight_column, "employed", "hours_unconditional"}
    missing = required - set(frame.columns)
    if missing:
        raise SystemExit(
            f"NEED_HUMAN: extract lacks required columns {sorted(missing)}. "
            "The frozen standard cannot be computed from an extract that does "
            "not carry age, month, person weight, an employment indicator, and "
            "zero-coded unconditional hours."
        )

    window = frame[
        (frame["month"].astype(str).str[:7] >= start_month)
        & (frame["month"].astype(str).str[:7] <= end_month)
        & (frame["age"].between(22, 25))
    ]
    if window.empty:
        raise SystemExit("NEED_HUMAN: no person records in the frozen window")

    weights = window[weight_column].astype(float)
    total = float(weights.sum())
    if total <= 0:
        raise SystemExit("NEED_HUMAN: person weights sum to zero in the frozen window")

    return {
        "n_person_records": int(len(window)),
        "baseline_employment_rate_22_25": float(
            (window["employed"].astype(float) * weights).sum() / total),
        "baseline_hours_unconditional_22_25": float(
            (window["hours_unconditional"].astype(float) * weights).sum() / total),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract", type=pathlib.Path, required=True)
    parser.add_argument("--weight-column", default="wtfinl")
    parser.add_argument("--force", action="store_true",
                        help="overwrite an already-frozen standard (requires a "
                             "dated deviation memo under memo section 11)")
    args = parser.parse_args()

    standard = json.loads(STANDARD.read_text(encoding="utf-8"))
    if standard["status"] == "FROZEN" and not args.force:
        print("standard is already FROZEN — refusing to recompute.", file=sys.stderr)
        print("Recomputing after the analysis has developed is exactly what D3 "
              "forbids. If this is a legitimate re-freeze, file the deviation "
              "memo first and pass --force.", file=sys.stderr)
        return 1

    if not args.extract.is_file():
        raise SystemExit(f"NEED_HUMAN: extract not found at {args.extract}")

    window = standard["frozen_window"]
    measured = compute(args.extract, window["start_month"], window["end_month"],
                       args.weight_column)

    benchmark = standard["benchmark"]
    benchmark["baseline_employment_rate_22_25"] = round(
        measured["baseline_employment_rate_22_25"], 6)
    benchmark["baseline_hours_unconditional_22_25"] = round(
        measured["baseline_hours_unconditional_22_25"], 4)

    fraction = standard["standard"]["max_mde_fraction_of_benchmark"]
    decline = benchmark["relative_decline"]
    standard["standard"]["employment_mde_ceiling"] = round(
        fraction * decline * benchmark["baseline_employment_rate_22_25"], 8)
    standard["standard"]["hours_mde_ceiling"] = round(
        fraction * decline * benchmark["baseline_hours_unconditional_22_25"], 6)

    standard["provenance"] = {
        "cps_extract_path": str(args.extract),
        "cps_extract_sha256": sha256(args.extract),
        "n_person_records": measured["n_person_records"],
        "weight_variable": args.weight_column,
    }
    standard["status"] = "FROZEN"
    standard["frozen_at_utc"] = dt.datetime.now(dt.timezone.utc).isoformat()

    STANDARD.write_text(json.dumps(standard, indent=2) + "\n", encoding="utf-8")
    print(f"FROZEN — employment ceiling {standard['standard']['employment_mde_ceiling']}, "
          f"hours ceiling {standard['standard']['hours_mde_ceiling']}")
    print(f"from {measured['n_person_records']} person records in "
          f"{window['start_month']}..{window['end_month']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
