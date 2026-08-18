#!/usr/bin/env python3
"""P1-T2 coverage-audit item 5 — SCOPE the international-sleeve decision.

The audit's last open item is a judgement call the owner has to make: does the
paper (a) define the sample as US-listed and document the international-equity
conversions as out of scope, or (b) scope a separate non-US analysis? Nothing
here makes that call. It attaches numbers to it, from committed artifacts only:

  p1/events_merged.csv                fund -> asset_class
  p1/t2_wrds/waves_members.csv        wave -> funds
  p1/conv_exposure_free.parquet       computed ConvExp cells

Output: international_sleeve_scoping.csv (+ stdout summary). Offline, no network.

The load-bearing subtlety this quantifies: ConvExp cells are aggregated per
(cusip, wave) ACROSS the funds converting in that wave, so a cell in a wave that
mixes a US fund with an international fund cannot be attributed to one of them
after the fact. "Drop the international funds" and "drop the international waves"
are therefore different operations, and the gap between them is exactly the
mixed-wave rows counted below.
"""
import json
import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[3]
HERE = pathlib.Path(__file__).resolve().parent
THRESHOLDS = [0.0025, 0.005, 0.01]
INTL = "equity_intl"


def wave_classes():
    events = pd.read_csv(ROOT / "p1" / "events_merged.csv", dtype=str).fillna("")
    members = pd.read_csv(ROOT / "p1" / "t2_wrds" / "waves_members.csv",
                          dtype=str).fillna("")
    ac = dict(zip(events["fund_name"], events["asset_class"]))
    rows = []
    for wid, g in members.groupby("wave_id"):
        classes = {ac.get(f, "") or "unclassified" for f in g["fund_name"]}
        has_intl = INTL in classes
        others = classes - {INTL}
        rows.append({
            "wave_id": wid,
            "effective_date": g["effective_date"].iloc[0],
            "n_funds": len(g),
            "asset_classes": "|".join(sorted(classes)),
            "wave_class": ("pure_intl" if has_intl and not others else
                           "mixed_intl" if has_intl else "no_intl"),
        })
    return pd.DataFrame(rows).sort_values("wave_id")


def counts(df, label):
    out = {"scope": label, "waves": df["wave_id"].nunique(), "cells": len(df),
           "distinct_stocks": df["cusip"].nunique()}
    for t in THRESHOLDS:
        out["stocks_ge_%gpct" % (t * 100)] = df.loc[df["conv_exp"] >= t, "cusip"].nunique()
    return out


def main():
    waves = wave_classes()
    cells = pd.read_parquet(ROOT / "p1" / "conv_exposure_free.parquet")
    cells = cells.merge(waves[["wave_id", "wave_class"]], on="wave_id", how="left")
    cells["wave_class"] = cells["wave_class"].fillna("unknown_wave")

    rows = [counts(cells, "ALL (as built)")]
    for wc in ("no_intl", "mixed_intl", "pure_intl", "unknown_wave"):
        sub = cells[cells["wave_class"] == wc]
        if len(sub):
            rows.append(counts(sub, "only " + wc))
    rows.append(counts(cells[cells["wave_class"] != "pure_intl"],
                       "OPTION A: drop pure-international waves"))
    rows.append(counts(cells[cells["wave_class"] == "no_intl"],
                       "OPTION A-strict: drop any wave touching international"))
    tab = pd.DataFrame(rows)
    tab.to_csv(HERE / "international_sleeve_scoping.csv", index=False)

    anchor = waves.loc[waves["effective_date"] == "2021-06-11", "wave_class"]
    power = json.loads((ROOT / "p1" / "t2a_power_results.json").read_text())

    print(tab.to_string(index=False))
    print("\nwave classes:", waves["wave_class"].value_counts().to_dict())
    print("anchor wave (2021-06-11) class:", list(anchor))
    print("mixed_intl waves (the un-splittable ones):",
          waves.loc[waves["wave_class"] == "mixed_intl", "wave_id"].tolist())
    print("power floor context: P1-T2a n_stocks =", power.get("n_stocks"))
    print("wrote", HERE / "international_sleeve_scoping.csv")


if __name__ == "__main__":
    main()
