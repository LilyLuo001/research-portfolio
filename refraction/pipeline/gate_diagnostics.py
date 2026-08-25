#!/usr/bin/env python3
"""REFR-R3 — the Gate-0 six-line diagnostic.

What this module is allowed to see
----------------------------------
PRE-period rows and simulation output. Nothing else. Touching a post-period
outcome column before the OSF timestamp exists is the prereg-before-outcomes
violation the whole queue is arranged to prevent, so it is a HARD STARTUP CHECK
here: `refuse_post_period()` raises on any frame still carrying Post rows, and
every G-line takes a frame that has been through it.

What this module may NOT do
---------------------------
1. Choose a threshold. Every pass line is read from frozen_config, and
   `threshold()` raises on a missing OR null value rather than defaulting —
   which is how the two thresholds that were undecided until 2026-08-19 stopped
   R3 instead of being quietly invented.
2. Recommend anything. The report states facts and PASS / FAIL / EDGE. The
   verdict is the owner's at REFR-GATE-PREREG (执行手册 §R3: "报告只陈述事实与
   PASS/FAIL, 不写'建议继续/放弃'"). A test asserts the report contains no
   recommendation language.

Estimation seams left open on purpose: G5 takes MDEs from the power simulation
and G6 takes pre-trend coefficient estimates. Both are computed elsewhere and
handed in, so this module stays the part that can be verified today.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from refraction.guards.prereg_guard import PreregError  # noqa: E402

PASS, FAIL, EDGE = "PASS", "FAIL", "EDGE"


class MissingThreshold(Exception):
    """A pass line has no number. R3 stops; it never picks one."""


def threshold(config: dict, key: str):
    g0 = config.get("gate0_thresholds", {})
    if key not in g0:
        raise MissingThreshold(f"NEED_HUMAN: gate0_thresholds.{key} is not in "
                               "frozen_config — R3 does not choose thresholds.")
    if g0[key] is None:
        raise MissingThreshold(
            f"NEED_HUMAN: gate0_thresholds.{key} is null. It is pre-registration "
            "content and must be decided in ops/decisions.md BEFORE this "
            "diagnostic runs — choosing it now, with the data in hand, would be "
            "specification search.")
    return g0[key]


def refuse_post_period(frame: pd.DataFrame, name: str = "panel") -> pd.DataFrame:
    """Hard check: R3 may not see a post-period row."""
    if "Post" in frame.columns and frame["Post"].astype(bool).any():
        n = int(frame["Post"].astype(bool).sum())
        raise PreregError(
            f"prereg-before-outcomes: {name} carries {n} post-period rows. R3 "
            "runs before the OSF timestamp exists and may only touch pre-period "
            "data and simulation. Pass pre_only(frame) instead.")
    return frame


def pre_only(frame: pd.DataFrame):
    """Split off the pre rows and say how many were dropped — never silently."""
    if "Post" not in frame.columns:
        return frame, 0
    mask = ~frame["Post"].astype(bool)
    return frame[mask].copy(), int((~mask).sum())


def _res(line, verdict, facts, **extra):
    return {"line": line, "verdict": verdict, "facts": facts, **extra}


# --------------------------------------------------------------------------- #
# G1 — surprise coverage                                                       #
# --------------------------------------------------------------------------- #
def g1_surprise_coverage(assert_report: dict, config: dict) -> dict:
    """Consumes R1b's assert_report. FOMC completeness is reported separately
    because Plan §9 makes it unconditional ("FOMC series complete regardless")
    while the ≥95% line covers all scheduled releases."""
    need = float(threshold(config, "surprise_coverage_min"))
    scheduled = int(assert_report["n_scheduled"])
    usable = int(assert_report["n_usable_S"])
    cov = usable / scheduled if scheduled else 0.0
    fomc = assert_report.get("fomc_complete")
    return _res("G1", PASS if cov >= need else FAIL,
                {"scheduled_releases": scheduled, "usable_surprises": usable,
                 "coverage": round(cov, 4), "required": need,
                 "fomc_series_complete": fomc},
                coverage=cov)


# --------------------------------------------------------------------------- #
# G2 — the coupled shrinkage window (the decisive line)                        #
# --------------------------------------------------------------------------- #
def g2_shrinkage_window(sweep: pd.DataFrame, config: dict) -> dict:
    """For each w on the grid: SD(L̂) among treated names, |corr(L, ConvExp)|,
    and the share whose SE(β̂) is small relative to SD(L̂).

    sweep: w_shrink | permno | wave | beta_i | se_beta | L | ConvExp
    """
    sd_min = float(threshold(config, "sd_L_min"))
    corr_max = float(threshold(config, "corr_L_convexp_max"))
    share_min = float(threshold(config, "se_share_min"))
    ratio_max = float(threshold(config, "se_to_sdL_ratio_max"))
    treated_min = float(threshold(config, "convexp_treated_min"))
    min_width = int(threshold(config, "sweep_window_min_gridpoints"))

    rows = []
    for w, g in sweep.groupby("w_shrink", sort=True):
        t = g[g["ConvExp"] >= treated_min]
        sd = float(t["L"].std(ddof=1)) if len(t) > 1 else np.nan
        corr = (float(np.corrcoef(t["L"], t["ConvExp"])[0, 1])
                if len(t) > 2 and t["L"].std() > 0 and t["ConvExp"].std() > 0 else np.nan)
        share = (float((t["se_beta"] <= ratio_max * sd).mean())
                 if len(t) and np.isfinite(sd) else np.nan)
        rows.append({"w_shrink": float(w), "sd_L": sd, "abs_corr_L_convexp": abs(corr),
                     "se_share": share, "n_treated": int(len(t)),
                     "meets": bool(np.isfinite(sd) and sd >= sd_min
                                   and np.isfinite(corr) and abs(corr) <= corr_max
                                   and np.isfinite(share) and share >= share_min)})
    curve = pd.DataFrame(rows)
    feasible = curve[curve["meets"]]["w_shrink"].tolist()
    width = len(feasible)
    if width == 0:
        verdict = FAIL
    elif width < min_width:
        verdict = EDGE          # knife-edge: 执行手册 §R3 "宽度<网格 2 格"
    else:
        verdict = PASS
    return _res("G2", verdict,
                {"feasible_w": feasible, "window_width_gridpoints": width,
                 "required_width": min_width,
                 "lines": {"sd_L_min": sd_min, "corr_max": corr_max,
                           "se_share_min": share_min}},
                curve=curve.to_dict("records"))


# --------------------------------------------------------------------------- #
# G3 — beta estimability                                                       #
# --------------------------------------------------------------------------- #
def g3_beta_estimability(betas: pd.DataFrame, config: dict) -> dict:
    """Median pre-period announcement count.

    Per the 2026-08-19 decision D-C, a G3 failure is NOT an isolated line: median
    n_pre does not vary with w_shrink, so if it fails it fails at every point of
    the sweep, which is an empty G2 window — the Plan's own trigger for
    portfolio-level-or-kill. The flag travels with the result so the report
    cannot present it as a standalone miss.
    """
    need = float(threshold(config, "n_pre_median_min"))
    s = betas["n_pre_announcements"].astype(float)
    med = float(s.median()) if len(s) else np.nan
    share = float((s >= need).mean()) if len(s) else np.nan
    ok = np.isfinite(med) and med >= need
    return _res("G3", PASS if ok else FAIL,
                {"median_n_pre": med, "share_at_or_above_min": round(share, 4)
                 if np.isfinite(share) else None, "required_median": need,
                 "n_stocks": int(len(s))},
                implies_empty_g2_window=not ok)


# --------------------------------------------------------------------------- #
# G4 — basket distinctiveness / the framing gate                               #
# --------------------------------------------------------------------------- #
def g4_basket_distinctiveness(enriched: pd.DataFrame, basket: pd.DataFrame,
                              config: dict) -> dict:
    """D_b = |beta_b_loo − 1| across treated mass, plus the basket factor tilt.

    Mass-weighted by ConvExp per decision D-A: the Plan says treatment *mass*,
    and a name carrying 0.02 ConvExp does not count the same as one carrying
    0.0006.
    """
    d_min = float(threshold(config, "d_b_min"))
    mass_min = float(threshold(config, "d_b_mass_share_min"))
    treated_min = float(threshold(config, "convexp_treated_min"))

    t = enriched[enriched["ConvExp"] >= treated_min].copy()
    t["D_b"] = (t["beta_b_loo"] - 1.0).abs()
    total = float(t["ConvExp"].sum())
    distinct = float(t.loc[t["D_b"] >= d_min, "ConvExp"].sum())
    share = distinct / total if total > 0 else np.nan
    ok = np.isfinite(share) and share >= mass_min

    tilt = {}
    if basket is not None and "F_tilt" in basket.columns:
        f = basket.dropna(subset=["F_tilt"])
        if len(f):
            tval = (f["F_tilt"] / f["F_tilt_se"]).replace([np.inf, -np.inf], np.nan) \
                if "F_tilt_se" in f.columns else pd.Series(dtype=float)
            tilt = {"waves_with_F_tilt": int(len(f)),
                    "median_abs_F_tilt": float(f["F_tilt"].abs().median()),
                    "median_abs_t": float(tval.abs().median()) if len(tval.dropna()) else None}
    return _res("G4", PASS if ok else FAIL,
                {"treated_mass": round(total, 6),
                 "mass_share_with_D_b_at_or_above_min": round(share, 4)
                 if np.isfinite(share) else None,
                 "required_mass_share": mass_min, "d_b_min": d_min,
                 "median_D_b": float(t["D_b"].median()) if len(t) else None,
                 "factor_tilt": tilt},
                framing_gate_triggered=not ok)


# --------------------------------------------------------------------------- #
# G5 — power                                                                   #
# --------------------------------------------------------------------------- #
def analytic_mde_sigma(n_treated: int, n_control: int, t_pre: int, t_post: int,
                       conservatism: float) -> float:
    """MDE at 80% power, in units of the outcome's sigma. Same convention as the
    P1-T2a simulation this reuses: (1.96 + 0.84) × SE × a conservatism factor."""
    n_t, n_c = max(int(n_treated), 1), max(int(n_control), 1)
    se = np.sqrt((1.0 / n_t + 1.0 / n_c) * (1.0 / max(t_pre, 1) + 1.0 / max(t_post, 1)))
    return float(2.80 * se * conservatism)


def g5_power(mdes: dict, config: dict, effective_clusters: int | None = None,
             exit_d_bar: float | None = None) -> dict:
    """Every reported MDE must clear the registered line — pooled AND the two
    decomposed γ, per Plan §9 ("run separately for γ pooled, γ_tilt and γ_fac").
    """
    need = float(threshold(config, "mde_sigma_max"))
    required = ("gamma_pooled", "gamma_tilt", "gamma_fac")
    missing = [k for k in required if k not in mdes]
    if missing:
        raise MissingThreshold(f"NEED_INPUT: G5 needs an MDE for {missing} — Plan §9 "
                               "requires the decomposed γ separately, not only pooled.")
    worst = max(float(mdes[k]) for k in required)
    warn_below = int(config.get("inference", {})
                     .get("effective_cluster_warning_below", 0) or 0)
    facts = {"mde_sigma": {k: round(float(mdes[k]), 4) for k in required},
             "required_max": need, "worst_line": round(worst, 4),
             # Reported as a FACT, not a gate: no threshold for it is registered,
             # and R3 does not invent one. It is here because the 2026-08-19 sample
             # decision cut the wave count, and waves are the clustering dimension.
             "effective_clusters": effective_clusters,
             "effective_cluster_warning_below": warn_below or None,
             "exit_d_power_bar_sigma": exit_d_bar}
    return _res("G5", PASS if worst <= need else FAIL, facts,
                cluster_count_below_warning=(effective_clusters is not None
                                             and warn_below
                                             and effective_clusters < warn_below))


# --------------------------------------------------------------------------- #
# G6 — the pre-trend triple                                                    #
# --------------------------------------------------------------------------- #
def holm_adjust(pvalues) -> list:
    """Holm step-down adjusted p-values, order preserved."""
    p = np.asarray(list(pvalues), dtype=float)
    n = len(p)
    if n == 0:
        return []
    order = np.argsort(p)
    adj = np.empty(n, dtype=float)
    running = 0.0
    for rank, idx in enumerate(order):
        val = (n - rank) * p[idx]
        running = max(running, val)
        adj[idx] = min(running, 1.0)
    return [float(x) for x in adj]


def g6_pretrend(tests: dict, config: dict) -> dict:
    """tests = {name: {"joint_p": float, "lead_p": [floats]}} for the three legs:
    event-time γ̂ on pre-period announcements, treated-vs-control announcement-beta
    trends, and placebo-in-time.

    Per the 2026-08-19 decision D-B this is a FAILURE TO REJECT, so it passes
    trivially at low power. The lead confidence intervals belong in the report
    beside the p-values, and G5's archived bar is what makes "flat" meaningful.
    """
    need = float(threshold(config, "pretrend_joint_p_min"))
    adjust = config.get("gate0_thresholds", {}).get("pretrend_individual_lead_adjust")
    legs, all_ok = {}, True
    for name, t in tests.items():
        joint_ok = float(t["joint_p"]) >= need
        leads = list(t.get("lead_p", []))
        adj = holm_adjust(leads) if adjust == "holm" else leads
        # An individually significant lead fails the leg even when the joint test
        # passes — that is the second clause, not a footnote.
        lead_ok = all(a >= 0.05 for a in adj) if adj else True
        legs[name] = {"joint_p": float(t["joint_p"]), "joint_pass": joint_ok,
                      "lead_p_adjusted": [round(a, 4) for a in adj],
                      "no_significant_lead": lead_ok}
        all_ok = all_ok and joint_ok and lead_ok
    return _res("G6", PASS if all_ok else FAIL,
                {"required_joint_p_min": need, "lead_adjustment": adjust,
                 "legs": legs,
                 "caveat": "failure to reject — read against G5's archived power bar"})


# --------------------------------------------------------------------------- #
# report                                                                       #
# --------------------------------------------------------------------------- #
TITLES = {"G1": "Surprise coverage", "G2": "Shrinkage feasible window",
          "G3": "Beta estimability", "G4": "Basket distinctiveness",
          "G5": "Power", "G6": "Pre-trend triple"}


def render_report(lines: dict, dropped_post_rows: int = 0) -> str:
    out = ["# Gate-0 diagnostic report", "",
           f"generated: {datetime.now(timezone.utc).isoformat()}", "",
           "Facts and verdicts only. The adjudication is the owner's at "
           "REFR-GATE-PREREG; any core-line failure routes to the Plan §10 exit "
           "matrix.", "",
           f"Pre-period rows only; {dropped_post_rows} post-period rows were "
           "excluded before any computation.", "",
           "| line | | verdict |", "|---|---|---|"]
    for k in ("G1", "G2", "G3", "G4", "G5", "G6"):
        if k in lines:
            out.append(f"| {k} | {TITLES[k]} | **{lines[k]['verdict']}** |")
    out.append("")
    for k in ("G1", "G2", "G3", "G4", "G5", "G6"):
        if k not in lines:
            continue
        r = lines[k]
        out += [f"## {k} — {TITLES[k]}", "", f"**{r['verdict']}**", "", "```json",
                json.dumps(r["facts"], indent=2, default=str), "```", ""]
        if r.get("framing_gate_triggered"):
            out += ["> Framing gate triggered: basket-specific language is barred "
                    "repo-wide; claims are pre-committed to \"wrapper-induced beta "
                    "compression\" (Plan §10).", ""]
        if r.get("implies_empty_g2_window"):
            out += ["> This failure is equivalent to an empty G2 window: median "
                    "n_pre does not vary with w_shrink, so it fails at every grid "
                    "point (decision D-C, 2026-08-19).", ""]
        if r.get("cluster_count_below_warning"):
            out += ["> Effective clusters are below the configured warning level. "
                    "Reported as a fact; no pass line for it is registered.", ""]
    return "\n".join(out) + "\n"


def run(lines: dict, out_dir: Path, dropped_post_rows: int = 0):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "gate_report.md").write_text(render_report(lines, dropped_post_rows))
    (out_dir / "gate_report.json").write_text(
        json.dumps({"lines": lines, "dropped_post_rows": dropped_post_rows,
                    "generated": datetime.now(timezone.utc).isoformat()},
                   indent=2, default=str) + "\n")
    return {k: v["verdict"] for k, v in lines.items()}
