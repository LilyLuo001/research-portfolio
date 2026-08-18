#!/usr/bin/env python3
"""Sample-scale audit of the refraction chapter's frozen P1 inputs.

Plan v2.1 §2/§4/§5 commit the chapter to "reuse events_merged.csv and
conv_exposure.parquet as-is" at a stated scale of "203 cumulative conversions
~$260B through 2025", US-equity only. This script recomputes that scale from
the files actually in the repo, so §9's Gate-0 lines can be re-read against
real treatment mass instead of the planning-time figure.

Scope discipline: this is a TREATMENT-SIDE count only. It is not Gate-0 (R3)
and cannot be — G2/G5 need beta-hat and L-hat, which come from the R2 panel
that does not exist yet. Nothing here touches an outcome variable, so it is
clean under the lookahead ban and runnable pre-prereg.

  python refraction/sample_scale_audit.py [--json refraction/sample_scale_audit.json]
"""
import argparse
import json
from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).resolve().parent / "frozen_config.yaml"
EVENTS = ROOT / "p1" / "events_merged.csv"
# Plan §4 names "conv_exposure.parquet"; the file P1 actually produced is the
# free-data channel build. Resolved here, and flagged in the audit output.
CONVEXP_CANDIDATES = [ROOT / "p1" / "conv_exposure.parquet",
                      ROOT / "p1" / "conv_exposure_free.parquet"]


def load_config():
    cfg = yaml.safe_load(CONFIG.read_text())
    s, g = cfg["sample"], cfg["gate0_thresholds"]
    return {
        "waves_start": s["waves_start"], "waves_end": s["waves_end"],
        "asset_class": s["asset_class"],
        "convexp_treated_min": g["convexp_treated_min"],
        "effective_cluster_warning_below":
            cfg["inference"]["effective_cluster_warning_below"],
    }


def audit_events(cfg):
    ev = pd.read_csv(EVENTS, dtype=str)
    eff = pd.to_datetime(ev["effective_date"], errors="coerce")
    in_window = eff.between(pd.Timestamp(cfg["waves_start"]),
                            pd.Timestamp(cfg["waves_end"]))
    is_eq = ev["asset_class"] == cfg["asset_class"]
    usable = ev[is_eq & in_window]
    aum = pd.to_numeric(ev.get("AUM_at_conversion_USD"), errors="coerce")
    return {
        "rows_total": int(len(ev)),
        "by_asset_class": {k: int(v) for k, v in
                           ev["asset_class"].value_counts().items()},
        "equity_US_total": int(is_eq.sum()),
        "equity_US_in_wave_window": int(len(usable)),
        "distinct_effective_dates_in_window": int(usable["effective_date"].nunique()),
        "distinct_families_in_window": int(usable["family"].nunique()),
        "undated_rows": int(eff.isna().sum()),
        "aum_populated_rows": int(aum.notna().sum()),
        "aum_sum_usd": None if aum.notna().sum() == 0 else float(aum.sum()),
        "plan_v2_1_stated_conversions": 203,
        "plan_v2_1_stated_aum_usd": 260e9,
    }


def audit_convexp(cfg):
    path = next((p for p in CONVEXP_CANDIDATES if p.exists()), None)
    if path is None:
        return {"status": "MISSING",
                "searched": [str(p.relative_to(ROOT)) for p in CONVEXP_CANDIDATES]}
    df = pd.read_parquet(path)
    thr = cfg["convexp_treated_min"]
    treated = df[df["conv_exp"] >= thr]
    per_wave = treated.groupby("wave_id").size().sort_values(ascending=False)
    return {
        "status": "OK",
        "path": str(path.relative_to(ROOT)),
        "path_matches_plan_name": path.name == "conv_exposure.parquet",
        "rows_total": int(len(df)),
        "distinct_waves": int(df["wave_id"].nunique()),
        # permno is blank throughout the free-path build; cusip is the live
        # stock key. permno coverage is reported separately as an R2 blocker.
        "distinct_stocks_cusip": int(df["cusip"].nunique()),
        "convexp_treated_min": float(thr),
        "treated_rows": int(len(treated)),
        "treated_distinct_stocks_cusip": int(treated["cusip"].nunique()),
        "treated_distinct_waves": int(treated["wave_id"].nunique()),
        "waves_with_ge_10_treated": int((per_wave >= 10).sum()),
        "largest_wave_share_of_treated":
            None if len(treated) == 0 else float(per_wave.iloc[0] / len(treated)),
        "largest_wave_id": None if len(per_wave) == 0 else str(per_wave.index[0]),
        # The refraction-specific read: identification is cross-sectional within
        # announcement, but the effective treatment shocks are WAVES. Split the
        # treated mass on the DFA anchor to see what survives without it (plan
        # §8.1 "drop DFA" robustness and §10 exit C both hinge on this).
        "treated_rows_by_wave": {str(k): int(v) for k, v in per_wave.items()},
        "treated_rows_excl_largest_wave": int(len(treated) - per_wave.iloc[0])
            if len(per_wave) else 0,
        "treated_waves_excl_largest": int(len(per_wave) - 1) if len(per_wave) else 0,
        "conv_exp_quantiles": {str(q): float(df["conv_exp"].quantile(q))
                               for q in (0.5, 0.9, 0.99, 1.0)},
        "pre_etf_ownership_populated": int(df["pre_etf_ownership"].notna().sum()),
        "permno_blank_rows": int((df["permno"].fillna("") == "").sum()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    cfg = load_config()
    out = {"config": cfg, "events": audit_events(cfg), "conv_exposure": audit_convexp(cfg)}

    ev, cx = out["events"], out["conv_exposure"]
    flags = []
    if ev["equity_US_in_wave_window"] < ev["plan_v2_1_stated_conversions"]:
        flags.append(
            "SCALE: plan v2.1 §2 states %d conversions; %d equity_US rows fall in "
            "the §sample wave window [%s, %s]."
            % (ev["plan_v2_1_stated_conversions"], ev["equity_US_in_wave_window"],
               cfg["waves_start"], cfg["waves_end"]))
    if ev["aum_populated_rows"] == 0:
        flags.append("AUM: plan §2 quotes ~$260B; AUM_at_conversion_USD is empty "
                     "in every row, so the figure is not reproducible from the file.")
    if cx.get("status") == "OK":
        if not cx["path_matches_plan_name"]:
            flags.append("FILENAME: plan §4/§5 name conv_exposure.parquet; the built "
                         "file is %s." % cx["path"])
        if cx["treated_distinct_waves"] < cfg["effective_cluster_warning_below"]:
            flags.append(
                "CLUSTERS: %d waves carry any stock at ConvExp>=%.3f, below the "
                "frozen_config effective_cluster_warning_below=%d."
                % (cx["treated_distinct_waves"], cx["convexp_treated_min"],
                   cfg["effective_cluster_warning_below"]))
        if (cx["largest_wave_share_of_treated"] or 0) > 0.5:
            flags.append(
                "CONCENTRATION: %.1f%% of treated stock-waves sit in a single wave "
                "(%s). Outside it the treated sample is %d stock-waves across %d "
                "waves. Plan §6 states the design is 'few, DFA-heavy'; this is the "
                "magnitude. Bears on §8.1 drop-DFA, §9 G5 power and §10 exit C."
                % (100 * cx["largest_wave_share_of_treated"], cx["largest_wave_id"],
                   cx["treated_rows_excl_largest_wave"], cx["treated_waves_excl_largest"]))
        if cx["permno_blank_rows"]:
            flags.append("PERMNO: %d/%d rows carry no permno; CRSP merge coverage "
                         "for the R2 panel is that much lower."
                         % (cx["permno_blank_rows"], cx["rows_total"]))
    out["flags"] = flags

    text = json.dumps(out, indent=2, ensure_ascii=False)
    if a.json:
        Path(a.json).write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
