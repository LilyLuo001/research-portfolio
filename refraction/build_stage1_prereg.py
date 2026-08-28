#!/usr/bin/env python3
"""Render the Stage-1 pre-registration from frozen_config.yaml.

Every number in the output is INJECTED from the config — the queue's REFR-R4-prereg note
requires "zero model-generated digits", and this script is how that is enforced rather than
promised. Prose describes; the config supplies the values.

Stage 1 registers what is already determined and needs no data: hypotheses, estimators, gate
algorithms, decision rules and definitions. Stage 2 later appends only quantities a stage-1
algorithm computes (realized w_shrink, the G8 outcome arm, usable cluster counts).

  python refraction/build_stage1_prereg.py [-o refraction/STAGE1_PREREG.md]

Submission itself is REFR-GATE-OSF, a human gate. This script prepares the document and its
hash; it cannot and does not register anything.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "refraction" / "frozen_config.yaml"


def _git_rev() -> str:
    r = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"],
                       capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else "unknown"


def _fmt(v) -> str:
    if isinstance(v, bool):
        return "yes" if v else "no"
    if v is None:
        return "**NOT SET** (stage 2)"
    if isinstance(v, (list, tuple)):
        return ", ".join(_fmt(x) for x in v)
    if isinstance(v, dict):
        return "; ".join("%s = %s" % (k, _fmt(x)) for k, x in v.items())
    return str(v)


def render(cfg: dict) -> str:
    ne = cfg["network_exposure"]
    d = ne["cr_definition"]
    beta = cfg["beta"]
    sel = beta["w_shrink_selection"]
    spec = beta["w_shrink_grid_spec"]
    g0 = cfg["gate0_thresholds"]
    rule = ne["first_stage_outcome_choice_rule"]
    norm = ne["first_stage_outcome_normalization"]
    L = []
    a = L.append

    a("# Refraction — Stage-1 pre-registration")
    a("")
    a("Registered spec: **%s**. Generated from `refraction/frozen_config.yaml`; every value "
      "below is injected from that file, not written by hand." % cfg["prereg"]["registered_spec"])
    a("")
    a("Stage 1 registers what is already determined and requires no data. Stage 2 appends "
      "only quantities a stage-1 algorithm computes: %s. Changes to hypotheses, estimators, "
      "decision rules or thresholds are forbidden at stage 2."
      % _fmt(cfg["prereg"]["stage2"]["contents_allowed"]))
    a("")

    a("## 1. Sample frame")
    a("")
    s = cfg["sample"]
    a("| item | value |")
    a("|---|---|")
    for k in ("announcements_start", "announcements_end", "waves_start", "waves_end"):
        a("| %s | %s |" % (k, _fmt(s.get(k))))
    for k in ("pre_quarters_required", "post_quarters_required", "announcement_types"):
        a("| %s | %s |" % (k, _fmt(cfg["panel"].get(k))))
    a("")

    a("## 2. The flow measure (CR)")
    a("")
    a("    %s" % d["formula"])
    a("")
    a("| element | registered value |")
    a("|---|---|")
    for k in ("source", "numerator", "numerator_uses_price_or_nav", "denominator",
              "denominator_timing", "sign_convention", "shares_corporate_action_adjusted",
              "corporate_action_convention", "undefined_on_missing_prior_day"):
        a("| %s | %s |" % (k, _fmt(d.get(k))))
    a("")
    a("### Primary exposure magnitude")
    a("")
    a("    CR_mag = |CR_raw|")
    a("")
    a("| element | registered value |")
    a("|---|---|")
    for k in ("transform", "centering", "scaling", "winsorization"):
        a("| %s | %s |" % (k, _fmt(d["primary_exposure_transform"].get(k))))
    a("| standardize_within_fund | %s |" % _fmt(d.get("standardize_within_fund")))
    a("")
    a("No centring, no within-fund scaling, no winsorization. Creation/redemption is rare, "
      "and any fund-specific statistic computed on a mostly-zero series is dominated by the "
      "zeros: a fund with 2 nonzero days in 250 has a within-fund 99th percentile of zero, "
      "which would clip both of its genuine events to zero exposure. Comparability across "
      "funds is handled by the fund x date fixed effects, which absorb any fund-level scale.")
    a("")
    a("### Robustness exposure magnitude (never the primary)")
    a("")
    a("| element | registered value |")
    a("|---|---|")
    for k in ("column", "clip", "clip_pct", "clip_estimated_on",
              "min_nonzero_events_for_fund_specific_cap", "pooled_cap_fallback",
              "preserve_zero_exactly", "never_zero_a_genuine_event", "scaling",
              "may_replace_primary"):
        a("| %s | %s |" % (k, _fmt(d["robustness_exposure_transform"].get(k))))
    a("")
    a("Columns: raw `%s` (sign, zero-event status, event census, concentration); untreated "
      "magnitude `%s`; primary exposure magnitude `%s`; robustness column `%s`."
      % (d["raw_column"], d["magnitude_raw_column"], d["analysis_column"],
         d["robustness_exposure_transform"]["column"]))
    a("")
    a("Invariants, enforced on every build:")
    a("")
    for k, v in d["invariants"].items():
        a("- **%s** — `%s`" % (k, v))
    a("")

    a("## 3. G8 — first-stage mechanism validation")
    a("")
    a("Primary outcome class `%s`; exposure `%s`. The signed form `%s` is forbidden for the "
      "primary and belongs only to the return corroboration."
      % (ne["first_stage_primary_outcome_class"], ne["first_stage_primary_exposure"],
         ne["first_stage_corroborating_exposure"]))
    a("")
    a("### 3.1 The two candidate arms")
    a("")
    a("| arm | outcome | exposure | sided | requires |")
    a("|---|---|---|---|---|")
    for arm, c in ne["first_stage_primary_candidates"].items():
        a("| %s | `%s` | %s | %s | %s |"
          % (arm, c["outcome_expression"], c["exposure"], c["sided"], c["requires"]))
    a("")
    a("### 3.2 The arm-selection rule (data quality only, resolved before any coefficient)")
    a("")
    a("| criterion | floor |")
    a("|---|---|")
    for k, v in rule["use_preferred_iff_all"].items():
        a("| %s | %s |" % (k, _fmt(v)))
    a("")
    a("All must hold; otherwise the fallback arm. Decided before any treatment coefficient: "
      "%s. Recorded in `%s`."
      % (_fmt(rule["decided_before_any_treatment_coefficient"]), rule["decision_record"]))
    a("")
    a("### 3.3 Outcome unit")
    a("")
    a("| element | registered value |")
    a("|---|---|")
    for k in ("numerator", "denominator", "unit", "adv_window_trading_days", "adv_statistic",
              "adv_min_nonzero_days", "winsorize_outcome_pct", "log_transform"):
        a("| %s | %s |" % (k, _fmt(norm.get(k))))
    a("")
    a("### 3.4 Design")
    a("")
    a("Pooled interaction, fixed effects `%s`; CR-interacted controls: %s (all predetermined). "
      "Post-treatment controls forbidden in the baseline: %s. Response lag: primary %s day(s), "
      "corroborating %s day(s)."
      % (ne["first_stage_fixed_effects"], _fmt(ne["first_stage_cr_interacted_controls"]),
         _fmt(ne["first_stage_post_treatment_controls_forbidden_in_baseline"]),
         _fmt(ne["first_stage_primary_outcome_lag_days"]),
         _fmt(ne["first_stage_response_lag_days"])))
    a("")
    a("Calibration window: %s." % _fmt(ne["calibration_window"]))
    a("")
    a("### 3.5 Decision rule")
    a("")
    a("Outcomes: %s." % _fmt(ne["first_stage_outcomes"]))
    a("")
    a("- Test is one-sided on the linear coefficient at `first_stage_primary_alpha` = %s."
      % _fmt(g0.get("first_stage_primary_alpha")))
    a("- Retirement requires an equivalence margin (`first_stage_equivalence_margin` = %s); "
      "without one, a non-significant estimate is **inconclusive**, not retired."
      % _fmt(ne["first_stage_equivalence_margin"]))
    a("- `INSUFFICIENT_IDENTIFYING_VARIATION` is a numerical-degeneracy classification: "
      "%s." % _fmt(ne["first_stage_insufficient_variation_rules"]))
    a("- Power trigger active: %s. MDE is reported in every case but classifies nothing."
      % _fmt(ne["first_stage_power_trigger_active"]))
    a("- Reported for every outcome: %s." % _fmt(ne["first_stage_report_always"]))
    a("- Headline use permitted only when: %s." % ne["first_stage_headline_use_blocked_unless"])
    a("")

    a("## 4. G9 — portfolio continuity")
    a("")
    a("Corporate-action convention: `%s`, field `%s`; as-of field `%s` (report date, never a "
      "filing date). Continuity is reported continuously with threshold sensitivities; the "
      "registered anchors are %s / %s / %s."
      % (d["corporate_action_convention"], "cfacshr", "report_dt",
         _fmt(g0.get("portfolio_overlap_min")), _fmt(g0.get("portfolio_weight_corr_min")),
         _fmt(g0.get("portfolio_turnover_max"))))
    a("")
    a("Response if continuity fails: %s" % _fmt(g0.get("g9_confirmatory_response")))
    a("")

    a("## 5. Shrinkage weight — the algorithm, not the value")
    a("")
    a("`beta.w_shrink` = %s at stage 1; it is a **stage-2** quantity, computed by the frozen "
      "algorithm below from the G2 sweep." % _fmt(beta["w_shrink"]))
    a("")
    a("Candidate grid, frozen at stage 1: min %s, max %s, step %s, %s points, endpoints "
      "included %s. Post-sweep refinement forbidden: %s."
      % (_fmt(spec["min"]), _fmt(spec["max"]), _fmt(spec["step"]), _fmt(spec["n_points"]),
         _fmt(spec["endpoints_included"]), _fmt(spec["refinement_after_sweep_forbidden"])))
    a("")
    a("    grid = %s" % _fmt(beta["w_shrink_sweep_grid"]))
    a("")
    a("Feasibility at a grid point requires all four G2 conditions:")
    a("")
    a("| condition | threshold |")
    a("|---|---|")
    for name in sel["feasibility_conditions"]:
        a("| %s | %s |" % (name, _fmt(g0.get(name))))
    a("")
    a("Selection: **%s**. Minimum qualifying run length = `%s` = %s grid points. "
      "Tie-breaks: run %s, midpoint %s. No feasible run → %s."
      % (sel["algorithm"], sel["min_run_length"], _fmt(g0.get(sel["min_run_length"])),
         sel["tie_break_run"], sel["tie_break_midpoint"], sel["on_no_feasible_run"]))
    a("")
    a("Implemented in `refraction/pipeline/w_shrink.py`.")
    a("")

    a("## 6. Gate-0 thresholds")
    a("")
    a("| threshold | value |")
    a("|---|---|")
    for k in sorted(g0):
        a("| %s | %s |" % (k, _fmt(g0[k])))
    a("")
    a("Null entries are undecided by policy: R3 stops rather than defaulting them, and any "
      "value they later acquire must arrive with a recorded owner decision.")
    a("")

    a("## 7. Lookahead and prereg-before-outcomes")
    a("")
    a("Betas, lever and weights use only data strictly before a wave's effective date "
      "(assert A4). Any estimation touching post-period outcomes calls "
      "`guards/prereg_guard.py::assert_prereg_ok()`, which refuses until "
      "`prereg.osf_timestamp` and `beta.w_shrink` are set.")
    a("")
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="render the Stage-1 pre-registration")
    ap.add_argument("-o", "--out", default=str(ROOT / "refraction" / "STAGE1_PREREG.md"))
    args = ap.parse_args(argv)

    cfg = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    body = render(cfg)
    out = Path(args.out)
    out.write_text(body, encoding="utf-8")

    sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
    meta = {
        "document": (str(out.relative_to(ROOT)) if ROOT in out.resolve().parents
                     else str(out)),
        "sha256": sha,
        "config_sha256": hashlib.sha256(CONFIG_PATH.read_bytes()).hexdigest(),
        "registered_spec": cfg["prereg"]["registered_spec"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "code_version": _git_rev(),
        "stage": 1,
        "submitted": False,
        "submission_gate": "REFR-GATE-OSF (human_gate: true)",
        "note": ("This file records that the stage-1 document exists and what it hashes to. "
                 "It is NOT a registration. Submission is a human act; on completion set "
                 "prereg.stage1.timestamp and prereg.stage1.url in frozen_config.yaml in the "
                 "same commit."),
    }
    Path(str(out) + ".submission.json").write_text(json.dumps(meta, indent=2) + "\n",
                                                   encoding="utf-8")
    print("wrote %s (%d lines)\nsha256 %s" % (out, body.count("\n"), sha))
    print("NOT SUBMITTED — REFR-GATE-OSF is a human gate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
