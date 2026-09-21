#!/usr/bin/env python3
"""Run the frozen model on an SCC-private, gate-authorized response panel."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from scipy.stats import t

from replication_statistics import design_diagnostics, fit_primary, sha256, support_gate, verify_opening_gate


def intervals(ans: dict) -> dict:
    # Two primary quantities: Bonferroni 95% familywise coverage uses
    # two-sided 97.5% marginal intervals, hence the .9875 quantile.
    crit = float(t.ppf(.9875, ans["cluster_df"]))
    out = dict(ans)
    for stem in ("same_industry_slope", "same_minus_other_slope"):
        out[stem + "_ci_low"] = out[stem] - crit * out[stem + "_se"]
        out[stem + "_ci_high"] = out[stem] + crit * out[stem + "_se"]
    out["critical_value_t_9875_bonferroni"] = crit
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=Path, required=True)
    ap.add_argument("--metadata", type=Path, nargs="+", required=True,
                    help="Exact metadata files bound by PREOUTCOME_REVIEW.json")
    ap.add_argument("--private-panel", type=Path, required=True,
                    help="Licensed SCC panel; must be created only after the gate passes")
    ap.add_argument("--public-out", type=Path, required=True)
    args = ap.parse_args()

    stage = args.stage.resolve()
    metadata = [p.resolve() for p in args.metadata]
    gate = verify_opening_gate(stage, metadata)  # before any response-bearing read
    panel = pd.read_parquet(args.private_panel)
    diagnostics = design_diagnostics(panel)
    minimum_controls = int(panel.n_controls.min()) if len(panel) and "n_controls" in panel else 0
    post_ok, post_reasons = support_gate(diagnostics, calendar_reuse_count=0,
                                         minimum_controls=minimum_controls)
    if not post_ok:
        args.public_out.mkdir(parents=True, exist_ok=True)
        pd.DataFrame([{"status": "NO_CERTIFIED_INTERVAL_POST_RESPONSE_ATTRITION",
                       "estimate": None, "standard_error": None, "ci_low": None, "ci_high": None,
                       "reason": "|".join(post_reasons)}]).to_csv(
                           args.public_out / "REPLICATION_RESULTS.csv", index=False)
        pd.DataFrame(columns=["kind", "omitted", "status"]).to_csv(
            args.public_out / "SENSITIVITY_RESULTS.csv", index=False)
        receipt = {
            "status": "INCONCLUSIVE_STOP_SPENDING_POST_RESPONSE_SUPPORT_FAILURE",
            "preoutcome_review_sha256": sha256(stage / "PREOUTCOME_REVIEW.json"),
            "private_panel_sha256": sha256(args.private_panel),
            "post_response_design_diagnostics": diagnostics,
            "post_response_support_failure_reasons": post_reasons,
            "sample_refilled_or_specification_changed": False,
            "interval_status": "NOT_CERTIFIED",
        }
        (args.public_out / "ESTIMATION_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
        return
    ans = intervals(fit_primary(panel))

    sensitivity = []
    for kind, column, prefix in (("leave_one_calendar_block", "block_id", "B"),
                                 ("leave_one_issuer", "issuer_id", "I")):
        values = sorted(panel[column].astype(str).unique())
        opaque = {value: f"{prefix}{i:02d}" for i, value in enumerate(values, 1)}
        for omitted in values:
            sub = panel[panel[column].astype(str) != omitted]
            try:
                z = fit_primary(sub)
                sensitivity.append({"kind": kind, "omitted": opaque[omitted],
                                    "same_industry_slope": z["same_industry_slope"],
                                    "same_minus_other_slope": z["same_minus_other_slope"],
                                    "rows": z["rows"], "issuer_events": z["issuer_events"],
                                    "calendar_blocks": z["calendar_blocks"], "status": "ESTIMATED"})
            except ValueError as exc:
                sensitivity.append({"kind": kind, "omitted": opaque[omitted], "status": f"NOT_ESTIMABLE:{exc}"})

    args.public_out.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {"quantity": "same_industry_slope", "estimate": ans["same_industry_slope"],
         "standard_error": ans["same_industry_slope_se"], "ci_low": ans["same_industry_slope_ci_low"],
         "ci_high": ans["same_industry_slope_ci_high"], "cluster_df": ans["cluster_df"]},
        {"quantity": "same_minus_other_slope_direct_interaction", "estimate": ans["same_minus_other_slope"],
         "standard_error": ans["same_minus_other_slope_se"], "ci_low": ans["same_minus_other_slope_ci_low"],
         "ci_high": ans["same_minus_other_slope_ci_high"], "cluster_df": ans["cluster_df"]},
    ]).to_csv(args.public_out / "REPLICATION_RESULTS.csv", index=False)
    pd.DataFrame(sensitivity).to_csv(args.public_out / "SENSITIVITY_RESULTS.csv", index=False)
    loo_positive = all((r.get("same_industry_slope", 0) > 0 and r.get("same_minus_other_slope", 0) > 0)
                       for r in sensitivity if r["status"] == "ESTIMATED")
    all_loo_estimable = all(r["status"] == "ESTIMATED" for r in sensitivity)
    if (ans["same_industry_slope_ci_low"] > 0 and ans["same_minus_other_slope_ci_low"] > 0
            and loo_positive and all_loo_estimable):
        scientific_action = "CONTINUE_MECHANISM_FEASIBILITY"
    elif ans["same_industry_slope_ci_high"] <= 0 or ans["same_minus_other_slope_ci_high"] <= 0:
        scientific_action = "STOP_SIGNAL_ROUTE"
    else:
        scientific_action = "INCONCLUSIVE_STOP_SPENDING"
    receipt = {
        "status": "ESTIMATION_COMPLETE_PENDING_INDEPENDENT_REVIEW",
        "preoutcome_review_sha256": sha256(stage / "PREOUTCOME_REVIEW.json"),
        "gate_status": gate["status"],
        "private_panel_sha256": sha256(args.private_panel),
        "private_panel_not_exported": True,
        "counts": {k: ans[k] for k in ("rows", "issuer_events", "calendar_blocks", "cluster_df")},
        "cr1_k_full_including_event_fixed_effects": ans["cr1_k_full_including_event_fixed_effects"],
        "post_response_design_diagnostics": diagnostics,
        "multiplicity": "Bonferroni 95% familywise coverage for two primary quantities via two-sided 97.5% marginal intervals",
        "scientific_action_pending_independent_review": scientific_action,
        "inference_limit": "descriptive; requires independent calendar-support blocks conditional on controls and can be violated by repeated firms or common shocks",
    }
    (args.public_out / "ESTIMATION_RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
