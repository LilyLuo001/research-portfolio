#!/usr/bin/env python3
"""Small SPY--ES measurement demo using existing SCC feature parquets.

This is deliberately non-structural.  It separates normalized price paths,
update activity, and cross-channel divergence/recovery.  It does not estimate
information shares or a channel-availability treatment effect.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


EVENTS = {
    "2023-02-01": {"kind": "EVENT", "pair": "FOMC_20230201"},
    "2023-01-25": {"kind": "CONTROL", "pair": "FOMC_20230201"},
    "2023-03-22": {"kind": "EVENT", "pair": "FOMC_20230322"},
    "2023-03-15": {"kind": "CONTROL", "pair": "FOMC_20230322"},
}
EQ_COLS = [
    "date", "symbol", "venue", "grid_shift_ms", "second_index",
    "quote_valid", "ret_0_100ms", "ret_100ms_1s", "spread_bp",
    "bid_depth", "ask_depth", "mid_update_count_1s", "mid_update_age_ms",
]
ES_COLS = [
    "date", "grid_shift_ms", "second_index", "es_valid", "ret_0_100ms",
    "ret_100ms_1s", "spread_bp", "bid_depth", "ask_depth",
    "mid_update_count_1s", "mid_update_age_ms",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def safe_corr(x: pd.Series, y: pd.Series) -> float:
    z = pd.concat([x, y], axis=1).replace([np.inf, -np.inf], np.nan).dropna()
    if len(z) < 10 or z.iloc[:, 0].std() == 0 or z.iloc[:, 1].std() == 0:
        return np.nan
    return float(z.iloc[:, 0].corr(z.iloc[:, 1]))


def load_inputs(eq_path: Path, es_path: Path, shift: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    dates = list(EVENTS)
    eq = pd.read_parquet(eq_path, columns=EQ_COLS, filters=[
        ("date", "in", dates), ("symbol", "==", "SPY"),
        ("venue", "==", "XNAS.ITCH"), ("grid_shift_ms", "==", shift),
    ])
    es = pd.read_parquet(es_path, columns=ES_COLS, filters=[
        ("date", "in", dates), ("grid_shift_ms", "==", shift),
    ])
    return eq, es


def one_date(date: str, eq: pd.DataFrame, es: pd.DataFrame, shift: int) -> tuple[dict, pd.DataFrame]:
    a = eq.loc[eq.date == date].copy()
    b = es.loc[es.date == date].copy()
    if a.duplicated("second_index").any() or b.duplicated("second_index").any():
        raise RuntimeError(f"duplicate second_index for {date}, shift {shift}")
    a["spy_ret_bp"] = a.ret_0_100ms + a.ret_100ms_1s
    b["es_ret_bp"] = b.ret_0_100ms + b.ret_100ms_1s
    z = a.merge(b, on=["date", "grid_shift_ms", "second_index"], suffixes=("_spy", "_es"), how="outer", validate="one_to_one")
    expected = pd.DataFrame({"second_index": np.arange(60, 1201, dtype=int)})
    z = expected.merge(z, on="second_index", how="left", validate="one_to_one")
    z["date"] = date
    z["grid_shift_ms"] = shift
    z["rel_second"] = z.second_index - 600
    z = z.loc[z.rel_second.between(-540, 600)].sort_values("rel_second").reset_index(drop=True)
    pre = z.loc[z.rel_second.between(-540, -60) & z.quote_valid & (z.es_valid == 1)].dropna(subset=["spy_ret_bp", "es_ret_bp"])
    denom = float(np.dot(pre.es_ret_bp, pre.es_ret_bp))
    beta = float(np.dot(pre.es_ret_bp, pre.spy_ret_bp) / denom) if len(pre) >= 120 and denom > 0 else np.nan
    # Exactly 60 consecutive one-second bins.  On the primary 0-ms grid they
    # cover (t0,t0+60s].  The 500-ms sensitivity covers
    # (t0+0.5s,t0+60.5s] and is labelled as such rather than pretending to
    # have identical endpoints.
    post = z.loc[z.rel_second.between(1, 60)].copy()
    joint = post.quote_valid.fillna(False) & post.es_valid.eq(1) & post.spy_ret_bp.notna() & post.es_ret_bp.notna()
    post["joint_valid"] = joint
    post["spy_cum_bp"] = post.spy_ret_bp.where(joint).cumsum(skipna=False)
    post["es_cum_bp"] = post.es_ret_bp.where(joint).cumsum(skipna=False)
    post["divergence_bp"] = post.spy_cum_bp - beta * post.es_cum_bp
    post["date_kind"] = EVENTS[date]["kind"]
    post["pair_id"] = EVENTS[date]["pair"]
    post["beta_pre"] = beta
    all_joint = bool(joint.all()) and len(post) == 60
    first10 = post.loc[post.rel_second.between(0, 10), "divergence_bp"].abs()
    max10 = float(first10.max()) if all_joint and len(first10) else np.nan
    at60 = post.loc[post.rel_second == 60, "divergence_bp"]
    abs60 = float(at60.abs().iloc[0]) if all_joint and len(at60) else np.nan
    residual_ratio = abs60 / max10 if np.isfinite(max10) and max10 > 0 else np.nan
    lead = post.set_index("rel_second")
    corr_es_to_spy = safe_corr(lead.es_ret_bp.shift(1), lead.spy_ret_bp) if all_joint else np.nan
    corr_spy_to_es = safe_corr(lead.spy_ret_bp.shift(1), lead.es_ret_bp) if all_joint else np.nan
    def endpoint(frame: pd.DataFrame, rel: int, field: str) -> float:
        value = frame.loc[frame.rel_second == rel, field]
        return float(value.iloc[0]) if len(value) and np.isfinite(value.iloc[0]) else np.nan
    metrics = {
        "date": date, "date_kind": EVENTS[date]["kind"], "pair_id": EVENTS[date]["pair"],
        "grid_shift_ms": shift, "pre_beta_spy_on_es": beta,
        "pre_rows": int(len(pre)), "post_expected_bins": 60, "post_grid_rows": int(len(post)),
        "post_joint_valid_bins": int(joint.sum()), "post_all_joint_valid": all_joint,
        "support_start_offset_ms_exclusive": shift, "support_end_offset_ms_inclusive": 60000 + shift,
        "spy_cum_end1_bp": endpoint(post, 1, "spy_cum_bp"),
        "es_cum_end1_bp": endpoint(post, 1, "es_cum_bp"),
        "spy_cum_end5_bp": endpoint(post, 5, "spy_cum_bp"),
        "es_cum_end5_bp": endpoint(post, 5, "es_cum_bp"),
        "spy_cum_end60_bp": endpoint(post, 60, "spy_cum_bp"),
        "es_cum_end60_bp": endpoint(post, 60, "es_cum_bp"),
        "max_abs_divergence_first10_bins_bp": max10,
        "abs_divergence_interval_end_bp": abs60,
        "residual_divergence_ratio_end_to_peak10bins": residual_ratio,
        "corr_es_lag1_to_spy": corr_es_to_spy, "corr_spy_lag1_to_es": corr_spy_to_es,
        "lead_balance_es_minus_spy": corr_es_to_spy - corr_spy_to_es,
        "spy_updates_60_bins": float(post.mid_update_count_1s_spy.sum(min_count=60)),
        "es_updates_60_bins": float(post.mid_update_count_1s_es.sum(min_count=60)),
        "spy_median_spread_bp_60_bins": float(post.spread_bp_spy.median()) if all_joint else np.nan,
        "es_median_spread_bp_60_bins": float(post.spread_bp_es.median()) if all_joint else np.nan,
        "spy_median_displayed_depth_60_bins": float(((post.bid_depth_spy + post.ask_depth_spy) / 2).median()) if all_joint else np.nan,
        "es_median_displayed_depth_60_bins": float(((post.bid_depth_es + post.ask_depth_es) / 2).median()) if all_joint else np.nan,
    }
    keep = ["date", "date_kind", "pair_id", "grid_shift_ms", "rel_second", "joint_valid", "beta_pre",
            "spy_cum_bp", "es_cum_bp", "divergence_bp"]
    return metrics, post[keep]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--equity", required=True, type=Path)
    ap.add_argument("--futures", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    all_metrics, all_paths = [], []
    for shift in (0, 500):
        eq, es = load_inputs(args.equity, args.futures, shift)
        for date in sorted(EVENTS):
            m, p = one_date(date, eq, es, shift)
            all_metrics.append(m); all_paths.append(p)
    metrics = pd.DataFrame(all_metrics).sort_values(["grid_shift_ms", "date"])
    paths = pd.concat(all_paths, ignore_index=True)
    if len(metrics) != 8 or len(paths) != 8 * 60:
        raise RuntimeError(f"unexpected outputs metrics={len(metrics)}, paths={len(paths)}")
    metrics_path = args.out / "FOMC_DEMO_METRICS.csv"
    paths_path = args.out / "FOMC_DEMO_PATHS.csv.gz"
    metrics.to_csv(metrics_path, index=False)
    paths.to_csv(paths_path, index=False, compression="gzip")
    receipt = {
        "status": "COMPLETE_REAL_EXISTING_DATA_DEMO", "dates": sorted(EVENTS),
        "selection": "first two chronological 2023 event/control pairs with existing feature files; no response selection",
        "instruments": ["SPY XNAS venue BBO", "front ES GLBX venue BBO"],
        "grid_shifts_ms": [0, 500], "event_second_index": 600,
        "grid_support": {"0": "(t0,t0+60s]", "500": "(t0+0.5s,t0+60.5s]"},
        "pre_beta_grid_indices_relative": [-540, -60], "post_grid_indices_relative": [1, 60],
        "interpretation": "non-structural measurement demo; not information share and not channel-treatment evidence",
        "input_hashes": {"equity": sha256(args.equity), "futures": sha256(args.futures)},
        "output_hashes": {"metrics": sha256(metrics_path), "paths": sha256(paths_path)},
        "output_rows": {"metrics": len(metrics), "paths": len(paths)},
    }
    (args.out / "FOMC_DEMO_RECEIPT.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": receipt["status"], "metrics_rows": len(metrics), "path_rows": len(paths)}))


if __name__ == "__main__":
    main()
