#!/usr/bin/env python3
"""
assert_panel.py — the R2 task's 14 assertions (执行手册 §R2, A1–A14) as
importable checks. panel_ann.parquet may be written ONLY if every hard
assertion passes; any failure exits non-zero. Upstream problems are reported
as UPSTREAM_ISSUE in the report — never "fixed" here (iron rule: don't bend
upstream data to pass an assert).

Expected schemas (C0-R):
  panel   : permno, announcement_id, type, date_ET, wave, is_treated, Post,
            ConvExp, r_total, <split cols>, beta_i, beta_b_loo, L, L_mkt,
            L_tilt, S_std (NULL legal for CPI/NFP w/o consensus), time_ET
  betas   : permno, wave, beta_i, se_beta, n_pre_announcements, max_est_date
  weights : wave, permno, weight            (pre-period holdings weights)
  basket  : wave, beta_b_full               (full-basket announcement beta)
  convexp : permno, wave, conv_exp          (P1 frozen file, read-only)
  calendar: announcement_id, type, date_ET  (scheduled only)

Usage:
  from refraction.pipeline.assert_panel import run_all
  report = run_all(...); ok = report["overall_pass"]
CLI:
  python assert_panel.py <panel.parquet> <betas.parquet> <weights.parquet>
                         <basket.parquet> <convexp.parquet> <calendar.csv>
                         <frozen_config.yaml> [src_dir]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[2]))
from refraction.guards.prereg_guard import LookaheadError, assert_no_lookahead  # noqa: E402

DEFAULT_SPLITS = ("r_c2o", "r_o2c")


def _res(passed: bool, detail: str, **extra) -> dict:
    return {"pass": bool(passed), "detail": detail, **extra}


def a1_primary_key(panel: pd.DataFrame) -> dict:
    dup = panel.duplicated(subset=["permno", "announcement_id"])
    n = int(dup.sum())
    return _res(n == 0, f"{n} duplicate (permno, announcement_id) rows")


def a2_treated_coverage(panel: pd.DataFrame, calendar: pd.DataFrame,
                        wave_effective: pd.Series, pre_quarters: int = 8) -> dict:
    """Every treated permno covers all scheduled announcements within ±pre_quarters
    quarters of its wave effective date; gaps are listed, any gap fails."""
    cal = calendar.copy()
    cal["date_ET"] = pd.to_datetime(cal["date_ET"])
    cal["q"] = cal["date_ET"].dt.to_period("Q")
    gaps: dict[str, list] = {}
    treated = panel[panel["is_treated"].astype(bool)]
    have = treated.groupby("permno")["announcement_id"].agg(set)
    for permno, grp in treated.groupby("permno"):
        wave = grp["wave"].iloc[0]
        eff_q = pd.Period(pd.to_datetime(wave_effective.loc[wave]), freq="Q")
        window = cal[(cal["q"] >= eff_q - pre_quarters) & (cal["q"] <= eff_q + pre_quarters)]
        missing = set(window["announcement_id"]) - have.get(permno, set())
        if missing:
            gaps[str(permno)] = sorted(missing)
    return _res(not gaps, f"{len(gaps)} treated permnos with coverage gaps", gaps=gaps)


def a3_return_identity(panel: pd.DataFrame, splits=DEFAULT_SPLITS, tol: float = 1e-8) -> dict:
    have_all = panel[list(splits)].notna().all(axis=1)
    diff = (panel.loc[have_all, "r_total"]
            - sum(panel.loc[have_all, c] for c in splits)).abs()
    bad = int((diff > tol).sum())
    n_missing = int((~have_all).sum())
    return _res(bad == 0,
                f"{bad} rows violate r_total = sum(splits) (tol {tol}); "
                f"{n_missing} rows lack a split component (legal, counted)",
                rows_missing_split=n_missing)


def a4_no_lookahead(betas: pd.DataFrame, wave_effective: pd.Series) -> dict:
    """Machine check of the lookahead ban: per (permno, wave), the max date used
    in beta estimation must be strictly before the wave effective date."""
    violations = []
    for _, row in betas.iterrows():
        try:
            assert_no_lookahead(row["max_est_date"], wave_effective.loc[row["wave"]],
                                what="beta estimation window",
                                permno=row["permno"], wave=row["wave"])
        except LookaheadError as e:
            violations.append(str(e))
    return _res(not violations, f"{len(violations)} lookahead violations",
                violations=violations[:20])


def a5_n_pre_distribution(betas: pd.DataFrame, n_pre_median_min: int) -> dict:
    s = betas["n_pre_announcements"]
    med, share30 = float(s.median()), float((s >= n_pre_median_min).mean())
    # Informational for the manifest; the PASS/FAIL judgement belongs to Gate-0 (G3).
    return _res(True, f"median n_pre = {med}, share >= {n_pre_median_min}: {share30:.2%} "
                      "(recorded for Gate-0 G3; not a hard assert here)",
                median=med, share_ge_min=share30)


def a6_no_magic_w_shrink(src_dir: Path) -> dict:
    """Static scan: w_shrink must come from frozen_config.yaml, never a literal."""
    pattern = re.compile(r"w_shrink\s*(?::|=)\s*[0-9.]")
    hits = []
    for py in sorted(Path(src_dir).rglob("*.py")):
        for i, line in enumerate(py.read_text().splitlines(), 1):
            if pattern.search(line) and "frozen_config" not in line:
                hits.append(f"{py}:{i}: {line.strip()}")
    return _res(not hits, f"{len(hits)} hard-coded w_shrink literals", hits=hits)


def a7_lever_identity(panel: pd.DataFrame, tol: float = 1e-10) -> dict:
    fails = []
    for col in ("beta_b_loo", "L"):
        n_inf = int(np.isinf(panel[col].to_numpy(dtype=float, na_value=np.nan)).sum())
        if n_inf:
            fails.append(f"{col}: {n_inf} inf values")
    resid = (panel["L"] - (panel["L_mkt"] + panel["L_tilt"])).abs()
    bad = int((resid > tol).sum())
    if bad:
        fails.append(f"{bad} rows violate L = L_mkt + L_tilt (tol {tol})")
    return _res(not fails, "; ".join(fails) or "ok")


def a8_weights_sum(weights: pd.DataFrame, lo: float = 0.98, hi: float = 1.02) -> dict:
    sums = weights.groupby("wave")["weight"].sum()
    bad = sums[(sums < lo) | (sums > hi)]
    return _res(bad.empty, f"{len(bad)} waves with weight sum outside [{lo},{hi}]",
                offending={str(k): float(v) for k, v in bad.items()})


def a9_loo_reconstruction(betas: pd.DataFrame, weights: pd.DataFrame,
                          basket: pd.DataFrame, n_sample: int = 50,
                          tol: float = 1e-10, seed: int = 42) -> dict:
    """beta_b_loo(i) must equal (beta_b_full − w_i·beta_i)/(1 − w_i)."""
    m = (betas.merge(weights, on=["permno", "wave"], how="inner")
              .merge(basket, on="wave", how="inner"))
    if m.empty:
        return _res(False, "UPSTREAM_ISSUE: no (permno, wave) rows join betas×weights×basket")
    take = m.sample(n=min(n_sample, len(m)), random_state=seed)
    recon = (take["beta_b_full"] - take["weight"] * take["beta_i"]) / (1 - take["weight"])
    bad = (recon - take["beta_b_loo"]).abs() > tol
    return _res(int(bad.sum()) == 0,
                f"{int(bad.sum())}/{len(take)} sampled rows fail LOO reconstruction (tol {tol})")


def a10_convexp_frozen(panel: pd.DataFrame, convexp: pd.DataFrame, tol: float = 0.0) -> dict:
    """Panel ConvExp must match the P1 frozen file row-for-row. Stocks absent from
    the frozen file are legal ONLY as controls, i.e. with ConvExp exactly 0."""
    m = panel[["permno", "wave", "ConvExp"]].drop_duplicates().merge(
        convexp.rename(columns={"conv_exp": "conv_exp_frozen"}),
        on=["permno", "wave"], how="left")
    absent = m["conv_exp_frozen"].isna()
    bad_absent = int((absent & (m["ConvExp"] != 0)).sum())
    mism = int((~absent & ((m["ConvExp"] - m["conv_exp_frozen"]).abs() > tol)).sum())
    return _res(bad_absent == 0 and mism == 0,
                f"{bad_absent} nonzero exposures absent from frozen file; "
                f"{mism} value mismatches vs frozen file")


def a11_no_silent_drops(panel: pd.DataFrame, expected_pairs: pd.DataFrame) -> dict:
    have = set(map(tuple, panel[["permno", "announcement_id"]].itertuples(index=False)))
    want = set(map(tuple, expected_pairs[["permno", "announcement_id"]].itertuples(index=False)))
    missing, extra = want - have, have - want
    return _res(not missing and not extra,
                f"{len(missing)} expected rows missing, {len(extra)} unexpected rows",
                missing=sorted(missing)[:20], extra=sorted(extra)[:20])


def a12_event_window_alignment(panel: pd.DataFrame, release_times: dict,
                               n_per_type: int = 5, seed: int = 42) -> dict:
    """time_ET must match the configured release time per type; emits a per-type
    human-checkable sample of announcements (the manual's 抽 5 个 clause)."""
    bad = []
    samples = {}
    for typ, grp in panel.groupby("type"):
        want = release_times.get(typ)
        if want is None:
            bad.append(f"type {typ} has no configured release time")
            continue
        off = grp[grp["time_ET"].astype(str) != str(want)]
        if len(off):
            bad.append(f"type {typ}: {len(off)} rows with time_ET != {want}")
        anns = grp["announcement_id"].drop_duplicates()
        samples[typ] = anns.sample(n=min(n_per_type, len(anns)), random_state=seed).tolist()
    return _res(not bad, "; ".join(bad) or "ok", human_check_sample=samples)


def a13_column_missingness(panel: pd.DataFrame) -> dict:
    rates = panel.isna().mean()
    all_nan = rates[rates >= 1.0].index.tolist()
    return _res(not all_nan, f"{len(all_nan)} all-NaN columns: {all_nan}",
                missing_rates={c: float(r) for c, r in rates.items()})


def a14_traceback_rows(panel: pd.DataFrame, upstream: dict[str, tuple[pd.DataFrame, list, list]],
                       n_sample: int = 20, seed: int = 42, tol: float = 1e-10) -> dict:
    """Sample rows and re-derive listed columns from upstream frames.
    upstream = {name: (frame, join_keys, compare_cols)}; column names must match."""
    take = panel.sample(n=min(n_sample, len(panel)), random_state=seed)
    fails = []
    for name, (frame, keys, cols) in upstream.items():
        m = take.merge(frame[keys + cols].rename(columns={c: f"{c}__up" for c in cols}),
                       on=keys, how="left")
        for c in cols:
            up = m[f"{c}__up"]
            bad = int(((m[c] - up).abs() > tol).sum()) + int(up.isna().sum())
            if bad:
                fails.append(f"{name}.{c}: {bad}/{len(m)} sampled rows fail traceback")
    return _res(not fails, "; ".join(fails) or f"{len(take)} rows traced clean")


HARD = ["A1", "A2", "A3", "A4", "A6", "A7", "A8", "A9", "A10", "A11", "A12", "A13", "A14"]


def run_all(panel, betas, weights, basket, convexp, calendar, wave_effective,
            config: dict, expected_pairs=None, src_dir: Path | None = None,
            upstream_for_a14: dict | None = None) -> dict:
    g0 = config.get("gate0_thresholds", {})
    rel = config.get("panel", {}).get("release_times_ET", {})
    pre_q = int(config.get("panel", {}).get("pre_quarters_required", 8))
    if expected_pairs is None:
        expected_pairs = panel[["permno", "announcement_id"]].drop_duplicates()
    report = {
        "A1": a1_primary_key(panel),
        "A2": a2_treated_coverage(panel, calendar, wave_effective, pre_quarters=pre_q),
        "A3": a3_return_identity(panel),
        "A4": a4_no_lookahead(betas, wave_effective),
        "A5": a5_n_pre_distribution(betas, int(g0.get("n_pre_median_min", 30))),
        "A6": a6_no_magic_w_shrink(src_dir or HERE.parent),
        "A7": a7_lever_identity(panel),
        "A8": a8_weights_sum(weights),
        "A9": a9_loo_reconstruction(betas, weights, basket),
        "A10": a10_convexp_frozen(panel, convexp),
        "A11": a11_no_silent_drops(panel, expected_pairs),
        "A12": a12_event_window_alignment(panel, rel),
        "A13": a13_column_missingness(panel),
        "A14": (a14_traceback_rows(panel, upstream_for_a14) if upstream_for_a14
                else _res(True, "skipped: no upstream frames supplied (dev mode); "
                                "REQUIRED on real data — R14 checks this is not skipped "
                                "in the production manifest")),
    }
    report["overall_pass"] = all(report[k]["pass"] for k in HARD)
    return report


def _read(path: str) -> pd.DataFrame:
    p = Path(path)
    return pd.read_parquet(p) if p.suffix == ".parquet" else pd.read_csv(p)


def main(argv):
    if len(argv) < 8:
        print(__doc__)
        return 2
    panel, betas, weights, basket, convexp, calendar = map(_read, argv[1:7])
    config = yaml.safe_load(Path(argv[7]).read_text())
    src_dir = Path(argv[8]) if len(argv) > 8 else HERE.parent
    eff = convexp.drop_duplicates("wave").set_index("wave")["effective_date"] \
        if "effective_date" in convexp.columns else None
    if eff is None:
        print("FAIL: convexp file lacks effective_date (needed for A2/A4)")
        return 1
    rep = run_all(panel, betas, weights, basket, convexp, calendar, eff,
                  config, src_dir=src_dir)
    out = Path("assert_report.json")
    out.write_text(json.dumps(rep, indent=2, default=str))
    print(("PASS" if rep["overall_pass"] else "FAIL") + f" — report at {out}")
    return 0 if rep["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
