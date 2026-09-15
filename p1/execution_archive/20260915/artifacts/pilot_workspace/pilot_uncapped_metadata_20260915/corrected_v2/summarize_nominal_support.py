#!/usr/bin/env python3
"""Aggregate source-clock PRE/POST support from the protected census output.

This does not reread either source.  It emits no row-level identifiers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


USECOLS = [
    "candidate_id", "wave_id", "provisional_tier", "event_side",
    "source_permno_mapping_status", "analyst_status", "overlap_status",
    "nominal_0930_1500_source_clock",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--protected", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--receipt", required=True)
    args = ap.parse_args()
    protected, out, receipt = map(Path, (args.protected, args.out, args.receipt))

    d = pd.read_csv(protected, usecols=USECOLS, dtype=str)
    d = d[d["candidate_id"].notna() & d["event_side"].isin(["PRE", "POST"])].copy()
    d["nominal"] = d["nominal_0930_1500_source_clock"].eq("True")
    d["cached_min2"] = d["analyst_status"].eq("EXISTING_EXACT_EVENT_MIN2")
    keys = ["wave_id", "provisional_tier", "source_permno_mapping_status", "overlap_status", "candidate_id"]
    # Keep exact overlap strata and add a non-overlapping all-status diagnostic.
    d_all = d.copy()
    d_all["overlap_status"] = "ALL_OVERLAP_STATUSES"
    d = pd.concat([d, d_all], ignore_index=True)
    rows = []
    for group, g in d.groupby(keys[:-1], dropna=False, sort=True):
        candidate_side = g.groupby(["candidate_id", "event_side"], sort=False).agg(
            any_nominal=("nominal", "any"),
            any_nominal_cached_min2=("cached_min2", lambda s: bool((s & g.loc[s.index, "nominal"]).any())),
        ).reset_index()
        wide = candidate_side.pivot(index="candidate_id", columns="event_side", values=["any_nominal", "any_nominal_cached_min2"]).fillna(False)
        for metric in ["any_nominal", "any_nominal_cached_min2"]:
            for side in ["PRE", "POST"]:
                if (metric, side) not in wide.columns:
                    wide[(metric, side)] = False
        rows.append(dict(zip(keys[:-1], group)) | {
            "candidate_ids_with_any_path_in_stratum": int(g["candidate_id"].nunique()),
            "stocks_with_nominal_pre_and_post_before_cached_min2": int((wide[("any_nominal", "PRE")] & wide[("any_nominal", "POST")]).sum()),
            "stocks_with_nominal_pre_and_post_cached_min2_both": int((wide[("any_nominal_cached_min2", "PRE")] & wide[("any_nominal_cached_min2", "POST")]).sum()),
            "clock_interpretation": "SOURCE_DISPLAY_CLOCK_ONLY_NOT_ET_OR_RTH",
            "support_interpretation": "DIAGNOSTIC_NOT_INFERENCE_CERTIFICATION",
        })
    result = pd.DataFrame(rows).sort_values(keys[:-1]).reset_index(drop=True)
    out.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out, index=False, lineterminator="\n")
    payload = {
        "status": "PASS",
        "input": "PROTECTED_CENSUS_OUTPUT_ONLY_NO_SOURCE_REREAD",
        "protected_input_sha256": sha256(protected),
        "output_sha256": sha256(out),
        "rows": int(len(result)),
        "row_level_identifiers_exported": False,
        "clock_certified_et_or_rth": False,
        "code_sha256": sha256(Path(__file__)),
    }
    receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
