#!/usr/bin/env python3
"""assert_panel.py — P1's outcome-panel assertions, importable and CLI.

Why this exists before the panel does
-------------------------------------
P1 is the project whose entire validity rests on not peeking across an event
date, and it had no panel guard at all — refraction has fourteen. The WRDS
assessment names look-ahead and report-period alignment as *the* iteration risk
of a borrowed window; that is an argument for writing the guards before the
window opens, not while the meter is running.

Iron rule, inherited from refraction/pipeline/assert_panel.py: upstream problems
are REPORTED, never repaired here. Bending upstream data to pass an assert
defeats the assert. A failure means fix the producer, not the check.

The nine checks
  A1  primary key (permno, yyyyq) is unique
  A2  treated_post is a pure function of the quarter and the effective date
      — the look-ahead guard: a pre-treatment quarter may never be marked post
  A3  conv_exp is constant within (permno, wave_id) — treatment is a
      PRE-conversion snapshot; variation over quarters means it was recomputed
      with post-event information
  A4  conv_exp matches the frozen T2 file exactly — the panel may not recompute
      treatment, only carry it
  A5  every (wave_id, effective_date) exists in the frozen wave table
  A6  clean controls: a stock already treated by an earlier wave may not serve
      as a control in a later wave's window (stacked-DiD rule, Project_1.md §T5)
  A7  no silent drops — every (permno, wave) with a ConvExp reaches the panel
      or is accounted for
  A8  declared value ranges hold, read from ops/contracts/outcomes_panel.yaml
      so the contract stays the single source of truth
  A9  column missingness is profiled (recorded, not a hard failure)

Usage:
  from p1.pipeline.assert_panel import run_all
  report = run_all(panel, convexp, waves); assert report["overall_pass"]
CLI:
  python p1/pipeline/assert_panel.py <panel.parquet> [<convexp.parquet>] [<waves.csv>]
"""
from __future__ import annotations

import json
import pathlib
import sys

import pandas as pd
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "ops" / "contracts" / "outcomes_panel.yaml"
DEFAULT_CONVEXP = ROOT / "p1" / "conv_exposure.parquet"
DEFAULT_WAVES = ROOT / "p1" / "t2_wrds" / "waves.csv"

HARD = "HARD"          # must pass before the panel may be written
REPORT = "REPORT"      # profiled and surfaced, not a gate


def _res(name: str, passed: bool, detail: str, severity: str = HARD, **extra) -> dict:
    return {"assert": name, "passed": bool(passed), "severity": severity,
            "detail": detail, **extra}


def quarter_end(yyyyq: int) -> pd.Timestamp:
    """Last calendar day of the quarter encoded as YYYYQ (e.g. 20212 -> 2021-06-30)."""
    y, q = divmod(int(yyyyq), 10)
    if not 1 <= q <= 4:
        raise ValueError(f"malformed yyyyq: {yyyyq}")
    return pd.Timestamp(year=y, month=3 * q, day=1) + pd.offsets.MonthEnd(0)


# --------------------------------------------------------------------------- #
def a1_primary_key(panel: pd.DataFrame) -> dict:
    dup = int(panel.duplicated(subset=["permno", "yyyyq"]).sum())
    return _res("A1_primary_key", dup == 0,
                f"{dup} duplicate (permno, yyyyq) rows", n_duplicates=dup)


def a2_no_lookahead_in_treatment(panel: pd.DataFrame) -> dict:
    """treated_post must be exactly 1(quarter end > effective date).

    This is the single most consequential check in P1. A stock marked post in a
    quarter that ends before its conversion has had post-event information
    pulled backwards, and every downstream DiD coefficient is contaminated.
    """
    if "treated_post" not in panel.columns or "effective_date" not in panel.columns:
        return _res("A2_no_lookahead", False,
                    "panel lacks treated_post or effective_date — cannot verify "
                    "the look-ahead guard, so this fails closed")
    p = panel.dropna(subset=["effective_date"]).copy()
    qe = p["yyyyq"].map(quarter_end)
    eff = pd.to_datetime(p["effective_date"])
    expected = (qe > eff).astype(int)
    bad = p[p["treated_post"].astype(int) != expected]
    early = p[(p["treated_post"].astype(int) == 1) & (qe <= eff)]
    return _res("A2_no_lookahead", len(bad) == 0,
                f"{len(bad)} rows where treated_post disagrees with "
                f"(quarter_end > effective_date); {len(early)} of them are marked "
                f"POST before the conversion happened",
                n_mismatched=int(len(bad)), n_premature_post=int(len(early)))


def a3_treatment_constant_within_wave(panel: pd.DataFrame) -> dict:
    """ConvExp is a pre-conversion snapshot — it must not vary across quarters."""
    if "conv_exp" not in panel.columns:
        return _res("A3_treatment_constant", True, "no conv_exp column — skipped",
                    severity=REPORT)
    g = panel.dropna(subset=["conv_exp"]).groupby(["permno", "wave_id"])["conv_exp"]
    varying = g.nunique()
    bad = varying[varying > 1]
    return _res("A3_treatment_constant", len(bad) == 0,
                f"{len(bad)} (permno, wave) groups whose conv_exp changes over "
                "quarters — treatment recomputed with post-event data?",
                n_varying=int(len(bad)))


def a4_treatment_matches_frozen(panel: pd.DataFrame, convexp: pd.DataFrame | None,
                                tol: float = 0.0) -> dict:
    """The panel carries treatment; it does not get to recompute it."""
    if convexp is None or "conv_exp" not in panel.columns:
        return _res("A4_treatment_frozen", True,
                    "frozen ConvExp not supplied — skipped", severity=REPORT)
    key = ["permno", "wave_id"]
    left = panel.dropna(subset=["conv_exp"]).drop_duplicates(key)[key + ["conv_exp"]]
    right = convexp[key + ["conv_exp"]].drop_duplicates(key)
    m = left.merge(right, on=key, how="inner", suffixes=("_panel", "_frozen"))
    drift = m[(m["conv_exp_panel"] - m["conv_exp_frozen"]).abs() > tol]
    return _res("A4_treatment_frozen", len(drift) == 0,
                f"{len(drift)} of {len(m)} matched (permno, wave) pairs differ from "
                "the frozen T2 ConvExp", n_drifted=int(len(drift)),
                n_compared=int(len(m)))


def a5_waves_exist(panel: pd.DataFrame, waves: pd.DataFrame | None) -> dict:
    if waves is None or "wave_id" not in panel.columns:
        return _res("A5_waves_exist", True, "wave table not supplied — skipped",
                    severity=REPORT)
    known = set(waves["wave_id"].astype(str))
    seen = set(panel["wave_id"].dropna().astype(str))
    unknown = seen - known
    return _res("A5_waves_exist", not unknown,
                f"{len(unknown)} wave_id(s) in the panel are absent from the frozen "
                f"wave table: {sorted(unknown)[:5]}", unknown=sorted(unknown)[:20])


def a6_clean_controls(panel: pd.DataFrame) -> dict:
    """Stacked DiD: a stock already treated by an earlier wave is not a clean
    control for a later one (Project_1.md §T5 '禁止 already-treated')."""
    need = {"permno", "wave_id", "effective_date", "yyyyq"}
    if not need <= set(panel.columns):
        return _res("A6_clean_controls", True, "columns missing — skipped",
                    severity=REPORT)
    p = panel.dropna(subset=["effective_date"]).copy()
    p["eff"] = pd.to_datetime(p["effective_date"])
    # earliest treatment date each stock ever receives
    first_treat = p.groupby("permno")["eff"].min()
    p["first_treat"] = p["permno"].map(first_treat)
    p["qe"] = p["yyyyq"].map(quarter_end)
    # a row belonging to wave W, in a quarter already after an EARLIER wave
    # treated this same stock, is contaminated
    contaminated = p[(p["first_treat"] < p["eff"]) & (p["qe"] > p["first_treat"])]
    return _res("A6_clean_controls", len(contaminated) == 0,
                f"{len(contaminated)} rows are attributed to a wave while the same "
                "stock was already treated by an earlier wave",
                n_contaminated=int(len(contaminated)))


def a7_no_silent_drops(panel: pd.DataFrame, convexp: pd.DataFrame | None) -> dict:
    if convexp is None:
        return _res("A7_no_silent_drops", True, "frozen ConvExp not supplied — skipped",
                    severity=REPORT)
    key = ["permno", "wave_id"]
    want = set(map(tuple, convexp[key].drop_duplicates().astype(str).values))
    got = set(map(tuple, panel[key].drop_duplicates().astype(str).values))
    missing = want - got
    return _res("A7_no_silent_drops", not missing,
                f"{len(missing)} (permno, wave) pairs have a ConvExp but never reach "
                "the panel — drops must be explicit, not silent",
                n_missing=len(missing), sample=sorted(missing)[:10])


def a8_declared_ranges(panel: pd.DataFrame,
                       contract_path: pathlib.Path = CONTRACT) -> dict:
    """Value ranges come from the contract, so there is one source of truth
    (§126 demands a 值域 assert per variable)."""
    spec = yaml.safe_load(contract_path.read_text())
    fails = []
    for col, rule in (spec.get("columns") or {}).items():
        if not isinstance(rule, dict) or col not in panel.columns:
            continue
        s = pd.to_numeric(panel[col], errors="coerce")
        if "min" in rule and (s < rule["min"]).any():
            fails.append(f"{col} < {rule['min']}")
        if "max" in rule and (s > rule["max"]).any():
            fails.append(f"{col} > {rule['max']}")
        if rule.get("required") and panel[col].isna().any():
            fails.append(f"{col} has nulls but is required")
    return _res("A8_declared_ranges", not fails,
                "; ".join(fails) if fails else "all declared ranges hold",
                violations=fails)


def a9_missingness(panel: pd.DataFrame) -> dict:
    prof = {c: float(panel[c].isna().mean()) for c in panel.columns}
    worst = sorted(prof.items(), key=lambda kv: -kv[1])[:5]
    return _res("A9_missingness", True,
                "worst columns: " + ", ".join(f"{c} {v:.1%}" for c, v in worst),
                severity=REPORT, profile=prof)


# --------------------------------------------------------------------------- #
def run_all(panel: pd.DataFrame, convexp: pd.DataFrame | None = None,
            waves: pd.DataFrame | None = None) -> dict:
    checks = [
        a1_primary_key(panel),
        a2_no_lookahead_in_treatment(panel),
        a3_treatment_constant_within_wave(panel),
        a4_treatment_matches_frozen(panel, convexp),
        a5_waves_exist(panel, waves),
        a6_clean_controls(panel),
        a7_no_silent_drops(panel, convexp),
        a8_declared_ranges(panel),
        a9_missingness(panel),
    ]
    hard_failed = [c for c in checks if c["severity"] == HARD and not c["passed"]]
    return {"overall_pass": not hard_failed,
            "n_rows": int(len(panel)),
            "n_hard_failures": len(hard_failed),
            "checks": checks}


def _read(path: str) -> pd.DataFrame:
    p = pathlib.Path(path)
    return pd.read_csv(p) if p.suffix == ".csv" else pd.read_parquet(p)


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    panel = _read(argv[0])
    convexp = _read(argv[1]) if len(argv) > 1 else (
        pd.read_parquet(DEFAULT_CONVEXP) if DEFAULT_CONVEXP.exists() else None)
    waves = _read(argv[2]) if len(argv) > 2 else (
        pd.read_csv(DEFAULT_WAVES) if DEFAULT_WAVES.exists() else None)
    rep = run_all(panel, convexp, waves)
    for c in rep["checks"]:
        mark = "ok  " if c["passed"] else ("FAIL" if c["severity"] == HARD else "note")
        print(f"  [{mark}] {c['assert']}: {c['detail']}")
    print(json.dumps({"overall_pass": rep["overall_pass"],
                      "n_hard_failures": rep["n_hard_failures"]}, indent=2))
    return 0 if rep["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
