#!/usr/bin/env python3
"""
apply_asset_class.py — merge the box's filled classifications back into
events_merged.csv, safely.

Safety properties, all enforced (this file edits the project's foundational
event set, so it refuses rather than guesses):

  1. ONLY fills rows whose asset_class is currently blank. An existing value is
     never overwritten — if the filled file disagrees with a classified row, that
     is an error, not an update.
  2. Every filled row must carry BOTH a class and a verbatim evidence quote.
     A class without evidence is a guess (meta-rule 1) and is rejected.
  3. The class must be one of the four frozen values (docs/Project_1.md §90).
  4. Row count, column order and every other cell must be unchanged.
  5. Blank fills are legal and are simply skipped — partial completion is fine.

Usage:
  python p1/t1_reconcile/apply_asset_class.py <filled.csv> [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[2]
EVENTS = REPO / "p1" / "events_merged.csv"
VALID = {"equity_US", "equity_intl", "fixed_income", "other"}
KEY = ["fund_name", "effective_date", "source_accession"]


def _text(col: pd.Series) -> pd.Series:
    """A column the box left entirely blank reads back as float64 NaN, where the
    .str accessor raises. Normalise to stripped strings before any text test."""
    return col.astype("string").fillna("").str.strip()


def validate(filled: pd.DataFrame, events: pd.DataFrame) -> list[str]:
    errs: list[str] = []
    for c in KEY + ["asset_class_FILL", "evidence_quote_FILL"]:
        if c not in filled.columns:
            errs.append(f"filled file missing required column: {c}")
    if errs:
        return errs

    # Normalise BOTH columns up front. `nan or ""` evaluates to nan, which is
    # truthy — testing the raw cell would silently accept a missing quote.
    cls_txt = _text(filled["asset_class_FILL"])
    ev_txt = _text(filled["evidence_quote_FILL"])
    has_class = cls_txt != ""
    for i in filled.index[has_class]:
        cls = cls_txt[i]
        who = f"{filled.at[i, 'fund_name']} @ {filled.at[i, 'source_accession']}"
        if cls not in VALID:
            errs.append(f"{who}: '{cls}' is not one of {sorted(VALID)}")
        if ev_txt[i] == "":
            errs.append(f"{who}: class given with no evidence quote — "
                        "meta-rule 1 requires a locator-backed quote")

    # never overwrite an existing classification
    cur = events.set_index(KEY)["asset_class"]
    for r in filled[has_class].itertuples():
        k = (r.fund_name, r.effective_date, r.source_accession)
        if k not in cur.index:
            errs.append(f"{k}: no matching row in events_merged.csv")
        elif pd.notna(cur.loc[k]):
            errs.append(f"{k}: already classified as '{cur.loc[k]}' — "
                        "refusing to overwrite")
    return errs


def apply(filled_path: Path, dry_run: bool = False) -> int:
    events = pd.read_csv(EVENTS)
    filled = pd.read_csv(filled_path)

    errs = validate(filled, events)
    if errs:
        print(f"REFUSED — {len(errs)} problem(s):", file=sys.stderr)
        for e in errs[:30]:
            print(f"  - {e}", file=sys.stderr)
        return 1

    before_rows, before_cols = len(events), list(events.columns)
    blank_before = int(events["asset_class"].isna().sum())

    has_class = _text(filled["asset_class_FILL"]) != ""
    upd = _text(filled.loc[has_class, "asset_class_FILL"])
    upd.index = pd.MultiIndex.from_frame(filled.loc[has_class, KEY])
    idx = events.set_index(KEY).index
    mapped = pd.Series(idx.map(upd), index=events.index)
    events["asset_class"] = events["asset_class"].fillna(mapped)

    assert len(events) == before_rows, "row count changed"
    assert list(events.columns) == before_cols, "column set changed"
    blank_after = int(events["asset_class"].isna().sum())

    print(f"classified {blank_before - blank_after} event(s); "
          f"{blank_after} still blank of {before_rows}")
    if dry_run:
        print("dry run — events_merged.csv not written")
        return 0
    events.to_csv(EVENTS, index=False)
    print(f"wrote {EVENTS}")
    print("now re-run: python p1/t1_reconcile/sample_scenarios.py "
          "(numbers must be IDENTICAL)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("filled", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not a.filled.exists():
        print(f"no such file: {a.filled}", file=sys.stderr)
        return 2
    return apply(a.filled, a.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
